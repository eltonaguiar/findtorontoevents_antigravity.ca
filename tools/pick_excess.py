#!/usr/bin/env python3
"""
pick_excess.py — fill in the "excess return" column for LIVE picks.

Why this exists
---------------
Every doc in WIRED_IN says EQUITY / ETF / CRYPTO live picks have no excess-return
number, so their edge is UNKNOWN rather than proven. This tool measures it per pick
against the class benchmark over the pick's own holding window, and prints the
aggregates with a paired t-stat.

Conventions (fixed before looking at results)
---------------------------------------------
* Source of truth for trades: audit_dashboard/data/dashboard_data.json -> picks.recent_closed.
  One record per closed pick, with entry_price, exit_price, timestamp, closed_at, direction.
* Pick return follows the dashboard's own convention so the numbers reconcile with
  pnl_pct: long = exit/entry - 1, short = entry/exit - 1. Where |calc - pnl_pct| > 0.5pp
  the pick is counted as a data-quality miss and excluded from the headline.
* Benchmark is the class beta, not a peer strategy: EQUITY/ETF -> SPY, CRYPTO -> BTC-USD.
  Adjusted close, daily. Bench return is measured from the last close on/before the
  signal date to the last close on/before the close date.
* A pick whose benchmark window collapses to zero length (entry and exit resolve to the
  same trading day, e.g. a 20-minute crypto scalp) cannot have an excess return. Those
  are counted as `window_collapsed` and excluded, never scored as 0 excess.
* Excess is in percentage points: pick_ret - bench_ret. A SHORT that profits while SPY
  rises has positive excess; that is the point of comparing to beta.

Output: reports/pick_excess_returns.json  (+ printed table)
"""
import os, sys, json, math, bisect, argparse, time
from datetime import datetime, timezone

DASH = "audit_dashboard/data/dashboard_data.json"
CACHE = "data/cache/pick_excess"
OUT = "reports/pick_excess_returns.json"
BENCH = {"EQUITY": "SPY", "ETF": "SPY", "CRYPTO": "BTC-USD"}
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) research"}


# ---------------- data ----------------
def fetch_daily(sym, start_year=2025, end_year=2026):
    """Daily adjusted closes, cached as CSV. Explicit period1/period2 — the
    range=max&interval=1d form silently returns monthly bars."""
    os.makedirs(CACHE, exist_ok=True)
    cp = os.path.join(CACHE, f"{sym.replace('/', '-').replace('^', '')}_{start_year}_{end_year}.csv")
    if os.path.exists(cp):
        rows = [l.strip().split(",") for l in open(cp) if l.strip()]
        return [r[0] for r in rows], [float(r[1]) for r in rows]
    import requests
    p1 = int(datetime(start_year, 1, 1).timestamp())
    p2 = int(datetime(end_year, 11, 20).timestamp())
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
    last = None
    for attempt in range(4):
        try:
            r = requests.get(url, params={"period1": p1, "period2": p2, "interval": "1d",
                                          "events": "div,splits"}, headers=H, timeout=30)
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}")
            res = r.json()["chart"]["result"][0]
            ts, ind = res["timestamp"], res["indicators"]
            px = None
            if ind.get("adjclose"):
                px = ind["adjclose"][0].get("adjclose")
            if not px or len(px) != len(ts):
                px = ind["quote"][0]["close"]
            rows = [(datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d"), float(p))
                    for t, p in zip(ts, px) if p is not None and p == p and p > 0]
            if len(rows) < 30:
                raise RuntimeError(f"only {len(rows)} rows")
            with open(cp, "w") as f:
                f.write("\n".join(f"{d},{p}" for d, p in rows))
            return [r[0] for r in rows], [r[1] for r in rows]
        except Exception as e:
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"fetch {sym} failed: {last}")


class Bench:
    def __init__(self, sym):
        self.sym = sym
        self.dates, self.px = fetch_daily(sym)

    def close_on_or_before(self, day):
        i = bisect.bisect_right(self.dates, day) - 1
        if i < 0:
            return None, None
        return self.dates[i], self.px[i]


def parse_day(s):
    s = str(s or "").strip()
    if not s:
        return None
    try:
        v = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        try:
            v = datetime.strptime(s[:10], "%Y-%m-%d")
        except ValueError:
            return None
    if v.tzinfo:
        v = v.astimezone(timezone.utc).replace(tzinfo=None)
    return v


def pick_return(p):
    """Dashboard convention: long exit/entry-1, short entry/exit-1."""
    e, x = p.get("entry_price"), p.get("exit_price")
    if not e or not x or e <= 0 or x <= 0:
        return None
    d = (p.get("direction") or "").upper()
    if d in ("LONG", "BUY"):
        return (x / e - 1.0) * 100.0
    if d in ("SHORT", "SELL"):
        return (e / x - 1.0) * 100.0
    return None


def tstat(xs):
    n = len(xs)
    if n < 2:
        return None
    m = sum(xs) / n
    v = sum((x - m) ** 2 for x in xs) / (n - 1)
    s = math.sqrt(v)
    return m / (s / math.sqrt(n)) if s > 0 else None


def cluster_t(rows):
    """Picks closed on the same pair of days share one market move, so their returns are
    not independent observations. Collapse each (entry_day, exit_day) window to its mean
    excess and run the t-stat over windows, not over picks. A strategy with 8 clones of a
    single 6-month window has n_windows=1 and therefore no t-stat at all."""
    g = {}
    for r in rows:
        g.setdefault((r["entry_day"], r["exit_day"]), []).append(r["excess_pp"])
    clusters = [sum(v) / len(v) for v in g.values()]
    return tstat(clusters), len(clusters)


def agg(rows, key):
    out = []
    g = {}
    for r in rows:
        g.setdefault(r[key], []).append(r)
    for k, rs in g.items():
        ex = [r["excess_pp"] for r in rs]
        m = sum(ex) / len(ex)
        t_cl, n_win = cluster_t(rs)
        out.append({
            key: k,
            "n": len(rs),
            "n_windows": n_win,
            "mean_excess_pp": m,
            "median_excess_pp": sorted(ex)[len(ex) // 2],
            "t_stat": tstat(ex),
            "t_cluster": t_cl,
            "excess_win_rate_pct": 100.0 * sum(1 for x in ex if x > 0) / len(ex),
            "mean_pick_ret_pct": sum(r["ret_pick_pct"] for r in rs) / len(rs),
            "mean_bench_ret_pct": sum(r["ret_bench_pct"] for r in rs) / len(rs),
            "sum_excess_pp": sum(ex),
        })
    out.sort(key=lambda d: (-(d["mean_excess_pp"] if d["mean_excess_pp"] is not None else 0)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dashboard", default=DASH)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--min-n", type=int, default=5, help="min picks to headline a strategy")
    ap.add_argument("--classes", default="EQUITY,ETF,CRYPTO")
    a = ap.parse_args()

    classes = [c.strip().upper() for c in a.classes.split(",") if c.strip()]
    print(f"loading {a.dashboard}")
    d = json.load(open(a.dashboard))
    rc = d["picks"]["recent_closed"]
    print(f"  recent_closed {len(rc)} picks | generated_at {d.get('generated_at')}")

    bench = {s: Bench(s) for s in sorted(set(BENCH[c] for c in classes if c in BENCH))}
    for s, b in bench.items():
        print(f"  bench {s}: {len(b.dates)} rows {b.dates[0]}..{b.dates[-1]}")

    scored, drop = [], {"no_price": 0, "no_dates": 0, "pnl_mismatch": 0, "window_collapsed": 0,
                        "no_bench_class": 0}
    for p in rc:
        cls = (p.get("asset_class") or "").upper()
        if cls not in classes:
            continue
        sym = BENCH.get(cls)
        if not sym:
            drop["no_bench_class"] += 1
            continue
        e, x = p.get("entry_price"), p.get("exit_price")
        if not e or not x or e <= 0 or x <= 0:
            drop["no_price"] += 1
            continue
        t0 = parse_day(p.get("timestamp") or p.get("entry_time"))
        t1 = parse_day(p.get("closed_at"))
        if not t0 or not t1 or t1 < t0:
            drop["no_dates"] += 1
            continue
        rp = pick_return(p)
        if rp is None:
            drop["no_price"] += 1
            continue
        rep = p.get("pnl_pct")
        if rep is not None and abs(rp - rep) > 0.5:
            drop["pnl_mismatch"] += 1
            continue
        b = bench[sym]
        d0, p0 = b.close_on_or_before(t0.strftime("%Y-%m-%d"))
        d1, p1 = b.close_on_or_before(t1.strftime("%Y-%m-%d"))
        if not d0 or not d1 or d0 >= d1:
            drop["window_collapsed"] += 1
            continue
        rb = (p1 / p0 - 1.0) * 100.0
        scored.append({
            "id": p.get("id"), "asset_class": cls, "strategy": p.get("strategy"),
            "symbol": p.get("symbol"), "direction": (p.get("direction") or "").upper(),
            "entry_day": d0, "exit_day": d1,
            "hold_hours": round((t1 - t0).total_seconds() / 3600.0, 2),
            "ret_pick_pct": rp, "ret_bench_pct": rb, "excess_pp": rp - rb,
            "exit_reason": p.get("exit_reason"), "benchmark": sym,
        })

    print(f"\nscored {len(scored)} picks | dropped {drop}")
    by_class = agg(scored, "asset_class")
    by_strategy = [r for r in agg(scored, "strategy") if r["n"] >= a.min_n]

    print(f"\n{'class':<8}{'n':>5}{'windows':>8}{'pick%':>8}{'bench%':>8}{'excess':>8}{'t_clust':>8}{'excWR':>7}")
    for r in by_class:
        t = f"{r['t_cluster']:.2f}" if r["t_cluster"] is not None else "n/a"
        print(f"{r['asset_class']:<8}{r['n']:>5}{r['n_windows']:>8}{r['mean_pick_ret_pct']:>7.2f}%"
              f"{r['mean_bench_ret_pct']:>7.2f}%{r['mean_excess_pp']:>7.2f}%"
              f"{t:>8}{r['excess_win_rate_pct']:>6.1f}%")

    print(f"\nper strategy (n>={a.min_n}): best 8 / worst 8 of {len(by_strategy)}")
    for r in (by_strategy[:8] + [None] + by_strategy[-8:]):
        if r is None:
            print("  " + "-" * 84)
            continue
        t = f"{r['t_cluster']:.2f}" if r["t_cluster"] is not None else "n/a"
        print(f"  {r['strategy'][:34]:<34}{r['n']:>5}{r['n_windows']:>6}w{r['mean_excess_pp']:>8.2f}pp"
              f"{t:>8}  excWR {r['excess_win_rate_pct']:>5.1f}%")

    payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": a.dashboard,
        "source_generated_at": d.get("generated_at"),
        "conventions": {
            "pick_return": "dashboard convention: long exit/entry-1, short entry/exit-1",
            "benchmark": BENCH,
            "window": "last close on/before signal date -> last close on/before close date",
            "excess_units": "percentage points, pick - benchmark",
            "excluded": "zero-length benchmark window, |calc-pnl_pct|>0.5pp, missing prices",
            "independence": "t_cluster collapses picks sharing one (entry_day, exit_day) window "
                            "to a single observation; t_stat is the naive per-pick version and "
                            "overstates significance whenever a strategy fires in batches",
        },
        "coverage": {"scored": len(scored), "dropped": drop},
        "by_class": by_class,
        "by_strategy": agg(scored, "strategy"),
        "min_n_headline": a.min_n,
        "picks": scored,
    }
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump(payload, open(a.out, "w"), indent=1)
    print(f"\nwrote {a.out}")
    return payload


if __name__ == "__main__":
    main()
