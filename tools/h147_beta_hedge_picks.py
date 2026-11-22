"""H-147: is the resolved book's PnL selection skill, or beta?

For every resolved pick that carries an entry timestamp we re-express the trade
return net of the same-window benchmark return scaled by the instrument's beta
estimated over the 60 trading days ending at entry. If the book's edge survives
hedging it is selection; if it vanishes it was directional exposure.

Usage:
  python3 tools/h147_beta_hedge_picks.py --out reports/h147_beta_hedge_2026-11-20.json
"""
from __future__ import annotations

import argparse
import json
import math
import random
from collections import Counter
from datetime import datetime
from pathlib import Path

CRYPTO_SUFFIXES = ("USDT", "USDC", "USD", "BUSD")
CRYPTO_FIX = {"BTC": "BTC-USD", "ETH": "ETH-USD", "SOL": "SOL-USD", "XRP": "XRP-USD",
              "DOGE": "DOGE-USD", "ADA": "ADA-USD", "AVAX": "AVAX-USD", "LINK": "LINK-USD"}


def map_symbol(sym: str) -> str:
    s = (sym or "").strip().upper()
    for suf in CRYPTO_SUFFIXES:
        if s.endswith(suf) and len(s) > len(suf):
            base = s[: -len(suf)]
            if base in CRYPTO_FIX:
                return CRYPTO_FIX[base]
            return f"{base}-USD"
    return s


def parse_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def load_rows(path: Path):
    data = json.loads(path.read_text())
    rows = data["picks"]["recent_closed"]
    out = []
    for r in rows:
        et, xt = parse_dt(r.get("entry_time")), parse_dt(r.get("closed_at"))
        if not (et and xt) or xt <= et:
            continue
        try:
            pnl = float(r["pnl_pct"]) / 100.0
        except (TypeError, ValueError):
            continue
        out.append({
            "id": r.get("id"), "symbol": map_symbol(r.get("symbol")),
            "asset_class": (r.get("asset_class") or "?").upper(),
            "direction": (r.get("direction") or "?").upper(),
            "entry": et, "exit": xt, "pnl": pnl,
        })
    return out


def fetch_closes(symbols, start, end):
    import yfinance as yf

    df = yf.download(sorted(symbols), start=start, end=end, auto_adjust=True,
                     progress=False, threads=True)["Close"]
    if hasattr(df, "columns") is False:          # single ticker -> Series
        df = df.to_frame(symbols[0])
    return df.dropna(how="all")


def clip(x, lim):
    return max(-lim, min(lim, x))


def beta_of(sym_rets, bench_rets, window=60):
    """``sym_rets``/``bench_rets`` are {date: return} maps; align on shared dates.

    Taking "the last 60 of each" is wrong whenever the calendars differ (crypto
    trades 7 days a week, SPY 5), because the two windows then cover different
    dates and the covariance is meaningless.
    """
    shared = sorted(set(sym_rets) & set(bench_rets))[-window:]
    if len(shared) < 30:
        return None
    xs = [bench_rets[d] for d in shared]
    ys = [clip(sym_rets[d], 0.20) for d in shared]   # winsorise cryptos at +-20%/day
    n = len(shared)
    mx, my = sum(xs) / n, sum(ys) / n
    var = sum((x - mx) ** 2 for x in xs)
    if var <= 0:
        return None
    raw = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / var
    return clip(raw, 3.0)   # a daily-bar beta outside +-3 is an artefact, not a hedge ratio


def boot_ci(vals, iters=4000, seed=11):
    if len(vals) < 20:
        return (None, None)
    rng = random.Random(seed)
    n = len(vals)
    means = []
    for _ in range(iters):
        means.append(sum(vals[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    return (round(means[int(0.025 * iters)], 6), round(means[int(0.975 * iters) - 1], 6))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--picks", default="audit_dashboard/data/dashboard_data.json")
    ap.add_argument("--bench", default="SPY")
    ap.add_argument("--max-symbols", type=int, default=60)
    ap.add_argument("--out", default="reports/h147_beta_hedge_2026-11-20.json")
    args = ap.parse_args()

    rows = load_rows(Path(args.picks))
    counts = Counter(r["symbol"] for r in rows)
    keep = {s for s, _ in counts.most_common(args.max_symbols)}
    rows = [r for r in rows if r["symbol"] in keep]

    print(f"  rows with entry+exit timestamps: {len(rows)} across {len(keep)} symbols")
    syms = {r["symbol"] for r in rows}
    start = min(r["entry"] for r in rows).date()
    end = max(r["exit"] for r in rows).date()
    try:
        closes = fetch_closes(syms | {args.bench}, start, end)
    except Exception as exc:                                  # noqa: BLE001
        print(f"  FETCH FAILED: {exc}")
        raise SystemExit(1)
    print(f"  price panel: {closes.shape[0]} bars x {closes.shape[1]} symbols")

    bench = closes[args.bench].dropna()
    b_idx = {d.date(): i for i, d in enumerate(bench.index)}
    b_rets = {bench.index[i].date(): bench.iloc[i] / bench.iloc[i - 1] - 1
              for i in range(1, len(bench))}

    hedged, unhedged, betas = [], [], []
    win_returns, exposures = [], []
    same_day = no_beta = no_bar = 0
    per_class = {}
    for r in rows:
        sym = r["symbol"]
        if sym not in closes:
            no_bar += 1
            continue
        s = closes[sym].dropna()
        s_idx = {d.date(): i for i, d in enumerate(s.index)}
        si, xi = s_idx.get(r["entry"].date()), s_idx.get(r["exit"].date())
        bi, bx = b_idx.get(r["entry"].date()), b_idx.get(r["exit"].date())
        if si is None or xi is None or bi is None or bx is None:
            no_bar += 1
            continue
        if xi <= si:
            same_day += 1
            continue
        s_rets = {s.index[i].date(): s.iloc[i] / s.iloc[i - 1] - 1
                  for i in range(1, si + 1)}
        beta = beta_of(s_rets, b_rets)
        if beta is None:
            no_beta += 1
            continue
        spy_win = bench.iloc[bx] / bench.iloc[bi] - 1
        h = r["pnl"] - beta * spy_win
        hedged.append(h)
        win_returns.append(spy_win)
        exposures.append(beta * spy_win)
        unhedged.append(r["pnl"])
        betas.append(beta)
        d = per_class.setdefault(r["asset_class"], {"n": 0, "h": 0.0, "u": 0.0})
        d["n"] += 1
        d["h"] += h
        d["u"] += r["pnl"]

    def summarise(vals):
        if not vals:
            return {"n": 0}
        m = sum(vals) / len(vals)
        sv = sorted(vals)
        cut = int(len(sv) * 0.10)
        trimmed = (sum(sv[cut:len(sv) - cut]) / len(sv[cut:len(sv) - cut])
                   if len(sv) - 2 * cut > 0 else m)
        lo, hi = boot_ci(vals)
        return {"n": len(vals), "mean": round(m, 6),
                "trimmed_mean_10pct": round(trimmed, 6),
                "median": round(sv[len(sv) // 2], 6),
                "ci95": [lo, hi], "hit_rate": round(sum(1 for v in vals if v > 0) / len(vals), 4),
                "t_stat": round(m / (math.sqrt(sum((v - m) ** 2 for v in vals) / max(len(vals) - 1, 1)) / math.sqrt(len(vals))), 3) if len(vals) > 2 else None}

    out = {
        "benchmark": args.bench,
        "rows_with_timestamps": len(rows),
        "coverage": {"hedged": len(hedged), "same_day_unhedgeable": same_day,
                     "no_price_bar": no_bar, "insufficient_beta_history": no_beta},
        "unhedged": summarise(unhedged),
        "hedged": summarise(hedged),
        "decomposition": {
            "mean_benchmark_return_in_window": round(sum(win_returns) / len(win_returns), 5) if win_returns else None,
            "mean_beta_times_benchmark": round(sum(exposures) / len(exposures), 5) if exposures else None,
            "share_of_gross_pnl_from_exposure": None,
        },
        "beta": {"mean": round(sum(betas) / len(betas), 3) if betas else None,
                 "share_long_beta": round(sum(1 for b in betas if b > 0) / len(betas), 3) if betas else None},
        "per_class": {k: {"n": v["n"], "mean_unhedged": round(v["u"] / v["n"], 6),
                          "mean_hedged": round(v["h"] / v["n"], 6)} for k, v in sorted(per_class.items())},
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    print(f"  written -> {args.out}")


if __name__ == "__main__":
    main()
