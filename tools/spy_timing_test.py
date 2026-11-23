#!/usr/bin/env python3
"""spy_timing_test.py — can a simple timing rule beat BUY-AND-HOLD on real dated bars?

Real dated data (market_prices.csv, 2021-11-15..2026-11-13, adjusted close). Tests the
most common retail timing claims against buy-and-hold on SPY, net of the ETF round trip:
  - 200-day moving-average timing (long when close>SMA200)
  - 10-month (210-day) MA timing
  - vol targeting (scale exposure to a 10% vol target, cap 2x)
Metric: annualised return, vol, Sharpe, max drawdown, and the DIFERENCE vs buy-and-hold
with a bootstrap CI. If the difference CI includes 0, timing does not beat the benchmark.
"""
import csv, json, math, random, statistics as st
from pathlib import Path

SRC = "2026-11-15_AM_profitability-plan/copilot-financial-review/market_prices.csv"
COST_RT = 0.067122 / 100.0  # ETF round trip, COST_OF_RECORD, as a fraction


def load(col="SPY_adj"):
    rows = list(csv.DictReader(open(SRC)))
    dates, px = [], []
    for r in rows:
        try:
            v = float(r[col])
        except Exception:
            continue
        dates.append(r["date"]); px.append(v)
    return dates, px


def returns(px):
    return [px[i] / px[i - 1] - 1 for i in range(1, len(px))]


def sma_timing(px, window, cost=COST_RT):
    """Long when close> Sma(window), else cash (0). Pay cost on each switch."""
    out = []
    pos = 0
    sd = 0.0
    for i in range(window, len(px) - 1):
        s = sum(px[i - window + 1:i + 1]) / window
        newpos = 1 if px[i] > s else 0
        r = px[i + 1] / px[i] - 1
        moved = abs(newpos - pos)
        out.append(newpos * r - moved * cost)
        pos = newpos
    return out


def vol_target(px, target=0.10, window=20, cap=2.0, cost=COST_RT):
    rr = [px[i] / px[i - 1] - 1 for i in range(1, len(px))]
    out = []
    prev_w = 1.0
    for i in range(window, len(rr)):
        v = st.pstdev(rr[i - window:i]) * math.sqrt(252)
        w = min(cap, max(0.0, target / v)) if v > 0 else 1.0
        out.append(w * rr[i] - abs(w - prev_w) * cost)
        prev_w = w
    return out


def stats(r, ann=252):
    if len(r) < 2:
        return None
    mu = st.mean(r) * ann
    sd = st.pstdev(r) * math.sqrt(ann)
    eq, peak, mdd = 1.0, 1.0, 0.0
    for x in r:
        eq *= (1 + x); peak = max(peak, eq); mdd = min(mdd, eq / peak - 1)
    return {"ann_ret": round(mu * 100, 2), "ann_vol": round(sd * 100, 2),
            "sharpe": round(mu / sd, 3) if sd else None, "max_dd": round(mdd * 100, 2),
            "n": len(r)}


def boot_diff_ci(a, b, n_boot=4000, seed=7):
    n = min(len(a), len(b)); a, b = a[-n:], b[-n:]
    d = [x - y for x, y in zip(a, b)]
    rng = random.Random(seed)
    means = sorted(sum(d[rng.randrange(n)] for _ in range(n)) / n for _ in range(n_boot))
    return {"mean_diff_ann_pct": round(st.mean(d) * 252 * 100, 2),
            "ci_lo_ann_pct": round(means[int(0.025 * n_boot)] * 252 * 100, 2),
            "ci_hi_ann_pct": round(means[int(0.975 * n_boot) - 1] * 252 * 100, 2)}


def main():
    dates, px = load()
    bh = returns(px)
    out = {"generated_at": __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(),
           "source": SRC, "period": [dates[0], dates[-1]], "n_days": len(bh),
           "cost_rt_pct": COST_RT * 100, "buy_and_hold": stats(bh), "rules": {}}
    for name, r in [("sma200", sma_timing(px, 200)), ("sma210", sma_timing(px, 210)),
                    ("vol_target_10pct", vol_target(px))]:
        s = stats(r)
        # both series end at the final bar, so align by trailing length
        bh_aligned = bh[-len(r):]
        d = boot_diff_ci(r, bh_aligned) if r else None
        beats = bool(d and d["ci_lo_ann_pct"] > 0)
        out["rules"][name] = {"stats": s, "buyhold_same_window": stats(bh[-len(r):]) if r else None,
                               "vs_buyhold": d, "beats_buyhold_CI_excludes_0": beats}
    Path("reports/spy_timing_test.json").write_text(json.dumps(out, indent=2) + "\n")
    print("buy-and-hold:", out["buy_and_hold"])
    for k, v in out["rules"].items():
        print(f"{k:16s}", "rule", v["stats"], "\n                 BH-same-window", v["buyhold_same_window"],
              "\n                 diff", v["vs_buyhold"], "BEATS:", v["beats_buyhold_CI_excludes_0"])


if __name__ == "__main__":
    main()
