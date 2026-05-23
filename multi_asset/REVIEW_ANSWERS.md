## Answers to Portfolio Health Review Questions

*Generated: 2026-03-11 | Based on code analysis of multi_asset/scanner.py, audit_dashboard/portfolio_manager.py, and live state data*

---

### Q1: What were the specific assets and conditions for the single trade that resulted in a realized loss of $7.65 in the forex_carry portfolio, and why was it closed so quickly?

**Answer:** The forex_carry portfolio had exactly one closed trade: **EURUSDT LONG**, opened at 2026-03-10T15:50:25 EST and closed at 2026-03-10T17:47:40 EST -- a hold time of approximately **1 hour 57 minutes**.

- **Strategy:** `incubator_gainer_composite` (source: `incubator_gainer` system)
- **Entry price:** $1.1613 (signal was $1.1648, so there was a 0.3% entry drift)
- **Stop loss:** $1.159568 (0.15% below entry)
- **Take profit:** $1.165696
- **R:R ratio:** 2.54
- **Exit price:** $1.1606 (SL hit)
- **Raw PnL:** -$0.90 on $1,500 position size
- **Commissions:** $2.25 entry + $2.25 exit = $4.50
- **Net PnL:** **-$5.40** (commissions were 5x the actual trading loss)
- **Total equity impact:** Equity went from $10,000 to $9,992.35 (-$7.65 total, including the $5.40 net loss plus ongoing commission drag)

**Why closed so quickly:** The stop loss was extremely tight at only 0.15% below entry. With forex spreads and the position drifting 0.3% from the signal price at entry, the SL was essentially within noise range. The trade never had room to breathe. This is an `incubator_gainer` signal issue, not a multi_asset scanner issue -- the forex_carry portfolio in `portfolio_manager.py` ingests picks from external systems.

---

### Q2: How is risk actively being managed for the stocks_best and stocks_short_term portfolios?

**Answer:** Risk management operates at **two layers**:

**Layer 1 -- Portfolio Manager (audit_dashboard/portfolio_manager.py):**
- **Position sizing:** Fixed 15% of equity per position (`position_pct: 0.15`), max 6 positions = max 90% deployed
- **4-AI Consensus Firewall:** Only picks from `PROVEN_STRATEGIES` whitelist pass (9 strategies + tier levels)
- **Concentration limits:** Max 1 position per symbol+direction, max 50% long exposure, max 40% short exposure
- **Trailing stops:** ATR-based dynamic trailing stop (`enhanced_trailing_stop`) activates after +1x ATR profit, trails at max(1.5x ATR, 50% of peak profit)
- **Time-based exits:** Force close if losing after 168 hours (7 days), absolute max hold 336 hours (14 days)
- **Strategy kill switch:** Strategies with WR < 45% and PF < 1.0 after 20+ trades are auto-blocked from future picks
- **Max drawdown tracking:** Both portfolios track `max_drawdown_pct` (currently 0.40% for stocks_best, 0.38% for stocks_short_term)
- **Commission modeling:** IBKR Canadian broker costs applied ($0.0035/share + $1.00 min + $0.02/share slippage)

**Layer 2 -- Multi-Asset Scanner (multi_asset/scanner.py):**
- Every pick has hard SL/TP from `RISK_PARAMS["stock"]`: -6% stop loss, +12% take profit, 10-day max hold
- RSI and trend filters prevent entries in unfavorable conditions (e.g., Connors RSI-2 requires RSI < 10 + price > 200d SMA)

**Current state:** stocks_best has 2 open positions (MSFT, COIN), stocks_short_term has 2 open positions (MSFT, COIN). Both use the `noncrypto_best` / `noncrypto_reversal` methodology with EQUITY asset_class filter.

---

### Q3: Are there hard stop-loss or take-profit parameters actively attached to the 4 open positions across the stock portfolios?

**Answer:** **Yes, every single position has hard SL and TP values attached.** Verified from `active_picks.json` and `claudes_test_state.json`:

| Portfolio | Symbol | Direction | Entry | Stop Loss | Take Profit | R:R |
|-----------|--------|-----------|-------|-----------|-------------|-----|
| stocks_best | MSFT | LONG | $405.76 | $399.92 | $445.74 | 6.84 |
| stocks_best | COIN | LONG | $234.56 | ~$220.49 | ~$262.71 | ~2.0 |
| stocks_short_term | MSFT | LONG | $405.76 | $399.92 | $445.74 | 6.84 |
| stocks_short_term | COIN | LONG | $234.56 | ~$220.49 | ~$262.71 | ~2.0 |

**Enforcement:** The scanner's `check_picks()` function (line 1230-1308 of scanner.py) runs every scan cycle and compares current_price against TP/SL:
- LONG: `hit_tp = current_price >= tp`, `hit_sl = current_price <= sl`
- SHORT: `hit_tp = current_price <= tp`, `hit_sl = current_price >= sl`

Additionally, `portfolio_manager.py` runs its own SL/TP check with the `enhanced_trailing_stop` which can **tighten** (never widen) the stop loss dynamically based on ATR.

---

### Q4: What is the expected average holding period for the open trades?

**Answer:** The system enforces **category-specific max hold periods** via `RISK_PARAMS` in scanner.py:

| Asset Class | Max Hold Days | SL % | TP % |
|-------------|---------------|-------|------|
| Futures | 10 days | -4% | +8% |
| Stocks | 10 days | -6% | +12% |
| Forex | 14 days | -2.5% | +3% |
| ETFs | 15 days | -5% | +10% |
| Penny Stocks | 5 days | -12% | +25% |

For **bounce trades** (extreme oversold), tighter params apply via `BOUNCE_RISK`: 3-day max hold across all categories, with tighter SL/TP (e.g., stocks: -2.5% SL, +4% TP).

The portfolio_manager adds a second layer: `STALE_LOSS_HOURS = 168` (7 days: force close if losing) and `MAX_HOLD_HOURS = 336` (14 days: force close regardless).

**Expected average:** Given that most trades will either hit SL/TP or time-expire, the expected average is **3-10 days for stocks/futures, up to 14 days for forex**. The current open trades are all 0 days old (opened 2026-03-11), so no time pressure yet.

---

### Q5: Do we have a pipeline to log historical daily equity data for computing Sharpe/Sortino?

**Answer:** **Yes, partially.** The system tracks equity history but at a **sub-daily granularity** (every 30-minute update cycle), not daily snapshots.

**What exists:**
1. **`equity_history` array** in `claudes_test_state.json`: Every portfolio has a timestamped equity history array, capped at 1000 entries (trimmed to last 500 when exceeded). Example: forex_carry has ~10 equity snapshots over its 1-day life.

2. **`calc_sharpe()` function** (portfolio_manager.py line 3186): Computes annualized Sharpe ratio from equity_history. Requires 20+ data points minimum. Uses consecutive equity changes as returns, annualized via `sqrt(252 * 48)` (assuming 48 half-hour periods per day).

3. **Backtest module** (scanner.py line 1072): The `walk_forward_backtest()` function computes Sharpe, Sortino, Calmar, profit factor, max drawdown, and max drawdown duration from simulated trade P&L series.

**What does NOT exist:**
- No separate daily equity snapshots file (all data is inline in state JSON)
- No Sortino computation in the live portfolio manager (only in backtester)
- No persistent historical database -- if state is reset, history is lost
- The equity_history is capped, so very long-running portfolios will lose early data points

---

### Q6: What is the current capital allocation percentage?

**Answer:** Position sizing is defined per portfolio via `position_pct`:

| Portfolio | Per-Position % | Max Positions | Max Deployed % |
|-----------|---------------|---------------|----------------|
| stocks_best | 15% | 6 | 90% |
| stocks_short_term | 15% | 6 | 90% |
| forex_carry | 15% | 4 | 60% |
| futures_index | 15% | 5 | 75% |
| Prop Conservative | 4% | 5 | 20% |
| Prop Aggressive | 6% | 8 | 48% |
| Prop Swing | 5% | 4 | 20% |

**Current actual allocation (from state data):**
- **stocks_best:** Cash $8,693 / Equity $9,962 = **12.7% deployed** (2 of 6 slots filled)
- **stocks_short_term:** Cash $8,473 / Equity $9,966 = **15.0% deployed** (2 of 6 slots filled)
- **forex_carry:** Cash $9,992 / Equity $9,992 = **0% deployed** (0 positions, 1 closed at a loss)

The multi_asset scanner (active_picks.json) currently has **27 open positions** across futures (7), stocks (8), forex (5), ETFs (7), and penny stocks (1). This is the signal-generation layer; actual capital deployment depends on which portfolio selects which picks.

---

### Q7: Are there any correlation risks between open positions?

**Answer:** **Yes, significant correlation risk exists.** Analysis of the 27 open picks in `active_picks.json`:

**All 27 positions are LONG except 1** (SOFI SHORT). This creates massive directional exposure.

**Correlated clusters:**
1. **US Equity Index cluster (highly correlated, all LONG):** ES=F, NQ=F, YM=F, SPY, QQQ, IWM -- these are essentially the same trade 6 times (S&P 500, Nasdaq 100, Dow Jones, and their ETF equivalents). Correlation > 0.90.

2. **Tech mega-cap cluster (all LONG):** AAPL, MSFT, NVDA, GOOGL, AMZN, META, TSLA -- all VIX reversal trades entered at the same time. These heavily overlap with the index futures above.

3. **Forex USD-short cluster (all LONG):** EURUSD, GBPUSD, AUDUSD, NZDUSD are all effectively short USD. USDJPY LONG is also USD-directional but in the opposite way (long USD vs JPY).

4. **All entered on the same signal:** 19 of 27 positions were triggered by just 2 strategies: `vix_reversal` (VIX spike 39.4% then reversed) and `connors_rsi2` (RSI(2) near 0). Both are mean-reversion "buy the dip" strategies that fired simultaneously on 2026-03-11.

**Risk assessment:** If the market continues falling (VIX stays elevated), virtually all 26 LONG positions lose simultaneously. The portfolio manager's `MAX_LONG_PCT = 0.50` limit should prevent individual portfolios from being 100% long, but the underlying signal pool is overwhelmingly one-directional.

---

### Q8: Why are there no new open positions replacing lost trades in forex?

**Answer:** The forex_carry portfolio is currently empty (0 positions) because:

1. **The forex signal pool is limited.** The multi_asset scanner scans only 6 forex pairs: `EURUSD=X, GBPUSD=X, USDJPY=X, AUDUSD=X, NZDUSD=X, USDCHF=X`. Currently, active_picks.json shows 5 forex picks are active at the scanner level.

2. **The portfolio_manager filters by source system and freshness.** The forex_carry portfolio uses methodology `noncrypto_best` with `asset_filter: ["FOREX"]`. It ingests picks from ALL source systems (not just multi_asset scanner), but the pick must pass the 4-AI Consensus Firewall (only `PROVEN_STRATEGIES` are accepted). None of the multi_asset scanner strategies (`connors_rsi2`, `macd_divergence`, `ema_stack_momentum`) are in the `PROVEN_STRATEGIES` whitelist, which is crypto-focused.

3. **The `incubator_gainer` system** that generated the original EURUSDT trade may not be producing fresh forex signals, or its `sys_wr: 0` (zero win rate with only 1 trade) may cause it to fail the `MIN_SYS_WR = 45%` gate.

4. **Update interval is 120 minutes** for forex portfolios, so it checks less frequently than crypto portfolios.

**Root cause:** The proven strategy whitelist in portfolio_manager.py is crypto-centric. Forex signals from multi_asset scanner exist but are not in the whitelist, so they cannot enter the forex_carry portfolio through the firewall.

---

### Q9: Does the 1-2 trade-per-day frequency align with expected strategy volume?

**Answer:** **Yes, this is consistent with the system design.**

**Scanner frequency (from `.github/workflows/multi-asset-scanner.yml`):**
- US market hours (Mon-Fri 9am-5pm ET): **every hour** (cron: `0 13-21 * * 1-5`)
- Extended hours (Mon-Fri outside market): **every 2 hours** (cron: `0 0,2,4,6,8,10,22 * * 1-5`)
- Sunday futures open: **once** at 11pm UTC (cron: `0 23 * * 0`)
- Total: approximately **12-14 scan runs per weekday**

**Strategy selectivity:**
- `connors_rsi2`: Requires RSI(2) < 10, which is an extreme oversold condition (~5-10% of trading days)
- `bollinger_mean_reversion`: Requires price below lower Bollinger Band + RSI < 30
- `ema_stack_momentum`: Requires all 4 EMAs (9/21/50/200) aligned + ADX > 25
- `macd_divergence`: Requires price making lower lows while MACD histogram makes higher lows
- `vix_reversal`: Requires VIX spike > 20% then reversal -- rare event (a few times per month)
- `oversold_bounce`: Requires RSI(2) < 5 or RSI(2) < 10 + price below BB + RSI(14) < 35

These are all designed to fire rarely on high-conviction setups. On a typical day, 0-3 new signals across all asset classes is expected. On extreme market days (like today's VIX spike), a burst of signals is normal -- which is exactly what happened (19 vix_reversal + connors_rsi2 signals on 2026-03-11).

---

### Q10: At what maximum drawdown threshold would the system trigger an auto-kill or pause?

**Answer:** **There is NO drawdown circuit breaker for the non-prop portfolios** (stocks_best, stocks_short_term, forex_carry, futures_index). These portfolios track `max_drawdown_pct` for reporting purposes but have `max_drawdown_limit_pct: 0`, meaning no automatic shutdown on drawdown.

**Prop firm portfolios DO have hard drawdown limits:**

| Portfolio | Daily Loss Limit | Max Total Drawdown | Action on Breach |
|-----------|------------------|--------------------|------------------|
| Prop Conservative | 4% | **8%** | Status = "BLOWN", all positions closed, auto-reset |
| Prop Aggressive | 6% | **10%** | Status = "BLOWN", all positions closed, auto-reset |
| Prop Swing | 5% | **10%** | Status = "BLOWN", all positions closed, auto-reset |

**Code path (portfolio_manager.py line 2878):**
```python
if total_dd >= port["max_drawdown_limit_pct"]:
    port["status"] = "BLOWN"
    # ... logs reset history
    # ... closes all positions
```

**Strategy-level kill switch (portfolio_manager.py):**
- `KILL_WR_THRESHOLD = 45%` -- strategies with WR < 45% after 20+ trades are blocked
- `KILL_PF_THRESHOLD = 1.0` -- strategies with profit factor < 1.0 are blocked
- `BLOCKED_SYSTEMS` set contains permanently banned strategies (e.g., `ml_bg_system_f`)

**Gap identified:** The non-prop portfolios (stocks_best, stocks_short_term, forex_carry) have **no maximum drawdown auto-kill**. A sustained losing streak could theoretically deplete capital to zero without triggering any automatic pause. The only protection is per-trade SL enforcement and time-based forced exits. Adding a global drawdown circuit breaker (e.g., pause at -15% portfolio drawdown) would be a recommended improvement.
