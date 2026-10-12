# Tech Finds: Apple section + video links + TOC; News API 64s stall fixed (2026-10-12)

> **Later additions the same day** are appended in section 5 — More Tech &
> Smart Kitchen, TV / Study / Software sections (committed `c49d890839`),
> and the /news/ AI category + AI/podcast feeds.

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

## 4. Embed test (same day)

Embedded the official Meta VR Glasses announcement video (yt id xyD_bmMy5nQ)
in the headline feature card via a responsive 16:9 `.embed-wrap` iframe using
youtube-nocookie.com. Deployed and validated live with Playwright: the
YouTube frame attaches, `#movie_player` renders (no "embedding disabled"
error), box 515x290. Embeds are NOT blocked on this host — other cards can be
embedded on request; the per-card "▶ Watch videos" links remain as fallback.

## 5. Same-day expansion: More Tech/Kitchen, TV/Study/Software, /news/ AI

### 5a. Tech Finds — three new sections (commit `c49d890839`)

Added after the AI Hardware section, each with source-verified cards,
comparison tables, and per-card video links:

- **More Tech & Smart Kitchen** (5 cards, `data-filter="more"`): DJI Osmo
  Pocket 4, RayNeo Air 4 Pro, Samsung Galaxy Ring 2 (rumor), wan AIChef
  Ultra (AI cooking robot), Samsung Bespoke AI Kitchen.
- **TV & Home Streaming** (`tv`): Samsung The Frame 2026 — art-mode 4K
  QLED. A dedicated LG OLED evo M5 card was planned but no clean product
  image could be fetched, so the redundant card was dropped rather than
  shipping a duplicated/placeholder image; the Frame card's comparison
  table already contrasts M5 vs Frame.
- **Study · Coding · Learning** (`study`): Lenovo Yoga Book 9i Gen 10
  (dual 14" 2.8K OLED, 360° yoga hinge), MacBook Pro (M-series, coding).
- **Software Innovations** (`software`, first non-hardware section):
  Cursor (AI code editor), Claude (assistant + coding).

New filter chips + page-TOC anchors for each section. 9 images added;
2 orphan images (`aiagent.jpg`, `samsungframe.jpg`) deleted after
confirming no card referenced them. Final sweep: 33 images, every
`img src` resolves, no orphans.

**Live verification (Playwright on the deployed page):** 32 cards, 10 TOC
links (0 broken), filter counts tv 1 / study 2 / software 2 / more 5 /
ai 3, 0 console errors, 0 missing-image requests. Committed + pushed to
`fix/oct10-thumbnail-crop-age-gate`.

### 5b. /news/ — back up + AI category + AI/podcast feeds

- **Health re-check** (the earlier stall fix is holding): page 0.13s,
  `action=sources` 0.17s, `action=get` 0.25s.
- **10 new AI sources** in `news_feed.php` (new `category => 'ai'`, added
  to `$valid_cats`, new `ai` auto-tag rule): OpenAI News, Google AI Blog,
  MIT Tech Review AI, VentureBeat AI, The Verge AI, TechCrunch AI,
  Ars Technica AI, r/MachineLearning, **Latent Space** (podcast),
  **No Priors** (podcast).
- **AI tab** on the frontend: new `data-cat="ai"` tab, `.badge-ai`
  styling, `catLabel`/`catLabels`/preload-cats updated.

**Live verification:** sources 102 → **112 (10 AI)**; `category=ai`
returns 20 real articles (r/MachineLearning, TechCrunch AI, The Verge AI,
Latent Space). Browser check: AI tab renders 21 cards with correct badge;
AI/Toronto/World tab-switching all work; 0 JS errors. Live file
byte-matches local; server backups `news_feed.bak-20261012.php` and
`news_index.bak-20261012.html`.

> Note: the /news/ page and `news_feed.php` live only on the FTP server
> (not tracked in this repo), so this work is documented here but is not
> committed as source.

### 5c. ServiceNow JS guide — GlideAggregate correction (uncommitted)

Fixed a wrong claim in the GlideAggregate section: the old example implied
`gs.info` does no positional substitution, which contradicted the correct
placeholder-teaching block later on the same page. The example now uses
`gs.info('Priority {0}: {1}', ...)` (the valid positional form), and the
callout teaches the real distinction — `agg.priority` (internal value) vs
`getDisplayValue('priority')` (label), and `getAggregate('COUNT')` (no
field) vs value aggregates (field as 2nd arg). Markup verified balanced
(`<pre>` 82/82, `<section>` 53/53, `<div>` 461/461, script/style stripped).

> This file also carries another session's large uncommitted work (~3,000
> lines across 12 hunks), so it is intentionally NOT committed here — the
> fix is live in the working tree and rides along with that session's
> eventual commit.

## 6. Creative Gadgets section (committed `ccc7a4d077`)

Added a 4th same-day expansion to Tech Finds: a **Creative Gadgets**
section for the unusual/quirky finds surfaced by the Popular Mechanics
gadget roundup and the Yanko Design guide the user flagged. Each pick was
cross-checked against **two independent sources** before adding, per the
page's own "Sources (cross-checked)" policy.

### Picks added

| Product | Price | Sources |
|---|---|---|
| piBrick Pocket-CM5 | $240 assembled kit / ~$172 DIY parts | CNX Software (Jun 11, 2026) + Tindie listing |
| Logitech MX Master 4 | $119.99 | Logitech official + The Verge (first haptic mouse) |
| Xreal 1S | $449 | The Verge (CES hands-on) + Mashable |
| OhSnap Wallet 2 | ~$76 retail / $61 Kickstarter | The Verge + GearDiary |

### Verification

- **Cross-source**: every price and headline spec confirmed from two
  independent outlets before the card was written; images pulled via
  the page's existing `og:image` fetch path and validated with `identify`
  (all real JPEG/PNG, 370x217 uniform render box).
- **Markup**: matched existing card markup exactly (`price-row`, `pills`,
  `cmp` comparison table, `vidlink`, `sources`). Two self-inflicted bugs
  found and fixed before deploy: a stray `class="review"` that should
  have been `class="release"`, and a `<th>` closed with `</td>` in the
  OhSnap comparison table.
- **Live browser check** (Playwright, after FTP deploy): 36 cards,
  11 TOC links (0 broken anchors), Creative filter → exactly 4 cards,
  4 new product images load at full resolution, 0 console errors.
- **Live == local**: md5 of served `index.html` matches the deployed
  file (106,665 bytes); all 4 new images return HTTP 200.

### Notes

- The XREAL og:image is only 400x400 (smallest on the page) — renders at
  the same uniform 370x217 box as every other card, slightly softer than
  the rest but no visual defect. Flagged here in case a higher-res asset
  is worth sourcing later.
- A mid-session check appeared to show ~24 pre-existing images broken
  (naturalWidth 0). Curl confirmed all returned HTTP 200 with valid
  JPEG bytes; a stricter re-test that waited on each image's `complete`
  flag showed all loading at full width. It was a measurement-timing
  artifact, not a defect — same conclusion reached earlier this session,
  re-confirmed here with a stricter method rather than assumed.
