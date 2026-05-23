#!/usr/bin/env python3
"""
ATM Challenge — The Ultimate Strategy Proving Ground
=====================================================

Continuously pulls picks from ALL systems, backtests them against recent data,
eliminates losers, mutates winners via DNA engine, and tracks performance
in real-time paper trading on AsterDEX.

Architecture:
    1. HARVEST  — Pull signals from all systems (proven, contrarian, DNA, Connors)
    2. BACKTEST — Quick 7-day walk-forward backtest on each strategy variant
    3. ELIMINATE — Kill strategies below threshold, demote declining ones
    4. MUTATE   — DNA-mutate top performers to create children
    5. EXECUTE  — Paper trade top-ranked strategies
    6. LEARN    — Update scores, adjust weights based on outcomes

Runs locally (no GitHub Actions needed). Designed for continuous operation.

Usage:
    # Run one cycle (scan + backtest + trade)
    python -m trading.atm_challenge --once

    # Continuous loop (every 5 min)
    python -m trading.atm_challenge --loop

    # Backtest-only mode (no trading)
    python -m trading.atm_challenge --backtest-only

    # Show leaderboard
    python -m trading.atm_challenge --leaderboard
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import random
import sqlite3
import time
import urllib.request
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── Constants ────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent
ATM_DB = REPO_ROOT / "trading" / "data" / "atm_challenge.db"
ATM_JSON = REPO_ROOT / "trading" / "data" / "atm_leaderboard.json"

# Backtest parameters
SLIPPAGE_PCT = 0.0005       # 0.05% per side
FEE_PCT = 0.00035           # 0.035% per side
MAX_HOLD_CANDLES = 64       # 16 hours at 15m
POSITION_SIZE_PCT = 0.01    # 1% of balance per trade
WARMUP_BARS = 60

# ATM scoring
MIN_TRADES_FOR_RANKING = 5
ELIMINATION_WR = 0.35       # Below 35% WR = eliminated
PROMOTION_WR = 0.55         # Above 55% WR = promoted to live candidates
PROMOTION_SHARPE = 1.0      # Sharpe >= 1.0 for live candidates
ELITE_WR = 0.60             # Above 60% = elite tier
ELITE_SHARPE = 1.5

# Symbols — high velocity crypto
HIGH_VELOCITY_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "XRPUSDT",
    "AVAXUSDT", "ADAUSDT", "DOTUSDT", "LINKUSDT", "NEARUSDT",
    "APTUSDT", "TIAUSDT", "SUIUSDT", "ARBUSDT", "OPUSDT",
]

# Scan interval
SCAN_INTERVAL_SEC = 300  # 5 minutes


# ── Data Classes ─────────────────────────────────────────────────────

@dataclass
class StrategyVariant:
    """A specific strategy configuration to test."""
    variant_id: str
    name: str
    parent_id: Optional[str] = None
    generation: int = 0
    genes: Dict[str, Any] = field(default_factory=dict)
    # Performance tracking
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    total_pnl: float = 0.0
    peak_pnl: float = 0.0
    max_drawdown: float = 0.0
    sharpe: float = 0.0
    pnl_history: List[float] = field(default_factory=list)
    # Status
    tier: str = "INCUBATOR"  # INCUBATOR -> CONTENDER -> CHAMPION -> ELITE
    status: str = "active"   # active, eliminated, paused
    created_at: str = ""
    last_signal_at: str = ""

    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return self.wins / self.total_trades

    def compute_sharpe(self) -> float:
        if len(self.pnl_history) < 2:
            return 0.0
        avg = sum(self.pnl_history) / len(self.pnl_history)
        var = sum((p - avg) ** 2 for p in self.pnl_history) / len(self.pnl_history)
        std = math.sqrt(var) if var > 0 else 0.001
        # Annualize assuming ~4 trades/day
        return round((avg / std) * math.sqrt(252 * 4), 2)

    def to_dict(self) -> Dict:
        return {
            "variant_id": self.variant_id,
            "name": self.name,
            "parent_id": self.parent_id,
            "generation": self.generation,
            "genes": self.genes,
            "total_trades": self.total_trades,
            "wins": self.wins,
            "losses": self.losses,
            "win_rate": round(self.win_rate() * 100, 1),
            "total_pnl": round(self.total_pnl, 2),
            "sharpe": self.sharpe,
            "max_drawdown": round(self.max_drawdown, 2),
            "tier": self.tier,
            "status": self.status,
            "created_at": self.created_at,
            "last_signal_at": self.last_signal_at,
        }


# ── Database ─────────────────────────────────────────────────────────

class ATMDatabase:
    """SQLite database for ATM Challenge state."""

    def __init__(self, db_path: Path = ATM_DB):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS variants (
                variant_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                parent_id TEXT,
                generation INTEGER DEFAULT 0,
                genes TEXT DEFAULT '{}',
                total_trades INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                total_pnl REAL DEFAULT 0.0,
                peak_pnl REAL DEFAULT 0.0,
                max_drawdown REAL DEFAULT 0.0,
                sharpe REAL DEFAULT 0.0,
                pnl_history TEXT DEFAULT '[]',
                tier TEXT DEFAULT 'INCUBATOR',
                status TEXT DEFAULT 'active',
                created_at TEXT,
                last_signal_at TEXT
            );

            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                variant_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL,
                exit_price REAL,
                pnl_pct REAL,
                pnl_usd REAL,
                entry_time TEXT,
                exit_time TEXT,
                exit_reason TEXT,
                is_backtest INTEGER DEFAULT 0,
                FOREIGN KEY (variant_id) REFERENCES variants(variant_id)
            );

            CREATE TABLE IF NOT EXISTS cycle_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                phase TEXT,
                details TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_trades_variant ON trades(variant_id);
            CREATE INDEX IF NOT EXISTS idx_variants_tier ON variants(tier);
            CREATE INDEX IF NOT EXISTS idx_variants_status ON variants(status);
        """)
        self.conn.commit()

    def save_variant(self, v: StrategyVariant):
        self.conn.execute("""
            INSERT OR REPLACE INTO variants
            (variant_id, name, parent_id, generation, genes,
             total_trades, wins, losses, total_pnl, peak_pnl, max_drawdown,
             sharpe, pnl_history, tier, status, created_at, last_signal_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            v.variant_id, v.name, v.parent_id, v.generation,
            json.dumps(v.genes), v.total_trades, v.wins, v.losses,
            v.total_pnl, v.peak_pnl, v.max_drawdown, v.sharpe,
            json.dumps(v.pnl_history[-200:]),  # Keep last 200
            v.tier, v.status, v.created_at, v.last_signal_at,
        ))
        self.conn.commit()

    def load_variant(self, variant_id: str) -> Optional[StrategyVariant]:
        row = self.conn.execute(
            "SELECT * FROM variants WHERE variant_id = ?", (variant_id,)
        ).fetchone()
        if not row:
            return None
        return self._row_to_variant(row)

    def load_active_variants(self) -> List[StrategyVariant]:
        rows = self.conn.execute(
            "SELECT * FROM variants WHERE status = 'active' ORDER BY sharpe DESC"
        ).fetchall()
        return [self._row_to_variant(r) for r in rows]

    def load_all_variants(self) -> List[StrategyVariant]:
        rows = self.conn.execute(
            "SELECT * FROM variants ORDER BY tier DESC, sharpe DESC"
        ).fetchall()
        return [self._row_to_variant(r) for r in rows]

    def record_trade(self, variant_id: str, symbol: str, direction: str,
                     entry_price: float, exit_price: float, pnl_pct: float,
                     pnl_usd: float, entry_time: str, exit_time: str,
                     exit_reason: str, is_backtest: bool = False):
        self.conn.execute("""
            INSERT INTO trades (variant_id, symbol, direction, entry_price,
            exit_price, pnl_pct, pnl_usd, entry_time, exit_time,
            exit_reason, is_backtest)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (variant_id, symbol, direction, entry_price, exit_price,
              pnl_pct, pnl_usd, entry_time, exit_time, exit_reason,
              1 if is_backtest else 0))
        self.conn.commit()

    def log_cycle(self, phase: str, details: str):
        self.conn.execute(
            "INSERT INTO cycle_log (timestamp, phase, details) VALUES (?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(), phase, details)
        )
        self.conn.commit()

    def get_variant_trades(self, variant_id: str, limit: int = 50) -> List[Dict]:
        rows = self.conn.execute(
            "SELECT * FROM trades WHERE variant_id = ? ORDER BY id DESC LIMIT ?",
            (variant_id, limit)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_tier_counts(self) -> Dict[str, int]:
        rows = self.conn.execute(
            "SELECT tier, COUNT(*) as cnt FROM variants WHERE status='active' GROUP BY tier"
        ).fetchall()
        return {r["tier"]: r["cnt"] for r in rows}

    def _row_to_variant(self, row) -> StrategyVariant:
        return StrategyVariant(
            variant_id=row["variant_id"],
            name=row["name"],
            parent_id=row["parent_id"],
            generation=row["generation"],
            genes=json.loads(row["genes"] or "{}"),
            total_trades=row["total_trades"],
            wins=row["wins"],
            losses=row["losses"],
            total_pnl=row["total_pnl"],
            peak_pnl=row["peak_pnl"],
            max_drawdown=row["max_drawdown"],
            sharpe=row["sharpe"],
            pnl_history=json.loads(row["pnl_history"] or "[]"),
            tier=row["tier"],
            status=row["status"],
            created_at=row["created_at"] or "",
            last_signal_at=row["last_signal_at"] or "",
        )

    def close(self):
        self.conn.close()


# ── Market Data ──────────────────────────────────────────────────────

def fetch_klines(symbol: str, interval: str = "15m", limit: int = 200) -> List:
    """Fetch klines from Binance public API."""
    try:
        url = (
            f"https://api.binance.com/api/v3/klines"
            f"?symbol={symbol}&interval={interval}&limit={limit}"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [ERROR] Klines fetch failed for {symbol}: {e}")
        return []


def get_current_price(symbol: str) -> Optional[float]:
    """Get current price from Binance."""
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return float(data["price"])
    except Exception:
        return None


# ── Strategy Library ─────────────────────────────────────────────────

def _compute_rsi(closes: List[float], period: int = 14) -> Optional[float]:
    """Wilder's RSI."""
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    first_gains = [d if d > 0 else 0.0 for d in deltas[:period]]
    first_losses = [-d if d < 0 else 0.0 for d in deltas[:period]]
    avg_gain = sum(first_gains) / period
    avg_loss = sum(first_losses) / period
    for d in deltas[period:]:
        avg_gain = (avg_gain * (period - 1) + (d if d > 0 else 0.0)) / period
        avg_loss = (avg_loss * (period - 1) + (-d if d < 0 else 0.0)) / period
    if avg_loss == 0:
        return 100.0
    return round(100.0 - (100.0 / (1.0 + avg_gain / avg_loss)), 4)


def _compute_atr(highs: List[float], lows: List[float],
                 closes: List[float], period: int = 14) -> Optional[float]:
    """Average True Range."""
    if len(closes) < period + 1:
        return None
    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]),
                 abs(lows[i] - closes[i-1]))
        trs.append(tr)
    if len(trs) < period:
        return None
    return sum(trs[-period:]) / period


def _compute_ema(values: List[float], period: int) -> Optional[float]:
    """Exponential Moving Average (current value only)."""
    if len(values) < period:
        return None
    mult = 2.0 / (period + 1)
    ema = sum(values[:period]) / period
    for v in values[period:]:
        ema = (v - ema) * mult + ema
    return ema


def _compute_sma(values: List[float], period: int) -> Optional[float]:
    """Simple Moving Average."""
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def _parse_klines(klines: List) -> Dict[str, List[float]]:
    """Parse Binance kline arrays to OHLCV."""
    return {
        "open": [float(k[1]) for k in klines],
        "high": [float(k[2]) for k in klines],
        "low": [float(k[3]) for k in klines],
        "close": [float(k[4]) for k in klines],
        "volume": [float(k[5]) for k in klines],
    }


def _vol_ratio(volumes: List[float], lookback: int = 20) -> float:
    """Current volume vs average."""
    if len(volumes) < lookback + 1:
        return 1.0
    avg = sum(volumes[-lookback-1:-1]) / lookback
    return volumes[-1] / avg if avg > 0 else 1.0


# ── Base Strategy Functions (with tunable genes) ─────────────────────

def strategy_whale_rsi(symbol: str, ohlcv: Dict, genes: Dict) -> Optional[Dict]:
    """Whale Confirmed RSI with tunable parameters."""
    rsi_period = genes.get("rsi_period", 14)
    rsi_oversold = genes.get("rsi_oversold", 30)
    rsi_overbought = genes.get("rsi_overbought", 70)
    vol_threshold = genes.get("vol_threshold", 2.0)
    tp_mult = genes.get("tp_mult", 2.0)
    sl_mult = genes.get("sl_mult", 1.5)

    closes, highs, lows, volumes = ohlcv["close"], ohlcv["high"], ohlcv["low"], ohlcv["volume"]
    rsi = _compute_rsi(closes, rsi_period)
    atr = _compute_atr(highs, lows, closes, 14)
    vr = _vol_ratio(volumes, 20)

    if rsi is None or atr is None or atr <= 0:
        return None

    price = closes[-1]
    direction = None

    if rsi < rsi_oversold and vr >= vol_threshold:
        direction = "LONG"
        tp = price + tp_mult * atr
        sl = price - sl_mult * atr
        conf = min(0.65 + (rsi_oversold - rsi) / 100 + (vr - vol_threshold) / 20, 0.92)
    elif rsi > rsi_overbought and vr >= vol_threshold:
        direction = "SHORT"
        tp = price - tp_mult * atr
        sl = price + sl_mult * atr
        conf = min(0.65 + (rsi - rsi_overbought) / 100 + (vr - vol_threshold) / 20, 0.92)
    else:
        return None

    return {"symbol": symbol, "direction": direction, "entry_price": price,
            "take_profit": tp, "stop_loss": sl, "confidence": round(conf, 3),
            "indicators": {"rsi": rsi, "atr": atr, "vol_ratio": round(vr, 2)}}


def strategy_atr_regime_rsi(symbol: str, ohlcv: Dict, genes: Dict) -> Optional[Dict]:
    """ATR Regime RSI with tunable parameters."""
    rsi_threshold = genes.get("rsi_threshold", 35)
    atr_regime_max = genes.get("atr_regime_max", 1.2)
    tp_mult = genes.get("tp_mult", 2.0)
    sl_mult = genes.get("sl_mult", 1.5)

    closes, highs, lows = ohlcv["close"], ohlcv["high"], ohlcv["low"]
    rsi = _compute_rsi(closes, 14)
    atr = _compute_atr(highs, lows, closes, 14)

    if rsi is None or atr is None or atr <= 0 or len(closes) < 65:
        return None

    # ATR regime
    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        trs.append(tr)
    if len(trs) < 50:
        return None
    current_atr = sum(trs[-14:]) / 14
    avg_atr = sum(trs[-50:]) / 50
    if avg_atr <= 0:
        return None
    atr_ratio = current_atr / avg_atr

    if atr_ratio >= atr_regime_max or rsi >= rsi_threshold:
        return None

    price = closes[-1]
    tp = price + tp_mult * atr
    sl = price - sl_mult * atr
    conf = min(0.55 + (rsi_threshold - rsi) / 100 + (atr_regime_max - atr_ratio) / 5, 0.85)

    return {"symbol": symbol, "direction": "LONG", "entry_price": price,
            "take_profit": tp, "stop_loss": sl, "confidence": round(conf, 3),
            "indicators": {"rsi": rsi, "atr_ratio": round(atr_ratio, 4)}}


def strategy_multi_rsi(symbol: str, ohlcv: Dict, genes: Dict) -> Optional[Dict]:
    """Multi-Period RSI Confluence with tunable parameters."""
    rsi_short_period = genes.get("rsi_short_period", 14)
    rsi_long_period = genes.get("rsi_long_period", 50)
    rsi_short_th = genes.get("rsi_short_threshold", 35)
    rsi_long_th = genes.get("rsi_long_threshold", 40)
    tp_mult = genes.get("tp_mult", 2.0)
    sl_mult = genes.get("sl_mult", 1.5)

    closes, highs, lows = ohlcv["close"], ohlcv["high"], ohlcv["low"]
    rsi_s = _compute_rsi(closes, rsi_short_period)
    rsi_l = _compute_rsi(closes, rsi_long_period)
    atr = _compute_atr(highs, lows, closes, 14)

    if rsi_s is None or rsi_l is None or atr is None or atr <= 0:
        return None
    if rsi_s >= rsi_short_th or rsi_l >= rsi_long_th:
        return None

    price = closes[-1]
    tp = price + tp_mult * atr
    sl = price - sl_mult * atr
    conf = min(0.70 + (rsi_short_th - rsi_s) / 100 + (rsi_long_th - rsi_l) / 100, 0.95)

    return {"symbol": symbol, "direction": "LONG", "entry_price": price,
            "take_profit": tp, "stop_loss": sl, "confidence": round(conf, 3),
            "indicators": {"rsi_short": rsi_s, "rsi_long": rsi_l}}


def strategy_connors_rsi2(symbol: str, ohlcv: Dict, genes: Dict) -> Optional[Dict]:
    """Connors RSI-2 mean reversion — the only statistically proven strategy."""
    rsi_period = genes.get("rsi_period", 2)
    rsi_entry = genes.get("rsi_entry", 10)
    rsi_exit = genes.get("rsi_exit", 90)
    tp_pct = genes.get("tp_pct", 0.03)   # 3% default
    sl_pct = genes.get("sl_pct", 0.02)   # 2% default

    closes = ohlcv["close"]
    if len(closes) < 10:
        return None

    rsi2 = _compute_rsi(closes, rsi_period)
    sma200 = _compute_sma(closes, min(200, len(closes) - 1))

    if rsi2 is None or sma200 is None:
        return None

    price = closes[-1]

    # Only buy when above 200 SMA (trend filter) and RSI-2 extremely oversold
    if price > sma200 and rsi2 < rsi_entry:
        tp = price * (1 + tp_pct)
        sl = price * (1 - sl_pct)
        conf = min(0.70 + (rsi_entry - rsi2) / 50, 0.95)
        return {"symbol": symbol, "direction": "LONG", "entry_price": price,
                "take_profit": tp, "stop_loss": sl, "confidence": round(conf, 3),
                "indicators": {"rsi2": rsi2, "sma200": round(sma200, 2),
                               "above_sma200": True}}

    # Short when below 200 SMA and RSI-2 extremely overbought
    if price < sma200 and rsi2 > rsi_exit:
        tp = price * (1 - tp_pct)
        sl = price * (1 + sl_pct)
        conf = min(0.65 + (rsi2 - rsi_exit) / 50, 0.90)
        return {"symbol": symbol, "direction": "SHORT", "entry_price": price,
                "take_profit": tp, "stop_loss": sl, "confidence": round(conf, 3),
                "indicators": {"rsi2": rsi2, "sma200": round(sma200, 2),
                               "above_sma200": False}}

    return None


def strategy_ema_crossover(symbol: str, ohlcv: Dict, genes: Dict) -> Optional[Dict]:
    """EMA crossover momentum strategy."""
    fast_period = genes.get("ema_fast", 9)
    slow_period = genes.get("ema_slow", 21)
    tp_mult = genes.get("tp_mult", 2.5)
    sl_mult = genes.get("sl_mult", 1.5)

    closes, highs, lows = ohlcv["close"], ohlcv["high"], ohlcv["low"]
    if len(closes) < slow_period + 5:
        return None

    ema_fast = _compute_ema(closes, fast_period)
    ema_slow = _compute_ema(closes, slow_period)
    # Previous values for crossover detection
    ema_fast_prev = _compute_ema(closes[:-1], fast_period)
    ema_slow_prev = _compute_ema(closes[:-1], slow_period)
    atr = _compute_atr(highs, lows, closes, 14)

    if any(v is None for v in [ema_fast, ema_slow, ema_fast_prev, ema_slow_prev, atr]):
        return None
    if atr <= 0:
        return None

    price = closes[-1]

    # Bullish crossover: fast crosses above slow
    if ema_fast_prev <= ema_slow_prev and ema_fast > ema_slow:
        tp = price + tp_mult * atr
        sl = price - sl_mult * atr
        spread = abs(ema_fast - ema_slow) / price
        conf = min(0.55 + spread * 100, 0.85)
        return {"symbol": symbol, "direction": "LONG", "entry_price": price,
                "take_profit": tp, "stop_loss": sl, "confidence": round(conf, 3),
                "indicators": {"ema_fast": round(ema_fast, 2), "ema_slow": round(ema_slow, 2)}}

    # Bearish crossover
    if ema_fast_prev >= ema_slow_prev and ema_fast < ema_slow:
        tp = price - tp_mult * atr
        sl = price + sl_mult * atr
        spread = abs(ema_slow - ema_fast) / price
        conf = min(0.55 + spread * 100, 0.85)
        return {"symbol": symbol, "direction": "SHORT", "entry_price": price,
                "take_profit": tp, "stop_loss": sl, "confidence": round(conf, 3),
                "indicators": {"ema_fast": round(ema_fast, 2), "ema_slow": round(ema_slow, 2)}}

    return None


def strategy_bollinger_squeeze(symbol: str, ohlcv: Dict, genes: Dict) -> Optional[Dict]:
    """Bollinger Band squeeze breakout."""
    bb_period = genes.get("bb_period", 20)
    bb_std = genes.get("bb_std", 2.0)
    squeeze_threshold = genes.get("squeeze_threshold", 0.03)  # 3% band width
    tp_mult = genes.get("tp_mult", 2.5)
    sl_mult = genes.get("sl_mult", 1.5)

    closes, highs, lows = ohlcv["close"], ohlcv["high"], ohlcv["low"]
    if len(closes) < bb_period + 5:
        return None

    sma = sum(closes[-bb_period:]) / bb_period
    std = math.sqrt(sum((c - sma) ** 2 for c in closes[-bb_period:]) / bb_period)
    upper = sma + bb_std * std
    lower = sma - bb_std * std
    bandwidth = (upper - lower) / sma if sma > 0 else 0

    atr = _compute_atr(highs, lows, closes, 14)
    if atr is None or atr <= 0:
        return None

    price = closes[-1]

    # Squeeze: bandwidth very narrow, price breaking out
    if bandwidth < squeeze_threshold:
        # Check direction of breakout
        if price > upper:
            tp = price + tp_mult * atr
            sl = price - sl_mult * atr
            conf = min(0.60 + (price - upper) / (atr * 2), 0.90)
            return {"symbol": symbol, "direction": "LONG", "entry_price": price,
                    "take_profit": tp, "stop_loss": sl, "confidence": round(conf, 3),
                    "indicators": {"bandwidth": round(bandwidth, 4), "bb_upper": round(upper, 2)}}
        elif price < lower:
            tp = price - tp_mult * atr
            sl = price + sl_mult * atr
            conf = min(0.60 + (lower - price) / (atr * 2), 0.90)
            return {"symbol": symbol, "direction": "SHORT", "entry_price": price,
                    "take_profit": tp, "stop_loss": sl, "confidence": round(conf, 3),
                    "indicators": {"bandwidth": round(bandwidth, 4), "bb_lower": round(lower, 2)}}

    return None


def strategy_funding_rate_carry(symbol: str, ohlcv: Dict, genes: Dict) -> Optional[Dict]:
    """Funding rate carry — short overleveraged longs (needs funding data)."""
    # This strategy checks if price has moved aggressively (proxy for high funding)
    # Real funding data requires exchange API, so we use momentum as proxy
    momentum_period = genes.get("momentum_period", 24)
    momentum_threshold = genes.get("momentum_threshold", 0.05)  # 5% move
    tp_mult = genes.get("tp_mult", 1.5)
    sl_mult = genes.get("sl_mult", 2.0)

    closes, highs, lows = ohlcv["close"], ohlcv["high"], ohlcv["low"]
    if len(closes) < momentum_period + 5:
        return None

    # Calculate momentum
    price = closes[-1]
    past_price = closes[-momentum_period]
    if past_price <= 0:
        return None
    momentum = (price - past_price) / past_price

    atr = _compute_atr(highs, lows, closes, 14)
    if atr is None or atr <= 0:
        return None

    # Extreme upward momentum = likely overleveraged longs -> short
    if momentum > momentum_threshold:
        tp = price - tp_mult * atr
        sl = price + sl_mult * atr
        conf = min(0.55 + abs(momentum) * 2, 0.85)
        return {"symbol": symbol, "direction": "SHORT", "entry_price": price,
                "take_profit": tp, "stop_loss": sl, "confidence": round(conf, 3),
                "indicators": {"momentum": round(momentum, 4), "period": momentum_period}}

    # Extreme downward momentum = overleveraged shorts -> long
    if momentum < -momentum_threshold:
        tp = price + tp_mult * atr
        sl = price - sl_mult * atr
        conf = min(0.55 + abs(momentum) * 2, 0.85)
        return {"symbol": symbol, "direction": "LONG", "entry_price": price,
                "take_profit": tp, "stop_loss": sl, "confidence": round(conf, 3),
                "indicators": {"momentum": round(momentum, 4), "period": momentum_period}}

    return None


# ── Strategy Registry ────────────────────────────────────────────────

# Map of strategy name -> (function, default_genes)
STRATEGY_REGISTRY: Dict[str, Tuple[Any, Dict]] = {
    "whale_rsi": (strategy_whale_rsi, {
        "rsi_period": 14, "rsi_oversold": 30, "rsi_overbought": 70,
        "vol_threshold": 2.0, "tp_mult": 2.0, "sl_mult": 1.5,
    }),
    "atr_regime_rsi": (strategy_atr_regime_rsi, {
        "rsi_threshold": 35, "atr_regime_max": 1.2,
        "tp_mult": 2.0, "sl_mult": 1.5,
    }),
    "multi_rsi": (strategy_multi_rsi, {
        "rsi_short_period": 14, "rsi_long_period": 50,
        "rsi_short_threshold": 35, "rsi_long_threshold": 40,
        "tp_mult": 2.0, "sl_mult": 1.5,
    }),
    "connors_rsi2": (strategy_connors_rsi2, {
        "rsi_period": 2, "rsi_entry": 10, "rsi_exit": 90,
        "tp_pct": 0.03, "sl_pct": 0.02,
    }),
    "ema_crossover": (strategy_ema_crossover, {
        "ema_fast": 9, "ema_slow": 21, "tp_mult": 2.5, "sl_mult": 1.5,
    }),
    "bollinger_squeeze": (strategy_bollinger_squeeze, {
        "bb_period": 20, "bb_std": 2.0, "squeeze_threshold": 0.03,
        "tp_mult": 2.5, "sl_mult": 1.5,
    }),
    "funding_carry": (strategy_funding_rate_carry, {
        "momentum_period": 24, "momentum_threshold": 0.05,
        "tp_mult": 1.5, "sl_mult": 2.0,
    }),
}

# Gene mutation ranges for DNA engine
GENE_RANGES: Dict[str, Dict[str, Tuple]] = {
    "rsi_period": {"type": "int", "range": (2, 21)},
    "rsi_oversold": {"type": "float", "range": (15, 40)},
    "rsi_overbought": {"type": "float", "range": (60, 85)},
    "rsi_threshold": {"type": "float", "range": (20, 45)},
    "rsi_short_period": {"type": "int", "range": (5, 21)},
    "rsi_long_period": {"type": "int", "range": (30, 60)},
    "rsi_short_threshold": {"type": "float", "range": (20, 45)},
    "rsi_long_threshold": {"type": "float", "range": (25, 50)},
    "rsi_entry": {"type": "float", "range": (3, 20)},
    "rsi_exit": {"type": "float", "range": (80, 97)},
    "vol_threshold": {"type": "float", "range": (1.2, 4.0)},
    "tp_mult": {"type": "float", "range": (1.0, 5.0)},
    "sl_mult": {"type": "float", "range": (0.5, 3.0)},
    "tp_pct": {"type": "float", "range": (0.01, 0.08)},
    "sl_pct": {"type": "float", "range": (0.01, 0.05)},
    "atr_regime_max": {"type": "float", "range": (0.8, 2.0)},
    "ema_fast": {"type": "int", "range": (5, 15)},
    "ema_slow": {"type": "int", "range": (15, 50)},
    "bb_period": {"type": "int", "range": (10, 30)},
    "bb_std": {"type": "float", "range": (1.5, 3.0)},
    "squeeze_threshold": {"type": "float", "range": (0.01, 0.06)},
    "momentum_period": {"type": "int", "range": (12, 48)},
    "momentum_threshold": {"type": "float", "range": (0.02, 0.10)},
}


# ── DNA Mutation Engine ──────────────────────────────────────────────

class DNAMutator:
    """Mutate strategy genes to create new variants."""

    @staticmethod
    def mutate(parent: StrategyVariant, mutation_rate: float = 0.3,
               strength: float = 0.2) -> StrategyVariant:
        """Create a mutated child from a parent variant."""
        child_genes = copy.deepcopy(parent.genes)
        strategy_name = child_genes.get("_strategy", "unknown")

        mutated_genes = []
        for gene_name, gene_value in child_genes.items():
            if gene_name.startswith("_"):
                continue
            if random.random() > mutation_rate:
                continue
            if gene_name not in GENE_RANGES:
                continue

            gene_info = GENE_RANGES[gene_name]
            lo, hi = gene_info["range"]

            if gene_info["type"] == "int":
                # Gaussian mutation for integers
                delta = max(1, int((hi - lo) * strength))
                new_val = int(gene_value + random.randint(-delta, delta))
                child_genes[gene_name] = max(lo, min(hi, new_val))
            else:
                # Gaussian mutation for floats
                delta = (hi - lo) * strength
                new_val = gene_value + random.gauss(0, delta)
                child_genes[gene_name] = round(max(lo, min(hi, new_val)), 4)

            mutated_genes.append(gene_name)

        # Ensure at least one gene mutated
        if not mutated_genes and child_genes:
            mutable = [g for g in child_genes if not g.startswith("_") and g in GENE_RANGES]
            if mutable:
                gene_name = random.choice(mutable)
                gene_info = GENE_RANGES[gene_name]
                lo, hi = gene_info["range"]
                if gene_info["type"] == "int":
                    child_genes[gene_name] = random.randint(lo, hi)
                else:
                    child_genes[gene_name] = round(random.uniform(lo, hi), 4)
                mutated_genes.append(gene_name)

        child_id = hashlib.md5(
            json.dumps(child_genes, sort_keys=True).encode()
        ).hexdigest()[:12]

        return StrategyVariant(
            variant_id=f"{strategy_name}_mut_{child_id}",
            name=f"{parent.name} (mut gen{parent.generation + 1})",
            parent_id=parent.variant_id,
            generation=parent.generation + 1,
            genes=child_genes,
            tier="INCUBATOR",
            status="active",
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    @staticmethod
    def crossover(parent_a: StrategyVariant, parent_b: StrategyVariant) -> StrategyVariant:
        """Create a child by combining genes from two parents."""
        child_genes = {}
        strategy_name = parent_a.genes.get("_strategy", "unknown")

        all_keys = set(parent_a.genes.keys()) | set(parent_b.genes.keys())
        for key in all_keys:
            if key.startswith("_"):
                child_genes[key] = parent_a.genes.get(key, parent_b.genes.get(key))
                continue

            a_val = parent_a.genes.get(key)
            b_val = parent_b.genes.get(key)

            if a_val is not None and b_val is not None:
                if isinstance(a_val, (int, float)) and isinstance(b_val, (int, float)):
                    # Blend: random weight between parents
                    w = random.random()
                    blended = a_val * w + b_val * (1 - w)
                    if isinstance(a_val, int) and isinstance(b_val, int):
                        child_genes[key] = int(round(blended))
                    else:
                        child_genes[key] = round(blended, 4)
                else:
                    child_genes[key] = random.choice([a_val, b_val])
            else:
                child_genes[key] = a_val if a_val is not None else b_val

        child_id = hashlib.md5(
            json.dumps(child_genes, sort_keys=True).encode()
        ).hexdigest()[:12]

        return StrategyVariant(
            variant_id=f"{strategy_name}_cross_{child_id}",
            name=f"Cross({parent_a.name[:20]} x {parent_b.name[:20]})",
            parent_id=f"{parent_a.variant_id}+{parent_b.variant_id}",
            generation=max(parent_a.generation, parent_b.generation) + 1,
            genes=child_genes,
            tier="INCUBATOR",
            status="active",
            created_at=datetime.now(timezone.utc).isoformat(),
        )


# ── Quick Backtester ─────────────────────────────────────────────────

class QuickBacktester:
    """Fast 7-day backtest for evaluating strategy variants."""

    def __init__(self, balance: float = 1000.0):
        self.initial_balance = balance

    def backtest_variant(self, variant: StrategyVariant, symbol: str,
                         klines: List) -> Dict:
        """Backtest a single variant on provided klines."""
        strategy_name = variant.genes.get("_strategy")
        if strategy_name not in STRATEGY_REGISTRY:
            return {"trades": 0, "wins": 0, "pnl": 0, "error": "unknown strategy"}

        strat_fn, _ = STRATEGY_REGISTRY[strategy_name]
        ohlcv = _parse_klines(klines)

        balance = self.initial_balance
        trades = []
        position = None

        for i in range(WARMUP_BARS, len(klines)):
            # Check existing position TP/SL
            if position:
                high = float(klines[i][2])
                low = float(klines[i][3])
                close = float(klines[i][4])
                bars_held = i - position["entry_bar"]

                exit_price = None
                exit_reason = None

                if position["direction"] == "LONG":
                    if low <= position["stop_loss"]:
                        exit_price = position["stop_loss"] * (1 - SLIPPAGE_PCT)
                        exit_reason = "SL"
                    elif high >= position["take_profit"]:
                        exit_price = position["take_profit"] * (1 - SLIPPAGE_PCT)
                        exit_reason = "TP"
                else:
                    if high >= position["stop_loss"]:
                        exit_price = position["stop_loss"] * (1 + SLIPPAGE_PCT)
                        exit_reason = "SL"
                    elif low <= position["take_profit"]:
                        exit_price = position["take_profit"] * (1 + SLIPPAGE_PCT)
                        exit_reason = "TP"

                if exit_price is None and bars_held >= MAX_HOLD_CANDLES:
                    exit_price = close
                    exit_reason = "TIME"

                if exit_price:
                    if position["direction"] == "LONG":
                        pnl_pct = (exit_price - position["entry_price"]) / position["entry_price"]
                    else:
                        pnl_pct = (position["entry_price"] - exit_price) / position["entry_price"]
                    pnl_pct -= 2 * FEE_PCT  # Round-trip fees
                    pnl_usd = position["size_usd"] * pnl_pct
                    balance += pnl_usd
                    trades.append({
                        "pnl_pct": round(pnl_pct * 100, 2),
                        "pnl_usd": round(pnl_usd, 2),
                        "reason": exit_reason,
                        "direction": position["direction"],
                    })
                    position = None

            # Generate signal if no position
            if not position and i < len(klines) - 1:
                window = {k: v[:i+1] for k, v in ohlcv.items()}
                try:
                    signal = strat_fn(symbol, window, variant.genes)
                except Exception:
                    signal = None

                if signal:
                    entry = signal["entry_price"] * (1 + SLIPPAGE_PCT if signal["direction"] == "LONG" else 1 - SLIPPAGE_PCT)
                    size_usd = balance * POSITION_SIZE_PCT
                    position = {
                        "direction": signal["direction"],
                        "entry_price": entry,
                        "take_profit": signal["take_profit"],
                        "stop_loss": signal["stop_loss"],
                        "entry_bar": i,
                        "size_usd": size_usd,
                    }

        # Force close any open position
        if position:
            close = float(klines[-1][4])
            if position["direction"] == "LONG":
                pnl_pct = (close - position["entry_price"]) / position["entry_price"]
            else:
                pnl_pct = (position["entry_price"] - close) / position["entry_price"]
            pnl_pct -= 2 * FEE_PCT
            pnl_usd = position["size_usd"] * pnl_pct
            balance += pnl_usd
            trades.append({"pnl_pct": round(pnl_pct * 100, 2), "pnl_usd": round(pnl_usd, 2),
                           "reason": "FORCE_CLOSE", "direction": position["direction"]})

        wins = sum(1 for t in trades if t["pnl_usd"] > 0)
        losses = len(trades) - wins
        total_pnl = sum(t["pnl_usd"] for t in trades)

        return {
            "trades": len(trades),
            "wins": wins,
            "losses": losses,
            "win_rate": round(wins / len(trades) * 100, 1) if trades else 0,
            "total_pnl": round(total_pnl, 2),
            "final_balance": round(balance, 2),
            "pnl_list": [t["pnl_usd"] for t in trades],
            "exit_reasons": {r: sum(1 for t in trades if t["reason"] == r)
                            for r in ["TP", "SL", "TIME", "FORCE_CLOSE"]},
        }


# ── ATM Challenge Engine ────────────────────────────────────────────

class ATMChallenge:
    """The ATM Challenge — evolve strategies until we find real winners."""

    def __init__(self, balance: float = 1000.0):
        self.db = ATMDatabase()
        self.backtester = QuickBacktester(balance)
        self.mutator = DNAMutator()
        self.balance = balance
        self._ensure_seed_variants()

    def _ensure_seed_variants(self):
        """Seed the database with initial variants if empty."""
        existing = self.db.load_active_variants()
        if existing:
            return

        print("[ATM] Seeding initial strategy variants...")
        now = datetime.now(timezone.utc).isoformat()

        for strat_name, (_, default_genes) in STRATEGY_REGISTRY.items():
            genes = {**default_genes, "_strategy": strat_name}
            variant_id = f"{strat_name}_v0"
            v = StrategyVariant(
                variant_id=variant_id,
                name=f"{strat_name} (original)",
                genes=genes,
                tier="INCUBATOR",
                status="active",
                created_at=now,
            )
            self.db.save_variant(v)

            # Also create 3 mutations of each
            for i in range(3):
                child = self.mutator.mutate(v, mutation_rate=0.5, strength=0.3)
                child.variant_id = f"{strat_name}_seed{i}"
                child.name = f"{strat_name} (seed mutation {i+1})"
                self.db.save_variant(child)

        count = len(self.db.load_active_variants())
        print(f"[ATM] Seeded {count} strategy variants")
        self.db.log_cycle("SEED", f"Created {count} initial variants")

    def harvest_signals(self, symbols: List[str] = None) -> Dict[str, List]:
        """Phase 1: Fetch market data for all symbols."""
        symbols = symbols or HIGH_VELOCITY_SYMBOLS
        klines_cache = {}

        print(f"\n[HARVEST] Fetching data for {len(symbols)} symbols...")
        for sym in symbols:
            klines = fetch_klines(sym, "15m", 200)
            if klines and len(klines) > WARMUP_BARS:
                klines_cache[sym] = klines
            time.sleep(0.1)  # Rate limiting

        print(f"[HARVEST] Got data for {len(klines_cache)}/{len(symbols)} symbols")
        return klines_cache

    def backtest_all(self, klines_cache: Dict[str, List],
                     max_variants: int = 50) -> List[Tuple[StrategyVariant, Dict]]:
        """Phase 2: Quick backtest all active variants."""
        variants = self.db.load_active_variants()[:max_variants]
        results = []

        print(f"\n[BACKTEST] Testing {len(variants)} variants across {len(klines_cache)} symbols...")

        for v in variants:
            strat_name = v.genes.get("_strategy")
            if strat_name not in STRATEGY_REGISTRY:
                continue

            # Test on a random subset of symbols to keep it fast
            test_symbols = random.sample(
                list(klines_cache.keys()),
                min(5, len(klines_cache))
            )

            combined = {"trades": 0, "wins": 0, "losses": 0, "total_pnl": 0.0, "pnl_list": []}
            for sym in test_symbols:
                result = self.backtester.backtest_variant(v, sym, klines_cache[sym])
                combined["trades"] += result["trades"]
                combined["wins"] += result["wins"]
                combined["losses"] += result["losses"]
                combined["total_pnl"] += result["total_pnl"]
                combined["pnl_list"].extend(result.get("pnl_list", []))

            combined["win_rate"] = (
                round(combined["wins"] / combined["trades"] * 100, 1)
                if combined["trades"] > 0 else 0
            )

            results.append((v, combined))

        # Sort by PnL descending
        results.sort(key=lambda x: x[1]["total_pnl"], reverse=True)
        return results

    def eliminate_and_promote(self, results: List[Tuple[StrategyVariant, Dict]]):
        """Phase 3: Eliminate losers, promote winners."""
        eliminated = 0
        promoted = 0
        demoted = 0

        print(f"\n[ELIMINATE] Evaluating {len(results)} variants...")

        for v, bt in results:
            trades = bt["trades"]
            wr = bt["win_rate"] / 100.0
            pnl = bt["total_pnl"]

            # Update variant stats
            v.total_trades += trades
            v.wins += bt["wins"]
            v.losses += bt["losses"]
            v.total_pnl += pnl
            v.pnl_history.extend(bt.get("pnl_list", []))
            v.sharpe = v.compute_sharpe()

            # Track drawdown
            if v.total_pnl > v.peak_pnl:
                v.peak_pnl = v.total_pnl
            dd = v.peak_pnl - v.total_pnl if v.peak_pnl > 0 else 0
            v.max_drawdown = max(v.max_drawdown, dd)

            # Elimination: persistent losers
            if v.total_trades >= MIN_TRADES_FOR_RANKING:
                total_wr = v.win_rate()

                if total_wr < ELIMINATION_WR and v.total_trades >= 10:
                    v.status = "eliminated"
                    eliminated += 1
                    print(f"  ELIMINATED: {v.name} (WR={total_wr:.1%}, PnL=${v.total_pnl:.2f})")

                # Promotion logic
                elif total_wr >= ELITE_WR and v.sharpe >= ELITE_SHARPE and v.total_trades >= 20:
                    if v.tier != "ELITE":
                        v.tier = "ELITE"
                        promoted += 1
                        print(f"  ELITE: {v.name} (WR={total_wr:.1%}, Sharpe={v.sharpe}, PnL=${v.total_pnl:.2f})")

                elif total_wr >= PROMOTION_WR and v.sharpe >= PROMOTION_SHARPE and v.total_trades >= 15:
                    if v.tier in ("INCUBATOR", "CONTENDER"):
                        v.tier = "CHAMPION"
                        promoted += 1
                        print(f"  CHAMPION: {v.name} (WR={total_wr:.1%}, Sharpe={v.sharpe})")

                elif total_wr >= 0.45 and v.total_trades >= 10:
                    if v.tier == "INCUBATOR":
                        v.tier = "CONTENDER"
                        promoted += 1

                # Demotion: champions that start losing
                elif v.tier in ("CHAMPION", "ELITE") and total_wr < 0.45:
                    v.tier = "CONTENDER"
                    demoted += 1
                    print(f"  DEMOTED: {v.name} (WR={total_wr:.1%})")

            self.db.save_variant(v)

        self.db.log_cycle("ELIMINATE",
                          f"Eliminated {eliminated}, promoted {promoted}, demoted {demoted}")
        print(f"[ELIMINATE] Eliminated={eliminated}, Promoted={promoted}, Demoted={demoted}")

    def mutate_winners(self, results: List[Tuple[StrategyVariant, Dict]],
                       max_children: int = 10):
        """Phase 4: DNA-mutate top performers to create new variants."""
        # Get top performers (positive PnL)
        winners = [(v, bt) for v, bt in results
                   if bt["total_pnl"] > 0 and bt["trades"] >= 3]

        if not winners:
            print("\n[MUTATE] No winners to mutate yet")
            return

        new_variants = []
        existing_ids = {v.variant_id for v in self.db.load_all_variants()}

        print(f"\n[MUTATE] Creating children from {len(winners)} winners...")

        # Mutate top performers
        for v, bt in winners[:5]:
            for _ in range(2):
                child = self.mutator.mutate(v, mutation_rate=0.3, strength=0.2)
                if child.variant_id not in existing_ids:
                    new_variants.append(child)
                    existing_ids.add(child.variant_id)

        # Crossover between top 2 winners if compatible
        if len(winners) >= 2:
            for i in range(min(3, len(winners) - 1)):
                a = winners[i][0]
                b = winners[i + 1][0]
                if a.genes.get("_strategy") == b.genes.get("_strategy"):
                    child = self.mutator.crossover(a, b)
                    if child.variant_id not in existing_ids:
                        new_variants.append(child)
                        existing_ids.add(child.variant_id)

        # Cap total new variants
        for child in new_variants[:max_children]:
            self.db.save_variant(child)

        print(f"[MUTATE] Created {min(len(new_variants), max_children)} new variants")
        self.db.log_cycle("MUTATE", f"Created {min(len(new_variants), max_children)} children")

    def generate_leaderboard(self) -> Dict:
        """Generate leaderboard JSON for dashboard."""
        all_variants = self.db.load_all_variants()
        tier_counts = self.db.get_tier_counts()
        now = datetime.now(timezone.utc).isoformat()

        # Split by tier
        tiers = {}
        for tier in ["ELITE", "CHAMPION", "CONTENDER", "INCUBATOR"]:
            tier_variants = [v for v in all_variants if v.tier == tier and v.status == "active"]
            tiers[tier] = [v.to_dict() for v in tier_variants[:20]]

        # Top 10 overall (by Sharpe among those with enough trades)
        ranked = [v for v in all_variants
                  if v.status == "active" and v.total_trades >= MIN_TRADES_FOR_RANKING]
        ranked.sort(key=lambda v: v.sharpe, reverse=True)
        top10 = [v.to_dict() for v in ranked[:10]]

        # Recently eliminated
        eliminated = [v for v in all_variants if v.status == "eliminated"]
        eliminated.sort(key=lambda v: v.total_pnl)
        graveyard = [v.to_dict() for v in eliminated[:10]]

        # Stats
        active_count = sum(1 for v in all_variants if v.status == "active")
        eliminated_count = sum(1 for v in all_variants if v.status == "eliminated")
        total_trades = sum(v.total_trades for v in all_variants)
        best = ranked[0] if ranked else None

        leaderboard = {
            "generated_at": now,
            "stats": {
                "active_variants": active_count,
                "eliminated_variants": eliminated_count,
                "total_backtested_trades": total_trades,
                "tier_counts": tier_counts,
                "best_variant": best.to_dict() if best else None,
            },
            "top10": top10,
            "tiers": tiers,
            "graveyard": graveyard,
        }

        ATM_JSON.parent.mkdir(parents=True, exist_ok=True)
        ATM_JSON.write_text(json.dumps(leaderboard, indent=2))
        return leaderboard

    def print_leaderboard(self):
        """Print leaderboard to console."""
        lb = self.generate_leaderboard()
        stats = lb["stats"]

        print(f"\n{'='*70}")
        print(f"  ATM CHALLENGE LEADERBOARD")
        print(f"  Active: {stats['active_variants']} | "
              f"Eliminated: {stats['eliminated_variants']} | "
              f"Total Trades: {stats['total_backtested_trades']}")
        print(f"{'='*70}")

        for tier_name in ["ELITE", "CHAMPION", "CONTENDER"]:
            variants = lb["tiers"].get(tier_name, [])
            if not variants:
                continue
            print(f"\n  [{tier_name}] ({len(variants)} strategies)")
            print(f"  {'Name':<35s} {'WR':>6s} {'PnL':>10s} {'Sharpe':>7s} {'Trades':>7s}")
            print(f"  {'-'*65}")
            for v in variants[:10]:
                name = v["name"][:35]
                print(f"  {name:<35s} {v['win_rate']:>5.1f}% ${v['total_pnl']:>8.2f} "
                      f"{v['sharpe']:>7.2f} {v['total_trades']:>7d}")

        if lb["top10"]:
            print(f"\n  TOP 10 (by Sharpe)")
            print(f"  {'Name':<35s} {'WR':>6s} {'PnL':>10s} {'Sharpe':>7s} {'Tier':>10s}")
            print(f"  {'-'*68}")
            for v in lb["top10"]:
                name = v["name"][:35]
                print(f"  {name:<35s} {v['win_rate']:>5.1f}% ${v['total_pnl']:>8.2f} "
                      f"{v['sharpe']:>7.2f} {v['tier']:>10s}")

        if lb.get("graveyard"):
            print(f"\n  GRAVEYARD (worst eliminated)")
            for v in lb["graveyard"][:5]:
                print(f"  X {v['name'][:40]}: WR={v['win_rate']:.1f}%, PnL=${v['total_pnl']:.2f}")

        print(f"\n{'='*70}\n")

    def run_cycle(self, symbols: List[str] = None):
        """Run one complete ATM cycle: harvest -> backtest -> eliminate -> mutate."""
        cycle_start = time.time()
        now = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
        print(f"\n{'#'*60}")
        print(f"  ATM CHALLENGE CYCLE — {now}")
        print(f"{'#'*60}")

        # Phase 1: Harvest
        klines_cache = self.harvest_signals(symbols)
        if not klines_cache:
            print("[ATM] No market data available, skipping cycle")
            return

        # Phase 2: Backtest
        results = self.backtest_all(klines_cache)

        # Phase 3: Eliminate & Promote
        self.eliminate_and_promote(results)

        # Phase 4: Mutate
        self.mutate_winners(results)

        # Phase 5: Leaderboard
        self.generate_leaderboard()
        self.print_leaderboard()

        elapsed = time.time() - cycle_start
        self.db.log_cycle("CYCLE_COMPLETE", f"Completed in {elapsed:.1f}s")
        print(f"[ATM] Cycle completed in {elapsed:.1f}s")

    def run_loop(self, interval: int = SCAN_INTERVAL_SEC, symbols: List[str] = None):
        """Continuous ATM Challenge loop."""
        print(f"\n{'='*60}")
        print(f"  ATM CHALLENGE — CONTINUOUS MODE")
        print(f"  Scanning every {interval}s | {len(symbols or HIGH_VELOCITY_SYMBOLS)} symbols")
        print(f"{'='*60}\n")

        while True:
            try:
                self.run_cycle(symbols)
                print(f"\n[ATM] Sleeping {interval}s until next cycle...")
                time.sleep(interval)
            except KeyboardInterrupt:
                print("\n\n[ATM] Stopping ATM Challenge...")
                self.print_leaderboard()
                break
            except Exception as e:
                print(f"[ATM ERROR] {e}")
                time.sleep(30)

    def close(self):
        self.db.close()


# ── Dashboard HTML ───────────────────────────────────────────────────

ATM_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ATM Challenge — Strategy Evolution Arena</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { background: #0a0a12; color: #c8c8d8; font-family: 'Segoe UI', -apple-system, sans-serif; min-height: 100vh; }
    .header { text-align: center; padding: 30px 20px 20px; border-bottom: 1px solid rgba(255,255,255,0.06); }
    .header h1 { font-size: 28px; font-weight: 200; letter-spacing: 4px; color: #fff; }
    .header .subtitle { color: #667; font-size: 13px; margin-top: 6px; }
    .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
    .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 24px; }
    .stat-card { background: #12121f; border: 1px solid #1e1e30; border-radius: 10px; padding: 16px; text-align: center; }
    .stat-card .label { font-size: 11px; color: #667; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; }
    .stat-card .value { font-size: 22px; font-weight: 300; color: #fff; }
    .stat-card .value.positive { color: #22c55e; }
    .stat-card .value.negative { color: #ef4444; }
    .section { background: #12121f; border: 1px solid #1e1e30; border-radius: 10px; padding: 20px; margin-bottom: 20px; }
    .section h3 { font-size: 14px; color: #888; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 1px; }
    .tier-badge { display: inline-block; padding: 2px 8px; border-radius: 8px; font-size: 11px; font-weight: 600; }
    .tier-ELITE { background: #f59e0b33; color: #f59e0b; border: 1px solid #f59e0b55; }
    .tier-CHAMPION { background: #22c55e33; color: #22c55e; border: 1px solid #22c55e55; }
    .tier-CONTENDER { background: #3b82f633; color: #3b82f6; border: 1px solid #3b82f655; }
    .tier-INCUBATOR { background: #64748b33; color: #64748b; border: 1px solid #64748b55; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th { text-align: left; padding: 8px 10px; color: #667; font-weight: 500; border-bottom: 1px solid #1e1e30; }
    td { padding: 8px 10px; border-bottom: 1px solid #0f0f1a; }
    .positive { color: #22c55e; }
    .negative { color: #ef4444; }
    .graveyard { opacity: 0.5; }
    .updated { text-align: center; color: #445; font-size: 11px; padding: 20px; }
    @media (max-width: 600px) { .stats-grid { grid-template-columns: repeat(2, 1fr); } }
  </style>
</head>
<body>
  <div class="header">
    <h1>ATM CHALLENGE</h1>
    <div class="subtitle">Strategy Evolution Arena — Survive or Die</div>
  </div>
  <div class="container">
    <div class="stats-grid" id="statsGrid"></div>
    <div class="section">
      <h3>Top 10 Strategies (by Sharpe)</h3>
      <table id="top10Table">
        <thead><tr><th>Rank</th><th>Strategy</th><th>Tier</th><th>WR</th><th>PnL</th><th>Sharpe</th><th>Trades</th><th>Gen</th></tr></thead>
        <tbody id="top10Body"><tr><td colspan="8" style="color:#445">Loading...</td></tr></tbody>
      </table>
    </div>
    <div class="section">
      <h3>Elite Tier</h3>
      <table id="eliteTable">
        <thead><tr><th>Strategy</th><th>WR</th><th>PnL</th><th>Sharpe</th><th>Trades</th><th>Max DD</th></tr></thead>
        <tbody id="eliteBody"><tr><td colspan="6" style="color:#445">No elite strategies yet — earn your place</td></tr></tbody>
      </table>
    </div>
    <div class="section">
      <h3>Champion Tier</h3>
      <table id="champTable">
        <thead><tr><th>Strategy</th><th>WR</th><th>PnL</th><th>Sharpe</th><th>Trades</th></tr></thead>
        <tbody id="champBody"><tr><td colspan="5" style="color:#445">No champions yet</td></tr></tbody>
      </table>
    </div>
    <div class="section graveyard">
      <h3>Graveyard (Eliminated)</h3>
      <table id="graveyardTable">
        <thead><tr><th>Strategy</th><th>WR</th><th>PnL</th><th>Trades</th><th>Cause of Death</th></tr></thead>
        <tbody id="graveyardBody"><tr><td colspan="5" style="color:#445">No casualties yet</td></tr></tbody>
      </table>
    </div>
  </div>
  <div class="updated" id="updatedAt">Loading...</div>
  <script>
    const DATA_URLS = [
      'data/atm_leaderboard.json',
      'https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/trading/data/atm_leaderboard.json',
    ];

    async function loadData() {
      for (const url of DATA_URLS) {
        try {
          const resp = await fetch(url + '?t=' + Date.now());
          if (!resp.ok) continue;
          const d = await resp.json();
          render(d);
          return;
        } catch (e) { continue; }
      }
      document.getElementById('updatedAt').textContent = 'Failed to load data';
    }

    function render(d) {
      const s = d.stats || {};
      const grid = document.getElementById('statsGrid');
      const tc = s.tier_counts || {};
      grid.innerHTML = [
        card('Active', s.active_variants || 0),
        card('Eliminated', s.eliminated_variants || 0, 'negative'),
        card('Total Trades', s.total_backtested_trades || 0),
        card('Elite', tc.ELITE || 0, 'positive'),
        card('Champions', tc.CHAMPION || 0, 'positive'),
        card('Contenders', tc.CONTENDER || 0),
      ].join('');

      renderTable('top10Body', d.top10 || [], (v, i) =>
        `<tr><td>#${i+1}</td><td>${v.name}</td><td><span class="tier-badge tier-${v.tier}">${v.tier}</span></td>` +
        `<td>${v.win_rate}%</td><td class="${v.total_pnl >= 0 ? 'positive' : 'negative'}">$${v.total_pnl.toFixed(2)}</td>` +
        `<td>${v.sharpe.toFixed(2)}</td><td>${v.total_trades}</td><td>${v.generation || 0}</td></tr>`
      );

      renderTable('eliteBody', (d.tiers || {}).ELITE || [], v =>
        `<tr><td>${v.name}</td><td>${v.win_rate}%</td>` +
        `<td class="${v.total_pnl >= 0 ? 'positive' : 'negative'}">$${v.total_pnl.toFixed(2)}</td>` +
        `<td>${v.sharpe.toFixed(2)}</td><td>${v.total_trades}</td><td>$${(v.max_drawdown||0).toFixed(2)}</td></tr>`
      );

      renderTable('champBody', (d.tiers || {}).CHAMPION || [], v =>
        `<tr><td>${v.name}</td><td>${v.win_rate}%</td>` +
        `<td class="${v.total_pnl >= 0 ? 'positive' : 'negative'}">$${v.total_pnl.toFixed(2)}</td>` +
        `<td>${v.sharpe.toFixed(2)}</td><td>${v.total_trades}</td></tr>`
      );

      renderTable('graveyardBody', d.graveyard || [], v =>
        `<tr><td>${v.name}</td><td class="negative">${v.win_rate}%</td>` +
        `<td class="negative">$${v.total_pnl.toFixed(2)}</td><td>${v.total_trades}</td>` +
        `<td>WR < 35%</td></tr>`
      );

      document.getElementById('updatedAt').textContent = 'Last updated: ' + new Date(d.generated_at).toLocaleString() + ' | Auto-refreshes every 30s';
    }

    function card(label, value, cls) {
      return `<div class="stat-card"><div class="label">${label}</div><div class="value ${cls||''}">${value}</div></div>`;
    }

    function renderTable(id, items, fn) {
      const tbody = document.getElementById(id);
      if (!items.length) return;
      tbody.innerHTML = items.map((v, i) => fn(v, i)).join('');
    }

    loadData();
    setInterval(loadData, 30000);
  </script>
</body>
</html>"""


def write_dashboard():
    """Write ATM Challenge dashboard HTML."""
    path = REPO_ROOT / "trading" / "atm_dashboard.html"
    path.write_text(ATM_DASHBOARD_HTML, encoding="utf-8")
    print(f"[ATM] Dashboard written to {path}")
    return path


# ── CLI ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="ATM Challenge — Strategy Evolution Arena")
    parser.add_argument("--once", action="store_true", help="Run one cycle")
    parser.add_argument("--loop", action="store_true", help="Run continuous loop")
    parser.add_argument("--backtest-only", action="store_true", help="Backtest without trading")
    parser.add_argument("--leaderboard", action="store_true", help="Show leaderboard")
    parser.add_argument("--balance", type=float, default=1000.0, help="Starting balance")
    parser.add_argument("--interval", type=int, default=SCAN_INTERVAL_SEC, help="Loop interval (sec)")
    parser.add_argument("--symbols", type=str, default=None, help="Comma-separated symbols")
    parser.add_argument("--write-dashboard", action="store_true", help="Write dashboard HTML")
    args = parser.parse_args()

    symbols = args.symbols.split(",") if args.symbols else None

    if args.write_dashboard:
        write_dashboard()
        return

    atm = ATMChallenge(balance=args.balance)

    try:
        if args.leaderboard:
            atm.print_leaderboard()
        elif args.loop:
            atm.run_loop(interval=args.interval, symbols=symbols)
        else:
            # Default: run one cycle
            atm.run_cycle(symbols)
    finally:
        atm.close()


if __name__ == "__main__":
    main()
