#!/usr/bin/env python3
"""
READ-ONLY stop-loss optimization validation backtest.

Validates the winsorization counterfactual for two CRYPTO strategies using REAL
intrabar (1-minute) Binance OHLC klines instead of the idealized winsorization
that assumed a tighter SL always exits at exactly -cap (an upper bound that
ignores whipsaw).

For each closed pick we replay the actual 1m price path from entry forward and
take whichever of {candidate tighter SL, original take-profit, original
exit_time} is hit FIRST. Direction-aware. No production code is modified.

Data source for TP/SL: closed_picks rows in this repo do NOT carry explicit
take_profit / stop_loss fields, so we INFER them per pick:
  - original TP price: if exit_reason==TP -> realized exit price (the level that
    was actually hit). Otherwise the per-strategy median TP% applied to entry.
  - original SL: only used as the "original SL" baseline column; for the swept
    candidate levels we use fixed % distances (0.4/0.5/0.6/0.8%).
Candidate SL levels are expressed as % distance from entry on the loss side.
"""
import json, time, urllib.request, urllib.error, datetime, statistics, sys

PICKS_FILE = "battleground/data/closed_picks.json"
STRATS = ["crypto_liquidity_wick_reversal_v1", "atr_percentile_gate"]
CANDIDATE_SL = [0.4, 0.5, 0.6, 0.8]  # percent from entry
INTERVAL = "1m"

BINANCE_HOSTS = ["api", "api1", "api2", "api3"]

def to_ms(iso):
    return int(datetime.datetime.fromisoformat(iso).timestamp() * 1000)

def fetch_binance(symbol, start_ms, end_ms):
    """Return list of [openTime, O,H,L,C] dicts via binance failover. None if all fail."""
    out = []
    cur = start_ms
    end_ms = end_ms + 60000  # include the exit minute
    while cur <= end_ms:
        url_path = ("/api/v3/klines?symbol=%s&interval=%s&startTime=%d&endTime=%d&limit=1000"
                    % (symbol, INTERVAL, cur, end_ms))
        data = None
        for h in BINANCE_HOSTS:
            try:
                req = urllib.request.Request("https://%s.binance.com%s" % (h, url_path),
                                             headers={"User-Agent": "rr-backtest/1.0"})
                with urllib.request.urlopen(req, timeout=15) as r:
                    data = json.load(r)
                break
            except Exception:
                continue
        if data is None:
            return None  # total API failure
        if not data:
            break
        for k in data:
            out.append({"t": k[0], "o": float(k[1]), "h": float(k[2]),
                        "l": float(k[3]), "c": float(k[4])})
        last = data[-1][0]
        if last <= cur:
            cur = cur + 60000
        else:
            cur = last + 60000
        if len(data) < 1000:
            break
        time.sleep(0.15)  # politeness
    return out

def replay(klines, entry, direction, tp_price, sl_price, exit_close):
    """Walk klines; return realized signed pnl_pct.
    direction BUY: SL below entry, TP above. SELL: inverse.
    Within a bar, if both SL and TP could trigger we conservatively assume SL
    first (worst case for the strategy)."""
    for k in klines:
        if direction == "BUY":
            hit_sl = k["l"] <= sl_price
            hit_tp = k["h"] >= tp_price
        else:
            hit_sl = k["h"] >= sl_price
            hit_tp = k["l"] <= tp_price
        if hit_sl:
            px = sl_price
            return signed_pct(entry, px, direction)
        if hit_tp:
            px = tp_price
            return signed_pct(entry, px, direction)
    # neither hit -> time exit at the actual close
    return signed_pct(entry, exit_close, direction)

def signed_pct(entry, exit_px, direction):
    raw = (exit_px - entry) / entry * 100.0
    return raw if direction == "BUY" else -raw

def pf_wr(pnls):
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    gw = sum(wins)
    gl = -sum(losses)
    pf = (gw / gl) if gl > 0 else float("inf")
    wr = 100.0 * len(wins) / len(pnls) if pnls else 0.0
    aw = statistics.mean(wins) if wins else 0.0
    al = statistics.mean(losses) if losses else 0.0
    return wr, pf, aw, al

def main():
    d = json.load(open(PICKS_FILE))
    results = {}
    coverage = {}
    for strat in STRATS:
        rows = [r for r in d if r.get("strategy") == strat]
        # infer per-strategy median TP%
        tp_moves = []
        for r in rows:
            if r["exit_reason"] == "TP":
                tp_moves.append(abs(signed_pct(r["entry_price"], r["exit_price"], r["direction"])))
        med_tp = statistics.median(tp_moves) if tp_moves else 0.5

        # fetch klines for each pick
        kl_cache = []
        skipped = 0
        for r in rows:
            s = to_ms(r["entry_time"]); e = to_ms(r["exit_time"])
            kl = fetch_binance(r["symbol"], s, e)
            if kl is None:
                print("  API FAILURE on", r["symbol"], r["entry_time"], file=sys.stderr)
                kl = "APIFAIL"
            elif not kl:
                skipped += 1
            kl_cache.append(kl)

        api_fail = any(k == "APIFAIL" for k in kl_cache)
        coverage[strat] = {
            "n_total": len(rows),
            "n_no_data": sum(1 for k in kl_cache if (k != "APIFAIL" and not k)),
            "n_api_fail": sum(1 for k in kl_cache if k == "APIFAIL"),
            "med_tp_pct": round(med_tp, 4),
            "n_tp_exits": len(tp_moves),
        }

        strat_res = {}
        # baseline = stored pnl, restricted to picks we have klines for (apples-to-apples)
        usable = [(r, k) for r, k in zip(rows, kl_cache) if isinstance(k, list) and k]
        base_pnls = [r["pnl_pct"] for r, _ in usable]
        wr, pf, aw, al = pf_wr(base_pnls)
        strat_res["BASELINE_stored"] = dict(n=len(base_pnls), wr=wr, pf=pf, aw=aw, al=al)

        for cand in CANDIDATE_SL:
            pnls = []
            for r, kl in usable:
                entry = r["entry_price"]; dirn = r["direction"]
                if dirn == "BUY":
                    sl_price = entry * (1 - cand / 100.0)
                    tp_pct = abs(signed_pct(entry, r["exit_price"], dirn)) if r["exit_reason"] == "TP" else med_tp
                    tp_price = entry * (1 + tp_pct / 100.0)
                else:
                    sl_price = entry * (1 + cand / 100.0)
                    tp_pct = abs(signed_pct(entry, r["exit_price"], dirn)) if r["exit_reason"] == "TP" else med_tp
                    tp_price = entry * (1 - tp_pct / 100.0)
                p = replay(kl, entry, dirn, tp_price, sl_price, r["exit_price"])
                pnls.append(p)
            wr, pf, aw, al = pf_wr(pnls)
            strat_res["SL_%.1f%%" % cand] = dict(n=len(pnls), wr=wr, pf=pf, aw=aw, al=al)

        results[strat] = strat_res
        print("done", strat, "usable=", len(usable), "skipped/no-data=", coverage[strat]["n_no_data"],
              "apifail=", coverage[strat]["n_api_fail"], file=sys.stderr)

    out = {"results": results, "coverage": coverage,
           "generated": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    print(json.dumps(out, indent=2, default=lambda x: "Infinity" if x == float("inf") else x))

if __name__ == "__main__":
    main()
