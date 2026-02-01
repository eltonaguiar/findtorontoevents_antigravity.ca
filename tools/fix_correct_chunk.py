import os
import ftplib

def fix_remote_file(subdir, filename):
    host = os.environ.get('FTP_SERVER')
    user = os.environ.get('FTP_USER')
    password = os.environ.get('FTP_PASS')
    
    local_temp = r'e:\findtorontoevents.ca\temp_to_fix.js'
    
    with ftplib.FTP(host) as ftp:
        ftp.login(user=user, passwd=password)
        ftp.cwd(subdir)
        
        # Download
        with open(local_temp, 'wb') as f:
            ftp.retrbinary(f'RETR {filename}', f.write)
        
        # Check for newlines and remove them
        with open(local_temp, 'rb') as f:
            content = f.read()
        
        original_size = len(content)
        # We want to replace literal newlines that occur within strings
        # But wait, if they are actual newlines in a JS file that is supposed to be minified, they shouldn't be there.
        # Let's just remove ALL newlines if it's supposed to be a single line chunk.
        # Actually, let's just use the 'problematic_chunk.js' (the 38924 one) which was clean.
        
        # Wait, I have 'fixed_chunk.js' already which has the escaped strings.
        # Let's just upload THAT to the correct path.
        
        clean_local = r'e:\findtorontoevents.ca\fixed_chunk.js'
        
        print(f"Uploading clean version to {subdir}/{filename}...")
        with open(clean_local, 'rb') as f:
            ftp.storbinary(f'STOR {filename}', f)
        print("Upload successful!")

if __name__ == "__main__":
    fix_remote_file('findtorontoevents.ca/_next/static/chunks', 'a2ac3a6616d60872.js')
