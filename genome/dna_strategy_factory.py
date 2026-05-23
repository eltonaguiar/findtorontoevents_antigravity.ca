"""
DNA Strategy Factory
====================
Creates combo DNA strategies from proven winners and expands them
across multiple crypto pairs and timeframes.

Produces:
- 8 combo DNA bundles (combining statistically proven signals)
- 168 expansion cells (8 base strategies x 7 pairs x 3 timeframes)
- SQLite persistence at battleground/data/dna_factory.db
- JSON registry at battleground/data/dna_factory_registry.json
"""

import sys
import hashlib
import json
import sqlite3
import argparse
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

# Ensure project root on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from genome.dna_engine import StrategyDNA, CombinationLogic, MarketRegime, create_strategy_dna

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "battleground" / "data" / "dna_factory.db"
REGISTRY_JSON = PROJECT_ROOT / "battleground" / "data" / "dna_factory_registry.json"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("DNAStrategyFactory")

# ===========================================================================
# 8 Combo Definitions
# ===========================================================================
COMBO_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "name": "RSI2_FearGreed_Confluence",
        "combination_logic": "and",
        "components": ["connors_rsi2", "fear_greed_contrarian"],
        "description": "RSI(2)<5 AND Fear&Greed<=20 — double-bottom confluence",
        "genes": {
            "rsi_period": 2,
            "rsi_threshold": 5,
            "fg_threshold": 20,
            "timeframe": "4h",
            "tp_mult": 2.5,
            "sl_mult": 1.0,
            "risk_profile": "moderate",
        },
        "expected_wr": 0.72,
        "expected_sharpe": 4.20,
        "rationale": (
            "Connors RSI-2 alone is 75.7% WR / 4.84 Sharpe on SPY; "
            "Fear&Greed contrarian is 59.3% WR / 4.05 Sharpe. "
            "AND logic filters to only highest-conviction entries."
        ),
    },
    {
        "name": "Keltner_RSI2_DoubleBottom",
        "combination_logic": "sequential",
        "components": ["keltner_mean_reversion", "connors_rsi2"],
        "description": "Keltner channel touch triggers, RSI-2 confirms oversold",
        "genes": {
            "keltner_period": 20,
            "keltner_atr_mult": 2.0,
            "rsi_period": 2,
            "rsi_confirm_threshold": 10,
            "timeframe": "4h",
            "tp_mult": 2.0,
            "sl_mult": 1.2,
            "risk_profile": "moderate",
        },
        "expected_wr": 0.70,
        "expected_sharpe": 3.50,
        "rationale": (
            "Keltner MR is 67.6% WR / 2.06 Sharpe; adding RSI-2 confirmation "
            "(75.7% WR) filters false signals for a tighter sequential entry."
        ),
    },
    {
        "name": "Carter_Keltner_VolSqueeze",
        "combination_logic": "weighted",
        "components": ["carter_squeeze_breakout", "keltner_mean_reversion"],
        "description": "TTM Squeeze fire + Keltner band filter (weighted voting)",
        "genes": {
            "squeeze_length": 20,
            "squeeze_mult_bb": 2.0,
            "squeeze_mult_kc": 1.5,
            "keltner_period": 20,
            "keltner_atr_mult": 2.0,
            "weight_carter": 0.6,
            "weight_keltner": 0.4,
            "timeframe": "4h",
            "tp_mult": 3.0,
            "sl_mult": 1.5,
            "risk_profile": "moderate",
        },
        "expected_wr": 0.68,
        "expected_sharpe": 3.80,
        "rationale": (
            "Carter Squeeze is 66.7% WR / 5.33 Sharpe; Keltner adds "
            "mean-reversion context. Weighted 60/40 in favour of squeeze momentum."
        ),
    },
    {
        "name": "Levine_Momentum_FG",
        "combination_logic": "majority",
        "components": ["levine_adaptive_lookback", "fear_greed_contrarian"],
        "description": "Adaptive momentum + macro fear/greed — majority vote",
        "genes": {
            "lookback_min": 5,
            "lookback_max": 50,
            "lookback_adapt_period": 100,
            "fg_threshold": 25,
            "timeframe": "1d",
            "tp_mult": 2.5,
            "sl_mult": 1.5,
            "risk_profile": "moderate",
        },
        "expected_wr": 0.63,
        "expected_sharpe": 5.50,
        "rationale": (
            "Levine adaptive lookback is 61.6% WR / 7.57 Sharpe; "
            "F&G contrarian is 59.3% / 4.05. Majority vote balances "
            "high-Sharpe momentum with macro sentiment."
        ),
    },
    {
        "name": "ConsecDown_Bollinger_Trap",
        "combination_logic": "and",
        "components": ["consecutive_down_rsi", "bollinger_mean_reversion"],
        "description": "3+ red candles + Bollinger lower-band touch — panic trap",
        "genes": {
            "consec_candles": 3,
            "rsi_period": 2,
            "rsi_threshold": 10,
            "bb_period": 20,
            "bb_std": 2.0,
            "timeframe": "4h",
            "tp_mult": 2.0,
            "sl_mult": 1.0,
            "risk_profile": "moderate",
        },
        "expected_wr": 0.71,
        "expected_sharpe": 1.50,
        "rationale": (
            "Consecutive-down RSI is 74.3% WR / 1.76 Sharpe; Bollinger MR "
            "is 60.7% / 0.72. AND logic catches panic sell-offs touching "
            "the lower band for high-probability mean reversion."
        ),
    },
    {
        "name": "BTCDom_RSI2_Rotation",
        "combination_logic": "sequential",
        "components": ["btc_dominance_rotation", "connors_rsi2"],
        "description": "BTC dominance rotation signal, then RSI-2 precise entry",
        "genes": {
            "btc_dom_sma": 30,
            "btc_dom_threshold": -0.02,
            "rsi_period": 2,
            "rsi_threshold": 5,
            "timeframe": "1d",
            "tp_mult": 3.0,
            "sl_mult": 1.5,
            "risk_profile": "moderate",
        },
        "expected_wr": 0.68,
        "expected_sharpe": 3.80,
        "rationale": (
            "BTC dominance rotation detects alt-season regime shift; "
            "RSI-2 (75.7% WR) provides pinpoint entry timing in the "
            "secondary sequential step."
        ),
    },
    {
        "name": "TripleMR_Confluence",
        "combination_logic": "consensus_75",
        "components": ["connors_rsi2", "keltner_mean_reversion", "bollinger_mean_reversion"],
        "description": "3 mean-reversion signals — 2 of 3 must agree (75% consensus)",
        "genes": {
            "rsi_period": 2,
            "rsi_threshold": 10,
            "keltner_period": 20,
            "keltner_atr_mult": 2.0,
            "bb_period": 20,
            "bb_std": 2.0,
            "timeframe": "4h",
            "tp_mult": 2.0,
            "sl_mult": 1.0,
            "risk_profile": "conservative",
        },
        "expected_wr": 0.73,
        "expected_sharpe": 2.80,
        "rationale": (
            "RSI-2 (75.7%), Keltner (67.6%), Bollinger (60.7%) — requiring "
            "2-of-3 agreement via CONSENSUS_75 filters noise while keeping "
            "enough signal frequency."
        ),
    },
    {
        "name": "FearGreed_Carter_Breakout",
        "combination_logic": "sequential",
        "components": ["fear_greed_contrarian", "carter_squeeze_breakout"],
        "description": "Buy extreme fear, then wait for squeeze breakout confirmation",
        "genes": {
            "fg_threshold": 15,
            "squeeze_length": 20,
            "squeeze_mult_bb": 2.0,
            "squeeze_mult_kc": 1.5,
            "timeframe": "1d",
            "tp_mult": 3.5,
            "sl_mult": 1.5,
            "risk_profile": "aggressive",
        },
        "expected_wr": 0.65,
        "expected_sharpe": 4.60,
        "rationale": (
            "F&G contrarian (59.3% / 4.05 Sharpe) identifies macro fear; "
            "Carter squeeze (66.7% / 5.33 Sharpe) confirms volatility "
            "expansion. Sequential: fear first, breakout confirms."
        ),
    },
]

# ===========================================================================
# Expansion Matrix
# ===========================================================================
EXPANSION_PAIRS: List[str] = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT",
    "DOGEUSDT", "LINKUSDT", "ATOMUSDT",
]

EXPANSION_TIMEFRAMES: List[str] = ["1h", "4h", "1d"]

BASE_STRATEGIES_FOR_EXPANSION: List[Dict[str, Any]] = [
    {
        "name": "connors_rsi2",
        "primary_indicator": "RSI",
        "entry_logic": "rsi2_below_5",
        "exit_logic": "rsi2_above_95",
        "risk_profile": "moderate",
        "rsi_period": 2,
        "rsi_entry": 5,
        "rsi_exit": 95,
        "streak_period": 3,
        "proven_wr": 0.757,
        "proven_sharpe": 4.84,
    },
    {
        "name": "keltner_mean_reversion",
        "primary_indicator": "Keltner",
        "entry_logic": "price_below_lower_keltner",
        "exit_logic": "price_crosses_keltner_mid",
        "risk_profile": "moderate",
        "keltner_period": 20,
        "keltner_atr_mult": 2.0,
        "proven_wr": 0.676,
        "proven_sharpe": 2.06,
    },
    {
        "name": "carter_squeeze_breakout",
        "primary_indicator": "TTM_Squeeze",
        "entry_logic": "squeeze_fire_long",
        "exit_logic": "momentum_reversal",
        "risk_profile": "moderate",
        "squeeze_length": 20,
        "squeeze_mult_bb": 2.0,
        "squeeze_mult_kc": 1.5,
        "proven_wr": 0.667,
        "proven_sharpe": 5.33,
    },
    {
        "name": "levine_adaptive_lookback",
        "primary_indicator": "Adaptive_Momentum",
        "entry_logic": "adaptive_breakout",
        "exit_logic": "adaptive_trailing_stop",
        "risk_profile": "moderate",
        "lookback_min": 5,
        "lookback_max": 50,
        "adapt_period": 100,
        "proven_wr": 0.616,
        "proven_sharpe": 7.57,
    },
    {
        "name": "consecutive_down_rsi",
        "primary_indicator": "RSI",
        "entry_logic": "consecutive_down_candles_rsi_oversold",
        "exit_logic": "rsi_recovery",
        "risk_profile": "moderate",
        "consec_candles": 3,
        "rsi_period": 2,
        "rsi_threshold": 10,
        "proven_wr": 0.743,
        "proven_sharpe": 1.76,
    },
    {
        "name": "bollinger_mean_reversion",
        "primary_indicator": "Bollinger",
        "entry_logic": "price_below_lower_bb",
        "exit_logic": "price_crosses_bb_mid",
        "risk_profile": "moderate",
        "bb_period": 20,
        "bb_std": 2.0,
        "proven_wr": 0.607,
        "proven_sharpe": 0.72,
    },
    {
        "name": "rsi2_bb_squeeze",
        "primary_indicator": "RSI_BB",
        "entry_logic": "rsi2_oversold_bb_squeeze",
        "exit_logic": "rsi2_recovery_or_bb_expansion",
        "risk_profile": "moderate",
        "rsi_period": 2,
        "rsi_threshold": 10,
        "bb_period": 20,
        "bb_std": 2.0,
        "proven_wr": 0.671,
        "proven_sharpe": 1.11,
    },
    {
        "name": "fear_greed_contrarian",
        "primary_indicator": "Fear_Greed_Index",
        "entry_logic": "fg_extreme_fear",
        "exit_logic": "fg_greed_zone",
        "risk_profile": "moderate",
        "fg_buy_threshold": 20,
        "fg_sell_threshold": 75,
        "proven_wr": 0.593,
        "proven_sharpe": 4.05,
    },
]

# ===========================================================================
# Helper: deterministic strategy ID
# ===========================================================================

def _strategy_id(name: str, symbol: str = "", timeframe: str = "") -> str:
    """Generate a deterministic MD5-based strategy ID."""
    raw = f"{name}|{symbol}|{timeframe}"
    return hashlib.md5(raw.encode()).hexdigest()


# ===========================================================================
# Database helpers
# ===========================================================================

def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    """Create tables if they don't exist."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS factory_strategies (
            strategy_id   TEXT PRIMARY KEY,
            name          TEXT,
            category      TEXT,
            combination_logic TEXT,
            components    TEXT,
            symbol        TEXT,
            timeframe     TEXT,
            genes         TEXT,
            tier          TEXT DEFAULT 'INCUBATOR',
            forward_trades   INTEGER DEFAULT 0,
            forward_wins     INTEGER DEFAULT 0,
            forward_losses   INTEGER DEFAULT 0,
            forward_wr       REAL DEFAULT 0,
            forward_sharpe   REAL DEFAULT 0,
            forward_pnl      REAL DEFAULT 0,
            expected_wr      REAL DEFAULT 0,
            expected_sharpe  REAL DEFAULT 0,
            created_at       TEXT,
            last_evaluated   TEXT,
            last_promoted    TEXT,
            last_signal      TEXT
        );

        CREATE TABLE IF NOT EXISTS factory_trades (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy_id   TEXT,
            symbol        TEXT,
            direction     TEXT,
            entry_price   REAL,
            tp_price      REAL,
            sl_price      REAL,
            entry_time    TEXT,
            exit_time     TEXT,
            status        TEXT DEFAULT 'ACTIVE',
            exit_price    REAL,
            pnl_pct       REAL,
            created_at    TEXT,
            FOREIGN KEY (strategy_id) REFERENCES factory_strategies(strategy_id)
        );
    """)
    conn.commit()
    conn.close()
    logger.info("Database initialized at %s", DB_PATH)


# ===========================================================================
# Registration functions
# ===========================================================================

def register_combo_strategies() -> List[str]:
    """Register the 8 combo DNA bundles. Idempotent (INSERT OR IGNORE)."""
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    registered: List[str] = []

    for combo in COMBO_DEFINITIONS:
        sid = _strategy_id(combo["name"])
        conn.execute(
            """
            INSERT OR IGNORE INTO factory_strategies
                (strategy_id, name, category, combination_logic, components,
                 symbol, timeframe, genes, expected_wr, expected_sharpe, created_at)
            VALUES (?, ?, 'combo', ?, ?, '', ?, ?, ?, ?, ?)
            """,
            (
                sid,
                combo["name"],
                combo["combination_logic"],
                json.dumps(combo["components"]),
                combo["genes"].get("timeframe", "4h"),
                json.dumps(combo["genes"]),
                combo["expected_wr"],
                combo["expected_sharpe"],
                now,
            ),
        )
        registered.append(combo["name"])

    conn.commit()
    conn.close()
    logger.info("Registered %d combo strategies", len(registered))
    return registered


def register_expansion_matrix() -> int:
    """Register 168 expansion cells (8 base x 7 pairs x 3 TFs). Idempotent."""
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    count = 0

    for strat in BASE_STRATEGIES_FOR_EXPANSION:
        for pair in EXPANSION_PAIRS:
            for tf in EXPANSION_TIMEFRAMES:
                sid = _strategy_id(strat["name"], pair, tf)
                genes = {
                    k: v
                    for k, v in strat.items()
                    if k not in ("name", "proven_wr", "proven_sharpe")
                }
                genes["timeframe"] = tf
                genes["symbol"] = pair

                conn.execute(
                    """
                    INSERT OR IGNORE INTO factory_strategies
                        (strategy_id, name, category, combination_logic, components,
                         symbol, timeframe, genes, expected_wr, expected_sharpe, created_at)
                    VALUES (?, ?, 'expansion', 'single', '[]', ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sid,
                        f"{strat['name']}_{pair}_{tf}",
                        pair,
                        tf,
                        json.dumps(genes),
                        strat["proven_wr"],
                        strat["proven_sharpe"],
                        now,
                    ),
                )
                count += 1

    conn.commit()
    conn.close()
    logger.info("Registered %d expansion cells", count)
    return count


# ===========================================================================
# Query helpers
# ===========================================================================

def get_all_strategies() -> List[Dict[str, Any]]:
    """Return every strategy from the DB as a list of dicts."""
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM factory_strategies").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_strategies_by_tier(tier: str) -> List[Dict[str, Any]]:
    """Return strategies filtered by tier (INCUBATOR, CONTENDER, PROVEN, etc.)."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM factory_strategies WHERE tier = ?", (tier,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ===========================================================================
# Trade recording
# ===========================================================================

def record_trade(
    strategy_id: str,
    symbol: str,
    direction: str,
    entry_price: float,
    tp_price: float,
    sl_price: float,
) -> Optional[int]:
    """
    Record a new trade for a strategy. Deduplicates: skips if an ACTIVE
    trade already exists for the same strategy_id + symbol + direction.
    Returns the trade id or None if deduplicated.
    """
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()

    existing = conn.execute(
        """
        SELECT id FROM factory_trades
        WHERE strategy_id = ? AND symbol = ? AND direction = ? AND status = 'ACTIVE'
        """,
        (strategy_id, symbol, direction),
    ).fetchone()

    if existing:
        conn.close()
        return None

    cur = conn.execute(
        """
        INSERT INTO factory_trades
            (strategy_id, symbol, direction, entry_price, tp_price, sl_price,
             entry_time, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?)
        """,
        (strategy_id, symbol, direction, entry_price, tp_price, sl_price, now, now),
    )
    trade_id = cur.lastrowid
    conn.commit()
    conn.close()
    return trade_id


# ===========================================================================
# JSON export
# ===========================================================================

def export_registry_json() -> str:
    """Export full registry to JSON with summary. Returns path written."""
    strategies = get_all_strategies()

    combos = [s for s in strategies if s["category"] == "combo"]
    expansions = [s for s in strategies if s["category"] == "expansion"]

    # Tier counts
    tier_counts: Dict[str, int] = {}
    for s in strategies:
        t = s.get("tier", "INCUBATOR")
        tier_counts[t] = tier_counts.get(t, 0) + 1

    registry = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_strategies": len(strategies),
            "combo_count": len(combos),
            "expansion_count": len(expansions),
            "tier_distribution": tier_counts,
            "expansion_pairs": EXPANSION_PAIRS,
            "expansion_timeframes": EXPANSION_TIMEFRAMES,
        },
        "combo_strategies": combos,
        "expansion_strategies": expansions,
    }

    REGISTRY_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(REGISTRY_JSON, "w") as f:
        json.dump(registry, f, indent=2, default=str)

    logger.info("Exported registry to %s (%d strategies)", REGISTRY_JSON, len(strategies))
    return str(REGISTRY_JSON)


# ===========================================================================
# CLI
# ===========================================================================

def _print_stats() -> None:
    strategies = get_all_strategies()
    combos = [s for s in strategies if s["category"] == "combo"]
    expansions = [s for s in strategies if s["category"] == "expansion"]

    print("=" * 60)
    print("  DNA Strategy Factory  —  Summary")
    print("=" * 60)
    print(f"  Total strategies : {len(strategies)}")
    print(f"  Combo bundles    : {len(combos)}")
    print(f"  Expansion cells  : {len(expansions)}")
    print()

    if combos:
        print("  COMBO BUNDLES:")
        for c in combos:
            print(
                f"    {c['name']:<35s}  logic={c['combination_logic']:<12s}  "
                f"E[WR]={c['expected_wr']:.0%}  E[Sharpe]={c['expected_sharpe']:.2f}"
            )
        print()

    # Expansion summary by pair
    if expansions:
        pair_counts: Dict[str, int] = {}
        for e in expansions:
            pair_counts[e["symbol"]] = pair_counts.get(e["symbol"], 0) + 1
        print("  EXPANSION MATRIX:")
        for pair, cnt in sorted(pair_counts.items()):
            print(f"    {pair:<12s}  {cnt} cells")
        print()

    # Tier distribution
    tier_counts: Dict[str, int] = {}
    for s in strategies:
        t = s.get("tier", "INCUBATOR")
        tier_counts[t] = tier_counts.get(t, 0) + 1
    print("  TIER DISTRIBUTION:")
    for tier, cnt in sorted(tier_counts.items()):
        print(f"    {tier:<15s}  {cnt}")
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="DNA Strategy Factory")
    parser.add_argument("--register", action="store_true", help="Register all strategies")
    parser.add_argument("--export", action="store_true", help="Export JSON registry")
    parser.add_argument("--stats", action="store_true", help="Print summary stats")
    args = parser.parse_args()

    # Default: do everything
    do_all = not (args.register or args.export or args.stats)

    init_db()

    if args.register or do_all:
        combos = register_combo_strategies()
        print(f"Registered {len(combos)} combo strategies")
        cells = register_expansion_matrix()
        print(f"Registered {cells} expansion cells")

    if args.export or do_all:
        path = export_registry_json()
        print(f"Exported registry to {path}")

    if args.stats or do_all:
        _print_stats()


if __name__ == "__main__":
    main()
