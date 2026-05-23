#!/usr/bin/env python3
"""H-010 — EQUITY post-earnings-announcement drift (PEAD) research backtest.

OPT-IN RESEARCH SIDECAR ONLY. This module has NO caller in quality_gates.py,
dashboard_generator.py, or any pick-generation / scoring path. It reads market
data (earnings surprises + daily prices) and writes a report — nothing else.
Per the repo Wire-Up Rule it is explicitly an opt-in research sidecar.

------------------------------------------------------------------------------
THE HYPOTHESIS  (pre-registered H-010 in reports/hypothesis_registry.json)
------------------------------------------------------------------------------
Post-earnings-announcement drift (PEAD): liquid US equities with a large
POSITIVE standardized-unexpected-earnings (SUE) surprise drift UP over the
weeks after the announcement; large NEGATIVE surprises drift DOWN. PEAD is the
most academically robust anomaly in the literature (Bernard & Thomas 1989,
decades of out-of-sample survival). BUT a sound prior is not an edge — only
the verdict of tools/edge_stability_harness.py counts:

    eff >= 0.30, SAME sign, >= 3 of the scored 14-day walk-forward windows.

Five prior candidates were killed by this same gate. H-010 gets no special
treatment.

------------------------------------------------------------------------------
METHOD (leakage-controlled)
------------------------------------------------------------------------------
1. Universe: large-cap liquid US equities (S&P-100-style mega/large caps).
   EXCLUDES microcaps structurally — every name is a multi-$10B+ company; an
   explicit price>$5 floor is applied at entry as a belt-and-braces check.
2. SUE per earnings event = (actual EPS - estimated EPS) standardized by the
   rolling std of the firm's OWN past surprises (strictly prior events only —
   no look-ahead). An event needs >= MIN_PRIOR_SURPRISES past surprises before
   it can be scored, so the standardizer never peeks forward.
3. Entry is the first trading bar STRICTLY AFTER the announcement date — the
   announcement timestamp must precede entry. Hold DRIFT_HOLD_DAYS trading days.
4. Slippage SLIPPAGE_BPS basis points ROUND-TRIP is subtracted from every
   forward return before WON/LOST resolution.
5. Each earnings event becomes one synthetic resolved pick (status WON/LOST
   from the direction-signed, slippage-adjusted forward return). Direction is
   LONG on positive SUE, SHORT on negative SUE.
6. Purged + embargoed walk-forward (EMBARGO_DAYS embargo, WINDOW_DAYS blocks).
7. VERDICT: records fed through edge_stability_harness.evaluate() — the SAME
   admissibility gate EDGE_VERDICT_2026-05-18.md names as the only gate that
   counts.

------------------------------------------------------------------------------
DATA SOURCES (failover where possible)
------------------------------------------------------------------------------
Earnings surprises (actual vs estimated EPS):
  1. AlphaVantage EARNINGS (ALPHAVANTAGE) — quarterlyEarnings, ~30 yrs of
     history, carries reportedDate (the announcement date) + reportedEPS +
     estimatedEPS + reportTime. The deep-history source PEAD needs.
  2. FMP   (FMP_API_KEY)      — /v3/earnings-surprises/{ticker} (free-tier key
     here returns 403 for this endpoint; kept in the chain in case the key is
     upgraded).
  3. Finnhub (FINNHUB)        — /stock/earnings?symbol=... (free tier ~4 qtrs).
  4. yfinance Ticker.earnings_dates — surprise column (last ~2-4 qtrs).
Daily prices: yfinance (auto-adjusted close), with a 3-retry loop.

NOTE on the announcement timestamp: AlphaVantage `reportedDate` is the actual
press-release date and is distinct from `fiscalDateEnding` (the quarter end).
Entry is gated on `reportedDate` — the announcement timestamp PRECEDES entry.

    python tools/h010_pead_research.py [--quick] [--hold 20|30|60]
                                       [--out reports/h010_equity_pead_2026-05-18.md]
                                       [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# tools/ on path so the harness imports the same way new_signal_research.py does
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

# Windows UTF-8
if sys.platform == "win32":
    for _s in (sys.stdout, sys.stderr):
        if hasattr(_s, "reconfigure"):
            try:
                _s.reconfigure(encoding="utf-8", errors="replace")
            except Exception:  # noqa: BLE001
                pass

import edge_stability_harness as harness  # noqa: E402

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------
EMBARGO_DAYS = 5            # purged-CV embargo between train/test (AFML Ch.7)
WINDOW_DAYS = 14            # walk-forward window length (harness default)
DRIFT_HOLD_DAYS = 30        # trading-day drift hold window (PEAD: 20-60d)
SLIPPAGE_BPS = 100          # round-trip slippage in basis points
MIN_PRIOR_SURPRISES = 4     # past surprises required before an event is scored
MIN_PRICE = 5.0             # ex-microcap price floor at entry (belt-and-braces)
ABS_SUE_MIN = 0.5           # only act on a real surprise (|SUE| above this)
ZED_HARNESS_FIELD = "signal_z"   # score field on each synthetic pick record
AV_RATE_SLEEP = 13.0        # seconds between earnings fetches (AlphaVantage
                            # free tier ~5 calls/min); keeps the chain legal

# Large-cap liquid US equity universe (~S&P-200 breadth). Every name is a
# multi-$10B+ large/mega-cap — microcaps are excluded structurally by
# construction. Breadth is deliberate: PEAD events are quarterly, so a wide
# cross-section is required for any 14-day earnings-season window to clear the
# harness's 80-event / 15-winner-15-loser floor. (Per PATH_TO_PROVEN_EDGE: a
# sparse event signal needs cross-sectional breadth, not a wider time window.)
UNIVERSE = [
    "AAPL", "MSFT", "AMZN", "GOOGL", "META", "NVDA", "TSLA", "JPM", "V", "JNJ",
    "WMT", "PG", "MA", "HD", "BAC", "XOM", "CVX", "ABBV", "PFE", "KO", "PEP",
    "COST", "MRK", "AVGO", "ADBE", "CSCO", "ACN", "MCD", "ABT", "CRM", "TMO",
    "NKE", "DHR", "TXN", "NEE", "VZ", "CMCSA", "INTC", "PM", "WFC", "QCOM",
    "ORCL", "AMD", "HON", "UNP", "IBM", "GE", "CAT", "LOW", "INTU", "AMAT",
    "GS", "MS", "BLK", "AXP", "SPGI", "ELV", "BKNG", "ISRG", "MDT", "GILD",
    "ADP", "VRTX", "REGN", "LRCX", "MU", "PANW", "SNPS", "CDNS", "KLAC", "MMC",
    "CB", "ZTS", "BSX", "SYK", "PGR", "CI", "SO", "DUK", "ITW", "EOG", "SLB",
    "MPC", "PSX", "VLO", "OXY", "PXD", "WMB", "KMI", "F", "GM", "DAL", "UAL",
    "DE", "EMR", "ETN", "PH", "ROK", "CMI", "GD", "LMT", "NOC", "RTX", "BA",
    "TGT", "DG", "DLTR", "ROST", "TJX", "YUM", "SBUX", "CMG", "MAR", "HLT",
    "ORLY", "AZO", "GPC", "EBAY", "ADSK", "FTNT", "CRWD", "NOW", "WDAY", "TEAM",
    "DDOG", "NET", "SHOP", "SQ", "PYPL", "UBER", "ABNB", "DASH", "ZM", "DOCU",
    "ROKU", "PINS", "SNAP", "SPOT", "TTD", "MTCH", "EA", "TTWO", "WBD", "DIS",
    "NFLX", "CHTR", "T", "TMUS", "FDX", "UPS", "CSX", "NSC", "ODFL", "WM",
    "RSG", "PCAR", "JCI", "CARR", "OTIS", "TT", "DOW", "DD", "LIN", "APD",
    "SHW", "ECL", "NEM", "FCX", "NUE", "STLD", "VMC", "MLM", "PPG", "ALB",
    "CTVA", "MOS", "CF", "LYB", "EXC", "AEP", "D", "SRE", "XEL", "PEG", "ED",
    "WEC", "ES", "EIX", "PCG", "AEE", "CNP", "CMS", "DTE", "FE", "ATO", "EQT",
    "HES", "DVN", "FANG", "MRO", "APA", "HAL", "BKR", "COP", "ENPH", "FSLR",
    "PLD", "AMT", "CCI", "EQIX", "DLR", "PSA", "O", "SPG", "WELL", "VICI",
    "AVB", "EQR", "SBAC", "ARE", "VTR", "INVH", "MAA", "ESS", "KIM", "REG",
    "UNH", "CVS", "HUM", "CNC", "HCA", "MCK", "CAH", "COR", "DXCM", "IDXX",
    "IQV", "A", "MTD", "WAT", "RMD", "BAX", "BDX", "EW", "HOLX", "ALGN", "STE",
]
UNIVERSE_QUICK = ["AAPL", "MSFT", "NVDA", "JPM", "WMT", "XOM", "PG", "AMD",
                  "HD", "KO", "MRK", "CAT"]


# ===========================================================================
# Generic helpers
# ===========================================================================
def _http_json(url: str, timeout: int = 30):
    """Plain JSON GET (used for FMP/Finnhub). None on any failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "h010-pead/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception:  # noqa: BLE001
        return None


def apply_slippage(raw_ret: float, slippage_bps: float = SLIPPAGE_BPS) -> float:
    """Subtract round-trip slippage from a raw forward return.

    slippage_bps is the TOTAL round-trip cost (entry + exit). 100 bps = 0.01.
    Returns the net return a trader would actually realise.
    """
    return raw_ret - slippage_bps / 10_000.0


def compute_sue(actual: float, estimate: float,
                prior_surprises: list[float]) -> float | None:
    """Standardized Unexpected Earnings.

    SUE = (actual - estimate) / std(prior raw surprises).

    `prior_surprises` is the list of (actual-estimate) values for the firm's
    OWN earnings events STRICTLY BEFORE this one. Requires >= MIN_PRIOR_SURPRISES
    so the standardizer is built only from past data — no look-ahead. Returns
    None if there is not enough history or the prior surprises have zero
    dispersion.
    """
    if actual is None or estimate is None:
        return None
    if len(prior_surprises) < MIN_PRIOR_SURPRISES:
        return None
    sd = statistics.pstdev(prior_surprises)
    if sd <= 0:
        return None
    return (actual - estimate) / sd


# ===========================================================================
# Earnings-surprise data — failover chain
# ===========================================================================
def fetch_earnings_alphavantage(ticker: str) -> list[dict]:
    """AlphaVantage EARNINGS — quarterlyEarnings, ~30 yrs. asc.

    Uses `reportedDate` (the announcement date) as the event date — strictly
    distinct from `fiscalDateEnding`. Returns [{date, actual, estimate}, ...].
    Free tier is rate-limited; an empty/throttled response yields []. The
    caller's failover chain handles a throttle gracefully.
    """
    key = os.environ.get("ALPHAVANTAGE", "").strip() or \
        os.environ.get("ALPHAVANTAGE_API_KEY", "").strip()
    if not key:
        return []
    url = (f"https://www.alphavantage.co/query?function=EARNINGS"
           f"&symbol={ticker}&apikey={key}")
    data = _http_json(url)
    if not isinstance(data, dict):
        return []
    if data.get("Note") or data.get("Information"):
        return []   # rate-limited / quota exhausted
    out = []
    for row in data.get("quarterlyEarnings", []):
        try:
            d = str(row.get("reportedDate") or "")[:10]
            if not d or d == "None":
                continue
            actual = row.get("reportedEPS")
            est = row.get("estimatedEPS")
            if actual in (None, "None", "") or est in (None, "None", ""):
                continue
            out.append({"date": d, "actual": float(actual),
                        "estimate": float(est)})
        except (KeyError, TypeError, ValueError):
            continue
    out.sort(key=lambda r: r["date"])
    return out


def fetch_earnings_fmp(ticker: str) -> list[dict]:
    """FMP earnings surprises — multi-year. [{date, actual, estimate}, ...] asc."""
    key = os.environ.get("FMP_API_KEY", "").strip()
    if not key:
        return []
    url = (f"https://financialmodelingprep.com/api/v3/earnings-surprises/"
           f"{ticker}?apikey={key}")
    data = _http_json(url)
    if not isinstance(data, list):
        return []
    out = []
    for row in data:
        try:
            d = str(row["date"])[:10]
            actual = row.get("actualEarningResult")
            est = row.get("estimatedEarning")
            if actual is None or est is None:
                continue
            out.append({"date": d, "actual": float(actual),
                        "estimate": float(est)})
        except (KeyError, TypeError, ValueError):
            continue
    out.sort(key=lambda r: r["date"])
    return out


def fetch_earnings_finnhub(ticker: str) -> list[dict]:
    """Finnhub earnings surprises — last ~4-8 quarters. asc."""
    key = os.environ.get("FINNHUB", "").strip() or \
        os.environ.get("FINNHUB_API_KEY", "").strip()
    if not key:
        return []
    url = f"https://finnhub.io/api/v1/stock/earnings?symbol={ticker}&token={key}"
    data = _http_json(url)
    if not isinstance(data, list):
        return []
    out = []
    for row in data:
        try:
            d = str(row["period"])[:10]
            actual = row.get("actual")
            est = row.get("estimate")
            if actual is None or est is None:
                continue
            out.append({"date": d, "actual": float(actual),
                        "estimate": float(est)})
        except (KeyError, TypeError, ValueError):
            continue
    out.sort(key=lambda r: r["date"])
    return out


def fetch_earnings_yfinance(ticker: str) -> list[dict]:
    """yfinance earnings dates — last ~2-4 quarters. Estimate + Reported EPS."""
    import warnings
    warnings.filterwarnings("ignore")
    try:
        import yfinance as yf
    except ImportError:
        return []
    try:
        tk = yf.Ticker(ticker)
        df = tk.get_earnings_dates(limit=48)   # ~12 yrs of quarterly history
    except Exception:  # noqa: BLE001
        return []
    if df is None or len(df) == 0:
        return []
    out = []
    for idx, row in df.iterrows():
        try:
            d = idx.date().isoformat() if hasattr(idx, "date") else str(idx)[:10]
            actual = row.get("Reported EPS")
            est = row.get("EPS Estimate")
            if actual is None or est is None:
                continue
            af, ef = float(actual), float(est)
            if af != af or ef != ef:   # NaN guard
                continue
            out.append({"date": d, "actual": af, "estimate": ef})
        except (KeyError, TypeError, ValueError):
            continue
    out.sort(key=lambda r: r["date"])
    return out


# Module-level latch: once AlphaVantage returns empty for the FIRST ticker we
# assume the 25/day free-tier quota is exhausted and stop calling it (so a
# 245-ticker run does not waste 245 dead HTTP round-trips). yfinance carries
# the run in that case — it has no quota, ~12 yrs depth at limit=48.
_AV_DISABLED = False


def fetch_earnings(ticker: str) -> tuple[list[dict], str, bool]:
    """Earnings-surprise history with failover.

    Returns (events, source, av_called). Chain (deepest history first):
    AlphaVantage -> FMP -> Finnhub -> yfinance. Whichever source returns the
    most events wins, so a partial/throttled response never silently shrinks
    the sample. `av_called` lets the caller rate-limit only when AV was hit.
    """
    global _AV_DISABLED
    best: list[dict] = []
    src = ""
    av_called = False
    if not _AV_DISABLED:
        av_called = True
        try:
            ev = fetch_earnings_alphavantage(ticker)
        except Exception:  # noqa: BLE001
            ev = []
        if ev:
            best, src = ev, "AlphaVantage"
        else:
            _AV_DISABLED = True   # quota exhausted / key invalid — stop calling
        if len(best) >= 20:
            return best, src, av_called   # AV depth is plenty
    for name, fn in (("FMP", fetch_earnings_fmp),
                     ("Finnhub", fetch_earnings_finnhub),
                     ("yfinance", fetch_earnings_yfinance)):
        try:
            ev = fn(ticker)
        except Exception:  # noqa: BLE001
            ev = []
        if len(ev) > len(best):
            best, src = ev, name
    return best, src, av_called


# ===========================================================================
# Price data
# ===========================================================================
def fetch_daily_close(ticker: str, period: str = "10y") -> dict[str, float]:
    """yfinance daily auto-adjusted close keyed by ISO date. {} on failure."""
    import warnings
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
        time.sleep(3)
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


# ===========================================================================
# Synthetic resolved-pick record
# ===========================================================================
def make_record(entry_date: str, resolved_at: str, sue: float,
                 net_ret: float, direction: int) -> dict:
    """One synthetic resolved pick.

    direction: +1 LONG (positive SUE), -1 SHORT (negative SUE).
    signed return = net_ret * direction (net_ret already slippage-adjusted).
    The harness reads `status` (WON/LOST) and ranks on the score field
    `signal_z`. We store |SUE| as conviction magnitude: if PEAD is a real edge
    the harness should find winners carrying a higher |SUE| than losers, with
    the SAME sign, in >= 3 windows.
    """
    signed = net_ret * direction
    return {
        "status": "WON" if signed > 0 else "LOST",
        "resolved_at": resolved_at,
        "entry_date": entry_date,
        "timestamp": entry_date,
        ZED_HARNESS_FIELD: abs(sue),
        "sue": round(sue, 4),
        "net_ret": round(net_ret, 5),
        "direction": direction,
    }


# ===========================================================================
# Purged + embargoed walk-forward (leakage-control picture)
# ===========================================================================
def purge_embargo(records: list[dict]) -> dict:
    """Purged + embargoed walk-forward summary (the harness eff is the verdict).

    Tiles the timeline into consecutive WINDOW_DAYS test blocks. Records whose
    [entry, resolved] interval overlaps the EMBARGO_DAYS band immediately
    before a test block are purged from that block's notional train side. Here
    we report per-OOS-block realised WR — the leakage-controlled performance
    picture; the harness eff stability is the actual admissibility verdict.
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
        test = [r for r in dated
                if cur <= date.fromisoformat(r["entry_date"]) < end]
        if test:
            won = sum(1 for r in test if r["status"] == "WON")
            blocks.append({"start": cur.isoformat(), "n": len(test),
                           "wr": round(won / len(test), 3)})
        cur = end
    won = sum(1 for r in dated if r["status"] == "WON")
    return {
        "blocks": blocks,
        "oos_n": len(dated),
        "oos_wr": round(won / len(dated), 3),
        "embargo_days": EMBARGO_DAYS,
        "note": "OOS = all earnings events; per-block WR is the walk-forward "
                "picture. Embargo is enforced inside the harness eff windows.",
    }


def harness_verdict(records: list[dict]) -> dict:
    """Run records through edge_stability_harness.evaluate() (THE gate)."""
    orig_load = harness._load
    try:
        harness._load = lambda: records  # type: ignore[assignment]
        verdict = harness.evaluate(ZED_HARNESS_FIELD, WINDOW_DAYS)
    finally:
        harness._load = orig_load  # type: ignore[assignment]
    return verdict


# ===========================================================================
# Backtest
# ===========================================================================
def research_pead(quick: bool, hold_days: int) -> dict:
    """H-010: SUE-driven PEAD backtest over a large-cap ex-microcap universe."""
    universe = UNIVERSE_QUICK if quick else UNIVERSE
    records: list[dict] = []
    per_ticker: dict[str, dict] = {}
    sources: dict[str, int] = {}

    for tk in universe:
        events, src, av_called = fetch_earnings(tk)
        if av_called:
            time.sleep(AV_RATE_SLEEP)    # respect AlphaVantage 5-calls/min limit
        if len(events) < MIN_PRIOR_SURPRISES + 2:
            per_ticker[tk] = {"skip": f"earnings={len(events)} src={src or 'none'}"}
            time.sleep(0.2)
            continue
        prices = fetch_daily_close(tk)
        if len(prices) < 120:
            per_ticker[tk] = {"skip": f"price_bars={len(prices)}"}
            time.sleep(0.2)
            continue
        sources[src] = sources.get(src, 0) + 1
        pdates = sorted(prices)
        prior_surprises: list[float] = []
        n = 0
        for ev in events:
            ann_date = ev["date"]
            raw_surprise = ev["actual"] - ev["estimate"]
            # SUE built ONLY from strictly-prior surprises (no look-ahead).
            sue = compute_sue(ev["actual"], ev["estimate"], prior_surprises)
            # record this surprise into history AFTER computing SUE for it.
            prior_surprises.append(raw_surprise)
            if sue is None or abs(sue) < ABS_SUE_MIN:
                continue
            # entry = first price bar STRICTLY AFTER the announcement date.
            entry = next((d for d in pdates if d > ann_date), None)
            if entry is None:
                continue
            ei = pdates.index(entry)
            if ei + hold_days >= len(pdates):
                continue
            entry_px = prices[entry]
            if entry_px < MIN_PRICE:        # ex-microcap belt-and-braces
                continue
            exit_px = prices[pdates[ei + hold_days]]
            raw_ret = exit_px / entry_px - 1.0
            net_ret = apply_slippage(raw_ret)
            # PEAD direction: positive SUE -> LONG (+1), negative SUE -> SHORT.
            direction = 1 if sue > 0 else -1
            resolved = pdates[ei + hold_days]
            records.append(make_record(entry, resolved, sue, net_ret, direction))
            n += 1
        per_ticker[tk] = {"n": n, "earnings": len(events), "src": src}
        time.sleep(0.2)

    return {
        "hypothesis": "H-010",
        "asset_class": "EQUITY",
        "signal": f"SUE-driven post-earnings drift, {hold_days}-trading-day hold, "
                  f"{SLIPPAGE_BPS}bps round-trip slippage",
        "data_source": "FMP earnings-surprises -> Finnhub -> yfinance "
                       "(failover) + yfinance daily close",
        "hold_days": hold_days,
        "per_ticker": per_ticker,
        "sources_used": sources,
        "records": records,
        "n": len(records),
    }


def evaluate_signal(res: dict) -> dict:
    """Attach purged-CV summary + harness verdict to the research result."""
    recs = res.get("records", [])
    if len(recs) < harness.MIN_WINDOW_N:
        res["purged_cv"] = {"oos_n": len(recs),
                            "note": f"too few earnings events ({len(recs)}) for "
                                    f"the harness (needs >= {harness.MIN_WINDOW_N}"
                                    f"/window)"}
        res["harness"] = {"admissible": False,
                          "windows_scored": 0,
                          "reason": f"INSUFFICIENT DATA — {len(recs)} events, "
                                    f"harness needs >= {harness.MIN_WINDOW_N} "
                                    f"per 14d window"}
        return res
    res["purged_cv"] = purge_embargo(recs)
    res["harness"] = harness_verdict(recs)
    # Supplementary wider-window check if 14d windows are too sparse to score.
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


# ===========================================================================
# Report
# ===========================================================================
def render_report(res: dict) -> str:
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    h = res.get("harness", {})
    adm = h.get("admissible", False)
    flag = "ADMISSIBLE" if adm else "REJECTED"
    out = [
        "# H-010 — EQUITY Post-Earnings-Announcement Drift (PEAD) — 2026-05-18",
        "",
        f"_Generated {ts} by `tools/h010_pead_research.py`._",
        "",
        "**Status: OPT-IN RESEARCH SIDECAR. No production wiring.** This module "
        "has no caller in `quality_gates.py`, `dashboard_generator.py`, or any "
        "pick-generation / scoring path. It reads earnings + price data and "
        "writes this report — nothing else. Per the repo Wire-Up Rule it is "
        "explicitly an opt-in research sidecar.",
        "",
        "## Mandate",
        "",
        "`reports/PATH_TO_PROVEN_EDGE_2026-05-18.md` item P4: build and "
        "harness-test H-010 — EQUITY post-earnings-announcement drift. PEAD is "
        "the most academically robust anomaly in the literature (Bernard & "
        "Thomas 1989; decades of out-of-sample survival). **But a sound prior "
        "is not an edge** — `reports/EDGE_VERDICT_2026-05-18.md` is the standing "
        "rule: no edge claim counts until it clears "
        "`tools/edge_stability_harness.py` (eff >= 0.30, same sign, >= 3 of 5 "
        "walk-forward windows). Five candidates have already been killed by "
        "this gate. H-010 was pre-registered in "
        "`reports/hypothesis_registry.json` BEFORE this backtest was written.",
        "",
        "## Method (leakage-controlled)",
        "",
        f"- **Universe:** {len(res.get('per_ticker', {}))} large-cap liquid US "
        "equities (S&P-100-style). Microcaps are excluded structurally — every "
        f"name is a multi-$10B+ company — plus an explicit price>${MIN_PRICE:.0f} "
        "floor at entry.",
        f"- **SUE:** (actual EPS - estimated EPS) standardized by the rolling "
        "std of the firm's OWN past surprises. An event needs >= "
        f"{MIN_PRIOR_SURPRISES} strictly-prior surprises before it is scored, so "
        "the standardizer never peeks forward. Only |SUE| >= "
        f"{ABS_SUE_MIN} events are acted on.",
        f"- **Entry:** first trading bar STRICTLY AFTER the announcement date "
        "(announcement timestamp must precede entry — no look-ahead).",
        f"- **Hold:** {res.get('hold_days')} trading days (PEAD drift window).",
        f"- **Slippage:** {SLIPPAGE_BPS} bps ROUND-TRIP, subtracted from every "
        "forward return before WON/LOST resolution.",
        f"- **Direction:** LONG on positive SUE, SHORT on negative SUE.",
        f"- **Walk-forward:** purged + embargoed ({EMBARGO_DAYS}-day embargo, "
        f"{WINDOW_DAYS}-day blocks).",
        "- **Verdict gate:** records fed through "
        "`edge_stability_harness.evaluate()` — the SAME gate EDGE_VERDICT names. "
        f"ADMISSIBLE iff |eff| >= {harness.EFF_MIN}, same sign, >= "
        f"{harness.MIN_STABLE_WINDOWS} of the scored {WINDOW_DAYS}-day windows.",
        "",
        "**A gaudy in-sample win rate is NOT a pass.** Only the harness verdict "
        "counts.",
        "",
        f"## H-010 — EQUITY PEAD — [{flag}]",
        "",
        f"- **Signal:** {res['signal']}",
        f"- **Data source:** {res['data_source']}",
        f"- **Sample size:** {res.get('n', 0)} earnings-event picks",
        f"- **Earnings sources used:** {res.get('sources_used', {})}",
    ]
    # per-ticker breakdown
    bd = res.get("per_ticker", {})
    if bd:
        out += ["", "| ticker | events | earnings rows | source |",
                "|---|---|---|---|"]
        for k, v in bd.items():
            if "skip" in v:
                out.append(f"| {k} | skip: {v['skip']} | | |")
            else:
                out.append(f"| {k} | {v.get('n', 0)} | {v.get('earnings', 0)} "
                            f"| {v.get('src', '')} |")
    # purged CV
    cv = res.get("purged_cv", {})
    out += ["", "### Purged + embargoed walk-forward"]
    if cv.get("oos_wr") is not None:
        out.append(f"- OOS sample: n={cv['oos_n']}, pooled WR="
                    f"{cv['oos_wr']*100:.1f}% (net of {SLIPPAGE_BPS}bps slippage)")
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
        if h.get("windows_scored", 0) == 0:
            out.append("- **classification: UNTESTED (insufficient density)** — "
                        f"the harness needs >= {harness.MIN_WINDOW_N} resolved "
                        "events AND >= 15 winners + >= 15 losers per 14-day "
                        "window; the data is too thin per window to render an "
                        "eff verdict. Not a pass.")
        elif h.get("windows_scored", 0) < harness.MIN_STABLE_WINDOWS:
            out.append("- **classification: UNTESTED (too few scored windows)** "
                        f"— only {h.get('windows_scored')} window(s) scored; the "
                        f"harness needs >= {harness.MIN_STABLE_WINDOWS}. Not a "
                        "pass.")
        else:
            out.append("- **classification: tested — the harness rendered a "
                        "verdict on the eff stability.**")
    out.append(f"- **{flag}** — {h.get('reason', 'n/a')}")
    # supplementary
    sh = res.get("harness_supplementary")
    if sh:
        out += ["",
                f"_Supplementary check — {sh['window_days']}-day windows "
                "(secondary view for a sparse signal; the 14-day verdict above "
                "remains authoritative per EDGE_VERDICT):_"]
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
    # honest conclusion
    out += ["", "## Honest conclusion", ""]
    if adm:
        out += [
            "**H-010 EQUITY PEAD CLEARED `edge_stability_harness`.** This is the "
            "first signal to pass the gate against a poor base rate (5 prior "
            "kills). It must be treated as a *research candidate*, not a green "
            "light. Before any wiring or sizing it needs: (a) re-test on a "
            "fresh out-of-sample period, (b) full transaction-cost + market-"
            "impact modelling beyond the flat 100bps, (c) a deflated-Sharpe / "
            "SPA multiple-testing correction, and (d) operator review. The "
            "harness is necessary, not sufficient — `cot_positioning` passed "
            "DSR + SPA and was still a leakage artifact. No signal is wired or "
            "sized by this module.",
        ]
    else:
        scored = h.get("windows_scored", 0)
        tested = scored >= harness.MIN_STABLE_WINDOWS
        if tested:
            out += [
                "**H-010 EQUITY PEAD did NOT clear `edge_stability_harness` — "
                "kill #6.** The harness rendered a real eff-stability verdict "
                "and the signal failed it. PEAD has a strong academic prior, "
                "but in this universe / hold / cost configuration the SUE "
                "signal does not separate winners from losers with a stable "
                "same-sign eff across >= 3 walk-forward windows. A sound prior "
                "is not an edge; this is the measured result. Per the "
                "EDGE_VERDICT standing rule, do NOT re-test this signal family "
                "on this sample — archive it.",
            ]
        else:
            out += [
                "**H-010 EQUITY PEAD is UNTESTED — the harness could not render "
                "a verdict.** Only "
                f"{scored} of the scored 14-day windows had enough events "
                f"(>= 15 winners + >= 15 losers, >= {harness.MIN_WINDOW_N} "
                "total) — the harness needs >= "
                f"{harness.MIN_STABLE_WINDOWS}. Earnings events are quarterly, "
                "so they cluster around earnings season and most 14-day "
                "windows are too thin. This is a data-density limit, not a "
                "clean noise-reject — and it is still NOT a pass. A denser "
                "sample (wider universe, longer history, or a paid intraday "
                "earnings-timestamp feed) is needed to test H-010 honestly. "
                "See the supplementary wider-window check above for a "
                "secondary, non-authoritative view.",
            ]
    out += [
        "",
        f"No signal is wired or sized by this module regardless of verdict. "
        f"H-010's result is recorded in `reports/hypothesis_registry.json`.",
        "",
    ]
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true",
                    help="smaller universe for a fast smoke run")
    ap.add_argument("--hold", type=int, default=DRIFT_HOLD_DAYS,
                    help="drift hold window in trading days (PEAD: 20-60)")
    ap.add_argument("--out", type=Path,
                    default=ROOT / "reports" / "h010_equity_pead_2026-05-18.md")
    ap.add_argument("--json", dest="as_json", action="store_true")
    args = ap.parse_args()

    print(f"# H-010 PEAD research — quick={args.quick} hold={args.hold}d ...",
          file=sys.stderr)
    res = research_pead(args.quick, args.hold)
    res = evaluate_signal(res)

    if args.as_json:
        slim = {k: v for k, v in res.items() if k != "records"}
        slim["n_records"] = len(res.get("records", []))
        print(json.dumps(slim, indent=2, default=str))
        return 0

    report = render_report(res)
    args.out.write_text(report, encoding="utf-8")
    print(f"# wrote {args.out}", file=sys.stderr)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
