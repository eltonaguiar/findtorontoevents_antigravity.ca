# Gear Settings Integration Guide

## Overview

This guide explains how to integrate the **Gear Settings modal** (event filtering & source management) into the existing hand-coded `index.html` at `findtorontoevents.ca`. The integration consists of:

1. **Frontend**: Vanilla JS modal + CSS (no React required)
2. **Backend**: PHP API endpoints for persistence when users are logged in
3. **Database**: `user_settings` table to store per-user JSON settings
4. **Event Filtering**: `maxEventsPerDayPerSource` limit with Eventbrite exemption

---

## Step 1: Add Static Assets to `index.html`

In the `<head>` section of your `index.html` (after any existing stylesheets), add:

```html
<!-- Gear Settings Modal Styles -->
<link rel="stylesheet" href="/static/gear-settings-integration.css?v=1">
```

At the bottom of `<body>` (after all other scripts), add:

```html
<!-- Gear Settings Modal Script -->
<script src="/static/gear-settings-integration.js?v=1" defer></script>
```

> **Note:** The `?v=1` query string is for cache-busting. Bump the version whenever you update the files.

---

## Step 2: Ensure the Gear Icon Exists

The JS auto-detects the gear icon using these selectors (in order):

```css
[data-testid="config-button"]
button[aria-label*="settings"]
button[aria-label*="config"]
button[title*="settings"]
button[title*="config"]
button:has-text("⚙️")
a:has-text("⚙️")
button:has-text("Settings")
button:has-text("Config")
```

If your page already has a ⚙️ icon button that matches one of these, the integration will attach automatically.

If **no gear icon is found**, the script will create one automatically and append it to the `<header>`. You can also manually add it:

```html
<button data-testid="config-button" aria-label="Open settings">
  ⚙️
</button>
```

---

## Step 3: Modify `applyThumbnails()` to Respect the Limit

The Gear Settings JS automatically hooks into `window.applyThumbnails()` if it exists. No code changes are required **if** your `applyThumbnails()` accepts an array of events as its argument.

If your `applyThumbnails()` reads from a global variable instead, make this minimal change:

### Before (example):

```javascript
function applyThumbnails() {
  const events = window.__RAW_EVENTS__ || [];
  // ... render logic
}
```

### After:

```javascript
function applyThumbnails(events) {
  const input = events || window.__FILTERED_EVENTS__ || window.__RAW_EVENTS__ || [];
  // ... render logic using `input`
}
```

The Gear Settings script sets `window.__FILTERED_EVENTS__` after applying the `maxEventsPerDayPerSource` filter. If `applyThumbnails` already takes an argument, the script wraps it transparently.

---

## Step 4: Add `data-source` Attributes to Event Cards

For the filter to work, each event card in the DOM (or each event object in `__RAW_EVENTS__`) must expose its source ID.

### Option A: On the event object (recommended)

Ensure each object in `window.__RAW_EVENTS__` has a `source` field:

```javascript
window.__RAW_EVENTS__ = [
  {
    id: "evt-001",
    title: "Jazz Night at the Rex",
    date: "2026-05-01",
    source: "eventbrite",   // <-- required
    // ...
  },
  // ...
];
```

Allowed source IDs (must match `gear-settings-integration.js`):

| Source ID | Name |
|-----------|------|
| `eventbrite` | Eventbrite |
| `ticketmaster` | Ticketmaster |
| `bandsintown` | Bandsintown |
| `meetup` | Meetup |
| `toronto_opendata` | Toronto Open Data |
| `ago` | Art Gallery of Ontario |
| `rom` | Royal Ontario Museum |
| `harbourfront` | Harbourfront Centre |
| `tiff` | TIFF |
| `sportsnet` | Sports Leagues |
| `blogto` | BlogTO |
| `facebook` | Facebook Events |

### Option B: On the DOM element

If filtering must happen after DOM render, add `data-source` to each card:

```html
<div class="event-card" data-source="eventbrite" data-date="2026-05-01">
  ...
</div>
```

> The JS filter primarily works on `window.__RAW_EVENTS__` before rendering. DOM-level `data-source` is not required but can be used for additional client-side filtering if needed.

---

## Step 5: Database Setup

### 5.1 Create the `user_settings` table

Run the SQL file against your database:

```bash
mysql -u your_user -p your_database < /path/to/api/db-schema-user-settings.sql
```

The SQL creates:

- `user_settings` table with `id`, `user_id`, `settings_json`, `created_at`, `updated_at`
- Unique index on `user_id`
- Foreign key to `users(id)` (adjust if your users table uses a different name)
- Trigger to prevent `created_at` mutation on update

### 5.2 Ensure `sessions` table exists

The `check-session.php` and `user-settings.php` endpoints look for a `sessions` table with:

```sql
CREATE TABLE sessions (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  session_id CHAR(64) NOT NULL,
  user_id INT UNSIGNED NOT NULL,
  expires_at DATETIME NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_session_id (session_id)
);
```

If your auth system uses a different session mechanism, update the `getCurrentUserId()` function in `api/user-settings.php` and `api/check-session.php`.

---

## Step 6: Deploy PHP API Endpoints

Copy the following files to your server:

```
api/
├── db-config.php          (your existing DB config)
├── check-session.php      (new / enhanced)
└── user-settings.php      (new)
```

### CORS Configuration

The PHP files already include CORS headers for:

- `https://findtorontoevents.ca`
- `https://www.findtorontoevents.ca`
- `http://localhost`
- `http://localhost:3000`

If your domain differs, edit the `$allowedOrigins` array in both PHP files.

---

## Step 7: How the Persistence Layer Works

### Flow Diagram

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Page Load     │────▶│  localStorage    │────▶│  Render events  │
│                 │     │  fte_gear_settings│    │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌──────────────────┐
│ check-session   │     │ Backend fetch    │
│ /api/check-     │────▶│ (if logged in)   │
│  session.php    │     │ /api/user-       │
│                 │     │  settings.php GET │
└─────────────────┘     └──────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │ Merge: backend   │
                        │ wins over local  │
                        └──────────────────┘
```

### Detailed Flow

1. **On page load**, the JS reads `fte_gear_settings` from `localStorage`.
2. **Async session check**: JS calls `/api/check-session.php`.
3. **If logged in**, JS calls `/api/user-settings.php` (GET) to fetch saved settings.
4. **Merge**: Backend settings override localStorage settings (backend wins).
5. **Merged settings are saved back to localStorage** so they work offline.
6. **Event filtering** is applied to `window.__RAW_EVENTS__` before rendering.

### Save Flow

1. User changes a setting in the modal.
2. Setting is written to `localStorage` immediately.
3. If user is logged in, a **debounced** POST is sent to `/api/user-settings.php` (400ms delay to batch rapid changes).
4. The "Save Now" button immediately triggers both localStorage + backend sync.

---

## Step 8: How the Max-Events Filter Works

### Algorithm

```javascript
const counts = {};
return events.filter((evt) => {
  const key = `${evt.date}__${evt.source}`;

  // 1. Skip disabled sources
  if (!enabledSet.has(evt.source)) return false;

  // 2. Eventbrite exemption
  if (exemptEventbrite && evt.source === "eventbrite") return true;

  // 3. Per-source-per-day limit
  counts[key] = (counts[key] || 0) + 1;
  return counts[key] <= maxEventsPerDayPerSource;
});
```

### Example

Given these settings:

```json
{
  "maxEventsPerDayPerSource": 2,
  "exemptEventbrite": true,
  "enabledSources": ["eventbrite", "ticketmaster"]
}
```

And these events:

| Date | Source | Title |
|------|--------|-------|
| May 1 | eventbrite | Jazz Night |
| May 1 | eventbrite | Comedy Show |
| May 1 | eventbrite | Food Festival |
| May 1 | ticketmaster | Raptors Game |
| May 1 | ticketmaster | Leafs Game |
| May 1 | ticketmaster | Concert |

**Result after filtering:**

- **Eventbrite**: All 3 events shown (exempt)
- **Ticketmaster**: Only "Raptors Game" and "Leafs Game" shown (limit = 2)
- "Concert" is hidden

---

## Step 9: Testing Instructions

### 9.1 Run Playwright Tests

Install dependencies:

```bash
cd /mnt/agents/output/findtorontoevents_swarm
npm install
npx playwright install
```

Run all tests:

```bash
npm test
```

Run specific suites:

```bash
npm run test:events    # events.spec.ts
npm run test:audit     # audit.spec.ts
npm run test:sports    # sports-betting.spec.ts + sports-betting-advanced.spec.ts
```

Debug mode (headed browser):

```bash
npm run test:debug
```

UI mode (interactive test runner):

```bash
npm run test:ui
```

### 9.2 Test the Gear Settings Modal Manually

1. Open `https://findtorontoevents.ca/index.html` in a browser.
2. Click the ⚙️ gear icon (top-right area, or wherever your UI places it).
3. Verify the modal opens with four tabs: **Display**, **Sources**, **Export**, **Advanced**.
4. In **Display**, drag the slider to change "Max events per day per source".
5. Toggle "Exempt Eventbrite from limit" off, then back on.
6. In **Sources**, disable "BlogTO" and close the modal.
7. Refresh the page — verify BlogTO events are hidden and slider value persists.

### 9.3 Test Backend Persistence

1. Log in to the site (ensure `session_id` cookie is set).
2. Open the gear modal, change a setting, click **Save Now**.
3. Open browser DevTools → Network → verify a POST to `/api/user-settings.php` returns `200` with `"success": true`.
4. Clear localStorage (`localStorage.removeItem('fte_gear_settings')`).
5. Refresh the page.
6. Open the modal — your saved settings should reappear (fetched from backend).

### 9.4 Test Guest Mode (No Login)

1. Log out (clear `session_id` cookie).
2. Open the gear modal, change settings.
3. Verify only `localStorage` is written (no POST requests in Network tab).
4. Refresh — settings should persist via `localStorage`.

---

## Step 10: API Reference

### `GET /api/check-session.php`

**Response:**

```json
{
  "loggedIn": true,
  "userId": "42"
}
```

### `GET /api/user-settings.php`

**Requires:** Valid `session_id` cookie.

**Response (success):**

```json
{
  "success": true,
  "data": {
    "settings": { ... },
    "updated_at": "2026-05-01T12:34:56+00:00",
    "source": "database"
  },
  "error": null
}
```

**Response (no saved settings):**

```json
{
  "success": true,
  "data": {
    "settings": { /* defaults */ },
    "updated_at": null,
    "source": "default"
  },
  "error": null
}
```

**Response (unauthorized):**

```json
{
  "success": false,
  "data": null,
  "error": "Unauthorized: valid session required"
}
```

### `POST /api/user-settings.php`

**Requires:** Valid `session_id` cookie + JSON body.

**Request body:**

```json
{
  "maxEventsPerDayPerSource": 3,
  "exemptEventbrite": true,
  "showSourceBadges": true,
  "groupByDate": false,
  "deduplicate": true,
  "enabledSources": ["eventbrite", "ticketmaster", "bandsintown"],
  "calendarExportFormat": "both"
}
```

**Validation rules:**

- `maxEventsPerDayPerSource`: integer, 1–10
- `exemptEventbrite`, `showSourceBadges`, `groupByDate`, `deduplicate`: booleans
- `enabledSources`: array of strings
- `calendarExportFormat`: `"ical" | "google" | "both"`

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Modal doesn't open | Gear icon not found | Add `data-testid="config-button"` to your gear button, or let JS auto-create it |
| Settings don't persist | `localStorage` disabled (private mode) | This is expected; settings won't persist in private/incognito |
| Backend save fails (401) | No valid `session_id` cookie | Ensure your auth flow sets a 64-char hex `session_id` cookie |
| Events not filtered | `__RAW_EVENTS__` missing `source` field | Add `source` property to each event object |
| `applyThumbnails` not called | Function not exposed on `window` | Assign it to `window.applyThumbnails = function(...) {}` |
| CORS errors in console | Origin not in `$allowedOrigins` | Add your domain to the CORS whitelist in the PHP files |
| Horizontal scrollbar on mobile | Modal overflow | The CSS uses `max-width: 100%` with `box-sizing: border-box`; ensure your base styles don't override |

---

## Files Summary

| File | Purpose |
|------|---------|
| `static/gear-settings-integration.js` | Vanilla JS modal + filtering logic |
| `static/gear-settings-integration.css` | Modal styles, animations, theming |
| `api/user-settings.php` | GET/POST settings persistence |
| `api/check-session.php` | Lightweight session validation |
| `api/db-schema-user-settings.sql` | DB table creation SQL |
| `playwright.config.ts` | Test runner configuration |
| `package.json` | Dependencies & test scripts |
| `GEAR_INTEGRATION_GUIDE.md` | This document |
