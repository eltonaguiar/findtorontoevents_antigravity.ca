#!/usr/bin/env python3
"""H-150 -- the pre-registered backtest, not the signal check.

tools/h150_ttm_gpa.py validated the SIGNAL (quarterly TTM GP/A reproduces the
audited 10-K GrossProfit for 91% of pairs). This file runs the PERFORMANCE test
frozen in reports/hypothesis_registry.json as H-150 on 2026-11-21:

  universe  SEC filers, seed 149; market cap $2B-$10B at formation
  signal    quarterly TTM GP/A from facts filed STRICTLY before formation
  book      top quintile (z >= 0.8416), equal weight, long only, no hedge
  entry     next session OPEN after the month-end close
  exit      first month-end >= 20 calendar days after entry, <= 60
  cost      20 bp round-trip fallback; 2x stress
  gate      edge_stability_harness UNMODIFIED + FF4 alpha t >= 2.0

Two numbers are produced on purpose.

  `harness`  the eff statistic over the whole in-band cross-section. That is the
             only shape edge_stability_harness can score: it needs winners AND
             losers carrying scores inside each window (>=15 of each).
  `book`     the long-only top-quintile portfolio the spec actually holds, with
             net IR against the FF4 benchmark and the intercept on those factors.

A book return with an unusable harness is a story about ~17 names a month, and
the report says exactly that rather than quoting the average.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import random
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "reports" / "h150_gpa_backtest_2026-11-22.json"

HOLD_MIN_DAYS, HOLD_MAX_DAYS = 20, 60
DEFAULT_SAMPLE = 2600          # the frozen data_sample_lock
MIN_FORWARD_N = 100
MIN_INFORMATION_RATIO = 0.5
MIN_FACTOR_ALPHA_T = 2.0
STRESS_COST_MULT = 2.0


def _load(name: str, filename: str):
    path = ROOT / "tools" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


H149 = _load("_h149_for_h150", "h149_midcap_gross_profitability.py")
TTM = _load("_ttm_for_h150", "h150_ttm_gpa.py")


def _download_field(tickers, start, end, field, chunk=80, retries=3):
    """Chunked OHLC field download. Same failure mode as H-149's close helper:
    one big call is throttled and loses every ticker at once."""
    import time

    import pandas as pd
    import yfinance as yf

    tickers = list(dict.fromkeys(tickers))
    frames = []
    for i in range(0, len(tickers), chunk):
        part = tickers[i:i + chunk]
        for attempt in range(1, retries + 1):
            try:
                raw = yf.download(part, start=start, end=end, interval="1d",
                                  progress=False, auto_adjust=True, threads=True,
                                  group_by="column")
            except Exception as exc:  # noqa: BLE001 - network layer varies
                print(f"  .. {field} chunk {i//chunk+1} attempt {attempt} raised "
                      f"{type(exc).__name__}", file=sys.stderr)
                raw = None
            df = None
            if raw is not None and not getattr(raw, "empty", True):
                if getattr(raw.columns, "nlevels", 1) > 1:
                    if field in set(raw.columns.get_level_values(0)):
                        df = raw[field]
                    elif field in set(raw.columns.get_level_values(1)):
                        df = raw.xs(field, axis=1, level=1)
                elif field in raw.columns:
                    df = raw[[field]]
                elif len(part) == 1 and raw.shape[1] == 1:
                    df = raw
            if df is not None and not df.empty:
                frames.append(df)
                print(f"  .. {field} {min(i + chunk, len(tickers))}/{len(tickers)} "
                      f"({df.shape[1]} tickers, chunk {i//chunk+1})", file=sys.stderr)
                break
            time.sleep(2 * attempt)
        else:
            print(f"  .. {field} chunk {i//chunk+1}: no data after {retries} tries",
                  file=sys.stderr)
        time.sleep(1.0)
    if not frames:
        return None
    out = pd.concat(frames, axis=1)
    return out.loc[:, ~out.columns.duplicated()].dropna(axis=1, how="all")


def _month_end_positions(idx) -> list[int]:
    """Position in the trading index of each month's last session."""
    import pandas as pd
    ser = pd.Series(range(len(idx)), index=idx)
    return [int(v) for v in ser.groupby([idx.year, idx.month]).max().tolist()]


def _exit_position(idx, entry_pos: int, month_ends: list[int]) -> int | None:
    """First month-end >= 20 calendar days after entry, and <= 60."""
    entry_day = idx[entry_pos]
    for m in month_ends:
        if m <= entry_pos:
            continue
        gap = (idx[m] - entry_day).days
        if gap < HOLD_MIN_DAYS:
            continue
        return m if gap <= HOLD_MAX_DAYS else None
    return None


def build(names, closes, opens, idx, month_ends, cost_bp, haircut_pct):
    """One record per in-band name per formation, plus the top-quintile book."""
    n_idx = len(idx)
    records: list[dict] = []
    book: list[dict] = []
    stats = {"formations": 0, "formations_used": 0, "skipped_sparse": 0,
             "skipped_no_exit": 0, "in_band_total": 0, "book_names_total": 0,
             "delisted": 0, "missing_open": 0}
    for i in month_ends:
        if i + 1 >= n_idx:
            continue
        stats["formations"] += 1
        asof = idx[i].strftime("%Y-%m-%d")
        rows = []
        for nm in names:
            got = TTM.ttm_gpa_at(nm["facts"], asof)
            if got is None:
                continue
            tk = nm["ticker"]
            if tk not in closes.columns or tk not in opens.columns:
                continue
            px = closes[tk].iloc[i]
            if not (px == px) or px <= 0:            # NaN-safe
                continue
            cap = got["shares"] * float(px)
            if not (H149.CAP_LO <= cap <= H149.CAP_HI):
                continue
            rows.append((got["gpa"], nm))
        if len(rows) < H149.MIN_IN_BAND:
            stats["skipped_sparse"] += 1
            continue
        entry_pos = i + 1
        exit_pos = _exit_position(idx, entry_pos, month_ends)
        if exit_pos is None:
            stats["skipped_no_exit"] += 1
            continue
        stats["formations_used"] += 1
        stats["in_band_total"] += len(rows)
        zs = H149._zscore([g for g, _ in rows])
        hold_days = exit_pos - entry_pos
        for (gpa, nm), z in zip(rows, zs):
            tk = nm["ticker"]
            p0 = opens[tk].iloc[entry_pos]
            if not (p0 == p0) or p0 <= 0:
                stats["missing_open"] += 1
                continue
            p1 = closes[tk].iloc[exit_pos]
            delisted = False
            if not (p1 == p1):
                traded = closes[tk].iloc[entry_pos + 1:exit_pos + 1].dropna()
                if traded.empty:
                    continue          # entered, never traded again: no exit price
                p1 = traded.iloc[-1]
                delisted = True
                stats["delisted"] += 1
            gross_pct = (float(p1) / float(p0) - 1.0) * 100.0
            if delisted:
                gross_pct += haircut_pct
            net_pct = gross_pct - cost_bp / 100.0
            in_book = z >= H149.TOP_QUINTILE_Z
            rec = {"ticker": tk, "entry_date": asof,
                   "resolved_at": idx[exit_pos].strftime("%Y-%m-%d"),
                   "status": "WON" if net_pct > 0 else "LOST",
                   "pnl_pct": net_pct, "gross_pct": gross_pct,
                   "gpa_score": z, "gpa_raw": gpa, "delisted": delisted,
                   "in_book": in_book, "hold_days": hold_days}
            records.append(rec)
            if in_book:
                book.append(rec)
        sel = [r for r in records if r["entry_date"] == asof and r["in_book"]]
        stats["book_names_total"] += len(sel)
        if len(sel) >= H149.MIN_BOOK_N:
            book.append({"_formation": asof, "n": len(sel)})
    # the book summary is built separately; drop the marker rows
    markers = [b for b in book if "_formation" in b]
    book = [b for b in book if "_formation" not in b]
    per_formation = []
    for mk in markers:
        sel = [r for r in book if r["entry_date"] == mk["_formation"]]
        uni = [r for r in records if r["entry_date"] == mk["_formation"]]
        if not sel:
            continue
        per_formation.append({
            "formation": mk["_formation"], "n_book": len(sel),
            "book_net_pct": round(sum(r["pnl_pct"] for r in sel) / len(sel), 4),
            "universe_net_pct": round(sum(r["pnl_pct"] for r in uni) / len(uni), 4),
            "hold_days": sel[0]["hold_days"],
            "resolved_at": sel[0]["resolved_at"],
        })
    stats["book_formation_rows"] = len(per_formation)
    return records, per_formation, stats


def _mean(xs):
    return round(sum(xs) / len(xs), 4) if xs else None


def _wr(xs):
    return round(100.0 * sum(1 for x in xs if x["pnl_pct"] > 0) / len(xs), 2) if xs else None


def book_summary(records, per_formation) -> dict:
    sel = [r for r in records if r["in_book"]]
    bot = [r for r in records if r["gpa_score"] <= -H149.TOP_QUINTILE_Z]
    return {
        "rule": f"long every in-band name with gpa_zscore >= {H149.TOP_QUINTILE_Z} "
                f"(top quintile), equal weight, no hedge",
        "n_book_records": len(sel),
        "book_net_mean_pct": _mean([r["pnl_pct"] for r in sel]),
        "book_wr_pct": _wr(sel),
        "universe_net_mean_pct": _mean([r["pnl_pct"] for r in records]),
        "n_bottom": len(bot),
        "bottom_net_mean_pct": _mean([r["pnl_pct"] for r in bot]),
        "long_short_net_pct": (round((_mean([r["pnl_pct"] for r in sel]) or 0.0)
                                     - (_mean([r["pnl_pct"] for r in bot]) or 0.0), 4)
                               if sel and bot else None),
        "formations": per_formation,
        "per_formation_mean_book_net_pct": _mean([f["book_net_pct"] for f in per_formation]),
    }


def factor_fit(per_formation: list[dict]) -> dict:
    """Net book return on [MKT, SMB, HML, RMW], overlapping and every-2nd.

    The factor month is the month AFTER formation (the month held), which is the
    same convention H-149 used, so the two numbers are comparable.
    """
    try:
        ff = H149._ff_monthly()
    except Exception as exc:  # noqa: BLE001 - network shape varies
        return {"available": False, "reason": f"{type(exc).__name__}: {exc}"}
    if not ff:
        return {"available": False, "reason": "FF5 file parsed to zero rows"}
    obs = []
    for f in per_formation:
        y, m = int(f["formation"][:4]), int(f["formation"][5:7]) + 1
        if m == 13:
            y, m = y + 1, 1
        key = f"{y}{m:02d}"
        fac = ff.get(key)
        if fac is None:
            continue
        monthly = (1.0 + f["book_net_pct"] / 100.0) ** (21.0 / max(f["hold_days"], 1)) - 1.0
        obs.append({"month": key, "y": monthly - fac["RF"], "book_n": f["n_book"],
                    **{c: fac[c] for c in H149.FACTOR_COLS}})
    overlapping = H149._ols(obs)
    if overlapping is None:
        return {"available": False,
                "reason": f"only {len(obs)} formations with factor data; 12 needed",
                "usable_formations": len(obs)}
    # 20-60 calendar days is ~1-2 months, so every 2nd formation limits overlap
    non_overlapping = H149._ols(obs[::2])
    # Information ratio as an APPRAISAL ratio, not the OLS residual mean.
    #
    # The previous version averaged the OLS residuals and divided by their sd.
    # Because the fit carries an intercept, that mean is exactly zero by
    # construction: the reported IR could only ever print -0.0, whatever the book
    # did. What the pre-registered benchmark asks for is the return the book earns
    # BEYOND its own factor exposure, relative to how noisy that is:
    #
    #     excess = alpha + epsilon        (y - beta'f, i.e. intercept included)
    #     IR     = mean(excess)/sd(excess) * sqrt(12) = alpha/sd(eps) * sqrt(12)
    #
    # Both an FF4 appraisal ratio and a model-free book-vs-universe IR are
    # reported; the gate uses the FF4 one, which is the declared benchmark.
    alpha_m = overlapping["alpha_pct_monthly"] / 100.0
    resid = []
    for r in obs:
        fitted = sum(overlapping["betas"][c] * r[c] for c in H149.FACTOR_COLS)
        resid.append(r["y"] - alpha_m - fitted)
    dof = max(len(resid) - 5, 1)              # 1 intercept + 4 factors
    sd_resid = (sum(x * x for x in resid) / dof) ** 0.5
    appraisal = (alpha_m / sd_resid * (12 ** 0.5)) if sd_resid > 0 else None

    diffs = [f["book_net_pct"] - f["universe_net_pct"] for f in per_formation]
    ir_universe = None
    if len(diffs) >= 3:
        m = sum(diffs) / len(diffs)
        v = sum((x - m) ** 2 for x in diffs) / (len(diffs) - 1)
        ir_universe = (m / (v ** 0.5) * (12 ** 0.5)) if v > 0 else None
    return {
        "available": True,
        "model": "r_book - RF = alpha + b*MKT + s*SMB + h*HML + r*RMW",
        "month_assignment": "factor month = month AFTER formation (the month held)",
        "return_conversion": "net formation return compounded to a monthly equivalent at "
                             "21/hold_days, where hold_days counts TRADING sessions",
        "overlapping": overlapping,
        "non_overlapping": non_overlapping,
        "appraisal_ratio_ff4": round(appraisal, 3) if appraisal is not None else None,
        "ir_vs_universe": round(ir_universe, 3) if ir_universe is not None else None,
        "tracking_error_monthly_pct": round(100.0 * sd_resid, 4),
        "ir_basis": ("appraisal ratio: monthly alpha divided by the sd of the FF4 residuals, "
                     "annualised by sqrt(12). The earlier version reported the mean of the OLS "
                     "residuals, which is zero by construction because the fit has an "
                     "intercept -- that number measured nothing and is not used as a gate."),
        "ir_vs_universe_basis": ("mean/sd of (book net - in-band universe net) per formation, "
                                 "annualised by sqrt(12); no factor model involved"),
        "overlap_note": ("formations overlap when a hold exceeds one month; the every-2nd fit "
                         "is the significance test, both are reported"),
    }


def verdict_of(harness: dict, book: dict, factors: dict, cost_bp: float) -> dict:
    ir = factors.get("appraisal_ratio_ff4")
    alpha_t = ((factors.get("overlapping") or {}).get("alpha_t")
               if factors.get("available") else None)
    gates = {
        "harness_admissible_positive": bool(harness.get("admissible")
                                            and harness.get("sign") == "+"),
        "min_forward_n": len(book["formations"]) >= 1 and book["n_book_records"] >= MIN_FORWARD_N,
        "appraisal_ratio_ge_0_5": (ir is not None and ir >= MIN_INFORMATION_RATIO),
        "factor_alpha_t": (alpha_t is not None and alpha_t >= MIN_FACTOR_ALPHA_T),
        "cost_survival": (harness.get("cost_survival") is not None
                          and harness["cost_survival"] >= H149.COST_SURVIVAL_MIN),
    }
    passed = all(gates.values())
    return {
        "gates": gates,
        "passed": passed,
        "verdict": "PROVEN_CANDIDATE" if passed else "NOT_PROVEN",
        "measured": {"appraisal_ratio_ff4": ir, "factor_alpha_t": alpha_t,
                     "n_book_records": book["n_book_records"],
                     "n_book_formations": len(book["formations"]),
                     "harness_sign": harness.get("sign"),
                     "cost_survival": harness.get("cost_survival")},
        "rule": ("every gate must pass: harness admissible and positive, >=100 forward "
                 "records, net IR >= 0.5 vs FF4, alpha t >= 2.0, cost survival >= 0.60. "
                 "Failing any one is NOT_PROVEN -- there is no partial credit and no "
                 "re-ranking of the book after seeing the result."),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sample-n", type=int, default=DEFAULT_SAMPLE,
                    help="CIKs attempted (frozen at 2600 for H-150)")
    ap.add_argument("--seed", type=int, default=149)
    ap.add_argument("--start", default="2016-01-01")
    ap.add_argument("--end", default="2025-12-31")
    ap.add_argument("--window-days", type=int, default=14)
    ap.add_argument("--self-check", action="store_true")
    ap.add_argument("--no-factors", action="store_true")
    ap.add_argument("--out", default=str(OUT_JSON))
    args = ap.parse_args()

    H = H149.load_harness()
    chk = H149.harness_self_check(H)
    print(f"# harness observed={chk['observed']} unmodified={chk['unmodified']}",
          file=sys.stderr)
    if not chk["unmodified"]:
        print("FATAL: harness thresholds differ from the published values", file=sys.stderr)
        return 2
    if args.self_check:
        print(json.dumps({"harness": chk,
                          "hold_days": [HOLD_MIN_DAYS, HOLD_MAX_DAYS],
                          "sample_n": DEFAULT_SAMPLE,
                          "top_quintile_z": H149.TOP_QUINTILE_Z}, indent=2))
        return 0

    import pandas as pd

    pool = []
    tpath = ROOT / "tools" / "cache" / "sec_companyfacts" / "company_tickers.json"
    tickers = json.loads(tpath.read_text(encoding="utf-8"))
    for v in tickers.values():
        try:
            pool.append({"cik": int(v["cik_str"]), "ticker": str(v["ticker"]).upper()})
        except (KeyError, TypeError, ValueError):
            continue
    pool.sort(key=lambda d: d["cik"])
    random.Random(args.seed).shuffle(pool)
    sample = pool[: args.sample_n]
    print(f"# pool {len(pool)} filers; attempting {len(sample)} (seed {args.seed})",
          file=sys.stderr)

    names = []
    for k, ent in enumerate(sample, 1):
        facts = TTM._load(ent["cik"])
        if facts and facts.get("quarters") and facts.get("assets") and facts.get("shares"):
            names.append({"ticker": ent["ticker"], "cik": ent["cik"], "facts": facts})
        if k % 50 == 0:
            print(f"  .. {k}/{len(sample)} fetched, {len(names)} with quarterly facts "
                  f"+ assets + shares", file=sys.stderr)
    names_no_price = len(names)
    print(f"# names with usable quarterly facts: {names_no_price}", file=sys.stderr)
    if not names:
        print("FATAL: no usable names -- DATA_GAP, nothing tested", file=sys.stderr)
        return 2

    tickers_list = [n["ticker"] for n in names]
    closes = H149._download_closes(tickers_list, args.start, args.end)
    opens = _download_field(tickers_list, args.start, args.end, "Open")
    if closes is None or closes.empty or opens is None or opens.empty:
        print("FATAL: price download failed", file=sys.stderr)
        return 2
    idx = closes.index
    opens = opens.reindex(idx)
    have = set(closes.columns) & set(opens.columns)
    names = [n for n in names if n["ticker"] in have]
    print(f"# names with both open and close history: {len(names)}", file=sys.stderr)

    cost_bp, cost_src = H149._round_trip_bp()
    print(f"# round-trip cost {cost_bp} bp ({cost_src})", file=sys.stderr)
    month_ends = _month_end_positions(idx)
    month_ends = [m for m in month_ends
                  if pd.Timestamp(args.start) <= idx[m] <= pd.Timestamp(args.end)]

    records, per_formation, stats = build(names, closes, opens, idx, month_ends,
                                          cost_bp, H149.DELIST_HAIRCUT_PCT)
    print(f"# records {len(records)} from {stats['formations_used']} formations "
          f"({stats['skipped_sparse']} sparse, {stats['skipped_no_exit']} no exit)",
          file=sys.stderr)
    if not records:
        print("FATAL: no records", file=sys.stderr)
        return 2

    harness = H149.evaluate(records, H, args.window_days)
    book = book_summary(records, per_formation)
    factors = ({"available": False, "reason": "--no-factors"}
               if args.no_factors else factor_fit(per_formation))

    # 2x cost stress: the same rule at double slippage
    rec2, pf2, _ = build(names, closes, opens, idx, month_ends,
                         cost_bp * STRESS_COST_MULT, H149.DELIST_HAIRCUT_PCT)
    stress = H149.evaluate(rec2, H, args.window_days)

    verdict = verdict_of(harness, book, factors, cost_bp)
    payload = {
        "hypothesis": "H-150 (quarterly TTM GP/A, next-open entry, 20-60 calendar-day exit)",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "module": "tools/h150_gpa_backtest.py",
        "signal_module": "tools/h150_ttm_gpa.py (validated 91.11% within 1% vs audited 10-K)",
        "harness": {"module": "tools/edge_stability_harness.py (imported unmodified)",
                    "self_check": chk, "result": harness},
        "spec": {"universe": f"SEC filers, seed {args.seed}, n={args.sample_n}, "
                             f"cap ${H149.CAP_LO:,.0f}-${H149.CAP_HI:,.0f}",
                 "signal": "quarterly TTM GP/A, facts filed STRICTLY before formation",
                 "book": f"top quintile z >= {H149.TOP_QUINTILE_Z}, equal weight, long only",
                 "entry": "next session OPEN after the month-end close",
                 "exit": f"first month-end >= {HOLD_MIN_DAYS} and <= {HOLD_MAX_DAYS} calendar days",
                 "cost_bp": cost_bp, "cost_source": cost_src,
                 "window_days": args.window_days,
                 "date_range": [args.start, args.end]},
        "universe": {"ciks_attempted": len(sample),
                     "names_with_quarterly_facts": names_no_price,
                     "names_with_prices": len(names),
                     "records": len(records),
                     "book_records": book["n_book_records"],
                     "stats": stats},
        "book": book,
        "factor_regression": factors,
        "cost_stress_2x": {"cost_bp": cost_bp * STRESS_COST_MULT,
                           "result": stress},
        "verdict": verdict,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print()
    print(f"harness: {harness['verdict']} — windows scored {harness['windows_scored']}, "
          f"strong {harness['windows_strong']} "
          f"({harness['strong_positive']}+ / {harness['strong_negative']}-), "
          f"sign {harness['sign']}, net {harness['net_edge_pct']}%")
    print(f"book:    n={book['n_book_records']} over {len(book['formations'])} formations, "
          f"net mean {book['book_net_mean_pct']}%, WR {book['book_wr_pct']}%, "
          f"L/S {book['long_short_net_pct']}%")
    if factors.get("available"):
        ov = factors["overlapping"]
        print(f"factors: alpha {ov['alpha_pct_monthly']}%/mo (t={ov['alpha_t']}), "
              f"R2 {ov['r_squared']}, appraisal {factors['appraisal_ratio_ff4']}")
    print(f"VERDICT: {verdict['verdict']} — gates {verdict['gates']}")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
