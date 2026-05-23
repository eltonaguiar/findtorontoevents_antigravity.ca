"""
Test that underperforming portfolios flagged in DEEPSEEK_APR122026.MD §6C
are excluded from the active-curation iteration in audit_dashboard/portfolio_manager.py.

Kills applied 2026-04-12:
  - rr_kings              (29.4% WR, -4.746% avg, n=17)
  - multi_asset_diversified (0% WR, -1.205% avg, n=11)

fear_greed_contrarian is left alive (80% WR, +0.724%, n=5, underpowered).
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from audit_dashboard import portfolio_manager as pm  # noqa: E402


KILLED_PORTFOLIOS = {"rr_kings", "multi_asset_diversified"}
UNDERPOWERED_ALIVE = "fear_greed_contrarian"


def _active_portfolio_ids():
    """Mirror the curation loop at portfolio_manager.py ~line 5014:
        for pdef in PORTFOLIOS:
            if pid in PAUSED_PORTFOLIOS: continue
    """
    return {
        p["id"] for p in pm.PORTFOLIOS if p["id"] not in pm.PAUSED_PORTFOLIOS
    }


@pytest.mark.parametrize("pid", sorted(KILLED_PORTFOLIOS))
def test_killed_portfolio_is_paused(pid):
    assert pid in pm.PAUSED_PORTFOLIOS, (
        f"{pid} must be in PAUSED_PORTFOLIOS per DeepSeek APR12 audit §6C"
    )


@pytest.mark.parametrize("pid", sorted(KILLED_PORTFOLIOS))
def test_killed_portfolio_not_in_active_set(pid):
    assert pid not in _active_portfolio_ids(), (
        f"{pid} should not receive new picks — still active in curation loop"
    )


def test_killed_portfolios_still_defined():
    """Definitions must remain so historical state can render, only curation is disabled."""
    defined = {p["id"] for p in pm.PORTFOLIOS}
    for pid in KILLED_PORTFOLIOS:
        assert pid in defined, f"{pid} definition removed — should only be paused"


def test_fear_greed_contrarian_left_alive():
    """Underpowered (n=5) but high WR — must NOT be killed."""
    assert UNDERPOWERED_ALIVE not in pm.PAUSED_PORTFOLIOS
    assert UNDERPOWERED_ALIVE in _active_portfolio_ids()
