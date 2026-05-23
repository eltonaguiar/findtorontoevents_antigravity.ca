# Tests for tools/scan_event_gaps.py and experimental supplement (no network).
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

from scan_event_gaps import (  # noqa: E402
    classify_confidence,
    fetch_baseline,
    filter_by_date,
    find_gaps,
    in_date_range,
    load_baseline_from_file,
    merge_scraped,
    parse_baseline_payload,
    slim_event,
    top_sources,
    write_markdown,
)
from scrapers.experimental_supplement import (  # noqa: E402
    parse_ical_events,
    parse_rss_items,
)
from scrapers.unified_scraper import UnifiedTorontoScraper  # noqa: E402


def test_parse_baseline_list():
    raw = [{"title": "A", "date": "2026-04-25T12:00:00Z"}]
    assert len(parse_baseline_payload(raw)) == 1


def test_parse_baseline_wrapped():
    raw = {"events": [{"title": "B", "date": "2026-04-26T12:00:00Z"}]}
    assert parse_baseline_payload(raw)[0]["title"] == "B"


def test_find_gaps_exact_duplicate():
    scraper = UnifiedTorontoScraper()
    baseline = [
        {
            "title": "Jazz Night at the Revue",
            "date": "2026-05-01T12:00:00Z",
            "source": "Test",
        }
    ]
    scraped = [
        {
            "title": "Jazz Night at the Revue",
            "date": "2026-05-01T12:00:00Z",
            "source": "Other",
            "url": "https://example.com/1",
        }
    ]
    gaps = find_gaps(baseline, scraped, scraper)
    assert gaps == []


def test_find_gaps_new_event():
    scraper = UnifiedTorontoScraper()
    baseline = [
        {
            "title": "Only In Baseline",
            "date": "2026-05-01T12:00:00Z",
        }
    ]
    scraped = [
        {
            "title": "Brand New Toronto Meetup",
            "date": "2026-06-15T12:00:00Z",
            "source": "TestSource",
            "url": "https://example.com/new",
            "location": "Toronto",
        }
    ]
    gaps = find_gaps(baseline, scraped, scraper)
    assert len(gaps) == 1
    assert gaps[0]["title"] == "Brand New Toronto Meetup"


def test_merge_scraped_dedup():
    scraper = UnifiedTorontoScraper()
    main = [{"title": "Same", "date": "2026-05-01T12:00:00Z", "source": "a"}]
    extra = [{"title": "Same", "date": "2026-05-01T12:00:00Z", "source": "b"}]
    merged = merge_scraped(main, extra, scraper)
    assert len(merged) == 1


def test_slim_event():
    s = slim_event(
        {
            "title": "T",
            "date": "2026-01-01T12:00:00Z",
            "source": "S",
            "url": "https://x",
            "location": "L",
            "extra": 1,
        }
    )
    assert set(s.keys()) == {"title", "date", "source", "url", "location"}
    assert "extra" not in s


def test_top_sources():
    gaps = [
        {"source": "A"},
        {"source": "A"},
        {"source": "B"},
    ]
    assert top_sources(gaps, limit=2) == [("A", 2), ("B", 1)]


def test_fetch_baseline_mock():
    payload = [{"title": "Live", "date": "2026-07-01T12:00:00Z"}]
    mock_resp = type(
        "R",
        (),
        {
            "status_code": 200,
            "text": json.dumps(payload),
            "json": lambda *a, **k: payload,
        },
    )()
    with patch("scan_event_gaps.requests.get", return_value=mock_resp):
        ev, url, st = fetch_baseline(["https://example.test/events.json"])
    assert len(ev) == 1
    assert url == "https://example.test/events.json"
    assert st == 200


def test_load_baseline_from_file(tmp_path):
    p = tmp_path / "b.json"
    p.write_text(
        json.dumps(
            {"events": [{"title": "X", "date": "2026-08-01T12:00:00Z"}]}
        ),
        encoding="utf-8",
    )
    ev = load_baseline_from_file(p)
    assert ev[0]["title"] == "X"


MINIMAL_RSS = """<?xml version="1.0"?>
<rss version="2.0"><channel>
<item>
<title>Free outdoor concert in Toronto this weekend</title>
<link>https://example.com/post/1</link>
<pubDate>Mon, 21 Apr 2026 14:00:00 +0000</pubDate>
</item>
<item>
<title>Boring news headline about taxes</title>
<link>https://example.com/post/2</link>
<pubDate>Mon, 21 Apr 2026 15:00:00 +0000</pubDate>
</item>
</channel></rss>
"""


def test_parse_rss_items_filters_later_in_experimental():
    items = parse_rss_items(MINIMAL_RSS)
    assert len(items) == 2
    assert "concert" in items[0]["title"].lower()


def test_in_date_range_inclusive_bounds():
    e = {"date": "2026-05-01T12:00:00Z"}
    assert in_date_range(e, "2026-05-01", "2026-12-31") is True
    assert in_date_range(e, "2026-05-02", "2026-12-31") is False
    assert in_date_range(e, "2026-04-01", "2026-04-30") is False
    assert in_date_range(e, None, None) is True
    assert in_date_range({"date": ""}, "2026-05-01", None) is False


def test_filter_by_date_passthrough_when_no_bounds():
    events = [{"date": "2025-01-01T00:00:00Z"}, {"date": "2027-01-01T00:00:00Z"}]
    assert filter_by_date(events, None, None) == events


def test_filter_by_date_drops_out_of_range():
    events = [
        {"title": "April", "date": "2026-04-30T00:00:00Z"},
        {"title": "May", "date": "2026-05-01T00:00:00Z"},
        {"title": "Dec", "date": "2026-12-31T00:00:00Z"},
        {"title": "Jan27", "date": "2027-01-01T00:00:00Z"},
    ]
    out = filter_by_date(events, "2026-05-01", "2026-12-31")
    assert [e["title"] for e in out] == ["May", "Dec"]


def test_classify_confidence_definitely_missing():
    scraper = UnifiedTorontoScraper()
    baseline = [{"title": "Completely Different Concert", "date": "2026-06-01T00:00:00Z"}]
    gaps = [{"title": "Toronto Robotics Expo", "date": "2026-07-15T00:00:00Z", "source": "X"}]
    definitely, likely = classify_confidence(gaps, baseline, scraper)
    assert len(definitely) == 1
    assert likely == []


def test_classify_confidence_likely_when_title_close_but_date_off():
    scraper = UnifiedTorontoScraper()
    baseline = [
        {"title": "Toronto Jazz Festival", "date": "2026-06-20T00:00:00Z"},
    ]
    gaps = [
        {"title": "Toronto Jazz Festival", "date": "2026-06-25T00:00:00Z", "source": "Y"},
    ]
    definitely, likely = classify_confidence(gaps, baseline, scraper)
    assert len(definitely) == 0
    assert len(likely) == 1
    assert likely[0]["_likely_match_baseline_title"] == "Toronto Jazz Festival"
    assert likely[0]["_likely_match_ratio"] >= 0.85


def test_write_markdown_smoke(tmp_path):
    out = tmp_path / "rep.md"
    write_markdown(
        out,
        baseline_url="https://example.com/events.json",
        baseline_count=10,
        scraped_count=12,
        definitely=[
            {"title": "New Event", "date": "2026-05-15T00:00:00Z", "source": "S", "location": "Toronto", "url": "https://x"}
        ],
        likely=[],
        sources_top=[("S", 1)],
        start_date="2026-05-01",
        end_date="2026-12-31",
    )
    content = out.read_text(encoding="utf-8")
    assert "# Event Gap Scan" in content
    assert "Definitely missing (1)" in content
    assert "New Event" in content
    assert "2026-05-01" in content


def test_parse_ical_events():
    ical = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:test1@example.com
DTSTART:20260425T180000Z
SUMMARY:ICS Test Event
URL:https://example.com/ics/1
END:VEVENT
END:VCALENDAR
"""
    evs = parse_ical_events(ical, "Test iCal")
    assert len(evs) == 1
    assert evs[0]["title"] == "ICS Test Event"
    assert "2026-04-25" in evs[0]["date"]
