# Testing Patterns

**Analysis Date:** 2025-02-23

## Test Framework

**Runner:**
- No pytest or unittest framework detected
- Tests are manual Python scripts executed directly: `python test_*.py`
- No test discovery or CI-integrated test runner

**Assertion Library:**
- Standard Python `assert` statements used for validation
- Example from `test_data_validator.py` (line 47): `assert agent.config.monitoring_interval_seconds == 5`
- No assertion library (no pytest, no unittest.TestCase)

**Run Commands:**
```bash
python test_agent.py                    # Run AB testing agent tests
python test_data_validator.py           # Run data validator tests
python test_model_health_agent.py       # Run model health tests
python test_risk_quantification.py      # Run risk quantification tests

# Battle tests (live/historical validation)
python battle_test.py                   # Walk-forward validation across all assets
python battle_test_rigorous.py          # Extended rigorous backtests
python battle_test_real_time.py         # Real-time market validation

# Backtesting specific strategies
python backtest_individual_changes.py   # Isolated strategy testing
python backtest_kimi_claw.py            # KIMI v1.1 validation
python simpleton_backtester.py          # Simpleton v0.01_Claude strategy validation
```

## Test File Organization

**Location:**
- Test files co-located with source in root or module directories
- Example: `ab_testing_agent/test_agent.py` tests `ab_testing_agent/ab_testing_agent.py`
- Battle tests in KIMI_RISEOFTHECLAW/, alpha_engine/, etc.
- No separate `tests/` directory

**Naming:**
- Prefix pattern: `test_*.py` for unit-like tests
- Suffix pattern: `*_test.py` less common
- Battle test pattern: `battle_test.py`, `battle_test_rigorous.py`
- Backtest pattern: `backtest_*.py` (actually validation/integration tests)

**Structure:**
```
ab_testing_agent/
├── ab_testing_agent.py         # Source module
├── test_agent.py               # Test script
├── config.py                   # Config
├── database.py                 # Database
└── statistics.py               # Statistics
```

## Test Structure

**Suite Organization:**
```python
# Pattern from test_agent.py (lines 13-89)

def test_statistical_analyzer():
    """Test statistical calculations"""
    print("Testing Statistical Analyzer...")

    analyzer = StatisticalAnalyzer()

    # Test 1: sample size calculation
    sample_size = analyzer.calculate_sample_size(0.1)
    print(f"Required sample size for 10% effect: {sample_size}")

    # Test 2: t-test
    group_a = [1.2, 1.1, 1.3, 1.0, 1.4]
    group_b = [1.0, 0.9, 1.1, 0.8, 1.2]
    results = analyzer.perform_t_test(group_a, group_b)
    print(f"T-test p-value: {results['p_value']:.4f}")
    print(f"Significant: {results['significant']}")

    print("✓ Statistical Analyzer tests passed\n")

def main():
    """Run all tests"""
    print("Running A/B Testing Agent Tests\n")
    print("=" * 50)

    try:
        test_statistical_analyzer()
        test_agent_creation()
        test_quick_experiment()

        print("=" * 50)
        print("🎉 All tests passed!")
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
```

**Patterns:**
- Setup: Direct object instantiation with test data
- Test: Method call with assertions or print output
- Teardown: Not explicitly used (implicit via exception handling)
- Grouping: Functions test single concerns (one analyzer, one component)

## Mocking

**Framework:** Not used

**Approach in Battle Tests:**
- Data fetched from yfinance live (no mocking)
- Historical data used as realistic test data
- Example from `battle_test.py` (lines 50-80):
  ```python
  def fetch_historical_data(symbols: list[str], period: str = "1y") -> dict[str, pd.DataFrame]:
      """Fetch full historical OHLCV for all symbols."""
      data = {}
      tickers = " ".join(symbols)

      try:
          raw = yf.download(tickers, period=period, interval="1d",
                            group_by="ticker", auto_adjust=True,
                            threads=True, progress=False)
      except Exception as e:
          print(f"  FATAL: yfinance download failed: {e}")
          return data

      for symbol in symbols:
          try:
              if len(symbols) == 1:
                  df = raw
              else:
                  df = raw[symbol] if symbol in raw.columns.get_level_values(0) else None
              if df is None or df.empty:
                  continue
              df = df.dropna(subset=["Close"])
              if len(df) < 50:
                  continue
              data[symbol] = df
          except Exception:
              continue
  ```

**What to Mock:**
- Nothing — live data sources preferred for realistic signal validation
- Tests designed to catch real market conditions, not sanitized scenarios

**What NOT to Mock:**
- Market data: Use actual yfinance/Binance feeds
- Signal indicators: Implement actual formulas (RSI, EMA, MACD, etc.)
- Asset prices: Walk-forward tests validate against real OHLCV

## Fixtures and Test Data

**Test Data:**
- Hardcoded in test files: See `test_data_validator.py` (lines 32-39)
  ```python
  config = DataValidatorConfig(
      primary_sources={
          'BTC': [DataSource.BINANCE, DataSource.COINGECKO],
          'ETH': [DataSource.BINANCE, DataSource.CRYPTOCOMPARE],
      },
      monitoring_interval_seconds=5,
      max_staleness_seconds=30,
  )
  ```
- Symbol lists hardcoded in test files or imported from config
- Historical data fetched on-demand from yfinance

**Location:**
- Fixtures not centralized
- Each test file defines its own test data
- Backtest files define asset symbol lists inline (see battle_test.py lines 30-60)

## Coverage

**Requirements:** Not enforced

**View Coverage:**
- No coverage tools detected (no `.coverage`, no pytest-cov)
- Manual validation of strategy coverage via battle tests

## Test Types

**Unit Tests:**
- Scope: Individual functions or components (StatisticalAnalyzer, Config loading)
- Approach: Create object, call method, assert result
- Example: `test_statistical_analyzer()` in test_agent.py (lines 13-35)
- Coverage: Component-level functionality

**Integration Tests:**
- Scope: Agent initialization + component interaction
- Approach: Create agent, call multiple methods, assert state
- Example: `test_agent_creation()` in test_agent.py (lines 37-76)
- Coverage: How components interact

**Validation Tests (Battle Tests):**
- Scope: Strategy signals against real historical data
- Approach: Walk-forward backtesting with realistic market data
- Files: `battle_test.py`, `battle_test_rigorous.py`, `backtest_*.py`
- Coverage: Historical performance across all assets
- Example flow:
  1. Fetch 6-12 months historical data for symbols
  2. Split: first 4 months training, last 2 months validation
  3. Generate signals daily using only past data
  4. Validate against future OHLCV (no lookahead)
  5. Record win rate, Sharpe, drawdown, etc.

**E2E Tests:**
- Scope: Live market scanning + signal generation
- Files: `live_test_now.py`, `unified_forward_test.py`
- Approach: Run scanner against current market, compare signals to benchmarks
- Not used for CI/CD, manual validation only

## Common Patterns

**Async Testing:**
- Used in `test_data_validator.py` (lines 23+)
  ```python
  async def test_data_validator_agent():
      """Test the Data Validator Agent functionality"""
      agent = DataValidatorAgent(redis_url, db_url, config)

      try:
          # Test 1: Agent initialization
          assert agent.config.monitoring_interval_seconds == 5

          # Test 2: Start agent
          await agent.start()
          await asyncio.sleep(2)

          # Test 3: Feed health checking
          await asyncio.sleep(10)
          feeds_checked = 0
          # ... verification
          assert feeds_checked > 0, "No feeds were successfully checked"
      finally:
          await agent.stop()
  ```
- Pattern: Create agent, await startup, await operations, verify state, cleanup

**Error Testing:**
- Broad exception catching with traceback output
  ```python
  try:
      test_statistical_analyzer()
      test_agent_creation()
  except Exception as e:
      print(f"❌ Test failed: {str(e)}")
      import traceback
      traceback.print_exc()
      sys.exit(1)
  ```

**Backtest Signal Validation:**
```python
# Walk-forward validation pattern from battle_test.py
def backtest_strategy(symbol: str, strategy_func, data: pd.DataFrame):
    """
    For each day in test period:
      1. Calculate signals using ONLY past data (no lookahead)
      2. Record entry price, TP, SL
      3. Walk forward checking if TP/SL hit using real OHLCV
      4. Record outcome (WIN/LOSS/EXPIRED)
    """
    trades = []
    for i in range(lookback_period, len(data)):
        # Get data up to this point (no future data)
        past_data = data.iloc[:i+1]

        # Generate signal
        signal = strategy_func(past_data)

        if signal:
            entry_price = data.iloc[i]['Close']
            # Track position forward until TP/SL hit
            for j in range(i+1, min(i+max_hold_days, len(data))):
                high = data.iloc[j]['High']
                low = data.iloc[j]['Low']

                if high >= take_profit_price:
                    # Winner
                    trades.append({'outcome': 'WIN', ...})
                    break
                elif low <= stop_loss_price:
                    # Loser
                    trades.append({'outcome': 'LOSS', ...})
                    break

    return calculate_metrics(trades)
```

## Test Execution Patterns

**Manual Test Command:**
```bash
$ python test_agent.py
Running A/B Testing Agent Tests

==================================================
Testing Statistical Analyzer...
Required sample size for 10% effect: 385
T-test p-value: 0.0234
Significant: True
✓ Statistical Analyzer tests passed

Testing Agent Creation...
Created experiment with ID: exp_001
Started experiment: True
Recorded test observations
Analysis status: running
✓ Agent creation tests passed

==================================================
🎉 All tests passed! A/B Testing Agent is ready to use.
```

**Backtest Output:**
- JSON files with metrics: win rate, Sharpe, max drawdown, trades
- Console output with progress indicators
- Results files: `data/alpha_picks.json`, `data/battle_results.json`

## Known Testing Gaps

- **No CI/CD test automation:** Tests run manually or via GitHub Actions scripts
- **No test framework:** Manual assertion approach vs pytest/unittest
- **No code coverage tracking:** Coverage verified manually via walk-forward results
- **Limited unit testing:** Focus on integration/validation tests
- **No mocking:** All tests use live data sources (realistic but slower)

---

*Testing analysis: 2025-02-23*
