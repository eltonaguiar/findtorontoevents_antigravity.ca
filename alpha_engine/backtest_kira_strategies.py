"""
KIRA Strategy Backtester -- Comprehensive Asset Class Analysis
==============================================================
Tests the 5 KIRA-inspired strategies (fractal_decay, swing_structure,
kalman_filter_trend, candle_momentum, cusum_regime) across:
  - Top 10 crypto pairs
  - Top 10 stocks
  - Top ETFs
  - Penny stocks / meme stocks
  - Scalping variants (tighter TP/SL, shorter holds)
  - Theory tests (6-red-bar continuation, historical touch points, etc.)

Outputs a JSON report + console summary with per-strategy, per-symbol metrics.
"""

from __future__ import annotations

import json
import time
import sys
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

import numpy as np
import pandas as pd

# -- Data fetching ----------------------------------------------------

DATA_DIR = Path(__file__).resolve().parent / "data"


def fetch_ohlcv(symbol: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
    """Fetch OHLCV via yfinance with parquet cache."""
    safe = symbol.replace("-", "_").replace("/", "_").replace("=", "_")
    cache_path = DATA_DIR / f"bt_cache_{safe}_{period}_{interval}.parquet"

    if cache_path.exists():
        age_h = (time.time() - cache_path.stat().st_mtime) / 3600
        if age_h < 12:
            return pd.read_parquet(cache_path)

    try:
        import yfinance as yf
        tk = yf.Ticker(symbol)
        df = tk.history(period=period, interval=interval)
        if df.empty:
            print(f"  [WARN] No data for {symbol}")
            return pd.DataFrame()
        df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        df.to_parquet(cache_path)
        return df
    except Exception as e:
        print(f"  [ERR] {symbol}: {e}")
        if cache_path.exists():
            return pd.read_parquet(cache_path)
        return pd.DataFrame()


# -- Indicator helpers (standalone, no imports needed) ----------------

def _rsi(close: np.ndarray, period: int = 14) -> np.ndarray:
    n = len(close)
    rsi_arr = np.full(n, 50.0)
    delta = np.diff(close)
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    if period >= n:
        return rsi_arr
    avg_g = np.mean(gain[:period])
    avg_l = np.mean(loss[:period])
    for i in range(period, len(delta)):
        avg_g = (avg_g * (period - 1) + gain[i]) / period
        avg_l = (avg_l * (period - 1) + loss[i]) / period
        rs = avg_g / avg_l if avg_l > 0 else 100
        rsi_arr[i + 1] = 100 - 100 / (1 + rs)
    return rsi_arr


def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    n = len(close)
    atr_arr = np.zeros(n)
    tr = np.maximum(high[1:] - low[1:],
                    np.maximum(np.abs(high[1:] - close[:-1]),
                               np.abs(low[1:] - close[:-1])))
    if period < n:
        atr_arr[period] = np.mean(tr[:period])
        for i in range(period + 1, n):
            atr_arr[i] = (atr_arr[i-1] * (period - 1) + tr[i-1]) / period
    return atr_arr


def _volume_ratio(volume: np.ndarray, period: int = 20) -> np.ndarray:
    n = len(volume)
    vr = np.ones(n)
    for i in range(period, n):
        avg = np.mean(volume[i-period:i])
        vr[i] = volume[i] / avg if avg > 0 else 1.0
    return vr


# -- Backtest engine --------------------------------------------------

@dataclass
class Trade:
    entry_idx: int
    entry_price: float
    direction: int  # 1=long, -1=short
    tp: float
    sl: float
    exit_idx: int = -1
    exit_price: float = 0.0
    pnl_pct: float = 0.0
    reason: str = ""


@dataclass
class BacktestResult:
    strategy: str
    symbol: str
    variant: str  # "normal" or "scalp"
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    sharpe: float = 0.0
    sortino: float = 0.0
    max_drawdown: float = 0.0
    total_return: float = 0.0
    avg_pnl: float = 0.0
    avg_hold: float = 0.0
    profit_factor: float = 0.0
    trades: list = field(default_factory=list)

    def to_dict(self):
        d = asdict(self)
        d.pop("trades", None)
        return d


def run_backtest(close: np.ndarray, high: np.ndarray, low: np.ndarray,
                 volume: np.ndarray, opn: np.ndarray,
                 signals: list[dict], max_hold: int = 14,
                 commission: float = 0.001) -> list[Trade]:
    """Execute signals against price data, return trades."""
    trades = []
    in_trade = False
    current_trade = None

    for sig in signals:
        idx = sig["idx"]
        direction = 1 if sig["type"] == "BUY" else -1
        entry = close[idx]
        atr_val = sig.get("atr", entry * 0.02)

        tp_mult = sig.get("tp_mult", 3.0)
        sl_mult = sig.get("sl_mult", 1.5)

        if direction == 1:
            tp = entry + tp_mult * atr_val
            sl = entry - sl_mult * atr_val
        else:
            tp = entry - tp_mult * atr_val
            sl = entry + sl_mult * atr_val

        # Walk forward to find exit
        exit_idx = min(idx + max_hold, len(close) - 1)
        exit_price = close[exit_idx]
        exit_reason = "max_hold"

        for j in range(idx + 1, min(idx + max_hold + 1, len(close))):
            if direction == 1:
                if high[j] >= tp:
                    exit_idx, exit_price, exit_reason = j, tp, "tp"
                    break
                if low[j] <= sl:
                    exit_idx, exit_price, exit_reason = j, sl, "sl"
                    break
            else:
                if low[j] <= tp:
                    exit_idx, exit_price, exit_reason = j, tp, "tp"
                    break
                if high[j] >= sl:
                    exit_idx, exit_price, exit_reason = j, sl, "sl"
                    break

        pnl = direction * (exit_price - entry) / entry - commission * 2
        trades.append(Trade(
            entry_idx=idx, entry_price=entry, direction=direction,
            tp=tp, sl=sl, exit_idx=exit_idx, exit_price=exit_price,
            pnl_pct=pnl, reason=exit_reason
        ))

    return trades


def calc_metrics(trades: list[Trade], strategy: str, symbol: str,
                 variant: str) -> BacktestResult:
    """Calculate performance metrics from trades."""
    r = BacktestResult(strategy=strategy, symbol=symbol, variant=variant)
    if not trades:
        return r

    pnls = [t.pnl_pct for t in trades]
    holds = [t.exit_idx - t.entry_idx for t in trades]

    r.total_trades = len(trades)
    r.wins = sum(1 for p in pnls if p > 0)
    r.losses = r.total_trades - r.wins
    r.win_rate = r.wins / r.total_trades if r.total_trades > 0 else 0
    r.total_return = float(np.prod([1 + p for p in pnls]) - 1)
    r.avg_pnl = float(np.mean(pnls))
    r.avg_hold = float(np.mean(holds))

    pnl_arr = np.array(pnls)
    if len(pnl_arr) > 1 and np.std(pnl_arr) > 0:
        r.sharpe = float(np.mean(pnl_arr) / np.std(pnl_arr) * np.sqrt(252 / max(np.mean(holds), 1)))
    downside = pnl_arr[pnl_arr < 0]
    if len(downside) > 0 and np.std(downside) > 0:
        r.sortino = float(np.mean(pnl_arr) / np.std(downside) * np.sqrt(252 / max(np.mean(holds), 1)))

    gross_profit = float(np.sum(pnl_arr[pnl_arr > 0]))
    gross_loss = float(np.abs(np.sum(pnl_arr[pnl_arr < 0])))
    r.profit_factor = gross_profit / gross_loss if gross_loss > 0 else 99.0

    # Max drawdown
    equity = np.cumprod([1 + p for p in pnls])
    peak = np.maximum.accumulate(equity)
    dd = (peak - equity) / peak
    r.max_drawdown = float(np.max(dd)) if len(dd) > 0 else 0

    r.trades = trades
    return r


# -- Strategy signal generators ---------------------------------------
# These operate on raw numpy arrays and return signal dicts with idx

def gen_fractal_decay(close, high, low, volume, opn,
                      depth=5, decay_period=24, sigma=0.18, mom_decay=0.41,
                      tp_mult=3.0, sl_mult=1.5):
    signals = []
    n = len(close)
    atr_arr = _atr(high, low, close)
    rsi_arr = _rsi(close)

    # Find fractals
    fractal_highs, fractal_lows = [], []
    for i in range(depth, n - depth):
        is_h = all(high[i] >= high[i-j] and high[i] >= high[i+j] for j in range(1, depth+1))
        is_l = all(low[i] <= low[i-j] and low[i] <= low[i+j] for j in range(1, depth+1))
        if is_h:
            fractal_highs.append((i, high[i]))
        if is_l:
            fractal_lows.append((i, low[i]))

    for i in range(max(decay_period + depth * 2, 50), n - depth):
        # Get fractals before this point
        fh = [(idx, v) for idx, v in fractal_highs if idx < i]
        fl = [(idx, v) for idx, v in fractal_lows if idx < i]
        if len(fh) < 2 or len(fl) < 2:
            continue

        def dw(fi):
            age = i - fi
            return np.exp(-sigma * (age / decay_period) ** 2)

        wh = sum(v * dw(idx) for idx, v in fh[-8:])
        swh = sum(dw(idx) for idx, _ in fh[-8:])
        wl = sum(v * dw(idx) for idx, v in fl[-8:])
        swl = sum(dw(idx) for idx, _ in fl[-8:])
        if swh == 0 or swl == 0:
            continue

        resistance = wh / swh
        support = wl / swl

        rets = np.diff(close[max(0,i-decay_period):i+1]) / close[max(0,i-decay_period):i][:]
        if len(rets) < 5:
            continue
        momentum = float(np.mean(rets)) * decay_period
        mf = 1.0 + mom_decay * momentum

        price = close[i]
        r = rsi_arr[i]

        if price <= support * 1.01 and mf > 1.0 and r < 45:
            signals.append({"idx": i, "type": "BUY", "atr": atr_arr[i],
                            "tp_mult": tp_mult, "sl_mult": sl_mult})
        elif price >= resistance * 0.99 and mf < 1.0 and r > 65:
            signals.append({"idx": i, "type": "SELL", "atr": atr_arr[i],
                            "tp_mult": tp_mult, "sl_mult": sl_mult})

    return signals


def gen_swing_structure(close, high, low, volume, opn,
                        lookback=5, tp_mult=3.0, sl_mult=1.5):
    signals = []
    n = len(close)
    atr_arr = _atr(high, low, close)
    rsi_arr = _rsi(close)
    vr = _volume_ratio(volume)

    swing_highs, swing_lows = [], []
    for i in range(lookback, n - lookback):
        is_sh = all(high[i] >= high[i-j] and high[i] >= high[i+j] for j in range(1, lookback+1))
        is_sl = all(low[i] <= low[i-j] and low[i] <= low[i+j] for j in range(1, lookback+1))
        if is_sh:
            swing_highs.append((i, high[i]))
        if is_sl:
            swing_lows.append((i, low[i]))

    for i in range(lookback * 4, n - lookback):
        sh = [(idx, v) for idx, v in swing_highs if idx < i]
        sl_pts = [(idx, v) for idx, v in swing_lows if idx < i]
        if len(sh) < 2 or len(sl_pts) < 2:
            continue

        sh1, sh2 = sh[-2][1], sh[-1][1]
        sl1, sl2 = sl_pts[-2][1], sl_pts[-1][1]
        hh = sh2 > sh1
        hl = sl2 > sl1
        lh = sh2 < sh1
        ll = sl2 < sl1

        price = close[i]
        r = rsi_arr[i]

        if hh and hl and price > sl2 and r < 75:
            signals.append({"idx": i, "type": "BUY", "atr": atr_arr[i],
                            "tp_mult": tp_mult, "sl_mult": sl_mult})
        elif lh and ll and price < sh2 and r > 25:
            signals.append({"idx": i, "type": "SELL", "atr": atr_arr[i],
                            "tp_mult": tp_mult, "sl_mult": sl_mult})

    return signals


def gen_kalman_filter(close, high, low, volume, opn,
                      Q=1e-5, R=0.001, tp_mult=2.5, sl_mult=1.2):
    signals = []
    n = len(close)
    atr_arr = _atr(high, low, close)
    rsi_arr = _rsi(close)

    estimates = np.zeros(n)
    estimates[0] = close[0]
    p = 1.0
    for i in range(1, n):
        pred = estimates[i-1]
        p_pred = p + Q
        k = p_pred / (p_pred + R)
        estimates[i] = pred + k * (close[i] - pred)
        p = (1 - k) * p_pred

    for i in range(30, n):
        slope = (estimates[i] - estimates[i-1]) / estimates[i-1]
        prev_above = close[i-1] > estimates[i-1]
        curr_above = close[i] > estimates[i]
        r = rsi_arr[i]

        if curr_above and not prev_above and slope > 0 and r < 65:
            signals.append({"idx": i, "type": "BUY", "atr": atr_arr[i],
                            "tp_mult": tp_mult, "sl_mult": sl_mult})
        elif not curr_above and prev_above and slope < 0 and r > 40:
            signals.append({"idx": i, "type": "SELL", "atr": atr_arr[i],
                            "tp_mult": tp_mult, "sl_mult": sl_mult})

    return signals


def gen_candle_momentum(close, high, low, volume, opn,
                        min_consec=3, body_thresh=0.6, tp_mult=2.5, sl_mult=1.2):
    signals = []
    n = len(close)
    atr_arr = _atr(high, low, close)
    rsi_arr = _rsi(close)
    vr = _volume_ratio(volume)

    for i in range(min_consec + 5, n):
        bull, bear = 0, 0
        for j in range(min_consec + 2, 0, -1):
            idx = i - j
            if idx < 0:
                continue
            rng = high[idx] - low[idx]
            if rng == 0:
                bull, bear = 0, 0
                continue
            body = abs(close[idx] - opn[idx])
            ratio = body / rng
            if ratio >= body_thresh and close[idx] > opn[idx]:
                bull += 1
                bear = 0
            elif ratio >= body_thresh and close[idx] < opn[idx]:
                bear += 1
                bull = 0
            else:
                bull, bear = 0, 0

        if vr[i] < 1.1:
            continue

        r = rsi_arr[i]
        if bull >= min_consec and r < 75:
            signals.append({"idx": i, "type": "BUY", "atr": atr_arr[i],
                            "tp_mult": tp_mult, "sl_mult": sl_mult})
        elif bear >= min_consec and r > 30:
            signals.append({"idx": i, "type": "SELL", "atr": atr_arr[i],
                            "tp_mult": tp_mult, "sl_mult": sl_mult})

    return signals


def gen_cusum_regime(close, high, low, volume, opn,
                     k_sens=0.5, h_thresh=4.0, lookback=60, tp_mult=3.0, sl_mult=1.5):
    signals = []
    n = len(close)
    atr_arr = _atr(high, low, close)
    rsi_arr = _rsi(close)
    returns = np.diff(close) / close[:-1]

    for i in range(lookback + 10, n):
        window = returns[i-lookback:i]
        mu = np.mean(window)
        sigma = np.std(window)
        if sigma == 0:
            continue

        k = k_sens * sigma
        h = h_thresh * sigma

        s_pos, s_neg = 0.0, 0.0
        pos_idx, neg_idx = None, None
        for j, r in enumerate(window):
            s_pos = max(0, s_pos + r - mu - k)
            s_neg = max(0, s_neg - r + mu - k)
            if s_pos > h:
                pos_idx = j
                s_pos = 0
            if s_neg > h:
                neg_idx = j
                s_neg = 0

        r = rsi_arr[i]
        if pos_idx is not None and pos_idx >= lookback - 5 and r < 70:
            signals.append({"idx": i, "type": "BUY", "atr": atr_arr[i],
                            "tp_mult": tp_mult, "sl_mult": sl_mult})
        elif neg_idx is not None and neg_idx >= lookback - 5 and r > 35:
            signals.append({"idx": i, "type": "SELL", "atr": atr_arr[i],
                            "tp_mult": tp_mult, "sl_mult": sl_mult})

    return signals


# -- Theory tests -----------------------------------------------------

def gen_red_bar_continuation(close, high, low, volume, opn,
                             n_bars=6, tp_mult=3.0, sl_mult=1.5):
    """Theory: N consecutive red bars → downtrend continues after pullback."""
    signals = []
    n = len(close)
    atr_arr = _atr(high, low, close)

    for i in range(n_bars + 2, n):
        # Check for N consecutive red bars ending 2 bars ago
        all_red = all(close[i-n_bars-1+j] < opn[i-n_bars-1+j] for j in range(n_bars))
        if not all_red:
            continue
        # Last bar should be a green pullback (or doji)
        if close[i-1] <= opn[i-1]:
            continue
        # Enter short on the pullback
        signals.append({"idx": i, "type": "SELL", "atr": atr_arr[i],
                        "tp_mult": tp_mult, "sl_mult": sl_mult})

    return signals


def gen_green_bar_continuation(close, high, low, volume, opn,
                               n_bars=6, tp_mult=3.0, sl_mult=1.5):
    """Theory: N consecutive green bars → uptrend continues after pullback."""
    signals = []
    n = len(close)
    atr_arr = _atr(high, low, close)

    for i in range(n_bars + 2, n):
        all_green = all(close[i-n_bars-1+j] > opn[i-n_bars-1+j] for j in range(n_bars))
        if not all_green:
            continue
        if close[i-1] >= opn[i-1]:
            continue
        signals.append({"idx": i, "type": "BUY", "atr": atr_arr[i],
                        "tp_mult": tp_mult, "sl_mult": sl_mult})

    return signals


def gen_historical_level_touch(close, high, low, volume, opn,
                               lookback=120, touch_dist=0.005, tp_mult=2.5, sl_mult=1.0):
    """Theory: price touching a historical high tends to break through or bounce."""
    signals = []
    n = len(close)
    atr_arr = _atr(high, low, close)
    rsi_arr = _rsi(close)

    for i in range(lookback + 5, n):
        hist_high = np.max(high[i-lookback:i-5])
        price = close[i]
        dist = abs(price - hist_high) / hist_high

        if dist < touch_dist:
            r = rsi_arr[i]
            vr = _volume_ratio(volume)
            # High volume at level = breakout, low volume = rejection
            if vr[i] > 1.5 and r < 75:
                signals.append({"idx": i, "type": "BUY", "atr": atr_arr[i],
                                "tp_mult": tp_mult, "sl_mult": sl_mult})
            elif vr[i] < 0.8 and r > 60:
                signals.append({"idx": i, "type": "SELL", "atr": atr_arr[i],
                                "tp_mult": tp_mult * 0.7, "sl_mult": sl_mult})

    return signals


# -- Main runner ------------------------------------------------------

STRATEGIES = {
    "fractal_decay": gen_fractal_decay,
    "swing_structure": gen_swing_structure,
    "kalman_filter": gen_kalman_filter,
    "candle_momentum": gen_candle_momentum,
    "cusum_regime": gen_cusum_regime,
}

THEORY_STRATEGIES = {
    "red_6bar_continuation": lambda c, h, l, v, o, **kw: gen_red_bar_continuation(c, h, l, v, o, n_bars=6, **kw),
    "green_6bar_continuation": lambda c, h, l, v, o, **kw: gen_green_bar_continuation(c, h, l, v, o, n_bars=6, **kw),
    "historical_level_touch": gen_historical_level_touch,
}

SCALP_OVERRIDES = {
    "tp_mult": 1.5,
    "sl_mult": 0.8,
}

# Asset universe
SYMBOLS = {
    "crypto_majors": ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
                       "ADA-USD", "AVAX-USD", "LINK-USD", "DOT-USD", "MATIC-USD"],
    "crypto_alts": ["SUI20947-USD", "TIA22861-USD", "INJ-USD", "NEAR-USD",
                     "ATOM-USD", "FIL-USD", "APT21794-USD", "SEI-USD"],
    "crypto_meme": ["DOGE-USD", "SHIB-USD", "PEPE24478-USD", "WIF-USD",
                     "BONK-USD", "FLOKI-USD"],
    "stocks_mega": ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "GOOGL",
                     "META", "AMD", "CRM", "NFLX"],
    "etfs": ["SPY", "QQQ", "IWM", "XLK", "XLF", "XLE", "GLD", "TLT",
             "ARKK", "SOXX"],
    "penny_meme": ["GME", "AMC", "PLTR", "SOFI", "RIVN", "LCID",
                    "NIO", "SNDL", "COIN", "MSTR"],
}


def run_all():
    print("=" * 80)
    print("KIRA STRATEGY BACKTESTER -- Comprehensive Asset Class Analysis")
    print(f"Started: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 80)

    all_results = []

    # Collect all unique symbols
    all_symbols = set()
    for cat_syms in SYMBOLS.values():
        all_symbols.update(cat_syms)

    # Fetch data
    print(f"\n[1/4] Fetching data for {len(all_symbols)} symbols...")
    data_cache = {}
    for sym in sorted(all_symbols):
        print(f"  Fetching {sym}...", end=" ", flush=True)
        df = fetch_ohlcv(sym, period="2y")
        if not df.empty:
            data_cache[sym] = df
            print(f"OK ({len(df)} bars)")
        else:
            print("SKIP")

    # Run backtests
    print(f"\n[2/4] Running {len(STRATEGIES)} strategies × {len(data_cache)} symbols...")
    for strat_name, strat_fn in STRATEGIES.items():
        print(f"\n{'-'*60}")
        print(f"Strategy: {strat_name}")
        print(f"{'-'*60}")

        for cat_name, cat_syms in SYMBOLS.items():
            for sym in cat_syms:
                if sym not in data_cache:
                    continue
                df = data_cache[sym]
                c = df["Close"].values.astype(float)
                h = df["High"].values.astype(float)
                l = df["Low"].values.astype(float)
                v = df["Volume"].values.astype(float)
                o = df["Open"].values.astype(float)

                # Normal variant
                try:
                    sigs = strat_fn(c, h, l, v, o)
                    if sigs:
                        trades = run_backtest(c, h, l, v, o, sigs, max_hold=14)
                        res = calc_metrics(trades, strat_name, sym, "normal")
                        res_dict = res.to_dict()
                        res_dict["asset_class"] = cat_name
                        all_results.append(res_dict)
                        wr = f"{res.win_rate*100:.1f}%"
                        print(f"  {sym:16s} [{cat_name:14s}] normal:  {res.total_trades:4d} trades | WR {wr:6s} | Sharpe {res.sharpe:+.2f} | Return {res.total_return*100:+.1f}% | PF {res.profit_factor:.2f}")
                except Exception as e:
                    print(f"  {sym:16s} [{cat_name:14s}] normal:  ERROR -- {e}")

                # Scalp variant
                try:
                    sigs = strat_fn(c, h, l, v, o, **SCALP_OVERRIDES)
                    if sigs:
                        trades = run_backtest(c, h, l, v, o, sigs, max_hold=5)
                        res = calc_metrics(trades, strat_name, sym, "scalp")
                        res_dict = res.to_dict()
                        res_dict["asset_class"] = cat_name
                        all_results.append(res_dict)
                        wr = f"{res.win_rate*100:.1f}%"
                        print(f"  {sym:16s} [{cat_name:14s}] scalp:   {res.total_trades:4d} trades | WR {wr:6s} | Sharpe {res.sharpe:+.2f} | Return {res.total_return*100:+.1f}% | PF {res.profit_factor:.2f}")
                except Exception as e:
                    pass

    # Theory tests
    print(f"\n[3/4] Running theory tests...")
    for theory_name, theory_fn in THEORY_STRATEGIES.items():
        print(f"\n{'-'*60}")
        print(f"Theory: {theory_name}")
        print(f"{'-'*60}")

        for cat_name, cat_syms in SYMBOLS.items():
            for sym in cat_syms:
                if sym not in data_cache:
                    continue
                df = data_cache[sym]
                c = df["Close"].values.astype(float)
                h = df["High"].values.astype(float)
                l = df["Low"].values.astype(float)
                v = df["Volume"].values.astype(float)
                o = df["Open"].values.astype(float)

                try:
                    sigs = theory_fn(c, h, l, v, o)
                    if sigs:
                        trades = run_backtest(c, h, l, v, o, sigs, max_hold=10)
                        res = calc_metrics(trades, theory_name, sym, "theory")
                        res_dict = res.to_dict()
                        res_dict["asset_class"] = cat_name
                        all_results.append(res_dict)
                        wr = f"{res.win_rate*100:.1f}%"
                        print(f"  {sym:16s} [{cat_name:14s}] {res.total_trades:4d} trades | WR {wr:6s} | Sharpe {res.sharpe:+.2f} | Return {res.total_return*100:+.1f}% | PF {res.profit_factor:.2f}")
                except Exception as e:
                    print(f"  {sym:16s} [{cat_name:14s}] ERROR -- {e}")

    # Analysis
    print(f"\n\n{'='*80}")
    print("[4/4] ANALYSIS SUMMARY")
    print(f"{'='*80}")

    if not all_results:
        print("No results generated!")
        return

    df_results = pd.DataFrame(all_results)

    # Best strategy-symbol combos
    print("\n\n*** TOP 20 BEST STRATEGY × SYMBOL COMBOS (by Sharpe) ***")
    print(f"{'Strategy':<28s} {'Symbol':<16s} {'Variant':<8s} {'Trades':>6s} {'WR':>7s} {'Sharpe':>7s} {'Return':>8s} {'PF':>6s} {'MaxDD':>7s}")
    print("-" * 100)
    top = df_results.nlargest(20, "sharpe")
    for _, row in top.iterrows():
        print(f"{row['strategy']:<28s} {row['symbol']:<16s} {row['variant']:<8s} "
              f"{row['total_trades']:6d} {row['win_rate']*100:6.1f}% {row['sharpe']:+6.2f} "
              f"{row['total_return']*100:+7.1f}% {row['profit_factor']:5.2f} {row['max_drawdown']*100:6.1f}%")

    # Best by win rate (min 10 trades)
    print("\n\n*** TOP 20 BY WIN RATE (min 10 trades) ***")
    filtered = df_results[df_results["total_trades"] >= 10]
    print(f"{'Strategy':<28s} {'Symbol':<16s} {'Variant':<8s} {'Trades':>6s} {'WR':>7s} {'Sharpe':>7s} {'Return':>8s} {'PF':>6s}")
    print("-" * 95)
    top_wr = filtered.nlargest(20, "win_rate")
    for _, row in top_wr.iterrows():
        print(f"{row['strategy']:<28s} {row['symbol']:<16s} {row['variant']:<8s} "
              f"{row['total_trades']:6d} {row['win_rate']*100:6.1f}% {row['sharpe']:+6.2f} "
              f"{row['total_return']*100:+7.1f}% {row['profit_factor']:5.2f}")

    # Scalp vs Normal comparison
    print("\n\n*** SCALP vs NORMAL -- Average metrics by strategy ***")
    for variant in ["normal", "scalp"]:
        subset = df_results[df_results["variant"] == variant]
        if subset.empty:
            continue
        print(f"\n  [{variant.upper()}]")
        by_strat = subset.groupby("strategy").agg({
            "win_rate": "mean", "sharpe": "mean", "total_return": "mean",
            "profit_factor": "mean", "total_trades": "mean", "max_drawdown": "mean"
        }).sort_values("sharpe", ascending=False)
        print(f"  {'Strategy':<28s} {'Avg WR':>7s} {'Avg Sharpe':>10s} {'Avg Return':>10s} {'Avg PF':>7s} {'Avg Trades':>10s}")
        for idx, row in by_strat.iterrows():
            print(f"  {idx:<28s} {row['win_rate']*100:6.1f}% {row['sharpe']:+9.2f} "
                  f"{row['total_return']*100:+9.1f}% {row['profit_factor']:6.2f} {row['total_trades']:9.0f}")

    # Best asset class per strategy
    print("\n\n*** BEST ASSET CLASS per STRATEGY ***")
    for strat in df_results["strategy"].unique():
        subset = df_results[(df_results["strategy"] == strat) & (df_results["variant"] != "theory")]
        if subset.empty:
            continue
        by_class = subset.groupby("asset_class").agg({
            "sharpe": "mean", "win_rate": "mean", "total_return": "mean",
            "profit_factor": "mean"
        }).sort_values("sharpe", ascending=False)
        best = by_class.index[0]
        s = by_class.iloc[0]
        print(f"  {strat:<28s} → {best:<16s} (Sharpe {s['sharpe']:+.2f}, WR {s['win_rate']*100:.1f}%, PF {s['profit_factor']:.2f})")

    # Theory validation
    print("\n\n*** THEORY TEST RESULTS ***")
    theories = df_results[df_results["variant"] == "theory"]
    if not theories.empty:
        for theory in theories["strategy"].unique():
            subset = theories[theories["strategy"] == theory]
            avg_wr = subset["win_rate"].mean()
            avg_sharpe = subset["sharpe"].mean()
            avg_pf = subset["profit_factor"].mean()
            total = subset["total_trades"].sum()
            print(f"\n  {theory}:")
            print(f"    Overall: {total:.0f} trades, WR {avg_wr*100:.1f}%, Sharpe {avg_sharpe:+.2f}, PF {avg_pf:.2f}")
            # Per asset class
            by_class = subset.groupby("asset_class").agg({
                "win_rate": "mean", "sharpe": "mean", "total_trades": "sum"
            }).sort_values("sharpe", ascending=False)
            for ac, row in by_class.iterrows():
                verdict = "CONFIRMED" if row["sharpe"] > 0 and row["win_rate"] > 0.5 else "MIXED" if row["win_rate"] > 0.45 else "BUSTED"
                print(f"    {ac:<16s}: WR {row['win_rate']*100:.1f}%, Sharpe {row['sharpe']:+.2f}, {row['total_trades']:.0f} trades → {verdict}")

    # Specific symbol insights
    print("\n\n*** SYMBOL-SPECIFIC INSIGHTS ***")
    for sym in ["BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD", "DOGE-USD", "NVDA", "SPY", "GME"]:
        subset = df_results[(df_results["symbol"] == sym) & (df_results["total_trades"] >= 3)]
        if subset.empty:
            continue
        best = subset.loc[subset["sharpe"].idxmax()]
        worst = subset.loc[subset["sharpe"].idxmin()]
        print(f"  {sym}:")
        print(f"    BEST:  {best['strategy']:<24s} ({best['variant']}) Sharpe {best['sharpe']:+.2f}, WR {best['win_rate']*100:.1f}%, PF {best['profit_factor']:.2f}")
        print(f"    WORST: {worst['strategy']:<24s} ({worst['variant']}) Sharpe {worst['sharpe']:+.2f}, WR {worst['win_rate']*100:.1f}%, PF {worst['profit_factor']:.2f}")

    # Save results
    out_path = DATA_DIR / "kira_backtest_results.json"
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\n\nFull results saved to: {out_path}")
    print(f"Total result rows: {len(all_results)}")


if __name__ == "__main__":
    run_all()
