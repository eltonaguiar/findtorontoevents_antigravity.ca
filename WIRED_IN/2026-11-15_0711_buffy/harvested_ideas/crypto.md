# CRYPTO

**Scan footprint:** 5,628 flagged files (largest class), 938 tree-ensemble, 700 state-space,
1,021 bootstrap/MC.

**Closed-ledger measurement** (3,500-pick payload, gross `pnl_pct`):

| n | mean | median | WR | PF |
|---:|---:|---:|---:|---:|
| 2,070 | +0.54% | −0.88% | 46.1% | 1.31 |

**Verdict: PRMISING, unproven.** Largest sample and the only class where PF > 1.2, but the
negative median means the mean is carried by a minority of large winners. Not benchmarked yet:
BTC-USD excess for these rows has never been computed (the machinery exists as of 2026-11-15).

**What has been tried:** 149 `ml_enhanced` per-symbol variants (119 with n=1 — phantom PF 6.67,
family PF 0.63); funding-rate arb (`alpha_engine/funding_rate_arb.py`); Kalman mean reversion;
RSI-whale; cointegration pairs (synthetic-only backtest); scalp suites; copy-trader clones.
**Abandoned within the class:** the ML variant farm, Mercury2 (paused), several scalp systems.

**What is missing:**
- excess vs BTC-USD on the closed ledger (never computed);
- a regime split (8,609 files mention regime, none report CRYPTO per regime);
- separation of majors from alts — the prior mixes them, so a majors-only edge is invisible.

**Next experiment:** recompute the 2,070 rows as excess vs BTC-USD, clustered on
`(entry_day, exit_day)`, split majors (BTC/ETH) vs alts. If excess CI excludes zero for majors
only, that is a real candidate; if not, the class is closed.
