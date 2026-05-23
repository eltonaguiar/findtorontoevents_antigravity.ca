# Provider Registry & Data Source Integration Architecture

> **Document Version:** 1.0
> **For:** findtorontoevents.ca v0.6+
> **Author:** Design Enhancement Swarm

---

## 1. Design Philosophy

The provider registry pattern decouples event sources from the UI and ingestion pipeline. Each source is a **self-describing adapter** that the system can enumerate, toggle, and rate-limit independently. This enables:

- **Hot-swapping sources** without code changes to the UI
- **Per-source rate limiting** and quota management
- **Auditability** — track which source contributed which event
- **A/B testing** source combinations for quality
- **Graceful degradation** — disable a failing source without downtime

---

## 2. Core Interface

```typescript
// types/provider.ts

export type SourceType = "api" | "rss" | "scrape" | "ics" | "webhook";

export type AuthScheme =
  | { kind: "api_key"; header: string; envVar: string }
  | { kind: "oauth2"; tokenUrl: string; scopes: string[] }
  | { kind: "none" };

export interface EventSource {
  /** Machine identifier — used in URLs, localStorage keys, DB foreign keys */
  id: string;

  /** Human-readable name shown in the UI */
  name: string;

  /** Integration pattern */
  type: SourceType;

  /** Canonical website or API base */
  baseURL: string;

  /** Rate limit: requests per windowMs */
  rateLimit: {
    requests: number;
    windowMs: number;
  };

  /** Authentication requirements */
  auth: AuthScheme;

  /** Is this source exempt from the "max events per day per source" rule? */
  exemptFromLimit: boolean;

  /** Optional Lucide icon name mapped to UI */
  icon: string;

  /** Whether the source is enabled by default for new users */
  defaultEnabled: boolean;

  /** Event categories this source primarily covers (for smart filtering) */
  categories: string[];

  /** Time-to-live for cached events from this source */
  cacheTTLMinutes: number;

  /** Health check endpoint or pattern */
  healthCheck?: {
    url: string;
    expectedStatus: number;
  };

  /** Estimated average event count per sync (for capacity planning) */
  avgEventCount: number;

  /** Data quality score (0-100) based on description completeness, image availability, venue accuracy */
  qualityScore: number;
}
```

---

## 3. Registry File Structure

```
src/
├── providers/
│   ├── registry.ts              # Central registry: all sources listed
│   ├── types.ts                 # TypeScript interfaces
│   ├── base-adapter.ts          # Abstract base class
│   ├── adapters/
│   │   ├── eventbrite.adapter.ts
│   │   ├── ticketmaster.adapter.ts
│   │   ├── bandsintown.adapter.ts
│   │   ├── meetup.adapter.ts
│   │   ├── toronto-opendata.adapter.ts
│   │   ├── ago.adapter.ts
│   │   ├── rom.adapter.ts
│   │   ├── harbourfront.adapter.ts
│   │   ├── tiff.adapter.ts
│   │   ├── sportsnet.adapter.ts
│   │   ├── blogto.adapter.ts
│   │   └── facebook.adapter.ts
│   └── deduplicator.ts          # Cross-source dedup engine
```

### Registry (registry.ts)

```typescript
import { EventSource } from "./types";

export const PROVIDER_REGISTRY: EventSource[] = [
  {
    id: "eventbrite",
    name: "Eventbrite",
    type: "api",
    baseURL: "https://www.eventbriteapi.com/v3",
    rateLimit: { requests: 50, windowMs: 1000 },
    auth: { kind: "api_key", header: "Authorization", envVar: "EVENTBRITE_API_KEY" },
    exemptFromLimit: true,
    icon: "Ticket",
    defaultEnabled: true,
    categories: ["business", "community", "music", "arts", "food", "sports", "general"],
    cacheTTLMinutes: 60,
    avgEventCount: 1200,
    qualityScore: 82,
  },
  {
    id: "ticketmaster",
    name: "Ticketmaster",
    type: "api",
    baseURL: "https://app.ticketmaster.com/discovery/v2",
    rateLimit: { requests: 5000, windowMs: 86400000 }, // 5k/day
    auth: { kind: "api_key", header: "apikey", envVar: "TICKETMASTER_API_KEY" },
    exemptFromLimit: false,
    icon: "Ticket",
    defaultEnabled: true,
    categories: ["music", "sports", "theatre", "arts"],
    cacheTTLMinutes: 120,
    avgEventCount: 300,
    qualityScore: 88,
    healthCheck: { url: "/events.json?size=1&apikey=$KEY", expectedStatus: 200 },
  },
  // ... additional sources (see Section 5)
];

/** Look up a source by ID */
export const getSource = (id: string): EventSource | undefined =>
  PROVIDER_REGISTRY.find((s) => s.id === id);

/** Sources that are API-based (highest reliability) */
export const apiSources = () => PROVIDER_REGISTRY.filter((s) => s.type === "api");

/** Sources requiring auth (for admin dashboard) */
export const authenticatedSources = () =>
  PROVIDER_REGISTRY.filter((s) => s.auth.kind !== "none");
```

---

## 4. Base Adapter Pattern

Every source implements the same interface, hiding the messy details of pagination, auth, and response mapping.

```typescript
// providers/base-adapter.ts

import { EventSource, RawEvent } from "./types";

export interface FetchResult {
  events: RawEvent[];
  hasMore: boolean;
  nextCursor?: string;
  rateLimitRemaining?: number;
}

export interface RawEvent {
  externalId: string;
  sourceId: string;
  title: string;
  description?: string;
  startAt: string;      // ISO 8601
  endAt?: string;
  venueName?: string;
  venueAddress?: string;
  venueLat?: number;
  venueLng?: number;
  url: string;
  imageUrl?: string;
  priceMin?: number;
  priceMax?: number;
  currency?: string;
  isFree?: boolean;
  isSoldOut?: boolean;
  categories: string[];
  sourceQuality: number;
  rawData: Record<string, unknown>; // keep for debugging
}

export abstract class EventAdapter {
  constructor(protected source: EventSource) {}

  /** Fetch a page of events. Implementations handle auth, pagination, retries. */
  abstract fetch(cursor?: string, filters?: Record<string, string>): Promise<FetchResult>;

  /** Health check ping */
  abstract ping(): Promise<{ ok: boolean; latencyMs: number; message?: string }>;

  /** Convert source-specific raw data to RawEvent */
  abstract normalize(raw: unknown): RawEvent;

  /** Human-readable status for admin dashboards */
  getStatus(): { source: string; type: string; lastSync?: Date; eventCount?: number } {
    return {
      source: this.source.id,
      type: this.source.type,
    };
  }
}
```

---

## 5. Toronto Event Sources — Integration Feasibility Matrix

| # | Source | Type | Priority | Feasibility | Auth | Avg Events | Quality | Notes |
|---|--------|------|----------|-------------|------|------------|---------|-------|
| 1 | **Eventbrite** | API | P0 | ✅ Done | API Key | ~1,200 | 82 | Already integrated; exempt from limit |
| 2 | **Ticketmaster** | API | P0 | ✅ Easy | API Key | ~300 | 88 | Discovery API v2; covers concerts, sports, theatre |
| 3 | **Bandsintown** | API | P1 | ✅ Easy | API Key | ~180 | 75 | Artist + venue search; strong music coverage |
| 4 | **Meetup** | API | P1 | ⚠️ Medium | OAuth2 | ~90 | 70 | GraphQL API; declining activity but niche groups remain |
| 5 | **Toronto Open Data** | API | P1 | ✅ Easy | None | ~60 | 65 | City-run festivals, park events, civic meetings |
| 6 | **Art Gallery of Ontario (AGO)** | API | P2 | ⚠️ Medium | None (public) | ~25 | 80 | Has JSON feed; exhibitions + events |
| 7 | **Royal Ontario Museum (ROM)** | API | P2 | ⚠️ Medium | None (public) | ~20 | 78 | Calendar API available |
| 8 | **Harbourfront Centre** | RSS | P2 | ✅ Easy | None | ~15 | 70 | RSS feed of cultural programming |
| 9 | **TIFF** | API | P2 | ⚠️ Medium | None (public) | ~12 | 85 | Seasonal spikes during festival; REST endpoints |
| 10 | **MLB / NBA / NHL / MLS** | API | P2 | ⚠️ Medium | API Key | ~40 | 90 | Sportsdata.io or ESPN API; Jays, Raptors, Leafs, TFC |
| 11 | **BlogTO** | RSS | P2 | ✅ Easy | None | ~50 | 60 | Event listings scraping; good for food & nightlife |
| 12 | **Facebook Events** | API | P3 | 🔴 Hard | OAuth2 (restricted) | ~? | 75 | Graph API v18+ heavily restricted; may need page-scrape fallback |
| 13 | **Eventful / Songkick** | API | P3 | ✅ Easy | API Key | ~70 | 72 | Songkick strong for music; Eventful general |
| 14 | **Toronto Public Library** | API | P3 | ✅ Easy | None | ~30 | 65 | Programs API; family-friendly events |
| 15 | **Now Toronto** | RSS | P3 | ⚠️ Medium | None | ~40 | 68 | Alt-weekly listings; scrape RSS or HTML |
| 16 | **Doors Open Toronto** | Scrape | P4 | ⚠️ Medium | None | ~5 | 90 | Annual only; high-value architectural events |
| 17 | **Taste of Toronto / Food Festivals** | Scrape | P3 | ⚠️ Medium | None | ~10 | 75 | Seasonal; aggregator sites or individual sites |
| 18 | **Evergreen Brick Works** | API | P3 | ✅ Easy | None | ~12 | 72 | Environmental + family events |
| 19 | **Canada's Wonderland** | API | P4 | ⚠️ Medium | None | ~8 | 80 | Seasonal events API |
| 20 | **Toronto Zoo** | Scrape | P4 | ⚠️ Medium | None | ~6 | 70 | Calendar page scraping |

### Source Type Legend
- **API** = Official REST/GraphQL endpoint (most reliable)
- **RSS** = XML feed polling (moderate reliability, needs parser)
- **Scrape** = HTML scraping (brittle, needs maintenance)
- **Webhook** = Push-based (ideal, rare)

---

## 6. Deduplication Algorithm

### 6.1 Problem

The same event is often listed on multiple platforms:
- A concert on **Ticketmaster** + **Bandsintown** + **Eventbrite**
- A food festival on **BlogTO** + **Facebook** + **Eventbrite**

Without deduplication, users see 3x the same event.

### 6.2 Algorithm: "Smart Fingerprint + Quality Arbitration"

```
DEDUPLICATE(events[]):
    fingerprints = []
    canonical = []

    FOR each event IN events:
        fp = GENERATE_FINGERPRINT(event)
        match = FIND_MATCH(fingerprints, fp, threshold=0.82)

        IF match EXISTS:
            existing = canonical[match.index]
            winner = ARBITRATE(existing, event)
            canonical[match.index] = winner
            Mark event as duplicateOf = winner.id
        ELSE:
            fingerprints.append(fp)
            canonical.append(event)

    RETURN canonical, duplicates

GENERATE_FINGERPRINT(event):
    normalizedTitle = lowercase(event.title)
                         .removePunctuation()
                         .removeStopWords()
                         .truncate(40 chars)
    venueKey = normalizeVenueName(event.venueName)  // "AGO" → "art gallery of ontario"
    dateKey = event.startAt.toDateString()          // day-level granularity
    timeBucket = floorHour(event.startAt)            // 2-hour buckets

    // Composite hash
    RETURN hash(normalizedTitle + "|" + venueKey + "|" + dateKey + "|" + timeBucket)

FIND_MATCH(fingerprints, fp, threshold):
    FOR each candidate IN fingerprints:
        sim = JARO_WINKLER(fp.title, candidate.title)
        IF sim > 0.85 AND sameVenue(fp, candidate) AND sameDateWindow(fp, candidate):
            RETURN candidate
    RETURN null

ARBITRATE(existing, candidate):
    scoreA = SCORE_SOURCE(existing.sourceId) + metadataCompleteness(existing)
    scoreB = SCORE_SOURCE(candidate.sourceId) + metadataCompleteness(candidate)
    RETURN scoreA >= scoreB ? existing : candidate

SCORE_SOURCE(sourceId):
    // Prefer API sources, then RSS, then scrape
    source = getSource(sourceId)
    IF source.type == "api":   base = 40
    IF source.type == "rss":   base = 30
    IF source.type == "scrape": base = 20
    RETURN base + source.qualityScore

METADATA_COMPLETENESS(event):
    score = 0
    IF event.description && length > 100:  score += 10
    IF event.imageUrl:                     score += 10
    IF event.priceMin OR event.isFree:     score += 5
    IF event.venueAddress:                  score += 5
    IF event.venueLat AND event.venueLng:   score += 5
    RETURN score
```

### 6.3 Edge Cases

| Scenario | Handling |
|----------|----------|
| Same title, different venues (tour) | Venue mismatch breaks dedup |
| Same venue, different days (recurring) | Date mismatch breaks dedup |
| Multi-day festivals | Use start date only; treat as single event |
| Minor title variations ("Live: Band" vs "Band Live") | Jaro-Winkler > 0.85 catches these |
| Different times, same event (doors vs show) | 2-hour time bucket normalizes |
| Different prices (early bird vs door) | Price treated as metadata, not part of fingerprint |
| One source sold out, another available | Prefer non-sold-out if deduped |

---

## 7. Rate Limiting & Quota Management

```typescript
// lib/rate-limiter.ts

import { EventSource } from "@/providers/types";

class QuotaBucket {
  private tokens: number;
  private lastRefill: number;

  constructor(
    private capacity: number,
    private windowMs: number
  ) {
    this.tokens = capacity;
    this.lastRefill = Date.now();
  }

  async consume(): Promise<boolean> {
    this.refill();
    if (this.tokens >= 1) {
      this.tokens -= 1;
      return true;
    }
    const wait = this.windowMs / this.capacity;
    await sleep(wait);
    return this.consume();
  }

  private refill() {
    const now = Date.now();
    const elapsed = now - this.lastRefill;
    const tokensToAdd = (elapsed / this.windowMs) * this.capacity;
    this.tokens = Math.min(this.capacity, this.tokens + tokensToAdd);
    this.lastRefill = now;
  }
}

const buckets = new Map<string, QuotaBucket>();

export async function rateLimitedFetch(
  source: EventSource,
  fetchFn: () => Promise<Response>
): Promise<Response> {
  if (!buckets.has(source.id)) {
    buckets.set(source.id, new QuotaBucket(source.rateLimit.requests, source.rateLimit.windowMs));
  }
  const bucket = buckets.get(source.id)!;
  await bucket.consume();
  return fetchFn();
}
```

---

## 8. Sync Orchestration (GitHub Actions Integration)

The existing workflows `scrape-events.yml`, `deploy-fte-events-json.yml`, and `torontoevent-algorithm-refresh.yml` should be unified under a single orchestrator:

```yaml
# .github/workflows/sync-events.yml
name: Unified Event Sync

on:
  schedule:
    - cron: "0 */3 * * *"   # Every 3 hours
  workflow_dispatch:
    inputs:
      source:
        description: "Specific source to sync (or 'all')"
        default: "all"

jobs:
  discover:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Sync all enabled sources
        run: |
          node scripts/sync.js --source ${{ github.event.inputs.source || 'all' }}
        env:
          EVENTBRITE_API_KEY: ${{ secrets.EVENTBRITE_API_KEY }}
          TICKETMASTER_API_KEY: ${{ secrets.TICKETMASTER_API_KEY }}
          BANDSINTOWN_API_KEY: ${{ secrets.BANDSINTOWN_API_KEY }}

  deduplicate:
    needs: discover
    runs-on: ubuntu-latest
    steps:
      - name: Run dedup algorithm
        run: node scripts/deduplicate.js

  deploy:
    needs: deduplicate
    runs-on: ubuntu-latest
    steps:
      - name: Deploy consolidated JSON
        run: node scripts/deploy-json.js
```

---

## 9. Database Schema (Minimal Changes)

```sql
-- New table: provider_registry (mirrors the TypeScript interface)
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
    categories      TEXT, -- JSON array
    cache_ttl_mins  INTEGER,
    avg_event_count INTEGER,
    quality_score   INTEGER,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- New table: user_source_preferences (per-user overrides)
CREATE TABLE user_source_preferences (
    user_id         TEXT REFERENCES users(id) ON DELETE CASCADE,
    source_id       TEXT REFERENCES provider_registry(id) ON DELETE CASCADE,
    enabled         BOOLEAN DEFAULT TRUE,
    custom_max_per_day INTEGER, -- null = use global default
    PRIMARY KEY (user_id, source_id)
);

-- Add source_id to existing events table
ALTER TABLE events ADD COLUMN source_id TEXT REFERENCES provider_registry(id);
ALTER TABLE events ADD COLUMN duplicate_of TEXT REFERENCES events(id);
ALTER TABLE events ADD COLUMN source_quality INTEGER DEFAULT 50;

-- Index for dedup queries
CREATE INDEX idx_events_dedup ON events(source_id, title, venue_name, start_at);
```

---

## 10. Migration Path

| Phase | Task | Effort |
|-------|------|--------|
| 1 | Create `provider_registry` table; backfill with existing Eventbrite + any known sources | 2h |
| 2 | Implement Base Adapter + first new adapter (Ticketmaster) | 4h |
| 3 | Add deduplication pipeline as post-sync step | 6h |
| 4 | Build Gear Settings Modal UI (React component) | 6h |
| 5 | Add per-user preference persistence | 3h |
| 6 | Add 3 more high-priority adapters (Bandsintown, Meetup, Toronto Open Data) | 8h |
| 7 | Add calendar export endpoint | 4h |
| 8 | Add analytics/logging for source quality scoring | 4h |

---

*End of Provider Registry Architecture Document*
