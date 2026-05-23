# Magic-Filter Hunt — 2026-05-18

**Prompt:** DAILY_IDEAS.MD Prompt C — find a consistently-profitable filtered slice per asset class, or prove none exists.
**Data source (canonical only):** `audit_dashboard/data/pf_registry.json` (generated 2026-05-18T20:45:46Z). Policy-clean-net views only. Raw `closed_picks.json` NOT used (pnl_pct unit-mismatch trap).
**Registry counts:** raw_rows 14677 → closed 12018 → after_flicker 12003 → deduped 7151 → **policy_clean_rows 1915**. dropped_duplicate_reemissions 4852, dropped_policy_excluded 5236.

## Class-level baseline (`by_asset_class_policy_clean_net`)

| Class | n | PF | WR | total_pnl_pct |
|---|---|---|---|---|
| CRYPTO | 1662 | 1.18 | 45.2% | 156.69 |
| FOREX | 144 | 1.64 | 57.6% | 0.12 |
| COMMODITY | 52 | 1.73 | 57.7% | 0.60 |
| UNKNOWN | 38 | 1.72 | 52.6% | 0.26 |
| FUTURES | 12 | 0.96 | 16.7% | -0.01 |
| EQUITY | 5 | 0.35 | 40.0% | -0.07 |
| BOND | 1 | 0.00 | 0.0% | -0.46 |
| PENNY_STOCK | 1 | 0.00 | 0.0% | -0.01 |

Only CRYPTO, FOREX, COMMODITY have enough policy-clean volume to slice (n≥30). EQUITY/FUTURES/BOND/PENNY_STOCK are below any meaningful filter threshold.

> Unit note: FOREX & COMMODITY `total_pnl_pct` are fractional-unit (gross_profit ≈ 0.2–1.4), not comparable in magnitude to CRYPTO. PF (a same-unit ratio) is still valid; absolute pnl is not.

---

## TASK 1 — Slices with n≥30 AND PF≥1.5

### View: `by_asset_class_strategy_policy_clean_net`

| Class | Strategy slice | n | PF | WR | pnl | W/L | Verdict |
|---|---|---|---|---|---|---|---|
| CRYPTO | ml_enhanced_DYDXUSDT_15m_D_ensemble_stack | 31 | 53.44 | 96.8% | 0.53 | 1.78 | **ARTIFACT** (ml_enhanced + near-zero-avg-loss placeholder) |
| CRYPTO | ml_enhanced_FETUSDT_1d_B_lightgbm | 44 | 9.25 | 56.8% | 7.56 | 7.03 | **ARTIFACT** (ml_enhanced + insane W/L 7.03) |
| CRYPTO | ml_enhanced_RENDERUSDT_1h_D_ensemble_stack | 47 | 3.80 | 61.7% | 1.59 | 2.36 | **ARTIFACT** (ml_enhanced family) |
| FOREX | cta_replicator | 95 | 2.69 | 66.3% | 0.12 | 1.36 | clean-candidate → see Task 4 |
| CRYPTO | mega_mutation | 72 | 2.19 | 56.9% | 110.39 | 1.66 | clean-candidate → see Task 4 |
| CRYPTO | ml_enhanced_RENDERUSDT_4h_D_ensemble_stack | 37 | 2.06 | 56.8% | 0.75 | 1.57 | **ARTIFACT** (ml_enhanced family) |
| COMMODITY | multi_asset_copytrader | 51 | 1.67 | 56.9% | 0.55 | 1.27 | clean-candidate → see Task 4 (FAILS) |

### View: `by_asset_class_strategy_symbol` (NOT policy-clean — pre-dedup; directional only)

| Class | Strategy / Symbol | n | PF | WR | W/L | Verdict |
|---|---|---|---|---|---|---|
| CRYPTO | ml_enhanced_DYDXUSDT.../DYDXUSDT | 31 | 60.54 | 96.8% | 2.02 | **ARTIFACT** placeholder |
| CRYPTO | ml_enhanced_FETUSDT.../FETUSDT | 44 | 9.43 | 56.8% | 7.16 | **ARTIFACT** insane W/L |
| CRYPTO | ml_enhanced_RENDERUSDT_1h.../RENDERUSDT | 47 | 3.94 | 61.7% | 2.45 | **ARTIFACT** ml_enhanced |
| FOREX | cta_replicator / USDJPY | 91 | 3.52 | 68.1% | 1.65 | clean ratio, but 86% of slice → see Task 4 |
| COMMODITY | multi_asset_copytrader / CT | 42 | 2.84 | 71.4% | 1.14 | **ARTIFACT** — CT=cotton, COT-leakage cohort |
| COMMODITY | multi_asset_cot / CT | 44 | 2.80 | 70.5% | 1.17 | **ARTIFACT** — `cot_positioning`-family on CT, COT-leakage |
| CRYPTO | ensemble / RENDERUSDT | 32 | 2.43 | 56.2% | 1.89 | clean-candidate → see Task 4 |
| CRYPTO | ml_enhanced_RENDERUSDT_4h.../RENDERUSDT | 37 | 2.12 | 56.8% | 1.62 | **ARTIFACT** ml_enhanced |
| CRYPTO | st_obv_support_divergence / AVAXUSDT | 34 | 1.96 | 50.0% | 1.84 | clean-candidate → see Task 4 |

### View: `by_asset_class_strategy_date` (n≥30, PF≥1.5)

All 8 hits are CRYPTO single-day buckets (one strategy on one calendar day). A single-day bucket is by definition NOT time-distributed — it is a same-day regime snapshot, not a filter. Listed for completeness, none qualify as a filter:
st_fear_greed_contrarian/2026-05-17 (n32 PF79 — W/L 5.27 insane → ARTIFACT), st_obv_support_divergence on 2026-05-01/02/03/04, quan_engine/2026-03-24 & /2026-04-07, st_bb_squeeze_expansion/2026-05-01.

No regime / score / FWD-WR / time-of-day bucket views exist in the registry — only strategy, strategy+symbol, strategy+date.

---

## TASK 2 — Artifacts excluded & flagged

- **`ml_enhanced_*` family** — 4 slices (DYDX, FET, 2×RENDER). Placeholder-stat family. DYDX additionally hits the near-zero-avg-loss placeholder pattern (PF 53, WR 96.8%). FET has an insane 7.0 W/L ratio. **All excluded.**
- **COT-leakage** — `multi_asset_copytrader/CT` and `multi_asset_cot/CT` (CT = cotton CT=F). CT=F is COMMODITY-blacklisted (Phase 2-D kill) and the COT-positioning family carries look-ahead leakage (gate M-095). **Both excluded.**
- **`st_fear_greed_contrarian/2026-05-17`** — PF 79, WR 93.8%, W/L 5.27: near-zero-avg-loss + insane W/L = placeholder pattern. **Excluded.**
- No `copy_trader_intel` 0%-WR cohort appeared at n≥30 in the policy-clean views (already dropped upstream by policy exclusion: 5236 rows dropped).

---

## TASK 3 — Inverse hunt (sub-1.0 PF classes: can removing ONE cohort flip it?)

| Class | PF | Verdict |
|---|---|---|
| EQUITY | 0.35 (n=5) | Not filterable — n too small. |
| FUTURES | 0.96 (n=12) | Single dominant strategy `multi_asset_scanner` n=11 PF 0.48; removing it leaves n=1. Not filterable. |
| BOND / PENNY_STOCK | 0.00 (n=1) | Single-row classes. Not filterable. |

CRYPTO (1.18) and FOREX/COMMODITY (>1.5) are already above 1.0, so the inverse hunt has no sub-1.0 class with enough volume to flip. **No corrupt-cohort-removal flip exists** — the broken classes are broken by sample-starvation, not by one bad cohort.

### Reverse inverse — the COMMODITY edge IS an artifact

The opposite finding is the load-bearing one. Removing the **CT (cotton)** cohort from COMMODITY:

- COMMODITY policy-clean baseline: n=52, PF 1.73.
- COMMODITY symbol view **excluding CT**: n=95, gross_profit 0.613 / gross_loss 2.627 → **PF 0.23**.

COMMODITY's entire apparent edge is the CT cohort — which is the COT-leakage artifact. **Filter out the artifact and COMMODITY is PF 0.23. The class has no real edge.**

---

## TASK 4 — Concentration cross-check on clean candidates

| Candidate | n | PF | Date span | Distinct days | Top-symbol share | Verdict |
|---|---|---|---|---|---|---|
| FOREX/cta_replicator | 95 (106 in date view) | 2.69 | 2026-04-23 → 05-18 | 18 | **USDJPY 86%** | Symbol-concentrated FAIL |
| COMMODITY/multi_asset_copytrader | 51–52 | 1.67 | 2026-04-23 → 05-18 | 15 | **CT 81%** (CT=cotton, COT-leak) | Artifact FAIL |
| CRYPTO/mega_mutation | 72 | 2.19 | 2026-03-13 → 05-17 | 27 | AVAX 17% (well-spread) | Survives concentration; see verdict |
| CRYPTO/ensemble (RENDERUSDT slice) | 32 (parent n=410) | 2.43 (slice) | 2026-02-25 → 05-17 | 64 | single-symbol slice | Single-symbol slice of a parent at PF 1.47 |
| CRYPTO/st_obv_support_divergence (AVAX slice) | 34 | 1.96 | 2026-04-30 → 05-18 | 19 | single-symbol slice | Single-symbol slice; parent strategy not in clean-net |

- **FOREX/cta_replicator** — 86% USDJPY. Fails the >50%-one-symbol rule. The strategy *is* a USDJPY trade. Date-distributed (18 days over ~4 weeks) but the edge is one currency pair, not a filter.
- **COMMODITY/multi_asset_copytrader** — 81% CT. Fails both the artifact rule (COT leakage) and >50%-one-symbol. Removing CT → PF 0.23 (Task 3).
- **CRYPTO/mega_mutation** — best-distributed candidate: n=72, PF 2.19, 27 distinct days across 2 months (Mar 13 → May 17), top symbol AVAX only 17%. W/L 1.66 (sane). Per-day pnl positive on 18/27 days. **This is the only slice that survives all four artifact/concentration screens.**
- **CRYPTO/ensemble** parent (n=410, PF 1.47, 64 days) is time-distributed and well-diversified but PF 1.47 is *below* the 1.5 bar. Its RENDERUSDT sub-slice (PF 2.43) is a single-symbol cherry-pick, not a filter.

---

## TASK 5 — Honest verdict per asset class

| Class | Real, non-artifact, time-distributed profitable filter? |
|---|---|
| **CRYPTO** | **MARGINAL YES — one slice.** `strategy = mega_mutation` is the only n≥30 / PF≥1.5 slice that survives every screen: n=72, PF 2.19, WR 56.9%, W/L 1.66, 27 trading days over 2 months, max symbol share 17%. Caveat: n=72 is modest and PF≥1.5 with n=72 has wide confidence bands; treat as a *candidate to size small and monitor*, not a proven edge. Filter rule: `asset_class==CRYPTO AND strategy=='mega_mutation'`. |
| **FOREX** | **NO.** Class PF 1.64 but the only PF≥1.5 strategy (`cta_replicator`, PF 2.69) is 86% USDJPY — a single-pair bet, not a filter. No symbol-diversified, n≥30 profitable slice exists. |
| **COMMODITY** | **NO.** Class PF 1.73 is an illusion: 81% of the volume is the CT (cotton) cohort, which is a COT-leakage / blacklisted artifact. Strip CT → PF 0.23. No real edge. |
| **EQUITY** | **NO.** n=5, PF 0.35. Insufficient data; nothing to filter. |
| **FUTURES** | **NO.** n=12, PF 0.96, dominated by one strategy at PF 0.48. Sample-starved. |
| **BOND** | **NO.** n=1. |
| **PENNY_STOCK** | **NO.** n=1. |
| **UNKNOWN** | **NO.** n=38, PF 1.72 at class level but no n≥30 strategy/symbol sub-slice clears PF≥1.5; UNKNOWN is an un-tagged residue, not a tradeable class. |

### Bottom line

Out of 8 asset classes, **one marginal filter exists** (CRYPTO / `mega_mutation`, PF 2.19, n=72, time- and symbol-distributed). Every other apparently-profitable slice is either (a) an `ml_enhanced_*` / placeholder artifact, (b) the COT-leakage CT cohort, or (c) a single-symbol concentration (FOREX→USDJPY). **No corrupt-cohort-removal flip turns a losing class into a winner** — the losing classes lose from sample-starvation, not from one removable bad cohort. The one removal that *does* matter works in reverse: stripping the CT artifact exposes COMMODITY as PF 0.23.
