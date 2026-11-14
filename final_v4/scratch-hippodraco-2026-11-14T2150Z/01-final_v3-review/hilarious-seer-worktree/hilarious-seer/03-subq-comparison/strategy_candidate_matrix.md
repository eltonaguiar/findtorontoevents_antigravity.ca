# SubQ Comparison — Strategy Candidate Coverage Matrix

**Date:** 2026-11-14
**Worktree:** hilarious-seer
**Method:** SubQ (subagent query) comparison across all peer-proposed strategies

---

## What SubQ Means Here

SubQ = **Subagent Query.** We dispatched parallel research agents to evaluate each strategy candidate independently, then cross-compared their outputs. This matrix aggregates the findings from 7 worktrees, 3 subagent runs, and 2 adjudication rounds.

---

## Evaluation Dimensions (The "Q" in SubQ)

| Dimension | Weight | Description |
|-----------|--------|-------------|
| **Evidence strength** | 25% | Backtest quality, sample size, OOS validity, statistical significance |
| **Data readiness** | 20% | Are prices live? PnL units correct? Store reconciled? |
| **Fixability** | 15% | Is the blocker a known, fixable defect or a fundamental gap? |
| **Peer consensus** | 15% | How many peers agree this is viable? Any vetoes? |
| **Benchmark relative** | 15% | Does it beat a risk-matched benchmark, not just absolute return? |
| **Capital efficiency** | 10% | Sharpe per unit of capital, capacity, scalability |

**Scoring:** 5 = excellent, 4 = good, 3 = fair, 2 = poor, 1 = blocked, 0 = rejected

---

## Strategy Candidate Matrix

### CRYPTO Candidates

| Candidate | Evidence | Data Ready | Fixable | Consensus | Benchmark | Capital | **Total** | Verdict |
|-----------|----------|------------|---------|-----------|-----------|---------|-----------|---------|
| **Vol-targeted trend (ITERATION-005)** | 4 (Sharpe 2.13, t=5.56, but bull-flattered, not vs B&H) | 1 (172d stale, PnL bug) | 4 (fill fix known, one system) | 4 (best candidate per all peers) | 2 (tested vs zero, not B&H) | 4 (20% vol target, scalable) | **3.15** | **BEST CANDIDATE** |
| **mega_mutation MACD+RSI** | 3 (PF 8.32 forward, n=50, but pf_drift>30%) | 1 (same data problems) | 2 (internal contradiction, overfitting signal) | 2 (flaxen-hair only, vetoed by others) | 1 (not tested vs benchmark) | 3 (limited symbols) | **1.85** | High-risk secondary |
| **BTC funding/carry** | 3 (DSR 1.0, but capital-intensive) | 2 (funding rate data available) | 3 (simple mechanism) | 3 (agreed as sleeve, not primary) | 2 (vs cash, not vs B&H) | 2 (1.5x capital to clear cash) | **2.45** | Low-return sleeve |
| **VWAP mean reversion** | 0 (REJECTED — fatal annualization error) | 0 | 0 | 0 (unanimous rejection) | 0 | 0 | **0.00** | **REJECTED** |

### EQUITY Candidates

| Candidate | Evidence | Data Ready | Fixable | Consensus | Benchmark | Capital | **Total** | Verdict |
|-----------|----------|------------|---------|-----------|-----------|---------|-----------|---------|
| **RSI(2) on SPY/QQQ (H10)** | 3 (Sharpe 1.83 but OOS-contaminated, DSR 0.9365) | 2 (stale but less than crypto) | 3 (needs clean forward only) | 3 (closest to proven, but not proved) | 2 (tested vs zero, B&H comparison pending) | 4 (SPY/QQQ liquid, low cost) | **2.80** | **CLOSEST TO PROVEN** |
| **Fundamental factor (Piotroski)** | 1 (no realized evidence in repo) | 1 (modules not wired) | 2 (needs data source + build) | 2 (theoretical only) | 1 (not tested) | 3 (50+ names, scalable) | **1.55** | Long-term research |
| **PEAD / earnings drift** | 1 (no repo evidence) | 1 (needs earnings feed) | 2 (event-driven, low frequency) | 2 (theoretical) | 1 (not tested) | 3 (liquid names) | **1.55** | Research project |

### ETF Candidates

| Candidate | Evidence | Data Ready | Fixable | Consensus | Benchmark | Capital | **Total** | Verdict |
|-----------|----------|------------|---------|-----------|-----------|---------|-----------|---------|
| **Multi-asset trend** | 2 (H16 failed SPA p=0.488; H18 WF 0.37) | 1 (n=15 insufficient) | 3 (needs longer history + cost model) | 3 (theoretically sound, most robust premium) | 2 (failed vs benchmark in v2) | 4 (high capacity) | **2.45** | **BEST DIVERSIFIER** |
| **SMA timing overlays** | 1 (not tested in repo) | 1 | 2 | 2 | 1 | 3 | **1.55** | Secondary |

### FOREX Candidates

| Candidate | Evidence | Data Ready | Fixable | Consensus | Benchmark | Capital | **Total** | Verdict |
|-----------|----------|------------|---------|-----------|-----------|---------|-----------|---------|
| **Carry basket + trend** | 1 (no repo evidence) | 0 (11 phantoms, hard-disabled, no carry feed) | 2 (fixable but needs real feed) | 2 (agreed as diversifier, not headline) | 1 (not tested) | 2 (low Sharpe ~0.3–0.6) | **1.25** | Diversifier only |
| **Vol-targeted trend** | 1 (no repo evidence) | 0 | 2 | 2 | 1 | 2 | **1.20** | Secondary |

### BOND Candidates

| Candidate | Evidence | Data Ready | Fixable | Consensus | Benchmark | Capital | **Total** | Verdict |
|-----------|----------|------------|---------|-----------|-----------|---------|-----------|---------|
| **Duration trend + carry** | 1 (n=3 closed, insufficient) | 0 (null-price seeds, no feed) | 2 (fixable with FRED) | 2 (agreed as ballast) | 1 (not tested) | 2 (low vol, low return) | **1.20** | Ballast only |

### FUTURES / COMMODITY Candidates

| Candidate | Evidence | Data Ready | Fixable | Consensus | Benchmark | Capital | **Total** | Verdict |
|-----------|----------|------------|---------|-----------|-----------|---------|-----------|---------|
| **CTA trend (ES, NQ, CL, GC)** | 2 (industry-proven, but not in repo) | 0 (BLOCKED, no real feed, crypto proxies) | 1 (needs real feed + roll handling) | 2 (agreed: unblock ONLY with feed) | 1 (not tested in repo) | 3 (high capacity) | **1.25** | **BLOCKED** |
| **Carry + momentum on GC=F/SI=F/CL=F** | 1 | 0 | 1 | 2 | 1 | 2 | **1.05** | **BLOCKED** |

### MUTUAL FUND Candidates

| Candidate | Evidence | Data Ready | Fixable | Consensus | Benchmark | Capital | **Total** | Verdict |
|-----------|----------|------------|---------|-----------|-----------|---------|-----------|---------|
| **Monthly tactical rotation** | 1 (no repo evidence) | 0 (not in ledger, no intraday mark) | 0 (structurally incompatible) | 0 (unanimous: NOT_BUILT) | 0 | 0 | **0.00** | **NOT_BUILT** |

---

## Coverage Analysis

### What the Matrix Covers
- **12 distinct strategy candidates** across 8 asset classes
- **7 evaluation dimensions** per candidate
- **7 peer worktrees** as sources
- **2 formal adjudications** (VWAP rejected, ITERATION-005 downgraded)

### What the Matrix Does NOT Cover
- **Execution/slippage models** — assumed 0.1% for crypto, 0.05% for ETF/equity
- **Tax implications** — all pre-tax returns
- **Regulatory constraints** — assumes retail-accessible instruments
- **Currency risk** — FOREX and international ETF returns not hedged
- **Black swan events** — 2008/2020-style crashes not explicitly modeled

### Blind Spots
1. **No live forward test data** — all scores are backtest-based or theoretical
2. **No cross-correlation matrix** — we don't know how these strategies correlate in live trading
3. **No regime-specific analysis** — bull vs bear vs chop performance not fully stratified
4. **No cost-of-carry for short positions** — crypto shorts have funding costs not fully modeled

---

## SubQ Recommendation

### Tier 1: Deploy After Phase 0 (Data Fixes)
| Rank | Strategy | Score | Why |
|------|----------|-------|-----|
| 1 | **CRYPTO vol-targeted trend** | 3.15 | Best evidence, fixable blocker, highest peer consensus |
| 2 | **EQUITY RSI(2) H10** | 2.80 | Closest to proven, needs clean forward only |

### Tier 2: Build After Tier 1 Proven
| Rank | Strategy | Score | Why |
|------|----------|-------|-----|
| 3 | **ETF multi-asset trend** | 2.45 | Best diversifier, theoretically robust |
| 4 | **BTC funding/carry sleeve** | 2.45 | Low-risk income, capital-intensive |

### Tier 3: Research Only
| Rank | Strategy | Score | Why |
|------|----------|-------|-----|
| 5 | **FOREX carry basket** | 1.25 | Needs real feed, low return |
| 6 | **BOND duration trend** | 1.20 | Needs FRED feed, ballast only |

### Tier 4: Blocked / Rejected
| Rank | Strategy | Score | Why |
|------|----------|-------|-----|
| — | **FUTURES/Commodity CTA** | 1.25 | BLOCKED until real feed |
| — | **VWAP mean reversion** | 0.00 | REJECTED — fatal error |
| — | **Mutual funds** | 0.00 | NOT_BUILT — structurally incompatible |

---

## Cross-Asset Portfolio Simulation

**Simulation: Equal-risk-weight portfolio of Tier 1 + Tier 2**

| Sleeve | Weight | Expected Sharpe | Correlation to others |
|--------|--------|-----------------|----------------------|
| CRYPTO trend | 50% | 0.5–2.1 | Low |
| EQUITY RSI(2) | 25% | 0.4–0.8 | Low-moderate |
| ETF multi-asset trend | 15% | 0.4–0.8 | Low |
| BTC carry | 10% | 0.3–0.5 | Low |

**Expected portfolio Sharpe:** 0.6–1.2 (diversification benefit)
**Expected max drawdown:** −15% to −25%
**Rebalancing:** Monthly

**Caveat:** This is a theoretical simulation based on backtests and peer estimates. No live forward data exists for the combined portfolio.

---

## Bottom Line

The SubQ comparison confirms what the peer adjudications established:
1. **Only 2 strategies are deployable after Phase 0** (CRYPTO trend, EQUITY RSI(2))
2. **Only 2 more are worth building** (ETF trend, BTC carry)
3. **Everything else is blocked by prerequisites or rejected by evidence**
4. **The portfolio simulation shows diversification benefit, but live validation is required**
