#!/usr/bin/env python3
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "ml_gatekeeper"))

from gatekeeper import _drop_leakage_enabled, _LEAKAGE_FEATURE_INDICES  # noqa: E402


def test_leakage_masking_default_on():
    os.environ.pop("ML_GATE_DROP_LEAKAGE", None)
    assert _drop_leakage_enabled() is True, "masking must be ON by default"


def test_leakage_masking_explicit_off():
    os.environ["ML_GATE_DROP_LEAKAGE"] = "0"
    assert _drop_leakage_enabled() is False


def test_leakage_masking_explicit_on():
    os.environ["ML_GATE_DROP_LEAKAGE"] = "1"
    assert _drop_leakage_enabled() is True


def test_leaky_feature_indices_are_the_confirmed_set():
    # forwarded_wr, strat_fwd_wr, eb_forward_wr, age_hours
    assert _LEAKAGE_FEATURE_INDICES == (5, 6, 19, 30)
