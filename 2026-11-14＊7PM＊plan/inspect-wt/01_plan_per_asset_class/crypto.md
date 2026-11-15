# CRYPTO — plan to profitability (conditional candidate)

**State:** sub-T2 overall (recent PF ~0.74, WR ~33%); elite-strat snapshots PF 2.3-4 are
pre-fix artifacts; fill fix shipped (+67.5pp correction, PF 0.768 → ~0.80 — NOT breakeven);
B4 settled (label-not-price, `--truncate-at-exit`); CRYPTO SWING emission should be killed
(n=243, PF 0.457, −328.6pp — peer P0); benchmark objection open (TSMOM Sharpe 2.13 vs
B&H ≈2.2). SubQ: P(2y) = 10-25%→25-40% band, style = position/swing, obstacle = costs (0.42).

## Order of operations
1. **Fill fidelity first (done for kimi; extend):** every strategy's claimed edge must
   exceed its measured fill error. Rule: if breakeven slippage < 2× measured slippage →
   strategy is dead regardless of backtest PF. Re-run `tools/stop_fill_replay.py
   --truncate-at-exit` per strategy; publish per-strategy fill budget.
2. **Kill CRYPTO SWING** (unanimous peer P0) and route `kimi_riseoftheclaw` through the
   intrabar resolver (P0 C1) before any new test.
3. **The ONE hypothesis:** vol-targeted trend on BTC/ETH only, position horizon 1-5 days,
   monthly re-rank, 0.15% round-trip cost, dual source (Binance + KuCoin).
   - **Gate:** forward **PF ≥ 1.3, WR ≥ 55%**, n ≥ 100, dual-source (peers' pre-registered
     gate) **AND beat B&H BTC risk-adjusted** (Sharpe basis — the TSMOM objection must be
     answered: beating *zero* is not beating *holding BTC*).
   - **Capacity/impact** check at $50k (crypto books are deep but our fills aren't modeled).
4. **Benchmark-relative honesty:** a crypto strategy that returns +30% with −60% MDD while
   BTC did +50% with −70% MDD is *maybe* worth it on Calmar — state the metric up front.

## Kill criteria
- Fill model unfixable for a strategy → dead.
- Gate miss at n=100 → dead (no threshold shopping).
- Either BTC-benchmark or PF gate fails → class returns to "conditional" and the allocation
  sleeve (which needs no alpha) remains the deployment path.

## Why conditional, not eliminated
It is the only class where (a) execution is API-native, (b) data is dual-sourced for free,
(c) a fill model now exists. That makes it the *cleanest* place to prove the process works —
even if the process's answer ends up "no".
