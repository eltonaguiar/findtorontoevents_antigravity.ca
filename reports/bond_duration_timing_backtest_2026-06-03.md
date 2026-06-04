# BOND Duration-Timing — clean-bar backtest: REJECTED (negative alpha) (2026-06-03)

Same clean-bar method as ETF/commodity/FX/EQUITY. Duration timing via dual-momentum across the
bond duration spectrum: hold the strongest-momentum bond ETF beating short cash, else SHY. Universe
TLT/IEF/AGG/LQD vs SHY, benchmark AGG. 48mo walk-forward. Closes the BONDS#7 data gap with a backtest.

## Result — REJECTED
| Metric | Value | Bar | Pass? |
|---|---|---|---|
| Profit factor | 1.08 | ≥1.5 | ❌ |
| Sharpe | **0.10** | ≥1.0 | ❌ |
| Max drawdown | −4.7% | ≤20% | ✅ (but irrelevant given no return) |
| CAGR | 0.4% | — | — |
| **#111 attribution vs AGG** | alpha **−0.08%/mo**, t=−0.63, IR −0.09, beta 0.50 | alpha>0 | ❌ NEGATIVE alpha |
| Bootstrap PF 95% CI | [0.53, 2.41] | lower>1 | ❌ |

## Read
Duration timing produced **negative alpha** vs simply holding AGG (t=−0.63) and a near-zero Sharpe
(0.10). The 2022–2025 rate-hike-then-plateau regime punished duration rotation — the timing added
nothing over passive aggregate-bond exposure. Clear reject.

## Final scorecard — 5 archetypes, identical clean-bar pipeline
| Archetype | Attr t | beta | Sharpe | bootstrap lower | Verdict |
|---|---|---|---|---|---|
| **ETF dual-momentum** | **2.36** | 0.34 | 1.62 | 1.64 | ✅ **VALIDATED** (only one) |
| Commodity TSMOM | 0.84 | 0.72 | 0.67 | 0.78 | REJECTED |
| FX trend | 2.13 | −0.61 | 0.42 | 0.63 | MIXED (alpha real, weak) |
| EQUITY momentum | 1.98 | 1.13 | 1.65 | 1.73 | MIXED (high-beta + survivorship) |
| BOND duration-timing | −0.63 | 0.50 | 0.10 | 0.53 | REJECTED (negative alpha) |

**1 validated forward-candidate (ETF dual-momentum) out of 5 archetypes.** The gate-stack
discriminates cleanly: it admits genuine low-beta alpha and rejects beta/survivorship/regime-luck.

## Reproduce
`python3 verified_strategies/bond_duration_timing_backtest.py`
