import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.backfill_volume_ratio import volume_ratio  # noqa: E402


def test_ratio_is_entry_volume_over_prior_median():
    vols = [100.0] * 20 + [200.0]
    assert volume_ratio(vols, 20) == 2.0


def test_ratio_is_none_without_enough_history():
    assert volume_ratio([100.0] * 19 + [200.0], 19) is None


def test_ratio_is_none_on_zero_or_missing_volume():
    vols = [100.0] * 20 + [0.0]
    assert volume_ratio(vols, 20) is None
    vols2 = [100.0] * 20 + [None]
    assert volume_ratio(vols2, 20) is None


def test_ratio_ignores_zero_volume_bars_in_the_median_window():
    # A zero-volume bar inside the window is dropped, so the window then holds
    # only 19 valid bars -> not enough history.
    vols = [0.0] + [100.0] * 19 + [300.0]
    assert volume_ratio(vols, 20) is None
    # With a full 20 valid bars before the entry, the ratio is exact.
    vols2 = [0.0] * 3 + [100.0] * 20 + [300.0]
    assert volume_ratio(vols2, 23) == 3.0


def test_ratio_is_robust_to_a_single_spike_in_the_window():
    vols = [100.0] * 19 + [10000.0] + [100.0]
    # median of the prior 20 is 100 (one spike does not move a median)
    assert volume_ratio(vols, 20) == 1.0
