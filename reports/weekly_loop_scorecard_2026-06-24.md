# Weekly Loop Scorecard — 2026-06-24

**Edition:** /money-maker-ready-June112026edition · **Author:** claude-opus · **Mode:** MEASURE→DIAGNOSE→FORWARD→RATCHET (no new ACT — edge-hunt exhausted + peer-validated; data-constrained)

## 1. MEASURE — honest intrabar truth by class (`build_intrabar_truth_by_class.py`, gen 2026-06-24T14:47Z)

| class | n | WR% | net PF | verdict |
|---|---:|---:|---:|---|
| CRYPTO | 1228 | 32.6 | 0.779 | FAIL |
| COMMODITY | 140 | 43.6 | 1.252 | FAIL |
| EQUITY | 128 | 35.9 | 0.474 | FAIL |
| FOREX | 122 | 45.9 | 1.246 | FAIL |
| MEMECOIN | 77 | 26.0 | 0.580 | INSUFFICIENT_N |
| ETF | 18 | 0.0 | 0.000 | INSUFFICIENT_N |
| FUTURES | 17 | 29.4 | 0.465 | INSUFFICIENT_N |
| BOND | 8 | 25.0 | 1.270 | INSUFFICIENT_N |

**0/9 classes pass Tier-2.** Only T2-*shaped* strategy lead: FOREX `forex_rsi2_mean_reversion` n=20 WR 60% PF 2.15 — **n far below the n≥80 promotion bar** (candidate-selection only, never sized).

## 2. DIAGNOSE (H1–H5)

- **H1 (measurement):** AMBER. `check_one_sided_resolution` shows persistent **one-sided** news/social sources (WON-only or LOST-only at n=20–91: reddit / gnews / currents / stocktwits / `copy_hl_lb_None` 37L/378 / `copy_pm_*`). These are resolution/labeling artifacts, not edge — they do not enter the verdict-grade clean cohort, but they inflate raw source tables. No new corruption; known pathology.
- **H2 (backtest-only):** GREEN-handled. No new backtests this cycle (every canonical signal already refuted/forward-shadowed; momentum live-pick list shown to be an AI-rally **survivorship/beta** artifact, not deployed).
- **H3 (data scarcity):** RED — the binding constraint. Honest ledger is ~95.7% placeholder; clean cohort dominated by a 6-day burst. EQUITY blocked by `daily_prices` freeze (2026-04-29 / 153 tickers). Free-API feeds landed (CFTC COT 5yr, SEC insider, futures/equity daily OHLCV) but commodity/equity **price-path** for resolution is the remaining gap.
- **H4 (external signals):** per-source one-sided pattern = keep clean cohort only; do not promote on raw source WR.
- **H5 (coverage):** RED — extend resolution before judging. Crypto multi-year OHLCV backfill (`RUNBOOK_crypto_ohlcv_backfill_2026-06-20.md`) is the #1 scoped lever (greenlight-ready, not fired — multi-million-row write needs backup + operator OK).

## 3. FORWARD — pre-registered checkpoints

- **CRYPTO rsi5070×US** (n≥150 gate): live **n=117**, accrual stalled (<3/day, flat >1 day) → gate slipped from ~Jun-25 to **mid-July+**; net CI-LB still sub-bar. SHADOW_TRACKING.
- **FOREX rsi2** (daily variant): n=20, PF 2.15 — accruing; n≥80 far off.
- No condition at/over its gate → **nothing promotable this cycle.** Promotion bar unchanged: net-PF 95% CI-LB > 1.15 @ n≥80 forward + time-split + concentration < 35%.

## 4. RATCHET — operator levers (unchanged, all gated)

1. **Restore/broaden `daily_prices`** past 2026-04-29 / >153 tickers → unblocks EQUITY honest-n + survivorship-free forward momentum test (highest-prob path to a first winner).
2. **Greenlight crypto OHLCV multi-year backfill** (backup-first, idempotent, ~30 min bounded) → converts placeholder CRYPTO picks to clean first-touch; grows honest n past 1,228.
3. **Point-in-time equity dataset** (external) → strips the WDC/MU/INTC survivorship distortion in momentum.

## Verdict

Steady-state, data-constrained, honest. **0/9 T2; no promotable candidate at a gate.** No new ACT warranted — the edge-hunt is exhausted and peer-validated; the bottleneck is clean-trade supply + resolution quality, not strategy supply. Highest-leverage next action is an operator/data decision (lever 1 or 2), not more analysis. Summary remains live on `findtorontoevents.ca/updates/index.html`.
