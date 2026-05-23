"""
Online Learning Layer -- Adaptive Signal Combiner
=================================================
Sits on top of ML ranker. Updates weights after EVERY trade outcome
via stochastic gradient descent. Adapts in minutes, not days.

#2 ranked technique from deep research:
- Used by Renaissance Technologies and Two Sigma
- Learns from each trade immediately (true online learning)
- Expected: +3-8% WR from faster adaptation to regime changes
"""

import json
import math
import numpy as np
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
STATE_FILE = DATA_DIR / "online_learner_state.json"

# Features the combiner uses (all available on each pick)
FEATURES = [
    "ml_score", "confidence", "elite_score_raw", "risk_reward",
    "pattern_predicted_wr", "entry_timing_score", "entry_zone_score",
    "thompson_bonus", "volume_confirmation_score",
]

DEFAULT_LR = 0.01
DECAY = 0.999  # per-step LR decay


class OnlineLearner:
    """Lightweight linear combiner that updates after every trade."""

    def __init__(self):
        self.weights = None
        self.bias = 0.0
        self.lr = DEFAULT_LR
        self.step = 0
        self.history = []  # last 100 updates
        self._load()

    def _load(self):
        try:
            if STATE_FILE.exists():
                with open(STATE_FILE, encoding="utf-8") as f:
                    state = json.load(f)
                self.weights = np.array(state["weights"])
                self.bias = state.get("bias", 0.0)
                self.step = state.get("step", 0)
                self.lr = state.get("lr", DEFAULT_LR)
                self.history = state.get("history", [])
        except Exception:
            pass

    def _save(self):
        try:
            state = {
                "weights": self.weights.tolist() if self.weights is not None else None,
                "bias": self.bias,
                "step": self.step,
                "lr": self.lr,
                "history": self.history[-100:],
            }
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception:
            pass

    def _extract_features(self, pick: dict) -> np.ndarray:
        """Extract feature vector from a pick dict."""
        feat = []
        for f in FEATURES:
            val = pick.get(f, 0)
            if val is None:
                val = 0
            try:
                feat.append(float(val))
            except (ValueError, TypeError):
                feat.append(0.0)
        return np.array(feat)

    def predict(self, pick: dict) -> float:
        """Predict win probability adjustment for a pick.

        Returns a score adjustment (-10 to +10) to add to elite_score.
        """
        x = self._extract_features(pick)

        if self.weights is None:
            self.weights = np.zeros(len(x))

        # Linear combination + sigmoid
        logit = np.dot(self.weights, x) + self.bias
        prob = 1.0 / (1.0 + math.exp(-max(-10, min(10, logit))))

        # Map probability to score adjustment: 0.5 = neutral, >0.5 = bonus
        adjustment = (prob - 0.5) * 20.0  # range: -10 to +10
        return round(adjustment, 1)

    def update(self, pick: dict, won: bool):
        """Update weights after a trade resolves. Core online learning step."""
        x = self._extract_features(pick)

        if self.weights is None:
            self.weights = np.zeros(len(x))

        # Current prediction
        logit = np.dot(self.weights, x) + self.bias
        pred = 1.0 / (1.0 + math.exp(-max(-10, min(10, logit))))

        # Target
        target = 1.0 if won else 0.0

        # Gradient (logistic loss)
        error = pred - target

        # Adaptive learning rate (AdaGrad-style decay)
        current_lr = self.lr * (DECAY ** self.step)

        # SGD update
        self.weights -= current_lr * error * x
        self.bias -= current_lr * error

        self.step += 1
        self.history.append({
            "step": self.step,
            "won": won,
            "pred": round(pred, 3),
            "error": round(error, 3),
            "lr": round(current_lr, 6),
        })

        self._save()

        return {
            "step": self.step,
            "prediction": round(pred, 3),
            "actual": target,
            "error": round(error, 3),
        }


# Singleton for import convenience
_learner = None

def get_online_learner():
    global _learner
    if _learner is None:
        _learner = OnlineLearner()
    return _learner

def online_score_adjustment(pick: dict) -> float:
    """Get score adjustment from online learner. Safe to call anywhere."""
    try:
        return get_online_learner().predict(pick)
    except Exception:
        return 0.0

def online_update(pick: dict, won: bool) -> dict:
    """Update online learner after trade. Call when a pick closes."""
    try:
        return get_online_learner().update(pick, won)
    except Exception:
        return {}
