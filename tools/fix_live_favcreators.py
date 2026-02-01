"""
Fix favcreators URL in the live JavaScript chunk file.
Host returns 500 for /favcreators/; correct URL is /fc/#/guest.
"""
import re
import os

def fix_all_chunk_files():
    """Fix all a2ac chunk files in the repository"""
    chunk_files = []
    for root, dirs, files in os.walk('.'):
        if 'a2ac3a6616d60872.js' in files:
            chunk_files.append(os.path.join(root, 'a2ac3a6616d60872.js'))
    
    print(f"Found {len(chunk_files)} chunk files to check")
    
    for file_path in chunk_files:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='surrogateescape') as f:
                content = f.read()
            
            wrong1 = re.findall(r'href:"/favcreators/"', content)
            wrong2 = re.findall(r'href:"/favcreators/#/guest"', content)
            correct_matches = re.findall(r'href:"/fc/#/guest"', content)
            
            print(f"\n{file_path}:")
            print(f"  Wrong (href:\"/favcreators/\"): {len(wrong1)}")
            print(f"  Wrong (href:\"/favcreators/#/guest\"): {len(wrong2)}")
            print(f"  Correct (href:\"/fc/#/guest\"): {len(correct_matches)}")
            
            if wrong1 or wrong2:
                content = content.replace('href:"/favcreators/#/guest"', 'href:"/fc/#/guest"')
                content = content.replace('href:"/favcreators/"', 'href:"/fc/#/guest"')
                with open(file_path, 'w', encoding='utf-8', errors='surrogateescape') as f:
                    f.write(content)
                print(f"  ✅ Fixed to /fc/#/guest")
        except Exception as e:
            print(f"  ❌ Error processing {file_path}: {e}")

if __name__ == "__main__":
    fix_all_chunk_files()
