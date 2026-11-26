"""Every dashboard payload must be strict JSON.

`json.loads` accepts the bare tokens `NaN` / `Infinity`, and `json.dumps` emits
them by default (`allow_nan=True`). Browsers do not accept them, and `ci.yml`'s
"deployable static tree is consistent" build gate rejects the whole tree when it
finds one.

On 2026-11-26 two producers shipped bare `NaN` into gate-checked payloads and
turned the build red (`ueps_picks.json`, then `forex_futures_picks.json` minutes
after the first was repaired). The writers now sanitise, but a new producer
calling `json.dump` without `allow_nan=False` would reintroduce the defect
silently until CI next runs. This test makes the directory a regression guard so
the failure names every offending file in one pass.

Run:
    python3 -m pytest tests/test_dashboard_payload_strict_json.py -q
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Directories whose *.json is published/consumed by the dashboards and the CI
#: strict-JSON build gate. Reports are excluded: some are hand-written logs.
PAYLOAD_DIRS = [
    REPO_ROOT / "audit_dashboard" / "data",
    REPO_ROOT / "multi_asset" / "data",
]

#: Cheap byte pre-filter: only files that merely *contain* the token need the
#: strict parse. A string such as "NaN handling" is fine — the parse decides.
_NON_FINITE = (b"NaN", b"Infinity")
_TOKEN_RE = re.compile(r"[:\[,]\s*(?:NaN|-?Infinity)")


def _payloads() -> list[Path]:
    files: list[Path] = []
    for d in PAYLOAD_DIRS:
        if d.is_dir():
            files.extend(sorted(d.glob("*.json")))
    return files


def _reject_constant(token: str):
    raise ValueError(f"non-strict JSON constant {token!r} (use null)")


def test_payload_directories_exist() -> None:
    """Guard against the scan silently matching nothing if paths move."""
    assert _payloads(), f"no *.json found under {[str(d) for d in PAYLOAD_DIRS]}"


def test_no_non_finite_json_constants() -> None:
    offenders: list[str] = []
    for path in _payloads():
        raw = path.read_bytes()
        if not any(tok in raw for tok in _NON_FINITE):
            continue  # fast path: no candidate token at all
        try:
            json.loads(raw, parse_constant=_reject_constant)
        except ValueError as exc:
            hit = _TOKEN_RE.search(raw.decode("utf-8", "replace"))
            where = f" first at ...{hit.group(0)[-40:]!r}" if hit else ""
            offenders.append(f"{path.relative_to(REPO_ROOT)}: {exc}{where}")

    assert not offenders, (
        "non-strict JSON in dashboard payloads (browsers and the ci.yml build "
        "gate reject these; the producing writer must sanitise non-finite floats "
        "to null and pass allow_nan=False):\n  " + "\n  ".join(offenders)
    )


@pytest.mark.parametrize("path", _payloads(), ids=lambda p: p.name)
def test_payload_parses(path: Path) -> None:
    """Each payload must at least be valid JSON (catches truncated writes)."""
    json.loads(path.read_bytes(), parse_constant=_reject_constant)
