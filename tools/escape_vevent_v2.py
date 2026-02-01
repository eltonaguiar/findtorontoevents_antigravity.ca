import os

def hex_escape(s):
    # Escape the second character of the string if it's alphanumeric
    if len(s) > 1 and s[1].isalnum():
        return s[0] + f'\\x{ord(s[1]):02x}' + s[2:]
    return s

patterns = [
    'BEGIN:VEVENT',
    'END:VEVENT',
    'BEGIN:VCALENDAR',
    'END:VCALENDAR',
    'SUMMARY:',
    'LOCATION:',
    'DESCRIPTION:',
    'DTSTART:',
    'DTEND:',
    'DTSTAMP:',
    'UID:'
]

file_path = r'e:\findtorontoevents.ca\problematic_chunk.js'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

new_content = content
for p in patterns:
    escaped = hex_escape(p)
    new_content = new_content.replace(p, escaped)
    print(f"Replaced {p} with {escaped}")

with open(r'e:\findtorontoevents.ca\fixed_chunk_v2.js', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("V2 Replacement complete.")
