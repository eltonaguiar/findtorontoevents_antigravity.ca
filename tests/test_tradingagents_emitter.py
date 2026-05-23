"""Tests for alpha_engine/tradingagents_emitter.py.

No live LLM calls — http_post is injected so CI never hits a network. Verifies:
  1. Default-OFF: emit_picks short-circuits with reason in summary.
  2. _parse_decision_json tolerates fences, prose wrappers, and bad JSON.
  3. _assemble_pick rejects below-floor confidence + bad risk-reward + HOLD.
  4. _assemble_pick stamps the dashboard-expected schema for BUY and SELL.
  5. emit_picks writes a JSON file with the right shape and respects the watchlist.
  6. emit_picks records errors (per-ticker failure does not abort the run).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from alpha_engine import tradingagents_emitter as tae


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    for k in (
        tae.ENV_FLAG, tae.ENV_PROVIDER, tae.ENV_MODEL,
        tae.ENV_MULTIASSET_PROMPT,
        "TRADINGAGENTS_CONFIDENCE_FLOOR",
        "DEEPSEEK_API_KEY", "DEEPSEEK_API",
        "XAI_API_KEY", "X_AI_KEY",
    ):
        monkeypatch.delenv(k, raising=False)
    yield


@pytest.fixture
def small_watchlist(tmp_path):
    p = tmp_path / "wl.json"
    p.write_text(json.dumps({
        "tickers": [
            {"symbol": "NVDA", "asset_class": "EQUITY"},
            {"symbol": "TSLA", "asset_class": "EQUITY"},
        ],
    }), encoding="utf-8")
    return p


def _oai_response(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


# ────────────────────────────────────────────────────────────────────────
# Default-OFF
# ────────────────────────────────────────────────────────────────────────

def test_emit_is_noop_when_flag_off(small_watchlist, tmp_path):
    out_path = tmp_path / "out.json"

    def stub(*_a, **_kw):
        raise AssertionError("LLM should not be called when flag is off")

    summary = tae.emit_picks(
        watchlist_path=small_watchlist, output_path=out_path, http_post=stub,
    )
    assert summary["emitted"] == 0
    assert "TRADINGAGENTS_EMITTER_ENABLED" in summary["reason"]
    assert not out_path.exists()


# ────────────────────────────────────────────────────────────────────────
# JSON parser
# ────────────────────────────────────────────────────────────────────────

def test_parse_clean_json():
    obj = tae._parse_decision_json('{"action":"BUY","confidence":0.8}')
    assert obj == {"action": "BUY", "confidence": 0.8}


def test_parse_markdown_fence():
    text = '```json\n{"action":"HOLD","confidence":0.4}\n```'
    obj = tae._parse_decision_json(text)
    assert obj["action"] == "HOLD"


def test_parse_with_prose_prefix():
    text = "Here is the decision:\n{\"action\":\"BUY\",\"confidence\":0.7}\nThanks."
    obj = tae._parse_decision_json(text)
    assert obj["action"] == "BUY"


def test_parse_returns_none_on_garbage():
    assert tae._parse_decision_json("nope, not json") is None


def test_parse_returns_none_on_array():
    """Top-level must be an object, not an array."""
    assert tae._parse_decision_json("[1,2,3]") is None


# ────────────────────────────────────────────────────────────────────────
# _assemble_pick
# ────────────────────────────────────────────────────────────────────────

def test_assemble_buy_pick_has_dashboard_shape():
    decision = {
        "action": "BUY",
        "confidence": 0.78,
        "thesis": "Strong AI capex tailwind.",
        "rationale": "Multi-quarter beat-and-raise pattern with widening moat.",
        "time_horizon_days": 30,
        "target_pct": 12.0,
        "stop_pct": 5.0,
        "key_risks": ["valuation", "China export controls"],
    }
    pick = tae._assemble_pick(decision, "NVDA", "EQUITY", ts_iso="2026-04-30T18:30:00+00:00")
    assert pick is not None
    assert pick["symbol"] == "NVDA"
    assert pick["direction"] == "LONG"
    assert pick["signal_type"] == "BUY"
    assert pick["asset_class"] == "EQUITY"
    assert pick["category"] == "equity"
    assert pick["source_system"] == "tradingagents"
    assert pick["strategy"] == "tradingagents_consensus"
    assert pick["status"] == "OPEN"
    assert pick["score"] == 78
    assert pick["confidence"] == 0.78
    assert pick["take_profit_pct"] == 12.0
    assert pick["stop_loss_pct"] == 5.0
    assert pick["time_horizon_days"] == 30
    assert pick["key_risks"] == ["valuation", "China export controls"]
    # entry_price intentionally None — downstream resolver fills it from live prices.
    assert pick["entry_price"] is None
    assert pick["id"].startswith("tradingagents::NVDA::")


def test_assemble_sell_pick_uses_short_direction():
    decision = {
        "action": "SELL", "confidence": 0.72,
        "target_pct": -8.0, "stop_pct": 4.0,
        "thesis": "x", "rationale": "y", "time_horizon_days": 14,
    }
    pick = tae._assemble_pick(decision, "AMD", "EQUITY", ts_iso="2026-04-30T18:30:00+00:00")
    assert pick is not None
    assert pick["direction"] == "SHORT"
    assert pick["signal_type"] == "SELL"


def test_assemble_rejects_hold():
    decision = {"action": "HOLD", "confidence": 0.5,
                "target_pct": 0.0, "stop_pct": 3.0}
    assert tae._assemble_pick(decision, "X", "EQUITY", ts_iso="t") is None


def test_assemble_rejects_below_confidence_floor():
    decision = {"action": "BUY", "confidence": 0.40,
                "target_pct": 10.0, "stop_pct": 5.0}
    assert tae._assemble_pick(decision, "X", "EQUITY", ts_iso="t") is None


def test_assemble_respects_custom_floor(monkeypatch):
    monkeypatch.setenv("TRADINGAGENTS_CONFIDENCE_FLOOR", "0.50")
    decision = {"action": "BUY", "confidence": 0.55,
                "target_pct": 10.0, "stop_pct": 5.0,
                "thesis": "x", "rationale": "y", "time_horizon_days": 30}
    assert tae._assemble_pick(decision, "X", "EQUITY", ts_iso="t") is not None


def test_assemble_rejects_zero_or_negative_stop():
    decision = {"action": "BUY", "confidence": 0.8,
                "target_pct": 10.0, "stop_pct": 0.0}
    assert tae._assemble_pick(decision, "X", "EQUITY", ts_iso="t") is None


def test_assemble_rejects_buy_with_target_below_stop():
    """target_pct must be >= stop_pct (positive risk-reward) for BUY."""
    decision = {"action": "BUY", "confidence": 0.8,
                "target_pct": 3.0, "stop_pct": 5.0,
                "thesis": "x", "rationale": "y", "time_horizon_days": 30}
    assert tae._assemble_pick(decision, "X", "EQUITY", ts_iso="t") is None


def test_assemble_truncates_long_text():
    decision = {
        "action": "BUY", "confidence": 0.8,
        "target_pct": 10.0, "stop_pct": 5.0,
        "thesis": "T" * 1000, "rationale": "R" * 1000,
        "key_risks": ["x" * 200] * 10,
        "time_horizon_days": 30,
    }
    pick = tae._assemble_pick(decision, "X", "EQUITY", ts_iso="t")
    assert pick is not None
    assert len(pick["thesis"]) <= 400
    assert len(pick["rationale"]) <= 800
    assert len(pick["key_risks"]) <= 5
    for r in pick["key_risks"]:
        assert len(r) <= 120


def test_assemble_clamps_horizon():
    decision = {"action": "BUY", "confidence": 0.8,
                "target_pct": 10.0, "stop_pct": 5.0,
                "thesis": "x", "rationale": "y",
                "time_horizon_days": 9999}
    pick = tae._assemble_pick(decision, "X", "EQUITY", ts_iso="t")
    assert pick["time_horizon_days"] == 365


# ────────────────────────────────────────────────────────────────────────
# end-to-end emit_picks
# ────────────────────────────────────────────────────────────────────────

def test_emit_picks_writes_dashboard_compatible_payload(monkeypatch, small_watchlist, tmp_path):
    monkeypatch.setenv(tae.ENV_FLAG, "1")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "k")

    def stub(url, headers, body):
        b = json.loads(body)
        ticker = b["messages"][1]["content"].split("Ticker: ")[1].split("\n")[0]
        # NVDA -> BUY high-conf; TSLA -> HOLD (will be skipped)
        if ticker == "NVDA":
            return _oai_response(json.dumps({
                "action": "BUY", "confidence": 0.82,
                "thesis": "AI demand", "rationale": "Beat-and-raise",
                "time_horizon_days": 21, "target_pct": 11.0, "stop_pct": 5.0,
                "key_risks": ["valuation"],
            }))
        return _oai_response(json.dumps({
            "action": "HOLD", "confidence": 0.4,
            "thesis": "wait", "rationale": "mixed",
            "time_horizon_days": 14, "target_pct": 0.0, "stop_pct": 3.0,
        }))

    out_path = tmp_path / "out.json"
    summary = tae.emit_picks(
        watchlist_path=small_watchlist, output_path=out_path, http_post=stub,
    )

    assert summary["emitted"] == 1
    assert "TSLA" in summary["skipped"]
    assert summary["errors"] == []
    assert out_path.exists()

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["source_system"] == "tradingagents"
    assert payload["watchlist_size"] == 2
    assert len(payload["active_picks"]) == 1
    pick = payload["active_picks"][0]
    assert pick["symbol"] == "NVDA"
    assert pick["direction"] == "LONG"
    assert pick["source_system"] == "tradingagents"


def test_emit_picks_records_per_ticker_errors(monkeypatch, small_watchlist, tmp_path):
    """A transport error on one ticker does not abort the run."""
    monkeypatch.setenv(tae.ENV_FLAG, "1")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "k")

    def stub(url, headers, body):
        ticker = json.loads(body)["messages"][1]["content"].split("Ticker: ")[1].split("\n")[0]
        if ticker == "NVDA":
            return _oai_response(json.dumps({
                "action": "BUY", "confidence": 0.8,
                "thesis": "x", "rationale": "y",
                "time_horizon_days": 21, "target_pct": 10.0, "stop_pct": 5.0,
            }))
        # TSLA — return malformed JSON to trigger DebateError via parser
        return _oai_response("not json at all and no braces")

    out_path = tmp_path / "out.json"
    summary = tae.emit_picks(
        watchlist_path=small_watchlist, output_path=out_path, http_post=stub,
    )
    assert summary["emitted"] == 1
    assert len(summary["errors"]) == 1
    assert summary["errors"][0]["ticker"] == "TSLA"


# ────────────────────────────────────────────────────────────────────────
# B24 — Placeholder thesis/rationale detection
# ────────────────────────────────────────────────────────────────────────

_VALID_DECISION = {
    "action": "BUY", "confidence": 0.78,
    "target_pct": 12.0, "stop_pct": 5.0,
    "time_horizon_days": 21,
    "thesis": "Nvidia's data-center GPU backlog extends 18 months.",
    "rationale": "Beat-and-raise cycle for 4 consecutive quarters with widening margins.",
}


@pytest.mark.parametrize("placeholder", [
    "Thesis text",
    "Rationale text",
    "thesis text",
    "THESIS TEXT",
    "  Thesis Text  ",  # strips before compare
    "Thesis here",
    "your thesis here",
    "n/a",
    "N/A",
    "",
])
def test_assemble_rejects_placeholder_thesis(placeholder):
    """_assemble_pick must return None when thesis is a known placeholder."""
    decision = dict(_VALID_DECISION, thesis=placeholder)
    assert tae._assemble_pick(decision, "NVDA", "EQUITY", ts_iso="t") is None


@pytest.mark.parametrize("placeholder", [
    "Rationale text",
    "Thesis text",
    "rationale here",
    "your rationale here",
    "n/a",
    "",
])
def test_assemble_rejects_placeholder_rationale(placeholder):
    """_assemble_pick must return None when rationale is a known placeholder."""
    decision = dict(_VALID_DECISION, rationale=placeholder)
    assert tae._assemble_pick(decision, "NVDA", "EQUITY", ts_iso="t") is None


def test_assemble_accepts_real_thesis_and_rationale():
    """Ensure a legitimate (non-placeholder) thesis+rationale passes through."""
    pick = tae._assemble_pick(_VALID_DECISION, "NVDA", "EQUITY", ts_iso="t")
    assert pick is not None
    assert "Nvidia" in pick["thesis"]


def test_emit_picks_skips_placeholder_picks(monkeypatch, small_watchlist, tmp_path):
    """emit_picks must count placeholder picks as skipped, not emitted."""
    monkeypatch.setenv(tae.ENV_FLAG, "1")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "k")

    def stub(url, headers, body):
        ticker = json.loads(body)["messages"][1]["content"].split("Ticker: ")[1].split("\n")[0]
        if ticker == "NVDA":
            # LLM echoed placeholder text verbatim
            return _oai_response(json.dumps({
                "action": "BUY", "confidence": 0.82,
                "thesis": "Thesis text",      # placeholder
                "rationale": "Rationale text",  # placeholder
                "time_horizon_days": 21, "target_pct": 11.0, "stop_pct": 5.0,
            }))
        return _oai_response(json.dumps({
            "action": "HOLD", "confidence": 0.4,
            "thesis": "mixed signals", "rationale": "no clear edge",
            "time_horizon_days": 14, "target_pct": 0.0, "stop_pct": 3.0,
        }))

    out_path = tmp_path / "out.json"
    summary = tae.emit_picks(
        watchlist_path=small_watchlist, output_path=out_path, http_post=stub,
    )
    # NVDA has placeholder text → skipped; TSLA is HOLD → skipped
    assert summary["emitted"] == 0
    assert "NVDA" in summary["skipped"]

def test_dashboard_compatibility_smoke(monkeypatch, small_watchlist, tmp_path):
    """The output JSON must contain an `active_picks` key the dashboard reader expects."""
    monkeypatch.setenv(tae.ENV_FLAG, "1")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "k")

    def stub(*_a, **_kw):
        return _oai_response(json.dumps({
            "action": "BUY", "confidence": 0.8,
            "thesis": "x", "rationale": "y",
            "time_horizon_days": 21, "target_pct": 10.0, "stop_pct": 5.0,
        }))

    out_path = tmp_path / "out.json"
    tae.emit_picks(watchlist_path=small_watchlist, output_path=out_path, http_post=stub)
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    # Mirrors what _extract_picks() in dashboard_generator.py looks for.
    assert "active_picks" in payload
    assert isinstance(payload["active_picks"], list)


# ────────────────────────────────────────────────────────────────────────
# B25 — identical-metrics bug regression tests
# ────────────────────────────────────────────────────────────────────────

@pytest.fixture
def three_ticker_watchlist(tmp_path):
    p = tmp_path / "wl3.json"
    p.write_text(json.dumps({
        "tickers": [
            {"symbol": "NVDA", "asset_class": "EQUITY"},
            {"symbol": "SOFI", "asset_class": "EQUITY"},
            {"symbol": "AMD",  "asset_class": "EQUITY"},
        ],
    }), encoding="utf-8")
    return p


def test_distinct_metrics_across_tickers(monkeypatch, three_ticker_watchlist, tmp_path):
    """If the LLM returns distinct per-ticker values, all picks differ. Regression guard."""
    monkeypatch.setenv(tae.ENV_FLAG, "1")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "k")

    # Each ticker gets a uniquely-calibrated response (what a well-behaved LLM does).
    _RESPONSES = {
        "NVDA": {"action": "BUY", "confidence": 0.91, "target_pct": 14.5, "stop_pct": 6.2,
                 "thesis": "NVDA AI data-centre backlog driven", "rationale": "Beat-raise, PT raised",
                 "time_horizon_days": 30, "key_risks": ["valuation"]},
        "SOFI": {"action": "BUY", "confidence": 0.72, "target_pct": 8.3, "stop_pct": 4.7,
                 "thesis": "SOFI student-loan rebound", "rationale": "NIM expansion thesis",
                 "time_horizon_days": 21, "key_risks": ["rate risk"]},
        "AMD":  {"action": "BUY", "confidence": 0.79, "target_pct": 11.1, "stop_pct": 5.5,
                 "thesis": "AMD server GPU share gain", "rationale": "MI300X ramp",
                 "time_horizon_days": 21, "key_risks": ["execution"]},
    }

    def stub(url, headers, body):
        ticker = json.loads(body)["messages"][1]["content"].split("Ticker: ")[1].split("\n")[0]
        return _oai_response(json.dumps(_RESPONSES[ticker]))

    out_path = tmp_path / "out.json"
    summary = tae.emit_picks(watchlist_path=three_ticker_watchlist, output_path=out_path, http_post=stub)

    assert summary["emitted"] == 3
    picks = json.loads(out_path.read_text())["active_picks"]
    tuples = [(round(p["confidence"], 2), round(p["take_profit_pct"], 1), round(p["stop_loss_pct"], 1))
              for p in picks]
    # All 3 tuples must be distinct — no two tickers should collapse to the same metrics.
    assert len(set(tuples)) == 3, f"Expected 3 distinct metric tuples; got: {tuples}"


def test_identical_metrics_logs_warning(monkeypatch, three_ticker_watchlist, tmp_path, caplog):
    """When LLM returns identical metrics for 2+ tickers, a WARNING is logged."""
    import logging
    monkeypatch.setenv(tae.ENV_FLAG, "1")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "k")

    # All 3 tickers get the same conf/TP/SL — the B25 bug scenario.
    def stub(url, headers, body):
        return _oai_response(json.dumps({
            "action": "BUY", "confidence": 0.86,
            "thesis": "Nvidia Jensen real thesis", "rationale": "Real rationale here beat-raise",
            "time_horizon_days": 21, "target_pct": 12.0, "stop_pct": 5.0,
            "key_risks": ["valuation"],
        }))

    out_path = tmp_path / "out.json"
    with caplog.at_level(logging.WARNING, logger="alpha_engine.tradingagents_emitter"):
        tae.emit_picks(watchlist_path=three_ticker_watchlist, output_path=out_path, http_post=stub)

    assert any("identical" in record.message.lower() for record in caplog.records), (
        "Expected WARNING about identical metrics, got: " + str([r.message for r in caplog.records])
    )


def test_prompt_hardening_line_present():
    """The SYSTEM_PROMPT must contain the anti-default numeric instruction added in B25."""
    assert "identical metrics" in tae.SYSTEM_PROMPT.lower() or \
           "round defaults" in tae.SYSTEM_PROMPT.lower(), (
        "B25 anti-default prompt instruction missing from SYSTEM_PROMPT"
    )


def test_debug_raw_env_var_defined():
    """ENV_DEBUG_RAW constant must be present for the debug logging path."""
    assert hasattr(tae, "ENV_DEBUG_RAW"), "ENV_DEBUG_RAW constant missing from emitter"
    assert tae.ENV_DEBUG_RAW == "TRADINGAGENTS_DEBUG_RAW"


# ────────────────────────────────────────────────────────────────────────
# Multi-asset prompt builder (env-gated output-hygiene shadow)
#
# These tests cover alpha_engine/prompts/build_system_prompt and the
# emitter's _resolve_system_prompt wiring. The flag defaults OFF, so the
# default-OFF assertions are the contract that protects production.
# ────────────────────────────────────────────────────────────────────────

def test_multiasset_flag_defaults_off():
    """With no env flag set, _resolve_system_prompt returns the unchanged
    hardcoded equity SYSTEM_PROMPT — production behavior is identical."""
    assert tae._multiasset_enabled() is False
    for ac in ("EQUITY", "CRYPTO", "FOREX", "COMMODITY", "ETF", "BOND"):
        assert tae._resolve_system_prompt(ac) == tae.SYSTEM_PROMPT


def test_build_system_prompt_per_class_is_class_appropriate():
    """build_system_prompt returns a prompt whose annex matches the asset
    class — a CRYPTO prompt mentions funding, a BOND prompt mentions duration."""
    from alpha_engine.prompts import build_system_prompt, supported_asset_classes

    expectations = {
        "CRYPTO": ("funding", "liquidation"),
        "EQUITY": ("earnings",),
        "FOREX": ("session", "swap"),
        "COMMODITY": ("cot", "roll"),
        "FUTURES": ("roll", "expiry"),
        "ETF": ("tracking error", "liquidity"),
        "BOND": ("duration", "yield-curve"),
    }
    for ac in supported_asset_classes():
        prompt = build_system_prompt(ac)
        assert prompt.strip(), f"{ac} prompt is empty"
        # Strict-JSON framing is always prepended.
        assert prompt.startswith("STRICT MODE")
        # Base committee rules are always present.
        assert "decision committee" in prompt.lower()
        assert '"action"' in prompt
        # Class-specific annex markers.
        low = prompt.lower()
        assert any(tok in low for tok in expectations[ac]), (
            f"{ac} prompt missing expected annex tokens {expectations[ac]}"
        )


def test_build_system_prompt_distinguishes_crypto_from_equity():
    """A crypto pick must not get equity-desk framing and vice versa."""
    from alpha_engine.prompts import build_system_prompt

    crypto = build_system_prompt("CRYPTO")
    equity = build_system_prompt("EQUITY")
    assert crypto != equity
    assert "funding" in crypto.lower()
    assert "funding" not in equity.lower() or "earnings" in equity.lower()
    assert "earnings" in equity.lower()


def test_build_system_prompt_unknown_class_falls_back_to_equity():
    """Unknown / empty asset classes resolve to the EQUITY annex rather
    than erroring — never worse than today's single-prompt baseline."""
    from alpha_engine.prompts import build_system_prompt

    equity = build_system_prompt("EQUITY")
    assert build_system_prompt("WIDGETS") == equity
    assert build_system_prompt("") == equity
    assert build_system_prompt(None) == equity


def test_resolve_system_prompt_uses_builder_when_flag_on(monkeypatch):
    """With the flag ON, _resolve_system_prompt returns the multi-asset
    prompt (different from the hardcoded equity SYSTEM_PROMPT for crypto)."""
    monkeypatch.setenv(tae.ENV_MULTIASSET_PROMPT, "1")
    assert tae._multiasset_enabled() is True
    crypto_prompt = tae._resolve_system_prompt("CRYPTO")
    assert crypto_prompt != tae.SYSTEM_PROMPT
    assert "funding" in crypto_prompt.lower()


def test_resolve_system_prompt_fails_safe_to_hardcoded(monkeypatch):
    """If build_system_prompt raises, _resolve_system_prompt must fall back
    to the hardcoded SYSTEM_PROMPT — the emitter never crashes on a
    packaging error."""
    monkeypatch.setenv(tae.ENV_MULTIASSET_PROMPT, "1")
    import alpha_engine.prompts as prompts_mod

    def _boom(_ac):
        raise FileNotFoundError("simulated missing prompt asset")

    monkeypatch.setattr(prompts_mod, "build_system_prompt", _boom)
    assert tae._resolve_system_prompt("CRYPTO") == tae.SYSTEM_PROMPT


def test_emit_picks_unchanged_with_flag_on(monkeypatch, small_watchlist, tmp_path):
    """Smoke: with the multi-asset flag ON, emit_picks still produces a
    schema-compatible payload (the JSON schema is unchanged — hygiene only)."""
    monkeypatch.setenv(tae.ENV_FLAG, "1")
    monkeypatch.setenv(tae.ENV_MULTIASSET_PROMPT, "1")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "k")

    def stub(*_a, **_kw):
        return _oai_response(json.dumps({
            "action": "BUY", "confidence": 0.8,
            "thesis": "real per-ticker thesis", "rationale": "real rationale here",
            "time_horizon_days": 21, "target_pct": 10.0, "stop_pct": 5.0,
        }))

    out_path = tmp_path / "out.json"
    summary = tae.emit_picks(
        watchlist_path=small_watchlist, output_path=out_path, http_post=stub,
    )
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert summary["emitted"] == 2
    assert "active_picks" in payload
    # Schema keys unchanged — no evidence_fields / data_gaps / regime_tag.
    pick = payload["active_picks"][0]
    for forbidden in ("evidence_fields", "data_gaps", "regime_tag", "disagreement_score"):
        assert forbidden not in pick, f"out-of-scope field {forbidden!r} leaked into pick schema"
