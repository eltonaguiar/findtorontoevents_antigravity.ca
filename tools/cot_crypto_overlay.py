#!/usr/bin/env python3
"""
A7 -- cross-asset COT -> CRYPTO sizing overlay (research / backtest harness).

HYPOTHESIS (DAILY_IDEAS_OLLAMA.MD O6 / kimi-k2.5)
-------------------------------------------------
When COMMODITY (and BOND) COT net-speculator positioning hits an extreme
rolling percentile (|z| > 2), scale CRYPTO position sizing INVERSELY -- a
variance-risk-premium overlay. The premise: extreme cross-asset speculative
crowding precedes broad risk-asset volatility, so de-risk CRYPTO sizing when
the COT z-score is stretched.

This is a SIZING OVERLAY, orthogonal to CRYPTO directional alpha. It is NOT a
new strategy and does NOT change which CRYPTO picks fire -- it only scales the
position weight of picks that already fired.

WHAT THIS FILE IS
-----------------
A research/backtest deliverable. It is NOT wired into production sizing.
Future caller (when/if OVERLAY-VIABLE): the CRYPTO branch of
`alpha_engine/backtest/position_sizing.py::PositionSizer.volatility_target_size`
would multiply its `target_weight` by `cot_size_scalar(pick_date)` -- gated
behind an opt-in flag exactly like the A3 `vol_scalar_cap` param. No wiring is
done here per the repo Wire-Up Rule (research/backtest deliverable).

DATA SOURCE INTERFACE
---------------------
The overlay needs a multi-week time-series of COMMODITY (and BOND) COT
net-speculator positioning to compute a rolling z-score. The repo's COT tooling
(`tools/cot_fetcher_socrata.py`, `alpha_engine/cot_positioning.py`) fetches COT
LIVE from the free CFTC Socrata feed (publicreporting.cftc.gov) -- it does NOT
persist a historical positioning *series*. The stored `cot_*.json` files are
SIGNAL snapshots / paper-pilot status, not a backtestable series.

`load_cot_series()` below implements a clean two-tier source:
  1. OFFLINE cache  : a JSON file of weekly net-spec %-of-OI rows, if present.
  2. LIVE fetch     : `tools/cot_fetcher_socrata.fetch_cot` (needs network;
                      CFTC_API_TOKEN/CFTC_API_KEY optional, raises higher cap).

If neither yields data, the harness reports INCONCLUSIVE-NO-DATA and does NOT
fabricate a series. An honest "harness ready, data blocked" is the correct
outcome when offline data is absent.

READ-ONLY: never writes to any input; never runs a generator.

Usage:
  python tools/cot_crypto_overlay.py                 # backtest, offline-first
  python tools/cot_crypto_overlay.py --allow-live     # permit live CFTC fetch
  python tools/cot_crypto_overlay.py --z-lookback 52  # rolling z window (weeks)
  python tools/cot_crypto_overlay.py --cot-cache PATH # explicit offline series

NFA -- research harness, no real-money sizing.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone

# --- repo root + imports ----------------------------------------------------
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(THIS_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

CLOSED_PICKS = os.path.join(REPO_ROOT, "alpha_engine", "data", "closed_picks.json")

# Default offline COT series cache. Shape (when present): a JSON list of
# {"report_date": "YYYY-MM-DD", "net_spec_pct_of_oi": float} rows, OR a dict
# {"COMMODITY": [...rows...], "BOND": [...rows...]}. Absent by default -> the
# harness falls back to live fetch (opt-in) or reports NO-DATA.
DEFAULT_COT_CACHE = os.path.join(
    REPO_ROOT, "audit_dashboard", "data", "cot_overlay_series.json"
)

# COMMODITY symbols whose noncomm (speculator) net positioning we average to
# form the cross-asset COMMODITY COT signal. Broad, liquid futures.
COMMODITY_COT_SYMBOLS = ["GC", "CL", "HG", "ZW", "ZC"]
# BOND COT proxy -- CFTC Legacy report market name fragment. Best-effort; if
# the live feed returns nothing for it the overlay degrades to COMMODITY-only.
BOND_COT_MARKET = "10-YEAR U.S. TREASURY"

Z_TRIGGER = 2.0          # |z| above this -> de-risk CRYPTO
SCALAR_FLOOR = 0.3       # most aggressive de-risk
SCALAR_CEIL = 1.0        # no overlay effect
DEFAULT_Z_LOOKBACK = 52  # rolling z window in weekly observations (~1 year)


# ===========================================================================
# data-source interface
# ===========================================================================
def load_cot_series(cache_path: str | None = None,
                     allow_live: bool = False,
                     z_lookback: int = DEFAULT_Z_LOOKBACK) -> dict:
    """
    Return a COT net-speculator series bundle:
        {"source": str,
         "available": bool,
         "COMMODITY": [{"report_date": str, "net_spec_pct_of_oi": float}, ...],
         "BOND": [...]   # may be empty
        }

    Tier 1: offline cache file (no network, deterministic, backtestable).
    Tier 2: live CFTC Socrata fetch (only if allow_live=True).
    Neither -> available=False (caller must report INCONCLUSIVE-NO-DATA).
    """
    cache_path = cache_path or DEFAULT_COT_CACHE

    # --- Tier 1: offline cache ---------------------------------------------
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            if isinstance(raw, list):
                bundle = {"COMMODITY": raw, "BOND": []}
            elif isinstance(raw, dict):
                bundle = {
                    "COMMODITY": raw.get("COMMODITY", []),
                    "BOND": raw.get("BOND", []),
                }
            else:
                bundle = {"COMMODITY": [], "BOND": []}
            if bundle["COMMODITY"]:
                bundle["source"] = f"offline-cache:{cache_path}"
                bundle["available"] = True
                return bundle
        except (OSError, json.JSONDecodeError, ValueError):
            pass  # fall through

    # --- Tier 2: live CFTC fetch -------------------------------------------
    if allow_live:
        try:
            from cot_fetcher_socrata import fetch_cot  # noqa: E402
        except ImportError:
            return {"COMMODITY": [], "BOND": [],
                    "source": "live-fetch-unavailable (import failed)",
                    "available": False}
        token = (os.environ.get("CFTC_API_TOKEN")
                 or os.environ.get("CFTC_API_KEY"))
        weeks = max(z_lookback + 16, 80)
        # average net_spec %-of-OI across commodity symbols per report_date
        per_date: dict[str, list[float]] = {}
        for sym in COMMODITY_COT_SYMBOLS:
            try:
                rows = fetch_cot(sym, weeks=weeks, app_token=token)
            except Exception:
                continue
            for r in rows:
                d = r.get("report_date")
                v = r.get("noncomm_net_pct_of_oi")
                if d and isinstance(v, (int, float)):
                    per_date.setdefault(d, []).append(float(v))
        commodity = [
            {"report_date": d,
             "net_spec_pct_of_oi": sum(vs) / len(vs)}
            for d, vs in sorted(per_date.items())
        ]
        if commodity:
            return {"COMMODITY": commodity, "BOND": [],
                    "source": "live-fetch:CFTC-Socrata-6dca-aqww",
                    "available": True}
        return {"COMMODITY": [], "BOND": [],
                "source": "live-fetch:no-rows-returned",
                "available": False}

    return {"COMMODITY": [], "BOND": [],
            "source": "no-offline-cache; live fetch not permitted "
                      "(pass --allow-live)",
            "available": False}


# ===========================================================================
# z-score + overlay scalar
# ===========================================================================
def _rolling_zscore_at(series: list[dict], as_of: str,
                       z_lookback: int) -> float | None:
    """
    Rolling z-score of the most-recent net_spec value at or before `as_of`,
    measured against the prior `z_lookback` weekly observations.

    `series` rows: {"report_date": "YYYY-MM-DD", "net_spec_pct_of_oi": float},
    chronological order not assumed (sorted here).
    """
    rows = sorted(
        (r for r in series
         if r.get("report_date") and isinstance(
             r.get("net_spec_pct_of_oi"), (int, float))),
        key=lambda r: r["report_date"],
    )
    visible = [r for r in rows if r["report_date"] <= as_of]
    if len(visible) < 8:  # need a minimum window for a meaningful z
        return None
    window = visible[-z_lookback:] if z_lookback > 0 else visible
    vals = [float(r["net_spec_pct_of_oi"]) for r in window]
    n = len(vals)
    mean = sum(vals) / n
    var = sum((x - mean) ** 2 for x in vals) / n
    if var <= 0:
        return None
    sd = math.sqrt(var)
    latest = vals[-1]
    return (latest - mean) / sd


def _scalar_from_z(z: float | None) -> float:
    """
    Map a COT z-score to a CRYPTO sizing scalar.

    |z| <= Z_TRIGGER  -> 1.0 (no effect; overlay is orthogonal/dormant)
    |z| >  Z_TRIGGER  -> de-risk linearly from 1.0 down to SCALAR_FLOOR,
                         reaching the floor at |z| = 4.0.
    Always clamped to [SCALAR_FLOOR, SCALAR_CEIL].
    """
    if z is None:
        return SCALAR_CEIL
    az = abs(z)
    if az <= Z_TRIGGER:
        return SCALAR_CEIL
    # linear de-risk over the band [Z_TRIGGER, 4.0]
    frac = min((az - Z_TRIGGER) / (4.0 - Z_TRIGGER), 1.0)
    scalar = SCALAR_CEIL - frac * (SCALAR_CEIL - SCALAR_FLOOR)
    return max(SCALAR_FLOOR, min(SCALAR_CEIL, scalar))


# module-level cache so the public API can stay a simple (date)->float call
_SERIES_CACHE: dict | None = None
_Z_LOOKBACK_CACHE: int = DEFAULT_Z_LOOKBACK


def cot_size_scalar(date: str,
                    z_lookback: int = DEFAULT_Z_LOOKBACK,
                    series: dict | None = None) -> float:
    """
    PUBLIC API. Return the CRYPTO sizing scalar in [0.3, 1.0] for a pick
    generated on `date` (ISO string or 'YYYY-MM-DD...').

    When |COT z| > 2 the scalar is < 1.0 (de-risk CRYPTO); else 1.0.

    If no COT series is available the scalar is 1.0 (overlay dormant,
    fail-safe -- never amplifies risk).

    `series` may be passed for a pure-function backtest; otherwise the
    module-level offline cache is used (loaded lazily, no live fetch in this
    code path).
    """
    global _SERIES_CACHE
    bundle = series
    if bundle is None:
        if _SERIES_CACHE is None:
            _SERIES_CACHE = load_cot_series(allow_live=False,
                                            z_lookback=z_lookback)
        bundle = _SERIES_CACHE
    if not bundle or not bundle.get("available"):
        return SCALAR_CEIL

    as_of = (date or "")[:10]
    if not as_of:
        return SCALAR_CEIL

    z_comm = _rolling_zscore_at(bundle.get("COMMODITY", []), as_of, z_lookback)
    z_bond = _rolling_zscore_at(bundle.get("BOND", []), as_of, z_lookback)

    # Use whichever asset's |z| is more extreme (most cautious read). The
    # overlay de-risks on EITHER commodity OR bond speculative crowding.
    candidates = [z for z in (z_comm, z_bond) if z is not None]
    if not candidates:
        return SCALAR_CEIL
    z = max(candidates, key=abs)
    return _scalar_from_z(z)


# ===========================================================================
# backtest harness  (cohort-replay pattern, mirrors tools/vol_scalar_backtest)
# ===========================================================================
def _pick_date(pick: dict) -> str | None:
    """Best-effort pick-generation date for COT z-score lookup."""
    for k in ("created_at", "opened_at", "entry_time", "generated_at"):
        v = pick.get(k)
        if isinstance(v, str) and len(v) >= 10:
            return v[:10]
    return None


def _sharpe(returns: list[float]) -> float:
    n = len(returns)
    if n < 2:
        return 0.0
    mean = sum(returns) / n
    var = sum((r - mean) ** 2 for r in returns) / (n - 1)
    sd = math.sqrt(var)
    return mean / sd if sd > 0 else 0.0


def _mdd(returns: list[float]) -> float:
    equity, peak, mdd = 1.0, 1.0, 0.0
    for r in returns:
        equity *= (1.0 + r)
        peak = max(peak, equity)
        if peak > 0:
            mdd = max(mdd, (peak - equity) / peak)
    return mdd


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    """Pearson correlation of two equal-length series."""
    n = len(xs)
    if n < 2 or n != len(ys):
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def run_backtest(z_lookback: int, allow_live: bool,
                 cot_cache: str | None) -> dict:
    """
    Replay CRYPTO closed picks with vs without the COT overlay scalar.

    Each pick's PLAIN return = pnl_pct * base_weight (base_weight constant, so
    the overlay's effect is isolated -- this is a sizing overlay test, not a
    directional test). OVERLAY return = pnl_pct * base_weight * cot_size_scalar.

    Returns a result dict with per-arm Sharpe/MDD/total and the orthogonality
    correlation rho, or a NO-DATA verdict.
    """
    with open(CLOSED_PICKS, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    crypto = [
        p for p in data
        if p.get("asset_class") == "CRYPTO"
        and isinstance(p.get("pnl_pct"), (int, float))
        and _pick_date(p) is not None
    ]
    crypto.sort(key=lambda p: _pick_date(p) or "")

    bundle = load_cot_series(cache_path=cot_cache, allow_live=allow_live,
                             z_lookback=z_lookback)

    result: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "z_lookback": z_lookback,
        "cohort": "CRYPTO closed picks",
        "n_crypto_picks": len(crypto),
        "cot_source": bundle.get("source"),
        "cot_available": bool(bundle.get("available")),
        "cot_commodity_rows": len(bundle.get("COMMODITY", [])),
        "cot_bond_rows": len(bundle.get("BOND", [])),
    }

    if not bundle.get("available"):
        result["verdict"] = "INCONCLUSIVE-NO-DATA"
        result["reason"] = (
            "No offline COT net-speculator time-series is stored in the repo, "
            "and live CFTC fetch was not permitted/available. The overlay "
            "module + this harness are READY; the backtest is data-blocked."
        )
        result["data_needed"] = {
            "what": "weekly COMMODITY (and BOND) COT noncomm net %-of-OI "
                    "series spanning the closed-picks window",
            "closed_picks_window": _picks_window(crypto),
            "offline_key": DEFAULT_COT_CACHE,
            "offline_shape": '[{"report_date":"YYYY-MM-DD",'
                             '"net_spec_pct_of_oi": <float>}, ...]  OR  '
                             '{"COMMODITY":[...],"BOND":[...]}',
            "fetch_step": (
                "python tools/cot_crypto_overlay.py --allow-live   "
                "(pulls CFTC Socrata 6dca-aqww via tools/cot_fetcher_socrata; "
                "set CFTC_API_TOKEN for the 50k/hr tier). Persist the returned "
                "series to the offline_key above for deterministic replay."
            ),
        }
        return result

    # --- both arms ---------------------------------------------------------
    base_weight = 0.05  # constant base sizing; overlay scales it
    plain_returns: list[float] = []
    overlay_returns: list[float] = []
    scalars: list[float] = []
    n_derisked = 0
    for p in crypto:
        d = _pick_date(p) or ""
        pnl = float(p["pnl_pct"])
        plain_r = base_weight * pnl
        scalar = cot_size_scalar(d, z_lookback=z_lookback, series=bundle)
        if scalar < SCALAR_CEIL - 1e-9:
            n_derisked += 1
        scalars.append(scalar)
        plain_returns.append(plain_r)
        overlay_returns.append(plain_r * scalar)

    plain_sharpe = _sharpe(plain_returns)
    overlay_sharpe = _sharpe(overlay_returns)
    rho = _pearson(overlay_returns, plain_returns)

    result.update({
        "verdict": None,  # filled below
        "n_picks_derisked": n_derisked,
        "pct_picks_derisked": round(100.0 * n_derisked / max(len(crypto), 1), 2),
        "avg_scalar": round(sum(scalars) / max(len(scalars), 1), 4),
        "plain": {
            "total_return_pct": round(sum(plain_returns) * 100, 4),
            "sharpe": round(plain_sharpe, 4),
            "mdd_pct": round(_mdd(plain_returns) * 100, 4),
        },
        "overlay": {
            "total_return_pct": round(sum(overlay_returns) * 100, 4),
            "sharpe": round(overlay_sharpe, 4),
            "mdd_pct": round(_mdd(overlay_returns) * 100, 4),
        },
        "sharpe_lift": round(overlay_sharpe - plain_sharpe, 4),
        "rho_orthogonality": round(rho, 4) if rho is not None else None,
    })

    sharpe_lift = result["sharpe_lift"]
    rho_val = result["rho_orthogonality"]
    if n_derisked == 0:
        result["verdict"] = "INCONCLUSIVE-NO-DATA"
        result["reason"] = (
            "COT series available but no pick fell in a |z|>2 window -- the "
            "overlay never bound. Need a series covering an extreme-positioning "
            "period within the closed-picks window."
        )
    elif sharpe_lift >= 0.15 and rho_val is not None and rho_val < 0.3:
        result["verdict"] = "OVERLAY-VIABLE"
    else:
        result["verdict"] = "NOT-VIABLE"
    return result


def _picks_window(picks: list[dict]) -> dict:
    dates = sorted(d for d in (_pick_date(p) for p in picks) if d)
    if not dates:
        return {"earliest": None, "latest": None}
    return {"earliest": dates[0], "latest": dates[-1]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--z-lookback", type=int, default=DEFAULT_Z_LOOKBACK,
                    help="rolling z-score window in weekly obs (default 52)")
    ap.add_argument("--allow-live", action="store_true",
                    help="permit live CFTC Socrata fetch when no offline cache")
    ap.add_argument("--cot-cache", default=None,
                    help="explicit offline COT series JSON path")
    ap.add_argument("--json", action="store_true",
                    help="emit the raw result dict as JSON")
    args = ap.parse_args()

    res = run_backtest(args.z_lookback, args.allow_live, args.cot_cache)

    if args.json:
        print(json.dumps(res, indent=2))
        return 0

    print("=" * 72)
    print("A7  --  cross-asset COT -> CRYPTO sizing overlay  (backtest harness)")
    print("=" * 72)
    print(f"closed picks file : {CLOSED_PICKS}")
    print(f"CRYPTO picks       : {res['n_crypto_picks']}")
    print(f"COT source         : {res['cot_source']}")
    print(f"COT rows           : COMMODITY={res['cot_commodity_rows']} "
          f"BOND={res['cot_bond_rows']}")
    print(f"z-lookback (weeks) : {res['z_lookback']}")
    print("-" * 72)

    if not res["cot_available"] or res["verdict"] == "INCONCLUSIVE-NO-DATA" \
            and "plain" not in res:
        print("VERDICT            : INCONCLUSIVE-NO-DATA")
        print(f"reason             : {res.get('reason', '')}")
        dn = res.get("data_needed")
        if dn:
            print("data needed        :")
            for k, v in dn.items():
                print(f"  - {k}: {v}")
        print("=" * 72)
        return 0

    pl, ov = res["plain"], res["overlay"]
    print(f"{'metric':<22}{'PLAIN':>16}{'OVERLAY':>16}{'delta':>16}")
    print(f"{'total return %':<22}{pl['total_return_pct']:>16}"
          f"{ov['total_return_pct']:>16}"
          f"{round(ov['total_return_pct']-pl['total_return_pct'],4):>16}")
    print(f"{'Sharpe (per-trade)':<22}{pl['sharpe']:>16}{ov['sharpe']:>16}"
          f"{res['sharpe_lift']:>+16}")
    print(f"{'max drawdown %':<22}{pl['mdd_pct']:>16}{ov['mdd_pct']:>16}"
          f"{round(ov['mdd_pct']-pl['mdd_pct'],4):>+16}")
    print("-" * 72)
    print(f"picks de-risked    : {res['n_picks_derisked']} "
          f"({res['pct_picks_derisked']}%)   avg scalar={res['avg_scalar']}")
    print(f"rho (orthogonality): {res['rho_orthogonality']}  "
          f"(bar: < 0.30)")
    print(f"Sharpe lift        : {res['sharpe_lift']:+}  (bar: >= +0.15)")
    print(f"VERDICT            : {res['verdict']}")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
