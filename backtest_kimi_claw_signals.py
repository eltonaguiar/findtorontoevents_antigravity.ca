"""
Kimi Claw Pro — Multi-Factor Confluence Signal Backtest
Tests the core signal logic from the 862-line Pine Script indicator.
Full version (6-factor + overrides + filters) vs Simplified (RSI-2 + trend + volume).
"""

import requests
import pandas as pd
import numpy as np
import json
import time
import sys
from datetime import datetime

# ─── Binance API failover chain ───────────────────────────────────────────────
BINANCE_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]

SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "AVAXUSDT",
    "ADAUSDT", "LINKUSDT", "DOGEUSDT", "LTCUSDT", "XRPUSDT",
]
TIMEFRAMES = ["1h", "4h", "1d"]
BARS = 1000
COMMISSION = 0.0005  # 0.05% per side


# ─── Data fetching ────────────────────────────────────────────────────────────
def fetch_klines(symbol: str, interval: str, limit: int = 1000) -> pd.DataFrame:
    """Fetch klines with Binance mirror failover."""
    for mirror in BINANCE_MIRRORS:
        try:
            url = f"{mirror}/api/v3/klines"
            params = {"symbol": symbol, "interval": interval, "limit": limit}
            r = requests.get(url, params=params, timeout=15)
            if r.status_code == 200:
                data = r.json()
                df = pd.DataFrame(data, columns=[
                    "open_time", "open", "high", "low", "close", "volume",
                    "close_time", "quote_vol", "trades", "taker_buy_base",
                    "taker_buy_quote", "ignore",
                ])
                for c in ["open", "high", "low", "close", "volume"]:
                    df[c] = df[c].astype(float)
                df["date"] = pd.to_datetime(df["open_time"], unit="ms")
                df.set_index("date", inplace=True)
                return df
        except Exception:
            continue
    print(f"  [WARN] All mirrors failed for {symbol} {interval}")
    return pd.DataFrame()


# ─── Technical indicators ─────────────────────────────────────────────────────
def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs = gain / loss
    return 100.0 - (100.0 / (1.0 + rs))


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    plus_di = 100.0 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100.0 * (minus_dm.rolling(window=period).mean() / atr)
    dx = 100.0 * ((plus_di - minus_di).abs() / (plus_di + minus_di))
    adx_val = dx.rolling(window=period).mean()
    return adx_val


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def choppiness_index(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr_sum = tr.rolling(window=period).sum()
    high_max = high.rolling(window=period).max()
    low_min = low.rolling(window=period).min()
    ci = 100.0 * np.log10(atr_sum / (high_max - low_min)) / np.log10(period)
    return ci


# ─── Signal generators ────────────────────────────────────────────────────────
def generate_full_signals(df: pd.DataFrame) -> pd.Series:
    """
    Full Kimi Claw Pro signal logic:
    6-factor confluence + RSI-2 Connors overrides + choppiness filter + swing failure.
    Returns Series: 1=LONG, -1=SHORT, 0=no signal
    """
    c = df["close"]
    h = df["high"]
    l = df["low"]
    v = df["volume"]

    # Indicators
    ema9 = ema(c, 9)       # KAMA proxy
    ema21 = ema(c, 21)     # KAMA proxy
    ema200 = ema(c, 200)
    macd_line, macd_signal, macd_hist = macd(c, 12, 26, 9)
    rsi14 = rsi(c, 14)
    rsi2 = rsi(c, 2)
    adx14 = adx(h, l, c, 14)
    vol_sma20 = sma(v, 20)
    ci14 = choppiness_index(h, l, c, 14)

    # Histogram rising/falling
    hist_rising = macd_hist > macd_hist.shift(1)
    hist_falling = macd_hist < macd_hist.shift(1)

    # Swing low (5-bar)
    swing_low_5 = l.rolling(window=5).min()
    bullish_candle = c > df["open"]

    signals = pd.Series(0, index=df.index)

    # --- Core 6-factor LONG ---
    long_core = (
        (ema9 > ema21) &              # 1. Trend alignment
        (macd_line > macd_signal) &    # 2. MACD bullish
        hist_rising &                  #    histogram rising
        (rsi14 >= 40) & (rsi14 <= 70) &  # 3. RSI not overbought
        (v > 1.2 * vol_sma20) &       # 4. Volume confirmation
        (adx14 > 20) &                # 5. Not choppy
        (c > ema200)                   # 6. Major trend filter
    )

    # --- Core 6-factor SHORT ---
    short_core = (
        (ema9 < ema21) &
        (macd_line < macd_signal) &
        hist_falling &
        (rsi14 >= 30) & (rsi14 <= 60) &
        (v > 1.2 * vol_sma20) &
        (adx14 > 20) &
        (c < ema200)
    )

    # --- Choppiness filter: skip if CI > 61.8 ---
    chop_ok = ci14 <= 61.8

    signals[long_core & chop_ok] = 1
    signals[short_core & chop_ok] = -1

    # --- RSI-2 Connors Override ---
    rsi2_long = (rsi2 < 10) & (c > ema200)
    rsi2_short = (rsi2 > 90) & (c < ema200)
    signals[rsi2_long] = 1
    signals[rsi2_short] = -1

    # --- Swing Failure Pattern (bonus LONG) ---
    swing_fail_long = (l < swing_low_5.shift(1)) & (c > swing_low_5.shift(1)) & bullish_candle
    signals[swing_fail_long & (c > ema200)] = 1

    return signals


def generate_simplified_signals(df: pd.DataFrame) -> pd.Series:
    """
    Simplified: EMA(9)>EMA(21) + RSI(2)<15 + volume spike -> LONG
                EMA(9)<EMA(21) + RSI(2)>85 + volume spike -> SHORT
    Tests if RSI-2 + trend + volume is the actual edge.
    """
    c = df["close"]
    v = df["volume"]

    ema9 = ema(c, 9)
    ema21 = ema(c, 21)
    rsi2 = rsi(c, 2)
    vol_sma20 = sma(v, 20)
    vol_spike = v > 1.2 * vol_sma20

    signals = pd.Series(0, index=df.index)
    signals[(ema9 > ema21) & (rsi2 < 15) & vol_spike] = 1
    signals[(ema9 < ema21) & (rsi2 > 85) & vol_spike] = -1
    return signals


# ─── Backtester ───────────────────────────────────────────────────────────────
def backtest(df: pd.DataFrame, signals: pd.Series, atr_series: pd.Series) -> dict:
    """
    Simple bar-by-bar backtest.
    TP = 2.5x ATR, SL = 2x ATR, max hold = 20 bars, commission = 0.05%/side.
    """
    trades = []
    position = 0  # 0=flat, 1=long, -1=short
    entry_price = 0.0
    entry_bar = 0
    tp_price = 0.0
    sl_price = 0.0

    closes = df["close"].values
    highs = df["high"].values
    lows = df["low"].values
    sigs = signals.values
    atrs = atr_series.values

    for i in range(1, len(df)):
        if position != 0:
            bars_held = i - entry_bar
            # Check exits
            if position == 1:
                # TP hit
                if highs[i] >= tp_price:
                    pnl = (tp_price / entry_price - 1.0) - 2 * COMMISSION
                    trades.append({"dir": "LONG", "pnl": pnl, "bars": bars_held, "exit": "TP"})
                    position = 0
                    continue
                # SL hit
                if lows[i] <= sl_price:
                    pnl = (sl_price / entry_price - 1.0) - 2 * COMMISSION
                    trades.append({"dir": "LONG", "pnl": pnl, "bars": bars_held, "exit": "SL"})
                    position = 0
                    continue
                # Max hold
                if bars_held >= 20:
                    pnl = (closes[i] / entry_price - 1.0) - 2 * COMMISSION
                    trades.append({"dir": "LONG", "pnl": pnl, "bars": bars_held, "exit": "TIMEOUT"})
                    position = 0
                    continue
            elif position == -1:
                if lows[i] <= tp_price:
                    pnl = (1.0 - tp_price / entry_price) - 2 * COMMISSION
                    trades.append({"dir": "SHORT", "pnl": pnl, "bars": bars_held, "exit": "TP"})
                    position = 0
                    continue
                if highs[i] >= sl_price:
                    pnl = (1.0 - sl_price / entry_price) - 2 * COMMISSION
                    trades.append({"dir": "SHORT", "pnl": pnl, "bars": bars_held, "exit": "SL"})
                    position = 0
                    continue
                if bars_held >= 20:
                    pnl = (1.0 - closes[i] / entry_price) - 2 * COMMISSION
                    trades.append({"dir": "SHORT", "pnl": pnl, "bars": bars_held, "exit": "TIMEOUT"})
                    position = 0
                    continue
        else:
            # Enter on signal
            if sigs[i] != 0 and not np.isnan(atrs[i]) and atrs[i] > 0:
                position = int(sigs[i])
                entry_price = closes[i]
                entry_bar = i
                current_atr = atrs[i]
                if position == 1:
                    tp_price = entry_price + 2.5 * current_atr
                    sl_price = entry_price - 2.0 * current_atr
                else:
                    tp_price = entry_price - 2.5 * current_atr
                    sl_price = entry_price + 2.0 * current_atr

    # Close any open position at end
    if position != 0:
        bars_held = len(df) - 1 - entry_bar
        if position == 1:
            pnl = (closes[-1] / entry_price - 1.0) - 2 * COMMISSION
        else:
            pnl = (1.0 - closes[-1] / entry_price) - 2 * COMMISSION
        trades.append({"dir": "LONG" if position == 1 else "SHORT", "pnl": pnl, "bars": bars_held, "exit": "EOD"})

    return compute_stats(trades)


def compute_stats(trades: list) -> dict:
    if not trades:
        return {"trades": 0, "win_rate": 0, "profit_factor": 0, "total_pnl": 0,
                "avg_pnl": 0, "max_dd": 0, "avg_bars": 0, "longs": 0, "shorts": 0,
                "tp_exits": 0, "sl_exits": 0, "timeout_exits": 0}

    pnls = [t["pnl"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    gross_profit = sum(wins) if wins else 0
    gross_loss = abs(sum(losses)) if losses else 0.0001

    # Max drawdown (cumulative)
    cum = np.cumsum(pnls)
    peak = np.maximum.accumulate(cum)
    dd = peak - cum
    max_dd = float(np.max(dd)) if len(dd) > 0 else 0

    return {
        "trades": len(trades),
        "win_rate": round(100.0 * len(wins) / len(trades), 1),
        "profit_factor": round(gross_profit / gross_loss, 2),
        "total_pnl": round(sum(pnls) * 100, 2),  # as percent
        "avg_pnl": round(np.mean(pnls) * 100, 3),
        "max_dd": round(max_dd * 100, 2),
        "avg_bars": round(np.mean([t["bars"] for t in trades]), 1),
        "longs": sum(1 for t in trades if t["dir"] == "LONG"),
        "shorts": sum(1 for t in trades if t["dir"] == "SHORT"),
        "tp_exits": sum(1 for t in trades if t["exit"] == "TP"),
        "sl_exits": sum(1 for t in trades if t["exit"] == "SL"),
        "timeout_exits": sum(1 for t in trades if t["exit"] == "TIMEOUT"),
    }


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    all_results = {"full": {}, "simplified": {}, "meta": {
        "generated": datetime.utcnow().isoformat() + "Z",
        "bars": BARS,
        "commission": COMMISSION,
        "tp_atr_mult": 2.5,
        "sl_atr_mult": 2.0,
        "max_hold": 20,
    }}

    total_combos = len(SYMBOLS) * len(TIMEFRAMES)
    done = 0

    for symbol in SYMBOLS:
        for tf in TIMEFRAMES:
            done += 1
            tag = f"{symbol}_{tf}"
            print(f"[{done}/{total_combos}] {tag} ...", end=" ", flush=True)

            df = fetch_klines(symbol, tf, BARS)
            if df.empty or len(df) < 250:
                print("SKIP (insufficient data)")
                all_results["full"][tag] = {"trades": 0, "skip": True}
                all_results["simplified"][tag] = {"trades": 0, "skip": True}
                continue

            atr14 = atr(df["high"], df["low"], df["close"], 14)

            # Full Kimi Claw signals
            full_sigs = generate_full_signals(df)
            full_stats = backtest(df, full_sigs, atr14)
            all_results["full"][tag] = full_stats

            # Simplified signals
            simp_sigs = generate_simplified_signals(df)
            simp_stats = backtest(df, simp_sigs, atr14)
            all_results["simplified"][tag] = simp_stats

            fc = full_stats["trades"]
            sc = simp_stats["trades"]
            print(f"Full: {fc} trades, WR={full_stats['win_rate']}%, PF={full_stats['profit_factor']} | "
                  f"Simp: {sc} trades, WR={simp_stats['win_rate']}%, PF={simp_stats['profit_factor']}")

            time.sleep(0.3)  # rate limit courtesy

    # ─── Save JSON ────────────────────────────────────────────────────────────
    out_path = "E:/findtorontoevents_antigravity.ca/backtest_kimi_claw_results.json"
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to {out_path}")

    # ─── Print ranked table ───────────────────────────────────────────────────
    print("\n" + "=" * 120)
    print("KIMI CLAW PRO BACKTEST — FULL SIGNAL RESULTS (ranked by Profit Factor)")
    print("=" * 120)
    print(f"{'Asset_TF':<20} {'Trades':>6} {'WR%':>6} {'PF':>6} {'TotPnL%':>9} {'AvgPnL%':>9} "
          f"{'MaxDD%':>8} {'AvgBars':>8} {'L/S':>7} {'TP/SL/TO':>10}")
    print("-" * 120)

    full_rows = [(k, v) for k, v in all_results["full"].items() if v.get("trades", 0) > 0]
    full_rows.sort(key=lambda x: x[1]["profit_factor"], reverse=True)

    for tag, s in full_rows:
        print(f"{tag:<20} {s['trades']:>6} {s['win_rate']:>5.1f}% {s['profit_factor']:>6.2f} "
              f"{s['total_pnl']:>8.2f}% {s['avg_pnl']:>8.3f}% {s['max_dd']:>7.2f}% "
              f"{s['avg_bars']:>7.1f} {s['longs']:>3}/{s['shorts']:<3} "
              f"{s['tp_exits']:>3}/{s['sl_exits']:<3}/{s['timeout_exits']:<3}")

    print("\n" + "=" * 120)
    print("SIMPLIFIED SIGNAL RESULTS (RSI-2 + EMA cross + Volume spike)")
    print("=" * 120)
    print(f"{'Asset_TF':<20} {'Trades':>6} {'WR%':>6} {'PF':>6} {'TotPnL%':>9} {'AvgPnL%':>9} "
          f"{'MaxDD%':>8} {'AvgBars':>8} {'L/S':>7} {'TP/SL/TO':>10}")
    print("-" * 120)

    simp_rows = [(k, v) for k, v in all_results["simplified"].items() if v.get("trades", 0) > 0]
    simp_rows.sort(key=lambda x: x[1]["profit_factor"], reverse=True)

    for tag, s in simp_rows:
        print(f"{tag:<20} {s['trades']:>6} {s['win_rate']:>5.1f}% {s['profit_factor']:>6.2f} "
              f"{s['total_pnl']:>8.2f}% {s['avg_pnl']:>8.3f}% {s['max_dd']:>7.2f}% "
              f"{s['avg_bars']:>7.1f} {s['longs']:>3}/{s['shorts']:<3} "
              f"{s['tp_exits']:>3}/{s['sl_exits']:<3}/{s['timeout_exits']:<3}")

    # ─── RECOMMENDED section ──────────────────────────────────────────────────
    print("\n" + "=" * 120)
    print("RECOMMENDED CONFIGURATIONS (WR > 50%, PF > 1.2, trades >= 10)")
    print("=" * 120)

    def print_recommended(label, rows):
        rec = [(k, v) for k, v in rows if v["win_rate"] > 50 and v["profit_factor"] > 1.2 and v["trades"] >= 10]
        rec.sort(key=lambda x: x[1]["profit_factor"], reverse=True)
        if rec:
            print(f"\n  --- {label} ---")
            for tag, s in rec:
                print(f"  {tag:<20} WR={s['win_rate']:.1f}%  PF={s['profit_factor']:.2f}  "
                      f"PnL={s['total_pnl']:+.2f}%  Trades={s['trades']}  "
                      f"TP/SL/TO={s['tp_exits']}/{s['sl_exits']}/{s['timeout_exits']}")
        else:
            print(f"\n  --- {label} --- NONE met all 3 criteria")
        return rec

    full_rec = print_recommended("FULL Kimi Claw", full_rows)
    simp_rec = print_recommended("SIMPLIFIED (RSI-2 core)", simp_rows)

    # ─── Comparison ───────────────────────────────────────────────────────────
    print("\n" + "=" * 120)
    print("FULL vs SIMPLIFIED COMPARISON")
    print("=" * 120)

    all_tags = set()
    for k in all_results["full"]:
        all_tags.add(k)

    full_better = 0
    simp_better = 0
    for tag in sorted(all_tags):
        f = all_results["full"].get(tag, {})
        s = all_results["simplified"].get(tag, {})
        ft = f.get("trades", 0)
        st = s.get("trades", 0)
        if ft == 0 and st == 0:
            continue
        fpf = f.get("profit_factor", 0)
        spf = s.get("profit_factor", 0)
        winner = "FULL" if fpf >= spf else "SIMP"
        if fpf > spf:
            full_better += 1
        elif spf > fpf:
            simp_better += 1
        print(f"  {tag:<20} Full: PF={fpf:.2f} WR={f.get('win_rate',0):.1f}% ({ft}t) | "
              f"Simp: PF={spf:.2f} WR={s.get('win_rate',0):.1f}% ({st}t) -> {winner}")

    print(f"\n  Score: FULL wins {full_better} | SIMPLIFIED wins {simp_better}")
    if simp_better > full_better:
        print("  VERDICT: Simplified RSI-2 core outperforms — complexity may be hurting the full model.")
    elif full_better > simp_better:
        print("  VERDICT: Full 6-factor confluence adds genuine edge over simplified RSI-2.")
    else:
        print("  VERDICT: Tie — both approaches have comparable edge.")

    print("\nDone.")


if __name__ == "__main__":
    main()
