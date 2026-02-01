import os

def force_patch_content(file_path):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    original_content = content
    modified = False

    # Define Replacements (Order matters? Specific to General)
    replacements = [
        # JSON Payload (Escaped)
        ('\\"/favcreators/\\"', '\\"/favcreators/#/guest\\"'),
        ('\\"/favcreators\\"', '\\"/favcreators/#/guest\\"'),
        
        # JSON Payload (Unescaped - rare but possible in some contexts)
        ('"/favcreators/"', '"/favcreators/#/guest"'),
        ('"/favcreators"', '"/favcreators/#/guest"'),
        
        # HTML Attributes
        ('href="/favcreators/"', 'href="/favcreators/#/guest"'),
        ('href="/favcreators"', 'href="/favcreators/#/guest"'),
        
        # Absolute Links
        ('href="https://findtorontoevents.ca/favcreators/"', 'href="/favcreators/#/guest"'),
        ('findtorontoevents.ca/favcreators/', 'findtorontoevents.ca/favcreators/#/guest'),
        
        # Ticket Icon? (User mentioned) - Optional fix
        ('🎟️', '💎'),
    ]

    for old, new in replacements:
        if old in content:
            content = content.replace(old, new)
            print(f"  Replaced '{old}' in {file_path}")
            modified = True

    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {file_path}")
    else:
        print(f"No changes needed for {file_path}")

def main():
    targets = [
        'index.html', 
        'page_content.html',
        'TORONTOEVENTS_ANTIGRAVITY/index.html',
        'TORONTOEVENTS_ANTIGRAVITY/TORONTOEVENTS_ANTIGRAVITY/index.html'
    ]
    
    for t in targets:
        force_patch_content(t)

if __name__ == "__main__":
    main()
