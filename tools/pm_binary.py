#!/usr/bin/env python3
"""
pm_binary.py — the PREDICTION asset class: binary contract settlement + calibration.

Why this is a separate module and not a row in sim_path_forward.py
------------------------------------------------------------------
A prediction-market contract is not a price series. It costs p in [0,1], pays exactly 1
or 0 at settlement, and cannot be marked to market once the market closes. The sim engine's
monthly/daily return loop cannot represent "pays 1 or 0" without inventing fills. So the
class gets its own settlement resolver and its own calibration statistics, and its trial
family is counted separately from the N=8 price-series registry (mixing the two would
corrupt the deflated-Sharpe trial variance).

What it does
------------
  settle   : turn a binary pick into a realized PnL once the outcome is known
  calibrate: Brier score, log loss, reliability bins, ECE over (predicted_p, outcome)
  fetch    : try to build a calibration sample from Polymarket settled markets, and
             report coverage honestly if price history is unavailable
  selftest : prove the fee/spread/calibration math against hand-computed values

Settlement conventions (fixed before seeing results)
----------------------------------------------------
* side is YES or NO. payout = 1.0 if side == outcome else 0.0.
* cost = entry_price * qty (entry_price is the price PAID for that side, in [0,1]).
* fee: Polymarket charges no protocol fee on trades, so fee_bps defaults to 0; the real
  cost is the spread, which is why entry_price should be the price actually crossed.
  Kalshi charges 0.07 * p * (1-p) per contract, rounded up to the next cent per order.
* return is on capital at risk: (payout*qty - fee - cost) / cost. A YES bought at 0.30
  that settles YES returns +233.3%; one that settles NO returns -100.0%. Asymmetry is
  the point of the class and it is preserved, never averaged away.
"""
import json, math, os, sys, argparse, time
from datetime import datetime, timezone

OUT = "reports/pm_calibration.json"
LEDGER = "state/pm_binary/settled.jsonl"
GAMMA = "https://gamma-api.polymarket.com/markets"
CLOB = "https://clob.polymarket.com/prices-history"
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) research"}

# Trial family for the deflated Sharpe. Two rules are pre-registered here: fade the
# longshot (buy YES under 0.10) and follow the favourite (buy YES over 0.90). Nothing
# else may be added without re-registering N.
PM_STRATEGIES = [
    ("PM_LONGSHOT_FADE", "buy NO when YES trades below 0.10"),
    ("PM_FAVOURITE",     "buy YES when YES trades above 0.90"),
]


# ---------------- settlement ----------------
def kalshi_fee(price, qty=1.0):
    """0.07 * p * (1-p) per contract, rounded UP to the cent for the whole order."""
    return math.ceil(0.07 * price * (1.0 - price) * qty * 100.0) / 100.0


def settle(side, entry_price, outcome, qty=1.0, venue="polymarket", fee_bps=None):
    """Settle one binary contract. side/outcome in {yes, no}. outcome=None => still open."""
    side = str(side).strip().lower()
    if side not in ("yes", "no"):
        raise ValueError(f"side must be yes/no, got {side!r}")
    if not (0.0 <= float(entry_price) <= 1.0):
        raise ValueError(f"entry_price must be within [0,1], got {entry_price!r}")
    cost = float(entry_price) * qty
    if outcome is None:
        return {"status": "open", "cost": round(cost, 6), "payout": None,
                "fee": None, "pnl": None, "ret_pct": None}
    out = str(outcome).strip().lower()
    if out not in ("yes", "no"):
        raise ValueError(f"outcome must be yes/no, got {outcome!r}")
    payout = qty if side == out else 0.0
    if fee_bps is None:
        fee = kalshi_fee(float(entry_price), qty) if venue == "kalshi" else 0.0
    else:
        fee = cost * float(fee_bps) / 10000.0
    pnl = payout - fee - cost
    return {"status": "settled", "side": side, "outcome": out, "cost": round(cost, 6),
            "payout": round(payout, 6), "fee": round(fee, 6), "pnl": round(pnl, 6),
            # capital at risk is the premium, so return is on premium: -100% is a total loss
            "ret_pct": round(100.0 * pnl / cost, 4) if cost > 0 else None}


# ---------------- calibration ----------------
def brier(pairs):
    """pairs = [(p_yes, outcome_01)]. Lower is better; 0.25 = always saying 0.5."""
    if not pairs:
        return None
    return sum((p - y) ** 2 for p, y in pairs) / len(pairs)


def log_loss(pairs, eps=1e-9):
    if not pairs:
        return None
    tot = 0.0
    for p, y in pairs:
        q = min(max(p, eps), 1 - eps)
        tot += -(y * math.log(q) + (1 - y) * math.log(1 - q))
    return tot / len(pairs)


def reliability(pairs, bins=10):
    """Equal-count-free fixed-width bins: mean predicted vs realised frequency."""
    out = []
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        sel = [(p, y) for p, y in pairs if (lo <= p < hi) or (b == bins - 1 and p == 1.0)]
        if not sel:
            continue
        out.append({"bin": f"{lo:.1f}-{hi:.1f}", "n": len(sel),
                    "mean_pred": round(sum(p for p, _ in sel) / len(sel), 4),
                    "mean_obs": round(sum(y for _, y in sel) / len(sel), 4),
                    "gap": round(sum(y for _, y in sel) / len(sel)
                                 - sum(p for p, _ in sel) / len(sel), 4)})
    return out


def ece(pairs, bins=10):
    """Expected calibration error, weighted by bin population."""
    rel = reliability(pairs, bins)
    if not rel or not pairs:
        return None
    n = sum(r["n"] for r in rel)
    return sum(r["n"] / n * abs(r["gap"]) for r in rel)


def calibration_summary(pairs):
    if not pairs:
        return {"status": "NOT MEASURED", "n": 0,
                "reason": "no resolved binary contracts in the sample"}
    wins = sum(y for _, y in pairs)
    # a sharp forecaster beats the base rate; report the base rate so Brier is readable
    base = wins / len(pairs)
    base_brier = sum((base - y) ** 2 for _, y in pairs) / len(pairs) if pairs else None
    return {"status": "MEASURED", "n": len(pairs),
            "brier": round(brier(pairs), 6),
            "log_loss": round(log_loss(pairs), 6),
            "ece": round(ece(pairs), 6) if ece(pairs) is not None else None,
            "base_rate": round(base, 4),
            "base_rate_brier": round(base_brier, 6),
            "skill_vs_base_rate_pct": (round(100.0 * (1 - brier(pairs) / base_brier), 2)
                                       if base_brier else None),
            "reliability": reliability(pairs)}


# ---------------- fetch ----------------
def _get(url, timeout=20):
    import requests
    return requests.get(url, headers=H, timeout=timeout).json()


def fetch_sample(limit=100, max_markets=25, fidelity=60):
    """Try to build (implied probability, outcome) pairs from settled Polymarket markets.

    Implied probability at decision time must come from the price history, not the final
    outcomePrices (which are just 0/1 and would score a perfect Brier by construction).
    If price history is unavailable the sample stays empty and the report says so."""
    markets = _get(f"{GAMMA}?closed=true&limit={limit}&order=volumeNum&ascending=false")
    tried = with_hist = 0
    pairs, per_market = [], []
    for m in markets[:max_markets]:
        toks = json.loads(m.get("clobTokenIds") or "[]")
        prices = json.loads(m.get("outcomePrices") or "[]")
        if len(toks) < 2 or len(prices) < 2:
            continue
        tried += 1
        hist = []
        for url in (f"{CLOB}?market={toks[0]}&interval=max&fidelity={fidelity}",
                    f"{CLOB}?market={toks[0]}&interval=all&fidelity={fidelity}"):
            try:
                hist = _get(url).get("history") or []
            except Exception:
                hist = []
            if hist:
                break
        if not hist:
            per_market.append({"question": m.get("question"), "volume": m.get("volumeNum"),
                               "status": "no_price_history"})
            continue
        with_hist += 1
        # YES price 7 days (or the last point) before settlement == implied probability
        end = hist[-1]["t"]
        cut = end - 7 * 86400
        at = [h for h in hist if h["t"] <= cut] or hist[:1]
        p_yes = float(at[-1]["p"])
        outcome = 1 if float(prices[0]) > 0.5 else 0
        pairs.append((p_yes, outcome))
        per_market.append({"question": m.get("question"), "volume": m.get("volumeNum"),
                           "status": "ok", "p_yes_7d_before": p_yes, "outcome": outcome})
    return {"markets_tried": tried, "with_price_history": with_hist,
            "pairs": pairs, "per_market": per_market}


# ---------------- selftest ----------------
def selftest():
    ok = 0
    total = 0
    def chk(label, got, want, tol=1e-6):
        nonlocal ok, total
        total += 1
        good = (got == want) if isinstance(want, str) else (got is not None and abs(got - want) <= tol)
        print(f"  [{'PASS' if good else 'FAIL'}] {label:<52} got={got} want={want}")
        ok += bool(good)

    # settlement: premium-at-risk returns
    chk("YES @0.30 settles YES -> +233.33%", settle("yes", 0.30, "yes")["ret_pct"], 233.3333, 1e-3)
    chk("YES @0.30 settles NO  -> -100%", settle("yes", 0.30, "no")["ret_pct"], -100.0)
    chk("NO  @0.70 settles NO  -> +42.857%", settle("no", 0.70, "no")["ret_pct"], 42.8571, 1e-3)
    chk("YES @0.30 still open  -> status", settle("yes", 0.30, None)["status"], "open")
    # Kalshi fee: 0.07*0.5*0.5 = 0.0175 -> rounds up to 0.02
    chk("kalshi fee p=0.50 qty=1", kalshi_fee(0.50, 1), 0.02)
    chk("kalshi fee p=0.50 qty=10", kalshi_fee(0.50, 10), 0.18)   # 0.175 -> 0.18
    # Kalshi rounds the fee UP to the cent: 0.0175 -> 0.02, so the winner keeps 96.0%, not
    # 96.5%. The rounded fee is what actually leaves the account, so the test pins 96.0.
    chk("YES @0.50 wins w/ kalshi fee (rounded up)",
        settle("yes", 0.50, "yes", venue="kalshi")["ret_pct"], 96.0)
    # calibration
    chk("brier perfect", brier([(1.0, 1), (0.0, 0)]), 0.0)
    chk("brier always-0.5 coin", brier([(0.5, 1), (0.5, 0)]), 0.25)
    chk("log loss p=0.9 y=1", log_loss([(0.9, 1)]), -math.log(0.9))
    chk("log loss is finite at p=0/1", log_loss([(0.0, 1)]), -math.log(1e-9), 1e-3)
    # a sharp forecaster (0.95 on 9 hits, 0.15 on the miss) beats the 0.90 base rate;
    # a constant 0.90 forecast cannot, by construction, so it must not be used here
    pairs = [(0.95, 1)] * 9 + [(0.15, 0)]
    s = calibration_summary(pairs)
    chk("skill positive for calibrated forecaster", s["skill_vs_base_rate_pct"] > 0, True)
    chk("empty sample reports NOT MEASURED", calibration_summary([])["status"], "NOT MEASURED")
    rel = reliability([(0.05, 0)] * 10 + [(0.95, 1)] * 10)
    chk("reliability bins count", len(rel), 2)
    chk("ece small for sharp forecaster", round(ece([(0.05, 0)] * 10 + [(0.95, 1)] * 10), 3), 0.05)

    print(f"\n{ok}/{total} cases pass")
    return 0 if ok == total else 1


# ---------------- commands ----------------
def cmd_settle(a):
    rows = json.load(open(a.picks))
    if isinstance(rows, dict):
        rows = rows.get("picks") or []
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    ledger, pairs = [], []
    for r in rows:
        s = settle(r["side"], r["entry_price"], r.get("outcome"), qty=r.get("qty", 1.0),
                   venue=r.get("venue", "polymarket"), fee_bps=r.get("fee_bps"))
        s.update({k: r.get(k) for k in ("market_id", "side", "entry_price", "question")})
        ledger.append(s)
        if s["status"] == "settled" and r.get("p_yes") is not None:
            pairs.append((float(r["p_yes"]), 1.0 if str(s["outcome"]) == "yes" else 0.0))
    with open(LEDGER, "a") as f:
        for s in ledger:
            s["logged_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            f.write(json.dumps(s) + "\n")
    cal = calibration_summary(pairs)
    print(f"settled {sum(1 for s in ledger if s['status']=='settled')} / {len(ledger)} contracts")
    print(f"calibration: {json.dumps({k: v for k, v in cal.items() if k != 'reliability'})}")
    json.dump({"ledger": LEDGER, "calibration": cal}, open(OUT, "w"), indent=1)
    print(f"wrote {OUT}")


def cmd_fetch(a):
    print(f"fetching up to {a.max_markets} settled Polymarket markets ...")
    got = fetch_sample(limit=a.limit, max_markets=a.max_markets)
    cal = calibration_summary(got["pairs"])
    print(f"  markets tried: {got['markets_tried']} | with price history: {got['with_price_history']}")
    if cal["status"] == "NOT MEASURED":
        print("  RESULT: NOT MEASURED — Polymarket's price-history endpoint returned no points, "
              "so there is no implied probability at decision time to score.")
    else:
        print(f"  brier={cal['brier']} log_loss={cal['log_loss']} ece={cal['ece']} n={cal['n']}")
    payload = {"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "class": "PREDICTION", "trial_family": [{"id": i, "rule": r} for i, r in PM_STRATEGIES],
               "coverage": {k: v for k, v in got.items() if k != "pairs"},
               "calibration": cal,
               "note": "Implied probability must be the market price before settlement. "
                       "outcomePrices are the settlement result and would score a perfect "
                       "Brier by construction — never use them as the forecast."}
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    json.dump(payload, open(a.out, "w"), indent=1)
    print(f"wrote {a.out}")


def cmd_selftest(a):
    sys.exit(selftest())


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    s = sub.add_parser("settle"); s.add_argument("--picks", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("--limit", type=int, default=100)
    f.add_argument("--max-markets", type=int, default=25)
    f.add_argument("--out", default=OUT)
    a = ap.parse_args()
    {"selftest": cmd_selftest, "settle": cmd_settle, "fetch": cmd_fetch}[a.cmd](a)


if __name__ == "__main__":
    main()
