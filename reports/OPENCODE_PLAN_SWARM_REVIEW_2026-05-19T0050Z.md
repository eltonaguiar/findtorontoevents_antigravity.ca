# Swarm review — OpenCode session ses_1bd0 plan — 2026-05-19T0050Z

Source plan: opencode peer (Qwen3.6 Plus Free runtime, `session-ses_1bd0.md`,
2026-05-19 21:26-21:36 UTC). 3-engine swarm critique via
`tools/swarm/swarm_run.py` (xAI grok-3-latest, Cerebras, Ring 2.6 1T via
OpenRouter). Outputs: `swarm_runs/opencode_plan_review_2026-05-19T0040Z*/`.

## Swarm verdict

| Engine | Overall | Key disagreement |
|---|---|---|
| **xAI** | **DISAGREE** | "Canonical `pf_registry.json` directly contradicts OpenCode verdicts on CRYPTO/FOREX/COMMODITY" |
| **Cerebras** | PARTIAL_AGREE | "FOREX mis-labelled as BLOCKED despite a healthy PF of 1.49" |
| **Ring 2.6 1T** | PARTIAL_AGREE | "Overstates COMMODITY (n=55 sub-floor) and ETF (n=18 noise); H-008 P1 priority unjustified" |

## Consensus pushback (3/3 or 2/3)

### 1. FOREX is NOT blocked — it's borderline T2 (2-of-3 flag)

OpenCode said: BLOCKED until SHORT-only rehab / cta_replicator rescue (PF 0.33).

Canonical `pf_registry.json` 2026-05-19T19:46Z `by_asset_class_policy_clean_net`:
**FOREX PF 1.49 / WR 56.1% / n=148** — closest class to T2 floor today.

OpenCode's 0.33 figure must reference an older or raw (pre-policy-clean) view.
**Cerebras (correct):** "Viable — canonical PF 1.49 with n=148 exceeds the
sub-floor threshold."

**Action:** Reconcile — opencode's plan ignores the canonical lift.
`cta_replicator` FOREX (n=97 PF 2.38) is the lead, not the rescue.

### 2. OpenCode overstates COMMODITY (Ring flag)

OpenCode said: NARROW REAL (COT 72-77% WR).

Canonical: COMMODITY PF 1.42 / n=55 — **sub-density** (n<100 floor). Calling
n=55 "narrow real" risks premature capital allocation.

**Action:** Keep COMMODITY at WATCH + accrue to n≥100 before T2 promotion.

### 3. OpenCode overstates ETF (Ring flag)

OpenCode said: BORDERLINE_T2 (PF 1.72 on n=18 sub-floor).

n=18 is noise scale, not "borderline." PF 1.72 is artifact-scale at that n.

**Action:** Class stays NOT_READY until n≥100 + harness clearance. Per
already-shipped `MONEY_MAKER_READYV2_NORTH_STAR_2026-05-19T2350Z.md`.

### 4. H-008 BOND 2s10s redesign P1 → DOWNGRADE to P2 (2-of-3)

OpenCode said: H-008 BOND 2s10s continuous-position variant, P1 priority.

**xAI:** "Continuous-position variant may violate sign-stability (cf. H-037
rejection); run `edge_stability_harness.py` on 2s10s before P1 commit."

**Ring:** "P1 priority premature — redesign may consume session bandwidth
before D1/D2 ops filters validate. Downgrade to P2; require `pf_registry`
entry + n≥50 post-gate before commitment."

**Cerebras:** Supports direction, run harness first.

**Action:** Update todo — H-008 BOND redesign DOWNGRADED from opencode-P1 to
**P2 conditional on canonical `is_admissible()` clearance** + n≥50 post-FDR
gate.

### 5. H-009 / H-010 / H-011 pre-reg priority (split)

- xAI: DEFER all 3 (queue post COT dedup + n≥100 filter)
- Cerebras: TOP_3 for H-009 (COMMODITY inventory-surprise) only; DEFER H-010/H-011
- Ring: DEFER all (need EQUITY/ETF admissible threshold first)

**Action:** H-009 may be worth pre-registering NOW (M-107 commit BEFORE
backtest), but **only if data pipeline ready** (Cerebras condition).
H-010/H-011 defer.

### 6. OpenCode missed our swarm-approved ops (2-of-3)

OpenCode plan did NOT account for our prior 2-of-3 swarm recommendations
(commit ab266e9):
- D1 `EMITTER_WHITELIST_ENFORCE` flip = Option C (forward 200-close)
- D2 `HARNESS_FDR_GATE` = Option A unanimous (BH q=0.10)

**Ring (cleanest):** "All per-class verdicts and pre-reg queue are
**unfiltered** — re-run `is_admissible()` with ops gates active before any
verdict."

**Action:** Apply D1/D2 retroactively to opencode's per-class table before
ingesting any verdict.

## Must-NOT-ship from opencode (3-engine consensus)

- Any code (opencode self-restricted: "NEVER commit code")
- COMMODITY "NARROW REAL" label at n=55 (would justify premature capital)
- ETF "BORDERLINE_T2" label at n=18 (could read as quasi-admissible)
- H-008 BOND promoted to P1 without canonical admissibility check
- H-009/H-010/H-011 pre-reg without D2 FDR clearance — violates 0-admissible
  invariant

## What OpenCode got right (worth keeping)

- Endorses `EDGE_VERDICT_2026-05-18.md` + 11/11 harness kill consensus ✓
- Flags Kimi `MASTER_ACTION_PLAN_2026-05-18.md` CRYPTO=MONEY_READY as FALSE ✓
- Cross-session continuity via holographic memory ✓
- Research-only discipline (zero code shipped) — appropriate for synthesis
  rounds ✓

## Updated next-3 actions (taking opencode + swarm critique into account)

1. **Apply D1 + D2 to opencode's per-class table** — re-run
   `is_admissible()` with FDR gate before promoting any class verdict.
2. **Downgrade H-008 BOND to P2** — run unmodified harness + BH-FDR q=0.10
   on continuous-position 2s10s variant; require `pf_registry` entry + n≥50
   post-gate.
3. **H-009 COMMODITY inventory-surprise:** pre-register only if data pipeline
   ready (M-107 commit BEFORE backtest); defer H-010/H-011.

## Companion docs

- `reports/MONEY_MAKER_READYV2_NORTH_STAR_2026-05-19T2350Z.md` (eb1053a)
- `reports/MONEY_MAKER_READYV2_ADDENDUM_TODOS_2026-05-19T0010Z.md` (7998b6d)
- `reports/MONEY_MAKER_READYV2_FREEBUFF_INTEGRATION_2026-05-19T0030Z.md` (1a7607b)
- `reports/EDGE_VERDICT_2026-05-18.md` — canonical no-edge frame
- Swarm outputs: `swarm_runs/opencode_plan_review_2026-05-19T0040Z{,_ring}/`

---

*Generated 2026-05-19T0050Z. Input: 3-engine swarm (xAI / Cerebras / Ring 2.6
1T). No fabrication. All canonical-PF numbers verified against
`pf_registry.json::by_asset_class_policy_clean_net` 2026-05-19T19:46Z.*
