#!/usr/bin/env python3
"""
Polymarket Wallet Intelligence Scanner
======================================

Uses Polymarket's public data API to discover leaderboard wallets, score them
on crypto-only resolved positions, and convert their current crypto positions
into copy-trader picks.

Primary endpoints:
  - GET https://data-api.polymarket.com/v1/leaderboard
  - GET https://data-api.polymarket.com/closed-positions
  - GET https://data-api.polymarket.com/positions

The goal is not to mirror every profitable Polymarket bettor. It is to find
wallets with repeatable crypto directional edge and copy only their current
crypto positioning.
"""

from __future__ import annotations

import json
import math
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# Fix Windows UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

LEADERBOARD_URL = "https://data-api.polymarket.com/v1/leaderboard"
CRYPTO_LEADERBOARD_PAGE_URL = "https://polymarket.com/leaderboard/crypto/all/profit"
POSITIONS_URL = "https://data-api.polymarket.com/positions"
CLOSED_POSITIONS_URL = "https://data-api.polymarket.com/closed-positions"
BINANCE_PRICE_URLS = [
    "https://data-api.binance.vision/api/v3/ticker/price",
    "https://api.binance.us/api/v3/ticker/price",
    "https://api1.binance.com/api/v3/ticker/price",
    "https://api2.binance.com/api/v3/ticker/price",
    "https://api3.binance.com/api/v3/ticker/price",
    "https://api.binance.com/api/v3/ticker/price",
]

REQUEST_TIMEOUT = 20
REQUEST_HEADERS = {
    "User-Agent": "CopyTraderIntel-Polymarket/1.0",
    "Accept": "application/json",
}

LEADERBOARD_LIMIT = 50
MAX_QUALIFIED_TRADERS = 20
CLOSED_POSITIONS_LIMIT = 200
OPEN_POSITIONS_LIMIT = 200

MIN_SYMBOL_DECISIONS = 2   # Lowered from 5: PM whales rarely have 5+ crypto-specific decisions
MIN_SYMBOL_WIN_RATE = 0.50  # Lowered from 0.60: 50% WR with positive PnL is still an edge
MIN_SYMBOL_TOTAL_PNL = 50.0  # Lowered from 500: $50+ total PnL per symbol is meaningful for PM
MIN_PROFILE_DECISIONS = 8
ESTABLISHED_PROFILE_DECISIONS = 20
PROFILE_SCORE_SATURATION_DECISIONS = 40
PROFILE_BAYES_PRIOR_WIN_RATE = 0.62
PROFILE_BAYES_PRIOR_STRENGTH = 20.0
SYMBOL_BAYES_PRIOR_WIN_RATE = 0.60
SYMBOL_BAYES_PRIOR_STRENGTH = 8.0
RECENT_FORM_MIN_DECISIONS = 5
CONCENTRATION_WARN_SHARE = 0.75
MIN_DIRECTIONAL_DOMINANCE = 0.65
MIN_SIGNAL_NOTIONAL = 100.0
MAX_SIGNAL_HOURS = 24 * 14
MIN_COPYABLE_SIGNAL_HOURS = 4.0
MIN_COPYABLE_DIRECTIONAL_NOTIONAL = 2_500.0
MIN_COPYABLE_LEAD_NOTIONAL = 500.0
MIN_ENTRY_QUALITY_SCORE = 0.45

_SPOT_CACHE: dict[str, float | None] = {}

ASSET_RULES: tuple[tuple[str, tuple[re.Pattern[str], ...]], ...] = (
    ("BTCUSDT", (re.compile(r"\bbitcoin\b", re.I), re.compile(r"\bbtc\b", re.I))),
    ("ETHUSDT", (re.compile(r"\bethereum\b", re.I), re.compile(r"\beth\b", re.I))),
    ("SOLUSDT", (re.compile(r"\bsolana\b", re.I),)),
    ("XRPUSDT", (re.compile(r"\bripple\b", re.I), re.compile(r"\bxrp\b", re.I))),
    ("DOGEUSDT", (re.compile(r"\bdogecoin\b", re.I), re.compile(r"\bdoge\b", re.I))),
    ("ADAUSDT", (re.compile(r"\bcardano\b", re.I), re.compile(r"\bada\b", re.I))),
    ("BNBUSDT", (re.compile(r"\bbinance coin\b", re.I), re.compile(r"\bbnb\b", re.I))),
    # Only match the ticker; the word "Avalanche" collides with NHL markets.
    ("AVAXUSDT", (re.compile(r"\bavax\b", re.I),)),
)

_NEWS_EVENT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\betf\b", re.I),
    re.compile(r"\bapprove\b", re.I),
    re.compile(r"\bpurchase\b", re.I),
    re.compile(r"\bcompany\b", re.I),
    re.compile(r"\blaunch\b", re.I),
    re.compile(r"\binsider\b", re.I),
    re.compile(r"\bexpose\b", re.I),
    re.compile(r"\bmention\b", re.I),
    re.compile(r"\bsay\b", re.I),
    re.compile(r"\btreasury\b", re.I),
    re.compile(r"\breserve\b", re.I),
)
_MILESTONE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bwhat price\b", re.I),
    re.compile(r"\breach\b", re.I),
    re.compile(r"\bhit\b", re.I),
    re.compile(r"\babove\b", re.I),
    re.compile(r"\bbelow\b", re.I),
    re.compile(r"\bdip\b", re.I),
    re.compile(r"\bfall\b", re.I),
    re.compile(r"\bunder\b", re.I),
    re.compile(r"\bover\b", re.I),
    re.compile(r"\bat least\b", re.I),
    re.compile(r"\bsurpass\b", re.I),
    re.compile(r"\bexceed\b", re.I),
)
_LATENCY_ARB_TITLE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bup or down\b", re.I),
    re.compile(r"\b(?:5|10|15|30)\s*min", re.I),
    re.compile(r"\b(?:1|one)\s*hour\b", re.I),
    re.compile(r"\bhourly\b", re.I),
)

LATENCY_ARB_MIN_MARKETS = 10
LATENCY_ARB_SHORT_EXPIRY_HOURS = 1.0
LATENCY_ARB_ULTRASHORT_HOURS = 0.35
LATENCY_ARB_SCORE_THRESHOLD = 0.55


def _fetch_json(url: str, params: dict[str, Any] | None = None) -> Any:
    """Fetch JSON with stdlib only."""
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=REQUEST_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        print(f"  [WARN] HTTP {exc.code} for {url}")
    except urllib.error.URLError as exc:
        print(f"  [WARN] URL error for {url}: {exc.reason}")
    except Exception as exc:
        print(f"  [WARN] Fetch failed for {url}: {exc}")
    return None


def _fetch_text(url: str, params: dict[str, Any] | None = None) -> str | None:
    """Fetch raw text with stdlib only."""
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=REQUEST_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        print(f"  [WARN] HTTP {exc.code} for {url}")
    except urllib.error.URLError as exc:
        print(f"  [WARN] URL error for {url}: {exc.reason}")
    except Exception as exc:
        print(f"  [WARN] Fetch failed for {url}: {exc}")
    return None


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _bayes_win_rate(
    wins: int,
    decisions: int,
    *,
    prior_mean: float,
    prior_strength: float,
) -> float:
    if decisions <= 0:
        return prior_mean
    alpha = prior_mean * prior_strength
    beta = (1.0 - prior_mean) * prior_strength
    return (wins + alpha) / (decisions + alpha + beta)


def _sample_weight(decisions: int, saturation: int) -> float:
    if saturation <= 0:
        return 1.0
    return min(max(decisions, 0) / float(saturation), 1.0)


def _parse_dt(raw: Any) -> datetime | None:
    if not raw:
        return None
    text = str(raw).strip().replace("Z", "+00:00")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        # Date-only fields from Polymarket should stay valid for the full day.
        text = f"{text}T23:59:59+00:00"
    for fmt in (None, "%Y-%m-%d"):
        try:
            if fmt is None:
                dt = datetime.fromisoformat(text)
            else:
                dt = datetime.strptime(text, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            continue
    return None


def _market_row_dt(row: dict[str, Any]) -> datetime | None:
    return _parse_dt(row.get("timestamp")) or _parse_dt(row.get("endDate"))


def _profile_sample_tier(decisions: int) -> str:
    if decisions >= ESTABLISHED_PROFILE_DECISIONS:
        return "established"
    if decisions >= MIN_PROFILE_DECISIONS:
        return "emerging"
    return "insufficient"


def _profile_rank_score(*, wins: int, decisions: int) -> float:
    bayes_wr = _bayes_win_rate(
        wins,
        decisions,
        prior_mean=PROFILE_BAYES_PRIOR_WIN_RATE,
        prior_strength=PROFILE_BAYES_PRIOR_STRENGTH,
    )
    return bayes_wr * _sample_weight(decisions, PROFILE_SCORE_SATURATION_DECISIONS)


def _profile_rank_sort_key(profile: dict[str, Any]) -> tuple[float, ...]:
    bayes_wr = _safe_float(profile.get("crypto_win_rate_bayes"), PROFILE_BAYES_PRIOR_WIN_RATE)
    recent_30d = _safe_float(profile.get("crypto_recent_score_30d"))
    recent_90d = _safe_float(profile.get("crypto_recent_score_90d"))
    has_recent_30d = 1.0 if int(profile.get("crypto_recent_decisions_30d") or 0) >= RECENT_FORM_MIN_DECISIONS else 0.0
    has_recent_90d = 1.0 if int(profile.get("crypto_recent_decisions_90d") or 0) >= MIN_PROFILE_DECISIONS else 0.0
    elite_quality = 1.0 if bayes_wr >= 0.84 else 0.0
    good_quality = 1.0 if bayes_wr >= 0.80 else 0.0
    return (
        1.0 if profile.get("established_crypto_history") else 0.0,
        1.0 if profile.get("copyable_archetype", True) else 0.0,
        has_recent_30d,
        recent_30d,
        has_recent_90d,
        recent_90d,
        -_safe_float(profile.get("latency_arb_score")),
        elite_quality,
        good_quality,
        _safe_float(profile.get("crypto_total_pnl")),
        float(int(profile.get("crypto_decisions") or 0)),
        bayes_wr,
        _safe_float(profile.get("crypto_profile_score")),
        -float(int(profile.get("crypto_profit_rank") or 10**9)),
    )


def _wallet_alias(user_name: str, wallet: str) -> str:
    base = (user_name or wallet).lower()
    base = re.sub(r"[^a-z0-9]+", "_", base).strip("_")
    if not base:
        base = wallet.lower().replace("0x", "pm_")
    if base.startswith("0x"):
        base = f"pm_{base[2:10]}"
    return base[:32]


def _row_text(row: dict[str, Any]) -> str:
    return " ".join(
        str(row.get(key, "") or "")
        for key in ("title", "slug", "eventSlug", "icon")
    )


def _extract_symbol(row: dict[str, Any]) -> str | None:
    text = _row_text(row)
    for symbol, patterns in ASSET_RULES:
        if any(pattern.search(text) for pattern in patterns):
            return symbol
    return None


def _infer_direction(title: str, outcome: str) -> str | None:
    """Infer spot direction from the market title plus the held outcome."""
    title_l = (title or "").lower()
    outcome_l = (outcome or "").lower().strip()

    if not title_l or not outcome_l:
        return None

    if "up or down" in title_l:
        if outcome_l == "up":
            return "LONG"
        if outcome_l == "down":
            return "SHORT"
        return None

    if "between" in title_l:
        return None

    if re.search(r"\b(reach|hit|above|over|at least|exceed|surpass)\b", title_l):
        if outcome_l == "yes":
            return "LONG"
        if outcome_l == "no":
            return "SHORT"
        return None

    if re.search(r"\b(dip|below|under|drop|fall)\b", title_l):
        if outcome_l == "yes":
            return "SHORT"
        if outcome_l == "no":
            return "LONG"
        return None

    return None


def _historical_exposure(row: dict[str, Any]) -> float:
    initial_value = _safe_float(row.get("initialValue"))
    if initial_value > 0:
        return abs(initial_value)
    total_bought = _safe_float(row.get("totalBought"))
    avg_price = _safe_float(row.get("avgPrice"))
    if total_bought > 0 and avg_price > 0:
        return abs(total_bought * avg_price)
    return abs(_safe_float(row.get("size")) * _safe_float(row.get("curPrice") or row.get("avgPrice")))


def _open_exposure(row: dict[str, Any]) -> float:
    current_value = _safe_float(row.get("currentValue"))
    if current_value > 0:
        return abs(current_value)
    size = _safe_float(row.get("size"))
    cur_price = _safe_float(row.get("curPrice") or row.get("avgPrice"))
    return abs(size * cur_price)


def _group_directional_markets(
    rows: list[dict[str, Any]],
    *,
    use_open_notional: bool,
) -> list[dict[str, Any]]:
    """Collapse per-outcome rows into directional per-market summaries."""
    grouped: dict[str, dict[str, Any]] = {}
    now = datetime.now(timezone.utc)

    for row in rows:
        symbol = _extract_symbol(row)
        direction = _infer_direction(row.get("title", ""), row.get("outcome", ""))
        if not symbol or not direction:
            continue

        end_dt = _parse_dt(row.get("endDate"))
        if use_open_notional:
            if end_dt is None:
                continue
            hours_to_expiry = (end_dt - now).total_seconds() / 3600
            if hours_to_expiry <= 0 or hours_to_expiry > MAX_SIGNAL_HOURS:
                continue
            exposure = _open_exposure(row)
        else:
            exposure = _historical_exposure(row)

        if exposure <= 0:
            continue

        key = str(row.get("conditionId") or row.get("slug") or row.get("eventSlug") or "")
        if not key:
            continue

        row_dt = _market_row_dt(row)
        avg_price = max(min(_safe_float(row.get("avgPrice") or row.get("curPrice")), 1.0), 0.0)
        group = grouped.setdefault(
            key,
            {
                "condition_id": key,
                "symbol": symbol,
                "title": row.get("title", ""),
                "slug": row.get("slug", ""),
                "event_slug": row.get("eventSlug", ""),
                "end_date": row.get("endDate", ""),
                "notional_by_direction": defaultdict(float),
                "pnl_by_direction": defaultdict(float),
                "price_x_notional_by_direction": defaultdict(float),
                "latest_dt": row_dt,
                "row_count": 0,
            },
        )
        group["notional_by_direction"][direction] += exposure
        group["pnl_by_direction"][direction] += _safe_float(row.get("realizedPnl"))
        group["price_x_notional_by_direction"][direction] += exposure * avg_price
        if row_dt and (group["latest_dt"] is None or row_dt > group["latest_dt"]):
            group["latest_dt"] = row_dt
        group["row_count"] += 1

    results: list[dict[str, Any]] = []
    for group in grouped.values():
        long_notional = group["notional_by_direction"].get("LONG", 0.0)
        short_notional = group["notional_by_direction"].get("SHORT", 0.0)
        total_notional = long_notional + short_notional
        if total_notional <= 0:
            continue

        dominant_direction = "LONG" if long_notional >= short_notional else "SHORT"
        dominant_notional = max(long_notional, short_notional)
        dominance = dominant_notional / total_notional
        if dominance < MIN_DIRECTIONAL_DOMINANCE:
            continue

        dominant_avg_price = 0.0
        if dominant_notional > 0:
            dominant_avg_price = (
                group["price_x_notional_by_direction"].get(dominant_direction, 0.0) / dominant_notional
            )

        results.append(
            {
                "condition_id": group["condition_id"],
                "symbol": group["symbol"],
                "title": group["title"],
                "slug": group["slug"],
                "event_slug": group["event_slug"],
                "end_date": group["end_date"],
                "market_ts": group["latest_dt"].isoformat() if group["latest_dt"] else "",
                "direction": dominant_direction,
                "dominance": dominance,
                "dominant_notional": dominant_notional,
                "dominant_avg_price": round(dominant_avg_price, 4),
                "net_pnl": group["pnl_by_direction"].get("LONG", 0.0) + group["pnl_by_direction"].get("SHORT", 0.0),
                "row_count": group["row_count"],
            }
        )

    return results


def fetch_leaderboard(limit: int = LEADERBOARD_LIMIT) -> list[dict[str, Any]]:
    data = _fetch_json(LEADERBOARD_URL, {"limit": limit})
    if isinstance(data, list):
        return data
    return []


def _normalize_leaderboard_row(
    row: dict[str, Any],
    *,
    source: str,
    sort_key: str | None = None,
) -> dict[str, Any] | None:
    wallet = str(row.get("proxyWallet") or "").lower().strip()
    if not wallet:
        return None

    normalized = {
        "rank": int(_safe_float(row.get("rank"), 0)),
        "proxyWallet": wallet,
        "userName": str(row.get("userName") or row.get("name") or row.get("pseudonym") or wallet),
        "pnl": _safe_float(row.get("pnl") or row.get("amount")),
        "vol": _safe_float(row.get("vol") or row.get("volume") or row.get("amount")),
        "verifiedBadge": bool(row.get("verifiedBadge")),
        "leaderboardSource": source,
    }
    if sort_key == "profit":
        normalized["cryptoProfitRank"] = normalized["rank"]
    elif sort_key == "volume":
        normalized["cryptoVolumeRank"] = normalized["rank"]
    return normalized


def fetch_crypto_leaderboard(limit: int = LEADERBOARD_LIMIT) -> list[dict[str, Any]]:
    html = _fetch_text(CRYPTO_LEADERBOARD_PAGE_URL)
    if not html:
        return []

    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json"[^>]*>(.*?)</script>',
        html,
        re.S,
    )
    if not match:
        print("  [WARN] Crypto leaderboard page missing __NEXT_DATA__ payload")
        return []

    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        print(f"  [WARN] Failed parsing crypto leaderboard payload: {exc}")
        return []

    queries = (
        payload.get("props", {})
        .get("pageProps", {})
        .get("dehydratedState", {})
        .get("queries", [])
    )
    by_wallet: dict[str, dict[str, Any]] = {}
    for query in queries:
        query_key = query.get("queryKey")
        if (
            not isinstance(query_key, list)
            or len(query_key) < 5
            or query_key[0] != "/leaderboard"
            or query_key[2] != "all"
            or query_key[4] != "crypto"
        ):
            continue

        sort_key = str(query_key[1] or "")
        if sort_key not in {"profit", "volume"}:
            continue

        rows = query.get("state", {}).get("data", [])
        if not isinstance(rows, list):
            continue

        for row in rows:
            normalized = _normalize_leaderboard_row(row, source="crypto_leaderboard", sort_key=sort_key)
            if not normalized:
                continue
            wallet = normalized["proxyWallet"]
            existing = by_wallet.get(wallet)
            if existing is None:
                by_wallet[wallet] = normalized
                continue
            if normalized.get("userName") and existing.get("userName", "").startswith("0x"):
                existing["userName"] = normalized["userName"]
            existing["pnl"] = max(existing.get("pnl", 0.0), normalized.get("pnl", 0.0))
            existing["vol"] = max(existing.get("vol", 0.0), normalized.get("vol", 0.0))
            if normalized.get("cryptoProfitRank"):
                existing["cryptoProfitRank"] = normalized["cryptoProfitRank"]
            if normalized.get("cryptoVolumeRank"):
                existing["cryptoVolumeRank"] = normalized["cryptoVolumeRank"]
            existing["rank"] = min(
                int(existing.get("cryptoProfitRank") or 10**9),
                int(existing.get("cryptoVolumeRank") or 10**9),
            )

    rows = list(by_wallet.values())
    rows.sort(
        key=lambda row: (
            int(row.get("cryptoProfitRank") or 10**9),
            int(row.get("cryptoVolumeRank") or 10**9),
            -_safe_float(row.get("pnl")),
            -_safe_float(row.get("vol")),
        )
    )
    return rows[:limit]


def fetch_candidate_leaderboard(limit: int = LEADERBOARD_LIMIT) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen_wallets: set[str] = set()

    for row in fetch_crypto_leaderboard(limit=limit):
        wallet = str(row.get("proxyWallet") or "").lower().strip()
        if not wallet or wallet in seen_wallets:
            continue
        seen_wallets.add(wallet)
        candidates.append(row)

    if len(candidates) >= limit:
        return candidates[:limit]

    for row in fetch_leaderboard(limit=max(limit, LEADERBOARD_LIMIT)):
        normalized = _normalize_leaderboard_row(row, source="generic_leaderboard")
        if not normalized:
            continue
        wallet = normalized["proxyWallet"]
        if wallet in seen_wallets:
            continue
        seen_wallets.add(wallet)
        candidates.append(normalized)
        if len(candidates) >= limit:
            break

    return candidates[:limit]


def fetch_closed_positions(wallet: str, limit: int = CLOSED_POSITIONS_LIMIT) -> list[dict[str, Any]]:
    data = _fetch_json(CLOSED_POSITIONS_URL, {"user": wallet, "limit": limit})
    if isinstance(data, list):
        return data
    return []


def fetch_open_positions(wallet: str, limit: int = OPEN_POSITIONS_LIMIT) -> list[dict[str, Any]]:
    data = _fetch_json(POSITIONS_URL, {"user": wallet, "limit": limit})
    if isinstance(data, list):
        return data
    return []


def _compute_recent_form(directional_history: list[dict[str, Any]]) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    now = datetime.now(timezone.utc)
    for days in (30, 90):
        cutoff = now - timedelta(days=days)
        window = [
            market
            for market in directional_history
            if (market_dt := _parse_dt(market.get("market_ts"))) and market_dt >= cutoff
        ]
        decisions = len(window)
        wins = sum(1 for market in window if _safe_float(market.get("net_pnl")) > 0)
        total_pnl = round(sum(_safe_float(market.get("net_pnl")) for market in window), 2)
        raw_wr = wins / decisions if decisions else 0.0
        bayes_wr = _bayes_win_rate(
            wins,
            decisions,
            prior_mean=PROFILE_BAYES_PRIOR_WIN_RATE,
            prior_strength=PROFILE_BAYES_PRIOR_STRENGTH,
        )
        score = _profile_rank_score(wins=wins, decisions=decisions) if decisions else 0.0
        metrics[f"crypto_recent_decisions_{days}d"] = decisions
        metrics[f"crypto_recent_win_rate_{days}d"] = round(raw_wr, 4)
        metrics[f"crypto_recent_win_rate_bayes_{days}d"] = round(bayes_wr, 4)
        metrics[f"crypto_recent_pnl_{days}d"] = total_pnl
        metrics[f"crypto_recent_score_{days}d"] = round(score, 4)
    return metrics


def _compute_concentration_metrics(qualified_symbols: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if not qualified_symbols:
        return {
            "crypto_top_symbol": "",
            "crypto_top_symbol_pnl_share": 0.0,
            "crypto_top_symbol_decision_share": 0.0,
            "crypto_concentration_penalty": 0.0,
            "crypto_concentration_flag": False,
        }

    total_abs_pnl = sum(abs(_safe_float(stats.get("total_pnl"))) for stats in qualified_symbols.values())
    total_decisions = sum(int(stats.get("decisions") or 0) for stats in qualified_symbols.values())
    top_symbol, top_stats = max(
        qualified_symbols.items(),
        key=lambda item: abs(_safe_float(item[1].get("total_pnl"))),
    )
    top_abs_pnl = abs(_safe_float(top_stats.get("total_pnl")))
    pnl_share = top_abs_pnl / total_abs_pnl if total_abs_pnl > 0 else 0.0
    decision_share = int(top_stats.get("decisions") or 0) / total_decisions if total_decisions > 0 else 0.0
    penalty = min(max((pnl_share - 0.55) / 0.35, 0.0), 1.0) * 0.20
    return {
        "crypto_top_symbol": top_symbol,
        "crypto_top_symbol_pnl_share": round(pnl_share, 4),
        "crypto_top_symbol_decision_share": round(decision_share, 4),
        "crypto_concentration_penalty": round(penalty, 4),
        "crypto_concentration_flag": pnl_share >= CONCENTRATION_WARN_SHARE,
    }


def _market_hours_to_expiry_at_trade(market: dict[str, Any]) -> float | None:
    end_dt = _parse_dt(market.get("end_date"))
    market_dt = _parse_dt(market.get("market_ts"))
    if end_dt is None or market_dt is None:
        return None
    hours = (end_dt - market_dt).total_seconds() / 3600
    if hours < 0:
        return None
    return hours


def _detect_latency_arb(
    directional_history: list[dict[str, Any]],
    leaderboard_volume: float,
) -> dict[str, Any]:
    if not directional_history:
        return {
            "latency_arb_flag": False,
            "latency_arb_score": 0.0,
            "latency_arb_title_share": 0.0,
            "latency_arb_short_expiry_share": 0.0,
            "latency_arb_ultrashort_share": 0.0,
            "latency_arb_midprice_share": 0.0,
            "latency_arb_avg_hours_to_expiry": None,
            "latency_arb_tracked_market_share": 0.0,
        }

    total_markets = len(directional_history)
    title_hits = 0
    short_expiry_hits = 0
    ultrashort_hits = 0
    midprice_hits = 0
    tracked_hours: list[float] = []

    for market in directional_history:
        title = str(market.get("title") or "")
        if any(pattern.search(title) for pattern in _LATENCY_ARB_TITLE_PATTERNS):
            title_hits += 1

        dominant_avg_price = _safe_float(market.get("dominant_avg_price"))
        if 0.40 <= dominant_avg_price <= 0.60:
            midprice_hits += 1

        hours_to_expiry = _market_hours_to_expiry_at_trade(market)
        if hours_to_expiry is None:
            continue
        tracked_hours.append(hours_to_expiry)
        if hours_to_expiry <= LATENCY_ARB_SHORT_EXPIRY_HOURS:
            short_expiry_hits += 1
        if hours_to_expiry <= LATENCY_ARB_ULTRASHORT_HOURS:
            ultrashort_hits += 1

    title_share = title_hits / total_markets
    short_expiry_share = short_expiry_hits / total_markets
    ultrashort_share = ultrashort_hits / total_markets
    midprice_share = midprice_hits / total_markets
    tracked_market_share = len(tracked_hours) / total_markets
    avg_hours_to_expiry = round(sum(tracked_hours) / len(tracked_hours), 2) if tracked_hours else None
    volume_scale = min(max(leaderboard_volume, 0.0) / 100_000_000.0, 1.0)

    score = min(
        1.0,
        0.45 * title_share
        + 0.25 * short_expiry_share
        + 0.15 * ultrashort_share
        + 0.10 * midprice_share
        + 0.05 * volume_scale,
    )
    flagged = bool(
        total_markets >= LATENCY_ARB_MIN_MARKETS
        and (
            (title_share >= 0.45 and short_expiry_share >= 0.30)
            or (ultrashort_share >= 0.20 and title_share >= 0.25)
            or score >= LATENCY_ARB_SCORE_THRESHOLD
        )
    )

    return {
        "latency_arb_flag": flagged,
        "latency_arb_score": round(score, 4),
        "latency_arb_title_share": round(title_share, 4),
        "latency_arb_short_expiry_share": round(short_expiry_share, 4),
        "latency_arb_ultrashort_share": round(ultrashort_share, 4),
        "latency_arb_midprice_share": round(midprice_share, 4),
        "latency_arb_avg_hours_to_expiry": avg_hours_to_expiry,
        "latency_arb_tracked_market_share": round(tracked_market_share, 4),
    }


def _infer_market_style(market: dict[str, Any]) -> str:
    title = str(market.get("title") or "")
    title_l = title.lower()
    if "up or down" in title_l:
        return "hft_micro"
    if any(pattern.search(title) for pattern in _NEWS_EVENT_PATTERNS):
        return "news_event"
    dominant_avg_price = _safe_float(market.get("dominant_avg_price"))
    if dominant_avg_price >= 0.82 or dominant_avg_price <= 0.18:
        return "high_prob_bond"
    if any(pattern.search(title) for pattern in _MILESTONE_PATTERNS):
        return "milestone_fade"
    return "directional_generalist"


def _classify_wallet_archetype(
    directional_history: list[dict[str, Any]],
    qualified_symbols: dict[str, dict[str, Any]],
    leaderboard_volume: float,
) -> dict[str, Any]:
    styles = Counter(_infer_market_style(market) for market in directional_history)
    total_markets = max(sum(styles.values()), 1)
    symbol_count = len(qualified_symbols)
    hft_share = styles["hft_micro"] / total_markets
    milestone_share = styles["milestone_fade"] / total_markets
    bond_share = styles["high_prob_bond"] / total_markets
    news_share = styles["news_event"] / total_markets

    if hft_share >= 0.45:
        archetype = "hft_micro"
    elif milestone_share >= 0.50 and symbol_count <= 3:
        archetype = "milestone_fade"
    elif bond_share >= 0.35:
        archetype = "high_prob_bond"
    elif news_share >= 0.25:
        archetype = "news_event"
    elif total_markets >= 35 and symbol_count >= 3 and leaderboard_volume >= 50_000_000:
        archetype = "market_maker_systematic"
    else:
        archetype = "directional_generalist"

    return {
        "wallet_archetype": archetype,
        "copyable_archetype": archetype not in {"hft_micro", "market_maker_systematic"},
        "wallet_archetype_market_count": total_markets,
        "wallet_archetype_styles": dict(styles),
        "wallet_archetype_hft_share": round(hft_share, 4),
        "wallet_archetype_milestone_share": round(milestone_share, 4),
        "wallet_archetype_bond_share": round(bond_share, 4),
        "wallet_archetype_news_share": round(news_share, 4),
    }


def _apply_copyability_gate(
    archetype: dict[str, Any],
    latency_arb: dict[str, Any],
) -> dict[str, Any]:
    archetype_copyable = bool(archetype.get("copyable_archetype", True))
    gate_reason = ""
    copyable = archetype_copyable

    if not archetype_copyable:
        gate_reason = str(archetype.get("wallet_archetype") or "archetype_gate")
    elif latency_arb.get("latency_arb_flag"):
        copyable = False
        gate_reason = "latency_arb"

    return {
        "archetype_copyable": archetype_copyable,
        "copyable_archetype": copyable,
        "copyability_gate_reason": gate_reason,
    }


def _score_contract_price_quality(contract_price: float) -> float:
    if contract_price <= 0.0 or contract_price >= 1.0:
        return 0.0
    if 0.05 <= contract_price <= 0.95:
        return 1.0
    if 0.02 <= contract_price <= 0.98:
        return 0.8
    if 0.01 <= contract_price <= 0.99:
        return 0.45
    return 0.15


def _score_expiry_quality(hours_to_expiry: float) -> float:
    if hours_to_expiry < MIN_COPYABLE_SIGNAL_HOURS or hours_to_expiry > MAX_SIGNAL_HOURS:
        return 0.0
    if 12.0 <= hours_to_expiry <= 24.0 * 10.0:
        return 1.0
    if hours_to_expiry < 12.0:
        return max(
            0.0,
            min((hours_to_expiry - MIN_COPYABLE_SIGNAL_HOURS) / (12.0 - MIN_COPYABLE_SIGNAL_HOURS), 1.0),
        )
    trailing_window = max(MAX_SIGNAL_HOURS - 24.0 * 10.0, 1.0)
    decay = (hours_to_expiry - 24.0 * 10.0) / trailing_window
    return max(0.4, 1.0 - 0.6 * decay)


def _evaluate_entry_quality(
    *,
    directional_notional: float,
    lead_notional: float,
    hours_to_expiry: float,
    contract_price: float,
    market_count: int,
) -> dict[str, Any]:
    directional_size_score = min(max(directional_notional, 0.0) / 10_000.0, 1.0)
    lead_size_score = min(max(lead_notional, 0.0) / 2_500.0, 1.0)
    expiry_score = _score_expiry_quality(hours_to_expiry)
    price_score = _score_contract_price_quality(contract_price)
    breadth_score = min(max(market_count, 0) / 3.0, 1.0)
    score = min(
        1.0,
        0.35 * directional_size_score
        + 0.25 * lead_size_score
        + 0.20 * expiry_score
        + 0.15 * price_score
        + 0.05 * breadth_score,
    )

    gate_reason = ""
    entry_quality_pass = True
    if hours_to_expiry < MIN_COPYABLE_SIGNAL_HOURS or hours_to_expiry > MAX_SIGNAL_HOURS:
        entry_quality_pass = False
        gate_reason = "expiry_horizon"
    elif directional_notional < MIN_COPYABLE_DIRECTIONAL_NOTIONAL:
        entry_quality_pass = False
        gate_reason = "thin_directional_notional"
    elif lead_notional < MIN_COPYABLE_LEAD_NOTIONAL:
        entry_quality_pass = False
        gate_reason = "thin_lead_market"
    elif contract_price <= 0.0 or contract_price >= 1.0:
        entry_quality_pass = False
        gate_reason = "bad_contract_price"
    elif score < MIN_ENTRY_QUALITY_SCORE:
        entry_quality_pass = False
        gate_reason = "entry_quality_low"

    return {
        "entry_quality_pass": entry_quality_pass,
        "entry_quality_score": round(score, 4),
        "entry_quality_gate_reason": gate_reason,
        "entry_quality_directional_notional": round(directional_notional, 2),
        "entry_quality_lead_notional": round(lead_notional, 2),
        "entry_quality_contract_price": round(contract_price, 4),
        "entry_quality_hours_to_expiry": round(hours_to_expiry, 2),
        "entry_quality_market_count": int(market_count),
        "entry_quality_directional_size_score": round(directional_size_score, 4),
        "entry_quality_lead_size_score": round(lead_size_score, 4),
        "entry_quality_expiry_score": round(expiry_score, 4),
        "entry_quality_price_score": round(price_score, 4),
        "entry_quality_breadth_score": round(breadth_score, 4),
    }


def _insider_confidence_score(profile: dict) -> dict:
    """
    Compute an insider-trading confidence score from an existing wallet profile.

    Uses heuristics derived from the polymarket-insider-tracker project
    (github.com/pselamy/polymarket-insider-tracker) — adapted to work
    entirely from fields already present in the scored profile dict so that
    no additional API calls or external dependencies are required.

    Returns
    -------
    dict with keys:
        insider_confidence : "HIGH" | "MEDIUM" | "LOW" | "NONE"
        insider_score      : float in [0.0, 1.0]
        flags              : list[str]  — triggered signal names
    """
    score: float = 0.0
    flags: list[str] = []

    # --- Signal 1: fresh wallet proxy ---
    # crypto_recent_decisions_30d == 0 AND wallet address looks like an on-chain address
    recent_30d = int(profile.get("crypto_recent_decisions_30d") or 0)
    wallet_addr = str(profile.get("wallet") or "")
    if recent_30d == 0 and wallet_addr.startswith("0x"):
        score += 0.30
        flags.append("fresh_wallet")

    # --- Signal 2: thin lifetime history ---
    # crypto_decisions < 10 → potentially new / purpose-built wallet
    crypto_decisions = int(profile.get("crypto_decisions") or 0)
    if crypto_decisions < 10:
        score += 0.20
        flags.append("thin_history")

    # --- Signal 3: suspicious entry timing ---
    # High latency_arb_score correlates with wallets that front-run short windows,
    # matching the "sniper" pattern in the reference tracker.
    latency_arb_score = float(profile.get("latency_arb_score") or 0.0)
    if latency_arb_score > 0.4:
        score += 0.20
        flags.append("latency_arb")

    # --- Signal 4: single-market concentration (niche market proxy) ---
    # A wallet that puts >80 % of its PnL into one market behaves like an
    # insider who only has an edge in one niche event.
    top_pnl_share = float(profile.get("crypto_top_symbol_pnl_share") or 0.0)
    if top_pnl_share > 0.80:
        score += 0.15
        flags.append("niche_market_concentration")

    # --- Signal 5: suspiciously high win rate ---
    # Bayes-smoothed WR > 80 % over a thin sample is a strong anomaly signal.
    win_rate_bayes = float(profile.get("crypto_win_rate_bayes") or 0.0)
    if win_rate_bayes > 0.80:
        score += 0.15
        flags.append("high_win_rate")

    # Cap at 1.0
    score = min(round(score, 4), 1.0)

    if score >= 0.70:
        confidence = "HIGH"
    elif score >= 0.40:
        confidence = "MEDIUM"
    elif score >= 0.20:
        confidence = "LOW"
    else:
        confidence = "NONE"

    return {
        "insider_confidence": confidence,
        "insider_score": score,
        "flags": flags,
    }


def _score_wallet(row: dict[str, Any]) -> dict[str, Any] | None:
    wallet = str(row.get("proxyWallet") or "").lower()
    if not wallet:
        return None

    closed_positions = fetch_closed_positions(wallet)
    directional_history = _group_directional_markets(closed_positions, use_open_notional=False)
    if not directional_history:
        return None

    per_symbol: dict[str, dict[str, Any]] = {}
    for market in directional_history:
        symbol = market["symbol"]
        stats = per_symbol.setdefault(
            symbol,
            {"decisions": 0, "wins": 0, "total_pnl": 0.0, "sample_titles": []},
        )
        stats["decisions"] += 1
        stats["wins"] += 1 if market["net_pnl"] > 0 else 0
        stats["total_pnl"] += market["net_pnl"]
        if len(stats["sample_titles"]) < 3:
            stats["sample_titles"].append(market["title"])

    qualified_symbols: dict[str, dict[str, Any]] = {}
    for symbol, stats in per_symbol.items():
        decisions = int(stats["decisions"])
        wins = int(stats["wins"])
        total_pnl = float(stats["total_pnl"])
        win_rate = wins / decisions if decisions else 0.0
        win_rate_bayes = _bayes_win_rate(
            wins,
            decisions,
            prior_mean=SYMBOL_BAYES_PRIOR_WIN_RATE,
            prior_strength=SYMBOL_BAYES_PRIOR_STRENGTH,
        )
        avg_pnl = total_pnl / decisions if decisions else 0.0
        if (
            decisions >= MIN_SYMBOL_DECISIONS
            and win_rate >= MIN_SYMBOL_WIN_RATE
            and total_pnl >= MIN_SYMBOL_TOTAL_PNL
        ):
            qualified_symbols[symbol] = {
                "decisions": decisions,
                "wins": wins,
                "win_rate": round(win_rate, 4),
                "win_rate_bayes": round(win_rate_bayes, 4),
                "total_pnl": round(total_pnl, 2),
                "avg_pnl": round(avg_pnl, 2),
                "sample_titles": stats["sample_titles"],
            }

    if not qualified_symbols:
        return None

    alias = _wallet_alias(str(row.get("userName") or ""), wallet)
    total_decisions = sum(v["decisions"] for v in qualified_symbols.values())
    total_wins = sum(v["wins"] for v in qualified_symbols.values())
    total_pnl = sum(v["total_pnl"] for v in qualified_symbols.values())
    if total_decisions < MIN_PROFILE_DECISIONS:
        return None

    raw_win_rate = total_wins / total_decisions if total_decisions else 0.0
    bayes_win_rate = _bayes_win_rate(
        total_wins,
        total_decisions,
        prior_mean=PROFILE_BAYES_PRIOR_WIN_RATE,
        prior_strength=PROFILE_BAYES_PRIOR_STRENGTH,
    )
    recent = _compute_recent_form(directional_history)
    concentration = _compute_concentration_metrics(qualified_symbols)
    archetype = _classify_wallet_archetype(
        directional_history,
        qualified_symbols,
        _safe_float(row.get("vol")),
    )
    latency_arb = _detect_latency_arb(
        directional_history,
        _safe_float(row.get("vol")),
    )
    copyability = _apply_copyability_gate(archetype, latency_arb)
    sample_tier = _profile_sample_tier(total_decisions)
    base_profile_score = _profile_rank_score(wins=total_wins, decisions=total_decisions)
    adjusted_profile_score = base_profile_score * (1.0 - _safe_float(concentration.get("crypto_concentration_penalty")))

    base_profile: dict[str, Any] = {
        "wallet": wallet,
        "user_name": str(row.get("userName") or wallet),
        "alias": alias,
        "leaderboard_rank": int(_safe_float(row.get("rank"), 0)),
        "leaderboard_pnl": round(_safe_float(row.get("pnl")), 2),
        "leaderboard_volume": round(_safe_float(row.get("vol")), 2),
        "leaderboard_source": str(row.get("leaderboardSource") or "generic_leaderboard"),
        "crypto_profit_rank": int(_safe_float(row.get("cryptoProfitRank"), 0)),
        "crypto_volume_rank": int(_safe_float(row.get("cryptoVolumeRank"), 0)),
        "verified_badge": bool(row.get("verifiedBadge")),
        "crypto_decisions": total_decisions,
        "crypto_win_rate": round(raw_win_rate, 4),
        "crypto_win_rate_bayes": round(bayes_win_rate, 4),
        "crypto_total_pnl": round(total_pnl, 2),
        "crypto_profile_score": round(adjusted_profile_score, 4),
        "crypto_sample_tier": sample_tier,
        "meets_min_crypto_history": True,
        "established_crypto_history": sample_tier == "established",
        "crypto_market_count": len(directional_history),
        **recent,
        **concentration,
        **archetype,
        **latency_arb,
        **copyability,
        "qualified_symbols": qualified_symbols,
    }
    insider = _insider_confidence_score(base_profile)
    return {**base_profile, **insider}


def _fetch_spot_price(symbol: str) -> float | None:
    if symbol in _SPOT_CACHE:
        return _SPOT_CACHE[symbol]
    # Try Binance mirrors (non-geo-blocked first)
    for url in BINANCE_PRICE_URLS:
        data = _fetch_json(url, {"symbol": symbol})
        if isinstance(data, dict):
            price = _safe_float(data.get("price"), 0.0)
            if price > 0:
                _SPOT_CACHE[symbol] = price
                return price
    # Fallback: CoinGecko
    _CG_IDS = {"BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "SOLUSDT": "solana",
                "XRPUSDT": "ripple", "DOGEUSDT": "dogecoin", "BNBUSDT": "binancecoin",
                "ADAUSDT": "cardano", "AVAXUSDT": "avalanche-2"}
    cg_id = _CG_IDS.get(symbol)
    if cg_id:
        data = _fetch_json("https://api.coingecko.com/api/v3/simple/price",
                           {"ids": cg_id, "vs_currencies": "usd"})
        if isinstance(data, dict) and cg_id in data:
            price = _safe_float(data[cg_id].get("usd"), 0.0)
            if price > 0:
                _SPOT_CACHE[symbol] = price
                return price
    _SPOT_CACHE[symbol] = None
    return None


def _tp_sl(entry_price: float, hours_to_expiry: float) -> tuple[float, float, str]:
    if hours_to_expiry <= 6:
        tp_pct, sl_pct, timeframe = 0.015, 0.010, "SCALP"
    elif hours_to_expiry <= 24:
        tp_pct, sl_pct, timeframe = 0.025, 0.015, "INTRADAY"
    elif hours_to_expiry <= 72:
        tp_pct, sl_pct, timeframe = 0.040, 0.020, "SWING"
    else:
        tp_pct, sl_pct, timeframe = 0.060, 0.030, "POSITION"
    return entry_price, tp_pct, sl_pct, timeframe


def _build_pick(
    profile: dict[str, Any],
    symbol_signal: dict[str, Any],
    now: datetime,
) -> dict[str, Any] | None:
    if not profile.get("copyable_archetype", True):
        return None
    if not symbol_signal.get("entry_quality_pass", True):
        return None

    symbol = symbol_signal["symbol"]
    direction = symbol_signal["direction"]
    stats = profile["qualified_symbols"][symbol]
    entry_price = _fetch_spot_price(symbol)
    if not entry_price or entry_price <= 0:
        return None

    hours_to_expiry = symbol_signal["hours_to_expiry"]
    _, tp_pct, sl_pct, timeframe = _tp_sl(entry_price, hours_to_expiry)
    if direction == "LONG":
        take_profit = round(entry_price * (1 + tp_pct), 8)
        stop_loss = round(entry_price * (1 - sl_pct), 8)
        signal_type = "BUY"
    else:
        take_profit = round(entry_price * (1 - tp_pct), 8)
        stop_loss = round(entry_price * (1 + sl_pct), 8)
        signal_type = "SELL"

    wr_raw = float(stats["win_rate"])
    wr = float(stats.get("win_rate_bayes") or wr_raw)
    wr_bonus = min(max((wr - 0.55) / 0.25, 0.0), 1.0) * 0.15
    sample_bonus = min(stats["decisions"] / 25.0, 1.0) * 0.10
    pnl_bonus = min(math.log10(max(stats["total_pnl"], 1.0) + 1.0) / 5.0, 1.0) * 0.10
    dominance_bonus = min(max((symbol_signal["dominance"] - 0.60) / 0.40, 0.0), 1.0) * 0.10
    notional_bonus = min(symbol_signal["total_notional"] / 5000.0, 1.0) * 0.05
    recent_30d_decisions = int(profile.get("crypto_recent_decisions_30d") or 0)
    recent_30d_score = _safe_float(profile.get("crypto_recent_score_30d"))
    recent_90d_score = _safe_float(profile.get("crypto_recent_score_90d"))
    recent_bonus = 0.0
    if recent_30d_decisions >= RECENT_FORM_MIN_DECISIONS:
        recent_bonus = min(recent_30d_score / 0.85, 1.0) * 0.08
    elif int(profile.get("crypto_recent_decisions_90d") or 0) >= MIN_PROFILE_DECISIONS:
        recent_bonus = min(recent_90d_score / 0.85, 1.0) * 0.04
    concentration_penalty = min(
        max((_safe_float(profile.get("crypto_top_symbol_pnl_share")) - 0.60) / 0.25, 0.0),
        1.0,
    ) * 0.07
    archetype_penalty = 0.08 if not profile.get("copyable_archetype", True) else 0.0
    confidence = round(
        min(
            0.95,
            max(
                0.50,
                0.55
                + wr_bonus
                + sample_bonus
                + pnl_bonus
                + dominance_bonus
                + notional_bonus
                + recent_bonus
                - concentration_penalty
                - archetype_penalty,
            ),
        ),
        3,
    )

    strategy = f"copy_pm_{profile['alias']}"
    ts = now.strftime("%Y-%m-%d_%H%M")
    archetype = str(profile.get("wallet_archetype") or "directional_generalist")
    reason = (
        f"Polymarket wallet {profile['user_name']} rank #{profile['leaderboard_rank']} "
        f"is net {direction} {symbol} across {symbol_signal['market_count']} open markets; "
        f"{stats['decisions']} closed crypto decisions, adj WR {wr:.1%} "
        f"(raw {wr_raw:.1%}), PnL ${stats['total_pnl']:,.0f}, archetype {archetype}, "
        f"latency risk {profile.get('latency_arb_score', 0):.2f}, "
        f"entry quality {symbol_signal.get('entry_quality_score', 0):.2f}. "
        f"Lead market: {symbol_signal['lead_title']}"
    )

    return {
        "id": f"{strategy}::{symbol}::{ts}",
        "symbol": symbol,
        "direction": direction,
        "signal_type": signal_type,
        "entry_price": round(entry_price, 8),
        "take_profit": take_profit,
        "stop_loss": stop_loss,
        "confidence": confidence,
        "strategy": strategy,
        "source_system": "copy_trader_polymarket",
        "category": "crypto",
        "status": "OPEN",
        "entry_date": now.strftime("%Y-%m-%d"),
        "timestamp": now.isoformat(),
        "trade_timeframe": timeframe,
        "allocation": 100,
        "position_sizing": "copy_trader",
        "risk_per_trade_pct": 0.01,
        "max_safe_leverage": 2,
        "trader_address": profile["wallet"],
        "trader_name": profile["user_name"],
        "trader_pnl": profile["leaderboard_pnl"],
        "leaderboard_rank": profile["leaderboard_rank"],
        "leaderboard_source": profile.get("leaderboard_source"),
        "crypto_profit_rank": profile.get("crypto_profit_rank"),
        "crypto_volume_rank": profile.get("crypto_volume_rank"),
        "profile_crypto_wr": profile.get("crypto_win_rate"),
        "profile_crypto_wr_bayes": profile.get("crypto_win_rate_bayes"),
        "profile_crypto_score": profile.get("crypto_profile_score"),
        "profile_crypto_sample_tier": profile.get("crypto_sample_tier"),
        "profile_crypto_recent_score_30d": profile.get("crypto_recent_score_30d"),
        "profile_crypto_recent_score_90d": profile.get("crypto_recent_score_90d"),
        "wallet_archetype": archetype,
        "archetype_copyable": profile.get("archetype_copyable", True),
        "copyable_archetype": profile.get("copyable_archetype", True),
        "copyability_gate_reason": profile.get("copyability_gate_reason"),
        "latency_arb_flag": profile.get("latency_arb_flag", False),
        "latency_arb_score": profile.get("latency_arb_score"),
        "latency_arb_title_share": profile.get("latency_arb_title_share"),
        "latency_arb_short_expiry_share": profile.get("latency_arb_short_expiry_share"),
        "latency_arb_ultrashort_share": profile.get("latency_arb_ultrashort_share"),
        "entry_quality_pass": symbol_signal.get("entry_quality_pass", True),
        "entry_quality_score": symbol_signal.get("entry_quality_score"),
        "entry_quality_gate_reason": symbol_signal.get("entry_quality_gate_reason"),
        "entry_quality_contract_price": symbol_signal.get("entry_quality_contract_price"),
        "entry_quality_directional_notional": symbol_signal.get("entry_quality_directional_notional"),
        "entry_quality_lead_notional": symbol_signal.get("entry_quality_lead_notional"),
        "crypto_top_symbol": profile.get("crypto_top_symbol"),
        "crypto_top_symbol_pnl_share": profile.get("crypto_top_symbol_pnl_share"),
        "history_trades": stats["decisions"],
        "history_wr": round(wr_raw, 4),
        "history_wr_bayes": round(wr, 4),
        "history_avg_pnl": stats["avg_pnl"],
        "history_total_pnl": stats["total_pnl"],
        "history_basis": "polymarket_closed_positions",
        "forward_trades": stats["decisions"],
        "forward_wr": round(wr_raw, 4),
        "forward_wr_bayes": round(wr, 4),
        "forward_validated": False,
        "reason": reason,
        "consensus_count": symbol_signal["market_count"],
        "consensus_sources": [profile["wallet"]],
        "copy_source": "polymarket_wallet",
        "copy_signal": {
            "lead_market": symbol_signal["lead_title"],
            "lead_market_direction": symbol_signal["lead_market_direction"],
            "lead_market_end": symbol_signal["lead_end_date"],
            "hours_to_expiry": round(hours_to_expiry, 2),
            "dominance": round(symbol_signal["dominance"], 4),
            "total_notional": round(symbol_signal["total_notional"], 2),
            "directional_notional": round(symbol_signal["directional_notional"], 2),
            "lead_notional": round(symbol_signal["lead_notional"], 2),
            "lead_contract_price": symbol_signal.get("lead_contract_price"),
            "market_titles": symbol_signal["market_titles"][:5],
            "wallet_archetype": archetype,
            "latency_arb_flag": profile.get("latency_arb_flag", False),
            "latency_arb_score": profile.get("latency_arb_score"),
            "copyable_archetype": profile.get("copyable_archetype", True),
            "entry_quality_pass": symbol_signal.get("entry_quality_pass", True),
            "entry_quality_score": symbol_signal.get("entry_quality_score"),
            "entry_quality_gate_reason": symbol_signal.get("entry_quality_gate_reason"),
        },
    }


def _resolve_direction_conflicts(picks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pick in picks:
        symbol = str(pick.get("symbol") or "").upper()
        if not symbol:
            continue
        by_symbol[symbol].append(pick)

    resolved: list[dict[str, Any]] = []
    for symbol, group in by_symbol.items():
        directions = {str(p.get("direction") or "").upper() for p in group if p.get("direction")}
        if len(directions) <= 1:
            resolved.extend(group)
            continue

        direction_scores: dict[str, tuple[float, float, int]] = {}
        for direction in ("LONG", "SHORT"):
            picks_for_direction = [p for p in group if str(p.get("direction") or "").upper() == direction]
            if not picks_for_direction:
                continue
            total_conf = sum(_safe_float(p.get("confidence")) for p in picks_for_direction)
            top_conf = max(_safe_float(p.get("confidence")) for p in picks_for_direction)
            direction_scores[direction] = (total_conf, top_conf, len(picks_for_direction))

        winner_direction = max(
            direction_scores.items(),
            key=lambda item: (item[1][0], item[1][1], item[1][2]),
        )[0]
        resolved.extend(
            pick
            for pick in group
            if str(pick.get("direction") or "").upper() == winner_direction
        )

    return resolved


def _extract_symbol_signals(profile: dict[str, Any]) -> list[dict[str, Any]]:
    open_positions = fetch_open_positions(profile["wallet"])
    markets = _group_directional_markets(open_positions, use_open_notional=True)
    if not markets:
        return []

    by_symbol: dict[str, dict[str, Any]] = {}
    now = datetime.now(timezone.utc)
    for market in markets:
        symbol = market["symbol"]
        if symbol not in profile["qualified_symbols"]:
            continue

        end_dt = _parse_dt(market["end_date"])
        if end_dt is None:
            continue
        hours_to_expiry = (end_dt - now).total_seconds() / 3600
        if hours_to_expiry <= 0:
            continue

        bucket = by_symbol.setdefault(
            symbol,
            {
                "symbol": symbol,
                "notional_by_direction": defaultdict(float),
                "price_x_notional_by_direction": defaultdict(float),
                "market_count": 0,
                "market_titles": [],
                "lead_title_by_direction": {},
                "lead_end_date_by_direction": {},
                "lead_notional_by_direction": defaultdict(float),
                "lead_contract_price_by_direction": {},
            },
        )
        bucket["notional_by_direction"][market["direction"]] += market["dominant_notional"]
        bucket["price_x_notional_by_direction"][market["direction"]] += (
            market["dominant_notional"] * _safe_float(market.get("dominant_avg_price"))
        )
        bucket["market_count"] += 1
        if len(bucket["market_titles"]) < 8:
            bucket["market_titles"].append(market["title"])
        direction = market["direction"]
        if market["dominant_notional"] > bucket["lead_notional_by_direction"][direction]:
            bucket["lead_notional_by_direction"][direction] = market["dominant_notional"]
            bucket["lead_title_by_direction"][direction] = market["title"]
            bucket["lead_end_date_by_direction"][direction] = market["end_date"]
            bucket["lead_contract_price_by_direction"][direction] = round(
                _safe_float(market.get("dominant_avg_price")),
                4,
            )

    signals: list[dict[str, Any]] = []
    for bucket in by_symbol.values():
        long_notional = bucket["notional_by_direction"].get("LONG", 0.0)
        short_notional = bucket["notional_by_direction"].get("SHORT", 0.0)
        total_notional = long_notional + short_notional
        if total_notional < MIN_SIGNAL_NOTIONAL:
            continue

        direction = "LONG" if long_notional >= short_notional else "SHORT"
        directional_notional = max(long_notional, short_notional)
        dominance = directional_notional / total_notional
        if dominance < 0.60:
            continue

        lead_end_date = str(bucket["lead_end_date_by_direction"].get(direction) or "")
        lead_dt = _parse_dt(lead_end_date)
        if lead_dt is None:
            continue
        hours_to_expiry = (lead_dt - datetime.now(timezone.utc)).total_seconds() / 3600
        lead_notional = _safe_float(bucket["lead_notional_by_direction"].get(direction))
        lead_contract_price = _safe_float(bucket["lead_contract_price_by_direction"].get(direction))
        entry_quality = _evaluate_entry_quality(
            directional_notional=directional_notional,
            lead_notional=lead_notional,
            hours_to_expiry=hours_to_expiry,
            contract_price=lead_contract_price,
            market_count=bucket["market_count"],
        )
        if not entry_quality["entry_quality_pass"]:
            continue

        directional_avg_price = 0.0
        if directional_notional > 0:
            directional_avg_price = (
                _safe_float(bucket["price_x_notional_by_direction"].get(direction)) / directional_notional
            )

        signals.append(
            {
                "symbol": bucket["symbol"],
                "direction": direction,
                "dominance": dominance,
                "total_notional": total_notional,
                "directional_notional": directional_notional,
                "market_count": bucket["market_count"],
                "market_titles": bucket["market_titles"],
                "lead_title": str(bucket["lead_title_by_direction"].get(direction) or ""),
                "lead_market_direction": direction,
                "lead_end_date": lead_end_date,
                "lead_notional": lead_notional,
                "lead_contract_price": round(lead_contract_price, 4),
                "directional_avg_contract_price": round(directional_avg_price, 4),
                "hours_to_expiry": hours_to_expiry,
                **entry_quality,
            }
        )

    return signals


def scan_polymarket_traders(max_traders: int = LEADERBOARD_LIMIT) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (qualified_profiles, live_picks)."""
    leaderboard = fetch_candidate_leaderboard(limit=max_traders)
    if not leaderboard:
        print("  [WARN] Polymarket leaderboard returned no rows")
        return [], []

    qualified_profiles: list[dict[str, Any]] = []
    for idx, row in enumerate(leaderboard, 1):
        profile = _score_wallet(row)
        if profile:
            qualified_profiles.append(profile)
            print(
                f"  [PM] #{idx:02d} {profile['user_name']} -> "
                f"{profile['crypto_decisions']} crypto decisions, "
                f"WR {profile['crypto_win_rate']:.1%}, "
                f"adj {profile['crypto_win_rate_bayes']:.1%}, "
                f"30d {profile.get('crypto_recent_decisions_30d', 0)}d/{profile.get('crypto_recent_pnl_30d', 0):,.0f}, "
                f"{profile.get('wallet_archetype', 'unknown')}, "
                f"lat {profile.get('latency_arb_score', 0):.2f}/{profile.get('copyability_gate_reason') or 'ok'}, "
                f"PnL ${profile['crypto_total_pnl']:,.0f}"
            )
        time.sleep(0.10)

    qualified_profiles.sort(key=_profile_rank_sort_key, reverse=True)
    qualified_profiles = qualified_profiles[:MAX_QUALIFIED_TRADERS]

    now = datetime.now(timezone.utc)
    picks: list[dict[str, Any]] = []
    for profile in qualified_profiles:
        for symbol_signal in _extract_symbol_signals(profile):
            pick = _build_pick(profile, symbol_signal, now)
            if pick:
                picks.append(pick)
        time.sleep(0.05)

    pre_conflict_count = len(picks)
    picks = _resolve_direction_conflicts(picks)
    if len(picks) != pre_conflict_count:
        print(f"  [PM] Conflict-resolved raw picks: {pre_conflict_count} -> {len(picks)}")

    return qualified_profiles, picks


def save_polymarket_results(profiles: list[dict[str, Any]], picks: list[dict[str, Any]]) -> None:
    profiles_path = DATA_DIR / "polymarket_trader_profiles.json"
    picks_path = DATA_DIR / "polymarket_picks.json"

    with open(profiles_path, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "source": "polymarket_crypto_leaderboard+data_api",
                "leaderboard_url": CRYPTO_LEADERBOARD_PAGE_URL,
                "qualified_traders": profiles,
            },
            fh,
            indent=2,
            default=str,
        )

    with open(picks_path, "w", encoding="utf-8") as fh:
        json.dump(picks, fh, indent=2, default=str)

    print(f"  [PM] Saved {len(profiles)} trader profiles -> {profiles_path}")
    print(f"  [PM] Saved {len(picks)} live picks      -> {picks_path}")


def run() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    print("=" * 68)
    print("  Polymarket Wallet Intelligence")
    print("=" * 68)
    profiles, picks = scan_polymarket_traders()
    save_polymarket_results(profiles, picks)
    print(
        f"  [PM] Complete: {len(profiles)} qualified wallets, "
        f"{len(picks)} live crypto picks"
    )
    return profiles, picks


if __name__ == "__main__":
    run()
