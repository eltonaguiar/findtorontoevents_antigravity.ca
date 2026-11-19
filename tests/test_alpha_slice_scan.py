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
    recs = []
    for i in range(40):                      # POSITION beats hold by +2%/pick
        recs.append({"class": "CRYPTO", "dir": "LONG", "timeframe": "POSITION",
                     "alpha": 2.0 + (0.1 if i % 2 else -0.1)})
    for i in range(400):                     # INTRADAY is symmetric noise
        recs.append({"class": "CRYPTO", "dir": "LONG", "timeframe": "INTRADAY",
                     "alpha": 0.02 if i % 2 else -0.02})
    res = scan(recs, min_n=30)
    by = {r["slice"]: r for r in res["slices"]}
    assert by["tf:POSITION"]["survives"] is True
    assert by["class:CRYPTO"]["survives"] is False
    # per_class only rolls up class-scoped slices ('class_...:'), never a bare
    # 'tf:' slice, so the class view must report its own class-scoped survivor.
    assert res["per_class"]["CRYPTO"]["best_surviving_slice"] == "class_tf:CRYPTO/POSITION"


def test_harmful_slice_is_flagged_not_cherry_picked():
    recs = [{"class": "ETF", "dir": "LONG", "timeframe": "INTRADAY",
             "alpha": -0.3 - (0.05 if i % 2 else 0.0)} for i in range(60)]
    res = scan(recs, min_n=30)
    by = {r["slice"]: r for r in res["slices"]}
    assert by["tf:INTRADAY"]["hurts"] is True
    assert by["tf:INTRADAY"]["survives"] is False
