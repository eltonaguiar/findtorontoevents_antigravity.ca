"""
AI Tournament Leaderboard Updater.

Reads all resolved picks from data/ai_tournament/picks_latest.json,
computes WR, PF, 95% CI (Wilson for WR, bootstrap for PF), and
Score = lower_95%(WR) × lower_95%(PF).

Writes to audit_dashboard/data/ai_tournament_leaderboard.json.

Statistical notes:
  - WR CI: Wilson interval (Brown, Cai, DasGupta 2001)
  - PF CI: bootstrap (10,000 resamples)
  - Score: product of lower 95% CI bounds (Cerebras consensus rec.)
  - Min n=30 to appear in ranked section
"""

from __future__ import annotations
import json
import math
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from normalize import is_resolution_trustworthy

REPO_ROOT = Path(__file__).parent.parent.parent
LATEST_PICKS = REPO_ROOT / "audit_dashboard" / "data" / "ai_tournament_picks_latest.json"
LEADERBOARD_OUT = REPO_ROOT / "audit_dashboard" / "data" / "ai_tournament_leaderboard.json"

MIN_N_TO_RANK = 30
N_BOOTSTRAP = 10_000
CI_LEVEL = 0.95  # 95% confidence intervals
Z_95 = 1.959964  # z_{0.975}


def wilson_ci(n_wins: int, n_total: int, z: float = Z_95) -> tuple[float, float]:
    """Wilson score confidence interval for a proportion."""
    if n_total == 0:
        return (0.0, 1.0)
    p_hat = n_wins / n_total
    denom = 1 + z * z / n_total
    centre = (p_hat + z * z / (2 * n_total)) / denom
    margin = (z * math.sqrt(p_hat * (1 - p_hat) / n_total + z * z / (4 * n_total * n_total))) / denom
    return (max(0.0, centre - margin), min(1.0, centre + margin))


def bootstrap_pf_ci(
    pnls: list[float], n_boot: int = N_BOOTSTRAP, alpha: float = 1 - CI_LEVEL
) -> tuple[float, float]:
    """Bootstrap 95% CI for profit factor from a list of per-trade P&L values."""
    if not pnls:
        return (0.0, 0.0)

    # Log-space PF estimator with pseudo-loss regularisation.
    # When a bootstrap resample contains zero real losses, the raw PF is
    # undefined (division by zero).  Adding a small pseudo-loss — half the
    # mean absolute P&L — to every sample's loss total prevents infinite PF
    # while barely affecting normal resamples.  The regularisation naturally
    # shrinks harder in small-n / high-PF edge cases where it is needed most.
    _PSEUDO_LOSS_FACTOR = 0.5   # fraction of mean_abs_pnl added as pseudo-loss
    _MIN_SAFE_WINS   = 0.001    # floor for log(wins) so we never feed log(0)
    mean_abs = sum(abs(v) for v in pnls) / len(pnls)
    pseudo_loss = mean_abs * _PSEUDO_LOSS_FACTOR

    def _log_pf(sample: list[float]) -> float:
        """Return log-PF for the sample.  Never +inf because pseudo_loss > 0."""
        wins   = sum(v for v in sample if v > 0)
        losses = abs(sum(v for v in sample if v < 0))
        return math.log(max(wins, _MIN_SAFE_WINS)) - math.log(losses + pseudo_loss)

    boot_pfs = []
    for _ in range(n_boot):
        sample = random.choices(pnls, k=len(pnls))
        boot_pfs.append(_log_pf(sample))

    boot_pfs.sort()
    lo_idx = int(alpha / 2 * n_boot)
    hi_idx = int((1 - alpha / 2) * n_boot)
    return (math.exp(boot_pfs[lo_idx]), math.exp(boot_pfs[min(hi_idx, n_boot - 1)]))


def tier(wr: float, pf: float) -> str:
    if pf >= 2.0 and wr >= 0.55:
        return "T1"
    if pf >= 1.5 and wr >= 0.50:
        return "T2"
    if pf >= 1.3 and wr >= 0.45:
        return "T3"
    return "BELOW"


def main() -> None:
    if not LATEST_PICKS.exists():
        print("[leaderboard] no picks file found — skipping")
        return

    picks: list[dict[str, Any]] = json.loads(LATEST_PICKS.read_text())
    if not picks:
        print("[leaderboard] empty picks file — writing empty leaderboard")
        write_leaderboard([])
        return

    # Group by model
    by_model: dict[str, list[dict]] = {}
    for p in picks:
        mid = p.get("model_id", "unknown")
        by_model.setdefault(mid, []).append(p)

    models = []
    for model_id, model_picks in by_model.items():
        all_resolved = [p for p in model_picks if p.get("status") not in ("OPEN",)]
        # Drop impossible resolutions (resolved_at < submitted_at, or TP/SL on the
        # wrong side of entry) so WR/PF aren't built on corrupt rows.
        resolved = [p for p in all_resolved if is_resolution_trustworthy(p)]
        n_excluded = len(all_resolved) - len(resolved)
        n_total = len(model_picks)
        n_resolved = len(resolved)

        pnls = [p["pnl_pct"] for p in resolved if p.get("pnl_pct") is not None]
        n_wins = sum(1 for v in pnls if v > 0)

        wr = n_wins / n_resolved if n_resolved > 0 else 0.0
        win_pnls = [v for v in pnls if v > 0]
        loss_pnls = [abs(v) for v in pnls if v < 0]
        pf = sum(win_pnls) / sum(loss_pnls) if sum(loss_pnls) > 0 else (10.0 if sum(win_pnls) > 0 else 0.0)

        wr_ci_lo, wr_ci_hi = wilson_ci(n_wins, n_resolved)
        pf_ci_lo, pf_ci_hi = bootstrap_pf_ci(pnls) if n_resolved >= 5 else (0.0, 0.0)

        score = wr_ci_lo * pf_ci_lo  # Cerebras recommended scoring formula

        provider = model_picks[0].get("provider", "unknown")
        model_version = model_picks[0].get("model_version", "")

        models.append({
            "model_id": model_id,
            "provider": provider,
            "model_version": model_version,
            "n_picks": n_total,
            "n_resolved": n_resolved,
            "n_excluded_untrustworthy": n_excluded,
            "n_wins": n_wins,
            "wr": round(wr, 4),
            "wr_ci_lo": round(wr_ci_lo, 4),
            "wr_ci_hi": round(wr_ci_hi, 4),
            "pf": round(pf, 3),
            "pf_ci_lo": round(pf_ci_lo, 3),
            "pf_ci_hi": round(pf_ci_hi, 3),
            "score": round(score, 4),
            "tier": tier(wr, pf) if n_resolved >= MIN_N_TO_RANK else "BUILDING",
            "rank_eligible": n_resolved >= MIN_N_TO_RANK,
        })

    # Sort: rank-eligible first by score desc, then building by n_resolved desc
    ranked = sorted([m for m in models if m["rank_eligible"]], key=lambda x: x["score"], reverse=True)
    building = sorted([m for m in models if not m["rank_eligible"]], key=lambda x: x["n_resolved"], reverse=True)

    for i, m in enumerate(ranked, 1):
        m["rank"] = i
    for m in building:
        m["rank"] = None

    all_models = ranked + building
    write_leaderboard(all_models)
    print(f"[leaderboard] updated: {len(ranked)} ranked, {len(building)} building")


def write_leaderboard(models: list[dict]) -> None:
    out = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "min_n_to_rank": MIN_N_TO_RANK,
        "scoring_formula": "lower_95pct_WR * lower_95pct_PF",
        "wr_ci_method": "Wilson (Brown 2001)",
        "pf_ci_method": f"Bootstrap ({N_BOOTSTRAP} resamples)",
        "models": models,
    }
    LEADERBOARD_OUT.parent.mkdir(parents=True, exist_ok=True)
    LEADERBOARD_OUT.write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
