#!/usr/bin/env python3
"""Generic Monte Carlo strategy validator.

Validates any strategy/asset-class/symbol claim against the picks dataset via
bootstrap CI + permutation test + forward projection. Zero external deps.

Usage:
  python tools/mc_strategy_validator.py \
    --strategy "Breakout Momentum" \
    --asset-class EQUITY \
    --iterations 10000 \
    --out alpha_engine/data/mc_breakout_momentum_equity.json

  # Inverse-edge claim for multiple losing strategies (substring match):
  python tools/mc_strategy_validator.py \
    --strategy-contains "Momentum" \
    --asset-class EQUITY \
    --inverse \
    --out alpha_engine/data/mc_momentum_inverse.json

Exit codes:
  0  success
  1  no matching trades found
  2  dashboard file missing / malformed
  3  bad CLI args
"""
from __future__ import annotations
import argparse
import json
import math
import random
import sys
from pathlib import Path
from datetime import datetime, timezone

REPO = Path(__file__).resolve().parents[1]
DEFAULT_DASHBOARD = REPO / "audit_dashboard" / "data" / "dashboard_data.json"

FORWARD_WINDOWS = [30, 100, 300]
DEFAULT_SEED = 42
DEFAULT_ITERATIONS = 10000
DEFAULT_FEES_PCT = 0.2  # round-trip

VALID_ASSET_CLASSES = {
    "EQUITY", "CRYPTO", "FOREX", "COMMODITY",
    "BOND", "ETF", "FUTURES", "ALL",
}


def wilson_ci(wins: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score 95% CI for a binomial proportion."""
    if n == 0:
        return (0.0, 0.0)
    p = wins / n
    denom = 1.0 + (z * z) / n
    center = (p + (z * z) / (2 * n)) / denom
    half = (z * math.sqrt((p * (1 - p) / n) + (z * z) / (4 * n * n))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def filter_trades(
    closed: list[dict],
    strategy_exact: str | None,
    strategy_contains: str | None,
    strategy_set: set[str] | None,
    asset_class: str,
    symbol: str | None,
    source_system: str | None,
) -> list[dict]:
    ac = (asset_class or "ALL").upper()
    sc = (strategy_contains or "").lower() if strategy_contains else None
    out: list[dict] = []
    for p in closed:
        if p.get("status") not in ("WON", "LOST"):
            continue
        if p.get("pnl_pct") is None:
            continue
        if ac != "ALL" and (p.get("asset_class") or "").upper() != ac:
            continue
        strat = p.get("strategy") or ""
        if strategy_exact and strat != strategy_exact:
            continue
        if sc and sc not in strat.lower():
            continue
        if strategy_set and strat not in strategy_set:
            continue
        if symbol and (p.get("symbol") or "").upper() != symbol.upper():
            continue
        if source_system and (p.get("source_system") or "") != source_system:
            continue
        out.append(p)
    return out


def bootstrap_ci(values: list[float], iterations: int, rng: random.Random) -> dict:
    n = len(values)
    boot_means: list[float] = []
    boot_wrs: list[float] = []
    for _ in range(iterations):
        sample = [rng.choice(values) for _ in range(n)]
        boot_means.append(sum(sample) / n)
        boot_wrs.append(sum(1 for x in sample if x > 0) / n)
    boot_means.sort()
    boot_wrs.sort()
    lo_idx = int(0.025 * iterations)
    hi_idx = int(0.975 * iterations)
    return {
        "mean_ci_lo": boot_means[lo_idx],
        "mean_ci_hi": boot_means[hi_idx],
        "wr_ci_lo": boot_wrs[lo_idx],
        "wr_ci_hi": boot_wrs[hi_idx],
        "p_mean_positive": sum(1 for x in boot_means if x > 0) / iterations,
        "p_wr_above_55": sum(1 for x in boot_wrs if x > 0.55) / iterations,
    }


def permutation_test(values: list[float], iterations: int, observed_mean: float, rng: random.Random) -> float:
    """Direction-flip null: each trade's sign is random 50/50."""
    n = len(values)
    abs_mags = [abs(x) for x in values]
    ge_count = 0
    for _ in range(iterations):
        s = 0.0
        for m in abs_mags:
            s += m if rng.random() < 0.5 else -m
        if (s / n) >= observed_mean:
            ge_count += 1
    return ge_count / iterations


def forward_projection(values: list[float], iterations: int, rng: random.Random) -> dict:
    out: dict = {}
    for horizon in FORWARD_WINDOWS:
        terms: list[float] = []
        pos = 0
        for _ in range(iterations):
            t = sum(rng.choice(values) for _ in range(horizon))
            terms.append(t)
            if t > 0:
                pos += 1
        terms.sort()
        out[f"n_{horizon}"] = {
            "p_positive_cumulative_pnl": round(pos / iterations, 4),
            "median_terminal_pnl_pct": round(terms[iterations // 2], 2),
            "p5_terminal_pnl_pct": round(terms[int(0.05 * iterations)], 2),
            "p95_terminal_pnl_pct": round(terms[int(0.95 * iterations)], 2),
            "max_drawdown_estimated_p5": round(terms[int(0.05 * iterations)], 2),
        }
    return out


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Generic MC validator for strategy claims (bootstrap + permutation + forward projection).",
    )
    p.add_argument("--strategy", type=str, default=None, help="Exact strategy name")
    p.add_argument("--strategy-contains", type=str, default=None, help="Substring match on strategy name")
    p.add_argument("--strategy-in", type=str, default=None,
                   help="Comma-separated list of exact strategy names (any-of match)")
    p.add_argument("--asset-class", type=str, default="ALL",
                   help="EQUITY/CRYPTO/FOREX/COMMODITY/BOND/ETF/FUTURES/ALL")
    p.add_argument("--symbol", type=str, default=None, help="Exact symbol filter (e.g. NVDA)")
    p.add_argument("--source-system", type=str, default=None, help="Exact source_system filter")
    p.add_argument("--source", type=str, default="picks.recent_closed",
                   help="Dataset path in dashboard_data.json (currently only picks.recent_closed supported)")
    p.add_argument("--inverse", action="store_true",
                   help="Flip pnl_pct sign (test inverse-strategy claim), fees applied after flip")
    p.add_argument("--fees-pct", type=float, default=DEFAULT_FEES_PCT,
                   help="Round-trip fees in percent (default 0.2)")
    p.add_argument("--iterations", type=int, default=DEFAULT_ITERATIONS,
                   help="Bootstrap/permutation iterations (default 10000)")
    p.add_argument("--seed", type=int, default=DEFAULT_SEED, help="RNG seed (default 42)")
    p.add_argument("--dashboard", type=str, default=str(DEFAULT_DASHBOARD),
                   help="Path to dashboard_data.json")
    p.add_argument("--out", type=str, required=True, help="Output JSON path")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    ac = (args.asset_class or "ALL").upper()
    if ac not in VALID_ASSET_CLASSES:
        print(f"[error] invalid --asset-class {args.asset_class}; must be one of {sorted(VALID_ASSET_CLASSES)}",
              file=sys.stderr)
        return 3

    if args.source != "picks.recent_closed":
        print(f"[error] --source {args.source} not supported (only picks.recent_closed)", file=sys.stderr)
        return 3

    dash_path = Path(args.dashboard)
    if not dash_path.exists():
        print(f"[error] dashboard file not found: {dash_path}", file=sys.stderr)
        return 2

    try:
        data = json.loads(dash_path.read_text(encoding="utf-8", errors="replace"))
        closed = data["picks"]["recent_closed"]
    except (json.JSONDecodeError, KeyError) as e:
        print(f"[error] malformed dashboard data: {e}", file=sys.stderr)
        return 2

    strategy_set: set[str] | None = None
    if args.strategy_in:
        strategy_set = {s.strip() for s in args.strategy_in.split(",") if s.strip()}

    matched = filter_trades(
        closed,
        strategy_exact=args.strategy,
        strategy_contains=args.strategy_contains,
        strategy_set=strategy_set,
        asset_class=ac,
        symbol=args.symbol,
        source_system=args.source_system,
    )

    if not matched:
        print("[error] no matching closed trades found for the given filters", file=sys.stderr)
        return 1

    # Build PnL vector (inverse flips sign; fees applied after flip).
    pnl_vec: list[float] = []
    for p in matched:
        raw = float(p.get("pnl_pct") or 0.0)
        if args.inverse:
            raw = -raw
        net = raw - args.fees_pct
        pnl_vec.append(net)

    n = len(pnl_vec)
    mean_pnl = sum(pnl_vec) / n
    wins = sum(1 for x in pnl_vec if x > 0)
    losses = n - wins
    wr = wins / n
    cum_pnl = sum(pnl_vec)

    rng = random.Random(args.seed)
    boot = bootstrap_ci(pnl_vec, args.iterations, rng)
    p_value = permutation_test(pnl_vec, args.iterations, mean_pnl, rng)
    fwd = forward_projection(pnl_vec, args.iterations, rng)
    wilson_lo, wilson_hi = wilson_ci(wins, n)

    # Compose filter description for output/logging
    filter_desc = {
        "strategy_exact": args.strategy,
        "strategy_contains": args.strategy_contains,
        "strategy_in": sorted(strategy_set) if strategy_set else None,
        "asset_class": ac,
        "symbol": args.symbol,
        "source_system": args.source_system,
        "inverse": args.inverse,
    }

    method_bits = ["bootstrap + permutation on"]
    if args.inverse:
        method_bits.append("INVERSE-flipped")
    if args.strategy:
        method_bits.append(f"strategy='{args.strategy}'")
    elif args.strategy_contains:
        method_bits.append(f"strategy~'{args.strategy_contains}'")
    elif strategy_set:
        method_bits.append(f"strategy in [{','.join(sorted(strategy_set))}]")
    else:
        method_bits.append("all-strategies")
    method_bits.append(f"asset_class={ac}")
    if args.symbol:
        method_bits.append(f"symbol={args.symbol}")
    if args.source_system:
        method_bits.append(f"source_system={args.source_system}")
    method_str = " ".join(method_bits) + " trades"

    out_obj = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "method": method_str,
        "random_seed": args.seed,
        "n_bootstrap": args.iterations,
        "n_permutation": args.iterations,
        "fees_per_round_trip_pct": args.fees_pct,
        "filters": filter_desc,
        "historical_sample": {
            "n": n,
            "mean_net_pnl_per_trade_pct": round(mean_pnl, 3),
            "wins": wins,
            "losses": losses,
            "wr_pct": round(wr * 100, 2),
            "cumulative_net_pnl_pct": round(cum_pnl, 2),
            "wilson_95_ci_wr_pct": [round(wilson_lo * 100, 2), round(wilson_hi * 100, 2)],
        },
        "bootstrap_95_ci": {
            "mean_pnl_per_trade_pct": [round(boot["mean_ci_lo"], 3), round(boot["mean_ci_hi"], 3)],
            "win_rate_pct": [round(boot["wr_ci_lo"] * 100, 1), round(boot["wr_ci_hi"] * 100, 1)],
            "p_mean_positive": round(boot["p_mean_positive"], 4),
            "p_wr_above_55_pct": round(boot["p_wr_above_55"], 4),
        },
        "permutation_test": {
            "null_hypothesis": "Direction flips are random (50/50) \u2014 no directional edge",
            "p_value_one_sided": round(p_value, 4),
            "reject_null_at_0.05": p_value < 0.05,
            "interpretation": (
                "p < 0.05: observed mean is unlikely under random-direction null (edge is real)"
                if p_value < 0.05
                else "p >= 0.05: observed mean cannot be distinguished from random direction flips"
            ),
        },
        "forward_projection_bootstrap_resample": fwd,
        "caveats": [
            "Bootstrap assumes trades are i.i.d. \u2014 regime shifts break this",
            "Permutation test's null is direction-flip-random, not 'no edge' per se",
            "Small-n samples have wide CIs; interpret with caution",
            "Forward projection is IN-SAMPLE resample; does not account for regime decay",
            "Real deployment adds borrow, slippage, and execution costs beyond --fees-pct",
        ],
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_obj, indent=2), encoding="utf-8")

    # Human summary
    print(f"wrote {out_path}")
    print(f"filter: {method_str}")
    print(f"historical: n={n}, wr={wr*100:.1f}%, mean_pnl={mean_pnl:.2f}%, cum={cum_pnl:.2f}%")
    print(f"wilson 95% CI WR: [{wilson_lo*100:.1f}, {wilson_hi*100:.1f}]%")
    print(f"bootstrap 95% CI mean: [{boot['mean_ci_lo']:.3f}, {boot['mean_ci_hi']:.3f}]% per trade")
    print(f"bootstrap 95% CI WR: [{boot['wr_ci_lo']*100:.1f}, {boot['wr_ci_hi']*100:.1f}]%")
    print(f"P(mean PnL > 0) = {boot['p_mean_positive']:.4f}")
    print(f"permutation p-value (one-sided): {p_value:.4f}  -> {'REJECT' if p_value < 0.05 else 'cannot reject'} null at 0.05")
    for h, res in fwd.items():
        print(f"forward {h}: median={res['median_terminal_pnl_pct']}%  P(positive)={res['p_positive_cumulative_pnl']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
