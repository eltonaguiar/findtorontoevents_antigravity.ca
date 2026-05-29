"""Regression: falsified COMMODITY sources must not bypass forward_validated (2026-05-28)."""
from __future__ import annotations

import re
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
QG = REPO / "audit_trail" / "quality_gates.py"


def test_commodity_fv_exempt_excludes_falsified_cot_sources():
    """multi_asset_cot / multi_asset_copytrader removed after 6.33x over-emission falsification."""
    src = QG.read_text(encoding="utf-8")
    m = re.search(r"_COMMODITY_FV_EXEMPT\s*=\s*frozenset\(\{([^}]*)\}\)", src)
    assert m, "_COMMODITY_FV_EXEMPT frozenset not found in quality_gates.py"
    body = m.group(1)
    assert "multi_asset_cot" not in body
    assert "multi_asset_copytrader" not in body
    assert "commodity_cot_contrarian" in body


def test_quality_gates_comment_documents_falsification():
    src = QG.read_text(encoding="utf-8")
    assert "6.33x over-emission" in src or "over-emission falsified" in src
