"""Tests for audit_trail.hf_policy_thresholds (HF approved thresholds A–G constants)."""

from audit_trail.hf_policy_thresholds import (
    DECAY_HARD_GAP_PERCENTAGE_POINTS,
    DECAY_HARD_MIN_CLOSED_TRADES,
    decay_hard_gate_triggers,
    normalize_wr_percent,
)


def test_normalize_ratio_to_percent():
    assert normalize_wr_percent(0.62) == 62.0
    assert normalize_wr_percent(0.0) == 0.0
    assert normalize_wr_percent(1.0) == 100.0


def test_normalize_already_percent():
    assert normalize_wr_percent(62.5) == 62.5
    assert normalize_wr_percent(100.0) == 100.0


def test_normalize_none():
    assert normalize_wr_percent(None) is None


def test_decay_gate_not_enough_trades():
    assert decay_hard_gate_triggers(70.0, 0.50, 19) is False


def test_decay_gate_missing_bt():
    assert decay_hard_gate_triggers(None, 0.50, 25) is False


def test_decay_gate_missing_fwd():
    assert decay_hard_gate_triggers(70.0, None, 25) is False


def test_decay_gate_triggers_15pp_gap():
    # BT 70%, FWD 54% ratio -> 54% — gap 16pp >= 15
    assert decay_hard_gate_triggers(70.0, 0.54, 20) is True


def test_decay_gate_no_trigger_below_gap():
    # BT 70%, FWD 56% — gap 14pp
    assert decay_hard_gate_triggers(70.0, 0.56, 20) is False


def test_decay_gate_boundary_exactly_15pp():
    # fwd 55%, bt 70% -> gap 15pp, policy is strict < (bt - 15) => 55 < 55 is False
    assert decay_hard_gate_triggers(70.0, 0.55, 20) is False
    assert decay_hard_gate_triggers(70.0, 0.549, 20) is True


def test_constants_match_hf_doc():
    assert DECAY_HARD_GAP_PERCENTAGE_POINTS == 15.0
    assert DECAY_HARD_MIN_CLOSED_TRADES == 20
