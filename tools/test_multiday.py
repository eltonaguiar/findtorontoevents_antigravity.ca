#!/usr/bin/env python3
"""Test multi-day detection logic in ScrapedEvent and unified scraper."""
import sys
import os
import json
sys.path.insert(0, '.')
os.environ["PYTHONIOENCODING"] = "utf-8"

from tools.scrapers.base_scraper import ScrapedEvent

passed = 0
failed = 0

def test(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  PASS: {name}")
        passed += 1
    else:
        print(f"  FAIL: {name} {detail}")
        failed += 1


print("=== ScrapedEvent Multi-Day Detection Tests ===\n")

# Test 1: Single-day event
e1 = ScrapedEvent(id='t1', title='Jazz Night', date='2026-02-15T20:00:00Z')
d1 = e1.to_dict()
test("Single-day: is_multi_day=False", d1['is_multi_day'] == False)
test("Single-day: isMultiDay=False", d1['isMultiDay'] == False)
test("Single-day: duration_category=single", d1['duration_category'] == 'single')
test("Single-day: durationCategory=single", d1['durationCategory'] == 'single')
test("Single-day: isFree alias exists", 'isFree' in d1)

# Test 2: Multi-day event (date range, 28 days)
e2 = ScrapedEvent(id='t2', title='KUUMBA Music Show', date='2026-02-01T00:00:00Z', end_date='2026-02-28T23:59:59Z')
d2 = e2.to_dict()
test("Date-range 28d: is_multi_day=True", d2['is_multi_day'] == True)
test("Date-range 28d: isMultiDay=True", d2['isMultiDay'] == True)
test("Date-range 28d: duration_category=medium", d2['duration_category'] == 'medium')
test("Date-range 28d: endDate alias exists", d2.get('endDate') == '2026-02-28T23:59:59Z')
test("Date-range 28d: end_date exists", d2.get('end_date') == '2026-02-28T23:59:59Z')

# Test 3: Multi-day by title keyword 'festival' (no end_date)
e3 = ScrapedEvent(id='t3', title='Toronto Winter Festival 2026', date='2026-02-15T10:00:00Z')
d3 = e3.to_dict()
test("Keyword 'festival': isMultiDay=True", d3['isMultiDay'] == True)
test("Keyword 'festival': is_multi_day=True", d3['is_multi_day'] == True)

# Test 4: Exhibition keyword
e4 = ScrapedEvent(id='t4', title='Sharks Exhibition', date='2026-01-15T00:00:00Z')
d4 = e4.to_dict()
test("Keyword 'exhibition': isMultiDay=True", d4['isMultiDay'] == True)

# Test 5: 'exhibit' keyword
e5 = ScrapedEvent(id='t5', title='New Art Exhibit at AGO', date='2026-02-01T00:00:00Z')
d5 = e5.to_dict()
test("Keyword 'exhibit': isMultiDay=True", d5['isMultiDay'] == True)

# Test 6: 'conference' keyword
e6 = ScrapedEvent(id='t6', title='Global AI Conference 2026', date='2026-02-15T09:00:00Z')
d6 = e6.to_dict()
test("Keyword 'conference': isMultiDay=True", d6['isMultiDay'] == True)

# Test 7: Short overnight event (NOT multi-day, only 5 hours)
e7 = ScrapedEvent(id='t7', title='DJ Night Party', date='2026-02-15T22:00:00Z', end_date='2026-02-16T03:00:00Z')
d7 = e7.to_dict()
test("Overnight 5h: isMultiDay=False", d7['isMultiDay'] == False)
test("Overnight 5h: is_multi_day=False", d7['is_multi_day'] == False)

# Test 8: Exactly 18h (IS multi-day per UI threshold)
e8 = ScrapedEvent(id='t8', title='Weekend Craft Fair', date='2026-02-15T08:00:00Z', end_date='2026-02-16T02:00:00Z')
d8 = e8.to_dict()
test("18h event: isMultiDay=True", d8['isMultiDay'] == True)

# Test 9: Short multi-day (2 days)
e9 = ScrapedEvent(id='t9', title='Weekend Brunch Pop-up', date='2026-02-15T00:00:00Z', end_date='2026-02-17T00:00:00Z')
d9 = e9.to_dict()
test("2-day: duration_category=short", d9['duration_category'] == 'short')

# Test 10: Long multi-day (>30 days)
e10 = ScrapedEvent(id='t10', title='Winter Art Show', date='2026-01-01T00:00:00Z', end_date='2026-03-31T00:00:00Z')
d10 = e10.to_dict()
test("90-day: duration_category=long", d10['duration_category'] == 'long')

# Test 11: Regular single-day event title with no keywords
e11 = ScrapedEvent(id='t11', title='Karaoke Night at The Pub', date='2026-02-15T19:00:00Z')
d11 = e11.to_dict()
test("Normal title: isMultiDay=False", d11['isMultiDay'] == False)

# Test 12: Recurring keyword detection
e12 = ScrapedEvent(id='t12', title='Weekly Board Game Night', date='2026-02-15T18:00:00Z', description='This is a recurring weekly event.')
d12 = e12.to_dict()
test("Recurring keyword: is_recurring=True", d12.get('is_recurring') == True)

print(f"\n=== Results: {passed} passed, {failed} failed ===")

# Now test normalize_multiday_fields from run_scrapers
print("\n=== normalize_multiday_fields Tests ===\n")
from tools.run_scrapers import normalize_multiday_fields

# Legacy event with only camelCase fields
legacy = {
    "title": "Art Exhibition at ROM",
    "date": "2026-02-01T00:00:00Z",
    "endDate": "2026-03-15T00:00:00Z",
    "isFree": False,
}
normalize_multiday_fields(legacy)
test("Legacy camelCase: isMultiDay=True", legacy.get('isMultiDay') == True)
test("Legacy camelCase: is_multi_day=True", legacy.get('is_multi_day') == True)
test("Legacy camelCase: end_date synced", legacy.get('end_date') == '2026-03-15T00:00:00Z')
test("Legacy camelCase: duration_category=long (42 days)", legacy.get('duration_category') == 'long')

# Legacy event with only snake_case
snake_ev = {
    "title": "Music Night",
    "date": "2026-02-15T20:00:00Z",
    "end_date": "2026-02-15T23:00:00Z",
    "is_free": True,
}
normalize_multiday_fields(snake_ev)
test("Snake-case: endDate synced", snake_ev.get('endDate') == '2026-02-15T23:00:00Z')
test("Snake-case: isFree synced", snake_ev.get('isFree') == True)
test("Snake-case: isMultiDay=False (3h)", snake_ev.get('isMultiDay') == False)

# Festival with no end_date
fest = {
    "title": "Toronto Film Festival Preview",
    "date": "2026-09-05T00:00:00Z",
}
normalize_multiday_fields(fest)
test("Festival keyword: isMultiDay=True", fest.get('isMultiDay') == True)

print(f"\n=== Final Results: {passed} passed, {failed} failed ===")
if failed > 0:
    sys.exit(1)
