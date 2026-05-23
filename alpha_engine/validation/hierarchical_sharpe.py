"""
hierarchical_sharpe.py — Bayesian hierarchical model for cross-asset edge sharing.

Fits a hierarchical Normal-means model across assets within the same strategy family:
  mu_i ~ Normal(mu_global, tau_global)
  observed_mean_i ~ Normal(mu_i, sigma_i / sqrt(N_i))

This "borrows strength" across assets so that low-trade symbols get shrunk toward
the group mean, reducing false-positive edge estimates.

Requirements: pymc>=5.10, arviz>=0.16, pandas, numpy, mysql-connector-python
Install: pip install pymc arviz pandas numpy mysql-connector-python

References:
  - Gelman et al., Bayesian Data Analysis (3rd ed.), Chapter 5
  - Testing Protocol Section 4 (Layer 4): Bayesian posterior of edge

Usage:
  python -m alpha_engine.validation.hierarchical_sharpe --strategy-id ema_crossover_v3
"""

import os
import sys
import json
import argparse
import numpy as np
import pandas as pd

try:
    import pymc as pm
    import arviz as az
    HAS_PYMC = True
except ImportError:
    HAS_PYMC = False

try:
    import mysql.connector
    HAS_MYSQL = True
except ImportError:
    HAS_MYSQL = False


def get_db_connection():
    """Create MySQL connection from environment variables.

    Uses `or` fallback so that empty strings (e.g. from a blank GitHub secret)
    also trigger the default, not just absent variables.
    """
    if not HAS_MYSQL:
        raise ImportError("mysql-connector-python is required")
    return mysql.connector.connect(
        user=os.getenv("MYSQL_USER") or "ejaguiar1_stocks",
        password=os.getenv("MYSQL_PASSWORD") or "",
        host=os.getenv("MYSQL_HOST") or "mysql.50webs.com",
        database=os.getenv("MYSQL_DB") or "ejaguiar1_stocks",
        raise_on_warnings=True,
    )


def load_returns_from_db(strategy_id: str, test_layer: str = "walk_forward") -> dict:
    """
    Load per-asset return statistics from strategy_test_runs.
    Returns dict of {symbol: {"n": int, "mean": float, "var": float}}.
    """
    cnx = get_db_connection()
    cursor = cnx.cursor(dictionary=True)
    cursor.execute("""
        SELECT symbol, trades, win_rate, profit_factor, sharpe,
               JSON_EXTRACT(metadata_json, '$.mean_return') AS mean_return,
               JSON_EXTRACT(metadata_json, '$.return_variance') AS return_variance
        FROM strategy_test_runs
        WHERE strategy_id = %s AND test_layer = %s
          AND symbol IS NOT NULL AND trades >= 20
        ORDER BY created_at DESC
    """, (strategy_id, test_layer))
    rows = cursor.fetchall()
    cursor.close()
    cnx.close()

    stats = {}
    for row in rows:
        sym = row["symbol"]
        if sym in stats:
            continue  # take most recent per symbol
        mean_r = float(row["mean_return"]) if row.get("mean_return") else None
        var_r = float(row["return_variance"]) if row.get("return_variance") else None
        if mean_r is not None and var_r is not None and var_r > 0:
            stats[sym] = {
                "n": int(row["trades"]),
                "mean": mean_r,
                "var": var_r,
            }
    return stats


def fit_hierarchical_model(
    asset_stats: dict,
    draws: int = 3000,
    tune: int = 2000,
    target_accept: float = 0.95,
    target_sharpe: float = 0.0,
) -> pd.DataFrame:
    """
    Fit a hierarchical Bayesian model to per-asset return statistics.

    Parameters
    ----------
    asset_stats : dict
        {symbol: {"n": int, "mean": float, "var": float}}
    target_sharpe : float
        Sharpe target for posterior probability calculation.

    Returns
    -------
    pd.DataFrame with columns:
        asset_id, posterior_mean_sharpe, hdi_lower, hdi_upper, prob_gt_target
    """
    if not HAS_PYMC:
        raise ImportError("PyMC 5+ is required: pip install pymc")

    assets = list(asset_stats.keys())
    n_assets = len(assets)

    if n_assets < 2:
        raise ValueError(f"Need >= 2 assets for hierarchical model, got {n_assets}")

    sigma_obs = []
    observed_means = []
    for a in assets:
        n_i = asset_stats[a]["n"]
        var_i = asset_stats[a]["var"]
        sigma_obs.append(np.sqrt(var_i / n_i))
        observed_means.append(asset_stats[a]["mean"])

    with pm.Model() as model:
        # Hyper-priors (weakly informative)
        mu_global = pm.Normal("mu_global", mu=0.0, sigma=1.0)
        tau_global = pm.HalfCauchy("tau_global", beta=0.5)

        # Asset-specific latent Sharpe
        mu_asset = pm.Normal("mu_asset", mu=mu_global, sigma=tau_global, shape=n_assets)

        # Likelihood
        pm.Normal("obs", mu=mu_asset, sigma=sigma_obs, observed=observed_means)

        # Inference
        trace = pm.sample(
            draws=draws, tune=tune, target_accept=target_accept,
            cores=min(2, os.cpu_count() or 1), random_seed=123,
            progressbar=True,
        )

    # Extract posterior summaries
    results = []
    for i, a in enumerate(assets):
        mu_samples = trace.posterior["mu_asset"].sel(mu_asset_dim_0=i).values.flatten()
        mean_sr = float(mu_samples.mean())
        hdi = az.hdi(mu_samples, hdi_prob=0.95)
        prob_gt = float((mu_samples > target_sharpe).mean())

        results.append({
            "asset_id": a,
            "posterior_mean_sharpe": round(mean_sr, 4),
            "hdi_lower": round(float(hdi[0]), 4),
            "hdi_upper": round(float(hdi[1]), 4),
            "prob_gt_target": round(prob_gt, 4),
        })

    return pd.DataFrame(results)


def write_results_to_db(strategy_id: str, results_df: pd.DataFrame, test_layer: str = "walk_forward"):
    """Write posterior Sharpe metrics back to strategy_test_runs."""
    cnx = get_db_connection()
    cursor = cnx.cursor()

    update_sql = """
        UPDATE strategy_test_runs
        SET deflated_sharpe = %s,
            prob_sharpe = %s,
            metadata_json = JSON_SET(
                COALESCE(metadata_json, '{}'),
                '$.posterior_mean_sharpe', %s,
                '$.hdi_lower', %s,
                '$.hdi_upper', %s,
                '$.bayesian_model', 'hierarchical_normal_means'
            )
        WHERE strategy_id = %s AND test_layer = %s AND symbol = %s
        ORDER BY created_at DESC LIMIT 1
    """

    for _, row in results_df.iterrows():
        cursor.execute(update_sql, (
            row["posterior_mean_sharpe"],
            row["prob_gt_target"],
            row["posterior_mean_sharpe"],
            row["hdi_lower"],
            row["hdi_upper"],
            strategy_id,
            test_layer,
            row["asset_id"],
        ))

    cnx.commit()
    cursor.close()
    cnx.close()
    print(f"Updated {len(results_df)} rows in strategy_test_runs.")


def main():
    parser = argparse.ArgumentParser(description="Hierarchical Bayesian edge sharing")
    parser.add_argument("--strategy-id", required=True, help="Strategy ID to evaluate")
    parser.add_argument("--test-layer", default="walk_forward", help="Test layer to pull data from")
    parser.add_argument("--target-sharpe", type=float, default=0.0, help="Target Sharpe for posterior prob")
    parser.add_argument("--draws", type=int, default=3000, help="MCMC draws")
    parser.add_argument("--dry-run", action="store_true", help="Print results without writing to DB")
    args = parser.parse_args()

    print(f"Loading data for strategy: {args.strategy_id}")
    asset_stats = load_returns_from_db(args.strategy_id, args.test_layer)

    if len(asset_stats) < 2:
        print(f"Insufficient assets ({len(asset_stats)}). Need >= 2 for hierarchical model.")
        sys.exit(1)

    print(f"Fitting hierarchical model across {len(asset_stats)} assets...")
    results_df = fit_hierarchical_model(
        asset_stats, draws=args.draws, target_sharpe=args.target_sharpe
    )

    print("\n=== Posterior Sharpe Summary ===")
    print(results_df.to_string(index=False))

    # Gate check
    passing = results_df[results_df["prob_gt_target"] >= 0.95]
    failing = results_df[results_df["prob_gt_target"] < 0.95]
    print(f"\nPassing P(Sharpe > {args.target_sharpe}) >= 0.95: {len(passing)}/{len(results_df)}")
    if len(failing) > 0:
        print(f"Failing assets: {', '.join(failing['asset_id'].tolist())}")

    if not args.dry_run:
        write_results_to_db(args.strategy_id, results_df, args.test_layer)
    else:
        print("(dry run — no DB writes)")


if __name__ == "__main__":
    main()
