# PR #751 — 5-Model 3-Round Swarm Review

**PR title:** fix: This Month / Next Month date filter bugs (zombie 2025 events, multi-day running events, label hiding)
**Branch:** `copilot/fix-month-filter-issues`
**Author:** GitHub Copilot agent
**Diff:** +226 / -7 LOC across 2 files (`TORONTOEVENTS_ANTIGRAVITY/index.html`, `updates/2026-05-04-this-month-next-month-filter-bug-fix.md`)
**Reviewer:** subagent MM1-PR751-REVIEW
**Date:** 2026-05-04

## Swarm metadata

| Item | Value |
|---|---|
| Engines | deepseek, xai, cerebras, kilo, ollama_cloud |
| Rounds | 3 (independent → cross-critique → final verdict) |
| Total swarm calls | 15 (5 × 3) |
| Total cost (estimated) | ~$0.207 ($0.071 + $0.068 + $0.068) |
| Cost cap | $1.50 |
| Total wall time | ~6 min (parallel within each round) |
| Engine failures | 0 (all 15/15 returned content) |
| Schema-strict parsing failures | 4 (cerebras + ollama_cloud each round 1 & 2 wrapped JSON in code-fence; content fully recoverable from `commentary_text`) |

## What the PR claims to fix

| Bug | Surface | Root cause (per Copilot) | Fix |
|---|---|---|---|
| **A** | "This Month" shows zombie 2025-05-23 events | `__RAW_EVENTS__` pre-filter drops `start<today`, but React still renders the unfiltered feed; `eventData=null` → `__parseCardDisplayedDate__("MAY 23")` assigns year 2026 (same-month wrap-guard `4<4`=false) | Fix 2: when `eventData=null` AND `__RAW_EVENTS__` loaded, set `shouldShow=false` |
| **B** | "This Month" hides 80 multi-day shows still running (& Juliet etc.) | Pre-filter only checked `start>=today`, dropping running shows whose `start<today` | Fix 1: keep events where `end_date>=today` too |
| **C** | "Next Month" shows "MAY xx" labels behind "JUN x" badge overlay | `_t.length <= 12` skipped React date elements like "MAY 8 Wednesday" (15 chars) | Fix 3: raise length limit 12 → 30 |

## Per-round consensus matrix

### Round 1 — Independent review

| Engine | Verdict | Bug A correct | Bug B correct | Bug C correct | Tests adequate |
|---|---|---|---|---|---|
| deepseek | APPROVE_WITH_CHANGES | yes | yes | yes | NO |
| xai | APPROVE_WITH_CHANGES | yes | yes | yes | NO |
| cerebras | APPROVE_WITH_CHANGES | yes | yes | yes | NO |
| kilo | APPROVE_WITH_CHANGES | yes | yes | yes | NO |
| ollama_cloud | REQUEST_CHANGES | yes | yes | yes | NO |

**Round 1 unanimous on:** all 3 bug diagnoses correct, all 3 fixes logically sound, no new tests added.

### Round 2 — Cross-critique

| Engine | Verdict | Refined blocking | Refined major |
|---|---|---|---|
| deepseek | APPROVE_WITH_CHANGES | tests; null-undefined fallback; race condition | timezone; substring on short strings; length-30 |
| xai | APPROVE_WITH_CHANGES | tests; race condition | timezone; length-30 |
| cerebras | APPROVE_WITH_CHANGES | undefined fallback; race condition | timezone; length-30 |
| kilo | APPROVE_WITH_CHANGES | undefined fallback; over-hide regression | timezone drift; substring ordering |
| ollama_cloud | APPROVE_WITH_CHANGES (softened from REQUEST_CHANGES) | undefined fallback | timezone; missing tests |

**Round 2 result:** ollama_cloud retracted REQUEST_CHANGES. 5/5 = APPROVE_WITH_CHANGES.

### Round 3 — Final verdict

| Engine | Final verdict | Risk | Must-fix count |
|---|---|---|---|
| deepseek | **MERGE_NOW** | LOW | 0 |
| xai | MERGE_AFTER_FIXES | MEDIUM | 2 |
| kilo | MERGE_AFTER_FIXES | LOW | 4 (tests only) |
| cerebras | MERGE_AFTER_FIXES | LOW | 4 (tests + regex tightening) |
| ollama_cloud | MERGE_AFTER_FIXES | MEDIUM | 3 (null-coalesce + regex + pad) |

**Tally:** 1× MERGE_NOW + 4× MERGE_AFTER_FIXES. 0× REQUEST_CHANGES. 0× REJECT.

## Cross-round evolution

- **R1 → R2:** Concerns coalesced from 10 unique items to two BLOCKING themes (the `String(undefined)` literal-string fallback and the Fix 2 over-hide race). Three concerns demoted as out-of-scope or pre-existing (recurring events, locale month names, misleading comment). Timezone confirmed pre-existing — PR inherits the bug, doesn't introduce it.
- **R2 → R3:** When the operator framing surfaced that (a) the `_ed` fallback prevents the literal-`"undefined"` path from being reachable in normal flows (because `_end` falls back to `_ed`, not to `String(undefined)`), and (b) `__RAW_EVENTS__` is set ONLY on fetch success (so the over-hide race cannot trigger on a failed fetch), three reviewers (deepseek, kilo, cerebras) downgraded the BLOCKING concerns to nice-to-haves. Two reviewers (xai, ollama_cloud) still wanted a defensive guard added before merge — but acknowledged the issues are "less likely than Round 2 suggested" (xai).

## Final verdict

**APPROVE WITH FOLLOW-UP HARDENING** — the swarm unanimously confirms all three bug diagnoses are correct, all three fixes are logically sound, and the production blast radius of the fix being wrong is strictly smaller than the current broken state (zombie 2025 events on the live homepage). 5/5 reviewers vote merge-track; majority want hardening tests + minor defensive guards before squash.

Per operator instructions ("If 3+ say MERGE_AFTER_FIXES … post `gh pr review --approve` … skip merge"), the action is **APPROVE without merge**, leaving the merge decision to the operator after the recommended hardening lands.

## Must-fix list (consolidated by frequency)

Items mentioned by ≥3/5 final reviewers:

1. **Add unit tests for the new pre-filter end-date logic** — keep events where `end_date>=today` and exclude where both dates `<today`. (5/5)
2. **Add unit tests for Fix 2 `shouldShow=false` branch** — verify hide when `eventData=null && __RAW_EVENTS__` set. (5/5)
3. **Add unit tests for length-30 threshold** — verify it hides "MAY 8 Wednesday" but does not hide a description like "May Festival in Trinity Bellwoods". (5/5)
4. **Tighten the length-30 hide condition with a stricter date-pattern regex** — e.g. `/^[A-Z]{3,9}\s+\d{1,2}(?:\s+[A-Z]{3,})?$/` — to avoid masking real description copy that happens to start with a month abbreviation. (3/5: cerebras, ollama_cloud, xai-implied)

Items mentioned by 1-2 reviewers (defer to follow-up):

5. **Add explicit `?? ''` null-coalesce on `String(e.end_date || e.endDate || _ed)`** so the literal-`"undefined"` path is provably unreachable, even though current data flow shouldn't hit it. (xai, ollama_cloud)
6. **Pad / normalize date strings to `YYYY-MM-DD`** before `substring(0,10)` comparison, defending against `2026-5-4` vs `2026-05-04` lexicographic mis-ordering. (deepseek, kilo, ollama_cloud)
7. **Compute `_today` in `America/Toronto` zone** instead of UTC. Pre-existing bug; document and queue. (5/5 nice-to-have)

## Test additions required (consensus)

| Test name | Verifies |
|---|---|
| `pre_filter_keeps_multi_day_events_with_end_date_after_today` | Fix 1: events with `start<today && end>=today` are retained in `__RAW_EVENTS__` |
| `pre_filter_excludes_purely_past_events` | Fix 1: events with `start<today && end<today` are dropped |
| `pre_filter_null_end_date_fallback_to_start` | Fix 1: `end_date=null` falls back to `start_date`, no `"undefined"` string |
| `pre_filter_handles_undated_events` | Fix 1: events with no date fields keep `return true` (TBD path) |
| `fix2_shouldShow_false_when_eventData_null_and_rawEvents_loaded` | Fix 2: hide branch fires correctly |
| `fix2_falls_through_to_displayParse_when_rawEvents_not_loaded` | Fix 2: pre-fetch race window does NOT silently hide |
| `nextMonth_badge_hides_react_dateLabel_with_dayName` | Fix 3: "MAY 8 Wednesday" gets `visibility: hidden` |
| `nextMonth_badge_does_not_hide_description_starting_with_month` | Fix 3: "May Festival …" stays visible |

## Risk assessment

**Regression risk:** LOW (3/5) to MEDIUM (2/5).

- The two MEDIUM votes (xai, ollama_cloud) cited the unguarded `String(undefined)` path and the length-30 over-hide. Both are theoretical until somebody serves a malformed event row or writes a description starting with `MAY 8 …` exactly.
- The three LOW votes correctly noted that `__RAW_EVENTS__` is only set on fetch-success, so Fix 2's race condition does not trigger on a failed feed (the global stays undefined → branch falls through to old behaviour).
- Production blast radius if wrong: at WORST, a few legitimate cards get hidden or a few zombies persist. The current state already has zombies live in production, so any partial regression is still net-positive.

## Action taken

1. **Posted approving review** on PR #751 with consensus summary + must-fix list (see action log below).
2. **Did NOT merge** — majority verdict is MERGE_AFTER_FIXES, so leaving merge to operator after follow-up hardening lands.
3. **No `--admin`, no force-push.**
4. **No CI to gate against** — `gh pr checks 751` returned "no checks reported on this branch", so the approve is on review-criteria alone.

## File index

- Round 1 prompt: `swarm_runs/_pr751_round1.md`
- Round 1 outputs: `swarm_runs/pr751/round1/{deepseek,xai,cerebras,kilo,ollama_cloud}.json` + `_summary.json`
- Round 2 prompt: `swarm_runs/_pr751_round2.md`
- Round 2 outputs: `swarm_runs/pr751/round2/`
- Round 3 prompt: `swarm_runs/_pr751_round3.md`
- Round 3 outputs: `swarm_runs/pr751/round3/`
- This report: `swarm_runs/PR_751_5MODEL_3ROUND_REVIEW.md`
