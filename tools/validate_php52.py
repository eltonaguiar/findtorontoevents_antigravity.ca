#!/usr/bin/env python3
"""Validate PHP files for constructs that break the production PHP 5.2 host."""

from __future__ import print_function

import os
import re
import sys


CHECKS = (
    ("null coalescing ??", re.compile(r"\?\?")),
    ("short ternary ?:", re.compile(r"\?:")),
    ("short array syntax []", re.compile(r"(^|[=\(,\{]\s*)\[[^\]\r\n]*[,\=>][^\]\r\n]*\]")),
    ("anonymous function", re.compile(r"\bfunction\s*\(")),
    ("__DIR__", re.compile(r"\b__DIR__\b")),
    ("http_response_code()", re.compile(r"\bhttp_response_code\s*\(")),
    ("late static binding", re.compile(r"\bstatic::")),
    ("namespace", re.compile(r"^\s*namespace\b")),
    ("trait", re.compile(r"^\s*trait\b")),
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
            lines = fh.readlines()
    except IOError as exc:
        return [(path, 0, "read error", str(exc))]

    for line_no, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("#") or stripped.startswith("*"):
            continue
        for label, pattern in CHECKS:
            if pattern.search(line):
                errors.append((path, line_no, label, stripped))
    return errors


def main(argv):
    paths = argv[1:]
    if not paths:
        paths = ["."]

    all_errors = []
    checked = 0
    for path in iter_php_files(paths):
        if not path.endswith(".php"):
            continue
        checked += 1
        all_errors.extend(validate_file(path))

    if all_errors:
        for path, line_no, label, line in all_errors:
            print("%s:%s: %s: %s" % (path, line_no, label, line))
        print("PHP 5.2 validation failed: %s issue(s) in %s file(s)" % (len(all_errors), checked))
        return 1

    print("PHP 5.2 validation passed: %s file(s)" % checked)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
