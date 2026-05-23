"""Pick contract extensions for long-term value and swing pick types.

Opt-in sidecar (per CLAUDE.md Wire-Up Rule). No production caller in this commit.
Wiring plan: Phase 6 `value_screener.py` and Phase 7 `swing_screener.py` will
construct picks via these factory functions. Existing pipelines are untouched —
all new fields are additive and nullable.

Project context: updates/long_term_value_project_2026-04-27/PROJECT.md
Synthesis lock: updates/long_term_value_project_2026-04-27/findings/SYNTHESIS.md §4
"""
from __future__ import annotations

from typing import Any, Literal, TypedDict

PickType = Literal["scalp", "intraday", "swing", "position", "long_term_value"]
HoldingHorizon = Literal["1d", "1w", "1m", "3m", "1y", "3y+"]
ExitMode = Literal["tp_sl", "thesis", "calendar", "trail"]


class ThesisBreakRule(TypedDict):
    metric: str
    op: Literal["<", "<=", ">", ">=", "=="]
    threshold: float
    source: str


class FundamentalSnapshot(TypedDict, total=False):
    pe: float
    pb: float
    ev_ebitda: float
    roic: float
    roe: float
    fcf_yield: float
    debt_to_equity: float
    interest_coverage: float
    piotroski_f: int
    magic_formula_rank: int
    acquirers_multiple: float
    altman_z_double_prime: float
    beneish_m: float
    sloan_accruals_decile: int


class EarningsRow(TypedDict):
    date: str
    eps_actual: float | None
    eps_estimate: float | None
    surprise_pct: float | None


class DividendEvent(TypedDict):
    ex_date: str
    amount: float


class DividendRecord(TypedDict, total=False):
    annual_yield: float
    payout_ratio: float
    consecutive_growth_years: int
    next_ex_div_date: str | None
    history_5y: list[DividendEvent]


class LongTermPickExtensions(TypedDict, total=False):
    """Fields added to the existing pick dict for long-term and swing picks.

    All fields are optional — old picks remain valid by simply not having them.
    """
    pick_type: PickType
    holding_horizon: HoldingHorizon
    exit_mode: ExitMode
    thesis: str
    thesis_break_rules: list[ThesisBreakRule]
    intrinsic_value: float | None
    fundamental_snapshot: FundamentalSnapshot
    earnings_history: list[EarningsRow]
    next_earnings_date: str | None
    dividend_record: DividendRecord
    catalyst_dates: list[str]
    universe_gate_passed: bool
    safety_gate_passed: bool


def make_long_term_value_pick(
    *,
    symbol: str,
    direction: str,
    entry_price: float,
    intrinsic_value: float,
    thesis: str,
    thesis_break_rules: list[ThesisBreakRule],
    fundamental_snapshot: FundamentalSnapshot,
    earnings_history: list[EarningsRow],
    next_earnings_date: str | None,
    dividend_record: DividendRecord,
    catalyst_dates: list[str],
    holding_horizon: HoldingHorizon = "3y+",
    asset_class: str = "EQUITY",
    source_system: str = "value_screener",
    strategy: str = "magic_formula_x_piotroski_x_acquirers",
    score: float | None = None,
    confidence: float | None = None,
    universe_gate_passed: bool = True,
    safety_gate_passed: bool = True,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Construct a `long_term_value` pick conforming to SYNTHESIS.md §4.

    Required invariants enforced:
    - thesis non-empty
    - at least one thesis_break_rule
    - intrinsic_value > 0
    - safety_gate_passed = True (otherwise the screener should have rejected upstream)
    """
    if not thesis.strip():
        raise ValueError("long_term_value pick requires non-empty thesis")
    if not thesis_break_rules:
        raise ValueError("long_term_value pick requires at least one thesis_break_rule")
    if intrinsic_value is None or intrinsic_value <= 0:
        raise ValueError("long_term_value pick requires intrinsic_value > 0")
    if not safety_gate_passed:
        raise ValueError(
            "long_term_value pick requires safety_gate_passed=True (Altman Z'' >= 1.10 AND Beneish M <= -1.78)"
        )

    pick: dict[str, Any] = {
        "symbol": symbol,
        "direction": direction,
        "entry_price": entry_price,
        "asset_class": asset_class,
        "source_system": source_system,
        "strategy": strategy,
        "status": "ACTIVE",
        # Long-term extensions
        "pick_type": "long_term_value",
        "holding_horizon": holding_horizon,
        "exit_mode": "thesis",
        "thesis": thesis,
        "thesis_break_rules": thesis_break_rules,
        "intrinsic_value": intrinsic_value,
        "fundamental_snapshot": fundamental_snapshot,
        "earnings_history": earnings_history,
        "next_earnings_date": next_earnings_date,
        "dividend_record": dividend_record,
        "catalyst_dates": catalyst_dates,
        "universe_gate_passed": universe_gate_passed,
        "safety_gate_passed": safety_gate_passed,
    }
    if score is not None:
        pick["score"] = score
    if confidence is not None:
        pick["confidence"] = confidence
    if extra:
        pick["extra"] = extra
    return pick


def make_swing_pick(
    *,
    symbol: str,
    direction: str,
    entry_price: float,
    take_profit: float,
    stop_loss: float,
    fundamental_snapshot: FundamentalSnapshot | None = None,
    earnings_history: list[EarningsRow] | None = None,
    next_earnings_date: str | None = None,
    catalyst_dates: list[str] | None = None,
    holding_horizon: HoldingHorizon = "1m",
    asset_class: str = "EQUITY",
    source_system: str = "swing_screener",
    strategy: str = "trend_momentum_earnings_catalyst",
    score: float | None = None,
    confidence: float | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Construct a `swing` pick conforming to SYNTHESIS.md §4."""
    pick: dict[str, Any] = {
        "symbol": symbol,
        "direction": direction,
        "entry_price": entry_price,
        "take_profit": take_profit,
        "stop_loss": stop_loss,
        "asset_class": asset_class,
        "source_system": source_system,
        "strategy": strategy,
        "status": "ACTIVE",
        "pick_type": "swing",
        "holding_horizon": holding_horizon,
        "exit_mode": "tp_sl",
    }
    if fundamental_snapshot is not None:
        pick["fundamental_snapshot"] = fundamental_snapshot
    if earnings_history is not None:
        pick["earnings_history"] = earnings_history
    if next_earnings_date is not None:
        pick["next_earnings_date"] = next_earnings_date
    if catalyst_dates is not None:
        pick["catalyst_dates"] = catalyst_dates
    if score is not None:
        pick["score"] = score
    if confidence is not None:
        pick["confidence"] = confidence
    if extra:
        pick["extra"] = extra
    return pick


def is_long_term_value(pick: dict[str, Any]) -> bool:
    return pick.get("pick_type") == "long_term_value"


def is_swing(pick: dict[str, Any]) -> bool:
    return pick.get("pick_type") == "swing"


def validate_long_term_pick(pick: dict[str, Any]) -> list[str]:
    """Return list of validation errors. Empty list means valid."""
    errors: list[str] = []
    if pick.get("pick_type") != "long_term_value":
        errors.append("pick_type must be 'long_term_value'")
    if pick.get("exit_mode") != "thesis":
        errors.append("exit_mode must be 'thesis' for long_term_value")
    thesis = pick.get("thesis", "")
    if not isinstance(thesis, str) or not thesis.strip():
        errors.append("thesis must be a non-empty string")
    rules = pick.get("thesis_break_rules", [])
    if not isinstance(rules, list) or len(rules) == 0:
        errors.append("thesis_break_rules must be a non-empty list")
    iv = pick.get("intrinsic_value")
    if iv is None or not isinstance(iv, (int, float)) or iv <= 0:
        errors.append("intrinsic_value must be a positive number")
    if not pick.get("safety_gate_passed", False):
        errors.append("safety_gate_passed must be True")
    snapshot = pick.get("fundamental_snapshot")
    if not isinstance(snapshot, dict):
        errors.append("fundamental_snapshot must be a dict")
    return errors


def evaluate_thesis_break(
    pick: dict[str, Any],
    current_metrics: dict[str, float],
) -> tuple[bool, list[str]]:
    """Check whether any thesis_break_rule has triggered.

    Returns (broken, list_of_triggered_rule_descriptions).
    Used by Phase 8 thesis_resolver.
    """
    if not is_long_term_value(pick):
        return (False, [])

    rules = pick.get("thesis_break_rules", [])
    triggered: list[str] = []
    op_map = {
        "<": lambda a, b: a < b,
        "<=": lambda a, b: a <= b,
        ">": lambda a, b: a > b,
        ">=": lambda a, b: a >= b,
        "==": lambda a, b: a == b,
    }
    for rule in rules:
        metric = rule.get("metric")
        op = rule.get("op")
        threshold = rule.get("threshold")
        if metric is None or op is None or threshold is None:
            continue
        current = current_metrics.get(metric)
        if current is None:
            continue
        check = op_map.get(op)
        if check is None:
            continue
        if check(current, threshold):
            triggered.append(
                f"{metric} {op} {threshold} (current={current})"
            )
    return (len(triggered) > 0, triggered)
