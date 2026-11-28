"""Unit tests for the bracket-repair SQL in tools/quarantine_bad_rows.py.

2026-11-28: the historical wrong-side-stop sweep NULLed 268 stop_loss fields by
rule B1. Two bugs in that SQL were caught only by running it against the live
ledger, so they get a database-free test here:

  1. an unbalanced parenthesis made every B1/B2 statement a MySQL syntax error;
  2. `entry_price > 0` on the zero-level clause left 28 rows with `stop_loss = 0`
     untouched, so the `bad_side_stops` audit gate stayed red after a sweep that
     reported success.

The SQL is built without a cursor, so `bracket_repairs(None, ...)` is enough.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.quarantine_bad_rows import (  # noqa: E402
    BRACKET_MAX_RATIO,
    bracket_repairs,
)


def _rules() -> list[tuple[str, str, str, tuple]]:
    return bracket_repairs(None, "trading_picks")


@pytest.mark.parametrize("rule,column,sql,params", _rules())
def test_sql_is_well_formed(rule, column, sql, params) -> None:
    assert sql.count("(") == sql.count(")"), f"{rule}: unbalanced parentheses"
    # pymysql formats `%s` against `params`, so the counts must agree exactly.
    assert sql.count("%s") == len(params), f"{rule}: placeholder/param mismatch"
    assert column == "stop_loss" or column == "take_profit"


def test_stop_rule_reaches_zero_stops_without_an_entry() -> None:
    """The zero clause must not be gated on entry_price."""
    sql = dict((r, s) for r, _c, s, _p in _rules())["B1_bad_stop"]
    zero_clause = [part for part in sql.split(" OR ") if "stop_loss <= 0" in part]
    assert zero_clause, "B1 must NULL a non-positive stop"
    assert "entry_price" not in zero_clause[0].split("stop_loss <= 0")[0]


@pytest.mark.parametrize("rule,column", [
    ("B1_bad_stop", "stop_loss"),
    ("B2_bad_take_profit", "take_profit"),
])
def test_wrong_side_is_direction_aware(rule, column) -> None:
    sql = dict((r, s) for r, _c, s, _p in _rules())[rule]
    assert "UPPER(COALESCE(direction,''))" in sql
    assert column in sql
    # Both directions must be covered, or half the ledger goes unswept.
    assert sql.count("IN (%s,%s)") == 2


def test_scale_rule_uses_the_ingest_multiple() -> None:
    b3 = [s for r, _c, s, _p in _rules() if r == "B3_bracket_scale"]
    assert len(b3) == 2, "B3 must run for both bracket columns"
    for sql in b3:
        assert str(BRACKET_MAX_RATIO) in sql
