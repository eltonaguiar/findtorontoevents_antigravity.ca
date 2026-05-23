import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_supplemental_prework_audit_generates_report():
    out_rel = "reports/supplemental_prework_audit_2026_05_14_test.json"
    out_path = ROOT / out_rel
    if out_path.exists():
        out_path.unlink()

    proc = subprocess.run(
        ["python", "tools/supplemental_prework_audit.py", "--out", out_rel],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Wrote" in proc.stdout
    assert out_path.exists()

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert "checks" in payload
    checks = payload["checks"]
    assert "cot_db_verifier_dry_run" in checks
    assert "browser_drift_auto_paper_only" in checks
    assert "strategy_level_staleness_contract" in checks
    assert checks["cot_db_verifier_dry_run"]["status"] in {"COMPLETE", "PARTIAL", "MISSING"}
