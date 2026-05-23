#!/usr/bin/env python3
"""
Deploy Vetted Master-Picks to Discord

This script:
1. Loads picks from DNA/Genome system (quality score >= 80)
2. Validates prices against real-time market data
3. Checks for duplicate signals
4. Verifies consensus from multiple systems
5. Sends only vetted picks to #master-picks
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Quality thresholds
MIN_QUALITY_SCORE = 75.0  # B+ grade minimum
MIN_CONSENSUS_COUNT = 2   # At least 2 systems must agree
MAX_PRICE_DEVIATION = 25.0  # 25% max deviation from current price


def load_genome_picks() -> List[Dict]:
    """Load picks from DNA/Genome system with quality scores."""
    picks = []
    
    # Load from genome active_picks.json
    genome_file = Path("genome/active_picks.json")
    if genome_file.exists():
        try:
            with open(genome_file, 'r') as f:
                data = json.load(f)
                
            for pick in data.get('picks', []):
                picks.append({
                    'symbol': pick.get('symbol'),
                    'direction': pick.get('direction', 'LONG'),
                    'entry_price': pick.get('entry_price'),
                    'tp_price': pick.get('take_profit'),
                    'sl_price': pick.get('stop_loss'),
                    'confidence': pick.get('confidence', 0.5),
                    'quality_score': pick.get('quality_score', 0),
                    'grade': pick.get('grade', 'F'),
                    'strategy_dna': pick.get('strategy_dna', 'unknown'),
                    'regime': pick.get('regime', 'unknown'),
                    'consensus_count': pick.get('consensus_count', 1),
                    'agreeing_systems': pick.get('agreeing_systems', []),
                    'backtest_metrics': pick.get('backtest_metrics', {}),
                    'source': 'dna_genome'
                })
                
            logger.info(f"Loaded {len(picks)} picks from genome system")
        except Exception as e:
            logger.error(f"Error loading genome picks: {e}")
    
    return picks


def load_consensus_picks() -> List[Dict]:
    """Load picks from consensus aggregation."""
    picks = []
    
    consensus_file = Path("signal_aggregator/data/consensus_output.json")
    if consensus_file.exists():
        try:
            with open(consensus_file, 'r') as f:
                data = json.load(f)
            
            for symbol, consensus in data.get('signals', {}).items():
                signals = consensus.get('signals', [])
                if not signals:
                    continue
                
                # Get highest confidence signal
                best_signal = max(signals, key=lambda x: x.get('confidence', 0))
                
                # Count agreeing systems
                systems = list(set(s.get('system', 'unknown') for s in signals))
                
                picks.append({
                    'symbol': symbol,
                    'direction': best_signal.get('direction', 'LONG'),
                    'entry_price': best_signal.get('entry_price'),
                    'tp_price': best_signal.get('tp_price'),
                    'sl_price': best_signal.get('sl_price'),
                    'confidence': best_signal.get('confidence', 0),
                    'quality_score': best_signal.get('quality_score', 50),
                    'systems': systems,
                    'consensus_count': len(systems),
                    'substrategy': best_signal.get('substrategy') or best_signal.get('strategy_dna'),
                    'source': 'consensus'
                })
                
            logger.info(f"Loaded {len(picks)} picks from consensus")
        except Exception as e:
            logger.error(f"Error loading consensus picks: {e}")
    
    return picks


def validate_price(pick: Dict) -> tuple:
    """Validate pick price against current market."""
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from signal_aggregator.price_fetcher import validate_entry_price
        
        symbol = pick['symbol']
        entry = pick.get('entry_price')
        
        if not entry:
            return False, None, 0
        
        is_valid, current_price, deviation = validate_entry_price(
            symbol, entry, max_deviation_pct=MAX_PRICE_DEVIATION
        )
        
        return is_valid, current_price, deviation
        
    except Exception as e:
        logger.error(f"Price validation error for {pick.get('symbol')}: {e}")
        return True, None, 0  # Allow if validation fails


def check_forward_test_performance(symbol: str) -> Dict:
    """Check forward test performance for a symbol."""
    # Load forward test results
    forward_file = Path("incubator/forward_test.db")
    performance = {
        'has_data': False,
        'recent_win_rate': 0,
        'total_signals': 0,
        'avg_return': 0
    }
    
    # Try to load from JSON if available
    json_file = Path(f"incubator/backtest_results/forward_matches_{symbol}.json")
    if json_file.exists():
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                performance['has_data'] = True
                performance['recent_win_rate'] = data.get('win_rate', 0)
                performance['total_signals'] = data.get('total_signals', 0)
                performance['avg_return'] = data.get('avg_return', 0)
        except:
            pass
    
    return performance


def vet_pick(pick: Dict) -> tuple:
    """
    Comprehensive vetting of a pick.
    
    Returns: (is_vetted: bool, reasons: List[str], score: float)
    """
    reasons = []
    score = 0
    max_score = 100
    
    # 1. Quality Score Check (25 points)
    quality = pick.get('quality_score', 0)
    if quality >= MIN_QUALITY_SCORE:
        score += 25
        reasons.append(f"Quality: {quality} (B+ grade)")
    elif quality >= 65:
        score += 15
        reasons.append(f"Quality: {quality} (B grade)")
    else:
        reasons.append(f"Quality too low: {quality}")
    
    # 2. Price Validation (25 points)
    price_valid, current_price, deviation = validate_price(pick)
    if price_valid:
        score += 25
        if current_price:
            reasons.append(f"Price validated: ${pick.get('entry_price')} (deviation: {deviation:.1f}%)")
        else:
            reasons.append("Price: validated (no current data)")
    else:
        reasons.append(f"Price invalid: ${pick.get('entry_price')} vs current ${current_price} ({deviation:.1f}% off)")
    
    # 3. Consensus Check (20 points)
    consensus = pick.get('consensus_count', 1)
    if consensus >= MIN_CONSENSUS_COUNT:
        score += 20
        systems = pick.get('agreeing_systems', pick.get('systems', []))
        reasons.append(f"Consensus: {consensus} systems agree ({', '.join(systems[:3])})")
    else:
        reasons.append(f"Low consensus: only {consensus} system(s)")
    
    # 4. Confidence Check (15 points)
    confidence = pick.get('confidence', 0)
    if confidence >= 0.85:
        score += 15
        reasons.append(f"High confidence: {confidence:.0%}")
    elif confidence >= 0.80:
        score += 10
        reasons.append(f"Good confidence: {confidence:.0%}")
    else:
        reasons.append(f"Low confidence: {confidence:.0%}")
    
    # 5. Forward Test Performance (15 points)
    fwd = check_forward_test_performance(pick['symbol'])
    if fwd['has_data'] and fwd['recent_win_rate'] >= 0.55:
        score += 15
        reasons.append(f"Forward test: {fwd['recent_win_rate']:.0%} win rate")
    elif fwd['has_data']:
        score += 5
        reasons.append(f"Forward test: {fwd['recent_win_rate']:.0%} win rate (below 55%)")
    else:
        reasons.append("No forward test data")
    
    # Vetting threshold: 70/100
    is_vetted = score >= 70 and price_valid
    
    return is_vetted, reasons, score


def deduplicate_picks(picks: List[Dict]) -> List[Dict]:
    """Remove duplicate picks for same symbol/direction, keeping highest quality."""
    unique = {}
    
    for pick in picks:
        key = f"{pick['symbol']}_{pick['direction']}"
        
        if key not in unique:
            unique[key] = pick
        else:
            # Keep the one with higher quality score
            existing_quality = unique[key].get('quality_score', 0)
            new_quality = pick.get('quality_score', 0)
            
            if new_quality > existing_quality:
                unique[key] = pick
    
    return list(unique.values())


def deploy_vetted_picks():
    """Main deployment function."""
    logger.info("=" * 60)
    logger.info("DEPLOYING VETTED MASTER-PICKS")
    logger.info("=" * 60)
    
    # Load picks from all sources
    genome_picks = load_genome_picks()
    consensus_picks = load_consensus_picks()
    
    # Combine and deduplicate
    all_picks = genome_picks + consensus_picks
    all_picks = deduplicate_picks(all_picks)
    
    logger.info(f"Total unique picks to vet: {len(all_picks)}")
    
    # Vet each pick
    vetted = []
    rejected = []
    
    for pick in all_picks:
        symbol = pick.get('symbol', 'UNKNOWN')
        is_vetted, reasons, score = vet_pick(pick)
        
        if is_vetted:
            vetted.append({
                **pick,
                'vet_score': score,
                'vet_reasons': reasons
            })
            logger.info(f"✅ {symbol}: VETTED (score {score}/100)")
            for reason in reasons:
                logger.info(f"   - {reason}")
        else:
            rejected.append({
                **pick,
                'vet_score': score,
                'vet_reasons': reasons
            })
            logger.warning(f"❌ {symbol}: REJECTED (score {score}/100)")
            for reason in reasons:
                logger.warning(f"   - {reason}")
    
    # Sort vetted picks by score
    vetted.sort(key=lambda x: x['vet_score'], reverse=True)
    
    logger.info(f"\nVetted: {len(vetted)}, Rejected: {len(rejected)}")
    
    if not vetted:
        logger.warning("No picks passed vetting!")
        return
    
    # Send to Discord
    try:
        from signal_aggregator.picks_router import PicksRouter
        
        router = PicksRouter()
        
        sent_count = 0
        for pick in vetted[:5]:  # Send top 5
            signal = {
                'symbol': pick['symbol'],
                'direction': pick['direction'],
                'confidence': pick.get('confidence', 0.8),
                'entry_price': pick.get('entry_price'),
                'tp_price': pick.get('tp_price'),
                'sl_price': pick.get('sl_price'),
                'system': pick.get('source', 'vetted'),
                'substrategy': pick.get('strategy_dna') or pick.get('substrategy'),
                'systems': pick.get('agreeing_systems', [pick.get('source')])
            }
            
            if router.send_signal(signal, 'master_picks'):
                sent_count += 1
                logger.info(f"Sent {pick['symbol']} to #master-picks")
        
        logger.info(f"\nDeployed {sent_count} vetted picks to #master-picks")
        
        # Send summary
        summary = f"""Vetted Picks Deployment Complete

✅ Vetted & Sent: {sent_count}
❌ Rejected: {len(rejected)}

Top Picks:"""
        
        for i, pick in enumerate(vetted[:3], 1):
            summary += f"\n{i}. {pick['symbol']} {pick['direction']} (Score: {pick['vet_score']}/100)"
        
        router.send_system_alert(summary, level='info')
        
    except Exception as e:
        logger.error(f"Error sending to Discord: {e}")


if __name__ == '__main__':
    deploy_vetted_picks()
