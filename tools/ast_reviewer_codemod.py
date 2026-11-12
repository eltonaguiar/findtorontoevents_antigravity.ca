#!/usr/bin/env python3
"""Structural codemod: rewrite ONE key inside ONE named dict, chosen by AST position.

Why this exists
---------------
`.ruflo/orchestrator.py` keeps the same role keys in several different dicts:

    FREE_MODELS  = {"reviewer": "<openrouter model>", ...}   # OpenRouter pool
    LOCAL_MODELS = {"reviewer": "<ollama model>",     ...}   # local Ollama pool
    role_map     = {"reviewer": "<proxy alias>",      ...}   # LiteLLM alias map

A textual find/replace for `"reviewer"` hits all three (or the wrong one, when
the value is unquoted or the spacing differs), which is how repeated edit
attempts on that file end up changing a map nobody meant to touch.

This tool asks the syntax tree instead of the text: it locates the dict by its
assignment node, locates the key/value pair nodes inside it, and rewrites only
the first (or exactly --expect) pair whose byte range falls inside that dict.
Everything else in the file is untouched by construction, not by luck.

Usage
-----
Report where a key actually lives (no writes, no value needed):

    python3 tools/ast_reviewer_codemod.py .ruflo/orchestrator.py --key reviewer

Rewrite the OpenRouter entry (dry run prints a unified diff, exit 2):

    python3 tools/ast_reviewer_codemod.py .ruflo/orchestrator.py \\
        --dict FREE_MODELS --key reviewer --value 'vendor/model:free'

...and add --apply to write, with a backup and a syntax gate.

Exit codes: 0 applied/clean, 1 refused or error, 2 dry run produced a diff
(the same convention as tools/safe_patch.py).

Requires ast-grep (`ast-grep` on PATH, or --ast-grep, or $AST_GREP_BIN).
Install: npm install --prefix ~/.local/ast-grep @ast-grep/cli
"""

from __future__ import annotations

import argparse
import ast
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

BACKUP_DIR = Path("/tmp/safe_patch_backups")


# --------------------------------------------------------------------------
# ast-grep plumbing
# --------------------------------------------------------------------------
def find_ast_grep(explicit: str | None = None) -> str:
    """Locate the ast-grep binary. The `sg` alias is NOT usable: on some boxes
    `sg` is setgroups(1), and ast-grep's own `sg` shim is a deprecated stub that
    can exit with a bare ENOENT. Always resolve the real `ast-grep`."""
    candidates = [
        explicit,
        os.environ.get("AST_GREP_BIN"),
        shutil.which("ast-grep"),
        str(Path.home() / ".local/ast-grep/node_modules/.bin/ast-grep"),
        "/tmp/asgtool/node_modules/.bin/ast-grep",
    ]
    for cand in candidates:
        if not cand:
            continue
        path = Path(cand).expanduser()
        if path.is_file() and os.access(path, os.X_OK):
            return str(path)
    sys.exit(
        "error: ast-grep not found. Install it with:\n"
        "  npm install --prefix ~/.local/ast-grep @ast-grep/cli\n"
        "then either add ~/.local/ast-grep/node_modules/.bin to PATH or pass\n"
        "  --ast-grep /path/to/ast-grep"
    )


LANG_NAMES = {"python": "Python", "javascript": "JavaScript", "typescript": "TypeScript"}


def _parse_stream(text: str) -> list[dict]:
    """ast-grep --json=stream emits one JSON object per line, plus maybe a banner."""
    matches = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            matches.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return matches


def sg_run_pattern(binary: str, pattern: str, path: Path, lang: str) -> list[dict]:
    """`ast-grep run --pattern`: for whole expressions/statements.

    ast-grep exits 1 when a pattern simply does not match, so only a non-{0,1}
    exit is treated as a failure.
    """
    proc = subprocess.run(
        [binary, "run", "--pattern", pattern, "--lang", lang, "--json=stream", str(path)],
        capture_output=True,
        text=True,
    )
    if proc.returncode not in (0, 1):
        sys.exit(f"error: ast-grep run failed ({proc.returncode}): {proc.stderr.strip()[:400]}")
    return _parse_stream(proc.stdout)


def sg_scan_rule(binary: str, key: str, path: Path, lang: str) -> list[dict]:
    """`ast-grep scan --rule`: for node kinds a pattern cannot express.

    A dict entry (`"key": value`) is a `pair` node, not an expression, so
    `--pattern '"key": $V'` fails to parse with "Multiple AST nodes are
    detected". A YAML rule can name the kind and constrain the key field.
    """
    rule = (
        "id: py-dict-pair-key\n"
        f"language: {LANG_NAMES.get(lang.lower(), lang)}\n"
        "rule:\n"
        "  kind: pair\n"
        "  has:\n"
        "    field: key\n"
        f"    regex: ^\"{re.escape(key)}\"$\n"
    )
    fd, rule_path = tempfile.mkstemp(suffix=".yml", prefix="ast-rule-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(rule)
        proc = subprocess.run(
            [binary, "scan", "--rule", rule_path, "--json=stream", str(path)],
            capture_output=True,
            text=True,
        )
    finally:
        if os.path.exists(rule_path):
            os.unlink(rule_path)
    if proc.returncode not in (0, 1):
        sys.exit(f"error: ast-grep scan failed ({proc.returncode}): {proc.stderr.strip()[:400]}")
    return _parse_stream(proc.stdout)


def span(match: dict) -> tuple[int, int]:
    off = match["range"]["byteOffset"]
    return off["start"], off["end"]


def line_of(match: dict) -> int:
    return match["range"]["start"]["line"] + 1  # ast-grep is 0-based


# --------------------------------------------------------------------------
# diff / write helpers (mirrors tools/safe_patch.py conventions)
# --------------------------------------------------------------------------
def unified(old: str, new: str, path: Path) -> str:
    return "".join(
        difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=f"a/{path.name}",
            tofile=f"b/{path.name}",
            n=2,
        )
    )


def check_syntax(text: str, path: Path) -> None:
    if path.suffix == ".py":
        ast.parse(text, filename=str(path))


def atomic_write(path: Path, text: str) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%S")
    backup = BACKUP_DIR / f"{path.name}.{stamp}"
    n = 1
    while backup.exists():  # two writes in the same second must not collide
        n += 1
        backup = BACKUP_DIR / f"{path.name}.{stamp}.{n}"
    shutil.copy2(path, backup)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return backup


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Rewrite one key inside one named dict, selected by AST position.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("path", type=Path, help="file to inspect/edit")
    ap.add_argument("--key", required=True, help="dict key to look for, e.g. reviewer")
    ap.add_argument("--dict", dest="dict_name", help="target dict variable, e.g. FREE_MODELS")
    ap.add_argument("--value", help="replacement value (string literal body, no quotes)")
    ap.add_argument("--expect", type=int, default=1, help="how many matches inside the target dict (default 1)")
    ap.add_argument("--apply", action="store_true", help="write the change (default: dry run)")
    ap.add_argument("--lang", default="python", help="ast-grep language (default python)")
    ap.add_argument("--ast-grep", dest="ast_grep", help="path to the ast-grep binary")
    args = ap.parse_args(argv)

    if not args.path.is_file():
        print(f"error: {args.path} is not a file", file=sys.stderr)
        return 1

    binary = find_ast_grep(args.ast_grep)
    source = args.path.read_text(encoding="utf-8")

    # 1. every dict-valued assignment, by name -> byte span.
    #    The pattern needs at least one `key: value` pair so a set literal
    #    ({"a", "b"}) cannot masquerade as a dict; the two forms cover
    #    single-pair and multi-pair dicts.
    containers: dict[str, tuple[int, int]] = {}
    for pattern in ("$NAME = {$K: $V, $$$REST}", "$NAME = {$K: $V}"):
        for m in sg_run_pattern(binary, pattern, args.path, args.lang):
            mv = (m.get("metaVariables") or {}).get("single") or {}
            name = (mv.get("NAME") or {}).get("text")
            if name and name not in containers:
                containers[name] = span(m)

    # 2. every `"<key>": <value>` pair in the file, via a kind:pair rule
    pairs = sg_scan_rule(binary, args.key, args.path, args.lang)

    def owner(pair_span: tuple[int, int]) -> str:
        """Innermost containing dict, so nested dicts report their own key."""
        start, end = pair_span
        best: tuple[str, int, int] | None = None
        for name, (cstart, cend) in containers.items():
            if cstart <= start and end <= cend:
                if best is None or (cend - cstart) < (best[2] - best[1]):
                    best = (name, cstart, cend)
        return best[0] if best else "<unknown>"

    report = []
    for p in pairs:
        report.append((line_of(p), owner(span(p)), p))

    if not report:
        print(f"error: no `\"{args.key}\": ...` pair found in {args.path}", file=sys.stderr)
        return 1

    print(f"{args.path}: {len(report)} AST match(es) for \"{args.key}\"")
    for line, owner_name, p in report:
        mark = "->" if owner_name == args.dict_name else "  "
        print(f"  {mark} line {line:>5}  in {owner_name:<14} {p['text'][:70]!r}")

    if not args.dict_name or args.value is None:
        print("\nreport only: pass --dict and --value to change one entry")
        return 0

    targets = [p for line, owner_name, p in report if owner_name == args.dict_name]
    if len(targets) != args.expect:
        print(
            f"\nrefused: expected {args.expect} match(es) inside {args.dict_name}, "
            f"found {len(targets)}. Nothing written.",
            file=sys.stderr,
        )
        return 1

    # 3. splice as BYTES. ast-grep reports UTF-8 byte offsets, and this file is
    #    full of multi-byte box-drawing characters, so slicing a `str` by those
    #    offsets corrupts the result (the syntax gate catches it, but silently
    #    mis-placing the edit is exactly what this tool exists to prevent).
    raw = args.path.read_bytes()
    replacement = f'"{args.key}": "{args.value}"'.encode("utf-8")
    for p in sorted(targets, key=lambda m: span(m)[0], reverse=True):
        start, end = span(p)
        raw = raw[:start] + replacement + raw[end:]
    new_source = raw.decode("utf-8")

    if new_source == source:
        print("\nno change: the target entry already has that value")
        return 0

    diff = unified(source, new_source, args.path)
    print()
    print(diff, end="")

    try:
        check_syntax(new_source, args.path)
    except SyntaxError as exc:
        print(f"\nrefused: patched file would not parse ({exc}). Nothing written.", file=sys.stderr)
        return 1

    if not args.apply:
        print("\nast_reviewer_codemod: dry run — re-run with --apply to write")
        return 2

    backup = atomic_write(args.path, new_source)
    print(f"\nwritten. backup: {backup}")

    # 4. prove the other maps did not move
    after = args.path.read_text(encoding="utf-8")
    for line, owner_name, p in report:
        if owner_name == args.dict_name:
            continue
        before_text = p["text"]
        if before_text not in after:
            print(
                f"WARNING: line {line} in {owner_name} changed unexpectedly",
                file=sys.stderr,
            )
            return 1
    print("untouched: every non-target entry is still byte-identical")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
