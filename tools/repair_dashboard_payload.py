#!/usr/bin/env python3
"""Repair corrupted dashboard_payload.json.

The known corruption pattern: 'agreeing_systems' arrays inside pick objects
get truncated mid-entry (e.g. {"system": "agg...) without a closing ] bracket.
This causes json.loads() to fail with 'Expecting ',' delimiter'.

Repair strategy (line-based, indentation-aware):
  1. Detect non-empty 'agreeing_systems': [...] blocks.
  2. If the array is properly closed with ']', validate it as JSON.
  3. If the array is unclosed (next sibling key found before ']'), or if the
     content is invalid JSON, replace the entire array with [].
  4. Re-validate the full file after all repairs.

The 'agreeing_systems' field is purely informational metadata (which systems
agree on a pick).  It is regenerated every hour by the dashboard generator,
so replacing corrupted entries with [] is safe.

Usage:
    python tools/repair_dashboard_payload.py [path]

Default path: audit_trail/data/dashboard_payload.json
"""

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "audit_trail" / "data" / "dashboard_payload.json"


def _is_valid_json(text: str) -> bool:
    try:
        json.loads(text)
        return True
    except (json.JSONDecodeError, ValueError):
        return False


def repair_agreeing_systems(content: str) -> tuple[str, int]:
    """Fix corrupted agreeing_systems arrays via line-based scan.

    Returns (repaired_content, number_of_fixes).
    """
    lines = content.split("\n")
    output: list[str] = []
    i = 0
    fixes = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        # Detect start of a non-empty agreeing_systems array
        if '"agreeing_systems"' in stripped and "[" in stripped and "[]" not in stripped:
            array_start_indent = indent
            collected: list[str] = [line]
            i += 1
            closed = False

            while i < len(lines):
                aline = lines[i]
                astripped = aline.lstrip()
                aindent = len(aline) - len(astripped)

                # Proper array close: line starts with ] at the expected depth
                if astripped.startswith("]") and aindent > array_start_indent:
                    collected.append(aline)
                    closed = True
                    i += 1
                    break

                # Corruption: a sibling key at the same indent as
                # 'agreeing_systems' appeared before the array closed.
                if (
                    aindent <= array_start_indent
                    and astripped.startswith('"')
                    and ":" in astripped
                ):
                    closed = False
                    break

                collected.append(aline)
                i += 1

            if closed:
                # Brackets matched — verify the array parses as valid JSON
                block = "\n".join(collected)
                arr_start = block.find("[")
                arr_end = block.rfind("]") + 1
                if arr_start >= 0 and arr_end > arr_start:
                    arr_text = block[arr_start:arr_end]
                    if _is_valid_json(arr_text):
                        output.extend(collected)
                        continue
                # Matched brackets but invalid content — replace
                prefix = collected[0][: collected[0].find("[")]
                output.append(prefix + "[],")
                fixes += 1
            else:
                # Array never closed — replace with empty
                prefix = collected[0][: collected[0].find("[")]
                output.append(prefix + "[],")
                fixes += 1
                # Do NOT increment i — current line is a sibling key
        else:
            output.append(line)
            i += 1

    return "\n".join(output), fixes


def repair(path: Path) -> bool:
    """Repair *path* in-place.  Returns True if changes were made."""
    if not path.is_file():
        print(f"ERROR: {path} not found")
        return False

    content = path.read_text(encoding="utf-8")

    # Quick check — already valid?
    if _is_valid_json(content):
        print(f"OK: {path.name} is already valid JSON ({len(content):,} chars)")
        return False

    print(f"Repairing {path.name} ({len(content):,} chars) ...")

    # Back up before modifying
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup = path.with_suffix(f".{ts}.bak")
    shutil.copy2(path, backup)
    print(f"  Backup saved to {backup.name}")

    repaired, fixes = repair_agreeing_systems(content)
    print(f"  Replaced {fixes} corrupted agreeing_systems arrays")

    # Validate the repaired content
    if _is_valid_json(repaired):
        path.write_text(repaired, encoding="utf-8", newline="\n")
        size_kb = len(repaired) / 1024
        print(f"  SUCCESS: {path.name} repaired and validated ({size_kb:.0f} KB)")
        return True

    # Still invalid — attempt a second pass (rare edge case: nested corruption)
    repaired2, fixes2 = repair_agreeing_systems(repaired)
    if _is_valid_json(repaired2):
        path.write_text(repaired2, encoding="utf-8", newline="\n")
        print(f"  SUCCESS (2-pass): {fixes + fixes2} total fixes")
        return True

    # Still broken — report the remaining error
    try:
        json.loads(repaired)
    except json.JSONDecodeError as e:
        print(
            f"  FAILED: JSON still invalid after repair — {e.msg} "
            f"at line {e.lineno}, col {e.colno}"
        )
    print(f"  Backup remains at {backup.name} for manual inspection")
    return False


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PATH
    ok = repair(target)
    sys.exit(0 if ok else 1)
