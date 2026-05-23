#!/usr/bin/env python3
"""
Strategy-Pair Affinity Matrix
=============================
Parses ae_results SQL dump and builds a lookup matrix showing which strategy
works best on which coin, based on OUT-OF-SAMPLE (test) performance.

Affinity score (0.0-1.0):
  0.40 * win_rate/100
  0.30 * min(profit_factor/3, 1.0)
  0.20 * min(sharpe/2, 1.0)
  0.10 * (1 - min(abs(max_dd)/20, 1.0))
"""

import sys, os, re, json
from pathlib import Path
from collections import defaultdict

# Windows UTF-8 fix
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SQL_FILE = os.environ.get(
    "AE_SQL_FILE",
    r"C:\Users\zerou\Downloads\ejaguiar1_memecoin_mar312026.sql"
)

DATA_DIR = Path(__file__).parent / "data"
OUTPUT_JSON = DATA_DIR / "strategy_pair_affinity.json"

# Strategy code -> Alpha Engine strategy names
STRATEGY_MAP = {
    "S1_VWTSMOM":  ["volume_weighted_momentum", "dynamic_gainer_momentum"],
    "S2_ADAPTIVE": ["adaptive_trend", "trend_following"],
    "S3_BBKC":     ["bb_keltner_squeeze", "keltner_compression"],
    "S4_RSI_REGIME": ["rsi_regime", "crypto_rsi_divergence"],
    "S5_OBV_DIV":  ["obv_divergence", "volume_spike"],
    "S6_HIERARCHY": ["multi_indicator", "hierarchy"],
    "S7_PUMP_PRE": ["pump_precursor", "pump_detector"],
    "S8_RULE_ENS": ["rule_ensemble", "best_of_breed"],
}

# Kraken-style pair -> standard USDT symbol
PAIR_MAP = {
    "XXBTZUSD":  "BTCUSDT",
    "XETHZUSD":  "ETHUSDT",
    "XXRPZUSD":  "XRPUSDT",
    "XXLMZUSD":  "XLMUSDT",
    "XXMRZUSD":  "XMRUSDT",
    "XLTCZUSD":  "LTCUSDT",
    "XETCZUSD":  "ETCUSDT",
    "XZECZUSD":  "ZECUSDT",
}


def normalize_pair(pair: str) -> str:
    """Convert Kraken-style pair to standard USDT symbol."""
    if pair in PAIR_MAP:
        return PAIR_MAP[pair]
    # Generic: XXXUSD -> XXXUSDT
    if pair.endswith("USD") and not pair.endswith("USDT"):
        base = pair[:-3]
        return f"{base}USDT"
    return pair


# ---------------------------------------------------------------------------
# SQL Parser
# ---------------------------------------------------------------------------
# Matches a single VALUES tuple from the INSERT statement
ROW_RE = re.compile(
    r"\(\s*(\d+)\s*,"              # id
    r"\s*'([^']+)'\s*,"            # strategy_id
    r"\s*'([^']+)'\s*,"            # strategy_name
    r"\s*'([^']+)'\s*,"            # pair
    r"\s*(\d+)\s*,"                # is_train
    r"\s*(\d+)\s*,"                # trades
    r"\s*(\d+)\s*,"                # wins
    r"\s*([-\d.]+)\s*,"            # win_rate
    r"\s*([-\d.]+)\s*,"            # profit_factor
    r"\s*([-\d.]+)\s*,"            # total_return
    r"\s*([-\d.]+)\s*,"            # sharpe
    r"\s*([-\d.]+)\s*,"            # max_dd
    r"\s*([-\d.]+)\s*,"            # avg_win
    r"\s*([-\d.]+)\s*,"            # avg_loss
    r"\s*'([^']+)'\s*\)"           # created_at
)


def parse_sql(filepath: str) -> list[dict]:
    """Parse ae_results INSERT statements from SQL dump."""
    rows = []
    in_ae = False
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            if "INSERT INTO `ae_results`" in line:
                in_ae = True
            if in_ae:
                for m in ROW_RE.finditer(line):
                    rows.append({
                        "id":             int(m.group(1)),
                        "strategy_id":    m.group(2),
                        "strategy_name":  m.group(3),
                        "pair":           m.group(4),
                        "is_train":       int(m.group(5)),
                        "trades":         int(m.group(6)),
                        "wins":           int(m.group(7)),
                        "win_rate":       float(m.group(8)),
                        "profit_factor":  float(m.group(9)),
                        "total_return":   float(m.group(10)),
                        "sharpe":         float(m.group(11)),
                        "max_dd":         float(m.group(12)),
                        "avg_win":        float(m.group(13)),
                        "avg_loss":       float(m.group(14)),
                        "created_at":     m.group(15),
                    })
                # End of INSERT block
                if line.rstrip().endswith(";"):
                    in_ae = False
    return rows


# ---------------------------------------------------------------------------
# Affinity calculation
# ---------------------------------------------------------------------------
def calc_affinity(row: dict) -> float:
    """Calculate affinity score 0.0-1.0 from test row metrics."""
    wr = row["win_rate"] / 100.0
    pf = min(row["profit_factor"] / 3.0, 1.0)
    sh = min(row["sharpe"] / 2.0, 1.0) if row["sharpe"] > 0 else 0.0
    dd = 1.0 - min(abs(row["max_dd"]) / 20.0, 1.0)
    return round(0.40 * wr + 0.30 * pf + 0.20 * sh + 0.10 * dd, 4)


def build_matrix(rows: list[dict]) -> dict:
    """Build the affinity matrix from test-only rows."""
    # Filter to test data only
    test_rows = [r for r in rows if r["is_train"] == 0]

    # Group by (strategy_id, symbol)
    matrix = {}          # {strategy_id: {symbol: affinity}}
    detail = {}          # {strategy_id: {symbol: row_data}}

    for r in test_rows:
        sid = r["strategy_id"]
        sym = normalize_pair(r["pair"])
        aff = calc_affinity(r)

        if sid not in matrix:
            matrix[sid] = {}
            detail[sid] = {}

        # If multiple test rows exist for same combo, keep best
        if sym not in matrix[sid] or aff > matrix[sid][sym]:
            matrix[sid][sym] = aff
            detail[sid][sym] = {
                "affinity": aff,
                "win_rate": r["win_rate"],
                "profit_factor": r["profit_factor"],
                "sharpe": r["sharpe"],
                "max_dd": r["max_dd"],
                "total_return": r["total_return"],
                "trades": r["trades"],
                "pair_raw": r["pair"],
            }

    return matrix, detail


# ---------------------------------------------------------------------------
# Expanded matrix: map strategy codes to Alpha Engine names
# ---------------------------------------------------------------------------
def expand_matrix(matrix: dict, detail: dict) -> tuple[dict, dict]:
    """Expand S1_VWTSMOM -> volume_weighted_momentum, dynamic_gainer_momentum etc."""
    expanded = {}
    expanded_detail = {}

    for sid, symbols in matrix.items():
        ae_names = STRATEGY_MAP.get(sid, [sid])
        for name in ae_names:
            expanded[name] = dict(symbols)
            expanded_detail[name] = dict(detail.get(sid, {}))

    return expanded, expanded_detail


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
_MATRIX = None
_DETAIL = None


def _ensure_loaded():
    global _MATRIX, _DETAIL
    if _MATRIX is not None:
        return
    # Try loading from cached JSON first
    if OUTPUT_JSON.exists():
        with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        _MATRIX = data.get("matrix", {})
        _DETAIL = data.get("detail", {})
    else:
        # Parse SQL and build fresh
        rows = parse_sql(SQL_FILE)
        raw_matrix, raw_detail = build_matrix(rows)
        _MATRIX, _DETAIL = expand_matrix(raw_matrix, raw_detail)
        save_matrix(_MATRIX, _DETAIL)


def get_affinity(strategy_name: str, symbol: str) -> float | None:
    """Returns 0.0-1.0 affinity score, or None if no data exists for this strategy.
    Higher = better historical performance. None means untested (no backtest data)."""
    _ensure_loaded()
    sym = symbol.upper()
    if not sym.endswith("USDT") and not sym.endswith("USD"):
        sym = sym + "USDT"
    strats = _MATRIX.get(strategy_name)
    if strats is None:
        return None  # Strategy not in matrix — no backtest data exists
    return strats.get(sym, 0.0)


def get_backtest_win_rate(strategy_name: str, symbol: str) -> float | None:
    """Returns the backtest win rate (0-100) for a strategy+symbol combo."""
    _ensure_loaded()
    sym = symbol.upper()
    if not sym.endswith("USDT") and not sym.endswith("USD"):
        sym = sym + "USDT"
    details = _DETAIL.get(strategy_name, {}).get(sym)
    if details:
        return details.get("win_rate")
    return None


def get_backtest_trades(strategy_name: str, symbol: str) -> int | None:
    """Returns the number of backtest trades for a strategy+symbol combo."""
    _ensure_loaded()
    sym = symbol.upper()
    if not sym.endswith("USDT") and not sym.endswith("USD"):
        sym = sym + "USDT"
    details = _DETAIL.get(strategy_name, {}).get(sym)
    if details:
        return details.get("trades")
    return None


def get_best_strategies_for_symbol(symbol: str) -> list[tuple[str, float]]:
    """Returns sorted list of (strategy, affinity_score) for a symbol."""
    _ensure_loaded()
    sym = symbol.upper()
    if not sym.endswith("USDT") and not sym.endswith("USD"):
        sym = sym + "USDT"
    results = []
    for strat, symbols in _MATRIX.items():
        if sym in symbols:
            results.append((strat, symbols[sym]))
    return sorted(results, key=lambda x: x[1], reverse=True)


def get_best_symbols_for_strategy(strategy_name: str) -> list[tuple[str, float]]:
    """Returns sorted list of (symbol, affinity_score) for a strategy."""
    _ensure_loaded()
    symbols = _MATRIX.get(strategy_name, {})
    return sorted(symbols.items(), key=lambda x: x[1], reverse=True)


def should_trade(strategy: str, symbol: str, min_affinity: float = 0.3) -> bool:
    """Returns True if this strategy+pair combo has proven edge."""
    return get_affinity(strategy, symbol) >= min_affinity


def save_matrix(matrix: dict, detail: dict):
    """Save matrix to JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "description": "Strategy-pair affinity matrix from ae_results backtest (test data only)",
        "scoring": "0.40*win_rate + 0.30*profit_factor + 0.20*sharpe + 0.10*(1-drawdown)",
        "strategy_map": {k: v for k, v in STRATEGY_MAP.items()},
        "matrix": matrix,
        "detail": detail,
    }
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"[OK] Saved affinity matrix to {OUTPUT_JSON}")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def print_report(matrix: dict, detail: dict):
    """Print comprehensive affinity report."""

    # Flatten all combos
    all_combos = []
    for strat, symbols in matrix.items():
        for sym, aff in symbols.items():
            d = detail.get(strat, {}).get(sym, {})
            all_combos.append((strat, sym, aff, d))

    all_combos.sort(key=lambda x: x[2], reverse=True)

    # Unique strategy names (use first from each STRATEGY_MAP group)
    seen_strats = set()
    unique_combos = []
    for strat, sym, aff, d in all_combos:
        # Deduplicate: volume_weighted_momentum and dynamic_gainer_momentum are same data
        base_key = f"{strat.split('_')[0]}_{sym}" if strat in sum(STRATEGY_MAP.values(), []) else f"{strat}_{sym}"
        unique_combos.append((strat, sym, aff, d))

    total_pairs = len(set(sym for _, sym, _, _ in all_combos))
    total_strats = len(matrix)

    print(f"\n{'='*80}")
    print(f"  STRATEGY-PAIR AFFINITY MATRIX REPORT")
    print(f"  {total_strats} strategies x {total_pairs} pairs = {len(all_combos)} combos")
    print(f"{'='*80}")

    # --- Top 10 ---
    print(f"\n{'='*80}")
    print(f"  TOP 10 BEST STRATEGY+PAIR COMBOS (highest affinity)")
    print(f"{'='*80}")
    print(f"  {'Strategy':<35} {'Symbol':<12} {'Aff':>5} {'WR%':>6} {'PF':>6} {'Sharpe':>7} {'Return%':>8} {'Trades':>6}")
    print(f"  {'-'*35} {'-'*12} {'-'*5} {'-'*6} {'-'*6} {'-'*7} {'-'*8} {'-'*6}")
    shown = set()
    count = 0
    for strat, sym, aff, d in all_combos:
        key = f"{sym}_{d.get('pair_raw','')}"
        if key in shown:
            continue
        shown.add(key)
        print(f"  {strat:<35} {sym:<12} {aff:>5.3f} {d.get('win_rate',0):>5.1f}% {d.get('profit_factor',0):>6.2f} {d.get('sharpe',0):>7.2f} {d.get('total_return',0):>7.2f}% {d.get('trades',0):>6d}")
        count += 1
        if count >= 10:
            break

    # --- Bottom 10 ---
    print(f"\n{'='*80}")
    print(f"  BOTTOM 10 WORST COMBOS (avoid these)")
    print(f"{'='*80}")
    print(f"  {'Strategy':<35} {'Symbol':<12} {'Aff':>5} {'WR%':>6} {'PF':>6} {'Sharpe':>7} {'Return%':>8}")
    print(f"  {'-'*35} {'-'*12} {'-'*5} {'-'*6} {'-'*6} {'-'*7} {'-'*8}")
    # Filter to combos that actually had trades
    traded = [c for c in all_combos if c[3].get("trades", 0) > 0]
    traded.sort(key=lambda x: x[2])
    shown = set()
    count = 0
    for strat, sym, aff, d in traded:
        key = f"{sym}_{d.get('pair_raw','')}"
        if key in shown:
            continue
        shown.add(key)
        print(f"  {strat:<35} {sym:<12} {aff:>5.3f} {d.get('win_rate',0):>5.1f}% {d.get('profit_factor',0):>6.2f} {d.get('sharpe',0):>7.2f} {d.get('total_return',0):>7.2f}%")
        count += 1
        if count >= 10:
            break

    # --- Per-Strategy Summary ---
    print(f"\n{'='*80}")
    print(f"  PER-STRATEGY SUMMARY (best coins per strategy)")
    print(f"{'='*80}")

    # Group by base strategy (S1-S8), show first name only
    for sid, ae_names in STRATEGY_MAP.items():
        primary = ae_names[0]
        if primary not in matrix:
            continue
        symbols = matrix[primary]
        sorted_syms = sorted(symbols.items(), key=lambda x: x[1], reverse=True)

        # Count tradeable
        tradeable = sum(1 for _, a in sorted_syms if a >= 0.3)
        avg_aff = sum(a for _, a in sorted_syms) / len(sorted_syms) if sorted_syms else 0

        print(f"\n  {sid} -> {', '.join(ae_names)}")
        print(f"  Avg affinity: {avg_aff:.3f} | Tradeable (>=0.3): {tradeable}/{len(sorted_syms)}")
        print(f"    Best:  ", end="")
        for sym, aff in sorted_syms[:5]:
            d = detail.get(primary, {}).get(sym, {})
            print(f"{sym}({aff:.2f}, WR={d.get('win_rate',0):.0f}%) ", end="")
        print()
        print(f"    Worst: ", end="")
        for sym, aff in sorted_syms[-3:]:
            d = detail.get(primary, {}).get(sym, {})
            print(f"{sym}({aff:.2f}, WR={d.get('win_rate',0):.0f}%) ", end="")
        print()

    # --- Per-Coin Summary ---
    print(f"\n{'='*80}")
    print(f"  PER-COIN SUMMARY (best strategies per coin, top 20 coins)")
    print(f"{'='*80}")

    # Aggregate per coin
    coin_data = defaultdict(list)
    for strat, sym, aff, d in all_combos:
        # Only use primary strategy names
        is_primary = any(strat == names[0] for names in STRATEGY_MAP.values())
        if is_primary:
            coin_data[sym].append((strat, aff, d))

    # Sort coins by best affinity
    coin_best = [(sym, max(entries, key=lambda x: x[1])) for sym, entries in coin_data.items()]
    coin_best.sort(key=lambda x: x[1][1], reverse=True)

    for sym, (best_strat, best_aff, _) in coin_best[:20]:
        entries = sorted(coin_data[sym], key=lambda x: x[1], reverse=True)
        strat_summary = ", ".join(f"{s}({a:.2f})" for s, a, _ in entries[:3])
        avg = sum(a for _, a, _ in entries) / len(entries)
        print(f"  {sym:<14} avg={avg:.3f} | best: {strat_summary}")

    # --- Summary stats ---
    affinities = [aff for _, _, aff, _ in all_combos]
    print(f"\n{'='*80}")
    print(f"  OVERALL STATS")
    print(f"{'='*80}")
    print(f"  Total combos:     {len(all_combos)}")
    print(f"  Mean affinity:    {sum(affinities)/len(affinities):.3f}")
    print(f"  Median affinity:  {sorted(affinities)[len(affinities)//2]:.3f}")
    print(f"  Tradeable (>=0.3): {sum(1 for a in affinities if a >= 0.3)} ({sum(1 for a in affinities if a >= 0.3)*100//len(affinities)}%)")
    print(f"  Strong (>=0.5):    {sum(1 for a in affinities if a >= 0.5)} ({sum(1 for a in affinities if a >= 0.5)*100//len(affinities)}%)")
    print(f"  Excellent (>=0.7): {sum(1 for a in affinities if a >= 0.7)} ({sum(1 for a in affinities if a >= 0.7)*100//len(affinities)}%)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print(f"Parsing SQL file: {SQL_FILE}")

    if not os.path.exists(SQL_FILE):
        print(f"ERROR: SQL file not found: {SQL_FILE}")
        print(f"Set AE_SQL_FILE env var or place file at expected path.")
        sys.exit(1)

    rows = parse_sql(SQL_FILE)
    print(f"Parsed {len(rows)} total rows from ae_results")

    train_rows = [r for r in rows if r["is_train"] == 1]
    test_rows = [r for r in rows if r["is_train"] == 0]
    print(f"  Train: {len(train_rows)} | Test: {len(test_rows)}")

    strategies = set(r["strategy_id"] for r in rows)
    pairs = set(r["pair"] for r in rows)
    print(f"  Strategies: {len(strategies)} | Pairs: {len(pairs)}")

    raw_matrix, raw_detail = build_matrix(rows)
    matrix, detail = expand_matrix(raw_matrix, raw_detail)

    save_matrix(matrix, detail)
    print_report(matrix, detail)

    # Quick demo of API
    print(f"\n{'='*80}")
    print(f"  API DEMO")
    print(f"{'='*80}")

    # Force reload from JSON to test the cache path
    global _MATRIX, _DETAIL
    _MATRIX, _DETAIL = matrix, detail

    demo_pairs = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "SUIUSDT"]
    for sym in demo_pairs:
        best = get_best_strategies_for_symbol(sym)
        if best:
            top = best[0]
            print(f"  {sym}: best={top[0]} (aff={top[1]:.3f}), should_trade={should_trade(top[0], sym)}")
        else:
            print(f"  {sym}: no data")


if __name__ == "__main__":
    main()
