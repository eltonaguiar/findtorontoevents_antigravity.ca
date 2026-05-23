#!/usr/bin/env python3
"""
Practical v3 audit pipeline for crypto picks.

Core design:
- Uses the existing composite Score as a primary feature.
- Adds system-level Bayesian priors (win rate + PnL expectancy).
- Trains separate LONG and SHORT models.
- Applies post-hoc probability calibration (isotonic/sigmoid).
- Selects per-direction gate thresholds with train sweep and holdout sanity checks.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import pathlib
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


TRUST_MAP: Dict[str, int] = {
    "DEMOTED": 0,
    "WATCH": 1,
    "SANDBOX": 2,
    "UNPROVEN": 3,
    "PROBATION": 4,
    "RELIABLE": 5,
    "PROVEN": 6,
}

GRADE_MAP: Dict[str, int] = {
    "F": 0,
    "D": 1,
    "C": 2,
    "B": 3,
    "A": 4,
}

SCORE_PATTERNS: Dict[str, str] = {
    "signal_score": r"Signal:\s*([-\d\.]+)/100",
    "consensus_score": r"Consensus:\s*([-\d\.]+)/100",
    "noconflict_score": r"NoConflict:\s*([-\d\.]+)/100",
    "trust_mult": r"Trust:\s*\w+\s*([-\d\.]+)x",
    "forward_score": r"Forward:\s*([-\d\.]+)/100",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Leak-free crypto pick audit v3")
    parser.add_argument("--closed", type=str, default="", help="Path to closed picks CSV")
    parser.add_argument("--active", type=str, default="", help="Path to active picks CSV")
    parser.add_argument("--outdir", type=str, default="reports", help="Output directory")
    parser.add_argument("--min-trust-tier", type=int, default=4, help="Trusted cohort min trust tier ordinal")
    parser.add_argument("--holdout-frac", type=float, default=0.2, help="Time holdout fraction")
    parser.add_argument("--min-holdout", type=int, default=50, help="Minimum holdout rows when available")
    parser.add_argument("--prior-shrink", type=float, default=30.0, help="Bayesian prior shrinkage strength")
    parser.add_argument("--cv-splits", type=int, default=5, help="Maximum CV splits")
    parser.add_argument("--calibration", choices=["isotonic", "sigmoid"], default="sigmoid", help="Calibration method")
    parser.add_argument("--allow-forward-score", action="store_true", help="Allow forward_score as feature")
    parser.add_argument("--allow-forward-wr", action="store_true", help="Allow Forward WR as feature")
    parser.add_argument("--gate-min", type=float, default=0.45, help="Gate sweep min threshold")
    parser.add_argument("--gate-max", type=float, default=0.85, help="Gate sweep max threshold")
    parser.add_argument("--gate-step", type=float, default=0.01, help="Gate sweep step")
    parser.add_argument("--min-coverage-abs", type=int, default=25, help="Min rows for threshold candidate")
    parser.add_argument("--min-coverage-frac", type=float, default=0.08, help="Min threshold coverage as fraction of direction train rows")
    parser.add_argument("--cost-pct", type=float, default=0.2, help="Roundtrip cost assumption in pct points")
    parser.add_argument("--exclude-short-warnings", action="store_true", default=True, help="Block short-in-bull warnings at gate stage")
    parser.add_argument(
        "--hard-block-systems",
        type=str,
        default="alpha_engine_fast",
        help="Comma-separated systems to block (default: alpha_engine_fast)",
    )
    parser.add_argument(
        "--hard-long-min-score",
        type=float,
        default=20.0,
        help="Minimum Score_num for LONG hard gate (default 20.0)",
    )
    parser.add_argument(
        "--hard-allow-shorts",
        action="store_true",
        default=False,
        help="Allow SHORTs through hard gate (default false)",
    )
    parser.add_argument(
        "--combine-with-model-gate",
        action="store_true",
        default=False,
        help="Require both model gate and hard gate (default false: hard gate only)",
    )
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO")
    return parser.parse_args()


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def parse_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str).str.replace("%", "", regex=False).str.replace(",", "", regex=False).str.strip(),
        errors="coerce",
    )


def safe_col(df: pd.DataFrame, col: str, default: str = "") -> pd.Series:
    if col in df.columns:
        return df[col]
    return pd.Series([default] * len(df), index=df.index)


def find_latest_file(pattern: str, base_dir: pathlib.Path) -> pathlib.Path:
    matches = list(base_dir.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"No files matched pattern: {pattern}")
    return max(matches, key=lambda p: p.stat().st_mtime)


def prepare_frame(df: pd.DataFrame, is_closed: bool) -> pd.DataFrame:
    out = df.copy()
    out["PnL_num"] = parse_numeric(safe_col(out, "PnL%", ""))
    out["Score_num"] = parse_numeric(safe_col(out, "Score", ""))
    out["Forward_WR_num"] = parse_numeric(safe_col(out, "Forward WR", ""))
    out["confluence_num"] = parse_numeric(safe_col(out, "Confluence Count", ""))

    direction = safe_col(out, "Direction", "").astype(str).str.upper()
    reason = safe_col(out, "Direction Reason", "").astype(str)
    out["direction_norm"] = direction
    out["direction_short"] = (direction == "SHORT").astype(int)
    out["short_in_bull_warning"] = reason.str.contains(
        "WARNING: Shorting in BULLISH regime", na=False
    ).astype(int)

    out["trust_tier_ord"] = safe_col(out, "Trust Tier", "").astype(str).str.upper().map(TRUST_MAP).fillna(0).astype(int)
    out["grade_ord"] = safe_col(out, "Grade", "").astype(str).str.upper().map(GRADE_MAP).fillna(0).astype(int)

    text = safe_col(out, "Score Breakdown (English)", "").astype(str)
    for col, pattern in SCORE_PATTERNS.items():
        out[col] = parse_numeric(text.str.extract(pattern, expand=False))

    out["System"] = safe_col(out, "System", "").astype(str)
    out["Strategy"] = safe_col(out, "Strategy", "").astype(str)

    time_col = "Entry Time" if is_closed and "Entry Time" in out.columns else "Picked At"
    out["event_time"] = pd.to_datetime(safe_col(out, time_col, ""), errors="coerce", utc=True)
    out["win"] = (out["PnL_num"] > 0).astype(int)
    return out


def dedupe_closed(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, int]]:
    key_cols = [c for c in ["Symbol", "Direction", "System", "Strategy", "Entry Time"] if c in df.columns]
    if len(key_cols) < 4:
        raise ValueError("Closed CSV missing required dedupe identity columns.")
    before = len(df)
    counts = df.groupby(key_cols, dropna=False).size().rename("duplicate_count").reset_index()
    merged = df.merge(counts, on=key_cols, how="left")
    deduped = merged.drop_duplicates(subset=key_cols, keep="last").copy()
    stats = {
        "closed_rows_before_dedupe": before,
        "closed_rows_after_dedupe": len(deduped),
        "duplicate_rows_removed": before - len(deduped),
        "duplicate_keys_with_repeats": int((counts["duplicate_count"] > 1).sum()),
    }
    return deduped, stats


def make_trusted(df_closed: pd.DataFrame, min_trust_tier: int) -> pd.DataFrame:
    if "Exit Reason" not in df_closed.columns:
        raise ValueError("Closed CSV requires Exit Reason column")
    trusted = df_closed.copy()
    trusted = trusted[trusted["Exit Reason"].notna()]
    trusted = trusted[trusted["PnL_num"].notna()]
    trusted = trusted[trusted["trust_tier_ord"] >= min_trust_tier]
    trusted = trusted[trusted["direction_norm"].isin(["LONG", "SHORT"])]
    return trusted.copy()


def split_train_holdout(df: pd.DataFrame, holdout_frac: float, min_holdout: int) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if df.empty:
        return df.copy(), df.copy()
    ordered = df.sort_values(["event_time", "Symbol"], ascending=[True, True], na_position="first").copy()
    n = len(ordered)
    holdout_n = max(min_holdout, int(math.ceil(holdout_frac * n)))
    holdout_n = min(holdout_n, max(0, n - 60))
    if holdout_n <= 0:
        return ordered.copy(), ordered.iloc[0:0].copy()
    return ordered.iloc[:-holdout_n].copy(), ordered.iloc[-holdout_n:].copy()


def compute_system_priors(train_dir: pd.DataFrame, shrink: float) -> Dict[str, Any]:
    if train_dir.empty:
        return {"wr_map": {}, "pnl_map": {}, "global_wr": 0.5, "global_pnl": 0.0}
    global_wr = float(train_dir["win"].mean())
    global_pnl = float(train_dir["PnL_num"].mean())
    grp = (
        train_dir.groupby("System", dropna=False)
        .agg(n=("win", "count"), wins=("win", "sum"), mean_pnl=("PnL_num", "mean"))
        .reset_index()
    )
    grp["prior_wr"] = (grp["wins"] + shrink * global_wr) / (grp["n"] + shrink)
    grp["prior_pnl"] = (grp["mean_pnl"] * grp["n"] + shrink * global_pnl) / (grp["n"] + shrink)
    return {
        "wr_map": dict(zip(grp["System"], grp["prior_wr"])),
        "pnl_map": dict(zip(grp["System"], grp["prior_pnl"])),
        "global_wr": global_wr,
        "global_pnl": global_pnl,
    }


def apply_system_priors(df: pd.DataFrame, priors: Dict[str, Any]) -> pd.DataFrame:
    out = df.copy()
    out["system_prior_wr"] = out["System"].map(priors["wr_map"]).fillna(priors["global_wr"])
    out["system_prior_pnl"] = out["System"].map(priors["pnl_map"]).fillna(priors["global_pnl"])
    return out


def build_features(args: argparse.Namespace) -> List[str]:
    features = [
        "Score_num",
        "signal_score",
        "consensus_score",
        "noconflict_score",
        "confluence_num",
        "trust_tier_ord",
        "grade_ord",
        "trust_mult",
        "system_prior_wr",
        "system_prior_pnl",
    ]
    if args.allow_forward_score:
        features.append("forward_score")
    if args.allow_forward_wr:
        features.append("Forward_WR_num")
    return features


def build_base_model() -> Pipeline:
    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(max_iter=5000, C=0.4, class_weight="balanced", solver="lbfgs")),
        ]
    )


def fit_calibrator(base_probs: np.ndarray, y: np.ndarray, method: str) -> Dict[str, Any]:
    if method == "isotonic":
        if len(np.unique(base_probs)) >= 10:
            iso = IsotonicRegression(out_of_bounds="clip")
            iso.fit(base_probs, y)
            return {"type": "isotonic", "model": iso}
    # sigmoid fallback or explicit sigmoid
    lr = LogisticRegression(max_iter=2000, solver="lbfgs")
    lr.fit(base_probs.reshape(-1, 1), y)
    return {"type": "sigmoid", "model": lr}


def apply_calibrator(base_probs: np.ndarray, calibrator: Dict[str, Any]) -> np.ndarray:
    if calibrator["type"] == "isotonic":
        return calibrator["model"].transform(base_probs)
    return calibrator["model"].predict_proba(base_probs.reshape(-1, 1))[:, 1]


def choose_cv_splits(y: pd.Series, max_splits: int) -> int:
    min_class = int(y.value_counts().min())
    if min_class < 2:
        raise ValueError("Need at least two rows in each class for CV.")
    return max(2, min(max_splits, min_class))


def sweep_gate(
    df_scored: pd.DataFrame,
    gate_min: float,
    gate_max: float,
    gate_step: float,
    min_coverage: int,
    cost_pct: float,
    exclude_short_warnings: bool,
) -> pd.DataFrame:
    rows: List[Dict[str, float]] = []
    for t in np.arange(gate_min, gate_max + 1e-9, gate_step):
        cand = df_scored[df_scored["entry_score"] >= t]
        if exclude_short_warnings:
            cand = cand[~cand["short_in_bull_warning"].astype(bool)]
        n = len(cand)
        if n < min_coverage:
            continue
        mean_pnl = float(cand["PnL_num"].mean())
        rows.append(
            {
                "threshold": float(round(t, 4)),
                "trades": int(n),
                "mean_pnl": mean_pnl,
                "net_mean_pnl": mean_pnl - cost_pct,
                "win_rate": float((cand["PnL_num"] > 0).mean()),
            }
        )
    return pd.DataFrame(rows)


def pick_threshold(train_sweep: pd.DataFrame, holdout_sweep: pd.DataFrame) -> Tuple[float | None, float | None]:
    if train_sweep.empty:
        return None, None

    train_best = float(
        train_sweep.sort_values(["net_mean_pnl", "win_rate", "trades"], ascending=[False, False, False]).iloc[0]["threshold"]
    )
    final_best = train_best

    # Holdout sanity: if train best has no holdout support, fallback to jointly strong threshold.
    if not holdout_sweep.empty and train_best not in set(holdout_sweep["threshold"].tolist()):
        merged = train_sweep.merge(holdout_sweep, on="threshold", suffixes=("_train", "_holdout"))
        if not merged.empty:
            final_best = float(
                merged.sort_values(
                    ["net_mean_pnl_holdout", "net_mean_pnl_train", "trades_holdout"],
                    ascending=[False, False, False],
                ).iloc[0]["threshold"]
            )
        else:
            final_best = None

    return train_best, final_best


def gate_stats(df_scored: pd.DataFrame, threshold: float | None, cost_pct: float, exclude_short_warnings: bool) -> Dict[str, float]:
    if threshold is None or df_scored.empty:
        return {"trades": 0, "mean_pnl": float("nan"), "net_mean_pnl": float("nan"), "win_rate": float("nan")}
    cand = df_scored[df_scored["entry_score"] >= threshold]
    if exclude_short_warnings:
        cand = cand[~cand["short_in_bull_warning"].astype(bool)]
    if cand.empty:
        return {"trades": 0, "mean_pnl": float("nan"), "net_mean_pnl": float("nan"), "win_rate": float("nan")}
    mean_pnl = float(cand["PnL_num"].mean())
    return {
        "trades": int(len(cand)),
        "mean_pnl": mean_pnl,
        "net_mean_pnl": mean_pnl - cost_pct,
        "win_rate": float((cand["PnL_num"] > 0).mean()),
    }


def write_report(
    path: pathlib.Path,
    args: argparse.Namespace,
    closed_path: pathlib.Path,
    active_path: pathlib.Path,
    dedupe_stats: Dict[str, int],
    trusted_rows: int,
    train_rows: int,
    holdout_rows: int,
    features: List[str],
    direction_meta: Dict[str, Dict[str, Any]],
    active_scored: pd.DataFrame,
) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    with path.open("w", encoding="utf-8") as f:
        f.write("# Crypto Audit v3 Report\n\n")
        f.write(f"- run_time: `{now}`\n")
        f.write(f"- closed_csv: `{closed_path}`\n")
        f.write(f"- active_csv: `{active_path}`\n")
        f.write(f"- features: `{features}`\n")
        f.write(f"- calibration: `{args.calibration}`\n\n")
        f.write("## Hard Gate Config\n\n")
        f.write(f"- hard_block_systems: `{args.hard_block_systems}`\n")
        f.write(f"- hard_long_min_score: `{args.hard_long_min_score}`\n")
        f.write(f"- hard_allow_shorts: `{args.hard_allow_shorts}`\n")
        f.write(f"- combine_with_model_gate: `{args.combine_with_model_gate}`\n\n")

        f.write("## Data Integrity\n\n")
        for k, v in dedupe_stats.items():
            f.write(f"- {k}: `{v}`\n")
        f.write(f"- trusted_rows: `{trusted_rows}`\n")
        f.write(f"- train_rows: `{train_rows}`\n")
        f.write(f"- holdout_rows: `{holdout_rows}`\n\n")

        f.write("## Direction Model Summary\n\n")
        f.write("| direction | train_n | holdout_n | oof_auc | holdout_auc | train_threshold | final_threshold | train_gate_trades | holdout_gate_trades |\n")
        f.write("|---|---:|---:|---:|---:|---:|---:|---:|---:|\n")
        for direction in ["LONG", "SHORT"]:
            meta = direction_meta.get(direction, {})
            f.write(
                f"| {direction} | {meta.get('train_n', 0)} | {meta.get('holdout_n', 0)} | "
                f"{meta.get('oof_auc', float('nan')):.4f} | {meta.get('holdout_auc', float('nan')):.4f} | "
                f"{meta.get('train_threshold', float('nan'))} | {meta.get('final_threshold', float('nan'))} | "
                f"{meta.get('train_gate_trades', 0)} | {meta.get('holdout_gate_trades', 0)} |\n"
            )
        f.write("\n")

        f.write("## Active Gate Summary\n\n")
        f.write(f"- active_rows_total: `{len(active_scored)}`\n")
        f.write(f"- active_model_gate_pass_rows: `{int(active_scored['model_gate_pass_v3'].sum())}`\n")
        f.write(f"- active_hard_gate_pass_rows: `{int(active_scored['hard_gate_pass_v3'].sum())}`\n")
        f.write(f"- active_final_gate_pass_rows: `{int(active_scored['gate_pass_v3'].sum())}`\n")
        f.write(
            f"- active_final_gate_pass_pct: `{(active_scored['gate_pass_v3'].mean() if len(active_scored) else 0):.2%}`\n\n"
        )
        by_dir = (
            active_scored.groupby("direction_norm", dropna=False)["gate_pass_v3"]
            .agg(["count", "sum"])
            .rename(columns={"count": "rows", "sum": "passes"})
            .reset_index()
        )
        f.write("| direction | rows | passes | pass_rate |\n")
        f.write("|---|---:|---:|---:|\n")
        for _, row in by_dir.iterrows():
            rate = (row["passes"] / row["rows"]) if row["rows"] else 0.0
            f.write(f"| {row['direction_norm']} | {int(row['rows'])} | {int(row['passes'])} | {rate:.2%} |\n")
        f.write("\n")


def main() -> int:
    args = parse_args()
    setup_logging(args.log_level)
    base_dir = pathlib.Path(".")

    try:
        closed_path = pathlib.Path(args.closed) if args.closed else find_latest_file("antigravity_closed_picks_*.csv", base_dir)
        active_path = pathlib.Path(args.active) if args.active else find_latest_file("antigravity_active_picks_*.csv", base_dir)
        outdir = pathlib.Path(args.outdir)
        outdir.mkdir(parents=True, exist_ok=True)

        logging.info("Using closed CSV: %s", closed_path)
        logging.info("Using active CSV: %s", active_path)

        closed_raw = pd.read_csv(closed_path)
        active_raw = pd.read_csv(active_path)

        closed_pre = prepare_frame(closed_raw, is_closed=True)
        active_pre = prepare_frame(active_raw, is_closed=False)
        closed_dedup, dedupe_stats = dedupe_closed(closed_pre)
        trusted = make_trusted(closed_dedup, args.min_trust_tier)

        if trusted.empty:
            raise ValueError("Trusted cohort is empty after filters.")

        train_all, holdout_all = split_train_holdout(trusted, args.holdout_frac, args.min_holdout)
        features = build_features(args)

        direction_meta: Dict[str, Dict[str, Any]] = {}
        train_sweeps: List[pd.DataFrame] = []
        holdout_sweeps: List[pd.DataFrame] = []
        direction_models: Dict[str, Dict[str, Any]] = {}

        # Prepare scoring containers
        closed_scored = closed_dedup.copy()
        active_scored = active_pre.copy()
        closed_scored["entry_score_v3"] = np.nan
        closed_scored["gate_threshold_v3"] = np.nan
        closed_scored["model_gate_pass_v3"] = False
        closed_scored["hard_gate_pass_v3"] = False
        closed_scored["gate_pass_v3"] = False
        active_scored["entry_score_v3"] = np.nan
        active_scored["gate_threshold_v3"] = np.nan
        active_scored["model_gate_pass_v3"] = False
        active_scored["hard_gate_pass_v3"] = False
        active_scored["gate_pass_v3"] = False
        active_scored["model_note_v3"] = ""

        for direction in ["LONG", "SHORT"]:
            train_dir = train_all[train_all["direction_norm"] == direction].copy()
            holdout_dir = holdout_all[holdout_all["direction_norm"] == direction].copy()

            meta: Dict[str, Any] = {
                "train_n": int(len(train_dir)),
                "holdout_n": int(len(holdout_dir)),
                "oof_auc": float("nan"),
                "holdout_auc": float("nan"),
                "train_threshold": float("nan"),
                "final_threshold": float("nan"),
                "train_gate_trades": 0,
                "holdout_gate_trades": 0,
            }

            if len(train_dir) < 60 or train_dir["win"].nunique() < 2:
                # Fallback: constant model from direction baseline.
                base_prob = float(train_dir["win"].mean()) if len(train_dir) else 0.5
                direction_models[direction] = {
                    "type": "constant",
                    "prob": base_prob,
                    "features": features,
                    "priors": {"wr_map": {}, "pnl_map": {}, "global_wr": 0.5, "global_pnl": 0.0},
                    "threshold": None,
                }
                meta["model_type"] = "constant"
                direction_meta[direction] = meta
                continue

            priors = compute_system_priors(train_dir, args.prior_shrink)
            train_dir = apply_system_priors(train_dir, priors)
            holdout_dir = apply_system_priors(holdout_dir, priors)

            model = build_base_model()
            y_train = train_dir["win"].astype(int)
            n_splits = choose_cv_splits(y_train, args.cv_splits)
            cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

            X_train = train_dir[features]
            oof_base = cross_val_predict(model, X_train, y_train, cv=cv, method="predict_proba")[:, 1]
            calibrator = fit_calibrator(oof_base, y_train.values, args.calibration)
            oof_probs = apply_calibrator(oof_base, calibrator)
            if y_train.nunique() > 1:
                meta["oof_auc"] = float(roc_auc_score(y_train, oof_probs))

            train_scored_dir = train_dir.copy()
            train_scored_dir["entry_score"] = oof_probs

            model.fit(X_train, y_train)

            holdout_scored_dir = holdout_dir.copy()
            if not holdout_dir.empty:
                holdout_base = model.predict_proba(holdout_dir[features])[:, 1]
                holdout_probs = apply_calibrator(holdout_base, calibrator)
                holdout_scored_dir["entry_score"] = holdout_probs
                if holdout_dir["win"].nunique() > 1:
                    meta["holdout_auc"] = float(roc_auc_score(holdout_dir["win"], holdout_probs))
            else:
                holdout_scored_dir["entry_score"] = []

            min_cov_train = max(args.min_coverage_abs, int(math.ceil(args.min_coverage_frac * len(train_scored_dir))))
            min_cov_holdout = (
                max(5, int(math.ceil(0.05 * len(holdout_scored_dir)))) if len(holdout_scored_dir) > 0 else 0
            )
            train_sweep = sweep_gate(
                train_scored_dir,
                gate_min=args.gate_min,
                gate_max=args.gate_max,
                gate_step=args.gate_step,
                min_coverage=min_cov_train,
                cost_pct=args.cost_pct,
                exclude_short_warnings=args.exclude_short_warnings,
            )
            holdout_sweep = (
                sweep_gate(
                    holdout_scored_dir,
                    gate_min=args.gate_min,
                    gate_max=args.gate_max,
                    gate_step=args.gate_step,
                    min_coverage=min_cov_holdout,
                    cost_pct=args.cost_pct,
                    exclude_short_warnings=args.exclude_short_warnings,
                )
                if len(holdout_scored_dir) > 0
                else pd.DataFrame()
            )
            train_thr, final_thr = pick_threshold(train_sweep, holdout_sweep)
            train_stats = gate_stats(
                train_scored_dir, final_thr, cost_pct=args.cost_pct, exclude_short_warnings=args.exclude_short_warnings
            )
            holdout_stats = gate_stats(
                holdout_scored_dir, final_thr, cost_pct=args.cost_pct, exclude_short_warnings=args.exclude_short_warnings
            )

            meta["train_threshold"] = train_thr
            meta["final_threshold"] = final_thr
            meta["train_gate_trades"] = int(train_stats["trades"])
            meta["holdout_gate_trades"] = int(holdout_stats["trades"])
            meta["model_type"] = "logistic_calibrated"

            if not train_sweep.empty:
                ts = train_sweep.copy()
                ts["direction"] = direction
                train_sweeps.append(ts)
            if not holdout_sweep.empty:
                hs = holdout_sweep.copy()
                hs["direction"] = direction
                holdout_sweeps.append(hs)

            direction_models[direction] = {
                "type": "logistic_calibrated",
                "base_model": model,
                "calibrator": calibrator,
                "features": features,
                "priors": priors,
                "threshold": final_thr,
            }
            direction_meta[direction] = meta

        # Score full closed and active sets per direction.
        for direction in ["LONG", "SHORT"]:
            model_info = direction_models.get(direction)
            if model_info is None:
                continue

            closed_mask = closed_scored["direction_norm"] == direction
            active_mask = active_scored["direction_norm"] == direction

            if model_info["type"] == "constant":
                prob = float(model_info["prob"])
                closed_scored.loc[closed_mask, "entry_score_v3"] = prob
                active_scored.loc[active_mask, "entry_score_v3"] = prob
                active_scored.loc[active_mask, "model_note_v3"] = "constant"
                continue

            priors = model_info["priors"]
            threshold = model_info["threshold"]
            base_model = model_info["base_model"]
            calibrator = model_info["calibrator"]
            feats = model_info["features"]

            closed_dir = apply_system_priors(closed_scored.loc[closed_mask], priors)
            active_dir = apply_system_priors(active_scored.loc[active_mask], priors)

            closed_base = base_model.predict_proba(closed_dir[feats])[:, 1]
            active_base = base_model.predict_proba(active_dir[feats])[:, 1]
            closed_prob = apply_calibrator(closed_base, calibrator)
            active_prob = apply_calibrator(active_base, calibrator)

            closed_scored.loc[closed_mask, "entry_score_v3"] = closed_prob
            active_scored.loc[active_mask, "entry_score_v3"] = active_prob
            closed_scored.loc[closed_mask, "gate_threshold_v3"] = threshold
            active_scored.loc[active_mask, "gate_threshold_v3"] = threshold
            active_scored.loc[active_mask, "model_note_v3"] = "logistic_calibrated"

            if threshold is not None:
                active_scored.loc[active_mask, "model_gate_pass_v3"] = (
                    active_scored.loc[active_mask, "entry_score_v3"] >= threshold
                )
                closed_scored.loc[closed_mask, "model_gate_pass_v3"] = (
                    closed_scored.loc[closed_mask, "entry_score_v3"] >= threshold
                )

        if args.exclude_short_warnings:
            active_scored.loc[active_scored["short_in_bull_warning"].astype(bool), "model_gate_pass_v3"] = False
            closed_scored.loc[closed_scored["short_in_bull_warning"].astype(bool), "model_gate_pass_v3"] = False

        # Apply practical hard gates requested from empirical review.
        blocked_systems = {
            s.strip() for s in args.hard_block_systems.split(",") if s.strip()
        }
        if blocked_systems:
            active_blocked = active_scored["System"].isin(blocked_systems)
            closed_blocked = closed_scored["System"].isin(blocked_systems)
        else:
            active_blocked = pd.Series(False, index=active_scored.index)
            closed_blocked = pd.Series(False, index=closed_scored.index)

        active_long_ok = (
            (active_scored["direction_norm"] == "LONG")
            & (active_scored["Score_num"] >= args.hard_long_min_score)
        )
        closed_long_ok = (
            (closed_scored["direction_norm"] == "LONG")
            & (closed_scored["Score_num"] >= args.hard_long_min_score)
        )

        if args.hard_allow_shorts:
            active_short_ok = active_scored["direction_norm"] == "SHORT"
            closed_short_ok = closed_scored["direction_norm"] == "SHORT"
            if args.exclude_short_warnings:
                active_short_ok &= ~active_scored["short_in_bull_warning"].astype(bool)
                closed_short_ok &= ~closed_scored["short_in_bull_warning"].astype(bool)
        else:
            active_short_ok = pd.Series(False, index=active_scored.index)
            closed_short_ok = pd.Series(False, index=closed_scored.index)

        active_scored["hard_gate_pass_v3"] = (
            (~active_blocked) & (active_long_ok | active_short_ok)
        )
        closed_scored["hard_gate_pass_v3"] = (
            (~closed_blocked) & (closed_long_ok | closed_short_ok)
        )

        if args.combine_with_model_gate:
            active_scored["gate_pass_v3"] = (
                active_scored["hard_gate_pass_v3"] & active_scored["model_gate_pass_v3"]
            )
            closed_scored["gate_pass_v3"] = (
                closed_scored["hard_gate_pass_v3"] & closed_scored["model_gate_pass_v3"]
            )
        else:
            active_scored["gate_pass_v3"] = active_scored["hard_gate_pass_v3"]
            closed_scored["gate_pass_v3"] = closed_scored["hard_gate_pass_v3"]

        train_sweep_df = pd.concat(train_sweeps, ignore_index=True) if train_sweeps else pd.DataFrame()
        holdout_sweep_df = pd.concat(holdout_sweeps, ignore_index=True) if holdout_sweeps else pd.DataFrame()

        # Persist artifacts
        closed_out = outdir / "cleaned_closed.csv"
        active_out = outdir / "active_scored.csv"
        train_sweep_out = outdir / "gate_sweep_train.csv"
        holdout_sweep_out = outdir / "gate_sweep_holdout.csv"
        report_out = outdir / "audit_report.md"
        model_out = outdir / "entry_model_v3.joblib"
        meta_out = outdir / "model_metadata.json"

        closed_scored.to_csv(closed_out, index=False)
        active_scored.to_csv(active_out, index=False)
        train_sweep_df.to_csv(train_sweep_out, index=False)
        holdout_sweep_df.to_csv(holdout_sweep_out, index=False)

        metadata = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "closed_csv": str(closed_path),
            "active_csv": str(active_path),
            "features": features,
            "direction_meta": direction_meta,
            "hard_gate": {
                "blocked_systems": sorted(blocked_systems),
                "long_min_score": args.hard_long_min_score,
                "allow_shorts": args.hard_allow_shorts,
                "combine_with_model_gate": args.combine_with_model_gate,
            },
            "args": vars(args),
            "dedupe_stats": dedupe_stats,
            "trusted_rows": int(len(trusted)),
            "train_rows": int(len(train_all)),
            "holdout_rows": int(len(holdout_all)),
        }
        joblib.dump({"direction_models": direction_models, "metadata": metadata}, model_out)
        with meta_out.open("w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        write_report(
            path=report_out,
            args=args,
            closed_path=closed_path,
            active_path=active_path,
            dedupe_stats=dedupe_stats,
            trusted_rows=len(trusted),
            train_rows=len(train_all),
            holdout_rows=len(holdout_all),
            features=features,
            direction_meta=direction_meta,
            active_scored=active_scored,
        )

        logging.info("Audit complete.")
        logging.info("Report: %s", report_out)
        logging.info("Active scored: %s", active_out)
        logging.info("LONG threshold: %s", direction_meta.get("LONG", {}).get("final_threshold"))
        logging.info("SHORT threshold: %s", direction_meta.get("SHORT", {}).get("final_threshold"))
        logging.info("Hard gate blocked systems: %s", sorted(blocked_systems))
        logging.info(
            "Active passes | model=%d hard=%d final=%d",
            int(active_scored["model_gate_pass_v3"].sum()),
            int(active_scored["hard_gate_pass_v3"].sum()),
            int(active_scored["gate_pass_v3"].sum()),
        )
        return 0

    except Exception as exc:
        logging.exception("v3 audit failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())

