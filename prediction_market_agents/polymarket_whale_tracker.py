#!/usr/bin/env python3
"""Polymarket whale tracker wrapper.

This module consumes the shared crypto-only wallet scanner in
`copy_trader_intel.polymarket_scraper` and adds a direct-position fallback for
wallets that do not already produce vetted copyable picks.
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from copy_trader_intel.polymarket_scraper import _evaluate_entry_quality, _parse_dt

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# API constants
# ---------------------------------------------------------------------------
POSITIONS_API = "https://data-api.polymarket.com/positions"
GAMMA_MARKETS_API = "https://gamma-api.polymarket.com/markets"
BINANCE_PRICE_URLS = [
    "https://data-api.binance.vision/api/v3/ticker/price",
    "https://api.binance.us/api/v3/ticker/price",
    "https://api1.binance.com/api/v3/ticker/price",
    "https://api2.binance.com/api/v3/ticker/price",
    "https://api3.binance.com/api/v3/ticker/price",
    "https://api.binance.com/api/v3/ticker/price",
]
COINGECKO_IDS = {
    "BTCUSDT": "bitcoin",
    "ETHUSDT": "ethereum",
    "SOLUSDT": "solana",
    "XRPUSDT": "ripple",
    "DOGEUSDT": "dogecoin",
    "ADAUSDT": "cardano",
    "BNBUSDT": "binancecoin",
    "AVAXUSDT": "avalanche-2",
}

_REQUEST_TIMEOUT = 20
_REQUEST_HEADERS = {
    "User-Agent": "PolymarketWhaleTracker/1.0",
    "Accept": "application/json",
}

# SSL context that works in CI (no cert verification)
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

GAMMA_MARKETS_URL = "https://gamma-api.polymarket.com/markets"
DATA_TRADES_URL = "https://data-api.polymarket.com/trades"
CLOB_TRADES_URL = "https://clob.polymarket.com/trades"

# Minimum USD notional for a trade to count a wallet as active in that market
_MIN_TRADE_NOTIONAL = 5.0
# How many top active wallets per discovery pass to collect
_MAX_DISCOVERY_WALLETS = 20
# How many top crypto markets to scan when using trade-based discovery
_MARKETS_TO_SCAN = 8

# Crypto asset matching rules (symbol -> regex patterns on market question text)
_ASSET_RULES: list[tuple[str, list[re.Pattern[str]]]] = [
    ("BTCUSDT", [re.compile(r"\bbitcoin\b", re.I), re.compile(r"\bbtc\b", re.I)]),
    ("ETHUSDT", [re.compile(r"\bethereum\b", re.I), re.compile(r"\beth\b", re.I)]),
    ("SOLUSDT", [re.compile(r"\bsolana\b", re.I), re.compile(r"\bsol\b", re.I)]),
    ("XRPUSDT", [re.compile(r"\bripple\b", re.I), re.compile(r"\bxrp\b", re.I)]),
    ("DOGEUSDT", [re.compile(r"\bdogecoin\b", re.I), re.compile(r"\bdoge\b", re.I)]),
    ("ADAUSDT", [re.compile(r"\bcardano\b", re.I), re.compile(r"\bada\b", re.I)]),
    ("BNBUSDT", [re.compile(r"\bbinance coin\b", re.I), re.compile(r"\bbnb\b", re.I)]),
    ("AVAXUSDT", [re.compile(r"\bavax\b", re.I)]),
]

_SPOT_CACHE: dict[str, float | None] = {}

DATA_DIR = Path(__file__).parent / "data"
OUTPUT_FILE = DATA_DIR / "whale_tracker.json"
WHALE_SIGNALS_FILE = DATA_DIR / "whale_signals.json"
WHALE_ALERTS_FILE = DATA_DIR / "whale_alerts.json"

# Kill-switch: set WHALE_SCANNER_ENABLED=0 in env to disable scan_large_trades.
# Default is ON (analytics only — no auto-trading ever).
_WHALE_SCANNER_ENABLED = os.environ.get("WHALE_SCANNER_ENABLED", "1").strip() not in ("0", "false", "no", "off")


def _fetch_json(url: str, params: dict[str, Any] | None = None) -> Any:
    """Fetch JSON via stdlib. SSL verify disabled for CI compatibility."""
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=_REQUEST_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT, context=_SSL_CTX) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        logger.warning("HTTP %s for %s", exc.code, url)
    except urllib.error.URLError as exc:
        logger.warning("URL error for %s: %s", url, exc.reason)
    except Exception as exc:
        logger.warning("Fetch failed for %s: %s", url, exc)
    return None


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _fetch_spot_price(symbol: str) -> float | None:
    """Get current price from Binance (with mirror fallback) or CoinGecko."""
    if symbol in _SPOT_CACHE:
        return _SPOT_CACHE[symbol]

    # Try Binance mirrors
    for base_url in BINANCE_PRICE_URLS:
        data = _fetch_json(base_url, {"symbol": symbol})
        if isinstance(data, dict) and _safe_float(data.get("price")) > 0:
            price = _safe_float(data["price"])
            _SPOT_CACHE[symbol] = price
            return price

    # Fallback: CoinGecko
    cg_id = COINGECKO_IDS.get(symbol)
    if cg_id:
        data = _fetch_json(
            "https://api.coingecko.com/api/v3/simple/price",
            {"ids": cg_id, "vs_currencies": "usd"},
        )
        if isinstance(data, dict) and cg_id in data:
            price = _safe_float(data[cg_id].get("usd"))
            if price > 0:
                _SPOT_CACHE[symbol] = price
                return price

    _SPOT_CACHE[symbol] = None
    return None


def _match_crypto_symbol(text: str) -> str | None:
    """Match market question text to a crypto trading symbol."""
    for symbol, patterns in _ASSET_RULES:
        if any(p.search(text) for p in patterns):
            return symbol
    return None


def _infer_direction(question: str, outcome: str) -> str | None:
    """Infer LONG/SHORT from market question + whale's outcome (YES/NO)."""
    q = (question or "").lower()
    o = (outcome or "").lower().strip()
    if not q or not o:
        return None

    # "up or down" style markets
    if "up or down" in q:
        if o == "up":
            return "LONG"
        if o == "down":
            return "SHORT"
        return None

    # Range / between markets are ambiguous
    if "between" in q:
        return None

    # "Will X reach / be above / hit $Y?" style
    if re.search(r"\b(reach|hit|above|over|at least|exceed|surpass)\b", q):
        return "LONG" if o == "yes" else ("SHORT" if o == "no" else None)

    # "Will X dip / fall below $Y?" style
    if re.search(r"\b(dip|below|under|drop|fall)\b", q):
        return "SHORT" if o == "yes" else ("LONG" if o == "no" else None)

    return None


# ---------------------------------------------------------------------------
# Core: fetch whale positions and convert to signals
# ---------------------------------------------------------------------------

def fetch_wallet_positions(wallet_address: str) -> list[dict[str, Any]]:
    """
    Fetch current active positions for a Polymarket wallet.
    Returns raw position objects from the Polymarket Data API.
    """
    data = _fetch_json(POSITIONS_API, {
        "user": wallet_address,
        "sizeThreshold": 100,
        "sortBy": "CURRENT",
        "limit": 50,
    })
    if isinstance(data, list):
        logger.info("  Wallet %s...%s: %d positions", wallet_address[:6], wallet_address[-4:], len(data))
        return data
    logger.warning("  Wallet %s...%s: no positions returned", wallet_address[:6], wallet_address[-4:])
    return []


def _lookup_market(condition_id: str) -> dict[str, Any] | None:
    """Look up market question/details via Gamma API."""
    data = _fetch_json(GAMMA_MARKETS_API, {"condition_id": condition_id})
    if isinstance(data, list) and len(data) > 0:
        return data[0]
    if isinstance(data, dict) and data.get("question"):
        return data
    return None


def positions_to_signals(
    positions: list[dict[str, Any]],
    whale_profile: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Convert raw Polymarket positions into alpha_engine-compatible trading signals.

    For each position:
      1. Look up the market question via Gamma API
      2. Check if it's crypto-related
      3. Infer direction (LONG/SHORT) from question + outcome
      4. Fetch current Binance price for entry
      5. Build signal with TP/SL
      6. Blend adjusted WR, recency, and copyability metadata from the shared scanner
    """
    now = datetime.now(timezone.utc)
    signals: list[dict[str, Any]] = []
    seen_symbols: set[str] = set()  # one signal per symbol per whale

    wallet = whale_profile.get("wallet", "")
    username = whale_profile.get("user_name") or whale_profile.get("username") or wallet
    raw_win_rate = _safe_float(whale_profile.get("crypto_win_rate") or whale_profile.get("history_wr"), 0.5)
    win_rate = _safe_float(
        whale_profile.get("crypto_win_rate_bayes")
        or whale_profile.get("history_wr_bayes")
        or whale_profile.get("history_posterior_wr")
        or raw_win_rate,
        raw_win_rate,
    )
    whale_pnl = _safe_float(whale_profile.get("crypto_total_pnl") or whale_profile.get("leaderboard_pnl"), 0.0)
    profile_score = _safe_float(whale_profile.get("crypto_profile_score"), 0.0)
    sample_tier = str(whale_profile.get("crypto_sample_tier") or "insufficient")
    archetype = str(whale_profile.get("wallet_archetype") or "unknown")
    copyable_archetype = bool(whale_profile.get("copyable_archetype", True))
    if not copyable_archetype:
        return []

    recent_30d_score = _safe_float(whale_profile.get("crypto_recent_score_30d"), 0.0)
    recent_90d_score = _safe_float(whale_profile.get("crypto_recent_score_90d"), 0.0)
    recent_30d_decisions = int(_safe_float(whale_profile.get("crypto_recent_decisions_30d"), 0))
    recent_90d_decisions = int(_safe_float(whale_profile.get("crypto_recent_decisions_90d"), 0))
    latency_arb_flag = bool(whale_profile.get("latency_arb_flag", False))
    latency_arb_score = _safe_float(whale_profile.get("latency_arb_score"), 0.0)
    copyability_gate_reason = str(whale_profile.get("copyability_gate_reason") or "")
    archetype_copyable = bool(whale_profile.get("archetype_copyable", copyable_archetype))
    top_symbol = str(whale_profile.get("crypto_top_symbol") or "")
    top_symbol_share = _safe_float(whale_profile.get("crypto_top_symbol_pnl_share"), 0.0)

    ranked_positions = sorted(
        positions,
        key=lambda pos: abs(
            _safe_float(pos.get("currentValue"))
            or (
                _safe_float(pos.get("size"))
                * _safe_float(pos.get("curPrice") or pos.get("avgPrice"))
            )
        ),
        reverse=True,
    )

    for pos in ranked_positions:
        try:
            condition_id = pos.get("conditionId") or pos.get("condition_id") or ""
            market: dict[str, Any] | None = None

            # Prefer title/question already embedded in the position (Data API returns it).
            # Fall back to GAMMA lookup only when the position lacks a title — GAMMA lookups
            # by condition_id are unreliable for Data API position rows.
            question = pos.get("title") or pos.get("question") or ""
            if not question and condition_id:
                market = _lookup_market(condition_id)
                if market:
                    question = market.get("question") or market.get("title") or ""

            symbol = _match_crypto_symbol(question)
            if not symbol:
                continue  # not crypto-related

            # Determine outcome (YES/NO) from position
            outcome = pos.get("outcome") or ""
            if not outcome:
                # Infer from size + side fields
                size = _safe_float(pos.get("size"))
                if size > 0:
                    outcome = "Yes"
                else:
                    continue

            direction = _infer_direction(question, outcome)
            if not direction:
                logger.debug("  Could not infer direction for: %s [%s]", question, outcome)
                continue

            if symbol in seen_symbols:
                continue  # already have a signal for this symbol from this whale

            contract_price = _safe_float(pos.get("curPrice") or pos.get("avgPrice"))
            if contract_price <= 0.0 or contract_price >= 1.0:
                continue

            pos_value = _safe_float(pos.get("currentValue"), 0.0)
            if pos_value <= 0:
                pos_value = abs(_safe_float(pos.get("size")) * contract_price)

            end_date = str(pos.get("endDate") or pos.get("end_date") or "")
            if not end_date and condition_id:
                market = market or _lookup_market(condition_id)
                if market:
                    end_date = str(market.get("endDate") or market.get("end_date") or "")
            end_dt = _parse_dt(end_date)
            if end_dt is None:
                continue
            hours_to_expiry = (end_dt - now).total_seconds() / 3600
            entry_quality = _evaluate_entry_quality(
                directional_notional=pos_value,
                lead_notional=pos_value,
                hours_to_expiry=hours_to_expiry,
                contract_price=contract_price,
                market_count=1,
            )
            if not entry_quality["entry_quality_pass"]:
                continue

            # Fetch current spot price
            entry_price = _fetch_spot_price(symbol)
            if not entry_price or entry_price <= 0:
                continue

            # Calculate confidence from whale stats
            # Base 0.55, then blend adjusted WR, profile quality, recency,
            # and copyability/concentration penalties from the shared scanner.
            wr_bonus = min(max((win_rate - 0.55) / 0.25, 0.0), 1.0) * 0.15
            pnl_bonus = min(math.log10(max(abs(whale_pnl), 1.0) + 1.0) / 5.0, 1.0) * 0.10
            size_bonus = min(pos_value / 5000.0, 1.0) * 0.10
            profile_bonus = min(profile_score / 0.75, 1.0) * 0.05
            entry_quality_bonus = min(_safe_float(entry_quality.get("entry_quality_score")) / 0.80, 1.0) * 0.05
            recent_bonus = 0.0
            if recent_30d_decisions >= 5:
                recent_bonus = min(recent_30d_score / 0.85, 1.0) * 0.05
            elif recent_90d_decisions >= 8:
                recent_bonus = min(recent_90d_score / 0.85, 1.0) * 0.03
            concentration_penalty = min(max((top_symbol_share - 0.60) / 0.25, 0.0), 1.0) * 0.07
            archetype_penalty = 0.08 if not copyable_archetype else 0.0
            confidence = round(
                min(
                    0.95,
                    max(
                        0.50,
                        0.55
                        + wr_bonus
                        + pnl_bonus
                        + size_bonus
                        + profile_bonus
                        + entry_quality_bonus
                        + recent_bonus
                        - concentration_penalty
                        - archetype_penalty,
                    ),
                ),
                3,
            )

            # TP/SL: 2.5% / 1.5% standard crypto
            tp_pct, sl_pct = 0.025, 0.015
            if direction == "LONG":
                take_profit = round(entry_price * (1 + tp_pct), 8)
                stop_loss = round(entry_price * (1 - sl_pct), 8)
                signal_type = "BUY"
            else:
                take_profit = round(entry_price * (1 - tp_pct), 8)
                stop_loss = round(entry_price * (1 + sl_pct), 8)
                signal_type = "SELL"

            strategy = f"pm_whale_{wallet[:8]}"
            ts = now.strftime("%Y-%m-%d_%H%M")

            signal = {
                "id": f"{strategy}::{symbol}::{ts}",
                "symbol": symbol,
                "direction": direction,
                "signal_type": signal_type,
                "entry_price": round(entry_price, 8),
                "take_profit": take_profit,
                "stop_loss": stop_loss,
                "confidence": confidence,
                "strategy": strategy,
                "source_system": "polymarket_whale_tracker",
                "signal_origin": "direct_position_inference",
                "category": "crypto",
                "status": "OPEN",
                "entry_date": now.strftime("%Y-%m-%d"),
                "timestamp": now.isoformat(),
                "allocation": 100,
                "position_sizing": "whale_copy",
                "risk_per_trade_pct": 0.008,
                "max_safe_leverage": 2,
                "reason": (
                    f"Polymarket whale {username} (adj WR {win_rate:.0%}, raw WR {raw_win_rate:.0%}, "
                    f"PnL ${whale_pnl:,.0f}, archetype {archetype}, latency risk {latency_arb_score:.2f}, "
                    f"entry quality {_safe_float(entry_quality.get('entry_quality_score')):.2f}) "
                    f"holds {direction} position on '{question[:80]}' -> {symbol}"
                ),
                "entry_quality_pass": entry_quality.get("entry_quality_pass", True),
                "entry_quality_score": entry_quality.get("entry_quality_score"),
                "entry_quality_gate_reason": entry_quality.get("entry_quality_gate_reason"),
                "entry_quality_contract_price": entry_quality.get("entry_quality_contract_price"),
                "whale_data": {
                    "wallet": wallet,
                    "username": username,
                    "win_rate_raw": raw_win_rate,
                    "win_rate": win_rate,
                    "pnl": whale_pnl,
                    "crypto_sample_tier": sample_tier,
                    "crypto_profile_score": profile_score,
                    "crypto_recent_score_30d": recent_30d_score,
                    "crypto_recent_score_90d": recent_90d_score,
                    "wallet_archetype": archetype,
                    "archetype_copyable": archetype_copyable,
                    "copyable_archetype": copyable_archetype,
                    "copyability_gate_reason": copyability_gate_reason,
                    "latency_arb_flag": latency_arb_flag,
                    "latency_arb_score": latency_arb_score,
                    "crypto_top_symbol": top_symbol,
                    "crypto_top_symbol_pnl_share": top_symbol_share,
                    "market_question": question,
                    "condition_id": condition_id,
                    "position_outcome": outcome,
                    "position_size": _safe_float(pos.get("size")),
                    "position_value": pos_value,
                    "position_pnl": _safe_float(pos.get("cashPnl") or pos.get("realizedPnl")),
                    "hours_to_expiry": round(hours_to_expiry, 2),
                    "market_end_date": end_date,
                    "entry_quality": entry_quality,
                },
            }
            seen_symbols.add(symbol)
            signals.append(signal)
            logger.info(
                "  SIGNAL: %s %s @ %.2f (conf=%.3f) from whale %s — %s",
                direction, symbol, entry_price, confidence, username, question[:60],
            )

        except Exception as exc:
            logger.warning("  Error processing position for wallet %s: %s", wallet[:10], exc)
            continue

    return signals


def _save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=str)


def _resolve_signal_direction_conflicts(signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_symbol: dict[str, list[dict[str, Any]]] = {}
    for signal in signals:
        symbol = str(signal.get("symbol") or "").upper()
        if not symbol:
            continue
        by_symbol.setdefault(symbol, []).append(signal)

    resolved: list[dict[str, Any]] = []
    for symbol, group in by_symbol.items():
        directions = {str(s.get("direction") or "").upper() for s in group if s.get("direction")}
        if len(directions) <= 1:
            resolved.extend(group)
            continue

        direction_scores: dict[str, tuple[float, float, int]] = {}
        for direction in ("LONG", "SHORT"):
            direction_group = [s for s in group if str(s.get("direction") or "").upper() == direction]
            if not direction_group:
                continue
            total_conf = sum(_safe_float(s.get("confidence")) for s in direction_group)
            top_conf = max(_safe_float(s.get("confidence")) for s in direction_group)
            direction_scores[direction] = (total_conf, top_conf, len(direction_group))

        winner_direction = max(
            direction_scores.items(),
            key=lambda item: (item[1][0], item[1][1], item[1][2]),
        )[0]
        resolved.extend(
            signal
            for signal in group
            if str(signal.get("direction") or "").upper() == winner_direction
        )

    return resolved


def _to_agent_signal(pick: dict[str, Any]) -> dict[str, Any]:
    signal = dict(pick)
    signal["source_system"] = "polymarket_whale_tracker"
    signal["status"] = "OPEN"
    signal["signal_origin"] = "vetted_wallet_copy"
    signal.setdefault("entry_price", 0)
    signal.setdefault("take_profit", 0)
    signal.setdefault("stop_loss", 0)
    signal.setdefault("entry_date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    signal.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    history_wr_bayes = (
        pick.get("history_wr_bayes")
        or pick.get("history_posterior_wr")
        or pick.get("history_wr")
    )
    signal["whale_data"] = {
        "wallet": pick.get("trader_address"),
        "username": pick.get("trader_name"),
        "leaderboard_rank": pick.get("leaderboard_rank"),
        "leaderboard_pnl": pick.get("trader_pnl"),
        "leaderboard_source": pick.get("leaderboard_source"),
        "crypto_profit_rank": pick.get("crypto_profit_rank"),
        "crypto_volume_rank": pick.get("crypto_volume_rank"),
        "history_trades": pick.get("history_trades"),
        "history_wr": pick.get("history_wr"),
        "history_wr_bayes": history_wr_bayes,
        "history_posterior_wr": history_wr_bayes,
        "history_total_pnl": pick.get("history_total_pnl"),
        "profile_crypto_wr": pick.get("profile_crypto_wr"),
        "profile_crypto_wr_bayes": pick.get("profile_crypto_wr_bayes"),
        "profile_crypto_score": pick.get("profile_crypto_score"),
        "profile_crypto_sample_tier": pick.get("profile_crypto_sample_tier"),
        "profile_crypto_recent_score_30d": pick.get("profile_crypto_recent_score_30d"),
        "profile_crypto_recent_score_90d": pick.get("profile_crypto_recent_score_90d"),
        "wallet_archetype": pick.get("wallet_archetype"),
        "archetype_copyable": pick.get("archetype_copyable", True),
        "copyable_archetype": pick.get("copyable_archetype", True),
        "copyability_gate_reason": pick.get("copyability_gate_reason"),
        "latency_arb_flag": pick.get("latency_arb_flag", False),
        "latency_arb_score": pick.get("latency_arb_score"),
        "entry_quality_pass": pick.get("entry_quality_pass", True),
        "entry_quality_score": pick.get("entry_quality_score"),
        "entry_quality_gate_reason": pick.get("entry_quality_gate_reason"),
        "entry_quality_contract_price": pick.get("entry_quality_contract_price"),
        "entry_quality_directional_notional": pick.get("entry_quality_directional_notional"),
        "entry_quality_lead_notional": pick.get("entry_quality_lead_notional"),
        "crypto_top_symbol": pick.get("crypto_top_symbol"),
        "crypto_top_symbol_pnl_share": pick.get("crypto_top_symbol_pnl_share"),
        "copy_signal": pick.get("copy_signal", {}),
    }
    return signal


def _fetch_active_crypto_condition_ids(max_markets: int = _MARKETS_TO_SCAN) -> list[str]:
    """Return conditionIds for the top-volume active crypto directional markets."""
    result = _fetch_json(
        GAMMA_MARKETS_URL,
        {
            "active": "true",
            "closed": "false",
            "order": "volume",
            "ascending": "false",
            "limit": "500",
        },
    )
    if not isinstance(result, list):
        return []

    crypto_patterns = [
        re.compile(r"\bbitcoin\b", re.I), re.compile(r"\bbtc\b", re.I),
        re.compile(r"\bethereum\b", re.I), re.compile(r"\beth\b", re.I),
        re.compile(r"\bsolana\b", re.I), re.compile(r"\bsol\b", re.I),
        re.compile(r"\bxrp\b", re.I), re.compile(r"\bdoge\b", re.I),
    ]
    directional_kw = ["up or down", "above", "below", "reach", "dip", "hit", "fall"]
    condition_ids: list[str] = []
    for m in result:
        cid = str(m.get("conditionId") or "")
        if len(cid) < 20:
            continue
        q = (m.get("question") or "").lower()
        if any(p.search(q) for p in crypto_patterns) and any(kw in q for kw in directional_kw):
            condition_ids.append(cid)
            if len(condition_ids) >= max_markets:
                break

    logger.info("Found %d active crypto directional markets for trade scan", len(condition_ids))
    return condition_ids


def _discover_crypto_traders(max_wallets: int = _MAX_DISCOVERY_WALLETS) -> list[dict[str, Any]]:
    """
    Discover wallets actively trading crypto Polymarket markets by scanning
    recent trades on top-volume active crypto directional markets.

    Used when the shared leaderboard scanner finds no qualified profiles
    (leaderboard leaders typically bet on politics/sports, not crypto).
    """
    condition_ids = _fetch_active_crypto_condition_ids()
    if not condition_ids:
        logger.warning("No crypto markets found for trade-based wallet discovery")
        return []

    wallet_notional: dict[str, float] = {}
    wallet_trade_count: dict[str, int] = {}
    wallet_market_count: dict[str, set] = {}
    for cid in condition_ids:
        trades = _fetch_json(DATA_TRADES_URL, {"conditionId": cid, "limit": "200"})
        if not isinstance(trades, list):
            continue
        for t in trades:
            w = str(t.get("proxyWallet") or "").lower().strip()
            if len(w) < 10:
                continue
            notional = _safe_float(t.get("size")) * _safe_float(t.get("price"))
            if notional < _MIN_TRADE_NOTIONAL:
                continue
            wallet_notional[w] = wallet_notional.get(w, 0.0) + notional
            wallet_trade_count[w] = wallet_trade_count.get(w, 0) + 1
            wallet_market_count.setdefault(w, set()).add(cid)

    if not wallet_notional:
        logger.warning("No wallets found via crypto market trades")
        return []

    # Filter likely HFT / latency-arb bots before ranking.
    # Heuristic 1: avg notional-per-trade < $25 AND trade count > 30 → HFT scalper.
    # Heuristic 2: traded across > 60% of scanned markets with > 20 trades → cross-market arb.
    total_markets = max(len(condition_ids), 1)
    filtered_notional: dict[str, float] = {}
    wallet_arb_scores: dict[str, float] = {}
    for w, total_n in wallet_notional.items():
        tc = wallet_trade_count.get(w, 1)
        mc = len(wallet_market_count.get(w, set()))
        avg_n = total_n / tc if tc else total_n
        spread = mc / total_markets
        # Compute a continuous arb score in [0, 1]
        hft_signal = min(max(30.0 - avg_n, 0.0) / 30.0, 1.0) if tc > 10 else 0.0
        arb_signal = spread if tc > 20 else 0.0
        arb_score = round(max(hft_signal, arb_signal), 3)
        wallet_arb_scores[w] = arb_score
        is_hft = (avg_n < 25.0 and tc > 30)
        is_arb = (spread > 0.60 and tc > 20)
        if not (is_hft or is_arb):
            filtered_notional[w] = total_n

    hft_excluded = len(wallet_notional) - len(filtered_notional)
    if hft_excluded:
        logger.info("Excluded %d likely HFT/arb wallets from discovery", hft_excluded)

    # Safety fallback: if everything was filtered, keep top 5 by raw notional
    if not filtered_notional:
        logger.warning("All discovery wallets classified as HFT/arb; retaining top 5 by notional")
        filtered_notional = dict(sorted(wallet_notional.items(), key=lambda kv: kv[1], reverse=True)[:5])

    top_wallets = sorted(filtered_notional.items(), key=lambda kv: kv[1], reverse=True)[:max_wallets]
    profiles = [
        {
            "wallet": wallet,
            "user_name": wallet[:10],
            "leaderboard_rank": 0,
            "leaderboard_pnl": 0.0,
            "leaderboard_volume": notional,
            "crypto_win_rate": 0.55,
            "crypto_win_rate_bayes": 0.55,
            "crypto_posterior_win_rate": 0.55,
            "wallet_rank_score": 0.55,
            "crypto_total_pnl": 0.0,
            "crypto_decisions": 0,
            "discovery_trade_count": wallet_trade_count.get(wallet, 0),
            "discovery_market_count": len(wallet_market_count.get(wallet, set())),
            "latency_arb_score": wallet_arb_scores.get(wallet, 0.0),
            "latency_arb_flag": wallet_arb_scores.get(wallet, 0.0) >= 0.5,
            "wallet_archetype": "crypto_trader",
            "archetype_copyable": True,
            "copyable_archetype": True,
            "copyability_gate_reason": "",
        }
        for wallet, notional in top_wallets
    ]
    logger.info(
        "Discovered %d crypto-active wallets via trades (top notional: $%.0f, %d HFT excluded)",
        len(profiles),
        top_wallets[0][1] if top_wallets else 0,
        hft_excluded,
    )
    return profiles


def scan_large_trades(threshold_usdc: float = 5000.0) -> list[dict[str, Any]]:
    """Scan the Polymarket CLOB API for recent large trades above *threshold_usdc*.

    This is a **read-only, analytics-only** function.  No keys, no signing,
    no auto-trading.  Controlled by the ``WHALE_SCANNER_ENABLED`` env-var
    (default ON).

    Alert tiers
    -----------
    WHALE   : usdc_value > 50 000
    SHARK   : usdc_value > 10 000
    DOLPHIN : usdc_value > threshold_usdc (default 5 000)

    A wallet is flagged ``is_fresh_wallet=True`` when it appears fewer than
    10 times across *all* trades returned in the same response.

    Returns
    -------
    list[dict]
        Each entry has the schema documented in the task brief.
        Writes results to ``prediction_market_agents/data/whale_alerts.json``.
        On API failure (403 / 429 / network error) returns an empty list and
        writes ``{"status": "api_unavailable", ...}`` to the JSON file instead
        of raising.
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    def _write_unavailable(reason: str) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {
            "status": "api_unavailable",
            "reason": reason,
            "generated_at": now_iso,
            "threshold_usdc": threshold_usdc,
            "alerts": [],
        }
        _save_json(WHALE_ALERTS_FILE, payload)
        logger.warning("scan_large_trades: api_unavailable — %s", reason)
        return []

    if not _WHALE_SCANNER_ENABLED:
        logger.info("scan_large_trades: disabled via WHALE_SCANNER_ENABLED=0")
        _save_json(WHALE_ALERTS_FILE, {
            "status": "disabled",
            "generated_at": now_iso,
            "alerts": [],
        })
        return []

    # ------------------------------------------------------------------
    # Fetch from CLOB trades endpoint.
    # We request without auth; the endpoint is public for recent trades.
    # The CLOB API does not support a server-side size_gt filter reliably,
    # so we fetch the last page and filter client-side.
    # ------------------------------------------------------------------
    raw_trades: list[dict[str, Any]] | None = None
    endpoints = [
        CLOB_TRADES_URL,
        "https://data-api.polymarket.com/trades",  # fallback mirror
    ]
    last_error = "no endpoints tried"
    for endpoint in endpoints:
        try:
            params = {
                "limit": "500",
                "taker_order_id": "",
                "maker_order_id": "",
                "market": "",
                "maker": "",
                "taker": "",
            }
            url_with_params = f"{endpoint}?{urllib.parse.urlencode({k: v for k, v in params.items() if v != ''})}&limit=500"
            req = urllib.request.Request(url_with_params, headers=_REQUEST_HEADERS)
            with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT, context=_SSL_CTX) as resp:
                status_code = resp.status
                if status_code in (403, 429):
                    last_error = f"HTTP {status_code} from {endpoint}"
                    logger.warning("scan_large_trades: %s", last_error)
                    continue
                body = resp.read().decode("utf-8")
                parsed = json.loads(body)
                # CLOB wraps in {"data": [...]} or returns a bare list
                if isinstance(parsed, dict) and isinstance(parsed.get("data"), list):
                    raw_trades = parsed["data"]
                elif isinstance(parsed, list):
                    raw_trades = parsed
                else:
                    last_error = f"unexpected response shape from {endpoint}"
                    logger.warning("scan_large_trades: %s", last_error)
                    continue
                break  # success
        except urllib.error.HTTPError as exc:
            last_error = f"HTTP {exc.code} from {endpoint}"
            logger.warning("scan_large_trades: %s", last_error)
            if exc.code in (403, 429):
                continue  # try fallback
        except urllib.error.URLError as exc:
            last_error = f"URLError from {endpoint}: {exc.reason}"
            logger.warning("scan_large_trades: %s", last_error)
        except Exception as exc:
            last_error = f"fetch error from {endpoint}: {exc}"
            logger.warning("scan_large_trades: %s", last_error)

    if raw_trades is None:
        return _write_unavailable(last_error)

    # ------------------------------------------------------------------
    # Count wallet appearances across all returned trades (freshness heuristic)
    # ------------------------------------------------------------------
    wallet_counts: dict[str, int] = {}
    for t in raw_trades:
        for field in ("taker", "maker", "transactorAddress", "proxyWallet"):
            w = str(t.get(field) or "").lower().strip()
            if len(w) >= 10:
                wallet_counts[w] = wallet_counts.get(w, 0) + 1

    # ------------------------------------------------------------------
    # Filter & classify large trades
    # ------------------------------------------------------------------
    alerts: list[dict[str, Any]] = []
    for t in raw_trades:
        try:
            # Normalise field names — CLOB uses camelCase; Data API uses snake_case
            size = _safe_float(
                t.get("size") or t.get("outcomeTokensTraded") or t.get("amount")
            )
            price = _safe_float(
                t.get("price") or t.get("outcomePrice")
            )
            usdc_value = size * price
            if usdc_value < threshold_usdc:
                continue  # below threshold

            # Determine alert tier
            if usdc_value > 50_000:
                alert_level = "WHALE"
            elif usdc_value > 10_000:
                alert_level = "SHARK"
            else:
                alert_level = "DOLPHIN"

            # Wallet: prefer taker (aggressor), fall back to maker / proxy
            wallet = str(
                t.get("taker") or t.get("maker")
                or t.get("transactorAddress") or t.get("proxyWallet") or ""
            ).lower().strip()

            # Market ID
            market_id = str(
                t.get("market") or t.get("marketId")
                or t.get("condition_id") or t.get("conditionId") or ""
            )

            # Side: CLOB uses "BUY"/"SELL"; Data API uses "YES"/"NO" sometimes
            side_raw = str(t.get("side") or t.get("type") or "").upper()
            if side_raw in ("BUY", "SELL"):
                side = side_raw
            elif side_raw in ("YES", "LONG"):
                side = "BUY"
            elif side_raw in ("NO", "SHORT"):
                side = "SELL"
            else:
                side = "BUY"  # default — CLOB taker is usually buyer

            # Timestamp
            ts_raw = (
                t.get("timestamp") or t.get("createdAt")
                or t.get("matchTime") or t.get("created_at") or ""
            )
            if ts_raw:
                try:
                    ts_val = float(ts_raw)
                    # Unix seconds or millis
                    if ts_val > 1e12:
                        ts_val /= 1000.0
                    timestamp = datetime.fromtimestamp(ts_val, tz=timezone.utc).isoformat()
                except (ValueError, TypeError, OSError):
                    timestamp = str(ts_raw)
            else:
                timestamp = now_iso

            is_fresh_wallet = wallet_counts.get(wallet, 0) < 10

            alerts.append({
                "wallet": wallet,
                "market_id": market_id,
                "side": side,
                "size": round(size, 6),
                "price": round(price, 6),
                "usdc_value": round(usdc_value, 2),
                "timestamp": timestamp,
                "alert_level": alert_level,
                "is_fresh_wallet": is_fresh_wallet,
            })

        except Exception as exc:
            logger.debug("scan_large_trades: skipping trade record — %s", exc)
            continue

    # Highest value first
    alerts.sort(key=lambda a: a["usdc_value"], reverse=True)

    payload = {
        "status": "ok",
        "generated_at": now_iso,
        "threshold_usdc": threshold_usdc,
        "total_raw_trades": len(raw_trades),
        "total_alerts": len(alerts),
        "alerts": alerts,
    }
    _save_json(WHALE_ALERTS_FILE, payload)
    logger.info(
        "scan_large_trades: %d large trades (>$%.0f) found from %d raw trades; written to %s",
        len(alerts), threshold_usdc, len(raw_trades), WHALE_ALERTS_FILE,
    )
    return alerts


def scan_whales(top_n: int = 20) -> dict[str, Any]:
    """
    Run the shared Polymarket wallet-intel scan and emit agent-compatible
    whale signals.
    """
    try:
        from copy_trader_intel.polymarket_scraper import scan_polymarket_traders, save_polymarket_results
    except Exception as exc:
        logger.error("Failed to import shared Polymarket scanner: %s", exc)
        return {"traders": [], "signals": [], "error": str(exc)}

    logger.info("=" * 60)
    logger.info("  Polymarket Whale Tracker")
    logger.info("=" * 60)

    profiles, picks = scan_polymarket_traders(max_traders=50)
    save_polymarket_results(profiles, picks)

    selected_profiles = [profile for profile in profiles if profile.get("copyable_archetype", True)][:top_n]
    existing_wallets = {profile.get("wallet", "").lower() for profile in selected_profiles}
    
    if len(selected_profiles) < top_n:
        logger.info(
            "Shared scanner returned %d qualified profiles. Backfilling up to %d with trade-based crypto discovery...",
            len(selected_profiles),
            top_n,
        )
        discovered_profiles = _discover_crypto_traders(max_wallets=top_n * 2)
        for profile in discovered_profiles:
            wallet = profile.get("wallet", "").lower()
            if not wallet or wallet in existing_wallets:
                continue
            selected_profiles.append(profile)
            existing_wallets.add(wallet)
            if len(selected_profiles) >= top_n:
                break

    allowed_wallets = {profile["wallet"] for profile in selected_profiles}
    wallet_copy_signals = [_to_agent_signal(pick) for pick in picks if pick.get("trader_address") in allowed_wallets]

    logger.info("Fetching direct positions for wallets not already represented in vetted picks...")
    wallets_with_shared_signals = {signal.get("whale_data", {}).get("wallet") for signal in wallet_copy_signals}
    direct_position_signals: list[dict[str, Any]] = []
    for profile in selected_profiles:
        wallet = profile.get("wallet", "")
        if not wallet or wallet in wallets_with_shared_signals:
            continue
        try:
            raw_positions = fetch_wallet_positions(wallet)
            if raw_positions:
                converted = positions_to_signals(raw_positions, profile)
                direct_position_signals.extend(converted)
        except Exception as exc:
            logger.warning("Failed to fetch positions for wallet %s: %s", wallet[:10], exc)
            continue

    signals = wallet_copy_signals + direct_position_signals
    pre_conflict_count = len(signals)
    signals = _resolve_signal_direction_conflicts(signals)
    logger.info(
        "Shared scanner produced %d vetted signals; direct fetch added %d inferred signals; conflict-resolved total %d -> %d",
        len(wallet_copy_signals),
        len(direct_position_signals),
        pre_conflict_count,
        len(signals),
    )
    
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "polymarket_whale_tracker",
        "total_traders_scanned": len(selected_profiles),
        "total_signals": len(signals),
        "wallet_copy_signals": len(wallet_copy_signals),
        "direct_position_signals": len(direct_position_signals),
        "traders": [
            {
                "wallet": profile["wallet"],
                "username": profile.get("user_name", ""),
                "rank": profile.get("leaderboard_rank"),
                "pnl": profile.get("leaderboard_pnl"),
                "leaderboard_source": profile.get("leaderboard_source"),
                "crypto_profit_rank": profile.get("crypto_profit_rank"),
                "crypto_volume_rank": profile.get("crypto_volume_rank"),
                "crypto_decisions": profile.get("crypto_decisions"),
                "crypto_win_rate": profile.get("crypto_win_rate"),
                "crypto_win_rate_bayes": profile.get("crypto_win_rate_bayes"),
                "crypto_posterior_win_rate": (
                    profile.get("crypto_win_rate_bayes")
                    or profile.get("crypto_posterior_win_rate")
                ),
                "crypto_total_pnl": profile.get("crypto_total_pnl"),
                "crypto_profile_score": profile.get("crypto_profile_score"),
                "wallet_rank_score": (
                    profile.get("crypto_profile_score")
                    or profile.get("wallet_rank_score")
                ),
                "crypto_sample_tier": profile.get("crypto_sample_tier"),
                "crypto_recent_score_30d": profile.get("crypto_recent_score_30d"),
                "crypto_recent_score_90d": profile.get("crypto_recent_score_90d"),
                "wallet_archetype": profile.get("wallet_archetype"),
                "archetype_copyable": profile.get("archetype_copyable", True),
                "copyable_archetype": profile.get("copyable_archetype", True),
                "copyability_gate_reason": profile.get("copyability_gate_reason"),
                "latency_arb_flag": profile.get("latency_arb_flag", False),
                "latency_arb_score": profile.get("latency_arb_score"),
                "entry_quality_score": profile.get("entry_quality_score"),
                "crypto_top_symbol": profile.get("crypto_top_symbol"),
                "crypto_top_symbol_pnl_share": profile.get("crypto_top_symbol_pnl_share"),
            }
            for profile in selected_profiles
        ],
        "signals": signals,
    }

    _save_json(OUTPUT_FILE, summary)
    _save_json(WHALE_SIGNALS_FILE, signals)
    logger.info("Saved %d whale signals to %s", len(signals), WHALE_SIGNALS_FILE)
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    result = scan_whales()
    print(f"\n{'='*60}")
    print(f"  Polymarket Whale Tracker Complete")
    print(f"{'='*60}")
    print(f"  Traders scanned: {result.get('total_traders_scanned', 0)}")
    print(f"  Signals generated: {result.get('total_signals', 0)}")
    print(f"{'='*60}")
    for sig in result.get("signals", [])[:10]:
        whale_name = sig.get("whale_data", {}).get("username", "Unknown")
        print(
            f"  {sig.get('direction','?'):5s} {sig.get('symbol','?'):12s} "
            f"conf={sig.get('confidence',0):.2f} - {whale_name}"
        )
    print(f"\n{'='*60}")
