"""Tests for alpha_engine.pm_consensus_overlay.

Coverage:
  - both platforms agree → consensus pick emitted with boosted confidence
  - both platforms disagree → no consensus pick, disagreement logged
  - one platform stale → consensus pick skipped (graceful)
  - missing Polymarket file → empty (no crash)
  - missing Kalshi file → empty (no crash)
  - rollback env → empty
  - schema completeness check on emitted picks
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpha_engine import pm_consensus_overlay as overlay_mod


REQUIRED_FIELDS = {
    "id",
    "strategy",
    "source_system",
    "symbol",
    "category",
    "direction",
    "signal_type",
    "confidence",
    "entry_price",
    "entry_date",
    "take_profit",
    "stop_loss",
    "status",
    "type_label",
    "created_at",
    "pm_consensus_data",
    "reason",
}

REQUIRED_PM_DATA_FIELDS = {
    "kalshi_pick_id",
    "polymarket_pick_id",
    "kalshi_confidence",
    "polymarket_confidence",
    "alignment_boost",
    "consensus_confidence",
    "kalshi_updated_at",
    "polymarket_updated_at",
}


def _now_iso(offset_hours: float = 0.0) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=offset_hours)).isoformat()


def _kalshi_payload(picks: list[dict], *, fresh: bool = True) -> dict:
    return {
        "updated_at": _now_iso(0 if fresh else -10),
        "source": "kalshi",
        "picks": picks,
    }


def _poly_payload(picks: list[dict], *, fresh: bool = True) -> dict:
    return {
        "updated_at": _now_iso(0 if fresh else -10),
        "source": "polymarket",
        "picks": picks,
    }


def _kalshi_pick(symbol: str, direction: str, conf: float = 0.75) -> dict:
    return {
        "id": f"kalshi_{symbol}_{direction[0]}_test",
        "strategy": "kalshi_mtf_consensus",
        "symbol": symbol,
        "category": "crypto",
        "signal_type": "BUY" if direction == "LONG" else "SELL",
        "direction": direction,
        "entry_price": 100.0,
        "take_profit": 105.0 if direction == "LONG" else 95.0,
        "stop_loss": 95.0 if direction == "LONG" else 105.0,
        "confidence": conf,
        "status": "OPEN",
        "source_system": "kalshi",
        "created_at": _now_iso(),
        "kalshi_data": {"reason": "test"},
    }


def _poly_pick(symbol: str, direction: str, conf: float = 0.85) -> dict:
    return {
        "id": f"polymarket_{symbol}_{direction[0]}_test",
        "strategy": "polymarket_prediction",
        "symbol": symbol,
        "category": "crypto",
        "signal_type": "BUY" if direction == "LONG" else "SELL",
        "direction": direction,
        "entry_price": 100.5,
        "take_profit": 110.0 if direction == "LONG" else 90.0,
        "stop_loss": 92.0 if direction == "LONG" else 108.0,
        "confidence": conf,
        "status": "OPEN",
        "source_system": "polymarket",
        "created_at": _now_iso(),
        "polymarket_data": {"reason": "test"},
    }


@pytest.fixture
def isolated_data(monkeypatch, tmp_path):
    """Redirect overlay module to a temp data dir per test."""
    poly_path = tmp_path / "polymarket_signals.json"
    kalshi_path = tmp_path / "kalshi_signals.json"
    monkeypatch.setattr(overlay_mod, "POLYMARKET_FILE", poly_path)
    monkeypatch.setattr(overlay_mod, "KALSHI_FILE", kalshi_path)
    monkeypatch.delenv(overlay_mod.ROLLBACK_ENV, raising=False)
    overlay_mod.clear_disagreement_history()
    yield poly_path, kalshi_path
    overlay_mod.clear_disagreement_history()


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


# --- Tests ---------------------------------------------------------------


def test_both_platforms_agree_emits_boosted_pick(isolated_data):
    poly_path, kalshi_path = isolated_data
    _write(kalshi_path, _kalshi_payload([_kalshi_pick("BTCUSDT", "LONG", conf=0.80)]))
    _write(poly_path, _poly_payload([_poly_pick("BTCUSDT", "LONG", conf=0.90)]))

    picks = overlay_mod.pm_consensus_overlay()
    assert len(picks) == 1
    p = picks[0]
    # Base = (0.80 + 0.90) / 2 = 0.85; both > 0.7 → 1.2x boost = 1.02 → capped at 0.95.
    assert p["confidence"] == pytest.approx(0.95, abs=1e-3)
    assert p["pm_consensus_data"]["alignment_boost"] == 1.20
    assert p["direction"] == "LONG"
    assert p["symbol"] == "BTCUSDT"
    assert overlay_mod.get_disagreement_history() == []


def test_no_boost_when_one_side_below_threshold(isolated_data):
    poly_path, kalshi_path = isolated_data
    _write(kalshi_path, _kalshi_payload([_kalshi_pick("ETHUSDT", "LONG", conf=0.60)]))
    _write(poly_path, _poly_payload([_poly_pick("ETHUSDT", "LONG", conf=0.85)]))

    picks = overlay_mod.pm_consensus_overlay()
    assert len(picks) == 1
    # Base = 0.725, no boost (kalshi 0.60 < 0.70 threshold).
    assert picks[0]["confidence"] == pytest.approx(0.725, abs=1e-3)
    assert picks[0]["pm_consensus_data"]["alignment_boost"] == 1.0


def test_disagreement_emits_no_pick_logs_event(isolated_data):
    poly_path, kalshi_path = isolated_data
    _write(kalshi_path, _kalshi_payload([_kalshi_pick("BTCUSDT", "LONG", conf=0.80)]))
    _write(poly_path, _poly_payload([_poly_pick("BTCUSDT", "SHORT", conf=0.90)]))

    picks = overlay_mod.pm_consensus_overlay()
    assert picks == []

    log = overlay_mod.get_disagreement_history()
    assert len(log) == 1
    ev = log[0]
    assert ev["symbol"] == "BTCUSDT"
    assert ev["kalshi_direction"] == "LONG"
    assert ev["polymarket_direction"] == "SHORT"
    assert ev["verdict"] == "NEUTRAL_NO_TRADE"


def test_one_platform_stale_skips_overlay(isolated_data):
    poly_path, kalshi_path = isolated_data
    _write(kalshi_path, _kalshi_payload([_kalshi_pick("BTCUSDT", "LONG")], fresh=False))
    _write(poly_path, _poly_payload([_poly_pick("BTCUSDT", "LONG")], fresh=True))

    picks = overlay_mod.pm_consensus_overlay()
    assert picks == []


def test_both_stale_skips_overlay(isolated_data):
    poly_path, kalshi_path = isolated_data
    _write(kalshi_path, _kalshi_payload([_kalshi_pick("BTCUSDT", "LONG")], fresh=False))
    _write(poly_path, _poly_payload([_poly_pick("BTCUSDT", "LONG")], fresh=False))

    picks = overlay_mod.pm_consensus_overlay()
    assert picks == []


def test_missing_polymarket_file_returns_empty(isolated_data):
    poly_path, kalshi_path = isolated_data
    _write(kalshi_path, _kalshi_payload([_kalshi_pick("BTCUSDT", "LONG")]))
    # No polymarket file written.
    assert not poly_path.exists()

    picks = overlay_mod.pm_consensus_overlay()
    assert picks == []


def test_missing_kalshi_file_returns_empty(isolated_data):
    poly_path, kalshi_path = isolated_data
    _write(poly_path, _poly_payload([_poly_pick("BTCUSDT", "LONG")]))
    assert not kalshi_path.exists()

    picks = overlay_mod.pm_consensus_overlay()
    assert picks == []


def test_rollback_env_returns_empty(isolated_data, monkeypatch):
    poly_path, kalshi_path = isolated_data
    _write(kalshi_path, _kalshi_payload([_kalshi_pick("BTCUSDT", "LONG", conf=0.80)]))
    _write(poly_path, _poly_payload([_poly_pick("BTCUSDT", "LONG", conf=0.85)]))

    monkeypatch.setenv(overlay_mod.ROLLBACK_ENV, "1")
    assert overlay_mod.pm_consensus_overlay() == []


def test_schema_completeness_on_emitted_picks(isolated_data):
    poly_path, kalshi_path = isolated_data
    _write(
        kalshi_path,
        _kalshi_payload(
            [
                _kalshi_pick("BTCUSDT", "LONG", conf=0.75),
                _kalshi_pick("SOLUSDT", "SHORT", conf=0.72),
            ]
        ),
    )
    _write(
        poly_path,
        _poly_payload(
            [
                _poly_pick("BTCUSDT", "LONG", conf=0.85),
                _poly_pick("SOLUSDT", "SHORT", conf=0.80),
            ]
        ),
    )

    picks = overlay_mod.pm_consensus_overlay()
    assert len(picks) == 2

    for p in picks:
        missing = REQUIRED_FIELDS - set(p.keys())
        assert not missing, f"missing fields in pick {p.get('id')}: {missing}"
        assert p["strategy"] == "pm_consensus_overlay"
        assert p["source_system"] == "pm_consensus"
        assert p["direction"] in ("LONG", "SHORT")
        assert p["signal_type"] in ("BUY", "SELL")
        assert 0.0 < p["confidence"] <= 0.95
        assert p["type_label"] == "🔮 PM Overlay"
        assert p["status"] in ("OPEN", "SIGNAL")
        assert p["id"].startswith("pm_overlay_")

        d = p["pm_consensus_data"]
        missing_d = REQUIRED_PM_DATA_FIELDS - set(d.keys())
        assert not missing_d, f"missing pm_consensus_data fields: {missing_d}"
        assert d["alignment_boost"] in (1.0, 1.20)
        assert d["consensus_confidence"] == p["confidence"]


def test_only_agreeing_pairs_emitted_among_mixed(isolated_data):
    """Mixed inputs: one symbol agrees, another disagrees, a third only on one side."""
    poly_path, kalshi_path = isolated_data
    _write(
        kalshi_path,
        _kalshi_payload(
            [
                _kalshi_pick("BTCUSDT", "LONG", conf=0.80),  # agree
                _kalshi_pick("SOLUSDT", "LONG", conf=0.75),  # disagree (poly SHORT)
                _kalshi_pick("ETHUSDT", "LONG", conf=0.75),  # only kalshi
            ]
        ),
    )
    _write(
        poly_path,
        _poly_payload(
            [
                _poly_pick("BTCUSDT", "LONG", conf=0.85),
                _poly_pick("SOLUSDT", "SHORT", conf=0.80),
                _poly_pick("BNBUSDT", "SHORT", conf=0.80),  # only polymarket
            ]
        ),
    )

    picks = overlay_mod.pm_consensus_overlay()
    assert {p["symbol"] for p in picks} == {"BTCUSDT"}

    disagreements = overlay_mod.get_disagreement_history()
    assert {ev["symbol"] for ev in disagreements} == {"SOLUSDT"}
