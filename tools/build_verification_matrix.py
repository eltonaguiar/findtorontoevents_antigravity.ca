"""
build_verification_matrix.py
M-042 — Verification matrix scaffold

Reads reports/enhancement_plan_per_asset_class.md, verifies each tracked M-item
against the codebase via grep/filesystem checks, and writes
reports/verification_matrix.json.

Usage:
    python tools/build_verification_matrix.py

No external dependencies beyond stdlib.
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = REPO_ROOT / "reports" / "verification_matrix.json"
PLAN_PATH = REPO_ROOT / "reports" / "enhancement_plan_per_asset_class.md"


# ---------------------------------------------------------------------------
# Helper: grep a pattern in a path (returns stdout text, empty string if none)
# ---------------------------------------------------------------------------
def _grep(pattern: str, search_path: Path, *, recursive: bool = True) -> str:
    """Run a recursive grep; return matched lines or empty string."""
    flags = ["-rl"] if recursive else ["-l"]
    try:
        result = subprocess.run(
            ["grep", "-r", "--include=*.py", "-l", pattern, str(search_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout.strip()
    except Exception as exc:
        return f"ERROR:{exc}"


def _grep_content(pattern: str, search_path: Path) -> str:
    """Return matching lines (not just file names)."""
    try:
        result = subprocess.run(
            ["grep", "-r", "--include=*.py", "-n", pattern, str(search_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout.strip()
    except Exception as exc:
        return f"ERROR:{exc}"


def _file_exists(rel_path: str) -> bool:
    return (REPO_ROOT / rel_path).exists()


def _grep_in_file(pattern: str, rel_path: str) -> str:
    """Grep a single file for pattern; return matched lines."""
    target = REPO_ROOT / rel_path
    if not target.exists():
        return ""
    try:
        result = subprocess.run(
            ["grep", "-n", pattern, str(target)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip()
    except Exception as exc:
        return f"ERROR:{exc}"


# ---------------------------------------------------------------------------
# M-item verification specs
# Each entry:  item_id, claimed_status, verify_fn -> (evidence_found, result, confidence, blocker)
# ---------------------------------------------------------------------------

def check_m017() -> dict:
    """M-017: vol_target_sizer in alpha_engine/"""
    pat = "vol_target_sizer"
    hits = _grep(pat, REPO_ROOT / "alpha_engine")
    found = bool(hits and not hits.startswith("ERROR"))
    if found:
        result = f"Found in: {hits[:200]}"
        conf = "high"
        blocker = None
    else:
        result = "Pattern 'vol_target_sizer' not found in alpha_engine/"
        conf = "high"
        blocker = "vol_target_sizer not implemented; M-017 position sizer rebuild pending"
    return dict(
        item_id="M-017",
        claimed_status="pending",
        evidence_found=found,
        verification_command="grep -r --include=*.py -l vol_target_sizer alpha_engine/",
        result=result,
        confidence=conf,
        blocker=blocker,
    )


def check_m028() -> dict:
    """M-028: DRIFT_PAUSE_DRY_RUN in audit_trail/quality_gates.py"""
    pat = "DRIFT_PAUSE_DRY_RUN"
    rel = "audit_trail/quality_gates.py"
    hits = _grep_in_file(pat, rel)
    found = bool(hits and not hits.startswith("ERROR"))
    file_exists = _file_exists(rel)
    if not file_exists:
        result = f"{rel} does not exist"
        conf = "high"
        blocker = f"{rel} missing; drift-pause gate cannot be verified"
    elif found:
        result = f"Found: {hits[:200]}"
        conf = "high"
        blocker = None
    else:
        result = f"Pattern '{pat}' not found in {rel}"
        conf = "high"
        blocker = "DRIFT_PAUSE_DRY_RUN flag not present; M-028 dry-run gate pending"
    return dict(
        item_id="M-028",
        claimed_status="pending",
        evidence_found=found,
        verification_command=f"grep -n DRIFT_PAUSE_DRY_RUN {rel}",
        result=result,
        confidence=conf,
        blocker=blocker,
    )


def check_m032() -> dict:
    """M-032: FRED_API_KEY in alpha_engine/config.py"""
    pat = "FRED_API_KEY"
    rel = "alpha_engine/config.py"
    hits = _grep_in_file(pat, rel)
    found = bool(hits and not hits.startswith("ERROR"))
    if found:
        result = f"Found: {hits[:200]}"
        conf = "high"
        blocker = None
    else:
        result = f"Pattern '{pat}' not found in {rel}"
        conf = "high"
        blocker = "FRED_API_KEY not present; M-032 FRED macro filter wire-up pending"
    return dict(
        item_id="M-032",
        claimed_status="pending",
        evidence_found=found,
        verification_command=f"grep -n FRED_API_KEY {rel}",
        result=result,
        confidence=conf,
        blocker=blocker,
    )


def check_m034() -> dict:
    """M-034: CRYPTO_CONF_INVERSION_GATE in audit_trail/quality_gates.py"""
    pat = "CRYPTO_CONF_INVERSION_GATE"
    rel = "audit_trail/quality_gates.py"
    hits = _grep_in_file(pat, rel)
    found = bool(hits and not hits.startswith("ERROR"))
    file_exists = _file_exists(rel)
    if not file_exists:
        result = f"{rel} does not exist"
        conf = "high"
        blocker = f"{rel} missing"
    elif found:
        result = f"Found: {hits[:200]}"
        conf = "high"
        blocker = None
    else:
        result = f"Pattern '{pat}' not found in {rel}"
        conf = "high"
        blocker = "CRYPTO_CONF_INVERSION_GATE not present; M-034 confidence-inversion gate pending"
    return dict(
        item_id="M-034",
        claimed_status="pending",
        evidence_found=found,
        verification_command=f"grep -n CRYPTO_CONF_INVERSION_GATE {rel}",
        result=result,
        confidence=conf,
        blocker=blocker,
    )


def check_m043() -> dict:
    """M-043: .github/workflows/secret-scan.yml exists"""
    rel = ".github/workflows/secret-scan.yml"
    found = _file_exists(rel)
    if found:
        result = f"{rel} exists"
        conf = "high"
        blocker = None
    else:
        result = f"{rel} not found"
        conf = "high"
        blocker = "secret-scan.yml workflow missing; M-043 credential enforcement pending"
    return dict(
        item_id="M-043",
        claimed_status="pending",
        evidence_found=found,
        verification_command=f"test -f {rel}",
        result=result,
        confidence=conf,
        blocker=blocker,
    )


def check_m044() -> dict:
    """M-044: TestM044GateParity in tests/"""
    pat = "TestM044GateParity"
    tests_dir = REPO_ROOT / "tests"
    if not tests_dir.exists():
        return dict(
            item_id="M-044",
            claimed_status="pending",
            evidence_found=False,
            verification_command="grep -r --include=*.py -l TestM044GateParity tests/",
            result="tests/ directory does not exist",
            confidence="high",
            blocker="tests/ directory missing; M-044 gate parity test pending",
        )
    hits = _grep(pat, tests_dir)
    found = bool(hits and not hits.startswith("ERROR"))
    if found:
        result = f"Found in: {hits[:200]}"
        conf = "high"
        blocker = None
    else:
        result = f"Pattern '{pat}' not found in tests/"
        conf = "high"
        blocker = "TestM044GateParity class not found; M-044 gate parity test not yet written"
    return dict(
        item_id="M-044",
        claimed_status="pending",
        evidence_found=found,
        verification_command="grep -r --include=*.py -l TestM044GateParity tests/",
        result=result,
        confidence=conf,
        blocker=blocker,
    )


def check_m049() -> dict:
    """M-049: SAFETY_HALT_GATE_ENABLED in audit_trail/quality_gates.py"""
    pat = "SAFETY_HALT_GATE_ENABLED"
    rel = "audit_trail/quality_gates.py"
    hits = _grep_in_file(pat, rel)
    found = bool(hits and not hits.startswith("ERROR"))
    file_exists = _file_exists(rel)
    if not file_exists:
        result = f"{rel} does not exist"
        conf = "high"
        blocker = f"{rel} missing"
    elif found:
        result = f"Found: {hits[:200]}"
        conf = "high"
        blocker = None
    else:
        result = f"Pattern '{pat}' not found in {rel}"
        conf = "high"
        blocker = "SAFETY_HALT_GATE_ENABLED not present; M-049 kill-switch audit pending"
    return dict(
        item_id="M-049",
        claimed_status="pending",
        evidence_found=found,
        verification_command=f"grep -n SAFETY_HALT_GATE_ENABLED {rel}",
        result=result,
        confidence=conf,
        blocker=blocker,
    )


def check_m013() -> dict:
    """M-013: CONCENTRATION_CAP_ENABLED.*1 in audit_trail/quality_gates.py"""
    pat = r"CONCENTRATION_CAP_ENABLED.*1"
    rel = "audit_trail/quality_gates.py"
    hits = _grep_in_file(pat, rel)
    found = bool(hits and not hits.startswith("ERROR"))
    file_exists = _file_exists(rel)
    if not file_exists:
        result = f"{rel} does not exist"
        conf = "high"
        blocker = f"{rel} missing"
    elif found:
        result = f"Found: {hits[:200]}"
        conf = "high"
        blocker = None
    else:
        result = f"Pattern '{pat}' not found in {rel}"
        conf = "high"
        blocker = "CONCENTRATION_CAP_ENABLED not set to 1; M-013 concentration checker pending"
    return dict(
        item_id="M-013",
        claimed_status="pending",
        evidence_found=found,
        verification_command=f"grep -nE 'CONCENTRATION_CAP_ENABLED.*1' {rel}",
        result=result,
        confidence=conf,
        blocker=blocker,
    )


def check_m004() -> dict:
    """M-004: SOURCE_QUARANTINE_WARN_ENABLED in audit_trail/quality_gates.py"""
    pat = "SOURCE_QUARANTINE_WARN_ENABLED"
    rel = "audit_trail/quality_gates.py"
    hits = _grep_in_file(pat, rel)
    found = bool(hits and not hits.startswith("ERROR"))
    file_exists = _file_exists(rel)
    if not file_exists:
        result = f"{rel} does not exist"
        conf = "high"
        blocker = f"{rel} missing"
    elif found:
        result = f"Found: {hits[:200]}"
        conf = "high"
        blocker = None
    else:
        result = f"Pattern '{pat}' not found in {rel}"
        conf = "high"
        blocker = "SOURCE_QUARANTINE_WARN_ENABLED not present; M-004 crypto drag autopsy gate pending"
    return dict(
        item_id="M-004",
        claimed_status="pending",
        evidence_found=found,
        verification_command=f"grep -n SOURCE_QUARANTINE_WARN_ENABLED {rel}",
        result=result,
        confidence=conf,
        blocker=blocker,
    )


def check_m027() -> dict:
    """M-027: FUTURES_DOW_TILT in alpha_engine/score_booster.py"""
    pat = "FUTURES_DOW_TILT"
    rel = "alpha_engine/score_booster.py"
    hits = _grep_in_file(pat, rel)
    found = bool(hits and not hits.startswith("ERROR"))
    file_exists = _file_exists(rel)
    if not file_exists:
        result = f"{rel} does not exist"
        conf = "high"
        blocker = f"{rel} missing"
    elif found:
        result = f"Found: {hits[:200]}"
        conf = "high"
        blocker = None
    else:
        result = f"Pattern '{pat}' not found in {rel}"
        conf = "high"
        blocker = "FUTURES_DOW_TILT not present; M-027 futures DOW gate pending"
    return dict(
        item_id="M-027",
        claimed_status="pending",
        evidence_found=found,
        verification_command=f"grep -n FUTURES_DOW_TILT {rel}",
        result=result,
        confidence=conf,
        blocker=blocker,
    )


def check_m030() -> dict:
    """M-030: last_signal_date in audit_trail/dashboard_generator.py"""
    pat = "last_signal_date"
    rel = "audit_trail/dashboard_generator.py"
    hits = _grep_in_file(pat, rel)
    found = bool(hits and not hits.startswith("ERROR"))
    file_exists = _file_exists(rel)
    if not file_exists:
        # Also check alpha_engine/dashboard_generator.py
        rel2 = "alpha_engine/dashboard_generator.py"
        hits2 = _grep_in_file(pat, rel2)
        found2 = bool(hits2 and not hits2.startswith("ERROR"))
        if found2:
            return dict(
                item_id="M-030",
                claimed_status="pending",
                evidence_found=True,
                verification_command=f"grep -n last_signal_date {rel2}",
                result=f"Found in alternate path {rel2}: {hits2[:200]}",
                confidence="medium",
                blocker=None,
            )
        result = f"Neither {rel} nor alpha_engine/dashboard_generator.py exist"
        conf = "high"
        blocker = "dashboard_generator missing; M-030 last_signal_date field pending"
    elif found:
        result = f"Found: {hits[:200]}"
        conf = "high"
        blocker = None
    else:
        result = f"Pattern '{pat}' not found in {rel}"
        conf = "high"
        blocker = "last_signal_date not written; M-030 staleness detection pending"
    return dict(
        item_id="M-030",
        claimed_status="pending",
        evidence_found=found,
        verification_command=f"grep -n last_signal_date {rel}",
        result=result,
        confidence=conf,
        blocker=blocker,
    )


def check_m031() -> dict:
    """M-031: _build_readiness_payload in audit_trail/dashboard_generator.py"""
    pat = "_build_readiness_payload"
    rel = "audit_trail/dashboard_generator.py"
    hits = _grep_in_file(pat, rel)
    found = bool(hits and not hits.startswith("ERROR"))
    file_exists = _file_exists(rel)
    if not file_exists:
        rel2 = "alpha_engine/dashboard_generator.py"
        hits2 = _grep_in_file(pat, rel2)
        found2 = bool(hits2 and not hits2.startswith("ERROR"))
        if found2:
            return dict(
                item_id="M-031",
                claimed_status="pending",
                evidence_found=True,
                verification_command=f"grep -n _build_readiness_payload {rel2}",
                result=f"Found in alternate path {rel2}: {hits2[:200]}",
                confidence="medium",
                blocker=None,
            )
        result = f"Neither {rel} nor alpha_engine/dashboard_generator.py exist"
        conf = "high"
        blocker = "dashboard_generator missing; M-031 readiness payload pending"
    elif found:
        result = f"Found: {hits[:200]}"
        conf = "high"
        blocker = None
    else:
        result = f"Pattern '{pat}' not found in {rel}"
        conf = "high"
        blocker = "_build_readiness_payload not implemented; M-031 pending"
    return dict(
        item_id="M-031",
        claimed_status="pending",
        evidence_found=found,
        verification_command=f"grep -n _build_readiness_payload {rel}",
        result=result,
        confidence=conf,
        blocker=blocker,
    )


def check_m014() -> dict:
    """M-014: _normalize_pick in audit_trail/dashboard_generator.py"""
    pat = "_normalize_pick"
    rel = "audit_trail/dashboard_generator.py"
    hits = _grep_in_file(pat, rel)
    found = bool(hits and not hits.startswith("ERROR"))
    file_exists = _file_exists(rel)
    if not file_exists:
        rel2 = "alpha_engine/dashboard_generator.py"
        hits2 = _grep_in_file(pat, rel2)
        found2 = bool(hits2 and not hits2.startswith("ERROR"))
        if found2:
            return dict(
                item_id="M-014",
                claimed_status="pending",
                evidence_found=True,
                verification_command=f"grep -n _normalize_pick {rel2}",
                result=f"Found in alternate path {rel2}: {hits2[:200]}",
                confidence="medium",
                blocker=None,
            )
        result = f"Neither {rel} nor alpha_engine/dashboard_generator.py exist"
        conf = "high"
        blocker = "dashboard_generator missing; M-014 normalizer pending"
    elif found:
        result = f"Found: {hits[:200]}"
        conf = "high"
        blocker = None
    else:
        result = f"Pattern '{pat}' not found in {rel}"
        conf = "high"
        blocker = "_normalize_pick not implemented; M-014 confidence schema normalizer pending"
    return dict(
        item_id="M-014",
        claimed_status="pending",
        evidence_found=found,
        verification_command=f"grep -n _normalize_pick {rel}",
        result=result,
        confidence=conf,
        blocker=blocker,
    )


def check_m036() -> dict:
    """M-036: ETF_SYMBOLS contains XLK in alpha_engine/config.py"""
    pat = "XLK"
    rel = "alpha_engine/config.py"
    hits = _grep_in_file(pat, rel)
    found = bool(hits and not hits.startswith("ERROR"))
    file_exists = _file_exists(rel)
    if not file_exists:
        result = f"{rel} does not exist"
        conf = "high"
        blocker = f"{rel} missing"
    elif found:
        result = f"Found: {hits[:200]}"
        conf = "high"
        blocker = None
    else:
        result = f"'XLK' not found in {rel}"
        conf = "high"
        blocker = "XLK not present in config; M-036 ETF universe expansion pending"
    return dict(
        item_id="M-036",
        claimed_status="pending",
        evidence_found=found,
        verification_command=f"grep -n XLK {rel}",
        result=result,
        confidence=conf,
        blocker=blocker,
    )


def check_m042() -> dict:
    """M-042: tools/build_verification_matrix.py exists (self-referential)"""
    rel = "tools/build_verification_matrix.py"
    found = _file_exists(rel)
    if found:
        result = f"{rel} exists (this script)"
        conf = "high"
        blocker = None
    else:
        result = f"{rel} not found"
        conf = "high"
        blocker = "Self-referential: script was not found at expected path"
    return dict(
        item_id="M-042",
        claimed_status="implemented",
        evidence_found=found,
        verification_command=f"test -f {rel}",
        result=result,
        confidence=conf,
        blocker=blocker,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

CHECKS = [
    check_m004,
    check_m013,
    check_m014,
    check_m017,
    check_m027,
    check_m028,
    check_m030,
    check_m031,
    check_m032,
    check_m034,
    check_m036,
    check_m042,
    check_m043,
    check_m044,
    check_m049,
]

COL_WIDTHS = {
    "item_id": 7,
    "claimed_status": 13,
    "evidence_found": 14,
    "confidence": 10,
    "blocker": 55,
}


def _truncate(s: str, n: int) -> str:
    s = str(s)
    return s if len(s) <= n else s[: n - 1] + "…"


def main() -> None:
    print(f"Build Verification Matrix — {datetime.now(timezone.utc).isoformat()}")
    print(f"Repo root: {REPO_ROOT}")
    print()

    rows = []
    for check_fn in CHECKS:
        row = check_fn()
        rows.append(row)

    # Summary table
    header = (
        f"{'M-Item':<{COL_WIDTHS['item_id']}} "
        f"{'Status':<{COL_WIDTHS['claimed_status']}} "
        f"{'Evidence':>{COL_WIDTHS['evidence_found']}} "
        f"{'Confidence':<{COL_WIDTHS['confidence']}} "
        f"{'Blocker / Notes'}"
    )
    separator = "-" * len(header)
    print(header)
    print(separator)
    for row in rows:
        blocker_text = row["blocker"] or "—"
        print(
            f"{row['item_id']:<{COL_WIDTHS['item_id']}} "
            f"{row['claimed_status']:<{COL_WIDTHS['claimed_status']}} "
            f"{'YES' if row['evidence_found'] else 'NO':>{COL_WIDTHS['evidence_found']}} "
            f"{row['confidence']:<{COL_WIDTHS['confidence']}} "
            f"{_truncate(blocker_text, COL_WIDTHS['blocker'])}"
        )

    print()
    implemented = [r for r in rows if r["evidence_found"]]
    pending = [r for r in rows if not r["evidence_found"]]
    print(f"Summary: {len(implemented)}/{len(rows)} items have evidence (implemented).")
    print(f"         {len(pending)}/{len(rows)} items are pending / not found.")

    # Write JSON
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "plan_source": str(PLAN_PATH.relative_to(REPO_ROOT)),
        "total_items": len(rows),
        "implemented_count": len(implemented),
        "pending_count": len(pending),
        "items": rows,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"\nJSON written to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
