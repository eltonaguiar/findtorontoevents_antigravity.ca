from alpha_engine.kelly_position_sizer import compute_position_size


def _pick(dd):
    return {
        "symbol": "ETHUSDT",
        "strategy": "s1",
        "entry_price": 100.0,
        "stop_loss": 97.0,
        "extra": {"atr_pct": 0.03, "rolling_dd_30d": dd},
    }


def _stats():
    return {"win_rate": 0.6, "avg_win_pct": 0.05, "avg_loss_pct": 0.03}


def test_dd_halt_triggers_when_enabled(monkeypatch):
    monkeypatch.setenv("KELLY_DD_HALT_ENABLED", "1")
    monkeypatch.setenv("KELLY_DD_HALT_MAX", "0.30")
    p = _pick(0.35)
    size = compute_position_size(p, _stats(), active_picks=[], portfolio_value=10000)
    assert size == 0.0
    assert p["dd_halt_triggered"] is True


def test_dd_halt_respects_disabled_flag(monkeypatch):
    monkeypatch.setenv("KELLY_DD_HALT_ENABLED", "0")
    p = _pick(0.60)
    size = compute_position_size(p, _stats(), active_picks=[], portfolio_value=10000)
    assert size >= 50.0
    assert "dd_halt_triggered" not in p


def test_dd_halt_recovery_when_drawdown_below_threshold(monkeypatch):
    monkeypatch.setenv("KELLY_DD_HALT_ENABLED", "1")
    monkeypatch.setenv("KELLY_DD_HALT_MAX", "0.30")
    p = _pick(0.12)
    size = compute_position_size(p, _stats(), active_picks=[], portfolio_value=10000)
    assert size >= 50.0
    assert "dd_halt_triggered" not in p


def test_hyro_overlay_caps_size_when_enabled(monkeypatch):
    monkeypatch.setenv("HYRO_RISK_SIZER_ENABLED", "1")
    monkeypatch.setenv("HYRO_TARGET_RISK_PCT", "0.25")
    monkeypatch.setenv("HYRO_TODAY_PNL_PCT", "0.0")
    p = _pick(0.10)
    p["direction"] = "LONG"
    p["risk_reward"] = 2.5
    size = compute_position_size(p, _stats(), active_picks=[], portfolio_value=10000)
    assert size > 0
    assert "hyro_size_usd" in p
    assert size <= p["hyro_size_usd"]


def test_hyro_overlay_can_reject_on_daily_soft_stop(monkeypatch):
    monkeypatch.setenv("HYRO_RISK_SIZER_ENABLED", "1")
    monkeypatch.setenv("HYRO_TODAY_PNL_PCT", "-3.0")
    p = _pick(0.10)
    p["direction"] = "LONG"
    p["risk_reward"] = 2.5
    size = compute_position_size(p, _stats(), active_picks=[], portfolio_value=10000)
    assert size == 0.0
    assert "hyro_reject_reasons" in p


# ---------------------------------------------------------------------------
# Wave 2 safety: graceful degradation under bad env / failed Hyro overlay.
# ---------------------------------------------------------------------------

def test_hyro_overlay_falls_back_to_legacy_size_on_import_failure(monkeypatch):
    """If the Hyro overlay module fails to import, sizing must fall back to the
    legacy Kelly size — not crash, not silently zero out, not annotate the pick
    with Hyro fields.

    Implementation note: `_apply_hyro_risk_sizer` lazily imports
    `tools.hyrotrader_risk_sizer.size_pick` inside a try/except, so we simulate
    a broken module by injecting a sentinel into `sys.modules` that raises on
    attribute access — `from X import size_pick` then re-raises ImportError.
    """
    import sys

    monkeypatch.setenv("HYRO_RISK_SIZER_ENABLED", "1")
    monkeypatch.setenv("HYRO_TARGET_RISK_PCT", "0.25")
    monkeypatch.setenv("HYRO_TODAY_PNL_PCT", "0.0")

    class _BoomModule:
        def __getattr__(self, name):
            raise ImportError(f"synthetic import block for {name}")

    monkeypatch.setitem(sys.modules, "tools.hyrotrader_risk_sizer", _BoomModule())

    p = _pick(0.10)
    p["direction"] = "LONG"
    p["risk_reward"] = 2.5
    size = compute_position_size(p, _stats(), active_picks=[], portfolio_value=10000)

    assert size > 0, "should fall back to legacy Kelly size, not zero out"
    assert "hyro_size_usd" not in p, "no Hyro annotations when overlay unavailable"
    assert "hyro_reject_reasons" not in p


def test_hyro_overlay_falls_back_to_legacy_size_on_runtime_exception(monkeypatch):
    """Bug 2 regression: runtime errors inside size_pick must not propagate.

    On exception, _apply_hyro_risk_sizer must return the legacy sized_usd
    without mutating the pick (no hyro_size_usd, no hyro_reject_reasons).
    """
    monkeypatch.setenv("HYRO_RISK_SIZER_ENABLED", "1")

    import tools.hyrotrader_risk_sizer as risk_mod

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated")

    monkeypatch.setattr(risk_mod, "size_pick", _boom)

    p = _pick(0.10)
    p["direction"] = "LONG"
    p["risk_reward"] = 2.5
    size = compute_position_size(p, _stats(), active_picks=[], portfolio_value=10000)

    assert size > 0
    assert "hyro_size_usd" not in p
    assert "hyro_reject_reasons" not in p


def test_invalid_kelly_dd_halt_max_env_falls_back_to_default(monkeypatch):
    """Garbage `KELLY_DD_HALT_MAX` (e.g. 'abc') must not crash sizing — the
    parser falls back to the documented default (0.30) and a 35% drawdown
    still triggers the halt.
    """
    monkeypatch.setenv("KELLY_DD_HALT_ENABLED", "1")
    monkeypatch.setenv("KELLY_DD_HALT_MAX", "abc")
    p = _pick(0.35)  # above the default 0.30 threshold
    size = compute_position_size(p, _stats(), active_picks=[], portfolio_value=10000)
    assert size == 0.0
    assert p.get("dd_halt_triggered") is True


def test_empty_kelly_dd_halt_max_env_falls_back_to_default(monkeypatch):
    """Empty-string `KELLY_DD_HALT_MAX` must not crash; default 0.30 applies.

    A 0.10 drawdown is below 0.30, so the halt should NOT fire and we should
    receive a normal Kelly-sized position.
    """
    monkeypatch.setenv("KELLY_DD_HALT_ENABLED", "1")
    monkeypatch.setenv("KELLY_DD_HALT_MAX", "")
    p = _pick(0.10)
    size = compute_position_size(p, _stats(), active_picks=[], portfolio_value=10000)
    assert size >= 50.0
    assert "dd_halt_triggered" not in p


def test_negative_kelly_dd_halt_max_env_clamps_safely(monkeypatch):
    """Negative `KELLY_DD_HALT_MAX` must not crash and must be clamped to a
    safe positive value (the parser clamps to [0.01, 0.95]).

    With the threshold clamped to ~0.01, even a tiny 0.05 drawdown should
    trigger the halt — proving the clamp is active rather than ignoring the
    negative value entirely.
    """
    monkeypatch.setenv("KELLY_DD_HALT_ENABLED", "1")
    monkeypatch.setenv("KELLY_DD_HALT_MAX", "-1.0")
    p = _pick(0.05)
    size = compute_position_size(p, _stats(), active_picks=[], portfolio_value=10000)
    assert size == 0.0
    assert p.get("dd_halt_triggered") is True


# ---------------------------------------------------------------------------
# Wave 2.2 visibility: silent fallbacks must surface as WARNING-level logs
# so ops can see Hyro overlay failures in production (debug is suppressed).
# ---------------------------------------------------------------------------

def test_hyro_runtime_exception_emits_warning(monkeypatch, caplog):
    """When `size_pick` raises at runtime, the fallback must emit a WARNING
    so ops sees the Hyro overlay is silently degrading to legacy Kelly."""
    import logging

    monkeypatch.setenv("HYRO_RISK_SIZER_ENABLED", "1")

    import tools.hyrotrader_risk_sizer as risk_mod

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated runtime failure")

    monkeypatch.setattr(risk_mod, "size_pick", _boom)

    caplog.set_level(logging.WARNING, logger="alpha_engine.kelly_position_sizer")

    p = _pick(0.10)
    p["direction"] = "LONG"
    p["risk_reward"] = 2.5
    size = compute_position_size(p, _stats(), active_picks=[], portfolio_value=10000)

    assert size > 0
    warnings = [
        r for r in caplog.records
        if r.name == "alpha_engine.kelly_position_sizer" and r.levelno >= logging.WARNING
    ]
    assert warnings, "expected a WARNING log on Hyro size_pick runtime failure"
    msg = warnings[-1].getMessage()
    assert "Hyro" in msg
    assert "fallback" in msg.lower() or "falling back" in msg.lower()
    assert "size_pick" in msg or "RuntimeError" in msg


def test_hyro_import_failure_emits_warning(monkeypatch, caplog):
    """When the lazy `from tools.hyrotrader_risk_sizer import size_pick`
    fails (module unavailable), the fallback must emit a WARNING — not be
    silent — so ops sees the overlay is unavailable in production."""
    import logging
    import sys

    monkeypatch.setenv("HYRO_RISK_SIZER_ENABLED", "1")
    monkeypatch.setenv("HYRO_TARGET_RISK_PCT", "0.25")
    monkeypatch.setenv("HYRO_TODAY_PNL_PCT", "0.0")

    class _BoomModule:
        def __getattr__(self, name):
            raise ImportError(f"synthetic import block for {name}")

    monkeypatch.setitem(sys.modules, "tools.hyrotrader_risk_sizer", _BoomModule())

    caplog.set_level(logging.WARNING, logger="alpha_engine.kelly_position_sizer")

    p = _pick(0.10)
    p["direction"] = "LONG"
    p["risk_reward"] = 2.5
    size = compute_position_size(p, _stats(), active_picks=[], portfolio_value=10000)

    assert size > 0, "should fall back to legacy Kelly size, not zero out"
    warnings = [
        r for r in caplog.records
        if r.name == "alpha_engine.kelly_position_sizer" and r.levelno >= logging.WARNING
    ]
    assert warnings, "expected a WARNING log on Hyro import failure"
    msg = warnings[-1].getMessage()
    assert "Hyro" in msg
    assert "fallback" in msg.lower() or "falling back" in msg.lower()
    assert "import" in msg.lower() or "ImportError" in msg
