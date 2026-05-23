"""Shared backtesting engine for mutation lab.

Runs strategy mutations against historical Binance klines and
computes performance metrics (win rate, Sharpe, profit factor, etc.).
"""

from __future__ import annotations
import hashlib
import logging
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Callable

import numpy as np
import pandas as pd
import requests

logger = logging.getLogger(__name__)

BINANCE_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://data-api.binance.vision",
]

BACKTEST_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

# Backtest configuration
INITIAL_CAPITAL = 10_000.0
POSITION_SIZE_PCT = 0.10
COMMISSION_PCT = 0.001      # 0.1% per side
SLIPPAGE_PCT = 0.0005       # 0.05% per side
MAX_HOLD_BARS = 15
KLINE_LIMIT = 750
KLINE_INTERVAL = "4h"


@dataclass
class BacktestResult:
    strategy_name: str
    symbol: str
    win_rate: float = 0.0
    sharpe_ratio: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    total_return: float = 0.0
    num_trades: int = 0
    avg_trade: float = 0.0
    wins: int = 0
    losses: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MutationGenes:
    """Strategy parameters that can be mutated."""
    name: str
    rsi_period: int = 14
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
    ema_fast: int = 9
    ema_slow: int = 21
    ema_trend: int = 50
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    bb_period: int = 20
    bb_std: float = 2.0
    atr_period: int = 14
    tp_atr_mult: float = 2.0
    sl_atr_mult: float = 1.5
    vol_threshold: float = 1.5
    confidence_base: float = 0.5
    invert_signals: bool = False
    extra: dict = field(default_factory=dict)

    @property
    def dna_hash(self) -> str:
        """Unique hash of gene values."""
        gene_str = f"{self.rsi_period}:{self.rsi_oversold}:{self.rsi_overbought}:" \
                   f"{self.ema_fast}:{self.ema_slow}:{self.macd_fast}:{self.macd_slow}:" \
                   f"{self.bb_period}:{self.bb_std}:{self.tp_atr_mult}:{self.sl_atr_mult}:" \
                   f"{self.vol_threshold}:{self.invert_signals}"
        return hashlib.sha256(gene_str.encode()).hexdigest()[:12]

    def tp_sl_valid(self) -> bool:
        """Pre-filter: TP must exceed SL by at least 1.2x."""
        if self.tp_atr_mult <= 0 or self.sl_atr_mult <= 0:
            return False
        return (self.tp_atr_mult / self.sl_atr_mult) >= 1.2

    def params_valid(self) -> bool:
        """Pre-filter: no degenerate parameters."""
        return (
            self.rsi_period > 1 and
            self.ema_fast > 0 and self.ema_slow > self.ema_fast and
            self.macd_fast > 0 and self.macd_slow > self.macd_fast and
            self.bb_period > 1 and self.bb_std > 0 and
            self.atr_period > 1 and
            self.tp_sl_valid()
        )


def fetch_klines(symbol: str, interval: str = KLINE_INTERVAL,
                 limit: int = KLINE_LIMIT) -> pd.DataFrame | None:
    """Fetch OHLCV from Binance with mirror rotation."""
    for base in BINANCE_MIRRORS:
        try:
            url = f"{base}/api/v3/klines"
            resp = requests.get(url, params={
                "symbol": symbol, "interval": interval, "limit": limit
            }, headers={"User-Agent": "MutationLab/1.0"}, timeout=10)
            resp.raise_for_status()
            raw = resp.json()

            df = pd.DataFrame(raw, columns=[
                "open_time", "Open", "High", "Low", "Close", "Volume",
                "close_time", "qav", "num_trades", "taker_buy_base",
                "taker_buy_quote", "ignore"
            ])
            for col in ("Open", "High", "Low", "Close", "Volume"):
                df[col] = pd.to_numeric(df[col])
            df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
            df.set_index("open_time", inplace=True)
            return df[["Open", "High", "Low", "Close", "Volume"]]
        except Exception as e:
            logger.debug(f"Mirror {base} failed for {symbol}: {e}")
            continue
    logger.error(f"All Binance mirrors failed for {symbol}")
    return None


def compute_indicators(df: pd.DataFrame, genes: MutationGenes) -> pd.DataFrame:
    """Compute technical indicators based on mutation genes."""
    df = df.copy()

    # RSI
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0).rolling(genes.rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(genes.rsi_period).mean()
    rs = gain / loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))

    # EMAs
    df["EMA_fast"] = df["Close"].ewm(span=genes.ema_fast, adjust=False).mean()
    df["EMA_slow"] = df["Close"].ewm(span=genes.ema_slow, adjust=False).mean()
    df["EMA_trend"] = df["Close"].ewm(span=genes.ema_trend, adjust=False).mean()

    # MACD
    ema_f = df["Close"].ewm(span=genes.macd_fast, adjust=False).mean()
    ema_s = df["Close"].ewm(span=genes.macd_slow, adjust=False).mean()
    df["MACD"] = ema_f - ema_s
    df["MACD_signal"] = df["MACD"].ewm(span=genes.macd_signal, adjust=False).mean()
    df["MACD_hist"] = df["MACD"] - df["MACD_signal"]

    # Bollinger Bands
    df["BB_mid"] = df["Close"].rolling(genes.bb_period).mean()
    bb_std = df["Close"].rolling(genes.bb_period).std()
    df["BB_upper"] = df["BB_mid"] + genes.bb_std * bb_std
    df["BB_lower"] = df["BB_mid"] - genes.bb_std * bb_std
    df["BB_pctb"] = (df["Close"] - df["BB_lower"]) / (df["BB_upper"] - df["BB_lower"]).replace(0, np.nan)

    # ATR
    tr = pd.concat([
        df["High"] - df["Low"],
        (df["High"] - df["Close"].shift()).abs(),
        (df["Low"] - df["Close"].shift()).abs()
    ], axis=1).max(axis=1)
    df["ATR"] = tr.rolling(genes.atr_period).mean()

    # Volume ratio
    df["Vol_ratio"] = df["Volume"] / df["Volume"].rolling(20).mean().replace(0, np.nan)

    # OBV
    obv = (np.sign(df["Close"].diff()) * df["Volume"]).fillna(0).cumsum()
    df["OBV"] = obv

    return df


def generate_signals(df: pd.DataFrame, genes: MutationGenes) -> list[dict]:
    """Generate buy/sell signals from indicator data and gene parameters."""
    signals = []
    in_position = False

    for i in range(max(genes.ema_trend, genes.bb_period, 50), len(df)):
        if in_position:
            continue

        row = df.iloc[i]
        close = row["Close"]
        atr = row.get("ATR", 0)

        if pd.isna(atr) or atr <= 0 or close <= 0:
            continue

        # Composite signal scoring
        score = 0.0

        # Momentum signals
        if row.get("MACD_hist", 0) > 0:
            score += 0.15
        if row.get("EMA_fast", 0) > row.get("EMA_slow", 0):
            score += 0.12
        rsi = row.get("RSI", 50)
        if genes.rsi_oversold < rsi < 50:
            score += 0.10  # recovering from oversold

        # Mean reversion signals
        bb_pctb = row.get("BB_pctb", 0.5)
        if not pd.isna(bb_pctb) and bb_pctb < 0.2:
            score += 0.12
        if rsi < genes.rsi_oversold:
            score += 0.15

        # Volume confirmation
        vol_ratio = row.get("Vol_ratio", 1.0)
        if not pd.isna(vol_ratio) and vol_ratio > genes.vol_threshold:
            score += 0.10

        # Trend filter
        if close > row.get("EMA_trend", close):
            score += 0.08

        # MACD crossover
        if i > 0:
            prev_hist = df.iloc[i - 1].get("MACD_hist", 0)
            curr_hist = row.get("MACD_hist", 0)
            if prev_hist < 0 and curr_hist > 0:
                score += 0.12  # bullish crossover
            elif prev_hist > 0 and curr_hist < 0:
                score -= 0.08  # bearish crossover

        # Determine direction
        direction = "BUY"
        if genes.invert_signals:
            score = -score
            if score < 0:
                direction = "SELL"
                score = abs(score)

        confidence = min(0.95, genes.confidence_base + score)

        if confidence >= 0.50:
            tp = close + genes.tp_atr_mult * atr if direction == "BUY" else close - genes.tp_atr_mult * atr
            sl = close - genes.sl_atr_mult * atr if direction == "BUY" else close + genes.sl_atr_mult * atr

            signals.append({
                "bar_index": i,
                "direction": direction,
                "entry_price": close,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(confidence, 4),
            })
            in_position = True
            # Release after MAX_HOLD_BARS
            release_bar = min(i + MAX_HOLD_BARS, len(df) - 1)
            # Simple: allow next signal after hold period
            # (actual exit logic in backtest_mutation)

    return signals


def backtest_mutation(df: pd.DataFrame, genes: MutationGenes) -> BacktestResult:
    """Run a full backtest of a mutation on a single symbol's data."""
    df = compute_indicators(df, genes)
    equity = INITIAL_CAPITAL
    peak_equity = equity
    max_dd = 0.0
    trades = []

    position = None  # {direction, entry, tp, sl, entry_bar}

    for i in range(max(genes.ema_trend, genes.bb_period, 50), len(df)):
        row = df.iloc[i]
        high = row["High"]
        low = row["Low"]
        close = row["Close"]

        # Check exits first
        if position is not None:
            bars_held = i - position["entry_bar"]
            exit_price = None
            exit_reason = None

            if position["direction"] == "BUY":
                if low <= position["sl"]:
                    exit_price = position["sl"] * (1 - SLIPPAGE_PCT)
                    exit_reason = "SL"
                elif high >= position["tp"]:
                    exit_price = position["tp"] * (1 - SLIPPAGE_PCT)
                    exit_reason = "TP"
                elif bars_held >= MAX_HOLD_BARS:
                    exit_price = close * (1 - SLIPPAGE_PCT)
                    exit_reason = "TIME"
            else:  # SELL/SHORT
                if high >= position["sl"]:
                    exit_price = position["sl"] * (1 + SLIPPAGE_PCT)
                    exit_reason = "SL"
                elif low <= position["tp"]:
                    exit_price = position["tp"] * (1 + SLIPPAGE_PCT)
                    exit_reason = "TP"
                elif bars_held >= MAX_HOLD_BARS:
                    exit_price = close * (1 + SLIPPAGE_PCT)
                    exit_reason = "TIME"

            if exit_price is not None:
                pos_size = equity * POSITION_SIZE_PCT
                if position["direction"] == "BUY":
                    pnl = pos_size * ((exit_price - position["entry"]) / position["entry"])
                else:
                    pnl = pos_size * ((position["entry"] - exit_price) / position["entry"])
                pnl -= pos_size * COMMISSION_PCT  # exit commission
                equity += pnl
                peak_equity = max(peak_equity, equity)
                dd = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0
                max_dd = max(max_dd, dd)
                trades.append({"pnl": pnl, "pnl_pct": pnl / pos_size if pos_size > 0 else 0,
                               "reason": exit_reason})
                position = None

        # Check entries
        if position is None:
            atr = row.get("ATR", 0)
            if pd.isna(atr) or atr <= 0 or close <= 0:
                continue

            score = 0.0
            if row.get("MACD_hist", 0) > 0:
                score += 0.15
            if row.get("EMA_fast", 0) > row.get("EMA_slow", 0):
                score += 0.12
            rsi = row.get("RSI", 50)
            if not pd.isna(rsi) and genes.rsi_oversold < rsi < 50:
                score += 0.10
            bb_pctb = row.get("BB_pctb", 0.5)
            if not pd.isna(bb_pctb) and bb_pctb < 0.2:
                score += 0.12
            if not pd.isna(rsi) and rsi < genes.rsi_oversold:
                score += 0.15
            vol_ratio = row.get("Vol_ratio", 1.0)
            if not pd.isna(vol_ratio) and vol_ratio > genes.vol_threshold:
                score += 0.10
            if close > row.get("EMA_trend", close):
                score += 0.08

            if i > 0:
                prev_hist = df.iloc[i - 1].get("MACD_hist", 0)
                curr_hist = row.get("MACD_hist", 0)
                if not pd.isna(prev_hist) and not pd.isna(curr_hist):
                    if prev_hist < 0 and curr_hist > 0:
                        score += 0.12

            direction = "BUY"
            if genes.invert_signals:
                score = -score
                if score < 0:
                    direction = "SELL"
                    score = abs(score)

            confidence = genes.confidence_base + score
            if confidence >= 0.50:
                entry = close * (1 + SLIPPAGE_PCT) if direction == "BUY" else close * (1 - SLIPPAGE_PCT)
                equity -= equity * POSITION_SIZE_PCT * COMMISSION_PCT  # entry commission

                if direction == "BUY":
                    tp = entry + genes.tp_atr_mult * atr
                    sl = entry - genes.sl_atr_mult * atr
                else:
                    tp = entry - genes.tp_atr_mult * atr
                    sl = entry + genes.sl_atr_mult * atr

                position = {"direction": direction, "entry": entry,
                            "tp": tp, "sl": sl, "entry_bar": i}

    # Compute metrics
    if not trades:
        return BacktestResult(strategy_name=genes.name, symbol="")

    wins = sum(1 for t in trades if t["pnl"] > 0)
    losses = len(trades) - wins
    gross_profit = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    gross_loss = abs(sum(t["pnl"] for t in trades if t["pnl"] <= 0))
    pnl_pcts = [t["pnl_pct"] for t in trades]
    mean_pnl = np.mean(pnl_pcts) if pnl_pcts else 0
    std_pnl = np.std(pnl_pcts) if len(pnl_pcts) > 1 else 1

    return BacktestResult(
        strategy_name=genes.name,
        symbol="",
        win_rate=wins / len(trades) if trades else 0,
        sharpe_ratio=(mean_pnl / std_pnl * np.sqrt(252 * 24)) if std_pnl > 0 else 0,
        profit_factor=gross_profit / gross_loss if gross_loss > 0 else 10.0,
        max_drawdown=max_dd,
        total_return=(equity - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100,
        num_trades=len(trades),
        avg_trade=mean_pnl,
        wins=wins,
        losses=losses,
    )


def backtest_on_all_symbols(genes: MutationGenes,
                            symbols: list[str] | None = None,
                            market_data: dict[str, pd.DataFrame] | None = None,
                            ) -> dict:
    """Backtest a mutation across multiple symbols. Returns aggregate results."""
    symbols = symbols or BACKTEST_SYMBOLS
    results = []

    for sym in symbols:
        if market_data and sym in market_data:
            df = market_data[sym]
        else:
            df = fetch_klines(sym)
        if df is None or len(df) < 100:
            logger.warning(f"Skipping {sym}: insufficient data")
            continue

        result = backtest_mutation(df, genes)
        result.symbol = sym
        results.append(result)

    if not results:
        return {"passed": False, "reason": "no_data", "results": [],
                "aggregate": {}}

    # Aggregate
    total_trades = sum(r.num_trades for r in results)
    total_wins = sum(r.wins for r in results)
    profitable_symbols = sum(1 for r in results if r.total_return > 0)
    avg_wr = total_wins / total_trades if total_trades > 0 else 0
    avg_sharpe = np.mean([r.sharpe_ratio for r in results])
    avg_pf = np.mean([r.profit_factor for r in results])
    worst_dd = max(r.max_drawdown for r in results)
    avg_return = np.mean([r.total_return for r in results])
    avg_trade = np.mean([r.avg_trade for r in results])

    aggregate = {
        "win_rate": round(avg_wr, 4),
        "sharpe_ratio": round(avg_sharpe, 2),
        "profit_factor": round(avg_pf, 2),
        "max_drawdown": round(worst_dd, 4),
        "total_return": round(avg_return, 2),
        "num_trades": total_trades,
        "avg_trade": round(avg_trade, 6),
        "profitable_symbols": profitable_symbols,
        "total_symbols": len(results),
    }

    # Quality gates (per spec: WR>=45%, Sharpe>=0.5, max_dd<20%, min_trades>=5)
    passed = (
        avg_wr >= 0.45 and
        avg_sharpe >= 0.5 and
        avg_pf >= 1.0 and
        total_trades >= 5 and
        worst_dd <= 0.20 and
        avg_trade > 0 and
        profitable_symbols >= 1
    )

    return {
        "passed": passed,
        "reason": "passed" if passed else _fail_reason(aggregate),
        "results": [r.to_dict() for r in results],
        "aggregate": aggregate,
    }


def _fail_reason(agg: dict) -> str:
    reasons = []
    if agg["win_rate"] < 0.45:
        reasons.append(f"WR={agg['win_rate']:.1%}<45%")
    if agg["sharpe_ratio"] < 0.5:
        reasons.append(f"Sharpe={agg['sharpe_ratio']:.1f}<0.5")
    if agg["profit_factor"] < 1.0:
        reasons.append(f"PF={agg['profit_factor']:.1f}<1.0")
    if agg["num_trades"] < 5:
        reasons.append(f"Trades={agg['num_trades']}<5")
    if agg["max_drawdown"] > 0.20:
        reasons.append(f"DD={agg['max_drawdown']:.1%}>20%")
    if agg["avg_trade"] <= 0:
        reasons.append("NegExpectancy")
    if agg["profitable_symbols"] < 1:
        reasons.append(f"ProfSymbols={agg['profitable_symbols']}<1")
    return "; ".join(reasons) or "unknown"
