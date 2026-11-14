# Live-Site Browser Validation — JS / Console / Network Errors (2026-11-14)

Method: Playwright 1.58 (headless Chromium) against the LIVE production URLs, capturing `console.error`, `pageerror`, and `requestfailed` events. Audit run 2026-11-14 ~17:55Z. Reusable spec: `tests/audit_live_js_errors_spec.ts` (+ `playwright.live.config.ts`).

## Results summary

| Page | URL | pageErrors | consoleErrors | failed requests | Verdict |
|---|---|---|---|---|---|
| Audit dashboard | findtorontoevents.ca/audit/ | **0** | 5 | 4 | PASS (fetch-blocked widgets) |
| HyroTrader | findtorontoevents.ca/audit/hyrotrader/ | **0** | 0 | 0 | PASS (clean) |
| Frontend (main) | findtorontoevents.ca/ | **1** | 4 | 12 | **FAIL** — uncaught React error |
| Interactive sanity | audit page filter/tab click | — | — | — | PASS (211 controls; page alive) |

## FAIL — Frontend (findtorontoevents.ca/): uncaught React error

- **pageerror:** `Error: Minified React error #418` (React hydration error #418 = "Hydration failed because the server rendered HTML didn't match the client."). This is a **real client-side crash** on the main site — the React root fails to hydrate, so interactive widget(s) on the homepage are broken/empty for end users.
- **consoleErrors (4):** two 400 responses + two 404 resource loads.
- **failed requests (12):** includes `pagead2.googlesyndication.com/pagead/ping` (ads), and several `nowtoronto.com/wp-content/uploads/…/__hp-blocked` images (hotlink protection blocking content images). These are external-resource failures — console noise, not the app crash, but they degrade the page.

## WARN — Audit dashboard (findtorontoevents.ca/audit/): blocked price-feed widgets

- 0 uncaught JS errors (page does not crash) — but 5 console errors / 4 failed requests are **CORS/feed failures** that leave price widgets empty:
  - `min-api.cryptocompare.com/data/v2/histohour?fsym=HYPE&tsym=USD…` → **blocked by CORS** (No 'Access-Control-Allow-Origin'). The dashboard can't fetch HYPE price history.
  - `api.allorigins.win/raw?url=…api.kucoin.com…HYPE-USDT…` → failed (proxy for KuCoin candles).
  - Impact: HYPE-scoped widgets render with no data; the rest of the dashboard is fine (title + 29k chars body + 211 controls).

## PASS — HyroTrader page
- 0 console errors, 0 page errors, 0 failed requests. Clean.

## Mapping back to the audit's "price feed" findings
These live failures are the *front-end symptom* of the data-pipeline findings: the dashboard's price feed is not reliably reaching the browser for some symbols (HYPE) due to CORS + proxy failures — consistent with the "stale/null current_price" and "zombie feed" findings. Fix direction: run Cryptocompare/KuCoin fetches server-side (dashboard generator) instead of client-side fetch, or add a CORS proxy header allow-list.

## Reproduce
```
npx playwright test tests/audit_live_js_errors_spec.ts --config=playwright.live.config.ts --project="Desktop Chrome"
```
(Requires playwright + Chromium installed; uses the live URLs, no webServer.)
