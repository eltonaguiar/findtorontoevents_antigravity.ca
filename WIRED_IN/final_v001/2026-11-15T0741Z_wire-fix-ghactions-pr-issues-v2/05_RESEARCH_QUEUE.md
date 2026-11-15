# 05 — Research Queue (pre-registered, ranked)

Every item gets an `H-id`, a fixed spec, a stated **trial count**, a benchmark,
and a kill rule **before** results (`01_PROOF_PROTOCOL.md`, Gate 1). Add each to
`state/forward_test/plan.json`.

| H-id | Class | Hypothesis (testable) | Prior / evidence | Benchmark | Cost RT | Expected effect to prove | Artifact |
|------|-------|-----------------------|------------------|-----------|---------|--------------------------|----------|
| **H-103** | ETF | 12-mo cross-asset dual momentum, monthly rebalance, long top-k / cash | PF 3.57, Sharpe 1.62, WR 72.9%, MDD −12.4%, CAGR 29.1%, boot CI [1.64, 9.69], alpha t 2.36 | SPY | 12 bps | net excess > 0, t ≥ 1.96 over 152 windows | `reports/etf_dual_momentum_backtest_2026-06-03.md` |
| **H-201** | CRYPTO | BTC long when close > SMA200, cash otherwise | OOS wealth 1.94 vs 1.67 (asserted) | BTC-USD | 30 bps | reproduce + forward n ≥ 100 | `reports/backtest/H-201.json` |
| **H-120** | CRYPTO | 1-week cross-sectional reversal on liquid top-20 | H-120 scaffold exists | BTC-USD | 30 bps | net PF > 1.0, DSR ≥ 0.95 | `reports/backtest/H-120.json` |
| **H-301** | EQUITY | Betting-Against-Beta: long low-beta / short high-beta, dollar-neutral | academic (Frazzini-Pedersen) | SPY | 12 bps + borrow | net excess > 0, t ≥ 1.96 | `reports/backtest/H-301.json` |
| **H-302** | EQUITY | Quality-Minus-Junk: long quality / short junk | academic (AQR) | SPY | 12 bps | net excess > 0 | `reports/backtest/H-302.json` |
| **H-401** | FOREX | G10 carry: long high-yield, short low-yield, monthly | classic carry prior | DXY | spread+1pip+swap | net excess > 0 after swap | `reports/backtest/H-401.json` |
| **H-501** | COMMODITY | COT positioning z-score on deduped series | COT 93.8% was contaminated → post-dedup PF ~0.17 | GLD | 1 tick + roll | net excess > 0 on clean series | `reports/backtest/H-501.json` |
| **H-601** | ETF | TAA top-5/6-mo rotation (risk reduction) | Sharpe 0.88 vs 0.74, MaxDD −19% vs −51% (in-sample) | SPY / 60-40 | 12 bps | prove it is risk-reduction, label as such | `reports/TACTICAL_ROTATION_EDGE_2026-07-04.md` |

## Explicitly de-prioritized (do not spend cycles)

- Meme coins, 0DTE options, penny momentum — no cost-survivable prior
  (per `08_ELIMINATION_REGISTER.md`).
- Any parameter sweep that has not been added to `trial_count.json`.
- Any "wealth beat" without a shipped, re-runnable script.

## Sequencing rule

Run **H-103 first**. It is the only hypothesis with a verifiable backtest
artifact and a positive bootstrap CI. Do not start H-120/H-301 in parallel
until the forward-ledger cron is live (Gate 6 infrastructure) — otherwise they
will suffer the same "0 forward trades" fate.

## Trial-count discipline

- Pre-register the exact parameter grid and symbol sets.
- Increment `state/forward_test/trial_count.json` for each evaluated cell.
- DSR uses the running total; PBO needs ≥ 5 registered strategies/variants.
- A hypothesis may be revised only with a new `H-id` (never silently re-tune).
