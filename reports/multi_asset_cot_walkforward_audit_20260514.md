# multi_asset_cot Walk-Forward Audit — 2026-05-14

## Request
Run walk-forward split: train on pre-2025, test on 2025-2026 to see if edge holds OOS.

## Verdict: 🔴 WALK-FORWARD VALIDATION IMPOSSIBLE — SYSTEM FAILS

**The requested split (train pre-2025 / test 2025+) cannot be executed.** The COT pipeline was first activated on **2026-04-23**. There are zero trades before that date. The system has no historical depth.

---

## 1. Data Availability

| Period | Trades | First Trade | Last Trade |
|--------|--------|-------------|-------------|
| Pre-2025 | **0** | — | — |
| 2025 | **0** | — | — |
| Jan-Mar 2026 | **0** | — | — |
| April 2026 | 28 | 2026-04-23 | 2026-04-30 |
| May 2026 | 74 | 2026-05-01 | 2026-05-12 |
| **Total** | **102** | 2026-04-23 | 2026-05-12 |

**Data source:** `alpha_engine/data/closed_picks.json` (102 trades, source_system=multi_asset_cot)

**Historical COT data:** `data/cftc_cot/` directory is **empty** (only .gitkeep). No historical CFTC COT reports available for backtesting.

---

## 2. Pseudo Walk-Forward: April 2026 (IS) vs May 2026 (OOS)

Since pre-2025 data doesn't exist, the only possible split is chronological within the available 19-day window.

### 2.1 Aggregate Metrics

| Metric | IS (Apr 2026) | OOS (May 2026) | Delta |
|--------|---------------|----------------|-------|
| Trades | 28 | 74 | +46 |
| Win Rate | 78.6% | 100.0% | **+21.4%** |
| Profit Factor | 5.52 | ∞ (no losses) | ∞ |
| Total PnL | +0.93% | +3.36% | +2.43% |
| Avg Win | +0.05% | +0.05% | 0.00% |
| Avg Loss | −0.03% | N/A | N/A |

### 2.2 Symbol Breakdown

| Symbol | IS (Apr) | IS WR | OOS (May) | OOS WR |
|--------|----------|-------|-----------|--------|
| CT=F | 23 (82%) | 78.3% | 68 (92%) | 100% |
| ZW=F | 5 (18%) | 80.0% | 0 (0%) | — |
| KC=F | 0 (0%) | — | 6 (8%) | 100% |

### 2.3 The OOS "Improvement" Is an Artifact

The OOS 100% WR is **not genuine edge**. Every May trade shares the same pattern:

```
Status:      WON (74/74)
Exit Reason: TP_HIT_REPLAY (74/74)
closed_at:   None (0/74)
exit_date:   None (0/74)
PnL range:   0.0395% to 0.0718% (tight)
```

**TP_HIT_REPLAY** means these trades never hit TP or SL in the market. They are **replayed/simulated exits** that assume TP always got hit. The April trades also show 22/28 as TP_HIT_REPLAY, but had 6 real exits (5 SL_HIT + 1 SL_HIT_REPLAY) providing the only actual market feedback.

The May "100% WR" is an artifact of the replay mechanic, not of real trading.

---

## 3. Why Pre-2025 Is Impossible

| Barrier | Detail |
|---------|--------|
| **Pipeline activation** | `cot_positioning.py` scanner first emitted signals on 2026-04-23 |
| **No historical data** | `data/cftc_cot/` directory empty — no CFTC report archive |
| **No backtest capability** | `bt_cme_cot_positioning()` in `backtest_new_research_strategies.py` only works with live-fetched COT data (limit=30 data points), not historical archives |
| **No DB records** | MySQL unreachable, but even if accessible, no pre-2025 multi_asset_cot trades would exist |

---

## 4. The Over-Emission Factor

As documented in `reports/cot_pipeline_audit_20260514.md`, the 102 trades come from **only 5 unique CFTC weekly releases** (~20:1 over-emission). After 1-pick-per-cycle dedup:

| Metric | Full 102 | Dedup ~5 |
|--------|----------|----------|
| WR | 94.1% | 40% |
| PF | 21.86 | 0.17 |
| PnL | +429% | −$52 |

The walk-forward split on the dedup set (n≈5) would be meaningless — too few trades for statistical significance.

---

## 5. Conclusion

**The `multi_asset_cot` system cannot be walk-forward validated** for three independent reasons:

1. **No pre-2025 data exists** — Pipeline activated 2026-04-23, zero historical depth
2. **All trades are REPLAY artifacts** — TP_HIT_REPLAY dominates both IS (79%) and OOS (100%), meaning most "trades" never saw real market exits
3. **Over-emission inflates n** — 102 apparent trades = only 5 unique CFTC releases

**Recommendation:** The `REQUIRES_WALKAHEAD_AUDIT` flag (P1, same date) should remain **permanently**. The system cannot graduate to paper/live until:
- A historical CFTC COT archive is ingested (at minimum 2018-2025)
- A proper walk-forward backtest is run: train on 2018-2022 COT data, test on 2023-2026
- The replay mechanic is replaced with actual market exit simulation
- The over-emission fix (PR #961) is verified to produce ≤1 signal per CFTC release

Until then, `multi_asset_cot` should remain **excluded from Smart Picks and High Conviction**.

---

## 6. Data Appendix

### Exit Reason Distribution

| Exit Reason | April 2026 | May 2026 | Total |
|-------------|------------|----------|-------|
| TP_HIT_REPLAY | 22 | 74 | 96 |
| SL_HIT | 5 | 0 | 5 |
| SL_HIT_REPLAY | 1 | 0 | 1 |

### Trade Status Distribution

| Status | April 2026 | May 2026 | Total |
|--------|------------|----------|-------|
| WON | 22 | 74 | 96 |
| LOST | 6 | 0 | 6 |

---

*Generated: 2026-05-14 | Source: `alpha_engine/data/closed_picks.json` | 102 trades analyzed*
