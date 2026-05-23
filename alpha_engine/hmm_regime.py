"""
Hidden Markov Model (HMM) Regime Detection
===========================================
3-state HMM (bull/bear/chop) on BTC returns + volatility.
Probabilistic regime membership + strategy routing.

#4 ranked technique: Man Group/AHL core component. Sharpe +0.3-0.7.
"""

import json
import math
import numpy as np
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
STATE_FILE = DATA_DIR / "hmm_regime_state.json"

BULL, BEAR, CHOP = 0, 1, 2
REGIME_NAMES = {BULL: "BULL", BEAR: "BEAR", CHOP: "CHOP"}

REGIME_SCORE_ADJ = {BULL: 5, BEAR: -5, CHOP: -3}


class SimpleHMM:
    """Lightweight 3-state HMM, pure numpy (no hmmlearn needed)."""

    def __init__(self):
        self.emissions = {
            BULL: {"ret_mean": 0.003, "ret_std": 0.015, "vol_mean": 0.012, "vol_std": 0.005},
            BEAR: {"ret_mean": -0.003, "ret_std": 0.025, "vol_mean": 0.025, "vol_std": 0.010},
            CHOP: {"ret_mean": 0.0, "ret_std": 0.010, "vol_mean": 0.008, "vol_std": 0.004},
        }
        self.transitions = np.array([
            [0.90, 0.05, 0.05],
            [0.05, 0.90, 0.05],
            [0.10, 0.10, 0.80],
        ])
        self.state_probs = np.array([0.4, 0.2, 0.4])

    def _gauss_ll(self, x, mean, std):
        if std <= 0:
            return -100
        return -0.5 * ((x - mean) / std) ** 2 - math.log(std)

    def update(self, daily_return, daily_volatility):
        log_likes = np.zeros(3)
        for s in range(3):
            p = self.emissions[s]
            log_likes[s] = self._gauss_ll(daily_return, p["ret_mean"], p["ret_std"]) + \
                           self._gauss_ll(daily_volatility, p["vol_mean"], p["vol_std"])
        prior = self.state_probs @ self.transitions
        likes = np.exp(log_likes - log_likes.max())
        posterior = prior * likes
        total = posterior.sum()
        if total > 0:
            self.state_probs = posterior / total
        return self.get_regime()

    def get_regime(self):
        best = int(np.argmax(self.state_probs))
        return {
            "regime": REGIME_NAMES[best],
            "regime_id": best,
            "confidence": float(self.state_probs[best]),
            "probabilities": {
                "BULL": float(self.state_probs[BULL]),
                "BEAR": float(self.state_probs[BEAR]),
                "CHOP": float(self.state_probs[CHOP]),
            },
        }


def fetch_btc_daily_stats():
    try:
        url = "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=30"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = json.loads(urllib.request.urlopen(req, timeout=10).read())
        closes = [float(d[4]) for d in data]
        returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
        return returns[-1], float(np.std(returns[-14:]))
    except Exception:
        return None, None


_hmm = None

def get_hmm():
    global _hmm
    if _hmm is None:
        _hmm = SimpleHMM()
        try:
            if STATE_FILE.exists():
                with open(STATE_FILE, encoding="utf-8") as f:
                    state = json.load(f)
                _hmm.state_probs = np.array(state.get("state_probs", [0.4, 0.2, 0.4]))
        except Exception:
            pass
    return _hmm


def detect_regime():
    hmm = get_hmm()
    ret, vol = fetch_btc_daily_stats()
    if ret is not None and vol is not None:
        result = hmm.update(ret, vol)
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump({"state_probs": hmm.state_probs.tolist(),
                           "last_update": datetime.now(timezone.utc).isoformat(),
                           "regime": result}, f, indent=2)
        except Exception:
            pass
        return result
    return hmm.get_regime()


def get_regime_score_adjustment(pick):
    try:
        regime = detect_regime()
        base = REGIME_SCORE_ADJ.get(regime["regime_id"], 0)
        direction = str(pick.get("direction", "LONG")).upper()
        if direction in ("SHORT", "SELL"):
            base = -base
        return round(base * regime["confidence"], 1)
    except Exception:
        return 0.0


if __name__ == "__main__":
    r = detect_regime()
    print(f"Regime: {r['regime']} ({r['confidence']:.0%})")
    print(f"BULL={r['probabilities']['BULL']:.0%} BEAR={r['probabilities']['BEAR']:.0%} CHOP={r['probabilities']['CHOP']:.0%}")
