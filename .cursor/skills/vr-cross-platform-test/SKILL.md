---
name: vr-cross-platform-test
description: Fully test any VR page across three user types — desktop keyboard/mouse (Chrome), mobile touch user, and Meta Quest 3 (controllers, hand tracking, gaze cursor). Verifies A-Frame scene loads, zero critical JS errors, input-specific interactions, navigation menu, zone links, and accessibility per modality. Use when the user asks to test a VR page, verify VR cross-platform, test Quest controller support, test mobile VR, or run a comprehensive VR input test.
---

# VR Cross-Platform Test

Test any VR page across **three user types** with input-method-specific assertions:

| User Type | Viewport | Input | Key Checks |
|---|---|---|---|
| **Desktop** (Chrome) | 1920x1080 | Keyboard + mouse | WASD, shortcuts 0-9, M/Tab menu, F1 help, mouse look |
| **Mobile** (iPhone 14 Pro) | 393x852 | Touch | Joystick, tap targets >= 44px, orientation warning, touch look-controls |
| **Meta Quest 3** | 1832x1920 | Controllers / hands / gaze | Laser pointers, thumbstick locomotion, snap turn, teleport, gaze fuse cursor, hand-tracking entities |

## Quick Start

### Run against local server

```bash
npx playwright test tests/vr_cross_platform_full.spec.ts
```

### Run against remote

```bash
VERIFY_REMOTE=1 npx playwright test tests/vr_cross_platform_full.spec.ts
```

### Test a specific page

```bash
VR_PAGE=/vr/movies.html npx playwright test tests/vr_cross_platform_full.spec.ts
```

### Test a specific user type only

```bash
npx playwright test tests/vr_cross_platform_full.spec.ts -g "Desktop"
npx playwright test tests/vr_cross_platform_full.spec.ts -g "Mobile"
npx playwright test tests/vr_cross_platform_full.spec.ts -g "Quest 3"
```

## Configuration

| Env Variable | Default | Description |
|---|---|---|
| `VERIFY_REMOTE` | (unset) | Set to `1` to test `https://findtorontoevents.ca` |
| `VR_PAGE` | `/vr/` | VR page path to test (e.g. `/vr/movies.html`) |
| `VR_TIMEOUT` | `60000` | Navigation timeout (ms) |
| `VR_WAIT` | `6000` | Post-load wait for A-Frame init (ms) |

## What Each Section Tests

### Section 1: Shared (all user types)
- Page returns HTTP 200
- Zero critical JS errors (filters non-critical: CORS, WebXR headless, Gamepad API, AudioContext, etc.)
- A-Frame `<a-scene>` loads (`hasLoaded === true`)
- Title contains "VR" or zone-relevant keyword
- No JS file 404s
- Loading screen hides after init

### Section 2: Desktop (keyboard/mouse)
- WASD movement controls enabled on camera
- Keyboard shortcuts (1-6 zone jump, 0 center, F1 help, Escape close)
- Nav menu opens with M/Tab, closes with Escape
- Mouse look-controls enabled
- Gaze cursor ring attached to camera
- Zone portals have `.clickable` class
- Enhancement JS modules loaded

### Section 3: Mobile (touch)
- Touch look-controls enabled on camera
- Joystick + action buttons exist
- Tap targets >= 44px
- Orientation warning in portrait
- Zone menu opens on tap, closes on X tap
- Mobile detection script loaded
- Mobile-specific UI elements present

### Section 4: Quest 3 (controllers / hands / gaze)
- Left/right laser-controls entities (`#left-hand`, `#right-hand`)
- Raycaster configured for `.clickable`
- Gaze cursor with fuse enabled (1500ms)
- Hand-tracking entities created (`#left-hand-tracking`, `#right-hand-tracking`)
- Teleport surface + indicator exist
- Controller-support.js + vr-controls.js loaded
- VR-mode-ui enabled on scene
- zone-link / teleport-surface / look-at-camera components registered
- Simulated gamepad loop runs without crash
- `VRControllerSupport` global API available

## VR Pages Available

| Page | Path |
|---|---|
| VR Hub | `/vr/` |
| Mobile Hub | `/vr/mobile-index.html` |
| Events | `/vr/events/` |
| Movies | `/vr/movies.html` |
| Creators | `/vr/creators.html` |
| Stocks | `/vr/stocks-zone.html` |
| Weather | `/vr/weather-zone.html` |
| Wellness | `/vr/wellness/` |
| Tutorial | `/vr/tutorial/` |
| Movies TikTok | `/vr/movies-tiktok.html` |

## Non-Critical Error Patterns (filtered out)

These errors are expected in headless Playwright and do not indicate real bugs:

- `net::`, `CORS`, `Failed to fetch`, `NetworkError` — network in headless
- `immersive-vr`, `navigator.xr`, `NotAllowedError` — WebXR requires real headset
- `getGamepads` — Gamepad API not available in headless
- `AudioContext`, `play()`, `SpeechSynthesis` — media restrictions
- `ServiceWorker`, `ResizeObserver` — benign browser warnings
- `Script error` — cross-origin script errors

## When Tests Fail

| Failure | Likely Cause | Fix |
|---|---|---|
| Critical JS error | Broken script or missing dependency | Check console output; use **fix-toronto-events** skill |
| A-Frame scene not loaded | CDN down or script blocked | Verify aframe CDN returns 200; check `.htaccess` |
| Missing controller entities | `controller-support.js` not loaded | Check script `src` paths; deploy if missing |
| Gaze cursor missing | Camera entity misconfigured | Inspect `<a-camera>` for `<a-ring cursor>` child |
| Mobile touch not enabled | `look-controls` missing `touchEnabled` | Check mobile page camera attributes |
| Teleport missing | `vr-controls.js` not loaded | Verify script tag exists; check 404s |
| 404 on JS file | File not deployed | Run `python tools/deploy_vr.py` |

## Files

- **Playwright spec:** `tests/vr_cross_platform_full.spec.ts`
- **Reference:** [reference.md](reference.md)
