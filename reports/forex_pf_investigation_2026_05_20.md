# FOREX PF Investigation — 2026-05-20

**Trigger:** Dashboard shows FOREX n=148, WR=56.1%, PF=1.491 — just below T2 threshold of 1.5.
**Source:** `audit_dashboard/data/pf_registry.json` canonical view = `by_asset_class_policy_clean_net`
**Generated:** 2026-05-20

---

## Aggregate Numbers by Filtering Level

| Level | n | WR | PF | Notes |
|---|---|---|---|---|
| Raw (all closed trades incl. flickers/dups) | 1,003 | 25.6% | 0.358 | All FOREX from alpha_engine + other sources |
| Deduped (flicker+dup removed) | 511 | 25.6% | 0.346 | After classifier removes re-emissions |
| Policy-clean (pre-slippage) | 149 | 55.7% | 1.654 | After policy exclusions applied |
| Policy-clean-net (slippage applied) | 149 | 55.7% | 1.476 | **Canonical registry view** |
| Dashboard `asset_class_health` | 148 | 56.1% | 1.491 | Dashboard computation (minor rounding diff) |

**Key insight:** The raw data is severely noise-polluted (PF=0.358 on 1,003 trades). Policy exclusions — which remove forward-test-only picks, blocked source systems, and spot-flicker artifacts — narrow the universe to 149 clean trades where the aggregate picture is PF=1.476–1.491. The gap between raw PF and policy-clean PF reflects how much the non-policy sources drag the system.

---

## Per-Strategy Breakdown (Policy-Clean-Net, Canonical View)

| Strategy | n | Wins | Losses | WR | PF | Gross Win | Gross Loss | Excl. PF | Delta |
|---|---|---|---|---|---|---|---|---|---|
| cta_replicator | 98 | 63 | 35 | 64.3% | 2.316 | 0.1946 | 0.0840 | 0.941 | −0.535 |
| multi_asset_copytrader | 25 | 13 | 12 | 52.0% | 1.419 | 0.0775 | 0.0546 | 1.495 | +0.019 |
| alpha_engine | 15 | 6 | 9 | 40.0% | 0.841 | 0.0408 | 0.0485 | 1.660 | +0.184 |
| multi_asset_scanner | 11 | 1 | 10 | 9.1% | 0.209 | 0.0061 | 0.0289 | 1.672 | +0.196 |
| **TOTAL** | **149** | **83** | **66** | **55.7%** | **1.476** | **0.319** | **0.216** | — | — |

"Excl. PF" = aggregate PF if this strategy were excluded. "Delta" = Excl.PF − Baseline PF.

---

## Root Cause: What Is Dragging PF from ~1.67 to 1.491?

Two strategies are the primary drag:

### 1. `multi_asset_scanner` — PRIMARY DRAG (+0.196 PF lift if excluded)
- **n=11, WR=9.1%, PF=0.209**
- Worst performing strategy in the FOREX policy-clean universe.
- 1 win, 10 losses. Near-zero win rate suggests structural signal failure.
- Gross loss = 0.029, nearly 5× its gross profit (0.006).
- Excluding this alone lifts aggregate FOREX PF from 1.476 → 1.672 (above T2).

### 2. `alpha_engine` — SECONDARY DRAG (+0.184 PF lift if excluded)
- **n=15, WR=40.0%, PF=0.841**
- Sub-1.0 PF: gross losses exceed gross wins.
- 6 wins, 9 losses. Not catastrophically bad but materially negative contribution.
- Together with multi_asset_scanner, excluding both would lift PF to ~1.85+.

### 3. `cta_replicator` — ANCHOR (must NOT be excluded)
- **n=98, WR=64.3%, PF=2.316**
- This is the entire engine of FOREX performance.
- Without it, aggregate PF collapses to 0.941 (below 1.0).
- Any FOREX sizing decision must be conditioned on cta_replicator remaining healthy.

### 4. `multi_asset_copytrader` — MARGINAL
- **n=25, WR=52.0%, PF=1.419**
- Below-T2 PF but contributing positively. Excluding it barely changes aggregate (+0.019).
- Watch-tier candidate; not a kill candidate.

---

## Pre-Policy vs Policy-Clean: Why 511 → 149?

Of 511 deduped FOREX trades, 362 are excluded by policy. The exclusions resolve most of the drag:
- `multi_asset_copytrader` raw: n=326, WR=11.3%, PF=0.166 → policy-clean: n=25, WR=52.0%, PF=1.419
- The 301 excluded `multi_asset_copytrader` picks are forward-test-only picks with a catastrophic WR; the policy filter correctly isolates only the higher-quality subset.

The remaining policy-clean drag comes from `alpha_engine` (15 picks) and `multi_asset_scanner` (11 picks) that are not excluded but perform poorly.

---

## T2 Threshold Gap Analysis

- Current policy-clean PF: 1.476 (net slippage) / 1.491 (dashboard rounding)
- T2 threshold: PF ≥ 1.5
- Gap: **−0.024 PF points** (extremely close — within noise)
- WR = 56.1% ✓ (T2 threshold: WR ≥ 50%)
- MDD = 0.043 (4.3%) ✓ (T2 threshold: MDD < 20%)

**The FOREX aggregate is functionally at T2 on WR and MDD.** The PF gap is driven entirely by `multi_asset_scanner` (PF=0.209) and `alpha_engine` (PF=0.841). Excluding these two strategies alone would bring aggregate PF to approximately 1.85+, comfortably in T2.

---

## Recommendations (Candidates for STRATEGY_INVESTIGATION_BEFORE_KILL)

The following strategies warrant `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` and `docs/MUTATION_THREE_AXIS_PROTOCOL.md` review before any blocking action. **Do NOT block without user approval.**

### Candidate 1: `multi_asset_scanner` (FOREX) — HIGH PRIORITY
- **Case:** n=11, WR=9.1%, PF=0.209. Near-zero win rate in FOREX. Structural failure.
- **Protocol step:** Export closed CSV → `python tools/mutation_analysis.py`. Check: is this a specific symbol concentration, a timeframe mismatch, or a signal-generation flaw?
- **Mutation options before kill:**
  1. Filter FOREX picks from multi_asset_scanner (asset-class block, not system kill)
  2. Restrict to specific symbols where WR is acceptable
  3. Tune entry conditions (RSI overbought threshold, etc.)
- **Kill threshold:** If mutation fails to achieve WR ≥ 40% / PF ≥ 1.0 after 3-axis test
- **Review date:** 2026-06-20 (allow 30 more days of live data)

### Candidate 2: `alpha_engine` (FOREX) — MEDIUM PRIORITY
- **Case:** n=15, WR=40.0%, PF=0.841. Below-1.0 PF but thin sample.
- **Protocol step:** Investigate which alpha_engine strategies are generating FOREX picks and their individual WR/PF breakdown.
- **Mutation options before kill:**
  1. Raise minimum confidence threshold for FOREX alpha_engine picks
  2. Apply FOREX session gate (M-078 08-16 UTC) more aggressively
  3. Add symbol-level filter (remove USD pairs with known carry-regime issues)
- **Kill threshold:** If n grows to 30+ and PF remains < 0.9
- **Review date:** 2026-06-20

### Not a candidate: `multi_asset_copytrader` (FOREX)
- n=25, WR=52.0%, PF=1.419 — marginal but positive. Monitor only.

### Not a candidate: `cta_replicator` (FOREX)
- n=98, WR=64.3%, PF=2.316 — this is the edge engine. Protect, do not touch.

---

## Action Items (Requiring User Approval)

1. **[APPROVAL NEEDED]** Initiate STRATEGY_INVESTIGATION_BEFORE_KILL for `multi_asset_scanner` FOREX picks
   - Run: `python tools/mutation_analysis.py --strategy multi_asset_scanner --class FOREX`
   - Target: understand if symbol/timeframe filter can rescue PF ≥ 1.0
2. **[APPROVAL NEEDED]** Initiate STRATEGY_INVESTIGATION_BEFORE_KILL for `alpha_engine` FOREX picks
   - Need to identify which sub-strategies within alpha_engine are generating the losing FOREX picks
3. **[MONITOR ONLY]** Watch `cta_replicator` FOREX health weekly — any WR drop below 55% triggers circuit-breaker review

---

## Sources

- `audit_dashboard/data/pf_registry.json` — canonical PF breakdown
- `audit_dashboard/data/dashboard_data.json` — asset_class_health n=148 reference
- Computation script: inline Python (tools/build_pf_registry.py load_rows + classify_rows)
