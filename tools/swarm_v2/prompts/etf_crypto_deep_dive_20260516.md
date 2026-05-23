# ETF & CRYPTO Deep-Dive: Statistical Edge Audit — 2026-05-16

You are a quantitative analyst reviewing a live trading system's performance data. Provide institutional-grade analysis and actionable recommendations. Be concise, data-driven, and specific.

## System Context

This is a multi-source algorithmic trading system (findtorontoevents.ca/audit) tracking picks across CRYPTO, EQUITY, ETF, FOREX, and other asset classes. Performance tiers:
- Tier 1 (Renaissance): PF>2.0 / WR>55% / MDD<10%
- Tier 2 (Hedge Fund): PF>1.5 / WR>50% / MDD<20%
- Sub-floor: PF<1.0 or WR<45% at scale

## ETF Analysis (n=105 resolved, WR=66.7%, PF=2.25 per dashboard)

### ETF Source System Breakdown (from 105 resolved picks):
| Source | n | W | L | WR | PF |
|---|---|---|---|---|---|
| kimi_riseoftheclaw | 99 | 56 | 43 | 56.6% | 1.39 |
| crypto_ml_edge | 4 | 3 | 1 | 75.0% | 1.19 |
| alpha_engine_fast | 1 | 1 | 0 | 100% | inf |
| goldmine_stocks | 1 | 0 | 1 | 0% | 0.00 |

### ETF Strategy Breakdown (significant strategies, n>=3):
| Strategy | n | WR | PF | Notes |
|---|---|---|---|---|
| adx-trend-scout | 10 | 80.0% | 6.91 | ELITE |
| rs-breakout-scout | 13 | 84.6% | 2.55 | Strong T1 |
| macd-hidden-div-scout | 4 | 75.0% | 3.85 | Strong |
| quality-momentum-scout | 4 | 50.0% | 3.25 | Good |
| vwap-reversion-scout | 4 | 75.0% | 2.86 | Good |
| intermarket-flow-scout | 19 | 63.2% | 1.96 | LARGEST, near-T1 |
| quality-minus-junk | 12 | 50.0% | 1.05 | Drag |
| quick_engine | 4 | 75.0% | 1.19 | Drag |
| betting-against-beta | 4 | 25.0% | 0.44 | CUT |
| rsi-divergence-scout | 3 | 33.3% | 0.63 | CUT |
| call-surge-scout | 3 | 33.3% | 0.26 | CUT |
| vol-contraction-scout | 3 | 0.0% | 0.00 | CUT |
| options-flow-scout | 3 | 0.0% | 0.00 | CUT |
| pairs-trading | 3 | 0.0% | 0.00 | CUT |

### ETF Symbol Performance:
| Symbol | n | WR | PF | Total PnL% |
|---|---|---|---|---|
| QQQ | 19 | 78.9% | 4.61 | +23.83 (PROMOTE) |
| XLK | 16 | 75.0% | 4.26 | +29.73 (PROMOTE) |
| SPY | 15 | 60.0% | 1.95 | +7.44 |
| XLE | 15 | 53.3% | 1.15 | +3.51 |
| GLD | 11 | 36.4% | 0.65 | -6.23 (REVIEW) |
| IWM | 19 | 36.8% | 0.41 | -14.82 (BLACKLIST?) |
| SLV | 2 | 0.0% | 0.00 | -15.74 (BLACKLIST) |

### Dashboard Discrepancy:
Dashboard shows n=75 with WR=66.7%/PF=2.25 (post-noise-filter), but raw resolved_picks shows 105 WON/LOST records with lower performance. The noise filter appears to correctly remove ~30 low-quality picks.

## CRYPTO Analysis (n=2961 resolved in sample, overall WR=45.6%, PF=1.25)

### CRYPTO Source System Breakdown (n>=50, sorted by PF):
| Source | n | WR | PF | Status |
|---|---|---|---|---|
| battleground | 68 | 41.2% | 0.55 | CUT IMMEDIATELY |
| luxalgo_filters | 765 | 43.5% | 1.00 | Break-even, 26% of volume |
| alpha_engine | 353 | 45.0% | 1.03 | Marginal |
| regime_terminal | 72 | 34.7% | 1.06 | Low WR drag |
| signal_engine_mutations | 92 | 38.0% | 1.15 | Below floor |
| mercury2 | 160 | 38.8% | 1.28 | Below floor |
| quan_engine | 343 | 34.4% | 1.30 | Low WR drag (12% volume) |
| baby_strats_forward | 568 | 52.8% | 1.64 | Near T2 |
| claude_gainer_st | 106 | 58.5% | 1.66 | T2 range |
| aggregated_picks | 54 | 48.1% | 1.68 | Good |
| kimi_riseoftheclaw | 87 | 59.8% | 1.71 | T2 range |
| dna_winner_picks | 112 | 53.6% | 1.91 | Near T2 |
| mega_mutation | 94 | 60.6% | 2.61 | ELITE T1 |

### CRYPTO PF Simulation (removing drag sources):
- All sources: PF=1.25, WR=45.6% (n=2961)
- Remove quan_engine: PF=1.25, WR=47.0% (n=2618)
- Remove quan+battleground: PF=1.26, WR=47.2% (n=2550)
- Remove quan+battleground+luxalgo_filters: PF=1.41, WR=48.7% (n=1785)
- Elite systems only (mega_mutation, signal_validation, kimi_signal_tracking, etc.): PF=2.27, WR=55.7% (n=174)

### CRYPTO Top 10 Winning Symbols (by total PnL):
| Symbol | n | WR | Total PnL% |
|---|---|---|---|
| ONDOUSDT | 213 | 47.4% | +167.61 |
| JUPUSDT | 98 | 53.1% | +73.96 |
| WIFUSDT | 56 | 51.8% | +72.37 |
| SEIUSDT | 41 | 78.0% | +70.30 |
| POLUSDT | 19 | 68.4% | +37.98 |
| ETHUSDT | 227 | 50.2% | +35.60 |
| ENJUSDT | 8 | 75.0% | +32.45 |
| DYDXUSDT | 12 | 100.0% | +30.61 |
| DOGE-USD | 18 | 55.6% | +29.92 |
| INJ-USD | 3 | 100.0% | +24.97 |

### CRYPTO Top 10 Losing Symbols (by total PnL):
| Symbol | n | WR | Total PnL% |
|---|---|---|---|
| FETUSDT | 28 | 35.7% | -50.81 |
| BCH-USD | 6 | 16.7% | -28.74 |
| TONUSDT | 10 | 20.0% | -17.02 |
| ETH-USD | 18 | 27.8% | -16.15 |
| ARBUSDT | 61 | 39.3% | -15.26 |
| STXUSDT | 70 | 47.1% | -14.43 |
| TAOUSDT | 6 | 0.0% | -12.50 |
| BTC-USD | 17 | 29.4% | -11.43 |
| TREEUSDT | 5 | 0.0% | -11.00 |
| HYPEUSDT | 49 | 24.5% | -10.62 |

## Research Questions

Please answer each question with quantitative reasoning:

**Q1 — ETF: Is the dashboard PF=2.25 noise-filtered number trustworthy at n=75?**
What confidence interval on WR and PF should we apply at n=75? What's the minimum n for a 90% confidence that WR > 55% given current observation of 66.7%?

**Q2 — ETF: Path to n=100 stable status**
Given the ETF source is almost entirely `kimi_riseoftheclaw` (99/105), what are the risks of concentration? What's the recommended diversification approach? At what generation rate does n=100 become meaningful for stable classification?

**Q3 — ETF: Which strategies should be cut vs promoted?**
Given the strategy breakdown above, which strategies clearly have edge (PF>2, WR>60%) and which are destroying value? What would ETF overall PF look like after cutting `betting-against-beta`, `rsi-divergence-scout`, `call-surge-scout`, `vol-contraction-scout`, `options-flow-scout`, and `pairs-trading`?

**Q4 — ETF: IWM anomaly — is IWM (small-cap ETF) structurally wrong for our strategy?**
IWM has n=19, WR=36.8%, PF=0.41, total_pnl=-14.82%. Meanwhile QQQ (n=19) has WR=78.9%, PF=4.61. What's the likely explanation and should IWM be blacklisted?

**Q5 — CRYPTO: Is luxalgo_filters genuinely break-even or just low-signal?**
luxalgo_filters has n=765, WR=43.5%, PF=1.00 using a single strategy (luxalgo_confluence). With PF=1.00 at 765 picks, it is destroying expected value after costs. What would be the expected cost-adjusted PF assuming 0.1% round-trip cost? Should it be cut or reformed?

**Q6 — CRYPTO: mega_mutation (PF=2.61, WR=60.6%, n=94) — what makes it elite?**
This is the best performing CRYPTO system at meaningful scale. What trading patterns correlate with a 60%+ WR in crypto? How should we promote/replicate this system's picks?

**Q7 — CRYPTO: ONDOUSDT concentration risk**
ONDOUSDT has n=213 (7.2% of all crypto sample picks), WR=47.4%, total_pnl=+167.61. However, quan_engine uses ONDOUSDT for 205/343 of its picks (60%). Is this a real edge or data artifact/backtesting bias?

**Q8 — CRYPTO: Losing symbols (FETUSDT, HYPEUSDT, BCH-USD)**
FETUSDT: -50.81% on n=28, WR=35.7%. HYPEUSDT: -10.62% on n=49, WR=24.5%. These symbols appear structurally broken. What's the mechanism (mean-reverting, regime-sensitive, news-driven?) and should they be blacklisted immediately?

**Q9 — System-level: What's the fastest path to Tier 1 (PF>2.0) for CRYPTO?**
Given elite systems (mega_mutation, signal_validation, kimi_signal_tracking) achieve PF=2.27 at n=174, but the system has 7815 total picks dragged by weak sources — what volume/source pruning plan gets overall CRYPTO to PF>1.5 (T2) within 30 days?

**Q10 — Portfolio allocation: ETF vs CRYPTO sizing**
If ETF is genuinely at PF=2.25/WR=66.7% (n=75) and CRYPTO is at PF=1.32/WR=46.9% (n=7815), what's the Kelly-fraction-based capital allocation between them? What position sizing multiplier should ETF get vs CRYPTO?
