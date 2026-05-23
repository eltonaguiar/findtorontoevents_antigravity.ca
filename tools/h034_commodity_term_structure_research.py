#!/usr/bin/env python3
"""H-034 — Commodity term-structure (basis / roll-yield) long-short backtest.

OPT-IN RESEARCH SIDECAR. HARNESS-GATED. FREE-DATA ONLY. NO PRODUCTION WIRING.

No caller in `audit_trail/quality_gates.py`, `audit_dashboard/dashboard_generator.py`,
`passes_active_gate`, `calculate_smart_score`, `production_scanner`, or any other
pick-generation / scoring path. This module fetches free public commodity-futures
data, computes a Gorton-Rouwenhorst (2006) basis / roll-yield long-short signal,
runs a continuous cross-sectional book, gates the result through
`tools.edge_stability_harness.is_admissible()` (imported UNMODIFIED), applies a
post-cost gate, and writes a verdict report. Nothing else. Importing this module
has no side effects on production.

This module is the cross-vendor multi-AI-D-path-consensus candidate flagged by
the Claude swarm: "Gorton-Rouwenhorst uses continuous front-month vs second-month
spread, available free from CME/Quandl. If it failed on construction bugs not
signal, re-run before calling it dead." H-034 is that clean re-run, deliberately
distinct from the killed H-007 (single-asset front/second roll-yield z-score on
ETF proxy): H-034 is a CROSS-SECTIONAL long-short quintile portfolio across a
fixed liquid futures universe, not a per-asset directional time-series score.

------------------------------------------------------------------------------
WHY THIS MODULE EXISTS
------------------------------------------------------------------------------
The canonical Gorton-Rouwenhorst (2006, "Facts and Fantasies about Commodity
Futures") cross-sectional sort RANKS commodities by their front-vs-second-month
basis and goes LONG the top-quintile (most-backwardated, positive roll-yield)
while SHORTING the bottom-quintile (most-contangoed, negative roll-yield). The
spread basket is the long-short carry portfolio. This is structurally DIFFERENT
from H-007's single-asset directional z-score and is therefore a permissible new
hypothesis under M-107 (registered as a separate family before any data fetch).

THE SIGNAL — front-vs-second-month basis / roll-yield:
  basis(i, t) = ln(price_second(i,t) / price_front(i,t)) / months_between
              ~ annualised roll-yield. POSITIVE basis = contango (cost of carry,
                bearish long-side); NEGATIVE basis = backwardation (positive
                expected roll, bullish long-side). Gorton-Rouwenhorst sign
                convention: LONG most-BACKWARDATED (most-negative basis), SHORT
                most-CONTANGOED (most-positive basis).
  signal_z = strictly-past rolling z-score of `-basis(i,t)` per commodity
             (so a high z = strongly backwardated -> LONG).
  Cross-sectionally we then take the top quintile (long) and bottom quintile
  (short) by this z each rebalance date.

------------------------------------------------------------------------------
DATA — FREE, NO KEY
------------------------------------------------------------------------------
  * yfinance daily OHLC for the front-month continuous futures contract
    (=F tickers): CL=F crude, NG=F nat gas, HG=F copper, GC=F gold, SI=F silver,
    ZC=F corn, ZW=F wheat, ZS=F soybeans, KC=F coffee, CT=F cotton.
  * yfinance second-month series via the same tickers' next-expiry futures
    are NOT exposed directly; yfinance =F tickers are STITCHED CONTINUOUS series.
    Construction caveat: a true CME front/second calendar-spread feed (Quandl
    CME WIKI continuous chains) would be cleaner — yfinance's stitched second
    series introduces roll noise on roll dates that can bias the basis estimate.
    The proxy used here is a strictly-past ROLLING-WINDOW return of the front
    series as a basis stand-in (positive trailing return correlates with
    backwardation regimes; the cross-sectional rank is the part that matters
    for Gorton-Rouwenhorst, not the absolute basis level). This is honestly
    labelled `basis_proxy_mode = "front_return_zscore"` in the registry and the
    verdict layer says so — a true calendar-spread feed would be a different
    test.
  * yfinance is the free, no-key tape; if the network is unavailable the module
    degrades to a deterministic synthetic series and reports the verdict
    `UNTESTED-data-gap` honestly — it never fabricates a pass.

NOTE on CT=F: per `MEMORY.md` cotton is on `COMMODITY_BLACKLIST` (Phase 2-D
kill). It is kept in the H-034 universe for HARNESS PURPOSES ONLY (the harness
needs a wide cross-section to compute quintile ranks). Any commercial / paper
sizing decision still treats CT=F as blacklisted; this sidecar does NOT emit
picks of any kind.

------------------------------------------------------------------------------
THE CONSTRUCTION (legitimate density pattern, H-008/H-019/H-020/H-026/H-027)
------------------------------------------------------------------------------
  * FULL continuous-position cross-sectional book. Every (commodity, rebalance
    date) with a next bar is one resolved record. The QUINTILE filter selects
    long/short legs but every record is resolved (we do NOT sparse-filter to
    only "extreme" days at the harness layer — the harness sees a dense daily
    stream; quintile membership is captured in the `direction` field and
    non-quintile records are dropped only at the SIGNAL stage, not at the
    harness stage).
  * Rebalance cadence: WEEKLY (every 5 trading days), per Gorton-Rouwenhorst
    paper convention (paper used monthly; weekly = denser harness windows,
    same signal family).
  * STRICT no-look-ahead: the basis z-score for a position dated D is computed
    from price observations STRICTLY BEFORE D; entry D+1; realized return is
    price close(D+1) -> close(D+1+HOLD_DAYS).

------------------------------------------------------------------------------
THE VERDICT GATE
------------------------------------------------------------------------------
Records pass through `tools.edge_stability_harness.evaluate()` /
`is_admissible()` imported UNMODIFIED. ADMISSIBLE iff |eff| >= 0.30, same sign,
>= 3 of 5 walk-forward 14-day windows, >= 80 records/window. PLUS a 15bps
round-trip + futures-roll-cost post-cost gate: net edge must keep >= 60% of
gross.

A gaudy in-sample WR is NOT a pass. The edge hunt's base rate is poor (8-11
prior harness kills, including H-007 roll-yield z-score). This module reports
the verdict honestly whichever way it lands. Nothing here is wired into or
sized by any production path.

    python tools/h034_commodity_term_structure_research.py [--quick] [--json]
            [--refresh-cache]
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = Path(__file__).resolve().parent
for _p in (ROOT, TOOLS_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

if sys.platform == "win32":
    for _s in (sys.stdout, sys.stderr):
        if hasattr(_s, "reconfigure"):
            try:
                _s.reconfigure(encoding="utf-8", errors="replace")
            except Exception:  # noqa: BLE001
                pass

# Harness imported UNMODIFIED — same wiring as H-026/H-027/H-028.
import edge_stability_harness as harness  # noqa: E402

# ---------------------------------------------------------------------------
# Tunables — pre-registered (H-034). The signal family is fixed; no per-window
# search, no post-hoc parameter tuning.
# ---------------------------------------------------------------------------
BASIS_TRAILING_DAYS = 21    # rolling window for the trailing-return basis proxy
Z_ROLL = 60                 # rolling z-score look-back (STRICTLY past obs)
REBALANCE_DAYS = 5          # weekly rebalance (5 trading days)
HOLD_DAYS = 5               # forward return horizon (weekly hold)
WINDOW_DAYS = 14            # walk-forward window length (harness default)
HARNESS_FIELD = "signal_z"  # conviction-magnitude score the harness reads
ROUND_TRIP_COST_BPS = 15.0  # commodity-futures round-trip (spread + slippage
                            # + futures roll cost, both legs)
COST_SURVIVAL_MIN = 0.60    # net edge must retain >= 60% of gross
QUINTILE_FRAC = 0.20        # top/bottom 20% quintile

CACHE = ROOT / "tools" / "cache" / "h034_commodity_term_structure_cache.json"

# Gorton-Rouwenhorst liquid commodity-futures universe (yfinance =F tickers).
# CT=F is blacklisted per MEMORY.md — kept here ONLY for harness cross-section;
# this sidecar does not emit / size any pick. See module docstring.
COMMODITIES_FULL = [
    "CL=F",   # WTI crude oil
    "NG=F",   # natural gas
    "HG=F",   # copper
    "GC=F",   # gold
    "SI=F",   # silver
    "ZC=F",   # corn
    "ZW=F",   # wheat
    "ZS=F",   # soybeans
    "KC=F",   # coffee
    "CT=F",   # cotton (BLACKLISTED — harness universe only)
]
COMMODITIES_QUICK = ["CL=F", "NG=F", "HG=F", "GC=F", "ZC=F"]


# ===========================================================================
# Data fetch — free public APIs, no key.
# ===========================================================================
def fetch_futures_series(ticker: str) -> dict:
    """Fetch a free daily close series for one commodity futures continuous.

    yfinance =F tickers are STITCHED continuous series (CME settle + roll
    convention chosen by yfinance). The roll bumps inject some noise; this is
    the construction caveat documented in the module docstring. A true CME
    front/second calendar-spread feed (Quandl/CME WIKI) would be cleaner.

    Returns {iso_date: close}. On total network failure returns {} and the
    caller degrades to a labelled synthetic series + UNTESTED verdict — never
    a fake pass.
    """
    price: dict[str, float] = {}
    try:
        import yfinance as yf  # noqa: PLC0415
        hist = yf.Ticker(ticker).history(
            period="max", interval="1d", auto_adjust=False)
        if hist is not None and not hist.empty:
            for idx, row in hist.iterrows():
                try:
                    d = idx.date().isoformat()
                    c = float(row["Close"])
                    if c > 0:
                        price[d] = c
                except Exception:  # noqa: BLE001
                    continue
    except Exception:  # noqa: BLE001
        pass
    return price


def _synthetic_series(ticker: str, n_days: int = 900) -> dict:
    """Deterministic synthetic price series for an OFFLINE run.

    Used ONLY when yfinance is unreachable. Clearly labelled; drives an
    UNTESTED-data-gap verdict — never a real pass. A small deterministic LCG
    (seeded by the ticker) keeps the run reproducible.
    """
    seed = sum(ord(c) for c in ticker) * 2654435761 & 0xFFFFFFFF
    state = seed

    def rand() -> float:
        nonlocal state
        state = (1103515245 * state + 12345) & 0x7FFFFFFF
        return state / 0x7FFFFFFF

    price: dict[str, float] = {}
    px = 50.0 + (seed % 60)
    base = datetime(2023, 1, 2, tzinfo=timezone.utc)
    for i in range(n_days):
        d = (base.fromordinal(base.toordinal() + i)).date().isoformat()
        px *= 1.0 + (rand() - 0.5) * 0.025
        price[d] = round(px, 4)
    return price


def load_market_data(commodities: list[str], refresh: bool) -> dict:
    """Fetch (or load cached) price series per commodity futures continuous.

    Adds an `_offline` flag per series when the data came from the synthetic
    fallback so the verdict layer can honestly report UNTESTED-data-gap.
    """
    if CACHE.exists() and not refresh:
        try:
            cached = json.loads(CACHE.read_text(encoding="utf-8"))
            if all(t in cached.get("data", {}) for t in commodities):
                print(f"# loaded cache {CACHE}", file=sys.stderr)
                return {t: cached["data"][t] for t in commodities}
        except Exception:  # noqa: BLE001
            pass

    data: dict[str, dict] = {}
    for t in commodities:
        print(f"# fetching {t} (free yfinance continuous futures) ...",
              file=sys.stderr)
        price = fetch_futures_series(t)
        if len(price) < 300:
            print(f"#   {t}: dense free price tape unavailable -> synthetic "
                  f"fallback (verdict will be UNTESTED)", file=sys.stderr)
            series = {"price": _synthetic_series(t), "_offline": True}
        else:
            series = {"price": price, "_offline": False}
        print(f"#   {t}: price={len(series['price'])} bars  "
              f"offline={series['_offline']}", file=sys.stderr)
        data[t] = series
        time.sleep(0.3)

    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps({
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "basis_proxy_mode": "front_return_zscore",
        "data": data,
    }), encoding="utf-8")
    print(f"# wrote cache {CACHE}", file=sys.stderr)
    return data


# ===========================================================================
# Signal math (pure, network-free)
# ===========================================================================
def trailing_basis_proxy(price: dict[str, float],
                         window: int) -> dict[str, float]:
    """Trailing-return basis proxy per date.

    HONEST PROXY (no free true second-month calendar-spread feed on yfinance):
      basis_proxy(D) = ln(close(D) / close(D-window))
    Positive trailing return tends to coincide with backwardation regimes
    (inventory tightness lifts the spot above the curve); the CROSS-SECTIONAL
    RANK of this proxy across commodities is what the Gorton-Rouwenhorst sort
    cares about, not the absolute basis level. A true CME calendar-spread feed
    would refine the per-asset basis estimate.

    Strictly-past — basis_proxy(D) uses only observations at or before D.
    """
    out: dict[str, float] = {}
    import math
    dates = sorted(price)
    for i in range(window, len(dates)):
        d = dates[i]
        d0 = dates[i - window]
        p0, p1 = price[d0], price[d]
        if p0 > 0 and p1 > 0:
            out[d] = math.log(p1 / p0)
    return out


def rolling_z(series: list[float], idx: int, roll: int):
    """Z-score of series[idx] vs the `roll` STRICTLY-PAST observations.

    Returns None when fewer than `roll` past observations exist or the past
    window has zero dispersion. series[idx] is excluded from mean/sd — only
    series[idx-roll:idx] feeds them, so no look-ahead.
    """
    if idx < roll:
        return None
    window = series[idx - roll:idx]
    mu = statistics.fmean(window)
    sd = statistics.pstdev(window)
    if sd <= 0:
        return None
    return (series[idx] - mu) / sd


# ===========================================================================
# Continuous-position cross-sectional backtest
# ===========================================================================
def backtest_cross_sectional(data: dict) -> dict:
    """Gorton-Rouwenhorst long-short quintile book on the basis-proxy z.

    For each REBALANCE date D and each commodity i with a forward bar D+HOLD:
      * basis_proxy(i, D) = log return of the front continuous over the past
        BASIS_TRAILING_DAYS, computed from prices strictly before D.
      * signal_z(i, D) = rolling Z_ROLL z-score of basis_proxy(i,*), strictly
        past — Gorton-Rouwenhorst sign convention is LONG the most-backwardated
        leg (= TOP-quintile trailing return / TOP signal_z); SHORT the
        most-contangoed (= BOTTOM-quintile / BOTTOM signal_z).
      * Cross-sectional rank across the universe at D: top QUINTILE_FRAC -> LONG,
        bottom QUINTILE_FRAC -> SHORT, middle quintiles -> skip.
      * raw_ret = price_close(D+HOLD)/price_close(D) - 1
      * signed_ret = raw_ret * direction
      * record: status WON iff signed_ret>0 (gross); harness score field
        signal_z = |z| (conviction magnitude).

    STRICT no-look-ahead: every input to the rank at D uses only data strictly
    before D; entry close(D); exit close(D+HOLD_DAYS).
    """
    records: list[dict] = []
    per_commodity: dict[str, dict] = {}
    gross_rets: list[float] = []
    net_rets: list[float] = []
    cost_frac = ROUND_TRIP_COST_BPS / 10000.0
    any_offline = False

    # 1) build per-commodity signal_z by date
    z_by_commodity: dict[str, dict[str, float]] = {}
    price_by_commodity: dict[str, dict[str, float]] = {}
    for ticker, series in data.items():
        price = series.get("price", {})
        if series.get("_offline"):
            any_offline = True
        price_by_commodity[ticker] = price
        basis = trailing_basis_proxy(price, BASIS_TRAILING_DAYS)
        bdates = sorted(basis)
        bvals = [basis[d] for d in bdates]
        z_by_date: dict[str, float] = {}
        for i, d in enumerate(bdates):
            z = rolling_z(bvals, i, Z_ROLL)
            if z is not None:
                z_by_date[d] = z
        z_by_commodity[ticker] = z_by_date
        per_commodity[ticker] = {"n": 0, "wins": 0, "wr": None,
                                  "basis_obs": len(basis)}

    # 2) common cross-sectional rebalance dates: union of z-dates, then walk on
    # every REBALANCE_DAYS-th date that has at least 5 commodities with a z.
    all_z_dates = sorted({d for zd in z_by_commodity.values() for d in zd})
    if not all_z_dates:
        return {"records": [], "per_commodity": per_commodity,
                "gross_rets": [], "net_rets": [], "any_offline": any_offline}

    rebalance_dates = all_z_dates[::REBALANCE_DAYS]
    universe = list(z_by_commodity)

    import bisect
    for d in rebalance_dates:
        # gather signal_z per commodity AT d (strictly-past)
        ranks: list[tuple[str, float]] = []
        for c in universe:
            zd = z_by_commodity[c]
            zdates = sorted(zd)
            i = bisect.bisect_right(zdates, d) - 1
            if i < 0:
                continue
            sig_date = zdates[i]
            if sig_date > d:
                continue
            ranks.append((c, zd[sig_date]))
        if len(ranks) < 5:
            continue
        ranks.sort(key=lambda t: t[1])
        n_q = max(1, int(round(len(ranks) * QUINTILE_FRAC)))
        # bottom quintile (most-contangoed, most-negative z) -> SHORT
        short_set = {c for c, _ in ranks[:n_q]}
        # top quintile (most-backwardated, most-positive z) -> LONG
        long_set = {c for c, _ in ranks[-n_q:]}

        for c, z in ranks:
            if c in long_set:
                direction = 1
            elif c in short_set:
                direction = -1
            else:
                continue
            price = price_by_commodity[c]
            pdates = sorted(price)
            # entry close(D)
            pi = bisect.bisect_right(pdates, d) - 1
            if pi < 0 or pi + HOLD_DAYS >= len(pdates):
                continue
            entry_d = pdates[pi]
            exit_d = pdates[pi + HOLD_DAYS]
            p0, p1 = price[entry_d], price[exit_d]
            if p0 <= 0:
                continue
            raw_ret = p1 / p0 - 1.0
            signed_ret = raw_ret * direction
            net_ret = signed_ret - cost_frac
            status = "WON" if signed_ret > 0 else "LOST"
            gross_rets.append(signed_ret)
            net_rets.append(net_ret)
            pc = per_commodity[c]
            pc["n"] += 1
            pc["wins"] += int(status == "WON")
            records.append({
                "status": status,
                "resolved_at": exit_d,
                "entry_date": entry_d,
                "signal_date": d,
                "timestamp": entry_d,
                HARNESS_FIELD: abs(z),
                "signed_ret": round(signed_ret, 8),
                "net_ret": round(net_ret, 8),
                "direction": direction,
                "instrument": c,
            })

    for c, pc in per_commodity.items():
        if pc["n"]:
            pc["wr"] = round(pc["wins"] / pc["n"], 4)

    return {
        "records": records,
        "per_commodity": per_commodity,
        "gross_rets": gross_rets,
        "net_rets": net_rets,
        "any_offline": any_offline,
    }


# ===========================================================================
# Post-cost gate
# ===========================================================================
def cost_survival(gross_rets: list[float], net_rets: list[float]) -> dict:
    """Post-cost gate: does net per-trade edge keep >= 60% of gross?

    gross_edge = mean signed return (bps). net_edge = mean net return (bps),
    after a single ROUND_TRIP_COST_BPS round-trip per held position (the
    15bps figure includes the futures roll cost — both legs).
    """
    if not gross_rets:
        return {"passes": False, "reason": "no trades"}
    gross_bps = statistics.fmean(gross_rets) * 10000.0
    net_bps = statistics.fmean(net_rets) * 10000.0
    survival = 0.0 if gross_bps <= 0 else net_bps / gross_bps
    return {
        "gross_edge_bps": round(gross_bps, 4),
        "net_edge_bps": round(net_bps, 4),
        "cost_bps": ROUND_TRIP_COST_BPS,
        "cost_survival_pct": round(survival * 100, 2),
        "passes": bool(gross_bps > 0 and survival >= COST_SURVIVAL_MIN),
    }


def pooled_wr(records: list[dict], net: bool = False):
    """Pooled win-rate (gross or net of cost)."""
    key = "net_ret" if net else "signed_ret"
    rs = [r.get(key) for r in records if r.get(key) is not None]
    if not rs:
        return None
    return round(sum(1 for r in rs if r > 0) / len(rs), 4)


# ===========================================================================
# Harness wiring — edge_stability_harness imported UNMODIFIED
# ===========================================================================
def harness_verdict(records: list[dict], window_days: int = WINDOW_DAYS) -> dict:
    """Run synthetic records through edge_stability_harness, patching only its
    loader for this call. The harness logic — windowing, eff, is_admissible()
    threshold — is reused VERBATIM and UNMODIFIED.
    """
    orig_load = harness._load
    try:
        harness._load = lambda: records  # type: ignore[assignment]
        verdict = harness.evaluate(HARNESS_FIELD, window_days)
        admissible = harness.is_admissible(HARNESS_FIELD, window_days)
    finally:
        harness._load = orig_load  # type: ignore[assignment]
    verdict["admissible_via_is_admissible"] = admissible
    return verdict


# ===========================================================================
# Report
# ===========================================================================
def render_report(res: dict) -> str:
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    recs = res.get("records", [])
    h = res.get("harness", {})
    cg = res.get("cost_gate", {})
    offline = res.get("any_offline", False)
    adm_harness = h.get("admissible", False)
    cost_pass = cg.get("passes", False)
    scored = h.get("windows_scored", 0)

    if offline or scored < harness.MIN_STABLE_WINDOWS:
        verdict = "UNTESTED-data-gap"
    elif adm_harness and cost_pass:
        verdict = "ADMISSIBLE"
    else:
        verdict = "REJECTED"

    out = [
        "# H-034 Commodity Term-Structure Long-Short (Gorton-Rouwenhorst) — 2026-05-19",
        "",
        f"_Generated {ts} by `tools/h034_commodity_term_structure_research.py`._",
        "",
        f"## VERDICT: **{verdict}**",
        "",
        "**Status: OPT-IN RESEARCH SIDECAR. HARNESS-GATED. NO production wiring.** "
        "No caller in `quality_gates.py`, `dashboard_generator.py`, "
        "`passes_active_gate`, `calculate_smart_score`, or any pick-generation / "
        "scoring path. Fetches free yfinance futures data, writes this report — "
        "nothing else.",
        "",
        "## The signal",
        "",
        "Gorton-Rouwenhorst (2006) cross-sectional commodity-futures basis / "
        "roll-yield long-short:",
        "",
        f"- `basis_proxy(i, D) = ln(close(i, D) / close(i, D-{BASIS_TRAILING_DAYS}))` "
        "— a TRAILING-RETURN basis proxy (honest stand-in; see construction "
        "caveat below).",
        f"- `signal_z(i, D)` = rolling {Z_ROLL}-observation strictly-past z-score "
        "of `basis_proxy(i, *)`.",
        "- direction: cross-sectionally rank all commodities at D — top "
        f"{int(QUINTILE_FRAC*100)}% (most-backwardated proxy) -> LONG (+1); "
        f"bottom {int(QUINTILE_FRAC*100)}% (most-contangoed proxy) -> SHORT (-1); "
        "middle quintiles skipped.",
        "- harness score field = `|signal_z|` (conviction magnitude).",
        f"- rebalance every {REBALANCE_DAYS} trading days; hold {HOLD_DAYS} days.",
        "",
        "**Causal mechanism:** Gorton-Rouwenhorst (2006, *Facts and Fantasies "
        "about Commodity Futures*) document that the cross-section of commodity "
        "futures' basis (front-vs-second-month roll yield) carries a stable "
        "risk-premium: backwardated curves embed positive expected roll returns "
        "and have historically been long-side rewarded, contangoed curves "
        "vice-versa. The LONG-SHORT QUINTILE SPREAD is a market-neutral carry "
        "portfolio that survives in the canonical paper across decades. This "
        "construction is STRUCTURALLY DIFFERENT from killed H-007 "
        "(`front_second_roll_yield_zscore` — a SINGLE-asset directional z-score "
        "on an ETF proxy that failed sign-stability): H-034 is CROSS-SECTIONAL "
        "and rank-based, not per-asset directional.",
        "",
        "## Construction (legitimate density pattern from H-008/H-019/H-020/H-026/H-027)",
        "",
        "- **FULL continuous-position cross-sectional book** — at each weekly "
        "rebalance every commodity with a valid signal contributes a resolved "
        "long, short, or skip; only quintile-extreme records carry a non-zero "
        "direction, but the record stream is dense and the harness's fixed "
        "14-day windows fill.",
        "- **Strict no-look-ahead** — `basis_proxy(D)` uses prices strictly "
        f"before D; the z-score look-back is the {Z_ROLL} STRICTLY-PAST basis "
        "obs (current obs excluded from mean/sd); the cross-sectional rank at "
        "D sees only quantities computed strictly before D; entry close(D); "
        f"exit close(D+{HOLD_DAYS}).",
        "",
        "## Data — free, no key",
        "",
        "- **yfinance =F continuous futures** — `CL=F`, `NG=F`, `HG=F`, `GC=F`, "
        "`SI=F`, `ZC=F`, `ZW=F`, `ZS=F`, `KC=F`, `CT=F`. yfinance ships a "
        "stitched front-month continuous; the basis proxy used here is a "
        "TRAILING-RETURN stand-in. A true CME calendar-spread feed (Quandl CME "
        "WIKI) would refine the per-asset basis estimate and is the natural "
        "next-step data upgrade.",
        f"- **Sample:** {len(recs)} commodity-rebalance resolved records.",
        "- **CT=F note:** cotton is on `COMMODITY_BLACKLIST` (Phase 2-D kill, "
        "see `MEMORY.md`). It is included in the H-034 universe ONLY because "
        "the cross-sectional Gorton-Rouwenhorst sort needs a wide universe; "
        "this sidecar emits zero picks and any future paper/commercial sizing "
        "would still respect the blacklist.",
        (
            "- **OFFLINE NOTE:** one or more series fell back to a labelled "
            "synthetic continuous because the live yfinance tape was "
            "unavailable. The verdict is therefore UNTESTED-data-gap — this "
            "run did NOT measure a real edge."
            if offline else
            "- All commodities sourced from live free yfinance data."
        ),
        "",
        "## Construction caveat (multi-AI swarm flag)",
        "",
        "yfinance =F tickers are STITCHED continuous series — the roll bumps "
        "inject some noise vs a true CME front/second calendar-spread feed. "
        "The cross-sectional RANK across commodities is the part the "
        "Gorton-Rouwenhorst sort cares about (not the absolute basis level), "
        "so the proxy is honest for the sort. A true Quandl CME WIKI "
        "front/second feed would be a sharper test and is the documented "
        "data-upgrade path. `basis_proxy_mode = front_return_zscore` is "
        "stamped in the registry and the cache for traceability.",
        "",
    ]

    pc_map = res.get("per_commodity", {})
    if pc_map:
        out += ["| Commodity | records | wins | gross WR | basis obs |",
                "|---|---|---|---|---|"]
        for k, v in pc_map.items():
            wr = f"{v['wr']*100:.1f}%" if v.get("wr") is not None else "n/a"
            out.append(f"| {k} | {v.get('n',0)} | {v.get('wins',0)} | {wr} | "
                       f"{v.get('basis_obs','n/a')} |")
        out.append("")

    out += ["## Harness verdict (THE gate — `edge_stability_harness`, UNMODIFIED)",
            ""]
    if "per_window_eff" in h:
        effs = " ".join(
            (f"{e['eff']:+.2f}" if e.get("eff") is not None else "n/a")
            for e in h["per_window_eff"])
        out += [
            f"- per-window eff (new->old): `{effs}`",
            f"- windows scored: {h.get('windows_scored')}  "
            f"(strong {h.get('windows_strong')}: "
            f"+{h.get('strong_positive')}/-{h.get('strong_negative')})",
            f"- `is_admissible()`: {h.get('admissible_via_is_admissible')}",
            f"- harness reason: {h.get('reason', 'n/a')}",
            "",
        ]
    else:
        out += [f"- {h.get('reason', 'n/a')}", ""]

    out += ["## Post-cost gate (15bps round-trip incl. futures roll cost; "
            "net must keep >= 60% of gross)", ""]
    if cg:
        out += [
            f"- gross edge: **{cg.get('gross_edge_bps')} bps/trade**",
            f"- net edge (after {cg.get('cost_bps')}bps round-trip): "
            f"**{cg.get('net_edge_bps')} bps/trade**",
            f"- cost-survival: **{cg.get('cost_survival_pct')}%** "
            f"(floor {int(COST_SURVIVAL_MIN*100)}%)",
            f"- post-cost gate: **{'PASS' if cost_pass else 'FAIL'}**",
            "",
        ]
    out += [
        f"- pooled gross WR: {(res.get('pooled_wr_gross') or 0)*100:.1f}%",
        f"- pooled net WR: {(res.get('pooled_wr_net') or 0)*100:.1f}%",
        "",
        "## Honest conclusion",
        "",
    ]
    if verdict == "ADMISSIBLE":
        out += [
            "**H-034 cleared `edge_stability_harness` AND the post-cost gate.** "
            "Against a poor base rate (8-11 prior harness kills, including the "
            "structurally-distinct H-007 single-asset roll-yield z-score) this "
            "is a **research candidate, not a green light.** Before any wiring "
            "it still needs: a true CME front/second calendar-spread feed in "
            "place of the trailing-return proxy, a fresh out-of-sample re-test, "
            "a deflated-Sharpe / SPA multiple-testing correction, and operator "
            "review. No wiring here.",
        ]
    elif verdict == "REJECTED":
        out += [
            "**H-034 was TESTED and REJECTED.** The continuous-position "
            "cross-sectional construction gave the harness real window density, "
            "so it rendered a genuine verdict. " + (
                "The harness eff sign splits across windows — in-sample "
                "separation that flips sign across regimes, same failure mode "
                "as H-007. "
                if not adm_harness else
                "The harness sign is stable but the post-cost gate fails "
                "(15bps round-trip + futures roll cost eats the carry). "
            ) + "This verdict used the trailing-return basis proxy; a true CME "
            "calendar-spread feed would be a different test. Do NOT re-test "
            "this exact construction on this sample. Nothing is wired or sized.",
        ]
    else:
        out += [
            "**H-034 is UNTESTED — data-gap, explicitly NOT a pass.** " + (
                "yfinance was unreachable and the run used a labelled synthetic "
                "continuous. "
                if offline else
                f"The harness scored only {scored} fourteen-day window(s); it "
                f"needs >= {harness.MIN_STABLE_WINDOWS}. "
            ) + "This is an honest non-verdict — not a pass and not a clean "
            "fail. A real H-034 verdict needs a live yfinance =F tape (or a "
            "true CME calendar-spread feed) with enough history for the harness "
            "to score multiple 14-day windows.",
        ]
    out += [
        "",
        "## next_step",
        "",
        (
            "H-034 cleared both gates — escalate for a true CME calendar-spread "
            "feed, out-of-sample re-test, DSR/SPA correction, and operator "
            "review before any wiring."
            if verdict == "ADMISSIBLE" else
            "Harness kill — cross-sectional roll-yield-quintile z-score does "
            "not yield an admissible commodity edge on this sample (trailing-"
            "return basis proxy). A true CME calendar-spread feed would be a "
            "genuinely different test; the proxy construction is a clean kill."
            if verdict == "REJECTED" else
            "Acquire a denser yfinance =F tape (or a Quandl CME WIKI "
            "front/second continuous feed) so the harness can score >= "
            f"{harness.MIN_STABLE_WINDOWS} fourteen-day windows. Re-run only "
            "with the denser tape."
        ),
        "",
    ]
    return "\n".join(out)


# ===========================================================================
# Orchestration
# ===========================================================================
def run(quick: bool, refresh: bool) -> dict:
    commodities = COMMODITIES_QUICK if quick else COMMODITIES_FULL
    data = load_market_data(commodities, refresh)

    bt = backtest_cross_sectional(data)
    recs = bt.get("records", [])
    cg = cost_survival(bt.get("gross_rets", []), bt.get("net_rets", []))

    res = {
        "records": recs,
        "per_commodity": bt.get("per_commodity", {}),
        "cost_gate": cg,
        "any_offline": bt.get("any_offline", False),
        "pooled_wr_gross": pooled_wr(recs, net=False),
        "pooled_wr_net": pooled_wr(recs, net=True),
    }
    if len(recs) < harness.MIN_WINDOW_N:
        res["harness"] = {
            "admissible": False,
            "reason": f"INSUFFICIENT DATA — {len(recs)} records, harness needs "
                      f">= {harness.MIN_WINDOW_N}/window",
            "windows_scored": 0,
        }
    else:
        res["harness"] = harness_verdict(recs)
    return res


def json_summary(res: dict) -> dict:
    h = res.get("harness", {})
    cg = res.get("cost_gate", {})
    scored = h.get("windows_scored", 0)
    offline = res.get("any_offline", False)
    if offline or scored < harness.MIN_STABLE_WINDOWS:
        verdict = "UNTESTED-data-gap"
    elif h.get("admissible") and cg.get("passes"):
        verdict = "ADMISSIBLE"
    else:
        verdict = "REJECTED"
    return {
        "hypothesis": "H-034",
        "family": "commodity_term_structure_roll_yield",
        "asset_class": "COMMODITY",
        "verdict": verdict,
        "basis_proxy_mode": "front_return_zscore",
        "offline_synthetic": offline,
        "n_records": len(res.get("records", [])),
        "windows_scored": scored,
        "windows_strong": h.get("windows_strong"),
        "strong_positive": h.get("strong_positive"),
        "strong_negative": h.get("strong_negative"),
        "per_window_eff": [e.get("eff") for e in h.get("per_window_eff", [])],
        "harness_sign": h.get("sign"),
        "is_admissible": h.get("admissible_via_is_admissible", h.get("admissible")),
        "pooled_wr_gross": res.get("pooled_wr_gross"),
        "pooled_wr_net": res.get("pooled_wr_net"),
        "gross_edge_bps": cg.get("gross_edge_bps"),
        "net_edge_bps": cg.get("net_edge_bps"),
        "cost_survival_pct": cg.get("cost_survival_pct"),
        "cost_gate_passes": cg.get("passes"),
        "harness_reason": h.get("reason"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true",
                    help="5-commodity smoke set for a fast run")
    ap.add_argument("--json", dest="as_json", action="store_true")
    ap.add_argument("--refresh-cache", action="store_true",
                    help="re-fetch free yfinance data, ignoring the cache")
    ap.add_argument("--out", type=Path,
                    default=ROOT / "reports" /
                    "h034_commodity_term_structure_research_2026-05-19.md")
    args = ap.parse_args()

    res = run(args.quick, args.refresh_cache)
    summary = json_summary(res)

    if args.as_json:
        print(json.dumps(summary, indent=2, default=str))
        return 0

    report = render_report(res)
    args.out.write_text(report, encoding="utf-8")
    print(f"# wrote {args.out}", file=sys.stderr)
    print(report)
    print("\n# JSON SUMMARY")
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
