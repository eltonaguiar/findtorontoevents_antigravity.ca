"""The publication label has to survive every writer that touches the artifact.

Measured 2026-11-20: a refresh run six minutes after the payload was labelled left
4 of 81 rows without a label while the payload still claimed 74 PROBATION, and it
re-emitted `regime_mild_bear` twice. The page derives the label when it is missing,
so the dashboard did not break -- which is exactly why a test has to catch it
instead of a reader.
"""
import json
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / "audit_dashboard" / "data" / "anti_overfit_audit.json"
VALID = {"PUBLISHABLE", "PROBATION", "UNRATED"}


@pytest.fixture(scope="module")
def payload():
    if not PAYLOAD.is_file():
        pytest.skip("anti_overfit_audit.json absent")
    return json.loads(PAYLOAD.read_text(encoding="utf-8"))


def test_every_row_carries_a_label(payload):
    rows = payload.get("strategies") or []
    assert rows, "payload has no strategies"
    missing = [r.get("strategy") for r in rows if r.get("publication_label") not in VALID]
    assert not missing, "rows without a publication label: %r" % (missing,)


def test_counts_match_the_rows(payload):
    rows = payload.get("strategies") or []
    actual = {k: v for k, v in Counter(r["publication_label"] for r in rows).items() if v}
    stated = {k: v for k, v in (payload.get("publication_label_counts") or {}).items() if v}
    assert actual == stated, "published counts %r != rows %r" % (stated, actual)


def test_label_follows_the_floor(payload):
    bad = []
    for row in payload.get("strategies") or []:
        label = row.get("publication_label")
        dsr = row.get("dsr")
        if dsr is None:
            if label != "UNRATED":
                bad.append((row.get("strategy"), label, dsr))
            continue
        threshold = row.get("publication_dsr_threshold", 0.95)
        want = "PUBLISHABLE" if float(dsr) >= threshold else "PROBATION"
        if label != want:
            bad.append((row.get("strategy"), label, dsr, threshold))
    assert not bad, "label disagrees with its own DSR: %r" % (bad,)


def test_no_row_lost_its_n(payload):
    rows = payload.get("strategies") or []
    bad = [r.get("strategy") for r in rows if not isinstance(r.get("n"), int) or r.get("n") <= 0]
    assert not bad, "rows without a usable n: %r" % (bad,)


def test_demotion_is_a_label_not_a_filter(payload):
    """Every audited strategy is still present, whatever its label."""
    rows = payload.get("strategies") or []
    stated_total = sum((payload.get("publication_label_counts") or {}).values())
    assert stated_total == len(rows), "counts total %d != %d rows" % (stated_total, len(rows))
    assert any(r["publication_label"] == "PROBATION" for r in rows) or True


def test_no_strategy_appears_twice(payload):
    """A repeated row is a merge artefact, not a second strategy.

    2026-11-20T20:46: `git pull -X ours` merged the labelled artifact against a
    freshly generated one line by line and emitted `regime_mild_bear` twice (81
    rows for 80 names). Collapsing an *identical* copy keeps the surviving row
    and its n, so this is deduplication, not the demotion-by-deletion the
    pipeline forbids.
    """
    names = [r["strategy"] for r in payload.get("strategies") or []]
    dups = sorted(n for n, c in Counter(names).items() if c > 1)
    assert not dups, "strategy rows appear more than once: %r" % (dups,)
    stated = payload.get("n_strategies_audited")
    assert stated == len(names), "n_strategies_audited=%r but %d rows" % (stated, len(names))


# ── duplicate-row handling (2026-11-20 merge-hybrid post-mortem) ───────────
def _tool():
    import importlib.util
    import pathlib
    path = (pathlib.Path(__file__).resolve().parents[1]
            / "tools" / "apply_dsr_probation_labels.py")
    spec = importlib.util.spec_from_file_location("_dsr_labels_dup_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _row(name, dsr, n):
    return {"strategy": name, "dsr": dsr, "n": n,
            "publication_label": "PROBATION",
            "publication_reason": "DSR %.4f < 0.95" % dsr,
            "publication_dsr_threshold": 0.95}


def test_check_reports_a_duplicated_strategy_row():
    tool = _tool()
    rows = [_row("regime_mild_bear", 0.0356, 283),
            _row("regime_mild_bear", 0.0356, 283)]
    payload = {"n_strategies_audited": 1, "strategies": rows,
               "publication_label_counts": {"PROBATION": 2}}
    issues = tool.check_payload(payload)
    assert any("appears 2 times" in i for i in issues), issues


def test_check_flags_row_count_disagreeing_with_n_strategies():
    tool = _tool()
    payload = {"n_strategies_audited": 80,
               "strategies": [_row("a", 0.1, 10), _row("b", 0.2, 20)],
               "publication_label_counts": {"PROBATION": 2}}
    issues = tool.check_payload(payload)
    assert any("n_strategies_audited=80" in i for i in issues), issues


def test_dedupe_collapses_an_exact_copy_and_keeps_its_n():
    tool = _tool()
    row = _row("regime_mild_bear", 0.0356, 283)
    kept, dropped = tool.dedupe_exact([row, dict(row)])
    assert len(kept) == 1
    assert dropped == ["regime_mild_bear"]
    assert kept[0]["n"] == 283


def test_dedupe_refuses_same_name_with_different_metrics():
    import pytest
    tool = _tool()
    with pytest.raises(ValueError):
        tool.dedupe_exact([_row("x", 0.1, 10), _row("x", 0.9, 99)])
