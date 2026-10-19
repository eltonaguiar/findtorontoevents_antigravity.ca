import re, sys
path = '.worktrees/cis-vr-coding-guide/findtorontoevents.ca/CIS-VR/index.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()
# Find body block and insert text-shadow before closing brace
def add_shadow_inside(match):
    block = match.group(0)
    # Insert before the final '}'
    if block.strip().endswith('}'):
        # Insert before last '}'
        pos = block.rfind('}')
        # Insert text-shadow with appropriate spacing
        new_block = block[:pos] + '  text-shadow: 0 0 2px rgba(0,0,0,0.6);\n' + block[pos:]
        return new_block
    return block
body_pattern = r'body\s*\{[^}]+\}'
new_content = re.sub(body_pattern, add_shadow_inside, content, flags=re.DOTALL)
with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content)
print('Fixed text-shadow insertion')