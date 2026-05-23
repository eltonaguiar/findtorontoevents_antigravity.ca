"""
ALPHA_ENGINE -- Hindsight Learner
=================================
Hourly feedback loop designed more like post-trade attribution / execution TCA
(Jane Street / Jump style) than a simple gainer scrape.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import ssl
import statistics
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

try:
    from alpha_engine.config import CRYPTO_SYMBOLS, DATA_DIR
except ImportError:
    from config import CRYPTO_SYMBOLS, DATA_DIR

try:
    from alpha_engine.bandit_tp_sl import ARMS as BANDIT_ARMS
except ImportError:
    try:
        from bandit_tp_sl import ARMS as BANDIT_ARMS
    except Exception:
        BANDIT_ARMS = [
            (1.5, 0.75),
            (2.0, 1.0),
            (2.5, 1.0),
            (3.0, 1.5),
            (2.0, 0.5),
            (1.5, 1.0),
            (3.0, 1.0),
        ]


HINDSIGHT_DIR = DATA_DIR / "hindsight"
SNAPSHOT_DIR = HINDSIGHT_DIR / "snapshots"
EVALUATION_DIR = HINDSIGHT_DIR / "evaluations"
STATE_PATH = HINDSIGHT_DIR / "state.json"
SUMMARY_PATH = HINDSIGHT_DIR / "summary.json"
LEGACY_LOG_PATH = DATA_DIR / "hindsight_log.json"
ACTIVE_PICK_FILES = (
    DATA_DIR / "active_picks_fast.json",
    DATA_DIR / "active_picks.json",
)
UNIVERSE_CACHE_PATH = DATA_DIR / "cache" / "universe_cache.json"

BINANCE_BASES = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://data-api.binance.vision",
    "https://api.binance.us",
]

if os.environ.get("GITHUB_ACTIONS"):
    _preferred = ["https://data-api.binance.vision", "https://api.binance.us"]
    BINANCE_BASES = _preferred + [url for url in BINANCE_BASES if url not in _preferred]

DEFAULT_HORIZON_HOURS = float(os.environ.get("ALPHA_HINDSIGHT_HOURS", "1"))
DEFAULT_TOP_K = int(os.environ.get("ALPHA_HINDSIGHT_TOPK", "10"))
DEFAULT_UNIVERSE_SIZE = int(os.environ.get("ALPHA_HINDSIGHT_UNIVERSE", "150"))
MIN_QUOTE_VOLUME = float(os.environ.get("ALPHA_HINDSIGHT_MIN_QUOTE_VOL", "5000000"))
SNAPSHOT_COOLDOWN_MINUTES = int(os.environ.get("ALPHA_HINDSIGHT_COOLDOWN_MIN", "45"))
ENTRY_WINDOW_RATIO = float(os.environ.get("ALPHA_HINDSIGHT_ENTRY_WINDOW_RATIO", "0.25"))
MAX_CASE_STUDIES = int(os.environ.get("ALPHA_HINDSIGHT_CASES", "5"))
KLINE_INTERVAL = os.environ.get("ALPHA_HINDSIGHT_INTERVAL", "5m")

STABLE_BASES = {
    "USDT", "USDC", "BUSD", "FDUSD", "TUSD", "USDP", "DAI", "EUR", "EURS",
    "PAX", "USDN", "UST", "USTC", "FRAX", "LUSD", "SUSD",
}
LEVERAGED_SUFFIXES = ("UP", "DOWN", "BULL", "BEAR", "3L", "3S", "5L", "5S")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
        if math.isnan(out) or math.isinf(out):
            return default
        return out
    except (TypeError, ValueError):
        return default


def _read_json(path: Path, default: Any) -> Any:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def _parse_dt(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _snapshot_path(snapshot_id: str) -> Path:
    return SNAPSHOT_DIR / f"{snapshot_id}.json"


def _evaluation_path(snapshot_id: str) -> Path:
    return EVALUATION_DIR / f"{snapshot_id}.json"


def _load_state() -> dict[str, Any]:
    return _read_json(STATE_PATH, {"last_snapshot_at": None, "last_run_at": None})


def _save_state(state: dict[str, Any]) -> None:
    _write_json(STATE_PATH, state)


def _ensure_dirs() -> None:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    EVALUATION_DIR.mkdir(parents=True, exist_ok=True)


def _fetch_json(url: str, timeout: int = 12) -> Optional[Any]:
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "AlphaHindsightLearner/2.0"},
        )
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def _fetch_binance_json(path: str, timeout: int = 12) -> Optional[Any]:
    for base in BINANCE_BASES:
        payload = _fetch_json(f"{base}{path}", timeout=timeout)
        if payload is not None:
            return payload
    return None


def _build_symbol_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for raw_symbol, meta in CRYPTO_SYMBOLS.items():
        binance_symbol = str(meta.get("binance", "")).upper().strip()
        if not binance_symbol:
            continue
        mapping[str(raw_symbol).upper()] = binance_symbol
        yf_symbol = str(meta.get("yf_ticker", "")).upper().strip()
        if yf_symbol:
            mapping[yf_symbol] = binance_symbol
    return mapping


SYMBOL_MAP = _build_symbol_map()


def _build_static_universe() -> set[str]:
    symbols = {str(meta.get("binance", "")).upper() for meta in CRYPTO_SYMBOLS.values()}
    symbols = {sym for sym in symbols if sym}
    cache = _read_json(UNIVERSE_CACHE_PATH, {})
    for entry in cache.get("added_entries", []):
        meta = entry.get("meta", {}) if isinstance(entry, dict) else {}
        binance_symbol = str(meta.get("binance", "")).upper().strip()
        if binance_symbol:
            symbols.add(binance_symbol)
    return symbols


STATIC_UNIVERSE = _build_static_universe()


def _normalize_binance_symbol(symbol: Any) -> str:
    sym = str(symbol or "").upper().strip().replace("/", "").replace(" ", "")
    if not sym:
        return ""
    if sym in SYMBOL_MAP:
        return SYMBOL_MAP[sym]
    if sym.endswith("USDT"):
        return sym
    if sym.endswith("-USD"):
        return SYMBOL_MAP.get(sym, sym[:-4].replace("-", "") + "USDT")
    if sym.endswith("USD") and not sym.endswith("USDT"):
        return SYMBOL_MAP.get(sym, sym[:-3] + "USDT")
    return SYMBOL_MAP.get(sym, sym)


def _is_tradeable_usdt_symbol(symbol: str) -> bool:
    if not symbol.endswith("USDT"):
        return False
    base = symbol[:-4]
    if base in STABLE_BASES:
        return False
    if any(base.endswith(suffix) for suffix in LEVERAGED_SUFFIXES):
        return False
    return True


def _extract_entries(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        return [row for row in raw if isinstance(row, dict)]
    if isinstance(raw, dict):
        for key in ("picks", "activePicks"):
            value = raw.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
    return []


def _pick_score(pick: dict[str, Any]) -> float:
    for key in ("fresh_score", "elite_score", "ml_score"):
        if key in pick and pick.get(key) is not None:
            raw = _safe_float(pick.get(key))
            if key == "ml_score" and raw <= 1.0:
                return round(raw * 100.0, 4)
            return round(raw, 4)
    confidence = _safe_float(pick.get("confidence"))
    if confidence <= 1.0:
        confidence *= 100.0
    return round(confidence, 4)


def load_candidate_picks() -> list[dict[str, Any]]:
    by_symbol: dict[str, dict[str, Any]] = {}
    for path in ACTIVE_PICK_FILES:
        raw = _read_json(path, None)
        if raw is None:
            continue
        for pick in _extract_entries(raw):
            binance_symbol = _normalize_binance_symbol(pick.get("symbol"))
            if not _is_tradeable_usdt_symbol(binance_symbol):
                continue
            direction = str(pick.get("direction") or pick.get("signal_type") or "LONG").upper()
            if direction in ("SELL", "SHORT"):
                continue
            score = _pick_score(pick)
            record = {
                "symbol": str(pick.get("symbol", "")),
                "binance_symbol": binance_symbol,
                "direction": "LONG",
                "score": score,
                "entry_price": round(_safe_float(pick.get("entry_price")), 8),
                "take_profit": round(_safe_float(pick.get("take_profit")), 8),
                "stop_loss": round(_safe_float(pick.get("stop_loss")), 8),
                "strategy": str(pick.get("strategy", "unknown")),
                "strategies": [str(pick.get("strategy", "unknown"))],
                "timestamp": str(pick.get("timestamp") or pick.get("created_at") or ""),
                "source_file": path.name,
            }
            current = by_symbol.get(binance_symbol)
            if current is None or record["score"] > current["score"]:
                if current is not None:
                    record["strategies"] = sorted(set(current["strategies"] + record["strategies"]))
                by_symbol[binance_symbol] = record
            elif current is not None:
                current["strategies"] = sorted(set(current["strategies"] + record["strategies"]))
    ranked = sorted(by_symbol.values(), key=lambda row: (-row["score"], row["binance_symbol"]))
    for rank, row in enumerate(ranked, start=1):
        row["rank"] = rank
    return ranked


def _fetch_binance_24h_rows() -> dict[str, dict[str, Any]]:
    payload = _fetch_binance_json("/api/v3/ticker/24hr")
    if not isinstance(payload, list):
        return {}
    rows: dict[str, dict[str, Any]] = {}
    for item in payload:
        symbol = str(item.get("symbol", "")).upper()
        if not _is_tradeable_usdt_symbol(symbol):
            continue
        price = _safe_float(item.get("lastPrice"))
        if price <= 0:
            continue
        rows[symbol] = {
            "symbol": symbol,
            "price": round(price, 8),
            "quote_volume": round(_safe_float(item.get("quoteVolume")), 2),
            "trades": int(_safe_float(item.get("count"))),
            "change_24h_pct": round(_safe_float(item.get("priceChangePercent")), 4),
        }
    return rows


def build_market_snapshot(
    forced_symbols: set[str],
    static_symbols: set[str],
    universe_size: int,
    min_quote_volume: float,
) -> dict[str, dict[str, Any]]:
    rows = _fetch_binance_24h_rows()
    if not rows:
        return {}
    liquid = [row for row in rows.values() if row["quote_volume"] >= min_quote_volume]
    liquid.sort(key=lambda row: row["quote_volume"], reverse=True)

    universe: dict[str, dict[str, Any]] = {}
    for row in liquid[:universe_size]:
        symbol = row["symbol"]
        universe[symbol] = {
            **row,
            "source": "liquid_24h",
            "in_static_universe": symbol in static_symbols,
        }

    for symbol in sorted(forced_symbols):
        if symbol in rows and symbol not in universe:
            universe[symbol] = {
                **rows[symbol],
                "source": "forced_symbol",
                "in_static_universe": symbol in static_symbols,
            }
    return universe


def create_snapshot(
    *,
    top_k: int = DEFAULT_TOP_K,
    horizon_hours: float = DEFAULT_HORIZON_HOURS,
    force: bool = False,
) -> dict[str, Any]:
    _ensure_dirs()
    now = _utc_now()
    state = _load_state()
    last_snapshot_at = _parse_dt(state.get("last_snapshot_at"))
    if (
        last_snapshot_at is not None
        and not force
        and (now - last_snapshot_at).total_seconds() < SNAPSHOT_COOLDOWN_MINUTES * 60
    ):
        return {
            "status": "skipped_cooldown",
            "last_snapshot_at": last_snapshot_at.isoformat(),
        }

    candidates = load_candidate_picks()
    candidate_symbols = {row["binance_symbol"] for row in candidates}
    market_snapshot = build_market_snapshot(
        forced_symbols=candidate_symbols | STATIC_UNIVERSE,
        static_symbols=STATIC_UNIVERSE,
        universe_size=DEFAULT_UNIVERSE_SIZE,
        min_quote_volume=MIN_QUOTE_VOLUME,
    )
    if not market_snapshot:
        return {"status": "no_market_snapshot"}

    snapshot_id = now.strftime("%Y%m%dT%H%M%SZ")
    snapshot = {
        "snapshot_id": snapshot_id,
        "created_at": now.isoformat(),
        "horizon_hours": horizon_hours,
        "top_k": top_k,
        "candidate_count": len(candidates),
        "top_candidates": candidates,
        "static_universe_symbols": sorted(STATIC_UNIVERSE),
        "universe_prices": market_snapshot,
        "selected_top_symbols": [row["binance_symbol"] for row in candidates[:top_k]],
    }
    _write_json(_snapshot_path(snapshot_id), snapshot)
    state["last_snapshot_at"] = now.isoformat()
    state["last_snapshot_id"] = snapshot_id
    _save_state(state)
    return {
        "status": "created",
        "snapshot_id": snapshot_id,
        "candidate_count": len(candidates),
        "universe_size": len(market_snapshot),
    }


def _compute_forward_returns(
    snapshot_universe: dict[str, dict[str, Any]],
    current_universe: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for symbol, snap in snapshot_universe.items():
        now_row = current_universe.get(symbol)
        snapshot_price = _safe_float(snap.get("price"))
        current_price = _safe_float(now_row.get("price")) if now_row else 0.0
        if snapshot_price <= 0 or current_price <= 0:
            continue
        forward_return = ((current_price - snapshot_price) / snapshot_price) * 100.0
        out[symbol] = {
            "symbol": symbol,
            "snapshot_price": round(snapshot_price, 8),
            "current_price": round(current_price, 8),
            "forward_return_pct": round(forward_return, 4),
            "quote_volume_snapshot": round(_safe_float(snap.get("quote_volume")), 2),
            "change_24h_snapshot_pct": round(_safe_float(snap.get("change_24h_pct")), 4),
            "in_static_universe": bool(snap.get("in_static_universe")),
        }
    return out


def _rank_true_top(
    return_map: dict[str, dict[str, Any]],
    top_k: int,
) -> list[dict[str, Any]]:
    rows = sorted(return_map.values(), key=lambda row: row["forward_return_pct"], reverse=True)
    positive = [row for row in rows if row["forward_return_pct"] > 0]
    selected = positive[:top_k] if positive else rows[:top_k]
    for rank, row in enumerate(selected, start=1):
        row["true_rank"] = rank
    return selected


def _compute_overlap_metrics(
    our_symbols: list[str],
    true_top: list[dict[str, Any]],
    return_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    true_symbols = [row["symbol"] for row in true_top]
    true_symbol_set = set(true_symbols)
    overlap_symbols = [symbol for symbol in our_symbols if symbol in true_symbol_set]
    our_returns = [
        return_map[symbol]["forward_return_pct"]
        for symbol in our_symbols
        if symbol in return_map
    ]
    true_returns = [row["forward_return_pct"] for row in true_top]
    true_return_sum = sum(max(0.0, ret) for ret in true_returns)
    captured_sum = sum(
        max(0.0, return_map[symbol]["forward_return_pct"])
        for symbol in overlap_symbols
        if symbol in return_map
    )
    return {
        "overlap_symbols": overlap_symbols,
        "overlap_count": len(overlap_symbols),
        "precision_at_k": round(len(overlap_symbols) / max(len(our_symbols), 1), 4),
        "recall_at_k": round(len(overlap_symbols) / max(len(true_top), 1), 4),
        "winner_capture_pct": round(captured_sum / true_return_sum, 4) if true_return_sum > 0 else 0.0,
        "our_avg_forward_return_pct": round(sum(our_returns) / len(our_returns), 4) if our_returns else 0.0,
        "true_avg_forward_return_pct": round(sum(true_returns) / len(true_returns), 4) if true_returns else 0.0,
        "best_true_symbol": true_symbols[0] if true_symbols else None,
        "best_true_return_pct": true_returns[0] if true_returns else None,
    }


def _classify_miss_reason(symbol: str, snapshot: dict[str, Any]) -> str:
    static_universe = set(snapshot.get("static_universe_symbols", []))
    top_k = int(snapshot.get("top_k", DEFAULT_TOP_K))
    candidate_ranks = {
        row.get("binance_symbol"): int(row.get("rank", 999999))
        for row in snapshot.get("top_candidates", [])
        if isinstance(row, dict) and row.get("binance_symbol")
    }
    if symbol not in static_universe:
        return "out_of_static_universe"
    if symbol in candidate_ranks and candidate_ranks[symbol] > top_k:
        return "ranked_below_cutoff"
    return "no_long_signal"


def _fetch_klines(
    symbol: str,
    start_ms: int,
    end_ms: int,
    interval: str = KLINE_INTERVAL,
) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode(
        {
            "symbol": symbol,
            "interval": interval,
            "startTime": int(start_ms),
            "endTime": int(end_ms),
            "limit": 1000,
        }
    )
    payload = _fetch_binance_json(f"/api/v3/klines?{params}")
    if not isinstance(payload, list):
        return []
    bars: list[dict[str, Any]] = []
    for row in payload:
        if not isinstance(row, list) or len(row) < 6:
            continue
        bars.append(
            {
                "open_time": int(row[0]),
                "open": _safe_float(row[1]),
                "high": _safe_float(row[2]),
                "low": _safe_float(row[3]),
                "close": _safe_float(row[4]),
                "volume": _safe_float(row[5]),
            }
        )
    return bars


def _compute_atr_from_bars(bars: list[dict[str, Any]], period: int = 14) -> float:
    if not bars:
        return 0.0
    if len(bars) == 1:
        return max(bars[0]["high"] - bars[0]["low"], bars[0]["close"] * 0.003)
    trs: list[float] = []
    prev_close = bars[0]["close"]
    for bar in bars[1: period + 1]:
        tr = max(
            bar["high"] - bar["low"],
            abs(bar["high"] - prev_close),
            abs(bar["low"] - prev_close),
        )
        trs.append(tr)
        prev_close = bar["close"]
    if not trs:
        trs.append(max(bars[0]["high"] - bars[0]["low"], bars[0]["close"] * 0.003))
    return max(sum(trs) / len(trs), bars[0]["close"] * 0.003)


def _simulate_long_arm(
    bars: list[dict[str, Any]],
    entry_price: float,
    start_index: int,
    atr: float,
    arm_index: int,
) -> dict[str, Any]:
    tp_mult, sl_mult = BANDIT_ARMS[arm_index]
    tp_price = entry_price + tp_mult * atr
    sl_price = entry_price - sl_mult * atr
    start_index = max(0, min(start_index, len(bars) - 1))

    outcome = "TIME_EXIT"
    exit_price = bars[-1]["close"]
    exit_index = len(bars) - 1

    for idx in range(start_index, len(bars)):
        bar = bars[idx]
        hit_sl = bar["low"] <= sl_price
        hit_tp = bar["high"] >= tp_price
        if hit_sl and hit_tp:
            outcome = "SL_HIT"
            exit_price = sl_price
            exit_index = idx
            break
        if hit_tp:
            outcome = "TP_HIT"
            exit_price = tp_price
            exit_index = idx
            break
        if hit_sl:
            outcome = "SL_HIT"
            exit_price = sl_price
            exit_index = idx
            break

    pnl_pct = ((exit_price - entry_price) / entry_price) * 100.0 if entry_price > 0 else 0.0
    return {
        "arm_index": arm_index,
        "tp_mult": tp_mult,
        "sl_mult": sl_mult,
        "take_profit": round(tp_price, 8),
        "stop_loss": round(sl_price, 8),
        "outcome": outcome,
        "realized_pnl_pct": round(pnl_pct, 4),
        "exit_bar_index": exit_index,
    }


def _best_arm_for_entry(
    bars: list[dict[str, Any]],
    entry_price: float,
    start_index: int,
    atr: float,
) -> dict[str, Any]:
    best: Optional[dict[str, Any]] = None
    outcome_priority = {"TP_HIT": 2, "TIME_EXIT": 1, "SL_HIT": 0}
    for arm_index in range(len(BANDIT_ARMS)):
        result = _simulate_long_arm(bars, entry_price, start_index, atr, arm_index)
        if best is None:
            best = result
            continue
        if result["realized_pnl_pct"] > best["realized_pnl_pct"]:
            best = result
        elif (
            result["realized_pnl_pct"] == best["realized_pnl_pct"]
            and outcome_priority[result["outcome"]] > outcome_priority[best["outcome"]]
        ):
            best = result
    return best or {}


def _analyze_long_path(
    bars: list[dict[str, Any]],
    snapshot_price: float,
    entry_window_ratio: float = ENTRY_WINDOW_RATIO,
) -> dict[str, Any]:
    if not bars:
        return {}

    baseline = snapshot_price if snapshot_price > 0 else bars[0]["open"]
    peak_index = max(range(len(bars)), key=lambda idx: bars[idx]["high"])
    best_pre_peak_index = min(range(peak_index + 1), key=lambda idx: bars[idx]["low"])
    entry_window_bars = max(1, math.ceil(len(bars) * entry_window_ratio))
    pullback_index = min(range(entry_window_bars), key=lambda idx: bars[idx]["low"])

    peak_price = bars[peak_index]["high"]
    best_pre_peak_price = bars[best_pre_peak_index]["low"]
    pullback_entry = bars[pullback_index]["low"]
    final_price = bars[-1]["close"]
    atr = _compute_atr_from_bars(bars)

    snapshot_arm = _best_arm_for_entry(bars, baseline, 0, atr)
    pullback_arm = _best_arm_for_entry(
        bars,
        pullback_entry,
        min(pullback_index + 1, len(bars) - 1),
        atr,
    )

    start_time = bars[0]["open_time"]
    return {
        "bars": len(bars),
        "interval": KLINE_INTERVAL,
        "atr_proxy": round(atr, 8),
        "snapshot_price": round(baseline, 8),
        "final_price": round(final_price, 8),
        "peak_price": round(peak_price, 8),
        "snapshot_to_peak_pct": round(((peak_price - baseline) / baseline) * 100.0, 4) if baseline > 0 else 0.0,
        "forward_return_pct": round(((final_price - baseline) / baseline) * 100.0, 4) if baseline > 0 else 0.0,
        "ideal_entry_price": round(best_pre_peak_price, 8),
        "early_pullback_entry_price": round(pullback_entry, 8),
        "entry_improvement_pct": round(((baseline - pullback_entry) / baseline) * 100.0, 4) if baseline > 0 else 0.0,
        "best_pre_peak_entry_pct": round(((baseline - best_pre_peak_price) / baseline) * 100.0, 4) if baseline > 0 else 0.0,
        "time_to_peak_min": round((bars[peak_index]["open_time"] - start_time) / 60000, 1),
        "time_to_pullback_min": round((bars[pullback_index]["open_time"] - start_time) / 60000, 1),
        "best_arm_from_snapshot": snapshot_arm,
        "best_arm_from_pullback": pullback_arm,
    }


def _build_our_pick_review(
    snapshot: dict[str, Any],
    return_map: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    review: list[dict[str, Any]] = []
    top_k = int(snapshot.get("top_k", DEFAULT_TOP_K))
    true_top_symbols = {row["symbol"] for row in _rank_true_top(return_map, top_k)}
    for row in snapshot.get("top_candidates", [])[:top_k]:
        symbol = row.get("binance_symbol")
        if not symbol:
            continue
        ret = return_map.get(symbol, {}).get("forward_return_pct")
        review.append(
            {
                "symbol": symbol,
                "rank": int(row.get("rank", 999999)),
                "score": round(_safe_float(row.get("score")), 4),
                "strategy": row.get("strategy", "unknown"),
                "forward_return_pct": round(_safe_float(ret), 4) if ret is not None else None,
                "was_true_top": symbol in true_top_symbols,
            }
        )
    return review


def _build_case_studies(
    snapshot: dict[str, Any],
    true_top: list[dict[str, Any]],
    evaluated_at: datetime,
) -> list[dict[str, Any]]:
    studies: list[dict[str, Any]] = []
    our_top_symbols = set(snapshot.get("selected_top_symbols", []))
    start_dt = _parse_dt(snapshot.get("created_at")) or evaluated_at
    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(evaluated_at.timestamp() * 1000)
    for row in true_top[:MAX_CASE_STUDIES]:
        symbol = row["symbol"]
        study = {
            "symbol": symbol,
            "forward_return_pct": row["forward_return_pct"],
            "snapshot_price": row["snapshot_price"],
            "current_price": row["current_price"],
            "quote_volume_snapshot": row["quote_volume_snapshot"],
            "change_24h_snapshot_pct": row["change_24h_snapshot_pct"],
            "was_in_our_top_k": symbol in our_top_symbols,
            "miss_reason": None if symbol in our_top_symbols else _classify_miss_reason(symbol, snapshot),
        }
        bars = _fetch_klines(symbol, start_ms=start_ms, end_ms=end_ms, interval=KLINE_INTERVAL)
        if bars:
            study["path_analysis"] = _analyze_long_path(bars, row["snapshot_price"])
        studies.append(study)
    return studies


def evaluate_snapshot(snapshot: dict[str, Any], evaluated_at: Optional[datetime] = None) -> dict[str, Any]:
    evaluated_at = evaluated_at or _utc_now()
    snapshot_universe = snapshot.get("universe_prices", {})
    snapshot_symbols = set(snapshot_universe.keys())
    current_universe = build_market_snapshot(
        forced_symbols=snapshot_symbols,
        static_symbols=set(snapshot.get("static_universe_symbols", [])),
        universe_size=max(len(snapshot_symbols), DEFAULT_UNIVERSE_SIZE),
        min_quote_volume=0.0,
    )
    if not current_universe:
        return {
            "snapshot_id": snapshot.get("snapshot_id"),
            "status": "no_current_market_snapshot",
            "evaluated_at": evaluated_at.isoformat(),
        }

    top_k = int(snapshot.get("top_k", DEFAULT_TOP_K))
    return_map = _compute_forward_returns(snapshot_universe, current_universe)
    true_top = _rank_true_top(return_map, top_k)
    our_symbols = [row["binance_symbol"] for row in snapshot.get("top_candidates", [])[:top_k]]
    metrics = _compute_overlap_metrics(our_symbols, true_top, return_map)

    misses = []
    miss_reason_counts: Counter[str] = Counter()
    for row in true_top:
        symbol = row["symbol"]
        if symbol in our_symbols:
            continue
        reason = _classify_miss_reason(symbol, snapshot)
        miss_reason_counts[reason] += 1
        misses.append(
            {
                "symbol": symbol,
                "forward_return_pct": row["forward_return_pct"],
                "reason": reason,
                "quote_volume_snapshot": row["quote_volume_snapshot"],
                "change_24h_snapshot_pct": row["change_24h_snapshot_pct"],
            }
        )

    created_at = _parse_dt(snapshot.get("created_at")) or evaluated_at
    return {
        "snapshot_id": snapshot.get("snapshot_id"),
        "snapshot_created_at": created_at.isoformat(),
        "evaluated_at": evaluated_at.isoformat(),
        "elapsed_minutes": round((evaluated_at - created_at).total_seconds() / 60.0, 1),
        "top_k": top_k,
        "candidate_count": int(snapshot.get("candidate_count", 0)),
        "universe_size": len(return_map),
        "our_top_symbols": our_symbols,
        "true_top_symbols": [row["symbol"] for row in true_top],
        "metrics": metrics,
        "our_pick_review": _build_our_pick_review(snapshot, return_map),
        "misses": misses,
        "miss_reason_counts": dict(miss_reason_counts),
        "true_top_case_studies": _build_case_studies(snapshot, true_top, evaluated_at),
    }


def _append_legacy_log(evaluation: dict[str, Any]) -> None:
    legacy = _read_json(LEGACY_LOG_PATH, [])
    if not isinstance(legacy, list):
        legacy = []
    metrics = evaluation.get("metrics", {})
    legacy.append(
        {
            "snapshot_id": evaluation.get("snapshot_id"),
            "snapshot_created_at": evaluation.get("snapshot_created_at"),
            "evaluated_at": evaluation.get("evaluated_at"),
            "elapsed_minutes": evaluation.get("elapsed_minutes"),
            "precision_at_k": metrics.get("precision_at_k"),
            "recall_at_k": metrics.get("recall_at_k"),
            "winner_capture_pct": metrics.get("winner_capture_pct"),
            "overlap_symbols": metrics.get("overlap_symbols", []),
            "best_true_symbol": metrics.get("best_true_symbol"),
            "best_true_return_pct": metrics.get("best_true_return_pct"),
            "miss_reason_counts": evaluation.get("miss_reason_counts", {}),
        }
    )
    legacy = legacy[-720:]
    _write_json(LEGACY_LOG_PATH, legacy)


def evaluate_due_snapshots(*, force: bool = False) -> list[dict[str, Any]]:
    _ensure_dirs()
    now = _utc_now()
    evaluations: list[dict[str, Any]] = []
    for path in sorted(SNAPSHOT_DIR.glob("*.json")):
        snapshot = _read_json(path, None)
        if not isinstance(snapshot, dict):
            continue
        snapshot_id = str(snapshot.get("snapshot_id", path.stem))
        created_at = _parse_dt(snapshot.get("created_at"))
        if created_at is None:
            continue
        due_ts = created_at.timestamp() + float(snapshot.get("horizon_hours", DEFAULT_HORIZON_HOURS)) * 3600.0
        if not force and now.timestamp() < due_ts:
            continue
        eval_path = _evaluation_path(snapshot_id)
        if eval_path.exists() and not force:
            continue
        evaluation = evaluate_snapshot(snapshot, evaluated_at=now)
        _write_json(eval_path, evaluation)
        _append_legacy_log(evaluation)
        evaluations.append(evaluation)
    return evaluations


def _most_common_arm_name(counter: Counter[str]) -> Optional[str]:
    if not counter:
        return None
    return counter.most_common(1)[0][0]


def _generate_recommendations(summary: dict[str, Any]) -> list[str]:
    recommendations: list[str] = []
    miss_counts = summary.get("miss_reason_counts", {})
    out_of_universe = int(miss_counts.get("out_of_static_universe", 0))
    ranked_below = int(miss_counts.get("ranked_below_cutoff", 0))
    no_signal = int(miss_counts.get("no_long_signal", 0))

    if out_of_universe > max(ranked_below, no_signal):
        recommendations.append(
            "Universe expansion is the biggest leak; promote liquid Binance movers into the live crypto list faster."
        )
    if ranked_below > 0:
        recommendations.append(
            "Ranking is leaking winners; add a momentum/liquidity promotion layer for symbols already in-universe but below the cutoff."
        )
    median_entry_improvement = summary.get("entry_learning", {}).get("median_entry_improvement_pct")
    if median_entry_improvement is not None and median_entry_improvement >= 0.5:
        recommendations.append(
            f"Stage pullback entries inside the first {int(ENTRY_WINDOW_RATIO * 100)}% of the hour; median entry improvement is {median_entry_improvement:.2f}%."
        )
    best_pullback_arm = summary.get("entry_learning", {}).get("most_common_best_pullback_arm")
    if best_pullback_arm:
        recommendations.append(
            f"The most common winning exit template from pullback entries is bandit arm {best_pullback_arm}; bias TP/SL exploration toward it."
        )
    return recommendations


def rebuild_summary() -> dict[str, Any]:
    _ensure_dirs()
    evaluations = []
    for path in sorted(EVALUATION_DIR.glob("*.json")):
        evaluation = _read_json(path, None)
        if isinstance(evaluation, dict) and evaluation.get("metrics"):
            evaluations.append(evaluation)

    if not evaluations:
        summary = {
            "updated_at": _utc_now().isoformat(),
            "evaluated_snapshots": 0,
            "metrics": {},
            "miss_reason_counts": {},
            "entry_learning": {},
            "most_missed_symbols": {},
            "recommendations": [],
        }
        _write_json(SUMMARY_PATH, summary)
        return summary

    precisions = []
    recalls = []
    captures = []
    our_avg_returns = []
    true_avg_returns = []
    miss_counts: Counter[str] = Counter()
    missed_symbols: Counter[str] = Counter()
    entry_improvements: list[float] = []
    peak_moves: list[float] = []
    snapshot_arm_counter: Counter[str] = Counter()
    pullback_arm_counter: Counter[str] = Counter()

    for evaluation in evaluations:
        metrics = evaluation.get("metrics", {})
        precisions.append(_safe_float(metrics.get("precision_at_k")))
        recalls.append(_safe_float(metrics.get("recall_at_k")))
        captures.append(_safe_float(metrics.get("winner_capture_pct")))
        our_avg_returns.append(_safe_float(metrics.get("our_avg_forward_return_pct")))
        true_avg_returns.append(_safe_float(metrics.get("true_avg_forward_return_pct")))

        for reason, count in evaluation.get("miss_reason_counts", {}).items():
            miss_counts[reason] += int(count)

        for miss in evaluation.get("misses", []):
            symbol = str(miss.get("symbol", ""))
            if symbol:
                missed_symbols[symbol] += 1

        for case in evaluation.get("true_top_case_studies", []):
            path = case.get("path_analysis", {})
            if not isinstance(path, dict):
                continue
            if path.get("entry_improvement_pct") is not None:
                entry_improvements.append(_safe_float(path.get("entry_improvement_pct")))
            if path.get("snapshot_to_peak_pct") is not None:
                peak_moves.append(_safe_float(path.get("snapshot_to_peak_pct")))
            snap_arm = path.get("best_arm_from_snapshot", {})
            pull_arm = path.get("best_arm_from_pullback", {})
            if snap_arm:
                snapshot_arm_counter[f"{snap_arm.get('tp_mult')}x/{snap_arm.get('sl_mult')}x"] += 1
            if pull_arm:
                pullback_arm_counter[f"{pull_arm.get('tp_mult')}x/{pull_arm.get('sl_mult')}x"] += 1

    summary = {
        "updated_at": _utc_now().isoformat(),
        "evaluated_snapshots": len(evaluations),
        "metrics": {
            "avg_precision_at_k": round(statistics.mean(precisions), 4) if precisions else 0.0,
            "avg_recall_at_k": round(statistics.mean(recalls), 4) if recalls else 0.0,
            "avg_winner_capture_pct": round(statistics.mean(captures), 4) if captures else 0.0,
            "avg_our_top_return_pct": round(statistics.mean(our_avg_returns), 4) if our_avg_returns else 0.0,
            "avg_true_top_return_pct": round(statistics.mean(true_avg_returns), 4) if true_avg_returns else 0.0,
        },
        "miss_reason_counts": dict(miss_counts),
        "most_missed_symbols": dict(missed_symbols.most_common(10)),
        "entry_learning": {
            "median_entry_improvement_pct": round(statistics.median(entry_improvements), 4) if entry_improvements else None,
            "median_snapshot_to_peak_pct": round(statistics.median(peak_moves), 4) if peak_moves else None,
            "most_common_best_snapshot_arm": _most_common_arm_name(snapshot_arm_counter),
            "most_common_best_pullback_arm": _most_common_arm_name(pullback_arm_counter),
        },
    }
    summary["recommendations"] = _generate_recommendations(summary)
    _write_json(SUMMARY_PATH, summary)
    return summary


def run_hourly_check(*, force: bool = False) -> dict[str, Any]:
    _ensure_dirs()
    state = _load_state()
    snapshot_result = create_snapshot(force=force)
    evaluations = evaluate_due_snapshots(force=force)
    summary = rebuild_summary()
    state["last_run_at"] = _utc_now().isoformat()
    _save_state(state)
    return {
        "snapshot": snapshot_result,
        "evaluations_written": len(evaluations),
        "summary": summary,
    }


def run_cycle() -> dict[str, Any]:
    """Compatibility shim for old manual usage."""
    return run_hourly_check(force=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="ALPHA_ENGINE hindsight learner")
    parser.add_argument("--force", action="store_true", help="Ignore cooldown and evaluate everything now")
    parser.add_argument("--snapshot-only", action="store_true", help="Only write a new snapshot")
    parser.add_argument("--evaluate-only", action="store_true", help="Only evaluate due snapshots")
    parser.add_argument("--summary-only", action="store_true", help="Only rebuild summary")
    args = parser.parse_args()

    if args.summary_only:
        print(json.dumps(rebuild_summary(), indent=2))
        return
    if args.snapshot_only:
        print(json.dumps(create_snapshot(force=args.force), indent=2))
        return
    if args.evaluate_only:
        evaluations = evaluate_due_snapshots(force=args.force)
        print(json.dumps({"evaluations_written": len(evaluations)}, indent=2))
        return
    print(json.dumps(run_hourly_check(force=args.force), indent=2))


if __name__ == "__main__":
    main()
