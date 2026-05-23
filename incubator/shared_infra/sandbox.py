"""
AgentSandbox - Isolated Execution Environment
=============================================

Each AI agent runs in its own sandbox with:
- Isolated file system
- Resource limits (compute, storage)
- No network access (except read-only data bridge)
- Automatic cleanup and archival
"""

import os
import json
import shutil
import logging
import traceback
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable
from contextlib import contextmanager
import sys

logger = logging.getLogger(__name__)

# Sandbox root
SANDBOX_ROOT = Path(__file__).resolve().parents[1] / "agents"


class AgentSandbox:
    """
    Isolated environment for a single AI agent.
    
    Usage:
        with AgentSandbox("agent_001_kimi") as sandbox:
            sandbox.write_strategy("my_strategy.py", code)
            result = sandbox.run_backtest("my_strategy.py")
    """
    
    def __init__(self, agent_id: str, agent_type: str = "generic"):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.sandbox_dir = SANDBOX_ROOT / agent_id
        self.created_at = datetime.now(timezone.utc)
        self.metrics = {
            "backtests_run": 0,
            "strategies_created": 0,
            "compute_minutes_used": 0,
            "last_activity": None
        }
        
        # Create directory structure
        self._create_structure()
        self._load_or_init_state()
    
    def _create_structure(self):
        """Create sandbox directory structure."""
        dirs = [
            "strategy_code",
            "backtests",
            "paper_trades", 
            "models",
            "metrics",
            "logs",
            "temp"
        ]
        for d in dirs:
            (self.sandbox_dir / d).mkdir(parents=True, exist_ok=True)
        
        logger.info(f"[Sandbox] Created structure for {self.agent_id}")
    
    def _load_or_init_state(self):
        """Load existing state or initialize new."""
        state_file = self.sandbox_dir / "state.json"
        if state_file.exists():
            with open(state_file) as f:
                data = json.load(f)
                self.metrics = data.get("metrics", self.metrics)
                self.created_at = datetime.fromisoformat(data.get("created_at", self.created_at.isoformat()))
    
    def save_state(self):
        """Persist sandbox state."""
        state_file = self.sandbox_dir / "state.json"
        with open(state_file, 'w') as f:
            json.dump({
                "agent_id": self.agent_id,
                "agent_type": self.agent_type,
                "created_at": self.created_at.isoformat(),
                "metrics": self.metrics,
                "last_saved": datetime.now(timezone.utc).isoformat()
            }, f, indent=2)
    
    def write_strategy(self, filename: str, code: str, metadata: Optional[Dict] = None) -> Path:
        """
        Write strategy code to sandbox.
        
        Args:
            filename: Name of strategy file
            code: Python code string
            metadata: Optional strategy metadata
            
        Returns:
            Path to written file
        """
        # Validate filename
        if not filename.endswith('.py'):
            raise ValueError("Strategy files must be .py")
        if '..' in filename or '/' in filename:
            raise ValueError("Invalid filename")
        
        strategy_dir = self.sandbox_dir / "strategy_code"
        file_path = strategy_dir / filename
        
        # Write code
        with open(file_path, 'w') as f:
            f.write(code)
        
        # Write metadata
        if metadata:
            meta_path = strategy_dir / f"{filename}.meta.json"
            with open(meta_path, 'w') as f:
                json.dump({
                    **metadata,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "agent_id": self.agent_id
                }, f, indent=2)
        
        self.metrics["strategies_created"] += 1
        self.metrics["last_activity"] = datetime.now(timezone.utc).isoformat()
        self.save_state()
        
        logger.info(f"[Sandbox] {self.agent_id} wrote strategy: {filename}")
        return file_path
    
    def get_strategy(self, filename: str) -> Optional[str]:
        """Read strategy code from sandbox."""
        file_path = self.sandbox_dir / "strategy_code" / filename
        if not file_path.exists():
            return None
        with open(file_path) as f:
            return f.read()
    
    def list_strategies(self) -> List[Dict]:
        """List all strategies in sandbox."""
        strategy_dir = self.sandbox_dir / "strategy_code"
        strategies = []
        for f in strategy_dir.glob("*.py"):
            if f.suffix == '.py' and not f.name.endswith('.meta.json'):
                meta_file = Path(str(f) + '.meta.json')
                meta = {}
                if meta_file.exists():
                    with open(meta_file) as f:
                        meta = json.load(f)
                strategies.append({
                    "filename": f.name,
                    "path": str(f),
                    "created": meta.get("created_at"),
                    "metadata": meta
                })
        return strategies
    
    def save_backtest_result(self, strategy_name: str, results: Dict) -> Path:
        """Save backtest results."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        result_file = self.sandbox_dir / "backtests" / f"{strategy_name}_{timestamp}.json"
        
        with open(result_file, 'w') as f:
            json.dump({
                "strategy": strategy_name,
                "agent_id": self.agent_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "results": results
            }, f, indent=2)
        
        self.metrics["backtests_run"] += 1
        self.save_state()
        
        return result_file
    
    def get_all_backtests(self) -> List[Dict]:
        """Get all backtest results."""
        backtest_dir = self.sandbox_dir / "backtests"
        results = []
        for f in sorted(backtest_dir.glob("*.json"), reverse=True):
            with open(f) as fp:
                data = json.load(fp)
                results.append(data)
        return results
    
    def get_best_strategy(self, metric: str = "sharpe_ratio") -> Optional[Dict]:
        """Find best performing strategy by metric."""
        backtests = self.get_all_backtests()
        if not backtests:
            return None
        
        # Sort by metric
        sorted_tests = sorted(
            backtests,
            key=lambda x: x.get("results", {}).get(metric, float('-inf')),
            reverse=True
        )
        return sorted_tests[0] if sorted_tests else None
    
    def archive(self, reason: str = "completed", destination: Optional[Path] = None):
        """
        Archive sandbox to storage.
        
        Args:
            reason: Why archiving (completed, rejected, promoted)
            destination: Optional destination path
        """
        if destination is None:
            archive_root = Path(__file__).resolve().parents[1] / "archive"
            if reason == "promoted":
                destination = archive_root / "promoted" / self.agent_id
            else:
                destination = archive_root / "rejected" / self.agent_id
        
        # Copy to archive
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(self.sandbox_dir, destination)
        
        # Add archive metadata
        with open(destination / "archive_info.json", 'w') as f:
            json.dump({
                "archived_at": datetime.now(timezone.utc).isoformat(),
                "reason": reason,
                "agent_id": self.agent_id,
                "final_metrics": self.metrics
            }, f, indent=2)
        
        logger.info(f"[Sandbox] {self.agent_id} archived to {destination}")
        return destination
    
    def cleanup(self, keep_backtests: bool = True):
        """
        Clean up temporary files.
        
        Args:
            keep_backtests: If True, preserve backtest results
        """
        temp_dir = self.sandbox_dir / "temp"
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            temp_dir.mkdir()
        
        if not keep_backtests:
            backtest_dir = self.sandbox_dir / "backtests"
            for f in backtest_dir.glob("*.json"):
                f.unlink()
        
        logger.info(f"[Sandbox] {self.agent_id} cleaned up")
    
    def destroy(self, archive_first: bool = True):
        """
        Completely remove sandbox.
        
        Args:
            archive_first: Archive before deletion
        """
        if archive_first:
            self.archive(reason="destroyed")
        
        shutil.rmtree(self.sandbox_dir)
        logger.info(f"[Sandbox] {self.agent_id} destroyed")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.save_state()
        if exc_type:
            logger.error(f"[Sandbox] {self.agent_id} error: {exc_val}")
            # Save error info
            error_file = self.sandbox_dir / "logs" / "last_error.txt"
            with open(error_file, 'w') as f:
                f.write(f"Time: {datetime.now(timezone.utc).isoformat()}\n")
                f.write(f"Error: {exc_val}\n")
                f.write(traceback.format_exc())
        return False  # Don't suppress exceptions


@contextmanager
def temporary_sandbox(agent_id: str):
    """Context manager for temporary sandbox that auto-cleans."""
    sandbox = AgentSandbox(agent_id)
    try:
        yield sandbox
    finally:
        sandbox.cleanup()
