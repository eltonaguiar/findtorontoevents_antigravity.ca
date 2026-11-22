#!/usr/bin/env python3
"""Execute the two pre-registered OUTSIDE kill tests.

Registration: reports/outside_preregistrations_2026-11-22.json, committed at
da5fd1fa371 BEFORE this file was written or run. Nothing here may alter the
thresholds; if a threshold is wrong the fix is to register a NEW test, not to
edit this one.

OUTSIDE-1  ETF breakout, top realised-vol tercile, 24 bp round trip
           KILL if top-tercile net < 0 bp OR top-tercile gross < 24 bp

OUTSIDE-2  Crypto lead (H-119), rolling-60d OOS DSR vs a 67-cell search
           KILL if DSR p >= 0.5 after 200 forward prints
                   OR any 50-trade window realises < 10 bp net
           The 200-forward-print condition is NOT YET EVALUABLE (forward count 0).

Both are written to KILL. Prior: nothing in this programme has survived a
correctly specified kill test yet.

Usage: python3 tools/prereg_outside_tests.py
"""
from __future__ import annotations

import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PREREG = ROOT / "reports" / "outside_preregistrations_2026-11-22.json"
OUT = ROOT / "reports" / "prereg_outside" / "prereg_outside_tests.json"
LEDGER = ROOT / "reports" / "forward_observations.jsonl"

# ---- OUTSIDE-1 constants, copied verbatim from the registration ----
MARKETS = ["^GSPC", "^FTSE", "^GDAXI", "^N225", "^GSPTSE", "^AXJO", "^HSI",
           "SPY", "QQQ", "GLD", "TLT", "IEF", "EEM", "EFA"]
LOOK, TP_ATR, SL_ATR, MAX_HOLD = 20, 2.0, 1.0, 10
VOL_WINDOW = 20
COST_RT_BP = 24.0
KILL_NET_BP, KILL_GROSS_BP = 0.0, 24.0

# ---- OUTSIDE-2 constants ----
N_TRIALS_SEARCH = 67
COST_RT_CRYPTO_BP = 16.0
ROLL_WINDOW_DAYS = 60
N_FORWARD_REQUIRED = 200
DSR_P_MAX = 0.5
MIN_WINDOW_NET_BP = 10.0
WINDOW_TRADES = 50


# --------------------------------------------------------------------------- #
def norm_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def norm_ppf(p: float) -> float:
    lo, hi = -8.0, 8.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if norm_cdf(mid) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def deflated_sharpe_p(sharpe_per_obs: float, n_obs: int, n_trials: int,
                      skew: float, kurt: float) -> float:
    """DSR: probability the true SR exceeds the best-of-N null. Lower = better."""
    if n_obs < 20 or n_trials < 2:
        return float("nan")
    euler = 0.5772156649
    e_max = ((1 - euler) * norm_ppf(1 - 1 / n_trials)
             + euler * norm_ppf(1 - 1 / (n_trials * math.e)))
    sr0 = math.sqrt(1.0 / n_obs) * e_max
    denom = 1 - skew * sharpe_per_obs + ((kurt - 1) / 4) * sharpe_per_obs ** 2
    if denom <= 0:
        return float("nan")
    z = (sharpe_per_obs - sr0) * math.sqrt(n_obs - 1) / math.sqrt(denom)
    # p-value convention: P(SR <= sr0) so a LARGE z gives a SMALL p
    return 1.0 - norm_cdf(z)


# --------------------------------------------------------------------------- #
def atr(bars: list[dict], i: int, n: int = 14) -> float:
    trs = []
    for j in range(max(1, i - n + 1), i + 1):
        h, l, pc = bars[j]["h"], bars[j]["l"], bars[j - 1]["c"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return sum(trs) / len(trs) if trs else 0.0


def realised_vol(bars: list[dict], i: int, n: int = VOL_WINDOW) -> float:
    """Std of daily returns over the n bars ENDING AT the signal bar i (known)."""
    rs = []
    for j in range(max(1, i - n + 1), i + 1):
        a, b = bars[j]["c"], bars[j - 1]["c"]
        if b > 0:
            rs.append(a / b - 1.0)
    return statistics.pstdev(rs) if len(rs) > 1 else float("nan")


def breakout_trades(bars: list[dict]) -> list[dict]:
    """The frozen rule from the registration. One position at a time."""
    out, i, n = [], LOOK + 1, len(bars)
    while i < n - 1:
        prior = bars[i - LOOK:i]
        if len(prior) < LOOK:
            break
        hi = max(b["h"] for b in prior)
        if bars[i]["c"] <= hi:
            i += 1
            continue
        a = atr(bars, i)
        if a <= 0:
            i += 1
            continue
        entry = bars[i + 1]["o"]              # next bar open, per spec
        vol = realised_vol(bars, i)           # through t-1/t, known before fill
        tp, sl = entry + TP_ATR * a, entry - SL_ATR * a
        exitp, reason, held = None, None, 0
        for j in range(i + 1, min(i + 1 + MAX_HOLD, n)):
            held = j - i
            if bars[j]["l"] <= sl:            # pessimistic: stop wins ties
                exitp, reason = sl, "SL"
                break
            if bars[j]["h"] >= tp:
                exitp, reason = tp, "TP"
                break
        if exitp is None:
            j = min(i + MAX_HOLD, n - 1)
            exitp, reason = bars[j]["c"], "TIMEOUT"
        out.append({"gross_bp": (exitp - entry) / entry * 1e4,
                    "vol": vol, "reason": reason, "held": held})
        i = j + 1                             # one position at a time
    return out


def fetch(ticker: str) -> list[dict]:
    import yfinance as yf
    df = yf.download(ticker, period="max", interval="1d", progress=False,
                     auto_adjust=False, threads=False)
    if df is None or len(df) < 200:
        return []
    if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
        df.columns = df.columns.get_level_values(0)
    bars = []
    for _, row in df.iterrows():
        try:
            o, h, l, c = (float(row["Open"]), float(row["High"]),
                          float(row["Low"]), float(row["Close"]))
        except (TypeError, ValueError, KeyError):
            continue
        if any(x != x for x in (o, h, l, c)) or c <= 0:
            continue
        bars.append({"o": o, "h": h, "l": l, "c": c})
    return bars


# --------------------------------------------------------------------------- #
def test_outside_1() -> dict:
    print("=" * 78)
    print("OUTSIDE-1 — ETF BREAKOUT, REALISED-VOL TERCILES, 24 bp ROUND TRIP")
    print("=" * 78)
    print(f"  KILL if top-tercile NET < {KILL_NET_BP} bp OR top-tercile GROSS "
          f"< {KILL_GROSS_BP} bp\n")

    rows, per_market = [], {}
    for m in MARKETS:
        try:
            bars = fetch(m)
        except Exception as exc:  # noqa: BLE001
            print(f"  {m:<8} FETCH FAILED {type(exc).__name__}")
            continue
        if not bars:
            print(f"  {m:<8} no data")
            continue
        tr = [t for t in breakout_trades(bars) if t["vol"] == t["vol"]]
        if len(tr) < 30:
            print(f"  {m:<8} only {len(tr)} trades, skipped")
            continue
        per_market[m] = tr
        vols = sorted(t["vol"] for t in tr)
        t1, t2 = vols[len(vols) // 3], vols[2 * len(vols) // 3]
        for t in tr:
            t["bucket"] = (0 if t["vol"] <= t1 else
                           (1 if t["vol"] <= t2 else 2))
        rows.extend(tr)
        print(f"  {m:<8} n={len(tr):>5}  vol cutoffs "
              f"{t1*100:.2f}% / {t2*100:.2f}%")

    if not rows:
        print("\n  No trades. Not a zero result — a data failure.")
        return {"test": "OUTSIDE-1", "status": "DATA_FAILURE"}

    print(f"\n  {'tercile':<10} {'n':>6} {'gross bp':>10} {'net@24bp':>10} "
          f"{'win%':>7} {'t':>7}")
    buckets = {}
    for b, label in ((0, "LOW vol"), (1, "MID vol"), (2, "TOP vol")):
        g = [t["gross_bp"] for t in rows if t["bucket"] == b]
        if not g:
            continue
        net = [x - COST_RT_BP for x in g]
        sd = statistics.pstdev(net)
        tstat = statistics.mean(net) / (sd / math.sqrt(len(net))) if sd else 0.0
        buckets[label] = {"n": len(g), "gross_bp": statistics.mean(g),
                          "net_bp": statistics.mean(net),
                          "win_pct": sum(1 for x in g if x > 0) / len(g) * 100,
                          "t": tstat}
        print(f"  {label:<10} {len(g):>6} {statistics.mean(g):>10.2f} "
              f"{statistics.mean(net):>10.2f} "
              f"{sum(1 for x in g if x > 0)/len(g)*100:>7.1f} {tstat:>7.2f}")

    top = buckets.get("TOP vol")
    if not top:
        return {"test": "OUTSIDE-1", "status": "NO_TOP_TERCILE"}
    cond_net = top["net_bp"] < KILL_NET_BP
    cond_gross = top["gross_bp"] < KILL_GROSS_BP
    killed = cond_net or cond_gross
    print(f"\n  KILL CONDITION (i) top-tercile net {top['net_bp']:+.2f} bp "
          f"< {KILL_NET_BP}: {'FIRED' if cond_net else 'not fired'}")
    print(f"  KILL CONDITION (ii) top-tercile gross {top['gross_bp']:+.2f} bp "
          f"< {KILL_GROSS_BP}: {'FIRED' if cond_gross else 'not fired'}")
    verdict = "KILLED" if killed else "SURVIVED"
    print(f"\n  ==> OUTSIDE-1 VERDICT: {verdict}")
    if killed:
        print(f"  The breakout family does not clear 24 bp even in the regime it")
        print(f"  should be strongest in. This is the most favourable framing")
        print(f"  available and it still dies, so the family is closed on ETFs.")
    else:
        print(f"  This SURVIVES the kill test — the first thing in this programme")
        print(f"  to do so. Treat as a shadow candidate pending forward prints,")
        print(f"  NOT as a promotion: terciles are in-sample.")
    return {"test": "OUTSIDE-1", "status": verdict, "buckets": buckets,
            "kill_net_fired": cond_net, "kill_gross_fired": cond_gross,
            "n_trades": len(rows), "n_markets": len(per_market)}


# --------------------------------------------------------------------------- #
def test_outside_2() -> dict:
    print("\n" + "=" * 78)
    print("OUTSIDE-2 — CRYPTO LEAD (H-119), ROLLING-60d OOS DSR vs 67-CELL SEARCH")
    print("=" * 78)
    print(f"  KILL if DSR p >= {DSR_P_MAX} after {N_FORWARD_REQUIRED} genuine "
          f"forward prints,")
    print(f"       OR any {WINDOW_TRADES}-trade window realises "
          f"< {MIN_WINDOW_NET_BP} bp net.\n")

    if not LEDGER.exists():
        print("  ledger missing; cannot evaluate")
        return {"test": "OUTSIDE-2", "status": "NO_LEDGER"}
    rows = []
    for ln in LEDGER.read_text().splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            r = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if r.get("hypothesis_id") == "H-119":
            rows.append(r)
    if not rows:
        print("  no H-119 rows")
        return {"test": "OUTSIDE-2", "status": "NO_ROWS"}

    # PROVENANCE: a forward observation must precede its own close.
    def ts(s):
        return datetime.fromisoformat(s)

    fwd, back = [], []
    for r in rows:
        try:
            (fwd if ts(r["created_at"]) < ts(r["closed_at"]) else back).append(r)
        except (KeyError, ValueError):
            back.append(r)
    print(f"  H-119 rows: {len(rows)}  genuine forward: {len(fwd)}  "
          f"backfilled: {len(back)}")

    def net_bp(r):
        e = float(r["entry_px"])
        x = float(r.get("resolver_exit_px") or r["exit_px"])
        g = x / e - 1.0
        if r["side"] != "LONG":
            g = -g
        return g * 1e4 - COST_RT_CRYPTO_BP

    # ---- component (i): DSR after 200 forward prints ----
    if len(fwd) < N_FORWARD_REQUIRED:
        print(f"\n  (i) DSR gating: NOT YET EVALUABLE — {len(fwd)} of "
              f"{N_FORWARD_REQUIRED} genuine forward prints.")
        print(f"      Registered so it cannot be retro-fitted after the fact.")
        dsr_state = "NOT_YET_EVALUABLE"
        dsr_p = None
    else:
        nets = [net_bp(r) for r in fwd]
        sd = statistics.pstdev(nets)
        sharpe = statistics.mean(nets) / sd if sd else 0.0
        m = statistics.mean(nets)
        sk = statistics.mean([(x - m) ** 3 for x in nets]) / sd ** 3 if sd else 0
        ku = statistics.mean([(x - m) ** 4 for x in nets]) / sd ** 4 if sd else 3
        dsr_p = deflated_sharpe_p(sharpe, len(nets), N_TRIALS_SEARCH, sk, ku)
        dsr_state = "KILLED" if dsr_p >= DSR_P_MAX else "not_fired"
        print(f"\n  (i) DSR on {len(nets)} forward prints: p={dsr_p:.4f} "
              f"-> {dsr_state}")

    # ---- component (ii): worst 50-trade window, HISTORICAL DIAGNOSTIC ----
    nets_all = sorted(((r["closed_at"], net_bp(r)) for r in rows))
    series = [v for _d, v in nets_all]
    worst = None
    if len(series) >= WINDOW_TRADES:
        for i in range(len(series) - WINDOW_TRADES + 1):
            w = statistics.mean(series[i:i + WINDOW_TRADES])
            worst = w if worst is None else min(worst, w)
    cond2 = worst is not None and worst < MIN_WINDOW_NET_BP
    print(f"\n  (ii) worst {WINDOW_TRADES}-trade rolling window: "
          f"{worst:+.2f} bp net" if worst is not None
          else "\n  (ii) fewer than 50 trades; not evaluable")
    print(f"       < {MIN_WINDOW_NET_BP} bp threshold: "
          f"{'FIRED' if cond2 else 'not fired'}")
    print(f"       LABEL: HISTORICAL DIAGNOSTIC on BACKFILLED rows. This is NOT")
    print(f"       forward evidence and must not be presented as such. It is")
    print(f"       reported because component (ii) is computable today.")

    killed = cond2 or (dsr_state == "KILLED")
    print(f"\n  ==> OUTSIDE-2 VERDICT: "
          f"{'KILLED' if killed else 'NOT YET DECIDABLE'}")
    print(f"  (i) is the primary condition and cannot fire before 200 forward")
    print(f"  prints exist. Do not act on this hypothesis in either direction")
    print(f"  until then.")
    return {"test": "OUTSIDE-2", "status": "KILLED" if killed else
            "NOT_YET_DECIDABLE",
            "n_rows": len(rows), "n_forward": len(fwd), "n_backfilled": len(back),
            "dsr_state": dsr_state, "dsr_p": dsr_p,
            "worst_50_trade_net_bp": worst, "window_kill_fired": cond2}


# --------------------------------------------------------------------------- #
def main() -> int:
    reg = json.loads(PREREG.read_text())
    print(f"Pre-registration: {reg['registered_utc']} ({reg['registered_by']})")
    print(f"  {len(reg['tests'])} tests\n")
    r1 = test_outside_1()
    r2 = test_outside_2()
    print("\n" + "=" * 78)
    print("SUMMARY")
    print("=" * 78)
    print(f"  OUTSIDE-1 : {r1['status']}")
    print(f"  OUTSIDE-2 : {r2['status']}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "computed_utc": datetime.now(timezone.utc).isoformat(),
        "prereg_commit": "da5fd1fa371",
        "results": [r1, r2],
        "evidence_class": "PRE-REGISTERED KILL TESTS",
        "note": "Thresholds are locked by the registration and were not tuned.",
    }, indent=2))
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
