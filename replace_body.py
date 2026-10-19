import re, sys
path = '.worktrees/cis-vr-coding-guide/findtorontoevents.ca/CIS-VR/index.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()
# Replace the whole body block with a corrected version
new_body = '''body {
      margin: 0;
      color: var(--ink);
      background:
        radial-gradient(900px 500px at 15% -10%, rgba(81,199,186,0.15), transparent 60%),
        radial-gradient(900px 600px at 90% 0%, rgba(122,162,255,0.15), transparent 60%),
        var(--paper);
      line-height: 1.65;
      text-shadow: 0 0 2px rgba(0,0,0,0.6);
    }'''
# Use regex to replace body block
pattern = r'body\s*\{[^}]+\}'
new_content = re.sub(pattern, new_body, content, flags=re.DOTALL)
with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content)
print('Replaced body block')