# Multi-Specialist Debugging Strategy

Source: extracted from the Kimi run that found the `findtorontoevents.ca` filter bug our single-prompt swarm missed (2026-05-04). Reports: `reports/kimi_filter_bug_2026_05_04/FINDINGS.md`, `audit_report.md`, `date_bugs_report.md`, `react_dom_mutation_observer_analysis.md`, `plan.md`. The bug — `stopImmediatePropagation()` swallowing a same-element programmatic `click()` — was missed by 3 prior PRs (#746, #747, #748) where one general reviewer was asked to look at the whole problem at once.

## When to use this strategy

Use it for **frontend bugs with multi-system symptoms** — race + DOM + dates simultaneously. Specifically:

- Symptom touches click handlers AND date logic AND DOM mutation observers.
- "Two filters appear active simultaneously" / "wrong month shows" / "events vanish in the evening" all reported in one session.
- Architecture is a vanilla-JS shell wrapping a React/Next.js app (or any framework with reconciliation).
- Single-reviewer attempts have produced fixes that look right but don't resolve the symptom.

**Do NOT** use it for:
- Pure data bugs (yfinance returned wrong PnL → use `cross-verification-auditor` + asset-class specialist instead).
- Single-system bugs where one persona obviously fits (a JPY-cross routing bug → `forex-specialist`).
- Trivial issues — the overhead of 3 specialists + coordinator is wasted on a 1-line patch.

## The specialist split (Kimi's pattern)

Three parallel specialists + one coordinator:

| Persona | Focuses on | File |
|---|---|---|
| `race-condition-specialist` | capture-phase listeners, `stopImmediatePropagation`, synthetic clicks, mutator re-entrancy, global flag mutation | `race_condition_specialist.md` |
| `datetime-timezone-specialist` | UTC↔local, ISO parsing, year-wrap heuristics, "today" computation, multi-day overlap | `datetime_timezone_specialist.md` |
| `react-dom-specialist` | MutationObserver loops, inline-style revert, sibling-positional guards, hydration polling, lazy-load batch timing | `react_dom_specialist.md` |
| `coordinator-synthesizer` | merges specialist outputs, ranks, buckets by deploy-readiness | `coordinator_synthesizer.md` |

## Phases

1. **Plan** (coordinator-synthesizer drafts only) — short `plan.md` naming the three specialists, their scopes, the file under review, and the line ranges. Mirrors `reports/kimi_filter_bug_2026_05_04/plan.md`.
2. **Parallel specialists** — fan out the three specialist personas against the same file/line range, in parallel. They do NOT see each other's output.
3. **Coordinator merge** — coordinator-synthesizer reads all 3 reports, builds the unified TL;DR table, deduplicates by `(file, line-range)`, ranks, buckets.
4. **Plan emission** — single `FINDINGS.md` (executive) + 3 specialist deep-dives + `plan.md` (deploy-priority buckets).

## Required outputs per specialist

Each specialist report must contain, for every finding:

- Severity (CRITICAL / HIGH / MEDIUM / LOW)
- Location (`file:line-line` cite — no hand-waves)
- Root cause (3-6 sentences with concrete inputs/outputs)
- Fix recommendation (a code snippet, not prose)
- Affected scenario (one user story)

Plus a roll-up summary table at the bottom.

## Coordinator output rollup

`FINDINGS.md` structure (mirrors Kimi's):

1. **TL;DR table** — `| User-reported bug | Root cause (cited) | Status |`
2. **Architecture context** — 1-2 paragraphs naming the design decision that produces the bug class.
3. **CRITICAL findings** (deploy today)
4. **HIGH findings** (deploy this week)
5. **MEDIUM findings** (next sprint)
6. **Recommended fix priority** — Immediate / This Week / Next Sprint buckets, numbered.
7. **Affected user scenarios** — `| Scenario | Bug | Result |` table.

## Worked example: the filter bug (2026-05-04)

- **User report**: "This Week and Next Month both active simultaneously; This Month shows 2025 events; Next Month sometimes empty."
- **Plan**: 3 specialists against `TORONTOEVENTS_ANTIGRAVITY/index.html` lines 3236–4600.
- **Race specialist** found the smoking gun: `_wireThisMonthOverride` (line 4376) calls `stopImmediatePropagation()` in capture phase, then `_activateNextMonth` (line 4256) calls `thisMonthBtn.click()` — the synthetic click is **swallowed**, React stays on This Week while `__nextMonthFilterActive__ = true`. Fix: `if (!e.isTrusted) return;` at top of capture handler, and `setTimeout(thisMonthBtn.click, 0)` in `_activateNextMonth`.
- **DateTime specialist** found `__parseCardDisplayedDate__` line 4333 wraps January cards to 2028 in February (and Nov/Dec stays in current year in January), plus `_today = new Date().toISOString().slice(0,10)` line 94 silently drops evening EDT events. Fixes: centered-delta wrap; local-date "today" formatter.
- **DOM specialist** found 5 React-reconciliation hazards (inline `style.display` on `.group` parent, MutationObserver self-trigger loop, fragile `previousElementSibling` guard, 500ms debounce too short for lazy-load waves, rAF hydration polling stalls in background tabs).
- **Coordinator** ranked: 4 CRITICAL findings deploy today (isTrusted guard, applyFilters mutex, UTC-today fix, parseCardDisplayedDate wrap), 5 HIGH this week, 1 architectural rewrite next sprint.

The single `stopImmediatePropagation` finding was the one our single-prompt swarm missed because it requires holding three concepts in mind at once: capture-phase ordering, synthetic-vs-trusted events, and React's synthetic-event delegation. A specialist whose entire system prompt is "always check `e.isTrusted` for synthetic-click guards" cannot miss it.

## What NOT to do

- **Don't ask one engine to be all 3 specialists at once.** That was our previous mistake. The hit rate on the swallowed-click bug was 0/3 in PRs #746-#748 with a generalist prompt.
- **Don't accept severity claims without `file:line` citations.** Coordinator must reject these.
- **Don't collapse two specialists' reports at different lines** into "same bug" without verifying. They are probably two bugs.
- **Don't let the coordinator write findings.** Coordinator only ranks and buckets.
- **Don't run the specialists sequentially with shared context.** They must be independent — that's the whole point. If specialist B sees specialist A's output, B anchors on A's framing and you lose the orthogonal coverage that makes the multi-specialist split work.
- **Don't put more than 5 items in the "deploy today" bucket.** That bucket is 1-line patches with no architectural risk only.
- **Don't skip the plan phase.** Without a `plan.md` naming line ranges, the specialists drift in scope and the coordinator can't merge cleanly.
