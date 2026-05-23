"""
Unit tests for the audit-driven scrapers added 2026-04-25:

  - tools/scrapers/tpl_bibliocommons_scraper.py
  - tools/scrapers/singles_extras_scraper.py

Tests focus on parsing/transformation logic (which is deterministic) rather
than live HTTP. Network calls are mocked so the suite runs offline.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

from scrapers.tpl_bibliocommons_scraper import TPLBiblioCommonsScraper  # noqa: E402
from scrapers.singles_extras_scraper import SingleInTheCityScraper  # noqa: E402


# ---------- TPL BiblioCommons scraper ----------

def _tpl_payload(items):
    """Build a minimal BiblioCommons-shaped payload from a list of event dicts."""
    return {
        "events": {
            "items": [e["id"] for e in items],
            "pagination": {"count": len(items), "pages": 1, "page": 1, "limit": 100},
        },
        "entities": {
            "events": {e["id"]: e for e in items},
            "locations": {
                "YO": {"id": "YO", "name": "Yorkville"},
                "KE": {"id": "KE", "name": "Kennedy/Eglinton"},
            },
            "eventTypes": {
                "T-CHILD": {"id": "T-CHILD", "name": "Kids & Family"},
                "T-COMP":  {"id": "T-COMP",  "name": "Computer Basics & Office Software"},
            },
            "eventAudiences": {
                "A-ADULT": {"id": "A-ADULT", "name": "Adults (18+)"},
            },
            "images": {
                "IMG1": {"id": "IMG1", "url": "https://tpl.example/img1.jpg"},
            },
        },
    }


def _tpl_event(eid, title, start, branch="YO", typ="T-COMP", img="IMG1", audience="A-ADULT", recurring=False):
    return {
        "id": eid,
        "key": start,
        "isRecurring": recurring,
        "definition": {
            "start": start,
            "end": None,
            "title": title,
            "description": f"<p>About <strong>{title}</strong>.</p>",
            "branchLocationId": branch,
            "typeIds": [typ],
            "audienceIds": [audience],
            "featuredImageId": img,
        },
    }


def test_tpl_iso_parses_naive_local_time():
    assert TPLBiblioCommonsScraper._to_iso("2026-05-20T17:00") == "2026-05-20T17:00:00Z"


def test_tpl_iso_handles_empty():
    assert TPLBiblioCommonsScraper._to_iso("") is None
    assert TPLBiblioCommonsScraper._to_iso(None) is None


def test_tpl_strip_html_collapses_and_decodes():
    s = TPLBiblioCommonsScraper._strip_html("<p>Hello&nbsp;<b>world</b></p>")
    assert s == "Hello world"


def test_tpl_build_event_happy_path():
    s = TPLBiblioCommonsScraper(max_pages=1)
    payload = _tpl_payload([_tpl_event("e1", "Coding 101", "2026-06-01T10:00")])
    raw = payload["entities"]["events"]["e1"]
    ev = s._build_event(raw, payload["entities"])
    assert ev is not None
    d = ev.to_dict()
    assert d["title"] == "Coding 101"
    assert d["date"] == "2026-06-01T10:00:00Z"
    assert d["source"] == "Toronto Public Library"
    assert d["is_free"] is True
    assert d["price_amount"] == 0.0
    assert "Yorkville" in d["location"]
    assert d["url"] == "https://tpl.bibliocommons.com/events/e1"
    assert d["image"] == "https://tpl.example/img1.jpg"


def test_tpl_build_event_dedupes_by_id():
    s = TPLBiblioCommonsScraper(max_pages=1)
    payload = _tpl_payload([_tpl_event("e1", "Coding 101", "2026-06-01T10:00")])
    raw = payload["entities"]["events"]["e1"]
    assert s._build_event(raw, payload["entities"]) is not None
    assert s._build_event(raw, payload["entities"]) is None  # second call dropped


def test_tpl_build_event_skips_when_title_or_date_missing():
    s = TPLBiblioCommonsScraper(max_pages=1)
    bad_title = _tpl_event("e1", "", "2026-06-01T10:00")
    bad_date  = _tpl_event("e2", "Storytime", "")
    payload = _tpl_payload([bad_title, bad_date])
    assert s._build_event(payload["entities"]["events"]["e1"], payload["entities"]) is None
    assert s._build_event(payload["entities"]["events"]["e2"], payload["entities"]) is None


def test_tpl_categorize_picks_up_metadata():
    s = TPLBiblioCommonsScraper(max_pages=1)
    cats, tags = s._categorize(
        title="French Conversation Circle",
        description="",
        type_names=["Newcomer Programs", "Languages"],
        audience_names=["Adults (18+)"],
    )
    assert "Community" in cats
    assert "Adults (18+)" in tags


def test_tpl_scrape_runs_full_loop_with_mocked_pages():
    """End-to-end scrape() call with the network mocked."""
    s = TPLBiblioCommonsScraper(max_pages=1, rate_limit=0)
    payload = _tpl_payload([
        _tpl_event("e1", "Storytime", "2026-06-01T10:00", typ="T-CHILD"),
        _tpl_event("e2", "Resume Workshop", "2026-06-02T18:00", typ="T-COMP"),
    ])
    s._fetch_page = MagicMock(return_value=payload)  # type: ignore[assignment]
    out = s.scrape()
    assert len(out) == 2
    assert {e.title for e in out} == {"Storytime", "Resume Workshop"}


# ---------- Single in the City scraper ----------

def _sitc_event(eid, title, start, city="Toronto", province="ON"):
    return {
        "id": eid,
        "title": title,
        "start_date": start,
        "end_date": start,
        "url": f"https://singleinthecity.ca/events/{eid}/",
        "image": {"url": "https://example.com/img.jpg"},
        "description": "<p>Mixer for ages 30-45.</p>",
        "cost": "$25",
        "venue": {
            "venue": "Test Venue",
            "city": city,
            "province": province,
            "address": "1 Yonge St",
            "geo_lat": "43.6532",
            "geo_lng": "-79.3832",
        },
    }


def test_sitc_filters_to_gta():
    s = SingleInTheCityScraper()
    keeper = s._build(_sitc_event("e1", "Toronto Speed Dating", "2026-05-06 19:00:00", city="Toronto"))
    rejected = s._build(_sitc_event("e2", "London Speed Dating", "2026-05-06 19:00:00", city="London"))
    assert keeper is not None
    assert rejected is None


def test_sitc_decodes_html_entities_in_title():
    s = SingleInTheCityScraper()
    ev = s._build(_sitc_event("e1", "Connection &#038; Cocktails", "2026-04-25 21:00:00"))
    assert ev is not None
    assert ev.title == "Connection & Cocktails"


def test_sitc_parses_price_amount_from_cost_string():
    s = SingleInTheCityScraper()
    ev = s._build(_sitc_event("e1", "Speed Dating", "2026-05-06 19:00:00"))
    assert ev is not None
    assert ev.price_amount == 25.0
    assert ev.is_free is False


def test_sitc_marks_free_events():
    s = SingleInTheCityScraper()
    raw = _sitc_event("e1", "Free Mixer", "2026-05-06 19:00:00")
    raw["cost"] = "Free"
    ev = s._build(raw)
    assert ev is not None
    assert ev.is_free is True


def test_sitc_dedupes_by_id():
    s = SingleInTheCityScraper()
    raw = _sitc_event("e1", "Speed Dating", "2026-05-06 19:00:00")
    assert s._build(raw) is not None
    assert s._build(raw) is None


def test_sitc_tags_speed_dating_and_professionals():
    s = SingleInTheCityScraper()
    ev = s._build(_sitc_event("e1", "Toronto Professional Speed Dating", "2026-05-06 19:00:00"))
    assert ev is not None
    assert "Speed Dating" in ev.tags
    assert "Professionals" in ev.tags


def test_sitc_scrape_paginates_and_stops():
    s = SingleInTheCityScraper(rate_limit=0)
    page1 = {
        "events": [_sitc_event("e1", "Toronto Mixer 1", "2026-05-06 19:00:00")],
        "total_pages": 2,
    }
    page2 = {
        "events": [_sitc_event("e2", "Toronto Mixer 2", "2026-05-13 19:00:00")],
        "total_pages": 2,
    }
    s._fetch = MagicMock(side_effect=[page1, page2, None])  # type: ignore[assignment]
    out = s.scrape()
    assert len(out) == 2
    assert {e.title for e in out} == {"Toronto Mixer 1", "Toronto Mixer 2"}


# ---------- Audit page integration ----------

def test_audit_page_exists_and_links_to_report():
    audit_html = REPO_ROOT / "TORONTOEVENTS_ANTIGRAVITY" / "audit" / "index.html"
    assert audit_html.is_file(), "audit page must be deployed at /audit/index.html"
    text = audit_html.read_text(encoding="utf-8")
    assert "Toronto_Events_Database_Audit.docx" in text
    for img in ("chart_categories.png", "chart_quality.png", "chart_coverage.png", "chart_priorities.png"):
        assert img in text, f"audit page missing image {img}"
    for asset in (
        "chart_categories.png", "chart_quality.png", "chart_coverage.png",
        "chart_priorities.png", "Toronto_Events_Database_Audit.docx",
    ):
        assert (audit_html.parent / asset).is_file(), f"missing asset {asset}"
