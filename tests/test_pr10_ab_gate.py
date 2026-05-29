"""PR #10: the ML A/B gate must honor the shared AB_ENABLED constant.

The constant is the single source of truth (it reads ML_GATE_AB_ENABLED with a
default of "0"). With the env var unset, AB_ENABLED must be False so the gate
defaults OFF in production.
"""
import importlib
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_ab_router_constant_defaults_false():
    """ab_router.AB_ENABLED is False when ML_GATE_AB_ENABLED is unset."""
    os.environ.pop("ML_GATE_AB_ENABLED", None)
    import ml_gatekeeper.ab_router as ab_router
    importlib.reload(ab_router)
    assert ab_router.AB_ENABLED is False


def test_gatekeeper_reexports_ab_enabled():
    """gatekeeper exposes AB_ENABLED and it is False with env unset.

    Importing gatekeeper is import-light enough for this check; if it ever
    grows heavy side effects this test can be dropped in favor of the
    ab_router-only assertion above.
    """
    os.environ.pop("ML_GATE_AB_ENABLED", None)
    from ml_gatekeeper.gatekeeper import AB_ENABLED
    assert AB_ENABLED is False
