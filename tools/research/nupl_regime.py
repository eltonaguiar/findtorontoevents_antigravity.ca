"""NUPL (Net Unrealized Profit/Loss) regime filter for CRYPTO.

NUPL > 0.75 = euphoria zone — historically precedes major corrections.
Source: Coin Metrics Community API (free, no key) via alpha_engine.onchain_strategies._fetch_nupl.
Also supports CoinGlass / Glassnode (requires paid plan) — wired via NUPL_OVERRIDE env var
for manual regime setting until a paid API is confirmed.

Shadow mode default: logs but does not block (NUPL_GATE_ENFORCE=0).

Existing NUPL integration note:
  alpha_engine/onchain_strategies.py already fetches real NUPL from Coin Metrics
  (CapMrktCurUSD / CapRealUSD) via _fetch_nupl(). This module re-uses that fetch
  as its live data source and adds the gate logic on top.
"""
import logging
import os

logger = logging.getLogger(__name__)

NUPL_EUPHORIA_THRESHOLD = float(os.getenv("NUPL_EUPHORIA_THRESHOLD", "0.75"))
NUPL_GATE_ENFORCE = os.getenv("NUPL_GATE_ENFORCE", "0") == "1"


def get_current_nupl() -> "float | None":
    """Fetch current NUPL. Returns None if unavailable.

    Priority:
      1. NUPL_OVERRIDE env var (manual override for testing / prod until paid API confirmed)
      2. Coin Metrics Community API via alpha_engine.onchain_strategies._fetch_nupl
         (free, no key — BTC MarketCap / RealizedCap)
      3. None (gracefully unavailable — gate fails open)
    """
    # Manual override takes priority
    override = os.getenv("NUPL_OVERRIDE")
    if override is not None:
        try:
            return float(override)
        except (TypeError, ValueError):
            logger.warning("NUPL_OVERRIDE=%r is not a valid float — ignoring", override)

    # Reuse the existing Coin Metrics fetch already in the codebase
    try:
        from alpha_engine.onchain_strategies import _fetch_nupl  # type: ignore[attr-defined]
        return _fetch_nupl()
    except Exception:
        return None  # gracefully unavailable


def is_crypto_long_blocked_by_nupl() -> "tuple[bool, str]":
    """Return (blocked, reason). Never raises — fails open.

    blocked=True only when:
      - NUPL is available AND > NUPL_EUPHORIA_THRESHOLD AND NUPL_GATE_ENFORCE=1

    In shadow mode (NUPL_GATE_ENFORCE=0, default), euphoria is logged but
    the pick is NOT blocked — allows production monitoring without live impact.
    """
    try:
        threshold = float(os.getenv("NUPL_EUPHORIA_THRESHOLD", str(NUPL_EUPHORIA_THRESHOLD)))
        enforce = os.getenv("NUPL_GATE_ENFORCE", "0") == "1"

        nupl = get_current_nupl()
        if nupl is None:
            return False, "nupl_unavailable:pass"
        if nupl > threshold:
            reason = f"M-038:nupl_euphoria({nupl:.3f}>{threshold})"
            if enforce:
                logger.info("M-038 NUPL euphoria gate: CRYPTO LONG blocked — %s", reason)
                return True, reason
            else:
                logger.info(
                    "M-038 NUPL euphoria gate (shadow): NUPL=%.3f > %.3f — "
                    "would block CRYPTO LONG; NUPL_GATE_ENFORCE=0 (pass-through)",
                    nupl, threshold,
                )
                return False, reason
        return False, f"nupl_ok({nupl:.3f})"
    except Exception as exc:
        logger.debug("M-038 NUPL gate error (fail-open): %s", exc)
        return False, "nupl_error:pass"
