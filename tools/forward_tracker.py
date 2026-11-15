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

# Cost assumption applied to synced ledger rows, on BOTH legs of the round trip.
# Matches the 6 bps/side the vwap-reversion-scout backtest assumed, so a forward
# PF is measured against the same cost basis as the prior it is testing.
# Override per strategy with fee_bps_per_side in plan.json, or per run with
# --fee-bps-per-side. `pnl` in the ledger is NET; `pnl_gross` keeps the raw move.
DEFAULT_FEE_BPS_PER_SIDE = 6.0

STATE = "state/forward_test"
LEDGER = os.path.join(STATE, "ledger.jsonl")
PLAN = os.path.join(STATE, "plan.json")

# hold_type is pre-registered per strategy id. short = fast elimination clock.
# Only backtest SURVIVORS belong here. The rest were killed on 2004-2026 evidence
# (see 10_simulations/BACKTEST_PROOF.md) and must not consume forward-test months.
DEFAULT_PLAN = {
    "created": date.today().isoformat(),
    "rules_version": "1.1",
    "cost_model": {"fee_bps_per_side": 6.0,
                   "applies_to": "both legs of the round trip, on notional"},
    "strategies": {
        "FABER10_SPY":  {"class": "ETF", "hold_type": "long",  "trades_per_year": 1.5,
                         "backtest_max_dd": -0.218, "thesis": "10M SMA overlay: risk reduction, not alpha"},
        "BTC_TREND200": {"class": "CRYPTO", "hold_type": "long", "trades_per_year": 2.7,
                         "backtest_max_dd": -0.636, "thesis": "200d SMA on BTC: promising, DSR 0.84"},
        # Registered 2026-11-15 on live-ledger evidence only: 28 closed picks over 25
        # independent windows, +1.96pp vs SPY, CLUSTERED t=1.99. That t does not clear 2.0
        # and 25 windows is too few to promote on — which is exactly why it needs a
        # pre-registered forward clock instead of another retrospective look.
        "vwap-reversion-scout": {
            "class": "EQUITY", "hold_type": "long", "trades_per_year": 48,
            "start": "2026-11-15", "backtest_max_dd": None, "auto_sync": True,
            "thesis": "Price >2% below its 20d VWAP with RSI<40 and the close in the upper half "
                      "of the day's range: institutional cost-basis reversion on liquid US names. "
                      "Exit on TP/SL or a 168h (7-day) time stop.",
            "baseline": {"source": "reports/pick_excess_returns.json", "measured_on": "2026-11-15",
                         "n_picks": 28, "n_windows": 25, "mean_excess_pp": 1.96,
                         "t_cluster": 1.99, "excess_win_rate_pct": 60.7, "median_hold_hours": 145,
                         "status": "PRIOR ONLY — not evidence that survives forward testing"},
            "kill_rule": "slow clock (median hold >5d): 180d & n>=8 & PF<1.00 -> KILL; "
                         "365d & n>=20 & PF<1.05 -> KILL; breaker n>=10 & PF<0.75 -> KILL. "
                         "PROMOTE requires 365d, n>=20, PF>=1.15 and boot5(PF)>1.00.",
        },
        # Registered 2026-11-15 as the second forward candidate: the vwap clock alone
        # needs ~3 years to reach a promotion sample. Prior is IN-SAMPLE SELECTION
        # (best clustered t of 127 pairs screened, |t|=1.74 vs a Bonferroni bar of
        # 3.54) and is recorded as weak evidence, not as an edge.
        "rs-breakout-scout": {
            "class": "EQUITY", "hold_type": "long", "trades_per_year": 74,
            "start": "2026-11-15", "backtest_max_dd": None, "auto_sync": True,
            "strict_class": True, "fee_bps_per_side": 6.0,
            "prior": {"n_picks": 45, "n_windows": 44, "mean_excess_pp": 1.084,
                      "sd_window_pp": 4.122, "t_cluster": 1.74, "excess_win_rate_pct": 53.3,
                      "status": "IN-SAMPLE SELECTION ONLY — fails Bonferroni (|t|>=3.54 at k=127)"},
            "measurement_design": {"windows_needed_fixed_sample": 152,
                                   "interim_looks": [25, 50, 100, 152],
                                   "interim_rule": "O'Brien-Fleming alpha spending; no KILL before "
                                                   "n>=20 windows, no PROMOTE before 152"},
            "kill_rule": "KILL at any look with n>=20 if mean excess < 0 and boot5(PF) < 1.00; "
                         "KILL at n>=50 if mean excess < +0.25pp. PROMOTE requires 152 windows, "
                         "mean excess > 0 and |t| >= 1.96.",
        },
    },
    "cost_model": {"fee_bps_per_side": 6.0,
                   "applies_to": "both legs of the round trip, on notional"},
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
           "thesis": a.thesis or "", "pick_id": getattr(a, "pick_id", None), "source": "manual",
           "logged_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    _append(rec)
    print(f"logged {a.strategy} {a.symbol}: pnl={pnl:+.2f} hold={rec['hold_days']}d")


def _append(rec):
    with open(LEDGER, "a") as f:
        f.write(json.dumps(rec) + "\n")


def _parse_ts(s):
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


def _ledger_keys(trades):
    """Idempotency keys: the pick id when present, plus a composite fallback so a
    re-run after losing the id column still cannot double-count a trade."""
    keys = set()
    for t in trades:
        if t.get("pick_id"):
            keys.add("id:" + str(t["pick_id"]))
        keys.add("k:%s|%s|%s|%s|%s" % (t.get("strategy"), t.get("symbol"), t.get("side"),
                                       t.get("opened"), t.get("closed")))
    return keys


def cmd_sync(a):
    """Append CLOSED picks from the live dashboard payload into the ledger so the
    forward clock fills itself.

    PRE-REGISTRATION GUARD (structural, not a flag): a pick is admitted only if it
    CLOSED on or after that strategy's registered start date. Every pick that
    produced the motivating prior closed before registration, so it cannot enter
    the ledger. The sample that generated a hypothesis is therefore never allowed
    to confirm it, and nobody has to remember not to backfill.
    """
    _ensure()
    plan = load_plan()
    if a.strategy:
        strategies = [a.strategy]
    else:
        strategies = [k for k, v in plan["strategies"].items() if v.get("auto_sync")]
    if not strategies:
        print("no strategies registered with auto_sync; pass --strategy <name>")
        return
    if not os.path.exists(a.dashboard):
        print(f"dashboard payload not found: {a.dashboard}")
        return
    payload = json.load(open(a.dashboard))
    rows = ((payload.get("picks") or {}).get("recent_closed")) or []
    existing = _ledger_keys(load_trades())
    print(f"sync {a.dashboard} ({len(rows)} closed rows, generated_at {payload.get('generated_at')})")

    total_added = 0
    for k in strategies:
        cfg = plan["strategies"].get(k, {})
        since = _parse_ts(a.since or cfg.get("start") or plan.get("created"))
        added = dupe = early = incomplete = class_mismatch = 0
        want_class = (cfg.get("class") or "").upper()
        for p in rows:
            if (p.get("strategy") or "") != k:
                continue
            closed = _parse_ts(p.get("closed_at") or p.get("resolved_at"))
            opened = _parse_ts(p.get("timestamp") or p.get("entry_time"))
            e, x = p.get("entry_price"), p.get("exit_price")
            side = (p.get("direction") or "").strip().lower()
            side = "long" if side in ("buy", "long") else "short" if side in ("sell", "short") else ""
            if not (closed and opened and e and x and e > 0 and x > 0 and side):
                incomplete += 1
                continue
            if (cfg.get("strict_class") and want_class
                    and (p.get("asset_class") or "").upper() not in ("", want_class)):
                # Opt-in: only when the prior was measured on ONE class (rs-breakout-scout
                # is EQUITY-only). vwap-reversion-scout's prior spans EQUITY+ETF, so it does
                # not set strict_class. Skipped rows are COUNTED, never silently dropped.
                class_mismatch += 1
                continue
            if since and closed < since:
                early += 1
                continue
            key_id = ("id:" + str(p["id"])) if p.get("id") else None
            key_c = "k:%s|%s|%s|%s|%s" % (k, p.get("symbol"), side, opened.date(), closed.date())
            if (key_id and key_id in existing) or key_c in existing:
                dupe += 1
                continue
            e, x = float(e), float(x)
            qty = a.notional / e
            pnl_gross = (x - e) * qty if side == "long" else (e - x) * qty
            # Net of costs. The dashboard payload has no fee field, so the backtest's
            # assumption is applied explicitly: fee_bps_per_side on BOTH legs of the
            # round trip. `pnl` (what decide() consumes) is the NET number, so a
            # forward PF cannot look healthy by ignoring costs.
            bps = (a.fee_bps_per_side if a.fee_bps_per_side is not None
                   else cfg.get("fee_bps_per_side",
                                (plan.get("cost_model") or {}).get("fee_bps_per_side",
                                                                   DEFAULT_FEE_BPS_PER_SIDE)))
            fees = a.notional * (bps / 10000.0) * 2.0
            pnl = pnl_gross - fees
            rec = {
                "strategy": k, "symbol": p.get("symbol"), "side": side,
                "entry": e, "exit": x, "qty": round(qty, 8), "fees": round(fees, 6),
                "pnl": round(pnl, 6), "pnl_gross": round(pnl_gross, 6),
                "fee_bps_per_side": bps,
                "opened": str(opened.date()), "closed": str(closed.date()),
                "hold_days": (closed.date() - opened.date()).days,
                "ret_pct": round((x / e - 1) * 100 if side == "long" else (e / x - 1) * 100, 4),
                "thesis": "auto-synced from dashboard: %s" % (p.get("exit_reason") or "?"),
                "pick_id": p.get("id"), "source": "dashboard_sync",
                "asset_class": (p.get("asset_class") or "").upper(),
                "notional_usd": a.notional,
                "cost_model": "net: %g bps/side on both legs of %g notional" % (bps, a.notional),
                "logged_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
            if a.dry_run:
                if added < 5:
                    print(f"   would add {p.get('symbol'):9} {side:5} {rec['opened']} -> {rec['closed']} "
                          f"gross={pnl_gross:+.2f} fees={fees:.2f} net={pnl:+.2f} ({p.get('exit_reason')})")
                added += 1
            else:
                _append(rec)
                added += 1
            existing.add(key_c)
            if key_id:
                existing.add(key_id)
        total_added += added
        print(f"  {k}: {'would append' if a.dry_run else 'appended'} {added} | "
              f"closed before registration {early} | duplicate {dupe} | incomplete {incomplete} | "
              f"class mismatch {class_mismatch}")
    print(f"  total {'would append' if a.dry_run else 'appended'}: {total_added}")
    if not a.dry_run and total_added:
        print(f"  ledger now {len(load_trades())} rows -> {LEDGER}")


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


# ---------------------------------------------------------------------------
# O'Brien-Fleming interim monitoring
#
# A fixed-sample test at n=152 can only speak once, ~2 years out. A sequential
# design can speak earlier WITHOUT inflating type I, provided the boundaries are
# fixed before the data arrive. That is what these are: c_k = C / sqrt(t_k) with
# t_k the information fraction, and C solved numerically so the total one-sided
# probability of crossing under H0 is exactly alpha.
#
# The solve uses the exact joint distribution (Z_k standardised, correlation
# sqrt(t_j/t_k)), not a normal approximation, so the boundaries are the real
# O'Brien-Fleming ones rather than the textbook C = z_{1-alpha/2} shortcut.
# ---------------------------------------------------------------------------
_GRID_N, _GRID_LO, _GRID_HI = 240, -8.0, 8.0
_OF_CACHE = {}


def _phi(x):
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


def _Phi(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _grid():
    n = _GRID_N
    zs = [_GRID_LO + (_GRID_HI - _GRID_LO) * i / n for i in range(n + 1)]
    w = [(_GRID_HI - _GRID_LO) / n] * (n + 1)
    w[0] *= 0.5; w[-1] *= 0.5
    return zs, w


def _kernels(ts):
    """Transition densities for standardised Z with Cov(Z_j, Z_k) = sqrt(t_j/t_k)."""
    zs, w = _grid(); G = _GRID_N
    out = [None]
    for k in range(1, len(ts)):
        rho = math.sqrt(ts[k - 1] / ts[k])
        s = math.sqrt(max(1e-12, 1.0 - ts[k - 1] / ts[k]))
        out.append([[_phi((zs[i] - zs[j] * rho) / s) / s * w[j] for j in range(G + 1)]
                    for i in range(G + 1)])
    return out


def _tail(g, zs, c):
    """Integrate g from c to +inf, interpolating inside the crossing cell.

    A step mask (z_i >= c) makes the crossing probability jump by one grid cell as
    the boundary bisection moves, which showed up as achieved-alpha jitter
    (0.0494 vs 0.0507 for the same solved C). Linear interpolation removes it.
    """
    h = zs[1] - zs[0]
    total = 0.0
    for j in range(len(zs) - 1):
        a, b = zs[j], zs[j + 1]
        if b <= c:
            continue
        ga, gb = g[j], g[j + 1]
        if a < c:
            gc = ga + (gb - ga) * ((c - a) / (b - a))
            total += (b - c) * (gc + gb) / 2.0
        else:
            total += h * (ga + gb) / 2.0
    return total


def _spend(C, ts, Ks):
    """Total one-sided crossing probability (alpha spent) for boundary C/sqrt(t_k)."""
    zs, w = _grid(); G = _GRID_N
    cs = [C / math.sqrt(t) for t in ts]
    g = [_phi(z) for z in zs]
    total = _tail(g, zs, cs[0])
    for k in range(1, len(ts)):
        prev = [g[j] if zs[j] < cs[k - 1] else 0.0 for j in range(G + 1)]
        K = Ks[k]
        g = [sum(K[i][j] * prev[j] for j in range(G + 1)) for i in range(G + 1)]
        total += _tail(g, zs, cs[k])
    return total


def of_boundaries(looks, n_final, alpha=0.05):
    """-> (boundaries, achieved_alpha). Cached: the solve costs ~0.3s."""
    key = (tuple(looks), n_final, round(alpha, 6))
    if key in _OF_CACHE:
        return _OF_CACHE[key]
    ts = [l / float(n_final) for l in looks]
    Ks = _kernels(ts)
    lo, hi = 0.5, 4.0
    for _ in range(50):
        mid = (lo + hi) / 2.0
        if _spend(mid, ts, Ks) > alpha: lo = mid
        else: hi = mid
    C = (lo + hi) / 2.0
    res = ([C / math.sqrt(t) for t in ts], _spend(C, ts, Ks))
    _OF_CACHE[key] = res
    return res


def _mean_sd(vals):
    n = len(vals)
    m = sum(vals) / n
    if n < 2: return m, float("nan")
    return m, math.sqrt(sum((x - m) ** 2 for x in vals) / (n - 1))


def _endpoint(rows):
    """Registered endpoint first.

    The pre-registered statistic is excess_pp vs the class benchmark. Ledger rows
    only carry it if the source supplied it; when they do not, this falls back to
    net return and RETURNS THE NAME, so the verdict can say which statistic it
    actually tested. Testing a different statistic than the pre-registered one
    without saying so is how a forward test turns into a story.
    """
    if rows and all(isinstance(r.get("excess_pp"), (int, float)) for r in rows):
        return "excess_pp", [float(r["excess_pp"]) for r in rows]
    out = []
    for r in rows:
        notional = r.get("notional_usd") or (abs(r.get("entry") or 0.0) * abs(r.get("qty") or 1.0))
        out.append((r.get("pnl", 0.0) / notional * 100.0) if notional else 0.0)
    return "net_return_pp", out


def _fmtz(x):
    if x is None: return "n/a"
    if isinstance(x, float):
        if math.isnan(x): return "n/a"
        if math.isinf(x): return "inf" if x > 0 else "-inf"
    return f"{x:.2f}"


def interim_verdict(cfg, trades, today=None):
    """Apply the pre-registered O'Brien-Fleming looks. Returns None if the strategy
    has no measurement design (most do not)."""
    d = cfg.get("measurement_design") or {}
    looks = d.get("interim_looks") or []
    n_final = d.get("windows_needed_fixed_sample")
    if not looks or not n_final:
        return None
    alpha = float(d.get("alpha", 0.05))
    if not trades:
        return dict(verdict="CONTINUE", endpoint=d.get("endpoint", "excess_pp"), n=0,
                    target=n_final, next_look=looks[0], z=None, boundary=None,
                    note=f"0/{looks[0]} windows to the first look")
    endpoint, per_row = _endpoint(trades)
    wins = {}
    for r, v in zip(trades, per_row):
        wins.setdefault((r.get("opened"), r.get("closed")), []).append(v)
    win_means = [sum(v) / len(v) for v in wins.values()]
    n = len(win_means)
    bounds, achieved = of_boundaries(looks, n_final, alpha)
    base = dict(endpoint=endpoint, n=n, target=n_final,
                boundaries=[round(b, 3) for b in bounds],
                achieved_alpha=round(achieved, 4), alpha=alpha)
    reached = [i for i, L in enumerate(looks) if n >= L]
    if not reached:
        base.update(verdict="CONTINUE", next_look=looks[0], z=None,
                    boundary=round(bounds[0], 3),
                    note=f"{n}/{looks[0]} windows to the first look")
        return base
    k = reached[-1]
    sub = win_means[:looks[k]]            # data available AT that scheduled look
    m, sd = _mean_sd(sub)
    se = sd / math.sqrt(len(sub)) if len(sub) > 1 else float("nan")
    if math.isnan(se) or se == 0:
        z = float("nan") if math.isnan(se) else (float("inf") if m > 0 else (0.0 if m == 0 else float("-inf")))
    else:
        z = m / se
    b5, _ = boot_pf([t["pnl"] for t in trades])
    base.update(z=(None if isinstance(z, float) and math.isnan(z) else round(z, 2)),
                boundary=round(bounds[k], 3), look=looks[k],
                mean_pp=round(m, 3),
                sd_pp=(None if math.isnan(sd) else round(sd, 3)),
                next_look=(looks[k + 1] if k + 1 < len(looks) else None),
                windows_seen=n)
    for kr in d.get("kill_rules") or []:
        at = kr.get("at_n_windows", 0)
        if n < at: continue
        thr = kr.get("if_mean_lt_pp", 0.0)
        pf_thr = kr.get("and_pf5_lt")
        if m < thr and (pf_thr is None or (not math.isnan(b5) and b5 < pf_thr)):
            base.update(verdict="KILL",
                        note=f"mean {m:+.3f}pp < {thr:g}pp at n={n}" +
                             (f" and boot5(PF)={b5:.2f} < {pf_thr:.2f}" if pf_thr is not None else ""))
            return base
    if not math.isnan(z) and z >= bounds[k]:
        base.update(verdict="PROMOTE",
                    note=f"z={_fmtz(z)} crosses the OF boundary {bounds[k]:.2f} at look n={looks[k]}")
        return base
    base.update(verdict="CONTINUE",
                note=f"z={_fmtz(z)} < boundary {bounds[k]:.2f} at look n={looks[k]}")
    return base


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
    if any((plan["strategies"].get(r["strategy"]) or {}).get("measurement_design") for r in rows):
        print("\npre-registered interim looks (O'Brien-Fleming, one-sided alpha shared across looks)")
        for st in rows:
            k = st["strategy"]
            iv = interim_verdict(plan["strategies"].get(k, {}), by.get(k, []), today)
            if not iv: continue
            st["interim"] = iv
            nxt = iv.get("next_look")
            print(f"  {k:<24}{iv['verdict']:<10}windows {iv['n']:>4}/{iv['target']:<4}"
                  f"look={str(iv.get('look') or '-'):>4} next={str(nxt or '-'):>4} "
                  f"z={_fmtz(iv.get('z')):<6}bar={_fmtz(iv.get('boundary')):<6}endpoint={iv['endpoint']}")

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

    print("\nselftest: O'Brien-Fleming interim boundaries")
    looks, nf = [25, 50, 100, 152], 152
    b, achieved = of_boundaries(looks, nf, 0.05)
    checks = [
        ("boundaries monotone decreasing", all(b[i] > b[i + 1] for i in range(len(b) - 1))),
        (f"achieved alpha {achieved:.4f} within 0.02 of 0.05", abs(achieved - 0.05) <= 0.02),
        (f"final boundary {b[-1]:.2f} >= z_0.95 1.645", b[-1] >= 1.6449 - 1e-9),
        (f"first boundary {b[0]:.2f} > 2x final (early looks are strict)", b[0] > 2 * b[-1]),
    ]
    design = {"interim_looks": looks, "windows_needed_fixed_sample": nf, "alpha": 0.05}
    def series(fn, count):
        return [{"strategy": "X", "pnl": fn(i), "notional_usd": 1000.0, "hold_days": 5,
                 "opened": str(base + timedelta(days=i)),
                 "closed": str(base + timedelta(days=i + 3))} for i in range(count)]
    iv = interim_verdict({"measurement_design": design}, series(lambda i: 30.0, looks[0]), base)
    checks.append((f"overwhelming edge promotes at look 1 (z={_fmtz(iv.get('z'))})",
                   iv["verdict"] == "PROMOTE"))
    iv2 = interim_verdict({"measurement_design": design}, series(lambda i: 2.0 if i % 2 else -2.0, looks[0]), base)
    checks.append((f"coin flip does NOT promote (z={_fmtz(iv2.get('z'))})",
                   iv2["verdict"] == "CONTINUE"))
    iv3 = interim_verdict({"measurement_design": design}, series(lambda i: 1.0, looks[0] - 1), base)
    checks.append((f"below the first look stays CONTINUE (n={iv3['n']})",
                   iv3["verdict"] == "CONTINUE" and iv3.get("z") is None))
    kill_design = dict(design, kill_rules=[{"at_n_windows": 20, "if_mean_lt_pp": 0, "and_pf5_lt": 1.0}])
    iv4 = interim_verdict({"measurement_design": kill_design}, series(lambda i: -10.0, looks[0]), base)
    checks.append(("losing series KILLs at the look", iv4["verdict"] == "KILL"))
    for label, okv in checks:
        print(f"  [{'PASS' if okv else 'FAIL'}] {label}")
        ok += okv

    total = len(cases) + len(checks)
    print(f"\n{ok}/{total} checks pass ({len(cases)} rule cases, {len(checks)} OF checks)")
    return 0 if ok == total else 1


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
    sy = sub.add_parser("sync")
    sy.add_argument("--dashboard", default="audit_dashboard/data/dashboard_data.json")
    sy.add_argument("--strategy", default="", help="default: every plan strategy with auto_sync")
    sy.add_argument("--since", default="", help="override the pre-registration date (use with --dry-run)")
    sy.add_argument("--notional", type=float, default=10000.0,
                    help="notional per trade so ledger pnl stays in dollars like manual log entries")
    sy.add_argument("--fee-bps-per-side", type=float, default=None,
                    help="cost assumption applied to both legs (default: plan fee_bps_per_side, else %.1f)"
                         % DEFAULT_FEE_BPS_PER_SIDE)
    sy.add_argument("--dry-run", action="store_true")
    sub.add_parser("status"); sub.add_parser("selftest")
    a = ap.parse_args()
    if a.cmd == "init":
        _ensure(); print(f"initialised {PLAN} and {LEDGER}")
    elif a.cmd == "log": cmd_log(a)
    elif a.cmd == "sync": cmd_sync(a)
    elif a.cmd == "status": cmd_status(a)
    elif a.cmd == "selftest": sys.exit(cmd_selftest(a))


if __name__ == "__main__":
    main()
