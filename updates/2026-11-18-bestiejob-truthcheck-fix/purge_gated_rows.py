#!/usr/bin/env python3
"""One-shot purge of signup-gated (paywall) links from the BESTIEJOB board.

Removes gated rows from README.md, FRESH_JOBS.md and jobs.json, and preserves
the ROLE (not the paywall link) in PAYWALL_ROLES.md with cross-ref search links
built by tools/job_source_truth.py::xref_search_links.

Run from the repo root:  python3 scripts/purge_gated_rows.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from job_source_truth import annotate  # noqa: E402

README = ROOT / "README.md"
FRESH = ROOT / "FRESH_JOBS.md"
JOBS_JSON = ROOT / "jobs.json"
LEDGER = ROOT / "PAYWALL_ROLES.md"

ROW_RE = re.compile(r"^\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*\[([^\]]+)\]\((\S+?)\)\s*\|")


def parse_row(line: str) -> dict | None:
    m = ROW_RE.match(line)
    if not m:
        return None
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    return {
        "posted": m.group(1),
        "title": m.group(2),
        "url": m.group(3),
        "company": cells[2] if len(cells) > 2 else "",
        "location": cells[3] if len(cells) > 3 else "",
        "note": cells[5] if len(cells) > 5 else "",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    # ---- README.md -------------------------------------------------------
    text = README.read_text(encoding="utf-8")
    kept: list[str] = []
    purged: list[dict] = []
    for line in text.splitlines(keepends=True):
        row = parse_row(line)
        if row:
            row["gated"] = annotate([row])["gated"]
            if row["gated"]:
                # annotate() mutates the dict it is given, adding 'xref'
                purged.append(row)
                continue
        kept.append(line)

    # ---- FRESH_JOBS.md ---------------------------------------------------
    fresh = FRESH.read_text(encoding="utf-8") if FRESH.exists() else ""
    gated_urls = {r["url"] for r in purged}
    fresh_lines = fresh.splitlines(keepends=True)
    fresh_kept = [ln for ln in fresh_lines if not any(u in ln for u in gated_urls)]

    # ---- jobs.json -------------------------------------------------------
    raw = JOBS_JSON.read_text(encoding="utf-8")
    payload = json.loads(raw)
    before = len(payload.get("jobs", []))
    # Preserve the file's own indentation so the diff is "removed 11 objects",
    # not a 108k-line whitespace reflow of the whole feed.
    _m = re.search(r"\n( +)\"", raw)
    indent = len(_m.group(1)) if _m else 2
    trailing_nl = "\n" if raw.endswith("\n") else ""
    jobs_kept = [
        j for j in payload.get("jobs", [])
        if not (j.get("url") in gated_urls)
    ]
    removed_json = before - len(jobs_kept)

    print(f"README : purged {len(purged)} gated rows "
          f"({len(text.splitlines())} -> {len(kept)} lines)")
    print(f"FRESH  : purged {len(fresh_lines) - len(fresh_kept)} lines")
    print(f"json   : purged {removed_json} entries ({before} -> {len(jobs_kept)})")

    if args.dry_run:
        for r in purged:
            print(f"  would purge [{r['posted']}] {r['title'][:60]} — {r['url'][:60]}")
        return 0

    README.write_text("".join(kept), encoding="utf-8")
    if FRESH.exists():
        FRESH.write_text("".join(fresh_kept), encoding="utf-8")
    payload["jobs"] = jobs_kept
    JOBS_JSON.write_text(
        json.dumps(payload, indent=indent, ensure_ascii=False) + trailing_nl,
        encoding="utf-8",
    )

    # ---- PAYWALL_ROLES.md : keep the ROLE, drop the paywall link ---------
    lines = [
        "# Paywall / signup-gated roles",
        "",
        "These postings were removed from `README.md` on 2026-11-18 because their",
        "only published link is a signup/paywall aggregator (jobleads.com,",
        "theladders.com). The *role* is real and is kept here so it is not lost; the",
        "link is not, because it never reaches the employer's posting.",
        "",
        "Each row carries cross-ref search links (title + company + location). Open",
        "one to reach the employer's own posting, then submit it through the normal",
        "`inbox/<model>--<date>--v<N>.md` flow.",
        "",
        "| Posted | Role | Company | Location | Find the real posting | Paywall link (do not use) |",
        "|---|---|---|---|---|---|",
    ]
    for r in sorted(purged, key=lambda x: x["posted"], reverse=True):
        search = " · ".join(f"[{name}]({url})" for name, url in r.get("xref", []))
        lines.append(
            f"| {r['posted']} | {r['title']} | {r['company']} | {r['location']} "
            f"| {search} | {r['url']} |"
        )
    LEDGER.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"ledger : wrote {LEDGER.name} with {len(purged)} roles + cross-refs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
