"""A register revision must be auditable, and must never quietly become a promotion.

These four invariants are the reason "rebuild the picks against new evidence" is a safe
instruction: the revision may sharpen evidence and record why, but it may not move a rank,
change a tier, rewrite a price that was frozen before the evidence existed, or flip the
readiness flag.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
V1 = ROOT / "reports" / "top3_picks_2026-11-22.v1.json"
V2 = ROOT / "reports" / "top3_picks_2026-11-22.json"
HIST = ROOT / "data" / "top3_picks_history.jsonl"


def _shape(reg):
    return [(c["asset_class"], p["rank"], p["symbol"], p["tier"])
            for c in reg["classes"] for p in c["picks"]]


def test_superseded_version_is_preserved():
    assert V1.exists(), "the superseded register must be kept for audit"
    json.loads(V1.read_text())


def test_revision_may_not_reorder_retier_or_resymbol_a_pick():
    v1, v2 = json.loads(V1.read_text()), json.loads(V2.read_text())
    assert _shape(v1) == _shape(v2)


def test_entry_prices_still_match_the_first_frozen_snapshot():
    first = json.loads(HIST.read_text().splitlines()[0])["rows"]
    frozen = {(r["asset_class"], r["symbol"]): r.get("entry_price") for r in first}
    v2 = json.loads(V2.read_text())
    checked = 0
    for c in v2["classes"]:
        for p in c["picks"]:
            f = frozen.get((c["asset_class"], p["symbol"]))
            if f is not None and p.get("entry_price") is not None:
                assert p["entry_price"] == f, f"{p['symbol']} entry price was rewritten"
                checked += 1
    assert checked >= 10, "expected the frozen picks to still be present"


def test_changelog_records_the_evidence_and_readiness_is_unchanged():
    v2 = json.loads(V2.read_text())
    assert v2["version"] == 2 and v2["supersedes"].endswith(".v1.json")
    cl = v2["changelog"]
    assert len(cl) >= 3
    blob = " ".join(json.dumps(e).lower() for e in cl)
    assert "commodity" in blob and "crypto" in blob and "equity" in blob
    assert v2["decision_readiness"] == "NOT_READY_FOR_3_PER_CLASS", "no class may be promoted by a revision"
