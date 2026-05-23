"""
Mercury #5: Simple Winner Model — empirical bucket-based win-rate predictor.
Mercury #6: Copy-Trader Quality Scoring — composite quality score for traders.

Stdlib only. Under 200 lines total.
"""
import json
import math
import os

# ── Paths ──────────────────────────────────────────────────────────────────
_DIR = os.path.dirname(os.path.abspath(__file__))
_DASH_DATA = os.path.join(_DIR, "..", "audit_dashboard", "data", "dashboard_data.json")
_LEADERBOARD = os.path.join(_DIR, "..", "copy_trader_intel", "data", "leaderboard.json")
_WEIGHTS_OUT = os.path.join(_DIR, "data", "winner_model_weights.json")

# ── Helpers ────────────────────────────────────────────────────────────────
def _bucket(value, edges):
    """Return bucket index for *value* given sorted *edges*."""
    for i, e in enumerate(edges):
        if value <= e:
            return i
    return len(edges)


def _clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


# ═══════════════════════════════════════════════════════════════════════════
# Item #5 — Simple Winner Model
# ═══════════════════════════════════════════════════════════════════════════

# Bucket edges for each feature (hand-picked from domain knowledge)
FEATURE_EDGES = {
    "confidence":      [0.5, 0.65, 0.8, 0.9],
    "direction":       [0.5],           # 0=LONG, 1=SHORT; single split
    "risk_reward":     [1.0, 1.5, 2.0, 3.0],
    "sl_distance_pct": [1.0, 2.0, 3.5, 5.0],
    "volume_ratio":    [0.5, 1.0, 1.5, 2.5],
}


def _extract_features(pick):
    """Return dict of 5 numeric features from a pick, or None if unusable."""
    try:
        conf = pick.get("confidence")
        if conf is None:
            return None
        direction = 0.0 if pick.get("direction", "LONG") == "LONG" else 1.0
        rr = pick.get("rr_ratio") or 1.5
        entry = pick.get("entry_price", 0)
        sl = pick.get("stop_loss", 0)
        sl_dist = abs(entry - sl) / entry * 100 if entry else 2.0
        vr = pick.get("volume_ratio")
        if vr is None:
            vr = 1.0  # default neutral
        return {
            "confidence": float(conf),
            "direction": direction,
            "risk_reward": float(rr),
            "sl_distance_pct": sl_dist,
            "volume_ratio": float(vr),
        }
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _is_winner(pick):
    """True if pick ended profitably."""
    status = (pick.get("status") or "").upper()
    if status == "WON":
        return True
    if status == "LOST":
        return False
    return (pick.get("pnl_pct") or 0) > 0


def train_winner_model(save=True):
    """Build empirical win-rate lookup from closed picks. Returns weights dict."""
    with open(_DASH_DATA, "r", encoding="utf-8") as f:
        data = json.load(f)

    closed = data.get("picks", {}).get("recent_closed", [])
    closed = closed[-2000:]  # last 2000

    # accumulators: feature -> bucket_idx -> [wins, total]
    buckets = {}
    for feat, edges in FEATURE_EDGES.items():
        buckets[feat] = {i: [0, 0] for i in range(len(edges) + 1)}

    for pick in closed:
        feats = _extract_features(pick)
        if feats is None:
            continue
        win = 1 if _is_winner(pick) else 0
        for feat, edges in FEATURE_EDGES.items():
            b = _bucket(feats[feat], edges)
            buckets[feat][b][0] += win
            buckets[feat][b][1] += 1

    # Convert to win-rate lookup
    weights = {}
    for feat, bmap in buckets.items():
        weights[feat] = {}
        for b, (w, t) in bmap.items():
            weights[feat][str(b)] = round(w / t, 4) if t >= 5 else 0.5
    weights["_global_wr"] = round(
        sum(1 for p in closed if _is_winner(p)) / max(len(closed), 1), 4
    )

    if save:
        os.makedirs(os.path.dirname(_WEIGHTS_OUT), exist_ok=True)
        with open(_WEIGHTS_OUT, "w", encoding="utf-8") as f:
            json.dump(weights, f, indent=2)
    return weights


def load_weights():
    with open(_WEIGHTS_OUT, "r", encoding="utf-8") as f:
        return json.load(f)


def predict_winner(pick, weights=None):
    """Return 0-1 probability that *pick* is a winner."""
    if weights is None:
        weights = load_weights()

    feats = _extract_features(pick)
    if feats is None:
        return weights.get("_global_wr", 0.5)

    # Average the per-feature bucket win rates
    rates = []
    for feat, edges in FEATURE_EDGES.items():
        b = str(_bucket(feats[feat], edges))
        rates.append(weights.get(feat, {}).get(b, 0.5))

    return _clamp(sum(rates) / len(rates))


# ═══════════════════════════════════════════════════════════════════════════
# Item #6 — Copy-Trader / Strategy-Variant Quality Scoring
# ═══════════════════════════════════════════════════════════════════════════

def compute_trader_quality(trader_data):
    """
    Score a trader/strategy-variant on 0-100 scale.

    *trader_data* should be a dict with a 'metrics' sub-dict containing:
        win_rate (0-100), profit_factor (float), max_drawdown_pct (float),
        sharpe_ratio (float, optional).

    Components:
        - Consistency  (low drawdown)     : 30 pts
        - Win rate                        : 40 pts
        - Profit factor                   : 30 pts
    """
    m = trader_data.get("metrics", trader_data)  # accept flat or nested

    # Win rate (0-100 scale in data) → 0-40 pts
    wr = float(m.get("win_rate", 50))
    wr_score = _clamp(wr / 100, 0, 1) * 40

    # Profit factor → 0-30 pts (cap at 5)
    pf = float(m.get("profit_factor", 1.0))
    pf_score = _clamp(pf / 5, 0, 1) * 30

    # Consistency: inverse of max drawdown % → 0-30 pts
    # 0% dd = perfect (30), 20%+ dd = 0
    dd = float(m.get("max_drawdown_pct", 10))
    dd_score = _clamp(1 - dd / 20, 0, 1) * 30

    return round(wr_score + pf_score + dd_score, 1)


# ── CLI entry point ───────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Training winner model...")
    w = train_winner_model(save=True)
    print(f"Saved weights to {_WEIGHTS_OUT}")
    print(f"Global win rate: {w['_global_wr']}")

    print("\nScoring leaderboard traders...")
    with open(_LEADERBOARD, "r", encoding="utf-8") as f:
        lb = json.load(f)
    for entry in lb.get("leaderboard", [])[:5]:
        score = compute_trader_quality(entry)
        print(f"  {entry['variant_name'][:50]:50s}  quality={score:5.1f}")
