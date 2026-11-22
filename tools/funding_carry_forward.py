"""Forward pod for the funding carry, with kill criteria written BEFORE the first observation.

H-228's problem was never the measurement — three desks reproduced it to three significant
figures. It was that the verdict sat inside a cost assumption nobody had measured. That cost
is now measured (42.64 bp round trip, 94% fees) and the answer is unfavourable at retail taker
fees, so the cell is deliberately at 0% allocation.

This pod exists for one reason: to accumulate FORWARD observations under a cost model that
states its holding period up front, so the next verdict is not another backtest. It does not
re-score H-228's history — that data is already spent, and re-running it would be the
retrofitting this programme exists to prevent. H-229 is a re-specification with a new clock.

FROZEN SPEC (do not edit after the first observation)
  signal      equal-weight delta-neutral spot/perp carry over BTC, ETH, BNB, SOL, XRP
  return      that day's summed funding per coin, averaged across coins, in bp/day
  cost        round trip / holding_days, holding floor 60 days, round trip 42.64 bp measured
  re-hedge    0.072 bp/day (5% drift band, measured on live books)
  benchmark   a 3.5% T-bill (the reader's cash alternative), not BTC buy-and-hold:
              the question is whether carry beats CASH, which is what it competes with
  judgment    none before min_n=20 days AND min_hold=60 days. A green series at n=6 is noise.

KILL CRITERIA (any one is sufficient; evaluated only once the judgment gate opens)
  K1 net CI-LB <= 0 at the pre-registered cost
  K2 realised second-half mean < 60% of the first half (the 46% decay accelerating)
  K3 realised round trip > 2x modelled (>85.28 bp) — execution, not the signal, has failed
  K4 pledged-collateral yield unavailable AND net < the T-bill hurdle
  K5 any single observation < -400 bp (outside the in-sample worst of -362.44) -> REVIEW flag.
     Recorded ALONGSIDE whatever K1-K3 say; it does not shield the pod from them. A print
     outside the in-sample worst is a reason to look, never a reason to relax a gate.

SIZING vs KILLING, kept separate on purpose
  Net below the T-bill hurdle means "do not size this". It is not a kill: K4 additionally
  requires the pledged-collateral fact, which nobody has measured. Collapsing the two would
  let an unmeasured question kill a hypothesis, or let a real kill hide behind a sizing note.

Usage
  python3 tools/funding_carry_forward.py --run      # append any missing days since inception
  python3 tools/funding_carry_forward.py --status   # gate + kill criteria on what exists
  python3 tools/funding_carry_forward.py --probe    # convention check vs the cached series
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HISTORY = ROOT / "data" / "funding_carry_forward.jsonl"
SPEC_PATH = ROOT / "reports" / "forward_pod_carry_h229.json"
CACHE = ROOT / "reports" / "funding_carry" / "funding_cache.json"

POD_ID = "POD-CRYPTO-CARRY-H229"
INCEPTION = "2026-11-22"
COINS = ("BTC/USDT:USDT", "ETH/USDT:USDT", "BNB/USDT:USDT", "SOL/USDT:USDT", "XRP/USDT:USDT")

SPEC = {
    "pod_id": POD_ID,
    "hypothesis_id": "H-229",
    "asset_class": "CRYPTO",
    "inception": INCEPTION,
    "frozen": True,
    "signal": "equal-weight delta-neutral spot/perp funding carry, 5 coins",
    "return_definition": "daily summed funding per coin, averaged across coins, bp/day",
    "cost_model": {
        "roundtrip_bp": 42.64,
        "fee_share_of_roundtrip": 0.94,
        "holding_floor_days": 60,
        "rehedge_bp_day": 0.072,
        "source": "mercury3 carry_execution_cost.py (live books) + tools/venue_rebalance_cost.py",
    },
    "benchmark": {"name": "T-bill", "rate_pct": 3.5,
                  "why": "carry competes with cash, not with BTC beta"},
    "judgment_gate": {"min_n_days": 20, "min_hold_days": 60,
                      "rule": "no verdict of any kind before both are met"},
    "kill_criteria": {
        "K1": "net CI-LB <= 0 at the pre-registered cost",
        "K2": "realised second-half mean < 60% of the first half",
        "K3": "realised round trip > 2x modelled (>85.28 bp)",
        "K4": "pledged-collateral yield unavailable AND net < T-bill hurdle",
        "K5": "any single observation < -400 bp -> REVIEW, not auto-kill",
    },
    "known_limitations": [
        "one exchange, one venue, no counterparty-risk price",
        "cost is a single measured snapshot treated as a floor; stress widens it",
        "a 60-day floor means the first judgment is impossible before ~2027-01-21",
    ],
}


def load_rows() -> list[dict]:
    if not HISTORY.exists():
        return []
    return [json.loads(line) for line in HISTORY.read_text().splitlines() if line.strip()]


def fetch_daily(since_day: str) -> dict[str, float]:
    """Mean-across-coins daily funding in bp, for every complete UTC day >= since_day."""
    import ccxt
    ex = ccxt.binance({"enableRateLimit": True, "timeout": 25000})
    since = int(time.mktime(time.strptime(since_day, "%Y-%m-%d")) * 1000)
    per_coin: dict[str, dict[str, float]] = {}
    for sym in COINS:
        try:
            hist = ex.fetch_funding_rate_history(sym, since=since, limit=1000)
        except Exception as e:  # noqa: BLE001
            print(f"  {sym}: {type(e).__name__}: {str(e)[:120]}")
            continue
        days: dict[str, float] = {}
        for h in hist:
            d = time.strftime("%Y-%m-%d", time.gmtime(h["timestamp"] / 1000))
            days[d] = days.get(d, 0.0) + float(h["fundingRate"]) * 1e4
        per_coin[sym] = days
    if not per_coin:
        return {}
    # only complete days present for every coin
    common = set.intersection(*(set(v) for v in per_coin.values()))
    today = time.strftime("%Y-%m-%d", time.gmtime())
    return {d: sum(per_coin[s][d] for s in per_coin) / len(per_coin)
            for d in sorted(common) if d < today}


def boot_ci_lb(xs: list[float], n: int = 2000, block: int = 5, seed: int = 11) -> float:
    """Block bootstrap lower bound of the mean; 0.0 when there is not enough history."""
    if len(xs) < 12:
        return 0.0
    import random
    rnd = random.Random(seed)
    L, out = len(xs), []
    for _ in range(n):
        acc, got = 0.0, 0
        while got < L:
            s = rnd.randrange(L)
            for k in range(block):
                acc += xs[(s + k) % L]
                got += 1
                if got >= L:
                    break
        out.append(acc / L)
    out.sort()
    return out[int(0.025 * n)]


def evaluate(rows: list[dict], spec: dict = SPEC) -> dict:
    """Gate + kill criteria. Pure function so it can be tested offline."""
    n = len(rows)
    gate = spec["judgment_gate"]
    vals = [r["mean_bp"] for r in rows]
    res = {"n_days": n, "gated": True, "verdict": f"no_judgment: n={n}", "triggered": []}
    if n:
        res["cumulative_bp"] = round(sum(vals), 2)
        res["ann_pct"] = round(sum(vals) / n * 365 / 100.0, 3)
        res["worst_day_bp"] = round(min(vals), 2)
        if min(vals) < -400:
            res["triggered"].append("K5")
    if n < gate["min_n_days"]:
        return res
    # days since inception, not row count, decides the holding floor
    res["gated"] = False
    ci_lo = boot_ci_lb(vals)
    cost = spec["cost_model"]
    drag = cost["roundtrip_bp"] / max(1, n) + cost["rehedge_bp_day"]
    net_lo = ci_lo - drag
    res.update({"ci_lb_bp": round(ci_lo, 4), "drag_bp_day": round(drag, 4),
                "net_ci_lb_bp": round(net_lo, 4)})
    if net_lo <= 0:
        res["triggered"].append("K1")
    half = n // 2
    if half:
        h1 = statistics.mean(vals[:half])
        h2 = statistics.mean(vals[half:])
        res["halves_bp"] = [round(h1, 3), round(h2, 3)]
        if h1 > 0 and h2 < 0.6 * h1:
            res["triggered"].append("K2")
    hurdle = spec["benchmark"]["rate_pct"] / 365 * 100.0
    res["beats_cash"] = (sum(vals) / n - drag) > hurdle
    if not res["beats_cash"]:
        # a sizing statement, deliberately NOT a trigger: K4 also needs the
        # pledged-collateral fact, and an unmeasured condition cannot kill anything
        res["sizing_note"] = ("net is below the T-bill hurdle, so this may not be sized. "
                              "K4 additionally requires the pledged-collateral fact, which "
                              "is unmeasured; see the break-even table.")
    res["verdict"] = "KILL" if any(t in ("K1", "K2", "K3") for t in res["triggered"]) else "ALIVE"
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--cache", default=str(CACHE),
                    help="path to the cached daily funding series used by the probe")
    a = ap.parse_args()

    if a.probe:
        # convention check: does summing settlements reproduce the cached daily series?
        cache = json.loads(Path(a.cache).read_text())
        coin = COINS[0]
        dates = sorted(cache[coin])[-5:]
        fresh = fetch_daily(dates[0])
        print("date        cache_bp   ccxt_sum_bp   ratio")
        for d in dates:
            c = cache[coin].get(d)
            f = fresh.get(d)
            if c is None or f is None:
                print(f"{d}  missing cache={c} ccxt={f}")
                continue
            print(f"{d}  {c*1e4:9.4f}   {f:9.4f}   {(f/(c*1e4) if c else float('nan')):.2f}")
        return

    if a.run:
        SPEC_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not SPEC_PATH.exists():
            SPEC_PATH.write_text(json.dumps(SPEC, indent=2) + "\n")
            print(f"wrote frozen spec {SPEC_PATH}")
        rows = load_rows()
        have = {r["date"] for r in rows}
        since = max([r["date"] for r in rows], default=INCEPTION)
        fresh = fetch_daily(since)
        added = 0
        HISTORY.parent.mkdir(parents=True, exist_ok=True)
        with HISTORY.open("a") as fh:
            for d, v in fresh.items():
                if d in have or d < INCEPTION:
                    continue
                fh.write(json.dumps({"date": d, "mean_bp": round(v, 6),
                                     "pod_id": POD_ID}) + "\n")
                added += 1
        print(f"appended {added} day(s); total {len(load_rows())} (inception {INCEPTION})")

    rows = load_rows()
    res = evaluate(rows)
    print(f"\n{POD_ID}  n_days={res['n_days']}  gated={res['gated']}  verdict={res['verdict']}")
    for k in ("cumulative_bp", "ann_pct", "worst_day_bp", "ci_lb_bp", "net_ci_lb_bp",
              "beats_cash", "halves_bp"):
        if k in res:
            print(f"  {k}: {res[k]}")
    if res["triggered"]:
        print(f"  triggered: {res['triggered']}")
    if res["gated"]:
        print(f"  GATE: no verdict before n>={SPEC['judgment_gate']['min_n_days']} days "
              f"and a {SPEC['judgment_gate']['min_hold_days']}-day hold. This is deliberate.")


if __name__ == "__main__":
    main()
