"""Stage 3: PROMOTE — Merge results, quality gates, live picks analysis.

Merges mutation results from all 3 parallel jobs, applies quality gates,
generates live trading picks from winning mutations against current market
data, and writes the final output for dashboard ingestion.

Usage:
    python -m genome.mutation_lab.promoter [--results-dir .] [--output genome/data/mutation_lab_picks.json]
"""

from __future__ import annotations
import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from genome.mutation_lab.backtester import (
    MutationGenes, compute_indicators, fetch_klines, BACKTEST_SYMBOLS,
    BINANCE_MIRRORS,
)
from genome.mutation_lab.schemas import validate_picks

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUTPUT = PROJECT_ROOT / "genome" / "data" / "mutation_lab_picks.json"
MAX_LIVE_PICKS = 999   # TESTING SPRINT: was 20, uncapped
MAX_PER_SYMBOL = 999   # TESTING SPRINT: was 4, uncapped


def load_all_results(results_dir: str = ".") -> list[dict]:
    """Load and merge mutation results from all parallel jobs."""
    results_path = Path(results_dir)
    all_results = []

    for pattern in ["mutation_results_*.json", "results_*.json"]:
        for f in results_path.glob(pattern):
            try:
                data = json.loads(f.read_text())
                for r in data.get("results", []):
                    r["_source_file"] = f.name
                    all_results.append(r)
                logger.info(f"Loaded {len(data.get('results', []))} results from {f.name}")
            except Exception as e:
                logger.warning(f"Failed to load {f}: {e}")

    return all_results


def filter_winners(results: list[dict]) -> list[dict]:
    """Apply quality gates and return only passing mutations."""
    winners = []
    for r in results:
        bt = r.get("backtest_results", {})
        if bt.get("passed"):
            winners.append(r)

    # Sort by composite quality score
    def quality_score(r: dict) -> float:
        agg = r.get("backtest_results", {}).get("aggregate", {})
        wr = agg.get("win_rate", 0)
        sharpe = agg.get("sharpe_ratio", 0)
        pf = agg.get("profit_factor", 0)
        dd = agg.get("max_drawdown", 1)
        trades = agg.get("num_trades", 0)

        score = (
            wr * 30 +
            min(sharpe / 3, 1) * 25 +
            min(pf / 3, 1) * 20 +
            max(0, 1 - dd / 0.15) * 15 +
            min(trades / 100, 1) * 10
        )
        return score

    winners.sort(key=quality_score, reverse=True)
    return winners


def fetch_current_prices() -> dict[str, float]:
    """Fetch current prices for all crypto symbols from Binance."""
    for base in BINANCE_MIRRORS:
        try:
            resp = requests.get(f"{base}/api/v3/ticker/price",
                                headers={"User-Agent": "MutationLab/1.0"},
                                timeout=10)
            resp.raise_for_status()
            return {t["symbol"]: float(t["price"]) for t in resp.json()}
        except Exception:
            continue
    return {}


def generate_live_picks(winners: list[dict],
                        market_data: dict[str, pd.DataFrame],
                        current_prices: dict[str, float]) -> list[dict]:
    """Run winning mutations against current market data to generate live picks.

    This is the LIVE PICKS ANALYSIS — it doesn't just promote backtested
    strategies, it actually runs them on current data to find actionable signals.
    """
    now = datetime.now(timezone.utc)
    live_picks = []
    symbol_counts: dict[str, int] = {}

    for winner in winners:
        if len(live_picks) >= MAX_LIVE_PICKS:
            break

        genes_data = winner.get("genes", {})
        genes = MutationGenes(
            name=winner.get("strategy_name", "unknown"),
            rsi_period=genes_data.get("rsi_period", 14),
            rsi_oversold=genes_data.get("rsi_oversold", 30),
            rsi_overbought=genes_data.get("rsi_overbought", 70),
            ema_fast=genes_data.get("ema_fast", 9),
            ema_slow=genes_data.get("ema_slow", 21),
            ema_trend=genes_data.get("ema_trend", 50),
            macd_fast=genes_data.get("macd_fast", 12),
            macd_slow=genes_data.get("macd_slow", 26),
            macd_signal=genes_data.get("macd_signal", 9),
            bb_period=genes_data.get("bb_period", 20),
            bb_std=genes_data.get("bb_std", 2.0),
            atr_period=genes_data.get("atr_period", 14),
            tp_atr_mult=genes_data.get("tp_atr_mult", 2.0),
            sl_atr_mult=genes_data.get("sl_atr_mult", 1.5),
            vol_threshold=genes_data.get("vol_threshold", 1.3),
            confidence_base=genes_data.get("confidence_base", 0.42),
            invert_signals=genes_data.get("invert_signals", False),
        )

        for symbol in BACKTEST_SYMBOLS:
            if symbol_counts.get(symbol, 0) >= MAX_PER_SYMBOL:
                continue
            if len(live_picks) >= MAX_LIVE_PICKS:
                break

            df = market_data.get(symbol)
            if df is None or len(df) < 100:
                continue

            # Compute indicators on current data
            df_ind = compute_indicators(df, genes)
            if len(df_ind) < 60:
                continue

            # Check the LAST bar for a signal (current market state)
            last = df_ind.iloc[-1]
            prev = df_ind.iloc[-2] if len(df_ind) > 1 else last
            close = last["Close"]
            atr = last.get("ATR", 0)

            if pd.isna(atr) or atr <= 0 or close <= 0:
                continue

            # Signal scoring (same logic as backtester)
            score = 0.0
            if last.get("MACD_hist", 0) > 0:
                score += 0.15
            ema_f = last.get("EMA_fast", 0)
            ema_s = last.get("EMA_slow", 0)
            if ema_f > ema_s:
                score += 0.12
            rsi = last.get("RSI", 50)
            if not pd.isna(rsi) and genes.rsi_oversold < rsi < 50:
                score += 0.10
            bb_pctb = last.get("BB_pctb", 0.5)
            if not pd.isna(bb_pctb) and bb_pctb < 0.2:
                score += 0.12
            if not pd.isna(rsi) and rsi < genes.rsi_oversold:
                score += 0.15
            vol_ratio = last.get("Vol_ratio", 1.0)
            if not pd.isna(vol_ratio) and vol_ratio > genes.vol_threshold:
                score += 0.10
            ema_t = last.get("EMA_trend", close)
            if close > ema_t:
                score += 0.08

            # MACD crossover
            prev_hist = prev.get("MACD_hist", 0)
            curr_hist = last.get("MACD_hist", 0)
            if not pd.isna(prev_hist) and not pd.isna(curr_hist):
                if prev_hist < 0 and curr_hist > 0:
                    score += 0.12

            direction = "LONG"
            if genes.invert_signals:
                score = -score
                if score < 0:
                    direction = "SHORT"
                    score = abs(score)

            confidence = min(0.95, genes.confidence_base + score)

            # Only generate pick if confidence threshold met
            if confidence < 0.50:
                continue

            # Use actual current price for entry
            current_price = current_prices.get(symbol, close)
            if current_price <= 0 or current_price > 1_000_000:
                current_price = close  # fallback to last close

            if direction == "LONG":
                tp = round(current_price + genes.tp_atr_mult * atr, 2)
                sl = round(current_price - genes.sl_atr_mult * atr, 2)
            else:
                tp = round(current_price - genes.tp_atr_mult * atr, 2)
                sl = round(current_price + genes.sl_atr_mult * atr, 2)

            # Backtest stats for this winner
            agg = winner.get("backtest_results", {}).get("aggregate", {})

            pick = {
                "symbol": symbol,
                "direction": direction,
                "entry_price": round(current_price, 2),
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(confidence, 4),
                "strategy": winner.get("strategy_name", "unknown"),
                "source_system": "mutation_lab",
                "trust_tier": "SANDBOX",
                "mutation_type": winner.get("mutation_type", "unknown"),
                "parent_strategy": winner.get("parent_strategy", "unknown"),
                "win_rate": agg.get("win_rate", 0),
                "sharpe_ratio": agg.get("sharpe_ratio", 0),
                "profit_factor": agg.get("profit_factor", 0),
                "total_trades": agg.get("num_trades", 0),
                "max_drawdown_pct": round(agg.get("max_drawdown", 0) * 100, 2),
                "tp_pct": round((abs(tp - current_price) / current_price), 4),
                "sl_pct": round((abs(sl - current_price) / current_price), 4),
                "dna_hash": winner.get("dna_hash", ""),
                "timestamp": now.isoformat(),
                "category": "crypto",
            }

            # Validate entry_price is sane (garbage filter compat)
            if pick["entry_price"] <= 0 or pick["entry_price"] > 1_000_000:
                continue

            live_picks.append(pick)
            symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
            logger.info(f"Live pick: {symbol} {direction} @ {current_price:.2f} "
                        f"(conf={confidence:.2f}, strategy={pick['strategy']})")

    return live_picks


def build_output(winners: list[dict], live_picks: list[dict],
                 total_mutations: int, total_passed: int) -> dict:
    """Build the final mutation_lab_picks.json payload."""
    now = datetime.now(timezone.utc)

    # Mutation type breakdown
    type_counts = {}
    for w in winners:
        mt = w.get("mutation_type", "unknown")
        type_counts[mt] = type_counts.get(mt, 0) + 1

    return {
        "system": "mutation_lab",
        "version": "1.0.0",
        "generated_at": now.isoformat(),
        "total_picks": len(live_picks),
        "mutation_stats": {
            "total_mutations_tested": total_mutations,
            "passed_quality_gates": total_passed,
            "live_signals_generated": len(live_picks),
            "mutation_type_breakdown": type_counts,
        },
        "winners_summary": [
            {
                "strategy": w.get("strategy_name"),
                "type": w.get("mutation_type"),
                "parent": w.get("parent_strategy"),
                "win_rate": w.get("backtest_results", {}).get("aggregate", {}).get("win_rate"),
                "sharpe": w.get("backtest_results", {}).get("aggregate", {}).get("sharpe_ratio"),
                "profit_factor": w.get("backtest_results", {}).get("aggregate", {}).get("profit_factor"),
            }
            for w in winners[:20]
        ],
        "picks": live_picks,
    }


def _register_winners_in_db(winners: list[dict]) -> None:
    """Register winning mutations in genome/strategy_registry.db."""
    import sqlite3

    db_path = PROJECT_ROOT / "genome" / "strategy_registry.db"
    if not db_path.parent.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Ensure strategies table exists (minimal schema for mutation lab)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategies (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                dna_hash TEXT UNIQUE NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                generation INTEGER DEFAULT 0,
                parent_ids TEXT,
                genes TEXT,
                symbol_specialization TEXT,
                metadata TEXT
            )
        """)

        now = datetime.now(timezone.utc).isoformat()
        registered = 0

        for w in winners:
            dna_hash = w.get("dna_hash", "")
            if not dna_hash:
                continue

            strategy_name = w.get("strategy_name", "unknown")
            strategy_id = f"mutation_lab_{dna_hash}"

            cursor.execute("SELECT id FROM strategies WHERE dna_hash = ?", (dna_hash,))
            if cursor.fetchone():
                # Update existing
                cursor.execute("""
                    UPDATE strategies SET updated_at = ?, status = 'active'
                    WHERE dna_hash = ?
                """, (now, dna_hash))
            else:
                # Insert new
                agg = w.get("backtest_results", {}).get("aggregate", {})
                metadata = json.dumps({
                    "mutation_type": w.get("mutation_type", "unknown"),
                    "parent_strategy": w.get("parent_strategy", "unknown"),
                    "win_rate": agg.get("win_rate", 0),
                    "sharpe_ratio": agg.get("sharpe_ratio", 0),
                    "profit_factor": agg.get("profit_factor", 0),
                    "max_drawdown": agg.get("max_drawdown", 0),
                    "source": "mutation_lab",
                })
                cursor.execute("""
                    INSERT INTO strategies (id, name, dna_hash, status, created_at,
                                            updated_at, generation, parent_ids, genes, metadata)
                    VALUES (?, ?, ?, 'active', ?, ?, 0, ?, ?, ?)
                """, (
                    strategy_id, strategy_name, dna_hash, now, now,
                    json.dumps([w.get("parent_strategy", "")]),
                    json.dumps(w.get("genes", {})),
                    metadata,
                ))
                registered += 1

        conn.commit()
        conn.close()
        logger.info(f"PROMOTE: Registered {registered} new winners in strategy_registry.db "
                     f"({len(winners)} total winners)")
    except Exception as e:
        logger.warning(f"PROMOTE: Failed to register in strategy_registry.db: {e}")


def _log_audit_event(total_mutations: int, passed: int, live_picks: int) -> None:
    """Log pipeline run event to audit_trail.db."""
    import sqlite3

    audit_db = PROJECT_ROOT / "audit_trail" / "audit_trail.db"
    if not audit_db.parent.exists():
        return

    try:
        conn = sqlite3.connect(str(audit_db))
        cursor = conn.cursor()

        # Ensure events table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pipeline TEXT NOT NULL,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                mutations_tested INTEGER,
                mutations_passed INTEGER,
                live_picks INTEGER,
                details TEXT
            )
        """)

        cursor.execute("""
            INSERT INTO pipeline_events (pipeline, event_type, timestamp,
                                          mutations_tested, mutations_passed, live_picks, details)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            "mutation_lab",
            "pipeline_run",
            datetime.now(timezone.utc).isoformat(),
            total_mutations,
            passed,
            live_picks,
            json.dumps({"version": "1.0.0"}),
        ))

        conn.commit()
        conn.close()
        logger.info(f"PROMOTE: Logged pipeline event to audit_trail.db")
    except Exception as e:
        logger.warning(f"PROMOTE: Failed to log audit event: {e}")


def run_promoter(results_dir: str = ".", output_path: str = None) -> dict:
    """Main promoter entry point."""
    output_path = output_path or str(DEFAULT_OUTPUT)

    logger.info("PROMOTE: Loading mutation results...")
    all_results = load_all_results(results_dir)
    logger.info(f"PROMOTE: Loaded {len(all_results)} total mutation results")

    # Filter winners
    winners = filter_winners(all_results)
    logger.info(f"PROMOTE: {len(winners)} passed quality gates")

    # Fetch current market data for live picks
    logger.info("PROMOTE: Fetching current market data for live picks analysis...")
    market_data = {}
    for sym in BACKTEST_SYMBOLS:
        df = fetch_klines(sym, limit=300)
        if df is not None:
            market_data[sym] = df

    current_prices = fetch_current_prices()
    logger.info(f"PROMOTE: Got prices for {len(current_prices)} symbols")

    # Generate live picks
    live_picks = generate_live_picks(winners, market_data, current_prices)
    logger.info(f"PROMOTE: Generated {len(live_picks)} live picks from mutations")

    # Run super mutation strategies on current market data
    try:
        from genome.mutation_lab.super_mutations import run_all_super_mutations
        super_mutation_picks = []
        for sym, df in market_data.items():
            if df is not None and len(df) >= 60:
                sm_signals = run_all_super_mutations(df, sym)
                super_mutation_picks.extend(sm_signals)
        if super_mutation_picks:
            live_picks.extend(super_mutation_picks)
            logger.info(f"PROMOTE: Added {len(super_mutation_picks)} super mutation picks")
    except Exception as e:
        logger.warning(f"PROMOTE: Super mutations failed (non-fatal): {e}")

    logger.info(f"PROMOTE: Total live picks: {len(live_picks)}")

    # Validate picks
    errors = validate_picks(live_picks)
    if errors:
        logger.warning(f"Pick validation warnings: {errors}")

    # Register winners in strategy_registry.db
    _register_winners_in_db(winners)

    # Log events to audit trail
    _log_audit_event(len(all_results), len(winners), len(live_picks))

    # Build and write output
    output = build_output(winners, live_picks, len(all_results),
                          len(winners))

    # Ensure output directory exists
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2, default=str))
    logger.info(f"PROMOTE: Written {len(live_picks)} picks to {out_path}")

    # Also write a summary log
    summary_path = out_path.parent / "mutation_lab_summary.json"
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mutations_tested": len(all_results),
        "passed_gates": len(winners),
        "live_picks": len(live_picks),
        "by_type": output["mutation_stats"]["mutation_type_breakdown"],
        "top_strategies": [
            f"{w.get('strategy_name')} (WR={w.get('backtest_results', {}).get('aggregate', {}).get('win_rate', 0):.1%})"
            for w in winners[:5]
        ],
    }
    summary_path.write_text(json.dumps(summary, indent=2, default=str))

    return output


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Mutation Lab: Promoter")
    parser.add_argument("--results-dir", default=".")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    output = run_promoter(args.results_dir, args.output)
    stats = output["mutation_stats"]
    print(f"Promoter complete:")
    print(f"  Mutations tested: {stats['total_mutations_tested']}")
    print(f"  Passed quality gates: {stats['passed_quality_gates']}")
    print(f"  Live picks generated: {stats['live_signals_generated']}")
    print(f"  Type breakdown: {stats['mutation_type_breakdown']}")


if __name__ == "__main__":
    main()
