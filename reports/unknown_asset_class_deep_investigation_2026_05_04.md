# UNKNOWN Asset-Class Deep Investigation — 2026-05-04

## TL;DR

The 6,886 "UNKNOWN" picks (92.2% of `closed_picks.json`) actually have `asset_class=null` (Python None / JSON null), not the literal string "UNKNOWN". They are **99.9% CRYPTO** and easily back-fillable by symbol-suffix heuristic. The investigation surfaced **5 buried elite strategies** (combined +$29K dollar PnL) and **5 buried disasters** (combined -$54K).

The single highest-EV upstream fix is in `audit_trail/dashboard_generator.py` — populate `asset_class` for `quan_engine_scalp` picks (5,293 of the 6,886 null-class) and the other ML-enhanced symbol-specific strategies.

## Verification (closed_picks.json, n=7,472, 2026-05-04)

```
Total picks:                7,472
asset_class is null:        6,886 (92.2%)
asset_class is "FOREX":       449
asset_class is "COMMODITY":    74
asset_class is "FUTURES":      31
asset_class is "EQUITY":       28
asset_class is "CRYPTO":        3
asset_class is "STOCKS":        1
```

Note: only **3 picks** are explicitly tagged "CRYPTO" — the rest of the crypto book is nulled.

## Heuristic backfill plan

Symbol-suffix classification of the 6,886 null-class picks:

| Heuristic class | n | % of null-class |
|---|---|---|
| **CRYPTO** (USDT/USDC/BUSD/USD/PERP suffix) | **6,881** | **99.93%** |
| FUTURES (=F suffix) | 2 | 0.03% |
| EQUITY (1-5 char ticker) | 2 | 0.03% |
| FOREX (=X suffix) | 1 | 0.01% |

Trivial back-fill: any symbol ending in `USDT|USDC|BUSD|USD|PERP` → asset_class="CRYPTO". This single rule covers 99.93% of the gap.

## Distribution of strategies emitting null-class

Top 10 strategies in null-class:

| Strategy | n |
|---|---|
| `quan_engine_scalp` | **5,293** |
| (empty/missing) | 468 |
| `quan_engine_swing` | 109 |
| `volume_spike_breakout` | 78 |
| `macd_rsi_confluence` | 66 |
| `ml_enhanced_RENDERUSDT_1h_D_ensemble_stack` | 47 |
| `ml_enhanced_FETUSDT_1d_B_lightgbm` | 44 |
| `ml_enhanced_RENDERUSDT_4h_D_ensemble_stack` | 37 |
| `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack` | 31 |
| `ml_enhanced_JTOUSDT_1d_B_lightgbm` | 30 |

So the bulk fix is on `quan_engine_scalp` — fixing its asset-class emission alone closes 77% of the gap. Add `quan_engine_swing` and the gap is 78%. Add the empty/missing-strategy backfill and 84%. The rest are individual ML-enhanced strategies that should also tag CRYPTO.

## Buried elites surfaced

Top strategies in null-class by dollar PnL (n>=20):

| Strategy | n | WR | PF | sum_$ |
|---|---|---|---|---|
| `ml_enhanced_FETUSDT_1d_B_lightgbm` | 44 | 56.8% | 9.43 | **+$15,181** |
| `ml_enhanced_INJUSDT_1d_B_lightgbm` | 28 | 96.4% | 41.52 | **+$8,106** |
| `ml_enhanced_RENDERUSDT_1h_D_ensemble_stack` | 47 | 61.7% | 3.94 | +$3,254 |
| `ml_enhanced_RENDERUSDT_4h_D_ensemble_stack` | 37 | 56.8% | 2.12 | +$1,552 |
| `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack` | 31 | 96.8% | 60.54 | +$1,119 |

**Combined: +$29,212 across 187 picks. None of these are visible on `/audit` because of the tagger gap.**

WR 96.4% / PF 41.52 (INJUSDT) and WR 96.8% / PF 60.54 (DYDXUSDT) are statistically suspicious (look-ahead bias / survivorship). Recommend jackknife sensitivity before promotion.

## Buried disasters surfaced

Worst strategies in null-class by dollar PnL (n>=20):

| Strategy | n | WR | PF | sum_$ |
|---|---|---|---|---|
| `ml_enhanced_TRXUSDT_1d_B_lightgbm` | 26 | 11.5% | 0.00 | **-$33,094** |
| `ml_enhanced_APEUSDT_1d_D_ensemble_stack` | 30 | 33.3% | 0.05 | **-$17,237** |
| `ml_enhanced_JTOUSDT_1d_B_lightgbm` | 30 | 36.7% | 0.30 | -$2,888 |
| `ml_enhanced_HBARUSDT_1d_D_ensemble_stack` | 28 | 42.9% | 0.29 | -$928 |
| `ml_enhanced_ALGOUSDT_15m_B_lightgbm` | 26 | 50.0% | 0.41 | -$700 |

**Combined: -$54,847 across 140 picks.** The TRXUSDT one (11.5% WR, PF 0.00 — every loss bigger than every win) is an exceptionally bad strategy that's been bleeding cash invisibly.

## The bimodal `ml_enhanced_*_1d_B_lightgbm` family

Note that the SAME architecture (1d_B_lightgbm) works on some symbols and catastrophically fails on others:

| Symbol | WR | PF | sum_$ |
|---|---|---|---|
| INJUSDT | 96.4% | 41.52 | +$8,106 |
| FETUSDT | 56.8% | 9.43 | +$15,181 |
| TRXUSDT | 11.5% | 0.00 | -$33,094 |
| JTOUSDT | 36.7% | 0.30 | -$2,888 |

This is the **ML-strategy-symbol-fit** pattern — a single model architecture trained per-symbol has wildly different out-of-sample performance. Per CLAUDE.md mutate-before-kill, this argues for **per-(strategy × symbol) gating** rather than blanket strategy bans.

## Recommended PR sequence

1. **`fix/asset-class-tagger-2026-05-04`** — add a `_normalize_asset_class()` helper that backfills null asset_class via symbol suffix (USDT→CRYPTO etc.). Apply at pick-emission time in `quan_engine_scalp`, `quan_engine_swing`, `volume_spike_breakout`, `macd_rsi_confluence`, and the `ml_enhanced_*` strategies. Single highest-EV change. Closes 99.9% of the null-class gap.

2. **`block/strategy-trxusdt-1d-lightgbm-2026-05-04`** — block `ml_enhanced_TRXUSDT_1d_B_lightgbm` specifically (-$33,094 in 26 picks; PF 0.00). Strategy-specific kill, not symbol-wide. Per CLAUDE.md mutate-before-kill, run `tools/mutation_analysis.py --json --strategy ml_enhanced_TRXUSDT_1d_B_lightgbm` first to confirm.

3. **`block/strategy-apeusdt-1d-ensemble-2026-05-04`** — block `ml_enhanced_APEUSDT_1d_D_ensemble_stack` (-$17,237 in 30 picks; PF 0.05).

4. **`feat/audit-promote-buried-elites-2026-05-04`** — surface the 5 buried elite strategies on `/audit` after the tagger fix lands. Apply jackknife sensitivity check on PF>20 strategies before public display.

5. **`fix/quan-engine-asset-class-emission-2026-05-04`** — root-cause fix in the `quan_engine_scalp` pick generator to emit `asset_class="CRYPTO"` directly (not just rely on downstream backfill).

## Cross-references

- `reports/fetusdt_buried_elite_2026_05_04.md` — focused FETUSDT verification
- `reports/verified_audit_findings_summary_2026_05_04.md` — master finding #5 (tagger gap)
- `reports/comet_strategy_verification_2026_05_04.md` — TRXUSDT loss verified at -$36,151 (broader scope incl. quan_engine_scalp)
- `reports/super_swarm_synthesis_2026_05_04.md` — original AHF-04 / hf_stats vs asset_class_health divergence is a downstream symptom of this same gap

## Provenance

- Source: `alpha_engine/data/closed_picks.json` (mtime 2026-05-04, 19 MB, 7,472 picks)
- Computed: 2026-05-04 via single Python aggregation (no external services)
- Heuristic was kept conservative: only suffix-based symbol classification, no NLP guesses
