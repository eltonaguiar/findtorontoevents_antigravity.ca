"""Tests for alpha_engine.ml_drift_repair_workflow."""

import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from alpha_engine.ml_drift_repair_workflow import (  # noqa: E402
    CryptoDriftJobConfig,
    DriftHaltError,
    LookAheadBiasError,
    execute_repair_plan,
    prediction_distribution_drift,
    repair_recommendation,
    run_crypto_price_drift_job,
    write_drift_artifact,
)
from datetime import datetime, timezone  # noqa: E402


def test_prediction_drift_same_gaussian_low_drift():
    rng = np.random.default_rng(42)
    ref = rng.normal(0, 1.0, size=600)
    cur = rng.normal(0, 1.0, size=400)
    rep = prediction_distribution_drift(ref, cur)
    assert rep["reference_n"] == 600
    assert rep["current_n"] == 400
    assert rep["psi"] is not None
    # Same DGP: PSI should usually stay in the "stable" band; allow sampling slack.
    assert rep["psi"] < 0.25
    if rep.get("ks_pvalue") is not None:
        assert rep["ks_pvalue"] > 0.01


def test_prediction_drift_shifted_mean_raises_psi_and_low_ks_p():
    rng = np.random.default_rng(1)
    ref = rng.normal(0, 1.0, size=400)
    cur = rng.normal(0.8, 1.0, size=200)
    rep = prediction_distribution_drift(ref, cur)
    assert rep["psi"] is not None
    assert rep["psi"] > 0.10
    if rep.get("ks_pvalue") is not None:
        assert rep["ks_pvalue"] < 0.01


def test_repair_recommendation_insufficient():
    rep = {"note": "insufficient_samples", "psi": None}
    plan = repair_recommendation(rep)
    assert plan["tier"] == "none"


def test_execute_repair_plan_dry_run_no_command():
    plan = {"tier": "retrain", "reasons": ["psi>=0.25"]}
    out = execute_repair_plan(plan, dry_run=True, command_alias=None, env_var="___MISSING_ENV___")
    assert out["executed"] is False
    assert out.get("skipped") == "no_command_alias"


# ─────────────────────────────────────────────────────────────────────────
# CRITICAL-fix tests — 3 findings from code review on this PR
# ─────────────────────────────────────────────────────────────────────────


class TestHaltTierEnforced:
    """Finding #1: HALT enum existed but was never assigned and never enforced.
    Now: psi >= psi_critical (default 0.40) sets HALT; execute_repair_plan
    raises DriftHaltError when tier=='halt' and dry_run=False."""

    def test_psi_critical_sets_halt_tier(self):
        plan = repair_recommendation({"psi": 0.50, "ks_pvalue": 0.5})
        assert plan["tier"] == "halt"
        assert any("critical" in r for r in plan["reasons"])

    def test_psi_severe_still_retrain_not_halt(self):
        plan = repair_recommendation({"psi": 0.30, "ks_pvalue": 0.5})
        assert plan["tier"] == "retrain"

    def test_extreme_ks_pvalue_sets_halt(self):
        plan = repair_recommendation({"psi": 0.05, "ks_pvalue": 1e-6})
        assert plan["tier"] == "halt"

    def test_execute_raises_drift_halt_error_when_not_dry_run(self):
        plan = {"tier": "halt", "reasons": ["psi>=0.40_critical"]}
        with pytest.raises(DriftHaltError, match="critical threshold"):
            execute_repair_plan(plan, dry_run=False)

    def test_execute_dry_run_flags_would_halt(self):
        plan = {"tier": "halt", "reasons": ["psi>=0.40_critical"]}
        out = execute_repair_plan(plan, dry_run=True)
        assert out.get("would_halt") is True
        assert "halt_reason" in out


class TestCommandInjectionSurface:
    """Finding #2: free-form shell command was an injection vector. Now:
    only aliases in REPAIR_COMMAND_WHITELIST resolve to pre-split argv lists;
    subprocess.run called with shell=False; no shlex.split on user input."""

    def test_non_whitelisted_alias_rejected(self):
        plan = {"tier": "retrain"}
        out = execute_repair_plan(plan, dry_run=False, command_alias="rm -rf /; curl evil.com")
        assert out["executed"] is False
        assert out.get("skipped") == "alias_not_in_whitelist"

    def test_semicolon_command_cannot_inject(self):
        """Even in dry-run, a string with shell metacharacters doesn't execute."""
        plan = {"tier": "retrain"}
        out = execute_repair_plan(plan, dry_run=True, command_alias="alias; echo pwned")
        assert "would_run_argv" not in out  # never resolved the alias
        assert out.get("skipped") == "alias_not_in_whitelist"

    def test_whitelisted_alias_dry_run_resolves_argv(self):
        plan = {"tier": "retrain"}
        wl = {"safe_retrain": ["python", "-c", "print('ok')"]}
        out = execute_repair_plan(plan, dry_run=True, command_alias="safe_retrain", whitelist=wl)
        assert out.get("would_run_argv") == ["python", "-c", "print('ok')"]

    def test_empty_whitelist_alias_rejects_everything(self):
        plan = {"tier": "retrain"}
        out = execute_repair_plan(plan, dry_run=False, command_alias="anything", whitelist={})
        assert out["executed"] is False
        assert out.get("skipped") == "alias_not_in_whitelist"


class TestLookAheadBiasGuard:
    """Finding #3: prediction_distribution_drift accepted overlapping windows
    silently. Now: supplying both reference_end_time and current_start_time
    enforces strict temporal ordering; overlaps raise LookAheadBiasError."""

    def test_overlapping_windows_raise(self):
        rng = np.random.default_rng(0)
        ref = rng.normal(0, 1, 100)
        cur = rng.normal(0, 1, 50)
        with pytest.raises(LookAheadBiasError, match="strictly before"):
            prediction_distribution_drift(
                ref, cur,
                reference_end_time=datetime(2026, 4, 22, 12, tzinfo=timezone.utc),
                current_start_time=datetime(2026, 4, 22, 10, tzinfo=timezone.utc),
            )

    def test_valid_ordering_passes(self):
        rng = np.random.default_rng(0)
        ref = rng.normal(0, 1, 100)
        cur = rng.normal(0, 1, 50)
        out = prediction_distribution_drift(
            ref, cur,
            reference_end_time=datetime(2026, 4, 22, 10, tzinfo=timezone.utc),
            current_start_time=datetime(2026, 4, 22, 12, tzinfo=timezone.utc),
        )
        assert out["psi"] is not None

    def test_equal_times_strict_raises(self):
        rng = np.random.default_rng(0)
        ref = rng.normal(0, 1, 100)
        cur = rng.normal(0, 1, 50)
        t = datetime(2026, 4, 22, 12, tzinfo=timezone.utc)
        with pytest.raises(LookAheadBiasError):
            prediction_distribution_drift(ref, cur, reference_end_time=t, current_start_time=t)

    def test_equal_times_non_strict_allowed(self):
        rng = np.random.default_rng(0)
        ref = rng.normal(0, 1, 100)
        cur = rng.normal(0, 1, 50)
        t = datetime(2026, 4, 22, 12, tzinfo=timezone.utc)
        out = prediction_distribution_drift(
            ref, cur, reference_end_time=t, current_start_time=t, strict_ordering=False,
        )
        assert out["psi"] is not None

    def test_missing_times_no_guard_applied(self):
        """When caller doesn't supply times, no check is enforced — caller
        accepts responsibility per the docstring."""
        rng = np.random.default_rng(0)
        ref = rng.normal(0, 1, 100)
        cur = rng.normal(0, 1, 50)
        out = prediction_distribution_drift(ref, cur)
        assert out["psi"] is not None

    def test_naive_datetime_coerced_to_utc(self):
        rng = np.random.default_rng(0)
        ref = rng.normal(0, 1, 100)
        cur = rng.normal(0, 1, 50)
        # Naive datetimes — function should treat as UTC.
        out = prediction_distribution_drift(
            ref, cur,
            reference_end_time=datetime(2026, 4, 22, 10),
            current_start_time=datetime(2026, 4, 22, 12),
        )
        assert out["psi"] is not None


def test_run_crypto_price_drift_job_json(tmp_path):
    ref_path = tmp_path / "ref.json"
    cur_path = tmp_path / "cur.json"
    out_path = tmp_path / "out.json"
    ref_path.write_text(
        json.dumps([{"y_pred": 0.01 * i} for i in range(50)]), encoding="utf-8"
    )
    cur_path.write_text(
        json.dumps([{"y_pred": 0.5 + 0.01 * i} for i in range(30)]), encoding="utf-8"
    )
    res = run_crypto_price_drift_job(
        CryptoDriftJobConfig(
            reference_path=ref_path,
            current_path=cur_path,
            value_key="y_pred",
            out_path=out_path,
        )
    )
    assert "drift" in res and "plan" in res
    assert out_path.is_file()


def test_write_drift_artifact(tmp_path):
    p = tmp_path / "d.json"
    write_drift_artifact({"psi": 0.2}, {"tier": "monitor"}, p)
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["drift"]["psi"] == 0.2
    assert data["plan"]["tier"] == "monitor"
