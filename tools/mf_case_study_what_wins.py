#!/usr/bin/env python3
"""Case study: what makes a 'consistently winning' mutual fund?

Buffy 2026-10-23. NOT FINANCIAL ADVICE — research only.

Part A — Pattern hunt: at each calendar year-end T (2005..2023), compute
  trailing features (ONLY data <= T) for every fund with >=36 months of
  history, then correlate them with FORWARD outcomes (next 12m, next 36m,
  net of the fund's expense ratio). Features: cost, trailing return,
  Sharpe, volatility, max drawdown, consistency (% of trailing 12m windows
  positive), beta/downside-capture/alpha vs SPY.

Part B — Point-in-time simulation: at each year-end, rank the universe with
  rules that use only trailing data, filter to what an account of
  $200 / $500 / $1,000 / $2,000 / $10,000 could actually BUY (fund minimums
  or 1 ETF share price + one RBC-style commission), buy equal-weight the
  top 3, hold 12 months, repeat. Compare vs SPY buy&hold and vs 2%/yr cash.

Honest limits (documented in output):
  * Expense ratios are TODAY's values (cache has no historical ER table).
  * Universe = funds that still exist today (survivorship bias upward).
  * Minimums are approximate historical values (encoded table, documented).
  * Manager tenure & style factors are NOT in the cache — not simulated.
  * CA ETFs priced in CAD converted at fixed 1.30 CAD/USD (approx).

Reproduce: python3 tools/mf_case_study_what_wins.py
Output: reports/mf_case_study_2026-10-23.json
"""
import csv
import json
import math
import os
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(REPO, "audit_dashboard", "data", "mf_backtest_cache")
OUT = os.path.join(REPO, "reports", "mf_case_study_2026-10-23.json")

CADUSD = 1.30  # fixed approx conversion for CA-listed prices
CASH_RATE = 0.02  # approx T-bill average, applied per year (documented)

# ---------------------------------------------------------------- load data
meta = json.load(open(os.path.join(CACHE, "mf_backtest_universe.json")))["funds"]


def load(ticker):
    path = os.path.join(CACHE, ticker.replace("/", "_") + ".csv")
    if not os.path.exists(path):
        return None
    series = {}
    with open(path) as fh:
        for row in csv.DictReader(fh):
            try:
                series[row["Date"][:7]] = float(row["close"])
            except (KeyError, ValueError):
                continue
    return series


def month_ends(series):
    """last known close per month -> ordered (month, close)"""
    return sorted(series.items())


raw = {}
for tk in meta:
    s = load(tk)
    if s and len(s) >= 40:
        raw[tk] = s

spy_s = load("SPY")
spy_me = month_ends(spy_s)
spy_ret = {}
for i in range(1, len(spy_me)):
    (m0, c0), (m1, c1) = spy_me[i - 1], spy_me[i]
    spy_ret[m1] = c1 / c0 - 1.0

MONTHS = sorted(spy_ret)
# decision points: last month of each year
YEARS = list(range(2005, 2024))
DECS = [f"{y}-12" for y in YEARS]

# ------------------------------------------------- approximate minimums (USD)
FID_PRE22 = 2500.0     # Fidelity investor-class funds: $2,500 until Mar 2022
VAN_ADM = 3000.0       # Vanguard Admiral
VAN_INV = 3000.0       # Vanguard Investor
SCHWAB = 100.0         # Schwab index funds: $100 until ~2021
OTHER_US_MF = 1000.0   # Dodge & Cox etc.

ETF_TICKERS_CA = {"XEQT.TO", "VEQT.TO", "ZEQT.TO", "VGRO.TO", "VBAL.TO",
                  "XBAL.TO", "ZBAL.TO", "VFV.TO", "XIC.TO", "VUN.TO",
                  "XAW.TO", "ZAG.TO"}
FREE_LIST_CA = {"XEQT.TO", "XBAL.TO", "VGRO.TO"}  # iShares core on RBC free list (current)


def min_inv(tk, year):
    if tk in ETF_TICKERS_CA:
        return None  # ETF: 1 share price, handled separately
    if tk.startswith("FS") or tk.startswith("FL") or tk in ("FOCPX", "FCNTX", "FDGRX", "FSCSX", "FRESX", "FSKAX", "FSPGX", "FSMDX", "FSSNX", "FSRNX"):
        return 0.0 if year >= 2022 else FID_PRE22
    if tk.startswith("SW"):
        return 0.0 if year >= 2021 else SCHWAB
    if tk.startswith("V") and tk not in ETF_TICKERS_CA:
        return VAN_ADM if tk[-1] == "X" else VAN_INV
    if tk.startswith("D"):
        return OTHER_US_MF
    return OTHER_US_MF


def trade_fee(tk, year):
    """USD commission to open the position"""
    if tk in FREE_LIST_CA:
        return 0.0
    if tk in ETF_TICKERS_CA:
        return 9.95 / CADUSD  # RBC ETF trade, converted
    if year >= 2019:
        return 0.0  # US brokers went commission-free 2019
    return 7.95


def er(tk):
    return float(meta[tk].get("expense_ratio") or 0.0)


def is_index(tk):
    return bool(meta[tk].get("is_index"))

# ------------------------------------------------------- trailing features


def trailing_features(tk, dec_month):
    s = raw[tk]
    # 36 months ending at dec_month
    idx = [i for i, (m, _) in enumerate(month_ends(s)) if m <= dec_month]
    if len(idx) < 37:
        return None
    me = month_ends(s)
    closes = [me[i][1] for i in idx[-37:]]
    months = [me[i][0] for i in idx[-36:]]
    rets = [closes[i + 1] / closes[i] - 1.0 for i in range(36)]
    tot = closes[-1] / closes[0]
    cagr = tot ** (12 / 36) - 1.0
    mean = sum(rets) / 36
    var = sum((r - mean) ** 2 for r in rets) / 35
    vol = math.sqrt(var * 12)
    sharpe = (mean * 12) / vol if vol > 0 else 0.0
    # max drawdown on monthly closes
    peak = closes[0]
    mdd = 0.0
    for c in closes:
        peak = max(peak, c)
        mdd = min(mdd, c / peak - 1.0)
    # consistency: fraction of positive trailing 12m windows inside the 36m
    pos = 0
    nwin = 0
    for i in range(0, 25):
        r = closes[i + 12] / closes[i] - 1.0
        nwin += 1
        if r > 0:
            pos += 1
    cons = pos / nwin if nwin else 0.0
    # beta / downside capture / alpha vs SPY (common months only)
    common = [(r, spy_ret[m]) for r, m in zip(rets, months) if m in spy_ret]
    if len(common) >= 24:
        fs = [a for a, _ in common]
        ss = [b for _, b in common]
        mf, ms = sum(fs) / len(fs), sum(ss) / len(ss)
        cov = sum((a - mf) * (b - ms) for a, b in zip(fs, ss)) / (len(fs) - 1)
        var_s = sum((b - ms) ** 2 for b in ss) / (len(ss) - 1)
        beta = cov / var_s if var_s > 0 else 1.0
        alpha_m = mf - beta * ms
        dn_f = [a for a, b in common if b < 0]
        dn_s = [b for a, b in common if b < 0]
        dcap = (sum(dn_f) / len(dn_f)) / (sum(dn_s) / len(dn_s)) if dn_s and sum(dn_s) != 0 else 1.0
    else:
        beta, alpha_m, dcap = 1.0, 0.0, 1.0
    return {"cagr": cagr, "sharpe": sharpe, "vol": vol, "mdd": mdd,
            "consistency": cons, "beta": beta, "downside_capture": dcap,
            "alpha_ann": alpha_m * 12}


def forward_outcome(tk, dec_month, horizon=12):
    s = month_ends(raw[tk])
    after = [i for i, (m, _) in enumerate(s) if m > dec_month]
    before = [i for i, (m, _) in enumerate(s) if m <= dec_month]
    if not after or not before:
        return None
    t0 = s[before[-1]][1]
    need = [i for i in after if True]
    # target month = dec_month + horizon
    y, mo = int(dec_month[:4]), int(dec_month[5:7])
    total = y * 12 + (mo - 1) + horizon
    ty, tm = divmod(total - 1, 12)
    tgt = f"{ty:04d}-{tm + 1:02d}"
    cand = [(i, m) for i, (m, c) in enumerate(s) if m <= tgt]
    if not cand:
        return None
    t1 = s[cand[-1][0]][1]
    months_h = (cand[-1][0] - before[-1])
    if months_h < horizon - 2:
        return None
    net = (t1 / t0 - 1.0) - er(tk) * (months_h / 12.0)
    return {"net_return": net, "months": months_h}


def spy_forward(dec_month, horizon=12):
    y, mo = int(dec_month[:4]), int(dec_month[5:7])
    total = y * 12 + (mo - 1) + horizon
    ty, tm = divmod(total - 1, 12)
    tgt = f"{ty:04d}-{tm + 1:02d}"
    c0 = [c for m, c in spy_me if m == dec_month]
    c1 = [c for m, c in spy_me if m == tgt]
    if not c0 or not c1:
        # fallback: nearest available
        before = [(m, c) for m, c in spy_me if m <= dec_month]
        after = [(m, c) for m, c in spy_me if m <= tgt]
        if not before or not after:
            return None
        c0, c1 = [before[-1][1]], [after[-1][1]]
    return c1[0] / c0[0] - 1.0

# ------------------------------------------------------ Part A: patterns
print("=" * 78)
print("PART A — trailing features vs forward net return (2005-2023, 12m horizon)")
print("=" * 78)


def spearman(xs, ys):
    n = len(xs)
    if n < 10:
        return None

    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        for pos, i in enumerate(order):
            r[i] = pos + 1
        return r
    rx, ry = rank(xs), rank(ys)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den_x = math.sqrt(sum((a - mx) ** 2 for a in rx))
    den_y = math.sqrt(sum((b - my) ** 2 for b in ry))
    return num / (den_x * den_y) if den_x and den_y else None


rows = []
for tk in sorted(raw):
    for dec in DECS:
        ft = trailing_features(tk, dec)
        fo = forward_outcome(tk, dec, 12)
        if ft and fo:
            rows.append({**ft, "net12": fo["net_return"], "ticker": tk, "dec": dec,
                         "er": er(tk), "index": is_index(tk)})

if rows:
    for feat in ("er", "cagr", "sharpe", "vol", "mdd", "consistency", "beta", "downside_capture", "alpha_ann"):
        rho = spearman([r[feat] for r in rows], [r["net12"] for r in rows])
        print(f"  rho(forward 12m net, {feat:>16}) = {rho:+.3f}   n={len(rows)} fund-years")
    # consistency vs forward *steadiness* (forward |monthly| path not stored here;
    # use forward 12m net sign as steadiness proxy)
    rho = spearman([r["consistency"] for r in rows], [1.0 if r["net12"] > 0 else 0.0 for r in rows])
    print(f"  rho(forward POSITIVE year, consistency) = {rho:+.3f}")
    idx_rows = [r for r in rows if r["index"]]
    act_rows = [r for r in rows if not r["index"]]
    for label, sub in (("index", idx_rows), ("active", act_rows)):
        if len(sub) > 20:
            m = sum(r["net12"] for r in sub) / len(sub)
            print(f"  {label:6} fund-years: mean net 12m {m * 100:+.2f}%  n={len(sub)}")

# ------------------------------------------- Part B: point-in-time simulation
print()
print("=" * 78)
print("PART B — point-in-time simulation by capital tier (top-3, 1y hold, net)")
print("=" * 78)

TIERS = [200.0, 500.0, 1000.0, 2000.0, 10000.0]


def afford(tk, year, capital, dec_month):
    s = raw[tk]
    before = [c for m, c in month_ends(s) if m <= dec_month]
    if not before:
        return False, 0.0
    price = before[-1]
    if tk in ETF_TICKERS_CA:
        price_usd = price / CADUSD
        fee = trade_fee(tk, year)
        ok = price_usd + fee <= capital
        return ok, fee
    mi = min_inv(tk, year)
    fee = trade_fee(tk, year)
    return (mi is not None and mi + fee <= capital), fee


def composite_score(universe, dec):
    """renormalized 4-component score: cost / risk / consistency / downside"""
    feats = {tk: trailing_features(tk, dec) for tk in universe}
    feats = {k: v for k, v in feats.items() if v}
    if len(feats) < 3:
        return []
    def prank(vals, invert=False):
        order = sorted(range(len(vals)), key=lambda i: vals[i])
        r = [0.0] * len(vals)
        for pos, i in enumerate(order):
            r[i] = pos / (len(vals) - 1)
        if invert:
            r = [1 - x for x in r]
        return r
    keys = list(feats)
    cost = prank([er(k) if er(k) > 0 else 0.00001 for k in keys], invert=True)
    risk = prank([feats[k]["sharpe"] for k in keys])
    cons = prank([feats[k]["consistency"] for k in keys])
    down = prank([feats[k]["downside_capture"] for k in keys], invert=True)
    scores = []
    for i, k in enumerate(keys):
        s = 0.22 * cost[i] + 0.26 * risk[i] + 0.18 * cons[i] + 0.16 * down[i]
        scores.append((s / 0.82, k))  # renormalized: capacity/manager not in cache
    return [k for _, k in sorted(scores, reverse=True)]


def run_rule(rule_name, tiers=TIERS):
    results = {}
    for cap in tiers:
        path = []  # (year, [tickers], portfolio net 12m return, spy return)
        for year in YEARS:
            dec = f"{year}-12"
            if year == YEARS[-1]:
                continue  # need forward year
            universe = []
            for tk in sorted(raw):
                if trailing_features(tk, dec) is None:
                    continue
                ok, _ = afford(tk, year, cap, dec)
                if ok:
                    universe.append(tk)
            if rule_name == "cheapest3":
                picks = sorted(universe, key=lambda t: (er(t) if er(t) > 0 else 1e-6, t))[:3]
            elif rule_name == "composite":
                picks = composite_score(universe, dec)[:3]
            elif rule_name == "steady":
                ft = [(trailing_features(t, dec)["consistency"], t) for t in universe]
                picks = [t for _, t in sorted(ft, reverse=True)[:3]]
            else:
                picks = []
            if not picks:
                path.append((year, [], None, spy_forward(dec)))
                continue
            outs = [forward_outcome(t, dec, 12) for t in picks]
            outs = [o["net_return"] for o in outs if o]
            ret = sum(outs) / len(outs) if outs else None
            path.append((year, picks, ret, spy_forward(dec)))
        # portfolio growth of cap over all years (skip missing years at cash)
        v = cap
        for year, picks, ret, spy_r in path:
            r = ret if ret is not None else CASH_RATE
            v *= (1 + r)
        wins = [1 for y, p, r, s in path if r is not None and s is not None and r > s]
        playable = [1 for y, p, r, s in path if r is not None]
        results[cap] = {
            "final_value": round(v, 2),
            "growth_multiple": round(v / cap, 3),
            "years_beat_spy": sum(wins),
            "years_playable": len(playable),
            "path": [{"year": y, "picks": p,
                      "net12": None if r is None else round(r, 4),
                      "spy12": None if s is None else round(s, 4)} for y, p, r, s in path],
        }
    return results


report = {"generated_at": "2026-10-23", "agent": "Buffy",
          "n_funds": len(raw), "decision_years": [YEARS[0], YEARS[-1]],
          "cash_rate_assumed": CASH_RATE, "cadusd": CADUSD,
          "limitations": [
              "expense ratios are current values, not historical",
              "survivorship bias: only surviving funds in cache",
              "fund minimums approximate (encoded table)",
              "manager tenure / style factors not in cache",
          ],
          "part_a_rows": len(rows), "part_b": {}}

for rule in ("cheapest3", "composite", "steady"):
    print(f"\n--- rule: {rule} ---")
    res = run_rule(rule)
    report["part_b"][rule] = res
    for cap in TIERS:
        r = res[cap]
        print(f"  ${cap:>8,.0f}: final ${r['final_value']:>10,.2f}  x{r['growth_multiple']:<6}  beat SPY {r['years_beat_spy']}/{r['years_playable']} yrs")
    # print one example year path for the $1,000 tier
    ex = res[1000.0]["path"][:4]
    for p in ex:
        print(f"     e.g. {p['year']}: picks={','.join(p['picks']) or '-'} net12={p['net12']} spy12={p['spy12']}")

print("\n--- benchmark: SPY buy&hold per year compounding (same method) ---")
v = 1.0
for year in YEARS[:-1]:
    s = spy_forward(f"{year}-12")
    if s is not None:
        v *= (1 + s)
print(f"  $1,000 -> ${1000 * v:,.2f}  x{v:.3f}")

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w") as fh:
    json.dump(report, fh, indent=1)
print(f"\nwrote {OUT}")
