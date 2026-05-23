"""CI assertions for ML feature contract — prevents drift between FEATURES list and feat array.

Catches the most common source of silent model breakage:
- Adding a feature to FEATURES but forgetting the corresponding line in _signal_to_features()
- Removing a feature from _signal_to_features() but forgetting to update FEATURES
- Accidentally re-adding a LEAKY feature to FEATURES
- Duplicate feature names (causes silent column misalignment)
"""

import json
from pathlib import Path

import sys

import pytest

# alpha_engine submodules use bare imports (e.g. `from config import DATA_DIR`)
# so we must put alpha_engine/ itself on sys.path, not just the project root.
_AE = str(Path(__file__).resolve().parent.parent / "alpha_engine")
if _AE not in sys.path:
    sys.path.insert(0, _AE)

from alpha_engine.ml_ranker import MLSignalRanker


# ---------------------------------------------------------------------------
# Minimal signal fixture — enough fields to exercise _signal_to_features()
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_signal():
    return {
        "strategy": "vt_ichimoku_cloud",
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "confidence": 0.75,
        "risk_reward": 2.5,
        "entry_price": 65000,
        "take_profit": 67000,
        "stop_loss": 64000,
        "source": "live",
        "volume_ratio": 1.5,
        "market_regime": "trending",
        "timestamp": "2026-04-14T14:00:00+00:00",
    }


# ===========================================================================
# 1. Feature vector length MUST match FEATURES list length
# ===========================================================================
def test_feature_vector_length_matches_features_list(sample_signal):
    """_signal_to_features() must return an array whose length == len(FEATURES).

    If this fails, someone added/removed a feature name in FEATURES without
    adding/removing the corresponding computation in _signal_to_features().
    """
    ranker = MLSignalRanker(auto_train=False)
    feat = ranker._signal_to_features(sample_signal)
    assert feat is not None, "_signal_to_features returned None — signal may be missing required fields"
    assert len(feat) == len(ranker.FEATURES), (
        f"FEATURE DRIFT: _signal_to_features produced {len(feat)} values "
        f"but FEATURES declares {len(ranker.FEATURES)} names. "
        f"Update FEATURES or _signal_to_features to match."
    )


# ===========================================================================
# 2. No LEAKY_FEATURES may appear in FEATURES
# ===========================================================================
def test_no_leaky_features_in_features_list():
    """LEAKY_FEATURES must not overlap with FEATURES.

    This prevents accidental re-addition of a feature that was previously
    removed for causing data leakage (AUC inflation, source-proxy, etc.).
    """
    ranker = MLSignalRanker(auto_train=False)
    leaked = set(ranker.FEATURES) & ranker.LEAKY_FEATURES
    assert leaked == set(), (
        f"LEAKED features found in FEATURES list: {leaked}. "
        f"These were removed because they act as source/strategy proxies. "
        f"Do NOT re-add them without updating LEAKY_FEATURES."
    )


# ===========================================================================
# 3. FEATURES list must have no duplicates
# ===========================================================================
def test_features_list_no_duplicates():
    """FEATURES must not contain duplicate names — causes silent column misalignment."""
    ranker = MLSignalRanker(auto_train=False)
    seen = set()
    dupes = []
    for f in ranker.FEATURES:
        if f in seen:
            dupes.append(f)
        seen.add(f)
    assert dupes == [], f"Duplicate feature names in FEATURES: {dupes}"


# ===========================================================================
# 4. Feature names are in the same order as produced by _signal_to_features
#    (catches reorder bugs where name[i] no longer maps to feat[i])
# ===========================================================================
def test_feature_names_match_vector_values(sample_signal):
    """Spot-check that specific feature values land at the expected index.

    If someone reorders the feature computation inside _signal_to_features
    without updating FEATURES (or vice versa), these assertions will fire.
    """
    ranker = MLSignalRanker(auto_train=False)
    feat = ranker._signal_to_features(sample_signal)
    assert feat is not None

    # confidence is always the first feature and should be exactly 0.75
    idx = ranker.FEATURES.index("confidence")
    assert feat[idx] == pytest.approx(0.75, abs=1e-6), (
        f"confidence at index {idx} = {feat[idx]}, expected 0.75 — possible column reorder"
    )

    # direction_market_alignment: LONG with no btc_24h_change → 1.0 (graceful fallback to raw direction)
    # When btc trend data is absent, the interaction feature falls back to raw direction value
    idx = ranker.FEATURES.index("direction_market_alignment")
    assert feat[idx] == pytest.approx(1.0, abs=1e-6), (
        f"direction_market_alignment at index {idx} = {feat[idx]}, expected 1.0 for LONG with no btc_trend (graceful fallback)"
    )

    # volume_ratio: signal has volume_ratio=1.5, normalized to [0,1]
    idx = ranker.FEATURES.index("volume_ratio")
    assert feat[idx] != pytest.approx(0.0, abs=1e-6), (
        f"volume_ratio at index {idx} = {feat[idx]}, expected non-zero — possible column reorder"
    )


# ===========================================================================
# 5. Closed-picks feature consistency (if data file exists)
# ===========================================================================
@pytest.mark.slow
def test_closed_picks_feature_vectors_match_features_list():
    """Every closed pick that yields a feature vector must have length == len(FEATURES).

    This catches real-world drift that the single sample_signal test might miss
    (e.g. a feature that only populates for quan_engine picks).
    """
    data_path = Path("alpha_engine/data/closed_picks.json")
    if not data_path.exists():
        pytest.skip("closed_picks.json not found — skip real-data consistency check")

    picks = json.loads(data_path.read_text(encoding="utf-8"))
    if not picks:
        pytest.skip("closed_picks.json is empty")

    ranker = MLSignalRanker(auto_train=False)
    mismatches = []
    checked = 0

    for p in picks:
        feat = ranker._signal_to_features(p)
        if feat is None:
            continue
        checked += 1
        if len(feat) != len(ranker.FEATURES):
            mismatches.append({
                "strategy": p.get("strategy", "?"),
                "source": p.get("source", "?"),
                "got": len(feat),
                "expected": len(ranker.FEATURES),
            })

    assert mismatches == [], (
        f"Feature length mismatches in {len(mismatches)}/{checked} closed picks: {mismatches[:5]}"
    )
