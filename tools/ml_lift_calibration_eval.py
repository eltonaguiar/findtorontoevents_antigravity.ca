#!/usr/bin/env python3
"""
Offline lift and calibration metrics for closed picks.

Compares baselines (elite_score, confidence, ml composite) to optional
ML Gatekeeper ensemble probabilities. Does not run scanners or heavy engines.

Usage (from repo root):
  python tools/ml_lift_calibration_eval.py
  python tools/ml_lift_calibration_eval.py --picks alpha_engine/data/closed_picks.json
  python tools/ml_lift_calibration_eval.py --dashboard audit_dashboard/data/dashboard_data.json
  python tools/ml_lift_calibration_eval.py --gatekeeper-model ml_gatekeeper/models/gatekeeper_model.joblib
  python tools/ml_lift_calibration_eval.py --compare-priors
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _f(v: Any) -> float:
    if v is None:
        return 0.0
    try:
        x = float(v)
        return x if math.isfinite(x) else 0.0
    except (TypeError, ValueError):
        return 0.0


def load_closed_array(path: Path) -> list[dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict) and "picks" in raw:
        inner = raw["picks"]
        if isinstance(inner, list):
            return inner
        closed = inner.get("recent_closed") or inner.get("closed")
        if isinstance(closed, list):
            return closed
    return []


def binary_label(pick: dict) -> int | None:
    pnl = pick.get("pnl_pct")
    if pnl is None:
        return None
    pnl = _f(pnl)
    if pnl == 0:
        return None
    return 1 if pnl > 0 else 0


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 3 or n != len(ys):
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    denx = sum((x - mx) ** 2 for x in xs) ** 0.5
    deny = sum((y - my) ** 2 for y in ys) ** 0.5
    if denx == 0 or deny == 0:
        return None
    return num / (denx * deny)


def _metrics(y_true: list[int], y_score: list[float]) -> dict[str, Any]:
    out: dict[str, Any] = {"n": len(y_true)}
    try:
        import numpy as np
        from sklearn.metrics import brier_score_loss, roc_auc_score

        y = np.array(y_true, dtype=np.int32)
        s = np.nan_to_num(np.array(y_score, dtype=np.float64), nan=0.0, posinf=1.0, neginf=0.0)
        s = np.clip(s, 0.0, 1.0)
        if len(np.unique(y)) < 2:
            out["note"] = "single_class_skip"
            return out
        if float(np.nanstd(s)) == 0.0:
            out["note"] = "constant_score_skip"
            out["base_rate"] = float(y.mean())
            return out
        auc = float(roc_auc_score(y, s))
        bri = float(brier_score_loss(y, s))
        out["roc_auc"] = auc
        out["brier"] = bri
        out["base_rate"] = float(y.mean())
    except Exception as e:
        out.pop("roc_auc", None)
        out.pop("brier", None)
        out["error"] = str(e)
    return out


def _decile_lift(y_true: list[int], y_score: list[float]) -> list[dict[str, Any]]:
    pairs = sorted(zip(y_score, y_true), key=lambda x: x[0])
    n = len(pairs)
    if n < 10:
        return []
    rows = []
    chunk = max(1, n // 10)
    for d in range(10):
        lo = d * chunk
        hi = n if d == 9 else (d + 1) * chunk
        sl = pairs[lo:hi]
        wins = sum(1 for _, y in sl if y == 1)
        tot = len(sl)
        rows.append(
            {
                "decile": d + 1,
                "n": tot,
                "win_rate": round(wins / tot, 4) if tot else 0,
                "score_min": round(sl[0][0], 4) if sl else 0,
                "score_max": round(sl[-1][0], 4) if sl else 0,
            }
        )
    return rows


def _gatekeeper_probs(picks: list[dict], model_path: Path) -> list[float] | None:
    try:
        import joblib
        import numpy as np
    except ImportError:
        print("[eval] joblib/numpy required for --gatekeeper-model")
        return None
    try:
        from ml_gatekeeper.gatekeeper import extract_features
    except ImportError as e:
        print(f"[eval] Cannot import gatekeeper extract_features: {e}")
        return None
    if not model_path.exists():
        print(f"[eval] Model not found: {model_path}")
        return None
    bundle = joblib.load(model_path)
    gb = bundle["gb"]
    rf = bundle["rf"]
    scaler = bundle["scaler"]
    rows = [extract_features(pick) for pick in picks]
    X = np.array(rows, dtype=np.float64)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    Xs = scaler.transform(X)
    gb_p = gb.predict_proba(Xs)[:, 1]
    rf_p = rf.predict_proba(Xs)[:, 1]
    return [float(0.6 * a + 0.4 * b) for a, b in zip(gb_p, rf_p)]


def _compare_priors(picks: list[dict], labels: list[int]) -> None:
    try:
        from ml_gatekeeper.gatekeeper import extract_features, FEATURE_NAMES
    except ImportError as e:
        print(f"[eval] --compare-priors needs ml_gatekeeper: {e}")
        return
    idx_strong = FEATURE_NAMES.index("strong_strategy")
    idx_weak = FEATURE_NAMES.index("weak_strategy")
    idx_sfwd = FEATURE_NAMES.index("strat_fwd_wr")

    strong = []
    weak = []
    sfwd = []
    ys = []
    for pick, y in zip(picks, labels):
        feat = extract_features(pick)
        strong.append(float(feat[idx_strong]))
        weak.append(float(feat[idx_weak]))
        sfwd.append(float(feat[idx_sfwd]))
        ys.append(float(y))

    for name, series in (
        ("strong_strategy_flag", strong),
        ("weak_strategy_flag", weak),
        ("strat_fwd_wr", sfwd),
    ):
        r = _pearson(series, ys)
        print(f"  Pearson(outcome, {name}): {r if r is not None else 'n/a'}")


def main() -> int:
    ap = argparse.ArgumentParser(description="ML lift/calibration on closed picks")
    ap.add_argument("--picks", type=Path, help="JSON array of closed picks")
    ap.add_argument(
        "--dashboard",
        type=Path,
        help="dashboard_data.json (uses picks.recent_closed)",
    )
    ap.add_argument(
        "--gatekeeper-model",
        type=Path,
        default=ROOT / "ml_gatekeeper" / "models" / "gatekeeper_model.joblib",
        help="Gatekeeper joblib bundle for ensemble probability",
    )
    ap.add_argument(
        "--compare-priors",
        action="store_true",
        help="Correlate static strategy flags vs strat_fwd_wr with outcome",
    )
    args = ap.parse_args()

    if args.dashboard:
        path = args.dashboard
        picks = load_closed_array(path)
    elif args.picks:
        picks = load_closed_array(args.picks)
    else:
        default_closed = ROOT / "alpha_engine" / "data" / "closed_picks.json"
        dash = ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
        if default_closed.exists():
            picks = load_closed_array(default_closed)
            print(f"[eval] Using default {default_closed}")
        elif dash.exists():
            picks = load_closed_array(dash)
            print(f"[eval] Using dashboard recent_closed from {dash}")
        else:
            print("[eval] No --picks/--dashboard and no default files found.")
            return 1

    rows: list[tuple[dict, int]] = []
    for pick in picks:
        lab = binary_label(pick)
        if lab is None:
            continue
        rows.append((pick, lab))
    if len(rows) < 30:
        print(f"[eval] Only {len(rows)} labeled picks — metrics may be unstable.")

    picks_l = [p for p, _ in rows]
    y_true = [y for _, y in rows]

    def col(name: str) -> list[float]:
        if name == "elite_norm":
            return [_f(p.get("elite_score")) / 100.0 for p in picks_l]
        if name == "confidence":
            return [_f(p.get("confidence")) for p in picks_l]
        if name == "ml_composite":
            # Stored as 0–100 style in many feeds; scale for probability metrics
            return [
                min(1.0, _f(p.get("ml_composite_score") or p.get("ml_score")) / 100.0)
                for p in picks_l
            ]
        return []

    print("=" * 72)
    print("LIFT / CALIBRATION (higher ROC-AUC is better; lower Brier is better)")
    print("=" * 72)
    for label, fn in (
        ("elite_score/100", "elite_norm"),
        ("confidence", "confidence"),
        ("ml_composite_score/100", "ml_composite"),
    ):
        s = col(fn)
        m = _metrics(y_true, s)
        print(f"\n[{label}] n={m.get('n')}")
        if m.get("note"):
            print(f"  ({m['note']})")
        if "roc_auc" in m and "brier" in m:
            print(f"  ROC-AUC: {m['roc_auc']:.4f}  Brier: {m['brier']:.4f}  base_rate: {m['base_rate']:.4f}")
        elif m.get("error"):
            print(f"  error: {m['error']}")
        for row in _decile_lift(y_true, s)[:3]:
            print(f"  decile {row['decile']}: WR={row['win_rate']:.2%} n={row['n']} score[{row['score_min']:.3f},{row['score_max']:.3f}]")
        if len(y_true) >= 30:
            tail = _decile_lift(y_true, s)
            if tail:
                print(f"  top decile WR: {tail[-1]['win_rate']:.2%}  bottom decile WR: {tail[0]['win_rate']:.2%}")

    gk_path = Path(args.gatekeeper_model)
    gk_probs = _gatekeeper_probs(picks_l, gk_path)
    if gk_probs is not None and len(gk_probs) == len(y_true):
        m = _metrics(y_true, gk_probs)
        print(f"\n[gatekeeper ensemble] model={gk_path.name} n={m.get('n')}")
        if m.get("note"):
            print(f"  ({m['note']})")
        if "roc_auc" in m and "brier" in m:
            print(f"  ROC-AUC: {m['roc_auc']:.4f}  Brier: {m['brier']:.4f}  base_rate: {m['base_rate']:.4f}")
        elif m.get("error"):
            print(f"  error: {m['error']}")
        for row in _decile_lift(y_true, gk_probs)[:3]:
            print(f"  decile {row['decile']}: WR={row['win_rate']:.2%} n={row['n']}")

    if args.compare_priors and picks_l:
        print("\n" + "=" * 72)
        print("PRIOR SIGNAL STRENGTH (Pearson correlation with binary win)")
        print("=" * 72)
        _compare_priors(picks_l, y_true)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
