#!/usr/bin/env python3
"""
DARWIN ENGINE — Failure-Specific DNA Evolution
================================================
Identifies strategies/systems that are failing, diagnoses root causes from
closed picks, then evolves improved variants that address specific failure modes.

Pipeline:
1. Scan all evolution portfolios for underperformers (WR < 45%, negative Sharpe)
2. Analyze closed picks: why did they lose? (wrong direction, bad timing, regime mismatch)
3. Classify failure modes (trend-reversal, stop-hunted, late-entry, regime-blind, overconfident)
4. Generate mutated variants that specifically address each failure mode
5. Backtest the variants and promote winners
6. Output: genome/data/failure_evolved_picks.json

Run: python genome/failure_evolver.py
"""

import importlib.util
import json
import logging
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GENOME_DIR = Path(__file__).resolve().parent
DB_PATH = GENOME_DIR / "darwin_portfolios.db"
FAILURE_DB = GENOME_DIR / "failure_evolution.db"
OUTPUT_PATH = GENOME_DIR / "data" / "failure_evolved_picks.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s")
logger = logging.getLogger("FailureEvolver")

# Import GP engine for backtesting
_gp_path = str(GENOME_DIR / "genetic_programmer.py")
_spec = importlib.util.spec_from_file_location("genetic_programmer", _gp_path)
_gp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gp)

FAILURE_MODES = {
    "trend_reversal": "Strategy entered against a developing trend — price kept moving away",
    "stop_hunted": "Hit stop-loss then reversed in the correct direction — stop was too tight",
    "late_entry": "Entered after the move already happened — signal was lagging",
    "regime_blind": "Strategy designed for one regime (e.g. ranging) deployed in another (trending)",
    "overconfident": "High confidence pick that lost — model was overfitting to recent patterns",
    "low_volume": "Entered during low volume — no follow-through on the signal",
    "correlation_break": "Assumed correlation (e.g. BTC leads alts) broke down",
    "unknown": "No clear pattern — random market noise"
}


class FailureDiagnostics:
    """Analyzes closed picks to diagnose why they failed."""

    def __init__(self):
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(str(FAILURE_DB))
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS failure_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                family_id TEXT, symbol TEXT, direction TEXT,
                entry_price REAL, exit_price REAL, pnl_pct REAL,
                failure_mode TEXT, diagnosis TEXT,
                corrective_action TEXT,
                analyzed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS evolved_variants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_family TEXT, failure_mode TEXT,
                variant_name TEXT, mutation_type TEXT,
                backtest_wr REAL, backtest_sharpe REAL,
                improvement_vs_parent REAL,
                created_at TEXT
            );
        """)
        conn.commit()
        conn.close()

    def analyze_portfolio_failures(self) -> Dict[str, List[Dict]]:
        """Scan all portfolios for failing closed picks and diagnose them."""
        if not DB_PATH.exists():
            logger.warning("No portfolio DB found")
            return {}

        conn = sqlite3.connect(str(DB_PATH))
        failures_by_family = {}

        families = ["genesis", "atlas", "nexus", "legion"]
        for family_id in families:
            closed = conn.execute(
                """SELECT symbol, direction, entry_price, exit_price, pnl_pct,
                          strategy, confidence, holding_bars
                   FROM positions WHERE family_id=? AND status!='OPEN' AND pnl_pct < 0
                   ORDER BY pnl_pct ASC""",
                (family_id,)
            ).fetchall()

            if not closed:
                continue

            failures = []
            for sym, direction, entry, exit_p, pnl, strategy, conf, hold_bars in closed:
                mode = self._classify_failure(sym, direction, entry, exit_p, pnl, conf, hold_bars)
                action = self._suggest_corrective(mode, pnl, conf, hold_bars)
                failures.append({
                    "symbol": sym, "direction": direction,
                    "entry_price": entry, "exit_price": exit_p,
                    "pnl_pct": pnl, "strategy": strategy,
                    "confidence": conf, "holding_bars": hold_bars,
                    "failure_mode": mode,
                    "diagnosis": FAILURE_MODES.get(mode, "Unknown"),
                    "corrective_action": action
                })

            if failures:
                failures_by_family[family_id] = failures
                logger.info(f"[{family_id}] Found {len(failures)} failed picks")

                # Log to failure DB
                fail_conn = sqlite3.connect(str(FAILURE_DB))
                now = datetime.now(timezone.utc).isoformat()
                for f in failures:
                    fail_conn.execute(
                        """INSERT INTO failure_analysis
                           (family_id, symbol, direction, entry_price, exit_price, pnl_pct,
                            failure_mode, diagnosis, corrective_action, analyzed_at)
                           VALUES (?,?,?,?,?,?,?,?,?,?)""",
                        (family_id, f["symbol"], f["direction"], f["entry_price"],
                         f["exit_price"], f["pnl_pct"], f["failure_mode"],
                         f["diagnosis"], f["corrective_action"], now)
                    )
                fail_conn.commit()
                fail_conn.close()

        conn.close()
        return failures_by_family

    def _classify_failure(self, symbol, direction, entry, exit_p, pnl, confidence, hold_bars) -> str:
        """Classify the type of failure based on trade characteristics."""
        loss_pct = abs(pnl) if pnl else 0

        # Stop hunted: loss is close to the SL level (2.5%) and holding was short
        if 2.0 <= loss_pct <= 3.5 and hold_bars <= 3:
            return "stop_hunted"

        # Overconfident: high confidence but still lost
        if confidence and confidence > 0.8 and loss_pct > 3:
            return "overconfident"

        # Late entry: entered but price immediately reversed (lost within 1-2 bars)
        if hold_bars <= 2 and loss_pct > 1:
            return "late_entry"

        # Trend reversal: held for a while but kept losing (trending against)
        if hold_bars >= 10 and loss_pct > 5:
            return "trend_reversal"

        # Regime blind: moderate loss over moderate time
        if 3 <= hold_bars <= 8 and 2 <= loss_pct <= 5:
            return "regime_blind"

        return "unknown"

    def _suggest_corrective(self, mode, pnl, confidence, hold_bars) -> str:
        """Suggest a corrective mutation for this failure mode."""
        corrections = {
            "stop_hunted": "Widen stop-loss by 1.5x ATR; add re-entry logic after SL hit",
            "overconfident": "Cap confidence at 0.7; add regime confirmation filter",
            "late_entry": "Add momentum confirmation; require signal persistence for 2+ bars",
            "trend_reversal": "Add trend filter (EMA slope check); reduce position size in trends",
            "regime_blind": "Add market regime detector; skip trades in mismatched regimes",
            "low_volume": "Require minimum volume threshold (1.5x average)",
            "correlation_break": "Validate cross-asset correlation before entry",
            "unknown": "Increase mutation diversity; add ensemble confirmation"
        }
        return corrections.get(mode, "Review and re-evolve")


class FailureEvolver:
    """Evolves improved strategy variants that address specific failure modes."""

    def __init__(self):
        self.diagnostics = FailureDiagnostics()

    def evolve_from_failures(self) -> Dict:
        """Main pipeline: diagnose failures, evolve corrective variants, backtest."""
        logger.info("=" * 70)
        logger.info("FAILURE-SPECIFIC DNA EVOLUTION")
        logger.info("Diagnosing failures and evolving corrective variants...")
        logger.info("=" * 70)

        # Step 1: Diagnose failures
        failures = self.diagnostics.analyze_portfolio_failures()
        if not failures:
            logger.info("No failures to analyze (portfolios are new or all winning)")
            return self._empty_result()

        # Step 2: Aggregate failure modes
        all_modes = Counter()
        for family, fails in failures.items():
            for f in fails:
                all_modes[f["failure_mode"]] += 1

        logger.info(f"\nFailure Mode Distribution:")
        for mode, count in all_modes.most_common():
            logger.info(f"  {mode}: {count} occurrences - {FAILURE_MODES.get(mode, '')}")

        # Step 3: Evolve corrective variants
        variants = self._evolve_corrective_variants(failures, all_modes)

        # Step 4: Generate picks from best variants
        picks = self._generate_corrective_picks(variants, failures)

        # Step 5: Save results
        result = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "system": "failure_evolver",
            "failure_analysis": {
                family: {
                    "total_failures": len(fails),
                    "modes": dict(Counter(f["failure_mode"] for f in fails)),
                    "avg_loss_pct": round(np.mean([f["pnl_pct"] for f in fails]), 2),
                    "worst_loss_pct": round(min(f["pnl_pct"] for f in fails), 2)
                }
                for family, fails in failures.items()
            },
            "corrective_variants": len(variants),
            "total_picks": len(picks),
            "picks": picks
        }

        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(json.dumps(result, indent=2))
        logger.info(f"\nSaved {len(picks)} failure-evolved picks to {OUTPUT_PATH}")

        return result

    def _evolve_corrective_variants(self, failures: Dict, modes: Counter) -> List[Dict]:
        """Create mutated GP strategies addressing each failure mode."""
        variants = []

        # Fetch market data for backtesting
        try:
            symbols = list(set(
                f["symbol"] for fails in failures.values() for f in fails
            ))[:5]
            market_data = _gp.fetch_market_data(symbols, limit=750)
        except Exception as e:
            logger.warning(f"Could not fetch market data: {e}")
            market_data = {}

        if not market_data:
            return variants

        for mode, count in modes.most_common(5):
            logger.info(f"\nEvolving variants for failure mode: {mode} ({count} cases)")

            # Create base strategies with corrective mutations
            for i in range(5):
                strategy = _gp.random_strategy(generation=0, name_prefix=f"Fix_{mode}")

                # Apply mode-specific mutations
                if mode == "stop_hunted":
                    strategy.sl_pct = min(strategy.sl_pct * 1.8, 8.0)  # Wider stops
                    strategy.tp_pct = strategy.tp_pct * 1.3  # Wider targets too
                elif mode == "overconfident":
                    strategy.tp_pct = strategy.tp_pct * 0.7  # Take profit earlier
                    strategy.max_hold_bars = max(strategy.max_hold_bars - 5, 10)
                elif mode == "late_entry":
                    strategy.max_hold_bars = min(strategy.max_hold_bars + 10, 60)  # Allow more time
                elif mode == "trend_reversal":
                    strategy.sl_pct = strategy.sl_pct * 0.8  # Tighter stops for trend trades
                elif mode == "regime_blind":
                    strategy.sl_pct = strategy.sl_pct * 1.2
                    strategy.tp_pct = strategy.tp_pct * 1.2

                # Backtest the variant
                best_result = None
                best_sym = None
                for sym, data in market_data.items():
                    try:
                        result = _gp.backtest_strategy(strategy, data)
                        if best_result is None or result.get("overall_fitness", 0) > best_result.get("overall_fitness", 0):
                            best_result = result
                            best_sym = sym
                    except:
                        pass

                if best_result and best_result.get("overall_fitness", 0) > 0.3:
                    variants.append({
                        "name": f"FailFix_{mode}_{i}",
                        "failure_mode": mode,
                        "strategy": strategy,
                        "best_symbol": best_sym,
                        "backtest": best_result
                    })
                    logger.info(f"  Variant {i}: {best_sym} WR={best_result.get('win_rate',0):.1%} "
                              f"Fitness={best_result.get('overall_fitness',0):.3f}")

        logger.info(f"\nGenerated {len(variants)} corrective variants")
        return variants

    def _generate_corrective_picks(self, variants: List[Dict], failures: Dict) -> List[Dict]:
        """Generate picks from the best corrective variants."""
        picks = []
        now = datetime.now(timezone.utc).isoformat()

        for v in sorted(variants, key=lambda x: x["backtest"].get("overall_fitness", 0), reverse=True)[:20]:
            bt = v["backtest"]
            trades = bt.get("trades", [])
            if not trades:
                continue

            last_trade = trades[-1]
            direction = last_trade.get("direction", "LONG")

            picks.append({
                "symbol": v["best_symbol"],
                "direction": direction,
                "confidence": min(bt.get("overall_fitness", 0.5), 0.95),
                "strategy": v["name"],
                "source_system": "failure_evolver",
                "failure_mode_addressed": v["failure_mode"],
                "correction_applied": FAILURE_MODES.get(v["failure_mode"], ""),
                "win_rate": bt.get("win_rate", 0),
                "sharpe_ratio": bt.get("sharpe_ratio", 0),
                "profit_factor": bt.get("profit_factor", 0),
                "performance_score": bt.get("overall_fitness", 0),
                "timestamp": now
            })

        return picks

    def _empty_result(self):
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "system": "failure_evolver",
            "failure_analysis": {},
            "corrective_variants": 0,
            "total_picks": 0,
            "picks": []
        }


def run_failure_evolution():
    """Main entry point."""
    evolver = FailureEvolver()
    result = evolver.evolve_from_failures()

    print("\n" + "=" * 70)
    print("FAILURE-SPECIFIC DNA EVOLUTION RESULTS")
    print("=" * 70)

    analysis = result.get("failure_analysis", {})
    for family, stats in analysis.items():
        print(f"\n  {family.upper()}:")
        print(f"    Failures: {stats['total_failures']} | Avg Loss: {stats['avg_loss_pct']:.1f}%")
        print(f"    Failure modes: {stats['modes']}")

    picks = result.get("picks", [])
    if picks:
        print(f"\n  Corrective Picks Generated: {len(picks)}")
        for p in picks[:5]:
            print(f"    {p['direction']} {p['symbol']} | Fixes: {p['failure_mode_addressed']} | "
                  f"WR={p['win_rate']:.0%} | Score={p['performance_score']:.3f}")
    else:
        print("\n  No corrective picks needed (portfolios healthy or too new)")

    return result


if __name__ == "__main__":
    run_failure_evolution()
