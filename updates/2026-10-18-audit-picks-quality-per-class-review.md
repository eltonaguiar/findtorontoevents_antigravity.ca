# 2026-10-18 — /audit picks quality review per asset class: stale-P&L status, strictness/near-miss analysis, and fix plan

Prepared 2026-10-18 ~02:05 UTC. Payload snapshots: `dashboard_data.json`
generated 2026-10-18T00:48Z (pre-merge build; PR #729 merged at 01:47Z was
still propagating — pending validations marked ⏳).

## 0. What landed first (context)

PR #729 merged to main 01:47Z (`79826045ed`): resolver zero-PnL heal,
`_enrich_live_pnl` fetch-first, `WR@0-trades` reason guard, analyst-tracker
cron-string revival, picks-now budget/atomic-write/always-push, Quick Add +
thumbnail-proxy (already live via FTP).

Post-merge dispatch results:
- **analyst-tracker `mode=validate`: SUCCESS — `validate-prices` job ran for
  the first time since ~March** (scrape correctly skipped in validate mode).
  The un-dead job works in production. ✅
- picks-now-refresh dispatched 01:51Z (⏳ the "system would have made new
  picks" CI test — run 39087973734).
- audit-dashboard dispatched 01:51Z (⏳ rebuild that applies the zero-PnL
  heal — run 39087972131).

## 1. Latest picks per asset class (payload 00:48Z)

`picks.active` composition rule (observed): each row is either
`_gate_passed=True` (emitter's own quality gate) **or** carries
`_visibility_floor="per_class"` (top-of-class display floor that keeps
representation even when class thresholds fail).

| class | actives | symbols | avgScore | fwdWR | thresholdPass |
|---|---|---|---|---|---|
| CRYPTO | 3 | BTCUSDT(100), XRPUSDT(79), SOLUSDT(73) | 84 | 0.0 | false |
| EQUITY | 2 | SPY(63)×2 | 63 | 0.909 | false |
| COMMODITY | 2 | GC=F(63), PA=F(19) | 41 | 0.274 | false |
| FOREX | 2 | EURGBP=X(62), GBPUSD=X(58) | 60 | 0.274 | false |
| FUTURES | 1 | NQ=F(56) | 56 | 1.0 | false |
| ETF | 2 | TQQQ(12), XLV(10) | 11 | 0.552 | false |
| BOND | **0** | — | 0.0 | 0.0 | true (vacuous) |

Closed 14d economics (from the 01:37 build): CRYPTO PF 1.44, FOREX PF 5.16,
COMMODITY 2.29, EQUITY 1.02, ETF **0.40 (29 SL : 7 TP stop-dance)**,
BOND above-floor PF 0.41 (gates are *protecting*), FUTURES n=1.
Book-wide: 30d PF 1.39 (mean +0.636), last 7d PF 1.02 — the "bad feeling"
is recency + the fabricated-zero cleanup now healing.

## 2. Stale / wrong P&L (=0%) status

- **Closed**: 53 fabricated zero rows (38 today's pre-fix TIME_EXIT batch,
  12 UNKNOWN, 3 impossible TP/SL-at-0). Resolver heal in PR #729 converts
  these to unresolved-with-NULL at the next build → ⏳ validated by run
  39087972131 (check: zero-share of recent_closed drops from 1.5% → ~0).
- **Active**: all 21 earlier rows verified against live yfinance/Binance —
  the 0.00% rows are genuine after-hours flats (picked at/near close), **not
  stale**. The fetch-first fix prevents future freeze.
- **Analyst blocks**: were 201–235d frozen; hourly validate job now
  un-skipped and ran ✅ (leaderboard contributor feed still needs the P1
  source investigation — scrape runs green but has produced no new rows
  since Feb).

## 3. Strictness / near-miss analysis (closed picks vs class floors)

Band = score in [minScore−10, minScore):

| class | thr | near n | near mean | near Σ | above n | above mean | above Σ | verdict |
|---|---|---|---|---|---|---|---|---|
| BOND | 35 | 3 | +0.738 | +2.2 | 25 | −0.347 | −8.7 | floor protects (above-floor loses) |
| CRYPTO | 65 | 106 | +0.558 | +59.1 | 133 | +4.382 | +582.8 | floor justified (10× mean) but near-band is real money |
| EQUITY | 40 | **412** | +0.480 | **+197.7** | 241 | +0.658 | +158.5 | **strictness costs more profit than it saves** (deep-below <30 is toxic −1.22) |
| ETF | 35 | 64 | −0.036 | −2.3 | 423 | +0.172 | +72.6 | floor fine |
| FOREX | 40 | 89 | +0.026 | +2.3 | 66 | +0.222 | +14.7 | floor fine |
| FUTURES | 45 | 1 | +0.651 | +0.7 | 1 | +14.94 | +14.9 | n too small |
| COMMODITY | 30 | 0 | — | — | 9 | +1.019 | +9.2 | fine |

### BOND: not strictness — an emitter scoring bug
All 11 BOND raw rows (bond_scanner, orphan_emitter_bond, alpha_engine_fast,
etf_sector_rotation/TIP) carry `score = 0.0 or null` with
`forward_status = NO_DATA/""`. They can never clear minScore 35, and the
per-class floor drops them too → **0 BOND actives**. The scanners never
populate the `score` field.

### FUTURES: data-starved forward gate, not tight risk rules
Emitters do score (ES=F 57, NQ=F 56, NKD=F 51, YM=F 44) but every row is
`_gate_passed=False` with `forward_status = "insufficient_data (1/50 trades)"`
or `NO_DATA` — the forward-track bar (50 trades) can't fill because
orphan/new emitters produce ~1 closed trade. NQ=F surfaced only via the
per-class floor; ES=F (57 > NQ 56) is absent — the floor ranks after
dedup/dup-handling, which needs a code check (see plan).

### "Closest top performers" (documented near-miss registry candidates)
- CRYPTO: 106 picks at 55–64, +59.1 Σ — e.g. next-tier entries below the
  65 floor; EQUITY: 412 picks at 30–39, +197.7 Σ (largest recoverable pool);
- FOREX 89 near, ETF 64 near — but means ≈ 0 → not recoverable value.
- Proposal: a weekly `near_miss_report.json` listing, per class, below-floor
  cohort counts/Σ plus the top-10 would-have-passed picks — tracked so gate
  changes are judged on realized near-band profit (M-107 prereg before any
  floor actually moves).

## 4. Linked pages freshness (audit index + picks-now)

All real `/audit/*` linked pages probe HTTP 200 with Last-Modified ≤2h old
(ai-tournament, anti_overfit, edge_stability, paper_pilot, pick_funnel,
real_money, live-monitor/sports-betting). The 404 rows in the sweep output
were artifacts of my URL normalization (absolute hrefs got re-prefixed) —
**not** broken links. json-backed blocks staleness covered in §2.

## 5. "System would have made new picks" test

- Local reduced-universe run (pre-merge): `PICKS_NOW_MAX_PER_CLASS=2
  PICKS_NOW_BUDGET_S=240` → 9s, exit 0, fresh atomic JSON,
  n_scored=12, picks=6 (1 STRONG_BUY + 5 BUY). ✅
- CI full-universe: picks-now-refresh dispatched 01:51Z ⏳ — success with a
  fresh `generated_at` + picks>0 (freshness assert enforces it) proves the
  production "new picks" path end-to-end.

## 6. Fix plan

### P0 (already merged / this doc)
- Zero-PnL heal, fetch-first prices, reason guard, analyst validate revival,
  picks-now resilience — merged PR #729; validations ⏳ per §0.

### P1 (mechanical, next PR)
1. **BOND score population**: bond_scanner / orphan_emitter_bond /
   alpha_engine_fast bond strategies must write `score` (confidence-weighted
   quant score like other classes) instead of 0/null. Until then BOND
   actives stay 0 by construction, and `thresholdPass: true` on
   `activeCount=0` must be fixed to show N/A (vacuous-pass display bug).
2. **FUTURES forward-gate catch-22**: fresh emitters can never reach 50
   trades → gate permanently "insufficient_data". Add a provisional pass:
   gate passes on `score ≥ minScore` while `forward_trades < minTrades`,
   with the row labeled PROVISIONAL (visibility without claiming a WR),
   or reduce minTrades for classes with <20 closed picks/90d — **M-107
   prereg + backtest first** (near-band n=1 today: no evidence either way).
3. **ES/F floor question**: confirm why ES=F(56–57) loses the per-class floor
   to NQ=F after dedup (dup rows share one id); fix floor ranking to use
   deduped score order.
4. **EQUITY floor candidate**: 40→30 keeps the toxic <30 out (−1.22 mean)
   while recovering part of the +197.7 near-band pool; keep the forward-WR
   gate as the real risk control. Preregister + walkforward per M-107
   (also aligns with Kilo's elite-gate 40→50 candidate — decide jointly on
   one metric, not both).
5. **Near-miss registry**: emit `near_miss_report.json` weekly (§3) so
   "lost profit to strictness" is continuously measured, not anecdotal.

### P2 (infrastructure)
- Freshness guard extends to predictions/analyst/walkforward blocks (stale
  → badge STALE, not silent); Spearman(score,pnl) per class as a ranking KPI
  (book-wide +0.093 today); per-class expectancy gates for *active emitters*
  (BOND would have been caught); ETF stop-dance study (ATR-based SL) under
  prereg.

## Verification status

| item | check | result |
|---|---|---|
| analyst validate revival | run 39087975131 | ✅ success (first since March) |
| picks-now new-picks CI test | run 39087973734 | ⏳ |
| zero-PnL heal live | run 39087972131 → zero-share | ⏳ |
| picks-now local reduced test | 9s exit0 fresh JSON | ✅ |
| actives ground-truth vs live feeds | 21/21 exact | ✅ |
| linked /audit pages freshness | 200 + ≤2h | ✅ |

🤖 Generated with Codebuff
Co-Authored-By: Codebuff <noreply@codebuff.com>