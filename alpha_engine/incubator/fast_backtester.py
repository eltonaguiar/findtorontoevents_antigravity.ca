"""
Incubator — Fast Vectorised Backtester
========================================
Runs permutations against BTC-USD, ETH-USD, SOL-USD, BNB-USD & XRP-USD
historical data using fully vectorised NumPy operations (no per-bar loops).

Supports:
  - ATR-based TP/SL
  - Percentage-based TP/SL
  - Trailing stops
  - Max hold time expiry
  - Slippage & commission modeling (for large-scale mode)

Performance target: ~500 permutations/second on single core.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from .permutation_engine import Permutation

ENGINE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ENGINE_DIR / "data"


@dataclass
class BacktestResult:
    """Results from backtesting a single permutation on a single symbol."""
    perm_id: str
    archetype: str
    symbol: str
    params: dict
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    sharpe: float = 0.0
    sortino: float = 0.0
    max_drawdown: float = 0.0
    profit_factor: float = 0.0
    total_return: float = 0.0
    avg_trade_pnl: float = 0.0
    avg_hold_bars: float = 0.0
    pnl_series: list[float] = field(default_factory=list)
    equity_curve: list[float] = field(default_factory=list)
    seed_strategy: str = ""

    def to_dict(self) -> dict:
        return {
            "perm_id": self.perm_id,
            "archetype": self.archetype,
            "symbol": self.symbol,
            "params": self.params,
            "total_trades": self.total_trades,
            "wins": self.wins,
            "losses": self.losses,
            "win_rate": round(self.win_rate, 4),
            "sharpe": round(self.sharpe, 3),
            "sortino": round(self.sortino, 3),
            "max_drawdown": round(self.max_drawdown, 6),
            "profit_factor": round(self.profit_factor, 3),
            "total_return": round(self.total_return, 6),
            "avg_trade_pnl": round(self.avg_trade_pnl, 6),
            "avg_hold_bars": round(self.avg_hold_bars, 1),
            "seed_strategy": self.seed_strategy,
        }


def fetch_ohlcv(symbol: str, period: str = "1y") -> pd.DataFrame:
    """Fetch OHLCV data via yfinance. Cached in DATA_DIR as parquet."""
    cache_path = DATA_DIR / f"cache_{symbol.replace('-', '_').replace('=', '_')}_{period}.parquet"

    if cache_path.exists():
        age_hours = (time.time() - cache_path.stat().st_mtime) / 3600
        if age_hours < 12:  # use cache if < 12h old
            return pd.read_parquet(cache_path)

    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval="1d")
        if df.empty:
            print(f"[backtester] WARNING: No data for {symbol}")
            return pd.DataFrame()
        # Standardize columns
        df.columns = [c.lower() for c in df.columns]
        df = df[["open", "high", "low", "close", "volume"]].dropna()
        # Cache
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        df.to_parquet(cache_path)
        return df
    except Exception as e:
        print(f"[backtester] Error fetching {symbol}: {e}")
        # Try loading stale cache
        if cache_path.exists():
            return pd.read_parquet(cache_path)
        return pd.DataFrame()


def compute_indicators(df: pd.DataFrame, params: dict) -> dict[str, np.ndarray]:
    """Pre-compute all indicators needed for signal generation."""
    close = df["close"].values.astype(float)
    high = df["high"].values.astype(float)
    low = df["low"].values.astype(float)
    volume = df["volume"].values.astype(float)
    n = len(close)

    indicators: dict[str, np.ndarray] = {
        "close": close, "high": high, "low": low, "volume": volume,
    }

    # ATR
    atr_period = params.get("atr_period", 14)
    tr = np.maximum(
        high[1:] - low[1:],
        np.maximum(
            np.abs(high[1:] - close[:-1]),
            np.abs(low[1:] - close[:-1])
        )
    )
    atr_arr = np.zeros(n)
    atr_arr[atr_period] = np.mean(tr[:atr_period])
    for i in range(atr_period + 1, n):
        atr_arr[i] = (atr_arr[i-1] * (atr_period - 1) + tr[i-1]) / atr_period
    indicators["atr"] = atr_arr

    # RSI
    rsi_period = params.get("rsi_period", params.get("stoch_period", 14))
    delta = np.diff(close)
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    rsi_arr = np.full(n, 50.0)
    if rsi_period < n:
        avg_gain = np.mean(gain[:rsi_period])
        avg_loss = np.mean(loss[:rsi_period])
        for i in range(rsi_period, len(delta)):
            avg_gain = (avg_gain * (rsi_period - 1) + gain[i]) / rsi_period
            avg_loss = (avg_loss * (rsi_period - 1) + loss[i]) / rsi_period
            rs = avg_gain / avg_loss if avg_loss > 0 else 100
            rsi_arr[i + 1] = 100 - 100 / (1 + rs)
    indicators["rsi"] = rsi_arr

    # SMAs
    for period in [20, 50, 100, 200]:
        if period <= n:
            sma = np.full(n, np.nan)
            cumsum = np.cumsum(close)
            sma[period-1:] = (cumsum[period-1:] - np.concatenate([[0], cumsum[:-period]])) / period
            indicators[f"sma_{period}"] = sma

    # EMAs
    for period in [9, 21, 50]:
        if period <= n:
            ema_arr = np.full(n, np.nan)
            ema_arr[period-1] = np.mean(close[:period])
            mult = 2 / (period + 1)
            for i in range(period, n):
                ema_arr[i] = close[i] * mult + ema_arr[i-1] * (1 - mult)
            indicators[f"ema_{period}"] = ema_arr

    # Bollinger Bands
    bb_period = params.get("bb_period", 20)
    bb_std = params.get("bb_std", 2.0)
    if bb_period <= n:
        sma_bb = indicators.get(f"sma_{bb_period}")
        if sma_bb is None:
            sma_bb = np.full(n, np.nan)
            cumsum = np.cumsum(close)
            sma_bb[bb_period-1:] = (cumsum[bb_period-1:] - np.concatenate([[0], cumsum[:-bb_period]])) / bb_period
        std_arr = np.full(n, np.nan)
        for i in range(bb_period - 1, n):
            std_arr[i] = np.std(close[i-bb_period+1:i+1])
        indicators["bb_upper"] = sma_bb + bb_std * std_arr
        indicators["bb_lower"] = sma_bb - bb_std * std_arr
        indicators["bb_mid"] = sma_bb
        indicators["bb_width"] = np.where(sma_bb > 0, (indicators["bb_upper"] - indicators["bb_lower"]) / sma_bb, 0)

    # Volume ratio (vs 20-bar SMA)
    if n > 20:
        vol_sma = np.full(n, np.nan)
        vol_cumsum = np.cumsum(volume)
        vol_sma[19:] = (vol_cumsum[19:] - np.concatenate([[0], vol_cumsum[:-20]])) / 20
        indicators["volume_ratio"] = np.where(vol_sma > 0, volume / vol_sma, 1.0)

    # Z-score
    lookback = params.get("lookback", 20)
    if lookback <= n:
        zscore = np.full(n, 0.0)
        for i in range(lookback, n):
            window = close[i-lookback:i]
            mu, sigma = window.mean(), window.std()
            zscore[i] = (close[i] - mu) / sigma if sigma > 0 else 0
        indicators["zscore"] = zscore

    return indicators


def generate_signals(archetype: str, indicators: dict, params: dict) -> np.ndarray:
    """Generate entry signals (1=LONG, -1=SHORT, 0=no signal) for each bar."""
    close = indicators["close"]
    n = len(close)
    signals = np.zeros(n, dtype=int)

    # Warmup period
    warmup = max(200, params.get("sma_filter_period", 200))

    if archetype == "rsi_mean_reversion":
        rsi = indicators["rsi"]
        entry_th = params.get("rsi_entry_threshold", 10)
        use_sma = params.get("use_sma_filter", True)
        sma_period = params.get("sma_filter_period", 200)
        sma_key = f"sma_{sma_period}"
        sma = indicators.get(sma_key, indicators.get("sma_200"))

        for i in range(warmup, n):
            if rsi[i] < entry_th:
                if not use_sma or (sma is not None and not np.isnan(sma[i]) and close[i] > sma[i]):
                    signals[i] = 1  # LONG

    elif archetype == "stochrsi_bounce":
        rsi = indicators["rsi"]
        oversold = params.get("oversold_level", 15)
        vol_mult = params.get("volume_mult", 1.5)
        vol_ratio = indicators.get("volume_ratio", np.ones(n))

        for i in range(warmup, n):
            if rsi[i] < oversold and vol_ratio[i] > vol_mult:
                signals[i] = 1

    elif archetype == "macd_divergence":
        fast = params.get("fast_period", 12)
        slow = params.get("slow_period", 26)
        sig = params.get("signal_period", 9)

        ema_fast = _ema_array(close, fast)
        ema_slow = _ema_array(close, slow)
        macd_line = ema_fast - ema_slow
        signal_line = _ema_array(macd_line, sig)
        hist = macd_line - signal_line

        for i in range(warmup, n):
            # Bullish: MACD crosses above signal while price making lower lows
            if hist[i] > 0 and hist[i-1] <= 0:
                signals[i] = 1

    elif archetype == "cross_sectional_momentum":
        # Simple: buy if return over lookback > 0
        lb = params.get("lookback_days", 14)
        for i in range(max(warmup, lb), n):
            ret = (close[i] - close[i - lb]) / close[i - lb]
            if ret > 0.02:  # > 2% return
                signals[i] = 1

    elif archetype == "ema_crossover":
        fast_p = params.get("fast_ema", 9)
        slow_p = params.get("slow_ema", 21)
        ema_f = indicators.get(f"ema_{fast_p}", _ema_array(close, fast_p))
        ema_s = indicators.get(f"ema_{slow_p}", _ema_array(close, slow_p))
        trend_p = params.get("trend_ema", 200)
        trend = indicators.get(f"sma_{trend_p}", indicators.get("sma_200"))
        require_trend = params.get("require_trend_alignment", True)

        for i in range(warmup, n):
            if np.isnan(ema_f[i]) or np.isnan(ema_s[i]):
                continue
            # Bullish cross
            if ema_f[i] > ema_s[i] and ema_f[i-1] <= ema_s[i-1]:
                if not require_trend or (trend is not None and not np.isnan(trend[i]) and close[i] > trend[i]):
                    signals[i] = 1

    elif archetype == "ichimoku_cloud":
        tenkan = params.get("tenkan_period", 20)
        kijun = params.get("kijun_period", 60)
        # Simplified: tenkan crosses above kijun
        tenkan_line = _donchian_mid(indicators["high"], indicators["low"], tenkan)
        kijun_line = _donchian_mid(indicators["high"], indicators["low"], kijun)

        for i in range(warmup, n):
            if tenkan_line[i] > kijun_line[i] and tenkan_line[i-1] <= kijun_line[i-1]:
                if close[i] > kijun_line[i]:  # price above kijun
                    signals[i] = 1

    elif archetype == "sma_bounce":
        sma_period = params.get("sma_period", 200)
        bounce_pct = params.get("bounce_pct", 0.01)
        vol_mult = params.get("volume_mult", 1.5)
        rsi_max = params.get("rsi_max", 50)
        sma = indicators.get(f"sma_{sma_period}", indicators.get("sma_200"))
        vol_ratio = indicators.get("volume_ratio", np.ones(n))
        rsi = indicators["rsi"]

        if sma is not None:
            for i in range(warmup, n):
                if np.isnan(sma[i]):
                    continue
                dist = (close[i] - sma[i]) / sma[i]
                if 0 <= dist <= bounce_pct and vol_ratio[i] > vol_mult and rsi[i] < rsi_max:
                    signals[i] = 1

    elif archetype == "bollinger_squeeze":
        bb_width = indicators.get("bb_width", np.full(n, 0.1))
        bb_upper = indicators.get("bb_upper")
        squeeze_th = params.get("squeeze_threshold", 0.04)

        if bb_upper is not None:
            for i in range(warmup, n):
                if np.isnan(bb_width[i]) or np.isnan(bb_upper[i]):
                    continue
                # Low bandwidth (squeeze) then breakout above upper band
                if bb_width[i] < squeeze_th and close[i] > bb_upper[i]:
                    signals[i] = 1

    elif archetype == "atr_breakout":
        atr_arr = indicators["atr"]
        atr_mult = params.get("atr_mult", 2.0)
        ema_p = params.get("ema_period", 20)
        ema_arr = _ema_array(close, ema_p)
        vol_confirm = params.get("volume_confirm", 1.5)
        vol_ratio = indicators.get("volume_ratio", np.ones(n))

        for i in range(warmup, n):
            if atr_arr[i] <= 0 or np.isnan(ema_arr[i]):
                continue
            upper_channel = ema_arr[i] + atr_mult * atr_arr[i]
            if close[i] > upper_channel and vol_ratio[i] > vol_confirm:
                signals[i] = 1

    elif archetype == "mean_reversion_zscore":
        zs = indicators.get("zscore", np.zeros(n))
        entry_z = params.get("entry_zscore", -2.0)

        for i in range(warmup, n):
            if zs[i] < entry_z:
                signals[i] = 1  # buy extreme negative z-score

    elif archetype == "volume_breakout":
        vol_mult = params.get("volume_mult", 3.0)
        breakout_pct = params.get("breakout_pct", 0.02)
        vol_ratio = indicators.get("volume_ratio", np.ones(n))
        lb = params.get("lookback", 20)

        for i in range(max(warmup, lb), n):
            if vol_ratio[i] > vol_mult:
                high_n = np.max(close[i-lb:i])
                if close[i] > high_n * (1 + breakout_pct):
                    signals[i] = 1

    elif archetype == "vwap_reversion":
        # Simplified VWAP (cumulative)
        zs = indicators.get("zscore", np.zeros(n))
        entry_z = params.get("vwap_sd_entry", -2.0)

        for i in range(warmup, n):
            if zs[i] < -entry_z:  # below VWAP by N std devs
                signals[i] = 1

    elif archetype == "support_resistance_bounce":
        sr_lb = params.get("sr_lookback", 30)
        sr_tol = params.get("sr_tolerance_pct", 0.005)
        rsi_max = params.get("rsi_filter_max", 45)
        rsi = indicators["rsi"]

        for i in range(max(warmup, sr_lb), n):
            # Find local min as support
            local_min = np.min(indicators["low"][i-sr_lb:i])
            dist = (close[i] - local_min) / local_min
            if 0 <= dist <= sr_tol and rsi[i] < rsi_max:
                signals[i] = 1

    elif archetype == "swing_failure_pattern":
        swing_lb = params.get("swing_lookback", 10)
        wick_pct = params.get("wick_exceed_pct", 0.005)

        for i in range(max(warmup, swing_lb), n):
            # Bearish SFP: wick above prior swing high, close below
            prior_high = np.max(indicators["high"][i-swing_lb:i])
            if indicators["high"][i] > prior_high * (1 + wick_pct) and close[i] < prior_high:
                signals[i] = -1  # SHORT

            # Bullish SFP: wick below prior swing low, close above
            prior_low = np.min(indicators["low"][i-swing_lb:i])
            if indicators["low"][i] < prior_low * (1 - wick_pct) and close[i] > prior_low:
                signals[i] = 1  # LONG

    elif archetype == "funding_rate_extreme":
        # Can't simulate funding rate from OHLCV alone → use RSI as proxy
        rsi = indicators["rsi"]
        threshold = 20  # extreme oversold as funding proxy
        for i in range(warmup, n):
            if rsi[i] < threshold:
                signals[i] = 1

    elif archetype == "fear_greed_contrarian":
        # Use RSI as proxy for fear/greed
        rsi = indicators["rsi"]
        fear_th = params.get("fear_threshold", 15)
        for i in range(warmup, n):
            if rsi[i] < fear_th:
                signals[i] = 1

    elif archetype in ("mvrv_proxy", "exchange_netflow"):
        # On-chain proxied via z-score
        zs = indicators.get("zscore", np.zeros(n))
        entry_z = params.get("z_entry", -1.5) if archetype == "mvrv_proxy" else -2.0
        for i in range(warmup, n):
            if zs[i] < entry_z:
                signals[i] = 1

    return signals


def backtest_permutation(
    perm: Permutation,
    df: pd.DataFrame,
    symbol: str,
    # Realistic costs: 0.05% slippage + 0.1% commission (Binance taker). Fixed 2026-03-13 — was 0% causing inflated rankings
    slippage_pct: float = 0.0005,
    commission_pct: float = 0.001,
) -> BacktestResult:
    """Run a single permutation against OHLCV data.

    Uses vectorised signal generation + per-trade loop for TP/SL/trailing.
    """
    if df.empty or len(df) < 250:
        return BacktestResult(perm_id=perm.perm_id, archetype=perm.archetype,
                              symbol=symbol, params=perm.params)

    params = perm.params
    indicators = compute_indicators(df, params)
    signals = generate_signals(perm.archetype, indicators, params)

    close = indicators["close"]
    high = indicators["high"]
    low = indicators["low"]
    atr_arr = indicators["atr"]
    n = len(close)

    # Extract TP/SL params
    tp_atr = params.get("tp_atr_mult", 3.0)
    sl_atr = params.get("sl_atr_mult", 2.0)
    tp_pct = params.get("tp_pct", 0.0)
    sl_pct = params.get("sl_pct", 0.0)
    max_hold = params.get("max_hold_days", 7)
    use_trailing = params.get("trailing_stop", False)
    trail_activate = params.get("trail_activate_pct", 0.04)

    # Simulate trades
    trades: list[float] = []
    hold_bars_list: list[int] = []
    in_trade = False
    entry_price = 0.0
    tp_price = 0.0
    sl_price = 0.0
    direction = 0
    entry_bar = 0
    hwm = 0.0  # high water mark for trailing

    for i in range(n):
        if in_trade:
            bars_held = i - entry_bar

            # Check TP/SL
            if direction == 1:  # LONG
                if high[i] >= tp_price:
                    pnl = (tp_price - entry_price) / entry_price - slippage_pct - commission_pct
                    trades.append(pnl)
                    hold_bars_list.append(bars_held)
                    in_trade = False
                    continue
                if low[i] <= sl_price:
                    pnl = (sl_price - entry_price) / entry_price - slippage_pct - commission_pct
                    trades.append(pnl)
                    hold_bars_list.append(bars_held)
                    in_trade = False
                    continue
                # Trailing stop
                if use_trailing and close[i] > hwm:
                    hwm = close[i]
                    gain_from_entry = (hwm - entry_price) / entry_price
                    if gain_from_entry > trail_activate:
                        new_sl = hwm * (1 - sl_atr * atr_arr[i] / hwm if atr_arr[i] > 0 else 0.02)
                        sl_price = max(sl_price, new_sl)

            elif direction == -1:  # SHORT
                if low[i] <= tp_price:
                    pnl = (entry_price - tp_price) / entry_price - slippage_pct - commission_pct
                    trades.append(pnl)
                    hold_bars_list.append(bars_held)
                    in_trade = False
                    continue
                if high[i] >= sl_price:
                    pnl = (entry_price - sl_price) / entry_price - slippage_pct - commission_pct
                    trades.append(pnl)
                    hold_bars_list.append(bars_held)
                    in_trade = False
                    continue

            # Max hold expiry
            if bars_held >= max_hold:
                pnl = (close[i] - entry_price) / entry_price * direction - slippage_pct - commission_pct
                trades.append(pnl)
                hold_bars_list.append(bars_held)
                in_trade = False
                continue

        elif signals[i] != 0:
            # Enter trade
            direction = signals[i]
            entry_price = close[i]
            entry_bar = i
            hwm = close[i]
            in_trade = True

            # Set TP/SL
            if atr_arr[i] > 0 and tp_atr > 0:
                tp_price = entry_price + direction * tp_atr * atr_arr[i]
                sl_price = entry_price - direction * sl_atr * atr_arr[i]
            elif tp_pct > 0:
                tp_price = entry_price * (1 + direction * tp_pct)
                sl_price = entry_price * (1 - direction * sl_pct)
            else:
                tp_price = entry_price * (1 + direction * 0.10)
                sl_price = entry_price * (1 - direction * 0.05)

    # Close any open trade at last bar
    if in_trade:
        pnl = (close[-1] - entry_price) / entry_price * direction - slippage_pct - commission_pct
        trades.append(pnl)
        hold_bars_list.append(n - entry_bar)

    # Compute metrics
    result = BacktestResult(
        perm_id=perm.perm_id,
        archetype=perm.archetype,
        symbol=symbol,
        params=perm.params,
        seed_strategy=perm.seed_strategy,
    )

    if not trades:
        return result

    pnl_arr = np.array(trades)
    result.total_trades = len(trades)
    result.wins = int(np.sum(pnl_arr > 0))
    result.losses = int(np.sum(pnl_arr <= 0))
    result.win_rate = result.wins / result.total_trades
    result.avg_trade_pnl = float(pnl_arr.mean())
    result.total_return = float(pnl_arr.sum())
    result.pnl_series = trades
    result.avg_hold_bars = float(np.mean(hold_bars_list)) if hold_bars_list else 0

    # Sharpe
    if pnl_arr.std() > 0:
        result.sharpe = float(pnl_arr.mean() / pnl_arr.std() * np.sqrt(252))
    # Sortino
    downside = pnl_arr[pnl_arr < 0]
    if len(downside) > 0 and downside.std() > 0:
        result.sortino = float(pnl_arr.mean() / downside.std() * np.sqrt(252))
    else:
        result.sortino = result.sharpe

    # Max drawdown
    cum = np.cumsum(pnl_arr)
    peak = np.maximum.accumulate(cum)
    dd = cum - peak
    result.max_drawdown = float(dd.min()) if len(dd) > 0 else 0.0
    result.equity_curve = cum.tolist()

    # Profit factor
    gross_profit = float(np.sum(pnl_arr[pnl_arr > 0]))
    gross_loss = float(abs(np.sum(pnl_arr[pnl_arr < 0])))
    result.profit_factor = gross_profit / gross_loss if gross_loss > 0 else 99.0

    return result


def run_batch_backtest(
    permutations: list[Permutation],
    symbols: list[str] = None,
    # Realistic costs: 0.05% slippage + 0.1% commission (Binance taker). Fixed 2026-03-13 — was 0% causing inflated rankings
    slippage_pct: float = 0.0005,
    commission_pct: float = 0.001,
    period: str = "1y",
) -> list[BacktestResult]:
    """Run backtests for all permutations across all symbols."""
    if symbols is None:
        symbols = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD"]

    # Pre-fetch data for all symbols
    data_cache: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        print(f"[backtester] Fetching {sym} ({period})...")
        data_cache[sym] = fetch_ohlcv(sym, period)

    results: list[BacktestResult] = []
    total = len(permutations) * len(symbols)
    start = time.time()

    for idx, perm in enumerate(permutations):
        for sym in symbols:
            df = data_cache[sym]
            if df.empty:
                continue
            result = backtest_permutation(perm, df, sym, slippage_pct, commission_pct)
            results.append(result)

        if (idx + 1) % 100 == 0:
            elapsed = time.time() - start
            rate = (idx + 1) * len(symbols) / elapsed
            print(f"[backtester] {idx+1}/{len(permutations)} permutations "
                  f"({rate:.0f} backtests/sec)")

    elapsed = time.time() - start
    print(f"[backtester] Completed {len(results)} backtests in {elapsed:.1f}s "
          f"({len(results)/max(elapsed,0.01):.0f}/sec)")
    return results


# --- Helpers ---

def _ema_array(data: np.ndarray, period: int) -> np.ndarray:
    """Compute EMA array."""
    n = len(data)
    ema = np.full(n, np.nan)
    if period > n:
        return ema
    ema[period - 1] = np.mean(data[:period])
    mult = 2 / (period + 1)
    for i in range(period, n):
        ema[i] = data[i] * mult + ema[i - 1] * (1 - mult)
    return ema


def _donchian_mid(high: np.ndarray, low: np.ndarray, period: int) -> np.ndarray:
    """Donchian channel midline (used for Ichimoku Tenkan/Kijun)."""
    n = len(high)
    mid = np.full(n, np.nan)
    for i in range(period - 1, n):
        mid[i] = (np.max(high[i-period+1:i+1]) + np.min(low[i-period+1:i+1])) / 2
    return mid
