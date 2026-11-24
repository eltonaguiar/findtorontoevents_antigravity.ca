# IMPLEMENTATION_PLAN — GH Actions final fix plan (check-act-validate)

**STAMP: 2026-11-16_01-40_EST (06:40 UTC)** · supersedes the SUMMARY.md P0–P3 list as the
executing plan · fleet = 4 worktrees + external agents still landing commits.

## 0. PROTOCOL (applies to EVERY step — peers are concurrently editing the same repo)

1. **CHECK before touching:** `git fetch origin main` + `git log origin/main --since=<last touch> --
   <target files>` + re-`git show origin/main:<file>`. Two precedents tonight: my banner fix landed
   7 min before a peer extended it; the 06:21 peer batch pre-covered 20 cron workflows of my P2.
   If already fixed → mark DONE-BY-PEER, validate their change instead of re-doing it.
2. **ACT minimally:** one logical change per commit, asserts on every replacement, YAML/`node --check`/
   `py_compile` + targeted tests before landing; land via clean worktree + fetch/rebase/push retry loop
   (bot commits land every ~60s).
3. **VALIDATE by run (mandatory):**
   a. Queue-capacity check first (browser `python3 /tmp/kilo/gha_browser/scrape.py runs "is:in_progress"`).
   b. If the workflow is `workflow_dispatch`-able AND in_progress < ~10: dispatch ONE run
      (`gh api -X POST .../actions/workflows/<file>/dispatches -f ref=main`; if API quota dead →
      browser "Run workflow" via CDP 9222 — note: the browser session's write-CSRF was stale earlier,
      CLI dispatch proved reliable).
   c. Else wait for the natural scheduled run (record its due time).
   d. **Monitor to conclusion** via `wf-history <file>` + `run-detail <id>` (browser primary;
      `gh api .../runs/<id>/jobs` supplement). PASS = conclusion success AND no new ERROR annotations
      AND the fix's specific symptom absent. Record PASS/FAIL + run id in the item row below.
4. **Fallback monitoring:** if GitHub API is unavailable mid-monitor, poll via the logged-in Chrome
   scrape (`wf-history`, `run-detail`) only — never declare unverified success.

## 0.5 FLEET RECONCILIATION (post-validation checklist — 2 concurrent fleets!)

Fleet A (GHACTIONS): `ghactions` (us) · `ghactions-v2/-v3/-v4`. Fleet B (**auditpage**):
`auditpage` / `auditpage-v2/-v3/-v4` — the source of tonight's mystery /audit fixes (publish-boundary
strict-JSON `7c3cb289a14`, per-asset-class wording `9516cd850ce`, feed-health PM warnings `f107b7da3e5`).

**Post-validation rules (run AFTER every validation step):**
1. Before judging any render/behavior check, `git log origin/main --since=<fix landed> -- <the touched
   paths>` and attribute the deployed artifact's content to a commit — is the observed state MY fix,
   a fleet-B extension of it, or a regression? (Precedent: my IC-hide check "passed" because fleet B
   healed the data instead — the right outcome via a different path.)
2. Never re-fix what fleet B changed mid-flight. Live known overlap: **`auditpage` is actively
   rewriting the ghost-rows truth-layer** (uncommitted `template.html`, `dashboard_enhancements.js`,
   `index.html`, `tools/db_health_check.py` on `fix/audit-truth-layer-2026-11-16`) — my banner
   reword (07 fix #2) is superseded-in-flight; validation = "banner is honest (my reword OR their
   truth-layer)", not "my exact string appears".
3. Stranding watch: auditpage's 4 dirty files are UNCOMMITTED (lost-if-session-dies) — same class we
   rescued twice tonight. If they land within the window, fine; if not at next review, escalate to
   the owner (we do not commit other sessions' worktrees unprompted).
4. Keep both fleets' artifacts additive: my docs live in `GHACTIONS_2026-11-16/…`; fleet B commits
   fixes + tests directly. Cross-reference, never overwrite.

## 1. Execution items (ordered; status column updates as we go)

| # | Item | Target files (verify current before edit) | Fix sketch | Validation run | Status |
|---|---|---|---|---|---|
| P0-1 | pead-shadow-collector scheduled path fails 49/50 (22–25m bare exit 1) | `.github/workflows/pead-shadow-collector.yml`, `alpha_engine/strategies/pead_equity.py` loader | dig failure log first (run 43520036730); likely schedule-vs-dispatch env/secrets delta in `equity_earnings_loader` cache path; make the failing call loud | natural 22:11 run, or dispatch if queue <10 | RUNNING (log dig) |
| P0-2 | daily-prices-yf-refresh scheduled path fails 48/50 (42–52s exit 1) | `tools/refresh_daily_prices_yf.py`, `.github/workflows/daily-prices-yf-refresh.yml` | log dig first (run 43521235051); likely yfinance fetch — add retry + loud output | natural 22:49 run / dispatch | QUEUED |
| P0-3 | alpha-engine-live MySQL sync integrity errors on green | `.github/workflows/alpha-engine-live.yml` "Full MySQL sync (all sources)" step | make tolerated sub-exit loud-fail or `::error::` + status-file gate | next ~4h run / dispatch | QUEUED |
| P1-4 | audit-dashboard Hyro `enhanced_scoring` sub-step failure on green | `alpha_engine/hyrotrader_enhanced_scoring.py` + audit-dashboard Hyro step | root-cause + loud handling | next audit cycle (verify by run-detail annotations) | QUEUED |
| P1-5 | alpha-engine-fast ρ>1 (30m cron vs 25–47m serialized) | `.github/workflows/alpha-engine-fast.yml` cron line | widen `M/30`→`M/45` or `M * * 0-6` hourly — **OWNER CALL**, prepare diff only | n/a until owner | OWNER |
| P1-6 | claude-gainer ×2 green-no-op (no .joblib → skip scanner, green) | `claude-gainer-ml-live.yml`, `claude-gainer-tracker.yml` | emit status-file/`::error::`-grade signal so no-op can't look healthy | next runs (2×/day family) | QUEUED |
| P1-7 | **land ghactions-v3's 2 unmerged commits** (`60141976a83` regime push harden, `e6f3932991d` ueps/audit-impact harden) + its dirty file | its worktree | coordinate: v3 lands via its own PR (nudged), else cherry-pick both to a clean branch + PR | affected workflows' next runs | WAIT-V3 (fallback = us) |
| P2-8 | guardian v1.1 rule re-reads (R1/R3 timeout-awareness, R5 p90, R9 baselines) | `tools/gha_health_audit.py` + tests | per 08 §4 | guardian's 08:37 + 12:37 runs (compare CANCEL BUCKETS + rule output) | QUEUED |
| P2-9 | PM momentum agent produces nothing (behind now-loud warning) | `prediction_market_agents/polymarket_momentum_agent.py` + audit-dashboard step | root-cause `scan_momentum()` failure | next audit cycle + grep payload for `pm_momentum_signals` rows | QUEUED |
| P2-10 | residue sweep: `queue:group` on must-not-drop ticks · `permissions:` least-privilege · SHA-pin 7 3rd-party actions · daily-stock 404 report-cache writer | various (verify 06:21 peer batch first — it added concurrency+timeout to 20 crons) | 06 §4 + hygiene patterns | spot-check next runs per family | QUEUED |

## 2. Standing validation watchers (already armed)

- 08:00 monitor cron (broad + dup-guard + queue baselines) · 08:37 first scheduled guardian report
  (`GHACTIONS_LIVE/`, CANCEL BUCKETS live debut) · 4h cadence thereafter.
- Tonight's natural proof runs: pead 22:11 · daily-prices-yf 22:49 · verified-pilot 06:53 UTC.

## 3. Rules of engagement (re-confirmed)

- Owner decisions stay owner decisions (P1-5 + P3 list in SUMMARY.md).
- Revert map per change; `backup/gha-audit-2026-11-16` anchor; file-by-file staging (stale-checkout trap).
- Browser-first when API is thin (logged-in Chrome CDP 9222), `gh api` fine at low volume.
