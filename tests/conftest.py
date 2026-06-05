"""Ensure repo root is on sys.path and neutralize the Phase 1 opt-in gates
across the test session.

Pre-existing tests in test_quality_gates.py, test_audit_pick_sanity_gate.py,
etc. were written before the Phase 1 confidence (≥0.80) + time-of-day
(08–11 UTC block) + deadzone (0.65-0.75) gates landed. Those fixtures set
confidence=0.7 / 0.68 and use entry_times that happen to fall in the blocked
window because they weren't testing Phase 1 behaviour. Enabling the gates
by default would make those unrelated tests fail.

Phase-1-specific tests in tests/test_phase1_active_gates.py manage their own
env via a `_ClearPhase1Env` context manager, so removing these keys inside
their setUp lets the gate's internal default ("1") kick back in for that
specific module.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# setdefault — do NOT overwrite if the outer environment explicitly sets
# these (e.g. CI experimenting with live-gate runs).
os.environ.setdefault("PHASE1_CONF_GATE_ENABLED", "0")
os.environ.setdefault("PHASE1_CONF_DEADZONE_ENABLED", "0")
os.environ.setdefault("PHASE1_TOD_GATE_ENABLED", "0")
# Transaction-cost gate landed 2026-05-14 (kilocode vet). Pre-existing test
# fixtures don't set pnl_pct, so apply_costs_to_pick treats gross_pnl=0.0
# and returns cost_cleared=False, blocking the smart_gate before the
# assertion-under-test fires. Production-side fix (quality_gates.py) also
# now skips the gate when pick has no realized pnl; this env-flag is the
# belt-and-braces for legacy fixtures that DO set pnl_pct but to values
# meaningful to other gates only.
os.environ.setdefault("TRANSACTION_COST_GATE_DISABLED", "1")
# FOREX SHORT-only gate landed in Hermes commits 2026-05-14. Blocks all
# FOREX LONG picks. Pre-existing tests fixture LONG FOREX picks (EURUSD=X
# LONG etc.) that are testing OTHER gates, not the short-only rule.
os.environ.setdefault("FOREX_SHORT_ONLY_GATE_DISABLED", "1")
# Admission-time guards added by multi-agent (Hermes/Kilo) commits 2026-05-13
# through 2026-05-14. Each guard has its own kill-switch env. Pre-existing
# test fixtures predate every guard. Tests that specifically exercise a
# guard should pop its env in setUp; everything else defaults to OFF here.
os.environ.setdefault("CRYPTO_HIGH_CONF_GUARD_ENABLED", "0")  # CRYPTO conf>0.85 inversion guard
os.environ.setdefault("DRIFT_PAUSE_GATE_ENABLED", "0")  # KS concept-drift auto-pause
os.environ.setdefault("BTC_BEAR_LONG_REJECT", "0")  # BTC-bear-regime LONG block
os.environ.setdefault("ML_CRYPTO_PRED_LONG_REJECT", "0")  # ml_crypto_pred LONG anti-edge
os.environ.setdefault("CRYPTO_UTC_HOUR_FILTER", "0")  # 08-09 UTC death-zone
# COT lag-correction + MATCH gate (M-008/M-021). New admission-time gate added
# with the cot_lag_corrector wiring. Default-disabled in tests; the gate's own
# tests in tests/test_cot_lag_corrector.py set their own env explicitly.
os.environ.setdefault("COT_MATCH_GATE_ENABLED", "0")
# FOREX directional + symbol gates added 2026-05-17 by automated agent commits.
# These default ON and block FOREX LONG picks with elite<75 and specific symbols.
# Pre-existing tests use FOREX LONG fixtures for OTHER gates (trust-tier, JPY-cross,
# ETF scoping, etc.) and would fail spuriously. Gates' own tests set env explicitly.
os.environ.setdefault("FOREX_DIRECTIONAL_GATE_ENABLED", "0")
os.environ.setdefault("FOREX_SYMBOL_GATE_ENABLED", "0")
# M-078 FOREX session gate (2026-05-17): fail-closed outside 08-16 UTC.
# Test fixtures use datetime.now() for timestamps, making tests time-dependent.
# All FOREX pick tests (both LONG and SHORT) fail after 16 UTC without this.
# Tests specifically exercising M-078 must pop this env in their setUp.
os.environ.setdefault("FOREX_SESSION_GATE_DISABLED", "1")
# Concentration cap reads live DB state. In CI (and local runs with active picks),
# the cap fires on BTCUSDT/EURUSD=X etc. and breaks tests that fixture those symbols
# for OTHER gates. Tests that specifically exercise the cap (test_quality_gates.py,
# test_cot_dedup_guard.py, test_audit_enhancements_wireup_2026_05_13.py) set
# CONCENTRATION_CAP_ENABLED=1 explicitly via monkeypatch, so this default is safe.
os.environ.setdefault("CONCENTRATION_CAP_ENABLED", "0")
# Safety-halt gate (M-049, 2026-05-15) reads live safety_status from DB.
# In CI/local, the safety_status can be STOP (Binance CB open, etc.) and would
# block ALL picks — breaking every test that expects a pick to pass. Tests that
# specifically test the safety halt should set SAFETY_HALT_GATE_ENABLED=1 explicitly.
os.environ.setdefault("SAFETY_HALT_GATE_ENABLED", "0")
# Anti-overfit validator (DSR/PBO) defaults ON since 2026-05-13. Pre-existing tests
# use strategy fixtures that have real closed-trade history (e.g. forex_rsi2_mean_reversion
# n>=20) whose DSR/PBO may fail the gate, causing tests written to exercise OTHER gates
# (e.g. test_smart_gate_uses_strategy_score_overrides_for_proven_non_crypto) to
# short-circuit before reaching the gate under test. Tests that specifically exercise
# the anti-overfit gate (test_anti_overfit_validator.py, already ignored in CI) manage
# this env themselves.
os.environ.setdefault("ANTI_OVERFIT_VALIDATOR_ENABLED", "0")
# EQUITY elite_score gate (>=55, 2026-05-16). Pre-existing EQUITY test fixtures
# use picks with elite_score in the 40-54 band (all historical EQUITY picks are
# in that range). Tests that specifically exercise this gate set
# EQUITY_ML_SCORE_GATE_ENABLED=1 explicitly.
os.environ.setdefault("EQUITY_ML_SCORE_GATE_ENABLED", "0")
# CRYPTO_PRODUCTION_BLOCK_LONG landed in Grok commit b9ffae732c (2026-06-05).
# Default ON in quality_gates.py via _truthy(env, "1"). Blocks all CRYPTO
# LONG picks at admission. Tests that pre-date this gate (most of
# test_quality_gates.py, test_crypto_gates_p0.py, test_phase1_active_gates.py)
# fixture CRYPTO LONG picks for OTHER gates and would fail spuriously.
# Tests specifically exercising this gate (none yet, future) set
# CRYPTO_PRODUCTION_BLOCK_LONG=1 + CRYPTO_PRODUCTION_BLOCK_LONG_OVERRIDE=1.
os.environ.setdefault("CRYPTO_PRODUCTION_BLOCK_LONG", "0")
os.environ.setdefault("CRYPTO_PRODUCTION_BLOCK_LONG_OVERRIDE", "0")
# HF_QUALITY_GATE default flipped to ON 2026-04-28. Pre-existing test fixtures
# (test_hf_quality_gate_wire.py, test_hf_gate_default_on_safety.py) explicitly
# set HF_QUALITY_GATE_ENABLED=0 to test the OFF path; those still work. But
# OTHER tests (test_m097_book_direction_conflict.py, etc.) that don't manage
# the env get the ON default, which blocks picks via hf-dead-band / hf-lag-bt.
# Tests that specifically test the HF gate set HF_QUALITY_GATE_ENABLED=1; the
# rest default to OFF here.
os.environ.setdefault("HF_QUALITY_GATE_ENABLED", "0")
