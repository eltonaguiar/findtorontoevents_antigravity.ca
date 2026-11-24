import os
import re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN = os.path.join(HERE, "audit_trail", "dashboard_generator.py")


def _src():
    with open(GEN, encoding="utf-8") as fh:
        return fh.read()


def test_imports_the_shaper():
    assert "coverage_excluded_summary" in _src()


def test_payload_carries_a_coverage_key():
    src = _src()
    # The key must appear as a payload-level literal, not only inside summary.
    assert re.search(r'^\s{8}"coverage": \{', src, re.M), \
        "no top-level coverage block in the payload literal"


def test_coverage_block_is_fed_the_auto_expired_list():
    src = _src()
    assert "coverage_excluded_summary(auto_expired)" in src, \
        "coverage block is not wired to the auto_expired cohort"


def test_auto_expired_is_built_before_the_payload():
    src = _src()
    build_at = src.index("auto_expired.append(p)")
    payload_at = src.index('"coverage": {')
    assert build_at < payload_at, "auto_expired built after payload; out of scope"
