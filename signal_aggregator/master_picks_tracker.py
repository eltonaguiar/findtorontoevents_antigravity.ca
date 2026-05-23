"""
Master-Picks Performance Tracker

Tracks all signals sent to #master-picks Discord channel
Monitors performance and calculates health-score
Shows active picks with unrealized P/L and closed picks with realized P/L
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# EST timezone handling
try:
    from zoneinfo import ZoneInfo
    HAS_ZONEINFO = True
except ImportError:
    HAS_ZONEINFO = False
    logger.warning("zoneinfo not available, using manual EST offset")

DATA_DIR = Path(__file__).resolve().parent / "data"
TRACKER_FILE = DATA_DIR / "master_picks_tracker.json"
HISTORY_FILE = DATA_DIR / "master_picks_history.json"


def to_est(timestamp_str: str) -> str:
    """Convert ISO timestamp to EST/EDT formatted string"""
    if not timestamp_str:
        return "N/A"
    
    try:
        # Parse the timestamp
        ts = timestamp_str.replace('Z', '+00:00')
        dt = datetime.fromisoformat(ts)
        
        # Ensure it's UTC aware
        if dt.tzinfo is None:
            import datetime as dt_module
            dt = dt.replace(tzinfo=dt_module.timezone.utc)
        
        # Convert to EST/EDT (UTC-5 or UTC-4)
        if HAS_ZONEINFO:
            est_tz = ZoneInfo("America/New_York")
            dt_est = dt.astimezone(est_tz)
        else:
            # Manual offset (EST = UTC-5 standard time)
            # Note: This doesn't account for DST, but is close enough
            dt_est = dt - timedelta(hours=5)
        
        return dt_est.strftime("%m/%d %H:%M EST")
    except Exception as e:
        logger.error(f"Error converting timestamp: {e}")
        return timestamp_str[:16] if len(timestamp_str) > 16 else timestamp_str


def get_current_price(symbol: str) -> Optional[float]:
    """Get current market price for a symbol"""
    # Try to get from crypto_data.db first
    try:
        import sqlite3
        db_path = Path("crypto_data.db")
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Try different table names
            for table in ['crypto_prices', 'prices', 'market_data']:
                try:
                    cursor.execute(
                        f"SELECT price FROM {table} WHERE symbol = ? ORDER BY timestamp DESC LIMIT 1",
                        (symbol,)
                    )
                    result = cursor.fetchone()
                    if result and result[0]:
                        conn.close()
                        return float(result[0])
                except:
                    continue
            conn.close()
    except Exception as e:
        logger.debug(f"DB price lookup failed for {symbol}: {e}")
    
    # Try to get from consensus output
    try:
        consensus_file = DATA_DIR / "consensus_output.json"
        if consensus_file.exists():
            with open(consensus_file, 'r') as f:
                data = json.load(f)
                signals = data.get('signals', {})
                if symbol in signals:
                    sig_data = signals[symbol]
                    # Look for current price in signals
                    for sig in sig_data.get('signals', []):
                        if 'current_price' in sig:
                            return float(sig['current_price'])
                        if 'entry_price' in sig:
                            return float(sig['entry_price'])
    except Exception as e:
        logger.debug(f"Consensus price lookup failed for {symbol}: {e}")
    
    return None


def calculate_unrealized_pnl(pick: Dict, current_price: float) -> float:
    """Calculate unrealized P/L percentage"""
    entry = pick.get('entry_price', 0)
    if not entry or not current_price:
        return 0.0
    
    direction = pick.get('direction', 'LONG')
    if direction == 'LONG':
        return ((current_price - entry) / entry) * 100
    else:
        return ((entry - current_price) / entry) * 100


def format_pnl(pnl: float) -> str:
    """Format P/L with sign and color indicator"""
    if pnl is None:
        return "N/A"
    sign = "+" if pnl >= 0 else ""
    return f"{sign}{pnl:.2f}%"
TRACKER_FILE = DATA_DIR / "master_picks_tracker.json"
HISTORY_FILE = DATA_DIR / "master_picks_history.json"


@dataclass
class MasterPick:
    """Represents a single master-pick signal"""
    id: str
    timestamp: str
    symbol: str
    direction: str
    entry_price: float
    tp_price: float
    sl_price: float
    confidence: float
    systems: List[str]
    status: str = "active"  # active, hit_tp, hit_sl, expired, manual_close
    exit_price: Optional[float] = None
    exit_time: Optional[str] = None
    pnl_percent: Optional[float] = None
    notes: str = ""
    
    @property
    def r_multiple(self) -> Optional[float]:
        """Calculate R-multiple (profit in terms of risk units)"""
        if self.pnl_percent is None:
            return None
        risk_percent = abs(self.tp_price - self.sl_price) / self.entry_price * 100
        if risk_percent == 0:
            return None
        return self.pnl_percent / risk_percent
    
    @property
    def duration_hours(self) -> Optional[float]:
        """Calculate trade duration in hours"""
        if not self.exit_time:
            return None
        entry = datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))
        exit_t = datetime.fromisoformat(self.exit_time.replace('Z', '+00:00'))
        return (exit_t - entry).total_seconds() / 3600


class MasterPicksTracker:
    """Tracks and monitors master-picks performance"""
    
    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.tracker_data = self._load_tracker()
        self.history_data = self._load_history()
    
    def _load_tracker(self) -> Dict:
        """Load current tracker data"""
        if TRACKER_FILE.exists():
            try:
                with open(TRACKER_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading tracker: {e}")
        return {
            "version": "1.0",
            "last_updated": datetime.utcnow().isoformat(),
            "active_picks": [],
            "stats": {
                "total_picks": 0,
                "winning_picks": 0,
                "losing_picks": 0,
                "total_pnl": 0.0
            }
        }
    
    def _load_history(self) -> List[Dict]:
        """Load historical closed picks"""
        if HISTORY_FILE.exists():
            try:
                with open(HISTORY_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading history: {e}")
        return []
    
    def _save_tracker(self):
        """Save tracker data"""
        self.tracker_data["last_updated"] = datetime.utcnow().isoformat()
        with open(TRACKER_FILE, 'w') as f:
            json.dump(self.tracker_data, f, indent=2)
    
    def _save_history(self):
        """Save history data"""
        with open(HISTORY_FILE, 'w') as f:
            json.dump(self.history_data, f, indent=2)
    
    def add_pick(self, signal: Dict, systems: List[str]) -> str:
        """Add a new master-pick to tracking"""
        pick_id = f"{signal['symbol']}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        pick = MasterPick(
            id=pick_id,
            timestamp=datetime.utcnow().isoformat(),
            symbol=signal['symbol'],
            direction=signal['direction'],
            entry_price=signal.get('entry_price', 0),
            tp_price=signal.get('tp_price', 0),
            sl_price=signal.get('sl_price', 0),
            confidence=signal.get('consensus_score', signal.get('confidence', 0)),
            systems=systems,
            status="active"
        )
        
        # Add to active picks
        self.tracker_data["active_picks"].append(asdict(pick))
        self.tracker_data["stats"]["total_picks"] += 1
        self._save_tracker()
        
        logger.info(f"Added master-pick: {pick_id}")
        return pick_id
    
    def update_pick_status(self, pick_id: str, status: str, 
                           exit_price: Optional[float] = None,
                           notes: str = "") -> bool:
        """Update status of an active pick"""
        for pick in self.tracker_data["active_picks"]:
            if pick["id"] == pick_id:
                pick["status"] = status
                pick["exit_time"] = datetime.utcnow().isoformat()
                pick["exit_price"] = exit_price
                pick["notes"] = notes
                
                # Calculate PnL
                if exit_price:
                    if pick["direction"] == "LONG":
                        pick["pnl_percent"] = ((exit_price - pick["entry_price"]) / 
                                               pick["entry_price"] * 100)
                    else:
                        pick["pnl_percent"] = ((pick["entry_price"] - exit_price) / 
                                               pick["entry_price"] * 100)
                
                # Move to history if closed
                if status in ["hit_tp", "hit_sl", "expired", "manual_close"]:
                    self.history_data.append(pick)
                    self.tracker_data["active_picks"].remove(pick)
                    
                    # Update stats
                    if pick.get("pnl_percent", 0) > 0:
                        self.tracker_data["stats"]["winning_picks"] += 1
                    else:
                        self.tracker_data["stats"]["losing_picks"] += 1
                    self.tracker_data["stats"]["total_pnl"] += pick.get("pnl_percent", 0)
                
                self._save_tracker()
                self._save_history()
                return True
        
        return False
    
    def get_active_picks(self) -> List[Dict]:
        """Get all currently active picks"""
        return self.tracker_data["active_picks"]
    
    def get_recent_history(self, days: int = 30) -> List[Dict]:
        """Get picks from last N days"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        recent = []
        for pick in self.history_data:
            try:
                pick_time = datetime.fromisoformat(pick["timestamp"].replace('Z', '+00:00'))
                if pick_time >= cutoff:
                    recent.append(pick)
            except:
                continue
        return recent
    
    def calculate_health_score(self, days: int = 7) -> Dict:
        """
        Calculate comprehensive health score for master-picks
        Returns score 0-100 with breakdown
        """
        recent_picks = self.get_recent_history(days)
        
        # Add active picks that are older than 1 hour (avoid skewing with brand new picks)
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        for pick in self.tracker_data["active_picks"]:
            try:
                pick_time = datetime.fromisoformat(pick["timestamp"].replace('Z', '+00:00'))
                if pick_time < one_hour_ago:
                    recent_picks.append(pick)
            except:
                continue
        
        if not recent_picks:
            return {
                "overall_score": 50,  # Neutral when no data
                "grade": "N/A (No Data)",
                "win_rate": 0,
                "profit_factor": 0,
                "avg_trade": 0,
                "total_trades": 0,
                "gross_profit": 0,
                "gross_loss": 0,
                "period_days": days,
                "components": {
                    "win_rate_score": 50,
                    "profit_factor_score": 50,
                    "consistency_score": 50,
                    "recency_score": 50
                }
            }
        
        # Calculate metrics
        winning_trades = [p for p in recent_picks if p.get("pnl_percent", 0) > 0]
        losing_trades = [p for p in recent_picks if p.get("pnl_percent", 0) <= 0]
        
        total_trades = len(recent_picks)
        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
        
        gross_profit = sum(p.get("pnl_percent", 0) for p in winning_trades)
        gross_loss = abs(sum(p.get("pnl_percent", 0) for p in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        avg_trade = sum(p.get("pnl_percent", 0) for p in recent_picks) / total_trades
        
        # Calculate component scores (0-100)
        # Win rate: 50%+ is good (100 score), <30% is bad (0 score)
        win_rate_score = min(100, max(0, (win_rate - 30) / 20 * 100))
        
        # Profit factor: 2.0+ is excellent (100), 1.0 is breakeven (50), <0.5 is bad (0)
        if profit_factor == float('inf'):
            profit_factor_score = 100
        else:
            profit_factor_score = min(100, max(0, (profit_factor - 0.5) / 1.5 * 100))
        
        # Consistency: Standard deviation of returns (lower is better)
        if len(recent_picks) > 1:
            import statistics
            returns = [p.get("pnl_percent", 0) for p in recent_picks]
            try:
                std_dev = statistics.stdev(returns)
                # Lower std dev is better, target <5% std dev
                consistency_score = min(100, max(0, (10 - std_dev) / 10 * 100))
            except:
                consistency_score = 50
        else:
            consistency_score = 50
        
        # Recency: More recent trades = more reliable data
        # Scale from 0-20 trades (0 trades = 0 score, 20+ = 100)
        recency_score = min(100, total_trades / 20 * 100)
        
        # Calculate overall score (weighted average)
        overall_score = (
            win_rate_score * 0.35 +
            profit_factor_score * 0.30 +
            consistency_score * 0.20 +
            recency_score * 0.15
        )
        
        # Determine grade
        if overall_score >= 80:
            grade = "A (Excellent)"
        elif overall_score >= 65:
            grade = "B (Good)"
        elif overall_score >= 50:
            grade = "C (Fair)"
        elif overall_score >= 35:
            grade = "D (Poor)"
        else:
            grade = "F (Failing)"
        
        return {
            "overall_score": round(overall_score, 1),
            "grade": grade,
            "win_rate": round(win_rate, 1),
            "profit_factor": round(profit_factor, 2) if profit_factor != float('inf') else "∞",
            "avg_trade": round(avg_trade, 2),
            "total_trades": total_trades,
            "period_days": days,
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "components": {
                "win_rate_score": round(win_rate_score, 1),
                "profit_factor_score": round(profit_factor_score, 1),
                "consistency_score": round(consistency_score, 1),
                "recency_score": round(recency_score, 1)
            }
        }
    
    def get_active_picks_with_pnl(self) -> List[Dict]:
        """Get active picks with current unrealized P/L"""
        active = []
        for pick in self.tracker_data["active_picks"]:
            current_price = get_current_price(pick["symbol"])
            unrealized_pnl = None
            if current_price:
                unrealized_pnl = calculate_unrealized_pnl(pick, current_price)
            
            active.append({
                **pick,
                "current_price": current_price,
                "unrealized_pnl": unrealized_pnl,
                "entry_time_est": to_est(pick["timestamp"])
            })
        
        # Sort by unrealized P/L (best performers first)
        active.sort(key=lambda x: x.get("unrealized_pnl") or -999, reverse=True)
        return active
    
    def get_closed_picks_summary(self, days: int = 30) -> Dict:
        """Get summary of closed picks performance"""
        recent_closed = self.get_recent_history(days)
        
        if not recent_closed:
            return {
                "total_closed": 0,
                "winners": 0,
                "losers": 0,
                "win_rate": 0,
                "avg_realized_pnl": 0,
                "total_realized_pnl": 0,
                "profit_factor": 0,
                "best_trade": None,
                "worst_trade": None
            }
        
        winners = [p for p in recent_closed if p.get("pnl_percent", 0) > 0]
        losers = [p for p in recent_closed if p.get("pnl_percent", 0) <= 0]
        
        total_pnl = sum(p.get("pnl_percent", 0) for p in recent_closed)
        gross_profit = sum(p.get("pnl_percent", 0) for p in winners)
        gross_loss = abs(sum(p.get("pnl_percent", 0) for p in losers))
        
        best = max(recent_closed, key=lambda x: x.get("pnl_percent", -999)) if recent_closed else None
        worst = min(recent_closed, key=lambda x: x.get("pnl_percent", 999)) if recent_closed else None
        
        return {
            "total_closed": len(recent_closed),
            "winners": len(winners),
            "losers": len(losers),
            "win_rate": round(len(winners) / len(recent_closed) * 100, 1),
            "avg_realized_pnl": round(total_pnl / len(recent_closed), 2),
            "total_realized_pnl": round(total_pnl, 2),
            "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss > 0 else float('inf'),
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "best_trade": {
                "symbol": best["symbol"],
                "pnl": round(best.get("pnl_percent", 0), 2)
            } if best else None,
            "worst_trade": {
                "symbol": worst["symbol"],
                "pnl": round(worst.get("pnl_percent", 0), 2)
            } if worst else None
        }
    
    def format_health_embed(self) -> Dict:
        """Format health score as Discord embed with active picks"""
        health = self.calculate_health_score(days=7)
        
        # Color based on score
        if health["overall_score"] >= 70:
            color = 0x00ff00  # Green
            emoji = "[HEALTHY]"
        elif health["overall_score"] >= 50:
            color = 0xffaa00  # Orange
            emoji = "[CAUTION]"
        else:
            color = 0xff0000  # Red
            emoji = "[WARNING]"
        
        # Progress bar
        score = health["overall_score"]
        filled = int(score / 10)
        empty = 10 - filled
        progress_bar = "█" * filled + "░" * empty
        
        embed = {
            "title": f"{emoji} Master-Picks Health Score",
            "description": f"**{progress_bar} {score}/100**\nGrade: **{health['grade']}**",
            "color": color,
            "fields": [],
            "footer": {
                "text": f"Updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} | Use !closed command to see closed picks"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Add Active Picks section first (most important)
        active_picks = self.get_active_picks_with_pnl()
        if active_picks:
            active_lines = []
            total_unrealized = 0
            for pick in active_picks[:10]:  # Show top 10
                symbol = pick["symbol"]
                direction = pick["direction"]
                entry = pick["entry_price"]
                pnl = pick.get("unrealized_pnl")
                entry_time = pick.get("entry_time_est", "N/A")
                
                if pnl is not None:
                    pnl_str = format_pnl(pnl)
                    total_unrealized += pnl
                else:
                    pnl_str = "N/A"
                
                active_lines.append(
                    f"{symbol} {direction} | Entry: ${entry:,.2f} | P/L: {pnl_str} | {entry_time}"
                )
            
            active_value = "```\n" + "\n".join(active_lines) + "\n```"
            if len(active_picks) > 10:
                active_value += f"\n*...and {len(active_picks) - 10} more*"
            
            total_str = format_pnl(total_unrealized)
            embed["fields"].append({
                "name": f"Active Picks ({len(active_picks)}) - Unrealized P/L: {total_str}",
                "value": active_value,
                "inline": False
            })
        else:
            embed["fields"].append({
                "name": "Active Picks",
                "value": "No active master-picks at this time",
                "inline": False
            })
        
        # Add Closed Picks Rollup Summary
        closed_summary = self.get_closed_picks_summary(days=7)
        if closed_summary["total_closed"] > 0:
            closed_value = (
                f"```\n"
                f"Closed Trades:   {closed_summary['total_closed']}\n"
                f"Win Rate:        {closed_summary['win_rate']}% ({closed_summary['winners']}W/{closed_summary['losers']}L)\n"
                f"Profit Factor:   {closed_summary['profit_factor']}\n"
                f"Avg Realized:    {closed_summary['avg_realized_pnl']}%\n"
                f"Total Realized:  {format_pnl(closed_summary['total_realized_pnl'])}\n"
                f"```"
            )
            if closed_summary.get("best_trade"):
                closed_value += (
                    f"```diff\n"
                    f"+ Best:  {closed_summary['best_trade']['symbol']} {format_pnl(closed_summary['best_trade']['pnl'])}\n"
                    f"- Worst: {closed_summary['worst_trade']['symbol']} {format_pnl(closed_summary['worst_trade']['pnl'])}\n"
                    f"```"
                )
            
            embed["fields"].append({
                "name": f"Closed Picks Summary (7d)",
                "value": closed_value,
                "inline": False
            })
        
        # Add Component Scores (collapsed)
        embed["fields"].append({
            "name": "Component Scores",
            "value": (
                f"```\n"
                f"Win Rate:     {health['components']['win_rate_score']:.0f}/100\n"
                f"Profit Factor: {health['components']['profit_factor_score']:.0f}/100\n"
                f"Consistency:  {health['components']['consistency_score']:.0f}/100\n"
                f"Sample Size:  {health['components']['recency_score']:.0f}/100\n"
                f"```"
            ),
            "inline": True
        })
        
        return embed
    
    def format_closed_picks_embed(self, days: int = 30) -> Optional[Dict]:
        """Format closed picks as Discord embed for command response"""
        recent_closed = self.get_recent_history(days)
        
        if not recent_closed:
            return {
                "title": "Closed Master-Picks",
                "description": "No closed picks found in the last 30 days",
                "color": 0x95a5a6,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Sort by exit time (most recent first)
        recent_closed.sort(
            key=lambda x: x.get("exit_time", x["timestamp"]), 
            reverse=True
        )
        
        # Build closed picks list
        closed_lines = []
        for pick in recent_closed[:20]:  # Show last 20
            symbol = pick["symbol"]
            direction = pick["direction"]
            pnl = pick.get("pnl_percent", 0)
            status = pick.get("status", "closed")
            entry_time = to_est(pick["timestamp"])
            exit_time = to_est(pick.get("exit_time")) if pick.get("exit_time") else "N/A"
            
            pnl_str = format_pnl(pnl)
            status_indicator = "TP" if status == "hit_tp" else "SL" if status == "hit_sl" else status[:4]
            
            closed_lines.append(
                f"{symbol} {direction} | {pnl_str} ({status_indicator}) | {entry_time} -> {exit_time}"
            )
        
        # Get summary
        summary = self.get_closed_picks_summary(days)
        
        total_pnl_str = format_pnl(summary['total_realized_pnl'])
        
        embed = {
            "title": f"Closed Master-Picks (Last {days}d)",
            "description": f"**Total Realized P/L: {total_pnl_str}** | Win Rate: {summary['win_rate']}%",
            "color": 0x3498db if summary['total_realized_pnl'] >= 0 else 0xe74c3c,
            "fields": [
                {
                    "name": f"Trade History ({summary['total_closed']} total)",
                    "value": "```\n" + "\n".join(closed_lines) + "\n```",
                    "inline": False
                },
                {
                    "name": "Statistics",
                    "value": (
                        f"```\n"
                        f"Win Rate:       {summary['win_rate']}%\n"
                        f"Win/Loss:       {summary['winners']}/{summary['losers']}\n"
                        f"Profit Factor:  {summary['profit_factor']}\n"
                        f"Avg Trade:      {summary['avg_realized_pnl']}%\n"
                        f"Gross Profit:   +{summary['gross_profit']}%\n"
                        f"Gross Loss:     -{summary['gross_loss']}%\n"
                        f"```"
                    ),
                    "inline": False
                }
            ],
            "footer": {
                "text": f"Showing last {min(20, len(recent_closed))} of {len(recent_closed)} closed picks"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return embed


# Singleton instance
_tracker_instance: Optional[MasterPicksTracker] = None


def get_tracker() -> MasterPicksTracker:
    """Get singleton tracker instance"""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = MasterPicksTracker()
    return _tracker_instance


if __name__ == "__main__":
    # Test
    tracker = get_tracker()
    
    # Add test pick
    test_signal = {
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "entry_price": 50000,
        "tp_price": 55000,
        "sl_price": 48000,
        "consensus_score": 85
    }
    
    pick_id = tracker.add_pick(test_signal, ["alpha_engine", "mercury2"])
    print(f"Added pick: {pick_id}")
    
    # Get health score
    health = tracker.calculate_health_score()
    print(f"\nHealth Score: {health['overall_score']}/100 ({health['grade']})")
    print(f"Win Rate: {health['win_rate']}%")
    print(f"Profit Factor: {health['profit_factor']}")
