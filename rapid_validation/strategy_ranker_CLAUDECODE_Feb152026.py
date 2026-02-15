#!/usr/bin/env python3
"""
STRATEGY RANKER - Auto-Promote Winners, Eliminate Losers
========================================================
Ranks strategies by performance and auto-promotes/eliminates them

CLAUDECODE_Feb152026
"""

import mysql.connector
import json
import os
import sys
from datetime import datetime, timezone
from typing import List, Dict

# Database configuration
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'favcreators', 'public', 'api'))
try:
    from events_db_config import events_servername, events_username, events_password, events_dbname
    DB_HOST = events_servername
    DB_USER = events_username
    DB_PASS = events_password
    DB_NAME = 'rapid_validation'
except:
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASS = os.getenv('DB_PASS', '')
    DB_NAME = 'rapid_validation'


class StrategyRanker:
    """
    Ranks strategies and auto-promotes/eliminates based on performance
    """

    PROMOTION_CRITERIA = {
        'min_trades': 100,
        'min_win_rate': 60.0,
        'min_profit_factor': 1.5,
        'min_sharpe_ratio': 1.2,
        'max_drawdown': -15.0
    }

    ELIMINATION_CRITERIA = {
        'min_trades': 50,
        'max_win_rate': 40.0,
        'max_profit_factor': 0.8,
        'max_consecutive_losses': 15
    }

    def __init__(self):
        self.db = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME
        )

    def get_all_strategy_stats(self) -> List[Dict]:
        """Get all strategy stats"""
        cursor = self.db.cursor(dictionary=True)
        cursor.execute("""
            SELECT *
            FROM rapid_strategy_stats
            ORDER BY status DESC, sharpe_ratio DESC, win_rate DESC
        """)
        return cursor.fetchall()

    def rank_strategies(self) -> Dict:
        """Rank and categorize strategies"""
        stats = self.get_all_strategy_stats()

        promoted = []
        testing = []
        eliminated = []

        for strategy in stats:
            # Check for promotion
            if (strategy['total_trades'] >= self.PROMOTION_CRITERIA['min_trades'] and
                strategy['win_rate'] >= self.PROMOTION_CRITERIA['min_win_rate'] and
                strategy['profit_factor'] >= self.PROMOTION_CRITERIA['min_profit_factor'] and
                strategy['sharpe_ratio'] >= self.PROMOTION_CRITERIA['min_sharpe_ratio']):

                if strategy['status'] != 'PROMOTED':
                    self.promote_strategy(strategy)
                promoted.append(strategy)

            # Check for elimination
            elif (strategy['total_trades'] >= self.ELIMINATION_CRITERIA['min_trades'] and
                  (strategy['win_rate'] <= self.ELIMINATION_CRITERIA['max_win_rate'] or
                   strategy['profit_factor'] <= self.ELIMINATION_CRITERIA['max_profit_factor'] or
                   strategy['consecutive_losses'] >= self.ELIMINATION_CRITERIA['max_consecutive_losses'])):

                if strategy['status'] != 'ELIMINATED':
                    self.eliminate_strategy(strategy)
                eliminated.append(strategy)

            # Still testing
            else:
                testing.append(strategy)

        return {
            'promoted': promoted,
            'testing': testing,
            'eliminated': eliminated,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    def promote_strategy(self, strategy: Dict):
        """Mark strategy as PROMOTED"""
        cursor = self.db.cursor()
        cursor.execute("""
            UPDATE rapid_strategy_stats
            SET status = 'PROMOTED'
            WHERE id = %s
        """, (strategy['id'],))
        self.db.commit()
        print(f"✅ PROMOTED: {strategy['strategy']} ({strategy['exit_strategy']}) - {strategy['win_rate']:.1f}% WR, {strategy['profit_factor']:.2f} PF")

    def eliminate_strategy(self, strategy: Dict):
        """Mark strategy as ELIMINATED"""
        cursor = self.db.cursor()
        cursor.execute("""
            UPDATE rapid_strategy_stats
            SET status = 'ELIMINATED'
            WHERE id = %s
        """, (strategy['id'],))
        self.db.commit()
        print(f"❌ ELIMINATED: {strategy['strategy']} ({strategy['exit_strategy']}) - {strategy['win_rate']:.1f}% WR, {strategy['profit_factor']:.2f} PF")

    def generate_leaderboard(self):
        """Generate leaderboard report"""
        rankings = self.rank_strategies()

        print(f"\n{'='*80}")
        print(f"STRATEGY LEADERBOARD - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"{'='*80}\n")

        # PROMOTED
        print(f"✅ PROMOTED TO LIVE (Ready for Real Money) - {len(rankings['promoted'])} strategies")
        print(f"{'-'*80}")
        if rankings['promoted']:
            print(f"{'Strategy':<25} {'Exit':<10} {'Trades':<8} {'WR%':<8} {'PF':<8} {'Sharpe':<8} {'P&L'}")
            print(f"{'-'*80}")
            for s in rankings['promoted']:
                print(f"{s['strategy']:<25} {s['exit_strategy']:<10} {s['total_trades']:<8} "
                      f"{s['win_rate']:<8.1f} {s['profit_factor']:<8.2f} {s['sharpe_ratio']:<8.2f} "
                      f"${s['total_pnl_usd']:.2f}")
        else:
            print("  (None yet - need 100+ trades)")
        print()

        # TESTING
        print(f"⏳ STILL TESTING (Needs More Data) - {len(rankings['testing'])} strategies")
        print(f"{'-'*80}")
        if rankings['testing']:
            print(f"{'Strategy':<25} {'Exit':<10} {'Trades':<8} {'WR%':<8} {'PF':<8} {'Sharpe':<8} {'P&L'}")
            print(f"{'-'*80}")
            for s in sorted(rankings['testing'], key=lambda x: x['sharpe_ratio'], reverse=True)[:10]:
                print(f"{s['strategy']:<25} {s['exit_strategy']:<10} {s['total_trades']:<8} "
                      f"{s['win_rate']:<8.1f} {s['profit_factor']:<8.2f} {s['sharpe_ratio']:<8.2f} "
                      f"${s['total_pnl_usd']:.2f}")
        print()

        # ELIMINATED
        print(f"❌ ELIMINATED (Failed Threshold) - {len(rankings['eliminated'])} strategies")
        print(f"{'-'*80}")
        if rankings['eliminated']:
            print(f"{'Strategy':<25} {'Exit':<10} {'Trades':<8} {'WR%':<8} {'PF':<8} {'P&L'}")
            print(f"{'-'*80}")
            for s in rankings['eliminated'][:5]:
                print(f"{s['strategy']:<25} {s['exit_strategy']:<10} {s['total_trades']:<8} "
                      f"{s['win_rate']:<8.1f} {s['profit_factor']:<8.2f} ${s['total_pnl_usd']:.2f}")
        print()

        print(f"{'='*80}\n")

        return rankings

    def save_rankings(self, rankings: Dict, output_file: str = 'rapid_validation/rankings_CLAUDECODE_Feb152026.json'):
        """Save rankings to JSON"""
        with open(output_file, 'w') as f:
            json.dump(rankings, f, indent=2, default=str)
        print(f"✅ Saved rankings to {output_file}")


def main():
    ranker = StrategyRanker()
    rankings = ranker.generate_leaderboard()
    ranker.save_rankings(rankings)


if __name__ == '__main__':
    main()
