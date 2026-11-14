#!/usr/bin/env python3
"""
Bootstrap Validation for Verified Edges

Validates the 3 verified profitable edges using bootstrap resampling
to compute confidence intervals for PF, WR, and Sharpe.

Usage:
    python3 alpha_engine/bootstrap_verified_edges.py

Output:
    audit_dashboard/data/bootstrap_verified_edges.json
"""
from __future__ import annotations

import json
import logging
import math
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("bootstrap_verified_edges")

# Bootstrap config
N_BOOTSTRAPS = 10_000
CI_ALPHA = 0.05  # 95% CI
RANDOM_SEED = 42

# Verified edges configuration
EDGES = {
    "quan_engine": {
        "source_system": "quan_engine",
        "n_claimed": 284,
        "wr_claimed": 0.958,
        "pf_claimed": None,  # compute from data
        "asset_class": "CRYPTO",
    },
    "st_rsi_momentum_confluence": {
        "strategy": "st_rsi_momentum_confluence",
        "n_claimed": 258,
        "wr_claimed": 0.651,
        "pf_claimed": 2.53,
        "asset_class": "CRYPTO",
    },
    "short_bias_crypto": {
        "direction": "SHORT",
        "asset_class": "CRYPTO",
        "wr_claimed": 0.72,
    },
}


def _load_closed_picks() -> list[dict]:
    """Load closed picks from various sources."""
    picks = []
    # Try MySQL first, then JSON fallbacks
    try:
        import pymysql
        from tools.db_env import get_stocks_creds
        creds = get_stocks_creds()
        conn = pymysql.connect(
            host=creds["host"], user=creds["user"], password=creds["password"],
            database=creds["database"], port=creds.get("port", 3306),
            cursorclass=pymysql.cursors.DictCursor,
        )
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT symbol, strategy, source_system, direction, entry_price, exit_price,
                       pnl_pct, status, asset_class, created_at
                FROM trading_picks
                WHERE status IN ('CLOSED', 'WON', 'LOST', 'TP_HIT', 'SL_HIT', 'TIME_EXIT')
                  AND pnl_pct IS NOT NULL
                  AND created_at >= DATE_SUB(NOW(), INTERVAL 90 DAY)
                """
            )
            picks = cur.fetchall()
        conn.close()
        log.info("Loaded %d closed picks from MySQL (last 90d)", len(picks))
    except Exception as exc:
        log.warning("MySQL load failed: %s — trying JSON fallbacks", exc)

    # JSON fallbacks
    if not picks:
        for path in [
            REPO / "audit_trail" / "data" / "universal_resolved_picks.json",
            REPO / "audit_dashboard" / "data" / "pf_registry.json",
        ]:
            if path.exists():
                try:
                    with open(path) as f:
                        data = json.load(f)
                    items = data if isinstance(data, list) else data.get("picks", data.get("closed_picks", []))
                    picks.extend([i for i in items if isinstance(i, dict)])
                except Exception:
                    pass
        log.info("Loaded %d closed picks from JSON fallbacks", len(picks))

    return picks


def _filter_edge(picks: list[dict], edge_config: dict) -> list[dict]:
    """Filter picks to those matching the edge configuration."""
    filtered = []
    for p in picks:
        match = True
        for key, value in edge_config.items():
            if key in ("n_claimed", "wr_claimed", "pf_claimed"):
                continue
            if str(p.get(key, "")).lower() != str(value).lower():
                match = False
                break
        if match:
            filtered.append(p)
    return filtered


def _compute_pf(pnls: list[float]) -> float:
    """Compute profit factor (gross wins / gross losses)."""
    wins = sum(p for p in pnls if p > 0)
    losses = abs(sum(p for p in pnls if p < 0))
    return wins / losses if losses > 0 else float("inf")


def _compute_sharpe(pnls: list[float]) -> float:
    """Compute annualized Sharpe (simplified: mean / std * sqrt(252))."""
    if len(pnls) < 2:
        return 0.0
    mean = sum(pnls) / len(pnls)
    variance = sum((p - mean) ** 2 for p in pnls) / (len(pnls) - 1)
    std = math.sqrt(variance)
    if std == 0:
        return 0.0
    return (mean / std) * math.sqrt(252)


def _bootstrap(pnls: list[float], n: int = N_BOOTSTRAPS, seed: int = RANDOM_SEED) -> dict:
    """Bootstrap resample pnls and return CI for WR, PF, Sharpe."""
    rng = random.Random(seed)
    n_samples = len(pnls)

    wrs, pfs, sharpes = [], [], []
    for _ in range(n):
        sample = [rng.choice(pnls) for _ in range(n_samples)]
        wins = sum(1 for p in sample if p > 0)
        wrs.append(wins / n_samples)
        pfs.append(_compute_pf(sample))
        sharpes.append(_compute_sharpe(sample))

    def _ci(values: list[float]) -> tuple[float, float, float]:
        values_sorted = sorted(values)
        lo_idx = int(n * CI_ALPHA / 2)
        hi_idx = int(n * (1 - CI_ALPHA / 2))
        return (
            round(values_sorted[lo_idx], 4),
            round(sum(values) / n, 4),
            round(values_sorted[hi_idx], 4),
        )

    return {
        "wr_ci": _ci(wrs),
        "pf_ci": _ci(pfs),
        "sharpe_ci": _ci(sharpes),
        "n": n_samples,
        "n_bootstraps": n,
    }


def main() -> int:
    log.info("Bootstrap Validation for Verified Edges starting")
    picks = _load_closed_picks()
    if not picks:
        log.error("No closed picks loaded — cannot validate")
        return 1

    results = {}
    for edge_name, edge_config in EDGES.items():
        edge_picks = _filter_edge(picks, edge_config)
        n = len(edge_picks)
        log.info("Edge %s: %d picks found (claimed n=%s)", edge_name, n, edge_config.get("n_claimed", "?"))

        if n < 30:
            log.warning("Edge %s: n=%d < 30 — insufficient for bootstrap", edge_name, n)
            results[edge_name] = {"status": "INSUFFICIENT_N", "n": n, "min_required": 30}
            continue

        pnls = [float(p.get("pnl_pct", 0) or 0) for p in edge_picks]
        bootstrap = _bootstrap(pnls)

        # Pass/fail gates
        wr_lo, wr_mean, wr_hi = bootstrap["wr_ci"]
        pf_lo, pf_mean, pf_hi = bootstrap["pf_ci"]
        sharpe_lo, sharpe_mean, sharpe_hi = bootstrap["sharpe_ci"]

        gates = {
            "n_min_30": n >= 30,
            "wr_ci_above_50": wr_lo > 0.50,
            "pf_ci_above_1": pf_lo > 1.0,
            "sharpe_ci_above_0": sharpe_lo > 0,
        }
        all_pass = all(gates.values())

        results[edge_name] = {
            "status": "PASS" if all_pass else "FAIL",
            "n": n,
            "wr_claimed": edge_config.get("wr_claimed"),
            "pf_claimed": edge_config.get("pf_claimed"),
            "bootstrap": bootstrap,
            "gates": gates,
        }

        log.info(
            "Edge %s: %s | WR=%.1f%% (CI: %.1f%%-%.1f%%) | PF=%.2f (CI: %.2f-%.2f) | Sharpe=%.2f (CI: %.2f-%.2f)",
            edge_name,
            "PASS" if all_pass else "FAIL",
            wr_mean * 100,
            wr_lo * 100,
            wr_hi * 100,
            pf_mean,
            pf_lo,
            pf_hi,
            sharpe_mean,
            sharpe_lo,
            sharpe_hi,
        )

    # Save results
    out_path = REPO / "audit_dashboard" / "data" / "bootstrap_verified_edges.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "n_bootstraps": N_BOOTSTRAPS,
            "ci_alpha": CI_ALPHA,
            "results": results,
        }, f, indent=2, default=str)
    log.info("Results saved to %s", out_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
