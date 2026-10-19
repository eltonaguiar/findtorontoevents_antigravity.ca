import re, sys, os

def add_shared_header(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if shared header already present
    if 'SERVICE NOW LEARNING — shared header' in content:
        print(f'Shared header already present in {filepath}')
        # Still we may need to update links to include all four
        # We'll replace the sn-lnav-links content
        # Find the sn-lnav block and replace its inner links
        # Pattern: <nav class="sn-lnav"[^>]*>.*?</nav>
        # We'll do a simple replacement using regex with DOTALL
        def replace_nav_links(match):
            nav_block = match.group(0)
            # Replace the inner <span class="sn-lnav-links">...</span>
            # We'll construct new links
            new_links = '''      <span class="sn-lnav-links">
        <a href="/servicenow/javascript/index.html" aria-current="page">JavaScript Reference</a>
        <a href="/servicenow/AIFeaturesOct2026/index.html">AI Features Guide</a>
        <a href="/servicenow/CIS-CSM/index.html">CIS‑CSM Study Briefing</a>
        <a href="/servicenow/CIS-VR/index.html">CIS‑VR Study Briefing</a>
      </span>'''
            # Replace the span
            # Find the span
            import re
            nav_block = re.sub(r'(<span class="sn-lnav-links">)(.*?)(</span>)', r'\1' + new_links.split('\n')[1].strip() + '\n' + new_links.split('\n')[2].strip() + '\n' + new_links.split('\n')[3].strip() + '\n      ' + r'\3', nav_block, flags=re.DOTALL)
            # Actually easier: replace entire sn-lnav with new one
            return f'''    <!-- SERVICE NOW LEARNING — shared header across the ServiceNow guide family -->
    <nav class="sn-lnav" aria-label="ServiceNow learning guides">
      <span class="sn-lnav-brand">ServiceNow<span class="sn-lnav-brand-dot">·</span>Learning</span>
      <span class="sn-lnav-links">
        <a href="/servicenow/javascript/index.html" aria-current="page">JavaScript Reference</a>
        <a href="/servicenow/AIFeaturesOct2026/index.html">AI Features Guide</a>
        <a href="/servicenow/CIS-CSM/index.html">CIS‑CSM Study Briefing</a>
        <a href="/servicenow/CIS-VR/index.html">CIS‑VR Study Briefing</a>
      </span>
    </nav>'''
        new_content = re.sub(r'<!-- SERVICE NOW LEARNING — shared header across the ServiceNow guide family -->.*?</nav>', replace_nav_links(match), content, flags=re.DOTALL)
        # This is getting messy. Let's just rewrite the whole block.
        # We'll instead replace from the comment to the closing nav.
        # We'll do a simple approach: replace the whole block with new block.
        # We'll find start and end indices.
        start = content.find('<!-- SERVICE NOW LEARNING — shared header across the ServiceNow guide family -->')
        if start == -1:
            return False
        end = content.find('</nav>', start) + len('</nav>')
        new_content = content[:start] + '''    <!-- SERVICE NOW LEARNING — shared header across the ServiceNow guide family -->
    <nav class="sn-lnav" aria-label="ServiceNow learning guides">
      <span class="sn-lnav-brand">ServiceNow<span class="sn-lnav-brand-dot">·</span>Learning</span>
      <span class="sn-lnav-links">
        <a href="/servicenow/javascript/index.html" aria-current="page">JavaScript Reference</a>
        <a href="/servicenow/AIFeaturesOct2026/index.html">AI Features Guide</a>
        <a href="/servicenow/CIS-CSM/index.html">CIS‑CSM Study Briefing</a>
        <a href="/servicenow/CIS-VR/index.html">CIS‑VR Study Briefing</a>
      </span>
    </nav>''' + content[end:]
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f'Updated shared header links in {filepath}')
        return True
    
    # Insert after <div class="page">
    # Find the opening <div class="page">
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