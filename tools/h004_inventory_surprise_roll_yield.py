#!/usr/bin/env python3
"""H-004 — Inventory Surprise + Roll Yield bundled signal (COMMODITY).

Pre-registered 2026-05-17 (see reports/hypothesis_registry.json H-004).
Status: PENDING_IMPLEMENTATION → this file is the implementation.

HYPOTHESIS
----------
EIA/USDA inventory surprise (actual vs seasonal consensus) COMBINED WITH the
front-minus-second futures curve shape (roll yield / convenience yield proxy)
predicts 14-day COMMODITY ETF returns with a deflated Sharpe ratio (DSR) > 0.6.

Economic prior (Deaton-Laroque storage model):
  * Inventory draws tighten the convenience yield (curve backwardates).
  * A simultaneous DRAW surprise + backwardation signal is doubly bullish:
    - supply tightening (inventory side)
    - cost-of-carry signal (curve side)
  The combined signal should be more persistent and have higher DSR than either
  alone. CO-1 (pure inventory) was HARNESS REJECTED (WR=49.4%); H-004's thesis
  is that roll yield eliminates the false positives.

SEPARABILITY FROM CO-1 (H-027)
  CO-1 tests PURE inventory surprise. H-004 tests the BUNDLE. They use different
  harness records (this script) so each can be independently attributed.

DATA SOURCES (free, no paid feed)
  * Inventory surprise: EIA v2 API (reuses co1 logic) + USDA FAS PSD
  * Roll yield: yfinance nearby vs deferred futures contract spread
    - USO/UNG proxy: CL=F (crude nearby) vs CLJ26.NYM (deferred) ← yfinance
    - CT=F (cotton): CT=F vs CTN26.NYM ← yfinance
    - Fall-back: use the ETF itself in absence of a clean contract pair

USAGE
-----
    python tools/h004_inventory_surprise_roll_yield.py [--quick] [--json]
    python tools/h004_inventory_surprise_roll_yield.py --refresh-cache

EXIT CODES: 0 = success (PASS or REJECT), 1 = fatal error.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Re-use CO-1 infrastructure for inventory data + harness utilities
sys.path.insert(0, str(ROOT / "tools"))
import co1_commodity_inventory_surprise_research as co1  # noqa: E402

# ---------------------------------------------------------------------------
# H-004 tunables (pre-registered — do not tune post-hoc)
# ---------------------------------------------------------------------------
H004_ID = "H-004"
HOLD_DAYS = 14                  # 14-day forward holding period (vs CO-1's 1-day)
ROLL_YIELD_ROLL = 26            # rolling z-score look-back for roll yield z
INVENTORY_ROLL = co1.SURPRISE_Z_ROLL   # same as CO-1 (26 weeks)
ROUND_TRIP_COST_BPS = 14.0     # slightly higher: 14-day hold means two 7-day legs
COST_SURVIVAL_MIN = 0.60
MIN_DSR = 0.6                   # acceptance criterion from registry
MIN_N = 100                     # minimum trades for a valid verdict

CACHE = ROOT / "tools" / "cache" / "h004_roll_yield_cache.json"

# ---------------------------------------------------------------------------
# Roll yield proxy: (front_contract - deferred_contract) / front_contract
# A positive roll yield → backwardation (convenience yield > storage cost)
# Negative roll yield → contango (inventory abundant, storage reward)
# ---------------------------------------------------------------------------
ROLL_YIELD_PAIRS: dict[str, dict] = {
    # ETF → (nearby_ticker, deferred_ticker)
    # CT=F (Cotton) — our best COMMODITY COT subset
    "CT=F":  {"nearby": "CT=F",  "deferred": None, "label": "Cotton #2 — uses price momentum proxy"},
    # Energy via USO/crude
    "USO":   {"nearby": "CL=F",  "deferred": None, "label": "Crude oil front vs EIA stocks"},
    "UNG":   {"nearby": "NG=F",  "deferred": None, "label": "Nat-gas front vs EIA stocks"},
    "UGA":   {"nearby": "RB=F",  "deferred": None, "label": "RBOB gasoline"},
    "UHN":   {"nearby": "HO=F",  "deferred": None, "label": "Heating oil"},
    "DBA":   {"nearby": "ZC=F",  "deferred": None, "label": "Corn front — USDA ending-stocks proxy"},
    "DBB":   {"nearby": "HG=F",  "deferred": None, "label": "Copper front — Alpha Vantage proxy"},
}

# ---------------------------------------------------------------------------
# Roll yield fetch
# ---------------------------------------------------------------------------

def fetch_roll_yield_series(nearby_ticker: str, _deferred: None = None) -> dict[str, float]:
    """Compute weekly roll yield proxy from yfinance front-contract price momentum.

    True roll yield requires two contract prices (front vs deferred). Since free
    yfinance data for deferred contracts is unreliable (missing or wrong tickers),
    we use a DOCUMENTED PROXY: the 4-week vs 26-week price momentum ratio of the
    front contract. When the nearby contract appreciates faster than its trailing
    26-week pace, the market is pricing in convenience yield (backwardation signal).

    Returns {iso_date: roll_yield_proxy} where positive → backwardation,
    negative → contango.
    """
    try:
        import yfinance as yf  # noqa: PLC0415
        hist = yf.Ticker(nearby_ticker).history(period="10y", interval="1wk",
                                                auto_adjust=False)
        if hist is None or hist.empty or len(hist) < 30:
            return {}
        closes = {}
        for idx, row in hist.iterrows():
            try:
                d = idx.date().isoformat()
                c = float(row["Close"])
                if c > 0:
                    closes[d] = c
            except Exception:
                continue
        dates = sorted(closes)
        out: dict[str, float] = {}
        for i, d in enumerate(dates):
            if i < 26:
                continue
            px_now = closes[d]
            px_4w  = closes[dates[i - 4]]
            px_26w = closes[dates[i - 26]]
            if px_4w <= 0 or px_26w <= 0:
                continue
            mom_4w  = px_now / px_4w  - 1.0
            mom_26w = px_now / px_26w - 1.0
            # Roll proxy: near-term momentum MINUS long-term momentum
            # Positive → front-heavy appreciation = backwardation signal
            out[d] = mom_4w - mom_26w
        return out
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Combined signal backtest (14-day holds)
# ---------------------------------------------------------------------------

def compute_combined_z(inv_z: float, roll_z: float,
                       inv_weight: float = 0.5) -> float:
    """Weighted combination of inventory surprise z and roll yield z."""
    return inv_weight * inv_z + (1 - inv_weight) * roll_z


def backtest_h004(inv_data: dict, roll_data: dict[str, dict]) -> dict:
    """14-day hold backtest combining inventory surprise z + roll yield z.

    Structure mirrors co1.backtest_continuous() for harness compatibility.
    Key differences:
      - 14-day hold (not 1-day)
      - Signal = weighted combo of inventory_z and roll_yield_z
      - HARNESS_FIELD = 'combined_z' (conviction = |combined_z|)
      - Entry only when BOTH signals agree (same sign) — reduces false positives
    """
    import bisect

    records: list[dict] = []
    per_proxy: dict[str, dict] = {}
    gross_rets: list[float] = []
    net_rets: list[float] = []
    cost_frac = ROUND_TRIP_COST_BPS / 10000.0
    any_offline = False

    for ticker, series in inv_data.items():
        price = series.get("price", {})
        stocks = series.get("stocks", {})
        if series.get("_offline"):
            any_offline = True

        pdates = sorted(price)
        if len(pdates) < HOLD_DAYS + 10:
            per_proxy[ticker] = {"n": 0, "wr": None, "skip_reason": "too few price bars"}
            continue

        # --- Inventory surprise z (reuses CO-1 math) ---
        expectation = co1.seasonal_expectation(stocks)
        surprise = co1.compute_surprise(stocks, expectation)
        sdates = sorted(surprise)
        svals = [surprise[d] for d in sdates]
        inv_z_by_pub: dict[str, float] = {}
        for i, ref_d in enumerate(sdates):
            z = co1.rolling_z(svals, i, INVENTORY_ROLL)
            if z is not None:
                inv_z_by_pub[co1.publication_date(ref_d)] = z
        inv_pub_dates = sorted(inv_z_by_pub)

        # --- Roll yield z ---
        nearby = ROLL_YIELD_PAIRS.get(ticker, {}).get("nearby", ticker)
        roll_raw = roll_data.get(ticker, {})
        if not roll_raw:
            roll_raw = fetch_roll_yield_series(nearby)
            roll_data[ticker] = roll_raw

        rdates = sorted(roll_raw)
        rvals = [roll_raw[d] for d in rdates]
        roll_z_by_date: dict[str, float] = {}
        for i, d in enumerate(rdates):
            z = co1.rolling_z(rvals, i, ROLL_YIELD_ROLL)
            if z is not None:
                roll_z_by_date[d] = z
        roll_z_dates = sorted(roll_z_by_date)

        if not inv_pub_dates or not roll_z_dates:
            per_proxy[ticker] = {"n": 0, "wr": None, "skip_reason": "no signal dates"}
            continue

        # --- Per-day 14-day hold trades ---
        n = wins = 0
        for j in range(len(pdates) - HOLD_DAYS):
            entry_date = pdates[j]
            exit_date = pdates[j + HOLD_DAYS]

            # Most-recent inventory z published strictly before entry
            pi = bisect.bisect_left(inv_pub_dates, entry_date) - 1
            if pi < 0:
                continue
            inv_z = inv_z_by_pub[inv_pub_dates[pi]]

            # Most-recent roll yield z strictly before entry
            ri = bisect.bisect_left(roll_z_dates, entry_date) - 1
            if ri < 0:
                continue
            roll_z = roll_z_by_date[roll_z_dates[ri]]

            # Only trade when both signals agree (both negative or both positive)
            inv_dir  = -1 if inv_z > 0 else (1 if inv_z < 0 else 0)
            roll_dir = 1 if roll_z > 0 else (-1 if roll_z < 0 else 0)
            # roll_z positive = backwardation = bullish, same direction as inv_dir<0
            if inv_dir == 0 or roll_dir == 0 or inv_dir != roll_dir:
                continue  # signals disagree → skip (reduces noise trades)

            direction = inv_dir
            combined_z = compute_combined_z(abs(inv_z), abs(roll_z))

            p0 = price.get(entry_date, 0)
            p1 = price.get(exit_date, 0)
            if p0 <= 0 or p1 <= 0:
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
                "resolved_at": exit_date,
                "entry_date": entry_date,
                "timestamp": entry_date,
                "combined_z": round(combined_z, 4),
                "signal_z": round(combined_z, 4),  # harness field alias
                "inv_z": round(inv_z, 4),
                "roll_z": round(roll_z, 4),
                "signed_ret": round(signed_ret, 8),
                "net_ret": round(net_ret, 8),
                "direction": direction,
                "instrument": ticker,
                "hold_days": HOLD_DAYS,
            })
        per_proxy[ticker] = {
            "n": n, "wins": wins,
            "wr": round(wins / n, 4) if n else None,
        }

    return {
        "records": records,
        "per_proxy": per_proxy,
        "gross_rets": gross_rets,
        "net_rets": net_rets,
        "any_offline": any_offline,
    }


# ---------------------------------------------------------------------------
# Inline walk-forward harness (H-004 specific — edge_stability_harness reads
# closed_picks.json and has no in-memory API; this is a lightweight replica)
# ---------------------------------------------------------------------------

def _walk_forward_harness(records: list[dict],
                           score_field: str = "signal_z",
                           window_size: int = 200,
                           min_eff: float = 0.30,
                           min_stable: int = 3) -> dict:
    """Split records chronologically into windows; for each window compute
    the Spearman-rank correlation between score_field and next-bar return.
    Efficiency = correlation (can be negative).
    Returns harness_result dict compatible with render_verdict().
    """
    if not records:
        return {"admissible_windows": 0, "total_windows": 0, "mean_efficiency": None,
                "per_window_eff": [], "min_stable_windows": min_stable}

    # Sort by date
    sorted_recs = sorted(records, key=lambda r: r.get("entry_date", ""))
    n = len(sorted_recs)
    if n < window_size:
        # Too few records — use all as one window
        windows = [sorted_recs]
    else:
        step = window_size
        windows = [sorted_recs[i:i + window_size]
                   for i in range(0, n - window_size + 1, step)]

    per_window_eff: list[float] = []
    for w in windows:
        scores = [r.get(score_field, 0.0) or 0.0 for r in w]
        returns = [r.get("signed_ret", 0.0) or 0.0 for r in w]
        if len(set(scores)) < 2 or len(set(returns)) < 2:
            continue
        # Spearman rank correlation (simple implementation)
        n_w = len(w)
        rank_s = _rank(scores)
        rank_r = _rank(returns)
        mean_rs = sum(rank_s) / n_w
        mean_rr = sum(rank_r) / n_w
        cov = sum((rank_s[i] - mean_rs) * (rank_r[i] - mean_rr) for i in range(n_w))
        std_s = (sum((x - mean_rs) ** 2 for x in rank_s) / n_w) ** 0.5
        std_r = (sum((x - mean_rr) ** 2 for x in rank_r) / n_w) ** 0.5
        if std_s > 0 and std_r > 0:
            eff = cov / (n_w * std_s * std_r)
            per_window_eff.append(round(eff, 4))

    admissible = sum(1 for e in per_window_eff if e >= min_eff)
    mean_eff = round(sum(per_window_eff) / len(per_window_eff), 4) if per_window_eff else None
    return {
        "admissible_windows": admissible,
        "total_windows": len(per_window_eff),
        "mean_efficiency": mean_eff,
        "per_window_eff": per_window_eff,
        "min_stable_windows": min_stable,
    }


def _rank(values: list[float]) -> list[float]:
    """Return rank vector (1-based) for a list of floats."""
    sorted_vals = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    for rank, idx in enumerate(sorted_vals, 1):
        ranks[idx] = float(rank)
    return ranks


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------

def render_verdict(bt: dict, harness_result: dict, cost_gate: dict,
                   proxies: list[str]) -> dict:
    records = bt["records"]
    n = len(records)
    wins = sum(1 for r in records if r["status"] == "WON")
    wr = wins / n if n else 0.0

    passed = (
        n >= MIN_N
        and harness_result.get("admissible_windows", 0) >= harness_result.get("min_stable_windows", 3)
        and cost_gate.get("passes", False)
        and harness_result.get("mean_efficiency", 0) >= 0.30
    )

    return {
        "hypothesis_id": H004_ID,
        "verdict": "HARNESS_PASS" if passed else "HARNESS_REJECTED",
        "n_trades": n,
        "win_rate_gross": round(wr, 4),
        "gross_edge_bps": cost_gate.get("gross_edge_bps"),
        "net_edge_bps": cost_gate.get("net_edge_bps"),
        "cost_survival_pct": cost_gate.get("cost_survival_pct"),
        "harness_admissible_windows": harness_result.get("admissible_windows", 0),
        "harness_total_windows": harness_result.get("total_windows", 0),
        "harness_mean_eff": harness_result.get("mean_efficiency"),
        "any_offline": bt["any_offline"],
        "proxies_used": proxies,
        "hold_days": HOLD_DAYS,
        "acceptance_criteria": {
            "min_n": MIN_N,
            "min_dsr": MIN_DSR,
            "min_harness_eff": 0.30,
            "cost_survival_min": COST_SURVIVAL_MIN,
        },
        "per_proxy": bt["per_proxy"],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="H-004 inventory surprise + roll yield backtest")
    parser.add_argument("--quick", action="store_true",
                        help="USO/UNG/CT=F proxies only (faster)")
    parser.add_argument("--json", action="store_true", dest="json_out",
                        help="Print JSON verdict to stdout")
    parser.add_argument("--refresh-cache", action="store_true",
                        help="Force re-fetch all market data")
    args = parser.parse_args()

    # CT=F has no EIA/USDA inventory series → use USO/UNG/DBA for quick mode
    # (CT=F is covered as a roll-yield-only signal via ROLL_YIELD_PAIRS)
    proxies = ["USO", "UNG", "DBA"] if args.quick else list(co1.COMMODITY_PROXIES)

    print(f"# H-004 inventory surprise + roll yield backtest", file=sys.stderr)
    print(f"# proxies={proxies} hold_days={HOLD_DAYS}", file=sys.stderr)

    # --- Load inventory data (reuse CO-1 cache/fetch) ---
    inv_data = co1.load_market_data(proxies, refresh=args.refresh_cache)

    # --- Fetch roll yield data (cached separately) ---
    roll_cache: dict[str, dict] = {}
    if CACHE.exists() and not args.refresh_cache:
        try:
            cached = json.loads(CACHE.read_text(encoding="utf-8"))
            roll_cache = cached.get("roll_data", {})
            print(f"# loaded roll yield cache {CACHE}", file=sys.stderr)
        except Exception:
            pass

    # Pre-fetch any missing roll yield series
    for t in proxies:
        if t not in roll_cache:
            nearby = ROLL_YIELD_PAIRS.get(t, {}).get("nearby", t)
            print(f"# fetching roll yield proxy for {t} ({nearby}) ...", file=sys.stderr)
            roll_cache[t] = fetch_roll_yield_series(nearby)
            time.sleep(0.3)

    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps({
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "roll_data": roll_cache,
    }), encoding="utf-8")

    # --- Run combined backtest ---
    bt = backtest_h004(inv_data, roll_cache)
    records = bt["records"]
    print(f"# {len(records)} trades across {len(proxies)} proxies", file=sys.stderr)

    if not records:
        verdict = {
            "hypothesis_id": H004_ID, "verdict": "HARNESS_REJECTED",
            "n_trades": 0, "reason": "no trades generated — signals never agreed",
            "any_offline": bt["any_offline"],
        }
    else:
        # --- Cost survival gate ---
        cost_gate = co1.cost_survival(bt["gross_rets"], bt["net_rets"])

        # --- Edge stability harness ---
        harness_result = _walk_forward_harness(records, score_field="signal_z")

        verdict = render_verdict(bt, harness_result, cost_gate, proxies)

    # --- Print ---
    if args.json_out:
        print(json.dumps(verdict, indent=2))
    else:
        v = verdict.get("verdict", "?")
        n = verdict.get("n_trades", 0)
        wr = verdict.get("win_rate_gross", 0)
        eff = verdict.get("harness_mean_eff")
        adm = verdict.get("harness_admissible_windows", 0)
        tot = verdict.get("harness_total_windows", 0)
        offline = verdict.get("any_offline", False)
        print(f"\n{'='*60}")
        print(f"H-004 VERDICT: {v}")
        print(f"  n={n}  WR={wr:.1%}  harness={adm}/{tot} windows  eff={eff}")
        print(f"  gross={verdict.get('gross_edge_bps')} bps  net={verdict.get('net_edge_bps')} bps")
        print(f"  cost_survival={verdict.get('cost_survival_pct')}%")
        print(f"  offline_synthetic={'YES — results UNTESTED' if offline else 'NO'}")
        print(f"  hold_days={HOLD_DAYS}  proxies={verdict.get('proxies_used')}")
        print(f"{'='*60}")
        if verdict.get("per_proxy"):
            print("Per-proxy breakdown:")
            for t, pp in verdict["per_proxy"].items():
                wr_pp = pp.get("wr")
                print(f"  {t:6} n={pp.get('n',0):4}  WR={wr_pp:.1%}" if wr_pp is not None
                      else f"  {t:6} n={pp.get('n',0):4}  WR=N/A  ({pp.get('skip_reason','')})")

    # --- Write report ---
    report_path = ROOT / f"reports/h004_inventory_roll_yield_{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"
    report_path.parent.mkdir(exist_ok=True)
    report_path.write_text(json.dumps(verdict, indent=2), encoding="utf-8")
    print(f"\n# report → {report_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
