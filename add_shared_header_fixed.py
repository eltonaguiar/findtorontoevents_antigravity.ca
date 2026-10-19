import re, sys, os

def add_shared_header(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if shared header already present
    marker = '<!-- SERVICE NOW LEARNING — shared header across the ServiceNow guide family -->'
    if marker in content:
        print(f'Shared header already present in {filepath}')
        # Replace the entire block with updated links
        start = content.find(marker)
        if start == -1:
            return False
        end = content.find('</nav>', start) + len('</nav>')
        new_block = '''    <!-- SERVICE NOW LEARNING — shared header across the ServiceNow guide family -->
    <nav class="sn-lnav" aria-label="ServiceNow learning guides">
      <span class="sn-lnav-brand">ServiceNow<span class="sn-lnav-brand-dot">·</span>Learning</span>
      <span class="sn-lnav-links">
        <a href="/servicenow/javascript/index.html" aria-current="page">JavaScript Reference</a>
        <a href="/servicenow/AIFeaturesOct2026/index.html">AI Features Guide</a>
        <a href="/servicenow/CIS-CSM/index.html">CIS‑CSM Study Briefing</a>
        <a href="/servicenow/CIS-VR/index.html">CIS‑VR Study Briefing</a>
      </span>
    </nav>'''
        new_content = content[:start] + new_block + content[end:]
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f'Updated shared header links in {filepath}')
        return True
    
    # Insert after <div class="page">
    pattern = re.compile(r'(<div class="page">)')
    match = pattern.search(content)
    if not match:
        print(f'Could not find <div class="page"> in {filepath}')
        return False
    insert_point = match.end()
    
    shared_header = '''    <!-- SERVICE NOW LEARNING — shared header across the ServiceNow guide family -->
    <nav class="sn-lnav" aria-label="ServiceNow learning guides">
      <span class="sn-lnav-brand">ServiceNow<span class="sn-lnav-brand-dot">·</span>Learning</span>
      <span class="sn-lnav-links">
        <a href="/servicenow/javascript/index.html" aria-current="page">JavaScript Reference</a>
        <a href="/servicenow/AIFeaturesOct2026/index.html">AI Features Guide</a>
        <a href="/servicenow/CIS-CSM/index.html">CIS‑CSM Study Briefing</a>
        <a href="/servicenow/CIS-VR/index.html">CIS‑VR Study Briefing</a>
      </span>
    </nav>
'''
    # Insert after the opening div, but before any content (maybe there is newline)
    new_content = content[:insert_point] + '\n' + shared_header + content[insert_point:]
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f'Added shared header to {filepath}')
    return True

files = [
    '/home/eaguiar2015/findtorontoevents_antigravity.ca/findtorontoevents.ca/servicenow/javascript/index.html',
    '/home/eaguiar2015/findtorontoevents_antigravity.ca/.worktrees/cis-vr-coding-guide/findtorontoevents.ca/CIS-VR/index.html',
    '/home/eaguiar2015/findtorontoevents_antigravity.ca/findtorontoevents.ca/CIS-CSM/index.html',
    '/home/eaguiar2015/findtorontoevents_antigravity.ca/TORONTOEVENTS_ANTIGRAVITY/servicenow/AIFeaturesOct2026/index.html'
]

for f in files:
    if os.path.exists(f):
        add_shared_header(f)
    else:
        print(f'File not found: {f}')