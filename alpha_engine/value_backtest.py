"""Walk-forward backtest harness for long-term value picks — Phase 13 of UEPS.

Opt-in sidecar (per CLAUDE.md Wire-Up Rule). Wiring plan: Phase 14 GHA
`value_backtest_quarterly.yml` runs full 13y window monthly; this module is
the harness.

Design constraints (locked in
`updates/long_term_value_project_2026-04-27/findings/SYNTHESIS.md` § 9 and § 7):

    Window:       2012-2025 (~13y EDGAR XBRL coverage)
    Sleeves:      4 overlapping quarterly cohorts → ~52 quarters × ~50 picks
                  ≈ 2600 picks per regime → comfortable n≥100 per regime band
    Train:        2012-2018
    Validate:     2019-2021
    Test:         2022-2025
    Discipline:   walk-forward only, no in-sample peeking
                    - on rebalance date T, fundamentals MUST have
                      period_end ≤ T - 90d (90-day SEC reporting lag floor)
                    - on rebalance date T, prices MUST be from T-1 or earlier
                    - exit decisions use prices through exit_date inclusive

Tier classification — aligned with CLAUDE.md MAJOR GOAL #1 + SYNTHESIS § 7:

    Tier 1 ("Renaissance-grade"):  PF ≥ 2.0  AND  WR ≥ 55%  AND  MaxDD ≤ 10%
    Tier 2 (size-up floor):        PF ≥ 1.5  AND  WR ≥ 50%  AND  MaxDD ≤ 20%
    Tier 3 (acceptable):           PF ≥ 1.2  AND  WR ≥ 45%  AND  MaxDD ≤ 30%
    below: anything else, OR n < 100 (n-floor governs all tier claims)

The harness is pure-orchestration. It accepts caller-provided
`fundamentals_history_provider(ticker, as_of_date)` and
`prices_history_provider(ticker, start_date, end_date)` so the backtest can
be driven against EDGAR + yfinance in production OR against synthetic data
in tests. The harness DOES NOT validate the providers' walk-forward
discipline; the providers own that contract, and tests assert the harness
calls them correctly.

This module is intentionally stdlib-only (plus the UEPS modules already
built) so it runs unchanged in the GHA workflow without numpy/pandas.

Phase 2 (`alpha_engine.long_term_pick_contract`) is not yet merged on `main`
at the time of writing, so the two helpers we need (`is_long_term_value`,
`evaluate_thesis_break`) are inlined below — they match the contract
documented in SYNTHESIS § 4 verbatim. When Phase 2 lands, swap the inline
helpers for the imports without touching call-sites.
"""
from __future__ import annotations

import logging
import math
import statistics
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Literal, Protocol

logger = logging.getLogger(__name__)


# ── Inline pick-contract helpers (decouple from Phase 2) ─────────────────────


def _is_long_term_value(pick: dict[str, Any]) -> bool:
    """True if this is a `pick_type=long_term_value` pick (per SYNTHESIS § 4)."""
    return pick.get("pick_type") == "long_term_value"


_THESIS_BREAK_OPS = {
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "==": lambda a, b: a == b,
}


def _evaluate_thesis_break(
    pick: dict[str, Any],
    current_metrics: dict[str, float],
) -> tuple[bool, list[str]]:
    """Same contract as `long_term_pick_contract.evaluate_thesis_break`.

    Returns (broken, [triggered_rule_descriptions]). A pick with no
    thesis_break_rules or no current_metrics returns (False, []) — the
    backtest never spuriously closes on missing data.
    """
    if not _is_long_term_value(pick):
        return (False, [])
    rules = pick.get("thesis_break_rules") or []
    if not isinstance(rules, list) or not rules:
        return (False, [])
    triggered: list[str] = []
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        metric = rule.get("metric")
        op = rule.get("op")
        threshold = rule.get("threshold")
        if metric is None or op is None or threshold is None:
            continue
        current = current_metrics.get(metric)
        if current is None:
            continue
        check = _THESIS_BREAK_OPS.get(op)
        if check is None:
            continue
        try:
            if check(float(current), float(threshold)):
                triggered.append(f"{metric} {op} {threshold} (current={current})")
        except (TypeError, ValueError):
            continue
    return (len(triggered) > 0, triggered)


# ── Tier thresholds (locked, see module docstring) ───────────────────────────

TIER_1_PF_MIN = 2.0
TIER_1_WR_MIN = 0.55
TIER_1_MAX_DD = 0.10

TIER_2_PF_MIN = 1.5
TIER_2_WR_MIN = 0.50
TIER_2_MAX_DD = 0.20

TIER_3_PF_MIN = 1.2
TIER_3_WR_MIN = 0.45
TIER_3_MAX_DD = 0.30

# CLAUDE.md MAJOR GOAL #1 n-floor: never label any band a "tier" without
# n≥100 clean trades.
TIER_N_FLOOR = 100

# Profit-factor sentinel for "all wins, no losses" (avoids float('inf') so the
# value serializes cleanly through JSON / parquet downstream).
PF_NO_LOSSES_SENTINEL = 999.0

# Trading-day annualization factor for daily returns.
TRADING_DAYS_PER_YEAR = 252

# Reporting lag floor (days) — fundamentals must be at least this old to use
# at rebalance time (no look-ahead via not-yet-filed financials).
DEFAULT_REPORTING_LAG_DAYS = 90

TierLabel = Literal["Tier 1", "Tier 2", "Tier 3", "below"]


# ── Provider protocols ───────────────────────────────────────────────────────


class FundamentalsHistoryProvider(Protocol):
    """Caller-provided: returns the fundamentals snapshot AS OF a given date.

    Implementations MUST enforce walk-forward discipline themselves —
    `as_of_date` is the rebalance date minus the reporting-lag floor. The
    provider returns whatever fundamentals had `period_end ≤ as_of_date`
    (i.e. were filed and visible to a real-time investor on `as_of_date`).
    Returning None means "no fundamentals visible yet for this ticker".
    """

    def __call__(self, ticker: str, as_of_date: date) -> Any | None: ...


class PricesHistoryProvider(Protocol):
    """Caller-provided: returns OHLCV close history within an inclusive window.

    Implementations MUST enforce walk-forward discipline — never return data
    after `end_date`. Output is `[(date, close_price), …]` sorted ascending.
    Empty list ⇒ no price history (pick will be skipped).
    """

    def __call__(
        self, ticker: str, start_date: date, end_date: date
    ) -> list[tuple[date, float]]: ...


class _ScreenerLike(Protocol):
    """Anything with the `screen_universe(inputs, top_n=…)` shape used by
    Phase 6.

    The harness only requires the method exists and returns a list of
    pick-shaped dicts. We do NOT import ValueScreener directly so tests can
    inject a stub without bringing the full dependency.
    """

    def screen_universe(
        self, inputs: list[Any], top_n: int = ...
    ) -> list[dict[str, Any]]: ...


# ── Sleeve + result dataclasses ──────────────────────────────────────────────


@dataclass
class BacktestSleeve:
    """One overlapping cohort of the 4-sleeve walk-forward.

    Sleeves are offset by approximately rebalance_freq_days/4 so the four
    cohorts together produce ~one fresh rebalance per (rebalance_freq_days/4)
    business days, smoothing the equity curve and producing 4× the closed-pick
    sample size for Tier classification.
    """

    name: str
    start_date: str  # ISO YYYY-MM-DD
    end_date: str
    rebalance_freq_days: int = 90
    picks_per_rebalance: int = 25


@dataclass
class BacktestResult:
    """Comprehensive metrics — every field needed for SYNTHESIS § 7 tier gates.

    `closed_picks` carries the full audit trail (one dict per realized pick).
    Each entry is shaped:
        {
          "ticker": str,
          "entry_date": "YYYY-MM-DD",
          "exit_date": "YYYY-MM-DD",
          "entry_price": float,
          "exit_price": float,
          "realized_pnl_pct": float,   # fractional, 0.10 = +10%
          "exit_reason": str,          # one of: "thesis_break" | "rebalance"
                                       #   | "horizon" | "end_of_window"
        }
    """

    sleeve_name: str
    total_picks: int
    wins: int
    losses: int
    wr: float
    pf: float
    cagr: float
    max_dd: float
    sharpe: float
    sortino: float
    calmar: float
    tier_classification: TierLabel
    closed_picks: list[dict[str, Any]] = field(default_factory=list)


# ── Pure-function metric calculators (testable in isolation) ─────────────────


def compute_wr(wins: int, losses: int) -> float:
    """Win rate as a fraction in [0, 1].

    Defensive: returns 0.0 if (wins+losses) == 0 rather than raising. Per
    SYNTHESIS § 7, an empty cohort is "below tier" — not an error.
    """
    total = wins + losses
    if total <= 0:
        return 0.0
    return wins / total


def compute_pf(profits: list[float], losses: list[float]) -> float:
    """Profit factor = sum(profits) / |sum(losses)|.

    Behavior:
      - profits empty AND losses empty → 0.0 (no trades, no factor)
      - losses empty (all wins)        → PF_NO_LOSSES_SENTINEL (=999.0). We
        use a sentinel rather than float('inf') so the value serializes
        cleanly through JSON/parquet downstream and so the Tier-1 PF check
        (≥ 2.0) trivially passes.
      - profits empty (all losses)     → 0.0
      - both present                   → sum(profits) / abs(sum(losses))

    `losses` is expected to contain NEGATIVE numbers (the realized pnl of
    losing trades). We take `abs(sum(losses))` to be robust either way.
    """
    if not profits and not losses:
        return 0.0
    if not losses:
        return PF_NO_LOSSES_SENTINEL
    if not profits:
        return 0.0
    total_profit = sum(profits)
    total_loss = abs(sum(losses))
    if total_loss == 0:
        # Degenerate: losses non-empty but all zeros (no real loss).
        return PF_NO_LOSSES_SENTINEL
    return total_profit / total_loss


def compute_cagr(start_value: float, end_value: float, years: float) -> float:
    """Compound annual growth rate.

    CAGR = (end/start)^(1/years) − 1.

    Defensive: returns 0.0 if start_value <= 0 or years <= 0. Returns -1.0
    (a -100% wipe) if end_value <= 0 with valid inputs (practical floor —
    math blows up for negative bases on fractional powers).
    """
    if start_value <= 0 or years <= 0:
        return 0.0
    if end_value <= 0:
        return -1.0
    return (end_value / start_value) ** (1.0 / years) - 1.0


def compute_max_dd(equity_curve: list[float]) -> float:
    """Max drawdown as a positive fraction of the peak.

    Walks the curve tracking the running peak; reports the largest
    (peak - trough) / peak observed. A monotonically non-decreasing curve
    returns 0.0. An empty curve returns 0.0.
    """
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for value in equity_curve:
        if value > peak:
            peak = value
        if peak > 0:
            dd = (peak - value) / peak
            if dd > max_dd:
                max_dd = dd
    return max_dd


def compute_sharpe(
    daily_returns: list[float], risk_free_rate: float = 0.0
) -> float:
    """Annualized Sharpe ratio: (mean(r) - rf) / std(r) * sqrt(252).

    `risk_free_rate` is interpreted as the DAILY risk-free rate (caller
    converts annual → daily if needed). Returns 0.0 for sample size < 2 or
    zero standard deviation (no volatility → no measurable risk-adjusted
    edge).
    """
    if len(daily_returns) < 2:
        return 0.0
    excess = [r - risk_free_rate for r in daily_returns]
    mean_excess = statistics.mean(excess)
    try:
        std_excess = statistics.stdev(excess)
    except statistics.StatisticsError:
        return 0.0
    if std_excess == 0:
        return 0.0
    return (mean_excess / std_excess) * math.sqrt(TRADING_DAYS_PER_YEAR)


def compute_sortino(
    daily_returns: list[float], risk_free_rate: float = 0.0
) -> float:
    """Annualized Sortino: (mean(r) - rf) / downside_std(r) * sqrt(252).

    Downside standard deviation only counts NEGATIVE excess returns (the
    deviations of returns below the risk-free rate). This is the canonical
    Sortino — it does not penalize upside volatility.

    Returns 0.0 if all returns are above the risk-free rate (no downside
    samples) — a degenerate "infinitely good" signal that we do not
    promote to inf, since callers downstream multiply / classify this.
    """
    if len(daily_returns) < 2:
        return 0.0
    excess = [r - risk_free_rate for r in daily_returns]
    mean_excess = statistics.mean(excess)
    downside = [r for r in excess if r < 0]
    if len(downside) < 2:
        return 0.0
    # Lower partial moment (Bloomberg-style) downside deviation:
    # sqrt(mean(downside_r^2)). Some references use sample stdev of
    # negatives only; we use the more standard form so this matches
    # hedge-fund usage downstream.
    sum_sq = sum(r * r for r in downside)
    downside_dev = math.sqrt(sum_sq / len(downside))
    if downside_dev == 0:
        return 0.0
    return (mean_excess / downside_dev) * math.sqrt(TRADING_DAYS_PER_YEAR)


def compute_calmar(cagr: float, max_dd: float) -> float:
    """Calmar = CAGR / MaxDD.

    Convention: max_dd is a positive fraction (e.g. 0.20 = 20% drawdown).
    Returns 0.0 if max_dd <= 0 (no drawdown observed → undefined / very
    high; we choose 0.0 over inf for serialization safety).
    """
    if max_dd <= 0:
        return 0.0
    return cagr / max_dd


def classify_tier(wr: float, pf: float, max_dd: float, n: int) -> TierLabel:
    """Classify a backtest result into Tier 1 / 2 / 3 / below.

    Per CLAUDE.md MAJOR GOAL #1 + SYNTHESIS § 7:
      - n < 100 → "below" regardless of metrics (the n-floor governs all
        tier claims; this prevents low-sample noise from masquerading as
        edge).
      - Tier 1: PF ≥ 2.0  AND  WR ≥ 0.55  AND  MaxDD ≤ 0.10
      - Tier 2: PF ≥ 1.5  AND  WR ≥ 0.50  AND  MaxDD ≤ 0.20
      - Tier 3: PF ≥ 1.2  AND  WR ≥ 0.45  AND  MaxDD ≤ 0.30
      - else:   "below"
    """
    if n < TIER_N_FLOOR:
        return "below"
    if (
        pf >= TIER_1_PF_MIN
        and wr >= TIER_1_WR_MIN
        and max_dd <= TIER_1_MAX_DD
    ):
        return "Tier 1"
    if (
        pf >= TIER_2_PF_MIN
        and wr >= TIER_2_WR_MIN
        and max_dd <= TIER_2_MAX_DD
    ):
        return "Tier 2"
    if (
        pf >= TIER_3_PF_MIN
        and wr >= TIER_3_WR_MIN
        and max_dd <= TIER_3_MAX_DD
    ):
        return "Tier 3"
    return "below"


# ── Date helpers (stdlib only; no pandas) ────────────────────────────────────


def _to_date(value: str | date | datetime) -> date:
    """Coerce ISO string / date / datetime → date. Strict on bad inputs."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        s = value.strip()
        if s.endswith("Z"):
            s = s[:-1]
        try:
            return datetime.fromisoformat(s).date()
        except ValueError:
            return datetime.strptime(s[:10], "%Y-%m-%d").date()
    raise TypeError(f"Cannot coerce {type(value).__name__} to date: {value!r}")


def _rebalance_dates(sleeve: BacktestSleeve) -> list[date]:
    """Generate the rebalance schedule for a sleeve (inclusive of start)."""
    start = _to_date(sleeve.start_date)
    end = _to_date(sleeve.end_date)
    if end < start:
        return []
    out: list[date] = []
    cur = start
    step = timedelta(days=sleeve.rebalance_freq_days)
    while cur <= end:
        out.append(cur)
        cur = cur + step
    return out


def _years_between(start: date, end: date) -> float:
    return max(0.0, (end - start).days / 365.25)


# ── Walk-forward backtest ────────────────────────────────────────────────────


class WalkForwardBacktest:
    """Orchestrates walk-forward backtest of long-term value picks.

    Walk-forward discipline is enforced via the two provider callables:

      * `fundamentals_history_provider(ticker, as_of_date)` — must return
        the snapshot visible AS OF `as_of_date` (i.e. period_end ≤ that
        date). The harness ALWAYS calls this with
        `rebalance_date - reporting_lag_days` so callers see the 90-day
        filing lag floor without having to compute it.

      * `prices_history_provider(ticker, start_date, end_date)` — must
        return OHLCV close data in [start_date, end_date] inclusive.
        Harness reads prices for entry, periodic thesis-break checks, and
        exit (the exit price is taken from the LATEST date ≤ exit_date
        inclusive — same-day close is OK because exit is a decision IN the
        future during simulation).

    Construction:
        backtest = WalkForwardBacktest(
            screener=ValueScreener(),
            fundamentals_history_provider=my_edgar_provider,
            prices_history_provider=my_yfinance_provider,
        )
        result = backtest.run_sleeve(sleeve, universe=["AAPL", "MSFT", ...])

    The harness does not run the full universe screening internally — it
    delegates ticker selection to the provided screener. For backtests, the
    screener is typically a thin wrapper that builds `ScreenerInput`s from
    the walk-forward fundamentals snapshot.
    """

    def __init__(
        self,
        screener: _ScreenerLike,
        fundamentals_history_provider: FundamentalsHistoryProvider,
        prices_history_provider: PricesHistoryProvider,
        *,
        starting_capital: float = 1.0,
        reporting_lag_days: int = DEFAULT_REPORTING_LAG_DAYS,
        max_holding_days: int = 1095,  # 3y, matches "3y+" horizon
    ):
        if reporting_lag_days < 0:
            raise ValueError("reporting_lag_days must be >= 0")
        if starting_capital <= 0:
            raise ValueError("starting_capital must be > 0")
        self.screener = screener
        self.fundamentals_history_provider = fundamentals_history_provider
        self.prices_history_provider = prices_history_provider
        self.starting_capital = float(starting_capital)
        self.reporting_lag_days = reporting_lag_days
        self.max_holding_days = max_holding_days

    # ── Public API ────────────────────────────────────────────────────────────

    def run_sleeve(
        self, sleeve: BacktestSleeve, universe: list[str]
    ) -> BacktestResult:
        """Run the full walk-forward simulation for one sleeve.

        Steps per rebalance window [T_i, T_{i+1}]:
          1. as_of = T_i - reporting_lag_days
          2. For each ticker in `universe`, ask
             `fundamentals_history_provider(ticker, as_of)` → snapshot.
             Skip tickers with no snapshot (NOT visible yet on T_i).
          3. Build a thin ScreenerInput list from those snapshots and call
             `screener.screen_universe(inputs, top_n=picks_per_rebalance)`.
          4. For each emitted pick, set entry_price = close on T_i (from
             prices provider). If no price on T_i, skip the pick.
          5. Hold until exit:
             - thesis-break on any future date (via `_evaluate_thesis_break`
               using next-rebalance fundamentals snapshot for refresh)
             - rebalance at T_{i+1}
             - max_holding_days hard cap
             - end_of_window if T_{i+1} > sleeve.end_date
          6. Realize pnl_pct = (exit - entry) / entry, sign-flipped for
             SHORT. Update equity curve.

        Returns a `BacktestResult` with full metrics + closed-picks audit
        trail.
        """
        rebalance_dates = _rebalance_dates(sleeve)
        sleeve_end = _to_date(sleeve.end_date)
        equity = self.starting_capital
        # Equity curve sampled at each rebalance + final exit. Adequate for
        # max_dd / Sharpe at the rebalance-sample frequency. Phase 14 GHA
        # can plug in a finer daily resampler when running the full 13y
        # window.
        equity_curve: list[float] = [equity]
        closed_picks: list[dict[str, Any]] = []
        wins = 0
        losses = 0
        profits: list[float] = []
        loss_pnls: list[float] = []

        for i, rebalance_date in enumerate(rebalance_dates):
            as_of = rebalance_date - timedelta(days=self.reporting_lag_days)
            if i + 1 < len(rebalance_dates):
                next_rebalance = rebalance_dates[i + 1]
            else:
                next_rebalance = sleeve_end + timedelta(days=1)

            picks = self._screen_at_rebalance(
                universe=universe,
                as_of=as_of,
                top_n=sleeve.picks_per_rebalance,
            )
            if not picks:
                continue

            # Equal-weight allocate the current equity across this
            # rebalance's picks. Each pick gets `slot_capital`; we do NOT
            # reinvest realized pnl back into still-open picks within the
            # same rebalance window (closed first, then sleeve-level equity
            # is updated for the next rebalance).
            n_picks = len(picks)
            slot_capital = equity / n_picks
            window_realized = 0.0

            for pick in picks:
                closed = self._simulate_hold(
                    pick=pick,
                    entry_date=rebalance_date,
                    rebalance_end=next_rebalance,
                    sleeve_end=sleeve_end,
                )
                if closed is None:
                    # Could not enter (no price at entry); slot returns 0.
                    window_realized += 0.0
                    continue
                pnl_pct = closed["realized_pnl_pct"]
                slot_pnl = slot_capital * pnl_pct
                window_realized += slot_pnl
                if pnl_pct > 0:
                    wins += 1
                    profits.append(slot_pnl)
                elif pnl_pct < 0:
                    losses += 1
                    loss_pnls.append(slot_pnl)
                # pnl_pct == 0 → counted as neither win nor loss
                closed_picks.append(closed)

            equity = equity + window_realized
            equity_curve.append(equity)

        # ── Metrics ─────────────────────────────────────────────────────────
        total_picks = wins + losses
        wr = compute_wr(wins, losses)
        pf = compute_pf(profits, loss_pnls)

        years = _years_between(_to_date(sleeve.start_date), sleeve_end)
        cagr = compute_cagr(self.starting_capital, equity, years)

        max_dd = compute_max_dd(equity_curve)
        # Period-over-period returns on the (rebalance-sampled) curve.
        rebalance_returns = _curve_to_returns(equity_curve)
        sharpe = compute_sharpe(rebalance_returns)
        sortino = compute_sortino(rebalance_returns)
        calmar = compute_calmar(cagr, max_dd)

        tier = classify_tier(wr=wr, pf=pf, max_dd=max_dd, n=total_picks)

        return BacktestResult(
            sleeve_name=sleeve.name,
            total_picks=total_picks,
            wins=wins,
            losses=losses,
            wr=wr,
            pf=pf,
            cagr=cagr,
            max_dd=max_dd,
            sharpe=sharpe,
            sortino=sortino,
            calmar=calmar,
            tier_classification=tier,
            closed_picks=closed_picks,
        )

    def run_all_sleeves(
        self, sleeves: list[BacktestSleeve], universe: list[str]
    ) -> dict[str, BacktestResult]:
        """Run every sleeve sequentially, returning {sleeve_name: result}."""
        out: dict[str, BacktestResult] = {}
        for sleeve in sleeves:
            out[sleeve.name] = self.run_sleeve(sleeve, universe)
        return out

    # ── Internals ─────────────────────────────────────────────────────────────

    def _screen_at_rebalance(
        self,
        *,
        universe: list[str],
        as_of: date,
        top_n: int,
    ) -> list[dict[str, Any]]:
        """Pull walk-forward fundamentals for every ticker, then call screener.

        We delegate the construction of `ScreenerInput`-shaped objects to
        whatever container the `fundamentals_history_provider` returns. The
        screener stub in tests can accept the raw dicts; in production the
        provider produces real `ScreenerInput`s.
        """
        inputs: list[Any] = []
        for ticker in universe:
            snapshot = self.fundamentals_history_provider(ticker, as_of)
            if snapshot is None:
                continue
            inputs.append(snapshot)
        if not inputs:
            return []
        return list(self.screener.screen_universe(inputs, top_n=top_n))

    def _simulate_hold(
        self,
        *,
        pick: dict[str, Any],
        entry_date: date,
        rebalance_end: date,
        sleeve_end: date,
    ) -> dict[str, Any] | None:
        """Simulate one held position. Returns the closed-pick audit dict.

        Exit precedence (mirrors thesis_resolver.py):
            1. thesis_break  — fundamentals deteriorate during the hold
            2. rebalance     — the next quarterly cycle fires
            3. horizon       — `max_holding_days` hard cap (handles
                                 single-rebalance and end-of-data cases)
            4. end_of_window — sleeve.end_date reached without other exit

        Returns None if entry_date is missing from the price provider — the
        pick simply isn't entered (mirrors a real trade-day with no fill).
        """
        ticker = pick.get("symbol", "")
        direction = (pick.get("direction") or "LONG").upper()

        # Hard cap the price-fetch window: never read past the sleeve end OR
        # the next rebalance OR the max-holding horizon.
        horizon_end = entry_date + timedelta(days=self.max_holding_days)
        # rebalance_end is exclusive of the next rebalance day in our
        # convention (we re-enter at that day); back off by one to make it
        # inclusive.
        rebalance_last = rebalance_end - timedelta(days=1)
        window_end = min(sleeve_end, rebalance_last, horizon_end)
        if window_end < entry_date:
            return None

        history = self.prices_history_provider(ticker, entry_date, window_end)
        if not history:
            return None

        entry_idx = 0
        entry_price = float(history[entry_idx][1])
        if entry_price <= 0:
            return None

        # Walk forward, periodically refreshing fundamentals to evaluate
        # thesis-break rules. Refresh frequency = once per
        # `_thesis_break_check_period_days` rows in the price history (≈ that
        # many calendar days for daily series; tests can shrink this).
        check_period = max(1, self._thesis_break_check_period_days)
        exit_idx: int | None = None
        exit_reason = "rebalance"
        last_idx = len(history) - 1

        # Only run thesis-break checks for long_term_value picks — others
        # fall through to rebalance / horizon / end_of_window.
        check_thesis = _is_long_term_value(pick)

        if check_thesis:
            for j in range(entry_idx + check_period, last_idx + 1, check_period):
                check_date = history[j][0]
                # Walk-forward refresh: as_of = check_date - reporting_lag.
                as_of = check_date - timedelta(days=self.reporting_lag_days)
                refresh = self.fundamentals_history_provider(ticker, as_of)
                if refresh is None:
                    continue
                metrics = _extract_metrics_for_thesis_break(refresh)
                if not metrics:
                    continue
                broken, _ = _evaluate_thesis_break(pick, metrics)
                if broken:
                    exit_idx = j
                    exit_reason = "thesis_break"
                    break

        if exit_idx is None:
            # Decide between rebalance / horizon / end_of_window by which
            # window-end constraint we hit.
            exit_idx = last_idx
            final_date = history[exit_idx][0]
            if final_date >= horizon_end - timedelta(days=1):
                exit_reason = "horizon"
            elif final_date >= sleeve_end - timedelta(days=1):
                exit_reason = "end_of_window"
            else:
                exit_reason = "rebalance"

        exit_date = history[exit_idx][0]
        exit_price = float(history[exit_idx][1])

        # PnL: long = (exit - entry)/entry; short = (entry - exit)/entry.
        if direction == "SHORT":
            pnl_pct = (entry_price - exit_price) / entry_price
        else:
            pnl_pct = (exit_price - entry_price) / entry_price

        return {
            "ticker": ticker,
            "entry_date": entry_date.isoformat(),
            "exit_date": (
                exit_date.isoformat() if isinstance(exit_date, date)
                else str(exit_date)
            ),
            "entry_price": entry_price,
            "exit_price": exit_price,
            "realized_pnl_pct": float(pnl_pct),
            "exit_reason": exit_reason,
        }

    # Override-point for tests: how often (in rows of the price series) we
    # re-evaluate thesis-break rules during the hold. Default 30 rows ≈ ~6
    # weeks at daily cadence.
    _thesis_break_check_period_days: int = 30


# ── Helpers ──────────────────────────────────────────────────────────────────


def _curve_to_returns(equity_curve: list[float]) -> list[float]:
    """Period-over-period returns of an equity curve.

    len(returns) = len(curve) - 1.
    """
    returns: list[float] = []
    for prev, cur in zip(equity_curve, equity_curve[1:]):
        if prev == 0:
            returns.append(0.0)
        else:
            returns.append((cur - prev) / prev)
    return returns


def _extract_metrics_for_thesis_break(snapshot: Any) -> dict[str, float]:
    """Best-effort extraction of metrics for `_evaluate_thesis_break`.

    Accepts:
      - dict with `metrics` key
      - object with `.ratios` attribute (FundamentalsRecord-shaped)
      - object with `.metrics` attribute
      - bare dict mapping metric→value
    Returns {} when nothing usable is present (caller treats as "no break").
    """
    if snapshot is None:
        return {}
    if isinstance(snapshot, dict):
        metrics = snapshot.get("metrics") or snapshot.get("ratios") or snapshot
        if isinstance(metrics, dict):
            return {
                k: float(v) for k, v in metrics.items()
                if isinstance(v, (int, float))
            }
        return {}
    ratios = getattr(snapshot, "ratios", None)
    if isinstance(ratios, dict):
        return {
            k: float(v) for k, v in ratios.items()
            if isinstance(v, (int, float))
        }
    metrics = getattr(snapshot, "metrics", None)
    if isinstance(metrics, dict):
        return {
            k: float(v) for k, v in metrics.items()
            if isinstance(v, (int, float))
        }
    return {}


__all__ = [
    "BacktestSleeve",
    "BacktestResult",
    "WalkForwardBacktest",
    "FundamentalsHistoryProvider",
    "PricesHistoryProvider",
    "compute_wr",
    "compute_pf",
    "compute_cagr",
    "compute_max_dd",
    "compute_sharpe",
    "compute_sortino",
    "compute_calmar",
    "classify_tier",
    "PF_NO_LOSSES_SENTINEL",
    "TIER_N_FLOOR",
    "DEFAULT_REPORTING_LAG_DAYS",
]
