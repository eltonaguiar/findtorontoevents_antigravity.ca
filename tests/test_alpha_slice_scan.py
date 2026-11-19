"""Slice scan must be conservative: no survivors from noise, no class mixing."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from alpha_slice_scan import _bh, _class_of, _exit_bucket, scan  # noqa: E402


def test_class_attribution_ignores_non_class_slices():
    assert _class_of("class:CRYPTO") == "CRYPTO"
    assert _class_of("class_dir:CRYPTO/SHORT") == "CRYPTO"
    assert _class_of("class_tf:CRYPTO/POSITION") == "CRYPTO"
    assert _class_of("class_dir_exit:TP:EQUITY/LONG") == "EQUITY"
    # a strategy slice that happens to mention a class must not be attributed to it
    assert _class_of("strategy:luxalgo_confluence") is None
    assert _class_of("tf:POSITION") is None


def test_exit_buckets_are_explicit():
    assert _exit_bucket("take profit hit") == "exit:TP"
    assert _exit_bucket("stop loss") == "exit:SL"
    assert _exit_bucket("expired") == "exit:TIME"
    assert _exit_bucket("manual") == "exit:OTHER"
    assert _exit_bucket("") == "exit:NONE"


def test_bh_values_are_bounded_and_monotone_in_p():
    q = _bh([0.001, 0.02, 0.5, 0.9])
    assert all(0.0 <= v <= 1.0 for v in q)
    assert q[0] <= q[1] <= q[2] <= q[3]


def test_noise_does_not_survive_but_a_real_edge_does():
    """A pure-noise class must not survive; a real edge must.

    The edge is planted in CRYPTO and the noise in ETF on purpose: an earlier
    version of this fixture planted the edge inside CRYPTO and then asserted
    that `class:CRYPTO` must NOT survive, which is wrong — a class that contains
    a real +2%/pick cohort is supposed to come out positive. The "noise stays
    noise" assertion needs a class made only of noise.
    """
    recs = []
    for i in range(40):                      # real edge: +2%/pick, tight
        recs.append({"class": "CRYPTO", "dir": "LONG", "timeframe": "POSITION",
                     "alpha": 2.0 + (0.1 if i % 2 else -0.1)})
    for i in range(400):                     # symmetric noise, zero mean
        recs.append({"class": "ETF", "dir": "LONG", "timeframe": "INTRADAY",
                     "alpha": 0.02 if i % 2 else -0.02})
    res = scan(recs, min_n=30)
    by = {r["slice"]: r for r in res["slices"]}

    assert by["tf:POSITION"]["survives"] is True
    assert by["class:ETF"]["survives"] is False          # noise stays noise
    assert by["class_dir:ETF/LONG"]["survives"] is False
    assert by["class:ETF"]["hurts"] is False             # and is not called harmful
    # per_class only rolls up class-scoped slices, never a bare 'tf:' slice, and
    # it must surface the class's surviving edge. Assert the *value*, not one tied
    # slice name: class:CRYPTO and class_tf:CRYPTO/POSITION both sit at +2.000, so
    # the winning name depends on sort order and is not a stable contract.
    assert res["per_class"]["CRYPTO"]["best_surviving_slice"].startswith("class")
    assert res["per_class"]["CRYPTO"]["best_slice_alpha_pct"] == 2.0
    assert res["per_class"]["ETF"]["best_surviving_slice"] is None


def test_harmful_slice_is_flagged_not_cherry_picked():
    recs = [{"class": "ETF", "dir": "LONG", "timeframe": "INTRADAY",
             "alpha": -0.3 - (0.05 if i % 2 else 0.0)} for i in range(60)]
    res = scan(recs, min_n=30)
    by = {r["slice"]: r for r in res["slices"]}
    assert by["tf:INTRADAY"]["hurts"] is True
    assert by["tf:INTRADAY"]["survives"] is False
