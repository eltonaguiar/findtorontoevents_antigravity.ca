"""
Test if JS files are accessible directly via FTP path
"""
import os
import ftplib
import urllib.request

def test():
    host = os.environ.get('FTP_SERVER')
    user = os.environ.get('FTP_USER')
    password = os.environ.get('FTP_PASS')
    
    # Test direct file access via different paths
    test_paths = [
        '/_next/static/chunks/a2ac3a6616d60872.js',
        '/next/_next/static/chunks/a2ac3a6616d60872.js',
        'https://findtorontoevents.ca/_next/static/chunks/a2ac3a6616d60872.js',
        'https://findtorontoevents.ca/next/_next/static/chunks/a2ac3a6616d60872.js',
    ]
    
    print("Testing direct file access...\n")
    
    # Test via FTP
    try:
        with ftplib.FTP(host) as ftp:
            ftp.login(user=user, passwd=password)
            for path in ['_next/static/chunks/a2ac3a6616d60872.js', 'next/_next/static/chunks/a2ac3a6616d60872.js']:
                try:
                    ftp.cwd('/')
                    for part in path.split('/')[:-1]:
                        if part:
                            ftp.cwd(part)
                    size = ftp.size(path.split('/')[-1])
                    print(f"OK: FTP access to {path}: {size} bytes")
                except Exception as e:
                    print(f"ERROR: FTP access to {path}: {e}")
    except Exception as e:
        print(f"ERROR: FTP connection: {e}")
    
    print("\nTesting HTTP access...")
    for url in test_paths[2:]:
        try:
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0')
            with urllib.request.urlopen(req, timeout=10) as r:
                content = r.read().decode('utf-8', errors='ignore')[:100]
                if content.startswith('(globalThis'):
                    print(f"OK: {url} - Valid JavaScript")
                elif '<' in content:
                    print(f"ERROR: {url} - Returns HTML: {content[:100]}")
                else:
                    print(f"WARN: {url} - Unknown: {content[:100]}")
        except Exception as e:
            print(f"ERROR: {url} - {e}")

if __name__ == "__main__":
    test()
