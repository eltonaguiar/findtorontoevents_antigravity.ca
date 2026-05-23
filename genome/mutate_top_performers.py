#!/usr/bin/env python3
"""
Mutate Top Performers (MySQL-first)
===================================

Creates DNA mutations from top-performing strategies.

Source priority:
1) MySQL `ejaguiar1_stocks` (`at_signal_outcomes`) - primary
2) Local CSV fallback (`backtest_results/strategy_rankings.csv`) - secondary

Usage:
  python genome/mutate_top_performers.py
  python genome/mutate_top_performers.py --top-n 15 --mutations-per-parent 12
  python genome/mutate_top_performers.py --source csv
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from genome.dna_engine import DNAPermutationEngine, StrategyDNA, create_strategy_dna
from genome.onchain_data import OnchainDataFetcher
from genome.strategy_registry import StrategyRegistry


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV_FALLBACK = REPO_ROOT / "backtest_results" / "strategy_rankings.csv"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "genome" / "results"


@dataclass
class TopPerformerRow:
    name: str
    strategy_type: str
    asset: str
    timeframe: str
    score: float
    total_return: float
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    total_trades: int
    source: str


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _infer_risk(max_drawdown: float) -> str:
    dd = abs(max_drawdown)
    if dd <= 0.03:
        return "conservative"
    if dd <= 0.08:
        return "moderate"
    return "aggressive"


def _infer_strategy_type(name: str) -> str:
    if name.startswith("RSI_MR_"):
        return "RSI_MEAN_REVERSION"
    if name.startswith("MA_Cross_"):
        return "MA_CROSSOVER"
    if name.startswith("BB_"):
        return "BOLLINGER_BANDS"
    if name.startswith("EMA_RSI_"):
        return "EMA_RSI"
    return "DNA_GENOME"


def _parse_name_genes(name: str) -> Dict[str, Any]:
    genes: Dict[str, Any] = {}

    m = re.match(r"^RSI_MR_(\d+)_(\d+)_(\d+)_([A-Z]+)$", name)
    if m:
        genes["rsi_period"] = int(m.group(1))
        genes["rsi_oversold"] = int(m.group(2))
        genes["rsi_overbought"] = int(m.group(3))
        genes["symbol"] = m.group(4)
        return genes

    m = re.match(r"^MA_Cross_(\d+)_(\d+)_([A-Z]+)$", name)
    if m:
        genes["ema_fast"] = int(m.group(1))
        genes["ema_slow"] = int(m.group(2))
        genes["symbol"] = m.group(3)
        return genes

    m = re.match(r"^BB_(\d+)_(\d+(?:\.\d+)?)_([A-Z]+)$", name)
    if m:
        genes["bb_period"] = int(m.group(1))
        genes["bb_std"] = float(m.group(2))
        genes["symbol"] = m.group(3)
        return genes

    m = re.match(r"^EMA_RSI_(\d+)_(\d+)_(\d+)_([A-Z]+)$", name)
    if m:
        genes["ema_fast"] = int(m.group(1))
        genes["ema_slow"] = int(m.group(2))
        genes["rsi_period"] = int(m.group(3))
        genes["symbol"] = m.group(4)
        return genes

    return genes


def _template_for(strategy_type: str) -> Tuple[str, str, str]:
    st = (strategy_type or "").upper()
    if st == "RSI_MEAN_REVERSION":
        return "RSI", "rsi_oversold", "rsi_overbought"
    if st == "MA_CROSSOVER":
        return "EMA", "golden_cross", "death_cross"
    if st == "BOLLINGER_BANDS":
        return "Bollinger", "mean_reversion", "take_profit"
    if st == "EMA_RSI":
        return "EMA", "momentum", "take_profit"
    return "EMA", "momentum", "take_profit"


def _compute_mysql_composite_score(
    win_rate: float,
    profit_factor: float,
    sharpe_ratio: float,
    expectancy_pct: float,
) -> float:
    # Bounded, interpretable score in a 0-100 range.
    wr_component = _clip(win_rate, 0.0, 1.0) * 45.0
    pf_component = _clip(profit_factor / 3.0, 0.0, 1.0) * 30.0
    sharpe_component = _clip(sharpe_ratio / 2.5, 0.0, 1.0) * 20.0
    exp_component = _clip((expectancy_pct + 1.0) / 3.0, 0.0, 1.0) * 5.0
    return round(wr_component + pf_component + sharpe_component + exp_component, 4)


def fetch_top_performers_from_mysql(
    top_n: int,
    min_trades: int,
    host: str,
    user: str,
    password: str,
    database: str,
    source_system: str = "",
) -> List[TopPerformerRow]:
    try:
        import pymysql
    except ImportError as exc:
        raise RuntimeError("pymysql is not installed") from exc

    conn = pymysql.connect(
        host=host,
        user=user,
        password=password,
        database=database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=15,
        read_timeout=30,
    )
    try:
        with conn.cursor() as cur:
            query = """
                SELECT
                    COALESCE(strategy, 'unknown') AS strategy_name,
                    source_system,
                    COALESCE(
                        UPPER(
                            REPLACE(
                                REPLACE(MAX(symbol), 'USDT', ''),
                                'USD', ''
                            )
                        ),
                        'CRYPTO'
                    ) AS asset_symbol,
                    COUNT(*) AS total_trades,
                    SUM(CASE WHEN LOWER(outcome) IN ('win', 'tp_hit') THEN 1 ELSE 0 END) AS wins,
                    SUM(CASE WHEN LOWER(outcome) IN ('loss', 'sl_hit') THEN 1 ELSE 0 END) AS losses,
                    AVG(CASE WHEN LOWER(outcome) IN ('win', 'tp_hit') THEN pnl_pct END) AS avg_win_pct,
                    AVG(CASE WHEN LOWER(outcome) IN ('loss', 'sl_hit') THEN ABS(pnl_pct) END) AS avg_loss_pct,
                    AVG(pnl_pct) AS avg_pnl_pct,
                    STDDEV_SAMP(pnl_pct) AS pnl_std,
                    SUM(pnl_pct) AS total_return_pct
                FROM at_signal_outcomes
                WHERE LOWER(outcome) IN ('win', 'tp_hit', 'loss', 'sl_hit')
                  AND strategy IS NOT NULL
                  AND strategy <> ''
            """
            params: List[Any] = []
            if source_system:
                query += " AND source_system = %s"
                params.append(source_system)
            query += """
                GROUP BY strategy_name, source_system
                HAVING COUNT(*) >= %s
                ORDER BY COUNT(*) DESC
            """
            params.append(min_trades)
            cur.execute(query, tuple(params))
            raw_rows = list(cur.fetchall())

        if not raw_rows:
            return []

        performers: List[TopPerformerRow] = []
        for row in raw_rows:
            total = int(row.get("total_trades") or 0)
            wins = int(row.get("wins") or 0)
            losses = int(row.get("losses") or 0)
            win_rate = (wins / total) if total > 0 else 0.0

            avg_win = _to_float(row.get("avg_win_pct"), 0.0)
            avg_loss = _to_float(row.get("avg_loss_pct"), 0.0)
            gross_win = wins * avg_win
            gross_loss = losses * avg_loss
            profit_factor = (gross_win / gross_loss) if gross_loss > 0 else (2.0 if gross_win > 0 else 0.0)

            expectancy = _to_float(row.get("avg_pnl_pct"), 0.0)
            pnl_std = _to_float(row.get("pnl_std"), 0.0)
            sharpe = (expectancy / pnl_std) if pnl_std > 0 else 0.0

            total_return = _to_float(row.get("total_return_pct"), 0.0) / 100.0
            worst_trade = -avg_loss / 100.0 if avg_loss > 0 else 0.0

            score = _compute_mysql_composite_score(
                win_rate=win_rate,
                profit_factor=profit_factor,
                sharpe_ratio=sharpe,
                expectancy_pct=expectancy,
            )

            name = str(row.get("strategy_name") or "unknown")
            asset = str(row.get("asset_symbol") or "CRYPTO")

            src_system = str(row.get("source_system") or "unknown")
            performers.append(
                TopPerformerRow(
                    name=name,
                    strategy_type=_infer_strategy_type(name),
                    asset=asset,
                    timeframe="1h",
                    score=score,
                    total_return=total_return,
                    win_rate=win_rate,
                    profit_factor=profit_factor,
                    sharpe_ratio=sharpe,
                    max_drawdown=worst_trade,
                    total_trades=total,
                    source=f"mysql:{database}.at_signal_outcomes:{src_system}",
                )
            )

        performers.sort(key=lambda r: r.score, reverse=True)
        return performers[:top_n]
    finally:
        conn.close()


def fetch_top_performers_from_csv(
    csv_path: Path,
    top_n: int,
) -> List[TopPerformerRow]:
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing CSV fallback file: {csv_path}")

    rows = list(csv.DictReader(csv_path.open("r", newline="", encoding="utf-8")))
    rows.sort(key=lambda r: _to_float(r.get("score"), -1e9), reverse=True)

    performers: List[TopPerformerRow] = []
    for row in rows[:top_n]:
        performers.append(
            TopPerformerRow(
                name=str(row.get("name") or "unknown"),
                strategy_type=str(row.get("type") or _infer_strategy_type(str(row.get("name") or ""))),
                asset=str(row.get("asset") or "CRYPTO"),
                timeframe=str(row.get("timeframe") or "1d"),
                score=_to_float(row.get("score"), 0.0),
                total_return=_to_float(row.get("total_return"), 0.0),
                win_rate=_to_float(row.get("win_rate"), 0.0),
                profit_factor=_to_float(row.get("profit_factor"), 0.0),
                sharpe_ratio=_to_float(row.get("sharpe_ratio"), 0.0),
                max_drawdown=_to_float(row.get("max_drawdown"), 0.0),
                total_trades=int(_to_float(row.get("num_trades"), 0)),
                source=f"csv:{csv_path}",
            )
        )

    return performers


def build_parent_dna(
    rank: int,
    performer: TopPerformerRow,
) -> StrategyDNA:
    primary, entry_logic, exit_logic = _template_for(performer.strategy_type)
    risk = _infer_risk(performer.max_drawdown)

    risk_to_position = {"conservative": 0.03, "moderate": 0.06, "aggressive": 0.10}
    risk_to_leverage = {"conservative": 1, "moderate": 2, "aggressive": 3}

    genes = _parse_name_genes(performer.name)
    genes.update(
        {
            "symbol": genes.get("symbol", performer.asset),
            "position_size": risk_to_position[risk],
            "leverage": risk_to_leverage[risk],
            "take_profit_mult": round(_clip(1.0 + performer.profit_factor, 1.2, 4.5), 2),
            "stop_loss_mult": round(_clip(0.7 + abs(performer.max_drawdown) * 20, 0.8, 2.5), 2),
            "expected_wr": round(performer.win_rate, 4),
            "expected_sharpe": round(performer.sharpe_ratio, 4),
            "expected_profit_factor": round(performer.profit_factor, 4),
            "expected_score": round(performer.score, 4),
            "source_rank": rank,
            "source_reference": performer.source,
            "source_metric_trades": performer.total_trades,
        }
    )

    return create_strategy_dna(
        name=performer.name,
        timeframe=performer.timeframe or "1h",
        primary_indicator=primary,
        entry_logic=entry_logic,
        exit_logic=exit_logic,
        risk_profile=risk,
        **genes,
    )


def mutate_top_performers(
    performers: List[TopPerformerRow],
    mutations_per_parent: int,
    mutation_rate: float,
    mutation_strength: float,
    use_onchain_bias: bool,
) -> Dict[str, Any]:
    engine = DNAPermutationEngine(seed=42)
    bias: Dict[str, Any] = {}
    onchain_genes: Dict[str, Any] = {}

    if use_onchain_bias:
        fetcher = OnchainDataFetcher(cache_ttl=3600)
        onchain_genes = fetcher.get_all_genes("BTCUSDT")
        bias = fetcher.get_mutation_bias(onchain_genes)

    parent_summaries: List[Dict[str, Any]] = []
    mutations: List[StrategyDNA] = []

    for rank, performer in enumerate(performers, start=1):
        parent = build_parent_dna(rank, performer)
        parent_summaries.append(
            {
                "rank": rank,
                "name": performer.name,
                "type": performer.strategy_type,
                "asset": performer.asset,
                "timeframe": performer.timeframe,
                "score": performer.score,
                "win_rate": performer.win_rate,
                "profit_factor": performer.profit_factor,
                "sharpe_ratio": performer.sharpe_ratio,
                "max_drawdown": performer.max_drawdown,
                "total_return": performer.total_return,
                "total_trades": performer.total_trades,
                "source": performer.source,
                "strategy_id": parent.strategy_id,
                "dna_hash": parent.dna_hash,
            }
        )

        for _ in range(mutations_per_parent):
            mutant = engine.mutate_dna(
                parent,
                mutation_rate=mutation_rate,
                mutation_strength=mutation_strength,
                bias=bias or None,
            )
            mutant.genes["parent_strategy_id"] = parent.strategy_id
            mutant.genes["parent_name"] = performer.name
            mutant.genes["parent_rank"] = rank
            mutant.genes["mutation_batch"] = "top_performer_mysql_first"
            mutations.append(mutant)

    unique_mutations = list({m.dna_hash: m for m in mutations}.values())

    return {
        "parents": parent_summaries,
        "mutations_raw": len(mutations),
        "mutations_unique": len(unique_mutations),
        "onchain_genes": onchain_genes,
        "onchain_bias": bias,
        "mutation_objects": unique_mutations,
    }


def save_output(
    out_dir: Path,
    source_mode: str,
    top_n: int,
    mutations_per_parent: int,
    result: Dict[str, Any],
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_file = out_dir / f"top_performer_mutations_{stamp}.json"

    preview = []
    for m in result["mutation_objects"][:30]:
        preview.append(
            {
                "strategy_id": m.strategy_id,
                "name": m.name,
                "parent_name": m.genes.get("parent_name"),
                "parent_rank": m.genes.get("parent_rank"),
                "dna_hash": m.dna_hash,
                "generation": m.generation,
                "recent_mutations": m.mutation_history[-3:] if m.mutation_history else [],
            }
        )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_mode": source_mode,
        "selection": {
            "top_n": top_n,
            "mutations_per_parent": mutations_per_parent,
        },
        "onchain_genes": result["onchain_genes"],
        "onchain_bias": result["onchain_bias"],
        "parents": result["parents"],
        "mutation_count_raw": result["mutations_raw"],
        "mutation_count_unique": result["mutations_unique"],
        "mutation_preview": preview,
        "mutations": [m.to_dict() for m in result["mutation_objects"]],
    }

    with out_file.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return out_file


def register_mutations(mutations: List[StrategyDNA]) -> Dict[str, int]:
    registry = StrategyRegistry()
    return registry.auto_register_strategies(mutations)


def _select_performers(
    source_mode: str,
    top_n: int,
    min_trades: int,
    mysql_host: str,
    mysql_user: str,
    mysql_password: str,
    mysql_db: str,
    mysql_source_system: str,
    csv_fallback: Path,
) -> Tuple[List[TopPerformerRow], str]:
    mode = source_mode.lower()
    errors: List[str] = []

    if mode in {"auto", "mysql"}:
        try:
            mysql_rows = fetch_top_performers_from_mysql(
                top_n=top_n,
                min_trades=min_trades,
                host=mysql_host,
                user=mysql_user,
                password=mysql_password,
                database=mysql_db,
                source_system=mysql_source_system,
            )
            if mysql_rows:
                return mysql_rows, "mysql"
            errors.append("MySQL query returned 0 rows")
        except Exception as exc:
            errors.append(f"MySQL fetch failed: {exc}")
            if mode == "mysql":
                raise
        if mode == "auto":
            print(f"[INFO] MySQL source unavailable in auto mode, falling back. Reason: {errors[-1]}")

    if mode in {"auto", "csv"}:
        try:
            csv_rows = fetch_top_performers_from_csv(csv_path=csv_fallback, top_n=top_n)
            if csv_rows:
                return csv_rows, "csv"
            errors.append("CSV fallback returned 0 rows")
        except Exception as exc:
            errors.append(f"CSV fetch failed: {exc}")
            if mode == "csv":
                raise

    raise RuntimeError("Could not load top performers. " + " | ".join(errors))


def main() -> int:
    parser = argparse.ArgumentParser(description="Create DNA mutations from top performers (MySQL-first).")
    parser.add_argument("--top-n", type=int, default=10, help="Number of top strategies to use as parents.")
    parser.add_argument("--mutations-per-parent", type=int, default=8, help="Mutations generated per parent.")
    parser.add_argument("--mutation-rate", type=float, default=0.45, help="Per-gene mutation probability.")
    parser.add_argument("--mutation-strength", type=float, default=0.35, help="Numeric mutation strength.")
    parser.add_argument(
        "--source",
        type=str,
        default="auto",
        choices=["auto", "mysql", "csv"],
        help="Source selection. auto prefers MySQL, falls back to CSV.",
    )
    parser.add_argument("--min-trades", type=int, default=3, help="Minimum trades required for MySQL ranking.")
    parser.add_argument(
        "--mysql-source-system",
        type=str,
        default="",
        help="Optional source_system filter for at_signal_outcomes (empty = all sources).",
    )
    parser.add_argument("--mysql-host", type=str, default=os.environ.get("MYSQL_HOST") or "mysql.50webs.com")
    parser.add_argument("--mysql-user", type=str, default=os.environ.get("MYSQL_USER") or "ejaguiar1_stocks")
    parser.add_argument("--mysql-password", type=str, default=os.environ.get("MYSQL_PASSWORD") or "stocks")
    parser.add_argument("--mysql-db", type=str, default=os.environ.get("MYSQL_DB") or "ejaguiar1_stocks")
    parser.add_argument("--csv-fallback", type=Path, default=DEFAULT_CSV_FALLBACK, help="Fallback rankings CSV.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output directory.")
    parser.add_argument("--no-onchain-bias", action="store_true", help="Disable on-chain bias in mutation.")
    parser.add_argument("--no-register", action="store_true", help="Do not register mutations in StrategyRegistry.")
    args = parser.parse_args()

    performers, used_source = _select_performers(
        source_mode=args.source,
        top_n=args.top_n,
        min_trades=args.min_trades,
        mysql_host=args.mysql_host,
        mysql_user=args.mysql_user,
        mysql_password=args.mysql_password,
        mysql_db=args.mysql_db,
        mysql_source_system=args.mysql_source_system,
        csv_fallback=args.csv_fallback,
    )

    result = mutate_top_performers(
        performers=performers,
        mutations_per_parent=args.mutations_per_parent,
        mutation_rate=args.mutation_rate,
        mutation_strength=args.mutation_strength,
        use_onchain_bias=not args.no_onchain_bias,
    )

    out_file = save_output(
        out_dir=args.output_dir,
        source_mode=used_source,
        top_n=args.top_n,
        mutations_per_parent=args.mutations_per_parent,
        result=result,
    )

    register_result: Optional[Dict[str, int]] = None
    if not args.no_register:
        register_result = register_mutations(result["mutation_objects"])

    print(f"Source used: {used_source}")
    print(f"Top parents: {len(result['parents'])}")
    print(f"Mutations raw: {result['mutations_raw']}")
    print(f"Mutations unique: {result['mutations_unique']}")
    print(f"Output: {out_file}")
    print("Top 5 parents:")
    for parent in result["parents"][:5]:
        print(
            f"  {parent['rank']}. {parent['name']} | score={parent['score']:.2f} | "
            f"wr={parent['win_rate']:.1%} | sharpe={parent['sharpe_ratio']:.3f} | src={parent['source']}"
        )
    if register_result is not None:
        print(f"Registry: {register_result}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
