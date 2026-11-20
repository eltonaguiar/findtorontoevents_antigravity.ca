"""Pin /audit2 into the surface parity assertion.

Why: /audit2 renders whichever entry of its fallback chain resolves first, so it
can silently disagree with /audit3 while both are 200. Parity covered /audit and
/audit3 only; this test fails if audit2's page drops out of ENDPOINTS.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.assert_surface_parity import ENDPOINTS  # noqa: E402


def test_audit2_page_is_asserted():
    keys = {key for key, _, _ in ENDPOINTS}
    assert "audit2_page" in keys, "/audit2 must be in the parity assertion, not just /audit and /audit3"


def test_audit2_url_points_at_the_live_path():
    urls = {key: url for key, url, _ in ENDPOINTS}
    # live site serves audit2 at /audit2/ (200); /audit/ is the legacy stack
    assert urls["audit2_page"].endswith("/audit2/")
