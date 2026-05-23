#!/usr/bin/env python3
"""
Event Data Quality Analysis Script
Analyzes events.json for data quality issues
"""

import json
from datetime import datetime
from collections import defaultdict

def load_events(filepath):
    """Load events from JSON file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def analyze_events(events):
    """Analyze events for data quality issues"""
    issues = {
        'critical': [],
        'high': [],
        'medium': [],
        'low': []
    }

    today = datetime.now()

    # Track duplicates by title+date
    event_signatures = defaultdict(list)

    # Geographic bounds for Toronto (approximate)
    # Toronto: lat 43.6-43.8, lng -79.6 to -79.3
    toronto_bounds = {'lat_min': 43.5, 'lat_max': 44.0, 'lng_min': -79.7, 'lng_max': -79.2}

    for idx, event in enumerate(events, 1):
        event_id = event.get('id', f'unknown_{idx}')
        title = event.get('title', 'NO TITLE')

        # Check for missing/empty fields
        if not title or title.strip() == '':
            issues['high'].append({
                'type': 'Missing Title',
                'id': event_id,
                'line': idx,
                'severity': 'HIGH'
            })

        description = event.get('description', '')
        if not description or description.strip() == '':
            issues['medium'].append({
                'type': 'Empty Description',
                'id': event_id,
                'title': title[:50],
                'line': idx,
                'severity': 'MEDIUM'
            })

        # Check for null/empty images
        image = event.get('image') or event.get('imageUrl')
        if not image or image.strip() == '':
            issues['medium'].append({
                'type': 'Missing Image/Thumbnail',
                'id': event_id,
                'title': title[:50],
                'line': idx,
                'severity': 'MEDIUM'
            })
        elif image.startswith('data:image/svg'):
            issues['medium'].append({
                'type': 'Placeholder/SVG Image',
                'id': event_id,
                'title': title[:50],
                'image': image[:100],
                'line': idx,
                'severity': 'MEDIUM'
            })

        # Check for missing/empty location
        location = event.get('location', '')
        if not location or location.strip() == '':
            issues['high'].append({
                'type': 'Missing Location',
                'id': event_id,
                'title': title[:50],
                'line': idx,
                'severity': 'HIGH'
            })

        # Check for missing/empty address
        address = event.get('address', '')
        if not address or address.strip() == '':
            issues['medium'].append({
                'type': 'Missing Address',
                'id': event_id,
                'title': title[:50],
                'line': idx,
                'severity': 'MEDIUM'
            })

        # Check for empty date (but TBD events may intentionally have empty dates)
        date = event.get('date', '')
        if not date or date.strip() == '':
            # Only flag if not marked as TBD
            tags = event.get('tags', [])
            if 'TBD' not in tags:
                issues['high'].append({
                    'type': 'Missing Date (not marked as TBD)',
                    'id': event_id,
                    'title': title[:50],
                    'line': idx,
                    'severity': 'HIGH'
                })

        # Check for past events
        if date and date.strip():
            try:
                event_date = datetime.fromisoformat(date.replace('T', ' ').replace('Z', '+00:00'))
                if event_date < today:
                    # Check if status is not CANCELLED or PAST
                    status = event.get('status', 'UNKNOWN')
                    if status not in ['CANCELLED', 'PAST', 'COMPLETED']:
                        issues['medium'].append({
                            'type': 'Past Event (should be archived or status updated)',
                            'id': event_id,
                            'title': title[:50],
                            'date': date,
                            'line': idx,
                            'severity': 'MEDIUM'
                        })
            except:
                pass  # Invalid date format, skip this check

        # Check for non-Toronto coordinates (if lat/lng present)
        lat = event.get('lat') or event.get('latitude')
        lng = event.get('lng') or event.get('longitude')

        if lat and lng:
            try:
                lat_float = float(lat)
                lng_float = float(lng)
                if not (toronto_bounds['lat_min'] <= lat_float <= toronto_bounds['lat_max'] and
                        toronto_bounds['lng_min'] <= lng_float <= toronto_bounds['lng_max']):
                    issues['low'].append({
                        'type': 'Coordinates Outside Toronto GTA',
                        'id': event_id,
                        'title': title[:50],
                        'location': location,
                        'coordinates': f"{lat}, {lng}",
                        'line': idx,
                        'severity': 'LOW'
                    })
            except:
                pass

        # Check for cancelled events still showing as UPCOMING
        status = event.get('status', '')
        if status == 'CANCELLED':
            issues['low'].append({
                'type': 'Cancelled Event (should be filtered/hidden)',
                'id': event_id,
                'title': title[:50],
                'line': idx,
                'severity': 'LOW'
            })

        # Check for duplicates
        signature = f"{title}_{date}_{location}"
        event_signatures[signature].append({'id': event_id, 'title': title, 'idx': idx})

        # Check for inconsistent case variations
        snake_case_count = sum(1 for k in event.keys() if k.islower())
        camel_case_count = sum(1 for k in event.keys() if k[0].islower() and any(c.isupper() for c in k))
        if snake_case_count > 0 and camel_case_count > 0:
            # Mixed naming conventions - note this generally
            pass

    # Find duplicates
    for signature, occurrences in event_signatures.items():
        if len(occurrences) > 1:
            issues['high'].append({
                'type': f'Duplicate Event ({len(occurrences)} occurrences)',
                'description': signature[:100],
                'occurrences': occurrences,
                'severity': 'HIGH'
            })

    return issues

def generate_report(issues, total_events, output_path):
    """Generate markdown report"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('# Event Data Quality Report\n\n')
        f.write(f'**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z")}\n\n')
        f.write(f'**Total Events Analyzed:** {total_events}\n\n')
        f.write('## Summary\n\n')
        f.write(f'| Severity | Count |\n')
        f.write(f'|----------|-------|\n')
        f.write(f'| Critical | {len(issues["critical"])} |\n')
        f.write(f'| High     | {len(issues["high"])} |\n')
        f.write(f'| Medium   | {len(issues["medium"])} |\n')
        f.write(f'| Low      | {len(issues["low"])} |\n')
        f.write(f'| **Total Issues** | {sum(len(v) for v in issues.values())} |\n\n')

        # Critical Issues
        if issues['critical']:
            f.write('## 🔴 Critical Issues\n\n')
            for issue in issues['critical']:
                f.write(f"- **{issue['type']}**\n")
                f.write(f"  - ID: `{issue.get('id')}`\n")
                if 'title' in issue:
                    f.write(f"  - Title: {issue['title']}\n")
                f.write(f"  - Line: {issue.get('line')}\n")
                f.write("\n")

        # High Priority Issues
        if issues['high']:
            f.write('## 🟠 High Priority Issues\n\n')
            for issue in issues['high'][:100]:  # Limit to first 100 to avoid massive report
                f.write(f"- **{issue['type']}**\n")
                f.write(f"  - ID: `{issue.get('id')}`\n")
                if 'title' in issue:
                    f.write(f"  - Title: {issue['title']}\n")
                if 'description' in issue:
                    f.write(f"  - Details: {issue['description']}\n")
                if 'occurrences' in issue:
                    f.write(f"  - Occurrences:\n")
                    for occ in issue['occurrences']:
                        f.write(f"    - `{occ['id']}`: {occ['title'][:50]}\n")
                f.write(f"  - Line: {issue.get('line')}\n")
                f.write("\n")
            if len(issues['high']) > 100:
                f.write(f"\n*...and {len(issues['high']) - 100} more high priority issues*\n\n")

        # Medium Priority Issues
        if issues['medium']:
            f.write('## 🟡 Medium Priority Issues\n\n')
            f.write(f'Total: {len(issues["medium"])} issues. Showing first 50:\n\n')
            for issue in issues['medium'][:50]:
                f.write(f"- **{issue['type']}**\n")
                f.write(f"  - ID: `{issue.get('id')}`\n")
                if 'title' in issue:
                    f.write(f"  - Title: {issue['title']}\n")
                if 'image' in issue:
                    f.write(f"  - Image: {issue['image']}\n")
                f.write(f"  - Line: {issue.get('line')}\n")
                f.write("\n")
            if len(issues['medium']) > 50:
                f.write(f"\n*...and {len(issues['medium']) - 50} more medium priority issues*\n\n")

        # Low Priority Issues
        if issues['low']:
            f.write('## 🟢 Low Priority Issues\n\n')
            f.write(f'Total: {len(issues["low"])} issues. Showing first 50:\n\n')
            for issue in issues['low'][:50]:
                f.write(f"- **{issue['type']}**\n")
                f.write(f"  - ID: `{issue.get('id')}`\n")
                if 'title' in issue:
                    f.write(f"  - Title: {issue['title']}\n")
                if 'coordinates' in issue:
                    f.write(f"  - Coordinates: {issue['coordinates']}\n")
                f.write(f"  - Line: {issue.get('line')}\n")
                f.write("\n")
            if len(issues['low']) > 50:
                f.write(f"\n*...and {len(issues['low']) - 50} more low priority issues*\n\n")

        # Recommendations
        f.write('## Recommendations\n\n')
        f.write('### Immediate Actions (Critical/High)\n\n')
        f.write('1. Fix missing dates for non-TBD events\n')
        f.write('2. Remove or update canceled events\n')
        f.write('3. Deduplicate recurring events\n')
        f.write('4. Add missing titles\n')
        f.write('5. Add missing locations\n\n')

        f.write('### Short-term Improvements (Medium)\n\n')
        f.write('1. Add placeholder images or fetch from source\n')
        f.write('2. Add event descriptions\n')
        f.write('3. Add venue addresses\n')
        f.write('4. Archive past events older than 3 months\n')
        f.write('5. Verify and correct event dates\n\n')

        f.write('### Long-term Improvements (Low)\n\n')
        f.write('1. Filter out non-Toronto events or mark as GTA\n')
        f.write('2. Standardize event schema\n')
        f.write('3. Add data validation on import\n')
        f.write('4. Implement automatic deduplication\n')
        f.write('5. Set up monitoring for data quality\n\n')

if __name__ == '__main__':
    events = load_events('events.json')
    issues = analyze_events(events)
    generate_report(issues, len(events), 'EVENT_DATA_QUALITY_REPORT.md')
    print(f"Analysis complete! Found {sum(len(v) for v in issues.values())} issues across {len(events)} events.")
    print(f"Report saved to: EVENT_DATA_QUALITY_REPORT.md")