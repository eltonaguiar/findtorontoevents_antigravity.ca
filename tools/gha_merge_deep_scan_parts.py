#!/usr/bin/env python3
"""Merge docs/GHA_DEEP_SCAN_LATEST_PRIOR_part0.md + part1.md into GHA_DEEP_SCAN_LATEST_PRIOR.md."""
from __future__ import annotations

import argparse
import re
from pathlib import Path


def table_rows(text: str) -> list[str]:
    lines = text.splitlines()
    rows: list[str] = []
    after_sep = False
    for line in lines:
        if line.startswith("|----------"):
            after_sep = True
            continue
        if after_sep:
            if not line.startswith("|"):
                break
            if "Workflow | Latest" in line:
                continue
            rows.append(line)
    return rows


def details_section(text: str) -> str:
    m = re.search(r"## Detailed excerpts\s*\n(.*)\Z", text, re.DOTALL)
    if not m:
        return ""
    return m.group(1).strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--part0", type=Path, default=Path("docs/GHA_DEEP_SCAN_LATEST_PRIOR_part0.md"))
    ap.add_argument("--part1", type=Path, default=Path("docs/GHA_DEEP_SCAN_LATEST_PRIOR_part1.md"))
    ap.add_argument("--out", type=Path, default=Path("docs/GHA_DEEP_SCAN_LATEST_PRIOR.md"))
    args = ap.parse_args()

    t0 = args.part0.read_text(encoding="utf-8")
    t1 = args.part1.read_text(encoding="utf-8")
    rows = table_rows(t0) + table_rows(t1)

    def sort_key(row: str) -> str:
        cell = row.split("|", 2)
        return cell[1].strip().lower() if len(cell) > 1 else row

    rows.sort(key=sort_key)

    head = t0.split("## Summary table")[0].rstrip()
    head = re.sub(
        r"- \*\*Shard:\*\* \d+/\d+",
        "- **Shards:** merged from parallel runs (part 0 + part 1)",
        head,
    )
    if "Shards:** merged" not in head:
        head += "\n- **Shards:** merged from parallel runs (part 0 + part 1)"

    d0 = details_section(t0)
    d1 = details_section(t1)
    blocks = []
    for d in (d0, d1):
        if not d:
            continue
        parts = re.split(r"\n(?=### )", d)
        for p in parts:
            p = p.strip()
            if p:
                blocks.append(p)

    def block_key(b: str) -> str:
        first = b.split("\n", 1)[0]
        m = re.match(r"###\s+(.+?)\s+—", first)
        return (m.group(1) if m else first).lower()

    blocks.sort(key=block_key)

    out = (
        head
        + "\n\n## Summary table\n\n"
        + "| Workflow | Latest | Prior (if scanned) | Signal hits (latest) |\n"
        + "|----------|--------|--------------------|----------------------|\n"
        + "\n".join(rows)
        + "\n\n## Detailed excerpts\n\n"
        + "\n\n".join(blocks)
        + "\n"
    )
    args.out.write_text(out, encoding="utf-8")
    print(f"Wrote {args.out} ({len(rows)} table rows, {len(blocks)} detail blocks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
