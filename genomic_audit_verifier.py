#!/usr/bin/env python3
"""
Genomic & FreshPicks Audit Trail Verifier
=========================================

Cross-verifies pre-computed genomic strategies against live audit trail data.
Identifies data integrity issues and validates forward performance.

Usage:
    python genomic_audit_verifier.py --full-check
    python genomic_audit_verifier.py --strategy gp_13b024246f61
    python genomic_audit_verifier.py --freshpicks-verify
"""

import json
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse

# Database paths
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
GENOME_DIR = PROJECT_ROOT / "genome"
PAPER_DIR = PROJECT_ROOT / "paper_trading" / "data"

DB_PATHS = {
    'audit': DATA_DIR / "audit_trail.db",
    'genetic': GENOME_DIR / "genetic_programmer.db",
    'mape': GENOME_DIR / "mape_evolver.db",
    'ensemble': GENOME_DIR / "ensemble_evolver.db",
    'paper': PAPER_DIR / "paper.db",
}

# Baby Strategies Registry
BABY_STRATEGIES = {
    'vwap_rsi_institutional': {
        'class_name': 'VWAPRSIInstitutionalStrategy',
        'module': 'baby_strategies.vwap_rsi_institutional',
        'category': 'MEAN_REVERSION',
        'expected_wr': 0.68,
        'expected_pf': 1.9,
    },
    'liquidation_cascade_contrarian': {
        'class_name': 'LiquidationCascadeContrarianStrategy',
        'module': 'baby_strategies.liquidation_cascade_contrarian',
        'category': 'STRUCTURAL',
        'expected_wr': 0.62,
        'expected_pf': 1.8,
    },
    'regime_sentinel_composite': {
        'class_name': 'RegimeSentinelCompositeStrategy',
        'module': 'baby_strategies.regime_sentinel_composite',
        'category': 'META_STRATEGY',
        'expected_wr': 0.75,
        'expected_pf': 2.2,
    },
    'rsi_pairs_arbitrage': {
        'class_name': 'RSIPairsArbitrageStrategy',
        'module': 'baby_strategies.rsi_pairs_arbitrage',
        'category': 'STATISTICAL_ARBITRAGE',
        'expected_wr': 0.74,
        'expected_pf': 2.2,
    },
}


@dataclass
class StrategyVerificationResult:
    """Result of verifying a strategy against audit trail"""
    strategy_id: str
    strategy_type: str
    source_db: str
    
    # Pre-computed metrics
    backtest_fitness: float
    backtest_win_rate: float
    backtest_sharpe: float
    
    # Live metrics from audit trail
    live_trades: int = 0
    live_wins: int = 0
    live_losses: int = 0
    live_win_rate: float = 0.0
    live_total_pnl: float = 0.0
    
    # Validation
    win_rate_delta: float = 0.0
    status: str = "UNKNOWN"  # VALIDATED, DEGRADED, INSUFFICIENT_DATA, NOT_TRACKED
    issues: List[str] = None
    
    def __post_init__(self):
        if self.issues is None:
            self.issues = []


class GenomicAuditVerifier:
    """Cross-verifies genomic systems against audit trail"""
    
    def __init__(self):
        self.connections = {}
        self.issues_found = []
        
    def connect_all(self):
        """Connect to all databases"""
        for name, path in DB_PATHS.items():
            if path.exists():
                self.connections[name] = sqlite3.connect(str(path))
                self.connections[name].row_factory = sqlite3.Row
            else:
                print(f"[WARN] Database not found: {path}")
    
    def close_all(self):
        """Close all connections"""
        for conn in self.connections.values():
            conn.close()
    
    def verify_gp_strategies(self) -> List[StrategyVerificationResult]:
        """Verify Genetic Programmer strategies against audit trail"""
        results = []
        
        if 'genetic' not in self.connections:
            print("[MISSING] genetic_programmer.db not available")
            return results
            
        if 'audit' not in self.connections:
            print("[MISSING] audit_trail.db not available")
            return results
        
        # Get all GP strategies
        gp_conn = self.connections['genetic']
        audit_conn = self.connections['audit']
        
        cursor = gp_conn.execute(
            "SELECT strategy_id, name, fitness_json, status, created_at FROM gp_strategies WHERE status = 'WINNER'"
        )
        strategies = cursor.fetchall()
        
        print(f"\n{'='*70}")
        print(f"GENETIC PROGRAMMER VERIFICATION ({len(strategies)} WINNER strategies)")
        print(f"{'='*70}")
        
        for strat in strategies:
            strategy_id = strat['strategy_id']
            name = strat['name']
            fitness_json = json.loads(strat['fitness_json'] or '{}')
            
            backtest_fitness = fitness_json.get('overall_fitness', 0)
            backtest_wr = fitness_json.get('win_rate', 0)
            backtest_sharpe = fitness_json.get('sharpe_ratio', 0)
            
            # Try to find live trades in audit trail
            # First check if strategy name appears in raw_picks
            audit_cursor = audit_conn.execute(
                """SELECT COUNT(*) as cnt, 
                          SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) as wins,
                          SUM(pnl_pct) as total_pnl
                   FROM consensus_picks 
                   WHERE strategy = ? AND status = 'CLOSED'""",
                (name,)
            )
            live_data = audit_cursor.fetchone()
            
            live_trades = live_data['cnt'] or 0
            live_wins = live_data['wins'] or 0
            live_losses = live_trades - live_wins
            live_wr = (live_wins / live_trades * 100) if live_trades > 0 else 0
            live_pnl = live_data['total_pnl'] or 0
            
            # Determine status
            issues = []
            if live_trades == 0:
                status = "NOT_TRACKED"
                issues.append("No live trades found in audit trail")
            elif live_trades < 10:
                status = "INSUFFICIENT_DATA"
                issues.append(f"Only {live_trades} trades - need 30 for validation")
            elif live_wr < backtest_wr - 15:
                status = "DEGRADED"
                issues.append(f"Live WR ({live_wr:.1f}%) significantly below backtest ({backtest_wr:.1f}%)")
            else:
                status = "VALIDATED"
            
            result = StrategyVerificationResult(
                strategy_id=strategy_id,
                strategy_type="gp",
                source_db="genetic_programmer",
                backtest_fitness=backtest_fitness,
                backtest_win_rate=backtest_wr,
                backtest_sharpe=backtest_sharpe,
                live_trades=live_trades,
                live_wins=live_wins,
                live_losses=live_losses,
                live_win_rate=live_wr,
                live_total_pnl=live_pnl,
                win_rate_delta=live_wr - backtest_wr,
                status=status,
                issues=issues
            )
            results.append(result)
            
            # Print summary
            status_icon = "[OK]" if status == "VALIDATED" else "[PENDING]" if status == "INSUFFICIENT_DATA" else "[DEGRADED]"
            print(f"\n{status_icon} {name}")
            print(f"   Backtest: Fitness={backtest_fitness:.3f}, WR={backtest_wr:.1f}%, Sharpe={backtest_sharpe:.2f}")
            print(f"   Live: {live_trades} trades, WR={live_wr:.1f}%, PnL={live_pnl:.2f}%")
            print(f"   Status: {status}")
            if issues:
                for issue in issues:
                    print(f"   [ISSUE] {issue}")
        
        return results
    
    def verify_baby_strategies(self) -> List[StrategyVerificationResult]:
        """
        Verify Baby Strategies module integration and audit trail presence.
        
        Checks:
        1. All baby strategy modules can be imported
        2. Strategy classes can be instantiated
        3. generate_signals method exists and is callable
        4. Strategies have audit trail entries (if available)
        """
        results = []
        
        print(f"\n{'='*70}")
        print(f"BABY STRATEGIES VERIFICATION ({len(BABY_STRATEGIES)} strategies)")
        print(f"{'='*70}")
        
        import importlib
        import sys
        
        # Add baby_strategies to path if needed
        baby_path = PROJECT_ROOT / "baby_strategies"
        if str(baby_path) not in sys.path:
            sys.path.insert(0, str(baby_path))
        
        for strategy_id, config in BABY_STRATEGIES.items():
            issues = []
            
            # Try to import the module
            try:
                module = importlib.import_module(strategy_id)
                strategy_class = getattr(module, config['class_name'])
                name_constant = getattr(module, 'NAME', strategy_id)
                
                # Try to instantiate
                instance = strategy_class()
                
                # Check generate_signals method
                if not hasattr(instance, 'generate_signals'):
                    issues.append("Missing generate_signals method")
                
                # Check audit trail if available
                live_trades = 0
                live_wins = 0
                live_pnl = 0.0
                
                if 'audit' in self.connections:
                    audit_conn = self.connections['audit']
                    try:
                        cursor = audit_conn.execute(
                            """SELECT COUNT(*) as cnt,
                                      SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) as wins,
                                      SUM(pnl_pct) as total_pnl
                               FROM consensus_picks 
                               WHERE strategy = ? AND status = 'CLOSED'""",
                            (name_constant,)
                        )
                        row = cursor.fetchone()
                        if row:
                            live_trades = row['cnt'] or 0
                            live_wins = row['wins'] or 0
                            live_pnl = row['total_pnl'] or 0
                    except Exception:
                        pass  # Table may not exist
                
                live_losses = live_trades - live_wins
                live_wr = (live_wins / live_trades * 100) if live_trades > 0 else 0
                
                # Determine status
                expected_wr = config['expected_wr'] * 100
                if live_trades == 0:
                    status = "NOT_TRACKED"
                elif live_trades < 10:
                    status = "INSUFFICIENT_DATA"
                    issues.append(f"Only {live_trades} trades - need 30 for validation")
                elif live_wr < expected_wr - 15:
                    status = "DEGRADED"
                    issues.append(f"Live WR ({live_wr:.1f}%) below expected ({expected_wr:.1f}%)")
                else:
                    status = "VALIDATED"
                
                result = StrategyVerificationResult(
                    strategy_id=strategy_id,
                    strategy_type="baby_strategy",
                    source_db="baby_strategies",
                    backtest_fitness=0,  # Baby strategies don't have GP fitness
                    backtest_win_rate=expected_wr,
                    backtest_sharpe=0,
                    live_trades=live_trades,
                    live_wins=live_wins,
                    live_losses=live_losses,
                    live_win_rate=live_wr,
                    live_total_pnl=live_pnl,
                    win_rate_delta=live_wr - expected_wr,
                    status=status,
                    issues=issues
                )
                results.append(result)
                
                # Print summary
                status_icon = "[OK]" if status == "VALIDATED" else "[PENDING]" if status in ("INSUFFICIENT_DATA", "NOT_TRACKED") else "[DEGRADED]"
                print(f"\n{status_icon} {name_constant}")
                print(f"   Class: {config['class_name']}")
                print(f"   Category: {config['category']}")
                print(f"   Expected: WR={expected_wr:.0f}%, PF={config['expected_pf']:.1f}")
                print(f"   Live: {live_trades} trades, WR={live_wr:.1f}%, PnL={live_pnl:.2f}%")
                print(f"   Status: {status}")
                if issues:
                    for issue in issues:
                        print(f"   [ISSUE] {issue}")
                
            except ImportError as e:
                print(f"\n[ERROR] {strategy_id}")
                print(f"   ERROR: Cannot import module - {e}")
                result = StrategyVerificationResult(
                    strategy_id=strategy_id,
                    strategy_type="baby_strategy",
                    source_db="baby_strategies",
                    backtest_fitness=0,
                    backtest_win_rate=config['expected_wr'] * 100,
                    backtest_sharpe=0,
                    status="IMPORT_ERROR",
                    issues=[f"Import failed: {e}"]
                )
                results.append(result)
            
            except Exception as e:
                print(f"\n[ERROR] {strategy_id}")
                print(f"   ERROR: {e}")
                result = StrategyVerificationResult(
                    strategy_id=strategy_id,
                    strategy_type="baby_strategy",
                    source_db="baby_strategies",
                    backtest_fitness=0,
                    backtest_win_rate=config['expected_wr'] * 100,
                    backtest_sharpe=0,
                    status="ERROR",
                    issues=[str(e)]
                )
                results.append(result)
        
        return results
    
    def verify_freshpicks(self) -> Dict:
        """Verify FreshPicks strategy claims against live data"""
        
        if 'paper' not in self.connections:
            print("[MISSING] paper.db not available")
            return {}
        
        paper_conn = self.connections['paper']
        
        # Get all FreshPicks positions
        cursor = paper_conn.execute(
            """SELECT * FROM positions 
               WHERE strategy LIKE '%freshpicks%' OR strategy_name LIKE '%freshpicks%'
               ORDER BY entry_date DESC"""
        )
        positions = cursor.fetchall()
        
        print(f"\n{'='*70}")
        print(f"FRESHPICKS VERIFICATION ({len(positions)} positions)")
        print(f"{'='*70}")
        
        if not positions:
            print("[MISSING] No FreshPicks positions found in paper.db")
            return {
                'positions_tracked': 0,
                'claimed_wr': 95.0,
                'actual_wr': 0.0,
                'claimed_expectancy': 1.61,
                'actual_avg_pnl': 0.0,
                'status': 'NO_DATA'
            }
        
        # Calculate actual performance
        wins = sum(1 for p in positions if p['pnl_pct'] and p['pnl_pct'] > 0)
        losses = sum(1 for p in positions if p['pnl_pct'] and p['pnl_pct'] <= 0)
        total = len(positions)
        actual_wr = (wins / total * 100) if total > 0 else 0
        
        total_pnl = sum(p['pnl_pct'] or 0 for p in positions)
        avg_pnl = total_pnl / total if total > 0 else 0
        
        # Check for state snapshot data
        has_snapshots = self._check_freshpicks_snapshots()
        
        print(f"\n📊 Performance Summary:")
        print(f"   Total Positions: {total}")
        print(f"   Wins: {wins}, Losses: {losses}")
        print(f"   Actual Win Rate: {actual_wr:.1f}% (Claimed: 95.0%)")
        print(f"   Actual Avg PnL: {avg_pnl:.2f}% (Claimed: +1.61%)")
        print(f"   Total Return: {total_pnl:.2f}%")
        
        issues = []
        if total < 30:
            issues.append(f"Insufficient sample size ({total} trades, need 30+)")
        if actual_wr < 80 and total > 5:
            issues.append(f"Win rate ({actual_wr:.1f}%) significantly below claim (95%)")
        if not has_snapshots:
            issues.append("No entry-time state snapshots found")
        
        status = "INSUFFICIENT_DATA" if total < 30 else "DEGRADED" if actual_wr < 80 else "VALIDATED"
        
        if issues:
            print(f"\n[ISSUES] Found:")
            for issue in issues:
                print(f"   - {issue}")
        
        # Show recent positions
        print(f"\n📋 Recent Positions:")
        for pos in positions[:5]:
            pnl = pos['pnl_pct'] or 0
            pnl_icon = "🟢" if pnl > 0 else "🔴"
            print(f"   {pnl_icon} {pos['symbol']} {pos['direction']}: {pnl:+.2f}% "
                  f"({pos['entry_date'][:10]} → {pos['exit_date'][:10] if pos['exit_date'] else 'OPEN'})")
        
        return {
            'positions_tracked': total,
            'claimed_wr': 95.0,
            'actual_wr': actual_wr,
            'claimed_expectancy': 1.61,
            'actual_avg_pnl': avg_pnl,
            'has_snapshots': has_snapshots,
            'status': status,
            'issues': issues
        }
    
    def _check_freshpicks_snapshots(self) -> bool:
        """Check if FreshPicks entry-time snapshots exist"""
        if 'audit' not in self.connections:
            return False
        
        cursor = self.connections['audit'].execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='freshpicks_snapshots'"
        )
        return cursor.fetchone()[0] > 0
    
    def check_data_integrity(self) -> List[Dict]:
        """Check for data integrity issues across databases"""
        issues = []
        
        print(f"\n{'='*70}")
        print(f"DATA INTEGRITY CHECK")
        print(f"{'='*70}")
        
        # Check 1: Strategy ID fragmentation
        if 'genetic' in self.connections and 'paper' in self.connections:
            gp_ids = set(r[0] for r in self.connections['genetic'].execute(
                "SELECT strategy_id FROM gp_strategies"
            ).fetchall())
            
            paper_ids = set(r[0] for r in self.connections['paper'].execute(
                "SELECT strategy_id FROM evolved_strategies WHERE strategy_type = 'gp'"
            ).fetchall())
            
            # Check for overlap
            overlap = gp_ids & paper_ids
            if not overlap:
                issues.append({
                    'severity': 'HIGH',
                    'issue': 'No strategy ID overlap between genetic_programmer and paper_trading',
                    'details': f'GP DB has {len(gp_ids)} strategies, Paper DB has {len(paper_ids)} GP strategies'
                })
                print("[HIGH] No strategy ID linkage between genetic_programmer.db and paper.db")
        
        # Check 2: Missing formula storage in audit trail
        if 'audit' in self.connections:
            cursor = self.connections['audit'].execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='consensus_picks'"
            )
            if cursor.fetchone()[0] > 0:
                cursor = self.connections['audit'].execute(
                    "SELECT COUNT(*) FROM consensus_picks WHERE strategy_formula IS NOT NULL"
                )
                count = cursor.fetchone()[0]
                if count == 0:
                    issues.append({
                        'severity': 'MEDIUM',
                        'issue': 'Strategy formulas not stored in consensus_picks',
                        'details': 'Cannot verify pre-computed logic was applied'
                    })
                    print("[MEDIUM] consensus_picks table exists but strategy_formula column is empty")
        
        # Check 3: Forward test validation table
        if 'audit' in self.connections:
            cursor = self.connections['audit'].execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='forward_test_validation'"
            )
            if cursor.fetchone()[0] == 0:
                issues.append({
                    'severity': 'MEDIUM',
                    'issue': 'forward_test_validation table does not exist',
                    'details': 'No structured way to compare backtest vs live performance'
                })
                print("[MEDIUM] forward_test_validation table missing")
        
        if not issues:
            print("[OK] No critical data integrity issues found")
        
        return issues
    
    def generate_report(self, output_file: str = "genomic_verification_report.json", include_baby: bool = True):
        """Generate comprehensive verification report"""
        
        self.connect_all()
        
        try:
            report = {
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'gp_verification': [asdict(r) for r in self.verify_gp_strategies()],
                'baby_strategies_verification': [asdict(r) for r in self.verify_baby_strategies()] if include_baby else [],
                'freshpicks_verification': self.verify_freshpicks(),
                'data_integrity_issues': self.check_data_integrity(),
            }
            
            # Calculate summary stats
            gp_results = report['gp_verification']
            baby_results = report['baby_strategies_verification']
            
            summary = {
                'total_strategies': len(gp_results) + len(baby_results),
            }
            
            if gp_results:
                gp_validated = sum(1 for r in gp_results if r['status'] == 'VALIDATED')
                gp_degraded = sum(1 for r in gp_results if r['status'] == 'DEGRADED')
                gp_untracked = sum(1 for r in gp_results if r['status'] == 'NOT_TRACKED')
                
                summary['gp_strategies'] = {
                    'total': len(gp_results),
                    'validated': gp_validated,
                    'degraded': gp_degraded,
                    'untracked': gp_untracked,
                    'validation_rate': (gp_validated / len(gp_results) * 100) if gp_results else 0
                }
            
            if baby_results:
                baby_validated = sum(1 for r in baby_results if r['status'] == 'VALIDATED')
                baby_import_errors = sum(1 for r in baby_results if 'IMPORT' in r['status'] or 'ERROR' in r['status'])
                baby_not_tracked = sum(1 for r in baby_results if r['status'] in ('NOT_TRACKED', 'INSUFFICIENT_DATA'))
                
                summary['baby_strategies'] = {
                    'total': len(baby_results),
                    'validated': baby_validated,
                    'import_errors': baby_import_errors,
                    'not_tracked': baby_not_tracked,
                    'ready_rate': ((len(baby_results) - baby_import_errors) / len(baby_results) * 100) if baby_results else 0
                }
            
            report['summary'] = summary
            
            # Save report
            output_path = PROJECT_ROOT / output_file
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            print(f"\n{'='*70}")
            print(f"REPORT SAVED: {output_path}")
            print(f"{'='*70}")
            
            return report
            
        finally:
            self.close_all()


def main():
    parser = argparse.ArgumentParser(description="Genomic & FreshPicks Audit Verifier")
    parser.add_argument("--full-check", action="store_true", help="Run full verification")
    parser.add_argument("--gp-verify", action="store_true", help="Verify GP strategies only")
    parser.add_argument("--baby-verify", action="store_true", help="Verify Baby Strategies only")
    parser.add_argument("--freshpicks-verify", action="store_true", help="Verify FreshPicks only")
    parser.add_argument("--integrity-check", action="store_true", help="Check data integrity only")
    parser.add_argument("--output", default="genomic_verification_report.json", help="Output file")
    parser.add_argument("--no-baby", action="store_true", help="Exclude baby strategies from full check")
    
    args = parser.parse_args()
    
    verifier = GenomicAuditVerifier()
    
    if args.full_check or (not args.gp_verify and not args.freshpicks_verify and not args.integrity_check and not args.baby_verify):
        verifier.generate_report(args.output, include_baby=not args.no_baby)
    elif args.gp_verify:
        verifier.connect_all()
        verifier.verify_gp_strategies()
        verifier.close_all()
    elif args.baby_verify:
        verifier.connect_all()
        verifier.verify_baby_strategies()
        verifier.close_all()
    elif args.freshpicks_verify:
        verifier.connect_all()
        verifier.verify_freshpicks()
        verifier.close_all()
    elif args.integrity_check:
        verifier.connect_all()
        verifier.check_data_integrity()
        verifier.close_all()


if __name__ == "__main__":
    main()
