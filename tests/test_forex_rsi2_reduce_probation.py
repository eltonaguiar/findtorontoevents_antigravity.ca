"""REDUCE-state enforcement tests (forex_rsi2 reconcile + crypto-momentum-scout).

Finding (2026-11-16): /audit STRATEGY_DEGRADATION "REDUCE" verdicts (forex_rsi2:
7d WR 5% vs 20% baseline; crypto-momentum-scout: 0% vs 41%) were advisory-only.
The REDUCE state is now a real flag in the strategy config
(alpha_engine.config.STRATEGY_PROBATION: `size_multiplier` / `probation`) that
alpha_engine.score_booster reads: matching picks are stamped with
`size_multiplier` (sizing layer must honour it) and are excluded from score
boosts. Live performance_alerts REDUCE rows fold in at runtime with 0.5x
(T2 REDUCE), so future alerts are enforceable without a code change.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpha_engine import score_booster
from alpha_engine.config import STRATEGY_PROBATION


def test_config_flags_cover_live_reduce_alerts():
    assert STRATEGY_PROBATION["crypto-momentum-scout"]["probation"] is True
    assert STRATEGY_PROBATION["crypto-momentum-scout"]["size_multiplier"] == 0.0
    assert STRATEGY_PROBATION["forex_rsi2_mean_reversion"]["probation"] is True
    assert STRATEGY_PROBATION["forex_rsi2_mean_reversion"]["size_multiplier"] == 0.5


def test_apply_probation_flags_stamps_picks():
    picks = [
        {"symbol": "SOL-USD", "strategy": "crypto-momentum-scout", "score": 50},
        {"symbol": "EURUSD=X", "strategy": "forex_rsi2_mean_reversion", "score": 50},
        {"symbol": "SPY", "strategy": "unrelated_strat", "score": 50},
    ]
    summary = score_booster._apply_probation_flags(picks, {})
    assert summary["enabled"] is True
    assert summary["flagged"] == 2
    assert set(summary["strategies"]) == {
        "crypto-momentum-scout",
        "forex_rsi2_mean_reversion",
    }
    scout, forex, other = picks
    assert scout["probation"] is True and scout["size_multiplier"] == 0.0
    assert forex["probation"] is True and forex["size_multiplier"] == 0.5
    assert "probation" not in other and "size_multiplier" not in other


def test_live_reduce_alerts_fold_in_with_half_size():
    payload = {
        "performance_alerts": [
            {
                "type": "STRATEGY_DEGRADATION",
                "action": "REDUCE",
                "message": "new_degraded: rolling 7d WR 5% vs baseline 40% (>20% drop)",
                "details": {"strategy": "new_degraded_strat"},
            },
            {
                "type": "DATA_STALE",
                "action": "MONITOR",
                "details": {"system": "whatever"},
            },
        ]
    }
    picks = [{"symbol": "QQQ", "strategy": "new_degraded_strat", "score": 50}]
    summary = score_booster._apply_probation_flags(picks, payload)
    assert picks[0]["probation"] is True
    assert picks[0]["size_multiplier"] == 0.5
    assert "new_degraded_strat" in summary["strategies"]


def test_config_entries_override_alert_default():
    payload = {
        "performance_alerts": [
            {
                "type": "STRATEGY_DEGRADATION",
                "action": "REDUCE",
                "message": "crypto-momentum-scout: rolling 7d WR 0% vs baseline 41%",
                "details": {"strategy": "crypto-momentum-scout"},
            }
        ]
    }
    picks = [{"symbol": "BTC-USD", "strategy": "crypto-momentum-scout", "score": 50}]
    score_booster._apply_probation_flags(picks, payload)
    # operator decision (0.0) wins over the runtime 0.5 default
    assert picks[0]["size_multiplier"] == 0.0


def test_run_score_booster_suppresses_boosts_for_probation(monkeypatch, tmp_path):
    payload_path = tmp_path / "payload.json"
    payload = {
        "performance_alerts": [],
        "picks": {
            "active": [
                {
                    "symbol": "SPY",
                    "asset_class": "EQUITY",
                    "direction": "LONG",
                    "strategy": "zz_control_strat",
                    "score": 50,
                },
                {
                    "symbol": "IWM",
                    "asset_class": "EQUITY",
                    "direction": "LONG",
                    "strategy": "forex_rsi2_mean_reversion",
                    "score": 50,
                },
            ],
            "recent_closed": [],
        },
    }
    payload_path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(score_booster, "BOOST_LOG_PATH", tmp_path / "boost_log.json")
    monkeypatch.setattr(score_booster, "_classify_family", lambda p: "kimi_signal_tracking")
    monkeypatch.setattr(score_booster, "compute_boost", lambda f, l, c: 10)

    summary = score_booster.run_score_booster(payload_path)

    assert summary.get("error") is None
    assert summary["probation"]["flagged"] == 1
    out = json.loads(payload_path.read_text(encoding="utf-8"))
    control, probation = out["picks"]["active"]
    assert control.get("_score_boosted") is True, "non-probation pick must still boost"
    assert control["score"] == 60
    assert probation.get("_score_boosted") is None, "probation pick must not be boosted"
    assert probation["probation"] is True
    assert probation["size_multiplier"] == 0.5
