"""
Evidence-backed copy trader lesson and mutation extractor.

This replaces the older proxy-scored version that leaned on trader-reported
forward stats and unrealized dollar PnL. The new flow uses:
  1. live agreement across direct/high-score/clone copy-trader picks
  2. realized outcomes from highscore_pick_history.json
  3. snapshot replay to test TP/SL mutations on recorded trade paths

Outputs:
  - copytrader_lessons.json
  - strategy_mutations.json
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

SOURCE_FILES = [
    ("copy_trader_intel", DATA_DIR / "active_picks.json"),
    ("copy_trader_highscore", DATA_DIR / "highscore_active_picks.json"),
    ("copy_trader_clones", DATA_DIR / "clone_active_picks.json"),
]
HISTORY_PATH = DATA_DIR / "highscore_pick_history.json"
LEARNED_STRATS_PATH = DATA_DIR / "learned_strategies.json"
LESSONS_OUT = DATA_DIR / "copytrader_lessons.json"
MUTATIONS_OUT = DATA_DIR / "strategy_mutations.json"

MIN_CONSENSUS_TRADERS = 2
MUTATION_OFFSETS = (-0.25, -0.10, 0.10, 0.25)


def safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_avg(values: list[float]) -> float | None:
    clean = [v for v in values if v is not None]
    return sum(clean) / len(clean) if clean else None


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return default


def normalize_direction(direction: Any) -> str:
    raw = str(direction or "").strip().upper()
    if raw in ("BUY", "LONG"):
        return "LONG"
    if raw in ("SELL", "SHORT"):
        return "SHORT"
    return raw


def normalize_symbol(symbol: Any) -> str:
    return str(symbol or "").strip().upper().replace("/", "").replace("-", "")


def extract_trader_label(strategy: Any = "", fallback: Any = "") -> str:
    label = str(fallback or "").strip()
    if label:
        return label

    strategy = str(strategy or "")
    lower = strategy.lower()
    for prefix in ("clone_hl_copy_", "copy_hl_", "hs_"):
        if lower.startswith(prefix):
            return strategy[len(prefix):]
    return strategy


def normalize_identity(
    strategy: Any = "",
    trader_label: Any = "",
    trader_address: Any = "",
) -> str:
    label = extract_trader_label(strategy, trader_label)
    label_key = " ".join(label.strip().lower().split())
    if label_key:
        return label_key

    addr_key = " ".join(str(trader_address or "").strip().lower().split())
    if addr_key:
        return addr_key

    return " ".join(str(strategy or "").strip().lower().split())


def load_source_picks() -> list[dict]:
    rows: list[dict] = []
    seen_keys: set[str] = set()

    for source_name, path in SOURCE_FILES:
        data = load_json(path, [])
        picks = data if isinstance(data, list) else data.get("picks", data.get("active_picks", []))
        for pick in picks:
            if not isinstance(pick, dict):
                continue

            row = dict(pick)
            row["_source_name"] = source_name
            row["_symbol"] = normalize_symbol(row.get("symbol"))
            row["_direction"] = normalize_direction(row.get("direction", row.get("signal_type")))
            row["_identity"] = normalize_identity(
                row.get("strategy", ""),
                row.get("trader_label", row.get("clone_source_trader", "")),
                row.get("trader_address", ""),
            )
            row["_label"] = extract_trader_label(
                row.get("strategy", ""),
                row.get("trader_label", row.get("clone_source_trader", "")),
            )

            unique_key = (
                row.get("id")
                or f"{source_name}:{row.get('strategy')}:{row.get('_symbol')}:{row.get('_direction')}:"
                f"{row.get('entry_price')}:{row.get('take_profit')}:{row.get('stop_loss')}"
            )
            if unique_key in seen_keys:
                continue
            seen_keys.add(unique_key)
            rows.append(row)

    return rows


def load_learned_strategies() -> dict[str, dict]:
    data = load_json(LEARNED_STRATS_PATH, {})
    profiles = {}
    for strategy in data.get("strategies", []):
        key = normalize_identity(
            trader_label=strategy.get("trader_label", ""),
            trader_address=strategy.get("trader_address", ""),
        )
        if key:
            profiles[key] = strategy
    return profiles


def sort_snapshots(snapshots: list[dict]) -> list[dict]:
    def sort_key(item: dict) -> str:
        return str(item.get("ts") or item.get("timestamp") or "")

    return sorted((s for s in snapshots if isinstance(s, dict)), key=sort_key)


def summarize_pnls(pnls: list[float]) -> dict[str, float]:
    if not pnls:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "avg_pnl": 0.0,
            "total_pnl": 0.0,
            "best_pnl": 0.0,
            "worst_pnl": 0.0,
        }

    wins = sum(1 for pnl in pnls if pnl > 0)
    return {
        "trades": len(pnls),
        "wins": wins,
        "losses": len(pnls) - wins,
        "win_rate": wins / len(pnls),
        "avg_pnl": sum(pnls) / len(pnls),
        "total_pnl": sum(pnls),
        "best_pnl": max(pnls),
        "worst_pnl": min(pnls),
    }


def summarize_history_rows(rows: list[dict]) -> dict[str, float]:
    pnls = [
        safe_float(row.get("final_pnl", row.get("current_pnl")), 0.0) or 0.0
        for row in rows
    ]
    summary = summarize_pnls(pnls)

    peaks = [safe_float(row.get("peak_pnl")) for row in rows]
    mins = []
    for row in rows:
        snapshots = sort_snapshots(row.get("pnl_snapshots", []))
        pnl_path = [safe_float(item.get("pnl")) for item in snapshots]
        pnl_path = [p for p in pnl_path if p is not None]
        if pnl_path:
            mins.append(min(pnl_path))

    summary["avg_peak_pnl"] = safe_avg([p for p in peaks if p is not None]) or 0.0
    summary["avg_trough_pnl"] = safe_avg(mins) or 0.0
    return summary


def is_realized_history_row(row: dict[str, Any]) -> bool:
    status = str(row.get("status") or "").strip().upper()
    if status in {"CLOSED", "WON", "LOST", "TP_HIT", "SL_HIT"}:
        return True
    return bool(row.get("closed_at"))


def load_history_rows() -> tuple[list[dict], dict]:
    rows = load_json(HISTORY_PATH, [])
    by_trader: dict[str, list[float]] = defaultdict(list)
    by_symbol_direction: dict[str, list[dict]] = defaultdict(list)
    by_trader_symbol_direction: dict[str, list[dict]] = defaultdict(list)

    normalized_rows = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        norm = dict(row)
        norm["_symbol"] = normalize_symbol(norm.get("symbol"))
        norm["_direction"] = normalize_direction(norm.get("direction"))
        norm["_identity"] = normalize_identity(norm.get("strategy", ""), norm.get("trader_label", ""))

        if not is_realized_history_row(norm):
            continue

        pnl = safe_float(norm.get("final_pnl", norm.get("current_pnl")))
        if pnl is None:
            continue

        normalized_rows.append(norm)
        if norm["_identity"]:
            by_trader[norm["_identity"]].append(pnl)

        sym_key = f"{norm['_symbol']}::{norm['_direction']}"
        by_symbol_direction[sym_key].append(norm)
        if norm["_identity"]:
            by_trader_symbol_direction[f"{norm['_identity']}::{sym_key}"].append(norm)

    scorebook = {
        "by_trader": {key: summarize_pnls(pnls) for key, pnls in by_trader.items() if pnls},
        "by_symbol_direction": {
            key: summarize_history_rows(group) for key, group in by_symbol_direction.items() if group
        },
        "rows_by_symbol_direction": dict(by_symbol_direction),
        "rows_by_trader_symbol_direction": dict(by_trader_symbol_direction),
    }
    return normalized_rows, scorebook


def aggregate_trader_stats(identities: list[str], scorebook: dict) -> dict[str, float]:
    stats_rows = []
    for identity in identities:
        stats = scorebook["by_trader"].get(identity)
        if stats and stats.get("trades", 0) > 0:
            stats_rows.append(stats)

    if not stats_rows:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "avg_pnl": 0.0,
            "total_pnl": 0.0,
        }

    trades = sum(int(stats["trades"]) for stats in stats_rows)
    wins = sum(int(stats["wins"]) for stats in stats_rows)
    total_pnl = sum(float(stats["total_pnl"]) for stats in stats_rows)
    weighted_avg_pnl = total_pnl / trades if trades else 0.0
    return {
        "trades": trades,
        "wins": wins,
        "losses": trades - wins,
        "win_rate": wins / trades if trades else 0.0,
        "avg_pnl": weighted_avg_pnl,
        "total_pnl": total_pnl,
    }


def extract_live_pnl_pct(pick: dict) -> float | None:
    for key in ("pnl_pct", "current_pnl"):
        value = safe_float(pick.get(key))
        if value is not None:
            return value
    return None


def derive_profile_parameters(
    identities: list[str],
    symbol: str,
    learned_profiles: dict[str, dict],
) -> dict[str, Any]:
    symbol_base = symbol.replace("USDT", "").replace("USD", "")
    tp_pcts: list[float] = []
    sl_pcts: list[float] = []
    hold_hours: list[float] = []
    sessions: list[str] = []
    leverages: list[float] = []
    supporting_profiles = []

    for identity in identities:
        profile = learned_profiles.get(identity)
        if not profile:
            continue

        coin_strategies = profile.get("coin_strategies", {})
        coin_data = None
        for coin_key, candidate in coin_strategies.items():
            if normalize_symbol(coin_key).replace("USDT", "") == symbol_base:
                coin_data = candidate
                break
            if normalize_symbol(candidate.get("coin", "")).replace("USDT", "") == symbol_base:
                coin_data = candidate
                break
        if not coin_data:
            continue

        tp = safe_float(coin_data.get("median_tp_pct"))
        sl = safe_float(coin_data.get("median_sl_pct"))
        hold = safe_float(coin_data.get("median_hold_hours"))
        lev = safe_float(coin_data.get("leverage"))
        session = coin_data.get("best_session") or profile.get("learned_patterns", {}).get("preferred_session")

        if tp and tp > 0:
            tp_pcts.append(tp)
        if sl and sl > 0:
            sl_pcts.append(sl)
        if hold and hold > 0:
            hold_hours.append(hold)
        if lev and lev > 0:
            leverages.append(lev)
        if session:
            sessions.append(str(session))

        trader_stats = profile.get("trader_stats", {})
        supporting_profiles.append({
            "trader": profile.get("trader_label", identity),
            "win_rate": safe_float(trader_stats.get("win_rate")),
            "pnl": safe_float(trader_stats.get("pnl")),
            "edge_score": safe_float(trader_stats.get("edge_score")),
        })

    session_vote = "ANY"
    if sessions:
        session_vote = Counter(sessions).most_common(1)[0][0]

    return {
        "tp_pct": round(safe_avg(tp_pcts), 3) if safe_avg(tp_pcts) is not None else None,
        "sl_pct": round(safe_avg(sl_pcts), 3) if safe_avg(sl_pcts) is not None else None,
        "expected_hold_hours": round(safe_avg(hold_hours), 2) if safe_avg(hold_hours) is not None else None,
        "preferred_session": session_vote,
        "avg_leverage": round(safe_avg(leverages), 2) if safe_avg(leverages) is not None else None,
        "trader_profiles": supporting_profiles,
    }


def history_points(stats: dict[str, float], max_points: float) -> float:
    trades = int(stats.get("trades", 0) or 0)
    if trades <= 0:
        return 0.0

    win_rate = float(stats.get("win_rate", 0) or 0)
    avg_pnl = float(stats.get("avg_pnl", 0) or 0)
    reliability = min(1.0, trades / 12.0)

    if win_rate >= 0.70:
        base = max_points * 0.95
    elif win_rate >= 0.62:
        base = max_points * 0.82
    elif win_rate >= 0.55:
        base = max_points * 0.66
    elif win_rate >= 0.50:
        base = max_points * 0.45
    elif win_rate < 0.35 and avg_pnl < 0:
        base = -max_points * 0.42
    elif win_rate < 0.45 and avg_pnl < 0:
        base = -max_points * 0.20
    else:
        base = 0.0

    pnl_adjust = 0.0
    if avg_pnl >= 2.0:
        pnl_adjust = max_points * 0.10
    elif avg_pnl >= 1.0:
        pnl_adjust = max_points * 0.06
    elif avg_pnl <= -1.0:
        pnl_adjust = -max_points * 0.08

    return round((base + pnl_adjust) * reliability, 2)


def active_points(active_pnls: list[float]) -> float:
    if not active_pnls:
        return 0.0

    avg_pnl = safe_avg(active_pnls) or 0.0
    pos_rate = sum(1 for pnl in active_pnls if pnl > 0) / len(active_pnls)
    if avg_pnl >= 1.0 and pos_rate >= 0.60:
        return 8.0
    if avg_pnl > 0 and pos_rate >= 0.50:
        return 5.0
    if avg_pnl <= -2.0 and pos_rate < 0.40:
        return -4.0
    if avg_pnl < 0:
        return -2.0
    return 1.0


def consensus_points(num_traders: int) -> float:
    if num_traders >= 7:
        return 30.0
    if num_traders == 6:
        return 27.0
    if num_traders == 5:
        return 24.0
    if num_traders == 4:
        return 20.0
    if num_traders == 3:
        return 14.0
    if num_traders == 2:
        return 8.0
    return 0.0


def parameter_points(params: dict[str, Any]) -> float:
    score = 0.0
    if params.get("tp_pct"):
        score += 1.5
    if params.get("sl_pct"):
        score += 1.5
    if params.get("expected_hold_hours"):
        score += 1.0
    if params.get("preferred_session") and params.get("preferred_session") != "ANY":
        score += 1.0
    if params.get("avg_leverage"):
        score += 1.0
    return score


def build_consensus_groups(
    picks: list[dict],
    learned_profiles: dict[str, dict],
    scorebook: dict,
) -> list[dict]:
    grouped: dict[str, dict[str, Any]] = defaultdict(lambda: {"picks": [], "unique": {}})

    for pick in picks:
        symbol = pick.get("_symbol") or normalize_symbol(pick.get("symbol"))
        direction = pick.get("_direction") or normalize_direction(pick.get("direction", pick.get("signal_type")))
        identity = pick.get("_identity") or normalize_identity(
            pick.get("strategy", ""),
            pick.get("trader_label", pick.get("clone_source_trader", "")),
            pick.get("trader_address", ""),
        )
        if not symbol or not direction or not identity:
            continue

        key = f"{symbol}::{direction}"
        grouped[key]["picks"].append(pick)
        if identity not in grouped[key]["unique"]:
            grouped[key]["unique"][identity] = pick

    lessons = []
    for key, bucket in grouped.items():
        unique = bucket["unique"]
        if len(unique) < MIN_CONSENSUS_TRADERS:
            continue

        symbol, direction = key.split("::", 1)
        supporting_identities = sorted(unique.keys())
        supporting_labels = sorted({
            unique[identity].get("_label")
            or unique[identity].get("trader_label")
            or identity
            for identity in unique
        })
        source_names = sorted({
            str(pick.get("_source_name") or pick.get("source_system") or "").lower()
            for pick in bucket["picks"]
            if pick.get("_source_name") or pick.get("source_system")
        })

        live_pnls = [
            pnl for pick in bucket["picks"]
            if (pnl := extract_live_pnl_pct(pick)) is not None
        ]
        entries = [safe_float(pick.get("entry_price")) for pick in bucket["picks"]]
        tps = [safe_float(pick.get("take_profit")) for pick in bucket["picks"]]
        sls = [safe_float(pick.get("stop_loss")) for pick in bucket["picks"]]
        entries = [value for value in entries if value is not None and value > 0]
        tps = [value for value in tps if value is not None and value > 0]
        sls = [value for value in sls if value is not None and value > 0]

        supporting_history_rows = []
        for identity in supporting_identities:
            supporting_history_rows.extend(
                scorebook["rows_by_trader_symbol_direction"].get(f"{identity}::{key}", [])
            )
        symbol_history_rows = scorebook["rows_by_symbol_direction"].get(key, [])

        supporting_closed = summarize_history_rows(supporting_history_rows)
        symbol_closed = summarize_history_rows(symbol_history_rows)
        trader_history = aggregate_trader_stats(supporting_identities, scorebook)

        params = derive_profile_parameters(supporting_identities, symbol, learned_profiles)

        breakdown = {
            "consensus_pts": consensus_points(len(supporting_identities)),
            "source_pts": min(6.0, len(source_names) * 2.0),
            "trader_history_pts": history_points(trader_history, 24.0),
            "supporting_history_pts": history_points(supporting_closed, 28.0),
            "symbol_history_pts": history_points(symbol_closed, 12.0),
            "active_pts": active_points(live_pnls),
            "parameter_pts": parameter_points(params),
        }

        lesson_score = round(clamp(sum(breakdown.values()), 0.0, 100.0), 1)
        avg_live_pnl = safe_avg(live_pnls)
        active_summary = {
            "tracked_positions": len(live_pnls),
            "positive_rate": round(sum(1 for pnl in live_pnls if pnl > 0) / len(live_pnls), 4) if live_pnls else 0.0,
            "avg_pnl_pct": round(avg_live_pnl, 4) if avg_live_pnl is not None else 0.0,
            "best_pnl_pct": round(max(live_pnls), 4) if live_pnls else 0.0,
            "worst_pnl_pct": round(min(live_pnls), 4) if live_pnls else 0.0,
        }

        lessons.append({
            "symbol": symbol,
            "direction": direction,
            "consensus_strength": len(supporting_identities),
            "supporting_traders": supporting_labels,
            "supporting_sources": source_names,
            "avg_entry_price": round(safe_avg(entries), 8) if entries else None,
            "avg_take_profit": round(safe_avg(tps), 8) if tps else None,
            "avg_stop_loss": round(safe_avg(sls), 8) if sls else None,
            "active_support": active_summary,
            "trader_history": {
                "trades": int(trader_history["trades"]),
                "win_rate": round(trader_history["win_rate"], 4),
                "avg_pnl": round(trader_history["avg_pnl"], 4),
                "total_pnl": round(trader_history["total_pnl"], 4),
            },
            "supporting_closed_history": {
                "trades": int(supporting_closed["trades"]),
                "win_rate": round(supporting_closed["win_rate"], 4),
                "avg_pnl": round(supporting_closed["avg_pnl"], 4),
                "total_pnl": round(supporting_closed["total_pnl"], 4),
                "avg_peak_pnl": round(supporting_closed["avg_peak_pnl"], 4),
                "avg_trough_pnl": round(supporting_closed["avg_trough_pnl"], 4),
            },
            "symbol_closed_history": {
                "trades": int(symbol_closed["trades"]),
                "win_rate": round(symbol_closed["win_rate"], 4),
                "avg_pnl": round(symbol_closed["avg_pnl"], 4),
                "total_pnl": round(symbol_closed["total_pnl"], 4),
                "avg_peak_pnl": round(symbol_closed["avg_peak_pnl"], 4),
                "avg_trough_pnl": round(symbol_closed["avg_trough_pnl"], 4),
            },
            "parameter_template": params,
            "score_breakdown": breakdown,
            "lesson_score": lesson_score,
            "_simulation_basis": "supporting_symbol_history" if supporting_closed["trades"] else "symbol_history",
            "_simulation_trades": int(
                supporting_closed["trades"] if supporting_closed["trades"] else symbol_closed["trades"]
            ),
        })

    lessons.sort(
        key=lambda lesson: (
            lesson["lesson_score"],
            lesson["supporting_closed_history"]["trades"],
            lesson["symbol_closed_history"]["trades"],
            lesson["consensus_strength"],
        ),
        reverse=True,
    )
    return lessons


def parse_ts(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def simulate_trade_from_snapshots(row: dict, tp_pct: float, sl_pct: float) -> dict:
    snapshots = sort_snapshots(row.get("pnl_snapshots", []))
    pnl_path = []
    for item in snapshots:
        pnl = safe_float(item.get("pnl"))
        ts = parse_ts(item.get("ts") or item.get("timestamp"))
        if pnl is not None:
            pnl_path.append((ts, pnl))

    final_pnl = safe_float(row.get("final_pnl", row.get("current_pnl")), 0.0) or 0.0
    closed_at = parse_ts(row.get("closed_at") or row.get("last_updated"))
    if not pnl_path or pnl_path[-1][1] != final_pnl:
        pnl_path.append((closed_at, final_pnl))

    tp_hit = None
    sl_hit = None
    for ts, pnl in pnl_path:
        if tp_hit is None and pnl >= tp_pct:
            tp_hit = (ts, tp_pct)
        if sl_hit is None and pnl <= -sl_pct:
            sl_hit = (ts, -sl_pct)
        if tp_hit or sl_hit:
            break

    max_dt = datetime.max.replace(tzinfo=timezone.utc)
    if tp_hit and sl_hit:
        exit_ts, exit_pnl, exit_reason = (
            tp_hit[0], tp_hit[1], "TP_HIT"
        ) if (tp_hit[0] or max_dt) <= (sl_hit[0] or max_dt) else (sl_hit[0], sl_hit[1], "SL_HIT")
    elif tp_hit:
        exit_ts, exit_pnl, exit_reason = tp_hit[0], tp_hit[1], "TP_HIT"
    elif sl_hit:
        exit_ts, exit_pnl, exit_reason = sl_hit[0], sl_hit[1], "SL_HIT"
    else:
        exit_ts, exit_pnl, exit_reason = pnl_path[-1][0], final_pnl, "NO_HIT_EXIT"

    opened_at = parse_ts(row.get("entered_at") or row.get("discovered_at"))
    exit_hours = None
    if opened_at and exit_ts:
        exit_hours = round((exit_ts - opened_at).total_seconds() / 3600.0, 3)

    values = [pnl for _, pnl in pnl_path]
    return {
        "exit_reason": exit_reason,
        "exit_pnl": round(exit_pnl, 4),
        "peak_pnl": round(max(values), 4) if values else round(final_pnl, 4),
        "trough_pnl": round(min(values), 4) if values else round(final_pnl, 4),
        "exit_hours": exit_hours,
        "is_win": exit_pnl > 0,
    }


def mutation_score(lesson_score: float, backtest: dict[str, Any], rr_ratio: float | None) -> float:
    trades = int(backtest.get("trades", 0) or 0)
    evidence_scale = min(1.0, trades / 10.0) if trades > 0 else 0.0
    win_rate = float(backtest.get("win_rate", 0) or 0)
    avg_pnl = float(backtest.get("avg_pnl", 0) or 0)
    total_pnl = float(backtest.get("total_pnl", 0) or 0)

    perf = 0.0
    perf += max(-8.0, min(22.0, (win_rate - 0.45) * 70.0)) * evidence_scale
    perf += max(-10.0, min(10.0, avg_pnl * 4.0)) * evidence_scale
    if trades >= 5 and total_pnl > 0:
        perf += 4.0
    elif trades >= 5 and total_pnl < 0:
        perf -= 3.0

    rr_pts = 0.0
    if rr_ratio is not None:
        if 1.2 <= rr_ratio <= 3.0:
            rr_pts = 6.0
        elif 0.8 <= rr_ratio < 1.2 or 3.0 < rr_ratio <= 4.0:
            rr_pts = 3.0
        else:
            rr_pts = -2.0

    base = lesson_score * 0.70
    return round(clamp(base + perf + rr_pts, 0.0, 100.0), 1)


def evaluate_mutation(history_rows: list[dict], tp_pct: float, sl_pct: float) -> dict[str, Any]:
    outcomes = [simulate_trade_from_snapshots(row, tp_pct, sl_pct) for row in history_rows]
    pnls = [outcome["exit_pnl"] for outcome in outcomes]
    summary = summarize_pnls(pnls)

    exit_hours = [outcome["exit_hours"] for outcome in outcomes if outcome["exit_hours"] is not None]
    avg_exit_hours = safe_avg(exit_hours)
    summary["avg_exit_hours"] = round(avg_exit_hours, 3) if avg_exit_hours is not None else None
    summary["tp_hits"] = sum(1 for outcome in outcomes if outcome["exit_reason"] == "TP_HIT")
    summary["sl_hits"] = sum(1 for outcome in outcomes if outcome["exit_reason"] == "SL_HIT")
    summary["no_hit_exits"] = sum(1 for outcome in outcomes if outcome["exit_reason"] == "NO_HIT_EXIT")
    summary["avg_peak_pnl"] = round(
        safe_avg([outcome["peak_pnl"] for outcome in outcomes]) or 0.0,
        4,
    )
    summary["avg_trough_pnl"] = round(
        safe_avg([outcome["trough_pnl"] for outcome in outcomes]) or 0.0,
        4,
    )
    return summary


def generate_mutations_for_lesson(lesson: dict, scorebook: dict) -> list[dict]:
    params = lesson.get("parameter_template", {})
    base_tp = safe_float(params.get("tp_pct"), 3.0) or 3.0
    base_sl = safe_float(params.get("sl_pct"), 1.5) or 1.5

    symbol_key = f"{lesson['symbol']}::{lesson['direction']}"
    supporting_rows = []
    for trader in lesson.get("supporting_traders", []):
        identity = normalize_identity(trader_label=trader)
        supporting_rows.extend(scorebook["rows_by_trader_symbol_direction"].get(f"{identity}::{symbol_key}", []))
    history_rows = supporting_rows or scorebook["rows_by_symbol_direction"].get(symbol_key, [])

    variants = [("base", base_tp, base_sl)]
    for offset in MUTATION_OFFSETS:
        variants.append((f"tp_{int(offset * 100):+d}pct", round(base_tp * (1 + offset), 3), base_sl))
    for offset in MUTATION_OFFSETS:
        variants.append((f"sl_{int(offset * 100):+d}pct", base_tp, round(base_sl * (1 + offset), 3)))

    mutations = []
    for variant_name, tp_pct, sl_pct in variants:
        if tp_pct <= 0 or sl_pct <= 0:
            continue

        rr_ratio = round(tp_pct / sl_pct, 3) if sl_pct > 0 else None
        backtest = evaluate_mutation(history_rows, tp_pct, sl_pct) if history_rows else summarize_pnls([])

        mutation = {
            "mutation_id": f"{lesson['symbol']}_{lesson['direction']}_{variant_name}",
            "symbol": lesson["symbol"],
            "direction": lesson["direction"],
            "tp_pct": round(tp_pct, 3),
            "sl_pct": round(sl_pct, 3),
            "rr_ratio": rr_ratio,
            "session": params.get("preferred_session", "ANY"),
            "mutation_type": variant_name,
            "source_lesson_score": lesson["lesson_score"],
            "backtest": {
                "trades": int(backtest.get("trades", 0) or 0),
                "win_rate": round(backtest.get("win_rate", 0.0), 4),
                "avg_pnl": round(backtest.get("avg_pnl", 0.0), 4),
                "total_pnl": round(backtest.get("total_pnl", 0.0), 4),
                "best_pnl": round(backtest.get("best_pnl", 0.0), 4),
                "worst_pnl": round(backtest.get("worst_pnl", 0.0), 4),
                "tp_hits": int(backtest.get("tp_hits", 0) or 0),
                "sl_hits": int(backtest.get("sl_hits", 0) or 0),
                "no_hit_exits": int(backtest.get("no_hit_exits", 0) or 0),
                "avg_exit_hours": backtest.get("avg_exit_hours"),
                "avg_peak_pnl": round(backtest.get("avg_peak_pnl", 0.0), 4),
                "avg_trough_pnl": round(backtest.get("avg_trough_pnl", 0.0), 4),
                "basis": "supporting_symbol_history" if supporting_rows else "symbol_history",
            },
        }
        mutation["score"] = mutation_score(lesson["lesson_score"], mutation["backtest"], rr_ratio)
        mutations.append(mutation)

    mutations.sort(
        key=lambda item: (
            item["score"],
            item["backtest"]["trades"],
            item["backtest"]["avg_pnl"],
        ),
        reverse=True,
    )
    return mutations


def mutation_boost_hint(lesson: dict, best_mutation: dict | None) -> int:
    boost = 0.0

    supporting = lesson.get("supporting_closed_history", {})
    trades = int(supporting.get("trades", 0) or 0)
    wr = float(supporting.get("win_rate", 0) or 0)
    avg_pnl = float(supporting.get("avg_pnl", 0) or 0)
    if trades >= 5 and wr >= 0.62 and avg_pnl > 0:
        boost += 4
    elif trades >= 3 and wr >= 0.55 and avg_pnl >= 0:
        boost += 2
    elif trades >= 3 and wr < 0.40 and avg_pnl < 0:
        boost -= 2

    if best_mutation:
        bt = best_mutation.get("backtest", {})
        m_trades = int(bt.get("trades", 0) or 0)
        m_wr = float(bt.get("win_rate", 0) or 0)
        m_avg_pnl = float(bt.get("avg_pnl", 0) or 0)
        if m_trades >= 5 and m_wr >= 0.65 and m_avg_pnl > 0:
            boost += 3
        elif m_trades >= 5 and m_wr < 0.40 and m_avg_pnl < 0:
            boost -= 2

    active_avg = float(lesson.get("active_support", {}).get("avg_pnl_pct", 0) or 0)
    if active_avg >= 1.0:
        boost += 1
    elif active_avg <= -1.0:
        boost -= 1

    return int(clamp(round(boost), -3, 8))


def build_lessons_and_mutations() -> dict[str, Any]:
    picks = load_source_picks()
    learned_profiles = load_learned_strategies()
    _, scorebook = load_history_rows()

    lessons = build_consensus_groups(picks, learned_profiles, scorebook)

    all_mutations = []
    for lesson in lessons:
        mutations = generate_mutations_for_lesson(lesson, scorebook)
        best_mutation = mutations[0] if mutations else None
        lesson["best_mutation"] = best_mutation
        lesson["score_boost_hint"] = mutation_boost_hint(lesson, best_mutation)
        all_mutations.extend(mutations)

    all_mutations.sort(
        key=lambda item: (
            item["score"],
            item["backtest"]["trades"],
            item["backtest"]["avg_pnl"],
        ),
        reverse=True,
    )

    lessons_output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evidence_basis": [
            "live_copy_trader_agreement",
            "highscore_pick_history_realized_outcomes",
            "snapshot_replay_backtests",
        ],
        "total_consensus_groups": len(lessons),
        "total_lessons": len(lessons),
        "min_consensus_traders": MIN_CONSENSUS_TRADERS,
        "lessons": lessons,
    }
    with open(LESSONS_OUT, "w", encoding="utf-8") as handle:
        json.dump(lessons_output, handle, indent=2, default=str)

    mutations_output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_mutations": len(all_mutations),
        "lessons_mutated": len(lessons),
        "mutations_per_lesson": 1 + len(MUTATION_OFFSETS) * 2,
        "mutations": all_mutations,
    }
    with open(MUTATIONS_OUT, "w", encoding="utf-8") as handle:
        json.dump(mutations_output, handle, indent=2, default=str)

    return {
        "lessons": lessons_output,
        "mutations": mutations_output,
    }


def main() -> None:
    print("=" * 70)
    print("  COPY TRADER LESSON EXTRACTOR")
    print("  " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    print("=" * 70)

    result = build_lessons_and_mutations()
    lessons = result["lessons"]["lessons"]
    mutations = result["mutations"]["mutations"]

    print(f"  Consensus lessons: {len(lessons)}")
    print(f"  Mutations scored:  {len(mutations)}")

    if lessons:
        print("\n  Top lessons:")
        for lesson in lessons[:5]:
            support = lesson["supporting_closed_history"]
            print(
                f"    {lesson['symbol']} {lesson['direction']} | "
                f"score={lesson['lesson_score']:.1f} | "
                f"consensus={lesson['consensus_strength']} | "
                f"hist={support['trades']} trades @ {support['win_rate']*100:.0f}% WR | "
                f"boost_hint={lesson['score_boost_hint']:+d}"
            )

    if mutations:
        print("\n  Top mutations:")
        for mutation in mutations[:5]:
            bt = mutation["backtest"]
            print(
                f"    {mutation['mutation_id']} | score={mutation['score']:.1f} | "
                f"tp={mutation['tp_pct']} sl={mutation['sl_pct']} | "
                f"backtest={bt['trades']} trades @ {bt['win_rate']*100:.0f}% WR "
                f"avg={bt['avg_pnl']:+.2f}%"
            )


if __name__ == "__main__":
    main()
