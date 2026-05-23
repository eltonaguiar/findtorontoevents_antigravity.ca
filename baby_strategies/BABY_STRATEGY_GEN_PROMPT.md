# Baby Strategy + Bundle Generation Prompt

Give this prompt to any AI (Claude, GPT, Gemini, Grok) to generate properly validated baby strategies.

---

## Prompt

```
You are designing a quantitative trading strategy for a crypto/equity/forex forward-testing system.
DO NOT ask clarifying questions — all specifications are provided below. Just build the strategy.

PLATFORM & LANGUAGE:
- Python 3.14, pandas, numpy — no external trading platforms (not QuantConnect, not MetaTrader)
- Data: yfinance for daily OHLCV, Binance API for 1h/4h crypto candles
- Execution: Paper trading via GitHub Actions (automated every 30 min)
- No live broker integration — all signals are tracked as paper trades with entry/TP/SL

ASSET COVERAGE:
- PRIMARY: Crypto (BTC, ETH, SOL, BNB, ADA, XRP, DOGE, AVAX, LINK, DOT, NEAR, LTC, ATOM, FIL)
- SECONDARY: US Equities (AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA, SPY, QQQ)
- TERTIARY: Forex (EURUSD, GBPUSD, USDJPY, AUDUSD)
- Strategy MUST work on 3+ asset classes to prove it's not curve-fitted to one market

DATA SOURCES:
- yfinance: `yf.download("BTC-USD", period="5y", interval="1d")` for backtesting
- Binance: `requests.get("https://api.binance.com/api/v3/klines", params={...})` for live scanning
- No paid APIs required at signal time — OHLCV only
- External data (Fear & Greed, funding rates, on-chain) is OK for context but NOT for entry signals

STRATEGY TYPE PREFERENCES (based on what actually works in our system):
- STRONGLY PREFER: Mean reversion (our top 5 survivors are ALL mean reversion)
- ACCEPTABLE: Volatility breakout, momentum crash recovery, statistical arbitrage
- AVOID: Pure trend-following (42% WR in our tests), calendar/seasonality, dominance rotation
- AVOID: Anything requiring real-time order book, Level 2, or tick data

TARGET METRICS:
- Win Rate: > 55% (our best is 68.4%)
- Sharpe Ratio: > 0.5 (our best is 1.17)
- Profit Factor: > 1.2 (our best is 6.25 but that's low-trade-count)
- Trades: > 30 per 5yr backtest across 24 symbols (our best generates 895)
- p-value: < 0.05 (binomial test vs 50% null hypothesis)

CONTEXT:
- Each strategy must output: entry_price, take_profit, stop_loss, side (LONG/SHORT), symbol
- Strategies are paper-traded for 100+ trades before going live
- We use ATR-based TP/SL (e.g., TP = 3x ATR, SL = 2x ATR)
- Strategies run on 1h/4h/1D candles

VALIDATION REQUIREMENTS (all 8 must pass):
1. min_trades >= 30 (across 5yr backtest on 24 symbols)
2. win_rate > 50%
3. p_value < 0.05 (binomial test vs 50% null)
4. profit_factor > 1.2
5. out_of_sample profitable (train on first 60%, test on last 40%)
6. multi_asset: profitable on 3+ different symbols
7. regime_robust: profitable in 2+ market regimes (bull/bear/sideways)
8. consistency: both halves of the data are profitable

PROVEN WINNERS (for reference — these passed all 8 checks):
- Connors RSI-2: RSI(2)<5 + Close>200SMA -> LONG, exit RSI(2)>65. 895 trades, 68.4% WR, Sharpe 1.17, PF 1.53
- VWAP Mean Reversion: Z-score < -2.0 vs 20d VWAP -> LONG, exit z=0. 732 trades, 64.3% WR, Sharpe 0.53, PF 1.37
- MACD Divergence: Price lower low + MACD histogram higher low -> LONG. 515 trades, 67.8% WR, Sharpe 0.57, PF 1.42
- Bollinger Mean Reversion: Touch lower BB(20,2) + price>90% of 200SMA -> LONG. 361 trades, 60.7% WR, Sharpe 0.72, PF 1.53
- RSI Extreme Reversal: RSI(14)<25 + Close>200SMA -> LONG, exit RSI(14)>70. 118 trades, 58.5% WR, Sharpe 0.70, PF 1.68

STRATEGIES THAT FAILED (avoid these patterns):
- EMA crossover trend following: 42.3% WR, inconsistent across regimes
- Smart Money / ICT Fair Value Gaps: 0% WR on 9 trades, -$928
- Cross-sectional momentum (top-N ranking): 0% WR, -$612
- Monthly seasonality / Halloween effect: calendar-based, no edge
- BTC dominance rotation: 0% WR, unreliable signal
- Price level magnetism: 89% WR but NEGATIVE PnL (tiny TP, huge SL = fake wins)
- Exchange netflow reversal: 0% WR, requires unreliable API data
- Break of structure (ICT BOS/CHOCH): 0% WR, subjective pattern recognition
- Altcoin season rotation: 0% WR, timing impossible
- Spike volume explosion: 0% WR, chases pumps too late

KEY LESSONS FROM 32 FAILED STRATEGIES:
1. Mean reversion dominates. Pure trend-following fails in crypto's regime-switching.
2. Beware "high win rate, negative PnL" traps — always check profit factor AND total PnL.
3. Strategies needing external APIs (on-chain, sentiment) fail when APIs go down.
4. Calendar/seasonal strategies have zero edge in 24/7 crypto markets.
5. ICT/Smart Money concepts are untestable and produce 0% WR in systematic form.
6. Any strategy with < 30 trades in 5 years is statistically meaningless.

CURRENT SYSTEM STATUS (Mar 1 2026):
- 124 strategies DISABLED (52 Phase 1 cull + 72 Phase 2 GRAVEYARD)
- 13 strategies SURVIVED Kelly Criterion audit with positive EV (see STRATEGY_GRAVEYARD.md)
- ALL top survivors are mean-reversion — we need diversification but NOT at the cost of quality
- The bar is HIGH. Only statistically proven strategies survive here.

GRAVEYARD SYSTEM (NEW — Mar 1 2026):
- Strategies with negative Kelly Criterion (negative expected value) are flagged as "graveyard"
- They remain in the codebase for reference but NEVER generate live picks
- Before creating any new strategy, CHECK `baby_strategies/STRATEGY_GRAVEYARD.md` for failed patterns
- See `stabilization/disabled_strategies.json` → `graveyard` array for the full list
- Key failed patterns to AVOID: order flow from OHLCV, delta divergence, complex regime detection (HMM/GARCH), vol expansion index, proxy decoupling, dynamic risk heat
- ANY new strategy must pass Kelly Criterion test after 10+ forward trades or it gets graveyarded

TASK:
1. Research and propose ONE new strategy with:
   - Academic or practitioner source (paper, book, or documented trader)
   - Clear entry/exit rules (no ambiguity — another programmer must be able to implement from your description alone)
   - Why it should work (market microstructure reason, not just "it backtested well")
   - Which asset classes it suits (must work on crypto + at least one of equity/forex)
   - Expected win rate and trade frequency
   - Max 3 tunable parameters (fewer is better)
   - What makes it DIFFERENT from our 5 existing survivors (don't just re-skin RSI or Bollinger)

2. Write a COMPLETE Python class implementing it (not pseudocode, not skeleton):

   import pandas as pd
   import numpy as np

   class YourStrategyNameStrategy:
       NAME = "your_strategy_name"
       DESCRIPTION = "One-line description"
       ENTRY_RULES = "Clear entry rules"
       EXIT_RULES = "Clear exit rules"
       ACADEMIC_SOURCE = "Author Year, Paper/Book title"
       EXPECTED_WR = "XX-YY%"
       EXPECTED_TRADES_PER_YEAR = "N per symbol"

       def __init__(self, tp_atr_mult=3.0, sl_atr_mult=2.0, max_hold_days=15):
           self.tp_atr_mult = tp_atr_mult
           self.sl_atr_mult = sl_atr_mult
           self.max_hold_days = max_hold_days

       def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
           """Add all required indicators to dataframe."""
           # MUST compute: ATR(14) at minimum for TP/SL
           # Add your strategy-specific indicators here
           return df

       def generate_signals(self, df: pd.DataFrame, symbol: str = "BTCUSDT") -> list[dict]:
           """
           Args:
               df: DataFrame with columns [open, high, low, close, volume], indexed by datetime
               symbol: Trading pair name (e.g., "BTCUSDT", "AAPL", "EURUSD")
           Returns:
               List of signal dicts, each with keys:
               {symbol, side, entry_price, take_profit, stop_loss, strength, reason, strategy}
           """
           df = self.compute_indicators(df.copy())
           signals = []

           for i in range(200, len(df)):  # Skip warmup period
               row = df.iloc[i]
               prev = df.iloc[i-1]
               close = row["close"]
               atr = row["atr_14"]

               # YOUR ENTRY LOGIC HERE
               # if entry_condition:
               #     signals.append({
               #         "symbol": symbol,
               #         "side": "LONG",
               #         "entry_price": close,
               #         "take_profit": close + atr * self.tp_atr_mult,
               #         "stop_loss": close - atr * self.sl_atr_mult,
               #         "strength": 65,  # 0-100 confidence
               #         "reason": f"Indicator=value, threshold=X",
               #         "strategy": self.NAME,
               #         "max_hold_days": self.max_hold_days,
               #     })

           return signals

3. Propose a BUNDLE of 3-5 strategies that complement each other:
   - Mix of mean-reversion + ONE non-mean-reversion (volatility or momentum-crash)
   - Different entry triggers (avoid: "3 strategies that all use RSI")
   - Different timeframe sensitivities (some work on 1D, some on 4h)
   - Combined expected Sharpe > 1.0
   - Explain WHY these strategies are uncorrelated (mathematically, not just "they use different indicators")
   - Include our existing survivors where appropriate — don't reinvent what works

4. Provide a simple backtest snippet to validate:

   # Quick validation (not the full 8-check suite, just a sanity check)
   import yfinance as yf
   df = yf.download("BTC-USD", period="5y", interval="1d")
   strategy = YourStrategyNameStrategy()
   signals = strategy.generate_signals(df, "BTCUSDT")
   print(f"Total signals: {len(signals)}")
   print(f"Long: {sum(1 for s in signals if s['side']=='LONG')}")
   print(f"Short: {sum(1 for s in signals if s['side']=='SHORT')}")
   # Expected: 30+ signals over 5 years for BTC alone

CONSTRAINTS:
- NO strategies that only work in bull markets (must handle bear + sideways)
- NO strategies requiring external APIs at signal time (OHLCV only)
- NO parameter overfitting (max 3 tunable parameters per strategy — NOT 7, NOT 5, exactly 3 or fewer)
- Prefer strategies with 100+ backtested trades over 5 years
- MUST include max hold period (10-20 day exit if no TP/SL hit)
- TP/SL must be ATR-based, not fixed percentages
- Strategy name must be snake_case, class name PascalCase + "Strategy" suffix
- Code must be COMPLETE and RUNNABLE — not pseudocode or skeleton
- Use only standard libraries + pandas + numpy (no ta-lib, no backtrader, no custom packages)

ABSOLUTELY FORBIDDEN — INSTANT REJECTION:
- DO NOT hardcode fake backtest results. No "simulated_results = {win_rate: 0.62, sharpe: 0.89}".
  If you haven't run a real backtest, say "NEEDS BACKTEST" — do NOT invent numbers.
- DO NOT re-skin existing strategies. We already have Connors RSI-2, VWAP Mean Reversion,
  MACD Divergence, Bollinger Mean Reversion, and RSI Extreme Reversal. Your strategy must use
  a DIFFERENT primary signal — not RSI, not Bollinger, not MACD, not VWAP z-score.
- DO NOT copy our existing survivors and rename them. We need NEW edges, not duplicates.
- DO NOT use deprecated pandas methods (e.g., df.append() was removed in pandas 2.0).
- DO NOT submit code with typos or bugs. Test your code mentally — if self.max_hold_hold_days
  has a double "hold", you failed. We WILL run your code and it MUST not crash.
- DO NOT use more than 3 tunable parameters. If your __init__ has 7 arguments, you failed.
  ATR period (14) and max_hold_days (15) are FIXED — they don't count as tunable but must
  not be changed. Your 3 parameters are for your strategy's unique logic only.

WHY THIS MATTERS:
We just purged 32 strategies and $1,500+ in losses from fake/unvalidated signals.
Mercury 2 showed +7.12% unrealized while hiding -30.49% realized losses.
Hardcoded fake results are HOW systems lie to themselves. We will ONLY trust
numbers that come from survivor_backtest.py running on real yfinance data.

OUTPUT FORMAT:
1. Strategy research summary (200 words max)
2. Complete Python file (ready to save as baby_strategies/your_strategy_name.py)
3. Bundle proposal with correlation analysis
4. Quick backtest validation snippet — this MUST actually run and print REAL signal counts,
   not hardcoded numbers. The snippet downloads real data and runs your generate_signals().
```

---

## How to Use

1. Copy the prompt above (everything between the ``` markers) and give it to any AI
2. Save the generated `.py` file in `baby_strategies/`
3. Register in `incubator/backtest_team/forward_signal_scanner.py` under `TIER1_STRATEGIES`
4. Run backtest: `py alpha_engine/survivor_backtest.py` to validate against 8 anti-overfit checks
5. If it passes all 8 checks, add to a bundle in `battleground/data/bundle_babies.db`
6. Forward test for 100+ paper trades before considering for live signals
7. Strategy must maintain > 50% WR and positive PnL through forward testing to stay active

---

## Strategy DNA System (Added Mar 2 2026)

Beyond manual strategy creation, our system now includes an **automated Strategy DNA Engine** that evolves, optimizes, and stress-tests strategy combinations. New strategies created via this prompt feed into the DNA pipeline automatically.

### How the DNA System Works

Every strategy combination is encoded as a **biological genome** with 5 chromosome groups:

| Chromosome Group | Genes | Purpose |
|---|---|---|
| `entry_genes` | 8 indicator types (consensus, weighted_vote, cascade, reversal_confirm, momentum_filter, volume_confirm, divergence_check, regime_filter) | When to enter a trade |
| `exit_genes` | 5 types (fixed_tp_sl, trailing_stop, time_exit, signal_exit, volatility_exit) | When to exit a trade |
| `risk_genes` | Position sizing, max drawdown tolerance, correlation limits | Risk management |
| `meta_genes` | Regime sensitivity, decay factor, confidence threshold | Adaptive behavior |
| `dna_hash` | MD5 fingerprint | Unique genome identifier |

### DNA Pipeline (Automated)

```
Baby Strategy Created (this prompt)
    ↓
Backtest Validation (8 anti-overfit checks)
    ↓
Signal Recorder (signal_log.db — tracks all picks + outcomes)
    ↓
Permutation Engine (generates 2-4 way strategy combos)
    ↓
Strategy DNA Evolution (50 generations × 100 population)
    ↓  - Tournament selection (best of N random)
    ↓  - Uniform crossover (gene-level blending of parents)
    ↓  - Regime-aware mutation (volatile→tighten risk, trending→extend lookbacks)
    ↓
PSO Swarm Optimization (10-dimension particle swarm)
    ↓  - Market-adaptive inertia (0.4 low vol → 0.9 high vol)
    ↓  - Softmax-normalized combo weights
    ↓
Nightmare Stress Tests (must survive 4/5 scenarios)
    ↓  - Flash Crash, Infinite Pump, Correlation One
    ↓  - Liquidity Void, Regime Flipper
    ↓
Meta-Label Filter (Lopez de Prado ML veto)
    ↓  - GBM classifier vetoes low-probability trades
    ↓  - 16 features, deploys if accuracy > 52%
    ↓
Autopoietic Self-Repair Monitor
    ↓  - Detects: Sharpe collapse, herding, freeze-up, chattering, drawdown spiral
    ↓  - Auto-repairs: probation, resurrection, threshold adjustment
    ↓
EXECUTE (only signals surviving all gates)
```

### Key DNA Files

| File | Purpose |
|---|---|
| `meta_strategy/strategy_genome.py` | DNA variation generator — encodes, crossovers, mutates, evolves genomes |
| `meta_strategy/swarm_consensus.py` | PSO swarm optimizer — 10-dim particle swarm for combo weights |
| `meta_strategy/stress_test.py` | Nightmare stress tester — 5 GBM synthetic market scenarios |
| `meta_strategy/meta_label_filter.py` | Meta-label ML filter — Lopez de Prado trade veto system |
| `meta_strategy/autopoietic_monitor.py` | Self-repair monitor — detects and fixes 5 anomaly types |
| `meta_strategy/permutation_engine.py` | Combo generator — all 2-4 way strategy permutations |
| `meta_strategy/data/evolved_genomes.json` | Output — top 50 evolved genomes |
| `meta_strategy/data/swarm_weights.json` | Output — optimized combo weights |
| `meta_strategy/data/stress_test_results.json` | Output — nightmare survival results |

### How New Strategies Enter the DNA System

1. You create a baby strategy using this prompt
2. It passes the 8-check backtest validation
3. It starts generating signals → recorded to `signal_log.db`
4. The permutation engine automatically includes it in combo generation
5. The DNA evolution engine breeds it with other strategies
6. Winning combinations survive stress tests and meta-label filtering
7. The best combos are displayed on the Battleground dashboard with their DNA hash

## Current Survivors (Feb 28 2026)

| Strategy | Trades | WR | Sharpe | PF | p-value | Status |
|---|---|---|---|---|---|---|
| Connors RSI-2 | 895 | 68.4% | 1.17 | 1.53 | 0.000000 | TIER_1_PROVEN |
| VWAP Mean Reversion | 732 | 64.3% | 0.53 | 1.37 | 0.000000 | TIER_1_PROVEN |
| MACD Divergence | 515 | 67.8% | 0.57 | 1.42 | 0.000000 | TIER_1_PROVEN |
| Bollinger Mean Rev | 361 | 60.7% | 0.72 | 1.53 | 0.00003 | TIER_1_PROVEN |
| RSI Extreme Reversal | 118 | 58.5% | 0.70 | 1.68 | 0.040 | TIER_2_PROVEN |
| Supertrend | 34 | 52.9% | 1.18 | 6.25 | 0.432 | TIER_3_WATCH |

## TIER_2 Forward-Test Winners (small sample, profitable in live)

| Strategy | WR | PnL | Trades | Direction |
|---|---|---|---|---|
| autocorrelation_exploiter | 83% | +$1,459 | 6 | SELL only |
| hurst_regime_adaptive | 71% | +$854 | 7 | BUY only |
| volume_profile_value_area | 80% | +$887 | 5 | SELL only |
| multi_sigma_reversal | 100% | +$656 | 3 | SELL only |
| fear_greed_extreme_dca | 100% | +$360 | 3 | BUY only |

## Eliminated (32 strategies) — See `stabilization/disabled_strategies.json`

## System Reality Check (Feb 28 2026)

| System | Advertised | Reality |
|---|---|---|
| Mercury 2 | +7.12% unrealized | -30.49% realized, 27% WR, Sharpe -4.48 |
| Alpha Engine | +0.92% unrealized | 10 of 21 picks from DISABLED strategies |
| Crypto ML Edge | -14.90% | 0% WR, at least honest about losses |

The bar is high. Don't propose anything that wouldn't survive our 8-check validation.
