"""Feed Health gate: registered-but-empty shadow sources warn, they don't fail.

Context: 2026-11-16 wiring added pm_kalshi_re_signals / pm_polymarket_re_signals
to JSON_PICK_SOURCES. Their producers are best-effort in audit-dashboard.yml
(`|| echo ::warning::`), so an empty feed made Feed Health Check exit 1 hourly
with `MISSING system rows`. Absence of a never-produced source is a warning;
absence of a healthy source is still a failure.
"""
from __future__ import annotations

import json
import sys
import types
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from audit_trail.dashboard_payload_health import check_dashboard_payload  # noqa: E402


_ABSENT = object()


@pytest.fixture(autouse=True)
def _restore_generator_module():
    """Put the real audit_trail.dashboard_generator back after each test.

    _install_fake_generator overwrites sys.modules for the whole pytest
    session. This file sorts before the modules that import the real
    generator, so leaking the stub broke their collection in CI
    (CI Tests run 43820418075: 21 failed, 16 errors) while an isolated
    run of this file still passed.
    """
    prior = sys.modules.get("audit_trail.dashboard_generator", _ABSENT)
    yield
    if prior is _ABSENT:
        sys.modules.pop("audit_trail.dashboard_generator", None)
    else:
        sys.modules["audit_trail.dashboard_generator"] = prior


def _install_fake_generator(sources, hidden=(), ghost=()):
    """Stub audit_trail.dashboard_generator so the test stays fast/offline."""
    fake = types.ModuleType("audit_trail.dashboard_generator")
    fake.JSON_PICK_SOURCES = list(sources)
    fake._HIDDEN_SYSTEMS = set(hidden)
    fake._GHOST_SYSTEMS = set(ghost)
    sys.modules["audit_trail.dashboard_generator"] = fake
    return fake


def _payload(tmp_path: Path, systems) -> Path:
    p = tmp_path / "payload.json"
    p.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "systems": [{"name": s} for s in systems],
            }
        ),
        encoding="utf-8",
    )
    return p


def test_optional_shadow_missing_is_warning_not_failure(tmp_path):
    _install_fake_generator(
        [
            ("required_feed", "x.json", None),
            ("pm_kalshi_re_signals", "kalshi_signals.json", None),
        ]
    )
    h = check_dashboard_payload(tmp_path, _payload(tmp_path, ["required_feed"]))
    assert h.ok is True
    assert h.problems == []
    assert h.missing_systems == []
    assert h.optional_missing == ["pm_kalshi_re_signals"]
    assert any("OPTIONAL" in line for line in h.summary_lines())


def test_required_missing_still_fails(tmp_path):
    _install_fake_generator([("required_feed", "x.json", None)])
    h = check_dashboard_payload(tmp_path, _payload(tmp_path, []))
    assert h.ok is False
    assert h.missing_systems == ["required_feed"]
    assert {"system": "required_feed", "reason": "missing_from_payload"} in h.problems


def test_optional_present_produces_no_warning(tmp_path):
    _install_fake_generator([("pm_polymarket_re_signals", "polymarket_signals.json", None)])
    h = check_dashboard_payload(
        tmp_path, _payload(tmp_path, ["pm_polymarket_re_signals"])
    )
    assert h.ok is True
    assert h.optional_missing == []


def test_hidden_and_ghost_still_excluded(tmp_path):
    _install_fake_generator(
        [("hidden_feed", "h.json", None), ("ghost_feed", "g.json", None)],
        hidden={"hidden_feed"},
        ghost={"ghost_feed"},
    )
    h = check_dashboard_payload(tmp_path, _payload(tmp_path, []))
    assert h.ok is True
    assert h.problems == []
