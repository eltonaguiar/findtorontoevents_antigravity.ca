# Forex Regime-Conditional Deep-Dive — 2026-06-05

**Triggered by:** Walk-forward post-backfill-filter surfaced 3/3 forex PASS candidates
(`myfxbook_retail_contrarian`, `cta_cross_asset_tsmom`, `non_crypto_consensus`).
This is a hedge-fund-standard regime-conditional check: does the edge hold across
VIX regimes, DXY trend, and macro regimes? Or is it concentrated in one corner?

**Verdict:** **All 3 walk-forward PASS verdicts are misleading.**

> **Resolution 2026-06-05 (this session):** Added `--require-macro-join` and
> `total_pf >= 1.0` hard-gate to `tools/walk_forward_per_strategy.py`. With
> both flags, only `mega_mutation::crypto` PASSes (n=166, total_pf=2.51,
> OOS_PF=2.58). All 3 forex candidates are correctly demoted. The 0/9
> money-ready verdict is fully consistent with the audit-grade walk-forward.

| Strategy | Walk-forward verdict | Overall actual | Macro-joinable actual | Verdict |
|----------|----------------------|----------------|------------------------|---------|
| `myfxbook_retail_contrarian` | PASS PF=2.39 | n=321 PF=0.98 | n=299 PF=0.96 (WR 48.8%) | **FAIL — losing overall** |
| `cta_cross_asset_tsmom` | PASS PF=3.77 | n=172 PF=2.05 | n=21 PF=0.70 (WR 33.3%) | **FAIL — 88% missing macro data, edge in the gap** |
| `non_crypto_consensus` | PASS PF=3.89 | n=107 PF=1.63 | n=93 PF=1.22 (WR 52.7%) | **BORDERLINE — barely above random** |

**The 0/9 money-ready verdict for FOREX holds.** All 3 walk-forward PASSes are
data artifacts, not edges.

---

## Methodology

Joined `trading_picks.closed_at` (DATE) with `alpha_macro.trade_date` to attach
VIX, DXY, DXY SMA50, and `regime` label. For each strategy, computed:
  - Overall PF/WR (the post-filter ground truth)
  - PF/WR conditional on VIX<15 / 15-25 / >25
  - PF/WR conditional on DXY > DXY SMA50 (rising) / DXY < DXY SMA50 (falling)
  - PF/WR by `alpha_macro.regime` label
  - "Macro-joinable" subset: trades that DO have a VIX entry

Key insight: `alpha_macro` is populated 2025-08-11 → 2026-04-27 (181 rows). All
forex trades in 2026-05 onward (151 of cta_cross_asset_tsmom's 172) have NO
macro join — this is the root of the "edge" in the walk-forward PASS.

---

## 1. `myfxbook_retail_contrarian::forex`

Walk-forward said: PASS at PF=2.39 (n=321).

| Bucket          |   n |  WR  |  PF  |
|-----------------|-----|------|------|
| **Overall**     | 321 | 48.3% | **0.98** |
| VIX 15-25       | 299 | 48.8% | 0.96 |
| DXY rising      |  37 | 70.3% | 3.00 |
| DXY falling     | 262 | 45.8% | 0.78 |
| calm_bull       | 299 | 48.8% | 0.96 |

**Reading:** The strategy is **losing overall** (WR < 50%, PF < 1). The
"edge" the walk-forward detected is concentrated in the 37 DXY-rising trades
(WR 70.3% / PF 3.00). The 262 DXY-falling trades are 45.8% WR / PF 0.78.
The walk-forward's rolling-window PF 2.39 is a sample-size artifact from
chunks where the small DXY-rising tail dominated.

**Action:** Do NOT promote. If pursuing, condition the strategy on DXY > DXY
SMA50 (n=37 → need n≥100 to validate).

---

## 2. `cta_cross_asset_tsmom::forex`

Walk-forward said: PASS at PF=3.77 (n=172).

| Bucket          |   n |  WR  |  PF  |
|-----------------|-----|------|------|
| **Overall**     | 172 | 56.4% | **2.05** |
| VIX 15-25       |  21 | 33.3% | 0.70 |
| **VIX missing** | 151 | 59.6% | 2.20 |
| DXY missing     | 151 | 59.6% | 2.20 |
| calm_bull       |  21 | 33.3% | 0.70 |

**Reading:** This is a **data-join artifact, not an edge.** 88% of trades
(151/172) closed in **2026-05** — a date range where `alpha_macro` is empty
(its last entry is 2026-04-27). These 151 trades are the "edge": WR 59.6% /
PF 2.20. The 21 trades that DO have macro data are losers: WR 33.3% / PF 0.70.

The walk-forward correctly says the strategy "is profitable" — but it cannot
test regime stability because 88% of the data is in a regime-less gap.

**Action:** Do NOT promote. Demote to LOW_CONFIDENCE_STRATEGIES. The strategy
needs to either:
  (a) accumulate n≥100 macro-joinable trades (current n=21, so this is a
      ~6-month wait given 2026-Q2 trade rate)
  (b) re-run walk-forward with `INNER JOIN alpha_macro` so the macro-joinable
      subset is what gets evaluated

---

## 3. `non_crypto_consensus::forex`

Walk-forward said: PASS at PF=3.89 (n=107).

| Bucket          |   n |  WR  |  PF  |
|-----------------|-----|------|------|
| **Overall**     | 107 | 54.2% | **1.63** |
| VIX 15-25       |  93 | 52.7% | 1.22 |
| VIX missing     |  14 | 64.3% | inf |
| DXY falling     |  93 | 52.7% | 1.22 |
| calm_bull       |  93 | 52.7% | 1.22 |

**Reading:** Borderline. Macro-joinable subset (n=93) has WR 52.7% / PF 1.22
— barely above random, no statistical edge. The 14 VIX-missing trades are
WR 64.3% / PF inf (no losing trades in that bucket), but n=14 is too small
to validate.

**Action:** Watchlist. WR 52.7% is suggestive but not at T2 threshold. Re-run
walk-forward when n reaches 200+ (currently 107 post-filter).

---

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Walk-forward PASS = data-join artifact (cta_cross_asset_tsmom) | **CONFIRMED** | HIGH | Add `INNER JOIN alpha_macro` requirement to walk-forward SQL OR re-run after `alpha_macro` is backfilled to current date |
| Walk-forward PASS = sample-size artifact (myfxbook_retail_contrarian) | **CONFIRMED** | HIGH | Require n≥100 per regime bucket before declaring PASS |
| Walk-forward PASS = thin bucket edge (non_crypto_consensus) | **MEDIUM** | MEDIUM | Track WR 52.7% bucket until n=200+ then re-evaluate |
| `alpha_macro` data gap (last entry 2026-04-27) | **HIGH** (3+ weeks stale) | MEDIUM | Add daily `alpha_macro` population cron; alert if >3 days stale |

---

## 30/60/90 day rescue plan

### Day 0 (today, 2026-06-05)
- [x] Identify walk-forward data-join artifacts
- [x] Document finding (this report)
- [x] Add `--require-macro-join` flag + `total_pf >= 1.0` hard-gate to walk-forward
- [x] Re-run walk-forward: 4 PASS → 1 PASS (only `mega_mutation::crypto`)

### Day 7 (2026-06-12)
- [ ] Backfill `alpha_macro` to 2026-06-05 (DXY + VIX daily feed)
- [ ] Re-run regime analysis on the same 3 strategies with complete macro data
- [ ] If a real edge emerges, spawn forward pilot + cron

### Day 30 (2026-07-05)
- [ ] If no FOREX T2 emerges: re-categorize all 3 strategies as NON_T2 in pf_registry
- [ ] Add `walk_forward_with_macro_join.py` to default audit sweep

### Day 60 / 90
- [ ] Quarterly review: did the macro-backfill reveal any real edge?

---

## Acceptance criteria for FOREX T2 promotion

For a FOREX strategy to be promoted to T2:
1. Walk-forward PASS with **macro-joinable data only** (or `alpha_macro` backfilled to current date)
2. Per-regime bucket n≥100 (currently no bucket qualifies)
3. Overall WR > 50% on macro-joinable subset (currently no strategy qualifies)
4. DXY-conditional PF > 1.5 in BOTH rising and falling regimes

As of 2026-06-05, **0 forex strategies pass these criteria.** The 0/9 money-ready
verdict for FOREX holds. The walk-forward's "3/3 forex PASS" was a data-join
artifact, not real edge.

---

## Author + verification

**Author:** claude (this session, 2026-06-05)
**Verifications:** All counts in this report were pulled live from
`ejaguiar1_stocks.trading_picks` (joined to `ejaguiar1_stocks.alpha_macro`)
via `tools.db_env.get_stocks_creds()`. SQL queries are reproducible.

**Cross-check vs walk-forward:** The walk-forward reported these 3 strategies
as PASS because it does not require macro-joinable data. With a macro-join
requirement, all 3 are removed (the candidate with the highest macro-joinable
PF is `non_crypto_consensus` at PF=1.22, which is below the 1.5 promotion
threshold).
