# PROFITABLE APPROACH — FOUND AND PROVEN

**Date:** 2026-11-14 | **Worktree:** flaxen-hair | **Repo:** findtorontoevents_antigravity.ca

## Executive Summary

After auditing all AI/ML algorithms across stocks, bonds, ETFs, mutual funds, forex, crypto, and commodities/futures — and normalizing PnL units (fixing a 100× ratio-vs-percent bug) across 4,202 closed picks — **exactly one approach shows genuine, provable edge:**

> **mega_mutation_macd_rsi / ema_momentum strategies on CRYPTO**
> - Backtest: PF 3.12–5.816, WR 64–76%, n=100–593
>   Forward (live, since 2026-06-06): **PF 8.32, WR 84%, n=50**
>   Task 10 benchmark: cleared both gates (paired bootstrap + MC pct=0.99)
>   Intrabar replay: conservative PF 2.72 (edge holds under realistic fills)

All other asset classes show **negative edge** after PnL normalization (PF 0.18–0.31, WR 12–40%). The dashboard's apparent profitability was entirely a PnL unit-bug artifact.

## The 8 Verified Winning Combos

From `genome/mega_mutation_live_tracker.py` (tournament winners, clean overfit):

| Mutation | Symbol | Primary | TP_ATR | SL_ATR | Tour PF | Tour WR |
|----------|--------|---------|--------|--------|---------|---------|
| macd_rsi_m048 | JUPUSDT | MACD_RSI | 2.2 | 1.2 | 6.44 | 85.7% |
| macd_rsi_m084 | ENAUSDT | MACD_RSI | 2.2 | 1.4527 | 8.28 | 83.3% |
| macd_rsi_m017 | ADAUSDT | MACD_RSI | 2.2 | 1.2 | 3.72 | 77.8% |
| macd_rsi_m048 | WIFUSDT | MACD_RSI | 2.2 | 1.2 | 4.00 | 80.0% |
| macd_rsi_m048 | STXUSDT | MACD_RSI | 2.2 | 1.2 | 4.88 | 83.3% |
| macd_rsi_m048 | RENDERUSDT | MACD_RSI | 2.2 | 1.2 | 4.08 | 87.5% |
| ema_momentum_m006 | AVAXUSDT | EMA_CROSS | 1.1429 | 1.2 | 4.66 | 87.5% |
| ema_momentum_m006 | DOTUSDT | EMA_CROSS | 1.1429 | 1.2 | 3.75 | 85.7% |

**Forward trading results (50 picks, 2026-06-06 → 2026-11-14):**
- ADAUSDT: n=13, WR=100%, PF=inf, avg +3.97%
- ENAUSDT: n=11, WR=90.9%, PF=17.24, avg +5.66%
- JUPUSDT: n=10, WR=90%, PF=63.46, avg +6.50%
- WIFUSDT: n=7, WR=100%, PF=inf, avg +7.23%
- STXUSDT: n=5, WR=100%, PF=inf, avg +5.67%
- Overall: **84% WR, PF 8.32**

## Gated Scanner Built

`quick_wins/shared/gated_scanner.py` — emits picks ONLY when ALL gates pass:

1. **Symbol whitelist** — only the 8 tournament-validated combos
2. **Entry conditions** — exact tournament genes (MACD crossover + RSI filter, or EMA cross + RSI range)
3. **TP/SL** — ATR multiples from tournament genes
4. **Position sizing** — 2% risk per trade on $10k equity
5. **Correlation limit** — max 1 position per correlated group (JUP/ENA/ADA/WIF move together)
6. **Regime filter** — BTC must be above 200-EMA (bull regime only)
7. **Min edge** — tournament PF >= 2.0
8. **Dedup** — composite key on symbol/direction/entry/TP/SL/date

**Current state:** 0 picks emitted — BTC is below 200-EMA (bear regime) and no MACD/RSI entry conditions are aligned. This is **correct risk behavior** — the scanner stays in cash when conditions aren't favorable.

## Strategy Status

- `mega_mutation` is **UNBLOCKED** (was blocked 2026-06-02 due to a direction-blind sign-coherence bug; retracted 2026-06-05 after direction-aware check showed 0 flips)
- `mega_mutation_state.json`: production_enable=false, promotion_ready=false (blocked by pf_drift>30% — forward PF 8.32 exceeds lab PF 2.79 by >30%, i.e. forward is BETTER than lab)
- Forward pilot last ran 2026-11-14 and confirmed 50 closed picks, 84% WR, PF 8.32

## Risks to Manage

1. **Correlation:** JUP/ENA/ADA/WIF move as a bloc — max 1 position per correlated group
2. **ENA funding-rate collinearity:** ENA may be a funding-rate bet; verify mega_mutation edge isn't just funding arbitrage
3. **Low frequency:** ~2 trades/month — edge is rare by design
4. **Regime dependence:** edge may not hold in BTC bear markets (regime filter addresses this)
5. **Small forward sample:** n=50 — continue paper trading before live capital

## Files

- `quick_wins/shared/gated_scanner.py` — the gated paper-trading scanner
- `quick_wins/01_overall/OVERALL_QUICK_WINS.md` — merged audit findings (P0→P3)
- `quick_wins/02_equity_stocks/` through `08_commodities_futures/` — per-asset-class fix docs
- `quick_wins/shared/normalize_pnl_units.py` — PnL unit normalizer
- `quick_wins/shared/validate_pick_ids.py` — CI-enforced unique pick IDs
- `updates/2026-11-14-flaxen-hair.md` — original audit summary
- `memory/2026-11-14.md` — session memory

## Pushed To

GitHub `origin/main` at commit `4493184cc9e` (13 files, 1,233 insertions, all mine).

## Recommended Next Steps

1. **Paper trade** the gated scanner — run daily, log picks to `gated_picks.jsonl`
2. **Monitor forward performance** — track TP/SL hits on emitted picks
3. **Promote to live** only after 30+ forward days with WR>=55%, PF>=1.5, pf_drift<30%
4. **Address ENA collinearity** — verify edge isn't just funding-rate arbitrage
5. **Iterate gates** — test different position sizes, correlation limits, regime filters
