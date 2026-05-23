#!/usr/bin/env python3
"""
Continuous Improvement Monitor
==============================

Reference style: hedge-fund risk desk plus SRE observability.

This module sits above the existing alpha_engine, copy_trader_intel,
and paper_trading subsystems. It consolidates open-position health,
realized performance, regime context, and benchmark lag into one
reporting loop without disabling strategies. Underperformers are routed
toward inverse or mutation workflows instead.

Usage:
    python alpha_engine/continuous_improvement_monitor.py
    python -m alpha_engine.continuous_improvement_monitor
    python -m alpha_engine.continuous_improvement_monitor --loop --interval-seconds 1200
    python -m alpha_engine.continuous_improvement_monitor --loop --interval-seconds 30
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
ALPHA_DIR = Path(__file__).resolve().parent
DATA_DIR = ALPHA_DIR / "data"

CONFIG_PATH = DATA_DIR / "continuous_improvement_config.json"
REPORT_PATH = DATA_DIR / "continuous_improvement_report.json"
REPORT_MD_PATH = DATA_DIR / "continuous_improvement_report.md"
HISTORY_PATH = DATA_DIR / "continuous_improvement_history.json"

PEER_INPUTS = {
    "alpha_engine": ROOT / "alpha_engine" / "data" / "active_picks.json",
    "copy_trader_intel": ROOT / "copy_trader_intel" / "data" / "active_picks.json",
    "paper_trading": ROOT / "paper_trading" / "data" / "active_picks.json",
}

PEER_STATUS_FILES = {
    "alpha_engine": ROOT / "alpha_engine" / "data" / "performance_snapshot.json",
    "copy_trader_intel": ROOT / "copy_trader_intel" / "data" / "portfolio_tracker.json",
    "paper_trading": ROOT / "paper_trading" / "data" / "performance.json",
}

BINANCE_BASES = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://data-api.binance.vision",
    "https://api.binance.us",
]

SAFE_ACTIONS = {
    "refresh_pick_quality": [sys.executable, str(ROOT / "alpha_engine" / "pick_quality_monitor.py")],
    "refresh_portfolio_monitor": [sys.executable, str(ROOT / "alpha_engine" / "portfolio_monitor.py")],
    "refresh_kpis": [sys.executable, str(ROOT / "alpha_engine" / "kpi_monitor.py")],
}

MUTATION_ACTIONS = {
    "alpha_mutation_scan": [sys.executable, str(ROOT / "alpha_engine" / "mutation_forward_scanner.py")],
    "kimi_inverse_scan": [sys.executable, str(ROOT / "alpha_engine" / "kimi_inverse_scanner.py")],
    "copytrader_mutation_extract": [sys.executable, str(ROOT / "copy_trader_intel" / "copytrader_lesson_extractor.py")],
}


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now_utc().isoformat()


def _safe_float(value: Any, default: float | None = None) -> float | None:
    if value is None:
        return default
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(parsed) or math.isinf(parsed):
        return default
    return parsed


def _safe_int(value: Any, default: int = 0) -> int:
    parsed = _safe_float(value)
    if parsed is None:
        return default
    return int(parsed)


def _sanitize(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {key: _sanitize(val) for key, val in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(val) for val in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj


def _load_json(path: Path, default: Any = None) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(_sanitize(payload), handle, indent=2, ensure_ascii=False)


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    for fmt in (None, "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            if fmt is None:
                return datetime.fromisoformat(text)
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _minutes_since(dt_value: datetime | None) -> float | None:
    if dt_value is None:
        return None
    if dt_value.tzinfo is None:
        dt_value = dt_value.replace(tzinfo=timezone.utc)
    return round((_now_utc() - dt_value).total_seconds() / 60.0, 2)


def _normalize_win_rate(value: Any) -> float | None:
    parsed = _safe_float(value)
    if parsed is None:
        return None
    if parsed <= 1.0:
        return round(parsed * 100.0, 2)
    return round(parsed, 2)


def _normalize_percent(value: Any) -> float | None:
    parsed = _safe_float(value)
    if parsed is None:
        return None
    if abs(parsed) <= 5.0:
        return round(parsed * 100.0, 4)
    return round(parsed, 4)


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    return round(statistics.median(values), 4)


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    defaults = {
        "history_limit": 720,
        "peer_stale_minutes": 45,
        "price_coverage_floor_pct": 80.0,
        "portfolio_drawdown_limit_pct": 8.0,
        "open_position_drawdown_limit_pct": 5.0,
        "directional_correctness_floor_pct": 45.0,
        "confidence_inversion_gap_pct": 10.0,
        "strategy_min_closed_trades": 5,
        "strategy_win_rate_floor_pct": 42.0,
        "strategy_profit_factor_floor": 1.0,
        "strategy_sharpe_floor": 0.5,
        "benchmark_alpha_floor_pct": 0.0,
        "regime_change_pnl_drop_pct": 1.5,
        "micro_cycle_seconds": 30,
        "full_cycle_seconds": 1200,
    }
    payload = _load_json(path, {}) or {}
    defaults.update(payload)
    return defaults


def classify_asset(symbol: str, category_hint: str = "", portfolio_type: str = "") -> str:
    sym = (symbol or "").upper().strip()
    category = (category_hint or "").lower()
    portfolio_type = (portfolio_type or "").lower()

    if category in {"forex", "fx"} or sym.endswith("=X"):
        return "forex"
    if category in {"commodity", "commodities"}:
        return "commodities"
    if sym.endswith("=F") or sym in {"GC=F", "SI=F", "HG=F", "ZC=F", "ZW=F", "ZS=F"}:
        return "commodities"
    if category in {"equity", "stock", "stocks", "etf"}:
        return "equities"
    if portfolio_type in {"macro", "technical", "verified", "correlation", "leap"} and not sym.endswith("USDT"):
        return "equities"
    if (
        category in {"crypto", "meme", "penny", "derivatives"}
        or sym.endswith("USDT")
        or sym.endswith("-USD")
        or sym.endswith("USD") and "=" not in sym and len(sym) <= 12
    ):
        return "crypto"
    return "equities"


def classify_monitor_bucket(raw_pick: dict[str, Any], asset_class: str) -> str:
    portfolio_type = (raw_pick.get("portfolio_type") or "").lower()
    source = (raw_pick.get("source") or "").lower()
    position_sizing = (raw_pick.get("position_sizing") or "").lower()
    category = (raw_pick.get("category") or "").lower()
    derivative_sources = {"hyperliquid", "bybit", "bitget", "bingx", "okx", "gmx", "dydx", "drift"}
    if (
        portfolio_type == "derivatives"
        or category == "derivatives"
        or position_sizing == "copy_trader"
        or _safe_float(raw_pick.get("max_safe_leverage")) is not None
        or source in derivative_sources
    ):
        return "derivatives"
    return asset_class


def normalize_direction(value: Any) -> str:
    text = str(value or "").upper().strip()
    if text in {"BUY", "LONG"}:
        return "LONG"
    if text in {"SELL", "SHORT"}:
        return "SHORT"
    return "LONG"


def confidence_bucket(confidence: float | None) -> str:
    if confidence is None:
        return "UNKNOWN"
    if confidence >= 0.80:
        return "HIGH"
    if confidence >= 0.65:
        return "MEDIUM"
    return "LOW"


def normalize_pick(raw_pick: dict[str, Any], peer_name: str) -> dict[str, Any] | None:
    symbol = str(raw_pick.get("symbol") or "").strip()
    entry_price = _safe_float(
        raw_pick.get("entry_price")
        or raw_pick.get("entryPrice")
        or raw_pick.get("original_trader_entry")
    )
    if not symbol or entry_price in (None, 0.0):
        return None

    current_price = _safe_float(raw_pick.get("current_price") or raw_pick.get("price") or raw_pick.get("exit_price"))
    confidence = _safe_float(
        raw_pick.get("confidence")
        or raw_pick.get("ml_score")
        or raw_pick.get("signalProbability")
    )
    if confidence is not None and confidence > 1.0:
        confidence = confidence / 100.0

    direction = normalize_direction(
        raw_pick.get("direction")
        or raw_pick.get("signal_type")
        or raw_pick.get("signal")
    )

    portfolio_type = str(raw_pick.get("portfolio_type") or "")
    category = str(raw_pick.get("category") or "")
    asset_class = classify_asset(symbol, category, portfolio_type)
    monitor_bucket = classify_monitor_bucket(raw_pick, asset_class)
    take_profit = _safe_float(
        raw_pick.get("take_profit")
        or raw_pick.get("tp")
        or raw_pick.get("targetPrice")
        or raw_pick.get("grossTargetPrice")
    )
    stop_loss = _safe_float(raw_pick.get("stop_loss") or raw_pick.get("sl") or raw_pick.get("stopPrice"))

    return {
        "id": raw_pick.get("id") or f"{peer_name}:{symbol}:{raw_pick.get('strategy')}",
        "peer": peer_name,
        "symbol": symbol,
        "strategy": raw_pick.get("strategy")
        or raw_pick.get("strategy_name")
        or raw_pick.get("algorithm")
        or raw_pick.get("display_name")
        or "unknown",
        "source_system": raw_pick.get("source_system") or raw_pick.get("system_name") or peer_name,
        "source": raw_pick.get("source") or peer_name,
        "asset_class": asset_class,
        "monitor_bucket": monitor_bucket,
        "portfolio_type": portfolio_type or None,
        "direction": direction,
        "entry_price": entry_price,
        "current_price": current_price,
        "take_profit": take_profit,
        "stop_loss": stop_loss,
        "confidence": confidence,
        "confidence_bucket": confidence_bucket(confidence),
        "allocation_usd": _safe_float(raw_pick.get("allocation") or raw_pick.get("position_size_usd"), 0.0),
        "timestamp": raw_pick.get("timestamp")
        or raw_pick.get("entry_date")
        or raw_pick.get("entryDate")
        or raw_pick.get("detected_at"),
        "status": raw_pick.get("status") or "OPEN",
        "unrealized_pnl_pct": _safe_float(raw_pick.get("pnl_pct")),
        "high_water_mark": _safe_float(raw_pick.get("high_water_mark")),
        "reason": raw_pick.get("reason"),
        "max_safe_leverage": _safe_float(raw_pick.get("max_safe_leverage")),
    }


def load_open_picks() -> list[dict[str, Any]]:
    picks: list[dict[str, Any]] = []
    for peer_name, path in PEER_INPUTS.items():
        payload = _load_json(path, [])
        if isinstance(payload, list):
            entries = payload
        elif isinstance(payload, dict):
            entries = payload.get("activePicks") or payload.get("active") or payload.get("picks") or []
        else:
            entries = []
        for raw_pick in entries:
            if isinstance(raw_pick, dict):
                normalized = normalize_pick(raw_pick, peer_name)
                if normalized is not None:
                    picks.append(normalized)
    return picks


def symbol_to_binance(symbol: str) -> str | None:
    sym = symbol.upper().strip()
    # Skip non-ASCII symbols (prevents UnicodeEncodeError in HTTP request)
    if not sym.isascii():
        return None
    if sym.endswith("USDT"):
        return sym
    if sym.endswith("-USD"):
        return sym.replace("-USD", "USDT")
    if sym.endswith("USD") and "=" not in sym and len(sym) <= 12:
        return f"{sym}T"
    return None


def fetch_binance_price(symbol: str) -> float | None:
    # Guard: reject non-ASCII to prevent http.client encode crash
    if not symbol.isascii():
        return None
    for base in BINANCE_BASES:
        try:
            req = urllib.request.Request(
                f"{base}/api/v3/ticker/price?symbol={symbol}",
                headers={"User-Agent": "ContinuousImprovementMonitor/1.0"},
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return _safe_float(payload.get("price"))
        except urllib.error.HTTPError as exc:
            if exc.code in {403, 451}:
                continue
            return None
        except (urllib.error.URLError, OSError, json.JSONDecodeError, TimeoutError):
            continue
    return None


def enrich_prices(picks: list[dict[str, Any]]) -> dict[str, Any]:
    stock_forex_prices = (_load_json(DATA_DIR / "stock_forex_prices.json", {}) or {}).get("prices", {})
    priced = 0
    missing_symbols: list[str] = []

    for pick in picks:
        if _safe_float(pick.get("current_price")) not in (None, 0.0):
            priced += 1
            continue

        symbol = pick["symbol"]
        current_price: float | None = None
        if str(pick.get("asset_class", "")).upper() == "CRYPTO" or pick.get("monitor_bucket") == "derivatives":
            binance_symbol = symbol_to_binance(symbol)
            if binance_symbol:
                current_price = fetch_binance_price(binance_symbol)
        if current_price is None:
            current_price = _safe_float(stock_forex_prices.get(symbol))

        if current_price is not None:
            pick["current_price"] = current_price
            priced += 1
        else:
            missing_symbols.append(symbol)

    coverage = round((priced / len(picks) * 100.0), 2) if picks else 100.0
    return {
        "priced_positions": priced,
        "total_positions": len(picks),
        "coverage_pct": coverage,
        "missing_symbols": sorted(set(missing_symbols)),
    }


def compute_pnl_pct(entry_price: float | None, current_price: float | None, direction: str) -> float | None:
    if entry_price in (None, 0.0) or current_price in (None, 0.0):
        return None
    if direction == "SHORT":
        return round(((entry_price - current_price) / entry_price) * 100.0, 4)
    return round(((current_price - entry_price) / entry_price) * 100.0, 4)


def distance_to_level_pct(current_price: float | None, level: float | None, direction: str, target: str) -> float | None:
    if current_price in (None, 0.0) or level in (None, 0.0):
        return None
    if target == "tp":
        if direction == "SHORT":
            return round(((current_price - level) / current_price) * 100.0, 4)
        return round(((level - current_price) / current_price) * 100.0, 4)
    if direction == "SHORT":
        return round(((level - current_price) / current_price) * 100.0, 4)
    return round(((current_price - level) / current_price) * 100.0, 4)


def annotate_open_positions(picks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for pick in picks:
        pnl_pct = compute_pnl_pct(pick.get("entry_price"), pick.get("current_price"), pick["direction"])
        if pnl_pct is None:
            pnl_pct = pick.get("unrealized_pnl_pct")
        pick["current_pnl_pct"] = _normalize_percent(pnl_pct)
        pick["directionally_correct"] = pick["current_pnl_pct"] is not None and pick["current_pnl_pct"] > 0
        pick["distance_to_tp_pct"] = distance_to_level_pct(
            pick.get("current_price"), pick.get("take_profit"), pick["direction"], "tp"
        )
        pick["distance_to_sl_pct"] = distance_to_level_pct(
            pick.get("current_price"), pick.get("stop_loss"), pick["direction"], "sl"
        )
        high_water_mark = _safe_float(pick.get("high_water_mark"))
        if high_water_mark not in (None, 0.0) and pick.get("current_price") not in (None, 0.0):
            if pick["direction"] == "SHORT":
                pick["drawdown_from_peak_pct"] = round(
                    ((pick["current_price"] - high_water_mark) / high_water_mark) * 100.0,
                    4,
                )
            else:
                pick["drawdown_from_peak_pct"] = round(
                    ((high_water_mark - pick["current_price"]) / high_water_mark) * 100.0,
                    4,
                )
        else:
            pick["drawdown_from_peak_pct"] = None
    return picks


def aggregate_positions(picks: list[dict[str, Any]], key_name: str) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pick in picks:
        key = str(pick.get(key_name) or "UNKNOWN")
        grouped[key].append(pick)

    result: dict[str, dict[str, Any]] = {}
    for key, bucket in sorted(grouped.items()):
        pnls = [pick["current_pnl_pct"] for pick in bucket if pick.get("current_pnl_pct") is not None]
        correct = [pick for pick in bucket if pick.get("current_pnl_pct") is not None]
        winners = sum(1 for pick in correct if pick["current_pnl_pct"] > 0)
        distances_to_tp = [pick["distance_to_tp_pct"] for pick in bucket if pick.get("distance_to_tp_pct") is not None]
        distances_to_sl = [pick["distance_to_sl_pct"] for pick in bucket if pick.get("distance_to_sl_pct") is not None]
        confidences = [pick["confidence"] for pick in bucket if pick.get("confidence") is not None]
        result[key] = {
            "count": len(bucket),
            "priced_count": len(pnls),
            "gross_allocation_usd": round(
                sum(_safe_float(pick.get("allocation_usd"), 0.0) or 0.0 for pick in bucket),
                2,
            ),
            "avg_pnl_pct": round(statistics.mean(pnls), 4) if pnls else None,
            "median_pnl_pct": _median(pnls),
            "best_pnl_pct": round(max(pnls), 4) if pnls else None,
            "worst_pnl_pct": round(min(pnls), 4) if pnls else None,
            "directional_correctness_pct": round((winners / len(correct) * 100.0), 2) if correct else None,
            "avg_confidence": round(statistics.mean(confidences), 4) if confidences else None,
            "avg_distance_to_tp_pct": round(statistics.mean(distances_to_tp), 4) if distances_to_tp else None,
            "avg_distance_to_sl_pct": round(statistics.mean(distances_to_sl), 4) if distances_to_sl else None,
            "long_count": sum(1 for pick in bucket if pick["direction"] == "LONG"),
            "short_count": sum(1 for pick in bucket if pick["direction"] == "SHORT"),
            "top_symbols": [symbol for symbol, _ in Counter(pick["symbol"] for pick in bucket).most_common(5)],
        }
    return result


def build_peer_consensus(picks: list[dict[str, Any]]) -> dict[str, Any]:
    symbol_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pick in picks:
        symbol_map[pick["symbol"]].append(pick)

    conflicts: list[dict[str, Any]] = []
    aligned: list[dict[str, Any]] = []
    for symbol, entries in symbol_map.items():
        peers = sorted({entry["peer"] for entry in entries})
        if len(peers) < 2:
            continue
        directions = Counter(entry["direction"] for entry in entries)
        detail = {
            "symbol": symbol,
            "peers": peers,
            "direction_counts": dict(directions),
            "strategies": sorted({str(entry["strategy"]) for entry in entries})[:6],
        }
        if len(directions) > 1:
            conflicts.append(detail)
        else:
            detail["consensus_direction"] = next(iter(directions))
            aligned.append(detail)

    conflicts.sort(key=lambda item: sum(item["direction_counts"].values()), reverse=True)
    aligned.sort(key=lambda item: len(item["peers"]), reverse=True)
    return {
        "conflicts": conflicts[:10],
        "aligned": aligned[:10],
        "conflict_count": len(conflicts),
        "aligned_count": len(aligned),
    }


def load_peer_status() -> dict[str, Any]:
    status: dict[str, Any] = {}
    for peer_name, path in PEER_STATUS_FILES.items():
        payload = _load_json(path, {}) or {}
        file_dt = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc) if path.exists() else None
        embedded_dt = None
        if isinstance(payload, dict):
            for candidate in ("timestamp", "updated_at", "generated_at", "last_updated"):
                embedded_dt = _parse_timestamp(payload.get(candidate))
                if embedded_dt is not None:
                    break
        best_dt = embedded_dt or file_dt
        status[peer_name] = {
            "path": str(path),
            "exists": path.exists(),
            "last_updated": best_dt.isoformat() if best_dt else None,
            "age_minutes": _minutes_since(best_dt),
        }
    return status


def load_alpha_summary() -> dict[str, Any]:
    snapshot = _load_json(DATA_DIR / "performance_snapshot.json", {}) or {}
    summary = snapshot.get("summary", {}) if isinstance(snapshot, dict) else {}
    strategy_actions = snapshot.get("strategy_actions", {}) if isinstance(snapshot, dict) else {}
    return {
        "summary": summary,
        "disabled_count": snapshot.get("disabled_count"),
        "boosted_count": snapshot.get("boosted_count"),
        "strategy_actions_sample": dict(list(strategy_actions.items())[:10]),
    }


def load_strategy_metrics() -> dict[str, Any]:
    payload = _load_json(DATA_DIR / "strategy_performance.json", {}) or {}
    if not isinstance(payload, dict):
        return {}
    return payload


def load_regime_context() -> dict[str, Any]:
    regime = _load_json(DATA_DIR / "regime_report.json", {}) or {}
    risk = _load_json(DATA_DIR / "risk_metrics.json", {}) or {}
    return {"regime": regime, "risk": risk}


def load_paper_trading_summary() -> dict[str, Any]:
    payload = _load_json(ROOT / "paper_trading" / "data" / "performance.json", {}) or {}
    portfolios = payload.get("portfolios", []) if isinstance(payload, dict) else []
    return {
        "updated_at": payload.get("updated_at"),
        "portfolios": portfolios,
        "worst_drawdown_pct": round(
            max((_safe_float(p.get("max_drawdown"), 0.0) or 0.0) for p in portfolios),
            2,
        ) if portfolios else None,
        "worst_portfolio": next(
            (
                p["name"]
                for p in sorted(
                    portfolios,
                    key=lambda item: _safe_float(item.get("max_drawdown"), 0.0) or 0.0,
                    reverse=True,
                )
            ),
            None,
        ),
    }


def load_copytrader_summary() -> dict[str, Any]:
    payload = _load_json(ROOT / "copy_trader_intel" / "data" / "portfolio_tracker.json", {}) or {}
    portfolios = payload.get("portfolios", {}) if isinstance(payload, dict) else {}
    open_trades = sum(_safe_int(item.get("open_trades")) for item in portfolios.values())
    avg_wr = None
    if portfolios:
        win_rates = [_normalize_win_rate(item.get("win_rate")) for item in portfolios.values()]
        win_rates = [value for value in win_rates if value is not None]
        avg_wr = round(statistics.mean(win_rates), 2) if win_rates else None
    return {
        "generated_at": payload.get("generated_at"),
        "portfolio_count": len(portfolios),
        "open_trades": open_trades,
        "avg_portfolio_win_rate_pct": avg_wr,
    }


def load_benchmark_context(skip_live_benchmark: bool = False) -> dict[str, Any]:
    existing = _load_json(DATA_DIR / "performance_benchmarks.json", {})
    if isinstance(existing, dict) and existing:
        benchmark = existing.get("btc_benchmark", existing)
        if isinstance(benchmark, dict):
            return benchmark

    if skip_live_benchmark:
        return {"error": "Live benchmark skipped", "alpha_generated_pct": None}

    try:
        if str(ALPHA_DIR) not in sys.path:
            sys.path.insert(0, str(ALPHA_DIR))
        import performance_benchmarks  # type: ignore

        return performance_benchmarks.btc_benchmark()
    except Exception as exc:  # pragma: no cover
        return {"error": str(exc), "alpha_generated_pct": None}


def choose_mutation_action(peer_name: str, strategy_name: str) -> str:
    strategy_name = (strategy_name or "").lower()
    if peer_name == "copy_trader_intel" or strategy_name.startswith("copy_"):
        return "copytrader_mutation_extract"
    if "kimi" in strategy_name or strategy_name.startswith("inverse_"):
        return "kimi_inverse_scan"
    return "alpha_mutation_scan"


def build_strategy_watchlist(
    picks: list[dict[str, Any]],
    strategy_metrics: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    active_counts = Counter(str(pick["strategy"]) for pick in picks)
    peer_by_strategy: dict[str, str] = {}
    for pick in picks:
        peer_by_strategy.setdefault(str(pick["strategy"]), pick["peer"])

    underperformers: list[dict[str, Any]] = []
    outperformers: list[dict[str, Any]] = []

    min_closed = _safe_int(config["strategy_min_closed_trades"], 5)
    wr_floor = _safe_float(config["strategy_win_rate_floor_pct"], 42.0) or 42.0
    pf_floor = _safe_float(config["strategy_profit_factor_floor"], 1.0) or 1.0
    sharpe_floor = _safe_float(config["strategy_sharpe_floor"], 0.5) or 0.5

    for strategy_name, open_count in active_counts.items():
        realized = strategy_metrics.get(strategy_name)
        if not isinstance(realized, dict):
            continue

        closed_picks = _safe_int(realized.get("closed_picks"))
        if closed_picks < min_closed:
            continue

        win_rate_pct = _normalize_win_rate(realized.get("win_rate"))
        profit_factor = _safe_float(realized.get("profit_factor"))
        sharpe = _safe_float(realized.get("sharpe"))
        max_drawdown_pct = _normalize_percent(realized.get("max_drawdown"))
        summary = {
            "strategy": strategy_name,
            "peer": peer_by_strategy.get(strategy_name, "alpha_engine"),
            "open_positions": open_count,
            "closed_picks": closed_picks,
            "win_rate_pct": win_rate_pct,
            "profit_factor": round(profit_factor, 4) if profit_factor is not None else None,
            "sharpe": round(sharpe, 4) if sharpe is not None else None,
            "max_drawdown_pct": max_drawdown_pct,
            "mutation_action": choose_mutation_action(peer_by_strategy.get(strategy_name, "alpha_engine"), strategy_name),
        }

        if (
            (win_rate_pct is not None and win_rate_pct < wr_floor)
            or (profit_factor is not None and profit_factor < pf_floor)
            or (sharpe is not None and sharpe < sharpe_floor)
        ):
            underperformers.append(summary)
        elif (
            (win_rate_pct is not None and win_rate_pct >= max(wr_floor, 55.0))
            and (profit_factor is not None and profit_factor >= 1.2)
            and (sharpe is not None and sharpe >= max(sharpe_floor, 1.0))
        ):
            outperformers.append(summary)

    underperformers.sort(
        key=lambda item: (
            item["sharpe"] if item["sharpe"] is not None else 9999.0,
            item["win_rate_pct"] if item["win_rate_pct"] is not None else 9999.0,
        )
    )
    outperformers.sort(
        key=lambda item: (
            -(item["sharpe"] if item["sharpe"] is not None else -9999.0),
            -(item["profit_factor"] if item["profit_factor"] is not None else -9999.0),
        )
    )

    return {
        "rehabilitation_candidates": underperformers[:10],
        "leaders": outperformers[:10],
    }


def load_history() -> list[dict[str, Any]]:
    payload = _load_json(HISTORY_PATH, [])
    if isinstance(payload, list):
        return payload
    return []


def generate_alerts(
    sections: dict[str, Any],
    previous_snapshot: dict[str, Any] | None,
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []

    peer_stale_limit = _safe_float(config["peer_stale_minutes"], 45.0) or 45.0
    for peer_name, peer_status in sections["peer_status"].items():
        age = _safe_float(peer_status.get("age_minutes"))
        if age is not None and age > peer_stale_limit:
            alerts.append({
                "severity": "HIGH",
                "code": "PEER_STALE",
                "summary": f"{peer_name} data is stale ({age:.1f}m old)",
                "details": {"peer": peer_name, "age_minutes": age},
            })

    coverage_pct = _safe_float(sections["price_status"].get("coverage_pct"), 100.0) or 100.0
    if coverage_pct < (_safe_float(config["price_coverage_floor_pct"], 80.0) or 80.0):
        alerts.append({
            "severity": "HIGH",
            "code": "PRICE_COVERAGE_GAP",
            "summary": f"Price coverage dropped to {coverage_pct:.1f}%",
            "details": {"missing_symbols": sections["price_status"].get("missing_symbols", [])[:10]},
        })

    alpha_win_rate = _normalize_win_rate(sections["alpha_summary"]["summary"].get("win_rate"))
    win_rate_floor = _safe_float(config["directional_correctness_floor_pct"], 45.0) or 45.0
    if alpha_win_rate is not None and alpha_win_rate < win_rate_floor:
        alerts.append({
            "severity": "HIGH",
            "code": "REALIZED_WIN_RATE_BREACH",
            "summary": f"Alpha engine realized win rate is {alpha_win_rate:.1f}%",
            "details": {"win_rate_pct": alpha_win_rate},
        })

    worst_drawdown = _safe_float(sections["paper_trading"].get("worst_drawdown_pct"))
    dd_limit = _safe_float(config["portfolio_drawdown_limit_pct"], 8.0) or 8.0
    if worst_drawdown is not None and worst_drawdown > dd_limit:
        alerts.append({
            "severity": "CRITICAL",
            "code": "PORTFOLIO_DRAWDOWN_BREACH",
            "summary": (
                f"Paper portfolio {sections['paper_trading'].get('worst_portfolio')} "
                f"hit {worst_drawdown:.2f}% drawdown"
            ),
            "details": {"drawdown_pct": worst_drawdown},
        })

    confidence_metrics = sections["by_confidence"]
    high_conf = confidence_metrics.get("HIGH", {})
    low_conf = confidence_metrics.get("LOW", {})
    high_correct = _safe_float(high_conf.get("directional_correctness_pct"))
    low_correct = _safe_float(low_conf.get("directional_correctness_pct"))
    inversion_gap = _safe_float(config["confidence_inversion_gap_pct"], 10.0) or 10.0
    if high_correct is not None and low_correct is not None and (high_correct + inversion_gap) < low_correct:
        alerts.append({
            "severity": "HIGH",
            "code": "CONFIDENCE_INVERSION",
            "summary": (
                f"High-confidence picks are underperforming low-confidence picks "
                f"({high_correct:.1f}% vs {low_correct:.1f}%)"
            ),
            "details": {"high_conf_pct": high_correct, "low_conf_pct": low_correct},
        })

    benchmark_alpha = _safe_float(sections["benchmark"].get("alpha_generated_pct"))
    benchmark_floor = _safe_float(config["benchmark_alpha_floor_pct"], 0.0) or 0.0
    if benchmark_alpha is not None and benchmark_alpha < benchmark_floor:
        alerts.append({
            "severity": "HIGH",
            "code": "BENCHMARK_LAG",
            "summary": f"System alpha vs BTC benchmark is {benchmark_alpha:.2f}%",
            "details": sections["benchmark"],
        })

    if sections["peer_consensus"].get("conflict_count", 0) > 0:
        top_conflict = sections["peer_consensus"]["conflicts"][0]
        alerts.append({
            "severity": "MEDIUM",
            "code": "PEER_DIRECTION_CONFLICT",
            "summary": (
                f"Peer systems disagree on {top_conflict['symbol']} "
                f"({top_conflict['direction_counts']})"
            ),
            "details": top_conflict,
        })

    rehab_candidates = sections["strategy_watchlist"]["rehabilitation_candidates"]
    if rehab_candidates:
        worst = rehab_candidates[0]
        alerts.append({
            "severity": "HIGH",
            "code": "STRATEGY_DECAY",
            "summary": (
                f"{worst['strategy']} is a rehabilitation candidate "
                f"(WR {worst['win_rate_pct']}%, PF {worst['profit_factor']}, Sharpe {worst['sharpe']})"
            ),
            "details": worst,
        })

    if previous_snapshot:
        prev_regime = previous_snapshot.get("regime")
        current_regime = sections["regime_context"]["regime"].get("regime")
        prev_open_pnl = _safe_float(previous_snapshot.get("open_avg_pnl_pct"))
        current_open_pnl = _safe_float(sections["topline"].get("open_avg_pnl_pct"))
        pnl_drop_limit = _safe_float(config["regime_change_pnl_drop_pct"], 1.5) or 1.5
        if prev_regime and current_regime and prev_regime != current_regime:
            summary = f"Regime changed {prev_regime} -> {current_regime}"
            severity = "MEDIUM"
            if (
                prev_open_pnl is not None
                and current_open_pnl is not None
                and (prev_open_pnl - current_open_pnl) > pnl_drop_limit
            ):
                severity = "HIGH"
                summary += f" while open PnL fell from {prev_open_pnl:.2f}% to {current_open_pnl:.2f}%"
            alerts.append({
                "severity": severity,
                "code": "REGIME_SHIFT",
                "summary": summary,
                "details": {
                    "previous_regime": prev_regime,
                    "current_regime": current_regime,
                    "previous_open_pnl_pct": prev_open_pnl,
                    "current_open_pnl_pct": current_open_pnl,
                },
            })

    severity_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    alerts.sort(key=lambda item: (severity_rank.get(item["severity"], 99), item["code"]))
    return alerts


def build_recommendations(sections: dict[str, Any], alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    recommendations: list[dict[str, Any]] = []
    alert_codes = {alert["code"] for alert in alerts}
    regime_name = str(sections["regime_context"]["regime"].get("regime") or "")

    if "PORTFOLIO_DRAWDOWN_BREACH" in alert_codes or regime_name.upper() == "CHOPPY":
        recommendations.append({
            "category": "risk",
            "action": "tighten_risk_and_reduce_gross_exposure",
            "rationale": "Choppy regime or drawdown breach warrants smaller sizing and tighter review cadence.",
            "command": None,
        })

    if "PRICE_COVERAGE_GAP" in alert_codes or "PEER_STALE" in alert_codes:
        recommendations.append({
            "category": "observability",
            "action": "refresh_local_monitors",
            "rationale": "Data freshness or pricing gaps need a local refresh cycle before acting on signals.",
            "command": "refresh_kpis",
        })

    if "CONFIDENCE_INVERSION" in alert_codes:
        recommendations.append({
            "category": "model",
            "action": "audit_confidence_calibration",
            "rationale": "High-confidence picks are not earning their weight; calibration likely drifted.",
            "command": "refresh_pick_quality",
        })

    if "STRATEGY_DECAY" in alert_codes:
        for candidate in sections["strategy_watchlist"]["rehabilitation_candidates"][:3]:
            recommendations.append({
                "category": "rehabilitation",
                "action": f"route_{candidate['strategy']}_to_mutation_or_inverse",
                "rationale": (
                    f"{candidate['strategy']} is under threshold. Follow the repo policy: mutate or invert instead of disabling."
                ),
                "command": candidate["mutation_action"],
            })

    if "PEER_DIRECTION_CONFLICT" in alert_codes:
        recommendations.append({
            "category": "consensus",
            "action": "review_symbol_level_peer_conflicts",
            "rationale": "Conflicting peer directions can indicate regime disagreement or stale assumptions.",
            "command": "refresh_portfolio_monitor",
        })

    leaders = sections["strategy_watchlist"]["leaders"]
    if leaders:
        leader_names = ", ".join(leader["strategy"] for leader in leaders[:3])
        recommendations.append({
            "category": "allocation",
            "action": "prefer_validated_leaders_for_next_cycle",
            "rationale": f"Current leaders are {leader_names}. Bias new risk toward proven survivors.",
            "command": None,
        })

    deduped: list[dict[str, Any]] = []
    seen = set()
    for rec in recommendations:
        key = (rec["action"], rec["command"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(rec)
    return deduped


def run_actions(
    recommendations: list[dict[str, Any]],
    run_safe_actions: bool = False,
    run_mutation_actions: bool = False,
) -> list[dict[str, Any]]:
    executed: list[dict[str, Any]] = []
    for rec in recommendations:
        command_key = rec.get("command")
        if not command_key:
            continue
        if command_key in SAFE_ACTIONS and not run_safe_actions:
            continue
        if command_key in MUTATION_ACTIONS and not run_mutation_actions:
            continue

        argv = SAFE_ACTIONS.get(command_key) or MUTATION_ACTIONS.get(command_key)
        if not argv:
            continue

        try:
            completed = subprocess.run(
                argv,
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=600,
                check=False,
            )
            executed.append({
                "command": command_key,
                "returncode": completed.returncode,
                "stdout_tail": completed.stdout[-400:],
                "stderr_tail": completed.stderr[-400:],
            })
        except Exception as exc:  # pragma: no cover
            executed.append({"command": command_key, "returncode": -1, "error": str(exc)})
    return executed


def build_topline(picks: list[dict[str, Any]], price_status: dict[str, Any]) -> dict[str, Any]:
    priced_pnls = [pick["current_pnl_pct"] for pick in picks if pick.get("current_pnl_pct") is not None]
    correct = [pick for pick in picks if pick.get("current_pnl_pct") is not None]
    winners = sum(1 for pick in correct if pick["current_pnl_pct"] > 0)
    return {
        "open_positions": len(picks),
        "priced_positions": price_status["priced_positions"],
        "price_coverage_pct": price_status["coverage_pct"],
        "open_avg_pnl_pct": round(statistics.mean(priced_pnls), 4) if priced_pnls else None,
        "open_median_pnl_pct": _median(priced_pnls),
        "directional_correctness_pct": round((winners / len(correct) * 100.0), 2) if correct else None,
    }


def snapshot_for_history(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "timestamp": report["generated_at"],
        "regime": report["regime_context"]["regime"].get("regime"),
        "open_avg_pnl_pct": report["topline"].get("open_avg_pnl_pct"),
        "directional_correctness_pct": report["topline"].get("directional_correctness_pct"),
        "price_coverage_pct": report["topline"].get("price_coverage_pct"),
        "alert_count": len(report.get("alerts", [])),
    }


def write_markdown_report(report: dict[str, Any]) -> None:
    lines = [
        "# Continuous Improvement Report",
        "",
        f"Generated: {report['generated_at']}",
        "",
        "## Topline",
        f"- Open positions: {report['topline']['open_positions']}",
        f"- Price coverage: {report['topline']['price_coverage_pct']}%",
        f"- Open average PnL: {report['topline']['open_avg_pnl_pct']}%",
        f"- Directional correctness: {report['topline']['directional_correctness_pct']}%",
        f"- Regime: {report['regime_context']['regime'].get('regime')}",
        "",
        "## Alerts",
    ]
    if report["alerts"]:
        for alert in report["alerts"]:
            lines.append(f"- [{alert['severity']}] {alert['code']}: {alert['summary']}")
    else:
        lines.append("- None")
    lines.extend(["", "## Recommendations"])
    if report["recommendations"]:
        for rec in report["recommendations"]:
            suffix = f" (`{rec['command']}`)" if rec.get("command") else ""
            lines.append(f"- {rec['action']}: {rec['rationale']}{suffix}")
    else:
        lines.append("- None")
    REPORT_MD_PATH.write_text("\n".join(lines), encoding="utf-8")


def run_cycle(
    config: dict[str, Any],
    skip_live_benchmark: bool = False,
    run_safe_actions: bool = False,
    run_mutation_actions: bool = False,
) -> dict[str, Any]:
    picks = load_open_picks()
    price_status = enrich_prices(picks)
    annotate_open_positions(picks)

    history = load_history()
    previous_snapshot = history[-1] if history else None

    sections = {
        "topline": build_topline(picks, price_status),
        "price_status": price_status,
        "peer_status": load_peer_status(),
        "alpha_summary": load_alpha_summary(),
        "paper_trading": load_paper_trading_summary(),
        "copytrader": load_copytrader_summary(),
        "benchmark": load_benchmark_context(skip_live_benchmark=skip_live_benchmark),
        "regime_context": load_regime_context(),
        "by_asset_class": aggregate_positions(picks, "asset_class"),
        "by_monitor_bucket": aggregate_positions(picks, "monitor_bucket"),
        "by_peer": aggregate_positions(picks, "peer"),
        "by_confidence": aggregate_positions(picks, "confidence_bucket"),
        "peer_consensus": build_peer_consensus(picks),
    }
    sections["strategy_watchlist"] = build_strategy_watchlist(
        picks=picks,
        strategy_metrics=load_strategy_metrics(),
        config=config,
    )

    alerts = generate_alerts(sections=sections, previous_snapshot=previous_snapshot, config=config)
    recommendations = build_recommendations(sections, alerts)
    executed_actions = run_actions(
        recommendations=recommendations,
        run_safe_actions=run_safe_actions,
        run_mutation_actions=run_mutation_actions,
    )

    report = {
        "generated_at": _now_iso(),
        "reference_style": "hedge-fund risk desk + SRE observability",
        "topline": sections["topline"],
        "peer_status": sections["peer_status"],
        "alpha_summary": sections["alpha_summary"],
        "paper_trading": sections["paper_trading"],
        "copytrader": sections["copytrader"],
        "benchmark": sections["benchmark"],
        "regime_context": sections["regime_context"],
        "by_asset_class": sections["by_asset_class"],
        "by_monitor_bucket": sections["by_monitor_bucket"],
        "by_peer": sections["by_peer"],
        "by_confidence": sections["by_confidence"],
        "peer_consensus": sections["peer_consensus"],
        "strategy_watchlist": sections["strategy_watchlist"],
        "alerts": alerts,
        "recommendations": recommendations,
        "executed_actions": executed_actions,
        "policy": {
            "disable_strategies": False,
            "rehabilitation_policy": "mutate_or_inverse_before_kill",
        },
    }

    _write_json(REPORT_PATH, report)
    write_markdown_report(report)

    history.append(snapshot_for_history(report))
    history = history[-_safe_int(config["history_limit"], 720):]
    _write_json(HISTORY_PATH, history)
    return report


def print_report_summary(report: dict[str, Any]) -> None:
    print("=" * 78)
    print("CONTINUOUS IMPROVEMENT MONITOR")
    print(report["generated_at"])
    print("=" * 78)
    topline = report["topline"]
    print(
        f"Open {topline['open_positions']} | "
        f"Coverage {topline['price_coverage_pct']}% | "
        f"Avg PnL {topline['open_avg_pnl_pct']}% | "
        f"Correct {topline['directional_correctness_pct']}%"
    )
    regime = report["regime_context"]["regime"]
    print(
        f"Regime {regime.get('regime')} | BTC {regime.get('btc_price')} | "
        f"Recommendation: {regime.get('recommendation')}"
    )
    if report["alerts"]:
        print("\nAlerts:")
        for alert in report["alerts"][:8]:
            print(f"  [{alert['severity']}] {alert['code']}: {alert['summary']}")
    else:
        print("\nAlerts: none")
    if report["recommendations"]:
        print("\nRecommendations:")
        for rec in report["recommendations"][:8]:
            suffix = f" -> {rec['command']}" if rec.get("command") else ""
            print(f"  - {rec['action']}{suffix}")
    print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cross-system continuous improvement monitor.")
    parser.add_argument("--loop", action="store_true", help="Run continuously.")
    parser.add_argument("--interval-seconds", type=int, default=None, help="Loop cadence in seconds.")
    parser.add_argument("--cycles", type=int, default=None, help="Stop after N cycles when looping.")
    parser.add_argument("--skip-live-benchmark", action="store_true", help="Do not fetch live benchmark data.")
    parser.add_argument("--run-safe-actions", action="store_true", help="Execute local non-mutation refresh actions.")
    parser.add_argument("--run-mutation-actions", action="store_true", help="Execute mutation/inverse actions from recommendations.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config()
    interval_seconds = args.interval_seconds or _safe_int(config["full_cycle_seconds"], 1200)

    if not args.loop:
        report = run_cycle(
            config=config,
            skip_live_benchmark=args.skip_live_benchmark,
            run_safe_actions=args.run_safe_actions,
            run_mutation_actions=args.run_mutation_actions,
        )
        print_report_summary(report)
        return 0

    completed_cycles = 0
    while True:
        report = run_cycle(
            config=config,
            skip_live_benchmark=args.skip_live_benchmark,
            run_safe_actions=args.run_safe_actions,
            run_mutation_actions=args.run_mutation_actions,
        )
        print_report_summary(report)
        completed_cycles += 1
        if args.cycles is not None and completed_cycles >= args.cycles:
            return 0
        time.sleep(max(1, interval_seconds))


if __name__ == "__main__":
    raise SystemExit(main())
