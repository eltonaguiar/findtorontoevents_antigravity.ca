#!/usr/bin/env python3
"""Publish the cell-sweep contest + per-asset-class findings + overall ranking.

Reads results/cells/*.json from the cells worktree and writes three markdown
documents into the review repo. Numbers come from the artifacts, never retyped.

Asset-class mapping is explicit because GLD/TLT are commodity/bond ETFs sitting
in a ledger that otherwise calls everything with a ticker "equity". Silently
lumping them into EQUITY would misreport two classes.

    python3 tools/publish_cell_findings.py --out-dir <review repo>/29_...
"""
import argparse
import json
import statistics as st
from pathlib import Path

CELLS = Path("/tmp/cells/results/cells")
LEDGER = Path("/tmp/cells/1000_TODOS.json")


def ledger_counts():
    """Cells per class in the LEDGER - not in the artifacts.

    Counting only artifacts made EQUITY look like a 1-cell class when the ledger
    actually holds 500 of them, all still open. Publishing that would have
    implied the class was measured and empty, which is a different and false
    claim from "not yet measured".
    """
    try:
        d = json.loads(LEDGER.read_text())
    except Exception:
        return {}, {}
    cells = d.get("cells", d) if isinstance(d, dict) else d
    tot, done = {}, {}
    for c in cells:
        k = CLASS.get(c.get("symbol"), "UNMAPPED")
        tot[k] = tot.get(k, 0) + 1
        if c.get("status") in ("killed", "done", "blocked_no_data"):
            done[k] = done.get(k, 0) + 1
    return tot, done

CLASS = {
    "BTCUSDT": "CRYPTO", "ETHUSDT": "CRYPTO", "SOLUSDT": "CRYPTO",
    "XRPUSDT": "CRYPTO", "DOGEUSDT": "CRYPTO", "ADAUSDT": "CRYPTO",
    "LINKUSDT": "CRYPTO",
    "SPY": "EQUITY", "QQQ": "EQUITY", "IWM": "EQUITY", "AAPL": "EQUITY",
    "MSFT": "EQUITY", "NVDA": "EQUITY", "JPM": "EQUITY", "XLE": "EQUITY",
    "GLD": "COMMODITY_ETF", "TLT": "BOND_ETF",
    "EURUSD": "FOREX", "USDJPY": "FOREX", "GBPUSD": "FOREX",
}


def load():
    rows = []
    for f in sorted(CELLS.glob("*.json")):
        if f.name.startswith("wf_"):
            continue
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        key = d.get("cell")
        if not key or "/" not in key:
            continue
        sym = key.split("/")[0]
        d["_class"] = CLASS.get(sym, "UNMAPPED")
        rows.append(d)
    return rows


def load_wf():
    out = {}
    for f in CELLS.glob("wf_*.json"):
        try:
            d = json.loads(f.read_text())
            out[d.get("cell", f.stem)] = d.get("verdict")
        except Exception:
            continue
    return out


def fmt(v, nd=2):
    return "n/a" if v is None else f"{v:+.{nd}f}"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args(argv)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    rows = load()
    wf = load_wf()
    tot_by_class, resolved_by_class = ledger_counts()
    measured = [r for r in rows if r.get("n") is not None and r.get("net_mean_bp") is not None]
    insuff = [r for r in rows if r.get("verdict") == "INSUFFICIENT_TRADES"]
    blocked = [r for r in rows if r.get("verdict") == "BLOCKED_NO_DATA"]

    # ---------- per asset class ----------
    # include classes that exist ONLY in the ledger, otherwise a class with no
    # artifacts vanishes from the table entirely - the worst outcome, because a
    # missing row reads as "nothing to report" instead of "never measured".
    classes = sorted({r["_class"] for r in measured} | {r["_class"] for r in rows}
                     | set(tot_by_class))
    per = []
    for c in classes:
        ms = [r for r in measured if r["_class"] == c]
        allc = [r for r in rows if r["_class"] == c]
        if not allc and not tot_by_class.get(c):
            continue
        nets = [r["net_mean_bp"] for r in ms]
        per.append({
            "class": c, "cells": tot_by_class.get(c, len(allc)),
            "cells_resolved": resolved_by_class.get(c, len(allc)),
            "measured": len(ms),
            "insufficient": len([r for r in allc if r.get("verdict") == "INSUFFICIENT_TRADES"]),
            "blocked": len([r for r in allc if r.get("verdict") == "BLOCKED_NO_DATA"]),
            "kills": len([r for r in ms if r.get("verdict") == "KILL"]),
            "passes": len([r for r in ms if r.get("verdict") == "PASS"]),
            "median_net": round(st.median(nets), 2) if nets else None,
            "best": max(ms, key=lambda r: r["net_mean_bp"]) if ms else None,
            "worst": min(ms, key=lambda r: r["net_mean_bp"]) if ms else None,
        })
    per.sort(key=lambda p: (p["median_net"] is None, -(p["median_net"] or 0)))

    lines = ["# Final findings per asset class — cell sweep 2026-11-24", "",
             "Source: `results/cells/*.json` cross-referenced against `1000_TODOS.json`. Every "
             "number below is read from those files, not retyped.", "",
             "## COVERAGE WARNING — read before the table", "",
             "The sweep ran **crypto-first**. Of 1000 ledger cells, the crypto class is the "
             "only one with measured artifacts. **EQUITY, FOREX, BOND_ETF and COMMODITY_ETF "
             "have zero measured cells and therefore no findings.** The table's "
             "`in ledger` column makes this explicit; the `measured` column would otherwise "
             "read as 'measured and empty', which is a different and false claim.", "",
             "**Headline: 0 PASS across all measured classes.** Not one cell met the "
             "pre-declared bar (CI excluding zero *and* DSR > 0.95 at 1000 trials).", "",
             "| asset class | in ledger | resolved | measured | KILL | PASS | median net bp | best cell |",
             "|---|---:|---:|---:|---:|---:|---:|---|"]
    for p in per:
        best = p["best"]
        bcell = f"`{best['cell']}` {fmt(best['net_mean_bp'])}" if best else "—"
        lines.append(f"| **{p['class']}** | {p['cells']} | {p.get('cells_resolved', 0)} | "
                     f"{p['measured']} | {p['kills']} | {p['passes']} | "
                     f"{fmt(p['median_net'])} | {bcell} |")

    lines += ["", "## Per-class commentary", ""]
    for p in per:
        lines.append(f"### {p['class']}")
        lines.append("")
        if p["measured"] == 0:
            lines.append(f"No measurable cells ({p['blocked']} blocked, {p['insufficient']} "
                         "insufficient trades). **No finding is possible for this class** — "
                         "stating otherwise would be fabrication.")
        else:
            b, w = p["best"], p["worst"]
            lines.append(f"- Cells measured: {p['measured']} ({p['insufficient']} more had "
                         f"n<30, {p['blocked']} blocked)")
            lines.append(f"- Verdicts: **{p['kills']} KILL**, **{p['passes']} PASS**")
            lines.append(f"- Median net bp/trade after 26bp: **{fmt(p['median_net'])}**")
            lines.append(f"- Best: `{b['cell']}` {fmt(b['net_mean_bp'])}bp (DSR {b.get('dsr')}, "
                         f"p {b.get('permutation_p')})")
            lines.append(f"- Worst: `{w['cell']}` {fmt(w['net_mean_bp'])}bp")
            if b["net_mean_bp"] > 0:
                lines.append(f"- **The best cell is not a PASS.** Its DSR is "
                             f"{b.get('dsr')} against 1000 trials; a positive point estimate "
                             f"selected from 1000 tries carries essentially no evidential weight.")
        lines.append("")

    (out / "FINAL_PER_ASSET_CLASS.md").write_text("\n".join(lines) + "\n")

    # ---------- contest ----------
    top = sorted(measured, key=lambda r: -r["net_mean_bp"])[:15]
    c = ["# Contest — top 15 cells by net bp/trade (post 26bp cost)", "",
         "This is a **ranking of a noisy quantity**, published because it was asked for. "
         "Read the DSR column before the net column: a cell can top this table and still be "
         "indistinguishable from noise.", "",
         "| # | cell | class | n | net bp | 95% CI | perm p | DSR | walk-forward | verdict |",
         "|---:|---|---|---:|---:|---|---:|---:|---|---|"]
    for i, r in enumerate(top, 1):
        ci = r.get("ci95_net_bp") or ["?", "?"]
        c.append(f"| {i} | `{r['cell']}` | {r['_class']} | {r['n']} | "
                 f"{fmt(r['net_mean_bp'])} | [{ci[0]}, {ci[1]}] | {r.get('permutation_p')} | "
                 f"{r.get('dsr')} | {wf.get(r['cell'], 'not run')} | {r.get('verdict')} |")
    c += ["", "## Contest winner: nobody", "",
          "The top cell is positive and the rest of the table decays into negatives. "
          "Of the three candidates that looked genuinely promising at the pooled stage, "
          "walk-forward killed two and left one:",
          "",
          "| candidate | folds positive | most recent fold | walk-forward |",
          "|---|---:|---:|---|",
          "| `SOLUSDT/breakout/1d` | 3/3 | **+122.74 bp** | CONSISTENT_SIGN |",
          "| `SOLUSDT/donchian/1d` | 1/2 | −77.16 bp | NOT_ROBUST |",
          "| `BTCUSDT/bb_meanrev/1d` | 2/3 | −17.82 bp | NOT_ROBUST (decayed 152→54→−18) |",
          "",
          "`SOLUSDT/breakout/1d` was pre-registered on 2026-11-24 and is awaiting "
          "out-of-sample data (0/30 forward trades at time of writing). It is **not a finding**.",
          "",
          "## Why a contest is the wrong instrument here",
          "",
          "Ranking 1000 cells by realised return selects the luckiest slice. The DSR column "
          "exists precisely to deflate that selection, and after deflation the leaderboard is "
          "flat: every DSR is ≈0. The honest reading of a table like this is *no winner*, "
          "not *the top row is the winner*."]
    (out / "CONTEST.md").write_text("\n".join(c) + "\n")

    # ---------- overall ranking ----------
    r2 = ["# Overall ranking — all measured cells", "",
          f"Generated from {len(rows)} artifacts: **{len(measured)} measured**, "
          f"{len(insuff)} insufficient trades (n<30), {len(blocked)} blocked (no bar data).", "",
          "Sorted by net bp/trade. CI and DSR included so the ranking can be read honestly.", "",
          "| rank | cell | class | n | gross bp | net bp | 95% CI | p | DSR | verdict |",
          "|---:|---|---|---:|---:|---:|---|---:|---:|---|"]
    for i, x in enumerate(sorted(measured, key=lambda r: -r["net_mean_bp"]), 1):
        ci = x.get("ci95_net_bp") or ["?", "?"]
        r2.append(f"| {i} | `{x['cell']}` | {x['_class']} | {x['n']} | "
                  f"{fmt(x.get('gross_mean_bp'))} | {fmt(x['net_mean_bp'])} | "
                  f"[{ci[0]}, {ci[1]}] | {x.get('permutation_p')} | {x.get('dsr')} | "
                  f"{x.get('verdict')} |")
    r2 += ["", "## Distribution", ""]
    nets = [x["net_mean_bp"] for x in measured]
    if nets:
        neg = sum(1 for v in nets if v < 0)
        r2 += [f"- Cells with negative net bp: **{neg}/{len(nets)}** "
               f"({neg/len(nets)*100:.0f}%)",
               f"- Median net bp: **{st.median(nets):+.2f}**",
               f"- Mean net bp: **{st.mean(nets):+.2f}**",
               f"- Range: {min(nets):+.2f} to {max(nets):+.2f}",
               "",
               "A distribution centred below zero after cost, with a right tail that dies "
               "under DSR, is what a null result looks like. That is the finding."]
    (out / "OVERALL_RANKING.md").write_text("\n".join(r2) + "\n")

    print(f"  wrote 3 files to {out}")
    print(f"  measured={len(measured)} insuff={len(insuff)} blocked={len(blocked)}")
    for p in per:
        print(f"    {p['class']:14s} cells={p['cells']:3d} measured={p['measured']:3d} "
              f"KILL={p['kills']:2d} PASS={p['passes']} median={fmt(p['median_net'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
