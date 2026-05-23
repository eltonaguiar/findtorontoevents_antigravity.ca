#!/usr/bin/env python3
"""H-020 — CRYPTO cross-exchange price-premium (Coinbase Premium Index) backtest.

OPT-IN RESEARCH SIDECAR. No production wiring. No caller in quality_gates.py,
dashboard_generator.py, or any pick-generation / scoring path. It fetches free
public market data and writes a report — nothing else.

------------------------------------------------------------------------------
WHY THIS MODULE EXISTS
------------------------------------------------------------------------------
The CRYPTO/EQUITY edge hunt has 10 harness kills and 0 admissible signals. The
next_step of every kill explicitly bans re-testing that family. H-020 picks a
genuinely-NEW free-data signal class the pick system has never ingested:
the CROSS-EXCHANGE PRICE PREMIUM between two venues.

THE SIGNAL — Coinbase Premium Index:
  premium = (coinbase_usd_close - binance_usdt_close) / binance_usdt_close
  on the synchronized UTC daily grid. Coinbase is the dominant US-institutional
  spot venue, Binance the global retail/offshore hub. A persistent positive
  premium proxies US-institutional net spot BUYING (price discovery leading on
  the US venue); a persistent negative premium proxies distribution. The signal
  is the strictly-past rolling z-score of the premium, direction-signed
  (momentum): z>0 -> LONG, z<0 -> SHORT.

  This is NOT a banned family. It is distinct from exchange net-flow
  (H-018/H-019, which uses on-chain exchange-attributed WALLET flow volumes) —
  H-020 uses the cross-VENUE order-book PRICE SPREAD. No funding rate, no COT,
  no yield curve, no on-chain address counts, no options data.

------------------------------------------------------------------------------
THE CONSTRUCTION (legitimate density pattern from H-008/H-014)
------------------------------------------------------------------------------
  * FULL continuous-position cross-sectional book. Every (coin, day) is one
    resolved record. NO |z| threshold, NO sparse event filter — so the record
    stream is dense and uniform and the harness's fixed 14-day windows fill.
  * ~8 liquid majors covered by BOTH Coinbase and Binance.
  * STRICT no-look-ahead: the premium z for a position dated D is computed from
    premium observations STRICTLY BEFORE D; entry D+1; the realized return is
    the Binance close(D)->close(D+1) move signed by the direction.
  * Both venues' UTC daily close on the SAME grid — no overnight-gap leak.

------------------------------------------------------------------------------
THE VERDICT GATE
------------------------------------------------------------------------------
Records pass through tools/edge_stability_harness.evaluate()/is_admissible()
imported UNMODIFIED. ADMISSIBLE iff |eff| >= 0.30, same sign, >= 3 of 5
walk-forward 14-day windows, >= 80 records/window. PLUS a 30bps round-trip
post-cost gate: net edge must keep >= 60% of gross.

A gaudy in-sample WR is NOT a pass. After 10 straight kills the base rate is
poor (swarm pressure-test 2026-05-18 estimated <20%). This module reports the
verdict honestly whichever way it lands.

    python tools/h020_cross_exchange_premium_research.py [--quick] [--json]
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
# Tunables — pre-registered. The signal family is fixed; no per-window search.
# ---------------------------------------------------------------------------
Z_ROLL = 30                 # rolling z-score look-back (STRICTLY past obs)
WINDOW_DAYS = 14            # walk-forward window length (harness default)
HARNESS_FIELD = "signal_z"  # conviction-magnitude score the harness reads
ROUND_TRIP_COST_BPS = 30.0  # crypto round-trip (taker fees + slippage, both legs)
COST_SURVIVAL_MIN = 0.60    # net edge must retain >= 60% of gross

CACHE = ROOT / "tools" / "cache" / "h020_cross_exchange_cache.json"

# coin -> (binance symbol, coinbase product). Majors covered by BOTH venues.
COINS_FULL = {
    "BTC":  ("BTCUSDT", "BTC-USD"),
    "ETH":  ("ETHUSDT", "ETH-USD"),
    "SOL":  ("SOLUSDT", "SOL-USD"),
    "XRP":  ("XRPUSDT", "XRP-USD"),
    "ADA":  ("ADAUSDT", "ADA-USD"),
    "AVAX": ("AVAXUSDT", "AVAX-USD"),
    "LINK": ("LINKUSDT", "LINK-USD"),
    "LTC":  ("LTCUSDT", "LTC-USD"),
}
COINS_QUICK = {
    "BTC": ("BTCUSDT", "BTC-USD"),
    "ETH": ("ETHUSDT", "ETH-USD"),
    "SOL": ("SOLUSDT", "SOL-USD"),
}


# ===========================================================================
# Data fetch — free public APIs, no key. With failover + pagination.
# ===========================================================================
def _http_json(url: str, timeout: int = 30):
    """GET JSON with a browser-ish UA; return parsed object or None."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 h020-research"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception:  # noqa: BLE001
        return None


# Binance API failover chain (per project API Failover Rule).
_BINANCE_HOSTS = ("api", "api1", "api2", "api3")


def fetch_binance_daily(symbol: str) -> dict[str, float]:
    """Binance spot daily close keyed by ISO UTC date. Paginated full history.

    /api/v3/klines caps at 1000 rows per call; paginate with startTime.
    Failover across api/api1/api2/api3 mirrors.
    """
    out: dict[str, float] = {}
    start_ms = 1451606400000  # 2016-01-01
    while True:
        rows = None
        for host in _BINANCE_HOSTS:
            url = (f"https://{host}.binance.com/api/v3/klines?symbol={symbol}"
                   f"&interval=1d&limit=1000&startTime={start_ms}")
            rows = _http_json(url)
            if isinstance(rows, list):
                break
        if not isinstance(rows, list) or not rows:
            break
        for k in rows:
            try:
                ts = int(k[0])
                d = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).date().isoformat()
                c = float(k[4])
                if c > 0:
                    out[d] = c
            except (TypeError, ValueError, IndexError):
                continue
        last_ts = int(rows[-1][0])
        if len(rows) < 1000:
            break
        start_ms = last_ts + 86400000
        time.sleep(0.25)
    return out


def fetch_coinbase_daily(product: str) -> dict[str, float]:
    """Coinbase Exchange daily close keyed by ISO UTC date. Paginated.

    /products/<p>/candles caps at 300 candles per call -> page backward by
    300-day windows. Candle row format: [time, low, high, open, close, volume].
    """
    out: dict[str, float] = {}
    end = datetime.now(timezone.utc)
    span_days = 300
    empty_pages = 0
    while True:
        start = end.timestamp() - span_days * 86400
        s_iso = datetime.fromtimestamp(start, tz=timezone.utc).isoformat()
        e_iso = end.isoformat()
        url = (f"https://api.exchange.coinbase.com/products/{product}/candles"
               f"?granularity=86400&start={s_iso}&end={e_iso}")
        rows = _http_json(url)
        if not isinstance(rows, list) or not rows:
            empty_pages += 1
            if empty_pages >= 2:
                break
            end = datetime.fromtimestamp(start, tz=timezone.utc)
            time.sleep(0.4)
            continue
        empty_pages = 0
        for k in rows:
            try:
                ts = int(k[0])
                d = datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
                c = float(k[4])  # close
                if c > 0:
                    out[d] = c
            except (TypeError, ValueError, IndexError):
                continue
        end = datetime.fromtimestamp(start, tz=timezone.utc)
        time.sleep(0.4)
        # stop once we have walked back far enough (Coinbase spot ~2015+)
        if end.year < 2016:
            break
    return out


def load_market_data(coins: dict, refresh: bool) -> dict:
    """Fetch (or load cached) Binance + Coinbase daily closes for each coin."""
    if CACHE.exists() and not refresh:
        try:
            cached = json.loads(CACHE.read_text(encoding="utf-8"))
            if all(c in cached.get("data", {}) for c in coins):
                print(f"# loaded cache {CACHE}", file=sys.stderr)
                return cached["data"]
        except Exception:  # noqa: BLE001
            pass
    data: dict[str, dict] = {}
    for coin, (bsym, cprod) in coins.items():
        print(f"# fetching {coin}  binance={bsym}  coinbase={cprod} ...",
              file=sys.stderr)
        bz = fetch_binance_daily(bsym)
        cb = fetch_coinbase_daily(cprod)
        print(f"#   {coin}: binance={len(bz)} bars  coinbase={len(cb)} bars",
              file=sys.stderr)
        data[coin] = {"binance": bz, "coinbase": cb}
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
def compute_premium_series(binance: dict[str, float],
                            coinbase: dict[str, float]) -> dict[str, float]:
    """ISO-date -> Coinbase premium = (coinbase - binance)/binance.

    Only dates present on BOTH venues' synchronized UTC daily grid are kept.
    Pure function — no look-ahead (each date uses only its own two closes).
    """
    out: dict[str, float] = {}
    for d in sorted(set(binance) & set(coinbase)):
        b = binance[d]
        if b > 0:
            out[d] = (coinbase[d] - b) / b
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
    """FULL continuous-position cross-sectional book on the premium z signal.

    For every (coin, day D) with a next bar D+1:
      * premium_z = rolling z of the premium computed STRICTLY from premium
        observations before D (the position taken on D+1 sees only <= D-1
        premium history -> see entry_date / signal_date below).
      * direction: premium z>0 (Coinbase bidding above Binance = US-institutional
        accumulation) -> LONG (+1); z<0 -> SHORT (-1); z==0 -> skip.
      * raw_ret = binance_close(D+1)/binance_close(D) - 1
      * signed_ret = raw_ret * direction
      * record: status WON iff signed_ret>0 (gross) AND a cost-adjusted leg
        used for the post-cost gate; harness score field signal_z = |z|.

    STRICT no-look-ahead: the signal date used is strictly before the entry
    date D, and the return is realized over [D, D+1).
    """
    records: list[dict] = []
    per_coin: dict[str, dict] = {}
    gross_rets: list[float] = []
    net_rets: list[float] = []

    cost_frac = ROUND_TRIP_COST_BPS / 10000.0

    for coin, venues in data.items():
        binance = venues.get("binance", {})
        coinbase = venues.get("coinbase", {})
        premium = compute_premium_series(binance, coinbase)
        pdates = sorted(premium)
        pvals = [premium[d] for d in pdates]
        # z by premium date (uses strictly-past premium obs)
        z_by_date: dict[str, float] = {}
        for i, d in enumerate(pdates):
            z = rolling_z(pvals, i, Z_ROLL)
            if z is not None:
                z_by_date[d] = z
        sorted_z_dates = sorted(z_by_date)
        if not sorted_z_dates:
            per_coin[coin] = {"n": 0, "wins": 0, "wr": None}
            continue

        bdates = sorted(binance)
        n = wins = 0
        import bisect
        for j in range(len(bdates) - 1):
            d = bdates[j]
            d_next = bdates[j + 1]
            # signal date strictly BEFORE the entry date D (no look-ahead)
            si = bisect.bisect_left(sorted_z_dates, d) - 1
            if si < 0:
                continue
            sig_date = sorted_z_dates[si]
            z = z_by_date[sig_date]
            direction = 1 if z > 0 else (-1 if z < 0 else 0)
            if direction == 0:
                continue
            p0, p1 = binance[d], binance[d_next]
            if p0 <= 0:
                continue
            raw_ret = p1 / p0 - 1.0
            signed_ret = raw_ret * direction
            net_ret = signed_ret - cost_frac  # one round-trip per held position
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
                "instrument": coin,
            })
        per_coin[coin] = {"n": n, "wins": wins,
                          "wr": round(wins / n, 4) if n else None,
                          "premium_obs": len(premium)}

    return {
        "records": records,
        "per_coin": per_coin,
        "gross_rets": gross_rets,
        "net_rets": net_rets,
    }


# ===========================================================================
# Post-cost gate
# ===========================================================================
def cost_survival(gross_rets: list[float], net_rets: list[float]) -> dict:
    """Post-cost gate: does net per-trade edge keep >= 60% of gross?

    gross_edge = mean signed return (bps). net_edge = mean net return (bps),
    after a single ROUND_TRIP_COST_BPS round-trip per held position.
    cost_survival = net_edge / gross_edge.
    """
    if not gross_rets:
        return {"passes": False, "reason": "no trades"}
    gross_bps = statistics.fmean(gross_rets) * 10000.0
    net_bps = statistics.fmean(net_rets) * 10000.0
    if gross_bps <= 0:
        survival = 0.0
    else:
        survival = net_bps / gross_bps
    return {
        "gross_edge_bps": round(gross_bps, 4),
        "net_edge_bps": round(net_bps, 4),
        "cost_bps": ROUND_TRIP_COST_BPS,
        "cost_survival_pct": round(survival * 100, 2),
        "passes": bool(gross_bps > 0 and survival >= COST_SURVIVAL_MIN),
    }


def pooled_wr(records: list[dict], net: bool = False) -> float | None:
    """Pooled win-rate (gross or net of cost)."""
    key = "net_ret" if net else "signed_ret"
    rs = [r.get(key) for r in records if r.get(key) is not None]
    if not rs:
        return None
    return round(sum(1 for r in rs if r > 0) / len(rs), 4)


# ===========================================================================
# Harness wiring
# ===========================================================================
def harness_verdict(records: list[dict], window_days: int = WINDOW_DAYS) -> dict:
    """Run synthetic records through edge_stability_harness, patching its loader
    for this call only. The harness logic — windowing, eff, is_admissible()
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
    adm_harness = h.get("admissible", False)
    cost_pass = cg.get("passes", False)
    scored = h.get("windows_scored", 0)

    if scored < harness.MIN_STABLE_WINDOWS:
        verdict = "UNTESTED-data-gap"
    elif adm_harness and cost_pass:
        verdict = "ADMISSIBLE"
    else:
        verdict = "REJECTED"

    out = [
        "# H-020 CRYPTO Cross-Exchange Premium (Coinbase Premium Index) — 2026-05-18",
        "",
        f"_Generated {ts} by `tools/h020_cross_exchange_premium_research.py`._",
        "",
        f"## VERDICT: **{verdict}**",
        "",
        "**Status: OPT-IN RESEARCH SIDECAR. No production wiring.** No caller in "
        "`quality_gates.py`, `dashboard_generator.py`, or any pick-generation / "
        "scoring path. Fetches free public market data, writes this report — "
        "nothing else.",
        "",
        "## The signal",
        "",
        "Cross-exchange price premium — the **Coinbase Premium Index**:",
        "",
        "- `premium = (coinbase_usd_close - binance_usdt_close) / binance_usdt_close` "
        "on the synchronized UTC daily grid.",
        f"- `signal_z` = rolling {Z_ROLL}-observation z-score of the premium, "
        "strictly-past window.",
        "- direction (momentum): premium z>0 (Coinbase bidding above Binance — "
        "US-institutional accumulation leading price discovery) -> LONG; z<0 -> "
        "SHORT.",
        "- harness score field = `|signal_z|` (conviction magnitude).",
        "",
        "**Causal mechanism:** Coinbase is the dominant US-institutional spot "
        "venue, Binance the global retail/offshore hub. A persistent premium "
        "proxies the direction of US-institutional net spot flow. The swarm "
        "pressure-test (groq/ollama/pollinations 2026-05-18) flagged that "
        "cross-exchange arbitrage closes the spread intraday, so the daily-close "
        "residual is thin — base rate estimated <20%. A sound prior is not an "
        "edge; only the harness + cost verdict counts.",
        "",
        "## Construction (legitimate density pattern from H-008/H-014)",
        "",
        "- **FULL continuous-position cross-sectional book** — one resolved "
        "record per coin per day, NO `|z|` self-selection, NO sparse event "
        "filter. This is the H-008-redesign density pattern, not threshold "
        "relaxation.",
        "- **Strict no-look-ahead** — the premium z for an entry dated D uses "
        "premium observations *strictly before* D; entry D+1; return realized "
        "over Binance close(D)->close(D+1). Both venues' UTC daily close on the "
        "same grid — no overnight-gap leak.",
        f"- `signal_z` = rolling {Z_ROLL}-obs z of the premium.",
        "",
        "## Data",
        "",
        "- **Binance** spot daily klines (failover api/api1/api2/api3), paginated "
        "full history.",
        "- **Coinbase Exchange** daily candles (`/products/<p>/candles`, free, no "
        "key), paginated backward in 300-candle pages.",
        f"- **Sample:** {len(recs)} coin-day resolved records.",
        "",
    ]
    pc = res.get("per_coin", {})
    if pc:
        out += ["| coin | records | wins | gross WR | premium obs |",
                "|---|---|---|---|---|"]
        for k, v in pc.items():
            wr = f"{v['wr']*100:.1f}%" if v.get("wr") is not None else "n/a"
            out.append(f"| {k} | {v.get('n',0)} | {v.get('wins',0)} | {wr} | "
                       f"{v.get('premium_obs','n/a')} |")
        out.append("")

    out += ["## Harness verdict (THE gate — `edge_stability_harness`, UNMODIFIED)",
            ""]
    if "per_window_eff" in h:
        effs = " ".join(
            (f"{e['eff']:+.2f}" if e["eff"] is not None else "n/a")
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

    out += ["## Post-cost gate (30bps round-trip; net must keep >= 60% of gross)",
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
        f"- pooled gross WR: "
        f"{(res.get('pooled_wr_gross') or 0)*100:.1f}%",
        f"- pooled net WR: {(res.get('pooled_wr_net') or 0)*100:.1f}%",
        "",
        "## Honest conclusion",
        "",
    ]
    if verdict == "ADMISSIBLE":
        out += [
            "**H-020 CLEARED `edge_stability_harness` AND the post-cost gate.** "
            "Against a poor base rate (10 straight kills) this must be treated as "
            "a **research candidate, not a green light.** Before any wiring or "
            "sizing it still needs: fresh out-of-sample re-test, full "
            "transaction-cost / slippage modelling, a deflated-Sharpe / SPA "
            "multiple-testing correction, and operator review. The harness is "
            "necessary, not sufficient. No wiring here.",
        ]
    elif verdict == "REJECTED":
        out += [
            "**H-020 was TESTED and REJECTED — kill #11 of the edge hunt.** The "
            "continuous-position construction gave the harness real window "
            "density, so it rendered a genuine verdict. " + (
                "The harness eff sign splits across windows — the identical "
                "failure mode that killed the prior 10 candidates: in-sample "
                "separation that flips sign across regimes. "
                if not adm_harness else
                "The harness sign is stable but the post-cost gate fails — "
                "the gross signal is too thin to survive a 30bps round-trip. "
            ) + "A sound prior is not an edge. Do NOT re-test this construction "
            "on this sample. Nothing is wired or sized.",
        ]
    else:
        out += [
            "**H-020 is UNTESTED — data-gap, explicitly NOT a pass.** The harness "
            f"scored only {scored} fourteen-day window(s); it needs >= "
            f"{harness.MIN_STABLE_WINDOWS}. Cross-exchange daily-close history "
            "did not supply enough dense windows to render an eff-stability "
            "verdict. This is an honest non-verdict, not a pass and not a clean "
            "fail.",
        ]
    out.append("")
    out += [
        "## next_step",
        "",
        (
            "Kill #11. Cross-exchange daily-close premium does not yield an "
            "admissible CRYPTO edge on this sample. Do NOT re-test the "
            "daily-close Coinbase-premium z-score on this data. A future retry "
            "would need intraday (hourly/minute) premium resolution — the "
            "swarm flagged the daily residual is post-arbitrage noise — and a "
            "materially different construction (e.g. premium *velocity* around "
            "known US-session opens, or a premium-vs-funding interaction), AND "
            "must clear `edge_stability_harness` + the post-cost gate before "
            "any claim."
            if verdict == "REJECTED" else
            "H-020 cleared both gates — escalate for out-of-sample re-test, "
            "DSR/SPA correction, and operator review before any wiring."
            if verdict == "ADMISSIBLE" else
            "Re-test only with a deeper / denser sample (more coins, or intraday "
            "resolution). The daily-close construction did not give the harness "
            "enough scored windows; this is a genuine coverage gap."
        ),
        "",
    ]
    return "\n".join(out)


# ===========================================================================
# Orchestration
# ===========================================================================
def run(quick: bool, refresh: bool) -> dict:
    coins = COINS_QUICK if quick else COINS_FULL
    data = load_market_data(coins, refresh)

    bt = backtest_continuous(data)
    recs = bt.get("records", [])
    cg = cost_survival(bt.get("gross_rets", []), bt.get("net_rets", []))

    res = {
        "records": recs,
        "per_coin": bt.get("per_coin", {}),
        "cost_gate": cg,
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
    if scored < harness.MIN_STABLE_WINDOWS:
        verdict = "UNTESTED-data-gap"
    elif h.get("admissible") and cg.get("passes"):
        verdict = "ADMISSIBLE"
    else:
        verdict = "REJECTED"
    return {
        "hypothesis": "H-020",
        "family": "cross_exchange_coinbase_premium_zscore",
        "asset_class": "CRYPTO",
        "verdict": verdict,
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
                    help="3-coin smoke set for a fast run")
    ap.add_argument("--json", dest="as_json", action="store_true")
    ap.add_argument("--refresh-cache", action="store_true",
                    help="re-fetch market data, ignoring the cache")
    ap.add_argument("--out", type=Path,
                    default=ROOT / "reports" /
                    "h020_cross_exchange_premium_research_2026-05-18.md")
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
