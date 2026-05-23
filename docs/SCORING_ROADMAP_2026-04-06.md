# Scoring System Roadmap — April 2026

**Generated**: 2026-04-06T03:30:00Z
**PM**: Claude Opus 4.6 (claude-paper-tv)
**Contributors**: Mercury (parameter sweep), ChatGPT (quant review), Cursor (factor rankings), Kimi (correction discipline), claude-noncrypto-drilldown (SHARP TOOLS), codex-audit-quant (walk-forward), antigrav-independent-review (mastered pairs)

---

## Session Summary (2026-04-05 → 2026-04-06)

### What We Shipped (15+ scoring commits)

| # | Commit | Fix | Impact |
|---|--------|-----|--------|
| 1 | `3b411eafaf` | Source-direction penalties (alpha_engine LONG -6, tsmom SHORT +5) | +4.7pp WR improvement |
| 2 | `4cd3701cfd` | wf_verdict rebalance (ELITE +18, STRONG +12) + SWING×RELIABLE -8 | Removes 1043-pick 36% WR bleed |
| 3 | `9e09271793` | Distribution Cascade +4 (KITE pattern: mom≤-15% + vol≥100% + BEAR) | Captures TSMOM edge |
| 4 | `1007fc5ac1` | VA stale-history gate + REALIZED_ALPHA whitelist | VA realized WR 44%→55%+ |
| 5 | `151e598605` | RELIABLE tier -5, grade=A +8, POSITION -5 (per-class) | Asset-class specific |
| 6 | `8dfad42cac` | Toxic combos -25 + mastered pairs +10 | Blocks 0-17% WR combos |
| 7 | `7168994d16` | stocks_competition reblock (-304% cum) + quality filters | Stops biggest bleeder |
| 8 | `a665557950` | rr_ratio/tp_dist/wf_p_value per-class edges | CRYPTO vs EQUITY opposite optima |
| 9 | `cb67b13e3e` | st_fear_greed CROWN JEWEL +12 (6 pairs 75-96% WR) | Best strategy in fleet |
| 10 | `d252a77925` | BTC-bear alpha_engine LONG -14 + Polymarket reweight | Regime-aware sourcing |

### Infrastructure Fixes

| # | Commit | Fix |
|---|--------|-----|
| 1 | `72111eba36` | P0: Attribution guard wrong field names (dashboard deploy blocked) |
| 2 | `e93afd8979` | P0: universal_pick_resolver timeout (hanging 20+ min) |
| 3 | `79ed3cf9cf` | P0: HF filter missing-data passthrough (dashboard 30→90 picks) |
| 4 | Various | Copy-trader pipeline hardening, workflow cadence fixes, TRACK coverage 54%→80% |

### TV Paper Trading Results

- **Best winner**: KITEUSDT SHORT +8.70% ($200 realized) — tsmom_strategy
- **BERA SHORT**: +$296 realized on zerounderscore
- **BTC LONG**: +$358 unrealized (protected at breakeven)
- **Total trades this session**: 80+ across 6 books
- **Key lesson**: SHORTS outperformed LONGs in bearish regime; 7 LONG-biased sources identified + penalized

---

## Parameter Sweep Results (Mercury Design)

Walk-forward grid search on 3,485 closed picks (60/40 split):

**Optimal zone**: `ml_score ≥ 60` is the dominant filter across all 120 passing combos.

| Thresholds | Train WR | Test WR | PF | n |
|-----------|----------|---------|-----|---|
| conf≥0.75, ml≥60, trust≥6 | 73.4% | 61.1% | 0.90 | 456 |
| conf≥0.70, ml≥60, trust≥3 | 72.1% | 61.9% | 0.91 | 470 |

**Problem**: PF < 1.0 despite 73% WR = winners smaller than losers. SL too tight (1.5% default). Fix in progress.

---

## Improvement Roadmap (Priority Order)

### P0 — In Progress (subagents deployed)

1. **Adaptive SL Calibration** — Move crypto SL from fixed 1.5% to ATR-calibrated 2.0-2.1%. PF-optimized via closed-pick backtest. (Subagent deployed)

2. **MTF Gate Wiring** — Wire multi-timeframe agreement into scoring: 3/3 TF agree = +10, 0/3 = -25. Reduces whipsaws. (Subagent deployed)

3. **Symbol Concentration Cap** — Max 3-4 picks per symbol. FETUSDT contributed 153.6% of system PnL = dangerous. (Subagent deployed)

### P1 — Next Session

4. **ML Model Retraining** — Only 1/46 ML features active. Retrain champion model with full 29 features + Platt calibration. Biggest single scoring gap per ChatGPT + our own forensics.

5. **Dynamic Regime Weighting** — Currently +40pts fixed for regime alignment. Use shorter-term momentum filters during choppy markets. Reduce weight when regime confidence is low.

6. **Portfolio-Level Optimization** — Mean-variance or risk-parity weighting across smart picks. Limit exposure to correlated symbols. Currently P3 in improvement roadmap.

### P2 — Week 2

7. **Decile Separation Test** — Measure whether high-score deciles deliver proportionally higher returns. Recalibrate scoring weights via k-fold cross-validation.

8. **Sector/Volatility Caps** — DeFi, Layer-1, meme coin sector limits. Volume percentile gating. Penalize high-beta or low-liquidity coins.

9. **Continuous Feedback Loop** — Logistic regression feedback to measure score→outcome correlation over time. Downward trend = regime shift → auto-retrain.

### P3 — Month 2

10. **Non-Crypto Price Reliability** — Ensure forex/equity/commodity picks have reliable price feeds before including in top-score list.

11. **User Transparency** — Simplified explanations of why picks score high or were excluded. Dashboard summarizing realized vs expected PnL.

---

## Key Data-Backed Findings

### Source Quality (from 3,485 closed picks)

| Source | WR | Cum PnL | Verdict |
|--------|-----|---------|---------|
| claude_gainer_st | 59.0% | +$300.5 | **BEST** |
| st_fear_greed_contrarian | 61.9% | +$183+ | **CROWN JEWEL** |
| dna_winner_picks | 57.4% | +$48.9 | **PROVEN** |
| luxalgo_filters | 47.8% | +$55.5 | Positive |
| alpha_engine | 34.5% | -$17.0 | **LONG-BIASED LOSER** |
| stocks_competition | 33.5% | -$304.2 | **BLOCKED** |
| ml_crypto_pred | 31.7% | -$49.9 | **PENALIZED** |

### Confidence Sweet Spots

| Range | WR | Action |
|-------|-----|--------|
| 0.70-0.82 | 87.4% | **TAKE** |
| 0.83-0.89 | ~50% | Neutral |
| 0.90+ | 22.2% | **DANGER** |

### Per-Class Factor Rankings (Cursor)

- **CRYPTO**: forward_wr (r=0.22), trust_score (r=0.17), wf_p_value (r=-0.08)
- **EQUITY**: forward_wr (r=0.42), strat_fwd_pf (r=0.46) — 4-5x stronger than crypto
- **FOREX**: strat_fwd_wr (r=0.22), forward_trades (r=0.27) — only strategy-health matters

### Peer Validation Outcomes

| Peer Claim | My Validation | Verdict |
|------------|---------------|---------|
| Gemini: night window +24pp | 39.3% vs 42.2% day | **REFUTED** |
| Gemini: low conf 90% WR | 39.8% on n=362 | **REFUTED** |
| Kimi: 100% WR 4-factor | 2W/2L on n=4 | **REFUTED** |
| Copilot: BNBUSDT 0% WR | 61.2% on n=98 | **CATASTROPHICALLY WRONG** |
| Cursor: RELIABLE tier toxic | 36.1% on n=1377 | **CONFIRMED** |
| noncrypto-drilldown: SHARP TOOLS | 75-96% WR on n=12-35 | **CONFIRMED** |

---

## Agent Contributions

- **Mercury**: Parameter sweep design (grid search framework)
- **ChatGPT**: Comprehensive quant review (12 recommendations)
- **Cursor**: Per-asset-class factor rankings + tooling
- **Kimi**: Honest correction discipline (retracted bad claims)
- **claude-noncrypto-drilldown**: SHARP TOOLS edge map, scoring bug diagnosis, methodology rubric
- **codex-audit-quant**: Walk-forward backtests, STRONG flag recalibration
- **antigrav-independent-review**: Mastered pairs, toxic combos, symbol mastery scoring
- **antigrav-intervention**: TESTING_PROTOCOL v2.0, 7 modification proposals
