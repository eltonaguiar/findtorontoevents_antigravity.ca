"""
Centralized Asset Classification Module

Standardizes asset class detection (CRYPTO, FOREX, EQUITY, FUTURES, COMMODITY, MEME, ETF)
across the dashboard, metrics, scoring, and automated reporting systems.

This resolves the critical issue where "crypto-tuned" parameters were being applied
to all asset classes, causing non-crypto assets to lose money.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import re


class AssetClass(Enum):
    """Standardized asset type classifications."""
    CRYPTO = "CRYPTO"
    MEME = "MEME"
    FOREX = "FOREX"
    EQUITY = "EQUITY"
    ETF = "ETF"
    COMMODITY = "COMMODITY"
    FUTURES = "FUTURES"
    MICRO_FUTURES = "MICRO_FUTURES"
    BOND = "BOND"  # Fixed income (TLT,IEF,SHY,AGG,BND,LQD,HYG,JNK)
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class AssetConfig:
    """
    Configuration properties for each asset class.
    
    These values are used for TP/SL calculation, position sizing,
    risk management, and scoring weights.
    """
    # TP/SL defaults (as decimal percentages, e.g., 0.15 = 15%)
    default_tp_pct: float
    default_sl_pct: float
    
    # ATR multipliers for dynamic TP/SL
    atr_mult_tp: float
    atr_mult_sl: float
    
    # Risk parameters
    max_position_pct: float      # Max portfolio allocation
    volatility_factor: float     # Multiplier for volatility-based sizing
    min_risk_reward_ratio: float  # Minimum acceptable R:R
    max_sl_distance_pct: float   # Maximum SL distance from entry
    
    # Scoring weights (must sum to 1.0)
    momentum_weight: float
    trend_weight: float
    volume_weight: float
    
    # Display name
    display_name: str


# Default configurations per asset class
DEFAULT_CONFIGS: dict[AssetClass, AssetConfig] = {
    AssetClass.CRYPTO: AssetConfig(
        default_tp_pct=0.15,
        default_sl_pct=0.08,
        atr_mult_tp=2.5,
        atr_mult_sl=2.0,
        max_position_pct=0.15,
        volatility_factor=1.0,
        min_risk_reward_ratio=1.5,
        max_sl_distance_pct=0.15,
        momentum_weight=0.40,
        trend_weight=0.35,
        volume_weight=0.25,
        display_name="Cryptocurrency"
    ),
    AssetClass.MEME: AssetConfig(
        default_tp_pct=0.35,
        default_sl_pct=0.15,
        atr_mult_tp=3.0,
        atr_mult_sl=2.5,
        max_position_pct=0.08,
        volatility_factor=1.5,
        min_risk_reward_ratio=2.0,
        max_sl_distance_pct=0.25,
        momentum_weight=0.45,
        trend_weight=0.30,
        volume_weight=0.25,
        display_name="Meme Coin"
    ),
    AssetClass.FOREX: AssetConfig(
        default_tp_pct=0.003,  # 0.3%
        default_sl_pct=0.002,  # 0.2%
        atr_mult_tp=2.0,
        atr_mult_sl=1.5,
        max_position_pct=0.10,
        volatility_factor=0.5,
        min_risk_reward_ratio=1.5,
        max_sl_distance_pct=0.005,
        momentum_weight=0.30,
        trend_weight=0.45,
        volume_weight=0.25,
        display_name="Forex"
    ),
    AssetClass.EQUITY: AssetConfig(
        default_tp_pct=0.12,
        default_sl_pct=0.06,
        atr_mult_tp=2.5,
        atr_mult_sl=2.0,
        max_position_pct=0.10,
        volatility_factor=0.7,
        min_risk_reward_ratio=1.5,
        max_sl_distance_pct=0.10,
        momentum_weight=0.35,
        trend_weight=0.40,
        volume_weight=0.25,
        display_name="Equity/Stock"
    ),
    AssetClass.ETF: AssetConfig(
        default_tp_pct=0.08,
        default_sl_pct=0.04,
        atr_mult_tp=2.0,
        atr_mult_sl=1.5,
        max_position_pct=0.15,
        volatility_factor=0.4,
        min_risk_reward_ratio=1.5,
        max_sl_distance_pct=0.06,
        momentum_weight=0.30,
        trend_weight=0.45,
        volume_weight=0.25,
        display_name="ETF"
    ),
    AssetClass.COMMODITY: AssetConfig(
        default_tp_pct=0.10,
        default_sl_pct=0.06,
        atr_mult_tp=2.5,
        atr_mult_sl=2.0,
        max_position_pct=0.08,
        volatility_factor=0.8,
        min_risk_reward_ratio=1.5,
        max_sl_distance_pct=0.12,
        momentum_weight=0.35,
        trend_weight=0.40,
        volume_weight=0.25,
        display_name="Commodity"
    ),
    AssetClass.FUTURES: AssetConfig(
        default_tp_pct=0.08,
        default_sl_pct=0.05,
        atr_mult_tp=2.5,
        atr_mult_sl=2.0,
        max_position_pct=0.10,
        volatility_factor=0.9,
        min_risk_reward_ratio=1.5,
        max_sl_distance_pct=0.10,
        momentum_weight=0.35,
        trend_weight=0.40,
        volume_weight=0.25,
        display_name="Futures"
    ),
    AssetClass.MICRO_FUTURES: AssetConfig(
        default_tp_pct=0.08,
        default_sl_pct=0.05,
        atr_mult_tp=2.5,
        atr_mult_sl=2.0,
        max_position_pct=0.10,
        volatility_factor=0.9,
        min_risk_reward_ratio=1.5,
        max_sl_distance_pct=0.10,
        momentum_weight=0.35,
        trend_weight=0.40,
        volume_weight=0.25,
        display_name="Micro Futures"
    ),
    AssetClass.BOND: AssetConfig(
        default_tp_pct=0.04,
        default_sl_pct=0.02,
        atr_mult_tp=2.0,
        atr_mult_sl=1.5,
        max_position_pct=0.15,
        volatility_factor=0.3,
        min_risk_reward_ratio=1.5,
        max_sl_distance_pct=0.04,
        momentum_weight=0.25,
        trend_weight=0.50,
        volume_weight=0.25,
        display_name="Bond/Fixed Income"
    ),
    AssetClass.UNKNOWN: AssetConfig(
        default_tp_pct=0.10,
        default_sl_pct=0.08,
        atr_mult_tp=2.0,
        atr_mult_sl=2.0,
        max_position_pct=0.05,
        volatility_factor=1.0,
        min_risk_reward_ratio=1.5,
        max_sl_distance_pct=0.15,
        momentum_weight=0.33,
        trend_weight=0.34,
        volume_weight=0.33,
        display_name="Unknown"
    ),
}


# Pattern matchers for asset classification
_CRYPTO_PATTERNS = [
    r"^(BTC|ETH|BNB|XRP|ADA|SOL|DOGE|DOT|AVAX|MATIC|LINK|UNI|ATOM|LTC|ETC|XLM|ALGO|VET|THETA|AAVE|MKR|SNX|CRV|APE|SHIB|FLOW|CHZ|ENJ|MANA|SAND|AXS|GALA|IMX|LRC|ONE|STORJ|GLMR|REQ|ZEC|XMR|DASH|ZIL|ENS|GLXY|BTCZ|RARE|GTC|PERP|GNO|RAI)",
    r".*USDT$", r".*USDC$",
    r"^(BTC|ETH|BNB|XRP|ADA|SOL|DOGE|DOT|AVAX|MATIC|LINK|UNI|ATOM|LTC|TRX|NEAR|HBAR|TIA|ARB|JUP|STX|ENA|APT|SUI|SEI|FET|INJ|RENDER|WIF|BONK|PEPE|FLOKI|OP|FIL)[-/]USD$",
    r"BITGET:", r"BINANCE:", r"BYBIT:", r"OKX:", r"HYPERLIQUID:",
]
_MEME_PATTERNS = [
    r"^(PEPE|WIF|DOGE|SHIB|BONK|FLOKI|PEOPLE|WOO|MAGIC|GMEE|BIGTIME|high|GOAT|ACT|AI16Z|FARTCOIN)",
    r"MEME",
]
_FOREX_PATTERNS = [
    r"=X$",  # Yahoo finance forex suffix
    r"^(EURUSD|GBPUSD|USDJPY|AUDUSD|USDCAD|NZDUSD|USDCHF|EURJPY|GBPJPY|AUDJPY|EURGBP|CHFJPY|CADJPY|NZDJPY|EURCHF|AUDNZD|EURCAD|GBPAUD|GBPCAD|EURAUD|GBPNZD|EURNZD|USDSEK|USDNOK|USDDKK|USDCZK|USDHUF|USDPLN|USDRUB|USDTRY|USDZAR|USDMXN|USDBRL|USDCLP|USDCOP|USDARS|USDPEN|USDTRY|USDILS|USDKRW|USDTWD|USDSGD|USDMYR|USDTHB|USDVND|USDPHP|USDIDR|USDRMB)",
    r"^(EUR|GBP|USD|AUD|CAD|NZD|CHF|JPY)[-/](EUR|GBP|USD|AUD|CAD|NZD|CHF|JPY)$",
]
_EQUITY_PATTERNS = [
    r"^(AAPL|MSFT|GOOGL|AMZN|META|NVDA|TSLA|BRK|B|JPM|V|UNH|JNJ|WMT|MA|PG|HD|CV|XOM|ABBV|PFE|MRK|KO|PEP|COST|AVGO|TMO|ABT|LLY|MCD|DHR|NEE|FIS|QCOM|ACN|UPS|MS|WFC|CASY|MM)",
    r"\.TO$",  # Toronto stock exchange
    r"^(REIT|CLOU|ARKK|ARKG|SQQQ|TQQQ|SPY|QQQ|IWM|DIA|SDS|SSO|TLT|GLD|SLV|IGC|SPA)",
]
_ETF_PATTERNS = [
    r"^(SPY|QQQ|IWM|DIA|SDS|SSO|TLT|GLD|SLV|IGC|SPA|XLF|XLE|XLV|XLI|XLC|XLP|XLY|XLC)",
    r"^(VTI|VGT|VOO|IVV|VEA|VWO|VIG|VYM|BND|AGG|JPGL|QQQM|SPYV|ESGU|IEFA|IE00)",
]
_COMMODITY_PATTERNS = [
    r"^(GC=F|SI=F|CL=F|NG=F|HG=F|PL=F|PA=F|ZC=F|ZS=F|ZW=F|KE=F|KC=F|SB=F|CC=F|CT=F|OJ=F|ZL=F|ZM=F|LE=F|HE=F|FC=F|DC=F)",
    r"^(XAUUSD|XAGUSD|XPTUSD|XPDUSD)",
]
_FUTURES_PATTERNS = [
    r"=F$",  # yfinance futures suffix
    r"^(MES|MNQ|MYM|M2K|MGC|MSI|MQM|MZN|MZT|MZF|MZB|M6E|M6J|M6B|M6S|M6A|M6C|M6N|MZC|MZS|MZW|MKE|MHE|MLE|MFC)",
]
_BOND_PATTERNS = [
    r"^(TLT|IEF|SHY|AGG|BND|LQD|HYG|JNK|SHYG|IG|LQD|VCSH|VCIT|VGIT|VGLT|BSV|BIV|BLV|SCHZ|AGG|SPAB|SCHB|ITOT|ijh|VTI)",
    r"^(TLT|IEF|SHY|AGG|BND|LQD|HYG|JNK).*US",
]


def _compile_patterns(patterns: list[str]) -> re.Pattern:
    """Compile a list of regex patterns into a single pattern."""
    combined = "|".join(f"({p})" for p in patterns)
    return re.compile(combined, re.IGNORECASE)


_CRYPTO_RE = _compile_patterns(_CRYPTO_PATTERNS)
_MEME_RE = _compile_patterns(_MEME_PATTERNS)
_FOREX_RE = _compile_patterns(_FOREX_PATTERNS)
_EQUITY_RE = _compile_patterns(_EQUITY_PATTERNS)
_ETF_RE = _compile_patterns(_ETF_PATTERNS)
_COMMODITY_RE = _compile_patterns(_COMMODITY_PATTERNS)
_FUTURES_RE = _compile_patterns(_FUTURES_PATTERNS)
_BOND_RE = _compile_patterns(_BOND_PATTERNS)


class AssetClassifier:
    """
    Main classifier for determining asset class from symbols and metadata.
    
    Uses pattern matching (regex, lists, and string prefixes) to determine
    the asset class based on symbols and optional metadata.
    """
    
    def __init__(self):
        self._configs = dict(DEFAULT_CONFIGS)
    
    def classify(
        self,
        symbol: str,
        category: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> AssetClass:
        """
        Classify a symbol into an asset class.
        
        Args:
            symbol: The trading symbol (e.g., "BTCUSDT", "EURUSD=X", "AAPL")
            category: Optional explicit category from the data source
            metadata: Optional additional metadata (e.g., {"cat": "crypto"})
        
        Returns:
            The classified AssetClass
        
        Priority order:
        1. Explicit category from metadata
        2. Symbol pattern matching
        3. Default to UNKNOWN
        """
        sym = (symbol or "").upper().strip()
        # Normalize noisy coin IDs like ARB11841-USD -> ARB-USD.
        sym = re.sub(r"^([A-Z]+)\d+([-/]USD)$", r"\1\2", sym)
        
        # Priority 1: Check explicit category from metadata
        if category:
            cat_upper = category.upper()
            if cat_upper in ("CRYPTO", "Crypto"):
                return AssetClass.CRYPTO
            elif cat_upper in ("MEME", "Meme"):
                return AssetClass.MEME
            elif cat_upper in ("FOREX", "Forex", "FX"):
                return AssetClass.FOREX
            elif cat_upper in ("EQUITY", "Equity", "STOCK", "Stock"):
                return AssetClass.EQUITY
            elif cat_upper in ("ETF", "Etf"):
                return AssetClass.ETF
            elif cat_upper in ("COMMODITY", "Commodity", "CMD"):
                return AssetClass.COMMODITY
            elif cat_upper in ("FUTURES", "Futures", "FUT"):
                return AssetClass.FUTURES
            elif cat_upper in ("BOND", "Bond", "FIXED_INCOME", "FIXEDINCOME"):
                return AssetClass.BOND
            elif cat_upper in ("MICRO_FUTURES", "MICROFUTURES"):
                return AssetClass.MICRO_FUTURES
        
        # Priority 2: Check metadata dict if provided
        if metadata:
            meta_cat = metadata.get("cat") or metadata.get("category")
            if meta_cat:
                result = self.classify(symbol, category=meta_cat)
                if result != AssetClass.UNKNOWN:
                    return result
        
        # Priority 3: Pattern matching
        # Order matters: check more specific patterns first
        
        # Check MEME first (subset of crypto)
        if _MEME_RE.search(sym):
            return AssetClass.MEME
        
        # Check CRYPTO
        if _CRYPTO_RE.search(sym):
            return AssetClass.CRYPTO
        
        # Check FUTURES (before forex due to =F suffix)
        if _FUTURES_RE.search(sym):
            return AssetClass.FUTURES
        
        # Check FOREX (=X suffix or major pairs)
        if _FOREX_RE.search(sym):
            return AssetClass.FOREX
        
        # Check ETF (before equity, more specific)
        if _ETF_RE.search(sym):
            return AssetClass.ETF
        
        # Check COMMODITY
        if _COMMODITY_RE.search(sym):
            return AssetClass.COMMODITY
        
        # Check BOND (before equity due to potential overlap)
        if _BOND_RE.search(sym):
            return AssetClass.BOND
        
        # Check EQUITY
        if _EQUITY_RE.search(sym):
            return AssetClass.EQUITY
        
        # Fallback
        return AssetClass.UNKNOWN
    
    def get_config(self, asset_class: AssetClass) -> AssetConfig:
        """Get the configuration for a specific asset class."""
        return self._configs.get(asset_class, DEFAULT_CONFIGS[AssetClass.UNKNOWN])
    
    def normalize_asset_class(self, asset_class_str: str) -> AssetClass:
        """
        Normalize a string representation to an AssetClass enum.
        
        Handles various input formats like "crypto", "CRYPTO", "Crypto", etc.
        """
        if not asset_class_str:
            return AssetClass.UNKNOWN
        
        normalized = asset_class_str.upper().strip()
        
        # Direct enum match
        try:
            return AssetClass(normalized)
        except ValueError:
            pass
        
        # Alias mapping
        aliases = {
            "CRYPTO": AssetClass.CRYPTO,
            "CRYPTOGRAPHIC": AssetClass.CRYPTO,
            "BTC": AssetClass.CRYPTO,
            "ETH": AssetClass.CRYPTO,
            "MEME": AssetClass.MEME,
            "MEMECOIN": AssetClass.MEME,
            "FOREX": AssetClass.FOREX,
            "FX": AssetClass.FOREX,
            "CURRENCY": AssetClass.FOREX,
            "EQUITY": AssetClass.EQUITY,
            "STOCK": AssetClass.EQUITY,
            "SHARE": AssetClass.EQUITY,
            "ETF": AssetClass.ETF,
            "EXCHANGE_TRADED": AssetClass.ETF,
            "COMMODITY": AssetClass.COMMODITY,
            "CMD": AssetClass.COMMODITY,
            "FUTURES": AssetClass.FUTURES,
            "FUT": AssetClass.FUTURES,
            "DERIVATIVE": AssetClass.FUTURES,
            "MICRO_FUTURES": AssetClass.MICRO_FUTURES,
            "MICROFUTURES": AssetClass.MICRO_FUTURES,
            "MES": AssetClass.MICRO_FUTURES,
            "MNQ": AssetClass.MICRO_FUTURES,
            "BOND": AssetClass.BOND,
            "FIXED_INCOME": AssetClass.BOND,
            "TREASURY": AssetClass.BOND,
        }
        
        return aliases.get(normalized, AssetClass.UNKNOWN)


# Global singleton instance
_classifier: Optional[AssetClassifier] = None


def get_classifier() -> AssetClassifier:
    """Get the global AssetClassifier singleton instance."""
    global _classifier
    if _classifier is None:
        _classifier = AssetClassifier()
    return _classifier


# Convenience functions
def classify_asset(
    symbol: str,
    category: Optional[str] = None,
    metadata: Optional[dict] = None
) -> AssetClass:
    """Convenience function to classify a symbol."""
    return get_classifier().classify(symbol, category, metadata)


def get_asset_config(asset_class: AssetClass) -> AssetConfig:
    """Convenience function to get asset configuration."""
    return get_classifier().get_config(asset_class)


def normalize_asset_class(asset_class_str: str) -> AssetClass:
    """Convenience function to normalize an asset class string."""
    return get_classifier().normalize_asset_class(asset_class_str)


# Backward compatibility: expose key functions for existing code
# ============================================================================
# BACKWARD COMPATIBILITY: Keep old API for existing code
# ============================================================================

# Forward declare ResolveResult for use in classify_symbol
@dataclass(frozen=True)
class ResolveResult:
    """Backward compatibility result class."""
    asset_class: str
    reason: str


def is_crypto(symbol: str) -> bool:
    """Check if symbol is crypto."""
    return classify_asset(symbol) == AssetClass.CRYPTO


def is_meme(symbol: str) -> bool:
    """Check if symbol is a meme coin."""
    return classify_asset(symbol) == AssetClass.MEME


def is_forex(symbol: str) -> bool:
    """Check if symbol is forex."""
    return classify_asset(symbol) == AssetClass.FOREX


def is_equity(symbol: str) -> bool:
    """Check if symbol is equity."""
    return classify_asset(symbol) == AssetClass.EQUITY


def is_commodity(symbol: str) -> bool:
    """Check if symbol is a commodity."""
    return classify_asset(symbol) == AssetClass.COMMODITY


def is_futures(symbol: str) -> bool:
    """Check if symbol is a futures contract."""
    return classify_asset(symbol) == AssetClass.FUTURES


def is_etf(symbol: str) -> bool:
    """Check if symbol is an ETF."""
    return classify_asset(symbol) == AssetClass.ETF


# ============================================================================
# CRYPTO SYMBOL GUARD — defends against the resolver-step7 BOND dispatch bug
# (2026-05-19): 500 rows in at_raw_picks were tagged asset_class='BOND' but
# carried crypto memecoin symbols (PEPEUSDT/WIFUSDT/BONKUSDT/DOGEUSDT/
# SHIBUSDT/FLOKIUSDT). The orphan-emitter normalization in
# dashboard_generator.py stamped BOND from the bond_picks.json filename
# without any symbol-vs-class consistency check. resolve_asset_class()
# trusted the upstream tag.
# ============================================================================

# Stablecoin/crypto pair suffixes — unambiguous crypto markers.
_CRYPTO_PAIR_SUFFIXES = ("USDT", "USDC", "BUSD", "DAI", "TUSD", "USDP")

# Known meme + major crypto bases (bare symbol or BASE-USD form).
_CRYPTO_KNOWN_BASES = frozenset({
    "PEPE", "WIF", "BONK", "DOGE", "SHIB", "FLOKI", "TURBO", "BRETT",
    "NEIRO", "POPCAT", "MOG", "BOME", "SLERF", "PONKE", "SATS", "ORDI",
    "BTC", "ETH", "SOL", "XRP", "ADA", "BNB", "AVAX", "DOT", "MATIC",
    "LINK", "UNI", "AAVE", "NEAR", "SUI", "FIL", "INJ", "TON", "SEI",
    "TIA", "RENDER", "FET", "AR", "OP", "ARB", "APT", "ATOM", "ALGO",
    "ICP", "HBAR", "VET", "FTM", "CRV", "LTC", "BCH", "ETC", "TRX",
})

# Forex base codes used to exclude rare cross-pair confusions (e.g. EURUSDT).
_FX_BASE_CODES = frozenset({"EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD"})


def is_obviously_crypto_symbol(symbol) -> bool:
    """Return True when the symbol is unambiguously a crypto pair or known
    crypto base. Defensive helper: NO classifier path should ever assign
    BOND/ETF/EQUITY/FOREX/COMMODITY to a symbol that matches this. Mirrors
    the Bug-2 fail-loud intent of resolver-step7.
    """
    if not symbol:
        return False
    s = str(symbol).upper().strip().replace("-", "").replace("/", "").replace("_", "")
    if any(s.endswith(sfx) for sfx in _CRYPTO_PAIR_SUFFIXES):
        # Exclude forex-base + stablecoin (rare cross-pairs).
        if s[:3] in _FX_BASE_CODES and len(s) <= 7:
            return False
        return True
    if s in _CRYPTO_KNOWN_BASES:
        return True
    for base in _CRYPTO_KNOWN_BASES:
        if s.startswith(base) and s[len(base):] in ("", "USD"):
            return True
    return False


# ============================================================================
# BACKWARD COMPATIBILITY: Keep old API for existing code
# ============================================================================

# The old module exported these functions - provide aliases for compatibility
def resolve_asset_class(
    symbol: str,
    raw: Optional[dict] = None,
    source_system: str = "",
    strategy: str = "",
) -> str:
    """
    Backward compatibility function.

    Resolves asset class from symbol and optional metadata.
    """
    if raw is None:
        raw = {}

    sym_upper = str(symbol or "").upper().strip()

    # 2026-05-19 defensive guard (resolver-step7 BOND dispatch bug): obviously
    # crypto symbols can NEVER be BOND/ETF/EQUITY/FOREX/COMMODITY. Refuses any
    # upstream `asset_class=BOND` tag on PEPEUSDT-style symbols at the source.
    if is_obviously_crypto_symbol(sym_upper):
        return AssetClass.CRYPTO.value

    # Suffix override: a yfinance "=F"/"=X" symbol suffix is unambiguous and
    # must beat any conflicting category hint (e.g. prevents NG=F -> FOREX).
    if sym_upper.endswith("=F"):
        return AssetClass.FUTURES.value
    if sym_upper.endswith("=X"):
        return AssetClass.FOREX.value

    # Check explicit category from raw dict
    for key in ("asset_class", "assetClass", "category", "asset_category", "asset_type"):
        if key in raw and raw[key]:
            result = normalize_asset_class(str(raw[key]))
            if result != AssetClass.UNKNOWN:
                return result.value
    
    # Check hint text from raw
    hint_text = " ".join(
        str(raw.get(k, "") or "")
        for k in ("source", "source_system", "name", "instrument_type", "market")
    )
    if hint_text:
        result = classify_asset(symbol, metadata={"cat": hint_text})
        if result != AssetClass.UNKNOWN:
            return result.value
    
    # Default to classification
    result = classify_asset(symbol)
    return result.value


def classify_symbol(
    symbol: str,
    source_system: str = "",
    strategy: str = "",
    hint: str = "",
) -> 'ResolveResult':
    """
    Backward compatibility function.
    
    Classifies symbol and returns a ResolveResult-like object.
    """
    result = classify_asset(symbol)
    return ResolveResult(
        asset_class=result.value,
        reason="classify_asset"
    )


# For backward compatibility - set of valid asset classes
ASSET_CLASSES = {
    "CRYPTO", "FOREX", "EQUITY", "ETF", "FUTURES", "COMMODITY", "BOND", "UNKNOWN"
}


# ============================================================================
# WRITE-TIME SYMBOL CANONICALIZATION
# ============================================================================
# Canonical symbol form (matches the one-time at_raw_picks normalization):
#   FOREX   -> yfinance-suffixed pair, e.g. EURUSD=X
#   FUTURES -> yfinance-suffixed root, e.g. NG=F
# All other classes (CRYPTO/EQUITY/ETF/COMMODITY/BOND/MEME/...) are left as-is.
# This prevents new MySQL inserts from re-introducing the EURUSD vs EURUSD=X split.

# 6-letter FX currency-pair currency codes (mirrors sync_all_picks_to_mysql._FOREX_PREFIXES).
_CANON_FOREX_CCYS = {"EUR", "GBP", "USD", "JPY", "AUD", "CAD", "CHF", "NZD"}


def canonicalize_symbol(symbol: Optional[str], asset_class: Optional[str]) -> Optional[str]:
    """
    Return the canonical write-time symbol form for the given asset class.

    - FOREX: a bare 6-letter FX pair (e.g. EURUSD) gets the yfinance "=X" suffix.
    - FUTURES: a symbol missing the yfinance "=F" suffix gets it appended.
    - CRYPTO / EQUITY / ETF / COMMODITY / BOND / MEME / UNKNOWN: returned unchanged.

    Never double-suffixes; handles None/empty input safely.
    """
    if not symbol:
        return symbol
    sym = str(symbol).strip()
    if not sym:
        return symbol
    ac = str(asset_class or "").upper().strip()

    if ac == "FOREX":
        if sym.upper().endswith("=X"):
            return sym
        # Already a futures/other suffixed symbol -> leave alone.
        if "=" in sym:
            return sym
        bare = sym.upper()
        if (len(bare) == 6 and bare[:3] in _CANON_FOREX_CCYS
                and bare[3:] in _CANON_FOREX_CCYS):
            return bare + "=X"
        return sym

    if ac in ("FUTURES", "MICRO_FUTURES"):
        if sym.upper().endswith("=F"):
            return sym
        if "=" in sym:
            return sym
        return sym.upper() + "=F"

    return sym
