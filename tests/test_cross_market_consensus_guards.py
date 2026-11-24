"""Guards for cross_market_consensus signal extraction.

2026-11-16 audit: a probability outside [0, 1] is an impossible odds feed and
must be dropped, not fed into the weighted consensus.
"""
from prediction_market_agents import cross_market_consensus as cmc


def test_valid_confidence_kept():
    sigs = cmc._extract_signals(
        [{"symbol": "BTCUSDT", "direction": "LONG", "confidence": 0.72}],
        "unit_test",
    )
    assert len(sigs) == 1
    assert sigs[0]["confidence"] == 0.72


def test_percentage_confidence_normalized():
    sigs = cmc._extract_signals(
        [{"symbol": "BTCUSDT", "direction": "LONG", "confidence": 72}],
        "unit_test",
    )
    assert len(sigs) == 1
    assert abs(sigs[0]["confidence"] - 0.72) < 1e-9


def test_negative_confidence_dropped():
    sigs = cmc._extract_signals(
        [{"symbol": "BTCUSDT", "direction": "LONG", "confidence": -0.3}],
        "unit_test",
    )
    assert sigs == []


def test_impossible_confidence_dropped():
    # 500 -> /100 = 5.0, still impossible
    sigs = cmc._extract_signals(
        [{"symbol": "BTCUSDT", "direction": "SHORT", "confidence": 500}],
        "unit_test",
    )
    assert sigs == []


def test_boundary_confidences_kept():
    sigs = cmc._extract_signals(
        [
            {"symbol": "BTCUSDT", "direction": "LONG", "confidence": 0.0},
            {"symbol": "ETHUSDT", "direction": "LONG", "confidence": 1.0},
        ],
        "unit_test",
    )
    assert len(sigs) == 2
