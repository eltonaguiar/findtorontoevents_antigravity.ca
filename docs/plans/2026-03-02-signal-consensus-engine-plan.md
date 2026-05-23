# Signal Consensus Engine + Combo Backtester — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a unified signal recorder that captures every pick from all 27+ trading systems + social predictions + TradingView technicals, then a combination engine that systematically discovers which signal combos produce statistically significant wins.

**Architecture:** Three layers: (1) Signal Recorder — a lightweight SQLite logger that snapshots every system's active picks every 15 min with live prices, (2) TradingView Technicals integration via `tradingview-ta` library, (3) Combo Backtester — nightly analysis that tests every 2-way and 3-way signal combination for statistical significance, surfacing winning combos to the Hub.

**Tech Stack:** Python 3.11+, SQLite, `tradingview-ta`, `requests`, GitHub Actions, existing `cross_aggregation/` infrastructure.

---

## Current State (Audit Findings)

### Systems Producing Active Picks (27 total)

**In Hub (15):** mercury2, claws_of_doom, alpha_engine, kimi, crypto_ml_edge, claude_gainer, ml_bg_a/b/c/d/e, signal_engine, breakout_a/b/c

**NOT in Hub (12):**
| System | Schedule | Output Path |
|---|---|---|
| ML Battleground Ensemble | 30 min | `ml_battleground/ensemble_data/active_picks.json` |
| Regime Terminal | 30 min | `regime_terminal/data/active_signals.json` |
| KIMI_FEB172026 | 5 min | `KIMI_FEB172026/data/latest_signals.json` |
| Antigravity Claude Opus | 1 hour | `ml_crypto_predictor/enhanced_models/live_picks/active_picks.json` |
| FC-CRYPTO PRO | 30 min | `data/fc_crypto_pro_picks.json` |
| Crypto Gainer ML | 15 min | `crypto_gainer_ml/tracker/live_picks.json` |
| Incubator Forward Scanner | 30 min | `incubator/backtest_results/forward_signals.json` |
| QuantumFusion | 1 hour | `quantum_fusion_report.json` |
| Predictions/Social | 15 min | `predictions/data/active_predictions.json` |
| Goldmine | 3x daily | `data/goldmine/unified_picks.json` |
| Stocks Competition | weekdays | `STOCKS/competition/forward_picks.json` |
| Cross-Aggregator output | 5 min | `data/aggregated_picks.json` |

### Predictions System Problems
- 98% of 367 predictions have NO entry price → 0 trades ever resolved
- Reddit scraper fully 403-blocked
- 20 named analysts have 0 scraped predictions
- StockTwits dominates with sentiment-only posts (no price levels)

### Not Yet Integrated
- `tradingview-ta` Python library (documented in tmp/CRYPTO_PREDICTION_SOURCES.md, not installed)
- TradingView technical ratings (Strong Buy/Buy/Neutral/Sell/Strong Sell across timeframes)

---

## Task 1: Signal Recorder Core — Database + Schema

**Files:**
- Create: `signal_recorder/db.py`
- Create: `signal_recorder/__init__.py`
- Test: manual SQLite inspection

**Step 1: Create the signal_recorder package**

```python
# signal_recorder/__init__.py
"""Unified Signal Recorder — logs every pick from every system with live prices."""
```

**Step 2: Create db.py with signal_log schema**

```python
# signal_recorder/db.py
"""SQLite database for the unified signal log."""
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(__file__).parent / "data" / "signal_log.db"


def get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _create_tables(conn)
    return conn


def _create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS signal_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            symbol TEXT NOT NULL,
            system_id TEXT NOT NULL,
            signal TEXT NOT NULL,
            strength REAL DEFAULT 0.5,
            entry_price REAL,
            take_profit REAL,
            stop_loss REAL,
            price_at_signal REAL,
            extra_json TEXT,
            batch_id TEXT
        );
        CREATE TABLE IF NOT EXISTS signal_outcomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_log_id INTEGER NOT NULL,
            check_minutes INTEGER NOT NULL,
            price_at_check REAL NOT NULL,
            pnl_pct REAL NOT NULL,
            FOREIGN KEY (signal_log_id) REFERENCES signal_log(id)
        );
        CREATE TABLE IF NOT EXISTS combo_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            combo_key TEXT NOT NULL,
            symbol TEXT,
            direction TEXT NOT NULL,
            window_minutes INTEGER NOT NULL,
            total_trades INTEGER NOT NULL,
            wins INTEGER NOT NULL,
            losses INTEGER NOT NULL,
            win_rate REAL NOT NULL,
            avg_pnl_pct REAL NOT NULL,
            sharpe REAL,
            p_value REAL,
            last_updated TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_sl_timestamp ON signal_log(timestamp);
        CREATE INDEX IF NOT EXISTS idx_sl_symbol ON signal_log(symbol);
        CREATE INDEX IF NOT EXISTS idx_sl_system ON signal_log(system_id);
        CREATE INDEX IF NOT EXISTS idx_sl_batch ON signal_log(batch_id);
        CREATE INDEX IF NOT EXISTS idx_so_signal ON signal_outcomes(signal_log_id);
        CREATE INDEX IF NOT EXISTS idx_cr_combo ON combo_results(combo_key);
    """)
    conn.commit()


def log_signal(conn: sqlite3.Connection, system_id: str, symbol: str,
               signal: str, strength: float, price_at_signal: float,
               entry_price: float = None, take_profit: float = None,
               stop_loss: float = None, extra: dict = None,
               batch_id: str = None) -> int:
    """Record one signal snapshot. Deduplicates by system+symbol+batch."""
    if batch_id:
        existing = conn.execute(
            "SELECT id FROM signal_log WHERE system_id=? AND symbol=? AND batch_id=?",
            (system_id, symbol, batch_id)
        ).fetchone()
        if existing:
            return existing["id"]
    now = datetime.now(timezone.utc).isoformat()
    cur = conn.execute("""
        INSERT INTO signal_log
            (timestamp, symbol, system_id, signal, strength, entry_price,
             take_profit, stop_loss, price_at_signal, extra_json, batch_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (now, symbol, system_id, signal, strength, entry_price,
          take_profit, stop_loss, price_at_signal,
          json.dumps(extra) if extra else None, batch_id))
    conn.commit()
    return cur.lastrowid


def record_outcome(conn: sqlite3.Connection, signal_log_id: int,
                   check_minutes: int, price_at_check: float, pnl_pct: float) -> None:
    """Record price outcome at a specific time horizon (15m, 1h, 4h, 24h, 7d)."""
    conn.execute("""
        INSERT INTO signal_outcomes (signal_log_id, check_minutes, price_at_check, pnl_pct)
        VALUES (?, ?, ?, ?)
    """, (signal_log_id, check_minutes, price_at_check, pnl_pct))
    conn.commit()


def get_signals_in_window(conn: sqlite3.Connection, symbol: str,
                          start: str, end: str) -> list[dict]:
    """Get all signals for a symbol within a time window."""
    rows = conn.execute("""
        SELECT * FROM signal_log
        WHERE symbol = ? AND timestamp BETWEEN ? AND ?
        ORDER BY timestamp
    """, (symbol, start, end)).fetchall()
    return [dict(r) for r in rows]


def save_combo_result(conn: sqlite3.Connection, combo_key: str,
                      direction: str, window_minutes: int,
                      total: int, wins: int, losses: int,
                      win_rate: float, avg_pnl: float,
                      sharpe: float = None, p_value: float = None,
                      symbol: str = None) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        INSERT OR REPLACE INTO combo_results
            (combo_key, symbol, direction, window_minutes, total_trades,
             wins, losses, win_rate, avg_pnl_pct, sharpe, p_value, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (combo_key, symbol, direction, window_minutes, total, wins, losses,
          win_rate, avg_pnl, sharpe, p_value, now))
    conn.commit()
```

**Step 3: Verify by running Python import**

Run: `cd /e/findtorontoevents_antigravity.ca && py -c "from signal_recorder.db import get_db; db=get_db(); print('OK:', db.execute('SELECT count(*) FROM signal_log').fetchone()[0])"`
Expected: `OK: 0`

**Step 4: Commit**

```bash
git add signal_recorder/
git commit -m "feat(signal-recorder): create unified signal log database schema"
```

---

## Task 2: System Scanner — Read All 27+ Systems

**Files:**
- Create: `signal_recorder/system_scanner.py`
- Modify: (none — reads existing JSON files)

**Step 1: Create system_scanner.py**

This reads every system's active_picks.json and normalizes picks into the signal_log. The key challenge is each system has a slightly different JSON format — this normalizer handles all variants.

```python
# signal_recorder/system_scanner.py
"""Read all trading system outputs and log signals."""
import json
import pathlib
import requests
from datetime import datetime, timezone
from typing import Optional

from signal_recorder.db import get_db, log_signal

ROOT = pathlib.Path(__file__).parent.parent

# ── All systems with their JSON paths and field mappings ──
SYSTEMS = {
    # Hub systems (15)
    "mercury2":         "mercury2/data/active_picks.json",
    "alpha_engine":     "alpha_engine/data/active_picks.json",
    "kimi_rotc":        "KIMI_RISEOFTHECLAW/data/active_picks.json",
    "crypto_ml_edge":   "crypto_ml_edge/data/active_picks.json",
    "claude_gainer":    "claude_gainer_ml/tracker/claude_live_picks.json",
    "ml_bg_a":          "ml_battleground/system_a_filter/data/active_picks.json",
    "ml_bg_b":          "ml_battleground/system_b_regime/data/active_picks.json",
    "ml_bg_c":          "ml_battleground/system_c_deeplearn/data/active_picks.json",
    "ml_bg_d":          "ml_battleground/system_d_carry/data/active_picks.json",
    "ml_bg_e":          "ml_battleground/system_e_momentum/data/active_picks.json",
    "claws_of_doom":    "ml_battleground/system_f_clawsofdoom/data/active_picks.json",
    "signal_engine":    "crypto_signal_engine/data/active_picks.json",
    "breakout_a":       "breakout_arena/approach_a_sr_breakout/data/active_picks.json",
    "breakout_b":       "breakout_arena/approach_b_ml_breakout/data/active_picks.json",
    "breakout_c":       "breakout_arena/approach_c_spike_reverse/data/active_picks.json",
    # Missing from Hub (12)
    "ensemble":         "ml_battleground/ensemble_data/active_picks.json",
    "regime_terminal":  "regime_terminal/data/active_signals.json",
    "kimi_feb17":       "KIMI_FEB172026/data/latest_signals.json",
    "ml_crypto_pred":   "ml_crypto_predictor/enhanced_models/live_picks/active_picks.json",
    "fc_crypto_pro":    "data/fc_crypto_pro_picks.json",
    "crypto_gainer":    "crypto_gainer_ml/tracker/live_picks.json",
    "incubator_fwd":    "incubator/backtest_results/forward_signals.json",
    "quantum_fusion":   "quantum_fusion_report.json",
    "social_predict":   "predictions/data/active_predictions.json",
    "goldmine":         "data/goldmine/unified_picks.json",
    "stocks_comp":      "STOCKS/competition/forward_picks.json",
    "cross_agg":        "data/aggregated_picks.json",
}

# Symbol normalizer (same logic as cross_aggregation)
SYMBOL_ALIASES = {
    "BTC-USD": "BTCUSDT", "BTCUSD": "BTCUSDT", "BTC": "BTCUSDT",
    "ETH-USD": "ETHUSDT", "ETHUSD": "ETHUSDT", "ETH": "ETHUSDT",
    "SOL-USD": "SOLUSDT", "SOLUSD": "SOLUSDT", "SOL": "SOLUSDT",
    "DOGE-USD": "DOGEUSDT", "DOGEUSD": "DOGEUSDT", "DOGE": "DOGEUSDT",
    "XRP-USD": "XRPUSDT", "XRPUSD": "XRPUSDT", "XRP": "XRPUSDT",
    "ADA-USD": "ADAUSDT", "ADAUSD": "ADAUSDT", "ADA": "ADAUSDT",
    "LINK-USD": "LINKUSDT", "LINKUSD": "LINKUSDT", "LINK": "LINKUSDT",
    "DOT-USD": "DOTUSDT", "DOTUSD": "DOTUSDT", "DOT": "DOTUSDT",
    "BNB-USD": "BNBUSDT", "BNBUSD": "BNBUSDT", "BNB": "BNBUSDT",
    "AVAX-USD": "AVAXUSDT", "AVAXUSD": "AVAXUSDT", "AVAX": "AVAXUSDT",
}

# Direction normalizer
DIRECTION_MAP = {
    "BUY": "BUY", "LONG": "BUY", "BULLISH": "BUY",
    "SELL": "SELL", "SHORT": "SELL", "BEARISH": "SELL",
    "STRONG_BUY": "BUY", "STRONG_SELL": "SELL",
    "NEUTRAL": "NEUTRAL",
}


def normalize_symbol(sym: str) -> str:
    s = sym.upper().strip()
    return SYMBOL_ALIASES.get(s, s)


def normalize_direction(d: str) -> str:
    return DIRECTION_MAP.get(d.upper().strip(), d.upper().strip())


def fetch_binance_prices() -> dict:
    """Fetch all USDT pair prices from Binance."""
    try:
        resp = requests.get("https://api.binance.com/api/v3/ticker/price", timeout=10)
        return {t["symbol"]: float(t["price"]) for t in resp.json()}
    except Exception as e:
        print(f"  Binance price fetch error: {e}")
        return {}


def _extract_picks_from_json(data, system_id: str) -> list[dict]:
    """Normalize various JSON formats into a list of pick dicts."""
    picks = []

    # Handle different JSON shapes
    if isinstance(data, list):
        raw_picks = data
    elif isinstance(data, dict):
        # Try common keys
        for key in ("active_picks", "picks", "active_predictions", "signals",
                     "active_calls", "active_signals", "forward_signals",
                     "consensus_picks", "data"):
            if key in data and isinstance(data[key], list):
                raw_picks = data[key]
                break
        else:
            raw_picks = []
    else:
        return []

    for p in raw_picks:
        if not isinstance(p, dict):
            continue
        # Extract symbol
        symbol = p.get("symbol") or p.get("pair") or p.get("ticker") or ""
        if not symbol:
            continue
        symbol = normalize_symbol(symbol)

        # Extract direction
        direction = (p.get("direction") or p.get("signal") or
                     p.get("side") or p.get("action") or "")
        if not direction:
            continue
        direction = normalize_direction(direction)

        # Extract strength/confidence
        strength = (p.get("confidence") or p.get("strength") or
                    p.get("score") or p.get("consensus_score") or 0.5)
        if isinstance(strength, str):
            try:
                strength = float(strength)
            except ValueError:
                strength = 0.5

        # Extract prices
        entry = p.get("entry_price") or p.get("entry") or p.get("entryPrice")
        tp = p.get("take_profit") or p.get("tp") or p.get("targetPrice") or p.get("target")
        sl = p.get("stop_loss") or p.get("sl") or p.get("stopPrice") or p.get("stop")

        # Strategy name for extra context
        strategy = (p.get("strategy") or p.get("strategy_name") or
                    p.get("source") or p.get("predictor_id") or "")

        picks.append({
            "symbol": symbol,
            "direction": direction,
            "strength": float(strength) if strength else 0.5,
            "entry_price": float(entry) if entry else None,
            "take_profit": float(tp) if tp else None,
            "stop_loss": float(sl) if sl else None,
            "extra": {"strategy": strategy, "system": system_id,
                      "raw_keys": list(p.keys())[:10]},
        })

    return picks


def scan_all_systems(batch_id: str = None) -> dict:
    """Read all system JSONs, log every signal with current Binance price."""
    if not batch_id:
        batch_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")

    prices = fetch_binance_prices()
    conn = get_db()
    stats = {"systems_read": 0, "signals_logged": 0, "errors": []}

    for system_id, rel_path in SYSTEMS.items():
        path = ROOT / rel_path
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text())
            picks = _extract_picks_from_json(data, system_id)
            for pick in picks:
                sym = pick["symbol"]
                price = prices.get(sym, None)
                log_signal(
                    conn, system_id=system_id, symbol=sym,
                    signal=pick["direction"], strength=pick["strength"],
                    price_at_signal=price,
                    entry_price=pick.get("entry_price"),
                    take_profit=pick.get("take_profit"),
                    stop_loss=pick.get("stop_loss"),
                    extra=pick.get("extra"),
                    batch_id=batch_id,
                )
                stats["signals_logged"] += 1
            stats["systems_read"] += 1
        except Exception as e:
            stats["errors"].append(f"{system_id}: {e}")

    conn.close()
    return stats


if __name__ == "__main__":
    stats = scan_all_systems()
    print(f"Systems read: {stats['systems_read']}")
    print(f"Signals logged: {stats['signals_logged']}")
    if stats["errors"]:
        print(f"Errors: {len(stats['errors'])}")
        for err in stats["errors"][:5]:
            print(f"  {err}")
```

**Step 2: Run locally to test**

Run: `cd /e/findtorontoevents_antigravity.ca && py signal_recorder/system_scanner.py`
Expected: `Systems read: 15+`, `Signals logged: 50+`

**Step 3: Commit**

```bash
git add signal_recorder/
git commit -m "feat(signal-recorder): system scanner reads all 27 trading systems"
```

---

## Task 3: TradingView Technicals Integration

**Files:**
- Create: `signal_recorder/tv_technicals.py`
- Modify: `signal_recorder/system_scanner.py` (add TV technicals call)
- Modify: `predictions/requirements.txt` (add tradingview-ta)

**Step 1: Add tradingview-ta to requirements**

Append `tradingview-ta>=3.3.0` to `predictions/requirements.txt`.

**Step 2: Create tv_technicals.py**

```python
# signal_recorder/tv_technicals.py
"""Fetch TradingView technical analysis ratings for tracked symbols."""

try:
    from tradingview_ta import TA_Handler, Interval
    _HAS_TV_TA = True
except ImportError:
    _HAS_TV_TA = False
    print("WARNING: tradingview-ta not installed. Run: pip install tradingview-ta")

from signal_recorder.db import get_db, log_signal

# Symbols to track with their TradingView screener/exchange info
CRYPTO_SYMBOLS = {
    "BTCUSDT": {"screener": "crypto", "exchange": "BINANCE"},
    "ETHUSDT": {"screener": "crypto", "exchange": "BINANCE"},
    "SOLUSDT": {"screener": "crypto", "exchange": "BINANCE"},
    "BNBUSDT": {"screener": "crypto", "exchange": "BINANCE"},
    "XRPUSDT": {"screener": "crypto", "exchange": "BINANCE"},
    "DOGEUSDT": {"screener": "crypto", "exchange": "BINANCE"},
    "ADAUSDT": {"screener": "crypto", "exchange": "BINANCE"},
    "AVAXUSDT": {"screener": "crypto", "exchange": "BINANCE"},
    "LINKUSDT": {"screener": "crypto", "exchange": "BINANCE"},
    "DOTUSDT": {"screener": "crypto", "exchange": "BINANCE"},
    "MATICUSDT": {"screener": "crypto", "exchange": "BINANCE"},
    "SUIUSDT": {"screener": "crypto", "exchange": "BINANCE"},
}

FOREX_SYMBOLS = {
    "EURUSD": {"screener": "forex", "exchange": "FX_IDC"},
    "GBPUSD": {"screener": "forex", "exchange": "FX_IDC"},
    "USDJPY": {"screener": "forex", "exchange": "FX_IDC"},
    "AUDUSD": {"screener": "forex", "exchange": "FX_IDC"},
}

STOCK_SYMBOLS = {
    "SPY": {"screener": "america", "exchange": "AMEX"},
    "QQQ": {"screener": "america", "exchange": "NASDAQ"},
    "AAPL": {"screener": "america", "exchange": "NASDAQ"},
    "TSLA": {"screener": "america", "exchange": "NASDAQ"},
}

# Timeframes to check
TIMEFRAMES = {
    "1h": Interval.INTERVAL_1_HOUR if _HAS_TV_TA else None,
    "4h": Interval.INTERVAL_4_HOURS if _HAS_TV_TA else None,
    "1d": Interval.INTERVAL_1_DAY if _HAS_TV_TA else None,
    "1w": Interval.INTERVAL_1_WEEK if _HAS_TV_TA else None,
}

# Map TV recommendation to signal + strength
RECOMMENDATION_MAP = {
    "STRONG_BUY":  ("BUY", 0.95),
    "BUY":         ("BUY", 0.70),
    "NEUTRAL":     ("NEUTRAL", 0.50),
    "SELL":        ("SELL", 0.70),
    "STRONG_SELL": ("SELL", 0.95),
}


def fetch_tv_technicals(batch_id: str = None) -> dict:
    """Fetch TradingView technical ratings and log as signals."""
    if not _HAS_TV_TA:
        return {"error": "tradingview-ta not installed"}

    conn = get_db()
    stats = {"symbols_checked": 0, "signals_logged": 0, "errors": []}
    all_symbols = {**CRYPTO_SYMBOLS, **FOREX_SYMBOLS, **STOCK_SYMBOLS}

    for symbol, info in all_symbols.items():
        for tf_name, tf_interval in TIMEFRAMES.items():
            if tf_interval is None:
                continue
            try:
                handler = TA_Handler(
                    symbol=symbol,
                    screener=info["screener"],
                    exchange=info["exchange"],
                    interval=tf_interval,
                )
                analysis = handler.get_analysis()
                rec = analysis.summary.get("RECOMMENDATION", "NEUTRAL")
                signal, strength = RECOMMENDATION_MAP.get(rec, ("NEUTRAL", 0.50))

                extra = {
                    "recommendation": rec,
                    "buy_count": analysis.summary.get("BUY", 0),
                    "sell_count": analysis.summary.get("SELL", 0),
                    "neutral_count": analysis.summary.get("NEUTRAL", 0),
                    "rsi": analysis.indicators.get("RSI"),
                    "macd": analysis.indicators.get("MACD.macd"),
                    "ema20": analysis.indicators.get("EMA20"),
                    "sma50": analysis.indicators.get("SMA50"),
                    "close": analysis.indicators.get("close"),
                }
                price = analysis.indicators.get("close")

                # Normalize symbol for our DB (forex doesn't have USDT suffix)
                db_symbol = symbol if symbol.endswith("USDT") else symbol

                system_id = f"tv_tech_{tf_name}"
                log_signal(
                    conn, system_id=system_id, symbol=db_symbol,
                    signal=signal, strength=strength,
                    price_at_signal=price,
                    extra=extra, batch_id=batch_id,
                )
                stats["signals_logged"] += 1
            except Exception as e:
                stats["errors"].append(f"{symbol}/{tf_name}: {e}")

        stats["symbols_checked"] += 1

    conn.close()
    return stats


if __name__ == "__main__":
    stats = fetch_tv_technicals()
    print(f"Symbols checked: {stats['symbols_checked']}")
    print(f"Signals logged: {stats['signals_logged']}")
    if stats["errors"]:
        print(f"Errors ({len(stats['errors'])}):")
        for e in stats["errors"][:5]:
            print(f"  {e}")
```

**Step 3: Test locally**

Run: `cd /e/findtorontoevents_antigravity.ca && pip install tradingview-ta && py signal_recorder/tv_technicals.py`
Expected: `Symbols checked: 20`, `Signals logged: 60+` (20 symbols × 4 timeframes × ~75% success rate)

**Step 4: Commit**

```bash
git add signal_recorder/tv_technicals.py predictions/requirements.txt
git commit -m "feat(signal-recorder): add TradingView technical analysis ratings (1h/4h/1d/1w)"
```

---

## Task 4: Fix Predictions — Auto-Fill Entry Prices

**Files:**
- Modify: `predictions/validation/price_validator.py`

The core fix: when a prediction has no entry_price, stamp it with the current Binance price. This makes the 98% of predictions with NULL entry prices actually trackable.

**Step 1: Add auto-fill logic to price_validator.py**

Add this block at the top of the `for pred in active:` loop, right after `current = prices[sym]` (after line 46):

```python
        # ── Auto-fill missing entry price with current price on first validation ──
        if not entry:
            entry = current
            conn.execute(
                "UPDATE predictions SET entry_price = ? WHERE id = ? AND entry_price IS NULL",
                (current, pred["id"])
            )
            conn.commit()
            # Also auto-fill TP/SL if missing (default 5% TP, 3% SL)
            if not tp:
                if direction == "LONG":
                    tp = round(current * 1.05, 8)
                else:
                    tp = round(current * 0.95, 8)
                conn.execute("UPDATE predictions SET take_profit = ? WHERE id = ? AND take_profit IS NULL",
                             (tp, pred["id"]))
            if not sl:
                if direction == "LONG":
                    sl = round(current * 0.97, 8)
                else:
                    sl = round(current * 1.03, 8)
                conn.execute("UPDATE predictions SET stop_loss = ? WHERE id = ? AND stop_loss IS NULL",
                             (sl, pred["id"]))
            conn.commit()
```

**Step 2: Verify the fix works**

Run: `cd /e/findtorontoevents_antigravity.ca && py predictions/validation/price_validator.py`
Expected: Predictions now have entry prices filled and start resolving (TP_HIT/SL_HIT).

**Step 3: Commit**

```bash
git add predictions/validation/price_validator.py
git commit -m "fix(predictions): auto-fill missing entry/TP/SL prices from Binance on first validation"
```

---

## Task 5: Outcome Tracker — Measure What Happened After Each Signal

**Files:**
- Create: `signal_recorder/outcome_tracker.py`

This is the critical piece that makes combo analysis possible. For every signal in the log, it records what the price did at 15m, 1h, 4h, 24h, and 7d after the signal fired.

**Step 1: Create outcome_tracker.py**

```python
# signal_recorder/outcome_tracker.py
"""Track price outcomes for signals at multiple time horizons."""
import json
import requests
from datetime import datetime, timezone, timedelta
from signal_recorder.db import get_db, record_outcome

CHECK_HORIZONS = [15, 60, 240, 1440, 10080]  # minutes: 15m, 1h, 4h, 24h, 7d


def fetch_binance_prices() -> dict:
    try:
        resp = requests.get("https://api.binance.com/api/v3/ticker/price", timeout=10)
        return {t["symbol"]: float(t["price"]) for t in resp.json()}
    except Exception:
        return {}


def track_outcomes() -> dict:
    """For signals old enough, record price outcome at each time horizon."""
    conn = get_db()
    prices = fetch_binance_prices()
    now = datetime.now(timezone.utc)
    stats = {"checked": 0, "outcomes_recorded": 0}

    # Get signals that don't yet have all outcomes recorded
    for horizon in CHECK_HORIZONS:
        cutoff = (now - timedelta(minutes=horizon)).isoformat()
        # Signals old enough for this horizon, that don't have this horizon recorded yet
        rows = conn.execute("""
            SELECT sl.id, sl.symbol, sl.signal, sl.price_at_signal, sl.timestamp
            FROM signal_log sl
            WHERE sl.timestamp <= ?
              AND sl.price_at_signal IS NOT NULL
              AND sl.signal IN ('BUY', 'SELL')
              AND NOT EXISTS (
                  SELECT 1 FROM signal_outcomes so
                  WHERE so.signal_log_id = sl.id AND so.check_minutes = ?
              )
            LIMIT 500
        """, (cutoff, horizon)).fetchall()

        for row in rows:
            sym = row["symbol"]
            if sym not in prices:
                continue
            current_price = prices[sym]
            entry_price = row["price_at_signal"]
            if not entry_price or entry_price == 0:
                continue

            # Calculate PnL based on direction
            if row["signal"] == "BUY":
                pnl = round((current_price - entry_price) / entry_price * 100, 4)
            else:  # SELL
                pnl = round((entry_price - current_price) / entry_price * 100, 4)

            record_outcome(conn, row["id"], horizon, current_price, pnl)
            stats["outcomes_recorded"] += 1
            stats["checked"] += 1

    conn.close()
    return stats


if __name__ == "__main__":
    stats = track_outcomes()
    print(f"Checked: {stats['checked']}")
    print(f"Outcomes recorded: {stats['outcomes_recorded']}")
```

**Step 2: Test locally**

Run: `cd /e/findtorontoevents_antigravity.ca && py signal_recorder/outcome_tracker.py`
Expected: First run records 0 (signals too fresh). After 15+ minutes of data: `Outcomes recorded: N`.

**Step 3: Commit**

```bash
git add signal_recorder/outcome_tracker.py
git commit -m "feat(signal-recorder): outcome tracker records PnL at 15m/1h/4h/24h/7d horizons"
```

---

## Task 6: Combo Backtester Engine

**Files:**
- Create: `signal_recorder/combo_engine.py`

The WIN FINDER. Systematically tests every 2-way and 3-way combination of systems to find statistically significant winning combos.

**Step 1: Create combo_engine.py**

```python
# signal_recorder/combo_engine.py
"""
Combo Backtester Engine — the WIN FINDER.

Tests every 2-way and 3-way combination of system signals:
  "When systems A+B both said BUY within the same 4h window, what was the 24h outcome?"

Outputs statistically significant winning combos with p-values.
"""
import json
import math
from itertools import combinations
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from pathlib import Path

from signal_recorder.db import get_db, save_combo_result

# Time window: signals must fire within this window to count as "concurrent"
CONFLUENCE_WINDOW_MIN = 240  # 4 hours

# Outcome horizon to evaluate (24h PnL)
EVAL_HORIZON_MIN = 1440  # 24 hours

# Minimum trades to consider a combo meaningful
MIN_TRADES = 5

# Significance threshold
P_VALUE_THRESHOLD = 0.05

# Win threshold (PnL > 0.5% to filter noise)
WIN_THRESHOLD_PCT = 0.5

OUTPUT_PATH = Path(__file__).parent / "data" / "winning_combos.json"


def _binomial_p_value(wins: int, total: int, null_prob: float = 0.50) -> float:
    """One-sided binomial test: P(X >= wins) under null hypothesis of null_prob."""
    if total == 0:
        return 1.0
    p_value = 0.0
    for k in range(wins, total + 1):
        binom_coeff = math.comb(total, k)
        p_value += binom_coeff * (null_prob ** k) * ((1 - null_prob) ** (total - k))
    return p_value


def _calc_sharpe(pnls: list[float]) -> float:
    if len(pnls) < 2:
        return 0.0
    mean = sum(pnls) / len(pnls)
    variance = sum((x - mean) ** 2 for x in pnls) / (len(pnls) - 1)
    std = variance ** 0.5
    if std == 0:
        return 0.0
    return round(mean / std * (252 ** 0.5), 2)  # Annualized


def find_winning_combos(max_combo_size: int = 3) -> dict:
    """Find all statistically significant winning signal combinations."""
    conn = get_db()

    # Get all signals that have 24h outcome data
    rows = conn.execute("""
        SELECT sl.id, sl.timestamp, sl.symbol, sl.system_id, sl.signal,
               sl.price_at_signal, so.pnl_pct
        FROM signal_log sl
        JOIN signal_outcomes so ON so.signal_log_id = sl.id
        WHERE so.check_minutes = ?
          AND sl.signal IN ('BUY', 'SELL')
          AND sl.price_at_signal IS NOT NULL
        ORDER BY sl.timestamp
    """, (EVAL_HORIZON_MIN,)).fetchall()

    if not rows:
        print("No outcome data yet. Need signals + 24h of price tracking.")
        conn.close()
        return {"combos_tested": 0, "winners": []}

    # Group signals by (symbol, time_bucket) — bucket = 4h windows
    buckets = defaultdict(list)
    for r in rows:
        ts = datetime.fromisoformat(r["timestamp"])
        bucket_key = (r["symbol"], ts.strftime("%Y%m%d_%H"))  # hourly buckets
        buckets[bucket_key].append(dict(r))

    # Find all unique system_ids
    all_systems = sorted(set(r["system_id"] for r in rows))
    print(f"Systems with outcome data: {len(all_systems)}: {all_systems}")
    print(f"Time buckets: {len(buckets)}")
    print(f"Total signals with outcomes: {len(rows)}")

    # Test all 2-way and 3-way combos
    results = []
    combos_tested = 0

    for combo_size in range(2, max_combo_size + 1):
        for combo in combinations(all_systems, combo_size):
            combo_key = "+".join(sorted(combo))
            # For each direction
            for direction in ("BUY", "SELL"):
                trades_pnl = []

                # Walk through each time bucket
                for bucket_key, signals in buckets.items():
                    # Check if ALL systems in this combo fired the same direction
                    # within the confluence window
                    systems_in_bucket = {}
                    for sig in signals:
                        if sig["signal"] == direction and sig["system_id"] in combo:
                            systems_in_bucket[sig["system_id"]] = sig

                    if len(systems_in_bucket) == len(combo):
                        # All systems agree! Use the average PnL of these signals
                        avg_pnl = sum(s["pnl_pct"] for s in systems_in_bucket.values()) / len(systems_in_bucket)
                        trades_pnl.append(avg_pnl)

                combos_tested += 1
                if len(trades_pnl) < MIN_TRADES:
                    continue

                wins = sum(1 for p in trades_pnl if p > WIN_THRESHOLD_PCT)
                losses = len(trades_pnl) - wins
                win_rate = wins / len(trades_pnl) if trades_pnl else 0
                avg_pnl = sum(trades_pnl) / len(trades_pnl)
                sharpe = _calc_sharpe(trades_pnl)
                p_value = _binomial_p_value(wins, len(trades_pnl))

                save_combo_result(
                    conn, combo_key=combo_key, direction=direction,
                    window_minutes=CONFLUENCE_WINDOW_MIN,
                    total=len(trades_pnl), wins=wins, losses=losses,
                    win_rate=win_rate, avg_pnl=avg_pnl,
                    sharpe=sharpe, p_value=p_value,
                )

                if p_value < P_VALUE_THRESHOLD and win_rate > 0.55:
                    results.append({
                        "combo": combo_key,
                        "direction": direction,
                        "trades": len(trades_pnl),
                        "wins": wins,
                        "win_rate": round(win_rate * 100, 1),
                        "avg_pnl": round(avg_pnl, 2),
                        "sharpe": sharpe,
                        "p_value": round(p_value, 4),
                    })

    # Sort by p_value (most significant first)
    results.sort(key=lambda x: x["p_value"])

    # Export winning combos
    output = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "combos_tested": combos_tested,
        "winners": results,
        "confluence_window_min": CONFLUENCE_WINDOW_MIN,
        "eval_horizon_min": EVAL_HORIZON_MIN,
        "min_trades": MIN_TRADES,
        "p_value_threshold": P_VALUE_THRESHOLD,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2))

    conn.close()
    print(f"\nCombos tested: {combos_tested}")
    print(f"Winning combos found: {len(results)}")
    for r in results[:10]:
        print(f"  {r['combo']} {r['direction']}: {r['win_rate']}% WR, "
              f"{r['trades']} trades, p={r['p_value']}, Sharpe={r['sharpe']}")

    return output


if __name__ == "__main__":
    find_winning_combos()
```

**Step 2: Test (will show 0 winners until data accumulates)**

Run: `cd /e/findtorontoevents_antigravity.ca && py signal_recorder/combo_engine.py`
Expected: `No outcome data yet.` or `Combos tested: N, Winning combos found: 0` (needs 24h+ of signal data)

**Step 3: Commit**

```bash
git add signal_recorder/combo_engine.py
git commit -m "feat(signal-recorder): combo backtester engine — systematic win finder for signal combinations"
```

---

## Task 7: GitHub Actions Workflow

**Files:**
- Create: `.github/workflows/signal-recorder.yml`

**Step 1: Create the workflow**

```yaml
# .github/workflows/signal-recorder.yml
name: Signal Recorder

on:
  schedule:
    - cron: '3,18,33,48 * * * *'  # Every 15 min (offset to avoid collision)
  workflow_dispatch:

jobs:
  record-signals:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: pip install requests tradingview-ta

      - name: Record all system signals
        run: python signal_recorder/system_scanner.py

      - name: Fetch TradingView technicals
        run: python signal_recorder/tv_technicals.py

      - name: Track signal outcomes
        run: python signal_recorder/outcome_tracker.py

      - name: Run combo engine (nightly only)
        if: github.event.schedule == '3 4 * * *' || github.event_name == 'workflow_dispatch'
        run: python signal_recorder/combo_engine.py

      - name: Commit data
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add signal_recorder/data/ || true
          git diff --staged --quiet || git commit -m "Signal recorder update $(date -u '+%Y-%m-%d %H:%M UTC')"
          git pull --rebase origin main || true
          git push || true
```

**Step 2: Add nightly combo analysis schedule**

Add a second cron entry to run the combo engine once daily at 4 AM UTC:

The current `if` condition in the workflow handles this: it runs the combo engine only at 4:03 UTC or on manual dispatch.

**Step 3: Commit**

```bash
git add .github/workflows/signal-recorder.yml
git commit -m "feat(signal-recorder): GitHub Actions workflow — record every 15 min, combo analysis nightly"
```

---

## Task 8: Add Missing Systems to Hub

**Files:**
- Modify: `hub/index.html` (add 7 missing systems to SYSTEMS array)

**Step 1: Add the missing systems to the SYSTEMS array in hub/index.html**

After the existing breakout_c entry, add:

```javascript
  {
    id: 'ensemble', name: 'ML: BG Ensemble', badge: 'new', scanInterval: 30,
    methodology: 'Consensus of Battleground Systems A+B+C. System B weighted 2x. Produces ensemble picks from multi-model agreement.',
    activePath: BASE+'ml_battleground/ensemble_data/active_picks.json',
    closedPath: BASE+'ml_battleground/ensemble_data/closed_picks.json',
    dashboard: null, extra: []
  },
  {
    id: 'regime_terminal', name: 'Regime Terminal', badge: 'new', scanInterval: 30,
    methodology: 'HMM regime detection. Identifies bull/bear/sideways market states and generates directional confidence signals.',
    activePath: BASE+'regime_terminal/data/active_signals.json', closedPath: null,
    dashboard: PAGES+'regime_terminal/', extra: []
  },
  {
    id: 'ml_crypto_pred', name: 'ML: Claude Opus Predictor', badge: 'new', scanInterval: 60,
    methodology: 'Enhanced ML models with Claude Opus integration for crypto price prediction.',
    activePath: BASE+'ml_crypto_predictor/enhanced_models/live_picks/active_picks.json',
    closedPath: BASE+'ml_crypto_predictor/enhanced_models/live_picks/closed_picks.json',
    dashboard: null, extra: []
  },
  {
    id: 'fc_crypto_pro', name: 'FC-CRYPTO PRO', badge: 'new', scanInterval: 30,
    methodology: 'Cross-aggregation derived crypto signals with momentum + trend filters.',
    activePath: BASE+'data/fc_crypto_pro_picks.json', closedPath: null,
    dashboard: null, extra: []
  },
  {
    id: 'crypto_gainer', name: 'ML: Crypto Gainer', badge: 'new', scanInterval: 15,
    methodology: 'ML-based crypto gainer prediction with live price tracking.',
    activePath: BASE+'crypto_gainer_ml/tracker/live_picks.json', closedPath: null,
    dashboard: null, extra: []
  },
  {
    id: 'quantum_fusion', name: 'QuantumFusion', badge: 'new', scanInterval: 60,
    methodology: 'Quantum-inspired signal fusion engine combining multiple factor models.',
    activePath: BASE+'quantum_fusion_report.json', closedPath: null,
    dashboard: null, extra: []
  },
  {
    id: 'incubator_fwd', name: 'Incubator Forward Test', badge: 'new', scanInterval: 30,
    methodology: 'Forward-testing promising baby strategies from the incubator pipeline.',
    activePath: BASE+'incubator/backtest_results/forward_signals.json', closedPath: null,
    dashboard: PAGES+'battleground/', extra: []
  },
```

**Step 2: Verify Hub loads correctly**

Open `hub/index.html` in browser and confirm all new system cards render.

**Step 3: Commit**

```bash
git add hub/index.html
git commit -m "feat(hub): add 7 missing systems — ensemble, regime terminal, claude opus, fc-crypto, crypto gainer, quantum fusion, incubator"
```

---

## Task 9: Add Missing Systems to Cross-Aggregator

**Files:**
- Modify: `cross_aggregation/aggregator.py` (add missing systems to SYSTEMS dict)

**Step 1: Add missing systems to the SYSTEMS dict (around line 40)**

After the existing entries, add:

```python
    "ml_bg_d":          "ml_battleground/system_d_carry/data/active_picks.json",
    "ml_bg_e":          "ml_battleground/system_e_momentum/data/active_picks.json",
    "regime_terminal":  "regime_terminal/data/active_signals.json",
    "kimi_feb17":       "KIMI_FEB172026/data/latest_signals.json",
    "ml_crypto_pred":   "ml_crypto_predictor/enhanced_models/live_picks/active_picks.json",
    "fc_crypto_pro":    "data/fc_crypto_pro_picks.json",
    "crypto_gainer":    "crypto_gainer_ml/tracker/live_picks.json",
    "incubator_fwd":    "incubator/backtest_results/forward_signals.json",
    "quantum_fusion":   "quantum_fusion_report.json",
```

Note: `ensemble` and `predictions` are already in the aggregator (lines 53-55). Don't re-add those.

**Step 2: Test**

Run: `cd /e/findtorontoevents_antigravity.ca && py cross_aggregation/aggregator.py`
Expected: Should read from more systems than before.

**Step 3: Commit**

```bash
git add cross_aggregation/aggregator.py
git commit -m "feat(cross-agg): add 9 missing systems — BG D/E, regime, KIMI feb17, claude opus, fc-crypto, gainer, incubator, quantum"
```

---

## Task 10: Export Winning Combos to Hub

**Files:**
- Create: `signal_recorder/export_hub_combos.py`
- Modify: `hub/index.html` (add winning combos section)

**Step 1: Create export script**

```python
# signal_recorder/export_hub_combos.py
"""Export winning combos as a JSON file for the Hub dashboard to display."""
import json
from pathlib import Path
from signal_recorder.db import get_db

OUTPUT_PATH = Path(__file__).parent / "data" / "winning_combos.json"
HUB_OUTPUT = Path(__file__).parent.parent / "hub" / "data" / "winning_combos.json"


def export_for_hub() -> None:
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM combo_results
        WHERE p_value < 0.05 AND win_rate > 0.55 AND total_trades >= 5
        ORDER BY p_value ASC
        LIMIT 50
    """).fetchall()
    conn.close()

    combos = [dict(r) for r in rows]
    output = {
        "updated_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
        "winning_combos": combos,
        "total_found": len(combos),
    }

    for path in (OUTPUT_PATH, HUB_OUTPUT):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(output, indent=2, default=str))

    print(f"Exported {len(combos)} winning combos to hub")


if __name__ == "__main__":
    export_for_hub()
```

**Step 2: Add winning combos display section to Hub**

Add a new tab/section in `hub/index.html` that loads `data/winning_combos.json` and renders a table of winning combos with: combo name, direction, win rate, trades, Sharpe, p-value. (Implementation details depend on current Hub HTML structure — adapt to match existing style.)

**Step 3: Commit**

```bash
git add signal_recorder/export_hub_combos.py hub/data/ hub/index.html
git commit -m "feat(hub): display winning signal combos from the combo backtester"
```

---

## Execution Order Summary

| Task | Description | Dependencies | Est. |
|------|-------------|--------------|------|
| 1 | Signal Recorder DB schema | None | 5 min |
| 2 | System Scanner (reads all 27 systems) | Task 1 | 10 min |
| 3 | TradingView Technicals integration | Task 1 | 10 min |
| 4 | Fix Predictions auto-fill entry prices | None (independent) | 5 min |
| 5 | Outcome Tracker (price @ 15m/1h/4h/24h/7d) | Task 1 | 8 min |
| 6 | Combo Backtester Engine | Tasks 1, 5 | 12 min |
| 7 | GitHub Actions workflow | Tasks 2, 3, 5, 6 | 5 min |
| 8 | Add missing systems to Hub | None (independent) | 8 min |
| 9 | Add missing systems to Cross-Aggregator | None (independent) | 5 min |
| 10 | Export winning combos to Hub | Tasks 6, 8 | 8 min |

**Parallel execution groups:**
- Group A (independent): Tasks 1, 4, 8, 9
- Group B (depends on Task 1): Tasks 2, 3, 5
- Group C (depends on Group B): Tasks 6, 7, 10

---

## Data Accumulation Timeline

After deployment:
- **Day 1:** Signal recorder starts logging. 200+ signals per 15-min batch. TradingView technicals every 15 min.
- **Day 1 + 15 min:** First outcome data (15-min horizon) starts appearing.
- **Day 1 + 24 hours:** First 24-hour outcomes. Combo engine can start finding patterns.
- **Day 7:** Full 7-day outcomes. First statistically significant combos likely visible with ~670 batches × 200+ signals.
- **Day 14:** Combo results become reliable with 1,300+ data points per system.

## Research Backlog — Mined from 300+ MDs in Repository

The research agent found **massive untapped value** buried across the codebase. Here are the highest-priority items for future tasks, organized by expected impact.

### P0 — Quick Wins (< 1 hour each, high impact)

| Item | Source File | Impact |
|------|------------|--------|
| **Bitcoin Overnight Seasonality** (22:00-00:00 UTC) — Sharpe 1.58, 33% annual, 2-line strategy | `tmp/RESEARCH_ROUNDS_1_5.md` | New baby strategy, near-zero effort |
| **DXY Weekly Drop Signal** — 94% WR, Sharpe 2.5-3.0, 18 occurrences since 2013 | `tmp/DEEP_RESEARCH_ROUNDS_17_19.md` | Free FRED data, 2-hour build |
| **NR7 Volatility Contraction Breakout** (Toby Crabel) — pure OHLCV | `tmp/RESEARCH_ROUNDS_1_5.md` | Easy baby strategy |

### P1 — Unbuilt Signal Sources (documented in `tmp/CRYPTO_PREDICTION_SOURCES.md`)

| Source | Status | Notes |
|--------|--------|-------|
| `tradingview-ta` (26-indicator consensus) | **Task 3 above** | Being built |
| Whale Alert API (free key) | NOT integrated | 2 hours |
| Glassnode free tier (SOPR, exchange flows) | NOT integrated | 3 hours |
| StockGeist (free 10k/month, real-time sentiment) | NOT integrated | 2 hours |
| CoinGlass (funding rates, OI, liquidations) | NOT integrated | 3 hours |
| LunarCrush (social volume, galaxy score) | NOT integrated | 2 hours |
| CME FedWatch (rate cut probabilities → crypto) | NOT integrated | 2 hours |
| VIX Term Structure (contango/backwardation) | NOT integrated | 1 hour |

### P2 — 10 Critical ML Bugs (from `CRYPTO_ML_WORLDCLASS_RESEARCH/FINAL_SYNTHESIS_REPORT.md`)

28 researcher AI agents found these bugs explaining poor ML performance — **none fixed**:

1. **System C GRU-Attention is a no-op** — squeezes to length 1 before attention
2. **XGBoost learning_rate=0.3** (should be 0.005-0.05)
3. **Cost model subtracts every bar** — 10x overcounting, all DSR values invalid
4. **System B regime = always "range_bound"** — ADX threshold never reached
5. **SOPR proxy uses SMA instead of real UTXO data** — wrong signal
6. **EnsembleStacker uses random split** — data leakage (should be TimeSeriesSplit)
7. **Stop losses too tight for 15m** — negative Kelly everywhere
8. **Sequential symbol fetching** — 12-50s bottleneck (need asyncio)
9. **Real-time scanner creates synthetic OHLC** — destroys microstructure
10. **CUSUM detector classifies but never acts**

### P3 — High-Sharpe Unbuilt Strategies

| Strategy | Source | Sharpe | Academic Reference |
|----------|--------|--------|-------------------|
| Turn-of-the-Candle Microstructure (buy at :00/:15/:30/:45) | `RARE_HOURLY_CRYPTO_STRATEGIES_RESEARCH.md` | **4.96** | Shanaev et al. 2023, Heliyon |
| Copula-Based Pairs Trading | same file | **3.77** | Tadi 2025, Financial Innovation |
| Order Flow Conditioned ML Portfolio | same file | **3.63** | Anastasopoulos & Gradojevic 2025 |
| Dynamic Grid Trading | `tmp/DEEP_RESEARCH_ROUND_11.md` | ~1.5 | arXiv:2506.11921 |
| Donchian Channel Ensemble (5 lookbacks) | `tmp/RESEARCH_ROUNDS_1_5.md` | >1.5 | SSRN 2025, Zarattini-Barbon |
| Gold/BTC Correlation Regime | `tmp/DEEP_RESEARCH_ROUNDS_17_19.md` | 1.2-1.6 | CME Group, WisdomTree 2025 |

### P4 — Architecture Upgrades (from `docs/plans/2026-02-28-ultimate-system-integration.md`)

Ready-to-copy code exists but was never deployed:
- **Fractal Regime Detector** (`incubator/regime/fractal_regime_detector.py` — file doesn't exist)
- **Correlation Filter** (cross-asset deduplicator — file doesn't exist)
- **Risk Parity Position Sizer** (inverse-volatility — file doesn't exist)
- **Quarter-Kelly sizing** — still flat $100/trade across 150+ strategies

### P5 — Social Predictions Gap (from `tmp/DEEP_RESEARCH_ROUND_12.md`)

8,000+ predictions in `predictions.db` are **not connected to the cross-aggregation engine**. A Bayesian predictor weighting system is fully designed but the `wisdom_of_crowds_aggregator.py` module does not exist.

### Key Research Files Index

| File | Content | Lines |
|------|---------|-------|
| `tmp/CRYPTO_PREDICTION_SOURCES.md` | Complete multi-source prediction aggregator | ~1,312 |
| `tmp/RESEARCH_ROUNDS_1_5.md` | 8 novel strategies (overnight seasonality, NR7, etc.) | ~800 |
| `tmp/DEEP_RESEARCH_ROUNDS_17_19.md` | DXY signal, Gold/BTC, yield curve, FedWatch | ~600 |
| `tmp/DEEP_RESEARCH_ROUND_12.md` | Social predictions bridge + Bayesian weights | ~500 |
| `RARE_HOURLY_CRYPTO_STRATEGIES_RESEARCH.md` | 3 strategies with Sharpe >3.5 | ~400 |
| `CRYPTO_ML_WORLDCLASS_RESEARCH/FINAL_SYNTHESIS_REPORT.md` | 10 critical ML bugs | ~800 |
| `docs/plans/2026-02-28-ultimate-system-integration.md` | Ready-to-copy regime/correlation/risk code | ~500 |
| `.planning/OPTIMIZATION_PLAN.md` | 6-phase system optimization + Super Strategy | ~400 |
| `DEEP_RESEARCH_ML_AI_TRADING.md` | Quantformer, GNN, stacked ensemble | ~600 |
| `DEEP_RESEARCH_PORTFOLIO_CONSTRUCTION.md` | Kelly, Black-Litterman, factor portfolios | ~700 |
