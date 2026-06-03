#!/usr/bin/env python3
"""
NOTE — SNAPSHOT-RESOLVER ARTIFACT (2026-06-03): WR/PF here is inflated by single
daily-snapshot TP/SL resolution (no intrabar OHLC path) — intraday SL touches are missed.
Do not size up on these numbers. See docs/RESOLVER_SNAPSHOT_ARTIFACT_AFFECTED_PORTFOLIOS_2026-06-03.md

Permutation Portfolio Manager - Tests system and strategy combinations for profitability.

This module creates and manages paper trading portfolios that test:
1. System permutations (which systems work alone or together)
2. Strategy combinations (which strategies work best together)

Usage:
    python -m paper_trading.permutation_portfolio_manager --mode systems
    python -m paper_trading.permutation_portfolio_manager --mode strategies
    python -m paper_trading.permutation_portfolio_manager --mode all
"""
import json
import logging
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict

from paper_trading.db import get_conn, DB_PATH
from paper_trading.models import NormalizedPick
from paper_trading.helpers import fetch_json
from paper_trading.multi_source import fetch_price

logger = logging.getLogger("permutation_portfolios")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(__file__).parent / "data"


@dataclass
class SystemPermutationPortfolio:
    """A portfolio that trades based on system agreement levels."""
    id: str
    name: str
    systems: List[str]
    min_agreement: int
    max_agreement: int
    starting_capital: float = 10000.0
    cash: float = 10000.0
    equity: float = 10000.0
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    max_drawdown: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "systems": self.systems,
            "min_agreement": self.min_agreement,
            "max_agreement": self.max_agreement,
            "starting_capital": self.starting_capital,
            "cash": self.cash,
            "equity": self.equity,
            "total_trades": self.total_trades,
            "wins": self.wins,
            "losses": self.losses,
            "win_rate": (self.wins / self.total_trades * 100) if self.total_trades > 0 else 0,
            "max_drawdown": self.max_drawdown,
            "pnl_pct": ((self.equity - self.starting_capital) / self.starting_capital * 100)
        }


@dataclass  
class StrategyCombinationPortfolio:
    """A portfolio that trades based on strategy confluence."""
    id: str
    name: str
    strategies: List[str]
    min_strategies: int
    require_same_direction: bool = True
    allow_opposing_directions: bool = False
    starting_capital: float = 10000.0
    cash: float = 10000.0
    equity: float = 10000.0
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    max_drawdown: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "strategies": self.strategies,
            "min_strategies": self.min_strategies,
            "require_same_direction": self.require_same_direction,
            "starting_capital": self.starting_capital,
            "cash": self.cash,
            "equity": self.equity,
            "total_trades": self.total_trades,
            "wins": self.wins,
            "losses": self.losses,
            "win_rate": (self.wins / self.total_trades * 100) if self.total_trades > 0 else 0,
            "max_drawdown": self.max_drawdown,
            "pnl_pct": ((self.equity - self.starting_capital) / self.starting_capital * 100)
        }


class PermutationPortfolioManager:
    """Manages system permutation and strategy combination portfolios."""
    
    def __init__(self):
        self.conn = get_conn()
        self._init_tables()
        self.system_config = self._load_system_config()
        self.strategy_config = self._load_strategy_config()
        self.system_portfolios: Dict[str, SystemPermutationPortfolio] = {}
        self.strategy_portfolios: Dict[str, StrategyCombinationPortfolio] = {}
        self._load_or_create_portfolios()
    
    def _init_tables(self):
        """Initialize database tables for permutation portfolios."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS permutation_portfolios (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                portfolio_type TEXT NOT NULL,  -- 'system' or 'strategy'
                config_json TEXT NOT NULL,
                cash REAL DEFAULT 10000.0,
                equity REAL DEFAULT 10000.0,
                total_trades INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                max_drawdown_pct REAL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS permutation_positions (
                id TEXT PRIMARY KEY,
                portfolio_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL NOT NULL,
                current_price REAL NOT NULL,
                tp REAL NOT NULL,
                sl REAL NOT NULL,
                position_size_usd REAL NOT NULL,
                entry_date TEXT NOT NULL,
                status TEXT DEFAULT 'ACTIVE',
                exit_price REAL,
                exit_date TEXT,
                pnl_pct REAL DEFAULT 0.0,
                pnl_usd REAL DEFAULT 0.0,
                -- System/strategy metadata
                source_systems TEXT,  -- JSON array of systems that agreed
                source_strategies TEXT,  -- JSON array of strategies that agreed
                agreement_count INTEGER DEFAULT 1,
                confidence REAL DEFAULT 0.5,
                FOREIGN KEY (portfolio_id) REFERENCES permutation_portfolios(id)
            );
            
            CREATE TABLE IF NOT EXISTS permutation_equity_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                portfolio_id TEXT NOT NULL,
                equity REAL NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (portfolio_id) REFERENCES permutation_portfolios(id)
            );
            
            CREATE INDEX IF NOT EXISTS idx_perm_pos_portfolio ON permutation_positions(portfolio_id);
            CREATE INDEX IF NOT EXISTS idx_perm_pos_status ON permutation_positions(status);
            CREATE INDEX IF NOT EXISTS idx_perm_snap_portfolio ON permutation_equity_snapshots(portfolio_id);
        """)
        self.conn.commit()
    
    def _load_system_config(self) -> dict:
        """Load system permutation configuration."""
        config_path = Path(__file__).parent / "system_permutation_config.json"
        if config_path.exists():
            return json.loads(config_path.read_text())
        return {"portfolios": {}}
    
    def _load_strategy_config(self) -> dict:
        """Load strategy combination configuration."""
        config_path = Path(__file__).parent / "strategy_combination_config.json"
        if config_path.exists():
            return json.loads(config_path.read_text())
        return {"portfolios": {}}
    
    def _load_or_create_portfolios(self):
        """Load existing portfolios or create from config."""
        now = datetime.now(timezone.utc).isoformat()
        
        # Load system portfolios
        for category, data in self.system_config.get("portfolios", {}).items():
            for pf_config in data.get("portfolios", []):
                pf_id = pf_config["id"]
                existing = self.conn.execute(
                    "SELECT * FROM permutation_portfolios WHERE id=?",
                    (pf_id,)
                ).fetchone()
                
                if existing:
                    # Load from DB
                    self.system_portfolios[pf_id] = SystemPermutationPortfolio(
                        id=pf_id,
                        name=existing["name"],
                        systems=json.loads(pf_config["systems"]),
                        min_agreement=pf_config["min_agreement"],
                        max_agreement=pf_config["max_agreement"],
                        cash=existing["cash"],
                        equity=existing["equity"],
                        total_trades=existing["total_trades"],
                        wins=existing["wins"],
                        losses=existing["losses"],
                        max_drawdown=existing["max_drawdown_pct"]
                    )
                else:
                    # Create new
                    portfolio = SystemPermutationPortfolio(
                        id=pf_id,
                        name=pf_config["name"],
                        systems=pf_config["systems"],
                        min_agreement=pf_config["min_agreement"],
                        max_agreement=pf_config["max_agreement"]
                    )
                    self.system_portfolios[pf_id] = portfolio
                    
                    # Insert to DB
                    self.conn.execute("""
                        INSERT INTO permutation_portfolios 
                        (id, name, portfolio_type, config_json, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (pf_id, pf_config["name"], "system", json.dumps(pf_config), now, now))
        
        # Load strategy portfolios
        for category, data in self.strategy_config.get("portfolios", {}).items():
            for pf_config in data.get("portfolios", []):
                pf_id = pf_config["id"]
                existing = self.conn.execute(
                    "SELECT * FROM permutation_portfolios WHERE id=?",
                    (pf_id,)
                ).fetchone()
                
                if existing:
                    self.strategy_portfolios[pf_id] = StrategyCombinationPortfolio(
                        id=pf_id,
                        name=existing["name"],
                        strategies=pf_config["strategies"],
                        min_strategies=pf_config["min_strategies"],
                        require_same_direction=pf_config.get("require_same_direction", True),
                        allow_opposing_directions=pf_config.get("allow_opposing_directions", False),
                        cash=existing["cash"],
                        equity=existing["equity"],
                        total_trades=existing["total_trades"],
                        wins=existing["wins"],
                        losses=existing["losses"],
                        max_drawdown=existing["max_drawdown_pct"]
                    )
                else:
                    portfolio = StrategyCombinationPortfolio(
                        id=pf_id,
                        name=pf_config["name"],
                        strategies=pf_config["strategies"],
                        min_strategies=pf_config["min_strategies"],
                        require_same_direction=pf_config.get("require_same_direction", True),
                        allow_opposing_directions=pf_config.get("allow_opposing_directions", False)
                    )
                    self.strategy_portfolios[pf_id] = portfolio
                    
                    self.conn.execute("""
                        INSERT INTO permutation_portfolios 
                        (id, name, portfolio_type, config_json, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (pf_id, pf_config["name"], "strategy", json.dumps(pf_config), now, now))
        
        self.conn.commit()
        logger.info(f"Loaded {len(self.system_portfolios)} system portfolios, {len(self.strategy_portfolios)} strategy portfolios")
    
    def fetch_all_picks(self) -> List[NormalizedPick]:
        """Fetch picks from all configured systems."""
        all_picks = []
        
        # Use the dashboard generator's data if available
        dashboard_path = ROOT / "audit_trail" / "data" / "dashboard_payload.json"
        if dashboard_path.exists():
            data = json.loads(dashboard_path.read_text())
            for pick_data in data.get("picks", {}).get("active", []):
                pick = self._normalize_pick(pick_data)
                if pick:
                    all_picks.append(pick)
        
        logger.info(f"Fetched {len(all_picks)} active picks from all systems")
        return all_picks
    
    def _normalize_pick(self, data: dict) -> Optional[NormalizedPick]:
        """Normalize a pick from dashboard format to NormalizedPick."""
        try:
            return NormalizedPick(
                symbol=data.get("symbol", ""),
                direction=data.get("direction", "LONG"),
                entry_price=float(data.get("entry_price", 0)),
                tp=float(data.get("take_profit", 0)),
                sl=float(data.get("stop_loss", 0)),
                strategy=data.get("strategy", "unknown"),
                strategy_name=data.get("strategy", "unknown"),
                category="crypto",
                confidence=float(data.get("confidence", 0.5)),
                reason=data.get("reason", ""),
                picked_at=data.get("timestamp", "")
            )
        except Exception as e:
            logger.warning(f"Failed to normalize pick: {e}")
            return None
    
    def group_picks_by_symbol_direction(self, picks: List[NormalizedPick]) -> Dict[Tuple[str, str], List[NormalizedPick]]:
        """Group picks by (symbol, direction) to find agreements."""
        groups = defaultdict(list)
        for pick in picks:
            key = (pick.symbol, pick.direction)
            groups[key].append(pick)
        return groups
    
    def get_systems_for_pick(self, pick: NormalizedPick) -> Set[str]:
        """Determine which system(s) generated this pick."""
        # This would need to be extended based on your data structure
        # For now, we infer from strategy name or source_system field
        systems = set()
        
        # Check if source_system is in the raw data (would need to pass this through)
        # For now, use heuristics based on strategy names
        strategy = pick.strategy.lower()
        
        if "ema_stack" in strategy or "macd" in strategy:
            systems.add("rapid_fire")
        if "kimi" in strategy:
            systems.add("kimi_signal_tracking")
        if "hoffman" in strategy or "irb" in strategy:
            systems.add("alpha_engine")
        if "ml" in strategy or "xgboost" in strategy or "lstm" in strategy:
            systems.add("crypto_ml_edge")
        
        # Default to at least one system
        if not systems:
            systems.add("alpha_engine")
        
        return systems
    
    def process_system_portfolios(self, picks: List[NormalizedPick]):
        """Process picks against all system permutation portfolios."""
        groups = self.group_picks_by_symbol_direction(picks)
        
        for portfolio in self.system_portfolios.values():
            # Find picks that meet the agreement criteria
            for (symbol, direction), group_picks in groups.items():
                # Count how many of the portfolio's systems are in this group
                systems_present = set()
                for pick in group_picks:
                    systems_present.update(self.get_systems_for_pick(pick))
                
                agreement_count = len(systems_present.intersection(set(portfolio.systems)))
                
                # Check if agreement level meets portfolio criteria
                if portfolio.min_agreement <= agreement_count <= portfolio.max_agreement:
                    # Get best pick from group (highest confidence)
                    best_pick = max(group_picks, key=lambda p: p.confidence)
                    self._enter_position(portfolio, best_pick, list(systems_present))
    
    def process_strategy_portfolios(self, picks: List[NormalizedPick]):
        """Process picks against all strategy combination portfolios."""
        groups = self.group_picks_by_symbol_direction(picks)
        
        for portfolio in self.strategy_portfolios.values():
            for (symbol, direction), group_picks in groups.items():
                # Count strategies from portfolio that are present
                strategies_present = []
                for pick in group_picks:
                    if pick.strategy in portfolio.strategies:
                        strategies_present.append(pick.strategy)
                
                unique_strategies = list(set(strategies_present))
                
                # Check if meets minimum strategy count
                if len(unique_strategies) >= portfolio.min_strategies:
                    # Check direction requirements
                    if portfolio.require_same_direction:
                        # All picks must be same direction (guaranteed by grouping)
                        pass
                    
                    # Get best pick
                    best_pick = max(group_picks, key=lambda p: p.confidence)
                    self._enter_strategy_position(portfolio, best_pick, unique_strategies)
    
    def _enter_position(self, portfolio: SystemPermutationPortfolio, pick: NormalizedPick, systems: List[str]):
        """Enter a position in a system portfolio."""
        # Check if position already exists
        existing = self.conn.execute(
            "SELECT COUNT(*) FROM permutation_positions WHERE portfolio_id=? AND symbol=? AND status='ACTIVE'",
            (portfolio.id, pick.symbol)
        ).fetchone()[0]
        
        if existing > 0:
            return
        
        # Calculate position size (2% risk)
        risk_amount = portfolio.equity * 0.02
        dist_sl = abs(pick.entry_price - pick.sl)
        if dist_sl <= 0:
            return
        
        shares = risk_amount / dist_sl
        position_usd = shares * pick.entry_price
        
        # Cap at 10% of equity per position
        max_pos = portfolio.equity * 0.10
        if position_usd > max_pos:
            position_usd = max_pos
            shares = position_usd / pick.entry_price
        
        if position_usd > portfolio.cash:
            return
        
        # Insert position
        now = datetime.now(timezone.utc).isoformat()
        pos_id = f"{portfolio.id}_{pick.symbol}_{now[:19]}"
        
        self.conn.execute("""
            INSERT INTO permutation_positions
            (id, portfolio_id, symbol, direction, entry_price, current_price, tp, sl,
             position_size_usd, entry_date, status, source_systems, agreement_count, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (pos_id, portfolio.id, pick.symbol, pick.direction, pick.entry_price, pick.entry_price,
              pick.tp, pick.sl, round(position_usd, 2), now, "ACTIVE", json.dumps(systems), 
              len(systems), pick.confidence))
        
        # Update portfolio cash
        portfolio.cash -= position_usd
        self.conn.execute(
            "UPDATE permutation_portfolios SET cash=? WHERE id=?",
            (round(portfolio.cash, 2), portfolio.id)
        )
        
        self.conn.commit()
        logger.info(f"Entered {portfolio.id}: {pick.symbol} {pick.direction} (${position_usd:.2f}) - Systems: {systems}")
    
    def _enter_strategy_position(self, portfolio: StrategyCombinationPortfolio, pick: NormalizedPick, strategies: List[str]):
        """Enter a position in a strategy portfolio."""
        existing = self.conn.execute(
            "SELECT COUNT(*) FROM permutation_positions WHERE portfolio_id=? AND symbol=? AND status='ACTIVE'",
            (portfolio.id, pick.symbol)
        ).fetchone()[0]
        
        if existing > 0:
            return
        
        # Calculate position size
        risk_amount = portfolio.equity * 0.02
        dist_sl = abs(pick.entry_price - pick.sl)
        if dist_sl <= 0:
            return
        
        shares = risk_amount / dist_sl
        position_usd = shares * pick.entry_price
        
        max_pos = portfolio.equity * 0.10
        if position_usd > max_pos:
            position_usd = max_pos
            shares = position_usd / pick.entry_price
        
        if position_usd > portfolio.cash:
            return
        
        now = datetime.now(timezone.utc).isoformat()
        pos_id = f"{portfolio.id}_{pick.symbol}_{now[:19]}"
        
        self.conn.execute("""
            INSERT INTO permutation_positions
            (id, portfolio_id, symbol, direction, entry_price, current_price, tp, sl,
             position_size_usd, entry_date, status, source_strategies, agreement_count, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (pos_id, portfolio.id, pick.symbol, pick.direction, pick.entry_price, pick.entry_price,
              pick.tp, pick.sl, round(position_usd, 2), now, "ACTIVE", json.dumps(strategies),
              len(strategies), pick.confidence))
        
        portfolio.cash -= position_usd
        self.conn.execute(
            "UPDATE permutation_portfolios SET cash=? WHERE id=?",
            (round(portfolio.cash, 2), portfolio.id)
        )
        
        self.conn.commit()
        logger.info(f"Entered {portfolio.id}: {pick.symbol} {pick.direction} (${position_usd:.2f}) - Strategies: {strategies}")
    
    def check_exits(self):
        """Check all active positions for TP/SL hits."""
        positions = self.conn.execute(
            "SELECT * FROM permutation_positions WHERE status='ACTIVE'"
        ).fetchall()
        
        for pos in positions:
            try:
                current_price = fetch_price(pos["symbol"])
                if not current_price:
                    continue
                
                direction = pos["direction"]
                entry = pos["entry_price"]
                tp = pos["tp"]
                sl = pos["sl"]
                
                # Check exit conditions
                exit_price = None
                exit_reason = None
                
                if direction == "LONG":
                    if current_price >= tp:
                        exit_price = tp
                        exit_reason = "TP_HIT"
                    elif current_price <= sl:
                        exit_price = sl
                        exit_reason = "SL_HIT"
                else:  # SHORT
                    if current_price <= tp:
                        exit_price = tp
                        exit_reason = "TP_HIT"
                    elif current_price >= sl:
                        exit_price = sl
                        exit_reason = "SL_HIT"
                
                # Check time stop (7 days)
                entry_date = datetime.fromisoformat(pos["entry_date"].replace('Z', '+00:00'))
                days_held = (datetime.now(timezone.utc) - entry_date).days
                if days_held >= 7 and not exit_price:
                    exit_price = current_price
                    exit_reason = "TIME_STOP"
                
                if exit_price:
                    self._close_position(pos, exit_price, exit_reason)
                else:
                    # Update current price
                    pnl_pct = ((current_price - entry) / entry * 100) if direction == "LONG" else ((entry - current_price) / entry * 100)
                    self.conn.execute(
                        "UPDATE permutation_positions SET current_price=?, pnl_pct=? WHERE id=?",
                        (current_price, round(pnl_pct, 4), pos["id"])
                    )
            except Exception as e:
                logger.error(f"Error checking position {pos['id']}: {e}")
        
        self.conn.commit()
    
    def _close_position(self, pos, exit_price: float, exit_reason: str):
        """Close a position and update portfolio."""
        direction = pos["direction"]
        entry = pos["entry_price"]
        position_usd = pos["position_size_usd"]
        portfolio_id = pos["portfolio_id"]
        
        # Calculate P&L
        if direction == "LONG":
            pnl_pct = (exit_price - entry) / entry * 100
        else:
            pnl_pct = (entry - exit_price) / entry * 100
        
        pnl_usd = position_usd * (pnl_pct / 100)
        
        # Update position
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute("""
            UPDATE permutation_positions
            SET status='CLOSED', exit_price=?, exit_date=?, pnl_pct=?, pnl_usd=?
            WHERE id=?
        """, (exit_price, now, round(pnl_pct, 4), round(pnl_usd, 2), pos["id"]))
        
        # Update portfolio
        pf_data = self.conn.execute(
            "SELECT * FROM permutation_portfolios WHERE id=?", (portfolio_id,)
        ).fetchone()
        
        if pf_data:
            new_cash = pf_data["cash"] + position_usd + pnl_usd
            new_equity = pf_data["equity"] + pnl_usd
            total_trades = pf_data["total_trades"] + 1
            wins = pf_data["wins"] + (1 if pnl_pct > 0 else 0)
            losses = pf_data["losses"] + (1 if pnl_pct <= 0 else 0)
            
            self.conn.execute("""
                UPDATE permutation_portfolios 
                SET cash=?, equity=?, total_trades=?, wins=?, losses=?, updated_at=?
                WHERE id=?
            """, (round(new_cash, 2), round(new_equity, 2), total_trades, wins, losses, now, portfolio_id))
            
            logger.info(f"Closed {portfolio_id}: {pos['symbol']} {exit_reason} PnL: {pnl_pct:.2f}%")
        
        self.conn.commit()
    
    def snapshot_equity(self):
        """Record equity snapshots for all portfolios."""
        now = datetime.now(timezone.utc).isoformat()
        
        for pf_id in list(self.system_portfolios.keys()) + list(self.strategy_portfolios.keys()):
            pf_data = self.conn.execute(
                "SELECT equity FROM permutation_portfolios WHERE id=?", (pf_id,)
            ).fetchone()
            
            if pf_data:
                self.conn.execute("""
                    INSERT INTO permutation_equity_snapshots (portfolio_id, equity, timestamp)
                    VALUES (?, ?, ?)
                """, (pf_id, pf_data["equity"], now))
        
        self.conn.commit()
    
    def export_results(self):
        """Export portfolio results to JSON."""
        results = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "system_portfolios": [],
            "strategy_portfolios": []
        }
        
        for pf in self.system_portfolios.values():
            results["system_portfolios"].append(pf.to_dict())
        
        for pf in self.strategy_portfolios.values():
            results["strategy_portfolios"].append(pf.to_dict())
        
        output_path = DATA_DIR / "permutation_results.json"
        output_path.write_text(json.dumps(results, indent=2))
        logger.info(f"Results exported to {output_path}")
        return results
    
    def run(self, mode: str = "all"):
        """Run the full process."""
        logger.info(f"Starting permutation portfolio run (mode: {mode})")
        
        # 1. Check exits
        self.check_exits()
        
        # 2. Fetch picks
        picks = self.fetch_all_picks()
        
        # 3. Process portfolios
        if mode in ("all", "systems"):
            self.process_system_portfolios(picks)
        
        if mode in ("all", "strategies"):
            self.process_strategy_portfolios(picks)
        
        # 4. Snapshot equity
        self.snapshot_equity()
        
        # 5. Export results
        results = self.export_results()
        
        logger.info("Permutation portfolio run complete")
        return results


def main():
    parser = argparse.ArgumentParser(description="Permutation Portfolio Manager")
    parser.add_argument("--mode", choices=["all", "systems", "strategies"], default="all",
                       help="Which portfolios to run")
    parser.add_argument("--export", action="store_true", help="Export results and exit")
    
    args = parser.parse_args()
    
    manager = PermutationPortfolioManager()
    
    if args.export:
        manager.export_results()
    else:
        manager.run(args.mode)


if __name__ == "__main__":
    main()
