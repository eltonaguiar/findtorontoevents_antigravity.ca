"""Keep the mirrored ladder constants in step with the production tribunal.

class_verdict_audit.py cannot import alpha_engine.audit3_tribunal (it pulls in
the whole scoring stack), so it copies the few constants the ladder needs. This
test reads the tribunal's source and fails if any copy has drifted.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import class_verdict_audit as audit  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRIBUNAL = os.path.join(HERE, "alpha_engine", "audit3_tribunal.py")

# constant name in the tribunal -> attribute mirrored in class_verdict_audit
MIRRORED = {
    "WR_MIN_N": "MIN_N",
    "HARM_PF_WATCH": "PF_KILL_FLOOR",
}


def _tribunal_value(name):
    with open(TRIBUNAL, encoding="utf-8") as fh:
        src = fh.read()
    m = re.search(rf"^{name}\s*=\s*([0-9.]+)", src, re.M)
    assert m, f"{name} not found in the tribunal source"
    return float(m.group(1))


def test_every_mirrored_constant_matches():
    drifted = []
    for theirs, ours in MIRRORED.items():
        expected = _tribunal_value(theirs)
        actual = float(getattr(audit, ours))
        if expected != actual:
            drifted.append(f"{ours}={actual} but {theirs}={expected}")
    assert not drifted, "mirror drifted: " + "; ".join(drifted)


def test_concentration_cap_matches_the_tribunal_check():
    # The tribunal compares top symbol share against the class cap inline, so we
    # only assert our value is the documented one.
    assert audit.CONCENTRATION_CAP == 0.60
