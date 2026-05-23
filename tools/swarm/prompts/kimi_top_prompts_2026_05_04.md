# Top Effective Prompts Extracted from Kimi Swarm (2026-05-04)

Source: `reports/kimi_swarm_archive_2026_05_04/` (Kimi Agent Swarm Playwright Testing Plan).

These prompts are reusable templates harvested from Kimi's run that produced ~8,000 LOC across 19 files in a single multi-agent dispatch.

---

## 1. Console Error Hunter (the killer pattern)

> **Build a Playwright suite that hunts for known-bad console patterns.** Listen on `page.on('console')`, `page.on('pageerror')`, and `page.on('requestfailed')`. Maintain a `KNOWN_BAD_PATTERNS` regex array including: `/counter\s*oscillation/i`, hydration-mismatch, chunk-load-failure, `undefined is not`, 4xx/5xx network failures, unhandled rejection. Maintain an `ALLOWLIST` for analytics/blocker noise. Fail the test on any unallowlisted bad pattern. Output a shared `tests/console-error-utils.ts` plus per-page `.spec.ts` files.

**Why effective:** the `KNOWN_BAD_PATTERNS / ALLOWLIST` separation is what keeps console-error CI tests from being either (a) noisy and ignored or (b) too lenient and missing real regressions. The "counter oscillation" pattern came from Claude catching it in production — promote any field-discovered bug into the regex array.

---

## 2. Audit Gap Table

> **Cross-reference an audit document against live code and produce a single markdown table.** Columns: `Requirement | Status (DONE/PARTIAL/PENDING/DISPUTED) | Gap | Priority (P0/P1/P2) | Suggested Fix (file:line)`. A requirement is DONE only if the symbol/file can be grep'd. Mathematical contradictions (e.g., headline PF vs breakdown PF) are automatic P0. Cite both sides on DISPUTED rows; do not silently side with the audit.

**Why effective:** forces evidence per row. Yields a table that doubles as a sprint backlog.

---

## 3. Stage-Gated Reconnaissance

> **Stage 1 reconnaissance:** spawn 3 parallel sub-agents — `Repo_Analyst`, `Audit_File_Analyzer`, `Page_Inspector`. Outputs: `repo_structure.md`, `tech_stack.md`, `page_inventory.md`, `known_issues.md`. **Do not start designing tests until reconnaissance returns.** This prevents blind test generation against assumed structures.

**Why effective:** Hermes' interrupt-prone behavior shows the cost of skipping reconnaissance. Stage gates make resumability easy.

---

## 4. UX Enhancement with Persistence Fallback

> Design a settings modal that supports `EXEMPT_SOURCES` for the dominant data provider. **Always implement BOTH backend persistence (PHP/REST + DB schema) AND a localStorage fallback.** If the user is logged in, persist server-side; otherwise localStorage. Test plan must include "guest sets pref → reload → still set" AND "logged-in sets pref → logout/login → still set".

**Why effective:** prevents the common bug where features "work for me" only because the developer is logged in.

---

## 5. Sports Betting Edge Audit

> Any WR claim with `n < 30` is FLAGGED, no exceptions. If CLV (closing line value) is not tracked, that is an automatic P0 finding because CLV is the gold-standard edge proxy. Identify whether quoted ROI is gross-of-vig or net-of-vig and flag if unclear. Do not recommend bet sizing without verifying responsible-gambling messaging is present (Ontario AGCO compliance).

**Why effective:** hard rules prevent the "+164% on n=3" overclaim trap.

---

## 6. Counter-Oscillation Detection (the original)

> The swarm's console error hunter specifically built detection for the "Counter oscillation subagent" bug that Claude previously caught. This pattern is now part of the `KNOWN_BAD_PATTERNS` regex array and will be flagged in every test run.

**Why effective:** field-discovered bugs become permanent regression nets when promoted into shared utils.

---

## 7. The "no fabrication" anchor

Every Kimi persona ends with: *"Don't fabricate API endpoints — read the page first."* and *"Every assertion must reference a real DOM selector or value the human can verify."*

**Why effective:** this single line, repeated across personas, is what kept Kimi's outputs runnable instead of plausible-looking-but-broken.
