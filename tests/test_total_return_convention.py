"""Static guard: the value pipeline must request ADJUSTED prices for any return use.

Regression for the total-return check (VALUE_TOTALRETURN_CHECK.md): a raw Close feed
silently drops dividends (~2.8%/yr for a value universe) and can make a positive value
premium look like +0.11%.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_value_pipeline_yfinance_uses_auto_adjust():
    for rel in ("alpha_engine/value_screener_runner.py", "alpha_engine/equity_price_failover.py"):
        txt = (ROOT / rel).read_text(errors="ignore")
        assert "auto_adjust=True" in txt, f"{rel} must request adjusted prices for total return"
