"""Tests for tools/php52_compat_lint.py — the PHP 5.2 gate for MOVIESHOWS3."""

import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import php52_compat_lint as lint  # noqa: E402


def _write(tmp_path, name, body):
    p = tmp_path / name
    p.write_text(body)
    return p


def test_flags_http_response_code(tmp_path):
    f = _write(tmp_path, "a.php", "<?php\nhttp_response_code(403);\n")
    file = lint.check_file(f)
    assert [x["rule"] for x in file] == ["http-response-code"]


def test_allows_guarded_http_response_code(tmp_path):
    body = (
        "<?php\n"
        "if (function_exists('http_response_code')) { http_response_code(403); }\n"
        "header('HTTP/1.1 403 Forbidden');\n"
    )
    f = _write(tmp_path, "b.php", body)
    assert lint.check_file(f) == []


def test_ignores_comments(tmp_path):
    f = _write(tmp_path, "c.php", "<?php\n// no ?? operator and no [1,2] here\n/* http_response_code(403) */\n")
    assert lint.check_file(f) == []


def test_flags_null_coalesce_and_short_array(tmp_path):
    f = _write(tmp_path, "d.php", "<?php\n$x = $a ?? 1;\n$y = ['a' => 1];\n")
    rules = {x["rule"] for x in lint.check_file(f)}
    assert {"null-coalesce", "short-array"} <= rules


def test_php52_allow_escape_hatch(tmp_path):
    f = _write(tmp_path, "e.php", "<?php\n$x = $a ?? 1; // php52-allow: legacy\n")
    assert lint.check_file(f) == []


def test_clean_file_passes(tmp_path):
    f = _write(tmp_path, "f.php", "<?php\n$y = array('a' => 1);\nif (isset($a)) { $x = $a; }\n")
    assert lint.check_file(f) == []


def test_repository_tree_is_clean():
    """The shipped MOVIESHOWS3 tree must stay 5.2-clean."""
    findings = []
    for php in lint.DEFAULT_ROOT.rglob("*.php"):
        findings.extend(lint.check_file(php))
    assert findings == [], findings
