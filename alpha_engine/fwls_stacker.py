"""
Feature-Weighted Linear Stacking (FWLS)
=======================================
Meta-learner weights VARY based on market context. In high-vol regimes,
weight XGBoost more; in low-vol, weight RF more.

#6 ranked technique: Netflix Prize (Sill et al.), WorldQuant BRAIN.
Expected: +2-5% improvement on top of static stacking.
"""

import json
import numpy as np
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
STATE_FILE = DATA_DIR / "fwls_state.json"


class FWLSStacker:
    """Context-weighted meta-learner for model blending.

    final = (w1 + a1*ctx) * pred1 + (w2 + a2*ctx) * pred2 + bias
    where ctx = [regime, volatility, hour_bucket]
    """

    def __init__(self):
        # Base weights for 2 models (primary + secondary RF)
        self.w_base = np.array([0.6, 0.4])  # primary 60%, RF 40%
        # Context interaction weights (3 context features x 2 models)
        self.w_ctx = np.zeros((3, 2))
        self.bias = 0.0
        self.lr = 0.005
        self.step = 0
        self._load()

    def _load(self):
        try:
            if STATE_FILE.exists():
                with open(STATE_FILE, encoding="utf-8") as f:
                    s = json.load(f)
                self.w_base = np.array(s.get("w_base", [0.6, 0.4]))
                self.w_ctx = np.array(s.get("w_ctx", np.zeros((3, 2)).tolist()))
                self.bias = s.get("bias", 0.0)
                self.step = s.get("step", 0)
        except Exception:
            pass

    def _save(self):
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "w_base": self.w_base.tolist(),
                    "w_ctx": self.w_ctx.tolist(),
                    "bias": self.bias,
                    "step": self.step,
                }, f, indent=2)
        except Exception:
            pass

    def _get_context(self, pick):
        """Extract 3 context features: regime, volatility, hour."""
        regime = 0  # -1=bear, 0=neutral, 1=bull
        r = str(pick.get("hmm_regime_adj", pick.get("regime", ""))).upper()
        if "BULL" in r or float(pick.get("hmm_regime_adj", 0) or 0) > 0:
            regime = 1
        elif "BEAR" in r or float(pick.get("hmm_regime_adj", 0) or 0) < 0:
            regime = -1

        vol = float(pick.get("vol_regime", 1) or 1)  # 0=low, 1=med, 2=high

        hour = 1  # 0=asian, 1=euro, 2=us
        try:
            ts = pick.get("timestamp", "")
            if ts and len(ts) >= 13:
                h = int(ts[11:13])
                hour = 0 if h < 8 else (1 if h < 16 else 2)
        except Exception:
            pass

        return np.array([regime, vol, hour])

    def blend(self, pick, primary_score, secondary_score):
        """Blend two model scores using context-weighted stacking.

        Returns blended score (0-1 probability).
        """
        ctx = self._get_context(pick)
        preds = np.array([primary_score, secondary_score])

        # Context-modulated weights: w = w_base + ctx @ w_ctx
        weights = self.w_base + ctx @ self.w_ctx

        # Softmax to ensure positive weights summing to 1
        exp_w = np.exp(weights - weights.max())
        weights = exp_w / exp_w.sum()

        blended = float(np.dot(weights, preds) + self.bias)
        return max(0.0, min(1.0, blended))

    def update(self, pick, primary_score, secondary_score, won):
        """Update weights after trade resolves."""
        ctx = self._get_context(pick)
        preds = np.array([primary_score, secondary_score])
        target = 1.0 if won else 0.0

        # Current blend
        weights = self.w_base + ctx @ self.w_ctx
        exp_w = np.exp(weights - weights.max())
        weights = exp_w / exp_w.sum()
        blended = float(np.dot(weights, preds) + self.bias)
        blended = max(0.01, min(0.99, blended))

        # Error
        error = blended - target

        # Update base weights
        self.w_base -= self.lr * error * preds
        # Update context interactions
        for i in range(len(ctx)):
            self.w_ctx[i] -= self.lr * error * ctx[i] * preds
        self.bias -= self.lr * error

        self.step += 1
        self._save()


# Singleton
_stacker = None

def get_stacker():
    global _stacker
    if _stacker is None:
        _stacker = FWLSStacker()
    return _stacker

def fwls_blend(pick, primary_score, secondary_score=0.5):
    """Blend scores with context-weighted stacking. Safe to call anywhere."""
    try:
        return get_stacker().blend(pick, primary_score, secondary_score)
    except Exception:
        return primary_score

def fwls_update(pick, primary_score, secondary_score, won):
    """Update FWLS after trade resolves."""
    try:
        get_stacker().update(pick, primary_score, secondary_score, won)
    except Exception:
        pass
