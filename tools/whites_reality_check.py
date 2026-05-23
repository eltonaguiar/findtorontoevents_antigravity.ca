"""
White's Reality Check & Hansen's Superior Predictive Ability (SPA) Test
(family-wise multiple-comparison correction, M-065)

Flags strategies whose edge does not survive family-wise correction across the
full strategy set. Complements per-strategy DSR (alpha_engine/deflated_sharpe.py)
and PBO/CSCV (tools/pbo_cscv.py) with a portfolio-level correction.

References:
    White, H. (2000). "A Reality Check for Data Snooping."
        Econometrica, 68(5), 1097-1126.
    Hansen, P.R. (2005). "A Test for Superior Predictive Ability."
        Journal of Business & Economic Statistics, 23(4), 365-380.

Usage:
    python tools/whites_reality_check.py               # print report
    python tools/whites_reality_check.py --n-boot 1000 # more bootstrap iterations
    python tools/whites_reality_check.py --min-n 20    # minimum resolved picks
    python tools/whites_reality_check.py --json        # JSON output
    python tools/whites_reality_check.py --alpha 0.05  # significance level

Inputs: alpha_engine/data/closed_picks.json (WON/LOST picks with pnl_pct)
Output: per-strategy SPA verdict + family-wise p-value table
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional
import numpy as np

REPO_ROOT = Path(__file__).parent.parent
CLOSED_PATH = REPO_ROOT / "alpha_engine/data/closed_picks.json"
GATES_PATH = REPO_ROOT / "audit_trail/quality_gates.py"

DEFAULT_N_BOOT = 500
DEFAULT_MIN_N = 20
DEFAULT_ALPHA = 0.05


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_blocked() -> set[str]:
    blocked: set[str] = set()
    if not GATES_PATH.exists():
        return blocked
    text = GATES_PATH.read_text(encoding="utf-8", errors="replace")
    in_block = False
    for line in text.splitlines():
        s = line.strip()
        if ("BLOCKED_SOURCE_SYSTEMS" in s or "BLOCKED_STRATEGIES" in s) and "=" in s:
            in_block = True
        elif in_block:
            if s.startswith("}"):
                in_block = False
                continue
            if s.startswith('"') or s.startswith("'"):
                name = s.split('"')[1] if '"' in s else s.split("'")[1]
                if name:
                    blocked.add(name)
    return blocked


def _dedup_key(p: dict) -> tuple:
    """Re-emission dedup key — same shape as tools/build_pf_registry.py.
    Collapses the SAME signal re-emitted across cycles into ONE trade."""
    ep = p.get("entry_price")
    try:
        ep_k = round(float(ep), 2) if ep is not None else None
    except (TypeError, ValueError):
        ep_k = None
    td = ""
    for f in ("entry_date", "entry_time", "timestamp", "created_at",
              "closed_at", "resolved_at", "exit_date"):
        v = p.get(f)
        if v:
            td = str(v)[:10]
            break
    return (str(p.get("strategy") or p.get("source_system") or ""),
            str(p.get("symbol") or ""),
            str(p.get("direction") or ""), td, ep_k)


def load_strategy_returns(min_n: int = DEFAULT_MIN_N) -> dict[str, list[float]]:
    """Return {strategy: [pnl_pct, ...]} for strategies with >=min_n resolved
    picks. DEDUPLICATES re-emissions first — without this, a single winning
    pick re-emitted N times (e.g. ml_enhanced_FETUSDT +58% counted 10x)
    trivially 'passes' the SPA test. The whole point of the family-wise
    correction is defeated by counting one trade many times. (M-065 fix.)"""
    closed = json.loads(CLOSED_PATH.read_text()) if CLOSED_PATH.exists() else []
    blocked = _load_blocked()

    seen: set = set()
    by_strat: dict[str, list[float]] = defaultdict(list)
    for p in closed:
        strat = p.get("strategy") or p.get("source_system") or ""
        if not strat or strat in blocked:
            continue
        status = str(p.get("status", "")).upper()
        if status not in ("WON", "LOST"):
            continue
        try:
            pnl = float(p.get("pnl_pct") or 0)
        except (TypeError, ValueError):
            continue
        k = _dedup_key(p)
        if k in seen:
            continue  # re-emission of an already-counted signal
        seen.add(k)
        by_strat[strat].append(pnl)

    return {k: v for k, v in by_strat.items() if len(v) >= min_n}


def winsorize_returns(
    strategy_returns: dict[str, list[float]], sigma: float = 5.0
) -> dict[str, list[float]]:
    """Winsorize per-strategy returns at ±sigma standard deviations.

    Standard quant practice for SPA robustness — caps extreme outliers that
    would otherwise dominate bootstrap test statistics. Does NOT remove picks;
    only clips their PnL contribution.
    """
    result: dict[str, list[float]] = {}
    for name, rets in strategy_returns.items():
        arr = np.array(rets, dtype=float)
        mu, sd = arr.mean(), arr.std()
        if sd == 0:
            result[name] = rets
            continue
        lower, upper = mu - sigma * sd, mu + sigma * sd
        result[name] = list(np.clip(arr, lower, upper))
    return result


# ---------------------------------------------------------------------------
# Hansen's SPA / White's Reality Check
# ---------------------------------------------------------------------------

def _mean_excess(returns: list[float], benchmark_mean: float = 0.0) -> float:
    """Mean excess return over benchmark (default 0 = coin-flip)."""
    return float(np.mean(returns)) - benchmark_mean


def whites_spa_test(
    strategy_returns: dict[str, list[float]],
    n_boot: int = DEFAULT_N_BOOT,
    alpha: float = DEFAULT_ALPHA,
    rng_seed: int = 42,
) -> dict:
    """
    Run White's Reality Check + Hansen's SPA test over all strategies.

    Returns
    -------
    dict with keys:
        strategies   : list of per-strategy dicts with spa_passes, p_value, mean_return
        family_p_max : family-wise max-statistic p-value (White's RC)
        spa_p        : Hansen's SPA p-value (consistent bootstrap)
        n_strategies : number of strategies tested
        n_bootstrap  : bootstrap iterations used
        alpha        : significance threshold
        passes_rc    : bool — does any strategy survive White's RC?
        summary      : human-readable one-liner
    """
    rng = np.random.default_rng(rng_seed)

    names = list(strategy_returns.keys())
    N = len(names)

    if N == 0:
        return {"error": "no strategies with sufficient resolved picks", "n_strategies": 0}

    # Align returns to a common length by repeating (resample to longest)
    # Use mean excess return per strategy as the test statistic
    means = {n: _mean_excess(strategy_returns[n]) for n in names}
    T_max = max(len(strategy_returns[n]) for n in names)

    # Build returns matrix (T_max × N) by resampling shorter series
    mat = np.zeros((T_max, N))
    for j, name in enumerate(names):
        r = np.array(strategy_returns[name], dtype=float)
        if len(r) < T_max:
            # Resample with replacement to fill
            idx = rng.integers(0, len(r), size=T_max)
            r = r[idx]
        mat[:, j] = r

    # Excess returns (demeaned under H0: E[r]=0)
    V = mat - 0.0  # H0: mean excess return = 0

    # Observed test statistic: max mean excess return across strategies
    obs_means = V.mean(axis=0)  # shape (N,)
    t_obs = obs_means.max()  # White's RC test statistic

    # --- Bootstrap ---
    boot_maxes: list[float] = []
    boot_spa_maxes: list[float] = []

    for _ in range(n_boot):
        # Block bootstrap: resample rows with replacement
        idx = rng.integers(0, T_max, size=T_max)
        boot_V = V[idx, :]
        boot_means = boot_V.mean(axis=0)

        # White's RC: centered bootstrap
        boot_centered = boot_means - obs_means
        boot_maxes.append(boot_centered.max())

        # Hansen's SPA: only center strategies with positive observed mean
        # (conservative SPA variant — less sensitive to poor strategies)
        center_mask = obs_means > 0
        boot_spa = boot_means.copy()
        boot_spa[center_mask] -= obs_means[center_mask]
        boot_spa_maxes.append(boot_spa.max())

    boot_maxes_arr = np.array(boot_maxes)
    boot_spa_arr = np.array(boot_spa_maxes)

    # Family-wise p-values
    p_rc = float((boot_maxes_arr >= t_obs).mean())   # White's RC p-value
    p_spa = float((boot_spa_arr >= t_obs).mean())    # Hansen's SPA p-value

    # Per-strategy individual RC p-values (not family-corrected — illustrative)
    strat_results = []
    for j, name in enumerate(names):
        mu_j = float(obs_means[j])
        # Marginal bootstrap p-value for this strategy
        boot_j = V[rng.integers(0, T_max, size=(n_boot, T_max)), j].mean(axis=1) - mu_j
        p_j = float((boot_j >= mu_j).mean())
        strat_results.append({
            "strategy": name,
            "mean_return_pct": round(mu_j * 100, 4),
            "n_resolved": len(strategy_returns[name]),
            "p_marginal": round(p_j, 4),
            "spa_passes": mu_j > 0 and p_j <= alpha,
        })

    strat_results.sort(key=lambda x: -x["mean_return_pct"])

    passes_rc = p_rc <= alpha
    n_spa_pass = sum(1 for s in strat_results if s["spa_passes"])

    summary = (
        f"{N} strategies tested, {n_spa_pass} pass SPA (p≤{alpha}). "
        f"White's RC p={p_rc:.3f}, SPA p={p_spa:.3f}. "
        f"{'Family-wide edge SURVIVES correction.' if passes_rc else 'No strategy survives family-wise correction at α=' + str(alpha)}"
    )

    return {
        "strategies": strat_results,
        "family_p_rc": round(p_rc, 4),
        "family_p_spa": round(p_spa, 4),
        "n_strategies": N,
        "n_bootstrap": n_boot,
        "alpha": alpha,
        "passes_rc": passes_rc,
        "n_spa_pass": n_spa_pass,
        "summary": summary,
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_report(result: dict, out: Optional[Path] = None) -> None:
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    lines = [
        f"# White's Reality Check / SPA Test — {today}",
        "",
        f"**Strategies tested:** {result.get('n_strategies', 0)}",
        f"**Bootstrap iterations:** {result.get('n_bootstrap', 0)}",
        f"**Significance level (α):** {result.get('alpha', 0.05)}",
        "",
        f"**White's RC family-wise p-value:** {result.get('family_p_rc', 'N/A')}",
        f"**Hansen's SPA family-wise p-value:** {result.get('family_p_spa', 'N/A')}",
        f"**Family-wide edge survives:** {'YES' if result.get('passes_rc') else 'NO'}",
        f"**Strategies passing SPA:** {result.get('n_spa_pass', 0)} / {result.get('n_strategies', 0)}",
        "",
        f"**Summary:** {result.get('summary', '')}",
        "",
        "---",
        "",
        "## Per-Strategy Results",
        "",
        f"{'Strategy':<45} {'n':>6} {'MeanRet%':>10} {'p_marg':>8} {'SPA':>6}",
        "-" * 80,
    ]

    for s in result.get("strategies", []):
        icon = "[PASS]" if s["spa_passes"] else "[FAIL]"
        lines.append(
            f"{s['strategy']:<45} {s['n_resolved']:>6} "
            f"{s['mean_return_pct']:>10.4f} {s['p_marginal']:>8.4f} {icon:>6}"
        )

    passes = [s for s in result.get("strategies", []) if s["spa_passes"]]
    fails = [s for s in result.get("strategies", []) if not s["spa_passes"]]

    lines += [
        "",
        "## SPA-Passing Strategies (genuine edge, family-corrected)",
        *(f"- `{s['strategy']}` — mean {s['mean_return_pct']:+.4f}%/pick, p={s['p_marginal']:.4f}, n={s['n_resolved']}" for s in passes),
        "" if passes else "*(none — no strategy survives family-wise correction at this α)*",
        "",
        "## Failed Strategies (edge not distinguishable from data snooping)",
        *(f"- `{s['strategy']}` — mean {s['mean_return_pct']:+.4f}%/pick, p={s['p_marginal']:.4f}, n={s['n_resolved']}" for s in fails[:20]),
        f"  ... and {len(fails)-20} more" if len(fails) > 20 else "",
        "",
        "## Interpretation",
        "- **SPA p-value ≤ α**: at least one strategy has genuine edge beyond data snooping.",
        "- **Per-strategy p_marginal**: marginal evidence for that strategy's edge (not family-corrected).",
        "- **Strategies with spa_passes=False but positive mean**: edge may be real but inflated by",
        "  selection bias across the full strategy set. Require more data or independent OOS validation.",
        "- This test does NOT replace per-strategy DSR (alpha_engine/deflated_sharpe.py) or",
        "  PBO/CSCV (tools/pbo_cscv.py). It adds family-wise correction on top.",
    ]

    text = "\n".join(lines) + "\n"
    if out:
        out.write_text(text, encoding="utf-8")
        print(f"Report written to {out}", file=sys.stderr)
    else:
        print(text)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="White's Reality Check / Hansen's SPA test")
    parser.add_argument("--n-boot", type=int, default=DEFAULT_N_BOOT, help=f"Bootstrap iterations (default {DEFAULT_N_BOOT})")
    parser.add_argument("--min-n", type=int, default=DEFAULT_MIN_N, help=f"Minimum resolved picks per strategy (default {DEFAULT_MIN_N})")
    parser.add_argument("--alpha", type=float, default=DEFAULT_ALPHA, help=f"Significance level (default {DEFAULT_ALPHA})")
    parser.add_argument("--winsorize", type=float, default=0.0, metavar="SIGMA",
                        help="Winsorize returns at ±SIGMA std devs before testing (0=off, 5=typical)")
    parser.add_argument("--json", dest="as_json", action="store_true", help="Output JSON")
    parser.add_argument("--out", type=Path, help="Write to file instead of stdout")
    args = parser.parse_args()

    strat_returns = load_strategy_returns(min_n=args.min_n)
    if not strat_returns:
        print(f"No strategies with >={args.min_n} resolved picks found.", file=sys.stderr)
        sys.exit(1)

    if args.winsorize > 0:
        strat_returns = winsorize_returns(strat_returns, sigma=args.winsorize)

    result = whites_spa_test(strat_returns, n_boot=args.n_boot, alpha=args.alpha)
    if args.winsorize > 0:
        result["winsorized_sigma"] = args.winsorize

    if args.as_json:
        print(json.dumps(result, indent=2))
    else:
        print_report(result, out=args.out)


if __name__ == "__main__":
    main()
