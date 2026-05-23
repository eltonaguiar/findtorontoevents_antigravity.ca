"""Meta-labeling scaffold (Lopez de Prado, AFML Ch. 3).

Pattern: a primary signal (our existing pipeline) emits a pick. A SECONDARY
classifier, trained on historical primary-signal outcomes, decides whether
to ACT on the primary signal. The meta-classifier learns features like:

  - Asset class / symbol characteristics
  - Time-of-day, day-of-week
  - Recent strategy WR
  - Recent symbol WR
  - Volatility regime
  - Cross-signal agreement

This dramatically reduces false positives when the primary signal is noisy.
Our cycle-8/9 perf-reviews show "no skill-verified strategies" — meta-labeling
is the textbook remedy: keep the (noisy) primary signals, add a classifier
trained on past wins/losses to skip the most-likely-to-lose primary signals.

Implementation constraint
-------------------------
This module is a SCAFFOLD. It defines the feature extractor, train/predict
contract, and integration point with AutoHedge committee (PR #298) as the
5th agent. It does NOT include a trained model — training requires scikit-learn
or lightgbm, which we don't want to add as a hard dep without engineer sign-off.

The scaffold is usable as:

    from tools.meta_labeler import extract_features, MetaLabelModel
    features = extract_features(closed_picks)
    model = MetaLabelModel()  # placeholder; swap in sklearn when ready
    model.fit(features, labels)

Then wire model.predict into the AutoHedge committee:

    def _agent_meta_label(pick: dict) -> dict:
        probs = META_MODEL.predict_proba(extract_features([pick]))
        prob_win = probs[0][1]
        return {"score": round(prob_win * 100, 1), "passed": prob_win >= 0.55, ...}
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _f(v: Any, default: float = 0.0) -> float:
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def extract_features(picks: list[dict]) -> list[dict]:
    """Per-pick feature vector for meta-labeling. Numeric only; nulls -> 0.

    Features intentionally keep to data already in dashboard_payload so the
    scaffold works without external APIs.
    """
    out = []
    for p in picks:
        entry_ts = _parse_iso(p.get("entry_time") or p.get("created_at") or p.get("timestamp"))
        hour = entry_ts.hour if entry_ts else 0
        dow = entry_ts.weekday() if entry_ts else 0  # Mon=0

        asset_class = (p.get("asset_class") or "UNKNOWN").upper()
        direction = (p.get("direction") or "LONG").upper()

        features = {
            # Numeric signal features
            "score": _f(p.get("score")),
            "elite_score": _f(p.get("elite_score")),
            "ml_composite_score": _f(p.get("ml_composite_score") or p.get("ml_score")),
            "antigravity_score": _f(p.get("antigravity_score")),
            "confidence": _f(p.get("confidence")),
            "risk_reward": _f(p.get("risk_reward") or p.get("rr_ratio")),
            "trust_score": _f(p.get("trust_score")),
            "rsi_at_entry": _f(p.get("rsi_at_entry")),
            # Time features
            "hour_utc": float(hour),
            "day_of_week": float(dow),
            "is_kill_window": float(1.0 if 8 <= hour <= 11 or 16 <= hour <= 21 else 0.0),
            # One-hot asset class
            "is_crypto": float(1.0 if asset_class == "CRYPTO" else 0.0),
            "is_equity": float(1.0 if asset_class == "EQUITY" else 0.0),
            "is_forex": float(1.0 if asset_class == "FOREX" else 0.0),
            "is_commodity": float(1.0 if asset_class == "COMMODITY" else 0.0),
            "is_futures": float(1.0 if asset_class == "FUTURES" else 0.0),
            # Direction
            "is_long": float(1.0 if direction == "LONG" else 0.0),
            # Conflict / consensus markers
            "has_direction_conflict": float(1.0 if p.get("_direction_conflict") else 0.0),
            "has_cross_feed_dup": float(1.0 if p.get("_cross_feed_dup") else 0.0),
            "degradation_penalty": _f(p.get("_degradation_penalty")),
            "is_fresh": float(1.0 if p.get("is_fresh", True) else 0.0),
        }
        out.append(features)
    return out


def pnl_to_label(pnl_pct: float | None, threshold_pct: float = 0.01) -> int | None:
    """Convert pnl_pct to binary meta-label: 1 = act (win), 0 = skip (loss/flat).

    None inputs return None so you can filter unresolved picks.
    """
    if pnl_pct is None:
        return None
    return 1 if pnl_pct > threshold_pct else 0


class MetaLabelModel:
    """Placeholder interface. Swap in sklearn/lightgbm when wired for real.

    Until then this is a pass-through that echoes a fixed prior so downstream
    code can be tested end-to-end.
    """
    def __init__(self, default_prob_win: float = 0.5):
        self.default_prob_win = default_prob_win
        self.fitted = False
        self.feature_names: list[str] = []

    def fit(self, features: list[dict], labels: list[int]) -> "MetaLabelModel":
        if features:
            self.feature_names = sorted(features[0].keys())
        # In the real implementation, a classifier (RF / LGBM / logistic)
        # would be trained here. For scaffold purposes we just record that
        # we have "seen" data; predictions remain the default prior.
        self.fitted = True
        return self

    def predict_proba(self, features: list[dict]) -> list[tuple[float, float]]:
        """Return (P(loss), P(win)) per feature vector."""
        p = self.default_prob_win
        return [(1 - p, p) for _ in features]

    def predict(self, features: list[dict], threshold: float = 0.5) -> list[int]:
        return [1 if p[1] >= threshold else 0 for p in self.predict_proba(features)]


def train_meta_labeler_from_closed(
    closed_picks: list[dict],
    threshold_pct: float = 0.01,
) -> tuple[MetaLabelModel, int, int]:
    """Build training set from closed picks and fit the (scaffold) model.

    Returns (model, n_train, n_positive_labels).
    """
    features: list[dict] = []
    labels: list[int] = []
    for p in closed_picks:
        label = pnl_to_label(p.get("pnl_pct"), threshold_pct=threshold_pct)
        if label is None:
            continue
        feats = extract_features([p])[0]
        features.append(feats)
        labels.append(label)
    model = MetaLabelModel()
    model.fit(features, labels)
    return model, len(features), sum(labels)


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser(description="Meta-labeling scaffold demo.")
    ap.add_argument("--dashboard", default="audit_trail/data/dashboard_payload.json")
    args = ap.parse_args()

    dp = json.load(open(args.dashboard, "r", encoding="utf-8"))
    closed = dp["picks"]["recent_closed"]
    model, n_train, n_pos = train_meta_labeler_from_closed(closed)
    feature_names = model.feature_names
    print(json.dumps({
        "n_train": n_train,
        "n_positive_labels": n_pos,
        "base_rate_pct": round(n_pos / n_train * 100, 2) if n_train else None,
        "feature_names": feature_names,
        "note": "Scaffold only. Swap in sklearn/lightgbm for real predictions.",
    }, indent=2))
