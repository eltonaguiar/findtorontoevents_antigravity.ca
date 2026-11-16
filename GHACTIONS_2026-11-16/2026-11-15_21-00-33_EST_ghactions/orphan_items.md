# Orphan Items — GHA Health Audit

**Base commit:** `origin/main` @ `eb23252219786dc09362a5a500aef2f9bc6f794f`
(`git rev-parse origin/main`, repo `/home/eaguiar2015/findtorontoevents_antigravity.ca`)

**Scope:** the two items nobody else in this swarm owns.

1. **DB Freshness Check** — workflow idle 176 days.
2. **Sports workflows** — 5 workflows reported as `disabled_manually`.

**Clone-state caveat (affects everything below):** the local clone is shallow + blob-filtered. Only `origin/main` objects are local; 212 of 213 branch heads are unresolvable (`fatal: Not a valid object name`). Every finding here is from `origin/main` trees only. Nothing here depends on an unreadable branch, but read this as "what main says", not "what GitHub is doing" — the *runtime* state of any workflow (last run, disabled flag) is **UNVERIFIED**; no API was called (per coordinator ruling).

**Method:** local git only. No API, no browser, no CDP, no DB, no workflow edits.

---

## Impact table

| workflow | what stops | affected /audit section/table | severity |
|---|---|---|---|
| `db-freshness-check.yml` (**DB Freshness Check (Legacy Manual)**) | Nothing operational — it can only ever be triggered by hand. `on:` is **`workflow_dispatch` only** (no `schedule`, no `push`). Its 176-day idle time is therefore *expected*, not a fault. What stops: it is the **only** thing that ever commits `audit_dashboard/data/db_freshness.json` back to the repo. | None directly. No PHP/JS/HTML consumer reads `db_freshness.json` (verified by `git grep` over `*.php *.js *.html`: only Python tooling reads it). Indirectly, the committed JSON is the repo's only in-tree record of DB health. | **LOW** (dead code, near-zero risk to archive) |
| `db-freshness-guardian.yml` (**DB Freshness Guardian** — the replacement) | Nothing stops; it runs hourly (`cron: 0 * * * *`). **But it only uploads an artifact** (`db-freshness-report`, 7-day retention) and **never commits**. So the committed `db_freshness.json` can only get older even while the guardian is green. | The `/audit` page has no DB-freshness tile — so no rendered section is lying. The stale file is a latent trap for any future consumer. | **MEDIUM** — design gap, not an outage |
| `sports-betting-refresh.yml` (**Sports Betting Odds Refresh & Auto-Settle**) | `cron: '0 15,18,21,0,3 * * *'` (5×/day). If disabled: no new odds, no paper auto-place, **no auto-settle**. Picks never resolve → win rate / ROI / CLV all freeze. Also gates the `03:00 UTC` extra-source slot. | `/live-monitor/sports-betting.html` — KPIs, picks today, performance, pick history (30d). **NOT** `/audit`: `audit_dashboard/index.html` L2882–2912 (`_applyGlobalSportsFilter`) drops every `asset_class` in `SPORTS|SPORT|BETTING` at data load, with the comment *"User directive: ensure sports is removed from findtorontoevents.ca/audit"*. | **HIGH** (if actually off) — freeze is silent: page renders, numbers just stop moving |
| `sports-data-snapshots.yml` (**Sports data snapshots**) | `cron: '*/15 * * * *'`. Pinnacle moneyline anchor + NHL goalie/GSAx feed, FTP'd to the live site. If disabled: Pinnacle snapshots age past the **15-minute staleness guard** in `sports_value_analyze_lib.php:278` and are **silently ignored** → devig falls back to Odds API, and if Odds API has dropped Pinnacle, value analysis loses the Shin devig path. | `/live-monitor/sports-betting.html` value/EV analysis (via `sports_value_analyze_lib.php`). NHL goalie overlay: `sports_value_nhl_goalie_lib.php` **is** wired in (`require_once`, L7 of analyze lib and L9 of `sports_picks.php`) — so the "Phase 2 not wired" header comment is **stale advice**. | **MEDIUM–HIGH** — silent degradation, no error surfaced |
| `sports-prediction-market-sync.yml` (**Sports Prediction Market Sync**) | `cron: '0 14,20 * * *'` (2×/day). Commits `sports_prediction_market_signals.json`, read by `sports_picks.php:106-107`. If disabled: prediction-market confirmation data goes stale; the divergence badge / PM composite boost stops updating. | `/live-monitor/sports-betting.html` — prediction-market divergence badges (`prediction_market_confidence`, `_score_boost`, `_hint`). | **MEDIUM** — degrades enrichment, not the base pick list |
| `sports-forensics-weekly.yml` (**Sports Forensics Weekly**) | `cron: '30 6 * * 1'` (Mondays). Pure **read-only** curl against production: fetches `sports_forensics.php` segments + daily returns and asserts `ok`. It writes nothing anywhere. If disabled: **zero** data impact; you only lose the Monday canary that the forensics endpoint still returns `ok`. | None. It is a canary over `/live-monitor/api/sports_forensics.php`, not a producer for it. | **LOW** |
| `sports-smoke-and-e2e.yml` (**Sports endpoint smoke + Playwright**) | `cron: '17 * * * *'` hourly, + PR-triggered, + dispatch. Read-only smoke/Playwright against live production endpoints. If disabled: lose the hourly **git-HEAD-vs-FTP-deployed drift canary** (header cites two outages from committed-but-not-deployed / deployed-but-not-committed). | None directly — it protects everything sports-facing in `/live-monitor/`, which is why losing it is not free. | **MEDIUM** — losing a monitor, not a producer |

> [!NOTE]
> **All 5 sports files still carry live `cron:` blocks in `origin/main`.** Their `disabled_manually` state is a **GitHub-side setting**, invisible to git. I could not confirm it from local git, and per the no-API ruling I did not try. Treat "these 5 are disabled" as **UNVERIFIED carrier claim**, and note that a git-side disable (`*.yml.disabled` rename) was **not** done — so nothing in the repo records the intent. That is itself the finding: *a disabled-by-UI workflow leaves no audit trail in the tree.*

---

## Finding 1 — DB Freshness Check is dead by design, and its replacement has a design gap

**Verified from git:**

- `.github/workflows/db-freshness-check.yml` → name `DB Freshness Check (Legacy Manual)`, `on:` = `workflow_dispatch` **only**. No schedule, no push. **176 days idle is fully explained**: nobody dispatches it. It is **not** `disabled_manually`.
- Its final step commits `audit_dashboard/data/db_freshness.json` back to the repo (`if: always()`, via `safe_push.sh || true`).
- Replacement: `db-freshness-guardian.yml` → hourly `cron: 0 * * * *` + `push [main]` on `tools/db_freshness_check.py`, on itself, + dispatch. **Same script, same thresholds.** But it **only uploads an artifact** and **never commits**.
- **The defect is the seam between them:** the committer is manual-only, the runner is artifact-only. Net effect — the committed `db_freshness.json` can only get older, regardless of the guardian being green.

**Two different ages, do not conflate them:**

| Age | What it measures | Value |
|---|---|---|
| 176 days | Inactivity of `db-freshness-check.yml` (the workflow) | 176 d |
| ~43 days | Last time `db_freshness.json` was *committed* on `origin/main` | commit `e59990e9729`, 2026-10-04 03:05:27 +0000, msg `Health check report [skip ci]` |

The 176-day number is the *workflow's* idleness. The *file's* real age is ~43 days as of base commit. Neither number is a live DB reading.

**Committed content (stale):** `"overall": "RED"`; `signal_outcomes` RED at `minutes_stale: 115782.0` (~80 days) — itself already stale at commit time, which is a second-generation staleness worth noting: *the file was committed RED, and then stopped being updated at all.*

**Consumers — the definitive answer (this was the open question):**

- **No PHP/JS/HTML consumer exists.** `git grep -l 'db_freshness' origin/main -- '*.php' '*.js' '*.html' '*.py'` returns **only Python**: `tools/db_freshness_check.py`, `tools/db_health_check.py`, `tools/check_pending_freshness.py`, `tools/at_signal_outcomes_volume_check.py`, `tools/audit_test_framework/tests.py`, `tools/test_audit_framework.py`.
- `outcome-resolver.yml` mentions `db_freshness` **only in a comment** (~L237): the insert-volume guard's comment says *"db_freshness_check tracks staleness, not insert VOLUME vs a baseline"*. **It is not a consumer.** Earlier drafts listed it as one — that was wrong.

**Consequence:** no rendered page is currently lying. The risk is *latent*, not active — but it becomes active the moment anyone builds a DB-health tile or a monitor that reads that path, and they will trust a file whose name promises freshness.

**Grader thresholds** (`tools/db_freshness_check.py`), for reference when deciding: live_picks GREEN <2h / YELLOW 2–6h / RED >6h; resolver_outputs GREEN <4h / YELLOW 4–12h / RED >12h; backtests GREEN <48h / YELLOW 48–168h / RED >168h; signal_outcomes GREEN <6h / YELLOW <24h / RED >24h. Exit 0/1/2 = all GREEN / any YELLOW / any RED.

### Decision A — what to do with the legacy manual workflow — **NOT DECIDED**

| Option | What it buys | Risk |
|---|---|---|
| **A1. Archive it** (delete `db-freshness-check.yml`, or rename to `*.yml.disabled`) | Removes a permanent 176-day red herring; anyone auditing "why is this workflow idle" stops asking. | **Near-zero.** Nothing can trigger it anyway. Only real cost: docs that tell a human to "dispatch `db-freshness-check`" become dead advice — `AGENTS.md`, `HEARTBEAT.md`, `docs/MYSQL_ENV_SETUP.md` reference it. Those need the same edit or they will send the next person to a missing workflow. |
| **A2. Leave it** | Zero effort now. | Every future audit re-opens the same 176-day question, and the one path that writes the JSON stays manual-only — so the stale file is preserved indefinitely. |

### Decision B — how to fix the guardian's no-commit gap — **NOT DECIDED**

| Option | What it buys | Risk |
|---|---|---|
| **B1. Restore commit-back in the guardian** | The in-tree `db_freshness.json` becomes truthful; artifact + repo agree. | **Hourly bot commits to `main`.** Every one is a push that can re-trigger push-based workflows and the FTP deploy chain — the same push→deploy→push amplification `@triage-expert` flagged in #91 (and #91's retraction of its own "~2 min deploy" number is the proof that this chain's frequency is not well understood). 24 commits/day of churn to `main` for a file nothing reads today. |
| **B2. Stop relying on the committed file** (delete `db_freshness.json` from the tree; keep artifact-only as the source of truth) | No `main` churn, no stale decoy. Artifacts already have 7-day retention, which is plenty for a staleness check. | Anything that *does* read the committed path breaks — currently nothing does, so the blast radius is zero **today**; if the artifact is the only copy and a run fails, there is no historical record beyond 7 days. |
| **B3. Leave both as-is** | Nothing changes. | A permanently stale, permanently RED JSON sits in the tree with a freshness-sounding name — a trap that will eventually be trusted. |

> [!IMPORTANT]
> A and B are **independent**. Do not couple "archive the legacy workflow" to "fix the guardian" — A1 is safe on its own, and B2 is what makes A1 fully clean.

---

## Finding 2 — the sports workflows are frozen in a way that reads as "recent"

**The trap, stated plainly:** `disabled_manually` stops *new* rows. It does not delete, date-stamp, or grey-out the *existing* rows. So `/live-monitor/sports-betting.html` keeps rendering the last written picks and odds at full confidence, and every "last 30 days" / "pick history 30d" view keeps counting them as current until the timestamps individually age out of their windows. **Frozen-but-plausible data is worse than an explicit "section retired" notice**, because the page gives no signal that it is a museum.

**What each disabled workflow actually takes down** (see table above): the odds/settle producer is the one that matters — without it picks never resolve, so win rate, ROI and CLV all freeze at their last values, and those are the headline KPIs.

**Two supporting oddities found while verifying:**

1. `sports-data-snapshots.yml`'s header says the NHL goalie overlay's *"PHP lib not yet wired — Phase 2"*. That comment is **stale**: `sports_value_analyze_lib.php:7` and `sports_picks.php:9` both `require_once sports_value_nhl_goalie_lib.php`. So the goalie feed has a live consumer and its staleness is a real, silent degradation — the comment will mislead whoever triages this.
2. All 5 files retain their `cron:` blocks. A future "are these disabled?" check done against the tree (as this audit had to do) returns **no**: the intent exists only in GitHub's UI state, which git history cannot show and no comment records.

### Decision C — sports: retire vs leave frozen — **NOT DECIDED**

| Option | What it buys | Risk |
|---|---|---|
| **C1. Retire with explicit notice** — add a visible "Sports betting monitoring retired as of <date>; figures below are historical" banner on `sports-betting.html`, and commit the `.yml.disabled` rename so the tree records the intent | Readers stop mistaking frozen numbers for live ones; the tree finally reflects reality. | Cost is a UI edit + a rename. If the pause is temporary, you are now announcing a retirement you intend to reverse — keep the banner date-stamped so un-retiring is a one-line revert. |
| **C2. Leave frozen** | Zero work; trivially reversible. | The page keeps presenting month-old ROI as current. Every downstream reader — human or scraper — is misled with no signal. Reversibility is the only thing in its favour. |
| **C3. Re-enable** | Data flows again. | Explicitly out of scope for this report pass (no workflow edits). Noting only so the set is complete: re-enabling `sports-betting-refresh` also re-arms the paper **auto-place** path, whose policy (`sports_bets.php auto_place: deny fliff/betanysports`) has had no live exercise while it sat off. Any re-enable should be a separate, deliberate decision with the auto-place policy re-read first. |

---

## Items I explicitly am not claiming

- **Runtime state of the 5 sports workflows** — UNVERIFIED. Git shows crons present; the claimed `disabled_manually` is a GitHub-side flag I cannot read without the API.
- **Whether the sports page currently renders stale data** — UNVERIFIED. Depends on live FTP-deployed files and DB rows, neither of which is in git. The *mechanism* is verified from source; the *current symptom* is not.
- **Any `deploy-competition.yml` interval** — retracted by `@triage-expert` in #91 (no such file on main; two path-triggered lookalikes exist, no cron). Nothing here depends on that number.
- **The 176-day vs ~43-day reconciliation** — both numbers are verified from git, and they measure different things (workflow idleness vs file commit age). Neither is a live DB reading.

---

*Report pass only. No workflow edits, no API, no browser, no CDP. Coordinator commits this folder.*
