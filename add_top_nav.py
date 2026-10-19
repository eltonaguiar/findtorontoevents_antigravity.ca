import re, sys, os

def add_top_nav(html_path):
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find </header> tag (closing of hero header)
    # Use regex to find </header> after <header class=\"hero\"> maybe.
    # We'll insert after the first </header>.
    header_close = content.find('</header>')
    if header_close == -1:
        print(f'No </header> found in {html_path}')
        return False
    insert_point = header_close + len('</header>')
    
    # Extract TOC ol from .toc
    # Find <ol> inside .toc
    # We'll locate .toc { ... } but easier: find '<ol>' after '.toc' maybe.
    # We'll find the first '<ol>' after '.toc' that is before next '}'? We'll just find the first '<ol>' after '.toc' and capture until '</ol>'.
    # Simple approach: find '<ol>' and '</ol>' assuming only one ol in toc.
    ol_start = content.find('<ol>')
    ol_end = content.find('</ol>') + len('</ol>')
    if ol_start == -1 or ol_end == -len('</ol>'):
        print(f'Could not find <ol> in {html_path}')
        return False
    toc_ol = content[ol_start:ol_end]
    
    # Build top nav HTML
    top_nav_html = f'\n  <nav class=\"top-nav\">\n    {toc_ol}\n  </nav>\n'
    
    # Insert after header
    new_content = content[:insert_point] + top_nav_html + content[insert_point:]
    
    # Now add CSS for .top-nav before </style>
    style_match = re.search(r'(<style[^>]*>)(.*?)(</style>)', content, re.DOTALL)
    if not style_match:
        print(f'No <style> tag found in {html_path}')
        return False
    style_open, css, style_close = style_match.groups()
    
    top_nav_css = '''.top-nav {
  position: sticky;
  top: 0;
  background: var(--card);
  border-bottom: 1px solid var(--line);
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  z-index: 1000;
}
.top-nav a {
  text-decoration: none;
  color: var(--ink);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
}
.top-nav a:hover {
  background: rgba(255,255,255,0.1);
}'''
    
    # Insert before </style>
    new_css = css + '\n\n' + top_nav_css
    new_content = content[:style_match.start(1)] + style_open + new_css + style_close + content[style_match.end(3):]
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f'Added top nav to {html_path}')
    return True

files = [
    '/home/eaguiar2015/findtorontoevents_antigravity.ca/.worktrees/cis-vr-coding-guide/findtorontoevents.ca/CIS-VR/index.html',
    '/home/eaguiar2015/findtorontoevents_antigravity.ca/findtorontoevents.ca/CIS-CSM/index.html',
    '/home/eaguiar2015/findtorontoevents_antigravity.ca/TORONTOEVENTS_ANTIGRAVITY/servicenow/AIFeaturesOct2026/index.html'
]

for f in files:
    if os.path.exists(f):
        add_top_nav(f)
    else:
        print(f'File not found: {f}')