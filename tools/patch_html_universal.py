import os
import re

def update_html_content(content, file_path):
    modified = False
    
    # 1. Fix Sidebar Link (Basic Replace) - host returns 500 for /favcreators/; use /fc/#/guest
    if 'href="/favcreators/"' in content or 'href="/favcreators/#/guest"' in content:
        content = content.replace('href="/favcreators/#/guest"', 'href="/fc/#/guest"')
        content = content.replace('href="/favcreators/"', 'href="/fc/#/guest"')
        modified = True
        print(f"  Fixed Sidebar Link (Relative) in {file_path}")
        
    if 'href="https://findtorontoevents.ca/favcreators/"' in content or 'href="https://findtorontoevents.ca/favcreators/#/guest"' in content:
        content = content.replace('href="https://findtorontoevents.ca/favcreators/#/guest"', 'href="/fc/#/guest"')
        content = content.replace('href="https://findtorontoevents.ca/favcreators/"', 'href="/fc/#/guest"')
        modified = True
        print(f"  Fixed Sidebar Link (Absolute) in {file_path}")


    # 2. Add 'Live Status' Link in Sidebar
    # Look for the FavCreators link we just fixed
    fav_link_pattern = r'(<a href="/fc/#/guest".*?</a>|<a href="/favcreators/#/guest".*?</a>)'
    if 'are your favorite creators live?' not in content:
        # Define the new link HTML
        # We need to guess the class style from the existing link
        # We capture the class from the found pattern
        match = re.search(r'class="([^"]+)"', content)
        if match:
             # This is risky if we capture 'body' class.
             # Better: Find the FavLink and copy its class.
             pass
        
        # We use a regex sub to append.
        # Find the FavCreators link.
        # Add the new link after it.
        
        new_link = (
            '<a href="/fc/#/guest" '
            'class="w-full text-left px-4 py-3 rounded-xl flex items-center gap-3 hover:bg-pink-500/20 text-pink-200 hover:text-white transition-all border border-transparent hover:border-pink-500/30 overflow-hidden">'
            '<span class="text-lg">🔴</span> Are they live?</a>'
        )
        # Note: I am hardcoding classes similar to the ones in grep output (Tailwind).
        # But best to copy from the existing link match.
        
        def insert_live_link(m):
            original = m.group(1)
            # Try to extract class from original
            class_match = re.search(r'class="([^"]+)"', original)
            link_class = class_match.group(1) if class_match else ""
            
            # Construct strict new link
            to_insert = f'<a href="/fc/#/guest" class="{link_class}"><span class="text-lg">🔴</span> are your favorite creators live?</a>'
            return original + to_insert

        content, count = re.subn(fav_link_pattern, insert_live_link, content)
        if count > 0:
            modified = True
            print(f"  Added Live Link in {file_path}")

    # 3. Add Hero Button (FavCreators Promo)
    if 'favcreators-promo' not in content and 'movieshows-promo' in content:
        # Regex to find the Container of Movies Promo
        # Pattern: <div class="max-w-7xl mx-auto px-4"> ... <div class="...movieshows-promo">...</div> ... </div>
        # We look for the 'movieshows-promo' div, and then try to find its parent 'max-w-7xl'.
        
        # Strategy: Find the movieshows-promo DIV.
        # Then Find the wrapping div around it.
        # Since HTML structure is reliable (React generated):
        # <div class="max-w-7xl mx-auto px-4"><div class="jsx-... movieshows-promo">...</div></div>
        
        promo_pattern = r'(<div class="max-w-7xl mx-auto px-4">\s*<div class="[^"]*movieshows-promo".*?</div>\s*</div>)'
        
        match = re.search(promo_pattern, content, re.DOTALL)
        if match:
            movies_block = match.group(1)
            
            # Create FavCreators Block by modification
            fav_block = movies_block.replace('movieshows-promo', 'favcreators-promo')
            
            # Replace Icon: 🎬 to 💎
            fav_block = fav_block.replace('🎬', '💎')
            # Replace Colors (Gradient)
            # movies uses: from-amber-500 to-orange-600
            fav_block = re.sub(r'from-[a-z]+-\d+', 'from-pink-500', fav_block)
            fav_block = re.sub(r'to-[a-z]+-\d+', 'to-rose-600', fav_block)
            
            # Replace Text
            fav_block = fav_block.replace('Movies &amp; TV', 'Fav Creators')
            fav_block = fav_block.replace('Trailers, Now Playing Toronto', 'Live Status &amp; More')
            
            # Replace Link
            fav_block = re.sub(r'href="[^"]+"', 'href="/fc/#/guest"', fav_block)
            
            # Insert BEFORE the Movies Block (so it's higher up? Or After?)
            # usage: windows(top) -> ? -> movies(bottom).
            # I'll put it Before Movies.
            
            new_content = content.replace(movies_block, fav_block + movies_block)
            content = new_content
            modified = True
            print(f"  Added Hero Button in {file_path}")
        else:
            print(f"  Could not match Movies Promo block in {file_path} (Regex mismatch)")

    return content, modified

def main():
    root_dir = 'e:/findtorontoevents_antigravity.ca'
    # Files to explicitly target first
    priority_files = [
        'index.html',
        'page_content.html',
        'TORONTOEVENTS_ANTIGRAVITY/index.html',
        'TORONTOEVENTS_ANTIGRAVITY/TORONTOEVENTS_ANTIGRAVITY/index.html'
    ]
    
    # Process priority files first
    for rel_path in priority_files:
        full_path = os.path.join(root_dir, rel_path)
        if os.path.exists(full_path):
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            new_content, modified = update_html_content(content, full_path)
            
            if modified:
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Updated {rel_path}")
    
    # Scan all HTMLs (skip node_modules etc if needed)
    for root, dirs, files in os.walk(root_dir):
        if 'node_modules' in root or '.git' in root or 'backups' in root:
            continue
        for name in files:
            if name.endswith('.html'):
                if name in output_files_checked: continue # Skip already processed
                full_path = os.path.join(root, name)
                # ... same process ...
                # (Simplifying for this script run: I just rely on priority files + maybe top level)
                pass

output_files_checked = []
if __name__ == '__main__':
    main()
