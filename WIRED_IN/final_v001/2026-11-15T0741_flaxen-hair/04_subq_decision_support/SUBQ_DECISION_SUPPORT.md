# MUTUAL FUNDS AS POTENTIAL WINNERS — Long-Term Perspective

**Worktree:** flaxen-hair_2026-11-15T0020 | **Date:** 2026-11-15T00:27Z | **Repo:** findtorontoevents_antigravity.ca

---

## User's Belief

The user believes mutual funds would be winners given enough time. This is **directionally correct** but with an important distinction:

**Mutual funds are NOT a prediction edge.** They are market beta (equity risk premium, bond yields) plus low costs. Active timing or stock-picking on top of them has NOT been proven in this system.

## Why Mutual Funds CAN Be Winners (Long-Term)

| Factor | Why It Works |
|--------|-------------|
| **Equity Risk Premium** | Stocks historically return ~7-10% annualized over multi-year periods |
| **Low Expense Ratios** | Index mutual funds: 0.015-0.20%; actively managed: 0.50-1.00% |
| **Diversification** | Hundreds/thousands of stocks reduce idiosyncratic risk |
| **Time Horizon** | 10-30 years smooths out volatility |
| **Low Turnover** | Index funds: 5-20% annually vs actively managed: 50-100% |
| **No Emotional Trading** | Automatic monthly contributions remove timing decisions |

## Mutual Fund Solid Pick Criteria (All Must Pass)

| Criterion | Threshold | Rationale |
|-----------|-----------|-----------|
| Expense ratio | ≤ 0.20% | Index funds should be cheap |
| Load fees | None | Loads destroy returns |
| 12b-1 fees | None | Marketing drag |
| Minimum investment | ≤ $1,000 | Retail accessibility |
| AUM | ≥ $1B | Liquidity, stability |
| Turnover | ≤ 20% | Lower transaction costs |
| Tracking error | ≤ 0.25% | Tight benchmark adherence |
| Track record | ≥ 10 years | Multiple market cycles |
| Net return > benchmark | 5+ years net of fees | Core "solid pick" test |
| NAV freshness | ≤ 24h | T+1 settlement |

## Starter Mutual Fund Universe

| Symbol | Name | Category | Expense Ratio | AUM |
|--------|------|----------|---------------|-----|
| VFIAX | Vanguard 500 Index Admiral | Large Blend | 0.05% | $400B+ |
| VTSAX | Vanguard Total Stock Mkt Admiral | Large Blend | 0.04% | $1.3T+ |
| FXAIX | Fidelity 500 Index Premium | Large Blend | 0.015% | $170B+ |
| VBTLX | Vanguard Total Bond Mkt Admiral | Intermediate Bond | 0.05% | $300B+ |
| VWELX | Vanguard Wellington Admiral | Allocation—50/70% Equity | 0.25% | $100B+ |
| VGSLX | Vanguard Real Estate Index Admiral | Real Estate | 0.12% | $50B+ |
| VTIAX | Vanguard Total Intl Stock Admiral | Foreign Large Blend | 0.11% | $350B+ |

*(Verify current fees/AUM from prospectus before trading)*

## Implementation: Mutual Fund Infrastructure Needed

**Zero coverage exists in this repo.** To build mutual fund support:

| # | File | Purpose |
|---|------|---------|
| 1 | alpha_engine/mutual_fund_ranker.py | Rank MF by solid-pick criteria |
| 2 | alpha_engine/data/mutual_fund_metadata.csv | Fund metadata |
| 3 | audit_dashboard/data/mutual_fund_nav_cache/ | NAV CSV cache |
| 4 | audit_dashboard/data/mf_backtest_cache/ | MF backtest cache |
| 5 | audit_dashboard/data/mf_cache_manifest.json | SHA-256 provenance manifest |
| 6 | tools/mf_traits_walkforward_runner.py | MF walkforward runner |
| 7 | tools/mf_walkforward_backtest.py | MF walkforward backtest |
| 8 | tools/mf_trait_features.py | MF trait feature computation |
| 9 | alpha_engine/mutual_fund_strategies.py | MF strategy stubs |

**Files to Modify:**
- alpha_engine/asset_class.py — Add MUTUAL_FUND_SYMBOLS, CAT_MAP, is_mutual_fund()
- ml_gatekeeper/gatekeeper.py — Add "MUTUAL_FUND": 7 to ASSET_CLASS_MAP
- audit_trail/dashboard_generator.py — Add mutual fund dashboard bucket

**Recommendation:** Do NOT build mutual fund prediction. Instead, hold low-cost index mutual funds as core allocation.

---

## OUTPERFORM S&P 500 / BUY & HOLD

### The Hard Truth

**Outperforming S&P 500 consistently is extremely difficult.** Over 10-15 year periods, ~85-90% of active managers underperform their benchmarks after fees.

| Strategy | 10-Year Beat Rate | 20-Year Beat Rate |
|----------|------------------|-------------------|
| Active Mutual Funds | ~10-15% | ~5-10% |
| Hedge Funds | ~20-30% | ~10-20% |
| Quantitative Funds | ~30-40% | ~15-25% |
| Passive Index Funds | 100% (match benchmark) | 100% (match benchmark) |

### What "Outperform Buy & Hold" Really Means

| Strategy | What It Means | Reality |
|----------|--------------|---------|
| Buy SPY, hold 10 years | Market return | ~10% annualized historical |
| Buy QQQ, hold 10 years | Tech-heavy market return | Higher vol, higher return historically |
| Tactical Asset Allocation | Match market with less drawdown | Smart-beta, not alpha |
| Active Stock Picking | Beat SPY consistently | ~10-15% of managers succeed |
| Market Timing | Avoid crashes, capture rallies | ~90% fail over long periods |

### How to "Outperform" Without Alpha

| Approach | Mechanism | Expected Result |
|----------|-----------|-----------------|
| **Lower Costs** | ER 0.05% vs 1.00% | +0.95% per year compounded |
| **Tax Efficiency** | Minimize capital gains | +0.5-1.0% per year |
| **Asset Allocation** | Stocks/bonds mix | Better risk-adjusted return |
| **Rebalancing** | Sell high, buy low | Small return boost |
| **Behavioral Discipline** | Don't panic sell | Avoid worst drawdowns |

**Bottom Line:** You don't need to beat SPY to be profitable. You need to capture market return with lower costs and lower drawdowns. That's what ETF TAA does.

---

## PROMOTIONS FOR AI CODING AGENTS IN PARALLEL WORKTREES

**Worktree:** flaxen-hair_2026-11-15T0020 | **Date:** 2026-11-15T00:27Z

---

## Prompts for AI Coding Agents

Each agent should work in isolation on their assigned asset class. Do not share results until pre-registered gates are met.

### Agent 1: Equity Researcher

```
You are auditing EQUITY strategies in /home/eaguiar2015/findtorontoevents_antigravity.ca.

TASK: Run a pre-registered benchmark test of equity strategies vs SPY total return.

REQUIREMENTS:
1. Load multi_asset/data/multi_asset_picks.json and multi_asset_closed.json
2. Filter for asset_class == "EQUITY"
3. Normalize pnl_pct to decimal ratio (fix ratio vs percent 100x bug)
4. Apply mandatory data-integrity filters:
   - Exclude resolver_version LIKE 'backfill%'
   - Exclude resolver_version IS NULL
   - Exclude banned sources (Predictions, sandbox_opposite, rapid_fire, incubator_gainer, luxalgo_filters, multi_asset_copytrader, forex_copy_trader, signal_validation, multi_asset_cot, regime_terminal, multi_asset_scanner, myfxbook_retail_contrarian, ig_contrarian_sentiment)
   - Apply sane-pnl guard: ABS(pnl_pct) <= 50 for EQUITY
   - Count EXPIRED as non-win: WR = WON / (WON+LOST+EXPIRED+FLAT)
   - Require intrabar validation (tools/reresolve_intrabar.py)
5. Compute PF, WR, avg_pnl per strategy
6. Compare vs SPY total return benchmark
7. Output: report with n, WR, PF, Sharpe, MDD, pass/fail vs gates

GATES (ALL MUST PASS):
- n ≥ 500 closed equity trades
- PF ≥ 1.15
- WR ≥ 55%
- OOS Sharpe ≥ SPY Sharpe
- Stability: first-half PF ≥ 1.05 AND second-half PF ≥ 1.05

DO NOT deploy any strategy until all gates pass.
DO NOT commit any trading logic without user approval.
```

### Agent 2: Crypto Researcher

```
You are auditing CRYPTO strategies in /home/eaguiar2015/findtorontoevents_antigravity.ca.

TASK: Fix entry_price integrity, then forward-test crypto strategies.

REQUIREMENTS:
1. Fix entry_price integrity (~29% clean, 37% >10% off bar, 7% >50%, +1.3% bias)
2. Re-resolve entries from bar-aligned NEXT-bar entries (tools/reresolve_intrabar.py)
3. Deepen OHLCV history (≥180d 1h bars; currently only ~30d)
4. Kill crypto SWING emission
5. Resolve stale open positions (>72h)
6. Forward-test POSITION horizon only, frozen rules
7. Compute PF, WR per strategy

GATES (ALL MUST PASS):
- n ≥ 100 forward picks
- PF ≥ 1.3
- WR ≥ 55%
- Regime filter: BTC > 200-EMA (bull regime only)
- Correlation limit: max 1 position per correlated group

DO NOT deploy any crypto strategy until all gates pass.
DO NOT trade crypto until entry_price integrity is fixed.
```

### Agent 3: ETF/Mutual Fund Researcher

```
You are building ETF/Mutual Fund infrastructure in /home/eaguiar2015/findtorontoevents_antigravity.ca.

TASK: Build mutual fund and ETF infrastructure from scratch.

REQUIREMENTS:
1. Create alpha_engine/mutual_fund_ranker.py
2. Create alpha_engine/data/mutual_fund_metadata.csv
3. Create audit_dashboard/data/mutual_fund_nav_cache/
4. Create audit_dashboard/data/mf_cache_manifest.json (SHA-256 provenance)
5. Create tools/mf_traits_walkforward_runner.py
6. Create tools/mf_walkforward_backtest.py
7. Create tools/mf_trait_features.py
8. Modify alpha_engine/asset_class.py — Add MUTUAL_FUND_SYMBOLS, CAT_MAP, is_mutual_fund()
9. Modify ml_gatekeeper/gatekeeper.py — Add "MUTUAL_FUND": 7 to ASSET_CLASS_MAP
10. Modify audit_trail/dashboard_generator.py — Add mutual fund dashboard bucket

MUTUAL FUND SOLID PICK CRITERIA (ALL MUST PASS):
- Expense ratio ≤ 0.20%
- Load fees = None
- 12b-1 fees = None
- Min investment ≤ $1,000
- AUM ≥ $1B
- Turnover ≤ 20%
- Tracking error ≤ 0.25%
- Track record ≥ 10 years
- Net return > benchmark 5+ years net of fees
- NAV freshness ≤ 24h

ETF SOLID PICK CRITERIA:
- Expense ratio ≤ 0.10%
- AUM ≥ $500M
- Avg daily volume ≥ $10M
- Bid-ask spread ≤ 0.05%
- Tracking error ≤ 0.20%
- Track record ≥ 5 years
- No leverage / no inverse
- Net return > benchmark 3+ years after costs

DO NOT build mutual fund prediction algorithms. Build infrastructure only.
```

### Agent 4: Risk Manager

```
You are building risk management infrastructure in /home/eaguiar2015/findtorontoevents_antigravity.ca.

TASK: Implement risk management controls and dashboard.

REQUIREMENTS:
1. Fix promotion gates in alpha_engine/money_ready_verdict.py:
   - MONEY_READY_FDR_GATE default "0" → "1"
   - MONEY_READY_SINGLE_SOURCE_GATE default "0" → "1"
2. Close cost gate fail-open paths in alpha_engine/per_class_cost_gate.py
3. Stop suppressing after-cost errors in audit_trail/dashboard_generator.py
4. Add weekly (-5%) and monthly (-10%) loss limits in alpha_engine/risk_controls.py
5. Create alpha_engine/risk_qa_validator.py with:
   - validate_pnl_pct() — flag PnL=0% with price movement
   - validate_blank_fields() — flag missing required fields
   - validate_open_items() — flag open positions >72h
   - validate_recently_closed() — flag closed picks missing exit data
   - run_all_qa_checks() — aggregate all checks
6. Wire QA checks into production_scanner.py before pick emission
7. Create alpha_engine/risk_thresholds.json — centralized risk config
8. Create risk_dashboard.html — standalone HTML with Chart.js visualizations
9. Create tools/risk_dashboard_data.py — aggregate risk data into JSON

RISK PARAMETERS:
- Position sizing: 1-2% risk per trade, Kelly 0.25× max
- Daily loss cap: -2%
- Weekly loss cap: -5%
- Monthly loss cap: -10%
- Stop loss: ATR-based (1.0× SL / 1.5× TP), min R:R 1.5:1
- Correlation limit: Max 3 per correlated group

DO NOT deploy any strategy until all risk gates pass.
```

### Agent 5: Data Integrity Auditor

```
You are auditing data integrity in /home/eaguiar2015/findtorontoevents_antigravity.ca.

TASK: Verify all data sources and fix inconsistencies.

REQUIREMENTS:
1. Fix PnL unit normalization (ratio vs percent, 100x bug) in:
   - multi_asset/data/multi_asset_closed.json (93 rows)
   - multi_asset/data/institutional_closed.json (23 rows)
   - coinglass_strategies/data/coinglass.db
2. Fix pick ID uniqueness — date-only IDs produce duplicates
3. Fix stale data:
   - recent_picks.txt: dated 2026-03-11, claims "Past 2 Hours" — fix header
   - institutional_picks.json: OPEN picks dated 2026-04-03, never resolved
   - multi_asset_picks.json: all forward_test_only, null Pnl
   - dna_factory.db: stale (2026-05-26)
   - coinglass positions: stale (max opened 2026-11-06)
   - meta_strategy.db: 5 empty tables (live_performance, walkforward_results, permutation_signals, meta_label_predictions, adversarial_compat)
4. Verify mutual funds: zero coverage — no algorithms, no data source
5. Verify ETFs: 9 hypotheses, all NOT_PROVED
6. Verify FOREX: zero DSR survivors
7. Verify BOND: n=11-18, below min_trades=60

OUTPUT: Report with all findings, fixed files, and remaining issues.

DO NOT commit any trading logic without user approval.
```

---

## WHY KALSI / POLYMARKET + COPY TRADING DOESN'T WORK

### The Core Problem

Prediction markets (Kalshi, Polymarket) and copy trading platforms appear to offer "free alpha" — just copy the winners. But they fail for structural reasons:

### 1. Selection Bias (Survivorship Bias)

| Problem | Explanation |
|---------|-------------|
| **Winner selection** | You only see the traders who are currently winning. The thousands who lost are invisible. |
| **Time window** | A trader may be up 50% in March but down 40% by June. You see them at their peak. |
| **Small sample** | Most "winning" traders have n < 20 trades. Their edge is noise. |

### 2. Cost Structure

| Cost | Impact |
|------|--------|
| **Platform fees** | Kalshi/Polymarket charge settlement fees (typically 1-2% per contract) |
| **Copy trading fees** | Copy platforms charge 10-30% of profits |
| **Spread** | Prediction markets have wide bid-ask spreads (5-10% not uncommon) |
| **Slippage** | Moving in/out of positions costs money |

**Result:** A trader needs to be right ~55-60% of the time just to break even after fees. Most are right 45-50%.

### 3. Correlation Risk

| Problem | Explanation |
|---------|-------------|
| **All copy the same trades** | When everyone copies the same "guru," the trade moves against them |
| **Liquidity crunch** | Small prediction markets can't absorb large copy flows |
| **Correlated losses** | When the guru loses, all copiers lose simultaneously |

### 4. Information Asymmetry

| Problem | Explanation |
|---------|-------------|
| **Guru has private info** | The guru may know something copiers don't |
| **Guru changes strategy** | The guru may stop copying their own successful strategy |
| **Guru has different risk tolerance** | The guru may risk 5% per trade; copiers risk 1% |

### 5. The Copy Trading Death Spiral

```
1. Guru posts winning trade → Copiers copy → Trade moves against guru
2. Guru exits early → Copiers stuck with losses
3. Copiers blame guru → Guru stops sharing
4. New "guru" appears → Cycle repeats
```

### 6. The Evidence in This Repo

| Evidence | Finding |
|----------|---------|
| `copy_trader_intel/` | Copy trader strategies exist but show negative PnL |
| `copy_trader_highscore` | n=326, WR 31.9%, PF 0.77, PnL -80% — **losing** |
| `copy_trader_clone` | Negative PnL contributors |
| AI Tournament | 39 models, ~47% picks still OPEN, none with n≥100 resolved + PF > 1.5 |
| `multi_asset_copytrader` | Listed in BLOCKED_SOURCE_SYSTEMS |

**Bottom Line:** Copy trading prediction markets does not work because:
1. The "winners" are survivors of a lottery
2. Fees eat all edge
3. Correlation causes crowding
4. Information asymmetry favors the original trader, not the copier

---

## Final Recommendation

**Do not copy trade prediction markets.** The evidence in this repo confirms it doesn't work. Instead:

1. **Fix measurement** (entry_price, PnL normalization, blank fields)
2. **Build mutual fund + ETF infrastructure** (zero coverage)
3. **Run EQUITY benchmark test** (slot 1)
4. **Run CRYPTO forward test** (slot 2, conditional on fill fix)
5. **Hold low-cost index funds** as core allocation (the only proven path)
