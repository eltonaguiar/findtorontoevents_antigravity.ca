import re, sys

path = '/home/eaguiar2015/findtorontoevents_antigravity.ca/.worktrees/cis-vr-coding-guide/findtorontoevents.ca/CIS-VR/index.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find closing header
header_close = content.find('</header>')
if header_close == -1:
    print('No </header> found')
    sys.exit(1)
insert_point = header_close + len('</header>')

# Extract TOC ol
# Find <ol> after .toc maybe, but we can find first <ol> that is inside .toc by scanning
# Simpler: find <ol> and </ol> assuming only one ol in the file (the TOC)
ol_start = content.find('<ol>')
ol_end = content.find('</ol>') + len('</ol>')
if ol_start == -1 or ol_end == -len('</ol>'):
    print('Could not find <ol>')
    sys.exit(1)
toc_ol = content[ol_start:ol_end]

top_nav_html = f'\n  <nav class=\"top-nav\">\n    {toc_ol}\n  </nav>\n'

new_content = content[:insert_point] + top_nav_html + content[insert_point:]

with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content)
print('Inserted top nav')