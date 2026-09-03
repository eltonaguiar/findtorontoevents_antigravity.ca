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
    assert universal_pick_resolver._max_hold_hours_for({"asset_class": "FOREX"}) == 72  # EAGLE2 2026-06-02: unified 120 -> 72
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
    assert universal_pick_resolver._max_hold_hours_for({"asset_class": "forex"}) == 72  # EAGLE2 unified
    assert universal_pick_resolver._max_hold_hours_for({"asset_class": "bond"}) == 120
    # Symbol-driven detection: =X suffix → forex, =F → futures (96h).
    assert universal_pick_resolver._max_hold_hours_for({"symbol": "EURUSD=X"}) == 72  # EAGLE2 unified
    assert universal_pick_resolver._max_hold_hours_for({"symbol": "CL=F"}) == 96
    # 6-char forex pair detected without explicit asset_class.
    assert universal_pick_resolver._max_hold_hours_for({"symbol": "EURUSD"}) == 72  # EAGLE2 unified
    # Stablecoin → crypto (48h).
    assert universal_pick_resolver._max_hold_hours_for({"symbol": "BTCUSDT"}) == 48


# ─────────────────────────────────────────────────────────────────────────────
# B1 (Backfill Price Guard, 2026-06-24) — per-class exit-price plausibility
# ─────────────────────────────────────────────────────────────────────────────

def test_b1_per_class_dict_has_all_required_keys() -> None:
    """B1: every asset class the system writes must have a configured ratio."""
    d = universal_pick_resolver.MAX_EXIT_RATIO_DEVIATION_BY_CLASS
    for k in ("CRYPTO", "EQUITY", "ETF", "COMMODITY", "FUTURES", "FOREX", "BOND"):
        assert k in d, f"missing key {k} in MAX_EXIT_RATIO_DEVIATION_BY_CLASS"
        v = d[k]
        assert 0 < v <= 1.0, f"{k} ratio {v} out of (0, 1] range"
    # FX and BOND tightened below the user-spec 0.50 default because corrupt
    # cases from June 11 (AUDUSD +93,965%, SOFI +2,280%) would otherwise pass
    # through with the loose 0.50 default for high-vol classes only.
    assert d["FOREX"] < universal_pick_resolver._MAX_EXIT_RATIO_DEVIATION_DEFAULT
    assert d["BOND"] < universal_pick_resolver._MAX_EXIT_RATIO_DEVIATION_DEFAULT


def test_b1_forex_audusd_cents_bug_quarantined() -> None:
    """B1: AUDUSD=X exit 0.70 -> 663.13 (June 11 bug); ratio = 947x; FX 12% bound.

    EXPECT: _exit_price_is_plausible returns False; sidecar receives the row.
    """
    pick = {
        "symbol": "AUDUSD=X",
        "direction": "LONG",
        "entry_price": 0.70,
        "exit_price": 663.13,
        "asset_class": "FOREX",
        "source_system": "goldmine_unified",
    }
    assert universal_pick_resolver._exit_price_is_plausible(
        pick, exit_price=663.13, system_name="goldmine_unified"
    ) is False
    # exact known June 11 bug - guard catches it


def test_b1_equity_sofi_split_skew_quarantined() -> None:
    """B1: SOFI exit 16.03 -> 381.67 (June 11 split-stale); ratio = 23.8x; EQUITY 50% bound."""
    pick = {
        "symbol": "SOFI",
        "direction": "LONG",
        "entry_price": 16.03,
        "exit_price": 381.67,
        "asset_class": "EQUITY",
        "source_system": "goldmine_stocks",
    }
    assert universal_pick_resolver._exit_price_is_plausible(
        pick, exit_price=381.67, system_name="goldmine_stocks"
    ) is False


def test_b1_crypto_normal_volatility_passes() -> None:
    """B1: SOLUSDT exit 100 -> 145 (legit +45%); ratio 1.45; CRYPTO 50% bound."""
    pick = {
        "symbol": "SOLUSDT",
        "direction": "LONG",
        "entry_price": 100.0,
        "exit_price": 145.0,
        "asset_class": "CRYPTO",
        "source_system": "alpha_engine",
    }
    assert universal_pick_resolver._exit_price_is_plausible(
        pick, exit_price=145.0, system_name="alpha_engine"
    ) is True


def test_b1_short_legit_loss_magnitude_passes() -> None:
    """B1: FUTURES SHORT entry 4000 -> exit 5800 (legit -45% loss).

    Magnitude check is symmetric; SHORT loss direction doesn't get special-cased.
    """
    pick = {
        "symbol": "ES=F",
        "direction": "SHORT",
        "entry_price": 4000.0,
        "exit_price": 5800.0,
        "asset_class": "FUTURES",
        "source_system": "alpha_engine",
    }
    # ratio = 1.45, abs(1.45-1) = 0.45, FUTURES bound = 0.50 -> passes
    assert universal_pick_resolver._exit_price_is_plausible(
        pick, exit_price=5800.0, system_name="alpha_engine"
    ) is True


def test_b1_bypass_no_entry_or_pm_or_zero_exit() -> None:
    """B1: missing entry_price / no exit_price / PM pick all BYPASS the guard.

    Otherwise legitimate pre-entry TIME_EXITs and PM-share picks would be
    quarantined for nothing.
    """
    # (a) no entry
    pick_no_entry = {
        "symbol": "EURUSD=X",
        "entry_price": 0.0,
        "exit_price": 1.085,
        "asset_class": "FOREX",
        "source_system": "fx_consensus",
    }
    assert universal_pick_resolver._exit_price_is_plausible(
        pick_no_entry, exit_price=1.085, system_name="fx_consensus"
    ) is True
    # (b) no exit / negative exit
    pick_no_exit = {
        "symbol": "AAPL",
        "entry_price": 200.0,
        "exit_price": 0.0,
        "asset_class": "EQUITY",
        "source_system": "goldmine_stocks",
    }
    assert universal_pick_resolver._exit_price_is_plausible(
        pick_no_exit, exit_price=0.0, system_name="goldmine_stocks"
    ) is True
    # (c) PM pick (system_name-based detection)
    pick_pm = {
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "entry_price": 60000.0,
        "exit_price": 99.0,  # clearly absurd, but PM should bypass
        "asset_class": "CRYPTO",
        # PM skipper identifies by system_name then strategy; we set strategy too.
        "strategy": "kalshi_mtf_consensus",
        "source_system": "pm_kalshi_signals",
    }
    assert universal_pick_resolver._exit_price_is_plausible(
        pick_pm, exit_price=99.0, system_name="pm_kalshi_signals"
    ) is True


def test_b1_unknown_asset_class_falls_back_to_50_percent() -> None:
    """B1: unknown / missing asset_class uses _MAX_EXIT_RATIO_DEVIATION_DEFAULT (50%)."""
    pick = {
        "symbol": "XYZABC",
        "entry_price": 100.0,
        "exit_price": 145.0,  # +45% — within 50% fallback -> plausible
        "asset_class": "UNKNOWN",
        "source_system": "alpha_engine",
    }
    assert universal_pick_resolver._exit_price_is_plausible(
        pick, exit_price=145.0, system_name="alpha_engine"
    ) is True
    # but +80% would fail
    pick_bad = {**pick, "exit_price": 180.0}
    assert universal_pick_resolver._exit_price_is_plausible(
        pick_bad, exit_price=180.0, system_name="alpha_engine"
    ) is False


def test_b1_quarantine_sidecar_round_trip(tmp_path, monkeypatch) -> None:
    """B1: _write_to_quarantine_sidecar persists and is idempotent across calls."""
    import json
    fake_qfile = tmp_path / "quarantine_implausible_exits.json"
    # redirect ROOT/_QUARANTINE_FILE path
    monkeypatch.setattr(universal_pick_resolver, "_QUARANTINE_FILE", fake_qfile)
    # Also patch the resolved-attribute lookup; helper reads via the module attr
    # directly so this works.

    sample = {
        "id": "abc123",
        "resolved_at": "2026-06-24T15:00:00Z",
        "symbol": "AUDUSD=X",
        "exit_price": 663.13,
        "entry_price": 0.70,
        "asset_class": "FOREX",
        "exit_reason": "price_plausibility_fail",
        "status": "QUARANTINED",
        "pnl_pct": "NO_DATA",
    }
    universal_pick_resolver._write_to_quarantine_sidecar(sample)
    data = json.loads(fake_qfile.read_text())
    assert isinstance(data, list) and len(data) == 1
    assert data[0]["id"] == "abc123"

    # Idempotent: same (id, resolved_at) -> still 1 row
    universal_pick_resolver._write_to_quarantine_sidecar(sample)
    data = json.loads(fake_qfile.read_text())
    assert len(data) == 1

    # Different resolved_at -> 2 rows
    sample2 = {**sample, "resolved_at": "2026-06-24T15:05:00Z"}
    universal_pick_resolver._write_to_quarantine_sidecar(sample2)
    data = json.loads(fake_qfile.read_text())
    assert len(data) == 2


def test_b1_nan_entry_or_exit_quarantines() -> None:
    """B1: NaN input should NOT enter WR/PF averages; must be quarantined.

    Reason: corrupt tape feeds occasionally arrive with float('nan') once the
    upstream feed corrupts (e.g. divide-by-zero in yfinance tape).  Pinning
    that the guard correctly classifies as IMPLAUSIBLE prevents future
    refactors from regressing into NaN propagation into pnl-clamp.
    """
    pick = {
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "entry_price": float("nan"),
        "exit_price": 70000.0,
        "asset_class": "CRYPTO",
        "source_system": "alpha_engine",
    }
    assert universal_pick_resolver._exit_price_is_plausible(
        pick, exit_price=70000.0, system_name="alpha_engine"
    ) is False


def test_b1_bond_with_zero_entry_bypasses() -> None:
    """B1: asset_class="BOND" + entry_price=0.0 still BYPASSES (entry<=0 short-circuit).

    Documents that the unknown-class fallback only fires AFTER the entry/exit/PM
    bypass short-circuits, so zero-entry picks are never misclassified by their
    literal asset_class label.
    """
    pick = {
        "symbol": "SHY",
        "direction": "LONG",
        "entry_price": 0.0,
        "exit_price": 81.5,  # would be 8150% off vs 1.00 -- clearly absurd; not relevant
        "asset_class": "BOND",  # specifically make sure BOND label doesn't trigger guard
        "source_system": "alpha_engine",
    }
    assert universal_pick_resolver._exit_price_is_plausible(
        pick, exit_price=81.5, system_name="alpha_engine"
    ) is True
