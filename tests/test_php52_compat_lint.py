"""Tests for tools/php52_compat_lint.py — the PHP 5.2 gate for the 50webs trees."""

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


def test_movieshows_trees_are_clean():
    """MOVIESHOWS2 and MOVIESHOWS3 ship to 50webs and must stay 5.2-clean."""
    findings = []
    for root in lint.DEFAULT_ROOTS[:2]:
        for php in root.rglob("*.php"):
            findings.extend(lint.check_file(php))
    assert findings == [], findings


def test_full_repository_scan_passes_with_baseline():
    """The whole 50webs surface must pass the gate as configured in CI."""
    assert lint.main([]) == 0


def test_strings_are_not_code(tmp_path):
    """Markdown bold inside a PHP string must not trip the power-operator rule."""
    f = _write(tmp_path, "g.php", "<?php\necho '**Note:** this is bold';\n")
    assert lint.check_file(f) == []


def test_baseline_suppresses_known_findings(tmp_path, monkeypatch):
    import json as _json
    base = tmp_path / "baseline.json"
    base.write_text(_json.dumps({"a.php|http-response-code": 1}))
    monkeypatch.setattr(lint, "BASELINE", base)
    monkeypatch.setattr(lint, "REPO_ROOT", tmp_path)
    _write(tmp_path, "a.php", "<?php\nhttp_response_code(403);\n")
    assert lint.main([str(tmp_path)]) == 0  # known -> allowed


def test_baseline_still_fails_on_new_finding(tmp_path, monkeypatch):
    import json as _json
    base = tmp_path / "baseline.json"
    base.write_text(_json.dumps({"a.php|http-response-code": 1}))
    monkeypatch.setattr(lint, "BASELINE", base)
    monkeypatch.setattr(lint, "REPO_ROOT", tmp_path)
    _write(tmp_path, "a.php", "<?php\nhttp_response_code(403);\nhttp_response_code(500);\n")
    assert lint.main([str(tmp_path)]) == 1  # second call is new -> fails
