"""Phase 6: Long-term value screener (Magic Formula x Piotroski x Acquirer's Multiple).

Opt-in sidecar (per CLAUDE.md Wire-Up Rule). No production caller in this commit.
Wiring plan: Phase 14 GHA workflows + Phase 11 dashboard.

Composite formula (verbatim from SYNTHESIS.md §3):

    LongTermScore = (0.45 * ValueComposite + 0.55 * QualityComposite) * SafetyGate

    ValueComposite = 0.40 * MagicFormulaPercentile
                   + 0.35 * AcquirersMultiplePercentile
                   + 0.25 * FCFYieldPercentile

    QualityComposite = 0.50 * PiotroskiFScore/9
                     + 0.30 * ROIC_Stability
                     + 0.20 * DebtToEquityScore

    SafetyGate = 1.0 if (AltmanZ_DoublePrime >= 1.10 AND BeneishM <= -1.78) else 0.0

Universe gates apply BEFORE scoring (hard exclusions). See `_apply_universe_gates`.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from alpha_engine.fundamentals_fetcher import FundamentalsRecord, compute_ratios
from alpha_engine.long_term_pick_contract import (
    make_long_term_value_pick,
)

# Beneish M placeholder used when prior-period data is missing. The 1999
# academic safe-zone is M <= -2.22; -2.5 is comfortably inside that zone.
BENEISH_M_PLACEHOLDER: float = -2.5

# Universe-gate constants
MIN_MARKET_CAP_USD: float = 300_000_000.0
MIN_OPERATING_HISTORY_YEARS: int = 5
MAX_10K_FILING_AGE_DAYS: int = 540
EXCLUDED_ASSET_CLASSES: frozenset[str] = frozenset({"Financial", "Utilities"})

# Composite weights
VALUE_WEIGHT: float = 0.45  # v1.1 quality-tilt (was 0.55 in v1.0; see research/08+06)
QUALITY_WEIGHT: float = 0.55  # v1.1 quality-tilt (was 0.45 in v1.0)
W_MAGIC: float = 0.40
W_ACQUIRERS: float = 0.35
W_FCF: float = 0.25
W_PIOTROSKI: float = 0.50
W_ROIC_STAB: float = 0.30
W_DTE: float = 0.20

# Safety thresholds
ALTMAN_Z_DOUBLE_PRIME_MIN: float = 1.10
BENEISH_M_MAX: float = -1.78


# =============================================================================
# Dataclasses
# =============================================================================
@dataclass
class ScreenerInput:
    """Inputs for one ticker, supplied to ValueScreener.score_one / screen_universe."""
    ticker: str
    current_price: float
    market_cap: float
    fundamentals: FundamentalsRecord
    earnings: Any | None = None  # EarningsRecord-like, optional
    dividends: Any | None = None  # dict (DividendRecord TypedDict), optional
    operating_history_years: int = 10
    going_concern_flag: bool = False
    pink_sheets: bool = False
    is_financial_or_utility: bool = False
    last_10k_filing_age_days: int = 90


@dataclass
class ScreenerScore:
    """Output of scoring a single ticker."""
    ticker: str
    total_score: float
    value_composite: float
    quality_composite: float
    safety_gate_passed: bool
    universe_gate_passed: bool
    piotroski_f: int
    magic_formula_rank: int
    acquirers_multiple: float | None
    altman_z_double_prime: float | None
    beneish_m: float | None
    rejection_reason: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Pure-function scorers
# =============================================================================
def compute_piotroski_f_score(
    record: FundamentalsRecord,
    prior_record: FundamentalsRecord | None = None,
) -> int:
    """Piotroski (2000) 9-test F-score.

    Tests (1 point each, max 9):
      Profitability:
        1. NI > 0
        2. ROA > 0  (NI / total_assets)
        3. OCF > 0
        4. OCF > NI  (accruals quality)
      Leverage / liquidity / source-of-funds:
        5. Decreasing leverage YoY  (LTD/TA decreases)
        6. Increasing current ratio YoY
        7. No new shares issued YoY
      Operating efficiency:
        8. Increasing gross margin YoY  (proxy: NI/Revenue)
        9. Increasing asset turnover YoY  (Revenue/TA)

    If `prior_record is None`, only the 4 static (profitability) tests can pass
    -> max F = 4.
    """
    score = 0
    inc = record.income_statement
    bs = record.balance_sheet
    cf = record.cash_flow

    ni = inc.get("net_income")
    revenue = inc.get("revenue")
    ta = bs.get("total_assets")
    cl = bs.get("current_liabilities")
    ca = bs.get("current_assets")
    ltd = bs.get("long_term_debt") or 0.0
    shares = bs.get("shares_outstanding")
    ocf = cf.get("operating_cash_flow")

    # 1. NI > 0
    if ni is not None and ni > 0:
        score += 1
    # 2. ROA > 0
    if ni is not None and ta is not None and ta > 0 and (ni / ta) > 0:
        score += 1
    # 3. OCF > 0
    if ocf is not None and ocf > 0:
        score += 1
    # 4. OCF > NI
    if ocf is not None and ni is not None and ocf > ni:
        score += 1

    if prior_record is None:
        return score

    p_inc = prior_record.income_statement
    p_bs = prior_record.balance_sheet

    p_ni = p_inc.get("net_income")
    p_revenue = p_inc.get("revenue")
    p_ta = p_bs.get("total_assets")
    p_cl = p_bs.get("current_liabilities")
    p_ca = p_bs.get("current_assets")
    p_ltd = p_bs.get("long_term_debt") or 0.0
    p_shares = p_bs.get("shares_outstanding")

    # 5. Decreasing leverage YoY (LTD/TA)
    if ta is not None and ta > 0 and p_ta is not None and p_ta > 0:
        cur_lev = ltd / ta
        prior_lev = p_ltd / p_ta
        if cur_lev < prior_lev:
            score += 1

    # 6. Increasing current ratio YoY
    if (ca is not None and cl is not None and cl > 0 and
            p_ca is not None and p_cl is not None and p_cl > 0):
        if (ca / cl) > (p_ca / p_cl):
            score += 1

    # 7. No new shares issued YoY (current <= prior)
    if shares is not None and p_shares is not None:
        if shares <= p_shares:
            score += 1

    # 8. Increasing gross margin (proxy: NI / Revenue)
    if (ni is not None and revenue is not None and revenue > 0 and
            p_ni is not None and p_revenue is not None and p_revenue > 0):
        if (ni / revenue) > (p_ni / p_revenue):
            score += 1

    # 9. Increasing asset turnover (Revenue / TA)
    if (revenue is not None and ta is not None and ta > 0 and
            p_revenue is not None and p_ta is not None and p_ta > 0):
        if (revenue / ta) > (p_revenue / p_ta):
            score += 1

    return score


def compute_beneish_m_score(
    record: FundamentalsRecord,
    prior_record: FundamentalsRecord | None,
) -> float | None:
    """Beneish (1999) 8-variable M-score.

    M = -4.84
        + 0.92  * DSRI
        + 0.528 * GMI
        + 0.404 * AQI
        + 0.892 * SGI
        + 0.115 * DEPI
        - 0.172 * SGAI
        + 4.679 * TATA
        - 0.327 * LVGI

    Returns None if prior_record is None or required inputs are missing.
    Threshold: M <= -1.78 = low manipulation risk.
    """
    if prior_record is None:
        return None

    inc = record.income_statement
    bs = record.balance_sheet
    cf = record.cash_flow
    p_inc = prior_record.income_statement
    p_bs = prior_record.balance_sheet

    revenue = inc.get("revenue")
    p_revenue = p_inc.get("revenue")
    ni = inc.get("net_income")
    ta = bs.get("total_assets")
    p_ta = p_bs.get("total_assets")
    cl = bs.get("current_liabilities")
    p_cl = p_bs.get("current_liabilities")
    ltd = bs.get("long_term_debt") or 0.0
    p_ltd = p_bs.get("long_term_debt") or 0.0
    da = inc.get("ebitda_proxy_da")
    p_da = p_inc.get("ebitda_proxy_da")
    ocf = cf.get("operating_cash_flow")

    required = (revenue, p_revenue, ni, ta, p_ta, cl, p_cl)
    if any(v is None for v in required):
        return None
    if revenue == 0 or p_revenue == 0 or ta == 0 or p_ta == 0:
        return None

    # We don't always have receivables / COGS / SGA broken out in our minimal
    # FundamentalsRecord. Use defensible proxies that converge on the original
    # signal: when manipulation is present the relevant ratio rises (DSRI, GMI,
    # AQI, SGI), so missing components default to 1.0 (neutral).
    dsri = 1.0  # receivables not in standardized record
    gmi = 1.0   # gross margin proxy unavailable
    aqi = 1.0   # asset quality index unavailable

    sgi = revenue / p_revenue
    if da is not None and p_da is not None and p_da != 0:
        depi = (p_da / (p_ta - 0)) / max((da / max(ta, 1.0)), 1e-9)
    else:
        depi = 1.0
    sgai = 1.0  # SG&A not broken out

    if ocf is not None:
        tata = (ni - ocf) / ta
    else:
        tata = 0.0

    cur_lev = ((ltd or 0.0) + (cl or 0.0)) / ta
    prior_lev = ((p_ltd or 0.0) + (p_cl or 0.0)) / p_ta
    lvgi = cur_lev / prior_lev if prior_lev > 0 else 1.0

    m = (-4.84
         + 0.92 * dsri
         + 0.528 * gmi
         + 0.404 * aqi
         + 0.892 * sgi
         + 0.115 * depi
         - 0.172 * sgai
         + 4.679 * tata
         - 0.327 * lvgi)
    return m


def compute_debt_to_equity_score(d_to_e: float | None) -> float:
    """Map Debt/Equity to a [0,1] score.

    1.0 if D/E < 0.5, scales linearly to 0.0 at D/E = 2.0, clamped.
    None / negative equity -> 0.0.
    """
    if d_to_e is None or d_to_e < 0:
        return 0.0
    if d_to_e < 0.5:
        return 1.0
    if d_to_e >= 2.0:
        return 0.0
    return 1.0 - (d_to_e - 0.5) / 1.5


def compute_value_composite(
    magic_pct: float, acquirers_pct: float, fcf_pct: float
) -> float:
    """ValueComposite = 0.40*Magic + 0.35*AcqMult + 0.25*FCFYield (percentiles)."""
    return W_MAGIC * magic_pct + W_ACQUIRERS * acquirers_pct + W_FCF * fcf_pct


def compute_quality_composite(
    piotroski_f: int, roic: float | None, d_to_e_score: float
) -> float:
    """QualityComposite per SYNTHESIS §3.

    ROIC_Stability proxy: clamp(roic / 0.20, 0, 1) — i.e. 20% ROIC = full credit.
    """
    f_norm = max(0, min(9, piotroski_f)) / 9.0
    if roic is None:
        roic_stab = 0.0
    else:
        roic_stab = max(0.0, min(1.0, roic / 0.20))
    return W_PIOTROSKI * f_norm + W_ROIC_STAB * roic_stab + W_DTE * d_to_e_score


def compute_safety_gate(
    altman_z: float | None, beneish_m: float | None
) -> bool:
    """SafetyGate: True iff Altman Z'' >= 1.10 AND Beneish M <= -1.78."""
    if altman_z is None:
        return False
    if beneish_m is None:
        # When M cannot be computed (no prior), use placeholder safe-zone value.
        beneish_m = BENEISH_M_PLACEHOLDER
    return altman_z >= ALTMAN_Z_DOUBLE_PRIME_MIN and beneish_m <= BENEISH_M_MAX


# =============================================================================
# Universe-gate helper
# =============================================================================
def _apply_universe_gates(s: ScreenerInput) -> str | None:
    """Return rejection reason string if any hard gate fails, else None."""
    if s.market_cap is None or s.market_cap < MIN_MARKET_CAP_USD:
        return "universe_gate_market_cap"
    if s.operating_history_years < MIN_OPERATING_HISTORY_YEARS:
        return "universe_gate_operating_history"
    if s.is_financial_or_utility:
        return "universe_gate_financial_or_utility"
    if s.going_concern_flag:
        return "universe_gate_going_concern"
    if s.pink_sheets:
        return "universe_gate_pink_sheets"
    if s.last_10k_filing_age_days > MAX_10K_FILING_AGE_DAYS:
        return "universe_gate_stale_10k"
    return None


# =============================================================================
# Percentile helper
# =============================================================================
def _percentiles(values: list[float | None], higher_is_better: bool) -> list[float]:
    """Return [0,1] percentile rank for each value. None -> 0.0."""
    n = len(values)
    if n == 0:
        return []
    indexed = [(i, v) for i, v in enumerate(values) if v is not None]
    if not indexed:
        return [0.0] * n

    indexed.sort(key=lambda t: t[1], reverse=higher_is_better)
    ranks = [0.0] * n
    m = len(indexed)
    for rank, (orig_idx, _v) in enumerate(indexed):
        # Highest gets ~1.0; lowest gets ~1/m
        ranks[orig_idx] = (m - rank) / m
    return ranks


# =============================================================================
# Helpers
# =============================================================================
def _extract_dividend_record(dividends: Any) -> dict[str, Any]:
    """Convert a DividendRecord dataclass or dict to a TypedDict-compatible dict.

    DividendHistoryFetcher returns a dataclass; the pick contract expects a dict
    with only the five TypedDict fields.  Passing the raw dataclass to
    isinstance(…, dict) always fails and produces an empty dividend_record.
    """
    if dividends is None:
        return {}
    if isinstance(dividends, dict):
        return dividends
    # Dataclass — extract only the TypedDict contract fields, skip None values.
    contract_fields = (
        "annual_yield", "payout_ratio", "consecutive_growth_years",
        "next_ex_div_date", "history_5y",
    )
    return {k: getattr(dividends, k) for k in contract_fields
            if getattr(dividends, k, None) is not None}


# =============================================================================
# ValueScreener facade
# =============================================================================
class ValueScreener:
    """Orchestrates universe-relative scoring + pick emission."""

    def __init__(
        self,
        fundamentals_fetcher: Any | None = None,
        earnings_fetcher: Any | None = None,
        dividends_fetcher: Any | None = None,
    ):
        self.fundamentals_fetcher = fundamentals_fetcher
        self.earnings_fetcher = earnings_fetcher
        self.dividends_fetcher = dividends_fetcher

    # ------------------------------------------------------------------
    def score_one(
        self,
        screener_input: ScreenerInput,
        prior_fundamentals: FundamentalsRecord | None = None,
        *,
        magic_pct: float = 0.5,
        acquirers_pct: float = 0.5,
        fcf_pct: float = 0.5,
        magic_formula_rank: int = 0,
    ) -> ScreenerScore:
        """Score a single ticker against absolute (non-universe) gates.

        Universe percentile-rank inputs default to 0.5 (neutral) if not provided.
        """
        rejection = _apply_universe_gates(screener_input)
        record = screener_input.fundamentals

        ratios = compute_ratios(record, market_cap=screener_input.market_cap,
                                share_price=screener_input.current_price)
        altman_z = ratios.get("altman_z_double_prime")
        roic = ratios.get("roic")
        d_to_e = ratios.get("debt_to_equity")
        acquirers_multiple = ratios.get("acquirers_multiple")

        piotroski_f = compute_piotroski_f_score(record, prior_fundamentals)
        beneish_m = compute_beneish_m_score(record, prior_fundamentals)
        d_to_e_score = compute_debt_to_equity_score(d_to_e)
        safety_gate_passed = compute_safety_gate(altman_z, beneish_m)

        value_comp = compute_value_composite(magic_pct, acquirers_pct, fcf_pct)
        quality_comp = compute_quality_composite(piotroski_f, roic, d_to_e_score)
        gate_mult = 1.0 if safety_gate_passed else 0.0
        total = (VALUE_WEIGHT * value_comp + QUALITY_WEIGHT * quality_comp) * gate_mult

        if rejection is None and not safety_gate_passed:
            rejection = "safety_gate_failed"

        return ScreenerScore(
            ticker=screener_input.ticker,
            total_score=total,
            value_composite=value_comp,
            quality_composite=quality_comp,
            safety_gate_passed=safety_gate_passed,
            universe_gate_passed=(_apply_universe_gates(screener_input) is None),
            piotroski_f=piotroski_f,
            magic_formula_rank=magic_formula_rank,
            acquirers_multiple=acquirers_multiple,
            altman_z_double_prime=altman_z,
            beneish_m=beneish_m,
            rejection_reason=rejection,
            extra={
                "roic": roic,
                "debt_to_equity": d_to_e,
                "fcf_yield": ratios.get("fcf_yield"),
                "magic_pct": magic_pct,
                "acquirers_pct": acquirers_pct,
                "fcf_pct": fcf_pct,
            },
        )

    # ------------------------------------------------------------------
    def screen_universe(
        self,
        inputs: list[ScreenerInput],
        top_n: int = 30,
        prior_fundamentals_map: dict[str, FundamentalsRecord] | None = None,
    ) -> list[dict[str, Any]]:
        """Compute universe-relative percentiles, then emit top_n picks via factory."""
        prior_map = prior_fundamentals_map or {}

        # First pass: compute ratios for all (non-rejected) candidates
        passing: list[ScreenerInput] = []
        passing_idx_map: dict[str, int] = {}
        for s in inputs:
            if _apply_universe_gates(s) is None:
                passing_idx_map[s.ticker] = len(passing)
                passing.append(s)

        # Universe arrays — only over passing candidates
        ratio_list: list[dict[str, float | None]] = []
        for s in passing:
            ratio_list.append(compute_ratios(s.fundamentals,
                                             market_cap=s.market_cap,
                                             share_price=s.current_price))

        earnings_yields = [r.get("earnings_yield") for r in ratio_list]
        roics = [r.get("roic") for r in ratio_list]
        acquirers = [r.get("acquirers_multiple") for r in ratio_list]
        fcf_yields = [r.get("fcf_yield") for r in ratio_list]

        # Magic Formula composite = earnings_yield (high better) + ROIC (high better).
        # We rank both, then sum ranks, then derive a percentile.
        ey_pct = _percentiles(earnings_yields, higher_is_better=True)
        roic_pct = _percentiles(roics, higher_is_better=True)
        mf_combined = [ey_pct[i] + roic_pct[i] for i in range(len(passing))]
        # Re-percentile combined Magic Formula scores
        mf_pct = _percentiles([float(x) for x in mf_combined], higher_is_better=True)
        # Magic Formula rank (1 = best)
        mf_order = sorted(range(len(passing)),
                          key=lambda i: mf_combined[i], reverse=True)
        mf_rank: dict[int, int] = {}
        for rank_pos, orig_idx in enumerate(mf_order, start=1):
            mf_rank[orig_idx] = rank_pos

        acq_pct = _percentiles(acquirers, higher_is_better=False)  # lower=cheaper
        fcf_pct = _percentiles(fcf_yields, higher_is_better=True)

        # Score each passing ticker
        scored: list[tuple[ScreenerScore, ScreenerInput]] = []
        for i, s in enumerate(passing):
            prior = prior_map.get(s.ticker)
            score = self.score_one(
                s,
                prior_fundamentals=prior,
                magic_pct=mf_pct[i],
                acquirers_pct=acq_pct[i],
                fcf_pct=fcf_pct[i],
                magic_formula_rank=mf_rank[i],
            )
            scored.append((score, s))

        # Also score (and reject) the universe-failures so callers can audit.
        # Excluded from final picks since rejection_reason is set.
        for s in inputs:
            if s.ticker not in passing_idx_map:
                # No universe stats — give neutral 0.5 for percentiles.
                _ = self.score_one(s, prior_fundamentals=prior_map.get(s.ticker))

        # Filter for safety + universe + take top_n
        eligible = [(sc, si) for sc, si in scored
                    if sc.safety_gate_passed
                    and sc.universe_gate_passed
                    and sc.rejection_reason is None]
        eligible.sort(key=lambda t: t[0].total_score, reverse=True)
        eligible = eligible[:top_n]

        picks: list[dict[str, Any]] = []
        n_universe = max(1, len(passing))
        # Decile-based intrinsic value multiplier
        for rank_pos, (sc, si) in enumerate(eligible, start=1):
            decile = max(1, math.ceil(rank_pos / max(1, len(eligible) / 10.0)))
            iv_mult = max(1.0, 1.5 - (decile - 1) * 0.05)  # 1.5x, 1.45x, 1.4x...
            intrinsic_value = iv_mult * si.current_price

            thesis = (
                f"Magic Formula rank {sc.magic_formula_rank} of {n_universe}; "
                f"F-score={sc.piotroski_f}/9; "
                f"Acquirer's Multiple {self._fmt(sc.acquirers_multiple)}; "
                f"ROIC {self._fmt_pct(sc.extra.get('roic'))}; "
                f"Altman Z''={self._fmt(sc.altman_z_double_prime)}; "
                f"Beneish M={self._fmt(sc.beneish_m)}"
            )

            roic_val = sc.extra.get("roic")
            d_to_e_val = sc.extra.get("debt_to_equity")
            roic_break = (roic_val * 0.7) if isinstance(roic_val, (int, float)) else 0.0
            d_to_e_break = ((d_to_e_val or 0.0) * 1.5) if isinstance(d_to_e_val, (int, float)) else 1.0

            thesis_break_rules = [
                {"metric": "ROIC", "op": "<", "threshold": float(roic_break),
                 "source": "value_screener"},
                {"metric": "DebtToEquity", "op": ">", "threshold": float(d_to_e_break),
                 "source": "value_screener"},
                {"metric": "AltmanZDoublePrime", "op": "<",
                 "threshold": float(ALTMAN_Z_DOUBLE_PRIME_MIN),
                 "source": "value_screener"},
            ]

            fundamental_snapshot = {
                "roic": roic_val,
                "fcf_yield": sc.extra.get("fcf_yield"),
                "debt_to_equity": d_to_e_val,
                "piotroski_f": sc.piotroski_f,
                "magic_formula_rank": sc.magic_formula_rank,
                "acquirers_multiple": sc.acquirers_multiple,
                "altman_z_double_prime": sc.altman_z_double_prime,
                "beneish_m": sc.beneish_m,
            }

            earnings_history: list[dict[str, Any]] = []
            next_earnings_date = None
            if si.earnings is not None:
                earnings_history = list(getattr(si.earnings, "history", []) or [])
                next_earnings_date = getattr(si.earnings, "next_earnings_date", None)

            dividend_record = _extract_dividend_record(si.dividends)
            catalyst_dates = [next_earnings_date] if next_earnings_date else []

            pick = make_long_term_value_pick(
                symbol=si.ticker,
                direction="LONG",
                entry_price=si.current_price,
                intrinsic_value=intrinsic_value,
                thesis=thesis,
                thesis_break_rules=thesis_break_rules,
                fundamental_snapshot=fundamental_snapshot,
                earnings_history=earnings_history,
                next_earnings_date=next_earnings_date,
                dividend_record=dividend_record,
                catalyst_dates=catalyst_dates,
                score=sc.total_score,
                universe_gate_passed=True,
                safety_gate_passed=True,
                extra={
                    "value_composite": sc.value_composite,
                    "quality_composite": sc.quality_composite,
                    "rank": rank_pos,
                },
            )
            picks.append(pick)
        return picks

    @staticmethod
    def _fmt(v: Any) -> str:
        if v is None:
            return "n/a"
        try:
            return f"{float(v):.2f}"
        except (TypeError, ValueError):
            return str(v)

    @staticmethod
    def _fmt_pct(v: Any) -> str:
        if v is None:
            return "n/a"
        try:
            return f"{float(v) * 100:.1f}%"
        except (TypeError, ValueError):
            return str(v)
