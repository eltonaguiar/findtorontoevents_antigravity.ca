# DNA Strategy Factory + Progressive Promotion Pipeline — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create 8 combo DNA strategies from proven winners, expand them across 7 crypto pairs × 3 timeframes, and build a progressive promotion pipeline (INCUBATOR → SANDBOX → FRESH_PICKS → DNA_MASTER) with Discord notifications.

**Architecture:** Three new files — `genome/dna_strategy_factory.py` (strategy creation + expansion matrix), `genome/progressive_promotion.py` (tier evaluation + Discord routing), and workflow updates. Uses existing `genome/dna_engine.py` StrategyDNA dataclass, `bundle_baby_system.py` BundleBaby, and `cross_aggregation/dna_master_tracker.py` for persistence.

**Tech Stack:** Python 3.10+, SQLite, numpy/pandas, Discord webhooks, GitHub Actions

---

### Task 1: Create `genome/dna_strategy_factory.py` — Combo DNA Bundle Definitions

**Files:**
- Create: `genome/dna_strategy_factory.py`

**Step 1: Write the combo strategy definitions**

This file defines all 8 combo DNA bundles and the expansion matrix. It uses `create_strategy_dna` from `genome/dna_engine.py` and `CombinationLogic` enum.

```python
#!/usr/bin/env python3
"""
DNA Strategy Factory — Creates combo bundles from proven winners + asset-timeframe expansion
============================================================================================

Workstream A: 8 combo DNA strategies combining statistically proven signals
Workstream B: Expansion matrix — top strategies × 7 pairs × 3 timeframes = 168 cells
"""

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from genome.dna_engine import (
    StrategyDNA, CombinationLogic, MarketRegime, create_strategy_dna
)

REPO_ROOT = Path(__file__).resolve().parent.parent
FACTORY_DB = REPO_ROOT / "battleground" / "data" / "dna_factory.db"
FACTORY_JSON = REPO_ROOT / "battleground" / "data" / "dna_factory_registry.json"

# ──────────────────────────────────────────────────────────────────
# Expansion matrix dimensions
# ──────────────────────────────────────────────────────────────────
EXPANSION_PAIRS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "DOGEUSDT", "LINKUSDT", "ATOMUSDT"
]
EXPANSION_TIMEFRAMES = ["1h", "4h", "1d"]

# ──────────────────────────────────────────────────────────────────
# Part A: 8 Combo DNA Bundles (proven winner combinations)
# ──────────────────────────────────────────────────────────────────

COMBO_DEFINITIONS: List[Dict] = [
    {
        "name": "RSI2_FearGreed_Confluence",
        "combination_logic": "and",
        "components": ["connors_rsi2_mean_reversion", "fear_greed_contrarian"],
        "description": "Buy only when BOTH RSI-2 oversold AND Fear&Greed <= 20",
        "genes": {
            "primary_indicator": "RSI",
            "secondary_indicator": "FearGreed",
            "entry_logic": "rsi_oversold",
            "exit_logic": "rsi_overbought",
            "risk_profile": "moderate",
            "rsi_period": 2,
            "rsi_oversold": 5,
            "rsi_overbought": 65,
            "fg_buy_threshold": 20,
            "sma_period": 200,
            "tp_atr_mult": 3.0,
            "sl_atr_mult": 2.0,
            "max_hold_bars": 30,
        },
        "expected_wr": 72.0,  # RSI-2 75% × F&G 59% confluence should improve precision
        "expected_sharpe": 3.5,
        "rationale": "RSI-2 proven 75% WR (p<0.001), F&G proven 59% WR Sharpe 4.05. AND logic = fewer trades, higher quality.",
    },
    {
        "name": "Keltner_RSI2_DoubleBottom",
        "combination_logic": "sequential",
        "components": ["keltner_mean_reversion", "connors_rsi2_mean_reversion"],
        "description": "Keltner band touch triggers watchlist, RSI-2 < 5 confirms entry",
        "genes": {
            "primary_indicator": "Keltner",
            "secondary_indicator": "RSI",
            "entry_logic": "mean_reversion",
            "exit_logic": "rsi_overbought",
            "risk_profile": "moderate",
            "keltner_period": 20,
            "keltner_atr_mult": 2.0,
            "rsi_period": 2,
            "rsi_entry": 5,
            "rsi_exit": 65,
            "tp_atr_mult": 2.5,
            "sl_atr_mult": 1.5,
        },
        "expected_wr": 70.0,
        "expected_sharpe": 2.5,
        "rationale": "Keltner MR Sharpe 2.06 (67.6% WR) + RSI-2 confirmation. Sequential = primary triggers, secondary confirms.",
    },
    {
        "name": "Carter_Keltner_VolSqueeze",
        "combination_logic": "weighted",
        "components": ["carter_squeeze_breakout", "keltner_mean_reversion"],
        "description": "TTM Squeeze breakout weighted with Keltner band mean-reversion filter",
        "genes": {
            "primary_indicator": "Bollinger",
            "secondary_indicator": "Keltner",
            "entry_logic": "breakout",
            "exit_logic": "trailing_stop",
            "risk_profile": "moderate",
            "bb_period": 20,
            "bb_std": 2.0,
            "keltner_period": 20,
            "keltner_atr_mult": 1.5,
            "squeeze_momentum_threshold": 0,
            "tp_atr_mult": 3.0,
            "sl_atr_mult": 1.5,
        },
        "expected_wr": 65.0,
        "expected_sharpe": 4.0,
        "rationale": "Carter Squeeze Sharpe 5.33 + Keltner MR Sharpe 2.06. Weighted voting avoids false breakouts.",
    },
    {
        "name": "Levine_Momentum_FG",
        "combination_logic": "majority",
        "components": ["levine_adaptive_lookback_momentum", "fear_greed_contrarian"],
        "description": "Adaptive lookback momentum + Fear&Greed contrarian, majority vote",
        "genes": {
            "primary_indicator": "Momentum",
            "secondary_indicator": "FearGreed",
            "entry_logic": "momentum",
            "exit_logic": "trailing_stop",
            "risk_profile": "moderate",
            "lookback_min": 10,
            "lookback_max": 60,
            "fg_buy_threshold": 25,
            "fg_sell_threshold": 75,
            "tp_atr_mult": 3.5,
            "sl_atr_mult": 1.5,
        },
        "expected_wr": 63.0,
        "expected_sharpe": 5.0,
        "rationale": "Levine Adaptive Sharpe 7.57 IS. F&G macro filter adds regime awareness.",
    },
    {
        "name": "ConsecDown_Bollinger_Trap",
        "combination_logic": "and",
        "components": ["consecutive_down_rsi", "bollinger_mean_reversion"],
        "description": "3+ consecutive red candles AND Bollinger lower band touch",
        "genes": {
            "primary_indicator": "RSI",
            "secondary_indicator": "Bollinger",
            "entry_logic": "mean_reversion",
            "exit_logic": "rsi_overbought",
            "risk_profile": "moderate",
            "consec_down_min": 3,
            "rsi_period": 2,
            "rsi_entry": 10,
            "bb_period": 20,
            "bb_std": 2.0,
            "tp_atr_mult": 2.5,
            "sl_atr_mult": 1.5,
        },
        "expected_wr": 73.0,
        "expected_sharpe": 2.0,
        "rationale": "Consecutive Down 74.3% WR + Bollinger MR 60.7% WR. AND = both must fire = high-conviction setups only.",
    },
    {
        "name": "BTCDom_RSI2_Rotation",
        "combination_logic": "sequential",
        "components": ["btc_dominance_rotation", "connors_rsi2_mean_reversion"],
        "description": "BTC Dominance signals alt season → RSI-2 gives precise entry timing",
        "genes": {
            "primary_indicator": "BTCDominance",
            "secondary_indicator": "RSI",
            "entry_logic": "momentum",
            "exit_logic": "rsi_overbought",
            "risk_profile": "moderate",
            "btc_dom_threshold": 0.50,
            "btc_dom_lookback": 14,
            "rsi_period": 2,
            "rsi_entry": 5,
            "rsi_exit": 65,
            "tp_atr_mult": 3.0,
            "sl_atr_mult": 2.0,
        },
        "expected_wr": 60.0,
        "expected_sharpe": 2.0,
        "rationale": "BTC Dom Combined Sharpe 1.62 (1,085 trades p<0.001) + RSI-2 precision entry.",
    },
    {
        "name": "TripleMR_Confluence",
        "combination_logic": "consensus_75",
        "components": ["connors_rsi2_mean_reversion", "keltner_mean_reversion", "bollinger_mean_reversion"],
        "description": "3 independent mean-reversion signals, 75% must agree (2 of 3)",
        "genes": {
            "primary_indicator": "RSI",
            "secondary_indicator": "Keltner",
            "tertiary_indicator": "Bollinger",
            "entry_logic": "mean_reversion",
            "exit_logic": "rsi_overbought",
            "risk_profile": "moderate",
            "rsi_period": 2,
            "rsi_entry": 10,
            "keltner_period": 20,
            "keltner_atr_mult": 2.0,
            "bb_period": 20,
            "bb_std": 2.0,
            "tp_atr_mult": 2.5,
            "sl_atr_mult": 1.5,
        },
        "expected_wr": 68.0,
        "expected_sharpe": 2.5,
        "rationale": "Three independent MR signals reduce false positives. CONSENSUS_75 = 2 of 3 must agree.",
    },
    {
        "name": "FearGreed_Carter_Breakout",
        "combination_logic": "sequential",
        "components": ["fear_greed_contrarian", "carter_squeeze_breakout"],
        "description": "Wait for F&G extreme fear, then enter on TTM Squeeze breakout",
        "genes": {
            "primary_indicator": "FearGreed",
            "secondary_indicator": "Bollinger",
            "entry_logic": "breakout",
            "exit_logic": "trailing_stop",
            "risk_profile": "moderate",
            "fg_buy_threshold": 25,
            "bb_period": 20,
            "bb_std": 2.0,
            "keltner_period": 20,
            "keltner_atr_mult": 1.5,
            "tp_atr_mult": 4.0,
            "sl_atr_mult": 2.0,
            "max_hold_bars": 48,
        },
        "expected_wr": 65.0,
        "expected_sharpe": 4.5,
        "rationale": "F&G Sharpe 4.05 provides macro timing. Carter Sharpe 5.33 provides precise breakout entry. Sequential = wait for fear, then squeeze.",
    },
]

# ──────────────────────────────────────────────────────────────────
# Part B: Proven base strategies for expansion
# ──────────────────────────────────────────────────────────────────

BASE_STRATEGIES_FOR_EXPANSION = [
    {
        "name": "connors_rsi2",
        "primary_indicator": "RSI",
        "entry_logic": "rsi_oversold",
        "exit_logic": "rsi_overbought",
        "risk_profile": "moderate",
        "rsi_period": 2, "rsi_oversold": 5, "rsi_overbought": 65,
        "sma_period": 200, "tp_atr_mult": 3.0, "sl_atr_mult": 2.0,
        "proven_wr": 75.7, "proven_sharpe": 4.84,
    },
    {
        "name": "keltner_mean_reversion",
        "primary_indicator": "Keltner",
        "entry_logic": "mean_reversion",
        "exit_logic": "take_profit",
        "risk_profile": "moderate",
        "keltner_period": 20, "keltner_atr_mult": 2.0,
        "tp_atr_mult": 2.5, "sl_atr_mult": 1.5,
        "proven_wr": 67.6, "proven_sharpe": 2.06,
    },
    {
        "name": "carter_squeeze_breakout",
        "primary_indicator": "Bollinger",
        "entry_logic": "breakout",
        "exit_logic": "trailing_stop",
        "risk_profile": "moderate",
        "bb_period": 20, "bb_std": 2.0, "keltner_period": 20,
        "keltner_atr_mult": 1.5, "tp_atr_mult": 3.0, "sl_atr_mult": 1.5,
        "proven_wr": 66.7, "proven_sharpe": 5.33,
    },
    {
        "name": "levine_adaptive_lookback",
        "primary_indicator": "Momentum",
        "entry_logic": "momentum",
        "exit_logic": "trailing_stop",
        "risk_profile": "moderate",
        "lookback_min": 10, "lookback_max": 60,
        "tp_atr_mult": 3.5, "sl_atr_mult": 1.5,
        "proven_wr": 61.6, "proven_sharpe": 7.57,
    },
    {
        "name": "consecutive_down_rsi",
        "primary_indicator": "RSI",
        "entry_logic": "mean_reversion",
        "exit_logic": "rsi_overbought",
        "risk_profile": "moderate",
        "consec_down_min": 3, "rsi_period": 2, "rsi_entry": 10,
        "tp_atr_mult": 2.5, "sl_atr_mult": 1.5,
        "proven_wr": 74.3, "proven_sharpe": 1.76,
    },
    {
        "name": "bollinger_mean_reversion",
        "primary_indicator": "Bollinger",
        "entry_logic": "mean_reversion",
        "exit_logic": "take_profit",
        "risk_profile": "moderate",
        "bb_period": 20, "bb_std": 2.0,
        "tp_atr_mult": 2.0, "sl_atr_mult": 1.5,
        "proven_wr": 60.7, "proven_sharpe": 0.72,
    },
    {
        "name": "rsi2_bb_squeeze",
        "primary_indicator": "RSI",
        "secondary_indicator": "Bollinger",
        "entry_logic": "mean_reversion",
        "exit_logic": "rsi_overbought",
        "risk_profile": "moderate",
        "rsi_period": 2, "bb_period": 20, "bb_std": 2.0,
        "tp_atr_mult": 2.5, "sl_atr_mult": 1.5,
        "proven_wr": 67.1, "proven_sharpe": 1.11,
    },
    {
        "name": "fear_greed_contrarian",
        "primary_indicator": "FearGreed",
        "entry_logic": "momentum",
        "exit_logic": "time_exit",
        "risk_profile": "moderate",
        "fg_buy_threshold": 20, "hold_days": 30,
        "tp_atr_mult": 3.0, "sl_atr_mult": 2.0,
        "proven_wr": 59.3, "proven_sharpe": 4.05,
    },
]


# ──────────────────────────────────────────────────────────────────
# Factory functions
# ──────────────────────────────────────────────────────────────────

def _strategy_id(name: str, symbol: str = "", timeframe: str = "") -> str:
    """Generate deterministic strategy ID from name+symbol+timeframe."""
    raw = f"{name}|{symbol}|{timeframe}"
    return f"dna_{hashlib.md5(raw.encode()).hexdigest()[:12]}"


def init_db():
    """Create factory registry table."""
    FACTORY_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(FACTORY_DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS factory_strategies (
            strategy_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            combination_logic TEXT,
            components TEXT,
            symbol TEXT DEFAULT '',
            timeframe TEXT DEFAULT '',
            genes TEXT NOT NULL,
            tier TEXT DEFAULT 'INCUBATOR',
            forward_trades INTEGER DEFAULT 0,
            forward_wins INTEGER DEFAULT 0,
            forward_losses INTEGER DEFAULT 0,
            forward_wr REAL DEFAULT 0,
            forward_sharpe REAL DEFAULT 0,
            forward_pnl REAL DEFAULT 0,
            expected_wr REAL DEFAULT 0,
            expected_sharpe REAL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_evaluated TEXT,
            last_promoted TEXT,
            last_signal TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS factory_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            direction TEXT NOT NULL,
            entry_price REAL NOT NULL,
            tp_price REAL NOT NULL,
            sl_price REAL NOT NULL,
            entry_time TEXT NOT NULL,
            exit_time TEXT,
            status TEXT DEFAULT 'ACTIVE',
            exit_price REAL,
            pnl_pct REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (strategy_id) REFERENCES factory_strategies(strategy_id)
        )
    """)
    conn.commit()
    conn.close()


def register_combo_strategies() -> List[Dict]:
    """Register all 8 combo DNA bundles. Idempotent — skips if already exists."""
    init_db()
    conn = sqlite3.connect(str(FACTORY_DB))
    registered = []

    for combo in COMBO_DEFINITIONS:
        sid = _strategy_id(combo["name"])
        existing = conn.execute(
            "SELECT strategy_id FROM factory_strategies WHERE strategy_id = ?", (sid,)
        ).fetchone()
        if existing:
            continue

        conn.execute(
            """INSERT INTO factory_strategies
               (strategy_id, name, category, combination_logic, components,
                genes, expected_wr, expected_sharpe, tier)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'INCUBATOR')""",
            (sid, combo["name"], "combo",
             combo["combination_logic"],
             json.dumps(combo["components"]),
             json.dumps(combo["genes"]),
             combo.get("expected_wr", 0),
             combo.get("expected_sharpe", 0))
        )
        registered.append({"strategy_id": sid, "name": combo["name"], "type": "combo"})

    conn.commit()
    conn.close()
    print(f"[Factory] Registered {len(registered)} new combo strategies")
    return registered


def register_expansion_matrix() -> List[Dict]:
    """Register all asset-timeframe expansion cells. Idempotent."""
    init_db()
    conn = sqlite3.connect(str(FACTORY_DB))
    registered = []

    for base in BASE_STRATEGIES_FOR_EXPANSION:
        base_name = base["name"]
        for symbol in EXPANSION_PAIRS:
            for tf in EXPANSION_TIMEFRAMES:
                cell_name = f"{base_name}__{symbol}__{tf}"
                sid = _strategy_id(base_name, symbol, tf)

                existing = conn.execute(
                    "SELECT strategy_id FROM factory_strategies WHERE strategy_id = ?", (sid,)
                ).fetchone()
                if existing:
                    continue

                genes = {k: v for k, v in base.items()
                         if k not in ("name", "proven_wr", "proven_sharpe")}
                genes["timeframe"] = tf
                genes["symbol"] = symbol

                conn.execute(
                    """INSERT INTO factory_strategies
                       (strategy_id, name, category, symbol, timeframe,
                        genes, expected_wr, expected_sharpe, tier)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'INCUBATOR')""",
                    (sid, cell_name, "expansion", symbol, tf,
                     json.dumps(genes),
                     base.get("proven_wr", 0),
                     base.get("proven_sharpe", 0))
                )
                registered.append({
                    "strategy_id": sid, "name": cell_name,
                    "type": "expansion", "symbol": symbol, "timeframe": tf,
                })

    conn.commit()
    conn.close()
    print(f"[Factory] Registered {len(registered)} new expansion cells")
    return registered


def get_all_strategies() -> List[Dict]:
    """Get all registered factory strategies with current metrics."""
    init_db()
    conn = sqlite3.connect(str(FACTORY_DB))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM factory_strategies ORDER BY tier, forward_wr DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_strategies_by_tier(tier: str) -> List[Dict]:
    """Get strategies in a specific tier."""
    init_db()
    conn = sqlite3.connect(str(FACTORY_DB))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM factory_strategies WHERE tier = ? ORDER BY forward_wr DESC",
        (tier,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def record_trade(strategy_id: str, symbol: str, direction: str,
                 entry_price: float, tp_price: float, sl_price: float) -> Optional[int]:
    """Record a new trade for a factory strategy."""
    init_db()
    conn = sqlite3.connect(str(FACTORY_DB))

    # Dedup: skip if same strategy+symbol+direction already active
    existing = conn.execute(
        "SELECT id FROM factory_trades WHERE strategy_id=? AND symbol=? AND direction=? AND status='ACTIVE'",
        (strategy_id, symbol, direction)
    ).fetchone()
    if existing:
        conn.close()
        return None

    now = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        """INSERT INTO factory_trades
           (strategy_id, symbol, direction, entry_price, tp_price, sl_price, entry_time)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (strategy_id, symbol, direction, entry_price, tp_price, sl_price, now)
    )
    trade_id = cur.lastrowid
    conn.commit()
    conn.close()
    return trade_id


def export_registry_json():
    """Export full registry to JSON for dashboard consumption."""
    strategies = get_all_strategies()
    summary = {
        "total": len(strategies),
        "by_tier": {},
        "by_category": {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    for s in strategies:
        tier = s.get("tier", "INCUBATOR")
        cat = s.get("category", "unknown")
        summary["by_tier"][tier] = summary["by_tier"].get(tier, 0) + 1
        summary["by_category"][cat] = summary["by_category"].get(cat, 0) + 1

    output = {"summary": summary, "strategies": strategies}
    FACTORY_JSON.parent.mkdir(parents=True, exist_ok=True)
    FACTORY_JSON.write_text(json.dumps(output, indent=2, default=str))
    print(f"[Factory] Exported {len(strategies)} strategies to {FACTORY_JSON}")


# ──────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="DNA Strategy Factory")
    parser.add_argument("--register", action="store_true", help="Register all strategies (combos + expansion)")
    parser.add_argument("--export", action="store_true", help="Export registry to JSON")
    parser.add_argument("--stats", action="store_true", help="Print summary stats")
    args = parser.parse_args()

    if args.register or not any(vars(args).values()):
        combos = register_combo_strategies()
        expansions = register_expansion_matrix()
        print(f"\n[Factory] Total new: {len(combos)} combos + {len(expansions)} expansions")

    if args.export or not any(vars(args).values()):
        export_registry_json()

    if args.stats or not any(vars(args).values()):
        strats = get_all_strategies()
        tiers = {}
        for s in strats:
            t = s.get("tier", "INCUBATOR")
            tiers[t] = tiers.get(t, 0) + 1
        print(f"\n[Factory] Registry: {len(strats)} strategies")
        for t, c in sorted(tiers.items()):
            print(f"  {t}: {c}")
```

**Step 2: Run to verify it creates the registry**

Run: `cd /e/findtorontoevents_antigravity.ca && py genome/dna_strategy_factory.py --register --export --stats`
Expected: "Registered 8 new combo strategies" + "Registered 168 new expansion cells" + JSON exported

**Step 3: Commit**

```bash
git add genome/dna_strategy_factory.py battleground/data/dna_factory.db battleground/data/dna_factory_registry.json
git commit -m "feat: add DNA Strategy Factory with 8 combo bundles + 168 expansion cells"
```

---

### Task 2: Create `genome/progressive_promotion.py` — Tier Evaluation Engine

**Files:**
- Create: `genome/progressive_promotion.py`

**Step 1: Write the progressive promotion engine**

```python
#!/usr/bin/env python3
"""
Progressive Promotion Pipeline
==============================

Evaluates factory strategies and promotes/demotes based on forward performance:

  INCUBATOR  →  SANDBOX (10+ trades)
  SANDBOX    →  FRESH_PICKS (20+ trades, WR>=50%, Sharpe>=0.5)
  FRESH_PICKS → DNA_MASTER (30+ trades, WR>=55%, Sharpe>=1.5)

Demotions happen on rolling 20-trade window:
  DNA_MASTER  → FRESH_PICKS if WR<50% or Sharpe<1.0
  FRESH_PICKS → SANDBOX if WR<45% or Sharpe<0.3
  SANDBOX     → INCUBATOR if WR<40% over 20 trades
"""

import json
import math
import os
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
FACTORY_DB = REPO_ROOT / "battleground" / "data" / "dna_factory.db"

# Discord webhooks
WEBHOOK_SANDBOX = os.environ.get("DISCORD_WEBHOOK_SANDBOX", "")
WEBHOOK_FRESH = os.environ.get("DISCORD_WEBHOOK_URL", "")
WEBHOOK_MASTER = os.environ.get("DISCORD_WEBHOOK_DNA_MASTER", "")

EST = timezone(timedelta(hours=-5))

# ──────────────────────────────────────────────────────────────────
# Promotion / Demotion thresholds
# ──────────────────────────────────────────────────────────────────

PROMOTION_RULES = {
    "INCUBATOR_TO_SANDBOX": {
        "min_trades": 10,
    },
    "SANDBOX_TO_FRESH_PICKS": {
        "min_trades": 20,
        "min_wr": 50.0,
        "min_sharpe": 0.5,
    },
    "FRESH_PICKS_TO_DNA_MASTER": {
        "min_trades": 30,
        "min_wr": 55.0,
        "min_sharpe": 1.5,
    },
}

DEMOTION_RULES = {
    "DNA_MASTER_TO_FRESH_PICKS": {
        "rolling_window": 20,
        "max_wr": 50.0,
        "max_sharpe": 1.0,
    },
    "FRESH_PICKS_TO_SANDBOX": {
        "rolling_window": 20,
        "max_wr": 45.0,
        "max_sharpe": 0.3,
    },
    "SANDBOX_TO_INCUBATOR": {
        "rolling_window": 20,
        "max_wr": 40.0,
    },
}

# Discord embed colors
COLOR_GOLD = 0xFFD700
COLOR_GREEN = 0x22C55E
COLOR_RED = 0xEF4444
COLOR_BLUE = 0x3B82F6
COLOR_PURPLE = 0x8B5CF6

TIER_EMOJI = {
    "INCUBATOR": "\U0001f331",      # 🌱
    "SANDBOX": "\U0001f9ea",         # 🧪
    "FRESH_PICKS": "\U0001f4ca",     # 📊
    "DNA_MASTER": "\U0001f9ec",      # 🧬
}


def _compute_sharpe(pnl_list: List[float]) -> float:
    """Compute annualized Sharpe from list of trade PnL percentages."""
    if len(pnl_list) < 2:
        return 0.0
    mean_pnl = sum(pnl_list) / len(pnl_list)
    variance = sum((p - mean_pnl) ** 2 for p in pnl_list) / (len(pnl_list) - 1)
    std = math.sqrt(variance) if variance > 0 else 1e-10
    # Annualize assuming ~250 trading days / avg hold
    return (mean_pnl / std) * math.sqrt(252)


def _get_strategy_forward_stats(conn: sqlite3.Connection, strategy_id: str,
                                 rolling_window: int = 0) -> Dict:
    """Compute forward stats for a strategy from factory_trades."""
    if rolling_window > 0:
        rows = conn.execute(
            """SELECT pnl_pct, status FROM factory_trades
               WHERE strategy_id=? AND status IN ('WON','LOST')
               ORDER BY id DESC LIMIT ?""",
            (strategy_id, rolling_window)
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT pnl_pct, status FROM factory_trades
               WHERE strategy_id=? AND status IN ('WON','LOST')
               ORDER BY id""",
            (strategy_id,)
        ).fetchall()

    if not rows:
        return {"trades": 0, "wins": 0, "losses": 0, "wr": 0, "sharpe": 0, "pnl": 0}

    wins = sum(1 for r in rows if r[1] == "WON")
    losses = sum(1 for r in rows if r[1] == "LOST")
    total = wins + losses
    wr = (wins / total * 100) if total else 0
    pnl_list = [r[0] for r in rows if r[0] is not None]
    sharpe = _compute_sharpe(pnl_list) if pnl_list else 0
    total_pnl = sum(pnl_list) if pnl_list else 0

    return {
        "trades": total, "wins": wins, "losses": losses,
        "wr": round(wr, 1), "sharpe": round(sharpe, 2),
        "pnl": round(total_pnl, 2),
    }


def evaluate_promotions() -> List[Dict]:
    """Evaluate all strategies for promotion/demotion. Returns list of tier changes."""
    conn = sqlite3.connect(str(FACTORY_DB))
    conn.row_factory = sqlite3.Row
    strategies = conn.execute("SELECT * FROM factory_strategies").fetchall()

    changes = []
    now = datetime.now(timezone.utc).isoformat()

    for strat in strategies:
        sid = strat["strategy_id"]
        current_tier = strat["tier"]
        stats = _get_strategy_forward_stats(conn, sid)

        # Update forward metrics in DB
        conn.execute(
            """UPDATE factory_strategies
               SET forward_trades=?, forward_wins=?, forward_losses=?,
                   forward_wr=?, forward_sharpe=?, forward_pnl=?,
                   last_evaluated=?
               WHERE strategy_id=?""",
            (stats["trades"], stats["wins"], stats["losses"],
             stats["wr"], stats["sharpe"], stats["pnl"], now, sid)
        )

        new_tier = current_tier

        # Check promotions (only promote UP one tier at a time)
        if current_tier == "INCUBATOR":
            rules = PROMOTION_RULES["INCUBATOR_TO_SANDBOX"]
            if stats["trades"] >= rules["min_trades"]:
                new_tier = "SANDBOX"

        elif current_tier == "SANDBOX":
            rules = PROMOTION_RULES["SANDBOX_TO_FRESH_PICKS"]
            if (stats["trades"] >= rules["min_trades"]
                    and stats["wr"] >= rules["min_wr"]
                    and stats["sharpe"] >= rules["min_sharpe"]):
                new_tier = "FRESH_PICKS"

            # Check demotion
            rolling = _get_strategy_forward_stats(conn, sid, rolling_window=20)
            d_rules = DEMOTION_RULES["SANDBOX_TO_INCUBATOR"]
            if rolling["trades"] >= d_rules["rolling_window"] and rolling["wr"] < d_rules["max_wr"]:
                new_tier = "INCUBATOR"

        elif current_tier == "FRESH_PICKS":
            rules = PROMOTION_RULES["FRESH_PICKS_TO_DNA_MASTER"]
            if (stats["trades"] >= rules["min_trades"]
                    and stats["wr"] >= rules["min_wr"]
                    and stats["sharpe"] >= rules["min_sharpe"]):
                new_tier = "DNA_MASTER"

            # Check demotion
            rolling = _get_strategy_forward_stats(conn, sid, rolling_window=20)
            d_rules = DEMOTION_RULES["FRESH_PICKS_TO_SANDBOX"]
            if rolling["trades"] >= d_rules["rolling_window"]:
                if rolling["wr"] < d_rules["max_wr"] or rolling["sharpe"] < d_rules["max_sharpe"]:
                    new_tier = "SANDBOX"

        elif current_tier == "DNA_MASTER":
            rolling = _get_strategy_forward_stats(conn, sid, rolling_window=20)
            d_rules = DEMOTION_RULES["DNA_MASTER_TO_FRESH_PICKS"]
            if rolling["trades"] >= d_rules["rolling_window"]:
                if rolling["wr"] < d_rules["max_wr"] or rolling["sharpe"] < d_rules["max_sharpe"]:
                    new_tier = "FRESH_PICKS"

        if new_tier != current_tier:
            conn.execute(
                "UPDATE factory_strategies SET tier=?, last_promoted=? WHERE strategy_id=?",
                (new_tier, now, sid)
            )
            change = {
                "strategy_id": sid,
                "name": strat["name"],
                "old_tier": current_tier,
                "new_tier": new_tier,
                "stats": stats,
                "direction": "PROMOTED" if _tier_rank(new_tier) > _tier_rank(current_tier) else "DEMOTED",
            }
            changes.append(change)

    conn.commit()
    conn.close()
    return changes


def _tier_rank(tier: str) -> int:
    """Numeric rank for tier comparison."""
    return {"INCUBATOR": 0, "SANDBOX": 1, "FRESH_PICKS": 2, "DNA_MASTER": 3}.get(tier, -1)


def send_tier_change_notifications(changes: List[Dict]) -> int:
    """Send Discord notifications for tier changes."""
    sent = 0
    for change in changes:
        new_tier = change["new_tier"]
        is_promotion = change["direction"] == "PROMOTED"
        stats = change["stats"]

        # Pick webhook based on new tier
        if new_tier == "DNA_MASTER":
            webhook = WEBHOOK_MASTER
        elif new_tier == "FRESH_PICKS":
            webhook = WEBHOOK_FRESH
        elif new_tier == "SANDBOX":
            webhook = WEBHOOK_SANDBOX
        else:
            continue  # No notification for demotion to INCUBATOR

        if not webhook:
            print(f"  [Promotion] No webhook for {new_tier}, skipping")
            continue

        emoji_old = TIER_EMOJI.get(change["old_tier"], "")
        emoji_new = TIER_EMOJI.get(new_tier, "")
        arrow = "\u2b06\ufe0f" if is_promotion else "\u2b07\ufe0f"  # ⬆️ / ⬇️

        color = COLOR_GREEN if is_promotion else COLOR_RED
        title_action = "PROMOTED" if is_promotion else "DEMOTED"

        embed = {
            "title": f"{arrow} Strategy {title_action}: {change['name']}",
            "color": color,
            "description": (
                f"{emoji_old} **{change['old_tier']}** → {emoji_new} **{new_tier}**\n\n"
                f"Forward performance ({stats['trades']} trades):\n"
                f"WR: **{stats['wr']:.0f}%** | Sharpe: **{stats['sharpe']:.2f}** | "
                f"PnL: **{stats['pnl']:+.1f}%** | W/L: {stats['wins']}/{stats['losses']}"
            ),
            "footer": {
                "text": f"DNA Factory | {datetime.now(EST).strftime('%Y-%m-%d %I:%M %p EST')}"
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            r = requests.post(webhook, json={"embeds": [embed]}, timeout=10)
            if r.status_code in (200, 204):
                sent += 1
                print(f"  [Promotion] {change['name']}: {change['old_tier']} → {new_tier}")
        except Exception as e:
            print(f"  [Promotion] Failed to notify: {e}")

    return sent


def print_tier_summary():
    """Print current tier distribution."""
    conn = sqlite3.connect(str(FACTORY_DB))
    rows = conn.execute(
        "SELECT tier, COUNT(*), AVG(forward_wr), AVG(forward_sharpe), SUM(forward_trades) "
        "FROM factory_strategies GROUP BY tier ORDER BY tier"
    ).fetchall()
    conn.close()

    print("\n=== DNA Factory Tier Summary ===")
    for tier, count, avg_wr, avg_sharpe, total_trades in rows:
        emoji = TIER_EMOJI.get(tier, "")
        avg_wr = avg_wr or 0
        avg_sharpe = avg_sharpe or 0
        total_trades = int(total_trades or 0)
        print(f"  {emoji} {tier:15s} | {count:3d} strategies | "
              f"avg WR: {avg_wr:5.1f}% | avg Sharpe: {avg_sharpe:5.2f} | "
              f"total trades: {total_trades}")


# ──────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Progressive Promotion Pipeline")
    parser.add_argument("--evaluate", action="store_true", help="Evaluate all strategies for promotion/demotion")
    parser.add_argument("--notify", action="store_true", help="Send Discord notifications for tier changes")
    parser.add_argument("--summary", action="store_true", help="Print tier summary")
    args = parser.parse_args()

    if args.evaluate or not any(vars(args).values()):
        changes = evaluate_promotions()
        if changes:
            print(f"\n[Promotion] {len(changes)} tier changes:")
            for c in changes:
                print(f"  {c['direction']}: {c['name']} ({c['old_tier']} → {c['new_tier']})")
            if args.notify:
                sent = send_tier_change_notifications(changes)
                print(f"[Promotion] Sent {sent} Discord notifications")
        else:
            print("[Promotion] No tier changes")

    if args.summary or not any(vars(args).values()):
        print_tier_summary()
```

**Step 2: Run to verify it evaluates (should show 0 changes since all are new)**

Run: `cd /e/findtorontoevents_antigravity.ca && py genome/progressive_promotion.py --evaluate --summary`
Expected: "No tier changes" + tier summary showing all in INCUBATOR

**Step 3: Commit**

```bash
git add genome/progressive_promotion.py
git commit -m "feat: add progressive promotion pipeline (INCUBATOR→SANDBOX→FRESH→MASTER)"
```

---

### Task 3: Update `cross_aggregation/dna_master_tracker.py` — Add Tier Integration

**Files:**
- Modify: `cross_aggregation/dna_master_tracker.py`

**Step 1: Add tier column to master_picks table and factory integration**

Add after the existing `init_db()` function (around line 81):

```python
# Add after init_db() — migrate existing table to include tier
def migrate_add_tier():
    """Add tier column if it doesn't exist (backward-compatible migration)."""
    init_db()
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute("ALTER TABLE master_picks ADD COLUMN tier TEXT DEFAULT 'ELITE'")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists
    conn.close()
```

Add a new function `register_factory_pick` after `register_elite_pick` that accepts tier-aware picks:

```python
def register_factory_pick(pick: Dict, tier: str = "ELITE") -> Optional[int]:
    """
    Register a pick from the DNA Factory with tier classification.
    Routes to appropriate Discord channel based on tier.
    """
    migrate_add_tier()
    conn = sqlite3.connect(str(DB_PATH))

    symbol = pick.get("symbol", "")
    direction = pick.get("direction", "")
    entry = float(pick.get("entry", 0))

    # Dedup
    existing = conn.execute(
        "SELECT id FROM master_picks WHERE symbol=? AND direction=? AND status='ACTIVE' AND ABS(entry_price - ?) / NULLIF(entry_price, 0) < 0.005",
        (symbol, direction, entry)
    ).fetchone()
    if existing:
        conn.close()
        return None

    now_est = datetime.now(EST).strftime("%Y-%m-%d %I:%M %p EST")
    sources = json.dumps(pick.get("source_systems", []))

    cur = conn.execute(
        """INSERT INTO master_picks (symbol, direction, entry_price, tp_price, sl_price,
           entry_time, confidence, agreement_count, source_systems, classification, tier)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (symbol, direction, entry,
         float(pick.get("tp", 0)), float(pick.get("sl", 0)),
         now_est, float(pick.get("confidence", 0)),
         int(pick.get("agreement_count", 0)), sources, tier, tier)
    )
    pick_id = cur.lastrowid
    conn.commit()
    conn.close()
    return pick_id
```

**Step 2: Commit**

```bash
git add cross_aggregation/dna_master_tracker.py
git commit -m "feat: add tier-aware pick registration to DNA master tracker"
```

---

### Task 4: Update `.github/workflows/dna_strategy_pipeline.yml` — Add Factory + Promotion Jobs

**Files:**
- Modify: `.github/workflows/dna_strategy_pipeline.yml`

**Step 1: Add two new jobs at the end of the workflow**

Append after the existing `notify` job:

```yaml
  # ── New: Register factory strategies ──────────────────────────
  factory-register:
    name: Register DNA Factory Strategies
    needs: evolve-strategies
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install numpy pandas requests

      - name: Register strategies & export
        run: |
          python genome/dna_strategy_factory.py --register --export --stats

      - name: Commit registry updates
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"

          git add battleground/data/dna_factory.db battleground/data/dna_factory_registry.json

          if git diff --staged --quiet; then
            echo "No factory changes"
          else
            git commit -m "DNA Factory registry update $(date -u +%Y-%m-%dT%H:%M:%SZ)"
            git push
          fi

  # ── New: Evaluate promotions ──────────────────────────────────
  evaluate-promotions:
    name: Evaluate Tier Promotions
    needs: [generate-picks, factory-register]
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install numpy pandas requests

      - name: Evaluate promotions
        env:
          DISCORD_WEBHOOK_URL: ${{ secrets.DISCORD_WEBHOOK_URL }}
          DISCORD_WEBHOOK_SANDBOX: ${{ secrets.DISCORD_WEBHOOK_SANDBOX }}
          DISCORD_WEBHOOK_DNA_MASTER: ${{ secrets.DISCORD_WEBHOOK_DNA_MASTER }}
        run: |
          python genome/progressive_promotion.py --evaluate --notify --summary

      - name: Commit updated metrics
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"

          git add battleground/data/dna_factory.db

          if git diff --staged --quiet; then
            echo "No metric changes"
          else
            git commit -m "DNA Factory promotion eval $(date -u +%Y-%m-%dT%H:%M:%SZ)"
            git push
          fi
```

**Step 2: Commit**

```bash
git add .github/workflows/dna_strategy_pipeline.yml
git commit -m "feat: add factory-register and evaluate-promotions jobs to DNA pipeline"
```

---

### Task 5: Verify Full System End-to-End

**Step 1: Run factory registration locally**

Run: `cd /e/findtorontoevents_antigravity.ca && py genome/dna_strategy_factory.py --register --export --stats`
Expected: 8 combos + 168 expansions registered, JSON exported, tier summary printed

**Step 2: Run promotion evaluation locally**

Run: `cd /e/findtorontoevents_antigravity.ca && py genome/progressive_promotion.py --evaluate --summary`
Expected: All strategies in INCUBATOR (0 forward trades), no tier changes

**Step 3: Verify JSON output is valid**

Run: `cd /e/findtorontoevents_antigravity.ca && py -c "import json; d=json.load(open('battleground/data/dna_factory_registry.json')); print(f'Total: {d[\"summary\"][\"total\"]}'); print(f'Tiers: {d[\"summary\"][\"by_tier\"]}'); print(f'Categories: {d[\"summary\"][\"by_category\"]}')"`
Expected: Total: 176, Tiers: {"INCUBATOR": 176}, Categories: {"combo": 8, "expansion": 168}

**Step 4: Verify DB schema**

Run: `cd /e/findtorontoevents_antigravity.ca && py -c "import sqlite3; conn=sqlite3.connect('battleground/data/dna_factory.db'); print('Tables:'); [print(f'  {r[0]}') for r in conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()]; print(f'Strategies: {conn.execute(\"SELECT COUNT(*) FROM factory_strategies\").fetchone()[0]}'); conn.close()"`
Expected: Tables: factory_strategies, factory_trades. Strategies: 176

**Step 5: Final commit with all artifacts**

```bash
git add -A battleground/data/dna_factory.db battleground/data/dna_factory_registry.json
git commit -m "chore: add initial DNA factory registry (176 strategies)"
```
