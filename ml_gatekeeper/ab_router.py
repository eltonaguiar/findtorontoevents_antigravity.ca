"""ml_gatekeeper/ab_router.py — Deterministic A/B routing for gatekeeper models.

Routes each pick to OLD (leaky) or NEW (leakage-masked) gatekeeper model
based on MD5 hash of pick_id. Deterministic: same pick always to same arm.
Reproducible: no randomness.

Per Grok-4 consultation 2026-05-12: highest-leverage remaining ML item.
Phase A (env-flag feature masking) shipped on main. This is Phase B + C
(router + dashboard summary).

Source: xiao mi mimo (Cerebras) code delivery 2026-05-12, peer mb2v7tau.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# These features are confirmed to leak future information.
# The NEW model must NOT see them.
LEAKAGE_FEATURES = (
    "forward_wr",
    "strat_fwd_wr",
    "eb_forward_wr",
    "age_hours",  # proxy for whether result is already known
)

TRAFFIC_SPLIT_NEW = float(os.environ.get("ML_GATE_AB_SPLIT", "0.5"))
AB_ENABLED = os.environ.get("ML_GATE_AB_ENABLED", "0") == "1"
AB_LOG_PATH = os.environ.get("ML_GATE_AB_LOG", "data/ml_gatekeeper/ab_router_log.jsonl")


@dataclass
class ABResult:
    """Result of an A/B routing decision + scoring."""
    pick_id: str
    strategy_id: str
    arm: str                # "OLD" or "NEW"
    model_version: str      # "old_leaky" or "new_clean"
    score: float
    confidence: float
    features_used: list
    features_masked: list
    timestamp: str

    def to_dict(self):
        return asdict(self)


class ABRouter:
    """Deterministic A/B router for ml_gatekeeper models."""

    def __init__(
        self,
        old_model_path: Optional[str] = None,
        new_model_path: Optional[str] = None,
        traffic_split: float = TRAFFIC_SPLIT_NEW,
        enabled: bool = AB_ENABLED,
        log_path: str = AB_LOG_PATH,
    ):
        self.traffic_split = max(0.0, min(1.0, traffic_split))
        self.enabled = enabled
        self.log_path = log_path
        self.old_model = self._load_model(old_model_path, "old")
        self.new_model = self._load_model(new_model_path, "new")
        self._counts = {"OLD": 0, "NEW": 0}
        self._outcomes = {"OLD": {"wins": 0, "losses": 0}, "NEW": {"wins": 0, "losses": 0}}

    def _load_model(self, path: Optional[str], label: str):
        if path is None:
            return None
        try:
            import joblib
            model = joblib.load(path)
            logger.info("Loaded %s model from %s", label, path)
            return model
        except Exception as e:
            logger.error("Failed to load %s model from %s: %s", label, path, e)
            return None

    def route(self, pick_id: str) -> str:
        """Deterministically route pick to OLD or NEW arm.

        Returns "OLD" or "NEW". Same pick_id always returns same arm.
        """
        hash_val = int(hashlib.md5(str(pick_id).encode("utf-8")).hexdigest()[:8], 16)
        bucket = (hash_val % 10000) / 10000.0
        return "NEW" if bucket < self.traffic_split else "OLD"

    def _mask_leakage_features(self, features: dict) -> tuple[dict, list]:
        masked = {k: v for k, v in features.items() if k not in LEAKAGE_FEATURES}
        masked_keys = [k for k in features if k in LEAKAGE_FEATURES]
        return masked, masked_keys

    def score(self, pick_id: str, features: dict, strategy_id: str = "") -> ABResult:
        """Route and score a pick. Returns ABResult."""
        now = datetime.utcnow().isoformat()

        if not self.enabled:
            score, conf = self._score_with_model(self.old_model, features, "old")
            return ABResult(
                pick_id=str(pick_id), strategy_id=strategy_id,
                arm="OLD", model_version="old_leaky",
                score=score, confidence=conf,
                features_used=list(features.keys()), features_masked=[],
                timestamp=now,
            )

        arm = self.route(pick_id)
        if arm == "NEW":
            clean_features, masked = self._mask_leakage_features(features)
            score, conf = self._score_with_model(self.new_model, clean_features, "new")
            result = ABResult(
                pick_id=str(pick_id), strategy_id=strategy_id,
                arm="NEW", model_version="new_clean",
                score=score, confidence=conf,
                features_used=list(clean_features.keys()), features_masked=masked,
                timestamp=now,
            )
        else:
            score, conf = self._score_with_model(self.old_model, features, "old")
            result = ABResult(
                pick_id=str(pick_id), strategy_id=strategy_id,
                arm="OLD", model_version="old_leaky",
                score=score, confidence=conf,
                features_used=list(features.keys()), features_masked=[],
                timestamp=now,
            )

        self._counts[arm] = self._counts.get(arm, 0) + 1
        self._log_result(result)
        return result

    def _score_with_model(self, model, features: dict, label: str):
        if model is None:
            return 0.5, 0.5
        try:
            import numpy as np
            X = np.array(list(features.values())).reshape(1, -1)
            if hasattr(model, "predict_proba"):
                proba = model.predict_proba(X)[0]
                return float(proba[1]), float(max(proba))
            if hasattr(model, "predict"):
                s = float(model.predict(X)[0])
                return s, abs(s)
            return 0.5, 0.5
        except Exception as e:
            logger.error("Scoring error with %s model: %s", label, e)
            return 0.5, 0.0

    def _log_result(self, result: ABResult) -> None:
        try:
            d = os.path.dirname(self.log_path)
            if d:
                os.makedirs(d, exist_ok=True)
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(result.to_dict()) + "\n")
        except Exception as e:
            logger.warning("Failed to write A/B log: %s", e)

    def record_outcome(self, pick_id: str, arm: str, won: bool) -> None:
        if arm not in self._outcomes:
            return
        if won:
            self._outcomes[arm]["wins"] += 1
        else:
            self._outcomes[arm]["losses"] += 1

    def summary(self) -> dict:
        out = {"timestamp": datetime.utcnow().isoformat(), "arms": {}}
        for arm in ("OLD", "NEW"):
            total = self._counts.get(arm, 0)
            wins = self._outcomes[arm]["wins"]
            losses = self._outcomes[arm]["losses"]
            resolved = wins + losses
            wr = wins / resolved if resolved > 0 else 0.0
            out["arms"][arm] = {
                "total_scored": total, "resolved": resolved,
                "wins": wins, "losses": losses, "win_rate": round(wr, 4),
            }
        old = out["arms"]["OLD"]
        new = out["arms"]["NEW"]
        if old["resolved"] >= 30 and new["resolved"] >= 30:
            n_old, n_new = old["resolved"], new["resolved"]
            p_pool = (old["wins"] + new["wins"]) / (n_old + n_new)
            if 0 < p_pool < 1:
                se = math.sqrt(p_pool * (1 - p_pool) * (1 / n_old + 1 / n_new))
                z = (new["win_rate"] - old["win_rate"]) / se if se > 0 else 0
                p_value = 2 * (1 - _normal_cdf(abs(z)))
                lift = new["win_rate"] - old["win_rate"]
                lift_pct = (lift / old["win_rate"] * 100) if old["win_rate"] > 0 else None
                out["z_test"] = {
                    "z_statistic": round(z, 4), "p_value": round(p_value, 4),
                    "significant_at_05": p_value < 0.05,
                    "significant_at_01": p_value < 0.01,
                    "lift": round(lift, 4),
                    "lift_pct": round(lift_pct, 2) if lift_pct is not None else None,
                }
            else:
                out["z_test"] = {"note": "Pool proportion 0 or 1; cannot compute"}
        else:
            out["z_test"] = {
                "note": f"Need >=30 resolved per arm; OLD={old['resolved']} NEW={new['resolved']}"
            }
        return out


def _normal_cdf(x: float) -> float:
    """Standard normal CDF via Abramowitz & Stegun approximation."""
    a1, a2, a3, a4, a5 = 0.254829592, -0.284496736, 1.421413741, -1.453152027, 1.061405429
    p = 0.3275911
    sign = 1 if x >= 0 else -1
    x = abs(x) / math.sqrt(2)
    t = 1.0 / (1.0 + p * x)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x)
    return 0.5 * (1.0 + sign * y)
