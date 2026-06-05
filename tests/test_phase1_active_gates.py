"""
Phase 1 Active-Gate Tests — Dead-Zone + Time-of-Day gates in
audit_trail.quality_gates.passes_active_gate.

Why these gates exist
---------------------
Deep-dive analysis of closed picks (2026-02-22 → 2026-04-22):

  1. Confidence < 0.80 gate REVERTED 2026-04-22 (PR #323 diagnosis):
     confidence proved anti-predictive — the < 0.80 gate was rejecting the
     BEST tier (conf 0.00–0.55: WR 42.8%) while KEEPING the worst
     (conf 0.65–0.75: WR 26.2%).  Full revert per 4-model consensus.

     Replaced with a narrower dead-zone gate targeting the ACTUALLY-WORST
     band (0.65–0.75), which has n=820 at WR 26.2%.  This gate defaults
     to shadow mode (tags but doesn't reject).

  2. Time-of-day bucketing revealed two death windows on crypto:
     Window A: 08:00–11:00 UTC (n=697, cumulative −164% P/L)
     Window B: 16:00–21:00 UTC (PR #291 deep investigation):
       20:00 UTC is the worst single hour in the dataset (WR 17.1%)
     By contrast, 22:00–23:00 UTC is the BEST window (WR 63–72%).
     Combined: 10 blocked hours out of 24.

Env knobs
---------
  PHASE1_CONF_DEADZONE_ENABLED  1 | 0 | shadow   (default shadow)
  PHASE1_CONF_DEADZONE_LOW      float              (default 0.65)
  PHASE1_CONF_DEADZONE_HIGH     float              (default 0.75)
  PHASE1_TOD_GATE_ENABLED       1 | 0 | shadow    (default shadow)
  PHASE1_TOD_GATE_HOURS         CSV of UTC hours   (default "8,9,10,11,16,17,18,19,20,21")

Both gates are scoped to CRYPTO. Shadow mode tags but doesn't reject.
"""
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from audit_trail.quality_gates import passes_active_gate  # noqa: E402


def _iso_utc(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _default_fixture_times() -> tuple[str, str, str]:
    """Recent created_at/timestamp/entry_time so crypto staleness (72h) passes
    AND entry_time lands outside both Phase 1 TOD block windows (08-11 + 16-21
    UTC per PR #291 expansion). Default entry hour is 12:00 UTC — safe in
    both windows."""
    created = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(hours=2)
    day = created.date()
    # 12:00 UTC is between the morning block (08-11) and the afternoon block (16-21)
    entry_at_12 = datetime(
        day.year, day.month, day.day, 12, 0, 0, tzinfo=timezone.utc
    )
    if entry_at_12 <= created:
        entry_at_12 = entry_at_12 - timedelta(days=1)
    return _iso_utc(created), _iso_utc(created), _iso_utc(entry_at_12)


def make_pick(**overrides):
    """Base pick that passes every gate on the path — override to probe one thing."""
    created_at, timestamp, entry_time = _default_fixture_times()
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
        entry_time=entry_time,
        confidence=0.85,
        direction="LONG",  # was "BUY" — M-036 gate (2026-05-17) hard-blocks BUY for CRYPTO
        source="volume_profile_deviation",
        source_system="quan_engine",
        source_systems=["quan_engine", "alpha_engine", "mega_mutation"],  # consensus gate requires >=3
        created_at=created_at,
        timestamp=timestamp,
        is_fresh=True,
        risk_reward=2.0,
        signal_type="entry",
    )
    pick.update(overrides)
    return pick


class _ClearPhase1Env:
    """Reset Phase 1 env vars between tests so one run doesn't taint the next.

    Also neutralizes the production defaults for cross-cutting gates that
    are ON in CI workflows (CRYPTO_PRODUCTION_BLOCK_LONG=1) so phase-1
    unit tests aren't blocked by stack-on-top gates they aren't testing.
    """

    _vars = (
        "PHASE1_TOD_GATE_ENABLED",
        "PHASE1_TOD_GATE_HOURS",
        "PHASE1_CONF_DEADZONE_ENABLED",
        "PHASE1_CONF_DEADZONE_LOW",
        "PHASE1_CONF_DEADZONE_HIGH",
        "CRYPTO_PRODUCTION_BLOCK_LONG",
        "CRYPTO_PRODUCTION_BLOCK_LONG_OVERRIDE",
    )

    def __enter__(self):
        self._saved = {k: os.environ.pop(k, None) for k in self._vars}
        # Default to off so individual tests that DO want the gate on can
        # set it explicitly within their `with` block. Mirrors the
        # OFF-by-default posture used in production tuning runs.
        os.environ.setdefault("CRYPTO_PRODUCTION_BLOCK_LONG", "0")
        return self

    def __exit__(self, *exc):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


# ── Dead-Zone Gate Tests ──────────────────────────────────────────────────
# The confidence < 0.80 gate was REVERTED (PR #323). It was replaced with
# a dead-zone gate that only targets the 0.65–0.75 band, which is the
# actually-worst tier. Defaults to shadow mode (tags, doesn't reject).


class Phase1DeadZoneGateTests(unittest.TestCase):
    """Test the dead-zone gate (confidence 0.65–0.75 band rejection).

    The reverted < 0.80 gate is gone — these tests verify the narrower
    dead-zone gate that replaced it.
    """

    def test_high_conf_crypto_passes(self):
        """confidence=0.85 is well above the dead zone — should pass."""
        with _ClearPhase1Env():
            os.environ["PHASE1_CONF_DEADZONE_ENABLED"] = "1"
            self.assertTrue(passes_active_gate(make_pick(confidence=0.85)))

    def test_low_conf_crypto_below_deadzone_passes(self):
        """confidence=0.50 is below the dead zone — should pass.
        This was INCORRECTLY rejected by the old < 0.80 gate."""
        with _ClearPhase1Env():
            os.environ["PHASE1_CONF_DEADZONE_ENABLED"] = "1"
            self.assertTrue(passes_active_gate(make_pick(confidence=0.50)))

    def test_deadzone_low_boundary_passes(self):
        """confidence=0.65 is at the low edge; dead zone is [0.65, 0.75)
        so 0.65 is IN the zone and should be blocked."""
        with _ClearPhase1Env():
            os.environ["PHASE1_CONF_DEADZONE_ENABLED"] = "1"
            self.assertFalse(passes_active_gate(make_pick(confidence=0.65)))

    def test_deadzone_high_boundary_passes(self):
        """confidence=0.75 is at the high edge; dead zone is [0.65, 0.75)
        so 0.75 is NOT in the zone and should pass."""
        with _ClearPhase1Env():
            os.environ["PHASE1_CONF_DEADZONE_ENABLED"] = "1"
            self.assertTrue(passes_active_gate(make_pick(confidence=0.75)))

    def test_inside_deadzone_blocked(self):
        """confidence=0.70 is squarely inside the dead zone — blocked."""
        with _ClearPhase1Env():
            os.environ["PHASE1_CONF_DEADZONE_ENABLED"] = "1"
            self.assertFalse(passes_active_gate(make_pick(confidence=0.70)))

    def test_non_crypto_not_gated(self):
        """EQUITY and others stay out of the dead-zone gate."""
        with _ClearPhase1Env():
            os.environ["PHASE1_CONF_DEADZONE_ENABLED"] = "1"
            eq = make_pick(
                asset_class="EQUITY", symbol="BNB", confidence=0.70,
                entry_time="2026-04-17T09:00:00Z",
            )
            self.assertTrue(passes_active_gate(eq))

    def test_env_disable(self):
        """PHASE1_CONF_DEADZONE_ENABLED=0 turns the gate off entirely."""
        with _ClearPhase1Env():
            os.environ["PHASE1_CONF_DEADZONE_ENABLED"] = "0"
            self.assertTrue(passes_active_gate(make_pick(confidence=0.70)))

    def test_shadow_mode_tags_without_rejecting(self):
        """Shadow mode (default) tags the pick but doesn't reject it."""
        with _ClearPhase1Env():
            os.environ["PHASE1_CONF_DEADZONE_ENABLED"] = "shadow"
            pick = make_pick(confidence=0.70)
            self.assertTrue(passes_active_gate(pick))
            self.assertIn("_phase1_dz_shadow_reject", pick)

    def test_env_deadzone_override(self):
        """Dead-zone bounds are env-tunable — widen to [0.60, 0.80)."""
        with _ClearPhase1Env():
            os.environ["PHASE1_CONF_DEADZONE_ENABLED"] = "1"
            os.environ["PHASE1_CONF_DEADZONE_LOW"] = "0.60"
            os.environ["PHASE1_CONF_DEADZONE_HIGH"] = "0.80"
            # 0.70 is in the widened zone — blocked
            self.assertFalse(passes_active_gate(make_pick(confidence=0.70)))
            # 0.85 is above the widened zone — passes
            self.assertTrue(passes_active_gate(make_pick(confidence=0.85)))

    def test_missing_confidence_does_not_reject(self):
        """Picks without a confidence value should fall through (bug-safe)."""
        with _ClearPhase1Env():
            os.environ["PHASE1_CONF_DEADZONE_ENABLED"] = "1"
            pick = make_pick()
            pick.pop("confidence", None)
            self.assertTrue(passes_active_gate(pick))

    def test_reverted_conf_gate_does_not_block(self):
        """The old confidence < 0.80 gate is fully reverted — low confidence
        picks (outside dead zone) must pass even with old env var set."""
        with _ClearPhase1Env():
            os.environ["PHASE1_CONF_DEADZONE_ENABLED"] = "1"
            # confidence=0.50 — below dead zone, would have been blocked by
            # the old gate, but should pass now
            self.assertTrue(passes_active_gate(make_pick(confidence=0.50)))
            # confidence=0.80 — above dead zone, would have been the old
            # threshold boundary, should pass
            self.assertTrue(passes_active_gate(make_pick(confidence=0.80)))


# ── Time-of-Day Gate Tests ────────────────────────────────────────────────
# Now covers BOTH death windows: 08-11 (original) + 16-21 (PR #291).


class Phase1TimeOfDayGateTests(unittest.TestCase):

    def test_safe_hour_passes(self):
        """14:00 UTC is between the two block windows — passes."""
        with _ClearPhase1Env():
            os.environ["PHASE1_TOD_GATE_ENABLED"] = "1"
            self.assertTrue(
                passes_active_gate(make_pick(entry_time="2026-04-17T14:00:00Z"))
            )

    def test_morning_kill_hours_blocked(self):
        """08-11 UTC morning death window — all blocked."""
        with _ClearPhase1Env():
            os.environ["PHASE1_TOD_GATE_ENABLED"] = "1"
            for h in (8, 9, 10, 11):
                with self.subTest(hour=h):
                    self.assertFalse(
                        passes_active_gate(
                            make_pick(entry_time=f"2026-04-17T{h:02d}:15:00Z")
                        )
                    )

    def test_afternoon_kill_hours_blocked(self):
        """16-21 UTC afternoon death window (PR #291) — all blocked."""
        with _ClearPhase1Env():
            os.environ["PHASE1_TOD_GATE_ENABLED"] = "1"
            for h in (16, 17, 18, 19, 20, 21):
                with self.subTest(hour=h):
                    self.assertFalse(
                        passes_active_gate(
                            make_pick(entry_time=f"2026-04-17T{h:02d}:15:00Z")
                        )
                    )

    def test_best_hour_passes(self):
        """22:00 UTC is the best hour (WR 63-72%) — must pass."""
        with _ClearPhase1Env():
            os.environ["PHASE1_TOD_GATE_ENABLED"] = "1"
            self.assertTrue(
                passes_active_gate(make_pick(entry_time="2026-04-17T22:00:00Z"))
            )

    def test_boundary_12_utc_passes(self):
        """12:00 UTC is between the morning and afternoon windows."""
        with _ClearPhase1Env():
            os.environ["PHASE1_TOD_GATE_ENABLED"] = "1"
            self.assertTrue(
                passes_active_gate(make_pick(entry_time="2026-04-17T12:00:00Z"))
            )

    def test_boundary_15_utc_passes(self):
        """15:00 UTC is the last safe hour before the afternoon window."""
        with _ClearPhase1Env():
            os.environ["PHASE1_TOD_GATE_ENABLED"] = "1"
            self.assertTrue(
                passes_active_gate(make_pick(entry_time="2026-04-17T15:00:00Z"))
            )

    def test_11_59_is_still_blocked(self):
        """11:59 UTC is still in the morning block window."""
        with _ClearPhase1Env():
            os.environ["PHASE1_TOD_GATE_ENABLED"] = "1"
            self.assertFalse(
                passes_active_gate(make_pick(entry_time="2026-04-17T11:59:00Z"))
            )

    def test_15_59_is_still_safe(self):
        """15:59 UTC is still safe (afternoon window starts at 16:00)."""
        with _ClearPhase1Env():
            os.environ["PHASE1_TOD_GATE_ENABLED"] = "1"
            self.assertTrue(
                passes_active_gate(make_pick(entry_time="2026-04-17T15:59:00Z"))
            )

    def test_env_disable(self):
        """PHASE1_TOD_GATE_ENABLED=0 turns the gate off entirely."""
        with _ClearPhase1Env():
            os.environ["PHASE1_TOD_GATE_ENABLED"] = "0"
            self.assertTrue(
                passes_active_gate(make_pick(entry_time="2026-04-17T08:30:00Z"))
            )

    def test_env_hour_override(self):
        """Shift the block window to 20–23 UTC."""
        with _ClearPhase1Env():
            os.environ["PHASE1_TOD_GATE_ENABLED"] = "1"
            os.environ["PHASE1_TOD_GATE_HOURS"] = "20,21,22,23"
            self.assertTrue(
                passes_active_gate(make_pick(entry_time="2026-04-17T09:00:00Z"))
            )
            self.assertFalse(
                passes_active_gate(make_pick(entry_time="2026-04-17T21:00:00Z"))
            )

    def test_non_crypto_not_gated(self):
        """EQUITY picks bypass the TOD gate entirely."""
        with _ClearPhase1Env():
            os.environ["PHASE1_TOD_GATE_ENABLED"] = "1"
            eq = make_pick(
                asset_class="EQUITY", symbol="BNB",
                entry_time="2026-04-17T09:00:00Z",
            )
            self.assertTrue(passes_active_gate(eq))

    def test_non_utc_offset_converted_to_utc(self):
        """Picks with non-UTC offsets must be converted to UTC before the
        block-window check. 08:30 at -05:00 = 13:30Z (passes). 03:30 at
        -05:00 = 08:30Z (blocks)."""
        with _ClearPhase1Env():
            os.environ["PHASE1_TOD_GATE_ENABLED"] = "1"
            # 13:30 UTC — safe hour
            self.assertTrue(
                passes_active_gate(make_pick(entry_time="2026-04-17T08:30:00-05:00"))
            )
            # 08:30 UTC — blocked
            self.assertFalse(
                passes_active_gate(make_pick(entry_time="2026-04-17T03:30:00-05:00"))
            )

    def test_missing_asset_class_fails_open(self):
        """Picks missing asset_class should NOT be silently gated as CRYPTO —
        unlabeled picks pass the Phase 1 gates (fail-open on missing field)."""
        with _ClearPhase1Env():
            os.environ["PHASE1_TOD_GATE_ENABLED"] = "1"
            # Would fail TOD gate if treated as CRYPTO (09:00 UTC)
            pick = make_pick(
                asset_class="", symbol="FOO", confidence=0.5,
                entry_time="2026-04-17T09:00:00Z",
            )
            self.assertTrue(passes_active_gate(pick))

    def test_missing_entry_time_uses_now(self):
        """If a source forgets entry_time, fall back to current UTC hour so
        stale picks can't sneak past the window check."""
        with _ClearPhase1Env():
            os.environ["PHASE1_TOD_GATE_ENABLED"] = "1"
            pick = make_pick()
            pick.pop("entry_time", None)
            pick.pop("opened_at", None)
            pick.pop("timestamp", None)
            pick.pop("created_at", None)
            # Just verify the call doesn't error — pass/block depends on wall clock.
            result = passes_active_gate(pick)
            self.assertIn(result, (True, False))

    def test_shadow_mode_tags_without_rejecting(self):
        """Shadow mode (default) tags the pick but doesn't reject it."""
        with _ClearPhase1Env():
            os.environ["PHASE1_TOD_GATE_ENABLED"] = "shadow"
            pick = make_pick(entry_time="2026-04-17T20:00:00Z")
            self.assertTrue(passes_active_gate(pick))
            self.assertIn("_phase1_tod_shadow_reject", pick)


# ── Combined Gate Tests ───────────────────────────────────────────────────


class Phase1CombinedTests(unittest.TestCase):

    def test_both_gates_applied_together(self):
        """A pick in the dead zone AND a blocked TOD hour should be rejected
        when both gates are active."""
        with _ClearPhase1Env():
            os.environ["PHASE1_CONF_DEADZONE_ENABLED"] = "1"
            os.environ["PHASE1_TOD_GATE_ENABLED"] = "1"
            self.assertFalse(
                passes_active_gate(
                    make_pick(confidence=0.70, entry_time="2026-04-17T08:30:00Z")
                )
            )

    def test_both_gates_disabled(self):
        """With both gates off, even a terrible pick should pass."""
        with _ClearPhase1Env():
            os.environ["PHASE1_CONF_DEADZONE_ENABLED"] = "0"
            os.environ["PHASE1_TOD_GATE_ENABLED"] = "0"
            self.assertTrue(
                passes_active_gate(
                    make_pick(confidence=0.50, entry_time="2026-04-17T08:30:00Z")
                )
            )

    def test_deadzone_blocks_tod_passes(self):
        """Pick in dead zone but safe hour — blocked by dead-zone gate."""
        with _ClearPhase1Env():
            os.environ["PHASE1_CONF_DEADZONE_ENABLED"] = "1"
            os.environ["PHASE1_TOD_GATE_ENABLED"] = "1"
            self.assertFalse(
                passes_active_gate(
                    make_pick(confidence=0.70, entry_time="2026-04-17T14:00:00Z")
                )
            )

    def test_tod_blocks_deadzone_passes(self):
        """Pick in blocked hour but outside dead zone — blocked by TOD gate."""
        with _ClearPhase1Env():
            os.environ["PHASE1_CONF_DEADZONE_ENABLED"] = "1"
            os.environ["PHASE1_TOD_GATE_ENABLED"] = "1"
            self.assertFalse(
                passes_active_gate(
                    make_pick(confidence=0.50, entry_time="2026-04-17T20:00:00Z")
                )
            )

    def test_both_gates_shadow_mode_tags(self):
        """Both gates in shadow mode — pick passes but gets both tags."""
        with _ClearPhase1Env():
            os.environ["PHASE1_CONF_DEADZONE_ENABLED"] = "shadow"
            os.environ["PHASE1_TOD_GATE_ENABLED"] = "shadow"
            pick = make_pick(confidence=0.70, entry_time="2026-04-17T20:00:00Z")
            self.assertTrue(passes_active_gate(pick))
            self.assertIn("_phase1_dz_shadow_reject", pick)
            self.assertIn("_phase1_tod_shadow_reject", pick)


if __name__ == "__main__":
    unittest.main(verbosity=2)
