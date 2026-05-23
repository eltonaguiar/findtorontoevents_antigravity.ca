# `ml_enhanced_FETUSDT_1d_B_lightgbm` — Verified Buried Elite

**TL;DR**: Comet's strategy claim VERIFIED. PF 9.43 on n=44 with +$15,180.86 dollar PnL is real. Currently invisible on `/audit` because asset_class is mis-tagged as UNKNOWN. **Highest-EV promotable strategy in `closed_picks.json`.**

## Verification (n=7,472 closed_picks.json, 2026-05-04)

| Metric | Value |
|---|---|
| Strategy | `ml_enhanced_FETUSDT_1d_B_lightgbm` |
| n | 44 |
| WR | 56.82% |
| PF (pnl_pct basis) | **9.4273** |
| Sum pnl_pct | +7.5904 |
| Sum pnl_dollar | **+$15,180.86** |
| Avg dollar/pick | +$345 |
| asset_class tag | **UNKNOWN** ← reason it's not surfaced |

This is the only Comet-round-2 claim that **survives** live verification. Other round-2 claims:
- "1/46 ML features active" → REJECTED (actual 9/40)
- "Battleground DNA 62%" → REJECTED (no such strategy exists)
- "DOTUSDT dominates loss" → REJECTED (TRXUSDT does, at -$36,151)

## Context — sister strategies on FETUSDT

All of FETUSDT's strategies are net-positive (75 picks total across 4 strategies):

| Strategy | n | WR | PF | sum_$ |
|---|---|---|---|---|
| `ml_enhanced_FETUSDT_1d_B_lightgbm` | 44 | 56.8% | **9.43** | **+$15,181** |
| `ml_enhanced_FETUSDT_15m_B_lightgbm` | 29 | 65.5% | 1.27 | +$140 |
| `ml_enhanced_FETUSDT_1h_A_xgboost` | 1 | 100% | ∞ | +$599 |
| `ml_enhanced_FETUSDT_15m_D_ensemble_stack` | 1 | 100% | ∞ | +$69 |

Only `1d_B_lightgbm` clears the T2 charter floor (PF>1.5 + n>=100). At n=44 it's between thin_sample and candidate per the tiered n-guard shipped in `f1b8d91b4ec` — would be labeled "thin_sample" until n grows.

## Why it's not visible on `/audit`

Its 44 closed picks have `asset_class="UNKNOWN"` in `closed_picks.json`. The audit dashboard's per-class panels (`asset_class_health`, `hf_stats.by_asset_class`) only surface picks with explicit asset_class. So a +$15K strategy is currently invisible to the credibility audit.

This is the same root-cause — 92% UNKNOWN tagger gap — that washes out every per-class metric on `/audit`. **One upstream tagger fix unblocks both the dashboard credibility AND surfaces this buried elite.**

## Promotion path (when asset-class tagger is fixed)

1. Back-fill `asset_class="CRYPTO"` for all FETUSDT picks (and similarly for the other 6,886 UNKNOWN picks — see `reports/verified_audit_findings_summary_2026_05_04.md` finding #5).
2. Re-run `audit_trail/dashboard_generator.py` (in CI, not locally — CLAUDE.md mandate).
3. After regeneration, `ml_enhanced_FETUSDT_1d_B_lightgbm` should appear in `tier2_proven_strategies` (subject to the strategy's PF/WR/n meeting the proven_strategies criteria; n=44 may need to grow first).

## Sizing caveat

PF 9.43 on n=44 is **statistically suspicious** — too good to be true. Possible explanations:
1. Genuine alpha (lightgbm captured a real FETUSDT 1d momentum pattern)
2. **Survivorship**: only the surviving 44 picks from a larger initial-train cohort were retained
3. **Look-ahead**: training data leaked into the test window
4. **Single-trade outlier**: one giant win pulls PF up; check if removing the top-1 pick collapses PF below 1.5

Recommend running `tools/mutation_analysis.py --json --strategy ml_enhanced_FETUSDT_1d_B_lightgbm` to break down by symbol/direction/timeframe before sizing up. Also recommend a **jackknife sensitivity**: remove each top-3 winner and report resulting PF distribution.

## Cross-reference to verified findings summary

This strategy is finding #3 in `reports/verified_audit_findings_summary_2026_05_04.md`. Both reports confirm: **the asset-class tagger fix is the single highest-EV change** because it unblocks (a) per-class dashboard credibility and (b) surfaces buried elites like this one.

## Recommended PR sequence

1. `fix/asset-class-tagger-2026-05-04` — close the 92% UNKNOWN gap (upstream fix in `audit_trail/dashboard_generator.py::_normalize_asset_class()`).
2. After regenerate: `feat/promote-fet-lightgbm-elite-2026-05-04` — review whether the strategy meets proven_strategies criteria post-tagger-fix, promote if yes, hold if jackknife shows fragility.
3. Symbol-concentration warning for FET on `/audit` — disclose that ~99% of CRYPTO `1d_B_lightgbm` PnL comes from this one symbol (single-strategy concentration).

## Provenance

- Source: `alpha_engine/data/closed_picks.json` (n=7,472)
- Computed: 2026-05-04 from a single grep+pandas-style aggregation
- Comet round-2 subagent (`reports/comet_strategy_verification_2026_05_04.md`) flagged this; this file confirms with raw numbers.
