#!/usr/bin/env python3
"""Per-asset-class edge diagnostic across last-N windows.

Answers:
  1. Are the user's last-20 WR claims real? (stocks 65%, forex 5%,
     commodities 15%, bonds 47.1%, etfs 85%).
  2. Do they hold when extended to last-50 / 100 / 200 / all?
  3. Where does the edge concentrate within each class (strategy,
     symbol, direction, confidence bucket)?

Data source: `audit_dashboard/data/dashboard_data.json` -> `picks.recent_closed`
which contains normalized non-crypto asset class tags.

Writes `reports/EDGE_BY_ASSET_CLASS_2026_04_22.md`.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
# dashboard_data.json.picks.recent_closed has asset_class tags applied by the dashboard
# generator; closed_picks.json is crypto-only. Use dashboard_data as authoritative source
# for per-asset-class analysis.
DASHBOARD = REPO / "audit_dashboard" / "data" / "dashboard_data.json"
REPORT = REPO / "reports" / "EDGE_BY_ASSET_CLASS_2026_04_22.md"

WINDOWS = [20, 50, 100, 200]
EDGE_WR = 0.45      # minimum WR to call something "has edge"
EDGE_PF = 1.10      # minimum PF to call something "has edge"
EDGE_MIN_N = 30     # minimum sample for the edge claim to be meaningful


def _wr(s: pd.Series) -> float:
    return float((s > 0).mean()) if len(s) else 0.0


def _pf(s: pd.Series) -> float:
    gp = s[s > 0].sum()
    gl = -s[s < 0].sum()
    return float(gp / gl) if gl > 0 else float("inf")


def _stats(df: pd.DataFrame) -> dict[str, Any]:
    n = len(df)
    if n == 0:
        return {"n": 0, "wr": None, "wr_excl_flat": None, "pf": None, "mean_pnl_pct": None, "total_pnl_pct": None}
    wins = int((df["pnl_pct"] > 0).sum())
    losses = int((df["pnl_pct"] < 0).sum())
    flat = int((df["pnl_pct"] == 0).sum())
    non_flat = wins + losses
    return {
        "n": n,
        "wins": wins,
        "losses": losses,
        "flat": flat,
        "wr": round(float(wins / n), 4),
        "wr_excl_flat": round(float(wins / non_flat), 4) if non_flat else None,
        "pf": round(_pf(df["pnl_pct"]), 4) if np.isfinite(_pf(df["pnl_pct"])) else None,
        "mean_pnl_pct": round(float(df["pnl_pct"].mean()), 4),
        "total_pnl_pct": round(float(df["pnl_pct"].sum()), 4),
    }


def _is_status_win(row: pd.Series) -> bool:
    st = str(row.get("status") or "").upper()
    if st == "WON":
        return True
    if st == "LOST":
        return False
    return bool(float(row.get("pnl_pct") or 0.0) > 0.0)


def _is_status_win_strict(row: pd.Series) -> bool:
    return str(row.get("status") or "").upper() == "WON"


def load() -> pd.DataFrame:
    raw = json.loads(DASHBOARD.read_text())
    picks = raw.get("picks", {}).get("recent_closed", [])
    df = pd.DataFrame(picks)

    def _col_num(name: str) -> pd.Series:
        if name in df.columns:
            return pd.to_numeric(df[name], errors="coerce")
        return pd.Series([np.nan] * len(df), index=df.index, dtype=float)

    pnl = _col_num("pnl_pct")
    realized = _col_num("realized_pnl_pct")
    unrealized = _col_num("unrealized_pnl_pct")
    df["pnl_pct"] = pnl.combine_first(realized).combine_first(unrealized).fillna(0.0)
    df["closed_at"] = pd.to_datetime(df.get("closed_at"), errors="coerce", utc=True)
    df["entry_time"] = pd.to_datetime(df.get("entry_time"), errors="coerce", utc=True)
    df["confidence"] = pd.to_numeric(df.get("confidence"), errors="coerce")
    df["score"] = pd.to_numeric(df.get("elite_score"), errors="coerce").fillna(0)
    ac = df.get("asset_class").where(df.get("asset_class").notna(), df.get("category"))
    df["asset_class"] = ac.astype(str).str.upper().replace({"NAN": "UNKNOWN", "": "UNKNOWN"}).fillna("UNKNOWN")
    # Normalize the "ETF"/"ETFS" and "BOND"/"BONDS" naming (dashboard uses singular)
    df["asset_class"] = df["asset_class"].replace({"ETFS": "ETF", "BONDS": "BOND", "COMMODITIES": "COMMODITY"})
    # Defensive: ensure signal_type column exists (fallback to direction or UNKNOWN).
    if "signal_type" not in df.columns:
        df["signal_type"] = df.get("direction", pd.Series(["UNKNOWN"] * len(df)))
    df["signal_type"] = df["signal_type"].astype(str).str.upper().replace({"NAN": "UNKNOWN", "": "UNKNOWN"}).fillna("UNKNOWN")
    if "strategy" not in df.columns:
        df["strategy"] = "UNKNOWN"
    if "symbol" not in df.columns:
        df["symbol"] = "UNKNOWN"
    df["strategy"] = df["strategy"].fillna("UNKNOWN").astype(str).replace({"": "UNKNOWN"})
    df["symbol"] = df["symbol"].fillna("UNKNOWN").astype(str).replace({"": "UNKNOWN"})
    df["status"] = df.get("status", pd.Series(["UNKNOWN"] * len(df))).fillna("UNKNOWN").astype(str)
    return df.sort_values("closed_at")


def claim_verification_table(df: pd.DataFrame) -> pd.DataFrame:
    """Compare status-based vs pnl-based WR on 20/100/200 windows.

    The user-facing dashboard often reports status-based wins, while quant
    diagnostics use realized pnl sign. Showing both resolves discrepancies.
    """
    ac_map = {
        "stocks": "EQUITY",
        "forex": "FOREX",
        "commodities": "COMMODITY",
        "bonds": "BOND",
        "etfs": "ETF",
    }
    windows = [20, 100, 200]
    rows: list[dict[str, Any]] = []
    for label, ac in ac_map.items():
        sub = df[df["asset_class"] == ac].sort_values("closed_at", ascending=False)
        for w in windows:
            win = sub.head(w)
            n = len(win)
            if n == 0:
                rows.append(
                    {
                        "asset_class": label,
                        "window": w,
                        "n_used": 0,
                        "strict_status_wr_pct": None,
                        "status_wr_pct": None,
                        "pnl_wr_pct": None,
                        "profit_factor": None,
                        "mean_pnl_pct": None,
                    }
                )
                continue
            strict_status_wr = 100.0 * float(win.apply(_is_status_win_strict, axis=1).mean())
            status_wr = 100.0 * float(win.apply(_is_status_win, axis=1).mean())
            pnl_wr = 100.0 * float((win["pnl_pct"] > 0).mean())
            rows.append(
                {
                    "asset_class": label,
                    "window": w,
                    "n_used": n,
                    "strict_status_wr_pct": round(strict_status_wr, 1),
                    "status_wr_pct": round(status_wr, 1),
                    "pnl_wr_pct": round(pnl_wr, 1),
                    "profit_factor": round(_pf(win["pnl_pct"]), 4) if np.isfinite(_pf(win["pnl_pct"])) else None,
                    "mean_pnl_pct": round(float(win["pnl_pct"].mean()), 4),
                }
            )
    return pd.DataFrame(rows)


def window_table(df: pd.DataFrame, ac: str) -> pd.DataFrame:
    sub = df[df["asset_class"] == ac].sort_values("closed_at", ascending=False)
    rows = []
    for w in WINDOWS:
        rows.append({"window": f"last_{w}", **_stats(sub.head(w))})
    rows.append({"window": f"all_{len(sub)}", **_stats(sub)})
    return pd.DataFrame(rows)


def strategy_breakdown(df: pd.DataFrame, ac: str, top_k: int = 10, min_n: int = 10) -> pd.DataFrame:
    sub = df[df["asset_class"] == ac]
    rows = []
    for strat, group in sub.groupby("strategy"):
        if len(group) < min_n:
            continue
        s = _stats(group)
        s["strategy"] = strat
        rows.append(s)
    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows)
    cols = ["strategy", "n", "wins", "losses", "wr", "pf", "mean_pnl_pct", "total_pnl_pct"]
    return out[cols].sort_values(["wr", "n"], ascending=[False, False]).head(top_k)


def symbol_breakdown(df: pd.DataFrame, ac: str, top_k: int = 10, min_n: int = 10) -> pd.DataFrame:
    sub = df[df["asset_class"] == ac]
    rows = []
    for sym, group in sub.groupby("symbol"):
        if len(group) < min_n:
            continue
        s = _stats(group)
        s["symbol"] = sym
        rows.append(s)
    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows)
    cols = ["symbol", "n", "wins", "losses", "wr", "pf", "mean_pnl_pct", "total_pnl_pct"]
    return out[cols].sort_values(["wr", "n"], ascending=[False, False]).head(top_k)


def direction_split(df: pd.DataFrame, ac: str) -> pd.DataFrame:
    sub = df[df["asset_class"] == ac]
    rows = []
    sig_col = sub["signal_type"] if "signal_type" in sub.columns else sub.get("direction", pd.Series(["UNKNOWN"] * len(sub)))
    sig_col = sig_col.astype(str).str.upper().fillna("UNKNOWN")
    for sig, group in sub.groupby(sig_col):
        s = _stats(group)
        s["signal_type"] = sig
        rows.append(s)
    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows)
    cols = ["signal_type", "n", "wins", "losses", "wr", "pf", "mean_pnl_pct", "total_pnl_pct"]
    return out[cols].sort_values("n", ascending=False)


def confidence_buckets(df: pd.DataFrame, ac: str) -> pd.DataFrame:
    sub = df[df["asset_class"] == ac].copy()
    bins = [0, 0.5, 0.6, 0.7, 0.8, 0.9, 1.01]
    labels = ["<0.50", "0.50-0.60", "0.60-0.70", "0.70-0.80", "0.80-0.90", "0.90-1.00"]
    sub["bucket"] = pd.cut(sub["confidence"].fillna(-1), bins=bins, labels=labels, include_lowest=True)
    rows = []
    for b, group in sub.groupby("bucket", observed=True):
        if len(group) < 10:
            continue
        s = _stats(group)
        s["bucket"] = str(b)
        rows.append(s)
    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows)
    cols = ["bucket", "n", "wins", "losses", "wr", "pf", "mean_pnl_pct"]
    return out[cols]


def find_edge_filters(df: pd.DataFrame, ac: str) -> list[dict]:
    """Try combinations of strategy/symbol/signal/confidence that pass the edge threshold."""
    sub = df[df["asset_class"] == ac].copy()
    if len(sub) < EDGE_MIN_N:
        return []
    sub["bucket"] = pd.cut(sub["confidence"].fillna(-1), bins=[0, 0.5, 0.6, 0.7, 0.8, 0.9, 1.01],
                          labels=["<0.50", "0.50-0.60", "0.60-0.70", "0.70-0.80", "0.80-0.90", "0.90-1.00"],
                          include_lowest=True)
    candidates = []
    # By strategy + signal_type
    for (strat, sig), group in sub.groupby(["strategy", sub["signal_type"].astype(str).str.upper()]):
        if len(group) < EDGE_MIN_N:
            continue
        s = _stats(group)
        if (s["wr"] or 0) >= EDGE_WR and (s["pf"] or 0) >= EDGE_PF:
            s["filter"] = f"strategy={strat} & direction={sig}"
            candidates.append(s)
    # By symbol
    for sym, group in sub.groupby("symbol"):
        if len(group) < EDGE_MIN_N:
            continue
        s = _stats(group)
        if (s["wr"] or 0) >= EDGE_WR and (s["pf"] or 0) >= EDGE_PF:
            s["filter"] = f"symbol={sym}"
            candidates.append(s)
    # By strategy + confidence bucket
    for (strat, bucket), group in sub.groupby(["strategy", "bucket"], observed=True):
        if len(group) < EDGE_MIN_N:
            continue
        s = _stats(group)
        if (s["wr"] or 0) >= EDGE_WR and (s["pf"] or 0) >= EDGE_PF:
            s["filter"] = f"strategy={strat} & confidence_bucket={bucket}"
            candidates.append(s)
    # Sort by PF then WR
    candidates.sort(key=lambda x: (-(x["pf"] or 0), -(x["wr"] or 0), -x["n"]))
    return candidates[:15]


def find_drag_filters(df: pd.DataFrame, ac: str) -> list[dict]:
    """Symmetric: find filters that drag WR way below baseline."""
    sub = df[df["asset_class"] == ac].copy()
    if len(sub) < EDGE_MIN_N:
        return []
    drags = []
    for (strat, sig), group in sub.groupby(["strategy", sub["signal_type"].astype(str).str.upper()]):
        if len(group) < EDGE_MIN_N:
            continue
        s = _stats(group)
        if (s["wr"] or 1) <= 0.25 and (s["pf"] or 1) <= 0.6:
            s["filter"] = f"strategy={strat} & direction={sig}"
            drags.append(s)
    for sym, group in sub.groupby("symbol"):
        if len(group) < EDGE_MIN_N:
            continue
        s = _stats(group)
        if (s["wr"] or 1) <= 0.25 and (s["pf"] or 1) <= 0.6:
            s["filter"] = f"symbol={sym}"
            drags.append(s)
    drags.sort(key=lambda x: ((x["wr"] or 0), (x["pf"] or 0)))
    return drags[:15]


def write_report(sections: dict[str, Any]) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Edge diagnosis by asset class — 2026-04-22\n"]
    lines.append("**Source:** `audit_dashboard/data/dashboard_data.json` (`picks.recent_closed`, 3,500 rows).")
    lines.append("**Method:** last-N window stats + strategy/symbol/direction/confidence-bucket drill-downs.")
    lines.append(f"**Edge definition:** WR ≥ {EDGE_WR*100:.0f}% AND PF ≥ {EDGE_PF:.2f} on n ≥ {EDGE_MIN_N}.")
    lines.append("**Drag definition:** WR ≤ 25% AND PF ≤ 0.6 on n ≥ 30 (candidates to kill/invert).\n")
    for title, body in sections.items():
        lines.append(f"\n## {title}\n")
        if isinstance(body, pd.DataFrame):
            if body.empty:
                lines.append("_empty_\n")
                continue
            try:
                lines.append(body.to_markdown(index=False))
            except ImportError:
                lines.append("```\n" + body.to_string(index=False) + "\n```")
        elif isinstance(body, list):
            if not body:
                lines.append("_none found_\n")
                continue
            for item in body:
                lines.append(f"- `{item.get('filter','?')}` — n={item.get('n','?')}, WR={item.get('wr','?')}, PF={item.get('pf','?')}, mean_pnl={item.get('mean_pnl_pct','?')}")
        elif isinstance(body, dict):
            lines.append("```json\n" + json.dumps(body, indent=2, default=str) + "\n```")
        else:
            lines.append(str(body))
        lines.append("")
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    df = load()
    print(f"Loaded {len(df):,} closed picks")
    print(f"Asset classes:", dict(df["asset_class"].value_counts()))

    sections: dict[str, Any] = {}

    overall = {
        "total": _stats(df),
    }
    for w in WINDOWS:
        overall[f"last_{w}_overall"] = _stats(df.sort_values("closed_at", ascending=False).head(w))
    sections["Overall (system-wide)"] = overall
    sections["Claim verification (status-based vs pnl-based WR)"] = claim_verification_table(df)

    asset_classes = sorted(df["asset_class"].unique())
    for ac in asset_classes:
        ac_sub = df[df["asset_class"] == ac]
        print(f"\n=== {ac} (n={len(ac_sub)}) ===")

        win_df = window_table(df, ac)
        print(win_df.to_string(index=False))

        sections[f"{ac} — Window table (last-N)"] = win_df
        sections[f"{ac} — Top strategies (by WR, min n=10, top 10)"] = strategy_breakdown(df, ac)
        sections[f"{ac} — Top symbols (by WR, min n=10, top 10)"] = symbol_breakdown(df, ac)
        sections[f"{ac} — Direction split"] = direction_split(df, ac)
        sections[f"{ac} — Confidence buckets"] = confidence_buckets(df, ac)

        edges = find_edge_filters(df, ac)
        drags = find_drag_filters(df, ac)
        sections[f"{ac} — Edge candidates (WR≥{EDGE_WR:.2f} AND PF≥{EDGE_PF:.2f}, n≥{EDGE_MIN_N})"] = edges
        sections[f"{ac} — Drag candidates (WR≤0.25 AND PF≤0.60, n≥{EDGE_MIN_N})"] = drags

    write_report(sections)
    print(f"\nReport -> {REPORT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
