# Skill: thingstocheck-June2026

## Description
Comprehensive audit checklist for findtorontoevents.ca/audit system. Use when reviewing the trading prediction system's health, performance, and edge discovery.

## Triggers
- "check the audit pages"
- "review findtorontoevents.ca/audit"
- "why are we losing money"
- "find the edge"
- "audit the system"
- "check picks performance"
- "review tournament"
- "check portfolios"

## Checklist

### 1. Main Dashboard (`/audit/`)
- [ ] Overall win rate (target: >50%)
- [ ] Per-class performance (CRYPTO, EQUITY, COMMODITY, FOREX, etc.)
- [ ] ML calibration (high confidence should = high win rate)
- [ ] Score-band tiles (check for survivorship artifacts)
- [ ] Smart Picks vs raw DB reality (check for EXPIRED→WON mislabeling)

### 2. Picks Now (`picks-now.html`)
- [ ] Forward-tested win rate (target: >50%)
- [ ] Risk/reward ratio (SL vs TP)
- [ ] Active picks performance
- [ ] Recently closed picks (winning/losing?)
- [ ] AI Tournament section (which models are winning?)

### 3. Pick Funnel (`pick_funnel.html`)
- [ ] Pipeline accuracy (Scanned → Smart → VA → HC → Opened → Closed)
- [ ] Swarm verdict (which classes have real edge?)
- [ ] Navigation-surface edge matrix

### 4. AI Leaderboard (`ai_leaderboard.html`)
- [ ] Which models have n≥30 trustworthy picks?
- [ ] Synthetic data contamination
- [ ] Monte-Carlo test results

### 5. AI Tournament (`ai-tournament.html`)
- [ ] Why everything is "NOT MONEY-ready"
- [ ] Pick exclusion rate (target: <30%)
- [ ] Mispriced entries (target: <10%)
- [ ] Model Portfolio performance

### 6. Portfolio History (`portfolio_history.html`)
- [ ] Is it stale? When last updated?
- [ ] Portfolio performance by class
- [ ] Sharpe ratios (target: >1.0)
- [ ] Leverage usage

### 7. Research Index (`research_index.html`)
- [ ] How many GO verdicts? (target: >0)
- [ ] Does research feed into pick generation?
- [ ] Which classes have research-backed edge?

### 8. Database Audit
- [ ] Active picks performance
- [ ] Recently closed picks (last 30 days)
- [ ] Strategy performance (which strategies are profitable?)
- [ ] AI model performance (which models produce winning picks?)
- [ ] Data quality issues (duplicates, missing data, zero PnL)

### 9. Key Metrics to Track
- [ ] Overall win rate (target: >55%)
- [ ] Sharpe ratio (target: >1.0)
- [ ] Maximum drawdown (target: <20%)
- [ ] Strategy concentration (HHI target: <0.30)
- [ ] Kill rate (% of strategies killed this month)

## Common Issues

### Scoring System Inverted
- High confidence = low win rate
- Low-score picks outperform high-score picks
- **Fix:** Investigate why the scoring system is anti-predictive

### TIME_EXIT Dominance
- 70% of picks expire at TIME_EXIT_MAX_HOLD
- System rarely hits take-profit
- **Fix:** Tighten TP levels or use trailing stops

### Synthetic Data Contamination
- 1,636 synthetic tournament picks
- cursor_agent is 100% synthetic
- **Fix:** Filter out synthetic picks from rankings

### Data Staleness
- Portfolio risk metrics stale since March 2026
- Walk-forward suite 2 months stale
- **Fix:** Update data pipelines

## References
- `PLAN_INSIGHTS_KILO_June122026_1236pm.MD` — Full audit findings
- `KILO_DEEP_DIVE_FINDINGS_2026-06-12.MD` — Root causes and action items
- `docs/QUANT_FUND_TURNAROUND_PLAYBOOK.md` — Turnaround playbook
