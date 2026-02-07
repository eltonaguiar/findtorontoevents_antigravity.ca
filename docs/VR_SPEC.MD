# VR Spec — findtorontoevents.ca

> Immersive WebXR experience built on **A-Frame 1.6.0**, optimized for Meta Quest 3 with full desktop fallback.

## Architecture

All VR content lives under `/vr/`. Shared modules (`controller-support.js`, `nav-menu.js`, `vr-controls.js`, `presence.js`) provide consistent input handling, navigation, and presence tracking across every zone. Entry point is the **VR Hub** (`/vr/index.html`).

### Input Methods (all zones)

| Method | Controls |
|---|---|
| **Desktop** | Mouse look, WASD movement, keyboard shortcuts |
| **Quest Controllers** | Laser pointers, left thumbstick locomotion, right thumbstick snap-turn / teleport |
| **Hand Tracking** | Pinch-to-select gesture |
| **Gaze Cursor** | 1.5 s fuse timer auto-click (fallback when no controllers) |

A global nav menu (M / Tab / Menu button) is available on every page with zone links, ambient music player (SomaFM), and a clock.

---

## Zones

### 1. VR Hub

Central starfield environment with 6–7 zone portals arranged in a circle around a rotating-ring platform. Click-to-teleport floor. Keyboard shortcuts 1–6 jump directly to zones; 0 returns to center.

### 2. Events Explorer (`/vr/events/`)

Browse 1 000+ Toronto events on a curved card wall (radius 7 m, 4 columns, 12 per page).

- **Data:** fetched from `/events.json`
- **Filters:** 10 category pills (Arts, Music, Nightlife, Sports, etc.) + time-period pills (Today, Tomorrow, Weekend, Week, Month)
- **Cards:** title, date, location, price, category badge, source — color-coded by category; past events flagged red, free events highlighted green
- **Detail overlay:** full description, tags, external link
- **Navigation:** arrow-key or gaze pagination

### 3. Movie Theater (`/vr/movies.html`)

Cinema environment with seats, a 12×7-unit main screen, and poster walls (Movies vs TV Shows).

- **Data:** fetched from MOVIESHOWS3 / MOVIESHOWS2 API (`get-movies.php`)
- **Playback:** YouTube IFrame API; auto-advances through a queue. Desktop uses a 2-D overlay player; VR uses WebXR DOM Overlay for in-headset playback.
- **Interaction:** hover a poster to reveal instant-play / add-to-queue popup. "Now Playing" bar shows current trailer and queue count.
- **Filters:** All / Movies / TV Shows. Poster frames are cyan (movies) or purple (TV).

### 4. Movies TikTok Mode (`/vr/movies-tiktok.html`)

Full-screen vertical-scroll feed of movie trailers (Intersection Observer lazy-load, scroll-snap). Includes Like, Save, Queue, Share, Find Similar actions; filter menu (type, genre, timeline, rating); auto-play with 5 s countdown. Experimental VR toggle.

### 5. FavCreators Live Lounge (`/vr/creators.html`)

Curved card wall of tracked creators with live / offline sections.

- **Data:** creator list from `/fc/api/get_my_creators.php`; live status from `get_streamer_status.php`; latest YouTube via `youtube_latest.php`
- **Live indicators:** pulsing red dot, "LIVE" badge, stream title, viewer count, red-glow card border
- **Platform filters:** TikTok, Twitch, Kick, YouTube, Instagram — each with brand colors
- **Detail overlay:** bio, stream-preview embed (Twitch / Kick / YouTube), recent videos, account links
- **"JOIN LIVE" button** floats when any creator goes live
- Auto-refresh every 60 s; 12 creators per page with pagination

### 6. Stock Ideas Trading Floor (`/vr/stocks-zone.html`)

Trading-floor office environment with a central desk, Top Gainers / Top Losers panels, and a scrolling news ticker. Simulated real-time price updates every 5 s for 8 tickers (AAPL, MSFT, NVDA, TSLA, AMZN, GOOGL, SPY, QQQ). Color-coded green / red / yellow. Ambient trading-floor audio. Ready for live API integration.

### 7. Weather Observatory (`/vr/weather-zone.html`)

Glass-walled observatory pulling real-time Toronto weather from the **Open-Meteo API**.

- **Panels:** temperature, condition, wind, humidity, UV index, 7-day forecast, atmosphere / comfort meter
- **"Real Feel":** wind-chill + humidex using Environment Canada formulas, plus clothing advice
- **Weather alerts:** extreme cold, heat, wind advisories
- **Particle systems:** rain, snow, lightning — optimized for Quest 3 (50 rain / 40 snow particles)
- **Seasonal effects:** spring petals, summer fireflies, autumn leaves, winter snow
- **Manual override buttons:** Clear, Rain, Snow, Storm
- **Passthrough AR toggle** overlays weather data on the real room

### 8. Wellness Garden (`/vr/wellness/`)

Forest environment with interconnected zones:

- **Breathing Sphere:** guided 4-7-8 breathing exercise with color transitions
- **Accountability Coach:** current goal, streak counter, daily check-in
- **Motivational Wall:** rotating quotes with left / right navigation
- **Meditation Spot:** floating orbs in a quiet area
- **Gratitude Tree:** interactive leaves
- Teleport points between zones; keyboard shortcuts 1–5 for quick jumps

### 9. Tutorial (`/vr/tutorial/`)

Seven-step interactive lesson: look around → point & click → move → teleport → snap turn → open menu → navigate to Hub. Progress dots track completion; input-method auto-detection.

---

## Shared Systems

| Module | Purpose |
|---|---|
| `controller-support.js` | Quest 3 laser pointers, thumbstick locomotion, snap turn, hand-tracking fallback, controller guide popup |
| `nav-menu.js` | Global menu overlay with zone links, current-zone indicator, ambient music, clock |
| `vr-controls.js` | Locomotion component, teleport arc visualization, rig height correction, gaze cursor |
| `presence.js` | Cross-tab user counter via BroadcastChannel + localStorage heartbeats |
| `scene-enhancements.js` | Set 8: 3D scene polish — portal particles, hover pulse, energy waves, screen glow, dust motes, price sparks, fireflies, sky tint, ambient motes, data badges |
| `completeness.js` | Set 9: Production readiness — session continuity, error recovery, accessibility, onboarding, performance LOD, calendar minimap, watch history, forecast timeline, device adaptive, changelog |
| `interaction.js` | Set 10: Immersive Interaction — events sort/save, creators follow, theater mode, movie ratings, 3D stock charts, watchlist, meditation timer, stats dashboard, achievements, sound cues |
| `personalization.js` | Set 11: Personalization & Social — theme customizer, named playlists, event sharing, event notes, multi-city weather, creator history, notification center, stock portfolio, cross-zone pinboard, hub quick-launch |
| `advanced-ux.js` | Set 12: Advanced UX & Immersion — data export/import, mini-map radar, dynamic weather FX, photo mode, events countdown, movie autoplay queue, creator spotlight, voice commands, usage analytics, spatial ambient audio |
| `comfort-intelligence.js` | Set 13: Comfort & Intelligence — multi-language i18n, zen mode, smart recommendations, custom hotkeys, zone transitions, daily challenges, comfort settings v2, content bookmarks, session replay, particle density control |
| `content-depth.js` | Set 14: Content Depth — scratchpad, event RSVP, genre filter, creator comparison, sector map, weather alerts, breathing exercise, news ticker, cross-zone timeline, ambient lighting sync |

## Testing & Deployment

- **Deploy:** `tools/deploy_vr.py` (full) or `tools/deploy_vr_only.py` (quick)
- **Verify:** `tools/verify_vr_remote.py`, `tools/check_vr_deploy.py`
- **Playwright suites:** hub structure, movies, events, creators, Quest controllers, gaze navigation, keyboard/mouse, global menu, comprehensive & deep tests

## Enhancement Status

| ID | Feature | Status |
|---|---|---|
| ENH-001 | Quest controller support | Done |
| ENH-002 | Teleport movement | Done |
| ENH-003 | Weather crash fix | Done |
| ENH-004 | In-VR movie playback (DOM Overlay) | Done |
| ENH-005 | Live creator quick-join button | Done |
| ENH-006 | Area Guide System (G key, TTS narration) | Done |
| ENH-007 | Events Audio Announcements (today/tomorrow/weekend) | Done |
| ENH-008 | Event Preview (inline browser in VR) | Done |
| ENH-009 | Cross-Zone Search (Ctrl+K) | Done |
| ENH-010 | Favorites System (star/save across zones) | Done |
| ENH-011 | Zone Ratings (1-5 stars) | Done |
| ENH-012 | Activity Feed (recent actions) | Done |
| ENH-013 | Content Preloader (prefetch likely zones) | Done |
| ENH-014 | Breadcrumb Navigation | Done |
| ENH-015 | Quick Stats Badge (per-zone live stats) | Done |
| ENH-016 | Share Snapshot (deep-link with state) | Done |
| ENH-017 | Set 5 Social Features (presence, notes, bookmarks, time-theme) | Done |
| ENH-018 | Hub Portal Particle Fountains (zone-themed particles per portal) | Done |
| ENH-019 | Hub Portal Hover Pulse (scale + glow on mouseenter) | Done |
| ENH-020 | Hub Platform Energy Waves (concentric expanding rings) | Done |
| ENH-021 | Movies Screen Glow (color-matched light behind screen) | Done |
| ENH-022 | Movies Dust Motes (floating particles in projector beam) | Done |
| ENH-023 | Stocks Price-Change Sparks (green/red burst on tick) | Done |
| ENH-024 | Wellness Fireflies + Falling Petals (animated nature particles) | Done |
| ENH-025 | Time-of-Day Sky Tint (ambient color shifts by clock) | Done |
| ENH-026 | Ambient Floating Motes (zone-colored luminous dust, all zones) | Done |
| ENH-027 | Hub Portal Data Badges (live stats floating below portals) | Done |
| ENH-028 | Session Continuity (resume last zone on return) | Done |
| ENH-029 | Error Recovery (resilient fetch, offline indicator, retry queue) | Done |
| ENH-030 | Accessibility Layer (ARIA, skip link, reduced motion, high contrast, Alt+A panel) | Done |
| ENH-031 | First-Visit Onboarding (contextual zone tips, auto-dismiss) | Done |
| ENH-032 | Performance LOD (FPS monitor, auto quality, particle toggling) | Done |
| ENH-033 | Events Calendar Minimap (month grid with event density dots) | Done |
| ENH-034 | Movies Watch History (tracked trailers, history panel) | Done |
| ENH-035 | Weather Forecast Timeline (24h hourly temperature bar from Open-Meteo) | Done |
| ENH-036 | Device Adaptive UI (auto-detect Quest/desktop/mobile, scale controls) | Done |
| ENH-037 | What's New Changelog (version-tracked, auto-show on updates) | Done |
| ENH-038 | Events Sort & Save (sort by date/price/name, personal saved list, CSV export) | Done |
| ENH-039 | Creators Follow System (follow/unfollow toggle, badge count) | Done |
| ENH-040 | Movies Theater Mode (dim lights on play, vignette, toggle) | Done |
| ENH-041 | Movies Rating System (5-star per movie, persisted, star HTML) | Done |
| ENH-042 | Stocks 3D Mini-Charts (price history bars as A-Frame entities) | Done |
| ENH-043 | Stocks Watchlist & Alerts (add/remove tickers, threshold alerts) | Done |
| ENH-044 | Wellness Meditation Timer (presets, countdown, session history) | Done |
| ENH-045 | Hub Stats Dashboard (visits, time per zone, bar visualization) | Done |
| ENH-046 | Achievement System (10 unlockable badges, toast notifications) | Done |
| ENH-047 | Ambient Sound Cues (zone entry chimes via Web Audio API, toggleable) | Done |
| ENH-048 | Theme Customizer (5 themes: Neon/Ocean/Forest/Sunset/Midnight, Ctrl+,) | Done |
| ENH-049 | Movies Named Playlists (create/manage/switch, localStorage) | Done |
| ENH-050 | Events Social Share (Twitter, copy link, Web Share API) | Done |
| ENH-051 | Events Personal Notes (per-event notes, badge count, panel) | Done |
| ENH-052 | Weather Multi-City (Toronto/Vancouver/Montreal/Calgary selector) | Done |
| ENH-053 | Creator View History (track views, recently watched panel) | Done |
| ENH-054 | Notification Center (persistent bell, read/unread, clear all) | Done |
| ENH-055 | Stocks Portfolio (simulated buy/sell, P&L tracking, auto-refresh) | Done |
| ENH-056 | Cross-Zone Pinboard (pin items from any zone, global panel) | Done |
| ENH-057 | Hub Quick-Launch Favorites (pinned zone shortcuts on hub) | Done |
| ENH-058 | Data Export/Import (backup all VR data as JSON, restore from file) | Done |
| ENH-059 | Mini-Map Radar (top-down zone map with position marker, canvas rendering) | Done |
| ENH-060 | Dynamic Weather FX (rain/snow/fog particles driven by Open-Meteo WMO codes) | Done |
| ENH-061 | Photo Mode (capture viewport with date/zone watermark, P key shortcut) | Done |
| ENH-062 | Events Countdown Timer (live countdown to next upcoming event) | Done |
| ENH-063 | Movie Autoplay Queue (add/advance queue, auto-toggle) | Done |
| ENH-064 | Creator Spotlight (rotating featured creator, 15s auto-cycle) | Done |
| ENH-065 | Voice Commands (speech recognition, 11 commands, V key shortcut) | Done |
| ENH-066 | Usage Analytics Dashboard (session tracking, zone breakdown, day graph) | Done |
| ENH-067 | Spatial Ambient Audio (zone-specific drone soundscapes, toggleable) | Done |
| ENH-068 | Multi-Language i18n (EN/FR/ES selector, 22 translated UI labels) | Done |
| ENH-069 | Focus/Zen Mode (hide all overlays, Z key toggle, minimal badge) | Done |
| ENH-070 | Smart Recommendations (usage-based "You might like", 3 suggestions) | Done |
| ENH-071 | Custom Hotkeys (user-rebindable shortcuts, visual editor, reset) | Done |
| ENH-072 | Zone Transition Effects (fade/wipe/zoom animations between zones) | Done |
| ENH-073 | Daily Challenge System (deterministic daily tasks, auto-progress tracking) | Done |
| ENH-074 | Comfort Settings V2 (FOV vignette, reduce motion, UI scale slider) | Done |
| ENH-075 | Content Bookmarks (add with tags, search, panel with filter) | Done |
| ENH-076 | Session Replay (action timeline, auto-log clicks/keys, visual timeline) | Done |
| ENH-077 | Particle Density Control (0-200% slider for all particle systems) | Done |
| ENH-078 | Quick Notes Scratchpad (floating sticky note, Ctrl+N toggle, auto-save) | Done |
| ENH-079 | Events RSVP System (attending/interested per event, count badge) | Done |
| ENH-080 | Movies Genre Filter (9 genre tags, multi-select, filter event dispatch) | Done |
| ENH-081 | Creator Comparison (side-by-side stat panel, 2-slot system) | Done |
| ENH-082 | Stocks Sector Map (6-sector bar chart with percentages) | Done |
| ENH-083 | Weather Alerts (severe wind/cold/heat/storm/snow from Open-Meteo) | Done |
| ENH-084 | Wellness Breathing Exercise (inhale/hold/exhale guided cycle, visual circle) | Done |
| ENH-085 | Hub News Ticker (scrolling headline banner, 10 headlines, auto-scroll) | Done |
| ENH-086 | Cross-Zone Timeline (unified chronological view from all data sources) | Done |
| ENH-087 | Ambient Lighting Sync (zone-matched A-Frame light + CSS tint overlay) | Done |
