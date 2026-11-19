"""Merge guard for the audit2 page: source must exist and be wired into the deploy
manifests (audit-dashboard.yml per-site page lists + deploy_audit_files.py).

Pure/offline: no FTP, no network, no live site.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.deploy_audit_files import UPLOADS  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
AUDIT2_HTML = REPO / "audit_dashboard" / "audit2.html"
AUDIT2_JS = REPO / "audit_dashboard" / "audit2.js"
AUDIT2_FWD = REPO / "audit_dashboard" / "data" / "audit2_forward.json"
WORKFLOW = REPO / ".github" / "workflows" / "audit-dashboard.yml"


def test_audit2_source_files_exist():
    assert AUDIT2_HTML.exists(), "audit_dashboard/audit2.html missing"
    assert AUDIT2_JS.exists(), "audit_dashboard/audit2.js missing"
    assert AUDIT2_FWD.exists(), "audit_dashboard/data/audit2_forward.json missing"


def test_audit2_referenced_in_deploy_script():
    local_paths = {local for local, _, _ in UPLOADS}
    assert "audit_dashboard/audit2.html" in local_paths
    assert "audit_dashboard/audit2.js" in local_paths
    assert "audit_dashboard/data/audit2_forward.json" in local_paths


def test_audit2_referenced_in_workflow_page_lists():
    text = WORKFLOW.read_text(encoding="utf-8")
    # 3 per-site page arrays must each name audit2.html
    assert text.count('"audit2.html"') >= 3, (
        "audit2.html must appear in every per-site page list in audit-dashboard.yml"
    )
    # deps must deploy next to the page on each site
    assert text.count('"audit2.js"') >= 3
    assert text.count('"audit2_forward.json"') >= 3
