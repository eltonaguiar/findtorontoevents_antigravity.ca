# TikTok Live Check (TLC) Implementation

**Created:** February 4, 2026  
**Endpoint:** `https://findtorontoevents.ca/fc/TLC.php?user=USERNAME`

## Overview

TLC is a PHP endpoint that checks if a TikTok user is currently live streaming. It uses multiple detection methods and verification passes to ensure accurate results, even when TikTok's responses are inconsistent.

## Files

| File | Purpose |
|------|---------|
| `favcreators/docs/TLC.php` | Main source file (deployed to `/fc/TLC.php`) |
| `favcreators/public/TLC.php` | Copy of main file |

## Usage

### Basic Check
```
GET https://findtorontoevents.ca/fc/TLC.php?user=gabbyvn3
```

### Response (Live)
```json
{
  "user": "gabbyvn3",
  "live": true,
  "method": "sigi_user_status",
  "checks": "1 live, 0 offline, 0 failed",
  "checked_at": "2026-02-04T22:22:55Z"
}
```

### Response (Offline)
```json
{
  "user": "sunnystoktik",
  "live": false,
  "method": "consensus_offline",
  "checks": "0 live, 3 offline, 0 failed",
  "checked_at": "2026-02-04T22:23:15Z"
}
```

### Debug Mode
```
GET https://findtorontoevents.ca/fc/TLC.php?user=gabbyvn3&debug=1
```
Returns additional `debug` object with all detection indicators and methods used.

## Detection Methods (12 Total)

The endpoint uses multiple detection methods in order of reliability:

| # | Method | Description | Indicator |
|---|--------|-------------|-----------|
| 1 | `sigi_user_status` | SIGI_STATE JSON user.status | status:2 = live, status:4 = offline |
| 2 | `sigi_room_status` | SIGI_STATE liveRoom.status | status:2 = live, status:4 = offline |
| 3 | `sigi_roomId` | Non-empty roomId in SIGI_STATE | roomId with 10+ digits = live |
| 4 | `universal_roomId` | roomId in __UNIVERSAL_DATA__ | Non-empty roomId = live |
| 5 | `og_description_live` | og:description meta tag | Contains "currently LIVE" |
| 6 | `title_contains_live` | Page title | Contains "is LIVE" |
| 7 | `regex_roomId` | roomId regex in raw HTML | `"roomId":"1234567890"` pattern |
| 8 | `stream_url` | TikTok CDN stream URLs | `pull-*.tiktokcdn.com/stage/stream-*` |
| 9 | `webcast_url` | WebSocket/WebCast URLs | `wss://...webcast...tiktok` |
| 10 | `viewer_count` | Viewer count fields | `user_count` or `viewerCount` > 0 |
| 11 | `isLive_field` | Boolean fields | `"isLive":true` or `"alive":true` |
| 12 | `roomInfo` | Room info object | Populated roomInfo = live |

## Verification Strategy

1. **Multiple Passes:** Performs up to 3 verification checks
2. **Early Exit:** Stops immediately when LIVE is detected (optimistic approach)
3. **Consensus:** If no LIVE detected, requires multiple offline confirmations
4. **Fallback Chain:** Direct fetch → Different User-Agent → Proxy services

## Anti-Blocking Features

### User-Agent Rotation
Rotates through 6 different browser User-Agents:
- Chrome (Windows, Mac, Linux)
- Firefox
- Safari (iPhone, iPad)
- Edge

### Proxy Fallbacks
If direct fetch fails, tries these proxy services:
- `api.allorigins.win`
- `corsproxy.io`
- `api.codetabs.com`

### Cache Busting
- Adds random `_cb` parameter to URLs
- Sets `Cache-Control: no-cache` headers
- Forces fresh connections with CURL

### Request Headers
Mimics real browser requests:
- Proper Accept headers
- Accept-Language
- Sec-Fetch-* headers
- Upgrade-Insecure-Requests

## TikTok Status Codes

From TikTok's SIGI_STATE JSON:

| Status | Meaning |
|--------|---------|
| `2` | **LIVE** - User is currently streaming |
| `4` | **OFFLINE** - User is not streaming |
| `0` | Indeterminate (check roomId) |

## Key Learnings

1. **"LIVE has ended" text is unreliable** - Always present in page as UI element, even during live streams
2. **SIGI_STATE JSON is most reliable** - Contains actual status codes (2=live, 4=offline)
3. **roomId presence indicates live** - Non-empty roomId (10+ digits) = streaming
4. **TikTok responses can be inconsistent** - Multiple checks needed for reliability
5. **Redirect detection** - `/live` URL redirecting to profile = not live

## Code Location

The main TLC.php file is located at:
```
favcreators/docs/TLC.php
```

This gets deployed to:
```
https://findtorontoevents.ca/fc/TLC.php
```

## Deployment

Files are deployed via:
```bash
python tools/deploy_to_ftp.py
```

## Testing

```bash
# Test live user
curl "https://findtorontoevents.ca/fc/TLC.php?user=gabbyvn3"

# Test offline user  
curl "https://findtorontoevents.ca/fc/TLC.php?user=sunnystoktik"

# Test with debug info
curl "https://findtorontoevents.ca/fc/TLC.php?user=gabbyvn3&debug=1"
```

## IMPORTANT: Do Not Modify Without Reading

When making changes to TLC.php:

1. **Read this document first**
2. **Preserve all 12 detection methods** - Each serves as a fallback
3. **Keep the multi-pass verification logic** - Prevents false negatives
4. **Maintain proxy fallbacks** - Handles TikTok blocking
5. **Test with both live AND offline users** before deploying
6. **Run multiple consistency tests** (at least 10 rapid checks)

## Architecture Diagram

```
Request: /fc/TLC.php?user=gabbyvn3
           │
           ▼
    ┌──────────────┐
    │ Validate     │
    │ Username     │
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │ Check #1:    │──► LIVE? ──► Return immediately
    │ Direct Fetch │
    └──────┬───────┘
           │ Not Live/Failed
           ▼
    ┌──────────────┐
    │ Check #2:    │──► LIVE? ──► Return immediately  
    │ Diff UA      │
    └──────┬───────┘
           │ Not Live/Failed
           ▼
    ┌──────────────┐
    │ Check #3:    │──► LIVE? ──► Return immediately
    │ Via Proxy    │
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │ Consensus:   │
    │ Offline if   │
    │ all checks   │
    │ agree        │
    └──────────────┘
```

## References

- TikTok SIGI_STATE JSON structure
- TikTok __UNIVERSAL_DATA_FOR_REHYDRATION__ format
- Open Graph meta tag specifications
- TikTok Live Connector library patterns
