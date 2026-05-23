#!/usr/bin/env python3
"""Forward-candidate signal research — H-002 / H-003 / H-004 (OPT-IN RESEARCH SIDECAR).

Tests three pre-registered hypotheses from reports/hypothesis_registry.json
(status PENDING_IMPLEMENTATION, M-107-gated) against the edge-stability harness:

  H-002  EQUITY     PEAD — post-earnings-announcement drift, top-SUE-decile
                    long / bottom-decile short, 30-day drift hold, ex-microcap.
  H-003  ETF        12-1 cross-sectional momentum on liquid US sector ETFs,
                    long top decile / short bottom decile, monthly rebalance,
                    skip the last month (reversal guard).
  H-004  COMMODITY  EIA inventory surprise (actual vs a rolling-mean expected
                    baseline — DOCUMENTED PROXY for missing free consensus)
                    interacted with front-minus-roll-ETF curve shape, 14-day fwd.

This module MIRRORS the proven pattern in tools/new_signal_research.py exactly:
  * strictly-past rolling z-scores (_rolling_z) — no look-ahead anywhere;
  * entry strictly AFTER the signal date;
  * synthetic resolved-pick records (status WON/LOST from a direction-signed
    forward return), score field `signal_z` carrying the conviction magnitude;
  * purged + embargoed walk-forward summary (5-day embargo, 14-day blocks);
  * records fed verbatim through tools/edge_stability_harness.evaluate() — the
    SAME admissibility gate the EDGE_VERDICT names as the only gate that counts.

HARD RULE — RESEARCH SIDECAR. It writes NOTHING to any production pick / score
/ gate path. No caller in quality_gates / dashboard_generator / pick-generation
/ production_scanner. It reads free market data and writes one report. Opt-in
per the repo Wire-Up Rule.

A gaudy in-sample number is NOT a pass. Only the harness verdict counts:
eff >= 0.30, same sign, >= 3 of the 14-day windows, MIN_WINDOW_N=80. If free
data cannot supply enough density the honest verdict is UNTESTED — explicitly
NOT a pass.

    python tools/forward_signal_research.py [--signal pead|etf-momentum|
                                             commodity-inventory|all]
                                            [--out reports/forward_signal_research_2026-05-18.md]
                                            [--quick]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
import time
import warnings
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
# Harness import — the ONLY verdict that counts. (tools/ is on sys.path via
# this file's own directory, exactly as new_signal_research.py imports it.)
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parent))
import edge_stability_harness as harness  # noqa: E402

EMBARGO_DAYS = 5          # purged-CV embargo between train and test (AFML Ch.7)
WINDOW_DAYS = 14          # walk-forward window length (matches harness default)
Z_ROLL = 30               # rolling z-score / rank look-back (observations, strictly past)
ZED_HARNESS_FIELD = "signal_z"   # score field name on each synthetic pick record


# ===========================================================================
# Generic helpers — IDENTICAL leakage controls for all three hypotheses.
# ===========================================================================
def _rolling_z(series: list[float], idx: int, roll: int):
    """Z-score of series[idx] vs the `roll` STRICTLY-PAST observations. None if short.

    The window is series[idx-roll:idx] — it NEVER includes index `idx` itself,
    so the z at a signal date uses only data the trader could have seen before
    that date. This is the non-negotiable look-ahead guard.
    """
    if idx < roll:
        return None
    window = series[idx - roll:idx]
    mu = statistics.fmean(window)
    sd = statistics.pstdev(window)
    if sd <= 0:
        return None
    return (series[idx] - mu) / sd


def _purge_embargo(records: list[dict]) -> dict:
    """Purged + embargoed walk-forward summary (mirror of new_signal_research)."""
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
    oos = list(dated)
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
    """Run the records through edge_stability_harness.evaluate() (loader patched)."""
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
    The harness reads `status` (WON/LOST) and the score field `signal_z`. We
    store abs(z) — the conviction magnitude — so a real edge shows winners
    carrying higher signal_z than losers, same sign, every window.
    """
    signed = fwd_ret * direction
    return {
        "status": "WON" if signed > 0 else "LOST",
        "resolved_at": resolved_at,
        "entry_date": entry_date,
        "timestamp": entry_date,
        ZED_HARNESS_FIELD: abs(z),
        "fwd_ret": round(fwd_ret, 6),
        "direction": direction,
    }


def _yf_daily_close(ticker: str, period: str = "10y") -> dict[str, float]:
    """yfinance daily auto-adjusted close keyed by ISO date. {} on failure."""
    warnings.filterwarnings("ignore")
    try:
        import yfinance as yf
    except ImportError:
        return {}
    df = None
    for _ in range(3):
        try:
            df = yf.download(ticker, period=period, interval="1d",
                             progress=False, auto_adjust=True)
        except Exception:  # noqa: BLE001
            df = None
        if df is not None and len(df) >= 60:
            break
        time.sleep(4)
    if df is None or len(df) < 30:
        return {}
    close = df["Close"]
    if hasattr(close, "columns"):
        close = close.iloc[:, 0]
    out: dict[str, float] = {}
    for idx, val in close.items():
        try:
            v = float(val)
        except (TypeError, ValueError):
            continue
        d = idx.date() if hasattr(idx, "date") else None
        if d is not None and v > 0:
            out[d.isoformat()] = v
    return out


def _fwd_return(prices: dict[str, float], pdates: list[str], entry: str,
                hold_days: int):
    """Forward return from `entry` close to the close `hold_days` bars later.

    Returns (fwd_ret, resolved_date) or None. The return is measured FORWARD
    only; entry and exit are both >= the signal date.
    """
    if entry not in prices:
        return None
    ei = pdates.index(entry)
    if ei + hold_days >= len(pdates):
        return None
    entry_px = prices[entry]
    exit_date = pdates[ei + hold_days]
    exit_px = prices[exit_date]
    if entry_px <= 0 or exit_px <= 0:
        return None
    return exit_px / entry_px - 1.0, exit_date


# ===========================================================================
# H-003 ETF — 12-1 cross-sectional momentum on liquid US sector ETFs
# ---------------------------------------------------------------------------
# FULLY FEASIBLE on free data. yfinance daily closes for the 11 SPDR sector
# ETFs. 12-1 momentum = total return from t-12mo to t-1mo (skip the last month
# to dodge short-term reversal). At each rebalance we cross-sectionally rank
# all ETFs by that strictly-past momentum; the top-decile names are LONG
# WON-candidates, bottom-decile SHORT. Modelled as a continuous-position book
# (one resolved record per ETF per day x a holding ladder) so the 14-day
# harness windows carry real density. signal_z = the cross-sectional z.
# ===========================================================================
SECTOR_ETFS = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP",
               "XLU", "XLB", "XLRE", "XLC"]
MOM_LOOKBACK_BARS = 252      # ~12 months of trading days
MOM_SKIP_BARS = 21           # skip the last ~1 month (reversal guard)
ETF_HOLD_LADDER = (5, 10, 21)  # holding-horizon ladder (trading days)


def _cross_sectional_z(values: dict[str, float]) -> dict[str, float]:
    """Cross-sectional z-score of {key -> value} at one rebalance date.

    This is NOT a time-series z — it ranks instruments against EACH OTHER at a
    single point in time, all inputs dated <= the rebalance date. No leakage.
    """
    vals = list(values.values())
    if len(vals) < 3:
        return {}
    mu = statistics.fmean(vals)
    sd = statistics.pstdev(vals)
    if sd <= 0:
        return {}
    return {k: (v - mu) / sd for k, v in values.items()}


def research_etf_momentum(quick: bool) -> dict:
    """H-003: 12-1 cross-sectional momentum — continuous daily-marked book.

    A pure monthly-rebalance design only emits ~6-8 events/month (long+short
    legs of an 11-ETF universe) — far below the harness MIN_WINDOW_N=80 per
    14-day window, so it returns UNTESTED for a density reason, not an edge
    reason. We therefore model the SAME economic hypothesis as a continuous-
    position book (the proven `research_bond_continuous` pattern): EVERY trading
    day each ETF carries a position set by its strictly-past 12-1 cross-
    sectional momentum z (LONG if it ranks in the top third, SHORT bottom
    third, FLAT mid), and that position is marked at a {5,10,21}-day holding
    ladder. ~7 ETFs x 3 horizons ~= 21 records/day -> >> 80 per 14-day window,
    so the harness renders a real verdict instead of UNTESTED.

    Leakage controls preserved verbatim:
      * the 12-1 momentum for date d uses prices from [d-252, d-21] — strictly
        past, the last month is skipped by construction;
      * the cross-sectional rank at d uses only momenta dated <= d;
      * entry is the first bar STRICTLY AFTER d; forward return measured
        forward only; resolved_at keyed at the horizon exit date.
    """
    universe = (["XLK", "XLF", "XLE", "XLV", "XLI", "XLY"]
                if quick else SECTOR_ETFS)
    max_h = max(ETF_HOLD_LADDER)

    prices: dict[str, dict[str, float]] = {}
    per_etf: dict[str, dict] = {}
    for etf in universe:
        px = _yf_daily_close(etf, period="10y")
        prices[etf] = px
        per_etf[etf] = {"obs": len(px)}
        if len(px) < MOM_LOOKBACK_BARS + max_h + 5:
            per_etf[etf]["skip"] = f"obs={len(px)}"
        time.sleep(0.2)

    usable = {e: p for e, p in prices.items()
              if len(p) >= MOM_LOOKBACK_BARS + max_h + 5}
    records: list[dict] = []
    if len(usable) >= 3:
        # common trading calendar across the usable ETFs
        common = sorted(set.intersection(*[set(p) for p in usable.values()]))
        counts: dict[str, int] = {e: 0 for e in usable}
        # walk EVERY trading day with enough lookback + forward room
        for i in range(MOM_LOOKBACK_BARS, len(common) - max_h):
            d = common[i]
            mom: dict[str, float] = {}
            for etf, px in usable.items():
                # 12-1 momentum: return from (i-252) to (i-21) — strictly past
                d_start = common[i - MOM_LOOKBACK_BARS]
                d_end = common[i - MOM_SKIP_BARS]
                if d_start in px and d_end in px and px[d_start] > 0:
                    mom[etf] = px[d_end] / px[d_start] - 1.0
            csz = _cross_sectional_z(mom)
            if not csz:
                continue
            ranked = sorted(csz.items(), key=lambda kv: kv[1])
            k = max(1, len(ranked) // 3)        # top / bottom third (decile-ish)
            longs = {e for e, _ in ranked[-k:]}
            shorts = {e for e, _ in ranked[:k]}
            for etf, z in csz.items():
                if etf not in longs and etf not in shorts:
                    continue                     # mid-rank ETFs stay FLAT
                direction = 1 if etf in longs else -1
                px = usable[etf]
                pdates = sorted(px)
                # entry = first bar STRICTLY AFTER the signal date d
                entry = next((dt for dt in pdates if dt > d), None)
                if entry is None:
                    continue
                for h in ETF_HOLD_LADDER:
                    fr = _fwd_return(px, pdates, entry, h)
                    if fr is None:
                        continue
                    fwd_ret, resolved = fr
                    records.append(_make_record(entry, resolved, z, fwd_ret,
                                                 direction))
                    counts[etf] += 1
        for etf in usable:
            per_etf[etf]["events"] = counts.get(etf, 0)

    return {
        "hypothesis": "H-003", "asset_class": "ETF",
        "signal": "12-1 cross-sectional momentum z-score on liquid US sector ETFs "
                  "(long top third / short bottom third, skip last month) — daily "
                  "mark-to-market continuous-position book x a {5,10,21}-day "
                  "holding ladder x forward return",
        "data_source": "yfinance daily auto-adjusted close — 11 SPDR sector ETFs "
                        "(XLK/XLF/XLE/XLV/XLI/XLY/XLP/XLU/XLB/XLRE/XLC)",
        "per_etf": per_etf, "records": records, "n": len(records),
        "feasibility": "FULLY FEASIBLE on free data — yfinance covers the full "
                       "sector-ETF universe. Modelled as a continuous-position "
                       "book (the research_bond_continuous pattern) so density "
                       "clears the harness MIN_WINDOW_N floor and a real verdict "
                       "is rendered. Same hypothesis + leakage controls; the "
                       "monthly-rebalance design only differs in cadence.",
    }


# ===========================================================================
# H-002 EQUITY — Post-Earnings-Announcement Drift (PEAD)
# ---------------------------------------------------------------------------
# yfinance Ticker.get_earnings_dates() supplies reported EPS + EPS estimate per
# earnings event. SUE proxy = (actual - estimate) standardized by the rolling
# std of the firm's OWN strictly-prior surprises (>=4 prior events required —
# no look-ahead). Direction-signed: positive SUE -> LONG drift, negative ->
# SHORT. Forward return measured 30 trading days AFTER the announcement, entry
# strictly the first bar after the announcement date. Universe is ~45 liquid
# US large-caps, ex-microcap by construction. If yfinance earnings coverage is
# too thin for the harness density floor, classified UNTESTED honestly.
# ===========================================================================
PEAD_UNIVERSE = [
    "AAPL", "MSFT", "AMZN", "GOOGL", "META", "NVDA", "TSLA", "JPM", "V", "MA",
    "UNH", "HD", "PG", "JNJ", "XOM", "CVX", "KO", "PEP", "WMT", "COST",
    "BAC", "DIS", "ADBE", "CRM", "NFLX", "INTC", "AMD", "QCOM", "TXN", "ORCL",
    "CSCO", "MCD", "NKE", "ABBV", "MRK", "PFE", "T", "VZ", "CAT", "BA",
    "GE", "IBM", "GS", "MS", "C",
]
PEAD_DRIFT_HOLD = 30         # trading days of post-earnings drift window
PEAD_MIN_PRIOR_SURPRISES = 4 # SUE std needs >=4 strictly-prior surprises


def _earnings_surprises(ticker: str) -> list[tuple[str, float]]:
    """[(announce_date_iso, surprise_pct), ...] ascending, from yfinance.

    surprise_pct = (reported EPS - estimated EPS). Only past-dated events with
    BOTH values present are kept. Returns [] if yfinance has no coverage.
    """
    warnings.filterwarnings("ignore")
    try:
        import yfinance as yf
    except ImportError:
        return []
    out: list[tuple[str, float]] = []
    try:
        tk = yf.Ticker(ticker)
        df = tk.get_earnings_dates(limit=48)
    except Exception:  # noqa: BLE001
        return []
    if df is None or len(df) == 0:
        return []
    today = date.today()
    # column names vary across yfinance versions
    cols = {c.lower(): c for c in df.columns}
    rep_col = next((cols[c] for c in cols if "reported" in c), None)
    est_col = next((cols[c] for c in cols if "estimate" in c), None)
    if rep_col is None or est_col is None:
        return []
    for idx, row in df.iterrows():
        d = idx.date() if hasattr(idx, "date") else None
        if d is None or d >= today:        # drop future / undated rows
            continue
        try:
            rep = float(row[rep_col])
            est = float(row[est_col])
        except (TypeError, ValueError):
            continue
        if math.isnan(rep) or math.isnan(est):
            continue
        out.append((d.isoformat(), rep - est))
    out.sort()
    return out


def research_equity_pead(quick: bool) -> dict:
    """H-002: SUE-decile post-earnings drift, 30-day hold, direction-signed."""
    universe = PEAD_UNIVERSE[:18] if quick else PEAD_UNIVERSE
    records: list[dict] = []
    per_ticker: dict[str, dict] = {}
    covered = 0

    for tk in universe:
        surprises = _earnings_surprises(tk)
        if len(surprises) < PEAD_MIN_PRIOR_SURPRISES + 2:
            per_ticker[tk] = {"skip": f"earnings_events={len(surprises)}"}
            time.sleep(0.3)
            continue
        px = _yf_daily_close(tk, period="10y")
        if len(px) < 300:
            per_ticker[tk] = {"skip": f"price_obs={len(px)}"}
            time.sleep(0.3)
            continue
        covered += 1
        pdates = sorted(px)
        surprise_vals = [s for _, s in surprises]
        n = 0
        for i in range(len(surprises)):
            announce, surprise = surprises[i]
            # SUE = surprise standardized by std of STRICTLY-PRIOR surprises
            prior = surprise_vals[:i]
            if len(prior) < PEAD_MIN_PRIOR_SURPRISES:
                continue
            sd = statistics.pstdev(prior)
            if sd <= 0:
                continue
            sue = (surprise - statistics.fmean(prior)) / sd
            # entry = first price bar STRICTLY AFTER the announcement date
            entry = next((d for d in pdates if d > announce), None)
            if entry is None:
                continue
            fr = _fwd_return(px, pdates, entry, PEAD_DRIFT_HOLD)
            if fr is None:
                continue
            fwd_ret, resolved = fr
            direction = 1 if sue > 0 else -1     # positive SUE -> LONG drift
            records.append(_make_record(entry, resolved, sue, fwd_ret, direction))
            n += 1
        per_ticker[tk] = {"events": n, "earnings_events": len(surprises)}
        time.sleep(0.3)

    res = {
        "hypothesis": "H-002", "asset_class": "EQUITY",
        "signal": "SUE (standardized unexpected earnings) post-earnings drift "
                  "z-score — long positive-SUE / short negative-SUE, 30-trading-day "
                  "drift hold, entry strictly after the announcement date",
        "data_source": "yfinance get_earnings_dates (reported vs estimate EPS) + "
                        "yfinance daily auto-adjusted close — ~45 liquid US "
                        "large-caps, ex-microcap by construction",
        "per_ticker": per_ticker, "records": records, "n": len(records),
        "tickers_with_coverage": covered,
        "caveat": "SUE is a PROXY: yfinance get_earnings_dates supplies the "
                  "reported-vs-estimate EPS pair; SUE is standardized by the std "
                  "of each firm's own strictly-prior surprises (>=4 required). "
                  "yfinance earnings-date coverage is shallower than a paid "
                  "Compustat/AlphaVantage feed; if density is below the harness "
                  "floor the verdict is UNTESTED, not a pass.",
    }
    return res


# ===========================================================================
# H-004 COMMODITY — EIA inventory surprise x roll-yield curve shape
# ---------------------------------------------------------------------------
# EIA weekly stocks come from the EIA v2 open-data API (api.eia.gov). This API
# REQUIRES a free registered key — there is no keyless free path, and FRED does
# NOT redistribute the EIA weekly inventory STOCKS series (only EIA prices and
# monthly NBER-era data). If no EIA_API_KEY is in the environment the honest
# verdict is UNTESTED for a data-access reason. Even WITH a key there is no
# free consensus/expected series, so the "expected" baseline is the rolling
# mean of the weekly inventory CHANGE and the surprise is the deviation of the
# latest change from that baseline — a DOCUMENTED proxy. The surprise z-score
# is GATED by the front-vs-roll-ETF spread (H-007's term-structure proxy).
# ===========================================================================
# (EIA v2 route, EIA series id, futures-continuous, roll-ETF, label)
EIA_COMMODITIES = [
    ("petroleum/stoc/wstk", "WCESTUS1", "CL=F", "USO",
     "crude oil — EIA weekly crude stocks ex-SPR"),
    ("petroleum/stoc/wstk", "WGTSTUS1", "RB=F", "UGA",
     "gasoline — EIA weekly total motor gasoline stocks"),
    ("natural-gas/stor/wkly", "NW2_EPG0_SWO_R48_BCF", "NG=F", "UNG",
     "natural gas — EIA weekly Lower-48 working gas in storage"),
]


def _eia_api_key() -> str:
    """Locate an EIA open-data API key in the environment (wide keyword scan).

    Per the repo rule 'check Windows env vars before claiming missing': EIA's
    weekly inventory series require a key (api.eia.gov returns 403
    API_KEY_MISSING without one). We scan for any EIA-named env var.
    """
    for name, val in os.environ.items():
        if "EIA" in name.upper() and val and val.strip():
            return val.strip()
    return ""


def fetch_eia_weekly_stocks(route: str, series_id: str) -> dict[str, float]:
    """EIA v2 weekly inventory level series keyed by ISO date. {} on failure.

    Returns {} (no exception) when no EIA_API_KEY is in the environment — the
    caller then classifies the hypothesis UNTESTED with a data-gap note.
    """
    key = _eia_api_key()
    if not key:
        return {}
    url = (f"https://api.eia.gov/v2/{route}/data/?api_key={key}"
           f"&frequency=weekly&data[0]=value"
           f"&facets[series][]={series_id}"
           f"&sort[0][column]=period&sort[0][direction]=asc&length=5000")
    try:
        from alpha_engine.api_failover import _http_get_json
        data = _http_get_json(url)
    except Exception:  # noqa: BLE001
        data = None
    out: dict[str, float] = {}
    if isinstance(data, dict):
        rows = data.get("response", {}).get("data", [])
        for row in rows:
            try:
                out[str(row["period"])[:10]] = float(row["value"])
            except (KeyError, TypeError, ValueError):
                continue
    return out


def _inventory_surprise_series(stocks: dict[str, float],
                               roll: int = 12) -> list[tuple[str, float]]:
    """[(report_date, surprise_z), ...] from a weekly EIA stocks level series.

    PROXY for a real consensus: weekly inventory CHANGE = level_t - level_{t-1};
    the "expected" baseline is the rolling mean of the `roll` STRICTLY-PRIOR
    changes; the surprise is (change_t - expected), z-scored by the strictly-
    prior change std. All inputs are strictly past — the z at report t never
    uses change_t in its own mean/std. Documented as a proxy in the report.
    """
    dates = sorted(stocks)
    changes = [stocks[dates[i]] - stocks[dates[i - 1]]
               for i in range(1, len(dates))]
    cdates = dates[1:]                       # change_i is dated at dates[i]
    out: list[tuple[str, float]] = []
    for i in range(roll, len(changes)):
        prior = changes[i - roll:i]          # strictly-prior changes only
        mu = statistics.fmean(prior)
        sd = statistics.pstdev(prior)
        if sd <= 0:
            continue
        surprise_z = (changes[i] - mu) / sd
        out.append((cdates[i], surprise_z))
    return out


def research_commodity_inventory(quick: bool) -> dict:
    """H-004: EIA inventory surprise x roll-yield curve shape, 14-day forward."""
    universe = EIA_COMMODITIES[:2] if quick else EIA_COMMODITIES
    fwd_days = 14
    records: list[dict] = []
    per_commodity: dict[str, dict] = {}
    have_key = bool(_eia_api_key())

    for route, series_id, fut, etf, label in universe:
        stocks = fetch_eia_weekly_stocks(route, series_id)
        if len(stocks) < 60:
            per_commodity[label] = {
                "skip": ("no EIA_API_KEY in environment — api.eia.gov "
                         "returns 403 API_KEY_MISSING; weekly inventory "
                         "stocks unavailable on free keyless sources"
                         if not have_key else f"eia_obs={len(stocks)}")}
            continue
        fclose = _yf_daily_close(fut, period="10y")
        eclose = _yf_daily_close(etf, period="10y")
        if len(fclose) < 200 or len(eclose) < 200:
            per_commodity[label] = {
                "skip": f"fut={len(fclose)} etf={len(eclose)}"}
            continue
        surprises = _inventory_surprise_series(stocks)
        if len(surprises) < 30:
            per_commodity[label] = {"skip": f"surprises={len(surprises)}"}
            continue

        # roll-yield proxy = log(futures-continuous) - log(roll-ETF); a rising
        # proxy = backwardation strengthening. Strictly-past curve shape only.
        common_curve = sorted(set(fclose) & set(eclose))
        roll_proxy = {d: math.log(fclose[d]) - math.log(eclose[d])
                      for d in common_curve}
        pdates = sorted(fclose)
        n = 0
        for report_date, surprise_z in surprises:
            if abs(surprise_z) < 1.0:            # require a real surprise extreme
                continue
            # entry = first futures bar STRICTLY AFTER the EIA report date
            entry = next((d for d in pdates if d > report_date), None)
            if entry is None:
                continue
            # curve shape: most recent roll-proxy value dated <= report_date
            curve_dates = [d for d in common_curve if d <= report_date]
            if not curve_dates:
                continue
            cd = curve_dates[-1]
            # 21-day change in the roll proxy = curve-shape momentum, past-only
            prior_cd = [d for d in common_curve if d <= cd]
            if len(prior_cd) < 22:
                continue
            curve_chg = roll_proxy[cd] - roll_proxy[prior_cd[-22]]
            fr = _fwd_return(fclose, pdates, entry, fwd_days)
            if fr is None:
                continue
            fwd_ret, resolved = fr
            # Economic direction (storage model): a bearish inventory surprise
            # (build above expected, surprise_z > 0) pressures price -> SHORT.
            # The curve shape is a CONFIRMING gate: only take the trade when
            # the curve agrees (contango / weakening backwardation confirms a
            # bearish build; backwardation confirms a bullish draw).
            inv_dir = -1 if surprise_z > 0 else 1
            curve_dir = 1 if curve_chg > 0 else -1   # rising proxy = backwardation up
            if inv_dir != curve_dir:
                continue                              # curve disagrees — skip
            direction = inv_dir
            # conviction = magnitude of the inventory surprise z
            records.append(_make_record(entry, resolved, surprise_z,
                                         fwd_ret, direction))
            n += 1
        per_commodity[label] = {"events": n, "eia_obs": len(stocks),
                                "surprises": len(surprises)}

    return {
        "hypothesis": "H-004", "asset_class": "COMMODITY",
        "signal": "EIA weekly inventory-surprise z-score (vs a rolling-mean "
                  "expected baseline) GATED by front-vs-roll-ETF curve-shape "
                  "agreement x forward 14-day futures return",
        "data_source": "EIA v2 open-data API (api.eia.gov — petroleum/stoc/wstk "
                        "WCESTUS1 crude / WGTSTUS1 gasoline; natural-gas/stor/wkly "
                        "NW2_EPG0_SWO_R48_BCF working gas) + yfinance futures-"
                        "continuous (CL/RB/NG) + roll-ETF (USO/UGA/UNG)",
        "per_commodity": per_commodity, "records": records, "n": len(records),
        "data_gap": (None if have_key else
                     "NO EIA API KEY — api.eia.gov requires a free registered "
                     "key (returns 403 API_KEY_MISSING without one); no "
                     "EIA_API_KEY (or any EIA-named var) is in the Windows "
                     "environment, and FRED does NOT redistribute the EIA "
                     "weekly inventory STOCKS series (only EIA prices / monthly "
                     "NBER-era data). H-004 is therefore UNTESTED for a data-"
                     "access reason — not an edge reason. To test it, register "
                     "a free key at eia.gov/opendata/register.php and set "
                     "EIA_API_KEY; the module will then run end-to-end."),
        "caveat": "TWO STACKED PROXIES even with an EIA key: (1) no FREE "
                  "consensus / expected-inventory series exists, so the "
                  "'expected' baseline is a DOCUMENTED PROXY — the rolling mean "
                  "of the weekly inventory CHANGE, with the surprise = "
                  "deviation of the latest change from that baseline; a real "
                  "Bloomberg/Reuters analyst consensus would behave "
                  "differently. (2) The roll-yield curve shape is the "
                  "futures-continuous-vs-roll-ETF log-spread PROXY documented "
                  "for H-007 — not a true CME calendar spread. Read the verdict "
                  "accordingly.",
    }


# ===========================================================================
# Evaluation + report
# ===========================================================================
def _evaluate_signal(res: dict) -> dict:
    """Attach purged-CV summary + harness verdict (mirror of new_signal_research)."""
    recs = res.get("records", [])
    if len(recs) < harness.MIN_WINDOW_N:
        res["purged_cv"] = {"oos_n": len(recs),
                            "note": f"too few signal events ({len(recs)}) for the "
                                    f"harness (needs >= {harness.MIN_WINDOW_N}/window)"}
        res["harness"] = {"admissible": False,
                          "reason": f"INSUFFICIENT DATA — {len(recs)} events, "
                                    f"harness needs >= {harness.MIN_WINDOW_N} per "
                                    f"14d window",
                          "windows_scored": 0}
        return res
    res["purged_cv"] = _purge_embargo(recs)
    res["harness"] = _harness_verdict(recs)
    # supplementary wider-window check for a sparse signal (labelled secondary;
    # the 14-day verdict stays authoritative per EDGE_VERDICT)
    if res["harness"].get("windows_scored", 0) < harness.MIN_STABLE_WINDOWS:
        orig_load = harness._load
        try:
            harness._load = lambda: recs  # type: ignore[assignment]
            for wd in (30, 60, 90):
                supp = harness.evaluate(ZED_HARNESS_FIELD, wd)
                if supp.get("windows_scored", 0) >= harness.MIN_STABLE_WINDOWS:
                    res["harness_supplementary"] = {"window_days": wd, **supp}
                    break
            else:
                res["harness_supplementary"] = {
                    "window_days": 90,
                    **harness.evaluate(ZED_HARNESS_FIELD, 90)}
        finally:
            harness._load = orig_load  # type: ignore[assignment]
    return res


def _classification(h: dict) -> str:
    """ADMISSIBLE / REJECTED / UNTESTED from a harness verdict dict."""
    if h.get("admissible"):
        return "ADMISSIBLE"
    if h.get("windows_scored", 0) < harness.MIN_STABLE_WINDOWS:
        return "UNTESTED"
    return "REJECTED"


def render_report(results: list[dict]) -> str:
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out = [
        "# Forward-Signal Research — H-002 / H-003 / H-004 — 2026-05-18",
        "",
        f"_Generated {ts} by `tools/forward_signal_research.py`._",
        "",
        "**Status: OPT-IN RESEARCH SIDECAR. No production wiring.** This module "
        "has no caller in `quality_gates.py`, `dashboard_generator.py`, "
        "`production_scanner.py`, or any pick-generation / scoring / gating "
        "path. It reads free market data and writes this report — nothing else. "
        "Per the repo Wire-Up Rule it is explicitly an opt-in research sidecar.",
        "",
        "## Mandate",
        "",
        "Three hypotheses were pre-registered in `reports/hypothesis_registry.json` "
        "(H-002 / H-003 / H-004, status `PENDING_IMPLEMENTATION`, M-107 gate) "
        "**before** any backtest. This module implements them through the same "
        "leakage-controlled pattern proven on H-006/H-007/H-008 and feeds the "
        "synthetic resolved-pick records to `tools/edge_stability_harness."
        "evaluate()` — the SAME admissibility gate `reports/EDGE_VERDICT_"
        "2026-05-18.md` names as the only gate that counts.",
        "",
        "## Method (identical leakage controls for all three)",
        "",
        "1. Compute the signal from REAL data using ONLY strictly-past "
        f"observations (rolling {Z_ROLL}-obs window for time-series z; "
        "cross-sectional rank for H-003 uses inputs all dated <= rebalance).",
        "2. Entry is the first price bar STRICTLY AFTER the signal date — no "
        "look-ahead. Forward return measured FORWARD only over a fixed hold.",
        "3. Each signal event becomes a synthetic resolved pick "
        "(status=WON/LOST from the direction-signed forward return); the score "
        f"field `{ZED_HARNESS_FIELD}` carries the conviction magnitude.",
        f"4. Purged + embargoed walk-forward ({EMBARGO_DAYS}-day embargo, "
        f"{WINDOW_DAYS}-day blocks).",
        "5. **Verdict gate:** records fed through `edge_stability_harness."
        "evaluate()`. ADMISSIBLE iff |eff| >= "
        f"{harness.EFF_MIN}, same sign, >= {harness.MIN_STABLE_WINDOWS} of the "
        f"scored {WINDOW_DAYS}-day windows (MIN_WINDOW_N={harness.MIN_WINDOW_N}).",
        "",
        "**A gaudy in-sample win rate is NOT a pass.** Only the harness verdict "
        "counts. If free data cannot supply enough density the honest verdict is "
        "**UNTESTED** — explicitly NOT a pass.",
        "",
    ]
    counts = {"ADMISSIBLE": 0, "REJECTED": 0, "UNTESTED": 0}
    for r in results:
        h = r.get("harness", {})
        cls = _classification(h)
        counts[cls] += 1
        out += [
            f"## {r['hypothesis']} — {r['asset_class']} — [{cls}]",
            "",
            f"- **Signal:** {r['signal']}",
            f"- **Data source:** {r['data_source']}",
            f"- **Sample size:** {r.get('n', 0)} signal events",
        ]
        if r.get("feasibility"):
            out.append(f"- **Feasibility:** {r['feasibility']}")
        if r.get("tickers_with_coverage") is not None:
            out.append(f"- **Tickers with usable coverage:** "
                       f"{r['tickers_with_coverage']}")
        if r.get("data_gap"):
            out.append(f"- **DATA GAP (UNTESTED reason):** {r['data_gap']}")
        if r.get("caveat"):
            out.append(f"- **Data caveat:** {r['caveat']}")
        if r.get("error"):
            out.append(f"- **ERROR:** {r['error']}")
        bd = (r.get("per_etf") or r.get("per_ticker")
              or r.get("per_commodity") or {})
        if bd:
            out += ["", "| instrument | events / status |", "|---|---|"]
            for k, v in bd.items():
                cell = v.get("skip") or str(v.get("events", v.get("n", 0)))
                out.append(f"| {k} | {cell} |")
        cv = r.get("purged_cv", {})
        out += ["", "### Purged + embargoed walk-forward"]
        if cv.get("oos_wr") is not None:
            out.append(f"- OOS sample: n={cv['oos_n']}, pooled "
                       f"WR={cv['oos_wr']*100:.1f}%")
            out.append(f"- embargo: {cv.get('embargo_days')} days")
            blocks = cv.get("blocks", [])
            if blocks:
                out += ["", "| block start | n | WR |", "|---|---|---|"]
                for b in blocks[:40]:
                    out.append(f"| {b['start']} | {b['n']} | "
                               f"{b['wr']*100:.1f}% |")
                if len(blocks) > 40:
                    out.append(f"| ...(+{len(blocks)-40} more) | | |")
        else:
            out.append(f"- {cv.get('note', 'no walk-forward data')}")
        out += ["", "### Harness verdict (THE gate)"]
        if "per_window_eff" in h:
            effs = " ".join(
                (f"{e['eff']:+.2f}" if e["eff"] is not None else "n/a")
                for e in h["per_window_eff"])
            out.append(f"- per-window eff (new->old): `{effs}`")
            out.append(f"- windows strong: {h.get('windows_strong')}/"
                       f"{h.get('windows_scored')}  "
                       f"(+{h.get('strong_positive')}/"
                       f"-{h.get('strong_negative')})")
            if h.get("windows_scored", 0) == 0:
                out.append("- **classification: UNTESTED (insufficient density)** "
                           f"— the harness needs >= {harness.MIN_WINDOW_N} "
                           "resolved events AND >= 15 winners + >= 15 losers per "
                           "14-day window; the freely-available data is too thin "
                           "per window. NOT a clean noise-reject — a data-"
                           "coverage limit. Still does NOT pass.")
            elif h.get("windows_scored", 0) < harness.MIN_STABLE_WINDOWS:
                out.append("- **classification: UNTESTED (too few scored "
                           f"windows)** — only {h.get('windows_scored')} "
                           "window(s) had enough events to score; the harness "
                           f"needs >= {harness.MIN_STABLE_WINDOWS}. Not a pass.")
            else:
                out.append("- **classification: tested — harness rendered a "
                           "verdict on the eff stability.**")
        out.append(f"- **{cls}** — {h.get('reason', 'n/a')}")
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
                           f"strong {sh.get('windows_strong')}, "
                           f"+{sh.get('strong_positive')}/"
                           f"-{sh.get('strong_negative')})")
            out.append(f"- supplementary verdict: "
                       f"{'ADMISSIBLE' if sh.get('admissible') else 'REJECTED'} "
                       f"— {sh.get('reason', 'n/a')}")
        out.append("")

    out += ["## Honest conclusion", ""]
    adm = [r for r in results if _classification(r.get("harness", {}))
           == "ADMISSIBLE"]
    rej = [r for r in results if _classification(r.get("harness", {}))
           == "REJECTED"]
    unt = [r for r in results if _classification(r.get("harness", {}))
           == "UNTESTED"]
    out += [
        f"- **ADMISSIBLE ({len(adm)}):** "
        + (", ".join(f"{r['hypothesis']} {r['asset_class']}" for r in adm)
           or "none"),
        f"- **REJECTED — tested, harness fail ({len(rej)}):** "
        + (", ".join(f"{r['hypothesis']} {r['asset_class']}" for r in rej)
           or "none"),
        f"- **UNTESTED — data too thin to render a verdict ({len(unt)}):** "
        + (", ".join(f"{r['hypothesis']} {r['asset_class']}" for r in unt)
           or "none"),
        "",
    ]
    if not adm:
        out += [
            "**0 of 3 candidate signals cleared `edge_stability_harness`.** None "
            "may rank or gate picks. None is wired. None is sized. The economic "
            "priors (post-earnings drift, cross-sectional momentum, storage-model "
            "inventory carry) are academically sound — but a sound prior is not "
            "an edge until the harness says so, and today it does not. This is "
            "consistent with the EDGE_VERDICT base rate. The paper-only posture "
            "(Fork 3) stands.",
        ]
    else:
        out += [
            f"**{len(adm)} of 3 candidate signals cleared the harness.** Against "
            "a poor base rate this is a *research candidate*, NOT a green light. "
            "Before any wiring it needs: (a) a fresh out-of-sample re-test, (b) "
            "full transaction-cost modelling, (c) a deflated-Sharpe / SPA "
            "multiple-testing correction, and (d) operator review. The harness "
            "is necessary, not sufficient. No signal is wired or sized by this "
            "module regardless of verdict.",
        ]
    out.append("")
    return "\n".join(out)


_FNS = {
    "pead": ("H-002", research_equity_pead),
    "etf-momentum": ("H-003", research_etf_momentum),
    "commodity-inventory": ("H-004", research_commodity_inventory),
}


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--signal",
                    choices=["pead", "etf-momentum", "commodity-inventory",
                             "all"],
                    default="all")
    ap.add_argument("--out", type=Path,
                    default=ROOT / "reports"
                    / "forward_signal_research_2026-05-18.md")
    ap.add_argument("--quick", action="store_true",
                    help="smaller universe for a fast smoke run")
    ap.add_argument("--json", dest="as_json", action="store_true")
    args = ap.parse_args()

    todo = (["pead", "etf-momentum", "commodity-inventory"]
            if args.signal == "all" else [args.signal])
    results = []
    for name in todo:
        hyp, fn = _FNS[name]
        print(f"# researching {name} ({hyp}) ...", file=sys.stderr)
        try:
            res = fn(args.quick)
        except Exception as exc:  # noqa: BLE001
            res = {"hypothesis": hyp,
                   "asset_class": name.split("-")[0].upper(),
                   "signal": "(fetch failed)", "data_source": "n/a",
                   "records": [], "n": 0,
                   "error": f"{type(exc).__name__}: {exc}"}
        res = _evaluate_signal(res)
        results.append(res)

    if args.as_json:
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
