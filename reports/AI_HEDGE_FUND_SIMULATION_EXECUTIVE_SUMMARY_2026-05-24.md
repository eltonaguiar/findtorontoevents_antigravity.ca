# AI Hedge Fund Simulation — Executive Summary
**Date:** May 24, 2026 | **Status:** LIVE PAPER SIMULATION — $0 real money deployed
**Simulation scope:** 22 forward-test picks across 6 asset classes | 3-round AI debate | 10+ models

---

## The One-Paragraph Verdict

This simulation has built real infrastructure — a functioning multi-model debate pipeline, a weekly resolver, statistical analysis with EV/Sharpe/Kelly, and risk-parity portfolio construction. But the system is **not ready for real money.** The confidence engine is inverted (higher reported confidence means lower win rate), two entire asset classes have zero resolved data (PENNY, FUTURES), the IPO strategy fails every statistical gate, and only 2 of 22 picks have a verified track record. The honest signal here is that the 3-round debate produced better risk-management findings than the underlying strategies produced alpha. Before a single dollar goes live: fix the confidence engine, add a minimum-sample-size gate, drop the zero-data classes, and verify every pipeline that currently shows n=0 in the resolved database.

---

## 1. What's Working (Proven Edges)

### Tier 1 Production Systems (OOS-Validated, Bootstrap-Confirmed)
| System | OOS n | WR | OOS PF | CI-95-Lower | Tier |
|--------|-------|----|--------|-------------|------|
| `kimi_signal_tracking` | 135 | 88.9% | 15.94 | 10.47 | Tier 1 |
| `aggregated_picks` | 383 | 78.1% | 7.02 | 5.71 | Tier 1 |

These two systems are the real deal. They have enough data that the bootstrap confidence intervals don't overlap 1.0 even at the 95th percentile. If any capital goes live, it flows through these two systems only.

### Verified-WR Anchor Picks (Only 2 of 22)
| Pick | WR | n | EV(R) | Status |
|------|----|---|-------|--------|
| PG SHORT $167.37 | 64.0% | 164 | 0.600 | **VERIFIED** |
| SOLUSDT LONG $157.39 | 65.0% | 23 | 1.015 | **VERIFIED** |

These are the only picks with a statistical basis. Everything else is estimated from confidence levels using a linear mapping that has zero empirical validation.

### The Debate Pipeline Is the Best Product
The 3-round debate (Risk Manager + Portfolio Manager + Quant + Behavioral + PM) produced more actionable findings than the strategies themselves. Specifically:
- **Identified the 80% confidence epidemic** — claiming 80% certainty on n=23 is mathematical malpractice
- **Caught duplicate MSFT entries** — the pipeline has no position deduplication
- **Flagged the n-threshold gap** — PENNY and FUTURES with 0 resolved data are generating live signals
- **Found the RR<1.0 leak** — picks risking more than they can make should be auto-rejected
- **Detected CL=F duplication** — the same instrument shorted twice at different prices

### Risk Parity Methodology (Deployed but on Estimated Data)
The risk-parity allocator (`tools/risk_parity_allocator.py`) correctly down-weights crypto (3.0% daily vol) and up-weights bonds (0.5% vol). However, it's running on 13 estimated-win-rate picks, so the weights are directionally right but numerically fragile.

---

## 2. What's Broken (Must Fix Before Real Money)

### Critical: ML Confidence Is Inverted System-Wide
The dashboard itself warns: **"Confidence is currently an anti-signal across asset classes."** The 0.85-0.90 confidence band has a 20% win rate. The 0.6-0.7 band (default range, 58% of all crypto trades) has a 23.3% WR. The system's confidence output is inversely correlated with actual outcomes. Using it for position sizing produces the opposite of the intended effect.

### Critical: No Minimum-Sample-Size Gate
PENNY stocks (MVST, KULR, QBTS) and FUTURES (ES=F, GC=F, CL=F) have **zero resolved data** — WR=0%, n=0. They are generating live signals in the pick list. Any system a hedge fund deploys would auto-reject any signal from a source with <50 resolved trades. This gate does not exist.

### Critical: FOREX Is Contaminated by Resolver Bug
63% of FOREX wins are 1-basis-point "resolver flicker" — the resolver uses live yfinance spot as the fill price, treating microscopic price noise as wins. The actual PF after correcting for this is below 1.0. FOREX picks are **blocked** (kill gate: 57.3% WR, -0.39% avg PnL) but the pipeline still produces them.

### Critical: COMMODITY Pipeline Broken
The two best COMMODITY systems (`multi_asset_cot` with dashboard PF=4.72, `multi_asset_copytrader` with PF=3.14) have **n=0 in `universal_resolved_picks.json`**. Their impressive dashboard stats come from a different data source without a pre-registered OOS split. These picks may not be resolving into the validated dataset at all.

### IPO Lockup Strategy Fails All Gates
Backtest results (2026-05-17): n=23, WR=34.8%, PF=0.18, total PnL=-164%. Fails 4/4 evaluable gates of the SS23 5-gate. The literature edge (Field & Hanka, -1.5% at lockup expiry) does not reproduce in the 2022-2025 sample. 2024 IPOs **rallied** through lockup windows, triggering the 15% stop-loss. The strategy is regime-fragile and must stay in the research sidecar.

### Data Quality: Only 6 of 22 Picks Have Verified WR
The other 13 picks use a linear confidence-to-WR mapping (Method 2/3 in the confidence methodology) that assumes 50% confidence = 50% WR. This is untested and likely wrong given the inverted calibration. 3 picks (PENNY) have zero data.

---

## 3. What's Missing (Data Infrastructure Gaps)

| Gap | Impact | Effort to Fix |
|-----|--------|---------------|
| **No live IPO scraper** | IPO lockup strategy starved of data; Nasdaq API only returns current-month IPOs | 4-6 hours (SEC EDGAR RSS + stockanalysis.com scrape) |
| **No insider trading tracker** | Cannot filter for insider accumulation/distribution ahead of events | Unknown (SEC Form 4 API is free but rate-limited) |
| **No ETF flow data** | ETF/BOND classes have n<10 OOS; no sector-rotation signals | 2-3 hours (ETF.com free daily flow data) |
| **COMMODITY pipeline not writing to resolved DB** | `multi_asset_cot` and `multi_asset_copytrader` picks are invisible to the OOS validator | Investigation needed — may be a config or table-name mismatch |
| **No covariance matrix for Kelly sizing** | Individual Kelly fractions assume uncorrelated bets; with clustered equity shorts and bond longs, actual optimal Kelly is 30-50% of individual | 1-2 hours (numpy covariance from price history) |
| **Stale IPO data** (800+ days) | The manual 24-IPO dataset ends in 2024; no 2025-2026 IPOs tracked | Same as IPO scraper row above |
| **Missing $500k risk-parity allocation implementation** | Methodology exists in statistical analysis but no executable script that outputs the 8-position portfolio with actual dollar sizes | 1-2 hours (wire up `tools/risk_parity_allocator.py` with the adjusted 8-position matrix) |

---

## 4. What's Next — Priority-Ordered Action Items

### P0 — Block Real Money Until Fixed
1. **Add n-threshold gate.** Minimum 50 resolved trades per source system before any signal passes. Reject all PENNY, FUTURES, FOREX picks at the gate. (~1 hour, edit `audit_trail/quality_gates.py`)
2. **Fix confidence engine.** Invert the mapping: if confidence 0.85-0.90 = 20% WR, then score = 1.0 - confidence. The model is anti-predictive — treat high confidence as a sell signal. (~2 hours, edit scoring in `alpha_engine/config.py` and/or `audit_trail/quality_gates.py`)
3. **Drop the zero-data picks.** Remove MVST, KULR, QBTS, ES=F, GC=F, FUTURES-CL=F from the active pick list. These have no statistical basis for inclusion. (~15 minutes)
4. **Fix CL=F duplication.** Keep the commodity entry at $68.25 (has RR=1.1). Drop the futures entry at $73 (WR=0%). (~15 minutes)

### P1 — This Week
5. **Investigate COMMODITY pipeline.** Confirm `multi_asset_cot` and `multi_asset_copytrader` picks are writing to the resolved database. If not, fix the pipeline. If they are writing but with different field names, fix the OOS validator to find them. (~2-4 hours)
6. **Add RR<1.0 auto-reject filter.** Any pick with risk/reward below 1.0 should not enter the pool. This catches the MSFT duplicate (RR=0.9, risking $13.20 to make $11.80). (~1 hour)
7. **Add duplicate detection.** Same symbol appearing twice in the active pick list with different entries should trigger deduplication. (~1 hour)

### P2 — Next Session
8. **Build IPO scraper.** SEC EDGAR S-1/424B4 RSS feed + Nasdaq IPO Calendar scrape. Target: 300+ IPOs from 2015-2025 for a real IPO lockup backtest. (~4-6 hours)
9. **Build insider trading tracker.** SEC Form 4 API (free, rate-limited) to flag insider buys/sells on active positions. (~3-5 hours)
10. **Build ETF flow data pipeline.** ETF.com free daily flow data or Alpha Vantage sector flow. Feed into ETF source-system growth. (~2-3 hours)
11. **Wire the $500k risk-parity portfolio.** Execute the 8-position adjusted portfolio from the statistical analysis into `tools/risk_parity_allocator.py` with real dollar amounts. (~1-2 hours)

### P3 — Ongoing
12. **Accumulate OOS data for `stocks_competition`.** At n=53 with AC1=0.74 (effective n~8), it's Tier 1 on paper but statistically fragile. Need n≥100 with AC1<0.3 before full-Kelly sizing. (~8-12 weeks at current emission rate)
13. **Re-run IPO lockup backtest with regime filter.** Test the strategy only when SPY/IWM is below 200-DMA (2022-like conditions where it actually worked). (~2 hours after IPO scraper is built)
14. **Add transaction cost model.** Subtract 0.15% round-trip from all crypto pnl_pct before computing PF. This reduces effective PF measurably for high-frequency systems. (~1 hour)

---

## 5. One-Week Prediction (Which Picks Resolve, and How)

The simulation resolver (`simulation-picks-resolver.yml`) fires Saturday May 30 at 23:00 UTC. Based on current market structure and the debate consensus, here are the directional calls:

### HIGH CONFIDENCE IN RESOLVING (these will trigger TP or hit exit)
| Pick | Direction | Prediction | Rationale |
|------|-----------|------------|-----------|
| **TLT LONG** $87.66 | BULLISH | **WIN** — bond bullish | The strongest consensus pick (7/7 models). Bonds rallied in risk-off week. TLT is the cleanest macro expression in the book. |
| **SPY SHORT** $726.80 | BEARISH | **WIN** — equity weakness | 7/7 models agreed this is the foundational bearish leg. Market correction continuing into late May. |
| **GLD LONG** $257.93 | BULLISH | **WIN** — gold bid | Stagflation-hedge thesis intact. Risk Manager found no red flags. |
| **PG SHORT** $167.37 | BEARISH | **WIN** — consumer staples fade | Only verified-WR equity pick (64% WR, n=164). Consumer staples underperforming in current tape. |

### MEDIUM CONFIDENCE
| Pick | Direction | Prediction | Rationale |
|------|-----------|------------|-----------|
| **SOLUSDT LONG** $157.39 | BULLISH | **WIN** — crypto relative strength | Verified WR=65%. SOL showing relative strength vs BTC/ETH. The only crypto pick with real statistical backing. |
| **WMT SHORT** $140.19 | BEARISH | **WIN** — retail weakness | Strong EV (0.783), high model confidence. Consumer discretionary pressure. |
| **XOM SHORT** $116.91 | BEARISH | **MIXED** — oil geopolitical risk | "The most honest pick" (Risk Manager). Low confidence (30%) but good RR (2.1). Oil is volatile on geopolitics — could go either way. PM cut it from top 5 due to redundancy with CL=F. |

### LOW CONFIDENCE / AVOID
| Pick | Direction | Prediction | Rationale |
|------|-----------|------------|-----------|
| **CL=F SHORT** $68.25 | BEARISH | **LOSS** — oil bounce risk | Near-zero EV (0.05 risk units). Geopolitical supply disruption could spike oil. The PM flagged CL=F as "first to cut" at 1.25% size. |
| **SHY SHORT** $82.36 | BEARISH | **LOSS** — rate cut expectations | Coin-flip with transaction costs. Both agents marked it as "skip" in debate. Shorting short-duration bonds when rate cuts are being priced in is counter-trend. |
| **ETHUSDT SHORT** $2,150.54 | BEARISH | **LOSS** — crypto rotation | Low Sharpe (1.85), estimated WR, conflicts directionally with SOLUSDT LONG. If SOL wins, ETH likely wins too — you'd be short one crypto and long another. |

### DO NOT COUNT
| Pick Class | Reason |
|------------|--------|
| ALL PENNY (MVST, KULR, QBTS) | WR=0%, no data. Cannot predict what you cannot measure. |
| ALL FUTURES (ES=F, GC=F, CL=F) | WR=0%, no data. Same. |
| ALL FOREX | Blocked by kill gate. 57.3% WR, negative average PnL. |

### Net Call
**5-7 wins, 3-4 losses, 6 no-calls (PENNY/FUTURES/FOREX).** The portfolio is short-biased (SPY/WMT/PG/XOM/CL=F/SI=F/ETHUSDT = 7 shorts vs TLT/GLD/SOL/BND = 4 longs). If equities correct further and bonds rally, the book prints. If equities rip on a Fed pivot, the shorts get stopped out. The position sizing from the statistical analysis (8-position adjusted portfolio, $100k) gives the shorts room to breathe with small allocations, but concentration risk on the equity-short cluster (SPY+WMT+PG = 39% of the 8-position portfolio) remains the single biggest vulnerability.

---

## Appendix: Key File Reference

| File | What It Contains |
|------|-----------------|
| `audit_dashboard/hedge_fund_simulation_20260524.html` | Full 3-round debate results (7 models, per-agent insights) |
| `reports/PICK_DEBATE_CONSENSUS_2026-05-24.md` | Risk Manager + Portfolio Manager consensus verdict |
| `updates/2026-05-24-cross-asset-statistical-analysis.md` | Per-pick EV/Sharpe/Kelly, correlation matrix, 8-position portfolio |
| `reports/statistical_edge_analysis_2026-05-16.md` | OOS-validated system rankings, bootstrap CI, promotion roadmap |
| `reports/CONFIDENCE_METHODOLOGY_2026-05-24.md` | 3 confidence methods, thresholds, calibration gap analysis |
| `reports/ipo_lockup_backtest_2026-05-17.md` | IPO lockup strategy backtest (fails all gates) |
| `tools/risk_parity_allocator.py` | Inverse-volatility capital allocator (deployed, needs wiring) |
| `.github/workflows/simulation-picks-resolver.yml` | Weekly GHA resolver (runs Saturday 23:00 UTC) |
| `alpha_engine/ipo_lockup_strategy.py` | IPO lockup strategy implementation (research sidecar, not wired) |

*Not financial advice. Educational/research simulation only. Zero real money deployed.*
