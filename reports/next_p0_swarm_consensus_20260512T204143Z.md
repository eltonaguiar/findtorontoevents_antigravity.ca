# Swarm consensus — Next P0 cluster plan review

**Date:** 2026-05-12T20:50Z
**Plan:** `reports/next_p0_cluster_plan_20260512T204143Z.md`
**Round 1 (free):** groq (returned), ollama_cloud (timed out 600s)
**Round 2 (paid):** cerebras, xai, deepseek (all returned)

## Per-question consensus

| Q | groq | cerebras | xai | deepseek | Consensus |
|---|---|---|---|---|---|
| Q1 ranking | PASS | ADD leverage | PASS | PASS | **PASS (3/4)** — cerebras hallucinated §2.1/§3.4/§4.2 refs that don't exist in plan; discount |
| Q2 DB vs JSON | BOTH | BOTH | BOTH | JSON | **BOTH (3/4)** |
| Q3 block vs warn | WARN | BLOCK | WARN | BLOCK | **SPLIT (2/2)** — default WARN, add config flag for BLOCK |
| Q4 cap review | REVIEW_FIRST | REVIEW_FIRST | REVIEW_FIRST | REVIEW_FIRST | **UNANIMOUS REVIEW_FIRST** |
| Q5 enforcement | NONE | gate suspect | NONE | NONE | **NONE (3/4)** — cerebras concern aligns with memory `feedback_gate_at_execution_not_generation`; spot-verify before next P0 ships |
| Q6 V1 root | DIFFERENT | DIFFERENT | DIFFERENT | DIFFERENT | **UNANIMOUS DIFFERENT** |

## Net actionable verdict

GO with 3 P0s as ranked + 4 binding rules:

1. **P0-#1 verify_system_pf.py** — implement BOTH DB + JSON
   cross-check. Per Q2 consensus. DB output canonical; JSON
   sanity-check catches stale-read races.

2. **P0-#2 asset_class_concentration** — ship as WARN tier with
   explicit `concentration_block_threshold` config (default 0.85)
   that escalates to BLOCK. Honors split Q3. Default WARN avoids
   silent kill of valid concentrated edges; config flag preserves
   ability to go hard-block.

3. **P0-#3 capped_vs_raw_pnl_gap** — review the cap thresholds
   themselves BEFORE the disclosure UI is built. Unanimous Q4.
   This is now a pre-step blocker: emit `cap_thresholds_audit.md`
   listing current values + their rationale before any UI work.

4. **Spot-verify execution-gate enforcement** — per Q5 cerebras
   concern + memory `feedback_gate_at_execution_not_generation`,
   add a one-time grep audit confirming the 7 shipped P0
   blocklists actually fire at exec, not just intake. Quick check
   (under 30 min); does not block other P0s.

## Cerebras fabrication flag

Cerebras response cited "§2.1 Leverage-Exposure-Limit", "§3.4", "§4.2",
"§5.1", "§6.3" — none of these sections exist in the plan. Its
single ADD vote for a new P0 is rejected. Its Q5 concern about the
execution gate aligns with prior memory, so kept as the verification
follow-up above.

## Cost

| Round | Engines | Cost | Time |
|---|---|---|---|
| 1 (free) | groq + ollama_cloud | $0.0034 | 600s (ollama timed out, groq 1.4s) |
| 2 (paid) | cerebras + xai + deepseek | TBD (see _summary.json) | parallel ~60s |

## NFA

Research surface only. Verdict steers next implementation PRs but
does not modify trade execution.
