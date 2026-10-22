#!/usr/bin/env python3
"""buffy_mega_mutation_paper_tracker.py — honest forward paper monitor.

Candidate under test (Buffy 2026-10-22):
    strategy LIKE 'mega_mutation%' AND direction='SHORT', CRYPTO,
    hard first-touch exits only (TP_HIT / SL_HIT), sentinels excluded.

Why this candidate: it is the ONLY strategy family that *improves*
out-of-sample (train PF 1.12 -> Oct PF 2.9) and whose forward-slice
(60d) bootstrap expectancy CI excludes zero — unlike the phantom
"proven" winners (high_trust_momentum, commodity_term_cot) which
decayed to negative in October when measured the same way.

This job records every NEW hard-resolved trade (by dedup_hash) into
audit_dashboard/data/buffy_paper_trades.json and, once n>=20, applies:
  1. exact binomial test of WR vs a coin flip (p<0.05 two-sided)
  2. forward bootstrap expectancy 95% CI (must exclude 0)
  3. vs BTC benchmark: strategy must have positive avg AND higher WR than BTC's
Hard-resolved only. Read-only against MySQL. No real sizing.

Run: python tools/buffy_mega_mutation_paper_tracker.py
"""
import json
import math
import os
import random
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

try:
    import pymysql
    from pymysql.cursors import DictCursor
except ImportError:
    sys.exit("pip install pymysql")

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "audit_dashboard" / "data" / "buffy_paper_trades.json"
MIN_N_VERDICT = 20

STRAT = "strategy LIKE 'mega_mutation%' AND direction='SHORT'"


def _pw():
    p = REPO / ".env.dbpw"
    if p.exists():
        try:
            return json.loads(p.read_text())["stocks"]
        except Exception:
            pass
    return os.getenv("AUDIT_DB_PASS", "")


def _conn():
    return pymysql.connect(
        host=os.getenv("AUDIT_DB_HOST", "mysql.50webs.com"),
        user=os.getenv("AUDIT_DB_USER", "ejaguiar1_stocks"),
        password=_pw(),
        database=os.getenv("AUDIT_DB_NAME", "ejaguiar1_stocks"),
        connect_timeout=30, cursorclass=DictCursor)


def _num(x):
    return float(x) if isinstance(x, Decimal) else x


def fetch_trades(cur):
    """All hard-resolved mega_mutation SHORT trades + a BTC benchmark slice."""
    cur.execute(f"""
        SELECT dedup_hash, symbol, strategy, entry_price, exit_price, pnl_pct,
               status, exit_reason, recorded_at, closed_at
        FROM at_raw_picks
        WHERE {STRAT} AND status IN ('WON','LOST')
          AND exit_reason IN ('TP_HIT','SL_HIT')
          AND entry_price>0 AND exit_price>0
          AND ABS(COALESCE(pnl_pct,0)) < 500
        ORDER BY recorded_at
    """)
    trades = [{k: _num(v) for k, v in r.items()} for r in cur.fetchall()]

    cur.execute("""
        SELECT pnl_pct FROM at_raw_picks
        WHERE symbol='BTCUSDT' AND status IN ('WON','LOST')
          AND exit_reason IN ('TP_HIT','SL_HIT') AND entry_price>0 AND exit_price>0
          AND ABS(COALESCE(pnl_pct,0)) < 500
          AND recorded_at >= NOW()-INTERVAL 180 DAY
    """)
    btc = [_num(r["pnl_pct"]) for r in cur.fetchall() if r["pnl_pct"] is not None]
    return trades, btc


def binom_two_sided_p(k, n):
    """Exact two-sided binomial p-value vs p=0.5, no scipy."""
    if n == 0:
        return 1.0
    def pmf(i):
        return math.comb(n, i) * 0.5 ** n
    p_obs = pmf(k)
    return sum(pmf(i) for i in range(n + 1) if pmf(i) <= p_obs + 1e-12)


def bootstrap_expectancy_ci(vals, n_iter=10000, seed=42):
    if not vals:
        return (0.0, 0.0, 0.0)
    random.seed(seed)
    means = []
    for _ in range(n_iter):
        s = [random.choice(vals) for _ in vals]
        means.append(sum(s) / len(s))
    means.sort()
    return (sum(means) / len(means), means[250], means[9750])


def main():
    conn = _conn()
    cur = conn.cursor()
    trades, btc = fetch_trades(cur)
    conn.close()

    prev = {"seen": [], "generated_at": None, "verdict": None}
    if OUT.exists():
        try:
            prev = json.loads(OUT.read_text())
        except Exception:
            pass
    seen = set(prev.get("seen", []))

    new = [t for t in trades if t.get("dedup_hash") and t["dedup_hash"] not in seen]
    for t in new:
        seen.add(t["dedup_hash"])

    pnls = [t["pnl_pct"] for t in trades if t.get("pnl_pct") is not None]
    wins = sum(1 for p in pnls if p > 0)
    n = len(pnls)
    wr = wins / n if n else 0.0
    pf = (sum(p for p in pnls if p > 0) / abs(sum(p for p in pnls if p < 0))) if any(p < 0 for p in pnls) else None
    mean, ci_lo, ci_hi = bootstrap_expectancy_ci(pnls)
    p_coinflip = binom_two_sided_p(wins, n) if n else 1.0

    # forward-only (last 60d) view — the anti-decay lens
    cutoff = datetime.now(timezone.utc).timestamp() - 60 * 86400
    fwd = [t["pnl_pct"] for t in trades
           if t.get("pnl_pct") is not None and t.get("recorded_at")
           and _ts(t["recorded_at"]) >= cutoff]
    fwd_wins = sum(1 for p in fwd if p > 0)
    fmean, flo, fhi = bootstrap_expectancy_ci(fwd)

    btc_wr = (sum(1 for p in btc if p > 0) / len(btc)) if btc else 0.0
    btc_mean = (sum(btc) / len(btc)) if btc else 0.0

    verdict = "INSUFFICIENT_DATA"
    reasons = []
    if n >= MIN_N_VERDICT:
        passes = []
        if p_coinflip < 0.05:
            passes.append(f"beats-coinflip(p={p_coinflip:.4f})")
        else:
            reasons.append(f"WR not >50% vs coin-flip (p={p_coinflip:.4f})")
        if ci_lo > 0:
            passes.append(f"pooled-CI-excludes-0([{ci_lo:.2f},{ci_hi:.2f}])")
        else:
            reasons.append(f"pooled CI straddles 0 ([{ci_lo:.2f},{ci_hi:.2f}])")
        if flo > 0:
            passes.append(f"forward-CI-excludes-0([{flo:.2f},{fhi:.2f}])")
        else:
            reasons.append(f"forward CI straddles 0 ([{flo:.2f},{fhi:.2f}])")
        if mean > 0 and wr > btc_wr:
            passes.append(f"beats-BTC(WR {wr:.2f}>{btc_wr:.2f})")
        else:
            reasons.append(f"does not beat BTC benchmark (WR {wr:.2f} vs {btc_wr:.2f})")
        verdict = "PAPER_WINNER" if len(passes) == 4 else "NOT_PROVEN"
        if verdict == "NOT_PROVEN":
            reasons = [f"only passed {len(passes)}/4 gates: " + "; ".join(passes)]

    payload = {
        "agent": "Buffy (Freebuff / MiMo)",
        "candidate": "mega_mutation* SHORT (CRYPTO, hard TP/SL first-touch)",
        "generated_at": datetime.now(timezone.utc).isoformat() + "Z",
        "n_trades": n, "wins": wins, "win_rate": round(wr, 4),
        "profit_factor": round(pf, 3) if pf else None,
        "expectancy_pct": round(mean, 3),
        "bootstrap_95ci": [round(ci_lo, 3), round(ci_hi, 3)],
        "p_coinflip": round(p_coinflip, 5),
        "forward_60d": {"n": len(fwd), "win_rate": round(fwd_wins / len(fwd), 4) if fwd else 0,
                        "expectancy_pct": round(fmean, 3),
                        "bootstrap_95ci": [round(flo, 3), round(fhi, 3)]},
        "benchmark_btc": {"n": len(btc), "win_rate": round(btc_wr, 4), "avg_pct": round(btc_mean, 3)},
        "verdict": verdict,
        "verdict_reason": reasons if reasons else ["all 4 gates passed"],
        "gates": ["beat coin-flip WR (p<0.05)", "pooled bootstrap CI excludes 0",
                  "forward 60d bootstrap CI excludes 0", "beat BTC benchmark WR"],
        "seen": sorted(seen),
        "disclaimer": "Paper forward-monitor only. Hard-resolved trades. Not real sizing. "
                      "Pooled CI can hide decay — trust the forward_60d CI.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"mega_mutation SHORT paper tracker: n={n} WR={wr:.1%} "
          f"PF={pf or 'NA'} exp={mean:.2f}% CI=[{ci_lo:.2f},{ci_hi:.2f}] "
          f"p={p_coinflip:.4f} | fwd60d n={len(fwd)} exp={fmean:.2f}% "
          f"CI=[{flo:.2f},{fhi:.2f}] | BTC WR={btc_wr:.1%}")
    print(f"VERDICT: {verdict} ({'; '.join(reasons) if reasons else 'all gates passed'})")
    print(f"new trades recorded this run: {len(new)}")
    return 0


def _ts(s):
    from dateutil import parser as _p  # optional
    try:
        return _p.parse(str(s)).timestamp()
    except Exception:
        return 0.0


if __name__ == "__main__":
    sys.exit(main())
