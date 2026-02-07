# VR Hub — Enhancement Plan (Post-Quest 3 Testing)

Based on real Meta Quest 3 user testing feedback. Prioritized by severity.

---

## CRITICAL — Quest 3 Broken Experience

### 1. Quest Controller Support & Teleportation (ALL ZONES)
**Problem:** Quest 3 controllers don't work for interaction or movement. User is stuck in place. Only gaze cursor works (eye-stare-to-click), no laser pointer from controllers, no thumbstick movement, no teleportation.

**Root Cause:** Camera rig only has `look-controls` + `wasd-controls` (keyboard-only). No `laser-controls`, no `hand-tracking-controls`, no `movement-controls` or `blink-controls` for thumbstick locomotion. Weather zone has hand entities but other zones don't.

**Fix:**
- Add `aframe-extras` script to all zones (provides `movement-controls`, `blink-controls`)
- Add left/right hand entities with `laser-controls` + `hand-tracking-controls` to camera rig
- Add `blink-controls` for teleportation (shows arc + landing circle)
- Add `movement-controls` as fallback for thumbstick continuous movement
- Keep gaze cursor as fallback for headset-only users
- Keep WASD for desktop users

**Files:** ALL zone HTML files (`index.html`, `creators.html`, `events/index.html`, `movies.html`, `weather-zone.html`, `wellness/index.html`, `stocks-zone.html`)

**Priority:** CRITICAL — Without this, Quest 3 is unusable.

---

### 2. VR Controller Testing / Tutorial Area
**Problem:** User doesn't know what works and what doesn't. No way to verify controller setup.

**Fix:**
- Create `vr/tutorial.html` — a dedicated testing zone
- Step-by-step guided tutorial:
  1. "Look around" — verify head tracking
  2. "Point your controller at this target" — verify laser pointer
  3. "Press trigger to click" — verify button mapping
  4. "Push thumbstick forward" — verify movement
  5. "Push thumbstick to aim, release to teleport" — verify blink
  6. "Pinch your fingers" — verify hand tracking
  7. "Press menu button" — verify nav menu
- Show green checkmarks for working features, red X for broken
- Suggest alternatives for non-working features
- Link from hub as a "?" or "Tutorial" portal

**Files:** New `vr/tutorial.html`, update `vr/index.html` to add portal

**Priority:** HIGH — Essential for onboarding.

---

### 3. Menu Button → Zone Navigation Overlay
**Problem:** Pressing the Quest menu button should show a navigation menu specific to the current zone with an easy exit option.

**Current State:** `nav-menu.js` exists and handles this, but it's missing from `creators.html`. It uses gamepad polling for the menu button (button index 14).

**Fix:**
- Add `<script src="/vr/nav-menu.js"></script>` to creators.html (already in other zones)
- Verify nav-menu.js works in VR mode (currently 2D overlay — may be occluded in VR)
- Add 3D in-VR menu as fallback (floating panel at fixed position relative to camera)
- Zone-specific quick actions (e.g., "Next Page", "Filter Live", "Back to Hub")

**Files:** `vr/creators.html`, possibly `vr/nav-menu.js` updates

**Priority:** HIGH

---

## HIGH — Zone-Specific Fixes

### 4. Creators Zone — Card Accessibility & Live Navigation
**Problem:** Cards form a curved wall at radius 7m — too far to reach. Live creator was visible but user couldn't navigate to them. No clear "Go to Live Creator" button.

**Fix:**
- Reduce card wall radius from 7m to 4-5m (bring cards closer)
- Add floating "GO TO LIVE" button that spawns when any creator is live:
  - Large, pulsing, always visible near the camera
  - Click to auto-navigate/teleport to the live creator's card
  - Shows creator name + platform
- Add "LIVE NOW" section at eye level (y=1.6) directly in front of camera
- Make cards respond to laser pointer (already `.clickable`, just needs controller raycaster)

**Files:** `vr/creators.html`

**Priority:** HIGH

---

### 5. Creators Zone — YouTube Embeds for Non-Live Creators
**Problem:** When clicking a non-live creator, user only sees bio/accounts. No content preview.

**Current State:** Code already has `getEmbedUrl()` and YouTube latest video fetching via `youtube_latest.php`. The detail overlay shows stream previews for live creators and YouTube recent videos for offline creators.

**Fix:**
- Verify `youtube_latest.php` endpoint exists and works
- Make the YouTube embed more prominent in the detail overlay
- Add a "Watch Content" section with latest videos when creator is offline
- Show thumbnail grid of recent videos
- Clicking a video should play it in an in-VR panel (not open browser)

**Files:** `vr/creators.html`, possibly `favcreators/public/api/youtube_latest.php`

**Priority:** HIGH

---

### 6. Movies Zone — In-VR Playback (Don't Exit VR)
**Problem:** Clicking a movie opens the browser, exiting VR mode. Movies should play on the cinema screen inside VR.

**Root Cause:** Movie links use `window.open()` or `<a href>` which opens a new browser tab, pulling the user out of the VR session.

**Fix:**
- YouTube trailers should embed via `<a-video>` entity on the cinema screen (A-Frame video component)
- Use YouTube iframe embed with `?autoplay=1&mute=1` inside a DOM overlay panel
- OR use a transparent plane with video texture mapped to the cinema screen
- Add play/pause/next controls as 3D buttons near the screen
- Queue system: click poster → adds to queue → plays on screen

**Files:** `vr/movies.html`

**Priority:** HIGH

---

### 7. Movies Zone — Controller Navigation
**Problem:** Only eye gaze works in the movie theatre. Controller laser pointer doesn't interact with posters or screen.

**Fix:** Same as Enhancement #1 — add laser-controls and hand-tracking-controls to the movies camera rig. Ensure poster `.clickable` class works with controller raycaster.

**Files:** `vr/movies.html`

**Priority:** HIGH (bundled with #1)

---

### 8. Weather Observatory — Session Timeout / Kickout
**Problem:** User gets kicked out of VR after a few seconds in the weather zone.

**Possible Causes:**
- `webxr` config mismatch: weather zone uses `webxr="optionalFeatures: dom-overlay, layers"` (no quotes, no hand-tracking) while other zones use the full quoted array syntax
- Passthrough toggle function calls `navigator.xr.requestSession('immersive-ar')` which creates a NEW session, conflicting with A-Frame's managed session
- Missing `referenceSpaceType: local-floor` (other zones have it, weather doesn't)
- `aframe-extras` loaded in weather zone may conflict with A-Frame 1.6.0

**Fix:**
- Standardize WebXR config across all zones: `webxr="optionalFeatures: ['dom-overlay', 'hand-tracking', 'local-floor', 'hit-test', 'layers']; referenceSpaceType: local-floor"`
- Remove the manual `navigator.xr.requestSession()` call — let A-Frame manage the session
- Replace custom passthrough toggle with A-Frame's built-in passthrough detection
- Test with and without aframe-extras to isolate conflicts

**Files:** `vr/weather-zone.html`

**Priority:** HIGH

---

### 9. Events Explorer — Declutter UI
**Problem:** Buttons feel cluttered and overwhelming. Needs better organization.

**Fix:**
- Group filters into collapsible sections:
  - "Categories" (expandable pill row)
  - "Time" (Today / This Week / This Month)
  - "Sort" (Date / Popular / Near Me)
- Move pagination to bottom rail only (remove top duplicate)
- Use a sidebar panel that slides in/out instead of fixed top bar
- In VR: filters as a floating panel to the left, events on the right
- Add a "Quick Filter" row with just the top 5 categories

**Files:** `vr/events/index.html`

**Priority:** MEDIUM

---

## MEDIUM — New Features

### 10. Multiplayer Presence & Voice Chat
**Problem:** Can't see other users or communicate with them.

**Current State:** `presence.js` only tracks tabs on same browser (localStorage). Shows "X users online" badge but no avatars, no voice, no chat.

**Implementation Plan:**
- **Phase A (Quick):** Server-Sent Events (SSE) or polling endpoint to share presence across devices. Show floating name tags for other users in each zone.
- **Phase B (Medium):** WebSocket server for real-time position sync. Floating avatar heads that move with other users.
- **Phase C (Full):** WebRTC for spatial voice chat. Proximity-based audio. Push-to-talk via controller button.

**Tech Stack:**
- `networked-aframe` library for avatar sync
- `easyrtc` or `janus-gateway` for WebRTC voice
- Small Node.js WebSocket signaling server

**Files:** New server component, updates to all zone files

**Priority:** MEDIUM — Great feature but significant server-side work.

---

### 11. Virtual Downtown Toronto Tour (Google Earth/Maps-like)
**Problem:** User wants to virtually walk/fly through downtown Toronto.

**Implementation Options:**

**Option A: 360 Panorama Tour** (Easiest, 1-2 days)
- Fetch Google Street View panoramas for key Toronto locations
- Navigate between them by clicking arrow markers
- Overlay event hotspots at real-world locations
- Works well in VR with head tracking

**Option B: 3D City Tiles** (Most immersive, 1-2 weeks)
- Google Maps 3D Tiles API or Cesium 3D Tiles
- Photogrammetric 3D model of Toronto buildings
- Fly/walk through at street level
- Requires API key + GPU-intensive rendering

**Option C: Passthrough AR + GPS** (Quest 3 native)
- Use Quest 3 passthrough camera
- Overlay VR markers at GPS coordinates of real venues
- Walk through real Toronto with floating VR event info
- Requires being physically in Toronto

**Recommended:** Start with Option A (360 panoramas), add Option B later.

**Files:** New `vr/toronto-tour.html`, new hub portal

**Priority:** MEDIUM — Flagship feature but complex.

---

### 12. Customizable Movie Theatre Environments
**Problem:** User wants to change the theatre environment (e.g., IMAX, outdoor drive-in, home theatre).

**Fix:**
- Add 3-4 preset environments selectable via menu button:
  1. Classic Cinema (current dark room)
  2. IMAX Theatre (curved screen, stadium seating)
  3. Drive-In (outdoor, starry sky, car hood view)
  4. Living Room (couch, TV, casual)
- Change sky, lighting, screen geometry, and ambient audio per preset
- Save preference to localStorage

**Files:** `vr/movies.html`

**Priority:** MEDIUM

---

## LOW — Polish & Quality of Life

### 13. Universal Navigation Bar (In-VR)
**Problem:** No consistent way to navigate between zones while in VR across all pages.

**Fix:** `nav-menu.js` already provides this. Ensure it's loaded in ALL zone pages and that the 3D menu works with controller laser pointer (not just keyboard).

**Files:** All zone HTML files

**Priority:** LOW (partially done)

---

### 14. Accessibility — Seated Mode & Comfort Options
**Fix:**
- Option to switch between standing and seated VR modes
- Adjustable camera height
- Comfort vignette during movement (reduces motion sickness)
- Snap turning option (45/90 degree turns via controller)

**Files:** Shared component, all zones

**Priority:** LOW

---

### 15. Audio System
**Problem:** Pixabay CDN blocks hotlinking. Weather zone audio may not load.

**Fix:**
- Host audio files locally in `vr/assets/`
- Add ambient audio to each zone (subtle, toggleable)
- Spatial audio for live creators (hear stream audio getting louder as you approach)

**Files:** New `vr/assets/` directory, all zone files

**Priority:** LOW

---

## Implementation Order

| # | Enhancement | Est. Effort | Status |
|---|-------------|-------------|--------|
| 1 | Quest Controller + Locomotion (all zones) | 3-4 hours | ✅ DONE |
| 2 | Tutorial/Testing Area | 2-3 hours | PENDING |
| 3 | Menu Button Nav Overlay | 1 hour | ✅ DONE |
| 4 | Creators — Live Navigation + Quick-Join | 1-2 hours | ✅ DONE |
| 5 | Creators — YouTube Embeds | 1-2 hours | ✅ DONE |
| 6 | Movies — In-VR Playback | 3-4 hours | ✅ DONE |
| 7 | Movies — Controller Nav | Bundled with #1 | ✅ DONE |
| 8 | Weather — Session Fix | 1-2 hours | ✅ DONE |
| 9 | Events — Declutter UI | 2-3 hours | PENDING |
| 10 | Multiplayer & Voice | 1-2 weeks | FUTURE |
| 11 | Toronto Tour | 1-2 weeks | FUTURE |
| 12 | Theatre Environments | 2-3 days | FUTURE |
| 13 | Universal Nav Bar | 1 hour | ✅ DONE |
| 14 | Accessibility (comfort vignette + F1 help) | 2-3 hours | ✅ DONE |
| 15 | Audio System (spatial hover/click/enter cues) | 1-2 hours | ✅ DONE |
| 16 | Stocks Zone Overhaul (A-Frame 1.6, rig, controls) | 30 min | ✅ DONE |
| 17 | Hub Zone Tooltips (floating descriptions on hover) | 30 min | ✅ DONE |
| 18 | Hub Portal Loading Feedback (flash + spinner overlay) | 20 min | ✅ DONE |
| 19 | Stocks Interactive Pedestals + Detail Popup | 1 hour | ✅ DONE |
| 20 | Tutorial Zone Controller Support (laser + locomotion) | 20 min | ✅ DONE |
| 21 | Movies Cinema Theme Selector (Classic/IMAX/Drive-In) | 30 min | ✅ DONE |
| 22 | Weather Interactive Forecast Cards + Detail Popup | 30 min | ✅ DONE |
| 23 | Mobile-Friendly: Shared vr-mobile.js (joystick, topbar, action bar, responsive CSS) | 1 hour | ✅ DONE |
| 24 | Mobile-Friendly: Updated mobile-detect.js (prompt vs hard-redirect) | 15 min | ✅ DONE |
| 25 | Mobile-Friendly: Updated mobile-index.html zone links + added Tutorial/Hub cards | 15 min | ✅ DONE |

---

## Shared VR Controller Module

To avoid duplicating controller setup across 7+ zone files, create a shared `vr/vr-controls.js` that:

1. Registers `vr-locomotion` component (teleport + thumbstick + snap turn)
2. Adds controller entities to the camera rig automatically
3. Handles controller button mapping (trigger=click, grip=grab, menu=nav, thumbstick=move/teleport)
4. Provides fallback gaze cursor for headset-only users
5. Detects input capabilities and adapts UI accordingly

Each zone file just needs: `<script src="/vr/vr-controls.js"></script>`

---

*Last updated: 2026-02-07 — Session 4: Zone tooltips, spatial audio, stock pedestals+popup, tutorial controllers, portal loading, cinema themes, weather forecast cards, mobile-friendly handling*
