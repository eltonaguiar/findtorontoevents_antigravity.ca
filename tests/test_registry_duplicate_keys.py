"""Registry integrity: a duplicate JSON key silently shadows the earlier one.

Two H-149 edits in this repo shipped duplicate keys -- first a second "verdict"
(so status said REJECTED while result.verdict still resolved to UNTESTED), then
seven copies of "stress_net_edge_pct". Both were invisible to json.load(), which
keeps the last value and says nothing. These tests parse with object_pairs_hook
so CI fails instead of silently resolving to whichever key came last.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alpha_engine.hypothesis_status import (  # noqa: E402
    CANONICAL_STATES, normalize_status)

REGISTRY = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "reports", "hypothesis_registry.json")


def _strict(pairs):
    keys = [k for k, _ in pairs]
    dupes = sorted({k for k in keys if keys.count(k) > 1})
    if dupes:
        raise ValueError(f"duplicate keys in one object: {dupes}")
    return dict(pairs)


def _raw():
    with open(REGISTRY, encoding="utf-8") as fh:
        return fh.read()


def test_hook_rejects_a_shadowed_key():
    with pytest.raises(ValueError, match="duplicate keys"):
        json.loads('{"verdict": "REJECTED", "verdict": "UNTESTED"}',
                   object_pairs_hook=_strict)


def test_registry_parses_without_duplicate_keys():
    try:
        json.loads(_raw(), object_pairs_hook=_strict)
    except ValueError as exc:
        pytest.fail(f"reports/hypothesis_registry.json has duplicate keys: {exc}")


def test_every_hypothesis_carries_id_and_status():
    doc = json.loads(_raw(), object_pairs_hook=_strict)
    hyps = doc.get("hypotheses")
    assert isinstance(hyps, list) and hyps, "hypotheses list missing or empty"
    missing = [h.get("id") or f"index {i}" for i, h in enumerate(hyps)
               if not h.get("id") or not h.get("status")]
    assert not missing, f"entries missing id/status: {missing}"


def test_h149_and_h150_present_with_a_canonical_status():
    doc = json.loads(_raw(), object_pairs_hook=_strict)
    hyps = {h["id"]: h for h in doc["hypotheses"] if h.get("id")}
    for hid in ("H-149", "H-150"):
        assert hid in hyps, f"{hid} missing from the registry"
        state = normalize_status(hyps[hid]["status"])
        assert state in CANONICAL_STATES, (hid, hyps[hid]["status"], state)


def test_h149_verdict_is_not_shadowed_by_a_stale_duplicate():
    """The exact failure mode: status and result.verdict must agree."""
    doc = json.loads(_raw(), object_pairs_hook=_strict)
    h = [x for x in doc["hypotheses"] if x.get("id") == "H-149"][0]
    assert h["status"] == h["result"]["verdict"], (
        f"status {h['status']!r} disagrees with result.verdict "
        f"{h['result']['verdict']!r} -- a duplicate key may be shadowing one of them")
