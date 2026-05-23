from __future__ import annotations

from audit_trail import universal_pick_resolver


def test_snapshot_prediction_market_entry_populates_long_levels() -> None:
    pick = {
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "entry_price": 0.0,
        "take_profit": 0.0,
        "stop_loss": 0.0,
        "strategy": "pm_momentum_detector",
        "source_system": "pm_momentum_signals",
    }

    snapped = universal_pick_resolver._snapshot_prediction_market_entry(pick, 68000.0)

    assert snapped is True
    assert pick["entry_price"] == 68000.0
    assert pick["take_profit"] == 69700.0
    assert pick["stop_loss"] == 66980.0


def test_is_prediction_market_pick_detects_kalshi_rows() -> None:
    pick = {
        "strategy": "kalshi_mtf_consensus",
        "source_system": "pm_kalshi_signals",
    }

    assert universal_pick_resolver._is_prediction_market_pick("pm_kalshi_signals", pick) is True


def test_extract_pick_fields_populates_asset_class() -> None:
    """Every resolved pick must carry asset_class so direct readers of
    universal_resolved_picks.json (forensic tools, copytrader_verification,
    edge analysis scripts) don't see a missing-field 'unknown' state."""
    crypto_raw = {
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "entry_price": 60000.0,
        "take_profit": 61800.0,
        "stop_loss": 59100.0,
        "timestamp": "2026-04-28T00:00:00Z",
        "strategy": "ml_crypto",
    }
    pick = universal_pick_resolver._extract_pick_fields(crypto_raw, "ml_crypto_pred")
    assert pick["asset_class"] == "crypto"

    equity_raw = {
        "symbol": "AAPL",
        "direction": "LONG",
        "entry_price": 200.0,
        "take_profit": 206.0,
        "stop_loss": 197.0,
        "timestamp": "2026-04-28T00:00:00Z",
        "strategy": "stocks_consensus",
    }
    pick = universal_pick_resolver._extract_pick_fields(equity_raw, "goldmine_stocks")
    assert pick["asset_class"] == "equity"

    forex_raw = {
        "symbol": "EURUSD=X",
        "direction": "SHORT",
        "entry_price": 1.08,
        "take_profit": 1.07,
        "stop_loss": 1.085,
        "timestamp": "2026-04-28T00:00:00Z",
        "strategy": "fx_consensus",
    }
    pick = universal_pick_resolver._extract_pick_fields(forex_raw, "stocks_forex_comp")
    assert pick["asset_class"] == "forex"


def test_max_hold_hours_per_asset_class() -> None:
    """CLAUDE_DEBUGGING_GUIDE.MD Step 7: forex/bond need longer windows."""
    assert universal_pick_resolver._max_hold_hours_for({"asset_class": "CRYPTO"}) == 48
    assert universal_pick_resolver._max_hold_hours_for({"asset_class": "FOREX"}) == 120
    assert universal_pick_resolver._max_hold_hours_for({"asset_class": "BOND"}) == 120
    assert universal_pick_resolver._max_hold_hours_for({"asset_class": "COMMODITY"}) == 96
    assert universal_pick_resolver._max_hold_hours_for({"asset_class": "ETF"}) == 96
    # 2026-05-04 (post-fix at f696316aced): unknown asset_class now routes
    # through normalize_asset_class which defaults to "equity" → 96h. The
    # prior 48h legacy fallback only fired because normalize was being
    # called with the wrong arg type and silently failing. Behaviour
    # improvement, not regression. CI on main was failing prior to this
    # update because the fix landed in main without updating this assertion.
    assert universal_pick_resolver._max_hold_hours_for({"asset_class": "WEIRD"}) == 96
    # Empty pick: normalize_asset_class still defaults to "equity" (96h).
    assert universal_pick_resolver._max_hold_hours_for({}) == 96


def test_max_hold_hours_normalizes_aliases() -> None:
    """2026-05-04 regression: PR #745 passed a string to normalize_asset_class,
    which expects a dict; AttributeError was silently swallowed. PR f696316aced
    fixed the resolver but didn't add aliased-input tests. This pins the fix.
    """
    # Lowercase canonical name should resolve via normalize_asset_class.
    assert universal_pick_resolver._max_hold_hours_for({"asset_class": "forex"}) == 120
    assert universal_pick_resolver._max_hold_hours_for({"asset_class": "bond"}) == 120
    # Symbol-driven detection: =X suffix → forex, =F → futures (96h).
    assert universal_pick_resolver._max_hold_hours_for({"symbol": "EURUSD=X"}) == 120
    assert universal_pick_resolver._max_hold_hours_for({"symbol": "CL=F"}) == 96
    # 6-char forex pair detected without explicit asset_class.
    assert universal_pick_resolver._max_hold_hours_for({"symbol": "EURUSD"}) == 120
    # Stablecoin → crypto (48h).
    assert universal_pick_resolver._max_hold_hours_for({"symbol": "BTCUSDT"}) == 48
