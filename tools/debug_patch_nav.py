import re
path = 'next/_next/static/chunks/a2ac3a6616d60872.js'
with open(path, 'r', encoding='utf-8', errors='replace') as f:
    c = f.read()
has_fav = '" FAVCREATORS"]' in c
has_details = '(0,t.jsxs)("details",{open:!0,className:"group/nav-section"' in c
print('has FAVCREATORS:', has_fav)
print('has details:', has_details)
print('8a runs (flat):', has_fav and not has_details)
mental_health_re = re.compile(
    r'(" Windows (?:Boot )?Fixer"\]\}\)),((\(0,t\.jsxs\)\("a",\{href:"/MENTALHEALTHRESOURCES/".*?" Mental Health Resources"\]\}\),)),',
    re.DOTALL,
)
mh = mental_health_re.search(c)
print('mental_health_re matches:', mh is not None)
fav_then_2xko_re = re.compile(
    r'(" FAVCREATORS"\]\}\)),\s*\((0,t\.jsxs\)\("a",\{href:"/2xko",)',
)
fav = fav_then_2xko_re.search(c)
print('fav_then_2xko_re matches:', fav is not None)
idx = c.find('" FAVCREATORS"]}),')
print('FAVCREATORS]), at:', idx)
if idx >= 0:
    snippet = c[idx:idx+150]
    print('snippet:', repr(snippet))
# Find Windows Fixer and what follows
idx2 = c.find('" Windows Fixer"]')
print('Windows Fixer at:', idx2)
if idx2 >= 0:
    snippet2 = c[idx2:idx2+400].encode('utf-8', errors='replace').decode('ascii', errors='replace')
    print('after Windows Fixer:', repr(snippet2))
