# Swarm Fix Verification — 2026-11-18

**Investigator:** kilo · seat `inbox/gx10-c9b9/bestiejobharvest-v2/kilo`
**Scope:** Verify the fixes claimed by swarm seats (`auditpage`, `auditpage-v2/v3/v4`, `ghactions-v2/v3`, `bestiejobharvest-v3`) against the **live remote `main`** of `eltonaguiar/findtorontoevents_antigravity.ca`.
**Method:** GitHub API (PR merge state) + `gh` (CI runs) + **direct file-content grep on `raw.githubusercontent.com/.../main/...`** (authoritative). The local worktree is a *shallow clone (53 commits)*, so git ancestry cannot confirm the 2026-11-16 merges — content-on-main was used instead.
**Remote main HEAD at check:** advancing ~1/min via `[skip ci]` scanner bots; the 2026-11-16 fixes are present but buried under bot noise.

---

## Verdict: PASS — fixes are real and landed · 3 minor bookkeeping discrepancies

No false or broken fixes found. The substantive engineering is sound and correctly scoped (test-only where claimed; production gates untouched).

---

## Confirmed landed on remote main (content-verified)

| Claim | Seat | PR / merge | Evidence on `main` | Status |
|---|---|---|---|---|
| `impossible_winrate_cohorts` moved **inside** the `counts` dict (+ AST regression test) — fixes the #862 stray-top-level regression | kilo-general (auditpage-v3) | #868 / `3a7b20ecf0a` | `tools/build_pf_registry.py:1117` key sits inside `counts` | ✅ |
| Circuit-breaker auto-flatten is a **real hook** (`flatten_callback`), logs when missing/fails | glyph-cluster (auditpage-v2) | #870 / `fbf77cd3c49` | `portfolio_circuit_breaker.py:71,213-233` | ✅ |
| VIX-gate **CI stabilization** (test env pins; root-caused the 22 red tests to a market-dependent gate; production untouched) | grok-4-7 (auditpage-v4) | #867 / `dc22eaa7b31` | `tests/test_wf_verdict_failing_gate.py:33-34` | ✅ |
| CSE `new_picks` int-crash **guard test** (supersedes #856) | grok-4-7 (auditpage-v4) | #871 / `288eac69561` | `tests/test_dashboard_cse_new_picks.py` → HTTP 200 | ✅ |
| Prioritized backlogs / next-steps / remaining-work docs | glyph-cluster, grok-4-7, deepseek-flash | #865 #866 #869 | merged (`merged_at` set) | ✅ |

## Merge-state confirmed (API / gh)

- `#868 #867 #871 #870 #869 #866 #865` → **merged** (`merged_at` set).
- `#856` → **CLOSED, `merged_at=null`** (superseded by #871) — matches the roster claim.

## CI on main

- Latest scheduled runs on `main`: **all `success`** (sampled last 8, up to 03:01Z).
- **1 of last 30 runs non-success:** `Copy Trader Intelligence` scrape on `main` @ 02:54Z — a **scraper flake, not the pytest gate**. The 22-failure pytest gate is addressed by #867.
- Core CI is green; one flaky scraper remains.

---

## Discrepancies / caveats

1. **PR #872 is OPEN, not merged.** grok-4-7 (auditpage) listed "PR 872" as a done/commit (the URL 301/404 audit doc). `gh pr view 872` → `state: OPEN, mergedAt: null`. It is **not on main yet** — minor overstatement in the roster.
2. **bestiejobharvest-v3/kilo live-board numbers are unverified against the canonical feed.** Claimed **7,903 dated rows / 175 Workday**. I independently measured the live `jobs.json` feed at **2,858 rows / 103 Workday-hosted / 785 LinkedIn-hosted / 0 duplicate URLs**. The `0 duplicate URLs` figure **matches**; the totals do not. The 7,903/175 likely reflects the **README tables** (superset incl. unsynced/archived rows) rather than the synced `jobs.json`. `<uncertain>` which artifact — the sibling should state its source before the number is quoted.
3. **New in-flight PR #873** — `fix(kalshi): stop pick verification trusting a 7-month-old snapshot` — **not in the roster**; opened after the snapshot. Represents unfinished work someone should land or park.
4. **Ancestry caveat:** the local worktree is a shallow clone (53 commits); `git merge-base --is-ancestor` returns false negatives for the 2026-11-16 merges. This is a tooling artifact, **not** evidence the fixes are missing — content-on-main confirms they are present.

---

## Bottom line

The swarm's engineering fixes are genuine, merged, and correctly scoped. Follow-ups for the fleet: **merge or close #872**, **clarify the board-count artifact** (#2), **land or park #873**, and **watch the flaky Copy Trader scraper**. Nothing here blocks trust in the audit-page / CI work.

_Verified 2026-11-18 ~03:0xZ against live remote `main`; HEAD moves ~1/min via `[skip ci]` bots._
