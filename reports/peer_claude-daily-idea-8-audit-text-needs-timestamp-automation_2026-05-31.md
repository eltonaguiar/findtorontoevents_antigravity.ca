# Daily Idea #8 — Audit Page Hardcoded Text Needs Automation + Timestamps

**Date:** 2026-05-31
**Agent:** claude-opus-4-7 (subagent #8 of daily ideas swarm)
**Idea slug:** `audit-text-needs-timestamp-automation`

## Verbatim user idea

> now we have pages findtorontoevents.ca/audit with text which needs to be
> automated and have a date/time stamp

**Investigation prompt:** Sweep `/audit` pages for hard-coded narrative
text/numbers and replace with auto-generated content backed by a refresh
timestamp. Add 'last refreshed: <UTC ts>' marker to every dynamic section.

## Classification

This is **NOT a trading-edge hypothesis.** It is a **dashboard data-integrity /
maintenance** idea. The CLAUDE.md tier system (T1/T2/T3/SHADOW/INSUFFICIENT_N
/ NO_EDGE / LEAKAGE_SUSPECTED) does not apply — there is no SQL "edge" to
backtest. Verdict slot is repurposed as `MAINTENANCE_ACTION_REQUIRED`.

The output is still falsifiable and measurable: count hardcoded numeric
claims in `audit_dashboard/template.html`, check the JSON sources they
should be reading from, and report the drift.

## Methodology

1. Count narrative claims that hardcode `PF X.YZ` / `WR X%` / `n=X` /
   `Tier X` patterns inside `audit_dashboard/template.html`.
2. Confirm whether matching live JSON sources exist under
   `audit_dashboard/data/` with fresh `generated_at`.
3. Identify how many of those narrative claims are statically bound vs
   wired to a live JSON field.
4. Recommend the minimum surgical change.

## Results

### Hardcoded narrative-number count (template.html)

```bash
$ wc -l audit_dashboard/template.html
18878 audit_dashboard/template.html

$ grep -cE "PF [0-9]|WR [0-9]+%|n=[0-9]" audit_dashboard/template.html
80
```

**80 hardcoded performance claims** live inside the template. Examples
spotted in lines 851 / 897-902 / 1331-1350 / 1427-1430:

- `RAW at_raw_picks (Kimi + 2026-05-12 audit): 11.13% WR / PF 0.46. Refreshed
  2026-05-29 (n=73,817 closed): WR 25.28% / PF 0.61` — manually dated string.
- `EQUITY — FAIL (PF 0.70, WR 37.4%, n=567 closed_picks; 14d=PF 5.56 WR 66.7%
  ...)` — manually dated, no JSON binding.
- `CRYPTO — FAIL (pf_registry policy-clean PF 0.98 WR 39.7% n=229; money_ready
  PF 0.96 WR 31.3% DSR 0.0073)` — numbers from `money_ready_verdict.json` but
  hardcoded into HTML.
- `FOREX — FAIL+FROZEN (PF 0.39 WR 15.4% n=13 policy-clean; 15,720 scanned
  90d → 0 high-conviction)` — date-bound, will drift in <7 days.
- Where Our Edge Actually Is (Closed-Pick Data, n=4,618) — header itself
  has a stale n.
- COMMODITY — cot_positioning DSR=1.0 FALSIFIED 2026-05-13 ... — refers to
  status `audit_dashboard/data/cot_paper_pilot_status.json` but the verdict
  string is frozen in HTML.
- 1916 closed picks "R:R Truth (CRYPTO, verified 2026-04-17 across 1,916
  closed picks)" — 6+ weeks stale.

### Timestamp infrastructure that ALREADY exists

```bash
$ grep -cE "generated_at|Last Updated|last refreshed|refreshed_at" audit_dashboard/template.html
45
```

The page already wires `D.generated_at` from `dashboard_data.json` to the
header (`#last-updated`) and stamps `Last updated <ts> EST` on multiple
sub-panels (UEPS, smart_picks_summary, ai_tournament_picks_latest).

The **data files have fresh timestamps**:

```bash
$ python3 -c "import json; d=json.load(open('audit_dashboard/data/money_ready_verdict.json')); print(d.get('generated_at'))"
2026-05-30T23:05:42.928016+00:00
```

### Drift gap (what's wrong)

The dashboard **machine-readable cells** (the top KPI strip, the per-class
verdict cards, the strategy tier table) ARE bound to live JSON. The
problem is the **narrative explainer paragraphs** (lines 851, 897-902,
1331-1350, 1427-1430) that exist *to give context to the cells*. Those
narratives:

1. Repeat numbers that already live in JSON (PF/WR/n/DSR) — **drift risk**.
2. Embed dates ("2026-05-13", "2026-05-29", "verified 2026-04-17") that
   freeze in HTML and silently age — **trust risk**.
3. Reference report filenames like `reports/ASSET_CLASS_EDGE_FIX_PLAN_2026-05-27.md`
   — fine if file exists, but no automated link check.
4. Have **no per-paragraph "last refreshed" badge**, so a reader can't tell
   the narrative is 7+ days behind the cell next to it.

## Cross-check vs today's NO_EDGE verdict

N/A — this idea is operational, not a trading edge claim. It does not
contradict the 10-agent + 3-external-AI NO_EDGE verdict; it actually
*reinforces* trust in the page by closing the hardcoded-vs-live gap that
makes outside reviewers (and Cloudflare-hosted models, per CLAUDE.md "DO
NOT trust unsourced model claims") doubt the cell numbers.

## Verdict

**MAINTENANCE_ACTION_REQUIRED — confidence HIGH.**

This is a real, measurable, fixable defect:
- 80 hardcoded numeric claims in one template, vs ~45 already-wired
  `generated_at` consumers.
- Live JSON sources exist with fresh ISO-8601 stamps.
- No new statistical research needed — pure plumbing.

This is **not** an edge claim and so does not get a T1/T2/T3 tier. It is
adjacent to the audit-integrity work tracked in MEMORY.md
"project-audit-integrity-banner-2026-05-31" (PR #207).

## Recommended next step

**SHADOW-PILOT a `data-narrative-binding` convention**, do not boil the
ocean:

1. **Phase 1 (this week, 1 PR, ≤2 files):** Add a `<small class="narrative-stamp">`
   span next to each of the 7 narrative blocks (lines 851, 897-902, 1331-1350,
   1427-1430). The stamp reads the same `generated_at` the adjacent cell
   uses and renders `Narrative aligned with data snapshot 2026-05-30 23:05
   UTC — re-verify if older than 14 days`. If `Date.now() - generated_at >
   14d`, the stamp turns amber. Two file scope: `template.html` +
   `dashboard_enhancements.js`.

2. **Phase 2 (separate PR, opt-in):** Move the 80 hardcoded `PF/WR/n`
   strings into `audit_dashboard/data/narrative_facts.json`, regenerated by
   `dashboard_generator` from `money_ready_verdict.json` +
   `pf_registry.json` + `pick_summary_stats_*.json`. Template reads via
   `data-narrative-key` attribute. Adds a `last_refreshed` per fact.

3. **Phase 3:** CI gate (`tools/check_narrative_drift.py`) — if any
   hardcoded `PF X.YZ` or `WR X%` survives outside `narrative_facts.json`,
   fail PR. Mirrors the existing pattern that blocks raw SQL in the
   template.

**Confidence the fix matters:** HIGH. Cited in MEMORY.md as the proximate
cause of the 2026-05-25 LiteLLM-proxy entry being "invisible until
scroll + pushed to git but not FTP-deployed" — narrative entries silently
diverge from live data.

**Effort:** Phase 1 = 2 file diff, <50 LOC. Phase 2 = full sprint.

## Final return string

```
IDEA8:slug=audit-text-needs-timestamp-automation:verdict=MAINTENANCE_ACTION_REQUIRED:n=80_hardcoded_claims:wr=N/A:pf=N/A:wilson_lb=N/A:recommend=shadow_pilot_phase_1_narrative_stamp
```
