#!/usr/bin/env python3
"""
Database Consolidation & QA Validation Script
Merges all portfolio data from every system into a unified format,
runs comprehensive quality checks, and scans dashboards for JS issues.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# ── Symbol normalization map ──
SYMBOL_CANONICAL = {}
_CRYPTO_BASES = [
    "BTC", "ETH", "SOL", "XRP", "ADA", "DOT", "LINK", "AVAX", "DOGE",
    "SHIB", "BNB", "NEAR", "FIL", "ATOM", "SAND", "FLOKI", "BONK",
    "PEPE", "WIF", "RENDER", "TRX", "BCH", "LTC", "MATIC", "ARB",
    "OP", "UNI", "AAVE", "MKR", "FET", "INJ", "SUI", "SEI", "TIA",
    "CHZ",
]
for base in _CRYPTO_BASES:
    canonical = f"{base}USDT"
    SYMBOL_CANONICAL[f"{base}-USD"] = canonical
    SYMBOL_CANONICAL[f"{base}USD"] = canonical
    SYMBOL_CANONICAL[f"{base}USDT"] = canonical
    SYMBOL_CANONICAL[f"{base}/USDT"] = canonical
    SYMBOL_CANONICAL[f"{base}/USD"] = canonical
    SYMBOL_CANONICAL[base] = canonical

# Equity/futures/forex pass through
_EQUITY_TICKERS = ["SPY", "QQQ", "IWM", "TLT", "SOFI", "AAPL", "MSFT", "NVDA", "AMD"]
for t in _EQUITY_TICKERS:
    SYMBOL_CANONICAL[t] = t

# Futures
_FUTURES_MAP = {"ES": "ES=F", "NQ": "NQ=F", "CL": "CL=F", "ZN": "ZN=F",
                "GC": "GC=F", "SI": "SI=F", "YM": "YM=F"}
for short, full in _FUTURES_MAP.items():
    SYMBOL_CANONICAL[short] = full
    SYMBOL_CANONICAL[full] = full

# Correlated asset pairs (for linked-pick detection)
CORRELATED_PAIRS = {
    ("SPY", "ES=F"), ("QQQ", "NQ=F"), ("BTCUSDT", "BTC=F"),
    ("ETHUSDT", "ETH=F"), ("EURUSD=X", "EURUSD"), ("GBPUSD=X", "GBPUSD"),
    ("AUDUSD=X", "AUDUSD"), ("GBPJPY=X", "GBPJPY"), ("NZDJPY=X", "NZDJPY"),
    ("USDMXN=X", "USDMXN"),
}


def normalize_symbol(sym: str) -> str:
    """Map any symbol variant to its canonical form."""
    s = sym.strip().upper()
    return SYMBOL_CANONICAL.get(s, s)


def classify_asset(symbol: str, category: str = "") -> str:
    """Determine asset class from symbol or category hint."""
    cat = category.lower() if category else ""
    sym = symbol.upper()
    if cat in ("crypto",) or sym.endswith("USDT") or "-USD" in sym:
        return "CRYPTO"
    if cat in ("futures",) or sym.endswith("=F"):
        return "FUTURES"
    if cat in ("forex",) or "=X" in sym or sym in ("EURUSD", "GBPUSD", "AUDUSD", "USDJPY"):
        return "FOREX"
    if cat in ("etf",) or sym in ("SPY", "QQQ", "IWM", "TLT", "GLD", "SLV", "XLF"):
        return "ETF"
    if cat in ("equity", "stock") or sym in ("SOFI", "AAPL", "MSFT", "NVDA", "AMD"):
        return "EQUITY"
    if cat in ("penny_stock",):
        return "PENNY_STOCK"
    if cat in ("mutual_fund",):
        return "MUTUAL_FUND"
    return "CRYPTO"  # default for this project


def safe_float(val, default=0.0):
    try:
        return float(val) if val is not None else default
    except (ValueError, TypeError):
        return default


def parse_timestamp(ts_str):
    """Parse various timestamp formats into datetime, return None on failure."""
    if not ts_str:
        return None
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.strptime(ts_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def load_json(path: Path):
    """Load a JSON file, return None if missing or invalid."""
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"  [WARN] Failed to load {path}: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# 1. CONSOLIDATE ALL PORTFOLIOS
# ═══════════════════════════════════════════════════════════════

def _normalize_pick(raw: dict, source: str) -> dict:
    """Convert any pick format into a unified schema."""
    symbol_raw = raw.get("symbol") or raw.get("ticker") or ""
    category = raw.get("category") or raw.get("asset_type") or raw.get("asset_class") or ""
    direction = (raw.get("direction") or raw.get("signal") or raw.get("signal_type") or "").upper()
    if direction in ("BUY", "STRONG_BUY"):
        direction = "LONG"
    elif direction in ("SELL", "STRONG_SELL"):
        direction = "SHORT"

    entry = safe_float(raw.get("entry_price") or raw.get("entryPrice") or raw.get("price"))
    tp = safe_float(raw.get("take_profit") or raw.get("tp_price") or raw.get("targetPrice"))
    sl = safe_float(raw.get("stop_loss") or raw.get("sl_price") or raw.get("stopPrice"))
    conf = safe_float(raw.get("confidence"))
    # KIMI uses 0-100 scale for confidence
    if conf > 1:
        conf = conf / 100.0

    ts_str = raw.get("timestamp") or raw.get("entry_time") or raw.get("generated_at") or raw.get("created_at") or ""
    status = (raw.get("status") or "OPEN").upper()
    strategy = raw.get("strategy") or raw.get("algorithm") or raw.get("source") or ""
    pnl = safe_float(raw.get("pnl_pct") or raw.get("unrealized_pnl_pct"))

    return {
        "symbol_raw": symbol_raw,
        "symbol": normalize_symbol(symbol_raw),
        "asset_class": classify_asset(symbol_raw, category),
        "direction": direction,
        "entry_price": entry,
        "take_profit": tp,
        "stop_loss": sl,
        "confidence": round(conf, 4),
        "timestamp": ts_str,
        "status": status,
        "strategy": strategy,
        "pnl_pct": round(pnl, 4),
        "source_system": source,
    }


def _load_multi_asset() -> dict:
    """Load multi_asset scanner picks."""
    active_path = BASE_DIR / "multi_asset" / "data" / "active_picks.json"
    closed_path = BASE_DIR / "multi_asset" / "data" / "multi_asset_closed.json"
    active_data = load_json(active_path) or []
    closed_data = load_json(closed_path) or []

    picks = []
    for p in active_data:
        picks.append(_normalize_pick(p, "multi_asset_scanner"))
    for p in closed_data:
        pick = _normalize_pick(p, "multi_asset_scanner")
        if pick["status"] == "OPEN":
            pick["status"] = p.get("status", "CLOSED").upper()
        picks.append(pick)

    wins = sum(1 for p in picks if p["status"] == "WON")
    losses = sum(1 for p in picks if p["status"] in ("LOST", "STOPPED"))
    decided = wins + losses
    pnl_vals = [p["pnl_pct"] for p in picks if p["pnl_pct"] != 0]

    return {
        "source_system": "multi_asset_scanner",
        "portfolio_id": "multi_asset_active",
        "asset_class": "MIXED",
        "picks": picks,
        "metrics": {
            "total_pnl": round(sum(pnl_vals), 4),
            "win_rate": round(wins / decided * 100, 2) if decided else 0.0,
            "sharpe": 0.0,
            "sortino": 0.0,
            "max_drawdown": 0.0,
        }
    }


def _load_alpha_engine() -> dict:
    """Load alpha engine picks."""
    path = BASE_DIR / "alpha_engine" / "data" / "active_picks.json"
    data = load_json(path) or []
    picks = [_normalize_pick(p, "alpha_engine") for p in data]

    pnl_vals = [p["pnl_pct"] for p in picks if p["pnl_pct"] != 0]
    wins = sum(1 for p in picks if p["pnl_pct"] > 0)
    decided = sum(1 for p in picks if p["pnl_pct"] != 0)

    return {
        "source_system": "alpha_engine",
        "portfolio_id": "alpha_active",
        "asset_class": "MIXED",
        "picks": picks,
        "metrics": {
            "total_pnl": round(sum(pnl_vals), 4),
            "win_rate": round(wins / decided * 100, 2) if decided else 0.0,
            "sharpe": 0.0,
            "sortino": 0.0,
            "max_drawdown": 0.0,
        }
    }


def _load_kimi() -> dict:
    """Load KIMI Rise of the Claw signals."""
    path = BASE_DIR / "KIMI_RISEOFTHECLAW" / "data" / "live_signals_now.json"
    data = load_json(path)
    if not data:
        return {
            "source_system": "kimi",
            "portfolio_id": "kimi_live",
            "asset_class": "MIXED",
            "picks": [],
            "metrics": {"total_pnl": 0, "win_rate": 0, "sharpe": 0, "sortino": 0, "max_drawdown": 0},
        }

    picks = []
    for section_key in ("crypto_signals", "forex_signals"):
        for sig in data.get(section_key, []):
            picks.append(_normalize_pick(sig, "kimi"))

    return {
        "source_system": "kimi",
        "portfolio_id": "kimi_live",
        "asset_class": "MIXED",
        "picks": picks,
        "metrics": {
            "total_pnl": 0.0,
            "win_rate": 0.0,
            "sharpe": 0.0,
            "sortino": 0.0,
            "max_drawdown": 0.0,
        }
    }


def _load_tournament() -> list:
    """Load tournament agent macro portfolios."""
    path = BASE_DIR / "tournament_agents" / "data" / "macro" / "macro_portfolios.json"
    data = load_json(path)
    if not data:
        return []

    portfolios = []
    for port in data:
        pid = port.get("portfolio_id", "unknown")
        asset_type = port.get("asset_type", "")
        perf = port.get("performance", {})

        picks = []
        for t in port.get("open_trades", []):
            picks.append(_normalize_pick(t, "tournament"))

        portfolios.append({
            "source_system": "tournament",
            "portfolio_id": pid,
            "asset_class": classify_asset("", asset_type),
            "picks": picks,
            "metrics": {
                "total_pnl": safe_float(perf.get("unrealized_pnl_pct")),
                "win_rate": safe_float(perf.get("win_rate")),
                "sharpe": 0.0,
                "sortino": 0.0,
                "max_drawdown": safe_float(perf.get("drawdown")),
            }
        })
    return portfolios


def _load_consensus() -> dict:
    """Load cross-aggregation consensus outcomes."""
    path = BASE_DIR / "cross_aggregation" / "data" / "consensus_outcomes.json"
    data = load_json(path)
    if not data:
        return {
            "source_system": "consensus",
            "portfolio_id": "consensus_tracker",
            "asset_class": "MIXED",
            "picks": [],
            "metrics": {"total_pnl": 0, "win_rate": 0, "sharpe": 0, "sortino": 0, "max_drawdown": 0},
        }

    picks = []
    for p in data.get("active", []):
        picks.append(_normalize_pick(p, "consensus"))
    for p in data.get("closed", []):
        pick = _normalize_pick(p, "consensus")
        pick["status"] = p.get("status", "CLOSED").upper()
        pick["pnl_pct"] = safe_float(p.get("pnl_pct"))
        picks.append(pick)

    stats = data.get("stats", {})
    return {
        "source_system": "consensus",
        "portfolio_id": "consensus_tracker",
        "asset_class": "MIXED",
        "picks": picks,
        "metrics": {
            "total_pnl": safe_float(stats.get("cumulative_pnl_pct")),
            "win_rate": safe_float(stats.get("win_rate")),
            "sharpe": 0.0,
            "sortino": 0.0,
            "max_drawdown": 0.0,
        }
    }


def consolidate_all_portfolios() -> list:
    """Merge all data sources into a unified format and save."""
    print("=" * 60)
    print("  CONSOLIDATING ALL PORTFOLIOS")
    print("=" * 60)

    portfolios = []

    print("\n  [1/5] Multi-Asset Scanner...")
    ma = _load_multi_asset()
    print(f"         -> {len(ma['picks'])} picks loaded")
    portfolios.append(ma)

    print("  [2/5] Alpha Engine...")
    ae = _load_alpha_engine()
    print(f"         -> {len(ae['picks'])} picks loaded")
    portfolios.append(ae)

    print("  [3/5] KIMI Rise of the Claw...")
    kimi = _load_kimi()
    print(f"         -> {len(kimi['picks'])} picks loaded")
    portfolios.append(kimi)

    print("  [4/5] Tournament Agents...")
    tourney = _load_tournament()
    total_tourney = sum(len(p["picks"]) for p in tourney)
    print(f"         -> {len(tourney)} portfolios, {total_tourney} picks loaded")
    portfolios.extend(tourney)

    print("  [5/5] Cross-Aggregation Consensus...")
    cons = _load_consensus()
    print(f"         -> {len(cons['picks'])} picks loaded")
    portfolios.append(cons)

    total_picks = sum(len(p["picks"]) for p in portfolios)
    print(f"\n  TOTAL: {len(portfolios)} portfolios, {total_picks} picks consolidated")

    out_path = DATA_DIR / "consolidated_portfolios.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(portfolios, f, indent=2, default=str)
    print(f"  Saved to: {out_path}")

    return portfolios


# ═══════════════════════════════════════════════════════════════
# 2. QA CHECKS
# ═══════════════════════════════════════════════════════════════

def run_qa_checks(portfolios: list) -> dict:
    """Comprehensive data quality validation."""
    print("\n" + "=" * 60)
    print("  RUNNING QA CHECKS")
    print("=" * 60)

    now = datetime.now(timezone.utc)
    all_picks = []
    for port in portfolios:
        for pick in port["picks"]:
            pick["_portfolio_id"] = port["portfolio_id"]
            all_picks.append(pick)

    report = {
        "generated_at": now.isoformat(),
        "total_picks_analyzed": len(all_picks),
        "duplicates": [],
        "stale_data": [],
        "price_issues": [],
        "sl_tp_issues": [],
        "linked_picks": [],
        "orphaned_picks": [],
        "confidence_issues": [],
        "symbol_normalization_applied": [],
    }

    # ── Duplicate Detection ──
    print("\n  [QA-1] Duplicate Detection...")
    seen = defaultdict(list)
    for pick in all_picks:
        key = (pick["symbol"], pick["direction"], pick["source_system"])
        seen[key].append(pick)

    # Cross-system duplicates (same symbol+direction across different systems)
    cross_seen = defaultdict(list)
    for pick in all_picks:
        cross_key = (pick["symbol"], pick["direction"])
        cross_seen[cross_key].append(pick)

    for key, group in cross_seen.items():
        sources = set(p["source_system"] for p in group)
        if len(sources) > 1:
            report["duplicates"].append({
                "symbol": key[0],
                "direction": key[1],
                "count": len(group),
                "sources": sorted(sources),
                "strategies": [p["strategy"] for p in group[:5]],
            })
    print(f"         -> {len(report['duplicates'])} cross-system duplicates found")

    # ── Stale Data ──
    print("  [QA-2] Stale Data Detection...")
    for pick in all_picks:
        ts = parse_timestamp(pick.get("timestamp", ""))
        if ts and (now - ts).total_seconds() > 86400:  # >24h
            hours_old = round((now - ts).total_seconds() / 3600, 1)
            report["stale_data"].append({
                "symbol": pick["symbol"],
                "source": pick["source_system"],
                "strategy": pick["strategy"],
                "timestamp": pick["timestamp"],
                "hours_old": hours_old,
            })
    print(f"         -> {len(report['stale_data'])} stale picks (>24h old)")

    # ── Price Validation ──
    print("  [QA-3] Price Validation...")
    for pick in all_picks:
        entry = pick["entry_price"]
        issues = []
        if entry <= 0:
            issues.append("zero_or_negative_entry")
        if entry > 1_000_000 and pick["asset_class"] == "CRYPTO":
            issues.append("unrealistic_crypto_price")
        if pick["take_profit"] <= 0 and pick["take_profit"] != 0:
            issues.append("negative_tp")
        if pick["stop_loss"] < 0:
            issues.append("negative_sl")
        if issues:
            report["price_issues"].append({
                "symbol": pick["symbol"],
                "source": pick["source_system"],
                "entry_price": entry,
                "take_profit": pick["take_profit"],
                "stop_loss": pick["stop_loss"],
                "issues": issues,
            })
    print(f"         -> {len(report['price_issues'])} price issues")

    # ── SL/TP Validation ──
    print("  [QA-4] SL/TP Validation...")
    for pick in all_picks:
        entry = pick["entry_price"]
        tp = pick["take_profit"]
        sl = pick["stop_loss"]
        direction = pick["direction"]
        issues = []

        if entry > 0 and tp > 0 and sl > 0:
            if direction == "LONG":
                if sl >= entry:
                    issues.append("sl_above_entry_for_long")
                if tp <= entry:
                    issues.append("tp_below_entry_for_long")
            elif direction == "SHORT":
                if sl <= entry:
                    issues.append("sl_below_entry_for_short")
                if tp >= entry:
                    issues.append("tp_above_entry_for_short")

        if issues:
            report["sl_tp_issues"].append({
                "symbol": pick["symbol"],
                "source": pick["source_system"],
                "direction": direction,
                "entry": entry,
                "tp": tp,
                "sl": sl,
                "issues": issues,
            })
    print(f"         -> {len(report['sl_tp_issues'])} SL/TP issues")

    # ── Linked Picks (correlated assets across systems) ──
    print("  [QA-5] Linked Pick Detection...")
    symbol_to_picks = defaultdict(list)
    for pick in all_picks:
        symbol_to_picks[pick["symbol"]].append(pick)

    for (s1, s2) in CORRELATED_PAIRS:
        picks_a = symbol_to_picks.get(s1, [])
        picks_b = symbol_to_picks.get(s2, [])
        if picks_a and picks_b:
            report["linked_picks"].append({
                "pair": [s1, s2],
                "count_a": len(picks_a),
                "count_b": len(picks_b),
                "sources_a": sorted(set(p["source_system"] for p in picks_a)),
                "sources_b": sorted(set(p["source_system"] for p in picks_b)),
            })
    print(f"         -> {len(report['linked_picks'])} correlated pairs active")

    # ── Orphaned Picks ──
    print("  [QA-6] Orphaned Pick Detection...")
    for pick in all_picks:
        issues = []
        if not pick.get("strategy"):
            issues.append("missing_strategy")
        if not pick.get("direction"):
            issues.append("missing_direction")
        if pick["entry_price"] == 0:
            issues.append("missing_entry_price")
        if not pick.get("timestamp"):
            issues.append("missing_timestamp")
        if not pick.get("symbol"):
            issues.append("missing_symbol")
        if issues:
            report["orphaned_picks"].append({
                "symbol": pick.get("symbol", "UNKNOWN"),
                "source": pick["source_system"],
                "strategy": pick.get("strategy", ""),
                "issues": issues,
            })
    print(f"         -> {len(report['orphaned_picks'])} orphaned picks")

    # ── Confidence Score Validation ──
    print("  [QA-7] Confidence Score Validation...")
    for pick in all_picks:
        conf = pick["confidence"]
        if conf < 0 or conf > 1:
            report["confidence_issues"].append({
                "symbol": pick["symbol"],
                "source": pick["source_system"],
                "confidence": conf,
                "issue": "out_of_range_0_1",
            })
    print(f"         -> {len(report['confidence_issues'])} confidence issues")

    # ── Symbol Normalization Log ──
    for pick in all_picks:
        if pick["symbol_raw"] != pick["symbol"]:
            report["symbol_normalization_applied"].append({
                "raw": pick["symbol_raw"],
                "canonical": pick["symbol"],
                "source": pick["source_system"],
            })
    # Deduplicate normalization entries
    seen_norms = set()
    unique_norms = []
    for entry in report["symbol_normalization_applied"]:
        key = (entry["raw"], entry["canonical"])
        if key not in seen_norms:
            seen_norms.add(key)
            unique_norms.append(entry)
    report["symbol_normalization_applied"] = unique_norms
    print(f"  [QA-8] Symbol normalizations applied: {len(unique_norms)} unique mappings")

    out_path = DATA_DIR / "qa_report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\n  QA report saved to: {out_path}")

    return report


# ═══════════════════════════════════════════════════════════════
# 3. JAVASCRIPT ERROR SCANNER
# ═══════════════════════════════════════════════════════════════

def check_javascript_errors() -> list:
    """Scan dashboard HTML files for common JS issues."""
    print("\n" + "=" * 60)
    print("  SCANNING DASHBOARD HTML FOR JS ISSUES")
    print("=" * 60)

    html_files = [
        BASE_DIR / "audit_dashboard" / "portfolio_history.html",
        BASE_DIR / "audit_dashboard" / "claudes_test.html",
        BASE_DIR / "multi_asset" / "dashboard.html",
    ]

    all_issues = []

    for fpath in html_files:
        if not fpath.exists():
            all_issues.append({
                "file": str(fpath.name),
                "issue": "FILE_NOT_FOUND",
                "line": 0,
                "detail": f"File does not exist: {fpath}",
            })
            continue

        try:
            content = fpath.read_text(encoding="utf-8")
        except Exception as e:
            all_issues.append({
                "file": str(fpath.name),
                "issue": "READ_ERROR",
                "line": 0,
                "detail": str(e),
            })
            continue

        lines = content.split("\n")
        print(f"\n  Scanning: {fpath.name} ({len(lines)} lines)")

        for i, line in enumerate(lines, 1):
            # Check 1: Unclosed quotes in onclick handlers (RECURRING BUG)
            # Pattern: html += '...<div onclick="...toggle('expanded')"...'
            if re.search(r"html\s*\+=\s*'.*onclick.*'[a-zA-Z]", line):
                all_issues.append({
                    "file": str(fpath.name),
                    "issue": "ONCLICK_QUOTE_BREAK",
                    "line": i,
                    "detail": "Single-quoted string with unescaped onclick handler — will break JS",
                })

            # Check 2: onclick with single quotes inside single-quoted string concatenation
            if re.search(r"html\s*\+=\s*'[^']*onclick\s*=\s*\"[^\"]*'", line):
                if not re.search(r"\\'", line):
                    all_issues.append({
                        "file": str(fpath.name),
                        "issue": "ONCLICK_UNESCAPED_QUOTE",
                        "line": i,
                        "detail": "onclick handler likely has unescaped quotes inside string concat",
                    })

            # Check 3: JSON.parse on potentially empty strings
            if re.search(r"JSON\.parse\s*\(\s*[a-zA-Z_]\w*\s*\)", line):
                # Check if there's a guard (|| '{}' or || '[]') on the same or previous line
                context = lines[max(0, i-2):i]
                context_str = " ".join(context)
                if "|| '{" not in context_str and '|| "[' not in context_str and "try" not in context_str:
                    all_issues.append({
                        "file": str(fpath.name),
                        "issue": "JSON_PARSE_NO_GUARD",
                        "line": i,
                        "detail": "JSON.parse() without try/catch or fallback — may crash on empty/null",
                    })

            # Check 4: Undefined variable risk — common patterns
            if re.search(r"\.innerHTML\s*=\s*[a-zA-Z_]\w*\s*;", line):
                var_match = re.search(r"\.innerHTML\s*=\s*([a-zA-Z_]\w*)\s*;", line)
                if var_match:
                    var_name = var_match.group(1)
                    # Check if this variable is declared somewhere in the file
                    if var_name not in ("html", "content", "text", "output", "result", "str", "s"):
                        declarations = [l for l in lines if re.search(rf"(let|var|const)\s+{var_name}\b", l)]
                        if not declarations:
                            all_issues.append({
                                "file": str(fpath.name),
                                "issue": "POSSIBLE_UNDEFINED_VAR",
                                "line": i,
                                "detail": f"Variable '{var_name}' used in innerHTML assignment — verify it's declared",
                            })

            # Check 5: Missing fallback for potentially null element access
            if re.search(r"document\.getElementById\(['\"][^'\"]+['\"]\)\.[a-zA-Z]", line):
                if "if " not in line and "?" not in line and "&&" not in line:
                    # Check previous line for null check
                    prev = lines[i-2] if i > 1 else ""
                    if "if " not in prev and "getElementById" not in prev:
                        all_issues.append({
                            "file": str(fpath.name),
                            "issue": "NO_NULL_CHECK_DOM",
                            "line": i,
                            "detail": "getElementById().property without null check — may throw if element missing",
                        })

        file_issues = [x for x in all_issues if x["file"] == fpath.name]
        print(f"         -> {len(file_issues)} potential issues found")

    return all_issues


# ═══════════════════════════════════════════════════════════════
# 4. SUMMARY REPORT
# ═══════════════════════════════════════════════════════════════

def generate_summary_report(portfolios: list, qa_report: dict, js_issues: list):
    """Print a human-readable summary."""
    now = datetime.now(timezone.utc)

    print("\n")
    print("=" * 60)
    print("  DATABASE CONSOLIDATION — SUMMARY REPORT")
    print(f"  Generated: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 60)

    # ── Portfolio Overview ──
    print("\n  PORTFOLIO OVERVIEW")
    print("  " + "-" * 56)
    total_picks = 0
    for port in portfolios:
        n = len(port["picks"])
        total_picks += n
        wr = port["metrics"]["win_rate"]
        pnl = port["metrics"]["total_pnl"]
        print(f"  {port['source_system']:25s} | {port['portfolio_id']:25s} | {n:4d} picks | WR {wr:5.1f}% | PnL {pnl:+8.2f}%")
    print("  " + "-" * 56)
    print(f"  {'TOTAL':25s} | {'':25s} | {total_picks:4d} picks")

    # ── Asset Class Distribution ──
    print("\n  ASSET CLASS DISTRIBUTION")
    print("  " + "-" * 40)
    class_counts = defaultdict(int)
    for port in portfolios:
        for pick in port["picks"]:
            class_counts[pick["asset_class"]] += 1
    for cls in sorted(class_counts, key=lambda x: -class_counts[x]):
        print(f"  {cls:20s} : {class_counts[cls]:4d} picks")

    # ── Data Freshness ──
    print("\n  DATA FRESHNESS")
    print("  " + "-" * 40)
    source_freshness = defaultdict(lambda: None)
    for port in portfolios:
        for pick in port["picks"]:
            ts = parse_timestamp(pick.get("timestamp", ""))
            if ts:
                src = pick["source_system"]
                if source_freshness[src] is None or ts > source_freshness[src]:
                    source_freshness[src] = ts

    for src in sorted(source_freshness):
        ts = source_freshness[src]
        if ts:
            age_hrs = (now - ts).total_seconds() / 3600
            status = "FRESH" if age_hrs < 1 else ("OK" if age_hrs < 24 else "STALE")
            marker = "  " if status != "STALE" else ">>"
            print(f"  {marker} {src:25s} : last data {age_hrs:6.1f}h ago  [{status}]")
        else:
            print(f"  >> {src:25s} : NO TIMESTAMP DATA  [UNKNOWN]")

    # ── QA Issues Summary ──
    print("\n  QA ISSUES SUMMARY")
    print("  " + "-" * 40)
    qa_categories = [
        ("duplicates", "Cross-system duplicates"),
        ("stale_data", "Stale picks (>24h)"),
        ("price_issues", "Price validation issues"),
        ("sl_tp_issues", "SL/TP logic errors"),
        ("linked_picks", "Correlated asset pairs"),
        ("orphaned_picks", "Orphaned/incomplete picks"),
        ("confidence_issues", "Confidence out of range"),
    ]
    total_issues = 0
    for key, label in qa_categories:
        count = len(qa_report.get(key, []))
        total_issues += count
        marker = "!!" if count > 0 else "  "
        print(f"  {marker} {label:35s} : {count:4d}")
    print("  " + "-" * 40)
    print(f"     {'TOTAL QA ISSUES':35s} : {total_issues:4d}")

    # ── Top Duplicates ──
    dupes = qa_report.get("duplicates", [])
    if dupes:
        print("\n  TOP DUPLICATED SYMBOLS (cross-system)")
        print("  " + "-" * 40)
        top_dupes = sorted(dupes, key=lambda x: -x["count"])[:10]
        for d in top_dupes:
            print(f"  {d['symbol']:15s} {d['direction']:6s} x{d['count']:2d}  sources: {', '.join(d['sources'])}")

    # ── JS Dashboard Issues ──
    print("\n  DASHBOARD JS SCAN")
    print("  " + "-" * 40)
    if js_issues:
        by_file = defaultdict(list)
        for iss in js_issues:
            by_file[iss["file"]].append(iss)
        for fname, issues in sorted(by_file.items()):
            print(f"  {fname}: {len(issues)} issues")
            for iss in issues[:3]:
                print(f"    L{iss['line']:4d} [{iss['issue']}] {iss['detail'][:60]}")
            if len(issues) > 3:
                print(f"    ... and {len(issues) - 3} more")
    else:
        print("  No JS issues detected.")

    # ── System Health ──
    print("\n  SYSTEM HEALTH")
    print("  " + "-" * 40)
    sources_found = set()
    for port in portfolios:
        if port["picks"]:
            sources_found.add(port["source_system"])
    expected = {"multi_asset_scanner", "alpha_engine", "kimi", "tournament", "consensus"}
    for src in sorted(expected):
        status = "UP" if src in sources_found else "NO DATA"
        marker = "  " if status == "UP" else "!!"
        print(f"  {marker} {src:25s} : {status}")

    health_score = len(sources_found & expected) / len(expected) * 100
    print(f"\n  Overall health: {health_score:.0f}% ({len(sources_found & expected)}/{len(expected)} systems reporting)")
    print(f"  Total QA issues: {total_issues}")
    print(f"  JS dashboard issues: {len(js_issues)}")
    print("=" * 60)

    return {
        "total_picks": total_picks,
        "total_portfolios": len(portfolios),
        "total_qa_issues": total_issues,
        "total_js_issues": len(js_issues),
        "health_score_pct": health_score,
    }


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    portfolios = consolidate_all_portfolios()
    qa_report = run_qa_checks(portfolios)
    js_issues = check_javascript_errors()
    summary = generate_summary_report(portfolios, qa_report, js_issues)

    print(f"\nOutputs saved to:")
    print(f"  {DATA_DIR / 'consolidated_portfolios.json'}")
    print(f"  {DATA_DIR / 'qa_report.json'}")
    print()
