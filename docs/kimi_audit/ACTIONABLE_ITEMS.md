# Kimi Audit Reports: Actionable Items

Extracted from 4 Kimi Agent audit reports (March 2026).
Source files in this directory: `crypto_forex_prediction_platforms_audit_report.md`, `toronto_crypto_trading_research_report.md`, `trading_prediction_evaluation_framework.md`, `findtorontoevent_ca_investigation_report.md`.

---

## ALREADY IMPLEMENTED

These items are present in our dashboards (audit_dashboard, alpha_engine, KIMI_RISEOFTHECLAW).

### Metrics We Already Display
| Metric | Where | Audit Benchmark | Our Status |
|--------|-------|-----------------|------------|
| Win Rate | All dashboards | >50% | Displayed per strategy |
| Sharpe Ratio | Audit dashboard, Alpha Engine | >1.0 good, >2.0 outstanding | Displayed; color-coded (green >1.5, yellow >0, red <0) |
| Profit Factor | Audit dashboard, Alpha Engine | >1.5 viable, >2.0 strong | Displayed per strategy |
| Max Drawdown | Audit dashboard, Alpha Engine | <20% conservative, <30% aggressive | Displayed as "Recent Max DD%" (last 10 trades) |
| Expectancy | Audit dashboard | Positive | Displayed as avg PnL per trade |
| Entry/Exit/SL/TP | All signal outputs | Required for legitimate signals | Included in every pick |
| Backtest Sharpe | Audit dashboard | Per-strategy | Shown in strategy detail panel |

### Transparency Practices We Already Follow
- **Full trade history**: All dashboards show both winning and losing trades
- **Public data access**: `active_picks.json` is publicly accessible on GitHub raw
- **Disclaimer text**: Audit dashboard has "does not constitute financial advice" disclaimer
- **Strategy methodology disclosed**: Strategy descriptions + academic citations in Alpha Engine
- **Real-time signal delivery**: Signals via Discord + dashboards updated every 15-30 min
- **p-value / statistical significance**: Computed in `forward_validator.py`, `vectorized_backtest.py`, `walk_forward_validator.py`
- **Walk-forward analysis**: Implemented in `alpha_engine/walk_forward_validator.py`
- **Monte Carlo simulation**: Referenced in `alpha_engine/run_massive_mutations.py`
- **Position sizing (Kelly Criterion)**: Quarter-Kelly implemented in Alpha Engine

### Event Scraping Already in Place
- **Eventbrite scraper**: `tools/scrapers/eventbrite_scraper.py` (JSON-LD)
- **Meetup scraper**: `tools/scrapers/meetup_scraper.py` (exists)

---

## SHOULD ADD (High Priority Gaps)

### 1. Missing Dashboard Metrics

| Metric | Audit Benchmark | Gap Description | Where to Add |
|--------|-----------------|-----------------|--------------|
| **Sortino Ratio** | >1.0 | Not displayed on any dashboard. We calculate Sharpe but not Sortino (downside-deviation only). More relevant for crypto since upside vol is desirable. | Audit dashboard + Alpha Engine |
| **Calmar Ratio** (CAGR/MDD) | >1.0 | Not computed. Would help compare strategies that have been running for different durations. | Audit dashboard strategy cards |
| **Recovery Factor** | >2.0 min, >5.0 excellent | Not tracked. How quickly a strategy recovers from drawdown. | Audit dashboard |
| **CAGR** | Context-dependent | Not annualized. We show total PnL but not annualized return. | All dashboards |
| **Live MDD** (full history) | <20% | We only show "recent max DD" (last 10 trades). Should track true peak-to-trough MDD across full history. | All dashboards, needs DB schema change |

### 2. Scam/Red-Flag Warning System for Users

The audit identifies specific red flags we should warn about on our dashboards. **Action: Add a "Signal Health" panel to audit_dashboard.**

| Red Flag | Detection Method | Implementation |
|----------|-----------------|----------------|
| Win Rate >80% | Flag if any strategy shows >80% WR | Yellow warning badge: "Possible overfitting" |
| Sharpe >3.0 | Flag if Sharpe exceeds 3.0 | Warning: "Suspiciously high Sharpe - verify data" |
| No losing trades in recent history | Detect if last N trades are all winners | Warning: "No recent losses - review for survivorship bias" |
| Drawdown 0% or <5% | Flag unrealistically low DD | Warning: "Unrealistically low drawdown" |
| Consecutive wins >15 | Count max consecutive wins | Flag as "Statistical anomaly" |

### 3. Benchmark Comparison

The audit strongly recommends comparing against benchmarks. **Action: Add benchmark comparison to audit_dashboard.**

| Benchmark | Purpose |
|-----------|---------|
| BTC buy-and-hold | Crypto strategies must beat this to justify complexity |
| S&P 500 buy-and-hold | Cross-asset comparison |
| 60/40 portfolio | Risk-adjusted baseline |

### 4. KIMI Dashboard Missing Disclaimer

`KIMI_RISEOFTHECLAW/index.html` has **no disclaimer text**. The audit explicitly requires:
- "Past performance does not guarantee future results"
- "Not financial advice"
- Risk disclosure

**Action: Add disclaimer footer to KIMI dashboard matching the one in audit_dashboard.**

### 5. Metric Threshold Discrepancies

| Metric | Audit "Minimum" | Audit "Red Flag" | Our Current Threshold | Action |
|--------|-----------------|------------------|-----------------------|--------|
| Profit Factor | >1.5 viable | <1.0 losing | We display but don't color-code at 1.5 | Add color coding: red <1.0, yellow 1.0-1.5, green >1.5 |
| Max Drawdown | <20% conservative | >30% dangerous | We show recent DD but no severity coloring | Color: green <15%, yellow 15-25%, red >25% |
| Win Rate | 40-70% healthy | >75% suspicious | No upper-bound warning | Add orange/warning for WR >75% |
| Min trades for validity | 30 basic, 200 recommended | <30 unreliable | No minimum trade count filter | Add "Low sample size" warning if <30 closed trades |

### 6. Toronto Crypto Events to Scrape

The Toronto research report identifies events NOT in our current scraping pipeline:

| Event/Source | URL/Platform | Priority | Notes |
|---|---|---|---|
| **Blockchain Futurist Conference** | blockchainevents.ca | HIGH | Canada's largest Web3 event, 7000+ attendees, July 2026 |
| **Consensus Toronto** | coindesk.com/consensus | HIGH | Major CoinDesk conference at Metro Convention Centre |
| **ETHWomen Toronto** | Via Eventbrite | MEDIUM | Hackathon at Rebel Entertainment Complex |
| **Bitcoin Bay Meetups** | meetup.com/the-bitcoin-bay | HIGH | 6710+ members, weekly/bi-weekly, Canada's longest-running |
| **GTA Algorithmic Trading** | meetup.com (search) | MEDIUM | 1597 members, algo trading focus |
| **Canada Crypto Week** | canadacryptoweek.com | MEDIUM | Aggregate crypto week events |
| **BlockchainEvents.ca** | blockchainevents.ca | LOW | Aggregate calendar (could be a scrape source) |
| **CryptoEvents.global** | cryptoevents.global | LOW | Global crypto event listing |

**Action: Add crypto/trading keywords to Meetup scraper. Add blockchainevents.ca and canadacryptoweek.com as scrape targets in unified_scraper.py.**

### 7. Out-of-Sample Reporting on Dashboard

Walk-forward analysis exists in code but results are not surfaced on dashboards. **Action: Show in-sample vs out-of-sample performance split on audit_dashboard strategy detail panels.**

---

## NICE TO HAVE (Lower Priority)

### 1. Additional Statistical Displays
- **Confusion Matrix metrics** (Precision, Recall, F1) for direction prediction accuracy
- **Ulcer Index** (measures depth + duration of drawdowns, "investment stress")
- **CAR/MDD and RAR/MDD** ratios for advanced risk-adjusted views
- **Bootstrapped confidence intervals** for Sharpe and WR (show 5th-95th percentile)

### 2. Equity Curve Visualization
- Audit recommends "running balance and equity curves." We have PnL data but no visual equity curve chart on the main dashboards. Adding a chart.js equity curve per strategy would increase transparency.

### 3. Market Regime Tagging
- Audit recommends showing performance "during bull/bear/sideways markets." We have regime detection in `ml_battleground/system_b_regime/` but don't tag picks with the regime they were generated in. Cross-referencing would add credibility.

### 4. Legitimate Community References
- Add a "Toronto Trading Community" section to the events site linking to verified communities:
  - Bitcoin Bay (meetup.com/the-bitcoin-bay)
  - GTA Algorithmic Trading (Meetup)
  - Blockchain Futurist Conference
  - University of Toronto Crypto Conference

### 5. OSC Warning List Integration
- The Toronto report lists 9+ OSC-warned platforms (ESET Trading, Grin Dominance, etc.). Could add a "Known Scam Platforms" reference page or warning overlay if any ticker/platform mentioned in signals matches a known scam.

### 6. Third-Party Verification Link
- Audit strongly emphasizes MyFXBook/FXBlue-style independent verification. We could link to our public GitHub data (`active_picks.json`) as a form of transparent, tamper-evident record (git history = audit trail).

---

## NOT APPLICABLE

| Item | Why Not Applicable |
|------|-------------------|
| CTA/NFA registration | We are not a signal provider service; this is a personal research/portfolio system |
| Series 3 examination | Not operating as a CTA |
| MyFXBook/FXBlue verification | We don't trade forex through MT4/MT5; our signals are crypto-focused on Binance |
| Subscription fee model concerns | We don't charge for access |
| Withdrawal issue detection | We don't custody funds |
| KYC/AML compliance | Not operating as an exchange |
| CIPF protection | Not a broker |
| MLM/pyramid detection | Not applicable to our system structure |
| "Pay fee to unlock withdrawals" | No payment system |
| Fake celebrity endorsements | Not applicable |
| Romance scam / pig butchering detection | Not a social platform |
| CFTC Red List checking | US-specific; we are Canadian-based |
| Honeypot / token sniffer checks | We trade existing pairs, not new tokens |

---

## METRIC BENCHMARK COMPARISON TABLE

Summary of audit-recommended thresholds vs. what our systems currently use or display.

| Metric | Platforms Audit | Evaluation Framework | Our Current | Gap? |
|--------|----------------|---------------------|-------------|------|
| Sharpe Ratio | >1.0 good, >2.0 outstanding, >3.0 suspicious | >0.5 min, >1.0 good, >1.5 excellent | Displayed, colored at 1.5 | Minor: should add >3.0 warning |
| Profit Factor | >1.75 viable, >2.0 strong | >1.2 min, >1.5 good, >2.0 excellent | Displayed, no color thresholds | YES: add tiered coloring |
| Max Drawdown | <20% | <40% min, <25% good, <15% excellent | Recent DD only (10 trades) | YES: need full-history MDD |
| Win Rate | >50% | 40-70% healthy, >75% suspicious | Displayed, no upper warning | YES: add >75% warning |
| Sortino Ratio | >1.0 | Not mentioned | NOT displayed | YES: add to dashboards |
| Calmar Ratio | Not mentioned | >1.0 | NOT computed | YES: add |
| Recovery Factor | Not mentioned | >2.0 min, >3.0 good, >5.0 excellent | NOT computed | LOW: nice to have |
| Expectancy | Positive | >$0 min | Displayed | OK |
| Min Trades | 200+ recommended | 100+ for significance | No minimum shown | YES: add sample-size warnings |
| Live DD multiplier | "Live DD typically 1.5-2x backtest DD" | N/A | Not factored in | YES: show adjusted DD estimate |

---

## REGULATORY CONTEXT (Canadian-Specific)

From the Toronto research report, relevant to our system:

1. **OSC (Ontario Securities Commission)** is the primary regulator. Any platform providing trading advice in Ontario must comply.
2. **We are NOT a registered dealer or advisor** -- our dashboards are personal research tools. If we ever open access publicly with trading recommendations, we would need to review OSC requirements.
3. **CSA registration check**: https://www.securities-administrators.ca/ -- useful reference link to add to dashboards.
4. **Known scam platforms warned by OSC (Feb 2026)**: ESET Trading, Grin Dominance, High Peak Zenix, IntelApp2, Protraderai.org, Profitbah, Skycrest Valtrio, Arctic Valtrix AI, Crysten Hexalo AI.
5. **Registered Canadian exchanges** we could reference for price feeds: Bitbuy, Coinsquare, WonderFi, Wealthsimple Crypto, Newton, VirgoCX.

---

*Generated: March 15, 2026*
*Source: Kimi Agent audit reports in docs/kimi_audit/*
