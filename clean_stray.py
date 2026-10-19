import re, sys
path = '.worktrees/cis-vr-coding-guide/findtorontoevents.ca/CIS-VR/index.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()
# Remove stray text-shadow after body closing brace
# Pattern: } followed by optional whitespace, then ; text-shadow...
new_content = re.sub(r'}\s*;\s*text-shadow:[^;]*;', '}', content)
with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content)
print('Cleaned stray text-shadow')