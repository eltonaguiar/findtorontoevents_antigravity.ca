#!/usr/bin/env python3
"""Monte Carlo test on equity-inverse mutations.

Bootstrap 10,000 resamples with replacement of the 15 historical inverse trades
to build the distribution of expected PnL and WR under the null and alternative.

Tests:
  1. Bootstrap CI on inverse aggregate PnL
  2. Bootstrap CI on inverse WR
  3. Permutation test: is inverse PnL distinguishable from random direction flips?
  4. Forward projection: P(positive PnL over next 30/100/300 trades)

Outputs: alpha_engine/data/equity_inverse_monte_carlo_2026-04-04.json
"""
from __future__ import annotations
import json
import random
from pathlib import Path
from datetime import datetime, timezone

REPO = Path(__file__).resolve().parents[1]
DASHBOARD = REPO / "audit_dashboard" / "data" / "dashboard_data.json"
OUT = REPO / "alpha_engine" / "data" / "equity_inverse_monte_carlo_2026-04-04.json"

LOSING_STRATEGIES = {
    "Breakout Momentum", "Classic Momentum", "macd-hidden-div-scout",
    "vol-contraction-scout", "quality-minus-junk",
}
FEES_PER_ROUND_TRIP_PCT = 0.2
N_BOOTSTRAP = 10000
N_PERMUTATION = 10000
FORWARD_WINDOWS = [30, 100, 300]
RANDOM_SEED = 42


def main() -> int:
    random.seed(RANDOM_SEED)
    data = json.loads(DASHBOARD.read_text(encoding="utf-8", errors="replace"))
    closed = data["picks"]["recent_closed"]
    # Inverse PnL of losing-strategy equity trades (PnL AFTER flipping direction)
    inverse_trades = []
    for p in closed:
        if (p.get("asset_class") or "").upper() != "EQUITY":
            continue
        if p.get("strategy") not in LOSING_STRATEGIES:
            continue
        orig_pnl = float(p.get("pnl_pct") or 0)
        # Inverse is just -orig_pnl (the trade closes at its actual direction,
        # so flipping would produce the mirror outcome minus fees)
        inv_pnl_net = -orig_pnl - FEES_PER_ROUND_TRIP_PCT
        inverse_trades.append(inv_pnl_net)

    n = len(inverse_trades)
    if n == 0:
        print("no losing-strategy equity trades found", flush=True)
        return 1

    mean_pnl = sum(inverse_trades) / n
    wins = sum(1 for x in inverse_trades if x > 0)
    wr = wins / n

    # ========== Bootstrap ==========
    boot_means = []
    boot_wrs = []
    for _ in range(N_BOOTSTRAP):
        sample = [random.choice(inverse_trades) for _ in range(n)]
        boot_means.append(sum(sample) / n)
        boot_wrs.append(sum(1 for x in sample if x > 0) / n)
    boot_means.sort()
    boot_wrs.sort()
    mean_ci = (boot_means[int(0.025 * N_BOOTSTRAP)], boot_means[int(0.975 * N_BOOTSTRAP)])
    wr_ci = (boot_wrs[int(0.025 * N_BOOTSTRAP)], boot_wrs[int(0.975 * N_BOOTSTRAP)])
    p_mean_positive = sum(1 for x in boot_means if x > 0) / N_BOOTSTRAP
    p_wr_above_55 = sum(1 for x in boot_wrs if x > 0.55) / N_BOOTSTRAP

    # ========== Permutation test (H0: inverse edge = random) ==========
    # Under null, each trade has equal prob of + or - (50/50 outcome).
    # Generate null distribution by flipping signs randomly.
    abs_magnitudes = [abs(x) for x in inverse_trades]
    null_means = []
    for _ in range(N_PERMUTATION):
        null_sample = [m if random.random() < 0.5 else -m for m in abs_magnitudes]
        null_means.append(sum(null_sample) / n)
    p_value_one_sided = sum(1 for x in null_means if x >= mean_pnl) / N_PERMUTATION

    # ========== Forward projection (30/100/300 new trades) ==========
    forward_projections = {}
    for horizon in FORWARD_WINDOWS:
        terminal_pnls = []
        positives = 0
        for _ in range(N_BOOTSTRAP):
            terminal = sum(random.choice(inverse_trades) for _ in range(horizon))
            terminal_pnls.append(terminal)
            if terminal > 0:
                positives += 1
        terminal_pnls.sort()
        forward_projections[f"n_{horizon}"] = {
            "p_positive_cumulative_pnl": round(positives / N_BOOTSTRAP, 4),
            "median_terminal_pnl_pct": round(terminal_pnls[N_BOOTSTRAP // 2], 2),
            "p5_terminal_pnl_pct": round(terminal_pnls[int(0.05 * N_BOOTSTRAP)], 2),
            "p95_terminal_pnl_pct": round(terminal_pnls[int(0.95 * N_BOOTSTRAP)], 2),
            "max_drawdown_estimated_p5": round(terminal_pnls[int(0.05 * N_BOOTSTRAP)], 2),
        }

    out = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "method": "bootstrap + permutation on inverse-flipped equity-losing-strategy trades",
        "random_seed": RANDOM_SEED,
        "n_bootstrap": N_BOOTSTRAP,
        "n_permutation": N_PERMUTATION,
        "fees_per_round_trip_pct": FEES_PER_ROUND_TRIP_PCT,
        "historical_sample": {
            "n": n,
            "mean_net_pnl_per_trade_pct": round(mean_pnl, 3),
            "wins": wins,
            "losses": n - wins,
            "wr_pct": round(wr * 100, 2),
            "cumulative_net_pnl_pct": round(sum(inverse_trades), 2),
        },
        "bootstrap_95_ci": {
            "mean_pnl_per_trade_pct": [round(mean_ci[0], 3), round(mean_ci[1], 3)],
            "win_rate_pct": [round(wr_ci[0] * 100, 1), round(wr_ci[1] * 100, 1)],
            "p_mean_positive": round(p_mean_positive, 4),
            "p_wr_above_55_pct": round(p_wr_above_55, 4),
        },
        "permutation_test": {
            "null_hypothesis": "Direction flips are random (50/50) \u2014 no inverse edge",
            "p_value_one_sided": round(p_value_one_sided, 4),
            "reject_null_at_0.05": p_value_one_sided < 0.05,
            "interpretation": (
                "p < 0.05 means the observed mean is unlikely under random-direction null"
                if p_value_one_sided < 0.05
                else "p >= 0.05 means inverse edge cannot be distinguished from random"
            ),
        },
        "forward_projection_bootstrap_resample": forward_projections,
        "caveats": [
            "Bootstrap assumes trades are i.i.d. \u2014 regime shifts break this",
            "Permutation test's null is direction-flip-random, not 'no edge' per se",
            "n=15 is small; CIs are wide; real deployment adds borrow + slippage costs",
            "Forward projection is IN-SAMPLE resample; does not account for regime decay"
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"historical: n={n}, wr={wr*100:.1f}%, mean_pnl={mean_pnl:.2f}%, cum={sum(inverse_trades):.2f}%")
    print(f"bootstrap 95% CI mean: [{mean_ci[0]:.3f}, {mean_ci[1]:.3f}]% per trade")
    print(f"bootstrap 95% CI WR: [{wr_ci[0]*100:.1f}, {wr_ci[1]*100:.1f}]%")
    print(f"P(mean PnL > 0) = {p_mean_positive:.3f}")
    print(f"permutation p-value (one-sided): {p_value_one_sided:.4f}")
    for h, res in forward_projections.items():
        print(f"forward {h}: median={res['median_terminal_pnl_pct']}%  P(positive)={res['p_positive_cumulative_pnl']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
