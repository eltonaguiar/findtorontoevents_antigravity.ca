#!/usr/bin/env python3
"""
Automatic fixes for event data quality issues
Run this to apply fixes to events.json
"""

import json

def fix_event_data(input_file='events.json', output_file='events_fixed.json'):
    """Apply automatic fixes to event data"""

    with open(input_file, 'r', encoding='utf-8') as f:
        events = json.load(f)

    fixed_count = {
        'svg_images': 0,
        'empty_descriptions': 0,
        'missing_addresses': 0,
        'cancelled_events': 0,
        'duplicates_removed': 0
    }

    # Duplicates to remove (keep first ID)
    duplicates_to_remove = [
        '032cf2e71e547cf6330be52cdbbe1533',  # Summerlicious dup
        'c7a59e85b777b78b30b97e3eeef6755b',   # Nuit Blanche dup
    ]

    # Filter out duplicates
    original_count = len(events)
    events = [e for e in events if e.get('id') not in duplicates_to_remove]
    fixed_count['duplicates_removed'] = original_count - len(events)

    for event in events:
        # Fix 1: Replace SVG placeholder images
        if event.get('image', '').startswith('data:image/svg'):
            title = event.get('title', 'Event')[:20]
            title_encoded = title.replace(' ', '+').strip('+')
            event['image'] = f"https://placehold.co/576x240/e9d5ff/333?text={title_encoded}"
            fixed_count['svg_images'] += 1

        # Fix 2: Add default descriptions
        if not event.get('description', '').strip():
            title = event.get('title', 'this event')
            event['description'] = f"Join us for {title}. Visit the event website for full details, times, and ticket information."
            fixed_count['empty_descriptions'] += 1

        # Fix 3: Extract address from location
        if not event.get('address', '').strip() and event.get('location', '').strip():
            location = event['location']
            # Remove venue name, keep address parts
            # Format: "Venue Name, 123 Street, City"
            parts = [p.strip() for p in location.split(',')]
            # Address is typically 2nd part onwards
            if len(parts) > 1:
                event['address'] = ', '.join(parts[1:2])  # Just street address
            else:
                event['address'] = location
            fixed_count['missing_addresses'] += 1

        # Fix 4: Filter out cancelled events
        if event.get('status') == 'CANCELLED':
            event['_archived'] = True
            fixed_count['cancelled_events'] += 1

    # Save fixed data
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

    print(f"Fixed {sum(fixed_count.values())} issues:")
    print(f"   - SVG images replaced: {fixed_count['svg_images']}")
    print(f"   - Empty descriptions added: {fixed_count['empty_descriptions']}")
    print(f"   - Missing addresses extracted: {fixed_count['missing_addresses']}")
    print(f"   - Cancelled events archived: {fixed_count['cancelled_events']}")
    print(f"   - Duplicates removed: {fixed_count['duplicates_removed']}")
    print(f"Output saved to: {output_file}")

if __name__ == '__main__':
    fix_event_data()