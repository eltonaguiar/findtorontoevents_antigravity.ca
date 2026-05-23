import json
from urllib.parse import urlparse

with open('next/events.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

events = data.get('events', data) if isinstance(data, dict) else data
total = len(events)
with_img = sum(1 for e in events if e.get('image') or e.get('imageUrl') or e.get('thumbnail'))

print(f'Total events: {total}')
print(f'Events with image: {with_img}')
print(f'Events WITHOUT image: {total - with_img}')
print(f'Image coverage: {with_img/total*100:.1f}%')

sources = {}
for e in events:
    s = e.get('source', 'unknown')
    sources.setdefault(s, {'total': 0, 'img': 0})
    sources[s]['total'] += 1
    has_img = bool(e.get('image') or e.get('imageUrl') or e.get('thumbnail'))
    sources[s]['img'] += int(has_img)

print('\nBy source:')
for k, v in sorted(sources.items()):
    pct = v['img']/v['total']*100 if v['total'] > 0 else 0
    print(f'  {k}: {v["img"]}/{v["total"]} have images ({pct:.0f}%)')

domains = {}
for e in events:
    img = e.get('image') or e.get('imageUrl') or e.get('thumbnail') or ''
    if img:
        try:
            d = urlparse(img).netloc
            domains[d] = domains.get(d, 0) + 1
        except:
            pass

print('\nImage domains:')
for d, c in sorted(domains.items(), key=lambda x: -x[1]):
    print(f'  {d}: {c}')

# Show some events without images
print('\nSample events WITHOUT images:')
no_img = [e for e in events if not (e.get('image') or e.get('imageUrl') or e.get('thumbnail'))]
for e in no_img[:10]:
    print(f'  [{e.get("source","?")}] {e.get("title","?")} - url: {e.get("url","?")}')
