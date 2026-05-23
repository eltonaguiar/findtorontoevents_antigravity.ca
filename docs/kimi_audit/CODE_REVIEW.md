# Kimi Agent "Proven Crypto/Forex Strategies" - Code Audit

**Date:** 2026-03-16
**Reviewer:** Claude Code (automated audit)
**Files reviewed:**
- `trading_strategies_implementation.py` (345 lines)
- `proven_trading_strategies_report.md` (353 lines)
- `proven_trading_strategies_report.json` (386 lines)

---

## VERDICT: Tutorial-grade garbage. Google AG was right.

This is exactly the "copy-paste sklearn tutorial" pattern that was warned about.
Nothing here is production-quality. Nothing here is novel. Nothing here is
salvageable for alpha_engine/ without a complete rewrite that would be faster
to write from scratch.

---

## Python Code Assessment

### Is it production-quality or tutorial-level?

**Tutorial-level.** Specifically:

1. **No real data anywhere.** The only runnable code (`run_example_backtest()`)
   generates fake trending data with `np.random.seed(42)` and a linear trend
   from 100 to 150. Any strategy will "profit" on a straight line up. This is
   not a backtest -- it is a demo that proves nothing.

2. **No slippage modeling.** Entries and exits use `close` price directly. In
   crypto, slippage on a 15M candle can be 0.1-0.5% depending on liquidity.
   This is not accounted for.

3. **No commission/fee modeling.** Zero transaction costs. On Binance taker
   fees alone (0.1%), a strategy generating 100+ trades would lose 10%+ of
   capital to fees. Not modeled.

4. **Broken position sizing.** Line 67:
   `position_size = (capital * risk_per_trade) / (entry_price * 0.02)`
   This hardcodes a 2% stop distance regardless of actual stop placement.
   The strategies themselves have no stop loss logic -- the backtest engine
   just uses an arbitrary divisor.

5. **No walk-forward or OOS testing.** The report TALKS about walk-forward
   analysis and Monte Carlo simulation in the methodology section, but the
   code implements exactly NONE of it. Zero. The backtest is a single
   in-sample pass on fake data.

6. **ADX calculation is wrong.** The `EMAPullbackStrategy` calculates ADX
   using a simplified method that does not properly handle the directional
   movement signs. `plus_dm` and `minus_dm` use raw `.diff()` without the
   conditional logic (plus_dm is positive only when high diff > low diff AND
   high diff > 0; similar for minus_dm). This produces incorrect ADX values.

7. **VWAP is cumulative from start of data.** The `VWAPBounceStrategy`
   calculates VWAP as a cumulative sum from the beginning of the dataset,
   which is only correct for intraday VWAP reset daily. On multi-day data
   this produces a meaningless number.

8. **Long-only backtester pretending to be long/short.** The backtest engine
   only tracks `position > 0`. Sell signals only exit longs -- there is no
   short-selling logic despite the strategies generating short signals.

### Any functions we could adapt into alpha_engine/?

**No.** Our alpha_engine already has:
- 158 Python files with 100+ strategies
- Proper backtesting with slippage and fees (backtest_*.py files)
- Real API data from Binance, CoinGecko, FRED, blockchain.info
- Walk-forward validation (auto_tuner.py)
- Signal tracking with real price validation (signal_tracker)

The three strategies implemented here (Hoffman EMA, VWAP Bounce, EMA Pullback)
are all subsets of strategies we already have:
- `multi_timeframe_ema_stack` covers the EMA alignment concept
- `vwap_bounce` (if we had one) is trivially implementable
- `ema_pullback` with ADX is already in our `advanced_strategies.py`

### Does it handle risk management?

Only superficially. The `risk_per_trade=0.02` parameter exists but the actual
position sizing math is broken (see point 4 above). There is no:
- Portfolio-level risk limits
- Correlation-aware sizing
- Dynamic position sizing based on volatility
- Maximum concurrent positions
- Drawdown circuit breakers

---

## Strategy Report Assessment

### Are the claimed win rates backed by data or aspirational?

**Aspirational.** Red flags:

1. **"62% win rate, 206% return on 100 trades"** (Hoffman) -- The source is
   listed as "Binance Square / TradingView community." This means someone
   posted it on social media. No verifiable trade log, no audited track record,
   no third-party validation. 206% return at 2% risk per trade with 62% WR
   requires an average win/loss ratio that does not match the stated 1:1.5 R/R.

2. **"65-70% win rate"** (VWAP Bounce) -- Validation listed as "Prop firm
   verified, used by institutional traders." Which prop firm? Which traders?
   No names, no links, no data. This is marketing language.

3. **"70-75% win rate"** (Stat Arb) -- Listed as "Institutional-grade,
   academic research validated." Which papers? No citations. Real pairs
   trading papers (Gatev et al. 2006, Krauss 2017) report much more modest
   returns with significant drawdowns since 2009.

4. **All win rates are given as ranges** (e.g., "55-65%") with no specific
   dataset, time period, or sample size. This is a hallmark of AI-generated
   content that wants to sound authoritative without committing to verifiable
   numbers.

5. **The one strategy with specific numbers** (VWAP+RSI(2): 254 trades on
   SPY 1H, 45.67% WR, PF 1.692) is actually the most honest entry -- and
   notably has the LOWEST win rate. The specificity suggests this one may
   have been tested. The rest are hand-waving.

### Do any strategies have genuinely new approaches?

**No.** Every strategy listed is well-known and already covered in our system:

| Kimi Strategy | Alpha Engine Equivalent |
|---|---|
| Hoffman EMA (3/5/18) | `multi_timeframe_ema_stack` (9/21/50/200) |
| VWAP Bounce | `vwap` concepts in scanner |
| EMA Pullback + ADX | `atr_volatility_breakout`, `advanced_strategies` |
| Stat Arb Pairs | `cross_sectional_momentum` |
| Supply/Demand Zones | `break_of_structure`, `swing_failure_pattern` |
| BB Squeeze | TTM Squeeze strategy (already implemented) |
| RSI + MACD | `rsi_macd_confluence` (Elder Triple Screen) |
| London Breakout | `london_breakout` in forex_strategies.py |

### Cross-reference with Google AG's warning

Google AG warned about "copy-paste sklearn tutorials." This is EXACTLY that
pattern, minus the sklearn (since there is no ML here at all despite the
report mentioning Monte Carlo and walk-forward analysis):

1. Generic base class with `calculate_indicators()` / `generate_signals()` --
   textbook OOP pattern from every "build a trading bot in Python" tutorial.
2. Fake data backtest that proves nothing.
3. Emoji-heavy markdown report with confident claims and zero evidence.
4. Strategy descriptions that read like they were summarized from Reddit posts
   (because they were -- the sources literally cite r/Daytrading).
5. JSON "data" file that is just the markdown content reformatted, not actual
   backtest results or trade logs.

---

## Summary

| Aspect | Rating | Notes |
|---|---|---|
| Code quality | 2/10 | Runs but proves nothing |
| Backtest rigor | 1/10 | Fake data, no fees, no slippage, no OOS |
| Strategy novelty | 0/10 | All covered in alpha_engine already |
| Statistical claims | 2/10 | Ranges without evidence |
| Adaptability | 0/10 | Faster to write from scratch |
| Overall | 1/10 | Tutorial-grade, no production value |

**Recommendation:** Archive for reference only. Do not integrate any code.
The alpha_engine is already far beyond what this provides.
