"""
H-OPT-001: Momentum Options Overlay — Reverse-engineered from April 2026 live trading recap.

Live performance: 90.5% WR (21/23), $991,538 net, TSLA+SPX primary.

Signal logic:
  1. Directional bias: 5d return vs 20d rolling average + RSI(14) + ATR(14)
  2. IV rank gate: high IV → sell premium (SHRTOPT); low IV → buy spreads
  3. Structure selection matrix (see _select_structure)
  4. Kelly ¼-fraction sizing with ½-Kelly drawdown brake

Pre-registered as H-OPT-001 in reports/hypothesis_registry.json (2026-05-19).
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    import yfinance as yf
    import pandas as pd
    import numpy as np
    DEPS_OK = True
except ImportError:
    DEPS_OK = False


# ── Structures ──────────────────────────────────────────────────────────────

STRUCTURES = (
    "bull_call_spread",
    "bear_put_spread",
    "covered_call",
    "married_put",
    "protective_collar",
    "shrtopt",          # short premium — sell calls/puts outright
    "long_call",
    "long_put",
)


@dataclass
class Signal:
    symbol: str
    date: str
    close: float
    ret5d: float          # 5-day return
    rolling_avg30d: float # 30-day rolling average of daily returns
    rsi14: float
    atr14: float
    iv_rank: float        # 0-100; estimated from HV ratio when real IV unavailable
    has_existing_long: bool = False
    unrealized_gain_pct: float = 0.0


@dataclass
class Trade:
    symbol: str
    date: str
    structure: str
    direction: str        # BULLISH / BEARISH / NEUTRAL
    conviction: float     # 0.0-1.0
    kelly_size: float     # fraction of account
    win: Optional[bool] = None
    pnl_pct: Optional[float] = None
    notes: str = ""


@dataclass
class BacktestResult:
    symbol: str
    period: str
    n_trades: int = 0
    n_wins: int = 0
    gross_pnl: float = 0.0
    trades: list[Trade] = field(default_factory=list)

    @property
    def win_rate(self) -> float:
        return self.n_wins / self.n_trades if self.n_trades else 0.0

    @property
    def profit_factor(self) -> float:
        wins = sum(t.pnl_pct for t in self.trades if t.pnl_pct and t.pnl_pct > 0)
        losses = abs(sum(t.pnl_pct for t in self.trades if t.pnl_pct and t.pnl_pct < 0))
        return wins / losses if losses > 0 else float("inf")


# ── Signal computation ───────────────────────────────────────────────────────

def _rsi(prices: "pd.Series", period: int = 14) -> "pd.Series":
    delta = prices.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, float("nan"))
    return 100 - (100 / (1 + rs))


def _atr(high: "pd.Series", low: "pd.Series", close: "pd.Series", period: int = 14) -> "pd.Series":
    tr = pd.concat([high - low,
                    (high - close.shift()).abs(),
                    (low - close.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def _iv_rank_proxy(close: "pd.Series", window: int = 252) -> "pd.Series":
    """Proxy IV rank from 30d HV relative to its 1-year range."""
    hv30 = close.pct_change().rolling(30).std() * math.sqrt(252) * 100
    hv_min = hv30.rolling(window).min()
    hv_max = hv30.rolling(window).max()
    return ((hv30 - hv_min) / (hv_max - hv_min).replace(0, float("nan")) * 100).clip(0, 100)


def compute_signals(df: "pd.DataFrame") -> "pd.DataFrame":
    """Add indicator columns to an OHLCV DataFrame."""
    c = df["Close"]
    df["ret5d"] = c.pct_change(5) * 100
    df["rolling_avg30d"] = c.pct_change().rolling(30).mean() * 100
    df["rsi14"] = _rsi(c)
    df["atr14"] = _atr(df["High"], df["Low"], c)
    df["iv_rank"] = _iv_rank_proxy(c)
    return df


# ── Structure selection ──────────────────────────────────────────────────────

def _select_structure(sig: Signal) -> tuple[str, str, float]:
    """
    Return (structure, direction, conviction 0-1).

    Matrix reverse-engineered from April 2026 trade recap:
      - Momentum strong bullish (ret5d > rolling_avg30d + 0.5*ATR%) + RSI<70 → bull_call_spread
      - Strong bullish + existing long + IV_rank<40 → married_put (protect profit)
      - Strong bullish + existing long + IV_rank≥40 → covered_call (sell premium)
      - Large unrealized gain (>15%) → protective_collar
      - Strong bearish (ret5d < rolling_avg30d - 0.5*ATR%) + RSI>30 → bear_put_spread
      - High IV rank (≥65) + |ret5d - rolling_avg30d| < atr_pct → shrtopt (neutral)
      - Default: long_call (mild bullish) or long_put (mild bearish)
    """
    atr_pct = (sig.atr14 / sig.close) * 100 if sig.close else 1.0
    momentum_delta = sig.ret5d - sig.rolling_avg30d
    strong_bullish = momentum_delta > 0.5 * atr_pct and sig.rsi14 < 70
    strong_bearish = momentum_delta < -0.5 * atr_pct and sig.rsi14 > 30
    neutral_high_iv = sig.iv_rank >= 65 and abs(momentum_delta) < atr_pct

    if sig.unrealized_gain_pct >= 15.0:
        return "protective_collar", "BULLISH", 0.70

    if strong_bullish:
        if sig.has_existing_long:
            if sig.iv_rank < 40:
                return "married_put", "BULLISH", 0.75
            else:
                return "covered_call", "BULLISH", 0.65
        conviction = min(0.90, 0.55 + momentum_delta / (5 * atr_pct))
        return "bull_call_spread", "BULLISH", conviction

    if strong_bearish:
        conviction = min(0.85, 0.55 + abs(momentum_delta) / (5 * atr_pct))
        return "bear_put_spread", "BEARISH", conviction

    if neutral_high_iv:
        return "shrtopt", "NEUTRAL", 0.60

    if momentum_delta > 0:
        return "long_call", "BULLISH", 0.45
    return "long_put", "BEARISH", 0.45


# ── Kelly sizing ─────────────────────────────────────────────────────────────

def kelly_size(win_rate: float, avg_win: float, avg_loss: float,
               fraction: float = 0.25) -> float:
    """Kelly ¼-fraction. Returns fraction of account to risk."""
    if avg_loss == 0:
        return 0.0
    b = avg_win / avg_loss
    k = (b * win_rate - (1 - win_rate)) / b
    return max(0.0, min(k * fraction, 0.10))  # cap at 10% per trade


# ── Simplified P&L model ─────────────────────────────────────────────────────

_PNL_BY_STRUCTURE = {
    "bull_call_spread": {"win": 0.42, "loss": -0.35},   # max profit/loss on spread
    "bear_put_spread":  {"win": 0.40, "loss": -0.35},
    "covered_call":     {"win": 0.08, "loss": -0.12},   # premium collected
    "married_put":      {"win": 0.25, "loss": -0.07},   # downside capped
    "protective_collar":{"win": 0.10, "loss": -0.05},   # range-bound
    "shrtopt":          {"win": 0.12, "loss": -0.45},   # premium vs assignment
    "long_call":        {"win": 0.80, "loss": -1.00},   # binary
    "long_put":         {"win": 0.80, "loss": -1.00},
}

def _simulate_pnl(structure: str, direction: str, forward_ret5d: float) -> float:
    """Simplified PnL given the realised 5-day forward return."""
    payoff = _PNL_BY_STRUCTURE.get(structure, {"win": 0.30, "loss": -0.30})
    if direction == "BULLISH":
        win = forward_ret5d > 0
    elif direction == "BEARISH":
        win = forward_ret5d < 0
    else:  # NEUTRAL / shrtopt — wins when move < ATR
        win = abs(forward_ret5d) < 2.0
    return payoff["win"] if win else payoff["loss"]


# ── Backtest ─────────────────────────────────────────────────────────────────

def backtest(symbol: str = "TSLA",
             start: str = "2024-01-01",
             end: str = "2026-04-30",
             min_score: float = 0.45) -> BacktestResult:
    """Run the H-OPT-001 momentum overlay on historical OHLCV data."""
    if not DEPS_OK:
        raise ImportError("yfinance, pandas, numpy required: pip install yfinance pandas numpy")

    ticker = yf.Ticker(symbol)
    raw = ticker.history(start=start, end=end, auto_adjust=True)
    if raw.empty:
        raise ValueError(f"No data returned for {symbol}")

    df = compute_signals(raw.copy())
    df.dropna(inplace=True)

    result = BacktestResult(symbol=symbol, period=f"{start}→{end}")
    wr_estimate = 0.60  # prior estimate for Kelly; updated rolling
    avg_win, avg_loss = 0.40, 0.35

    for i in range(len(df) - 5):
        row = df.iloc[i]
        fwd_row = df.iloc[i + 5]
        sig = Signal(
            symbol=symbol,
            date=str(row.name.date()),
            close=float(row["Close"]),
            ret5d=float(row["ret5d"]),
            rolling_avg30d=float(row["rolling_avg30d"]),
            rsi14=float(row["rsi14"]),
            atr14=float(row["atr14"]),
            iv_rank=float(row["iv_rank"]),
        )
        structure, direction, conviction = _select_structure(sig)
        if conviction < min_score:
            continue

        ks = kelly_size(wr_estimate, avg_win, avg_loss)
        forward_ret = float(fwd_row["ret5d"])
        pnl = _simulate_pnl(structure, direction, forward_ret)

        trade = Trade(
            symbol=symbol,
            date=sig.date,
            structure=structure,
            direction=direction,
            conviction=round(conviction, 3),
            kelly_size=round(ks, 4),
            win=(pnl > 0),
            pnl_pct=round(pnl * 100, 2),
        )
        result.trades.append(trade)
        result.n_trades += 1
        if pnl > 0:
            result.n_wins += 1
        result.gross_pnl += pnl

        # rolling Kelly update
        if result.n_trades >= 10:
            wr_estimate = result.win_rate

    return result


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="H-OPT-001 momentum options overlay backtest")
    parser.add_argument("--symbol", default="TSLA")
    parser.add_argument("--start", default="2024-01-01")
    parser.add_argument("--end", default="2026-04-30")
    parser.add_argument("--min-conviction", type=float, default=0.45)
    parser.add_argument("--out", help="Write JSON results to file")
    args = parser.parse_args()

    print(f"Running H-OPT-001 backtest: {args.symbol} {args.start}→{args.end}")
    result = backtest(args.symbol, args.start, args.end, args.min_conviction)

    print(f"\n{'='*50}")
    print(f"Symbol:       {result.symbol}")
    print(f"Period:       {result.period}")
    print(f"Trades:       {result.n_trades}")
    print(f"Win rate:     {result.win_rate:.1%}")
    print(f"Profit factor:{result.profit_factor:.2f}")
    print(f"Gross PnL:    {result.gross_pnl:+.2f} (in units of avg premium)")
    print(f"{'='*50}")

    # Structure breakdown
    from collections import Counter
    structs = Counter(t.structure for t in result.trades)
    wins_by = {s: sum(1 for t in result.trades if t.structure == s and t.win) for s in structs}
    print("\nStructure breakdown:")
    for s, n in structs.most_common():
        wr = wins_by[s] / n if n else 0
        print(f"  {s:<25} n={n:3d}  WR={wr:.0%}")

    if args.out:
        out = {
            "symbol": result.symbol,
            "period": result.period,
            "n_trades": result.n_trades,
            "win_rate": round(result.win_rate, 4),
            "profit_factor": round(result.profit_factor, 4),
            "gross_pnl": round(result.gross_pnl, 4),
            "trades": [asdict(t) for t in result.trades],
        }
        Path(args.out).write_text(json.dumps(out, indent=2))
        print(f"\nResults written to {args.out}")


if __name__ == "__main__":
    main()
