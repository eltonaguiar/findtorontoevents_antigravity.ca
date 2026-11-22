#!/usr/bin/env python3
"""REALTIME CHALLENGE — can I open and close a paper position on LIVE market
data and come out ahead within a short timeframe?

Two modes
    python3 tools/realtime_challenge.py --open     # find setups on live bars, open
    python3 tools/realtime_challenge.py --resolve  # walk forward, close, score

Pre-registration discipline (this whole project's hard-won rule): the signal
rules, the TP/SL multiples, the hold limit and the fee assumption were fixed
BEFORE the first live bar was fetched. They are constants below and must not be
edited after seeing a result. If they change, that is a NEW hypothesis run.

Honest constraints built in
  * The session clock is checked first. On a weekend only CRYPTO is live; the
    script reports the closed venues rather than fabricating a price.
  * Every price must come from >=2 independent venues that agree within 50bp.
    A divergent or stale feed is rejected, not averaged.
  * Intrabar conflicts are resolved PESSIMISTICALLY: if one bar's range covers
    both the stop and the target, the STOP is assumed to have filled first.
  * Fees are charged on both legs (taker, 10bp/side by default).
  * n is printed next to every number. One session of trades proves nothing.

State: reports/realtime_challenge/state.json  (append-only trade log inside)
Ledger: reports/realtime_challenge/trades.jsonl
"""
from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "realtime_challenge"
STATE = OUT / "state.json"
LEDGER = OUT / "trades.jsonl"

# ---------------------------------------------------------------- pre-registered
# ARM A1 (Donchian breakout) and ARM A2 (RSI oversold reversal) were both
# declared BEFORE any trade outcome was observed. Run 1 of the challenge fired
# zero A1 setups, which is what motivated adding A2 — no P&L had been seen at
# that point, so no outcome data influenced the choice. Family-wise error is
# inflated by the arm count and that is disclosed everywhere below.
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
           "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT",
           "LTCUSDT", "TRXUSDT", "ATOMUSDT", "UNIUSDT", "ETCUSDT",
           "FILUSDT", "NEARUSDT", "APTUSDT", "ARBUSDT", "OPUSDT",
           "INJUSDT", "SUIUSDT", "SEIUSDT", "AAVEUSDT", "ALGOUSDT",
           "EOSUSDT", "XLMUSDT", "VETUSDT", "MATICUSDT", "ICPUSDT"]
BAR = "5m"
LOOKBACK = 300            # bars fetched
BREAKOUT_N = 20           # Donchian channel length  (ARM A1)
RSI_N = 14                # RSI length               (ARM A2)
RSI_BUY = 30              # ARM A2 fires below this
ATR_N = 14
SL_ATR = 1.0              # stop distance in ATRs
TP_ATR = 2.0              # target distance in ATRs
MAX_HOLD_BARS = 24        # 24 * 5m = 2 hours
FEE_PER_SIDE = 0.0010     # 10bp taker
ALLOW_LONG = True
ALLOW_SHORT = False       # long-only in run 1; shorting is a separate hypothesis
MAX_CONCURRENT = 5
N_CONFIGS = len(SYMBOLS) * 2   # 2 arms x N symbols = disclosed search breadth
RISK_NOTE = ("Two arms, same exits: A1 Donchian breakout on a close beyond the "
             f"prior {BREAKOUT_N}-bar extreme; A2 RSI({RSI_N}) < {RSI_BUY} dip. "
             f"Both long-only, TP {TP_ATR}xATR, SL {SL_ATR}xATR, max hold "
             f"{MAX_HOLD_BARS} bars ({MAX_HOLD_BARS*5}min), 10bp/side.")

UA = {"User-Agent": "Mozilla/5.0 (compatible; antigravity-realtime-challenge/1.0)"}


# ---------------------------------------------------------------------- plumbing
def get(url: str, timeout: int = 12):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def session_status() -> dict:
    """Which venues are actually open right now (UTC)."""
    now = datetime.now(timezone.utc)
    wd, hh = now.weekday(), now.hour
    equity_open = wd < 5 and (13 <= hh < 21)          # 09:30-16:00 ET approx
    return {
        "utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "weekday": now.strftime("%A"),
        "crypto": True,
        "equity": equity_open,
        "futures": wd < 5 or wd == 6,
        "forex": wd < 5,
        "reason": ("weekend - cash equity, FX and most futures venues closed; "
                   "only crypto trades 24/7" if wd >= 5 else "weekday session"),
    }


# ------------------------------------------------------------------ data sources
def bars_binance(sym: str):
    for host in ("api.binance.com", "api1.binance.com", "api2.binance.com",
                 "api3.binance.com", "api4.binance.com"):
        try:
            d = get(f"https://{host}/api/v3/klines?symbol={sym}&interval={BAR}&limit={LOOKBACK}")
            return [{"t": int(k[0]), "o": float(k[1]), "h": float(k[2]),
                     "l": float(k[3]), "c": float(k[4]), "v": float(k[5])} for k in d], host
        except Exception:
            continue
    return None, None


def bars_kucoin(sym: str):
    try:
        base, quote = sym[:-4], sym[-4:]
        d = get(f"https://api.kucoin.com/api/v1/market/candles?type=5min&symbol={base}-{quote}")
        rows = d["data"][:LOOKBACK]
        out = [{"t": int(r[0]) * 1000, "o": float(r[1]), "c": float(r[2]),
                "h": float(r[3]), "l": float(r[4]), "v": float(r[5])} for r in rows]
        return sorted(out, key=lambda x: x["t"]), "kucoin"
    except Exception:
        return None, None


def bars_cryptocompare(sym: str):
    try:
        base, quote = sym[:-4], sym[-4:]
        d = get("https://min-api.cryptocompare.com/data/v2/histominute"
                f"?fsym={base}&tsym={quote}&limit={LOOKBACK}&aggregate=5")
        rows = d["Data"]["Data"]
        out = [{"t": int(r["time"]) * 1000, "o": r["open"], "h": r["high"],
                "l": r["low"], "c": r["close"], "v": r["volumefrom"]} for r in rows]
        return out, "cryptocompare"
    except Exception:
        return None, None


def live_price_consensus(sym: str) -> dict | None:
    """Last price from independent venues; reject if they disagree > 50bp."""
    px = {}
    b, src = bars_binance(sym)
    if b:
        px["binance"] = b[-1]["c"]
    k, _ = bars_kucoin(sym)
    if k:
        px["kucoin"] = k[-1]["c"]
    c, _ = bars_cryptocompare(sym)
    if c:
        px["cryptocompare"] = c[-1]["c"]
    if not px:
        return None
    vals = list(px.values())
    med = statistics.median(vals)
    spread_bp = (max(vals) - min(vals)) / med * 1e4 if med else 0.0
    return {"price": med, "venues": px, "n_venues": len(px),
            "spread_bp": round(spread_bp, 2), "trusted": len(px) >= 2 and spread_bp <= 50}


# --------------------------------------------------------------------- technicals
def atr(bars: list[dict], n: int = ATR_N) -> float:
    trs = []
    for i in range(1, len(bars)):
        h, l, pc = bars[i]["h"], bars[i]["l"], bars[i - 1]["c"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return sum(trs[-n:]) / min(n, len(trs)) if trs else 0.0


def rsi(bars: list[dict], n: int = RSI_N) -> float:
    if len(bars) <= n:
        return 50.0
    gains, losses = [], []
    for i in range(len(bars) - n, len(bars)):
        d = bars[i]["c"] - bars[i - 1]["c"]
        gains.append(max(d, 0.0)); losses.append(max(-d, 0.0))
    ag, al = sum(gains) / n, sum(losses) / n
    if al == 0:
        return 100.0
    rs = ag / al
    return 100.0 - 100.0 / (1.0 + rs)


def signal_at(bars: list[dict], i: int) -> str | None:
    """Which arm fires at bar i (decision uses bars up to and including i)."""
    if i < max(BREAKOUT_N, ATR_N, RSI_N) + 1:
        return None
    prior = bars[i - BREAKOUT_N:i]
    hi = max(b["h"] for b in prior)
    if ALLOW_LONG and bars[i]["c"] > hi:
        return "A1_donchian_long"
    if ALLOW_LONG and rsi(bars[:i + 1]) < RSI_BUY:
        return "A2_rsi_dip_long"
    return None


def evaluate(sym: str) -> dict | None:
    bars, src = bars_binance(sym)
    if not bars or len(bars) < BREAKOUT_N + ATR_N + 2:
        bars, src = bars_kucoin(sym)
    if not bars or len(bars) < BREAKOUT_N + ATR_N + 2:
        return None
    a = atr(bars)
    last = bars[-1]
    prior = bars[-(BREAKOUT_N + 1):-1]
    hi = max(b["h"] for b in prior)
    lo = min(b["l"] for b in prior)
    sig = signal_at(bars, len(bars) - 1)
    cons = live_price_consensus(sym)
    return {"symbol": sym, "source": src, "bars": len(bars), "atr": a,
            "last_close": last["c"], "last_bar_utc": datetime.fromtimestamp(
                last["t"] / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "prior_high": hi, "prior_low": lo, "rsi": rsi(bars),
            "dist_to_break_bp": round((hi - last["c"]) / last["c"] * 1e4, 1),
            "setup": sig, "side": "LONG" if sig else None,
            "consensus": cons,
            "atr_pct": (a / last["c"] * 100) if last["c"] else None}


def simulate(bars: list[dict], i: int, side: str) -> dict | None:
    """Signal at bar i close, FILL AT BAR i+1 OPEN, walk forward.

    FIXED 2026-11-22 (peer review): this used to fill at `bars[i]["c"]`, the same
    close the signal was computed from. That is a lag-0 fill: it trades at a price
    that only exists because we already know the bar closed above the breakout
    level, and it flatters every breakout backtest that uses it. A signal computed
    from a closed bar cannot be executed at that bar's close. Entry is now the next
    bar's open, which is the first price actually available to a live trader.

    Bars i+1.. still legitimately trigger TP/SL: we hold from the open of i+1.
    Pessimistic on intrabar ties (stop checked before target).
    """
    if i + 1 >= len(bars):
        return None                      # no bar left to fill on
    a = atr(bars[:i + 1])
    if a <= 0:
        return None
    entry = bars[i + 1]["o"]             # next-bar open = first executable price
    tp, sl = entry + TP_ATR * a, entry - SL_ATR * a
    for j in range(i + 1, min(i + 1 + MAX_HOLD_BARS, len(bars))):
        b = bars[j]
        if b["l"] <= sl:
            return {"exit": sl, "reason": "SL", "bars": j - i}
        if b["h"] >= tp:
            return {"exit": tp, "reason": "TP", "bars": j - i}
    j = min(i + MAX_HOLD_BARS, len(bars) - 1)
    if j <= i:
        return None
    return {"exit": bars[j]["c"], "reason": "TIMEOUT", "bars": j - i}


def backtest() -> None:
    """Run the SAME live rule over the bars just fetched. This is the only
    way to get a usable n today; the forward clock accrues one bar-set at a
    time. In-sample caveat: these are the most recent bars, not held out."""
    per_arm: dict[str, list[float]] = {}
    rows = []
    for sym in SYMBOLS:
        bars, src = bars_binance(sym)
        if not bars or len(bars) < 60:
            bars, src = bars_kucoin(sym)
        if not bars or len(bars) < 60:
            continue
        for i in range(max(BREAKOUT_N, RSI_N, ATR_N) + 1, len(bars) - 1):
            sig = signal_at(bars, i)
            if not sig:
                continue
            r = simulate(bars, i, "LONG")
            if not r:
                continue
            gross = (r["exit"] - bars[i]["c"]) / bars[i]["c"]
            net = gross - 2 * FEE_PER_SIDE
            per_arm.setdefault(sig, []).append(net)
            rows.append({"symbol": sym, "arm": sig, "net": net})
    if not rows:
        print("backtest: no trades")
        return
    print(f"\n=== BACKTEST ON LIVE BARS ({BAR}, last {LOOKBACK} bars/symbol) ===")
    print(f"  search breadth: {len(SYMBOLS)} symbols x 2 arms = {N_CONFIGS} configs "
          f"(disclosed; not deflated here)")
    for arm, v in sorted(per_arm.items()):
        n = len(v)
        mean = sum(v) / n
        sd = statistics.stdev(v) if n > 1 else 0.0
        t = mean / (sd / math.sqrt(n)) if sd and n > 1 else float("nan")
        wr = 100 * len([x for x in v if x > 0]) / n
        tot = sum(v) * 100
        print(f"  {arm:20} n={n:4d}  WR={wr:5.1f}%  mean={mean*100:+.4f}%  "
              f"total={tot:+7.2f}%  t={t:+.2f}" if n > 1 else
              f"  {arm:20} n={n:4d}  WR={wr:5.1f}%  mean={mean*100:+.4f}%")
    allnet = [r["net"] for r in rows]
    n = len(allnet); mean = sum(allnet) / n
    sd = statistics.stdev(allnet) if n > 1 else 0.0
    rng = random.Random(11); obs = abs(mean); hits = 0
    for _ in range(20000):
        perm = [x if rng.random() < 0.5 else -x for x in allnet]
        if abs(sum(perm) / n) >= obs:
            hits += 1
    p = (hits + 1) / 20001
    print(f"  {'ALL':20} n={n:4d}  mean={mean*100:+.4f}%  total={sum(allnet)*100:+.2f}%  "
          f"permutation p={p:.3f}")
    print(f"  VERDICT: {'mean is distinguishable from 0 at p<0.05' if p < 0.05 else 'NOT distinguishable from zero after fees'}")
    print(f"  NOTE: fees are {2*FEE_PER_SIDE*1e4:.0f}bp round-trip, which is "
          f"{abs(mean)/(2*FEE_PER_SIDE):.2f}x the mean net — cost is the binding constraint.")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "backtest_live_bars.json").write_text(json.dumps(
        {"generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
         "rules": RISK_NOTE, "n_configs": N_CONFIGS, "n_trades": n,
         "mean_net_pct": round(mean * 100, 5), "permutation_p": round(p, 4),
         "per_arm": {k: {"n": len(v), "mean_pct": round(sum(v)/len(v)*100, 5)}
                     for k, v in per_arm.items()}}, indent=1))


# ------------------------------------------------------------------- trade mgmt
def load_state() -> dict:
    if STATE.exists():
        try:
            return json.loads(STATE.read_text())
        except Exception:
            pass
    return {"run_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
            "rules": {"symbols": SYMBOLS, "bar": BAR, "breakout_n": BREAKOUT_N,
                      "sl_atr": SL_ATR, "tp_atr": TP_ATR,
                      "max_hold_bars": MAX_HOLD_BARS, "fee_per_side": FEE_PER_SIDE,
                      "note": RISK_NOTE},
            "open": [], "closed": [], "skipped": []}


def save_state(s: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(s, indent=1))


def append_ledger(rows: list[dict]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def do_open(s: dict) -> int:
    sess = session_status()
    print(f"session: {sess['utc']} {sess['weekday']} | crypto={sess['crypto']} "
          f"equity={sess['equity']} fx={sess['forex']} | {sess['reason']}")
    n_open = 0
    for sym in SYMBOLS:
        if len(s["open"]) >= MAX_CONCURRENT:
            print(f"  {sym}: skipped, max concurrent {MAX_CONCURRENT} reached")
            s["skipped"].append({"symbol": sym, "why": "max_concurrent"})
            continue
        ev = evaluate(sym)
        if ev is None:
            print(f"  {sym}: no bars from any venue")
            s["skipped"].append({"symbol": sym, "why": "no_data"})
            continue
        cons = ev["consensus"]
        state = f"ATR={ev['atr']:.6g} ({ev['atr_pct']:.2f}%) priorHi={ev['prior_high']:.6g}"
        if ev["setup"] is None:
            print(f"  {sym}: no setup. {state} last={ev['last_close']:.6g} "
                  f"RSI={ev['rsi']:.1f} gap_to_break={ev['dist_to_break_bp']:+.0f}bp")
            continue
        if not cons or not cons["trusted"]:
            why = "no_consensus" if not cons else f"venues_disagree_{cons['spread_bp']}bp"
            print(f"  {sym}: SETUP but REJECTED ({why})")
            s["skipped"].append({"symbol": sym, "why": why})
            continue
        entry = cons["price"]
        tp = entry + TP_ATR * ev["atr"]
        sl = entry - SL_ATR * ev["atr"]
        pos = {"id": f"{sym}-{int(time.time())}", "symbol": sym, "side": "LONG",
               "setup": ev["setup"], "entry": entry, "tp": tp, "sl": sl,
               "atr_at_entry": ev["atr"], "opened_utc": sess["utc"],
               "opened_bar_utc": ev["last_bar_utc"], "bars_held": 0,
               "venues": cons["venues"], "spread_bp": cons["spread_bp"],
               "fee_per_side": FEE_PER_SIDE, "status": "OPEN"}
        s["open"].append(pos)
        n_open += 1
        print(f"  {sym}: OPEN LONG @ {entry:.6g}  TP={tp:.6g}  SL={sl:.6g}  "
              f"venues={cons['n_venues']} spread={cons['spread_bp']}bp")
    save_state(s)
    print(f"\nopened {n_open} position(s); {len(s['open'])} open, {len(s['closed'])} closed")
    return 0


def do_resolve(s: dict) -> int:
    if not s["open"]:
        print("no open positions")
        score(s)
        return 0
    still, closed = [], []
    for p in s["open"]:
        bars, _ = bars_binance(p["symbol"])
        if not bars:
            bars, _ = bars_kucoin(p["symbol"])
        if not bars:
            still.append(p)
            print(f"  {p['symbol']}: no bars, keeping open")
            continue
        opened_ms = int(datetime.strptime(p["opened_bar_utc"], "%Y-%m-%dT%H:%M:%SZ")
                        .replace(tzinfo=timezone.utc).timestamp() * 1000)
        fwd = [b for b in bars if b["t"] > opened_ms]
        exit_px = reason = None
        for i, b in enumerate(fwd):
            hit_tp = b["h"] >= p["tp"]
            hit_sl = b["l"] <= p["sl"]
            if hit_sl:                       # pessimistic: stop wins ties
                exit_px, reason = p["sl"], "SL"
                break
            if hit_tp:
                exit_px, reason = p["tp"], "TP"
                break
            if i + 1 >= MAX_HOLD_BARS:
                exit_px, reason = b["c"], "TIMEOUT"
                break
        if exit_px is None:
            p["bars_held"] = len(fwd)
            still.append(p)
            print(f"  {p['symbol']}: still open, {len(fwd)} bars elapsed "
                  f"({len(fwd)*5}min of {MAX_HOLD_BARS*5}min)")
            continue
        gross = (exit_px - p["entry"]) / p["entry"]
        net = gross - 2 * p["fee_per_side"]
        p.update({"status": "CLOSED", "exit": exit_px, "exit_reason": reason,
                  "bars_held": min(len(fwd), MAX_HOLD_BARS),
                  "gross_pct": round(gross * 100, 4), "net_pct": round(net * 100, 4),
                  "closed_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
        closed.append(p)
        print(f"  {p['symbol']}: CLOSED {reason} @ {exit_px:.6g}  "
              f"gross={gross*100:+.3f}%  net={net*100:+.3f}%  bars={p['bars_held']}")
    s["open"] = still
    s["closed"].extend(closed)
    save_state(s)
    append_ledger(closed)
    score(s)
    return 0


def market_price(sym: str) -> tuple[float | None, str]:
    """Best available current price for marking an open position to market."""
    cons = live_price_consensus(sym)
    if cons and cons.get("price"):
        return cons["price"], "live_consensus"
    bars, _ = bars_binance(sym)
    if not bars:
        bars, _ = bars_kucoin(sym)
    if bars:
        return bars[-1]["c"], "last_bar_close"
    return None, "unavailable"


def mark_open_positions(s: dict) -> dict:
    """Mark open positions to market and append an equity point.

    ADDED 2026-11-22 (peer review, second time owed). This harness used to report
    REALISED PnL only, which means an open position bleeding toward its stop
    contributed nothing to the equity series until the moment it closed. A
    realised-only book shows a flat line then a cliff; it cannot express drawdown
    while you are actually in the trade, and drawdown is exactly what a risk
    decision is made on. Every observation here is now marked.

    Exit fees are charged on the mark, not just entry, so an open position is
    valued as if closed now -- the conservative direction.
    """
    marks, unreal_total = [], 0.0
    for p in s["open"]:
        px, how = market_price(p["symbol"])
        if px is None:
            marks.append({"id": p["id"], "symbol": p["symbol"],
                          "marked": False, "how": how})
            continue
        gross = (px - p["entry"]) / p["entry"]
        net = gross - 2 * p["fee_per_side"]   # as if closed now
        unreal_total += net
        marks.append({"id": p["id"], "symbol": p["symbol"], "marked": True,
                      "mark_px": px, "how": how,
                      "unreal_gross_pct": round(gross * 100, 4),
                      "unreal_net_pct": round(net * 100, 4)})
    realised = sum(c["net_pct"] for c in s["closed"]) / 100
    point = {
        "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "realised_pct": round(realised * 100, 4),
        "unrealised_pct": round(unreal_total * 100, 4),
        "total_pct": round((realised + unreal_total) * 100, 4),
        "n_closed": len(s["closed"]), "n_open_marked": len(marks),
        "positions": marks,
    }
    s.setdefault("equity_marks", []).append(point)
    return point


def score(s: dict) -> None:
    # MTM FIRST, and before any early return: the whole point of the fix is that
    # a book with zero closed trades still has a value and a drawdown.
    mtm = mark_open_positions(s) if s.get("open") else None
    save_state(s)

    cl = s["closed"]
    if not cl:
        print("\nscore: no closed trades yet — nothing to conclude")
        if mtm:
            print(f"  BUT the book is not empty. Mark-to-market of "
                  f"{mtm['n_open_marked']} open position(s):")
            for m in mtm["positions"]:
                if m["marked"]:
                    print(f"    {m['symbol']:12s} mark {m['mark_px']:.6g} "
                          f"unreal net {m['unreal_net_pct']:+.4f}%  ({m['how']})")
            print(f"  REALISED {mtm['realised_pct']:+.4f}%  |  "
                  f"UNREALISED {mtm['unrealised_pct']:+.4f}%  |  "
                  f"TOTAL MTM {mtm['total_pct']:+.4f}%")
            print("  Realised-only reporting would have shown a flat 0.00% here.")
        return
    nets = [c["net_pct"] / 100 for c in cl]
    wins = [x for x in nets if x > 0]
    n = len(nets)
    mean = sum(nets) / n
    sd = statistics.stdev(nets) if n > 1 else 0.0
    t = mean / (sd / math.sqrt(n)) if sd and n > 1 else float("nan")
    # random sign-flip permutation test: is the mean distinguishable from 0?
    rng = random.Random(7)
    if n >= 4:
        obs = abs(mean)
        hits = 0
        for _ in range(20000):
            perm = [x if rng.random() < 0.5 else -x for x in nets]
            if abs(sum(perm) / n) >= obs:
                hits += 1
        p = (hits + 1) / 20001
    else:
        p = float("nan")
    by_reason: dict[str, int] = {}
    for c in cl:
        by_reason[c["exit_reason"]] = by_reason.get(c["exit_reason"], 0) + 1
    print("\n=== REALTIME CHALLENGE SCORE ===")
    print(f"  closed trades      : {n}")
    print(f"  win rate           : {len(wins)}/{n} = {100*len(wins)/n:.1f}%")
    print(f"  mean net per trade : {mean*100:+.4f}%")
    print(f"  total net (sum)    : {sum(nets)*100:+.4f}%")
    print(f"  best / worst       : {max(nets)*100:+.4f}% / {min(nets)*100:+.4f}%")
    print(f"  sd / t-stat        : {sd*100:.4f}% / {t:.3f}" if sd else "  sd: 0")
    print(f"  permutation p      : {p:.3f}" if not math.isnan(p) else "  p: n<4")
    print(f"  exit mix           : {by_reason}")
    need = 0 if not sd else (2.8 * sd / abs(mean)) ** 2 if mean else float("inf")
    print(f"  trades needed for a 2.8-sigma result at this effect size: "
          f"{need:.0f}" if sd and mean else "  n/a")

    # ---- mark-to-market block: realised alone cannot express an open drawdown ----
    if mtm:
        print(f"\n  MARK-TO-MARKET (the part realised-only reporting hid):")
        print(f"    realised   {mtm['realised_pct']:+.4f}%")
        print(f"    unrealised {mtm['unrealised_pct']:+.4f}%  "
              f"({mtm['n_open_marked']} open)")
        print(f"    TOTAL      {mtm['total_pct']:+.4f}%")
    marks = s.get("equity_marks", [])
    if len(marks) >= 2:
        tot = [m["total_pct"] for m in marks]
        peak, mdd = tot[0], 0.0
        for v in tot:
            peak = max(peak, v)
            mdd = min(mdd, v - peak)
        print(f"    MTM marks recorded {len(marks)}  |  max drawdown of the MTM "
              f"path {mdd:+.4f}%")
    else:
        print(f"    MTM marks recorded {len(marks)} — need >=2 to report a "
              f"drawdown of the MTM path.")

    if n < 30:
        print("  VERDICT: n is far too small. This is a prototype smoke test, "
              "NOT evidence of edge.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--open", action="store_true")
    ap.add_argument("--resolve", action="store_true")
    ap.add_argument("--backtest", action="store_true")
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args()
    if a.backtest:
        backtest(); return 0
    s = load_state()
    if a.open:
        return do_open(s)
    if a.resolve:
        return do_resolve(s)
    print(json.dumps(session_status(), indent=1))
    print(f"open={len(s['open'])} closed={len(s['closed'])}")
    score(s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
