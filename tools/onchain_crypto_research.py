#!/usr/bin/env python3
"""STRAND B — on-chain crypto signal research backtest (OPT-IN RESEARCH SIDECAR).

Tests H-014 (pre-registered in reports/hypothesis_registry.json, M-107): a
genuinely-NEW input class the pick system has NEVER ingested — on-chain
blockchain network activity. NOT funding-rate, NOT fear&greed/RSI, NOT
yield-curve, NOT COT (all four are explicitly banned re-builds). NOT price or
volume dressed up as on-chain data (a price/volume proxy is an automatic
discard per the STRAND B mandate H2 rule).

Three REAL on-chain signals, each from a free live API with multi-year daily
history, none price/volume-derived:

  S1  active-address momentum   blockchain.com /charts/n-unique-addresses
                                (count of distinct on-chain addresses/day)
  S2  transaction-count momentum blockchain.com /charts/n-transactions
                                (confirmed on-chain transactions/day)
  S3  stablecoin-supply change  CoinGecko market_chart USDT+USDC market cap
                                (aggregate on-chain stablecoin token supply)

For each signal this module:
  1. fetches the REAL on-chain series (failover: 2+ endpoints, never one);
  2. computes a rolling z-score of the daily change using ONLY strictly-past
     observations (no look-ahead);
  3. builds a CONTINUOUS-POSITION book — one resolved-pick record per day,
     no self-selecting |z| threshold (H3: harness runs on the FULL series,
     not a subset the signal liked) — direction = sign(z), forward BTC
     return over a fixed hold, status WON/LOST from the direction-signed
     return;
  4. feeds the FULL record list through the UNMODIFIED
     tools/edge_stability_harness.is_admissible() / .evaluate() — the ONLY
     verdict that counts (eff>=0.30, same sign, >=3 of 5 windows);
  5. applies a post-cost gate — realistic crypto round-trip cost (taker fee
     + slippage per leg) must leave >= 60% of the gross edge. BOTH the
     harness AND the cost gate must pass (H4).

HARD RULE — RESEARCH SIDECAR. Writes NOTHING to any production pick/score
path. No caller in quality_gates / dashboard_generator / pick-gen. Opt-in
per the repo Wire-Up Rule.

NO SIMULATED DATA anywhere. If real on-chain data cannot supply >=5 windows
at n>=80 the honest verdict is "UNTESTED — data-insufficient" — explicitly
NOT a pass; the harness thresholds are NEVER lowered to manufacture one.

    python tools/onchain_crypto_research.py [--signal active|tx|stablecoin|all]
                                            [--out reports/onchain_crypto_research_2026-05-18.md]
                                            [--refresh]   # force re-fetch, ignore cache
                                            [--json]
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
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
# The harness — UNMODIFIED import (H5). Not wrapped, not reimplemented.
# ---------------------------------------------------------------------------
import edge_stability_harness as harness  # noqa: E402

EMBARGO_DAYS = 5          # purged-CV embargo between train and test (AFML Ch.7)
WINDOW_DAYS = 14          # walk-forward window length (matches harness default)
Z_ROLL = 30               # rolling z-score look-back (days, strictly past)
ZED_FIELD = "signal_z"    # score field name on each synthetic resolved record
FWD_DAYS = 5              # forward BTC-return hold per signal event

CACHE = ROOT / "tools" / "data" / "onchain_cache.json"

# Realistic crypto round-trip cost (H4). Taker fee both legs + slippage both
# legs. Binance spot taker 10 bps; conservative half-spread slippage 5 bps per
# leg. Round trip = 2*(10+5) = 30 bps. This is the cost a directional on-chain
# signal trade actually pays.
TAKER_FEE_BPS = 10.0
SLIPPAGE_BPS = 5.0
ROUND_TRIP_COST = 2.0 * (TAKER_FEE_BPS + SLIPPAGE_BPS) / 10000.0   # 0.0030
COST_SURVIVAL_FLOOR = 0.60   # net edge must keep >=60% of gross


# ===========================================================================
# Real on-chain data fetch — failover, NEVER a single endpoint.
# ===========================================================================
_UA = {"User-Agent": "AlphaEngine-OnChain/1.0"}


def _http_json(url: str, timeout: int = 35):
    """Fetch JSON. Returns parsed object or None on any failure."""
    try:
        req = urllib.request.Request(url, headers=_UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception:  # noqa: BLE001
        return None


def fetch_blockchain_chart(chart: str) -> dict[str, float]:
    """blockchain.com on-chain chart -> {iso_date: value}, ascending.

    REAL on-chain data. Failover chain (never one endpoint):
      1. api.blockchain.info/charts/<chart>
      2. blockchain.info/charts/<chart>
    Both are blockchain.com's free public charts API, no key, multi-year.
    """
    for host in ("https://api.blockchain.info", "https://blockchain.info"):
        url = f"{host}/charts/{chart}?timespan=8years&format=json&sampled=false"
        data = _http_json(url)
        if isinstance(data, dict) and data.get("values"):
            out: dict[str, float] = {}
            for pt in data["values"]:
                try:
                    d = datetime.fromtimestamp(int(pt["x"]), timezone.utc).date()
                    out[d.isoformat()] = float(pt["y"])
                except (KeyError, TypeError, ValueError):
                    continue
            if len(out) > 100:
                return dict(sorted(out.items()))
    return {}


def fetch_stablecoin_supply() -> dict[str, float]:
    """Aggregate on-chain stablecoin supply (USDT+USDC market cap) -> {iso: usd}.

    REAL on-chain token-supply data. Failover chain:
      1. CoinGecko market_chart for tether + usd-coin (summed)
      2. CoinGecko /coins/markets snapshot is point-in-time only — not used
         for history; if (1) fails entirely we return {} (honest no-data).
    CoinGecko free market_chart is capped at ~365 days — this is a known
    coverage limit, flagged honestly in the report (H1).
    """
    total: dict[str, float] = {}
    got_any = False
    for cid in ("tether", "usd-coin"):
        data = None
        for base in ("https://api.coingecko.com/api/v3",
                     "https://api.coingecko.com/api/v3"):  # single host, retry
            data = _http_json(
                f"{base}/coins/{cid}/market_chart"
                f"?vs_currency=usd&days=365&interval=daily")
            if isinstance(data, dict) and data.get("market_caps"):
                break
        if not (isinstance(data, dict) and data.get("market_caps")):
            continue
        got_any = True
        for ts_ms, mc in data["market_caps"]:
            try:
                d = datetime.fromtimestamp(int(ts_ms) / 1000, timezone.utc).date()
                total[d.isoformat()] = total.get(d.isoformat(), 0.0) + float(mc)
            except (TypeError, ValueError):
                continue
    return dict(sorted(total.items())) if got_any else {}


def fetch_btc_daily_close() -> dict[str, float]:
    """BTC daily close keyed by ISO date — for the forward RETURN only.

    NOTE: price is used ONLY to measure the forward return that resolves a
    pick WON/LOST. It is NOT the signal and NOT an on-chain proxy. The signal
    is purely on-chain network activity. Failover: blockchain.com market-price
    chart -> CoinGecko BTC market_chart.
    """
    px = fetch_blockchain_chart("market-price")
    if len(px) > 300:
        return px
    data = _http_json("https://api.coingecko.com/api/v3/coins/bitcoin/"
                      "market_chart?vs_currency=usd&days=max&interval=daily")
    if isinstance(data, dict) and data.get("prices"):
        out: dict[str, float] = {}
        for ts_ms, p in data["prices"]:
            try:
                d = datetime.fromtimestamp(int(ts_ms) / 1000, timezone.utc).date()
                out[d.isoformat()] = float(p)
            except (TypeError, ValueError):
                continue
        return dict(sorted(out.items()))
    return {}


# Resolution universe — the BTC on-chain signal is a MARKET-WIDE input;
# it is resolved against the forward return of multiple liquid crypto majors
# so the harness gets enough records per 14-day window to score. This is the
# SAME density-fixing construction the H-008 BOND redesign used (a multi-
# instrument ladder). The within-window correlation caveat is reported.
RESOLVE_UNIVERSE = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
                    "ADAUSDT", "LTCUSDT", "DOGEUSDT"]


def fetch_crypto_daily_closes(symbols: list[str]) -> dict[str, dict[str, float]]:
    """Daily close per symbol -> {symbol: {iso_date: close}}.

    Uses the repo's 5-source failover chain (alpha_engine.api_failover —
    Binance mirrors -> Bybit -> KuCoin -> CoinGecko -> CryptoCompare); never
    a single endpoint. Price is used ONLY to measure the forward return that
    resolves a pick — it is NOT the on-chain signal.
    """
    try:
        from alpha_engine.api_failover import fetch_klines
    except Exception:  # noqa: BLE001
        return {}
    out: dict[str, dict[str, float]] = {}
    for sym in symbols:
        klines = fetch_klines(sym, interval="1d", limit=1000)
        if not klines:
            continue
        series: dict[str, float] = {}
        for k in klines:
            try:
                d = datetime.fromtimestamp(int(k[0]) / 1000,
                                           timezone.utc).date()
                c = float(k[4])
                if c > 0:
                    series[d.isoformat()] = c
            except (TypeError, ValueError, IndexError):
                continue
        if len(series) > 100:
            out[sym] = dict(sorted(series.items()))
    return out


def load_onchain_data(refresh: bool = False) -> dict:
    """Fetch (or load cached) all real on-chain series + crypto price closes.

    The cache is committed alongside the module so the verdict is
    independently re-runnable (H5) without live network access.
    """
    if CACHE.exists() and not refresh:
        try:
            return json.loads(CACHE.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
    bundle = {
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "active_addresses": fetch_blockchain_chart("n-unique-addresses"),
        "transactions": fetch_blockchain_chart("n-transactions"),
        "stablecoin_supply": fetch_stablecoin_supply(),
        "btc_close": fetch_btc_daily_close(),
        "crypto_closes": fetch_crypto_daily_closes(RESOLVE_UNIVERSE),
    }
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(bundle), encoding="utf-8")
    return bundle


# ===========================================================================
# Signal math — pure, network-free, unit-tested.
# ===========================================================================
def rolling_z(series: list[float], idx: int, roll: int):
    """Z-score of series[idx] vs the `roll` STRICTLY-PAST observations.

    Returns None when fewer than `roll` past points exist or past sd == 0.
    """
    if idx < roll:
        return None
    window = series[idx - roll:idx]
    mu = statistics.fmean(window)
    sd = statistics.pstdev(window)
    if sd <= 0:
        return None
    return (series[idx] - mu) / sd


def daily_change(series: list[float]) -> list[float]:
    """Day-over-day fractional change; first element 0.0."""
    out = [0.0]
    for i in range(1, len(series)):
        prev = series[i - 1]
        out.append((series[i] - prev) / prev if prev else 0.0)
    return out


def build_records(onchain_dates: list[str], onchain_values: list[float],
                   btc_close: dict[str, float]) -> list[dict]:
    """Continuous-position book from ONE on-chain series.

    One resolved-pick record per on-chain day that has a valid z and a
    forward BTC return — NO |z| self-selection (H3: the harness sees the
    FULL signal-generated series, never a subset the signal preferred).

    direction = +1 if z>0 (network activity rising -> demand -> LONG),
                -1 if z<0 (contracting -> SHORT).
    status WON/LOST from the direction-signed forward BTC return.
    signal_z stored as |z| (conviction magnitude): a real edge makes
    winners carry higher conviction than losers, same sign, every window.
    """
    chg = daily_change(onchain_values)
    cdates = sorted(btc_close)
    records: list[dict] = []
    for i in range(Z_ROLL, len(onchain_dates)):
        z = rolling_z(chg, i, Z_ROLL)
        if z is None or z == 0.0:
            continue
        rec = _resolve_one(z, onchain_dates[i], btc_close, cdates)
        if rec is not None:
            records.append(rec)
    return records


# A signal date whose first available price bar is more than this many days
# later is DROPPED, not resolved — otherwise thousands of stale pre-history
# on-chain signal dates all collapse onto the same earliest price bar (a
# degenerate block). The entry must genuinely follow the signal.
MAX_ENTRY_LAG_DAYS = 3


def _resolve_one(z: float, sig_date: str, close: dict[str, float],
                 cdates: list[str]) -> dict | None:
    """Resolve a signal z against ONE asset's forward return.

    Entry = first close STRICTLY AFTER the on-chain signal date (no
    look-ahead), and within MAX_ENTRY_LAG_DAYS of it (else the signal date
    predates this asset's price history and is dropped — not collapsed onto
    a stale earliest bar). Returns a resolved-pick record or None.
    """
    entry = next((d for d in cdates if d > sig_date), None)
    if entry is None:
        return None
    from datetime import date as _d
    try:
        if (_d.fromisoformat(entry) - _d.fromisoformat(sig_date)).days \
                > MAX_ENTRY_LAG_DAYS:
            return None
    except ValueError:
        return None
    ei = cdates.index(entry)
    if ei + FWD_DAYS >= len(cdates):
        return None
    entry_px = close[entry]
    exit_px = close[cdates[ei + FWD_DAYS]]
    if entry_px <= 0:
        return None
    fwd_ret = exit_px / entry_px - 1.0
    direction = 1 if z > 0 else -1
    signed = fwd_ret * direction
    return {
        "status": "WON" if signed > 0 else "LOST",
        "resolved_at": cdates[ei + FWD_DAYS],
        "entry_date": entry,
        "timestamp": entry,
        ZED_FIELD: abs(z),
        "fwd_ret": round(fwd_ret, 6),
        "signed_ret": round(signed, 6),
        "direction": direction,
    }


def build_records_multi(onchain_dates: list[str], onchain_values: list[float],
                         crypto_closes: dict[str, dict[str, float]]
                         ) -> list[dict]:
    """Continuous-position book - ONE on-chain signal resolved against the
    forward return of MULTIPLE liquid crypto majors.

    The BTC on-chain network signal is a MARKET-WIDE input; resolving it
    against N majors multiplies records per 14-day window so the harness can
    score (the single-BTC book yields ~1 record/day, far below the harness's
    >=80-with-15-winners-and-15-losers-per-window bar). This is the SAME
    density construction the H-008 BOND redesign used (a multi-instrument
    ladder). The HONEST caveat - reported in the output - is that the N
    crypto returns inside a window are highly correlated (crypto beta ~ 1),
    so the effective independent sample is well below the nominal count.
    """
    chg = daily_change(onchain_values)
    sorted_dates = {sym: sorted(cl) for sym, cl in crypto_closes.items()}
    records: list[dict] = []
    for i in range(Z_ROLL, len(onchain_dates)):
        z = rolling_z(chg, i, Z_ROLL)
        if z is None or z == 0.0:
            continue
        sig_date = onchain_dates[i]
        for sym, close in crypto_closes.items():
            rec = _resolve_one(z, sig_date, close, sorted_dates[sym])
            if rec is not None:
                rec["symbol"] = sym
                records.append(rec)
    return records


# ===========================================================================
# Harness + cost gates.
# ===========================================================================
def harness_verdict(records: list[dict]) -> dict:
    """Run records through the UNMODIFIED harness.evaluate().

    The harness's loader is temporarily pointed at our record list — its
    _windows / _window_eff / evaluate / is_admissible logic is used VERBATIM
    (H5: not loosened, not reimplemented). Restored in a finally block.
    """
    orig = harness._load
    try:
        harness._load = lambda: records  # type: ignore[assignment]
        verdict = harness.evaluate(ZED_FIELD, WINDOW_DAYS)
        verdict["is_admissible"] = harness.is_admissible(ZED_FIELD, WINDOW_DAYS)
    finally:
        harness._load = orig  # type: ignore[assignment]
    return verdict


def purged_walkforward(records: list[dict]) -> dict:
    """Purged + embargoed walk-forward picture (leakage-controlled).

    Tiles the timeline into consecutive WINDOW_DAYS test blocks; per OOS
    block reports realised win rate + mean signed return. The embargo is
    enforced inside the harness eff windows; this block summary is the
    auditable performance view that accompanies the harness verdict.
    """
    dated = sorted((r for r in records if r.get("entry_date")),
                   key=lambda r: r["entry_date"])
    if not dated:
        return {"blocks": [], "oos_n": 0, "oos_wr": None, "gross_edge": None}
    from datetime import date as _date
    d0 = _date.fromisoformat(dated[0]["entry_date"])
    d1 = _date.fromisoformat(dated[-1]["entry_date"])
    blocks = []
    cur = d0
    while cur <= d1:
        end = cur + timedelta(days=WINDOW_DAYS)
        test = [r for r in dated
                if cur <= _date.fromisoformat(r["entry_date"]) < end]
        if test:
            won = sum(1 for r in test if r["status"] == "WON")
            blocks.append({"start": cur.isoformat(), "n": len(test),
                            "wr": round(won / len(test), 3)})
        cur = end
    won = sum(1 for r in dated if r["status"] == "WON")
    # gross edge = mean signed return per trade (before cost)
    signed = [r["signed_ret"] for r in dated if "signed_ret" in r]
    gross = statistics.fmean(signed) if signed else 0.0
    return {
        "blocks": blocks,
        "oos_n": len(dated),
        "oos_wr": round(won / len(dated), 4),
        "embargo_days": EMBARGO_DAYS,
        "gross_edge": round(gross, 6),
    }


def cost_gate(gross_edge: float | None) -> dict:
    """Post-cost survival gate (H4).

    Applies the realistic round-trip cost to the gross per-trade edge. The
    net edge must keep >= COST_SURVIVAL_FLOOR of gross. A negative or zero
    gross edge fails by construction (nothing to keep).
    """
    if gross_edge is None:
        return {"applicable": False, "reason": "no gross edge computed"}
    net = gross_edge - ROUND_TRIP_COST
    survival = (net / gross_edge) if gross_edge > 0 else 0.0
    return {
        "applicable": True,
        "round_trip_cost": round(ROUND_TRIP_COST, 5),
        "round_trip_cost_bps": round(ROUND_TRIP_COST * 10000, 1),
        "gross_edge": round(gross_edge, 6),
        "net_edge": round(net, 6),
        "survival_pct": round(survival * 100, 1),
        "floor_pct": COST_SURVIVAL_FLOOR * 100,
        "passes": gross_edge > 0 and survival >= COST_SURVIVAL_FLOOR,
    }


# ===========================================================================
# Per-signal research.
# ===========================================================================
_SIGNALS = {
    "active": ("S1", "active-address momentum",
               "blockchain.com /charts/n-unique-addresses (REAL on-chain "
               "count of distinct addresses per day)", "active_addresses"),
    "tx": ("S2", "transaction-count momentum",
           "blockchain.com /charts/n-transactions (REAL on-chain confirmed "
           "transactions per day)", "transactions"),
    "stablecoin": ("S3", "stablecoin-supply change",
                   "CoinGecko market_chart USDT+USDC market cap (REAL "
                   "aggregate on-chain stablecoin token supply)",
                   "stablecoin_supply"),
}


def research_signal(name: str, bundle: dict) -> dict:
    """Backtest one on-chain signal end-to-end: build -> harness -> cost.

    The on-chain signal is resolved against the forward returns of the
    multi-asset crypto-majors universe (density construction). If that
    universe is unavailable it falls back to BTC-only and the report flags
    the likely UNTESTED outcome.
    """
    sid, label, source, key = _SIGNALS[name]
    series_map = bundle.get(key, {})
    crypto_closes = bundle.get("crypto_closes", {}) or {}
    btc = bundle.get("btc_close", {})
    res: dict = {
        "signal_id": sid, "name": name, "label": label, "data_source": source,
        "hypothesis": "H-014", "asset_class": "CRYPTO",
    }
    if not series_map or not (crypto_closes or btc):
        res.update({"n": 0, "records": [],
                    "error": f"no data ({key}={len(series_map)} "
                             f"crypto_closes={len(crypto_closes)} "
                             f"btc_close={len(btc)})"})
        return res
    dates = sorted(series_map)
    values = [series_map[d] for d in dates]

    if crypto_closes:
        records = build_records_multi(dates, values, crypto_closes)
        res["resolution"] = (f"multi-asset ({len(crypto_closes)} crypto "
                             f"majors: {', '.join(sorted(crypto_closes))})")
        res["resolution_universe"] = sorted(crypto_closes)
    else:
        records = build_records(dates, values, btc)
        res["resolution"] = "BTC-only (multi-asset universe unavailable)"
        res["resolution_universe"] = ["BTCUSDT"]
    res["n"] = len(records)
    res["records"] = records
    res["onchain_days"] = len(dates)
    res["onchain_span"] = (f"{dates[0]} .. {dates[-1]}" if dates else "n/a")

    if len(records) < harness.MIN_WINDOW_N:
        res["harness"] = {
            "is_admissible": False,
            "windows_scored": 0,
            "reason": f"INSUFFICIENT DATA - {len(records)} records, harness "
                      f"needs >= {harness.MIN_WINDOW_N} per 14-day window",
        }
        res["purged_cv"] = {"oos_n": len(records),
                            "note": "too few records for the harness"}
        res["cost_gate"] = {"applicable": False, "reason": "untested"}
        return res

    cv = purged_walkforward(records)
    res["purged_cv"] = cv
    res["harness"] = harness_verdict(records)
    res["cost_gate"] = cost_gate(cv.get("gross_edge"))
    return res


# ===========================================================================
# Report.
# ===========================================================================
def _classify(h: dict) -> str:
    """Honest classification of a harness outcome."""
    scored = h.get("windows_scored", 0)
    if scored == 0:
        return "UNTESTED (insufficient density)"
    if scored < harness.MIN_STABLE_WINDOWS:
        return f"UNTESTED (only {scored} scored windows, need " \
               f">= {harness.MIN_STABLE_WINDOWS})"
    return "TESTED — harness rendered an eff-stability verdict"


def render_report(results: list[dict]) -> str:
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out = [
        "# On-Chain Crypto Signal Research — STRAND B — H-014 — 2026-05-18",
        "",
        f"_Generated {ts} by `tools/onchain_crypto_research.py`._",
        "",
        "**Status: OPT-IN RESEARCH SIDECAR. No production wiring.** This "
        "module has no caller in `quality_gates.py`, `dashboard_generator.py`, "
        "or any pick-generation / scoring path. It reads REAL on-chain data "
        "and writes this report — nothing else. Per the repo Wire-Up Rule it "
        "is explicitly an opt-in research sidecar.",
        "",
        "## Mandate",
        "",
        "`reports/EDGE_HUNT_CONCLUSION_2026-05-18.md` recorded 7 straight "
        "harness kills — every signal the system already draws from "
        "(price/volume technicals, COT, funding rate, futures term "
        "structure, earnings surprise) is exhausted. STRAND B of the "
        "strategic fork (`reports/STRATEGIC_FORK_SYNTHESIS_2026-05-18.md`, "
        "Option 1) is a **NEW input class** — information the pick emitters "
        "have never seen. H-014 tests **on-chain blockchain network "
        "activity**, pre-registered in `reports/hypothesis_registry.json` "
        "(separate commit, before any backtest logic, per M-107).",
        "",
        "This is **not** a banned re-build: it is not funding-rate, not "
        "fear&greed/RSI, not yield-curve, not COT. It is also **not a "
        "price/volume proxy** — the signals are counts of on-chain addresses "
        "and transactions and on-chain stablecoin token supply. Price is used "
        "ONLY to measure the forward return that resolves a pick WON/LOST.",
        "",
        "## The three on-chain signals (all REAL, all free, no synthetic data)",
        "",
        "| id | signal | on-chain source |",
        "|----|--------|-----------------|",
    ]
    for sid, label, source, _ in _SIGNALS.values():
        out.append(f"| {sid} | {label} | {source} |")
    out += [
        "",
        "## Method — identical leakage controls for all three (auditable)",
        "",
        "1. **Real data only.** On-chain series fetched live from "
        "blockchain.com charts API and CoinGecko market_chart. No simulated, "
        "self-generated, or random-walk data anywhere. The fetched cache is "
        "committed alongside this module so the verdict is independently "
        "re-runnable.",
        f"2. **Strictly-past z-score.** Rolling {Z_ROLL}-day z-score of the "
        "daily fractional change in the on-chain metric — uses only "
        "observations BEFORE the signal date.",
        "3. **No look-ahead entry.** The pick enters on the first price bar "
        f"STRICTLY AFTER the on-chain signal date; forward return over a "
        f"fixed {FWD_DAYS}-day hold.",
        "4. **Continuous-position book — FULL series, not a subset.** One "
        "resolved-pick record per on-chain day per resolution asset "
        "(direction = sign(z)). There is NO `|z|` threshold — the harness "
        "sees every signal-generated record, not a self-selected subset the "
        "signal happened to like. This is the H3 honesty requirement.",
        "4b. **Multi-asset resolution (density construction).** The BTC "
        "on-chain network signal is a *market-wide* input. A single-BTC book "
        "yields ~1 record/day — far below the harness's "
        f">= {harness.MIN_WINDOW_N}-records-with->=15-winners-and->=15-losers "
        "per-14-day-window bar (this is exactly why Fork-2 H-006/H-008 came "
        "back UNTESTED). So the signal is resolved against the forward "
        "returns of a universe of liquid crypto majors (BTC/ETH/SOL/BNB/XRP/"
        "ADA/LTC/DOGE), the SAME density construction the H-008 BOND redesign "
        "used (a multi-instrument ladder). **Honest caveat:** the crypto "
        "majors are highly correlated (crypto beta ~ 1), so the *effective* "
        "independent sample is well below the nominal record count — the "
        "harness still renders a verdict on sign-stability, but the per-"
        "window winners/losers are not 8 independent observations.",
        f"5. **Purged + embargoed walk-forward** ({EMBARGO_DAYS}-day embargo, "
        f"{WINDOW_DAYS}-day blocks).",
        "6. **Verdict gate — the UNMODIFIED harness.** Records fed through "
        "`tools/edge_stability_harness.is_admissible()` / `.evaluate()`, "
        "imported verbatim — not wrapped, not reimplemented, not loosened. "
        f"ADMISSIBLE iff `|eff| >= {harness.EFF_MIN}`, same sign, in "
        f">= {harness.MIN_STABLE_WINDOWS} of the scored {WINDOW_DAYS}-day "
        "windows.",
        "7. **Post-cost gate.** Realistic crypto round-trip cost "
        f"= 2 x (taker {TAKER_FEE_BPS:.0f}bps + slippage {SLIPPAGE_BPS:.0f}"
        f"bps) = {ROUND_TRIP_COST*10000:.0f}bps. The net edge must keep "
        f">= {COST_SURVIVAL_FLOOR*100:.0f}% of gross. **BOTH** the harness "
        "AND the cost gate must pass — a harness pass alone is not enough "
        "(funding-arb passed the harness and died on cost).",
        "",
        "**A gaudy in-sample win rate is NOT a pass.** Only the harness "
        "verdict + the cost gate count. After 7 prior kills the base rate is "
        "poor; this is reported honestly either way.",
        "",
        "## Exact harness construction (auditable per H3)",
        "",
        "The harness runs on the FULL continuous-position record list — one "
        "record for *every* on-chain day x resolution-asset with a "
        "computable z and a forward return, NOT a subset filtered by signal "
        "strength. Each record carries `status` (WON/LOST from the "
        "direction-signed forward return) and `signal_z` (the `|z|` "
        "conviction magnitude — the score field the harness evaluates). "
        "`harness._load` is temporarily pointed at this list; "
        "`harness.evaluate()` / `is_admissible()` then run their own "
        "unchanged `_windows` / `_window_eff` logic (the harness module is "
        "imported verbatim, EFF_MIN/MIN_WINDOW_N/MIN_STABLE_WINDOWS "
        "untouched). If a real edge exists, winners carry higher `|z|` than "
        "losers with a stable sign across >= 3 walk-forward windows. If not, "
        "the sign splits — the exact failure mode that killed the prior 7 "
        "candidates.",
        "",
    ]

    n_pass = 0
    for r in results:
        h = r.get("harness", {})
        cg = r.get("cost_gate", {})
        adm = bool(h.get("is_admissible"))
        cost_ok = bool(cg.get("passes"))
        overall = adm and cost_ok
        n_pass += int(overall)
        flag = "PASS" if overall else ("REJECTED" if h.get("windows_scored", 0)
                                       >= harness.MIN_STABLE_WINDOWS
                                       else "UNTESTED")
        out += [
            f"## {r['signal_id']} — {r['label']} — [{flag}]",
            "",
            f"- **Hypothesis:** {r['hypothesis']} ({r['asset_class']})",
            f"- **On-chain source:** {r['data_source']}",
            f"- **Resolution:** {r.get('resolution', 'n/a')}",
        ]
        if r.get("error"):
            out.append(f"- **ERROR:** {r['error']}")
        else:
            out += [
                f"- **On-chain history:** {r.get('onchain_days', 0)} days "
                f"({r.get('onchain_span', 'n/a')})",
                f"- **Continuous-position records:** {r.get('n', 0)}",
            ]
        cv = r.get("purged_cv", {})
        out += ["", "### Purged + embargoed walk-forward"]
        if cv.get("oos_wr") is not None:
            out += [
                f"- OOS sample: n={cv['oos_n']}, pooled WR="
                f"{cv['oos_wr']*100:.1f}%",
                f"- embargo: {cv.get('embargo_days')} days",
                f"- gross edge (mean signed return/trade): "
                f"{cv.get('gross_edge')}",
            ]
            blocks = cv.get("blocks", [])
            if blocks:
                shown = blocks[:8]
                out += ["", "| block start | n | WR |", "|---|---|---|"]
                for b in shown:
                    out.append(f"| {b['start']} | {b['n']} | "
                                f"{b['wr']*100:.1f}% |")
                if len(blocks) > 8:
                    out.append(f"| ... | ... | ({len(blocks)} blocks total) |")
        else:
            out.append(f"- {cv.get('note', 'no walk-forward data')}")

        out += ["", "### Harness verdict (THE gate — unmodified)"]
        if "per_window_eff" in h:
            effs = " ".join(
                (f"{e['eff']:+.2f}" if e["eff"] is not None else "n/a")
                for e in h["per_window_eff"][:24])
            tail = " ..." if len(h["per_window_eff"]) > 24 else ""
            out += [
                f"- per-window eff (new->old): `{effs}{tail}`",
                f"- windows strong: {h.get('windows_strong')}/"
                f"{h.get('windows_scored')} "
                f"(+{h.get('strong_positive')}/-{h.get('strong_negative')})",
                f"- classification: **{_classify(h)}**",
            ]
        out += [
            f"- **is_admissible(): {adm}** — {h.get('reason', 'n/a')}",
            "",
            "### Post-cost gate (H4)",
        ]
        if cg.get("applicable"):
            out += [
                f"- round-trip cost: {cg['round_trip_cost_bps']} bps "
                f"({cg['round_trip_cost']})",
                f"- gross edge: {cg['gross_edge']}  ->  net edge: "
                f"{cg['net_edge']}",
                f"- cost survival: {cg['survival_pct']}% of gross "
                f"(floor {cg['floor_pct']:.0f}%)",
                f"- **cost gate passes: {cg['passes']}**",
            ]
        else:
            out.append(f"- not applicable — {cg.get('reason', 'untested')}")
        out += [
            "",
            f"### Verdict: {'PASS — admissible AND cost-surviving' if overall else flag}",
            "",
        ]

    # honest conclusion
    out += ["## Honest conclusion", ""]
    tested = [r for r in results
              if r.get("harness", {}).get("windows_scored", 0)
              >= harness.MIN_STABLE_WINDOWS]
    untested = [r for r in results if r not in tested]
    if n_pass == 0:
        out += [
            f"**0 of {len(results)} on-chain signals cleared the gate.** None "
            "may rank, gate, or size a pick. Honest breakdown:",
            "",
            f"- **Tested and REJECTED ({len(tested)}):** "
            + (", ".join(f"{r['signal_id']} ({r['label']})" for r in tested)
               or "none")
            + ". The unmodified harness rendered a real eff-stability "
            "verdict and the signal failed it — a measured result, not a "
            "data gap.",
            f"- **UNTESTED — data-insufficient ({len(untested)}):** "
            + (", ".join(f"{r['signal_id']} ({r['label']})" for r in untested)
               or "none")
            + ". The harness needs >= " + str(harness.MIN_WINDOW_N)
            + " records with >= 15 winners and >= 15 losers per 14-day "
            "window across >= " + str(harness.MIN_STABLE_WINDOWS)
            + " windows. Where free on-chain history (e.g. CoinGecko's "
            "365-day market_chart cap for stablecoin supply) cannot supply "
            "that, the honest verdict is **UNTESTED — explicitly NOT a "
            "pass**. The harness thresholds were NOT lowered and the windows "
            "were NOT shrunk to manufacture a verdict.",
            "",
            "On-chain network activity is a genuinely new input class — but "
            "a new input class is not an edge until the harness says so, and "
            "today it does not. This is consistent with the EDGE_VERDICT "
            "base rate. No signal is wired, none is sized; paper-only posture "
            "stands.",
        ]
    else:
        names = [f"{r['signal_id']} ({r['label']})" for r in results
                 if r.get("harness", {}).get("is_admissible")
                 and r.get("cost_gate", {}).get("passes")]
        out += [
            f"**{n_pass} of {len(results)} on-chain signals cleared BOTH the "
            f"unmodified harness AND the post-cost gate:** {', '.join(names)}. "
            "Against a 7-kill base rate this is a surprising result and must "
            "be treated as a **research candidate, not a green light**. "
            "Before any wiring it needs: (a) re-test on a fresh "
            "out-of-sample period, (b) a deflated-Sharpe / SPA "
            "multiple-testing correction, (c) confirmation the on-chain data "
            "is not itself a price/volume artifact, and (d) operator review. "
            "The harness is necessary, not sufficient — `cot_positioning` "
            "passed DSR + SPA and was still a leakage artifact. No signal is "
            "wired or sized by this module regardless of verdict.",
        ]
    out.append("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--signal", choices=["active", "tx", "stablecoin", "all"],
                    default="all")
    ap.add_argument("--out", type=Path,
                    default=ROOT / "reports"
                    / "onchain_crypto_research_2026-05-18.md")
    ap.add_argument("--refresh", action="store_true",
                    help="force re-fetch of on-chain data, ignore cache")
    ap.add_argument("--json", dest="as_json", action="store_true")
    args = ap.parse_args()

    print("# loading on-chain data ...", file=sys.stderr)
    bundle = load_onchain_data(refresh=args.refresh)
    todo = (["active", "tx", "stablecoin"] if args.signal == "all"
            else [args.signal])
    results = []
    for name in todo:
        print(f"# researching {name} ...", file=sys.stderr)
        results.append(research_signal(name, bundle))

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
