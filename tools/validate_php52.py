#!/usr/bin/env python3
"""Validate PHP files for constructs that break the production PHP 5.2 host.

Production runs PHP 5.2.17 at 50webs with no shell access, so a file using a
newer construct does not merely misbehave -- it fails at PARSE time, before a
single line executes. This validator is therefore a deploy gate and must be
correct in BOTH directions: never PASS a file that would 500, never FAIL working
code.

This tool previously produced a FALSE PASS. Its short-array rule was

    (^|[=\\(,\\{]\\s*)\\[[^\\]\\r\\n]*[,\\=>][^\\]\\r\\n]*\\]

which requires the whole literal on ONE line, so multi-line literals -- how
everyone writes nested config arrays -- never matched. It also had no rule for
function-call array dereferencing (``$x->m()['k']``, PHP 5.4+). It printed
"PHP 5.2 validation passed: 7 file(s)" for two goldmines files that then
returned ``Parse error`` from the live host immediately after deploy.

Detection is now done by a string/comment-aware tokeniser rather than line
regexes, so multi-line literals and dereferences are caught, while URL strings
such as ``/findmutualfunds2/portfolio2/...`` can never look like syntax.
Regression: ``tests/test_php52_goldmines.py``.
Docs: ``updates/2026-11-23-goldmines-php52-deploy.md``.
"""

from __future__ import print_function

import os
import re
import sys


# --------------------------------------------------------------------------
# Tokeniser-aware structural scan
#
# WHY THIS EXISTS: the original version of this validator used a single line
# regex for short arrays,
#
#     (^|[=\(,\{]\s*)\[[^\]\r\n]*[,\=>][^\]\r\n]*\]
#
# which requires the ENTIRE literal to sit on one line. Multi-line literals --
# how everyone writes nested config arrays -- never matched, so this tool
# declared "passed: 7 file(s)" for two goldmines files that then returned
# "Parse error" from the live PHP 5.2 host. It also had no rule at all for
# function-call array dereferencing ($x->m()['k'], PHP 5.4+). A deploy gate that
# reports PASS on a file that cannot parse is worse than no gate, so the rule is
# now enforced by a scanner that understands strings and comments.
# --------------------------------------------------------------------------


def _strip_noncode(src):
    """Blank out string bodies and comments, preserving newlines and offsets."""
    out = list(src)
    i = 0
    n = len(src)

    def blank(start, end):
        for k in range(start, min(end, n)):
            if out[k] != "\n":
                out[k] = " "

    while i < n:
        c = src[i]
        if src.startswith("//", i) or c == "#":
            j = src.find("\n", i)
            j = n if j < 0 else j
            blank(i, j)
            i = j
            continue
        if src.startswith("/*", i):
            j = src.find("*/", i + 2)
            j = n if j < 0 else j + 2
            blank(i, j)
            i = j
            continue
        if c in "\"'":
            q = c
            j = i + 1
            while j < n:
                if src[j] == "\\":
                    j += 2
                    continue
                if src[j] == q:
                    break
                j += 1
            blank(i + 1, j)
            i = j + 1
            continue
        if src.startswith("<<<", i):
            m = re.match(r"<<<[ \t]*([\'\"]?)([A-Za-z_]\w*)\1\r?\n", src[i:])
            if m:
                tag = m.group(2)
                end = re.search(r"\n" + tag + r"\b", src[i:])
                stop = i + (end.end() if end else (n - i))
                blank(i, stop)
                i = stop
                continue
        i += 1
    return "".join(out)


_LITERAL_PREV = set(["=", "(", ",", "[", ":", "?", "{", "}", ";"])
_IDENT = re.compile(r"\$?[A-Za-z_]\w*")


def scan_php54(src):
    """Return [(line, label), ...] for PHP 5.3+/5.4+ constructs.

    Catches short array literals (multi-line aware), function-call array
    dereferencing, and closures.
    """
    findings = []
    stack = []
    prev = None
    i = 0
    n = len(src)
    line = 1

    while i < n:
        c = src[i]
        if c == "\n":
            line += 1
            i += 1
            continue
        if src.startswith("//", i) or c == "#":
            j = src.find("\n", i)
            i = n if j < 0 else j
            continue
        if src.startswith("/*", i):
            j = src.find("*/", i + 2)
            seg = src[i : (n if j < 0 else j + 2)]
            line += seg.count("\n")
            i += len(seg)
            continue
        if c in "\"'":
            q = c
            j = i + 1
            while j < n:
                if src[j] == "\\":
                    j += 2
                    continue
                if src[j] == q:
                    break
                j += 1
            line += src[i : j + 1].count("\n")
            i = j + 1
            prev = "str"
            continue
        if src.startswith("<<<", i):
            m = re.match(r"<<<[ \t]*([\'\"]?)([A-Za-z_]\w*)\1\r?\n", src[i:])
            if m:
                tag = m.group(2)
                end = re.search(r"\n" + tag + r"\b", src[i:])
                stop = i + (end.end() if end else (n - i))
                line += src[i:stop].count("\n")
                i = stop
            prev = "str"
            continue
        if c.isspace():
            i += 1
            continue
        if src.startswith("=>", i):
            prev = "=>"
            i += 2
            continue
        if c == "[":
            if prev in _LITERAL_PREV or prev is None or prev in ("=>", "return"):
                findings.append(
                    (line, "short array syntax [] (PHP 5.4+, catches multi-line)")
                )
                stack.append("lit")
            elif prev == ")":
                findings.append(
                    (line, "function-call array dereference )['k'] (PHP 5.4+)")
                )
                stack.append("idx")
            else:
                stack.append("idx")
            prev = "["
            i += 1
            continue
        if c == "]":
            if stack:
                stack.pop()
            prev = "]"
            i += 1
            continue
        m = _IDENT.match(src, i)
        if m:
            tok = m.group(0)
            prev = "return" if tok == "return" else "ident"
            i = m.end()
            continue
        prev = c
        i += 1

    return findings


CHECKS = (
    ("null coalescing ??", re.compile(r"\?\?")),
    ("short ternary ?:", re.compile(r"\?:")),
    ("anonymous function / closure", re.compile(r"\bfunction\s*\(")),
    ("__DIR__", re.compile(r"\b__DIR__\b")),
    ("http_response_code()", re.compile(r"\bhttp_response_code\s*\(")),
    ("late static binding", re.compile(r"\bstatic::")),
    ("namespace", re.compile(r"^\s*namespace\b")),
    ("trait", re.compile(r"^\s*trait\b")),
    ("generator yield", re.compile(r"^\s*yield\b")),
    ("finally block", re.compile(r"\bfinally\s*\{")),
)


def iter_php_files(paths):
    for path in paths:
        if os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "vendor")]
                for name in files:
                    if name.endswith(".php"):
                        yield os.path.join(root, name)
        else:
            yield path


def validate_file(path):
    errors = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            src = fh.read()
    except IOError as exc:
        return [(path, 0, "read error", str(exc))]

    # 1. tokeniser-aware structural scan (multi-line safe)
    for line_no, label in scan_php54(src):
        errors.append((path, line_no, label, ""))

    # 2. line-oriented checks, run against de-stringed source so URLs and
    #    SQL literals cannot produce phantom hits
    raw_lines = src.split("\n")
    for line_no, line in enumerate(_strip_noncode(src).split("\n"), 1):
        if not line.strip():
            continue
        for label, pattern in CHECKS:
            if pattern.search(line):
                errors.append(
                    (path, line_no, label, raw_lines[line_no - 1].strip())
                )
    return errors


def main(argv):
    paths = argv[1:] or ["."]

    all_errors = []
    checked = 0
    for path in iter_php_files(paths):
        if not path.endswith(".php"):
            continue
        checked += 1
        all_errors.extend(validate_file(path))

    if all_errors:
        for path, line_no, label, line in all_errors:
            suffix = (": " + line) if line else ""
            print("%s:%s: %s%s" % (path, line_no, label, suffix))
        print("PHP 5.2 validation failed: %s issue(s) in %s file(s)" % (len(all_errors), checked))
        return 1

    print("PHP 5.2 validation passed: %s file(s)" % checked)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
