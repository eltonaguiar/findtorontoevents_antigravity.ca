#!/usr/bin/env python3
"""Deploy with cache busting"""
import ftplib
import time

FTP_HOST = "torontoevent.net"
FTP_USER = "elton@torontoevent.net"
FTP_PASS = os.environ.get("FTPGODADDYPASS", "")

def deploy():
    print("CACHE BUST DEPLOY")
    print("=" * 60)
    
    ftp = ftplib.FTP(FTP_HOST, timeout=30)
    ftp.login(FTP_USER, FTP_PASS)
    ftp.cwd("MOVIESHOWS3")
    
    # Read local file
    with open("fte_clone/TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/index.html", "rb") as f:
        content = f.read()
    
    # Write a comment with timestamp to force file change
    content_str = content.decode('utf-8')
    timestamp = int(time.time())
    content_str = content_str.replace(
        '<title>MovieShows - Discover Movies & TV</title>',
        f'<title>MovieShows - Discover Movies & TV</title>\n    <!-- CACHE_BUST: {timestamp} -->'
    )
    
    # Save to temp
    temp_path = "/tmp/index_new.html"
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(content_str)
    
    print(f"[OK] Cache bust timestamp: {timestamp}")
    
    # Delete old file completely
    try:
        ftp.delete("index.html")
        print("[OK] Deleted old index.html")
    except:
        pass
    
    # Upload new
    with open(temp_path, "rb") as f:
        ftp.storbinary("STOR index.html", f)
    
    size = ftp.size("index.html")
    print(f"[OK] Uploaded: {size} bytes")
    ftp.quit()
    print("=" * 60)

if __name__ == "__main__":
    deploy()
