# Open PR Swarm Review (v2) — 2026-05-03

**Subagent:** NN1-OPEN-PR-SWARM
**Engines:** deepseek, xai, cerebras, kilo (4 fast/cheap engines)
**PRs reviewed:** #745, #749, #752, #724
**NOT touched:** #751 (MM1 owns)
**Total cost:** ~$0.21 (3 swarms × $0.07; #724 skipped at policy gate)

---

## Executive summary

| PR | Engine consensus | Action taken | CI | Mergeable |
|---|---|---|---|---|
| #745 | 4/4 favorable (3× APPROVE_WITH_CHANGES, 1× APPROVE) | Comment posted; **HOLD** | 3.11/3.12 FAIL (unrelated) | UNKNOWN |
| #749 | 4/4 APPROVE_WITH_CHANGES, all blocking on #752 overlap | Comment posted; **HOLD** | scan/smoke PASS | UNKNOWN |
| #752 | 4/4 APPROVE_WITH_CHANGES, all blocking on #749 overlap | Comment posted; **HOLD** | no checks reported | UNKNOWN |
| #724 | Skipped — bad commit `e4cb5b4f043` still in branch | Hold-comment posted | n/a | n/a |

**No PRs merged this run.** All 3 reviewed PRs got swarm comments; no APPROVE/REQUEST_CHANGES PR review left. Reviews are commentary-grade, not blocking, so author can still address & re-request.

---

## Per-PR detail

### PR #745 — `fix(resolver): wire MAX_HOLD_HOURS_BY_CLASS in universal_pick_resolver`

**Diff:** 41+/3- across 2 files (audit_trail/universal_pick_resolver.py + tests)
**Branch:** cherry-pick/max-hold-hours-by-class
**CI:** test (3.11) FAIL, test (3.12) FAIL — unrelated tests on main also fail (`test_events_staleness_filter`, `test_ueps_long_horizon_gate_bypass`, `test_stamp_feed_membership`). New `test_max_hold_hours_per_asset_class` passes locally.

**Verdict matrix:**
| Engine | Verdict | Risk | Headline |
|---|---|---|---|
| cerebras | APPROVE_WITH_CHANGES | MED | Case-sensitivity bug (FALSE POSITIVE — `.upper()` on line 33 handles it) |
| xai | APPROVE_WITH_CHANGES | MED | BOND 120h vs per_class_position_caps.py 336h inconsistency (acknowledged in PR body) |
| deepseek | APPROVE_WITH_CHANGES | LOW | Bare `except` swallows all exceptions in `_max_hold_hours_for` |
| kilo | APPROVE | MED | "MERGE_NOW" — same null-safety concerns as deepseek but non-blocking |

**Synthesized concerns (in priority order):**
1. (non-blocking) Hold-window inconsistency between this PR's `MAX_HOLD_HOURS_BY_CLASS` and the parallel constant in `alpha_engine/per_class_position_caps.py:80` — acknowledged as a follow-up TODO in PR body. Acceptable.
2. (non-blocking) `_max_hold_hours_for` catches bare `Exception` from `normalize_asset_class` and silently falls back to 48h. Recommend narrowing to `(ValueError, KeyError)` or logging on fallback.
3. (non-blocking) No integration test for `main()` expiry behavior with the new per-class window — only the helper is unit-tested.

**Action:** Posted commentary-grade comment. **Did NOT approve** — CI is red (even if for unrelated reasons). Operator should either (a) wait for main to clear unrelated failures + retrigger, or (b) override-merge if maintainer confirms failures are pre-existing.

---

### PR #749 — `fix(sports): fix DB connection variable mismatch causing 'Failed to load picks'`

**Diff:** 182+/17- across 6 files (db_config.php, sports_db.php, sports-betting.html, AGENTS.md, .env.example, updates/...)
**Branch:** fix/sports-picks-db-connection
**CI:** scan PASS, smoke PASS, deploy-guard skipped

**Verdict matrix:**
| Engine | Verdict | Risk | Headline |
|---|---|---|---|
| cerebras | APPROVE_WITH_CHANGES | MED | PHP fatal redeclaration with #752 (BLOCKING) |
| xai | APPROVE_WITH_CHANGES | MED | High overlap risk with #752 (BLOCKING) |
| deepseek | APPROVE_WITH_CHANGES | MED | Merge-conflict risk with #752; .env parser splits on first `=` |
| kilo | APPROVE_WITH_CHANGES | LOW | Coordinate with #752 to avoid conflict |

**Synthesized concerns (in priority order):**
1. **BLOCKING (4/4 unanimous):** PHP fatal `Cannot redeclare _lm_cred()` if both #749 and #752 land. Per CLAUDE.md, past sports PRs #399 (squash conflict markers) and #415 (missing require_once) caused production outages. One PR must close before the other merges.
2. (non-blocking) Hardcoded fallback URL `https://torontoevent.net/live-monitor/api/` in sports-betting.html:1382. Same-owner mirror per CLAUDE.md, acceptable.
3. (non-blocking) `.env` parser splits only on first `=`, so passwords containing `=` would truncate. Document this limitation.

**Action:** Posted commentary; **did NOT approve, did NOT request-changes** (commentary only). Operator must coordinate with #752 author and pick one.

---

### PR #752 — `fix(sports): db_config.php .env fallback so sports DB connects on 50webs shared hosting`

**Diff:** 64+/9- across 2 files (db_config.php, .env.example)
**Branch:** copilot/investigate-stale-sports-betting
**CI:** No checks reported on branch

**Verdict matrix:**
| Engine | Verdict | Risk | Headline |
|---|---|---|---|
| cerebras | APPROVE_WITH_CHANGES | MED | Error suppression masks .env misconfig; silent empty-string fallback |
| xai | APPROVE_WITH_CHANGES | MED | Sanitization gap in .env parser |
| deepseek | APPROVE_WITH_CHANGES | LOW | Cleaner than #749; overlap risk noted |
| kilo | APPROVE_WITH_CHANGES | MED | Null-byte handling missing vs reference impl in tmp/server_files/db_config.php |

**Synthesized concerns:**
1. **BLOCKING (4/4 unanimous):** Same redeclaration risk with #749. One PR must close.
2. (non-blocking, kilo) Reference impl in `tmp/server_files/db_config.php` includes `_fc_db_clean_password()` for null-byte stripping — this PR's `_lm_read_env_file()` does not. Trusted .env source so low impact, but worth porting.
3. (kilo flagged inconsistent fallback coverage; **REFUTED** on diff re-read — all 11 keys use `_lm_cred()` in final state lines 51-77).
4. (non-blocking, cerebras) Error suppression at top of file (`error_reporting(0); @getenv`) hides misconfig. Consider opt-in `LM_DEBUG=1`.

**Comparative analysis (deepseek + kilo):** PR #752 is the cleaner of the two — smaller blast radius (2 files vs 6), more thorough quote-stripping, sourced from proven `tmp/server_files/db_config.php` pattern. **Recommend keeping #752 + cherry-picking unique pieces from #749 (frontend failover in sports-betting.html, AGENTS.md destructive-git warnings, fix doc).**

**Action:** Posted commentary; **did NOT approve**. CI must trigger first; #749 must close first.

---

### PR #724 — `investigation(forex+crypto): deep-dives + FOREX rescue plan + 5 new strategies`

**Status:** Skipped at policy gate.
**Reason:** Bad commit `e4cb5b4f043` ("Add asset-class recovery analysis plan") still in commit list per `gh pr view 724 --json commits`. Per swarm consensus 2026-05-03, branch must be re-cut without that commit before swarm review.
**Action:** Posted hold-comment: `"Awaiting re-cut without commit e4cb5b4f043 per swarm consensus 2026-05-03. Holding."`

---

## Risk register (operator attention)

1. **#749 vs #752 conflict (HIGH).** Two open PRs both add identical-named PHP functions to the same file. Merging both = production fatal error. Decide which PR to close before any merge. Recommendation: close #749, take frontend+AGENTS pieces onto #752.
2. **#745 CI red on unrelated tests (MED).** New test passes locally; cleanup of stale tests on main is gating this merge. Cross-reference `reports/CI_TEST_311_312_DIAGNOSIS_2026_05_03.md`.
3. **#724 stuck on bad commit (LOW).** Author needs to re-cut branch.
4. **Frontend hardcoded fallback URL (LOW, #749).** `https://torontoevent.net/live-monitor/api/` is same-owner per CLAUDE.md but no integrity check.
5. **50webs deploy gate (post-merge ops).** Per CLAUDE.md, after either #749/#752 merges, `tools/deploy_sports_files.sh` MUST run + .env must be FTP-uploaded separately. PR bodies acknowledge this.

---

## Merge log

**This run:** 0 merges. 3 commentary-grade swarm reviews posted (#745, #749, #752). 1 hold-comment posted (#724).

---

## Outstanding queue (after this run)

- **#745:** Wait for unrelated CI to clear on main, then re-trigger. Or maintainer override-merge.
- **#749:** Coordinate with #752 author. One must close.
- **#752:** Same as #749. Trigger CI. Likely the survivor.
- **#724:** Author must re-cut branch without `e4cb5b4f043`.
- **#751:** MM1 owns (in flight) — NOT TOUCHED.

---

## Swarm metadata

- Run timestamps: 2026-05-04T00:44:00Z – 00:46:42Z
- All engines returned valid JSON with no transport failures.
- Cost: $0.21 actual ($1.20 budget cap, well under).
- Output dirs: `swarm_runs/run_review_745/`, `swarm_runs/run_review_749/`, `swarm_runs/run_review_752/` (gitignored — only this synthesis doc is checked in).

🤖 Compiled by NN1-OPEN-PR-SWARM
