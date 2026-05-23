# Documentation-PR Stall Audit — 2026-05-04

**Audited:** 2026-05-04T01:00Z  
**Scope:** All open PRs in `eltonaguiar/findtorontoevents_antigravity.ca`  
**Definition of doc-PR:** all changed files are `*.md`, `docs/**`, `updates/**`, `reports/**`, `.planning/**`, OR the PR carries a `documentation` label.  
**Definition of stalled:** open >72h with no commits or comments in the last 48h; OR has merge conflicts; OR has failing required checks not addressed in 48h; OR awaiting a review that was requested >5 days ago.

---

## 1. Full Open-PR Inventory (4 open PRs)

| # | Title | Doc-PR? | Why / Why Not |
|---|---|:---:|---|
| 754 | fix(sports): surface Odds API unauthorized + stale-picks banner | ❌ | Changes `.github/workflows/sports-betting-refresh.yml` + `live-monitor/sports-betting.html` |
| 751 | fix: This Month / Next Month date filter bugs | ❌ | Mixed — `TORONTOEVENTS_ANTIGRAVITY/index.html` (code) + `updates/*.md` |
| 745 | fix(resolver): wire MAX_HOLD_HOURS_BY_CLASS | ❌ | Changes `audit_trail/universal_pick_resolver.py` + `tests/test_universal_pick_resolver.py` |
| 724 | investigation(forex+crypto): deep-dives + FOREX rescue plan + 5 new strategies | ✅ | All 6 files are `reports/*.md` + `FOREX_COMMODITIES_BONDS.MD` — zero code |

**Doc-PRs found: 1 (PR #724 only)**

---

## 2. Doc-PR Detail Table

| Field | PR #724 |
|---|---|
| **Number** | 724 |
| **Title** | investigation(forex+crypto): deep-dives + FOREX rescue plan + 5 new strategies |
| **Branch** | `investigation/forex-crypto-deep-dives-2026-05-03` |
| **Author** | eltonaguiar |
| **Draft** | No |
| **Age (days)** | ~0.9 d (created 2026-05-03T03:40Z) |
| **Last activity (days ago)** | ~0.0 d (updatedAt 2026-05-04T00:42Z — < 2h ago) |
| **Mergeable** | Not marked CONFLICTING |
| **Review decision** | None (no human APPROVED / CHANGES_REQUESTED) |
| **Check runs** | 1 run: `scan` = **success** |
| **Labels** | None |
| **Files changed** | 6 (all `.md`) |

### Files in PR #724

| File | Type | Status |
|---|---|---|
| `FOREX_COMMODITIES_BONDS.MD` | Root-level MD | Added (651 lines) |
| `reports/deep_dive_FOREX_2026_05_03.md` | reports/ | Added |
| `reports/deep_dive_CRYPTO_quan_unknown_drag_2026_05_03.md` | reports/ | Added |
| `reports/FOREX_RESCUE_CONSOLIDATED_2026_05_03.md` | reports/ | Added |
| `reports/forex_corrupt_filter_analysis_2026_05_03.md` | reports/ | Added |
| `reports/forex_new_strategies_2026_05_03.md` | reports/ | Added |

---

## 3. Classification

| # | Title | age_days | last_activity_days | **Status** | Recommended Action |
|---|---|---:|---:|---|---|
| 724 | investigation(forex+crypto) deep-dives | 0.9 | 0.0 | **MERGEABLE_CLEAN** | Human owner review + peer ack, then merge |

### Stalled criteria check for PR #724

| Criterion | Result |
|---|---|
| Open >72h AND no activity in last 48h | ❌ No — only ~21h old, activity < 2h ago |
| Merge conflicts | ❌ No — not flagged as CONFLICTING |
| Failing required checks not addressed in 48h | ❌ No — `scan` = success, no other required checks |
| Awaiting review requested >5 days ago | ❌ No — PR is <1 day old |

**Result: PR #724 is NOT stalled by any strict criterion.**

### Classification rationale

PR #724 is classified **MERGEABLE_CLEAN** on mechanical criteria:
- CI passes (scan: success)
- No detected merge conflicts
- No failing checks
- Not a draft

**Caveats before merging:**
1. No human review approval exists yet — only a Codex bot `COMMENTED` review (submitted 2026-05-03T03:45Z, ~21h ago).
2. PR body states: *"Peer ack required before any code PR ships."* This gate applies to the downstream code PRs that would implement the investigation findings, not to merging the investigation docs themselves. The doc files (deep-dives, rescue plan, strategy proposals) are safe to land without a code gate.
3. **FOREX_RESCUE_CONSOLIDATED_2026_05_03.md** explicitly calls out that 2 claims in `deep_dive_FOREX_2026_05_03.md` were fabricated by an earlier agent and superseded. Both files are present in this PR so the record is self-consistent, but reviewers should be aware.
4. The PR notes a pending mobile gzip verify (`trig_017S21udszbns7J99jjdZ7UT @ 03:45Z`) — unclear if completed.

---

## 4. Summary Counts

| Category | Count |
|---|---|
| Total open PRs | 4 |
| Doc-PRs (pure) | **1** |
| Doc-PRs (mixed code + docs) | 1 (PR #751 excluded from this audit) |
| MERGEABLE_CLEAN | 1 |
| STALLED_NO_ACTIVITY | 0 |
| STALLED_CONFLICT | 0 |
| STALLED_FAILING_CHECKS | 0 |
| STALLED_AWAITING_REVIEW | 0 |
| DRAFT | 0 |

---

## 5. TOP-5 "Close or Unblock Now" List

Only 1 doc-PR exists. The list is ranked by urgency.

### #1 — **PR #724** `investigation/forex-crypto-deep-dives-2026-05-03` — Unblock / Merge

**Status:** MERGEABLE_CLEAN  
**Age:** ~21h  
**Why it needs attention:** This is the canonical investigation backing the FOREX rescue plan and CRYPTO drag re-attribution. Several downstream code PRs (corruption-filter fix, strategy wiring) are blocked on peer-ack of these docs. Every day these docs sit unmerged increases the chance of conflicting edits or a peer agent proposing the same fix independently.

**Recommended actions (in order):**
1. Owner reviews `reports/FOREX_RESCUE_CONSOLIDATED_2026_05_03.md` (authoritative doc) and `reports/forex_corrupt_filter_analysis_2026_05_03.md` (the corruption-filter root cause).
2. Confirm mobile gzip verify is either done or not a merge blocker.
3. Leave a GitHub review APPROVED or request changes within 24h.
4. Merge once acked — no further CI concerns.

*(No entries #2–#5: only one doc-PR is open as of this audit date.)*

---

## 6. Non-Doc PRs Noted for Cross-Reference

These were excluded from the doc-PR audit but are mentioned because they interact with the doc-PR investigation findings:

| # | Title | Age | Status | Note |
|---|---|---:|---|---|
| 745 | fix(resolver): wire MAX_HOLD_HOURS_BY_CLASS | ~5h | `test (3.12)` FAILING | Code companion to FOREX investigation; 3.12 CI failure needs triage before merge |
| 751 | fix: This Month / Next Month filter bugs | <1h | DRAFT, no checks yet | Mixed doc+code; marked draft, has APPROVED swarm review; operator action required to undraft |
| 754 | fix(sports): surface Odds API diagnostic | <1h | scan+smoke PASS | Unrelated to doc-PRs; mechanically ready |

---

*Report generated by Claude Code audit agent on 2026-05-04.*  
*Reproducer: spawn `doc-pr-audit` agent with instructions at top of this PR's body.*
