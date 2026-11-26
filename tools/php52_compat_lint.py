#!/usr/bin/env python3
"""Fail when a MOVIESHOWS3 PHP file needs a PHP version newer than 5.2.

Why this exists
---------------
50webs (findtorontoevents.ca) still runs PHP 5.2.17. These scripts set
display_errors to 0, so an unsupported function or syntax does not produce a
helpful error: the request dies as an EMPTY HTTP 500. That is how a call to
http_response_code() (PHP 5.4+) silently broke the movie refresh until it was
traced by hand -- see updates/2026-11-26-movieshows3-refresh-green.md.

Scope is every tree that ships to that host: MOVIESHOWS3/, MOVIESHOWS2/ and
favcreators/docs (which deploys as /fc/). Adding a rule is cheap; keeping false
positives at zero matters more, so comments AND string literals are stripped
before matching, and every rule is a real version gate.

Trees that already contain legacy violations can be baselined: only findings that
are NOT in the baseline fail the build, so the gate is useful today instead of
after a large risky refactor.

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
DEFAULT_ROOTS = [
    REPO_ROOT / "TORONTOEVENTS_ANTIGRAVITY" / "MOVIESHOWS3",
    REPO_ROOT / "TORONTOEVENTS_ANTIGRAVITY" / "MOVIESHOWS2",
    REPO_ROOT / "favcreators" / "docs",
]
BASELINE = REPO_ROOT / "tools" / "php52_baseline.json"

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


def php_regions(text: str) -> str:
    """Blank everything outside <?php ... ?> so inline JS/HTML is never matched.

    The /fc pages embed jQuery with .then(function() {...}); treating that as a PHP
    closure was a false positive class.
    """
    out = list(text)
    i, n = 0, len(text)
    while i < n:
        m = re.compile(r"<\?(php|=)?").search(text, i)
        if not m:
            for j in range(i, n):
                if out[j] != "\n":
                    out[j] = " "
            break
        for j in range(i, m.end()):
            out[j] = " " if out[j] != "\n" else "\n"
        end = text.find("?>", m.end())
        i = n if end == -1 else end + 2
    return "".join(out)


def strip_comments(text: str) -> str:
    """Blank out // # and /* */ comments and the inside of string literals.

    Strings matter as much as comments: markdown like "**Note:**" inside a PHP
    string literal otherwise trips the power-operator rule.
    """
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
        if ch in ("'", '"'):
            quote = ch
            out.append(ch)
            i += 1
            while i < n:
                c = text[i]
                if c == "\\" and i + 1 < n:
                    out.append("  ")
                    i += 2
                    continue
                if c == quote:
                    out.append(c)
                    i += 1
                    break
                out.append("\n" if c == "\n" else " ")
                i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def check_file(path: Path) -> list[dict]:
    raw = path.read_text(errors="replace")
    code = strip_comments(php_regions(raw))
    # The guard pattern lives inside a string literal, which strip_comments blanks,
    # so it has to be matched against the raw source.
    guarded = bool(GUARD_PATTERN.search(raw))
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


def _rel(path: str) -> str:
    """Repository-relative key that works for absolute and relative inputs."""
    p = Path(path)
    try:
        return p.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return p.as_posix()


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
    ap.add_argument("--write-baseline", action="store_true",
                    help="record current findings as the accepted baseline")
    args = ap.parse_args(argv)

    targets = args.paths or list(DEFAULT_ROOTS)
    files = collect(targets)
    if not files:
        print(f"php52 lint: no PHP files under {', '.join(map(str, targets))}", file=sys.stderr)
        return 0

    findings: list[dict] = []
    for f in files:
        findings.extend(check_file(f))

    known = json.loads(BASELINE.read_text()) if BASELINE.exists() else {}
    counts: dict[str, int] = {}
    for item in findings:
        key = f"{_rel(item['file'])}|{item['rule']}"
        counts[key] = counts.get(key, 0) + 1
    new_findings = []
    consumed: dict[str, int] = {}
    for item in findings:
        key = f"{_rel(item['file'])}|{item['rule']}"
        allowed = known.get(key, 0)
        consumed[key] = consumed.get(key, 0) + 1
        if consumed[key] > allowed:
            new_findings.append(item)

    if args.write_baseline:
        BASELINE.write_text(json.dumps(dict(sorted(counts.items())), indent=2) + "\n")
        print(f"php52 lint: baseline written with {len(counts)} key(s) -> {BASELINE}", file=sys.stderr)
        return 0

    if args.json:
        print(json.dumps({"files": len(files), "findings": new_findings,
                          "baselined": len(findings) - len(new_findings)}, indent=2))
    else:
        for item in new_findings:
            print(f"{item['file']}:{item['line']}: {item['rule']} needs {item['needs']} "
                  f"({item['advice']})\n    {item['snippet']}")
        print(f"\nphp52 lint: {len(files)} file(s) scanned, {len(new_findings)} new finding(s), "
              f"{len(findings) - len(new_findings)} baselined")
    return 1 if new_findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
