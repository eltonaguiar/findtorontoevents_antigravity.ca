import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def test_dashboard_generator_keeps_shadow_score_field():
    text = _read("audit_trail/dashboard_generator.py")
    assert "smart_score_v2_shadow" in text


def test_dashboard_generator_emits_system_stale_metadata():
    text = _read("audit_trail/dashboard_generator.py")
    assert '"is_stale": _is_stale' in text
    assert '"stale_days": _stale_days' in text


def test_hc_filter_has_dsr_gate_wiring():
    text = _read("audit_dashboard/hc_filter.js")
    assert "function _passesDsrGate" in text
    assert "hf_dsr_below_min" in text


def test_multi_asset_cot_verifier_dry_run():
    proc = subprocess.run(
        ["python", "tools/verify_multi_asset_cot_db.py", "--dry-run"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    out = proc.stdout
    assert "status breakdown" in out
    assert "aggregate PF/WR" in out
