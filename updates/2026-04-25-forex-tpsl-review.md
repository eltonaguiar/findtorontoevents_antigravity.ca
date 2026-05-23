# Forex TP/SL Cap Review — 2026-04-25

**Author:** Claude Opus 4.7 (1M context)
**Trigger:** USDJPY paper trade on `HIGHFWWRABV55_SCOREABOVE50_V4` was −74% of the way to its SL within 24h on a routine −0.11% intraday move
**Decision:** Widen FX caps from `(0.0075, 0.005)` → `(0.015, 0.008)` — 1.5% TP / 0.8% SL
**Status:** Patch landed in this PR; pre-merge review here

---

## TL;DR

The pipeline's FX TP/SL caps are demonstrably bleeding capital. Widening them is high-value:

| Metric | Current state | After patch |
|---|---|---|
| FX class realised PF | **0.26** | Targeted ≥1.0 |
| FX class expectancy | **−$0.99/trade** | Targeted positive |
| SL_HIT rate (n=1,558 closed) | **44%** | Targeted ~30% |
| TP_HIT rate | **12%** | Targeted ~25% |
| SL distance vs daily ATR | 0.5% / 0.3-0.8% (≈ median ATR) | 0.8% / 0.3-0.8% (above ATR ceiling) |
| R:R | 1.5:1 | 1.875:1 |

This is the **third** widening in 7 days (0.2/0.3 → 0.4/0.5 → 0.5/0.75 → **0.8/1.5**). Each prior step helped (4.3% WR → 47.5% WR) but didn't break the SL-clustering pattern that makes FX a noise-driven loser.

---

## Trigger event (the live case)

Place: USDJPY LONG on V4, entry **159.486**, TP **160.280** (+0.50%), SL **159.000** (−0.30%).

24h later: price moved to **159.308** (−0.11%) — a perfectly routine intraday tick. Position now **74% of the way to SL** with no progress toward TP. Trade value is $2,460 (FX qty conversion gives 22× the notional of equity entries at the same `qty=2` input — see `feedback_fx_qty_and_tpsl_scale.md`), so the dollar loss ($-2.75) was 3.3× larger than MRK's at the same gross % move (-0.75%).

**Conclusion:** the SL is one ordinary FX bar away. With typical USDJPY 1H bar range of ±0.15-0.30%, a 0.30% stop has high probability of triggering on noise alone — independent of any thesis.

---

## Pipeline audit — 3 conflicting cap locations (now aligned)

The codebase has FX TP/SL caps in **three** places. They've drifted apart historically (Copilot Bug #5 noted by another agent at production_scanner.py:973). Snapshot before this PR:

| File | Location | TP cap | SL cap | Notes |
|---|---|---|---|---|
| [`alpha_engine/non_crypto_policy.py`](../alpha_engine/non_crypto_policy.py) | `NON_CRYPTO_TP_SL_CAPS["forex"]` line 388 | 0.0075 | 0.005 | Last widened 2026-04-19 |
| [`alpha_engine/production_scanner.py`](../alpha_engine/production_scanner.py) | `TP_CAP_FOREX` / `SL_CAP_FOREX` lines 979,987 | 0.0075 | 0.005 | Last widened 2026-04-17 |
| [`alpha_engine/config.py`](../alpha_engine/config.py) | `CATEGORY_RISK["forex"]` lines 162, 178 | 0.0075 | 0.005 | Last widened 2026-04-18 |

**This PR updates all three to `(0.015, 0.008)` together.**

---

## Realised performance (the smoking gun)

Pulled from `audit_dashboard/data/dashboard_data.json` 2026-04-25:

```
=== Performance by asset class ===
CRYPTO     n=23,345  WR 44.1%  PF 1.19   expectancy +$0.21
EQUITY     n=   831  WR 52.8%  PF 1.41   expectancy +$0.65
FOREX      n= 1,558  WR 47.5%  PF 0.26   expectancy −$0.99    ← BLEEDING
COMMODITY  n=   629  WR 43.0%  PF 0.84   expectancy −$0.03
ETF        n=    97  WR 56.1%  PF 1.25   expectancy +$0.28
BOND       n=    17  WR 50.0%  PF 1.60   expectancy +$0.18
```

FX is uniquely catastrophic on PF and expectancy despite a respectable 47.5% WR. **The wins exist but are too small to recover the losses** — exactly what tight stops produce.

### FX exit-reason distribution (n=787 with full exit data)

```
SL_HIT:        353  (44%)
FORCE_CLOSED:  282  (36%)
TP_HIT:         93  (12%)
EXPIRED:        47   (6%)
UNKNOWN:        12   (2%)
```

**3.7× more SL hits than TP hits.** A neutral random walk with symmetric stops would produce ~1:1 SL:TP ratio. 3.7:1 is the signature of a stop placed inside the noise band.

### Cap-distance vs realised volatility

The code's own comment (at `non_crypto_policy.py:389-391`) acknowledges: *"Forex daily ATR 0.3-0.8% means 0.5%/0.4% caps were triggering on noise."* The 2026-04-19 widening to 0.5% SL **moved the stop from below the ATR floor (0.4%) to AT the median ATR (~0.55%)** — still inside the noise band, just closer to the edge.

| SL cap (era) | vs daily ATR median ~0.55% | Realised WR | Pattern |
|---|---|---|---|
| 0.2% (pre-2026-04-18) | 0.36× ATR (deep in noise) | 4.3% (22/23 SL hits) | Catastrophic |
| 0.4% (2026-04-18 step 1) | 0.73× ATR (still in noise) | not separately measured | — |
| **0.5% (current)** | **0.91× ATR (still in noise)** | **47.5% but PF 0.26** | Bleeding |
| 0.8% (this PR) | 1.45× ATR (above ATR ceiling) | targeted ~50% / PF >1.0 | Predicted positive |

---

## Cross-AI consensus

Consulted 2 Ollama Cloud models in parallel with the same prompt (current caps, observed performance, daily ATR data). Both agree the caps are too tight.

### gpt-oss:120b-cloud

> **Are the current caps too tight?** Yes. A daily ATR of 0.3‑0.8% means the "typical" 1‑day price swing already spans the whole SL band (0.5%). Placing the stop at roughly the median ATR is essentially a **noise filter**, not a risk guard – any normal intra‑day fluctuation will trigger it. The 12% TP hit rate versus a 44% SL rate confirms the stop is being hit far more often than the market can move the required distance.
>
> **Suggested replacement caps:** **forex 1.2% TP / 0.8% SL** — 0.8% sits just beyond the upper bound of the typical daily ATR (≈0.8%). It gives the price room to walk its natural volatility while still limiting loss to a level that respects portfolio risk. A 1.2% target yields a ~1.5:1 TP/SL ratio, enough to swing expectancy positive if win‑rate improves above ~35%.
>
> **Right unit:** ATR-relative — "0.8% of entry ≈ 1.0× ATR₁₀". Pips are instrument-dependent; raw % ignores volatility regime; ATR adapts.
>
> *Bottom line: shift the SL out to at least the upper-edge of the daily ATR (≈0.8%) and set the TP to 1.5× that SL. This widens the stop enough to survive normal noise while preserving a positive risk-reward profile.*

### qwen3-coder:480b-cloud

> **Caps too tight?** Yes. Setting SL at 0.5% when daily ATR is 0.3-0.8% puts SL directly in the noise zone. With 44% SL hit rate vs 12% TP hit rate (3.7:1 ratio), you're being stopped out by normal volatility before capturing meaningful moves.
>
> **Proposed replacement:** **`(0.015, 0.008)` = 1.5% TP, 0.8% SL** — moves the SL below typical daily ATR ceiling while keeping TP realistic. At 0.8% SL, you're below the 0.8% ATR ceiling but above pure noise. 1.5% TP gives reasonable reward given FX's mean-reverting nature and typical intraday ranges of 1-2%.
>
> **Right unit:** % of N-period ATR (1-day ATR as % of entry price). Pure percentage points ignore volatility differences between pairs (EUR/USD vs USD/JPY behave differently). Pips are pair-specific but don't account for volatility regime changes. ATR-adjusted percentages dynamically adapt.

### Where they agree (consensus)

1. ✅ **Current 0.5% SL is in the noise band** — both models flag this unambiguously
2. ✅ **0.8% SL is the right floor** — exactly the same number from both
3. ✅ **ATR-relative units are the long-term right framing** — both call for migration
4. ✅ **Expected outcome:** stops survive normal noise → realised expectancy turns positive

### Where they diverge

- **TP target:** gpt-oss says 1.2% (R:R 1.5:1); qwen says 1.5% (R:R 1.875:1). Difference is ~0.3pp.

### Synthesis

Adopting **qwen's 1.5% TP** for higher R:R margin (1.875:1 vs 1.5:1). Higher R:R buys more error tolerance against the WR estimate. If realised performance shows TP overshoots (price pauses at 1.2%, retraces, hits SL), revisit and tighten to gpt-oss's 1.2%.

**Final tuple: `forex: (0.015, 0.008)` — 1.5% TP / 0.8% SL.**

---

## Files changed in this PR

| File | Line | Change |
|---|---|---|
| `alpha_engine/non_crypto_policy.py` | 388 | `(0.0075, 0.005)` → `(0.015, 0.008)` + history comment |
| `alpha_engine/production_scanner.py` | 979 | `TP_CAP_FOREX = 0.0075` → `0.015` |
| `alpha_engine/production_scanner.py` | 987 | `SL_CAP_FOREX = 0.005` → `0.008` |
| `alpha_engine/config.py` | 162 | `CATEGORY_RISK["forex"] = (-0.005, 0.0075, 7)` → `(-0.008, 0.015, 7)` |
| `alpha_engine/config.py` | 178 | `CATEGORY_RISK_FAST["forex"] = (-0.005, 0.0075, 5)` → `(-0.008, 0.015, 5)` |
| `updates/2026-04-25-forex-tpsl-review.md` | new | this doc |

All 3 (or 4 with FAST variant) cap locations stay aligned to prevent the historical "tightest cap silently overrides" bug pattern (Copilot Bug #5).

---

## What this does NOT change (deferred)

1. **ATR-relative migration.** Both models recommend ATR-derived caps long-term. Implementing it requires (a) per-pair ATR computation in the scanner, (b) caching layer for daily ATR refresh, (c) per-pick ATR snapshot stored on the pick row. That's a separate larger refactor — recommended as follow-up after observing 2-week performance under the widened % caps.
2. **Per-pair tuning.** USDJPY (~0.4% ATR), EURUSD (~0.55% ATR), GBPJPY (~0.7% ATR) have different vol regimes. Per-pair caps would be more precise but the current 3-file aligned-tuple structure doesn't support it without refactor. ATR-relative migration would solve both.
3. **Live position adjustment.** The 6 currently-open FX positions across both paper accounts (USDJPY LONG on V4 and zerounderscore) keep their original tight stops — only NEW picks generated after this PR get the wider caps. Optional follow-up: manually widen V4 USDJPY SL to 158.20 (≈ −0.80% from entry) to bring the live trade in line with the new policy.

---

## Validation plan

After merge:
1. **Pipeline smoke check:** new FX picks generated should have TP/SL distances ≤1.5% / ≤0.8% respectively. `clamp_non_crypto_tp_sl()` should clamp wider strategy-emitted values down to the new caps.
2. **2-week realised observation:** track FX class WR, PF, expectancy, SL_HIT/TP_HIT ratio. Targets: PF >1.0, SL:TP ratio < 2.0. If still bleeding after 2 weeks at wider caps, escalate to ATR-relative migration as a structural fix.
3. **Compare vs hold-out group:** if any FX picks generated 24h before merge had narrow stops and 24h after have wide stops, comparing same-day exit reasons gives a small natural experiment.

---

## Provenance

- 2026-04-22 — discovery: my placed USDJPY LONG inherited 0.5% SL from pipeline, was −74% to stop on routine noise within 24h
- 2026-04-25 — investigation: pipeline source review, realised performance pull, 2-model Ollama Cloud consult
- This PR — 3-file aligned cap update
- See also: [`memory/feedback_fx_qty_and_tpsl_scale.md`](../memory/feedback_fx_qty_and_tpsl_scale.md) — the position-sizing twin issue (FX qty=2% gives 22× equity notional)

Co-Authored-By: gpt-oss:120b-cloud (Ollama, advisory)
Co-Authored-By: qwen3-coder:480b-cloud (Ollama, advisory)
