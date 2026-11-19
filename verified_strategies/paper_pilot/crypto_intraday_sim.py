#!/usr/bin/env python3
"""crypto_intraday_sim — live paper simulation of short-horizon crypto slots.

Three pre-registered strategy slots run in parallel on real 4h bars (fetched
through the tools.crypto_bars failover chain). Everything is paper: the sim
opens/closes virtual positions, logs CLOSE rows that
tools/pilot_forward_bridge.py re-resolves honestly into
reports/forward_observations.jsonl, and NOTHING here can promote itself — the
audit3 forward gate (n>=100, net PF CI-LB > 1.0, 100% intrabar honesty) is the
only path to a verdict.

Slots (one hypothesis each, M-107 pre-registered):

  vwap_reversion   H-2026-11-19-01  long a 1.5-2.5 z dip below rolling VWAP
  bollinger_mr     H-2026-11-19-02  long a close below the lower Bollinger band
  btc_4h_rsi_macd  H-2026-11-19-07  long RSI(50-70) + rising positive MACD hist

Prop-firm style guardrails per slot (judged on CLOSED trades only):
  * trailing drawdown > 10% of cumulative pnl peak -> HALTED (manual review)
  * daily realised loss > 3% -> PAUSED until the next UTC day
  * one UTC day > 40% of cumulative positive pnl -> consistency_flag (marks a
    lucky streak; blocks nothing but is reported)
  * n < 20 closed trades -> "no_judgment" (statistics are not interpretable)

Usage::

    python3 verified_strategies/paper_pilot/crypto_intraday_sim.py --one-shot
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PILOT_DIR = Path(__file__).resolve().parent
LOG_PATH = PILOT_DIR / "crypto_intraday_sim_paper_log.jsonl"
STATE_PATH = PILOT_DIR / "crypto_intraday_sim_state.json"

UNIVERSE = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
INTERVAL = "4h"
BAR_MS = 4 * 3600_000
LOOKBACK_BARS = 80

MAX_POSITIONS_PER_SLOT = 2
TRAILING_DD_HALT_PCT = 10.0
DAILY_LOSS_PAUSE_PCT = 3.0
CONSISTENCY_SHARE = 0.40
MIN_N_BEFORE_JUDGMENT = 20
#: Cost floor (peer review 2026-11-19, buffy): refuse any entry whose expected
#: move to target is under 4x the round-trip cost, so the forward clock cannot
#: fill with predictably negative rows (measured elsewhere: gross edge 1.4bp
#: vs 12bp cost = fees ate 757% of gross). 16bp matches the ledger's
#: CRYPTO_RT_BP convention.
ROUND_TRIP_COST_PCT = 0.16
COST_FLOOR_MULT = 4.0

SLOTS: dict[str, dict] = {
    "vwap_reversion": {
        "hypothesis_id": "H-2026-11-19-01",
        "max_hold_bars": 12,
        "z_entry": -1.5, "z_floor": -2.5,
        "stop_pct": None,  # close-only stop per hypothesis
        "close_stop_pct": -4.0,
    },
    "bollinger_mr": {
        "hypothesis_id": "H-2026-11-19-02",
        "max_hold_bars": 10,
        "bb_window": 20, "bb_k": 2.0,
        "stop_pct": None,
        "close_stop_pct": -4.0,
    },
    "btc_4h_rsi_macd": {
        "hypothesis_id": "H-2026-11-19-07",
        "max_hold_bars": 18,
        "take_profit_pct": 4.0, "stop_pct": -2.0,
    },
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()


def _load_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _save_state(state: dict) -> None:
    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True),
                          encoding="utf-8")


def _append_log(row: dict) -> None:
    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, default=str) + "\n")


def _closed_trades() -> list[dict]:
    if not LOG_PATH.exists():
        return []
    out = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if isinstance(obj, dict) and obj.get("event") == "CLOSE":
            out.append(obj)
    return out


# --------------------------------------------------------------- indicators
def _sma(xs: list[float], n: int) -> float | None:
    return sum(xs[-n:]) / n if len(xs) >= n else None


def _std(xs: list[float], n: int) -> float | None:
    if len(xs) < n:
        return None
    w = xs[-n:]
    m = sum(w) / n
    return (sum((x - m) ** 2 for x in w) / n) ** 0.5


def _rsi(closes: list[float], n: int = 14) -> float | None:
    if len(closes) < n + 1:
        return None
    gains = losses = 0.0
    for prev, cur in zip(closes[-n - 1:-1], closes[-n:]):
        d = cur - prev
        gains += max(d, 0.0)
        losses += max(-d, 0.0)
    if losses == 0:
        return 100.0
    rs = gains / losses
    return 100.0 - 100.0 / (1.0 + rs)


def _ema_series(xs: list[float], n: int) -> list[float]:
    if not xs:
        return []
    k = 2.0 / (n + 1.0)
    out = [xs[0]]
    for x in xs[1:]:
        out.append(x * k + out[-1] * (1.0 - k))
    return out


def _macd_hist(closes: list[float]) -> tuple[float, float] | None:
    """(hist_now, hist_prev) for MACD(12,26,9)."""
    if len(closes) < 35:
        return None
    fast = _ema_series(closes, 12)
    slow = _ema_series(closes, 26)
    macd = [f - s for f, s in zip(fast, slow)]
    signal = _ema_series(macd, 9)
    hist = [m - s for m, s in zip(macd, signal)]
    return hist[-1], hist[-2]


def _rolling_vwap(bars: list[dict], n: int = 30) -> tuple[float, float] | None:
    """(vwap, deviation_std) over the last n bars, or None."""
    if len(bars) < n:
        return None
    w = bars[-n:]
    pv = sum(((b["high"] + b["low"] + b["close"]) / 3.0) * b.get("volume", 0.0)
             for b in w)
    vol = sum(b.get("volume", 0.0) for b in w)
    if vol <= 0:
        return None
    vwap = pv / vol
    closes = [b["close"] for b in w]
    dev = _std([c - vwap for c in closes], n)
    if not dev:
        return None
    return vwap, dev


def _rolling_vwap_z(bars: list[dict], n: int = 30) -> float | None:
    res = _rolling_vwap(bars, n)
    if res is None:
        return None
    vwap, dev = res
    return (bars[-1]["close"] - vwap) / dev


# --------------------------------------------------------------- signals
def entry_signal(slot: str, bars: list[dict]) -> dict | None:
    """A LONG entry proposal {reason, expected_move_pct, take_profit?,
    stop_loss?} or None. Entries whose expected move to target is below
    COST_FLOOR_MULT x ROUND_TRIP_COST_PCT are refused outright."""
    cfg = SLOTS[slot]
    closes = [b["close"] for b in bars]
    last = closes[-1]
    floor_pct = COST_FLOOR_MULT * ROUND_TRIP_COST_PCT
    if slot == "vwap_reversion":
        res = _rolling_vwap(bars)
        if res is None:
            return None
        vwap, dev = res
        z = (last - vwap) / dev
        if cfg["z_floor"] <= z <= cfg["z_entry"]:
            expected = (vwap - last) / last * 100.0
            if expected < floor_pct:
                return None
            return {"reason": f"vwap_z={z:.2f}", "expected_move_pct": expected}
        return None
    if slot == "bollinger_mr":
        n, k = cfg["bb_window"], cfg["bb_k"]
        mid, sd = _sma(closes, n), _std(closes, n)
        if mid is None or not sd:
            return None
        lower = mid - k * sd
        if last < lower:
            expected = (mid - last) / last * 100.0
            if expected < floor_pct:
                return None
            return {"reason": f"close<{lower:.2f} (lower BB)",
                    "take_profit": mid, "expected_move_pct": expected}
        return None
    if slot == "btc_4h_rsi_macd":
        rsi = _rsi(closes)
        mh = _macd_hist(closes)
        if rsi is None or mh is None:
            return None
        hist_now, hist_prev = mh
        if 50.0 < rsi < 70.0 and hist_now > 0 and hist_now > hist_prev:
            expected = cfg["take_profit_pct"]
            if expected < floor_pct:
                return None
            return {
                "reason": f"rsi={rsi:.1f} macd_hist rising",
                "expected_move_pct": expected,
                "take_profit": last * (1.0 + cfg["take_profit_pct"] / 100.0),
                "stop_loss": last * (1.0 + cfg["stop_pct"] / 100.0),
            }
        return None
    return None


def exit_check(slot: str, pos: dict, bars_since_entry: list[dict],
               bars_all: list[dict]) -> tuple[str, float, int] | None:
    """(reason, exit_price, exit_ts_ms) or None to keep holding.

    TP/SL are checked intrabar on bars strictly after entry; close-only stops
    and signal exits are checked on the latest close, matching each
    hypothesis's registered expression.
    """
    cfg = SLOTS[slot]
    entry = float(pos["entry_price"])
    tp = pos.get("take_profit")
    sl = pos.get("stop_loss")
    for b in bars_since_entry:
        if sl is not None and b["low"] <= sl:
            return ("SL", float(sl), int(b["timestamp"]))
        if tp is not None and b["high"] >= tp:
            return ("TP", float(tp), int(b["timestamp"]))
    if not bars_all:
        return None
    last_bar = bars_all[-1]
    last = float(last_bar["close"])
    last_ts = int(last_bar["timestamp"])
    pnl_pct = (last / entry - 1.0) * 100.0
    close_stop = cfg.get("close_stop_pct")
    if close_stop is not None and pnl_pct <= close_stop:
        return ("CLOSE_STOP", last, last_ts)
    if slot == "vwap_reversion":
        z = _rolling_vwap_z(bars_all)
        if z is not None and z >= 0:
            return ("REVERTED", last, last_ts)
    held_bars = max(0, (last_ts - int(pos["entry_ts_ms"])) // BAR_MS)
    if held_bars >= cfg["max_hold_bars"]:
        return ("TIME", last, last_ts)
    return None


# --------------------------------------------------------------- guardrails
def slot_guardrails(slot: str, closed: list[dict],
                    today: str) -> dict:
    """Prop-firm style status from CLOSED trades only."""
    trades = [t for t in closed if t.get("slot") == slot]
    pnls = [float(t.get("pnl_pct") or 0.0) for t in trades]
    cum = peak = dd = 0.0
    for p in pnls:
        cum += p
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    daily: dict[str, float] = {}
    for t in trades:
        day = str(t.get("exit_ts") or t.get("date") or "")[:10]
        daily[day] = daily.get(day, 0.0) + float(t.get("pnl_pct") or 0.0)
    today_pnl = daily.get(today, 0.0)
    total = sum(pnls)
    consistency_flag = bool(
        total > 0 and daily and max(daily.values()) / total > CONSISTENCY_SHARE)
    status = "ACTIVE"
    reason = None
    if dd > TRAILING_DD_HALT_PCT:
        status, reason = "HALTED", f"trailing drawdown {dd:.1f}% > {TRAILING_DD_HALT_PCT}%"
    elif today_pnl < -DAILY_LOSS_PAUSE_PCT:
        status, reason = "PAUSED", f"daily loss {today_pnl:.1f}% > {DAILY_LOSS_PAUSE_PCT}%"
    return {
        "status": status, "reason": reason,
        "n_closed": len(trades), "cum_pnl_pct": round(total, 4),
        "max_dd_pct": round(dd, 4), "today_pnl_pct": round(today_pnl, 4),
        "consistency_flag": consistency_flag,
        "judgment": ("no_judgment: n<%d" % MIN_N_BEFORE_JUDGMENT
                     if len(trades) < MIN_N_BEFORE_JUDGMENT else "reportable"),
    }


# --------------------------------------------------------------- main loop
def completed_bars(bars: list[dict], now_ms: int) -> list[dict]:
    """Only bars whose interval has fully elapsed; the forming bar is excluded."""
    return [b for b in bars if int(b.get("timestamp") or 0) + BAR_MS <= now_ms]


def run_one_shot(bars_by_symbol: dict[str, list[dict]] | None = None) -> dict:
    """One tick: evaluate exits, then entries, then refresh guardrails.

    bars_by_symbol lets tests inject bars; live runs fetch through the
    failover chain.
    """
    now = _now()
    today = now.strftime("%Y-%m-%d")
    state = _load_state()
    positions: dict[str, dict] = state.get("positions") or {}

    if bars_by_symbol is None:
        from tools.crypto_bars import fetch_klines

        end_ms = int(now.timestamp() * 1000)
        start_ms = end_ms - LOOKBACK_BARS * BAR_MS
        # Drop the FORMING bar: its close mutates until the bar completes, so
        # trading on it is intra-bar lookahead (self-caught in the 2026-11-19
        # design debate while defending element 8). Injected test bars bypass
        # this on purpose — tests construct completed bars only.
        bars_by_symbol = {
            sym: completed_bars(
                fetch_klines(sym, INTERVAL, start_ms, end_ms), end_ms)
            for sym in UNIVERSE
        }

    closed = _closed_trades()
    guards = {slot: slot_guardrails(slot, closed, today) for slot in SLOTS}

    # 1) exits first — guardrail status never blocks an exit
    for key in list(positions.keys()):
        pos = positions[key]
        slot, sym = pos["slot"], pos["symbol"]
        bars = bars_by_symbol.get(sym) or []
        since = [b for b in bars if int(b["timestamp"]) > int(pos["entry_ts_ms"])]
        res = exit_check(slot, pos, since, bars)
        if res is None:
            continue
        reason, exit_px, exit_ms = res
        entry = float(pos["entry_price"])
        pnl_pct = round((exit_px / entry - 1.0) * 100.0, 4)
        close_row = {
            "date": today,
            "event": "CLOSE",
            "slot": slot,
            "strategy": slot,
            "hypothesis_id": SLOTS[slot]["hypothesis_id"],
            "asset_class": "CRYPTO",
            "symbol": sym,
            "direction": "LONG",
            "entry_price": entry,
            "entry_ts": _iso(int(pos["entry_ts_ms"])),
            "exit_price": exit_px,
            "exit_ts": _iso(exit_ms),
            "exit_reason": reason,
            "stop_loss": pos.get("stop_loss"),
            "take_profit": pos.get("take_profit"),
            "pnl_pct": pnl_pct,
            "outcome": "WIN" if pnl_pct > 0 else "LOSS",
        }
        _append_log(close_row)
        closed.append(close_row)
        del positions[key]
        guards[slot] = slot_guardrails(slot, closed, today)

    # 2) entries — only for ACTIVE slots, newest completed bar only
    for slot, cfg in SLOTS.items():
        if guards[slot]["status"] != "ACTIVE":
            continue
        open_in_slot = [p for p in positions.values() if p["slot"] == slot]
        for sym in UNIVERSE:
            if len(open_in_slot) >= MAX_POSITIONS_PER_SLOT:
                break
            key = f"{slot}|{sym}"
            if key in positions:
                continue
            bars = bars_by_symbol.get(sym) or []
            if len(bars) < 40:
                continue
            sig = entry_signal(slot, bars)
            if not sig:
                continue
            last_bar = bars[-1]
            entry_px = float(last_bar["close"])
            pos = {
                "slot": slot,
                "symbol": sym,
                "direction": "LONG",
                "entry_price": entry_px,
                "entry_ts_ms": int(last_bar["timestamp"]),
                "take_profit": sig.get("take_profit"),
                "stop_loss": sig.get("stop_loss"),
                "reason": sig.get("reason"),
                "status": "OPEN",
            }
            positions[key] = pos
            open_in_slot.append(pos)
            _append_log({
                "date": today, "event": "OPEN", "slot": slot, "strategy": slot,
                "hypothesis_id": cfg["hypothesis_id"], "asset_class": "CRYPTO",
                "symbol": sym, "direction": "LONG", "entry_price": entry_px,
                "entry_ts": _iso(int(last_bar["timestamp"])),
                "take_profit": sig.get("take_profit"),
                "stop_loss": sig.get("stop_loss"), "reason": sig.get("reason"),
            })

    state.update({
        "positions": positions,
        "guardrails": guards,
        "last_run": now.isoformat(),
        "universe": UNIVERSE,
        "interval": INTERVAL,
        "paper_only": True,
        "min_n_before_judgment": MIN_N_BEFORE_JUDGMENT,
    })
    _save_state(state)
    return {"date": today, "open_positions": len(positions),
            "guardrails": guards}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--one-shot", action="store_true", help="run a single tick")
    args = ap.parse_args(argv)
    if not args.one_shot:
        ap.print_help()
        return 0
    print(json.dumps(run_one_shot(), indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
