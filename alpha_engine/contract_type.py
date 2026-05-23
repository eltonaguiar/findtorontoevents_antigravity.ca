"""Contract-type classifier for trading symbols.

`audit_trail/dashboard_generator.py` routes `=F` symbols to asset-class tiles:
energy / metal / grain / soft futures land in COMMODITY, equity-index and
rates futures land in FUTURES. Grain/energy/metal volume therefore swamps the
COMMODITY tile while the FUTURES tile reads near-zero.

`classify_contract()` gives a finer `contract_type` label so picks can be
TAGGED without changing the existing COMMODITY/FUTURES `asset_class` routing —
a purely additive distinction (commodity_future vs index_future vs
rates_future vs currency_future, plus crypto/forex/equity).

Pure stdlib, import-safe, no side effects.
"""
from __future__ import annotations

# `=F` root sets — kept consistent with dashboard_generator.py's
# _COMMODITY_ROOTS / _INDEX_FUTURES_ROOTS groupings.
COMMODITY_FUTURE_ROOTS: frozenset[str] = frozenset({
    "CL", "BZ", "HO", "RB", "NG", "QM",          # energy
    "GC", "SI", "HG", "PL", "PA", "MGC", "SIL",  # metals
    "ZC", "ZW", "ZS", "ZM", "ZL", "ZO", "ZR",    # grains
    "CT", "KC", "SB", "CC", "OJ", "LBS",         # softs
    "LE", "HE", "GF",                            # livestock
})
INDEX_FUTURE_ROOTS: frozenset[str] = frozenset({
    "ES", "NQ", "YM", "RTY", "MES", "MNQ", "MYM", "M2K",
    "VX", "VXM", "DX",  # volatility + US dollar index
})
RATES_FUTURE_ROOTS: frozenset[str] = frozenset({
    "ZN", "ZB", "ZT", "ZF", "ZQ", "GE", "UB", "TN", "SR3",
})
CURRENCY_FUTURE_ROOTS: frozenset[str] = frozenset({
    "6E", "6B", "6J", "6A", "6C", "6S", "6N", "6M", "6L", "6R", "E7", "J7",
})

# Common crypto bases (for `<BASE>USDT`-style pairs without an exchange prefix).
_CRYPTO_BASES: frozenset[str] = frozenset({
    "BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "AVAX", "LINK", "MATIC",
    "POL", "DOT", "TRX", "LTC", "BCH", "ATOM", "UNI", "NEAR", "APT", "ARB",
    "OP", "SUI", "INJ", "TIA", "SEI", "RNDR", "RENDER", "HYPE", "PEPE", "WIF",
    "SHIB", "FIL", "ICP", "ETC", "XLM", "ALGO", "VET", "AAVE", "MKR", "GRT",
})
_EXCHANGE_PREFIXES: frozenset[str] = frozenset({
    "BINANCE", "COINBASE", "KUCOIN", "BYBIT", "OKX", "KRAKEN", "BITGET",
    "GATEIO", "MEXC", "CRYPTO", "BITSTAMP", "HUOBI",
})
_FIAT: frozenset[str] = frozenset({
    "USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "NZD", "CNH", "SEK",
})


def classify_contract(symbol: str) -> str:
    """Return the contract type of ``symbol``.

    One of: ``commodity_future``, ``index_future``, ``rates_future``,
    ``currency_future``, ``crypto``, ``forex``, ``equity``, ``unknown``.
    """
    if not symbol or not isinstance(symbol, str):
        return "unknown"
    s = symbol.strip()
    if not s:
        return "unknown"

    # strip an exchange prefix (BINANCE:BTCUSDT -> BTCUSDT); remember it
    prefix = ""
    if ":" in s:
        prefix, _, rest = s.partition(":")
        prefix = prefix.strip().upper()
        s = rest.strip()
        if prefix in _EXCHANGE_PREFIXES:
            return "crypto"

    up = s.upper()

    # futures: `<ROOT>=F`
    if up.endswith("=F"):
        root = up[:-2]
        if root in COMMODITY_FUTURE_ROOTS:
            return "commodity_future"
        if root in INDEX_FUTURE_ROOTS:
            return "index_future"
        if root in RATES_FUTURE_ROOTS:
            return "rates_future"
        if root in CURRENCY_FUTURE_ROOTS:
            return "currency_future"
        return "unknown"

    # forex: `EURUSD=X`, `EUR/USD`, or two fiat codes concatenated
    core = up[:-2] if up.endswith("=X") else up
    core_nosep = core.replace("/", "")
    if up.endswith("=X") or "/" in core:
        if len(core_nosep) == 6 and core_nosep[:3] in _FIAT and core_nosep[3:] in _FIAT:
            return "forex"
        return "forex" if up.endswith("=X") else "unknown"

    # crypto: `<BASE><QUOTE>` where quote is USDT/USDC/USD and base is known
    for quote in ("USDT", "USDC", "USD"):
        if up.endswith(quote) and len(up) > len(quote):
            base = up[: -len(quote)]
            if base in _CRYPTO_BASES:
                return "crypto"

    # plain alphanumeric ticker, no futures/fx/crypto markers -> equity
    if up.replace(".", "").replace("-", "").isalnum():
        return "equity"
    return "unknown"
