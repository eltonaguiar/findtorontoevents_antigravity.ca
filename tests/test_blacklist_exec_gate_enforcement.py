"""
PR-B — Verify blacklisted-strategy exec-gate enforcement.

(Was `kimi_signal_tracking`; that strategy was UNBLOCKED 2026-05-16, so the
intake assertion now targets a strategy that is still blacklisted.)

Per memory `feedback_gate_at_execution_not_generation`, filter-named accounts
can bypass intake-time blocks because the gate only runs at pick-generation.
This test pins the enforcement at BOTH layers:

1.  `alpha_engine.config.BLACKLISTED_STRATEGIES` — intake-side blacklist.
2.  `audit_trail.quality_gates.BLOCKED_SOURCE_SYSTEMS` — exec-time gate
    consulted by `passes_active_gate` / `passes_smart_gate`.

And verifies the live `alpha_engine/data/active_picks.json` has zero leaks.

Spec: `.planning/prs_2026_05_12/PR_SPECS.md` (PR-B).
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from alpha_engine.config import BLACKLISTED_STRATEGIES  # noqa: E402
from audit_trail.quality_gates import (  # noqa: E402
    BLOCKED_SOURCE_SYSTEMS,
    passes_active_gate,
    passes_smart_gate,
)

# NOTE: was "kimi_signal_tracking", which was UNBLOCKED 2026-05-16 (n=368,
# WR=76.6%, PF=7.70) — so it is correctly absent from BLACKLISTED_STRATEGIES.
# This constant must name a strategy that is STILL blacklisted; the previous
# value contradicted its own comment and made the test fail by design.
BLACKLISTED_STRATEGY = "quan_engine_scalp"
# Exec-gate enforcement tests use crypto_winners which remains in BLOCKED_SOURCE_SYSTEMS.
EXEC_BLOCKED_SOURCE = "crypto_winners"
ACTIVE_PICKS_PATH = REPO_ROOT / "alpha_engine" / "data" / "active_picks.json"


def _iso_utc(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _make_pick(**overrides):
    """Pick fixture cloned from `tests/test_phase1_active_gates.py::make_pick`
    — passes all unrelated gates so a rejection is unambiguously the
    blacklist rule."""
    created = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(hours=2)
    day = created.date()
    entry_at_12 = datetime(day.year, day.month, day.day, 12, 0, 0, tzinfo=timezone.utc)
    if entry_at_12 <= created:
        entry_at_12 = entry_at_12 - timedelta(days=1)
    pick = dict(
        id="T",
        symbol="BNBUSDT",
        status="OPEN",
        trust_tier="GOOD",
        strategy="volume_profile_deviation",
        asset_class="CRYPTO",
        entry_price=500.0,
        take_profit=510.0,
        stop_loss=495.0,
        pnl_pct=0.0,
        score=85,
        elite_grade="B",
        trust_score=8,
        entry_time=_iso_utc(entry_at_12),
        confidence=0.85,
        direction="LONG",  # was "BUY" — M-036 gate (2026-05-17) hard-blocks BUY for CRYPTO
        source="volume_profile_deviation",
        # Non-blocked source so the baseline passes and the negative test is
        # meaningful. "quan_engine" is itself in BLOCKED_SOURCE_SYSTEMS.
        source_system="alpha_engine",
        source_systems=["alpha_engine", "mega_mutation", "volume_profile_deviation"],  # consensus gate requires >=3
        created_at=_iso_utc(created),
        timestamp=_iso_utc(created),
        is_fresh=True,
        risk_reward=2.0,
        signal_type="entry",
    )
    pick.update(overrides)
    return pick


class BlacklistIntakeTests(unittest.TestCase):
    def test_blacklisted_strategy_in_intake_blacklist(self):
        """`alpha_engine.config.BLACKLISTED_STRATEGIES` must list the strategy."""
        self.assertIn(BLACKLISTED_STRATEGY, BLACKLISTED_STRATEGIES)


class BlacklistExecGateTests(unittest.TestCase):
    def test_kimi_in_exec_blocked_source_systems(self):
        """`audit_trail.quality_gates.BLOCKED_SOURCE_SYSTEMS` must list a
        known loser so `passes_active_gate` rejects late-bound exec emissions.
        kimi_signal_tracking was unblocked 2026-05-16; test uses crypto_winners."""
        self.assertIn(EXEC_BLOCKED_SOURCE, BLOCKED_SOURCE_SYSTEMS)

    # Cross-cutting gates added after this test was written would reject the
    # baseline before the source gate is reached. Neutralize them so the test
    # isolates the BLOCKED_SOURCE_SYSTEMS rule it actually verifies.
    _NEUTRALIZE = {
        "CRYPTO_PRODUCTION_BLOCK_LONG": "0",
        "CRYPTO_BUY_DIRECTION_GATE_ENABLED": "0",
        "CONCENTRATION_CAP_ENABLED": "0",
        "CRYPTO_CONCENTRATION_GATE": "0",
        "MATRIX_SYMBOL_GATES": "0",
    }

    def test_passes_active_gate_rejects_blocked_source(self):
        with patch.dict(os.environ, self._NEUTRALIZE):
            baseline = _make_pick()
            self.assertTrue(
                passes_active_gate(baseline),
                "baseline fixture should pass; otherwise the negative test is meaningless",
            )
            blocked_pick = _make_pick(source_system=EXEC_BLOCKED_SOURCE)
            self.assertFalse(
                passes_active_gate(blocked_pick),
                f"passes_active_gate must reject source_system={EXEC_BLOCKED_SOURCE!r}",
            )

    def test_passes_active_gate_rejects_kimi_case_insensitive(self):
        """Source-system match is lowercased per quality_gates.py:5063."""
        blocked_pick = _make_pick(source_system=EXEC_BLOCKED_SOURCE.upper())
        self.assertFalse(passes_active_gate(blocked_pick))

    def test_passes_smart_gate_rejects_kimi_source(self):
        """Smart gate delegates to active gate first, so it must also reject."""
        blocked_pick = _make_pick(source_system=EXEC_BLOCKED_SOURCE)
        self.assertFalse(passes_smart_gate(blocked_pick))


class LiveActivePicksTests(unittest.TestCase):
    def test_no_kimi_picks_in_live_active_picks_json(self):
        """`alpha_engine/data/active_picks.json` must contain zero rows with
        `source_system == kimi_signal_tracking`. Active emitter leakage =
        exec-gate bypass per memory `feedback_gate_at_execution_not_generation`."""
        if not ACTIVE_PICKS_PATH.exists():
            self.skipTest(f"active_picks.json not present at {ACTIVE_PICKS_PATH}")
        with ACTIVE_PICKS_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            rows = data.get("picks") or data.get("active") or []
        else:
            rows = data
        leaks = [
            r for r in rows
            if str(r.get("source_system", "") or "").lower().strip()
            == BLACKLISTED_STRATEGY
        ]
        self.assertEqual(
            len(leaks),
            0,
            f"{len(leaks)} {BLACKLISTED_STRATEGY} picks leaked into active set "
            f"(exec-gate bypass): {[r.get('id') for r in leaks[:5]]}",
        )


if __name__ == "__main__":
    unittest.main()
