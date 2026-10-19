# Weather Jacket Pages — /jacket & /doineedajacket (2026-10-12)

## What was built

- **`/weather/`** — Enhanced weather page with jacket verdict, Vanta.js dynamic background, rain probability, sunset/sunrise, postal/ZIP lookup, geolocation
- **`/jacket/`** — Redirects to `/weather/`
- **`/doineedajacket/`** — Redirects to `/weather/`

## What changed

### New files
- `weather/index.html` — Full weather page
- `jacket/index.html` — Meta-refresh + JS redirect to `/weather/`
- `doineedajacket/index.html` — Meta-refresh + JS redirect to `/weather/`
- `tests/weather_page.spec.ts` — Rewritten Playwright tests (4 tests)

### Modified files
- `tools/serve_local.py` — Added routes for `/weather/`, `/jacket/`, `/doineedajacket/`
- `tools/deploy_to_ftp.py` — Added `deploy_weather_jacket()` + `--weather-only` flag

## Features

1. **Jacket verdict** — Large card with emoji, YES/Maybe/NO title, and detailed reason based on feels-like temp, wind chill, and rain
2. **Rain probability** — Percentage bar + human-readable description
3. **Sunny day check** — Cloud cover + condition analysis
4. **Sun times** — Sunrise, sunset, UV index, daylight remaining
5. **Last updated** — API local timestamp ("Oct 12, 3:56 AM Toronto local")
6. **Location detection** — Browser geolocation + Nominatim reverse geocode, area label displayed
7. **Postal/ZIP lookup** — Canadian FSA lookup table, US ZIP via Zippopotam, city search via Open-Meteo geocoding
8. **Dynamic weather background** — HTML5 canvas particle engine:
   - Rain: fast-falling angled drops
   - Snow: drifting snowflakes with sway physics
   - Thunderstorm: rain + random lightning bolts with flash
   - Fog: floating radial-gradient mist layers
   - Clear day: warm sun glow + golden ray particles
   - Clear night: cool moon glow + twinkling stars + dark vignette
   - Cloudy: drifting elliptical cloud blobs
   - Day/night sky gradients: bright blue day skies vs dark navy night skies (driven by Open-Meteo `is_day` flag)
   - Vanta.js 3D mesh loads async as optional enhancement (50% opacity behind canvas)
9. **7-day forecast** — With precipitation probability
10. **24-hour hourly strip** — With rain probability per hour
11. **Weather alerts** — Extreme cold, heat, wind, UV
12. **Speech synthesis** — "Listen" button reads the full weather summary

## Bug fixed
- Open-Meteo returns naive local ISO times. The original page used `new Date(iso).toLocaleTimeString({timeZone:'America/Toronto'})` which double-shifted times (showed sunset as 2:40 PM instead of 6:40 PM). Fixed by parsing the ISO string directly.

## Verification
- Playwright: 4/4 tests pass (`npx playwright test tests/weather_page.spec.ts`)
- Weather loads, verdict renders, sunset correct, redirects work, postal lookup works

## Deploy
```
python tools/deploy_to_ftp.py --weather-only
```
