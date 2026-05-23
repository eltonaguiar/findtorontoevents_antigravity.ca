"""Tests for alpha_engine.contract_type.classify_contract."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "alpha_engine"))

from alpha_engine.contract_type import classify_contract


def test_commodity_futures():
    for s in ("CL=F", "GC=F", "NG=F", "ZW=F", "ZC=F", "CT=F", "KC=F", "SI=F", "HG=F"):
        assert classify_contract(s) == "commodity_future", s


def test_index_futures():
    for s in ("ES=F", "NQ=F", "YM=F", "RTY=F", "VX=F", "DX=F"):
        assert classify_contract(s) == "index_future", s


def test_rates_futures():
    for s in ("ZN=F", "ZB=F", "ZT=F", "ZF=F"):
        assert classify_contract(s) == "rates_future", s


def test_currency_futures():
    for s in ("6E=F", "6B=F", "6J=F", "6A=F", "6C=F"):
        assert classify_contract(s) == "currency_future", s


def test_crypto():
    for s in ("BINANCE:BTCUSDT", "BTCUSDT", "ETHUSDT", "SOLUSDC", "COINBASE:ETHUSD"):
        assert classify_contract(s) == "crypto", s


def test_forex():
    for s in ("EURUSD=X", "GBPUSD=X", "USDJPY=X", "EUR/USD"):
        assert classify_contract(s) == "forex", s


def test_equity():
    for s in ("AAPL", "MSFT", "NVDA", "BRK.B"):
        assert classify_contract(s) == "equity", s


def test_case_insensitive():
    assert classify_contract("cl=f") == "commodity_future"
    assert classify_contract("es=f") == "index_future"
    assert classify_contract("binance:btcusdt") == "crypto"


def test_exchange_prefix_stripped():
    assert classify_contract("NASDAQ:AAPL") == "equity"
    assert classify_contract("BINANCE:ETHUSDT") == "crypto"


def test_unknown():
    for s in ("", "   ", None, "???", "XYZ=F"):
        assert classify_contract(s) == "unknown", s
