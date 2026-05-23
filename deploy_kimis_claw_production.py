#!/usr/bin/env python3
"""
Kimi's Claw Production Deployment Script

Deploys files from findstocks/kimis_claw/ to the production server at ftps2.50webs.com

Usage:
    python deploy_kimis_claw_production.py
    
Environment Variables (checked in order):
    - FTP_USER, USERNAME, FTP_USERNAME, USER
    - FTP_PASS, PASSWORD, FTP_PASSWORD, PASS, FTP_PASSWD
    - FTP_HOST (defaults to ftps2.50webs.com)
"""

import os
import sys
import ftplib
import time
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass

# Configuration
LOCAL_BASE_PATH = Path(r"e:\findtorontoevents_antigravity.ca\findstocks\kimis_claw")
REMOTE_BASE_PATH = "/findstocks/kimis_claw"
DEFAULT_FTP_HOST = "ftps2.50webs.com"
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# Files to deploy with their remote paths
FILES_TO_DEPLOY: List[Tuple[str, str]] = [
    # (local_relative_path, remote_path)
    ("index.html", f"{REMOTE_BASE_PATH}/index.html"),
    ("leaderboard.html", f"{REMOTE_BASE_PATH}/leaderboard.html"),
    ("README.md", f"{REMOTE_BASE_PATH}/README.md"),
    ("api/competition.php", f"{REMOTE_BASE_PATH}/api/competition.php"),
    ("api/db_config.php", f"{REMOTE_BASE_PATH}/api/db_config.php"),
    ("api/db_connect.php", f"{REMOTE_BASE_PATH}/api/db_connect.php"),
    ("api/competition_schema.php", f"{REMOTE_BASE_PATH}/api/competition_schema.php"),
    ("api/live.php", f"{REMOTE_BASE_PATH}/api/live.php"),
    ("tests/kimis-claw.spec.js", f"{REMOTE_BASE_PATH}/tests/kimis-claw.spec.js"),
]


@dataclass
class DeployResult:
    """Result of a file deployment attempt"""
    local_path: Path
    remote_path: str
    success: bool
    local_size: int
    remote_size: Optional[int] = None
    error: Optional[str] = None


def get_ftp_credentials() -> Tuple[str, str, str]:
    """
    Retrieve FTP credentials from environment variables.
    Checks multiple common variable names.
    
    Returns:
        Tuple of (host, username, password)
        
    Raises:
        SystemExit: If required credentials are not found
    """
    # Check for username in order of preference
    username = None
    username_vars = ["FTP_USER", "USERNAME", "FTP_USERNAME", "USER", "FTP_LOGIN"]
    for var in username_vars:
        username = os.environ.get(var)
        if username:
            print(f"[INFO] Found username from environment variable: {var}")
            break
    
    # Check for password in order of preference
    password = None
    password_vars = ["FTP_PASS", "PASSWORD", "FTP_PASSWORD", "PASS", "FTP_PASSWD", "FTP_PWD"]
    for var in password_vars:
        password = os.environ.get(var)
        if password:
            # Don't print which var for security, just confirm found
            print(f"[INFO] Found password from environment variable: {var}")
            break
    
    # Check for host (optional, has default)
    host = os.environ.get("FTP_HOST", DEFAULT_FTP_HOST)
    if host != DEFAULT_FTP_HOST:
        print(f"[INFO] Using custom FTP host from environment: FTP_HOST")
    else:
        print(f"[INFO] Using default FTP host: {DEFAULT_FTP_HOST}")
    
    # Validate required credentials
    missing = []
    if not username:
        missing.append("username (checked: FTP_USER, USERNAME, FTP_USERNAME, USER)")
    if not password:
        missing.append("password (checked: FTP_PASS, PASSWORD, FTP_PASSWORD, PASS)")
    
    if missing:
        print("[ERROR] Missing required FTP credentials:")
        for item in missing:
            print(f"  - {item}")
        print("\nPlease set the appropriate environment variables and try again.")
        sys.exit(1)
    
    return host, username, password


def connect_ftp(host: str, username: str, password: str, max_retries: int = MAX_RETRIES) -> ftplib.FTP:
    """
    Establish FTP connection with retry logic.
    
    Args:
        host: FTP server hostname
        username: FTP username
        password: FTP password
        max_retries: Maximum number of connection attempts
        
    Returns:
        Connected FTP object
        
    Raises:
        Exception: If connection fails after all retries
    """
    for attempt in range(1, max_retries + 1):
        try:
            print(f"[INFO] Connecting to {host} (attempt {attempt}/{max_retries})...")
            ftp = ftplib.FTP(host, timeout=30)
            ftp.login(username, password)
            print(f"[SUCCESS] Connected to {host}")
            return ftp
        except Exception as e:
            print(f"[WARNING] Connection attempt {attempt} failed: {e}")
            if attempt < max_retries:
                print(f"[INFO] Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                raise Exception(f"Failed to connect after {max_retries} attempts: {e}")


def ensure_remote_directory(ftp: ftplib.FTP, remote_path: str) -> bool:
    """
    Ensure the remote directory exists, creating it if necessary.
    
    Args:
        ftp: Connected FTP object
        remote_path: Full remote file path
        
    Returns:
        True if directory exists/created successfully
    """
    # Extract directory from full path
    remote_dir = "/".join(remote_path.split("/")[:-1])
    
    if not remote_dir or remote_dir == "/":
        return True
    
    try:
        # Try to change to the directory to see if it exists
        ftp.cwd(remote_dir)
        return True
    except ftplib.error_perm:
        # Directory doesn't exist, need to create it
        # First, ensure parent directories exist recursively
        parent_dir = "/".join(remote_dir.split("/")[:-1])
        if parent_dir and parent_dir != "/":
            if not ensure_remote_directory(ftp, parent_dir + "/dummy"):
                return False
        
        # Create this directory
        try:
            dir_name = remote_dir.split("/")[-1]
            ftp.cwd("/".join(remote_dir.split("/")[:-1]) or "/")
            ftp.mkd(dir_name)
            print(f"[INFO] Created remote directory: {remote_dir}")
            return True
        except Exception as e:
            # Directory might already exist (race condition or permissions)
            print(f"[WARNING] Could not create directory {remote_dir}: {e}")
            return True  # Continue anyway, upload might still work


def get_remote_file_size(ftp: ftplib.FTP, remote_path: str) -> Optional[int]:
    """
    Get the size of a remote file.
    
    Args:
        ftp: Connected FTP object
        remote_path: Full remote file path
        
    Returns:
        File size in bytes, or None if file doesn't exist
    """
    try:
        return ftp.size(remote_path)
    except ftplib.error_perm:
        return None
    except Exception as e:
        print(f"[WARNING] Could not get size of {remote_path}: {e}")
        return None


def upload_file_with_retry(
    ftp: ftplib.FTP,
    local_path: Path,
    remote_path: str,
    max_retries: int = MAX_RETRIES
) -> DeployResult:
    """
    Upload a single file with retry logic and verification.
    
    Args:
        ftp: Connected FTP object
        local_path: Path to local file
        remote_path: Destination path on remote server
        max_retries: Maximum upload attempts
        
    Returns:
        DeployResult with success status and details
    """
    local_size = local_path.stat().st_size if local_path.exists() else 0
    
    if not local_path.exists():
        return DeployResult(
            local_path=local_path,
            remote_path=remote_path,
            success=False,
            local_size=0,
            error="Local file does not exist"
        )
    
    for attempt in range(1, max_retries + 1):
        try:
            # Ensure directory exists
            ensure_remote_directory(ftp, remote_path)
            
            # Change to the target directory
            remote_dir = "/".join(remote_path.split("/")[:-1])
            if remote_dir:
                ftp.cwd(remote_dir)
            
            remote_filename = remote_path.split("/")[-1]
            
            # Upload the file
            print(f"[INFO] Uploading {local_path.name} -> {remote_path} (attempt {attempt}/{max_retries})...")
            
            with open(local_path, 'rb') as f:
                ftp.storbinary(f"STOR {remote_filename}", f)
            
            # Verify by checking file size
            # Need to go back to root or directory for size check
            if remote_dir:
                ftp.cwd(remote_dir)
            
            remote_size = get_remote_file_size(ftp, remote_filename)
            
            if remote_size is None:
                return DeployResult(
                    local_path=local_path,
                    remote_path=remote_path,
                    success=False,
                    local_size=local_size,
                    error="Could not verify remote file size"
                )
            
            if remote_size != local_size:
                return DeployResult(
                    local_path=local_path,
                    remote_path=remote_path,
                    success=False,
                    local_size=local_size,
                    remote_size=remote_size,
                    error=f"Size mismatch: local={local_size}, remote={remote_size}"
                )
            
            return DeployResult(
                local_path=local_path,
                remote_path=remote_path,
                success=True,
                local_size=local_size,
                remote_size=remote_size
            )
            
        except Exception as e:
            error_msg = str(e)
            print(f"[WARNING] Upload attempt {attempt} failed for {local_path.name}: {error_msg}")
            
            if attempt < max_retries:
                print(f"[INFO] Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
                # Reconnect on failure
                try:
                    ftp.quit()
                except:
                    pass
                # Get credentials and reconnect
                host, username, password = get_ftp_credentials()
                ftp = connect_ftp(host, username, password, max_retries=1)
            else:
                return DeployResult(
                    local_path=local_path,
                    remote_path=remote_path,
                    success=False,
                    local_size=local_size,
                    error=f"Failed after {max_retries} attempts: {error_msg}"
                )
    
    # Should not reach here, but just in case
    return DeployResult(
        local_path=local_path,
        remote_path=remote_path,
        success=False,
        local_size=local_size,
        error="Unknown error"
    )


def print_summary(results: List[DeployResult]) -> None:
    """
    Print a formatted summary of deployment results.
    
    Args:
        results: List of DeployResult objects
    """
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]
    
    print("\n" + "=" * 70)
    print("DEPLOYMENT SUMMARY")
    print("=" * 70)
    
    print(f"\n[SUCCESS] Successfully deployed: {len(successful)}/{len(results)} files")
    
    if successful:
        print("\nDeployed files:")
        for r in successful:
            size_kb = r.local_size / 1024
            print(f"  ✓ {r.remote_path} ({size_kb:.1f} KB)")
    
    if failed:
        print(f"\n[FAILED] Failed to deploy: {len(failed)} files")
        for r in failed:
            print(f"\n  ✗ {r.remote_path}")
            print(f"    Local: {r.local_path}")
            print(f"    Error: {r.error}")
            if r.remote_size is not None:
                print(f"    Remote size: {r.remote_size} bytes (expected: {r.local_size})")
    
    print("\n" + "=" * 70)


def main() -> int:
    """
    Main deployment function.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print("=" * 70)
    print("KIMI'S CLAW - PRODUCTION DEPLOYMENT")
    print("=" * 70)
    print(f"Source: {LOCAL_BASE_PATH}")
    print(f"Target: ftps2.50webs.com{REMOTE_BASE_PATH}")
    print("=" * 70)
    print()
    
    # Check if source directory exists
    if not LOCAL_BASE_PATH.exists():
        print(f"[ERROR] Source directory does not exist: {LOCAL_BASE_PATH}")
        return 1
    
    # Get FTP credentials
    try:
        host, username, password = get_ftp_credentials()
    except SystemExit as e:
        return e.code if hasattr(e, 'code') else 1
    
    # Connect to FTP
    try:
        ftp = connect_ftp(host, username, password)
    except Exception as e:
        print(f"[ERROR] Could not connect to FTP server: {e}")
        return 1
    
    # Deploy files
    results: List[DeployResult] = []
    
    try:
        for local_rel_path, remote_path in FILES_TO_DEPLOY:
            local_path = LOCAL_BASE_PATH / local_rel_path
            result = upload_file_with_retry(ftp, local_path, remote_path)
            results.append(result)
            
            if result.success:
                print(f"[SUCCESS] {local_rel_path} deployed successfully")
            else:
                print(f"[FAILED] {local_rel_path}: {result.error}")
        
        # Print summary
        print_summary(results)
        
    finally:
        # Always close the connection
        try:
            ftp.quit()
            print("\n[INFO] FTP connection closed")
        except:
            pass
    
    # Return exit code based on success
    failed_count = len([r for r in results if not r.success])
    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
