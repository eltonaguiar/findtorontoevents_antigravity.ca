#!/usr/bin/env python3
"""
Deploy fix for findtorontoevents.ca
Uploads correct index.html and _next directory to fix asset path issues
"""
import os
import ssl
from ftplib import FTP_TLS, error_perm
from pathlib import Path


def ensure_remote_dir(ftp: FTP_TLS, remote_dir: str) -> None:
    """Ensure remote directory exists, creating it if necessary."""
    if remote_dir in ("", "/"):
        return
    parts = [p for p in remote_dir.split("/") if p]
    cur = ""
    for p in parts:
        cur = cur + "/" + p if cur else p
        try:
            ftp.mkd(cur)
        except error_perm:
            pass  # Directory already exists


def upload_file(ftp: FTP_TLS, local_path: str, remote_path: str) -> None:
    """Upload a single file to FTP server."""
    remote_dir = os.path.dirname(remote_path)
    if remote_dir:
        ensure_remote_dir(ftp, remote_dir)
    
    print(f"Uploading: {local_path} -> {remote_path}")
    with open(local_path, "rb") as f:
        ftp.storbinary(f"STOR {remote_path}", f)


def upload_directory(ftp: FTP_TLS, local_dir: str, remote_base: str) -> None:
    """Recursively upload a directory to FTP server."""
    local_path = Path(local_dir)
    for root, dirs, files in os.walk(local_dir):
        root_path = Path(root)
        rel_path = root_path.relative_to(local_path)
        
        for file in files:
            local_file = root_path / file
            if rel_path == Path("."):
                remote_file = f"{remote_base}/{file}"
            else:
                remote_file = f"{remote_base}/{rel_path}/{file}".replace("\\", "/")
            
            upload_file(ftp, str(local_file), remote_file)


def main():
    # FTP credentials
    FTP_HOST = "ftps2.50webs.com"
    FTP_USER = "ejaguiar1"
    FTP_PASS = "$a^FzN7BqKapSQMsZxD&^FeTJ"
    FTP_ROOT = "/"  # Root directory on server
    
    # Local paths (relative to workspace root)
    workspace_root = Path(__file__).parent.parent
    index_html = workspace_root / "index.html"
    next_dir = workspace_root / "_next"
    
    # Verify files exist
    if not index_html.exists():
        print(f"ERROR: {index_html} not found!")
        return 1
    
    if not next_dir.exists():
        print(f"ERROR: {next_dir} not found!")
        return 1
    
    print("Connecting to FTP server...")
    context = ssl.create_default_context()
    ftp = FTP_TLS(context=context)
    
    try:
        ftp.connect(FTP_HOST, 21, timeout=60)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.prot_p()
        print("Connected successfully!")
        
        # Upload index.html
        print("\n=== Uploading index.html ===")
        upload_file(ftp, str(index_html), "index.html")
        
        # Upload _next directory
        print("\n=== Uploading _next directory ===")
        upload_directory(ftp, str(next_dir), "_next")
        
        print("\n=== Deployment complete! ===")
        print("Please test the site at: https://findtorontoevents.ca/index.html")
        
    except Exception as e:
        print(f"ERROR: {e}")
        return 1
    finally:
        try:
            ftp.quit()
        except:
            pass
    
    return 0


if __name__ == "__main__":
    exit(main())
