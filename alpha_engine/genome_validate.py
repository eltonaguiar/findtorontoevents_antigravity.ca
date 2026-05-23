"""
Genome Validation Suite
========================
Walk-forward validation + multi-timeframe + expanded symbol testing.
Tests evolved genomes against unseen data to separate real edges from overfit.

Runs 3 parallel validation tracks:
  Track A: Walk-forward split (60/40) on 1h data for top-5 genomes
  Track B: 4h timeframe test (completely different data)
  Track C: Expanded symbol universe (12 symbols)
"""

import json
import ssl
import time
import math
import urllib.request
from typing import Dict, List

# --- Reuse backtest engine from genome_evolution -------------------------
def calc_ema(values, period):
    result = [0.0] * len(values)
    mult = 2.0 / (period + 1)
    result[0] = values[0]
    for i in range(1, len(values)):
        result[i] = values[i] * mult + result[i - 1] * (1 - mult)
    return result

def calc_atr(highs, lows, closes, period):
    n = len(closes)
    trs = [highs[0] - lows[0]]
    for i in range(1, n):
        trs.append(max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1])))
    result = [0.0] * n
    for i in range(n):
        start = max(0, i - period + 1)
        result[i] = sum(trs[start:i+1]) / (i - start + 1)
    return result

def calc_hma(values, period):
    half = max(1, period // 2)
    sqrt_n = max(1, int(period ** 0.5))
    wma_half = calc_ema(values, half)
    wma_full = calc_ema(values, period)
    raw = [2 * wma_half[i] - wma_full[i] for i in range(len(values))]
    return calc_ema(raw, sqrt_n)

def calc_sma(values, period):
    result = [0.0] * len(values)
    for i in range(len(values)):
        start = max(0, i - period + 1)
        result[i] = sum(values[start:i+1]) / (i - start + 1)
    return result

_BINANCE_KLINE_BASES = [
    "https://api.binance.com",
    "https://data-api.binance.vision",
    "https://api.binance.us",
]


def fetch_candles(symbol, interval="1h", limit=500):
    ctx = ssl.create_default_context()
    for base in _BINANCE_KLINE_BASES:
        url = f"{base}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            resp = urllib.request.urlopen(req, timeout=15, context=ctx)
            data = json.loads(resp.read())
            return [{"ts": int(k[0]), "open": float(k[1]), "high": float(k[2]),
                     "low": float(k[3]), "close": float(k[4]), "volume": float(k[5])} for k in data]
        except urllib.error.HTTPError as e:
            if e.code in (451, 403):
                continue
            time.sleep(1)
        except Exception:
            time.sleep(1)
            continue
    return []

def backtest(candles, genes):
    if len(candles) < 160:
        return []
    closes = [c["close"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    volumes = [c["volume"] for c in candles]

    ema_vals = calc_ema(closes, genes["ema_period"])
    atr_vals = calc_atr(highs, lows, closes, genes["atr_period"])
    hma_vals = calc_hma(closes, genes["hma_period"])
    atr_sma = calc_sma(atr_vals, 30)

    widths = [genes["channel_mult"] * atr_vals[i] / (ema_vals[i] + 1e-12) for i in range(len(closes))]
    trades = []
    min_bars = max(160, genes["comp_window"] + 5)
    last_sig = -999

    for i in range(min_bars, len(candles) - genes["max_hold"] - 1):
        if i - last_sig < genes.get("reentry_cooldown", 0):
            continue
        a = atr_vals[i]
        if a < 1e-12:
            continue
        atr_mean = atr_sma[i]
        atr_ratio = a / atr_mean if atr_mean > 0 else 1.0
        if atr_ratio > genes.get("vol_gate_extreme", 3.0):
            continue
        scale = 0.5 if atr_ratio > genes.get("vol_gate_high", 2.0) else 1.0

        ws = max(0, i - genes["comp_window"])
        ww = widths[ws:i]
        if len(ww) < 10:
            continue
        sw = sorted(ww)
        if widths[i-1] >= sw[len(sw)//4]:
            continue

        upper = ema_vals[i] + genes["channel_mult"] * a
        lower = ema_vals[i] - genes["channel_mult"] * a
        px = closes[i]
        hma_slope = (hma_vals[i] - hma_vals[i-1]) / (closes[i] + 1e-12)
        trend_min = genes.get("trend_strength_min", 0.0)

        vol_confirm = genes.get("volume_confirm", 0.0)
        if vol_confirm > 0:
            vol_sma_val = sum(volumes[max(0,i-19):i+1]) / min(20, i+1)
            if vol_sma_val > 0 and volumes[i] / vol_sma_val < vol_confirm:
                continue

        direction = None
        if px > upper and hma_slope > trend_min:
            direction = "LONG"
        elif px < lower and hma_slope < -trend_min:
            direction = "SHORT"
        if not direction:
            continue

        tp_dist = genes["tp_atr_mult"] * a
        sl_dist = genes["sl_atr_mult"] * a
        tp_px = px + tp_dist if direction == "LONG" else px - tp_dist
        sl_px = px - sl_dist if direction == "LONG" else px + sl_dist

        pnl = None
        bars = 0
        for j in range(i+1, min(i+1+genes["max_hold"], len(candles))):
            bars = j - i
            if direction == "LONG":
                if candles[j]["high"] >= tp_px:
                    pnl = (tp_px - px) / px * 100; break
                if candles[j]["low"] <= sl_px:
                    pnl = (sl_px - px) / px * 100; break
            else:
                if candles[j]["low"] <= tp_px:
                    pnl = (px - tp_px) / px * 100; break
                if candles[j]["high"] >= sl_px:
                    pnl = (px - sl_px) / px * 100; break
        if pnl is None:
            exit_bar = min(i + genes["max_hold"], len(candles) - 1)
            exit_px = candles[exit_bar]["close"]
            pnl = ((exit_px - px) / px * 100) if direction == "LONG" else ((px - exit_px) / px * 100)
            bars = exit_bar - i
        pnl *= scale
        trades.append({"dir": direction, "pnl": pnl, "bars": bars})
        last_sig = i
    return trades


def score_trades(trades):
    if not trades or len(trades) < 3:
        return {"trades": len(trades) if trades else 0, "wr": 0, "pf": 0, "pnl": 0, "status": "INSUFFICIENT"}
    wins = sum(1 for t in trades if t["pnl"] > 0)
    wr = wins / len(trades) * 100
    gw = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    gl = abs(sum(t["pnl"] for t in trades if t["pnl"] <= 0))
    pf = gw / gl if gl > 0 else 99.9
    pnl = sum(t["pnl"] for t in trades)
    consec = 0; max_consec = 0
    for t in trades:
        if t["pnl"] <= 0: consec += 1; max_consec = max(max_consec, consec)
        else: consec = 0
    return {"trades": len(trades), "wins": wins, "wr": round(wr, 1), "pf": round(pf, 2),
            "pnl": round(pnl, 2), "max_consec_loss": max_consec, "avg_pnl": round(pnl/len(trades), 3)}


# --- Load evolved genomes ------------------------------------------------
def load_genomes():
    with open("alpha_engine/data/genome_evolution_results.json") as f:
        data = json.load(f)
    genomes = {}
    genomes["EVOLVED_BEST"] = data["best_genome"]["genes"]
    for i, g in enumerate(data["hall_of_fame"][:5]):
        genomes[f"HOF_{i+1}"] = g["genes"]
    # Also include BASE for comparison
    genomes["BASE_ORIGINAL"] = {
        "ema_period": 30, "atr_period": 20, "channel_mult": 1.8, "comp_window": 80,
        "tp_atr_mult": 2.3, "sl_atr_mult": 1.3, "max_hold": 12, "hma_period": 21,
        "min_edge": 0.0, "vol_gate_high": 2.0, "vol_gate_extreme": 3.0,
        "trend_strength_min": 0.0, "reentry_cooldown": 0, "volume_confirm": 0.0,
    }
    # Add a "MODERATE" genome -- tight TP but less extreme than best
    genomes["MODERATE_TIGHT"] = {
        "ema_period": 30, "atr_period": 30, "channel_mult": 1.3, "comp_window": 80,
        "tp_atr_mult": 0.8, "sl_atr_mult": 1.5, "max_hold": 18, "hma_period": 30,
        "min_edge": 0.0, "vol_gate_high": 2.0, "vol_gate_extreme": 3.0,
        "trend_strength_min": 0.001, "reentry_cooldown": 0, "volume_confirm": 0.0,
    }
    # Mercury-inspired: very tight TP, moderate SL
    genomes["MERCURY_MICRO"] = {
        "ema_period": 25, "atr_period": 20, "channel_mult": 1.2, "comp_window": 60,
        "tp_atr_mult": 0.4, "sl_atr_mult": 1.0, "max_hold": 8, "hma_period": 21,
        "min_edge": 0.0, "vol_gate_high": 2.0, "vol_gate_extreme": 3.0,
        "trend_strength_min": 0.0, "reentry_cooldown": 1, "volume_confirm": 0.0,
    }
    return genomes


def main():
    print("=" * 90)
    print("  GENOME VALIDATION SUITE -- Walk-Forward + Multi-TF + Expanded Symbols")
    print("=" * 90)

    genomes = load_genomes()
    print(f"  Testing {len(genomes)} genomes\n")

    # --- TRACK A: Walk-Forward Validation (1h, 60/40 split) --------------
    print("=" * 90)
    print("  TRACK A: Walk-Forward Validation (1h, 60/40 split)")
    print("=" * 90)
    wf_symbols = ["BTCUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT"]
    wf_data = {}
    for sym in wf_symbols:
        print(f"  Fetching {sym} 1h (1000 candles)...", end=" ", flush=True)
        candles = fetch_candles(sym, "1h", 1000)
        wf_data[sym] = candles
        print(f"{len(candles)} candles")
        time.sleep(0.3)

    print(f"\n  {'Genome':<18} | {'TRAIN WR':<10} {'TRAIN PF':<10} {'TRAIN Tr':<10} | "
          f"{'TEST WR':<10} {'TEST PF':<10} {'TEST Tr':<10} {'TEST PnL':<10} | {'WR Change':<10} {'Verdict':<12}")
    print(f"  {'-'*130}")

    wf_results = {}
    for name, genes in genomes.items():
        train_all = []
        test_all = []
        for sym, candles in wf_data.items():
            if not candles:
                continue
            split = int(len(candles) * 0.6)
            train_candles = candles[:split]
            test_candles = candles[split:]

            train_trades = backtest(train_candles, genes)
            test_trades = backtest(test_candles, genes)
            train_all.extend(train_trades)
            test_all.extend(test_trades)

        train_s = score_trades(train_all)
        test_s = score_trades(test_all)

        wr_change = test_s["wr"] - train_s["wr"] if train_s["wr"] > 0 and test_s["wr"] > 0 else -999

        if test_s["trades"] < 5:
            verdict = "NO_DATA"
        elif test_s["wr"] >= 65 and test_s["pf"] >= 2.0:
            verdict = "ROBUST"
        elif test_s["wr"] >= 55 and test_s["pf"] >= 1.3:
            verdict = "PROMISING"
        elif test_s["wr"] >= 50 and test_s["pf"] >= 1.0:
            verdict = "MARGINAL"
        elif wr_change < -20:
            verdict = "OVERFIT"
        else:
            verdict = "WEAK"

        wf_results[name] = {"train": train_s, "test": test_s, "wr_change": round(wr_change, 1), "verdict": verdict}

        print(f"  {name:<18} | {train_s['wr']:<10.1f} {train_s['pf']:<10.2f} {train_s['trades']:<10} | "
              f"{test_s['wr']:<10.1f} {test_s['pf']:<10.2f} {test_s['trades']:<10} {test_s['pnl']:<+10.2f} | "
              f"{wr_change:<+10.1f} {verdict:<12}")

    # --- TRACK B: 4h Timeframe Test --------------------------------------
    print(f"\n{'=' * 90}")
    print("  TRACK B: 4h Timeframe Test (completely different data)")
    print("=" * 90)
    tf4h_symbols = ["BTCUSDT", "SOLUSDT", "BNBUSDT", "ETHUSDT"]
    tf4h_data = {}
    for sym in tf4h_symbols:
        print(f"  Fetching {sym} 4h (500 candles)...", end=" ", flush=True)
        candles = fetch_candles(sym, "4h", 500)
        tf4h_data[sym] = candles
        print(f"{len(candles)} candles")
        time.sleep(0.3)

    print(f"\n  {'Genome':<18} | {'WR%':<8} {'PF':<8} {'Trades':<8} {'PnL%':<10} {'Syms OK':<8} {'Verdict':<12}")
    print(f"  {'-'*80}")

    tf4h_results = {}
    for name, genes in genomes.items():
        all_trades = []
        syms_ok = 0
        for sym, candles in tf4h_data.items():
            if not candles: continue
            trades = backtest(candles, genes)
            if trades:
                s = score_trades(trades)
                if s["pnl"] > 0: syms_ok += 1
                all_trades.extend(trades)

        s = score_trades(all_trades)
        verdict = "ROBUST" if s["wr"] >= 60 and s["pf"] >= 1.5 else ("PROMISING" if s["wr"] >= 50 and s["pf"] >= 1.0 else "WEAK")
        tf4h_results[name] = {**s, "syms_ok": syms_ok, "verdict": verdict}
        print(f"  {name:<18} | {s['wr']:<8.1f} {s['pf']:<8.2f} {s['trades']:<8} {s['pnl']:<+10.2f} {syms_ok}/{len(tf4h_symbols):<5} {verdict:<12}")

    # --- TRACK C: Expanded Symbol Universe -------------------------------
    print(f"\n{'=' * 90}")
    print("  TRACK C: Expanded Symbol Universe (12 symbols, 1h)")
    print("=" * 90)
    expanded = ["BTCUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT", "ETHUSDT", "XRPUSDT",
                "AVAXUSDT", "LINKUSDT", "ADAUSDT", "NEARUSDT", "DOTUSDT", "LTCUSDT"]
    exp_data = {}
    for sym in expanded:
        if sym in wf_data:
            exp_data[sym] = wf_data[sym]
        else:
            print(f"  Fetching {sym} 1h...", end=" ", flush=True)
            candles = fetch_candles(sym, "1h", 1000)
            exp_data[sym] = candles
            print(f"{len(candles)}")
            time.sleep(0.3)

    # Only test top 3 genomes from walk-forward + BASE + MODERATE
    top_genomes_for_expansion = {}
    # Sort WF results by test WR, take top survivors
    wf_sorted = sorted(wf_results.items(), key=lambda x: (x[1]["test"]["wr"] if x[1]["test"]["trades"] >= 5 else 0), reverse=True)
    for name, _ in wf_sorted[:4]:
        top_genomes_for_expansion[name] = genomes[name]
    top_genomes_for_expansion["BASE_ORIGINAL"] = genomes["BASE_ORIGINAL"]

    print(f"\n  Testing top walk-forward survivors on {len(expanded)} symbols:")
    for name, genes in top_genomes_for_expansion.items():
        print(f"\n  {name}:")
        print(f"    {'Symbol':<12} {'Trades':<8} {'WR%':<8} {'PF':<8} {'PnL%':<10} {'Verdict'}")
        print(f"    {'-'*60}")
        total_t = 0; total_w = 0; total_pnl = 0; sym_pass = 0
        for sym in expanded:
            candles = exp_data.get(sym, [])
            if not candles: continue
            # Use last 40% as test
            test_start = int(len(candles) * 0.6)
            test_candles = candles[test_start:]
            trades = backtest(test_candles, genes)
            s = score_trades(trades)
            v = "PASS" if s["wr"] >= 55 and s["pf"] >= 1.0 and s["trades"] >= 3 else ("MARGINAL" if s["wr"] >= 45 else "FAIL")
            if v == "PASS": sym_pass += 1
            total_t += s["trades"]; total_w += s.get("wins", 0); total_pnl += s["pnl"]
            print(f"    {sym:<12} {s['trades']:<8} {s['wr']:<8.1f} {s['pf']:<8.2f} {s['pnl']:<+10.2f} {v}")
        wr_all = total_w / total_t * 100 if total_t > 0 else 0
        print(f"    {'TOTAL':<12} {total_t:<8} {wr_all:<8.1f} {'---':<8} {total_pnl:<+10.2f} {sym_pass}/{len(expanded)} pass")

    # --- FINAL RANKING ---------------------------------------------------
    print(f"\n{'=' * 90}")
    print("  FINAL RANKING -- Combined Score (WF + 4h + Symbol Breadth)")
    print("=" * 90)

    final_scores = {}
    for name in genomes:
        wf = wf_results.get(name, {})
        tf = tf4h_results.get(name, {})
        test_wr = wf.get("test", {}).get("wr", 0)
        test_pf = wf.get("test", {}).get("pf", 0)
        test_trades = wf.get("test", {}).get("trades", 0)
        wr_change = wf.get("wr_change", -999)
        tf_wr = tf.get("wr", 0)
        tf_pf = tf.get("pf", 0)

        # Penalize massive WR drop (overfit signal)
        overfit_penalty = 1.0
        if wr_change < -20: overfit_penalty = 0.3
        elif wr_change < -10: overfit_penalty = 0.6
        elif wr_change < -5: overfit_penalty = 0.8

        # Combine: 50% walk-forward, 30% 4h robustness, 20% trade count confidence
        wf_score = (test_wr / 100) * min(test_pf, 10) * overfit_penalty
        tf_score = (tf_wr / 100) * min(tf_pf, 10)
        trade_conf = min(1.0, test_trades / 50)
        combined = wf_score * 0.50 + tf_score * 0.30 + trade_conf * 0.20

        final_scores[name] = {
            "combined": round(combined, 4),
            "wf_wr": test_wr, "wf_pf": test_pf, "wf_trades": test_trades,
            "wr_change": wr_change, "overfit_penalty": overfit_penalty,
            "tf4h_wr": tf_wr, "tf4h_pf": tf_pf,
            "wf_verdict": wf.get("verdict", "?"), "tf_verdict": tf.get("verdict", "?"),
        }

    ranked = sorted(final_scores.items(), key=lambda x: x[1]["combined"], reverse=True)

    print(f"\n  {'#':<3} {'Genome':<18} {'Score':<8} {'WF WR':<8} {'WF PF':<8} {'WR Chg':<8} "
          f"{'4h WR':<8} {'4h PF':<8} {'WF Verdict':<12} {'4h Verdict':<12}")
    print(f"  {'-'*110}")
    for i, (name, sc) in enumerate(ranked):
        print(f"  {i+1:<3} {name:<18} {sc['combined']:<8.4f} {sc['wf_wr']:<8.1f} {sc['wf_pf']:<8.2f} "
              f"{sc['wr_change']:<+8.1f} {sc['tf4h_wr']:<8.1f} {sc['tf4h_pf']:<8.2f} "
              f"{sc['wf_verdict']:<12} {sc['tf_verdict']:<12}")

    # Save results
    output = {
        "walk_forward": wf_results,
        "timeframe_4h": tf4h_results,
        "final_ranking": {name: sc for name, sc in ranked},
        "genomes": {name: genes for name, genes in genomes.items()},
    }
    with open("alpha_engine/data/genome_validation_results.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Results saved to alpha_engine/data/genome_validation_results.json")

    # Return top genome name for downstream use
    winner = ranked[0][0]
    print(f"\n  WINNER: {winner}")
    print(f"  Parameters: {json.dumps(genomes[winner], indent=2)}")
    return winner, genomes[winner]


if __name__ == "__main__":
    start = time.time()
    winner, params = main()
    print(f"\n  Total time: {time.time()-start:.1f}s")
