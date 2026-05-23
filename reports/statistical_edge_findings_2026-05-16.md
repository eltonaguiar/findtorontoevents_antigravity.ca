# Statistical Edge Discovery & Strategy Optimization - Consolidated Findings

**Generated:** 2026-05-16  
**Sources:** DAILY_IDEAS_PROMPTS.MD, ALL_STRATEGIES.md, DAILY_IDEAS.MD, AGENT_PROMPT_LIBRARY.md, user requirements

---

## Executive Summary

Analysis of the provided input files reveals a comprehensive prompt library for systematic trading strategy improvement, targeting world-class statistical edge per asset class. The system comprises **700+ strategies** across multiple engines (Alpha Engine, Baby Strategies, KIMI Rise of the Claw, Coinglass DNA, ML systems) deployed via GitHub Actions to MySQL databases (`ejaguiar1_stocks`, `ejaguiar1_backtests`).

### Current System Architecture

| Component | Count | Status |
|-----------|-------|--------|
| Total Strategies | 700+ | Active |
| Asset Classes | 7 | Crypto, Forex, Equity, ETF, Futures, Commodities, Bonds |
| Strategy Engines | 15+ | Alpha, Baby, KIMI, ML, Coinglass |
| MySQL Databases | 2 | ejaguiar1_stocks, ejaguiar1_backtests |
| Repository Files | 5,758 | Python files, 29 Pine scripts |

---

## Part 1: Per Asset Class Performance & Issues

### Current Performance Metrics

| Asset Class | Profit Factor | Win Rate | Sample Size | Status |
|-------------|---------------|----------|-------------|--------|
| CRYPTO | Variable | Variable | n/a | ML confidence INVERTS - high confidence = high losses |
| EQUITY | 1.55 | Variable | n/a | Scale what works - needs systematic amplification with regime filters |
| FOREX | 0.86 | 46.4% | n=1,169 | Class blocked (hedge_fund_sprint) - needs full mutation protocol |
| COMMODITIES | Variable | <50% | n/a | COT artifact contamination - needs cleanup |
| ETF | 1.33 | Variable | n/a | Needs sector rotation + macro overlay |
| BONDS | 1.72 | 55.6% | n=18 | Meets PF+WR but n sub-floor (charter 100) |
| FUTURES | n/a | 5.9% | n/a | Silent-dead, no production scanner |

### Critical Issues Identified

1. **CRYPTO**: ML confidence calibration broken - conf ≥ 0.90 → 14.4% WR
2. **FOREX**: PF 0.86 is critically underperforming
3. **FUTURES**: Only 5.9% WR - essentially random
4. **COMMODITIES**: WR < 50% despite PF > 1.5
5. **BONDS**: Too few samples (n=18) to be statistically significant

---

## Part 2: Prompt Suite Categories (20 Production-Ready Prompts)

### SECTION 1: MySQL Edge Extraction (Priority: CRITICAL)

| Prompt | What It Does | Output |
|--------|-------------|--------|
| **1A** `Database Edge Scanner` | Connects to `ejaguiar1_stocks` + `ejaguiar1_backtests`, calculates PF/WR/Sharpe/MDD per asset class with 95% confidence intervals, rolling decay analysis, inversion candidates | `edge_report_mysql.md` + `edge_per_class.json` |
| **1B** `Deep Strategy Autopsy` | Per-strategy forensic analysis: streak analysis, fat tails, concentration risk, day-of-week effects, serial correlation | `strategy_autopsy.json` |

### SECTION 2: Per-Asset-Class Fixes (Priority: HIGH)

| Class | Prompt | Problem It Solves |
|-------|--------|-------------------|
| **CRYPTO** | 2A Confidence Recalibration | ML inverted: conf≥0.90 → 14.4% WR. Implements isotonic regression + direction flip layer |
| **EQUITY** | 2B Scale What Works | PF 1.55 → systematic amplification with regime filters + conviction stack |
| **FOREX** | 2C Mutation Protocol | PF 0.86 → full mutation (invert, session filter, COT overlay, A/B test) |
| **COMMODITY** | 2D Clean COT Artifact | Remove CT=F dedup contamination, add seasonality + clean COT |
| **ETF** | 2E Sector Rotation | PF 1.33 → 1.5 (T2) via relative strength rotation + macro overlay |
| **BOND** | 2F Accumulator | Paper-only until n=100, yield curve + credit spread signals |

### SECTION 3: System-Wide Engines (Priority: HIGH)

| Prompt | Concept | What It Does |
|--------|---------|-------------|
| **3A** DNA Mutation Engine | Genetic algorithm for strategies | Evolves strategies via point mutation, crossover, regime switching. Weekly evolution loop with fitness scoring |
| **3B** Strategy Inversion Layer | "Invert the losers" | Auto-detects strategies with 35-45% WR, creates inverted variants, A/B tests them |
| **3C** Swarm Research Agents | Multi-agent per-asset research | 5 parallel research agents (Crypto/Equity/Forex/Commodity/Bond-ETF) with technical, fundamental, sentiment, and COT tools |
| **3D** The Necromancer | Save failing strategies | Diagnoses WHY strategies fail, applies treatment (regime filter, parameter re-opt, symbol removal), resurrects via paper trading |
| **3E** Multi-Timeframe Confluence | Require 3 timeframe agreement | 1h/1d/1w must align for signal = fewer but higher-quality trades |
| **3F** Adaptive Risk Manager | Kelly + CPPI hybrid | Dynamic position sizing: Kelly * drawdown_factor * correlation_factor, hard CPPI floor |

### SECTION 4: CI/CD Integration (Priority: MEDIUM)

| Prompt | What It Does |
|--------|-------------|
| **4A** Efficient GitHub Actions | Adds swarm research to existing workflows (parallel matrix, shared cache, ~2 min overhead) |
| **4B** Automated Edge Alerts | Every 6 hours: Critical/Warning/Info alerts + auto-pause on degradation |

### SECTION 5: 10-Week Roadmap

Complete phased plan: Foundation → Amplify Winners → Fix Losers → Evolve → Swarm → Optimize

---

## Part 3: Top 5 Prompts to Run Immediately

| Rank | Prompt | Why First |
|------|--------|-----------|
| 1 | **1A (MySQL Edge Scanner)** | You need ground truth before any improvements |
| 2 | **2A (CRYPTO Calibration)** | Your biggest leak: high confidence = high losses |
| 3 | **3B (Inversion Layer)** | Free alpha: strategies with 35-45% WR become 55-65% when flipped |
| 4 | **2B (EQUITY Scale)** | Only proven T2 edge — scale systematically |
| 5 | **3A (DNA Mutation)** | Long-term: automated strategy evolution |

---

## Part 4: Missing/Insufficient Coverage

| Gap | Impact | Recommendation |
|-----|--------|----------------|
| No dry_run in pick generators | Blocks Layer 2 verification | Add dry_run kwargs to smart_picks_engine, production_scanner, dashboard_generator |
| No drift-pause activation | Silent strategy decay | Implement probation JSON + is_on_probation() |
| Cross-engine consensus not automated | Duplicate research | Build no_edge_knowledge_base.py |
| Hallucination-guard not implemented | Citation quality issues | Add HEAD-check verify_citations.py |

---

## Part 5: Alternative Data Opportunities

| Data Source | Asset Class | Feasibility | Priority |
|-------------|-------------|-------------|----------|
| Polymarket prediction markets | Macro | High | P1 |
| Options flow / put-call ratios | Equity | High | P1 |
| SEC EDGAR 8-K filings | Equity | Medium | P2 |
| Weather / NOAA | Commodities | High | P1 |
| Chinese HSI/SSE markets | Equity | Medium | P2 |
| Mutual fund no-load filters | Equity | High | P1 |
| COT Commercial extremes | Futures | Already wired | Maintain |
| On-chain whale flows | Crypto | Already wired | Maintain |

---

## Part 6: Safety Gates & Blocked Symbols

### Current Blocks in Place
- BLOCKED_DIRECTION_TRIPLES for ML models
- Direction filtering for various strategy types
- FOREX class blocked (hedge_fund_sprint)

### Proposed Unblock Criteria
A symbol should be considered for unblocking when ALL of:
1. **PnL Recovery**: > 20% improvement over trailing 90 days
2. **Win Rate Improvement**: > 10 percentage points improvement
3. **Regime Stability**: No active regime change detected (VIX < 25, no policy shift)
4. **Confidence Calibration**: Score stabilizes within 0.1 of realized WR

### Symbol Rehabilitation Protocol
1. Flag as "rehab_candidate" in database
2. Run 30-day paper trading with reduced position size (0.5x)
3. If WR > 45% and PF > 1.0, increase to 0.75x
4. If WR > 50% and PF > 1.2, restore full position size

---

## Part 7: Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
- [ ] Deploy MySQL Edge Scanner (1A) - ground truth extraction
- [ ] Implement Deep Strategy Autopsy (1B)
- [ ] Add dry_run to pick generators (3 PRs)

### Phase 2: Amplify Winners (Week 3-4)
- [ ] Scale EQUITY strategies (2B) - PF 1.55 → systematic
- [ ] Deploy ETF sector rotation (2E)
- [ ] Multi-timeframe confluence engine (3E)

### Phase 3: Fix Losers (Week 5-6)
- [ ] CRYPTO confidence recalibration (2A)
- [ ] FOREX mutation protocol (2C)
- [ ] COMMODITIES COT cleanup (2D)
- [ ] Strategy inversion layer (3B)

### Phase 4: Evolve (Week 7-8)
- [ ] DNA Mutation Engine (3A)
- [ ] The Necromancer - failing strategy rescue (3D)
- [ ] Drift-pause activation

### Phase 5: Swarm & Optimize (Week 9-10)
- [ ] Swarm research agents per class (3C)
- [ ] CI/CD integration (4A, 4B)
- [ ] Full edge monitoring dashboard

---

## Part 8: Key SQL Queries for Edge Detection

### Query 1: Edge Score per Asset Class
```sql
-- Step 1: Compute per-ticker daily returns
WITH ticker_stats AS (
  SELECT 
    ticker,
    asset_class,
    AVG(close - LAG(close) OVER w) - 1 AS daily_return,
    STDDEV_POP(close - LAG(close) OVER w) AS volatility,
    AVG(close - LAG(close) OVER w) / STDDEV_POP(close - LAG(close) OVER w) AS sharpe
  FROM ejaguiar1_stocks
  WINDOW w AS (PARTITION BY ticker ORDER BY trade_date)
  GROUP BY ticker, asset_class
),
-- Step 2: Aggregate by strategy + asset class
strategy_stats AS (
  SELECT 
    s.asset_class,
    s.strategy_id,
    AVG(b.sharpe) AS mean_sharpe,
    MEDIAN(b.sharpe) AS median_sharpe,
    AVG(b.win_rate) AS mean_win_rate,
    AVG(b.max_dd) AS mean_max_dd,
    AVG(b.pnl) AS mean_pnl,
    COUNT(*) AS trade_count
  FROM ejaguiar1_backtests b
  JOIN ticker_stats s ON b.ticker = s.ticker
  GROUP BY s.asset_class, s.strategy_id
)
-- Step 3: Calculate edge score with 95% CI
SELECT 
  asset_class,
  strategy_id,
  mean_sharpe,
  mean_win_rate,
  mean_max_dd,
  (mean_sharpe * mean_win_rate) / NULLIF(mean_max_dd, 0) AS edge_score,
  mean_sharpe - (STDDEV_POP(mean_sharpe) / SQRT(COUNT(*)) * 1.96) AS ci_low,
  mean_sharpe + (STDDEV_POP(mean_sharpe) / SQRT(COUNT(*)) * 1.96) AS ci_high
FROM strategy_stats
WHERE trade_count >= 20
ORDER BY edge_score DESC;
```

### Query 2: Find Inversion Candidates (35-45% WR)
```sql
SELECT 
  strategy_id,
  asset_class,
  mean_pnl,
  mean_win_rate,
  COUNT(*) AS trade_count
FROM ejaguiar1_backtests
WHERE entry_date >= CURDATE() - INTERVAL 365 DAY
GROUP BY strategy_id, asset_class
HAVING mean_win_rate BETWEEN 0.35 AND 0.45
  AND mean_pnl < 0
ORDER BY mean_win_rate ASC;
```

---

## Part 9: Immediate Action Items

### Priority 1 (Run Today)
1. **Run Database Edge Scanner** - Get current PF/WR/Sharpe per asset class
2. **Fix CRYPTO** - Implement confidence recalibration (isotonic regression + direction flip)
3. **Invert LOSERS** - Create inverted variants of 35-45% WR strategies

### Priority 2 (This Week)
4. **Scale EQUITY** - Systematic amplification with regime filters
5. **Deploy DNA Mutation** - Weekly evolution loop

### Priority 3 (This Month)
6. **FOREX Mutation** - Full protocol (invert, session filter, COT overlay)
7. **COMMODITIES COT Cleanup** - Remove CT=F contamination

---

## References

- **Source:** DAILY_IDEAS_PROMPTS.MD (1,027 lines) - Complete prompt library
- **Source:** ALL_STRATEGIES.md (1,100+ lines) - Strategy inventory
- **Source:** DAILY_IDEAS.MD (1,557 lines) - Daily research logs
- **Source:** AGENT_PROMPT_LIBRARY.md - Kimi Code swarm output
- **Database:** mysql.50webs.com - ejaguiar1_stocks, ejaguiar1_backtests
- **Deployment:** GitHub Actions → findtorontoevents.ca/audit

---

## Appendix: Strategy Mutation Protocol

### Three-Axis Mutation

1. **Inversion**: Flip buy/sell signals (35-45% WR → 55-65% WR)
2. **Parameter Perturbation**: ±5-15% on numeric thresholds
3. **Regime Switching**: Add volatility regime filter (VIX > N = no entry)

### DNA Mutation Engine Algorithm
```
For each top-5 strategy by edge_score:
  1. Clone strategy rules (JSON)
  2. Apply inversion (flip all >/<, buy/sell)
  3. Random perturbation (5% Gaussian noise on numeric values)
  4. Add regime gate if missing
  5. Generate 3 variants per parent
  6. Backtest on rolling 6-month window
  7. If PF > 1.2 and WR > 50%, add to production
```

---

*Document generated from analysis of multi-source prompt libraries. See individual source files for complete context.*
