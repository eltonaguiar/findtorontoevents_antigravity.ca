"""
Pump-and-Dump Detection Guard
==============================
Protects the Alpha Engine from entering positions during pump-and-dump events.

Built from forensic analysis of 57 pump_forensics_scans, 18 ah_pump_analysis
records, 23 sf_spikes entries, and 2 spike_detector_alerts from the
ejaguiar1_memecoin database (historical Kraken + multi-exchange data).

Reuses patterns from:
  - KIMI crypto_acceleration_engine.py signal_pump_detector (velocity + vol + RSI jerk)
  - skyrocket_detector feature_engine.py (vol_accel, RSI, BB features)

Usage:
    # Standalone
    python -m alpha_engine.pump_guard

    # As library
    from alpha_engine.pump_guard import calculate_pump_risk, filter_pump_signals
    risk = calculate_pump_risk("BTCUSDT", price_change_1h=18.0, volume_ratio=6.2)
    filtered = filter_pump_signals(picks)

    # Enrichment (add pump_risk_score to each pick)
    from alpha_engine.pump_guard import enrich_picks_with_pump_risk
    picks = enrich_picks_with_pump_risk(picks)
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Windows UTF-8 fix
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).resolve().parent
_DATA_DIR = _THIS_DIR / "data"
_PATTERNS_PATH = _DATA_DIR / "pump_patterns.json"

# Default SQL file location (can be overridden)
_DEFAULT_SQL_PATH = Path(r"C:\Users\zerou\Downloads\ejaguiar1_memecoin_mar312026.sql")


# ============================================================================
# PART 1: SQL Parser -- Extract pump forensics data
# ============================================================================

def _parse_sql_inserts(sql_text: str, table_name: str) -> list[dict]:
    """
    Parse INSERT INTO statements for a given table from a MySQL dump.
    Returns list of dicts with column names as keys.
    """
    # Find the column list from INSERT INTO ... (col1, col2, ...) VALUES
    pattern = (
        r"INSERT INTO `" + re.escape(table_name)
        + r"`\s*\(([^)]+)\)\s*VALUES\s*"
    )
    results = []
    for match in re.finditer(pattern, sql_text):
        columns_str = match.group(1)
        columns = [c.strip().strip("`") for c in columns_str.split(",")]

        # Extract the VALUES portion -- everything from the match end to the
        # next semicolon (handles multi-row INSERTs split across lines)
        start = match.end()
        # Find the closing semicolon
        semi = sql_text.find(";", start)
        if semi == -1:
            semi = len(sql_text)
        values_block = sql_text[start:semi]

        # Parse individual row tuples: (...), (...), ...
        # Use a simple state machine to handle quoted strings with commas
        rows = _extract_value_tuples(values_block)
        for row_values in rows:
            if len(row_values) == len(columns):
                record = {}
                for col, val in zip(columns, row_values):
                    record[col] = _cast_sql_value(val)
                results.append(record)

    return results


def _extract_value_tuples(block: str) -> list[list[str]]:
    """Extract individual value tuples from a VALUES block."""
    tuples = []
    i = 0
    n = len(block)

    while i < n:
        # Find opening paren
        if block[i] == "(":
            # Extract until matching closing paren (handle nested quotes)
            values, end = _parse_one_tuple(block, i)
            if values is not None:
                tuples.append(values)
            i = end + 1
        else:
            i += 1

    return tuples


def _parse_one_tuple(block: str, start: int) -> tuple[Optional[list[str]], int]:
    """Parse one (...) tuple, returns (values_list, end_index)."""
    i = start + 1  # skip opening paren
    n = len(block)
    values = []
    current = []
    in_string = False
    quote_char = None

    while i < n:
        ch = block[i]

        if in_string:
            if ch == "\\" and i + 1 < n:
                current.append(ch)
                current.append(block[i + 1])
                i += 2
                continue
            elif ch == quote_char:
                # Check for escaped quote ('')
                if i + 1 < n and block[i + 1] == quote_char:
                    current.append(ch)
                    current.append(ch)
                    i += 2
                    continue
                in_string = False
                current.append(ch)
            else:
                current.append(ch)
        else:
            if ch in ("'", '"'):
                in_string = True
                quote_char = ch
                current.append(ch)
            elif ch == ",":
                values.append("".join(current).strip())
                current = []
            elif ch == ")":
                values.append("".join(current).strip())
                return values, i
            else:
                current.append(ch)
        i += 1

    return None, i


def _cast_sql_value(val: str):
    """Cast a SQL value string to a Python type."""
    if val == "NULL" or val == "null":
        return None
    # Strip quotes
    if (val.startswith("'") and val.endswith("'")) or \
       (val.startswith('"') and val.endswith('"')):
        return val[1:-1].replace("\\'", "'").replace('\\"', '"')
    # Try numeric
    try:
        if "." in val:
            return float(val)
        return int(val)
    except (ValueError, TypeError):
        return val


def parse_pump_data(sql_path: Optional[str] = None) -> dict:
    """
    Parse all pump-related tables from the SQL dump file.

    Returns dict with keys:
        pump_forensics_scans: list[dict]
        ah_pump_analysis: list[dict]
        sf_spikes: list[dict]
        spike_detector_alerts: list[dict]
    """
    path = Path(sql_path) if sql_path else _DEFAULT_SQL_PATH
    if not path.exists():
        print(f"[pump_guard] SQL file not found: {path}")
        return {
            "pump_forensics_scans": [],
            "ah_pump_analysis": [],
            "sf_spikes": [],
            "spike_detector_alerts": [],
        }

    print(f"[pump_guard] Parsing SQL file: {path}")
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        sql_text = f.read()

    data = {
        "pump_forensics_scans": _parse_sql_inserts(sql_text, "pump_forensics_scans"),
        "ah_pump_analysis": _parse_sql_inserts(sql_text, "ah_pump_analysis"),
        "sf_spikes": _parse_sql_inserts(sql_text, "sf_spikes"),
        "spike_detector_alerts": _parse_sql_inserts(sql_text, "spike_detector_alerts"),
    }

    for table, rows in data.items():
        print(f"  {table}: {len(rows)} records")

    return data


# ============================================================================
# PART 2: Build Pump Pattern Library from historical data
# ============================================================================

def _normalize_symbol(pair: str) -> str:
    """
    Normalize Kraken/exchange pair formats to a canonical form.
    XXBTZUSD -> BTCUSDT, XETHZUSD -> ETHUSDT, SOLUSD -> SOLUSDT, etc.
    """
    pair = pair.upper().strip()

    # Kraken mappings
    kraken_map = {
        "XXBTZUSD": "BTCUSDT", "XETHZUSD": "ETHUSDT",
        "XXRPZUSD": "XRPUSDT", "XLTCZUSD": "LTCUSDT",
        "XDGUSD": "DOGEUSDT", "XZECZUSD": "ZECUSDT",
    }
    if pair in kraken_map:
        return kraken_map[pair]

    # Generic: remove trailing USD, append USDT
    if pair.endswith("USD") and not pair.endswith("USDT"):
        base = pair[:-3]
        # Strip leading X if it's a Kraken-style prefix and base is short
        if base.startswith("X") and len(base) <= 4:
            base = base[1:]
        return base + "USDT"

    if not pair.endswith("USDT"):
        return pair + "USDT"
    return pair


def build_pump_pattern_library(data: dict) -> dict:
    """
    Analyze historical pump data and build a pattern library.

    Returns a dict with:
        known_pump_symbols: dict of symbol -> pump stats
        grade_distribution: dict of grade -> count
        avg_scores_by_grade: dict of grade -> avg subscores
        post_spike_crash_stats: post-spike price action stats
        fingerprints: common pre-pump indicator fingerprints
        thresholds: calibrated thresholds for real-time detection
    """
    library = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_counts": {},
        "known_pump_symbols": {},
        "grade_distribution": {},
        "avg_scores_by_grade": {},
        "post_spike_crash_stats": {},
        "fingerprints": {},
        "thresholds": {},
    }

    # --- Analyze pump_forensics_scans ---
    scans = data.get("pump_forensics_scans", [])
    library["source_counts"]["pump_forensics_scans"] = len(scans)

    symbol_stats: dict[str, dict] = {}
    grade_counts: dict[str, int] = {}
    grade_scores: dict[str, list[dict]] = {}

    for scan in scans:
        pair = scan.get("pair", "")
        symbol = _normalize_symbol(pair)
        grade = scan.get("pump_grade", "LOW")
        score = scan.get("pump_score", 0) or 0

        # Track per-symbol
        if symbol not in symbol_stats:
            symbol_stats[symbol] = {
                "scan_count": 0,
                "max_score": 0,
                "avg_score": 0,
                "grades": [],
                "has_resolved": False,
                "tp_hits": 0,
                "sl_hits": 0,
                "avg_pnl": None,
                "scores_list": [],
            }
        stats = symbol_stats[symbol]
        stats["scan_count"] += 1
        stats["max_score"] = max(stats["max_score"], score)
        stats["grades"].append(grade)
        stats["scores_list"].append(score)

        # Track resolved outcomes
        status = scan.get("status", "")
        pnl = scan.get("pnl_pct")
        exit_reason = scan.get("exit_reason", "")
        if status == "RESOLVED":
            stats["has_resolved"] = True
            if exit_reason == "TP_HIT":
                stats["tp_hits"] += 1
            elif exit_reason == "SL_HIT":
                stats["sl_hits"] += 1

        # Grade distribution
        grade_counts[grade] = grade_counts.get(grade, 0) + 1

        # Collect subscores per grade
        if grade not in grade_scores:
            grade_scores[grade] = []
        grade_scores[grade].append({
            "vol_trend": scan.get("vol_trend_score", 0) or 0,
            "range_comp": scan.get("range_comp_score", 0) or 0,
            "dip_buy": scan.get("dip_buy_score", 0) or 0,
            "obv_accum": scan.get("obv_accum_score", 0) or 0,
            "rsi_setup": scan.get("rsi_setup_score", 0) or 0,
            "vol_spike": scan.get("vol_spike_score", 0) or 0,
            "momentum": scan.get("momentum_score", 0) or 0,
            "consolidation": scan.get("consolidation_score", 0) or 0,
        })

    # Finalize per-symbol stats
    for sym, stats in symbol_stats.items():
        scores = stats.pop("scores_list")
        stats["avg_score"] = round(sum(scores) / len(scores), 1) if scores else 0
        stats["grades"] = list(set(stats["grades"]))

    library["known_pump_symbols"] = symbol_stats
    library["grade_distribution"] = grade_counts

    # Average subscores by grade
    for grade, scores_list in grade_scores.items():
        avg = {}
        if scores_list:
            for key in scores_list[0]:
                vals = [s[key] for s in scores_list]
                avg[key] = round(sum(vals) / len(vals), 2)
        library["avg_scores_by_grade"][grade] = avg

    # --- Analyze ah_pump_analysis (pre-pump fingerprints) ---
    pumps = data.get("ah_pump_analysis", [])
    library["source_counts"]["ah_pump_analysis"] = len(pumps)

    fingerprints = {
        "avg_pump_pct": 0,
        "avg_pre_rsi": 0,
        "avg_pre_vol_ratio": 0,
        "avg_pre_adx": 0,
        "pct_bearish_ema": 0,
        "pct_near_support": 0,
        "pct_bb_squeeze": 0,
        "pump_symbols": [],
    }

    if pumps:
        pump_pcts = [p.get("pump_pct", 0) or 0 for p in pumps]
        rsis = [p.get("pre_rsi", 0) or 0 for p in pumps]
        vol_ratios = [p.get("pre_vol_ratio", 0) or 0 for p in pumps]
        adxs = [p.get("pre_adx", 0) or 0 for p in pumps]

        fingerprints["avg_pump_pct"] = round(sum(pump_pcts) / len(pump_pcts), 2)
        fingerprints["avg_pre_rsi"] = round(sum(rsis) / len(rsis), 2)
        fingerprints["avg_pre_vol_ratio"] = round(sum(vol_ratios) / len(vol_ratios), 2)
        fingerprints["avg_pre_adx"] = round(sum(adxs) / len(adxs), 2)

        bearish_count = sum(1 for p in pumps if (p.get("pre_ema_alignment") or "") == "bearish")
        support_count = sum(1 for p in pumps if p.get("pre_price_near_support") == 1)
        squeeze_count = sum(1 for p in pumps if p.get("pre_squeeze") == 1)

        fingerprints["pct_bearish_ema"] = round(100 * bearish_count / len(pumps), 1)
        fingerprints["pct_near_support"] = round(100 * support_count / len(pumps), 1)
        fingerprints["pct_bb_squeeze"] = round(100 * squeeze_count / len(pumps), 1)

        pump_syms = list(set(_normalize_symbol(p.get("pair", "")) for p in pumps))
        fingerprints["pump_symbols"] = sorted(pump_syms)

    library["fingerprints"] = fingerprints

    # --- Analyze sf_spikes (post-spike crash data) ---
    spikes = data.get("sf_spikes", [])
    library["source_counts"]["sf_spikes"] = len(spikes)

    if spikes:
        post3 = [s.get("post_3candle_pct", 0) or 0 for s in spikes]
        post5 = [s.get("post_5candle_pct", 0) or 0 for s in spikes]
        post10 = [s.get("post_10candle_pct", 0) or 0 for s in spikes]
        spike_pcts = [s.get("spike_pct", 0) or 0 for s in spikes]

        library["post_spike_crash_stats"] = {
            "n_spikes": len(spikes),
            "avg_spike_pct": round(sum(spike_pcts) / len(spike_pcts), 2),
            "avg_post_3candle_pct": round(sum(post3) / len(post3), 2),
            "avg_post_5candle_pct": round(sum(post5) / len(post5), 2),
            "avg_post_10candle_pct": round(sum(post10) / len(post10), 2),
            "pct_negative_post3": round(
                100 * sum(1 for v in post3 if v < 0) / len(post3), 1
            ),
            "pct_negative_post5": round(
                100 * sum(1 for v in post5 if v < 0) / len(post5), 1
            ),
            "pct_negative_post10": round(
                100 * sum(1 for v in post10 if v < 0) / len(post10), 1
            ),
        }

    # --- Calibrate thresholds from data ---
    # These thresholds are derived from the forensic data:
    #   - ah_pump_analysis avg pump was ~19% with avg vol_ratio ~1.5x
    #   - HIGH/VERY_HIGH grade scans had vol_spike_score >= 7 (vol > 2-3x)
    #   - Post-spike data shows ~48% crash in 3 candles after spike
    #   - KIMI pump_detector uses 8% velocity + 5x volume as entry
    library["thresholds"] = {
        "price_change_1h_warning": 10.0,    # % -- yellow flag
        "price_change_1h_danger": 15.0,     # % -- red flag
        "price_change_1h_extreme": 25.0,    # % -- almost certainly a pump
        "volume_ratio_warning": 3.0,        # x avg -- yellow flag
        "volume_ratio_danger": 5.0,         # x avg -- red flag (KIMI threshold)
        "volume_ratio_extreme": 10.0,       # x avg -- extreme
        "rsi_overbought": 70.0,             # RSI above this = overheated
        "rsi_extreme": 80.0,                # RSI above this = very overheated
        "known_pump_symbol_boost": 0.15,    # baseline risk boost for known pump symbols
        "social_spike_boost": 0.20,         # risk boost when social + price spike together
        "high_grade_block_threshold": 0.70, # block picks above this pump risk
        "warning_threshold": 0.50,          # warn but allow above this
    }

    return library


def save_pump_patterns(library: dict, path: Optional[Path] = None):
    """Save the pump pattern library to JSON."""
    out_path = path or _PATTERNS_PATH
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(library, f, indent=2, default=str)
    print(f"[pump_guard] Saved pump pattern library to {out_path}")
    print(f"  Known symbols: {len(library.get('known_pump_symbols', {}))}")
    print(f"  Fingerprints from: {library.get('source_counts', {})}")


def load_pump_patterns(path: Optional[Path] = None) -> dict:
    """Load the pump pattern library from JSON, or build it if missing."""
    load_path = path or _PATTERNS_PATH
    if load_path.exists():
        with open(load_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # Auto-build from SQL if available
    print("[pump_guard] Pattern library not found, attempting to build...")
    data = parse_pump_data()
    if any(data.values()):
        library = build_pump_pattern_library(data)
        save_pump_patterns(library)
        return library

    # Return minimal defaults
    return {"known_pump_symbols": {}, "thresholds": _default_thresholds()}


def _default_thresholds() -> dict:
    return {
        "price_change_1h_warning": 10.0,
        "price_change_1h_danger": 15.0,
        "price_change_1h_extreme": 25.0,
        "volume_ratio_warning": 3.0,
        "volume_ratio_danger": 5.0,
        "volume_ratio_extreme": 10.0,
        "rsi_overbought": 70.0,
        "rsi_extreme": 80.0,
        "known_pump_symbol_boost": 0.15,
        "social_spike_boost": 0.20,
        "high_grade_block_threshold": 0.70,
        "warning_threshold": 0.50,
    }


# ============================================================================
# PART 3: Real-Time Pump Risk Scorer
# ============================================================================

# Lazy-loaded pattern library (singleton)
_PATTERNS: Optional[dict] = None


def _get_patterns() -> dict:
    global _PATTERNS
    if _PATTERNS is None:
        _PATTERNS = load_pump_patterns()
    return _PATTERNS


def calculate_pump_risk(
    symbol: str,
    price_change_1h: float,
    volume_ratio: float,
    social_spike: bool = False,
    rsi: Optional[float] = None,
    price_change_4h: Optional[float] = None,
    momentum_jerk: Optional[float] = None,
) -> float:
    """
    Calculate pump-and-dump risk score for a symbol.

    Args:
        symbol: Trading pair (e.g. "BTCUSDT")
        price_change_1h: 1-hour price change in % (e.g. 15.0 = +15%)
        volume_ratio: Current volume vs 20-period average (e.g. 5.0 = 5x)
        social_spike: Whether social media mentions are spiking
        rsi: Current RSI value (optional, 0-100)
        price_change_4h: 4-hour price change in % (optional)
        momentum_jerk: 2nd derivative of price (optional, from KIMI)

    Returns:
        Float 0.0-1.0 pump risk score.
        0.0-0.3 = low risk (normal)
        0.3-0.5 = moderate (caution)
        0.5-0.7 = high (avoid entering)
        0.7-1.0 = extreme (very likely pump-and-dump)
    """
    patterns = _get_patterns()
    thresholds = patterns.get("thresholds", _default_thresholds())
    known_symbols = patterns.get("known_pump_symbols", {})

    risk = 0.0

    # --- Factor 1: Price velocity (biggest single factor) ---
    # Calibrated from ah_pump_analysis: avg pump was ~19%
    pc = abs(price_change_1h)
    if pc >= thresholds["price_change_1h_extreme"]:
        risk += 0.35
    elif pc >= thresholds["price_change_1h_danger"]:
        risk += 0.25
    elif pc >= thresholds["price_change_1h_warning"]:
        risk += 0.15

    # --- Factor 2: Volume spike ---
    # Calibrated from forensics: HIGH grade scans had vol_spike_score >= 7
    # KIMI pump_detector uses 5x as threshold
    if volume_ratio >= thresholds["volume_ratio_extreme"]:
        risk += 0.30
    elif volume_ratio >= thresholds["volume_ratio_danger"]:
        risk += 0.20
    elif volume_ratio >= thresholds["volume_ratio_warning"]:
        risk += 0.10

    # --- Factor 3: Combined velocity + volume (multiplicative danger) ---
    # When BOTH price and volume spike together, risk is much higher
    if pc >= 10.0 and volume_ratio >= 3.0:
        risk += 0.10  # synergy bonus
    if pc >= 15.0 and volume_ratio >= 5.0:
        risk += 0.10  # double synergy

    # --- Factor 4: RSI overheating ---
    if rsi is not None:
        if rsi >= thresholds["rsi_extreme"]:
            risk += 0.15
        elif rsi >= thresholds["rsi_overbought"]:
            risk += 0.08

    # --- Factor 5: 4h momentum (from KIMI signal_pump_detector pattern) ---
    if price_change_4h is not None:
        if abs(price_change_4h) >= 20.0:
            risk += 0.10
        elif abs(price_change_4h) >= 12.0:
            risk += 0.05

    # --- Factor 6: Momentum jerk (2nd derivative -- KIMI pattern) ---
    # Positive jerk during a spike = accelerating pump
    if momentum_jerk is not None and momentum_jerk > 0 and pc >= 10.0:
        risk += 0.05

    # --- Factor 7: Social spike amplifier ---
    # From forensic data: social + price spike = very likely pump
    if social_spike and pc >= 8.0:
        risk += thresholds["social_spike_boost"]
    elif social_spike:
        risk += 0.05

    # --- Factor 8: Known pump symbol baseline ---
    sym_upper = symbol.upper()
    if sym_upper in known_symbols:
        sym_data = known_symbols[sym_upper]
        max_grade = max(sym_data.get("grades", ["LOW"]),
                        key=lambda g: {"LOW": 0, "MODERATE": 1, "HIGH": 2, "VERY_HIGH": 3}.get(g, 0))
        if max_grade in ("HIGH", "VERY_HIGH"):
            risk += thresholds["known_pump_symbol_boost"]
        elif max_grade == "MODERATE":
            risk += 0.05

    return min(1.0, round(risk, 4))


# ============================================================================
# PART 4: Live Data Fetcher (Binance API with failover)
# ============================================================================

_BINANCE_ENDPOINTS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://data-api.binance.vision",
]


def _fetch_binance_ticker(symbol: str) -> Optional[dict]:
    """Fetch 24hr ticker stats for a symbol from Binance (with failover)."""
    for base in _BINANCE_ENDPOINTS:
        try:
            url = f"{base}/api/v3/ticker/24hr?symbol={symbol}"
            req = urllib.request.Request(url, headers={"User-Agent": "PumpGuard/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except Exception:
            continue
    return None


def _fetch_binance_klines(symbol: str, interval: str = "1h", limit: int = 25) -> Optional[list]:
    """Fetch klines for RSI / volume ratio calculation."""
    for base in _BINANCE_ENDPOINTS:
        try:
            url = f"{base}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
            req = urllib.request.Request(url, headers={"User-Agent": "PumpGuard/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except Exception:
            continue
    return None


def _compute_rsi(closes: list[float], period: int = 14) -> Optional[float]:
    """Compute RSI from a list of close prices."""
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def fetch_live_pump_risk(symbol: str) -> dict:
    """
    Fetch live data from Binance and compute pump risk for a symbol.

    Returns dict with:
        symbol, pump_risk_score, price_change_1h, volume_ratio,
        rsi, price_change_pct_24h, current_price, risk_label
    """
    result = {
        "symbol": symbol,
        "pump_risk_score": 0.0,
        "price_change_1h": 0.0,
        "volume_ratio": 1.0,
        "rsi": None,
        "price_change_pct_24h": 0.0,
        "current_price": 0.0,
        "risk_label": "LOW",
        "error": None,
    }

    # Get 24h ticker
    ticker = _fetch_binance_ticker(symbol)
    if ticker is None:
        result["error"] = "ticker_fetch_failed"
        return result

    try:
        result["price_change_pct_24h"] = float(ticker.get("priceChangePercent", 0))
        result["current_price"] = float(ticker.get("lastPrice", 0))
    except (ValueError, TypeError):
        pass

    # Get 1h klines for price change and volume ratio
    klines = _fetch_binance_klines(symbol, "1h", 25)
    if klines and len(klines) >= 3:
        try:
            closes = [float(k[4]) for k in klines]
            volumes = [float(k[5]) for k in klines]

            # 1h price change
            if closes[-2] > 0:
                result["price_change_1h"] = ((closes[-1] - closes[-2]) / closes[-2]) * 100

            # Volume ratio: current vs 20-period avg
            if len(volumes) > 2:
                avg_vol = sum(volumes[:-1]) / len(volumes[:-1])
                if avg_vol > 0:
                    result["volume_ratio"] = round(volumes[-1] / avg_vol, 2)

            # RSI
            result["rsi"] = _compute_rsi(closes)
            if result["rsi"] is not None:
                result["rsi"] = round(result["rsi"], 1)
        except Exception:
            pass

    # 4h price change (approximate from klines)
    price_change_4h = None
    if klines and len(klines) >= 5:
        try:
            c_now = float(klines[-1][4])
            c_4h = float(klines[-5][4])
            if c_4h > 0:
                price_change_4h = ((c_now - c_4h) / c_4h) * 100
        except Exception:
            pass

    # Compute risk score
    result["pump_risk_score"] = calculate_pump_risk(
        symbol=symbol,
        price_change_1h=result["price_change_1h"],
        volume_ratio=result["volume_ratio"],
        rsi=result["rsi"],
        price_change_4h=price_change_4h,
    )

    # Risk label
    score = result["pump_risk_score"]
    if score >= 0.70:
        result["risk_label"] = "EXTREME"
    elif score >= 0.50:
        result["risk_label"] = "HIGH"
    elif score >= 0.30:
        result["risk_label"] = "MODERATE"
    else:
        result["risk_label"] = "LOW"

    return result


# ============================================================================
# PART 5: Signal Filtering (Integration with Alpha Engine)
# ============================================================================

def filter_pump_signals(picks: list[dict], block_threshold: float = 0.70) -> list[dict]:
    """
    Remove picks on tokens currently showing pump-and-dump characteristics.

    Args:
        picks: List of pick dicts (must have 'symbol' key)
        block_threshold: Risk score above which picks are blocked (default 0.70)

    Returns:
        Filtered list of picks (blocked picks are removed).
        Prints warnings for blocked and flagged picks.
    """
    if not picks:
        return picks

    patterns = _get_patterns()
    warn_threshold = patterns.get("thresholds", {}).get("warning_threshold", 0.50)

    filtered = []
    blocked_count = 0
    warned_count = 0

    # Collect unique crypto symbols that need checking
    crypto_symbols = set()
    for pick in picks:
        sym = pick.get("symbol", "")
        # Only check crypto (skip forex =X suffix, stocks)
        if sym.endswith("USDT") or sym.endswith("-USD"):
            # Normalize to Binance format
            binance_sym = sym.replace("-USD", "USDT") if "-USD" in sym else sym
            crypto_symbols.add(binance_sym)

    # Batch fetch risk scores
    risk_cache: dict[str, dict] = {}
    for sym in crypto_symbols:
        try:
            risk_data = fetch_live_pump_risk(sym)
            risk_cache[sym] = risk_data
        except Exception as e:
            print(f"  [PUMP_GUARD] Error checking {sym}: {e}")
        time.sleep(0.2)  # Rate limiting

    # Filter picks
    for pick in picks:
        sym = pick.get("symbol", "")
        binance_sym = sym.replace("-USD", "USDT") if "-USD" in sym else sym

        if binance_sym not in risk_cache:
            # Non-crypto or fetch failed -- pass through
            filtered.append(pick)
            continue

        risk_data = risk_cache[binance_sym]
        risk_score = risk_data["pump_risk_score"]

        # Add pump_risk_score to the pick
        pick["pump_risk_score"] = risk_score
        pick["pump_risk_label"] = risk_data["risk_label"]

        if risk_score >= block_threshold:
            blocked_count += 1
            print(
                f"  [PUMP_GUARD] BLOCKED: {sym} "
                f"(risk={risk_score:.2f} [{risk_data['risk_label']}], "
                f"1h={risk_data['price_change_1h']:+.1f}%, "
                f"vol={risk_data['volume_ratio']:.1f}x, "
                f"RSI={risk_data.get('rsi', 'N/A')})"
            )
            continue  # Do not include in filtered output

        if risk_score >= warn_threshold:
            warned_count += 1
            print(
                f"  [PUMP_GUARD] WARNING: {sym} elevated pump risk "
                f"(risk={risk_score:.2f} [{risk_data['risk_label']}], "
                f"1h={risk_data['price_change_1h']:+.1f}%, "
                f"vol={risk_data['volume_ratio']:.1f}x)"
            )

        filtered.append(pick)

    total = len(picks)
    print(
        f"[PUMP_GUARD] Result: {len(filtered)}/{total} picks passed "
        f"({blocked_count} blocked, {warned_count} warned)"
    )
    return filtered


def enrich_picks_with_pump_risk(picks: list[dict]) -> list[dict]:
    """
    Add pump_risk_score and pump_risk_label to each crypto pick without filtering.

    This is a non-destructive enrichment suitable for wiring into
    production_scanner.py's enrichment pipeline.
    """
    if not picks:
        return picks

    crypto_picks = []
    for pick in picks:
        sym = pick.get("symbol", "")
        if sym.endswith("USDT") or sym.endswith("-USD"):
            crypto_picks.append(pick)

    if not crypto_picks:
        print("[PUMP_GUARD] No crypto picks to check")
        return picks

    # Deduplicate symbols
    symbols_to_check = set()
    for pick in crypto_picks:
        sym = pick.get("symbol", "")
        binance_sym = sym.replace("-USD", "USDT") if "-USD" in sym else sym
        symbols_to_check.add(binance_sym)

    # Fetch risk scores
    risk_cache: dict[str, dict] = {}
    for sym in symbols_to_check:
        try:
            risk_cache[sym] = fetch_live_pump_risk(sym)
        except Exception:
            pass
        time.sleep(0.15)

    # Enrich
    enriched_count = 0
    high_risk_count = 0
    for pick in picks:
        sym = pick.get("symbol", "")
        binance_sym = sym.replace("-USD", "USDT") if "-USD" in sym else sym

        if binance_sym in risk_cache:
            rd = risk_cache[binance_sym]
            pick["pump_risk_score"] = rd["pump_risk_score"]
            pick["pump_risk_label"] = rd["risk_label"]
            enriched_count += 1
            if rd["pump_risk_score"] >= 0.50:
                high_risk_count += 1
        else:
            pick.setdefault("pump_risk_score", 0.0)
            pick.setdefault("pump_risk_label", "N/A")

    print(
        f"[PUMP_GUARD] Enriched {enriched_count}/{len(picks)} picks "
        f"({high_risk_count} high-risk flagged)"
    )
    return picks


# ============================================================================
# PART 6: Standalone Runner
# ============================================================================

def _print_library_summary(library: dict):
    """Print a human-readable summary of the pump pattern library."""
    print("\n" + "=" * 70)
    print("  PUMP PATTERN LIBRARY SUMMARY")
    print("=" * 70)

    # Source counts
    src = library.get("source_counts", {})
    print(f"\n  Data sources:")
    for table, count in src.items():
        print(f"    {table}: {count} records")

    # Grade distribution
    grades = library.get("grade_distribution", {})
    print(f"\n  Grade distribution (forensic scans):")
    for grade in ["VERY_HIGH", "HIGH", "MODERATE", "LOW"]:
        count = grades.get(grade, 0)
        bar = "#" * min(count, 40)
        print(f"    {grade:>10s}: {count:>3d} {bar}")

    # Top pump symbols
    known = library.get("known_pump_symbols", {})
    print(f"\n  Known pump symbols: {len(known)}")
    top = sorted(known.items(), key=lambda x: x[1].get("max_score", 0), reverse=True)[:15]
    for sym, stats in top:
        print(
            f"    {sym:>12s}: max_score={stats['max_score']:>2.0f}  "
            f"avg={stats['avg_score']:>4.1f}  "
            f"scans={stats['scan_count']}  "
            f"grades={','.join(stats.get('grades', []))}"
        )

    # Post-spike crash stats
    crash = library.get("post_spike_crash_stats", {})
    if crash:
        print(f"\n  Post-spike crash analysis ({crash.get('n_spikes', 0)} spikes):")
        print(f"    Avg spike size: {crash.get('avg_spike_pct', 0):.1f}%")
        print(f"    Avg post-3 candle: {crash.get('avg_post_3candle_pct', 0):+.2f}%")
        print(f"    Avg post-5 candle: {crash.get('avg_post_5candle_pct', 0):+.2f}%")
        print(f"    Avg post-10 candle: {crash.get('avg_post_10candle_pct', 0):+.2f}%")
        print(f"    % negative after 3 candles: {crash.get('pct_negative_post3', 0):.0f}%")

    # Fingerprints
    fp = library.get("fingerprints", {})
    if fp:
        print(f"\n  Pre-pump fingerprint (from {len(fp.get('pump_symbols', []))} symbols):")
        print(f"    Avg pump size: {fp.get('avg_pump_pct', 0):.1f}%")
        print(f"    Avg pre-RSI: {fp.get('avg_pre_rsi', 0):.1f}")
        print(f"    Avg pre-vol ratio: {fp.get('avg_pre_vol_ratio', 0):.2f}x")
        print(f"    % bearish EMA alignment: {fp.get('pct_bearish_ema', 0):.0f}%")
        print(f"    % near support: {fp.get('pct_near_support', 0):.0f}%")

    # Thresholds
    t = library.get("thresholds", {})
    print(f"\n  Detection thresholds:")
    print(f"    Price 1h warning/danger/extreme: "
          f"{t.get('price_change_1h_warning')}% / "
          f"{t.get('price_change_1h_danger')}% / "
          f"{t.get('price_change_1h_extreme')}%")
    print(f"    Volume warning/danger/extreme: "
          f"{t.get('volume_ratio_warning')}x / "
          f"{t.get('volume_ratio_danger')}x / "
          f"{t.get('volume_ratio_extreme')}x")
    print(f"    Block threshold: {t.get('high_grade_block_threshold')}")


def _live_scan_demo():
    """Run a live pump risk scan on a set of symbols."""
    symbols = [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "XRPUSDT",
        "SUIUSDT", "PEPEUSDT", "WIFUSDT", "BONKUSDT", "FLOKIUSDT",
    ]

    print("\n" + "=" * 70)
    print("  LIVE PUMP RISK SCAN")
    print("=" * 70)
    print(f"  Time: {datetime.now(timezone.utc).isoformat()}")
    print(f"  Symbols: {len(symbols)}")
    print()

    results = []
    for sym in symbols:
        rd = fetch_live_pump_risk(sym)
        results.append(rd)
        label = rd["risk_label"]
        marker = "!!!" if label in ("HIGH", "EXTREME") else "   "
        print(
            f"  {marker} {sym:>12s}  risk={rd['pump_risk_score']:.2f} [{label:>8s}]  "
            f"1h={rd['price_change_1h']:+6.1f}%  "
            f"vol={rd['volume_ratio']:5.1f}x  "
            f"RSI={rd.get('rsi') or 'N/A':>5}  "
            f"24h={rd['price_change_pct_24h']:+6.1f}%"
        )
        time.sleep(0.3)

    high_risk = [r for r in results if r["pump_risk_score"] >= 0.50]
    if high_risk:
        print(f"\n  WARNING: {len(high_risk)} symbols with elevated pump risk!")
        for r in high_risk:
            print(f"    {r['symbol']}: {r['pump_risk_score']:.2f} -- would be blocked/warned")
    else:
        print("\n  All symbols within normal risk levels.")


def main():
    """CLI entry point: build pattern library + run live scan demo."""
    print("=" * 70)
    print("  PUMP-AND-DUMP DETECTION GUARD")
    print(f"  Time: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)

    # Step 1: Parse SQL and build pattern library
    data = parse_pump_data()
    if any(len(v) > 0 for v in data.values()):
        library = build_pump_pattern_library(data)
        save_pump_patterns(library)
        _print_library_summary(library)
    else:
        print("[pump_guard] No SQL data found, using cached patterns")
        library = load_pump_patterns()
        if library.get("known_pump_symbols"):
            _print_library_summary(library)

    # Step 2: Live scan demo
    _live_scan_demo()

    # Step 3: Output JSON
    print("\n--- JSON OUTPUT (last scan) ---")
    scan_path = _DATA_DIR / "pump_scan_latest.json"
    scan_path.parent.mkdir(parents=True, exist_ok=True)
    # Re-scan with full output
    scan_results = {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "patterns_loaded": bool(library.get("known_pump_symbols")),
        "thresholds": library.get("thresholds", {}),
    }
    with open(scan_path, "w", encoding="utf-8") as f:
        json.dump(scan_results, f, indent=2)
    print(f"Scan output saved to {scan_path}")


if __name__ == "__main__":
    main()
