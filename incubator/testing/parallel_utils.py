"""
Parallel Worker Coordination Utilities
======================================

Functions for coordinating multiple parallel testing workers.
Uses file-based locking to prevent duplicate work.

Functions:
- claim_strategy: Attempt to claim a strategy for testing
- release_claim: Release a claim when done
- is_strategy_claimed: Check if strategy is already claimed
- get_worker_id: Generate unique worker ID
"""

import os
import json
import time
import uuid
from datetime import datetime
from typing import Optional

# Default paths
CLAIMS_DIR = 'tmp/parallel_claims'
DEFAULT_CLAIM_TIMEOUT = 1800  # 30 minutes


def _ensure_claims_dir():
    """Ensure claims directory exists."""
    os.makedirs(CLAIMS_DIR, exist_ok=True)


def get_worker_id() -> str:
    """
    Generate a unique worker ID based on hostname and UUID.
    
    Returns:
        Unique worker ID string
    """
    try:
        import socket
        hostname = socket.gethostname()
    except:
        hostname = 'unknown'
    
    short_uuid = uuid.uuid4().hex[:8]
    return f"{hostname}_{short_uuid}"


def is_strategy_claimed(strategy_name: str) -> bool:
    """
    Check if a strategy is currently claimed by any worker.
    
    Args:
        strategy_name: Name of the strategy
        
    Returns:
        True if claimed and not stale, False otherwise
    """
    claim_file = os.path.join(CLAIMS_DIR, f"{strategy_name}.claim")
    
    if not os.path.exists(claim_file):
        return False
    
    try:
        with open(claim_file, 'r') as f:
            claim_data = json.load(f)
        
        claim_time = datetime.fromisoformat(claim_data.get('timestamp', '2000-01-01'))
        elapsed = (datetime.now() - claim_time).total_seconds()
        
        # If claim is stale, it's effectively not claimed
        if elapsed > DEFAULT_CLAIM_TIMEOUT:
            return False
        
        return True
    except:
        # If we can't read the file, assume not claimed
        return False


def claim_strategy_with_id(strategy_name: str, worker_id: str, timeout: int = DEFAULT_CLAIM_TIMEOUT) -> bool:
    """
    Attempt to claim a strategy for exclusive testing.
    
    Args:
        strategy_name: Name of the strategy to claim
        worker_id: Unique identifier for this worker
        timeout: Seconds before claim is considered stale (default: 1800)
        
    Returns:
        True if claim successful, False if already claimed by another worker
    """
    _ensure_claims_dir()
    claim_file = os.path.join(CLAIMS_DIR, f"{strategy_name}.claim")
    
    try:
        # Check if already claimed
        if os.path.exists(claim_file):
            try:
                with open(claim_file, 'r') as f:
                    claim_data = json.load(f)
                
                # Check if claim is stale
                claim_time = datetime.fromisoformat(claim_data.get('timestamp', '2000-01-01'))
                elapsed = (datetime.now() - claim_time).total_seconds()
                
                if elapsed > timeout:
                    # Stale claim, we can take over
                    pass
                elif claim_data.get('worker_id') == worker_id:
                    # We already own this claim
                    return True
                else:
                    # Active claim by another worker
                    return False
            except:
                # Error reading claim file, try to claim anyway
                pass
        
        # Create claim
        claim_data = {
            'worker_id': worker_id,
            'strategy': strategy_name,
            'timestamp': datetime.now().isoformat(),
            'timeout': timeout
        }
        
        with open(claim_file, 'w') as f:
            json.dump(claim_data, f, indent=2)
        
        return True
        
    except Exception as e:
        print(f"Error claiming strategy {strategy_name}: {e}")
        return False


def release_claim_with_id(strategy_name: str, worker_id: str) -> bool:
    """
    Release a claim on a strategy.
    
    Args:
        strategy_name: Name of the strategy
        worker_id: Worker ID that made the claim
        
    Returns:
        True if released successfully, False otherwise
    """
    claim_file = os.path.join(CLAIMS_DIR, f"{strategy_name}.claim")
    
    if not os.path.exists(claim_file):
        return True  # Nothing to release
    
    try:
        # Verify we own this claim before releasing
        with open(claim_file, 'r') as f:
            claim_data = json.load(f)
        
        if claim_data.get('worker_id') == worker_id:
            os.remove(claim_file)
            return True
        else:
            # Not our claim, don't release
            return False
    except Exception as e:
        print(f"Error releasing claim for {strategy_name}: {e}")
        return False


def get_claim_info(strategy_name: str) -> Optional[dict]:
    """
    Get information about a strategy claim.
    
    Args:
        strategy_name: Name of the strategy
        
    Returns:
        Claim info dict or None if not claimed
    """
    claim_file = os.path.join(CLAIMS_DIR, f"{strategy_name}.claim")
    
    if not os.path.exists(claim_file):
        return None
    
    try:
        with open(claim_file, 'r') as f:
            claim_data = json.load(f)
        
        # Check if stale
        claim_time = datetime.fromisoformat(claim_data.get('timestamp', '2000-01-01'))
        elapsed = (datetime.now() - claim_time).total_seconds()
        timeout = claim_data.get('timeout', DEFAULT_CLAIM_TIMEOUT)
        
        claim_data['is_stale'] = elapsed > timeout
        claim_data['elapsed_seconds'] = elapsed
        
        return claim_data
    except:
        return None


def list_active_claims() -> list:
    """
    List all active (non-stale) strategy claims.
    
    Returns:
        List of dicts with claim information
    """
    _ensure_claims_dir()
    
    active_claims = []
    
    try:
        for filename in os.listdir(CLAIMS_DIR):
            if not filename.endswith('.claim'):
                continue
            
            strategy_name = filename[:-6]  # Remove .claim
            claim_info = get_claim_info(strategy_name)
            
            if claim_info and not claim_info.get('is_stale', False):
                active_claims.append({
                    'strategy': strategy_name,
                    'worker_id': claim_info.get('worker_id'),
                    'elapsed': claim_info.get('elapsed_seconds', 0)
                })
    except:
        pass
    
    return active_claims


def cleanup_stale_claims():
    """Remove all stale claim files."""
    _ensure_claims_dir()
    
    cleaned = 0
    
    try:
        for filename in os.listdir(CLAIMS_DIR):
            if not filename.endswith('.claim'):
                continue
            
            strategy_name = filename[:-6]
            claim_file = os.path.join(CLAIMS_DIR, filename)
            
            try:
                with open(claim_file, 'r') as f:
                    claim_data = json.load(f)
                
                claim_time = datetime.fromisoformat(claim_data.get('timestamp', '2000-01-01'))
                elapsed = (datetime.now() - claim_time).total_seconds()
                timeout = claim_data.get('timeout', DEFAULT_CLAIM_TIMEOUT)
                
                if elapsed > timeout:
                    os.remove(claim_file)
                    cleaned += 1
            except:
                # Can't read file, remove it
                try:
                    os.remove(claim_file)
                    cleaned += 1
                except:
                    pass
    except:
        pass
    
    return cleaned


def wait_for_claim(strategy_name: str, worker_id: str, max_wait: int = 60) -> bool:
    """
    Wait for a strategy claim to be released.
    
    Args:
        strategy_name: Strategy to wait for
        worker_id: Your worker ID (to verify you're not waiting on yourself)
        max_wait: Maximum seconds to wait
        
    Returns:
        True if strategy became available, False if timeout
    """
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        claim_info = get_claim_info(strategy_name)
        
        if claim_info is None:
            return True  # Available
        
        if claim_info.get('worker_id') == worker_id:
            return True  # We own it
        
        if claim_info.get('is_stale', False):
            return True  # Stale, can claim
        
        time.sleep(1)
    
    return False  # Timeout


# Wrapper functions for the expected API
def claim_strategy(strategy_name: str, timeout: int = 30) -> bool:
    """
    Attempt to claim a strategy for exclusive testing.
    
    Args:
        strategy_name: Name of the strategy to claim
        timeout: Seconds before claim is considered stale
        
    Returns:
        True if claim successful, False if already claimed by another worker
    """
    worker_id = get_worker_id()
    return claim_strategy_with_id(strategy_name, worker_id, timeout)


def release_claim(strategy_name: str) -> bool:
    """
    Release a claim on a strategy.
    
    Args:
        strategy_name: Name of the strategy
        
    Returns:
        True if released successfully, False otherwise
    """
    worker_id = get_worker_id()
    return release_claim_with_id(strategy_name, worker_id)
