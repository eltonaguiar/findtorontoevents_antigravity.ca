"""Unit tests for record_raw_pick's absurd-barrier sanity clamp.

Some emitters (alpha_engine CRYPTO, n=86) shipped stops ~17x from entry (avg 1712%
distance) — unreachable, forcing TIME_EXIT and polluting ~19% of the honest CRYPTO
TIME_EXIT cohort. The clamp bounds barriers > 50% from entry to a per-class sane max.
"""
from audit_trail.recorder import _sanity_clamp_barriers


def test_absurd_long_sl_clamped_to_class_max():
    # CRYPTO LONG entry 100, SL at 0.5 (99.5% away — like the 1712% garbage) -> clamp to 8%
    tp, sl, slc, tpc = _sanity_clamp_barriers(100.0, 103.0, 0.5, "LONG", "CRYPTO")
    assert slc is True and tpc is False
    assert abs(sl - 92.0) < 1e-6   # 100 * (1 - 8/100)
    assert tp == 103.0             # 3% TP is sane, untouched


def test_normal_pick_untouched():
    # CRYPTO LONG with sane 5% SL / 3% TP -> nothing clamped
    tp, sl, slc, tpc = _sanity_clamp_barriers(100.0, 103.0, 95.0, "LONG", "CRYPTO")
    assert slc is False and tpc is False
    assert (tp, sl) == (103.0, 95.0)


def test_absurd_short_sl_clamped_up():
    # SHORT entry 100, SL 300 (200% away) -> clamp to entry*(1+8/100)=108
    tp, sl, slc, tpc = _sanity_clamp_barriers(100.0, 97.0, 300.0, "SHORT", "CRYPTO")
    assert slc is True and abs(sl - 108.0) < 1e-6


def test_absurd_tp_also_clamped():
    tp, sl, slc, tpc = _sanity_clamp_barriers(100.0, 5000.0, 95.0, "LONG", "CRYPTO")
    assert tpc is True and abs(tp - 115.0) < 1e-6  # 100*(1+15/100)


def test_equity_uses_tighter_cap():
    # EQUITY max SL 5% -> absurd SL clamps to 95
    tp, sl, slc, tpc = _sanity_clamp_barriers(100.0, 104.0, 1.0, "LONG", "EQUITY")
    assert slc is True and abs(sl - 95.0) < 1e-6


def test_zero_entry_is_noop():
    tp, sl, slc, tpc = _sanity_clamp_barriers(0.0, 50.0, 0.1, "LONG", "CRYPTO")
    assert (tp, sl, slc, tpc) == (50.0, 0.1, False, False)


def test_unknown_class_uses_default():
    # default (5,3); absurd SL on entry 100 LONG -> 97
    tp, sl, slc, tpc = _sanity_clamp_barriers(100.0, 104.0, 1.0, "LONG", "WEIRD")
    assert slc is True and abs(sl - 97.0) < 1e-6


def test_never_raises_on_bad_input():
    # defensive: garbage input must not raise (returns inputs unchanged)
    tp, sl, slc, tpc = _sanity_clamp_barriers(100.0, None, "bad", "LONG", "CRYPTO")
    assert slc is False and tpc is False
