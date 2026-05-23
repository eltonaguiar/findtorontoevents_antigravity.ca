#!/usr/bin/env python3
"""C-3 / H-017 — CRYPTO funding-settlement liquidation-cascade research.

OPT-IN RESEARCH SIDECAR. No caller in any pick-generation / scoring path.
Pre-registered in reports/hypothesis_registry.json::fork2_new_signals (H-017)
BEFORE this backtest logic was written, per M-107. Free-data build approved by
operator 2026-05-18.

HYPOTHESIS (H-017)
------------------
Perpetual funding settles every 8h at fixed UTC clock times (00:00 / 08:00 /
16:00). Positions on the wrong side of funding get squeezed; thin order books
around the settlement minute produce a brief MECHANICAL price dislocation that
mean-reverts. The signal is FORCED FLOW at a known clock time -- NOT a
funding-rate directional bet. FADE the displacement.

SIGNAL
------
For ~10 liquid Binance USDT-M perps, at each 8h funding settlement T:
  * displacement = (price at T) / (prior 1h VWAP) - 1
  * recent realized vol = stdev of 1-min log returns over the prior 60 min
  * funding magnitude rolling top-quartile gate (per-symbol, strictly-past)
  A pick FIRES when |displacement| > 1.5 * realized_vol AND the settlement's
  |funding| is in its per-symbol rolling top quartile.
  Direction = FADE: entry opposite the displacement sign.
  Entry  = close of the T+1min bar.
  Exit   = whichever first of: VWAP reversion (price crosses the prior-1h VWAP),
           30-min time stop, +/-20bps hard stop.
  Forward return is signed by the fade direction; WON if signed return > 0.

HARD RULES (repo CLAUDE.md / M-107)
-----------------------------------
  * RESEARCH SIDECAR. No production wiring.
  * API failover: NEVER a single Binance endpoint -- walk the fapi mirror
    chain (fapi, fapi1, fapi2) per the project's API Failover Rule.
  * tools/edge_stability_harness.py imported UNMODIFIED. EFF_MIN /
    MIN_WINDOW_N / MIN_STABLE_WINDOWS are NOT touched.
  * The harness is fed the FULL signal-generated record series -- every
    settlement that fired a pick, not a cherry-picked subset.
  * Honest verdict only: <5 scored 14-day windows => UNTESTED (data-gap),
    explicitly NOT a pass. Sign split => REJECTED. A gaudy WR is not a pass.
  * Post-cost gate: 30bps crypto round-trip; net edge must retain >=60% of
    gross or the verdict is REJECTED on cost grounds.

    python tools/c3_funding_settlement_research.py [--quick] [--months N]
        [--refresh-cache] [--cache PATH] [--out PATH]
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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
# Tunables (signal definition -- fixed BEFORE the run, per the H-017 entry)
# ---------------------------------------------------------------------------
UNIVERSE = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
            "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOGEUSDT", "LTCUSDT"]
QUICK_UNIVERSE = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

DEFAULT_MONTHS = 7            # aim 6+ months so the harness gets >=5 windows
VWAP_LOOKBACK_MIN = 60        # prior 1h VWAP anchor
VOL_LOOKBACK_MIN = 60         # realized-vol window (prior 60 min, 1-min rets)
DISPLACEMENT_MULT = 1.5       # |displacement| > 1.5 * realized vol
FUNDING_QUANTILE = 0.75       # top-quartile funding-magnitude gate
FUNDING_ROLL = 30             # per-symbol rolling window for the quartile (obs)
ENTRY_OFFSET_MIN = 1          # entry at settlement + 1 min close
TIME_STOP_MIN = 30            # 30-min time stop
HARD_STOP_BPS = 20.0          # +/-20bps hard stop
FETCH_PAD_MIN = 95            # minutes of 1-min klines fetched around each T
ROUND_TRIP_COST_BPS = 30.0    # crypto round-trip cost (post-cost gate)
COST_SURVIVAL_MIN = 0.60      # net edge must retain >=60% of gross
WINDOW_DAYS = 14              # canonical harness window
HARNESS_FIELD = "signal_z"    # conviction magnitude the harness scores

PAGE_LIMIT = 1000             # Binance klines / fundingRate cap per request
SETTLEMENT_HOURS = (0, 8, 16) # 8h UTC funding clock


# ===========================================================================
# Network helpers -- API FAILOVER (never a single endpoint)
# ===========================================================================
def _http(url: str):
    from alpha_engine.api_failover import _http_get_json
    return _http_get_json(url, timeout=20)


def fetch_funding_history(symbol: str, start_ms: int,
                          end_ms: int) -> list[tuple[int, float]]:
    """Paginated /fapi/v1/fundingRate over [start_ms, end_ms].

    Binance caps 1000 rows per request -- page forward via startTime. Walks the
    fapi mirror chain; Bybit v5 fallback if every mirror fails entirely.
    Returns [(fundingTime_ms, rate), ...] ascending, de-duplicated.
    """
    from alpha_engine.api_failover import BINANCE_FAPI_BASES, BYBIT_BASE
    out: dict[int, float] = {}
    cursor = start_ms
    pages = 0
    max_pages = (end_ms - start_ms) // (PAGE_LIMIT * 8 * 3600 * 1000) + 6
    while cursor < end_ms and pages < max_pages:
        page = None
        for base in BINANCE_FAPI_BASES:
            url = (f"{base}/fapi/v1/fundingRate?symbol={symbol}"
                   f"&startTime={cursor}&endTime={end_ms}&limit={PAGE_LIMIT}")
            data = _http(url)
            if isinstance(data, list):
                page = data
                break
        pages += 1
        if not page:
            break
        for row in page:
            try:
                out[int(row["fundingTime"])] = float(row["fundingRate"])
            except (KeyError, TypeError, ValueError):
                continue
        last = max(int(r["fundingTime"]) for r in page)
        if last <= cursor:
            break
        cursor = last + 1
        if len(page) < PAGE_LIMIT:
            break
        time.sleep(0.2)
    if out:
        return sorted(out.items())

    # --- Bybit v5 fallback (paginated backward by endTime) ---
    cursor_end = end_ms
    for _ in range(max_pages + 4):
        url = (f"{BYBIT_BASE}/v5/market/funding/history"
               f"?category=linear&symbol={symbol}&limit=200&endTime={cursor_end}")
        data = _http(url)
        if not (isinstance(data, dict) and data.get("retCode") == 0):
            break
        rows = data.get("result", {}).get("list", [])
        if not rows:
            break
        for row in rows:
            try:
                out[int(row["fundingRateTimestamp"])] = float(row["fundingRate"])
            except (KeyError, TypeError, ValueError):
                continue
        oldest = min(int(r["fundingRateTimestamp"]) for r in rows)
        if oldest <= start_ms or oldest >= cursor_end:
            break
        cursor_end = oldest - 1
        time.sleep(0.2)
    return sorted(out.items())


def fetch_1m_klines(symbol: str, start_ms: int,
                    end_ms: int) -> list[tuple[int, float, float]]:
    """Paginated 1-min klines over [start_ms, end_ms].

    /fapi/v1/klines caps 1000 rows per request -- page forward via startTime.
    Walks the fapi mirror chain; Bybit v5 linear fallback.
    Returns [(open_time_ms, close_px, base_volume), ...] ascending, de-duped.
    """
    from alpha_engine.api_failover import BINANCE_FAPI_BASES, BYBIT_BASE
    out: dict[int, tuple[float, float]] = {}
    cursor = start_ms
    pages = 0
    max_pages = (end_ms - start_ms) // (PAGE_LIMIT * 60_000) + 4
    while cursor < end_ms and pages < max_pages:
        rows = None
        for base in BINANCE_FAPI_BASES:
            url = (f"{base}/fapi/v1/klines?symbol={symbol}&interval=1m"
                   f"&startTime={cursor}&endTime={end_ms}&limit={PAGE_LIMIT}")
            data = _http(url)
            if isinstance(data, list):
                rows = data
                break
        pages += 1
        if not rows:
            break
        for k in rows:
            try:
                out[int(k[0])] = (float(k[4]), float(k[5]))
            except (TypeError, ValueError, IndexError):
                continue
        last = max(int(k[0]) for k in rows)
        if last <= cursor:
            break
        cursor = last + 60_000
        if len(rows) < PAGE_LIMIT:
            break
        time.sleep(0.12)
    if out:
        return sorted((t, px, vol) for t, (px, vol) in out.items())

    # --- Bybit fallback (paginated forward) ---
    cursor = start_ms
    for _ in range(max_pages + 4):
        url = (f"{BYBIT_BASE}/v5/market/kline?category=linear&symbol={symbol}"
               f"&interval=1&start={cursor}&end={end_ms}&limit=1000")
        data = _http(url)
        if not (isinstance(data, dict) and data.get("retCode") == 0):
            break
        rows = data.get("result", {}).get("list", [])
        if not rows:
            break
        for r in rows:
            try:
                out[int(r[0])] = (float(r[4]), float(r[5]))
            except (TypeError, ValueError, IndexError):
                continue
        last = max(int(r[0]) for r in rows)
        if last <= cursor:
            break
        cursor = last + 60_000
        time.sleep(0.15)
    return sorted((t, px, vol) for t, (px, vol) in out.items())


# ===========================================================================
# Signal logic -- NETWORK-FREE (deterministic, testable)
# ===========================================================================
def settlement_timestamps(start_ms: int, end_ms: int) -> list[int]:
    """Every 00:00 / 08:00 / 16:00 UTC settlement ms in [start, end]."""
    out: list[int] = []
    d = datetime.fromtimestamp(start_ms / 1000, timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0)
    while True:
        for h in SETTLEMENT_HOURS:
            t = int((d + timedelta(hours=h)).timestamp() * 1000)
            if start_ms <= t <= end_ms:
                out.append(t)
        d += timedelta(days=1)
        if int(d.timestamp() * 1000) > end_ms:
            break
    return sorted(out)


def _vwap(bars: list[tuple[int, float, float]]) -> float | None:
    """Volume-weighted average price over a list of (ts, close, vol) bars."""
    num = sum(px * vol for _, px, vol in bars)
    den = sum(vol for _, _, vol in bars)
    if den <= 0:
        # fall back to a simple mean if every bar reports zero volume
        closes = [px for _, px, _ in bars]
        return statistics.fmean(closes) if closes else None
    return num / den


def _realized_vol(bars: list[tuple[int, float, float]]) -> float | None:
    """Stdev of 1-min log returns over the bar list."""
    closes = [px for _, _, px in [(t, v, px) for t, px, v in bars]]
    closes = [px for _, px, _ in bars]
    rets = []
    for i in range(1, len(closes)):
        if closes[i - 1] > 0 and closes[i] > 0:
            rets.append(math.log(closes[i] / closes[i - 1]))
    if len(rets) < 5:
        return None
    return statistics.pstdev(rets)


def build_symbol_records(symbol: str,
                         klines: list[tuple[int, float, float]],
                         funding: list[tuple[int, float]]) -> list[dict]:
    """Generate the FULL H-017 resolved-pick series for one symbol.

    Network-free. One record per settlement that FIRED a pick (displacement &
    funding-quartile gates both pass). No cherry-picking: every qualifying
    settlement is emitted.
    """
    if not klines or not funding:
        return []
    by_ts = {t: (px, vol) for t, px, vol in klines}
    minute = lambda dt_ms: dt_ms - (dt_ms % 60_000)  # noqa: E731

    # per-symbol rolling funding-magnitude quartile, strictly-past
    funding.sort()
    fmag = [abs(r) for _, r in funding]
    funding_top_q: dict[int, bool] = {}
    for i, (ts, _) in enumerate(funding):
        if i < FUNDING_ROLL:
            funding_top_q[ts] = False
            continue
        past = sorted(fmag[i - FUNDING_ROLL:i])
        # 75th percentile of the strictly-past window
        q_idx = int(FUNDING_QUANTILE * (len(past) - 1))
        thresh = past[q_idx]
        funding_top_q[ts] = fmag[i] >= thresh and thresh > 0

    records: list[dict] = []
    for ts, rate in funding:
        # funding settlement timestamps land a few ms off the clock hour;
        # snap to the settlement minute
        t_settle = minute(ts)
        # --- gates need data, all strictly at-or-before T except entry/exit ---
        vwap_bars = [(m, *by_ts[m]) for m in
                     range(t_settle - VWAP_LOOKBACK_MIN * 60_000, t_settle, 60_000)
                     if m in by_ts]
        vol_bars = [(m, *by_ts[m]) for m in
                    range(t_settle - VOL_LOOKBACK_MIN * 60_000, t_settle, 60_000)
                    if m in by_ts]
        if len(vwap_bars) < VWAP_LOOKBACK_MIN // 2 or \
           len(vol_bars) < VOL_LOOKBACK_MIN // 2:
            continue
        if t_settle not in by_ts:
            continue
        prior_vwap = _vwap(vwap_bars)
        rvol = _realized_vol(vol_bars)
        if prior_vwap is None or rvol is None or prior_vwap <= 0 or rvol <= 0:
            continue
        price_at_T = by_ts[t_settle][0]
        displacement = price_at_T / prior_vwap - 1.0
        # --- GATE 1: displacement magnitude vs recent realized vol ---
        if abs(displacement) <= DISPLACEMENT_MULT * rvol:
            continue
        # --- GATE 2: funding magnitude in per-symbol rolling top quartile ---
        if not funding_top_q.get(ts, False):
            continue
        # --- FADE: entry opposite the displacement sign ---
        direction = -1 if displacement > 0 else 1   # +1 long, -1 short
        # entry = close of the T+1min bar
        t_entry = t_settle + ENTRY_OFFSET_MIN * 60_000
        if t_entry not in by_ts:
            continue
        entry_px = by_ts[t_entry][0]
        if entry_px <= 0:
            continue
        # --- forward path: VWAP reversion / 30-min time stop / +-20bps stop ---
        exit_px = None
        exit_reason = None
        hard_stop = HARD_STOP_BPS / 10_000.0
        for step in range(1, TIME_STOP_MIN + 1):
            t_bar = t_entry + step * 60_000
            if t_bar not in by_ts:
                continue
            px = by_ts[t_bar][0]
            signed_move = (px / entry_px - 1.0) * direction
            # hard stop (loss side)
            if signed_move <= -hard_stop:
                exit_px, exit_reason = px, "hard_stop"
                break
            # hard stop (profit side capped at +20bps too -- symmetric)
            if signed_move >= hard_stop:
                exit_px, exit_reason = px, "hard_take"
                break
            # VWAP reversion: price has crossed back through the prior-1h VWAP
            # relative to the displacement that triggered the fade
            if displacement > 0 and px <= prior_vwap:
                exit_px, exit_reason = px, "vwap_revert"
                break
            if displacement < 0 and px >= prior_vwap:
                exit_px, exit_reason = px, "vwap_revert"
                break
        if exit_px is None:
            # time stop -- use last available bar within the 30-min window
            for step in range(TIME_STOP_MIN, 0, -1):
                t_bar = t_entry + step * 60_000
                if t_bar in by_ts:
                    exit_px = by_ts[t_bar][0]
                    exit_reason = "time_stop"
                    break
        if exit_px is None:
            continue
        gross_ret = (exit_px / entry_px - 1.0) * direction   # signed by fade
        entry_dt = datetime.fromtimestamp(t_entry / 1000, timezone.utc)
        exit_dt = datetime.fromtimestamp((t_entry + TIME_STOP_MIN * 60_000) / 1000,
                                         timezone.utc)
        records.append({
            "symbol": symbol,
            "settlement_utc": datetime.fromtimestamp(
                t_settle / 1000, timezone.utc).isoformat(),
            "entry_date": entry_dt.date().isoformat(),
            "timestamp": entry_dt.date().isoformat(),
            "resolved_at": exit_dt.date().isoformat(),
            "direction": direction,
            "displacement_bps": round(displacement * 10_000, 2),
            "realized_vol_bps": round(rvol * 10_000, 2),
            "funding_rate": rate,
            "exit_reason": exit_reason,
            "gross_ret": gross_ret,
            "gross_ret_bps": round(gross_ret * 10_000, 3),
            # conviction magnitude the harness scores: how far past the
            # displacement gate this pick fired (winners should carry more)
            HARNESS_FIELD: abs(displacement) / (DISPLACEMENT_MULT * rvol),
            # status set later after the post-cost resolution
        })
    return records


def resolve_status(records: list[dict], cost_bps: float) -> None:
    """Mutate records in place: gross + net WON/LOST resolution.

    Gross status drives the harness verdict (the signal's raw separation).
    Net status (after cost_bps round-trip) drives the post-cost WR.
    """
    cost = cost_bps / 10_000.0
    for r in records:
        gross = r["gross_ret"]
        net = gross - cost
        r["status"] = "WON" if gross > 0 else "LOST"      # harness reads this
        r["net_ret"] = net
        r["net_ret_bps"] = round(net * 10_000, 3)
        r["net_status"] = "WON" if net > 0 else "LOST"


# ===========================================================================
# Harness verdict -- imported UNMODIFIED, fed the FULL record series
# ===========================================================================
def harness_verdict(records: list[dict], window_days: int = WINDOW_DAYS) -> dict:
    """Run records through edge_stability_harness.evaluate() -- THE gate.

    The harness loader is monkey-patched ONLY to point at our in-memory record
    list (the harness module code, EFF_MIN/MIN_WINDOW_N/MIN_STABLE_WINDOWS, and
    is_admissible() logic are all UNMODIFIED). Restored in finally.
    """
    orig_load = harness._load
    try:
        harness._load = lambda: records           # type: ignore[assignment]
        evaluation = harness.evaluate(HARNESS_FIELD, window_days)
        admissible = harness.is_admissible(HARNESS_FIELD, window_days)
        evaluation["is_admissible_call"] = admissible
        return evaluation
    finally:
        harness._load = orig_load                 # type: ignore[assignment]


# ===========================================================================
# Research driver
# ===========================================================================
def load_cache(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return {}
    return {}


def research(quick: bool, months: int, cache_path: Path,
             refresh: bool) -> dict:
    universe = QUICK_UNIVERSE if quick else UNIVERSE
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - months * 30 * 24 * 3600 * 1000

    cache = {} if refresh else load_cache(cache_path)
    cache_dirty = False

    all_records: list[dict] = []
    per_symbol: dict[str, dict] = {}

    for sym in universe:
        sym_cache = cache.get(sym, {})
        funding = [(int(t), float(r)) for t, r in sym_cache.get("funding", [])]
        klines = [(int(t), float(px), float(v))
                  for t, px, v in sym_cache.get("klines", [])]

        if not funding:
            print(f"# [{sym}] fetching funding history ...", file=sys.stderr)
            funding = fetch_funding_history(sym, start_ms, now_ms)
            cache_dirty = True
        if not klines:
            # fetch a +-FETCH_PAD_MIN window of 1-min klines around every
            # settlement -- complete coverage of every signal evaluation point,
            # far cheaper than the full continuous 1-min history.
            settles = settlement_timestamps(start_ms, now_ms)
            print(f"# [{sym}] fetching 1m klines around "
                  f"{len(settles)} settlements ...", file=sys.stderr)
            kl: dict[int, tuple[float, float]] = {}
            pad = FETCH_PAD_MIN * 60_000
            # merge overlapping windows so adjacent settlements share fetches
            spans: list[tuple[int, int]] = []
            for t in settles:
                lo, hi = t - pad, t + pad
                if spans and lo <= spans[-1][1] + 60_000:
                    spans[-1] = (spans[-1][0], max(spans[-1][1], hi))
                else:
                    spans.append((lo, hi))
            for lo, hi in spans:
                for t, px, v in fetch_1m_klines(sym, lo, hi):
                    kl[t] = (px, v)
            klines = sorted((t, px, v) for t, (px, v) in kl.items())
            cache_dirty = True

        if funding or klines:
            cache[sym] = {
                "funding": [[t, r] for t, r in funding],
                "klines": [[t, px, v] for t, px, v in klines],
            }

        recs = build_symbol_records(sym, klines, funding)
        all_records.extend(recs)
        fdates = ([datetime.fromtimestamp(funding[0][0] / 1000,
                                          timezone.utc).date().isoformat(),
                   datetime.fromtimestamp(funding[-1][0] / 1000,
                                          timezone.utc).date().isoformat()]
                  if funding else ["n/a", "n/a"])
        per_symbol[sym] = {
            "n_picks": len(recs),
            "funding_events": len(funding),
            "kline_bars": len(klines),
            "funding_span": f"{fdates[0]} -> {fdates[1]}",
        }
        print(f"# [{sym}] {len(recs)} picks from {len(funding)} settlements, "
              f"{len(klines)} 1m bars", file=sys.stderr)

    if cache_dirty:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(cache), encoding="utf-8")
        print(f"# cache written -> {cache_path}", file=sys.stderr)

    return {
        "hypothesis": "H-017",
        "asset_class": "CRYPTO",
        "months": months,
        "universe": universe,
        "per_symbol": per_symbol,
        "records": all_records,
        "n": len(all_records),
    }


def evaluate(res: dict) -> dict:
    """Resolve picks, run the harness, apply the post-cost gate."""
    records = res["records"]
    resolve_status(records, ROUND_TRIP_COST_BPS)

    n = len(records)
    won = sum(1 for r in records if r["status"] == "WON")
    res["pooled_gross_wr"] = round(won / n, 4) if n else None
    net_won = sum(1 for r in records if r["net_status"] == "WON")
    res["pooled_net_wr"] = round(net_won / n, 4) if n else None

    # gross vs net edge (mean per-trade return, bps)
    gross_edge = (statistics.fmean(r["gross_ret"] for r in records)
                  if records else 0.0)
    net_edge = (statistics.fmean(r["net_ret"] for r in records)
                if records else 0.0)
    res["gross_edge_bps"] = round(gross_edge * 10_000, 3)
    res["net_edge_bps"] = round(net_edge * 10_000, 3)
    # cost-survival: fraction of gross edge retained after the 30bps round-trip
    if gross_edge > 0:
        survival = net_edge / gross_edge
    else:
        survival = 0.0   # no positive gross edge -> nothing survives
    res["cost_survival_pct"] = round(survival * 100, 2)
    res["cost_gate_pass"] = survival >= COST_SURVIVAL_MIN

    # harness verdict on the FULL record series (gross status)
    if n < harness.MIN_WINDOW_N:
        res["harness"] = {
            "admissible": False,
            "windows_scored": 0,
            "reason": f"INSUFFICIENT DATA -- {n} picks, harness needs "
                      f">= {harness.MIN_WINDOW_N} per 14d window",
        }
    else:
        res["harness"] = harness_verdict(records, WINDOW_DAYS)

    h = res["harness"]
    ws = h.get("windows_scored", 0)
    same_sign_count = max(h.get("strong_positive", 0),
                          h.get("strong_negative", 0))

    # --- VERDICT logic (honest, per the H-017 acceptance criteria) ---
    if ws < 5:
        verdict = "UNTESTED-data-gap"
        verdict_reason = (
            f"only {ws} fourteen-day windows scored (need >=5 for a verdict). "
            f"Data density is insufficient -- explicitly NOT a pass.")
    elif h.get("strong_positive", 0) > 0 and h.get("strong_negative", 0) > 0:
        verdict = "REJECTED"
        verdict_reason = (
            f"eff SIGN SPLITS ({h.get('strong_positive')}+/"
            f"{h.get('strong_negative')}-) across strong windows -- "
            f"sign-unstable, fails the same-sign requirement.")
    elif not h.get("admissible", False):
        verdict = "REJECTED"
        verdict_reason = h.get("reason", "harness rejected")
    elif not res["cost_gate_pass"]:
        verdict = "REJECTED"
        verdict_reason = (
            f"harness ADMISSIBLE but the post-cost gate FAILS: only "
            f"{res['cost_survival_pct']}% of gross edge survives the "
            f"{ROUND_TRIP_COST_BPS:.0f}bps round-trip (need >=60%).")
    else:
        verdict = "ADMISSIBLE"
        verdict_reason = (
            f"harness ADMISSIBLE (stable same-sign separation, "
            f"{same_sign_count} strong windows) AND post-cost gate passes "
            f"({res['cost_survival_pct']}% of gross edge survives).")

    res["verdict"] = verdict
    res["verdict_reason"] = verdict_reason
    return res


# ===========================================================================
# Report
# ===========================================================================
def render_report(res: dict) -> str:
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    h = res.get("harness", {})
    verdict = res["verdict"]
    effs = h.get("per_window_eff", [])
    eff_str = " ".join((f"{e['eff']:+.2f}" if e.get("eff") is not None
                        else "n/a") for e in effs)
    eff_list = [e["eff"] for e in effs if e.get("eff") is not None]

    out = [
        "# C-3 / H-017 — CRYPTO Funding-Settlement Liquidation-Cascade — 2026-05-18",
        "",
        f"_Generated {ts} by `tools/c3_funding_settlement_research.py`._",
        "",
        "**Status: OPT-IN RESEARCH SIDECAR. No production wiring.** No caller in "
        "`quality_gates.py`, `dashboard_generator.py`, or any pick-generation / "
        "scoring path. Reads free Binance market data, writes this report.",
        "",
        "## Hypothesis (H-017, pre-registered per M-107)",
        "",
        "Perpetual funding settles every 8h at fixed UTC clock times "
        "(00:00 / 08:00 / 16:00). Over-leveraged positions get squeezed; thin "
        "books at the settlement minute overshoot, then mean-revert. The signal "
        "is FORCED FLOW at a known clock time -- NOT a funding-rate directional "
        "bet. **FADE the displacement.**",
        "",
        "## Method (signal defined BEFORE the run)",
        "",
        f"1. Universe: {len(res['universe'])} liquid Binance USDT-M perps "
        f"({', '.join(res['universe'])}).",
        f"2. Span: {res['months']} months of free 1-min klines + "
        "`/fapi/v1/fundingRate` history (both paginated via startTime/endTime; "
        "API-failover mirror chain fapi/fapi1/fapi2 -> Bybit).",
        f"3. At each 8h settlement T: displacement = price(T) / prior-1h VWAP "
        f"- 1; realized vol = stdev of prior-{VOL_LOOKBACK_MIN}-min 1-min log "
        "returns.",
        f"4. A pick FIRES when |displacement| > {DISPLACEMENT_MULT} x realized "
        f"vol AND |funding| is in its per-symbol rolling top quartile "
        f"({FUNDING_ROLL}-obs window, strictly-past).",
        f"5. Direction = FADE (entry opposite the displacement). Entry = close "
        f"of the T+{ENTRY_OFFSET_MIN}min bar.",
        f"6. Exit = whichever first: VWAP reversion / {TIME_STOP_MIN}-min time "
        f"stop / +-{HARD_STOP_BPS:.0f}bps hard stop. Forward return signed by "
        "the fade direction.",
        f"7. Each settlement that fires -> one resolved-pick record (status "
        "WON/LOST from the signed gross return). The FULL signal-generated "
        "series is fed to the harness -- no cherry-picking.",
        "8. `tools/edge_stability_harness.py` imported UNMODIFIED "
        f"(EFF_MIN={harness.EFF_MIN}, MIN_WINDOW_N={harness.MIN_WINDOW_N}, "
        f"MIN_STABLE_WINDOWS={harness.MIN_STABLE_WINDOWS}); "
        "`is_admissible()` called on the record series.",
        f"9. Post-cost gate: {ROUND_TRIP_COST_BPS:.0f}bps crypto round-trip; "
        "net edge must retain >=60% of gross.",
        "",
        f"## VERDICT: **{verdict}**",
        "",
        f"{res['verdict_reason']}",
        "",
        "## Per-symbol data coverage",
        "",
        "| symbol | picks fired | funding events | 1m bars | funding span |",
        "|---|---|---|---|---|",
    ]
    for k, v in res.get("per_symbol", {}).items():
        out.append(f"| {k} | {v['n_picks']} | {v['funding_events']} | "
                   f"{v['kline_bars']} | {v['funding_span']} |")

    out += [
        "",
        "## Harness verdict (THE gate -- 14-day walk-forward)",
        "",
        f"- **n picks (full signal series):** {res['n']}",
        f"- **windows scored:** {h.get('windows_scored', 0)}",
        f"- **windows strong (|eff|>={harness.EFF_MIN}):** "
        f"{h.get('windows_strong', 0)}  "
        f"(+{h.get('strong_positive', 0)} / -{h.get('strong_negative', 0)})",
        f"- **per-window eff (new->old):** `{eff_str or 'n/a'}`",
        f"- **same-sign check:** "
        + ("PASS -- one sign dominates" if h.get("admissible")
           else f"FAIL -- {h.get('strong_positive', 0)}+ vs "
                f"{h.get('strong_negative', 0)}- (signs split)"
           if (h.get("strong_positive", 0) and h.get("strong_negative", 0))
           else "n/a -- too few strong windows"),
        f"- **harness.is_admissible():** {h.get('is_admissible_call', False)}",
        f"- **harness reason:** {h.get('reason', 'n/a')}",
        "",
        "## Win rate & edge",
        "",
        f"- **pooled gross WR:** "
        + (f"{res['pooled_gross_wr']*100:.1f}%" if res.get('pooled_gross_wr')
           is not None else "n/a"),
        f"- **pooled net WR (after {ROUND_TRIP_COST_BPS:.0f}bps):** "
        + (f"{res['pooled_net_wr']*100:.1f}%" if res.get('pooled_net_wr')
           is not None else "n/a"),
        f"- **gross edge:** {res.get('gross_edge_bps')} bps/trade",
        f"- **net edge:** {res.get('net_edge_bps')} bps/trade",
        f"- **cost-survival:** {res.get('cost_survival_pct')}% of gross edge "
        f"retained (gate: >={COST_SURVIVAL_MIN*100:.0f}%) -- "
        f"{'PASS' if res.get('cost_gate_pass') else 'FAIL'}",
        "",
        "## Honest conclusion & next step",
        "",
    ]

    ws = h.get("windows_scored", 0)
    if verdict == "UNTESTED-data-gap":
        out.append(
            f"**H-017 is UNTESTED (data-gap).** The harness scored only {ws} "
            "fourteen-day window(s); the H-017 acceptance bar and the operator "
            "rules require >=5 for a verdict. Each window needs >=80 picks with "
            ">=15 winners and >=15 losers -- funding-settlement displacement "
            "picks fire too sparsely at the 1.5x-vol / top-quartile gate to "
            "reach that density across a 14-day bucket. **This is explicitly "
            "NOT a pass.** Next step: a longer span (12-18 months) and/or a "
            "wider perp universe would raise window density without touching "
            "the signal definition; only then can the harness render a real "
            "eff-stability verdict. Re-running with a looser gate to manufacture "
            "window count would be p-hacking the density, not edge discovery.")
    elif verdict == "REJECTED" and h.get("strong_positive", 0) and \
            h.get("strong_negative", 0):
        out.append(
            f"**H-017 was properly TESTED and REJECTED.** The harness scored "
            f"{ws} windows -- enough for a real verdict -- and the eff sign "
            f"SPLITS ({h.get('strong_positive')}+/{h.get('strong_negative')}-) "
            "across the strong windows. The fade signal separates winners from "
            "losers in some 14-day windows but flips sign in others -- the "
            "identical regime-noise failure mode that killed `method_a_score` "
            "and the prior edge-hunt candidates. A sound mechanical prior "
            "(forced flow at a clock time) is not an edge until the harness "
            "says so, and it does not. **NOT admissible, NOT wired, NOT sized.**")
    elif verdict == "REJECTED" and h.get("admissible") and \
            not res.get("cost_gate_pass"):
        out.append(
            f"**H-017 PASSED the harness but FAILS the post-cost gate.** The "
            f"gross fade signal is stably admissible ({ws} windows, same-sign), "
            f"but only {res.get('cost_survival_pct')}% of the gross edge "
            f"survives the {ROUND_TRIP_COST_BPS:.0f}bps crypto round-trip "
            "(>=60% required). The mechanical reversion is real but too thin "
            "to clear realistic retail costs -- the same constraint that killed "
            "the funding-arb carry trade (H-012). **NOT wired, NOT sized.** A "
            "future retry would need a materially cheaper cost structure "
            "(maker rebates / VIP fee tier) before it could clear the gate.")
    elif verdict == "REJECTED":
        out.append(
            f"**H-017 was TESTED and REJECTED by the harness.** {h.get('reason')}"
            " The fade signal does not show stable same-sign separation across "
            "the scored walk-forward windows. **NOT admissible, NOT wired, "
            "NOT sized.**")
    else:  # ADMISSIBLE
        out.append(
            f"**H-017 CLEARED both gates** -- the harness ({ws} windows, stable "
            f"same-sign separation) AND the post-cost gate "
            f"({res.get('cost_survival_pct')}% of gross edge survives the "
            f"{ROUND_TRIP_COST_BPS:.0f}bps round-trip). Against a long kill "
            "streak this is a surprising result and must be treated as a "
            "*research candidate*, NOT a green light. Before any wiring it "
            "needs: (a) re-test on a fresh out-of-sample span, (b) intraday "
            "slippage modelling at the settlement minute (thin books cut both "
            "ways -- the fill itself may be worse than the 30bps assumption), "
            "(c) a deflated-Sharpe / multiple-testing correction, "
            "(d) operator review. The harness is necessary, not sufficient.")

    out += [
        "",
        f"_Per-window eff: `{eff_list}`_",
        "",
        "Reproducer: `python tools/c3_funding_settlement_research.py` "
        "(uses the committed cache; `--refresh-cache` to re-fetch).",
        "",
    ]
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true",
                    help="3-symbol universe for a fast smoke run")
    ap.add_argument("--months", type=int, default=DEFAULT_MONTHS,
                    help=f"history span in months (default {DEFAULT_MONTHS})")
    ap.add_argument("--refresh-cache", action="store_true",
                    help="ignore the cache and re-fetch all data")
    ap.add_argument("--cache", type=Path,
                    default=ROOT / "tools" / "cache" /
                            "c3_funding_settlement_cache.json")
    ap.add_argument("--out", type=Path,
                    default=ROOT / "reports" /
                            "c3_funding_settlement_research_2026-05-18.md")
    args = ap.parse_args()

    args.out = Path(args.out).resolve()
    args.cache = Path(args.cache).resolve()

    print("# C-3 / H-017 funding-settlement research -- starting ...",
          file=sys.stderr)
    res = research(args.quick, args.months, args.cache, args.refresh_cache)
    res = evaluate(res)

    report = render_report(res)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")
    print(f"# wrote {args.out}", file=sys.stderr)

    summary = {
        "verdict": res["verdict"],
        "n": res["n"],
        "windows_scored": res["harness"].get("windows_scored", 0),
        "is_admissible": res["harness"].get("is_admissible_call",
                                            res["harness"].get("admissible",
                                                               False)),
        "cost_survival_pct": res["cost_survival_pct"],
        "report": (str(args.out.relative_to(ROOT)).replace("\\", "/")
                   if args.out.is_relative_to(ROOT) else str(args.out)),
    }
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
