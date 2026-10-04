#!/usr/bin/env python3
"""
equity_reachability_replay.py — does a *reachable* TP make EQUITY/ETF money-ready?
==================================================================================

The 2026-06-13 money-ready loop diagnosed the blocker as REACHABILITY: picks set
take-profits the price never reaches inside the hold window, so they time-exit flat
(reports/AMPLITUDE_GATE_ANALYSIS_2026-06-13.md, status-based inference). EQUITY/ETF
are the only classes with intraday OHLCV in this DB (`stock_ohlcv`, hourly bars), so
they are the only classes where that inference can be UPGRADED to a true intrabar
replay and the prescription ("size TP to X%") can be measured, not guessed.

What this does (read-only on the DB):
  Stage 1  Realized excursion — replay hourly bars from each pick's entry over a fixed
           horizon; report the max-favorable (MFE) and max-adverse (MAE) excursion
           distribution. This is descriptive (no fitting) and is the actionable
           prescription: it says how far these signals actually move.
  Stage 2  Original-TP reachability — replay each pick's OWN tp/sl (SL-first, conservative
           first-touch) and report how often the original TP was reachable inside the
           horizon. Cross-checks replay outcome vs the recorded DB status.
  Stage 3  TP/SL grid with an IS/OOS TIME-SPLIT — fit the best (tp,sl) cell on the
           in-sample (older) half by NET-of-cost PF, then report that same cell's
           out-of-sample (newer) half. A cell is only "money-ready" if its OOS net PF
           clears the bar. This guards against the exit-curve-fitting trap.

Disciplines baked in (hard-won this project):
  * NET of cost always (equity round-trip default 8bp); gross is shown only for contrast.
  * SL-first when a single bar straddles both levels (conservative, never optimistic).
  * Banned sources excluded by default (multi_asset_copytrader / multi_asset_scanner).
  * Stale-entry guard: skip picks whose stated entry_price is >TOL off the first OHLCV
    bar (templated/duplicate entries corrupt the anchor) — counted and reported.
  * IS/OOS time-split so a grid winner must survive forward, not just fit in-sample.

Usage (read-only; creds from env/dbpasses, never hardcoded):
  DB_PASS_STOCKS=... python3 tools/equity_reachability_replay.py
  DB_PASS_STOCKS=... python3 tools/equity_reachability_replay.py --category EQUITY ETF \
      --horizon-bars 30 --cost-bps 8 --json reports/equity_reachability_2026-06-13.json
  python3 tools/equity_reachability_replay.py --self-test    # no network

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Sources we never count toward a headline edge (documented bans).
BANNED_SOURCES = {"multi_asset_copytrader", "multi_asset_scanner"}

# Money-ready bar (PERFORMANCE_CHARTER Tier 2).
T2_PF = 1.5
T2_WR = 0.50


# --------------------------------------------------------------------------- #
# Core replay primitives (pure; unit-testable without a DB)
# --------------------------------------------------------------------------- #
def excursions(entry: float, direction: str, bars: list) -> tuple[float, float]:
    """Return (MFE, MAE) as signed-favorable / signed-adverse fractions over `bars`.

    MFE = best favorable move reached; MAE = worst adverse move reached (both >= 0).
    bars: list of dicts with high/low (floats).
    """
    if entry <= 0 or not bars:
        return 0.0, 0.0
    longish = str(direction).upper() in ("LONG", "BUY")
    mfe = mae = 0.0
    for b in bars:
        hi = float(b["high"]); lo = float(b["low"])
        if longish:
            mfe = max(mfe, hi / entry - 1.0)
            mae = max(mae, 1.0 - lo / entry)
        else:
            mfe = max(mfe, 1.0 - lo / entry)
            mae = max(mae, hi / entry - 1.0)
    return mfe, mae


def first_touch(entry: float, direction: str, bars: list, tp: float, sl: float) -> dict:
    """SL-first conservative first-touch over `bars`.

    tp, sl are positive fractions (distance from entry). Returns
    {outcome: TP|SL|TIME, gross: signed fraction, ambiguous: bool, bars_held: int}.
    """
    longish = str(direction).upper() in ("LONG", "BUY")
    if longish:
        tp_price, sl_price = entry * (1 + tp), entry * (1 - sl)
    else:
        tp_price, sl_price = entry * (1 - tp), entry * (1 + sl)

    for i, b in enumerate(bars):
        hi = float(b["high"]); lo = float(b["low"])
        if longish:
            hit_sl = lo <= sl_price
            hit_tp = hi >= tp_price
        else:
            hit_sl = hi >= sl_price
            hit_tp = lo <= tp_price
        if hit_sl and hit_tp:
            return {"outcome": "SL", "gross": -sl, "ambiguous": True, "bars_held": i + 1}
        if hit_sl:
            return {"outcome": "SL", "gross": -sl, "ambiguous": False, "bars_held": i + 1}
        if hit_tp:
            return {"outcome": "TP", "gross": tp, "ambiguous": False, "bars_held": i + 1}

    # Time-exit at last close.
    last_close = float(bars[-1]["close"])
    gross = (last_close / entry - 1.0) if longish else (entry / last_close - 1.0) if last_close else 0.0
    # SHORT time-exit gross expressed as fraction of entry, sign = favorable if price fell.
    if not longish:
        gross = (entry - last_close) / entry
    return {"outcome": "TIME", "gross": gross, "ambiguous": False, "bars_held": len(bars)}


def pf_wr(net_returns: list) -> tuple[float, float, int]:
    """Profit factor, win-rate, n from a list of net fractional returns."""
    n = len(net_returns)
    if n == 0:
        return 0.0, 0.0, 0
    gains = sum(r for r in net_returns if r > 0)
    losses = -sum(r for r in net_returns if r < 0)
    wins = sum(1 for r in net_returns if r > 0)
    pf = (gains / losses) if losses > 0 else (float("inf") if gains > 0 else 0.0)
    return pf, wins / n, n


def _pct(x: float) -> str:
    return f"{x * 100:+.2f}%"


def _quantiles(vals: list, qs=(0.25, 0.5, 0.75, 0.9)) -> dict:
    if not vals:
        return {q: 0.0 for q in qs}
    s = sorted(vals)
    out = {}
    for q in qs:
        idx = min(len(s) - 1, int(q * (len(s) - 1) + 0.5))
        out[q] = s[idx]
    return out


# --------------------------------------------------------------------------- #
# DB layer
# --------------------------------------------------------------------------- #
def load_cohort(cur, categories, horizon_bars, entry_tol, min_bars, max_hold_days,
                include_banned):
    """Return (usable_picks, stats). Each usable pick carries its replayed bar window."""
    cat_ph = ",".join(["%s"] * len(categories))
    cur.execute(
        f"""SELECT id, symbol, direction, source_system, entry_price, take_profit,
                   stop_loss, status, pnl_pct, created_at,
                   UNIX_TIMESTAMP(created_at)*1000 AS entry_ms
            FROM trading_picks
            WHERE category IN ({cat_ph})
              AND status IN ('TP_HIT','SL_HIT','LOST')
              AND entry_price>0 AND take_profit>0 AND stop_loss>0""",
        tuple(categories),
    )
    rows = cur.fetchall()
    max_ms = max_hold_days * 86400 * 1000 if max_hold_days else None

    usable = []
    stats = {"total": len(rows), "banned": 0, "stale_entry": 0, "few_bars": 0, "usable": 0}
    for p in rows:
        src = p["source_system"] or "?"
        if not include_banned and src in BANNED_SOURCES:
            stats["banned"] += 1
            continue
        cur.execute(
            "SELECT timestamp, high, low, close FROM stock_ohlcv "
            "WHERE symbol=%s AND timestamp>=%s ORDER BY timestamp ASC LIMIT %s",
            (p["symbol"], p["entry_ms"], horizon_bars),
        )
        bars = cur.fetchall()
        if max_ms:
            bars = [b for b in bars if b["timestamp"] - p["entry_ms"] <= max_ms]
        if len(bars) < min_bars:
            stats["few_bars"] += 1
            continue
        entry = float(p["entry_price"])
        first_close = float(bars[0]["close"])
        if entry <= 0 or abs(first_close / entry - 1.0) > entry_tol:
            stats["stale_entry"] += 1
            continue
        p["_bars"] = bars
        p["_tp_dist"] = abs(float(p["take_profit"]) / entry - 1.0)
        p["_sl_dist"] = abs(float(p["stop_loss"]) / entry - 1.0)
        usable.append(p)
    stats["usable"] = len(usable)
    return usable, stats


# --------------------------------------------------------------------------- #
# Stages
# --------------------------------------------------------------------------- #
def stage1_excursions(picks):
    mfes, maes = [], []
    by_dir = {"LONG": [], "SHORT": []}
    for p in picks:
        mfe, mae = excursions(float(p["entry_price"]), p["direction"], p["_bars"])
        mfes.append(mfe); maes.append(mae)
        d = "LONG" if str(p["direction"]).upper() in ("LONG", "BUY") else "SHORT"
        by_dir[d].append((mfe, mae))
    return {
        "n": len(picks),
        "mfe_q": _quantiles(mfes),
        "mae_q": _quantiles(maes),
        "by_dir": {d: {"n": len(v),
                       "mfe_med": _quantiles([m for m, _ in v]).get(0.5, 0.0),
                       "mae_med": _quantiles([a for _, a in v]).get(0.5, 0.0)}
                   for d, v in by_dir.items()},
    }


def stage2_original_tp(picks):
    reached = same = 0
    out_dist = {"TP": 0, "SL": 0, "TIME": 0}
    for p in picks:
        r = first_touch(float(p["entry_price"]), p["direction"], p["_bars"],
                        p["_tp_dist"], p["_sl_dist"])
        out_dist[r["outcome"]] += 1
        if r["outcome"] == "TP":
            reached += 1
        # cross-check vs recorded status
        rec = {"TP_HIT": "TP", "SL_HIT": "SL", "LOST": "TIME"}.get(p["status"])
        if rec == r["outcome"] or (rec == "TIME" and r["outcome"] == "SL"):
            same += 1
    n = len(picks)
    return {
        "n": n,
        "orig_tp_reached_pct": reached / n if n else 0.0,
        "replay_outcome_dist": out_dist,
        "replay_vs_recorded_agree_pct": same / n if n else 0.0,
    }


def stage3_grid(picks, tp_grid, sl_grid, cost_frac, split_q=0.5):
    """IS/OOS time-split grid. Fit best NET-PF cell on IS, report it OOS."""
    picks_sorted = sorted(picks, key=lambda p: p["created_at"])
    cut = int(len(picks_sorted) * split_q)
    is_picks, oos_picks = picks_sorted[:cut], picks_sorted[cut:]

    def sim(cohort, tp, sl):
        nets = []
        for p in cohort:
            r = first_touch(float(p["entry_price"]), p["direction"], p["_bars"], tp, sl)
            nets.append(r["gross"] - cost_frac)
        return pf_wr(nets)

    grid_rows = []
    for tp in tp_grid:
        for sl in sl_grid:
            pf_is, wr_is, n_is = sim(is_picks, tp, sl)
            grid_rows.append({"tp": tp, "sl": sl, "pf_is": pf_is, "wr_is": wr_is, "n_is": n_is})

    # Fit: best IS net-PF among cells with WR>=40% and finite PF.
    eligible = [g for g in grid_rows if g["n_is"] >= 10 and g["pf_is"] != float("inf")]
    eligible.sort(key=lambda g: -g["pf_is"])
    best = eligible[0] if eligible else (grid_rows[0] if grid_rows else None)

    oos = None
    if best:
        pf_oos, wr_oos, n_oos = sim(oos_picks, best["tp"], best["sl"])
        # full-sample for reference
        pf_full, wr_full, n_full = sim(picks_sorted, best["tp"], best["sl"])
        oos = {"tp": best["tp"], "sl": best["sl"],
               "pf_is": best["pf_is"], "wr_is": best["wr_is"], "n_is": best["n_is"],
               "pf_oos": pf_oos, "wr_oos": wr_oos, "n_oos": n_oos,
               "pf_full": pf_full, "wr_full": wr_full, "n_full": n_full,
               "money_ready_oos": pf_oos >= T2_PF and wr_oos >= T2_WR and n_oos >= 20}
    return {"n_is": len(is_picks), "n_oos": len(oos_picks), "grid": grid_rows, "best_oos": oos}


# --------------------------------------------------------------------------- #
# Self-test (no network)
# --------------------------------------------------------------------------- #
def _self_test() -> int:
    # LONG that rises 2% then continues: TP=1% should hit, SL=1% should not.
    bars = [{"high": 100.5, "low": 99.8, "close": 100.2},
            {"high": 101.2, "low": 100.1, "close": 101.0},
            {"high": 102.5, "low": 100.9, "close": 102.3}]
    r = first_touch(100.0, "LONG", bars, tp=0.01, sl=0.01)
    assert r["outcome"] == "TP" and abs(r["gross"] - 0.01) < 1e-9, r
    mfe, mae = excursions(100.0, "LONG", bars)
    assert abs(mfe - 0.025) < 1e-9 and abs(mae - 0.002) < 1e-9, (mfe, mae)
    # Straddle bar -> SL-first.
    straddle = [{"high": 103.0, "low": 97.0, "close": 100.0}]
    r2 = first_touch(100.0, "LONG", straddle, tp=0.02, sl=0.02)
    assert r2["outcome"] == "SL" and r2["ambiguous"], r2
    # SHORT favorable (price falls 2%): TP=1% hits.
    sbars = [{"high": 100.2, "low": 98.0, "close": 98.5}]
    r3 = first_touch(100.0, "SHORT", sbars, tp=0.01, sl=0.01)
    assert r3["outcome"] == "TP" and abs(r3["gross"] - 0.01) < 1e-9, r3
    # PF/WR.
    pf, wr, n = pf_wr([0.01, 0.01, -0.02, 0.01])
    assert n == 4 and abs(wr - 0.75) < 1e-9 and abs(pf - (0.03 / 0.02)) < 1e-9, (pf, wr, n)
    # Time-exit.
    flat = [{"high": 100.1, "low": 99.9, "close": 100.05}] * 3
    r4 = first_touch(100.0, "LONG", flat, tp=0.05, sl=0.05)
    assert r4["outcome"] == "TIME", r4
    print("[self-test] all assertions passed")
    return 0


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--category", nargs="+", default=["EQUITY", "ETF"])
    ap.add_argument("--horizon-bars", type=int, default=30,
                    help="Max hourly bars to replay from entry (default 30 ~= 4-5 trading days).")
    ap.add_argument("--max-hold-days", type=int, default=10)
    ap.add_argument("--min-bars", type=int, default=12)
    ap.add_argument("--entry-tol", type=float, default=0.03,
                    help="Skip picks whose entry_price is >this frac off the first OHLCV bar.")
    ap.add_argument("--cost-bps", type=float, default=8.0, help="Round-trip cost in bps (4bp/side).")
    ap.add_argument("--tp-grid", type=float, nargs="+",
                    default=[0.005, 0.0075, 0.01, 0.015, 0.02, 0.03])
    ap.add_argument("--sl-grid", type=float, nargs="+",
                    default=[0.005, 0.0075, 0.01, 0.015, 0.02, 0.03])
    ap.add_argument("--include-banned", action="store_true")
    ap.add_argument("--entry-next-bar", action="store_true",
                    help="Drop the entry/trigger bar from the replay window (fill at the NEXT bar). "
                         "REQUIRED for trigger-based signals (e.g. oversold/breakout) to avoid the "
                         "look-ahead of counting the trigger bar's own intrabar range as reachable. "
                         "For picks anchored to a stated entry_price this is optional/conservative.")
    ap.add_argument("--direction", choices=["LONG", "SHORT", "BOTH"], default="BOTH",
                    help="Restrict the cohort to one side (Stage-1 excursion asymmetry follow-up).")
    ap.add_argument("--source", nargs="+", default=None,
                    help="Restrict to one or more source_system values.")
    ap.add_argument("--json", type=str, default=None)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return _self_test()

    import pymysql
    from tools.db_env import get_stocks_creds

    conn = pymysql.connect(**get_stocks_creds(), cursorclass=pymysql.cursors.DictCursor)
    cur = conn.cursor()

    picks, cstats = load_cohort(cur, args.category, args.horizon_bars, args.entry_tol,
                                args.min_bars, args.max_hold_days, args.include_banned)
    conn.close()

    if args.entry_next_bar:
        # Fill at the next bar: drop bar[0] (the entry/trigger bar) so its own intrabar
        # range cannot be counted as reachable. Keep only picks that still have >=2 bars.
        kept = []
        for p in picks:
            if len(p["_bars"]) >= 2:
                p["_bars"] = p["_bars"][1:]
                kept.append(p)
        cstats["entry_next_bar"] = True
        cstats["dropped_for_next_bar"] = len(picks) - len(kept)
        picks = kept

    if args.direction != "BOTH":
        want_long = args.direction == "LONG"
        picks = [p for p in picks
                 if (str(p["direction"]).upper() in ("LONG", "BUY")) == want_long]
        cstats["direction_filter"] = args.direction
        cstats["usable_after_dir"] = len(picks)
    if args.source:
        srcset = set(args.source)
        picks = [p for p in picks if (p["source_system"] or "?") in srcset]
        cstats["source_filter"] = args.source
        cstats["usable_after_source"] = len(picks)

    cost_frac = args.cost_bps / 10000.0
    s1 = stage1_excursions(picks)
    s2 = stage2_original_tp(picks)
    s3 = stage3_grid(picks, args.tp_grid, args.sl_grid, cost_frac)

    # ---- report ----
    print(f"\n=== EQUITY/ETF REACHABILITY REPLAY  ({'+'.join(args.category)}) ===")
    print(f"cohort: total={cstats['total']} usable={cstats['usable']} "
          f"(banned={cstats['banned']} stale_entry={cstats['stale_entry']} few_bars={cstats['few_bars']}) "
          f"| horizon={args.horizon_bars} bars, cost={args.cost_bps}bp round-trip\n")

    print("── Stage 1: realized excursion (how far signals actually move) ──")
    mq, aq = s1["mfe_q"], s1["mae_q"]
    print(f"  MFE (max favorable): p25 {_pct(mq[0.25])}  median {_pct(mq[0.5])}  p75 {_pct(mq[0.75])}  p90 {_pct(mq[0.9])}")
    print(f"  MAE (max adverse):   p25 {_pct(aq[0.25])}  median {_pct(aq[0.5])}  p75 {_pct(aq[0.75])}  p90 {_pct(aq[0.9])}")
    for d, v in s1["by_dir"].items():
        if v["n"]:
            print(f"    {d:5s} n={v['n']:3d}  MFE_med {_pct(v['mfe_med'])}  MAE_med {_pct(v['mae_med'])}")

    print("\n── Stage 2: ORIGINAL tp/sl reachability (replay vs recorded) ──")
    print(f"  original TP reached within horizon: {s2['orig_tp_reached_pct']*100:.1f}%")
    print(f"  replay outcomes: {s2['replay_outcome_dist']}")
    print(f"  replay agrees with recorded status: {s2['replay_vs_recorded_agree_pct']*100:.1f}%")

    print("\n── Stage 3: TP/SL grid, IS/OOS time-split, NET of cost ──")
    print(f"  IS picks={s3['n_is']}  OOS picks={s3['n_oos']}")
    b = s3["best_oos"]
    if b:
        print(f"  best IS net-PF cell: TP {b['tp']*100:.2f}% / SL {b['sl']*100:.2f}%")
        print(f"    IS:   PF {b['pf_is']:.2f}  WR {b['wr_is']*100:.0f}%  n={b['n_is']}")
        print(f"    OOS:  PF {b['pf_oos']:.2f}  WR {b['wr_oos']*100:.0f}%  n={b['n_oos']}   <-- the honest number")
        print(f"    full: PF {b['pf_full']:.2f}  WR {b['wr_full']*100:.0f}%  n={b['n_full']}")
        print(f"  MONEY-READY (OOS net PF>={T2_PF}, WR>={T2_WR*100:.0f}%, n>=20): "
              f"{'YES ✅' if b['money_ready_oos'] else 'NO'}")
    else:
        print("  no eligible grid cell")

    if args.json:
        out = {"cohort": cstats, "params": vars(args),
               "stage1_excursions": s1, "stage2_original_tp": s2, "stage3_grid": s3}
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(out, indent=2, default=str))
        print(f"\n[json] wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
