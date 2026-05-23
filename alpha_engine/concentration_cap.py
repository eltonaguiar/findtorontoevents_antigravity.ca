"""Concentration cap check for active picks (per-symbol + HHI).

Size-aware escape hatch (v3, 2026-05-22): the percentage per-symbol cap
mechanically over-blocks low-count classes — with ~12 picks in a class,
the 3rd pick on a symbol = 25%% > 20%% FOREX cap and gets rejected even
though the absolute count is tiny. ``passes_concentration_cap`` now only
rejects when BOTH the %% cap is exceeded AND the absolute post-add symbol
count exceeds ``MIN_COUNT`` (default 3). A small book passes the %% cap;
a large book still enforces it.


Addresses the COMMODITY CT=F 75.6% / COT over-emission phantom-edge
pattern (PR #961 falsification audit) and mimo's per-class concentration
proposal — using verified-only thresholds and a clean, namespaced caller
contract.

Pure-function module. No global state. Single entry point::

    passes_concentration_cap(asset_class, symbol, active_picks)
        -> tuple[bool, str]   # (allow, reason_if_blocked)

Default policy::

    CRYPTO     max_per_symbol_pct=10  (lowered 15→10, 2026-05-17, APEUSDT gap-risk)
    COMMODITY  max_per_symbol_pct=30
    EQUITY     max_per_symbol_pct=10
    ETF        max_per_symbol_pct=15
    FOREX      max_per_symbol_pct=20
    BOND       max_per_symbol_pct=25
    FUTURES    max_per_symbol_pct=20

Counts are over currently-active picks for that asset class. If the new
pick would push the symbol's share above ``max_per_symbol_pct``, the
caller MUST reject before sizing.

WIRED (production caller): ``audit_trail/quality_gates.py::passes_active_gate``
invokes ``passes_concentration_cap`` (~line 7002), guarded by the
``CONCENTRATION_CAP_ENABLED`` kill-switch.

NFA. Read-only.
"""
from __future__ import annotations
import os
import logging
from collections import Counter
from typing import Iterable

logger = logging.getLogger(__name__)

DEFAULT_CAPS_PCT: dict[str, int] = {
    # 2026-05-17: CRYPTO lowered 15→10. ml_enhanced_APEUSDT_* had 7 correlated
    # SHORT variants open simultaneously when APEUSDT gapped 110% — all hit the
    # same exit at $0.2098 for -100% to -111% losses each. At 10% cap a symbol
    # is limited to ~5 picks per 50 active, reducing family-correlation gap risk.
    "CRYPTO": 10,
    "COMMODITY": 30,
    "EQUITY": 10,
    "ETF": 15,
    "FOREX": 20,
    "BOND": 50,     # 2026-05-15 M-013: raised 25→50 (BOND n small; single strategy OK)
    "FUTURES": 30,  # 2026-05-15 M-013: raised 20→30 (FUTURES still accumulating n)
}

MIN_ACTIVE_FOR_CAP = 10  # below this, do not apply cap (avoids cold-start lockout)

# Size-aware escape hatch: the % cap only rejects once the absolute post-add
# symbol count EXCEEDS this floor. Below/at it, a pick passes the % cap even
# in a small book — fixes the FOREX/COMMODITY 0-active-picks over-block.
# Clamped to [1, MIN_ACTIVE_FOR_CAP - 1] so it can never disable the early
# return nor allow unbounded concentration.
MIN_COUNT = max(1, min(int(os.getenv("CONCENTRATION_MIN_COUNT", "3")),
                       MIN_ACTIVE_FOR_CAP - 1))


def _class_of(p: dict) -> str:
    return (p.get("asset_class") or "").upper()


def _sym_of(p: dict) -> str:
    return (p.get("symbol") or "").upper()


def class_symbol_counts(active_picks: Iterable[dict],
                        asset_class: str) -> Counter:
    """Return Counter of symbols among active picks for the given class."""
    ac = (asset_class or "").upper()
    return Counter(_sym_of(p) for p in active_picks if _class_of(p) == ac)


def share_pct(counts: Counter, symbol: str) -> float:
    total = sum(counts.values())
    if total == 0:
        return 0.0
    return 100.0 * counts.get((symbol or "").upper(), 0) / total


def passes_concentration_cap(asset_class: str,
                             symbol: str,
                             active_picks: Iterable[dict],
                             caps_pct: dict[str, int] | None = None,
                             min_active: int = MIN_ACTIVE_FOR_CAP
                             ) -> tuple[bool, str]:
    """Return (allow, reason). Reason is '' when allow=True.

    Counts the NEW pick optimistically (i.e. as if already added) before
    applying the cap; this prevents the off-by-one race where the Nth
    pick that pushes share past the cap still gets in.
    """
    caps = caps_pct or DEFAULT_CAPS_PCT
    ac = (asset_class or "").upper()
    sym = (symbol or "").upper()
    cap = caps.get(ac)
    if cap is None:
        return True, ""
    counts = class_symbol_counts(active_picks, ac)
    total_after = sum(counts.values()) + 1
    if total_after < min_active:
        return True, ""
    sym_after = counts.get(sym, 0) + 1
    share_after = 100.0 * sym_after / total_after
    # Size-aware: only reject when the % cap is exceeded AND the absolute
    # post-add symbol count is above MIN_COUNT. A small book (sym_after <=
    # MIN_COUNT) passes the % cap — the escape hatch that fixes low-count
    # classes (FOREX/COMMODITY) emitting 0 active picks.
    if share_after > cap and sym_after > MIN_COUNT:
        return False, (
            f"concentration_cap_blocked: {ac}/{sym} would be "
            f"{share_after:.1f}% > {cap}% cap "
            f"(n={sym_after}/{total_after}, count > MIN_COUNT={MIN_COUNT})"
        )
    if share_after > cap:
        logger.debug(
            "concentration_cap escape hatch: %s/%s at %.1f%% > %d%% cap "
            "ALLOWED (n=%d/%d <= MIN_COUNT=%d, small-book exemption)",
            ac, sym, share_after, cap, sym_after, total_after, MIN_COUNT,
        )
    return True, ""


def class_hhi(active_picks: Iterable[dict], asset_class: str) -> float:
    """Herfindahl-Hirschman Index (0-10000) for symbol concentration.

    >2500 = highly concentrated. <1500 = diversified.
    """
    counts = class_symbol_counts(active_picks, asset_class)
    total = sum(counts.values())
    if total == 0:
        return 0.0
    shares = [100.0 * v / total for v in counts.values()]
    return sum(s * s for s in shares)


def class_hhi_verdict(hhi: float) -> str:
    if hhi >= 2500:
        return "HIGH_CONCENTRATION"
    if hhi >= 1500:
        return "MODERATE_CONCENTRATION"
    return "DIVERSIFIED"


# ──────────────────────────────────────────────────────────────────────────────
# COMMODITY CT=F emission cap (per-scan-cycle signal cap)
# ──────────────────────────────────────────────────────────────────────────────
# Hard-block CT=F > COMMODITY_CTF_MAX_PCT% of newly emitted COMMODITY signals
# per scan cycle. This is a PER-SIGNAL-BATCH cap (not active-pick cap), applied
# at emission time so that downstream PBO computation sees a diversified
# COMMODITY signal set rather than a CT=F mono-culture.
#
# PR-2026-0518-3: enables COMMODITY to advance from WATCH to PAPER PILOT.
# Override via env var COMMODITY_CTF_CAP_PCT (integer, default 40).

# Default max CT=F share of COMMODITY signals per scan cycle (percent)
COMMODITY_CTF_MAX_PCT = int(os.environ.get("COMMODITY_CTF_CAP_PCT", "40"))


# Default confidence floor for CT=F picks competing for limited slots.
# Picks below this floor are always rejected when over the cap, regardless of
# rank. Only applied during emission-cap enforcement (NOT otherwise).
COMMODITY_CTF_MIN_CONFIDENCE = float(os.environ.get("COMMODITY_CTF_MIN_CONF", "0.50"))


def _is_commodity_pick(p: dict) -> bool:
    """Return True if pick belongs to the COMMODITY asset class."""
    ac = str(p.get("asset_class") or "").upper().strip()
    cat = str(p.get("category") or "").lower().strip()
    return ac in ("COMMODITY", "COMMODITIES") or cat == "commodity"


def _is_ctf_pick(p: dict) -> bool:
    """Return True if pick is CT=F (Cotton No. 2)."""
    sym = str(p.get("symbol") or "").upper().strip()
    return sym in ("CT=F", "CT") and _is_commodity_pick(p)


def enforce_commodity_ctf_emission_cap(
    picks: list[dict],
    max_ctf_pct: int | None = None,
    min_conf: float | None = None,
) -> tuple[list[dict], list[dict]]:
    """Enforce CT=F <= max_ctf_pct% of newly emitted COMMODITY signals.

    This is a **per-scan-cycle signal emission cap**, distinct from the
    per-symbol active-pick cap (``passes_concentration_cap``). It limits how
    many CT=F picks can be emitted in a single scan rather than how many
    CT=F picks can be in the active portfolio at once.

    Algorithm:
        1. Identify COMMODITY picks and CT=F picks within the batch.
        2. If CT=F share > max_ctf_pct, sort CT=F picks by confidence
           (ascending) and reject the lowest-confidence picks until under cap.
        3. CT=F picks below ``min_conf`` are always rejected first, then
           the lowest remaining until the ratio is satisfied.
        4. Non-COMMODITY and non-CT=F COMMODITY picks pass through unchanged.

    Returns (passed, rejected) tuple.

    Args:
        picks: Batch of newly emitted signals (not active-pick snapshot).
        max_ctf_pct: Max CT=F %% of total COMMODITY signals (0-100).
                     Defaults to ``COMMODITY_CTF_MAX_PCT`` (40).
        min_conf: Minimum confidence for CT=F to compete for slots.
                  Defaults to ``COMMODITY_CTF_MIN_CONFIDENCE`` (0.50).
    """
    cap_pct = max_ctf_pct if max_ctf_pct is not None else COMMODITY_CTF_MAX_PCT
    floor_conf = min_conf if min_conf is not None else COMMODITY_CTF_MIN_CONFIDENCE

    if cap_pct >= 100:
        return picks, []  # cap disabled

    # Separate picks
    ctf_picks: list[dict] = []
    other_commodity: list[dict] = []
    non_commodity: list[dict] = []

    for p in picks:
        if _is_ctf_pick(p):
            ctf_picks.append(p)
        elif _is_commodity_pick(p):
            other_commodity.append(p)
        else:
            non_commodity.append(p)

    total_comm = len(ctf_picks) + len(other_commodity)

    if total_comm == 0:
        return picks, []  # no COMMODITY picks, nothing to cap

    # Max allowed CT=F count (round up so small batches don't get 0)
    max_ctf = max(0, int(round(cap_pct / 100.0 * total_comm)))

    if len(ctf_picks) <= max_ctf:
        # Under cap — all pass
        return picks, []

    # Over cap — sort CT=F picks: below-floor first, then by confidence ascending
    def _sort_key(p: dict) -> tuple[int, float]:
        conf = float(p.get("confidence", 0) or 0)
        below_floor = 0 if conf >= floor_conf else 1
        return (below_floor, conf)

    ctf_sorted = sorted(ctf_picks, key=_sort_key)

    # Keep the top `max_ctf` CT=F picks
    keep_count = max_ctf
    if keep_count <= 0:
        # No CT=F allowed at all — reject all
        kept_ctf: list[dict] = []
        rejected_ctf = ctf_sorted
    else:
        rejected_ctf = ctf_sorted[:-keep_count]
        kept_ctf = ctf_sorted[-keep_count:]

    returned = non_commodity + other_commodity + kept_ctf

    # Tag rejected picks
    for rp in rejected_ctf:
        rp["_rejected_reason"] = (
            f"ctf_emission_cap: CT=F would be "
            f"{len(ctf_picks)}/{total_comm} = "
            f"{100.0 * len(ctf_picks) / total_comm:.0f}%% > {cap_pct}%% cap"
        )

    print(
        f"  [CTF_CAP] CT=F {len(ctf_picks)}/{total_comm} COMMODITY signals "
        f"({100.0 * len(ctf_picks) / total_comm:.0f}%%). "
        f"Cap={cap_pct}%% -> kept {keep_count}, rejected {len(rejected_ctf)}"
    )

    return returned, rejected_ctf
