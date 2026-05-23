"""
RSI2 Mean Reversion Backtest Case Study
========================================
Strategy:
  LONG:  RSI(2) < 10 AND close > EMA(200)
  SHORT: RSI(2) > 90 AND close < EMA(200)
  TP: 2x ATR(14)  |  SL: 1x ATR(14)  |  Time exit: 10 bars
  Commission: 0.05% per trade (entry + exit)

Tests 15 crypto symbols across 3 timeframes (1h, 4h, 1d)
with 3 lookback periods (full, 6mo, 3mo) for consistency checks.
"""

import requests
import pandas as pd
import numpy as np
import json
import time
import sys
from datetime import datetime, timedelta

# ── Configuration ──────────────────────────────────────────────────────────
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "LINKUSDT",
    "DOGEUSDT", "ADAUSDT", "XRPUSDT", "BNBUSDT", "DOTUSDT",
    "LTCUSDT", "NEARUSDT", "ATOMUSDT", "HYPEUSDT", "SUIUSDT",
]
TIMEFRAMES = ["1h", "4h", "1d"]
BINANCE_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]

RSI_PERIOD = 2
EMA_PERIOD = 200
ATR_PERIOD = 14
RSI_LONG_THRESH = 10
RSI_SHORT_THRESH = 90
TP_ATR_MULT = 2.0
SL_ATR_MULT = 1.0
MAX_HOLD_BARS = 10
COMMISSION_PCT = 0.05 / 100  # 0.05% per side

# Binance kline limit per request
KLINE_LIMIT = 1000


# ── Data Fetching ──────────────────────────────────────────────────────────
def fetch_klines(symbol: str, interval: str, start_ms: int = None, end_ms: int = None) -> list:
    """Fetch klines from Binance with mirror failover. Returns raw list of lists."""
    params = {"symbol": symbol, "interval": interval, "limit": KLINE_LIMIT}
    if start_ms:
        params["startTime"] = start_ms
    if end_ms:
        params["endTime"] = end_ms

    for mirror in BINANCE_MIRRORS:
        url = f"{mirror}/api/v3/klines"
        try:
            r = requests.get(url, params=params, timeout=15)
            if r.status_code == 200:
                return r.json()
            # Symbol might not exist on Binance
            if r.status_code == 400:
                data = r.json()
                if "Invalid symbol" in data.get("msg", ""):
                    return []
        except Exception:
            continue
    return []


def fetch_all_klines(symbol: str, interval: str, start_ms: int = None) -> pd.DataFrame:
    """Paginate through all available klines for a symbol+interval.

    We need enough bars to cover EMA(200) warm-up + trading history.
    Target: at least 1500 bars for shorter TFs, or all available for 1d.
    """
    # If no start_ms provided, calculate a reasonable start based on interval
    if start_ms is None:
        now_ms = int(datetime.utcnow().timestamp() * 1000)
        # How many ms per bar
        interval_ms = {"1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}
        bar_ms = interval_ms.get(interval, 86_400_000)
        # Request ~2500 bars of history (enough for EMA200 warmup + good sample)
        target_bars = 2500
        start_ms = now_ms - (target_bars * bar_ms)

    all_rows = []
    cursor = start_ms
    max_pages = 10  # safety limit
    page = 0
    while page < max_pages:
        page += 1
        batch = fetch_klines(symbol, interval, start_ms=cursor)
        if not batch:
            break
        all_rows.extend(batch)
        # Next page starts after last candle
        last_open = batch[-1][0]
        if cursor and last_open <= cursor:
            break
        cursor = last_open + 1
        if len(batch) < KLINE_LIMIT:
            break
        time.sleep(0.08)  # rate-limit courtesy

    if not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_vol", "trades", "taker_buy_base",
        "taker_buy_quote", "ignore"
    ])
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df = df.drop_duplicates(subset=["open_time"]).sort_values("open_time").reset_index(drop=True)
    return df


# ── Indicator Calculations ─────────────────────────────────────────────────
def calc_rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calc_ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def calc_atr(df: pd.DataFrame, period: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


# ── Backtester ─────────────────────────────────────────────────────────────
def run_backtest(df: pd.DataFrame, trade_after: pd.Timestamp = None) -> dict:
    """Run RSI2 mean-reversion backtest on a prepared DataFrame.
    If trade_after is set, only count trades entered on or after that timestamp.
    Indicators still compute on the full df for proper warmup.
    Returns stats dict."""
    if len(df) < EMA_PERIOD + 10:
        return None

    df = df.copy()
    df["rsi"] = calc_rsi(df["close"], RSI_PERIOD)
    df["ema200"] = calc_ema(df["close"], EMA_PERIOD)
    df["atr"] = calc_atr(df, ATR_PERIOD)

    trades = []
    position = None  # dict with keys: dir, entry_price, tp, sl, entry_bar, entry_idx

    for i in range(EMA_PERIOD, len(df)):
        row = df.iloc[i]
        rsi_val = row["rsi"]
        close = row["close"]
        ema_val = row["ema200"]
        atr_val = row["atr"]

        # Check exit if in position
        if position is not None:
            bars_held = i - position["entry_idx"]
            high = row["high"]
            low = row["low"]
            exit_price = None
            exit_reason = None

            if position["dir"] == "LONG":
                if low <= position["sl"]:
                    exit_price = position["sl"]
                    exit_reason = "SL"
                elif high >= position["tp"]:
                    exit_price = position["tp"]
                    exit_reason = "TP"
                elif bars_held >= MAX_HOLD_BARS:
                    exit_price = close
                    exit_reason = "TIME"
            else:  # SHORT
                if high >= position["sl"]:
                    exit_price = position["sl"]
                    exit_reason = "SL"
                elif low <= position["tp"]:
                    exit_price = position["tp"]
                    exit_reason = "TP"
                elif bars_held >= MAX_HOLD_BARS:
                    exit_price = close
                    exit_reason = "TIME"

            if exit_price is not None:
                entry_p = position["entry_price"]
                if position["dir"] == "LONG":
                    pnl_pct = (exit_price - entry_p) / entry_p
                else:
                    pnl_pct = (entry_p - exit_price) / entry_p
                # Subtract commission (entry + exit)
                pnl_pct -= 2 * COMMISSION_PCT
                trades.append({
                    "dir": position["dir"],
                    "entry_price": entry_p,
                    "exit_price": exit_price,
                    "pnl_pct": pnl_pct,
                    "bars_held": bars_held,
                    "exit_reason": exit_reason,
                    "entry_time": df.iloc[position["entry_idx"]]["open_time"],
                    "exit_time": row["open_time"],
                })
                position = None
                continue  # Don't open new position on same bar we exit

        # Entry signals (only if flat, and after trade_after cutoff if set)
        bar_time = row["open_time"]
        if trade_after is not None and bar_time < trade_after:
            continue  # Skip entries before the period window
        if position is None and not np.isnan(rsi_val) and not np.isnan(atr_val) and atr_val > 0:
            if rsi_val < RSI_LONG_THRESH and close > ema_val:
                position = {
                    "dir": "LONG",
                    "entry_price": close,
                    "tp": close + TP_ATR_MULT * atr_val,
                    "sl": close - SL_ATR_MULT * atr_val,
                    "entry_idx": i,
                }
            elif rsi_val > RSI_SHORT_THRESH and close < ema_val:
                position = {
                    "dir": "SHORT",
                    "entry_price": close,
                    "tp": close - TP_ATR_MULT * atr_val,
                    "sl": close + SL_ATR_MULT * atr_val,
                    "entry_idx": i,
                }

    return _compute_stats(trades)


def _compute_stats(trades: list) -> dict:
    """Compute performance stats from list of trade dicts."""
    if not trades:
        return {
            "total_trades": 0, "win_rate": 0, "profit_factor": 0,
            "net_pnl_pct": 0, "max_drawdown_pct": 0, "sharpe": 0,
            "avg_bars_held": 0,
            "long_trades": 0, "long_wr": 0, "long_pf": 0, "long_pnl": 0,
            "short_trades": 0, "short_wr": 0, "short_pf": 0, "short_pnl": 0,
        }

    pnls = [t["pnl_pct"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    total = len(trades)
    wr = len(wins) / total * 100 if total else 0
    gross_profit = sum(wins) if wins else 0
    gross_loss = abs(sum(losses)) if losses else 0
    pf = gross_profit / gross_loss if gross_loss > 0 else (999 if gross_profit > 0 else 0)
    net_pnl = sum(pnls) * 100  # as percentage

    # Max drawdown on cumulative equity curve
    cum = np.cumsum(pnls)
    peak = np.maximum.accumulate(cum)
    dd = peak - cum
    max_dd = np.max(dd) * 100 if len(dd) > 0 else 0

    # Sharpe (annualized, assume ~365 trades/year as rough proxy)
    if len(pnls) > 1 and np.std(pnls) > 0:
        sharpe = (np.mean(pnls) / np.std(pnls)) * np.sqrt(min(len(pnls), 365))
    else:
        sharpe = 0

    avg_bars = np.mean([t["bars_held"] for t in trades])

    # Long/Short split
    long_trades = [t for t in trades if t["dir"] == "LONG"]
    short_trades = [t for t in trades if t["dir"] == "SHORT"]

    def side_stats(side_trades):
        if not side_trades:
            return 0, 0, 0, 0
        sp = [t["pnl_pct"] for t in side_trades]
        sw = [p for p in sp if p > 0]
        sl = [p for p in sp if p <= 0]
        s_wr = len(sw) / len(side_trades) * 100
        s_gp = sum(sw) if sw else 0
        s_gl = abs(sum(sl)) if sl else 0
        s_pf = s_gp / s_gl if s_gl > 0 else (999 if s_gp > 0 else 0)
        s_pnl = sum(sp) * 100
        return len(side_trades), s_wr, s_pf, s_pnl

    lt, lwr, lpf, lpnl = side_stats(long_trades)
    st, swr, spf, spnl = side_stats(short_trades)

    return {
        "total_trades": total,
        "win_rate": round(wr, 2),
        "profit_factor": round(pf, 3),
        "net_pnl_pct": round(net_pnl, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "sharpe": round(sharpe, 3),
        "avg_bars_held": round(avg_bars, 1),
        "long_trades": lt,
        "long_wr": round(lwr, 2),
        "long_pf": round(lpf, 3),
        "long_pnl": round(lpnl, 2),
        "short_trades": st,
        "short_wr": round(swr, 2),
        "short_pf": round(spf, 3),
        "short_pnl": round(spnl, 2),
    }


# ── Main ───────────────────────────────────────────────────────────────────
def main():
    now = datetime.utcnow()
    # Period cutoffs as datetime
    period_cutoffs = {
        "full": None,
        "6mo": now - timedelta(days=183),
        "3mo": now - timedelta(days=91),
    }

    all_results = []
    data_cache = {}  # (symbol, tf) -> df

    total_combos = len(SYMBOLS) * len(TIMEFRAMES)
    done = 0

    print("=" * 80)
    print("  RSI2 MEAN REVERSION BACKTEST CASE STUDY")
    print(f"  {len(SYMBOLS)} symbols x {len(TIMEFRAMES)} timeframes x 3 periods")
    print("=" * 80)
    print()

    for symbol in SYMBOLS:
        for tf in TIMEFRAMES:
            done += 1
            tag = f"[{done}/{total_combos}]"
            print(f"{tag} Fetching {symbol} {tf}...", end=" ", flush=True)

            # Fetch full history once
            df_full = fetch_all_klines(symbol, tf)
            if df_full.empty or len(df_full) < EMA_PERIOD + 50:
                print(f"SKIP (only {len(df_full)} bars)")
                continue

            data_cache[(symbol, tf)] = df_full
            print(f"{len(df_full)} bars.", end=" ", flush=True)

            for period_name, cutoff_dt in period_cutoffs.items():
                if cutoff_dt is not None:
                    # For sub-periods, we still need EMA200 warmup data before the cutoff.
                    # So we pass the full df but tell run_backtest to only COUNT trades
                    # after the cutoff. The indicators warm up on earlier data.
                    df_slice = df_full.copy()
                    trade_after = pd.Timestamp(cutoff_dt)
                else:
                    df_slice = df_full.copy()
                    trade_after = None

                if len(df_slice) < EMA_PERIOD + 20:
                    continue

                stats = run_backtest(df_slice, trade_after=trade_after)
                if stats is None:
                    continue

                stats["symbol"] = symbol
                stats["timeframe"] = tf
                stats["period"] = period_name
                stats["bars"] = len(df_slice)
                if trade_after is not None:
                    stats["date_from"] = str(trade_after.date())
                else:
                    stats["date_from"] = str(df_slice["open_time"].iloc[0].date())
                stats["date_to"] = str(df_slice["open_time"].iloc[-1].date())
                all_results.append(stats)

            print("Done.")
            time.sleep(0.1)

    if not all_results:
        print("\nNo results generated. Check API connectivity.")
        return

    # Convert to DataFrame
    results_df = pd.DataFrame(all_results)

    # ── Summary Table (Full period, sorted by Profit Factor) ───────────
    print("\n" + "=" * 120)
    print("  FULL-PERIOD RESULTS — Sorted by Profit Factor")
    print("=" * 120)
    full = results_df[results_df["period"] == "full"].sort_values("profit_factor", ascending=False)
    if not full.empty:
        cols = ["symbol", "timeframe", "bars", "total_trades", "win_rate", "profit_factor",
                "net_pnl_pct", "max_drawdown_pct", "sharpe", "avg_bars_held",
                "long_trades", "long_wr", "long_pf", "short_trades", "short_wr", "short_pf"]
        print(full[cols].to_string(index=False))

    # ── 6-Month Results ────────────────────────────────────────────────
    print("\n" + "=" * 120)
    print("  6-MONTH RESULTS — Sorted by Profit Factor")
    print("=" * 120)
    mo6 = results_df[results_df["period"] == "6mo"].sort_values("profit_factor", ascending=False)
    if not mo6.empty:
        cols = ["symbol", "timeframe", "total_trades", "win_rate", "profit_factor",
                "net_pnl_pct", "max_drawdown_pct", "sharpe"]
        print(mo6[cols].to_string(index=False))

    # ── 3-Month Results ────────────────────────────────────────────────
    print("\n" + "=" * 120)
    print("  3-MONTH RESULTS — Sorted by Profit Factor")
    print("=" * 120)
    mo3 = results_df[results_df["period"] == "3mo"].sort_values("profit_factor", ascending=False)
    if not mo3.empty:
        cols = ["symbol", "timeframe", "total_trades", "win_rate", "profit_factor",
                "net_pnl_pct", "max_drawdown_pct", "sharpe"]
        print(mo3[cols].to_string(index=False))

    # ── Consistency Filter ─────────────────────────────────────────────
    print("\n" + "=" * 120)
    print("  CONSISTENCY CHECK: WR > 55% AND PF > 1.2 across ALL 3 periods")
    print("=" * 120)

    consistent = []
    for symbol in SYMBOLS:
        for tf in TIMEFRAMES:
            combo_results = results_df[
                (results_df["symbol"] == symbol) & (results_df["timeframe"] == tf)
            ]
            if len(combo_results) < 3:
                continue
            # Check all 3 periods pass
            all_pass = True
            combo_data = {}
            for _, row in combo_results.iterrows():
                period = row["period"]
                if row["win_rate"] <= 55 or row["profit_factor"] <= 1.2 or row["total_trades"] < 5:
                    all_pass = False
                    break
                combo_data[period] = {
                    "trades": int(row["total_trades"]),
                    "wr": row["win_rate"],
                    "pf": row["profit_factor"],
                    "pnl": row["net_pnl_pct"],
                    "dd": row["max_drawdown_pct"],
                    "sharpe": row["sharpe"],
                }
            if all_pass and len(combo_data) == 3:
                consistent.append({
                    "symbol": symbol,
                    "timeframe": tf,
                    "periods": combo_data,
                })

    if consistent:
        print(f"\n  Found {len(consistent)} consistent edge(s):\n")
        for c in consistent:
            print(f"  >>> {c['symbol']} {c['timeframe']}")
            for pname, pdata in c["periods"].items():
                print(f"      {pname:>5s}: {pdata['trades']:3d} trades | "
                      f"WR {pdata['wr']:5.1f}% | PF {pdata['pf']:5.2f} | "
                      f"PnL {pdata['pnl']:+7.2f}% | DD {pdata['dd']:5.2f}% | "
                      f"Sharpe {pdata['sharpe']:+.3f}")
            print()
    else:
        print("\n  No symbol+timeframe combos passed ALL filters across ALL 3 periods.")
        print("  Relaxing filter: showing combos where at least FULL period passes (WR>50%, PF>1.0)...\n")
        relaxed = results_df[
            (results_df["period"] == "full") &
            (results_df["win_rate"] > 50) &
            (results_df["profit_factor"] > 1.0) &
            (results_df["total_trades"] >= 5)
        ].sort_values("profit_factor", ascending=False)
        if not relaxed.empty:
            for _, row in relaxed.iterrows():
                print(f"  {row['symbol']:>10s} {row['timeframe']:>3s} | "
                      f"{int(row['total_trades']):3d} trades | WR {row['win_rate']:5.1f}% | "
                      f"PF {row['profit_factor']:5.2f} | PnL {row['net_pnl_pct']:+7.2f}%")
        else:
            print("  No combos pass even relaxed filters.")

    # ── Final Recommendation ───────────────────────────────────────────
    print("\n" + "=" * 120)
    print("  RECOMMENDED COMBOS")
    print("=" * 120)
    if consistent:
        for c in consistent:
            full_d = c["periods"]["full"]
            print(f"  * {c['symbol']} {c['timeframe']}  —  "
                  f"WR {full_d['wr']:.1f}%, PF {full_d['pf']:.2f}, "
                  f"PnL {full_d['pnl']:+.2f}%, Sharpe {full_d['sharpe']:+.3f}")
    else:
        print("  No combos achieved consistent edge (WR>55% + PF>1.2) across all 3 periods.")
        print("  This strategy may need parameter optimization or market-regime filtering.")

    # ── Save JSON ──────────────────────────────────────────────────────
    output_path = "e:/findtorontoevents_antigravity.ca/backtest_rsi2_results.json"
    output = {
        "strategy": "RSI2 Mean Reversion",
        "params": {
            "rsi_period": RSI_PERIOD, "rsi_long_thresh": RSI_LONG_THRESH,
            "rsi_short_thresh": RSI_SHORT_THRESH, "ema_period": EMA_PERIOD,
            "atr_period": ATR_PERIOD, "tp_atr_mult": TP_ATR_MULT,
            "sl_atr_mult": SL_ATR_MULT, "max_hold_bars": MAX_HOLD_BARS,
            "commission_pct": COMMISSION_PCT * 100,
        },
        "run_time": str(now),
        "results": all_results,
        "consistent_combos": consistent,
    }
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n  Results saved to {output_path}")
    print()


if __name__ == "__main__":
    main()
