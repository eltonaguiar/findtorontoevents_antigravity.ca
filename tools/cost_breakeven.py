#!/usr/bin/env python3
"""Break-even cost analysis: is the null a signal problem or a cost problem?

Every measured cell loses money after a 26bp round-turn, across five asset
classes. Two competing explanations:

  (a) the signals have no gross edge            -> signals problem
  (b) the signals have a gross edge that 26bp eats -> cost problem

These are distinguishable from data already in results/cells/*.json. The
break-even cost of a cell is exactly its GROSS mean bp/trade: if gross > 0, some
cost level below that makes it profitable. If gross <= 0, no cost level helps.

    python3 tools/cost_breakeven.py --out-dir <review repo>/30_COST_STRUCTURE
"""
import argparse
import json
import statistics as st
from pathlib import Path

CELLS = Path("/tmp/cells/results/cells")
CLASS = {
    "BTCUSDT": "CRYPTO", "ETHUSDT": "CRYPTO", "SOLUSDT": "CRYPTO",
    "XRPUSDT": "CRYPTO", "DOGEUSDT": "CRYPTO", "ADAUSDT": "CRYPTO",
    "LINKUSDT": "CRYPTO",
    "SPY": "EQUITY", "QQQ": "EQUITY", "IWM": "EQUITY", "AAPL": "EQUITY",
    "MSFT": "EQUITY", "NVDA": "EQUITY", "JPM": "EQUITY", "XLE": "EQUITY",
    "GLD": "COMMODITY_ETF", "TLT": "BOND_ETF",
    "EURUSD": "FOREX", "USDJPY": "FOREX", "GBPUSD": "FOREX",
}
COST = 26.0


def load():
    out = []
    for f in CELLS.glob("*.json"):
        if f.name.startswith("wf_"):
            continue
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        if d.get("gross_mean_bp") is None or d.get("n") is None:
            continue
        d["_class"] = CLASS.get(d["cell"].split("/")[0], "UNMAPPED")
        out.append(d)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args(argv)
    rows = load()
    if not rows:
        print("  no measured cells")
        return 1

    gross = [r["gross_mean_bp"] for r in rows]
    pos = [g for g in gross if g > 0]
    neg = [g for g in gross if g <= 0]

    print(f"  measured cells: {len(rows)}")
    print(f"  gross > 0: {len(pos)} ({len(pos)/len(rows)*100:.0f}%)   gross <= 0: {len(neg)}")
    print(f"  median GROSS bp/trade: {st.median(gross):+.2f}   (cost charged: {COST:.0f}bp)")
    print(f"  median NET   bp/trade: {st.median([r['net_mean_bp'] for r in rows]):+.2f}")

    # per class
    classes = sorted({r["_class"] for r in rows})
    per = []
    for c in classes:
        rs = [r for r in rows if r["_class"] == c]
        g = [r["gross_mean_bp"] for r in rs]
        per.append({"class": c, "n": len(rs),
                    "median_gross": round(st.median(g), 2),
                    "pct_gross_positive": round(sum(1 for x in g if x > 0) / len(g) * 100, 1),
                    "best_gross": round(max(g), 2),
                    "breakeven_cost": round(max(g), 2)})
    per.sort(key=lambda p: -p["median_gross"])

    print(f"\n  {'class':14s}{'cells':>6s}{'median gross':>14s}{'% >0':>7s}{'best gross':>12s}")
    for p in per:
        print(f"  {p['class']:14s}{p['n']:6d}{p['median_gross']:>14.2f}"
              f"{p['pct_gross_positive']:>7.1f}{p['best_gross']:>12.2f}")

    verdict, why = "", ""
    if len(pos) / len(rows) < 0.5 and st.median(gross) <= 0:
        verdict = "SIGNAL PROBLEM"
        why = ("the median cell has NO gross edge at all; lowering cost cannot "
               "rescue a negative expectancy")
    else:
        verdict = "COST PROBLEM"
        why = ("the median cell has a positive gross edge that the 26bp round-turn "
               "consumes; a lower cost assumption would change the conclusion")

    # what cost would the best few cells need?
    top = sorted(rows, key=lambda r: -r["gross_mean_bp"])[:5]
    print(f"\n  verdict: {verdict} — {why}")

    md = ["# Cost structure vs signal quality — break-even analysis", "",
          f"Source: {len(rows)} measured cell artifacts. Round-turn cost charged in the "
          f"sweep was **{COST:.0f}bp**.", "",
          "## The question", "",
          "Every class loses after cost. Either the signals have no gross edge (a signal "
          "problem), or they have one that 26bp of cost eats (a cost problem). The "
          "break-even cost of a cell *is* its gross mean bp/trade, so this is answerable "
          "from data already collected.", "",
          f"## Result: **{verdict}**", "", why, "",
          f"- Median GROSS bp/trade across all cells: **{st.median(gross):+.2f}**",
          f"- Cells with positive gross edge: **{len(pos)}/{len(rows)}** "
          f"({len(pos)/len(rows)*100:.0f}%)",
          f"- Median NET bp/trade after {COST:.0f}bp: "
          f"**{st.median([r['net_mean_bp'] for r in rows]):+.2f}**", "",
          "## Per class", "",
          "| class | cells | median gross bp | % with gross > 0 | best gross bp |",
          "|---|---:|---:|---:|---:|"]
    for p in per:
        md.append(f"| {p['class']} | {p['n']} | {p['median_gross']:+.2f} | "
                  f"{p['pct_gross_positive']:.0f}% | {p['best_gross']:+.2f} |")

    md += ["", "## The best cells and the cost they would need", "",
           "| cell | n | gross bp | break-even cost | net bp at 26bp |",
           "|---|---:|---:|---:|---:|"]
    for r in top:
        md.append(f"| `{r['cell']}` | {r['n']} | {r['gross_mean_bp']:+.2f} | "
                  f"{r['gross_mean_bp']:.2f}bp | {r['net_mean_bp']:+.2f} |")

    md += ["", "## Honest reading", "",
           "A positive gross number is not an edge. It is an edge *candidate* that must "
           "still survive the paired/permutation test and DSR deflation — and every "
           "candidate in this sweep that got that far failed them. The break-even column "
           "answers a narrower and more useful question: **at what cost would this "
           "specific rule set stop losing money?**",
           "",
           "For the cells below-zero on gross, no execution improvement helps. Those are "
           "signal problems and should be closed rather than optimised.",
           "",
           "## Consequence", "",
           "If the verdict above is SIGNAL PROBLEM, the correct action on this rule set is "
           "to stop, not to hunt for a cheaper venue. If it is COST PROBLEM, the next "
           "experiment is a fill-quality study, not another strategy."]

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "COST_VS_SIGNAL.md").write_text("\n".join(md) + "\n")
    (out / "cost_vs_signal.json").write_text(json.dumps(
        {"cells": len(rows), "cost_bp": COST, "median_gross_bp": round(st.median(gross), 2),
         "pct_gross_positive": round(len(pos) / len(rows) * 100, 1),
         "verdict": verdict, "reason": why, "per_class": per}, indent=2))
    print(f"\n  wrote {out}/COST_VS_SIGNAL.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
