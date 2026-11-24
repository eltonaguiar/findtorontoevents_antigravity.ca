# GHA Cross-Worktree Review & Prioritized Fix Plan

**Worktree:** `ghactions-v4`
**Timestamp:** 2026-11-16_01-21_EST (2026-11-16_06-21 UTC)
**Reviewer:** Kilo (ghactions-v4 agent)
**Scope:** Review of ghactions, ghactions-v2, ghactions-v3, ghactions-v4 work; remaining actions; prioritized code fixes.

---

## 1. Worktree inventory

| Worktree | Branch | State | Own commits vs origin/main |
|----------|--------|-------|----------------------------|
| `ghactions` | `ghactions` | clean | 3 unlanded (VIX/ETF/forex) |
| `ghactions-v2` | `docs/alpha-verify-2-2026-11-16` | clean | 1 unlanded (VERIFICATION.md) |
| `ghactions-v3` | `fix/gha-cron-regime-hardening` | clean | 2 unlanded (regime-terminal + audit-impact + ueps hardening) |
| `ghactions-v4` | `fix/gha-disable-broken-workflows` | clean | 0 (all 11 commits pushed to main) |

**My commits on `origin/main` (verified):**
`3d1aa94ba5e` disable broken workflows · `2295c7b374c` path filters · `95614d65362` timeouts · `f085cde0177` concurrency · `4ca0ca135b4` docs · `7228654be2e` secret-scan disable · `63422bff4fe6` IC analysis · `793b0fd5d81d` BOND SKIP_FRED · `ed511749fd90` money-ready docs · `f85e947656ab` queue audit · `04a30246aef1` normalizer fix · `215ac5945fa` hourly cron hygiene batch.

---

## 2. Peer work review

### `ghactions` (unlanded, 3 commits) — SOUND, recommend landing
- `alpha_engine/config.py`: `FOREX_HARD_DISABLE` now read live from env (default OFF); added `ETF_BLOCKED_DIRECTIONS = {SHORT, SELL}` with ledger evidence (ETF SHORT n=75 WR 10.7% PF 0.09, inverted in both time halves).
- `alpha_engine/etf_scanner.py`: derives `direction`/`id`/`status` at scan time, not only at merge — fixes 12/15 signals saved with `direction=None`.
- `audit_trail/quality_gates.py`: `ETF_SHORT_CLASS_BLOCK` placed FIRST in the gate chain (a later placement was unreachable), kill-switch `ETF_SHORT_GATE_ENABLED=0`, fail-open; FOREX gate reads env live.
- Tests: `tests/test_etf_short_gate.py` (97 lines) + `tests/test_quality_gates.py` updates. **Wired and tested.**
- Minor: `import hashlib as _hl` inside a loop (works; should be module-level).
- **Action:** land via PR; no conflict with my changes (different files).

### `ghactions-v3` (unlanded, 2 commits) — SOUND, recommend landing
- Hardens commit/push steps in `regime-terminal.yml`, `audit-impact-tracker.yml`, `ueps-pick-runner.yml`:
  - `if: always()` + `timeout-minutes: 5` on commit steps
  - `assert_no_conflict_markers.sh` before commit
  - `git remote set-url` with `TOKEN_FOR_PUSH`
  - explicit `exit 1` on repeated push failure (no silent success)
- **No conflict** with my files. Land via PR.

### `ghactions-v2` (unlanded, 1 commit) — doc only
- Adds `VERIFICATION.md` noting ALPHA recheck (no post-#829 run; cron widened to 2h). Informational.

### Conflicts / duplication
- **None found.** v3 touches `regime-terminal`/`audit-impact-tracker`/`ueps-pick-runner`; ghactions touches `config.py`/`etf_scanner.py`/`quality_gates.py`/`dashboard_freshness.js`; I touched workflow YAML + `tools/` + `updates/` + `reports/`. Disjoint.

---

## 3. My work — self-review

**Landed and verified:**
- 3 broken workflows disabled (`ml-gatekeeper-ab-bootstrap`, `mysql-q001-sync`, `secret-scan`) — eliminates spurious per-push failures.
- Path filters on 3 push-only workflows; timeouts on 7; concurrency on 9; +20 hourly cron batch today.
- IC analysis restored (`build_ic_analysis.py` + generated JSON + workflow step).
- BOND `SKIP_FRED` un-hardcoded (repo var default `0`).
- Phase 3 queue/duration audit (`tools/gha_queue_audit.py` + `gha-queue-audit.yml`), live-verified registered.
- 3 dashboard escalation docs + best-practices doc.

**Verified clean:** 0 push-no-path-filter remaining; no workflow file >400 KB; all 20 new YAML edits parse.

**Known limitation:** the Actions-list page (CDP) lacks `updatedAt`, so duration stats only populate from the REST API (the workflow path). Documented in the script.

---

## 4. Further actions required (repo-wide scan 2026-11-16)

| # | Action | Count | Priority |
|---|--------|-------|----------|
| A | Concurrency group still missing | 181 workflows | HIGH |
| B | `timeout-minutes` still missing | 73 workflows | HIGH |
| C | `academic-strategies-daily.yml` timeout 25 min too tight (cancelled runs) | 1 | HIGH |
| D | Land peer PRs (ghactions VIX/ETF, ghactions-v3 hardening) | 2 | HIGH |
| E | 51 phantom queued runs | 51 | MEDIUM (needs GitHub Support / classic PAT) |
| F | QA Market Validation 5 API secrets | 5 | MEDIUM (needs GitHub UI / PR #786) |
| G | Reusable `gha-scan-job.yml` (dedupe checkout/setup/push) | 1 | MEDIUM (needs canary) |
| H | BOND still n=1; verify picks resume after SKIP_FRED fix | 1 | MEDIUM |
| I | Money Ready 0/9 — per-class emitter mutate/kill | 9 | MEDIUM (research) |

---

## 5. Prioritized code fixes — APPLIED this session

**Batch: 20 high-frequency hourly cron workflows** (commit `215ac5945fa`)
Added `concurrency: {group: ${{ github.workflow }}-${{ github.ref }}, cancel-in-progress: true}` + per-job `timeout-minutes`:
`analyst-tracker`, `asterdex-paper-trading`, `breakout-arena`, `claude-gainer-ml-live`, `coinglass-scanner`, `crypto-ml-tracker`, `deploy-battleground-ftp`, `discord_status`, `forward-tracking-v2`, `hourly-master-picks`, `hub-sync`, `live-monitor-refresh`, `live_tracker`, `master-automation-scheduler`, `obi-snapshot`, `qa-market-validation`, `recommended-portfolio`, `send-accountability-reminders`, `signal-quality-monitor`, `torontoevent-rapid-validation`.
All 20 validated as parseable YAML; diff is additive only.

**Remaining prioritized fix order (next batches):**
1. Apply the same hygiene script to the next ~33 high-frequency cron workflows (every-2h/4h tier) — script at `/tmp/kilo/add_hygiene.py` (recreate in repo if wanted).
2. `academic-strategies-daily.yml`: raise timeout 25 → 45.
3. Add concurrency to the 53 high-freq cron workflows still missing it (list in §4).
4. Land peer PRs.

---

## 6. Where files were put

| File | Location |
|------|----------|
| This summary | `GHACTIONS_2026-11-16/2026-11-16_01-21_EST_ghactions-v4/SUMMARY.md` |
| Queue audit script | `tools/gha_queue_audit.py` |
| Queue audit workflow | `.github/workflows/gha-queue-audit.yml` |
| Best-practices doc | `reports/gha_best_practices_findings.md` |
| Phase 1 inventory | `tools/gha_phase1_inventory.py` + `reports/gha_inventory_phase1.json` |
| Classification report | `reports/gha_phase1_classification_report.md` |
| Phase 3 recs | `reports/gha_phase3_recommendations.md` |
| Escalation docs | `updates/2026-11-16-gha-disable-broken-workflows.md`, `...-phantom-queued-runs.md`, `...-qa-market-validation-secrets.md`, `...-ic-analysis-missing.md`, `...-prediction-market-json-missing.md`, `...-stale-data-sources.md`, `...-money-ready-zero.md`, `...-strategy-kill-tribunal.md` |
| Triage prompt | `GHA_TRIAGE_AND_FIX_PROMPT.md` |
| Hygiene helper (session) | `/tmp/kilo/add_hygiene.py`, `/tmp/kilo/add_job_timeout.py` |

---

## 7. Verification

- `git status` clean; `HEAD == origin/main`.
- GHA live (Chrome CDP): 0 failures in latest 25 runs; only normal in-progress/queued.
- New `GHA queue & duration audit` workflow confirmed registered in the Actions workflows list.
