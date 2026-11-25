# Dead Deploy Script Scan — 2026-11-25

**Scope:** every `*deploy*` script in the repo (`.py` / `.sh` / `.mjs` / `.js` / `.ps1` / `.php`),
max depth 3, excluding `node_modules`, `.git`, `.venv`, `.kilo`, `.worktrees`.

**Method:** for each script, counted callers in three independent layers — GitHub
workflow references (`.github/workflows/`), markdown/doc references, and code
references (excluding self). A script was only called **dead** if it had no caller
*and* independent proof it cannot run (missing source files) or a live replacement
was verified to do the same job.

**Result:** 38 scripts scanned → 8 live, 1 live-via-script, 4 provably broken,
2 test files, 23 orphaned/superseded.

---

## 1. Live — called by workflows (8)

| Script | Workflow callers |
|---|---|
| `tools/deploy_audit_files.py` | **7** — canonical dashboard/updates deployer |
| `tools/deploy_to_ftp.py` | 2 |
| `tools/ftp_deploy_picks_now.py` | 2 |
| `tools/deploy_sports_files.sh` | 1 |
| `tools/deploy_gha_summary.py` | 1 |
| `tools/deploy_riseoftheclaw.py` | 1 |
| `KIMI_FEB172026/deploy_underdog_strategies.py` | 1 |
| `signal_aggregator/deploy_vetted_picks.py` | 1 |

Plus `scripts/alpha_engine_deployer.py` — imported by `scripts/run_all.py:252`
(`from alpha_engine_deployer import main as deploy_main`). Live via script caller.

**`tools/deploy_audit_files.py` is the canonical tool** — 7 workflow callers and a
`--only <tag>` selector (`tools/deploy_audit_files.py:306`) covering
`incidents/pick_funnel/model/ai_tournament/updates`.

---

## 2. Provably broken — references local files that no longer exist (4)

These crash on `open()` before any network call. Evidence: extracted every
quoted local path from the script and tested `os.path.exists`.

| Script | Missing source files |
|---|---|
| `tools/deploy_to_altsite.py` | **25** — incl. `index.html`, `api/get-movies.php`, `api/login.php`, `fresh_server_check.html` |
| `tools/deploy_movieshows3.py` | **15** — incl. `api/db_connect.php`, `api/get-movies.php`, `index.html` |
| `tools/deploy_movieshows2.py` | **7** — incl. `admin.html`, `fetch_new_content.php` |
| `tools/gen_deploy_html.py` | 1 — `index.html` |

`tools/deploy_to_altsite.py:399-400` is the proof it actually opens them:

```python
with open(local_path, "rb") as f:
    ftp.storbinary(f"STOR {remote_file}", f)
```

Spot-verified absent at repo root: `admin_add_single.php`, `api/get-movies.php`,
`index.html`, `fresh_server_check.html` — all `ABSENT`.

---

## 3. Orphaned / superseded (23)

No workflow, no code caller. Many are cited only by session transcripts
(`session-ses_*.md`) or one-off reports — those are **not** callers.

### 3a. Superseded by a verified live replacement

| Script | Superseded by | Proof |
|---|---|---|
| `deploy_goldmine_maintenance.py` | `torontoevent-deploy-live-monitor.yml`, `torontoevent-goldmine-tracker.yml`, `goldmine-tracker.yml` | 3 live workflows own `goldmine_maintenance.php` (`torontoevent-deploy-live-monitor.yml:3`) |
| `deploy_all_godaddy.py`, `deploy_ftps.py`, `deploy_simple.py`, `deploy_meme_fixes.ps1` | `meme-scanner-v2.yml` | **4-way duplicate.** All four deploy the identical 3 files; `meme-scanner-v2.yml:63` does `put findcryptopairs/api/meme_scanner_fixed.php` |
| `deploy_updates_page.py`, `tools/deploy_updates_v05.py` | `tools/deploy_audit_files.py --only updates` | flag exists at `deploy_audit_files.py:306` |

The meme cluster is the clearest case: four scripts, one identical job, all
orphaned, while a workflow does it properly.

### 3b. Orphaned with no replacement (no caller, no live equivalent)

`ab_testing_agent/deployment_manager.py`, `alpha_engine/deploy_phase7_picks.py`,
`deploy/dna_updates_ftp_deploy.py`, `deploy_godaddy.py`,
`deploy_high_performance_bundles.py`, `deploy_immediate_recommendations.py`,
`deploy_kimis_claw_production.py`, `KIMI_FEB172026/deploy_remote.py`,
`KIMI_RISEOFTHECLAW/deploy_dashboard_new.py`,
`scripts/deploy_testing_protocol_tables.py`, `tools/deploy_adsense_and_fix.py`,
`tools/deploy_adsense_to_altsite.py`, `tools/deploy_supplements.py`,
`tools/deploy_sync_instrumented.py`, `stabilization/validate_before_deploy.py`.

---

## 4. Credential hazard — `deploy_instrumented_audit.py`

Not merely dead. It logs into **two different accounts on two hosts** using the
**same environment variable**:

```python
  9:  ftp.login('ejaguiar1', os.getenv('FTP_PASS', ''))   # 50webs
 41:  ftp2.login('findtoro', os.getenv('FTP_PASS', ''))   # 162.210.101.36
```

Line 41 sends the **50webs password** to `162.210.101.36` for the `findtoro`
account. That host is the origin server named in
`updates/2026-11-25-phishing-kit-compromise.md` (the `easybank AT` phishing
compromise). The account name and `os.getenv('FTP_PASS')` pattern are also
documented in `.agent/workflows/deploy.md:124-126`.

Two consequences:
1. **Cross-tenant credential reuse** — one env var, two services, two identities.
   Any correct `FTP_PASS` value for one host is wrong (and needlessly transmitted)
   for the other.
2. It was already broken before the 2026-11-25 rotation and is **certainly** broken
   after it: `FTP_PASS` now holds the 50webs password, which cannot authenticate
   as `findtoro`.

It also deploys `/findtorontoevents.ca/audit_dashboard/index.html` directly, which
contradicts `CLAUDE.md` ("Edit `audit_dashboard/template.html`, NOT `index.html` —
index.html is auto-generated"; "Never run dashboard generators locally").

**Recommendation:** delete it, or split the credentials into separate env vars and
confirm the `findtoro` account still exists before reviving.

---

## 5. Verified negative — no hardcoded passwords

Checked all 38 scripts for literal credential assignments
(`pass(word)?|pwd|FTP_PASS` = `'...'`, 6+ chars, excluding `os.getenv`/`environ`/
`getpass`/format strings).

**Zero hardcoded password literals.** The two hits were false positives:
- `tools/deploy_sports_files.sh:136-137` — builds `.env` content from variables
- `deploy_updates_page.py:17` — `print("Set it with: $env:FTP_PASS='your_password'")`

**Correction to an earlier report.** `updates/2026-11-25-credential-rotation-audit-and-ci-state.md`
line 15 lists `deploy_updates_page.py | FTP_PASS (13 chars)` under a "File | Exposed"
table. The script does **not** contain a hardcoded password — it reads only
`os.getenv('FTP_PASS')` (`deploy_updates_page.py:13`). That row should be read as
"consumes FTP_PASS from env", not "contains a hardcoded secret". Flagging so nobody
greps for a literal that isn't there.

---

## 6. Methodological caveats

- **First-pass greps over-called 5 scripts dead.** A basename grep for
  `alpha_engine_deployer.py` returned zero hits, but `scripts/run_all.py:252`
  references the *module* name without the extension. Re-running with stem-based
  matching saved 1 live script from being wrongly deleted. `validate_before_deploy`,
  `deploy_all_godaddy`, `deploy_ftps`, `deploy_immediate_recommendations`,
  `deploy_simple` are cited only by a `WIRED_IN/*/00_inventory.csv`
  (`file_path,language,...` — a harvested listing, not a caller), so they remain
  orphans, but the distinction is why a bare grep count is not sufficient.
- **Absence of a caller is not by itself proof of death.** Only 4 scripts have
  positive evidence of un-runnability (missing sources). The rest are
  "unreferenced", which is a weaker claim.
- **`--dry-run` style checks were not used** as evidence; they don't exercise the
  code path.

---

## 7. Suggested next steps

1. Delete the 4 provably-broken scripts (§2) — they cannot work.
2. Delete `deploy_instrumented_audit.py` or split its credentials (§4).
3. Collapse the 4-script meme cluster to nothing (§3a) — `meme-scanner-v2.yml` covers it.
4. Point any human runbook that still says `deploy_updates_page.py` at
   `tools/deploy_audit_files.py --only updates`.
5. Leave §3b alone until someone confirms each is genuinely unwanted — unreferenced
   one-off fix scripts are cheap to keep and expensive to regret deleting.

---

# Appendix A — Reverse direction: workflows calling scripts that don't exist

Sections 1–7 audit **script → caller** (orphans). This appendix audits the inverse,
**caller → script**, because a workflow whose target is missing is strictly worse
than an orphaned script: nothing breaks loudly, so it fails silently and
indefinitely.

Verified against BOTH this worktree and `origin/main`, because "absent here" and
"absent from main" are different claims.

| # | Workflow | Referenced target | On origin/main? | Failure mode |
|---|---|---|---|---|
| 1 | `ai-tournament-pipeline.yml:194` | `tools/ai_tournament/generate_diagnostics.py` | **NO** | `\|\| echo "::warning"` → run stays **green**, output never regenerated |
| 2 | `cost-model-reconciliation.yml:45` | `tools/cost_model_reconciliation.py` | **NO** | deliberate stub — python line **commented out** |
| 3 | `hypothesis-registry-append-guard.yml:41` | `tools/hypothesis_registry_guard.py` | **NO** | deliberate stub — commented out |
| 4 | `premia-pod-forward-clock.yml:57` | `tools/premia_forward_clock.py` | **NO** | deliberate stub — commented out |
| 5 | `sports-betting-refresh.yml:684` | `tools/update_custom_sports_picks.py` | **NO** | `if [ -f ]` else-skip → **silent**, exits 0 |
| — | `forward-test-new-strategies.yml`, `audit3-health.yml` | `tools/strategy_freeze_gate.py` | **YES** | **FALSE POSITIVE** — worktree drift only, not a real break |

## A.1 `ai-tournament-pipeline.yml:194` — wrong filename, not a missing script

This one is **not** a missing script. The intended script exists under a different
name:

- Workflow calls: `python tools/ai_tournament/generate_diagnostics.py`
- Actually on main: `tools/ai_tournament/build_model_diagnostics.py`

`build_model_diagnostics.py` (on `origin/main`) writes exactly the file the workflow
then stages:

```
  20: OUT = REPO / "audit_dashboard" / "data" / "ai_tournament_model_diagnostics.json"
 136:     OUT.write_text(json.dumps(diagnostics, indent=2))
```

Its own docstring states the purpose:

> This powers the fleet-status panel on `/audit/ai-tournament.html` so the page can
> show the real tournament coverage gap: configured models, keys available on the
> runner, which models produced picks today, and which ones are blocked.

**Consequence — measured:** `audit_dashboard/data/ai_tournament_model_diagnostics.json`
is **11,639 B with mtime 2026-11-19**, last commit `7ab67511177`. It has been frozen
for 6 days. Line 295 then does `git add audit_dashboard/data/ai_tournament_model_diagnostics.json || true`,
so every run **re-stages the stale file** — the pipeline keeps recommitting 6-day-old
data and reports success.

Net effect: the fleet-status panel on `/audit/ai-tournament.html` has been presenting
stale diagnostics as live, while CI showed green the whole time. This is a Goal #1
(`/audit` performance) data-integrity defect, not cosmetic.

**Fix is one line** — point line 194 at `build_model_diagnostics.py`. Also remove the
`|| true` on line 295 (or the `|| echo "::warning"` on 194) so the next
disappearance fails loudly instead of hiding for 6 days.

## A.2 `sports-betting-refresh.yml` — double-blind: skip AND swallowed failure

The step is guarded so the missing script is skipped, and the skip reports success:

```yaml
      - name: Update custom sports picks (UFC/Tennis/Golf)
        id: custom_update
        continue-on-error: true
        run: |
          if [ -f tools/update_custom_sports_picks.py ]; then
            python3 tools/update_custom_sports_picks.py
          else
            echo "tools/update_custom_sports_picks.py not present — skipping"
          fi
      - name: Surface silent scraper failure
        if: steps.custom_update.outcome == 'failure'
```

Three independent reasons this can never surface:

1. The `else` branch `echo`s and **exits 0** → `steps.custom_update.outcome == 'success'`.
2. The "Surface silent scraper failure" step fires on `outcome == 'failure'` — which
   the guard above makes unreachable. **The safety net cannot trigger.**
3. `continue-on-error: true` means even a genuine traceback would not redden the job.

**Measured:** `tools/update_custom_sports_picks.py` is absent from main, and
`find . -name '*sports_custom_picks*'` returns **nothing** — the expected output file
has never been produced. The UFC/Tennis/Golf refresh path is entirely non-functional
and has been reporting success.

## A.3 The three stub workflows are intentional — do not "fix" them

`cost-model-reconciliation.yml`, `hypothesis-registry-append-guard.yml` and
`premia-pod-forward-clock.yml` each print a "not yet implemented (Phase N)" message
and have the `python` invocation **commented out**. These are honest placeholders,
not defects. Their value is that the `echo` names what is missing:

- cost-model reconciliation (Phase 5) — not running
- **hypothesis-registry append-guard (Phase 0) — the M-107 pre-registration rule is
  NOT machine-enforced**; the guard is a placeholder, so nothing stops a backtest
  being published without pre-registration
- premia pod forward clock (Phase 3) — not running

A green run on any of these three proves nothing. Do not read green CI as evidence
that cost reconciliation or the append guard are working.

## A.4 Correction to the `mentions/all` headline

The retained headline on `mentions/all` (1110 B, `[dead-deploy-scripts 2026-11-25]`)
lists all six of these together as "6 workflow-referenced scripts missing on
origin/main". Two corrections, from the table above:

- `tools/strategy_freeze_gate.py` is **present on origin/main** — it is missing only
  from this worktree. It is a worktree-drift artefact, **not** a broken workflow
  reference. It should not be in the list.
- The three "echo-only stubs" are correct as descriptions but are **deliberate**,
  and lumping them with the two genuine failures obscures the priority. The two that
  matter are `ai-tournament-pipeline` (stale as of 2026-11-19) and
  `sports-betting-refresh` (never produced output).

Corrected count: **5 refs to non-existent scripts — 3 deliberate stubs, 2 genuine
silent failures, 1 false positive.**

## A.5 Why this class matters more than orphaned scripts

An orphaned deploy script costs nothing: nobody runs it, nothing breaks. A workflow
pointing at a missing script costs **trust** — it produces green CI and stale
artefacts simultaneously. Both findings in A.1 and A.2 were invisible from CI status;
they surfaced only by comparing workflow targets against `git cat-file -e origin/main:<path>`.

**Recommended check to run in CI:** for every `python <path>` in every workflow step,
assert the path exists on the default branch. That single guard would have caught both.
