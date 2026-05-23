# MMR Audit + Synthesis Corrections — 2026-05-14

Supersedes specific claims in `reports/money_maker_ready_20260514T001749Z.md` (PR #986) and `reports/mmr_round2_synthesis_2026-05-14.md` (PR #996) per pr-reviewer findings 2026-05-14. Original reports preserved as historical record; this doc carries the verified-correct numbers.

Source: `audit_dashboard/data/dashboard_data.json` generated_at `2026-05-13T23:19:53Z` (the same snapshot both originals reference, just re-read with correct field names).

## 1. B3 drift — DOWNGRADE from blocker, UPGRADE to P0 auto-pause

**Original audit claim (PR #986 §6, PR #996 §1.B3):** "ks_d / ks_critical are None" — described as a writer-bug / field-name mismatch blocker.

**Verified correct:**
```
hf_stats.concept_drift = {
  "ks_D": 0.312576,
  "ks_critical_05": 0.047292,
  "distribution_shift": True,
  "drift_alert": True,
  "early_n": 1654,
  "late_n": 1654
}
```

Both stats ARE populated. The bug was IN MY AUDIT — I read lowercase `ks_d` / `ks_critical` (which don't exist in the schema). Correct field names are uppercase `ks_D` + `ks_critical_05` (the latter denoting the 0.05 critical-value variant).

**Recomputed verdict:**
- D / critical = 0.312576 / 0.047292 = **6.61** = SEVERE per spec threshold (>5).
- Skill spec Step 7: "recommend auto-pause sizing if D > 0.10". D=0.31 is **3x the auto-pause threshold**.
- **Action: P0 auto-pause new sizing.** Original audit's "do NOT auto-pause" recommendation was INVERTED.

## 2. Asset-class baseline (§1 of original audit) — fill in resolved_n

The skill's hard rule is `(asset_class | n | timeframe)` on every claim. Original §1 showed `n?` placeholders. Verified values from `asset_class_health.resolved_n`:

| Class | resolved_n | WR (%) | PF |
|---|---|---|---|
| CRYPTO | **8025** | 46.5 | 1.34 |
| EQUITY | **416** | 51.4 | 1.55 |
| COMMODITY | **281** | 70.5 | 4.03 |
| ETF | **106** | 56.6 | 1.41 |
| FOREX | **438** | 41.8 | 0.63 |
| BOND | **11** | 54.5 | 0.66 |
| FUTURES | **0** | 0.0 | n/a |

Note: BOND n=11 not n=12 as originally stated. CRYPTO WR 46.5 / PF 1.34 (originals had 46.4 / 1.33 — small rounding).

## 3. CRYPTO walkforward (§2)

| | Original | Verified |
|---|---|---|
| oos_wr | 45.2% | **45.4%** |
| oos_sharpe | 1.74 | **1.818** |

## 4. alpha_engine_fast drag attribution (PR #996 §1.CRYPTO)

| Stat | Original | Verified |
|---|---|---|
| Volume share of CRYPTO | "0.2% (negligible)" | **~3% (n=299 of CRYPTO 8025) — material drag** |
| WR | — | 43.2% |
| PF | — | 0.62 |
| Block status | (not stated) | Already blocked CRYPTO/BOND/COMMODITY via `BLOCKED_ASSET_SOURCE_PAIRS` (quality_gates.py:1825-1827) |

The "0.2% negligible" framing was wrong by ~15×. At n=299 / PF 0.62, alpha_engine_fast contributes a real drag that the existing block partially mitigates (3 asset classes) but does NOT eliminate (any non-blocked class still emits).

## 5. §4 draggers — missed entries

Reviewer noted §4 table truncated at 6 rows. Full top-10 by negative pnl_pct (filter: PF<0.5 OR pnl<-50%, n>=20):

Added missed entries from original list:
- **crypto_winners** — n=49, WR 30.6%, PF 0.39, pnl -49.2%. P1 investigate per `MUTATION_THREE_AXIS_PROTOCOL.md`.
- ml_bg_system_a — n=19, PF 0.14, pnl -49.8% (already in BLOCKED_SOURCE_SYSTEMS line ~1360)
- ml_bg_system_b — n=19, PF 0.02, pnl -54.7% (already in BLOCKED_SOURCE_SYSTEMS line ~1361)

## 6. §9 top edges — "missed by swarm" recharacterization

Reviewer caught: 2 of the 5 "missed candidates" already exist in repo. Re-classified:

| Candidate | Original claim | Actual state |
|---|---|---|
| CRYPTO basis trade | "biggest miss" | `alpha_engine/basis_strategies.py::generate_funding_arbitrage_signals` + `alpha_engine/mercury_ai_strategies.py::spot_perp_basis_arb`. Latter is in `scanner.py::STRATEGY_REGIME_MAP` line 1073 and has 3 resolved picks. Real gap: **scaling / tuning**, not wiring. |
| FUTURES VIX contango roll | "critical miss" | `alpha_engine/untapped_strategies.py:1309::vix_term_structure_signal` registered in `UNTAPPED_STRATEGIES` dict (claimed WR 83.3%) and merged into the live strategy pool via `scanner.py:341`. Real gap: **scaling / verification**, not wiring. |
| EQUITY put-writing on SPY/QQQ | "biggest miss" | TRUE miss — no options strategies in repo. Stays P1. |
| ETF TLT put spreads | "miss" | TRUE miss — same options gap. P2. |
| COMMODITY CL=F calendar spread | "miss" | TRUE miss — CL=F outright blocked but no calendar surfaces exist. P4. |

## 7. ONDOUSDT × quan_engine (PR #996 §1.CRYPTO)

| Stat | Original | Verified (full recent_closed) |
|---|---|---|
| n | 128 | **187** |
| WR | 64.1% | **46.0%** |

The original 128/64.1% claim is untraceable. Full recent_closed shows ONDOUSDT × quan_engine at sub-floor WR. **Drop from "top unexploited edge" list** — this is not an edge.

## 8. COMMODITY non-COT subset (PR #996 §1.COMMODITY)

Reviewer claimed n=38 / WR 55.3% / PF 4.11 from a different filter. My recompute with `'cot' not in strategy AND 'cot' not in source_system` filter on recent_closed gives:

```
Non-COT COMMODITY: n=15, W=4, L=11, WR=26.7%, PF=1.73
```

Different from BOTH the synthesis (n=15 / WR 20% / PF 0.88) AND reviewer (n=38 / WR 55.3% / PF 4.11). Filter-definition divergence — none is wrong; they answer different questions. **Conservative reading: small-n any way you slice it.** "All 3 COMMODITY candidates are traps" verdict stands on n-starvation grounds independent of which non-COT WR is canonical.

## 9. Revised verdict gate

Original §10 said COMMODITY walkforward must show "neither stable nor decay" — vague. Reviewer correctly flagged as untestable.

**Replacement explicit gate:** COMMODITY walkforward (post-PR #993 + #1005) must show:
- `oos_wr >= 50%`
- `decay >= 0` (positive = OOS improves over IS)
- `consistency >= 70%`
- `folds >= 3` (after the n-floor=30 check in PR #1005 passes)

Tied to Charter Tier-2 floor.

## 10. Real-money green-light checklist (current as of 2026-05-14)

| Gate | Status |
|---|---|
| ✅ Pass §1 Tier-2 floor | 5/129 systems do |
| ❌ Pass §2 walkforward all classes | 4/7 today (CRYPTO, EQUITY, ETF, FOREX). Adding BOND/FUTURES requires PR #993 merge **and** PR #1005 n-floor gate. |
| ❌ §3 multi_asset_cot audit closed | Pending PR #994 merge |
| ✅ §4 P0 draggers quarantined | HYPE blocked PR #974; breakout_b_ml + kimi_claw_research PR #1002 in flight |
| ⏳ §5 baby_strats surgical quarantine | Template exists, not yet shipped |
| 🚨 §6 drift status | **D=0.31 / critical=0.047 / D/critical=6.6 SEVERE — auto-pause new sizing NOW per spec** |
| ⏳ §7 UI High-Conviction filter audit | P2 — memory: 0.90+ conf = 22.2% WR trap; not yet verified in template.html |
| ⏳ §8 risk-cap (Riskfolio-Lib) | P3 — not started |

**Verdict update:** NOT ready for real-money. Adding to original list: **§6 drift alert is severity-SEVERE and requires auto-pause per spec, not "do NOT auto-pause" as originally written.** This is the single most important correction in this addendum.

## Refs
- Original audit: `reports/money_maker_ready_20260514T001749Z.md` (PR #986)
- Original synthesis: `reports/mmr_round2_synthesis_2026-05-14.md` (PR #996)
- 5 pr-reviewer transcripts in `C:\Users\zerou\AppData\Local\Temp\claude\…\tasks\*.output`
- Skill spec: `.claude/skills/money-maker-ready/SKILL.md`
