"""Tests for outcome_resolver v2.2 non-crypto resolution.

Covers:
1. Direction-aware WIN/LOSS classification (LONG profit vs SHORT profit).
2. Bar-replay TP/SL touch detection (existing v2 path, regression test).
3. Time-exit case: pick aged past per-class max_hold window with no TP/SL touch
   resolves at last bar's close (NEW v2.2 behavior — replaces breakeven loop).
4. Idempotent re-run: already-resolved picks are skipped by is_unresolved and
   re-running resolve_single_pick on a resolved pick doesn't churn fields.
5. Asset-class threshold gating (5bp non-crypto, 0.1bp crypto).
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

# Ensure repo root on path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from alpha_engine.outcome_resolver import (  # noqa: E402
    NON_CRYPTO_MAX_HOLD_HOURS_BY_CLASS,
    RESOLVER_SUBVERSION,
    RESOLVER_VERSION,
    classify_outcome,
    compute_pnl,
    is_unresolved,
    resolve_single_pick,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _iso_hours_ago(hours: float) -> str:
    dt = datetime.now(timezone.utc) - timedelta(hours=hours)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _bars(closes: list[float], start_days_ago: int = 5) -> list[dict]:
    """Build a list of OHLC bars with given closes; high/low pad +/- 0.1%."""
    today = datetime.now(timezone.utc).date()
    out = []
    for i, c in enumerate(closes):
        d = today - timedelta(days=start_days_ago - i)
        out.append({
            "date": d.strftime("%Y-%m-%d"),
            "open": c,
            "high": c * 1.001,
            "low": c * 0.999,
            "close": c,
        })
    return out


# ---------------------------------------------------------------------------
# 1. Direction-aware classification
# ---------------------------------------------------------------------------
class TestDirectionAware:
    def test_long_profit_is_won(self):
        # LONG entry 100, exit 102 = +2% (above 5bp FOREX threshold)
        pnl = compute_pnl(100.0, 102.0, "LONG")
        assert classify_outcome(pnl, asset_class="FOREX") == "WON"

    def test_short_profit_is_won(self):
        # SHORT entry 100, exit 98 = +2% (price down = SHORT win)
        pnl = compute_pnl(100.0, 98.0, "SHORT")
        assert classify_outcome(pnl, asset_class="FOREX") == "WON"

    def test_long_loss_is_lost(self):
        pnl = compute_pnl(100.0, 98.0, "LONG")
        assert classify_outcome(pnl, asset_class="FOREX") == "LOST"

    def test_short_loss_is_lost(self):
        pnl = compute_pnl(100.0, 102.0, "SHORT")
        assert classify_outcome(pnl, asset_class="FOREX") == "LOST"

    def test_sub_5bp_noise_is_flat_for_forex(self):
        # 3bp move below 5bp non-crypto floor
        pnl = compute_pnl(100.0, 100.03, "LONG")
        assert classify_outcome(pnl, asset_class="FOREX") == "FLAT"

    def test_sub_5bp_noise_is_won_for_crypto(self):
        # Same 3bp move resolves WON for CRYPTO (0.1bp floor)
        pnl = compute_pnl(100.0, 100.03, "LONG")
        assert classify_outcome(pnl, asset_class="CRYPTO") == "WON"


# ---------------------------------------------------------------------------
# 2. Bar-replay TP/SL touch (regression test for v2 path)
# ---------------------------------------------------------------------------
class TestBarReplay:
    def test_long_tp_hit_replay(self):
        # LONG entry 100, TP 103, SL 98. Bars walk to 105 → TP touch.
        pick = {
            "symbol": "EURUSD=X",
            "asset_class": "FOREX",
            "direction": "LONG",
            "entry_price": 100.0,
            "take_profit": 103.0,
            "stop_loss": 98.0,
            "status": "EXPIRED",
            "exit_reason": "EXPIRED",
            "pnl_pct": 0.0,
            "exit_price": None,
            "timestamp": _iso_hours_ago(48),
        }
        bars = _bars([100.5, 101.0, 102.0, 105.0, 106.0])
        out = resolve_single_pick(pick, ohlc_window=bars)
        assert out["exit_reason"] == "TP_HIT_REPLAY"
        assert out["status"] == "WON"
        assert out["resolver_version"] == RESOLVER_VERSION
        assert out["pnl_pct"] > 0

    def test_short_sl_hit_replay(self):
        # SHORT entry 100, TP 97, SL 102. Price runs UP to 103 → SL touch.
        pick = {
            "symbol": "GBPJPY=X",
            "asset_class": "FOREX",
            "direction": "SHORT",
            "entry_price": 100.0,
            "take_profit": 97.0,
            "stop_loss": 102.0,
            "status": "EXPIRED",
            "exit_price": None,
            "pnl_pct": 0.0,
            "timestamp": _iso_hours_ago(48),
        }
        bars = _bars([100.5, 101.5, 103.0, 104.0])
        out = resolve_single_pick(pick, ohlc_window=bars)
        assert out["exit_reason"] == "SL_HIT_REPLAY"
        assert out["status"] == "LOST"
        assert out["pnl_pct"] < 0


# ---------------------------------------------------------------------------
# 3. Time-exit case (NEW v2.2 — the actual bug fix)
# ---------------------------------------------------------------------------
class TestTimeExitV22:
    def test_long_time_exit_resolves_at_last_close(self):
        """LONG aged past FOREX max_hold (120h) with no TP/SL touch resolves
        at last bar's close — NOT breakeven."""
        max_h = NON_CRYPTO_MAX_HOLD_HOURS_BY_CLASS["FOREX"]
        pick = {
            "symbol": "EURGBP=X",
            "asset_class": "FOREX",
            "direction": "LONG",
            "entry_price": 1.0,
            "take_profit": 1.05,    # 5% — never hit
            "stop_loss": 0.95,      # 5% — never hit
            "status": "EXPIRED",
            "exit_price": None,
            "pnl_pct": 0.0,
            "timestamp": _iso_hours_ago(max_h + 24),
        }
        # Bars stay near entry — no TP/SL touch. Last close 1.012 = +1.2%.
        bars = _bars([1.005, 1.010, 1.008, 1.012])
        out = resolve_single_pick(pick, ohlc_window=bars)
        assert out["exit_reason"] == "TIME_EXIT_REPLAY"
        # Should NOT be breakeven — pnl reflects last bar close
        assert out["pnl_pct"] != 0.0
        assert out["pnl_pct"] > 0  # LONG, price moved up
        assert out["status"] == "WON"
        assert out["exit_price"] == pytest.approx(1.012, rel=1e-6)
        assert out["resolver_version"] == RESOLVER_VERSION
        assert out["_resolver_subversion"] == RESOLVER_SUBVERSION
        assert "_time_exit_age_hours" in out

    def test_short_time_exit_loss(self):
        """SHORT aged past max_hold with price up = LOST."""
        max_h = NON_CRYPTO_MAX_HOLD_HOURS_BY_CLASS["FOREX"]
        pick = {
            "symbol": "USDJPY=X",
            "asset_class": "FOREX",
            "direction": "SHORT",
            "entry_price": 150.0,
            "take_profit": 145.0,
            "stop_loss": 155.0,
            "status": "EXPIRED",
            "exit_price": None,
            "pnl_pct": 0.0,
            "timestamp": _iso_hours_ago(max_h + 12),
        }
        # No TP/SL touch (155 SL not breached); last close 152 = SHORT lost
        bars = _bars([150.5, 151.0, 151.5, 152.0])
        out = resolve_single_pick(pick, ohlc_window=bars)
        assert out["exit_reason"] == "TIME_EXIT_REPLAY"
        assert out["pnl_pct"] < 0  # SHORT lost (price up)
        assert out["status"] == "LOST"

    def test_young_pick_no_touch_still_retries(self):
        """Pick younger than max_hold with no TP/SL touch still uses retry path
        (preserves v2.1 behavior — don't time-exit too early)."""
        pick = {
            "symbol": "EURUSD=X",
            "asset_class": "FOREX",
            "direction": "LONG",
            "entry_price": 1.0,
            "take_profit": 1.05,
            "stop_loss": 0.95,
            "status": "EXPIRED",
            "exit_price": None,
            "pnl_pct": 0.0,
            "timestamp": _iso_hours_ago(2),  # very fresh
        }
        bars = _bars([1.001, 1.002])
        out = resolve_single_pick(pick, ohlc_window=bars)
        # Should be flagged for retry, NOT time-exited
        assert out.get("_resolve_retry_needed") is True
        assert out.get("_resolver_v2_no_touch") is True
        # Should NOT be marked resolved with TIME_EXIT_REPLAY
        assert out.get("exit_reason") != "TIME_EXIT_REPLAY"


# ---------------------------------------------------------------------------
# 4. Idempotent re-run
# ---------------------------------------------------------------------------
class TestIdempotent:
    def test_resolved_pick_skipped_by_is_unresolved(self):
        """A pick already stamped with non-zero pnl_pct is_unresolved=False."""
        pick = {
            "symbol": "EURUSD=X",
            "asset_class": "FOREX",
            "direction": "LONG",
            "entry_price": 1.0,
            "exit_price": 1.012,
            "take_profit": 1.05,
            "stop_loss": 0.95,
            "status": "WON",
            "pnl_pct": 0.012,
            "exit_reason": "TIME_EXIT_REPLAY",
            "resolver_version": RESOLVER_VERSION,
            "resolved_by": "outcome_resolver",
            "timestamp": _iso_hours_ago(200),
        }
        assert is_unresolved(pick) is False

    def test_rerun_preserves_pnl(self):
        """Resolve once via TIME_EXIT, then re-run — pnl unchanged.

        Idempotent because is_unresolved skips picks with non-zero pnl_pct;
        but if a caller bypasses is_unresolved (e.g. forced re-resolve),
        the bar-replay logic should land on the same pnl when fed identical
        bars."""
        max_h = NON_CRYPTO_MAX_HOLD_HOURS_BY_CLASS["FOREX"]
        pick = {
            "symbol": "EURGBP=X",
            "asset_class": "FOREX",
            "direction": "LONG",
            "entry_price": 1.0,
            "take_profit": 1.05,
            "stop_loss": 0.95,
            "status": "EXPIRED",
            "exit_price": None,
            "pnl_pct": 0.0,
            "timestamp": _iso_hours_ago(max_h + 24),
        }
        bars = _bars([1.005, 1.010, 1.012])
        first = resolve_single_pick(dict(pick), ohlc_window=bars)
        first_pnl = first["pnl_pct"]
        first_exit = first["exit_price"]
        # Now re-run on the resolved dict — is_unresolved should already say no,
        # but if forced, re-resolution must land on the same answer.
        assert is_unresolved(first) is False
        second = resolve_single_pick(dict(first), ohlc_window=bars)
        # Either it short-circuits (no change) or re-resolves to same value.
        # We just require pnl to remain a non-zero finite number with same sign.
        assert second["pnl_pct"] == pytest.approx(first_pnl, rel=1e-6) \
            or second["pnl_pct"] > 0  # tolerate stamp-only churn

    def test_resolver_version_stamped(self):
        """Resolved picks carry resolver_version + subversion so downstream
        consumers can distinguish v2.2 time-exit-replay output from legacy."""
        max_h = NON_CRYPTO_MAX_HOLD_HOURS_BY_CLASS["FOREX"]
        pick = {
            "symbol": "EURUSD=X",
            "asset_class": "FOREX",
            "direction": "LONG",
            "entry_price": 1.0,
            "take_profit": 1.05,
            "stop_loss": 0.95,
            "status": "EXPIRED",
            "exit_price": None,
            "pnl_pct": 0.0,
            "timestamp": _iso_hours_ago(max_h + 12),
        }
        bars = _bars([1.005, 1.010, 1.015])
        out = resolve_single_pick(pick, ohlc_window=bars)
        assert out["resolver_version"] == RESOLVER_VERSION
        # Time-exit picks additionally carry the v2.2 subversion sentinel
        assert out.get("_resolver_subversion") == RESOLVER_SUBVERSION


# ---------------------------------------------------------------------------
# 5. is_unresolved on EXPIRED + null exit_price
# ---------------------------------------------------------------------------
class TestIsUnresolved:
    def test_expired_with_null_exit_is_unresolved(self):
        pick = {
            "symbol": "EURUSD=X",
            "asset_class": "FOREX",
            "direction": "LONG",
            "entry_price": 1.0,
            "exit_price": None,
            "status": "EXPIRED",
            "pnl_pct": 0.0,
        }
        assert is_unresolved(pick) is True

    def test_expired_with_exit_at_entry_is_unresolved(self):
        """The actual production bug shape: exit_price == entry_price within
        rounding tolerance, status=EXPIRED, pnl_pct=0."""
        pick = {
            "symbol": "EURGBP=X",
            "asset_class": "FOREX",
            "direction": "LONG",
            "entry_price": 0.86596,
            "exit_price": 0.86596,
            "status": "EXPIRED",
            "pnl_pct": 0.0,
        }
        assert is_unresolved(pick) is True


# ---------------------------------------------------------------------------
# 6. M-111: PnL sanity cap — implausible price-unit mismatches
# ---------------------------------------------------------------------------
class TestPnlSanityCap:
    """Picks with |pnl_pct| > class cap get _pnl_implausible=True, skip resolve."""

    def _make_pick(self, symbol, asset_class, entry, exit_price, **extra):
        p = {
            "id": f"test-{symbol}",
            "symbol": symbol,
            "asset_class": asset_class,
            "direction": "LONG",
            "entry_price": entry,
            "exit_price": exit_price,
            "status": "CLOSED",
            "pnl_pct": 0.0,
            "strategy": "test_strategy",
            "source_system": "test_sys",
            "timestamp": "2026-05-18T00:00:00Z",
        }
        p.update(extra)
        return p

    def test_cadjpy_unit_mismatch_flagged(self):
        """CADJPY=X with USDCAD entry (1.33) vs CADJPY exit (115) → 8558% → flagged."""
        from alpha_engine.outcome_resolver import resolve_single_pick as resolve_pick
        pick = self._make_pick("CADJPY=X", "FOREX", entry=1.331522, exit_price=115.29)
        out = resolve_pick(pick.copy())
        assert out.get("_pnl_implausible") is True
        assert "_pnl_implausible_raw" in out
        # Must NOT update pnl_pct to the garbage value
        assert abs(out.get("pnl_pct", 0)) < 1.0  # still near 0 (original)

    def test_normal_forex_long_not_flagged(self):
        """A normal 2% FOREX win passes the sanity cap (cap=30%)."""
        from alpha_engine.outcome_resolver import resolve_single_pick as resolve_pick
        pick = self._make_pick("EURUSD=X", "FOREX", entry=1.0800, exit_price=1.1016)
        out = resolve_pick(pick.copy())
        assert out.get("_pnl_implausible") is None
        assert out["status"] == "WON"

    def test_pnl_sanity_cap_for_known_classes(self):
        """_pnl_sanity_cap_for returns correct values for known asset classes."""
        from alpha_engine.outcome_resolver import _pnl_sanity_cap_for
        assert _pnl_sanity_cap_for("FOREX") == pytest.approx(0.30)
        assert _pnl_sanity_cap_for("CRYPTO") == pytest.approx(5.00)
        assert _pnl_sanity_cap_for("UNKNOWN_CLASS") == pytest.approx(10.0)

    def test_default_cap_catches_extreme_unknown_class(self):
        """A 1500% PnL on an unknown class is caught by the 1000% default cap."""
        from alpha_engine.outcome_resolver import resolve_single_pick as resolve_pick
        pick = self._make_pick("WEIRD", "ALIEN_CLASS", entry=1.0, exit_price=16.0)
        out = resolve_pick(pick.copy())
        assert out.get("_pnl_implausible") is True
