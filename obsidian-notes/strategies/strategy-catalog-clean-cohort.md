---
tags: [strategy, catalog, clean-cohort]
created: 2026-06-09
status: active
---

# Strategy Catalog — Clean Cohort (live DB, 2026-06-09)

> Source: `at_pick_outcomes`, clean cohort = exclude backfill + NULL-resolved + banned sources + per-class sane-pnl guard; EXPIRED counts as non-win. This is the HONEST per-strategy view — not raw dashboard numbers.
> **None clears the money-ready bar** (n≥100, ≥3 months, PF>1.5, WR>52%, intrabar-validated). Treat all as research/paper only.

## Top strategies by clean resolved n

| Strategy | Class | n | WR% | PF | months | Read |
|----------|-------|---|-----|-----|--------|------|
| unknown | CRYPTO | 305 | 40.0 | 1.31 | 2 | unlabeled bucket; not a strategy |
| hs_lb_None | CRYPTO | 261 | 50.6 | 3.26 | 2 | only 2 months; PF inflated by few big wins — verify |
| (blank) | CRYPTO | 250 | 39.2 | 0.46 | 2 | losing; unlabeled |
| MeanReversionBB | EQUITY | 214 | 44.9 | 1.88 | 2 | best-volume equity; single-snapshot May; not durable |
| alpha_engine | UNKNOWN | 108 | 49.1 | 0.71 | 1 | losing |
| **luxalgo_confluence** | CRYPTO | 87 | 69.0 | 5.38 | **3** | only clean-subset that clears 3mo; but 87 of 2040 raw rows (4% clean) — NOT intrabar-validated; treat as artifact until confirmed |
| MeanReversionBB | FOREX | 69 | 0.0 | — | 2 | 100% expire; dead |
| MomentumEMA | EQUITY | 66 | 15.2 | 0.36 | 2 | losing |
| enhanced_ml_A_xgboost | CRYPTO | 58 | 20.7 | 0.41 | 1 | losing |
| futures_momentum | COMMODITY | 42 | 52.4 | 1.12 | 1 | 1 month only |
| battleground_ml_relaxed_mut | CRYPTO | 31 | 71.0 | 4.35 | 1 | 1 month — small-n artifact pattern |
| claude_ml_moderate_mut | CRYPTO | 31 | 61.3 | 2.74 | 1 | 1 month |
| battleground_vwap_1h_mut | CRYPTO | 24 | 58.3 | 2.25 | 1 | 1 month |
| MeanReversionBB | CRYPTO | 22 | 59.1 | 2.63 | 2 | small-n |

## Reading guide
- **High WR/PF on n<50 or 1 month = small-n artifact**, not edge (the recipe warns against this).
- The intrabar verdict for CRYPTO picks now lives in `trading_picks.intrabar_*` (parallel columns) — re-screen there before trusting any WR.
- Banned/refuted (do NOT re-emit): `multi_asset_scanner`, `forex_carry_momentum`, `forex_rsi2_mean_reversion`, `myfxbook_retail_contrarian`, `ig_contrarian_sentiment`, `regime_terminal`, `cta_replicator`, + the `multi_asset_*` family. See [[reference/banned-sources]].

## Class verdict (clean cohort)
| Class | n | WR | PF | verdict |
|-------|---|----|----|---------|
| CRYPTO | 1773 | 46.6% | 1.25 | sub-T2 / coin-flip (39.6% after intrabar) |
| EQUITY | 358 | 32.4% | 1.30 | not durable (single-snapshot) |
| FOREX | 117 | 8.5% | 0.63 | catastrophic |
| COMMODITY | 46 | ~50% | ~1.0 | insufficient |

## Related
- [[reference/edge-rescue-roadmap]]
- [[strategies/READY-TO-TRADE-NOW]]
- [[sessions/2026-06-09-rescue-fixes-and-benefits]]
- `reports/OBS_FINDING_JUNE8.MD`
