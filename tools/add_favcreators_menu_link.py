#!/usr/bin/env python3
"""
Add FAVCREATORS link to the nav menu on findtorontoevents.ca/index.html
1. Download current remote index.html as backup
2. Add the favcreators link to NETWORK section
3. Upload the modified index.html
"""

import os
import ssl
import re
from ftplib import FTP_TLS
from pathlib import Path
from datetime import datetime

def load_env_file():
    """Load environment variables from .env file"""
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

def get_ftp_credentials():
    """Get FTP credentials from environment variables"""
    load_env_file()
    return {
        'host': os.getenv('FTP_HOST'),
        'user': os.getenv('FTP_USER'),
        'password': os.getenv('FTP_PASS') or os.getenv('FTP_PASSWORD'),
        'port': int(os.getenv('FTP_PORT', '21'))
    }

def add_favcreators_link(content):
    """Add FAVCREATORS link after Movies & TV in the NETWORK section"""

    # The favcreators link to insert (using orange color theme)
    favcreators_link = '<a href="/favcreators/" class="w-full text-left px-4 py-3 rounded-xl flex items-center gap-3 hover:bg-orange-500/20 text-orange-200 hover:text-white transition-all border border-transparent hover:border-orange-500/30 overflow-hidden"><span class="text-lg">⭐</span> Favorite Creators</a>'

    # First, fix any existing /favcreators link to use trailing slash
    if 'href="/favcreators"' in content and 'href="/favcreators/"' not in content:
        content = content.replace('href="/favcreators"', 'href="/favcreators/"')
        print("  Fixed existing link: /favcreators -> /favcreators/")
        return content, True

    # Check if already exists with correct URL
    if '/favcreators/' in content:
        print("  FAVCREATORS link already exists with correct URL")
        return content, False

    # Find the Movies & TV link and insert after it
    # Pattern to match the Movies & TV anchor tag
    movies_pattern = r'(<a href="/MOVIESHOWS/"[^>]*>[^<]*<span[^>]*>[^<]*</span>[^<]*Movies[^<]*TV[^<]*</a>)'

    match = re.search(movies_pattern, content, re.IGNORECASE)
    if match:
        # Insert the favcreators link after Movies & TV
        insert_pos = match.end()
        modified = content[:insert_pos] + favcreators_link + content[insert_pos:]
        print("  Added FAVCREATORS link after Movies & TV")
        return modified, True

    # Alternative: Find the System Settings button and insert before it
    system_pattern = r'(<button[^>]*>[^<]*<span[^>]*>⚙️</span>[^<]*System Settings[^<]*</button>)'
    match = re.search(system_pattern, content)
    if match:
        insert_pos = match.start()
        modified = content[:insert_pos] + favcreators_link + content[insert_pos:]
        print("  Added FAVCREATORS link before System Settings")
        return modified, True

    print("  WARNING: Could not find insertion point for FAVCREATORS link")
    return content, False

def main():
    print("=" * 60)
    print("Add FAVCREATORS Menu Link")
    print("=" * 60)

    workspace_root = Path(__file__).parent.parent
    backup_dir = workspace_root / "backups" / "remote"
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Get FTP credentials
    creds = get_ftp_credentials()

    if not all([creds['host'], creds['user'], creds['password']]):
        print("ERROR: FTP credentials not found in environment variables")
        print("Required: FTP_HOST, FTP_USER, FTP_PASSWORD")
        return 1

    print(f"\nConnecting to {creds['host']}...")

    context = ssl.create_default_context()
    ftp = FTP_TLS(context=context)

    try:
        ftp.connect(creds['host'], creds['port'], timeout=60)
        ftp.login(creds['user'], creds['password'])
        ftp.prot_p()
        print(f"Connected as {creds['user']}")

        # Step 1: Download and backup current remote index.html
        print("\n[Step 1] Downloading remote index.html for backup...")
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        backup_path = backup_dir / f"index-{timestamp}.html"

        remote_content = []
        def store_line(line):
            remote_content.append(line)

        ftp.retrbinary("RETR index.html", store_line)
        content = b''.join(remote_content).decode('utf-8')

        # Save backup
        backup_path.write_text(content, encoding='utf-8')
        print(f"  Backup saved: {backup_path}")
        print(f"  Size: {len(content) / 1024:.1f} KB")

        # Step 2: Add the favcreators link
        print("\n[Step 2] Adding FAVCREATORS link to menu...")
        modified_content, changed = add_favcreators_link(content)

        if not changed:
            print("\nNo changes needed - link may already exist")
            ftp.quit()
            return 0

        # Step 3: Upload the modified index.html
        print("\n[Step 3] Uploading modified index.html...")
        from io import BytesIO
        modified_bytes = modified_content.encode('utf-8')
        ftp.storbinary("STOR index.html", BytesIO(modified_bytes))
        print(f"  Uploaded successfully ({len(modified_bytes) / 1024:.1f} KB)")

        print("\n" + "=" * 60)
        print("DEPLOYMENT SUCCESSFUL")
        print("=" * 60)
        print("\nChanges deployed:")
        print("  - FAVCREATORS link added to NETWORK section")
        print(f"  - Backup saved to: {backup_path}")
        print(f"\nView at: https://findtorontoevents.ca/favcreators/")

        ftp.quit()
        return 0

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
