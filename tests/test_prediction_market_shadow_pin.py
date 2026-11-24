"""Hard shadow pin for prediction-market picks.

2026-11-16 audit: PM picks must never reach sizing. Both merge paths
(alpha_engine.prediction_market_consensus and
prediction_market_agents.orchestrator) must stamp forward_test_only=True,
sizing_allowed=False, shadow=True.
"""
import json

from prediction_market_agents import orchestrator


def test_orchestrator_merge_stamps_shadow_pin(tmp_path, monkeypatch):
    active_path = tmp_path / "active_picks.json"
    active_path.write_text(json.dumps([]), encoding="utf-8")
    monkeypatch.setattr(orchestrator, "ACTIVE_PICKS_PATH", active_path)

    merged = orchestrator.merge_into_active_picks(
        [
            {
                "id": "pm_test_1",
                "symbol": "BTCUSDT",
                "direction": "LONG",
                "strategy": "prediction_market_consensus",
                "source_system": "prediction_market_consensus",
                "confidence": 0.85,
                "entry_price": 68000.0,
                "take_profit": 72000.0,
                "stop_loss": 66000.0,
            }
        ]
    )

    assert merged == 1
    data = json.loads(active_path.read_text(encoding="utf-8"))
    picks = data.get("picks", data) if isinstance(data, dict) else data
    pick = next(p for p in picks if p.get("symbol") == "BTCUSDT")
    assert pick["forward_test_only"] is True
    assert pick["sizing_allowed"] is False
    assert pick["shadow"] is True


# --- audit3 denylist isolation (2026-11-19) ---------------------------------
# These tests exercise feed-hygiene rules against synthetic BTC/CRYPTO fixtures.
# The audit3 denylist now vetoes BTC (a KILL symbol) and CRYPTO (a KILL class),
# so the fixture would be rejected before the rule under test is reached. The
# denylist has its own tests in tests/test_audit3_enforcement.py; disable it here
# and restore the environment when the module finishes.
import os as _os


def setUpModule():
    _os.environ["AUDIT3_DENYLIST_DISABLED"] = "1"


def tearDownModule():
    _os.environ.pop("AUDIT3_DENYLIST_DISABLED", None)
