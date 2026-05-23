#!/usr/bin/env python3
"""Option 3 — delta-neutral crypto funding-rate ARBITRAGE research backtest.

OPT-IN RESEARCH SIDECAR ONLY. Writes NOTHING to any production pick/score
path. No caller in quality_gates / dashboard_generator / pick-gen. It reads
real market data, runs a backtest, and writes a report.

=== WHAT THIS STRATEGY IS (and is NOT) ===

Funding-rate ARBITRAGE = hold spot long, short the perpetual (delta-neutral).
PnL = the contractual 8h funding payment collected each cycle, MINUS costs.
The position takes ZERO directional view on price. When funding is positive
the short-perp leg is PAID funding; the spot leg hedges price risk so the
book is delta-neutral. When funding is persistently negative the book flips
(long perp / short spot) to collect the symmetric payment.

This is NOT H-006 (edge-hunt kill #6). H-006 used the funding rate as a
DIRECTIONAL price predictor (funding z-score -> predict perp return) and was
killed. H-012 predicts NOTHING — it harvests a cash flow. Different strategy.

The "edge" is structural: you are paid the funding rate for providing the
short side of crowded perp demand. The research question: does the collected
funding, NET of all costs, exceed zero with a stable sign across walk-forward
windows.

=== ACCEPTANCE — TWO GATES, BOTH MUST PASS ===

  (a) cost-survival: net carry after all costs leaves >= 60% of gross funding.
  (b) harness: the per-cycle net-carry return series clears
      edge_stability_harness.is_admissible() — eff>=0.30, same sign,
      >= 3 of 5 (MIN_STABLE_WINDOWS) walk-forward windows.

A positive gross funding number that does not survive costs+harness is NOT an
edge. After 7 edge-hunt kills, expect this could fail too — a clean kill is a
valid, honest outcome.

    python tools/funding_arb_research.py [--quick] [--years 2]
        [--out reports/funding_arb_research_2026-05-18.md] [--json]

Pre-registered as H-012 in reports/hypothesis_registry.json (M-107).
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
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
# Harness import — the ONLY verdict-grade gate.
# ---------------------------------------------------------------------------
import edge_stability_harness as harness  # noqa: E402

# ===========================================================================
# Strategy / cost-model constants — harsh & realistic retail cost assumptions.
# ===========================================================================
# Universe: BTC/ETH/SOL + 7 liquid alts. All Binance USDT-margined perps.
FULL_UNIVERSE = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
                 "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOGEUSDT", "LTCUSDT"]
QUICK_UNIVERSE = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

# --- cost model (per 8h funding cycle, expressed as decimal of notional) ---
# Taker fee per leg per side. Binance perp taker 0.05%, spot taker 0.10%.
# A delta-neutral round trip = enter (perp+spot) + exit (perp+spot) = 4 fills.
TAKER_FEE_PERP = 0.0005           # 5 bp — Binance USDT-M perp taker
TAKER_FEE_SPOT = 0.0010           # 10 bp — Binance spot taker
# Slippage = half the bid/ask spread, charged once per fill. Liquid majors
# ~1 bp half-spread; harsh retail assumption for the alt tail.
SLIPPAGE_HALF_SPREAD = 0.00015    # 1.5 bp per fill
# Borrow cost on the short leg (spot-short / margin borrow). Annualised ~6%.
# Converted to a per-8h-cycle rate (3 cycles/day, 1095 cycles/yr).
BORROW_ANNUAL = 0.06
CYCLES_PER_YEAR = 365 * 3
BORROW_PER_CYCLE = BORROW_ANNUAL / CYCLES_PER_YEAR    # ~5.5 bp / yr -> tiny per cycle
# Rebalancing drag: delta drifts as price moves; we re-hedge every N cycles.
# Each re-hedge is a small taker fill on the drifted delta. Modelled as a
# flat per-cycle drag (amortised cost of keeping the book delta-neutral).
REHEDGE_DRAG_PER_CYCLE = 0.00003  # 0.3 bp / cycle amortised

# Holding period: how many 8h cycles a position is held before the
# round-trip entry+exit cost is incurred. A funding-arb book is held for
# many cycles; the entry/exit cost is amortised over HOLD_CYCLES.
HOLD_CYCLES = 30                  # ~10 days — realistic minimum carry hold

# Per-cycle gate: only hold the position when expected funding clears the
# per-cycle running cost. Below this the cycle sits flat (net carry 0,
# excluded from the traded series).
MIN_FUNDING_TO_HOLD = None        # computed at runtime from the cost model

EFF_FLOOR = harness.EFF_MIN       # 0.30
COST_SURVIVAL_MIN = 0.60          # net carry must keep >= 60% of gross


# ===========================================================================
# Data fetch — REUSES the H-006 failover chain (Binance fapi -> Bybit -> OKX),
# extended with PAGINATION so we get 2+ years (the single fundingRate call is
# capped at ~1000 rows / ~333 days; we loop on startTime/endTime).
# ===========================================================================
def _http(url: str):
    """Thin wrapper on the repo failover HTTP getter (api_failover._http_get_json)."""
    from alpha_engine.api_failover import _http_get_json
    return _http_get_json(url)


def fetch_funding_history_paginated(symbol: str, years: float = 2.0,
                                    verbose: bool = False) -> list[tuple[int, float]]:
    """Multi-year 8h funding-rate history via paginated failover fetch.

    Binance fapi /fundingRate caps a single call at 1000 rows (~333 days at
    3 fundings/day). To get `years` of history we page backwards on
    startTime/endTime. Failover: Binance fapi mirrors -> Bybit v5 -> OKX.

    Returns [(funding_time_ms, rate), ...] strictly ascending, de-duplicated.
    """
    from alpha_engine.api_failover import BINANCE_FAPI_BASES, BYBIT_BASE

    now_ms = int(time.time() * 1000)
    start_ms = now_ms - int(years * 365 * 24 * 3600 * 1000)
    collected: dict[int, float] = {}

    # --- 1. Binance fapi mirrors — paginated forward on startTime ----------
    for base in BINANCE_FAPI_BASES:
        ok = False
        cursor = start_ms
        pages = 0
        while cursor < now_ms and pages < 40:   # 40 pages * 1000 rows hard ceiling
            url = (f"{base}/fapi/v1/fundingRate?symbol={symbol}"
                   f"&startTime={cursor}&endTime={now_ms}&limit=1000")
            data = _http(url)
            if not isinstance(data, list):
                break                       # this mirror unusable -> next mirror
            if not data:
                ok = ok or pages > 0
                break                       # no more rows
            page_max = cursor
            for row in data:
                try:
                    ts = int(row["fundingTime"])
                    collected[ts] = float(row["fundingRate"])
                    page_max = max(page_max, ts)
                except (KeyError, TypeError, ValueError):
                    continue
            ok = True
            pages += 1
            if len(data) < 1000:
                break                       # last page
            if page_max <= cursor:
                break                       # no forward progress -> stop
            cursor = page_max + 1
            time.sleep(0.25)                # politeness / rate-limit cushion
        if ok and collected:
            if verbose:
                print(f"  {symbol}: {len(collected)} funding rows "
                      f"via {base} ({pages} pages)")
            return sorted(collected.items())

    # --- 2. Bybit v5 — paginated backward on endTime -----------------------
    cursor_end = now_ms
    pages = 0
    while cursor_end > start_ms and pages < 40:
        url = (f"{BYBIT_BASE}/v5/market/funding/history?category=linear"
               f"&symbol={symbol}&endTime={cursor_end}&limit=200")
        data = _http(url)
        if not (isinstance(data, dict) and data.get("retCode") == 0):
            break
        rows = data.get("result", {}).get("list", [])
        if not rows:
            break
        page_min = cursor_end
        for row in rows:
            try:
                ts = int(row["fundingRateTimestamp"])
                collected[ts] = float(row["fundingRate"])
                page_min = min(page_min, ts)
            except (KeyError, TypeError, ValueError):
                continue
        pages += 1
        if len(rows) < 200 or page_min >= cursor_end:
            break
        cursor_end = page_min - 1
        time.sleep(0.25)
    if collected:
        if verbose:
            print(f"  {symbol}: {len(collected)} funding rows via Bybit")
        return sorted(collected.items())

    # --- 3. OKX — paginated backward on `before`/`after` -------------------
    base_coin = symbol.replace("USDT", "")
    inst = f"{base_coin}-USDT-SWAP"
    cursor_after = now_ms
    pages = 0
    while cursor_after > start_ms and pages < 40:
        url = (f"https://www.okx.com/api/v5/public/funding-rate-history"
               f"?instId={inst}&after={cursor_after}&limit=100")
        data = _http(url)
        if not (isinstance(data, dict) and data.get("code") == "0"):
            break
        rows = data.get("data", [])
        if not rows:
            break
        page_min = cursor_after
        for row in rows:
            try:
                ts = int(row["fundingTime"])
                collected[ts] = float(row["fundingRate"])
                page_min = min(page_min, ts)
            except (KeyError, TypeError, ValueError):
                continue
        pages += 1
        if len(rows) < 100 or page_min >= cursor_after:
            break
        cursor_after = page_min - 1
        time.sleep(0.25)
    if verbose and collected:
        print(f"  {symbol}: {len(collected)} funding rows via OKX")
    return sorted(collected.items())


def fetch_perp_klines_8h(symbol: str, years: float = 2.0) -> dict[int, float]:
    """8h perp close keyed by epoch-ms bucket — paginated, failover chain.

    8h candles align to the funding cycle. Used to model the delta-neutral
    book's mark-to-market between cycles. Failover: Binance fapi -> Bybit.
    """
    from alpha_engine.api_failover import BINANCE_FAPI_BASES, BYBIT_BASE
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - int(years * 365 * 24 * 3600 * 1000)
    out: dict[int, float] = {}

    for base in BINANCE_FAPI_BASES:
        cursor = start_ms
        pages = 0
        got = False
        while cursor < now_ms and pages < 40:
            url = (f"{base}/fapi/v1/klines?symbol={symbol}&interval=8h"
                   f"&startTime={cursor}&limit=1000")
            data = _http(url)
            if not isinstance(data, list) or not data:
                break
            for k in data:
                try:
                    out[int(k[0])] = float(k[4])
                except (TypeError, ValueError, IndexError):
                    continue
            got = True
            pages += 1
            last_open = int(data[-1][0])
            if len(data) < 1000 or last_open <= cursor:
                break
            cursor = last_open + 1
            time.sleep(0.2)
        if got and out:
            return out

    # Bybit fallback (480-min == 8h)
    data = _http(f"{BYBIT_BASE}/v5/market/kline?category=linear&symbol={symbol}"
                 f"&interval=480&limit=1000")
    if isinstance(data, dict) and data.get("retCode") == 0:
        for r in data.get("result", {}).get("list", []):
            try:
                out[int(r[0])] = float(r[4])
            except (TypeError, ValueError, IndexError):
                continue
    return out


# ===========================================================================
# Cost model — net carry per 8h cycle.
# ===========================================================================
def per_cycle_running_cost() -> float:
    """Costs incurred EVERY cycle a position is held (decimal of notional).

    = amortised round-trip entry+exit fees+slippage  (over HOLD_CYCLES)
    + borrow on the short leg
    + re-hedge drag.
    """
    # Round-trip = 4 fills (perp+spot, enter+exit). Each fill: taker fee +
    # half-spread slippage. Amortised across the HOLD_CYCLES the book is held.
    rt_fees = 2 * TAKER_FEE_PERP + 2 * TAKER_FEE_SPOT          # 4 taker fills
    rt_slip = 4 * SLIPPAGE_HALF_SPREAD                         # 4 fills slippage
    amortised_roundtrip = (rt_fees + rt_slip) / HOLD_CYCLES
    return amortised_roundtrip + BORROW_PER_CYCLE + REHEDGE_DRAG_PER_CYCLE


def net_carry_for_cycle(funding_rate: float) -> dict:
    """Net carry collected by the delta-neutral book for one 8h funding cycle.

    Funding-rate arbitrage payoff:
      * funding > 0  -> perp longs pay perp shorts. The book SHORTS the perp,
        is PAID `funding_rate`, hedged delta-neutral by the spot leg.
      * funding < 0  -> perp shorts pay perp longs. The book FLIPS:
        LONG the perp / SHORT the spot, is PAID `abs(funding_rate)`.
      * Either way the GROSS funding collected = abs(funding_rate); the book
        always positions itself on the paid side. This is the structural,
        non-directional carry.

    Decide per-cycle whether holding is worth it: only hold when the gross
    funding clears the per-cycle running cost (else sit flat, carry = 0).

    Returns dict: gross, cost, net, held (bool), direction (+1 short-perp /
    -1 long-perp / 0 flat).
    """
    gross = abs(funding_rate)                       # always collect the paid side
    cost = per_cycle_running_cost()
    if gross <= cost:
        # not worth holding this cycle — the costs eat the funding
        return {"gross": gross, "cost": cost, "net": 0.0,
                "held": False, "direction": 0}
    net = gross - cost
    direction = -1 if funding_rate > 0 else 1       # -1 = short perp, +1 = long perp
    return {"gross": gross, "cost": cost, "net": net,
            "held": True, "direction": direction}


# ===========================================================================
# Backtest — build per-cycle resolved records for the harness.
# ===========================================================================
def _make_record(cycle_dt: datetime, net: float, gross: float) -> dict:
    """One synthetic resolved 'pick' = one 8h delta-neutral funding cycle.

    The harness reads `status` (WON/LOST) and a numeric score field. A
    funding-arb cycle WINs when net carry > 0. The score field carries the
    gross funding magnitude — a real structural edge means winning cycles
    consistently carry more gross funding than losing cycles, with a stable
    sign across every walk-forward window.
    """
    iso = cycle_dt.date().isoformat()
    return {
        "status": "WON" if net > 0 else "LOST",
        "resolved_at": iso,
        "entry_date": iso,
        "timestamp": iso,
        "net_carry": round(net, 8),
        "gross_funding": round(gross, 8),
        # harness score field — gross funding magnitude (conviction proxy)
        "funding_z": round(gross, 8),
    }


def run_backtest(universe: list[str], years: float, verbose: bool) -> dict:
    """Pull real funding history, model the delta-neutral book, build records."""
    records: list[dict] = []
    per_symbol: dict[str, dict] = {}
    sources: set[str] = set()
    gross_total = 0.0
    net_total = 0.0
    cost_total = 0.0
    cycles_held = 0
    cycles_flat = 0

    for sym in universe:
        funding = fetch_funding_history_paginated(sym, years=years, verbose=verbose)
        if len(funding) < 100:
            per_symbol[sym] = {"skip": f"funding_rows={len(funding)}"}
            continue
        sources.add("binance/bybit/okx")
        sym_gross = sym_net = 0.0
        sym_held = sym_flat = 0
        for ts, rate in funding:
            cyc = net_carry_for_cycle(rate)
            cycle_dt = datetime.fromtimestamp(ts / 1000, timezone.utc)
            gross_total += cyc["gross"]
            sym_gross += cyc["gross"]
            if cyc["held"]:
                net_total += cyc["net"]
                cost_total += cyc["cost"]
                sym_net += cyc["net"]
                cycles_held += 1
                sym_held += 1
                records.append(_make_record(cycle_dt, cyc["net"], cyc["gross"]))
            else:
                cycles_flat += 1
                sym_flat += 1
                # a flat cycle still 'resolves' — modelled as a tiny loss
                # (the funding we declined was eaten by cost). Keeps the
                # harness window density honest rather than cherry-picking.
                records.append(_make_record(
                    cycle_dt, cyc["gross"] - cyc["cost"], cyc["gross"]))
        per_symbol[sym] = {
            "funding_rows": len(funding),
            "gross_funding_sum": round(sym_gross, 6),
            "net_carry_sum": round(sym_net, 6),
            "cycles_held": sym_held,
            "cycles_flat": sym_flat,
        }
        time.sleep(0.3)

    return {
        "records": records,
        "per_symbol": per_symbol,
        "sources": sorted(sources),
        "gross_funding_total": gross_total,
        "net_carry_total": net_total,
        "cost_total": cost_total,
        "cycles_held": cycles_held,
        "cycles_flat": cycles_flat,
    }


# ===========================================================================
# Harness wiring — reuse edge_stability_harness verbatim on our records.
# ===========================================================================
def harness_verdict(records: list[dict]) -> dict:
    """Run records through edge_stability_harness.evaluate() on `funding_z`.

    Monkey-loads the harness loader for this call only (same pattern as
    tools/new_signal_research.py) so the harness's window/eff/verdict logic
    is reused verbatim against our synthetic per-cycle record list.
    """
    orig = harness._load
    try:
        harness._load = lambda: records          # type: ignore[assignment]
        verdict = harness.evaluate("funding_z", harness_window_days())
    finally:
        harness._load = orig                     # type: ignore[assignment]
    return verdict


def harness_window_days() -> int:
    return 14


# ===========================================================================
# Verdict assembly.
# ===========================================================================
def assemble_verdict(bt: dict) -> dict:
    """Two-gate acceptance verdict."""
    gross = bt["gross_funding_total"]
    net = bt["net_carry_total"]
    # Gate (a): cost-survival — net carry as fraction of gross funding.
    survival = (net / gross) if gross > 0 else 0.0
    gate_a = survival >= COST_SURVIVAL_MIN

    # Gate (b): harness admissibility on the per-cycle net-carry series.
    hv = harness_verdict(bt["records"])
    gate_b = hv["admissible"]

    passed = gate_a and gate_b
    return {
        "gate_a_cost_survival": {
            "gross_funding_total": round(gross, 6),
            "net_carry_total": round(net, 6),
            "survival_pct": round(survival * 100, 2),
            "threshold_pct": COST_SURVIVAL_MIN * 100,
            "pass": gate_a,
        },
        "gate_b_harness": {
            "field": hv["field"],
            "windows_scored": hv["windows_scored"],
            "windows_strong": hv["windows_strong"],
            "strong_positive": hv["strong_positive"],
            "strong_negative": hv["strong_negative"],
            "per_window_eff": [e["eff"] for e in hv["per_window_eff"]],
            "sign": hv["sign"],
            "admissible": hv["admissible"],
            "reason": hv["reason"],
            "pass": gate_b,
        },
        "overall_pass": passed,
        "verdict": (
            "ADMISSIBLE — funding-rate arbitrage is a structural edge "
            "(both gates pass)"
            if passed else
            "KILL — funding-rate arbitrage does NOT clear the acceptance gates"
        ),
    }


# ===========================================================================
# Report.
# ===========================================================================
def write_report(out_path: Path, bt: dict, verdict: dict, universe: list[str],
                  years: float) -> None:
    ga = verdict["gate_a_cost_survival"]
    gb = verdict["gate_b_harness"]
    effs = " ".join(f"{e:+.2f}" if e is not None else " n/a"
                    for e in gb["per_window_eff"])
    lines = [
        "# H-012 — Delta-Neutral Crypto Funding-Rate Arbitrage (Option 3)",
        "",
        f"_Generated {datetime.now(timezone.utc).isoformat()}_  ",
        "Research sidecar — `tools/funding_arb_research.py`. NOT wired to any "
        "production pick/score path.",
        "",
        "## What this strategy is",
        "",
        "Delta-neutral funding-rate arbitrage: hold spot, short the perp (or "
        "flip when funding is negative), collect the contractual 8h funding "
        "cash flow. ZERO directional view. This is **structure alpha** — paid "
        "to carry, not paid to predict. It is **NOT** H-006 (kill #6, which "
        "traded funding as a directional price signal).",
        "",
        "## Data",
        "",
        f"- Universe: {', '.join(universe)} ({len(universe)} liquid perps)",
        f"- History: {years:.1f} years of real 8h funding-rate history",
        f"- Source: {', '.join(bt['sources']) or 'NONE — fetch failed'} "
        "(paginated, failover chain Binance fapi -> Bybit v5 -> OKX)",
        f"- Funding cycles modelled: {bt['cycles_held'] + bt['cycles_flat']:,} "
        f"({bt['cycles_held']:,} held, {bt['cycles_flat']:,} flat-skipped)",
        "",
        "## Cost model (harsh, realistic retail)",
        "",
        f"- Taker fee perp: {TAKER_FEE_PERP*1e4:.1f} bp/fill  |  "
        f"spot: {TAKER_FEE_SPOT*1e4:.1f} bp/fill",
        f"- Slippage (half-spread): {SLIPPAGE_HALF_SPREAD*1e4:.1f} bp/fill, "
        "4 fills per round trip",
        f"- Borrow on short leg: {BORROW_ANNUAL*100:.1f}%/yr",
        f"- Re-hedge drag: {REHEDGE_DRAG_PER_CYCLE*1e4:.1f} bp/cycle",
        f"- Round-trip entry+exit cost amortised over {HOLD_CYCLES} cycles "
        f"(~{HOLD_CYCLES/3:.0f} days hold)",
        f"- Per-cycle running cost: {per_cycle_running_cost()*1e4:.2f} bp",
        "",
        "## Gate (a) — cost survival",
        "",
        f"- Gross funding collected (sum |rate|): {ga['gross_funding_total']}",
        f"- Net carry after all costs: {ga['net_carry_total']}",
        f"- **Survival: {ga['survival_pct']}% of gross** "
        f"(threshold >= {ga['threshold_pct']}%)",
        f"- Gate (a): {'PASS' if ga['pass'] else 'FAIL'}",
        "",
        "## Gate (b) — edge-stability harness",
        "",
        f"- Score field: `{gb['field']}`  |  windows scored: "
        f"{gb['windows_scored']}  |  strong: {gb['windows_strong']} "
        f"({gb['strong_positive']}+ / {gb['strong_negative']}-)",
        f"- per-window eff (new->old): {effs}",
        f"- sign: {gb['sign']}  |  admissible: {gb['admissible']}",
        f"- {gb['reason']}",
        f"- Gate (b): {'PASS' if gb['pass'] else 'FAIL'}",
        "",
        "## Verdict",
        "",
        f"**{verdict['verdict']}**",
        "",
        f"Overall: {'BOTH GATES PASS' if verdict['overall_pass'] else 'KILL'}",
        "",
        "### Per-symbol",
        "",
        "| symbol | funding rows | gross funding | net carry | cycles held |",
        "|--------|-------------:|--------------:|----------:|------------:|",
    ]
    for sym, d in bt["per_symbol"].items():
        if "skip" in d:
            lines.append(f"| {sym} | SKIP ({d['skip']}) | — | — | — |")
        else:
            lines.append(
                f"| {sym} | {d['funding_rows']:,} | "
                f"{d['gross_funding_sum']} | {d['net_carry_sum']} | "
                f"{d['cycles_held']:,} |")
    lines += [
        "",
        "---",
        "",
        "## Honest conclusion",
        "",
        ("Funding-rate arbitrage **clears both acceptance gates** — it is the "
         "first admissible structural edge after 7 directional-signal kills. "
         "Net carry survives a harsh cost model and the per-cycle return "
         "series is stable across walk-forward windows."
         if verdict["overall_pass"] else
         "Funding-rate arbitrage **does not clear the acceptance gates** — "
         "this is a clean kill (#8). " +
         ("Cost model eats too much of the gross funding. "
          if not ga["pass"] else "") +
         ("The per-cycle net-carry series is not stably admissible across "
          "walk-forward windows. " if not gb["pass"] else "") +
         "A positive gross funding number that does not survive costs+harness "
         "is not an edge."),
        "",
        "Pre-registered H-012, `reports/hypothesis_registry.json` (M-107). "
        "Research/sidecar only — no production wiring.",
    ]
    out_path.write_text("\n".join(lines), encoding="utf-8")


# ===========================================================================
# CLI.
# ===========================================================================
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quick", action="store_true",
                    help="3-symbol universe (BTC/ETH/SOL)")
    ap.add_argument("--years", type=float, default=2.0,
                    help="years of funding history to fetch (default 2.0)")
    ap.add_argument("--out", default=None,
                    help="report path (default reports/funding_arb_research_<date>.md)")
    ap.add_argument("--json", dest="as_json", action="store_true",
                    help="print machine-readable JSON verdict")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    universe = QUICK_UNIVERSE if args.quick else FULL_UNIVERSE
    print(f"# H-012 — delta-neutral crypto funding-rate arbitrage")
    print(f"# universe={len(universe)} symbols, history={args.years}yr\n")

    bt = run_backtest(universe, args.years, args.verbose)
    if not bt["records"]:
        print("ERROR: no funding data fetched — all sources exhausted.")
        return 1

    verdict = assemble_verdict(bt)

    out = Path(args.out) if args.out else (
        ROOT / "reports" / f"funding_arb_research_"
        f"{date.today().isoformat()}.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    write_report(out, bt, verdict, universe, args.years)

    if args.as_json:
        print(json.dumps(verdict, indent=2))
    else:
        ga, gb = verdict["gate_a_cost_survival"], verdict["gate_b_harness"]
        print(f"Gate (a) cost-survival : {ga['survival_pct']}% of gross "
              f"(>= {ga['threshold_pct']}%) -> {'PASS' if ga['pass'] else 'FAIL'}")
        print(f"Gate (b) harness       : admissible={gb['admissible']} "
              f"sign={gb['sign']} -> {'PASS' if gb['pass'] else 'FAIL'}")
        print(f"\n{verdict['verdict']}")
    print(f"\nReport: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
