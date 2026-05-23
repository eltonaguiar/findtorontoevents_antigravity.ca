# VR Cross-Platform Test — Reference

## Device Configurations

### Desktop (Chrome)
- **Viewport:** 1920x1080
- **User Agent:** Default Chrome
- **Input:** keyboard (WASD, 0-9, M, Tab, F1, Escape), mouse (look-controls)

### Mobile (iPhone 14 Pro)
- **Viewport:** 393x852 (portrait), 852x393 (landscape)
- **User Agent:** `Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1`
- **Flags:** `isMobile: true`, `hasTouch: true`
- **Input:** touch (joystick, tap, swipe)

### Meta Quest 3
- **Viewport:** 1832x1920
- **User Agent:** `Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) OculusBrowser/32.0.0.0.0 SamsungBrowser/4.0 Chrome/120.0.0.0 VR Safari/537.36`
- **Input (cannot be fully simulated in headless):**
  - Controllers: left stick (move), right stick (snap turn + teleport), trigger (select)
  - Hand tracking: pinch gesture
  - Gaze cursor: fuse timer (1500ms dwell = click)

## Key DOM Selectors

| Selector | Purpose |
|---|---|
| `a-scene` | Main A-Frame scene |
| `#rig` / `#camera-rig` | Camera rig entity |
| `a-camera` | Camera entity |
| `#left-hand` / `#left-ctrl` | Left controller |
| `#right-hand` / `#right-ctrl` | Right controller |
| `#left-hand-tracking` | Left hand tracking entity |
| `#right-hand-tracking` | Right hand tracking entity |
| `a-camera a-ring[cursor]` | Gaze cursor ring |
| `#teleport-floor` | Teleport surface |
| `#teleport-indicator` | Teleport landing marker |
| `#vr-nav-menu-2d` | Desktop nav menu overlay |
| `#vr-nav-floating-btn` | Nav menu floating button |
| `#vr-nav-button` | 3D nav menu sphere (VR) |
| `.clickable` | Raycaster-targetable elements |
| `[zone-link]` | A-Frame zone portal components |
| `#loading` / `#mobile-loading` | Loading screens |
| `#help-overlay` | F1 help overlay |
| `#joystick` / `#joystick-knob` | Mobile joystick |
| `.mobile-action-btn` | Mobile action buttons |
| `.mobile-zone-card` | Mobile zone menu cards |
| `#mobile-zone-menu` | Mobile zone menu container |
| `#orientation-warning` | Portrait orientation warning |
| `#vr-mode-toggle` | Simple/Advanced mode toggle |

## Global JavaScript APIs

| API | Availability | Description |
|---|---|---|
| `window.VRControllerSupport.isVR()` | Hub pages | Whether in VR mode |
| `window.VRControllerSupport.getActiveInput()` | Hub pages | Current input: keyboard/controllers/hands/gaze |
| `window.VRControllerSupport.isTeleporting()` | Hub pages | Whether teleport arc is active |
| `window.toggleNavMenu()` | All pages | Toggle nav menu |
| `window.closeNavMenu()` | All pages | Close nav menu |
| `window.MobileDetect.isMobile()` | Hub pages | Mobile detection result |
| `window.VRModeToggle.mode` | All pages | Current mode: simple/advanced |
| `window.VRModeToggle.setMode(m)` | All pages | Set mode |
| `window.AFRAME.version` | All pages | A-Frame version string |
| `window.AFRAME.components` | All pages | Registered A-Frame components |

## Headless Testing Limitations

Playwright runs in headless Chromium which **cannot**:
- Enter WebXR immersive mode (requires real headset)
- Provide real gamepad input (Gamepad API returns empty array)
- Run hand tracking (requires Quest hardware)
- Play audio (AudioContext suspended by default)
- Access SpeechSynthesis (TTS not available)

**What we CAN verify in headless:**
- DOM elements created for controllers, hand tracking, gaze cursor
- Scripts loaded without errors
- A-Frame components registered
- Raycaster configured correctly
- Keyboard/mouse interactions work
- Touch simulation works
- Teleport surface + indicator DOM present
- Nav menu opens/closes
- Zone links resolve to valid URLs
- No critical JS errors during initialization

## All VR Pages

```
/vr/                    — VR Hub (main)
/vr/mobile-index.html   — Mobile Hub
/vr/events/             — Events Explorer
/vr/movies.html         — Movie Theater
/vr/movies-tiktok.html  — Movies TikTok Mode
/vr/creators.html       — Creators Live Lounge
/vr/stocks-zone.html    — Stock Trading Floor
/vr/weather-zone.html   — Weather Observatory
/vr/wellness/           — Wellness Garden
/vr/tutorial/           — Tutorial
```

## Running All Pages at Once

To test every VR page sequentially:

```bash
for page in /vr/ /vr/events/ /vr/movies.html /vr/creators.html /vr/stocks-zone.html /vr/weather-zone.html /vr/wellness/ /vr/tutorial/; do
  VR_PAGE=$page npx playwright test tests/vr_cross_platform_full.spec.ts
done
```

PowerShell:

```powershell
$pages = @("/vr/", "/vr/events/", "/vr/movies.html", "/vr/creators.html", "/vr/stocks-zone.html", "/vr/weather-zone.html", "/vr/wellness/", "/vr/tutorial/")
foreach ($p in $pages) {
  $env:VR_PAGE = $p
  npx playwright test tests/vr_cross_platform_full.spec.ts
}
```
