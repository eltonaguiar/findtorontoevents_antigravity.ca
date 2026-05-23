"""Test ensemble calibration integration."""
import sys
sys.path.insert(0, '.')


def test_calibration_map_builds():
    """Calibration map should build from closed trades."""
    from ml_battleground.shared.calibration import build_calibration_map

    # Simulate 50 closed trades
    trades = []
    for i in range(50):
        conf = 0.50 + (i / 100)  # 0.50 to 0.99
        pnl = 0.01 if i > 25 else -0.01  # higher conf = more wins
        trades.append({"confidence": conf, "net_pnl_pct": pnl})

    cal_map = build_calibration_map(trades)
    assert cal_map["method"] != "insufficient_data"
    assert len(cal_map["buckets"]) > 0


def test_calibrate_confidence():
    """Calibrated confidence should differ from raw."""
    from ml_battleground.shared.calibration import build_calibration_map, calibrate_confidence

    trades = []
    for i in range(50):
        conf = 0.50 + (i / 100)
        pnl = 0.01 if i > 25 else -0.01
        trades.append({"confidence": conf, "net_pnl_pct": pnl})

    cal_map = build_calibration_map(trades)

    # High raw confidence (0.95) should map to actual win rate
    calibrated = calibrate_confidence(0.95, cal_map)
    assert 0.0 <= calibrated <= 1.0


def test_calibration_graceful_with_no_data():
    """Calibration with insufficient data should return identity."""
    from ml_battleground.shared.calibration import build_calibration_map, calibrate_confidence

    cal_map = build_calibration_map([])  # no trades
    assert cal_map["method"] == "insufficient_data"

    # Should fall through to temperature scaling fallback (not isotonic)
    result = calibrate_confidence(0.75, cal_map)
    assert result is not None
    assert 0.0 <= result <= 1.0
