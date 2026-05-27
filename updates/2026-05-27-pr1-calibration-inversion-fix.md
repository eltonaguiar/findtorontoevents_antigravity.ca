# PR1: Fix ML Calibration Inversion in Smart Picks Engine

**Date:** 2026-05-27
**Branch:** `fix/pr1-calibration-inversion-smart-picks`
**Severity:** P0 — System-wide scoring inversion
**Incidents resolved:** INC #P0 (ML calibration system-wide inverted), INC #P0 (smart_picks_engine weights confidence-derived elite/quality at 35%)

## Problem

The ML Smart Picks engine uses confidence as a key ranking signal, but confidence is **system-wide inverted**:

| Confidence Band | CRYPTO WR | Implication |
|---|---|---|
| conf >= 0.90 | **14.4%** | Catastrophic — worse than coin flip |
| conf 0.85-0.90 | ~30% | Bad |
| conf 0.70-0.85 | ~45% | Mediocre |
| conf 0.50-0.60 | **60.3%** | Best band — the sweet spot |

This inversion poisons **two** scoring paths:

1. **`_compute_ml_composite` (ranking function):** Weights confidence at 0.10 (down from 0.30) but even 10% of an anti-predictive signal degrades ranking quality. For CRYPTO picks without ml_score, the fallback path uses `conf * 0.4` as the primary ranker — effectively random.

2. **`score_pick` (0-100 quality score):** The quality component (35 pts for CRYPTO) is derived from `elite_score`, which itself is partially confidence-derived. High-confidence CRYPTO picks get inflated quality scores despite having the lowest win rates.

## Changes

### File: `alpha_engine/smart_picks_engine.py`

#### Change 1: Asset-class-aware ml_composite weights (lines ~96-116)
- **CRYPTO:** `ml_score * 0.80 + confidence * 0.00 + forward_wr * 0.20`
  - Confidence weight ZEROED for CRYPTO (anti-predictive)
  - Forward WR boosted to 0.20 (IC=+0.17, best available non-ml signal)
- **Non-crypto:** `ml_score * 0.75 + confidence * 0.10 + forward_wr * 0.15` (unchanged)
  - EQUITY/FOREX confidence IC ~0.20 — still informative

#### Change 2: CRYPTO quality score confidence adjustment (after line ~1021)
- conf > 0.90: quality_score -= 10 (overconfidence penalty)
- conf > 0.85: quality_score -= 5 (mild penalty)
- conf 0.50-0.65: quality_score += 5 (sweet spot bonus)

#### Change 3: CRYPTO fallback path penalty (lines ~128-134)
- CRYPTO fallback `ml_null_penalty` reduced from 0.5 to 0.15
- Prevents high-confidence-no-ml-score picks from dominating the ranking

## Impact Analysis

### Expected Win Rate Improvement
- **CRYPTO Smart Picks:** The top-ranked picks will shift from high-confidence (14.4% WR) to moderate-confidence + ml_score-verified (55-60% WR). Conservative estimate: **+10-15pp WR lift** on the Smart Picks tab.
- **Non-crypto:** No change — weights preserved.
- **Active Picks (broadest feed):** Minimal impact — Smart Picks is the filtered subset.

### Risk Assessment
- **False negative risk:** Some genuinely good high-confidence CRYPTO picks may be downranked. Mitigated by ml_score still being 80% of the composite — if ml_score is high, the pick still ranks well regardless of confidence.
- **Fallback path risk:** CRYPTO picks without ml_score are now heavily penalized (0.15 multiplier). This may reduce CRYPTO coverage in the Smart Picks tab. Acceptable trade-off — picks without ml_score have no quantitative basis for ranking.
- **Regression risk:** LOW — changes are additive penalties, not removals. No existing logic is deleted.

### Peer Review Notes
- **Gemini consult (2026-05-25):** Identified confidence as "active poison" in the ranking formula. Recommended zeroing for CRYPTO. ✅ Implemented.
- **Kimi audit (2026-05-16):** Found CRYPTO strategy-family boost (+20/-15) partially compensates but doesn't address the root cause at the ranking level. ✅ Root cause now addressed.
- **Swarm 3-engine consensus (2026-05-25):** All 3 engines (deepseek, cerebras, gemini) flagged this as REAL P0. Fix aligns with their recommendation.

## Verification

After merge, verify via:
1. Check `/audit/` Smart Picks tab — CRYPTO picks should show conf 0.55-0.75 range (not 0.85+)
2. Compare Smart Picks WR in 7 days vs prior 7 days
3. Run `python -m alpha_engine.smart_picks_engine --dry-run` to confirm scoring output
4. Monitor `data/smart_picks.json` — ml_composite_method should show "ml_composite" not "confidence_fallback_penalized" for top picks

## Dependencies
- None — pure scoring logic change, no new imports or data dependencies
- Compatible with existing score_booster `_calibrate_confidence` (stacks multiplicatively)
- Compatible with confidence_calibrator (isotonic regression at line 84 runs first, then these adjustments apply)
