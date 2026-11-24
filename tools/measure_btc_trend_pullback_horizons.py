#!/usr/bin/env python3
"""Measure BTCUSDT/trend_pullback at 4h/1d/1w by resampling the committed 1h bars.

Reuses the exact trend_pullback rule (EMA50>EMA200 uptrend + RSI14 dip through 40, hold=24 bars
of that horizon, net of 26 bp). Writes results/cells/BTCUSDT_trend_pullback_<hz>.json.
"""
import csv, json, math, random, statistics as st, subprocess
from pathlib import Path

CSV = "data/cache/BTCUSDT_3mo_1h.csv"; COST = 26.0; N_TRIALS = 1000
FACTOR = {"4h": 4, "1d": 24, "1w": 168}; HOLD = 24


def load_1h():
    rows = list(csv.reader(open(CSV)))[3:]
    out = []
    for r in rows:
        if len(r) < 2:
            continue
        try: out.append(float(r[1]))
        except: pass
    return out


def resample(closes, k):
    # take every k-th bar close as a higher-timeframe close
    return closes[::k]


def ema(v, span):
    k = 2 / (span + 1); o = [v[0]]
    for x in v[1:]: o.append(x * k + o[-1] * (1 - k))
    return o


def rsi(v, p=14):
    o = [None] * len(v); g = l = 0.0; ag = al = None
    for i in range(1, len(v)):
        ch = v[i] - v[i - 1]; gg = max(ch, 0); ll = max(-ch, 0)
        if i <= p:
            g += gg; l += ll
            if i == p: ag, al = g / p, l / p; o[i] = 100 if al == 0 else 100 - 100 / (1 + ag / al)
        else:
            ag = (ag * (p - 1) + gg) / p; al = (al * (p - 1) + ll) / p
            o[i] = 100 if al == 0 else 100 - 100 / (1 + ag / al)
    return o


def measure(hz):
    closes = resample(load_1h(), FACTOR[hz])
    if len(closes) < 220:
        return {"cell": f"BTCUSDT/trend_pullback/{hz}", "verdict": "BLOCKED_NO_DATA",
                "bars": len(closes), "reason": "fewer than 220 resampled bars"}
    e50, e200, rs = ema(closes, 50), ema(closes, 200), rsi(closes, 14)
    trades = []; i = 1
    while i < len(closes) - HOLD:
        if e50[i] > e200[i] and rs[i] is not None and rs[i - 1] is not None and rs[i] < 40 <= rs[i - 1]:
            e = closes[i]; xi = min(i + HOLD, len(closes) - 1)
            trades.append((closes[xi] / e - 1) * 1e4 - COST); i = xi + 1; continue
        i += 1
    n = len(trades)
    res = {"cell": f"BTCUSDT/trend_pullback/{hz}", "bars": len(closes), "n": n, "cost_round_turn_bp": COST,
           "hold_bars": HOLD, "source": "resampled 1h"}
    if n == 0:
        res["verdict"] = "KILLED"; res["reason"] = "n=0"; return res
    mean = st.mean(trades); rng = random.Random(7)
    bm = sorted(sum(trades[rng.randrange(n)] for _ in range(n)) / n for _ in range(4000))
    ci = [round(bm[100], 3), round(bm[3899], 3)]
    obs = abs(mean); cnt = 0
    for _ in range(5000):
        if abs(sum(trades[j] * (1 if rng.random() < .5 else -1) for j in range(n)) / n) >= obs: cnt += 1
    p = (cnt + 1) / 5001
    dsr = None
    try:
        import sys; sys.path.insert(0, ".")
        from alpha_engine.audit3_tribunal import deflated_sharpe
        d = deflated_sharpe([t / 1e4 for t in trades], N_TRIALS); dsr = round(d["dsr"], 4) if d else None
    except Exception: dsr = None
    kill = (n < 30) or (ci[0] <= 0 <= ci[1]) or (p > 0.05)
    res.update({"net_mean_bp": round(mean, 3), "ci95_bp": ci, "permutation_p": round(p, 4), "dsr": dsr,
                "dsr_n_trials": N_TRIALS, "verdict": "KILLED" if kill else "DONE"})
    return res


def main():
    out = []
    for hz in ("4h", "1d", "1w"):
        r = measure(hz)
        sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        r["git_sha"] = sha
        r["generated_at"] = __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat()
        p = Path(f"results/cells/BTCUSDT_trend_pullback_{hz}.json"); p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(r, indent=2) + "\n")
        out.append(r)
    for r in out:
        print(r["cell"], "n=%s" % r.get("n"), "net=%s" % r.get("net_mean_bp"), r["verdict"],
              r.get("ci95_bp"), "p=%s" % r.get("permutation_p"))


if __name__ == "__main__":
    main()
