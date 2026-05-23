#!/usr/bin/env python3
"""
/audit-daily.py -- 3-Day Pick Review with Asset Class Analysis
==============================================================

Performs daily audit review of closed and open picks:
- Recent picks (last 3 days) grouped by asset class
- Significant movers identification (>5% moves)
- Entry condition analysis at open date/time (EST)
- Swarm agent consultation for pick quality evaluation
- Strategy/system dataflow investigation

Sources:
  - MySQL ejaguiar1_stocks dump file (15GB SQL)
  - Local JSON pick files (active_picks, closed_picks)
  - ejaguiar1_backtests database (reduced-size, faster queries)

Usage:
    python /audit-daily.py                    # Standard 3-day review
    python /audit-daily.py --days 7           # Extended 7-day review
    python /audit-daily.py --debug             # Verbose output
    python /audit-daily.py --swarm             # Enable agent swarm review
    python /audit-daily.py --moves 3           # 3% threshold for significant moves

Output:
    /audit-daily-report-{DATE}.html         # Dashboard-style HTML report
    /audit-daily-report-{DATE}.md           # Markdown summary with action items
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import textwrap
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Configuration
SQL_FILE = r"C:\Users\zerou\Downloads\10_123_0_33 (4).sql"
REPO_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = REPO_ROOT / "audit_reports"

SIGNIFICANT_MOVE_PCT = 5.0  # Percentage threshold for "moved significantly"

# Dynamic EST/EDT: Toronto observes EDT (UTC-4) Mar-Nov, EST (UTC-5) Nov-Mar.
# Uses time.localtime().tm_isdst: 1=DST, 0=standard, -1=unknown (transition edge).
_is_dst = time.localtime().tm_isdst
EST_TIMEZONE = timezone(timedelta(hours=-4 if _is_dst in (1, -1) else -5))

# Asset class patterns
ASSET_PATTERNS = {
    'CRYPTO': re.compile(r'(BTC|ETH|SOL|XRP|ADA|DOT|LINK|UNI|AAVE|LDO|RNDR|FET|AGIX|OCEAN|NUM|GRT|1INCH|SUSHI|CRV|COMP|MKR|YFI|BAL|LRC|IMX|DYDX|SNX|PERP|APE|BLUR|LOOKS|CHZ|ENJ|SAND|MANA|AXS|GALA|MAGIC|ILV|GMT|JASMY|SHIB|DOGE|PEPE|FLOKI|BONK|WIF|BOME|MEME|SQUAD|TURBO|GROK|AI|GPT|BARD|GEMINI|CLAUDE|WLD|ARKM|TAO|RPL|LIDO|STETH|WETH|WBTC|ETHBTC|ETHUSDT|BTCUSDT|TON|NEAR|APT|SUI|OP|ARB|STRK|TIA|SEI|INJ|RUNE|ATOM|FIL|HBAR|ALGO|XTZ|EOS|FLOW|QNT|EGLD|STX|MINA|ROSE|KAVA|OSMO|JUP|PYTH|JTO|WEN)', re.I),
    'FOREX': re.compile(r'(EUR|GBP|JPY|CHF|AUD|CAD|NZD|USD)[\s/]?(EUR|GBP|JPY|CHF|AUD|CAD|NZD|USD)', re.I),
    'COMMODITY': re.compile(r'(GOLD|SILVER|OIL|GAS|COPPER|WHEAT|CORN|SOY|SUGAR|COFFEE|XAU|XAG|CL|NG|HG|ZC|ZS|SB|KC)', re.I),
    'INDEX': re.compile(r'(SPY|QQQ|IWM|DIA|VIX|ES|NQ|YM|RTY|SPX|NDX|DJI|RUT|FTSE|DAX|CAC|NIKKEI|HSI)', re.I),
}

ETF_SYMBOLS = frozenset([
    'SPY', 'QQQ', 'IWM', 'VXX', 'UVXY', 'TLT', 'GLD', 'SLV', 'USO', 'UNG',
    'XLF', 'XLE', 'XLK', 'XLI', 'XLU', 'XLP', 'XLB', 'XRT', 'SMH', 'SOXX',
    'ARKK', 'ARKG', 'ARKW', 'ARKF', 'ARKQ', 'ARKX'
])

BOND_SYMBOLS = frozenset([
    'TLT', 'IEF', 'SHY', 'LQD', 'HYG', 'JNK', 'EMB', 'TLH', 'MUB', 'BND'
])


def classify_asset_class(symbol: str, strategy: Optional[str] = None) -> str:
    """Classify a symbol into its asset class."""
    if not symbol:
        return 'UNKNOWN'
    
    symbol_upper = symbol.upper()
    
    # Bond symbols pre-check
    if symbol_upper in BOND_SYMBOLS:
        return 'BOND'
    
    # ETF check
    if symbol_upper in ETF_SYMBOLS:
        return 'ETF'
    
    # Pattern matching
    if ASSET_PATTERNS['CRYPTO'].search(symbol_upper):
        return 'CRYPTO'
    if ASSET_PATTERNS['FOREX'].search(symbol_upper):
        return 'FOREX'
    if ASSET_PATTERNS['COMMODITY'].search(symbol_upper):
        return 'COMMODITY'
    if ASSET_PATTERNS['INDEX'].search(symbol_upper):
        return 'INDEX'
    
    # Strategy-based classification
    if strategy:
        strategy_lower = strategy.lower()
        if any(x in strategy_lower for x in ['crypto', 'btc', 'eth', 'sniper', 'meme']):
            return 'CRYPTO'
        if any(x in strategy_lower for x in ['forex', 'fx', 'currency']):
            return 'FOREX'
        if any(x in strategy_lower for x in ['commodity', 'gold', 'oil']):
            return 'COMMODITY'
        if any(x in strategy_lower for x in ['bond', 'fixed income', 'treasury']):
            return 'BOND'
        if any(x in strategy_lower for x in ['etf', 'sector', 'rotation']):
            return 'ETF'
    
    # Default: STOCKS
    # Most picks are stocks if they don't match above
    return 'STOCK'


def extract_picks_from_sql(sql_file: str, days_back: int = 3) -> List[Dict]:
    """
    Extract recent picks from the large SQL dump without loading it all.
    Uses streaming search with date filtering.
    """
    cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    
    picks = []
    tables_to_scan = ['alpha_picks', 'trading_picks', 'bt_backtest_trades', 'picks']
    
    print(f"[INFO] Scanning SQL file for picks newer than {cutoff_date}...")
    print(f"[INFO] This may take several minutes for large files...")
    
    # Stream through the file looking for INSERT statements
    chunk_size = 1024 * 1024  # 1MB chunks
    current_table = None
    buffer = ""
    total_scanned = 0
    
    try:
        with open(sql_file, 'r', encoding='utf-8', errors='ignore') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                
                buffer += chunk
                total_scanned += len(chunk)
                
                # Process complete lines
                lines = buffer.split('\n')
                buffer = lines[-1]  # Keep incomplete line
                
                for line in lines[:-1]:
                    # Check for INSERT statements
                    if line.startswith('INSERT INTO'):
                        # Determine which table
                        for table in tables_to_scan:
                            if f'`{table}`' in line or f'"{table}"' in line.lower():
                                current_table = table
                                break
                        
                        # Parse and filter by date
                        if current_table:
                            pick = parse_insert_line(line, current_table)
                            if pick and pick.get('date', '') >= cutoff_date:
                                picks.append(pick)
                
                # Progress indicator
                if total_scanned % (100 * 1024 * 1024) == 0:  # Every 100MB
                    print(f"[INFO] Scanned {total_scanned / (1024**3):.1f} GB...")
                    
    except Exception as e:
        print(f"[WARN] Error scanning SQL file: {e}")
    
    print(f"[INFO] Found {len(picks)} recent picks")
    return picks


def parse_insert_line(line: str, table: str) -> Optional[Dict]:
    """Parse an INSERT statement and extract pick data."""
    try:
        # Extract values between parentheses
        match = re.search(r'VALUES \((.+)\)', line, re.IGNORECASE)
        if not match:
            return None
        
        values_str = match.group(1)
        values = parse_sql_values(values_str)
        
        # Map based on table schema
        if table == 'alpha_picks':
            if len(values) < 5:
                return None
            return {
                'symbol': values[1],
                'strategy': values[2],
                'date': values[3].strip("'").replace("'", ""),
                'entry_price': parse_decimal(values[4]) if values[4] != 'NULL' else 0,
                'score': parse_decimal(values[5]) if len(values) > 5 and values[5] != 'NULL' else 0,
                'conviction': values[6].strip("'").replace("'", "") if len(values) > 6 else '',
                'table_source': table,
                'status': 'OPEN',
                'source': 'alpha_picks'
            }
        
        elif table == 'trading_picks':
            # Schema: id, symbol, direction, strategy, entry_price, take_profit, stop_loss, ...
            return {
                'symbol': values[1] if len(values) > 1 else '',
                'direction': values[2] if len(values) > 2 else 'LONG',
                'strategy': values[3] if len(values) > 3 else '',
                'entry_price': parse_decimal(values[4]) if len(values) > 4 else 0,
                'take_profit': parse_decimal(values[5]) if len(values) > 5 else 0,
                'stop_loss': parse_decimal(values[6]) if len(values) > 6 else 0,
                'confidence': parse_decimal(values[7]) if len(values) > 7 else 0,
                'elite_score': int(values[8]) if len(values) > 8 and values[8] != 'NULL' else 0,
                'trust_score': int(values[9]) if len(values) > 9 and values[9] != 'NULL' else 0,
                'category': values[10] if len(values) > 10 else '',
                'source_system': values[11] if len(values) > 11 else '',
                'date': values[16][:10] if len(values) > 16 and values[16] != 'NULL' else datetime.now().strftime('%Y-%m-%d'),
                'status': values[12] if len(values) > 12 else 'OPEN',
                'pnl_pct': parse_decimal(values[13]) if len(values) > 13 else 0,
                'table_source': table,
                'source': 'trading_picks'
            }
        
        elif table == 'bt_backtest_trades':
            return {
                'symbol': values[1] if len(values) > 1 else '',
                'strategy': values[2] if len(values) > 2 else '',
                'direction': values[3] if len(values) > 3 else 'LONG',
                'entry_price': parse_decimal(values[4]) if len(values) > 4 else 0,
                'exit_price': parse_decimal(values[5]) if len(values) > 5 else 0,
                'entry_date': values[6].strip("'").replace("'", "") if len(values) > 6 else '',
                'exit_date': values[7].strip("'").replace("'", "") if len(values) > 7 else '',
                'pnl_pct': parse_decimal(values[8]) if len(values) > 8 else 0,
                'exit_reason': values[9] if len(values) > 9 else '',
                'date': values[6].strip("'").replace("'", "")[:10] if len(values) > 6 else datetime.now().strftime('%Y-%m-%d'),
                'status': 'CLOSED',
                'table_source': table,
                'source': 'backtest_trades'
            }
        
    except Exception as e:
        return None


def parse_sql_values(values_str: str) -> List[str]:
    """Parse SQL VALUES tuple into individual values."""
    values = []
    current = ''
    in_quotes = False
    
    for i, char in enumerate(values_str):
        if char == "'" and (i == 0 or values_str[i-1] != '\\'):
            in_quotes = not in_quotes
            current += char
        elif char == ',' and not in_quotes:
            values.append(current.strip())
            current = ''
        else:
            current += char
    
    if current.strip():
        values.append(current.strip())
    
    return values


def parse_decimal(val_str: str) -> float:
    """Parse a decimal value from SQL format."""
    try:
        return float(val_str.strip("'"))
    except (ValueError, TypeError):
        return 0.0


def load_local_picks(days_back: int = 3) -> List[Dict]:
    """Load picks from local JSON files."""
    picks = []
    cutoff = datetime.now() - timedelta(days=days_back)
    
    # Try multiple locations for pick files
    pick_files = [
        REPO_ROOT / 'alpha_engine' / 'data' / 'active_picks.json',
        REPO_ROOT / 'alpha_engine' / 'data' / 'closed_picks.json',
        REPO_ROOT / 'data' / 'active_picks.json',
        REPO_ROOT / 'data' / 'closed_picks.json',
        REPO_ROOT / 'audit_trail' / 'data' / 'universal_resolved_picks.json',
    ]
    
    for pf in pick_files:
        if pf.exists():
            try:
                with open(pf, 'r') as f:
                    data = json.load(f)
                    
                records = data if isinstance(data, list) else data.get('picks', [])
                
                for record in records:
                    # Filter by date if available
                    created_at = record.get('created_at') or record.get('date') or ''
                    if created_at:
                        try:
                            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            if dt < cutoff:
                                continue
                        except:
                            pass
                    
                    picks.append({
                        'symbol': record.get('symbol', ''),
                        'strategy': record.get('strategy', record.get('strategy_name', '')),
                        'direction': record.get('direction', 'LONG'),
                        'entry_price': float(record.get('entry_price', 0) or 0),
                        'take_profit': float(record.get('take_profit', 0) or 0),
                        'stop_loss': float(record.get('stop_loss', 0) or 0),
                        'status': record.get('status', 'OPEN'),
                        'pnl_pct': float(record.get('pnl_pct', 0) or 0),
                        'score': float(record.get('score', 0) or 0),
                        'confidence': float(record.get('confidence', 0) or 0),
                        'elite_score': int(record.get('elite_score', 0) or 0),
                        'trust_score': int(record.get('trust_score', 0) or 0),
                        'date': record.get('date', datetime.now().strftime('%Y-%m-%d')),
                        'exit_reason': record.get('exit_reason', ''),
                        'source_system': record.get('source_system', ''),
                        'source': str(pf.stem),
                        'file_path': str(pf)
                    })
                    
            except Exception as e:
                print(f"[WARN] Could not load {pf}: {e}")
    
    return picks


def identify_significant_movers(picks: List[Dict], threshold_pct: float) -> List[Dict]:
    """Identify picks with significant price movements."""
    movers = []
    
    for pick in picks:
        pnl_pct = pick.get('pnl_pct', 0) or 0
        entry = pick.get('entry_price', 0)
        
        # Check if current pnl exceeds threshold
        if abs(pnl_pct) >= threshold_pct:
            pick['significant_move'] = True
            pick['move_magnitude'] = pnl_pct
            pick['move_direction'] = 'UP' if pnl_pct > 0 else 'DOWN'
            movers.append(pick)
        
        # Also check TP/SL proximity for open picks
        elif pick.get('status', '').upper() in ['OPEN', 'ACTIVE'] and entry > 0:
            tp = pick.get('take_profit', 0)
            sl = pick.get('stop_loss', 0)
            
            if tp > 0 or sl > 0:
                # Calculate distance to tp/sl
                if pick.get('direction', 'LONG').upper() == 'LONG':
                    tp_dist = ((tp - entry) / entry * 100) if tp and entry else 0
                    sl_dist = ((sl - entry) / entry * 100) if sl and entry else 0
                else:  # SHORT
                    tp_dist = ((entry - tp) / entry * 100) if tp and entry else 0
                    sl_dist = ((entry - sl) / entry * 100) if sl and entry else 0
                
                # Check if near TP/SL (within 50% of target)
                if tp_dist > 0 and pnl_pct >= tp_dist * 0.5:
                    pick['significant_move'] = True
                    pick['move_magnitude'] = pnl_pct
                    pick['move_direction'] = 'UP'
                    pick['move_reason'] = 'near_tp'
                    movers.append(pick)
                elif sl_dist < 0 and pnl_pct <= sl_dist * 0.5:
                    pick['significant_move'] = True
                    pick['move_magnitude'] = pnl_pct
                    pick['move_direction'] = 'DOWN'
                    pick['move_reason'] = 'near_sl'
                    movers.append(pick)
    
    return movers


def group_picks_by_asset_class(picks: List[Dict]) -> Dict[str, List[Dict]]:
    """Group picks by their asset class."""
    grouped = defaultdict(list)
    
    for pick in picks:
        asset_class = classify_asset_class(pick.get('symbol', ''), pick.get('strategy', ''))
        pick['asset_class'] = asset_class
        grouped[asset_class].append(pick)
    
    return dict(grouped)


def get_strategy_dataflow(strategy_name: str) -> Dict:
    """
    Investigate the base strategy and dataflow.
    Look for strategy definitions, data sources, and upstream systems.
    """
    dataflow = {
        'strategy_name': strategy_name,
        'found_in': [],
        'data_sources': [],
        'upstream_systems': [],
        'algorithm_records': [],
    }
    
    # Search for strategy in codebase
    strategy_patterns = [
        REPO_ROOT / 'alpha_engine' / 'data' / 'systems',
        REPO_ROOT / 'systems',
        REPO_ROOT / 'strategies',
    ]
    
    for pattern_path in strategy_patterns:
        if pattern_path.exists():
            for py_file in pattern_path.rglob('*.py'):
                try:
                    with open(py_file, 'r', errors='ignore') as f:
                        content = f.read()
                    if strategy_name.lower() in content.lower():
                        dataflow['found_in'].append(str(py_file))
                except Exception:
                    pass
    
    # Check JSON configs
    config_files = [
        REPO_ROOT / 'alpha_engine' / 'data' / 'strategy_config.json',
        REPO_ROOT / 'strategy_registry.json',
    ]
    
    for cf in config_files:
        if cf.exists():
            try:
                with open(cf, 'r') as f:
                    configs = json.load(f)
                for key, value in configs.items():
                    if strategy_name.lower() in key.lower() or strategy_name.lower() in str(value).lower():
                        dataflow['algorithm_records'].append({key: value})
            except Exception:
                pass
    
    return dataflow


def spawn_swarm_review(pick: Dict) -> Dict:
    """
    Spawn agent swarm to review a specific pick.
    Uses local free models for review.
    """
    review = {
        'pick_id': f"{pick.get('symbol', '')}_{pick.get('date', '')}",
        'agent_reviewed': False,
        'review_notes': '',
        'recommendation': 'UNKNOWN',
        'confidence': 0,
    }
    
    # Only spawn swarm for significant movers
    if not pick.get('significant_move'):
        review['review_notes'] = "No significant move - basic review only"
        review['recommendation'] = 'HOLD'
        return review
    
    # Build context for agent review
    symbol = pick.get('symbol', '')
    direction = pick.get('direction', 'LONG')
    entry = pick.get('entry_price', 0)
    current_pnl = pick.get('pnl_pct', 0)
    move = pick.get('move_magnitude', 0)
    asset_class = pick.get('asset_class', 'STOCK')
    
    prompt = f"""
    Review this trading pick for entry quality:
    
    SYMBOL: {symbol}
    DIRECTION: {direction}
    ENTRY PRICE: {entry}
    CURRENT P&L: {current_pnl:.2f}%
    MOVE MAGNITUDE: {move:.2f}%
    ASSET CLASS: {asset_class}
    STRATEGY: {pick.get('strategy', 'unknown')}
    
    QUESTIONS:
    1. Was the entry timing (based on open date {pick.get('date', 'unknown')}) appropriate?
    2. Given the {move:.2f}% move, was this a good entry or should it have been avoided?
    3. What market conditions might have contributed to this move?
    4. Should this strategy be adjusted for future similar setups?
    
    Provide:
    - Verdict: GOOD_ENTRY / BAD_ENTRY / UNCLEAR
    - Confidence: 0-100
    - Explanation: 2-3 sentences
    """
    
    review['prompt'] = prompt
    review['review_notes'] = "Agent swarm review queued"
    review['recommendation'] = 'PENDING'
    review['confidence'] = 50
    
    # TODO: Integrate with .ruflo/orchestrator.py for actual swarm execution
    # For now, structure is ready
    
    return review


def generate_html_report(report: Dict, output_path: Path) -> None:
    """Generate an HTML dashboard report."""
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Audit Daily Report - {report['date']}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #e2e8f0; line-height: 1.6; }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #60a5fa; margin-bottom: 10px; font-size: 2rem; }}
        h2 {{ color: #94a3b8; margin: 30px 0 15px; font-size: 1.5rem; border-bottom: 2px solid #334155; padding-bottom: 10px; }}
        h3 {{ color: #60a5fa; margin: 20px 0 10px; }}
        .header {{ background: linear-gradient(135deg, #1e293b, #0f172a); padding: 30px; border-radius: 12px; margin-bottom: 30px; }}
        .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }}
        .summary-card {{ background: #1e293b; padding: 20px; border-radius: 8px; border-left: 4px solid #60a5fa; }}
        .summary-card h4 {{ color: #94a3b8; font-size: 0.875rem; margin-bottom: 8px; }}
        .summary-card .value {{ font-size: 2rem; font-weight: bold; color: #e2e8f0; }}
        .summary-card.positive {{ border-left-color: #22c55e; }}
        .summary-card.negative {{ border-left-color: #ef4444; }}
        .summary-card.warning {{ border-left-color: #f59e0b; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th {{ background: #1e293b; color: #60a5fa; padding: 12px; text-align: left; font-weight: 600; }}
        td {{ padding: 12px; border-bottom: 1px solid #334155; }}
        tr:hover {{ background: #1e293b; }}
        .symbol {{ font-weight: bold; color: #60a5fa; }}
        .up {{ color: #22c55e; }}
        .down {{ color: #ef4444; }}
        .asset-class {{ display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }}
        .asset-crypto {{ background: #fef3c7; color: #92400e; }}
        .asset-stock {{ background: #dbeafe; color: #1e40af; }}
        .asset-forex {{ background: #d1fae5; color: #065f46; }}
        .asset-commodity {{ background: #fce7f3; color: #be185d; }}
        .asset-bond {{ background: #ede9fe; color: #5b21b6; }}
        .asset-etf {{ background: #f3e8ff; color: #7e22ce; }}
        .asset-index {{ background: #f1f5f9; color: #475569; }}
        .move-significant {{ background: rgba(245, 158, 11, 0.2); }}
        .section {{ background: #1e293b; padding: 20px; border-radius: 12px; margin-bottom: 20px; }}
        .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; }}
        .badge-open {{ background: #22c55e; }}
        .badge-closed {{ background: #ef4444; }}
        .badge-won {{ background: #22c55e; }}
        .badge-lost {{ background: #ef4444; }}
        .swarm-review {{ background: #252f4a; padding: 15px; border-left: 3px solid #60a5fa; margin: 10px 0; border-radius: 0 8px 8px 0; }}
        .pre {{ background: #0f172a; padding: 15px; border-radius: 8px; overflow-x: auto; font-family: 'Courier New', monospace; font-size: 0.875rem; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 Audit Daily Report</h1>
            <p style="color: #94a3b8;">Generated: {report['generated_at']} | Period: Last {report['days_back']} days</p>
        </div>
        
        <div class="summary-grid">
            <div class="summary-card">
                <h4>Total Picks</h4>
                <div class="value">{report['total_picks']}</div>
            </div>
            <div class="summary-card {('positive' if report['total_pnl'] > 0 else 'negative')}">
                <h4>Total P&L</h4>
                <div class="value">{report['total_pnl']:+.2f}%</div>
            </div>
            <div class="summary-card positive">
                <h4>Open Picks</h4>
                <div class="value">{report['open_count']}</div>
            </div>
            <div class="summary-card {'negative' if report['closed_count'] == 0 else 'positive'}">
                <h4>Closed Picks</h4>
                <div class="value">{report['closed_count']}</div>
            </div>
            <div class="summary-card warning">
                <h4>Significant Movers</h4>
                <div class="value">{report['significant_movers_count']}</div>
            </div>
        </div>
"""
    
    # Add per-asset-class sections
    for asset_class, asset_data in report.get('by_asset_class', {}).items():
        html += f"""
        <div class="section">
            <h2>📊 {asset_class} Picks ({len(asset_data['picks'])})</h2>
            <div class="summary-grid">
                <div class="summary-card {'positive' if asset_data['avg_pnl'] > 0 else 'negative'}">
                    <h4>Avg P&L</h4>
                    <div class="value">{asset_data['avg_pnl']:+.2f}%</div>
                </div>
                <div class="summary-card">
                    <h4>Win Rate</h4>
                    <div class="value">{asset_data.get('win_rate', 0):.1f}%</div>
                </div>
                <div class="summary-card warning">
                    <h4>Significant Movers</h4>
                    <div class="value">{len(asset_data.get('movers', []))}</div>
                </div>
            </div>
        """
        
        if asset_data['picks']:
            html += """
            <table>
                <thead>
                    <tr>
                        <th>Symbol</th>
                        <th>Strategy</th>
                        <th>Entry Date</th>
                        <th>P&L</th>
                        <th>Status</th>
                        <th>Review</th>
                    </tr>
                </thead>
                <tbody>
            """
            
            for pick in asset_data['picks'][:10]:  # First 10 picks
                symbol = pick.get('symbol', 'N/A')
                pnl = pick.get('pnl_pct', 0)
                status = pick.get('status', 'OPEN')
                significant = pick.get('significant_move', False)
                
                html += f"""
                    <tr class="{'move-significant' if significant else ''}">
                        <td><span class="symbol">{symbol}</span></td>
                        <td>{pick.get('strategy', 'unknown')}</td>
                        <td>{pick.get('date', 'N/A')}</td>
                        <td class="{'up' if pnl > 0 else 'down'}">{pnl:+.2f}%</td>
                        <td><span class="badge badge-{status.lower()}">{status}</span></td>
                        <td>{'⚠️ Significant' if significant else '✓ Normal'}</td>
                    </tr>
                """
            
            html += "</tbody></table>"
        
        html += "</div>"
    
    # Significant Movers section
    if report.get('significant_movers_with_reviews'):
        html += """
        <div class="section">
            <h2>⚠️ Significant Movers (Agent Review)</h2>
        """
        
        for item in report['significant_movers_with_reviews']:
            pick = item['pick']
            review = item['review']
            
            html += f"""
            <div class="swarm-review">
                <h3>{pick.get('symbol', 'N/A')} - {pick.get('move_magnitude', 0):+.2f}% Move</h3>
                <p><strong>Strategy:</strong> {pick.get('strategy', 'unknown')} | 
                   <strong>Asset Class:</strong> {pick.get('asset_class', 'STOCK')} |
                   <strong>Direction:</strong> {pick.get('direction', 'LONG')}</p>
                <p><strong>Entry:</strong> {pick.get('entry_price', 0)} | 
                   <strong>Current P&L:</strong> {pick.get('pnl_pct', 0):+.2f}%</p>
                <p><strong>Agent Verdict:</strong> {review.get('recommendation', 'PENDING')} 
                   (Confidence: {review.get('confidence', 0)}%)</p>
                <div class="pre">{review.get('review_notes', 'Review pending...')}</div>
            </div>
            """
        
        html += "</div>"
    
    html += """
    </div>
</body>
</html>
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"[INFO] HTML report saved to: {output_path}")


def generate_markdown_report(report: Dict, output_path: Path) -> None:
    """Generate a Markdown summary report with action items."""
    
    md = f"""# Audit Daily Report - {report['date']}

**Generated:** {report['generated_at']}  
**Period:** Last {report['days_back']} days  
**Threshold:** {report['significant_move_threshold']}% for significant moves

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Total Picks | {report['total_picks']} |
| Total P&L | {report['total_pnl']:+.2f}% |
| Open Picks | {report['open_count']} |
| Closed Picks | {report['closed_count']} |
| Significant Movers | {report['significant_movers_count']} |

---

## Asset Class Breakdown

"""
    
    for asset_class, asset_data in report.get('by_asset_class', {}).items():
        movers_count = len(asset_data.get('movers', []))
        
        md += f"""### {asset_class} ({len(asset_data['picks'])} picks)

- **Avg P&L:** {asset_data['avg_pnl']:+.2f}%
- **Win Rate:** {asset_data.get('win_rate', 0):.1f}%
- **Significant Movers:** {movers_count}

| Symbol | Strategy | Entry Date | P&L | Status |
|--------|----------|------------|-----|--------|
"""
        
        for pick in asset_data['picks'][:10]:
            symbol = pick.get('symbol', 'N/A')
            strategy = pick.get('strategy', 'unknown')[:20]
            date = pick.get('date', 'N/A')
            pnl = pick.get('pnl_pct', 0)
            status = pick.get('status', 'OPEN')
            significant = '⚠️' if pick.get('significant_move') else ''
            
            md += f"| {symbol} | {strategy} | {date} | {pnl:+.2f}% | {status} {significant} |\n"
        
        md += "\n"
    
    # Significant Movers section
    if report.get('significant_movers_with_reviews'):
        md += """## ⚠️ Significant Movers (Agent Review)

"""
        
        for item in report['significant_movers_with_reviews']:
            pick = item['pick']
            review = item['review']
            
            md += f"""### {pick.get('symbol', 'N/A')}: {pick.get('move_magnitude', 0):+.2f}% Move

- **Strategy:** {pick.get('strategy', 'unknown')}
- **Asset Class:** {pick.get('asset_class', 'STOCK')}
- **Direction:** {pick.get('direction', 'LONG')}
- **Entry Price:** {pick.get('entry_price', 0)}
- **Current P&L:** {pick.get('pnl_pct', 0):+.2f}%
- **Agent Verdict:** {review.get('recommendation', 'PENDING')} (Confidence: {review.get('confidence', 0)}%)

**Review Notes:**
> {review.get('review_notes', 'Review pending...')}

---

"""
    
    # Action Items
    md += """## Action Items

"""
    
    action_items = []
    
    for asset_class, asset_data in report.get('by_asset_class', {}).items():
        if asset_data.get('movers'):
            movers = asset_data['movers']
            avg_move = sum(m.get('move_magnitude', 0) for m in movers) / len(movers) if movers else 0
            
            action_items.append(
                f"Review {len(movers)} significant movers in {asset_class} "
                f"(avg move: {avg_move:+.1f}%) - evaluate strategy effectiveness"
            )
        
        if asset_data['avg_pnl'] < -1.0:
            action_items.append(
                f"Investigate {asset_class} strategy underperformance "
                f"(avg P&L: {asset_data['avg_pnl']:+.2f}%)"
            )
    
    if action_items:
        for i, item in enumerate(action_items, 1):
            md += f"{i}. {item}\n"
    else:
        md += "No critical action items identified.\n"
    
    md += """

## Data Sources

- SQL Dump: `10_123_0_33 (4).sql`
- Local Pick Files: alpha_engine/data/*.json
- Strategy Configs: alpha_engine/data/strategy_config.json
- Algorithm Registry: strategy_registry.json

---

*Generated by /audit-daily.py*
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(md)
    
    print(f"[INFO] Markdown report saved to: {output_path}")


def run_swarm_orchestrator(reviews: List[Dict]) -> List[Dict]:
    """
    Spawn ruflo swarm orchestrator for agent execution on significant picks.
    Writes reviews to temp JSON, calls .ruflo/orchestrator.py, reads back results.
    """
    if not reviews:
        return reviews
    
    orchestrator_path = REPO_ROOT / '.ruflo' / 'orchestrator.py'
    if not orchestrator_path.exists():
        print("[WARN] .ruflo/orchestrator.py not found — swarm reviews queued only")
        return reviews
    
    try:
        # Write review context to temp JSON
        review_payload = []
        for item in reviews:
            p = item['pick']
            review_payload.append({
                'symbol': p.get('symbol', ''),
                'strategy': p.get('strategy', 'unknown'),
                'direction': p.get('direction', 'LONG'),
                'entry_price': p.get('entry_price', 0),
                'pnl_pct': p.get('pnl_pct', 0),
                'move_magnitude': p.get('move_magnitude', 0),
                'asset_class': p.get('asset_class', 'STOCK'),
                'date': p.get('date', ''),
                'prompt': item['review'].get('prompt', ''),
            })
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tf:
            json.dump({'reviews': review_payload, 'mode': 'audit_daily'}, tf)
            temp_path = tf.name
        
        result = subprocess.run(
            [sys.executable, str(orchestrator_path),
             '--swarm', 'audit', '--input', temp_path],
            capture_output=True, text=True, timeout=300,
            cwd=str(REPO_ROOT)
        )
        
        if result.returncode == 0 and result.stdout.strip():
            try:
                swarm_output = json.loads(result.stdout)
                for i, item in enumerate(reviews):
                    if i < len(swarm_output.get('results', [])):
                        sw = swarm_output['results'][i]
                        item['review']['recommendation'] = sw.get('verdict', 'PENDING')
                        item['review']['confidence'] = sw.get('confidence', 50)
                        item['review']['review_notes'] = sw.get('explanation', '')
                        item['review']['agent_reviewed'] = True
            except json.JSONDecodeError:
                print(f"[WARN] Swarm output not valid JSON — using queued reviews")
        else:
            print(f"[WARN] Swarm orchestrator failed (rc={result.returncode}) — using queued reviews")
        
        # Cleanup temp file
        try:
            os.unlink(temp_path)
        except OSError:
            pass
            
    except FileNotFoundError:
        print("[WARN] Python not found for subprocess — reviews queued")
    except subprocess.TimeoutExpired:
        print("[WARN] Swarm orchestrator timed out after 5min — reviews queued")
    except Exception as e:
        print(f"[WARN] Swarm orchestrator error: {e} — reviews queued")
    
    return reviews


def main():
    parser = argparse.ArgumentParser(
        description="3-Day Pick Review with Asset Class Analysis"
    )
    parser.add_argument('--days', type=int, default=3,
                        help='Number of days to look back (default: 3)')
    parser.add_argument('--moves', type=float, default=SIGNIFICANT_MOVE_PCT,
                        help=f'Percentage threshold for significant moves (default: {SIGNIFICANT_MOVE_PCT})')
    parser.add_argument('--swarm', action='store_true',
                        help='Enable agent swarm review for significant movers')
    parser.add_argument('--sql-file', type=str, default=SQL_FILE,
                        help=f'Path to MySQL dump file (default: {SQL_FILE})')
    parser.add_argument('--output-dir', type=str, default=str(OUTPUT_DIR),
                        help=f'Output directory for reports')
    parser.add_argument('--debug', action='store_true',
                        help='Enable verbose debug output')
    
    args = parser.parse_args()
    
    print(f"=" * 80)
    print(f"AUDIT DAILY - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} EST")
    print(f"=" * 80)
    print(f"[INFO] Days back: {args.days}")
    print(f"[INFO] Significant move threshold: {args.moves}%")
    print(f"[INFO] Source SQL: {args.sql_file}")
    print(f"[INFO] Swarm enabled: {args.swarm}")
    print(f"-" * 80)
    
    # Ensure output directory exists
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load picks from multiple sources
    all_picks = []
    
    # 1. Local JSON files (fastest)
    print("\n[PHASE 1] Loading local pick files...")
    local_picks = load_local_picks(args.days)
    all_picks.extend(local_picks)
    print(f"[OK] Loaded {len(local_picks)} picks from local files")
    
    # 2. SQL dump (only if requested - can be slow on 15GB file)
    if args.sql_file and Path(args.sql_file).exists():
        print("\n[PHASE 2] Scanning SQL dump...")
        print("[WARN] This may take 10-30 minutes on a 15GB file")
        response = input("Continue SQL scan? (y/n): ") if not args.debug else 'y'
        if response.lower() == 'y':
            sql_picks = extract_picks_from_sql(args.sql_file, args.days)
            all_picks.extend(sql_picks)
            print(f"[OK] Loaded {len(sql_picks)} picks from SQL")
    else:
        print("\n[PHASE 2] SKIPPED: SQL file not found")
    
    if not all_picks:
        print("\n[ERROR] No picks loaded. Exiting.")
        sys.exit(1)
    
    # Deduplicate picks by symbol+date
    seen = {}
    unique_picks = []
    for p in all_picks:
        key = f"{p.get('symbol', '')}_{p.get('date', '')}_{p.get('strategy', '')}"
        if key not in seen:
            seen[key] = p
            unique_picks.append(p)
    
    print(f"\n[OK] Total unique picks: {len(unique_picks)}")
    
    # Identify significant movers
    print(f"\n[PHASE 3] Identifying significant movers (>={args.moves}%)...")
    significant_movers = identify_significant_movers(unique_picks, args.moves)
    print(f"[OK] Found {len(significant_movers)} significant movers")
    
    # Group by asset class
    print(f"\n[PHASE 4] Grouping by asset class...")
    by_asset_class = group_picks_by_asset_class(unique_picks)
    print(f"[OK] Found {len(by_asset_class)} asset classes: {', '.join(by_asset_class.keys())}")
    
    # Calculate stats
    total_pnl = sum(p.get('pnl_pct', 0) for p in unique_picks)
    open_count = sum(1 for p in unique_picks if p.get('status', '').upper() in ['OPEN', 'ACTIVE'])
    closed_count = len(unique_picks) - open_count
    
    # Per-asset-class stats
    by_asset_class_formatted = {}
    for ac, picks in by_asset_class.items():
        ac_pnl = sum(p.get('pnl_pct', 0) for p in picks)
        ac_avg = ac_pnl / len(picks) if picks else 0
        
        # Get movers for this asset class
        ac_movers = [p for p in significant_movers if p.get('asset_class') == ac]
        
        # Calculate win rate for closed picks
        closed_picks = [p for p in picks if p.get('status', '').upper() not in ['OPEN', 'ACTIVE']]
        winners = [p for p in closed_picks if p.get('pnl_pct', 0) > 0]
        win_rate = (len(winners) / len(closed_picks) * 100) if closed_picks else 0
        
        by_asset_class_formatted[ac] = {
            'picks': picks,
            'count': len(picks),
            'total_pnl': ac_pnl,
            'avg_pnl': ac_avg,
            'movers': ac_movers,
            'win_rate': win_rate,
        }
    
    # Agent swarm review for significant movers
    print(f"\n[PHASE 5] Agent swarm review for significant movers...")
    significant_with_reviews = []
    
    if args.swarm:
        for pick in significant_movers[:10]:  # Limit to top 10 for swarm review
            review = spawn_swarm_review(pick)
            
            # Add strategy dataflow investigation
            dataflow = get_strategy_dataflow(pick.get('strategy', ''))
            
            significant_with_reviews.append({
                'pick': pick,
                'review': review,
                'dataflow': dataflow
            })
            
            print(f"[OK] Reviewed {pick.get('symbol', 'N/A')}: {review.get('recommendation', 'PENDING')}")
        
        # Run actual swarm if available
        significant_with_reviews = run_swarm_orchestrator(significant_with_reviews)
    else:
        print("[INFO] Swarm review skipped (use --swarm to enable)")
    
    # Build report
    date_str = datetime.now().strftime('%Y-%m-%d')
    report = {
        'date': date_str,
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'days_back': args.days,
        'significant_move_threshold': args.moves,
        'total_picks': len(unique_picks),
        'total_pnl': total_pnl,
        'open_count': open_count,
        'closed_count': closed_count,
        'significant_movers_count': len(significant_movers),
        'by_asset_class': by_asset_class_formatted,
        'significant_movers_with_reviews': significant_with_reviews,
    }
    
    # Generate reports
    print(f"\n[PHASE 6] Generating reports...")
    
    html_path = output_dir / f"audit-daily-report-{date_str}.html"
    generate_html_report(report, html_path)
    
    md_path = output_dir / f"audit-daily-report-{date_str}.md"
    generate_markdown_report(report, md_path)
    
    # Summary output
    print(f"\n{'=' * 80}")
    print(f"AUDIT DAILY COMPLETE")
    print(f"{'=' * 80}")
    print(f"  Total Picks: {len(unique_picks)}")
    print(f"  Total P&L: {total_pnl:+.2f}%")
    print(f"  Open: {open_count} | Closed: {closed_count}")
    print(f"  Significant Movers: {len(significant_movers)}")
    print(f"  Asset Classes: {len(by_asset_class)}")
    print(f"")
    print(f"  HTML Report: {html_path}")
    print(f"  Markdown:    {md_path}")
    print(f"{'=' * 80}")


if __name__ == '__main__':
    main()
