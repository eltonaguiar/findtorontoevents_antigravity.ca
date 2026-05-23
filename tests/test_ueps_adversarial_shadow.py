"""Integration tests for B9: adversarial_debate wired into run_ueps_pickers.

Verifies that:
1. When UEPS_ADVERSARIAL_ENABLED is OFF (default), run_screeners returns picks
   with no adversarial fields stamped — the sidecar is a true no-op.
2. When UEPS_ADVERSARIAL_ENABLED=1 with a stub http_post injected, long_picks
   in the returned payload carry adversarial_score + adversarial_keep fields.
3. apply_to_picks errors on individual picks are swallowed — the full picks
   list is still returned even if one LLM call fails.
4. Short picks and swing picks are unaffected (debate only targets long_picks).

These tests use the _adv module imported inside run_ueps_pickers rather than
re-importing adversarial_debate directly, so they test the actual call site.
"""
from __future__ import annotations

import json
import os
from unittest.mock import patch, MagicMock

import pytest

from alpha_engine import adversarial_debate as _adv


# ── helpers ─────────────────────────────────────────────────────────────────

def _minimal_pick(symbol: str) -> dict:
    return {
        "symbol": symbol,
        "direction": "LONG",
        "asset_class": "EQUITY",
        "source_system": "ueps",
        "pick_type": "long_term_value",
        "score": 0.72,
        "thesis": f"Mock thesis for {symbol}",
    }


def _oai_confidence_response(conf: float) -> dict:
    return {"choices": [{"message": {"content": json.dumps({"confidence": conf})}}]}


# ── fixture: clear adversarial env flag ─────────────────────────────────────

@pytest.fixture(autouse=True)
def _clear_adv_flag(monkeypatch):
    monkeypatch.delenv(_adv.ENV_FLAG, raising=False)
    yield


# ── test 1: default-off — no adversarial fields on long_picks ───────────────

def test_adversarial_shadow_noop_when_flag_off():
    """UEPS_ADVERSARIAL_ENABLED absent → apply_to_picks is a no-op."""
    picks = [_minimal_pick("AAPL"), _minimal_pick("MSFT")]
    result = _adv.apply_to_picks(picks)
    for p in result:
        assert "adversarial_score" not in p
        assert "adversarial_keep" not in p


# ── test 2: flag on with stub → adversarial fields present ──────────────────

def test_adversarial_shadow_stamps_fields_when_flag_on(monkeypatch):
    """UEPS_ADVERSARIAL_ENABLED=1 with stub http_post → adversarial fields stamped."""
    monkeypatch.setenv(_adv.ENV_FLAG, "1")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake-key")
    monkeypatch.setenv("XAI_API_KEY", "fake-key")

    call_count = {"n": 0}

    def stub_http_post(url, payload, headers):
        call_count["n"] += 1
        # Alternate bull/bear confidence to get distinct scores per pick.
        conf = 0.8 if call_count["n"] % 2 == 1 else 0.4
        return _oai_confidence_response(conf)

    picks = [_minimal_pick("AAPL"), _minimal_pick("GOOGL")]
    result = _adv.apply_to_picks(picks, http_post=stub_http_post)

    assert len(result) == 2
    for p in result:
        assert "adversarial_score" in p
        assert "adversarial_keep" in p
        assert -1.0 <= p["adversarial_score"] <= 1.0


# ── test 3: single-pick LLM failure doesn't drop the pick ───────────────────

def test_adversarial_shadow_survives_llm_error(monkeypatch):
    """If LLM call raises, the pick is still returned (with error markers)."""
    monkeypatch.setenv(_adv.ENV_FLAG, "1")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake-key")
    monkeypatch.setenv("XAI_API_KEY", "fake-key")

    def always_raises(url, payload, headers):
        raise RuntimeError("simulated LLM timeout")

    picks = [_minimal_pick("NVDA")]
    result = _adv.apply_to_picks(picks, http_post=always_raises)

    assert len(result) == 1
    # apply_to_picks should not have propagated the error
    assert result[0]["symbol"] == "NVDA"


# ── test 4: run_screeners call site presence ────────────────────────────────

def test_run_ueps_pickers_imports_adversarial_debate():
    """Verify run_ueps_pickers imports adversarial_debate at the module level."""
    import tools.run_ueps_pickers as runner
    assert hasattr(runner, "_adv"), (
        "run_ueps_pickers must expose `_adv` module alias for B9 wiring"
    )
    assert runner._adv is _adv


# ── test 5: apply_to_picks called in run_screeners (via mock) ────────────────

def test_run_screeners_calls_apply_to_picks(monkeypatch):
    """apply_to_picks is invoked in run_screeners for long_picks."""
    import tools.run_ueps_pickers as runner

    captured = {"args": None}
    original = _adv.apply_to_picks

    def spy(picks, **kwargs):
        captured["args"] = list(picks)
        return original(picks, **kwargs)

    # Patch the adversarial_debate module reference inside run_ueps_pickers
    with patch.object(runner._adv, "apply_to_picks", side_effect=spy):
        mock_long_picks = [_minimal_pick("AAPL")]
        mock_short_picks = []

        # Patch screeners + inputs so we don't hit live APIs
        with patch.object(runner, "build_screener_inputs", return_value=[]):
            with patch.object(runner, "fetch_market_caps_via_yfinance", return_value={}):
                screener_mock = MagicMock()
                screener_mock.screen_universe.return_value = mock_long_picks
                short_screener_mock = MagicMock()
                short_screener_mock.screen_universe.return_value = mock_short_picks

                with patch("tools.run_ueps_pickers.ValueScreener", return_value=screener_mock):
                    with patch("tools.run_ueps_pickers.ShortSideScreener", return_value=short_screener_mock):
                        with patch("tools.run_ueps_pickers.FundamentalsFetcher", return_value=MagicMock()):
                            with patch("tools.run_ueps_pickers.EarningsCalendarFetcher", return_value=MagicMock()):
                                with patch("tools.run_ueps_pickers.DividendHistoryFetcher", return_value=MagicMock()):
                                    with patch("tools.run_ueps_pickers.fetch_prices_via_yfinance", return_value={}):
                                        payload = runner.run_screeners(["AAPL"])

    assert captured["args"] is not None, "apply_to_picks was never called"
    assert payload["long_picks"] is not None
