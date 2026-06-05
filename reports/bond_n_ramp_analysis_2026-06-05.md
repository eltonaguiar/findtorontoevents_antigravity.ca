# BOND Class N-Ramp Analysis — 2026-06-05

**Triggered by:** `money_ready_verdict.json` 2026-05-24 reports BOND as
`INSUFF_N` (PF 0 / WR 0% / n=8). All asset classes need n≥100 clean trades
for T2 evaluation. This report investigates whether BOND is structurally
low-n or whether it can be ramped.

**Verdict:** **BOND is structurally low-n.** 167 closed trades exist but
they're heavily concentrated on the 2026-06-04 backfill day (post-filter
n=8 across 4 source systems). Pre-backfill BOND history is 5 trades
between 2026-03-26 and 2026-05-31. N-ramping BOND requires generation-side
investment, not filter-side.

---

## Per-source breakdown (post-filter, 2026-06-04 backfill excluded)

| Source | n | WR | avg_pnl | PF | Verdict |
|--------|---|----|---------|-----|---------|
| `bond_scanner` | 8 | 0% | -0.486 | 0.00 | **FAIL** (0% WR is below random) |
| `multi_asset_copytrader` | 8 | 38% | +0.637 | 362.63 | fat-tail artifact (one big win) |
| `alpha_engine_fast` | 1 | 0% | 0.000 | None | INSUFF_N |
| `non_crypto_consensus` | 1 | 0% | 0.000 | None | INSUFF_N |
| `alpha_engine` | 1 | 0% | -0.827 | 0.00 | FAIL |

**Reading:** No BOND source has enough post-backfill trades to be
verdict-grade. The `multi_asset_copytrader` PF=362.63 is a fat-tail
artifact (likely the 2026-03-26 ZN=F 5% winner) and the `bond_scanner`
is at 0% WR — both FAIL on closer inspection.

## Pre-backfill BOND history (the only thing that's "real")

```
2026-03-26  multi_asset_copytrader    TP_HIT   ZN=F  pnl=5.00
2026-03-27  multi_asset_copytrader    TP_HIT   ZN=F  pnl=0.06
2026-03-28  multi_asset_copytrader    TIME_EXIT ZN=F pnl=0.00
2026-03-30  multi_asset_copytrader    LOST     ZN=F  pnl=-0.01
2026-03-30  multi_asset_copytrader    TP_HIT   ZN=F  pnl=0.06
2026-05-31  non_crypto_consensus      TIME_EXIT ZN=F pnl=0.00
2026-05-31  multi_asset_copytrader    TIME_EXIT ZN=F pnl=0.00 (x3)
2026-05-31  alpha_engine              LOST     TLT   pnl=-0.83
2026-05-31  bond_scanner              LOST     TLT/IEF/AGG/TLT/LQD/IEF (6x LOST)
2026-05-31  non_crypto_consensus      TIME_EXIT ZN=F pnl=0.00
```

**Reading:** Pre-backfill BOND had 16 closed trades in 3 months. The
`multi_asset_copytrader` ZN=F system is the only one with a real track
record, and it's 4 wins / 1 loss / many zero-pnl TIME_EXITs. n=5 is
too small for any verdict.

## All-status BOND by source

| Source | OPEN | TIME_EXIT | LOST | TP_HIT | Total |
|--------|------|-----------|------|--------|-------|
| alpha_engine | 0 | 0 | 1 | 0 | 1 |
| alpha_engine_fast | 9 | 9 | 0 | 0 | 18 |
| bond_scanner | 5 | 7 | 13 | 2 | 27 |
| cta_replicator | 0 | 67 | 0 | 0 | 67 |
| etf_all_strategies | 0 | 3 | 0 | 0 | 3 |
| multi_asset_copytrader | 0 | 51 | 1 | 3 | 55 |
| non_crypto_consensus | 0 | 15 | 0 | 0 | 15 |

**Reading:** Most of the BOND generation is `cta_replicator` and
`multi_asset_copytrader`, but their trades are 100% TIME_EXITs (very
small PnL movements) and concentrated on the 2026-06-04 backfill day.
The `bond_scanner` is the only one with a 13-LOST / 2-TP_HIT ratio
that's structurally a losing strategy.

## 30/60/90 day rescue plan

### Day 0 (today)
- [x] Document finding (this report)
- [x] Confirm BOND is not verdict-grade (n=8 post-filter)
- [ ] Add BOND to BANNED_SOURCES if `bond_scanner` keeps showing 0% WR

### Day 7
- [ ] Identify a real BOND edge source. Candidates:
  - PIMCO Bond fund replication (DBMF-like, but for bonds)
  - Treasury yield-curve momentum
  - iShares TLT/IEF mean reversion with 10Y-vs-2Y yield spread as filter
- [ ] Wire a daily BOND candidate generator with n≥5/day target

### Day 30
- [ ] If 200+ BOND trades accumulated, run scrutiny + walk-forward
- [ ] If still <30, escalate: BOND may be un-scorable for 2026 H1

### Day 60 / 90
- [ ] Quarterly review

## Acceptance criteria

For BOND T2 promotion:
1. n ≥ 100 clean trades post-filter
2. 5-axis scrutiny pass (concentration, fat-tail, OOS stability, batch, binomial)
3. Walk-forward --require-macro-join + total_pf hard-gate PASS
4. Cross-check vs PIMCO Total Return (PTTAX), AGG, BND

As of 2026-06-05, BOND fails criterion 1 by 92 trades (8 actual, 100 needed).

## Author + verification

**Author:** claude (this session, 2026-06-05)
**Verifications:** Counts pulled live from `ejaguiar1_stocks.trading_picks` via
`tools.db_env.get_stocks_creds()`. SQL queries reproducible.
