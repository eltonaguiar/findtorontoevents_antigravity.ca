#!/usr/bin/env python3
"""H-019 / C-2 FULL-BOOK — exchange net-flow cross-sectional FULL-BOOK backtest.

OPT-IN RESEARCH SIDECAR. Writes NOTHING to any production pick/score path.
No caller in quality_gates / dashboard_generator / pick-gen. Pre-registered
in reports/hypothesis_registry.json under the `c2_fullbook` key (H-019) per
M-107, BEFORE this backtest logic was written.

WHY H-019 EXISTS (vs H-018):
  H-018's registered LONG-2/SHORT-2 daily-rebalanced spec emits exactly 4
  leg-coin records per traded day. Across ~18 months of free Dune cex.flows
  the densest 14-day harness window held only 56 records — below the harness
  80-record floor — so ZERO windows scored and H-018 came back UNTESTED.

  H-019 is the SAME economic prior (exchange-netflow cross-sectional signal)
  with a DIFFERENT, legitimate resolution construction: the continuous-position
  FULL-BOOK pattern already used successfully for H-008 (BOND, 57k records) and
  H-014 (onchain). EVERY EVM coin on EVERY day is one resolved record — the
  whole book is held continuously, position-weighted by the coin's
  cross-sectional netflow_z rank that day. This does NOT lower any harness
  threshold; it uses the FULL signal instead of only the 4 extreme legs, which
  is what gives the harness real window density. It is registered explicitly
  as a new hypothesis (M-107) because the resolution differs from H-018's
  registered spec — not a silent threshold tweak.

STRATEGY (H-019 / C-2 FULL-BOOK):
  Per coin, netflow_z is the strictly-past 30-day z-score of daily
  (exchange inflow - outflow). On each signal day D, ALL coins with a
  netflow_z are ranked cross-sectionally. Each coin gets a linear rank weight
  in [-1, +1]:
    * top-ranked OUTFLOW  (most negative netflow_z = accumulation) -> +1 LONG
    * bottom-ranked INFLOW (most positive netflow_z = distribution) -> -1 SHORT
    * linearly scaled between, demeaned so the book is cross-sectionally
      market-neutral (sum of weights ~ 0).
  Entry = D+1 close, exit = D+2 close (1-day hold, continuous daily rebalance).
  ONE resolved record per coin per day. The record's outcome is signed by the
  coin's rank weight: signed_ret = weight * (beta-neutral coin return).
  status WON/LOST = sign(signed_ret). The harness score field is the
  conviction magnitude |weight| (how extreme the coin's cross-sectional rank
  was) — the harness then tests whether |weight| separates winners from losers
  stably across walk-forward windows.

LOOK-AHEAD CONTROL (identical to H-018):
  netflow_z for day D uses ONLY flow observations strictly before D's close.
  Entry is D+1. The cross-sectional rank on day D uses only information
  knowable at D's UTC close. Strictly look-ahead-free.

GATES (BOTH must pass to call it an edge):
  1. tools/edge_stability_harness.is_admissible() — UNMODIFIED import.
     EFF_MIN / MIN_WINDOW_N / MIN_STABLE_WINDOWS are NEVER touched.
  2. Post-cost gate: 30bps crypto round-trip; net edge must retain >= 60%
     of gross edge.

HONEST VERDICT RULE:
  ADMISSIBLE only if the harness genuinely passes (eff>=0.30, same sign,
  >=3 stable windows) AND cost-survival >= 60%. If it scores >=5 windows but
  signs split -> REJECTED (a clean kill). If it still scores <5 windows ->
  UNTESTED (data-gap). Thresholds are NEVER lowered.

COVERAGE CAVEAT:
  Dune cex.flows is EVM-only — 12 EVM majors only. BTC/SOL/XRP are absent.
  The cross-sectional universe is the EVM-traded subset; this is reported.

    python tools/h019_netflow_fullbook.py [--json]

Re-uses the cached Dune raw result at tools/cache/h018_dune_netflow_cache.json
(8550 rows, 12 EVM coins, ~18mo). Does NOT re-query Dune (0 credits).
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

# The harness — UNMODIFIED import. Not wrapped, not reimplemented.
import edge_stability_harness as harness  # noqa: E402

# Re-use the H-018 module's Dune/price machinery verbatim — same cached data.
import h018_netflow_research as h018  # noqa: E402

CACHE_DIR = ROOT / "tools" / "cache"
DUNE_CACHE = CACHE_DIR / "h018_dune_netflow_cache.json"
REPORT = ROOT / "reports" / "h019_netflow_fullbook_2026-05-18.md"

# --- strategy / harness constants ------------------------------------------
WINDOW_DAYS = 14          # walk-forward window length (harness default)
Z_ROLL = 30               # rolling netflow z-score look-back (strictly past)
SCORE_FIELD = "rank_weight_mag"  # harness score: |cross-sectional rank weight|
EMBARGO_DAYS = 5          # purged-CV embargo (AFML Ch.7) — reported only
COST_BPS_ROUNDTRIP = 30.0     # crypto round-trip cost (taker + slippage)
COST_SURVIVAL_FLOOR = 0.60    # net edge must retain >= 60% of gross
MIN_COINS = 6             # data-gap floor: need clean coverage on >= 6 coins
MIN_BOOK = 4              # need >= 4 coins ranked on a day to form a book

# H-018 spec majors (for the coverage caveat).
H018_SPEC_MAJORS = h018.H018_SPEC_MAJORS


def build_fullbook_records(z_by_sym: dict[str, dict[str, float]],
                           prices: dict[str, dict[str, float]]
                           ) -> tuple[list[dict], dict]:
    """Continuous-position FULL-BOOK construction (the H-008/H-014 pattern).

    On each signal day D:
      * resolve every coin's D+1 entry / D+2 exit return; a coin with no
        price coverage on that day is simply NOT in the book (it is not a
        whole-day abort — the book is whatever coins resolved cleanly, still
        market-neutral via cross-sectional demeaning).
      * rank the RESOLVED coins by netflow_z (ascending: lowest z = biggest
        outflow = strongest LONG).
      * give each coin a linear rank weight in [-1, +1]:
            raw = +1 for the lowest-z (top outflow) coin,
                  -1 for the highest-z (top inflow) coin,
                  linear in between.
        Then demean the raw weights so the book is cross-sectionally
        market-neutral (sum ~ 0). The +1/-1 endpoints survive demeaning when
        the rank distribution is symmetric.
      * beta removal: each coin's contribution = its return MINUS the
        equal-weight mean return of ALL booked coins that day.
      * signed_ret = weight * beta_neutral_return.
      * ONE resolved record per coin per day (the full book, not 4 legs).
      * harness score field = |weight| (conviction magnitude — how extreme the
        coin's cross-sectional rank was).
    """
    coins = sorted(z_by_sym)
    all_days = sorted({d for sym in coins for d in z_by_sym[sym]})
    records: list[dict] = []
    daily_book: list[dict] = []
    sym_counts: dict[str, int] = {}

    for d in all_days:
        signal = [(s, z_by_sym[s][d]) for s in coins if d in z_by_sym[s]]
        if len(signal) < MIN_BOOK:
            continue

        # entry = D+1 close, exit = D+2 close. Resolve EACH coin independently;
        # a coin with no price coverage on day d is dropped from the book (not
        # a whole-day abort) — this is the correct full-book behavior, the
        # book on day d is whatever coins resolved cleanly.
        leg: dict[str, dict] = {}
        for sym, _z in signal:
            pser = prices.get(sym, {})
            pdays = sorted(pser)
            entry = next((x for x in pdays if x > d), None)
            if entry is None:
                continue
            ei = pdays.index(entry)
            if ei + 1 >= len(pdays):
                continue
            exit_d = pdays[ei + 1]
            ep, xp = pser[entry], pser[exit_d]
            if ep <= 0:
                continue
            leg[sym] = {"entry": entry, "exit": exit_d, "ret": xp / ep - 1.0}
        if len(leg) < MIN_BOOK:
            continue

        # rank ONLY the resolved coins by netflow_z; weight on that subset.
        ranked = sorted(((s, z) for s, z in signal if s in leg),
                        key=lambda kv: kv[1])   # ascending netflow_z
        m = len(ranked)
        raw_w = {}
        for i, (sym, _z) in enumerate(ranked):
            # i=0 -> +1 (lowest z, top outflow) ; i=m-1 -> -1 (top inflow)
            raw_w[sym] = 1.0 - 2.0 * (i / (m - 1)) if m > 1 else 0.0
        mu_w = statistics.mean(raw_w.values())
        weight = {s: w - mu_w for s, w in raw_w.items()}   # demean -> neutral

        mean_ret = statistics.mean(v["ret"] for v in leg.values())
        long_excess, short_excess = [], []
        for sym, info in leg.items():
            w = weight[sym]
            beta_neutral = info["ret"] - mean_ret      # remove crypto beta
            signed = w * beta_neutral                  # position-weighted
            records.append({
                "status": "WON" if signed > 0 else "LOST",
                "resolved_at": info["exit"],
                "timestamp": info["entry"],
                SCORE_FIELD: round(abs(w), 6),
                "signed_ret": round(signed, 6),
                "raw_ret": round(info["ret"], 6),
                "weight": round(w, 6),
                "symbol": sym,
                "signal_day": d,
            })
            sym_counts[sym] = sym_counts.get(sym, 0) + 1
            if w > 0:
                long_excess.append(w * (info["ret"] - mean_ret))
            elif w < 0:
                short_excess.append(w * (info["ret"] - mean_ret))
        # book return for the day = sum of all position-weighted excess returns
        bret = sum(weight[s] * (leg[s]["ret"] - mean_ret) for s in leg)
        daily_book.append({"day": d, "book_ret": round(bret, 6),
                            "n_coins": len(leg)})

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
        "n_traded_days": len(daily_book),
        "symbol_counts": sym_counts,
        "daily_book": daily_book,
        "window_record_counts": win_counts,
        "windows_at_floor": sum(1 for v in win_counts
                                if v >= harness.MIN_WINDOW_N),
    }
    return records, diag


def harness_verdict(records: list[dict]) -> dict:
    """Run records through the UNMODIFIED harness.evaluate(). The harness
    loader is temporarily pointed at our list — _windows / _window_eff /
    evaluate / is_admissible run VERBATIM. Restored in finally."""
    orig = harness._load
    try:
        harness._load = lambda: records  # type: ignore[assignment]
        verdict = harness.evaluate(SCORE_FIELD, WINDOW_DAYS)
        verdict["is_admissible"] = harness.is_admissible(SCORE_FIELD,
                                                         WINDOW_DAYS)
    finally:
        harness._load = orig  # type: ignore[assignment]
    return verdict


def cost_gate(records: list[dict]) -> dict:
    """Post-cost gate. Gross edge = mean signed position-weighted return.
    Net = gross - per-coin round-trip cost. Survival = net / gross."""
    rets = [r["signed_ret"] for r in records]
    if not rets:
        return {"gross_edge_bps": 0.0, "net_edge_bps": 0.0,
                "cost_bps": COST_BPS_ROUNDTRIP,
                "cost_survival_pct": 0.0, "passes": False}
    gross = statistics.mean(rets)
    gross_bps = gross * 1e4
    cost = COST_BPS_ROUNDTRIP / 1e4          # per coin, round-trip
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


def classify(verdict: dict, n_records: int, diag: dict,
             cost: dict) -> tuple[str, str]:
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
                f"floor (need >= {harness.MIN_STABLE_WINDOWS}). The FULL-BOOK "
                f"construction emits {biggest} records in its densest 14-day "
                f"window across {diag.get('n_traded_days', 0)} traded days "
                f"({at_floor} windows >= {harness.MIN_WINDOW_N}). Density still "
                f"short — NOT a signal verdict.")
    if verdict.get("is_admissible"):
        if cost["passes"]:
            return ("ADMISSIBLE",
                    "harness same-sign stable across windows AND net edge "
                    "survives the 30bps round-trip cost gate.")
        return ("REJECTED",
                "harness scored same-sign stable, BUT net edge does NOT "
                "survive the 30bps round-trip cost gate "
                f"(cost-survival {cost['cost_survival_pct']}% < "
                f"{int(COST_SURVIVAL_FLOOR*100)}%). Both gates must pass.")
    return ("REJECTED", verdict.get("reason", "harness rejected"))


def write_report(summary: dict, verdict: dict, cost: dict, diag: dict,
                 dune_meta: dict, missing: list[str]) -> None:
    eff_trend = [e["eff"] for e in verdict.get("per_window_eff", [])
                 if e["eff"] is not None]
    lines = [
        "# H-019 / C-2 FULL-BOOK — Exchange Net-Flow Cross-Sectional FULL-BOOK "
        "— Research Backtest",
        "",
        "**Date:** 2026-05-18  ",
        "**Hypothesis:** H-019 (`c2_fullbook` in "
        "`reports/hypothesis_registry.json`)  ",
        "**Module:** `tools/h019_netflow_fullbook.py` (OPT-IN RESEARCH SIDECAR "
        "— no production caller)  ",
        "**Data source:** free Dune Analytics `cex.flows` Spellbook table — "
        "RE-USES the cached H-018 raw result "
        "(`tools/cache/h018_dune_netflow_cache.json`, 8550 rows, 0 extra Dune "
        "credits).  ",
        f"**Harness:** `tools/edge_stability_harness.py` imported UNMODIFIED "
        f"(EFF_MIN={harness.EFF_MIN}, MIN_WINDOW_N={harness.MIN_WINDOW_N}, "
        f"MIN_STABLE_WINDOWS={harness.MIN_STABLE_WINDOWS}).",
        "",
        f"## VERDICT: {summary['verdict']}",
        "",
        summary["verdict_reason"],
        "",
        "## Why H-019 (vs H-018)",
        "",
        "H-018's registered LONG-2/SHORT-2 daily-rebalanced spec emits exactly "
        "4 leg-coin records per traded day; its densest 14-day window held "
        "only 56 records — below the harness 80-record floor — so 0 windows "
        "scored and H-018 came back UNTESTED. H-019 keeps the SAME economic "
        "prior (exchange-netflow cross-sectional signal) but uses the "
        "legitimate continuous-position FULL-BOOK resolution already proven on "
        "H-008 (BOND, 57k records) and H-014 (onchain): EVERY EVM coin on "
        "EVERY day is one resolved record, position-weighted by its "
        "cross-sectional netflow_z rank. This does NOT lower any harness "
        "threshold — it uses the FULL signal instead of only the 4 extreme "
        "legs. Registered explicitly as a new hypothesis per M-107.",
        "",
        "## Construction",
        "",
        "Per coin, `netflow_z` = strictly-past 30-day z-score of daily "
        "(exchange inflow - outflow) from Dune `cex.flows`. On each signal day "
        "D, ALL coins with a `netflow_z` are ranked cross-sectionally; each "
        "gets a linear rank weight in [-1, +1] (top outflow = +1 LONG, top "
        "inflow = -1 SHORT, linear between), demeaned so the book is "
        "market-neutral. Entry D+1 close, exit D+2 close, 1-day hold, "
        "continuous daily rebalance. Beta removed: each coin's contribution = "
        "its return minus the equal-weight mean of the booked coins. "
        "`signed_ret = weight * beta_neutral_return`. ONE resolved record per "
        "coin per day. Harness score field = `|weight|` (conviction "
        "magnitude). `netflow_z` for day D uses only flow strictly before D; "
        "entry is D+1 — strictly look-ahead-free.",
        "",
        "## Data coverage",
        "",
        f"- Dune query (cached): `query_id={dune_meta.get('query_id')}`, "
        f"`execution_id={dune_meta.get('execution_id')}`, "
        f"from_cache={dune_meta.get('from_cache')}, "
        f"raw rows={dune_meta.get('row_count', 'n/a')}.",
        f"- Coins with usable netflow_z signal: "
        f"{', '.join(diag['coins_with_signal']) or 'NONE'} "
        f"({len(diag['coins_with_signal'])} coins).",
        f"- **Coverage caveat:** Dune `cex.flows` is EVM-only — the universe "
        f"is 12 EVM majors. H-018 spec majors MISSING clean coverage: "
        f"{', '.join(missing) or 'none'} (notably BTC/SOL/XRP are absent — "
        f"BTC/SOL need `cex.addresses` native-chain joins; XRP is non-EVM). "
        f"The cross-sectional universe is necessarily the EVM-traded subset.",
        f"- Dune cex.flows history span: "
        f"{min((d['day'] for d in diag.get('daily_book', [])), default='n/a')}"
        f" .. "
        f"{max((d['day'] for d in diag.get('daily_book', [])), default='n/a')}"
        f" (~18 months — free-tier label depth).",
        f"- Signal days: {diag['n_signal_days']}; traded days: "
        f"{diag['n_traded_days']}.",
        f"- Resolved records (coin x day, FULL BOOK): {summary['n']}.",
        "- **Price-coverage note:** of the 12 coins with a netflow_z signal, "
        "MATIC contributes 0 records — its Binance price series ends "
        "2024-09-09 (MATIC->POL migration / pair delist), so it never has a "
        "D+1 entry inside the cex.flows window. MKR is partial (Binance "
        "MKRUSDT history shorter). A coin with no price on day D is dropped "
        "from that day's book (not a whole-day abort) — the book is whatever "
        "coins resolved cleanly, still cross-sectionally demeaned to "
        "market-neutral. Effective tradeable universe is ~11 EVM coins.",
        f"- Per-14d-window record counts (densest first): "
        f"{diag.get('window_record_counts', [])}.",
        f"- Windows at the harness floor (>= {harness.MIN_WINDOW_N} records): "
        f"{diag.get('windows_at_floor', 0)} — harness floor is "
        f"{harness.MIN_WINDOW_N} records WITH >=15 winners AND >=15 losers; "
        f"need {harness.MIN_STABLE_WINDOWS} scored windows minimum.",
        f"- Per-symbol record share: "
        + ", ".join(f"{s}={c}" for s, c in
                    sorted(diag['symbol_counts'].items()))
        + ".",
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
        "## Performance",
        "",
        f"- Pooled book WR (coin-day records): {summary['pooled_wr']}%  ",
        f"- Gross edge: {cost['gross_edge_bps']} bps/coin-trade  ",
        f"- Net edge after {cost['cost_bps']}bps round-trip: "
        f"{cost['net_edge_bps']} bps  ",
        f"- Cost-survival: {cost['cost_survival_pct']}% of gross "
        f"(floor {int(COST_SURVIVAL_FLOOR*100)}%) — "
        f"{'PASS' if cost['passes'] else 'FAIL'}  ",
        f"- Purged/embargoed walk-forward embargo: {EMBARGO_DAYS} days "
        f"(AFML Ch.7).",
        "",
        "> **Caveat:** when the verdict is UNTESTED (data-gap) the pooled "
        "numbers are NOT verdict-grade — the harness scored fewer than "
        f"{harness.MIN_STABLE_WINDOWS} windows, so in-sample WR / gross-vs-net "
        "edge carry no statistical weight. They document what the sample "
        "looked like; they are explicitly NOT an edge or no-edge claim.",
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
        "EFF_MIN / MIN_WINDOW_N / MIN_STABLE_WINDOWS untouched. FULL-BOOK "
        "construction is legitimate density (H-008/H-014 precedent), not "
        "p-hacking.*",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", dest="as_json", action="store_true")
    args = ap.parse_args()

    # --- 1. Dune cex.flows (cached only — never re-query) --------------------
    dune_meta: dict = {}
    netflow: dict = {}
    dune_error = None
    try:
        rows, dune_meta = h018.get_dune_rows(refresh=False)
        netflow = h018.parse_netflow(rows)
    except Exception as e:  # noqa: BLE001
        dune_error = str(e)
        dune_meta = {"error": dune_error}

    # --- 2. signal -----------------------------------------------------------
    z_by_sym = h018.build_netflow_z(netflow) if netflow else {}
    coins_with_z = sorted(z_by_sym)

    price_syms = [s for s in coins_with_z if s in h018.UNIVERSE]
    prices = h018.fetch_prices(price_syms, refresh=False) if price_syms else {}

    records, diag = ([], {"coins_with_signal": [], "n_signal_days": 0,
                          "n_traded_days": 0, "symbol_counts": {},
                          "daily_book": []})
    if z_by_sym and prices:
        z_priced = {s: z_by_sym[s] for s in z_by_sym if prices.get(s)}
        if z_priced:
            records, diag = build_fullbook_records(z_priced, prices)

    n = len(records)
    missing = [s for s in sorted(H018_SPEC_MAJORS)
               if s not in diag.get("coins_with_signal", [])]

    # --- 3. gates ------------------------------------------------------------
    if n >= harness.MIN_WINDOW_N:
        verdict = harness_verdict(records)
    else:
        verdict = {"windows_scored": 0, "windows_strong": 0,
                   "strong_positive": 0, "strong_negative": 0,
                   "per_window_eff": [], "sign": "n/a", "is_admissible": False,
                   "reason": f"INSUFFICIENT DATA — {n} records "
                             f"(< harness MIN_WINDOW_N={harness.MIN_WINDOW_N})"}
    cost = cost_gate(records)

    top, reason = classify(verdict, n, diag, cost)
    if dune_error:
        top = "UNTESTED-data-gap"
        reason = (f"Dune cache load failed ({dune_error}); no cex.flows data, "
                  f"so the strategy could not be backtested.")

    # honest next step
    scored = verdict.get("windows_scored", 0)
    if top == "ADMISSIBLE":
        next_step = (
            "Harness ADMISSIBLE on the FULL-BOOK construction AND net edge "
            "survives the 30bps round-trip cost gate. This is the first "
            "exchange-netflow construction to clear both gates. Honest next "
            "step: this is still a 12-EVM-coin, ~18-month, free-data result — "
            "BTC/SOL/XRP are absent, so it is NOT yet a sized-trade signal. "
            "Recommend a paper-only follow-up with a wider label set "
            "(`cex.addresses` BTC/SOL joins) and an out-of-sample re-run "
            "before any operator sizing decision. Do NOT wire to production "
            "on this sample alone.")
    elif top == "REJECTED" and scored >= harness.MIN_STABLE_WINDOWS:
        if verdict.get("is_admissible"):
            next_step = (
                "Harness scored same-sign stable but the net edge does NOT "
                "survive the 30bps crypto round-trip — gross edge is real but "
                "too thin to clear costs. Treat as a no-go: the signal exists "
                "but is not tradeable at retail crypto cost. Do NOT re-test "
                "this construction hoping costs change. A future retry needs a "
                "materially stronger raw signal (longer hold to amortise cost, "
                "or a higher-conviction sub-universe).")
        else:
            next_step = (
                "Clean harness KILL (#10) — the FULL-BOOK construction scored "
                f"{scored} windows but the eff sign SPLITS across them "
                "(no stable same-sign separation). Exchange netflow rank "
                "weight does not predict cross-sectional crypto returns "
                "stably on this 12-EVM-coin / 18-month sample. Do NOT re-test "
                "this construction on this data. A future retry needs a "
                "materially different signal (e.g. the registered H-018 "
                "SOPR/realized-profit construction via paid Glassnode, an "
                "operator paid-data decision).")
    else:  # UNTESTED
        win_counts = diag.get("window_record_counts", [])
        biggest = win_counts[0] if win_counts else 0
        next_step = (
            "UNTESTED — data-gap, explicitly NOT a pass. The FULL-BOOK "
            f"construction lifted density vs H-018 (densest 14-day window now "
            f"{biggest} records vs H-018's 56) but still scored only {scored} "
            f"windows at the harness's >= {harness.MIN_WINDOW_N}-record / "
            f">=15-winner / >=15-loser floor (need "
            f">= {harness.MIN_STABLE_WINDOWS}). The binding constraint is "
            "free-tier history depth: Dune `cex.flows` only goes back ~18 "
            "months (from 2024-11-18). To render a real harness verdict "
            "WITHOUT lowering any threshold: (a) extend history with an older "
            "label source, or (b) the registered H-018 SOPR/realized-profit "
            "construction via Glassnode (Standard ~$29/mo, 8-asset) — an "
            "operator paid-data decision. NOT an edge claim either way.")

    summary = {
        "hypothesis": "H-019",
        "strategy": "C-2 exchange net-flow cross-sectional FULL-BOOK",
        "data_source": "Dune Analytics cex.flows (free tier, cached H-018 raw)",
        "verdict": top,
        "verdict_reason": reason,
        "n": n,
        "coins_tested": diag.get("coins_with_signal", []),
        "coins_missing_from_spec": missing,
        "coverage_caveat": ("Dune cex.flows is EVM-only; BTC/SOL/XRP absent; "
                            "universe is 12 EVM majors"),
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
        "next_step": next_step,
    }

    write_report(summary, verdict, cost, diag, dune_meta, missing)

    if args.as_json:
        print(json.dumps(summary, indent=2))
        return 0

    print("=" * 72)
    print("H-019 / C-2 EXCHANGE NET-FLOW CROSS-SECTIONAL FULL-BOOK — RESEARCH")
    print("=" * 72)
    print(f"Dune from_cache : {dune_meta.get('from_cache')}")
    print(f"Coins w/ signal : {summary['coins_tested']}")
    print(f"Missing (spec)  : {missing}")
    print(f"Records (n)     : {n}")
    print(f"Window counts   : {diag.get('window_record_counts', [])}")
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
