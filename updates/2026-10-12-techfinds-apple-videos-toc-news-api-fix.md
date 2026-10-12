# Tech Finds: Apple section + video links + TOC; News API 64s stall fixed (2026-10-12)

## 1. Tech Finds page additions (https://findtorontoevents.ca/techfinds/)

- **Apple section (4 new cards)** — per user request, the non-Apple-first
  stance now includes Apple's latest/upcoming gear:
  - iPhone 18 Pro & Pro Max ($1,199/$1,299 — Apple Newsroom + CNET)
  - iPhone Duo foldable ($1,999, ships October — PopSci + 9to5Mac)
  - AirPods Pro 3 ($249 — MacRumors + Apple Store)
  - Apple Watch Series 12 ($399) & Ultra 4 ($799) — apple.com + ESR guide
  All with USD+CAD, gen-comparison tables, sources; 4 images added.
- **Video links on all 24 cards** ("▶ Watch videos"): the Meta card links its
  verified official announcement video; the rest link YouTube searches per
  product so links never go stale.
- **Table of contents**: chip-style `.page-toc` under the hero with anchors
  to every section (Featured/Trackers/AR-VR/Audio/Apple/AI); section heads
  got ids. Hero badge now "24 verified finds".
- Verified with Playwright: 6 TOC links (0 broken), 24 vidlinks, Apple
  filter → exactly 4 cards, anchor scroll works, 0 console errors. Deployed
  via FTP; live-checked (HTTP 200, images serve).

## 2. /news/ "loading news feeds.." fix

Diagnosis (curl timing): page shell loads in 0.17s but
`/fc/api/news_feed.php?action=get` blocked for **19–64s**. Causes found:
1. `news_feed_schema.php` connected to `mysql.50webs.com` with bare
   `new mysqli(...)` — no connect timeout (default ~60s hang when the DB is
   slow; even an empty category took 52s).
2. The RSS fallback (`_nf_fetch_all`) live-fetched every expired source
   synchronously (15s/10s curl timeouts), and failed feeds re-fetched on
   every request with no retry marker; good cached articles could be wiped
   by a transient empty parse.

Fixes (both files deployed with `.bak-20261012` server backups):
- `news_feed_schema.php`: `mysqli_init` + `MYSQLI_OPT_CONNECT_TIMEOUT = 3`.
- `news_feed.php`: serve stale cache (up to 7 days) with a 15-minute
  per-source retry marker and a hard cap of 2 blocking fetches per request;
  curl timeouts 15/10 → 8/4; never overwrite cache with an empty parse when
  stale data exists. `?action=fetch` still forces a full refresh.

Verified live: `action=get` now **1.0–3.5s** (was 19–64s), JSON intact
(`ok:true, source:rss_cache`, articles present).

## 3. ServiceNow JS guide reorg (deployed earlier today)

Appendix D/S/T/V (Advanced Glide & JS APIs, Joins & Encoded Queries,
Reusable Code, API Deep-Dive) moved up after section 28 into a new
"JS & Query Deep-Dives" TOC group; hashchange scrollspy re-sync added.
See 2026-10-12-servicenow-js-toc-mobile-fix.md for the earlier TOC fix.
