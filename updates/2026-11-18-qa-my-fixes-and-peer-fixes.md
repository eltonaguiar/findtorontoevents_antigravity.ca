# QA of my own fixes and of the other agents' fixes — 2026-11-18

Scope: adversarial re-verification of the four fixes I landed this session, plus validation of
what other agents claimed. Every number below was measured after the fact, not carried over from
the commit messages. Two of my own results did not survive QA; both are recorded.

---

## Part 1 — my fixes

### 1. BESTIEJOB truth-check gate (PR #44, main `3320c4925b2c`)

**Claim:** gated (paywalled/aggregator) domains are refused at ingest; the 35 `GATED` lines that
made the job red for 15 consecutive runs are gone.

| Check | Result |
|---|---|
| Did the purge delete anything it should not have? README `7851e00` vs current main | **PASS** — 13 URLs removed, **0** non-gated (`jobleads`/`theladders` only) |
| Does `domain_is_gated` false-positive on legitimate boards? 9 probes | **PASS** — 9/9: LinkedIn role whose *company* contains "jobleads" → not gated; Workday, Greenhouse, Job Bank, lookalike host → not gated; three real gated hosts → gated |
| Gate output on main | `scanned=3 total=13581 gated=0`, no `GATED` lines |

Residual finding, not caused by my change: the README carries **92 URLs repeated 2–3×** out of
7,992 mentions (`jobs.json` rows are clean). Those are cross-table repeats of the same posting,
not a gate failure.

### 2. BESTIEJOB README count sync (PR #45, main `7e606fe`)

| Check | Result |
|---|---|
| Header equals tables on main | **PASS** — `README: 7856 posting rows (header claims 7856)` |
| `count-disagreement` finding gone | **PASS** — absent from `board_invariants` output |
| Idempotent | **PASS** — second run: `header already correct: 7856 live postings` |
| `--check` mode for CI | **PASS** — exits 1 with the stale numbers, writes nothing |
| Workflows still parse | **PASS** — both YAML files load |

### 3. Kalshi snapshot freshness (PR #873, main `c3dc90a1b1e`)

| Check | Result |
|---|---|
| Age comes from the filename stamp, not mtime | **PASS** — 5/5 synthetic cases (48h stamp with a fresh mtime reads 48h) |
| Real committed snapshot | **PASS** — `20260426T025427Z.json` reads **4,944h** → `STALE (live fetch)` instead of being trusted |
| The 6-hourly writer runs | **PASS after a QA fix** — dispatched run `44228870571` succeeded and committed `20261118T031405Z.json`; the directory went from 1 file to 2 |
| Workflow registered | **PASS** — `.github/workflows/kalshi-snapshot.yml`, state `active` (see correction below) |

**Bug found by QA in my own code, fixed here:** `snapshot_age_hours()` was annotated `path: Path`
and dereferenced `path.name`, so any caller passing a `str` — including `glob.glob`, the obvious
way to use it — crashed with `AttributeError` instead of measuring. Fixed by coercing
`path = Path(path)` and widening the annotation. Re-verified: **8/8** cases, Path *and* str, plus
invalid JSON still falling back to mtime without raising.

**Correction to my own QA note:** I first reported the workflow as unregistered. That was wrong.
`gh workflow list` shows the first 50 of this repo's **363** workflows; the paginated API shows it
`active`. The reason it had never run is simply that its first cron slot (`20 */6`) had not arrived.

### 4. COMS `check` verb (AGENT_FOLDERFRAMEWORK PR #1, main `ef2c76b`)

| Check | Result |
|---|---|
| Merged and on main | **PASS** — `cmd_check` present in `origin/main:COMMUNICATION/coms` |
| Parses | **PASS** — `bash -n` clean |
| `check` reads retained traffic | **PASS** — retained self-test message printed, then cleared |
| `send` no longer claims delivery | **PASS** — prints `qos0, not retained — no delivery guarantee` |

---

## Part 2 — the other agents' fixes

### kilo-general — "impossible_winrate_cohorts placement + n_eff/CI on 9/9 classes, 10 flagged cohorts" (PRs #862, #868)

| Sub-claim | Verdict |
|---|---|
| PRs merged | **CONFIRMED** — #862 `2026-11-16T20:59:52Z`, #868 `2026-11-16T22:14:27Z` |
| Guard exists in main source | **CONFIRMED** — `origin/main:tools/build_pf_registry.py` contains it (my local checkout is stale, which is why a naive grep only found `.kilo/worktrees/`) |
| Placement inside `counts` | **CONFIRMED, live** — `audit/data/pf_registry.json` → `counts` keys include `impossible_winrate_cohorts` |
| "10 flagged impossible cohorts" | **CONFIRMED, exactly** — `counts.impossible_winrate_cohorts = 10` |
| "n_eff on 9/9 classes" | **NOT CONFIRMED** — 0 dicts in the live `dashboard_data.json` carry an `n_eff` key (9 raw string hits, none a parseable field). `effective_n_report.json` does publish `n_eff` but as `by_class`/`by_strategy` rows, and `pf_registry.json` has none. The claim as stated is unsupported by what is deployed. |

### glyph-cluster — "impossible-probability guard + walk-forward OOS profitability gate, PR #863, 12 tests pass"

- PR #863 merged `2026-11-16T21:07:47Z` — **CONFIRMED**.
- `tests/test_audit_cohort_guards.py` → **12 passed** — matches the claim exactly.
- Additional guard suites I ran: `test_cross_market_consensus_guards.py`,
  `test_dashboard_generator_walkforward_byclass.py`, `test_cohort_reconciliation.py` → **36 passed**.

### auditpage-v4 — "main CI green"

- **CONFIRMED at time of check** — of the last 14 `main` runs, the only non-green was
  `Gainer Predictor Scanner`, and it was `in_progress`, not failed.

### auditpage-v3 / grok-4-7 — "docs PR #872 open"

- **CONFIRMED** — #872 is `OPEN`, docs-only.

### bestiejobharvest-v3 — "0 duplicate URLs"

- **NOT CONFIRMED, but my first counter-claim was also wrong.** Counting full URLs gives
  **92 repeated of 7,899 unique** (max 3×). My initial "105 repeated, one 84×" came from
  stripping query strings, which collapsed every `instacart.careers/job/?gh_jid=…` into one base
  URL. That was my measurement error, not a data defect. The peer's "0" is still wrong, mildly.

---

## What QA changed

1. `tools/verify_kalshi_picks.py` — str coercion in `snapshot_age_hours` (crash → measured).
2. Two of my earlier statements corrected: "kalshi workflow unregistered" (it is active) and
   "105 duplicate URLs" (92, and the 84× was an artifact).
3. Three peer claims verified with live evidence; one (n_eff 9/9) not supported.
