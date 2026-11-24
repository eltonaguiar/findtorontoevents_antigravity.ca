#!/usr/bin/env python3
"""Measure one research cell and write results/cells/<SYMBOL>_<STRATEGY>_<HORIZON>.json.

Contract (per the cell ledger spec):
  n                       number of trades
  net mean bp per trade   after a 26bp round-turn cost
  95% bootstrap CI        percentile bootstrap over trades
  permutation p           signal-label permutation, not a t-test
  DSR                     deflated Sharpe, penalised for N_TRIALS

Strategy definitions are explicit and recorded IN the artifact, because
"trend_pullback" is only a name in the ledger - there was no canonical crypto
implementation to call. Writing the definition down is what makes the cell
reproducible; leaving it implicit is how two agents measure different things
under the same key.

Execution model, stated so it cannot be assumed away:
  * signal evaluated on the CLOSE of bar i
  * entry at the OPEN of bar i+1 (no look-ahead)
  * exit at the OPEN of bar i+1+h (h = horizon in bars)
  * cost 26bp round-turn charged once per trade

    python3 tools/measure_cell.py --symbol BTCUSDT --strategy trend_pullback --horizon 1d
"""
import argparse
import json
import math
import random
import statistics as st
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

COST_BP = 26.0
N_BOOT = 2000
N_PERM = 1000
N_TRIALS = 1000          # the ledger size: every cell is a trial
SEED = 20261124
HORIZON_BARS = {"1d": 1, "1h": 1, "4h": 1, "1w": 1}   # bars to hold


def load_bars(symbol, horizon):
    """Daily by default; 1h uses the committed cache if present."""
    from tools.crypto_bars import fetch_klines  # noqa: PLC0415

    interval = {"1d": "1d", "1h": "1h", "4h": "4h"}.get(horizon, "1d")
    resample_weekly = horizon == "1w"
    if interval == "1h":
        cache = REPO_ROOT / "data/cache" / f"{symbol}_3mo_1h.csv"
        if cache.exists():
            import csv  # noqa: PLC0415
            rows = list(csv.DictReader(open(cache)))
            if rows:
                return ([float(r.get("close") or r.get("Close")) for r in rows],
                        [float(r.get("open") or r.get("Open")) for r in rows],
                        f"cache:{cache.name}")
        return [], [], "no 1h cache"

    end = int(time.time() * 1000)
    start = end - 1000 * 24 * 3600 * 1000
    k = fetch_klines(symbol, interval, start, end)
    closes = [float(b["close"]) for b in k]
    opens = [float(b["open"]) for b in k]
    if resample_weekly:
        # crypto_bars has no weekly interval; bucket daily bars into 7s.
        # Recorded in bar_source so the resampling is visible, not implied.
        wc, wo = [], []
        for i in range(0, len(closes) - 6, 7):
            wo.append(opens[i])
            wc.append(closes[i + 6])
        return wc, wo, f"binance:1d resampled->1w ({len(wc)} bars from {len(closes)} daily)"
    return closes, opens, f"binance:{interval}"


def rsi(closes, n=14):
    out = [None] * len(closes)
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0.0))
        losses.append(max(-d, 0.0))
    if len(gains) < n:
        return out
    ag, al = sum(gains[:n]) / n, sum(losses[:n]) / n
    for i in range(n, len(gains)):
        ag = (ag * (n - 1) + gains[i]) / n
        al = (al * (n - 1) + losses[i]) / n
        out[i + 1] = 100.0 if al == 0 else 100.0 - 100.0 / (1 + ag / al)
    return out


def sma(xs, n):
    out = [None] * len(xs)
    run = 0.0
    for i, x in enumerate(xs):
        run += x
        if i >= n:
            run -= xs[i - n]
        if i >= n - 1:
            out[i] = run / n
    return out


def signals(closes, strategy):
    """Boolean entry signal per bar, evaluated on the close."""
    if strategy == "trend_pullback":
        # v2. v1 was `close>SMA50 AND RSI14<35`, whose conjunction is EMPTY:
        # over 1000 BTCUSDT daily bars, RSI<35 occurs 96 times and never once
        # while close>SMA50, because a sharp dip puts price under the 50-day.
        # Corrected to the conventional definition: uptrend intact, price
        # pulled back below its short MA. Chosen on SIGNAL-COUNT grounds before
        # any return was computed, and both versions are recorded in the
        # artifact so this is auditable.
        s50, s10 = sma(closes, 50), sma(closes, 10)
        return [bool(s50[i] and s10[i] and closes[i] > s50[i]
                     and closes[i] < s10[i])
                for i in range(len(closes))]
    if strategy == "breakout":
        s20 = sma(closes, 20)
        return [bool(i >= 20 and s20[i] and closes[i] > max(closes[i - 20:i]))
                for i in range(len(closes))]
    if strategy == "rsi2_pullback":
        r = rsi(closes, 7)
        return [bool(r[i] is not None and r[i] < 10.0) for i in range(len(closes))]
    if strategy == "donchian":
        s55 = sma(closes, 55)
        return [bool(i >= 55 and s55[i] and closes[i] == max(closes[i - 55:i + 1]))
                for i in range(len(closes))]
    raise SystemExit(f"unknown strategy {strategy!r} - define it before measuring")


def trades(sig, opens, h):
    """Non-overlapping trades, entry next open, exit open h bars later."""
    out, i, n = [], 0, len(sig)
    while i < n - h - 1:
        if sig[i]:
            entry, exit_ = opens[i + 1], opens[i + 1 + h]
            if entry > 0:
                out.append(exit_ / entry - 1.0)
            i += 1 + h          # do not stack overlapping trades
        else:
            i += 1
    return out


def boot_ci(xs, n_boot=N_BOOT, seed=SEED):
    rng = random.Random(seed)
    means = []
    n = len(xs)
    for _ in range(n_boot):
        means.append(st.mean(xs[rng.randrange(n)] for _ in range(n)))
    means.sort()
    return means[int(0.025 * n_boot)], means[int(0.975 * n_boot)]


def perm_p(sig, opens, h, observed, n_perm=N_PERM, seed=SEED):
    """Shuffle the signal labels; p = P(permuted mean >= observed)."""
    rng = random.Random(seed)
    s = list(sig)
    hits = 0
    for _ in range(n_perm):
        rng.shuffle(s)
        r = trades(s, opens, h)
        if len(r) >= 3 and st.mean(r) >= observed:
            hits += 1
    return hits / n_perm


def normal_cdf(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def dsr(rs, n_trials=N_TRIALS):
    """Deflated Sharpe Ratio (Bailey & Lopez de Prado).

    sr is per-trade; sr0 is the expected maximum Sharpe under the null across
    n_trials independent tries, sr0 = sqrt(2 ln N) / sqrt(n).
    """
    n = len(rs)
    if n < 8:
        return None
    sd = st.stdev(rs)
    if sd == 0:
        return None
    sr = st.mean(rs) / sd
    m = st.mean(rs)
    skew = (sum((x - m) ** 3 for x in rs) / n) / (sd ** 3)
    kurt = (sum((x - m) ** 4 for x in rs) / n) / (sd ** 4)
    sr0 = math.sqrt(2 * math.log(n_trials)) / math.sqrt(n)
    denom = math.sqrt(max(1e-12, 1 - skew * sr + (kurt - 1) / 4 * sr ** 2))
    z = (sr - sr0) * math.sqrt(n - 1) / denom
    return round(normal_cdf(z), 4)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--strategy", required=True)
    ap.add_argument("--horizon", default="1d")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    closes, opens, src = load_bars(args.symbol, args.horizon)
    bars = len(closes)
    out_path = Path(args.out or (REPO_ROOT / "results" / "cells" /
                                 f"{args.symbol}_{args.strategy}_{args.horizon}.json"))
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if bars < 100:
        payload = {"cell": f"{args.symbol}/{args.strategy}/{args.horizon}",
                   "verdict": "BLOCKED_NO_DATA", "bars": bars, "bar_source": src,
                   "measured_at": datetime.now(timezone.utc).isoformat()}
        out_path.write_text(json.dumps(payload, indent=2))
        print(f"  BLOCKED_NO_DATA  bars={bars} source={src}")
        print(f"  wrote {out_path}")
        return 0

    h = HORIZON_BARS.get(args.horizon, 1)
    sig = signals(closes, args.strategy)
    rs = trades(sig, opens, h)
    n = len(rs)

    if n < 30:
        payload = {"cell": f"{args.symbol}/{args.strategy}/{args.horizon}",
                   "verdict": "INSUFFICIENT_TRADES", "n": n, "bars": bars,
                   "bar_source": src, "trades_found": n,
                   "measured_at": datetime.now(timezone.utc).isoformat()}
        out_path.write_text(json.dumps(payload, indent=2))
        print(f"  INSUFFICIENT_TRADES  n={n} bars={bars}")
        print(f"  wrote {out_path}")
        return 0

    net = [r - COST_BP / 1e4 for r in rs]
    mean_net_bp = st.mean(net) * 1e4
    lo, hi = boot_ci(net)
    p = perm_p(sig, opens, h, st.mean(rs))
    d = dsr(net)

    verdict = "KILL"
    if lo > 0 and p < 0.05 and (d is None or d > 0.95):
        verdict = "PASS"
    elif hi > 0:
        verdict = "INCONCLUSIVE"

    payload = {
        "cell": f"{args.symbol}/{args.strategy}/{args.horizon}",
        "verdict": verdict,
        "n": n, "bars": bars, "bar_source": src,
        "strategy_definition": {
            "trend_pullback": "close>SMA50 and close<SMA10 (pullback within uptrend). v1 'close>SMA50 and RSI14<35' had an EMPTY conjunction and was discarded on signal-count grounds before measuring returns",
        }.get(args.strategy, args.strategy),
        "execution": "signal on close i; entry open i+1; exit open i+1+h",
        "horizon_bars": h,
        "cost_bp_round_turn": COST_BP,
        "gross_mean_bp": round(st.mean(rs) * 1e4, 2),
        "net_mean_bp": round(mean_net_bp, 2),
        "ci95_net_bp": [round(lo * 1e4, 2), round(hi * 1e4, 2)],
        "permutation_p": round(p, 4),
        "dsr": d,
        "n_trials_assumed": N_TRIALS,
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "seed": SEED,
    }
    out_path.write_text(json.dumps(payload, indent=2))

    print(f"  cell {payload['cell']}")
    print(f"  bars {bars} ({src})   trades n={n}")
    print(f"  gross {st.mean(rs)*1e4:+.2f}bp -> net {mean_net_bp:+.2f}bp after {COST_BP:.0f}bp")
    print(f"  95% CI [{lo*1e4:+.2f}, {hi*1e4:+.2f}] bp   perm p={p:.4f}   DSR={d}")
    print(f"  VERDICT {verdict}")
    print(f"  wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
