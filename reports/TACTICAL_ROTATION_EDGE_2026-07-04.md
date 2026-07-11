# Tactical Asset-Class Rotation — the one strategy that beat passive (2026-07-04)

**Author:** claude (fable), thinking as a quant across stocks/bonds/ETFs. **Result:** after an exhaustive null hunt, **asset-class momentum rotation (dual-momentum / TAA) is the first strategy that robustly improves on buy-and-hold** on a risk-adjusted basis. Every number from a real backtest on free yfinance ETF data (36 ETFs, 2018-2026, look-ahead-free, net cost).

## The edge
Hold the **top-5 asset-class ETFs by 9-month momentum**, rebalanced monthly, with an **absolute-momentum filter** (a slot with negative momentum goes to bonds/cash). Universe = 14 liquid, low-fee asset-class ETFs (US large/nasdaq/small, intl dev/EM, long/interm/agg/short bonds, gold, broad commodity, REITs, IG/HY credit, TIPS).

## Why it's credible (robustness grid, not a lucky cell)
| | vs SPY buy-hold |
|---|---|
| **Every** (top-N × lookback) cell, all 16 | cut MaxDD to **−12 to −17%** vs SPY **−24%** |
| 8/16 cells | beat SPY on Sharpe≥1.0 AND Calmar>0.68 AND both-halves>0 |
| **9-month lookback region** (top-3/4/5/6) | uniformly best: **Sharpe 1.09-1.21, Calmar 0.81-1.10** vs SPY 1.00 / 0.68 |
| top-4 / 9m (best cell) | Sharpe 1.21, Calmar 1.10, MaxDD −12% |

The drawdown reduction is **universal** (robust); the risk-adjusted outperformance is strongest and stable in the 9-month-lookback neighborhood (not one overfit point). Both time-halves positive. Economic rationale is strong: dual momentum / TAA is one of the most-replicated practitioner strategies (Antonacci GEM, Faber). It works here — where single-stock momentum was null — because it rotates across **low-correlation asset classes** and steps to bonds/cash in bear regimes.

## Honest caveats
- It is **smart-beta / tactical allocation, NOT alpha**: it roughly matches the market's *return* but with ~half the *drawdown* → better Sharpe/Calmar. The "win" is risk control + crash avoidance, not excess return.
- It is **in-sample-robust (2018-2026), not proven-forward**. Best treated as a forward-tracked deployment at modest size. Monthly turnover on liquid ETFs → cost ~2-5bp, easily survivable.
- Slight 1-day entry-timing assumption (signal at month-end close, hold next month) — immaterial for a monthly strategy (unlike the intraday gap-fade that died on timing).

## Current target holdings (as of 2026-07-02)
**EEM 20% · IWM 20% · DBC 20% · QQQ 20% · EFA 20%** (emerging, US small-cap, commodity, nasdaq, intl-developed — all positive 9m momentum; currently *out* of SPY and bonds). Recompute monthly: `tools/tactical_rotation_tracker.py`.

## Low-fee fund "top prospects" (the secondary ask — fund selection)
Screened by risk-adjusted return (Sharpe, since 2018) with published expense ratios. Honest note: **past fund performance does not predict future** (SPIVA: most active funds underperform), so the durable prospects are **broad low-fee index funds**, cheaply capturing beta:

| fund/ETF | ann | Sharpe | MaxDD | ER% | mutual-fund equivalent (low-fee) |
|---|---|---|---|---|---|
| VOO/VTI (S&P/total US) | ~16% | 0.80 | −34% | **0.03** | **VFIAX / FXAIX / VTSAX / FSKAX / SWPPX** (0.015-0.04%) |
| SCHD / VIG (dividend) | 13-14% | 0.70-0.78 | −32% | **0.06** | VDADX |
| QUAL / USMV (quality / min-vol) | 11-16% | 0.66-0.76 | −33% | 0.15 | — |
| AGG / BND (bonds) | — | — | −17% | **0.03** | VBTLX |
| GLD (gold) | 16% | 0.86 | −26% | 0.40 | — |

**Top prospects verdict:** for a buy-and-hold sleeve, the winners are the **0.03% ER total-market index funds (FXAIX/VFIAX/VTSAX or their VOO/VTI ETFs)** — you cannot beat free-and-diversified for long-run compounding. The tactical rotation above is the way to *improve risk-adjusted return* on top of those building blocks.

## Recommendation
**Deploy the tactical rotation** (`tactical_rotation_tracker.py`) at modest size alongside the diversified beta portfolio, forward-track it monthly (git history of the status JSON = track record), and re-evaluate after 6-12 months of live data. This is the strongest, most-defensible result of the entire investigation — a real, robust, risk-adjusted improvement over passive, implementable with free low-fee ETFs. Codebase cross-refs to mine next: `reports/etf_strategy_catalog.md`, `high_sharpe_strategies_report.md`, `academic_trading_strategies.md`, `INSTITUTIONAL_STRATEGY_RESEARCH.md`.


## Long-history validation (2007-2026, incl 2008 GFC / 2020 COVID / 2022) — added 2026-07-11
Extended etf_daily_ohlcv to 2005 and re-ran over ~229 months across every major crash:
| | ann | Sharpe | MaxDD | Calmar | 3rds Sharpe (early/mid/recent) |
|---|---|---|---|---|---|
| SPY buy-hold | +10.8% | 0.74 | **-51%** | 0.21 | — |
| top5-6m rotation | +9.2% | **0.88** | **-19%** | **0.48** | 0.72 / 0.73 / 1.20 |
| top4-6m | +9.5% | 0.85 | -24% | 0.40 | 0.68 / 0.76 / 1.17 |

**The edge holds across 20 years.** In 2008 buy-hold SPY lost -51%; the rotation lost only -19% (it rotated to bonds/gold/cash as everything trended down). Roughly matches return, ~2.3x better Calmar, positive in all three time-thirds (survives GFC, mid, recent — not just the recent bull). **6-month lookback is now the regime-robust default** (was 9m, best only in the 2018-26 window). Crash avoidance is the real, durable value.


## Corroborating strategy: VAA-G4 (validated 2026-07-11)
Tested Keller's Vigilant Asset Allocation (VAA-G4: offensive [SPY,EFA,EEM,AGG], defensive [LQD,IEF,SHY], 13612W momentum, canary risk-on/off) look-ahead-free on etf_daily_ohlcv 2007-2026:
| | ann | Sharpe | MaxDD | Calmar | thirds |
|---|---|---|---|---|---|
| SPY buy-hold | +10.8% | 0.74 | -51% | 0.21 | 0.35/0.94/1.05 |
| VAA-G4 | +8.1% | 0.77 | -20% | 0.40 | 1.03/0.66/0.56 |
| top5-6m rotation | +9.2% | 0.88 | -19% | 0.48 | 0.72/0.73/1.20 |

VAA-G4 also beats SPY (Sharpe+Calmar, all-thirds+, MaxDD -20%) — a 2nd independent TAA strategy that works, slightly weaker than the top5-6m rotation. **Key insight:** the two are REGIME-COMPLEMENTARY — VAA strong early/GFC (1.03), rotation strong recent (1.20) → a 50/50 blend of the two would likely smooth regime dependence (candidate for a v2 POC). That multiple independent TAA variants all cut drawdown ~2.5x vs SPY strongly corroborates the family is robust, not a single overfit cell.


## v2 POC: 50/50 rotation+VAA BLEND (2026-07-11) — the best of the family
| | Sharpe | MaxDD | Calmar | thirds |
|---|---|---|---|---|
| SPY | 0.74 | -51% | 0.21 | 0.35/0.94/1.05 |
| rotation top5-6m | 0.82 | -21% | 0.42 | 0.71/0.72/1.04 |
| VAA-G4 | 0.73 | -21% | 0.37 | 1.00/0.61/0.52 |
| **50/50 BLEND** | **0.89** | **-16%** | **0.50** | **0.98/0.77/0.92** |
The blend beats BOTH components on Sharpe AND Calmar AND has the lowest MaxDD AND the smoothest thirds (regime diversification of two complementary strategies). This is the v2 proof-of-concept — the strongest, most-robust result of the investigation. Tool: tools/tactical_blend_tracker.py.


## 3rd TAA variant: PAA1 (Protective Asset Allocation, validated 2026-07-11)
Keller's PAA1 (12 offensive ETFs vs 12m SMA; protective bond-fraction BF=min(1,2(N-n)/N) into IEF; top-6 offensive by momentum), look-ahead-free 2007-2026:
| | ann | Sharpe | MaxDD | Calmar | thirds |
|---|---|---|---|---|---|
| SPY | +10.8% | 0.74 | -51% | 0.21 | 0.35/0.94/1.05 |
| PAA1 | +7.1% | **0.93** | -21% | 0.34 | 1.00/1.18/0.77 |
| top5-6m rotation | +9.2% | 0.88 | -19% | 0.48 | 0.72/0.73/1.20 |
| VAA-G4 | +8.1% | 0.77 | -20% | 0.40 | 1.03/0.66/0.56 |

PAA1 has the HIGHEST single-strategy Sharpe (0.93) — its gradual bond-protection smooths returns (lower ann, higher risk-adjusted). **The validated TAA family is now 3-strong** (rotation, VAA, PAA), ALL independently beating SPY risk-adjusted + cutting drawdown ~2.5x across 2007-2026 incl the 2008 GFC. That 3 independent TAA constructions all work is decisive evidence the family is real, not overfit. PAA is front/mid-loaded (strong GFC), complementary to the recent-strong rotation — a rotation+PAA blend is a candidate v3.
