import re, sys, os

def update_toc_css(html_path):
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find <style> tag
    style_match = re.search(r'(<style[^>]*>)(.*?)(</style>)', content, re.DOTALL)
    if not style_match:
        print(f'No <style> tag found in {html_path}')
        return False
    style_open, css, style_close = style_match.groups()
    
    # Define new .toc CSS
    new_toc_css = '''.toc {
  position: sticky;
  top: 24px;
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 16px;
  max-height: calc(100vh - 80px);
  overflow-y: auto;
}
.toc h2 {
  margin: 0 0 0.65rem;
  font-size: 1rem;
  color: var(--muted);
}
.toc ol { margin: 0; padding-left: 1.3rem; }
.toc li { padding: 0.18rem 0; font-size: 0.91rem; }
.toc a { text-decoration: none; }'''
    
    # Replace existing .toc block (including any existing .toc, .toc h2, etc.)
    # We'll replace from .toc { up to next } that is not nested? Simpler: replace all occurrences of .toc {
    # but we need to replace the block until closing brace at same nesting level.
    # We'll do a regex that matches .toc { ... } with nested braces? Assuming no nested braces inside.
    # We'll replace .toc { ... } where ... does not contain { or }.
    # Safer: replace the whole .toc block we know from earlier pattern: .toc, article, ... but we'll just replace from .toc { to the next } that is at same depth.
    # Since CSS is simple, we can do:
    # Find .toc {
    # Then find matching } using a simple stack.
    def replace_toc_block(match):
        # We'll just return new_toc_css
        return new_toc_css
    
    # Pattern to find .toc {
    pattern = re.compile(r'\\.toc\\s*\\{[^}]*\\}', re.DOTALL)
    # However .toc may be part of a list like .toc, article, .course-card... We need to replace the whole rule set.
    # Instead we can replace from .toc { to the next } that is not inside another block.
    # Let's do a more robust: find '.toc {' then balance braces.
    def replace_toc_rule(css_text):
        # Find all occurrences of .toc {
        out = []
        i = 0
        while i < len(css_text):
            if css_text[i:i+4] == '.toc' and (i+4 < len(css_text) and css_text[i+4] == '{'):
                # Found start
                start = i
                # Find matching closing brace
                depth = 0
                j = i
                while j < len(css_text):
                    if css_text[j] == '{':
                        depth += 1
                    elif css_text[j] == '}':
                        depth -= 1
                        if depth == 0:
                            j += 1  # include the closing brace
                            break
                    j += 1
                # Replace this block with new_toc_css
                out.append(new_toc_css)
                i = j
            else:
                out.append(css_text[i])
                i += 1
        return ''.join(out)
    
    new_css = replace_toc_rule(css)
    
    # If no .toc found, we may need to add it.
    if '.toc' not in new_css:
        # Append before </style>
        new_css = css + '\n\n' + new_toc_css
    
    # Reassemble
    new_content = content[:style_match.start(1)] + style_open + new_css + style_close + content[style_match.end(3):]
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f'Updated TOC CSS in {html_path}')
    return True

# List of files to update
files = [
    '/home/eaguiar2015/findtorontoevents_antigravity.ca/.worktrees/cis-vr-coding-guide/findtorontoevents.ca/CIS-VR/index.html',
    '/home/eaguiar2015/findtorontoevents_antigravity.ca/findtorontoevents.ca/CIS-CSM/index.html',
    '/home/eaguiar2015/findtorontoevents_antigravity.ca/TORONTOEVENTS_ANTIGRAVITY/servicenow/AIFeaturesOct2026/index.html'
]

for f in files:
    if os.path.exists(f):
        update_toc_css(f)
    else:
        print(f'File not found: {f}')