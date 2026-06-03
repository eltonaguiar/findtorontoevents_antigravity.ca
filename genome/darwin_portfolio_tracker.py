#!/usr/bin/env python3
"""
NOTE — SNAPSHOT-RESOLVER ARTIFACT (2026-06-03): WR/PF here is inflated by single
daily-snapshot TP/SL resolution (no intrabar OHLC path) — intraday SL touches are missed.
Do not size up on these numbers. See docs/RESOLVER_SNAPSHOT_ARTIFACT_AFFECTED_PORTFOLIOS_2026-06-03.md

DARWIN ENGINE — Paper Trading Portfolio Tracker
================================================
DNA Evolution Portfolio System

Creates and monitors paper trading portfolios for each evolution family:
- GENESIS (GP) — Genetic Programming DNA evolution
- ATLAS (MAP-Elites) — Quality-Diversity DNA evolution
- NEXUS (Audit Ensemble) — Meta-Weight DNA evolution
- LEGION (Ensemble Coevolution) — Team DNA evolution
- DARWIN CONSENSUS — Cross-engine consensus picks

Tracks P/L, Sharpe ratio, max drawdown, win rate, avg holding time.
"""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GENOME_DIR = Path(__file__).resolve().parent
DB_PATH = GENOME_DIR / "darwin_portfolios.db"
OUTPUT_PATH = GENOME_DIR / "data" / "darwin_portfolios.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s")
logger = logging.getLogger("DarwinPortfolios")

# Evolution family definitions
EVOLUTION_FAMILIES = {
    "genesis": {
        "name": "GENESIS",
        "full_name": "Genetic Programming DNA Evolution",
        "engine": "genetic_programmer",
        "picks_file": "genome/data/gp_active_picks.json",
        "color": "#00ff88",
        "description": "Expression tree DNA evolution — invents novel indicator formulas"
    },
    "atlas": {
        "name": "ATLAS",
        "full_name": "MAP-Elites Quality-Diversity DNA Evolution",
        "engine": "mape_evolver",
        "picks_file": "genome/data/mape_active_picks.json",
        "color": "#00aaff",
        "description": "Quality-diversity DNA evolution — maps the entire strategy behavior space"
    },
    "nexus": {
        "name": "NEXUS",
        "full_name": "Audit Ensemble Meta-Weight DNA Evolution",
        "engine": "audit_ensemble",
        "picks_file": "genome/data/ae_active_picks.json",
        "color": "#ff6600",
        "description": "Meta-weight DNA evolution — evolves optimal trust weights across 40+ systems"
    },
    "legion": {
        "name": "LEGION",
        "full_name": "Ensemble Coevolution DNA Evolution",
        "engine": "ensemble_evolver",
        "picks_file": "genome/data/ensemble_active_picks.json",
        "color": "#cc44ff",
        "description": "Team DNA evolution — evolves voting ensembles of strategies"
    },
    "darwin_consensus": {
        "name": "DARWIN CONSENSUS",
        "full_name": "Cross-Engine DNA Evolution Consensus",
        "engine": "universal_evolver",
        "picks_file": "genome/data/universal_picks.json",
        "color": "#ffd700",
        "description": "Picks agreed upon by 2+ DNA evolution engines — highest conviction"
    },
    "failure_evolver": {
        "name": "PHOENIX",
        "full_name": "Failure-Specific DNA Evolution",
        "engine": "failure_evolver",
        "picks_file": "genome/data/failure_evolved_picks.json",
        "color": "#ff4444",
        "description": "Rises from failed strategies — diagnoses failure modes and evolves corrective variants"
    },
    "momentum_evolver": {
        "name": "VORTEX",
        "full_name": "Momentum Scanner DNA Evolution",
        "engine": "momentum_evolver",
        "picks_file": "genome/data/momentum_active_picks.json",
        "color": "#ff00ff",
        "description": "Scans 20 symbols for momentum, evolves strategies on highest-momentum assets"
    },
    "multitf_evolver": {
        "name": "HORIZON",
        "full_name": "Multi-Timeframe DNA Evolution",
        "engine": "multitf_evolver",
        "picks_file": "genome/data/multitf_active_picks.json",
        "color": "#00ffcc",
        "description": "Evolves swing strategies across 1h/4h/1d timeframes with HTF trend alignment"
    },
    "contrarian_evolver": {
        "name": "REBEL",
        "full_name": "Contrarian DNA Evolution",
        "engine": "contrarian_evolver",
        "picks_file": "genome/data/contrarian_active_picks.json",
        "color": "#ffaa00",
        "description": "Evolves mean-reversion strategies that fade consensus — counters SHORT bias"
    }
}

INITIAL_CAPITAL = 10000.0  # $10,000 per portfolio


class DarwinPortfolioTracker:
    """Manages paper trading portfolios for each DNA evolution family."""

    def __init__(self):
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(str(DB_PATH))
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS portfolios (
                family_id TEXT PRIMARY KEY,
                name TEXT, capital REAL,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                total_pnl REAL DEFAULT 0,
                max_drawdown REAL DEFAULT 0,
                peak_capital REAL,
                created_at TEXT, updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                family_id TEXT, symbol TEXT, direction TEXT,
                entry_price REAL, current_price REAL,
                quantity REAL, entry_time TEXT,
                strategy TEXT, confidence REAL,
                tp_pct REAL DEFAULT 5.0, sl_pct REAL DEFAULT 2.5,
                status TEXT DEFAULT 'OPEN',
                exit_price REAL, exit_time TEXT, pnl_pct REAL,
                holding_bars INTEGER DEFAULT 0,
                FOREIGN KEY (family_id) REFERENCES portfolios(family_id)
            );
            CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                family_id TEXT, timestamp TEXT,
                capital REAL, unrealized_pnl REAL,
                total_value REAL, position_count INTEGER
            );
        """)
        conn.commit()
        conn.close()

        # Initialize portfolios if not exist
        self._ensure_portfolios()

    def _ensure_portfolios(self):
        conn = sqlite3.connect(str(DB_PATH))
        now = datetime.now(timezone.utc).isoformat()
        for fid, fam in EVOLUTION_FAMILIES.items():
            existing = conn.execute("SELECT 1 FROM portfolios WHERE family_id=?", (fid,)).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO portfolios (family_id, name, capital, peak_capital, created_at, updated_at) VALUES (?,?,?,?,?,?)",
                    (fid, fam["name"], INITIAL_CAPITAL, INITIAL_CAPITAL, now, now)
                )
        conn.commit()
        conn.close()

    def load_picks(self, family_id: str) -> List[Dict]:
        """Load active picks for a given evolution family."""
        fam = EVOLUTION_FAMILIES.get(family_id)
        if not fam:
            return []
        picks_path = PROJECT_ROOT / fam["picks_file"]
        try:
            if picks_path.exists():
                data = json.loads(picks_path.read_text())
                if family_id == "darwin_consensus":
                    return data.get("consensus_picks", data.get("picks", []))
                return data.get("picks", [])
        except Exception as e:
            logger.debug(f"Failed to load picks for {family_id}: {e}")
        return []

    def update_positions(self, family_id: str, current_prices: Dict[str, float]):
        """Update open positions with current prices, check TP/SL."""
        conn = sqlite3.connect(str(DB_PATH))
        now = datetime.now(timezone.utc).isoformat()

        open_positions = conn.execute(
            "SELECT id, symbol, direction, entry_price, quantity, tp_pct, sl_pct FROM positions WHERE family_id=? AND status='OPEN'",
            (family_id,)
        ).fetchall()

        for pos_id, symbol, direction, entry_price, qty, tp_pct, sl_pct in open_positions:
            price = current_prices.get(symbol)
            if not price:
                continue

            # Calculate P&L
            if direction == "LONG":
                pnl_pct = ((price - entry_price) / entry_price) * 100
            else:
                pnl_pct = ((entry_price - price) / entry_price) * 100

            # Update current price
            conn.execute("UPDATE positions SET current_price=?, holding_bars=holding_bars+1 WHERE id=?", (price, pos_id))

            # Check TP/SL
            if pnl_pct >= tp_pct:
                self._close_position(conn, pos_id, family_id, price, pnl_pct, now, "TP_HIT")
            elif pnl_pct <= -sl_pct:
                self._close_position(conn, pos_id, family_id, price, pnl_pct, now, "SL_HIT")

        conn.commit()
        conn.close()

    def _close_position(self, conn, pos_id, family_id, exit_price, pnl_pct, now, reason):
        conn.execute(
            "UPDATE positions SET status=?, exit_price=?, exit_time=?, pnl_pct=? WHERE id=?",
            (reason, exit_price, now, pnl_pct, pos_id)
        )
        # Update portfolio stats
        conn.execute("UPDATE portfolios SET total_trades=total_trades+1, updated_at=? WHERE family_id=?", (now, family_id))
        if pnl_pct > 0:
            conn.execute("UPDATE portfolios SET winning_trades=winning_trades+1 WHERE family_id=?", (family_id,))
        conn.execute("UPDATE portfolios SET total_pnl=total_pnl+? WHERE family_id=?", (pnl_pct, family_id))

    def open_new_positions(self, family_id: str, current_prices: Dict[str, float], max_positions: int = 5):
        """Open new positions from latest picks."""
        conn = sqlite3.connect(str(DB_PATH))
        now = datetime.now(timezone.utc).isoformat()

        # Check existing open positions
        open_count = conn.execute(
            "SELECT COUNT(*) FROM positions WHERE family_id=? AND status='OPEN'", (family_id,)
        ).fetchone()[0]

        if open_count >= max_positions:
            conn.close()
            return

        # Get current open symbols to avoid duplicates
        open_symbols = set(row[0] for row in conn.execute(
            "SELECT symbol FROM positions WHERE family_id=? AND status='OPEN'", (family_id,)
        ).fetchall())

        picks = self.load_picks(family_id)
        portfolio = conn.execute("SELECT capital FROM portfolios WHERE family_id=?", (family_id,)).fetchone()
        capital = portfolio[0] if portfolio else INITIAL_CAPITAL

        slots_available = max_positions - open_count
        for pick in picks[:slots_available]:
            symbol = pick.get("symbol", "")
            if symbol in open_symbols or symbol not in current_prices:
                continue

            price = current_prices[symbol]
            direction = pick.get("direction", "LONG")
            confidence = float(pick.get("confidence", 0.5))
            strategy = pick.get("strategy", "unknown")

            # Position size: 20% of capital per position
            position_value = capital * 0.20
            quantity = position_value / price

            conn.execute(
                """INSERT INTO positions (family_id, symbol, direction, entry_price, current_price,
                   quantity, entry_time, strategy, confidence, tp_pct, sl_pct)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (family_id, symbol, direction, price, price, quantity, now, strategy, confidence, 5.0, 2.5)
            )
            open_symbols.add(symbol)
            logger.info(f"[{EVOLUTION_FAMILIES[family_id]['name']}] Opened {direction} {symbol} @ {price:.2f}")

        conn.commit()
        conn.close()

    def get_portfolio_summary(self) -> Dict:
        """Get summary of all DNA evolution portfolios."""
        conn = sqlite3.connect(str(DB_PATH))
        summaries = {}

        for fid, fam in EVOLUTION_FAMILIES.items():
            port = conn.execute(
                "SELECT capital, total_trades, winning_trades, total_pnl, max_drawdown, peak_capital FROM portfolios WHERE family_id=?",
                (fid,)
            ).fetchone()

            if not port:
                continue

            capital, total_trades, winning_trades, total_pnl, max_dd, peak = port

            # Open positions
            positions = conn.execute(
                "SELECT symbol, direction, entry_price, current_price, pnl_pct, strategy, confidence, holding_bars, entry_time FROM positions WHERE family_id=? AND status='OPEN'",
                (fid,)
            ).fetchall()

            # Closed positions for stats
            closed = conn.execute(
                "SELECT pnl_pct, holding_bars FROM positions WHERE family_id=? AND status!='OPEN'",
                (fid,)
            ).fetchall()

            # Closed positions with full details for dashboard
            closed_detail = conn.execute(
                "SELECT symbol, direction, entry_price, exit_price, pnl_pct, strategy, entry_time, exit_time, status FROM positions WHERE family_id=? AND status!='OPEN' ORDER BY exit_time DESC LIMIT 50",
                (fid,)
            ).fetchall()

            # Calculate metrics
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            closed_pnls = [c[0] for c in closed if c[0] is not None]
            avg_pnl = np.mean(closed_pnls) if closed_pnls else 0
            sharpe = (np.mean(closed_pnls) / (np.std(closed_pnls) + 1e-8)) if len(closed_pnls) > 1 else 0
            avg_hold = np.mean([c[1] for c in closed]) if closed else 0

            unrealized_pnl = sum(
                ((p[3] - p[2]) / p[2] * 100 if p[1] == "LONG" else (p[2] - p[3]) / p[2] * 100)
                for p in positions if p[2] > 0
            )

            summaries[fid] = {
                "name": fam["name"],
                "full_name": fam["full_name"],
                "color": fam["color"],
                "description": fam["description"],
                "capital": round(capital, 2),
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "win_rate": round(win_rate, 1),
                "total_pnl_pct": round(total_pnl, 2),
                "avg_pnl_pct": round(avg_pnl, 2),
                "sharpe_ratio": round(sharpe, 2),
                "max_drawdown": round(max_dd, 2),
                "avg_holding_bars": round(avg_hold, 1),
                "unrealized_pnl_pct": round(unrealized_pnl, 2),
                "open_positions": [
                    {
                        "symbol": p[0], "direction": p[1],
                        "entry_price": p[2], "current_price": p[3],
                        "pnl_pct": round(((p[3]-p[2])/p[2]*100 if p[1]=="LONG" else (p[2]-p[3])/p[2]*100), 2) if p[2] > 0 else 0,
                        "strategy": p[5], "confidence": p[6],
                        "holding_bars": p[7], "entry_time": p[8]
                    }
                    for p in positions
                ],
                "closed_trades": [
                    {
                        "symbol": c[0], "direction": c[1],
                        "entry_price": c[2], "exit_price": c[3],
                        "pnl": round(c[4], 2) if c[4] else 0,
                        "strategy": c[5],
                        "opened": c[6], "closed": c[7],
                        "result": "WIN" if (c[4] or 0) > 0 else "LOSS"
                    }
                    for c in closed_detail
                ],
                "closed_count": len(closed)
            }

        conn.close()
        return summaries

    def save_dashboard_json(self):
        """Save portfolio data for dashboard consumption."""
        summaries = self.get_portfolio_summary()
        output = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "system": "darwin_portfolio_tracker",
            "initial_capital_per_family": INITIAL_CAPITAL,
            "evolution_families": len(EVOLUTION_FAMILIES),
            "portfolios": summaries
        }
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(json.dumps(output, indent=2))
        logger.info(f"Saved portfolio data to {OUTPUT_PATH}")
        return output


def run_portfolio_update():
    """Main entry point — update all DNA evolution portfolios."""
    tracker = DarwinPortfolioTracker()

    # Fetch current prices
    try:
        import importlib.util
        gp_path = str(GENOME_DIR / "genetic_programmer.py")
        spec = importlib.util.spec_from_file_location("genetic_programmer", gp_path)
        gp = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gp)

        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "DOGEUSDT"]
        market_data = gp.fetch_market_data(symbols, limit=10)
        current_prices = {sym: float(data.close[-1]) for sym, data in market_data.items()}
        logger.info(f"Current prices: {current_prices}")
    except Exception as e:
        logger.warning(f"Could not fetch prices: {e}")
        current_prices = {}

    if current_prices:
        for fid in EVOLUTION_FAMILIES:
            tracker.update_positions(fid, current_prices)
            tracker.open_new_positions(fid, current_prices)

    output = tracker.save_dashboard_json()

    print("\n" + "=" * 70)
    print("DARWIN ENGINE — DNA Evolution Portfolio Status")
    print("=" * 70)
    for fid, summary in output.get("portfolios", {}).items():
        print(f"\n  {summary['name']} ({summary['full_name']})")
        print(f"    Capital: ${summary['capital']:,.2f} | Trades: {summary['total_trades']} | WR: {summary['win_rate']:.1f}%")
        print(f"    Realized P/L: {summary['total_pnl_pct']:.2f}% | Unrealized: {summary['unrealized_pnl_pct']:.2f}%")
        print(f"    Sharpe: {summary['sharpe_ratio']:.2f} | Max DD: {summary['max_drawdown']:.2f}%")
        open_pos = summary.get("open_positions", [])
        if open_pos:
            for p in open_pos:
                print(f"      {p['direction']} {p['symbol']} @ {p['entry_price']:.4f} -> {p['current_price']:.4f} ({p['pnl_pct']:+.2f}%)")
        else:
            print(f"      No open positions")

    return output


if __name__ == "__main__":
    run_portfolio_update()
