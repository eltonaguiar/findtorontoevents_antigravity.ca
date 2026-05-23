# Hermes Giant-Swarm Value Assessment — 2026-05-04

**Verdict: MIXED — leans WORTH-IT for ideation breadth, OVERKILL for acceptance.**

## What Hermes shipped

| Asset | Count / LOC | Novelty |
|---|---|---|
| Local branches `pr1/pr2/pr3-*` | 3 branches, no push auth | Branch hygiene only |
| `prs/PR{1,2,3}-*.md` + `PR{1,2,3}-60MODEL-ADDITIONS.md` | 6 files, ~1,120 lines | Format-aligned PR templates with 30+ feature ideas per surface |
| `updates/SWARM-ANALYSIS-task{1,2,3}-*.md` | 3 files, ~501 lines | Task-by-task summaries; some duplicate of `task{1-3}-summary.md` from earlier Hermes wave |
| `updates/{kimi-audit-gap, toronto-event-sources, sports-betting-enhancements}.md` | 3 files, ~240 lines | Mostly redundant with prior Hermes outputs + my Kimi-review files |
| `tests/events-page.spec.ts` | 102 lines | **Aspirational, not runnable on live page** |
| `tests/audit-pages.spec.ts` | 189 lines | Aspirational |
| `tests/test_event_filters_chips.spec.ts` | 86 lines | Possibly useful (chip filter regression) |
| `TORONTOEVENTS_ANTIGRAVITY/index.html` | +100 lines | Edits on `pr1` branch — needs review for what changed |
| `audit_dashboard/template.html` | edited | Probably the HTML comment bug fix (already known) |

**Total:** ~1,860 lines of MD + 377 lines of tests + 2 HTML edits + 6 local branches.

## What was novel vs duplicate

- **Novel-and-useful:** the 30+ feature ideas per surface in `PR{1,2,3}-60MODEL-ADDITIONS.md` (Mercury-v1 to v20 attribution). Concrete examples not in my synthesis: WCAG 2.2 SC 2.4.11 / 4.1.3 / 2.5.8 specific gates; soft assertions pattern for a11y; token bucket + exponential backoff for rate limiting; semantic search + Fuse.js fuzzy matching; Betting Circles cross-product idea.
- **Duplicate of my work:** the 5-gate matrix per asset class (already in my Kimi archive); 15-source Toronto data list (already in my synthesis Top-10); HTML comment bug fix verdict (already noted).
- **Duplicate of repo state:** `tests/test_event_filters_chips.spec.ts` likely overlaps with my just-landed `fix/today-tomorrow-week-zero-events-2026-05-04` branch's regression test.

## Critical issue with Hermes tests

Hermes's `tests/events-page.spec.ts` lines 30-39 assert `aria-pressed='true'` on chip filter buttons and uses `page.getByText(filter, {exact:true})`. But the live page uses Tailwind class string `from-[var(--pk-600)]` for active-state detection (per QA-02 in my events super-swarm). **These tests will fail on the live page** — they're written to an aspirational DOM, not the real one.

## Was the 60-model swarm worth the compute?

- **For ideation:** YES — 30+ specific feature ideas with WCAG citations and library names is more breadth than my 11-engine swarm produced. Mercury models across versions provided genuine variety.
- **For correctness:** NO — none of the test code references actual selectors from the live page. Output is plausible-looking but unrunnable. My Kimi-review subagent caught the same issue with Kimi's React .tsx targeting a vanilla codebase.
- **For shipping:** OVERKILL — there is no ship-this-week PR among Hermes's outputs. All 3 PR branches are local; tests don't run; HTML edits unverified. The ratio of "useful ideas" to "shippable artifacts" is roughly 30 ideas : 0 ships.

## Recommendation

1. **Harvest the 30+ feature ideas** into a single backlog (merge with my super-swarm synthesis).
2. **Discard `tests/events-page.spec.ts` + `tests/audit-pages.spec.ts`** as written; rewrite against actual selectors. Keep `test_event_filters_chips.spec.ts` after diff against my regression test.
3. **Don't commission another giant Mercury swarm** for this scope — the marginal value drops sharply. 5-8 reliable engines + a strong reviewer is better.
4. **Proceed to the unified test/integration plan** with Hermes's ideas as inputs, but my Kimi-review subagent verdicts as the architecture anchor (vanilla JS, no PHP backend on 50webs, etc.).

## CRITICAL CAVEAT — "60 models" was 60 calls to the same model

Per `FINAL-MASTER-SUMMARY-60-MODELS.md`: all 60 calls used `tencent/hy3-preview:free`. The "Mercury-v1 to v20 / Claude-v2 to v20" labels are cosmetic — there is no actual model diversity. This means:

- The 30+ feature ideas reflect ONE model's latent space sampled with temperature variation, not consensus across diverse architectures.
- The "all 60 models agreed on X" framing is misleading — it's "this one model said X across 60 prompts".
- My 11-engine super-swarm (claude / deepseek / cerebras / opencode / kilo / gemini / xai / ollama_cloud — 7 truly different model families) is a stronger correctness signal even though it's smaller.

This downgrades Hermes's swarm from "MIXED 6/10" to **"OVERKILL with low-cost ideation value, 4/10"**. Use as a brainstorm bank only; do not weight any consensus claim as cross-model agreement.

## Score (revised): 4/10 — OVERKILL on compute, useful only as single-model ideation breadth.
