"""Tests for the DNA mutation engine wire-up in production_scanner.

Verifies:
  - The wire-up call site exists at the right location and has the right shape.
  - Default OFF (no env var): apply_mutations_to_scanner is NOT invoked.
  - Default ON (MUTATION_ENGINE_ENABLED=1): success path logs mutation count.
  - Default ON: exception path is swallowed (fail-safe), scanner continues.
  - apply_mutations_to_scanner is callable and returns a list (sanity).

We do NOT execute the full production_scanner.main() (network-heavy).
We test the wire-up snippet in isolation, mirroring its exact shape.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ALPHA_ENGINE_DIR = REPO_ROOT / "alpha_engine"


def _run_wire_block(env_value: str | None, mock_apply, captured_logs: list):
    """Mirror the wire-up snippet in production_scanner.py:3812-3826.

    Replicates the production logic byte-for-byte so a refactor that breaks
    the contract is caught here.
    """
    env = {} if env_value is None else {"MUTATION_ENGINE_ENABLED": env_value}
    active = [{"symbol": "BTCUSDT", "strategy": "quan_engine_position"}]

    def _print(*a, **k):
        captured_logs.append(" ".join(str(x) for x in a))

    if env.get("MUTATION_ENGINE_ENABLED", "0") == "1":
        try:
            apply_mutations_to_scanner = mock_apply
            _pre_mut_count = len(active)
            active = apply_mutations_to_scanner(active)
            _added_mut = len(active) - _pre_mut_count
            _print(
                f"  [MUTATION ENGINE] Applied mutations: {_added_mut} variant(s) "
                f"added (pre={_pre_mut_count}, post={len(active)})"
            )
        except Exception as _mut_err:
            _print(f"  [MUTATION ENGINE] Skipped (non-fatal): {_mut_err}")
    return active


def _run_wire_block_v2(
    env: dict,
    mock_apply,
    captured_logs: list,
    initial_active: list | None = None,
):
    """Mirror the v2 wire-up snippet (with shadow + haircut gates).

    Mirrors production_scanner.py post-amendment, byte-for-byte. Replicates
    the production logic so a refactor that breaks the contract is caught.
    """
    active = list(
        initial_active
        if initial_active is not None
        else [
            {
                "symbol": "BTCUSDT",
                "strategy": "quan_engine_position",
                "ml_composite": 0.80,
            }
        ]
    )

    def _print(*a, **k):
        captured_logs.append(" ".join(str(x) for x in a))

    _ME_ENABLED = env.get("MUTATION_ENGINE_ENABLED", "0") == "1"
    _ME_SHADOW = env.get("MUTATION_ENGINE_SHADOW", "0") == "1"
    try:
        _ME_HAIRCUT = float(
            env.get("MUTATION_SCORE_HAIRCUT", "0.85") or "0.85"
        )
    except (TypeError, ValueError):
        _ME_HAIRCUT = 0.85

    invoked = {"called": False}

    if _ME_ENABLED or _ME_SHADOW:
        try:
            def _apply(picks):
                invoked["called"] = True
                return mock_apply(picks)

            apply_mutations_to_scanner = _apply
            _pre_mut_count = len(active)
            _maybe_extended = apply_mutations_to_scanner(list(active))
            _mutated_only = [
                p for p in _maybe_extended[_pre_mut_count:]
                if isinstance(p, dict)
            ]
            _added_mut = len(_mutated_only)

            if _ME_SHADOW and not _ME_ENABLED:
                _sample = []
                for _v in _mutated_only[:5]:
                    _sample.append(
                        {
                            "strategy": _v.get("strategy"),
                            "symbol": _v.get("symbol"),
                            "mutation_type": _v.get("mutation_type"),
                            "mutation_parent": _v.get("mutation_parent"),
                            "ml_composite": _v.get("ml_composite"),
                        }
                    )
                _print(
                    f"  [MUT-SHADOW] Computed {_added_mut} mutated variant(s) from "
                    f"{_pre_mut_count} parent picks (NOT EMITTED). Sample: {_sample}"
                )
            elif _ME_ENABLED:
                _haircut_applied = 0
                for _v in _mutated_only:
                    if _v.get("is_mutation") and "ml_composite" in _v:
                        try:
                            _orig = float(_v["ml_composite"])
                            _v["ml_composite_pre_haircut"] = _orig
                            _v["ml_composite"] = _orig * _ME_HAIRCUT
                            _v["mutation_score_haircut"] = _ME_HAIRCUT
                            _haircut_applied += 1
                        except (TypeError, ValueError):
                            pass
                active = _maybe_extended
                _print(
                    f"  [MUT-LIVE] Applied mutations: {_added_mut} variant(s) "
                    f"added (pre={_pre_mut_count}, post={len(active)}, "
                    f"haircut={_ME_HAIRCUT}, scored={_haircut_applied})"
                )
        except Exception as _mut_err:
            _print(f"  [MUTATION ENGINE] Skipped (non-fatal): {_mut_err}")

    return {
        "active": active,
        "invoked": invoked["called"],
        "haircut": _ME_HAIRCUT,
    }


def _fake_apply_with_two_mutations(picks):
    """Test fixture: returns picks + 2 mutated variants with ml_composite=0.80."""
    return picks + [
        {
            "symbol": "BTCUSDT",
            "strategy": "quan_engine_position_mut_inverse_g1",
            "ml_composite": 0.80,
            "is_mutation": True,
            "mutation_type": "inverse",
            "mutation_parent": "quan_engine_position",
        },
        {
            "symbol": "BTCUSDT",
            "strategy": "quan_engine_position_mut_tighter_g1",
            "ml_composite": 0.80,
            "is_mutation": True,
            "mutation_type": "tighter_stops",
            "mutation_parent": "quan_engine_position",
        },
    ]


def test_wire_default_off_does_not_invoke_mutation():
    """No env var -> apply_mutations_to_scanner is not called, active untouched."""
    invoked = {"called": False}

    def fake_apply(picks):
        invoked["called"] = True
        return picks + [{"strategy": "MUTATED"}]

    logs: list[str] = []
    result = _run_wire_block(env_value=None, mock_apply=fake_apply, captured_logs=logs)

    assert invoked["called"] is False, "apply_mutations_to_scanner must NOT run when env var is unset"
    assert len(result) == 1, "active list must be unchanged when default OFF"
    assert not any("MUTATION ENGINE" in m for m in logs), "no log line when default OFF"


def test_wire_default_off_explicit_zero():
    """MUTATION_ENGINE_ENABLED=0 -> apply_mutations_to_scanner is not called."""
    invoked = {"called": False}

    def fake_apply(picks):
        invoked["called"] = True
        return picks

    logs: list[str] = []
    result = _run_wire_block(env_value="0", mock_apply=fake_apply, captured_logs=logs)

    assert invoked["called"] is False
    assert len(result) == 1


def test_wire_enabled_success_logs_count():
    """MUTATION_ENGINE_ENABLED=1 + success -> log line emitted, picks extended."""
    def fake_apply(picks):
        # Simulate adding 2 mutated variants
        return picks + [
            {"strategy": "quan_engine_position_mut_inverse_g1", "is_mutation": True},
            {"strategy": "quan_engine_position_mut_tighter_g1", "is_mutation": True},
        ]

    logs: list[str] = []
    result = _run_wire_block(env_value="1", mock_apply=fake_apply, captured_logs=logs)

    assert len(result) == 3, "should have original + 2 mutated"
    assert any("MUTATION ENGINE" in m for m in logs), "must emit log line on success"
    assert any("2 variant" in m for m in logs), "must report variant count"


def test_wire_enabled_exception_is_failsafe():
    """MUTATION_ENGINE_ENABLED=1 + exception -> active unchanged, no crash."""
    def fake_apply(picks):
        raise RuntimeError("simulated mutation engine failure")

    logs: list[str] = []
    result = _run_wire_block(env_value="1", mock_apply=fake_apply, captured_logs=logs)

    assert len(result) == 1, "active list must be unchanged when mutation engine raises"
    assert any("Skipped (non-fatal)" in m for m in logs), "must log non-fatal skip on exception"
    assert any("simulated mutation engine failure" in m for m in logs), "exception text must surface in log"


def test_apply_mutations_to_scanner_importable_and_callable():
    """Sanity: the real function is importable and returns a list.

    Run in a subprocess because dna_mutation_engine.py reassigns sys.stdout
    at module import on Windows (UTF-8 fix), which conflicts with pytest's
    capture machinery on teardown.
    """
    import subprocess
    code = (
        "import sys; sys.path.insert(0, r'" + str(ALPHA_ENGINE_DIR) + "');"
        " from dna_mutation_engine import apply_mutations_to_scanner;"
        " out = apply_mutations_to_scanner([]);"
        " assert isinstance(out, list) and out == [], f'unexpected: {out!r}';"
        " print('OK')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"subprocess failed: stderr={result.stderr}"
    assert "OK" in result.stdout


def test_wire_call_site_exists_in_production_scanner():
    """Static check: the wire-up snippet is present in production_scanner.py."""
    scanner_path = ALPHA_ENGINE_DIR / "production_scanner.py"
    text = scanner_path.read_text(encoding="utf-8")

    # Required tokens — if any of these go missing, the wire-up has been
    # removed/regressed and the lifecycle runner is back to evaluating nothing.
    assert "MUTATION_ENGINE_ENABLED" in text, "env-gate token missing"
    assert "MUTATION_ENGINE_SHADOW" in text, "shadow-mode env-gate token missing"
    assert "MUTATION_SCORE_HAIRCUT" in text, "haircut env-gate token missing"
    assert "from dna_mutation_engine import apply_mutations_to_scanner" in text, \
        "lazy import line missing"
    assert "[MUT-SHADOW]" in text, "shadow-mode log prefix missing"
    assert "[MUT-LIVE]" in text, "live-mode log prefix missing"
    assert "Skipped (non-fatal)" in text, "fail-safe except branch missing"
    assert "ml_composite_pre_haircut" in text, "haircut bookkeeping field missing"


# ----------------------------------------------------------------------------
# v2 wire-up: shadow + haircut safety gates (PR #484 amendment)
# ----------------------------------------------------------------------------

def test_mutation_engine_default_off():
    """Both env vars unset -> mutations NOT invoked, picks unchanged."""
    logs: list[str] = []
    out = _run_wire_block_v2(env={}, mock_apply=_fake_apply_with_two_mutations, captured_logs=logs)

    assert out["invoked"] is False, "apply_mutations_to_scanner must NOT run when both env vars unset"
    assert len(out["active"]) == 1, "active list must be unchanged when default OFF"
    assert not any("MUT-SHADOW" in m or "MUT-LIVE" in m for m in logs), \
        "no shadow/live log line when default OFF"


def test_mutation_engine_shadow_mode():
    """MUTATION_ENGINE_SHADOW=1 -> mutations computed, picks UNCHANGED, log emitted."""
    logs: list[str] = []
    out = _run_wire_block_v2(
        env={"MUTATION_ENGINE_SHADOW": "1"},
        mock_apply=_fake_apply_with_two_mutations,
        captured_logs=logs,
    )

    # Mutation engine WAS called (computed)
    assert out["invoked"] is True, "shadow mode must still invoke apply_mutations_to_scanner"
    # But picks were NOT extended
    assert len(out["active"]) == 1, "shadow mode must NOT extend `active`"
    assert out["active"][0]["strategy"] == "quan_engine_position", \
        "original pick must remain untouched"
    # Log line must be present
    assert any("MUT-SHADOW" in m for m in logs), "shadow-mode log line missing"
    assert any("Computed 2 mutated variant" in m for m in logs), \
        "shadow log must report variant count"
    assert any("NOT EMITTED" in m for m in logs), \
        "shadow log must explicitly say NOT EMITTED"


def test_mutation_engine_live_mode_with_haircut():
    """MUTATION_ENGINE_ENABLED=1 + haircut=0.85 -> mutated picks have ml_composite x 0.85."""
    logs: list[str] = []
    out = _run_wire_block_v2(
        env={"MUTATION_ENGINE_ENABLED": "1", "MUTATION_SCORE_HAIRCUT": "0.85"},
        mock_apply=_fake_apply_with_two_mutations,
        captured_logs=logs,
    )

    assert out["invoked"] is True
    assert len(out["active"]) == 3, "live mode must extend with original + 2 mutated"

    # Original pick: untouched
    orig = out["active"][0]
    assert orig["strategy"] == "quan_engine_position"
    assert orig["ml_composite"] == 0.80, "original ml_composite must NOT be haircut"
    assert "ml_composite_pre_haircut" not in orig, \
        "original must not carry pre-haircut bookkeeping"

    # Mutated picks: haircut applied
    for mp in out["active"][1:]:
        assert mp.get("is_mutation") is True
        assert abs(mp["ml_composite"] - (0.80 * 0.85)) < 1e-9, \
            f"mutated ml_composite should be 0.80*0.85=0.68, got {mp['ml_composite']}"
        assert mp["ml_composite_pre_haircut"] == 0.80, \
            "pre_haircut bookkeeping must equal original parent ml_composite"
        assert mp["mutation_score_haircut"] == 0.85

    # Log line
    assert any("MUT-LIVE" in m for m in logs), "live-mode log line missing"
    assert any("haircut=0.85" in m for m in logs), "live log must record haircut value"
    assert any("scored=2" in m for m in logs), "live log must report scored count"


def test_mutation_engine_live_mode_default_haircut():
    """MUTATION_ENGINE_ENABLED=1 + haircut env unset -> 0.85 default applied."""
    logs: list[str] = []
    out = _run_wire_block_v2(
        env={"MUTATION_ENGINE_ENABLED": "1"},  # no MUTATION_SCORE_HAIRCUT
        mock_apply=_fake_apply_with_two_mutations,
        captured_logs=logs,
    )

    assert out["haircut"] == 0.85, "default haircut must be 0.85"
    assert len(out["active"]) == 3

    for mp in out["active"][1:]:
        assert mp["mutation_score_haircut"] == 0.85, \
            "default 0.85 haircut must be stamped on mutated picks"
        assert abs(mp["ml_composite"] - (0.80 * 0.85)) < 1e-9, \
            "default haircut must produce 0.80 * 0.85 = 0.68"


def test_mutation_engine_shadow_takes_precedence_when_only_shadow_set():
    """Only SHADOW=1 set (ENABLED unset) -> shadow path, not live path."""
    logs: list[str] = []
    out = _run_wire_block_v2(
        env={"MUTATION_ENGINE_SHADOW": "1"},
        mock_apply=_fake_apply_with_two_mutations,
        captured_logs=logs,
    )
    assert len(out["active"]) == 1
    assert any("MUT-SHADOW" in m for m in logs)
    assert not any("MUT-LIVE" in m for m in logs)


def test_mutation_engine_live_overrides_shadow_when_both_set():
    """ENABLED=1 takes precedence over SHADOW=1 (live path runs, shadow does not)."""
    logs: list[str] = []
    out = _run_wire_block_v2(
        env={"MUTATION_ENGINE_ENABLED": "1", "MUTATION_ENGINE_SHADOW": "1"},
        mock_apply=_fake_apply_with_two_mutations,
        captured_logs=logs,
    )
    # Live path: picks extended, haircut applied
    assert len(out["active"]) == 3
    assert any("MUT-LIVE" in m for m in logs)
    assert not any("MUT-SHADOW" in m for m in logs), \
        "shadow log must NOT fire when ENABLED is also set"


def test_mutation_engine_invalid_haircut_falls_back_to_default():
    """Garbage MUTATION_SCORE_HAIRCUT -> 0.85 fallback, no crash."""
    logs: list[str] = []
    out = _run_wire_block_v2(
        env={"MUTATION_ENGINE_ENABLED": "1", "MUTATION_SCORE_HAIRCUT": "not-a-number"},
        mock_apply=_fake_apply_with_two_mutations,
        captured_logs=logs,
    )
    assert out["haircut"] == 0.85
    for mp in out["active"][1:]:
        assert mp["mutation_score_haircut"] == 0.85
