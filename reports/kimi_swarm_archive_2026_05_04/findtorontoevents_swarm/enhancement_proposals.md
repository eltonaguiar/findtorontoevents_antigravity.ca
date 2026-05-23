# findtorontoevents.ca — Enhancement Proposals v1.0

> **Date:** 2026-04-26
> **Version:** v1.0
> **Status:** Design Complete / Ready for Implementation
> **Target Release:** v0.6.0

---

## Executive Summary

findtorontoevents.ca (v0.5.2) is a hand-coded HTML shell with Next.js event grid chunks serving Toronto event discovery. The platform currently shows ~50 events initially with scroll-to-sync loading, supports basic filters (date ranges, nearby, sold-out, price), and has a growing category taxonomy. Data quality issues persist — 49 events lack proper dates, and the single-source reliance (primarily Eventbrite) limits comprehensiveness.

**This proposal designs 7 concrete enhancements** to improve user control, data quality, and source diversity:

| Priority | Feature | Impact | Effort |
|----------|---------|--------|--------|
| P0 | Gear Settings Modal (Max Events Per Day / Source, Source Toggles) | 🔥 High | Medium |
| P0 | Provider Registry & 10+ New Data Sources | 🔥 High | High |
| P1 | Smart Deduplication | 🔥 High | Medium |
| P1 | Calendar Export (iCal + Google Calendar) | Medium | Low |
| P2 | Data Quality Dashboard | Medium | Low |
| P3 | Notification Preferences | Low | Medium |
| P3 | Weather-Aware Outdoor Filtering | Low | High |

**Estimated total implementation:** 3-4 sprints (6-8 weeks) with 1 full-stack developer.

---

## Feature 1: Gear Settings Modal

### 1.1 Overview

The existing ⚙️ gear icon opens a minimal panel. This feature expands it into a **full settings modal** with 4 tabs: Display, Sources, Export, and Advanced. The centerpiece is the **"Max events per day per source"** slider — letting users prevent any single platform from dominating their feed.

### 1.2 UX Flow

```
User clicks ⚙️ gear icon
  └─> Full-screen bottom sheet (mobile) / centered modal (desktop) opens
      ├─ Tab: Display
      │   ├─ Slider: "Max events per day per source" [1 ───── 10]  (default: 3)
      │   ├─ Toggle: "Exempt Eventbrite from limit"  (default: ON)
      │   ├─ Toggle: "Show source badges on cards"     (default: ON)
      │   └─ Toggle: "Group events by date"            (default: OFF)
      ├─ Tab: Sources
      │   ├─ List of all sources with enable/disable toggle
      │   ├─ Per-source: event count, type badge (API/RSS/Scrape), exempt status
      │   └─ Summary: "8 of 12 sources active • 1,847 events"
      ├─ Tab: Export
      │   ├─ Export format selector: iCal / Google Calendar / Both
      │   └─ "Export My Filtered View" button
      └─ Tab: Advanced
          ├─ Toggle: "Smart deduplication" with explanation
          ├─ Data quality meter (events with missing dates)
          └─ Future features placeholder (notifications, weather)

User makes changes → Auto-saved to localStorage (anon) or account (signed in)
User clicks "Done" → Modal closes, events grid re-filters with new settings
```

### 1.3 Detailed Component Spec

**File:** `/components/GearSettingsModal.tsx`

**Props Interface:**
```typescript
interface GearSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  isLoggedIn: boolean;
  initialSettings?: Partial<GearSettings>;
  onSettingsChange?: (settings: GearSettings) => void;  // notifies parent to re-filter
}
```

**Settings Shape:**
```typescript
interface GearSettings {
  maxEventsPerDayPerSource: number;  // 1-10, default 3
  exemptEventbrite: boolean;         // default true
  showSourceBadges: boolean;         // default true
  groupByDate: boolean;              // default false
  deduplicate: boolean;              // default true
  sources: EventSource[];            // from registry, with per-user enabled state
  calendarExportFormat: "ical" | "google" | "both";
}
```

### 1.4 Persistence Logic

| User State | Storage | Key | Sync Strategy |
|------------|---------|-----|---------------|
| Anonymous | `localStorage` | `fte_settings_local_v1` | Immediate write on change |
| Signed In | Database + `localStorage` fallback | `fte_settings_v1` | Write to DB async; localStorage as optimistic cache |

**Persistence Flow:**
```
 onSettingChange(newValue):
   ├─ Update React state (immediate UI feedback)
   ├─ Write to localStorage (synchronous, always)
   └─ IF isLoggedIn:
        ├─ Debounce 500ms
        ├─ POST /api/user/settings { settings }
        └─ Show "Saved to account" toast
```

**API Endpoint:**
```
POST /api/user/settings
Body: { settings: GearSettings }
Auth: Bearer token (JWT)
Response: { success: boolean, syncedAt: ISO8601 }

GET /api/user/settings
Auth: Bearer token
Response: { settings: GearSettings }
```

### 1.5 Accessibility

- **Focus trap:** Tab cycles within modal; `Shift+Tab` loops backward
- **Escape key:** Closes modal, restores previous focus
- **ARIA:** `role="dialog"`, `aria-modal="true"`, `aria-labelledby` on title
- **Keyboard:** All interactive elements reachable via Tab; toggles via Space/Enter
- **Screen reader:** Section headers announced; slider has `aria-valuemin/now/max`
- **Mobile:** Full-screen sheet with drag-to-dismiss gesture (future enhancement)

### 1.6 Mobile-Responsive Behavior

| Breakpoint | Behavior |
|------------|----------|
| `< 640px` | Bottom sheet: `w-full`, `rounded-t-2xl`, slides up from bottom. Max height 90vh. |
| `>= 640px` | Centered modal: `max-w-lg`, `rounded-2xl`, vertical centering. Max height 85vh. |

---

## Feature 2: Smart Deduplication

### 2.1 Problem Statement

Users see the same concert on Eventbrite, Ticketmaster, and Bandsintown. This creates:
- Noise and scrolling fatigue
- Mistrust in data quality
- Missed genuinely unique events buried under duplicates

### 2.2 Algorithm Design

**"Fingerprint + Quality Arbitration"**

```typescript
interface DedupFingerprint {
  titleHash: string;      // normalized, stemmed, first 40 chars
  venueKey: string;       // normalized venue name
  dateKey: string;        // YYYY-MM-DD
  timeBucket: number;     // 2-hour floor
}

function generateFingerprint(event: RawEvent): DedupFingerprint {
  return {
    titleHash: normalizeTitle(event.title),
    venueKey: normalizeVenue(event.venueName),
    dateKey: event.startAt.slice(0, 10),
    timeBucket: Math.floor(new Date(event.startAt).getHours() / 2) * 2,
  };
}

function isDuplicate(a: DedupFingerprint, b: DedupFingerprint): boolean {
  const titleSim = jaroWinkler(a.titleHash, b.titleHash);
  return titleSim > 0.85
      && a.venueKey === b.venueKey
      && a.dateKey === b.dateKey
      && Math.abs(a.timeBucket - b.timeBucket) <= 2;
}

function arbitrateWinner(a: Event, b: Event): Event {
  const scoreA = sourceQualityScore(a.sourceId) + metadataScore(a);
  const scoreB = sourceQualityScore(b.sourceId) + metadataScore(b);
  return scoreA >= scoreB ? a : b;
}
```

### 2.3 Edge Cases & Handling

| Scenario | Resolution |
|----------|------------|
| Same title, different venue (band on tour) | Venue mismatch → NOT duplicate |
| Same venue, recurring weekly event | Date mismatch → NOT duplicate |
| Title variations: "Band LIVE" vs "Live: Band" | Jaro-Winkler > 0.85 catches it |
| Multi-day festival | Use start date only; single fingerprint |
| Different prices (early bird vs door) | Price not in fingerprint; metadata only |
| One source has image, another doesn't | Image availability adds to metadata score |
| API source vs scraped source | API sources get +20 base score |
| Sold-out on one, available on another | Prefer available; add penalty to sold-out |

### 2.4 Implementation

```typescript
// lib/deduplicate.ts
export function deduplicateEvents(events: Event[]): {
  canonical: Event[];
  duplicates: Map<string, string>; // duplicateId -> canonicalId
} {
  const canonical: Event[] = [];
  const fingerprints: DedupFingerprint[] = [];
  const duplicates = new Map<string, string>();

  for (const event of events) {
    const fp = generateFingerprint(event);
    const matchIdx = fingerprints.findIndex(
      (f) => f.venueKey === fp.venueKey
          && f.dateKey === fp.dateKey
          && jaroWinkler(f.titleHash, fp.titleHash) > 0.85
    );

    if (matchIdx >= 0) {
      const existing = canonical[matchIdx];
      const winner = arbitrateWinner(existing, event);
      canonical[matchIdx] = winner;
      duplicates.set(
        winner.id === existing.id ? event.id : existing.id,
        winner.id
      );
    } else {
      fingerprints.push(fp);
      canonical.push(event);
    }
  }

  return { canonical, duplicates };
}
```

**Execution:** Run as a post-sync step after all sources are ingested but before the JSON is deployed.

---

## Feature 3: Calendar Export

### 3.1 User Story

> "I filtered to Food & Drink events this week. I want to add them to my Google Calendar so I can plan my weekend."

### 3.2 Export Formats

#### iCal (.ics) — Universal

```
GET /api/export/ical?filters=<base64_encoded_filters>
Response: text/calendar

BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//findtorontoevents.ca//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
BEGIN:VEVENT
UID:{{event.id}}@findtorontoevents.ca
DTSTAMP:{{now_iso}}
DTSTART:{{event.startAt}}
DTEND:{{event.endAt || event.startAt + 2h}}
SUMMARY:{{event.title}}
DESCRIPTION:{{event.description | truncate(500) | strip_newlines}}
LOCATION:{{event.venueName}}, {{event.venueAddress}}
URL:{{event.url}}
END:VEVENT
... (repeat)
END:VCALENDAR
```

**Notes:**
- Use `DTSTART;TZID=America/Toronto` for Toronto timezone
- Escape special characters in ICS fields (comma, semicolon, backslash, newline)
- Include `URL` property linking back to source
- Set `STATUS:CONFIRMED` (or `TENTATIVE` if date is fuzzy)

#### Google Calendar — Direct Add

```
Per-event "Add to Google Calendar" link:
https://www.google.com/calendar/render?action=TEMPLATE
  &text={{encodeURIComponent(event.title)}}
  &dates={{start_utc}}/{{end_utc}}
  &details={{encodeURIComponent(event.description)}}
  &location={{encodeURIComponent(event.venueAddress)}}

Bulk subscription (preferred):
User clicks "Subscribe" → we generate a hosted .ics URL
→ Google Calendar can subscribe to this URL and auto-sync
```

### 3.3 API Design

```
GET /api/export/calendar
Query params:
  format: "ical" | "google" | "both"
  filter_json: <base64 of active filter state>
  dedup: boolean (default true)
  max_days: number (default 30)

Response (format=ical):
  Content-Type: text/calendar
  Content-Disposition: attachment; filename="toronto-events-2026-04.ics"

Response (format=google):
  JSON { subscribeUrl: string, eventCount: number }

Response (format=both):
  JSON {
    icalUrl: string,
    googleSubscribeUrl: string,
    eventCount: number,
    expiresAt: ISO8601
  }
```

### 3.4 Caching & Performance

- Generated exports cached for 1 hour (events update frequently)
- Signed URLs with expiry (prevents abuse)
- Max 500 events per export (warn if filtered set exceeds)

---

## Feature 4: Source Toggles & Provider Registry

### 4.1 Overview

Users can enable/disable individual event sources. This pairs with the **Provider Registry** (see `providerRegistry.md`) which abstracts all sources behind a common interface.

### 4.2 UI Design

**Sources Tab in Gear Modal:**
```
┌─────────────────────────────────────────┐
│  Data Sources          8 of 12 active  │
│              1,847 events enabled        │
├─────────────────────────────────────────┤
│ [✓] Eventbrite         [Official API]   │
│     1,240 events       Exempt from limit │
│ [✓] Ticketmaster       [Official API]   │
│     310 events                          │
│ [✓] Bandsintown        [Official API]   │
│     185 events                          │
│ [✗] Facebook Events    [Official API]   │
│     Not yet synced                      │
│ [✓] Harbourfront       [RSS Feed]        │
│     18 events                           │
│ ...                                     │
└─────────────────────────────────────────┘
```

### 4.3 Toggle Behavior

- Disabling a source immediately removes its events from the grid (client-side filter)
- Re-enabling triggers a refresh (fetch from cache or API)
- Per-user preference stored in `user_source_preferences` table (or localStorage)

### 4.4 Badge System

| Badge | Color | Meaning |
|-------|-------|---------|
| Official API | Green (`emerald`) | REST/GraphQL; highest reliability |
| RSS Feed | Amber (`amber`) | XML polling; moderate reliability |
| Scraped | Rose (`rose`) | HTML scraping; may break |
| Exempt | Indigo (`indigo`) | Not subject to max-per-day limit |
| Not Synced | Slate (`slate`) | Source registered but never fetched |

---

## Feature 5: Additional Data Sources

### 5.1 Proposed Sources Table

| # | Source | Type | Priority | Feasibility | Auth | Est. Events | Quality | Notes |
|---|--------|------|----------|-------------|------|-------------|---------|-------|
| 1 | **Eventbrite** | API | P0 | ✅ Done | API Key | ~1,200 | 82 | Already primary source; exempt from limit |
| 2 | **Ticketmaster** | API | P0 | ✅ Easy | API Key | ~300 | 88 | Discovery API v2; concerts, sports, theatre |
| 3 | **Bandsintown** | API | P1 | ✅ Easy | API Key | ~180 | 75 | Artist + venue search; strong music |
| 4 | **Meetup** | API | P1 | ⚠️ Medium | OAuth2 | ~90 | 70 | GraphQL; declining but niche groups persist |
| 5 | **Toronto Open Data** | API | P1 | ✅ Easy | None | ~60 | 65 | City festivals, park events, civic meetings |
| 6 | **AGO** | API | P2 | ⚠️ Medium | None | ~25 | 80 | JSON feed; exhibitions + ticketed events |
| 7 | **ROM** | API | P2 | ⚠️ Medium | None | ~20 | 78 | Calendar API; exhibitions + lectures |
| 8 | **Harbourfront Centre** | RSS | P2 | ✅ Easy | None | ~15 | 70 | Cultural programming feed |
| 9 | **TIFF** | API | P2 | ⚠️ Medium | None | ~12 | 85 | Seasonal spikes; REST endpoints |
| 10 | **Sports Leagues** | API | P2 | ⚠️ Medium | API Key | ~40 | 90 | MLB (Jays), NBA (Raptors), NHL (Leafs), MLS (TFC) |
| 11 | **BlogTO** | RSS | P2 | ✅ Easy | None | ~50 | 60 | Food & nightlife listings |
| 12 | **Facebook Events** | API | P3 | 🔴 Hard | OAuth2 | ~? | 75 | Graph API v18+ restricted; page-scrape fallback |
| 13 | **Songkick** | API | P3 | ✅ Easy | API Key | ~70 | 72 | Music-focused; excellent concert coverage |
| 14 | **Toronto Public Library** | API | P3 | ✅ Easy | None | ~30 | 65 | Family programs, workshops |
| 15 | **Now Toronto** | RSS | P3 | ⚠️ Medium | None | ~40 | 68 | Alt-weekly; arts & music focus |

### 5.2 Integration Feasibility Analysis

**Easy (P0-P1):**
- Ticketmaster: Well-documented Discovery API, generous rate limits (5k/day)
- Bandsintown: Simple REST API, artist-centric queries
- Toronto Open Data: CKAN API, no auth, open JSON endpoints
- BlogTO / Harbourfront: RSS 2.0 feeds, standard XML parsing

**Medium (P2):**
- AGO / ROM: Public calendar endpoints, but may need HTML scraping for full detail
- TIFF: RESTful but seasonal (quiet most of year, massive during festival)
- Meetup: OAuth2 flow required; API has been restricted post-2023
- Sports Leagues: Multiple APIs needed (MLB, NBA, NHL, MLS); Sportsdata.io aggregates

**Hard (P3):**
- Facebook Events: Graph API severely restricted for events since 2023; may require public page scraping with Puppeteer
- Facebook scraper risk: ToS violation, brittle selectors, CAPTCHA challenges

### 5.3 Rate Limit Summary

| Source | Requests | Window | Notes |
|--------|----------|--------|-------|
| Eventbrite | 50 | 1 second | 1000/hour total tiered |
| Ticketmaster | 5,000 | 1 day | Generous |
| Bandsintown | 100 | 1 hour | Free tier |
| Meetup | 200 | 1 hour | OAuth2 required |
| Toronto Open Data | None | — | No rate limit |

---

## Feature 6: Notification Preferences (Future)

### 6.1 Concept

Allow signed-in users to subscribe to push/email notifications when new events match their saved filters.

### 6.2 Proposed Design

```
Tab: Notifications (visible only when signed in)
├─ Toggle: "Email me weekly digest of new events"
├─ Toggle: "Push notification for same-day events"
├─ Toggle: "Alert when a sold-out event gets tickets"
└─ Filter preview: "You have 3 saved filters"
    ├─ "Food & Drink • This Week" [Edit] [Delete]
    ├─ "Music • Tonight" [Edit] [Delete]
    └─ "Free Events • Family" [Edit] [Delete]
```

### 6.3 Technical Requirements

- Web Push API + service worker for browser notifications
- Resend/SendGrid for email digests
- Background job (Cron) to check for new matches and queue notifications
- `user_notification_preferences` table with JSON filter definitions

### 6.4 Status

**Deferred to v0.7.0** — requires auth infrastructure, email service, and push notification setup.

---

## Feature 7: Weather-Aware Outdoor Event Filtering (Future)

### 7.1 Concept

Automatically deprioritize or badge outdoor events when rain, snow, or extreme temperatures are forecast.

### 7.2 Proposed Design

```
Advanced Tab (when enabled):
├─ Toggle: "Weather-aware filtering"
│   └─ When ON:
│       ├─ If rain > 40% probability:
│       │   └─ Outdoor events get "🌧️ Rain Expected" badge
│       │   └─ Optional: move to bottom of list
│       ├─ If temp < -10°C or > 35°C:
│       │   └─ "Extreme temp" badge on outdoor events
│       └─ Indoor events unaffected
```

### 7.3 Data Requirements

- Weather API: OpenWeatherMap, WeatherAPI, or Environment Canada
- Event tagging: Need "venue_type" field (indoor / outdoor / mixed)
- Geocoding: Event lat/lng for hyperlocal weather (if Toronto-wide, city-level sufficient)

### 7.4 Status

**Deferred to v0.8.0** — requires weather API integration, venue type classification, and a recommendation engine.

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1-2)

| Task | Owner | Days |
|------|-------|------|
| Create `provider_registry` DB table & backfill | Backend | 1 |
| Implement Provider Registry TypeScript types + BaseAdapter | Backend | 2 |
| Build GearSettingsModal React component (UI only) | Frontend | 3 |
| Add localStorage persistence | Frontend | 0.5 |
| Add per-user settings API endpoints | Backend | 1 |

**Deliverable:** Settings modal works for anonymous users; sources listed; toggles functional locally.

### Phase 2: Sources & Deduplication (Week 3-4)

| Task | Owner | Days |
|------|-------|------|
| Implement Ticketmaster adapter | Backend | 2 |
| Implement Bandsintown adapter | Backend | 1.5 |
| Implement Toronto Open Data adapter | Backend | 1 |
| Build deduplication pipeline | Backend | 3 |
| Integrate dedup into sync workflow | DevOps | 1 |
| Add source badges to event cards | Frontend | 1 |

**Deliverable:** 3 new sources live; deduplication running; event cards show source badges.

### Phase 3: Calendar Export & Polish (Week 5-6)

| Task | Owner | Days |
|------|-------|------|
| Build iCal export endpoint | Backend | 2 |
| Build Google Calendar URL generator | Backend | 1 |
| Wire export buttons in modal | Frontend | 1 |
| Add mobile sheet drag-to-dismiss | Frontend | 1 |
| Add focus trap + full a11y audit | Frontend | 1 |
| Add analytics (source quality scoring) | Backend | 1 |

**Deliverable:** Calendar export functional; mobile UX polished; analytics tracking source performance.

### Phase 4: Advanced Sources (Week 7-8)

| Task | Owner | Days |
|------|-------|------|
| AGO + ROM adapters | Backend | 2 |
| Harbourfront RSS adapter | Backend | 0.5 |
| Sports leagues aggregator | Backend | 2 |
| Performance optimization (query caching) | Backend | 2 |
| BlogTO RSS adapter | Backend | 0.5 |

**Deliverable:** 8+ sources active; system stable under load.

---

## API / Backend Changes

### New Endpoints

```
POST /api/user/settings
  → Save user settings to DB
  Auth: JWT
  Body: { maxEventsPerDay, exemptEventbrite, showBadges, groupByDate, dedup, sources[], calendarFormat }

GET /api/user/settings
  → Retrieve user settings
  Auth: JWT

POST /api/export/calendar
  → Generate calendar export
  Query: { format, filter_json, dedup, max_days }
  Response: File or JSON with URLs

GET /api/sources
  → List all sources with metadata
  Response: { sources: EventSource[], totalEvents, lastSync }

GET /api/sources/:id/health
  → Health check for a specific source
  Response: { ok, latencyMs, lastSuccess, eventCount, error? }

POST /api/admin/sync
  → Trigger manual sync (admin only)
  Body: { sourceId?: string, force?: boolean }
```

### Modified Endpoints

```
GET /api/events
  → Add query params:
    - source_ids: string[] (filter to specific sources)
    - dedup: boolean (default true)
    - max_per_day: number (default 3)
    - exempt_ids: string[] (sources exempt from per-day limit)
```

---

## Database Schema Changes

### New Tables

```sql
-- Provider registry (canonical source definitions)
CREATE TABLE provider_registry (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    type            TEXT NOT NULL CHECK (type IN ('api','rss','scrape','ics','webhook')),
    base_url        TEXT,
    rate_limit_req  INTEGER,
    rate_limit_ms   INTEGER,
    auth_kind       TEXT,
    exempt_limit    BOOLEAN DEFAULT FALSE,
    icon            TEXT,
    default_enabled BOOLEAN DEFAULT TRUE,
    categories      JSONB,
    cache_ttl_mins  INTEGER,
    avg_event_count INTEGER,
    quality_score   INTEGER,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- Per-user source preferences (override defaults)
CREATE TABLE user_source_preferences (
    user_id            TEXT REFERENCES users(id) ON DELETE CASCADE,
    source_id          TEXT REFERENCES provider_registry(id) ON DELETE CASCADE,
    enabled            BOOLEAN DEFAULT TRUE,
    custom_max_per_day INTEGER,
    PRIMARY KEY (user_id, source_id)
);

-- User settings (gear modal state)
CREATE TABLE user_settings (
    user_id                   TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    max_events_per_day        INTEGER DEFAULT 3,
    exempt_eventbrite         BOOLEAN DEFAULT TRUE,
    show_source_badges        BOOLEAN DEFAULT TRUE,
    group_by_date             BOOLEAN DEFAULT FALSE,
    deduplicate               BOOLEAN DEFAULT TRUE,
    calendar_export_format    TEXT DEFAULT 'both',
    updated_at                TIMESTAMPTZ DEFAULT now()
);

-- Export tokens (for calendar subscribe URLs)
CREATE TABLE export_tokens (
    token         TEXT PRIMARY KEY,
    user_id       TEXT REFERENCES users(id) ON DELETE CASCADE,
    filter_json   JSONB,
    format        TEXT,
    expires_at    TIMESTAMPTZ,
    created_at    TIMESTAMPTZ DEFAULT now()
);
```

### Modified Tables

```sql
-- Add columns to existing events table
ALTER TABLE events ADD COLUMN source_id TEXT REFERENCES provider_registry(id);
ALTER TABLE events ADD COLUMN duplicate_of TEXT REFERENCES events(id);
ALTER TABLE events ADD COLUMN source_quality INTEGER DEFAULT 50;
ALTER TABLE events ADD COLUMN is_outdoor BOOLEAN DEFAULT NULL;  -- for future weather feature

-- Indexes for performance
CREATE INDEX idx_events_source ON events(source_id);
CREATE INDEX idx_events_duplicate ON events(duplicate_of) WHERE duplicate_of IS NOT NULL;
CREATE INDEX idx_events_dedup_query ON events(title, venue_name, start_at);
CREATE INDEX idx_events_outdoor ON events(is_outdoor, start_at) WHERE is_outdoor = TRUE;
```

---

## Appendix A: Priority Ratings Summary

| Feature | Priority | Business Value | User Value | Technical Risk | Effort |
|---------|----------|----------------|------------|----------------|--------|
| Gear Settings Modal | **P0** | High | Very High | Low | 4 days |
| Provider Registry + 10 Sources | **P0** | Very High | Very High | Medium | 10 days |
| Smart Deduplication | **P1** | High | Very High | Medium | 4 days |
| Calendar Export | **P1** | Medium | High | Low | 3 days |
| Data Quality Dashboard | **P2** | Medium | Medium | Low | 2 days |
| Notification Preferences | **P3** | Medium | Medium | Medium | 5 days |
| Weather-Aware Filtering | **P3** | Low | Medium | High | 6 days |

---

*End of Enhancement Proposals Document*
