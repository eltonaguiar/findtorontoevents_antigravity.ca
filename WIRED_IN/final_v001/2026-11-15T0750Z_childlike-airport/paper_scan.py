#!/usr/bin/env python3
"""Paper-only scan of peer-cited sleeves. Does not size. Does not touch live engines."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

OUT = Path(__file__).resolve().parent / "paper_scan_results.json"
STAMP = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

CONNORS = ["SPY", "QQQ", "IWM", "DIA", "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "LLY", "JNJ", "XOM", "WMT"]
ETFS = ["SPY", "QQQ", "IWM", "XLK", "XLV", "XLF", "XLE", "XLY", "XLP", "XLI", "XLB"]
EQUITIES = ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "LLY", "JPM", "JNJ", "UNH", "XOM", "COST"]
BONDS = ["TLT", "SHY", "IEF"]
CRYPTO = ["BTC-USD", "ETH-USD", "SOL-USD"]


def _flat(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = [c[0] for c in df.columns]
    df = df.rename(columns={c: str(c).lower() for c in df.columns})
    return df.dropna(subset=["close"])


def rsi2(close: pd.Series) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=0.5, min_periods=2).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=0.5, min_periods=2).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


def atr14(df: pd.DataFrame) -> float:
    prev = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev).abs(),
        (df["low"] - prev).abs(),
    ], axis=1).max(axis=1)
    val = tr.rolling(14).mean().iloc[-1]
    return float(val) if pd.notna(val) else 0.0


def load(symbols: list[str]) -> dict[str, pd.DataFrame]:
    raw = yf.download(symbols, period="2y", interval="1d", auto_adjust=True, progress=False, group_by="ticker", threads=False)
    out = {}
    for sym in symbols:
        try:
            frame = raw[sym] if isinstance(raw.columns, pd.MultiIndex) else raw
        except Exception:
            continue
        frame = _flat(frame)
        if len(frame) >= 210:
            out[sym] = frame
    return out


def snap(df: pd.DataFrame) -> dict:
    close = df["close"]
    price = float(close.iloc[-1])
    sma200 = float(close.rolling(200).mean().iloc[-1])
    r21 = float(close.iloc[-1] / close.iloc[-22] - 1) if len(close) > 22 else None
    r63 = float(close.iloc[-1] / close.iloc[-64] - 1) if len(close) > 64 else None
    return {
        "date": str(df.index[-1].date()),
        "close": round(price, 4),
        "sma200": round(sma200, 4),
        "above_sma200": price > sma200,
        "ret_21d": None if r21 is None else round(r21, 4),
        "ret_63d": None if r63 is None else round(r63, 4),
        "rsi2": round(float(rsi2(close).iloc[-1]), 2),
        "atr14": round(atr14(df), 4),
    }


def connors_pick(sym: str, s: dict, asset_class: str) -> dict | None:
    if s["atr14"] <= 0:
        return None
    price = s["close"]
    if s["rsi2"] < 10 and s["above_sma200"]:
        direction = "LONG"
        tp = round(price + 2.0 * s["atr14"], 4)
        sl = round(price - 1.5 * s["atr14"], 4)
    elif s["rsi2"] > 90 and not s["above_sma200"]:
        direction = "SHORT"
        tp = round(price - 2.0 * s["atr14"], 4)
        sl = round(price + 1.5 * s["atr14"], 4)
    else:
        return None
    return {
        "id": f"wired_in_final_v001::{sym}::connors_rsi2::{s['date']}",
        "symbol": sym,
        "asset_class": asset_class,
        "direction": direction,
        "strategy": "connors_rsi2_paper",
        "entry_price": price,
        "take_profit": tp,
        "stop_loss": sl,
        "rsi2": s["rsi2"],
        "status": "OPEN",
        "paper_trade": True,
        "sizing_allowed": False,
        "trust_tier": "UNPROVEN",
        "reason": f"Connors RSI2 paper: RSI2={s['rsi2']} SMA200={'above' if s['above_sma200'] else 'below'}. Not money-ready.",
    }


def main() -> None:
    books = {
        "connors": load(CONNORS),
        "etf": load(ETFS),
        "equity": load(EQUITIES),
        "bond": load(BONDS),
        "crypto": load(CRYPTO),
    }
    rows = {k: {sym: snap(df) for sym, df in v.items()} for k, v in books.items()}
    connors_fires = []
    for sym, s in rows["connors"].items():
        klass = "ETF" if sym in {"SPY", "QQQ", "IWM", "DIA"} else "EQUITY"
        pick = connors_pick(sym, s, klass)
        if pick:
            connors_fires.append(pick)
    etf_eligible = [sym for sym, s in rows["etf"].items() if s["above_sma200"] and (s["ret_21d"] or 0) > 0 and (s["ret_63d"] or 0) > 0]
    eq_eligible = [sym for sym, s in rows["equity"].items() if s["above_sma200"] and (s["ret_21d"] or 0) > 0 and (s["ret_63d"] or 0) > 0]
    etf_winner = max(etf_eligible, key=lambda sym: rows["etf"][sym]["ret_63d"]) if etf_eligible else None
    eq_winner = max(eq_eligible, key=lambda sym: rows["equity"][sym]["ret_63d"]) if eq_eligible else None
    tlt = rows["bond"].get("TLT")
    ballast = "SHY" if tlt and not tlt["above_sma200"] else ("IEF" if tlt else None)
    payload = {
        "generated_at": STAMP,
        "paper_only": True,
        "sizing_allowed": False,
        "note": "Peer shortlist said no strategy passed proof gates. This scan only records whether cited rules fire today.",
        "connors_fires": connors_fires,
        "trend_momo": {
            "etf_eligible": etf_eligible,
            "etf_winner": etf_winner,
            "equity_eligible": eq_eligible,
            "equity_winner": eq_winner,
        },
        "bond_ballast": ballast,
        "snapshots": rows,
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({
        "generated_at": STAMP,
        "connors_fires": [p["symbol"] for p in connors_fires],
        "etf_winner": etf_winner,
        "equity_winner": eq_winner,
        "bond_ballast": ballast,
        "crypto": {k: {"above": v["above_sma200"], "r21": v["ret_21d"], "rsi2": v["rsi2"]} for k, v in rows["crypto"].items()},
    }, indent=2))


if __name__ == "__main__":
    main()
