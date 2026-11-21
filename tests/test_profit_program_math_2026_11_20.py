"""Trial counter (P0.5), entry-regime stamping, corrected cost gate."""
import json

import pytest

from alpha_engine import cost_gate, entry_regime, trial_counter


def test_captured_fraction_is_60pct_at_standard_calibration():
    assert cost_gate.captured_fraction(1.25, 0.5) == pytest.approx(0.60, abs=1e-9)
    assert cost_gate.captured_fraction(1.0, 0.5) == pytest.approx(0.50, abs=1e-9)
    assert cost_gate.captured_fraction(0.5, 0.5) == 0.0
    assert cost_gate.captured_fraction(0, 0.5) == 0.0


def test_full_reversion_overstates_the_margin_by_two_thirds():
    sigma = 0.02                        # 2% sigma_eq (a fraction), 20 bps round trip
    full = abs(1.25) * sigma * 10_000.0  # the old, wrong comparison, in bps
    captured = cost_gate.captured_edge_bps(1.25, sigma, 0.5)
    assert captured == pytest.approx(full * 0.60, rel=1e-9)
    assert full / captured == pytest.approx(1.6667, abs=1e-3)


def test_should_trade_boundary():
    assert cost_gate.should_trade(1.25, 0.02, 20.0)["trade"] is True   # 150 bps vs 40
    assert cost_gate.should_trade(1.25, 0.001, 20.0)["trade"] is False  # 7.5 bps vs 40
    assert cost_gate.should_trade(1.25, 0.001, 20.0)["required_bps"] == 40.0


def test_regime_uses_only_past_bars():
    closes = [100 + i for i in range(260)]
    r = entry_regime.classify_regime(closes, 250)
    assert r["regime_trend"] == "up"
    assert r["regime_bars_available"] == 251
    # appending future bars must not change a past classification
    later = entry_regime.classify_regime(closes + [1, 2, 3], 250)
    assert later == r


def test_regime_detects_downtrend_and_stamps():
    closes = [200 - i for i in range(260)]
    r = entry_regime.classify_regime(closes, 255)
    assert r["regime_trend"] == "down"
    picked = entry_regime.stamp_regime_at_entry({"id": "x"}, closes, 255)
    assert picked["entry_regime_stamped"] is True
    assert picked["at_entry_regime_label"].startswith("down/")
    assert "id" in picked


def test_regime_rejects_bad_index():
    with pytest.raises(IndexError):
        entry_regime.classify_regime([1.0, 2.0], 5)


def test_trial_counter_never_lowers_the_estimate(tmp_path):
    p = tmp_path / "tc.json"
    trial_counter.record(658, "GLOBAL", path=p)
    trial_counter.record(12, "CRYPTO", path=p)
    # local run says 3 trials; global says 670 -> 670 wins
    assert trial_counter.effective_n_trials(3, "GLOBAL", path=p) == 670
    # a family count is also respected
    assert trial_counter.effective_n_trials(1, "CRYPTO", path=p) == 670
    data = json.loads(p.read_text())
    assert data["total"] == 670
    assert data["families"]["CRYPTO"] == 12


def test_trial_counter_missing_file_is_safe(tmp_path):
    assert trial_counter.effective_n_trials(5, "GLOBAL", path=tmp_path / "nope.json") == 5
    assert trial_counter.effective_n_trials(None, "GLOBAL", path=tmp_path / "nope.json") == 1


def test_dsr_gate_uses_the_class_trial_count():
    """P0.5: the gate must correct for every system tested in the class, not 1."""
    from alpha_engine.money_ready_verdict import NB_TRIALS_BY_CLASS, _dsr_gate

    rets = [0.004, -0.002, 0.006] * 40
    gated = _dsr_gate(rets, asset_class="CRYPTO")
    assert gated["nb_trials"] >= NB_TRIALS_BY_CLASS["CRYPTO"]
    assert gated["nb_trials"] > 1
    # 2026-11-21: an unmapped class is an explicit SKIP, not a silent 1. The old
    # assertion (nb_trials >= 1) encoded the pre-P0.5 behaviour where an unknown
    # class deflated by a single trial -- zero multiple-testing correction
    # reported as a usable number. A missing baseline must fail closed instead.
    unknown = _dsr_gate(rets, asset_class="NOPE")
    assert unknown["ok"] is None
    assert unknown["skipped"] is True
    assert unknown["nb_trials"] is None


def test_dsr_gate_correction_is_monotone_conservative():
    """More trials can only lower DSR, never raise it."""
    from alpha_engine.money_ready_verdict import _dsr_gate

    rets = [0.004, -0.002, 0.006] * 40
    low = _dsr_gate(rets, asset_class="COMMODITY")   # 3 trials
    high = _dsr_gate(rets, asset_class="CRYPTO")     # 14 trials
    assert high["nb_trials"] > low["nb_trials"]
    if low["dsr_score"] is not None and high["dsr_score"] is not None:
        assert high["dsr_score"] <= low["dsr_score"] + 1e-12
