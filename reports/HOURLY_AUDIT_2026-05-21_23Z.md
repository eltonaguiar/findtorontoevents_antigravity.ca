# Hourly Audit — 2026-05-21 23Z

**Dashboard snapshot:** `2026-05-21T22:45:32Z` ✅
**Generated:** 2026-05-21 ~23:00Z
**Session:** claude-sonnet-4-6

## Context (from issues #685 / #686 / #693)

- Issue #685: resolver-rescope DONE — do not re-open
- Issue #686: live per-asset regression tracker (FOREX recovery, EQUITY drift, CRYPTO improving)
- Issue #693: EQUITY 7d/14d/30d monotonic decline — closed 2026-05-13 post-PR-#692 (goldmine_6x kill)
- Today's merged PRs: #684 #674 #673 #664 #683 #687 #692 #694

## Per-asset snapshot (recent_closed n=3500)

| Class | PF (24h) | PF (7d) | WR (7d) | PF (30d) | vs Baseline | Delta vs 22Z |
|-------|----------|---------|---------|----------|-------------|--------------|
| CRYPTO | 1.757 | 1.412 | 48.4% | 1.322 | 7d +0.082 vs 1.33 | −0.021 |
| **EQUITY** | 0.300 | **0.654** | **30.8%** | 1.349 | 7d −0.233 from 0.87 | **−0.101 ↓** |
| FOREX | 1.434 | 1.359 | 30.0% | 2.572 | 7d +1.219 vs 0.14 pre-#687 | −0.092 |
| COMMODITY | 1.933 | 0.246 | 11.4% | 0.943 | 7d unchanged | 0.000 |
| ETF | 0.000 | 0.884 | 8.3% | 2.248 | stable | 0.000 |
| BOND | 0.000 | 0.000 | 0.0% | 0.000 | critical (n=5 too small) | — |

## asset_class_health (rolling, from dashboard_data.json)

| Class | PF | WR | n | Tier status |
|-------|----|----|---|-------------|
| CRYPTO | 1.355 | 48.2% | 1085 | Approaching T2 (PF>1.5 target) |
| EQUITY | 0.921 | 36.4% | 55 | Sub-T2 |
| FOREX | 1.368 | 53.5% | 155 | Approaching T2 (WR strong, PF needs lift) |
| COMMODITY | 1.296 | 50.8% | 61 | Approaching T2 |
| ETF | 11.995 | 50.0% | 2 | n too small to tier |

## PR Triage

| PR | Title | CI | Mergeable | Reviews | Action |
|----|-------|----|-----------|---------|--------|
| #1302 | audit 22Z FINDING-62 | 3/3 ✅ | clean | No REQUEST_CHANGES | **MERGED ✅** |
| #1301 | audit 21Z FINDING-60/61 | 3/3 ✅ | clean | No REQUEST_CHANGES | **MERGED ✅** |
| #1299 | chore(loop) LOOP_COMPLETE | 3/3 ✅ | **dirty** | — | HOLD — merge conflict |
| #1287 | feat(b10) UEPS KPI panel | test(3.11) FAILED | — | — | HOLD — CI failure |
| #1279 | docs AGENTS.md cloud note | — | — | — | HOLD — DRAFT |

**HOLD set (#660 #658 #681 #661):** all confirmed closed ✅

**Author-rebase PRs (#669 #676 #608 #665 #644 #597 #615 #655):** all confirmed merged/closed ✅

**Plan v2.1 guardrails:** no PR citing PF 5.81 / ml_score 0.90 / WINNER_FILTER found ✅

## Mutation Analysis (python tools/mutation_analysis.py --json)

**No new strategies with PF<0.5 + n≥20 found this cycle.** Threshold is clean.

Closest candidates (all above PF 0.5 floor):

| Strategy | n | WR | PF | Notes |
|---|---|---|---|---|
| `claude_ml_conservative_mut` | 20 | 20.0% | 0.545 | Just above kill threshold |
| `mega_mutation_ema_momentum_m006` | 33 | 45.5% | 0.803 | Monitor |
| `stocks_rsi2_pullback` | 48 | 37.5% | 0.996 | Primary EQUITY drag |
| `luxalgo_confluence` | 667 | 43.9% | 0.997 | Large-n near-breakeven |

Direction-flip candidates from mutation analysis (Axis 1):
- `ig_contrarian_sentiment`: LONG WR=16.5% (n=200) vs SHORT WR=60.3% (n=58) → 44pp spread (known, per #1299)
- `myfxbook_retail_contrarian`: LONG WR=13.7% (n=124) vs SHORT WR=50.0% (n=14) → 36pp spread (**new this cycle**)
- `quan_engine_swing`: LONG WR=26.0% (n=104) vs SHORT WR=60.0% (n=5) → 34pp spread (known)
- `cta_cross_asset_tsmom`: LONG WR=29.4% (n=85) vs SHORT WR=50.0% (n=178) → 21pp spread (known)

**`myfxbook_retail_contrarian` LONG** is new to this analysis: n=124, WR=13.7% — meets investigation gate (n≥20, WR<35%). PF not yet at <0.5 aggregate threshold, but LONG direction is severely impaired. Flagged for next session SHORT-only mutation proposal per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`.

Symbol-level Axis 3 findings (unchanged from 22Z):
- `cta_replicator`×NG=F: n=24, WR=0% → FINDING-60, awaiting 3-AI consensus
- `rapid_fire`×UUSDT: n=34, WR=0% → FINDING-61, awaiting 3-AI consensus

## NEW FINDING-63 — EQUITY 7d accelerating deterioration

**Trigger:** EQUITY 7d PF dropped 0.755 → 0.654 (WR 35.6% → 30.8%) between the 22Z and 23Z snapshots (~60 min window).

**Evidence:**
- 22Z snapshot (21:38:30Z): EQUITY 7d PF=0.755, WR=35.6%
- 23Z snapshot (22:45:32Z): EQUITY 7d PF=0.654, WR=30.8%
- Monotonic decline continues: 30d PF=1.349 / 7d PF=0.654

**Primary driver:** `stocks_rsi2_pullback` n=48, WR=37.5%, PF=0.996. Highest EQUITY sample size among underperformers. Not yet kill-eligible (PF>0.5). Approaching mutation analysis gate.

**Secondary driver:** `luxalgo_confluence` n=667, WR=43.9%, PF=0.997 — large-n near break-even system-wide.

**Action (monitor-only):** If `stocks_rsi2_pullback` 7d WR stays <40% at n≥50 in next audit, propose mutation analysis per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`. Do NOT kill without 3-AI consensus.

**Posted to issue #686.**

## Summary of FINDING status

| Finding | Strategy×Symbol | n | WR | PF | Status |
|---|---|---|---|---|---|
| FINDING-59 | `futures_momentum`×COMMODITY | 17 | 11.4% | — | Monitor (n<20) |
| FINDING-60 | `cta_replicator`×NG=F | 24 | 0% | 0.0 | Awaiting 3-AI consensus |
| FINDING-61 | `rapid_fire`×UUSDT | 34 | 0% | 0.0 | Awaiting 3-AI consensus |
| FINDING-62 | `cftc_cot_commercial_signal`×COMMODITY | 16 | 12.5% | 0.409 | Monitor (n<20) |
| **FINDING-63** | EQUITY 7d system / `stocks_rsi2_pullback` | 48 | 30.8%/37.5% | 0.654/0.996 | **New — monitor; mutation gate at n=50** |

## Actions taken this cycle

- Merged PR #1301 (audit 21Z — FINDING-60/61) ✅
- Merged PR #1302 (audit 22Z — FINDING-62) ✅
- Posted FINDING-63 to issue #686 ✅
- No strategy kills (no PF<0.5 + n≥20 candidates) ✅
- PR #1299 held (dirty/merge conflict) ✅
- PR #1287 held (test(3.11) FAILED) ✅

## References

- Issue #685: resolver-rescope status (DONE)
- Issue #686: live regression tracker (updated this cycle)
- Issue #693: EQUITY divergence monitor (closed 2026-05-13)
- `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`
- `docs/MUTATION_THREE_AXIS_PROTOCOL.md`
