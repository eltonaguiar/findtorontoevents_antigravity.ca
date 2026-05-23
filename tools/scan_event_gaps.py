#!/usr/bin/env python3
"""
Scan for Toronto events found by scrapers that are not in the live findtorontoevents.ca catalog.

Compares UnifiedTorontoScraper output (optionally plus experimental supplements) against a
baseline snapshot: the public events.json (or { "events": [...] }) from production.

Dedup rules match the merge path: UnifiedTorontoScraper.is_duplicate().

Usage:
  python tools/scan_event_gaps.py
  python tools/scan_event_gaps.py --baseline-file events.json
  python tools/scan_event_gaps.py --skip-scrape --scraped-json path/to/scraped.json
  python tools/scan_event_gaps.py --include-experimental
"""
from __future__ import annotations

import argparse
import csv
import difflib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from scrapers.unified_scraper import UnifiedTorontoScraper  # noqa: E402

DEFAULT_BASELINE_URLS: Tuple[str, ...] = (
    "https://findtorontoevents.ca/events.json",
    "https://findtorontoevents.ca/next/events.json",
)

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; FindTorontoEvents-GapScan/1.0)",
    "Accept": "application/json, */*;q=0.8",
}


def parse_baseline_payload(raw: Any) -> List[dict]:
    """Accept top-level list or { \"events\": [...] }."""
    if raw is None:
        return []
    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]
    if isinstance(raw, dict) and "events" in raw:
        evs = raw["events"]
        if isinstance(evs, list):
            return [x for x in evs if isinstance(x, dict)]
    return []


def fetch_baseline(
    urls: List[str], timeout: int = 120
) -> Tuple[List[dict], Optional[str], Optional[int]]:
    """Try each URL; return (events, url_used, status_code)."""
    last_status: Optional[int] = None
    for url in urls:
        if not url:
            continue
        try:
            r = requests.get(url, headers=REQUEST_HEADERS, timeout=timeout)
            last_status = r.status_code
            if r.status_code != 200 or not (r.text or "").strip():
                continue
            data = r.json()
            events = parse_baseline_payload(data)
            if events:
                return events, url, r.status_code
        except (requests.RequestException, json.JSONDecodeError, ValueError):
            continue
    return [], None, last_status


def load_baseline_from_file(path: Path) -> List[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return parse_baseline_payload(json.load(f))


def find_gaps(
    baseline: List[dict], scraped: List[dict], scraper: UnifiedTorontoScraper
) -> List[dict]:
    """Events in scraped that are not duplicates of any baseline event."""
    gaps: List[dict] = []
    for ev in scraped:
        if not isinstance(ev, dict):
            continue
        if not scraper.is_duplicate(ev, baseline):
            gaps.append(ev)
    return gaps


def in_date_range(event: dict, start: Optional[str], end: Optional[str]) -> bool:
    """Return True if event['date'][:10] falls within [start, end] (inclusive). Either bound may be None."""
    raw = (event.get("date") or "")[:10]
    if not raw:
        return False
    if start and raw < start:
        return False
    if end and raw > end:
        return False
    return True


def filter_by_date(events: List[dict], start: Optional[str], end: Optional[str]) -> List[dict]:
    if not start and not end:
        return events
    return [e for e in events if in_date_range(e, start, end)]


def classify_confidence(gaps: List[dict], baseline: List[dict], scraper: UnifiedTorontoScraper) -> Tuple[List[dict], List[dict]]:
    """Split gaps into (definitely_missing, likely_missing).

    A gap is 'likely_missing' (needs human review) if its normalized title is
    >= 0.85 similar to any baseline title, even though is_duplicate() returned
    False (which means the date didn't match). Such cases are commonly the
    same event with a corrected/shifted date and warrant a manual look.
    """
    if not gaps:
        return [], []
    baseline_norm_titles = [scraper.normalize_title(b.get("title", "")) for b in baseline]
    definitely: List[dict] = []
    likely: List[dict] = []
    for ev in gaps:
        ev_norm = scraper.normalize_title(ev.get("title", ""))
        if not ev_norm:
            definitely.append(ev)
            continue
        best = 0.0
        best_idx = -1
        for i, bt in enumerate(baseline_norm_titles):
            if not bt:
                continue
            r = difflib.SequenceMatcher(None, ev_norm, bt).ratio()
            if r > best:
                best = r
                best_idx = i
        if best >= 0.85:
            ev = dict(ev)
            ev["_likely_match_baseline_title"] = baseline[best_idx].get("title")
            ev["_likely_match_baseline_date"] = baseline[best_idx].get("date")
            ev["_likely_match_ratio"] = round(best, 3)
            likely.append(ev)
        else:
            definitely.append(ev)
    return definitely, likely


def slim_event(e: dict) -> dict:
    return {
        "title": e.get("title"),
        "date": e.get("date"),
        "source": e.get("source"),
        "url": e.get("url"),
        "location": e.get("location"),
    }


def top_sources(gaps: List[dict], limit: int = 12) -> List[Tuple[str, int]]:
    c = Counter((g.get("source") or "(none)") for g in gaps)
    return c.most_common(limit)


def write_json_report(
    path: Path,
    baseline_url: Optional[str],
    baseline_count: int,
    scraped_count: int,
    gap_count: int,
    sources_top: List[Tuple[str, int]],
    gaps: List[dict],
    use_full_gaps: bool,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if use_full_gaps:
        out_gaps: Any = gaps
    else:
        out_gaps = [slim_event(g) for g in gaps]
    payload: Dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "baseline_url": baseline_url,
        "baseline_count": baseline_count,
        "scraped_count": scraped_count,
        "gap_count": gap_count,
        "gap_sources": [{"source": s, "count": n} for s, n in sources_top],
        "gaps": out_gaps,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")


def write_csv(path: Path, gaps: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["title", "date", "source", "url", "location"]
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for g in gaps:
            row = {k: g.get(k) for k in fieldnames}
            w.writerow(row)


def write_markdown(
    path: Path,
    baseline_url: Optional[str],
    baseline_count: int,
    scraped_count: int,
    definitely: List[dict],
    likely: List[dict],
    sources_top: List[Tuple[str, int]],
    start_date: Optional[str],
    end_date: Optional[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    lines: List[str] = []
    lines.append(f"# Event Gap Scan — {ts}")
    lines.append("")
    if start_date or end_date:
        lines.append(f"**Date range:** {start_date or '*'} → {end_date or '*'}")
    lines.append(f"**Baseline:** {baseline_url or '(local file)'} — {baseline_count} events")
    lines.append(f"**Scraped:** {scraped_count} events")
    lines.append(f"**Definitely missing:** {len(definitely)}  |  **Likely missing (review):** {len(likely)}")
    lines.append("")
    lines.append("## Top gap sources")
    if sources_top:
        lines.append("")
        lines.append("| Source | Count |")
        lines.append("|---|---:|")
        for s, n in sources_top:
            lines.append(f"| {s} | {n} |")
        lines.append("")

    def _table(title: str, rows: List[dict], extra_cols: List[str] = []) -> None:
        lines.append(f"## {title} ({len(rows)})")
        lines.append("")
        if not rows:
            lines.append("_None._")
            lines.append("")
            return
        cols = ["title", "date", "source", "location", "url"] + extra_cols
        header = "| " + " | ".join(cols) + " |"
        sep = "|" + "|".join(["---"] * len(cols)) + "|"
        lines.append(header)
        lines.append(sep)
        for r in rows:
            cells = []
            for c in cols:
                v = r.get(c) or ""
                v = str(v).replace("|", "\\|").replace("\n", " ")
                if len(v) > 200:
                    v = v[:200] + "…"
                cells.append(v)
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")

    _table("Definitely missing", definitely)
    _table(
        "Likely missing (needs human review)",
        likely,
        extra_cols=["_likely_match_baseline_title", "_likely_match_baseline_date", "_likely_match_ratio"],
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        f.write("\n")


def merge_scraped(
    main: List[dict], extra: List[dict], scraper: UnifiedTorontoScraper
) -> List[dict]:
    """Append extra events, skipping duplicates already in main (scraper internal dedup)."""
    out = list(main)
    for ev in extra:
        if not isinstance(ev, dict):
            continue
        if not scraper.is_duplicate(ev, out):
            out.append(ev)
    return out


def run_experimental(scraper: UnifiedTorontoScraper) -> List[dict]:
    from scrapers.experimental_supplement import fetch_experimental_events

    return fetch_experimental_events(scraper)


def main() -> int:
    p = argparse.ArgumentParser(description="List scraped Toronto events not in live catalog")
    p.add_argument(
        "--baseline-file",
        type=Path,
        help="Local JSON (array or {events: [...]}) instead of downloading baseline",
    )
    p.add_argument(
        "--baseline-url",
        action="append",
        dest="baseline_urls",
        help="Override baseline URL (repeatable). Defaults try events.json then next/events.json",
    )
    p.add_argument(
        "--skip-scrape",
        action="store_true",
        help="Do not run UnifiedTorontoScraper; use --scraped-json only",
    )
    p.add_argument(
        "--scraped-json",
        type=Path,
        help="Path to JSON array of events (used with --skip-scrape, or merged after scrape)",
    )
    p.add_argument(
        "--include-experimental",
        action="store_true",
        help="Merge RSS/optional iCal supplement (see experimental_supplement.py)",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "reports",
        help="Directory for timestamped event_gaps_*.json",
    )
    p.add_argument(
        "--csv", action="store_true", help="Also write event_gaps_*.csv"
    )
    p.add_argument(
        "--md", action="store_true", help="Also write event_gaps_*.md (Markdown report with confidence tiers)"
    )
    p.add_argument(
        "--start-date",
        type=str,
        default=None,
        help="Filter gaps to events with date >= YYYY-MM-DD (inclusive). Applied after dedup.",
    )
    p.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="Filter gaps to events with date <= YYYY-MM-DD (inclusive). Applied after dedup.",
    )
    p.add_argument(
        "--full-events-in-report",
        action="store_true",
        help="Include full event objects in JSON (default: title/date/source/url/location only)",
    )
    args = p.parse_args()

    baseline: List[dict] = []
    baseline_url_used: Optional[str] = None
    if args.baseline_file:
        baseline = load_baseline_from_file(args.baseline_file)
        if not baseline:
            print(
                f"ERROR: no events in baseline file: {args.baseline_file}",
                file=sys.stderr,
            )
            return 1
    else:
        urls = list(args.baseline_urls) if args.baseline_urls else list(DEFAULT_BASELINE_URLS)
        baseline, baseline_url_used, st = fetch_baseline(urls)
        if not baseline:
            print(
                "ERROR: could not load baseline from URLs (tried: %s) last_status=%s"
                % (", ".join(urls), st),
                file=sys.stderr,
            )
            return 1
        print(f"Baseline: {len(baseline)} events from {baseline_url_used}")

    scraper = UnifiedTorontoScraper()
    scraped: List[dict] = []

    if args.skip_scrape:
        if not args.scraped_json:
            print("ERROR: --skip-scrape requires --scraped-json", file=sys.stderr)
            return 1
        scraped = parse_baseline_payload(
            json.loads(args.scraped_json.read_text(encoding="utf-8"))
        )
        print(f"Scraped (from file): {len(scraped)} events")
    else:
        print("Running UnifiedTorontoScraper (full run; may take a long time)...")
        scraped = scraper.scrape_all()
        print(f"Unified scraper: {len(scraped)} events")
        if args.scraped_json:
            more = parse_baseline_payload(
                json.loads(args.scraped_json.read_text(encoding="utf-8"))
            )
            scraped = merge_scraped(scraped, more, scraper)
            print(f"After merge with {args.scraped_json}: {len(scraped)} events")

    if args.include_experimental:
        ex = run_experimental(scraper)
        print(f"Experimental supplement: {len(ex)} events")
        scraped = merge_scraped(scraped, ex, scraper)

    gaps = find_gaps(baseline, scraped, scraper)
    pre_filter_count = len(gaps)
    gaps = filter_by_date(gaps, args.start_date, args.end_date)
    if args.start_date or args.end_date:
        print(
            f"Date filter [{args.start_date or '*'} .. {args.end_date or '*'}]: "
            f"{pre_filter_count} -> {len(gaps)} gaps"
        )
    definitely, likely = classify_confidence(gaps, baseline, scraper)
    sources_ranked = top_sources(gaps)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_json = args.output_dir / f"event_gaps_{ts}.json"
    write_json_report(
        out_json,
        baseline_url_used,
        len(baseline),
        len(scraped),
        len(gaps),
        sources_ranked,
        gaps,
        use_full_gaps=bool(args.full_events_in_report),
    )
    print(
        f"Gaps: {len(gaps)} (definitely={len(definitely)}, likely={len(likely)}) "
        f"from scraped {len(scraped)} vs baseline {len(baseline)}"
    )
    print("Top gap sources:", sources_ranked[:8])
    print(f"Wrote {out_json}")
    if args.csv:
        out_csv = args.output_dir / f"event_gaps_{ts}.csv"
        write_csv(out_csv, gaps)
        print(f"Wrote {out_csv}")
    if args.md:
        out_md = args.output_dir / f"event_gaps_{ts}.md"
        write_markdown(
            out_md,
            baseline_url_used,
            len(baseline),
            len(scraped),
            definitely,
            likely,
            sources_ranked,
            args.start_date,
            args.end_date,
        )
        print(f"Wrote {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
