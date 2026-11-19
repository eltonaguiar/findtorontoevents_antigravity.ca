"""audit2 deploy regression guard (2026-11-19).

The 2026-11-19 peer review found that an earlier deploy wired audit2 into
`/audit/`, which 404s, because the live page is `/audit2/`. The fix lives in
`.github/workflows/audit3-ledger.yml`: it creates the `audit2` directory, `cd`s
into it, and uploads `index.html`, `audit2.js` and `audit2_forward.json`.

This test asserts the **remote destination**, not merely that filenames appear in
a workflow (the old false-green pattern). It also checks the page's data paths
resolve to files the same workflow deploys.

Set AUDIT2_LIVE_CHECK=1 to additionally HEAD the live URL (off by default so CI
does not depend on the network).
"""
from __future__ import annotations

import os
import re
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "audit3-ledger.yml"
AUDIT2_HTML = ROOT / "audit_dashboard" / "audit2.html"
AUDIT2_JS = ROOT / "audit_dashboard" / "audit2.js"
AUDIT2_FWD = ROOT / "audit_dashboard" / "data" / "audit2_forward.json"
AUDIT3_LEDGER = ROOT / "audit_dashboard" / "data" / "audit3_ledger.json"


def _workflow_text() -> str:
    assert WORKFLOW.exists(), f"missing {WORKFLOW}"
    return WORKFLOW.read_text(encoding="utf-8")


def test_audit2_assets_exist():
    for p in (AUDIT2_HTML, AUDIT2_JS, AUDIT2_FWD, AUDIT3_LEDGER):
        assert p.exists(), f"missing deploy source {p}"


def test_workflow_deploys_into_the_audit2_directory_not_audit():
    text = _workflow_text()
    # It must create and enter the audit2 remote directory.
    assert re.search(r'ftp\.mkd\(\s*"audit2"\s*\)', text), "workflow does not create /audit2"
    assert re.search(r'ftp\.cwd\(\s*"audit2"\s*\)', text), "workflow does not enter /audit2"
    # The three audit2 artifacts must be uploaded after entering that directory.
    tail = text.split('ftp.cwd("audit2")', 1)[1]
    for local, remote in [
        ("audit_dashboard/audit2.html", "index.html"),
        ("audit_dashboard/audit2.js", "audit2.js"),
        ("audit_dashboard/data/audit2_forward.json", "audit2_forward.json"),
    ]:
        assert local in tail, f"{local} is not uploaded under /audit2"
        assert f'"{remote}"' in tail, f"{remote} is not the /audit2 target name"


def test_audit3_ledger_is_deployed_for_the_relative_path():
    """audit2.js reads ../audit3/audit3_ledger.json, so audit3/ must carry it."""
    text = _workflow_text()
    audit3_block = text.split('ftp.cwd("audit3")', 1)[1].split('ftp.cwd("..")', 1)[0]
    assert "audit_dashboard/data/audit3_ledger.json" in audit3_block
    assert '"audit3_ledger.json"' in audit3_block


def test_audit2_page_uses_the_deployed_ledger_path():
    js = AUDIT2_JS.read_text(encoding="utf-8")
    assert "../audit3/audit3_ledger.json" in js, (
        "audit2.js must read the audit3 ledger via the deployed relative path")
    assert "audit2_forward.json" in js


@pytest.mark.skipif(os.environ.get("AUDIT2_LIVE_CHECK") != "1",
                    reason="set AUDIT2_LIVE_CHECK=1 to probe the live URL")
def test_live_audit2_url_resolves():
    req = urllib.request.Request("https://findtorontoevents.ca/audit2/",
                                 method="HEAD",
                                 headers={"User-Agent": "audit2-deploy-test"})
    with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310
        assert resp.status == 200
