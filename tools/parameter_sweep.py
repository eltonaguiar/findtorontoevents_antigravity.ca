#!/usr/bin/env python3
"""
Parameter sweep for confidence/ML-score thresholds.
Adapted from Mercury's design to use dashboard_data.json closed picks
(the actual resolved outcomes, not open active_picks.json).

Author: Mercury (design) + Claude Opus 4.6 (adaptation)
"""
import json, pathlib, itertools, math, sys
import numpy as np

DATA_FILE = pathlib.Path("audit_dashboard/data/dashboard_data.json")
GRID_STEPS = 7
MIN_WR = 55.0
MIN_PF = 1.3
MIN_TRADES = 30
TOP_N = 15

def load_closed():
    with DATA_FILE.open("r", encoding="utf-8") as f:
        d = json.load(f)
    return [p for p in d["picks"].get("recent_closed", []) if (p.get("pnl_pct") or 0) != 0]

def split(picks, ratio=0.6):
    picks.sort(key=lambda p: p.get("timestamp", ""))
    n = int(len(picks) * ratio)
    return picks[:n], picks[n:]

def metrics(picks):
    n = len(picks)
    if n == 0:
        return {"n": 0, "wr": 0, "pf": 0, "sharpe": -999}
    wins = [p["pnl_pct"] for p in picks if p["pnl_pct"] > 0]
    losses = [p["pnl_pct"] for p in picks if p["pnl_pct"] <= 0]
    wr = len(wins) / n * 100
    avg_win = np.mean(wins) if wins else 0
    avg_loss = -np.mean(losses) if losses else 0.001
    pf = avg_win / avg_loss if avg_loss > 0 else 99
    pnls = np.array([p["pnl_pct"] / 100 for p in picks])
    sharpe = (pnls.mean() / pnls.std()) * math.sqrt(6 * 365) if pnls.std() > 0 else -999
    return {"n": n, "wr": round(wr, 1), "pf": round(pf, 2), "sharpe": round(sharpe, 2)}

def main():
    closed = load_closed()
    print(f"Loaded {len(closed)} closed picks from dashboard_data.json")
    train, test = split(closed)
    print(f"Train: {len(train)}, Test: {len(test)}")

    conf_vals = np.linspace(0.50, 0.85, GRID_STEPS)
    ml_vals = np.linspace(30, 80, GRID_STEPS)
    # No entry_timing_score (only 6 picks have it) — use trust_score instead
    trust_vals = np.linspace(3, 8, GRID_STEPS)

    results = []
    total = len(conf_vals) * len(ml_vals) * len(trust_vals)
    print(f"Scanning {total} combos...")

    for conf_t, ml_t, tr_t in itertools.product(conf_vals, ml_vals, trust_vals):
        def filt(picks):
            return [p for p in picks
                    if (p.get("confidence") or 0) >= conf_t
                    and (p.get("ml_composite_score") or p.get("score") or 0) >= ml_t
                    and (p.get("trust_score") or 0) >= tr_t]
        tr_f = filt(train)
        te_f = filt(test)
        tr_m = metrics(tr_f)
        te_m = metrics(te_f)
        if (tr_m["n"] >= MIN_TRADES and te_m["n"] >= MIN_TRADES
            and tr_m["wr"] >= MIN_WR and te_m["wr"] >= MIN_WR
            and tr_m["pf"] >= MIN_PF and te_m["pf"] >= MIN_PF):
            comp = 0.5 * (tr_m["wr"] + te_m["wr"]) + 0.3 * (tr_m["pf"] + te_m["pf"]) * 5
            results.append({
                "conf": round(conf_t, 3), "ml": round(ml_t, 1), "trust": round(tr_t, 1),
                "train": tr_m, "test": te_m, "composite": round(comp, 2)
            })

    results.sort(key=lambda x: -x["composite"])
    print(f"\n{'='*90}")
    print(f"TOP {min(TOP_N, len(results))} RESULTS (from {len(results)} passing combos)")
    print(f"{'='*90}")
    for i, r in enumerate(results[:TOP_N], 1):
        print(f"{i:2d}. Conf>={r['conf']:.2f} ML>={r['ml']:.0f} Trust>={r['trust']:.0f} | "
              f"Train WR:{r['train']['wr']}% PF:{r['train']['pf']} n={r['train']['n']} | "
              f"Test WR:{r['test']['wr']}% PF:{r['test']['pf']} n={r['test']['n']}")

    out = pathlib.Path("parameter_sweep_results.json")
    out.write_text(json.dumps(results[:50], indent=2))
    print(f"\nResults: {out}")

    if results:
        b = results[0]
        print(f"\nRECOMMENDED: confidence >= {b['conf']}, ml_score >= {b['ml']}, trust >= {b['trust']}")
    else:
        print("\nNo combos passed gates. Try lower thresholds.")

if __name__ == "__main__":
    main()
