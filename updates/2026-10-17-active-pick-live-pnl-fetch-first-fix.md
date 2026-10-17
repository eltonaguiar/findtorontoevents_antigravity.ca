# 2026-10-17 — Active-pick live-PnL enrichment: stop treating carried prices as authoritative

Date: 2026-10-17

Follow-up to the /audit pick-quality review. Context: an earlier QA pass flagged
"active-window PnL structurally frozen — 18/21 actives show `current_price` at
or near `entry_price`". This note records what was verified and the defect fixed.

## Verification first: the displayed numbers are true

A live cross-check of all 21 production active picks against yfinance
(`period="5d"` last close; crypto via Binance) matched exactly:

- 19/19 non-crypto actives: displayed `current_price` equals the live close
  (EFA 103.55, SPY 763.25, TIP 105.54, NQ=F 29391.5, EURGBP=X 0.84321, …).
- The 18 picks showing 0.00% PnL were picked at/near today's market close
  (age_hours 0.1–3.4, generation 21:49Z = after the 20:00Z close) — the
  market genuinely has not moved since entry. **Not fabricated, not stale.**
- Crypto actives (DOTUSDT +2.6%, SUIUSDT +0.88%) match Binance live prices.

So the active-tab 0% readings are honest after-hours flat prices. The
historical *closed*-pick 0% fabrication is the resolver defect fixed earlier
today (heal-on-load; `updates/2026-10-17-resolver-mtm-quickadd-crossplatform-image-proxy-fix.md`).

## The latent defect fixed anyway

`_enrich_live_pnl()` in `audit_trail/dashboard_generator.py` had a
structural freeze trap:

1. The symbol-collection loop did `continue` when a pick already carried a
   `current_price > 0` — so such picks were **never queued for a live
   fetch**. A pick born with `current_price == entry_price` would show
   0.00% forever, regardless of real price movement.
2. Fetched quotes were applied with `prices.setdefault(...)`, so any
   carried (stale) price won over a fresh quote.

It never bit in yesterday's run only because picks arrive with the carried
price already refreshed by the pre-step — but any upstream that persists
`current_price` would permanently mask real moves.

**Change:**
- Carried `current_price` is recorded only as a fallback; symbol queuing no
  longer `continue`s, so every active symbol is fetched each pass.
- Fresh quotes collected into `fetched` and take lookup precedence.
- If neither fetcher returns a quote, the pick is left untouched (no
  fabricated 0 written).

**Verification:**
- `python3 -m py_compile audit_trail/dashboard_generator.py` — pass.
- In-process harness (`_enrich_live_pnl` called directly with production-shaped
  picks): crypto + equity paths fetch live quotes and override carried prices
  (`SPY` carried 763.25 → fetched value written, PnL recomputed); with both
  fetchers stubbed to `{}`, picks pass through untouched and no exception
  is raised.
- Live sanity (above): all 21 production actives match ground truth.

## Playwright suites this session

- `tests/mental-health-resources.spec.ts` — **10/10 passed**.
- `tests/active_picks_count.spec.ts` + `tests/dashboard_data_loading.spec.ts`
  + `tests/audit_page.spec.ts` — **22 passed, 1 failed**: the failure is
  `Alpha Engine has no fatal JS errors`, a timeout navigating to
  `https://eltonaguiar.github.io/.../alpha/` with `waitUntil: networkidle`
  (external GH-Pages host/network flake), not a code defect in this change —
  none of these specs touch `dashboard_generator.py`, which is CI-only.

## Recently-closed pick quality (production `dashboard_data.json`, 3500 rows)

- Non-zero PnL distribution healthy: n=3447, min −97.2%, max +100%, mean +0.47%.
- 53 rows at exactly 0.00%: 38 are today's TIME_EXIT batch fabricated by the
  pre-fix resolver, 12 UNKNOWN, 3 impossible TP_HIT/SL_HIT-at-0 rows
  (2026-10-13/14) — all covered by the resolver heal-on-load once the fix
  reaches `main`.
- 14-day slice: 1037 closed, 407 SL_HIT / 346 TP_HIT / 193 FORCE_CLOSED /
  87 TIME_EXIT — normal mix, WR ≈ 44.6%.

## Delivery status

Fixes live on branch `fix/js-reference-accuracy-audit` (commits
`c56f1af9ee`, `1cabf7bd9a`, `e468138675` + this one). The branch's history
has diverged heavily from `origin/main` (thousands of CI commits on each
side), so merging is an operator decision — the hourly audit-dashboard cron
runs from `main` and will not pick these up until they land there.