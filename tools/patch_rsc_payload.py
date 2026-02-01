import os

def patch_rsc_payload(file_path):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    modified = False
    new_lines = []
    
    for line in lines:
        if 'self.__next_f.push' in line:
            # It's a payload line. We need to replace hidden JSON strings.
            # The structure is usually JSON inside a string array inside the push.
            # We target the escaped strings.
            
            # 1. Target: \"/favcreators/\" -> \"/favcreators/#/guest\"
            # Note: In the file, quotes are already escaped as \" inside the string?
            # Or double escaped?
            # Let's try simple string replacement on the line first.
            
            original_line = line
            
            # Simple Replace (No Trailing Slash)
            # Replaces \"/favcreators\" with \"/favcreators/#/guest\"
            # Should capture quoted properties.
            if '\\"/favcreators\\"' in line:
                line = line.replace('\\"/favcreators\\"', '\\"/favcreators/#/guest\\"')
            
            # Trailing Slash
            if '\\"/favcreators/\\"' in line:
                line = line.replace('\\"/favcreators/\\"', '\\"/favcreators/#/guest\\"')

            # Absolute URL
            if 'findtorontoevents.ca/favcreators/' in line:
                 line = line.replace('findtorontoevents.ca/favcreators/', 'findtorontoevents.ca/favcreators/#/guest')
                 # Also check escaped forward slashes? JSON logic varies.
                 # Usually forward slash is not escaped in standard JSON but can be.
            
            if line != original_line:
                print(f"  Patched RSC Payload in {file_path}")
                modified = True
        
        new_lines.append(line)

    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
    else:
        print(f"  No RSC Payload match found in {file_path}")

def main():
    targets = ['index.html', 'page_content.html']
    for t in targets:
        patch_rsc_payload(t)

if __name__ == "__main__":
    main()
