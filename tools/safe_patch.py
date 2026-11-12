#!/usr/bin/env python3
"""safe_patch.py — edits that either land exactly or not at all.

Built for files that resist ad-hoc editing: multi-site backend maps, repeated
boilerplate, a file someone has already broken three times. Every edit is
anchored by exact text, counted, syntax-checked against a temp copy, and written
atomically only if the result still parses. There is no state where the file on
disk is half-edited or syntactically dead.

CLI:
  tools/safe_patch.py FILE --find 'OLD' --replace 'NEW' [--expect 1] [--apply]
  tools/safe_patch.py FILE --pairs edits.json [--apply]
  tools/safe_patch.py FILE --diff fix.patch [--apply]
  tools/safe_patch.py FILE --show-lines 'ANCHOR'      # where does this text live?

  Default is DRY RUN: prints the unified diff and exits. --apply writes.
  --expect N refuses to edit unless the anchor occurs exactly N times
  (use it to catch "I thought there was one map, there were three").

Library:
  from tools.safe_patch import apply_pairs
  apply_pairs("path.py", [{"find": "...", "replace": "...", "expect": 3}], apply=True)

Exit codes: 0 applied/nothing to do, 1 refused or invalid, 2 dry-run would edit.
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import shutil
import subprocess
import sys
import time

BACKUP_DIR = os.environ.get("SAFE_PATCH_BACKUP", "/tmp/safe_patch_backups")

# syntax gate per extension — a patched file that does not parse is never written
SYNTAX = {
    ".py": ["python3", "-m", "py_compile"],
    ".sh": ["bash", "-n"],
    ".bash": ["bash", "-n"],
}

JSON_TYPES = {".json": (json.loads, None), ".yaml": (None, None)}  # yaml checked only if PyYAML present


def _read(path: str) -> str:
    with open(path, encoding="utf-8", newline="") as fh:
        return fh.read()


def _syntax_error(path: str, text: str) -> str | None:
    """Return an error string if `text` would not parse as `path`'s language."""
    ext = os.path.splitext(path)[1]
    if ext in SYNTAX:
        fd, tmp = _tmp_like(path, text)
        try:
            proc = subprocess.run(SYNTAX[ext] + [tmp], capture_output=True, text=True)
            return None if proc.returncode == 0 else (proc.stdout + proc.stderr).strip()
        finally:
            os.unlink(tmp)
    if ext == ".json":
        try:
            json.loads(text)
        except Exception as exc:  # noqa: BLE001 - report any parse failure
            return f"invalid JSON: {exc}"
    if ext in (".yaml", ".yml"):
        try:
            import yaml  # noqa: PLC0415 - optional dependency
        except ImportError:
            return None
        try:
            yaml.safe_load(text)
        except Exception as exc:  # noqa: BLE001
            return f"invalid YAML: {exc}"
    return None


def _tmp_like(path: str, text: str) -> tuple[int, str]:
    import tempfile

    fd, tmp = tempfile.mkstemp(suffix=os.path.splitext(path)[1])
    with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    return fd, tmp


def _first_line(text: str, needle: str) -> int:
    idx = text.find(needle)
    return 0 if idx < 0 else text.count("\n", 0, idx) + 1


def _diff(path: str, old: str, new: str) -> str:
    label = path.lstrip("/")
    return "".join(
        difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=f"a/{label}",
            tofile=f"b/{label}",
            n=3,
        )
    )


def _write_atomic(path: str, text: str) -> str:
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%S")
    base = os.path.join(BACKUP_DIR, f"{os.path.basename(path)}.{stamp}")
    backup, n = base, 1
    while os.path.exists(backup):  # two writes in the same second must not share a backup
        n += 1
        backup = f"{base}.{n}"
    shutil.copy2(path, backup)
    tmp = f"{path}.safepatch.tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    os.replace(tmp, path)  # atomic on POSIX and Windows
    return backup


def apply_pairs(path: str, pairs: list[dict], apply: bool = False, quiet: bool = False) -> dict:
    """Apply anchored find/replace pairs. Returns a report dict.

    Each pair: {"find": str, "replace": str, "expect": int|None}
    Raises nothing on refusal — callers check report["ok"].
    """
    old = _read(path)
    new = old
    for pair in pairs:
        find = pair["find"]
        repl = pair.get("replace", "")
        expect = pair.get("expect")
        hits = new.count(find)
        if hits == 0:
            return {"ok": False, "reason": f"anchor not found in {path}: {find[:90]!r}"}
        if expect is not None and hits != expect:
            return {
                "ok": False,
                "reason": (
                    f"anchor occurs {hits}x but --expect {expect}: {find[:90]!r}\n"
                    f"  first occurrence at line {_first_line(new, find)}"
                ),
            }
    # all anchors validated; apply in order
    for pair in pairs:
        new = new.replace(pair["find"], pair.get("replace", ""))

    err = _syntax_error(path, new)
    if err:
        return {"ok": False, "reason": f"patched file would not parse, refusing to write:\n{err}"}

    diff = _diff(path, old, new)
    if not apply:
        return {"ok": True, "applied": False, "diff": diff, "path": path}

    backup = _write_atomic(path, new)
    report = {"ok": True, "applied": True, "diff": diff, "backup": backup, "path": path}
    # post-write truth check: the file on disk must parse with the real name
    err = _syntax_error(path, _read(path))
    if err:  # pragma: no cover - _syntax_error already gated this
        shutil.copy2(backup, path)
        return {"ok": False, "reason": f"post-write check failed, restored from {backup}:\n{err}"}
    if not quiet:
        print(diff, end="")
    return report


def apply_diff(path: str, patch: str, apply: bool = False) -> dict:
    check = subprocess.run(["git", "apply", "--check", "--3way", patch], capture_output=True, text=True)
    if check.returncode != 0:
        return {"ok": False, "reason": f"git apply --check failed:\n{(check.stdout + check.stderr).strip()}"}
    if not apply:
        return {"ok": True, "applied": False, "diff": open(patch, encoding="utf-8").read(), "path": path}
    old = _read(path)
    run = subprocess.run(["git", "apply", "--3way", patch], capture_output=True, text=True)
    if run.returncode != 0:
        return {"ok": False, "reason": f"git apply failed:\n{(run.stdout + run.stderr).strip()}"}
    err = _syntax_error(path, _read(path))
    if err:
        _write_atomic(path, old)  # restore original content
        return {"ok": False, "reason": f"patched file would not parse, reverted:\n{err}"}
    return {"ok": True, "applied": True, "diff": _diff(path, old, _read(path)), "path": path}


def show_lines(path: str, anchor: str) -> int:
    text = _read(path)
    hits, start = [], 0
    while True:
        idx = text.find(anchor, start)
        if idx < 0:
            break
        hits.append(text.count("\n", 0, idx) + 1)
        start = idx + 1
    print(f"{path}: {len(hits)} occurrence(s) of {anchor[:60]!r} at line(s): "
          + (", ".join(map(str, hits)) or "(none)"))
    return 0 if hits else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="anchored, syntax-gated, atomic file edits")
    ap.add_argument("file")
    ap.add_argument("--find")
    ap.add_argument("--replace", default="")
    ap.add_argument("--expect", type=int)
    ap.add_argument("--pairs", help="JSON file: [{\"find\":..,\"replace\":..,\"expect\":..}]")
    ap.add_argument("--diff", help="path to a unified diff to apply via git apply --3way")
    ap.add_argument("--show-lines", metavar="ANCHOR")
    ap.add_argument("--apply", action="store_true", help="write the change (default: dry run)")
    args = ap.parse_args(argv)

    if not os.path.isfile(args.file):
        print(f"safe_patch: no such file: {args.file}", file=sys.stderr)
        return 1
    if args.show_lines:
        return show_lines(args.file, args.show_lines)

    if args.diff:
        report = apply_diff(args.file, args.diff, apply=args.apply)
    else:
        if args.pairs:
            pairs = json.load(open(args.pairs, encoding="utf-8"))
        elif args.find is not None:
            pairs = [{"find": args.find, "replace": args.replace, "expect": args.expect}]
        else:
            ap.error("give --find/--replace, --pairs, --diff or --show-lines")

        # validate every anchor before touching anything
        old = _read(args.file)
        for pair in pairs:
            hits = old.count(pair["find"])
            where = _first_line(old, pair["find"]) if hits else "-"
            print(f"anchor: {hits}x at line {where}: {pair['find'][:70]!r}")
            expect = pair.get("expect", args.expect)
            if hits == 0:
                print("safe_patch: anchor not found — nothing written", file=sys.stderr)
                return 1
            if expect is not None and hits != expect:
                print(f"safe_patch: found {hits}, expected {expect} — nothing written",
                      file=sys.stderr)
                return 1
        report = apply_pairs(args.file, pairs, apply=args.apply)

    if not report["ok"]:
        print(f"safe_patch: {report['reason']}", file=sys.stderr)
        return 1
    if report["applied"]:
        print(f"\nsafe_patch: wrote {report['path']} (backup: {report.get('backup', '-')})")
        return 0
    print("\nsafe_patch: dry run — re-run with --apply to write")
    return 2


if __name__ == "__main__":
    sys.exit(main())
