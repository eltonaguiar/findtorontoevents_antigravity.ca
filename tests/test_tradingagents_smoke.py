"""End-to-end smoke tests for the TradingAgents pipeline.

Gated on TRADINGAGENTS_LIVE_SMOKE=1.  These tests make REAL LLM calls
and exercise the full emitter → output path.  Not run in normal CI.

To run:
    TRADINGAGENTS_EMITTER_ENABLED=1 TRADINGAGENTS_LIVE_SMOKE=1 \\
    DEEPSEEK_API_KEY=<key> pytest tests/test_tradingagents_smoke.py -v -s

Assertions (§6.6 B26 spec):
  1. thesis / rationale are not placeholder strings  (B24 regression)
  2. ≥2 of 3 tickers have distinct (confidence, TP, SL)  (B25 regression)
  3. TRADINGAGENTS_DEBUG_RAW=1 surfaces raw LLM response in debug logs
  4. tradingagents source is registered in SYSTEM_SOURCES (resolver)
     + entry_price fill path is exercised  [xfail until resolver helper lands]
"""
import contextlib
import json
import logging as _log
import os

import pytest

_SMOKE_FLAG = "TRADINGAGENTS_LIVE_SMOKE"

pytestmark = pytest.mark.skipif(
    os.environ.get(_SMOKE_FLAG, "0").strip().lower() not in ("1", "true"),
    reason=f"Set {_SMOKE_FLAG}=1 to run live TradingAgents smoke tests",
)

_MINI_WATCHLIST = {
    "tickers": [
        {"symbol": "NVDA", "asset_class": "EQUITY"},
        {"symbol": "SOFI", "asset_class": "EQUITY"},
        {"symbol": "AMD",  "asset_class": "EQUITY"},
    ]
}

_PLACEHOLDER_STRINGS = frozenset({"Thesis text", "Rationale text", "x", "y", ""})


@contextlib.contextmanager
def _capture_debug(logger_name: str):
    """Collect DEBUG+ records from a named logger without modifying test config."""

    class _Sink(_log.Handler):
        def __init__(self):
            super().__init__(_log.DEBUG)
            self.records: list[_log.LogRecord] = []

        def emit(self, record: _log.LogRecord) -> None:
            self.records.append(record)

    sink = _Sink()
    logger = _log.getLogger(logger_name)
    old_level = logger.level
    logger.setLevel(_log.DEBUG)
    logger.addHandler(sink)
    try:
        yield sink.records
    finally:
        logger.removeHandler(sink)
        logger.setLevel(old_level)


@pytest.fixture(scope="module", autouse=True)
def require_api_key():
    if not any(
        os.environ.get(k)
        for k in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "XAI_API_KEY")
    ):
        pytest.skip(
            "No LLM API key (DEEPSEEK_API_KEY / OPENAI_API_KEY / XAI_API_KEY)"
        )


@pytest.fixture(scope="module")
def smoke_picks(tmp_path_factory):
    """Emit picks once against the mini watchlist; share result across tests."""
    import alpha_engine.tradingagents_emitter as tae

    wl = tmp_path_factory.mktemp("smoke") / "mini_wl.json"
    wl.write_text(json.dumps(_MINI_WATCHLIST), encoding="utf-8")
    out = tmp_path_factory.mktemp("smoke") / "picks.json"

    old_flag = os.environ.get(tae.ENV_FLAG)
    os.environ[tae.ENV_FLAG] = "1"
    try:
        summary = tae.emit_picks(watchlist_path=wl, output_path=out)
    finally:
        if old_flag is None:
            os.environ.pop(tae.ENV_FLAG, None)
        else:
            os.environ[tae.ENV_FLAG] = old_flag

    picks = json.loads(out.read_text(encoding="utf-8")).get("active_picks", [])
    return {"summary": summary, "picks": picks, "path": out}


# ── 1. No placeholder text (B24 regression) ─────────────────────────────────

def test_no_placeholder_text(smoke_picks):
    picks = smoke_picks["picks"]
    if not picks:
        pytest.skip(f"No picks emitted; summary={smoke_picks['summary']}")
    for pick in picks:
        assert pick.get("thesis") not in _PLACEHOLDER_STRINGS, (
            f"Placeholder thesis on {pick.get('symbol')}: {pick.get('thesis')!r}"
        )
        assert pick.get("rationale") not in _PLACEHOLDER_STRINGS, (
            f"Placeholder rationale on {pick.get('symbol')}: {pick.get('rationale')!r}"
        )


# ── 2. Distinct metrics across tickers (B25 regression) ─────────────────────

def test_at_least_two_distinct_metrics(smoke_picks):
    picks = smoke_picks["picks"]
    if len(picks) < 2:
        pytest.skip(f"Only {len(picks)} picks emitted; need ≥2 for distinct-metric check")
    tuples = {
        (round(p["confidence"], 2), round(p["take_profit_pct"], 1), round(p["stop_loss_pct"], 1))
        for p in picks
    }
    assert len(tuples) >= 2, (
        f"Expected ≥2 distinct (conf, TP, SL) tuples across {len(picks)} picks; got: {tuples}"
    )


# ── 3. DEBUG_RAW env var logs raw LLM response ──────────────────────────────

def test_debug_raw_env_flag(tmp_path):
    """With TRADINGAGENTS_DEBUG_RAW=1, raw LLM response appears in debug logs."""
    import alpha_engine.tradingagents_emitter as tae

    assert hasattr(tae, "ENV_DEBUG_RAW"), "ENV_DEBUG_RAW constant missing from emitter"

    wl = tmp_path / "single.json"
    wl.write_text(
        json.dumps({"tickers": [{"symbol": "NVDA", "asset_class": "EQUITY"}]}),
        encoding="utf-8",
    )
    out = tmp_path / "picks.json"

    old_flag = os.environ.get(tae.ENV_FLAG)
    old_raw = os.environ.get(tae.ENV_DEBUG_RAW)
    os.environ[tae.ENV_FLAG] = "1"
    os.environ[tae.ENV_DEBUG_RAW] = "1"
    try:
        with _capture_debug("alpha_engine.tradingagents_emitter") as records:
            tae.emit_picks(watchlist_path=wl, output_path=out)
    finally:
        if old_flag is None:
            os.environ.pop(tae.ENV_FLAG, None)
        else:
            os.environ[tae.ENV_FLAG] = old_flag
        if old_raw is None:
            os.environ.pop(tae.ENV_DEBUG_RAW, None)
        else:
            os.environ[tae.ENV_DEBUG_RAW] = old_raw

    debug_msgs = [r.getMessage() for r in records if r.levelno == _log.DEBUG]
    assert any("raw LLM response" in m for m in debug_msgs), (
        f"Expected debug log with 'raw LLM response' for NVDA; got: {debug_msgs[:5]}"
    )


# ── 4a. tradingagents registered in resolver ────────────────────────────────

def test_tradingagents_registered_in_resolver():
    """tradingagents must appear in SYSTEM_SOURCES so the resolver tracks outcomes."""
    from audit_trail.universal_pick_resolver import SYSTEM_SOURCES

    names = [name for name, _path in SYSTEM_SOURCES]
    assert "tradingagents" in names, (
        "tradingagents missing from SYSTEM_SOURCES; TP/SL/TIME_EXIT outcomes "
        "will never be resolved.  Register it in universal_pick_resolver.py."
    )


# ── 4b. resolver entry-price snapshot (xfail until helper lands) ─────────────

@pytest.mark.xfail(
    strict=False,
    reason=(
        "_snapshot_tradingagents_entry() helper not yet in universal_pick_resolver.py. "
        "The emitter leaves entry_price=None; the resolver currently skips such picks "
        "(no_entry path at resolver.py:732-734).  Fix: add _TRADINGAGENTS_SYSTEMS set "
        "and _snapshot_tradingagents_entry() mirroring the prediction-market snapshot "
        "path (resolver.py:532-545)."
    ),
)
def test_resolver_fills_entry_price(smoke_picks):
    """After emit, entry_price should be non-None (emitter or resolver must fill it)."""
    picks = smoke_picks["picks"]
    if not picks:
        pytest.skip("No picks emitted")
    none_entry = [p.get("symbol") for p in picks if p.get("entry_price") is None]
    assert not none_entry, (
        f"entry_price is None on {none_entry} — resolver entry-snapshot path not "
        "implemented for tradingagents source_system."
    )
