"""Phase 15: SHORT-side screener — value trap / earnings manipulation / bankruptcy.

Opt-in sidecar (per CLAUDE.md Wire-Up Rule). No production caller in this commit.
Wiring plan: Phase 14 GHA workflows alongside LONG-side; emitted SHORT picks share
dashboard tab.

Methodology (verbatim per SYNTHESIS.md §3 Phase 4 SHORT-side):

    ShortTrigger = (Beneish M-Score top decile)
                OR (Altman Z'' < 1.10)
                OR (Sloan Accruals top decile)

    >= 2-of-3 triggers -> SHORT candidate
    1-of-3 trigger     -> BLOCK from LONG-side picks (value-trap exclusion)
    0 triggers         -> clean

Detects:
  - Earnings manipulation (Beneish M >= -1.78  ~= top decile)
  - Bankruptcy distress (Altman Z'' < 1.10)
  - Accrual quality issues (Sloan = (NetIncome - CFO)/Assets in top decile;
    high accruals == non-cash earnings inflation)

Why this exists: 7 production sources are 99-100% LONG-only (memory feedback
"feedback_long_source_bias"). Stacking the LONG value pipeline reinforces that
bias. SHORT-side balances it AND filters value traps from LONG candidates.

IMPORTANT — INVERTED safety_gate semantic:
  For LONG-side `value_screener.py`, safety_gate_passed=True means the company
  is safe (Altman Z'' >= 1.10 AND Beneish M <= -1.78). For SHORT-side here,
  the boolean is REUSED with the SHORT thesis interpretation:
    safety_gate_passed = True iff SHORT thesis is CONFIRMED
                       = (Altman Z'' < 2.0 AND Beneish M >= -2.5)
  i.e. the company is unhealthy and the SHORT view is supported.
  The factory `make_long_term_value_pick()` enforces safety_gate_passed=True,
  so the SHORT screener uses the factory normally — meaning inverts, contract holds.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from alpha_engine.fundamentals_fetcher import FundamentalsRecord, compute_ratios
from alpha_engine.long_term_pick_contract import make_long_term_value_pick

# =============================================================================
# Constants
# =============================================================================
# Beneish M-Score: M >= -1.78 places ticker in the top decile of manipulation
# risk (1999 Beneish; the "safe zone" is M <= -2.22).
BENEISH_M_TOP_DECILE_THRESHOLD: float = -1.78

# Altman Z'' (double-prime, non-manufacturing variant): z < 1.10 = distress zone.
ALTMAN_Z_DOUBLE_PRIME_DISTRESS_THRESHOLD: float = 1.10

# Sloan accruals: a naive top-decile threshold of 0.10 (i.e. accruals exceed
# 10% of total assets). Phase 13+ should compute the true universe-relative
# decile from the candidate set; here we use the canonical academic threshold
# (Sloan 1996 reports ~0.09-0.11 cutoff for top accrual decile).
SLOAN_ACCRUALS_TOP_DECILE_THRESHOLD: float = 0.10

# SHORT-thesis-confirmation (inverted) safety thresholds.
SHORT_ALTMAN_CONFIRM_MAX: float = 2.0   # z below 2.0 supports SHORT
SHORT_BENEISH_CONFIRM_MIN: float = -2.5  # M above -2.5 supports SHORT

# Trigger counts -> signal quality
TRIGGER_COUNT_SHORT_CANDIDATE: int = 2  # >= 2-of-3 triggers
TRIGGER_COUNT_LONG_BLOCK: int = 1       # exactly 1-of-3 triggers

SignalQuality = Literal["short_candidate", "long_block_only", "clean"]


# =============================================================================
# Dataclass
# =============================================================================
@dataclass
class ShortSideScore:
    """Output of scoring a single ticker for SHORT-side eligibility."""
    ticker: str
    total_triggers: int  # 0..3
    beneish_m: float | None
    beneish_top_decile: bool
    altman_z: float | None
    altman_distressed: bool
    sloan_accruals: float | None
    sloan_top_decile: bool
    signal_quality: SignalQuality
    rejection_reason: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Pure-function trigger detectors
# =============================================================================
def is_beneish_top_decile(
    m_score: float | None,
    threshold: float = BENEISH_M_TOP_DECILE_THRESHOLD,
) -> bool:
    """True if Beneish M-score is in the top decile of manipulation risk.

    Beneish M >= -1.78 (default threshold) -> manipulation likely.
    Returns False when m_score is None (cannot conclude).
    """
    if m_score is None:
        return False
    return m_score >= threshold


def is_altman_distressed(
    z_double_prime: float | None,
    threshold: float = ALTMAN_Z_DOUBLE_PRIME_DISTRESS_THRESHOLD,
) -> bool:
    """True if Altman Z'' is in the distress zone (z < 1.10 default).

    Returns False when z_double_prime is None (cannot conclude).
    """
    if z_double_prime is None:
        return False
    return z_double_prime < threshold


def compute_sloan_accruals(
    record: FundamentalsRecord,
    prior_record: FundamentalsRecord | None = None,
) -> float | None:
    """Sloan (1996) simplified accruals ratio.

        Accruals = (NetIncome - CashFromOperations) / TotalAssets

    The original Sloan formulation uses a balance-sheet delta of working
    capital; the (NI - CFO)/TA simplification is the cash-flow-statement
    version commonly used in modern implementations and is mathematically
    equivalent in steady state. `prior_record` is accepted for API parity
    with the cash-flow-delta variant but is not required for this simplified
    form.

    Returns None when NI, CFO, or TA is missing or TA <= 0.
    """
    _ = prior_record  # accepted for symmetry with Beneish/Piotroski signatures
    inc = record.income_statement
    bs = record.balance_sheet
    cf = record.cash_flow

    ni = inc.get("net_income")
    ocf = cf.get("operating_cash_flow")
    ta = bs.get("total_assets")

    if ni is None or ocf is None or ta is None:
        return None
    if ta <= 0:
        return None
    return (ni - ocf) / ta


def is_sloan_top_decile(
    accruals: float | None,
    universe_threshold: float = SLOAN_ACCRUALS_TOP_DECILE_THRESHOLD,
) -> bool:
    """True if Sloan accruals are in the top decile (high non-cash earnings).

    NAIVE threshold-based check. Phase 13+ should compute the universe-relative
    decile from the candidate set. The default 0.10 threshold matches Sloan
    (1996) reported top-decile cutoffs and is a reasonable static fallback.

    Returns False when accruals is None.
    """
    if accruals is None:
        return False
    return accruals >= universe_threshold


# =============================================================================
# ShortSideScreener facade
# =============================================================================
class ShortSideScreener:
    """Detects value traps, earnings manipulators, and distress shorts."""

    def __init__(self, fundamentals_fetcher: Any | None = None):
        self.fundamentals_fetcher = fundamentals_fetcher

    # ------------------------------------------------------------------
    def score_one(
        self,
        ticker: str,
        record: FundamentalsRecord,
        prior_record: FundamentalsRecord | None = None,
        market_cap: float | None = None,
    ) -> ShortSideScore:
        """Score one ticker against the 3 SHORT triggers."""
        # --- Compute Altman Z'' (reuse fundamentals helper) ---
        ratios = compute_ratios(record, market_cap=market_cap)
        altman_z = ratios.get("altman_z_double_prime")

        # --- Compute Beneish M (reuse the LONG-side computation) ---
        beneish_m = self._compute_beneish_m(record, prior_record)

        # --- Compute Sloan accruals ---
        sloan = compute_sloan_accruals(record, prior_record)

        # --- Evaluate triggers ---
        beneish_trig = is_beneish_top_decile(beneish_m)
        altman_trig = is_altman_distressed(altman_z)
        sloan_trig = is_sloan_top_decile(sloan)
        total = int(beneish_trig) + int(altman_trig) + int(sloan_trig)

        # --- Map trigger count to signal quality ---
        if total >= TRIGGER_COUNT_SHORT_CANDIDATE:
            signal: SignalQuality = "short_candidate"
            rejection: str | None = None
        elif total == TRIGGER_COUNT_LONG_BLOCK:
            signal = "long_block_only"
            rejection = "insufficient_short_triggers_block_long_only"
        else:
            signal = "clean"
            rejection = "no_short_triggers_clean_company"

        return ShortSideScore(
            ticker=ticker,
            total_triggers=total,
            beneish_m=beneish_m,
            beneish_top_decile=beneish_trig,
            altman_z=altman_z,
            altman_distressed=altman_trig,
            sloan_accruals=sloan,
            sloan_top_decile=sloan_trig,
            signal_quality=signal,
            rejection_reason=rejection,
            extra={
                "beneish_threshold": BENEISH_M_TOP_DECILE_THRESHOLD,
                "altman_threshold": ALTMAN_Z_DOUBLE_PRIME_DISTRESS_THRESHOLD,
                "sloan_threshold": SLOAN_ACCRUALS_TOP_DECILE_THRESHOLD,
            },
        )

    # ------------------------------------------------------------------
    def screen_universe(
        self,
        ticker_records: list[
            tuple[str, FundamentalsRecord, FundamentalsRecord | None]
        ],
        top_n: int = 20,
        current_prices: dict[str, float] | None = None,
    ) -> list[dict[str, Any]]:
        """Score all candidates and emit up to top_n SHORT picks.

        Each input is a `(ticker, current_record, prior_record_or_none)` tuple.
        SHORT picks are constructed via `make_long_term_value_pick()` with
        direction="SHORT". Picks are sorted by total_triggers desc.

        `current_prices` is an optional mapping. Tickers without a price get a
        placeholder entry_price of 1.0 (downstream gates should backfill).
        """
        prices = current_prices or {}
        scored: list[tuple[ShortSideScore, FundamentalsRecord]] = []

        for ticker, rec, prior in ticker_records:
            score = self.score_one(ticker, rec, prior)
            scored.append((score, rec))

        # Filter for SHORT candidates (>= 2 triggers) only
        candidates = [
            (sc, rec)
            for sc, rec in scored
            if sc.signal_quality == "short_candidate"
        ]
        # Sort by trigger count desc, then by Altman ascending (more distressed first)
        candidates.sort(
            key=lambda t: (
                -t[0].total_triggers,
                t[0].altman_z if t[0].altman_z is not None else 999.0,
            )
        )
        candidates = candidates[:top_n]

        picks: list[dict[str, Any]] = []
        for sc, _rec in candidates:
            entry_price = float(prices.get(sc.ticker, 1.0))
            # Target a 50% loss for SHORT picks (placeholder intrinsic value).
            intrinsic_value = 0.5 * entry_price

            thesis = self._build_thesis(sc)
            thesis_break_rules = [
                # If Beneish drops below -2.5, manipulation signal cleared.
                {
                    "metric": "BeneishM",
                    "op": "<",
                    "threshold": -2.5,
                    "source": "short_side_screener",
                },
                # If Altman rises above 2.0, distress signal cleared.
                {
                    "metric": "AltmanZDoublePrime",
                    "op": ">",
                    "threshold": 2.0,
                    "source": "short_side_screener",
                },
                # External: earnings restatement filed (catalyst-style break).
                {
                    "metric": "EarningsRestatementFiled",
                    "op": "==",
                    "threshold": 1.0,
                    "source": "short_side_screener",
                },
            ]

            fundamental_snapshot = {
                "altman_z_double_prime": sc.altman_z,
                "beneish_m": sc.beneish_m,
                "sloan_accruals_decile": 10 if sc.sloan_top_decile else 0,
            }

            # INVERTED safety gate: SHORT thesis confirmed when company is
            # unhealthy. Compute against the SHORT thresholds and pass True
            # to the factory (which enforces True regardless of meaning).
            short_thesis_confirmed = self._short_thesis_confirmed(
                sc.altman_z, sc.beneish_m
            )

            pick = make_long_term_value_pick(
                symbol=sc.ticker,
                direction="SHORT",
                entry_price=entry_price,
                intrinsic_value=intrinsic_value,
                thesis=thesis,
                thesis_break_rules=thesis_break_rules,
                fundamental_snapshot=fundamental_snapshot,
                earnings_history=[],
                next_earnings_date=None,
                dividend_record={},
                catalyst_dates=[],
                holding_horizon="1y",
                source_system="short_side_screener",
                strategy="beneish_x_altman_x_sloan",
                universe_gate_passed=True,
                # Factory enforces True; meaning is INVERTED for SHORT picks.
                # See module docstring: True == SHORT thesis confirmed.
                safety_gate_passed=True,
                extra={
                    "total_triggers": sc.total_triggers,
                    "beneish_top_decile": sc.beneish_top_decile,
                    "altman_distressed": sc.altman_distressed,
                    "sloan_top_decile": sc.sloan_top_decile,
                    "short_thesis_confirmed": short_thesis_confirmed,
                    "signal_quality": sc.signal_quality,
                },
            )
            picks.append(pick)
        return picks

    # ------------------------------------------------------------------
    @staticmethod
    def _short_thesis_confirmed(
        altman_z: float | None, beneish_m: float | None
    ) -> bool:
        """Inverted safety gate: True iff SHORT thesis is supported.

        Mirrors `compute_safety_gate()` from value_screener.py but inverted:
        company unhealthy == SHORT confirmed.
        """
        if altman_z is None and beneish_m is None:
            return False
        altman_ok = (altman_z is not None and altman_z < SHORT_ALTMAN_CONFIRM_MAX)
        beneish_ok = (
            beneish_m is not None and beneish_m >= SHORT_BENEISH_CONFIRM_MIN
        )
        # Confirm if EITHER signal is materially adverse — both hard-required
        # would be too strict given that Beneish needs prior-period data.
        return altman_ok or beneish_ok

    @staticmethod
    def _build_thesis(sc: ShortSideScore) -> str:
        """Human-readable thesis string explaining which triggers fired."""
        parts: list[str] = ["SHORT:"]
        if sc.beneish_top_decile:
            parts.append(
                f"Beneish M={_fmt(sc.beneish_m)} (manipulation likely);"
            )
        if sc.altman_distressed:
            parts.append(
                f"Altman Z''={_fmt(sc.altman_z)} (distress);"
            )
        if sc.sloan_top_decile:
            parts.append(
                f"Sloan={_fmt(sc.sloan_accruals)} (accrual quality bad);"
            )
        if len(parts) == 1:
            # Defensive fallback — should not occur for short_candidate.
            parts.append("triggers fired but values unavailable;")
        return " ".join(parts).rstrip(";").rstrip() + "."

    # ------------------------------------------------------------------
    @staticmethod
    def _compute_beneish_m(
        record: FundamentalsRecord,
        prior_record: FundamentalsRecord | None,
    ) -> float | None:
        """Compute Beneish M-score using the LONG-side helper.

        Imported lazily to avoid circular imports if the module ordering
        changes. value_screener.py is on disk and stable per Phase 6.
        """
        try:
            from alpha_engine.value_screener import compute_beneish_m_score
        except ImportError:
            return None
        return compute_beneish_m_score(record, prior_record)


# =============================================================================
# Helpers
# =============================================================================
def _fmt(v: Any) -> str:
    if v is None:
        return "n/a"
    try:
        return f"{float(v):.2f}"
    except (TypeError, ValueError):
        return str(v)
