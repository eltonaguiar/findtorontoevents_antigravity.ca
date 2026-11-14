"""Append the latest frozen H10 target to the forward paper ledger. Idempotent per close date."""
from __future__ import annotations

import csv
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from data.loader import nasdaq_daily, panel, treasury_bill_daily
from strategies import rsi, rsi2_cash

HERE = Path(__file__).resolve().parent
LEDGER = HERE / "ledger.csv"
CORE = ["SPY", "QQQ"]
COLS = ["signal_date", "spy_w", "qqq_w", "cash_w", "spy_close", "qqq_close",
        "spy_rsi2", "qqq_rsi2", "cash_rate_pct", "note"]


def cash_returns(idx, tb):
    rate = tb["rate"].reindex(idx, method="ffill").ffill().bfill()
    return (rate / 100.0 / 252.0).fillna(0.0)


def main():
    end = date.today().isoformat()
    core = panel(nasdaq_daily, CORE, start="2016-01-01", end=end).sort_index()
    tb = treasury_bill_daily(2018, date.today().year)
    w = rsi2_cash(core, cash_returns(core.index, tb))
    w = w.dropna(how="all")
    last = w.index[-1]
    row = {
        "signal_date": last.date().isoformat(),
        "spy_w": round(float(w.loc[last].get("SPY", 0.0)), 6),
        "qqq_w": round(float(w.loc[last].get("QQQ", 0.0)), 6),
        "cash_w": round(float(w.loc[last].get("CASH", 0.0)), 6),
        "spy_close": round(float(core["SPY"].loc[last]), 4),
        "qqq_close": round(float(core["QQQ"].loc[last]), 4),
        "spy_rsi2": round(float(rsi(core["SPY"], 2).loc[last]), 3),
        "qqq_rsi2": round(float(rsi(core["QQQ"], 2).loc[last]), 3),
        "cash_rate_pct": round(float(tb["rate"].reindex(core.index, method="ffill").loc[last]), 3),
        "note": "frozen H10; execute next session",
    }
    existing = []
    if LEDGER.exists():
        with LEDGER.open() as f:
            existing = list(csv.DictReader(f))
    if any(r.get("signal_date") == row["signal_date"] for r in existing):
        print(f"ledger already has {row['signal_date']}; no change")
        return
    with LEDGER.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLS)
        if not existing:
            writer.writeheader()
        writer.writerow(row)
    print("appended", row)


if __name__ == "__main__":
    main()
