#!/usr/bin/env python3
"""
Offline validation: hedge-fund conviction tiers vs closed-book outcomes by asset class.

Enhancements (Mercury 2 / quant hygiene):
  - Optional two-proportion z-test vs asset-class baseline (HF slice vs rest)
  - Bootstrap CI for tier win rates (boolean outcomes)
  - Strategy-level rollups (min sample filter)
  - Profit factor / Sortino on pnl_pct per slice
  - Optional JSON report (--json-out)
  - Optional Pydantic row sampling (--check-contracts; requires pydantic)

Run from repo root:
  python tools/validate_hf_by_asset_class.py
  python tools/validate_hf_by_asset_class.py --json-out audit_trail/data/hf_asset_class_report.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[1]
_TOOLS = Path(__file__).resolve().parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from alpha_engine.conviction_stack import classify_hf_conviction_tier, load_conviction_tiers_config

from hf_validation_stats import (
    bootstrap_wr_ci,
    summarize_pnl_metrics,
    two_proportion_z_score,
    two_sided_normal_pvalue,
)


def norm_ac(p: dict) -> str:
    ac = (p.get("asset_class") or p.get("category") or "").upper()
    if ac in ("", "MISSING"):
        sym = str(p.get("symbol") or "")
        if sym.endswith("USDT") or sym.endswith("USDC"):
            return "CRYPTO"
        return "UNKNOWN"
    if ac in ("STOCKS", "PENNY_STOCK", "EQUITIES", "STOCK"):
        return "EQUITY"
    if ac == "COMMODITIES":
        return "COMMODITY"
    return ac


def is_won(p: dict) -> bool:
    st = str(p.get("status", "")).upper()
    if st == "WON":
        return True
    if st in ("LOST", "EXPIRED"):
        return False
    er = str(p.get("exit_reason", "")).upper()
    if "TP" in er:
        return True
    if "SL" in er:
        return False
    pnl = p.get("pnl_pct")
    try:
        return float(pnl) > 0 if pnl is not None else False
    except (TypeError, ValueError):
        return False


def pnl_float(p: dict) -> float | None:
    v = p.get("pnl_pct")
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def pct(w: int, n: int) -> float:
    return round(100.0 * w / n, 1) if n else 0.0


# Minimum closed rows per asset class for meaningful tier inference (documentation / warnings only)
SAMPLE_MIN_BY_ASSET_CLASS: dict[str, int] = {
    "EQUITY": 30,
    "FOREX": 20,
    "CRYPTO": 20,
    "ETF": 15,
    "FUTURES": 10,
    "COMMODITY": 10,
}
MIN_PER_TIER_CELL = 5


def sample_adequacy_warnings(
    by_ac: dict[str, dict[str, int]],
    by_ac_tier: dict[tuple[str, str], dict[str, int]],
) -> list[str]:
    """Non-fatal warnings when slices are too small for bootstrap / inference."""
    out: list[str] = []
    for ac, need in SAMPLE_MIN_BY_ASSET_CLASS.items():
        n = by_ac.get(ac, {}).get("n", 0)
        if n < need:
            out.append("%s: only %s closed rows (suggest %s+ for stable tier stats)" % (ac, n, need))
    for (ac, tier), d in by_ac_tier.items():
        n = d.get("n", 0)
        if 0 < n < MIN_PER_TIER_CELL:
            out.append("%s tier %s: n=%s (<%s — bootstrap CI unreliable)" % (ac, tier, n, MIN_PER_TIER_CELL))
    return out


def strat_key(p: dict) -> str:
    s = str(p.get("strategy") or p.get("algorithm") or "").strip()
    return s[:64] if s else "(none)"


def run_validation(
    data: list,
    cfg: dict[str, Any],
    *,
    min_cell_n: int = 8,
    min_strategy_n: int = 5,
    bootstrap_n: int = 2000,
    check_contracts: bool = False,
) -> dict[str, Any]:
    by_ac_tier: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: {"w": 0, "n": 0})
    by_ac: dict[str, dict[str, int]] = defaultdict(lambda: {"w": 0, "n": 0})
    by_tier: dict[str, dict[str, int]] = defaultdict(lambda: {"w": 0, "n": 0})
    hf_any: dict[str, dict[str, int]] = defaultdict(lambda: {"w": 0, "n": 0})
    # For z-test: per asset class, HF wins/total vs non-HF wins/total
    hf_detail: dict[str, dict[str, int]] = defaultdict(lambda: {"w": 0, "n": 0, "bw": 0, "bn": 0})
    tier_outcomes: dict[str, list[bool]] = defaultdict(list)
    tier_pnl: dict[str, list[float]] = defaultdict(list)
    strat_ac_tier: dict[tuple[str, str, str], dict[str, int]] = defaultdict(lambda: {"w": 0, "n": 0})
    contract_ok = 0
    contract_fail = 0

    if check_contracts:
        from hf_pick_contracts import validate_pick_dict

    for p in data:
        if not isinstance(p, dict):
            continue
        if check_contracts:
            ok, _ = validate_pick_dict(p)
            if ok:
                contract_ok += 1
            else:
                contract_fail += 1

        ac = norm_ac(p)
        tier, _ = classify_hf_conviction_tier(p, cfg)
        won = is_won(p)
        pnl = pnl_float(p)

        by_ac[ac]["n"] += 1
        if won:
            by_ac[ac]["w"] += 1

        sk = strat_key(p)
        if tier:
            by_ac_tier[(ac, tier)]["n"] += 1
            if won:
                by_ac_tier[(ac, tier)]["w"] += 1
            by_tier[tier]["n"] += 1
            if won:
                by_tier[tier]["w"] += 1
            hf_any[ac]["n"] += 1
            if won:
                hf_any[ac]["w"] += 1
            tier_outcomes[tier].append(won)
            if pnl is not None:
                tier_pnl[tier].append(pnl)
            strat_ac_tier[(ac, tier, sk)]["n"] += 1
            if won:
                strat_ac_tier[(ac, tier, sk)]["w"] += 1
            hf_detail[ac]["w"] += 1 if won else 0
            hf_detail[ac]["n"] += 1
        else:
            hf_detail[ac]["bw"] += 1 if won else 0
            hf_detail[ac]["bn"] += 1

    report: dict[str, Any] = {
        "tiers": {},
        "baseline_by_asset_class": {},
        "hf_vs_baseline_z": {},
        "tier_bootstrap_wr_ci": {},
        "tier_pnl_metrics": {},
        "cells_min_n": {},
        "strategy_slices": [],
        "notes": [],
    }

    if check_contracts:
        report["contract_sample"] = {"ok": contract_ok, "fail": contract_fail}

    for t in ("S", "A", "B"):
        d = by_tier[t]
        report["tiers"][t] = {"w": d["w"], "n": d["n"], "wr_pct": pct(d["w"], d["n"])}
        if tier_outcomes[t]:
            lo, hi = bootstrap_wr_ci(tier_outcomes[t], n_bootstrap=bootstrap_n)
            report["tier_bootstrap_wr_ci"][t] = {
                "low": round(lo, 4) if lo is not None else None,
                "high": round(hi, 4) if hi is not None else None,
            }
        if tier_pnl[t]:
            report["tier_pnl_metrics"][t] = summarize_pnl_metrics(tier_pnl[t])

    for ac in sorted(by_ac.keys(), key=lambda x: -by_ac[x]["n"]):
        d = by_ac[ac]
        report["baseline_by_asset_class"][ac] = {"w": d["w"], "n": d["n"], "wr_pct": pct(d["w"], d["n"])}

    for ac in sorted(hf_detail.keys(), key=lambda x: -by_ac.get(x, {}).get("n", 0)):
        hd = hf_detail[ac]
        n_h = hd["n"]
        n_b = hd["bn"]
        if n_h < 2 or n_b < 2:
            report["hf_vs_baseline_z"][ac] = {"skipped": "insufficient_n", "n_hf": n_h, "n_non_hf": n_b}
            continue
        w_h, w_b = hd["w"], hd["bw"]
        z = two_proportion_z_score(w_h, n_h, w_b, n_b)
        pval = two_sided_normal_pvalue(z) if z is not None else None
        report["hf_vs_baseline_z"][ac] = {
            "z": round(z, 4) if z is not None else None,
            "p_value_two_sided": round(pval, 6) if pval is not None else None,
            "hf_wr": round(w_h / n_h, 4),
            "non_hf_wr": round(w_b / n_b, 4),
            "n_hf": n_h,
            "n_non_hf": n_b,
        }

    for (ac, t), d in sorted(by_ac_tier.items()):
        if d["n"] < min_cell_n:
            continue
        report["cells_min_n"]["%s|%s" % (ac, t)] = {
            "w": d["w"],
            "n": d["n"],
            "wr_pct": pct(d["w"], d["n"]),
        }

    for (ac, t, sk), d in sorted(strat_ac_tier.items()):
        if d["n"] < min_strategy_n:
            continue
        report["strategy_slices"].append(
            {
                "asset_class": ac,
                "tier": t,
                "strategy": sk,
                "w": d["w"],
                "n": d["n"],
                "wr_pct": pct(d["w"], d["n"]),
            }
        )
    report["strategy_slices"].sort(key=lambda x: -x["n"])

    report["notes"].append(
        "Non-crypto tiers need larger N for significance; z-test compares HF-labelled vs non-HF within each asset class."
    )
    report["notes"].append(
        "Bootstrap CI uses boolean wins only; pnl-based PF/Sortino are descriptive on closed pnl_pct."
    )
    report["sample_adequacy_warnings"] = sample_adequacy_warnings(by_ac, by_ac_tier)

    return report


def print_report(report: dict[str, Any]) -> None:
    print("=== HF tier win rate (closed picks, classify_hf_conviction_tier) ===")
    for t in ("S", "A", "B"):
        tr = report["tiers"].get(t, {})
        print("  Tier %s: %s/%s = %s%%" % (t, tr.get("w"), tr.get("n"), tr.get("wr_pct")))

    print()
    print("=== Bootstrap 95%% CI for tier WR (win/loss boolean) ===")
    for t in ("S", "A", "B"):
        ci = report.get("tier_bootstrap_wr_ci", {}).get(t)
        if not ci:
            print("  Tier %s: (no outcomes)" % t)
            continue
        print(
            "  Tier %s: [%s, %s]"
            % (t, ci.get("low"), ci.get("high"))
        )

    print()
    print("=== Baseline WR by asset class (all closed) ===")
    for ac, d in sorted(
        report["baseline_by_asset_class"].items(), key=lambda x: -x[1].get("n", 0)
    ):
        print("  %s: %s/%s = %s%%" % (ac, d["w"], d["n"], d["wr_pct"]))

    print()
    print("=== HF vs non-HF within asset class (two-proportion z) ===")
    for ac, zd in report.get("hf_vs_baseline_z", {}).items():
        if "skipped" in zd:
            print("  %s: skipped (%s)" % (ac, zd.get("skipped")))
            continue
        print(
            "  %s: z=%s p=%s | HF_wr=%s n=%s vs nonHF_wr=%s n=%s"
            % (
                ac,
                zd.get("z"),
                zd.get("p_value_two_sided"),
                zd.get("hf_wr"),
                zd.get("n_hf"),
                zd.get("non_hf_wr"),
                zd.get("n_non_hf"),
            )
        )

    print()
    print("=== Tier PnL metrics (profit factor, Sortino-like) ===")
    for t in ("S", "A", "B"):
        m = report.get("tier_pnl_metrics", {}).get(t)
        if not m:
            print("  Tier %s: (no pnl)" % t)
            continue
        print("  Tier %s: %s" % (t, m))

    print()
    print("=== (asset_class, tier) cells with n >= min_cell ===")
    for k, d in report.get("cells_min_n", {}).items():
        print("  %s: %s/%s = %s%%" % (k, d["w"], d["n"], d["wr_pct"]))

    print()
    print("=== Strategy x tier slices (min n) — top 15 by n ===")
    for row in report.get("strategy_slices", [])[:15]:
        print(
            "  %s %s %s: %s/%s = %s%%"
            % (
                row["asset_class"],
                row["tier"],
                row["strategy"][:48],
                row["w"],
                row["n"],
                row["wr_pct"],
            )
        )

    if "contract_sample" in report:
        c = report["contract_sample"]
        print()
        print("=== Pydantic contract sample ===")
        print("  ok=%s fail=%s" % (c.get("ok"), c.get("fail")))

    warns = report.get("sample_adequacy_warnings") or []
    if warns:
        print()
        print("=== Sample adequacy (non-crypto / small cells) ===")
        for w in warns:
            print("  %s" % w)


def main() -> int:
    ap = argparse.ArgumentParser(description="HF tier validation by asset class (closed book)")
    ap.add_argument(
        "--closed-path",
        type=Path,
        default=_REPO / "alpha_engine" / "data" / "closed_picks.json",
        help="Path to closed picks JSON array",
    )
    ap.add_argument("--json-out", type=Path, default=None, help="Write machine-readable report JSON")
    ap.add_argument("--min-cell-n", type=int, default=8, help="Min n for asset|tier cells")
    ap.add_argument("--min-strategy-n", type=int, default=5, help="Min n for strategy slices")
    ap.add_argument("--bootstrap", type=int, default=2000, help="Bootstrap resamples for tier WR CI")
    ap.add_argument(
        "--check-contracts",
        action="store_true",
        help="Run Pydantic validation on each row (requires pydantic)",
    )
    args = ap.parse_args()

    path = args.closed_path
    if not path.is_file():
        print("Missing file: %s" % path, file=sys.stderr)
        return 1

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        print("Expected JSON array", file=sys.stderr)
        return 1

    cfg = load_conviction_tiers_config()
    report = run_validation(
        data,
        cfg,
        min_cell_n=args.min_cell_n,
        min_strategy_n=args.min_strategy_n,
        bootstrap_n=args.bootstrap,
        check_contracts=args.check_contracts,
    )
    report["source_file"] = str(path)
    report["config_version"] = cfg.get("version")

    print_report(report)

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print()
        print("Wrote %s" % args.json_out)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
