# PROBATION on `/audit/anti_overfit.html`, beside n and DSR

## What was missing

The anti-overfit gate already refused 74 of 80 strategies (DSR below 0.95), and the sidecar now
writes `publication_label` on every row. The page did not read it, so a strategy that cannot be
published looked identical to one that can: same table, same colour, same silence. The demotion
existed in the JSON and nowhere a reader would meet it.

## What changed

`audit_dashboard/anti_overfit.html` only. No JSON schema change, no filtering of the payload.

- **Publication column** — the first column of the per-strategy table, `PUBLISHABLE` in green,
  `PROBATION` in red, `UNRATED` in grey. The badge's tooltip is the row's own
  `publication_reason`, so the arithmetic behind a demotion is one hover away.
- **Two KPI tiles** — Publishable and On probation, counted from the rows rather than the payload,
  so the numbers cannot drift from what is displayed.
- **A note above the table** — `74 of 80 strategies are PROBATION — DSR below the 0.95
  publication floor`, with the sentence that matters: the label is a display rule, not a filter.
- **An opt-in filter** — `hide PROBATION rows`, unchecked by default. Filtering is a reader's
  choice and is remembered only for the session; the default view shows every row with its `n`.
- **Fallback** — a snapshot generated before the label existed derives it from `dsr >= 0.95` and
  labels the rest `UNRATED`, rather than claiming a status it never computed.

Rows are not removed, not reordered by label, and not hidden by default. `n`, `WR`, `PF`,
`Sharpe` and the DSR bar are untouched, so the demotion is visible without the evidence
disappearing.

## Verification

- `node --check` on the extracted `<script>`: **SYNTAX_OK**.
- Payload read back at commit time: `publication_label_counts = {PUBLISHABLE: 6, PROBATION: 74}`,
  and every row carries `publication_label`.
- `publication_dsr_threshold` is absent from this snapshot, so the page falls back to `0.95` —
  the same constant the label was computed with. When the sidecar emits the field the page uses
  it, so the two cannot disagree.

## Deployment

`anti_overfit.html` is already in the `audit-dashboard.yml` page lists for all three sites, so the
hourly cron picks this up with no manual step. The page is a research surface: this changes what a
reader sees, not what the system trades.

## What this does not do

- Does not gate picks, sizing, or the money-ready verdict.
- Does not hide, delete, or re-rank any strategy.
- Does not change `publication_label` semantics; the page is a view of the JSON.
