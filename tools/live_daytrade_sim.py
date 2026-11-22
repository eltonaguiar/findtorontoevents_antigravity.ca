#!/usr/bin/env python3
"""Live parallel day-trading paper sim.

Architecture: DETERMINISTIC REPLAY + DEDUP PERSISTENCE.
  - Every run re-fetches bars, replays full history, and regenerates every trade.
  - So the report is always the authoritative truth for the current bar data; there is no
    mutable position state that can drift or corrupt.
  - Newly-seen closed trades are appended to trades.jsonl, de-duplicated by trade_id.
  - That makes the job idempotent: run it 100x and the ledger is unchanged.

Honesty rules baked in:
  - Signal is evaluated at bar CLOSE i, fill happens at OPEN of bar i+1 (no look-ahead).
  - The entry bar itself is checked for the stop-out (conservative).
  - When stop and target are both inside the same bar, the STOP is assumed to hit first.
  - Costs are charged on BOTH sides: 12 bp round-trip crypto, 4 bp equities.
  - 1% of book risked per trade, notional capped at 1x book (no leverage).
  - No parameter search is performed here; these are fixed pre-registered settings.

Usage:
  python3 tools/live_daytrade_sim.py              # run + persist + scoreboard
  python3 tools/live_daytrade_sim.py --no-persist # scoreboard only
  python3 tools/live_daytrade_sim.py --gates      # show promotion gate status
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
SD = ROOT / "paper_trading" / "live_sim"
BARSD = SD / "bars"
SD.mkdir(parents=True, exist_ok=True)
BARSD.mkdir(parents=True, exist_ok=True)

TRADES = SD / "trades.jsonl"
STATE = SD / "state.json"
RUNS = SD / "runs.jsonl"

BOOK = 1000.0
RISK_PCT = 0.01
CACHE_TTL = 240  # seconds

VENUES = {
    "CRYPTO": {"BTC-USD", "ETH-USD", "SOL-USD"},
    "EQUITY": {"SPY", "QQQ", "AAPL"},
}
COST_BPS = {"CRYPTO": 12.0, "EQUITY": 4.0}

# ----- gates: pre-registered, not tunable per-run -----------------------------
GATE_JUDGE_N = 30       # below this: no verdict
GATE_PROMOTE_N = 200    # forward sample needed before a promotion review
GATE_T = 2.0            # per-trade t-stat for CANDIDATE
GATE_T_PROMOTE = 3.0
GATE_PF = 1.15          # profit factor
GATE_MIN_AVG = 0.0      # average net trade must be > 0


# ----------------------------------------------------------------------------- data
def fetch(sym: str, interval: str, period: str) -> pd.DataFrame | None:
    import yfinance as yf

    f = BARSD / f"{sym.replace('-', '_')}_{interval}.csv"
    df = None
    if f.exists() and (time.time() - f.stat().st_mtime) < CACHE_TTL:
        try:
            df = pd.read_csv(f, index_col=0, parse_dates=True)
        except Exception:
            df = None
    if df is None or len(df) == 0:
        try:
            d = yf.download(sym, interval=interval, period=period, progress=False,
                            auto_adjust=False, threads=False)
        except Exception as e:
            print(f"  ! fetch {sym} {interval}: {type(e).__name__}: {str(e)[:60]}", file=sys.stderr)
            d = None
        if d is None or len(d) == 0:
            if not f.exists():
                return None
            df = pd.read_csv(f, index_col=0, parse_dates=True)
        else:
            if isinstance(d.columns, pd.MultiIndex):
                d.columns = [c[0] for c in d.columns]
            d = d[["Open", "High", "Low", "Close", "Volume"]].dropna()
            d.to_csv(f)
            df = d
    df.index = pd.to_datetime(df.index, utc=True)
    return df.sort_index()


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    pc = df.Close.shift()
    tr = pd.concat([df.High - df.Low, (df.High - pc).abs(), (df.Low - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / n, adjust=False).mean()


# ------------------------------------------------------------------------ strategies
def s_donchian(df: pd.DataFrame, look: int = 24) -> pd.Series:
    """Trend: break of the prior `look`-bar extreme; hold until the flip."""
    hi = df.High.rolling(look).max().shift(1)
    lo = df.Low.rolling(look).min().shift(1)
    s = pd.Series(0.0, index=df.index)
    s[df.Close > hi] = 1.0
    s[df.Close < lo] = -1.0
    return s.replace(0.0, np.nan).ffill().fillna(0.0)


def s_zrevert(df: pd.DataFrame, w: int = 96, entry_z: float = 2.0, exit_z: float = 0.35) -> pd.Series:
    """Mean reversion: fade a 2-sigma stretch from the rolling mean, exit near the mean."""
    m = df.Close.rolling(w).mean()
    sd = df.Close.rolling(w).std()
    z = (df.Close - m) / sd.replace(0, np.nan)
    s = pd.Series(0.0, index=df.index)
    s[z < -entry_z] = 1.0
    s[z > entry_z] = -1.0
    s[z.abs() < exit_z] = 0.0
    return s.fillna(0.0)


def s_ema(df: pd.DataFrame, fast: int = 9, slow: int = 21) -> pd.Series:
    """Trend: persistent side from the EMA relationship."""
    ef = df.Close.ewm(span=fast, adjust=False).mean()
    es = df.Close.ewm(span=slow, adjust=False).mean()
    s = pd.Series(np.where(ef > es, 1.0, -1.0), index=df.index)
    return s


def s_orb(df: pd.DataFrame, opening_bars: int = 12, bars_per_day: int = 288) -> pd.Series:
    """Day trade: first break of the opening range, one shot per session."""
    s = pd.Series(0.0, index=df.index)
    d = df.index.floor("D")
    pos = 0
    for _, sub in df.groupby(d):
        if len(sub) < opening_bars + 2:
            continue
        hi = float(sub.High.iloc[:opening_bars].max())
        lo = float(sub.Low.iloc[:opening_bars].min())
        side = 0.0
        for k in range(opening_bars, len(sub)):
            c = float(sub.Close.iloc[k])
            if side == 0.0:
                if c > hi:
                    side = 1.0
                elif c < lo:
                    side = -1.0
            s.iloc[pos + k] = side
        pos += len(sub)
    return s


def s_rsi2(df: pd.DataFrame, lo: float = 10.0, hi: float = 90.0) -> pd.Series:
    """Short-term swing: buy the 2-period oversold pop, exit as RSI normalises."""
    delta = df.Close.diff()
    up = delta.clip(lower=0).ewm(alpha=0.5, adjust=False).mean()
    dn = (-delta).clip(lower=0).ewm(alpha=0.5, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    rsi = 100 - 100 / (1 + rs)
    s = pd.Series(0.0, index=df.index)
    s[rsi < lo] = 1.0
    s[rsi > hi] = -1.0
    s[(rsi > 45) & (rsi < 55)] = 0.0
    return s.fillna(0.0)


STRATEGIES = [
    # id, venue, interval, period, fn, stop_mult, tp_mult, max_hold_bars, trail, cooldown_bars
    ("S1_DONCHIAN_5M", "CRYPTO", "5m", "1mo", s_donchian, 1.5, 3.0, 48, True, 6),
    ("S2_ZREVERT_5M",  "CRYPTO", "5m", "1mo", s_zrevert,  2.0, 2.0, 24, False, 6),
    ("S3_EMATREND_1H", "CRYPTO", "1h", "6mo", s_ema,      2.5, 6.0, 120, True, 3),
    ("S4_ORB_5M",      "CRYPTO", "5m", "1mo", s_orb,      2.0, 3.0, 140, False, 3),
    ("S5_RSI2_1H",     "CRYPTO", "1h", "6mo", s_rsi2,     2.0, 3.0, 12, False, 3),
    ("S6_DONCHIAN_EQ", "EQUITY", "5m", "1mo", s_donchian, 1.5, 3.0, 48, True, 6),
    ("S7_ORB_EQ",      "EQUITY", "5m", "1mo", s_orb,      2.0, 3.0, 70, False, 3),
]


# --------------------------------------------------------------------------- engine
def simulate(df: pd.DataFrame, sig: pd.Series, a: pd.Series, cost_bps: float,
             sl_mult: float, tp_mult: float, max_hold: int, trail: bool,
             sid: str, sym: str, book: float = BOOK, cooldown: int = 0,
             min_tp_bps: float = 0.0) -> list[dict]:
    o, h, l = df.Open.values, df.High.values, df.Low.values
    av = a.values
    sg = sig.values
    idx = df.index
    n = len(df)
    half = cost_bps / 1e4 / 2.0
    out: list[dict] = []
    pos = None
    cd = 0  # bar index before which no new entry is allowed

    for i in range(n - 1):
        j = i + 1
        if pos is None and i < cd:
            continue
        if pos is None:
            s = float(sg[i]) if np.isfinite(av[i]) and av[i] > 0 else 0.0
            if s != 0.0 and np.isfinite(av[i]) and av[i] > 0:
                entry = float(o[j])
                stop = entry - s * sl_mult * float(av[i])
                tgt = entry + s * tp_mult * float(av[i])
                risk = abs(entry - stop)
                # cost gate: skip trades whose target is too small to clear the round-trip cost
                if entry > 0 and min_tp_bps > 0 and (abs(float(av[i])) * tp_mult / entry * 1e4) < min_tp_bps:
                    continue
                if risk > 0 and entry > 0:
                    units = min(book * RISK_PCT / risk, book / entry)
                    if units * entry >= 1.0:
                        pos = dict(side=s, entry=entry, stop=stop, tgt=tgt, units=units,
                                   i0=j, fee=units * entry * half)
        if pos is None:
            continue

        s = pos["side"]
        exit_px = None
        reason = None
        if s > 0 and l[j] <= pos["stop"]:
            exit_px, reason = pos["stop"], "SL"
        elif s < 0 and h[j] >= pos["stop"]:
            exit_px, reason = pos["stop"], "SL"
        elif s > 0 and h[j] >= pos["tgt"]:
            exit_px, reason = pos["tgt"], "TP"
        elif s < 0 and l[j] <= pos["tgt"]:
            exit_px, reason = pos["tgt"], "TP"
        elif (j - pos["i0"]) >= max_hold:
            exit_px, reason = float(o[j]), "TIME"
        elif sg[i] != s:
            exit_px, reason = float(o[j]), "SIGNAL"

        if exit_px is None:
            if trail and j > 0:
                cand = float(df.Close.values[j]) - s * sl_mult * float(av[j]) if np.isfinite(av[j]) else None
                if cand is not None:
                    pos["stop"] = max(pos["stop"], cand) if s > 0 else min(pos["stop"], cand)
            continue

        gross = s * (exit_px - pos["entry"]) * pos["units"]
        fees = pos["fee"] + pos["units"] * exit_px * half
        pnl = gross - fees
        out.append({
            "id": f"{sid}|{sym}|{pd.Timestamp(idx[pos['i0']]).isoformat()}",
            "strategy": sid, "symbol": sym,
            "entry_ts": pd.Timestamp(idx[pos["i0"]]).isoformat(),
            "exit_ts": pd.Timestamp(idx[j]).isoformat(),
            "side": int(s), "entry": round(pos["entry"], 6), "exit": round(exit_px, 6),
            "units": round(pos["units"], 8), "bars": int(j - pos["i0"]),
            "reason": reason, "gross": round(gross, 4), "fees": round(fees, 4),
            "pnl": round(pnl, 4), "ret_pct_book": round(pnl / book * 100, 5),
        })
        pos = None
        cd = j + cooldown
    return out


# -------------------------------------------------------------------------- scoring
def stats(trades: list[dict], book: float = BOOK) -> dict:
    n = len(trades)
    if n == 0:
        return dict(n=0)
    pnl = np.array([t["pnl"] for t in trades], dtype=float)
    ret = pnl / book
    wins = pnl[pnl > 0]
    losses = pnl[pnl <= 0]
    pf = (wins.sum() / abs(losses.sum())) if losses.sum() != 0 else float("inf")
    sd = ret.std(ddof=1) if n > 1 else 0.0
    t = float(ret.mean() / (sd / math.sqrt(n))) if sd > 0 else 0.0
    eq = np.cumsum(pnl)
    dd = float((np.maximum.accumulate(eq) - eq).max()) if n else 0.0
    return {
        "n": n, "wr_pct": round(100 * len(wins) / n, 2),
        "avg_win": round(float(wins.mean()), 3) if len(wins) else 0.0,
        "avg_loss": round(float(losses.mean()), 3) if len(losses) else 0.0,
        "avg_net": round(float(pnl.mean()), 4),
        "total_pnl": round(float(pnl.sum()), 3),
        "pf": round(pf, 3) if pf != float("inf") else 99.0,
        "total_gross": round(float(sum(t_["gross"] for t_ in trades)), 3),
        "avg_gross": round(float(np.mean([t_["gross"] for t_ in trades])), 4),
        "t": round(t, 2), "max_dd_usd": round(dd, 3),
        "avg_bars": round(float(np.mean([t_["bars"] for t_ in trades])), 1),
        "fees_paid": round(float(sum(t_["fees"] for t_ in trades)), 3),
    }


def verdict(st: dict) -> str:
    n = st.get("n", 0)
    if n < GATE_JUDGE_N:
        return "INSUFFICIENT_N"
    if st["avg_net"] <= GATE_MIN_AVG or st["pf"] < GATE_PF:
        return "NO-EDGE"
    if n >= GATE_PROMOTE_N and st["t"] >= GATE_T_PROMOTE:
        return "PROMOTE-REVIEW"
    if st["t"] >= GATE_T:
        return "CANDIDATE"
    return "DIRECTIONAL"


# ----------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-persist", action="store_true")
    ap.add_argument("--gates", action="store_true")
    ap.add_argument("--only", default=None, help="substring filter on strategy id")
    ap.add_argument("--min-tp-bps", type=float, default=0.0,
                    help="skip trades whose ATR-based target is below this many bp")
    args = ap.parse_args()

    run_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    all_trades: list[dict] = []
    per_strat: dict[str, dict] = {}
    print(f"=== LIVE DAY-TRADE PAPER SIM  {run_ts} ===")
    print(f"    venue cost: crypto {COST_BPS['CRYPTO']}bp round-trip, equity {COST_BPS['EQUITY']}bp | "
          f"risk {RISK_PCT*100:.0f}%/trade | min target {args.min_tp_bps or 0:.0f}bp\n")

    for sid, venue, interval, period, fn, sl, tp, hold, trail, cd in STRATEGIES:
        if args.only and args.only.upper() not in sid:
            continue
        strat_trades: list[dict] = []
        for sym in sorted(VENUES[venue]):
            df = fetch(sym, interval, period)
            if df is None or len(df) < 120:
                print(f"  - {sid:16s} {sym:8s} no data")
                continue
            a = atr(df, 14)
            try:
                sig = fn(df)
            except Exception as e:
                print(f"  - {sid:16s} {sym:8s} signal error {type(e).__name__}: {str(e)[:50]}")
                continue
            try:
                tr = simulate(df, sig, a, COST_BPS[venue], sl, tp, hold, trail, sid, sym,
                              cooldown=cd, min_tp_bps=args.min_tp_bps)
            except Exception as e:
                print(f"  - {sid:16s} {sym:8s} sim error {type(e).__name__}: {str(e)[:50]}")
                continue
            strat_trades.extend(tr)
            st = stats(tr)
            print(f"  - {sid:16s} {sym:8s} bars={len(df):5d}  n={st.get('n',0):4d}  "
                  f"net=${st.get('total_pnl',0):+8.2f}  avg={st.get('avg_net',0):+7.4f}  "
                  f"wr={st.get('wr_pct',0):5.1f}%  pf={st.get('pf',0):5.2f}  t={st.get('t',0):+5.2f}")
        st = stats(strat_trades)
        per_strat[sid] = st
        all_trades.extend(strat_trades)

    # ----- persist (dedup by trade id)
    new = 0
    if not args.no_persist:
        seen = set()
        if TRADES.exists():
            with TRADES.open() as fh:
                for line in fh:
                    try:
                        seen.add(json.loads(line)["id"])
                    except Exception:
                        pass
        with TRADES.open("a") as fh:
            for t in sorted(all_trades, key=lambda x: x["exit_ts"]):
                if t["id"] not in seen:
                    fh.write(json.dumps(t, sort_keys=True) + "\n")
                    seen.add(t["id"])
                    new += 1
        summary = {"run_ts": run_ts, "trades_total": len(all_trades), "trades_new": new,
                   "per_strategy": per_strat}
        with RUNS.open("a") as fh:
            fh.write(json.dumps(summary, sort_keys=True) + "\n")
        STATE.write_text(json.dumps({"last_run": run_ts, "trades_total": len(all_trades),
                                     "trades_new": new,
                                     "per_strategy": per_strat}, indent=2) + "\n")

    # ----- scoreboard
    print("\n=== SCOREBOARD (pre-registered gates) ===")
    print(f"{'strategy':17s} {'n':>5s} {'gross$':>9s} {'net$':>9s} {'avg$':>8s} {'wr%':>6s} {'pf':>6s} "
          f"{'t':>6s} {'fees':>8s} {'maxDD':>8s}  verdict")
    rows = []
    for sid, st in sorted(per_strat.items(), key=lambda kv: -kv[1].get("total_pnl", 0)):
        v = verdict(st)
        print(f"{sid:17s} {st.get('n',0):5d} {st.get('total_gross',0):+9.2f} {st.get('total_pnl',0):+9.2f} "
              f"{st.get('avg_net',0):+8.4f} {st.get('wr_pct',0):6.1f} {st.get('pf',0):6.2f} "
              f"{st.get('t',0):+6.2f} {st.get('fees_paid',0):8.2f} {st.get('max_dd_usd',0):8.2f}  {v}")
        rows.append((sid, v))

    tot = stats(all_trades)
    print(f"\n{'TOTAL':17s} {tot.get('n',0):5d} {tot.get('total_gross',0):+9.2f} {tot.get('total_pnl',0):+9.2f} "
          f"{tot.get('avg_net',0):+8.4f} {tot.get('wr_pct',0):6.1f} {tot.get('pf',0):6.2f} "
          f"{tot.get('t',0):+6.2f} {tot.get('fees_paid',0):8.2f} {tot.get('max_dd_usd',0):8.2f}  {verdict(tot)}")
    g = tot.get("total_gross", 0.0)
    f = tot.get("fees_paid", 0.0)
    print(f"\ncost audit: gross ${g:+.2f}, fees ${f:.2f}, net ${tot.get('total_pnl',0):+.2f} "
          f"-> fees ate {100*f/abs(g) if g else float('inf'):.0f}% of gross edge; "
          f"signal-only verdict = {'EDGE' if g > 0 else 'NO EDGE'}")
    if not args.no_persist:
        print(f"persisted: {new} new trade(s) -> {TRADES.relative_to(ROOT)}")

    if args.gates:
        print("\n=== GATE DETAIL ===")
        print(f"judge at n>={GATE_JUDGE_N}; CANDIDATE needs avg>0 & PF>={GATE_PF} & t>={GATE_T}; "
              f"PROMOTE-REVIEW needs n>={GATE_PROMOTE_N} & t>={GATE_T_PROMOTE}")
        for sid, v in rows:
            print(f"  {sid:17s} {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
