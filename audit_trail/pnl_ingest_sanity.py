"""
Asset-aware clamp for recorded ``pnl_pct`` at ingest (resolver + dashboard normalize).

Forex/equity rows have been corrupted by pip-vs-percent confusion or bad price
stamps (|pnl_pct| >> 200%). Crypto can have legitimate large single-trade %
moves; cap separately.
"""

from __future__ import annotations

# Crypto: allow wide tails (e.g. micro-cap pumps) but reject impossible -100%+ wipeout artifacts.
_PNL_CLAMP_CRYPTO = (-99.0, 500.0)
# Non-crypto: single-trade % beyond this range is almost always data corruption (RCA 2026-04-21).
_PNL_CLAMP_NON_CRYPTO = (-100.0, 200.0)


def normalize_asset_class_for_pnl(pick: dict) -> str:
    """Lightweight class for clamp only — aligns with dashboard _derive_asset_class when possible."""
    ac = str(pick.get("asset_class") or pick.get("category") or "").upper().strip()
    if ac in ("STOCK", "STOCKS", "PENNY_STOCK", "EQUITIES"):
        return "EQUITY"
    if ac == "COMMODITIES":
        return "COMMODITY"
    if ac:
        return ac
    sym = str(pick.get("symbol") or "").upper()
    if sym.endswith("=X"):
        return "FOREX"
    if sym.endswith("=F"):
        return "FUTURES"
    if any(sym.endswith(s) for s in ("USDT", "USDC", "BUSD")):
        return "CRYPTO"
    return "UNKNOWN"


def clamp_pnl_pct_for_pick(pnl: float, asset_class: str) -> tuple[float, bool]:
    """Return (clamped_pnl, was_clamped)."""
    ac = str(asset_class or "UNKNOWN").upper()
    crypto_like = ac in ("CRYPTO", "MEME")
    lo, hi = _PNL_CLAMP_CRYPTO if crypto_like else _PNL_CLAMP_NON_CRYPTO
    if pnl < lo:
        return lo, True
    if pnl > hi:
        return hi, True
    return pnl, False


def apply_pnl_clamp_to_pick(pick: dict, pnl_key: str = "pnl_pct") -> bool:
    """Mutate pick in place. Returns True if clamped."""
    raw = pick.get(pnl_key)
    if raw is None:
        return False
    try:
        pnl = float(raw)
    except (TypeError, ValueError):
        return False
    ac = normalize_asset_class_for_pnl(pick)
    new_pnl, clamped = clamp_pnl_pct_for_pick(pnl, ac)
    if not clamped:
        return False
    pick[pnl_key] = round(new_pnl, 4)
    pick["pnl_pct_ingest_clamped"] = True
    pick["pnl_pct_pre_clamp"] = round(pnl, 4)
    return True
