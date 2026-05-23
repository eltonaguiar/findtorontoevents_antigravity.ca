#!/usr/bin/env python3
import json
with open('battleground/data/baby_strats_dashboard.json', 'r') as f:
    data = json.load(f)

print('Total bundles:', data.get('total_bundles', 'N/A'))
print('Last updated:', data.get('last_updated', 'N/A'))

if 'sections' in data:
    print('\nSections in dashboard:')
    for i, section in enumerate(data['sections']):
        section_name = section.get('section', section.get('title', f'section_{i}'))
        print(f"  {i}. {section_name}")
        if section_name == 'BUNDLE_BABIES_TOP':
            print(f"     Description: {section.get('description', 'N/A')}")
            bundles = section.get('bundles', [])
            print(f"     Bundles in this section: {len(bundles)}")
            for b in bundles[:2]:
                print(f"       - {b.get('name', 'unknown')}")
