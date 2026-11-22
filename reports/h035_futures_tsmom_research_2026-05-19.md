# H-035 FUTURES Time-Series Momentum Diversified — 2026-05-19

_Generated 2026-11-22T08:50:23+00:00 by `tools/h035_futures_tsmom_research.py`._

## VERDICT: **REJECTED**

**Status: OPT-IN RESEARCH SIDECAR. HARNESS-GATED. FREE-DATA. NO PRODUCTION WIRING.** No caller in `quality_gates.py`, `dashboard_generator.py`, `passes_active_gate`, `calculate_smart_score`, or any pick-generation / scoring path. Fetches free public futures data, runs the backtest, gates through `edge_stability_harness` (imported UNMODIFIED), writes this report — nothing else. Multi-AI-D-path consensus (Grok + Claude swarm 2026-05-19).

## The signal (Moskowitz-Ooi-Pedersen 2012)

Time-series momentum across a diversified liquid-futures universe — equity indices, currencies, commodities, government bonds. The sign of each contract's trailing 12-month total return is the direction; each leg is vol-scaled to a target ~10% annualised volatility; the diversified book is equal-weighted; rebalance monthly.

- look-back: **12 months (252 trading days)**
- vol target per leg: **10.0% annualised** (realised over the trailing 60d, strictly past)
- conviction magnitude (harness score field): |z-score of trailing return against its own 60-obs strictly-past distribution|
- universe: ES=F, NQ=F, YM=F, RTY=F, 6E=F, 6B=F, 6J=F, 6A=F, CL=F, GC=F, HG=F, ZN=F, ZB=F

**Causal mechanism:** Moskowitz, Ooi & Pedersen 2012 documented the TSMOM premium across 58 contracts spanning equities, FX, commodities, bonds (1985-2009). The premium is consistent with under-reaction to information and delayed over-reaction by uninformed momentum traders. The diversification across uncorrelated futures classes is the moat — a single-class TSMOM book is noisier. A sound prior is NOT an edge; only the harness + cost verdict counts.

## Construction (legitimate density pattern from H-008/H-019/H-026/H-027/H-028)

- **FULL continuous-position diversified book** — one resolved record per (contract, day) on the daily-rebalance variant. NO sparse event filter, NO threshold. The daily variant is what feeds the harness; a parallel classical monthly-rebalance MOP book is computed for descriptive context only (monthly records are too sparse for the 14-day harness window).
- **Vol-scaling per leg** — weight = `TARGET_VOL / realised_vol_60d`, capped at 5x to keep extreme low-vol periods from blowing up. The record stores `weight` and `signed_ret = raw_ret * direction * weight`.
- **Strict no-look-ahead** — trailing return and realised vol are computed from prices STRICTLY at or before day D; the position is entered at close(D) and exited at close(D+1).

## Data (free sources only — yfinance =F continuous-front)

- **PRIMARY (verdict input):** yfinance `=F` continuous-front-month tickers (free, no key). The Claude swarm verdict (2026-05-19) was explicit: *"AQR publishes factor returns but NOT constituent positions. You need to reimplement using yfinance =F tickers."* So the yfinance reconstruction IS the real implementation.
- **OPTIONAL SANITY CHECK:** AQR's published monthly TSMOM factor return series, manually downloaded from <https://www.aqr.com/Insights/Datasets/Time-Series-Momentum-Factors-Monthly> into `tools/cache/aqr_tsmom_monthly.csv` (or `.xlsx`). When present, it is reported alongside the reconstruction as a smell-test — it CANNOT drive the harness (no per-contract positions).
- **Sample:** 76765 contract-day resolved records.
- All contracts sourced from live free yfinance data.

| Contract | class | records | wins | gross WR |
|---|---|---|---|---|
| ES=F | EQUITY | 6294 | 3363 | 53.4% |
| NQ=F | EQUITY | 6297 | 3419 | 54.3% |
| YM=F | EQUITY | 5887 | 3103 | 52.7% |
| RTY=F | EQUITY | 2047 | 1025 | 50.1% |
| 6E=F | FX | 6299 | 3159 | 50.1% |
| 6B=F | FX | 6208 | 3098 | 49.9% |
| 6J=F | FX | 6216 | 3203 | 51.5% |
| 6A=F | FX | 6197 | 3158 | 51.0% |
| CL=F | COMMODITY | 6275 | 3176 | 50.6% |
| GC=F | COMMODITY | 6267 | 3288 | 52.5% |
| HG=F | COMMODITY | 6272 | 3229 | 51.5% |
| ZN=F | BOND | 6245 | 3129 | 50.1% |
| ZB=F | BOND | 6261 | 3139 | 50.1% |

## Harness verdict (THE gate — `edge_stability_harness`, UNMODIFIED)

- per-window eff (new->old): `-0.20 +0.18 +0.01 -0.04 -0.17 +0.28 -0.01 -0.21 -0.02 +0.24 -0.16 -0.25 -0.12 -0.02 -0.20 +0.32 +0.05 +0.08 +0.35 +0.03 -0.10 +0.27 -0.17 +0.28 -0.06 +0.63 -0.15 -0.01 +0.17 -0.07 -0.13 +0.10 -0.04 +0.09 -0.07 -0.13 +0.07 -0.24 -0.07 -0.24 -0.26 +0.14 +0.08 -0.13 -0.11 +0.03 +0.18 -0.04 -0.34 +0.34 +0.03 -0.12 +0.23 +0.07 -0.23 -0.19 -0.15 -0.09 -0.17 -0.07 -0.05 -0.34 -0.22 -0.15 +0.23 -0.18 -0.36 +0.08 +0.14 -0.09 -0.08 +0.00 -0.21 -0.22 -0.06 -0.25 +0.31 -0.15 -0.23 -0.44 +0.18 -0.03 +0.02 -0.06 -0.16 +0.09 +0.07 +0.05 +0.04 +0.01 +0.21 -0.21 -0.33 +0.01 +0.18 +0.41 -0.01 -0.24 +0.29 -0.14 +0.34 -0.02 +0.22 -0.07 +0.01 -0.10 -0.20 -0.14 -0.25 +0.14 -0.15 -0.10 -0.14 -0.09 -0.02 -0.11 -0.19 -0.38 -0.16 +0.01 -0.05 -0.18 +0.15 -0.01 -0.05 -0.15 -0.15 +0.21 -0.14 +0.13 +0.09 +0.34 +0.03 -0.04 +0.14 +0.16 +0.12 -0.26 +0.40 +0.05 -0.20 +0.01 -0.08 +0.09 -0.29 +0.17 -0.46 -0.30 +0.14 -0.05 +0.23 -0.16 -0.09 -0.42 -0.25 +0.11 +0.31 -0.07 +0.09 +0.05 -0.33 +0.08 +0.28 -0.15 +0.30 +0.19 +0.32 +0.01 +0.05 +0.42 -0.01 -0.09 -0.26 -0.39 -0.19 +0.45 -0.26 -0.11 -0.03 +0.06 +0.33 +0.39 +0.05 +0.10 +0.17 -0.03 +0.18 -0.07 -0.21 +0.19 +0.29 -0.30 -0.04 -0.04 -0.14 +0.21 -0.28 -0.09 +0.25 +0.10 +0.06 -0.05 +0.03 +0.19 +0.19 +0.10 -0.23 -0.03 +0.18 -0.19 -0.18 -0.13 -0.34 -0.40 +0.06 -0.21 +0.23 -0.37 -0.05 +0.28 -0.12 -0.05 -0.13 -0.17 -0.02 +0.25 +0.01 -0.16 -0.19 +0.36 +0.14 +0.08 +0.36 -0.20 -0.30 -0.10 -0.15 +0.08 -0.07 -0.21 +0.39 -0.00 +0.06 -0.09 -0.47 -0.41 -0.04 -0.40 +0.11 +0.10 -0.17 +0.05 -0.01 +0.18 -0.21 -0.07 +0.23 -0.05 +0.28 -0.35 +0.08 +0.06 -0.23 +0.16 -0.14 +0.12 +0.03 -0.01 +0.01 -0.14 +0.27 +0.09 +0.08 +0.23 -0.11 -0.03 -0.01 -0.37 +0.10 +0.14 -0.05 +0.04 -0.03 -0.01 -0.33 +0.26 +0.28 +0.21 +0.22 -0.04 -0.47 +0.04 -0.20 -0.20 +0.06 +0.25 -0.11 +0.28 +0.08 +0.28 +0.17 +0.16 -0.15 +0.08 -0.09 +0.16 -0.03 -0.21 +0.20 +0.77 +0.02 +0.26 -0.24 -0.01 +0.14 +0.14 -0.03 +0.32 -0.03 -0.67 +0.08 +0.12 -0.37 +0.48 -0.17 -0.16 +0.31 +0.18 -0.04 -0.22 -0.00 -0.12 -0.09 +0.07 +0.04 +0.06 -0.33 +0.07 -0.11 -0.04 +0.27 -0.12 +0.17 +0.16 +0.31 +0.04 -0.12 +0.04 -0.55 -0.19 +0.08 +0.02 -0.21 +0.08 -0.51 -0.33 +0.10 +0.08 -0.07 -0.04 -0.21 -0.04 +0.25 +0.27 -0.04 +0.23 -0.21 -0.08 -0.06 +0.03 -0.18 -0.06 +0.16 -0.24 -0.28 +0.02 -0.39 -0.11 -0.43 +0.14 -0.11 -0.18 -0.06 +0.27 +0.10 -0.17 -0.15 -0.48 +0.24 +0.01 -0.06 +0.03 -0.11 +0.22 +0.09 -0.10 +0.26 +0.18 -0.17 +0.02 -0.10 +0.06 +0.22 -0.24 -0.29 -0.19 +0.22 -0.34 -0.28 -0.06 -0.27 -0.01 +0.18 -0.15 +0.05 -0.19 -0.13 +0.13 +0.12 +0.05 -0.19 -0.23 +0.31 -0.14 +0.20 +0.10 +0.31 -0.40 -0.14 +0.14 -0.18 -0.05 -0.09 -0.14 -0.04 +0.48 +0.07 +0.64 +0.02 -0.41 +0.05 +0.35 -0.07 -0.31 -0.28 -0.07 -0.11 -0.06 +0.18 -0.19 +0.01 +0.02 -0.26 -0.04 +0.39 +0.37 -0.08 +0.16 +0.24 +0.13 +0.28 +0.03 -0.04 +0.14 -0.22 +0.47 +0.31 -0.06 +0.33 -0.30 -0.19 +0.12 +0.19 -0.05 -0.06 -0.07 +0.02 +0.02 +0.04 -0.11 +0.13 -0.01 -0.13 +0.11 +0.11 -0.02 +0.18 -0.01 -0.05 -0.40 -0.30 +0.11 -0.04 -0.09 +0.27 +0.29 -0.14 -0.03 -0.05 -0.21 -0.02 +0.18 +0.10 +0.29 +0.08 +0.21 -0.28 +0.04 +0.06 +0.03 +0.05 -0.31 -0.21 +0.09 +0.05 -0.12 -0.20 -0.01 +0.16 -0.27 -0.77 +0.39 -0.15 +0.15 +0.51 -0.13 -0.14 +0.35 -0.00 +0.28 +0.10 +0.11 +0.19 -0.35 -0.07 +0.05 -0.32 +0.37 -0.16 -0.13 +0.05 -0.16 -0.32 -0.40 +0.18 -0.21 +0.01 -0.23 +0.13 +0.13 +0.05 -0.54 +0.03 -0.02 +0.20 -0.31 +0.04 +0.15 +0.15 -0.14 +0.05 +0.02 -0.13 -0.10 +0.01 -0.14 +0.28 -0.11 -0.07 +0.26 -0.06 +0.07 +0.12 -0.31 +0.20 -0.03 -0.20 +0.20 +0.24 +0.10 -0.00 +0.10 -0.14 -0.06 +0.27 +0.18 +0.21 +0.12 +0.15 +0.15 -0.00 -0.38 -0.09 +0.18 +0.34 -0.05 +0.14 -0.13 -0.04 -0.01 +0.06 -0.34 +0.03 -0.07 -0.03 -0.38 -0.15 -0.53 -0.04 -0.46 -0.22 -0.12 -0.43 -0.21 -0.36 -0.11 +0.26 -0.18 +0.09 -0.43 -0.12 +0.11 -0.02 +0.14 +0.16 -0.13 -0.50 +0.37 +0.20 -0.24 -0.01 +0.02 +0.24 +0.09 +0.01 -0.09 -0.10 -0.29 -0.24 -0.51 -0.12 -0.19 +0.10 +0.19 -0.09 +0.13`
- windows scored: 646  (strong 96: +40/-56)
- `is_admissible()`: False
- harness reason: REJECTED — strong in 96 windows but signs split (40+/56-); needs 3 same-sign

## Post-cost gate (10bps round-trip; net must keep >= 60% of gross)

- gross edge: **1.0048 bps/trade**
- net edge (after 10.0bps round-trip): **-8.9952 bps/trade**
- cost-survival: **-895.27%** (floor 60%)
- post-cost gate: **FAIL**

- pooled gross WR: 51.4%
- pooled net WR: 44.4%

## Honest conclusion

**H-035 was TESTED and REJECTED.** The diversified continuous-position construction gave the harness real window density, so it rendered a genuine verdict. The harness eff sign splits across windows — in-sample separation that flips sign across regimes (the same failure mode that killed H-014, H-038, method_a_score). Do NOT re-test this construction on this sample. Nothing is wired or sized.

## next_step

Harness kill — diversified TSMOM does not yield an admissible futures edge on this sample. Do NOT re-test this construction on this data.
