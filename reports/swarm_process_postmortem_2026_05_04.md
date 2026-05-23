# Swarm Process Postmortem — Filter Bug PRs #746/#747/#748

**Date:** 2026-05-04
**Trigger:** Swarm + subagent reviewers all approved patches treating symptoms; external Kimi audit found the real root cause (`_wireThisMonthOverride` capture handler with `stopImmediatePropagation()` swallowing synthetic clicks from `_activateNextMonth`).

## What we missed

- **Synthetic-click swallow:** `_wireThisMonthOverride` runs in capture phase on `document` and calls `stopImmediatePropagation()`; the programmatic `thisMonthBtn.click()` inside `_activateNextMonth` (and the handler's own re-dispatch) is therefore never seen by React, so React stays on whatever filter was previously active while our flag flips to Next Month — both filters live simultaneously.
- **applyFilters mutex absence:** 7+ async sources (120/180/200ms timeouts, 500ms observer, 800ms click debounce, 0ms loop-guard re-run, 2500ms init) call `applyFilters()` with no global re-entry guard, so passes interleave on partially-mutated DOM and the loop-guard's hide-streak counter goes nonsensical.
- **parseCardDisplayedDate centered-delta wrap:** `if (idx < now.getMonth()) year += 1` mis-wraps near year boundaries — January cards in February become 2028; November/December cards in January stay in current year.
- **UTC "today" timezone bug:** `_today = new Date().toISOString().slice(0,10)` is UTC, so after ~8pm EDT today's local events get filtered out of `__RAW_EVENTS__`.

## Why we missed it

- **Prompt-design issues:** Our review templates for #746/#747 listed *six leading questions about the patch as written* ("any logic bug introduced", "does the loop-guard fix correctly...") — they asked engines to *validate the diff*, not to ask "is this the actual root cause?" The brainstorm prompt asked for "5 most-likely root causes" but pre-anchored on the symptoms (year-strip, eventData gate, feed drift) seen in console logs.
- **Tool/context issues:** We sent **diff hunks plus narrative** rather than whole-file scope. Kimi had read access to the full 5,700-line file and grep across all listeners; our engines only saw ~50 lines around each edit site. Critically, no engine was asked to enumerate *all* `document.addEventListener('click', ..., true)` capture handlers and trace what happens to a programmatic `.click()`. None ran a Playwright trace; the subagent report was static-analysis only.
- **Cognitive bias:** The first subagent produced a confident, detailed "eventData gate + recurring fallback + feed drift" hypothesis. Every subsequent prompt embedded that framing. Five engines converged because they were all answering the same anchored question. No one was tasked to *disprove* the hypothesis.

## Process changes

1. **Two-prompt protocol for runtime bugs.** Prompt A: "given symptoms X, enumerate root causes — you may NOT assume the prior investigation is correct, list at least 3 hypotheses that contradict it." Prompt B (separate engine, fresh context): "red-team this patch — describe a DOM/event sequence where it fails."
2. **Whole-file scope for DOM/event bugs.** When a bug involves event propagation, listeners, or React/vanilla interop, attach the full file (or grant tool access), and *require* the engine to list every capture-phase listener and every `stopPropagation`/`stopImmediatePropagation` call before answering.
3. **Mandatory Playwright/console-trace evidence.** For any "filter/UI/click" bug, a swarm review is non-binding without a runtime trace artifact (CDP event log + DOM snapshot per click). Static review approves only typo-class fixes.
4. **Devil's-advocate engine required.** One engine per swarm gets the prompt: "the patch is wrong; explain why." Verdict ladder: APPROVE requires the red-team engine to fail to find a counter-case.
5. **Subagent vs swarm vs both:** subagent for *scoping* (read repo, produce hypotheses + reproducer); swarm for *adversarial validation* of the leading hypothesis with red-team engine; both, in that order, for any production-touching UI bug.

## Session experiment

Counter-test prompt to run now against gpt-5/kimi/grok with full file attached:

> "List every `document.addEventListener('click', ..., true)` in `TORONTOEVENTS_ANTIGRAVITY/index.html`. For each, identify whether it calls `stopImmediatePropagation`, and trace what happens when `_activateNextMonth` calls `thisMonthBtn.click()` programmatically. Does React's chip-state update? Show the event-loop timeline."

If any engine produces "the synthetic click is swallowed because the capture handler stops propagation before React's delegated listener runs", the protocol works. If none do with full-file context, escalate to mandatory live Playwright trace.

## Durable rule (memory-worthy)

**When swarm review is asked to validate a patch, also run a parallel red-team prompt with no patch context that asks the engine to independently diagnose the bug. Disagreement between the two = block merge until reconciled.**
