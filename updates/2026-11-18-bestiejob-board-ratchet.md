# BESTIEJOB board ratchet cleared — 2026-11-18

The `board-invariants` gate on `eltonaguiar/BESTIEJOB` had been red since its baseline was
recorded (2026-11-14). Fixed in BESTIEJOB PR #46; the full write-up, with the per-kind evidence
and the follow-up list, is `BOARD_RULES_CLEANUP_2026-11-18.md` in that repo.

## What was actually wrong (two different failures)

**1. The gate's own location rule was wrong about 1,111 rows.** `CA_RE` only knew province names
and codes, so these valid Canadian locations counted as "names no province or country":

`Mississauga, Peel region` (103), `Ottawa, Ottawa region` (90), `Calgary, Calgary region` (80),
`Toronto, ca` (63), `Vancouver, Greater Vancouver` (33), `Markham, York region` (26)

`Toronto, ca` is the posting's own country code. Fixed with `CA_PLACE_RE`, consulted *after* the
explicit-country check so `region_of()` still decides non-Canada first (`Vancouver, WA` is still
caught). `location-ambiguous` 1111 → below its 821 allowance.

**2. 1,294 published rows genuinely broke the board's promises.** Non-Canada reqs (1,113, mostly
US ServiceNow/Salesforce from the SmartRecruiters sweep), rows older than the 30-day window (107),
malformed rows with a link leaked into the Company/Location cell (81, all from the Workopolis
slice), vendor sales roles (8), scraper bookkeeping in Company/Title (3).

`scripts/normalize_board.py` removes them from **all three** places they live — `README.md`,
`jobs.json`, `inbox/*.md` — because pruning the README alone is undone by the next hourly merge
(the inbox held **1,025 copies** of those rows across 32 files). It is wired into `hourly-scan`
after the merge, so the board self-heals.

```
README 7856 -> 6562 rows · jobs.json 2847 -> 2552 · inbox 1025 rows removed
gate   errors 1314 -> 2 · PASS: the published board satisfies its own rules
```

## Left open on purpose (recommendations)

1. `identity-date-conflict` (505 > 413) is a *warning*, so it does not fail the gate. `url-date-conflict`
   is **0**, so all 505 rows have distinct URLs — the same job on LinkedIn and Workopolis on different
   days, which "deduplicated by URL" permits. Narrow the rule, or stop ratcheting a heuristic; do not
   raise the baseline.
2. `split-row` is a symptom: `jobs_merge_inbox.rows_are_readable()` accepted Workopolis rows shaped
   `| date | Title / City, ON | City, ON](url) | Workopolis Canada | … |`. Fix the parser and add a
   `](` check on the Company/Location cells at ingest.
3. `clock-date` (2 rows): the Workday adapter copies `scrapedAt` into `postedDate` instead of omitting it.
4. Non-Canada keeps entering through the ATS sweep; `scripts/enforce_canada_scope.py` exists but runs
   as a manual purge, not at ingress.
