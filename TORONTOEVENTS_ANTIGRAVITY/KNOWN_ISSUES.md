# Toronto Events - Known Issues

## Event Times
**Issue**: Eventbrite listing pages only provide dates, not times, in their JSON-LD structured data.

**Impact**: Events from Eventbrite show as "All Day" or with estimated times instead of exact start times.

**Workaround Options**:
1. Click "Tickets" button to see actual event time on Eventbrite's site
2. Scrape individual event pages (slow, not implemented yet)
3.Add time estimation heuristics based on event type (concerts = evening, etc.)

**Affected Events**: All Eventbrite events (majority of our catalog)

## Missing Events
Some events from Eventbrite's "today" page may not appear if:
- They don't have valid JSON-LD structured data
- The date cannot be parsed
- They fail quality checks (past events, incomplete data)

## Next Steps
- Add individual event page scraping for accurate times
- Add more event sources (Meetup, Facebook Events, etc.)
- Implement time estimation based on event categories
