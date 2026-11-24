"""Invariants for tools/kill_list_reconcile.py against the committed artifacts."""
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.kill_list_reconcile import reconcile  # noqa: E402


def test_runs_on_committed_artifacts():
    rep = reconcile()
    c = rep["counts"]
    assert c["legacy_names"] > 0
    assert c["audit3_kill_cells_named"] > 0
    assert c["union"] == c["legacy_names"] + c["audit3_kill_cells_named"] - c["overlap"]


def test_overlap_is_present_in_both_sources():
    rep = reconcile()
    for name, hit in rep["overlap"].items():
        assert hit["legacy"], name
        assert hit["audit3"], name


def test_audit3_kills_carry_direction():
    """A name-only list cannot represent the tribunal; these cells must keep direction."""
    rep = reconcile()
    seen = [cell for cells in rep["audit3_only"].values() for cell in cells]
    seen += [cell for hit in rep["overlap"].values() for cell in hit["audit3"]]
    assert seen
    for cell in seen:
        assert cell["direction"] in ("LONG", "SHORT", "UNKNOWN", "-")
