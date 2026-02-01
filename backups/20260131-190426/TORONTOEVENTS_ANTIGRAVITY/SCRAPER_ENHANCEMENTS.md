# Event Scraper Enhancement Summary

## Date: January 26, 2026

### New Event Sources Added

1. **Thursday App** (`source-thursday.ts`)
   - URL: https://events.getthursday.com/toronto/
   - Scrapes singles events from Thursday dating app
   - Automatically categorized as Dating events

2. **Toronto Dating Hub** (`source-torontodatinghub.ts`)
   - URL: https://www.torontodatinghub.com/events
   - Scrapes speed dating and singles events
   - Categories: Dating, Speed Dating

3. **Waterworks Food Hall** (`source-waterworks.ts`)
   - URL: https://www.waterworksfoodhall.com/whats-on
   - Scrapes community events and workshops
   - Location: Waterworks Food Hall, Toronto

4. **blogTO** (`source-blogto.ts`)
   - URL: https://www.blogto.com/events/
   - Scrapes general Toronto events
   - Wide variety of categories

5. **Narcity** (`source-narcity.ts`)
   - URL: https://www.narcity.com/tag/toronto-events
   - Scrapes Toronto event articles
   - General event coverage

### Existing Sources Enhanced

1. **Eventbrite** (`source-eventbrite.ts`)
   - ✅ Added Mohan Matchmaking organizer (o/mohan-matchmaking-63764588373/)
   - Now scrapes all Mohan Matchmaking events from Toronto/GTA

2. **Fatsoma** (`source-fatsoma.ts`)
   - Already scraping Thursday events via thursday-toronto profile
   - No changes needed

### New Features

#### 1. Location-Based Filtering ("Events Near Me")

**Backend:**
- Added geolocation utilities (`src/lib/geolocation.ts`):
  - `calculateDistance()` - Haversine formula for distance calculation
  - `geocodePostalCode()` - Convert Canadian postal codes to coordinates
  - `geocodeAddress()` - Convert addresses to coordinates
  - `getBrowserLocation()` - Get user's browser geolocation

**Frontend:**
- Updated `SettingsContext.tsx` with new settings:
  - `enableLocationFilter`: Toggle location filtering on/off
  - `userLatitude` / `userLongitude`: User's coordinates
  - `maxDistanceKm`: Maximum distance radius (1-50km)
  - `locationSource`: 'browser' | 'postal-code' | 'address'

- Updated `SettingsManager.tsx` with new UI:
  - Toggle to enable/disable location filtering
  - Three location input methods:
    1. **Browser**: Use browser's geolocation API
    2. **Postal Code**: Enter Canadian postal code (e.g., M5V 3A8)
    3. **Address**: Enter full address
  - Distance slider (1-50km radius)
  - Location status indicator

**How It Works:**
1. User enables "Events Near Me" in settings
2. User chooses location method (browser/postal/address)
3. System geocodes the location to lat/lng coordinates
4. Events are filtered by distance from user's location
5. Only events within the specified radius are shown

#### 2. Event Consolidation

- Added `consolidateEvents()` function to `utils.ts`
- Deduplicates events with similar titles on the same day
- Keeps the version with the most complete information
- Scoring based on:
  - Description length
  - Image availability
  - Geolocation data
  - Price information

### Files Created

1. `src/lib/scraper/source-thursday.ts`
2. `src/lib/scraper/source-torontodatinghub.ts`
3. `src/lib/scraper/source-waterworks.ts`
4. `src/lib/scraper/source-blogto.ts`
5. `src/lib/scraper/source-narcity.ts`
6. `src/lib/geolocation.ts`

### Files Modified

1. `src/lib/scraper/index.ts` - Registered all new scrapers
2. `src/lib/scraper/source-eventbrite.ts` - Added Mohan Matchmaking
3. `src/lib/scraper/utils.ts` - Added consolidateEvents function
4. `src/context/SettingsContext.tsx` - Added location filtering settings
5. `src/components/SettingsManager.tsx` - Added location filtering UI

### Total Event Sources

The scraper now pulls from **11 sources**:
1. Eventbrite (including Mohan Matchmaking)
2. AllEvents.in
3. Showpass (Flare Events, Single in the City, 25Dates)
4. Fatsoma (Thursday events)
5. CitySwoon
6. 25Dates
7. Thursday App
8. Toronto Dating Hub
9. Waterworks Food Hall
10. blogTO
11. Narcity

### Next Steps

To fully implement location filtering in the EventFeed component:

1. Import geolocation utilities
2. Add useEffect to geocode user location when settings change
3. Filter events based on distance calculation
4. Display distance in event cards (optional)
5. Add "Get Location" button for browser geolocation

### Testing Recommendations

1. Run scraper: `npm run scrape`
2. Verify new sources are collecting events
3. Test location filtering with different methods:
   - Browser geolocation
   - Postal code (e.g., M5V 3A8)
   - Address (e.g., "123 Queen St W, Toronto")
4. Verify distance calculations are accurate
5. Check that events are properly deduplicated

### Notes

- All scrapers use robust error handling
- Scrapers respect rate limiting (500ms delay between requests)
- Location filtering uses OpenStreetMap's Nominatim API (free, no API key required)
- Browser geolocation requires HTTPS and user permission
- Postal code validation ensures Canadian format (A1A 1A1)
