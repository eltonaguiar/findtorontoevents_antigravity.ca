# PROVEN STRATEGY PER ASSET CLASS — Master Plan
## Date: 2026-04-11
## Goal: At least 1 strategy per asset class with n≥30, WR>breakeven, p<0.01

---

# THE CORE PROBLEM

You have ~100 strategies running across ~7 asset classes, but only **2 strategies** have statistically proven edge. Everything else is either unvalidated, insufficient data, or confirmed losers. The goal is to get from 2 to **at least 7** (one per asset class) within 8 weeks.

---

# CURRENT STATUS BY ASSET CLASS

| Asset Class | Proven Strategy | Status | WR | n | Sharpe | Gap to Fill |
|-------------|----------------|--------|-----|---|--------|-------------|
| **CRYPTO** | st_fear_greed_contrarian | ✅ PROVEN | 69.4% | 291 | — | None — deploy now |
| **EQUITY** | A_SuperTrend_VWMA (backtest) | 🟡 BACKTEST ONLY | 62-71% | 26-43 | 2.0-2.4 | Needs forward validation |
| **EQUITY** | Connors RSI-2 (SPY/QQQ) | ✅ PROVEN (AUDIT) | 75% | 74 | 4.8-6.5 | Not in live pipeline |
| **COMMODITY** | C_Triple_Confirmation (Gold/NG) | 🟡 BACKTEST ONLY | 62-73% | 59-63 | 2.2-2.3 | Needs forward validation |
| **ETF** | A_SuperTrend_VWMA (XLP/XLK) | 🟡 BACKTEST ONLY | 60-66% | 44-47 | 1.4-2.0 | Needs forward validation |
| **FOREX** | F_SHORT_Only_Contrarian (EURUSD) | 🟡 BACKTEST ONLY | 84.6% | 13 | 2.15 | n too low (need 30+) |
| **BONDS** | Nothing | ❌ NONE | — | 8 total | — | Build from scratch |
| **FUTURES** | E_Momentum_Persistence (ES=F) | 🟡 BACKTEST ONLY | 60% | 15 | 1.37 | n too low |

---

# THE STRATEGY PROVING PIPELINE

Every strategy must pass through 4 gates before it gets "PROVEN" status:

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────┐
│  GATE 1     │───>│  GATE 2      │───>│  GATE 3      │───>│  GATE 4  │
│  Backtest   │    │  Walk-Forward│    │  Paper Forward│    │  PROVEN  │
│  (history)  │    │  (OOS split) │    │  (live market)│    │  (deploy)│
└─────────────┘    └──────────────┘    └──────────────┘    └──────────┘
   n ≥ 30             Metrics within      n ≥ 30 new          Auto-
   WR > BE            30% of Gate 1       trades in real      promote
   PF > 1.2           No regime cherry    time, no tweaks     to live
   Sharpe > 1.0       picking                                 pipeline
```

**What makes this different from what you have now:**
- Gate 2 prevents overfitting (current backtests don't have proper OOS holdout)
- Gate 3 is real-time — no looking at results and tweaking
- Gate 4 is automatic — no manual kill lists or hand-picked tiers

---

# ASSET CLASS 1: CRYPTO ✅ (Already Proven)

## Strategy: `st_fear_greed_contrarian`
- **Status**: PROVEN — 291 trades, 69.4% WR, 17/19 symbols profitable
- **Action**: Deploy as primary crypto strategy NOW

## Enhancement: Add Regime Filter
Currently loses money in sustained bears. Add:
```python
def should_take_signal(fgi_value, btc_regime):
    if fgi_value < 25 and btc_regime in ["bull", "neutral", "sideways"]:
        return True  # Extreme fear + not in bear = BUY
    return False
```
Expected improvement: WR from 69.4% → ~75% by avoiding bear-market whipsaws.

## Backup Strategy: Keltner Compression Expansion
- SOL variant: 77.8% WR, 18 trades (need 12 more for Gate 3)
- ETH variant: 72.2% WR, 18 trades
- **Action**: Continue paper trading, graduate at n=30

## Backup Strategy: Whale Copy Trading
- `copy_hl_whale_24.5M`: 68.8% WR, 16 symbols, MULTI_SYMBOL tier
- **Action**: Continue but fix Bitget 403 first for fresh data

---

# ASSET CLASS 2: EQUITY ✅ (Almost Proven — 2 weeks to go)

## Primary Strategy: Connors RSI-2
- **Status**: PROVEN in AUDIT (Sharpe 4.8-6.5) but NOT in live pipeline
- Already coded in `alpha_engine/strategies/connors_rsi2.py`
- Currently only scans SPY, QQQ + 4 crypto symbols

### Action: Expand and Deploy
```python
# Expand symbol universe in connors_rsi2.py
EQUITY_SYMBOLS = [
    "SPY", "QQQ",           # Already proven (75% WR)
    "IWM", "DIA",           # Other major indexes
    "AAPL", "MSFT", "GOOGL", "AMZN", "META",  # Mega-cap (institutional bid)
    "JNJ", "PG", "WMT", "HD",  # Defensive (strong mean-reversion)
]
```

### Why It Works Across Equities (Not Just SPY/QQQ)
RSI-2 mean-reversion works on ANY liquid equity with consistent institutional buying:
- Pension funds rebalance into dips (structural buyer)
- Market makers provide liquidity at extremes (structural floor)
- The more liquid the name, the stronger the mean-reversion

### Validation Plan
- Run on expanded universe for 60 days
- Need: n ≥ 30 trades total, WR > 60%, PF > 1.2
- Timeline: 6-8 weeks (RSI-2 triggers ~2-3 signals/week across this universe)

## Secondary Strategy: A_SuperTrend_VWMA (Daily)
- **Status**: Backtested with Sharpe > 2.0 on GOOGL, MSFT, QQQ, WMT
- Already in the cross_asset_edge_finder pipeline

### Action: Deploy as Paper Forward Test
Create a new workflow: `supertrend-vwma-forward-test.yml`
- Run daily on the 5 best equity symbols from backtest
- Log signals to `alpha_engine/data/supertrend_forward_test.json`
- Do NOT include in live picks until Gate 3 passes (n ≥ 30)
- Timeline: 8-12 weeks (SuperTrend generates ~1 trade/week per symbol)

## Third Strategy: Quality Value (Already Coded, Needs Validation)
- `quality_value.py` exists in `alpha_engine/strategies/`
- Implements Piotroski F-Score + ROE + Value composite
- **Action**: Backtest on 2 years of data, then paper forward test
- This is a long-horizon strategy (monthly rebalance) — takes 6+ months to validate

---

# ASSET CLASS 3: COMMODITY 🟡 (Backtest Done, Needs Forward)

## Primary Strategy: C_Triple_Confirmation on Gold (GC=F) 1h
- **Backtest**: 59 trades, 72.9% WR, PF 1.91, Sharpe 2.26
- This is your best commodity signal from cross_asset_edge_finder

### What C_Triple_Confirmation Does
It requires 3 independent signals to align before entry:
1. Trend direction (SuperTrend or MA)
2. Momentum confirmation (RSI or MACD)
3. Volume confirmation (above-average volume)

Triple confirmation = fewer signals but much higher quality.

### Action: Deploy as Paper Forward Test
```yaml
# New workflow: commodity-triple-confirm-forward.yml
# Symbols: GC=F (gold), NG=F (nat gas), SI=F (silver), CL=F (oil)
# Timeframe: 1h
# Run: Every hour during commodity market hours
# Output: alpha_engine/data/commodity_forward_test.json
```

### Timeline
- Commodities trade 23h/day, 5.5 days/week
- With 4 symbols × 1h timeframe, expect ~3-5 trades/week
- Gate 3 (n=30): 6-10 weeks

## Secondary Strategy: A_SuperTrend_VWMA on Silver/Copper/Oil
- Already backtested: SI=F (Sharpe 2.18), CL=F (1.42), HG=F (1.42)
- **Action**: Paper forward test alongside Triple Confirmation
- Compare which performs better in real-time

---

# ASSET CLASS 4: ETF 🟡 (Backtest Done, Needs Forward)

## Primary Strategy: A_SuperTrend_VWMA on Sector ETFs
- **Backtest**: XLP 1h (Sharpe 2.04), XLK 1d (1.41), XLV 1h (1.32)

### Why Sector ETFs Are Special
Sector ETFs are ideal for trend-following because:
- They represent diversified baskets (less random noise than single stocks)
- Sector rotation is a well-documented phenomenon
- Institutional sector rebalancing creates persistent trends

### Action: Deploy Paper Forward Test
```python
ETF_UNIVERSE = [
    "XLP",  # Consumer Staples — Sharpe 2.04 in backtest
    "XLK",  # Technology — Sharpe 1.41
    "XLV",  # Healthcare — Sharpe 1.32
    "XLF",  # Financials — not yet backtested, add
    "XLI",  # Industrials — not yet backtested, add
    "XLU",  # Utilities — not yet backtested, add (defensive sectors mean-revert well)
]
```

### Timeline
- Daily timeframe = slower signal generation
- Expect ~1-2 trades/week across 6 ETFs
- Gate 3 (n=30): 15-20 weeks
- **Acceleration**: Also run the 1h timeframe for XLP/XLV (more signals)

## Bonus Strategy: RSI-2 on SPY/QQQ ETFs
- Already proven on these as equity — they're also the most liquid ETFs
- This can double-count for both EQUITY and ETF asset classes

---

# ASSET CLASS 5: FOREX 🔴 (Needs Work)

## The Problem
Forex is your worst asset class. The quality_gates comment says it all: "FOREX WR=16% p=0.999 — catastrophic."

## Why Forex Is Hard
1. **Near-efficient**: G7 FX pairs are the most liquid markets on Earth. Every basis point of edge is competed away by banks, HFTs, and sovereign wealth funds.
2. **Transaction costs matter more**: FX spreads look small (1-3 pips) but on small moves they eat 30-50% of the signal.
3. **Carry is the only persistent factor**: Interest rate differentials drive long-term FX returns. Everything else is noise.

## What Actually Works in Forex (Academic Literature)

### Strategy A: Carry Trade (Proven Factor)
- **What**: Buy high-yield currencies, sell low-yield currencies
- **Why it works**: Risk premium — investors get compensated for holding volatile EM currencies
- **Expected WR**: 55-60% with PF > 1.3
- **Academic source**: Lustig, Roussanov, Verdelhan (2011) — "Common Risk Factors in Currency Markets"
- **Implementation**: Simple — rank currencies by 3-month yield differential, go long top 3, short bottom 3

### Strategy B: RSI-2 Adapted for Forex
- Take the proven Connors RSI-2 logic
- Apply to major forex pairs (EUR/USD, GBP/USD, USD/JPY, AUD/USD)
- Tighter TP/SL (forex moves are smaller): TP = 1.5x ATR, SL = 1.0x ATR
- Only trade in direction of the 50-day MA (trend filter)

### Strategy C: F_SHORT_Only_Contrarian (EURUSD)
- Already backtested: 84.6% WR, PF 4.23, Sharpe 2.15
- Problem: Only 13 trades
- **Action**: Continue paper trading until n=30

### The Forex Plan
```
Week 1-2: Implement carry trade strategy
Week 3-4: Adapt RSI-2 for forex pairs
Week 5-12: Paper forward test all three strategies
Week 13: Evaluate — promote whichever hits Gate 3 first
```

### Realistic Expectation
Forex edge will be smaller than equity/crypto. Target:
- WR: 55-60% (not 70%+)
- PF: 1.2-1.5 (not 2.0+)
- Sharpe: 1.0-1.5 (not 2.0+)
- That's fine — it's still positive expectancy

---

# ASSET CLASS 6: BONDS 🔴 (Build From Scratch)

## The Problem
Only 8 closed bond trades total. No strategy, no data, no edge.

## What Works in Bonds (Academic Literature)

### Strategy A: Duration Momentum (TSMOM on Bond Futures)
- **What**: When bond prices are trending up (yields falling), go long. When trending down, go short.
- **Why it works**: Central bank policy creates persistent trends in rates. When the Fed is cutting, bonds trend up for months. When hiking, they trend down.
- **Academic source**: Moskowitz, Ooi, Pedersen (2012) — "Time-Series Momentum" — validated on bond futures over 25 years.
- **Implementation**:
```python
def bond_tsmom_signal(price_series, lookback=60):
    """Time-series momentum on bond prices."""
    ret = price_series.pct_change(lookback).iloc[-1]
    if ret > 0:
        return "LONG"  # Price trending up = yields falling
    elif ret < 0:
        return "SHORT"  # Price trending down = yields rising
    return None
```
- **Symbols**: TLT (20Y Treasury), IEF (7-10Y Treasury), BND (Total Bond), SHY (1-3Y Treasury)

### Strategy B: Yield Curve Mean-Reversion
- **What**: When the 2Y-10Y spread is extreme, it tends to revert
- **Why it works**: The yield curve reflects economic consensus. When it's extreme (deeply inverted or steeply positive), the consensus is usually wrong and the curve normalizes.
- **Implementation**: Track 2Y-10Y spread via TLT/SHY ratio

### The Bond Plan
```
Week 1-2: Implement TSMOM on TLT/IEF/BND (daily timeframe)
Week 3-4: Backtest on 3+ years of data
Week 5-12: Paper forward test
Week 13+: Evaluate — bonds trade slowly, may need 4-6 months for n=30
```

### Realistic Timeline
Bonds are slow-moving. Daily signals mean ~1-2 trades/month per symbol. With 4 symbols, that's 4-8 trades/month. **Gate 3 (n=30) will take ~4-6 months.** This is the longest path to proving.

---

# ASSET CLASS 7: FUTURES 🔴 (Mostly Broken)

## The Problem
- Only 5 closed futures trades (4 losers + 1 phantom bug)
- Symbol format mismatches (/ES vs ES=F vs ES1!)
- Entire FUTURES asset class is BLOCKED in quality_gates

## What Works in Futures

### Strategy A: TSMOM (Time-Series Momentum)
- THE most documented factor in futures. Moskowitz et al. (2012) tested it across **58 liquid futures** spanning:
  - Equity index futures (ES, NQ, YM, RTY)
  - Bond futures (ZN, ZB, ZF)
  - Commodity futures (GC, SI, CL, NG, ZC, ZW)
  - FX futures (6E, 6B, 6J)
- Average Sharpe: 1.5-2.0 across all asset classes
- Works because of: herding behavior, slow information diffusion, institutional mandates that force trend-following

### Strategy B: E_Momentum_Persistence (Already Backtested)
- ES=F 1h: 15 trades, 60% WR, Sharpe 1.37
- Conceptually similar to TSMOM but on shorter timeframe
- **Action**: Continue forward test on ES=F, add NQ=F, YM=F

### The Futures Plan
```
Week 1: Fix symbol format mismatches (standardize to =F suffix)
Week 1: Unblock FUTURES in quality_gates (remove from BLOCKED_ASSET_CLASSES)
Week 2-3: Implement proper TSMOM on 8-10 liquid futures
Week 4-12: Paper forward test
```

### Realistic Timeline
Futures have good liquidity and trade nearly 24h — signal generation is fast. With 8 symbols on daily timeframe: ~8-16 trades/month → **Gate 3 in 2-4 months.**

---

# THE IMPLEMENTATION: WHAT TO BUILD

## Tool 1: `tools/strategy_prover.py` — The Universal Validation Pipeline

```python
"""
Strategy Prover — runs any strategy through the 4-gate proving pipeline.

Usage:
    python tools/strategy_prover.py --strategy connors_rsi2 --asset-class EQUITY
    python tools/strategy_prover.py --strategy supertrend_vwma --asset-class COMMODITY
    python tools/strategy_prover.py --all  # Run all strategies through gates
"""

class StrategyProver:
    def __init__(self, strategy_name, asset_class):
        self.strategy = strategy_name
        self.asset_class = asset_class
        self.closed_picks = load_closed_picks(strategy_name, asset_class)
        self.forward_picks = load_forward_picks(strategy_name, asset_class)
    
    def gate1_backtest(self) -> dict:
        """Gate 1: Historical backtest validation."""
        n = len(self.closed_picks)
        if n < 30:
            return {"pass": False, "reason": f"n={n} < 30"}
        
        wr = self.win_rate()
        pf = self.profit_factor()
        sharpe = self.sharpe_ratio()
        be_wr = self.break_even_wr()  # Based on actual R:R
        p_value = binom_test(self.wins(), n, be_wr, alternative='greater')
        
        passes = (
            wr > be_wr and
            pf > 1.2 and
            sharpe > 1.0 and
            p_value < 0.01
        )
        
        return {
            "pass": passes,
            "n": n, "wr": wr, "pf": pf, "sharpe": sharpe,
            "p_value": p_value, "break_even_wr": be_wr,
        }
    
    def gate2_walk_forward(self) -> dict:
        """Gate 2: Out-of-sample validation (split data 70/30)."""
        train = self.closed_picks[:int(len(self.closed_picks) * 0.7)]
        test = self.closed_picks[int(len(self.closed_picks) * 0.7):]
        
        train_wr = win_rate(train)
        test_wr = win_rate(test)
        
        # Test metrics must be within 30% of train
        wr_decay = abs(train_wr - test_wr) / train_wr
        passes = wr_decay < 0.30 and test_wr > self.break_even_wr()
        
        return {
            "pass": passes,
            "train_wr": train_wr, "test_wr": test_wr,
            "decay_pct": wr_decay * 100,
        }
    
    def gate3_paper_forward(self) -> dict:
        """Gate 3: Paper forward test (real-time, no tweaks)."""
        n = len(self.forward_picks)
        if n < 30:
            return {"pass": False, "reason": f"forward n={n} < 30, need more time"}
        
        wr = win_rate(self.forward_picks)
        pf = profit_factor(self.forward_picks)
        
        passes = wr > self.break_even_wr() and pf > 1.0
        return {"pass": passes, "n": n, "wr": wr, "pf": pf}
    
    def gate4_auto_promote(self) -> str:
        """Gate 4: Automatic promotion based on gates 1-3."""
        g1 = self.gate1_backtest()
        g2 = self.gate2_walk_forward()
        g3 = self.gate3_paper_forward()
        
        if g1["pass"] and g2["pass"] and g3["pass"]:
            return "PROVEN"
        elif g1["pass"] and g2["pass"] and not g3["pass"]:
            return "PAPER_TESTING"
        elif g1["pass"] and not g2["pass"]:
            return "BACKTEST_ONLY"
        else:
            return "UNPROVEN"
    
    def full_report(self) -> dict:
        return {
            "strategy": self.strategy,
            "asset_class": self.asset_class,
            "gate1": self.gate1_backtest(),
            "gate2": self.gate2_walk_forward(),
            "gate3": self.gate3_paper_forward(),
            "final_tier": self.gate4_auto_promote(),
        }
```

## Tool 2: `tools/asset_class_scorecard.py` — Weekly Health Report

```python
"""
Generates the weekly scorecard showing proving status per asset class.

Output: updates/YYYY-MM-DD-asset-class-scorecard.md
"""

def generate_scorecard():
    asset_classes = ["CRYPTO", "EQUITY", "COMMODITY", "ETF", "FOREX", "BONDS", "FUTURES"]
    
    for ac in asset_classes:
        strategies = get_strategies_for_asset_class(ac)
        
        print(f"\n{'='*60}")
        print(f"  {ac}")
        print(f"{'='*60}")
        
        for strat in strategies:
            prover = StrategyProver(strat, ac)
            report = prover.full_report()
            
            status_emoji = {
                "PROVEN": "✅",
                "PAPER_TESTING": "🟡",
                "BACKTEST_ONLY": "🟠",
                "UNPROVEN": "❌",
            }
            
            print(f"  {status_emoji[report['final_tier']]} {strat}")
            print(f"     Gate 1 (Backtest):  {'PASS' if report['gate1']['pass'] else 'FAIL'}")
            print(f"     Gate 2 (OOS):       {'PASS' if report['gate2']['pass'] else 'FAIL'}")
            print(f"     Gate 3 (Forward):   {'PASS' if report['gate3']['pass'] else 'FAIL'}")
            print(f"     Status: {report['final_tier']}")
```

## Tool 3: New Workflow — `strategy-forward-tester.yml`

```yaml
# One workflow to rule them all — runs all paper forward tests
name: Strategy Forward Tester
on:
  schedule:
    - cron: '0 */2 * * *'  # Every 2 hours
  workflow_dispatch:

jobs:
  forward-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run forward tests
        run: |
          # Crypto: fear/greed contrarian + keltner
          python alpha_engine/strategies/fear_greed_forward.py
          
          # Equity: RSI-2 on expanded universe + SuperTrend VWMA
          python alpha_engine/strategies/connors_rsi2.py
          python alpha_engine/strategies/supertrend_vwma_equity.py
          
          # Commodity: Triple Confirmation + SuperTrend
          python alpha_engine/strategies/triple_confirm_commodity.py
          
          # ETF: SuperTrend on sector ETFs
          python alpha_engine/strategies/supertrend_vwma_etf.py
          
          # Forex: Carry + RSI-2 adapted + SHORT contrarian
          python alpha_engine/strategies/forex_carry.py
          python alpha_engine/strategies/forex_rsi2.py
          
          # Bonds: TSMOM on TLT/IEF/BND
          python alpha_engine/strategies/bond_tsmom.py
          
          # Futures: TSMOM on ES/NQ/GC/CL
          python alpha_engine/strategies/futures_tsmom.py
          
          # Run the prover on all forward tests
          python tools/strategy_prover.py --all
          
      - name: Commit results
        run: |
          git add alpha_engine/data/forward_tests/ tools/data/
          git commit -m "Forward test update $(date -u +%Y-%m-%dT%H:%M)" || true
          git push
```

---

# TIMELINE TO "PROVEN IN EVERY ASSET CLASS"

| Week | Milestone | Asset Classes Proven |
|------|-----------|---------------------|
| 0 (now) | Deploy fear/greed contrarian (crypto), wire RSI-2 to pipeline | 1 (CRYPTO) |
| 2 | RSI-2 live on expanded equity universe, commodity paper tests start | 1 |
| 4 | RSI-2 hits n=30 forward equity trades → EQUITY PROVEN | 2 (+ EQUITY) |
| 6 | SuperTrend VWMA commodity hits n=30 → COMMODITY PROVEN | 3 (+ COMMODITY) |
| 8 | SuperTrend VWMA ETF hits n=30 → ETF PROVEN | 4 (+ ETF) |
| 10 | Forex carry/RSI-2 hits n=30 → FOREX PROVEN (maybe) | 5 (+ FOREX) |
| 12 | Futures TSMOM hits n=30 → FUTURES PROVEN | 6 (+ FUTURES) |
| 16-20 | Bond TSMOM hits n=30 → BONDS PROVEN | 7 (ALL) |

## Acceleration Options
- **Run more symbols**: More symbols = more signals = faster n accumulation
- **Add shorter timeframes**: 1h instead of 1d doubles signal rate (but increases costs)
- **Run on multiple exchanges**: Equity on NYSE+NASDAQ, crypto on Binance+OKX
- **But don't cheat**: n=30 means 30 INDEPENDENT trades, not the same signal counted twice

---

# WHAT TO BUILD THIS WEEK (Priority Order)

## Day 1-2: Wire the Proven Stuff

1. **Make RSI-2 actually flow into the live pipeline**
   - Currently it writes to `connors_rsi2_picks.json` but nothing reads it
   - Add it to the aggregation workflow that feeds `active_picks.json`
   - Expand to 13 equity symbols (see list above)

2. **Ensure fear/greed contrarian is unblocked for deployment**
   - Verify no kill-list entries or penalties are suppressing it
   - Check that the specific symbols (DOT, SUI, LTC, NEAR, XRP) still perform

## Day 3-4: Build the Forward Test Infrastructure

3. **Create `alpha_engine/data/forward_tests/` directory structure**
   ```
   forward_tests/
   ├── crypto/
   │   ├── fear_greed_contrarian.json
   │   └── keltner_compression.json
   ├── equity/
   │   ├── connors_rsi2.json
   │   └── supertrend_vwma.json
   ├── commodity/
   │   ├── triple_confirmation.json
   │   └── supertrend_vwma.json
   ├── etf/
   │   └── supertrend_vwma.json
   ├── forex/
   │   ├── carry_trade.json
   │   ├── rsi2_adapted.json
   │   └── short_contrarian.json
   ├── bonds/
   │   └── tsmom.json
   └── futures/
       └── tsmom.json
   ```

4. **Build `tools/strategy_prover.py`** (the 4-gate validation tool)

## Day 5-7: Implement Missing Strategies

5. **Forex Carry Trade** — new strategy, ~100 lines
6. **Bond TSMOM** — new strategy, ~80 lines  
7. **Futures TSMOM** — new strategy, ~80 lines (adapt from the E_Momentum_Persistence backtest)
8. **RSI-2 Forex Adaptation** — adapt existing connors_rsi2.py for forex pairs

## Day 7: Launch the Forward Tester Workflow

9. **Create `strategy-forward-tester.yml`** — single workflow running all paper tests
10. **Create `asset-class-scorecard.yml`** — weekly report on proving status

---

# WHAT SUCCESS LOOKS LIKE

```
ASSET CLASS SCORECARD — Week 8
================================

✅ CRYPTO     | st_fear_greed_contrarian  | PROVEN  | WR 71.2% | n=312 | PF 1.89
✅ EQUITY     | connors_rsi2              | PROVEN  | WR 68.4% | n=47  | PF 1.72
✅ COMMODITY  | triple_confirmation_gold  | PROVEN  | WR 65.8% | n=34  | PF 1.54
✅ ETF        | supertrend_vwma_sectors   | PROVEN  | WR 63.1% | n=31  | PF 1.41
🟡 FOREX     | carry_trade               | TESTING | WR 57.2% | n=22  | PF 1.28
🟡 FUTURES   | tsmom                     | TESTING | WR 59.5% | n=25  | PF 1.35
🟡 BONDS     | tsmom                     | TESTING | WR 55.0% | n=14  | PF 1.15

Proven: 4/7 asset classes
Testing: 3/7 (on track for Week 12-16)
```

**The difference from today**: Instead of 100 strategies at 43% aggregate WR with -1.53% expectancy, you'd have 7-10 validated strategies at 60%+ WR with positive expectancy in every asset class. Fewer trades, all with proven edge, each with a clear statistical proof that anyone can audit.

---

## Review feedback — Cursor agent (2026-04-19)

1. **Stale “PROVEN” example:** The scorecard block listing **`st_fear_greed_contrarian`** at high WR is **superseded** by 2026-04-19 reconciliation (dashboard vs `closed_picks` splits). Update the exemplar to a strategy with **current** verified stats or mark the block “illustrative only.”
2. **Align gates:** The 4-gate diagram should reference **Strategy Factory v1.1** naming (S0–S6) so operators don’t maintain two mental models — add a mapping table Gate1↔S1, etc.
3. **Forex row:** “F_SHORT_Only_Contrarian n=13” conflicts with later **forex rehab** narrative in 2026-04-19 summaries — refresh forex chapter after `kimi_signal_tracking` isolation fix is confirmed.
4. **Discovery:** Use [STRATEGY_DISCOVERY_PROTOCOL.md](STRATEGY_DISCOVERY_PROTOCOL.md) for new per-class hypotheses; this masterplan is the **coverage target**, not the research method.
5. **Bonds / futures:** Keep “data desert” language consistent with [STRATEGY_SUMMARY_BY_ASSET_CLASS_2026_04_19.md](STRATEGY_SUMMARY_BY_ASSET_CLASS_2026_04_19.md) — small n means **no promotion**, not “build more untested strategies.”
