# Ollama 3-Model Consult Synthesis — /money-maker-ready 2026-05-12

Background agent `aee195735c7c1d95e` queried 3 local Ollama models on
real-money-readiness for `cot_positioning + CT=F`.

## Availability

| Model | Status | Lines |
|---|---|---|
| `jcyhsiao/qwen3.5cloud:latest` | RETURNED | 174 lines (TTY-noise-decoded below) |
| `qwen2.5-coder:14b` | EMPTY (likely model-pull/runtime issue) | 0 |
| `hf.co/TeichAI/Qwen3-14B-Claude-4.5-Opus-High-Reasoning-Distill` | EMPTY (likely model-pull/runtime issue) | 0 |

Only qwen3.5cloud generated substantive output. The other two need
investigation (most likely cause: model not pulled or out-of-memory on a
14GB-class CPU).

## qwen3.5cloud — Top 5 recommendations (decoded from TTY-mangled output)

1. **Resolve COT Step 3 Conditional** — investigate the fold_1 outlier
   (10% WR vs 99% average) causing the walk-forward variance breach.
   Either exclude the cohort with a regime-gate, or document the regime
   discontinuity and accept the risk.
2. **Execute PR #2** — flip `active_picks_sync.py` from DRY-RUN to live
   writer to ensure `closed_picks.json` integrity. This is the upstream
   bridge identified by Investigator B that's keeping raw-pick outcome
   coverage at 0.09%.
3. **Verify Step 7 Monte Carlo** — confirm the risk-of-ruin cron job
   produces results within tolerance thresholds at $10k (<5% margin call
   prob) and $25k (<1%).
4. **Finalize Paper Pilot** — ensure `/audit/paper_pilot.html` shows
   stable SHADOW state performance matching the 90% WR over a defined
   period (e.g., 7 days minimum, ideally 4 weeks per the testing plan).
5. **Enable Real Money Gate** — update `/audit/real_money.html` to
   reflect PASS on all COT-specific gates once recs 1-4 complete.

## Cross-model convergence

Only one model returned, so no cross-validation possible. However, the
single model's 5 recommendations align tightly with our existing pending
P0/P1 list — no new direction proposed. This is a confirmation, not a
divergence.

## Strongest single recommendation

**Rec #2 (execute PR #2 active_picks_sync flip to live writer)** is the
critical-path blocker. Without it, `closed_picks.json` will never receive
new entries from `at_raw_picks` and the resolver remains starved. The
paper-pilot gate (Rec #4) can't graduate without fresh closed picks
flowing.

## Synthesis verdict (≤150 words)

The qwen3.5cloud assessment converges fully with our internal session
plan — no new vectors, but useful external validation of priorities. The
single 14B-class model produced a clean Top-5 list inside the 300-word
cap; the other two models failed to generate, which the agent reported
without retry/recovery. Recommendation: investigate why qwen2.5-coder:14b
and the Qwen3-claude-opus-distill variant didn't respond (likely
OOM-on-load given the 14B parameter count and 9GB+ disk size). The
critical path remains: (1) PR #2 active_picks_sync flip → live writer,
(2) regime-gate add to handle Step 3 fold_1 outlier, (3) 4-week paper-
pilot graduation, (4) Step 7 ROR MC tier verdict, (5) Real Money hub
gate-status table refresh once 1-4 clear.

## Refs

- `reports/ollama_consult_money_maker_qwen35cloud.md` (raw output, TTY-noisy)
- `reports/ollama_consult_money_maker_qwen25coder14b.md` (empty)
- `reports/ollama_consult_money_maker_qwen3-claude-opus-distill.md` (empty)
- Investigator `aee195735c7c1d95e` 2026-05-12
- Prior synthesis: `reports/cot_steps_1_to_5_synthesis_2026-05-12.md`
- Master plan: `updates/2026-05-11-money-maker-master-plan.html`

## NFA

Research surface. The 5 recs align with the in-flight roadmap; consult
adds external corroboration but no new direction. Real-money sizing still
gated on the 10-step Lopez de Prado AFML readiness pipeline.
