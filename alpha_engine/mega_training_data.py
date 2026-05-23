#!/usr/bin/env python3
"""
Mega Training Data Extractor
============================
Extracts ALL historical trade data from both SQL databases (memecoin + stocks)
and normalizes into a unified training dataset for ML models.

Sources:
  - ejaguiar1_memecoin: ai_predictions, algo_predictions, bt100_picks, bt100_results,
                        ae_signals, psi_results, pp_picks, algo_battle_preds
  - ejaguiar1_stocks:   bt_backtest_trades (4,123 INSERT blocks!), at_consensus_picks,
                        at_raw_picks, alpha_picks

Output: alpha_engine/data/mega_training_data.json
"""

import re
import json
import os
import sys
import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Windows UTF-8 fix
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

MEMECOIN_SQL = Path(r"C:\Users\zerou\Downloads\ejaguiar1_memecoin_mar312026.sql")
STOCKS_SQL   = Path(r"C:\Users\zerou\Downloads\ejaguiar1_stocks.sql")
OUTPUT_FILE  = DATA_DIR / "mega_training_data.json"

# ── Symbol Normalization ───────────────────────────────────────────────────────
SYMBOL_MAP = {
    # Kraken-style → standard
    'XXBTZUSD': 'BTCUSDT', 'XETHZUSD': 'ETHUSDT', 'XXRPZUSD': 'XRPUSDT',
    'XDGUSD': 'DOGEUSDT', 'XXLMZUSD': 'XLMUSDT', 'XLTCZUSD': 'LTCUSDT',
    'XXMRZUSD': 'XMRUSDT', 'XZECZUSD': 'ZECUSDT',
    # Simple USD → USDT
    'BTCUSD': 'BTCUSDT', 'ETHUSD': 'ETHUSDT', 'SOLUSD': 'SOLUSDT',
    'ADAUSD': 'ADAUSDT', 'DOTUSD': 'DOTUSDT', 'LINKUSD': 'LINKUSDT',
    'AVAXUSD': 'AVAXUSDT', 'SHIBUSD': 'SHIBUSDT', 'PEPEUSD': 'PEPEUSDT',
    'BONKUSD': 'BONKUSDT', 'WIFUSD': 'WIFUSDT', 'SUIUSD': 'SUIUSDT',
    'SNXUSD': 'SNXUSDT', 'BCHUSD': 'BCHUSDT', 'DASHUSD': 'DASHUSDT',
    'FARTCOINUSD': 'FARTCOINUSDT', 'MOODENGUSD': 'MOODENGUSDT',
    'PENGUUSD': 'PENGUUSDT', 'SPXUSD': 'SPX6900USDT',
    'PONKEUSD': 'PONKEUSDT', 'VIRTUALUSD': 'VIRTUALUSDT',
    'FLOKIUSD': 'FLOKIUSDT', 'COMPUSD': 'COMPUSDT', 'EULUSD': 'EULUSDT',
    'DEEPUSD': 'DEEPUSDT', 'CTCUSD': 'CTCUSDT', 'ARCUSD': 'ARCUSDT',
    'CCDUSD': 'CCDUSDT', 'AAVEUSD': 'AAVEUSDT', 'CRVUSD': 'CRVUSDT',
    'FETUSD': 'FETUSDT', 'ALTHEAUSD': 'ALTHEAUSDT', 'APTUSD': 'APTUSDT',
    'XRPUSD': 'XRPUSDT',
}

def normalize_symbol(raw: str) -> str:
    """Normalize any symbol format to XXXUSDT or stock ticker."""
    if not raw:
        return 'UNKNOWN'
    s = raw.strip().upper().replace('/', '').replace('-', '')
    # Direct map first
    if s in SYMBOL_MAP:
        return SYMBOL_MAP[s]
    # Already ends with USDT
    if s.endswith('USDT'):
        return s
    # Ends with USD but not USDT → add T
    if s.endswith('USD') and not s.endswith('USDT'):
        return s + 'T'
    # Stock tickers (no USD suffix) — leave as-is
    return s


def classify_asset(symbol: str, asset_class_hint: str = None) -> str:
    """Classify asset as crypto, equity, forex, etc."""
    if asset_class_hint:
        h = asset_class_hint.upper()
        if h in ('CRYPTO', 'MEMECOIN'):
            return 'crypto'
        if h in ('EQUITY', 'ETF', 'PENNY_STOCK'):
            return 'equity'
        if h == 'FOREX':
            return 'forex'
    s = symbol.upper()
    if s.endswith('USDT') or s.endswith('USD'):
        return 'crypto'
    # Common stock/ETF tickers
    stock_tickers = {'SPY', 'QQQ', 'DIA', 'IWM', 'AAPL', 'GOOGL', 'MSFT', 'AMZN',
                     'META', 'NVDA', 'TSLA', 'CAT', 'JNJ', 'XOM', 'WMT', 'SLB',
                     'UPS', 'HON', 'WFC', 'JPM', 'BAC', 'GS'}
    if s in stock_tickers or (len(s) <= 5 and not s.endswith('USDT')):
        return 'equity'
    return 'crypto'


# ── SQL Value Parser ───────────────────────────────────────────────────────────
def parse_sql_values(sql_text: str):
    """
    Parse VALUES from SQL INSERT statements.
    Handles multi-row inserts: VALUES (row1), (row2), ...;
    Returns list of tuples of string values.
    """
    rows = []
    # Use a state-machine parser to handle nested parens, quotes, escaped chars
    i = 0
    n = len(sql_text)
    while i < n:
        # Find start of a row: opening paren
        if sql_text[i] == '(':
            i += 1
            values = []
            current = []
            in_quote = False
            quote_char = None
            depth = 0
            while i < n:
                ch = sql_text[i]
                if in_quote:
                    if ch == '\\' and i + 1 < n:
                        current.append(ch)
                        current.append(sql_text[i + 1])
                        i += 2
                        continue
                    elif ch == quote_char:
                        # Check for escaped quote ''
                        if i + 1 < n and sql_text[i + 1] == quote_char:
                            current.append(ch)
                            current.append(ch)
                            i += 2
                            continue
                        in_quote = False
                        current.append(ch)
                    else:
                        current.append(ch)
                else:
                    if ch in ("'", '"'):
                        in_quote = True
                        quote_char = ch
                        current.append(ch)
                    elif ch == '(' :
                        depth += 1
                        current.append(ch)
                    elif ch == ')':
                        if depth > 0:
                            depth -= 1
                            current.append(ch)
                        else:
                            # End of row
                            val = ''.join(current).strip()
                            values.append(val)
                            rows.append(tuple(values))
                            i += 1
                            break
                    elif ch == ',' and depth == 0:
                        val = ''.join(current).strip()
                        values.append(val)
                        current = []
                        i += 1
                        continue
                    else:
                        current.append(ch)
                i += 1
        else:
            i += 1
    return rows


def clean_val(v: str):
    """Clean a parsed SQL value — strip quotes, handle NULL."""
    if v == 'NULL' or v == 'null':
        return None
    if (v.startswith("'") and v.endswith("'")) or (v.startswith('"') and v.endswith('"')):
        inner = v[1:-1]
        # Unescape
        inner = inner.replace("\\'", "'").replace('\\"', '"').replace('\\\\', '\\')
        return inner
    try:
        if '.' in v:
            return float(v)
        return int(v)
    except (ValueError, TypeError):
        return v


def safe_float(v) -> float:
    """Convert to float safely."""
    if v is None:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def safe_date(v) -> str:
    """Extract date string."""
    if v is None:
        return None
    s = str(v)[:10]
    if len(s) >= 10 and s[4] == '-':
        return s
    return None


def compute_pnl(entry: float, exit_p: float, direction: str, pnl_raw: float = None) -> float:
    """Compute PnL% from entry/exit prices if pnl_raw is None."""
    if pnl_raw is not None:
        return pnl_raw
    if entry and exit_p and entry > 0:
        if direction == 'SHORT':
            return round((entry - exit_p) / entry * 100, 4)
        else:
            return round((exit_p - entry) / entry * 100, 4)
    return None


def win_from_pnl(pnl):
    """Return True/False/None based on pnl."""
    if pnl is None:
        return None
    return pnl > 0


# ── Extractors for each table ──────────────────────────────────────────────────

def extract_from_small_file(filepath: Path, table_name: str, column_names: list):
    """Extract INSERT data from a file that fits in memory."""
    text = filepath.read_text(encoding='utf-8', errors='replace')

    # Find all INSERT blocks for this table
    pattern = re.compile(
        r"INSERT INTO `" + re.escape(table_name) + r"` \([^)]+\) VALUES\s*\n?",
        re.IGNORECASE
    )

    results = []
    for m in pattern.finditer(text):
        start = m.end()
        # Find the end of this INSERT statement (;)
        end = text.find(';\n', start)
        if end == -1:
            end = len(text)
        block = text[start:end]
        rows = parse_sql_values(block)
        for row in rows:
            cleaned = [clean_val(v) for v in row]
            if len(cleaned) >= len(column_names):
                record = dict(zip(column_names, cleaned[:len(column_names)]))
                results.append(record)
            elif len(cleaned) > 0:
                # Pad with None
                padded = cleaned + [None] * (len(column_names) - len(cleaned))
                record = dict(zip(column_names, padded))
                results.append(record)
    return results


def extract_from_large_file_streaming(filepath: Path, table_name: str, column_names: list):
    """
    Stream-parse a large SQL file line by line for a specific table's INSERT statements.
    Accumulates multi-line INSERT blocks and parses them in chunks.
    """
    results = []
    header_pattern = re.compile(
        r"INSERT INTO `" + re.escape(table_name) + r"` \([^)]+\) VALUES\s*$",
        re.IGNORECASE
    )

    in_insert = False
    buffer = []

    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line_stripped = line.rstrip('\n').rstrip('\r')

            if header_pattern.search(line_stripped):
                # Start of a new INSERT block
                if buffer:
                    # Parse previous buffer
                    block = '\n'.join(buffer)
                    rows = parse_sql_values(block)
                    for row in rows:
                        cleaned = [clean_val(v) for v in row]
                        if len(cleaned) >= len(column_names):
                            record = dict(zip(column_names, cleaned[:len(column_names)]))
                            results.append(record)
                        elif len(cleaned) > 0:
                            padded = cleaned + [None] * (len(column_names) - len(cleaned))
                            record = dict(zip(column_names, padded))
                            results.append(record)
                    buffer = []
                in_insert = True
                continue

            if in_insert:
                buffer.append(line_stripped)
                if line_stripped.endswith(';'):
                    # End of INSERT block
                    block = '\n'.join(buffer)
                    rows = parse_sql_values(block)
                    for row in rows:
                        cleaned = [clean_val(v) for v in row]
                        if len(cleaned) >= len(column_names):
                            record = dict(zip(column_names, cleaned[:len(column_names)]))
                            results.append(record)
                        elif len(cleaned) > 0:
                            padded = cleaned + [None] * (len(column_names) - len(cleaned))
                            record = dict(zip(column_names, padded))
                            results.append(record)
                    buffer = []
                    in_insert = False

    # Final buffer
    if buffer:
        block = '\n'.join(buffer)
        rows = parse_sql_values(block)
        for row in rows:
            cleaned = [clean_val(v) for v in row]
            if len(cleaned) >= len(column_names):
                record = dict(zip(column_names, cleaned[:len(column_names)]))
                results.append(record)

    return results


# ── Normalizers for each source ────────────────────────────────────────────────

def normalize_ai_predictions(records: list) -> list:
    """From memecoin ai_predictions table."""
    trades = []
    for r in records:
        status = str(r.get('status', '')).upper()
        if status not in ('RESOLVED',):
            continue
        pnl = safe_float(r.get('pnl_pct'))
        entry = safe_float(r.get('entry_price'))
        exit_p = safe_float(r.get('exit_price')) or safe_float(r.get('current_price'))
        trades.append({
            'symbol': normalize_symbol(r.get('symbol', '') or r.get('kraken_pair', '')),
            'strategy': 'ai_prediction',
            'direction': str(r.get('direction', 'LONG')).upper(),
            'entry_price': entry,
            'exit_price': exit_p,
            'pnl_pct': pnl,
            'is_win': win_from_pnl(pnl),
            'entry_date': safe_date(r.get('created_at')),
            'exit_date': safe_date(r.get('resolved_at')),
            'source': 'ai_predictions',
            'source_db': 'memecoin',
            'source_weight': 0.8,  # Live AI predictions
            'asset_class': 'crypto',
            'confidence': str(r.get('confidence', '')),
            'exit_reason': r.get('exit_reason'),
        })
    return trades


def normalize_algo_predictions(records: list) -> list:
    """From memecoin algo_predictions table."""
    trades = []
    for r in records:
        status = str(r.get('status', '')).upper()
        pnl = safe_float(r.get('pnl_pct'))
        entry = safe_float(r.get('entry_price'))
        exit_p = safe_float(r.get('exit_price')) or safe_float(r.get('current_price'))
        direction = str(r.get('direction', 'LONG')).upper()
        algo = r.get('algo_name', 'unknown')
        trades.append({
            'symbol': normalize_symbol(r.get('symbol', '') or r.get('kraken_pair', '')),
            'strategy': f"algo_{algo}",
            'direction': direction,
            'entry_price': entry,
            'exit_price': exit_p,
            'pnl_pct': pnl,
            'is_win': win_from_pnl(pnl),
            'entry_date': safe_date(r.get('created_at')),
            'exit_date': safe_date(r.get('resolved_at')),
            'source': 'algo_predictions',
            'source_db': 'memecoin',
            'source_weight': 0.7,  # Algo predictions (semi-live)
            'asset_class': 'crypto',
            'confidence': str(r.get('confidence', '')),
            'exit_reason': r.get('exit_reason'),
        })
    return trades


def normalize_algo_battle_preds(records: list) -> list:
    """From memecoin algo_battle_preds table."""
    trades = []
    for r in records:
        pnl = safe_float(r.get('pnl_pct'))
        entry = safe_float(r.get('entry_price'))
        exit_p = safe_float(r.get('exit_price')) or safe_float(r.get('current_price'))
        direction = str(r.get('direction', 'LONG')).upper()
        algo = r.get('algo_name', 'unknown')
        trades.append({
            'symbol': normalize_symbol(r.get('symbol', '') or r.get('kraken_pair', '')),
            'strategy': f"battle_{algo}",
            'direction': direction,
            'entry_price': entry,
            'exit_price': exit_p,
            'pnl_pct': pnl,
            'is_win': win_from_pnl(pnl),
            'entry_date': safe_date(r.get('created_at')),
            'exit_date': safe_date(r.get('resolved_at')),
            'source': 'algo_battle_preds',
            'source_db': 'memecoin',
            'source_weight': 0.7,
            'asset_class': 'crypto',
            'confidence': str(r.get('confidence', '')),
            'exit_reason': r.get('exit_reason'),
        })
    return trades


def normalize_bt100_picks(records: list) -> list:
    """From memecoin bt100_picks table."""
    trades = []
    for r in records:
        pnl = safe_float(r.get('pnl_pct'))
        entry = safe_float(r.get('entry_price'))
        exit_p = safe_float(r.get('exit_price')) or safe_float(r.get('current_price'))
        direction = str(r.get('direction', 'LONG')).upper()
        trades.append({
            'symbol': normalize_symbol(r.get('pair', '')),
            'strategy': 'bt100_consensus',
            'direction': direction,
            'entry_price': entry,
            'exit_price': exit_p,
            'pnl_pct': pnl,
            'is_win': win_from_pnl(pnl),
            'entry_date': safe_date(r.get('created_at')),
            'exit_date': safe_date(r.get('resolved_at')),
            'source': 'bt100_picks',
            'source_db': 'memecoin',
            'source_weight': 0.8,  # Consensus of 100 backtested strategies
            'asset_class': 'crypto',
            'confidence': str(r.get('certainty_grade', '')),
            'exit_reason': r.get('exit_reason'),
            'strategies_agreeing': r.get('strategies_agreeing'),
            'avg_backtest_winrate': safe_float(r.get('avg_backtest_winrate')),
        })
    return trades


def normalize_ae_signals(records: list) -> list:
    """From memecoin ae_signals table."""
    trades = []
    for r in records:
        pnl = safe_float(r.get('pnl_pct'))
        entry = safe_float(r.get('entry_price'))
        current = safe_float(r.get('current_price'))
        direction = str(r.get('direction', 'LONG')).upper()
        strategy_id = r.get('strategy_id', 'unknown')
        trades.append({
            'symbol': normalize_symbol(r.get('pair', '')),
            'strategy': f"ae_{strategy_id}",
            'direction': direction,
            'entry_price': entry,
            'exit_price': current,
            'pnl_pct': pnl,
            'is_win': win_from_pnl(pnl),
            'entry_date': safe_date(r.get('created_at')),
            'exit_date': safe_date(r.get('resolved_at')),
            'source': 'ae_signals',
            'source_db': 'memecoin',
            'source_weight': 0.9,  # Alpha Engine live signals
            'asset_class': 'crypto',
            'confidence': safe_float(r.get('confidence')),
            'exit_reason': r.get('exit_reason'),
        })
    return trades


def normalize_psi_results(records: list) -> list:
    """
    From memecoin psi_results table.
    Each row is a strategy summary with trade_log JSON containing individual trades.
    """
    trades = []
    for r in records:
        strategy = r.get('sname', 'unknown')
        pair = r.get('pair', '')
        trade_log_str = r.get('trade_log', '[]')

        if trade_log_str and trade_log_str != '[]':
            try:
                trade_log = json.loads(trade_log_str) if isinstance(trade_log_str, str) else trade_log_str
            except (json.JSONDecodeError, TypeError):
                trade_log = []

            for t in trade_log:
                entry_p = safe_float(t.get('entry'))
                exit_p = safe_float(t.get('exit'))
                pnl = safe_float(t.get('pnl'))
                trades.append({
                    'symbol': normalize_symbol(pair),
                    'strategy': f"psi_{strategy}",
                    'direction': 'LONG',  # PSI results are directional from backtest
                    'entry_price': entry_p,
                    'exit_price': exit_p,
                    'pnl_pct': pnl,
                    'is_win': win_from_pnl(pnl),
                    'entry_date': safe_date(r.get('computed_at')),
                    'exit_date': None,
                    'source': 'psi_results',
                    'source_db': 'memecoin',
                    'source_weight': 0.6,  # Backtest results
                    'asset_class': 'crypto',
                    'exit_reason': t.get('reason'),
                })
    return trades


def normalize_pp_picks(records: list) -> list:
    """From memecoin pp_picks table."""
    trades = []
    for r in records:
        pnl = safe_float(r.get('pnl_pct'))
        entry = safe_float(r.get('entry_price'))
        current = safe_float(r.get('current_price'))
        direction = str(r.get('direction', 'LONG')).upper()
        trades.append({
            'symbol': normalize_symbol(r.get('pair', '')),
            'strategy': 'paper_portfolio',
            'direction': direction,
            'entry_price': entry,
            'exit_price': current,
            'pnl_pct': pnl,
            'is_win': win_from_pnl(pnl),
            'entry_date': safe_date(r.get('created_at')),
            'exit_date': safe_date(r.get('resolved_at')),
            'source': 'pp_picks',
            'source_db': 'memecoin',
            'source_weight': 0.85,  # Paper portfolio (live tracking, no real money)
            'asset_class': 'crypto',
            'confidence': safe_float(r.get('confidence')),
            'exit_reason': r.get('exit_reason'),
            'tier': r.get('tier'),
        })
    return trades


def normalize_bt_backtest_trades(records: list) -> list:
    """From stocks bt_backtest_trades table — THE BIG ONE."""
    trades = []
    for r in records:
        entry = safe_float(r.get('entry_price'))
        exit_p = safe_float(r.get('exit_price'))
        direction = str(r.get('direction', 'LONG')).upper()
        pnl = compute_pnl(entry, exit_p, direction, safe_float(r.get('pnl_pct')))
        strategy = r.get('strategy', 'unknown')
        asset_class = str(r.get('asset_class', 'UNKNOWN')).upper()
        symbol = normalize_symbol(r.get('symbol', ''))

        trades.append({
            'symbol': symbol,
            'strategy': strategy,
            'direction': direction,
            'entry_price': entry,
            'exit_price': exit_p,
            'pnl_pct': pnl,
            'is_win': win_from_pnl(pnl),
            'entry_date': safe_date(r.get('entry_time')),
            'exit_date': safe_date(r.get('exit_time')),
            'source': 'bt_backtest_trades',
            'source_db': 'stocks',
            'source_weight': 0.7,  # Backtest trades
            'asset_class': classify_asset(symbol, asset_class),
            'status': r.get('status'),
            'confidence': safe_float(r.get('confidence')),
        })
    return trades


def normalize_at_consensus_picks(records: list) -> list:
    """From stocks at_consensus_picks table."""
    trades = []
    for r in records:
        entry = safe_float(r.get('entry_price'))
        exit_p = safe_float(r.get('exit_price'))
        direction = str(r.get('direction', 'LONG')).upper()
        pnl = compute_pnl(entry, exit_p, direction, safe_float(r.get('pnl_pct')))
        asset_class = str(r.get('asset_class', '')).upper()
        symbol = normalize_symbol(r.get('symbol', ''))

        # Extract strategies from source_strategies JSON
        strats = r.get('source_strategies', '{}')
        try:
            strat_dict = json.loads(strats) if isinstance(strats, str) else strats or {}
            strategy_names = list(strat_dict.values()) if isinstance(strat_dict, dict) else []
            strategy = ', '.join([s for s in strategy_names if s]) if strategy_names else 'consensus'
        except (json.JSONDecodeError, TypeError):
            strategy = 'consensus'

        trades.append({
            'symbol': symbol,
            'strategy': f"consensus_{strategy[:80]}",
            'direction': direction,
            'entry_price': entry,
            'exit_price': exit_p,
            'pnl_pct': pnl,
            'is_win': win_from_pnl(pnl),
            'entry_date': safe_date(r.get('generated_at')),
            'exit_date': safe_date(r.get('closed_at')),
            'source': 'at_consensus_picks',
            'source_db': 'stocks',
            'source_weight': 1.0,  # Live consensus picks
            'asset_class': classify_asset(symbol, asset_class),
            'confidence': safe_float(r.get('confidence')),
            'exit_reason': r.get('exit_reason'),
            'consensus_tier': r.get('consensus_tier'),
            'agreement_count': r.get('agreement_count'),
        })
    return trades


def normalize_at_raw_picks(records: list) -> list:
    """From stocks at_raw_picks table."""
    trades = []
    for r in records:
        entry = safe_float(r.get('entry_price'))
        exit_p = safe_float(r.get('exit_price'))
        direction = str(r.get('direction', 'LONG')).upper()
        pnl = compute_pnl(entry, exit_p, direction, safe_float(r.get('pnl_pct')))
        asset_class = str(r.get('asset_class', '')).upper()
        symbol = normalize_symbol(r.get('symbol', ''))
        strategy = r.get('strategy', 'unknown')

        trades.append({
            'symbol': symbol,
            'strategy': f"raw_{strategy}",
            'direction': direction,
            'entry_price': entry,
            'exit_price': exit_p,
            'pnl_pct': pnl,
            'is_win': win_from_pnl(pnl),
            'entry_date': safe_date(r.get('recorded_at') or r.get('signal_timestamp')),
            'exit_date': safe_date(r.get('closed_at')),
            'source': 'at_raw_picks',
            'source_db': 'stocks',
            'source_weight': 0.8,  # Raw live picks
            'asset_class': classify_asset(symbol, asset_class),
            'confidence': safe_float(r.get('confidence')),
            'exit_reason': r.get('exit_reason'),
            'source_system': r.get('source_system'),
        })
    return trades


def normalize_alpha_picks(records: list) -> list:
    """From stocks alpha_picks table."""
    trades = []
    for r in records:
        entry = safe_float(r.get('entry_price'))
        ticker = r.get('ticker', 'UNKNOWN')
        strategy = r.get('strategy', 'unknown')
        sl_pct = safe_float(r.get('stop_loss_pct'))
        tp_pct = safe_float(r.get('take_profit_pct'))

        trades.append({
            'symbol': ticker,
            'strategy': f"alpha_{strategy}",
            'direction': 'LONG',
            'entry_price': entry,
            'exit_price': None,  # No exit tracking in this table
            'pnl_pct': None,
            'is_win': None,
            'entry_date': safe_date(r.get('pick_date') or r.get('created_at')),
            'exit_date': None,
            'source': 'alpha_picks',
            'source_db': 'stocks',
            'source_weight': 0.5,  # Picks without outcomes
            'asset_class': 'equity',
            'conviction': r.get('conviction'),
            'score': safe_float(r.get('score')),
            'tp_pct': tp_pct,
            'sl_pct': sl_pct,
        })
    return trades


# ── Main Extraction ────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("MEGA TRAINING DATA EXTRACTOR")
    print("=" * 70)

    all_trades = []
    source_counts = {}
    skipped = defaultdict(int)

    # ── MEMECOIN DB (fits in memory — 48K lines) ──────────────────────────
    print(f"\n[1/2] Reading memecoin DB: {MEMECOIN_SQL}")
    if not MEMECOIN_SQL.exists():
        print(f"  ERROR: File not found: {MEMECOIN_SQL}")
    else:
        memecoin_text = MEMECOIN_SQL.read_text(encoding='utf-8', errors='replace')

        # ai_predictions
        print("  Extracting ai_predictions...")
        cols = ['id', 'batch_id', 'symbol', 'kraken_pair', 'direction', 'entry_price',
                'current_price', 'tp_price', 'sl_price', 'tp_pct', 'sl_pct', 'confidence',
                'thesis', 'timeframe', 'status', 'pnl_pct', 'peak_pnl_pct', 'trough_pnl_pct',
                'exit_price', 'exit_reason', 'checks_count', 'last_check', 'created_at', 'resolved_at']
        recs = extract_from_small_file(MEMECOIN_SQL, 'ai_predictions', cols)
        trades = normalize_ai_predictions(recs)
        source_counts['ai_predictions'] = len(trades)
        all_trades.extend(trades)
        print(f"    -> {len(recs)} raw records -> {len(trades)} trades")

        # ai_personal_predictions (same structure)
        print("  Extracting ai_personal_predictions...")
        cols_personal = ['id', 'batch_id', 'symbol', 'kraken_pair', 'direction', 'entry_price',
                'current_price', 'tp_price', 'sl_price', 'tp_pct', 'sl_pct', 'confidence',
                'thesis', 'timeframe', 'status', 'pnl_pct', 'peak_pnl_pct', 'trough_pnl_pct',
                'exit_price', 'exit_reason', 'checks_count', 'last_check', 'created_at', 'resolved_at',
                'ai_model', 'prediction_type']
        recs = extract_from_small_file(MEMECOIN_SQL, 'ai_personal_predictions', cols_personal)
        trades = normalize_ai_predictions(recs)
        source_counts['ai_personal_predictions'] = len(trades)
        all_trades.extend(trades)
        print(f"    -> {len(recs)} raw records -> {len(trades)} trades")

        # algo_predictions
        print("  Extracting algo_predictions...")
        cols = ['id', 'round_id', 'algo_name', 'algo_type', 'symbol', 'kraken_pair',
                'direction', 'entry_price', 'current_price', 'tp_price', 'sl_price',
                'tp_pct', 'sl_pct', 'confidence', 'reason', 'consensus_count',
                'status', 'pnl_pct', 'peak_pnl_pct', 'trough_pnl_pct',
                'exit_price', 'exit_reason', 'checks_count', 'last_check',
                'created_at', 'resolved_at']
        recs = extract_from_small_file(MEMECOIN_SQL, 'algo_predictions', cols)
        trades = normalize_algo_predictions(recs)
        source_counts['algo_predictions'] = len(trades)
        all_trades.extend(trades)
        print(f"    -> {len(recs)} raw records -> {len(trades)} trades")

        # algo_battle_preds
        print("  Extracting algo_battle_preds...")
        cols = ['id', 'batch_id', 'algo_id', 'algo_name', 'algo_source', 'symbol', 'kraken_pair',
                'direction', 'entry_price', 'current_price', 'tp_price', 'sl_price',
                'tp_pct', 'sl_pct', 'signal_strength', 'confidence', 'thesis', 'timeframe',
                'status', 'pnl_pct', 'peak_pnl_pct', 'trough_pnl_pct',
                'exit_price', 'exit_reason', 'consensus_count', 'checks_count', 'last_check',
                'created_at', 'resolved_at']
        recs = extract_from_small_file(MEMECOIN_SQL, 'algo_battle_preds', cols)
        trades = normalize_algo_battle_preds(recs)
        source_counts['algo_battle_preds'] = len(trades)
        all_trades.extend(trades)
        print(f"    -> {len(recs)} raw records -> {len(trades)} trades")

        # bt100_picks
        print("  Extracting bt100_picks...")
        cols = ['id', 'run_id', 'pair', 'direction', 'entry_price', 'tp_price', 'sl_price',
                'tp_pct', 'sl_pct', 'certainty_score', 'certainty_grade', 'strategies_agreeing',
                'strategy_names', 'avg_backtest_winrate', 'avg_backtest_pf', 'thesis',
                'status', 'current_price', 'pnl_pct', 'exit_price', 'exit_reason',
                'created_at', 'resolved_at']
        recs = extract_from_small_file(MEMECOIN_SQL, 'bt100_picks', cols)
        trades = normalize_bt100_picks(recs)
        source_counts['bt100_picks'] = len(trades)
        all_trades.extend(trades)
        print(f"    -> {len(recs)} raw records -> {len(trades)} trades")

        # ae_signals
        print("  Extracting ae_signals...")
        cols = ['id', 'pair', 'strategy_id', 'strategy_name', 'direction',
                'entry_price', 'tp_price', 'sl_price', 'tp_pct', 'sl_pct',
                'confidence', 'regime', 'rationale', 'status', 'current_price',
                'pnl_pct', 'exit_reason', 'created_at', 'resolved_at']
        recs = extract_from_small_file(MEMECOIN_SQL, 'ae_signals', cols)
        trades = normalize_ae_signals(recs)
        source_counts['ae_signals'] = len(trades)
        all_trades.extend(trades)
        print(f"    -> {len(recs)} raw records -> {len(trades)} trades")

        # psi_results (has trade_log JSON with individual trades)
        print("  Extracting psi_results (with trade logs)...")
        cols = ['id', 'sid', 'sname', 'scat', 'pair', 'tf', 'trades', 'wins', 'losses',
                'win_rate', 'total_ret', 'profit_factor', 'sharpe', 'max_dd',
                'avg_win', 'avg_loss', 'best_trade', 'worst_trade', 'avg_bars',
                'trade_log', 'computed_at']
        recs = extract_from_small_file(MEMECOIN_SQL, 'psi_results', cols)
        trades = normalize_psi_results(recs)
        source_counts['psi_results'] = len(trades)
        all_trades.extend(trades)
        print(f"    -> {len(recs)} raw records -> {len(trades)} individual trades from logs")

        # pp_picks
        print("  Extracting pp_picks...")
        cols = ['id', 'pick_id', 'pair', 'direction', 'entry_price', 'entry_price_slippage',
                'tp_price', 'sl_price', 'confidence', 'consensus_count', 'engines_agreeing',
                'engine_details', 'market_state', 'tier', 'slippage_bps', 'status',
                'current_price', 'high_since', 'low_since', 'pnl_pct', 'pnl_after_slip',
                'exit_reason', 'created_at', 'resolved_at', 'hours_held']
        recs = extract_from_small_file(MEMECOIN_SQL, 'pp_picks', cols)
        trades = normalize_pp_picks(recs)
        source_counts['pp_picks'] = len(trades)
        all_trades.extend(trades)
        print(f"    -> {len(recs)} raw records -> {len(trades)} trades")

        del memecoin_text  # Free memory

    # ── STOCKS DB (1M lines — stream) ─────────────────────────────────────
    print(f"\n[2/2] Streaming stocks DB: {STOCKS_SQL}")
    if not STOCKS_SQL.exists():
        print(f"  ERROR: File not found: {STOCKS_SQL}")
    else:
        # bt_backtest_trades — 4,123 INSERT blocks, THE BIG ONE
        print("  Extracting bt_backtest_trades (4,123 INSERT blocks)...")
        cols = ['id', 'backtest_run_id', 'source_db', 'source_table', 'symbol',
                'asset_class', 'direction', 'strategy', 'entry_price', 'exit_price',
                'take_profit', 'stop_loss', 'entry_time', 'exit_time', 'pnl_pct',
                'status', 'confidence', 'raw_data', 'imported_at']
        recs = extract_from_large_file_streaming(STOCKS_SQL, 'bt_backtest_trades', cols)
        trades = normalize_bt_backtest_trades(recs)
        source_counts['bt_backtest_trades'] = len(trades)
        all_trades.extend(trades)
        print(f"    -> {len(recs)} raw records -> {len(trades)} trades")

        # at_consensus_picks
        print("  Extracting at_consensus_picks...")
        cols = ['id', 'aggregation_run_id', 'symbol', 'asset_class', 'direction',
                'entry_price', 'take_profit', 'stop_loss', 'risk_reward', 'confidence',
                'agreement_count', 'source_systems', 'source_strategies', 'system_confidences',
                'consensus_tier', 'classification', 'regime_data', 'discord_channel',
                'discord_message_id', 'status', 'exit_price', 'exit_reason', 'pnl_pct',
                'slippage_estimate', 'generated_at', 'closed_at']
        recs = extract_from_large_file_streaming(STOCKS_SQL, 'at_consensus_picks', cols)
        trades = normalize_at_consensus_picks(recs)
        source_counts['at_consensus_picks'] = len(trades)
        all_trades.extend(trades)
        print(f"    -> {len(recs)} raw records -> {len(trades)} trades")

        # at_raw_picks
        print("  Extracting at_raw_picks...")
        cols = ['id', 'aggregation_run_id', 'source_system', 'symbol', 'asset_class',
                'direction', 'entry_price', 'take_profit', 'stop_loss', 'risk_reward',
                'confidence', 'strategy', 'raw_payload', 'signal_timestamp', 'recorded_at',
                'dedup_hash', 'was_stale', 'was_banned', 'was_demoted', 'was_wr_suppressed',
                'created_by', 'status', 'exit_price', 'exit_reason', 'pnl_pct', 'closed_at']
        recs = extract_from_large_file_streaming(STOCKS_SQL, 'at_raw_picks', cols)
        trades = normalize_at_raw_picks(recs)
        source_counts['at_raw_picks'] = len(trades)
        all_trades.extend(trades)
        print(f"    -> {len(recs)} raw records -> {len(trades)} trades")

        # alpha_picks
        print("  Extracting alpha_picks...")
        cols = ['id', 'ticker', 'strategy', 'pick_date', 'entry_price', 'score',
                'conviction', 'expected_horizon', 'risk_level', 'position_size_pct',
                'stop_loss_pct', 'take_profit_pct', 'rationale', 'top_factors',
                'avoid_reasons', 'pick_hash', 'created_at']
        recs = extract_from_large_file_streaming(STOCKS_SQL, 'alpha_picks', cols)
        trades = normalize_alpha_picks(recs)
        source_counts['alpha_picks'] = len(trades)
        all_trades.extend(trades)
        print(f"    -> {len(recs)} raw records -> {len(trades)} trades")

    # ── Build Summary Stats ───────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("BUILDING SUMMARY STATS")
    print("=" * 70)

    total = len(all_trades)

    # Trades with PnL data
    trades_with_pnl = [t for t in all_trades if t.get('pnl_pct') is not None]
    trades_with_outcome = [t for t in all_trades if t.get('is_win') is not None]

    # Win rate
    wins = sum(1 for t in trades_with_outcome if t['is_win'])
    losses = sum(1 for t in trades_with_outcome if not t['is_win'])
    overall_wr = (wins / len(trades_with_outcome) * 100) if trades_with_outcome else 0

    # By source
    by_source = defaultdict(lambda: {'total': 0, 'wins': 0, 'losses': 0, 'pnl_sum': 0.0, 'pnl_count': 0})
    for t in all_trades:
        src = t['source']
        by_source[src]['total'] += 1
        if t.get('is_win') is True:
            by_source[src]['wins'] += 1
        elif t.get('is_win') is False:
            by_source[src]['losses'] += 1
        if t.get('pnl_pct') is not None:
            by_source[src]['pnl_sum'] += t['pnl_pct']
            by_source[src]['pnl_count'] += 1

    # By asset class
    by_asset = defaultdict(lambda: {'total': 0, 'wins': 0, 'losses': 0})
    for t in all_trades:
        ac = t.get('asset_class', 'unknown')
        by_asset[ac]['total'] += 1
        if t.get('is_win') is True:
            by_asset[ac]['wins'] += 1
        elif t.get('is_win') is False:
            by_asset[ac]['losses'] += 1

    # By strategy — WR leaderboard
    by_strategy = defaultdict(lambda: {'total': 0, 'wins': 0, 'losses': 0, 'pnl_sum': 0.0, 'pnl_count': 0})
    for t in all_trades:
        strat = t.get('strategy') or 'unknown'
        # Truncate long strategy names
        if len(strat) > 60:
            strat = strat[:57] + '...'
        by_strategy[strat]['total'] += 1
        if t.get('is_win') is True:
            by_strategy[strat]['wins'] += 1
        elif t.get('is_win') is False:
            by_strategy[strat]['losses'] += 1
        if t.get('pnl_pct') is not None:
            by_strategy[strat]['pnl_sum'] += t['pnl_pct']
            by_strategy[strat]['pnl_count'] += 1

    # By symbol
    by_symbol = defaultdict(lambda: {'total': 0, 'wins': 0, 'losses': 0, 'pnl_sum': 0.0, 'pnl_count': 0})
    for t in all_trades:
        sym = t.get('symbol', 'UNKNOWN')
        by_symbol[sym]['total'] += 1
        if t.get('is_win') is True:
            by_symbol[sym]['wins'] += 1
        elif t.get('is_win') is False:
            by_symbol[sym]['losses'] += 1
        if t.get('pnl_pct') is not None:
            by_symbol[sym]['pnl_sum'] += t['pnl_pct']
            by_symbol[sym]['pnl_count'] += 1

    # Best strategies (min 10 resolved trades)
    strat_wr = {}
    for name, data in by_strategy.items():
        resolved = data['wins'] + data['losses']
        if resolved >= 10:
            wr = data['wins'] / resolved * 100 if resolved > 0 else 0
            avg_pnl = data['pnl_sum'] / data['pnl_count'] if data['pnl_count'] > 0 else 0
            strat_wr[name] = {'win_rate': round(wr, 2), 'trades': resolved, 'avg_pnl': round(avg_pnl, 4)}
    best_strategies = dict(sorted(strat_wr.items(), key=lambda x: x[1]['win_rate'], reverse=True)[:30])

    # Best symbols (min 5 resolved trades)
    sym_wr = {}
    for name, data in by_symbol.items():
        resolved = data['wins'] + data['losses']
        if resolved >= 5:
            wr = data['wins'] / resolved * 100 if resolved > 0 else 0
            avg_pnl = data['pnl_sum'] / data['pnl_count'] if data['pnl_count'] > 0 else 0
            sym_wr[name] = {'win_rate': round(wr, 2), 'trades': resolved, 'avg_pnl': round(avg_pnl, 4)}
    best_symbols = dict(sorted(sym_wr.items(), key=lambda x: x[1]['win_rate'], reverse=True)[:20])

    summary = {
        'total_trades': total,
        'trades_with_pnl': len(trades_with_pnl),
        'trades_with_outcome': len(trades_with_outcome),
        'overall_win_rate': round(overall_wr, 2),
        'wins': wins,
        'losses': losses,
        'avg_pnl': round(sum(t['pnl_pct'] for t in trades_with_pnl) / len(trades_with_pnl), 4) if trades_with_pnl else 0,
        'by_source': {k: dict(v) for k, v in sorted(by_source.items(), key=lambda x: x[1]['total'], reverse=True)},
        'by_asset_class': {k: dict(v) for k, v in by_asset.items()},
        'best_strategies_by_wr': best_strategies,
        'best_symbols_by_wr': best_symbols,
        'extraction_date': datetime.now().isoformat(),
    }

    # ── Save Output ───────────────────────────────────────────────────────
    output = {
        'summary': summary,
        'trades': all_trades,
    }

    print(f"\nSaving to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=1, default=str, ensure_ascii=False)

    file_size = OUTPUT_FILE.stat().st_size / (1024 * 1024)
    print(f"Saved: {OUTPUT_FILE} ({file_size:.1f} MB)")

    # ── Print Report ──────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("EXTRACTION REPORT")
    print("=" * 70)

    print(f"\nTotal trades extracted: {total:,}")
    print(f"Trades with PnL data:  {len(trades_with_pnl):,}")
    print(f"Trades with outcome:   {len(trades_with_outcome):,}")
    print(f"Overall Win Rate:      {overall_wr:.1f}%")
    print(f"Wins: {wins:,} | Losses: {losses:,}")
    if trades_with_pnl:
        avg_pnl = sum(t['pnl_pct'] for t in trades_with_pnl) / len(trades_with_pnl)
        print(f"Average PnL:           {avg_pnl:.4f}%")

    print(f"\n{'Source':<30} {'Total':>8} {'Wins':>8} {'Losses':>8} {'WR':>8}")
    print("-" * 70)
    for src, data in sorted(by_source.items(), key=lambda x: x[1]['total'], reverse=True):
        resolved = data['wins'] + data['losses']
        wr = (data['wins'] / resolved * 100) if resolved > 0 else 0
        print(f"{src:<30} {data['total']:>8,} {data['wins']:>8,} {data['losses']:>8,} {wr:>7.1f}%")

    print(f"\n{'Asset Class':<20} {'Total':>8} {'Wins':>8} {'Losses':>8} {'WR':>8}")
    print("-" * 50)
    for ac, data in by_asset.items():
        resolved = data['wins'] + data['losses']
        wr = (data['wins'] / resolved * 100) if resolved > 0 else 0
        print(f"{ac:<20} {data['total']:>8,} {data['wins']:>8,} {data['losses']:>8,} {wr:>7.1f}%")

    print(f"\nTop 15 Strategies by Win Rate (min 10 trades):")
    print(f"{'Strategy':<50} {'WR':>7} {'Trades':>7} {'Avg PnL':>9}")
    print("-" * 75)
    for name, data in list(best_strategies.items())[:15]:
        print(f"{name:<50} {data['win_rate']:>6.1f}% {data['trades']:>7,} {data['avg_pnl']:>8.2f}%")

    print(f"\nTop 10 Symbols by Win Rate (min 5 trades):")
    print(f"{'Symbol':<20} {'WR':>7} {'Trades':>7} {'Avg PnL':>9}")
    print("-" * 45)
    for name, data in list(best_symbols.items())[:10]:
        print(f"{name:<20} {data['win_rate']:>6.1f}% {data['trades']:>7,} {data['avg_pnl']:>8.2f}%")

    print(f"\nData quality:")
    no_symbol = sum(1 for t in all_trades if t['symbol'] == 'UNKNOWN')
    no_pnl = total - len(trades_with_pnl)
    print(f"  Trades missing symbol: {no_symbol:,}")
    print(f"  Trades missing PnL:    {no_pnl:,}")
    print(f"  Normalization rate:    {(total - no_symbol) / total * 100:.1f}%")

    print(f"\nOutput: {OUTPUT_FILE}")
    print("=" * 70)

    return output


if __name__ == '__main__':
    main()
