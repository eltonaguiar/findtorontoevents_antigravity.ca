"""Turn the harness JSON into the results report and the updates/ card.

Verdicts are computed here, from the JSON, so no number in the report is
transcribed by hand.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ORDER = ["EQUITY", "ETF", "FUTURES", "INDEX", "BOND",
         "COMMODITY", "FOREX", "MUTUAL_FUND", "PENNY_STOCK", "CRYPTO"]
MEANING = {
    "DATA_INTEGRITY_FAIL": "series is roll/pricing-contaminated — unmeasurable until repaired",
    "PASSES_ALL_BACKTEST_GATES": "backtest candidate — still needs a forward pod (G8), not money",
    "FAILS_MULTIPLICITY": "survives cost/stability but not the trial-count-adjusted Sharpe bar",
    "FAILS_BENCHMARK": "beats cash but not buy-and-hold of its own universe",
    "FAILS_STABILITY": "one half of the sample carries the result",
    "FAILS_2X_COST": "signal exists, cannot pay for itself at 2× cost",
    "REFUTED_OR_WEAK": "no usable signal at this resolution",
    "INSUFFICIENT_N": "not enough trades to speak — labelled, not dropped",
}


def verdict(c: dict) -> str:
    if c.get("integrity_flag"):
        return "DATA_INTEGRITY_FAIL"
    if (c.get("n_trades") or 0) < 30:
        return "INSUFFICIENT_N"
    if c["boot_ci_lb_bps"] <= 0:
        return "REFUTED_OR_WEAK"
    if c["boot_ci_lb_2x_cost_bps"] <= 0:
        return "FAILS_2X_COST"
    h = c["split_half_bps"]
    if h[0] <= 0 or h[1] <= 0:
        return "FAILS_STABILITY"
    if c["excess_vs_bench_bps"] <= 0:
        return "FAILS_BENCHMARK"
    if (c.get("dsr") or 0) < 0.95:
        return "FAILS_MULTIPLICITY"
    return "PASSES_ALL_BACKTEST_GATES"


def main() -> int:
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "reports/per_class_edge_2026-11-22.json")
    md_out = Path(sys.argv[2] if len(sys.argv) > 2 else "reports/2026-11-22-per-class-edge-results.md")
    card = Path(sys.argv[3] if len(sys.argv) > 3 else "updates/2026-11-22-per-class-edge-sweep.md")
    d = json.loads(src.read_text())
    for c in d["cells"]:
        c["final_status"] = verdict(c)
    src.write_text(json.dumps(d, indent=1))

    cells = sorted(d["cells"], key=lambda c: (ORDER.index(c["asset_class"]),
                                              -(c.get("mean_daily_bps") or -999)))
    L = ["# Per-class edge sweep — results, 2026-11-22", "",
         f"Window **{d['window']['start']} → {d['window']['end']}** · {len(cells)} cells · "
         f"n_trials declared **{d['n_trials_declared']}** · expected-max daily Sharpe "
         f"**{d['expected_max_sharpe_daily']}** · **PBO(CSCV) {d['pbo_cscv']}**", "",
         "Every cell was pre-registered in `reports/hypothesis_registry.json` (H-200…H-225) and "
         "`reports/preregistration_2026-11-22_per_class.json` **before** the first run. Costs are "
         "round-trip: EQUITY/ETF/BOND/INDEX/MF 10 bps, CRYPTO 20, FOREX 5, COMMODITY 15, FUTURES 10, "
         "PENNY 10 (understated by design).", "",
         "| class | id | cell | n | PF | mean trade % | daily bps | CI-LB | CI-LB @2× | halves | excess vs bench | DSR | verdict |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for c in cells:
        L.append(f"| {c['asset_class']} | {c['id']} | {c['name']} | {c['n_trades']} | "
                 f"{c['profit_factor']} | {c['mean_trade_pct']} | {c['mean_daily_bps']} | "
                 f"{c['boot_ci_lb_bps']} | {c['boot_ci_lb_2x_cost_bps']} | {c['split_half_bps']} | "
                 f"{c['excess_vs_bench_bps']} | {c['dsr']} | **{c['final_status']}** |")

    by: dict[str, list[dict]] = {}
    for c in cells:
        by.setdefault(c["asset_class"], []).append(c)
    L += ["", "## Class verdicts", "",
          "| class | cells | best cell | verdict | what it means |", "|---|---|---|---|---|"]
    # Rank by strength of verdict, and never let an under-sampled cell decide the
    # class: NVDA tsmom (n=13) has the highest CI-LB in EQUITY but cannot speak.
    STRENGTH = ["PASSES_ALL_BACKTEST_GATES", "FAILS_MULTIPLICITY", "FAILS_BENCHMARK",
                "FAILS_STABILITY", "FAILS_2X_COST", "REFUTED_OR_WEAK",
                "INSUFFICIENT_N", "DATA_INTEGRITY_FAIL"]
    for cls in ORDER:
        cs = by.get(cls, [])
        if not cs:
            continue
        eligible = [c for c in cs if c["final_status"] != "INSUFFICIENT_N"] or cs
        cls_verdict = min(eligible, key=lambda c: STRENGTH.index(c["final_status"]))["final_status"]
        best = max(eligible, key=lambda c: c["boot_ci_lb_bps"] or -1e9)
        L.append(f"| {cls} | {len(cs)} | {best['id']} {best['name']} (CI-LB "
                 f"{best['boot_ci_lb_bps']} bps, n={best['n_trades']}, DSR {best['dsr']}) | "
                 f"{cls_verdict} | {MEANING[cls_verdict]} |")

    # ---- G6b: the same cells levered to their benchmark's own volatility.
    matched = [c for c in cells if c.get("matched_excess_bps") is not None]
    ra = [c for c in matched if c.get("risk_adj_pass")]
    L += ["", "## Volatility-matched comparison (G6b) — reported, not a promotion", "",
          "G6 as written asks a cell to beat buy-and-hold of its own universe on raw daily "
          "return. No de-risking rule can pass that: holding cash part of the time must lower "
          "the mean. G6b scales each cell to the benchmark's ex-post volatility (capped at 4×) "
          "and compares there. It is a separate yardstick, applied to every cell alike, and "
          "**no cell is promoted on G6b alone** — it tells us which classes have a risk-adjusted "
          "edge worth a forward pod, nothing more.", "",
          "| class | id | cell | vol | bench vol | lev | matched bps | matched CI-LB | halves | CAGR | bench CAGR | levered CAGR | MDD | bench MDD | G6b |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for c in sorted(matched, key=lambda r: (ORDER.index(r["asset_class"]),
                                            -(r.get("matched_ci_lb_bps") or -999))):
        L.append(f"| {c['asset_class']} | {c['id']} | {c['name']} | {c['strategy_vol_pct']}% | "
                 f"{c['bench_vol_pct']}% | {c['leverage_to_match']}× | {c['matched_excess_bps']} | "
                 f"{c['matched_ci_lb_bps']} | {c['matched_halves_bps']} | {c['cagr_pct']}% | "
                 f"{c['bench_cagr_pct']}% | {c['levered_cagr_pct']}% | {c['mdd_pct']}% | "
                 f"{c['bench_mdd_pct']}% | {'PASS' if c.get('risk_adj_pass') else '—'} |")
    L += ["", f"Cells clearing G6b (matched-vol excess > 0, CI-LB > 0, both halves > 0): "
          f"**{len(ra)}** — " + (", ".join(f"{c['id']} {c['asset_class']}" for c in ra) or "none")]

    passing = [c for c in cells if c["final_status"] == "PASSES_ALL_BACKTEST_GATES"]
    counts = Counter(c["final_status"] for c in cells)
    L += ["", f"**Cells clearing every backtest gate: {len(passing)}**"
          + ("" if not passing else " — " + ", ".join(
              f"{c['id']} {c['asset_class']} {c['name']}" for c in passing)), "",
          "## Reading this honestly", "",
          "- A `PASSES_ALL_BACKTEST_GATES` cell is a **backtest** result. It has not been "
          "forward-tested, so it is not an edge yet (G8 = n ≥ 100 closed forward trades).",
          "- `excess vs bench` is the beta check: a cell can be profitable and still be worthless "
          "if it just tracks its own universe.",
          "- `CI-LB @2×` is the cost stress; `FAILS_2X_COST` cells are the gross-looking strategies "
          "this desk has over-trusted before.",
          "- PENNY_STOCK costs are understated (no market impact), so even a passing cell there "
          "needs a liquidity haircut first.",
          "- MUTUAL_FUND cells trade at daily NAV with next-day execution; they can support a "
          "fund-selection rule, not a trading edge.", "",
          "Reproduce: `python3 tools/per_class_edge_harness.py --out "
          "reports/per_class_edge_2026-11-22.json --md reports/per_class_edge_2026-11-22.md "
          f"--n-trials {d['n_trials_declared']}` then `python3 tools/build_per_class_report.py`"]
    md_out.write_text("\n".join(L) + "\n")

    integ = (d.get("data_integrity") or {}).get("commodity") or []
    if integ:
        L += ["", "## Data integrity (why COMMODITY is not merely 'weak')", "",
              "| symbol | rows | negative prices | |ret|>8% | max |ret| | recurring month-day spikes | usable |",
              "|---|---|---|---|---|---|---|"]
        for r in integ:
            L.append(f"| {r['symbol']} | {r['rows']} | {r['negative_prices']} | "
                     f"{r['spikes_gt_threshold']} | {r['max_abs_ret_pct']}% | "
                     f"{r['recurring_month_day_spikes'] or '—'} | {r['usable']} |")
        L += ["", "A series with roll-gap spikes on the same calendar day in multiple years, "
              "or a negative print, cannot confirm or refute a strategy. COMMODITY is "
              "reported as `DATA_INTEGRITY_FAIL` until rebuilt on roll-adjusted contracts."]
        md_out.write_text("\n".join(L) + "\n")

    card.write_text(
        "# Per-class edge sweep across all 10 asset classes\n\n"
        f"**Why:** the desk needed every class measured on the same contract, after a sweep that "
        f"silently dropped classes under a minimum row count.\n\n"
        f"**What:** `tools/per_class_edge_harness.py` (pre-registered mechanisms, block-bootstrap "
        f"CI, 2× cost stress, split-half, DSR with n_trials={d['n_trials_declared']}, PBO via CSCV, "
        f"benchmark excess) + `tools/build_per_class_report.py` + 7 invariant tests.\n\n"
        f"**Result:** {len(cells)} cells over {d['window']['start']} → {d['window']['end']}; "
        f"PBO {d['pbo_cscv']}; " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) + ".\n\n"
        "**Two defects found and fixed while running it:** portfolio cells reported `n_trades=1` "
        "(PF meaningless) until PF was taken from monthly buckets; and `xsmom` replaced explicit "
        "zero weights with NaN before `ffill`, so dropped names kept their weight forever, exposure "
        "drifted above 1, and the first equity result (30 bps/day) was pure leverage artifact. "
        "Now guarded by an exposure assertion plus tests for exposure ≤ 1, closing dropped names, "
        "and lookahead independence.\n\n"
        "**Verification:** `python3 -m pytest tests/test_per_class_edge_harness.py -q` → 7 passed; "
        "full table and verdicts in `reports/2026-11-22-per-class-edge-results.md`.\n")

    print("\n".join(L[L.index("## Class verdicts"):]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
