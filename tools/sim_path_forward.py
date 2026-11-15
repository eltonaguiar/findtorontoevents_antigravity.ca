#!/usr/bin/env python3
"""
sim_path_forward.py — pre-registered backtest of the "path forward" claim.

Claim under test
----------------
"The realistic path forward (low-cost beta core + a slow trend/dual-momentum overlay,
occasionally a short-horizon swing rule) is profitable after costs and beats a
matched-exposure benchmark."

Design rules (fixed BEFORE results were seen — no parameter search):
  * 8 strategies, listed in STRATEGIES. Trial count N=8 used for the deflated Sharpe.
  * Parameters are textbook defaults, not tuned: Faber 10-month SMA, 12-month
    momentum, RSI(2)<5, 200-day SMA, 60/40.
  * Costs applied on every position change. No cost-free run is reported as a result.
  * Split: IS 2003-01..2015-12, OOS 2016-01..2026-11 (BTC: IS 2014-10..2020-12).
  * Benchmark for every strategy = its OWN exposure in SPY + cash. Absolute
    profitability is never reported as an edge.

Data: Yahoo chart API, adjusted close (dividends + splits). Cached under data/cache/sim.
Output: reports/backtest_path_forward.json
"""
import os, sys, json, math, time, hashlib, argparse
from datetime import datetime, timezone
import numpy as np

CACHE = "data/cache/sim"
OUT = "reports/backtest_path_forward.json"
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) research"}
PPY = {"1d": 252, "1mo": 12}

# ---- pre-registered trial registry (N=8). Adding a strategy invalidates the DSR. ----
STRATEGIES = [
    ("BH_SPY",         "monthly", "beta core",            "hold SPY"),
    ("SIXTY_FORTY",    "monthly", "beta core",            "60% SPY / 40% TLT, monthly rebalance"),
    ("FABER10_SPY",    "monthly", "trend overlay",        "SPY if month-end close > 10M SMA, else T-bills"),
    ("DUALMOM_2",      "monthly", "trend overlay",        "12M momentum SPY vs TLT; hold winner if >0, else cash"),
    ("DUALMOM_3",      "monthly", "trend overlay",        "12M momentum SPY vs TLT vs GLD; best if >0, else cash"),
    ("RSI2_SPY",       "daily",   "swing",                "RSI(2)<5 & close>200SMA; exit close>5SMA|RSI>65|10d"),
    ("BTC_BH",         "daily",   "beta core",            "hold BTC"),
    ("BTC_TREND200",   "daily",   "trend overlay",        "BTC if close > 200SMA, else cash"),
]
COST_BPS = {"equity": 6.0, "btc": 15.0}   # per side: commission+spread+slippage


def _cache_path(sym, itv, p1, p2):
    key = f"{sym}_{itv}_{p1}_{p2}".replace("/", "-").replace("^", "")
    return os.path.join(CACHE, key + ".csv")


def fetch(sym, itv, start_year, end_year=2026):
    """Return (dates: np.array[str], prices: np.array[float]) of adjusted close."""
    os.makedirs(CACHE, exist_ok=True)
    p1 = int(datetime(start_year, 1, 1).timestamp())
    p2 = int(datetime(end_year, 11, 20).timestamp())
    cp = _cache_path(sym, itv, p1, p2)
    if os.path.exists(cp):
        rows = [l.strip().split(",") for l in open(cp) if l.strip()]
        return np.array([r[0] for r in rows]), np.array([float(r[1]) for r in rows])
    import requests
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
    last = None
    for attempt in range(4):
        try:
            r = requests.get(url, params={"period1": p1, "period2": p2, "interval": itv,
                                          "events": "div,splits"}, headers=H, timeout=30)
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}")
            res = r.json()["chart"]["result"][0]
            ts = res["timestamp"]
            ind = res["indicators"]
            px = None
            if ind.get("adjclose"):
                px = ind["adjclose"][0].get("adjclose")
            if px is None or len(px) != len(ts):
                px = ind["quote"][0]["close"]
            rows = [(datetime.utcfromtimestamp(t).strftime("%Y-%m-%d"), float(p))
                    for t, p in zip(ts, px) if p is not None and p == p and p > 0]
            if len(rows) < 30:
                raise RuntimeError(f"only {len(rows)} rows")
            with open(cp, "w") as f:
                f.write("\n".join(f"{d},{p}" for d, p in rows))
            return np.array([r[0] for r in rows]), np.array([r[1] for r in rows])
        except Exception as e:
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"fetch {sym} {itv} failed: {last}")


def fetch_cash_rate(start_year):
    """Daily T-bill (^IRX, annualized %) -> per-period decimal, ffilled."""
    d, p = fetch("^IRX", "1d", start_year)
    return d, np.maximum(p, 0.0) / 100.0


def month_end_series(sym, start_year):
    d, p = fetch(sym, "1mo", start_year)
    return d, p


def align(dates, series_list):
    """Inner-join several (dates, values) series on date."""
    common = set(dates[0])
    for d in dates[1:]:
        common &= set(d)
    common = sorted(common)
    out = []
    for (d, v) in zip(dates, series_list):
        idx = {x: i for i, x in enumerate(d)}
        out.append(np.array([v[idx[c]] for c in common], float))
    return np.array(common), out


# ---------------- metrics ----------------
def max_dd(eq):
    peak = np.maximum.accumulate(eq)
    return float(np.min(eq / peak - 1.0))


def norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def norm_ppf(p):
    # Acklam's inverse normal CDF
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    dd = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
          3.754408661907416e+00]
    pl, ph = 0.02425, 1 - 0.02425
    if p < pl:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((dd[0]*q+dd[1])*q+dd[2])*q+dd[3])*q+1)
    if p > ph:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((dd[0]*q+dd[1])*q+dd[2])*q+dd[3])*q+1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def stats(ret, rf, bench, ppy, n_trades, turnover):
    ret = np.asarray(ret, float); rf = np.asarray(rf, float)
    ex = ret - rf
    n = len(ret)
    if n < 12:
        return None
    eq = np.cumprod(1 + ret)
    years = n / ppy
    cagr = eq[-1] ** (1 / years) - 1
    vol = ret.std(ddof=1) * math.sqrt(ppy)
    sd_ex = ex.std(ddof=1)
    sharpe = (ex.mean() * ppy) / (sd_ex * math.sqrt(ppy)) if sd_ex > 0 else 0.0
    downside = ret[ret < 0]
    sortino = (ex.mean() * ppy) / (downside.std(ddof=1) * math.sqrt(ppy)) if len(downside) > 2 else 0.0
    mdd = max_dd(eq)
    d = ret - bench
    ir = (d.mean() * ppy) / (d.std(ddof=1) * math.sqrt(ppy)) if d.std(ddof=1) > 0 else 0.0
    tstat = d.mean() / (d.std(ddof=1) / math.sqrt(n)) if d.std(ddof=1) > 0 else 0.0
    m, s = ret.mean(), ret.std(ddof=1)
    skew = float(((ret - m) ** 3).mean() / s ** 3) if s > 0 else 0.0
    kurt = float(((ret - m) ** 4).mean() / s ** 4) if s > 0 else 3.0
    def f(x):
        v = float(x)
        return v if math.isfinite(v) else None
    sr_period = (ex.mean() / sd_ex) if sd_ex > 0 else 0.0
    return dict(n_periods=int(n), years=round(float(years), 2), cagr=f(cagr), vol=f(vol),
                sharpe=f(sharpe), sr_period=f(sr_period), sortino=f(sortino), max_dd=f(mdd),
                calmar=f(cagr / abs(mdd) if mdd < 0 else float("nan")),
                excess_ann=f(d.mean() * ppy), ir=f(ir), t_stat=f(tstat),
                bench_cagr=f((np.cumprod(1 + bench)[-1]) ** (1 / years) - 1),
                n_trades=int(n_trades), turnover=f(turnover),
                skew=f(skew), kurt=f(kurt), hit_rate=f((ret > 0).mean()))


def deflated_sharpe(sr, T, N, var_sr, skew, kurt):
    """Bailey & Lopez de Prado (2014). var_sr = cross-sectional variance of trial SRs."""
    if N <= 1 or var_sr <= 0:
        return float("nan"), float("nan")
    g = 0.5772156649
    e = math.e
    sr0 = math.sqrt(var_sr) * ((1 - g) * norm_ppf(1 - 1.0 / N) + g * norm_ppf(1 - 1.0 / (N * e)))
    denom = math.sqrt(max(1e-9, 1 - skew * sr + (kurt - 1) / 4.0 * sr ** 2))
    dsr = norm_cdf((sr - sr0) * math.sqrt(max(T - 1, 1)) / denom)
    return float(dsr), float(sr0)


# ---------------- strategies ----------------
class Res:
    def __init__(self, name, style, desc):
        self.name, self.style, self.desc = name, style, desc
        self.ret = self.rf = self.bench = None
        self.exposure = None
        self.trades = 0
        self.turnover = 0.0
        self.ppy = 12
        self.dates = None


def monthly_strategy(dates, price, weights_fn, rf_m, cost_bps, name, style, desc):
    """weights_fn(i) -> dict{sym: weight} using data up to and including period i.
    Uninvested weight earns the T-bill rate rf_m[i] (cash is not assumed to yield 0)."""
    r = Res(name, style, desc)
    rets, exps, n_tr = [], [], 0
    prev_w = {}
    for i in range(1, len(dates)):
        w = weights_fn(i - 1)
        exp = sum(w.values())
        gross = (1.0 - exp) * rf_m[i]
        for sym, wt in w.items():
            if wt:
                p0, p1 = price[sym][i - 1], price[sym][i]
                gross += wt * (p1 / p0 - 1.0)
        chg = sum(abs(w.get(k, 0) - prev_w.get(k, 0)) for k in set(w) | set(prev_w))
        cost = chg * cost_bps / 10000.0
        if chg > 0:
            n_tr += 1
        rets.append(gross - cost)
        exps.append(exp)
        prev_w = w
    r.ret = np.array(rets)
    r.exposure = np.array(exps)
    r.trades = n_tr
    r.turnover = float(np.mean(np.abs(np.diff(r.exposure))) * 12) if len(exps) > 2 else 0.0
    r.dates = dates[1:]
    r.ppy = 12
    return r


def daily_strategy(dates, rets, pos, rf, cost_bps, name, style, desc):
    r = Res(name, style, desc)
    # pos[t] is decided on close t and earns rets[t] (close t -> close t+1).
    pos_l = np.asarray(pos, float)[:-1]
    assert len(pos_l) == len(rets), (len(pos_l), len(rets))
    pnl = pos_l * rets
    chg = np.abs(np.diff(pos_l, prepend=0.0))
    net = pnl - chg * cost_bps / 10000.0
    r.ret = net
    r.exposure = pos_l
    r.trades = int((np.diff(pos_l, prepend=0.0) > 0).sum())   # round trips = entries
    r.turnover = float(chg.mean() * 252)
    r.dates = dates[1:]
    r.ppy = 252
    return r


def rsi(vals, period=2):
    d = np.diff(vals, prepend=vals[0])
    up = np.clip(d, 0, None); dn = np.clip(-d, 0, None)
    au = np.zeros_like(vals); ad = np.zeros_like(vals)
    for i in range(1, len(vals)):
        au[i] = (au[i-1] * (period - 1) + up[i]) / period
        ad[i] = (ad[i-1] * (period - 1) + dn[i]) / period
    rs = au / np.where(ad == 0, 1e-12, ad)
    return 100 - 100 / (1 + rs)


def sma(x, n):
    out = np.full_like(x, np.nan)
    c = np.cumsum(np.insert(x, 0, 0.0))
    out[n-1:] = (c[n:] - c[:-n]) / n
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cost-mult", type=float, default=1.0, help="stress: 2.0 doubles all costs")
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()

    print("fetching data ...")
    # monthly universe
    md = {}; mp = {}
    for s in ("SPY", "TLT", "GLD"):
        d, p = month_end_series(s, 2001 if s != "GLD" else 2004)
        md[s], mp[s] = d, p
    mdtes, (spy_m, tlt_m, gld_m) = align([md["SPY"], md["TLT"], md["GLD"]], [mp["SPY"], mp["TLT"], mp["GLD"]])
    # daily universe
    dd, dspy = fetch("SPY", "1d", 2001)
    bdates_all, btc_all = fetch("BTC-USD", "1d", 2014)
    cdates, crate = fetch_cash_rate(2001)
    print(f"  monthly {len(mdtes)} rows {mdtes[0]}..{mdtes[-1]}")
    print(f"  daily SPY {len(dd)}  BTC {len(bdates_all)}  cash {len(cdates)}")

    price = {"SPY": spy_m, "TLT": tlt_m, "GLD": gld_m}
    r_spy_m = spy_m[1:] / spy_m[:-1] - 1

    # monthly T-bill rate aligned to month-end dates (mean of daily ^IRX in that month)
    from collections import defaultdict
    bym = defaultdict(list)
    for d, v in zip(cdates, crate):
        bym[d[:7]].append(v)
    rf_m = np.array([float(np.mean(bym[d[:7]])) / 12.0 if bym.get(d[:7]) else 0.02 / 12
                     for d in mdtes])
    rf_m_ret = rf_m[1:]

    results = {}
    NAMES = [s[0] for s in STRATEGIES]
    meta = {s[0]: s for s in STRATEGIES}

    # --- monthly strategies ---
    def w_bh(i):   return {"SPY": 1.0}
    def w_6040(i): return {"SPY": 0.6, "TLT": 0.4}
    def w_faber(i):
        if i < 10: return {"SPY": 0.0}
        return {"SPY": 1.0 if spy_m[i] > spy_m[i-9:i+1].mean() else 0.0}
    def mom(v, i, look=12):
        if i < look: return -9.99
        return v[i] / v[i-look] - 1
    def w_dm2(i):
        ms, mt = mom(spy_m, i), mom(tlt_m, i)
        if max(ms, mt) <= 0 or ms < -9: return {"SPY": 0.0, "TLT": 0.0}
        return {"SPY": 1.0, "TLT": 0.0} if ms >= mt else {"SPY": 0.0, "TLT": 1.0}
    def w_dm3(i):
        cands = {"SPY": mom(spy_m, i), "TLT": mom(tlt_m, i), "GLD": mom(gld_m, i)}
        best = max(cands, key=cands.get)
        if cands[best] <= 0 or i < 12: return {k: 0.0 for k in cands}
        return {k: (1.0 if k == best else 0.0) for k in cands}

    for nm, fn in (("BH_SPY", w_bh), ("SIXTY_FORTY", w_6040), ("FABER10_SPY", w_faber),
                   ("DUALMOM_2", w_dm2), ("DUALMOM_3", w_dm3)):
        results[nm] = monthly_strategy(mdtes, price, fn, rf_m, COST_BPS["equity"] * a.cost_mult,
                                       nm, meta[nm][1], meta[nm][2])

    # --- daily strategies ---
    # SPY: align to cash dates
    idx = {d: i for i, d in enumerate(dd)}
    cidx = [idx[c] for c in cdates if c in idx]
    sdates = np.array([dd[i] for i in cidx])
    spx = np.array([dspy[i] for i in cidx])
    sret = spx[1:] / spx[:-1] - 1
    rf_d = np.array([crate[list(cdates).index(c)] / 252.0 for c in sdates])[1:]

    close = spx
    r2 = rsi(close)
    s200 = sma(close, 200); s5 = sma(close, 5)
    pos = np.zeros(len(close)); held = 0
    for t in range(1, len(close)):
        if pos[t-1] == 0:
            if not np.isnan(s200[t]) and r2[t] < 5 and close[t] > s200[t]:
                pos[t] = 1.0; held = 1
        else:
            held += 1
            if (not np.isnan(s5[t]) and close[t] > s5[t]) or r2[t] > 65 or held >= 10:
                pos[t] = 0.0
    results["RSI2_SPY"] = daily_strategy(sdates, sret, pos, rf_d,
                                         COST_BPS["equity"] * a.cost_mult,
                                         "RSI2_SPY", meta["RSI2_SPY"][1], meta["RSI2_SPY"][2])

    # BTC — keep BTC's own calendar (it trades weekends), match dates against SPY's
    bidx = {d: i for i, d in enumerate(dd)}
    bi = [(i, d) for i, d in enumerate(bdates_all) if d in bidx]
    if len(bi) < 500:
        raise RuntimeError(f"BTC/SPY date alignment failed: {len(bi)} common days")
    bdates = np.array([d for _, d in bi])
    btc = np.array([btc_all[i] for i, _ in bi])
    bret = btc[1:] / btc[:-1] - 1
    b200 = sma(btc, 200)
    bpos = np.where(btc > b200, 1.0, 0.0)
    bpos[:200] = 0.0
    rf_by_date_d = {d: v for d, v in zip(sdates[1:], rf_d)}
    rfb = np.array([rf_by_date_d.get(d, 0.0) for d in bdates[1:]])
    results["BTC_BH"] = daily_strategy(bdates, bret, np.ones(len(btc)), rfb,
                                       COST_BPS["btc"] * a.cost_mult, "BTC_BH",
                                       meta["BTC_BH"][1], meta["BTC_BH"][2])
    results["BTC_TREND200"] = daily_strategy(bdates, bret, bpos, rfb,
                                             COST_BPS["btc"] * a.cost_mult, "BTC_TREND200",
                                             meta["BTC_TREND200"][1], meta["BTC_TREND200"][2])

    # --- benchmarks at matched exposure + stats ---
    # Benchmark = same exposure in SPY, remainder in cash. Missing SPY days (BTC trades
    # weekends) contribute 0, i.e. the SPY price is forward-filled.
    spy_by_date = {d: v for d, v in zip(sdates[1:], sret)}
    rf_by_date = {d: v for d, v in zip(sdates[1:], rf_d)}
    for nm, r in results.items():
        n = len(r.ret) if r.ret is not None else 0
        if n < 12:
            print(f"  SKIP {nm}: only {n} return periods (dates {r.dates[0] if r.dates is not None and len(r.dates) else '?'}.."
                  f"{r.dates[-1] if r.dates is not None and len(r.dates) else '?'})")
            continue
        if r.ppy == 12:
            r.bench = r.exposure * r_spy_m[-n:] + (1 - r.exposure) * rf_m_ret[-n:]
            r.rf = rf_m_ret[-n:]
        else:
            spy_al = np.array([spy_by_date.get(d, 0.0) for d in r.dates])
            cash = np.array([rf_by_date.get(d, 0.0) for d in r.dates])
            assert len(spy_al) == n, (nm, len(spy_al), n)
            r.bench = r.exposure * spy_al + (1 - r.exposure) * cash
            r.rf = cash
        r.stats = stats(r.ret, r.rf, r.bench, r.ppy, r.trades, r.turnover)
        r.stats["exposure"] = float(np.mean(r.exposure))
        r.stats["start"] = str(r.dates[0]); r.stats["end"] = str(r.dates[-1])

    # --- deflated Sharpe across the 8 pre-registered trials ---
    live = {nm: r for nm, r in results.items() if getattr(r, "stats", None)}
    # DSR must use per-PERIOD Sharpe and a trial variance from the same frequency.
    # Mixing annualised monthly and daily Sharpes inflates the variance and is wrong.
    var_sr_by_freq = {}
    for freq, ppy in (("monthly", 12), ("daily", 252)):
        grp = [r for r in live.values() if r.ppy == ppy]
        n_pre = sum(1 for s in STRATEGIES if (s[1] == "monthly") == (freq == "monthly"))
        srs = [r.stats["sr_period"] for r in grp]
        vsr = float(np.var(srs, ddof=1)) if len(srs) > 1 else 0.0
        var_sr_by_freq[freq] = vsr
        for r in grp:
            dsr, sr0 = deflated_sharpe(r.stats["sr_period"], r.stats["n_periods"], n_pre,
                                       vsr, r.stats["skew"], r.stats["kurt"])
            r.stats["dsr"] = dsr; r.stats["sr0"] = sr0
            r.stats["dsr_family"] = f"{freq} (N={n_pre} trials)"
    var_sr = var_sr_by_freq

    # --- IS / OOS split ---
    def split_stats(r, lo, hi):
        mask = np.array([(lo <= d[:7] <= hi) for d in r.dates])
        if mask.sum() < 24: return None
        i0 = int(np.argmax(mask))
        sl = slice(i0, i0 + int(mask.sum()))
        return stats(r.ret[sl], r.rf[sl], r.bench[sl], r.ppy, 0, 0.0)

    for nm, r in live.items():
        if nm.startswith("BTC"):
            r.is_ = split_stats(r, "2014-10", "2020-12")
            r.oos = split_stats(r, "2021-01", "2026-11")
        else:
            r.is_ = split_stats(r, "2003-01", "2015-12")
            r.oos = split_stats(r, "2016-01", "2026-11")

    # --- verdicts ---
    def pass_gates(r):
        s = r.stats
        g = {
            "beats_matched_benchmark": bool(s["excess_ann"] > 0),
            "ir_positive": bool(s["ir"] > 0),
            "dsr_ge_95": bool(s["dsr"] is not None and s["dsr"] >= 0.95),
            "oos_positive": bool(r.oos and r.oos["excess_ann"] is not None and r.oos["excess_ann"] > 0),
            "is_positive": bool(r.is_ and r.is_["excess_ann"] is not None and r.is_["excess_ann"] > 0),
        }
        return g, sum(g.values())

    payload = {"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "trial_count_N": len(STRATEGIES), "cost_mult": a.cost_mult,
               "cost_bps_per_side": COST_BPS, "var_sr_used": var_sr,
               "note": "Benchmark for each row is that row's OWN exposure in SPY plus cash. "
                       "excess_ann is annualized return minus that benchmark.",
               "strategies": {}}
    print(f"\n{'strategy':<14}{'CAGR':>8}{'excess':>8}{'IR':>7}{'Sharpe':>8}{'MaxDD':>8}{'DSR':>7}{'exp':>6}{'trades':>7}  gates")
    for nm, r in live.items():
        s = r.stats; g, np_ = pass_gates(r)
        print(f"{nm:<14}{s['cagr']*100:>7.2f}%{s['excess_ann']*100:>7.2f}%{s['ir']:>7.2f}"
              f"{s['sharpe']:>8.2f}{s['max_dd']*100:>7.1f}%{s['dsr']:>7.2f}{s['exposure']:>6.2f}"
              f"{s['n_trades']:>7}  {np_}/5")
        payload["strategies"][nm] = {"style": r.style, "rule": r.desc, "full": s,
                                     "is": r.is_, "oos": r.oos, "gates": g, "gates_passed": np_}
    with open(a.out, "w") as f:
        json.dump(payload, f, indent=1)
    print(f"\nwrote {a.out}  (N={len(STRATEGIES)} trials, cost_mult={a.cost_mult})")
    return payload


if __name__ == "__main__":
    main()
