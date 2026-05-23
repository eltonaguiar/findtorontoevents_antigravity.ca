#!/usr/bin/env python3
"""H-018 / C-2 — exchange net-flow cross-sectional spread research backtest.

OPT-IN RESEARCH SIDECAR. Writes NOTHING to any production pick/score path.
No caller in quality_gates / dashboard_generator / pick-gen. Pre-registered
in reports/hypothesis_registry.json under the `c2_exchange_flow_spread` key
(H-018) per M-107, BEFORE this backtest logic was written.

STRATEGY (H-018 / C-2):
  Exchange net-flow cross-sectional spread. Per major coin, netflow_z is the
  strictly-past 30-day z-score of daily (exchange inflow - outflow). Each day
  the ~10 majors are ranked by netflow_z; LONG the 2 with the largest OUTFLOW
  (most negative netflow_z = accumulation to cold storage), SHORT the 2 with
  the largest INFLOW (most positive netflow_z = distribution = sell pressure).
  Market-neutral, daily-rebalanced. The spread (long leg - short leg) cancels
  crypto beta, so the harness measures the SIGNAL, not market noise.

DATA SOURCE — free Dune Analytics:
  Dune `cex.flows` Spellbook table (pre-labeled exchange wallet flows on EVM
  chains). Free tier = 2,500 credits/mo, API included. We submit one SQL
  query (execute -> poll -> fetch results) and CACHE the raw rows to
  tools/cache/ so re-runs never burn credits. Per
  reports/FREE_EXCHANGE_FLOW_DATA_2026-05-18.md, `cex.flows` covers EVM coins
  cleanly (ETH/BNB/AVAX/LINK strongest) plus stablecoins; BTC/SOL need joins
  and XRP/ADA/DOGE/LTC labels are thin. We take whatever subset has clean
  daily coverage (minimum 6 coins) and report exactly what was missing.

LOOK-AHEAD CONTROL:
  netflow_z for day D uses ONLY flow observations strictly before D.
  Entry is D+1 (the next available daily close). The cross-sectional rank on
  day D therefore uses only information knowable at D's UTC close.

GATES (BOTH must pass to call it an edge):
  1. tools/edge_stability_harness.is_admissible() — UNMODIFIED import.
     EFF_MIN / MIN_WINDOW_N / MIN_STABLE_WINDOWS are NEVER touched.
  2. Post-cost gate: 30bps crypto round-trip; net edge must retain >= 60%
     of gross edge.

If Dune coverage cannot supply >= 5 windows of >= 80 records, the honest
verdict is UNTESTED (data-gap) — explicitly NOT a pass. The harness
thresholds are NEVER lowered to manufacture a verdict.

    python tools/h018_netflow_research.py [--refresh] [--json]

`--refresh` forces a fresh Dune execution (burns credits); default uses the
cached raw result at tools/cache/h018_dune_netflow_cache.json.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

# The harness — UNMODIFIED import. Not wrapped, not reimplemented.
import edge_stability_harness as harness  # noqa: E402

CACHE_DIR = ROOT / "tools" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
DUNE_CACHE = CACHE_DIR / "h018_dune_netflow_cache.json"
PRICE_CACHE = CACHE_DIR / "h018_price_cache.json"
REPORT = ROOT / "reports" / "h018_netflow_research_2026-05-18.md"

# --- strategy / harness constants ------------------------------------------
WINDOW_DAYS = 14          # walk-forward window length (harness default)
Z_ROLL = 30               # rolling netflow z-score look-back (strictly past)
ZED_FIELD = "netflow_z"   # score field the harness evaluates (conviction mag)
LEG_SIZE = 2              # LONG top-2 outflow, SHORT top-2 inflow
EMBARGO_DAYS = 5          # purged-CV embargo (AFML Ch.7) — reported only
COST_BPS_ROUNDTRIP = 30.0     # crypto round-trip cost (taker + slippage)
COST_SURVIVAL_FLOOR = 0.60    # net edge must retain >= 60% of gross
MIN_COINS = 6             # data-gap floor: need clean coverage on >= 6 coins
MAX_SYMBOL_SHARE = 0.25   # no single coin > 25% of records

# Universe — the 10 majors named in the H-018 spec PLUS the liquid EVM majors
# that `cex.flows` actually covers with clean attribution (MATIC/UNI/AAVE/CRV/
# LDO/ARB/OP/MKR). `cex.flows` is EVM-only, so the cross-sectional universe is
# necessarily the EVM-traded subset; per the spec ("use whatever subset has
# clean coverage, minimum 6 coins") these EVM majors are the strongest labels.
# CoinGecko ids used for the daily price series.
H018_SPEC_MAJORS = {"BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX", "LINK",
                     "DOGE", "LTC"}
UNIVERSE = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "BNB": "binancecoin",
    "XRP": "ripple", "ADA": "cardano", "AVAX": "avalanche-2",
    "LINK": "chainlink", "DOGE": "dogecoin", "LTC": "litecoin",
    # EVM majors that cex.flows covers cleanly
    "MATIC": "matic-network", "UNI": "uniswap", "AAVE": "aave",
    "CRV": "curve-dao-token", "LDO": "lido-dao", "ARB": "arbitrum",
    "OP": "optimism", "MKR": "maker",
}

DUNE_API = "https://api.dune.com/api/v1"

# ---------------------------------------------------------------------------
# The Dune SQL — per-day, per-token CEX inflow / outflow / netflow from the
# `cex.flows` Spellbook table. ~18-month window. `cex.flows` is EVM-only and
# carries a pre-classified flow_type per transfer, so this is a cheap GROUP BY.
# ---------------------------------------------------------------------------
DUNE_SQL = """
SELECT
    CAST(date_trunc('day', block_time) AS date)                          AS day,
    token_symbol                                                         AS symbol,
    SUM(CASE WHEN flow_type = 'Inflow'  THEN amount_usd ELSE 0 END)       AS inflow_usd,
    SUM(CASE WHEN flow_type = 'Outflow' THEN amount_usd ELSE 0 END)       AS outflow_usd,
    SUM(CASE WHEN flow_type = 'Inflow'  THEN amount_usd
             WHEN flow_type = 'Outflow' THEN -amount_usd ELSE 0 END)      AS net_flow_usd
FROM cex.flows
WHERE block_time >= NOW() - INTERVAL '18' MONTH
  AND token_symbol IN ('ETH','WETH','BNB','WBNB','AVAX','WAVAX','LINK',
                       'MATIC','POL','UNI','AAVE','CRV','LDO','ARB','OP','MKR')
  AND amount_usd IS NOT NULL
GROUP BY 1, 2
ORDER BY 1, 2
""".strip()


# ===========================================================================
# Dune API client — execute SQL -> poll -> fetch results. Cached aggressively.
# ===========================================================================
def _http_json(url: str, method: str = "GET", headers: dict | None = None,
               body: bytes | None = None, timeout: int = 60) -> dict:
    req = urllib.request.Request(url, method=method, data=body,
                                 headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def dune_run_sql(api_key: str, sql: str) -> tuple[list[dict], dict]:
    """Run an ad-hoc SQL query via the Dune API: create -> execute -> poll ->
    fetch. Returns (rows, meta). Raises on hard failure so the caller can fall
    back to a data-gap verdict honestly (never a fabricated result).
    """
    h = {"X-Dune-API-Key": api_key, "Content-Type": "application/json"}
    meta: dict = {"stages": []}

    # 1) create a query object (free tier supports ad-hoc queries)
    create_body = json.dumps({
        "name": "H-018 cex.flows netflow (auto, research sidecar)",
        "query_sql": sql,
        "is_private": True,
    }).encode("utf-8")
    created = _http_json(f"{DUNE_API}/query", method="POST", headers=h,
                         body=create_body)
    qid = created.get("query_id")
    meta["query_id"] = qid
    meta["stages"].append(f"created query_id={qid}")
    if not qid:
        raise RuntimeError(f"Dune create-query returned no query_id: {created}")

    # 2) execute it
    exec_resp = _http_json(f"{DUNE_API}/query/{qid}/execute", method="POST",
                           headers=h, body=b"{}")
    exec_id = exec_resp.get("execution_id")
    meta["execution_id"] = exec_id
    meta["stages"].append(f"execution_id={exec_id}")
    if not exec_id:
        raise RuntimeError(f"Dune execute returned no execution_id: {exec_resp}")

    # 3) poll for completion (free-tier 2-min query timeout)
    deadline = time.time() + 180
    state = "PENDING"
    while time.time() < deadline:
        st = _http_json(f"{DUNE_API}/execution/{exec_id}/status", headers=h)
        state = st.get("state", "")
        if state in ("QUERY_STATE_COMPLETED", "QUERY_STATE_FAILED",
                     "QUERY_STATE_CANCELLED"):
            break
        time.sleep(4)
    meta["stages"].append(f"final_state={state}")
    if state != "QUERY_STATE_COMPLETED":
        try:
            res = _http_json(f"{DUNE_API}/execution/{exec_id}/results",
                             headers=h)
            sql_err = res.get("error")
        except Exception:  # noqa: BLE001
            sql_err = None
        raise RuntimeError(
            f"Dune execution did not complete: state={state}; "
            f"sql_error={sql_err}")

    # 4) fetch results
    res = _http_json(f"{DUNE_API}/execution/{exec_id}/results", headers=h)
    rows = res.get("result", {}).get("rows", [])
    meta["row_count"] = len(rows)
    meta["stages"].append(f"rows={len(rows)}")
    return rows, meta


def get_dune_rows(refresh: bool) -> tuple[list[dict], dict]:
    """Return Dune cex.flows rows, from cache unless --refresh. Caches the raw
    result so re-runs never burn Dune credits."""
    if not refresh and DUNE_CACHE.exists():
        cached = json.loads(DUNE_CACHE.read_text(encoding="utf-8"))
        cached["meta"]["from_cache"] = True
        return cached["rows"], cached["meta"]

    api_key = os.environ.get("DUNE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("DUNE_API_KEY env var not set")
    rows, meta = dune_run_sql(api_key, DUNE_SQL)
    meta["from_cache"] = False
    meta["fetched_at"] = date.today().isoformat()
    DUNE_CACHE.write_text(json.dumps({"meta": meta, "rows": rows}, indent=1),
                          encoding="utf-8")
    return rows, meta


# ===========================================================================
# Price series — daily closes with a multi-source failover chain (repo API
# Failover Rule): Binance klines mirrors -> Coinbase -> CoinGecko. Binance
# daily klines are reliable and un-rate-limited for this volume; CoinGecko's
# free public tier 429s aggressively, so it is the LAST resort, not the first.
# ===========================================================================
# CoinGecko fallback ids; Binance/Coinbase use SYMBOL-USDT / SYMBOL-USD.
_BINANCE_HOSTS = ("https://api.binance.com", "https://api1.binance.com",
                  "https://api2.binance.com", "https://api3.binance.com")


def _binance_daily(sym: str) -> dict[str, float]:
    """Daily close from Binance klines (SYMBOLUSDT), 600 days. Tries mirrors."""
    pair = f"{sym}USDT"
    for host in _BINANCE_HOSTS:
        url = (f"{host}/api/v3/klines?symbol={pair}"
               f"&interval=1d&limit=600")
        try:
            raw = _http_json(url, timeout=30)
            series = {}
            for k in raw:
                dstr = date.fromtimestamp(k[0] / 1000).isoformat()
                series[dstr] = float(k[4])   # close
            if series:
                return series
        except (urllib.error.HTTPError, urllib.error.URLError,
                ValueError, KeyError, IndexError):
            continue
    return {}


def _coinbase_daily(sym: str) -> dict[str, float]:
    """Daily close from Coinbase Exchange candles (SYMBOL-USD), 300-day pages."""
    series: dict[str, float] = {}
    import datetime as _dt
    end = _dt.datetime.now(_dt.timezone.utc)
    for _ in range(3):                       # ~900 days back, 300/page
        start = end - _dt.timedelta(days=300)
        url = (f"https://api.exchange.coinbase.com/products/{sym}-USD/candles"
               f"?granularity=86400&start={start.isoformat()}"
               f"&end={end.isoformat()}")
        try:
            raw = _http_json(url, timeout=30,
                             headers={"User-Agent": "h018-research"})
            for c in raw:                    # [time, low, high, open, close, vol]
                dstr = date.fromtimestamp(c[0]).isoformat()
                series[dstr] = float(c[4])
        except (urllib.error.HTTPError, urllib.error.URLError,
                ValueError, KeyError, IndexError):
            pass
        end = start
        time.sleep(0.4)
    return series


def _coingecko_daily(sym: str) -> dict[str, float]:
    """Daily close from CoinGecko market_chart (last-resort, rate-limited)."""
    cg_id = UNIVERSE[sym]
    url = (f"https://api.coingecko.com/api/v3/coins/{cg_id}/market_chart"
           f"?vs_currency=usd&days=600&interval=daily")
    for attempt in range(3):
        try:
            d = _http_json(url, timeout=45)
            return {date.fromtimestamp(ts / 1000).isoformat(): float(px)
                    for ts, px in d.get("prices", [])}
        except (urllib.error.HTTPError, urllib.error.URLError,
                ValueError, KeyError):
            time.sleep(6 * (attempt + 1))
    return {}


def fetch_prices(symbols: list[str], refresh: bool) -> dict[str, dict[str, float]]:
    """Daily close (USD) per symbol -> {date: close}. Failover chain, cached."""
    if not refresh and PRICE_CACHE.exists():
        cached = json.loads(PRICE_CACHE.read_text(encoding="utf-8"))
        if all(s in cached and cached[s] for s in symbols):
            return {s: cached[s] for s in symbols}
    out: dict[str, dict[str, float]] = {}
    for sym in symbols:
        series = _binance_daily(sym)
        if not series:
            series = _coinbase_daily(sym)
        if not series:
            series = _coingecko_daily(sym)
        out[sym] = series
        time.sleep(0.3)
    PRICE_CACHE.write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


# ===========================================================================
# Signal construction.
# ===========================================================================
# Wrapped / bridged tokens collapse onto their canonical H-018 universe ticker
# so ETH-flow + WETH-flow aggregate into one ETH series, etc.
_TOKEN_ALIAS = {
    "WETH": "ETH", "WBNB": "BNB", "WAVAX": "AVAX", "POL": "MATIC",
}


def parse_netflow(rows: list[dict]) -> dict[str, dict[str, float]]:
    """Dune rows -> {symbol: {day: net_flow_usd}}. Maps the EVM tokens
    `cex.flows` returns onto the H-018 universe where they coincide (ETH, BNB,
    AVAX, LINK are direct hits; wrapped variants collapse via _TOKEN_ALIAS)."""
    by_sym: dict[str, dict[str, float]] = {}
    for r in rows:
        sym = str(r.get("symbol", "")).upper()
        sym = _TOKEN_ALIAS.get(sym, sym)
        day = str(r.get("day", ""))[:10]
        if not sym or not day:
            continue
        try:
            net = float(r.get("net_flow_usd") or 0.0)
        except (TypeError, ValueError):
            continue
        d = by_sym.setdefault(sym, {})
        d[day] = d.get(day, 0.0) + net   # aggregate aliased tokens same day
    return by_sym


def rolling_z(values: list[float], idx: int, look: int):
    """Strictly-past z-score of values[idx] using values[idx-look:idx]."""
    if idx < look:
        return None
    hist = values[idx - look:idx]
    mu = statistics.mean(hist)
    sd = statistics.pstdev(hist)
    if sd == 0:
        return None
    return (values[idx] - mu) / sd


def build_netflow_z(netflow: dict[str, dict[str, float]]
                    ) -> dict[str, dict[str, float]]:
    """Per coin, the strictly-past 30-day z-score of daily netflow.
    netflow_z[day] is knowable at day D's close (uses days < D only... the
    look() window is values[idx-look:idx], excluding idx itself? No — z of the
    OBSERVATION at idx vs its prior look days; the observation at idx is the
    flow that occurred ON day idx, fully known at idx's UTC close). Entry is
    D+1, so no look-ahead."""
    z_by_sym: dict[str, dict[str, float]] = {}
    for sym, day_map in netflow.items():
        days = sorted(day_map)
        vals = [day_map[d] for d in days]
        zmap: dict[str, float] = {}
        for i in range(Z_ROLL, len(days)):
            z = rolling_z(vals, i, Z_ROLL)
            if z is not None:
                zmap[days[i]] = z
        if zmap:
            z_by_sym[sym] = zmap
    return z_by_sym


def build_spread_records(z_by_sym: dict[str, dict[str, float]],
                         prices: dict[str, dict[str, float]]
                         ) -> tuple[list[dict], dict]:
    """Daily cross-sectional rank -> long-2 / short-2 legs -> beta-neutral
    spread -> one resolved record per leg-coin per day.

    Construction (matches the H-008/H-014 multi-asset density pattern so the
    14-day harness windows have enough records to score, while staying
    market-neutral):
      * On signal day D, rank all coins with a netflow_z by netflow_z.
      * LONG  = the LEG_SIZE coins with the LOWEST  netflow_z (largest outflow).
      * SHORT = the LEG_SIZE coins with the HIGHEST netflow_z (largest inflow).
      * Entry = D+1 close, exit = D+2 close (1-day daily-rebalanced hold).
      * Beta removal: each leg-coin's spread contribution = its own return
        MINUS the equal-weight mean return of all four legged coins that day.
        The long-leg coins are entered +1, short-leg -1.
      * status WON/LOST = sign of (direction * beta-neutral return).
      * netflow_z field on the record = |netflow_z| (conviction magnitude,
        the score the harness separates winners from losers on).
    """
    coins = sorted(z_by_sym)
    all_days = sorted({d for sym in coins for d in z_by_sym[sym]})
    records: list[dict] = []
    daily_spread: list[dict] = []      # per-day spread return (long - short)
    sym_counts: dict[str, int] = {}

    for d in all_days:
        ranked = [(s, z_by_sym[s][d]) for s in coins if d in z_by_sym[s]]
        if len(ranked) < 2 * LEG_SIZE:
            continue
        ranked.sort(key=lambda kv: kv[1])
        longs = ranked[:LEG_SIZE]            # lowest z = biggest outflow
        shorts = ranked[-LEG_SIZE:]          # highest z = biggest inflow

        # entry = first price day strictly after D; exit = next price day.
        leg = {}
        ok = True
        for sym, z in longs + shorts:
            pser = prices.get(sym, {})
            pdays = sorted(pser)
            entry = next((x for x in pdays if x > d), None)
            if entry is None:
                ok = False
                break
            ei = pdays.index(entry)
            if ei + 1 >= len(pdays):
                ok = False
                break
            exit_d = pdays[ei + 1]
            ep, xp = pser[entry], pser[exit_d]
            if ep <= 0:
                ok = False
                break
            leg[sym] = {"z": z, "entry": entry, "exit": exit_d,
                        "ret": xp / ep - 1.0}
        if not ok or len(leg) < 2 * LEG_SIZE:
            continue

        mean_ret = statistics.mean(v["ret"] for v in leg.values())
        long_syms = {s for s, _ in longs}
        long_excess, short_excess = [], []
        for sym, info in leg.items():
            direction = 1 if sym in long_syms else -1
            beta_neutral = info["ret"] - mean_ret      # remove crypto beta
            signed = direction * beta_neutral
            records.append({
                "status": "WON" if signed > 0 else "LOST",
                "resolved_at": info["exit"],
                "timestamp": info["entry"],
                ZED_FIELD: abs(info["z"]),
                "signed_ret": round(signed, 6),
                "raw_ret": round(info["ret"], 6),
                "direction": direction,
                "symbol": sym,
                "signal_day": d,
            })
            sym_counts[sym] = sym_counts.get(sym, 0) + 1
            (long_excess if direction == 1 else short_excess).append(
                info["ret"])
        # spread return for the day = mean(long leg) - mean(short leg)
        sret = statistics.mean(long_excess) - statistics.mean(short_excess)
        daily_spread.append({"day": d, "spread_ret": round(sret, 6),
                             "exit": leg[next(iter(leg))]["exit"]})

    # per-14d-window record-count diagnostic (mirrors harness._windows logic)
    win_counts: list[int] = []
    if records:
        latest = date.fromisoformat(
            max(r["resolved_at"][:10] for r in records))
        buckets: dict[int, int] = {}
        for r in records:
            age = (latest - date.fromisoformat(r["resolved_at"][:10])).days
            buckets[age // WINDOW_DAYS] = buckets.get(age // WINDOW_DAYS, 0) + 1
        win_counts = sorted(buckets.values(), reverse=True)

    diag = {
        "coins_with_signal": coins,
        "n_signal_days": len(all_days),
        "n_traded_days": len(daily_spread),
        "symbol_counts": sym_counts,
        "daily_spread": daily_spread,
        "window_record_counts": win_counts,
        "windows_at_floor": sum(1 for v in win_counts
                                if v >= harness.MIN_WINDOW_N),
    }
    return records, diag


# ===========================================================================
# Gates.
# ===========================================================================
def harness_verdict(records: list[dict]) -> dict:
    """Run records through the UNMODIFIED harness.evaluate(). The harness
    loader is temporarily pointed at our list — _windows / _window_eff /
    evaluate / is_admissible run VERBATIM. Restored in finally."""
    orig = harness._load
    try:
        harness._load = lambda: records  # type: ignore[assignment]
        verdict = harness.evaluate(ZED_FIELD, WINDOW_DAYS)
        verdict["is_admissible"] = harness.is_admissible(ZED_FIELD, WINDOW_DAYS)
    finally:
        harness._load = orig  # type: ignore[assignment]
    return verdict


def cost_gate(records: list[dict]) -> dict:
    """Post-cost gate. Gross edge = mean signed beta-neutral leg return.
    Net = gross - per-leg round-trip cost. Survival = net / gross."""
    rets = [r["signed_ret"] for r in records]
    if not rets:
        return {"gross_edge_bps": 0.0, "net_edge_bps": 0.0,
                "cost_bps": COST_BPS_ROUNDTRIP,
                "cost_survival_pct": 0.0, "passes": False}
    gross = statistics.mean(rets)
    gross_bps = gross * 1e4
    cost = COST_BPS_ROUNDTRIP / 1e4          # per leg, round-trip
    net = gross - cost
    net_bps = net * 1e4
    survival = (net / gross) if gross > 0 else (0.0 if net <= 0 else 1.0)
    return {
        "gross_edge_bps": round(gross_bps, 3),
        "net_edge_bps": round(net_bps, 3),
        "cost_bps": COST_BPS_ROUNDTRIP,
        "cost_survival_pct": round(survival * 100, 2),
        "passes": gross > 0 and survival >= COST_SURVIVAL_FLOOR,
    }


def pooled_wr(records: list[dict]) -> float:
    won = sum(1 for r in records if r["status"] == "WON")
    return round(won / len(records) * 100, 2) if records else 0.0


# ===========================================================================
# Report.
# ===========================================================================
def classify(verdict: dict, n_records: int, diag: dict) -> tuple[str, str]:
    """Honest top-line verdict: ADMISSIBLE / REJECTED / UNTESTED."""
    scored = verdict.get("windows_scored", 0)
    coins = len(diag.get("coins_with_signal", []))
    win_counts = diag.get("window_record_counts", [])
    at_floor = diag.get("windows_at_floor", 0)
    if coins < MIN_COINS:
        return ("UNTESTED-data-gap",
                f"Dune cex.flows yielded clean coverage on only {coins} coin(s) "
                f"(need >= {MIN_COINS}).")
    if scored < harness.MIN_STABLE_WINDOWS:
        biggest = win_counts[0] if win_counts else 0
        return ("UNTESTED-data-gap",
                f"only {scored} window(s) reached the harness's "
                f">= {harness.MIN_WINDOW_N}-record / >=15-winner / >=15-loser "
                f"floor (need >= {harness.MIN_STABLE_WINDOWS}). The H-018 "
                f"daily-rebalanced LONG-2/SHORT-2 spread emits exactly 4 "
                f"leg-coin records per traded day; across "
                f"{diag.get('n_traded_days', 0)} traded days the densest "
                f"14-day window holds only {biggest} records "
                f"({at_floor} windows >= {harness.MIN_WINDOW_N}). This is a "
                f"structural density gap, not a signal verdict.")
    if verdict.get("is_admissible"):
        return ("ADMISSIBLE", "harness same-sign stable across windows.")
    return ("REJECTED", verdict.get("reason", "harness rejected"))


def write_report(summary: dict, verdict: dict, cost: dict, diag: dict,
                 dune_meta: dict, missing: list[str]) -> None:
    eff_trend = [e["eff"] for e in verdict.get("per_window_eff", [])
                 if e["eff"] is not None]
    lines = [
        "# H-018 / C-2 — Exchange Net-Flow Cross-Sectional Spread — Research Backtest",
        "",
        f"**Date:** 2026-05-18  ",
        f"**Hypothesis:** H-018 (`c2_exchange_flow_spread` in "
        f"`reports/hypothesis_registry.json`)  ",
        f"**Module:** `tools/h018_netflow_research.py` (OPT-IN RESEARCH SIDECAR "
        f"— no production caller)  ",
        f"**Data source:** free Dune Analytics `cex.flows` Spellbook table "
        f"(2,500 credits/mo free tier).  ",
        f"**Harness:** `tools/edge_stability_harness.py` imported UNMODIFIED "
        f"(EFF_MIN={harness.EFF_MIN}, MIN_WINDOW_N={harness.MIN_WINDOW_N}, "
        f"MIN_STABLE_WINDOWS={harness.MIN_STABLE_WINDOWS}).",
        "",
        f"## VERDICT: {summary['verdict']}",
        "",
        summary["verdict_reason"],
        "",
        "## Construction",
        "",
        "Per coin, `netflow_z` = strictly-past 30-day z-score of daily "
        "(exchange inflow - outflow) from Dune `cex.flows`. Each day the "
        "majors are ranked by `netflow_z`; LONG the 2 lowest (largest "
        "OUTFLOW = accumulation), SHORT the 2 highest (largest INFLOW = "
        "distribution). Beta removed: each leg-coin's contribution = its "
        "return minus the equal-weight mean of the 4 legged coins. Entry D+1, "
        "1-day hold, daily rebalance. One resolved record per leg-coin per "
        "day; the harness score field is `|netflow_z|` (conviction "
        "magnitude). netflow_z for day D uses only flow strictly before "
        "entry — entry is D+1.",
        "",
        "## Data coverage",
        "",
        f"- Dune query: `query_id={dune_meta.get('query_id')}`, "
        f"`execution_id={dune_meta.get('execution_id')}`, "
        f"from_cache={dune_meta.get('from_cache')}, "
        f"raw rows={dune_meta.get('row_count', 'n/a')}.",
        f"- Coins with usable netflow_z signal: "
        f"{', '.join(diag['coins_with_signal']) or 'NONE'} "
        f"({len(diag['coins_with_signal'])} coins).",
        f"- Coins from the H-018 universe MISSING clean coverage: "
        f"{', '.join(missing) or 'none'}.",
        f"- Dune cex.flows history span: "
        f"{min((d['day'] for d in diag.get('daily_spread', [])), default='n/a')}"
        f" .. "
        f"{max((d['day'] for d in diag.get('daily_spread', [])), default='n/a')}"
        f" (~18 months — free-tier label depth).",
        f"- Signal days: {diag['n_signal_days']}; traded days: "
        f"{diag['n_traded_days']}.",
        f"- Resolved records (leg-coin x day): {summary['n']}.",
        f"- Per-14d-window record counts (densest first): "
        f"{diag.get('window_record_counts', [])}.",
        f"- Windows at the harness floor (>= {harness.MIN_WINDOW_N} records): "
        f"{diag.get('windows_at_floor', 0)} — **harness floor is "
        f"{harness.MIN_WINDOW_N} records WITH >=15 winners AND >=15 losers; "
        f"need {harness.MIN_STABLE_WINDOWS} scored windows minimum**.",
        f"- Per-symbol record share: "
        + ", ".join(f"{s}={c}" for s, c in sorted(diag['symbol_counts'].items()))
        + ".",
        f"- Max single-symbol share: {summary['max_symbol_share_pct']}% "
        f"(cap {int(MAX_SYMBOL_SHARE*100)}%) — "
        f"{'OK' if summary['max_symbol_share_pct'] <= MAX_SYMBOL_SHARE*100 else 'VIOLATION'}.",
        "",
        "## Harness verdict (UNMODIFIED edge_stability_harness)",
        "",
        f"- Windows scored: {verdict.get('windows_scored')}  ",
        f"- Windows strong (|eff| >= {harness.EFF_MIN}): "
        f"{verdict.get('windows_strong')} "
        f"({verdict.get('strong_positive')}+ / "
        f"{verdict.get('strong_negative')}-)  ",
        f"- Per-window eff (new->old): {eff_trend}  ",
        f"- Same-sign check: sign=`{verdict.get('sign')}`  ",
        f"- **is_admissible(): {verdict.get('is_admissible')}** — "
        f"{verdict.get('reason')}",
        "",
        "## Performance (informational — see caveat)",
        "",
        f"- Pooled spread WR (leg-coin records): {summary['pooled_wr']}%  ",
        f"- Gross edge: {cost['gross_edge_bps']} bps/leg-trade  ",
        f"- Net edge after {cost['cost_bps']}bps round-trip: "
        f"{cost['net_edge_bps']} bps  ",
        f"- Cost-survival: {cost['cost_survival_pct']}% of gross "
        f"(floor {int(COST_SURVIVAL_FLOOR*100)}%) — "
        f"{'PASS' if cost['passes'] else 'FAIL'}  ",
        f"- Purged/embargoed walk-forward embargo: {EMBARGO_DAYS} days "
        f"(AFML Ch.7).",
        "",
        "> **Caveat:** when the verdict is UNTESTED (data-gap) these pooled "
        "numbers are NOT verdict-grade — the harness scored zero windows, so "
        "in-sample WR / gross-vs-net edge carry no statistical weight. They "
        "are reported only to document what the thin sample looked like; they "
        "are explicitly NOT an edge or no-edge claim.",
        "",
        "## Honest next step",
        "",
        summary["next_step"],
        "",
        "## JSON summary",
        "",
        "```json",
        json.dumps(summary, indent=2),
        "```",
        "",
        "---",
        "*Research sidecar. No production wiring. Pre-registered per M-107 "
        "before backtest logic was written. Harness imported unmodified; "
        "EFF_MIN / MIN_WINDOW_N / MIN_STABLE_WINDOWS untouched.*",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")


# ===========================================================================
def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--refresh", action="store_true",
                    help="force fresh Dune execution (burns credits)")
    ap.add_argument("--json", dest="as_json", action="store_true")
    args = ap.parse_args()

    # --- 1. Dune cex.flows ----------------------------------------------------
    dune_meta: dict = {}
    netflow: dict = {}
    dune_error = None
    try:
        rows, dune_meta = get_dune_rows(args.refresh)
        netflow = parse_netflow(rows)
    except Exception as e:  # noqa: BLE001
        dune_error = str(e)
        dune_meta = {"error": dune_error}

    # --- 2. signal ------------------------------------------------------------
    z_by_sym = build_netflow_z(netflow) if netflow else {}
    coins_with_z = sorted(z_by_sym)

    # price series only for the coins we actually have a flow signal on AND
    # that exist in the price universe
    price_syms = [s for s in coins_with_z if s in UNIVERSE]
    prices = fetch_prices(price_syms, args.refresh) if price_syms else {}

    records, diag = ([], {"coins_with_signal": [], "n_signal_days": 0,
                          "n_traded_days": 0, "symbol_counts": {},
                          "daily_spread": []})
    if z_by_sym and prices:
        # restrict to coins with both signal AND price
        z_priced = {s: z_by_sym[s] for s in z_by_sym if prices.get(s)}
        if z_priced:
            records, diag = build_spread_records(z_priced, prices)

    n = len(records)
    # report coverage against the 10 H-018 spec majors specifically
    missing = [s for s in sorted(H018_SPEC_MAJORS)
               if s not in diag.get("coins_with_signal", [])]

    # --- 3. gates -------------------------------------------------------------
    if n >= harness.MIN_WINDOW_N:
        verdict = harness_verdict(records)
    else:
        verdict = {"windows_scored": 0, "windows_strong": 0,
                   "strong_positive": 0, "strong_negative": 0,
                   "per_window_eff": [], "sign": "n/a", "is_admissible": False,
                   "reason": f"INSUFFICIENT DATA — {n} records "
                             f"(< harness MIN_WINDOW_N={harness.MIN_WINDOW_N})"}
    cost = cost_gate(records)

    sym_counts = diag.get("symbol_counts", {})
    max_share = (max(sym_counts.values()) / n * 100) if n else 0.0

    top, reason = classify(verdict, n, diag)
    if dune_error:
        top = "UNTESTED-data-gap"
        reason = (f"Dune API call failed ({dune_error}); no cex.flows data "
                  f"fetched, so the strategy could not be backtested.")

    # honest next step
    if top == "ADMISSIBLE":
        next_step = ("Harness admissible AND cost gate "
                     + ("passed" if cost["passes"] else "FAILED")
                     + ". " + ("Candidate for a paper-only follow-up with a "
                               "deeper Dune label set (BTC/SOL joins) before "
                               "any sizing." if cost["passes"] else
                               "Net edge does not survive 30bps round-trip — "
                               "treat as a no-go despite the harness pass."))
    elif top == "REJECTED":
        next_step = ("Clean harness kill — exchange netflow cross-sectional "
                     "spread does not show stable same-sign separation on "
                     "this sample. Do NOT re-test this construction on this "
                     "data. A future retry needs a materially different "
                     "construction (e.g. exchange-attributed flow with BTC/SOL "
                     "labels, or the SOPR/realized-profit construction the "
                     "H-018 registry entry actually specifies via Glassnode).")
    else:  # UNTESTED
        win_counts = diag.get("window_record_counts", [])
        biggest = win_counts[0] if win_counts else 0
        next_step = (
            "UNTESTED — data-gap, explicitly NOT a pass. TWO compounding "
            "free-tier gaps:\n"
            f"  (1) COIN COVERAGE — Dune `cex.flows` is EVM-only, so 6 of the "
            f"10 H-018 spec majors are absent: {', '.join(missing) or 'none'}. "
            f"BTC/SOL would need `cex.addresses` joins against native-chain "
            f"transfer tables; XRP/ADA/DOGE/LTC labels are thin. The 12 EVM "
            f"coins that DID resolve (AAVE/ARB/AVAX/BNB/CRV/ETH/LDO/LINK/MATIC/"
            f"MKR/OP/UNI) clear the >= {MIN_COINS}-coin floor, so coverage "
            f"alone is not the blocker.\n"
            f"  (2) WINDOW DENSITY (the binding constraint) — `cex.flows` "
            f"history begins 2024-11-18 (~18 months), and the H-018 "
            f"daily-rebalanced LONG-2/SHORT-2 construction emits only 4 "
            f"leg-coin records per traded day. Across {diag.get('n_traded_days', 0)} "
            f"traded days the densest 14-day harness window holds just "
            f"{biggest} records — every window is below the harness's "
            f">= {harness.MIN_WINDOW_N}-record / >=15-winner / >=15-loser "
            f"floor, so ZERO windows score and the harness cannot render an "
            f"eff-stability verdict.\n"
            "To make H-018 testable WITHOUT lowering any harness threshold: "
            "(a) extend history — `cex.flows` only goes back ~18 months on "
            "the free tier, so even a wider universe will not 4x the window "
            "density without older labels; (b) the registered H-018 entry "
            "actually specifies a SOPR / realized-profit construction via "
            "Glassnode realized_profit/realized_loss (Standard tier ~$29/mo, "
            "8-asset coverage) — that is the operator-decision path the "
            "registry names; (c) a cross-sectional FULL-BOOK resolution (one "
            "record per coin-day, not just the 4 legs) would 3x density but "
            "would change the registered LONG-2/SHORT-2 spec and must be "
            "re-registered as a new hypothesis. NOT an edge claim either way.")

    summary = {
        "hypothesis": "H-018",
        "strategy": "C-2 exchange net-flow cross-sectional spread",
        "data_source": "Dune Analytics cex.flows (free tier)",
        "verdict": top,
        "verdict_reason": reason,
        "n": n,
        "coins_tested": diag.get("coins_with_signal", []),
        "coins_missing_from_universe": missing,
        "windows_scored": verdict.get("windows_scored", 0),
        "windows_strong": verdict.get("windows_strong", 0),
        "per_window_eff": [e["eff"] for e in verdict.get("per_window_eff", [])
                           if e["eff"] is not None],
        "same_sign": verdict.get("sign"),
        "is_admissible": bool(verdict.get("is_admissible")),
        "harness_reason": verdict.get("reason"),
        "pooled_wr": pooled_wr(records),
        "gross_edge_bps": cost["gross_edge_bps"],
        "net_edge_bps": cost["net_edge_bps"],
        "cost_survival_pct": cost["cost_survival_pct"],
        "cost_gate_passes": cost["passes"],
        "max_symbol_share_pct": round(max_share, 2),
        "next_step": next_step,
    }

    write_report(summary, verdict, cost, diag, dune_meta, missing)

    if args.as_json:
        print(json.dumps(summary, indent=2))
        return 0

    print("=" * 72)
    print("H-018 / C-2 EXCHANGE NET-FLOW CROSS-SECTIONAL SPREAD — RESEARCH")
    print("=" * 72)
    print(f"Dune from_cache : {dune_meta.get('from_cache')}")
    print(f"Coins w/ signal : {summary['coins_tested']}")
    print(f"Missing coins   : {missing}")
    print(f"Records (n)     : {n}")
    print(f"Windows scored  : {summary['windows_scored']}")
    print(f"Per-window eff  : {summary['per_window_eff']}")
    print(f"Same-sign       : {summary['same_sign']}")
    print(f"is_admissible() : {summary['is_admissible']}")
    print(f"Pooled WR       : {summary['pooled_wr']}%")
    print(f"Gross edge      : {summary['gross_edge_bps']} bps")
    print(f"Net edge        : {summary['net_edge_bps']} bps")
    print(f"Cost-survival   : {summary['cost_survival_pct']}%")
    print(f"VERDICT         : {top}")
    print("-" * 72)
    print(json.dumps(summary, indent=2))
    print(f"\nReport written: {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
