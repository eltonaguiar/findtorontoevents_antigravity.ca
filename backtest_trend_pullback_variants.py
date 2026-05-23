"""
Trend Pullback Strategy - Parameter Grid Backtester
====================================================
Tests RSI/ADX/TP/SL/hold variants across 15 symbols on 1d and 4h timeframes.

CRITICAL: No look-ahead bias. Entry is next-bar open after signal.
"""

import json
import time
import math
import urllib.request
import urllib.error
from itertools import product
from statistics import mean, stdev

OUTPUT_JSON = "e:/findtorontoevents_antigravity.ca/backtest_trend_pullback_variants.json"

SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT",
    "AVAXUSDT", "LINKUSDT", "DOGEUSDT", "LTCUSDT", "XRPUSDT",
    "NEARUSDT", "DOTUSDT", "ATOMUSDT", "TRXUSDT", "MATICUSDT",
]
TIMEFRAMES = ["1d", "4h"]

# Grid
RSI_THRESHOLDS = [10, 15, 20, 25, 30]
ADX_THRESHOLDS = [10, 15, 20, 25]
TP_MULTS = [2.0, 2.5, 3.0, 3.5]
SL_MULTS = [1.0, 1.5, 2.0]
MAX_HOLDS = [5, 10, 15, 20]

BINANCE_HOSTS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://data-api.binance.vision",
]

DEFAULT_PARAMS = {"rsi": 20, "adx": 15, "tp": 2.5, "sl": 1.5, "hold": 10}


# ---------- Data fetch ----------
def fetch_klines(symbol, interval, limit=1500):
    """Fetch with failover across Binance mirrors."""
    last_err = None
    for host in BINANCE_HOSTS:
        url = f"{host}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return [
                    {
                        "open_time": k[0],
                        "open": float(k[1]),
                        "high": float(k[2]),
                        "low": float(k[3]),
                        "close": float(k[4]),
                        "volume": float(k[5]),
                    }
                    for k in data
                ]
        except Exception as e:
            last_err = e
            continue
    print(f"    [WARN] fetch failed {symbol} {interval}: {last_err}")
    return []


# ---------- Indicators ----------
def ema(values, period):
    k = 2.0 / (period + 1)
    out = [None] * len(values)
    if len(values) < period:
        return out
    seed = sum(values[:period]) / period
    out[period - 1] = seed
    for i in range(period, len(values)):
        out[i] = values[i] * k + out[i - 1] * (1 - k)
    return out


def rsi(values, period):
    out = [None] * len(values)
    if len(values) <= period:
        return out
    gains = 0.0
    losses = 0.0
    for i in range(1, period + 1):
        diff = values[i] - values[i - 1]
        if diff >= 0:
            gains += diff
        else:
            losses -= diff
    avg_gain = gains / period
    avg_loss = losses / period
    rs = avg_gain / avg_loss if avg_loss > 0 else float("inf")
    out[period] = 100.0 - 100.0 / (1.0 + rs) if avg_loss > 0 else 100.0
    for i in range(period + 1, len(values)):
        diff = values[i] - values[i - 1]
        gain = diff if diff > 0 else 0.0
        loss = -diff if diff < 0 else 0.0
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        if avg_loss == 0:
            out[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            out[i] = 100.0 - 100.0 / (1.0 + rs)
    return out


def atr_and_adx(candles, period=14):
    """Wilder's ATR and ADX."""
    n = len(candles)
    atr = [None] * n
    adx_out = [None] * n
    if n < period * 2 + 1:
        return atr, adx_out

    tr_list = [0.0] * n
    plus_dm = [0.0] * n
    minus_dm = [0.0] * n

    for i in range(1, n):
        high = candles[i]["high"]
        low = candles[i]["low"]
        prev_close = candles[i - 1]["close"]
        prev_high = candles[i - 1]["high"]
        prev_low = candles[i - 1]["low"]
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        tr_list[i] = tr
        up = high - prev_high
        down = prev_low - low
        plus_dm[i] = up if (up > down and up > 0) else 0.0
        minus_dm[i] = down if (down > up and down > 0) else 0.0

    # Wilder smoothing
    tr_sm = sum(tr_list[1:period + 1])
    plus_sm = sum(plus_dm[1:period + 1])
    minus_sm = sum(minus_dm[1:period + 1])
    atr[period] = tr_sm / period

    dx_list = []
    plus_di = 100.0 * plus_sm / tr_sm if tr_sm > 0 else 0.0
    minus_di = 100.0 * minus_sm / tr_sm if tr_sm > 0 else 0.0
    dx = 100.0 * abs(plus_di - minus_di) / (plus_di + minus_di) if (plus_di + minus_di) > 0 else 0.0
    dx_list.append(dx)

    for i in range(period + 1, n):
        tr_sm = tr_sm - (tr_sm / period) + tr_list[i]
        plus_sm = plus_sm - (plus_sm / period) + plus_dm[i]
        minus_sm = minus_sm - (minus_sm / period) + minus_dm[i]
        atr[i] = tr_sm / period
        plus_di = 100.0 * plus_sm / tr_sm if tr_sm > 0 else 0.0
        minus_di = 100.0 * minus_sm / tr_sm if tr_sm > 0 else 0.0
        dx = 100.0 * abs(plus_di - minus_di) / (plus_di + minus_di) if (plus_di + minus_di) > 0 else 0.0
        dx_list.append(dx)

    # ADX = Wilder smoothed DX over 'period'
    if len(dx_list) >= period:
        first_adx = sum(dx_list[:period]) / period
        adx_idx = period + period  # first adx at index 2*period
        if adx_idx < n:
            adx_out[adx_idx] = first_adx
            cur_adx = first_adx
            for j in range(period, len(dx_list)):
                cur_adx = (cur_adx * (period - 1) + dx_list[j]) / period
                idx_pos = period + 1 + j
                if idx_pos < n:
                    adx_out[idx_pos] = cur_adx
    return atr, adx_out


# ---------- Backtest single combo ----------
def backtest(candles, ema50, ema200, rsi2, atr14, adx14,
             rsi_th, adx_th, tp_mult, sl_mult, max_hold):
    trades = []
    n = len(candles)
    i = 0
    # Need ema200 ready
    while i < n - 2:
        # Skip if indicators not ready
        if (ema50[i] is None or ema200[i] is None or rsi2[i] is None
                or atr14[i] is None or adx14[i] is None):
            i += 1
            continue

        close = candles[i]["close"]
        long_trend = ema50[i] > ema200[i] and close > ema200[i]
        short_trend = ema50[i] < ema200[i] and close < ema200[i]
        adx_ok = adx14[i] > adx_th

        direction = None
        if long_trend and rsi2[i] < rsi_th and adx_ok:
            direction = "LONG"
        elif short_trend and rsi2[i] > (100 - rsi_th) and adx_ok:
            direction = "SHORT"

        if direction is None:
            i += 1
            continue

        entry_idx = i + 1
        if entry_idx >= n - 1:
            break
        entry = candles[entry_idx]["open"]
        at = atr14[i]
        if at <= 0:
            i += 1
            continue

        if direction == "LONG":
            tp = entry + tp_mult * at
            sl = entry - sl_mult * at
        else:
            tp = entry - tp_mult * at
            sl = entry + sl_mult * at

        exit_price = None
        exit_reason = "TIMEOUT"
        bars_held = 0
        for j in range(entry_idx, min(entry_idx + max_hold, n)):
            bar = candles[j]
            bars_held = j - entry_idx + 1
            if direction == "LONG":
                if bar["low"] <= sl:
                    exit_price = sl
                    exit_reason = "SL"
                    break
                if bar["high"] >= tp:
                    exit_price = tp
                    exit_reason = "TP"
                    break
            else:
                if bar["high"] >= sl:
                    exit_price = sl
                    exit_reason = "SL"
                    break
                if bar["low"] <= tp:
                    exit_price = tp
                    exit_reason = "TP"
                    break
        if exit_price is None:
            final_j = min(entry_idx + max_hold - 1, n - 1)
            exit_price = candles[final_j]["close"]
            bars_held = final_j - entry_idx + 1

        if direction == "LONG":
            ret = (exit_price - entry) / entry
        else:
            ret = (entry - exit_price) / entry

        trades.append({
            "dir": direction,
            "ret": ret,
            "reason": exit_reason,
            "bars": bars_held,
        })
        # Advance past the trade to avoid overlap
        i = entry_idx + bars_held
    return trades


def summarize(trades):
    if not trades:
        return None
    wins = [t["ret"] for t in trades if t["ret"] > 0]
    losses = [t["ret"] for t in trades if t["ret"] <= 0]
    wr = len(wins) / len(trades) * 100.0
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    pf = gross_win / gross_loss if gross_loss > 0 else float("inf")
    avg = mean([t["ret"] for t in trades])
    sd = stdev([t["ret"] for t in trades]) if len(trades) > 1 else 0.0001
    sharpe = avg / sd * math.sqrt(len(trades)) if sd > 0 else 0.0
    longs = [t for t in trades if t["dir"] == "LONG"]
    shorts = [t for t in trades if t["dir"] == "SHORT"]
    def sub(tl):
        if not tl:
            return {"trades": 0, "wr": 0, "pf": 0, "avg_ret": 0}
        w = [t["ret"] for t in tl if t["ret"] > 0]
        l = [t["ret"] for t in tl if t["ret"] <= 0]
        gw = sum(w)
        gl = abs(sum(l))
        return {
            "trades": len(tl),
            "wr": len(w) / len(tl) * 100.0,
            "pf": gw / gl if gl > 0 else float("inf"),
            "avg_ret": mean([t["ret"] for t in tl]),
        }
    return {
        "trades": len(trades),
        "wr": wr,
        "pf": pf if pf != float("inf") else 999.0,
        "avg_ret": avg,
        "sharpe": sharpe,
        "total_ret": sum(t["ret"] for t in trades),
        "long": sub(longs),
        "short": sub(shorts),
    }


def main():
    print("=" * 80)
    print("TREND PULLBACK PARAMETER GRID BACKTEST")
    print("=" * 80)
    print(f"Symbols: {len(SYMBOLS)} | Timeframes: {TIMEFRAMES}")
    total_combos = (len(RSI_THRESHOLDS) * len(ADX_THRESHOLDS) * len(TP_MULTS)
                    * len(SL_MULTS) * len(MAX_HOLDS))
    print(f"Grid: {total_combos} combos per (symbol,tf)")
    print()

    # Fetch all data first
    data = {}
    for sym in SYMBOLS:
        for tf in TIMEFRAMES:
            print(f"Fetching {sym} {tf}...", end=" ", flush=True)
            c = fetch_klines(sym, tf, 1500)
            if len(c) < 250:
                print(f"SKIP (only {len(c)} bars)")
                continue
            print(f"{len(c)} bars")
            closes = [x["close"] for x in c]
            ema50v = ema(closes, 50)
            ema200v = ema(closes, 200)
            rsi2v = rsi(closes, 2)
            atrv, adxv = atr_and_adx(c, 14)
            data[(sym, tf)] = {
                "candles": c,
                "ema50": ema50v,
                "ema200": ema200v,
                "rsi2": rsi2v,
                "atr": atrv,
                "adx": adxv,
            }
            time.sleep(0.1)

    print(f"\nLoaded {len(data)} (symbol,tf) pairs\n")

    # Build combos
    combos = list(product(RSI_THRESHOLDS, ADX_THRESHOLDS, TP_MULTS, SL_MULTS, MAX_HOLDS))

    # Per-combo aggregated results (across all symbols/tfs)
    combo_results = {}
    # Per-(symbol,tf,combo) for best-per-symbol
    per_symbol_results = {}

    print("Running grid (aggregated across symbols/tfs)...")
    for ci, (rth, ath, tpm, slm, mh) in enumerate(combos):
        all_trades = []
        for key, d in data.items():
            trades = backtest(
                d["candles"], d["ema50"], d["ema200"], d["rsi2"],
                d["atr"], d["adx"],
                rth, ath, tpm, slm, mh,
            )
            # Early stop per (symbol,tf)
            if len(trades) < 5:
                pass
            all_trades.extend(trades)
            per_symbol_results.setdefault(key, {})[(rth, ath, tpm, slm, mh)] = trades

        if len(all_trades) < 10:
            continue
        summ = summarize(all_trades)
        if summ:
            summ["params"] = {"rsi": rth, "adx": ath, "tp": tpm, "sl": slm, "hold": mh}
            combo_results[(rth, ath, tpm, slm, mh)] = summ
        if (ci + 1) % 100 == 0:
            print(f"  processed {ci+1}/{len(combos)}")

    print(f"\nValid combos (>=10 trades): {len(combo_results)}\n")

    # Rank by Sharpe
    ranked = sorted(combo_results.values(), key=lambda s: s["sharpe"], reverse=True)

    print("=" * 80)
    print("TOP 20 COMBOS BY SHARPE")
    print("=" * 80)
    header = f"{'Rank':>4} {'RSI':>4} {'ADX':>4} {'TP':>4} {'SL':>4} {'HLD':>4} {'Trd':>5} {'WR%':>6} {'PF':>6} {'Sharpe':>7} {'TotRet':>8}"
    print(header)
    print("-" * len(header))
    for rank, s in enumerate(ranked[:20], 1):
        p = s["params"]
        print(f"{rank:>4} {p['rsi']:>4} {p['adx']:>4} {p['tp']:>4} {p['sl']:>4} {p['hold']:>4} "
              f"{s['trades']:>5} {s['wr']:>6.2f} {s['pf']:>6.2f} {s['sharpe']:>7.3f} {s['total_ret']*100:>7.1f}%")

    # Default comparison
    print("\n" + "=" * 80)
    print("DEFAULT PARAMS COMPARISON (RSI<20, ADX>15, TP 2.5x, SL 1.5x, hold 10)")
    print("=" * 80)
    dk = (20, 15, 2.5, 1.5, 10)
    if dk in combo_results:
        dsumm = combo_results[dk]
        # Rank of default
        default_rank = next((i for i, s in enumerate(ranked, 1) if s["params"] == DEFAULT_PARAMS), None)
        print(f"Default: trades={dsumm['trades']} WR={dsumm['wr']:.2f}% PF={dsumm['pf']:.2f} "
              f"Sharpe={dsumm['sharpe']:.3f} TotRet={dsumm['total_ret']*100:.1f}%")
        print(f"Default rank: #{default_rank} of {len(ranked)}")
        best = ranked[0]
        bp = best["params"]
        print(f"Best:    RSI={bp['rsi']} ADX={bp['adx']} TP={bp['tp']} SL={bp['sl']} HLD={bp['hold']} "
              f"Sharpe={best['sharpe']:.3f}")
        if best["sharpe"] > dsumm["sharpe"]:
            print(f">>> Best beats default by {best['sharpe'] - dsumm['sharpe']:.3f} Sharpe")
        else:
            print(">>> Default is among top combos")
    else:
        print("Default had <10 trades (invalid)")

    # Long vs Short for top 10
    print("\n" + "=" * 80)
    print("LONG vs SHORT BREAKDOWN (Top 10)")
    print("=" * 80)
    print(f"{'Rnk':>3} {'Params (R/A/TP/SL/H)':>22} | {'L.Trd':>5} {'L.WR%':>6} {'L.PF':>5} | {'S.Trd':>5} {'S.WR%':>6} {'S.PF':>5}")
    print("-" * 80)
    for rank, s in enumerate(ranked[:10], 1):
        p = s["params"]
        pstr = f"{p['rsi']}/{p['adx']}/{p['tp']}/{p['sl']}/{p['hold']}"
        L, S = s["long"], s["short"]
        print(f"{rank:>3} {pstr:>22} | {L['trades']:>5} {L['wr']:>6.2f} {L['pf']:>5.2f} | "
              f"{S['trades']:>5} {S['wr']:>6.2f} {S['pf']:>5.2f}")

    # Best per symbol
    print("\n" + "=" * 80)
    print("BEST PARAMS PER SYMBOL (Sharpe)")
    print("=" * 80)
    print(f"{'Symbol':>10} {'TF':>4} {'RSI':>4} {'ADX':>4} {'TP':>4} {'SL':>4} {'HLD':>4} {'Trd':>4} {'WR%':>6} {'PF':>6} {'Sharpe':>7}")
    print("-" * 80)
    per_symbol_best = {}
    for key, combo_trades in per_symbol_results.items():
        best_s = None
        best_combo = None
        for combo, trades in combo_trades.items():
            if len(trades) < 10:
                continue
            s = summarize(trades)
            if s and (best_s is None or s["sharpe"] > best_s["sharpe"]):
                best_s = s
                best_combo = combo
        if best_s:
            per_symbol_best[f"{key[0]}_{key[1]}"] = {
                "params": {
                    "rsi": best_combo[0], "adx": best_combo[1],
                    "tp": best_combo[2], "sl": best_combo[3], "hold": best_combo[4]
                },
                "stats": best_s,
            }
            sym, tf = key
            p = best_combo
            print(f"{sym:>10} {tf:>4} {p[0]:>4} {p[1]:>4} {p[2]:>4} {p[3]:>4} {p[4]:>4} "
                  f"{best_s['trades']:>4} {best_s['wr']:>6.2f} {best_s['pf']:>6.2f} {best_s['sharpe']:>7.3f}")

    # Success criteria
    print("\n" + "=" * 80)
    print("SUCCESS CRITERIA: WR>45% AND PF>1.3 AND Sharpe>0.8 on 100+ trades")
    print("=" * 80)
    winners = [s for s in ranked if s["wr"] > 45 and s["pf"] > 1.3
               and s["sharpe"] > 0.8 and s["trades"] >= 100]
    print(f"Found {len(winners)} combos meeting criteria.")
    for s in winners[:10]:
        p = s["params"]
        print(f"  RSI<{p['rsi']} ADX>{p['adx']} TP={p['tp']}x SL={p['sl']}x HLD={p['hold']}: "
              f"trd={s['trades']} WR={s['wr']:.2f}% PF={s['pf']:.2f} Sharpe={s['sharpe']:.3f}")

    # Save
    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "grid": {
            "rsi": RSI_THRESHOLDS, "adx": ADX_THRESHOLDS,
            "tp": TP_MULTS, "sl": SL_MULTS, "hold": MAX_HOLDS,
        },
        "symbols": SYMBOLS,
        "timeframes": TIMEFRAMES,
        "valid_combos": len(combo_results),
        "top_20": ranked[:20],
        "default_params": DEFAULT_PARAMS,
        "default_stats": combo_results.get(dk),
        "winners_criteria": winners[:50],
        "per_symbol_best": per_symbol_best,
    }
    with open(OUTPUT_JSON, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nSaved to {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
