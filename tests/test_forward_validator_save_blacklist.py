"""
Regression: alpha_engine.forward_validator.save_active_picks() must enforce
BLACKLISTED_STRATEGIES before writing active_picks.json.

The canonical write path filters by the core-whitelist kill list and by
BLOCKED_SYMBOLS, but historically did NOT filter by
config.BLACKLISTED_STRATEGIES. Any emitter that writes through
save_active_picks (the code comment in the function notes "11 emitters
write to active_picks.json without going through production_scanner's
blocked-symbol gate") could therefore persist a pick whose strategy is
blacklisted, as long as it is not on the separate core_whitelist kill_list.

This test locks in the fix: blacklisted strategies are filtered at the
canonical recording path.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from alpha_engine import forward_validator as fv  # noqa: E402
from alpha_engine.config import BLACKLISTED_STRATEGIES  # noqa: E402


def _pick(strategy: str, symbol: str = "BTCUSDT") -> dict:
    return {
        "id": f"t-{strategy}-{symbol}",
        "symbol": symbol,
        "direction": "LONG",
        "strategy": strategy,
        "source_system": strategy,
        "category": "crypto",
        "asset_class": "CRYPTO",
        "entry_price": 100.0,
        "take_profit": 105.0,
        "stop_loss": 98.0,
        "confidence": 0.9,
        "elite_score": 80,
        "signal_type": "BUY",
    }


@pytest.mark.parametrize("strat", list(BLACKLISTED_STRATEGIES))
def test_save_active_picks_filters_blacklisted_strategies(strat, tmp_path, monkeypatch):
    """save_active_picks must never persist a BLACKLISTED_STRATEGIES pick."""
    out = tmp_path / "active_picks.json"
    monkeypatch.setattr(fv, "ACTIVE_PICKS_PATH", out)
    picks = [_pick(strat), _pick("dna_winner", symbol="ETHUSDT")]
    fv.save_active_picks(picks)
    saved = json.loads(out.read_text())
    leaked = [p for p in saved if str(p.get("strategy", "") or "").lower().strip() == strat.lower()]
    assert leaked == [], (
        f"Blacklisted strategy {strat!r} leaked into active_picks.json: "
        f"{[p.get('id') for p in leaked]}"
    )
    # The non-blacklisted control pick must survive.
    assert any(p.get("strategy") == "dna_winner" for p in saved)


def test_save_active_picks_keeps_non_blacklisted(tmp_path, monkeypatch):
    """Negative control — non-blacklisted picks fall through to save."""
    out = tmp_path / "active_picks.json"
    monkeypatch.setattr(fv, "ACTIVE_PICKS_PATH", out)
    fv.save_active_picks([_pick("dna_winner")])
    saved = json.loads(out.read_text())
    assert any(p.get("strategy") == "dna_winner" for p in saved)


def test_live_active_picks_no_new_blacklisted_leaks_via_save(tmp_path, monkeypatch):
    """The canonical save path must not introduce NEW blacklisted leaks.

    Run the persisted active_picks.json through save_active_picks() (as the
    production cycle does on every writeback) and confirm the resulting set
    contains zero BLACKLISTED_STRATEGIES rows. This verifies the guard works
    against the real data feed without mutating the on-disk file.
    """
    path = fv.ACTIVE_PICKS_PATH
    if not path.exists():
        pytest.skip(f"active_picks.json not present at {path}")
    data = json.loads(path.read_text())
    rows = data if isinstance(data, list) else (data.get("picks") or data.get("active") or [])
    if not rows:
        pytest.skip("active_picks.json is empty")
    out = tmp_path / "active_picks.json"
    # Route the write to a temp file so the real on-disk file is never touched.
    monkeypatch.setattr(fv, "ACTIVE_PICKS_PATH", out)
    fv.save_active_picks(rows)
    saved = json.loads(out.read_text())
    bl = {s.lower() for s in BLACKLISTED_STRATEGIES}
    leaks = [
        r for r in saved
        if str(r.get("strategy", "") or "").lower().strip() in bl
    ]
    assert leaks == [], (
        f"{len(leaks)} BLACKLISTED_STRATEGIES rows passed through "
        f"save_active_picks: {[r.get('id') for r in leaks[:5]]}"
    )
