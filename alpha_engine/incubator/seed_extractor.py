"""
Incubator — Seed Extractor
============================
Queries the alpha.db (SQLite) strategy_stats table AND the MySQL audit DB
for the top 20-30 strategies by Sharpe ratio + lowest max drawdown.

Returns structured seed records with full parameter metadata.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

# Alpha engine paths
ENGINE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ENGINE_DIR / "data"
ALPHA_DB = DATA_DIR / "alpha.db"


def extract_seeds(
    top_n: int = 30,
    min_closed_picks: int = 5,
    db_path: Path = ALPHA_DB,
) -> pd.DataFrame:
    """Extract top-performing strategies from the local alpha.db.

    Returns DataFrame with columns:
        strategy, closed_picks, wins, losses, win_rate, avg_pnl_pct,
        total_pnl_pct, sharpe, sortino, max_drawdown, profit_factor,
        kelly_fraction, avg_hold_days, composite_score
    """
    if not db_path.exists():
        print(f"[seed_extractor] WARNING: {db_path} not found, returning empty")
        return pd.DataFrame()

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Get latest snapshot per strategy
    rows = conn.execute("""
        SELECT s.*
        FROM strategy_stats s
        INNER JOIN (
            SELECT strategy, MAX(snapshot_date) AS max_date
            FROM strategy_stats
            GROUP BY strategy
        ) latest ON s.strategy = latest.strategy AND s.snapshot_date = latest.max_date
        WHERE s.closed_picks >= ?
        ORDER BY s.sharpe DESC
    """, (min_closed_picks,)).fetchall()

    if not rows:
        # Fallback: compute stats from picks table directly
        print("[seed_extractor] No strategy_stats found, computing from picks...")
        rows = _compute_from_picks(conn, min_closed_picks)

    conn.close()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame([dict(r) for r in rows])

    # Compute composite score for ranking
    df = _add_composite_score(df)

    # Sort by composite and take top N
    df = df.sort_values("composite_score", ascending=False).head(top_n)
    df = df.reset_index(drop=True)

    print(f"[seed_extractor] Extracted {len(df)} seed strategies "
          f"(min {min_closed_picks} closed picks)")
    return df


def _compute_from_picks(conn: sqlite3.Connection, min_closed: int) -> list[dict]:
    """Compute strategy stats directly from the picks table."""
    query = """
        SELECT strategy,
               COUNT(*) as closed_picks,
               SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) as wins,
               SUM(CASE WHEN pnl_pct <= 0 THEN 1 ELSE 0 END) as losses,
               AVG(pnl_pct) as avg_pnl_pct,
               SUM(pnl_pct) as total_pnl_pct,
               AVG(hold_days) as avg_hold_days
        FROM picks
        WHERE status IN ('WON', 'LOST', 'EXPIRED')
        GROUP BY strategy
        HAVING closed_picks >= ?
    """
    rows = conn.execute(query, (min_closed,)).fetchall()
    results = []
    for r in rows:
        d = dict(r)
        d["win_rate"] = d["wins"] / d["closed_picks"] if d["closed_picks"] > 0 else 0

        # Compute Sharpe from individual PnLs
        pnls = conn.execute(
            "SELECT pnl_pct FROM picks WHERE strategy = ? AND status IN ('WON','LOST','EXPIRED')",
            (d["strategy"],)
        ).fetchall()
        pnl_arr = np.array([p[0] for p in pnls if p[0] is not None])

        if len(pnl_arr) > 1 and pnl_arr.std() > 0.001:
            raw_sharpe = float(pnl_arr.mean() / pnl_arr.std() * np.sqrt(252))
            d["sharpe"] = round(max(-99.99, min(99.99, raw_sharpe)), 3)
            downside = pnl_arr[pnl_arr < 0]
            raw_sortino = float(
                pnl_arr.mean() / downside.std() * np.sqrt(252)
                if len(downside) > 0 and downside.std() > 0.001 else d["sharpe"]
            )
            d["sortino"] = round(max(-99.99, min(99.99, raw_sortino)), 3)
        else:
            d["sharpe"] = 0.0
            d["sortino"] = 0.0

        # Max drawdown
        cum = np.cumsum(pnl_arr)
        peak = np.maximum.accumulate(cum) if len(cum) > 0 else np.array([0])
        dd = cum - peak
        d["max_drawdown"] = round(float(dd.min()), 6) if len(dd) > 0 else 0.0

        # Profit factor
        gross_profit = sum(p for p in pnl_arr if p > 0)
        gross_loss = abs(sum(p for p in pnl_arr if p < 0))
        d["profit_factor"] = round(gross_profit / gross_loss, 3) if gross_loss > 0 else 99.0

        # Kelly
        if 0 < d["win_rate"] < 1:
            avg_win = np.mean([p for p in pnl_arr if p > 0]) if d["wins"] > 0 else 0
            avg_loss = abs(np.mean([p for p in pnl_arr if p < 0])) if d["losses"] > 0 else 1
            d["kelly_fraction"] = round(d["win_rate"] - (1 - d["win_rate"]) / (avg_win / avg_loss) if avg_loss > 0 else 0, 4)
        else:
            d["kelly_fraction"] = 0.0

        results.append(d)
    return results


def _add_composite_score(df: pd.DataFrame) -> pd.DataFrame:
    """Add composite ranking score: 0.4*Sharpe - 0.3*MaxDD + 0.2*PF + 0.1*WR."""
    # Normalize each metric to 0-1 scale
    def norm(series: pd.Series) -> pd.Series:
        s_min, s_max = series.min(), series.max()
        if s_max == s_min:
            return pd.Series(0.5, index=series.index)
        return (series - s_min) / (s_max - s_min)

    sharpe_n = norm(df["sharpe"].clip(-5, 20))
    # MaxDD is negative, so we want LESS negative = better → invert
    dd_n = norm(-df["max_drawdown"].clip(-1, 0))
    pf_n = norm(df["profit_factor"].clip(0, 10))
    wr_n = norm(df["win_rate"].clip(0, 1) if df["win_rate"].max() <= 1
                else df["win_rate"].clip(0, 100) / 100)

    df["composite_score"] = (
        0.4 * sharpe_n
        - 0.3 * (1 - dd_n)  # penalize high drawdown
        + 0.2 * pf_n
        + 0.1 * wr_n
    ).round(4)

    return df


def map_seed_to_archetype(strategy_name: str) -> Optional[str]:
    """Map a live strategy name to its closest incubator archetype."""
    from .parameter_space import ARCHETYPES

    # Keyword mapping: strategy name patterns → archetype names
    MAPPING = {
        "rsi": "rsi_mean_reversion",
        "connors_rsi": "rsi_mean_reversion",
        "stochrsi": "stochrsi_bounce",
        "macd": "macd_divergence",
        "cross_sectional": "cross_sectional_momentum",
        "ema": "ema_crossover",
        "ichimoku": "ichimoku_cloud",
        "sma_bounce": "sma_bounce",
        "200d_sma": "sma_bounce",
        "bollinger": "bollinger_squeeze",
        "squeeze": "bollinger_squeeze",
        "keltner": "atr_breakout",
        "atr": "atr_breakout",
        "zscore": "mean_reversion_zscore",
        "mean_reversion": "mean_reversion_zscore",
        "volume_breakout": "volume_breakout",
        "volume_climax": "volume_breakout",
        "obv": "volume_breakout",
        "vwap": "vwap_reversion",
        "support_resistance": "support_resistance_bounce",
        "sr_": "support_resistance_bounce",
        "swing_failure": "swing_failure_pattern",
        "sfp": "swing_failure_pattern",
        "funding": "funding_rate_extreme",
        "fear_greed": "fear_greed_contrarian",
        "mvrv": "mvrv_proxy",
        "netflow": "exchange_netflow",
        "momentum": "cross_sectional_momentum",
    }

    name_lower = strategy_name.lower()
    for keyword, archetype in MAPPING.items():
        if keyword in name_lower:
            return archetype

    # Default: pick based on family from STRATEGY_FAMILIES
    return None


if __name__ == "__main__":
    seeds = extract_seeds()
    if len(seeds) > 0:
        print("\n=== TOP SEED STRATEGIES ===")
        for _, row in seeds.iterrows():
            print(f"  {row['strategy']:40s} Sharpe={row['sharpe']:6.2f}  "
                  f"WR={row.get('win_rate', 0):.1%}  "
                  f"DD={row.get('max_drawdown', 0):.4f}  "
                  f"PF={row.get('profit_factor', 0):.2f}  "
                  f"Score={row['composite_score']:.3f}")
    else:
        print("No seeds found. Run the scanner first to accumulate picks.")
