#!/usr/bin/env python3
"""Edge diagnostic on latent features not currently surfaced in audit columns.

Scope (expanding beyond strategy×symbol HC-picks):
  1. Claude ML Gainer's native scores (pump_probability, confidence tier) from
     updates/data/claude_ml_picks.json (486 already-RESOLVED picks with
     tp1_hit/tp2_hit/sl_hit labels).
  2. RSI buckets (technical_rsi_1h, technical_rsi_4h) from closed_picks.
  3. Raw elite-breakdown components (regime_match, technical_alignment,
     sector_rotation) from closed_picks.
  4. Confidence × asset-class interaction (cross-check the slice diagnosis).

Writes `reports/EDGE_LATENT_FEATURES_2026_04_22.md`.

Why this tool exists: `high-conviction picks` tracks symbol-strategy WR, which
is one axis. This tool samples OTHER axes to discover where edge lives
outside the current gate's visibility.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
CLOSED_DASH = REPO / "audit_dashboard" / "data" / "dashboard_data.json"
CLAUDE_ML = REPO / "updates" / "data" / "claude_ml_picks.json"
REPORT = REPO / "reports" / "EDGE_LATENT_FEATURES_2026_04_22.md"

EDGE_MIN_N = 20


def _wr_pf(pnl: pd.Series) -> tuple[float, float, int, int, int]:
    n = len(pnl)
    if n == 0:
        return 0.0, 0.0, 0, 0, 0
    wins = int((pnl > 0).sum())
    losses = int((pnl < 0).sum())
    gp = pnl[pnl > 0].sum()
    gl = -pnl[pnl < 0].sum()
    pf = float(gp / gl) if gl > 0 else float("inf")
    return float(wins / n), pf, n, wins, losses


def bucketize_by_quantile(series: pd.Series, n_buckets: int = 4) -> pd.Series:
    """Return quantile bucket labels preserving NaN."""
    mask = series.notna()
    if mask.sum() < n_buckets * 5:
        # Not enough samples; fall back to equal-width or single bucket.
        return pd.Series(["all"] * len(series), index=series.index)
    try:
        qs = pd.qcut(series[mask], q=n_buckets, duplicates="drop", labels=None)
        out = pd.Series([None] * len(series), index=series.index, dtype=object)
        out.loc[mask] = [f"Q{i+1}" for i in range(len(qs.cat.categories))] and [
            f"Q{list(qs.cat.categories).index(x)+1}_[{x.left:.3f},{x.right:.3f}]" for x in qs
        ]
        return out
    except Exception:
        return pd.Series(["all"] * len(series), index=series.index)


def edge_table(df: pd.DataFrame, bucket_col: str, pnl_col: str = "pnl_pct", min_n: int = EDGE_MIN_N) -> pd.DataFrame:
    sub = df[[bucket_col, pnl_col]].dropna(subset=[bucket_col])
    rows = []
    for b, group in sub.groupby(bucket_col):
        pnl = group[pnl_col].dropna()
        if len(pnl) < min_n:
            continue
        wr, pf, n, wins, losses = _wr_pf(pnl)
        rows.append({
            "bucket": str(b),
            "n": n,
            "wins": wins,
            "losses": losses,
            "wr": round(wr, 4),
            "pf": round(pf, 4) if np.isfinite(pf) else None,
            "mean_pnl_pct": round(float(pnl.mean()), 4),
            "total_pnl_pct": round(float(pnl.sum()), 4),
        })
    return pd.DataFrame(rows).sort_values("wr", ascending=False).reset_index(drop=True) if rows else pd.DataFrame()


def load_claude_ml_with_labels() -> pd.DataFrame:
    """Claude ML picks carry their own resolution labels. Convert to pnl_pct for edge eval."""
    raw = json.loads(CLAUDE_ML.read_text())
    rows = raw.get("picks", [])
    records = []
    for r in rows:
        # Determine outcome from tp1_hit / tp2_hit / sl_hit flags
        entry = float(r.get("entry_price") or 0)
        exit_p = float(r.get("exit_price") or 0)
        tp2 = float(r.get("tp2_price") or 0)
        if entry > 0 and exit_p > 0:
            pnl = (exit_p - entry) / entry * 100
        elif r.get("tp2_hit"):
            pnl = float(r.get("tp2_pct") or 10)
        elif r.get("tp1_hit"):
            pnl = float(r.get("tp1_pct") or 5)
        elif r.get("sl_hit"):
            pnl = float(r.get("sl_pct") or -5)
        else:
            pnl = 0.0
        records.append({
            "pick_id": r.get("pick_id"),
            "symbol": r.get("symbol"),
            "pump_probability": float(r.get("pump_probability") or 0),
            "confidence_tier": str(r.get("confidence") or "").upper().strip(),
            "entry_time": r.get("entry_time"),
            "expiry_time": r.get("expiry_time"),
            "status": r.get("status"),
            "tp1_hit": bool(r.get("tp1_hit")),
            "tp2_hit": bool(r.get("tp2_hit")),
            "sl_hit": bool(r.get("sl_hit")),
            "pnl_pct": pnl,
            "outcome": (
                "TP2" if r.get("tp2_hit")
                else "TP1" if r.get("tp1_hit")
                else "SL" if r.get("sl_hit")
                else "EXPIRED"
            ),
        })
    return pd.DataFrame(records)


def load_closed() -> pd.DataFrame:
    raw = json.loads(CLOSED_DASH.read_text())
    picks = raw.get("picks", {}).get("recent_closed", [])
    df = pd.DataFrame(picks)
    df["pnl_pct"] = pd.to_numeric(df.get("pnl_pct"), errors="coerce")
    df = df.dropna(subset=["pnl_pct"]).copy()
    # Pull nested elite_breakdown fields
    def _eb(row: Any, k: str) -> float | None:
        eb = row.get("elite_breakdown") if isinstance(row, dict) else None
        if isinstance(eb, dict):
            v = eb.get(k)
            try: return float(v) if v is not None else None
            except (TypeError, ValueError): return None
        return None
    df["eb_regime_match"] = df.apply(lambda r: _eb(r, "regime_match"), axis=1)
    df["eb_technical_alignment"] = df.apply(lambda r: _eb(r, "technical_alignment"), axis=1)
    df["eb_sector_rotation"] = df.apply(lambda r: _eb(r, "sector_rotation"), axis=1)
    df["eb_forward_wr"] = df.apply(lambda r: _eb(r, "forward_wr"), axis=1)
    df["eb_ml_score"] = df.apply(lambda r: _eb(r, "ml_score"), axis=1)
    df["technical_rsi_1h"] = pd.to_numeric(df.get("technical_rsi_1h"), errors="coerce")
    df["technical_rsi_4h"] = pd.to_numeric(df.get("technical_rsi_4h"), errors="coerce")
    df["confidence"] = pd.to_numeric(df.get("confidence"), errors="coerce")
    df["asset_class"] = df.get("asset_class").astype(str).str.upper().replace({"ETFS": "ETF", "BONDS": "BOND", "COMMODITIES": "COMMODITY"})
    return df


def rsi_band(rsi: float | None) -> str | None:
    if rsi is None or not np.isfinite(rsi):
        return None
    if rsi < 20: return "oversold_extreme_<20"
    if rsi < 30: return "oversold_20_30"
    if rsi < 40: return "weak_30_40"
    if rsi < 60: return "neutral_40_60"
    if rsi < 70: return "strong_60_70"
    if rsi < 80: return "overbought_70_80"
    return "overbought_extreme_80+"


def pump_prob_band(p: float | None) -> str | None:
    if p is None or not np.isfinite(p) or p == 0:
        return None
    if p < 0.20: return "very_low_<0.20"
    if p < 0.35: return "low_0.20_0.35"
    if p < 0.50: return "mid_0.35_0.50"
    if p < 0.65: return "high_0.50_0.65"
    return "very_high_0.65+"


def main() -> int:
    sections: dict[str, Any] = {}

    # ── Claude ML score edge ──
    ml_df = load_claude_ml_with_labels()
    ml_df["pump_band"] = ml_df["pump_probability"].apply(pump_prob_band)
    print(f"Claude ML picks loaded: {len(ml_df)}")
    print("\nOutcome distribution:")
    print(ml_df["outcome"].value_counts().to_string())
    sections["Claude ML: outcome distribution"] = ml_df["outcome"].value_counts().reset_index().rename(columns={"index": "outcome", "outcome": "n"})

    pump_edge = edge_table(ml_df, "pump_band")
    print("\nClaude ML: edge by pump_probability band")
    print(pump_edge.to_string(index=False))
    sections["Claude ML: edge by pump_probability band"] = pump_edge

    tier_edge = edge_table(ml_df, "confidence_tier")
    print("\nClaude ML: edge by confidence_tier (VERY HIGH / HIGH / etc.)")
    print(tier_edge.to_string(index=False))
    sections["Claude ML: edge by confidence_tier"] = tier_edge

    # ── Closed picks: latent technical features ──
    cl = load_closed()
    print(f"\nClosed picks loaded: {len(cl)}")

    cl["rsi_1h_band"] = cl["technical_rsi_1h"].apply(rsi_band)
    rsi1h_edge = edge_table(cl, "rsi_1h_band")
    print("\nClosed picks: edge by technical_rsi_1h band")
    print(rsi1h_edge.to_string(index=False))
    sections["Closed picks: edge by technical_rsi_1h band"] = rsi1h_edge

    cl["rsi_4h_band"] = cl["technical_rsi_4h"].apply(rsi_band)
    rsi4h_edge = edge_table(cl, "rsi_4h_band")
    print("\nClosed picks: edge by technical_rsi_4h band")
    print(rsi4h_edge.to_string(index=False))
    sections["Closed picks: edge by technical_rsi_4h band"] = rsi4h_edge

    # Elite breakdown components
    for col in ("eb_regime_match", "eb_technical_alignment", "eb_sector_rotation", "eb_ml_score"):
        cl[f"{col}_band"] = bucketize_by_quantile(cl[col], n_buckets=4)
        e = edge_table(cl, f"{col}_band")
        if not e.empty:
            print(f"\nClosed picks: edge by {col} quartile")
            print(e.to_string(index=False))
            sections[f"Closed picks: edge by {col} quartile"] = e

    # ── Cross: RSI × asset_class (RSI strategies may only work on crypto) ──
    cl["rsi4h_x_ac"] = cl["rsi_4h_band"].astype(str) + " | " + cl["asset_class"].astype(str)
    cross = edge_table(cl, "rsi4h_x_ac", min_n=30)
    print("\nClosed picks: edge by RSI-4h × asset_class (min_n=30)")
    print(cross.head(20).to_string(index=False))
    sections["Closed picks: edge by RSI-4h × asset_class (top 20)"] = cross.head(20)

    # ── Write report ──
    lines = ["# Latent-Feature Edge Diagnostic — 2026-04-22\n"]
    lines.append("**Purpose:** discover edge on features NOT currently surfaced as audit columns.\n")
    lines.append("**Inputs:** `updates/data/claude_ml_picks.json` (486 resolved ML picks with pump_probability + confidence tier) + `audit_dashboard/data/dashboard_data.json` (3,500 closed picks, incl. technical_rsi_1h/4h + elite_breakdown components).\n")
    lines.append(f"**Edge threshold:** n >= {EDGE_MIN_N} to report a bucket.\n")
    for title, body in sections.items():
        lines.append(f"\n## {title}\n")
        if isinstance(body, pd.DataFrame):
            if body.empty:
                lines.append("_empty_\n")
                continue
            try: lines.append(body.to_markdown(index=False))
            except ImportError: lines.append("```\n" + body.to_string(index=False) + "\n```")
            lines.append("")
        else:
            lines.append(str(body) + "\n")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport -> {REPORT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
