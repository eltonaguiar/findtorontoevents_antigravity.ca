"""Gate: published PHP must be loadable on the production PHP 5.2.17 host (todo 7).

WHY THIS EXISTS
---------------
The goldmines API shipped to production with a closure (`set_error_handler(function(){...})`).
Closures are PHP 5.3+. The host runs 5.2.17, so the file could not compile and every
`?action=` request 500'd at the parser -- while the page rendered fine, because HTML does not
need PHP to parse. The repo already had tools/validate_php52.py; nothing was gating with it.

This test does not add a new checker. It wires the existing one to a path that is published.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
VALIDATOR = ROOT / "tools" / "validate_php52.py"

# Paths that are SERVED and therefore must parse on the host.
GATED_PATHS = [
    ROOT / "investments",
]


@pytest.mark.parametrize("path", [p for p in GATED_PATHS if p.exists()],
                         ids=[p.name for p in GATED_PATHS if p.exists()])
def test_php52_clean(path):
    r = subprocess.run([sys.executable, str(VALIDATOR), str(path)],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, (
        f"PHP 5.2 incompatibilities in {path.name} -- these files are served by a "
        f"PHP 5.2.17 host and will fail at PARSE time:\n{r.stdout}{r.stderr}"
    )


def test_kimi_api_has_no_closure():
    """Regression pin for the exact defect: no anonymous function in the served API."""
    f = ROOT / "investments" / "goldmines" / "kimi" / "kimi_goldmine_api.php"
    if not f.exists():
        pytest.skip("kimi api not vendored")
    src = f.read_text(encoding="utf-8", errors="replace")
    assert "set_error_handler(function" not in src, "closure reintroduced (PHP 5.2 cannot parse it)"
    assert "set_error_handler('goldmine_api_error_handler')" in src


def test_kimi_api_has_no_short_array_literals():
    """Short array syntax is PHP 5.4+. Only literals matter; subscripts are legal in 5.2."""
    f = ROOT / "investments" / "goldmines" / "kimi" / "kimi_goldmine_api.php"
    if not f.exists():
        pytest.skip("kimi api not vendored")
    src = f.read_text(encoding="utf-8", errors="replace")
    # json_encode(['...']) is the literal form that broke; array('...') is correct.
    assert "json_encode(['" not in src
    assert "json_encode(array(" in src
