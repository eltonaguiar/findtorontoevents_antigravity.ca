"""
delisted_symbols.py — Shared blocklist of delisted / renamed equity tickers.

These tickers break yfinance batch downloads (they return all-NaN columns,
trigger "possibly delisted; no price data found" warnings, and waste API
calls). Scanner seed/watchlist lists should be filtered through
`filter_delisted()` before being passed to `yfinance.download()`.

Maintenance: add a ticker here when yfinance starts returning empty data for
it. Each entry carries a short reason + the year it left the tape so a future
maintainer can re-validate. Renamed tickers list their successor.
"""

from __future__ import annotations

# Symbol -> reason. Confirmed delisted, bankrupt, or renamed as of 2026-05.
DELISTED_SYMBOLS: dict[str, str] = {
    "NKLA": "Nikola Corp — Chapter 11 bankruptcy, delisted 2025",
    "SQ": "Block Inc — renamed/reticker'd to XYZ in 2025; SQ no longer trades",
    "SURF": "Surface Oncology — merged into Coherus (CHRS) 2023",
    "FFIE": "Faraday Future — reverse-split / delisted from Nasdaq",
    "MMAT": "Meta Materials — Chapter 7 bankruptcy 2023",
    "NAKD": "Naked Brand — renamed Cenntro Electric (CENN) 2021",
    "AGTC": "Applied Genetic Tech — acquired by Syncona 2022",
    "BBIG": "Vinco Ventures — delisted from Nasdaq",
    "RDBX": "Redbox — Chicken Soup bankruptcy, delisted 2024",
    "SPRT": "Support.com — merged into Greenidge (GREE) 2021",
    "IRNT": "IronNet — Chapter 11 bankruptcy 2023, delisted",
    "ESSC": "East Stone Acquisition — SPAC liquidated/delisted",
    "PRTY": "Party City — Chapter 11 bankruptcy, delisted 2023",
    "GNUS": "Genius Brands — renamed Kartoon Studios (TOON) 2022",
    "WKHS": "Workhorse — reverse-split; legacy WKHS data unreliable",
    "EXPR": "Express Inc — Chapter 11 bankruptcy 2024, delisted",
    "CIDM": "Cinedigm — delisted; ticker stale",
    "ABIO": "ARCA biopharma — merged into Oruka (ORKA) 2024",
}


def is_delisted(symbol: str) -> bool:
    """True if `symbol` is a known delisted/renamed ticker (case-insensitive)."""
    return str(symbol or "").strip().upper() in DELISTED_SYMBOLS


def filter_delisted(symbols):
    """Return `symbols` with known delisted/renamed tickers removed.

    Order-preserving and de-dup-safe for the common list/tuple/set inputs.
    """
    return [s for s in symbols if not is_delisted(s)]
