#!/usr/bin/env python3
"""Measure BTCUSDT/trend_pullback/1h for the 1000-cell backlog.

trend_pullback (LONG): uptrend when EMA50>EMA200 on close; enter on the bar AFTER RSI14 crosses
below 40 (a dip within the trend); exit at close after HOLD=24 bars. Net return per trade in bp
after a 26 bp round-turn. Reports n, net mean bp, 95% bootstrap CI, permutation p, DSR (N=1000
backlog trials). Kill rule: n<30 OR CI includes 0 OR perm p>0.05 -> KILLED (valid completion).
"""
import csv, json, math, random, statistics as st, subprocess
from pathlib import Path

CSV = "data/cache/BTCUSDT_3mo_1h.csv"
HOLD = 24
COST_BP = 26.0
N_TRIALS = 1000
OUT = Path("results/cells/BTCUSDT_trend_pullback_1h.json")


def load_close():
    rows = []
    with open(CSV) as f:
        r = csv.reader(f)
        allrows = list(r)
    # yfinance 3-row header: Price, Ticker, Datetime then data
    data = allrows[3:]
    for row in data:
        if len(row) < 2:
            continue
        try:
            close = float(row[1])
        except Exception:
            continue
        rows.append((row[0], close))
    return rows


def ema(vals, span):
    k = 2.0 / (span + 1.0)
    out = [vals[0]]
    for v in vals[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def rsi(vals, period=14):
    out = [None] * len(vals)
    gains = losses = 0.0
    for i in range(1, len(vals)):
        ch = vals[i] - vals[i - 1]
        g = max(ch, 0.0); l = max(-ch, 0.0)
        if i <= period:
            gains += g; losses += l
            if i == period:
                ag, al = gains / period, losses / period
                out[i] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
        else:
            ag = (ag * (period - 1) + g) / period
            al = (al * (period - 1) + l) / period
            out[i] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


def main():
    rows = load_close()
    if len(rows) < 250:
        print(f"BLOCKED: only {len(rows)} bars"); return 2
    close = [c for _, c in rows]
    e50, e200, rs = ema(close, 50), ema(close, 200), rsi(close, 14)
    trades = []
    i = 1
    while i < len(close) - HOLD:
        if e50[i] > e200[i] and rs[i] is not None and rs[i - 1] is not None:
            if rs[i] < 40 and rs[i - 1] >= 40:   # RSI dips through 40 within an uptrend
                entry = close[i]                     # enter at this close (signal bar close)
                exit_i = min(i + HOLD, len(close) - 1)
                ret_bp = (close[exit_i] / entry - 1) * 1e4 - COST_BP
                trades.append(ret_bp)
                i = exit_i + 1                       # no overlap
                continue
        i += 1
    n = len(trades)
    res = {"cell": "BTCUSDT/trend_pullback/1h", "bars": len(close), "n": n,
           "cost_round_turn_bp": COST_BP, "hold_bars": HOLD,
           "bars_source": CSV}
    if n == 0:
        res.update({"verdict": "KILLED", "reason": "n=0: strategy never fired"}); write(res); return 0
    mean = st.mean(trades)
    # 95% bootstrap CI (resample trades)
    rng = random.Random(7)
    bm = sorted(sum(trades[rng.randrange(n)] for _ in range(n)) / n for _ in range(4000))
    ci = [round(bm[int(0.025 * 4000)], 3), round(bm[int(0.975 * 4000) - 1], 3)]
    # permutation p: shuffle SIGNS of trade returns; p = P(|perm mean| >= |obs|)
    obs = abs(mean); cnt = 0; REP = 5000
    for _ in range(REP):
        s = sum(trades[j] * (1 if rng.random() < 0.5 else -1) for j in range(n)) / n
        if abs(s) >= obs:
            cnt += 1
    p_perm = (cnt + 1) / (REP + 1)
    # DSR via repo function if available
    dsr = None
    try:
        import sys; sys.path.insert(0, ".")
        from alpha_engine.audit3_tribunal import deflated_sharpe
        fr = [t / 1e4 for t in trades]
        d = deflated_sharpe(fr, N_TRIALS)
        dsr = round(d["dsr"], 4) if d else None
    except Exception as e:
        dsr = None
    killed = (n < 30) or (ci[0] <= 0 <= ci[1]) or (p_perm > 0.05)
    res.update({"net_mean_bp": round(mean, 3), "ci95_bp": ci, "permutation_p": round(p_perm, 4),
                "dsr": dsr, "dsr_n_trials": N_TRIALS,
                "verdict": "KILLED" if killed else "DONE",
                "kill_reasons": [r for r, c in (("n<30", n < 30), ("CI includes 0", ci[0] <= 0 <= ci[1]),
                                                ("perm p>0.05", p_perm > 0.05)) if c]})
    write(res)
    print(json.dumps({k: res[k] for k in ("n", "net_mean_bp", "ci95_bp", "permutation_p", "dsr", "verdict")}, indent=1))


def write(res):
    sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    res["git_sha"] = sha
    res["generated_at"] = __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
