# Action Plan Swarm Check — 2026-05-03

**Run:** `swarm_runs/action_plan_check_20260503T201011Z/`
**Preset:** `fast-cheap` (cerebras `gpt-oss-120b` + deepseek `deepseek-v4-flash`)
**Cost actual:** ~$0.0016 (cap was $0.05; well under)
**Engines OK:** 2/2 (no failures)
**Plan input:** 6-step QQ/RR/SS/TT next-batch operator queue
   (cherry-pick #745, close #723, drop commit on #724, CI remediation
    #615/#597/#661, #660↔#644 config reconcile, PENNY/MEME §4)

---

## Per-engine verdict

| Engine   | Approval                | Confidence | Top severity flagged   |
|----------|-------------------------|------------|------------------------|
| cerebras | APPROVE_WITH_CHANGES    | MED        | blocking (item 4)      |
| deepseek | APPROVE_WITH_CHANGES    | HIGH       | blocking (items 4 + 5) |

**Consensus verdict: APPROVE_WITH_CHANGES.** Plan is structurally sound;
two blocking concerns must be addressed before progressing past their
respective items.

---

## Item-by-item consensus

### Item 1 — Cherry-pick PR #745 (`MAX_HOLD_HOURS_BY_CLASS`)

- **cerebras:** major — cherry-picking before CI green could regress
  resolver. Suggests dedicated validation branch + peer review.
- **deepseek:** no concern raised, but flagged via missing_steps:
  verify resolver consistency with `asset_class_health` baseline.

→ **Action: keep as-is** (the plan already states "Awaiting CI green +
operator merge", which addresses cerebras' concern). Add a verify-step
post-merge as deepseek suggests.

### Item 2 — Close-supersede PR #723

- **cerebras:** minor — add explicit comment citing #719 + verify no
  open PRs depend on #723.
- **deepseek:** no concern.

→ **Action: keep as-is.** The proposed close-comment template
("Superseded by merged PR #719…") already covers cerebras' note.

### Item 3 — Drop commit `e4cb5b4f043` from PR #724

- **cerebras:** major — interactive rebase rewrites history, can break
  CI for contributors who fetched the branch. Prefers author re-cut a
  fresh PR.
- **deepseek:** major — risk of orphaning the 5 deep-dive reports if
  they have hidden dependencies on the dropped commit.

→ **Both engines independently prefer the "author re-cut" alternative
over interactive rebase.** Action: ask the author for a re-cut PR
rather than force-pushing a rebase.

### Item 4 — Per-PR CI remediation (#615 / #597 / #661)

- **cerebras:** **blocking** — multiple test failures will surface in
  the dashboard if merged unchanged.
- **deepseek:** **blocking** — #661's 89 collection errors are a
  structural defect (missing `StrategyValidator`), not flake; will
  block the entire swarm if merged.

→ **HARD BLOCK for #661 specifically.** Both engines agree. PRs #615
and #597 are recoverable via targeted fixes per the plan; #661 needs
the missing class added before anything else from this PR can land.

### Item 5 — #660 ↔ #644 config reconciliation

- **cerebras:** major — contradictory thresholds will corrupt
  `asset_class_health`; suggests dedicated config-cleanup PR with
  precedence rule + schema version bump.
- **deepseek:** **blocking** — plan doesn't specify *how* to detect
  contradictions; needs explicit diff + manual reconcile step.

→ **Soft block.** Add an explicit reconcile substep: "diff
`config/per_asset_thresholds.json` between #660 and #644, manually
merge, version-bump schema, commit as standalone PR." Then merge #660
→ #644.

### Item 6 — PENNY/MEME §4 policy questions

- **cerebras:** question — schedule operator policy review.
- **deepseek:** minor — set 48h deadline; escalate if unanswered.

→ **Action:** add a 48h timer + decision-log requirement. Operator-only
remains correct.

---

## Top-3 blocking concerns (must address before progressing)

1. **#661 missing `StrategyValidator` class** in
   `alpha_engine/statistical_rigor.py` — 89 collection errors. Both
   engines flagged blocking. (item 4)
2. **#660 ↔ #644 config contradiction** in
   `config/per_asset_thresholds.json` — needs explicit diff +
   reconcile substep, not just "resolve in #660 first." (item 5)
3. **PR #724 history rewrite risk** — both engines independently
   prefer author re-cut over interactive rebase to avoid orphaning the
   5 deep-dive reports. (item 3)

---

## Recommended ordering changes

| Source   | Proposed order             | Rationale                               |
|----------|----------------------------|-----------------------------------------|
| original | 1 → 2 → 3 → 4 → 5 → 6      | (as written in the brief)               |
| cerebras | **4 → 5 → 1 → 2 → 3 → 6**  | Resolve blockers + config first         |
| deepseek | step 3 ‖ step 4 (parallel) | Independent; saves wall-clock time      |

**Synthesized recommendation:**

```
  Step 4 (CI remediation, esp. #661 missing class)   [BLOCKING]
    ‖ in parallel with
  Step 3 (request author re-cut of PR #724)          [async]
    ↓
  Step 5 (config reconcile #660 ↔ #644)              [BLOCKING]
    ↓
  Step 1 (cherry-pick #745)                          [trivial after CI green]
    ↓
  Step 2 (close-supersede #723)                      [trivial]
    ↓
  Step 6 (PENNY/MEME policy, 48h deadline)           [operator-only, async]
```

This pulls the two blocking items forward, runs the async author re-cut
in parallel with CI remediation to save wall-clock, and leaves the
trivial PR-housekeeping (#745 cherry-pick, #723 close) for last when
the dependency graph is clean.

---

## Missing steps flagged by engines

- **Both:** end-to-end / integration test on `audit_dashboard` after
  all merges, to verify `performance.asset_class_health` reflects
  intended thresholds.
- **cerebras:** doc the new `MAX_HOLD_HOURS_BY_CLASS` behavior; latency
  benchmark on production scanner for SLA compliance.
- **deepseek:** decision log for PENNY/MEME §4 outcomes; cross-PR
  regression suite after steps 1-5.

---

## Caveats

- Both engines are working from plan-text + repo metadata only; neither
  inspected actual CI logs or live diffs. Their evidence cites
  plausible file paths but in some cases (e.g., cerebras citing
  `quant_engine/resolvers/max_hold_hours.py:line 42-57`) the path
  appears extrapolated rather than verified — treat path/line numbers
  as illustrative, not load-bearing.
- cerebras hallucinated a CI run URL (`actions/runs/1234567890`) — this
  is a known cerebras-API tendency (placeholder evidence); does not
  affect the verdict but confirms why MED confidence is appropriate.
- No engine failures during this check.

---

## Failed engines this check

None. 2/2 OK.

---

**Verify before progressing:**
- [ ] #661 `StrategyValidator` class added (item 4 hard block)
- [ ] #660/#644 config diff produced + reconciled (item 5 hard block)
- [ ] #724 author asked to re-cut without `e4cb5b4f043` (item 3 pref)
- [ ] 48h timer started on PENNY/MEME §4 questions (item 6)
