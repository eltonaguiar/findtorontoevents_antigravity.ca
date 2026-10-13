# 2026-10-13 — ServiceNow playbook section on /integrations + JS page async/await clarification

Follow-on to `updates/2026-10-13-integrations-portfolio-page.md` (same day).
Commit: see git log for "Add ServiceNow integration playbook section".

## What was requested

1. A final section on the public `/integrations` page covering key components
   of any integration plus ServiceNow-specific best practices: instance-to-
   instance transport, clone protocol and frequency, family-upgrade cadence,
   change freezes, top recommended integration types (Jira, SCCM —
   IntegrationHub spokes?), and CMDB integrations — how to make the IRE
   engine run, and, in the rare case it should not, how to prevent that both
   programmatically and non-programmatically (table design/inheritance).
2. Fix `findtorontoevents.ca/servicenow/javascript/index.html#best-practices`:
   the operator believed Promise/async/await are NOT supported even though
   they are ES6 features.

## What changed

### `/integrations` — new Section 9 "ServiceNow integration playbook"

- **9.1 Anatomy of any integration** — checklist cards: identity/ownership
  (per-field source of truth), protocol/auth (OAuth2 first, no shared
  passwords), data contract + idempotency key, reliability/observability
  (error queue with replay, freshness alerting, audit trail, rollback).
- **9.2 Methods table** — IntegrationHub spoke/Flow Designer, scripted
  REST/EIB, Service Graph Connectors + MID (RTE + IRE), Import Sets +
  Transform Maps (coalesce = idempotency key), update sets/source control
  for config transport.
- **9.3 Worked examples** — Jira via the Jira Spoke + Flow Designer (OAuth,
  per-field source of truth, no dual-writes, watch transaction consumption;
  REST/Store fallback); SCCM via the Service Graph Connector for Microsoft
  SCCM through a MID Server (official docs: uses RTE + IRE) — raw REST into
  `cmdb_ci_*` called out as the duplicate-CI anti-pattern.
- **9.4 CMDB/IRE** — IRE runs automatically on IRE-aware payload pipelines
  (SG Connectors, Discovery, IH CMDB actions, IRE API); run it deliberately
  via identification simulation, Identification Logs replay, and the
  `glide.cmdb.logger.source.identification_engine` property. No supported
  global off switch — bypass = don't route through IRE pipelines: direct
  GlideRecord/transform-map writes, or a staging table that doesn't extend
  `cmdb` (programmatic); behavior properties (`glide.class.upgrade/
  downgrade/switch.enabled`, `glide.identification_engine.skip_duplicates`,
  `glide.required.attribute.enabled`) as the non-programmatic levers.
- **9.5 Clone/upgrade/freeze table** — update sets for config, data only via
  cloning; Clone Admin Console + data preservers + post-clone integration
  re-pointing; cadence: dev on-demand, test ≥ monthly and after every
  upgrade (prevailing practice, labeled as such); two family releases/year
  with sub-prods upgraded first; change freeze ≈1 week pre-upgrade until
  post-upgrade validation, no update-set pushes or connector changes during.

### JS training page — `#best-practices` section

Added a checklist bullet + `.warning` callout: `Promise` and
`async`/`await` are ES6 features but are **Disallowed in ES5 Standards
mode** (still the default for global server scripts — they throw), and
**supported in the engine's ES12 mode** (default for new scoped-app scripts
since Xanadu, per-script toggle elsewhere). Both modes disallow async
generators and `for await...of`; ES5 additionally disallows
`Promise.allSettled()`, `Promise.any()`, `Promise.prototype.finally()`,
`Promise.withResolvers()`. Portable rule: write the ES5-safe subset; treat
ES12 syntax as explicit per-script opt-in. Linked the official
"JavaScript engine features" matrix.

## Sources (fetched 2026-10-13)

- ServiceNow docs: "JavaScript engine features" (ES12 vs ES5 Standards
  support matrix — async functions, Promise methods, async iterators)
- ServiceNow docs: "Properties for Identification and Reconciliation"
  (IRE property reference)
- ServiceNow docs: "Microsoft SCCM" Service Graph Connector page
  (RTE + IRE via MID)
- ServiceNow docs: Jira Spoke (IntegrationHub)
- ServiceNow support KB "Clone FAQs" + community clone/upgrade playbooks

## Verification

- Integrations page: workflow validation step passes (no conflict markers,
  no credential literals); Chromium render — 9 sections, 9 tables, TOC
  anchor navigation works, zero console errors, no horizontal overflow.
- JS page: the existing `tests/servicenow_js_es6_overflow.spec.ts`
  assertions replicated manually in Chromium (heading present, ES6 grid
  visible, 5 cards, no grid/page overflow) plus the new content checks
  (warning present once, bullet present, official-doc link present), zero
  console errors. The spec itself could not be executed: it is excluded by
  the repo's `playwright.config.ts` `testMatch` allowlist, and under this
  repo's ESM package config Playwright's transform fails with
  "require is not defined in ES module scope" — a pre-existing environment
  issue, not introduced here, and intentionally not changed (CI behavior
  untouched).
- Both files deployed manually over FTP to the 50webs host (findtorontoevents.ca
  only; GoDaddy/tdotevent.ca untouched) with byte-size confirmation, then
  live-checked via curl (HTTP 200, new content markers present).
- Git hygiene: the JS page carries another session's uncommitted training
  work; only my single hunk was staged (filtered patch via
  `git apply --cached`), verified by asserting their markers are absent
  from the staged diff.

## Changelog

- 2026-10-13 (later, commit "Clarify quiz context, add getXML + first-character
  questions, fix emoji question"): quiz fixes on the same JS training page —
  `aj-03` question now states the onChange client-script context so its
  `newValue` canonical answer is unambiguous; `aj-07` hint verified against
  sources (the flag is exactly "Client callable"/`client_callable` — no
  "ajax enabled" checkbox exists) and says so; new `aj-09` (full
  `ga.getXML()` wiring incl. `response.responseXML.documentElement`
  `getAttribute('answer')`, grading smoke-tested); new `js-23` (first
  character of a string, `charAt(0)`/`[0]`/`at(0)` accepted); `js-05` emoji
  question rewritten to explain the surrogate-pair mechanism, with the
  operator's runnable `[...x]` example in the hint; `.q-hint` gained
  `white-space: pre-wrap` for multi-line examples. Deployed byte-verified;
  live `quiz-data.js` byte-identical to repo.

## Follow-ups

- None outstanding. Operator-side later: credential rotation (see
  `updates/2026-10-13-movieshows-sync-key-hardening.md`), and optionally
  restoring `RATE_CAP` in `cross_aggregation/freshpicks_gate.py`.
