#!/usr/bin/env python3
"""ET-1 — ETF creation/redemption share-count flow backtest (H-026).

OPT-IN RESEARCH SIDECAR. No production wiring. No caller in quality_gates.py,
dashboard_generator.py, passes_active_gate, calculate_smart_score, or any
pick-generation / scoring path. It fetches free public ETF data and writes a
report — nothing else. Importing this module has no side effects on production.

------------------------------------------------------------------------------
WHY THIS MODULE EXISTS
------------------------------------------------------------------------------
`reports/new_strategy_proposals_2026_05_18.md` ranks ET-1 the #1 candidate of
14 proposals: cleanest mechanism, genuinely-new primary-market input, lowest
effort, no banned/arbitrage flag. The ETF mechanisms already in the ledger
(dual momentum, sector/risk-parity rotation, Faber, RSI2) are all *price-overlay*
strategies. ET-1 reads the *primitive* that makes an ETF an ETF.

THE SIGNAL — ETF creation/redemption share-count flow:
  When an ETF's *shares outstanding* rises, an Authorized Participant (AP)
  created new units — committed capital flowing into the basket. A falling
  share count = redemption = outflow. Shares-outstanding flow is a PRIMARY-MARKET
  fund-flow signal, distinct from every price-based rotation strategy in the
  ledger. It is the cleanest "smart-money allocation" tape ETFs produce.

  net_creation_flow = (shares_out(D) - shares_out(D-1)) / shares_out(D-1)
  signal_z = strictly-past rolling z-score of the 10-day net-creation flow.
  Direction (momentum): z>0 (persistent net creation = institutional inflow)
  -> LONG; z<0 (persistent net redemption = institutional outflow) -> SHORT.

  This is NOT a banned family. It is NOT yield-curve (H-008), NOT COT (H-001),
  NOT funding rate (H-006), NOT roll-yield (H-007), NOT options-flow
  (H-009/H-011/H-013), NOT exchange net-flow (H-018/H-019), NOT premium/discount
  to iNAV. It is the share-count delta — a primary-market input the pick system
  has never ingested.

------------------------------------------------------------------------------
DATA SOURCES — FREE ONLY
------------------------------------------------------------------------------
  * SEC EDGAR `data.sec.gov` company-facts / submissions API (free, no key) —
    fund registrants file N-PORT monthly with shares-outstanding.
  * yfinance `sharesOutstanding` and the daily price series for sector ETFs.
    yfinance is the free, no-key fallback for the shares-outstanding tape that
    issuer fund pages publish daily.
  * Issuer fund pages (SPDR / iShares / Vanguard / Invesco) publish daily
    shares-outstanding — handled here only as documented manual-fetch fallback.

No paid feed. No API key. A SEC EDGAR fetch sends the SEC-required descriptive
User-Agent. If the network is unavailable the module degrades to a synthetic
demonstration series and labels the verdict UNTESTED-data-gap honestly — it
never fabricates a pass.

------------------------------------------------------------------------------
THE CONSTRUCTION (legitimate density pattern from H-008/H-014/H-019/H-020)
------------------------------------------------------------------------------
  * FULL continuous-position cross-sectional book. Every (etf, day) with a next
    bar is one resolved record. NO |z| threshold, NO sparse event filter — so
    the record stream is dense and the harness's fixed 14-day windows fill.
  * Thematic / sector ETFs only (the proposal's risk mitigation: broad-market
    mega-funds create/redeem mechanically on index rebalances, not on a view).
  * STRICT no-look-ahead: the signal z for a position dated D is computed from
    share-count observations STRICTLY BEFORE D; entry D+1; the realized return
    is the price close(D)->close(D+1) move signed by the direction.

------------------------------------------------------------------------------
THE VERDICT GATE
------------------------------------------------------------------------------
Records pass through tools/edge_stability_harness.evaluate()/is_admissible()
imported UNMODIFIED. ADMISSIBLE iff |eff| >= 0.30, same sign, >= 3 of 5
walk-forward 14-day windows, >= 80 records/window. PLUS a 10bps round-trip
post-cost gate (ETF spreads are tight): net edge must keep >= 60% of gross.

A gaudy in-sample WR is NOT a pass. The edge hunt's base rate is poor (8-11
harness kills to date). This module reports the verdict honestly whichever way
it lands. Nothing here is wired into or sized by any production path.

    python tools/et1_etf_creation_redemption_research.py [--quick] [--json]
            [--refresh-cache]
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import urllib.request
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
# Tunables — pre-registered (H-026). The signal family is fixed; no per-window
# search, no post-hoc parameter tuning.
# ---------------------------------------------------------------------------
FLOW_WINDOW = 10            # net-creation flow look-back (trading days)
Z_ROLL = 30                 # rolling z-score look-back (STRICTLY past obs)
WINDOW_DAYS = 14            # walk-forward window length (harness default)
HARNESS_FIELD = "signal_z"  # conviction-magnitude score the harness reads
ROUND_TRIP_COST_BPS = 10.0  # ETF round-trip (tight spreads + slippage, both legs)
COST_SURVIVAL_MIN = 0.60    # net edge must retain >= 60% of gross

CACHE = ROOT / "tools" / "cache" / "et1_etf_creation_redemption_cache.json"

# SEC requires a descriptive UA with contact info for data.sec.gov access.
SEC_UA = "findtorontoevents-research et1-sidecar zerounderscore@gmail.com"

# Thematic / sector ETFs — discretionary creation flow (proposal risk mitigation:
# broad-market mega-funds excluded; their flow is mechanical index rebalancing).
ETFS_FULL = [
    "XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB", "XLRE",
    "SMH", "XBI", "ITB", "KRE", "JETS", "TAN", "ICLN", "ARKK", "IYR", "XOP",
]
ETFS_QUICK = ["XLK", "XLF", "XLE", "XLV", "SMH"]


# ===========================================================================
# Data fetch — free public APIs, no key.
# ===========================================================================
def _http_json(url: str, timeout: int = 30, ua: str = "Mozilla/5.0 et1-research"):
    """GET JSON with a descriptive UA; return parsed object or None."""
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception:  # noqa: BLE001
        return None


def fetch_etf_series(ticker: str) -> dict:
    """Fetch a free daily price + shares-outstanding series for one ETF.

    Strategy (free sources only, in priority order):
      1. yfinance — daily close series + `sharesOutstanding`. yfinance is the
         free, no-key tape of the shares-outstanding figure that issuer fund
         pages publish daily and that N-PORT filings carry monthly.
      2. SEC EDGAR data.sec.gov — N-PORT-derived shares-outstanding facts for
         the fund registrant (free, no key, SEC-UA required) as a cross-check.

    Returns {"price": {iso_date: close}, "shares": {iso_date: shares_out}}.
    On total network failure returns empty dicts; the caller then degrades to
    a clearly-labelled synthetic series and an UNTESTED verdict — never a fake
    pass.
    """
    price: dict[str, float] = {}
    shares: dict[str, float] = {}

    # ---- 1. yfinance daily close + shares-outstanding -----------------------
    try:
        import yfinance as yf  # noqa: PLC0415
        tk = yf.Ticker(ticker)
        hist = tk.history(period="max", interval="1d", auto_adjust=False)
        if hist is not None and not hist.empty:
            for idx, row in hist.iterrows():
                try:
                    d = idx.date().isoformat()
                    c = float(row["Close"])
                    if c > 0:
                        price[d] = c
                except Exception:  # noqa: BLE001
                    continue
        # yfinance exposes a single current sharesOutstanding scalar; the
        # historical share-count tape is reconstructed below from N-PORT.
        info = {}
        try:
            info = tk.get_info() if hasattr(tk, "get_info") else tk.info
        except Exception:  # noqa: BLE001
            info = {}
        so_now = info.get("sharesOutstanding") if isinstance(info, dict) else None
        if so_now and price:
            # anchor: most-recent date carries the current share count.
            shares[max(price)] = float(so_now)
    except Exception:  # noqa: BLE001
        pass

    # ---- 2. SEC EDGAR N-PORT shares-outstanding cross-check -----------------
    # The full historical shares-outstanding tape lives in N-PORT monthly
    # filings; data.sec.gov company-concept exposes it as a free JSON fact
    # stream. This block documents the canonical free path; it is best-effort
    # and the run still completes if EDGAR is unreachable.
    try:
        # company_tickers maps ticker -> CIK for the EDGAR fact endpoints.
        tickers_map = _http_json(
            "https://www.sec.gov/files/company_tickers.json", ua=SEC_UA)
        cik = None
        if isinstance(tickers_map, dict):
            for _, rec in tickers_map.items():
                if isinstance(rec, dict) and \
                        str(rec.get("ticker", "")).upper() == ticker.upper():
                    cik = str(rec.get("cik_str", "")).zfill(10)
                    break
        if cik:
            # N-PORT shares-outstanding is filed under fund-specific tags;
            # EntityCommonStockSharesOutstanding is the broadly-available
            # company-concept fact used here as the free cross-check.
            facts = _http_json(
                f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}"
                f"/dei/EntityCommonStockSharesOutstanding.json", ua=SEC_UA)
            if isinstance(facts, dict):
                for unit_rows in facts.get("units", {}).values():
                    for row in unit_rows:
                        try:
                            end = str(row.get("end"))
                            val = float(row.get("val"))
                            if end and val > 0:
                                shares[end] = val
                        except (TypeError, ValueError):
                            continue
        time.sleep(0.2)  # SEC fair-access courtesy delay
    except Exception:  # noqa: BLE001
        pass

    return {"price": price, "shares": shares}


def _synthetic_series(ticker: str, n_days: int = 900) -> dict:
    """Deterministic synthetic price + share-count series for an OFFLINE run.

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
    shares: dict[str, float] = {}
    px = 100.0 + (seed % 50)
    so = 1_000_000.0 + (seed % 9) * 100_000.0
    base = datetime(2023, 1, 2, tzinfo=timezone.utc)
    for i in range(n_days):
        d = (base.fromordinal(base.toordinal() + i)).date().isoformat()
        px *= 1.0 + (rand() - 0.5) * 0.02
        so *= 1.0 + (rand() - 0.5) * 0.01
        price[d] = round(px, 4)
        shares[d] = round(so, 2)
    return {"price": price, "shares": shares}


def load_market_data(etfs: list[str], refresh: bool) -> dict:
    """Fetch (or load cached) price + shares-outstanding series per ETF.

    Adds an `_offline` flag per ETF when the series came from the synthetic
    fallback so the verdict layer can honestly report UNTESTED-data-gap.
    """
    if CACHE.exists() and not refresh:
        try:
            cached = json.loads(CACHE.read_text(encoding="utf-8"))
            if all(t in cached.get("data", {}) for t in etfs):
                print(f"# loaded cache {CACHE}", file=sys.stderr)
                return cached["data"]
        except Exception:  # noqa: BLE001
            pass

    data: dict[str, dict] = {}
    for t in etfs:
        print(f"# fetching {t} (free yfinance + SEC EDGAR) ...", file=sys.stderr)
        series = fetch_etf_series(t)
        # An ET-1 backtest needs a dense share-count tape. yfinance gives a
        # single scalar; N-PORT is monthly. When the dense tape is unavailable
        # the run is honestly UNTESTED — fall back to a labelled synthetic.
        if len(series.get("shares", {})) < 60 or len(series.get("price", {})) < 120:
            print(f"#   {t}: dense share-count tape unavailable from free "
                  f"sources -> synthetic fallback (verdict will be UNTESTED)",
                  file=sys.stderr)
            series = _synthetic_series(t)
            series["_offline"] = True
        else:
            series["_offline"] = False
        print(f"#   {t}: price={len(series['price'])} bars  "
              f"shares={len(series['shares'])} obs  offline={series['_offline']}",
              file=sys.stderr)
        data[t] = series
        time.sleep(0.3)

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
def forward_fill_shares(price_dates: list[str],
                        shares: dict[str, float]) -> dict[str, float]:
    """Forward-fill the (monthly N-PORT) share-count onto the daily price grid.

    N-PORT shares-outstanding is reported monthly; the daily price grid is
    denser. Each price date carries the most-recent share-count observation
    AT OR BEFORE it — a strictly-past forward fill, no look-ahead. Price dates
    before the first share observation are left unfilled.
    """
    out: dict[str, float] = {}
    sdates = sorted(shares)
    if not sdates:
        return out
    import bisect
    for d in price_dates:
        i = bisect.bisect_right(sdates, d) - 1
        if i >= 0:
            out[d] = shares[sdates[i]]
    return out


def compute_creation_flow(shares_daily: dict[str, float],
                           window: int) -> dict[str, float]:
    """ISO-date -> net creation flow over the trailing `window` trading days.

    flow(D) = (shares_out(D) - shares_out(D-window)) / shares_out(D-window).
    Pure function — flow(D) uses only observations at or before D.
    """
    out: dict[str, float] = {}
    dates = sorted(shares_daily)
    for i in range(window, len(dates)):
        d = dates[i]
        s0 = shares_daily[dates[i - window]]
        s1 = shares_daily[d]
        if s0 > 0:
            out[d] = (s1 - s0) / s0
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
# Continuous-position backtest
# ===========================================================================
def backtest_continuous(data: dict) -> dict:
    """FULL continuous-position cross-sectional book on the creation-flow z.

    For every (etf, day D) with a next bar D+1:
      * signal_z = rolling z of the net-creation flow computed STRICTLY from
        flow observations before D (the position taken on D+1 sees only flow
        history strictly before D).
      * direction: z>0 (persistent net creation = institutional inflow) ->
        LONG (+1); z<0 (persistent net redemption = outflow) -> SHORT (-1);
        z==0 -> skip.
      * raw_ret = price_close(D+1)/price_close(D) - 1
      * signed_ret = raw_ret * direction
      * record: status WON iff signed_ret>0 (gross); harness score field
        signal_z = |z| (conviction magnitude).

    STRICT no-look-ahead: the signal date used is strictly before the entry
    date D, and the return is realized over [D, D+1).
    """
    records: list[dict] = []
    per_etf: dict[str, dict] = {}
    gross_rets: list[float] = []
    net_rets: list[float] = []
    cost_frac = ROUND_TRIP_COST_BPS / 10000.0
    any_offline = False

    for ticker, series in data.items():
        price = series.get("price", {})
        shares = series.get("shares", {})
        if series.get("_offline"):
            any_offline = True
        pdates = sorted(price)
        shares_daily = forward_fill_shares(pdates, shares)
        flow = compute_creation_flow(shares_daily, FLOW_WINDOW)
        fdates = sorted(flow)
        fvals = [flow[d] for d in fdates]

        z_by_date: dict[str, float] = {}
        for i, d in enumerate(fdates):
            z = rolling_z(fvals, i, Z_ROLL)
            if z is not None:
                z_by_date[d] = z
        sorted_z_dates = sorted(z_by_date)
        if not sorted_z_dates:
            per_etf[ticker] = {"n": 0, "wins": 0, "wr": None,
                               "flow_obs": len(flow)}
            continue

        import bisect
        n = wins = 0
        for j in range(len(pdates) - 1):
            d = pdates[j]
            d_next = pdates[j + 1]
            # signal date strictly BEFORE entry date D (no look-ahead)
            si = bisect.bisect_left(sorted_z_dates, d) - 1
            if si < 0:
                continue
            sig_date = sorted_z_dates[si]
            z = z_by_date[sig_date]
            direction = 1 if z > 0 else (-1 if z < 0 else 0)
            if direction == 0:
                continue
            p0, p1 = price[d], price[d_next]
            if p0 <= 0:
                continue
            raw_ret = p1 / p0 - 1.0
            signed_ret = raw_ret * direction
            net_ret = signed_ret - cost_frac
            status = "WON" if signed_ret > 0 else "LOST"
            n += 1
            wins += int(status == "WON")
            gross_rets.append(signed_ret)
            net_rets.append(net_ret)
            records.append({
                "status": status,
                "resolved_at": d_next,
                "entry_date": d,
                "signal_date": sig_date,
                "timestamp": d,
                HARNESS_FIELD: abs(z),
                "signed_ret": round(signed_ret, 8),
                "net_ret": round(net_ret, 8),
                "direction": direction,
                "instrument": ticker,
            })
        per_etf[ticker] = {"n": n, "wins": wins,
                           "wr": round(wins / n, 4) if n else None,
                           "flow_obs": len(flow)}

    return {
        "records": records,
        "per_etf": per_etf,
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
    after a single ROUND_TRIP_COST_BPS round-trip per held position.
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
        "# ET-1 ETF Creation/Redemption Share-Count Flow (H-026) — 2026-05-18",
        "",
        f"_Generated {ts} by `tools/et1_etf_creation_redemption_research.py`._",
        "",
        f"## VERDICT: **{verdict}**",
        "",
        "**Status: OPT-IN RESEARCH SIDECAR. No production wiring.** No caller in "
        "`quality_gates.py`, `dashboard_generator.py`, `passes_active_gate`, "
        "`calculate_smart_score`, or any pick-generation / scoring path. Fetches "
        "free public ETF data, writes this report — nothing else.",
        "",
        "## The signal",
        "",
        "ETF creation/redemption share-count flow — a PRIMARY-MARKET fund-flow "
        "signal:",
        "",
        "- `net_creation_flow(D) = (shares_out(D) - shares_out(D-10)) / "
        "shares_out(D-10)` — the 10-day Authorized-Participant creation/redemption "
        "share-count delta.",
        f"- `signal_z` = rolling {Z_ROLL}-observation z-score of the net creation "
        "flow, strictly-past window.",
        "- direction (momentum): z>0 (persistent net creation = institutional "
        "inflow) -> LONG; z<0 (persistent net redemption = outflow) -> SHORT.",
        "- harness score field = `|signal_z|` (conviction magnitude).",
        "",
        "**Causal mechanism:** creation/redemption is executed by APs and large "
        "allocators — a revealed institutional-flow signal with no behavioural "
        "noise. Persistent net creation into a sector/thematic ETF is a "
        "momentum-of-capital signal that may lead the basket. The data is free "
        "but scattered across issuer sites / N-PORT filings — assembly cost is "
        "the only moat. The proposal flags one risk: broad-market mega-funds "
        "create/redeem on mechanical index rebalances, so this book restricts to "
        "thematic/sector ETFs where the flow is discretionary.",
        "",
        "## Construction (legitimate density pattern from H-008/H-014/H-019/H-020)",
        "",
        "- **FULL continuous-position cross-sectional book** — one resolved "
        "record per ETF per day, NO `|z|` self-selection, NO sparse event "
        "filter. This is the H-008 density pattern, not threshold relaxation.",
        "- **Strict no-look-ahead** — the creation-flow z for an entry dated D "
        "uses share-count observations strictly before D; entry D+1; return "
        "realized over price close(D)->close(D+1). N-PORT monthly share counts "
        "are forward-filled onto the daily grid (most-recent obs at-or-before "
        "each date — a strictly-past fill).",
        "",
        "## Data (free sources only)",
        "",
        "- **yfinance** — daily ETF close series + `sharesOutstanding` scalar "
        "(free, no key).",
        "- **SEC EDGAR `data.sec.gov`** — N-PORT-derived shares-outstanding "
        "facts per fund registrant (free, no key, SEC-UA required).",
        f"- **Sample:** {len(recs)} ETF-day resolved records.",
        (
            "- **OFFLINE NOTE:** one or more ETFs fell back to a labelled "
            "synthetic series because a dense free share-count tape was "
            "unavailable. The verdict is therefore UNTESTED-data-gap — this run "
            "did NOT measure a real edge."
            if offline else
            "- All ETFs sourced from live free data."
        ),
        "",
    ]

    pe = res.get("per_etf", {})
    if pe:
        out += ["| ETF | records | wins | gross WR | flow obs |",
                "|---|---|---|---|---|"]
        for k, v in pe.items():
            wr = f"{v['wr']*100:.1f}%" if v.get("wr") is not None else "n/a"
            out.append(f"| {k} | {v.get('n',0)} | {v.get('wins',0)} | {wr} | "
                       f"{v.get('flow_obs','n/a')} |")
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

    out += ["## Post-cost gate (10bps round-trip; net must keep >= 60% of gross)",
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
            "**ET-1 cleared `edge_stability_harness` AND the post-cost gate.** "
            "Against a poor base rate (8-11 prior kills) this is a **research "
            "candidate, not a green light.** Before any wiring it still needs: "
            "fresh out-of-sample re-test, a true daily issuer share-count tape "
            "(not the N-PORT-monthly forward fill), a deflated-Sharpe / SPA "
            "multiple-testing correction, and operator review. No wiring here.",
        ]
    elif verdict == "REJECTED":
        out += [
            "**ET-1 was TESTED and REJECTED.** The continuous-position "
            "construction gave the harness real window density, so it rendered "
            "a genuine verdict. " + (
                "The harness eff sign splits across windows — in-sample "
                "separation that flips sign across regimes. "
                if not adm_harness else
                "The harness sign is stable but the post-cost gate fails. "
            ) + "Do NOT re-test this construction on this sample. Nothing is "
            "wired or sized.",
        ]
    else:
        out += [
            "**ET-1 is UNTESTED — data-gap, explicitly NOT a pass.** " + (
                "A dense free daily share-count tape was unavailable, so the "
                "run used a labelled synthetic series. "
                if offline else
                f"The harness scored only {scored} fourteen-day window(s); it "
                f"needs >= {harness.MIN_STABLE_WINDOWS}. "
            ) + "This is an honest non-verdict — not a pass and not a clean "
            "fail. A real ET-1 verdict needs a dense daily issuer "
            "shares-outstanding series (SPDR/iShares/Vanguard/Invesco fund "
            "pages publish it; N-PORT is only monthly).",
        ]
    out += [
        "",
        "## next_step",
        "",
        (
            "ET-1 cleared both gates — escalate for out-of-sample re-test, a "
            "true daily issuer share-count tape, DSR/SPA correction, and "
            "operator review before any wiring."
            if verdict == "ADMISSIBLE" else
            "Harness kill — ETF creation/redemption flow z-score does not yield "
            "an admissible ETF edge on this sample. Do NOT re-test this "
            "construction on this data."
            if verdict == "REJECTED" else
            "Acquire a dense daily issuer shares-outstanding series (per-issuer "
            "fund-page scraper) — the N-PORT monthly cadence forward-filled onto "
            "the daily grid is too coarse for a 14-day-window harness verdict. "
            "Re-run only with the denser tape."
        ),
        "",
    ]
    return "\n".join(out)


# ===========================================================================
# Orchestration
# ===========================================================================
def run(quick: bool, refresh: bool) -> dict:
    etfs = ETFS_QUICK if quick else ETFS_FULL
    data = load_market_data(etfs, refresh)

    bt = backtest_continuous(data)
    recs = bt.get("records", [])
    cg = cost_survival(bt.get("gross_rets", []), bt.get("net_rets", []))

    res = {
        "records": recs,
        "per_etf": bt.get("per_etf", {}),
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
        "hypothesis": "H-026",
        "family": "etf_creation_redemption_share_count_flow",
        "asset_class": "ETF",
        "verdict": verdict,
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
                    help="5-ETF smoke set for a fast run")
    ap.add_argument("--json", dest="as_json", action="store_true")
    ap.add_argument("--refresh-cache", action="store_true",
                    help="re-fetch ETF data, ignoring the cache")
    ap.add_argument("--out", type=Path,
                    default=ROOT / "reports" /
                    "et1_etf_creation_redemption_research_2026-05-18.md")
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
