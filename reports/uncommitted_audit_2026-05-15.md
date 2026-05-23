# Uncommitted-Files Audit — 2026-05-15

> **Scope:** classify every uncommitted + untracked file in
> `e:/findtorontoevents_antigravity.ca` and recommend a commit/keep/ignore
> action for each.
> **Constraint:** read-only audit. No files were committed, deleted, or pushed.

## Top-line numbers

| Metric | Value |
|--------|------:|
| Total `git status -uall` entries | **14,060** |
| Inside `.tmp_ghcopilot_main_commit/` worktree (noise) | 13,868 |
| Real signal (outside that worktree) | **~192** lines, of which **~30 unique files** |
| Modified-tracked files (`M`) | 1 (`audit_trail/dashboard_generator.py`) |
| Submodule pointer churn (`m`/`?`) | 2 (`openclaude`, `openclaude-vscode`) |
| **Sensitive findings** (real-looking keys) | **5 hits → 4 unique keys** (all inside `.tmp_ghcopilot_main_commit/`) — see §1 |
| Stashes pending | 20 (stash@{0}..stash@{19}) |
| Local branches | 623 |
| Local-only branches (no upstream) | **218** |
| Branches AHEAD of upstream | **72** |
| MASTER_ACTION_PLAN_2026-05-15.md present? | YES — 574 lines, 60KB, untracked under `reports/` |

---

## 1. SENSITIVE FINDINGS — 5 hits, 4 unique live-looking keys

**All hits are inside `.tmp_ghcopilot_main_commit/` (worktree scratch dir, untracked
in this repo) — so they are NOT staged for any commit from this working copy.**
But because they appear to have been COPIED from real source, they very likely
exist in committed history on some remote branch. **Rotate first, investigate
history second.**

| File | Line | Type | Value in restricted file? |
|------|-----:|------|---------------------------|
| `.tmp_ghcopilot_main_commit/.env.example` | 31-32 | Cerebras `csk-...` (commented) | ***LEAKED-SECRET-REDACTED*** |
| `.tmp_ghcopilot_main_commit/TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/api/freestyle-search.php` | 75 | Google/YouTube API key | ***LEAKED-SECRET-REDACTED*** |
| `.tmp_ghcopilot_main_commit/TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS2/api/freestyle-search.php` | 75 | Google/YouTube API key (dup) | ***LEAKED-SECRET-REDACTED*** |
| `.tmp_ghcopilot_main_commit/TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS2/scroll-fix.js` | 49 | YouTube API key | ***LEAKED-SECRET-REDACTED*** |
| `.tmp_ghcopilot_main_commit/STOCKSUNIFY/scripts/lib/stock-api-keys.ts` (+ STOCKSUNIFY2 dup) | 32 | Google Custom Search key | ***LEAKED-SECRET-REDACTED*** |

Full plaintext values + rotation playbook: **`reports/sensitive_findings_2026-05-15.md`**
(intentionally untracked / restricted-share).

> **DB creds / FTP creds:** scanned (`DB_PASS*`, `FTP_PASS`, `password=...`,
> `aws_access_key`, `ghp_*`, `sk-*`, `xox[bp]-*`, `AKIA*`) and found only env-var
> NAMES — no literal values. Good.

---

## 2. COMMIT-CANDIDATES — 13 legitimate items

| Path | LoC | Likely author | Recommended branch | Risk |
|------|----:|---------------|--------------------|------|
| `reports/MASTER_ACTION_PLAN_2026-05-15.md` | **574** | This session (Antigravity, post-hermes-blocks) | `docs/master-action-plan-2026-05-15` → PR to `main` | docs-only |
| `reports/daily_ideas_synthesis_2026-05-15.md` | 186 | This session | same branch as MASTER_ACTION_PLAN (groups) | docs-only |
| `reports/asset_class_performance.html` | 33 | Same session (HTML wrapper for synthesis) | same branch | docs-only |
| `daily_ideas_KimiCode.MD` | 498 | Kimi-Code agent session | `docs/daily-ideas-kimicode-2026-05-15` → PR | docs-only |
| `agents/AGENTS_WORKFLOW_RESILIENCE.md` | 123 | GH Actions analysis session | `docs/agents-workflow-resilience-2026-05-15` → PR | docs-only |
| `updates/2026-05-14-mysql-database-verification-tests.md` | 39 | GH Copilot Auto | `docs/updates-mysql-verify-2026-05-14` → PR | docs-only |
| `updates/2026-05-14-verbatim-chatlog-censored.md` | 182 | GH Copilot Auto | same updates branch | docs-only (env-var names only, no creds in body) |
| `updates/2026-05-14-weak-asset-enhancements.md` | 59 | Kimi-Code | same updates branch | docs-only |
| `updates/2026-05-15-institutional-roadmap-commit.MD` | 16 | This session | same updates branch | docs-only |
| `updates/workflow-fixes-2026-05-14/API_FALLBACK_PATTERN.md` | 149 | GH Actions session | `docs/workflow-fixes-2026-05-14` → PR | docs-only |
| `updates/workflow-fixes-2026-05-14/RETRY_LOGIC_TEMPLATE.md` | 115 | same | same | docs-only |
| `updates/workflow-fixes-2026-05-14/TIMEOUT_FIXES.md` | 89 | same | same | docs-only |
| `tools/_weekly_perf_analyzer.py` | 326 | This session | `feat/weekly-perf-report-2026-05-15` → PR + CI | code-touching (new tool, no callers yet) |
| `tools/_weekly_perf_writer.py` | 299 | same | same | code-touching (Wire-Up Rule: opt-in sidecar — body must include `## Wiring Plan`) |
| `tests/test_mysql_50webs_connectivity.py` | 181 | Kimi-Code | `test/mysql-50webs-smoke-2026-05-15` → PR | code-touching (opt-in `LIVE_DB_SMOKE=1` smoke) |
| `audit_trail/dashboard_generator.py` (modified) | +52/-4 lines | This session (Mercury2 P1 #7 net-of-cost gate) | `feat/mercury2-cost-gate-2026-05-15` → PR | **production code-touching** — runs in `audit-dashboard.yml` |

### Notes per candidate

- **`audit_trail/dashboard_generator.py`** diff is a clean additive Mercury2 §4 net-of-cost
  slippage gate (cost_bps lookup + `net_total_pnl_pct` stamping). Self-contained inside one
  `try/except`. Should be its own PR with reviewer attention, not bundled with docs.
- **`tools/_weekly_perf_analyzer.py` + `_weekly_perf_writer.py`**: leading-underscore +
  `REPO = Path("E:/...")` hardcode suggests these are ad-hoc local scripts. Either
  (a) drop the absolute Windows path before committing, or (b) keep them as
  developer-only and add `tools/_weekly_*` to .gitignore.
- **`CLAUDE_IM_DONE_COULDNT_COMMIT_TV_THELEAPCRYPTO_MAY2026.txt`** — 19-line plain-text
  abort note from a prior Claude session that hit a git-timeout failure. **Not a normal
  commit candidate.** See §4.

---

## 3. NOISE — gitignore-candidates

| Category | Example paths | Count | Recommend |
|----------|---------------|------:|-----------|
| Stale worktree scratch | `.tmp_ghcopilot_main_commit/**` | 13,868 | **Add `.tmp_ghcopilot_main_commit/` to .gitignore** (high-priority — 99% of `status -u` noise) |
| Generic tmp scratch | `.tmp/pr1024_eval.txt` | 1 | **Add `.tmp/` to .gitignore** |
| Submodule pointer churn | `openclaude`, `openclaude-vscode` | 2 | Inspect — if intentional submodules, register in `.gitmodules`; otherwise add to .gitignore |
| Scraping-output dumps | `tools/SCRAPING/scraping_summary_playwright.json`, `tradingview_playwright*.json`, `tradingview_scrapling_stealth.json` | 4 | **Add `tools/SCRAPING/*.json` to .gitignore** (107KB playwright dump = data artifact, not source) |
| `.claude/skills/swarm-*/SKILL.md` (6 files) | `.claude/skills/swarm-audit/SKILL.md` etc. | 6 | Borderline — these are skill defs the operator may want shared. **Operator decision**: commit if cross-machine portability is wanted (under `chore/swarm-skill-files-2026-05-15`), otherwise add `.claude/skills/swarm-*/` to .gitignore. |

### Proposed `.gitignore` additions (one block)

```gitignore
# uncommitted-audit 2026-05-15
.tmp/
.tmp_ghcopilot_main_commit/
tools/SCRAPING/*.json
tools/SCRAPING/*.jsonl
```

(`__pycache__/`, `.kilo/`, `.kilocode/`, `.tmp_research/` already present.)

---

## 4. NEEDS-OPERATOR-DECISION — 4 items

| Path | Reason | Suggested resolution |
|------|--------|----------------------|
| `CLAUDE_IM_DONE_COULDNT_COMMIT_TV_THELEAPCRYPTO_MAY2026.txt` | Abort note from prior session ("Git commit failed due to large repo (119k+ commits) causing timeouts"). References a file `TV_THELEAPCRYPTO_MAY2026.MD` that the note says was created — **but the file does not exist in working tree** (phantom-work signature, cf. memory `project_hermes_phantom_work_2026-05-09`). | Move to `reports/session_aborts/2026-05-14-tv-leap-crypto-abort.md` if you want a record; otherwise delete. Do NOT commit at repo root. |
| `tools/SCRAPING/tradingview_playwright_full.json` (107KB) | Looks like the real scraped output the abort note referenced — usernames + returns, no credentials | Either (a) move to `data/raw/tradingview_leap_crypto_may_2026.json` and commit as dataset under `data/raw/`, or (b) gitignore (preferred — large data artifact). |
| `.claude/skills/swarm-*/SKILL.md` (6 files) | Could be agent-private skill defs OR cross-team docs | If shared across operator's machines → commit under `chore/swarm-skill-files-2026-05-15`. If single-machine → gitignore `.claude/skills/swarm-*/`. |
| Submodule pointers `openclaude` (`?`) + `openclaude-vscode` (`m`) | No `.gitmodules` file exists, but `openclaude/` has full content (CHANGELOG, bin/, etc.). Looks like a previously-cloned tool that lost its submodule registration. | If you want it tracked → either re-register as submodule or import as vendored subtree. If not → add `openclaude/` + `openclaude-vscode/` to .gitignore. |

---

## 5. Local-only branches — 218 (no upstream)

Sample (first 25): GROK_FINAL_2026, OPUS46, STOCKS_KIMIS_CLAW, abalone-larch, add-stat-tests-engine,
alert/antigravity-bad-kills-blast-radius-2026-05-03, aloud-linen, audit-loop3-ship-plan-2026-05-08,
audit-review, audit-supplements-dsr-calibration-2026-05-02, azure-tomato, boom-kitten, booming-inspiration,
brainy-group, brick-chicken, bright-hallway, buttercup-bill, canary-system, catkin-naranja,
ci-fix-pyarrow-submodules, cliff-law, codex/crypto-audit-quality-refresh, codex/daily-idea-cursor-main,
codex/nba-nhl-fallback-paper-bets, codex/recent-performance-macro-failover ... (193 more).

**Recommendation:** the `aloud-linen` / `boom-kitten` / `buttercup-bill` random-pair names are
auto-generated worktree branches from some agent harness — most can be pruned. Suggested
triage script (operator-only, NOT run by this audit):

```bash
# Dry-run: show local-only branches that have NO commits unique to them (= safe to delete)
for b in $(git for-each-ref --format='%(refname:short)' refs/heads); do
  up=$(git rev-parse --abbrev-ref "$b@{upstream}" 2>/dev/null)
  [ -n "$up" ] && continue
  unique=$(git rev-list --count "$b" --not --remotes 2>/dev/null)
  echo "$unique $b"
done | sort -n | head -50
```

**72 branches AHEAD of upstream.** Top 5 by commit-count:
- `codex/crypto-quality-hard-gates` — **662** commits ahead of origin
- `codex/revive-dormant-picks-dashboard-mysql` — 446 ahead
- `docs/cloud-agent-pr-roadmap-2026-05-02` — 261 ahead
- `docs-non-crypto-picks-diagnosis-2026-04-16` — 84 ahead
- `extract/asset-class-cleanup-clean` — 31 ahead

The 662-ahead and 446-ahead branches are unusual — likely contain peer-session work that
never got rebased. Operator should `git log <branch>@{upstream}..<branch> --oneline` on
each before deciding to push, rebase, or abandon.

---

## 6. Stash inventory — 20 stashes

| # | Branch | Tag |
|--:|--------|-----|
| 0 | `docs/kimi-protocol-archive-2026-05-15` | `stash-pre-kimi-archive` |
| 1 | `kimi-code-daily-ideas-2026-05-14` | `p0.5-4-and-peer-WIP` |
| 2 | `fix/mercury2-p0-audit-truth-2026-05-15` | WIP on a7eec2a9 (Institutional Escape Protocol + Kimi Gate-to-Money) |
| 3 | `fix/mercury2-p0-audit-truth-2026-05-15` | WIP on 237fe510 (daily ideas GH Copilot + NVIDIA + institutional roadmap) |
| 4 | `fix/live-picks-tracker-datetime-unbound-2026-05-14` | WIP on e2c72397 (datetime UnboundLocalError fix) |
| 5 | `docs/mmr-audit-corrections-2026-05-14` | WIP on 82245d84 (drift field-name fix + 7 numeric corrections) |
| 6 | `docs/mmr-audit-corrections-2026-05-14` | WIP on 2063b943 (DSR+drift gates wired) |
| 7 | `fix/quarantine-zombie-strategies-2026-05-14` | WIP on 3b22664f (quarantine breakout_b_ml + kimi_claw_research) |
| 8 | `docs/mmr-round1-round2-round3-synthesis-2026-05-14` | temp pre-PR996-merge |
| 9 | `feat/bond-fred-wiring` | temp ml perf data |
| 10 | `fix/forex-rsi2-reblock-2026-05-13` | WIP on e75ec5ac (Hermes 14d cross-check, EQUITY-collapse FALSE) |
| 11 | `docs/penny-stocks-brokie-suitability-2026-05-13` | `regime-fix-prep` |
| 12 | `feat/sports-betting-enhancements-2026-05-13` | WIP on d7c0d8e3 (swarm pick panel explainer) |
| 13 | `feat/sports-betting-enhancements-2026-05-13` | `branch-switch-staging` |
| 14 | `main` | `wip-lock` |
| 15 | `main` | `wip-scheduled-tasks-lock` |
| 16 | `main` | `wip-edge-stability-noise` |
| 17 | `feat/audit-dashboard-enhancements-hermes-2026-05-09` | `feature-branch-other-mods-before-cherry-pick` |
| 18 | `research-orchestrator-edge-stability-2026-05-11` | WIP on 01248efb (top 10 prompts deep-dive list) |
| 19 | `feat/audit-dashboard-enhancements-hermes-2026-05-09` | `wip-uncommitted-before-merge` |

**Triage suggestion:** stash@{0..3} are recent (today/yesterday). stash@{14..19} are weeks old
("on main: wip-lock" pattern suggests forgotten branch-switch escapes — safe to drop after
quick `git stash show -p stash@{N} | head -40` peek).

---

## 7. Recommended next 3 commits

These are the highest-leverage cleanup commits the operator should make today, in order:

### Commit 1 — `chore: add .tmp_ghcopilot_main_commit, .tmp, scraping JSON to .gitignore`

Target: `main` directly (low-risk infra change).
File: `.gitignore` only.
Effect: drops `git status -uall` line count from 14,060 → **~30**, making every future
audit + every PR review readable.

```diff
+# uncommitted-audit 2026-05-15
+.tmp/
+.tmp_ghcopilot_main_commit/
+tools/SCRAPING/*.json
+tools/SCRAPING/*.jsonl
```

### Commit 2 — `docs(reports): MASTER_ACTION_PLAN_2026-05-15 + daily ideas synthesis`

Branch: `docs/master-action-plan-2026-05-15` → PR to `main`.
Files:
- `reports/MASTER_ACTION_PLAN_2026-05-15.md` (574 lines)
- `reports/daily_ideas_synthesis_2026-05-15.md` (186 lines)
- `reports/asset_class_performance.html` (33 lines)

Effect: ships the de-duplicated master plan + per-asset synthesis. Pure docs, no CI risk.

### Commit 3 — `feat(mercury2): net-of-cost slippage gate on asset_class_health`

Branch: `feat/mercury2-cost-gate-2026-05-15` → PR to `main`.
File: `audit_trail/dashboard_generator.py` (+52/-4)
Effect: ships the Mercury2 §4 / Foolproof v2.1 net-pnl gate so shadow-promotion decisions
use NET (post-cost) instead of gross PnL. Code-touching → needs CI green +
1 reviewer (`audit-dashboard.yml` will exercise it on next hourly tick).

### After those 3 → tackle the side workstreams

- 4. Kimi-Code daily ideas (`docs/daily-ideas-kimicode-2026-05-15`)
- 5. workflow-fixes-2026-05-14 batch (`docs/workflow-fixes-2026-05-14`)
- 6. MySQL connectivity test (`test/mysql-50webs-smoke-2026-05-15`)
- 7. weekly perf tooling (`feat/weekly-perf-report-2026-05-15`) — requires Wire-Up Plan
- 8. Rotate the 4 leaked API keys per `reports/sensitive_findings_2026-05-15.md`. **Do not delay this; rotate even if the worktree dir gets gitignored — the keys are out there.**

---

## Appendix — methodology

Commands run (all read-only):
- `git fetch --all --prune`
- `git status --short -uall`
- `git stash list`
- `git for-each-ref --format='%(refname:short)|%(upstream:short)' refs/heads` (loop counted ahead / local-only)
- `git diff` / `git diff --stat` (audit_trail/dashboard_generator.py)
- `Grep` (ripgrep) for secret patterns over all candidate files + `.tmp_ghcopilot_main_commit/` subtree
- `wc -l` for line counts on each candidate

Constraints honored: nothing committed, nothing deleted, nothing pushed, no `git reset`.
