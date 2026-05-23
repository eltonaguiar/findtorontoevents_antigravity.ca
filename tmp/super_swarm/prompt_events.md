# Super-Swarm Analysis: findtorontoevents.ca/ (events homepage)

You are one of 11 diverse AI engines doing **QA + product analysis** on the public events homepage at https://findtorontoevents.ca/. Surface bugs, UX issues, data-quality problems, and propose enhancements + new Toronto event data sources.

## Context

- Homepage source: `TORONTOEVENTS_ANTIGRAVITY/index.html` (4,800+ lines, hand-coded). NOT auto-generated.
- Events flow: `*_scraper.py` → `events.json` → `window.__RAW_EVENTS__` → `applyThumbnails()` injector.
- Known recently-fixed: multi-day events leaking under date-window filters (PR #774, >31d cap), Today/Tomorrow/Week 0-events bug (just fixed), counter oscillation (PR #778), date bucketing (PR #777).
- Known open issues: gear-icon settings panel "blurs/disappears on scroll", tabular view UX is poor, possible chip-active-state detection drift in React refactors.
- Active scrapers cover Eventbrite, BlogTO, NowToronto, university, library, dating events. Cancelled-event filter active since Apr 27.

## Your task — produce JSON envelope

```json
{
  "engine": "<engine name>",
  "verdict_summary": "<2-3 sentences on overall events page health>",
  "qa_findings": [
    {
      "id": "QA-XX",
      "surface": "filter_chips|gear_panel|tabular_view|event_cards|mega_menu|mobile|ai_assistant|other",
      "severity": "critical|high|medium|low",
      "issue": "<concrete observable bug>",
      "repro": "<step-by-step>",
      "suggested_fix": "<file:line + change>",
      "confidence": 0.0-1.0
    }
  ],
  "data_quality_concerns": [
    {"issue": "<stale/duplicate/cancelled/wrong-tz/missing-image>", "evidence": "...", "fix": "..."}
  ],
  "ux_enhancements": [
    {"name": "<feature>", "value": "high|medium|low", "effort": "S|M|L", "description": "..."}
  ],
  "new_data_sources": [
    {
      "name": "<source>",
      "url": "<api/scrape target>",
      "auth": "free|free-tier|paid|scrape-only",
      "event_types": ["..."],
      "estimated_events_per_week": <number>,
      "implementation_notes": "..."
    }
  ],
  "ranked_top3_priorities": ["..."]
}
```

## Rules

- Prefer Toronto-specific sources (ROM, AGO, Harbourfront, TIFF, TPL, U of T, TMU, OCAD, Massey Hall, Roy Thomson, Casa Loma, Distillery District, etc.) over generic global aggregators.
- Suggest at least 5 new data sources not already integrated.
- For QA findings, only flag things plausibly observable on the live site — don't speculate without basis.
- Propose enhancements that align with the events product (not feature creep into trading/sports).

Output ONLY the JSON envelope.
