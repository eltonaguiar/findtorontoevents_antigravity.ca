#!/usr/bin/env python3
"""
Run All DNA Variations - Master Script
======================================

Runs all DNA analysis modes in sequence:
1. Reverse engineer today's winners
2. Find universal multi-symbol patterns  
3. Run massive evolution with expanded genes
4. Generate live signals from best patterns
5. Update Discord with new picks

Usage:
    python run_all_dna_variations.py          # Run all
    python run_all_dna_variations.py --quick  # Fast mode (fewer iterations)
    python run_all_dna_variations.py --live   # Generate live signals only
"""

import subprocess
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)
logger = logging.getLogger('DNAMaster')


def run_command(cmd: list, description: str, timeout: int = 300):
    """Run a command with logging."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Running: {description}")
    logger.info(f"Command: {' '.join(cmd)}")
    logger.info('='*60)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if result.stdout:
            logger.info(result.stdout)
        if result.stderr:
            logger.warning(result.stderr)
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout after {timeout}s")
        return False
    except Exception as e:
        logger.error(f"Error: {e}")
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--quick', action='store_true', help='Fast mode')
    parser.add_argument('--live', action='store_true', help='Live signals only')
    parser.add_argument('--skip-reverse', action='store_true', help='Skip reverse engineering')
    parser.add_argument('--skip-universal', action='store_true', help='Skip universal finder')
    parser.add_argument('--skip-evolution', action='store_true', help='Skip evolution')
    args = parser.parse_args()
    
    results = {}
    start_time = datetime.now()
    
    logger.info("🧬 DNA MASSIVE VARIATION SYSTEM")
    logger.info(f"Started: {start_time}")
    
    # 1. Reverse Engineer Today's Winners
    if not args.skip_reverse and not args.live:
        logger.info("\n🔍 PHASE 1: Reverse Engineering Today's Winners")
        success = run_command(
            [sys.executable, "genome/reverse_engineer_today.py", "--analyze"],
            "Reverse Engineer Analysis",
            timeout=180 if args.quick else 300
        )
        results['reverse_engineer'] = success
        
        if success:
            try:
                with open('genome/results/reverse_engineered_today.json') as f:
                    data = json.load(f)
                    logger.info(f"✅ Found {data['summary']['total_opportunities']} hypothetical winners")
                    logger.info(f"✅ Total PnL opportunity: {data['summary']['total_pnl_pct']:.1f}%")
            except:
                pass
    
    # 2. Universal Strategy Finder
    if not args.skip_universal and not args.live:
        logger.info("\n🌍 PHASE 2: Universal Multi-Symbol Pattern Discovery")
        success = run_command(
            [sys.executable, "genome/universal_strategy_finder.py", "--run"],
            "Universal Pattern Finder",
            timeout=300 if args.quick else 600
        )
        results['universal'] = success
        
        if success:
            try:
                with open('genome/results/universal_patterns.json') as f:
                    data = json.load(f)
                    logger.info(f"✅ Found {len(data.get('patterns', []))} universal patterns")
            except:
                pass
    
    # 3. Enhanced DNA Evolution
    if not args.skip_evolution and not args.live:
        logger.info("\n🧬 PHASE 3: Enhanced DNA Evolution")
        pop_size = 500 if args.quick else 2000
        generations = 50 if args.quick else 200
        
        success = run_command(
            [
                sys.executable, 
                "genome/dna_engine_enhanced_v2.py",
                "--evolve",
                "--population", str(pop_size),
                "--generations", str(generations),
                "--output", "genome/results/enhanced_evolution_v2.json"
            ],
            f"DNA Evolution (pop={pop_size}, gen={generations})",
            timeout=600 if args.quick else 1800
        )
        results['evolution'] = success
    
    # 4. Generate Live Signals
    logger.info("\n📡 PHASE 4: Generating Live Signals")
    success = run_command(
        [sys.executable, "genome/universal_strategy_finder.py", "--live"],
        "Live Signal Generation",
        timeout=120
    )
    results['live_signals'] = success
    
    # 5. Aggregate Results
    logger.info("\n📊 PHASE 5: Aggregating Results")
    
    # Load all results
    all_signals = []
    all_patterns = []
    
    # From reverse engineer
    try:
        with open('genome/results/reverse_engineered_today.json') as f:
            rev_data = json.load(f)
            all_patterns.extend(rev_data.get('top_patterns', []))
            logger.info(f"Loaded {len(rev_data.get('top_patterns', []))} reverse engineered patterns")
    except:
        pass
    
    # From universal finder
    try:
        with open('genome/results/universal_patterns.json') as f:
            uni_data = json.load(f)
            all_patterns.extend(uni_data.get('patterns', [])[:20])
            logger.info(f"Loaded {len(uni_data.get('patterns', []))} universal patterns")
    except:
        pass
    
    # From live signals
    try:
        with open('genome/results/live_signals_universal.json') as f:
            live_data = json.load(f)
            all_signals = live_data.get('signals', [])
            logger.info(f"Loaded {len(all_signals)} live signals")
    except:
        pass
    
    # Create master output
    master_output = {
        'generated_at': datetime.utcnow().isoformat(),
        'phases_completed': sum(1 for v in results.values() if v),
        'phases_total': len(results),
        'summary': {
            'patterns_discovered': len(all_patterns),
            'live_signals': len(all_signals),
            'reverse_engineered_opportunities': rev_data.get('summary', {}).get('total_opportunities', 0) if 'rev_data' in dir() else 0
        },
        'top_patterns': sorted(all_patterns, key=lambda x: x.get('total_pnl_pct', 0) + x.get('universal_score', 0)*10, reverse=True)[:20],
        'live_signals': all_signals[:20]
    }
    
    output_path = Path('genome/results/dna_master_output.json')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(master_output, f, indent=2, default=str)
    
    logger.info(f"\n💾 Master output saved to {output_path}")
    
    # 6. Print Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    logger.info("\n" + "="*60)
    logger.info("🏁 DNA MASSIVE VARIATION COMPLETE")
    logger.info("="*60)
    logger.info(f"Duration: {duration/60:.1f} minutes")
    logger.info(f"Phases Completed: {sum(1 for v in results.values() if v)}/{len(results)}")
    logger.info(f"Total Patterns: {len(all_patterns)}")
    logger.info(f"Live Signals: {len(all_signals)}")
    
    if all_signals:
        logger.info("\n🎯 TOP 5 LIVE SIGNALS:")
        for i, sig in enumerate(all_signals[:5], 1):
            r_r = abs(sig['tp'] - sig['entry']) / abs(sig['entry'] - sig['sl'])
            logger.info(f"{i}. {sig['symbol']} {sig['direction']} | "
                       f"Entry: ${sig['entry']:.2f} | "
                       f"R:R {r_r:.1f} | "
                       f"Conf: {sig['confidence']:.0%}")
    
    logger.info("\n" + "="*60)
    logger.info("Next Steps:")
    logger.info("  1. Review patterns in genome/results/dna_master_output.json")
    logger.info("  2. Deploy top patterns to paper trading")
    logger.info("  3. Update Discord webhooks with new signals")
    logger.info("="*60)


if __name__ == "__main__":
    main()
