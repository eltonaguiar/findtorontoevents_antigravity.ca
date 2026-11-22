#!/usr/bin/env python3
"""ledger_net_and_oos.py — turn the closed ledger's gross numbers into net numbers,
and split the two surviving strategies into in-sample / out-of-sample halves.

Why: `audit_dashboard/data/dashboard_data.json` carries `after_cost_net_per_trade`
on 0 of 3,500 closed picks, so every verdict computed from it (including the
2026-11-18 edge-by-asset-class audit) is GROSS. A 0.54%/trade crypto edge and a
0.08%/trade ETF edge are not the same claim once fees and slippage are subtracted.

What this does:
  1. Per asset class, re-runs the win-rate-vs-own-breakeven test on NET returns
     using a round-trip cost model, and reports the cost level at which the
     class edge would disappear (breakeven_cost_bps).
  2. For named strategies, splits the resolved picks chronologically (60/40 and
     thirds) and reports PF/expectancy per segment at a cost grid.
     This is an out-of-sample split of realised picks, NOT a re-backtest.
  3. Audits what can be checked without price bars: internal consistency of
     SL_HIT/TP_HIT against the recorded pnl sign. A true first-touch
     re-resolution needs OHLC bars between entry and exit, which the ledger does
     not carry — that gap is reported, not papered over.

Usage:
  python3 tools/ledger_net_and_oos.py --dashboard PATH [--json OUT] [--md OUT]
  python3 tools/ledger_net_and_oos.py --self-check
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict

# Round-trip cost in basis points of notional (entry + exit, fees + slippage).
# Deliberately conservative-but-realistic retail numbers; override per class in
# COST_BPS if your broker differs. Every figure is net of THIS model only.
COST_BPS = {
    "CRYPTO": 20,     # 10bp taker each side
    "EQUITY": 10,     # commission-free + 5bp slippage each side
    "ETF": 10,
    "FOREX": 8,       # ~0.8 pip on majors
    "COMMODITY": 12,
    "FUTURES": 12,
    "BOND": 10,
}
DEFAULT_COST_BPS = 15
GRID_BPS = (0, 5, 10, 15, 20, 30)


def wilson(wins: int, n: int, z: float = 1.96):
    if not n:
        return 0.0, 0.0
    p = wins / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, centre - half), min(1.0, centre + half)


def binom_p(wins: int, n: int, p0: float) -> float:
    if not n or not 0 < p0 < 1:
        return 1.0
    mean = n * p0
    sd = math.sqrt(n * p0 * (1 - p0))
    if sd == 0:
        return 0.0 if wins > mean else 1.0
    z = (wins - 0.5 - mean) / sd
    return 0.5 * math.erfc(z / math.sqrt(2))


def stats(pnls):
    n = len(pnls)
    if not n:
        return {"n": 0}
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    avg_w = sum(wins) / len(wins) if wins else 0.0
    avg_l = abs(sum(losses) / len(losses)) if losses else 0.0
    be = avg_l / (avg_w + avg_l) if (avg_w + avg_l) > 0 else 0.5
    gross_l = abs(sum(losses))
    lo, hi = wilson(len(wins), n)
    return {
        "n": n,
        "win_rate": len(wins) / n,
        "wilson_low": lo, "wilson_high": hi,
        "breakeven_wr": be,
        "avg_win": avg_w, "avg_loss": avg_l,
        "profit_factor": (sum(wins) / gross_l) if gross_l else None,
        "expectancy_pct": sum(pnls) / n,
        "p_value": binom_p(len(wins), n, be),
    }


def cost_pct(cls: str) -> float:
    return COST_BPS.get(cls.upper(), DEFAULT_COST_BPS) / 100.0


def fnum(r, key, default=None):
    v = r.get(key)
    try:
        f = float(v)
    except (TypeError, ValueError):
        return default
    return f if math.isfinite(f) else default


def load_closed(path):
    d = json.load(open(path, encoding="utf-8"))
    picks = d.get("picks") or {}
    closed = picks.get("recent_closed") or []
    return d, closed


def check_geometry(rows):
    """What CAN be checked with no price bars: SL/TP exits that disagree with the pnl sign."""
    bad = []
    for r in rows:
        reason = str(r.get("exit_reason") or r.get("exit_reason_raw") or "").upper()
        pnl = fnum(r, "pnl_pct")
        if pnl is None:
            continue
        if "SL" in reason and pnl > 0:
            bad.append({"id": r.get("id"), "kind": "SL_HIT but pnl>0", "pnl_pct": pnl,
                        "asset_class": r.get("asset_class")})
        elif "TP" in reason and pnl < 0:
            bad.append({"id": r.get("id"), "kind": "TP_HIT but pnl<0", "pnl_pct": pnl,
                        "asset_class": r.get("asset_class")})
    return bad


def strategy_slices(rows, name, cost_bps):
    sel = [r for r in rows if str(r.get("strategy", "")).lower() == name.lower()]
    sel.sort(key=lambda r: str(r.get("timestamp") or r.get("closed_at") or ""))
    pnls = [fnum(r, "pnl_pct") for r in sel]
    pnls = [p for p in pnls if p is not None]
    n = len(pnls)
    out = {"strategy": name, "n": n,
           "ts_coverage": sum(1 for r in sel if r.get("timestamp")),
           "cost_bps": cost_bps}
    if n < 10:
        out["note"] = "n<10: no split attempted"
        return out
    cut = int(n * 0.6)
    segs = {"IS_first60": pnls[:cut], "OOS_last40": pnls[cut:],
            "third1": pnls[: n // 3],
            "third2": pnls[n // 3: 2 * n // 3],
            "third3": pnls[2 * n // 3:]}
    out["segments"] = {k: stats(v) for k, v in segs.items() if v}
    out["net_at_cost"] = {
        "gross": stats(pnls),
        f"net_{cost_bps}bps": stats([p - cost_bps / 100.0 for p in pnls]),
    }
    out["cost_grid"] = {
        f"{bps}bps": {
            "expectancy_pct": stats([p - bps / 100.0 for p in pnls])["expectancy_pct"],
            "profit_factor": stats([p - bps / 100.0 for p in pnls])["profit_factor"],
            "win_rate": stats([p - bps / 100.0 for p in pnls])["win_rate"],
        } for bps in GRID_BPS
    }
    exp = stats(pnls)["expectancy_pct"]
    out["breakeven_cost_bps"] = round(exp * 100, 1)   # 1 pct = 100 bps
    # OOS half after cost: the only number that speaks to "survives out of sample"
    oos = [p - cost_bps / 100.0 for p in pnls[cut:]]
    out["oos_net_expectancy_pct"] = round(stats(oos)["expectancy_pct"], 4)
    out["oos_net_pf"] = stats(oos)["profit_factor"]
    return out


def self_check():
    ok = True
    s = stats([1.0, -1.0, 2.0, -1.0])
    checks = [
        ("pf", abs(s["profit_factor"] - 1.5) < 1e-9),
        ("wr", abs(s["win_rate"] - 0.5) < 1e-9),
        ("be", abs(s["breakeven_wr"] - 0.4) < 1e-9),
        ("exp", abs(s["expectancy_pct"] - 0.25) < 1e-9),
        ("wilson_lo<wr<wilson_hi", s["wilson_low"] < s["win_rate"] < s["wilson_high"]),
        ("cost_crypto", abs(cost_pct("CRYPTO") - 0.20) < 1e-9),
        ("cost_unknown", abs(cost_pct("XYZ") - 0.15) < 1e-9),
        ("net_shifts_pf", stats([p - 0.2 for p in [1.0, -1.0, 2.0, -1.0]])["profit_factor"] < 1.5),
    ]
    for name, good in checks:
        ok &= good
        print(f"  {'ok  ' if good else 'FAIL'} {name}")
    print("SELF-CHECK PASSED" if ok else "SELF-CHECK FAILED")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dashboard", default="audit_dashboard/data/dashboard_data.json")
    ap.add_argument("--json", default="reports/2026-11-22-ledger-net-cost-oos.json")
    ap.add_argument("--md", default="reports/2026-11-22-ledger-net-cost-oos.md")
    ap.add_argument("--strategies", default="MomentumEMA,mega_mutation_macd_rsi_m048")
    ap.add_argument("--self-check", action="store_true")
    a = ap.parse_args()
    if a.self_check:
        return self_check()

    doc, closed = load_closed(a.dashboard)
    if not closed:
        print("no picks.recent_closed in dashboard", file=sys.stderr)
        return 2
    have_cost = sum(1 for r in closed if r.get("after_cost_net_per_trade") is not None)

    by_class = defaultdict(list)
    for r in closed:
        by_class[str(r.get("asset_class") or "UNKNOWN").upper()].append(fnum(r, "pnl_pct") or 0.0)

    classes = {}
    for cls, pnls in sorted(by_class.items(), key=lambda kv: -len(kv[1])):
        c = cost_pct(cls)
        g = stats(pnls)
        n_ = stats([p - c for p in pnls])
        classes[cls] = {
            "cost_bps_round_trip": COST_BPS.get(cls, DEFAULT_COST_BPS),
            "gross": g, "net": n_,
            "breakeven_cost_bps": round(g["expectancy_pct"] * 100, 1),
            "net_expectancy_delta_pct": round(n_["expectancy_pct"] - g["expectancy_pct"], 4),
            "verdict_gross": "PROVEN" if g["n"] >= 100 and g["wilson_low"] > g["breakeven_wr"]
                             and (g["profit_factor"] or 0) > 1.2 else "NOT PROVEN",
            "verdict_net": "PROVEN" if n_["n"] >= 100 and n_["wilson_low"] > n_["breakeven_wr"]
                           and (n_["profit_factor"] or 0) > 1.2 else "NOT PROVEN",
        }

    strategies = [s.strip() for s in a.strategies.split(",") if s.strip()]
    strat_out = {}
    for name in strategies:
        cls_rows = next((r.get("asset_class") for r in closed
                         if str(r.get("strategy", "")).lower() == name.lower()), None)
        bps = COST_BPS.get(str(cls_rows or "").upper(), DEFAULT_COST_BPS)
        strat_out[name] = strategy_slices(closed, name, bps)

    bad = check_geometry(closed)

    out = {
        "dashboard": a.dashboard,
        "generated_at": doc.get("generated_at"),
        "closed_picks": len(closed),
        "records_with_after_cost_field": have_cost,
        "cost_model_bps": {**COST_BPS, "DEFAULT": DEFAULT_COST_BPS},
        "classes": classes,
        "strategies": strat_out,
        "geometry_audit": {
            "inconsistent_exit_reason_vs_pnl": len(bad),
            "examples": bad[:10],
            "first_touch": "BLOCKED: needs OHLC bars between entry_time and exit_time; "
                           "the ledger stores only entry_price/exit_price and "
                           f"entry_time on {sum(1 for r in closed if r.get('entry_time'))}/{len(closed)} records",
        },
    }
    json.dump(out, open(a.json, "w"), indent=2)

    L = [f"# Net-of-cost ledger audit and out-of-sample split — 2026-11-22", "",
         f"Source: `{a.dashboard}` · {len(closed)} closed picks · "
         f"`after_cost_net_per_trade` present on **{have_cost}/{len(closed)}**.",
         "", "Costs are a stated round-trip model (fees + slippage), not measured fills:",
         "", "| class | bps |", "|---|---|"]
    for k, v in COST_BPS.items():
        L.append(f"| {k} | {v} |")
    L += [f"| (default) | {DEFAULT_COST_BPS} |", "",
          "## Class edge, gross vs net", "",
          "| class | cost bps | n | WR net | CI low net | breakeven net | PF gross | PF net | exp gross % | exp net % | breakeven cost bps | verdict gross -> net |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for cls, c in classes.items():
        g, n_ = c["gross"], c["net"]
        L.append(f"| {cls} | {c['cost_bps_round_trip']} | {n_['n']} | {n_['win_rate']:.1%} | "
                 f"{n_['wilson_low']:.1%} | {n_['breakeven_wr']:.1%} | "
                 f"{(g['profit_factor'] or 0):.3f} | {(n_['profit_factor'] or 0):.3f} | "
                 f"{g['expectancy_pct']:+.4f} | {n_['expectancy_pct']:+.4f} | "
                 f"{c['breakeven_cost_bps']:+.1f} | {c['verdict_gross']} -> {c['verdict_net']} |")
    L += ["", "## Strategy out-of-sample split", "",
          "A chronological split of **realised picks**, not a re-backtest: the same "
          "signals are re-scored on later exits. It answers 'did the edge decay', "
          "not 'would a fresh run reproduce it'.", ""]
    for name, s in strat_out.items():
        L += [f"### {name}", "",
              f"n={s['n']} · round-trip cost {s['cost_bps']} bps · "
              f"breakeven cost **{s.get('breakeven_cost_bps')} bps**", ""]
        if "segments" not in s:
            L += [s.get("note", "no split"), ""]
            continue
        L += ["| segment | n | WR | PF | expectancy % |", "|---|---|---|---|---|"]
        for seg, st in s["segments"].items():
            L.append(f"| {seg} | {st['n']} | {st['win_rate']:.1%} | "
                     f"{(st['profit_factor'] or 0):.3f} | {st['expectancy_pct']:+.4f} |")
        L += ["", "| cost bps | expectancy % | PF | WR |", "|---|---|---|---|"]
        for bps, cg in s["cost_grid"].items():
            L.append(f"| {bps} | {cg['expectancy_pct']:+.4f} | "
                     f"{(cg['profit_factor'] or 0):.3f} | {cg['win_rate']:.1%} |")
        L += ["", f"OOS half, net at model cost: expectancy "
                  f"**{s['oos_net_expectancy_pct']:+.4f}%/trade**, PF "
                  f"**{(s['oos_net_pf'] or 0):.3f}**.", ""]
    L += ["## First-touch resolution", "",
          f"- {out['geometry_audit']['inconsistent_exit_reason_vs_pnl']} records have an exit "
          "reason that contradicts the sign of their own pnl (SL_HIT with pnl>0, or TP_HIT with pnl<0).",
          f"- {out['geometry_audit']['first_touch']}.",
          "- No OHLC is derivable from entry_price/exit_price alone, so the H-120 honest "
          "re-resolution cannot be applied to the rest of this ledger without a bar source.",
          ""]
    open(a.md, "w").write("\n".join(L) + "\n")

    print(f"closed={len(closed)} after_cost_field={have_cost}")
    print(f"{'class':11}{'n':>6}{'PFg':>7}{'PFn':>7}{'expg':>9}{'expn':>9}{'be_bps':>8}  verdict")
    for cls, c in classes.items():
        g, n_ = c["gross"], c["net"]
        print(f"{cls:11}{n_['n']:6d}{(g['profit_factor'] or 0):7.3f}{(n_['profit_factor'] or 0):7.3f}"
              f"{g['expectancy_pct']:+9.4f}{n_['expectancy_pct']:+9.4f}"
              f"{c['breakeven_cost_bps']:+8.1f}  {c['verdict_gross']} -> {c['verdict_net']}")
    for name, s in strat_out.items():
        if "segments" in s:
            print(f"\n{name}: n={s['n']} be_cost={s['breakeven_cost_bps']}bps "
                  f"OOS_net_exp={s['oos_net_expectancy_pct']:+.4f}% OOS_PF={(s['oos_net_pf'] or 0):.3f}")
            for seg, st in s["segments"].items():
                print(f"   {seg:12s} n={st['n']:4d} PF={(st['profit_factor'] or 0):6.3f} "
                      f"exp={st['expectancy_pct']:+.4f}%")
    print(f"\ngeometry inconsistencies: {len(bad)}")
    print(f"wrote {a.json} and {a.md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
