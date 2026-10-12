# Tech Finds page — findtorontoevents.ca/techfinds/ (2026-10-12)

## What

Added a new **Tech Finds** section to findtorontoevents.ca: a curated, source-verified catalog of upcoming and just-launched tech products (non-Apple first, Beats by exception).

## Why

The site's "news" footprint (News Aggregator at `/news/`) has no product-tech coverage. The user wanted a "be the first to know" page for upcoming gadgets — with verified release dates, USD **and CAD** pricing, cited + cross-checked sources, generational comparison tables (e.g. SmartTag3 works with iOS where SmartTag2/1 did not), and product images.

## What was built

- **New page:** `findtorontoevents.ca/techfinds/index.html` — standalone, self-contained (embedded CSS/JS, Google Fonts), dark glassmorphism design with animated aurora background.
- **20 verified products**, each with: product image (downloaded locally to `techfinds/images/`, 20 files), status badge (Out now / Coming soon / Rumor), release date, **USD price + CAD estimate**, key-feature pills, an expandable **"vs previous generation(s)"** comparison table, and **2–3 cited sources** (official first + corroborating outlet).
- Two headline featured cards: **Meta VR Glasses** ($1,299.99, Spring 2027) and **Samsung Galaxy SmartTag3** ($29.99, US early Nov 2026, first Galaxy tag with iOS support).
- Category filter bar (All / Trackers / AR-VR / Audio / AI Hardware / Coming soon / Rumors) with sticky behavior + scroll-reveal animation.
- CAD estimates converted at **1 USD ≈ 1.426 CAD** (XE mid-market, Oct 11 2026), stated on-page; official Canadian MSRP used where published (Sony 1000X THE COLLEXION C$849.99, confirmed via Gadgets360).
- **Nav wiring:** "💻 Tech Finds" added to the Other Stuff menu in `TORONTOEVENTS_ANTIGRAVITY/index.html` in both places (static desktop nav after News Aggregator, and the JS popup builder), plus `NAV_MENU_BACKUP.md` documentation.

## Verification

- Every product's price/date cross-checked against ≥2 independent sources via live web research (Samsung Newsroom, Meta blog, Google blog, Beats/BusinessWire, Bose pressroom, Sony press centre, Technics newsroom, Logitech newsroom, NVIDIA newsroom, PR Newswire + corroborating outlets).
- All 20 product images downloaded and confirmed valid on disk (4.6 MB total).
- Page rendered and screenshot-tested with Playwright/Chromium: hero + featured cards, category filtering (AR/VR filter correctly shows only XR cards and hides other sections), comparison tables, sources links, footer — all confirmed working. Two HTML defects found in self-review (stray `>` in SmartTag3 table, stray class attribute) fixed and re-verified.

## Deploy note

Not deployed from this session — push `findtorontoevents.ca/techfinds/` to the FTP server (alongside the existing `updates/` folder) for the page to go live; nav links point to `/techfinds/`.

## Hotfix (same day) — mobile filter bar

User report: "menu is fried — cut-off and overlaps other text." Diagnosis via
Playwright at 390×844: the sticky filter bar wrapped chips to 3 rows (203px tall,
~24% of the viewport) and its 78%-opacity backdrop let card text show through
while scrolling; a compare-summary also broke mid-word on narrow screens.

Fix: chips are now a single-row horizontally-swipeable strip below 700px
(flex-wrap:nowrap + overflow-x + hidden scrollbar), sticky bar background made
effectively opaque (96–98% gradient + shadow), chips get white-space:nowrap /
flex:none, and the compare summary wraps safely (overflow-wrap:anywhere,
smaller font ≤520px). Desktop unchanged (single 65px row).

Verified: local + live at 390×844 — bar 58px, single row, swipeable; filter
clicks still work (Audio → 12 cards); desktop 1380px unchanged. Redeployed
index.html to /techfinds/ over FTP.
