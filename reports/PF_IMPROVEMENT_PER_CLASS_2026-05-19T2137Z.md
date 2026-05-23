# PF / WR Improvement Plan — Per Asset Class — 2026-05-19T2137Z

**Frame:** Practical, harness-compatible, near-term actions to raise per-class
PF / WR on the canonical `audit_dashboard/data/pf_registry.json` (policy-clean,
deduped, **net-of-cost**) — the verdict-grade ledger. Dashboard tiles inflate
and are NOT used here.

**Source plans reviewed:**
- `reports/MERGED_ACTION_PLAN_2026-05-19.md` (today's authoritative merge)
- `reports/MASTER_ACTION_PLAN_2026-05-18.md`, `..._KIMI_V2_2026-05-18.md`
- `reports/NEXT_MOVES_2026-05-19.md` (Tier-1/2/3/4 roadmap)
- `reports/daily_ideas_synthesis_2026-05-16.md`, `..._edge_sweep_2026_05_17.md`
- `DAILY_IDEAS.MD` (2,341-line operator log)
- `reports/EDGE_VERDICT_2026-05-18.md` + `EDGE_HUNT_EXHAUSTED_2026-05-18.md`
- 7+ external/local AI consults under `reports/*CONSULT*`, `*RESCUE*`

**Honest framing — do NOT walk past this:**
- 17 pre-registered causal hypotheses → 0 admissible under
  `tools/edge_stability_harness.py`. **No durable real-money edge measured.**
- Every action below is an **emitter-hygiene / data-integrity** lift on the
  EXISTING ledger. None of it creates new edge — it stops bleeding from drag
  emitters and surfaces what already exists.
- The only "new edge" bet (Tier-3 in merged plan) is the tick-microstructure
  probe; that's a paper-only 2-4 week test, ~5-20% odds.
- **All numbers below = canonical net-of-cost from `pf_registry.json`.**

---

## Canonical per-class baseline (this snapshot)

| Class | n | WR% | PF (net) | total_pnl_pct | T2 gate (PF≥1.5, WR≥50, n≥100) |
|-------|--:|----:|---------:|--------------:|:------------------------------:|
| BOND        |    5 |  0.0 | 0.00 |   −0.49 | ❌ n |
| COMMODITY   |   55 | 54.5 | 1.42 |   +0.43 | ❌ PF, n |
| **CRYPTO**  | **1116** | **44.1** | **0.64** | **−43.36** | ❌ PF, WR |
| EQUITY      |    5 | 20.0 | 0.25 |   −0.10 | ❌ all |
| ETF         |    2 | 50.0 | n/a  |   +0.22 | ❌ n |
| **FOREX**   |  148 | 56.1 | **1.49** |   +0.11 | ⚠ borderline (PF 1.49) |
| FUTURES     |   12 | 16.7 | 0.96 |   −0.01 | ❌ all |
| UNKNOWN     |   38 | 52.6 | 1.72 |   +0.26 | ❌ n, unclassified |

**Verdict:** Only FOREX is anywhere near T2 (net PF 1.49 just shy of 1.50 gate).
CRYPTO is the volume class but bleeds −43 PnL_pct on the canonical view.

---

## The single biggest lift available: kill one CRYPTO drag emitter

`pf_registry.by_asset_class_strategy_policy_clean_net` reveals:

| Asset | Strategy | n | WR | PF | total_pnl_pct |
|-------|----------|--:|---:|---:|-------------:|
| CRYPTO | **`ensemble`** | 79 | 5.1% | 0.01 | **−56.35** |
| CRYPTO | `copy_trader_intel` | 32 | 0.0% | 0.00 | −0.03 |
| CRYPTO | `ml_breakout` | 21 | 0.0% | 0.00 | −0.02 |
| CRYPTO | `UNKNOWN` (orphan) | 23 | 0.0% | 0.00 | −0.02 |
| CRYPTO | `rapid_fire` | 80 | 35.0% | 0.73 | −0.31 |
| CRYPTO | `multi_period_rsi_confluence_eth` | 15 | 46.7% | 0.56 | −1.50 |

`ensemble` alone = −56.35pp PnL on CRYPTO. Total CRYPTO bucket is −43.36pp.
**Removing `ensemble` from the canonical aggregation flips the class from
PF 0.64 / −43pp to roughly PF >1.5 / +13pp.** (Numerator floor; this is a
ledger-clean number, not a backtest claim. Math: gross_profit −
`ensemble`_gross_profit ÷ gross_loss − `ensemble`_gross_loss.)

**Caveat (mandatory):** before killing `ensemble`, confirm it's not a data
artifact (single-symbol 100%-LOSS sequence like the historical MATIC ghost
in `project_quan_engine_matic_positive_artifact.md`). Investigation gate per
`docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`. Mutate-before-kill protocol
per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`.

---

## Per-class action plan (concrete, harness-compatible)

### CRYPTO — biggest lever; emitter purge

**Goal:** PF 0.64 → ≥1.2 on canonical via emitter cuts; ≥1.5 only if forward
probe clears. n=1116, plenty of density.

| ID | Action | Wire target | Acceptance test |
|----|--------|-------------|-----------------|
| C-1 | Investigate `ensemble` n=79 5.1% WR — symbol/ToD ghost check | `tools/mutation_analysis.py --strategy ensemble --asset CRYPTO` | Confirm not single-symbol artifact; if ghost → backfill, if real → block |
| C-2 | After investigation: add `("CRYPTO","ensemble")` to `BLOCKED_ASSET_STRATEGY_PAIRS` | `audit_trail/quality_gates.py` | New CRYPTO `ensemble` picks = 0; PF lift ≥ +0.5 next 200 closes |
| C-3 | Block `copy_trader_intel`/CRYPTO + `ml_breakout`/CRYPTO + orphan `UNKNOWN` row source (n≥20 all WR=0) | `BLOCKED_ASSET_STRATEGY_PAIRS` | New n=0 in 24h |
| C-4 | Tighten `quan_engine` CRYPTO bucket (PF 0.70 18% volume per CLAUDE.md) — confidence-floor gate | `audit_trail/quality_gates.py::passes_active_gate` | quan_engine CRYPTO volume share ≤8% in 7-day rolling |
| C-5 | **Do NOT promote** `ml_enhanced_*USDT_*` cohorts with 89-97% WR + n<50 — textbook overfit (single-symbol/timeframe) | reject from any "T1/T2-ready" list | Filter: require ml_enhanced cohort to have ≥3 distinct symbols at n≥30 each before promotion |
| C-6 | Track `st_fear_greed_contrarian` (n=101 WR 49.5 PF 1.34 +6.54pnl) — borderline; let n accrue to 400 | passive | Re-harness at n≥200; if eff/sign stays → candidate; if not → kill |
| C-7 | Paper-only: `mega_mutation` cohort (PF 2.19 n=72) via `crypto_paper_pilot.py` | already shipped | Forward result = verdict |

**Expected canonical CRYPTO lift after C-1..C-4:** PF 0.64 → ~1.4-1.7
(arithmetic; not new edge — removing measurable bleed).

### FOREX — push borderline to T2

**Goal:** PF 1.49 → ≥1.55 net; WR is already 56.1%. n=148 already T2-density.

| ID | Action | Wire target | Acceptance test |
|----|--------|-------------|-----------------|
| F-1 | Whitelist `cta_replicator` (n=97 WR 64.9% PF 2.38 +0.11pnl) as **only** FOREX emitter on `EMITTER_WHITELIST` | `ml_consensus/consensus.py`, `forward_validator.py` | New FOREX volume ≥90% cta_replicator |
| F-2 | Block `alpha_engine`/FOREX (n=15 WR 40% PF 0.84) | `BLOCKED_ASSET_STRATEGY_PAIRS` | 0 new alpha_engine FOREX picks |
| F-3 | Block `multi_asset_scanner`/FOREX (n=11 PF 0.21 WR 9.1%) | `BLOCKED_ASSET_STRATEGY_PAIRS` | 0 new picks |
| F-4 | Accrue `cta_replicator` to n=200 with whitelist active | passive | At n=200: re-canonical → check WR sign-stability across 14d windows (harness) |
| F-5 | Run `cta_replicator` through `tools/edge_stability_harness.py` once n≥150 | harness | Verdict: ADMISSIBLE/REJECTED/UNTESTED |

**Expected canonical FOREX lift:** −drag from alpha_engine + scanner is ~0.03
of total pnl; the real lift is **stable T2 promotion** by removing the small-n
losers, not arithmetic. Path to true PF 1.55+ requires F-5 harness clearance.

### COMMODITY — close the n-gap

**Goal:** Get to n≥100 with current PF 1.42 / WR 54.5% stability; then test.

| ID | Action | Wire target | Acceptance test |
|----|--------|-------------|-----------------|
| K-1 | Whitelist `multi_asset_copytrader` COMMODITY (n=54 WR 53.7% PF 1.38) | `EMITTER_WHITELIST` | Continue emission |
| K-2 | Block `cta_replicator` on COMMODITY per Grok autopsy (Merged plan T2-02) | `BLOCKED_ASSET_STRATEGY_PAIRS` | 0 new cta_replicator COMMODITY |
| K-3 | Allow `multi_asset_cot` (H-001 LIVE_TESTING, separate track) | passive | Track separately under hypothesis_registry |
| K-4 | At n=100: harness run; if ADMISSIBLE → T2; if not → kill | `edge_stability_harness.py` | Verdict |

**Note:** previous DEEP_DIVE flagged COT leakage (`project_edge_verdict_2026_05_18.md`)
— `cot_positioning` was blocked under M-095. Keep that block; do NOT re-introduce
cot_positioning via copytrader proxy.

### EQUITY — too thin to act on

n=5 net-clean is insufficient for any improvement claim. The historical 421-pick
EQUITY post-noise-filter view (CLAUDE.md major-goals banner) lived in pre-canonical
data. Today's clean view: 5 picks, WR 20%, PF 0.25. **Don't size up. Don't
promote.** Wait for emitter volume; revisit at n≥100 canonical.

| ID | Action | Note |
|----|--------|------|
| E-1 | DO NOT promote `claude_gainer_st`/`kimi_gainer_*` cohorts pending re-validation against canonical | per Cursor 2026-04-13 inflation finding |
| E-2 | Wait for canonical n≥100 EQUITY; then harness | passive |
| E-3 | If H-033/H-034 EQUITY hypotheses pre-register + clear harness → enable | per merged plan T3-04 |

### ETF — n=2, ignore

PF 11.99 is noise. Wait for n≥50 before any claim. Per NEXT_MOVES roadmap.

### BOND — frozen

n=5, 0% WR. Hold all sizing per `system_drift_alert_2026_05_14`. Wait for emitter
activity.

### FUTURES — halt emission

n=12 WR 16.7% PF 0.96 — sub-floor. Merged plan T2-04 + `project_futures_kill_without_replacement`:
**halt new FUTURES picks** at workflow gate until clean replacement.

| ID | Action | Wire target |
|----|--------|-------------|
| FU-1 | Halt FUTURES emission via workflow gate | `.github/workflows/audit-dashboard.yml` or `audit_trail/quality_gates.py` |
| FU-2 | Pre-register replacement hypothesis BEFORE re-enable | `hypothesis_registry.json` M-107 |

### UNKNOWN — classify

n=38 PF 1.72 WR 52.6% — interesting but unclassified. **Cannot manage what we
can't name.**

| ID | Action | Wire target |
|----|--------|-------------|
| U-1 | Source-trace UNKNOWN picks: which emitter? what symbol? | `tools/code_index.py` query + grep `pf_registry` UNKNOWN rows |
| U-2 | Classify into proper asset_class via `asset_classification.py::resolve_asset_class` | `audit_trail/asset_classification.py` |
| U-3 | Re-run pf_registry build → UNKNOWN row should shrink to 0 | `tools/build_pf_registry.py` |

---

## Cross-class infrastructure lifts (raise PF everywhere)

These are PF-multipliers because they fix the **measurement** of PF, not the
underlying picks. Drawn from MERGED_ACTION_PLAN T1.

| ID | Action | Lift mechanism |
|----|--------|----------------|
| X-1 | T1-01 confidence corruption clamp at emission | Stops 2,575 rows of >1.0 confidence corrupting tier filters |
| X-2 | T1-02 dedup guard pre-`at_raw_picks` insert | Prevents inflated n from re-emission; tightens canonical |
| X-3 | T1-05 widen harness ledger scope (32 files vs 1) | Currently harness can't even score most cohorts → ADMISSIBLE rate is upper-bound capped at zero for invisible strategies |
| X-4 | Magnitude gate M-108 (already shipped) | Stops `mega_mutation` ghost-pick inflation |
| X-5 | Net-of-cost as **default** in all dashboards + tiles | Stops "raw PF" celebration when net is sub-floor |
| X-6 | Position-sizing ceiling per pick = `min(0.05, kelly_quarter)` | Caps tail blow-up risk; PF stability ↑ at cost of slight gross ↓ |

---

## Estimated end-state — CORRECTED after swarm + Grok review

**Original (1.4-1.7 PF) estimate was wrong** — swarm flagged + I re-ran arithmetic
directly on `pf_registry.json`. Actual canonical aggregate after exclusions:

| Aggregation | n | WR% | PF (net) | total_pnl_pct |
|-------------|--:|----:|---------:|--------------:|
| CRYPTO **before** | 1116 | 44.1 | 0.64 | −43.36 |
| CRYPTO **ex-`ensemble` only** | 1037 | 47.1 | **1.21** | +12.98 |
| CRYPTO **ex-9-drag** (ensemble + copy_trader_intel + ml_breakout + UNKNOWN + multi_period_rsi_eth + rapid_fire + seasonal_factor_rotation + copy_trader_clones + fractal_sr_bounce) | 787 | 54.1 | **1.26** | +14.99 |

**Reality:** drag-exclusion lifts CRYPTO canonical PF to ~1.20-1.26, not 1.4-1.7.
That is still meaningful (PF crosses 1.0 with positive pnl) but **below the T2
PF gate of 1.5**. Honest framing: this gets us from "bleeding" to "near-flat"
on the existing ledger — not to T2 admissibility.

| Class | Before | After (canonical math) | Mechanism |
|-------|--------|------------------------|-----------|
| CRYPTO | PF 0.64 / −43pp | PF 1.21 / +13pp (ex-ensemble) | Remove `ensemble` n=79 −56pp drag |
| FOREX | PF 1.49 / +0.11pp | PF ~1.51 / +0.13pp | Drop alpha_engine + scanner (small lift) |
| COMMODITY | PF 1.42 / +0.43pp | PF ~1.42 holding | Hygiene only; n still <100 |
| FUTURES | PF 0.96 | frozen | Halt emission |

**Crucially:** these are **same-ledger re-aggregation numbers** — i.e.
**post-selection bias by construction**. The actual edge claim still requires
forward, out-of-sample harness clearance. See post-selection-bias section below.

---

## ⚠ Post-selection bias warning (added per 3-AI swarm critique)

External review (Grok, DeepSeek, xAI — all MAJOR_REVISION verdict) flags:

> "Killing the emitter after observing its drag to 'lift class PF' is metric
> chasing on the same sample. Legitimate hygiene requires a priori rules or
> independent OOS; this is ex-post pruning." — Grok

> "Whitelisting cta_replicator without harness clearance creates a
> single-point-of-failure." — DeepSeek + xAI consensus

**This plan, as written, is at risk of repeating the data-dredging trap that
killed 17/17 hypotheses.** Mitigations now baked in below:

1. **C-2 (kill ensemble) is gated on investigation, not naive PF.** Before
   adding to BLOCKED_ASSET_STRATEGY_PAIRS:
   - Run `tools/mutation_analysis.py --strategy ensemble --asset CRYPTO` —
     check symbol/ToD concentration (MATIC-ghost test).
   - Run **inverse** (flip direction) over the same n=79; if inverse → PF >1.3
     this is a sign-flipped real edge, not noise — **invert, don't kill**.
   - Only kill if ghost-confirmed OR inverse also PF<1.0.
2. **F-1 (whitelist cta_replicator) requires harness clearance FIRST.** No
   "whitelist as sole FOREX emitter" until `tools/edge_stability_harness.py`
   returns ADMISSIBLE on the unmodified harness. At n=97 it's also one trade
   shy of the n≥100 density floor — wait, don't promote.
3. **C-5 (reject ml_enhanced_*USDT_* cohorts) — heuristic alone is
   insufficient.** Stricter rule: cohort cannot ship unless (a) ≥3 distinct
   symbols at n≥30 each AND (b) harness clearance. The 89-97% WR + n<50 is
   prima-facie overfit; harness is the falsifier.
4. **Acceptance gate cannot be canonical-aggregate-on-same-ledger.** Replace
   with forward 30-day rolling: after each cut, the **next 200 closes** must
   show PF≥1.3 net on the post-cut whitelist, OR roll back.
5. **`X-3` (widen harness ledger scope) is the highest-confidence X action.**
   We can't accept-or-reject most cohorts because the harness can't see them.
   Fix that first — it's the only honest measurement upgrade.

**This is a measurement / hygiene plan, not an edge plan.** A genuine PF lift
above 1.5 with sign-stability + cost-survival ≥60% requires either:
1. Forward proof of a borderline cohort under harness (cta_replicator FOREX is
   the only realistic candidate this quarter), or
2. The tick-microstructure probe (T3-01 in merged plan) clearing harness on
   ~5-20% odds.

---

## Acceptance gate — REVISED (forward, not same-sample)

Per-class success criterion (carries to /money-maker-readyv2). Same-sample
canonical re-aggregation is **necessary but not sufficient** — forward 200-close
window required.

- [ ] **CRYPTO**: (a) canonical PF ≥1.20 net post-cuts ON existing ledger AND
      (b) next 200 closes after cut-deploy show PF≥1.20 forward, AND
      (c) no top-5 strategy with WR=0 and n≥15.
- [ ] **FOREX**: `cta_replicator` at n≥150; `tools/edge_stability_harness.py`
      verdict recorded (ADMISSIBLE / REJECTED / UNTESTED). Whitelist + scale
      only on ADMISSIBLE.
- [ ] **COMMODITY**: n≥100 canonical; PF≥1.4 holds across most-recent 50
      closes (not just lifetime).
- [ ] **FUTURES**: emission halted; replacement hypothesis registered + clears
      harness before re-enable.
- [ ] **UNKNOWN**: row size = 0 (all classified into named asset_class).
- [ ] **System integrity**: confidence>1.0 rate at emission = 0%;
      raw dashboard tiles within 0.15 PF of canonical per class.
- [ ] **Harness scope**: ≥80% of ledger files visible to
      `edge_stability_harness.py` (currently 1/32).

Anything that does **not** pass the unmodified harness remains paper-only.
Real capital sizing waits on harness clearance + forward 30-day OOS.

---

## Next steps (sequenced)

1. **Investigate `ensemble` CRYPTO ghost** (C-1) — single command:
   `python tools/mutation_analysis.py --strategy ensemble --asset CRYPTO`.
   1-hour task.
2. **Block confirmed drag emitters** (C-2..C-3, F-2..F-3, K-2, FU-1) — single
   PR amending `BLOCKED_ASSET_STRATEGY_PAIRS` + workflow gate. 2-hour task.
3. **EMITTER_WHITELIST shadow mode** (F-1, K-1) — Merged plan T2-01. Already
   running shadow per operator note (7-day shadow → enforce ~2026-05-26).
4. **Classify UNKNOWN rows** (U-1..U-3) — 1-day task.
5. **Confidence clamp + dedup guard** (X-1..X-2) — already shipped, verify
   in production CI cycles next 24h.
6. **At n=150 for cta_replicator FOREX**: harness run (F-5). Time-gated.

---

## What this plan deliberately does NOT do

- **Does not** claim any class is "money-ready" today. Verdict is paper-only
  until harness clears, per `reports/EDGE_VERDICT_2026-05-18.md`.
- **Does not** introduce new families bypassing M-107. Any new hypothesis
  goes through `hypothesis-registry` skill.
- **Does not** trust dashboard tile numbers — canonical only.
- **Does not** unblock `cot_positioning` (M-095) or `quan_engine` (per
  CLAUDE.md drag).
- **Does not** re-test killed families (`H-006..H-020`) on the same data —
  convergence trap.

---

*Generated 2026-05-19T2137Z. Canonical source: `pf_registry.json` 2026-05-19
snapshot. Authoritative companion: `reports/MERGED_ACTION_PLAN_2026-05-19.md`.*

---

## Review trail

Reviewed by Grok (xAI superGrok), DeepSeek (deepseek-chat), xAI (Grok-2) via
`tools/swarm/swarm_run.py` — outputs in `swarm_runs/pf_improvement_review_2026-05-19T2137Z/`.

**3-AI consensus:** MAJOR_REVISION required.

Key revisions folded in (above):
- End-state math corrected: CRYPTO ex-ensemble = PF 1.21 (not 1.4-1.7) per
  live `pf_registry.json` arithmetic.
- C-2 ensemble kill conditional on mutation/inverse investigation
  (not naive blocklist add).
- F-1 cta_replicator whitelist gated on harness clearance + n≥100 density.
- C-5 ml_enhanced overfit rejection requires harness, not just heuristic.
- Acceptance gate switched from same-sample re-aggregation to forward 200-close
  window.
- Post-selection bias warning section added explicitly.

**Must-not-ship items** flagged by all 3 engines:
- Whitelisting `cta_replicator` as sole FOREX emitter without harness pass.
- Killing `ensemble` without inverse/mutation test.
- Promoting any cohort on canonical re-aggregation alone.
- Acceptance gate that uses the same ledger already exhausted by
  EDGE_HUNT_EXHAUSTED_2026-05-18.md.
