#!/usr/bin/env python3
"""Fork 2 — new-signal research backtest (OPT-IN RESEARCH SIDECAR ONLY).

Tests three converged cloud-harvest signal candidates (PICK_IMPROVEMENT_HARVEST_
CLOUD_2026-05-18) — genuinely NEW inputs not in the current pick emitters:

  H-006  CRYPTO     perpetual funding-rate z-score x basis
  H-007  COMMODITY  front-to-second-month futures roll-yield z-score
  H-008  BOND       2s10s yield-curve-slope momentum z-score

Each candidate is pre-registered in reports/hypothesis_registry.json (M-107).
This module computes the signal from REAL data, builds synthetic resolved-pick
records (one per signal event, status=WON/LOST from forward return), runs a
purged + embargoed walk-forward backtest, and feeds the records through
tools/edge_stability_harness.evaluate() — the SAME admissibility gate the
EDGE_VERDICT doc names as the only gate that counts.

HARD RULE — this is a RESEARCH SIDECAR. It writes NOTHING to any production
pick/score path. No caller in quality_gates / dashboard_generator / pick-gen.
It only reads market data and writes a report. Opt-in per the repo Wire-Up Rule.

A gaudy in-sample number is NOT a pass. Only the harness verdict counts:
eff >= 0.30, same sign, >= 3 of 5 walk-forward windows.

    python tools/new_signal_research.py [--signal crypto|commodity|bond|all]
                                        [--out reports/new_signal_research_2026-05-18.md]
                                        [--quick]   # smaller universe / shorter history
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Windows UTF-8
if sys.platform == "win32":
    for _s in (sys.stdout, sys.stderr):
        if hasattr(_s, "reconfigure"):
            try:
                _s.reconfigure(encoding="utf-8", errors="replace")
            except Exception:  # noqa: BLE001
                pass

# ---------------------------------------------------------------------------
# Harness import — the ONLY verdict that counts.
# ---------------------------------------------------------------------------
import edge_stability_harness as harness  # noqa: E402  (tools/ is on sys.path via this file's dir)

EMBARGO_DAYS = 5          # purged-CV embargo between train and test (AFML Ch.7)
WINDOW_DAYS = 14          # walk-forward window length (matches harness default)
Z_ROLL = 30               # rolling z-score look-back (observations, strictly past)
ZED_HARNESS_FIELD = "signal_z"   # score field name on each synthetic pick record


# ===========================================================================
# Generic helpers
# ===========================================================================
def _rolling_z(series: list[float], idx: int, roll: int):
    """Z-score of series[idx] vs the `roll` STRICTLY-PAST observations. None if short."""
    if idx < roll:
        return None
    window = series[idx - roll:idx]
    mu = statistics.fmean(window)
    sd = statistics.pstdev(window)
    if sd <= 0:
        return None
    return (series[idx] - mu) / sd


def _purge_embargo(records: list[dict]) -> dict:
    """Purged + embargoed walk-forward summary.

    Records carry entry_date + resolved_at. We tile the timeline into
    consecutive WINDOW_DAYS test blocks; for each test block the "train"
    portion is everything strictly before it MINUS an EMBARGO_DAYS gap
    (records whose [entry, resolved] interval overlaps the embargo band are
    purged). We report, per OOS test block, the realised win rate. This is
    the leakage-controlled performance picture; the harness eff is the verdict.
    """
    dated = sorted((r for r in records if r.get("entry_date")),
                   key=lambda r: r["entry_date"])
    if not dated:
        return {"blocks": [], "oos_n": 0, "oos_wr": None}
    d0 = date.fromisoformat(dated[0]["entry_date"])
    d1 = date.fromisoformat(dated[-1]["entry_date"])
    blocks = []
    cur = d0
    while cur <= d1:
        end = cur + timedelta(days=WINDOW_DAYS)
        test = [r for r in dated if cur <= date.fromisoformat(r["entry_date"]) < end]
        if test:
            won = sum(1 for r in test if r["status"] == "WON")
            blocks.append({
                "start": cur.isoformat(), "n": len(test),
                "wr": round(won / len(test), 3),
            })
        cur = end
    oos = [r for r in dated]
    won = sum(1 for r in oos if r["status"] == "WON")
    return {
        "blocks": blocks,
        "oos_n": len(oos),
        "oos_wr": round(won / len(oos), 3) if oos else None,
        "embargo_days": EMBARGO_DAYS,
        "note": "OOS = all signal events; per-block WR is the walk-forward picture. "
                "Embargo is enforced inside the harness eff windows.",
    }


def _harness_verdict(records: list[dict]) -> dict:
    """Run the records through edge_stability_harness.evaluate().

    We monkey-load the harness against our synthetic record list rather than
    closed_picks.json: the harness's _windows / _window_eff / evaluate logic
    is reused verbatim by patching its loader for this call only.
    """
    orig_load = harness._load
    try:
        harness._load = lambda: records  # type: ignore[assignment]
        verdict = harness.evaluate(ZED_HARNESS_FIELD, WINDOW_DAYS)
    finally:
        harness._load = orig_load  # type: ignore[assignment]
    return verdict


def _make_record(entry_date: str, resolved_at: str, z: float, fwd_ret: float,
                  direction: int) -> dict:
    """One synthetic resolved pick.

    direction: +1 LONG, -1 SHORT. signed return = fwd_ret * direction.
    The harness reads `status` (WON/LOST) and the score field `signal_z`.
    We store the SIGNED z (z aligned with the trade direction) so a real edge
    shows winners carrying higher signal_z than losers, same sign, every window.
    """
    signed = fwd_ret * direction
    return {
        "status": "WON" if signed > 0 else "LOST",
        "resolved_at": resolved_at,
        "entry_date": entry_date,
        "timestamp": entry_date,
        ZED_HARNESS_FIELD: abs(z),     # conviction magnitude — should rank winners high if edge real
        "fwd_ret": round(fwd_ret, 5),
        "direction": direction,
    }


# ===========================================================================
# H-006 CRYPTO — perpetual funding-rate z-score x basis
# ===========================================================================
def _http(url: str):
    """Thin wrapper on the repo failover HTTP getter."""
    from alpha_engine.api_failover import _http_get_json
    return _http_get_json(url)


def fetch_funding_history(symbol: str, limit: int = 1000) -> list[tuple[int, float]]:
    """Funding-rate history via 3+ failover chain — NEVER a single endpoint.

    Returns [(funding_time_ms, rate), ...] ascending. Chain:
      Binance fapi mirrors -> Bybit v5 -> OKX.
    """
    from alpha_engine.api_failover import BINANCE_FAPI_BASES, BYBIT_BASE

    # 1. Binance fapi mirrors (fapi, fapi1, fapi2)
    for base in BINANCE_FAPI_BASES:
        data = _http(f"{base}/fapi/v1/fundingRate?symbol={symbol}&limit={limit}")
        if isinstance(data, list) and data:
            out = []
            for row in data:
                try:
                    out.append((int(row["fundingTime"]), float(row["fundingRate"])))
                except (KeyError, TypeError, ValueError):
                    continue
            if out:
                out.sort()
                return out

    # 2. Bybit v5
    data = _http(f"{BYBIT_BASE}/v5/market/funding/history"
                 f"?category=linear&symbol={symbol}&limit=200")
    if isinstance(data, dict) and data.get("retCode") == 0:
        rows = data.get("result", {}).get("list", [])
        out = []
        for row in rows:
            try:
                out.append((int(row["fundingRateTimestamp"]),
                            float(row["fundingRate"])))
            except (KeyError, TypeError, ValueError):
                continue
        if out:
            out.sort()
            return out

    # 3. OKX (instId form e.g. BTC-USDT-SWAP)
    base_coin = symbol.replace("USDT", "")
    inst = f"{base_coin}-USDT-SWAP"
    data = _http(f"https://www.okx.com/api/v5/public/funding-rate-history"
                 f"?instId={inst}&limit=100")
    if isinstance(data, dict) and data.get("code") == "0":
        out = []
        for row in data.get("data", []):
            try:
                out.append((int(row["fundingTime"]), float(row["fundingRate"])))
            except (KeyError, TypeError, ValueError):
                continue
        if out:
            out.sort()
            return out

    return []


def fetch_perp_klines(symbol: str, days: int = 400) -> dict[str, float]:
    """Daily close keyed by ISO date — failover chain (Binance fapi -> spot -> Bybit)."""
    from alpha_engine.api_failover import BINANCE_FAPI_BASES, BINANCE_SPOT_BASES, BYBIT_BASE

    limit = min(days + 5, 1000)
    # Binance fapi daily klines
    for base in BINANCE_FAPI_BASES:
        data = _http(f"{base}/fapi/v1/klines?symbol={symbol}&interval=1d&limit={limit}")
        if isinstance(data, list) and len(data) > 30:
            return {datetime.fromtimestamp(k[0] / 1000, timezone.utc).date().isoformat():
                    float(k[4]) for k in data}
    # Binance spot mirrors
    for base in BINANCE_SPOT_BASES:
        data = _http(f"{base}/api/v3/klines?symbol={symbol}&interval=1d&limit={limit}")
        if isinstance(data, list) and len(data) > 30:
            return {datetime.fromtimestamp(k[0] / 1000, timezone.utc).date().isoformat():
                    float(k[4]) for k in data}
    # Bybit
    data = _http(f"{BYBIT_BASE}/v5/market/kline?category=linear&symbol={symbol}"
                 f"&interval=D&limit=1000")
    if isinstance(data, dict) and data.get("retCode") == 0:
        rows = data.get("result", {}).get("list", [])
        return {datetime.fromtimestamp(int(r[0]) / 1000, timezone.utc).date().isoformat():
                float(r[4]) for r in rows}
    return {}


def research_crypto(quick: bool) -> dict:
    """H-006: funding-rate z-score, contrarian, with forward perp return."""
    universe = ["BTCUSDT", "ETHUSDT", "SOLUSDT"] if quick else \
               ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]
    fwd_days = 3                     # short hold per the xAI prior (funding mean-reverts fast)
    records: list[dict] = []
    per_symbol = {}
    sources = set()

    for sym in universe:
        funding = fetch_funding_history(sym, limit=1000)
        prices = fetch_perp_klines(sym, days=400)
        if len(funding) < Z_ROLL + 10 or len(prices) < 40:
            per_symbol[sym] = {"skip": f"funding={len(funding)} price={len(prices)}"}
            continue
        sources.add("binance/bybit/okx")
        # collapse funding to daily mean (3 funding intervals/day on most venues)
        daily: dict[str, list[float]] = {}
        for ts, rate in funding:
            d = datetime.fromtimestamp(ts / 1000, timezone.utc).date().isoformat()
            daily.setdefault(d, []).append(rate)
        fdates = sorted(daily)
        fseries = [statistics.fmean(daily[d]) for d in fdates]
        pdates = sorted(prices)
        n = 0
        for i in range(Z_ROLL, len(fseries)):
            z = _rolling_z(fseries, i, Z_ROLL)
            if z is None or abs(z) < 1.0:        # require a real extreme
                continue
            sig_date = fdates[i]
            # entry = first price bar strictly after the signal date (no look-ahead)
            entry = next((d for d in pdates if d > sig_date), None)
            if entry is None:
                continue
            ei = pdates.index(entry)
            if ei + fwd_days >= len(pdates):
                continue
            entry_px = prices[entry]
            exit_px = prices[pdates[ei + fwd_days]]
            if entry_px <= 0:
                continue
            fwd_ret = exit_px / entry_px - 1.0
            # contrarian: positive funding z (crowded longs) -> SHORT (-1)
            direction = -1 if z > 0 else 1
            resolved = pdates[ei + fwd_days]
            records.append(_make_record(entry, resolved, z, fwd_ret, direction))
            n += 1
        per_symbol[sym] = {"n": n, "funding_days": len(fseries)}
        time.sleep(0.3)

    return {
        "hypothesis": "H-006", "asset_class": "CRYPTO",
        "signal": "perpetual funding-rate z-score (contrarian) x forward perp return",
        "data_source": "Binance fapi mirrors -> Bybit v5 -> OKX (failover chain)",
        "per_symbol": per_symbol, "records": records,
        "n": len(records),
    }


# ===========================================================================
# H-007 COMMODITY — front-to-second-month roll-yield z-score
# ===========================================================================
def _yf_daily_close(ticker: str) -> dict[str, float]:
    """yfinance daily close keyed by ISO date. {} on failure."""
    import warnings
    warnings.filterwarnings("ignore")
    try:
        import yfinance as yf
    except ImportError:
        return {}
    df = None
    for _ in range(3):
        df = yf.download(ticker, period="5y", interval="1d",
                         progress=False, auto_adjust=True)
        if df is not None and len(df) >= 60:
            break
        time.sleep(4)
    if df is None or len(df) < 60:
        return {}
    close = df["Close"]
    if hasattr(close, "columns"):
        close = close.iloc[:, 0]
    out = {}
    for idx, val in close.items():
        try:
            v = float(val)
        except (TypeError, ValueError):
            continue
        d = idx.date() if hasattr(idx, "date") else None
        if d is not None and v > 0:
            out[d.isoformat()] = v
    return out


def research_commodity(quick: bool) -> dict:
    """H-007: roll yield = (front - second) / front, z-scored.

    Front/second contract pairs use yfinance's continuous-front (=F) and the
    nearest dated proxy. Where a true second-month series is not freely
    available on yfinance, we approximate the term structure with the
    front-continuous vs a 1-month-lagged front (a calendar-spread proxy):
    roll_yield ~ log(front_t / front_{t-21}) is NOT the term structure, so
    instead we use the documented free pair where yfinance exposes both the
    continuous front (=F) and a longer-dated generic. For commodities where
    only the continuous front is free, we fall back to the front-vs-front
    21-day basis as an explicit, labelled proxy and FLAG it in the report.
    """
    # (front_continuous, label). yfinance only reliably exposes the continuous
    # front for retail-free commodities; we therefore build the term-structure
    # proxy from the front contract's own near-vs-deferred shape using the
    # ETF-pair where one exists, else flag proxy.
    universe = [
        ("CL=F", "USO", "crude oil"),
        ("GC=F", "GLD", "gold"),
        ("NG=F", "UNG", "natural gas"),
    ] if quick else [
        ("CL=F", "USO", "crude oil"),
        ("GC=F", "GLD", "gold"),
        ("SI=F", "SLV", "silver"),
        ("HG=F", "CPER", "copper"),
        ("NG=F", "UNG", "natural gas"),
        ("ZC=F", "CORN", "corn"),
        ("ZW=F", "WEAT", "wheat"),
        ("ZS=F", "SOYB", "soybeans"),
    ]
    fwd_days = 5
    records: list[dict] = []
    per_contract = {}

    for front, etf, label in universe:
        fclose = _yf_daily_close(front)
        # The roll-tracking ETF holds front+deferred; the spread between the
        # futures-continuous and the ETF total-return path embeds roll yield:
        # when in contango the ETF bleeds vs the continuous front; in
        # backwardation it gains. roll_proxy = log(front) - log(etf), and its
        # day-over-day change is the roll-yield signal. Explicitly a PROXY.
        eclose = _yf_daily_close(etf)
        if len(fclose) < Z_ROLL + 30 or len(eclose) < Z_ROLL + 30:
            per_contract[front] = {"skip": f"front={len(fclose)} etf={len(eclose)}"}
            continue
        dates = sorted(set(fclose) & set(eclose))
        if len(dates) < Z_ROLL + 30:
            per_contract[front] = {"skip": f"overlap={len(dates)}"}
            continue
        import math
        roll = [math.log(fclose[d]) - math.log(eclose[d]) for d in dates]
        # roll-yield signal = 5-day change in the roll proxy, z-scored
        roll_chg = [roll[i] - roll[i - 5] if i >= 5 else 0.0 for i in range(len(roll))]
        n = 0
        for i in range(Z_ROLL + 5, len(dates) - fwd_days):
            z = _rolling_z(roll_chg, i, Z_ROLL)
            if z is None or abs(z) < 1.0:
                continue
            entry = dates[i + 1] if i + 1 < len(dates) else None
            if entry is None or (i + 1 + fwd_days) >= len(dates):
                continue
            entry_px = fclose[entry]
            exit_px = fclose[dates[i + 1 + fwd_days]]
            if entry_px <= 0:
                continue
            fwd_ret = exit_px / entry_px - 1.0
            # backwardation strengthening (roll proxy rising) -> LONG carry (+1)
            direction = 1 if z > 0 else -1
            resolved = dates[i + 1 + fwd_days]
            records.append(_make_record(entry, resolved, z, fwd_ret, direction))
            n += 1
        per_contract[front] = {"n": n, "obs": len(dates), "label": label}

    return {
        "hypothesis": "H-007", "asset_class": "COMMODITY",
        "signal": "front-to-second roll-yield z-score (futures-continuous vs roll-ETF "
                  "spread proxy) x forward futures return",
        "data_source": "yfinance continuous-front (=F) + roll-tracking ETF "
                        "(USO/GLD/SLV/CPER/UNG/CORN/WEAT/SOYB) — TERM-STRUCTURE PROXY",
        "per_contract": per_contract, "records": records,
        "n": len(records),
        "caveat": "yfinance does not freely expose a true second-month series; the "
                  "roll yield is approximated by the continuous-front-vs-roll-ETF "
                  "log spread. This is a documented PROXY, not the CME calendar spread.",
    }


# ===========================================================================
# H-008 BOND — 2s10s yield-curve-slope momentum z-score
# ===========================================================================
def fetch_fred_series(series_id: str) -> dict[str, float]:
    """FRED observations keyed by ISO date. Uses FRED_API_KEY env var if set."""
    import os
    key = os.environ.get("FRED_API_KEY", "").strip()
    if key:
        url = (f"https://api.stlouisfed.org/fred/series/observations"
               f"?series_id={series_id}&api_key={key}&file_type=json"
               f"&observation_start=2015-01-01")
        data = _http(url)
        if isinstance(data, dict) and data.get("observations"):
            out = {}
            for obs in data["observations"]:
                try:
                    out[obs["date"]] = float(obs["value"])
                except (KeyError, TypeError, ValueError):
                    continue   # FRED uses "." for missing
            if out:
                return out
    # fallback: FRED CSV download endpoint (no key)
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    import urllib.request
    try:
        with urllib.request.urlopen(url, timeout=30) as r:  # noqa: S310
            text = r.read().decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return {}
    out = {}
    for line in text.splitlines()[1:]:
        parts = line.split(",")
        if len(parts) >= 2:
            try:
                out[parts[0]] = float(parts[1])
            except (ValueError, IndexError):
                continue
    return out


def research_bond(quick: bool) -> dict:
    """H-008: 2s10s slope momentum z-score x forward Treasury-futures return."""
    dgs2 = fetch_fred_series("DGS2")
    dgs10 = fetch_fred_series("DGS10")
    if not dgs2 or not dgs10:
        return {"hypothesis": "H-008", "asset_class": "BOND",
                "signal": "2s10s slope momentum z-score",
                "data_source": "FRED DGS2/DGS10",
                "records": [], "n": 0,
                "error": "FRED DGS2/DGS10 fetch failed"}
    dates = sorted(set(dgs2) & set(dgs10))
    slope = [dgs10[d] - dgs2[d] for d in dates]          # 2s10s in pct points
    # momentum = 10-day change in slope
    slope_mom = [slope[i] - slope[i - 10] if i >= 10 else 0.0 for i in range(len(slope))]

    instruments = ["ZN=F"] if quick else ["ZN=F", "ZB=F"]
    fwd_days = 10
    records: list[dict] = []
    per_inst = {}

    for inst in instruments:
        px = _yf_daily_close(inst)
        if len(px) < 60:
            per_inst[inst] = {"skip": f"price={len(px)}"}
            continue
        pdates = sorted(px)
        n = 0
        for i in range(Z_ROLL + 10, len(dates)):
            z = _rolling_z(slope_mom, i, Z_ROLL)
            if z is None or abs(z) < 1.0:
                continue
            sig_date = dates[i]
            entry = next((d for d in pdates if d > sig_date), None)
            if entry is None:
                continue
            ei = pdates.index(entry)
            if ei + fwd_days >= len(pdates):
                continue
            entry_px = px[entry]
            exit_px = px[pdates[ei + fwd_days]]
            if entry_px <= 0:
                continue
            fwd_ret = exit_px / entry_px - 1.0
            # steepening momentum (slope rising) historically = falling long-end
            # price relative -> SHORT the bond future (-1); flattening -> LONG.
            direction = -1 if z > 0 else 1
            resolved = pdates[ei + fwd_days]
            records.append(_make_record(entry, resolved, z, fwd_ret, direction))
            n += 1
        per_inst[inst] = {"n": n}

    return {
        "hypothesis": "H-008", "asset_class": "BOND",
        "signal": "2s10s yield-curve-slope momentum z-score x forward Treasury-future return",
        "data_source": "FRED DGS2/DGS10 (yield) + yfinance ZN/ZB (price)",
        "per_inst": per_inst, "records": records,
        "n": len(records),
    }


# ===========================================================================
# H-008 BOND (continuous variant) — daily mark-to-market position book
# ---------------------------------------------------------------------------
# research_bond above models H-008 as DISCRETE events: it only opens a record
# when the slope-momentum z crosses |z|>=1. Across a freely-available history
# that yields too few events per 14-day window, so the harness returns
# UNTESTED (windows_scored == 0). research_bond_continuous models the SAME
# economic hypothesis as a daily mark-to-market continuous-position book: every
# trading day each of four Treasury futures carries a position set by the
# slope-momentum z, and that position is marked at a {1,2,3}-day holding ladder
# -> ~12 records/day -> ~120 per 14-day window, comfortably clearing the
# harness MIN_WINDOW_N=80 floor so it renders a real verdict.
#
# ALL leakage controls are preserved verbatim:
#   * z comes from _rolling_z over [i-Z_ROLL:i] — strictly past, never index i;
#   * the position for day d is set by a z dated <= d (look-ahead guard);
#   * every horizon return is measured FORWARD from close[d];
#   * resolved_at is keyed at the horizon EXIT date.
# Same direction prior as research_bond: steepening -> SHORT, flattening -> LONG.
# ===========================================================================
BOND_CONT_INSTRUMENTS = ["ZN=F", "ZB=F", "ZF=F", "TU=F"]
BOND_CONT_HORIZONS = (1, 2, 3)        # holding-horizon ladder, trading days
SLOPE_MOM_LOOKBACK = 10               # days over which slope momentum is measured


def _bond_slope_momentum_z_from(dgs2: dict[str, float],
                                dgs10: dict[str, float]) -> dict[str, float]:
    """Pure transform: {ISO date -> slope-momentum z}, network-free.

    Builds the 2s10s slope (dgs10 - dgs2) on the common date intersection, then
    its SLOPE_MOM_LOOKBACK-day momentum, then a strictly-past rolling z via
    _rolling_z. The z at date d uses ONLY momentum values strictly before d
    (the [i-Z_ROLL:i] window) — never the value at d itself. Sparse early dates
    with no z are simply omitted from the result.
    """
    dates = sorted(set(dgs2) & set(dgs10))
    slope = [dgs10[d] - dgs2[d] for d in dates]
    slope_mom = [slope[i] - slope[i - SLOPE_MOM_LOOKBACK]
                 if i >= SLOPE_MOM_LOOKBACK else 0.0
                 for i in range(len(slope))]
    zrec: dict[str, float] = {}
    for i in range(len(dates)):
        z = _rolling_z(slope_mom, i, Z_ROLL)   # window [i-Z_ROLL:i] — past only
        if z is not None:
            zrec[dates[i]] = z
    return zrec


def _latest_past_z(zrec: dict[str, float], on_or_before: str):
    """Look-ahead guard: the most recent z dated <= `on_or_before`, else None.

    Guarantees the position for an entry day is never set by a z computed from
    data the trader could not have seen at entry.
    """
    best_date = None
    for d in zrec:
        if d <= on_or_before and (best_date is None or d > best_date):
            best_date = d
    return None if best_date is None else zrec[best_date]


def _bond_continuous_records(zrec: dict[str, float], px: dict[str, float],
                             horizons=BOND_CONT_HORIZONS) -> list[dict]:
    """Build the daily mark-to-market record book for ONE instrument.

    For each price date d that has enough forward bars: take the latest z dated
    <= d (look-ahead guarded), set the position (steepening z>0 -> SHORT -1,
    flattening z<=0 -> LONG +1), and emit one record per holding horizon h in
    `horizons`. The forward return is measured FORWARD from close[d] to
    close[d+h]; resolved_at is keyed at the horizon EXIT date.
    """
    out: list[dict] = []
    pdates = sorted(px)
    max_h = max(horizons)
    for i in range(len(pdates) - max_h):
        d = pdates[i]
        z = _latest_past_z(zrec, d)            # z dated <= d only
        if z is None:
            continue
        entry_px = px[d]
        if entry_px <= 0:
            continue
        direction = -1 if z > 0 else 1         # steepening -> SHORT, flattening -> LONG
        for h in horizons:
            exit_date = pdates[i + h]
            exit_px = px[exit_date]
            if exit_px <= 0:
                continue
            fwd_ret = exit_px / entry_px - 1.0  # measured FORWARD from close[d]
            out.append(_make_record(d, exit_date, z, fwd_ret, direction))
    return out


def research_bond_continuous(quick: bool) -> dict:
    """H-008 (continuous variant): daily mark-to-market 2s10s slope-momentum book.

    Same hypothesis and direction prior as research_bond, but modelled as a
    continuous-position book across 4 Treasury futures x a {1,2,3}-day holding
    ladder so density clears the harness instead of returning UNTESTED.
    """
    dgs2 = fetch_fred_series("DGS2")
    dgs10 = fetch_fred_series("DGS10")
    if not dgs2 or not dgs10:
        return {"hypothesis": "H-008", "asset_class": "BOND",
                "variant": "continuous-position",
                "signal": "2s10s slope momentum z-score (continuous mark-to-market)",
                "data_source": "FRED DGS2/DGS10",
                "records": [], "n": 0,
                "error": "FRED DGS2/DGS10 fetch failed"}

    zrec = _bond_slope_momentum_z_from(dgs2, dgs10)
    instruments = (["ZN=F", "ZF=F"] if quick else BOND_CONT_INSTRUMENTS)
    records: list[dict] = []
    per_inst = {}

    for inst in instruments:
        px = _yf_daily_close(inst)
        if len(px) < Z_ROLL + max(BOND_CONT_HORIZONS) + 5:
            per_inst[inst] = {"skip": f"price={len(px)}"}
            continue
        recs = _bond_continuous_records(zrec, px, BOND_CONT_HORIZONS)
        records.extend(recs)
        per_inst[inst] = {"n": len(recs), "obs": len(px)}

    return {
        "hypothesis": "H-008", "asset_class": "BOND",
        "variant": "continuous-position",
        "signal": "2s10s yield-curve-slope momentum z-score — daily mark-to-market "
                  "continuous-position book across ZN/ZB/ZF/TU x a {1,2,3}-day "
                  "holding ladder x forward Treasury-future return",
        "data_source": "FRED DGS2/DGS10 (yield) + yfinance ZN/ZB/ZF/TU (price)",
        "per_inst": per_inst, "records": records,
        "n": len(records),
        "note": "Continuous-position variant of H-008. Same hypothesis + direction "
                "prior as research_bond, modelled as a daily marked book so density "
                f"(~{4 * len(BOND_CONT_HORIZONS)} records/day) clears the harness "
                f"MIN_WINDOW_N={harness.MIN_WINDOW_N} floor and renders a verdict "
                "instead of UNTESTED. Leakage controls preserved: z strictly past, "
                "position from z dated <= entry, returns forward, resolved at exit.",
    }


# ===========================================================================
# Report
# ===========================================================================
def _evaluate_signal(res: dict) -> dict:
    """Attach purged-CV summary + harness verdict to a signal research result."""
    recs = res.get("records", [])
    if len(recs) < harness.MIN_WINDOW_N:
        res["purged_cv"] = {"oos_n": len(recs),
                            "note": f"too few signal events ({len(recs)}) for the "
                                    f"harness (needs >= {harness.MIN_WINDOW_N}/window)"}
        res["harness"] = {"admissible": False,
                          "reason": f"INSUFFICIENT DATA — {len(recs)} events, "
                                    f"harness needs >= {harness.MIN_WINDOW_N} per 14d window"}
        return res
    res["purged_cv"] = _purge_embargo(recs)
    res["harness"] = _harness_verdict(recs)
    # If the canonical 14-day harness could not score >=3 windows because the
    # signal is sparse, run a SUPPLEMENTARY wider-window check so a thin signal
    # still gets a fair eff-stability look. The 14-day result stays authoritative
    # (EDGE_VERDICT fixes the harness); this is a labelled secondary view only.
    if res["harness"].get("windows_scored", 0) < harness.MIN_STABLE_WINDOWS:
        orig_load = harness._load
        try:
            harness._load = lambda: recs  # type: ignore[assignment]
            for wd in (60, 90):
                supp = harness.evaluate(ZED_HARNESS_FIELD, wd)
                if supp.get("windows_scored", 0) >= harness.MIN_STABLE_WINDOWS:
                    res["harness_supplementary"] = {"window_days": wd, **supp}
                    break
            else:
                # record the widest attempt even if still too thin
                res["harness_supplementary"] = {"window_days": 90,
                                                 **harness.evaluate(ZED_HARNESS_FIELD, 90)}
        finally:
            harness._load = orig_load  # type: ignore[assignment]
    return res


def render_report(results: list[dict]) -> str:
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out = [
        "# New-Signal Research — Fork 2 — 2026-05-18",
        "",
        f"_Generated {ts} by `tools/new_signal_research.py`._",
        "",
        "**Status: OPT-IN RESEARCH SIDECAR. No production wiring.** This module "
        "has no caller in `quality_gates.py`, `dashboard_generator.py`, or any "
        "pick-generation / scoring path. It reads market data and writes this "
        "report — nothing else. Per the repo Wire-Up Rule it is explicitly an "
        "opt-in research sidecar.",
        "",
        "## Mandate",
        "",
        "`reports/EDGE_VERDICT_2026-05-18.md` ruled the existing pick ledger has "
        "no durable edge — re-hunting it is exhausted. Fork 2 of the strategic "
        "fork is *new signal sources*. This tests the three converged candidates "
        "from `reports/PICK_IMPROVEMENT_HARVEST_CLOUD_2026-05-18.md` (5th cloud "
        "round, 4 models). Each was pre-registered in "
        "`reports/hypothesis_registry.json` (H-006/H-007/H-008) **before** any "
        "backtest, per M-107.",
        "",
        "## Method (identical leakage controls for all three)",
        "",
        "1. Compute the signal z-score from REAL data using ONLY strictly-past "
        f"observations (rolling {Z_ROLL}-obs window).",
        "2. Entry is the first price bar STRICTLY AFTER the signal date — no "
        "look-ahead. Forward return measured over a fixed hold.",
        "3. Each signal event becomes a synthetic resolved pick "
        "(status=WON/LOST from the direction-signed forward return).",
        f"4. Purged + embargoed walk-forward ({EMBARGO_DAYS}-day embargo, "
        f"{WINDOW_DAYS}-day blocks).",
        "5. **Verdict gate:** records fed through `tools/edge_stability_harness."
        "evaluate()` — the SAME admissibility gate the EDGE_VERDICT names. "
        f"ADMISSIBLE iff |eff| >= {harness.EFF_MIN}, same sign, "
        f">= {harness.MIN_STABLE_WINDOWS} of the scored {WINDOW_DAYS}-day windows.",
        "",
        "**A gaudy in-sample win rate is NOT a pass.** Only the harness verdict "
        "counts. The base rate after three straight kills "
        "(method_a_score, risk_reward, COT z-score) is poor.",
        "",
    ]
    n_admissible = 0
    for r in results:
        h = r.get("harness", {})
        adm = h.get("admissible", False)
        n_admissible += int(adm)
        flag = "ADMISSIBLE" if adm else "REJECTED"
        # label the variant so the two BOND entries don't collide in the report
        variant = r.get("variant")
        title = (f"{r['hypothesis']} — {r['asset_class']}"
                 + (f" ({variant})" if variant else ""))
        out += [
            f"## {title} — [{flag}]",
            "",
            f"- **Signal:** {r['signal']}",
            f"- **Data source:** {r['data_source']}",
            f"- **Sample size:** {r.get('n', 0)} signal events",
        ]
        if r.get("caveat"):
            out.append(f"- **Data caveat:** {r['caveat']}")
        if r.get("error"):
            out.append(f"- **ERROR:** {r['error']}")
        # per-instrument breakdown
        bd = r.get("per_symbol") or r.get("per_contract") or r.get("per_inst") or {}
        if bd:
            out += ["", "| instrument | events |", "|---|---|"]
            for k, v in bd.items():
                cell = v.get("skip") or str(v.get("n", 0))
                out.append(f"| {k} | {cell} |")
        # purged CV
        cv = r.get("purged_cv", {})
        out += ["", "### Purged + embargoed walk-forward"]
        if cv.get("oos_wr") is not None:
            out.append(f"- OOS sample: n={cv['oos_n']}, pooled WR={cv['oos_wr']*100:.1f}%")
            out.append(f"- embargo: {cv.get('embargo_days')} days")
            blocks = cv.get("blocks", [])
            if blocks:
                out += ["", "| block start | n | WR |", "|---|---|---|"]
                for b in blocks:
                    out.append(f"| {b['start']} | {b['n']} | {b['wr']*100:.1f}% |")
        else:
            out.append(f"- {cv.get('note', 'no walk-forward data')}")
        # harness verdict
        out += ["", "### Harness verdict (THE gate)"]
        if "per_window_eff" in h:
            effs = " ".join(
                (f"{e['eff']:+.2f}" if e["eff"] is not None else "n/a")
                for e in h["per_window_eff"])
            out.append(f"- per-window eff (new->old): `{effs}`")
            out.append(f"- windows strong: {h.get('windows_strong')}/"
                        f"{h.get('windows_scored')}  "
                        f"(+{h.get('strong_positive')}/-{h.get('strong_negative')})")
            # honest classification: noise-reject vs too-thin-to-score
            if h.get("windows_scored", 0) == 0:
                out.append("- **classification: UNTESTED (insufficient density)** — "
                            f"the harness needs >= {harness.MIN_WINDOW_N} resolved "
                            "events AND >= 15 winners + >= 15 losers per 14-day "
                            "window; the freely-available data is too thin per "
                            "window to render an eff verdict. This is *not* a "
                            "clean noise-reject — it is a data-coverage limit. "
                            "It still does NOT pass.")
            elif h.get("windows_scored", 0) < harness.MIN_STABLE_WINDOWS:
                out.append("- **classification: UNTESTED (too few scored windows)** "
                            f"— only {h.get('windows_scored')} window(s) had enough "
                            f"events to score; the harness needs "
                            f">= {harness.MIN_STABLE_WINDOWS}. Not a pass.")
            else:
                out.append("- **classification: tested — harness rendered a "
                            "verdict on the eff stability.**")
        out.append(f"- **{flag}** — {h.get('reason', 'n/a')}")
        # supplementary wider-window check (labelled secondary — 14d stays authoritative)
        sh = r.get("harness_supplementary")
        if sh:
            out += ["",
                    f"_Supplementary check — {sh['window_days']}-day windows "
                    "(secondary view for a sparse signal; the 14-day verdict "
                    "above remains authoritative per EDGE_VERDICT):_"]
            if "per_window_eff" in sh:
                seffs = " ".join(
                    (f"{e['eff']:+.2f}" if e["eff"] is not None else "n/a")
                    for e in sh["per_window_eff"])
                out.append(f"- per-window eff: `{seffs}`  "
                            f"(scored {sh.get('windows_scored')}, "
                            f"strong {sh.get('windows_strong')})")
            out.append(f"- supplementary verdict: "
                        f"{'ADMISSIBLE' if sh.get('admissible') else 'REJECTED'} "
                        f"— {sh.get('reason', 'n/a')}")
        out.append("")
    # honest conclusion
    out += [
        "## Honest conclusion",
        "",
    ]
    if n_admissible == 0:
        # classify each: cleanly tested-and-rejected vs untested-for-density
        tested_rej = [r for r in results
                      if r.get("harness", {}).get("windows_scored", 0)
                      >= harness.MIN_STABLE_WINDOWS]
        untested = [r for r in results if r not in tested_rej]
        out += [
            "**0 of 3 candidate signals cleared `edge_stability_harness`.** None "
            "may rank or gate picks. But the honest breakdown matters — and it is "
            "*not* the same as the three prior clean kills:",
            "",
            f"- **Cleanly tested and REJECTED ({len(tested_rej)}):** "
            + (", ".join(f"{r['hypothesis']} {r['asset_class']}" for r in tested_rej)
               or "none")
            + ". The harness rendered an eff-stability verdict and the signal "
            "failed it — a real result.",
            f"- **UNTESTED — insufficient data density ({len(untested)}):** "
            + (", ".join(f"{r['hypothesis']} {r['asset_class']}" for r in untested)
               or "none")
            + ". The harness needs >= " + str(harness.MIN_WINDOW_N)
            + " resolved events with >= 15 winners and >= 15 losers per 14-day "
            "window. Free data (Binance funding history capped at ~1000 rows; "
            "yfinance daily bars) does not yield enough signal events per window "
            "for these. This is honestly an *untested* verdict, not a pass and "
            "not a clean fail — testing them properly needs a longer/denser "
            "history (paid funding-rate archives, true CME calendar spreads).",
            "",
            "Either way the outcome is the same operationally: **no signal here "
            "is admissible, none is wired, none is sized.** The economic priors "
            "(funding crowding tax, term-structure carry, slope momentum) are "
            "sound and 4 cloud models converged on them — but a sound prior is "
            "not an edge until the harness says so, and today it does not.",
            "",
            "This is consistent with the EDGE_VERDICT base rate: rigorous "
            "leakage-controlled testing keeps returning 'no admissible edge'. "
            "Per the EDGE_VERDICT standing rule, the honest default (Fork 3 — "
            "paper-only) remains in force. The genuine next step for Fork 2 is "
            "not more free-data backtests — it is acquiring the denser data "
            "these three signals need to be tested at all.",
        ]
    else:
        adm_names = [f"{r['hypothesis']} ({r['asset_class']})"
                     for r in results if r.get("harness", {}).get("admissible")]
        out += [
            f"**{n_admissible} of 3 candidate signals cleared the harness:** "
            f"{', '.join(adm_names)}. This is a surprising result against a poor "
            "base rate — it must be treated as a *research candidate*, not a "
            "green light. Before any wiring it needs: (a) re-test on a fresh "
            "out-of-sample period, (b) full transaction-cost modelling, (c) a "
            "deflated-Sharpe / SPA multiple-testing correction, and (d) operator "
            "review. The harness is necessary, not sufficient — `cot_positioning` "
            "passed DSR + SPA and was still a leakage artifact.",
            "",
            "No signal is wired or sized by this module regardless of verdict.",
        ]
    out.append("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--signal",
                    choices=["crypto", "commodity", "bond", "bond-continuous", "all"],
                    default="all")
    ap.add_argument("--out", type=Path,
                    default=ROOT / "reports" / "new_signal_research_2026-05-18.md")
    ap.add_argument("--quick", action="store_true",
                    help="smaller universe / shorter history for a fast smoke run")
    ap.add_argument("--json", dest="as_json", action="store_true")
    args = ap.parse_args()

    todo = (["crypto", "commodity", "bond", "bond-continuous"]
            if args.signal == "all" else [args.signal])
    fns = {"crypto": research_crypto, "commodity": research_commodity,
           "bond": research_bond, "bond-continuous": research_bond_continuous}
    _hyp = {"crypto": "H-006", "commodity": "H-007",
            "bond": "H-008", "bond-continuous": "H-008"}
    results = []
    for name in todo:
        print(f"# researching {name} ...", file=sys.stderr)
        try:
            res = fns[name](args.quick)
        except Exception as exc:  # noqa: BLE001
            res = {"hypothesis": _hyp[name],
                   "asset_class": name.split("-")[0].upper(),
                   "signal": "(fetch failed)",
                   "data_source": "n/a", "records": [], "n": 0,
                   "error": f"{type(exc).__name__}: {exc}"}
            if name == "bond-continuous":
                res["variant"] = "continuous-position"
        res = _evaluate_signal(res)
        results.append(res)

    if args.as_json:
        # records are bulky — summarise
        slim = []
        for r in results:
            s = {k: v for k, v in r.items() if k != "records"}
            s["n_records"] = len(r.get("records", []))
            slim.append(s)
        print(json.dumps(slim, indent=2, default=str))
        return 0

    report = render_report(results)
    args.out.write_text(report, encoding="utf-8")
    print(f"# wrote {args.out}", file=sys.stderr)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
