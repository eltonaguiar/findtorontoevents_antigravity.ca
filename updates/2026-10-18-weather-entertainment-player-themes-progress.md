# Weather page — Entertainment, Player, Themes (progress snapshot)

Status: PAUSED by user request. Local changes are NOT yet deployed to FTP (last deploy was prior to dynamic video/Piped + subtabs). Run `python3 tools/deploy_to_ftp.py --weather-only` to publish.

## Achievements so far (weather/index.html)

1. Moved "Top Entertainment — Most Played" (TV/Movies/Podcasts/Songs) from inline card into the left side (Quick Nav) panel. Tests pass.
2. Added embedded player card (music videos / movie trailers / live radio / top songs) in main container.
   - YouTube playlist param approach replaced with reliable curated video IDs + daily rotation by date + Prev/Next buttons.
   - Live radio via SomaFM/iHeart audio element.
   - Top Songs via Spotify embed (Top 50 / New Releases / Trending tabs) — fixed invalid playlist IDs (New Music Friday global = 37i9dQZF1DX4JAvHpjipBk; Pop Rising = 37i9dQZF1DWUa8ZRTfalHk).
3. Added 7 selectable themes (Auto/Dark/Light/Midnight/Sunset/Forest/Ocean) with localStorage persistence; non-auto themes hide weather canvas and apply gradient.
4. Added Self-Development Books (Open Library) and Tech News (Hacker News) sections to right side panel.
5. Dynamic video lists via Piped API (api.piped.private.coffee) with curated fallback; video sub-tabs (Top / New Releases / Trending) for both music videos and movie trailers.
6. Fixed prev/next controls visibility (hidden outside video modes) so they no longer leak movie titles into Top Songs.

## Pending / next steps

- Deploy latest (weather-only) to FTP.
- Test Piped dynamic fetch reliability in production; consider fallback instance rotation.
- Add more dynamic sliders: TV series vs Movies separation under trailers; latest vs top performing vs upcoming this week.
- Possibly add audiobooks section (Open Library audiobooks subject).
- Verify live page after deploy.

## Verification

- Playwright tests/weather_page.spec.ts: 4/4 pass, 0 JS errors (as of last run).
