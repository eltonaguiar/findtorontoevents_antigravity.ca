#!/usr/bin/env python3
"""
NOTE — SNAPSHOT-RESOLVER ARTIFACT (2026-06-03): WR/PF here is inflated by single
daily-snapshot TP/SL resolution (no intrabar OHLC path) — intraday SL touches are missed.
Do not size up on these numbers. See docs/RESOLVER_SNAPSHOT_ARTIFACT_AFFECTED_PORTFOLIOS_2026-06-03.md

ALPHA ENGINE -- Forward-Test Portfolio System
==============================================
Manages 8 paper-trade portfolios across crypto, forex, and equity asset
classes.  Each portfolio has its own pick filter, capital, and position
management rules.  Every run:

  1. Sources picks from active_picks, dashboard_payload, copy_trader,
     and strategy-specific JSON files.
  2. Filters picks into the correct portfolio based on rules.
  3. Fetches live prices (Binance 5-mirror for crypto, cached for others).
  4. Checks TP/SL/max-hold exits.
  5. Opens new positions (quarter-Kelly sizing, max 10 per portfolio).
  6. Persists state -> forward_test_state.json
  7. Appends snapshot -> forward_test_history.json (capped 1000)
  8. Prints ranked comparison table.

Stdlib only.  Windows UTF-8 fix.  Binance 5-mirror failover.
"""

from __future__ import annotations

import copy
import json
import logging
import math
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Windows UTF-8 fix
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
REPO_DIR = BASE_DIR.parent

STATE_FILE = DATA_DIR / "forward_test_state.json"
HISTORY_FILE = DATA_DIR / "forward_test_history.json"
HISTORY_CAP = 1000

# Pick source files
ALPHA_PICKS = DATA_DIR / "active_picks.json"
COPY_PICKS = REPO_DIR / "copy_trader_intel" / "data" / "active_picks.json"
DASHBOARD_PAYLOAD = REPO_DIR / "audit_trail" / "data" / "dashboard_payload.json"
HIGHSCORE_HISTORY = REPO_DIR / "copy_trader_intel" / "data" / "highscore_pick_history.json"
SHORT_DOMINANT_FILE = DATA_DIR / "short_dominant_picks.json"
ROCKET_PICKS_FILE = DATA_DIR / "rocket_picks.json"

# ---------------------------------------------------------------------------
# Binance 5-mirror failover
# ---------------------------------------------------------------------------
BINANCE_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://api4.binance.com",
]

_SSL_CTX: Optional[ssl.SSLContext] = None


def _get_ssl_ctx() -> ssl.SSLContext:
    global _SSL_CTX
    if _SSL_CTX is None:
        _SSL_CTX = ssl.create_default_context()
        _SSL_CTX.check_hostname = False
        _SSL_CTX.verify_mode = ssl.CERT_NONE
    return _SSL_CTX


def _http_get(url: str, timeout: int = 10) -> Optional[bytes]:
    """GET with SSL fallback."""
    for ctx in (None, _get_ssl_ctx()):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AlphaFwdTest/1.0"})
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                return resp.read()
        except Exception:
            continue
    return None


# Price cache: symbol -> (price, fetch_time)
_price_cache: Dict[str, Tuple[float, float]] = {}
PRICE_CACHE_TTL = 120  # seconds


def fetch_crypto_price(symbol: str) -> Optional[float]:
    """Fetch current price from Binance with 5-mirror failover."""
    now = time.time()
    cached = _price_cache.get(symbol)
    if cached and (now - cached[1]) < PRICE_CACHE_TTL:
        return cached[0]

    sym = symbol.upper().replace("-", "").replace("/", "")
    for mirror in BINANCE_MIRRORS:
        url = f"{mirror}/api/v3/ticker/price?symbol={sym}"
        data = _http_get(url)
        if data:
            try:
                price = float(json.loads(data)["price"])
                _price_cache[symbol] = (price, now)
                return price
            except (KeyError, ValueError, json.JSONDecodeError):
                continue
    return None


def fetch_price(symbol: str, asset_class: str) -> Optional[float]:
    """Fetch price based on asset class.  Non-crypto uses cached/entry price."""
    ac = (asset_class or "CRYPTO").upper()
    if ac == "CRYPTO":
        return fetch_crypto_price(symbol)
    # For forex/equity we cannot reliably fetch free prices with stdlib only.
    # Return None -- caller will use last known / entry price.
    return None


# ---------------------------------------------------------------------------
# Portfolio definitions
# ---------------------------------------------------------------------------
GOLDEN_FILTER_TRADERS = frozenset([
    "whale_20.7M", "NMTD_25M", "whale_123M_87roi",
    "whale_58M_287roi", "lb_NMTD",
])
# Also match partial labels (lb_NMTD matches "lb_NMTD -Thank you Jeff")
GOLDEN_FILTER_PREFIXES = ["whale_20.7M", "NMTD_25M", "whale_123M_87roi",
                           "whale_58M_287roi", "lb_NMTD"]

PORTFOLIO_DEFS: List[Dict[str, Any]] = [
    # --- CRYPTO (5) ---
    {
        "name": "GOLDEN_FILTER",
        "asset_class": "CRYPTO",
        "start_capital": 1000.0,
        "max_hold_hours": 48,
        "freshness_hours": 4,
        "description": "Top 5 traders + entry_score >= 70",
    },
    {
        "name": "MTF_GATED",
        "asset_class": "CRYPTO",
        "start_capital": 1000.0,
        "max_hold_hours": 48,
        "freshness_hours": 4,
        "description": "MTF 3-timeframe agreement + score >= 50",
    },
    {
        "name": "ENSEMBLE_2OF3",
        "asset_class": "CRYPTO",
        "start_capital": 1000.0,
        "max_hold_hours": 48,
        "freshness_hours": 4,
        "description": "2-of-3 ensemble gate (price+whale+structure)",
    },
    {
        "name": "SHORT_DOMINANT",
        "asset_class": "CRYPTO",
        "start_capital": 1000.0,
        "max_hold_hours": 48,
        "freshness_hours": 4,
        "description": "Short-dominant picks from short_dominant_picks.json",
    },
    {
        "name": "ROCKET_PICKS",
        "asset_class": "CRYPTO",
        "start_capital": 500.0,
        "max_hold_hours": 48,
        "freshness_hours": 4,
        "description": "Rocket picks from rocket_picks.json",
    },
    # --- FOREX (2) ---
    {
        "name": "PROVEN_FOREX",
        "asset_class": "FOREX",
        "start_capital": 500.0,
        "max_hold_hours": 168,
        "freshness_hours": 24,
        "description": "Proven forex strategies. Paper-trade only.",
    },
    {
        "name": "COT_CARRY",
        "asset_class": "FOREX",
        "start_capital": 500.0,
        "max_hold_hours": 168,
        "freshness_hours": 24,
        "description": "COT positioning + carry trade picks",
    },
    # --- EQUITY (1) ---
    {
        "name": "QUALITY_STOCKS",
        "asset_class": "EQUITY",
        "start_capital": 500.0,
        "max_hold_hours": 336,
        "freshness_hours": 24,
        "description": "quality-momentum-scout + connors_rsi2 only",
    },
]

MAX_POSITIONS = 10
MAX_EQUITY_PCT = 0.10  # 10% per position
MIN_KELLY = 0.01
DEFAULT_WR = 0.45  # before any data


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _parse_iso(s: str) -> Optional[datetime]:
    if not s:
        return None
    try:
        # Handle various ISO formats
        s = s.replace("Z", "+00:00")
        if "+" not in s and s.endswith("00:00"):
            pass
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def _age_hours(ts_str: str) -> float:
    dt = _parse_iso(ts_str)
    if dt is None:
        return 9999.0
    now = _utcnow()
    # Ensure both are tz-aware or both naive to avoid TypeError
    if dt.tzinfo is not None and now.tzinfo is None:
        now = now.replace(tzinfo=dt.tzinfo)
    elif dt.tzinfo is None and now.tzinfo is not None:
        dt = dt.replace(tzinfo=now.tzinfo)
    delta = now - dt
    return max(0.0, delta.total_seconds() / 3600.0)


def _load_json(path: Path) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        # Atomic rename (best-effort on Windows)
        if path.exists():
            path.unlink()
        tmp.rename(path)
    except Exception as e:
        logger.error("Failed to save %s: %s", path, e)
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def _matches_golden_trader(label: str) -> bool:
    """Check if a trader label matches one of the golden filter traders."""
    if not label:
        return False
    label_lower = label.lower()
    for prefix in GOLDEN_FILTER_PREFIXES:
        if label_lower.startswith(prefix.lower()):
            return True
    return False


# ---------------------------------------------------------------------------
# Pick sourcing
# ---------------------------------------------------------------------------
def _normalize_pick(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a pick from any source into a consistent structure."""
    symbol = (raw.get("symbol") or "").upper()
    direction = (raw.get("direction") or raw.get("signal_type") or "LONG").upper()
    if direction == "BUY":
        direction = "LONG"
    elif direction in ("SELL", "SHORT"):
        direction = "SHORT"

    entry_price = float(raw.get("entry_price") or 0)
    tp = float(raw.get("take_profit") or raw.get("tp") or 0)
    sl = float(raw.get("stop_loss") or raw.get("sl") or 0)

    # Determine asset class
    ac = (raw.get("asset_class") or raw.get("category") or "CRYPTO").upper()
    if ac in ("FOREX", "FX"):
        ac = "FOREX"
    elif ac in ("EQUITY", "STOCK", "STOCKS"):
        ac = "EQUITY"
    else:
        ac = "CRYPTO"

    strategy = raw.get("strategy") or raw.get("source_system") or "unknown"
    confidence = float(raw.get("confidence") or 0)
    entry_score = float(raw.get("entry_score") or raw.get("score") or
                        raw.get("elite_score") or (confidence * 100))

    ts = (raw.get("timestamp") or raw.get("entered_at") or
          raw.get("entry_date") or raw.get("discovered_at") or "")

    trader_label = raw.get("trader_label") or ""

    return {
        "symbol": symbol,
        "direction": direction,
        "entry_price": entry_price,
        "take_profit": tp,
        "stop_loss": sl,
        "asset_class": ac,
        "strategy": strategy,
        "confidence": confidence,
        "entry_score": entry_score,
        "timestamp": ts,
        "trader_label": trader_label,
        "source_id": raw.get("id") or f"{strategy}::{symbol}::{ts[:10] if ts else 'x'}",
        "paper_trade_only": ac != "CRYPTO" or raw.get("paper_trade_only", False),
        "status": (raw.get("status") or "OPEN").upper(),
        # Exit mechanics flags — opt-in, default False for backward compat.
        # New picks may set these to True to enable partial TP at tp1 and
        # breakeven SL activation after +1R.  Absent flag == legacy behavior.
        "partial_tp_enabled": bool(raw.get("partial_tp_enabled", False)),
        "breakeven_enabled": bool(raw.get("breakeven_enabled", False)),
    }


def load_all_picks() -> List[Dict[str, Any]]:
    """Load and normalize picks from all source files."""
    picks: List[Dict[str, Any]] = []
    seen_ids: set = set()

    def _add(raw_list: Any, source_tag: str = "") -> None:
        if not isinstance(raw_list, list):
            return
        for raw in raw_list:
            if not isinstance(raw, dict):
                continue
            p = _normalize_pick(raw)
            if not p["symbol"] or p["entry_price"] <= 0:
                continue
            if p["status"] not in ("OPEN", "ACTIVE"):
                continue
            pid = p["source_id"]
            if pid not in seen_ids:
                seen_ids.add(pid)
                if source_tag:
                    p["_source_tag"] = source_tag
                picks.append(p)

    # 1. Alpha engine active picks
    alpha_data = _load_json(ALPHA_PICKS)
    _add(alpha_data, "alpha")

    # 2. Copy trader active picks
    copy_data = _load_json(COPY_PICKS)
    _add(copy_data, "copy_trader")

    # 3. Highscore pick history (for golden filter trader matching)
    hs_data = _load_json(HIGHSCORE_HISTORY)
    _add(hs_data, "highscore")

    # 4. Dashboard payload (active picks)
    dash = _load_json(DASHBOARD_PAYLOAD)
    if isinstance(dash, dict):
        dash_picks = dash.get("picks", {})
        if isinstance(dash_picks, dict):
            _add(dash_picks.get("active", []), "dashboard_active")
            # Also load recent closed for WR tracking
        elif isinstance(dash_picks, list):
            _add(dash_picks, "dashboard")

    # 5. Short dominant picks
    sd_data = _load_json(SHORT_DOMINANT_FILE)
    _add(sd_data, "short_dominant")

    # 6. Rocket picks
    rk_data = _load_json(ROCKET_PICKS_FILE)
    _add(rk_data, "rocket")

    return picks


# ---------------------------------------------------------------------------
# Portfolio filtering
# ---------------------------------------------------------------------------
def _try_mtf_gate(symbol: str, direction: str) -> Optional[Dict]:
    """Try to call mtf_gate.check_mtf_alignment with fallback."""
    try:
        sys.path.insert(0, str(BASE_DIR))
        from mtf_gate import check_mtf_alignment
        bull_bear = "BULL" if direction == "LONG" else "BEAR"
        result = check_mtf_alignment(symbol, bull_bear)
        return result
    except Exception:
        return None


def _try_ensemble_gate(symbol: str, direction: str) -> Optional[Dict]:
    """Try to call ensemble_gate.check_ensemble with fallback."""
    try:
        sys.path.insert(0, str(BASE_DIR))
        from ensemble_gate import check_ensemble
        result = check_ensemble(symbol, direction)
        return result
    except Exception:
        return None


def filter_picks_for_portfolio(
    portfolio_name: str,
    all_picks: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Return picks that qualify for a specific portfolio."""
    result: List[Dict[str, Any]] = []

    for p in all_picks:
        ac = p["asset_class"]

        if portfolio_name == "GOLDEN_FILTER":
            if ac != "CRYPTO":
                continue
            # Check trader_label OR strategy name for golden trader match
            trader_match = _matches_golden_trader(p.get("trader_label", ""))
            if not trader_match:
                # Also check strategy name (e.g. "copy_hl_whale_123M_87roi")
                strat = p.get("strategy", "")
                trader_match = any(
                    prefix.lower() in strat.lower()
                    for prefix in GOLDEN_FILTER_PREFIXES
                )
            if not trader_match:
                continue
            if p["entry_score"] < 70:
                continue
            result.append(p)

        elif portfolio_name == "MTF_GATED":
            if ac != "CRYPTO":
                continue
            if p["entry_score"] < 50:
                continue
            # MTF check is expensive -- defer to position opening
            p["_needs_mtf"] = True
            result.append(p)

        elif portfolio_name == "ENSEMBLE_2OF3":
            if ac != "CRYPTO":
                continue
            # Ensemble check deferred to position opening
            p["_needs_ensemble"] = True
            result.append(p)

        elif portfolio_name == "SHORT_DOMINANT":
            if ac != "CRYPTO":
                continue
            if p.get("_source_tag") == "short_dominant":
                result.append(p)

        elif portfolio_name == "ROCKET_PICKS":
            if ac != "CRYPTO":
                continue
            if p.get("_source_tag") == "rocket":
                result.append(p)

        elif portfolio_name == "PROVEN_FOREX":
            if ac != "FOREX":
                continue
            # Accept forex strategies from any source
            strat = (p.get("strategy") or "").lower()
            forex_keywords = [
                "forex", "fx", "carry", "london", "eur", "gbp", "jpy",
                "usd", "aud", "nzd", "chf", "cad", "currency",
                "rsi_ema", "breakout",
            ]
            if any(kw in strat for kw in forex_keywords) or ac == "FOREX":
                p["paper_trade_only"] = True
                result.append(p)

        elif portfolio_name == "COT_CARRY":
            if ac != "FOREX":
                continue
            strat = (p.get("strategy") or "").lower()
            if any(kw in strat for kw in ("cot", "carry", "carry_trade", "carry-trade")):
                p["paper_trade_only"] = True
                result.append(p)

        elif portfolio_name == "QUALITY_STOCKS":
            if ac != "EQUITY":
                continue
            strat = (p.get("strategy") or "").lower()
            if any(kw in strat for kw in (
                "quality-momentum-scout", "quality_momentum_scout",
                "connors_rsi2", "connors-rsi2",
            )):
                p["paper_trade_only"] = True
                result.append(p)

    return result


# ---------------------------------------------------------------------------
# Position & portfolio state
# ---------------------------------------------------------------------------
def _new_portfolio_state(pdef: Dict[str, Any]) -> Dict[str, Any]:
    now = _iso(_utcnow())
    return {
        "portfolio_name": pdef["name"],
        "asset_class": pdef["asset_class"],
        "description": pdef["description"],
        "start_date_utc": now,
        "start_capital": pdef["start_capital"],
        "equity": pdef["start_capital"],
        "cash": pdef["start_capital"],
        "positions": [],
        "closed_positions": [],
        "stats": {
            "total_trades": 0,
            "open_trades": 0,
            "closed_trades": 0,
            "wins": 0,
            "losses": 0,
            "wr_pct": 0.0,
            "total_pnl_pct": 0.0,
            "total_pnl_dollar": 0.0,
            "max_drawdown_pct": 0.0,
            "sharpe_estimate": 0.0,
            "profit_factor": 0.0,
            "best_pick": None,
            "worst_pick": None,
            "peak_equity": pdef["start_capital"],
        },
        "pnl_series": [],  # list of (timestamp, equity) for sharpe/drawdown
    }


def _quarter_kelly(wr: float, avg_win: float, avg_loss: float) -> float:
    """Compute quarter-Kelly fraction.  Returns fraction of equity to risk."""
    if avg_loss <= 0 or avg_win <= 0:
        return MIN_KELLY
    b = avg_win / avg_loss  # win/loss ratio
    kelly = (wr * b - (1 - wr)) / b
    if kelly <= 0:
        return MIN_KELLY
    return max(MIN_KELLY, min(0.25 * kelly, 0.10))  # capped at 10%


def _compute_realized_wr(portfolio: Dict[str, Any]) -> float:
    """Compute realized WR from closed positions."""
    stats = portfolio["stats"]
    closed = stats["closed_trades"]
    if closed < 5:
        return DEFAULT_WR
    return stats["wins"] / closed if closed > 0 else DEFAULT_WR


def _compute_avg_win_loss(portfolio: Dict[str, Any]) -> Tuple[float, float]:
    """Compute average win and loss from closed positions."""
    wins_pnl: List[float] = []
    loss_pnl: List[float] = []
    for cp in portfolio.get("closed_positions", []):
        pnl = cp.get("realized_pnl_pct", 0)
        if pnl > 0:
            wins_pnl.append(pnl)
        elif pnl < 0:
            loss_pnl.append(abs(pnl))
    avg_w = sum(wins_pnl) / len(wins_pnl) if wins_pnl else 2.0
    avg_l = sum(loss_pnl) / len(loss_pnl) if loss_pnl else 1.5
    return avg_w, avg_l


def _position_size(portfolio: Dict[str, Any]) -> float:
    """Compute position size using quarter-Kelly."""
    equity = portfolio["equity"]
    wr = _compute_realized_wr(portfolio)
    avg_w, avg_l = _compute_avg_win_loss(portfolio)
    kelly_frac = _quarter_kelly(wr, avg_w, avg_l)
    size = kelly_frac * equity
    # Also enforce max 10% equity
    max_size = MAX_EQUITY_PCT * equity
    return max(1.0, min(size, max_size))


# ---------------------------------------------------------------------------
# Exit reason constants
# ---------------------------------------------------------------------------
# Standard reasons
EXIT_TP_HIT = "TP_HIT"
EXIT_SL_HIT = "SL_HIT"
EXIT_MAX_HOLD = "MAX_HOLD"
# Partial TP at the halfway point to the full TP (tp1).  When triggered the
# position closes 50% of its allocation and the remainder continues running.
EXIT_TP1_PARTIAL = "TP1_PARTIAL"
# Breakeven SL — after price moves +1R in favor, the SL is moved to entry.
# When that moved stop is hit, the exit reason is this constant (remainder
# pnl is approximately zero, converting a potential loss into a scratch).
EXIT_BREAKEVEN_SL = "BREAKEVEN_SL"


def _compute_tp1_price(entry: float, tp: float) -> float:
    """Half-distance to the full TP (same side as tp, regardless of direction)."""
    if entry <= 0 or tp <= 0:
        return 0.0
    return entry + (tp - entry) / 2.0


def _close_position_record(
    portfolio: Dict[str, Any],
    pos: Dict[str, Any],
    exit_price: float,
    exit_reason: str,
    now,
    allocation_override: Optional[float] = None,
    tag_suffix: str = "",
) -> float:
    """Build a closed_positions record, update cash + stats, return realized_pnl_dollar.

    allocation_override lets partial exits close only a fraction of the
    position's allocation without consuming the full remainder.
    """
    direction = pos["direction"]
    entry = pos["entry_price"]
    if direction == "LONG":
        realized_pnl_pct = ((exit_price - entry) / entry) * 100 if entry else 0
    else:
        realized_pnl_pct = ((entry - exit_price) / entry) * 100 if entry else 0

    alloc = allocation_override if allocation_override is not None else pos["allocation"]
    realized_pnl_dollar = realized_pnl_pct / 100 * alloc

    closed_pos = {
        **pos,
        "allocation": round(alloc, 2),
        "exit_time_utc": _iso(now),
        "exit_price": exit_price,
        "exit_reason": exit_reason,
        "realized_pnl_pct": round(realized_pnl_pct, 4),
        "realized_pnl_dollar": round(realized_pnl_dollar, 2),
        "status": exit_reason,
    }
    if tag_suffix:
        closed_pos["source_id"] = f"{pos.get('source_id', '')}{tag_suffix}"
    # Remove transient keys on the record
    for k in ("unrealized_pnl_pct", "unrealized_pnl_dollar", "last_price"):
        closed_pos.pop(k, None)

    portfolio["closed_positions"].append(closed_pos)
    portfolio["cash"] += alloc + realized_pnl_dollar

    stats = portfolio["stats"]
    stats["closed_trades"] += 1
    stats["total_pnl_dollar"] = round(
        stats["total_pnl_dollar"] + realized_pnl_dollar, 2)
    if realized_pnl_pct > 0:
        stats["wins"] += 1
    else:
        stats["losses"] += 1

    symbol = pos["symbol"]
    if stats["best_pick"] is None or realized_pnl_pct > (stats["best_pick"].get("pnl", -9999)):
        stats["best_pick"] = {
            "symbol": symbol, "pnl": round(realized_pnl_pct, 2),
            "strategy": pos.get("strategy", ""),
        }
    if stats["worst_pick"] is None or realized_pnl_pct < (stats["worst_pick"].get("pnl", 9999)):
        stats["worst_pick"] = {
            "symbol": symbol, "pnl": round(realized_pnl_pct, 2),
            "strategy": pos.get("strategy", ""),
        }

    logger.info(
        "[%s] CLOSED %s %s @ %.4f -> %.4f  PnL=%.2f%%  reason=%s  alloc=%.2f",
        portfolio["portfolio_name"], direction, symbol,
        entry, exit_price, realized_pnl_pct, exit_reason, alloc,
    )
    return realized_pnl_dollar


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------
def _check_exits(portfolio: Dict[str, Any], pdef: Dict[str, Any]) -> None:
    """Check TP/SL/max-hold and close positions accordingly."""
    now = _utcnow()
    max_hold = pdef["max_hold_hours"]
    still_open: List[Dict] = []

    for pos in portfolio["positions"]:
        symbol = pos["symbol"]
        ac = pos.get("asset_class", pdef["asset_class"])
        current_price = fetch_price(symbol, ac)

        if current_price is None:
            current_price = pos.get("last_price", pos["entry_price"])

        pos["last_price"] = current_price
        direction = pos["direction"]
        entry = pos["entry_price"]
        tp = pos["take_profit"]
        sl = pos["stop_loss"]

        # Compute unrealized PnL
        if direction == "LONG":
            pnl_pct = ((current_price - entry) / entry) * 100 if entry else 0
        else:
            pnl_pct = ((entry - current_price) / entry) * 100 if entry else 0

        pos["unrealized_pnl_pct"] = round(pnl_pct, 4)
        pos["unrealized_pnl_dollar"] = round(pnl_pct / 100 * pos["allocation"], 2)

        # ---- Opt-in exit mechanics: partial TP at tp1, breakeven at +1R ----
        partial_enabled = bool(pos.get("partial_tp_enabled", False))
        be_enabled = bool(pos.get("breakeven_enabled", False))

        # Partial TP at tp1 (half-distance to the full TP).  Fires once per
        # position; closes 50% of remaining allocation, keeps the rest running.
        if (
            partial_enabled
            and not pos.get("partial_tp_taken", False)
            and tp > 0 and entry > 0
        ):
            tp1 = _compute_tp1_price(entry, tp)
            tp1_touched = (
                (direction == "LONG" and current_price >= tp1 > 0)
                or (direction == "SHORT" and 0 < tp1 and current_price <= tp1)
            )
            if tp1_touched:
                half_alloc = pos["allocation"] / 2.0
                _close_position_record(
                    portfolio, pos, tp1, EXIT_TP1_PARTIAL, now,
                    allocation_override=half_alloc,
                    tag_suffix="::tp1",
                )
                # Shrink the live position to the remaining half.
                pos["allocation"] = round(pos["allocation"] - half_alloc, 2)
                pos["quantity"] = round(pos.get("quantity", 0) / 2.0, 8)
                pos["partial_tp_taken"] = True
                # Recompute unrealized on the smaller remainder
                pos["unrealized_pnl_dollar"] = round(
                    pnl_pct / 100 * pos["allocation"], 2)

        # Breakeven stop activation: once price has moved +1R in favor of the
        # trade (one stop-loss distance), slide the SL up/down to the entry.
        if (
            be_enabled
            and not pos.get("breakeven_activated", False)
            and sl > 0 and entry > 0
        ):
            r_distance = abs(entry - sl)
            if r_distance > 0:
                favorable = (
                    (direction == "LONG" and current_price - entry >= r_distance)
                    or (direction == "SHORT" and entry - current_price >= r_distance)
                )
                if favorable:
                    pos["stop_loss"] = entry
                    sl = entry  # reflect locally for same-bar SL check below
                    pos["breakeven_activated"] = True

        # Check exits
        exit_reason = None
        exit_price = current_price

        # TP hit (full TP)
        if direction == "LONG" and tp > 0 and current_price >= tp:
            exit_reason = EXIT_TP_HIT
        elif direction == "SHORT" and tp > 0 and current_price <= tp:
            exit_reason = EXIT_TP_HIT

        # SL hit (may be the breakeven-moved stop)
        if direction == "LONG" and sl > 0 and current_price <= sl:
            exit_reason = (
                EXIT_BREAKEVEN_SL if pos.get("breakeven_activated", False)
                and sl == entry else EXIT_SL_HIT
            )
        elif direction == "SHORT" and sl > 0 and current_price >= sl:
            exit_reason = (
                EXIT_BREAKEVEN_SL if pos.get("breakeven_activated", False)
                and sl == entry else EXIT_SL_HIT
            )

        # Max hold
        entry_time = _parse_iso(pos["entry_time_utc"])
        if entry_time and (now - entry_time).total_seconds() / 3600 > max_hold:
            exit_reason = EXIT_MAX_HOLD

        if exit_reason:
            _close_position_record(
                portfolio, pos, exit_price, exit_reason, now,
            )
        else:
            still_open.append(pos)

    portfolio["positions"] = still_open


def _update_equity(portfolio: Dict[str, Any]) -> None:
    """Recompute equity = cash + sum of position market values."""
    unrealized = sum(
        pos.get("unrealized_pnl_dollar", 0)
        for pos in portfolio["positions"]
    )
    allocated = sum(pos["allocation"] for pos in portfolio["positions"])
    portfolio["equity"] = round(portfolio["cash"] + allocated + unrealized, 2)

    stats = portfolio["stats"]
    stats["open_trades"] = len(portfolio["positions"])
    stats["total_trades"] = stats["open_trades"] + stats["closed_trades"]

    # WR
    closed = stats["closed_trades"]
    if closed > 0:
        stats["wr_pct"] = round(stats["wins"] / closed * 100, 1)
    else:
        stats["wr_pct"] = 0.0

    # PnL %
    start_cap = portfolio["start_capital"]
    if start_cap > 0:
        stats["total_pnl_pct"] = round(
            (portfolio["equity"] - start_cap) / start_cap * 100, 2)

    # Peak equity / drawdown
    if portfolio["equity"] > stats["peak_equity"]:
        stats["peak_equity"] = portfolio["equity"]
    if stats["peak_equity"] > 0:
        dd = (stats["peak_equity"] - portfolio["equity"]) / stats["peak_equity"] * 100
        stats["max_drawdown_pct"] = round(max(stats["max_drawdown_pct"], dd), 2)

    # Profit factor
    gross_wins = sum(
        cp.get("realized_pnl_dollar", 0) for cp in portfolio["closed_positions"]
        if cp.get("realized_pnl_dollar", 0) > 0
    )
    gross_losses = abs(sum(
        cp.get("realized_pnl_dollar", 0) for cp in portfolio["closed_positions"]
        if cp.get("realized_pnl_dollar", 0) < 0
    ))
    if gross_losses > 0:
        stats["profit_factor"] = round(gross_wins / gross_losses, 2)
    elif gross_wins > 0:
        stats["profit_factor"] = 999.0
    else:
        stats["profit_factor"] = 0.0

    # Sharpe estimate from PnL series
    series = portfolio.get("pnl_series", [])
    series.append((_iso(_utcnow()), portfolio["equity"]))
    # Keep last 500
    if len(series) > 500:
        series = series[-500:]
    portfolio["pnl_series"] = series

    if len(series) >= 3:
        returns = []
        for i in range(1, len(series)):
            prev_eq = series[i - 1][1]
            cur_eq = series[i][1]
            if prev_eq > 0:
                returns.append((cur_eq - prev_eq) / prev_eq)
        if returns:
            mean_r = sum(returns) / len(returns)
            var_r = sum((r - mean_r) ** 2 for r in returns) / len(returns)
            std_r = math.sqrt(var_r) if var_r > 0 else 1e-9
            stats["sharpe_estimate"] = round(mean_r / std_r, 4)


def _open_new_positions(
    portfolio: Dict[str, Any],
    pdef: Dict[str, Any],
    candidates: List[Dict[str, Any]],
) -> None:
    """Open new positions from candidate picks, respecting limits."""
    now = _utcnow()
    freshness = pdef["freshness_hours"]

    # Current open symbols
    open_symbols = {pos["symbol"] for pos in portfolio["positions"]}
    capacity = MAX_POSITIONS - len(portfolio["positions"])
    if capacity <= 0:
        return

    for pick in candidates:
        if capacity <= 0:
            break

        symbol = pick["symbol"]
        if symbol in open_symbols:
            continue

        # Freshness check
        age = _age_hours(pick.get("timestamp", ""))
        if age > freshness:
            continue

        # Deferred gate checks
        if pick.get("_needs_mtf"):
            mtf_result = _try_mtf_gate(symbol, pick["direction"])
            if mtf_result and not mtf_result.get("aligned", False):
                continue

        if pick.get("_needs_ensemble"):
            ens_result = _try_ensemble_gate(symbol, pick["direction"])
            if ens_result and not ens_result.get("passes", False):
                continue

        # Position sizing
        alloc = _position_size(portfolio)
        if alloc > portfolio["cash"]:
            continue

        entry_price = pick["entry_price"]
        if entry_price <= 0:
            continue

        quantity = alloc / entry_price if entry_price > 0 else 0

        pos = {
            "symbol": symbol,
            "direction": pick["direction"],
            "entry_price": entry_price,
            "take_profit": pick["take_profit"],
            "stop_loss": pick["stop_loss"],
            "quantity": round(quantity, 8),
            "allocation": round(alloc, 2),
            "strategy": pick.get("strategy", "unknown"),
            "entry_time_utc": _iso(now),
            "entry_score": pick.get("entry_score", 0),
            "trader_label": pick.get("trader_label", ""),
            "asset_class": pick.get("asset_class", pdef["asset_class"]),
            "paper_trade_only": pick.get("paper_trade_only", False),
            "source_id": pick.get("source_id", ""),
            "last_price": entry_price,
            "unrealized_pnl_pct": 0.0,
            "unrealized_pnl_dollar": 0.0,
            # Exit mechanics state (opt-in per pick; absent flag == legacy).
            "partial_tp_enabled": bool(pick.get("partial_tp_enabled", False)),
            "breakeven_enabled": bool(pick.get("breakeven_enabled", False)),
            "partial_tp_taken": False,
            "breakeven_activated": False,
        }

        portfolio["positions"].append(pos)
        portfolio["cash"] -= alloc
        open_symbols.add(symbol)
        capacity -= 1

        logger.info(
            "[%s] OPENED %s %s @ %.4f  alloc=$%.2f  tp=%.4f  sl=%.4f",
            portfolio["portfolio_name"], pick["direction"], symbol,
            entry_price, alloc, pick["take_profit"], pick["stop_loss"],
        )


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------
def load_state() -> Dict[str, Dict[str, Any]]:
    """Load portfolio state from disk, initializing missing portfolios."""
    raw = _load_json(STATE_FILE)
    state: Dict[str, Dict[str, Any]] = {}

    if isinstance(raw, dict):
        state = raw

    # Ensure all portfolios exist
    for pdef in PORTFOLIO_DEFS:
        name = pdef["name"]
        if name not in state:
            state[name] = _new_portfolio_state(pdef)

    return state


def save_state(state: Dict[str, Dict[str, Any]]) -> None:
    _save_json(STATE_FILE, state)


def append_history(state: Dict[str, Dict[str, Any]]) -> None:
    """Append a snapshot to history (capped)."""
    history = _load_json(HISTORY_FILE)
    if not isinstance(history, list):
        history = []

    snapshot = {
        "timestamp": _iso(_utcnow()),
        "portfolios": {},
    }
    for name, pstate in state.items():
        snapshot["portfolios"][name] = {
            "equity": pstate["equity"],
            "pnl_pct": pstate["stats"]["total_pnl_pct"],
            "wr_pct": pstate["stats"]["wr_pct"],
            "open_trades": pstate["stats"]["open_trades"],
            "closed_trades": pstate["stats"]["closed_trades"],
            "max_drawdown_pct": pstate["stats"]["max_drawdown_pct"],
            "profit_factor": pstate["stats"]["profit_factor"],
            "sharpe": pstate["stats"]["sharpe_estimate"],
        }

    history.append(snapshot)
    if len(history) > HISTORY_CAP:
        history = history[-HISTORY_CAP:]

    _save_json(HISTORY_FILE, history)


# ---------------------------------------------------------------------------
# Console output
# ---------------------------------------------------------------------------
def print_comparison_table(state: Dict[str, Dict[str, Any]]) -> None:
    """Print ranked comparison table of all portfolios."""
    rows: List[Tuple[float, str, Dict]] = []
    for name, pstate in state.items():
        rows.append((pstate["equity"], name, pstate))

    # Rank by equity descending
    rows.sort(key=lambda x: x[0], reverse=True)

    header = (
        f"{'Rank':<5} {'Portfolio':<18} {'Equity':>10} {'PnL%':>8} "
        f"{'WR%':>6} {'Open':>5} {'Closed':>7} {'MaxDD%':>8} "
        f"{'PF':>6} {'Sharpe':>7} {'Best Pick':<20} {'Worst Pick':<20}"
    )
    sep = "-" * len(header)

    print("\n" + sep)
    print("  FORWARD-TEST PORTFOLIO COMPARISON  ".center(len(header)))
    print(f"  {_iso(_utcnow())}  ".center(len(header)))
    print(sep)
    print(header)
    print(sep)

    for rank, (equity, name, pstate) in enumerate(rows, 1):
        stats = pstate["stats"]
        best = stats.get("best_pick")
        worst = stats.get("worst_pick")
        best_str = f"{best['symbol']} {best['pnl']:+.1f}%" if best else "---"
        worst_str = f"{worst['symbol']} {worst['pnl']:+.1f}%" if worst else "---"

        print(
            f"{rank:<5} {name:<18} ${equity:>9.2f} {stats['total_pnl_pct']:>+7.2f}% "
            f"{stats['wr_pct']:>5.1f}% {stats['open_trades']:>5} "
            f"{stats['closed_trades']:>7} {stats['max_drawdown_pct']:>7.2f}% "
            f"{stats['profit_factor']:>5.2f} {stats['sharpe_estimate']:>7.4f} "
            f"{best_str:<20} {worst_str:<20}"
        )

    print(sep)
    total_equity = sum(r[0] for r in rows)
    total_capital = sum(
        pstate["start_capital"]
        for pstate in state.values()
    )
    overall_pnl = ((total_equity - total_capital) / total_capital * 100
                    if total_capital > 0 else 0)
    print(
        f"{'':>5} {'TOTAL':<18} ${total_equity:>9.2f} {overall_pnl:>+7.2f}% "
        f"{'':>6} {sum(s['stats']['open_trades'] for s in state.values()):>5} "
        f"{sum(s['stats']['closed_trades'] for s in state.values()):>7}"
    )
    print(sep + "\n")


# ---------------------------------------------------------------------------
# Main run
# ---------------------------------------------------------------------------
def run() -> Dict[str, Dict[str, Any]]:
    """
    Main entry point.  Sources picks, updates all 8 portfolios,
    persists state, appends history, prints comparison table.
    Returns the full state dict.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger.info("=== Forward-Test Portfolio System ===")

    # 1. Load state
    state = load_state()

    # 2. Load all picks
    all_picks = load_all_picks()
    logger.info("Loaded %d total picks from all sources", len(all_picks))

    # 3. Process each portfolio
    pdef_map = {pd["name"]: pd for pd in PORTFOLIO_DEFS}

    for pdef in PORTFOLIO_DEFS:
        name = pdef["name"]
        portfolio = state[name]
        logger.info("--- Processing portfolio: %s ---", name)

        # Filter picks for this portfolio
        candidates = filter_picks_for_portfolio(name, copy.deepcopy(all_picks))
        logger.info("  %d candidate picks for %s", len(candidates), name)

        # Check exits on existing positions
        _check_exits(portfolio, pdef)

        # Open new positions
        _open_new_positions(portfolio, pdef, candidates)

        # Update equity and stats
        _update_equity(portfolio)

        # Cap closed_positions to last 200 to prevent unbounded growth
        if len(portfolio["closed_positions"]) > 200:
            portfolio["closed_positions"] = portfolio["closed_positions"][-200:]

    # 4. Save state
    save_state(state)

    # 5. Append history
    append_history(state)

    # 6. Print comparison table
    print_comparison_table(state)

    logger.info("=== Forward-Test complete ===")
    return state


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    state = run()
    
    # Sync picks to live_forward_test_picks.json for dashboard display
    import sync_forward_test_picks
    sync_forward_test_picks.sync_picks()
