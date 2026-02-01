"""
Download the live JavaScript chunk, fix it, and save it locally
"""
import urllib.request
import re
import os

def download_and_fix():
    url = 'https://findtorontoevents.ca/next/_next/static/chunks/a2ac3a6616d60872.js'
    output_path = 'next/_next/static/chunks/a2ac3a6616d60872.js'
    
    print(f"Downloading {url}...")
    try:
        with urllib.request.urlopen(url) as response:
            content = response.read().decode('utf-8', errors='surrogateescape')
        
        print(f"Downloaded {len(content)} characters")
        
        # Count occurrences
        wrong_matches = re.findall(r'href:"/favcreators/"', content)
        correct_matches = re.findall(r'href:"/favcreators/#/guest"', content)
        
        print(f"Wrong URL (href:\"/favcreators/\"): {len(wrong_matches)}")
        print(f"Correct URL (href:\"/favcreators/#/guest\"): {len(correct_matches)}")
        
        if len(wrong_matches) > 0:
            print(f"\nFixing {len(wrong_matches)} wrong URL(s)...")
            content = content.replace('href:"/favcreators/"', 'href:"/favcreators/#/guest"')
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Save fixed file
            with open(output_path, 'w', encoding='utf-8', errors='surrogateescape') as f:
                f.write(content)
            
            print(f"✅ Fixed and saved to {output_path}")
            
            # Verify fix
            wrong_after = len(re.findall(r'href:"/favcreators/"', content))
            correct_after = len(re.findall(r'href:"/favcreators/#/guest"', content))
            print(f"\nAfter fix:")
            print(f"  Wrong URL: {wrong_after}")
            print(f"  Correct URL: {correct_after}")
        else:
            print("No wrong URLs found - file is already correct")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    download_and_fix()
