"""Item 11: cross-venue basis (Binance vs KuCoin vs Kraken), 1-minute candles.

Harvest test: is the cross-venue price basis bigger than the measured all-in
cost of entering on one venue and exiting on the other?  Measured all-in round
trip at $10k (reports/cost_measurement_20261122.json): Binance BTC 20.00bp,
KuCoin 20.48bp, Kraken 52.02bp.  Two-venue thresholds are the sums:
Binance<->KuCoin 40.48bp, Binance<->Kraken 72.02bp, KuCoin<->Kraken 72.50bp.

Data: public REST 1m OHLC, no keys.  Binance /api/v3/klines, KuCoin
/api/v1/market/candles, Kraken /0/public/OHLC.  Overlap is intersected on
exact minute timestamps; nothing is interpolated.
"""
import json
import math
import os
import statistics as st
import time
import urllib.request
from datetime import datetime, timezone

import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYMBOL = "BTCUSDT"
BINANCE_PAGES = 6        # 1000 bars/page -> ~6000 minutes (~4.2 days)
KRAKEN_MAX_BARS = 720
SEED = 20261122
N_BOOT = 10000


def get(url, tries=3, pause=1.0):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "research/1.0"})
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            if k == tries - 1:
                raise
            time.sleep(pause)


def binance_1m(pages=BINANCE_PAGES):
    out = {}
    end = None
    for _ in range(pages):
        url = f"https://api.binance.com/api/v3/klines?symbol={SYMBOL}&interval=1m&limit=1000"
        if end:
            url += f"&endTime={end}"
        d = get(url)
        for k in d:
            out[int(k[0]) // 60000] = float(k[4])
        end = int(d[0][0]) - 1
        time.sleep(0.25)
    return out


def kucoin_1m(minutes_back=KRAKEN_MAX_BARS):
    # KuCoin caps at 180 bars per request even with startAt/endAt, so page
    # backwards in 180-minute chunks to cover the same window as Kraken.
    out = {}
    end = int(time.time())
    start = end - minutes_back * 60
    while end > start:
        chunk_start = max(start, end - 180 * 60)
        url = (f"https://api.kucoin.com/api/v1/market/candles?type=1min&symbol=BTC-USDT"
               f"&startAt={chunk_start}&endAt={end}")
        d = get(url)
        for k in (d.get("data") or []):
            out[int(k[0]) // 60] = float(k[2])   # [time, open, close, high, low, ...]
        end = chunk_start - 1
        time.sleep(0.2)
    return out


def kraken_1m():
    d = get("https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=1")
    res = d["result"]
    key = [k for k in res if k != "last"][0]
    out = {}
    for k in res[key][-KRAKEN_MAX_BARS:]:
        out[int(k[0]) // 60] = float(k[4])
    return out


def maxdd(eq):
    peak, dd = -1e9, 0.0
    for v in eq:
        peak = max(peak, v)
        dd = min(dd, v / peak - 1)
    return dd


def skew(x):
    a = np.asarray(x, float)
    s = a.std(ddof=0)
    return float(((a - a.mean()) ** 3).mean() / s ** 3) if s > 0 else 0.0


def main():
    print("pulling 1m candles ...")
    b = binance_1m()
    print(f"binance: {len(b)} minutes")
    try:
        k = kucoin_1m()
        print(f"kucoin: {len(k)} minutes")
    except Exception as e:
        print(f"kucoin FAILED: {e}")
        k = {}
    try:
        kr = kraken_1m()
        print(f"kraken: {len(kr)} minutes")
    except Exception as e:
        print(f"kraken FAILED: {e}")
        kr = {}

    ts = sorted(set(b) & set(k) & set(kr))
    print(f"3-way overlap: {len(ts)} minutes "
          f"({datetime.fromtimestamp(ts[0]*60, timezone.utc)} .. {datetime.fromtimestamp(ts[-1]*60, timezone.utc)})" if ts else "no overlap")

    out = {"item": 11, "strategy": "cross_venue_basis", "symbol": SYMBOL,
           "generated_utc": datetime.now(timezone.utc).isoformat(),
           "bars": {"binance": len(b), "kucoin": len(k), "kraken": len(kr), "overlap_3way": len(ts)},
           "overlap_window": [datetime.fromtimestamp(ts[0]*60, timezone.utc).isoformat(),
                              datetime.fromtimestamp(ts[-1]*60, timezone.utc).isoformat()] if ts else None,
           "break_even_bp_2venue": {"binance_kucoin": 40.48, "binance_kraken": 72.02, "kucoin_kraken": 72.50},
           "pairs": {}}
    if len(ts) < 300:
        out["verdict"] = "BLOCKED_DATA"
        out["note"] = "insufficient 3-way overlap"
    else:
        for (na, A), (nb, B), thr in [(("binance", b), ("kucoin", k), 40.48),
                                     (("binance", b), ("kraken", kr), 72.02),
                                     (("kucoin", k), ("kraken", kr), 72.50)]:
            basis = [(A[t] - B[t]) / ((A[t] + B[t]) / 2) * 1e4 for t in ts]
            basis = np.asarray(basis, float)
            absb = np.abs(basis)
            above = float((absb > thr).mean())
            stat = {"mean_bp": float(basis.mean()), "median_bp": float(np.median(basis)),
                    "sd_bp": float(basis.std(ddof=1)), "min_bp": float(basis.min()),
                    "max_bp": float(basis.max()), "p1_bp": float(np.percentile(basis, 1)),
                    "p99_bp": float(np.percentile(basis, 99)), "skew": skew(basis),
                    "threshold_bp": thr,
                    "frac_abs_gt_threshold": above,
                    "persistence_note": "naive minute count; a trade needs the gap to persist for entry+exit latency"}
            out["pairs"][f"{na}_vs_{nb}"] = stat
            print(f"{na} vs {nb}: median={stat['median_bp']:.2f}bp sd={stat['sd_bp']:.2f} max|={max(abs(stat['min_bp']),stat['max_bp']):.2f} frac>40bp={above:.4%}")
        # decisive number: best pair's frac above break-even
        best = max(out["pairs"].items(), key=lambda kv: kv[1]["frac_abs_gt_threshold"])
        out["verdict"] = "MARGINAL" if best[1]["frac_abs_gt_threshold"] > 0.01 else "KILL"
        out["decisive"] = {"best_pair": best[0], "frac_abs_gt_threshold": best[1]["frac_abs_gt_threshold"]}

    os.makedirs(os.path.join(BASE, "reports"), exist_ok=True)
    with open(os.path.join(BASE, "reports", "cross_venue_basis_20261122.json"), "w") as f:
        json.dump(out, f, indent=1)
    print("verdict:", out.get("verdict"))


if __name__ == "__main__":
    main()
