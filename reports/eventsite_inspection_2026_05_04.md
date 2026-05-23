# findtorontoevents.ca — Live Inspection Findings + Swarm Test Plan

**Date:** 2026-05-04
**Tool:** `tmp/full_site_inspection.js` (Playwright headless, captures console + network + JS errors + per-chip behavior + gear-icon scroll + tabular toggle)
**Artifacts:** `tmp/inspection_artifacts/full_inspection_*.json`

## Live findings (this run)

### 🚨 CRITICAL #1 — All chip filters return 0 visible cards (DOM selector or hide-mechanism mismatch)

| Chip | Counter | Visible (my DOM probe) |
|---|---|---|
| 🔥 Today | 0 | 0 |
| Tomorrow | 0 | 0 |
| This Week | 0 | 0 |
| This Month | 31 | 0 |
| Next Month | 27 | 0 |
| All Dates | 27 | 0 |

The counter (`.glow-text.tabular-nums`) says 31/27 cards visible under This Month / Next Month, but my DOM probe (`.group:not([style*="display: none"]) [class*="event-card"]:not(.event-card-hidden)`) finds 0 in every case. Two possibilities:
- (a) Cards are visible but my selector is stale (class names changed in PR #775's chip-state refactor)
- (b) Cards are actually hidden (the CSS class hide moved to a different element / the `.group` wrapper still has inline `display:none` despite PR #753's class-based fix)

Today/Tomorrow/This Week genuinely return 0 — that's a real "no events surface for users" regression.

### 🚨 CRITICAL #2 — `applyFilters` fires 20× on initial load + clear oscillation pattern

Console captures 48 `[FILTERS]` lines on a fresh page load with NO user interaction. 5 consecutive `Shown: 27 Hidden: 23` cycles, then a sudden `Shown: 0 Hidden: 0` (counter drops 27→0).

This is a milder version of the 195↔196 oscillation user already reported. The mutex retry queue from PR #773 is firing on no-op DOM state because something else (a MutationObserver? lazy-load batch?) keeps signaling that work is needed.

### ⚠️ HIGH — Gear icon panel detection failed

`aria-label="open settings"` button is found and clicked. But:
- `visiblePanels` before scroll = 0
- `visiblePanels` after scroll = 0

User reports "opens but blurs/disappears on scroll." My panel selector (`[role="dialog"], [class*="modal"], [class*="dropdown"], [class*="settings"]`) doesn't match — meaning the panel uses a different DOM structure (probably a custom positioned element). Need a targeted DOM probe that captures the actual panel selector.

### ⚠️ HIGH — Tabular view doesn't show table after click

`tables=1, visibleTables=0, maxRows=0` — the table element exists in DOM but is not visible after the click. Either the click doesn't activate the right state or the table is rendered inside a hidden container.

### NOISE (ignore)

- React #418 hydration warning in minified bundle — pre-existing, non-blocking
- 2 Google Ads 400s (ad blocker)
- 3 PostHog 127.0.0.1:7838 connection refused (local dev telemetry)

---

## Swarm Test Plan

### Mission

Continuously verify findtorontoevents.ca behaves correctly across all UX surfaces (filtering, gear, tabular, AI assistant, scroll, mobile) by fanning specialists across the test surfaces and aggregating into a single CI-gateable verdict.

### Test surfaces (10)

| ID | Surface | Specialist | Live verdict from this run |
|---|---|---|---|
| S1 | Filter chips (6: All Dates / Today / Tomorrow / This Week / This Month / Next Month) | datetime-timezone-specialist + race-condition-specialist | 🚨 0 cards visible across all 6 |
| S2 | Multi-day overlay logic (>31d duration cap, active-today exception) | datetime-timezone-specialist | needs deeper probe |
| S3 | Gear-icon settings panel (open + scroll behavior) | react-dom-specialist | ⚠️ panel not detected by generic selectors; user report unconfirmed |
| S4 | Tabular view (toggle + render + sort + filter + export) | react-dom-specialist + event-surface-engineer | ⚠️ table not visible after click |
| S5 | AI Assistant (bottom-right chat panel) | event-surface-engineer | not yet probed |
| S6 | Scroll/lazy-load (cards arrive in batches; filter must re-apply) | race-condition-specialist | applyFilters fires 20× — oscillation |
| S7 | Counter accuracy (visible cards == counter span) | event-surface-engineer | 🚨 counter says 31, DOM shows 0 |
| S8 | applyFilters mutex correctness (no oscillation on idle DOM) | race-condition-specialist | 🚨 5+ no-op repeats per chip change |
| S9 | Mobile viewport (chip layout, hamburger, touch handlers) | react-dom-specialist | not yet probed |
| S10 | Network failure handling (cache-warm fallback, stale badge) | event-surface-engineer | not yet probed (would need fault injection) |

### Specialists (already in `tools/swarm/agent_personas/`)

- `race_condition_specialist.md` — handles S1 (chip switching races), S6, S8
- `datetime_timezone_specialist.md` — S1 (date logic), S2
- `react_dom_specialist.md` — S3, S4, S9
- `event_surface_engineer.md` — S5, S7, S10
- `coordinator_synthesizer.md` — final ranked rollup
- `forex_diagnostic_surgeon.md` — analogue pattern; not used here, but the persona format is the model

### Phase plan (mirrors `events-swarm-incident-plan_91d51306.plan.md`)

1. **Phase 0: live baseline capture** (Playwright headless + `tmp/full_site_inspection.js` patterns)
   - Capture per-surface JSON before any code change
   - Output: `swarm_runs/eventsite_baseline_<ts>/<surface>.json`

2. **Phase 1: parallel specialist fan-out** (4-5 specialists, each gets the relevant baseline JSON + a focused prompt)
   - Each specialist outputs a structured JSON envelope per `events-swarm-incident-plan` schema (lines 133-163)
   - Required fields: `rootCauseId`, `file`, `symbol`, `confidence`, `severity`, `reproSteps`, `evidenceLink`, `suggestedPatch`, `crossValidatedBy`

3. **Phase 2: cross-critique round** (each specialist reviews the others; flag fabrications)
   - Adds `crossValidatedBy` corroborations
   - Discards any finding without ≥2 specialist support OR confidence ≥0.85 + deterministic repro

4. **Phase 3: coordinator synthesis** (`coordinator_synthesizer` persona via deepseek/claude)
   - Ranked patch list; ship-today / this-week / next-sprint buckets
   - File: `reports/eventsite_swarm_audit_<ts>.md`

5. **Phase 4: surgical patches** (single-file edits in `TORONTOEVENTS_ANTIGRAVITY/index.html` per swarm consensus)

6. **Phase 5: re-baseline + verify**
   - Re-run `tmp/full_site_inspection.js` post-patch
   - Compare baseline-vs-post JSON
   - Promote to FTP only if every surface shows IMPROVEMENT or NO REGRESSION on its primary assertion

### Required output schema (per specialist)

```json
{
  "specialist": "race_condition_specialist",
  "runId": "swarm_runs/run_<TS>",
  "schemaVersion": "1.1",
  "findings": [
    {
      "rootCauseId": "RC-CHIP-COUNTER-MISMATCH-001",
      "file": "TORONTOEVENTS_ANTIGRAVITY/index.html",
      "symbol": "applyFilters",
      "issue": "Counter span shows 31 but no .group elements visible",
      "confidence": 0.92,
      "severity": "critical",
      "reproSteps": [
        "Load https://findtorontoevents.ca/ headless",
        "Click 'This Month' chip",
        "Read .glow-text.tabular-nums textContent",
        "Count .group:not([style*=display:none]) [class*=event-card]:not(.event-card-hidden)",
        "Observe: counter=31, count=0"
      ],
      "evidenceLink": "tmp/inspection_artifacts/full_inspection_chips.json",
      "suggestedPatch": "Audit which DOM mutator hides cards; ensure counter == visible-card count invariant",
      "crossValidatedBy": ["react_dom_specialist", "event_surface_engineer"]
    }
  ]
}
```

### Coordinator merge rules

- A finding is **CONFIRMED** when ≥2 specialists corroborate the same `(file, symbol)` pair
- A finding is **CANDIDATE** with single-engine flag — held in backlog, requires repro evidence before patch
- A finding is **DISPUTED** when specialists disagree — coordinator emits `preferredHypothesis` + `rejectedHypotheses` + `tieBreakEvidence`
- Patch admission: confidence ≥0.85 + deterministic repro OR ≥2 specialist agreement

### Schedule + integration

- **Per-PR gate:** run `tmp/full_site_inspection.js` against the PR's deployed preview (or post-FTP)
- **Nightly:** run full Phase 0 baseline against prod + diff against last successful baseline
- **On-demand:** `python tools/swarm/swarm_run.py --persona race-condition-specialist --prompt-file tmp/inspection_artifacts/full_inspection_summary.json`
- **Hooks:** add to `.github/workflows/sports-smoke-and-e2e.yml` style file: `events-smoke-and-swarm.yml` triggering on push to main + 4-hourly cron

### Action items (for THIS session, in order)

1. **Validate finding #1** (chip filter 0-cards) — write a tighter Playwright probe that uses MULTIPLE DOM selectors to find visible event cards. If actually 0 visible, that's a P0 prod outage requiring immediate fix.
2. **Validate finding #2** (gear panel + scroll blur) — capture the panel's actual class/aria when it opens, then re-test scroll behavior with the right selector.
3. **Validate finding #3** (oscillation 5+ no-op repeats) — already in flight via the counter-oscillation subagent (`a4a6180d1c6bd63da`).
4. **Run Phase 1 specialist fan-out** — use the 4 personas above against the baseline JSON we just captured. 4 specialists × 5 engines = 20 outputs, then synthesis.

🤖 Plan authored 2026-05-04 by the swarm-orchestrating Claude. Inspired by `events-swarm-incident-plan_91d51306.plan.md` (specialist JSON contract + coordinator merge rules + decision rules for patch admission).
