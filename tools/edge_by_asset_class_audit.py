#!/usr/bin/env python3
"""edge_by_asset_class_audit.py — what can /audit actually *prove* per asset class?

A win rate on its own proves nothing: 45% is edge with a 1:2 payoff and ruin with
a 2:1 payoff. For each asset class this reads the dashboard's own closed picks and
asks whether the observed win rate clears the **breakeven** win rate implied by the
class's own average win and average loss, with a Wilson 95% lower bound (so small
samples cannot look proven) and a one-sided binomial p-value against breakeven.

Verdicts:
  PROVEN            n >= 100, Wilson lower bound > breakeven, profit factor > 1.2
  PROMISING         n >= 30, win rate > breakeven, but the CI still crosses it
  NO EDGE           n >= 30 and the CI does not clear breakeven (pf may still be > 1)
  INSUFFICIENT      n < 30 — nothing can be concluded either way

Usage:  python3 tools/edge_by_asset_class_audit.py [--json PATH] [--md PATH]
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict

DASH = "audit_dashboard/data/dashboard_data.json"
MIN_N = 30
PROVEN_N = 100
FDR_Q = 0.10   # Benjamini-Hochberg false-discovery rate across every strategy test
# Strategy-cell values that are really "system did not record a strategy".
SYSTEM_BUCKETS = {"alpha_engine", "multi_asset_copytrader", "battleground", "paper_trading",
                  "?", "unknown", "none", ""}


def wilson(wins: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if not n:
        return 0.0, 0.0
    p = wins / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, centre - half), min(1.0, centre + half)


def binom_p(wins: int, n: int, p0: float) -> float:
    """One-sided P(X >= wins | n, p0), normal approximation with continuity."""
    if not n or not 0 < p0 < 1:
        return 1.0
    mean = n * p0
    sd = math.sqrt(n * p0 * (1 - p0))
    if sd == 0:
        return 0.0 if wins > mean else 1.0
    z = (wins - 0.5 - mean) / sd
    return 0.5 * math.erfc(z / math.sqrt(2))


def num(v) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def stats(rows: list[dict]) -> dict:
    pnls = [num(r.get("pnl_pct")) for r in rows]
    pnls = [p for p in pnls if p is not None]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    n = len(pnls)
    avg_w = sum(wins) / len(wins) if wins else 0.0
    avg_l = abs(sum(losses) / len(losses)) if losses else 0.0
    be = avg_l / (avg_w + avg_l) if (avg_w + avg_l) > 0 else 0.5
    gross_w, gross_l = sum(wins), abs(sum(losses))
    lo, hi = wilson(len(wins), n)
    return {
        "n": n, "wins": len(wins), "losses": len(losses),
        "win_rate": len(wins) / n if n else 0.0,
        "wilson_low": lo, "wilson_high": hi,
        "breakeven_wr": be,
        "avg_win": avg_w, "avg_loss": avg_l,
        "profit_factor": (gross_w / gross_l) if gross_l else None,
        "expectancy_pct": (sum(pnls) / n) if n else 0.0,
        "p_value": binom_p(len(wins), n, be),
    }


def verdict(s: dict) -> str:
    if s["n"] < MIN_N:
        return "INSUFFICIENT"
    if s["n"] >= PROVEN_N and s["wilson_low"] > s["breakeven_wr"] and (s["profit_factor"] or 0) > 1.2:
        return "PROVEN"
    if s["win_rate"] > s["breakeven_wr"] and s["p_value"] < 0.05:
        return "PROMISING" if s["n"] >= MIN_N else "INSUFFICIENT"
    return "NO EDGE"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dashboard", default=DASH)
    ap.add_argument("--json", default="reports/edge_by_asset_class_2026-11-18.json")
    ap.add_argument("--md", default="reports/edge_by_asset_class_2026-11-18.md")
    args = ap.parse_args()

    d = json.load(open(args.dashboard, encoding="utf-8"))
    closed = d["picks"].get("recent_closed") or []
    by_class: dict[str, list[dict]] = defaultdict(list)
    for r in closed:
        by_class[(r.get("asset_class") or "UNKNOWN").upper()].append(r)

    out = {"generated_for": args.dashboard, "closed_picks": len(closed),
           "min_n": MIN_N, "proven_n": PROVEN_N, "classes": {}}
    print(f"closed picks analysed: {len(closed)}\n")
    print(f"{'class':11} {'n':>5} {'WR':>6} {'CI low':>6} {'breakeven':>9} {'PF':>6} {'exp%':>6} {'p':>8}  verdict")
    print("-" * 78)
    for cls, rows in sorted(by_class.items(), key=lambda kv: -len(kv[1])):
        s = stats(rows)
        v = verdict(s)
        out["classes"][cls] = {**s, "verdict": v}
        # strategies inside the class, same test, only where a sample exists
        strat: dict[str, list[dict]] = defaultdict(list)
        for r in rows:
            strat[r.get("strategy") or "?"].append(r)
        # A bucket named after the system, not a strategy, is an unattributed pile:
        # `alpha_engine` (n=33, 13 symbols, every exit a TP/SL) is the fallback name
        # when no strategy was recorded. It cannot be "proven" or "rejected", and
        # letting it into the FDR family inflates the tests without a hypothesis.
        ok = [(k, stats(v2)) for k, v2 in strat.items()
              if len(v2) >= MIN_N and k.lower() not in SYSTEM_BUCKETS]
        ok.sort(key=lambda kv: (-kv[1]["wilson_low"] > kv[1]["breakeven_wr"], -kv[1]["n"]))
        out["classes"][cls]["strategies"] = {
            k: {**sv, "verdict": verdict(sv)} for k, sv in ok}
        pf = f"{s['profit_factor']:.2f}" if s["profit_factor"] else "  — "
        print(f"{cls:11} {s['n']:5} {s['win_rate']*100:5.1f}% {s['wilson_low']*100:5.1f}% "
              f"{s['breakeven_wr']*100:8.1f}% {pf:>6} {s['expectancy_pct']:6.2f} "
              f"{s['p_value']:8.4f}  {v}")

    # Multiple testing: ~30 strategies get tested against their own breakeven at
    # once, so one p<0.05 is cheap. Benjamini-Hochberg at q=0.10 across every
    # (class, strategy) test with a sample; only survivors may be called proven.
    tests = [(cls, name, sv) for cls, cs in out["classes"].items()
             for name, sv in cs["strategies"].items()]
    tests.sort(key=lambda t: t[2]["p_value"])
    m = len(tests)
    cut = 0
    for i, (_, _, sv) in enumerate(tests, 1):
        if sv["p_value"] <= i / m * FDR_Q:
            cut = i
    survivors = {(cls, name) for cls, name, _ in tests[:cut]}
    for cls, name, sv in tests:
        sv["fdr_pass"] = (cls, name) in survivors
        if sv["fdr_pass"] and sv["wilson_low"] > sv["breakeven_wr"]:
            sv["verdict"] = "PROVEN"
    out["fdr"] = {"q": FDR_Q, "tests": m,
                  "survivors": sorted(f"{c}:{n}" for c, n in survivors)}

    json_out = json.dumps(out, indent=1)
    open(args.json, "w", encoding="utf-8").write(json_out)

    lines = ["# Edge by asset class — what the ledger can prove", "",
             f"Source: `{args.dashboard}` · {len(closed)} closed picks · "
             f"verdict thresholds n>={MIN_N}, proven n>={PROVEN_N}.", "",
             "Win rate is compared with the **breakeven** win rate implied by the class's own",
             "average win and average loss, not with 50%: a 45% win rate is edge on a 1:2",
             "payoff and ruin on 2:1.", "",
             "| class | n | win rate | Wilson 95% low | breakeven | PF | expectancy % | p vs breakeven | verdict |",
             "|---|---|---|---|---|---|---|---|---|"]
    for cls, s in out["classes"].items():
        pf = f"{s['profit_factor']:.2f}" if s["profit_factor"] else "—"
        lines.append(f"| {cls} | {s['n']} | {s['win_rate']*100:.1f}% | "
                     f"{s['wilson_low']*100:.1f}% | {s['breakeven_wr']*100:.1f}% | {pf} | "
                     f"{s['expectancy_pct']:.2f} | {s['p_value']:.4f} | **{s['verdict']}** |")
    lines += ["", "## Strategies carrying each class (n >= 30)", ""]
    for cls, s in out["classes"].items():
        if not s["strategies"]:
            lines.append(f"* **{cls}** — no strategy has 30 closed picks yet.")
            continue
        lines.append(f"* **{cls}** — {s['verdict']}")
        for name, sv in list(s["strategies"].items())[:6]:
            pf = f"{sv['profit_factor']:.2f}" if sv["profit_factor"] else "—"
            lines.append(f"  * `{name}` — n={sv['n']}, WR {sv['win_rate']*100:.1f}% "
                         f"(CI low {sv['wilson_low']*100:.1f}%, breakeven {sv['breakeven_wr']*100:.1f}%), "
                         f"PF {pf}, p={sv['p_value']:.4f}, "
                         f"FDR {'pass' if sv.get('fdr_pass') else 'no'} → {sv['verdict']}")
    fdr = out["fdr"]
    lines += ["", f"## Multiple testing (Benjamini-Hochberg, q={fdr['q']})", "",
              f"{fdr['tests']} strategy tests with n>={MIN_N}; {len(fdr['survivors'])} survive "
              f"at q={fdr['q']}. A strategy is only called PROVEN when it survives this "
              f"and its Wilson lower bound clears its own breakeven win rate.", ""]
    for name in fdr["survivors"]:
        cls, strat = name.split(":", 1)
        sv = out["classes"][cls]["strategies"][strat]
        lines.append(f"* **{cls}** `{strat}` — n={sv['n']}, WR {sv['win_rate']*100:.1f}%, "
                     f"PF {(sv['profit_factor'] or 0):.2f}, p={sv['p_value']:.5f}")
    if not fdr["survivors"]:
        lines.append("* none — no strategy's edge survives correction for the number of tests")
    open(args.md, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"\njson: {args.json}\nmd:   {args.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
