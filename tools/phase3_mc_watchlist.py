#!/usr/bin/env python3
"""Phase 3 Monte Carlo bootstrap on watchlist candidates.

READ-ONLY. SELECT-only on ejaguiar1_stocks.trading_picks.
Resamples pnl_pct with replacement to estimate P(T2) and P(T1) at n=100 / n=200.
"""
from __future__ import annotations
import os, sys, json
import numpy as np
import pymysql

DB = dict(host='mysql.50webs.com', user='ejaguiar1_stocks',
          password=os.environ.get('DB_PASS_STOCKS','') or os.environ.get('MYSQL_PASSWORD',''), database='ejaguiar1_stocks',
          cursorclass=pymysql.cursors.Cursor, connect_timeout=15)

CANDIDATES = [
    ('stocks_rsi2_pullback', 'EQUITY'),
    ('fx_smart_carry_trade_momentum', 'FOREX'),
    ('cta_golden_cross_200', 'COMMODITY'),
    ('prediction_market_consensus', 'CRYPTO'),
    ('luxalgo_confluence', 'CRYPTO'),
    ('futures_momentum', 'BOND'),
]

CLOSED_STATUSES = ('WON','LOST','CLOSED','TP_HIT','SL_HIT','EXPIRED','TP','SL')

def fetch_pnl(cur, strategy: str, category: str) -> np.ndarray:
    # Category may be lowercase in DB
    cur.execute(
        """SELECT pnl_pct FROM trading_picks
           WHERE strategy=%s
             AND LOWER(category)=LOWER(%s)
             AND pnl_pct IS NOT NULL
             AND closed_at IS NOT NULL""",
        (strategy, category))
    rows = cur.fetchall()
    return np.array([float(r[0]) for r in rows], dtype=float)

def pf_wr(pnl: np.ndarray) -> tuple[float, float]:
    if len(pnl) == 0:
        return float('nan'), float('nan')
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]
    wr = len(wins) / len(pnl) * 100.0
    pos = wins.sum()
    neg = abs(losses.sum())
    pf = (pos / neg) if neg > 0 else (float('inf') if pos > 0 else float('nan'))
    return pf, wr

def bootstrap(pnl: np.ndarray, target_n: int, iters: int = 10000, seed: int = 42):
    if len(pnl) == 0:
        return None
    rng = np.random.default_rng(seed)
    pfs = np.empty(iters)
    wrs = np.empty(iters)
    for i in range(iters):
        sample = rng.choice(pnl, size=target_n, replace=True)
        pfs[i], wrs[i] = pf_wr(sample)
    # Clip infinities (rare; when zero losses in resample) for percentiles
    pfs_finite = pfs[np.isfinite(pfs)]
    return {
        'pf_p5': float(np.percentile(pfs_finite, 5)) if len(pfs_finite) else None,
        'pf_p50': float(np.percentile(pfs_finite, 50)) if len(pfs_finite) else None,
        'pf_p95': float(np.percentile(pfs_finite, 95)) if len(pfs_finite) else None,
        'wr_p5': float(np.percentile(wrs, 5)),
        'wr_p50': float(np.percentile(wrs, 50)),
        'wr_p95': float(np.percentile(wrs, 95)),
        'p_t2': float(np.mean((pfs >= 1.5) & (wrs >= 50.0))),
        'p_t1': float(np.mean((pfs >= 2.0) & (wrs >= 55.0))),
        'inf_rate': float(np.mean(~np.isfinite(pfs))),
    }

def main():
    conn = pymysql.connect(**DB)
    cur = conn.cursor()
    results = []
    for strategy, category in CANDIDATES:
        pnl = fetch_pnl(cur, strategy, category)
        n_now = len(pnl)
        pf_now, wr_now = pf_wr(pnl) if n_now else (None, None)
        row = {
            'strategy': strategy, 'category': category,
            'n_now': n_now,
            'pf_now': pf_now, 'wr_now': wr_now,
            'mean_pnl': float(pnl.mean()) if n_now else None,
            'std_pnl': float(pnl.std(ddof=1)) if n_now > 1 else None,
        }
        if n_now > 0:
            row['boot_now'] = bootstrap(pnl, max(n_now, 5))
            row['boot_100'] = bootstrap(pnl, 100)
            row['boot_200'] = bootstrap(pnl, 200)
        results.append(row)
    cur.close(); conn.close()
    print(json.dumps(results, indent=2, default=str))

if __name__ == '__main__':
    main()
