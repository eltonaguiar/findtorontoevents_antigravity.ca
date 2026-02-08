#!/usr/bin/env python3
"""
Validate PHP files for PHP 5.2 compatibility.

Scans PHP files for constructs that are NOT available in PHP 5.2, including:
  - Namespaces (namespace / use)
  - Closures / anonymous functions (function() { ... })
  - Short array syntax ([$a, $b])
  - Traits, generators, finally, yield
  - ::class constant
  - __DIR__ magic constant (use dirname(__FILE__) instead)
  - Short ternary ?: (added 5.3)
  - Null coalescing ?? (added 7.0)
  - Spaceship <=> (added 7.0)
  - Arrow functions fn() => (added 7.4)
  - http_response_code() (added 5.4)
  - Late static binding static:: (added 5.3)
  - goto (added 5.3)
  - nowdoc syntax (added 5.3)
  - Return / parameter type declarations (added 7.0)
  - Splat operator ... (added 5.6)
  - json_encode with options/flags (added 5.3)

Usage:
  python tools/validate_php52.py                     # Check all deployable PHP dirs
  python tools/validate_php52.py path/to/file.php    # Check a specific file
  python tools/validate_php52.py path/to/dir/        # Check all .php in a directory

Exit codes:
  0 = all files pass
  1 = one or more files have PHP 5.2 incompatibilities
"""

import os
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Patterns that indicate PHP > 5.2 constructs
# Each entry: (compiled_regex, human-readable description, severity)
# severity: "error" = must fix, "warning" = review
# ---------------------------------------------------------------------------
PATTERNS = [
    # --- PHP 5.3+ ---
    (
        re.compile(r'^\s*namespace\s+[A-Za-z]', re.MULTILINE),
        "namespace declaration (PHP 5.3+)",
        "error",
    ),
    (
        re.compile(r'^\s*use\s+[A-Z][A-Za-z0-9_\\]+\s*;', re.MULTILINE),
        "'use' import statement (PHP 5.3+)",
        "error",
    ),
    (
        re.compile(r'=\s*function\s*\('),
        "anonymous function / closure (PHP 5.3+)",
        "error",
    ),
    (
        # Closures as arguments: foo(function($x) { ... })
        re.compile(r'[,(]\s*function\s*\('),
        "closure passed as argument (PHP 5.3+)",
        "error",
    ),
    (
        re.compile(r'__DIR__'),
        "__DIR__ magic constant (PHP 5.3+) — use dirname(__FILE__)",
        "error",
    ),
    (
        # Short ternary: $x ?: $y  (but not  $x ? $y : $z)
        # NOTE: We match ?<optional-whitespace>: — in a full ternary there is always
        # a non-whitespace expression between ? and :, so \?\s*: only fires on short
        # ternaries.  The old negative lookahead (?![\s>]) wrongly excluded "?: ''"
        # (space after colon) — which is the most common real-world usage.
        # ?> (PHP close tag) has no colon, so \?\s*: can never match it.
        re.compile(r'\?\s*:(?!:)'),
        "short ternary ?: (PHP 5.3+)",
        "error",
    ),
    (
        re.compile(r'\bstatic\s*::'),
        "late static binding static:: (PHP 5.3+)",
        "error",
    ),
    (
        re.compile(r'^\s*goto\s+\w', re.MULTILINE),
        "goto statement (PHP 5.3+)",
        "error",
    ),
    (
        # nowdoc: <<<'IDENTIFIER'
        re.compile(r"<<<\s*'[A-Za-z_]+'\s*$", re.MULTILINE),
        "nowdoc syntax <<<'...' (PHP 5.3+)",
        "error",
    ),
    # json_encode with options is checked separately via _check_json_encode_options()
    # because simple regex can't handle nested parentheses.
    # --- PHP 5.4+ ---
    (
        re.compile(r'\bhttp_response_code\s*\('),
        "http_response_code() (PHP 5.4+) — use header('HTTP/1.1 ...')",
        "error",
    ),
    (
        # Short array syntax: = [  or  ([ or ,[ but NOT inside strings
        # Heuristic: look for  = [ or => [ or ( [ after non-$ char
        re.compile(r'(?<!=\s)(?:=|=>)\s*\[(?!\])'),
        "short array syntax [] (PHP 5.4+) — use array()",
        "error",
    ),
    (
        # Also catch [ used as array literal at start of statement / return
        re.compile(r'(?:return|echo)\s+\['),
        "short array syntax in return/echo (PHP 5.4+) — use array()",
        "error",
    ),
    (
        re.compile(r'\btrait\s+[A-Z]'),
        "trait declaration (PHP 5.4+)",
        "error",
    ),
    (
        re.compile(r'\buse\s+[A-Z][A-Za-z0-9_]+\s*;', re.MULTILINE),
        "trait 'use' inside class (PHP 5.4+)",
        "warning",  # also caught by namespace 'use' — warning to review
    ),
    # --- PHP 5.5+ ---
    (
        re.compile(r'::class\b'),
        "::class constant (PHP 5.5+)",
        "error",
    ),
    (
        re.compile(r'\bfinally\s*\{'),
        "finally block (PHP 5.5+)",
        "error",
    ),
    (
        re.compile(r'\byield\b'),
        "yield / generators (PHP 5.5+)",
        "error",
    ),
    # --- PHP 5.6+ ---
    (
        re.compile(r'\.\.\.\$'),
        "splat operator ...$ (PHP 5.6+)",
        "error",
    ),
    (
        re.compile(r'const\s+[A-Z_]+\s*=\s*.*(?:[\+\-\*\/]|\.)\s*'),
        "constant scalar expressions (PHP 5.6+)",
        "warning",
    ),
    # --- PHP 7.0+ ---
    (
        re.compile(r'\?\?'),
        "null coalescing ?? (PHP 7.0+)",
        "error",
    ),
    (
        re.compile(r'<=>'),
        "spaceship operator <=> (PHP 7.0+)",
        "error",
    ),
    (
        # Return type declaration:  function foo(): Type
        re.compile(r'function\s+\w+\s*\([^)]*\)\s*:\s*(?:int|string|float|bool|array|void|self|callable|iterable|\??\s*[A-Z])'),
        "return type declaration (PHP 7.0+)",
        "error",
    ),
    (
        # Scalar type hints in params:  function foo(int $x, string $y)
        re.compile(r'function\s+\w+\s*\(\s*(?:int|string|float|bool|callable|iterable)\s+\$'),
        "scalar type hint in parameter (PHP 7.0+)",
        "error",
    ),
    (
        # Nullable type hint: ?int, ?string
        re.compile(r'\?\s*(?:int|string|float|bool|array)\s+\$'),
        "nullable type hint (PHP 7.1+)",
        "error",
    ),
    # --- PHP 7.4+ ---
    (
        re.compile(r'\bfn\s*\('),
        "arrow function fn() (PHP 7.4+)",
        "error",
    ),
    (
        # Typed properties:  public int $x
        re.compile(r'(?:public|protected|private)\s+(?:int|string|float|bool|array|\??\s*[A-Z][A-Za-z0-9_]*)\s+\$'),
        "typed property declaration (PHP 7.4+)",
        "error",
    ),
    # --- PHP 8.0+ ---
    (
        re.compile(r'\bmatch\s*\('),
        "match expression (PHP 8.0+)",
        "error",
    ),
    (
        re.compile(r'\?\->'),
        "nullsafe operator ?-> (PHP 8.0+)",
        "error",
    ),
    (
        # Named arguments: func(name: value)
        re.compile(r'\b\w+\s*\(\s*[a-z_]+\s*:\s*(?!:)'),
        "named arguments (PHP 8.0+)",
        "warning",  # can false-positive on ternary in args
    ),
]

# Directories to check by default (relative to workspace root)
DEFAULT_DIRS = [
    "favcreators/public/api",
    "favcreators/docs/api",
    "api",
]

# Files/directories to skip
SKIP_NAMES = {".env", ".env.example", "vendor", "node_modules", "__pycache__"}


def strip_php_strings_and_comments(content):
    """
    Replace string literals and comments with placeholders so regex patterns
    don't match inside strings/comments. Returns cleaned content.
    """
    # Remove // single-line comments (but not inside strings)
    # Remove /* ... */ block comments
    # Remove '...' and "..." string contents
    # This is a rough heuristic — good enough for syntax scanning.
    result = []
    i = 0
    in_sq = False  # single quote
    in_dq = False  # double quote
    length = len(content)

    while i < length:
        c = content[i]

        # Inside single-quoted string
        if in_sq:
            if c == '\\' and i + 1 < length:
                result.append('  ')  # replace escape sequence
                i += 2
                continue
            if c == "'":
                in_sq = False
                result.append("'")
            else:
                result.append(' ')  # blank out string content
            i += 1
            continue

        # Inside double-quoted string
        if in_dq:
            if c == '\\' and i + 1 < length:
                result.append('  ')
                i += 2
                continue
            if c == '"':
                in_dq = False
                result.append('"')
            else:
                result.append(' ')
            i += 1
            continue

        # Check for string start
        if c == "'" and not in_dq:
            in_sq = True
            result.append("'")
            i += 1
            continue
        if c == '"' and not in_sq:
            in_dq = True
            result.append('"')
            i += 1
            continue

        # Check for // comment
        if c == '/' and i + 1 < length and content[i + 1] == '/':
            # Skip to end of line
            while i < length and content[i] != '\n':
                result.append(' ')
                i += 1
            continue

        # Check for /* ... */ comment
        if c == '/' and i + 1 < length and content[i + 1] == '*':
            result.append('  ')
            i += 2
            while i < length:
                if content[i] == '*' and i + 1 < length and content[i + 1] == '/':
                    result.append('  ')
                    i += 2
                    break
                if content[i] == '\n':
                    result.append('\n')
                else:
                    result.append(' ')
                i += 1
            continue

        # Check for # comment
        if c == '#':
            while i < length and content[i] != '\n':
                result.append(' ')
                i += 1
            continue

        result.append(c)
        i += 1

    return ''.join(result)


def _check_json_encode_options(cleaned_content):
    """
    Find json_encode() calls with a second argument (options parameter, PHP 5.3+).
    Uses parenthesis-depth counting so commas inside nested array()/function()
    calls don't cause false positives.
    Returns list of (line_number, description, severity).
    """
    issues = []
    # Find all json_encode( occurrences
    pattern = re.compile(r'json_encode\s*\(')
    for m in pattern.finditer(cleaned_content):
        start = m.end()  # position right after the opening '('
        depth = 1
        found_comma_at_depth_1 = False
        pos = start
        while pos < len(cleaned_content) and depth > 0:
            ch = cleaned_content[pos]
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
            elif ch == ',' and depth == 1:
                found_comma_at_depth_1 = True
                break
            pos += 1

        if found_comma_at_depth_1:
            # Count which line this is on
            line_num = cleaned_content[:m.start()].count('\n') + 1
            issues.append((line_num, "json_encode() with options parameter (PHP 5.3+)", "error"))

    return issues


def check_file(filepath):
    """
    Check a single PHP file for PHP 5.2 incompatibilities.
    Returns list of (line_number, description, severity).
    """
    issues = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            raw_content = f.read()
    except Exception as e:
        return [(-1, f"Could not read file: {e}", "error")]

    # Strip strings and comments to avoid false positives
    cleaned = strip_php_strings_and_comments(raw_content)
    lines = cleaned.split('\n')

    for pattern, description, severity in PATTERNS:
        for line_num, line in enumerate(lines, 1):
            if pattern.search(line):
                issues.append((line_num, description, severity))

    # Check json_encode with options (needs depth-aware parsing)
    issues.extend(_check_json_encode_options(cleaned))

    return issues


def find_php_files(path):
    """Recursively find all .php files under a path, skipping vendor/node_modules."""
    path = Path(path)
    if path.is_file() and path.suffix == '.php':
        return [path]
    if not path.is_dir():
        return []
    files = []
    for root, dirs, filenames in os.walk(path):
        dirs[:] = [d for d in dirs if d not in SKIP_NAMES]
        for name in filenames:
            if name.endswith('.php') and name not in SKIP_NAMES:
                files.append(Path(root) / name)
    return sorted(files)


def main():
    workspace = Path(__file__).resolve().parent.parent

    # Determine targets
    if len(sys.argv) > 1:
        targets = [Path(arg) for arg in sys.argv[1:]]
    else:
        targets = []
        for d in DEFAULT_DIRS:
            p = workspace / d
            if p.is_dir():
                targets.append(p)
        if not targets:
            print("No default PHP directories found. Specify a path.")
            sys.exit(1)

    # Collect all PHP files
    all_files = []
    for target in targets:
        if not target.is_absolute():
            target = workspace / target
        all_files.extend(find_php_files(target))

    if not all_files:
        print("No PHP files found.")
        sys.exit(0)

    print(f"Checking {len(all_files)} PHP files for PHP 5.2 compatibility...\n")

    total_errors = 0
    total_warnings = 0
    files_with_issues = 0

    for filepath in all_files:
        issues = check_file(filepath)
        if not issues:
            continue

        files_with_issues += 1
        try:
            rel = filepath.relative_to(workspace)
        except ValueError:
            rel = filepath

        errors = [i for i in issues if i[2] == "error"]
        warnings = [i for i in issues if i[2] == "warning"]
        total_errors += len(errors)
        total_warnings += len(warnings)

        # Deduplicate (same line + same description)
        seen = set()
        for line_num, desc, sev in issues:
            key = (line_num, desc)
            if key in seen:
                continue
            seen.add(key)
            marker = "ERROR" if sev == "error" else "WARN "
            print(f"  {marker}  {rel}:{line_num}  {desc}")

    print()
    if total_errors == 0 and total_warnings == 0:
        print(f"OK — {len(all_files)} files checked, all PHP 5.2 compatible.")
        sys.exit(0)
    else:
        print(f"RESULT: {files_with_issues} file(s) with issues")
        print(f"  {total_errors} error(s), {total_warnings} warning(s)")
        if total_errors > 0:
            print("\nFix all ERRORs before deploying. Warnings should be reviewed.")
            sys.exit(1)
        else:
            print("\nNo errors — warnings should be reviewed but won't block deploy.")
            sys.exit(0)


if __name__ == "__main__":
    main()
