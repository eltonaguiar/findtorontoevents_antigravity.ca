#!/usr/bin/env python3
"""R1 FEE-REALITY AUDIT (REALTIMECHALLENGE kilo, 200-round program Phase 0).

Question (pre-registered): Is the project's assumed 20 bp round-trip cost right,
and does the cost-vs-edge conclusion survive the *real* published fee schedules?

Reproducible: `python3 reports/realtime_challenge/kilo/r1_fee_reality_audit.py`
Read-only. No keys. Uses ccxt public `exchange.fees['trading']` (published tiers).
Reports gross/fee/net together and names the least-survivable number.
"""
import json, hashlib, datetime, sys

PROJECT_ASSUMED_RT_BP = 20.0          # the number under audit
GATE_C_EDGE_COST = 3.0                # gross edge must be >= 3x RT cost
# Round-0 measured gross edge per trade (peer + my probe, 5m crypto): +2.2 bp/trade
MEASURED_GROSS_BP_PER_TRADE = 2.2

def rt_bp(fee):
    return round((fee["maker"] + fee["taker"]) * 1e4, 3)

def main():
    import ccxt
    rows = []
    for ex_id, kind in [
        ("binance", "spot"), ("binanceusdm", "perp"),
        ("bybit", "spot"), ("okx", "spot"),
        ("kraken", "spot"), ("coinbase", "spot"),
    ]:
        try:
            ex = getattr(ccxt, ex_id)({"enableRateLimit": True})
            f = ex.fees.get("trading", {})
            maker, taker = f.get("maker"), f.get("taker")
            if maker is None or taker is None:
                rows.append({"exchange": ex_id, "kind": kind, "status": "no-public-fee"})
                continue
            rows.append({
                "exchange": ex_id, "kind": kind,
                "maker_bp": round(maker * 1e4, 3), "taker_bp": round(taker * 1e4, 3),
                "rt_maker_bp": round(maker * 2 * 1e4, 3),
                "rt_taker_bp": round(taker * 2 * 1e4, 3),
                "status": "ok",
            })
        except Exception as e:
            rows.append({"exchange": ex_id, "kind": kind, "status": f"err:{type(e).__name__}"})

    # verdict math: can measured gross clear Gate C at each real RT cost?
    for r in rows:
        if r["status"] != "ok":
            continue
        for leg in ("rt_maker_bp", "rt_taker_bp"):
            need = GATE_C_EDGE_COST * r[leg]
            r[f"gateC_need_bp_{leg}"] = round(need, 2)
            r[f"passes_{leg}"] = MEASURED_GROSS_BP_PER_TRADE >= need

    out = {
        "round": "R1",
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "project_assumed_rt_bp": PROJECT_ASSUMED_RT_BP,
        "measured_gross_bp_per_trade": MEASURED_GROSS_BP_PER_TRADE,
        "gateC_edge_cost": GATE_C_EDGE_COST,
        "exchanges": rows,
    }
    blob = json.dumps(out, indent=2, sort_keys=True)
    print(blob)
    with open(__file__, "rb") as fh:
        out["artifact_sha"] = hashlib.sha256(fh.read()).hexdigest()[:16]
    with open(__file__.replace(".py", ".json"), "w") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)

    # least-survivable number
    oks = [r for r in rows if r["status"] == "ok"]
    if oks:
        best = min(oks, key=lambda r: r["rt_taker_bp"])
        print("\nLEAST-SURVIVABLE NUMBER:",
              f"even at {best['exchange']} taker RT={best['rt_taker_bp']}bp, "
              f"Gate C needs >={best['gateC_need_bp_rt_taker_bp']}bp/trade but "
              f"measured gross is {MEASURED_GROSS_BP_PER_TRADE}bp -> "
              f"{'PASS' if best['passes_rt_taker_bp'] else 'FAIL'} by "
              f"{round(best['gateC_need_bp_rt_taker_bp']/MEASURED_GROSS_BP_PER_TRADE,1)}x")

if __name__ == "__main__":
    main()