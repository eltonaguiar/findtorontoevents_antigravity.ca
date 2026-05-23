# Statistical Edge Analysis — Per Asset Class
**Date:** 2026-05-16 (revised 2026-05-16T06:00Z) | **Source:** `audit_trail/data/universal_resolved_picks.json` (5000 picks)
**OOS split:** Pre-registered cutoff 2026-04-01 | IS n=830 (Feb-Mar), OOS n=4,170 (Apr-May, 46 days)
**Bootstrap:** 5,000-iteration CI on OOS PF; `audit_trail/edge_filter_bootstrap.py`
**Goal:** Identify and document proven OOS edge per system suitable for real-money allocation.
**Tier definitions:** Tier 1 (CI-lower ≥ 2.0, P(PF>1.5) ≥ 90%), Tier 2 (CI-lower ≥ 1.0, P(PF>1.5) ≥ 80%).

---

## Data Integrity Notes (READ FIRST)

1. **EQUITY mislabeling:** `signal_validation` labels 131 picks as EQUITY but all symbols are crypto tokens (BTC-USD, ETH-USD, ADA-USD, etc.). True stock picks are from `stocks_competition` (n=11) and `stocksunify2` (n=18, open). The "EQUITY" asset class in the dataset is unreliable.
2. **Ghost systems:** `multi_asset_cot`, `multi_asset_copytrader`, `claude_gainer`, `mega_mutation` have n=0 in `universal_resolved_picks.json`. Their dashboard stats (PF=4.72, etc.) come from `audit_dashboard/data/dashboard_data.json` (different data source, unvalidated OOS split). These systems are EXCLUDED from all OOS claims below.
3. **FOREX WR:** 60.6% applies to the 33 closed FOREX picks. 35 of 68 total FOREX picks have pnl_pct=0 (open/unresolved). The WR figure is correct on a closed-trades basis.
4. **COMMODITY:** No validated OOS data. All COMMODITY claims are from the live dashboard only.
5. **`stocks_competition` serial correlation:** AC1=0.74 → effective n ≈ 8 independent samples (not 53). The Tier 1 classification is statistically fragile. Treat as "promising but thin."

---

## Executive Summary — OOS-Validated Rankings

| System | OOS n | WR | OOS PF | CI-95-lo | CI-95-hi | P(PF>1.5) | AC1 | Tier |
|--------|-------|----|--------|----------|----------|-----------|-----|------|
| `kimi_signal_tracking` | 135 | 88.9% | 15.94 | 10.47 | 27.88 | 100% | -0.06 | ✅ TIER 1 |
| `aggregated_picks` | 383 | 78.1% | 7.02 | 5.71 | 8.71 | 100% | 0.24⚠ | ✅ TIER 1 |
| `stocks_competition` | 53 | 67.9% | 3.71 | 2.28 | 5.98 | 100% | 0.74⚠ | ✅ TIER 1* |
| `signal_validation` | 179 | 55.3% | 1.82 | 1.41 | 2.36 | 89.5% | 0.18 | ✅ TIER 2 |
| `rapid_fire` | 47 | 51.1% | 1.67 | 1.01 | 2.72 | 62.7% | 0.06 | ⚠️ MONITORING |
| `luxalgo_filters` | 350 | 41.4% | 1.39 | 1.15 | 1.67 | 24.4% | 0.21⚠ | ⚠️ MONITORING |
| `quan_engine` | 628 | 33.0% | 1.27 | 1.10 | 1.46 | 2.5% | 0.44⚠ | ⚠️ MONITORING |

*`stocks_competition` AC1=0.74 → effective independent n ≈ 8. Bootstrap CI is optimistic. Do not size as Tier 1 until more independent picks accumulate.

**Sub-floor (CI-lower < 1.0):** `dna_winner_picks`, `signal_engine_mutations`, `copy_trader_intel`, `copy_trader_highscore`, `dna_rapid_fire_mutations`, `ml_crypto_pred`, `claude_gainer_st`, `alpha_engine`, `mutation_lab`, `battleground`.

---

## Asset Class Deep Dives

### CRYPTO — Tier 1 elite systems ✅ (class-wide sub-floor)

**Class-wide OOS:** Dominated by sub-floor systems. Raw class PF ≈ 1.1 due to volume from `ml_crypto_pred` (n=837, PF=0.82), `dna_winner_picks` (n=388, PF=1.07), `alpha_engine` (n=307, PF=0.67).

**Elite-only (apply elite filter):**
| System | OOS n | OOS PF | CI-lower | Tier |
|--------|-------|--------|----------|------|
| `kimi_signal_tracking` | 135 | 15.94 | 10.47 | ✅ T1 |
| `aggregated_picks` | 383 | 7.02 | 5.71 | ✅ T1 |
| `signal_validation` | 179 | 1.82 | 1.41 | ✅ T2 |

**Weekly filter (building — CRYPTO):**
- source_system ∈ {`aggregated_picks`, `kimi_signal_tracking`, `signal_validation`}
- confidence ≥ 0.70 (tighter due to noise)
- risk_reward ≥ 2.0
- Max allocation: 0.5% per pick (Quarter-Kelly, building)
- **Expected OOS edge (filtered):** WR ~75%, PF ~4-8

**Promotion tracker:**
- `kimi_signal_tracking` n=135 OOS → promote to full Kelly when n≥200 clean picks
- `signal_validation` n=179 OOS → already Tier 2, consider upsizing to 1% when n≥250

---

### EQUITY — Thin but promising real stocks ⚠️

**Class-wide:** NOT meaningful. `signal_validation` EQUITY picks (n=112 OOS closed) are all crypto tokens mislabeled as EQUITY — do not use class-wide stats.

**True stock systems:**
| System | OOS n | OOS WR | OOS PF | Note |
|--------|-------|--------|--------|------|
| `stocks_competition` | 53 | 67.9% | 3.71 | AC1=0.74 → eff. n≈8 |
| `stocksunify2` | 18 (open) | — | — | All open, no pnl |

**Real-money status:** `stocks_competition` passes bootstrap CI on face value (CI-lower=2.28) but serial correlation (AC1=0.74) means true independent sample is ~8 trades. This is encouraging evidence but insufficient for full-Kelly sizing.

**Weekly filter (real-money cautious):**
- source_system = `stocks_competition`
- confidence ≥ 0.65, risk_reward ≥ 2.0
- asset_class check: verify symbol is a real stock ticker (not -USD suffix)
- **Max allocation: 0.75% per pick** (half Tier 2 rate until AC1 normalizes and n≥100 independent)

**Path to confidence:** Need ≥100 picks with AC1 < 0.3 (i.e., pick frequency must not cluster). At current emission rate with de-correlation → estimate 8-12 weeks.

---

### COMMODITY — No OOS validation ❌

**Status:** `multi_asset_cot` (dashboard PF=4.72) and `multi_asset_copytrader` (dashboard PF=3.14) have **n=0 in `universal_resolved_picks.json`**. Their stats come from live `dashboard_data.json` without a pre-registered OOS split.

**Do not size COMMODITY** until picks from these systems appear in the validated dataset with a pre-registered split. The dashboard numbers may be in-sample or survivorship-biased.

**Required action:** Confirm `multi_asset_cot` picks are being written to `alpha_engine/data/active_picks.json` and subsequently resolved to `universal_resolved_picks.json`. If not, the pipeline is broken.

---

### FOREX — Do not size (no Tier 2 system active) ❌

**Closed OOS picks:** 21 picks from `signal_validation` only. WR=60.6% on 21 closed (47.9% WR if zeros counted).

**Constraint:** FOREX picks from `signal_validation` are included in the FOREX count but `signal_validation`'s OOS edge is measured across all asset classes (PF=1.82 Tier 2). Too thin at n=21 to make FOREX-specific claims.

**Mutation plan:**
1. Route FOREX exclusively through `signal_validation` + `kimi_signal_tracking`
2. Stop `rapid_fire` from emitting FOREX picks (PF=1.67, WR=51% — borderline)
3. Accumulate 50+ closed FOREX picks from elite systems, then re-evaluate

---

### ETF / BOND — Insufficient data ❌

ETF: n < 10 in OOS. BOND: n < 5 in OOS. No statistical claims possible.

---

## Position Sizing — OOS-Validated (Quarter-Kelly)

| System | OOS PF | Kelly f* | Quarter-Kelly | MDD adj | AC1 adj | **Max per pick** |
|--------|--------|----------|---------------|---------|---------|-----------------|
| `kimi_signal_tracking` | 15.94 | ~40% | 10% | ×1.0 (MDD<5%) | ×1.0 | **1.0%** |
| `aggregated_picks` | 7.02 | ~25% | 6% | ×0.67 (MDD~35%) | ×0.75 | **0.75%** (CRYPTO) |
| `stocks_competition` | 3.71 | ~15% | 3.75% | ×1.0 | ×0.15 (AC1 adj) | **0.5%** (thin n) |
| `signal_validation` | 1.82 | ~10% | 2.5% | ×1.0 (MDD<10%) | ×1.0 | **0.5%** |
| `rapid_fire` | 1.67 | ~8% | 2% | monitoring | monitoring | **0%** (do not size yet) |

---

## Weekly Action Filter (Runnable)

```bash
# Run weekly filter to get elite picks
python tools/weekly_filter_picks.py --dry-run

# Save to JSON
python tools/weekly_filter_picks.py --output reports/weekly_picks_$(date +%Y-%m-%d).json

# Full OOS bootstrap (takes ~10 seconds)
python audit_trail/edge_filter_bootstrap.py --save reports/oos_validation_latest.md
```

---

## Systems to Kill (Post-Investigation Gate)

Per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`:

| System | OOS PF | OOS WR | n | Priority |
|--------|--------|--------|---|----------|
| `mutation_lab` | 0.19 | 10.3% | 39 | P0 — catastrophic |
| `battleground` | 0.00 | 0.0% | 27 | P0 — zero winners |
| `alpha_engine` | 0.67 | 30.0% | 307 | P1 — high volume drag |
| `claude_gainer_st` | 0.71 | 28.6% | 112 | P1 — sub-floor |

**Required before kill:** `python tools/mutation_analysis.py --system <name>` → export closed CSV → review `docs/MUTATION_THREE_AXIS_PROTOCOL.md` → check for profitable sub-strategies in `core_whitelist.json`.

---

## Promotion Roadmap

| System | Current n | Target n | Current Status | Promotion Criteria |
|--------|-----------|----------|----------------|-------------------|
| `stocks_competition` | 53 | 100 + AC1<0.3 | T1 fragile (AC1 high) | Independent n≥100, AC1 normalizes |
| `kimi_signal_tracking` | 135 | 200 | T1 ✅ | Upsizing when n≥200 |
| `signal_validation` | 179 | 250 | T2 ✅ | Increase alloc to 1% when n≥250 |
| `rapid_fire` | 47 | 100 | Monitoring | Full Tier 2 if CI-lower ≥ 1.5 at n=100 |
| `luxalgo_filters` | 350 | — | Monitoring | Needs P(PF>1.5) ≥ 80% — unlikely with WR=41% |

---

## Known Limitations

1. **OOS duration:** 46 days (Apr 1 - May 16) is in a single market regime (mild bull trend). Two-regime validation needs ≥6 months data.
2. **Serial correlation:** `aggregated_picks` AC1=0.24, `stocks_competition` AC1=0.74, `copy_trader_highscore` AC1=0.60. Bootstrap CI is optimistic for these systems — treat CI-lower as upper bound on true confidence.
3. **Asset class mislabeling:** `signal_validation` EQUITY picks are crypto. Class-level EQUITY stats are unreliable.
4. **No transaction cost model:** pnl_pct figures are simulator labels (bounded at [-3.41%, +4.0%]). Real spread + commission for crypto ≈ 0.1-0.2% round-trip. This reduces effective PF.
5. **COMMODITY unvalidated:** Two best COMMODITY systems (multi_asset_cot, multi_asset_copytrader) have zero picks in validated dataset.

---

## Follow-ups

- [ ] Confirm `multi_asset_cot` picks are being resolved to `universal_resolved_picks.json` (pipeline check)
- [ ] Investigate `stocks_competition` AC1=0.74 — is this clustering on the same underlying signal? If so, de-duplicate.
- [ ] Add transaction cost model: subtract 0.15% round-trip from all pnl_pct before computing PF
- [ ] Re-run OOS analysis when n≥100 for `stocks_competition` with AC1 checked
- [ ] Wire `luxalgo_filters` (n=350, PF=1.39, monitoring) into the weekly filter at 0% allocation for data accumulation

---

*NOT FINANCIAL ADVICE — research surface only.*
*OOS split pre-registered at 2026-04-01 before examining system performance.*
*Bootstrap: `audit_trail/edge_filter_bootstrap.py` (5,000 iterations, seed=42).*
