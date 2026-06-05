#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Outcome Resolver — Validate Unresolved Closed Picks
=====================================================
Scans closed_picks.json and dashboard_payload.json for picks that were
tracked but never price-checked (pnl_pct == 0 or None with valid entry_price).

For each unresolved pick:
  1. If exit_price exists and differs from entry_price, compute PnL from that.
  2. Otherwise fetch current price via api_failover (Binance mirrors -> Bybit ->
     CoinGecko -> KuCoin) or yfinance for forex/equity/commodity.
  3. Determine outcome: WON (>0.01%), LOST (<-0.01%), FLAT.
  4. Save resolved picks back to closed_picks.json.

Exports:
    resolve_outcomes(closed_picks) -> list[dict]   # resolved subset
    run_outcome_resolver() -> dict                  # full report

Usage:
    python alpha_engine/outcome_resolver.py           # standalone
    python alpha_engine/outcome_resolver.py --dry-run # preview only
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Charter §7 slippage stamping (P0.5-2 wire-up 2026-05-13). Lazy import
# pattern: deferred to call sites so this module stays importable even
# during partial-checkout test scenarios where charter_slippage might
# be absent. See alpha_engine/charter_slippage.py + tests/test_charter_slippage.py.

# Windows UTF-8 fix
if sys.platform == "win32":
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ENGINE_DIR = Path(__file__).resolve().parent
DATA_DIR = ENGINE_DIR / "data"
CLOSED_PICKS_FILE = DATA_DIR / "closed_picks.json"
DASHBOARD_PAYLOAD_FILE = ENGINE_DIR.parent / "audit_trail" / "data" / "dashboard_payload.json"
RESOLVER_LOG_FILE = DATA_DIR / "outcome_resolver_log.json"

# Source-specific paths
QUAN_ENGINE_DIR = ENGINE_DIR.parent / "quan_engine"
QUAN_ENGINE_DATA_DIR = QUAN_ENGINE_DIR / "data"
QUAN_ENGINE_DB_PATH = QUAN_ENGINE_DATA_DIR / "quan_engine.db"
QUAN_ENGINE_SIGNALS_PATH = QUAN_ENGINE_DATA_DIR / "active_signals.json"

RAPID_FIRE_DIR = ENGINE_DIR.parent / "rapid_fire_data"
RAPID_FIRE_ACTIVE_FILE = RAPID_FIRE_DIR / "active_picks.json"
RAPID_FIRE_CLOSED_FILE = RAPID_FIRE_DIR / "closed_picks.json"
RAPID_FIRE_NOW_FILE = RAPID_FIRE_DIR / "now_picks.json"

CLAUDE_GAINER_ML_DIR = ENGINE_DIR.parent / "claude_gainer_ml"
CLAUDE_GAINER_ML_LIVE_PICKS = CLAUDE_GAINER_ML_DIR / "tracker" / "claude_live_picks.json"

# ---------------------------------------------------------------------------
# Import api_failover for crypto price fetching
# ---------------------------------------------------------------------------
sys.path.insert(0, str(ENGINE_DIR))
try:
    from api_failover import fetch_price as _failover_fetch_price
    _HAS_FAILOVER = True
except ImportError:
    _HAS_FAILOVER = False
    _failover_fetch_price = None

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("outcome_resolver")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# v2 (2026-04-28) — Asset-class-gated WIN/LOSS thresholds.
#
# The legacy single threshold of 0.00001 (0.1bp / 0.001%) was set for crypto
# (24x7 markets, sub-bp spreads, tight TPs). When the SAME threshold was applied
# to FOREX/COMMODITY/EQUITY/etc., it converted normal spread/slippage noise
# into "WIN" labels — driving 63.25% of FOREX wins and 66.79% of COMMODITY
# wins to be sub-5bp resolver flicker, not real edge.
#
# Refs:
#   * reports/action_B_resolver_2026_04_27.md (Workstream B investigation)
#   * reports/asset_class_independent_recompute_2026_04_27.md (Part 2 noise table)
#   * memory/feedback_noncrypto_resolver_live_close_bug.md
#   * Copilot Cloud P2 escalation: "Resolver-noise share > 30% on any class"
#
# 5bp non-crypto floor justification: FOREX median TP-distance ~30bp (5bp = 1/6
# of typical TP, well above 1bp spread on majors); COMMODITY median TP-distance
# ~3-4% (5bp is 70x smaller than typical TP); EQUITY 5bp is below intraday
# spread on liquid names but above tick noise. Crypto stays at 0.1bp.
PNL_WIN_THRESHOLD_BY_CLASS = {
    "CRYPTO":    0.00001,   # 0.1bp — keep crypto-tight (high vol, tight TP common)
    "EQUITY":    0.0005,    # 5bp — institutional standard for stocks
    "ETF":       0.0005,    # 5bp
    "FOREX":     0.0005,    # 5bp — tight FX moves are resolver flicker
    "COMMODITY": 0.0005,    # 5bp
    "BOND":      0.0005,    # 5bp
    "FUTURES":   0.0005,    # 5bp
    "STOCK":     0.0005,    # alias for EQUITY
    "INDEX":     0.0005,    # alias for ETF
}
PNL_WIN_THRESHOLD_DEFAULT = 0.00001  # crypto-tight default preserved for unknown classes

# M-111 (2026-05-18): PnL sanity cap — picks with |pnl_pct| exceeding these
# values have implausible price-unit mismatches (e.g. USDCAD stored as CADJPY
# entry_price → 8558% ghost win). The resolver skips resolution and marks the
# pick as _pnl_implausible=True rather than writing corrupt data to analytics.
PNL_SANITY_CAP_BY_CLASS = {
    "FOREX":     0.30,   # 30% — FX majors can't move 30% in a trade
    "EQUITY":    5.00,   # 500%
    "ETF":       2.00,   # 200%
    "CRYPTO":    5.00,   # 500%
    "COMMODITY": 2.00,   # 200%
    "BOND":      0.50,   # 50%
    "FUTURES":   3.00,   # 300%
    "STOCK":     5.00,   # alias
    "INDEX":     2.00,   # alias
}
PNL_SANITY_CAP_DEFAULT = 10.0  # 1000% — catch egregious mismatches on unknown classes


def _pnl_sanity_cap_for(asset_class) -> float:
    """Return the per-class PnL sanity cap (fractional, e.g. 0.30 = 30%)."""
    return PNL_SANITY_CAP_BY_CLASS.get(
        str(asset_class or "").upper(),
        PNL_SANITY_CAP_DEFAULT,
    )


# 2026-05-05: Source-system blocklist by asset class. Twin to BLACKLISTED_STRATEGIES
# but at (class, system) granularity. See updates/index.html PR #2 of 6.
SOURCE_SYSTEM_BLOCKLIST_BY_CLASS = {
    "COMMODITY": frozenset({
        # PF 0.31, n=46 per dashboard_data.json::performance.systems.forex_copy_trader.
        # Bulk of the WR drag keeping COMMODITY 0.4pt below T2 (>50% WR floor).
        "forex_copy_trader",
    }),
}


def _is_source_system_blocked_for_class(asset_class, source_system) -> bool:
    """True when (class, system) pair is in SOURCE_SYSTEM_BLOCKLIST_BY_CLASS.
    Case-insensitive on class, case-sensitive on system."""
    if not source_system:
        return False
    blocked = SOURCE_SYSTEM_BLOCKLIST_BY_CLASS.get(str(asset_class or "").upper())
    return bool(blocked and source_system in blocked)


def _win_threshold_for(asset_class) -> float:
    """Return the per-asset-class WIN PnL threshold.

    Falls back to PNL_WIN_THRESHOLD_DEFAULT (crypto-tight 0.1bp) when the class
    is unknown — preserving legacy behavior for unclassified picks.
    """
    return PNL_WIN_THRESHOLD_BY_CLASS.get(
        str(asset_class or "").upper(),
        PNL_WIN_THRESHOLD_DEFAULT,
    )


def _loss_threshold_for(asset_class) -> float:
    """Return the per-asset-class LOSS PnL threshold (negative mirror)."""
    return -_win_threshold_for(asset_class)


# Legacy single-threshold names retained for backwards-compatibility with any
# external imports. Prefer _win_threshold_for() / _loss_threshold_for().
PNL_WIN_THRESHOLD = PNL_WIN_THRESHOLD_DEFAULT       # crypto-tight; legacy alias
PNL_LOSS_THRESHOLD = -PNL_WIN_THRESHOLD_DEFAULT     # crypto-tight; legacy alias

HTTP_TIMEOUT = 10
RAPID_FIRE_MAX_HOLD_HOURS = 24

# v2.1 (2026-05-02) — Retry cap for non-crypto picks that yfinance can't
# resolve (delisted symbols, weekend runs, persistent feed gaps). Without
# the cap, picks with `_resolve_retry_needed=True` and `exit_price==entry`
# loop forever in is_unresolved → resolve_single_pick → BREAKEVEN fallback
# → is_unresolved (perpetual re-processing, never WR-aggregated).
#
# After MAX_RESOLVE_RETRIES attempts, the pick is force-closed at entry
# (status=FLAT to remain MySQL-compatible), exit_reason set to the
# distinct "RESOLVE_FAILED_MAX_RETRIES" so downstream WR aggregators can
# filter via exit_reason.startswith("RESOLVE_FAILED"), and the diagnostic
# flag _resolve_max_retries_hit=True is set so is_unresolved skips it.
#
# Refs:
#   * reports/PR_609_KIMI_DECOMPOSITION_2026_05_02.md (decomposition rationale)
#   * reports/feedback/{deepseek,cerebras-qwen}-decomp.md (adversarial reviews)
#   * Opus 4.7 Kimi-review session 2026-05-01T20:50Z (original 5-bug catalog)
MAX_RESOLVE_RETRIES = 3

# v2.1 (2026-05-02) — yfinance OHLC fetch timeout. Wrapping yf.Ticker.history()
# in concurrent.futures.ThreadPoolExecutor with a hard timeout — Windows-safe
# (signal.alarm is Unix-only). Without this, a hung yfinance call can stall
# the entire resolver batch.
YFINANCE_TIMEOUT_SECS = 15

# v2 stamping — picks resolved by the v2 logic carry resolver_version="v2" so
# downstream consumers can distinguish post-fix data without schema migration.
# v2.1 increment for the bugfix bundle (retry cap + empty-list guard + yfinance timeout).
RESOLVER_VERSION = "v2.1"
# v2.2 (2026-05-09) — Time-exit replay sub-revision.  Kept on the v2.1 string
# to preserve backwards-compat with downstream pinning (see
# tests/test_outcome_resolver_v21_bugfixes.py).  Use RESOLVER_SUBVERSION when
# you need to identify the time-exit-replay path specifically.
RESOLVER_SUBVERSION = "v2.3"

# v2.2 (2026-05-09) — Per-asset-class TIME_EXIT window for non-crypto picks.
# Mirrors audit_trail/universal_pick_resolver.MAX_HOLD_HOURS_BY_CLASS so a pick
# that has aged past this window with no TP/SL touch can be resolved at the
# LAST OHLC BAR'S CLOSE (real time-exit pnl) instead of retrying-then-breakeven.
#
# Root cause this fixes: pre-v2.2 the no-touch + aged path would call
# _resolve_retry_needed=True → MAX_RESOLVE_RETRIES → breakeven force-close at
# entry with pnl_pct=0.0 status=FLAT. That hid real winners and losers in the
# noise floor and dropped them out of WR aggregations.
NON_CRYPTO_MAX_HOLD_HOURS_BY_CLASS = {
    "EQUITY":    96,
    "ETF":       96,
    "COMMODITY": 96,
    "FUTURES":   96,
    "STOCK":     96,
    "INDEX":     96,
    "FOREX":    72,  # EAGLE2 2026-06-02: unified to 72h (was 120)
    "BOND":     120,
}
NON_CRYPTO_MAX_HOLD_HOURS_DEFAULT = 96


def _non_crypto_max_hold_hours(asset_class) -> int:
    """Return the per-asset-class TIME_EXIT window for non-crypto picks (hours)."""
    return NON_CRYPTO_MAX_HOLD_HOURS_BY_CLASS.get(
        str(asset_class or "").upper(),
        NON_CRYPTO_MAX_HOLD_HOURS_DEFAULT,
    )


def _pick_age_hours(pick: dict) -> Optional[float]:
    """Return how long a pick has been open in hours, or None if unparseable.

    Tries entry_date / entry_time / created_at / timestamp in that order.
    """
    for key in ("entry_date", "entry_time", "created_at", "timestamp",
                "opened_at", "scan_time"):
        raw = pick.get(key)
        if not raw:
            continue
        parsed = _parse_utc_timestamp(str(raw))
        if parsed:
            return (datetime.now(timezone.utc) - parsed).total_seconds() / 3600.0
    return None

# ---------------------------------------------------------------------------
# Yahoo Finance symbols (forex, equity, commodity, bond)
# ---------------------------------------------------------------------------
_YAHOO_SUFFIXES = {"=X", "=F"}
_EQUITY_SYMBOLS = {
    "SPY", "QQQ", "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "TSLA",
    "META", "NVDA", "AMD", "NFLX", "DIS", "BA", "JPM", "GS", "V", "MA",
    "PYPL", "SQ", "COIN", "MSTR", "RIOT", "MARA", "HUT", "BITF",
    "IWM", "DIA", "VTI", "VOO", "ARKK", "XLF", "XLE", "XLK", "GLD",
    "SLV", "USO", "TLT", "VIX", "UVXY", "SQQQ", "TQQQ", "EFA", "EEM",
    "PG", "JNK", "HYG", "LQD", "BND", "AGG",
}

# Categories that are NOT crypto
_NON_CRYPTO_CATEGORIES = {"forex", "equity", "commodity", "bond", "stock", "index"}


# Crypto-quote suffixes that unambiguously identify a crypto trading pair
# (added 2026-05-31 for incident #48 — see _is_non_crypto)
_CRYPTO_SUFFIXES = ("USDT", "USDC", "BUSD", "TUSD", "FDUSD", "DAI", "-USD")


def _is_non_crypto(pick: dict) -> bool:
    """Determine if pick is forex/equity/commodity (not crypto).

    Hardened (incident #48, 2026-05-31) to prioritize unambiguous symbol
    suffixes OVER the upstream ``category`` / ``asset_class`` field. The
    category field has been observed corrupted in production:
        SHIBUSDT  labeled COMMODITY  (vwap_rsi_confluence)
        LINKUSDT  labeled stocks     (regime_terminal)
        AVAXUSDT  labeled stocks     (regime_terminal)
        BNBUSDT   labeled stocks     (regime_terminal)
        BTCUSDT   labeled forex      (alpha_engine)
    Routing these to yfinance instead of api_failover produces 6-9
    order-of-magnitude exit-price drift (e.g. SHIBUSDT exit=4100.97 vs
    entry=5.53e-06), poisoning per-class PF/WR/Sharpe.

    Resolution order:
      1. Yahoo-suffix symbols (=X, =F) → yfinance, always.
      2. Crypto-suffix symbols (USDT/USDC/BUSD/-USD/...) → api_failover,
         regardless of upstream label.
      3. Otherwise honor the category / asset_class field.
      4. Last resort: known equity tickers (base-symbol exact match).
    """
    sym = str(pick.get("symbol", ""))

    # 1. Yahoo Finance suffixes (forex =X, futures/commodity =F) — yfinance
    if any(sym.endswith(s) for s in _YAHOO_SUFFIXES):
        return True

    # 2. Crypto-quote suffixes — api_failover. Beat any corrupted upstream label.
    if any(sym.endswith(s) for s in _CRYPTO_SUFFIXES):
        return False

    # 3. Honor explicit non-crypto category/asset_class label
    cat = str(pick.get("category", pick.get("asset_class", ""))).lower()
    if cat in _NON_CRYPTO_CATEGORIES:
        return True

    # 4. Known equity tickers (base symbol check)
    base = sym.replace("-USD", "").replace("USDT", "").replace("=X", "").replace("=F", "")
    if base in _EQUITY_SYMBOLS:
        return True

    return False


# ---------------------------------------------------------------------------
# Price fetching: crypto via api_failover, non-crypto via yfinance
# ---------------------------------------------------------------------------
def _fetch_crypto_price(symbol: str) -> Optional[float]:
    """Fetch crypto price via api_failover module.

    2026-04-14 fix (issue #193 item 3): when api_failover IS available and
    returned None, do NOT fall back to _fetch_crypto_price_fallback. The
    fallback only retries Binance mirrors, but api_failover already tried
    Binance first in its chain (Binance → Bybit → CoinGecko → KuCoin). If
    api_failover returned None, every provider in that chain failed —
    including Binance — so re-trying Binance is guaranteed to fail again
    and just costs 5 × HTTP_TIMEOUT seconds per pick (~25s per unresolved
    pick at the default 5s timeout).

    On GitHub Actions runners, all 5 Binance mirrors return HTTP 451
    (geo-blocked), causing the Unified Audit Dashboard's resolve_active_picks
    step to time out after 8 minutes when 50+ picks need resolution. With
    the redundant fallback removed, failed lookups return immediately and
    the workflow stays within its budget.

    The fallback is still used when _HAS_FAILOVER is False (api_failover
    module not importable) — that's the legitimate "no other option" case.
    """
    if not _HAS_FAILOVER:
        return _fetch_crypto_price_fallback(symbol)
    try:
        price = _failover_fetch_price(symbol)
        if price and price > 0:
            return float(price)
    except Exception as e:
        log.debug("api_failover failed for %s: %s", symbol, e)
    # api_failover already tried Binance + Bybit + CoinGecko + KuCoin and
    # returned None — no point retrying Binance via the fallback. See docstring.
    return None


def _fetch_crypto_price_fallback(symbol: str) -> Optional[float]:
    """Direct Binance mirror fetch as last resort."""
    sym = symbol.upper().replace("-", "").replace("/", "")
    if sym.endswith("USD") and not sym.endswith("USDT"):
        sym += "T"

    mirrors = [
        "https://data-api.binance.vision",
        "https://api.binance.us",
        "https://api1.binance.com",
        "https://api2.binance.com",
        "https://api3.binance.com",
    ]
    for base in mirrors:
        try:
            url = f"{base}/api/v3/ticker/price?symbol={sym}"
            req = urllib.request.Request(url, headers={"User-Agent": "OutcomeResolver/1.0"})
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                data = json.loads(resp.read())
                if data and "price" in data:
                    return float(data["price"])
        except Exception:
            continue
    return None


def _fetch_yfinance_price(symbol: str) -> Optional[float]:
    """Fetch forex/equity/commodity price via yfinance (if available)."""
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1d")
        if hist is not None and not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception as e:
        log.debug("yfinance failed for %s: %s", symbol, e)

    # Fallback: try stock_forex_prices.json cache
    try:
        prices_file = DATA_DIR / "stock_forex_prices.json"
        if prices_file.exists():
            with open(prices_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            prices = data.get("prices", {})
            # Try exact match then normalized
            for key in [symbol, symbol.replace("=X", "").replace("=F", "")]:
                if key in prices:
                    return float(prices[key])
    except Exception:
        pass
    return None


def _fetch_yfinance_ohlc_window(symbol: str,
                                 entry_dt: Optional[datetime],
                                 lookback_days: int = 30) -> list[dict]:
    """Fetch daily OHLC bars from yfinance for the holding window of a pick.

    v2 (2026-04-28). Mirrors the crypto bar-replay path used by
    ``alpha_engine/forward_validator.py:1060`` (``day_high`` / ``day_low``).
    Returns a list of bars sorted ascending by date::

        [{"date": "YYYY-MM-DD", "open": .., "high": .., "low": .., "close": ..}, ...]

    On any failure (yfinance import error, network, empty history, missing
    columns) returns an empty list — the caller MUST treat that as "no
    bar-replay data available" rather than fabricating a result.
    """
    if not symbol:
        return []
    try:
        import yfinance as yf
    except Exception as e:
        log.debug("yfinance unavailable for OHLC window: %s", e)
        return []

    # Determine fetch window: from entry_dt (or lookback fallback) through today.
    end_dt = datetime.now(timezone.utc)
    if entry_dt is None:
        start_dt = end_dt - __import__("datetime").timedelta(days=lookback_days)
    else:
        # Always pull at least the entry day; cap window to lookback_days.
        from datetime import timedelta
        start_dt = entry_dt - timedelta(days=1)
        if (end_dt - start_dt).days > lookback_days:
            start_dt = end_dt - timedelta(days=lookback_days)

    # v2.1 (2026-05-02): wrap yfinance call in concurrent.futures with a hard
    # timeout so a hung HTTP connection doesn't stall the entire resolver
    # batch. signal.alarm is Unix-only and would break on Windows; this is
    # cross-platform. See reports/PR_609_KIMI_DECOMPOSITION_2026_05_02.md.
    import concurrent.futures as _cf

    def _fetch_history():
        ticker = yf.Ticker(symbol)
        return ticker.history(
            start=start_dt.strftime("%Y-%m-%d"),
            end=(end_dt + __import__("datetime").timedelta(days=1)).strftime("%Y-%m-%d"),
            interval="1d",
            auto_adjust=False,
        )

    _pool = None
    future = None
    try:
        _pool = _cf.ThreadPoolExecutor(max_workers=1)
        future = _pool.submit(_fetch_history)
        hist = future.result(timeout=YFINANCE_TIMEOUT_SECS)
    except _cf.TimeoutError:
        if future is not None:
            future.cancel()
        if _pool is not None:
            try:
                _pool.shutdown(wait=False, cancel_futures=True)
            except TypeError:
                _pool.shutdown(wait=False)
        log.debug("yfinance history TIMED OUT (%ds) for %s", YFINANCE_TIMEOUT_SECS, symbol)
        return []
    except Exception as e:
        if _pool is not None:
            try:
                _pool.shutdown(wait=False, cancel_futures=True)
            except TypeError:
                _pool.shutdown(wait=False)
        log.debug("yfinance history failed for %s: %s", symbol, e)
        return []
    finally:
        # Success path: clean blocking shutdown. Not-done path (BaseException
        # like KeyboardInterrupt / SystemExit propagating through future.result)
        # gets a non-blocking shutdown so the worker thread doesn't outlive the
        # interpreter holding the yfinance HTTP socket.
        if _pool is not None:
            try:
                if future is not None and future.done():
                    _pool.shutdown(wait=True)
                else:
                    if future is not None:
                        future.cancel()
                    _pool.shutdown(wait=False, cancel_futures=True)
            except Exception:
                pass

    if hist is None or hist.empty:
        return []

    bars: list[dict] = []
    try:
        for ts, row in hist.iterrows():
            try:
                hi = float(row["High"])
                lo = float(row["Low"])
                op = float(row["Open"])
                cl = float(row["Close"])
            except (KeyError, TypeError, ValueError):
                continue
            if math.isnan(hi) or math.isnan(lo) or math.isnan(cl):
                continue
            bars.append({
                "date": ts.strftime("%Y-%m-%d") if hasattr(ts, "strftime") else str(ts),
                "open": op, "high": hi, "low": lo, "close": cl,
            })
    except Exception:
        return []

    # Filter bars to those at or after the entry date (yfinance can return one
    # extra leading bar). Keep all bars when entry_dt is unknown.
    if entry_dt is not None:
        cutoff = entry_dt.strftime("%Y-%m-%d")
        bars = [b for b in bars if b["date"] >= cutoff]
    return bars


def _scan_ohlc_for_touch(bars: list[dict], direction: str,
                          tp: float, sl: float) -> Optional[dict]:
    """Walk daily OHLC bars from entry forward; return first TP or SL touch.

    v2 (2026-04-28). Mirrors the crypto bar-replay logic in
    ``alpha_engine/forward_validator.py:1180-1213``. Returns
    ``{"price": <fill>, "reason": "TP_HIT_REPLAY"|"SL_HIT_REPLAY",
       "bar_date": "YYYY-MM-DD"}`` for the first bar where a touch occurred,
    or ``None`` if neither TP nor SL was touched in the supplied window.

    Tie-break: when both TP and SL would fire in the same bar, SL is checked
    first (conservative — assumes worst-case fill). This mirrors the
    forward_validator's TP-then-SL ordering only when current_price is closer
    to TP; the resolver runs after-the-fact so it must be conservative.
    """
    if not bars or not (tp > 0 or sl > 0):
        return None
    is_long = str(direction or "").upper() in ("LONG", "BUY")
    # C1 fix (reports/crypto_edge_artifact_audit_2026_05_17.md): credit a
    # gap-aware OBSERVED fill. When a bar OPENS past the level, the order filled
    # at the gap-through open price, not at the nominal level. Crediting the
    # nominal `tp`/`sl` pinned every win to exactly the TP distance, producing
    # the "ghost row" artifact (e.g. 81% of wins at exactly +3.0%). `gapped` is
    # surfaced so callers / aggregators can flag non-nominal fills.
    for bar in bars:
        try:
            hi = float(bar.get("high", 0) or 0)
            lo = float(bar.get("low", 0) or 0)
            op = float(bar.get("open", 0) or 0)
        except (TypeError, ValueError):
            continue
        if hi <= 0 or lo <= 0:
            continue
        if is_long:
            # SL first (conservative — assume worst case if both possible)
            if sl > 0 and lo <= sl:
                gapped = op > 0 and op <= sl
                return {"price": op if gapped else sl, "reason": "SL_HIT_REPLAY",
                        "bar_date": bar.get("date", ""), "gapped": gapped}
            if tp > 0 and hi >= tp:
                gapped = op > 0 and op >= tp
                return {"price": op if gapped else tp, "reason": "TP_HIT_REPLAY",
                        "bar_date": bar.get("date", ""), "gapped": gapped}
        else:  # SHORT
            if sl > 0 and hi >= sl:
                gapped = op > 0 and op >= sl
                return {"price": op if gapped else sl, "reason": "SL_HIT_REPLAY",
                        "bar_date": bar.get("date", ""), "gapped": gapped}
            if tp > 0 and lo <= tp:
                gapped = op > 0 and op <= tp
                return {"price": op if gapped else tp, "reason": "TP_HIT_REPLAY",
                        "bar_date": bar.get("date", ""), "gapped": gapped}
    return None


def fetch_price_for_pick(pick: dict) -> Optional[float]:
    """Fetch current price for a pick, routing to correct source."""
    symbol = pick.get("symbol", "")
    if not symbol:
        return None

    if _is_non_crypto(pick):
        return _fetch_yfinance_price(symbol)
    else:
        return _fetch_crypto_price(symbol)


def _parse_utc_timestamp(value: str) -> Optional[datetime]:
    """Parse common timestamp shapes and normalize them to UTC-aware datetimes."""
    if not value:
        return None

    raw = str(value).strip()
    if not raw:
        return None

    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        parsed = None
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
        ):
            try:
                parsed = datetime.strptime(raw, fmt)
                break
            except ValueError:
                continue
        if parsed is None:
            return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------
def _safe_float(val) -> float:
    """Convert to float safely, returning 0.0 on failure."""
    if val is None:
        return 0.0
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return 0.0
        return f
    except (ValueError, TypeError):
        return 0.0


def is_unresolved(pick: dict) -> bool:
    """Check if a closed pick needs outcome resolution."""
    status = str(pick.get("status", "")).upper()
    pnl = pick.get("pnl_pct")
    entry = _safe_float(pick.get("entry_price"))
    exit_raw = pick.get("exit_price")
    exit_p = _safe_float(exit_raw)

    # Must have an entry price
    if not entry or entry <= 0:
        return False

    # v2.1 (2026-05-02): picks that hit MAX_RESOLVE_RETRIES are FINAL.
    # Without this guard, the BREAKEVEN fallback (exit_p == entry) would
    # re-trigger the unresolved branch below in perpetuity. Force-closed
    # picks have _resolve_max_retries_hit=True set in resolve_single_pick.
    if pick.get("_resolve_max_retries_hit"):
        return False

    # FIX: Closed picks with NO exit_price are ALWAYS unresolved, regardless of pnl_pct.
    # Previously missed: 393 forex/commodity copy-trader picks with
    # status=CLOSED, exit_price=None, pnl_pct=0.0 went undetected.
    if status in ("WON", "LOST", "CLOSED", "EXPIRED"):
        if exit_raw is None or exit_p <= 0:
            return True

    # Must have pnl_pct == 0 or None for the remaining checks
    pnl_val = _safe_float(pnl)
    if pnl_val != 0.0:
        return False

    # If pnl is explicitly None, it's unresolved
    if pnl is None:
        return True

    # pnl_pct == 0 but has exit_price equal to entry (copy artifact)
    if exit_p > 0 and abs(exit_p - entry) / entry < 0.00001:
        # exit == entry, was never properly resolved
        return True

    # Status says WON/LOST but pnl is 0 — needs resolution
    if status in ("WON", "LOST", "CLOSED", "EXPIRED"):
        return True

    return False


def get_split_adjustment(symbol: str, entry_dt, exit_dt) -> float:
    """Return cumulative split factor between entry_dt and exit_dt.

    Only meaningful for EQUITY/ETF symbols. Returns 1.0 on any error or when
    no splits occurred, so callers never need to guard against exceptions.
    """
    try:
        if not symbol or entry_dt is None or exit_dt is None:
            return 1.0
        import yfinance as yf  # lazy import — not always installed
        ticker = yf.Ticker(symbol)
        splits = ticker.splits
        if splits is None or splits.empty:
            return 1.0
        # Normalise tz to naive UTC for comparison
        def _naive(dt):
            if hasattr(dt, "tzinfo") and dt.tzinfo is not None:
                return dt.replace(tzinfo=None)
            return dt
        entry_n, exit_n = _naive(entry_dt), _naive(exit_dt)
        idx_naive = splits.index.tz_localize(None) if splits.index.tzinfo is not None else splits.index.tz_convert(None)
        mask = (idx_naive > entry_n) & (idx_naive <= exit_n)
        relevant = splits[mask]
        if relevant.empty:
            return 1.0
        return float(relevant.prod())
    except Exception:
        return 1.0


def compute_pnl(entry: float, exit_price: float, direction: str) -> float:
    """Compute PnL percentage.

    Returns fractional PnL: 0.05 = 5%, -0.03 = -3%.
    """
    if not entry or entry <= 0:
        return 0.0
    if direction.upper() in ("SHORT", "SELL"):
        return (entry - exit_price) / entry
    else:
        return (exit_price - entry) / entry


def classify_outcome(pnl_pct: float, asset_class: Optional[str] = None) -> str:
    """Classify PnL into WON/LOST/FLAT using an asset-class-aware threshold.

    v2 (2026-04-28): when ``asset_class`` is provided, the win/loss thresholds
    come from ``PNL_WIN_THRESHOLD_BY_CLASS`` (5bp for non-crypto, 0.1bp for
    crypto). When ``asset_class`` is omitted, falls back to the legacy 0.1bp
    threshold so existing call sites keep their old behavior. New callers
    SHOULD pass ``asset_class``.

    See ``reports/action_B_resolver_2026_04_27.md`` for the 5bp justification.
    """
    if asset_class is not None:
        win_thr = _win_threshold_for(asset_class)
        loss_thr = -win_thr
    else:
        win_thr = PNL_WIN_THRESHOLD
        loss_thr = PNL_LOSS_THRESHOLD
    if pnl_pct > win_thr:
        return "WON"
    elif pnl_pct < loss_thr:
        return "LOST"
    return "FLAT"


def _resolve_asset_class(pick: dict) -> str:
    """Best-effort asset_class string for threshold gating.

    Reads pick["asset_class"] / pick["category"], otherwise infers from the
    Yahoo Finance suffix or the existing _is_non_crypto() heuristic. Returns
    the uppercase canonical key the threshold map uses ("CRYPTO", "FOREX", ...)
    or "" when nothing can be inferred (caller falls back to default).

    Symbol suffixes (=X → FOREX, =F → COMMODITY/FUTURES) are always trusted
    over the asset_class field — they are unambiguous Yahoo Finance markers and
    cannot be overridden by a misclassified upstream pick (e.g. USDJPY=X
    tagged as BOND by cta_replicator).
    """
    sym = str(pick.get("symbol", "") or "")
    # Suffix check first — unambiguous; beats any upstream asset_class tag
    if sym.endswith("=X"):
        return "FOREX"
    if sym.endswith("=F"):
        return "COMMODITY"
    raw = str(pick.get("asset_class") or pick.get("category") or "").upper().strip()
    if raw:
        # Some upstream writers use "STOCKS" / "FX" — normalize a few aliases.
        aliases = {"STOCKS": "EQUITY", "FX": "FOREX", "COMMODITIES": "COMMODITY",
                   "BONDS": "BOND", "INDICES": "INDEX"}
        return aliases.get(raw, raw)
    if _is_non_crypto(pick):
        return "EQUITY"
    return "CRYPTO"


def _infer_direction(pick: dict) -> str:
    """Infer direction from pick data."""
    direction = str(pick.get("direction", pick.get("signal_type",
                    pick.get("signal", pick.get("action", ""))))).upper()
    if "BUY" in direction or "LONG" in direction:
        return "LONG"
    if "SELL" in direction or "SHORT" in direction:
        return "SHORT"
    # Infer from TP vs entry
    entry = _safe_float(pick.get("entry_price"))
    tp = _safe_float(pick.get("take_profit", pick.get("targetPrice",
                     pick.get("tp", 0))))
    if entry > 0 and tp > 0:
        return "LONG" if tp > entry else "SHORT"
    return "LONG"  # default


def resolve_single_pick(pick: dict, live_price: Optional[float] = None,
                         ohlc_window: Optional[list[dict]] = None) -> dict:
    """Resolve a single unresolved pick. Returns updated pick dict.

    If ``live_price`` is provided, uses that for the legacy crypto path.
    For non-crypto picks, the v2 fix (2026-04-28) prefers ``ohlc_window`` —
    a list of daily OHLC bars from entry through today — and walks them for
    a TP or SL touch via :func:`_scan_ohlc_for_touch`. If no touch is found
    in the OHLC window, the pick is left as ``still_active`` rather than
    being closed at live spot (the legacy bug).

    See ``reports/action_B_resolver_2026_04_27.md`` for context.
    """
    # 2026-05-03: Skip resolution for BLACKLISTED_STRATEGIES so they do not
    # contaminate per-strategy/per-class PF/WR aggregates. Picks remain in
    # storage but are tagged exit_reason=BLACKLISTED for downstream filtering.
    # Twin to smart_picks_engine.py:score_pick blacklist gate. Per
    # reports/HEDGE_FUND_PR_MERGE_AUDIT_2026_05_03.md section 5.
    try:
        from alpha_engine.config import BLACKLISTED_STRATEGIES as _BLACKLIST
    except Exception:
        _BLACKLIST = []
    _strat = (pick.get("strategy") or "").strip().lower()
    if _strat and _strat in {s.lower() for s in _BLACKLIST}:
        out = dict(pick)
        out["status"] = "CLOSED"
        out["exit_reason"] = "BLACKLISTED"
        out["pnl_pct"] = 0.0
        out["_blacklist_reason"] = f"strategy={_strat} in BLACKLISTED_STRATEGIES"
        return out

    # 2026-05-05: (class, system) blocklist gate. Twin to the BLACKLIST gate above.
    _src = pick.get("source_system") or ""
    _cls_blk = _resolve_asset_class(pick) if _src else ""
    if _src and _cls_blk and _is_source_system_blocked_for_class(_cls_blk, _src):
        out = dict(pick)
        out["status"] = "CLOSED"
        out["exit_reason"] = "BLOCKED_SOURCE_FOR_CLASS"
        out["pnl_pct"] = 0.0
        out["_blacklist_reason"] = f"source_system={_src} blocked for class={_cls_blk}"
        return out

    entry = _safe_float(pick.get("entry_price"))
    exit_p = _safe_float(pick.get("exit_price"))
    direction = _infer_direction(pick)
    tp = _safe_float(pick.get("take_profit", pick.get("targetPrice", 0)))
    sl = _safe_float(pick.get("stop_loss", pick.get("stopPrice", 0)))
    # Persist the resolved class back to the pick so downstream consumers
    # (dashboard hf_stats.by_asset_class, per-class panels, strategy promotion
    # gates, audit credibility footnotes) inherit the same value the resolver
    # used internally for win-threshold gating. Gated by a null/empty/UNKNOWN
    # check so we never clobber an upstream-tagged value. Root cause for the
    # 92% null-asset_class gap on closed_picks.json — see
    # reports/asset_class_tagger_investigation_2026_05_04.md.
    _existing_ac = str(pick.get("asset_class") or "").upper().strip()
    if _existing_ac in ("UNKNOWN", "NONE"):
        # Force re-derivation by stripping the sentinel before the resolver
        # reads it. _resolve_asset_class would otherwise echo "UNKNOWN" back.
        _scrubbed = dict(pick); _scrubbed["asset_class"] = None
        asset_class = _resolve_asset_class(_scrubbed)
    else:
        asset_class = _resolve_asset_class(pick)
    if asset_class and (not _existing_ac or _existing_ac in ("UNKNOWN", "NONE")):
        pick["asset_class"] = asset_class
    is_non_crypto = asset_class != "CRYPTO" and (asset_class != "" or _is_non_crypto(pick))

    # Determine the best exit price to use
    effective_exit = None
    exit_reason = pick.get("exit_reason", "")
    # 2026-06-02 fix: capture original exit_reason/status BEFORE live_price/OHLC
    # paths overwrite them. The v2.3 EXPIRED guard below uses these originals.
    _orig_exit_reason = str(exit_reason or "").upper()
    _orig_status = str(pick.get("status", "") or "").upper()

    # If exit_price meaningfully differs from entry, use it
    if exit_p > 0 and entry > 0 and abs(exit_p - entry) / entry > 0.00001:
        effective_exit = exit_p
        if not exit_reason:
            exit_reason = "EXIT_PRICE_RESOLVED"
    elif is_non_crypto and ohlc_window is not None and len(ohlc_window) > 0:
        # v2 path — bar-replay TP/SL detection. Replaces the legacy "close at
        # live spot" branch which was the source of FOREX/COMMODITY 63%/67%
        # noise-share. See reports/action_B_resolver_2026_04_27.md §3.2.
        # v2.1 (2026-05-02): explicit `is not None and len > 0` instead of
        # truthiness check `and ohlc_window:` — empty list `[]` is falsy and
        # used to fall through to the crypto live-spot branch below, defeating
        # the v2 fix. See reports/PR_609_KIMI_DECOMPOSITION_2026_05_02.md.
        hit = _scan_ohlc_for_touch(ohlc_window, direction, tp, sl)
        if hit:
            effective_exit = float(hit["price"])
            exit_reason = hit["reason"]  # TP_HIT_REPLAY or SL_HIT_REPLAY
            pick["_replay_bar_date"] = hit.get("bar_date", "")
        else:
            # Neither TP nor SL was touched in the window.
            #
            # v2.2 (2026-05-09): if the pick has aged past its per-asset-class
            # MAX_HOLD window, resolve at the LAST OHLC BAR'S CLOSE (real
            # time-exit pnl) instead of retry-then-breakeven. This was the
            # core no_resolve bug — non-crypto picks with valid OHLC but no
            # TP/SL touch were stuck in an infinite retry → breakeven loop
            # that hid real winners and losers in the noise floor.
            #
            # Direction-aware pnl is computed downstream by compute_pnl()
            # using the existing direction/entry; we just supply effective_exit.
            age_h = _pick_age_hours(pick)
            max_hold_h = _non_crypto_max_hold_hours(asset_class)
            if age_h is not None and age_h >= max_hold_h:
                last_bar = ohlc_window[-1]
                last_close = float(last_bar.get("close", 0) or 0)
                if last_close > 0:
                    effective_exit = last_close
                    exit_reason = "TIME_EXIT_REPLAY"
                    pick["_replay_bar_date"] = last_bar.get("date", "")
                    pick["_time_exit_age_hours"] = round(age_h, 1)
                    pick["_resolver_subversion"] = RESOLVER_SUBVERSION
                else:
                    # Last bar has no usable close — fall through to retry path.
                    pick["_resolver_v2_no_touch"] = True
            if effective_exit is None:
                # v2.1 retry path preserved for picks too young to time-exit.
                # Increment retry counter; after MAX_RESOLVE_RETRIES, fall
                # through to the breakeven block which force-closes at entry.
                retry_count = int(pick.get("_resolve_retry_count", 0) or 0) + 1
                pick["_resolve_retry_count"] = retry_count
                if retry_count < MAX_RESOLVE_RETRIES:
                    pick["_resolve_retry_needed"] = True
                    pick["_resolver_v2_no_touch"] = True
                    return pick
                # else: retries exhausted — fall through to effective_exit=None
                # → breakeven block force-closes at entry with status=FLAT and
                # exit_reason=RESOLVE_FAILED_MAX_RETRIES.
                pick["_resolver_v2_no_touch"] = True
    elif is_non_crypto and (ohlc_window is None or len(ohlc_window) == 0):
        # v2.1 (2026-05-02): empty/missing ohlc_window for non-crypto. Refuse
        # to close at live spot — this was the legacy bug AND the bug that the
        # truthiness check on line 608 was silently masking. Flag for retry
        # by a caller that can supply OHLC. Includes the previous live_price
        # path (which only fired when ohlc_window was None, never []).
        # Increment retry counter; after MAX, fall through to breakeven force-close.
        retry_count = int(pick.get("_resolve_retry_count", 0) or 0) + 1
        pick["_resolve_retry_count"] = retry_count
        if retry_count < MAX_RESOLVE_RETRIES:
            pick["_resolve_retry_needed"] = True
            pick["_resolver_v2_no_ohlc"] = True
            return pick
        # else: retries exhausted — fall through to breakeven block.
        pick["_resolver_v2_no_ohlc"] = True
    elif live_price and live_price > 0:
        # Crypto-only legacy path (preserved). Use live price — pick is already
        # closed so this is a retroactive resolution. Crypto pairs trade 24x7
        # with sub-bp spreads so live spot is a reasonable witness; the noise
        # audit confirmed CRYPTO did NOT trip the >30% noise-share bar.
        effective_exit = live_price
        # C1 fix (reports/crypto_edge_artifact_audit_2026_05_17.md): credit the
        # REAL observed live price, not the nominal tp/sl. live_price is the
        # genuine witness (the pick is already closed — retroactive resolution).
        # Overwriting effective_exit with tp/sl pinned every win's pnl_pct to
        # exactly the TP distance — the "ghost row" artifact.
        if direction == "LONG":
            if tp > 0 and live_price >= tp:
                exit_reason = "TP_HIT_RESOLVED"
            elif sl > 0 and live_price <= sl:
                exit_reason = "SL_HIT_RESOLVED"
            else:
                exit_reason = "PRICE_RESOLVED"
        else:  # SHORT
            if tp > 0 and live_price <= tp:
                exit_reason = "TP_HIT_RESOLVED"
            elif sl > 0 and live_price >= sl:
                exit_reason = "SL_HIT_RESOLVED"
            else:
                exit_reason = "PRICE_RESOLVED"

    if effective_exit is None or effective_exit <= 0:
        # Can't fetch live price (e.g. yfinance forex timeout). Instead of
        # leaving exit_price=None and status=CLOSED (which triggers the 393
        # "missing exit_price" bug in the audit dashboard), persist a breakeven
        # exit using entry price with a distinct exit_reason so these picks
        # can be retried later AND are no longer data-integrity violations.
        #
        # v2.1 (2026-05-02): retry cap. The pre-v2.1 behavior set
        # _resolve_retry_needed=True unconditionally, and is_unresolved
        # returned True for picks where exit_p == entry — creating an
        # infinite re-processing loop where the pick was never WR-aggregated.
        # After MAX_RESOLVE_RETRIES attempts the pick is force-closed at
        # entry with exit_reason="RESOLVE_FAILED_MAX_RETRIES" and the
        # diagnostic flag _resolve_max_retries_hit=True so is_unresolved
        # treats it as resolved. Downstream WR aggregators filter
        # exit_reason.startswith("RESOLVE_FAILED") to exclude these from
        # win-rate denominators. status remains "FLAT" for MySQL
        # compatibility (mysql_client.py:674 maps FLAT -> CLOSED).
        status = str(pick.get("status", "")).upper()
        # 2026-05-31 fix: preserve pre-recorded exit_price when an upstream
        # closer (portfolio_tracker_* TIME_EXIT_*, force_close_breached
        # STALE_NO_DATA, MAX_HOLD, EXPIRED, etc.) already stamped a real
        # exit_price that differs from entry. The pre-fix breakeven branch
        # below unconditionally overwrote exit_price=entry and pnl_pct=0.0,
        # destroying 581 of 1,394 exit-logic divergence rows per
        # reports/peer_claude-exit-logic-divergence_2026-05-31.md.
        #
        # Rule: only zero pnl_pct when exit_price is None/0/missing OR
        # within float-tolerance of entry. If exit_price is recorded and
        # differs meaningfully from entry, recompute pnl_pct from it.
        if (
            status in ("CLOSED", "EXPIRED", "WON", "LOST")
            and entry > 0
            and exit_p > 0
            and abs(exit_p - entry) / entry > 0.00001
        ):
            preserved_pnl = compute_pnl(entry, exit_p, direction)
            _pnl_cap_preserve = _pnl_sanity_cap_for(asset_class)
            if abs(preserved_pnl) <= _pnl_cap_preserve:
                pick["pnl_pct"] = round(preserved_pnl, 6)
                pick["direction"] = direction
                pick["resolved_at"] = datetime.now(timezone.utc).isoformat()
                pick["resolved_by"] = "outcome_resolver_preserve_exit_price"
                pick["_resolver_preserved_exit_price"] = True
                # Re-classify so status/exit_reason are consistent.
                _preserved_outcome = classify_outcome(preserved_pnl, asset_class=asset_class or None)
                _er = str(pick.get("exit_reason") or "").upper()
                if _er and any(
                    _er.startswith(prefix)
                    for prefix in ("EXPIRED", "TIME_EXIT", "MAX_HOLD", "STALE_NO_DATA")
                ):
                    _preserved_outcome = "EXPIRED"
                pick["status"] = _preserved_outcome
                if not pick.get("resolver_version"):
                    pick["resolver_version"] = RESOLVER_VERSION
                return pick

        if status in ("CLOSED", "EXPIRED", "WON", "LOST") and entry > 0:
            retry_count = int(pick.get("_resolve_retry_count", 0) or 0) + 1
            pick["_resolve_retry_count"] = retry_count
            pick["exit_price"] = entry
            pick["pnl_pct"] = 0.0
            pick["direction"] = direction
            pick["resolved_at"] = datetime.now(timezone.utc).isoformat()

            if retry_count >= MAX_RESOLVE_RETRIES:
                # Cap reached — finalize as failed-resolution. Distinct
                # exit_reason so downstream WR aggregators can exclude.
                pick["status"] = "FLAT"
                pick["exit_reason"] = "RESOLVE_FAILED_MAX_RETRIES"
                pick["resolved_by"] = "outcome_resolver_max_retries"
                pick["_resolver_fallback"] = True   # analytics: yfinance exhausted retries, pnl forced 0.0
                pick["_resolve_max_retries_hit"] = True
                # Clear the perpetual-retry flag so is_unresolved skips it.
                pick.pop("_resolve_retry_needed", None)
                logger = logging.getLogger("outcome_resolver")
                logger.info(
                    "Pick force-closed at MAX_RESOLVE_RETRIES=%d: %s %s",
                    MAX_RESOLVE_RETRIES,
                    pick.get("symbol", ""),
                    pick.get("strategy", ""),
                )
            else:
                # Below cap — retry on next pass. Preserve original behavior.
                if not pick.get("exit_reason") or pick.get("exit_reason") == "CLOSED":
                    pick["exit_reason"] = "RESOLVE_FAILED_BREAKEVEN"
                pick["resolved_by"] = "outcome_resolver_fallback"
                pick["_resolver_fallback"] = True   # analytics: yfinance returned None, pnl forced 0.0
                pick["_resolve_retry_needed"] = True  # flag for later re-resolution
        return pick

    pnl_pct = compute_pnl(entry, effective_exit, direction)

    # M-111: PnL sanity cap — flag implausible results from price-unit mismatches
    # (e.g. USDCAD stored as CADJPY entry → (115.29-1.33)/1.33 = 8558%).
    _pnl_cap = _pnl_sanity_cap_for(asset_class)
    if abs(pnl_pct) > _pnl_cap:
        _logger = logging.getLogger("outcome_resolver")
        _logger.warning(
            "PNL_IMPLAUSIBLE: %s %s ac=%s pnl=%.4f > cap=%.2f "
            "(entry=%.6f exit=%.6f) — marking _pnl_implausible=True, skipping",
            pick.get("symbol", ""), pick.get("strategy", ""),
            asset_class, pnl_pct, _pnl_cap, entry, effective_exit,
        )
        pick["_pnl_implausible"] = True
        pick["_pnl_implausible_raw"] = round(pnl_pct, 6)
        pick["_pnl_implausible_cap"] = _pnl_cap
        return pick  # do not write corrupt PnL to analytics

    # v2: asset-class-gated thresholds. Picks below the per-class noise floor
    # land as FLAT and are filtered from WR aggregations downstream.
    outcome = classify_outcome(pnl_pct, asset_class=asset_class or None)

    # v2.3 (2026-05-27): EXPIRED/TIME_EXIT/MAX_HOLD picks must be labeled
    # as EXPIRED regardless of PnL sign — intraday drift should not convert
    # an expired pick into a WON. See reports/2026-05-25_crypto_78pct_wr_verification.md
    # 2026-06-02 fix: ALSO check _orig_status/_orig_exit_reason (captured before
    # live_price overwrites exit_reason to TP_HIT_RESOLVED/PRICE_RESOLVED, and
    # before OHLC path overwrites to TP_HIT_REPLAY/SL_HIT_REPLAY).
    _expired_original = (
        _orig_status == "EXPIRED"
        or any(_orig_exit_reason.startswith(p) for p in ("EXPIRED", "TIME_EXIT", "MAX_HOLD"))
    )
    if _expired_original or (exit_reason and any(
        str(exit_reason).upper().startswith(prefix)
        for prefix in ("EXPIRED", "TIME_EXIT", "MAX_HOLD")
    )):
        outcome = "EXPIRED"
        pick["_resolver_subversion"] = "v2.3"

    # v2: preserve legacy values BEFORE overwriting, so audit trail remains
    # reproducible. Only stamp on the FIRST v2 pass (don't churn legacy fields
    # if a pick is re-resolved twice).
    if not pick.get("resolver_version"):
        if "pnl_pct" in pick and pick.get("pnl_pct") not in (None, 0, 0.0):
            pick["_legacy_pnl_pct"] = pick.get("pnl_pct")
        if pick.get("exit_reason"):
            pick["_legacy_exit_reason"] = pick.get("exit_reason")

    # Incident #10 (2026-05-31): FOREX pnl_pct clamp to [-100, +inf).
    # A long position can lose at most 100% of capital; anything more negative
    # (e.g. -106700%) is a price-unit/direction-sign bug, not a real loss.
    # Upper bound is left open (+inf) because a short FX position can exceed
    # 100% gain on extreme moves. M-111 implausibility cap (above) still
    # short-circuits the truly absurd cases; this clamp catches the residual
    # write-path leak observed in 5 surviving rows.
    if (asset_class or "").upper() == "FOREX" and pnl_pct < -100.0:
        _logger = logging.getLogger("outcome_resolver")
        _logger.warning(
            "FOREX_PNL_CLAMP: %s %s pnl=%.4f clamped to -100.0 "
            "(entry=%.6f exit=%.6f dir=%s)",
            pick.get("symbol", ""), pick.get("strategy", ""),
            pnl_pct, entry, effective_exit, direction,
        )
        pick["_pnl_clamped_raw"] = round(pnl_pct, 6)
        pick["_pnl_clamped_reason"] = "forex_lower_bound_-100"
        pnl_pct = -100.0

    # Update pick
    pick["exit_price"] = effective_exit
    pick["pnl_pct"] = round(pnl_pct, 6)
    pick["status"] = outcome
    pick["exit_reason"] = exit_reason
    pick["direction"] = direction
    pick["resolved_at"] = datetime.now(timezone.utc).isoformat()
    pick["resolved_by"] = "outcome_resolver"
    pick["resolver_version"] = RESOLVER_VERSION  # "v2"
    # Charter §7 P0.5-2: stamp _pnl_pct_gross + _pnl_pct_net using per-class
    # round-trip slippage. Idempotent; doesn't change `pnl_pct` or `status`.
    try:
        from alpha_engine.charter_slippage import stamp_pick_net_pnl
        stamp_pick_net_pnl(pick)
    except ImportError:
        pass
    if asset_class:
        pick["_resolved_asset_class"] = asset_class
        pick["asset_class"] = asset_class

    # Fix B: record recent exit for re-entry cooldown.
    try:
        from alpha_engine.non_crypto_policy import record_recent_exit as _record_recent_exit
        _kind = "SL" if "SL" in str(exit_reason).upper() else (
            "TP" if "TP" in str(exit_reason).upper() else (
                "EXPIRED" if ("TIME" in str(exit_reason).upper() or "EXPIR" in str(exit_reason).upper()) else ""
            )
        )
        if _kind:
            _record_recent_exit(str(pick.get("symbol") or ""), _kind, pick["resolved_at"])
    except Exception:
        pass

    # Backfill entry_date if missing (fixes 97.9% missing entry_date in closed picks)
    if not pick.get("entry_date"):
        pick["entry_date"] = (pick.get("created_at") or pick.get("entry_time") or pick.get("timestamp") or "")[:10]

    # Compute dollar PnL if allocation exists
    allocation = _safe_float(pick.get("allocation", 2000.0))
    if allocation > 0:
        pick["pnl_dollar"] = round(pnl_pct * allocation, 2)

    return pick


def resolve_outcomes(closed_picks: list[dict], fetch_prices: bool = True,
                     dry_run: bool = False) -> list[dict]:
    """Resolve all unresolved picks in the list.

    Args:
        closed_picks: List of closed pick dicts (modified in-place).
        fetch_prices: Whether to fetch live prices for picks without exit_price.
        dry_run: If True, don't modify picks, just report.

    Returns:
        List of picks that were resolved (subset of closed_picks).
    """
    unresolved = [p for p in closed_picks if is_unresolved(p)]
    if not unresolved:
        log.info("No unresolved picks found.")
        return []

    log.info("Found %d unresolved picks out of %d total closed.", len(unresolved), len(closed_picks))

    # Group by symbol to batch price fetches
    by_symbol: dict[str, list[dict]] = defaultdict(list)
    for pick in unresolved:
        sym = pick.get("symbol", "UNKNOWN")
        by_symbol[sym].append(pick)

    log.info("Fetching prices for %d unique symbols...", len(by_symbol))

    # Fetch prices (legacy live-spot — still used for crypto)
    price_cache: dict[str, Optional[float]] = {}
    # v2: per-symbol OHLC window cache for non-crypto bar-replay TP/SL detection.
    ohlc_cache: dict[str, list[dict]] = {}
    if fetch_prices:
        for sym, picks_for_sym in by_symbol.items():
            if sym in price_cache:
                continue
            # Use the first pick to determine asset class
            sample_pick = picks_for_sym[0]
            price = fetch_price_for_pick(sample_pick)
            price_cache[sym] = price
            if price:
                log.debug("  %s = %.6f", sym, price)
            else:
                log.debug("  %s = NO PRICE", sym)

            # v2: For non-crypto picks, additionally fetch the OHLC window
            # spanning entry_date -> today so resolve_single_pick can do
            # bar-replay TP/SL detection instead of closing at live spot.
            if _is_non_crypto(sample_pick):
                # Find earliest entry_date across all picks for this symbol so
                # the window covers them all.
                earliest_entry: Optional[datetime] = None
                for p in picks_for_sym:
                    raw = (p.get("entry_date") or p.get("entry_time")
                           or p.get("created_at") or p.get("timestamp") or "")
                    parsed = _parse_utc_timestamp(str(raw)) if raw else None
                    if parsed and (earliest_entry is None or parsed < earliest_entry):
                        earliest_entry = parsed
                ohlc_cache[sym] = _fetch_yfinance_ohlc_window(sym, earliest_entry)
                if ohlc_cache[sym]:
                    log.debug("  %s OHLC bars=%d", sym, len(ohlc_cache[sym]))
                else:
                    log.debug("  %s OHLC=EMPTY", sym)

            # Rate limit: be gentle with APIs
            time.sleep(0.1)

    # Resolve each pick
    resolved = []
    for pick in unresolved:
        sym = pick.get("symbol", "UNKNOWN")
        live_price = price_cache.get(sym)
        ohlc_window = ohlc_cache.get(sym) or None

        if dry_run:
            # Preview only — use the v2 asset-class-gated classifier so the
            # preview matches what the actual resolver will write.
            entry = _safe_float(pick.get("entry_price"))
            exit_p = _safe_float(pick.get("exit_price"))
            direction = _infer_direction(pick)
            preview_exit = live_price or exit_p
            # Mirror the persistence pattern from resolve_single_pick. See
            # reports/asset_class_tagger_investigation_2026_05_04.md.
            _existing_ac = str(pick.get("asset_class") or "").upper().strip()
            if _existing_ac in ("UNKNOWN", "NONE"):
                _scrubbed = dict(pick); _scrubbed["asset_class"] = None
                asset_class = _resolve_asset_class(_scrubbed)
            else:
                asset_class = _resolve_asset_class(pick)
            if asset_class and (not _existing_ac or _existing_ac in ("UNKNOWN", "NONE")):
                pick["asset_class"] = asset_class
            if preview_exit and entry and abs(preview_exit - entry) / entry > 0.00001:
                pnl = compute_pnl(entry, preview_exit, direction)
                outcome = classify_outcome(pnl, asset_class=asset_class or None)
                resolved.append({
                    "symbol": sym,
                    "strategy": pick.get("strategy", "?"),
                    "entry": entry,
                    "exit": preview_exit,
                    "pnl_pct": round(pnl, 6),
                    "outcome": outcome,
                    "source_system": pick.get("source_system", "?"),
                    "asset_class": asset_class,
                })
            continue

        original_status = pick.get("status", "")
        original_pnl = pick.get("pnl_pct", 0)
        updated = resolve_single_pick(pick, live_price, ohlc_window=ohlc_window)

        # Check if pick was actually resolved
        new_pnl = _safe_float(updated.get("pnl_pct"))
        if new_pnl != 0.0 or updated.get("resolved_by") == "outcome_resolver":
            resolved.append(updated)

    return resolved


# ---------------------------------------------------------------------------
# Source-specific helpers
# ---------------------------------------------------------------------------

def _load_quan_engine_closed_signals() -> list[dict]:
    """Load closed signals from quan_engine SQLite DB.
    
    Returns list of closed signals in standard format for resolution.
    """
    closed_signals = []
    if not QUAN_ENGINE_DB_PATH.exists():
        log.debug("quan_engine DB not found at %s", QUAN_ENGINE_DB_PATH)
        return closed_signals
    
    try:
        import sqlite3
        conn = sqlite3.connect(str(QUAN_ENGINE_DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM signals WHERE status = 'CLOSED' AND (pnl_pct = 0 OR pnl_pct IS NULL)"
        )
        for row in cursor.fetchall():
            sig = dict(row)
            # Normalize to standard pick format
            closed_signals.append({
                "id": sig.get("id"),
                "symbol": sig.get("symbol", ""),
                "direction": sig.get("direction", "BUY"),
                "entry_price": sig.get("entry_price", 0),
                "take_profit": sig.get("take_profit", 0),
                "stop_loss": sig.get("stop_loss", 0),
                "exit_price": sig.get("exit_price"),
                "exit_time": sig.get("exit_time"),
                "exit_reason": sig.get("exit_reason", ""),
                "pnl_pct": sig.get("pnl_pct", 0),
                "status": sig.get("status", "CLOSED"),
                "mode": sig.get("mode", ""),
                "confidence": sig.get("confidence", 0),
                "entry_time": sig.get("entry_time", ""),
                "source_system": "quan_engine",
                "_db_id": sig.get("id"),  # Track for DB update
            })
        conn.close()
        log.info("Loaded %d unresolved closed signals from quan_engine DB", len(closed_signals))
    except Exception as e:
        log.warning("Could not load quan_engine DB: %s", e)
    return closed_signals


def _update_quan_engine_db_resolved(resolved_picks: list[dict], dry_run: bool = False) -> int:
    """Update resolved picks back to quan_engine SQLite DB.
    
    Returns count of updated records.
    """
    if dry_run or not resolved_picks:
        return 0
    
    updated = 0
    try:
        import sqlite3
        conn = sqlite3.connect(str(QUAN_ENGINE_DB_PATH))
        for pick in resolved_picks:
            db_id = pick.get("_db_id")
            if not db_id:
                continue
            conn.execute("""
                UPDATE signals 
                SET pnl_pct = ?, exit_price = ?, exit_reason = ?, status = ?
                WHERE id = ?
            """, (
                pick.get("pnl_pct", 0),
                pick.get("exit_price", 0),
                pick.get("exit_reason", ""),
                pick.get("status", "CLOSED"),
                db_id
            ))
            updated += 1
        conn.commit()
        conn.close()
        log.info("Updated %d resolved signals in quan_engine DB", updated)
    except Exception as e:
        log.error("Failed to update quan_engine DB: %s", e)
    return updated


def _load_rapid_fire_closed_picks() -> list[dict]:
    """Load closed picks from rapid_fire_data/closed_picks.json.
    
    Returns list of unresolved closed picks in standard format.
    """
    closed_picks = []
    if not RAPID_FIRE_CLOSED_FILE.exists():
        log.debug("rapid_fire closed picks not found at %s", RAPID_FIRE_CLOSED_FILE)
        return closed_picks
    
    try:
        with open(RAPID_FIRE_CLOSED_FILE, "r", encoding="utf-8") as f:
            picks = json.load(f)
        for pick in picks:
            # Check if unresolved (pnl_pct is 0 or None, or exit_price equals entry)
            pnl = pick.get("pnl_pct")
            entry = _safe_float(pick.get("entry_price"))
            exit_p = _safe_float(pick.get("exit_price"))
            
            is_unresolved_pick = (
                pnl is None or 
                (isinstance(pnl, (int, float)) and abs(pnl) < 0.0001) or
                (exit_p > 0 and entry > 0 and abs(exit_p - entry) / entry < 0.00001)
            )
            
            if is_unresolved_pick and entry > 0:
                closed_picks.append({
                    "symbol": pick.get("symbol", ""),
                    "direction": pick.get("direction", "LONG"),
                    "entry_price": entry,
                    "take_profit": pick.get("take_profit") or pick.get("tp_price_1_5", 0),
                    "stop_loss": pick.get("stop_loss") or pick.get("sl_price", 0),
                    "exit_price": exit_p if exit_p > 0 else None,
                    "exit_reason": pick.get("exit_reason", ""),
                    "pnl_pct": pnl if pnl is not None else 0,
                    "status": pick.get("status", "CLOSED"),
                    "strategy": pick.get("strategy", ""),
                    "opened_at": pick.get("opened_at", ""),
                    "closed_at": pick.get("closed_at", ""),
                    "source_system": "rapid_fire",
                    "_original_pick": pick,  # Keep reference for updating
                })
        log.info("Loaded %d unresolved closed picks from rapid_fire", len(closed_picks))
    except Exception as e:
        log.warning("Could not load rapid_fire closed picks: %s", e)
    return closed_picks


def _update_rapid_fire_closed_picks(resolved_picks: list[dict], dry_run: bool = False) -> int:
    """Update resolved picks back to rapid_fire closed_picks.json.
    
    Returns count of updated records.
    """
    if dry_run or not resolved_picks or not RAPID_FIRE_CLOSED_FILE.exists():
        return 0
    
    updated = 0
    try:
        with open(RAPID_FIRE_CLOSED_FILE, "r", encoding="utf-8") as f:
            all_picks = json.load(f)
        
        # Build lookup by symbol + entry_time for matching
        resolved_lookup = {}
        for pick in resolved_picks:
            key = (pick.get("symbol"), pick.get("opened_at"))
            resolved_lookup[key] = pick
        
        # Update matching picks
        for pick in all_picks:
            key = (pick.get("symbol"), pick.get("opened_at"))
            if key in resolved_lookup:
                resolved = resolved_lookup[key]
                pick["pnl_pct"] = resolved.get("pnl_pct", 0)
                pick["exit_price"] = resolved.get("exit_price", pick.get("exit_price"))
                pick["exit_reason"] = resolved.get("exit_reason", pick.get("exit_reason", ""))
                pick["status"] = resolved.get("status", "CLOSED")
                updated += 1
        
        with open(RAPID_FIRE_CLOSED_FILE, "w", encoding="utf-8") as f:
            json.dump(all_picks, f, indent=2)
        log.info("Updated %d resolved picks in rapid_fire closed_picks.json", updated)
    except Exception as e:
        log.error("Failed to update rapid_fire closed picks: %s", e)
    return updated


def _load_rapid_fire_now_picks() -> list[dict]:
    """Load now_picks.json and find picks with PENDING outcomes.
    
    These are picks that haven't been checked against live prices yet.
    """
    pending_picks = []
    if not RAPID_FIRE_NOW_FILE.exists():
        return pending_picks
    
    try:
        with open(RAPID_FIRE_NOW_FILE, "r", encoding="utf-8") as f:
            picks = json.load(f)
        
        for pick in picks:
            # Check if either 1.5 or 2.0 outcome is still pending
            outcome_15 = pick.get("outcome_1_5", "PENDING")
            outcome_20 = pick.get("outcome_2_0", "PENDING")
            
            if outcome_15 == "PENDING" or outcome_20 == "PENDING":
                scan_time = pick.get("scan_time", "")
                pending_picks.append({
                    "symbol": pick.get("symbol", ""),
                    "direction": pick.get("direction", "LONG"),
                    "entry_price": pick.get("entry_price", 0),
                    "take_profit_15": pick.get("tp_price_1_5", 0),
                    "take_profit_20": pick.get("tp_price_2_0", 0),
                    "stop_loss": pick.get("sl_price", 0),
                    "strategy": pick.get("strategy", ""),
                    "scan_time": scan_time,
                    "run_id": pick.get("run_id", ""),
                    "source_system": "rapid_fire_now",
                    "_scan_dt": _parse_utc_timestamp(scan_time),
                    "_original_pick": pick,
                })
        log.info("Loaded %d pending picks from rapid_fire now_picks.json", len(pending_picks))
    except Exception as e:
        log.debug("Could not load rapid_fire now_picks: %s", e)
    return pending_picks


def _resolve_rapid_fire_now_pick(pick: dict, live_price: Optional[float]) -> Optional[dict]:
    """Resolve a rapid_fire now_pick against live price.
    
    Returns resolution result without modifying original pick.
    """
    if not live_price or live_price <= 0:
        return None
    
    entry = _safe_float(pick.get("entry_price"))
    if entry <= 0:
        return None
    
    direction = str(pick.get("direction", "LONG")).upper()
    tp_15 = _safe_float(pick.get("take_profit_15"))
    tp_20 = _safe_float(pick.get("take_profit_20"))
    sl = _safe_float(pick.get("stop_loss"))
    
    original = pick.get("_original_pick", {})
    result = {
        "symbol": pick.get("symbol"),
        "scan_time": pick.get("scan_time"),
        "entry_price": entry,
        "current_price": live_price,
        "outcome_1_5": original.get("outcome_1_5", "PENDING"),
        "outcome_2_0": original.get("outcome_2_0", "PENDING"),
    }
    
    # Determine if TP or SL hit based on direction
    tp_15_hit = False
    tp_20_hit = False
    sl_hit = False
    
    if direction in ("LONG", "BUY"):
        if tp_15 > 0 and live_price >= tp_15:
            tp_15_hit = True
        if tp_20 > 0 and live_price >= tp_20:
            tp_20_hit = True
        if sl > 0 and live_price <= sl:
            sl_hit = True
    else:  # SHORT/SELL
        if tp_15 > 0 and live_price <= tp_15:
            tp_15_hit = True
        if tp_20 > 0 and live_price <= tp_20:
            tp_20_hit = True
        if sl > 0 and live_price >= sl:
            sl_hit = True
    
    # Calculate PnL
    if direction in ("LONG", "BUY"):
        pnl_pct = (live_price - entry) / entry
    else:
        pnl_pct = (entry - live_price) / entry
    
    result["pnl_pct"] = round(pnl_pct, 6)

    scan_dt = pick.get("_scan_dt") or _parse_utc_timestamp(pick.get("scan_time", ""))
    aged_out = False
    if scan_dt is not None:
        age_hours = max((datetime.now(timezone.utc) - scan_dt).total_seconds() / 3600, 0.0)
        result["age_hours"] = round(age_hours, 2)
        aged_out = age_hours >= RAPID_FIRE_MAX_HOLD_HOURS

    def _set_pending(outcome_15: Optional[str] = None, outcome_20: Optional[str] = None) -> None:
        if outcome_15 is not None and result["outcome_1_5"] == "PENDING":
            result["outcome_1_5"] = outcome_15
        if outcome_20 is not None and result["outcome_2_0"] == "PENDING":
            result["outcome_2_0"] = outcome_20
    
    # Determine outcomes
    if sl_hit:
        _set_pending("LOST", "LOST")
        result["exit_reason"] = "SL_HIT"
    elif tp_20_hit:
        _set_pending("WON", "WON")
        result["exit_reason"] = "TP_2_0_HIT"
    elif tp_15_hit:
        _set_pending("WON")
        if result["outcome_2_0"] == "PENDING" and aged_out:
            _set_pending(outcome_20=classify_outcome(pnl_pct))
            result["exit_reason"] = "TIME_EXIT_AFTER_TP_1_5"
        else:
            result["exit_reason"] = "TP_1_5_HIT"
    else:
        if not aged_out:
            return None
        time_exit_outcome = classify_outcome(pnl_pct)
        _set_pending(time_exit_outcome, time_exit_outcome)
        result["exit_reason"] = "TIME_EXIT"

    if (
        result["outcome_1_5"] == original.get("outcome_1_5", "PENDING")
        and result["outcome_2_0"] == original.get("outcome_2_0", "PENDING")
    ):
        return None

    return result


def _update_rapid_fire_now_picks(resolved_results: list[dict], dry_run: bool = False) -> int:
    """Update resolved outcomes back to now_picks.json.
    
    Returns count of updated records.
    """
    if dry_run or not resolved_results or not RAPID_FIRE_NOW_FILE.exists():
        return 0
    
    updated = 0
    try:
        with open(RAPID_FIRE_NOW_FILE, "r", encoding="utf-8") as f:
            picks = json.load(f)
        
        # Build lookup
        resolved_lookup = {}
        for res in resolved_results:
            key = (res.get("symbol"), res.get("scan_time"))
            resolved_lookup[key] = res
        
        # Update matching picks
        for pick in picks:
            key = (pick.get("symbol"), pick.get("scan_time"))
            if key in resolved_lookup:
                res = resolved_lookup[key]
                if "outcome_1_5" in res:
                    pick["outcome_1_5"] = res["outcome_1_5"]
                if "outcome_2_0" in res:
                    pick["outcome_2_0"] = res["outcome_2_0"]
                if "exit_reason" in res:
                    pick["_resolved_exit_reason"] = res["exit_reason"]
                    pick["_resolved_at"] = datetime.now(timezone.utc).isoformat()
                if "pnl_pct" in res:
                    pick["_resolved_pnl_pct"] = res["pnl_pct"]
                if "current_price" in res:
                    pick["_resolved_price"] = res["current_price"]
                updated += 1
        
        with open(RAPID_FIRE_NOW_FILE, "w", encoding="utf-8") as f:
            json.dump(picks, f, indent=2)
        log.info("Updated %d resolved outcomes in rapid_fire now_picks.json", updated)
    except Exception as e:
        log.error("Failed to update rapid_fire now_picks: %s", e)
    return updated


# ---------------------------------------------------------------------------
# claude_gainer_ml — resolve ACTIVE picks against live TP/SL/expiry
# ---------------------------------------------------------------------------

def _load_claude_gainer_ml_active_picks() -> list[dict]:
    """Load ACTIVE picks from claude_gainer_ml/tracker/claude_live_picks.json.

    These picks have TP/SL targets but never get checked against live prices,
    accumulating as zombie ACTIVE entries.  Returns list of ACTIVE picks
    normalized to the standard resolver format.
    """
    active_picks: list[dict] = []
    if not CLAUDE_GAINER_ML_LIVE_PICKS.exists():
        log.debug("claude_gainer_ml live picks not found at %s", CLAUDE_GAINER_ML_LIVE_PICKS)
        return active_picks

    try:
        with open(CLAUDE_GAINER_ML_LIVE_PICKS, "r", encoding="utf-8") as f:
            data = json.load(f)
        all_picks = data.get("picks", [])
        for pick in all_picks:
            if str(pick.get("status", "")).upper() != "ACTIVE":
                continue
            entry = _safe_float(pick.get("entry_price"))
            if entry <= 0:
                continue
            price_symbol = (
                pick.get("pair")
                or pick.get("coin_id")
                or pick.get("symbol", "")
            )
            active_picks.append({
                "pick_id": pick.get("pick_id", ""),
                "symbol": price_symbol,
                "display_symbol": pick.get("symbol", "") or price_symbol,
                "direction": "LONG",  # claude_gainer_ml is always long
                "entry_price": entry,
                "take_profit": pick.get("tp1_price", 0),
                "stop_loss": pick.get("sl_price", 0),
                "tp2_price": pick.get("tp2_price", 0),
                "exit_price": pick.get("exit_price"),
                "exit_time": pick.get("exit_time"),
                "exit_reason": pick.get("exit_reason", ""),
                "pnl_pct": pick.get("pnl_pct"),
                "status": "ACTIVE",
                "entry_time": pick.get("entry_time", ""),
                "expiry_time": pick.get("expiry_time", ""),
                "source_system": "claude_gainer_ml",
                "strategy": pick.get("source", "claude_gainer_ml"),
                "category": "crypto",
                "_original_pick": pick,
            })
        log.info("Loaded %d ACTIVE picks from claude_gainer_ml", len(active_picks))
    except Exception as e:
        log.warning("Could not load claude_gainer_ml live picks: %s", e)
    return active_picks


def _resolve_claude_gainer_ml_pick(pick: dict, live_price: Optional[float]) -> bool:
    """Check a claude_gainer_ml ACTIVE pick against live price for TP/SL/expiry.

    Modifies the _original_pick in-place if resolved.
    Returns True if the pick was resolved.
    """
    if not live_price or live_price <= 0:
        return False

    entry = _safe_float(pick.get("entry_price"))
    if entry <= 0:
        return False

    original = pick.get("_original_pick", {})
    tp1 = _safe_float(pick.get("take_profit"))
    tp2 = _safe_float(pick.get("tp2_price"))
    sl = _safe_float(pick.get("stop_loss"))
    direction = str(pick.get("direction", pick.get("signal_direction", "LONG"))).upper()
    is_short = direction in ("SHORT", "SELL")
    now = datetime.now(timezone.utc)

    exit_price = None
    exit_reason = None

    # C1 fix (reports/crypto_edge_artifact_audit_2026_05_17.md): credit the real
    # observed live_price, not the nominal sl/tp1/tp2. Crediting the nominal
    # level pinned every win's pnl_pct to exactly the TP distance — the
    # "ghost row" artifact. live_price is the genuine observed witness.
    # Direction-aware TP/SL: SHORT positions use inverted comparisons.
    # Bug fix: prior code used live_price <= sl for ALL directions — SHORT stops
    # never fired when price rose above SL (e.g. APEUSDT SHORT: SL=$0.121,
    # exit=$0.2098 = 73% past stop). Mirrors direction logic at lines 1378-1391.
    if sl > 0 and (live_price >= sl if is_short else live_price <= sl):
        exit_price = live_price
        exit_reason = "STOP_LOSS"
        original["sl_hit"] = True
    # Check TP2 hit
    elif tp2 > 0 and (live_price <= tp2 if is_short else live_price >= tp2):
        exit_price = live_price
        exit_reason = "TP2_HIT"
        original["tp1_hit"] = True
        original["tp2_hit"] = True
    # Check TP1 hit
    elif tp1 > 0 and (live_price <= tp1 if is_short else live_price >= tp1):
        exit_price = live_price
        exit_reason = "TP1_HIT"
        original["tp1_hit"] = True
    else:
        # Check expiry
        expiry_str = pick.get("expiry_time", "")
        expiry_dt = _parse_utc_timestamp(expiry_str) if expiry_str else None
        if expiry_dt and now > expiry_dt:
            exit_price = live_price
            exit_reason = "EXPIRED"

    if exit_price is None:
        return False

    # Compute PnL — direction-aware (SHORT: entry-exit, LONG: exit-entry)
    if is_short:
        pnl_pct = round((entry - exit_price) / entry * 100, 2)
    else:
        pnl_pct = round((exit_price - entry) / entry * 100, 2)

    # Update the original pick in-place
    # v2.3 (2026-05-27): EXPIRED/TIME_EXIT/MAX_HOLD exits must stay
    # as EXPIRED, not RESOLVED. See reports/2026-05-25_crypto_78pct_wr_verification.md
    _is_expired_exit = exit_reason and any(
        str(exit_reason).upper().startswith(prefix)
        for prefix in ("EXPIRED", "TIME_EXIT", "MAX_HOLD")
    )
    original["status"] = "EXPIRED" if _is_expired_exit else "RESOLVED"
    original["exit_price"] = exit_price
    original["exit_time"] = now.isoformat()
    original["exit_reason"] = exit_reason
    original["pnl_pct"] = pnl_pct
    return True


def _save_claude_gainer_ml_picks(data: dict, resolved_count: int) -> None:
    """Save updated claude_gainer_ml live picks back to disk."""
    if resolved_count <= 0:
        return
    try:
        # Recount active/resolved
        picks = data.get("picks", [])
        active = sum(1 for p in picks if str(p.get("status", "")).upper() == "ACTIVE")
        resolved = sum(1 for p in picks if str(p.get("status", "")).upper() == "RESOLVED")
        data["total_active"] = active
        data["total_resolved"] = resolved
        data["updated_at"] = datetime.now(timezone.utc).isoformat()

        with open(CLAUDE_GAINER_ML_LIVE_PICKS, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        log.info("Saved claude_gainer_ml live picks (%d active, %d resolved)", active, resolved)
    except Exception as e:
        log.error("Failed to save claude_gainer_ml live picks: %s", e)


def _sync_resolved_to_mysql_trading_picks(resolved_picks: list[dict]) -> int:
    """Write resolved outcomes back to trading_picks table."""
    if not resolved_picks:
        return 0

    # Prefer canonical close API when available.
    try:
        from audit_trail.mysql_client import mysql_close_trade as _mysql_close_trade
    except Exception:
        _mysql_close_trade = None

    if _mysql_close_trade is not None:
        updated = 0
        for pick in resolved_picks:
            symbol = str(pick.get("symbol", "") or "")
            direction = str(pick.get("direction", "LONG") or "LONG")
            if not symbol:
                continue
            affected = _mysql_close_trade(
                symbol=symbol,
                direction=direction,
                exit_price=pick.get("exit_price"),
                exit_reason=pick.get("exit_reason"),
                pnl_pct=pick.get("pnl_pct"),
                closed_at=(pick.get("closed_at") or pick.get("exit_date")),
            )
            if affected and affected > 0:
                updated += 1
        return updated

    try:
        import pymysql
    except ImportError:
        log.warning("pymysql missing; skipping trading_picks MySQL sync")
        return 0

    db_pass = (
        os.environ.get("DB_PASS")
        or os.environ.get("AUDIT_DB_PASS")
        or os.environ.get("MYSQL_PASSWORD")
        or "stocks"
    )
    try:
        conn = pymysql.connect(
            host=os.environ.get("DB_HOST", "mysql.50webs.com"),
            port=int(os.environ.get("DB_PORT", "3306")),
            user=os.environ.get("DB_USER", "ejaguiar1_stocks"),
            password=db_pass,
            database=os.environ.get("DB_NAME", "ejaguiar1_stocks"),
            connect_timeout=10,
            autocommit=True,
            charset="utf8mb4",
        )
    except Exception as e:
        log.warning("MySQL connect failed for trading_picks sync: %s", e)
        return 0

    def _canonical_status(pick: dict) -> str:
        exit_reason = str(pick.get("exit_reason", "") or "").upper()
        pnl_raw = pick.get("pnl_pct", 0) or 0
        try:
            pnl_val = float(pnl_raw)
        except (ValueError, TypeError):
            pnl_val = 0.0

        # Sign-coherence guard: when exit_reason claims TP but pnl is negative
        # (or SL but pnl is positive), trust the pnl sign — source supplied
        # contradictory reason+pnl, which produced the WON-vs-PnL contradiction
        # flagged at audit_dashboard/data/db_health.json::won_pnl_contradiction.
        tp_reasons = ("TP", "TP_HIT", "TP_HIT_RESOLVED", "TP2_HIT", "TP1_HIT")
        sl_reasons = ("SL", "SL_HIT", "SL_HIT_RESOLVED", "STOP_LOSS", "ATR_TRAIL", "TRAIL", "TRAIL_SL")
        if exit_reason in tp_reasons:
            if pnl_val < 0:
                log.warning("won_pnl_contradiction: exit_reason=%s but pnl_pct=%s for pick id=%s — trusting pnl sign",
                            exit_reason, pnl_val, pick.get("id"))
                return "LOST"
            return "WON"
        if exit_reason in sl_reasons:
            if pnl_val > 0:
                log.warning("won_pnl_contradiction: exit_reason=%s but pnl_pct=%s for pick id=%s — trusting pnl sign",
                            exit_reason, pnl_val, pick.get("id"))
                return "WON"
            return "LOST"
        if exit_reason in ("TIME_EXIT", "MAX_HOLD", "EXPIRED", "FORCE_CLOSED_TOXIC"):
            return "EXPIRED"
        if pnl_val > 0:
            return "WON"
        if pnl_val < 0:
            return "LOST"
        return "EXPIRED"

    cur = conn.cursor()
    updated = 0
    for pick in resolved_picks:
        pick_id = str(pick.get("id", "") or "")[:100]
        if not pick_id:
            continue

        exit_reason = str(pick.get("exit_reason", "") or "").upper()
        closed_at_raw = pick.get("closed_at") or pick.get("exit_date")
        closed_at = closed_at_raw
        if isinstance(closed_at_raw, str) and "T" in closed_at_raw:
            try:
                closed_at = datetime.fromisoformat(
                    closed_at_raw.replace("Z", "+00:00")
                ).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                closed_at = None

        pnl_raw = pick.get("pnl_pct", 0) or 0
        try:
            pnl = round(float(pnl_raw), 4)
        except (ValueError, TypeError):
            pnl = 0.0

        try:
            exit_price_raw = pick.get("exit_price")
            try:
                exit_price = float(exit_price_raw) if exit_price_raw is not None else None
            except (ValueError, TypeError):
                exit_price = None
            cur.execute(
                """UPDATE trading_picks
                   SET status=%s, pnl_pct=%s, exit_price=%s, exit_reason=%s, closed_at=%s
                   WHERE id=%s AND status NOT IN ('WON','LOST','EXPIRED')""",
                (_canonical_status(pick), pnl, exit_price, exit_reason, closed_at, pick_id),
            )
            if cur.rowcount > 0:
                updated += 1
        except Exception as e:
            log.debug("trading_picks update failed for %s: %s", pick_id, e)

    conn.close()
    return updated


# ---------------------------------------------------------------------------
# at_pick_outcomes MySQL upsert (opt-in)
# ---------------------------------------------------------------------------
# Kill-switch env: PICK_OUTCOMES_MYSQL_ENABLED=0  (default OFF)
# Enable via: PICK_OUTCOMES_MYSQL_ENABLED=1  OR  --mysql CLI flag.
#
# Schema reference: audit_trail/mysql_schema.sql → at_pick_outcomes
# Wiring: called at the end of run_outcome_resolver() when flag/env active.
# ---------------------------------------------------------------------------

def _write_outcomes_to_mysql(resolved_picks: list[dict]) -> int:
    """Upsert resolved picks into at_pick_outcomes.

    Args:
        resolved_picks: list of pick dicts that have just been resolved.

    Returns:
        Number of rows upserted (0 if skipped/failed).
    """
    # Kill-switch check first (default OFF — opt-in only)
    enabled_env = os.environ.get("PICK_OUTCOMES_MYSQL_ENABLED", "0").strip().lower()
    if enabled_env not in ("1", "true", "yes", "on"):
        return 0

    if not resolved_picks:
        return 0

    try:
        import pymysql  # type: ignore
    except ImportError:
        log.warning("pymysql not installed; skipping at_pick_outcomes MySQL upsert")
        return 0

    db_pass = (
        os.environ.get("DB_PASS_STOCKS")
        or os.environ.get("MYSQL_PASSWORD")
        or os.environ.get("AUDIT_DB_PASS")
        or os.environ.get("DB_PASS")
        or "stocks"
    )

    try:
        conn = pymysql.connect(
            host=os.environ.get("DB_HOST", "mysql.50webs.com"),
            port=int(os.environ.get("DB_PORT", "3306")),
            user=os.environ.get("DB_USER", "ejaguiar1_stocks"),
            password=db_pass,
            database=os.environ.get("DB_NAME", "ejaguiar1_stocks"),
            connect_timeout=10,
            autocommit=True,
            charset="utf8mb4",
        )
    except Exception as e:
        log.warning("at_pick_outcomes: MySQL connect failed: %s", e)
        return 0

    # Status enum for at_pick_outcomes: OPEN | WON | LOST | EXPIRED | FLAT
    _STATUS_MAP = {
        "WON":      "WON",
        "LOST":     "LOST",
        "CLOSED":   "EXPIRED",   # generic CLOSED → EXPIRED
        "EXPIRED":  "EXPIRED",
        "FLAT":     "FLAT",
        "OPEN":     "OPEN",
    }

    # resolution_method enum: TP_HIT | SL_HIT | TIME_EXPIRED | MANUAL
    _TP_REASONS = frozenset({"TP", "TP_HIT", "TP_HIT_RESOLVED", "TP2_HIT", "TP1_HIT"})
    _SL_REASONS = frozenset({"SL", "SL_HIT", "SL_HIT_RESOLVED", "STOP_LOSS",
                              "ATR_TRAIL", "TRAIL", "TRAIL_SL"})
    _TIME_REASONS = frozenset({"TIME_EXIT", "MAX_HOLD", "EXPIRED", "FORCE_CLOSED_TOXIC",
                                "RESOLVE_FAILED_MAX_RETRIES"})

    def _map_resolution_method(exit_reason: str) -> Optional[str]:
        r = str(exit_reason or "").upper()
        if r in _TP_REASONS:
            return "TP_HIT"
        if r in _SL_REASONS:
            return "SL_HIT"
        if r in _TIME_REASONS:
            return "TIME_EXPIRED"
        return "MANUAL"

    UPSERT_SQL = (
        "INSERT INTO at_pick_outcomes "
        "(pick_id, symbol, strategy, asset_class, status, resolution_method, "
        " pnl_pct, resolved_at, resolver_version) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) "
        "ON DUPLICATE KEY UPDATE "
        "  status=VALUES(status), "
        "  pnl_pct=VALUES(pnl_pct), "
        "  resolved_at=VALUES(resolved_at), "
        "  resolution_method=VALUES(resolution_method)"
    )

    cur = conn.cursor()
    upserted = 0
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    for pick in resolved_picks:
        # P0 §15 dedup harmonization (TON-validated 2026-06-01): use canonical helper
        from alpha_engine.dedup import build_canonical_outcomes_pick_id
        pick_id = build_canonical_outcomes_pick_id(pick)
        if not pick_id:
            continue

        symbol = str(pick.get("symbol", "") or "")[:50]
        strategy = str(pick.get("strategy", pick.get("source_system", "")) or "")[:200]
        asset_class = str(pick.get("asset_class", pick.get("category", "UNKNOWN")) or "UNKNOWN")[:20]

        raw_status = str(pick.get("status", pick.get("outcome", "FLAT")) or "FLAT").upper()
        status = _STATUS_MAP.get(raw_status, "FLAT")

        exit_reason = str(pick.get("exit_reason", "") or "")
        resolution_method = _map_resolution_method(exit_reason)

        pnl_raw = pick.get("pnl_pct", 0) or 0
        try:
            pnl_pct = round(float(pnl_raw), 4)
        except (ValueError, TypeError):
            pnl_pct = 0.0

        # resolved_at: prefer closed_at/exit_date, else now
        resolved_at_raw = pick.get("closed_at") or pick.get("exit_date")
        if resolved_at_raw and isinstance(resolved_at_raw, str) and "T" in resolved_at_raw:
            try:
                resolved_at = datetime.fromisoformat(
                    resolved_at_raw.replace("Z", "+00:00")
                ).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                resolved_at = now_str
        else:
            resolved_at = now_str

        try:
            cur.execute(
                UPSERT_SQL,
                (pick_id, symbol, strategy, asset_class, status, resolution_method,
                 pnl_pct, resolved_at, RESOLVER_VERSION),
            )
            upserted += 1
        except Exception as e:
            log.debug("at_pick_outcomes upsert failed for pick_id=%s: %s", pick_id, e)

    conn.close()
    log.info("at_pick_outcomes: upserted %d rows", upserted)
    return upserted


# ---------------------------------------------------------------------------
# Full run
# ---------------------------------------------------------------------------
def run_outcome_resolver(dry_run: bool = False, mysql: bool = False) -> dict:
    """Full outcome resolution cycle.

    1. Load closed picks from closed_picks.json
    2. Merge any from dashboard_payload.json (recent_closed)
    3. Resolve unresolved picks
    4. Save back to closed_picks.json
    5. Return report

    Args:
        dry_run: preview only, no file/DB writes.
        mysql:   when True (or PICK_OUTCOMES_MYSQL_ENABLED=1), upserts resolved
                 picks into at_pick_outcomes after batch resolution.

    Returns dict with keys: total_closed, unresolved_found, resolved_count,
    win_rate, per_system_breakdown.
    """
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_closed": 0,
        "unresolved_found": 0,
        "resolved_count": 0,
        "won": 0,
        "lost": 0,
        "flat": 0,
        "win_rate": 0.0,
        "per_system": {},
        "no_price_available": 0,
    }

    # 1. Load closed picks
    closed_picks = []
    if CLOSED_PICKS_FILE.exists():
        try:
            with open(CLOSED_PICKS_FILE, "r", encoding="utf-8") as f:
                closed_picks = json.load(f)
            log.info("Loaded %d picks from closed_picks.json", len(closed_picks))
        except Exception as e:
            log.error("Failed to load closed_picks.json: %s", e)
            return report

    # 2. Merge dashboard payload recent_closed (avoid duplicates)
    if DASHBOARD_PAYLOAD_FILE.exists():
        try:
            with open(DASHBOARD_PAYLOAD_FILE, "r", encoding="utf-8") as f:
                payload = json.load(f)
            recent_closed = payload.get("recent_closed", [])
            if recent_closed:
                existing_ids = {p.get("id", "") for p in closed_picks if p.get("id")}
                merged = 0
                for pick in recent_closed:
                    pid = pick.get("id", "")
                    if pid and pid not in existing_ids:
                        # P0-A (2026-05-06): preserve score fields so
                        # closed_picks.json inherits scoring metadata.
                        _preserve_score_fields(pick, pick)
                        closed_picks.append(pick)
                        existing_ids.add(pid)
                        merged += 1
                if merged:
                    log.info("Merged %d picks from dashboard_payload.json", merged)
        except Exception as e:
            log.warning("Could not load dashboard_payload.json: %s", e)

    # 2b. Merge rapid_fire closed picks (have exit_price == entry_price, pnl 0%)
    rapid_fire_resolved = 0
    if RAPID_FIRE_CLOSED_FILE.exists():
        try:
            with open(RAPID_FIRE_CLOSED_FILE, "r", encoding="utf-8") as f:
                rf_closed = json.load(f)
            if rf_closed:
                # Build dedup key: symbol + opened_at + strategy
                def _pick_key(p):
                    return (p.get("symbol", ""), p.get("opened_at", p.get("scan_time", "")),
                            p.get("strategy", ""))
                existing_keys = {_pick_key(p) for p in closed_picks}
                merged_rf = 0
                for pick in rf_closed:
                    # Normalize rapid_fire field names to what resolver expects
                    if "tp_price_1_5" in pick and "take_profit" not in pick:
                        pick["take_profit"] = pick["tp_price_1_5"]
                    if "sl_price" in pick and "stop_loss" not in pick:
                        pick["stop_loss"] = pick["sl_price"]
                    if "source_system" not in pick:
                        pick["source_system"] = "rapid_fire"
                    key = _pick_key(pick)
                    if key not in existing_keys:
                        closed_picks.append(pick)
                        existing_keys.add(key)
                        merged_rf += 1
                if merged_rf:
                    log.info("Merged %d picks from rapid_fire closed_picks.json", merged_rf)
                    rapid_fire_resolved = merged_rf
        except Exception as e:
            log.warning("Could not load rapid_fire closed_picks.json: %s", e)

    # 2c. Merge quan_engine closed picks from active_signals.json
    quan_resolved = 0
    if QUAN_ENGINE_SIGNALS_PATH.exists():
        try:
            with open(QUAN_ENGINE_SIGNALS_PATH, "r", encoding="utf-8") as f:
                qe_data = json.load(f)
            qe_closed = qe_data.get("closed_picks", [])
            if qe_closed:
                def _qe_key(p):
                    return (p.get("symbol", ""), str(p.get("id", "")),
                            p.get("entry_time", ""))
                existing_keys_qe = {_qe_key(p) for p in closed_picks
                                    if p.get("source_system") == "quan_engine"}
                merged_qe = 0
                for pick in qe_closed:
                    # Normalize field names
                    if "source_system" not in pick:
                        pick["source_system"] = "quan_engine"
                    if "opened_at" not in pick and "entry_time" in pick:
                        pick["opened_at"] = pick["entry_time"]
                    if "closed_at" not in pick and "exit_time" in pick:
                        pick["closed_at"] = pick["exit_time"]
                    key = _qe_key(pick)
                    if key not in existing_keys_qe:
                        closed_picks.append(pick)
                        existing_keys_qe.add(key)
                        merged_qe += 1
                if merged_qe:
                    log.info("Merged %d picks from quan_engine active_signals.json", merged_qe)
                    quan_resolved = merged_qe
        except Exception as e:
            log.warning("Could not load quan_engine active_signals.json: %s", e)

    report["total_closed"] = len(closed_picks)
    report["rapid_fire_merged"] = rapid_fire_resolved
    report["quan_engine_merged"] = quan_resolved

    # Count unresolved before resolving
    unresolved_before = sum(1 for p in closed_picks if is_unresolved(p))
    report["unresolved_found"] = unresolved_before

    resolved = []
    if unresolved_before == 0:
        log.info("All %d closed picks already have outcomes. Nothing to resolve.", len(closed_picks))
    else:
        log.info("Found %d unresolved picks. Starting resolution...", unresolved_before)

        # 3. Resolve
        resolved = resolve_outcomes(closed_picks, fetch_prices=True, dry_run=dry_run)

        # 4. Build report
        per_system: dict[str, dict] = defaultdict(lambda: {"resolved": 0, "won": 0, "lost": 0, "flat": 0})
        won = lost = flat = 0

        for pick in resolved:
            outcome = str(pick.get("status", pick.get("outcome", ""))).upper()
            system = pick.get("source_system", pick.get("strategy", "unknown"))

            if outcome == "WON":
                won += 1
                per_system[system]["won"] += 1
            elif outcome == "LOST":
                lost += 1
                per_system[system]["lost"] += 1
            else:
                flat += 1
                per_system[system]["flat"] += 1
            per_system[system]["resolved"] += 1

        report["resolved_count"] = len(resolved)
        report["won"] = won
        report["lost"] = lost
        report["flat"] = flat
        report["win_rate"] = round(won / max(won + lost, 1) * 100, 1)
        report["no_price_available"] = unresolved_before - len(resolved)

        # Per-system breakdown with WR
        for sys_name, counts in per_system.items():
            w = counts["won"]
            l = counts["lost"]
            counts["win_rate"] = round(w / max(w + l, 1) * 100, 1)
        report["per_system"] = dict(per_system)

        # 5. Save back to closed_picks.json (unless dry run)
        if not dry_run and resolved:
            try:
                # Sanitize NaN/Inf
                def _sanitize(obj):
                    if isinstance(obj, dict):
                        return {k: _sanitize(v) for k, v in obj.items()}
                    if isinstance(obj, list):
                        return [_sanitize(v) for v in obj]
                    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
                        return None
                    return obj

                # A9 (2026-05-17): emitter/resolver idempotency. Drop
                # duplicate re-emissions (fresh id, same signal) before
                # persisting. Env-gated (EMITTER_DEDUP), fail-soft.
                try:
                    from alpha_engine.emitter_dedup import (
                        dedup_closed_picks as _a9_dedup,
                    )
                    closed_picks, _ = _a9_dedup(
                        closed_picks, label="closed_picks.json")
                except Exception as _a9_err:
                    log.warning("EMITTER_DEDUP guard failed: %s", _a9_err)

                with open(CLOSED_PICKS_FILE, "w", encoding="utf-8") as f:
                    json.dump(_sanitize(closed_picks), f, indent=2)
                log.info("Saved %d picks to closed_picks.json (%d resolved)",
                         len(closed_picks), len(resolved))
            except Exception as e:
                log.error("Failed to save closed_picks.json: %s", e)

            # 5b. Write resolved picks back to their source system files
            rf_resolved = [p for p in resolved if p.get("source_system") == "rapid_fire"]
            if rf_resolved:
                rf_updated = _update_rapid_fire_closed_picks(rf_resolved, dry_run=dry_run)
                report["rapid_fire_updated"] = rf_updated

            qe_resolved = [p for p in resolved if p.get("source_system") == "quan_engine"]
            if qe_resolved:
                qe_updated = _update_quan_engine_db_resolved(qe_resolved, dry_run=dry_run)
                report["quan_engine_updated"] = qe_updated

    # 6. Resolve quan_engine DB closed signals (separate from main closed_picks)
    log.info("Checking quan_engine DB for unresolved closed signals...")
    qe_closed_signals = _load_quan_engine_closed_signals()
    if qe_closed_signals:
        qe_resolved = resolve_outcomes(qe_closed_signals, fetch_prices=True, dry_run=dry_run)
        if qe_resolved and not dry_run:
            _update_quan_engine_db_resolved(qe_resolved, dry_run=dry_run)
        report["quan_engine_resolved"] = len(qe_resolved)
        log.info("Resolved %d quan_engine DB signals", len(qe_resolved))
    else:
        report["quan_engine_resolved"] = 0

    # 7. Resolve rapid_fire closed picks with exit_price == entry_price
    log.info("Checking rapid_fire closed_picks.json for unresolved picks...")
    rf_closed_picks = _load_rapid_fire_closed_picks()
    if rf_closed_picks:
        rf_resolved = resolve_outcomes(rf_closed_picks, fetch_prices=True, dry_run=dry_run)
        if rf_resolved and not dry_run:
            _update_rapid_fire_closed_picks(rf_resolved, dry_run=dry_run)
        report["rapid_fire_closed_resolved"] = len(rf_resolved)
        log.info("Resolved %d rapid_fire closed picks", len(rf_resolved))
    else:
        report["rapid_fire_closed_resolved"] = 0

    # 8. Resolve rapid_fire now_picks pending outcomes
    log.info("Checking rapid_fire now_picks.json for pending outcomes...")
    rf_now_picks = _load_rapid_fire_now_picks()
    if rf_now_picks:
        # Group by symbol to batch price fetches
        by_symbol: dict[str, list[dict]] = defaultdict(list)
        for pick in rf_now_picks:
            sym = pick.get("symbol", "UNKNOWN")
            by_symbol[sym].append(pick)
        
        # Fetch prices
        price_cache: dict[str, Optional[float]] = {}
        for sym, picks_for_sym in by_symbol.items():
            price = fetch_price_for_pick(picks_for_sym[0])
            price_cache[sym] = price
            time.sleep(0.1)  # Rate limit
        
        # Resolve each pick
        rf_now_resolved = []
        for pick in rf_now_picks:
            sym = pick.get("symbol", "UNKNOWN")
            live_price = price_cache.get(sym)
            result = _resolve_rapid_fire_now_pick(pick, live_price)
            if result:
                rf_now_resolved.append(result)
        
        if rf_now_resolved and not dry_run:
            _update_rapid_fire_now_picks(rf_now_resolved, dry_run=dry_run)
        report["rapid_fire_now_resolved"] = len(rf_now_resolved)
        log.info("Resolved %d rapid_fire now picks", len(rf_now_resolved))
    else:
        report["rapid_fire_now_resolved"] = 0

    # 9. Resolve claude_gainer_ml ACTIVE picks (zombie picks with no PnL tracking)
    log.info("Checking claude_gainer_ml for zombie ACTIVE picks...")
    cgml_active = _load_claude_gainer_ml_active_picks()
    cgml_resolved_count = 0
    if cgml_active:
        # Group by symbol to batch price fetches
        cgml_by_symbol: dict[str, list[dict]] = defaultdict(list)
        for pick in cgml_active:
            sym = pick.get("symbol", "UNKNOWN")
            cgml_by_symbol[sym].append(pick)

        # Fetch prices
        cgml_price_cache: dict[str, Optional[float]] = {}
        for sym, picks_for_sym in cgml_by_symbol.items():
            price = fetch_price_for_pick(picks_for_sym[0])
            cgml_price_cache[sym] = price
            time.sleep(0.1)

        # Resolve each pick
        for pick in cgml_active:
            sym = pick.get("symbol", "UNKNOWN")
            live_price = cgml_price_cache.get(sym)
            if not dry_run and _resolve_claude_gainer_ml_pick(pick, live_price):
                cgml_resolved_count += 1

        # Save updated file
        if cgml_resolved_count > 0 and not dry_run:
            try:
                with open(CLAUDE_GAINER_ML_LIVE_PICKS, "r", encoding="utf-8") as f:
                    cgml_data = json.load(f)
                # Apply resolutions from _original_pick refs back to file data
                resolved_map = {}
                for pick in cgml_active:
                    orig = pick.get("_original_pick", {})
                    if orig.get("status") == "RESOLVED" and orig.get("pick_id"):
                        resolved_map[orig["pick_id"]] = orig
                if resolved_map:
                    for p in cgml_data.get("picks", []):
                        pid = p.get("pick_id", "")
                        if pid in resolved_map:
                            r = resolved_map[pid]
                            p["status"] = r["status"]
                            p["exit_price"] = r["exit_price"]
                            p["exit_time"] = r["exit_time"]
                            p["exit_reason"] = r["exit_reason"]
                            p["pnl_pct"] = r["pnl_pct"]
                            p["sl_hit"] = r.get("sl_hit", p.get("sl_hit", False))
                            p["tp1_hit"] = r.get("tp1_hit", p.get("tp1_hit", False))
                            p["tp2_hit"] = r.get("tp2_hit", p.get("tp2_hit", False))
                _save_claude_gainer_ml_picks(cgml_data, cgml_resolved_count)
            except Exception as e:
                log.error("Failed to save claude_gainer_ml picks: %s", e)
        log.info("Resolved %d claude_gainer_ml ACTIVE picks", cgml_resolved_count)
    report["claude_gainer_ml_resolved"] = cgml_resolved_count

    # 10. Save resolver log
    try:
        log_entries = []
        if RESOLVER_LOG_FILE.exists():
            with open(RESOLVER_LOG_FILE, "r", encoding="utf-8") as f:
                log_entries = json.load(f)
        log_entries.append(report)
        # Keep last 100 entries
        if len(log_entries) > 100:
            log_entries = log_entries[-100:]
        with open(RESOLVER_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(log_entries, f, indent=2)
    except Exception as e:
        log.warning("Could not save resolver log: %s", e)

    if not dry_run and resolved:
        report["trading_picks_mysql_updates"] = _sync_resolved_to_mysql_trading_picks(resolved)
    else:
        report["trading_picks_mysql_updates"] = 0

    # at_pick_outcomes upsert — opt-in via --mysql flag or PICK_OUTCOMES_MYSQL_ENABLED=1
    # Default OFF; set env to activate without the flag.
    mysql_env = os.environ.get("PICK_OUTCOMES_MYSQL_ENABLED", "0").strip().lower()
    mysql_active = mysql or mysql_env in ("1", "true", "yes", "on")
    if mysql_active and not dry_run and resolved:
        # Temporarily set the env so _write_outcomes_to_mysql sees it enabled
        _prev_env = os.environ.get("PICK_OUTCOMES_MYSQL_ENABLED", "0")
        os.environ["PICK_OUTCOMES_MYSQL_ENABLED"] = "1"
        try:
            report["pick_outcomes_mysql_upserted"] = _write_outcomes_to_mysql(resolved)
        finally:
            os.environ["PICK_OUTCOMES_MYSQL_ENABLED"] = _prev_env
    else:
        report["pick_outcomes_mysql_upserted"] = 0

    return report


def print_report(report: dict) -> None:
    """Print a human-readable report."""
    print("\n" + "=" * 70)
    print("OUTCOME RESOLVER REPORT")
    print("=" * 70)
    print(f"  Total closed picks:    {report['total_closed']}")
    print(f"  Unresolved found:      {report['unresolved_found']}")
    print(f"  Successfully resolved: {report['resolved_count']}")
    print(f"  No price available:    {report['no_price_available']}")
    print(f"  WON:  {report['won']}")
    print(f"  LOST: {report['lost']}")
    print(f"  FLAT: {report['flat']}")
    print(f"  Win Rate (resolved):   {report['win_rate']}%")
    
    # Source-specific resolution stats
    qe_resolved = report.get("quan_engine_resolved", 0)
    rf_closed_resolved = report.get("rapid_fire_closed_resolved", 0)
    rf_now_resolved = report.get("rapid_fire_now_resolved", 0)
    cgml_resolved = report.get("claude_gainer_ml_resolved", 0)

    if qe_resolved or rf_closed_resolved or rf_now_resolved or cgml_resolved:
        print("\n  Source-Specific Resolution:")
        if qe_resolved:
            print(f"    quan_engine DB:        {qe_resolved} resolved")
        if rf_closed_resolved:
            print(f"    rapid_fire closed:     {rf_closed_resolved} resolved")
        if rf_now_resolved:
            print(f"    rapid_fire now:        {rf_now_resolved} resolved")
        if cgml_resolved:
            print(f"    claude_gainer_ml:      {cgml_resolved} resolved")

    if report["per_system"]:
        print("\n  Per-System Breakdown:")
        print(f"  {'System':<35s} {'Resolved':>8s} {'Won':>5s} {'Lost':>5s} {'Flat':>5s} {'WR':>7s}")
        print("  " + "-" * 65)
        for sys_name, counts in sorted(report["per_system"].items(),
                                        key=lambda x: -x[1]["resolved"]):
            print(f"  {sys_name[:35]:<35s} {counts['resolved']:>8d} "
                  f"{counts['won']:>5d} {counts['lost']:>5d} {counts['flat']:>5d} "
                  f"{counts['win_rate']:>6.1f}%")
    print("=" * 70)


# Score fields to preserve when a pick transitions from ACTIVE→CLOSED.
# These are written by smart_picks_engine / trust_score / ml models while
# a pick is live, and must survive the transition so downstream consumers
# (feature_health.py, institutional_scorecard.py, model_calibration.py)
# can compute score→WR correlations on the closed set.
#
# 2026-05-06: closed_picks.json had 0/7,867 picks with these fields populated
# (elite_score was present on 6,383, but score/trust_score/smart_score/grade/
# 2026-05-07: Add method_a_score + ml_composite_score (actual scoring fields)
# and ml_score (alias). strat_fwd_wr removed — it is nested under
# forward_validation (pick["forward_validation"]["strat_fwd_wr"]), not a
# top-level key, so the old top-level lookup always returned None.
SCORE_FIELDS_TO_PRESERVE = (
    "score",
    "trust_score",
    "smart_score",
    "grade",
    "trust_tier",
    # Written by scanner.py / ml_ranker.py at pick creation time.
    "elite_score",
    "method_a_score",
    "ml_composite_score",
    # Alias for ml_composite_score — some pipelines use this name.
    "ml_score",
)


def _preserve_score_fields(source: dict, target: dict) -> None:
    """Copy score/trust/smart/grade fields from source to target.

    Call this whenever a pick transitions from ACTIVE→CLOSED or when a
    new pick is added to closed_picks.json, so that scoring metadata
    computed by smart_picks_engine / trust_score / ml models survives
    the transition.

    Only writes a field if it has a non-null, non-zero, non-empty value
    in the source — this avoids clobbering an existing better value in
    the target.
    """
    for field in SCORE_FIELDS_TO_PRESERVE:
        val = source.get(field)
        if val is not None and val != 0 and val != "":
            if field not in target or target.get(field) in (None, 0, ""):
                target[field] = val

# ---------------------------------------------------------------------------
# Non-Crypto Active Pick TP/SL Resolver (C1 fix — 2026-04-02)
# ---------------------------------------------------------------------------
# Problem: Futures/Commodity have 0 closures, Forex only 7/160.
# Root cause: No pipeline checks ACTIVE non-crypto picks against live prices.
# This function loads active picks, fetches yfinance prices, and closes
# any that have hit TP or SL.

ACTIVE_PICKS_FILE = DATA_DIR / "active_picks.json"
MULTI_ASSET_PICKS = Path(__file__).resolve().parent.parent / "multi_asset" / "data" / "active_picks.json"
FOREX_FUTURES_FILE = Path(__file__).resolve().parent.parent / "audit_dashboard" / "data" / "forex_futures_picks.json"
BOND_SCANNER_FILE = DATA_DIR / "scanner_output" / "active_picks_bond.json"

# ETF pick sources (2026-05-18, M-113): ETF picks have valid TP/SL but were never
# included in resolve_active_non_crypto() source list → 0 ETF picks ever reached
# closed_picks.json → ETF PF registry n=0 → ETF appears dead despite WR=61%/PF=2.
ETF_SECTOR_PICKS_FILE = DATA_DIR / "etf_sector_picks.json"
ETF_DECAY_PICKS_FILE = DATA_DIR / "etf_decay_picks.json"
ETF_LEVERAGED_DECAY_FILE = DATA_DIR / "leveraged_etf_decay_picks.json"
ETF_SCANNER_FILE = DATA_DIR / "scanner_output" / "active_picks_etf.json"


def resolve_active_non_crypto(dry_run: bool = False) -> dict:
    """Check active non-crypto picks against live prices for TP/SL hits.

    Loads from multiple sources, fetches yfinance prices, and resolves
    any picks where price has crossed TP or SL.
    """
    report = {
        "checked": 0, "resolved": 0, "tp_hits": 0, "sl_hits": 0,
        "no_price": 0, "by_asset_class": {},
    }

    # Load active picks from multiple sources
    active_non_crypto = []
    for source_file in [
        ACTIVE_PICKS_FILE, MULTI_ASSET_PICKS, FOREX_FUTURES_FILE, BOND_SCANNER_FILE,
        # ETF pick files (M-113 2026-05-18): sector / decay / leveraged-decay / scanner
        ETF_SECTOR_PICKS_FILE, ETF_DECAY_PICKS_FILE,
        ETF_LEVERAGED_DECAY_FILE, ETF_SCANNER_FILE,
    ]:
        if not source_file.exists():
            continue
        try:
            with open(source_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            picks = data if isinstance(data, list) else data.get("picks", data.get("active", []))
            for p in picks:
                if _is_non_crypto(p) and is_unresolved(p):
                    p["_source_file"] = str(source_file)
                    active_non_crypto.append(p)
        except Exception as e:
            log.warning("Failed to load %s: %s", source_file, e)

    # Deduplicate by symbol + direction + strategy
    seen = set()
    unique_picks = []
    for p in active_non_crypto:
        key = f"{p.get('symbol', '')}_{p.get('direction', '')}_{p.get('strategy', p.get('source', ''))}"
        if key not in seen:
            seen.add(key)
            unique_picks.append(p)

    log.info("Found %d unique active non-crypto picks to check", len(unique_picks))

    resolved_picks = []
    for pick in unique_picks:
        symbol = pick.get("symbol", "")
        entry = _safe_float(pick.get("entry_price"))
        tp = _safe_float(pick.get("take_profit", pick.get("targetPrice", 0)))
        sl = _safe_float(pick.get("stop_loss", pick.get("stopPrice", 0)))
        direction = _infer_direction(pick)
        asset_class = str(pick.get("asset_class", pick.get("category", "UNKNOWN"))).upper()

        if entry <= 0:
            continue

        report["checked"] += 1
        if asset_class not in report["by_asset_class"]:
            report["by_asset_class"][asset_class] = {"checked": 0, "resolved": 0}
        report["by_asset_class"][asset_class]["checked"] += 1

        # v2 (2026-04-28): Replace one-shot live-spot snapshot with bar-replay
        # over the daily OHLC window since entry. The legacy "if live_price >= tp"
        # check missed any TP/SL hit that occurred between resolver runs and
        # mean-reverted. See reports/action_B_resolver_2026_04_27.md §3.2.
        entry_dt_raw = (pick.get("entry_date") or pick.get("entry_time")
                        or pick.get("created_at") or pick.get("timestamp") or "")
        entry_dt = _parse_utc_timestamp(str(entry_dt_raw)) if entry_dt_raw else None
        ohlc_window = _fetch_yfinance_ohlc_window(symbol, entry_dt)

        hit = _scan_ohlc_for_touch(ohlc_window, direction, tp, sl) if ohlc_window else None

        if hit is None:
            # No TP/SL touch found in the bar-replay window. Per v2, leave the
            # pick still_active rather than closing at live spot.
            report["no_price"] += 1
            continue

        exit_price = float(hit["price"])
        hit_tp = hit["reason"] == "TP_HIT_REPLAY"
        hit_sl = hit["reason"] == "SL_HIT_REPLAY"

        # M-112 (2026-05-18): price-scale mismatch guard. Some upstream writers
        # emit futures/equity picks with entry_price/tp/sl stored as a
        # normalized ~0-1 ratio (e.g. YM=F entry_price=0.2606) while the Yahoo
        # OHLC feed for that symbol returns raw index levels (YM=F ~49000).
        # A gapped bar in _scan_ohlc_for_touch then credits the raw bar OPEN as
        # the fill, so compute_pnl(0.2606, 49000) explodes to ~18,900,000%.
        # Root-cause fix: if the resolved exit price and the stored entry price
        # differ by more than an order of magnitude (10x), the two are on
        # different unit scales — refuse to resolve and flag for upstream repair
        # rather than writing a corrupt PnL into closed_picks.json / analytics.
        if entry > 0 and exit_price > 0:
            _scale_ratio = max(exit_price / entry, entry / exit_price)
            if _scale_ratio > 10.0:
                log.warning(
                    "PNL_SCALE_MISMATCH: %s ac=%s entry=%.6f exit=%.6f "
                    "ratio=%.1fx — entry/OHLC on different unit scales, "
                    "skipping (not writing corrupt PnL)",
                    symbol, asset_class, entry, exit_price, _scale_ratio,
                )
                pick["_pnl_scale_mismatch"] = True
                pick["_pnl_scale_ratio"] = round(_scale_ratio, 2)
                report["no_price"] += 1
                continue

        pnl_pct = compute_pnl(entry, exit_price, direction)

        # M-111 parity: PnL sanity cap. resolve_single_pick() already clamps
        # implausible PnL from price-unit mismatches; this parallel non-crypto
        # bar-replay path lacked the same guard, which let the YM=F 18.9M%
        # row reach closed_picks.json. Defense-in-depth behind the scale guard.
        _pnl_cap = _pnl_sanity_cap_for(asset_class)
        if abs(pnl_pct) > _pnl_cap:
            log.warning(
                "PNL_IMPLAUSIBLE: %s ac=%s pnl=%.4f > cap=%.2f "
                "(entry=%.6f exit=%.6f) — marking _pnl_implausible=True, skipping",
                symbol, asset_class, pnl_pct, _pnl_cap, entry, exit_price,
            )
            pick["_pnl_implausible"] = True
            pick["_pnl_implausible_raw"] = round(pnl_pct, 6)
            pick["_pnl_implausible_cap"] = _pnl_cap
            report["no_price"] += 1
            continue

        outcome = classify_outcome(pnl_pct, asset_class=asset_class or None)

        # v2: stamp resolver_version + preserve legacy fields if present.
        if not pick.get("resolver_version"):
            if pick.get("pnl_pct") not in (None, 0, 0.0):
                pick["_legacy_pnl_pct"] = pick.get("pnl_pct")
            if pick.get("exit_reason"):
                pick["_legacy_exit_reason"] = pick.get("exit_reason")

        pick["exit_price"] = exit_price
        pick["pnl_pct"] = round(pnl_pct, 6)
        pick["status"] = outcome
        # Charter §7 P0.5-2: stamp _pnl_pct_gross + _pnl_pct_net.
        try:
            from alpha_engine.charter_slippage import stamp_pick_net_pnl
            stamp_pick_net_pnl(pick)
        except ImportError:
            pass
        pick["exit_reason"] = hit["reason"]   # TP_HIT_REPLAY or SL_HIT_REPLAY
        pick["resolved_at"] = datetime.now(timezone.utc).isoformat()
        pick["resolved_by"] = "non_crypto_resolver"
        pick["resolver_version"] = RESOLVER_VERSION  # "v2"
        pick["direction"] = direction
        pick["_replay_bar_date"] = hit.get("bar_date", "")

        resolved_picks.append(pick)
        report["resolved"] += 1
        report["by_asset_class"][asset_class]["resolved"] += 1
        if hit_tp:
            report["tp_hits"] += 1
        else:
            report["sl_hits"] += 1

        log.info("RESOLVED (v2 bar-replay): %s %s %s @%s -> %s PnL=%.4f%%",
                 symbol, direction, hit["reason"], hit.get("bar_date", "?"),
                 asset_class, pnl_pct * 100)

    # Save resolved picks to closed_picks.json
    if resolved_picks and not dry_run:
        closed_picks = []
        if CLOSED_PICKS_FILE.exists():
            try:
                with open(CLOSED_PICKS_FILE, "r", encoding="utf-8") as f:
                    closed_picks = json.load(f)
            except Exception:
                pass

        # A9 (2026-05-17): emitter/resolver idempotency. The id-dedup below
        # misses re-emissions (each gets a FRESH id). Build a set of existing
        # deterministic dedup_keys so a re-emitted signal is blocked even when
        # its id is new. Env-gated (EMITTER_DEDUP), fail-soft.
        _a9_on = False
        _a9_seen_keys: set = set()
        try:
            from alpha_engine.emitter_dedup import (
                dedup_enabled as _a9_enabled,
                ensure_dedup_key as _a9_key,
            )
            _a9_on = _a9_enabled()
            if _a9_on:
                _a9_seen_keys = {_a9_key(p) for p in closed_picks}
                _a9_seen_keys.discard("")
        except Exception as _a9_err:
            log.warning("EMITTER_DEDUP guard failed: %s", _a9_err)
            _a9_on = False

        existing_ids = {p.get("id", "") for p in closed_picks if p.get("id")}
        added = 0
        _a9_blocked = 0
        for rp in resolved_picks:
            pid = rp.get("id", f"{rp.get('symbol', '')}_{rp.get('strategy', '')}_{rp.get('resolved_at', '')}")
            if pid in existing_ids:
                continue
            if _a9_on:
                _k = _a9_key(rp)  # stamps rp['dedup_key']
                if _k and _k in _a9_seen_keys:
                    _a9_blocked += 1
                    continue
                if _k:
                    _a9_seen_keys.add(_k)
            rp["id"] = pid
            # P0-A (2026-05-06): copy score/trust/smart/grade fields from
            # the active pick so closed_picks.json inherits scoring metadata.
            _preserve_score_fields(rp, rp)
            closed_picks.append(rp)
            existing_ids.add(pid)
            added += 1

        if _a9_blocked:
            log.info("EMITTER_DEDUP blocked %d duplicate re-emission(s) "
                     "(non-crypto resolved)", _a9_blocked)

        with open(CLOSED_PICKS_FILE, "w", encoding="utf-8") as f:
            json.dump(closed_picks, f, indent=2, default=str)
        log.info("Added %d non-crypto resolved picks to closed_picks.json", added)

    # Log report
    log_file = DATA_DIR / "outcome_resolver_log.json"
    try:
        log_data = []
        if log_file.exists():
            log_data = json.load(open(log_file, "r", encoding="utf-8"))
        log_data.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "non_crypto_resolver",
            **report,
        })
        if len(log_data) > 200:
            log_data = log_data[-200:]
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, default=str)
    except Exception:
        pass

    return report


# ---------------------------------------------------------------------------
# Forex/Commodity Null-Exit-Price Healer (2026-04-04)
# ---------------------------------------------------------------------------
# Problem: 540+ forex/commodity/equity/bond picks in secondary data files
# (closed_picks_fast.json, augmented_training.json, forex_futures_picks.json,
# consolidated_portfolios.json) have status=CLOSED/WON/LOST/EXPIRED but
# exit_price=None and pnl_pct=None. These bypass the canonical
# closed_picks.json resolver so they never get healed.
#
# Root cause: The non-crypto resolver (resolve_active_non_crypto) only
# writes TP/SL hits to closed_picks.json. Picks that are closed by OTHER
# pipelines (e.g. expiry scripts, scanners that write closed_picks_fast.json
# directly) skip the resolver entirely. When yfinance fails to return a
# price for forex (EURUSD=X) or commodity (GC=F) symbols, those picks end
# up marked CLOSED with exit_price=None.
#
# Fix: Sweep secondary data files and heal null exit_price picks by
# fetching live yfinance price OR falling back to breakeven
# (exit_price = entry_price, exit_reason=RESOLVE_FAILED_BREAKEVEN), mirroring
# the crypto fallback already present in resolve_single_pick().

NON_CRYPTO_SECONDARY_FILES = [
    DATA_DIR / "closed_picks_fast.json",
    DATA_DIR / "augmented_training.json",
    Path(__file__).resolve().parent.parent / "audit_dashboard" / "data" / "forex_futures_picks.json",
    Path(__file__).resolve().parent.parent / "audit_dashboard" / "data" / "consolidated_portfolios.json",
]


def _extract_picks_from_obj(obj):
    """Return (picks_list, mutate_callback) pairs found under obj.
    Handles: top-level list, {picks: [...]}, {closed_picks: [...]},
    {portfolios: [{trades_list: [...]}, ...]}.
    """
    out = []
    if isinstance(obj, list):
        # Only accept if first item looks like a pick
        if obj and isinstance(obj[0], dict) and ("exit_price" in obj[0] or "entry_price" in obj[0]):
            out.append(obj)
        return out
    if isinstance(obj, dict):
        for key in ("picks", "closed_picks", "trades_list", "closed", "items", "history"):
            v = obj.get(key)
            if isinstance(v, list) and v and isinstance(v[0], dict) and ("exit_price" in v[0] or "entry_price" in v[0]):
                out.append(v)
        # Recurse into dict/list children (for portfolios[].trades_list etc.)
        for v in obj.values():
            if isinstance(v, (dict, list)):
                out.extend(_extract_picks_from_obj(v))
    return out


def heal_null_exit_prices_non_crypto(dry_run: bool = False) -> dict:
    """Heal forex/commodity/equity/bond closed picks that have null exit_price.

    Scans secondary data files that aren't touched by the canonical
    closed_picks.json resolver. Applies the breakeven-fallback pattern:
    attempt live yfinance fetch first, then fall back to
    exit_price=entry_price with exit_reason=RESOLVE_FAILED_BREAKEVEN so
    these picks stop corrupting backtest/audit aggregates.
    """
    report = {
        "files_scanned": 0, "files_modified": 0,
        "picks_scanned": 0, "healed_with_price": 0,
        "healed_breakeven": 0, "skipped": 0,
        "by_asset_class": {},
    }

    price_cache: dict = {}

    for source_file in NON_CRYPTO_SECONDARY_FILES:
        if not source_file.exists():
            continue
        try:
            with open(source_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            log.warning("heal_null_exit: failed to load %s: %s", source_file, e)
            continue

        report["files_scanned"] += 1
        pick_lists = _extract_picks_from_obj(data)
        if not pick_lists:
            continue

        file_modified = False
        for picks in pick_lists:
            for pick in picks:
                if not isinstance(pick, dict):
                    continue
                if not _is_non_crypto(pick):
                    continue

                report["picks_scanned"] += 1
                status = str(pick.get("status", "")).upper()
                exit_raw = pick.get("exit_price")
                entry = _safe_float(pick.get("entry_price"))

                # Only heal closed picks with null exit AND a valid entry
                if status not in ("CLOSED", "EXPIRED", "WON", "LOST"):
                    continue
                if exit_raw is not None and _safe_float(exit_raw) > 0:
                    continue
                if entry <= 0:
                    report["skipped"] += 1
                    continue

                asset_class = (
                    str(pick.get("asset_class", pick.get("category", "UNKNOWN"))).upper()
                    or ("FOREX" if str(pick.get("symbol", "")).endswith("=X")
                        else "COMMODITY" if str(pick.get("symbol", "")).endswith("=F")
                        else "UNKNOWN")
                )
                if asset_class not in report["by_asset_class"]:
                    report["by_asset_class"][asset_class] = {
                        "healed_with_price": 0, "healed_breakeven": 0,
                    }

                # Try live price fetch (yfinance + cached JSON fallback)
                sym = pick.get("symbol", "")
                if sym in price_cache:
                    live_price = price_cache[sym]
                else:
                    live_price = _fetch_yfinance_price(sym) if sym else None
                    price_cache[sym] = live_price

                direction = _infer_direction(pick)
                tp = _safe_float(pick.get("take_profit", pick.get("targetPrice", 0)))
                sl = _safe_float(pick.get("stop_loss", pick.get("stopPrice", 0)))

                if live_price and live_price > 0:
                    # Prefer TP/SL if crossed, else live price
                    effective_exit = live_price
                    exit_reason = "PRICE_HEALED"
                    if direction == "LONG":
                        if tp > 0 and live_price >= tp:
                            effective_exit = tp; exit_reason = "TP_HIT_HEALED"
                        elif sl > 0 and live_price <= sl:
                            effective_exit = sl; exit_reason = "SL_HIT_HEALED"
                    else:
                        if tp > 0 and live_price <= tp:
                            effective_exit = tp; exit_reason = "TP_HIT_HEALED"
                        elif sl > 0 and live_price >= sl:
                            effective_exit = sl; exit_reason = "SL_HIT_HEALED"

                    if not dry_run:
                        # v2: preserve legacy + stamp resolver_version
                        if not pick.get("resolver_version"):
                            if pick.get("pnl_pct") not in (None, 0, 0.0):
                                pick["_legacy_pnl_pct"] = pick.get("pnl_pct")
                            if pick.get("exit_reason"):
                                pick["_legacy_exit_reason"] = pick.get("exit_reason")
                        pick["exit_price"] = effective_exit
                        pnl_pct = compute_pnl(entry, effective_exit, direction)
                        pick["pnl_pct"] = round(pnl_pct, 6)
                        pick["status"] = classify_outcome(pnl_pct, asset_class=asset_class)
                        pick["exit_reason"] = exit_reason
                        pick["direction"] = direction
                        pick["resolved_at"] = datetime.now(timezone.utc).isoformat()
                        pick["resolved_by"] = "heal_null_exit_non_crypto"
                        pick["resolver_version"] = RESOLVER_VERSION
                    report["healed_with_price"] += 1
                    report["by_asset_class"][asset_class]["healed_with_price"] += 1
                    file_modified = True
                else:
                    # Breakeven fallback — mirrors resolve_single_pick() pattern
                    if not dry_run:
                        pick["exit_price"] = entry
                        pick["pnl_pct"] = 0.0
                        pick["exit_reason"] = "RESOLVE_FAILED_BREAKEVEN"
                        pick["direction"] = direction
                        pick["resolved_at"] = datetime.now(timezone.utc).isoformat()
                        pick["resolved_by"] = "heal_null_exit_non_crypto_breakeven"
                        pick["_resolver_fallback"] = True   # analytics: yfinance returned None, pnl forced 0.0
                        pick["_resolve_retry_needed"] = True
                    report["healed_breakeven"] += 1
                    report["by_asset_class"][asset_class]["healed_breakeven"] += 1
                    file_modified = True

        if file_modified and not dry_run:
            try:
                with open(source_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, default=str)
                report["files_modified"] += 1
                log.info("heal_null_exit: updated %s", source_file)
            except Exception as e:
                log.warning("heal_null_exit: failed to write %s: %s", source_file, e)

    return report


# ---------------------------------------------------------------------------
# Triple-barrier labeling (Lopez de Prado AFML, Ch. 3) — ADDITIVE labeler
# ---------------------------------------------------------------------------
#
# Wires the orphan ``tools/triple_barrier_labeler.py`` module into the
# resolver as an ADDITIVE label source. Triple-barrier walks the OHLC bars
# from each pick's entry forward and returns the first barrier hit (TP, SL,
# or TIMEOUT). Unlike the legacy resolver path which used a single live spot
# snapshot + 0.1bp WIN threshold (the source of FOREX 63% / COMMODITY 67%
# noise share documented in ``reports/action_B_resolver_2026_04_27.md``),
# bar-replay catches barriers that fired between resolver runs and then
# mean-reverted.
#
# OPT-IN. Default OFF — gated by env var ``TRIPLE_BARRIER_LABEL=1`` or the
# ``--triple-barrier`` CLI flag. This is intentional: the first deployment
# writes ``triple_barrier_label`` as an ADDITIONAL field next to the existing
# ``pnl_pct`` so a follow-up audit can compare the two and decide which to
# promote to canonical. Live label flip happens in a separate, deliberate PR.
#
# Refs:
#   * tools/triple_barrier_labeler.py — sign-based ``label_pick`` (the
#     existing public API; we call it for cross-validation only).
#   * alpha_engine/forward_validator.py:1060,1180-1213 — the crypto
#     bar-replay reference implementation; same TP/SL detection pattern.
#   * reports/action_B_resolver_2026_04_27.md — the resolver bug context.
#   * reports/HEDGE_LIBS_LEVERAGE_AUDIT_2026_04_22.md — orphan-rate audit
#     this wire-up retires for ``triple_barrier_labeler.py``.
#
# Companion PR: ``fix/non-crypto-resolver-bar-replay-2026-04-28`` (PR #463)
# replaces the live-spot close in ``resolve_single_pick`` itself. This
# wire-up is COMPLEMENTARY — it adds an INDEPENDENT label source so we can
# cross-check both resolver versions before promoting either to canonical.

# Per-asset-class default holding window for the time barrier.
TRIPLE_BARRIER_HOLD_DAYS_BY_CLASS = {
    "EQUITY":    14,   # 2 weeks for stocks
    "ETF":       14,
    "STOCK":     14,
    "INDEX":     14,
    "FOREX":     7,    # 1 week for FX
    "COMMODITY": 7,
    "FUTURES":   7,
    "BOND":      14,
    "CRYPTO":    7,    # default; crypto is skipped by default (forward_validator owns)
}
TRIPLE_BARRIER_HOLD_DAYS_DEFAULT = 14


def _triple_barrier_asset_class(pick: dict) -> str:
    """Lightweight asset-class inference for the time-barrier window.

    Self-contained — does NOT depend on any helper added by the
    resolver-fix PR (#463) so this wire-up can land independently.

    Symbol suffixes (=X → FOREX, =F → COMMODITY) always beat the asset_class
    field — they are unambiguous Yahoo Finance markers (same guard as the main
    _resolve_asset_class() fix for USDJPY=X misclassified as BOND).
    """
    sym = str(pick.get("symbol", "") or "")
    # Suffix check first — unambiguous; beats any upstream asset_class tag
    if sym.endswith("=X"):
        return "FOREX"
    if sym.endswith("=F"):
        return "COMMODITY"
    raw = str(pick.get("asset_class") or pick.get("category") or "").upper().strip()
    aliases = {"STOCKS": "EQUITY", "FX": "FOREX", "COMMODITIES": "COMMODITY",
               "BONDS": "BOND", "INDICES": "INDEX"}
    if raw:
        return aliases.get(raw, raw)
    if _is_non_crypto(pick):
        return "EQUITY"
    return "CRYPTO"


def _triple_barrier_fetch_bars(symbol: str,
                                 entry_dt: Optional[datetime],
                                 hold_days: int) -> list[dict]:
    """Fetch daily OHLC bars covering [entry_dt, entry_dt+hold_days].

    Self-contained yfinance fetcher — kept independent of any helper the
    resolver-fix PR may add to ``outcome_resolver.py`` so the two PRs can
    land in either order. Returns a list of bars sorted ascending by date,
    each with keys: date, open, high, low, close. Empty list on any failure.
    """
    if not symbol:
        return []
    try:
        import yfinance as yf
    except Exception as e:
        log.debug("triple_barrier: yfinance unavailable: %s", e)
        return []

    from datetime import timedelta
    end_dt = datetime.now(timezone.utc)
    if entry_dt is None:
        start_dt = end_dt - timedelta(days=hold_days + 2)
    else:
        start_dt = entry_dt - timedelta(days=1)
        cap = entry_dt + timedelta(days=hold_days + 1)
        if cap < end_dt:
            end_dt = cap

    try:
        hist = yf.Ticker(symbol).history(
            start=start_dt.strftime("%Y-%m-%d"),
            end=(end_dt + timedelta(days=1)).strftime("%Y-%m-%d"),
            interval="1d",
            auto_adjust=False,
        )
    except Exception as e:
        log.debug("triple_barrier: yf.history failed for %s: %s", symbol, e)
        return []

    if hist is None or hist.empty:
        return []

    bars: list[dict] = []
    try:
        for ts, row in hist.iterrows():
            try:
                op = float(row["Open"]); hi = float(row["High"])
                lo = float(row["Low"]);  cl = float(row["Close"])
            except (KeyError, TypeError, ValueError):
                continue
            if math.isnan(hi) or math.isnan(lo) or math.isnan(cl):
                continue
            bars.append({
                "date": ts.strftime("%Y-%m-%d") if hasattr(ts, "strftime") else str(ts),
                "open": op, "high": hi, "low": lo, "close": cl,
            })
    except Exception:
        return []

    if entry_dt is not None:
        cutoff = entry_dt.strftime("%Y-%m-%d")
        bars = [b for b in bars if b["date"] >= cutoff]
    return bars


def _triple_barrier_label_bar_replay(pick: dict, bars: list[dict],
                                       hold_days: int) -> dict:
    """Walk OHLC bars from entry forward; return first TP/SL/TIMEOUT hit.

    Mirrors the crypto bar-replay pattern in
    ``alpha_engine/forward_validator.py:1180-1213``. Conservative tie-break:
    if a single bar would touch both TP and SL, SL wins (worst-case fill
    for retroactive labeling — within-bar order is unobservable from daily
    bars, so we assume the position got hit on the wrong side first).

    Returns the additive-field schema used by ``apply_triple_barrier_labels``.
    """
    out = {
        "triple_barrier_label": "UNLABELED",
        "triple_barrier_first_barrier": "NONE",
        "triple_barrier_resolved_at": "",
        "triple_barrier_resolution_price": None,
        "triple_barrier_bars_walked": 0,
        "triple_barrier_hold_days_cap": int(hold_days),
    }
    direction = str(pick.get("direction", "") or "").upper()
    entry = _safe_float(pick.get("entry_price"))
    tp = _safe_float(pick.get("take_profit", pick.get("targetPrice", 0)))
    sl = _safe_float(pick.get("stop_loss", pick.get("stopPrice", 0)))
    if not bars or entry <= 0 or (tp <= 0 and sl <= 0):
        return out

    is_long = direction in ("LONG", "BUY")
    walked = 0
    last_bar = None
    for bar in bars[: max(1, int(hold_days))]:
        walked += 1
        last_bar = bar
        try:
            hi = float(bar.get("high", 0) or 0)
            lo = float(bar.get("low", 0) or 0)
        except (TypeError, ValueError):
            continue
        if hi <= 0 or lo <= 0:
            continue

        if is_long:
            if sl > 0 and lo <= sl:
                out.update(triple_barrier_label="LOSS",
                           triple_barrier_first_barrier="SL",
                           triple_barrier_resolution_price=float(sl),
                           triple_barrier_resolved_at=bar.get("date", "") or "",
                           triple_barrier_bars_walked=walked)
                return out
            if tp > 0 and hi >= tp:
                out.update(triple_barrier_label="WIN",
                           triple_barrier_first_barrier="TP",
                           triple_barrier_resolution_price=float(tp),
                           triple_barrier_resolved_at=bar.get("date", "") or "",
                           triple_barrier_bars_walked=walked)
                return out
        else:  # SHORT
            if sl > 0 and hi >= sl:
                out.update(triple_barrier_label="LOSS",
                           triple_barrier_first_barrier="SL",
                           triple_barrier_resolution_price=float(sl),
                           triple_barrier_resolved_at=bar.get("date", "") or "",
                           triple_barrier_bars_walked=walked)
                return out
            if tp > 0 and lo <= tp:
                out.update(triple_barrier_label="WIN",
                           triple_barrier_first_barrier="TP",
                           triple_barrier_resolution_price=float(tp),
                           triple_barrier_resolved_at=bar.get("date", "") or "",
                           triple_barrier_bars_walked=walked)
                return out

    # No barrier hit in window → TIMEOUT, resolution price = last close.
    out["triple_barrier_first_barrier"] = "TIME"
    out["triple_barrier_bars_walked"] = walked
    if last_bar:
        try:
            close_p = float(last_bar.get("close", 0) or 0)
        except (TypeError, ValueError):
            close_p = 0.0
        if close_p > 0:
            out["triple_barrier_resolution_price"] = close_p
            out["triple_barrier_resolved_at"] = last_bar.get("date", "") or ""
            out["triple_barrier_label"] = "TIMEOUT"
    return out


def apply_triple_barrier_labels(
    closed_picks: list[dict],
    fetch_bars: bool = True,
    skip_crypto: bool = True,
    dry_run: bool = False,
) -> dict:
    """Stamp triple-barrier labels onto closed picks (ADDITIVE — does NOT
    overwrite ``pnl_pct``, ``status``, ``exit_price``, ``exit_reason``).

    For each closed pick:
      1. Determine asset class and per-class hold-window (EQUITY=14d, FX=7d).
      2. Fetch daily OHLC bars from entry forward (yfinance for non-crypto;
         crypto picks are skipped by default since the crypto path in
         ``alpha_engine/forward_validator.py`` already does bar-replay).
      3. Walk the bars to detect first-barrier hit (TP / SL / TIMEOUT).
      4. ALSO call the existing ``tools.triple_barrier_labeler.label_pick``
         (sign-based) so both labels are stamped — gives a follow-up audit
         the bar-replay vs sign-based delta to compare.
      5. Stamp under additive keys::

            triple_barrier_label              ∈ {WIN, LOSS, TIMEOUT, UNLABELED}
            triple_barrier_first_barrier      ∈ {TP, SL, TIME, NONE}
            triple_barrier_resolved_at        "YYYY-MM-DD"
            triple_barrier_resolution_price   float or None
            triple_barrier_bars_walked        int
            triple_barrier_hold_days_cap      int
            triple_barrier_asset_class        normalized class string
            triple_barrier_stamped_at         ISO timestamp of this run
            triple_barrier_labeler_version    "v1"
            triple_barrier_pnl_sign_label     {WIN, LOSS, TIMEOUT, FLAT_CLOSE_BUG, UNLABELED}
                (cross-check from the existing sign-based labeler)

    Returns a summary report. Picks are mutated in-place ONLY when
    ``dry_run`` is False. The original ``pnl_pct`` / ``status`` / etc. are
    NEVER touched here — promotion to canonical happens in a follow-up PR.

    Args:
        closed_picks: List of closed pick dicts.
        fetch_bars: When False, skip yfinance fetch and only stamp picks
            that already carry an ``ohlc_window`` field. Useful for tests
            and offline re-labeling runs.
        skip_crypto: When True (default), skip picks whose asset_class
            resolves to CRYPTO — the existing forward_validator path is
            already authoritative for those.
        dry_run: When True, compute labels but do not mutate picks.

    Refs:
        * tools/triple_barrier_labeler.py:label_pick (sign-based cross-check)
        * reports/action_B_resolver_2026_04_27.md (resolver bug context)
    """
    # Ensure repo root on sys.path so ``tools.triple_barrier_labeler`` is
    # importable when the resolver runs from alpha_engine/.
    repo_root = ENGINE_DIR.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    try:
        from tools.triple_barrier_labeler import label_pick as _tb_label_pick
    except Exception as e:
        log.warning("triple_barrier: import failed: %s — sign-based cross-check disabled", e)
        _tb_label_pick = None  # bar-replay still runs

    report: dict = {
        "stamped": 0,
        "skipped_crypto": 0,
        "skipped_no_bars": 0,
        "skipped_no_barriers": 0,
        "errors": 0,
        "label_counts": defaultdict(int),
        "by_asset_class": defaultdict(lambda: {"stamped": 0, "label_counts": defaultdict(int)}),
        "agreement_with_pnl_sign": {"agree": 0, "disagree": 0, "either_unlabeled": 0},
    }

    bars_cache: dict[tuple[str, int], list[dict]] = {}

    for pick in closed_picks:
        try:
            asset_class = _triple_barrier_asset_class(pick)
            if skip_crypto and asset_class == "CRYPTO":
                report["skipped_crypto"] += 1
                continue

            entry = _safe_float(pick.get("entry_price"))
            tp = _safe_float(pick.get("take_profit", pick.get("targetPrice", 0)))
            sl = _safe_float(pick.get("stop_loss", pick.get("stopPrice", 0)))
            if entry <= 0 or (tp <= 0 and sl <= 0):
                report["skipped_no_barriers"] += 1
                continue

            hold_days = TRIPLE_BARRIER_HOLD_DAYS_BY_CLASS.get(
                asset_class, TRIPLE_BARRIER_HOLD_DAYS_DEFAULT,
            )

            entry_raw = (pick.get("entry_date") or pick.get("entry_time")
                         or pick.get("created_at") or pick.get("timestamp") or "")
            entry_dt = _parse_utc_timestamp(str(entry_raw)) if entry_raw else None

            # Test fixtures may pre-supply ``ohlc_window`` — wins over fetch.
            bars = pick.get("ohlc_window") if isinstance(pick.get("ohlc_window"), list) else None
            if bars is None and fetch_bars:
                symbol = str(pick.get("symbol", "") or "")
                cache_key = (symbol, hold_days)
                if cache_key not in bars_cache:
                    bars_cache[cache_key] = _triple_barrier_fetch_bars(
                        symbol, entry_dt, hold_days,
                    )
                bars = bars_cache[cache_key]

            if not bars:
                report["skipped_no_bars"] += 1
                if not dry_run:
                    pick["triple_barrier_label"] = "UNLABELED"
                    pick["triple_barrier_first_barrier"] = "NONE"
                    pick["triple_barrier_asset_class"] = asset_class
                    pick["triple_barrier_hold_days_cap"] = hold_days
                    pick["triple_barrier_stamped_at"] = datetime.now(timezone.utc).isoformat()
                    pick["triple_barrier_labeler_version"] = "v1"
                continue

            # Bar-replay (primary).
            result = _triple_barrier_label_bar_replay(pick, bars, hold_days)

            # Sign-based cross-check via the existing public API of the labeler.
            sign_label = "UNLABELED"
            if _tb_label_pick is not None:
                try:
                    sign_rec = _tb_label_pick(pick, default_hold_hours=hold_days * 24.0)
                    sign_label = str(sign_rec.get("label", "UNLABELED"))
                except Exception:
                    sign_label = "UNLABELED"

            # Tally cross-agreement (for the report, regardless of dry_run).
            tb_lbl = result.get("triple_barrier_label", "UNLABELED")
            if tb_lbl in ("UNLABELED",) or sign_label in ("UNLABELED", "FLAT_CLOSE_BUG"):
                report["agreement_with_pnl_sign"]["either_unlabeled"] += 1
            elif tb_lbl == sign_label:
                report["agreement_with_pnl_sign"]["agree"] += 1
            else:
                # WIN-vs-LOSS or WIN-vs-TIMEOUT etc. count as disagreement.
                report["agreement_with_pnl_sign"]["disagree"] += 1

            if not dry_run:
                pick.update(result)
                pick["triple_barrier_asset_class"] = asset_class
                pick["triple_barrier_pnl_sign_label"] = sign_label
                pick["triple_barrier_stamped_at"] = datetime.now(timezone.utc).isoformat()
                pick["triple_barrier_labeler_version"] = "v1"

            report["stamped"] += 1
            report["label_counts"][tb_lbl] += 1
            report["by_asset_class"][asset_class]["stamped"] += 1
            report["by_asset_class"][asset_class]["label_counts"][tb_lbl] += 1
        except Exception as e:
            report["errors"] += 1
            log.debug("triple_barrier: pick failed (%s): %s",
                      pick.get("symbol", "?"), e)

    # defaultdicts → plain dicts for JSON serialization
    report["label_counts"] = dict(report["label_counts"])
    report["by_asset_class"] = {
        k: {"stamped": v["stamped"], "label_counts": dict(v["label_counts"])}
        for k, v in report["by_asset_class"].items()
    }
    return report


def _triple_barrier_load_closed_picks() -> list[dict]:
    """Load closed picks from CLOSED_PICKS_FILE for the wire-up step."""
    if not CLOSED_PICKS_FILE.exists():
        return []
    try:
        with open(CLOSED_PICKS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and isinstance(data.get("picks"), list):
            return data["picks"]
    except Exception as e:
        log.warning("triple_barrier: failed to load closed picks: %s", e)
    return []


def _triple_barrier_save_closed_picks(picks: list[dict]) -> bool:
    """Persist closed picks back to CLOSED_PICKS_FILE preserving wrapper shape."""
    if not CLOSED_PICKS_FILE.exists() or not picks:
        return False
    try:
        with open(CLOSED_PICKS_FILE, "r", encoding="utf-8") as f:
            existing = json.load(f)
        if isinstance(existing, list):
            payload: object = picks
        else:
            existing["picks"] = picks  # type: ignore[index]
            payload = existing
        with open(CLOSED_PICKS_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=str)
        return True
    except Exception as e:
        log.warning("triple_barrier: failed to save closed picks: %s", e)
        return False


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Outcome Resolver for closed picks")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview resolution without modifying files")
    parser.add_argument("--non-crypto", action="store_true",
                        help="Also resolve active non-crypto picks against live TP/SL")
    parser.add_argument("--heal-null-exit", action="store_true",
                        help="Sweep secondary files and heal forex/commodity picks with null exit_price")
    parser.add_argument("--triple-barrier", action="store_true",
                        help="Apply triple-barrier labels to closed picks (additive). "
                             "Also enabled by env TRIPLE_BARRIER_LABEL=1.")
    parser.add_argument("--mysql", action="store_true",
                        help="Upsert resolved picks into at_pick_outcomes MySQL table. "
                             "Also enabled by env PICK_OUTCOMES_MYSQL_ENABLED=1. "
                             "Requires pymysql + DB_HOST/DB_USER/DB_PASS_STOCKS env vars.")
    args = parser.parse_args()

    report = run_outcome_resolver(dry_run=args.dry_run, mysql=args.mysql)
    print_report(report)

    if args.non_crypto:
        print("\n  [NON-CRYPTO RESOLVER] Checking active non-crypto picks...")
        nc_report = resolve_active_non_crypto(dry_run=args.dry_run)
        print(f"  Checked: {nc_report['checked']} | Resolved: {nc_report['resolved']} "
              f"(TP: {nc_report['tp_hits']}, SL: {nc_report['sl_hits']}) | No price: {nc_report['no_price']}")
        for ac, counts in nc_report.get("by_asset_class", {}).items():
            print(f"    {ac}: checked={counts['checked']} resolved={counts['resolved']}")
    elif not args.dry_run:
        # Always run non-crypto resolver as part of the standard cycle
        nc_report = resolve_active_non_crypto(dry_run=args.dry_run)
        if nc_report["resolved"] > 0:
            print(f"\n  [NON-CRYPTO] Resolved {nc_report['resolved']} picks "
                  f"(TP: {nc_report['tp_hits']}, SL: {nc_report['sl_hits']})")

    # Heal null exit_price in secondary forex/commodity files
    # (always runs as part of standard cycle — this is idempotent).
    if args.heal_null_exit or not args.dry_run:
        print("\n  [HEAL NULL EXIT] Sweeping forex/commodity secondary files...")
        heal_report = heal_null_exit_prices_non_crypto(dry_run=args.dry_run)
        print(f"  Files scanned: {heal_report['files_scanned']} | "
              f"modified: {heal_report['files_modified']} | "
              f"picks scanned: {heal_report['picks_scanned']}")
        print(f"  Healed w/ live price: {heal_report['healed_with_price']} | "
              f"breakeven fallback: {heal_report['healed_breakeven']}")
        for ac, counts in heal_report.get("by_asset_class", {}).items():
            print(f"    {ac}: price={counts['healed_with_price']} "
                  f"breakeven={counts['healed_breakeven']}")

    # ------------------------------------------------------------------
    # Triple-barrier additive labeler (opt-in: --triple-barrier or env var)
    # ------------------------------------------------------------------
    # OPT-IN by design. This wire-up adds triple_barrier_label as an
    # ADDITIONAL field on each closed pick — it does NOT mutate pnl_pct,
    # status, or any existing resolver field. The flip to canonical happens
    # in a later, deliberate PR after we audit cross-agreement vs the
    # existing resolver. See the module-level docstring above for refs.
    tb_env = os.environ.get("TRIPLE_BARRIER_LABEL", "").strip().lower()
    tb_enabled = bool(args.triple_barrier) or tb_env in ("1", "true", "yes", "on")
    if tb_enabled:
        print("\n  [TRIPLE-BARRIER] Additive labeling enabled "
              f"(via {'flag' if args.triple_barrier else 'env'}).")
        closed_picks = _triple_barrier_load_closed_picks()
        if not closed_picks:
            print("  [TRIPLE-BARRIER] No closed picks found at "
                  f"{CLOSED_PICKS_FILE}; skipping.")
        else:
            tb_report = apply_triple_barrier_labels(
                closed_picks, fetch_bars=True, skip_crypto=True, dry_run=args.dry_run,
            )
            print(f"  Stamped: {tb_report['stamped']} | "
                  f"crypto skipped: {tb_report['skipped_crypto']} | "
                  f"no-bars: {tb_report['skipped_no_bars']} | "
                  f"no-barriers: {tb_report['skipped_no_barriers']} | "
                  f"errors: {tb_report['errors']}")
            for lbl, n in (tb_report.get("label_counts") or {}).items():
                print(f"    {lbl}: {n}")
            agree = tb_report.get("agreement_with_pnl_sign", {})
            if agree.get("agree", 0) + agree.get("disagree", 0) > 0:
                total = agree["agree"] + agree["disagree"]
                pct = (agree["agree"] / total * 100) if total else 0.0
                print(f"  Agreement vs pnl-sign: {agree['agree']}/{total} ({pct:.1f}%) "
                      f"(unlabeled either side: {agree.get('either_unlabeled', 0)})")
            for ac, ac_rep in (tb_report.get("by_asset_class") or {}).items():
                summary = ", ".join(f"{k}={v}" for k, v in ac_rep["label_counts"].items())
                print(f"    [{ac}] stamped={ac_rep['stamped']} ({summary})")
            if not args.dry_run and tb_report["stamped"] > 0:
                _triple_barrier_save_closed_picks(closed_picks)
                print("  [TRIPLE-BARRIER] Saved updates to closed_picks.json")

    if args.dry_run:
        print("\n  [DRY RUN] No files were modified.\n")


if __name__ == "__main__":
    main()
