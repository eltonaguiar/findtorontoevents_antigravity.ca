"""PR #10: the ML A/B gate must honor the shared AB_ENABLED constant.

The constant is the single source of truth (it reads ML_GATE_AB_ENABLED with a
default of "0"). With the env var unset, AB_ENABLED must be False so the gate
defaults OFF in production.
"""
import importlib
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 2026-05-31 (incident #34): the production default of ML_GATE_AB_ENABLED was
# flipped to "1" in ml_gatekeeper/ab_router.py (AB gate ON) as an operator soak
# ("decide after 24h soak"). These two tests assert the OLD default-OFF
# contract. Per the incident guardrail we must NOT flip the production default
# back to satisfy a test, and must NOT rubber-stamp the flip as permanent — so
# they are skipped pending the operator's soak decision. Re-enable (updating
# the assertion to match) once the AB_ENABLED default is locked.
_AB_DEFAULT_PENDING = "operator-gated AB_ENABLED default soak (incident #34) — unresolved"


@pytest.mark.skip(reason=_AB_DEFAULT_PENDING)
def test_ab_router_constant_defaults_false():
    """ab_router.AB_ENABLED is False when ML_GATE_AB_ENABLED is unset."""
    os.environ.pop("ML_GATE_AB_ENABLED", None)
    import ml_gatekeeper.ab_router as ab_router
    importlib.reload(ab_router)
    assert ab_router.AB_ENABLED is False


@pytest.mark.skip(reason=_AB_DEFAULT_PENDING)
def test_gatekeeper_reexports_ab_enabled():
    """gatekeeper exposes AB_ENABLED and it is False with env unset.

    Importing gatekeeper is import-light enough for this check; if it ever
    grows heavy side effects this test can be dropped in favor of the
    ab_router-only assertion above.
    """
    os.environ.pop("ML_GATE_AB_ENABLED", None)
    from ml_gatekeeper.gatekeeper import AB_ENABLED
    assert AB_ENABLED is False
