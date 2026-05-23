#!/usr/bin/env python3
"""
Backtest Novel Strategies 10-12
- Strategy 10: Fair Value Gap (FVG) Contrarian
- Strategy 11: Volume-Weighted Momentum (VWMA vs EMA)
- Strategy 12: Dual Timeframe RSI Confluence

Tests on 10 symbols x 3 timeframes, Binance API with failover.
"""

import json, time, sys, os
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# ─── Binance API failover ───────────────────────────────────────────
BINANCE_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]

SYMBOLS = ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","AVAXUSDT",
           "ADAUSDT","LINKUSDT","DOGEUSDT","LTCUSDT","XRPUSDT"]
TIMEFRAMES = ["1h","4h","1d"]
COMMISSION = 0.0005  # 0.05%
BARS = 1000

def fetch_klines(symbol, interval, limit=1000):
    """Fetch klines with Binance mirror failover."""
    for base in BINANCE_MIRRORS:
        url = f"{base}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            # Parse into list of dicts
            candles = []
            for k in data:
                candles.append({
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                })
            return candles
        except Exception as e:
            print(f"  [failover] {base} failed for {symbol} {interval}: {e}")
            continue
    print(f"  [ERROR] All mirrors failed for {symbol} {interval}")
    return None

# ─── Indicators ─────────────────────────────────────────────────────
def calc_rsi(closes, period=14):
    """RSI array, first `period` values are None."""
    rsi = [None] * len(closes)
    if len(closes) < period + 1:
        return rsi
    gains, losses = 0.0, 0.0
    for i in range(1, period + 1):
        delta = closes[i] - closes[i-1]
        if delta > 0: gains += delta
        else: losses -= delta
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0:
        rsi[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi[period] = 100 - 100 / (1 + rs)
    for i in range(period + 1, len(closes)):
        delta = closes[i] - closes[i-1]
        g = delta if delta > 0 else 0
        l = -delta if delta < 0 else 0
        avg_gain = (avg_gain * (period - 1) + g) / period
        avg_loss = (avg_loss * (period - 1) + l) / period
        if avg_loss == 0:
            rsi[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[i] = 100 - 100 / (1 + rs)
    return rsi

def calc_atr(candles, period=14):
    """ATR array."""
    atr = [None] * len(candles)
    if len(candles) < period + 1:
        return atr
    trs = []
    for i in range(1, len(candles)):
        h = candles[i]["high"]
        l = candles[i]["low"]
        pc = candles[i-1]["close"]
        tr = max(h - l, abs(h - pc), abs(l - pc))
        trs.append(tr)
    # first ATR = SMA of first `period` TRs
    if len(trs) < period:
        return atr
    avg = sum(trs[:period]) / period
    atr[period] = avg
    for i in range(period, len(trs)):
        avg = (avg * (period - 1) + trs[i]) / period
        atr[i + 1] = avg
    return atr

def calc_ema(values, period):
    """EMA array (None where insufficient data)."""
    ema = [None] * len(values)
    k = 2 / (period + 1)
    # find first non-None
    start = None
    for i, v in enumerate(values):
        if v is not None:
            start = i
            break
    if start is None or (len(values) - start) < period:
        return ema
    # seed with SMA
    sma = sum(values[start:start+period]) / period
    ema[start + period - 1] = sma
    for i in range(start + period, len(values)):
        if values[i] is None:
            ema[i] = ema[i-1]
        else:
            ema[i] = values[i] * k + ema[i-1] * (1 - k)
    return ema

def calc_vwma(candles, period):
    """VWMA array."""
    vwma = [None] * len(candles)
    for i in range(period - 1, len(candles)):
        cv_sum = sum(candles[j]["close"] * candles[j]["volume"] for j in range(i - period + 1, i + 1))
        v_sum = sum(candles[j]["volume"] for j in range(i - period + 1, i + 1))
        vwma[i] = cv_sum / v_sum if v_sum > 0 else candles[i]["close"]
    return vwma

def calc_adx(candles, period=14):
    """ADX array."""
    adx = [None] * len(candles)
    if len(candles) < 2 * period + 1:
        return adx
    plus_dm_list = []
    minus_dm_list = []
    tr_list = []
    for i in range(1, len(candles)):
        h = candles[i]["high"]
        l = candles[i]["low"]
        ph = candles[i-1]["high"]
        pl = candles[i-1]["low"]
        pc = candles[i-1]["close"]
        up = h - ph
        down = pl - l
        plus_dm = up if (up > down and up > 0) else 0
        minus_dm = down if (down > up and down > 0) else 0
        tr = max(h - l, abs(h - pc), abs(l - pc))
        plus_dm_list.append(plus_dm)
        minus_dm_list.append(minus_dm)
        tr_list.append(tr)

    if len(tr_list) < period:
        return adx

    # Smoothed sums
    atr_s = sum(tr_list[:period])
    pdm_s = sum(plus_dm_list[:period])
    mdm_s = sum(minus_dm_list[:period])

    dx_list = []
    for i in range(period, len(tr_list)):
        atr_s = atr_s - atr_s / period + tr_list[i]
        pdm_s = pdm_s - pdm_s / period + plus_dm_list[i]
        mdm_s = mdm_s - mdm_s / period + minus_dm_list[i]
        if atr_s == 0:
            dx_list.append(0)
            continue
        plus_di = 100 * pdm_s / atr_s
        minus_di = 100 * mdm_s / atr_s
        di_sum = plus_di + minus_di
        dx = 100 * abs(plus_di - minus_di) / di_sum if di_sum > 0 else 0
        dx_list.append(dx)

    if len(dx_list) < period:
        return adx

    adx_val = sum(dx_list[:period]) / period
    idx_base = 2 * period  # candle index where first ADX is ready
    if idx_base < len(candles):
        adx[idx_base] = adx_val
    for i in range(period, len(dx_list)):
        adx_val = (adx_val * (period - 1) + dx_list[i]) / period
        ci = i + period + 1  # candle index
        if ci < len(candles):
            adx[ci] = adx_val
    return adx

# ─── Trade simulator ────────────────────────────────────────────────
def simulate_trades(signals, candles, commission=COMMISSION):
    """
    signals: list of (bar_index, direction, tp_atr_mult, sl_atr_mult, max_hold)
    Returns list of trade dicts.
    """
    atr = calc_atr(candles)
    trades = []
    for idx, direction, tp_mult, sl_mult, max_hold in signals:
        if idx >= len(candles) - 1:
            continue
        if atr[idx] is None or atr[idx] == 0:
            continue
        entry = candles[idx]["close"]
        a = atr[idx]
        if direction == "LONG":
            tp = entry + tp_mult * a
            sl = entry - sl_mult * a
        else:
            tp = entry - tp_mult * a
            sl = entry + sl_mult * a

        exit_price = None
        exit_bar = None
        exit_reason = None
        for j in range(idx + 1, min(idx + 1 + max_hold, len(candles))):
            h = candles[j]["high"]
            l = candles[j]["low"]
            if direction == "LONG":
                if l <= sl:
                    exit_price = sl; exit_bar = j; exit_reason = "SL"; break
                if h >= tp:
                    exit_price = tp; exit_bar = j; exit_reason = "TP"; break
            else:
                if h >= sl:
                    exit_price = sl; exit_bar = j; exit_reason = "SL"; break
                if l <= tp:
                    exit_price = tp; exit_bar = j; exit_reason = "TP"; break
        if exit_price is None:
            # max hold exit
            exit_bar = min(idx + max_hold, len(candles) - 1)
            exit_price = candles[exit_bar]["close"]
            exit_reason = "HOLD"

        if direction == "LONG":
            pnl_pct = (exit_price - entry) / entry - 2 * commission
        else:
            pnl_pct = (entry - exit_price) / entry - 2 * commission

        trades.append({
            "entry_bar": idx,
            "exit_bar": exit_bar,
            "direction": direction,
            "entry": entry,
            "exit": exit_price,
            "pnl_pct": pnl_pct,
            "reason": exit_reason,
        })
    return trades

def calc_stats(trades):
    """Calculate strategy statistics from trades."""
    if not trades:
        return {"trades": 0, "win_rate": 0, "pf": 0, "total_pnl": 0, "avg_pnl": 0,
                "max_dd_pct": 0, "avg_hold": 0, "sharpe": 0}
    wins = [t for t in trades if t["pnl_pct"] > 0]
    losses = [t for t in trades if t["pnl_pct"] <= 0]
    gross_profit = sum(t["pnl_pct"] for t in wins) if wins else 0
    gross_loss = abs(sum(t["pnl_pct"] for t in losses)) if losses else 0.0001
    total_pnl = sum(t["pnl_pct"] for t in trades)
    pnls = [t["pnl_pct"] for t in trades]
    avg_pnl = total_pnl / len(trades)
    # Sharpe (simplified)
    if len(pnls) > 1:
        import statistics
        std = statistics.stdev(pnls)
        sharpe = (avg_pnl / std) * (len(pnls) ** 0.5) if std > 0 else 0
    else:
        sharpe = 0
    # Max drawdown on cumulative equity
    cum = 0; peak = 0; max_dd = 0
    for p in pnls:
        cum += p
        if cum > peak: peak = cum
        dd = peak - cum
        if dd > max_dd: max_dd = dd
    avg_hold = sum(t["exit_bar"] - t["entry_bar"] for t in trades) / len(trades)
    return {
        "trades": len(trades),
        "win_rate": round(100 * len(wins) / len(trades), 1),
        "pf": round(gross_profit / gross_loss, 2) if gross_loss > 0 else 99.0,
        "total_pnl": round(100 * total_pnl, 2),
        "avg_pnl": round(100 * avg_pnl, 3),
        "max_dd_pct": round(100 * max_dd, 2),
        "avg_hold": round(avg_hold, 1),
        "sharpe": round(sharpe, 2),
    }

# ─── Strategy Implementations ──────────────────────────────────────
def strategy_10_fvg_contrarian(candles):
    """Fair Value Gap Contrarian: bearish FVG + RSI<40 → LONG, bullish FVG + RSI>60 → SHORT."""
    closes = [c["close"] for c in candles]
    rsi = calc_rsi(closes, 14)
    signals = []
    for i in range(2, len(candles)):
        if rsi[i] is None:
            continue
        c0 = candles[i - 2]  # oldest of the 3
        c1 = candles[i - 1]  # middle
        c2 = candles[i]      # newest

        # Bearish FVG: c2.high < c0.low (gap down) → contrarian LONG
        if c2["high"] < c0["low"] and rsi[i] < 40:
            signals.append((i, "LONG", 1.5, 1.0, 8))

        # Bullish FVG: c2.low > c0.high (gap up) → contrarian SHORT
        if c2["low"] > c0["high"] and rsi[i] > 60:
            signals.append((i, "SHORT", 1.5, 1.0, 8))

    return simulate_trades(signals, candles)

def strategy_11_vwma_momentum(candles):
    """Volume-Weighted Momentum: VWMA vs EMA crossover with ADX filter."""
    closes = [c["close"] for c in candles]
    vwma = calc_vwma(candles, 20)
    ema = calc_ema(closes, 20)
    adx = calc_adx(candles, 14)
    signals = []
    for i in range(2, len(candles)):
        if vwma[i] is None or ema[i] is None or adx[i] is None:
            continue
        if vwma[i-2] is None or ema[i-2] is None:
            continue
        if adx[i] < 20:
            continue

        # Check fresh crossover in last 2 bars
        vwma_above_now = vwma[i] > ema[i]
        vwma_above_prev1 = vwma[i-1] > ema[i-1] if (vwma[i-1] is not None and ema[i-1] is not None) else None
        vwma_above_prev2 = vwma[i-2] > ema[i-2]

        crossed_up = vwma_above_now and (vwma_above_prev1 == False or vwma_above_prev2 == False)
        crossed_down = not vwma_above_now and (vwma_above_prev1 == True or vwma_above_prev2 == True)

        if crossed_up and closes[i] > vwma[i]:
            signals.append((i, "LONG", 2.0, 1.5, 15))
        elif crossed_down and closes[i] < vwma[i]:
            signals.append((i, "SHORT", 2.0, 1.5, 15))

    return simulate_trades(signals, candles)

def strategy_12_dual_tf_rsi(candles):
    """Dual Timeframe RSI Confluence: RSI on 1x and approximated 4x timeframe."""
    closes = [c["close"] for c in candles]
    rsi_lower = calc_rsi(closes, 14)

    # Approximate higher TF by sampling every 4th bar's close
    htf_closes_full = [None] * len(candles)
    for i in range(0, len(candles), 4):
        htf_closes_full[i] = closes[i]
    # Forward-fill
    last = None
    for i in range(len(htf_closes_full)):
        if htf_closes_full[i] is not None:
            last = htf_closes_full[i]
        else:
            htf_closes_full[i] = last
    # Some early values may still be None
    if htf_closes_full[0] is None:
        htf_closes_full[0] = closes[0]
        for i in range(1, len(htf_closes_full)):
            if htf_closes_full[i] is None:
                htf_closes_full[i] = htf_closes_full[i-1]

    rsi_higher = calc_rsi(htf_closes_full, 14)

    signals = []
    for i in range(1, len(candles)):
        if rsi_lower[i] is None or rsi_higher[i] is None:
            continue
        # LONG: both oversold
        if rsi_lower[i] < 35 and rsi_higher[i] < 35:
            signals.append((i, "LONG", 2.5, 1.5, 12))
        # SHORT: both overbought
        elif rsi_lower[i] > 65 and rsi_higher[i] > 65:
            signals.append((i, "SHORT", 2.5, 1.5, 12))

    return simulate_trades(signals, candles)

# ─── Main ───────────────────────────────────────────────────────────
def main():
    strategies = {
        "S10_FVG_Contrarian": strategy_10_fvg_contrarian,
        "S11_VWMA_Momentum": strategy_11_vwma_momentum,
        "S12_DualTF_RSI": strategy_12_dual_tf_rsi,
    }

    all_results = []
    total_combos = len(SYMBOLS) * len(TIMEFRAMES)
    done = 0

    for symbol in SYMBOLS:
        for tf in TIMEFRAMES:
            done += 1
            print(f"[{done}/{total_combos}] {symbol} {tf} ... ", end="", flush=True)
            candles = fetch_klines(symbol, tf, BARS)
            if candles is None or len(candles) < 100:
                print("SKIP (no data)")
                continue
            print(f"{len(candles)} bars", end="")

            for sname, sfunc in strategies.items():
                trades = sfunc(candles)
                stats = calc_stats(trades)
                stats["strategy"] = sname
                stats["symbol"] = symbol
                stats["timeframe"] = tf
                all_results.append(stats)

            print(f" | done")
            time.sleep(0.15)  # rate limit courtesy

    # Save JSON
    out_path = "e:/findtorontoevents_antigravity.ca/backtest_novel_strategy_results.json"
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to {out_path}")

    # ─── Display ranked table ───────────────────────────────────────
    # Filter PF > 1.0 and trades >= 10
    qualified = [r for r in all_results if r["pf"] > 1.0 and r["trades"] >= 10]
    qualified.sort(key=lambda x: x["pf"], reverse=True)

    print("\n" + "=" * 120)
    print("RANKED RESULTS (PF > 1.0, trades >= 10)")
    print("=" * 120)
    hdr = f"{'Rank':<5} {'Strategy':<22} {'Symbol':<10} {'TF':<5} {'Trades':>7} {'WR%':>7} {'PF':>7} {'TotalPnL%':>10} {'AvgPnL%':>9} {'MaxDD%':>8} {'AvgHold':>8} {'Sharpe':>7}"
    print(hdr)
    print("-" * 120)
    for i, r in enumerate(qualified, 1):
        print(f"{i:<5} {r['strategy']:<22} {r['symbol']:<10} {r['timeframe']:<5} "
              f"{r['trades']:>7} {r['win_rate']:>6.1f}% {r['pf']:>7.2f} "
              f"{r['total_pnl']:>9.2f}% {r['avg_pnl']:>8.3f}% "
              f"{r['max_dd_pct']:>7.2f}% {r['avg_hold']:>7.1f}  {r['sharpe']:>6.2f}")

    if not qualified:
        print("  (no results meet PF>1.0 and trades>=10 filter)")

    # ─── Recommended section ────────────────────────────────────────
    recommended = [r for r in all_results if r["win_rate"] > 50 and r["pf"] > 1.2 and r["trades"] >= 15]
    recommended.sort(key=lambda x: x["pf"], reverse=True)

    print("\n" + "=" * 120)
    print("RECOMMENDED (WR > 50%, PF > 1.2, trades >= 15)")
    print("=" * 120)
    if recommended:
        print(hdr)
        print("-" * 120)
        for i, r in enumerate(recommended, 1):
            print(f"{i:<5} {r['strategy']:<22} {r['symbol']:<10} {r['timeframe']:<5} "
                  f"{r['trades']:>7} {r['win_rate']:>6.1f}% {r['pf']:>7.2f} "
                  f"{r['total_pnl']:>9.2f}% {r['avg_pnl']:>8.3f}% "
                  f"{r['max_dd_pct']:>7.2f}% {r['avg_hold']:>7.1f}  {r['sharpe']:>6.2f}")
    else:
        print("  (no results meet all recommended criteria)")

    # ─── Summary by strategy ────────────────────────────────────────
    print("\n" + "=" * 120)
    print("AGGREGATE SUMMARY BY STRATEGY")
    print("=" * 120)
    for sname in strategies:
        strats = [r for r in all_results if r["strategy"] == sname]
        total_trades = sum(r["trades"] for r in strats)
        if total_trades == 0:
            print(f"  {sname}: 0 trades across all combos")
            continue
        avg_wr = sum(r["win_rate"] * r["trades"] for r in strats if r["trades"] > 0) / total_trades
        avg_pf_vals = [r["pf"] for r in strats if r["trades"] >= 5]
        avg_pf = sum(avg_pf_vals) / len(avg_pf_vals) if avg_pf_vals else 0
        total_pnl = sum(r["total_pnl"] for r in strats)
        qualified_count = len([r for r in strats if r["pf"] > 1.0 and r["trades"] >= 10])
        recommended_count = len([r for r in strats if r["win_rate"] > 50 and r["pf"] > 1.2 and r["trades"] >= 15])
        print(f"  {sname:<22} | Total trades: {total_trades:>5} | Avg WR: {avg_wr:>5.1f}% | "
              f"Avg PF: {avg_pf:>5.2f} | Sum PnL: {total_pnl:>8.2f}% | "
              f"Qualified: {qualified_count} | Recommended: {recommended_count}")

    print("\nDone.")

if __name__ == "__main__":
    main()
