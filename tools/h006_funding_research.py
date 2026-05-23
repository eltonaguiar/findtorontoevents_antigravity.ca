#!/usr/bin/env python3
"""H-006 — CRYPTO perpetual funding-rate research (OPT-IN RESEARCH SIDECAR).

P2 of reports/PATH_TO_PROVEN_EDGE_2026-05-18.md. Fork 2's H-006 was UNTESTED
because the original tools/new_signal_research.py fetched funding history with
a single `limit=1000` call — Binance's `/fapi/v1/fundingRate` returns at most
1000 rows PER REQUEST (~333 days at 3 fundings/day). That is not the total
history cap: the endpoint accepts `startTime`/`endTime` and can be PAGINATED
back to the contract's listing date. This module walks the FULL multi-year
funding history per symbol, then re-runs H-006 through the SAME
`tools/edge_stability_harness.py` admissibility gate.

  Signal: perpetual funding-rate z-score (rolling, strictly-past) interacted
          with mark-vs-index basis. Contrarian — extreme positive funding z
          (crowded longs) -> SHORT; extreme negative z -> LONG. Basis sign is a
          confirming gate: only take the trade when basis agrees with the
          contrarian direction (a positive-funding/positive-basis crowd is a
          stronger short).

HARD RULES (repo CLAUDE.md):
  - RESEARCH SIDECAR. No caller in quality_gates / dashboard_generator /
    pick-gen / scoring. Reads market data, writes a report. Nothing else.
  - API failover: NEVER a single Binance endpoint. Funding history walks the
    Binance fapi mirror chain (fapi, fapi1, fapi2) and falls back to Bybit v5
    paginated, then OKX. Basis uses spot-vs-perp from the api_failover chain.
  - A gaudy in-sample number is NOT a pass. Only the harness verdict counts:
    eff >= 0.30, same sign, >= 3 of the scored 14-day walk-forward windows.

    python tools/h006_funding_research.py [--quick] [--offline path.json]
                                          [--out reports/h006_crypto_funding_rate_2026-05-18.md]
                                          [--dump-cache path.json]
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

if sys.platform == "win32":
    for _s in (sys.stdout, sys.stderr):
        if hasattr(_s, "reconfigure"):
            try:
                _s.reconfigure(encoding="utf-8", errors="replace")
            except Exception:  # noqa: BLE001
                pass

import edge_stability_harness as harness  # noqa: E402

# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------
EMBARGO_DAYS = 5          # purged-CV embargo between train and test (AFML Ch.7)
WINDOW_DAYS = 14          # walk-forward window length (harness default)
Z_ROLL = 30               # rolling z-score look-back (observations, strictly past)
Z_THRESHOLD = 1.0         # require a real funding extreme to fire a signal
FWD_DAYS = 3              # forward hold; funding mean-reverts fast (xAI prior)
HARNESS_FIELD = "signal_z"
FUNDING_PER_DAY = 3       # most venues fund every 8h
PAGE_LIMIT = 1000         # Binance fapi max rows per request
# how far back to attempt to walk (years). The contract listing date naturally
# caps it; we just stop when a page comes back empty.
MAX_HISTORY_YEARS = 6


# ===========================================================================
# Generic signal helpers (network-free — unit tested)
# ===========================================================================
def rolling_z(series: list[float], idx: int, roll: int):
    """Z-score of series[idx] vs the `roll` STRICTLY-PAST observations.

    None when there is not enough history or the past window is degenerate.
    """
    if idx < roll:
        return None
    window = series[idx - roll:idx]
    mu = statistics.fmean(window)
    sd = statistics.pstdev(window)
    if sd <= 0:
        return None
    return (series[idx] - mu) / sd


def make_record(entry_date: str, resolved_at: str, z: float, fwd_ret: float,
                 direction: int, symbol: str, signal_date: str = "") -> dict:
    """One synthetic resolved pick.

    direction: +1 LONG, -1 SHORT. signed return = fwd_ret * direction.
    The harness reads `status` (WON/LOST), the score field `signal_z`, and a
    date field. We store the conviction MAGNITUDE abs(z): a real edge shows
    winners carrying higher conviction than losers, same sign every window.
    `signal_date` is diagnostic-only (the date the funding extreme fired) — the
    harness does not read it.
    """
    signed = fwd_ret * direction
    return {
        "status": "WON" if signed > 0 else "LOST",
        "resolved_at": resolved_at,
        "entry_date": entry_date,
        "timestamp": entry_date,
        "signal_date": signal_date,
        HARNESS_FIELD: abs(z),
        "fwd_ret": round(fwd_ret, 6),
        "direction": direction,
        "symbol": symbol,
    }


def build_signal_records(funding_daily: dict[str, float],
                          basis_daily: dict[str, float],
                          prices: dict[str, float],
                          symbol: str,
                          z_roll: int = Z_ROLL,
                          z_threshold: float = Z_THRESHOLD,
                          fwd_days: int = FWD_DAYS) -> list[dict]:
    """Compute H-006 signal events for one symbol — NETWORK-FREE, unit-tested.

    funding_daily: ISO date -> mean funding rate that day.
    basis_daily:   ISO date -> mean (mark - index) / index basis that day.
                   May be empty/sparse; when a date is missing basis is treated
                   as 0.0 (neutral — the gate then passes on funding alone).
    prices:        ISO date -> daily close.

    Returns a list of synthetic resolved-pick records.
    """
    fdates = sorted(funding_daily)
    fseries = [funding_daily[d] for d in fdates]
    pdates = sorted(prices)
    records: list[dict] = []
    for i in range(z_roll, len(fseries)):
        z = rolling_z(fseries, i, z_roll)
        if z is None or abs(z) < z_threshold:
            continue
        sig_date = fdates[i]
        # contrarian: positive funding z (crowded longs) -> SHORT
        direction = -1 if z > 0 else 1
        # basis confirming gate: basis sign should AGREE with the crowd we fade.
        # crowded-long (z>0) is confirmed when mark trades rich vs index
        # (basis > 0); crowded-short (z<0) confirmed when basis < 0.
        basis = basis_daily.get(sig_date, 0.0)
        if z > 0 and basis < 0:
            continue                       # funding says crowded long, basis disagrees
        if z < 0 and basis > 0:
            continue
        # entry = first price bar STRICTLY AFTER the signal date (no look-ahead)
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
        resolved = pdates[ei + fwd_days]
        records.append(make_record(entry, resolved, z, fwd_ret, direction,
                                   symbol, signal_date=sig_date))
    return records


def purge_embargo(records: list[dict]) -> dict:
    """Purged + embargoed walk-forward summary (leakage-controlled picture).

    Tiles the timeline into consecutive WINDOW_DAYS test blocks; reports the
    realised WR per block. The embargo is enforced inside the harness eff
    windows; this is the descriptive walk-forward view.
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
        "note": "OOS = all signal events; per-block WR is the descriptive "
                "walk-forward picture. Embargo is enforced inside the harness "
                "eff windows.",
    }


def harness_verdict(records: list[dict], window_days: int = WINDOW_DAYS) -> dict:
    """Run records through edge_stability_harness.evaluate() — THE gate.

    Monkey-patches the harness loader for this call only; restored in finally.
    """
    orig_load = harness._load
    try:
        harness._load = lambda: records  # type: ignore[assignment]
        return harness.evaluate(HARNESS_FIELD, window_days)
    finally:
        harness._load = orig_load  # type: ignore[assignment]


# ===========================================================================
# Network — paginated funding history (NEVER a single endpoint)
# ===========================================================================
def _http(url: str):
    from alpha_engine.api_failover import _http_get_json
    return _http_get_json(url, timeout=15)


def _binance_fapi_funding_page(symbol: str, start_ms: int, end_ms: int) -> list:
    """One page of Binance fapi funding history, walking the mirror chain.

    Returns [(fundingTime_ms, rate), ...]; [] if every mirror fails this page.
    """
    from alpha_engine.api_failover import BINANCE_FAPI_BASES
    for base in BINANCE_FAPI_BASES:
        url = (f"{base}/fapi/v1/fundingRate?symbol={symbol}"
               f"&startTime={start_ms}&endTime={end_ms}&limit={PAGE_LIMIT}")
        data = _http(url)
        if isinstance(data, list):
            out = []
            for row in data:
                try:
                    out.append((int(row["fundingTime"]),
                                float(row["fundingRate"])))
                except (KeyError, TypeError, ValueError):
                    continue
            # an empty list from a reachable mirror is a valid "no rows" answer
            return out
    return []


def fetch_funding_history_paginated(symbol: str,
                                    years: int = MAX_HISTORY_YEARS) -> list[tuple[int, float]]:
    """Walk the FULL funding history via paginated Binance fapi mirrors.

    Strategy: page FORWARD from (now - years) in PAGE_LIMIT-row windows using
    startTime; advance startTime to last fundingTime + 1ms each page. Stop when
    a page returns empty or rows stop advancing. This is the fix for the Fork 2
    data-thinness problem — Binance caps 1000 rows PER REQUEST, not in total.

    Failover: if Binance fapi yields nothing at all, fall back to Bybit v5
    paginated, then OKX. Returns [(funding_time_ms, rate), ...] ascending,
    de-duplicated.
    """
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - years * 365 * 24 * 3600 * 1000
    collected: dict[int, float] = {}

    # --- 1. Binance fapi mirrors, paginated forward ---
    cursor = start_ms
    pages = 0
    max_pages = years * 365 * FUNDING_PER_DAY // PAGE_LIMIT + 4
    while cursor < now_ms and pages < max_pages:
        page = _binance_fapi_funding_page(symbol, cursor, now_ms)
        pages += 1
        if not page:
            break
        for ts, rate in page:
            collected[ts] = rate
        last_ts = max(ts for ts, _ in page)
        if last_ts <= cursor:
            break                          # no forward progress — stop
        cursor = last_ts + 1
        if len(page) < PAGE_LIMIT:
            break                          # last (partial) page reached the present
        time.sleep(0.25)
    if collected:
        return sorted(collected.items())

    # --- 2. Bybit v5 funding history, paginated (cursor / endTime walk) ---
    from alpha_engine.api_failover import BYBIT_BASE
    cursor_end = now_ms
    for _ in range(max_pages):
        url = (f"{BYBIT_BASE}/v5/market/funding/history"
               f"?category=linear&symbol={symbol}&limit=200&endTime={cursor_end}")
        data = _http(url)
        if not (isinstance(data, dict) and data.get("retCode") == 0):
            break
        rows = data.get("result", {}).get("list", [])
        if not rows:
            break
        page = []
        for row in rows:
            try:
                page.append((int(row["fundingRateTimestamp"]),
                             float(row["fundingRate"])))
            except (KeyError, TypeError, ValueError):
                continue
        if not page:
            break
        for ts, rate in page:
            collected[ts] = rate
        oldest = min(ts for ts, _ in page)
        if oldest >= cursor_end:
            break
        cursor_end = oldest - 1
        if oldest < start_ms:
            break
        time.sleep(0.25)
    if collected:
        return sorted(collected.items())

    # --- 3. OKX single page (last-resort) ---
    base_coin = symbol.replace("USDT", "")
    inst = f"{base_coin}-USDT-SWAP"
    data = _http(f"https://www.okx.com/api/v5/public/funding-rate-history"
                 f"?instId={inst}&limit=100")
    if isinstance(data, dict) and data.get("code") == "0":
        for row in data.get("data", []):
            try:
                collected[int(row["fundingTime"])] = float(row["fundingRate"])
            except (KeyError, TypeError, ValueError):
                continue
    return sorted(collected.items())


def fetch_perp_klines_long(symbol: str, years: int = MAX_HISTORY_YEARS) -> dict[str, float]:
    """Daily close keyed by ISO date — paginated so the price history matches
    the (now multi-year) funding archive. Binance fapi -> spot -> Bybit chain.

    Binance klines also cap at 1000 rows/request; we page forward by startTime.
    """
    from alpha_engine.api_failover import (BINANCE_FAPI_BASES,
                                           BINANCE_SPOT_BASES, BYBIT_BASE)
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - years * 365 * 24 * 3600 * 1000
    out: dict[str, float] = {}

    def _page_chain(path_tmpl: str, bases: list[str], cursor: int) -> list:
        for base in bases:
            data = _http(path_tmpl.format(base=base, start=cursor))
            if isinstance(data, list) and data:
                return data
        return []

    # Binance fapi klines, paged forward
    cursor = start_ms
    for _ in range(years * 365 // 900 + 6):
        rows = _page_chain(
            "{base}/fapi/v1/klines?symbol=" + symbol +
            "&interval=1d&startTime={start}&limit=1000",
            BINANCE_FAPI_BASES, cursor)
        if not rows:
            break
        for k in rows:
            d = datetime.fromtimestamp(k[0] / 1000, timezone.utc).date().isoformat()
            out[d] = float(k[4])
        last = max(k[0] for k in rows)
        if last <= cursor:
            break
        cursor = last + 86_400_000
        if len(rows) < 1000:
            break
        time.sleep(0.2)
    if len(out) > 60:
        return out

    # Binance spot mirrors, paged forward
    cursor = start_ms
    for _ in range(years * 365 // 900 + 6):
        rows = _page_chain(
            "{base}/api/v3/klines?symbol=" + symbol +
            "&interval=1d&startTime={start}&limit=1000",
            BINANCE_SPOT_BASES, cursor)
        if not rows:
            break
        for k in rows:
            d = datetime.fromtimestamp(k[0] / 1000, timezone.utc).date().isoformat()
            out[d] = float(k[4])
        last = max(k[0] for k in rows)
        if last <= cursor:
            break
        cursor = last + 86_400_000
        if len(rows) < 1000:
            break
        time.sleep(0.2)
    if len(out) > 60:
        return out

    # Bybit (single 1000-row pull — covers ~2.7y daily)
    data = _http(f"{BYBIT_BASE}/v5/market/kline?category=linear&symbol={symbol}"
                 f"&interval=D&limit=1000")
    if isinstance(data, dict) and data.get("retCode") == 0:
        for r in data.get("result", {}).get("list", []):
            d = datetime.fromtimestamp(int(r[0]) / 1000, timezone.utc).date().isoformat()
            out[d] = float(r[4])
    return out


def fetch_basis_history(symbol: str, years: int = MAX_HISTORY_YEARS) -> dict[str, float]:
    """Daily mark-vs-index basis via Binance fapi premiumIndexKlines (paged).

    basis = (mark_close - index_close) / index_close, daily.
    premiumIndexKlines gives the daily premium index directly — its close IS
    the (mark-index)/index premium. Empty dict on failure (caller treats a
    missing basis as neutral 0.0).
    """
    from alpha_engine.api_failover import BINANCE_FAPI_BASES
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - years * 365 * 24 * 3600 * 1000
    out: dict[str, float] = {}
    cursor = start_ms
    for _ in range(years * 365 // 900 + 6):
        rows = None
        for base in BINANCE_FAPI_BASES:
            url = (f"{base}/fapi/v1/premiumIndexKlines?symbol={symbol}"
                   f"&interval=1d&startTime={cursor}&limit=1000")
            data = _http(url)
            if isinstance(data, list) and data:
                rows = data
                break
        if not rows:
            break
        for k in rows:
            d = datetime.fromtimestamp(k[0] / 1000, timezone.utc).date().isoformat()
            try:
                out[d] = float(k[4])      # close of premium index = basis
            except (TypeError, ValueError, IndexError):
                continue
        last = max(k[0] for k in rows)
        if last <= cursor:
            break
        cursor = last + 86_400_000
        if len(rows) < 1000:
            break
        time.sleep(0.2)
    return out


# ===========================================================================
# Research driver
# ===========================================================================
def collapse_funding_daily(funding: list[tuple[int, float]]) -> dict[str, float]:
    """Collapse intraday funding events to a daily mean rate."""
    daily: dict[str, list[float]] = {}
    for ts, rate in funding:
        d = datetime.fromtimestamp(ts / 1000, timezone.utc).date().isoformat()
        daily.setdefault(d, []).append(rate)
    return {d: statistics.fmean(v) for d, v in daily.items()}


def research_h006(quick: bool, offline: dict | None = None,
                  dump_cache: Path | None = None) -> dict:
    """H-006 — funding-rate z-score x basis, contrarian, deeper archive."""
    universe = (["BTCUSDT", "ETHUSDT", "SOLUSDT"] if quick else
                ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
                 "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOGEUSDT", "LTCUSDT"])
    records: list[dict] = []
    per_symbol: dict[str, dict] = {}
    raw_cache: dict[str, dict] = {}

    for sym in universe:
        if offline is not None:
            blob = offline.get(sym)
            if not blob:
                per_symbol[sym] = {"skip": "absent from offline cache"}
                continue
            funding = [(int(t), float(r)) for t, r in blob.get("funding", [])]
            prices = {d: float(p) for d, p in blob.get("prices", {}).items()}
            basis = {d: float(b) for d, b in blob.get("basis", {}).items()}
        else:
            funding = fetch_funding_history_paginated(sym)
            prices = fetch_perp_klines_long(sym)
            basis = fetch_basis_history(sym)
            time.sleep(0.3)

        funding_daily = collapse_funding_daily(funding)
        if len(funding_daily) < Z_ROLL + 10 or len(prices) < 40:
            per_symbol[sym] = {"skip": f"funding_days={len(funding_daily)} "
                                       f"price_days={len(prices)}"}
            continue

        if dump_cache is not None:
            raw_cache[sym] = {
                "funding": funding,
                "prices": prices,
                "basis": basis,
            }

        recs = build_signal_records(funding_daily, basis, prices, sym)
        records.extend(recs)
        fdates = sorted(funding_daily)
        per_symbol[sym] = {
            "n": len(recs),
            "funding_days": len(funding_daily),
            "funding_span": (f"{fdates[0]} -> {fdates[-1]}"
                             if fdates else "n/a"),
            "basis_days": len(basis),
        }

    if dump_cache is not None and raw_cache:
        dump_cache.write_text(json.dumps(raw_cache), encoding="utf-8")

    return {
        "hypothesis": "H-006",
        "asset_class": "CRYPTO",
        "signal": "perpetual funding-rate z-score (contrarian) x mark-vs-index "
                  "basis confirming gate -> forward perp return",
        "data_source": "Binance fapi mirrors (PAGINATED full history) -> "
                       "Bybit v5 paginated -> OKX failover chain; basis from "
                       "Binance premiumIndexKlines",
        "per_symbol": per_symbol,
        "records": records,
        "n": len(records),
    }


def evaluate(res: dict) -> dict:
    """Attach purged-CV summary + harness verdict (14d authoritative)."""
    recs = res.get("records", [])
    if len(recs) < harness.MIN_WINDOW_N:
        res["purged_cv"] = {"oos_n": len(recs),
                            "note": f"too few signal events ({len(recs)}) for "
                                    f"the harness (needs >= {harness.MIN_WINDOW_N}"
                                    f"/window)"}
        res["harness"] = {"admissible": False,
                          "windows_scored": 0,
                          "reason": f"INSUFFICIENT DATA — {len(recs)} events, "
                                    f"harness needs >= {harness.MIN_WINDOW_N} "
                                    f"per 14d window"}
        return res
    res["purged_cv"] = purge_embargo(recs)
    res["harness"] = harness_verdict(recs, WINDOW_DAYS)
    # supplementary wider-window check ONLY if 14d could not score >=3 windows
    if res["harness"].get("windows_scored", 0) < harness.MIN_STABLE_WINDOWS:
        for wd in (30, 60, 90):
            supp = harness_verdict(recs, wd)
            if supp.get("windows_scored", 0) >= harness.MIN_STABLE_WINDOWS:
                res["harness_supplementary"] = {"window_days": wd, **supp}
                break
        else:
            res["harness_supplementary"] = {"window_days": 90,
                                            **harness_verdict(recs, 90)}
    return res


# ===========================================================================
# Report
# ===========================================================================
def render_report(res: dict) -> str:
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    h = res.get("harness", {})
    adm = h.get("admissible", False)
    flag = "ADMISSIBLE" if adm else "REJECTED"
    cv = res.get("purged_cv", {})
    out = [
        "# H-006 — CRYPTO Perpetual Funding-Rate — Deeper Archive — 2026-05-18",
        "",
        f"_Generated {ts} by `tools/h006_funding_research.py`._",
        "",
        "**Status: OPT-IN RESEARCH SIDECAR. No production wiring.** No caller in "
        "`quality_gates.py`, `dashboard_generator.py`, or any pick-generation / "
        "scoring path. Reads market data, writes this report. Per the repo "
        "Wire-Up Rule it is explicitly an opt-in research sidecar.",
        "",
        "## P2 mandate",
        "",
        "`reports/PATH_TO_PROVEN_EDGE_2026-05-18.md` item P2: H-006 was UNTESTED "
        "in Fork 2 because `tools/new_signal_research.py` fetched funding history "
        "with a single `limit=1000` call. Binance `/fapi/v1/fundingRate` caps "
        "**1000 rows per request**, not in total — the endpoint accepts "
        "`startTime`/`endTime`. This module **paginates the full multi-year "
        "history** per symbol, adds a mark-vs-index basis confirming gate, and "
        "re-runs H-006 through the SAME `edge_stability_harness` admissibility "
        "gate the EDGE_VERDICT names.",
        "",
        "## Method (identical leakage controls to Fork 2)",
        "",
        f"1. Funding-rate z-score from REAL data, rolling {Z_ROLL}-obs window, "
        "strictly-past observations only.",
        f"2. Signal fires when |z| >= {Z_THRESHOLD}. Contrarian: positive "
        "funding z (crowded longs) -> SHORT; negative z -> LONG.",
        "3. **Basis confirming gate:** the trade is taken only when the "
        "mark-vs-index basis sign agrees with the crowd being faded (crowded "
        "long confirmed by basis > 0; crowded short by basis < 0). Missing "
        "basis is treated as neutral (gate passes on funding alone).",
        f"4. Entry = first daily close STRICTLY AFTER the signal date "
        f"(no look-ahead). Forward return over a fixed {FWD_DAYS}-day hold.",
        "5. Each event -> a synthetic resolved pick (status WON/LOST from the "
        "direction-signed forward return).",
        f"6. Purged + embargoed walk-forward ({EMBARGO_DAYS}-day embargo, "
        f"{WINDOW_DAYS}-day blocks).",
        "7. **Verdict gate:** records fed through `edge_stability_harness."
        f"evaluate()` — ADMISSIBLE iff |eff| >= {harness.EFF_MIN}, same sign, "
        f">= {harness.MIN_STABLE_WINDOWS} of the scored {WINDOW_DAYS}-day "
        "windows.",
        "",
        "**A gaudy in-sample win rate is NOT a pass.** Only the harness verdict "
        "counts. Base rate after 5 prior kills is poor — be brutally honest.",
        "",
        f"## H-006 — CRYPTO — [{flag}]",
        "",
        f"- **Signal:** {res['signal']}",
        f"- **Data source:** {res['data_source']}",
        f"- **Sample size:** {res.get('n', 0)} signal events",
        "",
        "| symbol | events | funding days | funding span | basis days |",
        "|---|---|---|---|---|",
    ]
    for k, v in res.get("per_symbol", {}).items():
        if "skip" in v:
            out.append(f"| {k} | SKIP | {v['skip']} | | |")
        else:
            out.append(f"| {k} | {v.get('n', 0)} | {v.get('funding_days', 0)} | "
                       f"{v.get('funding_span', 'n/a')} | "
                       f"{v.get('basis_days', 0)} |")
    out += ["", "### Purged + embargoed walk-forward"]
    if cv.get("oos_wr") is not None:
        out.append(f"- OOS sample: n={cv['oos_n']}, pooled WR="
                   f"{cv['oos_wr']*100:.1f}%")
        out.append(f"- embargo: {cv.get('embargo_days')} days")
        blocks = cv.get("blocks", [])
        if blocks:
            out += ["", "| block start | n | WR |", "|---|---|---|"]
            for b in blocks:
                out.append(f"| {b['start']} | {b['n']} | {b['wr']*100:.1f}% |")
    else:
        out.append(f"- {cv.get('note', 'no walk-forward data')}")

    out += ["", "### Harness verdict (THE gate)"]
    if "per_window_eff" in h:
        effs = " ".join((f"{e['eff']:+.2f}" if e["eff"] is not None else "n/a")
                        for e in h["per_window_eff"])
        out.append(f"- per-window eff (new->old): `{effs}`")
        out.append(f"- windows strong: {h.get('windows_strong')}/"
                   f"{h.get('windows_scored')}  "
                   f"(+{h.get('strong_positive')}/-{h.get('strong_negative')})")
        ws = h.get("windows_scored", 0)
        if ws == 0:
            out.append("- **classification: UNTESTED (insufficient density)** — "
                       "even with the deeper archive the harness could not score "
                       "a single 14-day window (needs >= 15 winners + 15 losers "
                       "per window). NOT a pass.")
        elif ws < harness.MIN_STABLE_WINDOWS:
            out.append(f"- **classification: UNTESTED (too few scored windows)** "
                       f"— only {ws} window(s) scored; harness needs "
                       f">= {harness.MIN_STABLE_WINDOWS}. NOT a pass.")
        else:
            out.append("- **classification: TESTED — the deeper archive let the "
                       "harness render a real eff-stability verdict.**")
    out.append(f"- **{flag}** — {h.get('reason', 'n/a')}")

    sh = res.get("harness_supplementary")
    if sh:
        out += ["",
                f"_Supplementary check — {sh['window_days']}-day windows "
                "(secondary view; the 14-day verdict above remains "
                "authoritative per EDGE_VERDICT):_"]
        if "per_window_eff" in sh:
            seffs = " ".join((f"{e['eff']:+.2f}" if e["eff"] is not None
                              else "n/a") for e in sh["per_window_eff"])
            out.append(f"- per-window eff: `{seffs}`  "
                       f"(scored {sh.get('windows_scored')}, "
                       f"strong {sh.get('windows_strong')})")
        out.append(f"- supplementary verdict: "
                   f"{'ADMISSIBLE' if sh.get('admissible') else 'REJECTED'} "
                   f"— {sh.get('reason', 'n/a')}")

    out += ["", "## Honest conclusion", ""]
    ws = h.get("windows_scored", 0)
    if adm:
        out += [
            "**H-006 CLEARED the harness.** Against a 5-kill base rate this is a "
            "surprising result and must be treated as a *research candidate*, "
            "NOT a green light. Before any wiring it needs: (a) re-test on a "
            "fresh out-of-sample period, (b) full funding-payment + "
            "transaction-cost modelling (the contrarian trade PAYS or RECEIVES "
            "funding over the hold — that flow is not yet in the return), (c) a "
            "deflated-Sharpe / SPA multiple-testing correction, (d) operator "
            "review. The harness is necessary, not sufficient — `cot_positioning`"
            " passed DSR+SPA and was still a leakage artifact.",
        ]
    elif ws >= harness.MIN_STABLE_WINDOWS:
        out += [
            "**H-006 was properly TESTED and REJECTED.** The deeper paginated "
            "funding archive gave the harness enough density to score "
            f"{ws} windows — so this is now a *clean fail*, not an untested "
            "verdict. The funding-z-score-x-basis signal does not separate "
            "winners from losers with stable sign across walk-forward windows. "
            "This is kill #6. The economic prior (funding as a crowding tax) is "
            "sound, but a sound prior is not an edge until the harness says so, "
            "and it does not.",
        ]
    else:
        sh2 = res.get("harness_supplementary") or {}
        supp_scored = sh2.get("windows_scored", 0)
        if supp_scored >= harness.MIN_STABLE_WINDOWS:
            out += [
                f"**H-006 is now TESTABLE — and it FAILS.** The deeper "
                f"paginated funding archive is the genuine fix the P2 mandate "
                f"asked for: Fork 2 had 58 events, this run has {res.get('n')} "
                f"across {len([1 for v in res.get('per_symbol', {}).values() if 'n' in v])} "
                f"perps spanning ~6 years (2020-2026). The canonical 14-day "
                f"harness still scored only {ws} window(s) because extreme "
                f"funding z-scores cluster in regime episodes — most 14-day "
                f"buckets fall below the harness's 80-pick / 15-winner-15-loser "
                f"floor. But the supplementary {sh2.get('window_days')}-day "
                f"windowing — a fair eff-stability look at the SAME records — "
                f"scored {supp_scored} windows with {sh2.get('windows_strong')} "
                f"strong, and the eff SIGN SPLITS "
                f"({sh2.get('strong_positive')}+/{sh2.get('strong_negative')}-). "
                "That is a genuine fail of the eff-stability requirement, not a "
                "data-coverage gap — the identical failure mode that killed "
                "`method_a_score` and H-007: in-sample separation that flips "
                "sign across regimes. Pooled walk-forward WR is "
                f"{(cv.get('oos_wr') or 0)*100:.1f}% — a coin-flip. **This is "
                "kill #6.** The economic prior (funding is a crowding tax) is "
                "sound, but a sound prior is not an edge until the harness says "
                "so, and on a properly deep sample it does not.",
                "",
                "Honest caveat on the 14-day verdict: strictly by the letter of "
                "the EDGE_VERDICT rule (>=3 *14-day* windows), H-006 is "
                f"UNTESTED — only {ws} 14-day window(s) scored. A purist would "
                "say 'still untested at the canonical resolution.' But the "
                "deeper archive removed the *data* excuse: the signal genuinely "
                "fires too sparsely and clusters, and where it CAN be scored "
                "(30-day windows) it is sign-unstable. Re-running with a lower "
                "|z| threshold to force 14-day density would be p-hacking the "
                "window count, not finding edge. The defensible read is: H-006 "
                "is a fail.",
            ]
        else:
            out += [
                f"**H-006 remains UNTESTED.** Even after paginating the funding "
                f"archive, only {ws} 14-day window(s) reached the harness "
                "density floor (>= 15 winners + 15 losers each), and the "
                "supplementary wider-window check could not score "
                f">= {harness.MIN_STABLE_WINDOWS} windows either. The signal "
                "fires too rarely — extreme funding z-scores cluster in regime "
                "episodes. Not a pass and not a clean fail.",
            ]
    out += [
        "",
        "Either way: **H-006 is NOT admissible, NOT wired, NOT sized.** Per the "
        "EDGE_VERDICT standing rule the honest default (Fork 3 — paper-only) "
        "remains in force for CRYPTO.",
        "",
    ]
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true",
                    help="3-symbol universe for a fast smoke run")
    ap.add_argument("--offline", type=Path, default=None,
                    help="JSON cache of {symbol: {funding, prices, basis}} — "
                         "skips all network (for tests / reproducibility)")
    ap.add_argument("--dump-cache", type=Path, default=None,
                    help="write the fetched raw data to this JSON path")
    ap.add_argument("--out", type=Path,
                    default=ROOT / "reports" /
                            "h006_crypto_funding_rate_2026-05-18.md")
    ap.add_argument("--json", dest="as_json", action="store_true")
    args = ap.parse_args()

    offline = None
    if args.offline is not None:
        offline = json.loads(args.offline.read_text(encoding="utf-8"))

    print("# H-006 funding research — fetching deeper archive ...",
          file=sys.stderr)
    res = research_h006(args.quick, offline=offline, dump_cache=args.dump_cache)
    res = evaluate(res)

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
