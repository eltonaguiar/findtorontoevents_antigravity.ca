# Per-Class T2 Inventory — Post-Backfill-Filter (2026-06-05)

**Generated:** 2026-06-05 10:25 UTC
**Source:** `reports/per_class_scrutiny_20260605.json` (29 (source, class) pairs, n≥30)
**Methodology:** 5-axis scrutiny (concentration, fat-tail, OOS stability, batch-artifact, binomial) on `trading_picks` post-`DATE(closed_at) != '2026-06-04'` filter.

**Headline:** 0/9 classes are money-ready. Only `mega_mutation::crypto` is T1-confirmed (5/5 PASS_ALL_AXES). All other candidates are WATCHLIST (4/5), BORDERLINE (3/5), or FAIL (≤2/5).

**Verdict breakdown:**
- ✅ **PASS_ALL_AXES (5/5):** 1 candidate — `mega_mutation::crypto`
- ⚠️ **WATCHLIST (4/5):** 2 candidates — `luxalgo_filters::crypto`, `multi_asset_copytrader::forex`
- 🟡 **BORDERLINE (3/5):** 6 candidates
- ❌ **FAIL (≤2/5):** 20 candidates
- **(empty class):** 1 candidate (alpha_engine with no class label — needs triage)

---

## CRYPTO — 16 sources, 1 PASS / 1 WATCH / 5 BORDERLINE / 9 FAIL

| Verdict | Source | n | WR | PF | Axes | Failing axes |
|---------|--------|---|----|----|------|--------------|
| ✅ PASS_ALL_AXES | `mega_mutation` | 295 | 64.1% | **3.16** | 5/5 | — |
| ⚠️ WATCHLIST | `luxalgo_filters` | 2009 | 43.4% | 1.06 | 4/5 | bin |
| 🟡 BORDERLINE | `kimi_signal_tracking` | 138 | 58.0% | 2.46 | 3/5 | fat, bat |
| 🟡 BORDERLINE | `ml_crypto_predictor` | 324 | 45.4% | 1.83 | 3/5 | oos, bin |
| 🟡 BORDERLINE | `battleground` | 145 | 57.9% | 1.17 | 3/5 | con, bat |
| 🟡 BORDERLINE | `alpha_engine` | 804 | 50.5% | 0.57 | 3/5 | oos, bin |
| 🟡 BORDERLINE | `genome` | 44 | 34.1% | 5.34 | 3/5 | fat, bin |
| ❌ FAIL | `prediction_market_agents` | 135 | 47.4% | 44.24 | 2/5 | con, bat, bin |
| ❌ FAIL | `genome_mutations` | 51 | 51.0% | 16.8 | 2/5 | fat, bat, bin |
| ❌ FAIL | `battleground_luxalgo` | 97 | 46.4% | 9.09 | 2/5 | fat, oos, bin |
| ❌ FAIL | `ml_crypto_pred` | 40 | 37.5% | 2.57 | 1/5 | fat, oos, bat, bin |
| ❌ FAIL | `copy_trader_intel` | 90 | 2.2% | 2.12 | 2/5 | fat, bat, bin |
| ❌ FAIL | `ml_strategy_reviver` | 58 | 19.0% | 1.14 | 1/5 | fat, oos, bat, bin |
| ❌ FAIL | `mercury2` | 76 | 44.7% | 0.34 | 2/5 | oos, bat, bin |
| ❌ FAIL | `alpha_engine_fast` | 399 | 19.5% | 0.6 | 2/5 | oos, bat, bin |
| ❌ FAIL | `short_dominant_engine` | 56 | 3.6% | — | 2/5 | fat, bat, bin |

**Reading:** `mega_mutation::crypto` is the only confirmed T1 in CRYPTO. The
two near-promotions (`luxalgo_filters`, `kimi_signal_tracking`) fail the
binomial axis — not enough wins vs sample size to be statistically distinguishable
from a 50% coin flip.

**The "78.9% CRYPTO Smart-Picks" cell on /audit/pick_funnel.html remains
DISPUTED** (per memory `confidence-trust-edges-2026-05-31.md`). Raw DB CRYPTO
n=728 has WR=43% PF=1.14 — the 78.9% figure comes from a different aggregation
path (4 leakage signals: 1864 duplicate signal-ts groups, EXPIRED→WON mislabels,
91.7% concentration in `claude_gainer_st` with only 3 closed rows in raw DB).
Live money_ready_verdict.json shows CRYPTO n=303 WR=35% PF=0.99, which is
NOT_READY. The 0/9 money-ready verdict is correct.

---

## FOREX — 1 WATCH / 1 BORDERLINE / 3 FAIL

| Verdict | Source | n | WR | PF | Axes | Failing axes |
|---------|--------|---|----|----|------|--------------|
| ⚠️ WATCHLIST | `multi_asset_copytrader` | 1198 | 45.2% | 1.01 | 4/5 | oos |
| 🟡 BORDERLINE | `non_crypto_consensus` | 110 | 54.5% | 1.77 | 3/5 | oos, bin |
| ❌ FAIL | `cta_replicator` | 179 | 55.9% | 2.06 | 1/5 | con, oos, bat, bin |
| ❌ FAIL | `forex_copy_trader` | 65 | 38.5% | 0.84 | 2/5 | fat, oos, bin |
| ❌ FAIL | `alpha_engine` | 40 | 30.0% | 0.36 | 2/5 | fat, oos, bin |

**Reading:** `multi_asset_copytrader` is the strongest FOREX candidate
(WR 45.2% PF 1.01 n=1198) but it fails the OOS axis (likely
non-stationary across sub-regimes). Per `reports/deep_dive_forex_regime_2026-06-05.md`,
the walk-forward 3/3 forex PASSes were data-join artifacts. None of the
FOREX candidates are T2-promotable.

---

## EQUITY — 3 FAIL

| Verdict | Source | n | WR | PF | Axes | Failing axes |
|---------|--------|---|----|----|------|--------------|
| ❌ FAIL | `multi_asset_copytrader` | 404 | 23.3% | 0.66 | 2/5 | oos, bat, bin |
| ❌ FAIL | `regime_terminal` | 143 | 39.2% | 1.05 | 2/5 | oos, bat, bin |
| ❌ FAIL | `non_crypto_consensus` | 32 | 3.1% | 0.22 | 0/5 | con, fat, oos, bat, bin |
| ❌ FAIL | `alpha_engine` | 41 | 46.3% | 0.48 | 1/5 | fat, oos, bat, bin |

**Reading:** EQUITY is structurally low-n and not T2-promotable. Per
`reports/per-asset-winner-dig-2026-06-05.md`, NVDA/META/MSFT consensus is
the strongest paper-only candidate (5 NVDA trades all losers in live DB;
Wall Street yfinance data confirms +30% upside but our 0-n execution layer
fails). No equity T2 candidate has n≥30 with stable edge.

---

## COMMODITY — 2 FAIL

| Verdict | Source | n | WR | PF | Axes | Failing axes |
|---------|--------|---|----|----|------|--------------|
| ❌ FAIL | `cta_replicator` | 220 | 29.1% | 0.8 | 2/5 | oos, bat, bin |
| ❌ FAIL | `multi_asset_copytrader` | 795 | 29.9% | 0.32 | 2/5 | con, oos, bin |

**Reading:** **0/6 commodity classes are money-ready.** Per
`reports/deep_dive_commodity_2026-06-05.md`, the n=220 / n=795 figures are
post-2026-06-04 backfill filter. The original 5,960 commodity rows on
2026-06-04 were the resolver backfill (97% of all commodity-class closed
trades), which made commodity look like a T1 candidate. Post-filter,
commodity has zero T2 candidates.

---

## BOND — 0 sources (n<30)

| Verdict | Source | n | WR | PF | Axes | Failing axes |
|---------|--------|---|----|----|------|--------------|
| — | — | — | — | — | — | — |

**Reading:** Per `reports/bond_n_ramp_analysis_2026-06-05.md`, BOND is
structurally low-n (8 post-filter trades). 167 closed trades exist but
159 are 2026-06-04 backfill; pre-backfill is 16 trades in 3 months.
N-ramp requires generation-side investment, not filter-side. No bond
candidate qualifies for 5-axis scrutiny at n≥30.

---

## ETF — 0 sources (n<30)

No ETF source has n≥30 in the post-filter data. ETF candidates exist in
the live picks list but haven't accumulated enough closed trades for
5-axis scrutiny. The `etf_verified_dual_momentum` paper pilot (per memory
`ETF paper pilot Day-1 2026-06-02`) is the only lab Tier-2 wired for
forward n; pilot is running but hasn't yet hit the n≥30 audit threshold.

---

## MEME — 1 FAIL

| Verdict | Source | n | WR | PF | Axes | Failing axes |
|---------|--------|---|----|----|------|--------------|
| ❌ FAIL | `alpha_engine_fast` | 45 | 26.7% | 0.31 | 2/5 | fat, oos, bin |

**Reading:** MEME is a single-source class with 0% win rate. Not T2-promotable.

---

## (empty class) — 1 FAIL

| Verdict | Source | n | WR | PF | Axes | Failing axes |
|---------|--------|---|----|----|------|--------------|
| ❌ FAIL | `alpha_engine` | 87 | 52.9% | 0.92 | 1/5 | con, oos, bat, bin |

**Reading:** One alpha_engine row with an empty class label. Likely a
data-quality issue (no category stamped at creation). Needs triage —
should not be classified as a T2 candidate.

---

## Per-class summary table

| Class | n sources | PASS | WATCH | BORDERLINE | FAIL | Money-ready? |
|-------|-----------|------|-------|------------|------|--------------|
| CRYPTO | 16 | 1 | 1 | 5 | 9 | **NOT_READY** (only 1 T1 sub-strategy) |
| FOREX | 5 | 0 | 1 | 1 | 3 | **INSUFFICIENT_DATA** |
| EQUITY | 4 | 0 | 0 | 0 | 4 | **INSUFFICIENT_DATA** |
| COMMODITY | 2 | 0 | 0 | 0 | 2 | **INSUFFICIENT_DATA** |
| BOND | 0 | 0 | 0 | 0 | 0 | **INSUFFICIENT_DATA** (n=0) |
| ETF | 0 | 0 | 0 | 0 | 0 | **INSUFFICIENT_DATA** (n<30) |
| MEME | 1 | 0 | 0 | 0 | 1 | **INSUFFICIENT_DATA** |
| (empty) | 1 | 0 | 0 | 0 | 1 | **INSUFFICIENT_DATA** |

**Verdict: 0/9 classes are money-ready.**

---

## T1 promotion checklist (per CLAUDE.md Goal #1)

For a (source, class) to be promoted to T2, ALL 5 axes must pass:
- [x] **Concentration** (max single-symbol share < 30%)
- [x] **Fat-tail** (top-3 wins < 30% of gross wins)
- [x] **OOS stability** (h1 PF >= 1.0 AND h2 PF >= 1.0)
- [x] **Batch artifact** (max single-date share < 35%)
- [x] **Binomial** (p < 0.05 vs 50% null)

**As of 2026-06-05, only 1 of 29 (source, class) candidates passes all 5: `mega_mutation::crypto`.**

---

## Cross-check vs walk-forward

Walk-forward (with `--require-macro-join` + `total_pf >= 1.0` hard-gate, per
PR `c7abecb289` and `7cd7586238`):

| Strategy | Walk-forward verdict | Scrutiny verdict | Reconciliation |
|----------|----------------------|------------------|----------------|
| `::crypto` (mega_mutation) | **PASS** (PF=2.58 n=166) | **5/5 PASS** (PF=3.16 n=295) | **CONSISTENT** |
| `luxalgo_confluence::crypto` | FAIL (PF=2.03, total=1.12, OOS_WR 46%) | 4/5 WATCHLIST (PF=1.06, n=2009) | borderline, n=2009 is misleading |
| `forex_rsi2_mean_reversion::forex` | FAIL (PF=1.93, total=1.10, OOS_WR 47%) | not in top-29 scrutiny | needs re-run |
| `futures_momentum::commodity` | FAIL (PF=1.39, total=0.93) | 2/5 FAIL | CONSISTENT |
| `myfxbook_retail_contrarian::forex` | FAIL (PF=2.50, total=0.96) | not scrutinized (n=321<scrutiny min) | needs scrutiny re-run |

**Reading:** The walk-forward PASS for `::crypto` is consistent with
scrutiny's 5/5 PASS for `mega_mutation::crypto`. The walk-forward FAIL for
`futures_momentum::commodity` is consistent with scrutiny's 2/5 FAIL. The
walk-forward + scrutiny verdicts now agree on the macro picture.

---

## Action items

### Day 0 (today, 2026-06-05)
- [x] Ship per-class T2 inventory (this report)
- [x] Per-class scrutiny post-filter: 1 PASS, 2 WATCH, 6 BORDERLINE, 20 FAIL
- [x] Walk-forward post-macro-join + hard-gate: 1 PASS (only ::crypto)
- [x] Deep-dive series on commodity, forex, bond
- [x] Live updates page entry on findtorontoevents.ca

### Day 7 (2026-06-12)
- [ ] Backfill `alpha_macro` to 2026-06-05 (DXY + VIX daily feed)
- [ ] Re-run per-class scrutiny with macro-join (move `luxalgo_confluence::crypto` from FAIL to re-evaluation)
- [ ] Identify a real BOND edge source (PIMCO replication, yield-curve momentum)
- [ ] Investigate the `luxalgo_confluence::crypto` n=767 vs scrutiny n=2009 discrepancy

### Day 30 (2026-07-05)
- [ ] Forward n for any surviving T2 candidate
- [ ] Re-evaluate WATCHLIST candidates with rolling forward n
- [ ] Cross-check vs DBMF / KMLM / QMOM / PIMCO (external replication)

---

## Author + verification

**Author:** claude (this session, 2026-06-05)
**Verifications:** All counts pulled live from `ejaguiar1_stocks.trading_picks`
via `tools.db_env.get_stocks_creds()`. SQL queries reproducible from
`tools/per_class_scrutiny_engine.py --min-n 30`.
**Cross-check vs memory:**
- [[backfill-data-quality-2026-06-05]] — backfill filter context
- [[project-data-quality-session3-2026-06-05]] — backfill root cause
- [[confidence-trust-edges-2026-05-31]] — 78.9% dispute
- [[money-ready-2026-05-31]] — money-ready bottleneck context
