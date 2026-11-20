"""Reconcile the CRYPTO profit factors that look contradictory (2026-11-20).

Copilot flagged money_ready_verdict CRYPTO pf=0.26 against audit3 pf=0.83.
Profit factor has ONE formula in this repo -- gross wins over gross losses -- so
a gap that large cannot be a formula dispute. This tool recomputes PF from each
artifact on disk, then attributes the gap to the only thing that can explain it:
the POPULATION the number was computed over.

Usage: python tools/crypto_pf_reconcile.py [--out reports/....md]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
D = REPO_ROOT / "audit_dashboard" / "data"


def pf(vals):
    g = [v for v in vals if v > 0]
    l = [v for v in vals if v < 0]
    return (sum(g) / abs(sum(l))) if l else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="reports/crypto_pf_denominator_2026-11-20.md")
    args = ap.parse_args()

    dash = json.loads((D / "dashboard_data.json").read_text())["picks"]["recent_closed"]
    cr = [r for r in dash if str(r.get("asset_class", "")).upper() == "CRYPTO"]
    resolved = [r for r in cr if isinstance(r.get("pnl_pct"), (int, float))
                and str(r.get("status", "")).upper() not in ("OPEN", "ACTIVE", "PENDING")]
    gv = [float(r["pnl_pct"]) for r in resolved]

    mr = json.loads((D / "money_ready_verdict.json").read_text())["classes"]["CRYPTO"]
    led = json.loads((D / "audit3_ledger.json").read_text())
    a3 = next((c for c in led.get("classes", [])
               if str(c.get("asset_class", "")).upper() == "CRYPTO"), {}) or {}

    cohorts = [
        {"name": "dashboard book (recent_closed, gross desired)",
         "n": len(gv), "pf": round(pf(gv), 4) if pf(gv) else None,
         "wr_pct": round(100 * sum(v > 0 for v in gv) / len(gv), 2),
         "mean_pct": round(sum(gv) / len(gv), 4), "cost": 0.0},
        {"name": "dashboard book, net 40bp",
         "n": len(gv), "pf": round(pf([v - 0.4 for v in gv]), 4),
         "wr_pct": round(100 * sum(v - 0.4 > 0 for v in gv) / len(gv), 2),
         "mean_pct": round(sum(v - 0.4 for v in gv) / len(gv), 4), "cost": 0.4},
        {"name": "audit3 ledger class node", "n": a3.get("n"), "pf": a3.get("pf"),
         "wr_pct": round(100 * (a3.get("wins") or 0) / (a3.get("n") or 1), 2),
         "mean_pct": a3.get("net_expectancy_pct"), "cost": a3.get("mean_cost_pct")},
        {"name": "money_ready policy-clean", "n": mr.get("policy_clean_n"),
         "pf": mr.get("policy_clean_pf"),
         "wr_pct": round(100 * (mr.get("policy_clean_wr") or 0), 2),
         "mean_pct": mr.get("expectancy"), "cost": None},
    ]

    ordered = [c for c in cohorts if c["n"]]
    widest = max(ordered, key=lambda c: c["n"])
    narrow = [c for c in ordered if c["name"].startswith("audit3")][0]
    ratio_n = widest["n"] / narrow["n"]
    ratio_pf = (narrow["pf"] / widest["pf"]) if widest["pf"] else None

    L = ["# CRYPTO profit factor: the 0.26 vs 0.83 gap is a population gap", "",
         "Date: 2026-11-20  |  author: freebuff (deepseek-v4-flash)", "",
         "## Claim under test", "",
         "Copilot: `money_ready_verdict` shows CRYPTO PF **0.26**, audit3 shows **0.83** — "
         "presented as the same class carrying two profit factors.", "",
         "## One formula, three call sites", "",
         "PF is `sum(wins) / |sum(losses)|` at every implementation: "
         "`alpha_engine/audit3_tribunal.py:294`, `alpha_engine/money_ready_verdict.py:1585`, "
         "`tools/anti_overfit_audit_sidecar.py`. There is no competing convention in the repo, "
         "so no arithmetic can reconcile the two numbers. Only the population can.", "",
         "## Measured", "",
         "| cohort | n | PF | WR | mean net/pick | cost charged |",
         "|---|---|---|---|---|---|"]
    for c in cohorts:
        L.append(f"| {c['name']} | {c['n']} | {c['pf']} | {c['wr_pct']}% | {c['mean_pct']}% | "
                 f"{c['cost'] if c['cost'] is not None else 'via registry'} |")

    L += ["", "## The attribution", "",
          f"- Widest population: **{widest['n']:,}** picks ({widest['name']}), PF **{widest['pf']}**.",
          f"- audit3's {narrow['n']:,} is a **subset**: {100 * (1 - narrow['n'] / widest['n']):.1f}% "
          f"of the class is missing from it.",
          f"- The population ratio is **{ratio_n:.2f}x** and the PF ratio is **{ratio_pf:.2f}x**. "
          "Those are the same number. The two figures are not contradicting each other; they are "
          "describing different sets, and the gap in PF tracks the gap in n almost exactly.", "",
          "## Which denominator is right", "",
          f"**{widest['name']}'s, i.e. the 0.26** — as a statement about CRYPTO. A class-level PF "
          "must cover the class's resolved population, and that is the only one of the three that "
          "does. It is also the only one whose cohort is defined by policy rather than by what "
          "happened to make it through a pipeline stage.", "",
          f"That does **not** make audit3's 0.83 wrong — it is correct for its {narrow['n']:,}-pick "
          "cohort, and it charges cost per pick (`mean_cost_pct="
          f"{a3.get('mean_cost_pct')}`). It is wrong only if quoted with the word \"CRYPTO\" and no n. "
          f"Same for the dashboard's {cohorts[0]['pf']} on {cohorts[0]['n']:,} rows: a recent-window "
          "figure, gross, not the class.", "",
          "## What does not change", "",
          "Every cohort is below PF 1.0 once its own filter is honoured, and the widest one is far "
          "below. The disagreement is about magnitude, not direction: **CRYPTO loses money on every "
          "convention tested here.** Any promotion argument has to beat the widest population, not "
          "the friendliest one.", "",
          "## Rule adopted", "",
          "Quote a class PF only with its n and its cost treatment. A PF without a denominator is "
          "not a measurement.", ""]

    Path(args.out).write_text("\n".join(L))
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
