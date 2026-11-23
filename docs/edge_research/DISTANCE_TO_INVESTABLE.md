# Distance to investable — measured, 2026-11-23

**Paper only. Zero capital. Not investment advice.**

## 1. Is there an edge worth real money? No.
- **0 of 6 classes** survive deflation (copilot, N=90) and **0 of 69 ranked picks**
  pass all five gates (this worktree, G1–G5).
- Best robust DSR by minimum-n floor: **n≥30 → 0.159**, **n≥50 → 0.136**,
  **n≥100 → 0.021**. The only `0.9999` DSR is at **n=22**, below any promotion floor.
- SR* at programme N: **1.62 (N=90) → 1.66 (N=108) → 1.92 (N=362) → 2.03 (N=658)**.
  Best observed *credible* Sharpe ≈ 0.31 (n=38). The gap does not close by adding trials — it widens.

## 2. Is there something worth *buying*? Yes, and it is not an edge.
10-year cost on $100,000 (implied MER, sector-typical, **tax not modelled**):

| Vehicle | 10-y cost | implied/yr | vs ETF |
|---|---|---|---|
| Direct holdings | $50 | 0.005% | 0.05× |
| Broad low-cost index ETF | $1,050 | 0.105% | 1× |
| Index mutual fund | $4,520 | 0.452% | 4.3× |
| Active mutual fund | $18,520 | 1.852% | **17.6×** |

**Break-even bar for any active strategy** (monthly turnover, beat the ETF net):
- **$1k tickets → must earn +3.34%/yr excess** over the ETF.
- **$25k tickets → +0.80%/yr excess.**

## 3. Distance to paper trading? Harness ready, nothing worth feeding it.
A frozen forward harness already ticks (`tools/tom_forward_clock.py`, `n_records=0`;
ETF trend clock frozen 2026-11-23). Paper trading an unvalidated signal produces a
number, not information, and it burns the one free forward look. Current state:
**0 validated, so 0 worth paper trading.**

## 4. Distance to backtests? Rig is trustworthy; running more is the wrong move.
Identical entry criteria across classes, measured cost (4.97 bp copilot / 12.87 bp
conservative), DSR+PBO with programme-level N. The binding constraint is
**multiple-testing debt**, not missing ideas. Every new backtest widens SR* for
everything else.

## 5. What I would actually do
1. **Buy the low-cost index ETF.** That is the only defensible real-money answer.
2. **Stop running backtests.** Spend trials only on (a) an unspent data axis and
   (b) forward-only measurement (pre-registered by construction → 1 trial, not 5).
3. Scale PIT fundamentals 12→500 tickers so a fundamental test can be run **once**
   and believed.

## 6. Defects I found in my own claims this session (fixed or logged)
- Kill rule had **one** hurdle; a strategy long the benchmark clears it on beta. Fixed → two hurdles.
- Mean-only paired bootstrap **falsely passed H-119** (+20.6%/yr); the median test (and sign test p=0.45) **kills** it. Fixed → require mean **and** median CI.
- `12.07 bp` spread cited as "13 names measured" but the **13 names were never persisted** → logged LOW_CONFIDENCE; adopt copilot's 4.97 bp as primary, 12.87 as conservative bound.
- Trial count **conflated**: registry 108 vs cells 362 vs symbols 658 vs copilot 146 — every claim must state which.
- BH over bootstrap p-values yields 21 "survivors" that **all sit at the p=0.0005 resolution floor** — saturation, not signal.
- EQUITY/ETF universe is **survivorship-biased** (0 delisted names) → treat those backtests as upward-biased.
