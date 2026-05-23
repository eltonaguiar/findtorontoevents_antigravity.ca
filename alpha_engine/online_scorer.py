#!/usr/bin/env python3
"""
Online Learning Scorer — Streaming Logistic Regression
=======================================================
Replaces batch retrain with true online learning. Processes each closed
pick ONE AT A TIME in chronological order, updating weights via SGD
with L2 regularization and learning rate decay.

After training on all closed picks, scores every active pick with P(win)
and flags picks the online learner disagrees with.

Key insight from our data: is_consensus should carry NEGATIVE weight
(18% WR for consensus picks vs 35% solo).

Standalone runnable:
  python alpha_engine/online_scorer.py
"""

import sys, os, io, json, math
from datetime import datetime, timezone
from pathlib import Path
from collections import deque

# ── Windows UTF-8 fix ──────────────────────────────────────────────
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── Paths ──────────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent.parent
DATA_DIR = Path(__file__).resolve().parent / "data"
PAYLOAD_PATH = BASE / "audit_trail" / "data" / "dashboard_payload.json"
WEIGHTS_PATH = DATA_DIR / "online_scorer_weights.json"
PREDICTIONS_PATH = DATA_DIR / "online_scorer_predictions.json"

# ── Feature names (order matters — weights correspond to these) ────
FEATURE_NAMES = [
    "score",             # normalized 0-1
    "confidence",        # raw confidence from pick
    "direction",         # 1=LONG, 0=SHORT
    "is_copy_trader",    # 1 if source is copy_trader
    "is_consensus",      # 1 if agreement_count >= 3 (EXPECTED NEGATIVE)
    "age_hours",         # normalized
    "risk_reward",       # rr_ratio
    "regime_match",      # 1 if direction matches regime
    "source_system_tier",  # 1=tier1, 0.5=tier2, 0=tier3
    "volume_ratio",      # volume confirmation if available
]

N_FEATURES = len(FEATURE_NAMES)

# ── Hyperparameters ───────────────────────────────────────────────
INITIAL_LR = 0.01
LR_DECAY = 0.001       # lr = INITIAL_LR / (1 + LR_DECAY * step)
L2_LAMBDA = 0.001      # L2 regularization strength
AUC_WINDOW = 100       # rolling window for AUC computation

# ── Tier classification ──────────────────────────────────────────
TIER1_SYSTEMS = {
    "alpha_engine", "super_signals", "kimi_riseoftheclaw",
    "mercury2", "ml_crypto_predictor", "crypto_ml_edge",
}
TIER2_SYSTEMS = {
    "copy_trader_consensus", "copy_trader_intel", "aggregated_picks",
    "kimi_signal_tracking", "breakout_b_ml", "rapid_fire",
    "luxalgo_filters", "signal_engine_mutations",
}
# Everything else = tier3

# ── Regime detection ─────────────────────────────────────────────
CURRENT_REGIME = None  # loaded from payload


def _sigmoid(z):
    """Numerically stable sigmoid."""
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    else:
        ez = math.exp(z)
        return ez / (1.0 + ez)


def _load_payload():
    """Load dashboard_payload.json."""
    if not PAYLOAD_PATH.exists():
        print(f"[online_scorer] WARN: payload not found at {PAYLOAD_PATH}")
        return None
    with open(PAYLOAD_PATH, encoding="utf-8") as f:
        return json.load(f)


def _detect_regime(payload):
    """Determine current regime from payload."""
    global CURRENT_REGIME
    regime_data = payload.get("regime_validation", {}).get("regime_wr_breakdown", {})
    # Find regime with most trades
    best_regime = "RANGING"
    max_trades = 0
    for regime, stats in regime_data.items():
        total = stats.get("total", 0)
        if total > max_trades:
            max_trades = total
            best_regime = regime
    CURRENT_REGIME = best_regime
    print(f"[online_scorer] Detected regime: {CURRENT_REGIME} ({max_trades} trades)")


def _get_system_tier(source_system):
    """Classify source system into tier."""
    s = (source_system or "").lower().strip()
    if s in TIER1_SYSTEMS:
        return 1.0
    elif s in TIER2_SYSTEMS:
        return 0.5
    return 0.0


def _is_copy_trader(pick):
    """Check if pick is from a copy trader system."""
    source = (pick.get("source_system") or "").lower()
    sources = [s.lower() for s in (pick.get("source_systems") or [])]
    ct_keywords = ["copy_trader", "copytrader", "ct_consensus"]
    for kw in ct_keywords:
        if kw in source:
            return 1.0
        for s in sources:
            if kw in s:
                return 1.0
    return 0.0


def _is_consensus(pick):
    """Check if pick has 3+ systems agreeing."""
    agreement = pick.get("agreement_count", 0) or 0
    consensus = pick.get("consensus_count") or 0
    return 1.0 if (agreement >= 3 or consensus >= 3) else 0.0


def _regime_match(pick):
    """Check if pick direction matches detected regime."""
    direction = (pick.get("direction") or "").upper()
    if CURRENT_REGIME == "TRENDING_UP" and direction == "LONG":
        return 1.0
    elif CURRENT_REGIME == "TRENDING_DOWN" and direction == "SHORT":
        return 1.0
    elif CURRENT_REGIME == "RANGING":
        return 0.5  # neutral in ranging
    return 0.0


def _extract_features(pick, max_score=100.0, max_age=168.0):
    """Extract feature vector from a pick.

    Returns list of floats in FEATURE_NAMES order.
    """
    # score: normalize to 0-1
    raw_score = pick.get("score", 0) or 0
    score = min(max(raw_score / max_score, 0.0), 1.0)

    # confidence
    confidence = pick.get("confidence", 0.5) or 0.5
    confidence = min(max(float(confidence), 0.0), 1.0)

    # direction: 1=LONG, 0=SHORT
    direction = 1.0 if (pick.get("direction") or "").upper() == "LONG" else 0.0

    # is_copy_trader
    copy_trader = _is_copy_trader(pick)

    # is_consensus
    consensus = _is_consensus(pick)

    # age_hours: normalize (cap at max_age)
    age = pick.get("age_hours", 0) or 0
    age_norm = min(max(float(age) / max_age, 0.0), 1.0)

    # risk_reward ratio (cap at 10)
    rr = pick.get("rr_ratio", 1.0) or 1.0
    rr = min(max(float(rr) / 10.0, 0.0), 1.0)

    # regime_match
    regime = _regime_match(pick)

    # source_system_tier
    tier = _get_system_tier(pick.get("source_system", ""))

    # volume_ratio: check scoreBreakdown or direct field
    vol = 0.0
    breakdown = pick.get("_scoreBreakdown", {}) or {}
    vol_score = breakdown.get("volume", 0) or 0
    if vol_score:
        vol = min(float(vol_score) / 10.0, 1.0)  # normalize
    elif pick.get("technical_v_1h"):
        # Use technical volume if available
        try:
            vol = min(float(pick["technical_v_1h"]) / 100.0, 1.0)
        except (ValueError, TypeError):
            vol = 0.0

    return [score, confidence, direction, copy_trader, consensus,
            age_norm, rr, regime, tier, vol]


def _pick_is_win(pick):
    """Determine if a closed pick was a win."""
    status = (pick.get("status") or "").upper()
    if status in ("WON", "WIN", "TP_HIT"):
        return 1
    if status in ("LOST", "LOSS", "SL_HIT"):
        return 0
    # Check pnl
    pnl = pick.get("pnl_pct", 0) or 0
    if pnl > 0:
        return 1
    elif pnl < 0:
        return 0
    # Check exit_reason
    exit_r = (pick.get("exit_reason") or "").upper()
    if "TP" in exit_r:
        return 1
    if "SL" in exit_r:
        return 0
    return None  # indeterminate — skip


def _compute_rolling_auc(recent_preds):
    """Compute AUC from recent (pred, label) pairs.

    Uses the Mann-Whitney U statistic formulation for AUC.
    """
    positives = [p for p, y in recent_preds if y == 1]
    negatives = [p for p, y in recent_preds if y == 0]

    if not positives or not negatives:
        return 0.5  # no discrimination possible

    # Count concordant pairs
    concordant = 0
    total = len(positives) * len(negatives)
    for pp in positives:
        for pn in negatives:
            if pp > pn:
                concordant += 1
            elif pp == pn:
                concordant += 0.5

    return concordant / total if total > 0 else 0.5


class OnlineLogisticRegression:
    """Online logistic regression with SGD, L2 regularization, and LR decay."""

    def __init__(self):
        self.weights = [0.0] * N_FEATURES
        self.bias = 0.0
        self.step = 0
        self.recent_preds = deque(maxlen=AUC_WINDOW)
        self.weight_history = []  # snapshots every 100 steps

    def _lr(self):
        """Current learning rate with decay."""
        return INITIAL_LR / (1.0 + LR_DECAY * self.step)

    def predict(self, features):
        """Compute P(win) for a feature vector."""
        z = self.bias
        for w, x in zip(self.weights, features):
            z += w * x
        return _sigmoid(z)

    def update(self, features, label):
        """SGD update for one sample.

        label: 1 = win, 0 = loss
        """
        pred = self.predict(features)
        error = pred - label  # gradient of log loss
        lr = self._lr()

        # Update weights with L2 regularization
        for i in range(N_FEATURES):
            grad = error * features[i] + L2_LAMBDA * self.weights[i]
            self.weights[i] -= lr * grad

        # Update bias (no regularization on bias)
        self.bias -= lr * error

        self.step += 1

        # Track for AUC
        self.recent_preds.append((pred, label))

        # Snapshot weight history every 100 steps
        if self.step % 100 == 0:
            self.weight_history.append({
                "step": self.step,
                "weights": list(self.weights),
                "bias": self.bias,
                "lr": lr,
                "auc": self.get_auc(),
            })

    def get_auc(self):
        """Get rolling AUC on recent predictions."""
        if len(self.recent_preds) < 10:
            return 0.5
        return _compute_rolling_auc(list(self.recent_preds))

    def to_dict(self):
        """Serialize state."""
        return {
            "weights": {name: round(w, 6) for name, w in zip(FEATURE_NAMES, self.weights)},
            "weights_raw": [round(w, 6) for w in self.weights],
            "bias": round(self.bias, 6),
            "step": self.step,
            "learning_rate": round(self._lr(), 6),
            "rolling_auc": round(self.get_auc(), 4),
            "weight_history": self.weight_history[-20:],  # last 20 snapshots
        }


def run():
    """Main entry point."""
    print("=" * 60)
    print("  ONLINE SCORER — Streaming Logistic Regression")
    print("=" * 60)

    payload = _load_payload()
    if not payload:
        print("[online_scorer] No payload data. Exiting.")
        return

    # Detect regime
    _detect_regime(payload)

    # ── 1. Load closed picks ──────────────────────────────────────
    closed_picks = payload.get("picks", {}).get("recent_closed", [])
    active_picks = payload.get("picks", {}).get("active", [])

    print(f"[online_scorer] Loaded {len(closed_picks)} closed picks, {len(active_picks)} active picks")

    if not closed_picks:
        print("[online_scorer] No closed picks to train on. Exiting.")
        return

    # ── 2. Sort closed picks chronologically ──────────────────────
    def _sort_key(p):
        ts = p.get("closed_at") or p.get("timestamp") or ""
        return ts

    closed_picks.sort(key=_sort_key)

    # ── 3. Find max score for normalization ───────────────────────
    all_scores = [p.get("score", 0) or 0 for p in closed_picks + active_picks]
    max_score = max(all_scores) if all_scores else 100.0
    if max_score <= 0:
        max_score = 100.0

    # ── 4. Online training: process each pick one at a time ───────
    model = OnlineLogisticRegression()
    trained = 0
    skipped = 0

    for pick in closed_picks:
        label = _pick_is_win(pick)
        if label is None:
            skipped += 1
            continue

        features = _extract_features(pick, max_score=max_score)
        model.update(features, label)
        trained += 1

    print(f"[online_scorer] Trained on {trained} picks (skipped {skipped} indeterminate)")
    print(f"[online_scorer] Final rolling AUC (last {AUC_WINDOW}): {model.get_auc():.4f}")
    print(f"[online_scorer] Step: {model.step}, LR: {model._lr():.6f}")

    # ── 5. Feature importance analysis ────────────────────────────
    print()
    print("-" * 60)
    print("  FEATURE WEIGHTS (what predicts wins vs losses)")
    print("-" * 60)

    weight_pairs = list(zip(FEATURE_NAMES, model.weights))
    weight_pairs.sort(key=lambda x: -x[1])

    print()
    print("  TOP POSITIVE (predicts WINS):")
    for name, w in weight_pairs:
        if w > 0:
            bar = "+" * min(int(abs(w) * 50), 40)
            print(f"    {name:22s} {w:+.4f}  {bar}")

    print()
    print("  TOP NEGATIVE (predicts LOSSES):")
    for name, w in reversed(weight_pairs):
        if w < 0:
            bar = "-" * min(int(abs(w) * 50), 40)
            print(f"    {name:22s} {w:+.4f}  {bar}")

    print(f"\n  Bias: {model.bias:+.4f}")
    print("-" * 60)

    # ── 6. Score active picks ─────────────────────────────────────
    predictions = []
    warned = 0
    recommended = 0

    for pick in active_picks:
        features = _extract_features(pick, max_score=max_score)
        p_win = model.predict(features)

        flag = None
        if p_win < 0.35:
            flag = "online_learner_warns"
            warned += 1
        elif p_win > 0.65:
            flag = "online_learner_recommends"
            recommended += 1

        pred = {
            "symbol": pick.get("symbol", ""),
            "direction": pick.get("direction", ""),
            "strategy": pick.get("strategy", ""),
            "source_system": pick.get("source_system", ""),
            "current_score": pick.get("score", 0),
            "p_win": round(p_win, 4),
            "flag": flag,
            "features": {name: round(v, 4) for name, v in zip(FEATURE_NAMES, features)},
        }
        predictions.append(pred)

    # Sort by P(win) descending
    predictions.sort(key=lambda x: -x["p_win"])

    # ── 7. Compare rankings ──────────────────────────────────────
    print()
    print("-" * 60)
    print("  ACTIVE PICKS SCORING")
    print("-" * 60)
    print(f"  Total active: {len(predictions)}")
    print(f"  Recommended (P(win) > 0.65): {recommended}")
    print(f"  Warned (P(win) < 0.35): {warned}")

    if predictions:
        print()
        print("  TOP 10 by P(win):")
        for p in predictions[:10]:
            flag_str = f" [{p['flag']}]" if p["flag"] else ""
            print(
                f"    {p['symbol']:12s} {p['direction']:5s} | "
                f"Score={p['current_score']:3.0f} P(win)={p['p_win']:.3f}{flag_str}"
            )

        print()
        print("  BOTTOM 10 by P(win):")
        for p in predictions[-10:]:
            flag_str = f" [{p['flag']}]" if p["flag"] else ""
            print(
                f"    {p['symbol']:12s} {p['direction']:5s} | "
                f"Score={p['current_score']:3.0f} P(win)={p['p_win']:.3f}{flag_str}"
            )

    # ── 8. Rank divergence: score rank vs P(win) rank ────────────
    score_ranked = sorted(predictions, key=lambda x: -(x["current_score"] or 0))
    pwin_ranked = predictions  # already sorted by p_win desc

    score_rank_map = {p["symbol"] + p["direction"] + p["strategy"]: i for i, p in enumerate(score_ranked)}
    pwin_rank_map = {p["symbol"] + p["direction"] + p["strategy"]: i for i, p in enumerate(pwin_ranked)}

    divergences = []
    for key in score_rank_map:
        s_rank = score_rank_map[key]
        p_rank = pwin_rank_map.get(key, s_rank)
        diff = s_rank - p_rank  # positive = online learner ranks higher
        divergences.append((key, diff, s_rank, p_rank))

    divergences.sort(key=lambda x: -abs(x[1]))

    if divergences:
        print()
        print("  BIGGEST RANK DIVERGENCES (score rank vs P(win) rank):")
        for key, diff, s_rank, p_rank in divergences[:5]:
            direction_str = "OVERRATED by score" if diff > 0 else "UNDERRATED by score"
            print(f"    {key[:30]:30s} | Score#{s_rank+1} vs P(win)#{p_rank+1} | {direction_str}")

    print("-" * 60)

    # ── 9. Save outputs ──────────────────────────────────────────
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    weights_output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": model.to_dict(),
        "training_stats": {
            "total_closed": len(closed_picks),
            "trained_on": trained,
            "skipped": skipped,
            "final_auc": round(model.get_auc(), 4),
        },
    }
    with open(WEIGHTS_PATH, "w", encoding="utf-8") as f:
        json.dump(weights_output, f, indent=2, default=str)
    print(f"\n[online_scorer] Weights saved to {WEIGHTS_PATH}")

    predictions_output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_active": len(predictions),
        "recommended_count": recommended,
        "warned_count": warned,
        "predictions": predictions,
    }
    with open(PREDICTIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(predictions_output, f, indent=2, default=str)
    print(f"[online_scorer] Predictions saved to {PREDICTIONS_PATH}")


if __name__ == "__main__":
    run()
