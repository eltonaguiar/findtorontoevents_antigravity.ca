#!/usr/bin/env python3
"""filter_bias_check.py — does the DATED-ONLY filter flatter class means? (FreeBuff's finding, applied to us)

FreeBuff showed that quarantining zero-PnL rows deletes breakeven trades and flatters a class.
This checks the analogous risk in MY method: I compute on dated rows only (entry_date set). If the
dateless rows are systematically worse, excluding them flatters every class.

Reports, per class: ALL-rows mean, DATED-only mean, and the bias (dated - all). Positive bias = flattering.
"""
import json, statistics as st, sys, glob
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

def main():
    cp = json.load(open("alpha_engine/data/closed_picks.json"))
    def mb(rows):
        d = defaultdict(list)
        for r in rows:
            if r.get("pnl_pct") is not None:
                d[r.get("asset_class") or "UNKNOWN"].append(float(r["pnl_pct"]))
        return {k: (len(v), st.mean(v)) for k, v in d.items()}
    allm = mb(cp)
    dated = mb([r for r in cp if r.get("entry_date")])
    rows = []
    for c in sorted(set(allm) | set(dated)):
        an, am = allm.get(c, (0, 0.0)); dn, dm = dated.get(c, (0, 0.0))
        rows.append({"class": c, "all_n": an, "all_mean_pct": round(am, 4),
                     "dated_n": dn, "dated_mean_pct": round(dm, 4),
                     "bias_pct": round(dm - am, 4) if dn and an else None})
    zero = [r for r in cp if r.get("pnl_pct") is not None and abs(float(r["pnl_pct"])) < 1e-9]
    out = {"generated_at": __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(),
           "finding": "dated-only filter flatters classes when dateless rows are worse",
           "zero_pnl_rows": len(zero),
           "zero_pnl_dated": sum(1 for r in zero if r.get("entry_date")),
           "note": "we KEEP breakevens (all zero-pnl rows are dated) - good; but dateless exclusion still biases",
           "per_class": rows}
    Path("reports/filter_bias_check.json").write_text(json.dumps(out, indent=2) + "\n")
    print(f"{'class':10s}{'ALL n':>6s}{'ALL%':>9s}{'DATED n':>8s}{'DATED%':>9s}{'bias%':>9s}")
    for r in rows:
        print(f"{r['class']:10s}{r['all_n']:6d}{r['all_mean_pct']:9.3f}{r['dated_n']:8d}{r['dated_mean_pct']:9.3f}{str(r['bias_pct']):>9s}")
    print(f"\nzero-pnl rows: {len(zero)} (all dated: {out['zero_pnl_dated']}) -> breakevens kept")

if __name__ == "__main__":
    main()
