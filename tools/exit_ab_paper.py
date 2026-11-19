"""tools/exit_ab_paper.py — E14: does a plain time exit beat our TP/SL geometry?

The ledger can say a cell loses money. It cannot say *why*, and the exit is the
usual suspect: a TP that fires early caps the winners, an SL that fires on noise
converts a drawdown into a realised loss. This tool answers one narrow,
falsifiable question on the same signals the book actually took:

    for each closed pick, what would a fixed-horizon time exit (no TP, no SL)
    have returned, versus what the current exit actually returned?

Rules that keep it honest:
  * same entry fill and the same direction as the pick — only the exit changes;
  * the counterfactual fill uses the last bar at or *before* the horizon, so no
    future information leaks in;
  * picks with no entry price, no bar at/before the horizon, or a degenerate
    zero-second hold are counted as `skipped[reason]`, never silently dropped;
  * the output is a paired per-pick delta with a CI, not a class average that
    hides the mix.

This is paper evidence. It places no orders and changes no ledger verdict.

Usage:
  python3 tools/exit_ab_paper.py --rows /tmp/rows.jsonl --json-out /tmp/exit_ab.json
  python3 tools/exit_ab_paper.py --rows rows.jsonl --horizons 1,3,7 --cost 0.10

Exit codes: 0 ok; 2 unusable input; 3 no reproducible pairs.
"""
from __future__ import annotations

import argparse
import bisect
import json
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

MODULE = Path(__file__).resolve()
ROOT = MODULE.parent.parent
if str(ROOT) not in sys.path:  # direct invocation: python tools/exit_ab_paper.py
    sys.path.insert(0, str(ROOT))

from alpha_engine.audit3_selection_alpha import (  # noqa: E402
    TABLE_FOR, TOLERANCE_MS, _close_at, load_bars, symbol_candidates,
)

# Round-trip cost assumption for the counterfactual leg. The actual leg's cost is
# already inside its recorded pnl, so subtracting the same constant from both
# would double count — only the counterfactual pays it.
DEFAULT_COST_PCT = 0.10
DEFAULT_HORIZONS = (1.0, 3.0, 7.0)

# Volatility-scaled horizon: hold until the instrument's own expected move reaches
# the target, so a quiet ETF and a 6%-a-day crypto get different clocks instead of
# the same fixed 3-day guess. Vol is measured only on bars BEFORE the entry.
VOL_TARGET_PCT = 3.0
RETURN_LOOKBACK_DAYS = 30.0
MIN_HOLD_DAYS = 0.25
MAX_HOLD_DAYS = 14.0


def _ms(iso: str) -> int | None:
    """ISO timestamp -> epoch ms. Naive stamps are read as UTC."""
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)  # payload stamps are UTC
    return int(dt.timestamp() * 1000)


def _close_before(series: list[tuple[int, float]], ts_ms: int) -> float | None:
    """Close of the last bar at or before ts — the fill you could actually get."""
    if not series:
        return None
    keys = [k for k, _ in series]
    i = bisect.bisect_right(keys, ts_ms) - 1
    if i < 0:
        return None
    return series[i][1]


def _sign(direction: str) -> int | None:
    d = str(direction or "").strip().upper()
    if d == "LONG":
        return 1
    if d == "SHORT":
        return -1
    return None


def time_exit_pnl(series: list[tuple[int, float]], entry_ms: int, horizon_days: float,
                  dir_sign: int, cost: float = DEFAULT_COST_PCT,
                  tol_ms: int = 3 * 3600_000) -> float | None:
    """Percent return of a no-TP/no-SL time exit, net of the counterfactual cost."""
    entry_px = _close_at(series, entry_ms, tol_ms)
    if entry_px is None or entry_px <= 0:
        return None
    target = entry_ms + int(horizon_days * 86400_000)
    px = _close_before(series, target)
    if px is None or px <= 0:
        return None
    return (px / entry_px - 1.0) * 100.0 * dir_sign - cost


def daily_vol_pct(series: list[tuple[int, float]], entry_ms: int,
                  keys: list[int] | None = None,
                  lookback_days: float = RETURN_LOOKBACK_DAYS) -> float | None:
    """Realised daily volatility (%) from bars strictly before the entry signal.

    Only pre-entry bars are used, so the sizing is knowable at decision time. The
    per-bar stdev is scaled by the square root of bars-per-day (inferred from the
    median bar spacing), which makes 1h crypto and daily equity comparable.
    """
    if not series:
        return None
    idx = keys if keys is not None else [k for k, _ in series]
    start = entry_ms - int(lookback_days * 86400_000)
    lo = bisect.bisect_left(idx, start)
    hi = bisect.bisect_left(idx, entry_ms)
    window = series[lo:hi]
    if len(window) < 8:
        return None
    rets = []
    for (_, c0), (_, c1) in zip(window, window[1:]):
        if c0 and c0 > 0 and c1:
            rets.append(c1 / c0 - 1.0)
    if len(rets) < 7:
        return None
    gaps = [k1 - k0 for (k0, _), (k1, _) in zip(window, window[1:]) if k1 > k0]
    if not gaps:
        return None
    med_gap = statistics.median(gaps)
    if med_gap <= 0:
        return None
    per_day = 86400_000 / med_gap
    vol = statistics.stdev(rets) * (per_day ** 0.5) * 100.0
    return vol if vol > 0 else None


def vol_scaled_days(vol_pct: float | None, target: float = VOL_TARGET_PCT,
                    lo: float = MIN_HOLD_DAYS, hi: float = MAX_HOLD_DAYS) -> float | None:
    """Hold horizon whose expected move equals `target`, clipped to a sane band."""
    if vol_pct is None or vol_pct <= 0:
        return None
    return max(lo, min(hi, target / vol_pct))


def _series_for(bars: dict[str, list[tuple[int, float]]], klass: str, symbol: str):
    for cand in symbol_candidates(symbol, klass):
        s = bars.get(f"{klass}:{cand}")
        if s:
            return s
    return None


def _ci(values: list[float]) -> dict:
    """Paired mean CI. Prefers the tribunal's bootstrap; falls back to normal."""
    if len(values) < 3:
        return {"lo": None, "hi": None, "method": "insufficient_n"}
    try:
        from alpha_engine.audit3_tribunal import bootstrap_mean_ci
        out = bootstrap_mean_ci(values)
        if isinstance(out, (tuple, list)) and len(out) == 2:
            return {"lo": round(float(out[0]), 4), "hi": round(float(out[1]), 4),
                    "method": "bootstrap_mean_ci"}
    except Exception:
        pass
    m = statistics.mean(values)
    se = statistics.stdev(values) / (len(values) ** 0.5)
    return {"lo": round(m - 1.96 * se, 4), "hi": round(m + 1.96 * se, 4),
            "method": "normal_approx"}


def _agg(deltas: list[float], alts: list[float], actuals: list[float]) -> dict:
    if not deltas:
        return {"n": 0, "mean_delta_pct": None, "mean_alt_pct": None,
                "mean_actual_pct": None, "ci": {"lo": None, "hi": None,
                                                "method": "insufficient_n"}}
    ci = _ci(deltas)
    return {"n": len(deltas),
            "mean_delta_pct": round(statistics.mean(deltas), 4),
            "mean_alt_pct": round(statistics.mean(alts), 4),
            "mean_actual_pct": round(statistics.mean(actuals), 4),
            "median_delta_pct": round(statistics.median(deltas), 4),
            "better_share": round(sum(1 for d in deltas if d > 0) / len(deltas), 4),
            "ci": ci}


def ab_report(rows: list[dict], bars: dict[str, list[tuple[int, float]]],
              horizons=DEFAULT_HORIZONS, cost: float = DEFAULT_COST_PCT,
              vol_target: float | None = VOL_TARGET_PCT) -> dict:
    """Paired comparison, per horizon, per class, and vol-scaled, on the same picks."""
    per_h: dict[float, dict[str, dict[str, list[float]]]] = {
        h: defaultdict(lambda: {"delta": [], "alt": [], "actual": []}) for h in horizons
    }
    vol_buckets: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: {"delta": [], "alt": [], "actual": []})
    vol_horizons: list[float] = []
    keys_cache: dict[int, list[int]] = {}
    skipped: dict[str, int] = defaultdict(int)
    usable_rows = 0

    for r in rows:
        klass = str(r.get("class") or "").strip().upper()
        symbol = str(r.get("symbol") or "")
        d = _sign(r.get("dir"))
        actual = r.get("pnl")
        entry_ms = _ms(r.get("entry_time") or "")
        closed_ms = _ms(r.get("closed_at") or "")
        if klass not in TABLE_FOR:
            skipped["class_without_price_table"] += 1
            continue
        if d is None or actual is None or entry_ms is None:
            skipped["missing_direction_pnl_or_entry"] += 1
            continue
        if closed_ms is not None and closed_ms - entry_ms <= 0:
            # Same-second entry/close: the recorded pnl is not a hold outcome.
            skipped["degenerate_zero_hold"] += 1
            continue
        series = _series_for(bars, klass, symbol)
        if not series:
            skipped["no_price_series"] += 1
            continue
        entry_px = _close_at(series, entry_ms, TOLERANCE_MS.get(klass, 5 * 86400_000))
        if entry_px is None:
            skipped["no_entry_bar"] += 1
            continue
        usable_rows += 1
        for h in horizons:
            alt = time_exit_pnl(series, entry_ms, h, d, cost=cost,
                                tol_ms=TOLERANCE_MS.get(klass, 5 * 86400_000))
            if alt is None:
                skipped[f"no_bar_within_{h:g}d"] += 1
                continue
            bucket = per_h[h][klass]
            bucket["delta"].append(alt - float(actual))
            bucket["alt"].append(alt)
            bucket["actual"].append(float(actual))
        if vol_target is not None:
            tol = TOLERANCE_MS.get(klass, 5 * 86400_000)
            keys = keys_cache.setdefault(id(series), [k for k, _ in series])
            vol = daily_vol_pct(series, entry_ms, keys=keys)
            if vol is None:
                skipped["no_pre_entry_bars"] += 1
                continue
            hd = vol_scaled_days(vol, vol_target)
            alt = time_exit_pnl(series, entry_ms, hd, d, cost=cost, tol_ms=tol)
            if alt is None:
                skipped["no_bar_within_vol_horizon"] += 1
                continue
            vol_horizons.append(hd)
            vb = vol_buckets[klass]
            vb["delta"].append(alt - float(actual))
            vb["alt"].append(alt)
            vb["actual"].append(float(actual))

    out = {"schema": "audit3.exit_ab_paper.v1", "mode": "paper",
           "generated_at": datetime.now().astimezone().isoformat(),
           "definition": ("delta = counterfactual time-exit return - actual recorded "
                          "return, same entry/direction; positive means the plain time "
                          "exit would have done better. Counterfactual pays "
                          f"{cost}% round-trip; the actual leg's cost is already in pnl."),
           "cost_pct": cost, "rows_in": len(rows), "rows_with_entry_bar": usable_rows,
           "skipped": dict(skipped), "horizons": []}

    for h in horizons:
        buckets = per_h[h]
        all_d = [x for b in buckets.values() for x in b["delta"]]
        all_a = [x for b in buckets.values() for x in b["alt"]]
        all_act = [x for b in buckets.values() for x in b["actual"]]
        out["horizons"].append({
            "horizon_days": h,
            "overall": _agg(all_d, all_a, all_act),
            "by_class": {k: _agg(v["delta"], v["alt"], v["actual"])
                         for k, v in sorted(buckets.items())},
        })

    if vol_target is not None:
        all_d = [x for b in vol_buckets.values() for x in b["delta"]]
        all_a = [x for b in vol_buckets.values() for x in b["alt"]]
        all_act = [x for b in vol_buckets.values() for x in b["actual"]]
        hs = sorted(vol_horizons)
        out["vol_scaled"] = {
            "vol_target_pct": vol_target,
            "lookback_days": RETURN_LOOKBACK_DAYS,
            "hold_band_days": [MIN_HOLD_DAYS, MAX_HOLD_DAYS],
            "overall": _agg(all_d, all_a, all_act),
            "by_class": {k: _agg(v["delta"], v["alt"], v["actual"])
                         for k, v in sorted(vol_buckets.items())},
            "horizon_days": ({"min": round(hs[0], 4), "p10": round(hs[len(hs) // 10], 4),
                              "median": round(statistics.median(hs), 4),
                              "p90": round(hs[9 * len(hs) // 10], 4),
                              "max": round(hs[-1], 4)} if hs else None),
        }
    else:
        out["vol_scaled"] = None
    return out


def _load_rows(path: str) -> list[dict]:
    text = Path(path).read_text(encoding="utf-8").strip()
    if not text:
        return []
    if text[0] == "[":
        return json.loads(text)
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", required=True,
                    help="selection-alpha rows jsonl (or a JSON array)")
    ap.add_argument("--horizons", default=",".join(f"{h:g}" for h in DEFAULT_HORIZONS))
    ap.add_argument("--cost", type=float, default=DEFAULT_COST_PCT)
    ap.add_argument("--vol-target", dest="vol_target", type=float, default=VOL_TARGET_PCT,
                    help="%% expected move per vol-scaled hold; 0 disables the arm")
    ap.add_argument("--out", help="human-readable text report")
    ap.add_argument("--json-out", dest="json_out")
    args = ap.parse_args(argv)

    rows = _load_rows(args.rows)
    if not rows:
        print("ERROR: empty rows file", file=sys.stderr)
        return 2
    try:
        horizons = tuple(float(x) for x in args.horizons.split(",") if x.strip())
    except ValueError:
        print("ERROR: --horizons must be comma-separated numbers", file=sys.stderr)
        return 2
    if not horizons:
        print("ERROR: no horizons", file=sys.stderr)
        return 2

    # load_bars keys off the payload's class field, so hand it what it expects.
    bars = load_bars([{"asset_class": r.get("class"), "symbol": r.get("symbol")}
                      for r in rows])
    res = ab_report(rows, bars, horizons, args.cost,
                    vol_target=args.vol_target or None)
    if not any(h["overall"]["n"] for h in res["horizons"]):
        print(json.dumps(res, indent=1))
        print("no reproducible pairs", file=sys.stderr)
        return 3

    lines = ["exit A/B (paper) — same entry, only the exit differs",
             f"rows in {res['rows_in']:,} | with entry bar {res['rows_with_entry_bar']:,}"
             f" | cost {args.cost}%", ""]
    for h in res["horizons"]:
        o = h["overall"]
        lines.append(f"-- {h['horizon_days']:g}d time exit: n={o['n']:,} "
                     f"delta={o['mean_delta_pct']:+.3f}%/pick "
                     f"CI=[{o['ci']['lo']}, {o['ci']['hi']}] "
                     f"| time={o['mean_alt_pct']:+.3f}% vs actual={o['mean_actual_pct']:+.3f}%"
                     f" | better on {o['better_share']*100:.0f}% of picks")
        for k, c in h["by_class"].items():
            if c["n"] >= 20:
                lines.append(f"     {k:<9} n={c['n']:<5} delta={c['mean_delta_pct']:+.3f}%  "
                             f"CI=[{c['ci']['lo']}, {c['ci']['hi']}]")
    v = res.get("vol_scaled")
    if v and v["overall"]["n"]:
        o = v["overall"]
        hd = v["horizon_days"] or {}
        lines.append(f"-- vol-scaled ({v['vol_target_pct']:g}% target): n={o['n']:,} "
                     f"delta={o['mean_delta_pct']:+.3f}%/pick "
                     f"CI=[{o['ci']['lo']}, {o['ci']['hi']}] "
                     f"| time={o['mean_alt_pct']:+.3f}% vs actual={o['mean_actual_pct']:+.3f}%"
                     f" | hold median={hd.get('median')}d p10={hd.get('p10')} p90={hd.get('p90')}")
        for k, c in v["by_class"].items():
            if c["n"] >= 20:
                lines.append(f"     {k:<9} n={c['n']:<5} delta={c['mean_delta_pct']:+.3f}%  "
                             f"CI=[{c['ci']['lo']}, {c['ci']['hi']}]")
    lines += ["", f"skipped: {json.dumps(res['skipped'], sort_keys=True)}"]
    text = "\n".join(lines)
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
