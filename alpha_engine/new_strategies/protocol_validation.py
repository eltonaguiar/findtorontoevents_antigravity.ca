import random
from typing import List, Dict


def _percentile(sorted_vals: List[float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = max(0, min(len(sorted_vals) - 1, int(q * (len(sorted_vals) - 1))))
    return float(sorted_vals[idx])


def bootstrap_ci(trade_pnls: List[float], n_boot: int = 1000, seed: int = 42) -> Dict:
    if not trade_pnls:
        return {"mean": 0.0, "ci_low": 0.0, "ci_high": 0.0, "n_boot": n_boot}

    rng = random.Random(seed)
    n = len(trade_pnls)
    means = []
    for _ in range(n_boot):
        sample = [trade_pnls[rng.randrange(0, n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    return {
        "mean": round(sum(means) / len(means), 4),
        "ci_low": round(_percentile(means, 0.025), 4),
        "ci_high": round(_percentile(means, 0.975), 4),
        "n_boot": n_boot,
    }


def monte_carlo_prob_profitable(trade_pnls: List[float], n_sims: int = 2000, horizon: int = 30, seed: int = 42) -> Dict:
    if not trade_pnls:
        return {"prob_profitable": 0.0, "n_sims": n_sims, "horizon": horizon}

    rng = random.Random(seed)
    n = len(trade_pnls)
    profitable = 0
    totals = []
    for _ in range(n_sims):
        pnl_total = 0.0
        for _ in range(horizon):
            pnl_total += trade_pnls[rng.randrange(0, n)]
        totals.append(pnl_total)
        if pnl_total > 0:
            profitable += 1
    totals.sort()
    return {
        "prob_profitable": round(profitable / n_sims, 4),
        "median_total_pnl": round(_percentile(totals, 0.5), 4),
        "p10_total_pnl": round(_percentile(totals, 0.1), 4),
        "p90_total_pnl": round(_percentile(totals, 0.9), 4),
        "n_sims": n_sims,
        "horizon": horizon,
    }


def summarize_protocol(trade_pnls: List[float], wins: int, losses: int) -> Dict:
    total = len(trade_pnls)
    wr = (wins / total * 100.0) if total else 0.0
    avg = (sum(trade_pnls) / total) if total else 0.0
    gross_win = sum(p for p in trade_pnls if p > 0)
    gross_loss = abs(sum(p for p in trade_pnls if p <= 0))
    pf = (gross_win / gross_loss) if gross_loss > 0 else 0.0
    boot = bootstrap_ci(trade_pnls)
    mc = monte_carlo_prob_profitable(trade_pnls)
    wf = walk_forward_validation(trade_pnls)
    return {
        "trades": total,
        "win_rate": round(wr, 2),
        "avg_pnl": round(avg, 4),
        "profit_factor": round(pf, 3),
        "walk_forward": wf,
        "bootstrap": boot,
        "monte_carlo": mc,
    }


def walk_forward_validation(trade_pnls: List[float], train: int = 12, test: int = 6, step: int = 3) -> Dict:
    """Simple anchored walk-forward over trade sequence."""
    n = len(trade_pnls)
    if n < (train + test):
        return {
            "folds": 0,
            "avg_oos_wr": 0.0,
            "avg_oos_pnl": 0.0,
            "status": "insufficient_trades",
        }

    folds = []
    start = train
    while start + test <= n:
        oos = trade_pnls[start:start + test]
        oos_wins = sum(1 for p in oos if p > 0)
        oos_wr = (oos_wins / len(oos)) * 100 if oos else 0
        oos_avg = (sum(oos) / len(oos)) if oos else 0
        folds.append((oos_wr, oos_avg))
        start += step

    if not folds:
        return {
            "folds": 0,
            "avg_oos_wr": 0.0,
            "avg_oos_pnl": 0.0,
            "status": "insufficient_trades",
        }

    return {
        "folds": len(folds),
        "avg_oos_wr": round(sum(f[0] for f in folds) / len(folds), 2),
        "avg_oos_pnl": round(sum(f[1] for f in folds) / len(folds), 4),
        "status": "ok",
    }


def protocol_gate(
    trade_count: int,
    win_rate: float,  # 0.0-1.0
    profit_factor: float,
    ci: Dict,
    mc_prob: float,
    min_trades: int = 10,
    min_wr: float = 0.45,
    min_pf: float = 1.20,
    min_mc: float = 0.65,
    min_ci_check: bool = True,  # set False for low-frequency strategies
) -> Dict:
    """
    Standardized protocol gate (keyword-arg version used by new strategy scripts).
    Returns gate=PASS|FAIL with reason.
    """
    reasons = []
    if trade_count < min_trades:
        reasons.append(f"insufficient_trades:{trade_count}<{min_trades}")
    if win_rate < min_wr:
        reasons.append(f"low_wr:{win_rate:.3f}<{min_wr:.3f}")
    if profit_factor < min_pf:
        reasons.append(f"low_pf:{profit_factor:.3f}<{min_pf:.3f}")
    if mc_prob < min_mc:
        reasons.append(f"low_mc:{mc_prob:.3f}<{min_mc:.3f}")
    ci_low = ci.get("ci_low", 0.0) if isinstance(ci, dict) else 0.0
    if min_ci_check and ci_low < 0:
        reasons.append(f"ci_lower_negative:{ci_low:.4f}")

    gate = "PASS" if not reasons else "FAIL"
    return {
        "gate": gate,
        "trade_count": trade_count,
        "win_rate": round(win_rate, 4),
        "profit_factor": round(profit_factor, 4),
        "mc_prob": round(mc_prob, 4),
        "ci_low": round(ci_low, 4),
        "reasons": reasons,
    }
