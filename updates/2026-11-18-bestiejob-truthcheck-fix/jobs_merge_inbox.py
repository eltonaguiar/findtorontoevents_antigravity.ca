#!/usr/bin/env python3
"""
Merge inbox/ job submissions into README.md's three tables.

Agents submit work by dropping a file in inbox/ (or a PR that only adds one), named:

    inbox/<model-slug>--<YYYY-MM-DD>--v<N>.md

If the file is submitted again — a correction, a later scan from the same model on the
same day — increment N instead of creating a second file.

By default the merger leaves inbox/ alone: a hand run must never rewrite another
agent's submission. Pass --bump-inbox to get the old behaviour (rename each merged
file to the next version and stamp it with what it contributed); the CI workflows do
that so the commit records which version was merged.

Usage:
  python3 tools/jobs_merge_inbox.py --dry-run
  python3 tools/jobs_merge_inbox.py
  python3 tools/jobs_merge_inbox.py --today 2026-11-02 --days 30

Merging (additive by default):
  * inserts new rows into the matching table and touches nothing else
  * --rebuild restores the old behaviour: rewrite the tables, cap at --max-per-table,
    archive rows outside --days (that path rewrote the board to 600 rows twice on
    2026-11-11, so it is opt-in now)
  * reads every inbox/*.md except files starting with "_" or "TEMPLATE"
  * keeps rows with an absolute YYYY-MM-DD posted date and a URL
  * refuses to write when the tables hold more dated rows than it can parse back
    out (a row glued onto another line, or with a broken [title](url), would
    otherwise be dropped silently by the insert or the --rebuild re-render)
  * dedupes on normalised URL against the README and the other inbox files
  * rewrites README with the same three-table layout the consolidator produces
  * moves rows older than --days into README.BAK_<UTC timestamp>.md
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from jobs_consolidate import (  # noqa: E402
    README,
    classify,
    dedupe,
    extract_rows,
    extract_scan_block,
    is_listing_url,
    normalise_url,
    render,
)

# Single source of truth for signup-gated / paywall aggregator traps. Same
# import build_site.py uses; the merger previously did not consult it at all.
from job_source_truth import domain_is_gated  # noqa: E402

INBOX = ROOT / "inbox"
# The board is a technical ServiceNow/Salesforce listing, and every scanner that
# feeds it rejects sales/marketing roles. The merger used to accept them, so a
# harvest could smuggle "Regional Sales Manager" onto a technical table.
#
# Match the marketing *job function*, not the word: bare "marketing"/"growth" threw
# out platform work ("Marketing Cloud Specialist") and analytics work ("Data
# Scientist, Growth", "Lead Data Analyst, Growth Marketing"), which are exactly the
# roles this board exists for.
EXCL = re.compile(r"\b(account executive|account manager|sales representative|"
                  r"sales manager|business development|recruiter|talent acquisition|"
                  r"pre-?sales|customer success|product marketing|"
                  r"demand gen(?:eration)?|content marketing|email marketing|"
                  r"social media|brand manager|growth hacker|growth marketing manager|"
                  r"marketing (?:manager|specialist|coordinator|director|associate|"
                  r"intern|consultant|executive|ops|operations))\b", re.I)
NAME_RE = re.compile(r"^(?P<model>[a-z0-9._-]+)--(?P<date>\d{4}-\d{2}-\d{2})--v(?P<ver>\d+)\.md$", re.I)
LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
BARE_URL_RE = re.compile(r"https?://[^\s|)]+")


def _clean_title(title: str) -> str:
    """Strip bracket artifacts from a submission title so it survives as [title](url).

    Older submissions carried titles like ``[[[Hiring] X @Y](url)`` or
    ``[[IT Project Manager [4987]](url)``: nested brackets make the inserted
    README line unparseable by ``extract_rows``, which would silently drop the
    row on the next render.  Collapse leading brackets and turn inner ``]`` into
    ``:``; the URL, company and location are untouched, so nothing is lost.
    """
    t = re.sub(r"^\[+", "", str(title or ""))
    t = t.replace("]", ":").strip().rstrip(":").strip()
    return title if not t else t


def parse_inbox_file(path: Path) -> list[dict]:
    """Rows: | Posted | Role | Company | Location | URL | (extra columns tolerated)."""
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue
        posted = cells[0].strip()
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", posted):
            continue
        link = LINK_RE.search(line)
        if link:
            title, url = link.group(1), link.group(2)
        else:
            bare = BARE_URL_RE.search(line)
            if not bare:
                continue
            url = bare.group(0)
            title = cells[1]
        company = cells[2] if len(cells) > 2 else ""
        location = cells[3] if len(cells) > 3 else ""
        note = (cells[4] if len(cells) > 4 and "http" not in cells[4] else "").strip()
        rows.append(
            {
                "posted": posted,
                "title": title.replace("|", "/").strip(),
                "url": url,
                "company": company.replace("|", "/").strip(),
                "location": location.replace("|", "/").strip(),
                "note": note or f"via {path.name}",
                "family": classify(title, url),
                "origin": path.name,
            }
        )
    return rows


SECTION = {"servicenow": "### ServiceNow jobs (",
           "salesforce": "### Salesforce jobs (",
           "other": "### Other jobs ("}


def _bump_counts(lines: list[str], heading_idx: int) -> None:
    m = re.match(r"(### .* jobs \()(\d+)(\).*)", lines[heading_idx])
    if m:
        lines[heading_idx] = f"{m.group(1)}{int(m.group(2)) + 1}{m.group(3)}"
    for j in range(heading_idx, min(heading_idx + 8, len(lines))):
        s = re.match(r"(<details><summary><strong>Show )(\d+)( postings</strong></summary>)", lines[j])
        if s:
            lines[j] = f"{s.group(1)}{int(s.group(2)) + 1}{s.group(3)}"
            break


TABLE_HEADINGS = ("### ServiceNow jobs (", "### Salesforce jobs (", "### Other jobs (")
DATED_CELL_RE = re.compile(r"\|\s*20\d\d-\d\d-\d\d\s*\|")


def board_tables(text: str) -> str:
    """Just the three job tables — the how-to examples and daily-scan echo excluded."""
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith(TABLE_HEADINGS)]
    if not starts:
        return ""
    end = next(
        (i for i in range(starts[-1] + 1, len(lines)) if lines[i].startswith("## ")),
        len(lines),
    )
    return "\n".join(lines[starts[0] : end])


def count_dated_rows(text: str) -> int:
    """Dated row cells in the tables, counting rows glued onto another row's line.

    extract_rows() reads one row per line. Two rows written on one line — the
    2026-11-11 corruption was `| ... | row || row |` — parse as one, so the second
    vanishes the next time the tables are re-rendered. Counting cells rather than
    lines is what makes that visible before the write instead of after.
    """
    region = board_tables(text)
    return sum(
        len(DATED_CELL_RE.findall(line))
        for line in region.splitlines()
        if line.lstrip().startswith("|")
    )


def unreadable_row_lines(text: str) -> list[str]:
    """Table lines holding dated rows the merger cannot parse back out."""
    problems: list[str] = []
    for line in board_tables(text).splitlines():
        if not line.lstrip().startswith("|"):
            continue
        dates = DATED_CELL_RE.findall(line)
        if not dates:
            continue
        if len(dates) > 1:
            problems.append(f"{len(dates)} rows glued onto one line: {line.strip()[:120]}")
        elif not LINK_RE.search(line):
            problems.append(f"dated row without a parsable [title](url): {line.strip()[:120]}")
    return problems


def rows_are_readable(text: str, stage: str, allow: bool) -> bool:
    """Refuse to write when the tables hold more dated rows than parse back out.

    The additive path inserts into the text it read and --rebuild re-renders the
    parsed rows from scratch, so either one turns an unreadable row into a deleted
    row. Both paths run this on the document they are about to write, which is the
    last point where the loss can still be refused.
    """
    parsed, _ = extract_rows(board_tables(text))
    raw = count_dated_rows(text)
    if len(parsed) == raw:
        return True
    print(f"\nREFUSING to write: {stage} would lose rows.", file=sys.stderr)
    print(f"  dated rows in the tables  : {raw}", file=sys.stderr)
    print(
        f"  rows the merger can parse : {len(parsed)} ({raw - len(parsed)} unreadable)",
        file=sys.stderr,
    )
    problems = unreadable_row_lines(text)
    for problem in problems[:10]:
        print(f"    - {problem}", file=sys.stderr)
    if len(problems) > 10:
        print(f"    ... and {len(problems) - 10} more", file=sys.stderr)
    print(
        "  One row per line, each with a plain [title](url): a row glued onto another "
        "line, or carrying a broken link, parses as no row at all — so writing this "
        "document would drop it silently.",
        file=sys.stderr,
    )
    if allow:
        print("  --allow-row-loss given: writing anyway.", file=sys.stderr)
        return True
    print(
        "  Fix the rows above, or re-run with --allow-row-loss once you have read them.",
        file=sys.stderr,
    )
    return False


def insert_rows(readme_text: str, rows: list[dict]) -> tuple[str, int]:
    """Insert rows into the matching table, preserving every existing line."""
    lines = readme_text.splitlines(True)
    added = 0
    for row in sorted(rows, key=lambda r: r["posted"], reverse=True):
        marker = SECTION.get(row.get("family", "other"), SECTION["other"])
        start = next((i for i, l in enumerate(lines) if l.startswith(marker)), None)
        if start is None:
            continue
        # Bound the search to this section. The three job tables carry no
        # "| Posted | Role |" header row (that header only exists in the
        # submission guide at the bottom of the file), so the old file-wide
        # header search fell through to the guide and inserted live postings
        # into the documentation instead of the board.
        section_end = len(lines)
        for i in range(start + 1, len(lines)):
            if lines[i].startswith("### ") or lines[i].startswith("## "):
                section_end = i
                break
        row_lines = [
            i for i in range(start + 1, section_end)
            if DATED_CELL_RE.search(lines[i])
        ]
        if not row_lines:
            continue
        first_row, last_row = row_lines[0], row_lines[-1]
        pos = last_row + 1
        for i in range(first_row, last_row + 1):
            m = re.search(r"(20\d\d-\d\d-\d\d)", lines[i])
            if m and m.group(1) < row["posted"]:
                pos = i
                break
        lines.insert(
            pos,
            f"| {row['posted']} | [{_clean_title(row['title'])}]({row['url']}) | {row['company']} | "
            f"{row['location']} | {row['note']} |\n",
        )
        _bump_counts(lines, start)
        added += 1
    return "".join(lines), added


def next_version(path: Path, ver: int) -> Path:
    m = NAME_RE.match(path.name)
    assert m
    return path.with_name(f"{m.group('model')}--{m.group('date')}--v{ver + 1}.md")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--today", default=None)
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--max-per-table", type=int, default=150)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--rebuild",
        action="store_true",
        help="legacy destructive path: rewrites the tables, caps each at --max-per-table "
        "and archives rows outside --days. Default is additive (insert only).",
    )
    ap.add_argument(
        "--bump-inbox",
        action="store_true",
        help="rename merged inbox files to the next v<N> and stamp them (CI only; "
        "without it a run never touches another agent's submission)",
    )
    ap.add_argument(
        "--allow-row-loss",
        action="store_true",
        help="write even when the tables hold more dated rows than the merger can "
        "parse back out (only after reading the list it prints)",
    )
    args = ap.parse_args()

    today = date.fromisoformat(args.today) if args.today else datetime.now(timezone.utc).date()
    cutoff = today - timedelta(days=args.days)

    if not INBOX.exists():
        print("no inbox/ directory — nothing to merge")
        return 0

    submissions = [
        p
        for p in sorted(INBOX.glob("*.md"))
        if not p.name.startswith(("_", "TEMPLATE", "README"))
    ]
    if not submissions:
        print("inbox/ is empty — nothing to merge")
        return 0

    old_readme = README.read_text(encoding="utf-8")
    if not rows_are_readable(old_readme, "reading README.md", args.allow_row_loss):
        return 1
    readme_rows, _ = extract_rows(old_readme)
    known = {normalise_url(r["url"]) for r in readme_rows}
    # Applied roles (APPLIED.md) must never be re-added to the live tables.
    applied = Path(__file__).resolve().parent.parent / "APPLIED.md"
    if applied.exists():
        import re as _re
        for u in _re.findall(r"https?://[^\s)|]+", applied.read_text()):
            known.add(normalise_url(u))
    incoming: list[dict] = []
    per_file: dict[str, dict[str, int]] = {}

    for path in submissions:
        if not NAME_RE.match(path.name):
            print(f"skip {path.name}: name must be <model>--<YYYY-MM-DD>--v<N>.md")
            continue
        added = dup = bad = listing = gated = 0
        for row in parse_inbox_file(path):
            key = normalise_url(row["url"])
            if key in known:
                dup += 1
                continue
            if is_listing_url(row["url"]):
                listing += 1
                continue
            # Signup-gated / paywall aggregator traps (jobleads.com,
            # theladders.com, …). tools/job_source_truth.py is the single
            # source of truth for that blocklist; until 2026-11-18 only
            # build_site.py consulted it, and that merely *labelled* the row
            # and swapped in a cross-ref — so a harvest could re-merge a
            # paywall link and turn `truth-check.yml` red on the next run
            # (13 rows in README, 15 consecutive hourly failures). Drop at
            # ingest instead: a gated URL is not a posting.
            if domain_is_gated(row["url"]):
                gated += 1
                continue
            if EXCL.search(row.get("title") or ""):
                bad += 1
                continue
            known.add(key)
            incoming.append(row)
            added += 1
        per_file[path.name] = {"added": added, "duplicate": dup, "bad": bad,
                               "listing": listing, "gated": gated}
        extra = f", {listing} listing page(s)" if listing else ""
        if gated:
            extra += f", {gated} signup-gated link(s)"
        print(f"{path.name}: +{added} new, {dup} duplicate{extra}")

    if not args.rebuild:
        fresh = [r for r in incoming if cutoff.isoformat() <= r["posted"] <= today.isoformat()]
        stale = len(incoming) - len(fresh)
        print(f"\nincoming rows    : {len(incoming)} ({stale} older than {cutoff.isoformat()}, not added)")
        print(f"existing rows    : {len(readme_rows)} (preserved verbatim)")
        if args.dry_run:
            for row in fresh[:15]:
                print(f"  will add [{row['family']}] {row['posted']} {row['title'][:60]} — {row['company'][:28]}")
            print(f"additive dry run : +{len(fresh)} rows, 0 removed")
            return 0
        doc, added = insert_rows(old_readme, fresh)
        if not rows_are_readable(doc, "inserting rows", args.allow_row_loss):
            return 1
        if added:
            README.write_text(doc, encoding="utf-8")
        after_rows, _ = extract_rows(README.read_text(encoding="utf-8"))
        print(f"additive         : +{added} rows -> README now {len(after_rows)} (was {len(readme_rows)})")
        if len(after_rows) < len(readme_rows):
            print("REFUSING to write: row count shrank", file=sys.stderr)
            return 1
        if args.bump_inbox:
            stamp0 = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
            for path in submissions:
                m = NAME_RE.match(path.name)
                if not m:
                    continue
                stats = per_file.get(path.name, {"added": 0, "duplicate": 0})
                target = next_version(path, int(m.group("ver")))
                body = path.read_text(encoding="utf-8")
                if not body.startswith("<!-- merged"):
                    body = (f"<!-- merged {stamp0}: +{stats['added']} new, "
                            f"{stats['duplicate']} duplicate, version {int(m.group('ver')) + 1} -->\n") + body
                target.write_text(body, encoding="utf-8")
                path.unlink()
        else:
            print("inbox/left as submitted (pass --bump-inbox to version-stamp merged files)")
        return 0

    merged = readme_rows + incoming
    unique, dropped = dedupe(merged)
    current = [r for r in unique if cutoff.isoformat() <= r["posted"] <= today.isoformat()]
    expired = [r for r in unique if r["posted"] < cutoff.isoformat()]

    kept: list[dict] = []
    for key in ("servicenow", "salesforce", "other"):
        group = sorted((r for r in current if r["family"] == key), key=lambda r: r["posted"], reverse=True)
        kept.extend(group[: args.max_per_table])
        expired.extend(group[args.max_per_table :])
    current = sorted(kept, key=lambda r: r["posted"], reverse=True)
    counts = {k: sum(1 for r in current if r["family"] == k) for k in ("servicenow", "salesforce", "other")}

    off_board = sum(v["bad"] for v in per_file.values())
    listing_pages = sum(v["listing"] for v in per_file.values())
    gated_rows = sum(v.get("gated", 0) for v in per_file.values())
    if gated_rows:
        print(f"\nskipped          : {gated_rows} rows on signup-gated/paywall "
              f"domains (see tools/job_source_truth.py)")
    if listing_pages:
        print(f"\nskipped          : {listing_pages} rows that are aggregator listing pages, not postings")
    if off_board:
        print(f"skipped          : {off_board} rows outside the board's remit (sales/marketing)")
    print(f"\nincoming rows    : {len(incoming)}")
    print(f"total unique     : {len(unique)} (dupes merged: {dropped})")
    print(f"in {args.days}-day window: {len(current)}  {counts}")
    print(f"archiving        : {len(expired)} rows older than {cutoff.isoformat()}")

    if args.dry_run:
        for row in incoming[:15]:
            print(f"  will add [{row['family']}] {row['posted']} {row['title'][:60]} — {row['company'][:28]}")
        return 0

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    archive_name = f"README.BAK_{stamp}.md"
    archive = [f"# Archived on {today.isoformat()}", "", f"Rows older than {cutoff.isoformat()}:"]
    archive.append("")
    archive.append("| Posted | Role | Company | Location | URL |")
    archive.append("|---|---|---|---|---|")
    for row in sorted(expired, key=lambda r: r["posted"], reverse=True):
        archive.append(
            f"| {row['posted']} | {row['title']} | {row['company']} | {row['location']} | {row['url']} |"
        )
    (ROOT / archive_name).write_text("\n".join(archive) + "\n", encoding="utf-8")

    doc = render(current, today, args.days, cutoff, archive_name)
    scan_block = extract_scan_block(old_readme)
    if scan_block:
        doc += (
            "## Automated feed (rewritten daily)\n\n"
            "Raw output of `npm run scan:daily`; it may repeat rows from the tables above.\n\n"
            + scan_block
            + "\n"
        )
    doc += (
        f"\n## Archive\n\n`{archive_name}` holds the rows that aged out of the "
        f"{args.days}-day window on {today.isoformat()}.\n"
    )
    if not rows_are_readable(doc, "rebuilding the tables", args.allow_row_loss):
        return 1
    README.write_text(doc, encoding="utf-8")
    print(f"wrote README.md with {len(current)} rows; archived {len(expired)} to {archive_name}")

    if not args.bump_inbox:
        print("inbox/left as submitted (pass --bump-inbox to version-stamp merged files)")
        return 0

    for path in submissions:
        m = NAME_RE.match(path.name)
        if not m:
            continue
        stats = per_file.get(path.name, {"added": 0, "duplicate": 0})
        target = next_version(path, int(m.group("ver")))
        header = (
            f"<!-- merged {stamp}: +{stats['added']} new, "
            f"{stats['duplicate']} duplicate, version {int(m.group('ver')) + 1} -->\n"
        )
        body = path.read_text(encoding="utf-8")
        if not body.startswith("<!-- merged"):
            body = header + body
        target.write_text(body, encoding="utf-8")
        path.unlink()
        print(f"bumped {path.name} -> {target.name}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
