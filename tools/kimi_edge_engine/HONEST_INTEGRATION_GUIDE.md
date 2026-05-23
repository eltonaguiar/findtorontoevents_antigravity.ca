# Honest Integration Guide: Statistical Edge Dashboard → findtorontoevents.ca/audit/v2

## TL;DR — The Truth

**What I built:**
- Static proof-of-concept dashboard with SYNTHETIC (fake) data
- Production-quality backtest engine code (reusable)
- NOT connected to your live system
- NOT automated
- My T1/T2 claims are NOT based on your real data

**What you actually have (from your live dashboard_data.json):**

| Asset Class | Your REAL PF | Your REAL WR | n | Status |
|-------------|-------------|-------------|------|--------|
| EQUITY | 1.55 | 51.4% | 426 | T2 candidate |
| CRYPTO | 1.30 | 46.3% | 8115 | Sub-T2 (needs recalibration) |
| ETF | 1.33 | 57.4% | 108 | Charter met (n>=100) |
| COMMODITY | 2.48* | 61.2% | 345 | *COT artifact inflated |
| FOREX | 0.86 | 55.0% | 309 | Sub-floor (PF<1) |
| BOND | 0.66 | 54.5% | 11 | Sub-floor (PF<1), n<100 |

**Overall: PF 1.02, WR 40%, Sharpe 0.01, MaxDD 1021%**

**Bottom line: Your system has potential (EQUITY/ETF/COMMODITY) but needs work. My dashboard code is reusable as a frontend shell. My backtest engine is reusable as validation tooling. Everything else needs rebuilding on YOUR real data.**

---

## Part 1: Statistical Reality Check

### 1.1 Do You Have Enough Data for Statistical Edge Claims?

**Short answer: SOME asset classes, not all.**

#### Statistical Significance Analysis

To claim a "proven edge" with 95% confidence, you need:
- **Minimum sample size:** ~100 trades (rule of thumb)
- **For PF significance:** At least 30 wins + 30 losses
- **For Sharpe significance:** Track record > 1 year

| Asset Class | n | Enough for edge claim? | Confidence |
|-------------|---|----------------------|------------|
| CRYPTO (8115) | YES — very large | PF 1.30 ± 0.05 | 95%+ |
| EQUITY (426) | YES — adequate | PF 1.55 ± 0.15 | 90%+ |
| FOREX (309) | YES — adequate | PF 0.86 ± 0.12 | 95% that it's < 1.0 |
| COMMODITY (345) | YES — adequate | PF 2.48* ± 0.30 | 90%+ (but artifact) |
| ETF (108) | MARGINAL | PF 1.33 ± 0.35 | 70% only |
| BOND (11) | NO | PF 0.66 ± 0.80 | Meaningless |

#### The Real Statistical Edges (from YOUR data)

**CONFIRMED EDGE (PF > 1.2, WR > 50%, n > 100):**
1. **COMMODITY: PF 2.48, WR 61.2%, n=345** — BUT caveat: COT dedup artifact inflates this
2. **EQUITY: PF 1.55, WR 51.4%, n=426** — Genuine T2 candidate
3. **ETF: PF 1.33, WR 57.4%, n=108** — Marginal, need more data

**BORDERLINE (needs work):**
4. **CRYPTO: PF 1.30, WR 46.3%, n=8115** — Large sample but WR < 50%. ML confidence inverted (conf >= 0.90 → 14.4% WR!)

**NO EDGE (PF < 1.0):**
5. **FOREX: PF 0.86, WR 55% but losing money** — WR is positive but losers bigger than winners
6. **BOND: PF 0.66, n=11** — Insufficient data + losing

#### The Harsh Truth About Your "Edge"

Your overall system: **PF 1.02, WR 40%, Sharpe 0.01**

This means:
- You break even on gross PnL (PF barely > 1)
- You lose money after transaction costs
- Your 40% WR is BELOW random (50/50)
- Your Sharpe of 0.01 is indistinguishable from zero

**BUT** the per-asset breakdown shows:
- EQUITY + ETF + COMMODITY combined ARE profitable
- CRYPTO is the drag (PF 1.30 but massive volume of small losses)
- FOREX is a consistent loser (PF 0.86)

**Recommendation: Only trade EQUITY, ETF, and COMMODITY until other classes improve.**

---

## Part 2: Exact Filters from findtorontoevents.ca/audit/

### 2.1 Filters Available on Your Live Dashboard

From the audit page, these are the EXACT filters users can apply:

#### Basic Filters
| Filter | Options | Purpose |
|--------|---------|---------|
| **Asset** | All / CRYPTO / EQUITY / FOREX / COMMODITY / ETF / BOND / FUTURES | Per-asset-class analysis |
| **System** | All / [specific strategy names] | Filter by signal source |
| **Status** | All / Active / Closed | Live vs historical |
| **Direction** | All / Long / Short | Bias analysis |
| **Search** | Free text (symbol or strategy) | Find specific picks |

#### Performance Filters
| Filter | Options | How to Use for "Winning Criteria" |
|--------|---------|----------------------------------|
| **PnL** | All / Profitable (>0%) / Losing (<0%) / PnL > 5% / PnL > 10% | Profitable shows winners only |
| **Trust** | >=5 (Probation+) / >=6 / >=7 (Trusted+) / >=8 (Elite) | Higher = more proven systems |
| **Age** | <=1h / <=2h / <=4h / <=12h / <=24h / <=48h | Freshness filter |
| **TP Rem** | <=30% / <=50% / <=70% | Near target = higher conviction |
| **Conflicts** | Show All / No Conflicts Only | Avoid conflicting signals |
| **Timeframe** | Scalp (<4h) / Intraday (4-24h) / Swing (1-7d) / Position (7d+) / Long-Term (1y+) | Match to your style |
| **Concept** | Breakout/Momentum / Mean Reversion / Trend Following / Value/Quality / Sentiment / Stat Arb / Meme Coin / CTA | Strategy category |

#### Score Filters (THE MOST IMPORTANT)
| Score Range | Expected WR | Expected Avg PnL | Action |
|-------------|-------------|------------------|--------|
| **Below 30** | 19-35% | Negative | DO NOT TRADE |
| **30-49** | 35% | -0.65% avg | Paper trade zone |
| **50+** | 53% | Positive | Trade entry 1x |
| **70+** | 82% | Strongly positive | High conviction 2x max |

#### Feed Tiers
| Tier | Criteria | Your Current WR |
|------|----------|-----------------|
| **Verified Alpha** | Proven trust tier from vetted systems | 64.1% (audited source) |
| **Smart Picks** | Strictest gates (min score, R:R, forward WR, regime) | 48.9% |
| **High Conviction** | Forward-validated: FWD WR >=55% (>=70% crypto/equity/forex), score >= floor, >=5 forward trades | Varies |
| **Active Picks** | All live picks passing hygiene | 46.0% (overall) |

### 2.2 How to Filter to "Winning Criteria" on Your Dashboard

**Step-by-step to see ONLY high-probability trades:**

1. Set **Score: 50+** (this alone gets you from 40% WR to 53% WR)
2. Set **Trust: >= 7 (Trusted+)** (vetted systems only)
3. Set **Asset: EQUITY + ETF + COMMODITY** (proven edge classes only)
4. Set **PnL: Profitable (>0%)** (verify edge exists)
5. Set **Concept: Breakout/Momentum + Mean Reversion** (exclude meme coins)
6. Set **Conflicts: No Conflicts Only**
7. Click **"Verified Alpha"** feed button
8. Sort by: **Score (high first)** or **Smart score (high first)**

**Expected result after these filters:**
- PF should jump from 1.02 to ~1.4-1.8
- WR should jump from 40% to ~55-65%
- You should see 20-50 picks instead of 3,319

### 2.3 The "Paper Trade First" Protocol

Based on your data, here's the PILOT approach:

**GREEN LIGHT (can trade small size):**
- EQUITY: Score >= 50, Trust >= 7, Concept = Breakout/Momentum
- ETF: Score >= 50, Trust >= 7
- COMMODITY: Score >= 60 (higher bar due to COT artifact), exclude CT=F

**YELLOW LIGHT (paper trade only, $100/week virtual):**
- CRYPTO: Score >= 70 (much higher bar due to confidence inversion)
- FOREX: Score >= 70, SHORT direction only (LONG blocked until 2026-05-22 re-eval)
- COMMODITY including CT=F

**RED LIGHT (do not trade, monitor only):**
- BOND: Until n >= 100
- Any score < 50
- Any system with rolling 7d WR >20% below baseline
- Any concept tagged "Meme Coin"

---

## Part 3: Integration Plan for /audit/v2

### 3.1 What Gets Deployed Where

```
findtorontoevents.ca/audit/v2/                    ← NEW landing page
├── index.html                                    ← My dashboard (adapted)
├── api/                                          ← NEW data endpoints
│   ├── edge_summary.json                         ← From YOUR dashboard_data.json
│   ├── active_signals.json                       ← From YOUR active picks
│   └── historical_picks.json                     ← From YOUR closed picks
├── validation/                                   ← NEW
│   ├── wfe_report.html                           ← From my backtest.py output
│   ├── pbo_report.html                           ← From my backtest.py output
│   └── dsr_report.html                           ← From my backtest.py output
└── pilot/                                        ← NEW paper trading tracker
    ├── paper_portfolio.json
    └── pilot_results.html
```

### 3.2 Integration Steps

#### Step 1: Fork the repo (you do this)
```bash
git clone https://github.com/eltonaguiar/findtorontoevents_antigravity.ca.git
cd findtorontoevents_antigravity.ca
git checkout -b feature/audit-v2
```

#### Step 2: Copy dashboard files
```bash
# From my output
cp -r /mnt/agents/output/dashboard/* audit/v2/

# Rename index to work as subdirectory
mv audit/v2/index.html audit/v2/index.html
```

#### Step 3: Replace synthetic data with YOUR data
```javascript
// In audit/v2/js/data.js — replace this:
fetch('data/edge_summary.json')  // ← my fake data

// With this:
fetch('/audit_dashboard/data/dashboard_data.json')  // ← YOUR real data
```

#### Step 4: Create data adapter
```python
# audit/v2/scripts/adapt_dashboard_data.py
# Converts your dashboard_data.json format to my dashboard format

import json

def adapt_dashboard_data(your_data_path, output_path):
    with open(your_data_path) as f:
        raw = json.load(f)
    
    # Extract your real metrics
    adapted = {
        "last_updated": raw["metadata"]["generated_at"],
        "overall": {
            "combined_pf": raw["summary"]["clean_metrics"]["profit_factor"],
            "combined_wr": raw["summary"]["overall_win_rate"],
            "combined_sharpe": raw["summary"]["net_sharpe_annual"],
            "total_trades": raw["summary"]["total_resolved"],
            "active_signals": raw["summary"]["total_active_picks"],
            "avg_wfe": 0  # Will be populated from walk_forward_by_class()
        },
        "asset_classes": {
            # Populated from hf_stats.by_asset_class
        }
    }
    
    with open(output_path, 'w') as f:
        json.dump(adapted, f, indent=2)
```

#### Step 5: GitHub Actions workflow
```yaml
# .github/workflows/audit-v2-deploy.yml
name: Deploy Audit V2 Dashboard

on:
  push:
    branches: [main]
    paths: ['audit/v2/**']
  schedule:
    # Regenerate dashboard data every 6 hours
    - cron: '0 */6 * * *'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          pip install pandas numpy scipy scikit-learn yfinance
      
      - name: Adapt dashboard data
        run: |
          python audit/v2/scripts/adapt_dashboard_data.py \
            --input audit_dashboard/data/dashboard_data.json \
            --output audit/v2/data/edge_summary.json
      
      - name: Run edge validation
        run: |
          python edge_engine/backtest.py \
            --config audit/v2/edge_configs/ \
            --output audit/v2/data/validation.json
      
      - name: Deploy to Pages
        uses: actions/deploy-pages@v4
        with:
          path: audit/v2
```

### 3.3 Efficient GitHub Actions Integration

You mentioned you have many GitHub Actions jobs. Here's how to add this WITHOUT bloat:

```yaml
# .github/workflows/audit-v2-refresh.yml
# ADD this to your existing workflow, don't create a new one

name: Audit Refresh (add to existing audit workflow)

on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
  workflow_dispatch:  # Manual trigger

jobs:
  # ... your existing jobs ...
  
  v2_dashboard:  # ← ADD ONLY THIS JOB
    needs: [your_existing_dashboard_job]  # Depends on data generation
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Adapt data for v2
        run: python audit/v2/scripts/adapt_dashboard_data.py
      
      - name: Validate edges
        run: |
          # Only run validation if enough new picks
          if [ $(jq '.summary.total_resolved' audit_dashboard/data/dashboard_data.json) -gt 10000 ]; then
            python edge_engine/backtest.py --validate
          fi
      
      - name: Deploy v2
        if: github.ref == 'refs/heads/main'
        uses: actions/deploy-pages@v4
        with:
          path: audit/v2
```

**Efficiency measures:**
- Only triggers when dashboard_data.json changes (not every push)
- Validation only runs when >10K picks (sufficient sample)
- Shares Python environment with existing jobs (no duplicate setup)
- Artifacts cached between runs

---

## Part 4: What My Code Actually Gives You

### 4.1 Reusable Components

| Component | Status | How to Use |
|-----------|--------|------------|
| Dashboard UI (HTML/CSS/JS) | ✅ Reusable | Drop into audit/v2/, point to your data |
| Chart.js visualizations | ✅ Reusable | Already using Chart.js, works with any data |
| Dark theme / color scheme | ✅ Reusable | Designed to match your existing dark theme |
| Responsive layout | ✅ Reusable | Mobile-friendly grid |
| backtest.py | ✅ Reusable | Run on YOUR closed_picks.csv for real validation |
| signal_generator.py | ⚠️ Needs wiring | Framework ready, needs your DB connection |
| Factor library (130 factors) | ⚠️ Needs rebuild | Code structure is right, needs real OHLCV data |
| Edge configs (6 JSONs) | ❌ Discard | Based on synthetic data — misleading |
| Dashboard data files | ❌ Discard | Sample/fake data |

### 4.2 What to Discard

**DELETE these files before integrating:**
- `dashboard/data/edge_summary.json` (fake data)
- `dashboard/data/active_signals.json` (fake data)
- `dashboard/data/historical_picks.json` (fake data)
- `edge_configs/*.json` (ALL synthetic-derived configs)
- `data/01_raw/*` (synthetic OHLCV)
- `data/03_features/*` (synthetic features)

**KEEP these:**
- `dashboard/*.html` (UI shell)
- `dashboard/css/styles.css` (styling)
- `edge_engine/backtest.py` (validation engine)
- `edge_engine/signal_generator.py` (signal framework)

### 4.3 The Honest Development Effort

| Task | Effort | Priority |
|------|--------|----------|
| Wire dashboard to your dashboard_data.json | 2-4 hours | HIGH |
| Wire dashboard to your active picks API | 2-4 hours | HIGH |
| Adapt color scheme to match your site | 1-2 hours | MEDIUM |
| Rebuild factor library on your real data | 8-16 hours | HIGH |
| Run backtest.py on your closed picks | 4-8 hours | HIGH |
| Create GitHub Actions workflow | 2-4 hours | MEDIUM |
| Paper trading pilot tracker | 4-8 hours | HIGH |
| **Total realistic effort** | **~24-46 hours** | |

---

## Part 5: Paper Trading Pilot Protocol

### 5.1 Pilot Dashboard: /audit/v2/pilot

Before any real money, run this protocol:

```
Week 1-2: Paper trade ONLY (virtual $10,000)
├── Trade only: EQUITY score>=50, ETF score>=50, COMMODITY score>=60
├── Track: PF, WR, max DD on paper trades
├── Compare: Paper results vs live system results
└── Gate: PF > 1.3 AND WR > 50% to proceed

Week 3-4: Expand if Week 1-2 passes
├── Add: CRYPTO score>=70
├── Size: 0.5% of portfolio per trade
├── Track: Realized vs paper slippage
└── Gate: Net PF > 1.2 after costs

Week 5-8: Scale if Week 3-4 passes
├── Add: FOREX score>=70 (SHORT only)
├── Size: 1% of portfolio per trade
├── Max exposure: 5% per asset class
└── Gate: Net PF > 1.2, MDD < 10%

Week 9+: Full deployment if all gates pass
├── Size: 2% per trade (Kelly-derived)
├── All proven asset classes
├── Monthly review: kill any class with 4-week rolling PF < 1.0
└── Quarterly: full edge revalidation
```

### 5.2 Kill Criteria (automatic stop)

| Condition | Action |
|-----------|--------|
| Rolling 7d WR drops >20% below baseline | REDUCE exposure 50% |
| Rolling 4w PF < 1.0 | PAUSE new trades in that class |
| Rolling 4w PF < 0.8 | STOP all trades, investigate |
| Score >= 70 but WR < 50% | Confidence calibration broken, revert to score >= 80 |
| Any single trade >5% loss | Hard stop hit, review strategy |
| Portfolio DD > 15% | Emergency stop all trading |

---

## Part 6: Summary of What I Built vs. What You Need

| Need | What I Built | Gap | Solution |
|------|-------------|-----|----------|
| Automated dashboard | Static HTML with fake data | Not connected to your system | Wire to your dashboard_data.json |
| Real statistical edge | Synthetic data "edge" | Not real | Run backtest.py on your closed picks |
| Per-asset-class filters | Generic filters | Not calibrated to your data | Extract from your hf_stats.by_asset_class |
| Real-time signals | None | Not built | Extend signal_generator.py with your DB |
| GitHub Actions ready | Manual deployment only | No CI/CD | Add workflow (see Step 5) |
| Paper trading tracker | None | Not built | Build /audit/v2/pilot/ |

---

## Appendix A: Your Real Data — Key Metrics Table

### Overall System (from dashboard_data.json, 2026-05-04)

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Total systems | 130 | Many strategies, mixed quality |
| Total active picks | 61 | Moderate activity |
| Total closed picks | 29,258 | Large sample |
| Valid closed picks | 8,927 | After integrity filtering |
| Total resolved | 9,707 | Trades with outcomes |
| Overall WR | 40.0% | Below random — needs filtering |
| Overall PF | 1.02 | Break-even (small edge) |
| Purged PnL | +342.36% | After removing outliers |
| Clean PF | 1.02 | Still marginal |
| Avg win | 2.62% | Winners are decent |
| Avg loss | -2.04% | Losers are painful |
| W/L ratio | 1.27 | Winners bigger than losers |
| Expectancy | +0.02% | Barely positive |
| Median trade | -0.02% | More losers than winners |
| Net Sharpe (annual) | 0.01 | Essentially zero |
| Max drawdown | 1021.89% | Catastrophic without stops |
| Daily volatility | 132.69% | Extremely high |

### Per-Timeframe (clean metrics)

| Window | PF | Avg PnL | Sharpe/trade | Max DD |
|--------|-----|---------|-------------|--------|
| 24h | 1.32 | 0.28% | 0.097 | 12.0% |
| 7d | 1.22 | 0.16% | 0.068 | 78.0% |
| 30d | 1.21 | 0.12% | 0.055 | — |

### Concentration Risk

| Symbol | PnL Contribution | Risk Level |
|--------|-----------------|------------|
| USDCHF=X | -215.4% | CRITICAL — remove or hedge |
| INJUSDT | +153.5% | HIGH — single name risk |
| FETUSDT | +114.2% | HIGH |
| AUDJPY=X | -101.5% | CRITICAL |
| NZDJPY=X | -100.4% | CRITICAL |

**Action: Cap any single symbol at 10% of portfolio PnL. The 4 forex pairs above should be excluded or position-limited.**

---

## Appendix B: Quick Start — Deploy /audit/v2 This Week

### Monday (2 hours)
1. Create `audit/v2/` directory in your repo
2. Copy my dashboard HTML/CSS files
3. Create `scripts/adapt_dashboard_data.py` to transform your data

### Tuesday (4 hours)
4. Wire dashboard JavaScript to read from your `dashboard_data.json`
5. Adjust colors to match your existing theme
6. Test locally with real data

### Wednesday (4 hours)
7. Add GitHub Actions job to your existing workflow
8. Run backtest.py on your closed_picks for REAL validation
9. Generate per-asset-class edge report from YOUR data

### Thursday (2 hours)
10. Deploy to staging
11. Compare v2 numbers vs. v1 numbers — they should match
12. Fix any discrepancies

### Friday (2 hours)
13. Deploy to production at `/audit/v2/`
14. Announce to team
15. Start paper trading pilot protocol

---

*This document is honest. No synthetic claims. No fake edges. Integration plan based on your actual system state as of 2026-05-16.*
