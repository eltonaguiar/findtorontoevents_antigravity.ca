# Live Playwright JS / console error report — 2026-11-14

Tool: Playwright 1.58.2, headless Chromium, 1600×1000, UA spoofed as desktop Chrome 120,
9–12 s settle to allow the 25 MB payload to parse. Scripts: `.inspect-wt/_audit_tmp/js_check.js`,
`js_probe.js`.

## Results table

| Page | HTTP | pageerror (JS exceptions) | console errors | Rendered | Notable |
|---|---|---|---|---|---|
| `/audit/` | 200 | 0 | 4 | 2,673 rows / 112 tables / 74 tab controls | 404 data file + CORS blocks |
| `/audit/hyrotrader/` | 200 | 0 | 0 | 406 rows / 11 tables / 23 cards | clean |
| `/audit/funds.html` | 200 | 0 | 0 | 71 funds, 18,257 trades, 169 holdings | **prices stuck "Loading..."** |
| `/audit/pick_funnel.html` | 200 | 0 | 0 | 574 rows / 38 tables | clean |

## Bugs found (user-visible)

### B1 — `strategy_tribunal_latest.json` 404 (data deploy gap)
```
HTTP 404 https://findtorontoevents.ca/audit/data/strategy_tribunal_latest.json
```
Same class as the `pick_funnel_snapshot.json` 404 already reported: a data file the frontend
requests is not deployed. Any panel sourcing it silently renders empty.

### B2 — Cryptocompare / Kucoin CORS failures (HYPE price enrichment broken)
```
Access to fetch at 'https://min-api.cryptocompare.com/data/v2/histohour?fsym=HYPE&tsym=USD&limit=15'
from origin 'https://findtorontoevents.ca' has been blocked by CORS policy:
No 'Access-Control-Allow-Origin' header is present.
GET https://api.allorigins.win/raw?url=...kucoin... :: net::ERR_ABORTED
```
Proxy-based price lookups fail in-browser. Either move behind a server-side proxy or drop the
HYPE enrichment path.

### B3 — funds.html "Prices: Loading..." never resolves
After 12 s the header still shows `Prices: Loading... • Data: 2h ago` (fund stats load fine).
Requests made: `api.binance.com/api/v3/ticker/price`, `api1`, `api2`, `data-api.binance.vision`.
None populate the price column → perpetual "Loading..." label. This is consistent with my earlier
note that the Binance quote endpoint is reachable via curl but the browser path is blocked/limited.
Fix: fetch prices server-side into `stock_prices.json`/a `prices.json` and have funds.html read that
file (no live browser fetch), or show the last-known price with its age.

### B4 — confirmed non-issue: no hard JS crashes
Zero `pageerror` events across all four pages. The dashboards' JS is runtime-sound; the failures are
data/resource-level. The "no data" strings on `/audit/` are legitimate, self-documented cases
(A/B NEW sleeve never built; kill-switch status) — not rendering breakage.

## Recommendations
1. Deploy `strategy_tribunal_latest.json` (or remove it from the fetch list).
2. Replace browser-side Binance/Cryptocompare/Kucoin price fetches with a server-side price file —
   this simultaneously fixes B2 and B3 and removes the CORS dependency.
3. Add these to a Playwright smoke test in CI (the repo already has `playwright.audit.config.ts`
   and `tests/audit-pages.spec.ts`) so 404s and stuck "Loading..." fail the build.
