# Coding Conventions

**Analysis Date:** 2025-02-23

## Naming Patterns

**Files:**
- Module files use `snake_case`: `battle_test.py`, `connors_rsi2.py`, `crypto_acceleration_engine.py`
- Test files use prefixes: `test_*.py` (e.g., `test_agent.py`, `test_data_validator.py`)
- Config files: `config.py`
- Main entry points: `main.py`, `live_scanner.py`

**Functions:**
- Use `snake_case` for all functions: `fetch_historical_data()`, `calculate_sample_size()`, `_setup_logging()`
- Private/helper functions prefixed with single underscore: `_rsi()`, `_atr()`, `_ema()`, `_setup_logging()`
- Indicator functions often unprefixed in signal modules: `rsi()`, `sma()`, `atr()`

**Variables:**
- Use `snake_case` for all variables: `data_dir`, `max_allocation_per_pick`, `btc_feeds`, `monitoring_interval_seconds`
- Constants use `UPPER_SNAKE_CASE`: `STARTING_CAPITAL`, `MAX_RISK_PER_TRADE`, `DATA_DIR`, `EST`, `UTC`
- Dictionary/config keys use `snake_case`: `max_staleness_seconds`, `outlier_threshold_std`, `monitoring_interval_seconds`

**Classes:**
- Use `PascalCase`: `ABTestingAgent`, `ExperimentManager`, `DataValidatorAgent`, `StatisticalAnalyzer`
- Dataclass names use `PascalCase`: `BacktestResult`, `Trade`, `Config`
- Exception classes use `PascalCase`: Standard for Python

**Enums and Constants in Config:**
- Dictionary keys use `snake_case`: See `alpha_engine/config.py` (lines 43-49)
- Tier identifiers: `"major"`, `"alt"`, `"scout"`
- Category labels: `"crypto"`, `"forex"`, `"stock"`, `"meme"`, `"penny"`

## Code Style

**Formatting:**
- No automatic formatter enforced (no `.prettierrc` or `eslintrc` found)
- Indentation: 4 spaces (Python standard)
- Line length: Implicit max ~100-120 chars (based on observations)
- Imports follow alphabetical grouping within standard categories

**Linting:**
- No linting config files detected (no `.eslintrc`, `.pylintrc`, `pyproject.toml` with linting rules)
- Code follows PEP 8 conventions implicitly

## Import Organization

**Order:**
1. Standard library imports (datetime, pathlib, json, sys, os, asyncio)
2. Third-party imports (numpy, pandas, yfinance, flask, sqlalchemy, pydantic)
3. Local/relative imports (from `.config import`, `from .database import`)

**Pattern from `ab_testing_agent.py`:**
```python
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import smtplib
from email.mime.text import MIMEText

from apscheduler.schedulers.background import BackgroundScheduler

try:
    from .database import init_db
    from .experiment_manager import ExperimentManager
except ImportError:
    from database import init_db
    from experiment_manager import ExperimentManager
```

**Path Aliases:**
- Relative imports use try/except fallback pattern (see `ab_testing_agent.py` lines 12-23)
- Allows module to run standalone or as package import

**Type Hints:**
- Used consistently: `Dict`, `List`, `Optional`, `Tuple` from `typing`
- Example: `def fetch_historical_data(symbols: list[str], period: str = "1y") -> dict[str, pd.DataFrame]`
- Function parameters and return types documented with type hints (lines in `battle_test.py` line 50)

## Error Handling

**Patterns:**
- Try/except blocks around external API calls and data fetching
- Broad `except Exception` used in signal/strategy code to prevent cascade failures
- Specific exception catching in critical paths: `except (ValueError, AttributeError, KeyError, TypeError, IndexError)`
- Example pattern from `advanced_strategies.py` (line 798):
  ```python
  try:
      # calculation
  except (KeyError, TypeError, ValueError, IndexError):
      return None
  ```
- Silent failures common in non-critical paths (strategy signal generation)
- Critical system failures logged but execution continues

**Import Error Handling:**
- Optional module imports wrapped in try/except (see `live_scanner.py` lines 42-98)
- Flags like `_HAS_ACCEL`, `_HAS_PROVEN` track module availability
- Graceful degradation when optional signal modules unavailable

## Logging

**Framework:** Python `logging` standard library

**Patterns:**
- Logger instantiated per module: `logger = logging.getLogger(__name__)` (e.g., `ab_testing_agent.py` line 25)
- Configured in setup methods: `_setup_logging()` (line 60-69 in `ab_testing_agent.py`)
- Log levels: DEBUG, INFO, WARNING, ERROR
- File and stream handlers combined (line 66-68 in `ab_testing_agent.py`)
- Log files written to project root or data directories

**Usage in Signals/Backtests:**
- Print statements used for real-time feedback instead of logging in many signal files
- Example: `print(f"Created experiment with ID: {exp_id}")` (test file line 55)
- Success indicators use emoji/symbols: `✓`, `✅`, `❌`, `🎉`

## Comments

**When to Comment:**
- Module-level docstrings at top of file (3-5 line description of purpose)
- Function docstrings explaining parameters and return values
- Inline comments for non-obvious logic (particularly in signal generation)
- Comments cite academic papers and sources for strategy thresholds
- Configuration comments explain "why" values were chosen

**Example from `connors_rsi2.py`:**
```python
"""
CONNORS RSI-2 MEAN REVERSION SYSTEM
=====================================
The most documented short-term retail edge in quantitative finance.

ACADEMIC BACKING:
- Source: "Short Term Trading Strategies That Work" — Larry Connors & Cesar Alvarez (2008)
- Published data: 73-76% WR on SPY from 1993–2008 (15 years, 2,000+ trades)
```

**JSDoc/TSDoc:**
- Not used (Python codebase)
- Docstrings use standard Python triple-quote format

## Function Design

**Size:**
- Most functions 10-50 lines
- Indicator functions very small (5-15 lines)
- Complex strategy functions 30-100 lines
- No artificial length constraints observed

**Parameters:**
- Functions accept dataframes, series, and simple types (float, int, str)
- Optional parameters use default values: `def rsi(close: pd.Series, period: int = 14)`
- Configuration passed via Config objects or dictionaries

**Return Values:**
- Indicator functions return pandas Series or scalar values
- Strategy functions return tuples: `[long_signal, short_signal, strength]` or boolean/dict
- Batch operations return dictionaries keyed by symbol/ticker
- Example from config pattern: Return config dicts with nested structure

## Module Design

**Exports:**
- Modules export functions and classes directly
- Strategy files export signal function dictionaries: `SIGNAL_FUNCS = {"strategy_name": func}`
- Config modules export constants and Config classes

**Barrel Files:**
- No barrel files (`__init__.py` with exports) in most packages
- Relative imports used within packages (e.g., ab_testing_agent)
- Main entry points import specific modules explicitly

**Patterns in Signal Modules:**
- Central dictionary of signal functions keyed by algorithm name
- Example: `CRYPTO_STRATEGIES = {strategy_name: strategy_func_tuple, ...}`
- Decentralized: Each signal file maintains its own registry
- Merged at runtime in orchestrator/scanner files

## Common Patterns

**Configuration:**
- Config class with environment variable loading: `DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///ab_testing.db')`
- Module-level constants in config files (see `alpha_engine/config.py`)
- Nested dictionaries for symbol metadata (lines 62-100 in config.py)

**Data Flow:**
- Fetch data from yfinance/Binance → Process indicators → Generate signals → Record results
- Results written to JSON, SQLite, or CSV files in data directories
- Walk-forward backtests common: train period + test period separation

**Signal Generation:**
- Functions return signal tuples or lists: `[entry_signal, exit_signal, confidence]`
- Confidence/strength represented as 0-100 float or 0-1 ratio
- Multiple strategies run independently, results merged for consensus

**Testing Architecture:**
- Battle tests run all strategies against historical data
- Walk-forward validation: train on early data, validate on future data
- Live tests match signal generation against real market data
- Results aggregated: win rate, sharpe ratio, expectancy, drawdown

---

*Convention analysis: 2025-02-23*
