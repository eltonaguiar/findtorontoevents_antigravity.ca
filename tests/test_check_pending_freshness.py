"""Tests for tools/check_pending_freshness.py."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from tools.check_pending_freshness import parse_pending_items, check_item, KNOWN_SIGNALS


def test_parse_pending_items_extracts_pending(tmp_path: Path) -> None:
    plan = tmp_path / "plan.md"
    plan.write_text(textwrap.dedent("""\
        | M-001 | BTC UTC-hour filter | P0 | infra | S | none | PENDING | Wire filter into gate |
        | M-002 | DB Freshness GH workflow | P1 | infra | S | none | DONE 2026-05-17 | shipped |
        | M-099 | Some new item | P2 | infra | M | none | PLANNED | Not yet built |
    """), encoding="utf-8")
    items = parse_pending_items(plan)
    ids = [i["id"] for i in items]
    assert "M-001" in ids, "PENDING item should be extracted"
    assert "M-099" in ids, "PLANNED item should be extracted"
    assert "M-002" not in ids, "DONE item should NOT be extracted"


def test_parse_pending_items_skips_pending_to_done(tmp_path: Path) -> None:
    plan = tmp_path / "plan.md"
    plan.write_text(
        "| M-067 | Registry-backed verdict | P0 | infra | M | none | PENDING → DONE 2026-05-17 | done |\n",
        encoding="utf-8",
    )
    items = parse_pending_items(plan)
    assert not items, "PENDING→DONE line should be skipped"


def test_known_signals_registered_for_common_items() -> None:
    important = ["M-001", "M-003", "M-006", "M-007", "M-010", "M-041", "M-061", "M-067"]
    for m_id in important:
        assert m_id in KNOWN_SIGNALS, f"{m_id} should have grep signals registered"


def test_check_item_unregistered_returns_unregistered() -> None:
    # M-XXX not in KNOWN_SIGNALS
    result = check_item("M-999")
    assert result == "UNREGISTERED"


def test_check_item_empty_signals_returns_none() -> None:
    # M-039 has empty signals (not yet implemented, can't auto-detect)
    result = check_item("M-039")
    assert result is None, "Empty signals should return None (PENDING_CLEAN)"


def test_check_item_m001_detected(monkeypatch) -> None:
    # Monkeypatch grep to simulate finding CRYPTO_UTC_HOUR_FILTER
    import tools.check_pending_freshness as mod

    def _fake_grep(pattern):
        return pattern in ("CRYPTO_UTC_HOUR_FILTER", "utc_hour.*filter", "death.zone")

    monkeypatch.setattr(mod, "grep_repo", _fake_grep)
    result = check_item("M-001")
    assert result == "CRYPTO_UTC_HOUR_FILTER", "M-001 should be detected via CRYPTO_UTC_HOUR_FILTER"


def test_check_item_not_found_returns_none(monkeypatch) -> None:
    import tools.check_pending_freshness as mod
    monkeypatch.setattr(mod, "grep_repo", lambda _: False)
    result = check_item("M-001")
    assert result is None
