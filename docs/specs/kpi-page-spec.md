# Spec: KPI Page (spec only — no code this week)

**Status:** Spec only. No implementation this week.
**Branch:** opencode/kpi-page-spec
**Canonical data source:** `audit_dashboard/data/money_ready_verdict.json` (generated 2026-10-19T19:38:52Z, 9 classes). Secondary: `audit_dashboard/data/dashboard_data.json` (generated 2026-10-19T19:40:11Z).

## 1. Goal
One KPI page computed from the canonical table, showing money-pass status per asset class with full source attribution. No READY/ENTER wording anywhere.

## 2. Canonical table fields (per KPI list)
For each class in `money_ready_verdict.json::classes.<CLASS>`:
- `class` (string)
- `n` — cite which n: intrabar (`intrabar_truth.n`) vs resolved (`n_resolved` / `policy_clean_n`). Default display = intrabar n.
- `wr` — hidden when n<20 (display "n<20, not shown"). Source: `intrabar_truth.wr` (×100).
- `pf` — `intrabar_truth.pf`.
- `mdd` — `mdd` (if present).
- `verdict` — `verdict` field (WATCH / FAIL / INSUFFICIENT_DATA). No READY/ENTER wording.
- `source` — `audit_dashboard/data/money_ready_verdict.json`
- `generated_at` — `money_ready_verdict.json::generated_at`

## 3. Page layout
- Title: "KPI — Money-Pass Status by Asset Class"
- One table with the fields above. Every panel shows `source` + `generated_at`.
- Footer note: gates applied are n≥100, PF≥1.5, WR≥50%, MDD≤20%; no lower gates proposed.

## 4. Panels to remove or label
- Walk-forward panel: empty since 2026-04-15 (`walkforward.by_class` is empty). Action: REMOVE from page (or label "No walk-forward data available since 2026-04-15"). Do not show empty chart.
- "+9,650% compounded" headline: REMOVE. Not supported by canonical table.

## 5. WR display rule
Hide WR when n<20. Display "n<20, not shown".

## 6. Wording constraints
- No READY/ENTER wording anywhere.
- Verdict values allowed: WATCH, FAIL, INSUFFICIENT_DATA (from canonical source).

## 7. Reconciliation
If another agent's doc reports different n/WR/PF, the difference is intrabar vs resolved n (e.g., COMMODITY resolved n=18 vs intrabar n=227). Name both sources; do not overwrite.

## 8. Acceptance
- Spec only this week; implementation deferred.
- When implemented, the page must show source + generated_at on every panel, no walk-forward panel, no "+9,650%" headline, WR hidden for n<20.
"