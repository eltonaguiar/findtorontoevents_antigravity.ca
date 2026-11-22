"""Tests for tools/digest_artifact_guard.py — the four contract outcomes.

PASS  : artifact retrievable and the recomputed digest matches.
FAIL  : digest published but no artifact (missing ref).
FAIL  : artifact retrievable but the recomputed digest differs.
SKIP  : no digests published (explicitly not a pass).

Plus path/url resolution and the real-manifest read-only run.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools import digest_artifact_guard as G


def _payload(rows):
    return json.dumps({"schema": "audit.canonical.v1", "rows": rows}).encode()


ROWS = [
    {"symbol": "AAPL", "closed_at": "2026-11-01T00:00:00Z", "pnl_net_pct": 1.5},
    {"symbol": "MSFT", "closed_at": "2026-10-01T00:00:00Z", "pnl_net_pct": -0.5},
]


def test_pass_when_artifact_matches():
    digest = G.canonical_rows_digest(ROWS)
    manifest = {"digests": [{"surface": "s", "digest": digest, "artifact": "x.json"}]}
    report = G.evaluate(manifest, lambda ref: _payload(ROWS))
    assert report["verdict"] == G.OUTCOME_PASS
    assert report["results"][0]["outcome"] == G.OUTCOME_PASS


def test_fail_when_no_artifact_reference():
    manifest = {"digests": [{"surface": "s", "digest": "abc", "artifact": None}]}
    report = G.evaluate(manifest, lambda ref: _payload(ROWS))
    assert report["verdict"] == G.OUTCOME_FAIL
    assert report["results"][0]["reason"] == G.REASON_NO_ARTIFACT


def test_fail_when_artifact_unretrievable():
    manifest = {"digests": [{"surface": "s", "digest": "abc", "artifact": "gone.json"}]}
    report = G.evaluate(manifest, lambda ref: None)
    assert report["verdict"] == G.OUTCOME_FAIL
    assert report["results"][0]["reason"] == G.REASON_UNRETRIEVABLE


def test_fail_when_hash_mismatches():
    manifest = {"digests": [{"surface": "s", "digest": "0" * 64, "artifact": "x.json"}]}
    report = G.evaluate(manifest, lambda ref: _payload(ROWS))
    assert report["verdict"] == G.OUTCOME_FAIL
    assert report["results"][0]["reason"] == G.REASON_MISMATCH
    assert report["results"][0]["actual_digest"] == G.canonical_rows_digest(ROWS)


def test_fail_when_artifact_has_no_rows():
    manifest = {"digests": [{"surface": "s", "digest": "abc", "artifact": "x.json"}]}
    report = G.evaluate(manifest, lambda ref: b'{"schema": "audit.canonical.v1"}')
    assert report["verdict"] == G.OUTCOME_FAIL
    assert report["results"][0]["reason"] == G.REASON_NO_ROWS


def test_skip_when_no_digests_published():
    report = G.evaluate({"digests": []}, lambda ref: None)
    assert report["verdict"] == G.OUTCOME_SKIP
    assert report["n_digests"] == 0


def test_digest_is_order_independent():
    assert G.canonical_rows_digest(ROWS) == G.canonical_rows_digest(list(reversed(ROWS)))


def test_digest_changes_with_data():
    tampered = [dict(ROWS[0], pnl_net_pct=9.9), ROWS[1]]
    assert G.canonical_rows_digest(ROWS) != G.canonical_rows_digest(tampered)


def test_resolver_reads_file_refs(tmp_path):
    p = tmp_path / "rows.json"
    p.write_bytes(_payload(ROWS))
    resolve = G.make_resolver(root=tmp_path)
    assert resolve("rows.json") == _payload(ROWS)
    assert resolve("file:rows.json") == _payload(ROWS)
    assert resolve("missing.json") is None


def test_resolver_url_requires_online(tmp_path):
    resolve = G.make_resolver(online=False, root=tmp_path)
    assert resolve("url:https://example.invalid/x.json") is None


def test_main_returns_skip_for_empty_manifest(tmp_path, capsys):
    m = tmp_path / "m.json"
    m.write_text(json.dumps({"digests": []}))
    rc = G.main(["--manifest", str(m)])
    assert rc == 0
    assert "verdict=SKIP" in capsys.readouterr().out


def test_main_returns_nonzero_for_failing_manifest(tmp_path):
    m = tmp_path / "m.json"
    m.write_text(json.dumps({"digests": [{"surface": "s", "digest": "abc", "artifact": None}]}))
    assert G.main(["--manifest", str(m)]) == 1


def test_real_manifest_runs_read_only():
    """The committed manifest must evaluate without raising; verdict may be FAIL."""
    manifest = json.loads((REPO / "reports" / "published_digests_manifest.json").read_text())
    report = G.evaluate(manifest, G.make_resolver(online=False))
    assert report["verdict"] in (G.OUTCOME_PASS, G.OUTCOME_FAIL, G.OUTCOME_SKIP)
    assert report["n_digests"] == len(manifest.get("digests") or [])
