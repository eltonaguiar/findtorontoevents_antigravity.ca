"""Unit tests for the at_signal_outcomes insert-volume monitor grading.

The grading is the un-mask layer that turns the resolver job RED when the honest
ledger's insert volume collapses (the 2026-06-12..06-18 green-on-empty freeze).
These pin the thresholds against the real-baseline vectors.
"""
from tools.at_signal_outcomes_volume_check import grade


def test_exact_freeze_signature_is_red():
    # 06-13..06-18: 0 inserts while a normal day is ~5338 -> hard RED, exit 1
    status, ratio, code = grade(0, 5338)
    assert status == "RED" and code == 1 and ratio == 0.0


def test_trickle_is_red():
    # 06-19 trickle: 15 inserts vs 5338 median -> ratio 0.003 < 0.10 -> RED
    status, _, code = grade(15, 5338)
    assert status == "RED" and code == 1


def test_healthy_day_is_green():
    status, _, code = grade(5000, 5338)
    assert status == "GREEN" and code == 0


def test_low_but_healthy_is_green():
    # 0.40 floor: a genuine quiet-but-fine day must not false-alarm
    status, _, code = grade(2200, 5338)  # ratio ~0.41
    assert status == "GREEN" and code == 0


def test_degraded_is_yellow_not_fatal():
    # 0.10 <= ratio < 0.40 -> YELLOW warning, exit 0 (non-fatal)
    status, ratio, code = grade(1000, 5338)  # ratio ~0.187
    assert status == "YELLOW" and code == 0 and 0.10 <= ratio < 0.40


def test_zero_on_quiet_table_still_red_via_ratio():
    # today==0 but median<50 (not the hard-RED branch): ratio 0.0 < 0.10 -> still RED
    status, _, code = grade(0, 10)
    assert status == "RED" and code == 1


def test_quiet_table_nonzero_does_not_false_alarm():
    # a small table inserting at its normal low rate is GREEN (ratio>=0.40)
    status, _, code = grade(8, 10)
    assert status == "GREEN" and code == 0


def test_median_one_floor_no_div_zero():
    # empty baseline -> max(median,1) guard; any positive today is GREEN
    status, _, code = grade(5, 0)
    assert code == 0
