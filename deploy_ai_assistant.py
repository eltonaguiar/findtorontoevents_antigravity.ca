import subprocess
import sys
from ftplib import FTP_TLS

def get_env_var(name):
    """Read a User-level environment variable via PowerShell."""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         f"[System.Environment]::GetEnvironmentVariable('{name}','User')"],
        capture_output=True, text=True
    )
    val = result.stdout.strip()
    if not val:
        print(f"ERROR: Could not read env var '{name}' (empty or not set)")
        sys.exit(1)
    return val

def main():
    local_file = r"e:\findtorontoevents_antigravity.ca\ai-assistant.js"
    remote_path = "/findtorontoevents.ca/ai-assistant.js"

    print("Reading FTP credentials from Windows User environment variables...")
    ftp_server = get_env_var("FTP_SERVER")
    ftp_user = get_env_var("FTP_USER")
    ftp_pass = get_env_var("FTP_PASS")
    print(f"  Server: {ftp_server}")
    print(f"  User:   {ftp_user}")

    print(f"\nConnecting to {ftp_server} via FTP_TLS...")
    ftps = FTP_TLS(ftp_server)
    ftps.login(ftp_user, ftp_pass)
    print("  Logged in successfully.")

    ftps.prot_p()
    print("  Data protection enabled (prot_p).")

    print(f"\nUploading {local_file} -> {remote_path} ...")
    with open(local_file, "rb") as f:
        ftps.storbinary(f"STOR {remote_path}", f)
    print("  Upload complete.")

    # Verify by checking file size on remote
    try:
        remote_size = ftps.size(remote_path)
        import os
        local_size = os.path.getsize(local_file)
        print(f"\n  Local size:  {local_size:,} bytes")
        print(f"  Remote size: {remote_size:,} bytes")
        if local_size == remote_size:
            print("  Size match confirmed!")
        else:
            print("  WARNING: Size mismatch!")
    except Exception as e:
        print(f"  Could not verify remote size: {e}")

    ftps.quit()
    print("\nDone. ai-assistant.js deployed successfully.")

if __name__ == "__main__":
    main()
