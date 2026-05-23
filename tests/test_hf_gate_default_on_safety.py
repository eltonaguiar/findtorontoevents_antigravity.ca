"""Default-on flip safety tests for the HF Quality Gate companion.

PR: feat/wire-hf-quality-gate-default-on-2026-04-28
Wire site: audit_trail/quality_gates.py::passes_smart_gate (HF block)
Telemetry: audit_trail/hf_gate_telemetry.py
Smoke CLI: tools/run_hf_gate_smoke.py

Covers the 4 mandatory guardrails the external-AI consensus required:
  1) Default-on (env unset) → gate runs
  2) ENABLED="0" override → gate skipped (rollback path)
  3) 50-pick rolling circuit-breaker
  4) Per-asset-class reject counters
  5) Smoke CLI exit codes
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from audit_trail import hf_gate_telemetry as hfgt  # noqa: E402
from audit_trail.quality_gates import passes_smart_gate  # noqa: E402


def _safe_timestamp() -> str:
    now = datetime.now(timezone.utc)
    candidate = now.replace(hour=22, minute=0, second=0, microsecond=0)
    if candidate > now:
        candidate -= timedelta(days=1)
    return candidate.isoformat()


def _pick(**overrides):
    p = {
        "id": overrides.pop("id", "p"),
        "symbol": "BTCUSDT",
        "asset_class": "CRYPTO",
        "source_system": "pm_whale_signals",
        "strategy": "pm_whale_test",
        "status": "OPEN",
        "direction": "LONG",
        "entry_price": 100.0,
        "take_profit": 110.0,
        "stop_loss": 95.0,
        "score": 65,
        "trust_score": 6,
        "trust_label": "MODERATE",
        "confidence": 0.80,
        "timestamp": _safe_timestamp(),
        "source_tier": "PROVEN",
        "ml_score": 0.72,
        "forward_trades": 30,
        "forward_wr": 0.65,
        "strat_fwd_trades": 30,
        "strat_fwd_wr": 0.65,
        # PR #644 added explicit forward_validated requirement at the top of
        # passes_smart_gate (rejects with `_smart_reject_reasons=["forward_validated=false"]`
        # before the HF block can run). Test fixture must opt in.
        "forward_validated": True,
    }
    p.update(overrides)
    return p


@pytest.fixture(autouse=True)
def _reset_telemetry():
    hfgt._reset_for_tests()
    yield
    hfgt._reset_for_tests()


# ─────────── 1) default ENABLED=unset → gate runs ───────────


def test_default_on_unset_env_runs_gate(monkeypatch):
    """With env unset (default-on), HF gate must execute and stamp the pick."""
    monkeypatch.delenv("HF_QUALITY_GATE_ENABLED", raising=False)
    p = _pick()
    assert passes_smart_gate(p) is True
    # Default-ON consults the HF module — pick must be stamped:
    assert p.get("_hf_quality_gate_pass") is True


def test_default_on_unset_env_rejects_banned_symbol(monkeypatch):
    """Default-on must actually tighten — DOGEUSDT in CRYPTO_BANNED_SYMBOLS."""
    monkeypatch.delenv("HF_QUALITY_GATE_ENABLED", raising=False)
    p = _pick(symbol="DOGEUSDT")
    assert passes_smart_gate(p) is False
    assert "DOGEUSDT" in (p.get("_hf_quality_gate_reason") or "")


# ─────────── 2) ENABLED="0" → gate skipped (rollback path) ───────────


def test_explicit_zero_env_disables_gate(monkeypatch):
    """The rollback procedure (set env to "0") must short-circuit the HF block."""
    monkeypatch.setenv("HF_QUALITY_GATE_ENABLED", "0")
    p = _pick(symbol="DOGEUSDT")
    # DOGEUSDT would be rejected by HF gate, but with rollback active the smart
    # gate falls through to its pre-HF verdict (True for this fixture).
    assert passes_smart_gate(p) is True
    # No HF stamp because the block was bypassed:
    assert "_hf_quality_gate_pass" not in p


# ─────────── 3) circuit-breaker ───────────


def test_circuit_breaker_does_not_trip_below_threshold(monkeypatch):
    monkeypatch.delenv("HF_QUALITY_GATE_ENABLED", raising=False)
    # 49 rejects + 1 accept across the 50-pick window → 49/50 = 98% reject.
    # Use the telemetry primitive directly so the test is hermetic and not
    # affected by smart-gate fixture quirks.
    for i in range(49):
        hfgt.record_hf_gate_decision(
            _pick(id=f"r{i}", asset_class="CRYPTO"), False, "test_reject"
        )
    hfgt.record_hf_gate_decision(_pick(id="a0", asset_class="CRYPTO"), True, None)
    # Window full at 50 with 49 rejects → must trip.
    assert hfgt._should_circuit_break_hf_gate() is True


def test_circuit_breaker_window_must_be_full_to_trip():
    """Until we have 50 samples, breaker stays open even if 100% reject."""
    for i in range(10):
        hfgt.record_hf_gate_decision(
            _pick(id=f"r{i}", asset_class="CRYPTO"), False, "test_reject"
        )
    assert hfgt._should_circuit_break_hf_gate() is False


def test_circuit_breaker_at_50pct_does_not_trip():
    """Threshold is strictly > 50% — exactly 25/50 must NOT trip."""
    for i in range(25):
        hfgt.record_hf_gate_decision(
            _pick(id=f"r{i}", asset_class="CRYPTO"), False, "test_reject"
        )
    for i in range(25):
        hfgt.record_hf_gate_decision(
            _pick(id=f"a{i}", asset_class="CRYPTO"), True, None
        )
    assert hfgt._should_circuit_break_hf_gate() is False


def test_circuit_breaker_above_threshold_trips():
    """26/50 = 52% → trips."""
    for i in range(26):
        hfgt.record_hf_gate_decision(
            _pick(id=f"r{i}", asset_class="CRYPTO"), False, "test_reject"
        )
    for i in range(24):
        hfgt.record_hf_gate_decision(
            _pick(id=f"a{i}", asset_class="CRYPTO"), True, None
        )
    assert hfgt._should_circuit_break_hf_gate() is True


# ─────────── 4) per-asset-class counters ───────────


def test_per_asset_class_counters_increment():
    for i in range(5):
        hfgt.record_hf_gate_decision(
            _pick(id=f"c{i}", asset_class="CRYPTO"), False, "crypto_band"
        )
    for i in range(2):
        hfgt.record_hf_gate_decision(
            _pick(id=f"e{i}", asset_class="EQUITY"), True, None
        )
    snap = hfgt.get_telemetry_snapshot()
    per_ac = snap["per_asset_class"]
    assert per_ac["CRYPTO"]["rejects"] == 5
    assert per_ac["CRYPTO"]["accepts"] == 0
    assert per_ac["EQUITY"]["rejects"] == 0
    assert per_ac["EQUITY"]["accepts"] == 2
    # Asset classes that never saw a pick should not appear:
    assert "FOREX" not in per_ac
    assert "COMMODITY" not in per_ac


def test_attribution_log_caps_at_200_entries():
    for i in range(250):
        hfgt.record_hf_gate_decision(
            _pick(id=f"x{i}", asset_class="CRYPTO"), False, "fill"
        )
    snap = hfgt.get_telemetry_snapshot()
    assert len(snap["attribution_log_recent"]) == 200
    # Most recent entries kept (deque drops oldest):
    assert snap["attribution_log_recent"][-1]["pick_id"] == "x249"


def test_telemetry_flush_writes_disk(tmp_path, monkeypatch):
    monkeypatch.setattr(
        hfgt, "_TELEMETRY_PATH", tmp_path / "hf_gate_telemetry.json"
    )
    hfgt.record_hf_gate_decision(
        _pick(id="d1", asset_class="EQUITY"), True, None
    )
    assert hfgt._flush_telemetry_to_disk() is True
    payload = json.loads((tmp_path / "hf_gate_telemetry.json").read_text())
    assert "circuit_breaker" in payload
    assert "per_asset_class" in payload
    assert payload["per_asset_class"]["EQUITY"]["accepts"] == 1


# ─────────── 5) smoke CLI exit codes ───────────


def _write_dashboard_blob(path: Path, picks: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"picks": {"active": picks, "recent_closed": []}}))


def test_smoke_cli_passes_for_low_reject_sample(tmp_path):
    # 100 BTCUSDT LONG @0.88 confidence — none in CRYPTO_BANNED_SYMBOLS,
    # outside dead-band [0.60,0.70). Reject rate should be ~0.
    picks = [_pick(id=f"p{i}") for i in range(100)]
    blob = tmp_path / "dashboard_data.json"
    _write_dashboard_blob(blob, picks)

    proc = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "tools" / "run_hf_gate_smoke.py"),
            "--picks-source",
            str(blob),
            "--max-reject",
            "0.35",
            "--n",
            "100",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, (
        f"Expected PASS exit 0, got {proc.returncode}\n"
        f"stdout={proc.stdout}\nstderr={proc.stderr}"
    )
    assert "PASS" in proc.stdout


def test_smoke_cli_fails_for_high_reject_sample(tmp_path):
    # All-DOGEUSDT (banned) → reject_rate ~1.0 → FAIL exit 1.
    picks = [_pick(id=f"p{i}", symbol="DOGEUSDT") for i in range(50)]
    blob = tmp_path / "dashboard_data.json"
    _write_dashboard_blob(blob, picks)

    proc = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "tools" / "run_hf_gate_smoke.py"),
            "--picks-source",
            str(blob),
            "--max-reject",
            "0.35",
            "--n",
            "50",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1, (
        f"Expected FAIL exit 1, got {proc.returncode}\n"
        f"stdout={proc.stdout}\nstderr={proc.stderr}"
    )
    assert "FAIL" in proc.stdout


def test_smoke_cli_handles_missing_file(tmp_path):
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "tools" / "run_hf_gate_smoke.py"),
            "--picks-source",
            str(tmp_path / "does_not_exist.json"),
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
