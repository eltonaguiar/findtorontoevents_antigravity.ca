"""
BTC-Neutral Residual Mean Reversion
====================================
#1 ranked research strategy (reported Sharpe 2.3).

Core idea: regress each altcoin's returns against BTC returns using rolling OLS.
The residual captures idiosyncratic alpha stripped of market beta. When the
z-score of that residual is extreme, the altcoin is mispriced relative to its
expected BTC-beta relationship and should revert.

LONG:  residual z-score < -2.0  (altcoin cheap vs BTC beta)
SHORT: residual z-score > +2.0  (altcoin expensive vs BTC beta)
EXIT:  z-score crosses back to 0
TP: 2.0x ATR   SL: 1.5x ATR
Confidence: 0.55 + min(abs(z) - 2.0, 2.0) * 0.15   (cap 0.85)
"""

import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


# ---------------------------------------------------------------------------
# Binance OHLCV fetcher with mirror failover (api, api1, api2, api3)
# ---------------------------------------------------------------------------
BINANCE_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]

SYMBOLS = [
    "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT",
    "AVAXUSDT", "DOTUSDT", "LINKUSDT", "NEARUSDT", "FETUSDT",
]


def _fetch_ohlcv(symbol: str, interval: str = "4h", limit: int = 500) -> pd.DataFrame:
    """Fetch klines from Binance with mirror failover."""
    import requests

    for base in BINANCE_MIRRORS:
        url = f"{base}/api/v3/klines"
        params = {"symbol": symbol, "interval": interval, "limit": limit}
        try:
            r = requests.get(url, params=params, timeout=15)
            if r.status_code == 200:
                data = r.json()
                df = pd.DataFrame(data, columns=[
                    "open_time", "open", "high", "low", "close", "volume",
                    "close_time", "quote_vol", "trades", "taker_buy_base",
                    "taker_buy_quote", "ignore",
                ])
                for c in ("open", "high", "low", "close", "volume"):
                    df[c] = df[c].astype(float)
                df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms")
                df = df[["timestamp", "open", "high", "low", "close", "volume"]]
                return df
        except Exception:
            continue
    raise RuntimeError(f"All Binance mirrors failed for {symbol}")


# ---------------------------------------------------------------------------
# Strategy
# ---------------------------------------------------------------------------
class BtcNeutralResidualMRStrategy:
    """BTC-Neutral Residual Mean Reversion."""

    def __init__(self, params: Optional[Dict] = None):
        self.p = params or {}
        self.reg_window = self.p.get("regression_window", 30)
        self.z_window = self.p.get("zscore_window", 20)
        self.z_entry = self.p.get("z_entry", 2.0)
        self.atr_period = self.p.get("atr_period", 14)
        self.tp_atr = self.p.get("tp_atr", 2.0)
        self.sl_atr = self.p.get("sl_atr", 1.5)

    # -- helpers -------------------------------------------------------------
    @staticmethod
    def _atr(data: pd.DataFrame, period: int) -> pd.Series:
        h, l, c = data["high"], data["low"], data["close"]
        tr = pd.concat(
            [(h - l), (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1
        ).max(axis=1)
        return tr.rolling(period, min_periods=1).mean()

    @staticmethod
    def _rolling_ols_residual(
        alt_ret: pd.Series, btc_ret: pd.Series, window: int
    ) -> pd.Series:
        """Rolling OLS: alt_ret = alpha + beta * btc_ret + residual.
        Returns the residual series."""
        residuals = pd.Series(np.nan, index=alt_ret.index)
        for i in range(window, len(alt_ret)):
            y = alt_ret.iloc[i - window : i].values.astype(float)
            x = btc_ret.iloc[i - window : i].values.astype(float)
            # Skip windows containing NaN or inf
            if np.any(~np.isfinite(y)) or np.any(~np.isfinite(x)):
                continue
            x_mat = np.column_stack([np.ones(window), x])
            try:
                coeffs = np.linalg.lstsq(x_mat, y, rcond=None)[0]
            except Exception:
                continue
            predicted = coeffs[0] + coeffs[1] * float(btc_ret.iloc[i])
            alt_val = float(alt_ret.iloc[i])
            if np.isfinite(predicted) and np.isfinite(alt_val):
                residuals.iloc[i] = alt_val - predicted
        return residuals

    @staticmethod
    def _rolling_zscore(series: pd.Series, window: int) -> pd.Series:
        mu = series.rolling(window, min_periods=window).mean()
        sd = series.rolling(window, min_periods=window).std(ddof=0)
        sd = sd.replace(0, np.nan)
        return (series - mu) / sd

    # -- main signal generation ----------------------------------------------
    def generate_signals(
        self, data: pd.DataFrame, symbol: str = "ETHUSDT",
        btc_data: Optional[pd.DataFrame] = None,
    ) -> List[Signal]:
        """Generate signals for one altcoin.

        Parameters
        ----------
        data : pd.DataFrame
            Altcoin OHLCV with columns: open, high, low, close, volume.
        symbol : str
            Altcoin symbol (e.g. ETHUSDT).
        btc_data : pd.DataFrame, optional
            BTC OHLCV.  If None, fetched internally from Binance.
        """
        min_bars = self.reg_window + self.z_window + 10
        if data is None or len(data) < min_bars:
            return []

        # Fetch BTC data if not supplied
        if btc_data is None:
            btc_data = _fetch_ohlcv("BTCUSDT", interval="4h", limit=len(data) + 20)

        # Align lengths
        n = min(len(data), len(btc_data))
        alt = data.iloc[-n:].reset_index(drop=True)
        btc = btc_data.iloc[-n:].reset_index(drop=True)

        alt_ret = alt["close"].pct_change()
        btc_ret = btc["close"].pct_change()

        # Rolling OLS residuals
        residuals = self._rolling_ols_residual(alt_ret, btc_ret, self.reg_window)

        # Z-score of residuals
        z = self._rolling_zscore(residuals, self.z_window)

        current_z = z.iloc[-1]
        if np.isnan(current_z):
            return []

        current_price = float(alt["close"].iloc[-1])
        atr = self._atr(alt, self.atr_period)
        current_atr = float(atr.iloc[-1])
        if np.isnan(current_atr) or current_atr <= 0:
            return []

        signals: List[Signal] = []

        # LONG: z < -2.0  (altcoin underpriced relative to BTC beta)
        if current_z < -self.z_entry:
            conf = 0.55 + min(abs(current_z) - self.z_entry, 2.0) * 0.15
            conf = round(min(conf, 0.85), 3)
            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=conf,
                entry_price=round(current_price, 6),
                take_profit=round(current_price + current_atr * self.tp_atr, 6),
                stop_loss=round(current_price - current_atr * self.sl_atr, 6),
                reason=f"BTC-Neutral ResidZ={current_z:.2f} LONG",
            ))

        # SHORT: z > 2.0  (altcoin overpriced relative to BTC beta)
        if current_z > self.z_entry:
            conf = 0.55 + min(abs(current_z) - self.z_entry, 2.0) * 0.15
            conf = round(min(conf, 0.85), 3)
            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=conf,
                entry_price=round(current_price, 6),
                take_profit=round(current_price - current_atr * self.tp_atr, 6),
                stop_loss=round(current_price + current_atr * self.sl_atr, 6),
                reason=f"BTC-Neutral ResidZ={current_z:.2f} SHORT",
            ))

        return signals


# ---------------------------------------------------------------------------
# Backtest
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import requests  # noqa: F811

    BT_SYMBOLS = ["ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT"]
    INTERVAL = "4h"
    # 180 days * 6 bars/day = 1080 bars
    LIMIT = 1080
    TP_ATR_MULT = 2.0
    SL_ATR_MULT = 1.5
    HORIZON = 12  # bars to check TP/SL

    REG_WINDOW = 30
    Z_WINDOW = 20
    Z_ENTRY = 2.0
    ATR_PERIOD = 14

    print("=" * 70)
    print("BTC-Neutral Residual Mean Reversion  --  Walk-Forward Backtest")
    print(f"Period: 180 days 4h  |  Regression: {REG_WINDOW}  |  Z-window: {Z_WINDOW}")
    print(f"Entry: |z| > {Z_ENTRY}  |  TP: {TP_ATR_MULT}x ATR  |  SL: {SL_ATR_MULT}x ATR")
    print("=" * 70)

    # Fetch BTC once
    print("\nFetching BTCUSDT ...", end=" ", flush=True)
    btc_df = _fetch_ohlcv("BTCUSDT", INTERVAL, LIMIT)
    print(f"{len(btc_df)} bars")
    time.sleep(0.3)

    # ATR helper
    def compute_atr(df: pd.DataFrame, period: int = ATR_PERIOD) -> pd.Series:
        h, l, c = df["high"], df["low"], df["close"]
        tr = pd.concat(
            [(h - l), (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1
        ).max(axis=1)
        return tr.rolling(period, min_periods=1).mean()

    all_trades: List[Dict] = []

    for sym in BT_SYMBOLS:
        print(f"Fetching {sym} ...", end=" ", flush=True)
        try:
            alt_df = _fetch_ohlcv(sym, INTERVAL, LIMIT)
        except RuntimeError as e:
            print(f"FAILED: {e}")
            continue
        print(f"{len(alt_df)} bars")
        time.sleep(0.3)

        # Align
        n = min(len(alt_df), len(btc_df))
        alt = alt_df.iloc[-n:].reset_index(drop=True)
        btc = btc_df.iloc[-n:].reset_index(drop=True)

        alt_ret = alt["close"].pct_change()
        btc_ret = btc["close"].pct_change()

        # Rolling OLS residuals
        residuals = BtcNeutralResidualMRStrategy._rolling_ols_residual(
            alt_ret, btc_ret, REG_WINDOW
        )
        # Z-score
        z_mu = residuals.rolling(Z_WINDOW, min_periods=Z_WINDOW).mean()
        z_sd = residuals.rolling(Z_WINDOW, min_periods=Z_WINDOW).std(ddof=0).replace(0, np.nan)
        z_scores = (residuals - z_mu) / z_sd

        atr = compute_atr(alt)

        # Walk-forward: scan each bar for entry, then check outcome
        start_bar = REG_WINDOW + Z_WINDOW + 5
        sym_trades = []

        for i in range(start_bar, len(alt) - HORIZON):
            zv = z_scores.iloc[i]
            if np.isnan(zv):
                continue

            direction = None
            if zv < -Z_ENTRY:
                direction = "BUY"
            elif zv > Z_ENTRY:
                direction = "SELL"
            else:
                continue

            entry_price = alt["close"].iloc[i]
            atr_val = atr.iloc[i]
            if np.isnan(atr_val) or atr_val <= 0:
                continue

            tp_dist = atr_val * TP_ATR_MULT
            sl_dist = atr_val * SL_ATR_MULT

            if direction == "BUY":
                tp_price = entry_price + tp_dist
                sl_price = entry_price - sl_dist
            else:
                tp_price = entry_price - tp_dist
                sl_price = entry_price + sl_dist

            # Check future bars for TP/SL hit
            outcome = "TIMEOUT"
            pnl_pct = 0.0
            for j in range(1, HORIZON + 1):
                bar_idx = i + j
                bar_high = alt["high"].iloc[bar_idx]
                bar_low = alt["low"].iloc[bar_idx]

                if direction == "BUY":
                    if bar_low <= sl_price:
                        outcome = "SL"
                        pnl_pct = -sl_dist / entry_price * 100
                        break
                    if bar_high >= tp_price:
                        outcome = "TP"
                        pnl_pct = tp_dist / entry_price * 100
                        break
                else:  # SELL
                    if bar_high >= sl_price:
                        outcome = "SL"
                        pnl_pct = -sl_dist / entry_price * 100
                        break
                    if bar_low <= tp_price:
                        outcome = "TP"
                        pnl_pct = tp_dist / entry_price * 100
                        break

            if outcome == "TIMEOUT":
                exit_price = alt["close"].iloc[i + HORIZON]
                if direction == "BUY":
                    pnl_pct = (exit_price - entry_price) / entry_price * 100
                else:
                    pnl_pct = (entry_price - exit_price) / entry_price * 100

            conf = 0.55 + min(abs(zv) - Z_ENTRY, 2.0) * 0.15
            conf = min(conf, 0.85)

            sym_trades.append({
                "symbol": sym,
                "bar": i,
                "direction": direction,
                "z_score": round(zv, 2),
                "confidence": round(conf, 3),
                "entry": round(entry_price, 6),
                "outcome": outcome,
                "pnl_pct": round(pnl_pct, 3),
            })

        all_trades.extend(sym_trades)
        print(f"  -> {len(sym_trades)} trades for {sym}")

    # ---------------------------------------------------------------------------
    # Results
    # ---------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    if not all_trades:
        print("No trades generated.")
    else:
        df_trades = pd.DataFrame(all_trades)
        total = len(df_trades)
        wins = len(df_trades[df_trades["pnl_pct"] > 0])
        losses = len(df_trades[df_trades["pnl_pct"] <= 0])
        wr = wins / total * 100 if total else 0
        avg_pnl = df_trades["pnl_pct"].mean()
        gross_profit = df_trades[df_trades["pnl_pct"] > 0]["pnl_pct"].sum()
        gross_loss = abs(df_trades[df_trades["pnl_pct"] <= 0]["pnl_pct"].sum())
        pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        print(f"\nTotal trades:  {total}")
        print(f"Wins:          {wins}   Losses: {losses}")
        print(f"Win rate:      {wr:.1f}%")
        print(f"Profit factor: {pf:.2f}")
        print(f"Avg PnL/trade: {avg_pnl:.3f}%")
        print(f"Total PnL:     {df_trades['pnl_pct'].sum():.2f}%")

        # Outcome breakdown
        print(f"\nOutcome breakdown:")
        for outcome in ["TP", "SL", "TIMEOUT"]:
            subset = df_trades[df_trades["outcome"] == outcome]
            print(f"  {outcome:8s}: {len(subset):4d} trades  avg PnL={subset['pnl_pct'].mean():.3f}%")

        # Per-symbol breakdown
        print(f"\n{'Symbol':<12} {'Trades':>6} {'WR%':>6} {'PF':>7} {'AvgPnL%':>9} {'TotalPnL%':>10}")
        print("-" * 55)
        for sym in BT_SYMBOLS:
            s = df_trades[df_trades["symbol"] == sym]
            if len(s) == 0:
                continue
            sw = len(s[s["pnl_pct"] > 0])
            swr = sw / len(s) * 100
            sgp = s[s["pnl_pct"] > 0]["pnl_pct"].sum()
            sgl = abs(s[s["pnl_pct"] <= 0]["pnl_pct"].sum())
            spf = sgp / sgl if sgl > 0 else float("inf")
            print(f"{sym:<12} {len(s):>6} {swr:>5.1f}% {spf:>7.2f} {s['pnl_pct'].mean():>8.3f}% {s['pnl_pct'].sum():>9.2f}%")

        # Direction breakdown
        print(f"\nDirection breakdown:")
        for d in ["BUY", "SELL"]:
            subset = df_trades[df_trades["direction"] == d]
            if len(subset) == 0:
                continue
            dw = len(subset[subset["pnl_pct"] > 0])
            dwr = dw / len(subset) * 100
            print(f"  {d:5s}: {len(subset):4d} trades  WR={dwr:.1f}%  AvgPnL={subset['pnl_pct'].mean():.3f}%")
