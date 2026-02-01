import os

def patch_js_safe():
    # Targets for the main chunk
    targets = [
        'next/_next/static/chunks/a2ac3a6616d60872.js',
        '_next/static/chunks/a2ac3a6616d60872.js'
    ]
    
    for file_path in targets:
        if not os.path.exists(file_path):
            print(f"Skipping {file_path}")
            continue
            
        print(f"Patching {file_path}")
        with open(file_path, 'r', encoding='utf-8', errors='surrogateescape') as f:
            content = f.read()

        # 1. Update text for System Settings
        # Original: " System Settings"
        # New: " Event System Settings"
        # We replace the text string literal in the JS
        content = content.replace('" System Settings"', '" Event System Settings"')

        # 2. Update text for Windows Boot Fixer
        # Original: "Windows Fixer"
        # New: "Windows Boot Fixer" (and we can try to sneak in the tooltip if possible, but keeping it simple first)
        content = content.replace('"Windows Fixer"', '"Windows Boot Fixer"')

        # 3. Swap "Find a movie" with "FAVCREATORS" information
        # We find the specific link configuration and replace the essential parts
        # If we can't find the exact struct, we replace the label only
        content = content.replace('" Find a movie"', '" FAVCREATORS"')
        content = content.replace('href:"/findamovie/"', 'href:"/favcreators/"')
        # Note: The emoji might be separate in a span, but swapping the Label text is the critical part

        # 4. Hide original FAVCREATOR link if it duplicates
        # content = content.replace('href:"/FAVCREATOR"', 'href:"/FAVCREATOR",style:{display:"none"}')
        # Actually, let's just leave it for now to avoid syntax errors if the structure is tight.

        with open(file_path, 'w', encoding='utf-8', errors='surrogateescape') as f:
            f.write(content)
        print("Done.")

if __name__ == "__main__":
    patch_js_safe()
