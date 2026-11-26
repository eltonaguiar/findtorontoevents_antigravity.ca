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


# ---------------------------------------------------------------------------
# Regression tests for the VALIDATOR ITSELF (the second incident, 2026-11-23)
#
# The gate above passed two files that still contained 13 short-array literals
# and 6 function-call dereferences. The old short-array regex demanded the whole
# literal on one line, so multi-line literals were invisible to it, and there
# was no dereference rule at all. Both files then returned "Parse error" from
# the live PHP 5.2 host. A gate that PASSES unparseable code is worse than none,
# so the false-PASS cases are pinned here.
# ---------------------------------------------------------------------------

def _validate_source(tmp_path, body: str):
    """Write ``body`` as a .php file and return the validator CompletedProcess."""
    f = tmp_path / "sample.php"
    f.write_text(body, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(VALIDATOR), str(f)],
        capture_output=True, text=True, timeout=120,
    )


def test_validator_catches_multiline_short_array(tmp_path):
    """THE false-PASS case: a literal that opens at end-of-line."""
    r = _validate_source(tmp_path, "<?php\n$systems = array(\n")
    # sanity: a correctly written multi-line array must PASS
    ok = _validate_source(tmp_path, "<?php\n$systems = array(\n  'a' => 1\n);\n")
    assert ok.returncode == 0, ok.stdout

    r = _validate_source(tmp_path, "<?php\n$systems = [\n  'a' => 1\n];\n")
    assert r.returncode == 1, "multi-line short array literal was NOT caught:\n" + r.stdout
    assert "short array syntax" in r.stdout


def test_validator_catches_call_dereference(tmp_path):
    """$res->fetch_assoc()['c'] is PHP 5.4+ and must be flagged."""
    r = _validate_source(tmp_path, "<?php\n$x = $res->fetch_assoc()['c'];\n")
    assert r.returncode == 1, r.stdout
    assert "dereference" in r.stdout


def test_validator_allows_subscripts_and_url_strings(tmp_path):
    """No false positives: index writes and URL/string contents are legal 5.2."""
    body = (
        "<?php\n"
        "$a = array();\n"
        "$a['k'] = 1;\n"
        "$b[] = 2;\n"
        "$u = '/findmutualfunds2/portfolio2/api/data.php?type=stats';\n"
        "$q = \"SELECT x FROM t WHERE c = '{$a['k']}'\";\n"
        "echo json_encode(array('ok' => true));\n"
    )
    r = _validate_source(tmp_path, body)
    assert r.returncode == 0, "false positive on valid PHP 5.2:\n" + r.stdout


def test_validator_catches_dir_magic_constant(tmp_path):
    r = _validate_source(tmp_path, "<?php\n$f = __DIR__ . '/x.json';\n")
    assert r.returncode == 1, r.stdout
    assert "__DIR__" in r.stdout
