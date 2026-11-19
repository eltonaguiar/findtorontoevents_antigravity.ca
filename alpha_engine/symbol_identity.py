"""symbol_identity.py — one instrument, one key.

The closed ledger carries the same instrument under several vendor spellings:
`BTC-USD`, `BTCUSDT`, `BTC/USD` and `btc` are one thing; `EURUSD=X` and `EURUSD`
are one pair; `BRK-B` and `BRK.B` are one share class. When a scorer groups by
raw string it produces *separate cells with separate verdicts for the same
instrument* — on the 2026-11-19 ledger `BTC-USD LONG` (n=25) was KILL while
`BTCUSDT LONG` (n=120) was WEAK, and every major crypto LONG appeared killed
purely because the `-USD` spelling is what the older emitters stamped.

`canonical_symbol()` strips quote currency, vendor suffixes and separator
differences so grouping, scoring and denylisting all see one key.
"""
from __future__ import annotations

# Quote assets that turn a base symbol into a pair. Ordered longest-first so
# "USDT" wins over "USD".
_CRYPTO_QUOTES = ("FDUSD", "USDT", "USDC", "BUSD", "TUSD", "USD")

_CRYPTO_CLASSES = {"", "CRYPTO", "MEME", "PENNY_STOCK"}


def canonical_symbol(symbol: str | None, asset_class: str | None = None) -> str:
    """Return the canonical key for an instrument.

    ``asset_class`` narrows the rules: crypto stripping only applies to crypto
    classes (or when the class is unknown), so an equity ticker is never reduced
    to the part before a dash.
    """
    s = str(symbol or "").strip().upper()
    if not s:
        return ""
    s = s.replace("/", "").replace("_", "").replace(" ", "")

    # Vendor suffixes: EURUSD=X (forex), CL=F (futures).
    if s.endswith("=X") or s.endswith("=F"):
        s = s[:-2]

    ac = str(asset_class or "").upper()
    if ac in _CRYPTO_CLASSES:
        for quote in _CRYPTO_QUOTES:
            dash = f"-{quote}"
            if s.endswith(dash) and len(s) > len(dash):
                s = s[: -len(dash)]
                break
        else:
            for quote in _CRYPTO_QUOTES:
                if s.endswith(quote) and len(s) > len(quote):
                    s = s[: -len(quote)]
                    break

    # Share-class separator: BRK-B / BRK.B are the same line.
    if "-" in s and "." not in s and ac not in {"CRYPTO", "MEME"}:
        head, tail = s.split("-", 1)
        if 1 <= len(head) <= 5 and 1 <= len(tail) <= 2:
            s = f"{head}.{tail}"
    return s


def direction_key(direction: str | None) -> str:
    """Normalise BUY/SELL/L/S spellings onto LONG/SHORT."""
    d = str(direction or "").strip().upper()
    if d.startswith("B") or d.startswith("L"):
        return "LONG"
    if d.startswith("S"):
        return "SHORT"
    return d or "UNKNOWN"
