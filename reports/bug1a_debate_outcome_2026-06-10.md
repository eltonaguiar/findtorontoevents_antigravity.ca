# Bug 1A Entry-Anchored Resolver — Debate Outcome (2026-06-10)

Structure (operator-requested): a **meta round** designed the review methodology, then **adversarial
debate rounds** used it. 7 agents, 4 phases. Workflow run `wf_c4de4f26-92c`.

## Methodology (meta round)
Weighted rubric: Look-ahead-elimination/correctness (30) · Backward-compat/blast-radius (18) · Test
adequacy (15) · Rollout safety/reversibility (14) · Performance/API-cost (10) · Observability (8) ·
Simplicity/reuse (5). Failure modes mandated for probing: off-by-one entry==bar boundary; tz/ms parsing
of `pick.timestamp`; unparseable-entry path; per-symbol fetch-cost blowup; production-API-vs-DB-range gap;
shadow-diff skipped/rubber-stamped; harness gaps.

## Rounds
- R1 scores: Proponent 74, Red-team 52, Quant-risk 58.
- R2: proponent rebuttal + independent judge → **REVISE**.
- Synthesis: **REVISE / NO-GO as written**; GO only after the must-fix list + a two-PR rollout.

## What the debate caught (verified in live code — not speculation)
1. **CRITICAL look-ahead reintroduction #1:** v1's "fall back to recent-window if entry unparseable"
   branch — `_parse_timestamp` returns None for offset timestamps (`+00:00`/`-05:00`, judge ran it),
   so it would replay unfiltered stale bars for every offset-bearing pick.
2. **CRITICAL look-ahead reintroduction #2 (production-fetch vs DB-range):** v1 mislabeled the fix as a
   "port" of `reresolve_intrabar.py` (which entry-anchors via a SQL range query). Production hits the
   LIVE yfinance/binance API (1h intraday ~60d ceiling); for old picks the API returns a window
   STARTING AFTER entry that fake-resolves unless explicitly degraded to close_approx.
3. **HIGH crash:** sole caller (`:1275`) strict-unpacks a 3-tuple; the harness asserted a 4th element →
   ValueError on the hot path for every ambiguous bar.
4. **HIGH fictional observability:** JSON `resolution_method` (`:1288`) never reaches the
   `at_pick_outcomes` DB column (a status enum from `exit_reason`, `:901-920`); no ambiguous/geometry
   columns — the "wire through DB upsert" claim was impossible without a migration.
5. Plus: missing shadow-diff blocking threshold, undecided historical-row backfill (this resolver IS the
   measurement layer), BAD_GEOMETRY still firing on the close_approx path, entry-boundary off-by-one.

## Resolution
All 11 must-fixes + the two-PR rollout are folded into the v2 section of
`reports/plan_bug1a_entry_anchored_resolver_2026-06-10.md`. The 8 harness gaps are addressed:
`tests/test_resolver_intrabar_accuracy.py` expanded to 14 cases (7 pass / 7 xfail), adding offset-entry,
partial-API, entry==bar, gap-through (#8), un-timestamped defensive-keep, and the ambiguous-via-dict-flag
contract. Remaining for the fix PR: a DB-upsert-mapping test + flip all xfail→strict.

**Net:** the debate did its job — it converted a directionally-correct but unsafe plan into an
implementation-ready, two-PR, gated spec, and prevented shipping two verified look-ahead-reintroduction
bugs + a crash into the hot production resolver. Implementation remains deliberately deferred to the
gated PR1 (flag-OFF logic) → PR2 (default-ON after shadow-diff + quant sign-off).
