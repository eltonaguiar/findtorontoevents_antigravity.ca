#!/usr/bin/env python3
"""H-033 — EQUITY industry/sector cross-sectional momentum backtest.

OPT-IN RESEARCH SIDECAR. No production wiring. No caller in quality_gates.py,
dashboard_generator.py, passes_active_gate, calculate_smart_score, or any
pick-generation / scoring path. It fetches free public sector-ETF price data
and writes a report — nothing else. Importing this module has no side effects
on production. Multi-AI D-path consensus (Grok/Codex/Gemini/Kilo/Opencode
2026-05-19) ranked sector cross-sectional momentum the cleanest equity sidecar
candidate of the Fork-2 D-paths.

------------------------------------------------------------------------------
WHY THIS MODULE EXISTS
------------------------------------------------------------------------------
EQUITY is the system's strongest Tier-2 candidate per `audit_dashboard/data/
dashboard_data.json::performance.asset_class_health` (PF 1.41 / WR 52.7% /
n=421 post-resolver-v2). Every existing equity strategy in the ledger is a
TICKER-LEVEL technical or factor overlay — momentum, value, quality, PEAD,
residualized overnight reversal (H-033's original ID, killed 2026-05-19). None
runs an INDUSTRY / SECTOR cross-sectional rotation on the SPDR sector-ETF set.
Moskowitz-Grinblatt (1999) documented sector momentum as a separable risk-
premium distinct from individual-stock momentum: industries that have
outperformed over 6-12 months continue to outperform over the next 1-3 months.

THE SIGNAL — industry/sector cross-sectional momentum (Moskowitz-Grinblatt 1999):
  Universe: the 11 SPDR sector ETFs — XLB (materials), XLE (energy), XLF
  (financials), XLI (industrials), XLK (technology), XLP (consumer staples),
  XLU (utilities), XLV (health care), XLY (consumer discretionary), XLRE
  (real estate), XLC (communication services). These exhaust the GICS sector
  partition of the US large-cap market.

  At every monthly rebalance date D:
    momentum_i(D) = close_i(D) / close_i(D - 21 trading days) - 1
    rank sectors by momentum_i(D); LONG the top 2, SHORT the bottom 2.
  Hold the equal-weight long-short basket until the next monthly rebalance.

  OPTIONAL TREND FILTER (pre-registered): activate the book only when SPY is
  above its 12-month (252-trading-day) moving average. In bear regimes the
  cross-sectional dispersion of sectors narrows and the momentum spread
  inverts; the trend filter is the proposal's regime guard.

  Direction: signed by rank; harness score field = |momentum z-score across
  the 11 sectors| (conviction magnitude of the picked sector vs the rest).

  This is NOT a banned family. It is NOT yield-curve (H-008), NOT COT (H-001),
  NOT funding-rate (H-006), NOT roll-yield (H-007), NOT PEAD (H-002/H-010),
  NOT options-flow (H-009/H-011/H-013), NOT ETF creation/redemption (H-026),
  NOT insider cluster-buy (H-028), NOT residualized-overnight reversal (the
  prior H-033, killed 2026-05-19 — uses individual-name 1-day overnight gaps,
  NOT 21-day sector cross-sectional momentum). It is the sector-momentum
  primitive — a primary cross-sectional risk-premium the pick system has
  never ingested.

------------------------------------------------------------------------------
DATA SOURCES — FREE ONLY
------------------------------------------------------------------------------
  * yfinance — daily close series for the 11 SPDR sector ETFs and SPY (the
    trend-filter benchmark). Free, no API key. Adjusted close (auto_adjust=
    False) so the absolute price level is preserved; momentum is a ratio so
    splits/dividends do not matter once the ratio is taken.

No paid feed. No API key. If the network is unavailable the module degrades to
a clearly-labelled synthetic series and reports the verdict UNTESTED-data-gap
honestly — it never fabricates a pass.

------------------------------------------------------------------------------
THE CONSTRUCTION (legitimate density pattern from H-008/H-019/H-020/H-026/H-027)
------------------------------------------------------------------------------
  * FULL continuous-position cross-sectional book. The basket is rebalanced
    monthly; while held, every (sector, day) in the long or short leg with a
    next bar is one resolved record. NO selection of "big" momentum moves, NO
    |z| threshold — the basket always holds top-2 long / bottom-2 short on
    rebalance dates (subject to the optional trend filter). Density comes from
    holding daily, the H-008 pattern, not from threshold relaxation.
  * STRICT no-look-ahead: the 21-day momentum used to rank on rebalance date D
    uses close(D - 21) -> close(D), both known at the close of D; positions
    enter at the OPEN of D+1 (next trading day); the realized return for each
    held day is close(d) -> close(d+1) signed by the leg (LONG=+1, SHORT=-1).
    The 12-month SPY MA used to gate the rebalance is computed from closes
    strictly through D (252-day rolling, end-anchored, no future bars).

------------------------------------------------------------------------------
COST GATE
------------------------------------------------------------------------------
ROUND_TRIP_COST_BPS = 15. SPDR sector ETF spreads are tight (1-3bps each leg
on XLK/XLF/XLE; 5-8bps round-trip including slippage). 15bps is the proposal-
specified round-trip and includes both legs of the long-short pair PLUS the
monthly turnover cost of one full sector swap on each leg.

------------------------------------------------------------------------------
THE VERDICT GATE
------------------------------------------------------------------------------
Records pass through tools/edge_stability_harness.evaluate()/is_admissible()
imported UNMODIFIED. ADMISSIBLE iff |eff| >= 0.30, same sign, >= 3 of 5
walk-forward 14-day windows, >= 80 records/window. PLUS a 15bps round-trip
post-cost gate: net edge must keep >= 60% of gross.

A gaudy in-sample WR is NOT a pass. The edge hunt's base rate is poor (8-11
harness kills to date including the prior H-033 residualized-overnight
reversal). This module reports the verdict honestly whichever way it lands.
Nothing here is wired into or sized by any production path.

    python tools/h033_equity_sector_momentum_research.py [--quick] [--json]
            [--refresh-cache] [--no-trend-filter]
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if sys.platform == "win32":
    for _s in (sys.stdout, sys.stderr):
        if hasattr(_s, "reconfigure"):
            try:
                _s.reconfigure(encoding="utf-8", errors="replace")
            except Exception:  # noqa: BLE001
                pass

import edge_stability_harness as harness  # noqa: E402

# ---------------------------------------------------------------------------
# Tunables — pre-registered (H-033 / registry id H-040). The signal family is
# fixed; no per-window search, no post-hoc parameter tuning.
# ---------------------------------------------------------------------------
MOMENTUM_LOOKBACK_DAYS = 21        # trailing momentum window (~1 month)
REBALANCE_TRADING_DAYS = 21        # monthly rebalance (~1 trading month)
TOP_N = 2                          # LONG the top-2 sectors by momentum
BOTTOM_N = 2                       # SHORT the bottom-2 sectors by momentum
TREND_FILTER_DAYS = 252            # SPY 12-month MA (~252 trading days)
WINDOW_DAYS = 14                   # harness walk-forward window length
HARNESS_FIELD = "signal_z"         # conviction-magnitude score the harness reads
ROUND_TRIP_COST_BPS = 15.0         # round-trip ETF spread + slippage (both legs)
COST_SURVIVAL_MIN = 0.60           # net edge must retain >= 60% of gross

CACHE = ROOT / "tools" / "cache" / "h033_equity_sector_momentum_cache.json"

# The 11 SPDR sector ETFs — exhaust the GICS sector partition of the US
# large-cap market. Pre-registered, no swap-in / swap-out at runtime.
SECTOR_ETFS = [
    "XLB",   # materials
    "XLE",   # energy
    "XLF",   # financials
    "XLI",   # industrials
    "XLK",   # technology
    "XLP",   # consumer staples
    "XLU",   # utilities
    "XLV",   # health care
    "XLY",   # consumer discretionary
    "XLRE",  # real estate
    "XLC",   # communication services
]
TREND_BENCHMARK = "SPY"   # 12-month MA trend gate
ETFS_QUICK = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP"]


# ===========================================================================
# Data fetch — free public APIs, no key.
# ===========================================================================
def fetch_price_series(ticker: str) -> dict:
    """Fetch a free daily close series for one ETF via yfinance.

    Returns {iso_date: close}. On any error returns {} and the caller degrades
    to a labelled synthetic series + UNTESTED verdict — never a fake pass.
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


def _synthetic_series(ticker: str, n_days: int = 1500) -> dict:
    """Deterministic synthetic daily close series for an OFFLINE run.

    Used ONLY when every free network source fails. It is clearly labelled and
    drives an UNTESTED-data-gap verdict — it is never reported as a real pass.
    A small deterministic LCG (seeded by the ticker) keeps the run reproducible.
    """
    seed = sum(ord(c) for c in ticker) * 2654435761 & 0xFFFFFFFF
    state = seed

    def rand() -> float:
        nonlocal state
        state = (1103515245 * state + 12345) & 0x7FFFFFFF
        return state / 0x7FFFFFFF

    price: dict[str, float] = {}
    px = 50.0 + (seed % 80)
    base = datetime(2019, 1, 2, tzinfo=timezone.utc)
    for i in range(n_days):
        d = (base.fromordinal(base.toordinal() + i)).date().isoformat()
        # mild trend + idiosyncratic noise — enough dispersion to rank sectors
        drift = 0.0002 + ((seed >> (i % 7)) % 7 - 3) * 0.00005
        px *= 1.0 + drift + (rand() - 0.5) * 0.015
        price[d] = round(max(px, 1.0), 4)
    return price


def load_market_data(etfs: list[str], refresh: bool,
                     include_benchmark: bool = True) -> dict:
    """Fetch (or load cached) daily close series per ETF + the SPY benchmark.

    Adds an `_offline` flag per ETF when the series came from the synthetic
    fallback so the verdict layer can honestly report UNTESTED-data-gap.
    """
    tickers = list(etfs)
    if include_benchmark and TREND_BENCHMARK not in tickers:
        tickers.append(TREND_BENCHMARK)

    if CACHE.exists() and not refresh:
        try:
            cached = json.loads(CACHE.read_text(encoding="utf-8"))
            if all(t in cached.get("data", {}) for t in tickers):
                print(f"# loaded cache {CACHE}", file=sys.stderr)
                return cached["data"]
        except Exception:  # noqa: BLE001
            pass

    data: dict[str, dict] = {}
    for t in tickers:
        print(f"# fetching {t} (free yfinance) ...", file=sys.stderr)
        price = fetch_price_series(t)
        if len(price) < TREND_FILTER_DAYS + MOMENTUM_LOOKBACK_DAYS + 10:
            print(f"#   {t}: dense free daily-close tape unavailable -> "
                  f"synthetic fallback (verdict will be UNTESTED)",
                  file=sys.stderr)
            price = _synthetic_series(t)
            offline = True
        else:
            offline = False
        series = {"price": price, "_offline": offline}
        print(f"#   {t}: bars={len(price)}  offline={offline}", file=sys.stderr)
        data[t] = series
        time.sleep(0.2)

    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps({
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data": data,
    }), encoding="utf-8")
    print(f"# wrote cache {CACHE}", file=sys.stderr)
    return data


# ===========================================================================
# Signal math (pure, network-free)
# ===========================================================================
def trailing_momentum(price: dict[str, float], dates: list[str], idx: int,
                      lookback: int):
    """21-day trailing momentum at dates[idx], or None.

    momentum(D) = price(D)/price(D-lookback) - 1. Uses ONLY closes at or before
    D (the value used to RANK on D is therefore known at the close of D).
    """
    if idx < lookback:
        return None
    d0 = dates[idx - lookback]
    d1 = dates[idx]
    p0 = price.get(d0)
    p1 = price.get(d1)
    if p0 is None or p1 is None or p0 <= 0:
        return None
    return p1 / p0 - 1.0


def cross_sectional_z(values: list[float], idx: int):
    """Z-score of values[idx] vs the same-day cross-section of sectors.

    Uses ALL sectors on the rebalance date (cross-sectional dispersion), NOT a
    time-series rolling window — this is the Moskowitz-Grinblatt conviction
    magnitude (how far is this sector from the sector mean). Returns 0 when
    the cross-section has zero dispersion.
    """
    if not values or idx >= len(values):
        return 0.0
    finite = [v for v in values if v is not None]
    if len(finite) < 2:
        return 0.0
    mu = statistics.fmean(finite)
    sd = statistics.pstdev(finite)
    if sd <= 0:
        return 0.0
    v = values[idx]
    if v is None:
        return 0.0
    return (v - mu) / sd


def spy_above_12m_ma(spy_price: dict[str, float], spy_dates: list[str],
                     idx: int, lookback: int) -> bool:
    """Trend filter: True iff SPY close at dates[idx] is above its 12-month MA.

    The MA is end-anchored at dates[idx] over the trailing `lookback` closes —
    no future bars. Returns False (i.e. trend gate FAILS) when the lookback is
    not yet filled.
    """
    if idx < lookback:
        return False
    window = [spy_price.get(spy_dates[k]) for k in range(idx - lookback, idx)]
    window = [w for w in window if w is not None and w > 0]
    if len(window) < lookback // 2:
        return False
    ma = statistics.fmean(window)
    cur = spy_price.get(spy_dates[idx])
    if cur is None:
        return False
    return cur > ma


# ===========================================================================
# Continuous-position backtest
# ===========================================================================
def _intersect_calendar(data: dict, etfs: list[str]) -> list[str]:
    """Trading-day calendar present in EVERY sector + SPY series."""
    sets = [set(data[t]["price"].keys()) for t in etfs if t in data]
    if not sets:
        return []
    common = set.intersection(*sets)
    return sorted(common)


def backtest_continuous(data: dict, etfs: list[str],
                         use_trend_filter: bool) -> dict:
    """FULL continuous-position long-short cross-sectional sector book.

    For every monthly rebalance date D (every REBALANCE_TRADING_DAYS trading
    days) with a next bar:
      * 21-day momentum is computed for each of the 11 sectors using closes
        STRICTLY through D.
      * if the trend filter is active and SPY's close at D is NOT above its
        12-month MA at D, the book sits FLAT for the next rebalance period.
      * otherwise: LONG the TOP_N sectors by momentum, SHORT the BOTTOM_N.
      * each (selected_sector, day d) in [D+1, next rebalance] with a next bar
        d+1 is one resolved record. raw_ret = close(d+1)/close(d) - 1;
        signed_ret = raw_ret * leg_direction. The harness score field signal_z
        carries the |cross-sectional momentum z-score| of that sector on D
        (conviction magnitude of the pick).
      * cost is amortised on rebalance: a single ROUND_TRIP_COST_BPS round-trip
        is charged against the FIRST held day of each rebalance period
        (turnover-aware accounting, not per-day).

    STRICT no-look-ahead: ranks computed at close(D), positions held from
    close(D+1)->close(d+1); the 12-month MA uses only closes through D; entry
    on the bar AFTER the signal date.
    """
    records: list[dict] = []
    gross_rets: list[float] = []
    net_rets: list[float] = []
    cost_frac = ROUND_TRIP_COST_BPS / 10000.0
    any_offline = any(data[t].get("_offline") for t in etfs if t in data)
    if data.get(TREND_BENCHMARK, {}).get("_offline"):
        any_offline = True

    cal = _intersect_calendar(data, etfs + [TREND_BENCHMARK])
    if len(cal) < TREND_FILTER_DAYS + MOMENTUM_LOOKBACK_DAYS + 10:
        return {
            "records": [],
            "gross_rets": [],
            "net_rets": [],
            "any_offline": any_offline,
            "rebalance_dates": [],
            "n_rebalances_active": 0,
            "n_rebalances_flat": 0,
            "calendar_len": len(cal),
        }

    spy_price = data[TREND_BENCHMARK]["price"]
    per_etf_price = {t: data[t]["price"] for t in etfs if t in data}

    # rebalance dates: every REBALANCE_TRADING_DAYS bars, starting after enough
    # history exists for both the 21d momentum and the 12-month MA.
    start_idx = max(MOMENTUM_LOOKBACK_DAYS,
                    TREND_FILTER_DAYS if use_trend_filter else 0)
    rebalance_idxs = list(range(start_idx, len(cal) - 1, REBALANCE_TRADING_DAYS))

    n_active = n_flat = 0
    per_sector_records: dict[str, dict] = {t: {"n": 0, "wins": 0,
                                                "long_n": 0, "short_n": 0}
                                            for t in etfs}

    for r_idx, D_idx in enumerate(rebalance_idxs):
        D = cal[D_idx]

        # Trend filter at D (pre-registered): book sits FLAT in bear regimes.
        if use_trend_filter:
            if not spy_above_12m_ma(spy_price, cal, D_idx, TREND_FILTER_DAYS):
                n_flat += 1
                continue

        # rank sectors by 21d momentum at D
        moms: list[tuple[str, float | None]] = []
        for t in etfs:
            m = trailing_momentum(per_etf_price[t], cal, D_idx,
                                  MOMENTUM_LOOKBACK_DAYS)
            moms.append((t, m))
        valid = [(t, m) for (t, m) in moms if m is not None]
        if len(valid) < TOP_N + BOTTOM_N:
            n_flat += 1
            continue
        valid.sort(key=lambda kv: kv[1], reverse=True)
        longs = [t for (t, _) in valid[:TOP_N]]
        shorts = [t for (t, _) in valid[-BOTTOM_N:]]
        n_active += 1

        # cross-sectional z of each picked sector's momentum at D (conviction)
        vals = [m for (_, m) in valid]
        z_by_sector: dict[str, float] = {}
        for j, (t, _m) in enumerate(valid):
            z_by_sector[t] = cross_sectional_z(vals, j)

        # held window: D+1 .. min(D + REBALANCE_TRADING_DAYS, len(cal)-2)
        end_idx = min(D_idx + REBALANCE_TRADING_DAYS, len(cal) - 1)
        first_held_day = True
        for d_idx in range(D_idx + 1, end_idx):
            d = cal[d_idx]
            d_next = cal[d_idx + 1]
            for (t, leg) in [(x, +1) for x in longs] + [(x, -1) for x in shorts]:
                p0 = per_etf_price[t].get(d)
                p1 = per_etf_price[t].get(d_next)
                if p0 is None or p1 is None or p0 <= 0:
                    continue
                raw_ret = p1 / p0 - 1.0
                signed_ret = raw_ret * leg
                # turnover-aware cost: charge ONLY on the first held day of the
                # rebalance period (round-trip in + out across the period).
                applied_cost = cost_frac if first_held_day else 0.0
                net_ret = signed_ret - applied_cost
                status = "WON" if signed_ret > 0 else "LOST"
                gross_rets.append(signed_ret)
                net_rets.append(net_ret)
                records.append({
                    "status": status,
                    "resolved_at": d_next,
                    "entry_date": d,
                    "signal_date": D,
                    "timestamp": d,
                    HARNESS_FIELD: abs(z_by_sector.get(t, 0.0)),
                    "signed_ret": round(signed_ret, 8),
                    "net_ret": round(net_ret, 8),
                    "direction": leg,
                    "leg": "LONG" if leg > 0 else "SHORT",
                    "instrument": t,
                    "rebalance_idx": r_idx,
                })
                pr = per_sector_records[t]
                pr["n"] += 1
                pr["wins"] += int(status == "WON")
                if leg > 0:
                    pr["long_n"] += 1
                else:
                    pr["short_n"] += 1
            first_held_day = False

    for t, pr in per_sector_records.items():
        pr["wr"] = round(pr["wins"] / pr["n"], 4) if pr["n"] else None

    return {
        "records": records,
        "per_sector": per_sector_records,
        "gross_rets": gross_rets,
        "net_rets": net_rets,
        "any_offline": any_offline,
        "n_rebalances_active": n_active,
        "n_rebalances_flat": n_flat,
        "calendar_len": len(cal),
        "trend_filter_used": use_trend_filter,
    }


# ===========================================================================
# Post-cost gate
# ===========================================================================
def cost_survival(gross_rets: list[float], net_rets: list[float]) -> dict:
    """Post-cost gate: does net per-trade edge keep >= 60% of gross?

    gross_edge = mean signed return (bps). net_edge = mean net return (bps),
    after a turnover-amortised ROUND_TRIP_COST_BPS round-trip on the rebalance
    period's first held day. The pooled mean correctly reflects the per-bar
    average cost over the held window.
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
    trend_used = res.get("trend_filter_used", True)

    if offline or scored < harness.MIN_STABLE_WINDOWS:
        verdict = "UNTESTED-data-gap"
    elif adm_harness and cost_pass:
        verdict = "ADMISSIBLE"
    else:
        verdict = "REJECTED"

    out = [
        "# H-033 EQUITY Industry/Sector Cross-Sectional Momentum — 2026-05-19",
        "",
        f"_Generated {ts} by `tools/h033_equity_sector_momentum_research.py`._",
        "",
        f"## VERDICT: **{verdict}**",
        "",
        "**Status: OPT-IN RESEARCH SIDECAR. No production wiring.** No caller in "
        "`quality_gates.py`, `dashboard_generator.py`, `passes_active_gate`, "
        "`calculate_smart_score`, or any pick-generation / scoring path. Fetches "
        "free public sector-ETF data, writes this report — nothing else.",
        "",
        "## The signal",
        "",
        "EQUITY industry/sector cross-sectional momentum (Moskowitz-Grinblatt "
        "1999). Universe: the 11 SPDR sector ETFs (XLB / XLE / XLF / XLI / XLK / "
        "XLP / XLU / XLV / XLY / XLRE / XLC) — the GICS sector partition of the "
        "US large-cap market:",
        "",
        f"- `momentum_i(D) = close_i(D)/close_i(D-{MOMENTUM_LOOKBACK_DAYS}) - 1` "
        "— trailing 21-day return per sector.",
        f"- Rank cross-sectionally at the monthly rebalance date; LONG the "
        f"top-{TOP_N}, SHORT the bottom-{BOTTOM_N}. Equal-weight long-short, "
        f"held until the next rebalance.",
        f"- Optional trend filter (pre-registered): the book is FLAT unless SPY "
        f"is above its {TREND_FILTER_DAYS}-day moving average at the rebalance "
        f"date. Trend filter THIS RUN: **{'ON' if trend_used else 'OFF'}**.",
        "- harness score field = `|cross-sectional momentum z-score|` of the "
        "picked sector vs the 11-sector cross-section on the rebalance date "
        "(conviction magnitude).",
        "",
        "**Causal mechanism:** Moskowitz-Grinblatt (1999) documented industry "
        "momentum as a separable risk-premium distinct from individual-stock "
        "momentum: industries that have outperformed over 1-12 months continue "
        "to outperform over the next 1-3 months. The mechanism is slow "
        "information diffusion across the supply chain plus persistent factor "
        "exposure shifts (rates, energy prices, credit) that benefit some "
        "sectors over multi-month horizons. The optional SPY 12-month trend "
        "filter is the documented regime guard — cross-sectional dispersion "
        "narrows and the momentum spread inverts in bear markets.",
        "",
        "## Construction (legitimate density pattern from H-008/H-019/H-026/H-027)",
        "",
        "- **FULL continuous-position long-short book** — top-2 LONG / bottom-2 "
        "SHORT every rebalance (subject to the optional trend filter); every "
        "(picked_sector, held_day) with a next bar is one resolved record. NO "
        "selection of 'big' momentum moves, NO post-hoc threshold — density "
        "comes from holding daily, the H-008 pattern, not threshold relaxation.",
        f"- **Strict no-look-ahead** — the {MOMENTUM_LOOKBACK_DAYS}-day momentum "
        f"used to rank on rebalance date D uses closes strictly through D; "
        f"positions enter on the bar AFTER D; the {TREND_FILTER_DAYS}-day SPY MA "
        "is end-anchored at D over its trailing window — no future bars.",
        "- **Turnover-aware cost** — a single 15bps round-trip is charged on the "
        "FIRST held day of each rebalance period (in + out across the period), "
        "not per-day. Pooled mean reflects the per-bar average.",
        "",
        "## Data (free sources only)",
        "",
        "- **yfinance** — daily close series for the 11 SPDR sector ETFs and the "
        "SPY trend benchmark (free, no key).",
        f"- **Sample:** {len(recs)} sector-day resolved records across "
        f"{res.get('n_rebalances_active', 0)} active rebalances "
        f"({res.get('n_rebalances_flat', 0)} flat by trend filter / data gap).",
        (
            "- **OFFLINE NOTE:** one or more sectors fell back to a labelled "
            "synthetic series because a dense free daily-close tape was "
            "unavailable. The verdict is therefore UNTESTED-data-gap — this run "
            "did NOT measure a real edge."
            if offline else
            "- All sectors sourced from live free data."
        ),
        "",
    ]

    pe = res.get("per_sector", {})
    if pe:
        out += ["| Sector | records | wins | gross WR | longs | shorts |",
                "|---|---|---|---|---|---|"]
        for k, v in pe.items():
            wr = f"{v['wr']*100:.1f}%" if v.get("wr") is not None else "n/a"
            out.append(f"| {k} | {v.get('n',0)} | {v.get('wins',0)} | {wr} | "
                       f"{v.get('long_n',0)} | {v.get('short_n',0)} |")
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

    out += ["## Post-cost gate (15bps round-trip; net must keep >= 60% of gross)",
            ""]
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
            "**H-033 cleared `edge_stability_harness` AND the post-cost gate.** "
            "Against a poor base rate (8-11 prior harness kills incl. the prior "
            "H-033 residualized-overnight reversal killed 2026-05-19) this is a "
            "**research candidate, not a green light.** Before any wiring it "
            "still needs: a fresh out-of-sample re-test on closes after the "
            "data_sample_lock, a deflated-Sharpe / SPA multiple-testing "
            "correction across the trend-filter on/off configurations, and "
            "operator review. No wiring here.",
        ]
    elif verdict == "REJECTED":
        out += [
            "**H-033 was TESTED and REJECTED.** The continuous long-short book "
            "gave the harness real window density, so it rendered a genuine "
            "verdict. " + (
                "The harness eff sign splits across windows — in-sample "
                "separation that flips sign across regimes. "
                if not adm_harness else
                "The harness sign is stable but the post-cost gate fails — the "
                "monthly turnover cost eats the spread. "
            ) + "Do NOT re-test this construction on this sample. Nothing is "
            "wired or sized.",
        ]
    else:
        out += [
            "**H-033 is UNTESTED — data-gap, explicitly NOT a pass.** " + (
                "A dense free daily-close tape was unavailable for one or more "
                "sectors, so the run used a labelled synthetic series. "
                if offline else
                f"The harness scored only {scored} fourteen-day window(s); it "
                f"needs >= {harness.MIN_STABLE_WINDOWS}. "
            ) + "This is an honest non-verdict — not a pass and not a clean "
            "fail. A real H-033 verdict needs the full yfinance daily close "
            "history for all 11 SPDR sector ETFs + SPY.",
        ]
    out += [
        "",
        "## next_step",
        "",
        (
            "H-033 cleared both gates — escalate for out-of-sample re-test, "
            "DSR/SPA correction across trend-filter on/off, and operator review "
            "before any wiring."
            if verdict == "ADMISSIBLE" else
            "Harness kill — sector cross-sectional momentum does not yield an "
            "admissible equity edge on this sample. Do NOT re-test this "
            "construction on this data."
            if verdict == "REJECTED" else
            "Re-fetch the yfinance daily close history for all 11 SPDR sector "
            "ETFs + SPY so the harness has the full ~7-15 year cross-section. "
            "Re-run only with the dense tape."
        ),
        "",
    ]
    return "\n".join(out)


# ===========================================================================
# Orchestration
# ===========================================================================
def run(quick: bool, refresh: bool, use_trend_filter: bool = True) -> dict:
    etfs = ETFS_QUICK if quick else SECTOR_ETFS
    data = load_market_data(etfs, refresh, include_benchmark=True)

    bt = backtest_continuous(data, etfs, use_trend_filter=use_trend_filter)
    recs = bt.get("records", [])
    cg = cost_survival(bt.get("gross_rets", []), bt.get("net_rets", []))

    res = {
        "records": recs,
        "per_sector": bt.get("per_sector", {}),
        "cost_gate": cg,
        "any_offline": bt.get("any_offline", False),
        "n_rebalances_active": bt.get("n_rebalances_active", 0),
        "n_rebalances_flat": bt.get("n_rebalances_flat", 0),
        "calendar_len": bt.get("calendar_len", 0),
        "trend_filter_used": bt.get("trend_filter_used", use_trend_filter),
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
        "hypothesis": "H-033",
        "registry_id": "H-040",
        "family": "equity_sector_cross_sectional_momentum",
        "asset_class": "EQUITY",
        "verdict": verdict,
        "trend_filter_used": res.get("trend_filter_used", True),
        "offline_synthetic": offline,
        "n_records": len(res.get("records", [])),
        "n_rebalances_active": res.get("n_rebalances_active", 0),
        "n_rebalances_flat": res.get("n_rebalances_flat", 0),
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
                    help="7-sector smoke set for a fast run")
    ap.add_argument("--json", dest="as_json", action="store_true")
    ap.add_argument("--refresh-cache", action="store_true",
                    help="re-fetch sector-ETF + SPY data, ignoring the cache")
    ap.add_argument("--no-trend-filter", action="store_true",
                    help="disable the SPY 12-month MA trend filter "
                         "(pre-registered configuration: ON)")
    ap.add_argument("--out", type=Path,
                    default=ROOT / "reports" /
                    "h033_equity_sector_momentum_research_2026-05-19.md")
    args = ap.parse_args()

    res = run(args.quick, args.refresh_cache,
              use_trend_filter=not args.no_trend_filter)
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
