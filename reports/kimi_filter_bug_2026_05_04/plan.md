# Code Review Plan: findtorontoevents.ca Event Filtering

## Context
The codebase is a single large `index.html` (~5740 lines) that acts as the canonical homepage. It contains imperative JavaScript that injects filters and thumbnails into a Next.js React app. The filtering logic is complex because it overrides/manipulates React's native chip-based date filtering.

## Bugs Reported by User
1. **Dual activation**: "This Week" and "Next Month" filters could both be active simultaneously (possibly due to lag / rapid clicking)
2. **Next Month bug**: User clicked "Next Month" but didn't see next-month events
3. **This Month bug**: User clicked "This Month" and saw events from 2025 (already partially fixed per code comments)

## Review Stages

### Stage 1 — Static Code Analysis (Parallel Subagents)
Load the vibecoding-general-swarm skill for code review guidance. Deploy 3 parallel specialist reviewers:

1. **RaceCondition_Reviewer**: Focus on event listener ordering (capture phase), `stopPropagation`, `stopImmediatePropagation`, `setTimeout` chains, MutationObserver timing, and flag/state transitions. Examine how rapid user clicks could leave two filters active.
2. **DateLogic_Reviewer**: Focus on date arithmetic, timezone handling (UTC↔EDT), month-boundary logic, year wrap-around, past-event filtering, recurring event matching, and the `__parseCardDisplayedDate__` fallback.
3. **DOM_React_Reviewer**: Focus on React hydration detection, DOM mutation observer loops, chip re-injection across rerenders, lazy-loading interactions, and counter-sync accuracy.

### Stage 2 — Cross-Validation & Synthesis
Merge findings, identify root causes, and produce prioritized fix recommendations.

### Stage 3 — Final Report
Produce a markdown report with: bug root causes, fix recommendations, and code snippets.

## Key Files
- `/mnt/agents/repos/index.html` — canonical homepage with all filter logic
- Relevant line ranges: ~3236-4555 (filter controls, applyFilters, Next Month chip, This Month override, event listeners, init)
