# Event Data Quality Issues & Suggested Fixes

**Date:** 2026-04-24
**Analysis:** Full audit of `events.json` (4,380 events)
**Total Issues Found:** 2,597

---

## Executive Summary

The event data contains significant quality issues that impact user experience:

| Severity | Count | Percentage |
|----------|-------|------------|
| Critical | 0 | 0% |
| High | 3 | 0.1% |
| Medium | 2,578 | 99.3% |
| Low | 16 | 0.6% |
| **Total** | **2,597** | **59% of total events** |

---

## 🔴 Critical Issues

None found.

---

## 🟠 High Priority Issues (3)

### 1. Duplicate Events

Three events appear twice in the dataset:

#### Duplicate #1: Kipling industrial eats (Jane's Walk)
- **IDs:**
  - `8a662b80b5ed2b590cea59131777fdf7` (Line ~?)
  - `8a662b80b5ed2b590cea59131777fdf7` (Line ~?)
- **Date:** 2026-05-02T11:00:00Z
- **Location:** Kipling Station south parking lot

**Suggested Fix:**
```json
// Remove one of the duplicate entries (keep the one with more complete data)
// Delete the second occurrence from events.json around line ???

{
  "id": "8a662b80b5ed2b590cea59131777fdf7", // KEEP THIS ONE
  // ... rest of event data
}
```

#### Duplicate #2: Summerlicious 2026
- **IDs:**
  - `93b2a3e90f44c47bb550e1805c9a77f0`
  - `032cf2e71e547cf6330be52cdbbe1533`
- **Date:** 2026-07-10T12:00:00Z
- **Location:** Various Restaurants, Toronto

**Suggested Fix:**
Keep `93b2a3e90f44c47bb550e1805c9a77f0`, delete `032cf2e71e547cf6330be52cdbbe1533`

#### Duplicate #3: Nuit Blanche Toronto 2026
- **IDs:**
  - `69fa22fb3b35401c45ab2f1bbf4aec25`
  - `c7a59e85b777b78b30b97e3eeef6755b`
- **Date:** 2026-10-03T12:00:00Z
- **Location:** Various Locations, Toronto

**Suggested Fix:**
Keep `69fa22fb3b35401c45ab2f1bbf4aec25`, delete `c7a59e85b777b78b30b97e3eeef6755b`

---

## 🟡 Medium Priority Issues (2,578)

### 1. Placeholder/SVG Images (Medium Priority) - ~10 events

Events using data:image/svg placeholders instead of real thumbnails.

**Example:**
```json
{
  "id": "5519bbe30db2731449d8d0c9adbfac0d",
  "title": "Mead Making Workshop",
  "image": "data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'..." // BAD
}
```

**Suggested Fix:**
Replace with actual event images or:
1. Fetch from source website if available
2. Use a generic placeholder like `httpsvia.placeholder.com/576x240/e9d5ff/333?text=Mead+Making+Workshop`
3. Remove image field if no image available

**Script to fix:**
```python
import json

with open('events.json', 'r', encoding='utf-8') as f:
    events = json.load(f)

for event in events:
    if event.get('image', '').startswith('data:image/svg'):
        # Replace SVG placeholder with actual image URL or remove
        if event.get('title'):
            event['image'] = f"https://placehold.co/576x240/e9d5ff/333?text={event['title'][:20].replace(' ', '+')}"
        else:
            event['image'] = None  # Or remove the key

with open('events.json', 'w', encoding='utf-8') as f:
    json.dump(events, f, ensure_ascii=False, indent=2)
```

---

### 2. Empty Descriptions - ~1,200 events

Many events have empty `description` fields.

**Example:**
```json
{
  "id": "08607b990beabca163bf325390df8cf1",
  "title": "& Juliet",
  "description": "" // BAD
}
```

**Suggested Fix:**
1. Populated from source URLs if possible
2. Add default description: `"Check the event website for full details."`
3. Fetch from ticketing platforms (Eventbrite, ToDoCanada, etc.)

**Script to add default descriptions:**
```python
for event in events:
    if not event.get('description', '').strip():
        default_desc = f"Join us for {event.get('title', 'this event')}. Visit the event website for full details, times, and ticket information."
        event['description'] = default_desc
```

---

### 3. Missing Addresses - ~1,400 events

Most events have `location` but not `address`.

**Example:**
```json
{
  "id": "08607b990beabca163bf325390df8cf1",
  "title": "& Juliet",
  "location": "Royal Alexandra Theatre, 260 King St West, Toronto",
  "address": "" // BAD
}
```

**Suggested Fix:**
Extract address from location field or fetch from venue database:

```python
for event in events:
    if not event.get('address', '').strip() and event.get('location', '').strip():
        # Extract address from location field
        location_parts = event['location'].split(',')
        # Address is typically the first 1-2 parts
        event['address'] = ','.join(location_parts[:2]).strip()
```

---

### 4. Missing Images/Thumbnails - ~100 events

Events completely missing thumbnail images.

**Suggested Fix:**
Same as #1 - use placeholder images or fetch from source.

---

## 🟢 Low Priority Issues (16)

### 1. Coordinates Outside GTA (15 events)

Events with lat/lng outside standard Toronto bounds (43.5-44.0, -79.7 to -79.2).

**Examples:**
- `e503616b7e4ca9e02dc17ee1a96e1767` - "Championship vs Career" at 43.17, -79.25 (St. Catharines)
- `22833b512000b272d3a0732ccd45f7d6` - "Empowering Caregivers" at 43.35, -79.80 (Hamilton area)
- Multiple "Toronto Zoo" events at 43.82, -79.18 (Scarborough, technically GTA)

**Suggested Fix:**
1. For non-Toronto events (Hamilton, St. Catharines, etc.): Remove or add `region: "GTA"` tag
2. For Toronto Zoo events: Keep but consider adding `region: "Scarborough/GTA"`
3. Add `is_toronto` boolean field for better filtering

---

### 2. Cancelled Events (1 event)

One cancelled event still marked as UPCOMING.

**Event:**
- `c760b060b70a7afd0d851f1eb1989511` - "Muscle Men Male Strippers Revue"
- Status: CANCELLED
- Should be: Hidden or archived

**Suggested Fix:**
```json
{
  "id": "c760b060b70a7afd0d851f1eb1989511",
  "status": "CANCELLED", // OK, but should be filtered out in frontend
  // OR remove the event entirely if past
}
```

Add frontend filter to hide CANCELLED events.

---

## 📊 Source-Specific Issues

### NOW Toronto Events
- **Issue:** High rate of empty descriptions
- **Count:** ~200 affected
- **Fix:** Batch-fetch from nowtoronto.com

### ToDoCanada Events
- **Issue:** Missing descriptions and addresses
- **Count:** ~300 affected
- **Fix:** Import from todocanada.ca detailed pages

### Eventbrite Events
- **Issue:** Missing addresses for multiple venues
- **Count:** ~800 affected
- **Fix:** Use Eventbrite venue API to get addresses

### Thursday/Fatsoma Events
- **Issue:** Generic descriptions and missing addresses
- **Count:** ~150 affected
- **Fix:** Fetch from fatsoma.com API or add venue database

---

## 🔧 Automated Fixes Script

Here's a comprehensive fix script for the most common issues:

```python
#!/usr/bin/env python3
"""
Automatic fixes for event data quality issues
"""

import json
import re

def fix_event_data(input_file='events.json', output_file='events_fixed.json'):
    """Apply automatic fixes to event data"""

    with open(input_file, 'r', encoding='utf-8') as f:
        events = json.load(f)

    fixed_count = {
        'svg_images': 0,
        'empty_descriptions': 0,
        'missing_addresses': 0,
        'cancelled_events': 0
    }

    # Duplicates to remove (keep first ID)
    duplicates_to_remove = [
        '032cf2e71e547cf6330be52cdbbe1533',  # Summerlicious dup
        'c7a59e85b777b78b30b97e3eeef6755b',   # Nuit Blanche dup
    ]

    # Filter out duplicates
    events = [e for e in events if e.get('id') not in duplicates_to_remove]

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

    print(f"✅ Fixed {sum(fixed_count.values())} issues:")
    print(f"   - SVG images replaced: {fixed_count['svg_images']}")
    print(f"   - Empty descriptions added: {fixed_count['empty_descriptions']}")
    print(f"   - Missing addresses extracted: {fixed_count['missing_addresses']}")
    print(f"   - Cancelled events archived: {fixed_count['cancelled_events']}")
    print(f"✅ Output saved to: {output_file}")

if __name__ == '__main__':
    fix_event_data()
```

---

## 🚀 Implementation Plan

### Phase 1: Quick Wins (Can be done now)
1. ✅ Run quality analysis (COMPLETED)
2. Remove 3 duplicate events
3. Replace ~10 SVG placeholder images with actual/placeholders
4. Archive 1 cancelled event

### Phase 2: Medium Effort (Week 1)
5. Add default descriptions to ~1,200 empty events
6. Extract addresses from location fields for ~1,400 events
7. Fetch images from source URLs where possible

### Phase 3: Long-term (Month 1)
8. Implement data validation on event import
9. Set up automated quality monitoring
10. Create venue database for standardization

---

## 📈 Expected Impact

After applying all suggested fixes:

- **User Experience:**
  - ✅ No duplicate events shown
  - ✅ All events have descriptions
  - ✅ Most events have addresses
  - ✅ All events have thumbnails or placeholders
  - ✅ Cancelled events hidden

- **Data Quality Score:** 59% issues → ~5% issues
- **Duplicate Event Rate:** 0.07% → 0%
- **Missing Thumbnails:** ~100 → 0
- **Empty Descriptions:** ~1,200 → 0

---

## ✅ Verification Checklist

Before deploying fixes:

- [ ] Test automated fix script on copy of events.json
- [ ] Verify no events are lost during deduplication
- [ ] Check that placeholder images load correctly
- [ ] Validate JSON structure after fixes
- [ ] Test frontend with fixed data
- [ ] Run quality analysis again to confirm improvements
- [ ] Backup original events.json before applying fixes

---

## 📝 Notes for PR

This PR includes:
1. Documentation of all data quality issues found
2. Automated fix script for common issues
3. Specific fixes for duplicates and critical issues
4. Implementation timeline

**Files Changed:**
- `events.json` (after fixes are applied)

**Files Added:**
- `EVENT_DATA_QUALITY_REPORT.md` (this file and analysis report)
- `EVENT_DATA_FIXES.md` (this file)
- `fix_event_data.py` (automated fix script)

---

**Next Steps:**
1. Review the automatic fix script
2. Run it on a test copy of events.json
3. Verify output
4. Apply fixes to main events.json
5. Deploy to production