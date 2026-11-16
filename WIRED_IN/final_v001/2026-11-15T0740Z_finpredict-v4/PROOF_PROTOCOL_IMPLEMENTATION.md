# PROOF_PROTOCOL_IMPLEMENTATION — how each gate is run

**Folder**: `WIRED_IN/final_v001/2026-11-15T0740Z_finpredict-v4/`

This maps the project's mandatory 10-gate standard (from `Summary.MD` and `PROFITABLE_SCORING_FRAMEWORK.md`) to concrete runnable checks for the three active candidates (BTC sma200, GLD sma200, vwap-reversion-scout).

## The 10 gates

| Gate | Requirement | Concrete implementation |
|---|---|---|
| 1 Temporal discipline | strict chronological train/test; features from past only | weekly signal uses `shift(1)`; last 40% = OOS |
| 2 Walk-forward | stability heatmaps | sweep sma∈{180..220}; ≥60% profitable folds; mean OOS PF>1.2 |
| 3 Multiple-testing | Bonferroni/Holm across configs | α_adj = 0.05 / m (m = # configs tried) |
| 4 Monte Carlo | block-bootstrap; % positive after costs; 5th% worst case | 10k resamples of weekly net returns |
| 5 Friction model | spread, commission, slippage, funding, tax; breakeven | 10bp RT + vol-adjusted slippage for BTC (0.25% maker-taker on Binance) |
| 6 Bootstrap CI | mean excess return excludes zero; t-stat; p | 5th percentile PF>1.0, Sharpe>0 |
| 7 Regime robustness | positive expectancy in majority regimes | split bull/bear/sideways; require majority positive |
| 8 Shuffle control | permuted prices must NOT reproduce | permute returns; strategy edge must vanish |
| 9 Pre-registered forward test | defined protocol + duration + thresholds | n≥100 (BTC/GLD), n≈155 (vwap); PF≥1.3; WR≥55%; bootstrap 5th%>0 |
| 10 Reproducibility | fixed seeds; versioned data; documented; runnable | seed, pinned data snapshot, runnable script |

## Where each runs today

- BTC / GLD: extend `experiments/crypto_sma200_oos_protocol.py` (exists) and add a GLD analog with the 1% wealth-margin gate.
- vwap-reversion-scout: pre-register clock per `FORWARD_TEST.md`; wire PnL validation through `qa_ledger.py` (live market-data check), not self-reported.

## File outputs expected per candidate

- `proof/wfo_<cand>_heatmap.png` — walk-forward efficiency.
- `proof/monte_<cand>_boot.png` — 10k-path bootstrap distribution.
- `proof/shuffle_<cand>.txt` — permuted-series negative result.
- `proof/regime_<cand>.json` — regime-split net expectancy.
- `proof/forward_clock_<cand>.json` — running forward-test status (n, t, PF, boundary).

## Standard verdict transition

- Gates 1-8 all PASS → `PROMISING` → run Gate 9.
- Gate 9 PASS → `PROVEN` → sizing allowed.
- Any gate FAIL → `REJECT`, recorded in `DECISION_LOG.md`, no re-test.

## Non-negotiables

- `shift(1)` on all signals (no look-ahead).
- Cost model is never zero.
- Multiplicity correction is never skipped.
- No backfill after seeing a result — forward clock only.
- `sizing_allowed:false` until `PROVEN`.
