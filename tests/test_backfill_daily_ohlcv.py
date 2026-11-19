# -*- coding: utf-8 -*-
"""Tests for tools/backfill_daily_ohlcv.py ``--symbols`` universe forcing.

A symbol the target table has never held cannot be advanced by a date-bounded
backfill — which is exactly what kept /audit3 at EQUITY 23/37 priced: BBAI, CHPT,
CLSK, NIO, SNAP, SPCE, JETS, XLP/XLV/XLY were simply absent from
equity_daily_ohlcv, so no amount of freshness helped them.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.backfill_daily_ohlcv import universe


class _Cur:
    """Minimal cursor stand-in: one SELECT, rows handed back as fetched."""

    def __init__(self, rows):
        self._rows = rows
        self.sql = None

    def execute(self, sql):
        self.sql = sql

    def fetchall(self):
        return self._rows


def test_force_adds_symbols_the_table_never_had():
    got = universe("equity_daily_ohlcv", _Cur([("AAPL",)]), extra=False,
                   force=["bbai", "CHPT"])
    assert got == ["AAPL", "BBAI", "CHPT"]


def test_force_is_optional_and_normalising():
    cur = _Cur([(" JETS ",)])
    assert universe("equity_daily_ohlcv", cur, extra=False) == ["JETS"]
    assert universe("equity_daily_ohlcv", cur, extra=False, force=None) == ["JETS"]
    assert universe("equity_daily_ohlcv", cur, extra=False, force=["", "  ", "jets"]) == ["JETS"]


def test_force_dedupes_against_stored_rows():
    got = universe("equity_daily_ohlcv", _Cur([("AAPL",)]), extra=False,
                   force=["AAPL", "aapl", " SNAP "])
    assert got == ["AAPL", "SNAP"]
