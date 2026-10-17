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

## GitHub Actions health double-check (on request)

- Stale failures (latest completed run failed, no later success): **0**
- Chronic cancellations (≥4 cancels, 0 successes): **0**
- Recurring failures (≥3 consecutive): **0**
- Cancelled runs in the last 200: **0**
- Runs stalled in_progress/queued >90min (last 500): **none**
- Annotations/warnings on check-runs of the last 8 main commits: **0**
- Job-level scan of the last 60 runs: the only non-success jobs were
  `status=in_progress` with empty conclusion (mid-flight), not failures.

No CI fixes are needed.

## Per-asset-class pick quality (production payload)

Closed (3500 rows in the recent window):

| class | n | WR% | flat | zero% | mean% |
|---|---|---|---|---|---|
| CRYPTO | 2091 | 46.7 | 0 | 0.0 | +0.60 |
| EQUITY | 688 | 48.2 | 10 | 1.5 | +0.46 |
| ETF | 503 | 44.3 | 0 | 0.0 | +0.08 |
| FOREX | 180 | 47.1 | 40 | **22.2** | +0.08 |
| BOND | 28 | 33.3 | 0 | 3.6 | −0.23 |
| COMMODITY | 9 | 50.0 | 1 | 11.1 | +0.59 |
| FUTURES | 1 | 100 | 0 | 0.0 | +14.94 |

- FOREX's 22% zero share is the fabricated TIME_EXIT cluster (today's
  pre-fix batch + the March 11–13 batch) — healed by the resolver fix.
- Every class still shows `thresholdPass: false` / `smartCount: 0`
  (known floors state, unchanged).
- `active_raw`: 3280/4098 picks (80%) auto-expire with
  `expired_no_pnl` — CRYPTO 84%, FOREX 70%, EQUITY 50%. This is the
  real stall-data finding: most picks' lifecycles end without a measured
  PnL, which deflates every class's `forwardWR` and keeps score floors
  unpassed. **Planned follow-up (not fixed here):** make the resolver
  cover crypto/forex emitter rows so TIME/SL/TP resolution (with real
  prices) replaces silent auto-expiry.
- Cosmetic reason smells fixed: `combined_confidence_strategy.py` no
  longer emits `WR=80.0%, 0 trades` — with `trade_count == 0` it now
  says `(no trade history yet)` (verified: 0-trade → no WR string, 8-trade
  → `WR=75.0%, 8 trades`; py_compile + module import pass).
- Concurrent session note: commit `aefb74685e` (parallel agent, same
  branch) widened yfinance lookups `period 1d→5d` for weekend prices in
  `_fetch_equity_prices`; verified compatible — this session's
  `_enrich_live_pnl` fetch-first fix (comment marker at line 1674,
  `fetched = {}` at 1716) remains intact.

## Delivery status

Fixes live on branch `fix/js-reference-accuracy-audit` (commits
`c56f1af9ee`, `1cabf7bd9a`, `e468138675` + this one). The branch's history
has diverged heavily from `origin/main` (thousands of CI commits on each
side), so merging is an operator decision — the hourly audit-dashboard cron
runs from `main` and will not pick these up until they land there.