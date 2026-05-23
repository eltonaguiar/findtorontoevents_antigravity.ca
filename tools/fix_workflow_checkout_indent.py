"""
Fix invalid YAML: `with:` must be a sibling of `uses:`, not a child.
Pattern broken by bulk edit:
    uses: actions/checkout@v4
      with:   # WRONG (extra indent)
"""
from __future__ import annotations

import re
from pathlib import Path


def normalize_checkout_with_children(lines: list[str]) -> bool:
    """
    Under `uses: actions/checkout@v4` + `with:`, every child key (token, fetch-depth, …)
    must share the same indent (with_indent + 2). Bulk edits sometimes leave token too
    deep and fetch-depth aligned with the old wrong `with:`.
    """
    changed = False
    i = 0
    while i < len(lines) - 1:
        line = lines[i]
        if "uses: actions/checkout@v4" not in line or line.strip().startswith("#"):
            i += 1
            continue
        nxt = lines[i + 1]
        m = re.match(r"^(\s*)with:\s*$", nxt)
        if not m:
            i += 1
            continue
        with_indent = len(m.group(1))
        want = with_indent + 2
        j = i + 2
        while j < len(lines):
            lj = lines[j]
            if not lj.strip():
                j += 1
                continue
            sp = len(lj) - len(lj.lstrip(" "))
            if sp <= with_indent:
                break
            stripped = lj.lstrip(" ")
            if stripped.startswith("#"):
                j += 1
                continue
            if re.match(r"^[\w-]+:\s", stripped):
                if sp != want:
                    lines[j] = " " * want + stripped
                    changed = True
            j += 1
        i += 1
    return changed


def fix_file(path: Path) -> bool:
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines(keepends=True)
    changed = False
    i = 0
    while i < len(lines) - 1:
        line = lines[i]
        if "uses: actions/checkout@v4" not in line or line.strip().startswith("#"):
            i += 1
            continue
        # Column where the `uses:` key starts (works for both `uses:` and `- uses:`).
        uses_col = line.find("uses:")
        if uses_col < 0:
            i += 1
            continue
        nxt = lines[i + 1]
        m = re.match(r"^(\s*)with:\s*", nxt)
        if not m:
            i += 1
            continue
        indent_with = len(m.group(1))
        # `with:` must align with `uses:`, not be nested under it. Do not use the line's
        # leading spaces for `- uses:` steps — that falsely flags valid compact checkout.
        if indent_with <= uses_col:
            i += 1
            continue
        delta = indent_with - uses_col
        lines[i + 1] = " " * uses_col + nxt.lstrip()
        changed = True
        j = i + 2
        while j < len(lines):
            lj = lines[j]
            if not lj.strip():
                j += 1
                continue
            sp = len(lj) - len(lj.lstrip(" "))
            if sp <= uses_col:
                break
            lines[j] = " " * (sp - delta) + lj.lstrip()
            j += 1
        i = i + 1
    if normalize_checkout_with_children(lines):
        changed = True
    if changed:
        path.write_text("".join(lines), encoding="utf-8")
    return changed


def main():
    root = Path(__file__).resolve().parent.parent / ".github" / "workflows"
    n = 0
    for p in sorted(root.glob("*.yml")):
        if fix_file(p):
            print("fixed", p.name)
            n += 1
    print("total files modified:", n)


if __name__ == "__main__":
    main()
