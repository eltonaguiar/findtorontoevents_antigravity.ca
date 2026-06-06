"""Canonical asset-class normalization — single source of truth.

Consolidates duplicated logic from smart_picks_engine._normalized_asset_class,
conviction_stack._is_crypto_pick, and conviction_stack._norm_sym into one module.

Usage:
    from alpha_engine.asset_class import (
        normalize_asset_class, classify_pick_asset_class_upper,
        is_crypto, is_non_crypto,
        asset_class_from_symbol, normalize_symbol,
        FOREX_CODES, BOND_SYMBOLS, ETF_SYMBOLS, EQUITY_SYMBOLS,
        COMMODITY_SYMBOLS,
        CRYPTO_SOURCE_HINTS, CRYPTO_STRATEGY_HINTS,
    )
"""
from __future__ import annotations

from typing import Any

# ── Constants ────────────────────────────────────────────────────────────────

FOREX_CODES: frozenset[str] = frozenset({
    "EUR", "GBP", "USD", "JPY", "AUD", "CAD", "CHF", "NZD",
    "SEK", "NOK", "DKK", "SGD", "HKD", "CNH", "CNY", "MXN",
    "ZAR", "TRY", "INR",
})

BOND_SYMBOLS: frozenset[str] = frozenset({
    # Core rates / investment grade (2→14 expansion 2026-05-17)
    "TLT", "IEF", "SHY", "LQD", "AGG", "BND",
    # High yield / credit
    "HYG", "JNK", "SJNK", "BKLN",
    # Specialty: EM, TIPS, munis, IG intermediate
    "EMB", "TIP", "MUB", "IGIB",
})

ETF_SYMBOLS: frozenset[str] = frozenset({
    # Broad market & core
    "SPY", "QQQ", "IWM", "DIA", "VTI", "VOO",
    # Sector SPDRs (all 11)
    "XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP",
    "XLRE", "XLV", "XLY", "XLU",
    # Thematic / innovation
    "ARKK", "XBI", "SMH", "SOXX", "XHB", "IBB", "XRT", "XOP", "XME",
    # International / EM
    "EFA", "EEM",
    # Real estate / alternatives
    "VNQ", "GLD", "SLV", "USO",
    # Leveraged / inverse
    "SQQQ", "TQQQ", "UVXY",
    # NOTE: TLT, IEF, and other bond ETFs are in BOND_SYMBOLS above
    # (bond ETFs, not equity ETFs — checked before this frozenset)
})

EQUITY_SYMBOLS: frozenset[str] = frozenset({
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "TSLA", "META", "NVDA", "AMD",
    "NFLX", "DIS", "BA", "JPM", "GS", "V", "MA", "PYPL", "SQ", "COIN",
    "MSTR", "RIOT", "MARA", "HUT", "BITF", "BAC", "COST", "PFE", "JNJ",
    "ABBV", "AVGO", "HD", "LLY", "TMO", "ORCL", "LCID",
})

COMMODITY_SYMBOLS: frozenset[str] = frozenset({
    # Precious / industrial metals (yfinance roots and spot tickers)
    "GC", "SI", "HG", "PL", "PA", "ALI",
    # Energy / ag roots commonly emitted without =F suffix
    "CL", "NG", "HO", "RB", "ZC", "ZS", "ZW", "KC", "SB", "CC", "CT",
    # Spot metal pairs
    "XAUUSD", "XAGUSD", "XPTUSD", "XPDUSD",
})

CRYPTO_SOURCE_HINTS: tuple[str, ...] = (
    "claude_gainer", "copy_trader", "coinglass", "crypto", "binance", "bybit",
    "hyperliquid", "okx", "gmx", "drift", "dex", "dune", "copin", "onchain",
)

CRYPTO_STRATEGY_HINTS: tuple[str, ...] = (
    "copy_hl_", "ct_consensus_", "cg_whale", "funding", "skyrocket", "onchain",
)

COMMODITY_STRATEGY_HINTS: tuple[str, ...] = (
    "commodity", "metals", "metal", "palladium", "platinum", "gold", "silver",
    "crude", "grain", "cot_", "cta_", "commod",
)

EQUITY_STRATEGY_HINTS: tuple[str, ...] = (
    "equity", "vt_equity", "momentum_rider", "dividend", "earnings", "sector",
    "analyst", "penny", "stock", "stocks",
)

FOREX_STRATEGY_HINTS: tuple[str, ...] = (
    "forex", "fx_", "carry_trade", "oanda", "myfxbook",
)

# Stablecoin suffixes that unambiguously indicate crypto pairs
_CRYPTO_SUFFIXES: tuple[str, ...] = ("USDT", "BUSD", "USDC", "DAI", "TUSD", "USDP")

_UNKNOWN_CATEGORY_TOKENS: frozenset[str] = frozenset({
    "", "unknown", "none", "null", "nan",
})

# Categories that map to each canonical class
_CAT_MAP: dict[str, str] = {
    "crypto": "crypto", "meme": "crypto",
    "forex": "forex", "fx": "forex",
    "etf": "etf",
    "bond": "bond",
    "commodity": "commodity", "futures": "futures",
    "equity": "equity", "stock": "equity", "stocks": "equity", "penny": "equity",
}

_LOWER_TO_UPPER: dict[str, str] = {
    "crypto": "CRYPTO",
    "forex": "FOREX",
    "equity": "EQUITY",
    "etf": "ETF",
    "bond": "BOND",
    "futures": "FUTURES",
    "commodity": "COMMODITY",
    "unknown": "UNKNOWN",
}

# ── Public API ───────────────────────────────────────────────────────────────


def normalize_symbol(symbol: str | None) -> str:
    """Uppercase and strip common separators (-, /, _)."""
    return (symbol or "").upper().replace("-", "").replace("_", "").replace("/", "")


def asset_class_from_symbol(symbol: str | None) -> str:
    """Determine asset class from symbol alone (no pick dict required).

    Returns one of: crypto, forex, futures, bond, etf, equity, unknown.
    """
    sym = normalize_symbol(symbol)

    # ── Futures suffix (=F) ──
    if sym.endswith("=F"):
        return "futures"

    # ── Forex suffix (=X) ──
    if sym.endswith("=X"):
        return "forex"

    # Strip suffix for further checks
    sym_core = sym[:-2] if sym.endswith(("=X", "=F")) else sym

    # ── Stablecoin suffixes → crypto ──
    if sym_core.endswith(_CRYPTO_SUFFIXES):
        return "crypto"

    # ── 6-char forex pair (e.g. EURUSD) ──
    if len(sym_core) == 6:
        base, quote = sym_core[:3], sym_core[3:]
        if base in FOREX_CODES and quote in FOREX_CODES:
            return "forex"

    # ── Known bond symbols (checked before ETF — bond ETFs like TLT/IEF are bonds, not equity ETFs) ──
    if sym_core in BOND_SYMBOLS:
        return "bond"

    # ── Known ETF symbols ──
    if sym_core in ETF_SYMBOLS:
        return "etf"

    # ── Known commodity symbols ──
    if sym_core in COMMODITY_SYMBOLS:
        return "commodity"

    # ── Known equity symbols ──
    if sym_core in EQUITY_SYMBOLS:
        return "equity"

    return "unknown"


def _strategy_hint_class(strategy: str, source: str) -> str | None:
    """Infer asset class from strategy/source naming when symbol is ambiguous."""
    blob = f"{strategy} {source}".strip().lower()
    if not blob:
        return None
    if any(tag in blob for tag in COMMODITY_STRATEGY_HINTS):
        return "commodity"
    if any(tag in blob for tag in FOREX_STRATEGY_HINTS):
        return "forex"
    if any(tag in blob for tag in EQUITY_STRATEGY_HINTS):
        return "equity"
    return None


def normalize_asset_class(pick: dict[str, Any]) -> str:
    """Full asset-class normalization from a pick dict.

    Checks (in priority order):
      1. Symbol suffix  (=F → futures, =X → forex)
      2. Stablecoin suffix  (USDT/USDC/BUSD → crypto)
      3. 6-char forex pair detection
      4. Category / asset_class field mapping  (explicit metadata — beats guessing)
      5. Source-system and strategy hints → crypto
      6. Known-symbol frozensets  (bond → ETF → equity, fallback when no category)
      7. Default fallback → equity

    Returns: crypto | equity | forex | etf | bond | futures | commodity | unknown
    """
    # ── Field extraction ──
    raw_cat = str(pick.get("category") or pick.get("asset_class") or "").strip().lower()
    if raw_cat in _UNKNOWN_CATEGORY_TOKENS:
        raw_cat = ""
    strategy = str(pick.get("strategy") or "").lower()
    source = str(pick.get("source_system") or pick.get("source") or "").lower()
    sym = normalize_symbol(pick.get("symbol"))

    # ── Unambiguous symbol suffixes (=F → futures, =X → forex) — always trusted ──
    if sym.endswith("=F"):
        return "futures"
    if sym.endswith("=X"):
        return "forex"

    # Strip suffix for further checks
    sym_core = sym[:-2] if sym.endswith(("=X", "=F")) else sym

    # ── Stablecoin suffixes → crypto (unambiguous) ──
    if sym_core.endswith(_CRYPTO_SUFFIXES):
        return "crypto"

    # ── 6-char forex pair detection (high confidence) ──
    if len(sym_core) == 6:
        base, quote = sym_core[:3], sym_core[3:]
        if base in FOREX_CODES and quote in FOREX_CODES:
            return "forex"

    # ── Category / asset_class field (explicit metadata — beats symbol guessing) ──
    # Non-crypto strategies set category="bond"/"etf"/"futures"/"commodity" etc.
    # This must come BEFORE known-symbol frozensets so bond ETFs like IEF/TLT
    # classify as "bond" (not "etf") when the strategy says they're bonds.
    if raw_cat in _CAT_MAP:
        return _CAT_MAP[raw_cat]

    # ── Source/strategy crypto hints ──
    if any(tag in source for tag in CRYPTO_SOURCE_HINTS):
        return "crypto"
    if any(tag in strategy for tag in CRYPTO_STRATEGY_HINTS):
        return "crypto"

    # ── Known-symbol frozensets (fallback when no category set) ──
    if sym_core in BOND_SYMBOLS:
        return "bond"
    if sym_core in COMMODITY_SYMBOLS:
        return "commodity"
    if sym_core in ETF_SYMBOLS:
        return "etf"
    if sym_core in EQUITY_SYMBOLS:
        return "equity"

    hinted = _strategy_hint_class(strategy, source)
    if hinted:
        return hinted

    # ── Default fallback ──
    return "equity"


def classify_pick_asset_class_upper(pick: dict[str, Any]) -> str:
    """Return uppercase canonical asset class for registry/dashboard surfaces."""
    lowered = normalize_asset_class(pick if isinstance(pick, dict) else {})
    return _LOWER_TO_UPPER.get(lowered, lowered.upper())


def is_crypto(pick: dict[str, Any]) -> bool:
    """Return True if pick is a crypto asset."""
    return normalize_asset_class(pick) == "crypto"


def is_non_crypto(pick: dict[str, Any]) -> bool:
    """Return True if pick is NOT crypto (forex/equity/ETF/futures/bond)."""
    return normalize_asset_class(pick) != "crypto"


# ── CRYPTO liquidity gate (ADV) ────────────────────────────────────────────
# Screens out illiquid / penny / meme coins from CRYPTO picks.
# Uses CoinGecko free /coins/markets endpoint; cached hourly in
# alpha_engine/data/coingecko_adv_cache.json. Fail-open (returns True) if
# CoinGecko is unreachable or symbol not found in snapshot.
#
# Min ADV thresholds sourced from supplement doc asset_class_data_supplements:
#   MAJOR (BTC/ETH/…):     >= $500M USD 24h volume
#   ALTCOIN:               >= $50M  USD 24h volume
#   Below threshold:       not liquid enough for production picks

import json as _json
import time as _time
from pathlib import Path as _Path

_COINGECKO_CACHE_PATH = _Path(__file__).resolve().parent / "data" / "coingecko_adv_cache.json"
_COINGECKO_CACHE_TTL_SECONDS = 3600  # 1 hour
_ADV_THRESHOLD_USD = 50_000_000      # $50M 24h volume minimum for ALTCOIN
_ADV_MAJOR_SYMBOLS = frozenset({"BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"})
_ADV_MAJOR_THRESHOLD_USD = 500_000_000  # $500M for majors


def _load_coingecko_adv_cache() -> dict:
    """Load cached CoinGecko 24h volume data. Returns {} on any error."""
    try:
        if not _COINGECKO_CACHE_PATH.exists():
            return {}
        data = _json.loads(_COINGECKO_CACHE_PATH.read_text(encoding="utf-8"))
        cache_age = _time.time() - float(data.get("_fetched_at", 0))
        if cache_age > _COINGECKO_CACHE_TTL_SECONDS * 2:
            return {}  # too stale to trust
        return data
    except Exception:
        return {}


def is_liquid_crypto(symbol: str | None) -> bool:
    """Return True if a CRYPTO symbol has sufficient 24h ADV (fail-open on missing data).

    Gate: 24h USD volume >= $50M for altcoins, >= $500M for BTC/ETH majors.
    Uses alpha_engine/data/coingecko_adv_cache.json (updated hourly by
    tools/coingecko_adv_fetcher.py or the production scanner warm-up path).

    Fail-open: returns True (passes the gate) when:
    - Symbol not in cache (unlisted or cache miss)
    - Cache file missing or unreadable
    - CoinGecko data unavailable
    """
    if not symbol:
        return True  # fail-open
    sym = str(symbol).upper().strip()
    cache = _load_coingecko_adv_cache()
    if not cache:
        return True  # fail-open: no cache available
    adv_map: dict = cache.get("adv_by_symbol", {})
    if sym not in adv_map:
        return True  # fail-open: symbol not in snapshot
    adv_usd = float(adv_map[sym])
    threshold = _ADV_MAJOR_THRESHOLD_USD if sym in _ADV_MAJOR_SYMBOLS else _ADV_THRESHOLD_USD
    return adv_usd >= threshold
