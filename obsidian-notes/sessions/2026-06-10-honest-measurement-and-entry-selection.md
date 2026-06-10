---
tags: [session, money-ready, resolver, entry-conditioning, 2026-06-10]
created: 2026-06-10
asset_classes: [CRYPTO, EQUITY, COMMODITY, FOREX]
---

# 2026-06-10 — Honest Measurement Live + Entry-Selection Pivot

The 12-hour autonomous run that closed the measurement-layer chapter and opened the entry-selection one.

## The chapter that closed: measurement is honest now
- **Entry-anchored intrabar resolution is the production default** (`RESOLVER_ENTRY_ANCHORED=1`). The 23–24% win-rate inflation from close-walk/stale-window replay is gone. Rollback flag = `0`. Harness `tests/test_resolver_intrabar_accuracy.py` 15/15.
- **The honest verdict flows to the live site**: `money_ready_verdict.json → classes.<CLASS>.intrabar_truth` (from `at_signal_outcomes.intrabar_*`). Nested shape: `{generated_at, classes:{...}, drift, summary}`. Both writer workflows env-complete and self-sustaining.
- **0/9 classes money-ready, honestly.** CRYPTO n=1154 32.4%/PF0.73; EQUITY n=107 34.6%/PF0.47 — both crossed n≥100 and FAIL. Small-n "leads" dissolve as n grows. PBO 0.822 (FAIL≥0.7) correctly blocks promotion.

## The chapter that opened: it's an ENTRY problem
- **σ-geometry experiment = NULL.** Vol-scaled TP/SL cuts TIME_EXIT and manufactures payoff asymmetry, but win-rate drops in exact compensation. Conclusion: **our losses are wrong-way ENTRY/selection losses, not exit-geometry losses.** No exit math fixes a bad entry distribution.
- **First disciplined entry candidates** (R1 time-split / R2 concentration<35% / R3 p<0.005): CRYPTO RSI(14,1h) 50–70 × US-session (n=108, 47.2%/PF1.54 vs baseline 32%/0.72 — tracked, below the 50% promote bar); `luxalgo_confluence` SHORT cell (n≈41, ~68%/PF~2, all-recency caveat). Negative entry filters: FOREX trend-contrarian ≈76% of class losses, EQUITY high-vol concentrates losses.
- **Forward measurement lane**: `tools/stamp_entry_conditions.py` → `entry_conditions_forward.json` (read-only, no-look-ahead). Promote nothing until n≥100 + R1/R2/R3 re-pass.

## Data hygiene this run (all backed up to ejaguiar1_backups)
+591 NULL-pnl recovered · 93+7 corrupt rows + 2 sign-flips quarantined/purged · 827k OHLCV bars backfilled · +221 honest rows · PBO 1.0→0.822 · Option-A signal-week dedup + all 3 crypto callers threaded.

## Open items filed to incidents (2026-06-10)
CRYPTO ADV liquidity gate orphan (is_liquid_crypto unwired) · FOREX carry = hardcoded snapshot not live FRED · portfolio factor-risk/de-gross kill-switch (Model Portfolios) · per-class R:R floor gate · look-ahead leakage CI gate · 41 CI tests quarantined (drift) need reconciliation.

## Do-not-relitigate
stocks_rsi2_pullback, CRYPTO direction-flip, futures_momentum/forex_rsi2 shadow, luxalgo "best-in-system", MeanReversionBB, trust=7, alpha_engine×CRYPTO 80.6%, `kimi_ultimate_proven_edge` (MiniMax-authored, self-admitted SYNTHETIC).

## Sources
`reports/MASTER_PROGRESS_2026-06-10.md` · `reports/entry_conditioning_experiment_2026-06-10.json` · `reports/sigma_geometry_experiment_2026-06-10.json` · `reports/md_2month_findings_sweep_2026-06-10.md` · `reports/kimi_insights_sweep_2026-06-10.md`
