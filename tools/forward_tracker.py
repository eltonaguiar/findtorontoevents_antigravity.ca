#!/usr/bin/env python3
"""
forward_tracker.py — the "can I kill this yet?" ledger.

Append one line per CLOSED trade. One command tells you, per strategy, whether to
KILL it, keep TESTING, or PROMOTE it. Rules are pre-registered below and must not be
changed after seeing results (that would be a trial).

Verdicts
--------
  KILL          evidence is already sufficient that the edge is not there
  BROKEN        no trades at all after the window -> the strategy is not firing (different bug)
  CONTINUE      not enough evidence yet; keep trading
  PROMOTE       passed on forward data; still needs capital-committee sign-off
  HOLD-LONGER   too few trades because holds are long: extend the clock, do not kill

Pre-registered rules
--------------------
FAST (hold < 5d, high frequency): decide on trade count.
  n >= 20 and PF < 1.00                  -> KILL
  n >= 20 and Wilson_lower(WR) < 0.40    -> KILL
  n >= 30 and PF >= 1.15 and boot5(PF) > 1.05 -> PROMOTE
SLOW (hold >= 5d):
  180d elapsed, n >= 8,  PF < 1.00       -> KILL
  365d elapsed, n >= 20, PF < 1.05       -> KILL
  365d elapsed, n >= 20, PF >= 1.15 and boot5(PF) > 1.00 -> PROMOTE
  365d elapsed, n < 20                   -> HOLD-LONGER (clock extended once to 730d)
BROKEN: 60d elapsed and n == 0.

Why hold_type matters: a strategy holding 60 days cannot reach n=20 in 90 days. Killing
it on trade count would kill every slow strategy for being slow, not for losing. That is
the "eliminate fast vs hold longer" split, decided by expected holding period, not by PnL.
"""
import json, os, sys, math, random, argparse
from datetime import date, datetime, timezone

STATE = "state/forward_test"
LEDGER = os.path.join(STATE, "ledger.jsonl")
PLAN = os.path.join(STATE, "plan.json")

# hold_type is pre-registered per strategy id. short = fast elimination clock.
# Only backtest SURVIVORS belong here. The rest were killed on 2004-2026 evidence
# (see 10_simulations/BACKTEST_PROOF.md) and must not consume forward-test months.
DEFAULT_PLAN = {
    "created": date.today().isoformat(),
    "rules_version": "1.1",
    "strategies": {
        "FABER10_SPY":  {"class": "ETF", "hold_type": "long",  "trades_per_year": 1.5,
                         "backtest_max_dd": -0.218, "thesis": "10M SMA overlay: risk reduction, not alpha"},
        "BTC_TREND200": {"class": "CRYPTO", "hold_type": "long", "trades_per_year": 2.7,
                         "backtest_max_dd": -0.636, "thesis": "200d SMA on BTC: promising, DSR 0.84"},
    },
    "killed_in_backtest": {
        "RSI2_SPY": "0.21% CAGR, SR -0.64, DSR 0.00, negative at 2x costs",
        "DUALMOM_2": "-2.57%/yr vs matched exposure",
        "DUALMOM_3": "+2.55% IS then -6.34% OOS (regime overfit)",
        "SIXTY_FORTY": "-3.03%/yr vs 60% SPY + 40% cash",
    },
}


def _ensure():
    os.makedirs(STATE, exist_ok=True)
    if not os.path.exists(PLAN):
        json.dump(DEFAULT_PLAN, open(PLAN, "w"), indent=1)


def load_plan():
    _ensure(); return json.load(open(PLAN))


def load_trades():
    _ensure()
    if not os.path.exists(LEDGER): return []
    out = []
    for ln in open(LEDGER):
        ln = ln.strip()
        if ln:
            try: out.append(json.loads(ln))
            except json.JSONDecodeError: pass
    return out


def cmd_log(a):
    _ensure()
    pnl = (a.exit - a.entry) * a.qty - a.fees
    d0 = datetime.strptime(a.opened, "%Y-%m-%d").date()
    d1 = datetime.strptime(a.closed, "%Y-%m-%d").date()
    rec = {"strategy": a.strategy, "symbol": a.symbol, "side": a.side,
           "entry": a.entry, "exit": a.exit, "qty": a.qty, "fees": a.fees,
           "pnl": round(pnl, 6), "opened": a.opened, "closed": a.closed,
           "hold_days": (d1 - d0).days,
           "ret_pct": round((a.exit / a.entry - 1) * 100, 4) if a.side == "long"
                      else round((a.entry / a.exit - 1) * 100, 4),
           "thesis": a.thesis or "", "logged_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    with open(LEDGER, "a") as f:
        f.write(json.dumps(rec) + "\n")
    print(f"logged {a.strategy} {a.symbol}: pnl={pnl:+.2f} hold={rec['hold_days']}d")


def wilson_lower(w, n, z=1.645):
    if n == 0: return 0.0
    p = w / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - m) / d


def pf(rets):
    g = sum(r for r in rets if r > 0); l = -sum(r for r in rets if r < 0)
    if l <= 0: return float("inf") if g > 0 else 0.0
    return g / l


def boot_pf(rets, k=2000, seed=7):
    if len(rets) < 4: return (float("nan"), float("nan"))
    rnd = random.Random(seed); out = []
    for _ in range(k):
        s = [rets[rnd.randrange(len(rets))] for _ in rets]
        v = pf(s)
        out.append(v if v != float("inf") else 99.0)
    out.sort()
    return (out[int(0.05 * k)], out[int(0.95 * k)])


def decide(name, cfg, trades, today):
    n = len(trades)
    hd = [t["hold_days"] for t in trades]
    avg_hold = sum(hd) / n if n else 0.0
    start = cfg.get("start") or (load_plan().get("created"))
    days = (today - datetime.strptime(start, "%Y-%m-%d").date()).days if start else 0
    # "Slow" = cannot reach n=20 inside a quarter, either because holds are long or because
    # the rule fires rarely. Frequency matters, not just hold length: a 2-day rule that fires
    # 5x/yr still takes 4 years to reach 20 trades.
    tpy = cfg.get("trades_per_year")
    slow = cfg.get("hold_type", "long") == "long" or avg_hold >= 5 or (tpy is not None and tpy < 25)
    if n == 0:
        return ("BROKEN" if days >= 60 else "CONTINUE", f"0 trades in {days}d", dict(n=0, days=days))
    rets = [t["pnl"] for t in trades]
    w = sum(1 for r in rets if r > 0)
    P = pf(rets); wl = wilson_lower(w, n); b5, b95 = boot_pf(rets)
    stats = dict(n=n, days=days, wr=w / n, pf=P, wilson_lower=wl, boot5=b5, boot95=b95,
                 avg_hold=round(avg_hold, 1), avg_pnl=sum(rets) / n,
                 expectancy=sum(rets) / n)
    # BREAKER: the fast exit for slow strategies — no waiting for n=20 or a calendar anniversary.
    # 10 trades at PF<0.75 is evidence, not noise.
    if n >= 10 and P < 0.75:
        return ("KILL", f"BREAKER n={n} PF={P:.2f} < 0.75", stats)
    if not slow:
        if n >= 20 and (P < 1.00 or wl < 0.40):
            return ("KILL", f"n={n} PF={P:.2f} WRlb={wl:.2f}", stats)
        if n >= 30 and P >= 1.15 and b5 > 1.05:
            return ("PROMOTE", f"n={n} PF={P:.2f} boot5={b5:.2f}", stats)
        return ("CONTINUE", f"n={n}/{20 if n < 20 else 30}", stats)
    if days < 180:
        return ("CONTINUE", f"{days}d < 180d checkpoint (n={n})", stats)
    if days < 365:
        if n >= 8 and P < 1.00: return ("KILL", f"180d n={n} PF={P:.2f}", stats)
        return ("CONTINUE", f"180d checkpoint passed, n={n}", stats)
    if n < 20:
        if days < 730: return ("HOLD-LONGER", f"{days}d but n={n}<20, avg_hold={avg_hold:.0f}d", stats)
        if P < 1.00: return ("KILL", f"730d n={n} PF={P:.2f}", stats)
        return ("CONTINUE", f"730d n={n}", stats)
    if P < 1.05: return ("KILL", f"365d n={n} PF={P:.2f}", stats)
    if P >= 1.15 and b5 > 1.00: return ("PROMOTE", f"365d n={n} PF={P:.2f} boot5={b5:.2f}", stats)
    return ("CONTINUE", f"365d n={n} PF={P:.2f} between 1.05 and 1.15", stats)


def cmd_status(a):
    plan = load_plan(); trades = load_trades()
    today = date.today()
    by = {}
    for t in trades: by.setdefault(t["strategy"], []).append(t)
    ids = list(plan["strategies"]) + [k for k in by if k not in plan["strategies"]]
    print(f"forward ledger: {len(trades)} closed trades across {len(by)} strategies\n")
    print(f"{'strategy':<14}{'n':>4}{'days':>6}{'WR':>7}{'PF':>7}{'PF5%':>7}{'avgHold':>9}  {'verdict':<13}note")
    rows = []
    for k in ids:
        cfg = plan["strategies"].get(k, {"hold_type": "long"})
        v, note, st = decide(k, cfg, by.get(k, []), today)
        st.update(strategy=k, verdict=v, note=note)
        rows.append(st)
        print(f"{k:<14}{st.get('n',0):>4}{st.get('days',0):>6}{st.get('wr',0)*100:>6.1f}%"
              f"{st.get('pf',0):>7.2f}{st.get('boot5',float('nan')):>7.2f}{st.get('avg_hold',0):>8.0f}d  {v:<13}{note}")
    ap = os.path.join(STATE, "status.json")
    json.dump({"as_of": str(today), "rows": rows}, open(ap, "w"), indent=1)
    print(f"\nwrote {ap}")
    print("\nsample size needed to separate a per-trade edge from luck "
          "(one-sided 5%, 80% power):  n = ((1.645+0.842)/SR_per_trade)^2")
    for sr in (0.40, 0.30, 0.20, 0.15, 0.10):
        print(f"  per-trade Sharpe {sr:.2f} -> {math.ceil(((1.645 + 0.842) / sr) ** 2):>4} closed trades")
    print("  read: a strategy whose real edge is 0.20 per-trade Sharpe needs ~155 closed trades")
    print("  before a 'PROMOTE' is statistically honest. 'KILL' needs far fewer (see rules above).")


def cmd_selftest(a):
    """Prove the decision rules fire correctly before trusting them."""
    import tempfile, shutil
    from datetime import timedelta
    print("selftest: decision rules")
    base = date(2026, 1, 1)
    def mk(pnls, hold=2):
        return [{"strategy": "X", "pnl": p, "hold_days": hold, "opened": str(base),
                 "closed": str(base + timedelta(days=hold))} for p in pnls]
    cases = [
        ("fast losing (n=25, mostly -1)", mk([-1.0]*18 + [1.0]*7), {"hold_type": "short", "start": str(base)}, base + timedelta(days=120), "KILL"),
        ("fast winning (n=40, PF~2)",     mk([2.0]*27 + [-1.0]*13), {"hold_type": "short", "start": str(base)}, base + timedelta(days=120), "PROMOTE"),
        ("fast early (n=10)",             mk([1.0]*10), {"hold_type": "short", "start": str(base)}, base + timedelta(days=30), "CONTINUE"),
        ("slow losing @200d n=10",        mk([-1.0]*7 + [1.0]*3, hold=40), {"hold_type": "long", "start": str(base)}, base + timedelta(days=200), "KILL"),
        ("slow thin @400d n=10",          mk([1.0]*6 + [-1.0]*4, hold=60), {"hold_type": "long", "start": str(base)}, base + timedelta(days=400), "HOLD-LONGER"),
        ("slow no trades @90d",           [], {"hold_type": "long", "start": str(base)}, base + timedelta(days=90), "BROKEN"),
        ("breaker: slow, n=12, PF<0.75",  mk([-1.0]*10 + [1.0]*2, hold=60), {"hold_type": "long", "start": str(base)}, base + timedelta(days=100), "KILL"),
        # 9 trades, PF 0.50 @200d: a FAST rule would say "n<20, keep going"; the slow clock
        # (fires 5x/yr) kills at n>=8. This case distinguishes the two clocks.
        ("rare-fire rule uses slow clock", mk([-1.0]*6 + [1.0]*3, hold=2), {"hold_type": "short", "trades_per_year": 5, "start": str(base)}, base + timedelta(days=200), "KILL"),
    ]
    ok = 0
    for label, tr, cfg, today, want in cases:
        got, note, _ = decide("X", cfg, tr, today)
        flag = "PASS" if got == want else "FAIL"
        ok += got == want
        print(f"  [{flag}] {label:<32} want={want:<12} got={got:<12} ({note})")
    print(f"\n{ok}/{len(cases)} rule cases pass")
    return 0 if ok == len(cases) else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    lg = sub.add_parser("log")
    lg.add_argument("--strategy", required=True); lg.add_argument("--symbol", required=True)
    lg.add_argument("--side", default="long", choices=["long", "short"])
    lg.add_argument("--entry", type=float, required=True); lg.add_argument("--exit", type=float, required=True)
    lg.add_argument("--qty", type=float, default=1.0); lg.add_argument("--fees", type=float, default=0.0)
    lg.add_argument("--opened", required=True); lg.add_argument("--closed", required=True)
    lg.add_argument("--thesis", default="")
    sub.add_parser("status"); sub.add_parser("selftest")
    a = ap.parse_args()
    if a.cmd == "init":
        _ensure(); print(f"initialised {PLAN} and {LEDGER}")
    elif a.cmd == "log": cmd_log(a)
    elif a.cmd == "status": cmd_status(a)
    elif a.cmd == "selftest": sys.exit(cmd_selftest(a))


if __name__ == "__main__":
    main()
