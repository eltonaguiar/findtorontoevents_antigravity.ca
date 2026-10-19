import sys

filepath = '/home/eaguiar2015/findtorontoevents_antigravity.ca/TORONTOEVENTS_ANTIGRAVITY/servicenow/AIFeaturesOct2026/index.html'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the line after the scroll-progress div (we already have shared header after that)
# We want to insert skip-link after the scroll-progress div and before the shared header comment.
insert_idx = None
for i, line in enumerate(lines):
    if '<div class=\"scroll-progress\" aria-hidden=\"true\"></div>' in line:
        insert_idx = i + 1
        break
if insert_idx is None:
    print('Could not find scroll-progress div')
    sys.exit(1)

skip_link = '  <a class=\"skip-link\" href=\"#main-content\">Skip to briefing</a>\n'
# Insert
lines.insert(insert_idx, skip_link)

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Added skip-link to AIFeaturesOct2026')