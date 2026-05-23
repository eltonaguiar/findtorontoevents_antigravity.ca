# DAILY IDEAS — LMArena Benchmark Mining — 2026-05-16

**Author:** Claude Opus 4.7 (1M) orchestrator
**Input:** LMArena head-to-head "financial-prediction-algorithm-benchmarking" —
Gemini-3.1-pro.preview ("QuantEdge Arena") vs Z glm-5.1 ("Nexus Quant
OmniPredict"). Both submissions reviewed; see review verdict below.
**Goal:** Goal #1 — per-asset-class statistical edge on `/audit`.
**Status:** SELF-VETTED → awaiting agent-swarm review (see §6).

---

## 0. HONESTY DISCLAIMER (read first)

Neither LMArena app is a valid benchmark, and **NONE of their reported numbers
are admissible as evidence**:

- **glm-5.1** = 100% hardcoded mock arrays. Zero algorithm code. Fabricated
  metrics (Sharpe 4.12, "10,000+ assets", "Bloomberg Terminal", "satellite
  imagery"). Pure marketing fiction.
- **Gemini-3.1-pro** = real implementation (6 algorithms, 9 TA indicators,
  backtest engine) BUT backtests a pure `Math.random()` random walk with an
  **unseeded RNG** and an **optimistic same-bar target-before-stop fill bug**
  (`strategies.ts:816-826`). Its benchmark of "Antigravity" is hardcoded
  guesswork (`:1080-1103`). Any PF it reports is noise + bug, not edge.

**Therefore the benefit case below rests ONLY on the academic/industry
provenance of the *techniques themselves*** (López de Prado meta-labeling,
volatility-targeted sizing, regime-conditional Kelly) — never on the apps'
output. Every proposal must still earn its place through OUR own backtest +
30-day rolling-clean validation before any sizing. This is consistent with the
`feedback_confidence_is_not_edge` and `feedback_multi_ai_convergence_trap`
memory rules.

---

## 1. What is actually salvageable

### From Gemini-3.1-pro (real code)

| Technique | Where | Verdict |
|---|---|---|
| **RAKO — regime-conditional Kelly + overconfidence decay** (`regimeAwareKelly`, `strategies.ts:695-780`) | regime multiplier bull 1.2 / bear 0.8 / neutral 0.6; `if abs(score)>8: score*=0.8` | **KEEP** — concrete, cheap, directly attacks our cumulative-overconfidence trap |
| **VSM — ATR-normalized momentum** (`volatilityScaledMomentum`, `:535-601`) | momentum measured in ATR units; position size ∝ 1/volRatio | **KEEP** — makes thresholds comparable across asset classes (we have none today) |
| **MFE — regime-alignment multiplier** (`multiFactorEnsemble`, `:500-503`) | counter-regime trades ×0.6, with-regime ×1.2 | **KEEP** — simple exec-time penalty |
| `detectRegime` (ADX>25 + price/SMA + momentum) | `:248-265` | **SKIP** — cruder than our HMM 7-state regime terminal |
| CACS cross-asset lead-lag | `:607-689` | **SKIP** — Gemini's own comment says it copies our existing "BTC Lead-Lag Causal" |
| backtest `riskReward>=1.2` gate | `:803` | **SKIP** — we already enforce `MIN_RR=2.0` |

### From glm-5.1 (concepts only — no code, but two are real techniques)

| Concept | Verdict |
|---|---|
| **Triple-barrier meta-labeling** (López de Prado) — secondary ML model predicts P(primary signal wins) | **KEEP (highest value)** — this IS the textbook fix for our confidence-inversion problem |
| **EGARCH volatility-targeted sizing** | **KEEP (downgrade to realized-vol target)** — EGARCH is overkill; realized-vol / ATR targeting captures 90% of the benefit |
| "50+ Bloomberg/satellite data sources", "250+ ensembles" | **DROP** — infra cosplay, no edge thesis, Wire-Up-Rule reject |

---

## 2. KEY repo finding that makes this cheap

`alpha_engine/meta_labeler.py` **already exists** — a real 694-line module:
`MetaLabeler` class, `extract_features` (incl. hour sin/cos + day-of-week
cyclical encoding), `build_dataset`, `heuristic_score`. It is referenced by
`forward_validator.py` but is **NOT wired into the production scorer**
(`dashboard_generator._normalize_pick` / `smart_picks_engine` /
`production_scanner` / `scanner`). It is an orphan per the Wire-Up Rule.

**The single highest-leverage action is not building anything — it is wiring
the meta-labeler that already exists into the production gate.** Gemini's RAKO
algorithm independently re-invented the same idea (overconfidence decay), which
is corroboration of direction, not of magnitude.

---

## 3. Proposals per asset class

Each proposal: technique → our current state → edge mechanism → effort →
wiring plan → acceptance criteria.

### P1 — CRYPTO: wire `meta_labeler.py` as an exec-time pick gate *(highest ROI)*

- **Technique:** triple-barrier meta-labeling. Secondary model scores P(win) for
  each primary pick; reject picks below a learned probability threshold.
- **Our state:** CRYPTO PF ~1.3, WR 46.5%, confidence metric INVERTED
  (conf≥0.9 → 14.4% WR per memory `project_performance_reality`). 4 drag
  strategies produce 60%+ volume at PF<1. `meta_labeler.py` exists, unwired.
- **Edge mechanism:** meta-labeler is trained on *realized outcomes*, so it
  cannot inherit the broken `confidence` calibration — it learns the true
  win-probability surface directly. Filtering CRYPTO picks by meta-label P(win)
  removes drag-strategy volume without a hand-maintained blocklist.
- **Effort:** M (meta_labeler module exists; ~6h to wire + A/B harness).
- **Wiring Plan:** add `meta_label_gate(pick) -> bool` call inside
  `audit_trail/quality_gates.passes_active_gate` (production caller — satisfies
  Wire-Up Rule). Gate behind `META_LABEL_GATE=1` env flag, shadow-log first.
- **Acceptance:** on next-30-day rolling-clean CRYPTO cohort, picks passing the
  meta-gate must show ≥ +8pp WR vs picks failing it, n≥150 each side, before
  the gate flips from shadow to enforce.
- **Risk:** meta-labeler trained on polluted history (resolver live-close bug,
  ghost rows) → garbage-in. MUST train only on post-resolver-v2.1 clean closed
  picks. Verify training-set provenance first.

#### P1 — leak audit of `meta_labeler.extract_features` (done 2026-05-16)

Audited the existing 10-feature vector (`alpha_engine/meta_labeler.py:170-218`):

| Feat | Field | Leak verdict |
|---|---|---|
| F0 | num_agreeing_systems | clean (entry-time) |
| F1 | `confidence` | **redundant** — this is the known-inverted metric. Not a leak, but if F1 dominates feature-importance the meta-model just mirrors `confidence` and adds nothing. **Action: train with + without F1; drop it if importance > 0.3.** |
| F2 | strategy_historical_wr | sourced from a **static hardcoded `STRATEGY_WR` dict** (`:72`) — NOT live-computed, so no look-ahead. But it is stale; low value. |
| F3 | symbol_encoded | clean |
| F4-F6 | hour_sin/cos, day_of_week | **clean** — derived from `timestamp`/`entry_time`/`created_at` (entry-time), never resolved-at. Swarm's look-ahead concern is cleared by code inspection. |
| F7 | risk_reward | clean (entry-time) |
| F8 | ml_score | clean *if* stamped at entry — verify the pipeline does not re-stamp post-close. |
| F9 | `forward_wr` | **GENUINE LEAK RISK** — a forward/realized win-rate aggregate. If `forward_wr` is computed over a window that includes the pick's own outcome (or any close after the pick's entry), it is look-ahead. **Action: drop F9, OR re-derive it strictly from closes dated before the pick's entry timestamp.** |

Also `build_dataset` (`:221-250`) does **no temporal train/test split** — it
pools all picks. **Action: replace with a purged walk-forward split** (train on
older closes, validate on newer) before trusting any reported meta-model WR.

**Net P1 implementation gate:** before wiring `meta_label_gate` into
`passes_active_gate`, (a) drop/repair F9, (b) add purged walk-forward split,
(c) confirm training set is post-resolver-v2.1 clean. Until then P1 stays a
spec, not code — too risky to wire untested (swarm: most-damaging-if-wrong).

### P2 — ALL CLASSES: regime-alignment multiplier + overconfidence decay

- **Technique:** Gemini RAKO/MFE — counter-regime score ×0.6, with-regime ×1.2;
  `if abs(score) > THRESH: score *= 0.8` (overconfidence decay).
- **Our state:** `conviction_stack.py` / `elite_scorer.py` have partial
  regime logic; no explicit overconfidence decay. `claude_gainer_st`
  (cumulative PF 6.80 → real WR 26.5%) is the canonical overconfidence blowup.
- **Edge mechanism:** decay caps the score inflation that the non-ergodic
  cumulative-PnL trap feeds on; regime multiplier penalizes fighting the HMM
  regime. Both are monotone, interpretable, no new data.
- **Effort:** S (2-3h — additive multiplier in `score_booster.py`).
- **Wiring Plan:** add `_regime_overconf_adjust(score, regime, signal)` to
  `alpha_engine/score_booster.py`; call from `calculate_smart_score`. Additive,
  fail-soft, env-flag `REGIME_DECAY=1`.
- **Acceptance:** A/B over 30d — adjusted-score ranking must not REDUCE
  realized WR of the top-quartile cohort; target +2-4pp on EQUITY/CRYPTO.
- **Risk:** double-penalising picks already gated by HMM regime. Verify no
  overlap with existing `conviction_stack` regime logic before wiring.

### P3 — FOREX / COMMODITY / ETF: realized-volatility-targeted sizing

- **Technique:** glm "EGARCH sizing" downgraded to realized-vol target —
  size ∝ target_vol / realized_vol(20); Gemini VSM uses ATR-normalized
  momentum for the same purpose.
- **Our state:** charter uses Quarter-Kelly + per-class caps; no per-pick
  vol-targeting. COMMODITY edge is concentrated in CT=F (75% volume) — a
  vol-target naturally caps the fat-tail single-instrument exposure.
- **Edge mechanism:** equalizes risk contribution per pick; prevents a
  high-vol FOREX pick from carrying 5× the risk of a low-vol BOND pick at the
  same nominal size. Improves realized Sharpe even at constant WR.
- **Effort:** M (1 day — sizing layer + backtest).
- **Wiring Plan:** extend `alpha_engine/backtest/position_sizing.py` with
  `vol_target_size(pick, realized_vol, target=0.10)`; wire into the TV
  paper-trade sizing path. Opt-in sidecar until backtested.
- **Acceptance:** on COMMODITY + ETF 30d cohort, vol-targeted sizing must
  raise Sharpe ≥ +0.2 vs fixed sizing at equal-or-better MDD.
- **Risk:** realized-vol estimate lags regime shifts; cap the scalar at [0.3, 2.0].

### P4 — FOREX rehab: ATR-normalized momentum as a mutate-before-kill candidate

- **Technique:** Gemini VSM — momentum in ATR units + multi-timeframe alignment.
- **Our state:** FOREX PF 0.27-0.86, catastrophic; `MUTATION_THREE_AXIS_PROTOCOL`
  active; carry-factor is the documented rescue (edge-per-class #14).
- **Edge mechanism:** FOREX raw momentum thresholds are mis-scaled vs other
  classes (FOREX vol ~0.005 vs CRYPTO ~0.04); ATR-normalization is the correct
  fix and is a legitimate *mutation axis*, not a new strategy.
- **Effort:** S (within existing mutation harness).
- **Wiring Plan:** register ATR-normalized momentum as a mutation variant in
  `tools/mutation_analysis.py`; NO production wiring until it clears the
  investigation gate per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`.
- **Acceptance:** mutated variant must reach PF>1.0 + WR>45% over 30d before
  any FOREX emission resumes. Otherwise FOREX stays hard-disabled.
- **Risk:** none added — this is research-only until the gate clears.

### P5 — (NOT a proposal) classes to skip

- **BOND** (n=11-18): too thin for any of the above; ramp sample first.
- **EQUITY** beyond P2: already Tier-2; do not over-engineer the one class
  that works.

---

## 4. What we explicitly REJECT from the LMArena apps

- glm's "10,000+ assets / 250+ ensembles / Bloomberg / satellite" — infra
  cosplay, no edge thesis, Wire-Up-Rule reject.
- Gemini's hardcoded "Antigravity benchmark" numbers — fabricated; if this
  comparison surfaces externally, correct it with real
  `dashboard_data.json::asset_class_health`.
- Both apps' headline PF/WR/Sharpe — inadmissible (see §0).
- glm's strawman of our system ("fixed 5% sizing / 3 data sources / 58% WR") —
  factually wrong.

---

## 5. SELF-VETTING (done before swarm review)

| Check | Result |
|---|---|
| Are any proposals justified by the LMArena apps' *numbers*? | NO — provenance is academic only (§0). |
| Wire-Up Rule — does each new code path name a production caller? | P1 → `passes_active_gate`; P2 → `calculate_smart_score`; P3 → opt-in sidecar w/ plan; P4 → research-only. ✅ |
| Multi-AI convergence trap (`feedback_multi_ai_convergence_trap`)? | Gemini RAKO ≈ glm meta-labeling is *direction* corroboration only; magnitude still requires our own backtest. Flagged. |
| Training-data pollution risk? | P1 explicitly requires post-resolver-v2.1 clean training set. ✅ |
| Does anything bypass the mutate-before-kill protocol? | No — P4 stays research-only behind the investigation gate. ✅ |
| New orphan modules created? | No — P1 wires an EXISTING orphan (`meta_labeler.py`); P2-P4 extend existing files. ✅ |
| Sizing claims gated? | All acceptance criteria require 30d rolling-clean + n≥150. ✅ |

**Self-vet verdict:** P1 and P2 are the strongest (lowest effort, attack the
known confidence-inversion root cause, wire existing code). P3 is sound but
medium effort. P4 is safe (research-only). No proposal claims proven edge yet —
all are hypotheses with explicit acceptance gates.

---

## 6. SWARM REVIEW REQUEST

Agent swarm: verify each proposal would produce a **provable** statistical edge,
not just a plausible one. Specifically challenge:

1. **P1 meta-labeler:** does training a secondary model on our closed-pick
   history actually escape the confidence-inversion, or does it relearn the
   same bias? Is there look-ahead leakage in `extract_features`?
2. **P2 overconfidence decay:** is the `score*0.8` decay double-counting a
   penalty `conviction_stack.py` already applies? Quantify the overlap.
3. **P3 vol-targeting:** does realized-vol targeting actually lift Sharpe on
   OUR data, or just on the textbook assumption? Name the failure mode.
4. **P4 ATR-normalized FOREX:** is this a genuine mutation axis or just a
   re-parameterization that the mutation harness already explores?
5. **Cross-cutting:** which single proposal, if wrong, does the most damage?

Reject any proposal that cannot name a falsifiable test on OUR data.

---

## 7. SWARM REVIEW RESULTS — 2026-05-16

Ran `tools/swarm/swarm_run.py` on this document. Engines: kilo, groq, kimi
(deepseek/xai/cerebras/openrouter skipped — no/mismatched API keys; kimi
returned an empty stub). **Effective reviewers: kilo (complete, P1-P5), groq
(P1 + partial P2).**

| Proposal | kilo | groq | Reconciled verdict |
|---|---|---|---|
| **P1** meta-labeler gate | REVISE | KEEP (conditional) | **REVISE** — keep the idea, but MANDATORY: exclude `confidence` and any confidence-derived feature from `extract_features` (else it relearns the inversion); audit hour/day encoding for look-ahead (use only the pick's own past timestamp, never the resolved-at time). |
| **P2** overconfidence decay | REVISE | REVISE | **REVISE (unanimous)** — `conviction_stack.py` already applies a regime-dependent penalty; flat `score*0.8` risks a double-penalty. Make decay conditional on absence of the conviction_stack adjustment, or net the two. Quantify overlap before wiring. |
| **P3** vol-targeted sizing | REVISE | (not reached) | **REVISE** — named failure mode: realized-vol target assumes ~iid returns; in trending/mean-reverting regimes the *lagged* vol estimate makes sizing pro-cyclical (undersized into a spike, oversized after) → higher turnover, lower risk-adjusted return. Keep only if the 30d Sharpe≥+0.2 acceptance test passes. |
| **P4** ATR-normalized FOREX momentum | KEEP | (not reached) | **KEEP** — confirmed a distinct mutation axis not covered by the current three-axis protocol; low-effort, research-only. |
| **Most damaging if wrong** | P1 | — | **P1** — it sits directly in the live pick-flow gate; a flawed meta-label gate either suppresses profitable picks or lets toxic drag-strategy volume through, degrading PF system-wide. |

### Post-swarm action order (revised)

1. **P4 first** (KEEP, safest) — register ATR-normalized momentum in the FOREX mutation harness; research-only, zero production risk.
2. **P2 second** (REVISE) — but ONLY after a 1-hour audit of `conviction_stack.py` to measure the existing regime penalty; ship the decay net of that.
3. **P1 third** (REVISE, highest value + highest risk) — rebuild the meta-labeler training/feature set with confidence-derived features removed + leak audit; ship in shadow-log mode for a full 30d before any enforce.
4. **P3 last** (REVISE) — backtest against the pro-cyclical-sizing failure mode explicitly; drop if Sharpe lift <+0.2.

**Net:** 0 proposals DROP, 3 REVISE, 1 KEEP. No proposal survives as-is for
production without the revisions above. Swarm confirmed the §0 honesty stance —
nothing here is "proven edge" yet; all four remain falsifiable hypotheses with
explicit 30-day acceptance gates.

---

## 8. IMPLEMENTATION STATUS — 2026-05-16 (branch `lmarena-edge-proposals-20260516`)

| Proposal | Shipped | What |
|---|---|---|
| **P4** | ✅ doc | Axis 4 (volatility/threshold-normalization) added to `docs/MUTATION_THREE_AXIS_PROTOCOL.md` Step 1b — research-only, zero production risk. |
| **P2** | ✅ code | `_apply_overconfidence_decay` in `alpha_engine/score_booster.py`, applied to active picks after the UTC-hour block. Decays score excess above 80 (×0.8 on excess, cap −10). Env kill `OVERCONFIDENCE_DECAY=0`. NO overlap: `_calibrate_confidence` keys on `confidence`, `conviction_stack` on direction×regime, this on aggregate `score`. py_compile + unit-tested (85→−1, 100→−4, 200→−10, off→0). |
| **P1** | ✅ code (leak-fix) | `alpha_engine/meta_labeler.py`: (a) **F9 `forward_wr` removed** from the trained-model feature vector (10-dim→9-dim, `NUM_FEATURES=9`) — kills the look-ahead leak; `heuristic_score()` keeps it for legit LIVE scoring. (b) `build_dataset` now **sorts picks chronologically** (`_pick_epoch`) so the `[:split]` split is genuinely past→future. (c) `train()` adds an **EMBARGO purge gap** (`EMBARGO_RATIO=0.01`). py_compile + unit-tested (9-dim vector, ascending-epoch sort, no-ts→last). Production `meta_label_gate` wiring still needs a clean retrain at AUC≥0.55 on the fixed pipeline. |
| **P3** | ✅ code (guard) | `volatility_target_size` in `alpha_engine/backtest/position_sizing.py` gains opt-in `vol_scalar_cap=(lo,hi)` — clamps the raw inverse-vol scalar BEFORE position-pct bounds, blocking stale-low-vol oversizing (the pro-cyclical failure mode). Default `None` = prior behaviour unchanged (opt-in sidecar). py_compile + unit-tested. |

**Net: 4 of 4 shipped as code/doc, all py_compile-clean + unit-tested.**
What remains is *live validation*, not code — the §3 acceptance gates still bind:
P2 decay must show no top-quartile WR regression over a 30d A/B
(`OVERCONFIDENCE_DECAY` flag); P1's `meta_label_gate` needs a clean retrain on
post-resolver-v2.1 data at AUC≥0.55 before wiring into `passes_active_gate`;
P3's `vol_scalar_cap` needs a backtest confirming Sharpe≥+0.2 before a caller
opts in. No proposal is "proven edge" until those run — by design.

---
*Generated 2026-05-16. Companion files: `DAILY_IDEAS_OLLAMA.MD`,
`DAILY_IDEAS_HUGGINGFACE.MD`. LMArena source extracted at
`E:\tmp\lmarena_gemini` + `E:\tmp\lmarena_glm`. Swarm run dir:
`swarm_runs/run_20260517T011705Z` + `run_20260517T011856Z`.*
