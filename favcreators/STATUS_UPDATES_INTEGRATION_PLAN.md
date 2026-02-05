# Creator Status Updates — Integration Plan

## Overview

A new feature module that tracks the **latest content updates** (posts, stories, streams, tweets, VODs, etc.) from creators across **7+ platforms**: Twitch, Kick, TikTok, Instagram, Twitter/X, Reddit, and YouTube.

This sits alongside the existing `streamer_last_seen` live-detection system but covers **all content types**, not just live status.

---

## New Files Created

| File | Purpose |
|------|---------|
| `public/api/creator_status_updates_schema.php` | DB schema — `creator_status_updates` + `creator_status_check_log` tables |
| `public/api/status_updates.php` | **GET** endpoint — query/filter stored status updates |
| `public/api/update_creator_status.php` | **POST** endpoint — insert/update status records (single + batch) |
| `public/api/fetch_platform_status.php` | **GET** endpoint — live-fetch from platform APIs, with optional DB save |
| `tests/status-updates-api.spec.ts` | 50+ Playwright tests — all endpoints, all platforms, edge cases, security |

---

## API Endpoints

### 1. `GET /api/status_updates.php` — Query stored updates

| Parameter | Type | Description |
|-----------|------|-------------|
| `platform` | string | Filter by platform: `twitch`, `kick`, `tiktok`, `instagram`, `twitter`, `reddit`, `youtube`, `spotify` |
| `user` | string | Filter by username |
| `creator_id` | string | Filter by creator ID |
| `type` | string | Filter by update type: `post`, `story`, `stream`, `vod`, `tweet`, `comment`, `video`, `short`, `reel` |
| `live_only` | 1/0 | Only return currently-live entries |
| `since_hours` | int | Only return entries from the last N hours |
| `limit` | int | Max results (default 50, max 100) |

**Example:**
```
GET /api/status_updates.php?platform=twitch&user=nevsrealm
GET /api/status_updates.php?platform=tiktok&type=story&since_hours=24
GET /api/status_updates.php?live_only=1
```

**Response:**
```json
{
  "ok": true,
  "updates": [ { ... } ],
  "count": 5,
  "stats": {
    "total_tracked": 150,
    "unique_creators": 45,
    "platforms_tracked": 6,
    "currently_live": 3,
    "last_check_time": "2026-02-05 14:30:00"
  },
  "platform_breakdown": {
    "twitch": { "tracked": 30, "live": 2 },
    "youtube": { "tracked": 40, "live": 0 }
  },
  "supported_platforms": ["twitch", "kick", "tiktok", "instagram", "twitter", "reddit", "youtube", "spotify"]
}
```

### 2. `POST /api/update_creator_status.php` — Save updates

**Single:**
```json
{
  "creator_id": "nevsrealm",
  "creator_name": "NevsRealm",
  "platform": "twitch",
  "username": "nevsrealm",
  "update_type": "stream",
  "content_title": "Playing Elden Ring",
  "content_url": "https://twitch.tv/nevsrealm",
  "is_live": true,
  "viewer_count": 500
}
```

**Batch:**
```json
{
  "updates": [
    { "creator_id": "a", "creator_name": "A", "platform": "twitch", "username": "a", ... },
    { "creator_id": "b", "creator_name": "B", "platform": "youtube", "username": "b", ... }
  ]
}
```

### 3. `GET /api/fetch_platform_status.php` — Live-fetch from platforms

| Parameter | Type | Description |
|-----------|------|-------------|
| `platform` | string | **Required.** Platform to check |
| `user` | string | **Required.** Username on that platform |
| `save` | 1/0 | Auto-save results to DB |
| `creator_id` | string | Creator ID to use when saving |
| `creator_name` | string | Creator name to use when saving |

**Example:**
```
GET /api/fetch_platform_status.php?platform=twitch&user=nevsrealm
GET /api/fetch_platform_status.php?platform=reddit&user=spez&save=1&creator_id=spez_reddit
```

---

## Supported Platforms & Data Sources

| Platform | Method | What's Checked | Auth Required |
|----------|--------|---------------|---------------|
| **Twitch** | decapi.me public API | Live status, stream title, latest VOD | No |
| **Kick** | Kick API v2 (`/api/v2/channels/`) | Live status, stream title, viewers, recent VODs | No |
| **TikTok** | Page scraping (`/live`, profile) | Live status, latest post | No |
| **Instagram** | Web profile API + page scraping | Latest post, likes, comments | No (rate-limited) |
| **Twitter/X** | Syndication API + Nitter RSS fallback | Latest tweet | No |
| **Reddit** | Public JSON API (`/user/.json`) | Latest post, latest comment, upvotes | No (rate-limited) |
| **YouTube** | RSS feed + page scraping | Latest video, live status, thumbnails | No |

---

## Database Schema

### `creator_status_updates`

| Column | Type | Description |
|--------|------|-------------|
| `id` | INT AUTO_INCREMENT | Primary key |
| `creator_id` | VARCHAR(64) | Maps to existing creator system |
| `creator_name` | VARCHAR(255) | Display name |
| `platform` | VARCHAR(32) | twitch, kick, tiktok, instagram, twitter, reddit, youtube |
| `username` | VARCHAR(255) | Platform username |
| `account_url` | VARCHAR(1024) | Full URL to profile |
| `update_type` | VARCHAR(32) | post, story, stream, vod, tweet, comment, video, short, reel |
| `content_title` | VARCHAR(512) | Title or text snippet |
| `content_url` | VARCHAR(1024) | Direct link to content |
| `content_preview` | VARCHAR(2048) | Description or text preview |
| `content_thumbnail` | VARCHAR(1024) | Thumbnail image URL |
| `content_id` | VARCHAR(255) | Platform-specific content ID |
| `is_live` | TINYINT(1) | Currently live? |
| `viewer_count` | INT | Current/peak viewers |
| `like_count` | INT | Likes/upvotes |
| `comment_count` | INT | Comments |
| `content_published_at` | DATETIME | When content was originally published |
| `last_checked` | DATETIME | When we last checked |
| `last_updated` | DATETIME | When this record was last modified |
| `check_count` | INT | How many times this has been checked |
| `checked_by` | VARCHAR(255) | Who/what performed the check |
| `error_message` | VARCHAR(512) | Last error if any |

**Unique Key:** `(creator_id, platform, update_type)` — one record per creator per platform per content type.

### `creator_status_check_log`

Audit log of every check performed (same pattern as `streamer_check_log`).

---

## Integration Steps for https://findtorontoevents.ca/fc/

### Phase 1: Deploy API (Backend Only)

1. **Upload the 4 new PHP files** to `public/api/` on the server
2. **Tables auto-create** — the schema file runs `CREATE TABLE IF NOT EXISTS` on first request
3. **Test endpoints** — run `npx playwright test tests/status-updates-api.spec.ts` against production
4. **Verify** — hit `/fc/api/status_updates.php` in browser, confirm `{"ok":true,...}`

### Phase 2: Connect to Existing Creator Data

5. **Hook into CreatorCard.tsx** — when a creator card is rendered and has social accounts, call `fetch_platform_status.php` for each account to get latest content
6. **Add a "Last Activity" indicator** to each `SocialAccount` row in the creator card:
   ```tsx
   // In CreatorCard.tsx, for each account:
   const lastActivity = useStatusUpdate(account.platform, account.username);
   // Show: "Last post: 2h ago" or "LIVE" badge
   ```
7. **Extend the `SocialAccount` type** in `types.ts`:
   ```typescript
   export interface SocialAccount {
     // ... existing fields ...
     lastContentTitle?: string;
     lastContentUrl?: string;
     lastContentAt?: number;  // Unix timestamp
     lastContentType?: string; // 'post' | 'tweet' | 'video' etc.
   }
   ```

### Phase 3: Add Status Updates UI Panel

8. **Create `StatusUpdatesPanel.tsx`** — a new component that shows a feed of recent creator activity across all platforms, similar to `LiveSummary.tsx`
9. **Add a tab or section** in the main FC UI for "Recent Activity" alongside the existing creator list
10. **Auto-refresh** — poll `status_updates.php?since_hours=24` every 5 minutes for a live feed

### Phase 4: Automated Background Checks

11. **Create a cron job / scheduled task** that iterates over all tracked creators and calls `fetch_platform_status.php?save=1` for each of their accounts
12. **Suggested frequency:**
    - Twitch/Kick/TikTok live checks: every 5 minutes
    - YouTube/Reddit/Twitter posts: every 30 minutes
    - Instagram: every 1 hour (most rate-limited)
13. **Implementation:** A simple PHP script (`cron_check_all_creators.php`) that:
    - Queries `get_all_followed_creators.php` for the master list
    - Loops through each creator's accounts
    - Calls `fetch_platform_status.php?save=1` for each
    - Respects rate limits with delays between calls

### Phase 5: Enhanced Features (Future)

14. **Notifications** — alert users when a followed creator posts new content
15. **Activity timeline** — show a chronological feed of all creator activity
16. **Content type filtering in UI** — let users toggle what types they care about (streams, posts, tweets, etc.)
17. **API keys** — add optional Twitch Client-ID, YouTube API key, etc. in `.env` for higher rate limits
18. **Webhook support** — receive push notifications from platforms that support it (Twitch EventSub, YouTube PubSubHubbub)

---

## Content Safety

- **NSFW filtering:** Reddit fetcher skips posts/comments with `over_18: true`
- **Platform whitelist:** Only 8 approved platforms are accepted; adult/illegal platforms are rejected with 400 error
- **No user-generated arbitrary URLs** — all platform URLs are constructed server-side from known patterns
- **Input validation** — all POST fields are validated for type and allowed values

---

## Testing

Run the full test suite:

```bash
cd favcreators
npx playwright test tests/status-updates-api.spec.ts --reporter=list
```

The test file contains **50+ tests** organized in 6 groups:

1. **status_updates.php GET** — 16 tests (filtering, validation, CORS, structure)
2. **update_creator_status.php POST** — 13 tests (create, update, batch, validation, all types/platforms)
3. **fetch_platform_status.php** — 15 tests (all 7 platforms, error handling, normalization)
4. **End-to-end flows** — 4 tests (insert→retrieve, fetch→save→retrieve, check_count)
5. **Edge cases & security** — 7 tests (SQL injection, XSS, unicode, special chars)
6. **Performance** — 3 tests (response time thresholds)

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────┐
│  Frontend (React)                                            │
│  ┌─────────────┐  ┌──────────────────┐  ┌────────────────┐  │
│  │ CreatorCard  │  │ StatusUpdates    │  │ LiveSummary    │  │
│  │  + activity  │  │ Panel (new)      │  │ (existing)     │  │
│  └──────┬───────┘  └────────┬─────────┘  └───────┬────────┘  │
│         │                   │                     │           │
└─────────┼───────────────────┼─────────────────────┼───────────┘
          │                   │                     │
          ▼                   ▼                     ▼
┌─────────────────────────────────────────────────────────────┐
│  PHP API Layer                                               │
│  ┌────────────────────┐  ┌──────────────────────────────┐   │
│  │ status_updates.php │  │ fetch_platform_status.php    │   │
│  │ (GET — read DB)    │  │ (GET — live-check platforms) │   │
│  └────────┬───────────┘  └──────────────┬───────────────┘   │
│           │                             │                    │
│  ┌────────┴───────────┐  ┌──────────────┴───────────────┐   │
│  │ update_creator_    │  │ Platform Fetchers:            │   │
│  │ status.php         │  │  • fetch_twitch_status()     │   │
│  │ (POST — write DB)  │  │  • fetch_kick_status()       │   │
│  └────────┬───────────┘  │  • fetch_tiktok_status()     │   │
│           │              │  • fetch_instagram_status()   │   │
│           │              │  • fetch_twitter_status()     │   │
│           │              │  • fetch_reddit_status()      │   │
│           │              │  • fetch_youtube_status()     │   │
│           │              └──────────────────────────────┘    │
│           │                                                  │
└───────────┼──────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────┐
│  MySQL Database                          │
│  ┌──────────────────────────────────┐   │
│  │ creator_status_updates           │   │
│  │ (main data table)                │   │
│  ├──────────────────────────────────┤   │
│  │ creator_status_check_log         │   │
│  │ (audit log)                      │   │
│  ├──────────────────────────────────┤   │
│  │ streamer_last_seen (existing)    │   │
│  │ creators (existing)              │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

---

## Merge Strategy

This feature is **fully self-contained** — no existing files are modified. To merge:

1. Copy the 4 new PHP files into `public/api/`
2. Copy the test file into `tests/`
3. Deploy to server
4. Tables auto-create on first API call
5. Frontend integration (Phase 2-3) can be done incrementally

To remove: delete the 4 PHP files and drop the 2 DB tables. No other code is affected.
