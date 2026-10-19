import sys

filepath = '/home/eaguiar2015/findtorontoevents_antigravity.ca/TORONTOEVENTS_ANTIGRAVITY/servicenow/AIFeaturesOct2026/index.html'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find index of line containing scroll-progress div
insert_idx = None
for i, line in enumerate(lines):
    if '<div class=\"scroll-progress\" aria-hidden=\"true\"></div>' in line:
        insert_idx = i + 1
        break
if insert_idx is None:
    print('Could not find scroll-progress div')
    sys.exit(1)

shared_header = '''<!-- SERVICE NOW LEARNING — shared header across the ServiceNow guide family -->
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

# Insert lines
for i, l in enumerate(shared_header.splitlines(keepends=True)):
    lines.insert(insert_idx + i, l)

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Inserted shared header into AIFeaturesOct2026')