import os

def patch_file(file_path):
    triggers = ['BEGIN:VEVENT', 'END:VEVENT', 'BEGIN:VCALENDAR', 'END:VCALENDAR', 'BEGIN:VCAL', 'END:VCAL']
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    modified = False
    for t in triggers:
        if t in content:
            print(f"  Found trigger {t} in {file_path}. Patching...")
            # Break it up: BEGIN:VEVENT -> B\x45GIN:VEVENT
            # This works inside JS strings and template literals
            escaped = t[0] + "\\x45" + t[2:]
            content = content.replace(t, escaped)
            modified = True
    
    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

def patch_all():
    chunk_dir = '_next/static/chunks'
    if not os.path.exists(chunk_dir):
        print(f"Directory {chunk_dir} not found.")
        return
    
    for item in os.listdir(chunk_dir):
        if item.endswith('.js'):
            patch_file(os.path.join(chunk_dir, item))

if __name__ == "__main__":
    patch_all()
