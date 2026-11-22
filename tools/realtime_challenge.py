#!/usr/bin/env python3
"""Buffy realtime paper-trading challenge.

Paper only. No API keys, no orders, no wallet: prices come from the public
Binance spot endpoint and fills are simulated at the last traded price plus
slippage. The point is to test whether a mechanical intraday rule can open and
close a winner on LIVE data in a short window, paying the costs a real account
would pay, and to leave an auditable record whether it wins or loses.

Frozen rules (registered in REALTIMECHALLENGE_*.MD before the first fill):
  venue        Binance spot, public klines (24/7, so the challenge never has
               to wait for an open)
  timeframe    5-minute bars, 200-bar lookback
  entry        long when close > EMA20, EMA20 > EMA60, 40 <= RSI14 <= 72 and
               the last 3 bars are net positive; rank candidates by 3-bar
               return and take the best 3 not already held
  exit         take-profit +0.60 %, stop-loss -0.40 %, time stop 60 minutes,
               first one hit wins; if a bar touches both, the STOP is assumed
               to fill first (conservative)
  costs        10 bps fee per side + 2 bps slippage per side = 24 bps round trip
  size         1/3 of the notional per slot, 3 slots, $10,000 book

Usage:
  python3 tools/realtime_challenge.py open   --tag buffy
  python3 tools/realtime_challenge.py mark   --tag buffy
  python3 tools/realtime_challenge.py cycle  --tag buffy
  python3 tools/realtime_challenge.py status --tag buffy
  python3 tools/realtime_challenge.py report --tag buffy
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

API = "https://api.binance.com/api/v3"
UNIVERSE = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
            "ADAUSDT", "DOGEUSDT", "LINKUSDT"]
TIMEFRAME = "5m"
FEE_BPS_PER_SIDE = 10.0
SLIP_BPS_PER_SIDE = 2.0
TP_PCT = 0.0060
SL_PCT = 0.0040
TIME_STOP_MIN = 60
SLOTS = 3
BOOK_USD = 10_000.0
STATE_DIR = Path("data/realtime_challenge")


# --------------------------------------------------------------------- market
def http_json(url: str, tries: int = 3) -> object:
    last: Exception | None = None
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=15) as r:
                return json.loads(r.read().decode())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"market data unavailable: {url} ({last})")


def klines(symbol: str, interval: str = TIMEFRAME, limit: int = 200) -> list[dict]:
    raw = http_json(f"{API}/klines?symbol={symbol}&interval={interval}&limit={limit}")
    return [{"open_time": int(k[0]), "open": float(k[1]), "high": float(k[2]),
             "low": float(k[3]), "close": float(k[4]), "volume": float(k[5])}
            for k in raw]


def ema(values: list[float], n: int) -> float:
    k = 2.0 / (n + 1.0)
    e = values[0]
    for v in values[1:]:
        e = v * k + e * (1 - k)
    return e


def rsi(values: list[float], n: int = 14) -> float:
    if len(values) < n + 1:
        return 50.0
    gains = losses = 0.0
    for i in range(len(values) - n, len(values)):
        d = values[i] - values[i - 1]
        gains += max(d, 0.0)
        losses += max(-d, 0.0)
    if losses == 0:
        return 100.0
    rs = (gains / n) / (losses / n)
    return 100.0 - 100.0 / (1.0 + rs)


def snapshot(symbol: str) -> dict:
    bars = klines(symbol)
    closes = [b["close"] for b in bars]
    return {
        "symbol": symbol,
        "price": closes[-1],
        "bar_time": bars[-1]["open_time"],
        "ema20": ema(closes[-60:], 20),
        "ema60": ema(closes, 60),
        "rsi14": rsi(closes),
        "ret3": closes[-1] / closes[-4] - 1.0,
    }


# ---------------------------------------------------------------------- state
def state_path(tag: str) -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    return STATE_DIR / f"{tag}.json"


def load_state(tag: str) -> dict:
    p = state_path(tag)
    if p.exists():
        return json.loads(p.read_text())
    return {"tag": tag, "book_usd": BOOK_USD, "opened_at": None,
            "positions": [], "closed": [], "signals_seen": []}


def save_state(tag: str, st: dict) -> None:
    state_path(tag).write_text(json.dumps(st, indent=1) + "\n")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


# ------------------------------------------------------------------------ ops
def cmd_open(tag: str) -> int:
    st = load_state(tag)
    held = {p["symbol"] for p in st["positions"]}
    free = SLOTS - len(st["positions"])
    if free <= 0:
        print(f"open: all {SLOTS} slots occupied; nothing to do")
        return 0

    snaps, errors = [], []
    for sym in UNIVERSE:
        try:
            snaps.append(snapshot(sym))
        except RuntimeError as exc:
            errors.append(str(exc))
    if not snaps:
        print(f"open: no market data ({errors[:1]})")
        return 2

    cands = [s for s in snaps
             if s["symbol"] not in held
             and s["price"] > s["ema20"] > s["ema60"]
             and 40.0 <= s["rsi14"] <= 72.0
             and s["ret3"] > 0]
    cands.sort(key=lambda s: -s["ret3"])

    st["opened_at"] = st["opened_at"] or now_utc().isoformat()
    st["signals_seen"].append({
        "at": now_utc().isoformat(),
        "scan": [{k: round(v, 6) if isinstance(v, float) else v
                  for k, v in s.items()} for s in snaps],
        "qualified": [s["symbol"] for s in cands],
    })

    taken = 0
    for s in cands[:free]:
        px = s["price"]
        entry = px * (1 + SLIP_BPS_PER_SIDE / 1e4)
        notional = BOOK_USD / SLOTS
        st["positions"].append({
            "id": f"{tag}-{s['symbol']}-{int(time.time())}",
            "symbol": s["symbol"],
            "side": "LONG",
            "signal_price": px,
            "entry_price": round(entry, 8),
            "qty": round(notional / entry, 8),
            "notional_usd": round(notional, 2),
            "tp_price": round(px * (1 + TP_PCT), 8),
            "sl_price": round(px * (1 - SL_PCT), 8),
            "opened_at": now_utc().isoformat(),
            "deadline": (now_utc() + timedelta(minutes=TIME_STOP_MIN)).isoformat(),
            "signal": {k: round(s[k], 6) for k in ("ema20", "ema60", "rsi14", "ret3")},
        })
        taken += 1
    save_state(tag, st)
    if taken == 0:
        print(f"open: {len(cands)} candidates after filters, none taken "
              f"(held={sorted(held)})")
    else:
        print(f"open: took {taken} — " + ", ".join(
            f"{p['symbol']}@{p['entry_price']}" for p in st["positions"]))
    return 0


def _close(pos: dict, fill_px: float, why: str, st: dict) -> None:
    gross = pos["side"] == "LONG" and (fill_px / pos["entry_price"] - 1.0) or 0.0
    net = gross - 2 * FEE_BPS_PER_SIDE / 1e4
    pnl = net * pos["notional_usd"]
    st["closed"].append({**pos, "exit_price": round(fill_px, 8),
                         "closed_at": now_utc().isoformat(), "exit_reason": why,
                         "gross_pct": round(100 * gross, 4),
                         "net_pct": round(100 * net, 4),
                         "pnl_usd": round(pnl, 2)})
    st["positions"] = [p for p in st["positions"] if p["id"] != pos["id"]]
    print(f"close {pos['symbol']:9s} {why:9s} exit={fill_px:.6f} "
          f"net={100 * net:+.3f}% pnl=${pnl:+.2f}")


def cmd_mark(tag: str) -> int:
    st = load_state(tag)
    if not st["positions"]:
        print("mark: no open positions")
        return 0
    for pos in list(st["positions"]):
        try:
            bars = klines(pos["symbol"], limit=3)
        except RuntimeError as exc:
            print(f"mark: {pos['symbol']} skipped ({exc})")
            continue
        bar = bars[-1]
        slip = SLIP_BPS_PER_SIDE / 1e4
        hit_sl = bar["low"] <= pos["sl_price"]
        hit_tp = bar["high"] >= pos["tp_price"]
        # Both touched in the same bar: assume the stop fills first.
        if hit_sl:
            _close(pos, pos["sl_price"] * (1 - slip), "STOP", st)
        elif hit_tp:
            _close(pos, pos["tp_price"] * (1 - slip), "TARGET", st)
        elif now_utc() >= datetime.fromisoformat(pos["deadline"]):
            _close(pos, bar["close"] * (1 - slip), "TIME", st)
        else:
            mark = bar["close"]
            print(f"hold {pos['symbol']:9s} mark={mark:.6f} "
                  f"open_pnl={100 * (mark / pos['entry_price'] - 1):+.3f}% "
                  f"tp={pos['tp_price']} sl={pos['sl_price']}")
    save_state(tag, st)
    return 0


def cmd_flatten(tag: str, reason: str = "SPRINT_CLOSE") -> int:
    """Close every open slot at market. Used to end a bounded sprint round.

    Kept as an explicit, labelled exit reason so a sprint close is never
    confused with a rule exit (TP/SL/TIME) in the ledger.
    """
    st = load_state(tag)
    if not st["positions"]:
        print("flatten: nothing open")
        return 0
    for pos in list(st["positions"]):
        try:
            px = klines(pos["symbol"], limit=1)[-1]["close"]
        except RuntimeError as exc:
            print(f"flatten: {pos['symbol']} skipped ({exc})")
            continue
        _close(pos, px * (1 - SLIP_BPS_PER_SIDE / 1e4), reason, st)
    save_state(tag, st)
    return 0


def cmd_cycle(tag: str) -> int:
    cmd_mark(tag)
    return cmd_open(tag)


def summary(st: dict) -> dict:
    closed = st["closed"]
    wins = [c for c in closed if c["net_pct"] > 0]
    pnl = sum(c["pnl_usd"] for c in closed)
    reasons: dict[str, int] = {}
    for c in closed:
        reasons[c["exit_reason"]] = reasons.get(c["exit_reason"], 0) + 1
    return {
        "tag": st["tag"],
        "book_usd": st["book_usd"],
        "opened_at": st["opened_at"],
        "n_closed": len(closed),
        "n_open": len(st["positions"]),
        "wins": len(wins),
        "win_rate_pct": round(100 * len(wins) / len(closed), 1) if closed else None,
        "net_pnl_usd": round(pnl, 2),
        "return_on_book_pct": round(100 * pnl / st["book_usd"], 3),
        "mean_net_pct": round(sum(c["net_pct"] for c in closed) / len(closed), 4) if closed else None,
        "exit_reasons": reasons,
        "still_open": [p["symbol"] for p in st["positions"]],
    }


def cmd_status(tag: str) -> int:
    st = load_state(tag)
    s = summary(st)
    print(json.dumps(s, indent=1))
    for p in st["positions"]:
        print(f"  OPEN  {p['symbol']:9s} entry={p['entry_price']} "
              f"tp={p['tp_price']} sl={p['sl_price']} until={p['deadline']}")
    for c in st["closed"]:
        print(f"  DONE  {c['symbol']:9s} {c['exit_reason']:6s} "
              f"net={c['net_pct']:+.3f}% pnl=${c['pnl_usd']:+.2f}")
    return 0


def cmd_report(tag: str) -> int:
    st = load_state(tag)
    out = STATE_DIR / f"{tag}_summary.json"
    out.write_text(json.dumps({**summary(st), "generated_at": now_utc().isoformat(),
                               "rules": {"timeframe": TIMEFRAME, "tp_pct": TP_PCT,
                                         "sl_pct": SL_PCT, "time_stop_min": TIME_STOP_MIN,
                                         "fee_bps_per_side": FEE_BPS_PER_SIDE,
                                         "slip_bps_per_side": SLIP_BPS_PER_SIDE,
                                         "slots": SLOTS}}, indent=1) + "\n")
    print(f"wrote {out}")
    print(json.dumps(summary(st), indent=1))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Buffy realtime paper challenge")
    ap.add_argument("cmd", choices=["open", "mark", "cycle", "flatten",
                                   "status", "report"])
    ap.add_argument("--tag", default="buffy")
    ap.add_argument("--reason", default="SPRINT_CLOSE")
    a = ap.parse_args()
    if a.cmd == "flatten":
        return cmd_flatten(a.tag, a.reason)
    return {"open": cmd_open, "mark": cmd_mark, "cycle": cmd_cycle,
            "status": cmd_status, "report": cmd_report}[a.cmd](a.tag)


if __name__ == "__main__":
    sys.exit(main())
