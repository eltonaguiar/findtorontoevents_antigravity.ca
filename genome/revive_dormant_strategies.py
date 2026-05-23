#!/usr/bin/env python3
"""
Generate fresh mutation-based picks for strong strategies that currently have no live picks.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from genome.dna_engine import DNAPermutationEngine, create_strategy_dna
from genome.onchain_data import OnchainDataFetcher
from genome.revive_stale_systems import apply_quality_filters, convert_mutations_to_picks


DASHBOARD_DATA_PATH = PROJECT_ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
DASHBOARD_PAYLOAD_PATH = PROJECT_ROOT / "audit_trail" / "data" / "dashboard_payload.json"
UNIVERSAL_RESOLVED_PATH = PROJECT_ROOT / "audit_trail" / "data" / "universal_resolved_picks.json"
DNA_MUTATION_REPORT_PATH = PROJECT_ROOT / "alpha_engine" / "data" / "dna_mutation_report.json"
OUTPUT_PATH = PROJECT_ROOT / "genome" / "data" / "revival_dormant_strategies_picks.json"
SUMMARY_DIR = PROJECT_ROOT / "genome" / "results"
SUMMARY_DIR.mkdir(parents=True, exist_ok=True)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _norm_symbol(symbol: Any) -> str:
    raw = str(symbol or "").upper().replace("/", "").replace("-", "")
    if not raw:
        return ""
    if raw.endswith("USD") and not raw.endswith("USDT"):
        raw = f"{raw}T"
    return raw


def _norm_direction(direction: Any) -> str:
    raw = str(direction or "").upper()
    return "SHORT" if raw in ("SHORT", "SELL") else "LONG"


def _parse_any_timestamp(row: dict[str, Any]) -> datetime | None:
    for key in (
        "timestamp",
        "generated_at",
        "entry_date",
        "entry_time",
        "created_at",
        "opened_at",
        "resolved_at",
        "closed_at",
        "exit_time",
    ):
        value = row.get(key)
        if not value:
            continue
        try:
            ts = str(value).replace("Z", "+00:00")
            for suffix in (" EST", " EDT", " UTC", " GMT"):
                ts = ts.replace(suffix, "")
            parsed = datetime.fromisoformat(ts)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except Exception:
            continue
    return None


def load_dna_mutation_catalog() -> dict[str, list[str]]:
    if not DNA_MUTATION_REPORT_PATH.exists():
        return {}
    try:
        report = json.load(open(DNA_MUTATION_REPORT_PATH, "r", encoding="utf-8"))
    except Exception:
        return {}

    catalog: dict[str, list[str]] = {}
    for section in ("super_winners", "super_losers"):
        for row in report.get(section, []):
            strategy = str(row.get("strategy") or "").strip()
            if not strategy:
                continue
            catalog[strategy] = [str(v) for v in row.get("mutations_created", []) if str(v).strip()]
    return catalog


def find_dormant_candidates(
    *,
    min_trades: int,
    min_wr: float,
    min_total_pnl: float,
    limit: int,
) -> list[dict[str, Any]]:
    if not DASHBOARD_DATA_PATH.exists():
        return []
    try:
        dashboard = json.load(open(DASHBOARD_DATA_PATH, "r", encoding="utf-8"))
    except Exception:
        return []

    mutation_catalog = load_dna_mutation_catalog()
    deduped: dict[str, dict[str, Any]] = {}
    for entry in dashboard.get("leaderboard", []):
        strategy = str(entry.get("strategy") or "").strip()
        if not strategy or strategy.startswith("Revival_"):
            continue

        active_picks = _safe_int(entry.get("active_picks"), 0)
        fwd_trades = _safe_int(entry.get("fwd_trades"), 0)
        fwd_wr = _safe_float(entry.get("fwd_wr"), 0.0)
        fwd_total_pnl = _safe_float(entry.get("fwd_total_pnl"), 0.0)
        fwd_pf = _safe_float(entry.get("fwd_pf"), 0.0)
        if active_picks > 0:
            continue
        if fwd_trades < min_trades or fwd_wr < min_wr or fwd_total_pnl <= min_total_pnl:
            continue

        systems = [str(s).strip() for s in entry.get("systems") or [] if str(s).strip()]
        strategy_lc = strategy.lower()
        system_name = str(entry.get("system_name") or "").strip().lower()
        if strategy_lc == system_name or strategy_lc in {s.lower() for s in systems}:
            continue
        variants = mutation_catalog.get(strategy, [])
        candidate_score = (
            fwd_wr * 2.0
            + min(fwd_trades, 100) * 0.35
            + max(fwd_total_pnl, 0.0) * 0.4
            + min(fwd_pf, 5.0) * 6.0
            + (12.0 if variants else 0.0)
        )
        candidate = {
            "strategy": strategy,
            "systems": systems,
            "fwd_wr": round(fwd_wr, 2),
            "fwd_trades": fwd_trades,
            "fwd_total_pnl": round(fwd_total_pnl, 2),
            "fwd_pf": round(fwd_pf, 3) if fwd_pf else 0.0,
            "candidate_score": round(candidate_score, 3),
            "known_variants": variants,
        }
        current = deduped.get(strategy)
        if current is None or candidate["candidate_score"] > current["candidate_score"]:
            deduped[strategy] = candidate

    ranked = sorted(
        deduped.values(),
        key=lambda row: (
            row["candidate_score"],
            row["fwd_wr"],
            row["fwd_trades"],
            row["fwd_total_pnl"],
        ),
        reverse=True,
    )
    return ranked[:limit]


def load_local_strategy_history(strategy_names: set[str]) -> dict[str, dict[str, Any]]:
    if not strategy_names or not UNIVERSAL_RESOLVED_PATH.exists():
        return {}
    try:
        resolved = json.load(open(UNIVERSAL_RESOLVED_PATH, "r", encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(resolved, list):
        return {}

    targets = {str(name).strip() for name in strategy_names if str(name).strip()}
    history: dict[str, dict[str, Any]] = {}
    for pick in resolved:
        strategy = str(pick.get("strategy") or "").strip()
        if strategy not in targets:
            continue
        symbol = _norm_symbol(pick.get("symbol", pick.get("pair", "")))
        if not symbol:
            continue

        strat_bucket = history.setdefault(
            strategy,
            {"symbols": {}, "last_seen": None},
        )
        sym_bucket = strat_bucket["symbols"].setdefault(
            symbol,
            {
                "symbol": symbol,
                "total_trades": 0,
                "wins": 0,
                "losses": 0,
                "total_pnl": 0.0,
                "directions": Counter(),
                "source_systems": Counter(),
                "last_seen": None,
            },
        )

        sym_bucket["total_trades"] += 1
        pnl = _safe_float(
            pick.get("pnl_pct", pick.get("realized_pnl_pct", pick.get("gross_pnl_pct", 0.0))),
            0.0,
        )
        sym_bucket["total_pnl"] += pnl

        status = str(pick.get("status", pick.get("outcome", ""))).upper()
        if status in ("WON", "WIN", "TP_HIT", "CLOSED_TP") or (not status and pnl > 0):
            sym_bucket["wins"] += 1
        elif status in ("LOST", "LOSS", "SL_HIT", "CLOSED_SL") or (not status and pnl < 0):
            sym_bucket["losses"] += 1

        sym_bucket["directions"][_norm_direction(pick.get("direction", pick.get("signal_type", pick.get("signal", ""))))] += 1
        source_system = str(pick.get("source_system") or "").strip().lower()
        if source_system:
            sym_bucket["source_systems"][source_system] += 1

        ts = _parse_any_timestamp(pick)
        if ts and (sym_bucket["last_seen"] is None or ts > sym_bucket["last_seen"]):
            sym_bucket["last_seen"] = ts
        if ts and (strat_bucket["last_seen"] is None or ts > strat_bucket["last_seen"]):
            strat_bucket["last_seen"] = ts

    return history


def load_dashboard_strategy_fallback(strategy_names: set[str]) -> dict[str, list[dict[str, Any]]]:
    if not strategy_names or not DASHBOARD_PAYLOAD_PATH.exists():
        return {}
    try:
        payload = json.load(open(DASHBOARD_PAYLOAD_PATH, "r", encoding="utf-8"))
    except Exception:
        return {}

    targets = {str(name).strip() for name in strategy_names if str(name).strip()}
    fallback: dict[str, list[dict[str, Any]]] = {}
    for system in payload.get("systems", []):
        for strat in system.get("strategies", []):
            strategy = str(strat.get("name") or "").strip()
            if strategy not in targets:
                continue
            long_total = _safe_int(strat.get("long_wins"), 0) + _safe_int(strat.get("long_losses"), 0)
            short_total = _safe_int(strat.get("short_wins"), 0) + _safe_int(strat.get("short_losses"), 0)
            direction_bias = "SHORT" if short_total > long_total else "LONG"
            top_symbols = strat.get("top_symbols") or []
            rows = fallback.setdefault(strategy, [])
            for sym in top_symbols:
                symbol = _norm_symbol(sym.get("symbol"))
                if not symbol:
                    continue
                wins = _safe_int(sym.get("wins"), 0)
                losses = _safe_int(sym.get("losses"), 0)
                flats = _safe_int(sym.get("flat"), 0)
                total = wins + losses + flats
                if total <= 0:
                    total = _safe_int(strat.get("resolved"), 0)
                total_pnl = _safe_float(sym.get("pnl"), 0.0)
                rows.append(
                    {
                        "strategy": strategy,
                        "symbol": symbol,
                        "total_trades": total,
                        "wins": wins,
                        "losses": losses,
                        "avg_pnl": round(total_pnl / total, 4) if total else 0.0,
                        "total_pnl": round(total_pnl, 4),
                        "direction_bias": direction_bias,
                    }
                )
    return fallback


def build_history_rows(
    candidate: dict[str, Any],
    local_history: dict[str, dict[str, Any]],
    dashboard_fallback: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    strategy = candidate["strategy"]
    local_symbols = local_history.get(strategy, {}).get("symbols", {})
    rows: list[dict[str, Any]] = []
    for symbol, stats in local_symbols.items():
        total = _safe_int(stats.get("total_trades"), 0)
        if total < 2:
            continue
        directions = stats.get("directions", Counter())
        direction_bias = directions.most_common(1)[0][0] if directions else "LONG"
        total_pnl = _safe_float(stats.get("total_pnl"), 0.0)
        rows.append(
            {
                "strategy": strategy,
                "symbol": symbol,
                "total_trades": total,
                "wins": _safe_int(stats.get("wins"), 0),
                "losses": _safe_int(stats.get("losses"), 0),
                "avg_pnl": round(total_pnl / total, 4) if total else 0.0,
                "total_pnl": round(total_pnl, 4),
                "direction_bias": direction_bias,
            }
        )

    rows.sort(
        key=lambda row: (
            row["wins"] / max(row["total_trades"], 1),
            row["total_trades"],
            row["total_pnl"],
        ),
        reverse=True,
    )
    if rows:
        return rows[:5]

    fallback_rows = dashboard_fallback.get(strategy, [])
    fallback_rows = sorted(
        fallback_rows,
        key=lambda row: (
            row["wins"] / max(row["total_trades"], 1),
            row["total_trades"],
            row["total_pnl"],
        ),
        reverse=True,
    )
    return fallback_rows[:5]


def create_mutations_for_candidate(
    candidate: dict[str, Any],
    history_rows: list[dict[str, Any]],
    *,
    mutations_per_parent: int,
    mutation_rate: float,
    mutation_strength: float,
):
    engine = DNAPermutationEngine(seed=int(time.time()) % 2**31)
    onchain_genes = {}
    bias = {}
    try:
        fetcher = OnchainDataFetcher(cache_ttl=3600)
        onchain_genes = fetcher.get_all_genes("BTCUSDT")
        bias = fetcher.get_mutation_bias(onchain_genes)
    except Exception:
        pass

    mutations = []
    for row in history_rows:
        strategy = str(row.get("strategy") or candidate["strategy"])
        symbol = _norm_symbol(row.get("symbol", "BTCUSDT"))
        total = _safe_int(row.get("total_trades"), 0)
        wins = _safe_int(row.get("wins"), 0)
        win_rate = wins / total if total > 0 else max(candidate["fwd_wr"] / 100.0, 0.55)
        direction_bias = _norm_direction(row.get("direction_bias", "LONG"))

        parent = create_strategy_dna(
            name=strategy,
            timeframe="1h",
            primary_indicator="EMA",
            entry_logic="momentum",
            exit_logic="take_profit",
            risk_profile="moderate" if win_rate >= 0.55 else "aggressive",
            symbol=symbol,
            position_size=0.05,
            leverage=2,
            take_profit_mult=round(2.0 + win_rate, 2),
            stop_loss_mult=round(1.0 + (1 - win_rate), 2),
            expected_wr=round(win_rate, 4),
        )
        parent.genes["direction_bias"] = direction_bias

        for _ in range(mutations_per_parent):
            mutant = engine.mutate_dna(
                parent,
                mutation_rate=mutation_rate,
                mutation_strength=mutation_strength,
                bias=bias or None,
            )
            mutant.genes["parent_strategy"] = strategy
            mutant.genes["parent_symbol"] = symbol
            mutant.genes["parent_win_rate"] = win_rate
            mutant.genes["source_system"] = "dormant_strategy_revival"
            mutant.genes["mutation_type"] = "dormant_strategy_revival"
            mutations.append(mutant)

    unique = list({m.dna_hash: m for m in mutations}.values())
    return unique, onchain_genes


def save_pick_file(path: Path, picks: list[dict[str, Any]], label: str) -> None:
    try:
        from alpha_engine.feed_hygiene import sanitize_active_picks
    except ImportError:
        sanitize_active_picks = lambda rows, _label: rows
    cleaned = sanitize_active_picks(picks, label)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, indent=2, default=str)


def main() -> int:
    parser = argparse.ArgumentParser(description="Revive dormant high-track-record strategies")
    parser.add_argument("--min-trades", type=int, default=5)
    parser.add_argument("--min-wr", type=float, default=55.0)
    parser.add_argument("--min-total-pnl", type=float, default=0.0)
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--mutations-per", type=int, default=8)
    parser.add_argument("--mutation-rate", type=float, default=0.45)
    parser.add_argument("--mutation-strength", type=float, default=0.35)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    candidates = find_dormant_candidates(
        min_trades=args.min_trades,
        min_wr=args.min_wr,
        min_total_pnl=args.min_total_pnl,
        limit=args.limit,
    )
    if not candidates:
        print("No dormant high-track-record strategies found.")
        return 0

    print(f"Found {len(candidates)} dormant strategy candidates:")
    for row in candidates:
        systems = ",".join(row.get("systems", [])[:3]) or "unknown"
        print(
            f"  {row['strategy'][:42]:42s} | "
            f"WR={row['fwd_wr']:.1f}% | trades={row['fwd_trades']:>3} | "
            f"pnl={row['fwd_total_pnl']:>6.2f} | systems={systems}"
        )
    if args.dry_run:
        return 0

    target_names = {c["strategy"] for c in candidates}
    local_history = load_local_strategy_history(target_names)
    dashboard_fallback = load_dashboard_strategy_fallback(target_names)
    pseudo_system = {"name": "dormant_strategies"}
    all_picks: list[dict[str, Any]] = []
    summary: list[dict[str, Any]] = []

    for candidate in candidates:
        history_rows = build_history_rows(candidate, local_history, dashboard_fallback)
        if not history_rows:
            print(f"  [SKIP] {candidate['strategy']}: no historical symbol data")
            continue

        mutations, onchain = create_mutations_for_candidate(
            candidate,
            history_rows,
            mutations_per_parent=args.mutations_per,
            mutation_rate=args.mutation_rate,
            mutation_strength=args.mutation_strength,
        )
        candidate_picks = convert_mutations_to_picks(mutations, pseudo_system)
        for pick in candidate_picks:
            pick["source_system"] = "revival_dormant_strategies"
            pick["revival_target_strategy"] = candidate["strategy"]
            pick["revival_parent_systems"] = candidate["systems"]
            pick["revival_reason"] = "dormant_high_track_record"
            pick["revival_metrics"] = {
                "fwd_wr": candidate["fwd_wr"],
                "fwd_trades": candidate["fwd_trades"],
                "fwd_total_pnl": candidate["fwd_total_pnl"],
                "fwd_pf": candidate["fwd_pf"],
            }
            if candidate["known_variants"]:
                pick["known_dna_variants"] = candidate["known_variants"][:5]
        candidate_picks = apply_quality_filters(candidate_picks)
        candidate_picks.sort(
            key=lambda row: (
                row.get("pick_score", 0.0),
                row.get("confidence", 0.0),
                row.get("profit_to_risk", 0.0),
            ),
            reverse=True,
        )
        kept = 0
        for pick in candidate_picks:
            if kept >= 5:
                break
            all_picks.append(pick)
            kept += 1

        summary.append(
            {
                "strategy": candidate["strategy"],
                "systems": candidate["systems"],
                "history_rows": len(history_rows),
                "mutations_created": len(mutations),
                "picks_kept": kept,
                "known_variants": candidate["known_variants"],
                "onchain_bias_used": bool(onchain),
            }
        )
        print(f"  [OK] {candidate['strategy']}: kept {kept} picks")

    all_picks = apply_quality_filters(all_picks)
    all_picks.sort(
        key=lambda row: (
            row.get("pick_score", 0.0),
            row.get("confidence", 0.0),
            row.get("profit_to_risk", 0.0),
        ),
        reverse=True,
    )

    capped: list[dict[str, Any]] = []
    per_strategy: Counter[str] = Counter()
    per_symbol: Counter[str] = Counter()
    for pick in all_picks:
        target_strategy = str(pick.get("revival_target_strategy") or "")
        symbol = str(pick.get("symbol") or "")
        if per_strategy[target_strategy] >= 5:
            continue
        if per_symbol[symbol] >= 2:
            continue
        capped.append(pick)
        per_strategy[target_strategy] += 1
        per_symbol[symbol] += 1

    save_pick_file(OUTPUT_PATH, capped, "genome_revival_dormant")
    summary_path = SUMMARY_DIR / f"dormant_revival_summary_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "candidates": candidates,
                "summary": summary,
                "output_count": len(capped),
                "output_path": str(OUTPUT_PATH),
            },
            f,
            indent=2,
            default=str,
        )

    print(f"Saved {len(capped)} dormant-strategy revival picks -> {OUTPUT_PATH}")
    print(f"Summary -> {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
