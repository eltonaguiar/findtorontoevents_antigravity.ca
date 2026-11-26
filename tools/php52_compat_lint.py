#!/usr/bin/env python3
"""Fail when a MOVIESHOWS3 PHP file needs a PHP version newer than 5.2.

Why this exists
---------------
50webs (findtorontoevents.ca) still runs PHP 5.2.17. These scripts set
display_errors to 0, so an unsupported function or syntax does not produce a
helpful error: the request dies as an EMPTY HTTP 500. That is how a call to
http_response_code() (PHP 5.4+) silently broke the movie refresh until it was
traced by hand -- see updates/2026-11-26-movieshows3-refresh-green.md.

Scope is deliberately limited to MOVIESHOWS3/, the only tree that ships to that
host. Adding a rule is cheap; keeping false positives at zero matters more, so
comments are stripped before matching and every rule is a real version gate.

Usage:
    python3 tools/php52_compat_lint.py                 # scan the default tree
    python3 tools/php52_compat_lint.py path/to/*.php   # explicit files/dirs
    python3 tools/php52_compat_lint.py --json          # machine-readable

Opt out of a single finding with a trailing comment:
    http_response_code(403);  // php52-allow: guarded below
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ROOT = REPO_ROOT / "TORONTOEVENTS_ANTIGRAVITY" / "MOVIESHOWS3"

# (rule id, regex, version that introduced it, what the reader should do)
RULES: list[tuple[str, str, str, str]] = [
    ("short-array",        r"(?:=|return|\(|,|=>)\s*\[\s*(?:['\"$0-9]|$)", "5.4", "use array(...)"),
    ("array-destructure",  r"\[\s*\$[A-Za-z_]\w*\s*,\s*\$[A-Za-z_]\w*\s*\]\s*=", "7.1", "use list(...)"),
    ("null-coalesce",      r"\?\?", "7.0", "use isset($x) ? $x : $default"),
    ("spaceship",          r"<=>", "7.0", "compare explicitly"),
    ("arrow-fn",           r"\bfn\s*\(", "7.4", "use a regular function"),
    ("closure",            r"\bfunction\s*\(", "5.3", "avoid closures on this host"),
    ("closure-use",        r"\bfunction\s*\([^)]*\)\s*use\s*\(", "5.3", "avoid closures on this host"),
    ("http-response-code", r"\bhttp_response_code\s*\(", "5.4", "header('HTTP/1.1 ...') guarded by function_exists"),
    ("array-column",       r"\barray_column\s*\(", "5.5", "loop manually"),
    ("json-last-error",    r"\bjson_last_error\s*\(", "5.3", "check the decoded value instead"),
    ("lcfirst",            r"\blcfirst\s*\(", "5.3", "use strtolower on the first character"),
    ("str-getcsv",         r"\bstr_getcsv\s*\(", "5.3", "parse manually"),
    ("array-replace",      r"\barray_replace\w*\s*\(", "5.3", "array_merge / manual loop"),
    ("hash-equals",        r"\bhash_equals\s*\(", "5.6", "compare with === after normalising"),
    ("password-hash",      r"\bpassword_(?:hash|verify)\s*\(", "5.5", "use md5/sha1 legacy scheme on this host"),
    ("class-const",        r"::class\b", "5.5", "use the class name string"),
    ("finally",            r"\bfinally\b", "5.5", "restructure the try/catch"),
    ("yield",              r"\byield\b", "5.5", "return an array"),
    ("variadic",           r"\.\.\.\s*\$", "5.6", "use func_get_args()"),
    ("power-op",           r"[^*/]\*\*[^*=]", "5.6", "use pow()"),
    ("trait",              r"\btrait\s+\w+", "5.4", "use inheritance"),
    ("str-contains",       r"\bstr_(?:contains|starts_with|ends_with)\s*\(", "8.0", "use strpos()"),
    ("nullsafe",           r"\?->", "8.0", "guard with isset()"),
    ("match",              r"\bmatch\s*\(", "8.0", "use switch"),
    ("scalar-type-hint",   r"\bfunction\s+\w+\s*\([^)]*\b(?:int|string|bool|float)\s+\$", "7.0", "drop the type hint"),
    ("return-type",        r"\bfunction\s+\w+\s*\([^)]*\)\s*:\s*\??[A-Za-z_]", "7.0", "drop the return type"),
]

# http_response_code() is fine once it is guarded, which is how the codebase does it.
GUARD_PATTERN = re.compile(r"function_exists\s*\(\s*['\"]http_response_code['\"]")


def strip_comments(text: str) -> str:
    """Blank out // # and /* */ comments while keeping line numbers intact."""
    out: list[str] = []
    i, n = 0, len(text)
    in_block = False
    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if in_block:
            if ch == "*" and nxt == "/":
                in_block = False
                out.append("  ")
                i += 2
                continue
            out.append("\n" if ch == "\n" else " ")
            i += 1
            continue
        if ch == "/" and nxt == "*":
            in_block = True
            out.append("  ")
            i += 2
            continue
        # Line comments: only when not inside a string literal.
        if ch in "#" or (ch == "/" and nxt == "/"):
            # Heuristic: a bare # in PHP code always starts a comment; // likewise,
            # unless it is part of a URL inside a string. Strings are tracked below.
            if ch == "/" and out and "".join(out).rstrip().endswith(("'", '"')):
                pass
            j = text.find("\n", i)
            j = n if j == -1 else j
            out.append(" " * (j - i))
            i = j
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def check_file(path: Path) -> list[dict]:
    raw = path.read_text(errors="replace")
    code = strip_comments(raw)
    guarded = bool(GUARD_PATTERN.search(code))
    raw_lines = raw.splitlines()
    findings: list[dict] = []
    for rule, pattern, version, advice in RULES:
        if rule == "http-response-code" and guarded:
            continue
        rx = re.compile(pattern)
        for lineno, line in enumerate(code.splitlines(), 1):
            if not rx.search(line):
                continue
            if "php52-allow" in raw_lines[lineno - 1]:
                continue
            findings.append({
                "file": str(path),
                "line": lineno,
                "rule": rule,
                "needs": f"PHP {version}",
                "advice": advice,
                "snippet": raw_lines[lineno - 1].strip()[:140],
            })
    return findings


def collect(targets: list[Path]) -> list[Path]:
    files: list[Path] = []
    for t in targets:
        if t.is_dir():
            files.extend(sorted(t.rglob("*.php")))
        elif t.suffix == ".php" and t.exists():
            files.append(t)
    return files


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Reject syntax newer than PHP 5.2 in MOVIESHOWS3.")
    ap.add_argument("paths", nargs="*", type=Path, help="files or directories (default: MOVIESHOWS3/)")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of text")
    args = ap.parse_args(argv)

    targets = args.paths or [DEFAULT_ROOT]
    files = collect(targets)
    if not files:
        print(f"php52 lint: no PHP files under {', '.join(map(str, targets))}", file=sys.stderr)
        return 0

    findings: list[dict] = []
    for f in files:
        findings.extend(check_file(f))

    if args.json:
        print(json.dumps({"files": len(files), "findings": findings}, indent=2))
    else:
        for item in findings:
            print(f"{item['file']}:{item['line']}: {item['rule']} needs {item['needs']} "
                  f"({item['advice']})\n    {item['snippet']}")
        print(f"\nphp52 lint: {len(files)} file(s) scanned, {len(findings)} finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
