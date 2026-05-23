"""Tests for tools/render_sidecar_status_md.py."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import render_sidecar_status_md as rss  # noqa: E402


def test_renders_with_empty_payload(tmp_path):
    md = rss.render_markdown({}, "2026-05-09T21:29:05Z")
    assert "Sidecar Promotion Status — 2026-05-09T21:29:05Z" in md
    assert "No sidecar promotion data available" in md
    # No table headers when empty.
    assert "| Strategy | Status |" not in md
    # Footer still present.
    assert "Regen: `python tools/render_sidecar_status_md.py`" in md


def test_renders_promoted_first():
    payload = {
        "incub_strat": {
            "n": 5, "wr": 40.0, "pf": 0.9,
            "gate_n": 30, "gate_wr": 50.0, "gate_pf": 1.3,
            "status": "INCUBATING",
            "days_since_first_trade": 3,
            "eta_to_promotion_days": 15.0,
        },
        "promoted_strat": {
            "n": 200, "wr": 60.0, "pf": 1.8,
            "gate_n": 30, "gate_wr": 55.0, "gate_pf": 1.3,
            "status": "PROMOTED",
            "days_since_first_trade": 60,
            "eta_to_promotion_days": None,
        },
        "ready_strat": {
            "n": 35, "wr": 58.0, "pf": 1.5,
            "gate_n": 30, "gate_wr": 55.0, "gate_pf": 1.3,
            "status": "READY_TO_PROMOTE",
            "days_since_first_trade": 20,
            "eta_to_promotion_days": None,
        },
        "below_strat": {
            "n": 50, "wr": 30.0, "pf": 0.7,
            "gate_n": 30, "gate_wr": 55.0, "gate_pf": 1.3,
            "status": "BELOW_GATE",
            "days_since_first_trade": 25,
            "eta_to_promotion_days": None,
        },
    }
    md = rss.render_markdown(payload, "2026-05-09T00:00:00Z")
    # Find row order in markdown.
    pos_promoted = md.index("promoted_strat")
    pos_ready = md.index("ready_strat")
    pos_below = md.index("below_strat")
    pos_incub = md.index("incub_strat")
    assert pos_promoted < pos_ready < pos_below < pos_incub


def test_status_badge_for_each_status():
    payload = {
        f"strat_{s.lower()}": {
            "n": 1, "wr": 0.0, "pf": 0.0,
            "gate_n": 30, "gate_wr": 50.0, "gate_pf": 1.3,
            "status": s,
            "days_since_first_trade": 1,
            "eta_to_promotion_days": None,
        }
        for s in ("PROMOTED", "READY_TO_PROMOTE", "BELOW_GATE", "INCUBATING")
    }
    md = rss.render_markdown(payload, "now")
    assert "🟢 PROMOTED" in md
    assert "🚀 READY_TO_PROMOTE" in md
    assert "🟡 BELOW_GATE" in md
    assert "🔵 INCUBATING" in md


def test_writes_to_correct_path(tmp_path):
    fake_data = tmp_path / "dashboard_data.json"
    fake_out = tmp_path / "out" / "SIDECAR_STATUS.md"
    fake_data.write_text(json.dumps({
        "generated_at": "2026-05-09T12:00:00Z",
        "sidecar_promotion_status": {
            "x": {
                "n": 0, "wr": 0.0, "pf": 0.0,
                "gate_n": 30, "gate_wr": 50.0, "gate_pf": 1.3,
                "status": "INCUBATING",
                "days_since_first_trade": 0,
                "eta_to_promotion_days": None,
            }
        }
    }))
    rc = rss.main([str(fake_data), str(fake_out)])
    assert rc == 0
    assert fake_out.exists()
    text = fake_out.read_text(encoding="utf-8")
    assert "2026-05-09T12:00:00Z" in text
    assert "`x`" in text


def test_eta_days_handles_None():
    # Incubating sidecar with no trades yet → eta None must not blow up
    # and must render as the em-dash placeholder.
    payload = {
        "no_trades_yet": {
            "n": 0, "wr": 0.0, "pf": 0.0,
            "gate_n": 20, "gate_wr": 55.0, "gate_pf": 1.5,
            "status": "INCUBATING",
            "days_since_first_trade": 0,
            "eta_to_promotion_days": None,
        }
    }
    md = rss.render_markdown(payload, "now")
    # Find the row for no_trades_yet, confirm None rendered as em-dash.
    row = next(line for line in md.splitlines() if "no_trades_yet" in line)
    cells = [c.strip() for c in row.strip("|").split("|")]
    # Columns: name, status, n, wr, pf, gate, eta, days
    assert cells[6] == "—"  # eta column


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
