# Action Plan A — ML Pipeline Reliability

**Date:** 2026-04-27
**Workstream:** A (ML Pipeline Reliability)
**Author:** Investigation by Claude Opus 4.7 (1M ctx)
**Scope:** Investigation + writeup only. No code changes. No PRs.
**Source artifacts read:** `reports/asset_class_independent_recompute_2026_04_27.md`,
`.github/workflows/alpha-engine-live.yml`, `.github/workflows/audit-dashboard.yml`,
`.github/workflows/enhanced-ml-crypto.yml`, `.github/workflows/ml-monthly-retrain.yml`,
`.github/workflows/ml-feedback-retrain.yml`, `alpha_engine/auto_tuner.py`,
`alpha_engine/ml_ranker.py`, `ml_gatekeeper/gatekeeper.py`, `ml_crypto_predictor/self_improvement.py`,
`model_health_agent.py`.

---

## 1. Methodology

1. Confirmed mtimes / file existence via `ls -la` on the four model artifacts called out in the canonical audit.
2. Read `auto_tuner.py:1-80, 622-1060` and the workflow step that invokes it (`alpha-engine-live.yml:587-592`).
3. Read `ml_gatekeeper/gatekeeper.py:1-80` and grepped `.github/workflows/*.yml` for `ml_gatekeeper` and `git add ml_gatekeeper`.
4. Read `ml_crypto_predictor/self_improvement.py` (full file, 24 lines) and listed `ml_crypto_predictor/results/` contents.
5. For each ML system with a `models/` directory, verified which workflow `git add`s it: `mercury2/models/`, `claude_gainer_ml/models/`, `ml_consensus/models/`, `ml_battleground/system_*/models/`, `ml_crypto_predictor/models/`, `ml_crypto_predictor/enhanced_models/models/`, `crypto_ml_edge/models/`, `crypto_signal_engine/data/models/`, `local_gpu_trainer/models/`, `rl_agent/models/`, `ml_gatekeeper/models/`, `HedgeFundData/models/`.
6. Counted `|| echo "<x> failed (non-fatal)"` occurrences across all workflow YAML.
7. `git log` per-file to confirm last actual commit-touching-file dates: `alpha_engine/data/rf_model.pkl`, `ml_gatekeeper/models/`, `ml_crypto_predictor/enhanced_models/models/AAVEUSDT_15m_A_xgboost.joblib`.
8. Read `model_health_agent.py` (1348 lines) end-to-end and grepped workflows for `model_health_agent`.

---

## 2. Per-Finding Investigation

### Finding 1 — `python -m auto_tuner` silently fails at `alpha-engine-live.yml:592`

**Root cause (compounded — two bugs stacking).** File is at `alpha_engine/auto_tuner.py`. Workflow step:

```yaml
# alpha-engine-live.yml:587-592
- name: Run Auto-Tuner (enforce strategy quality)
  if: steps.mode.outputs.mode == 'full-cycle' || steps.mode.outputs.mode == 'validate-only'
  env:
    PYTHONPATH: ${{ github.workspace }}
  run: python -m auto_tuner || echo "Auto-tuner run failed (non-fatal)"
```

`python -m auto_tuner` with `PYTHONPATH=<repo root>` looks for a top-level `auto_tuner.py` or `auto_tuner/__init__.py` — neither exists. The actual file is `alpha_engine/auto_tuner.py`. Verified: `find -maxdepth 3 -name "auto_tuner*"` returns only the alpha_engine file plus its `__pycache__`. So the step exits with `ModuleNotFoundError: No module named 'auto_tuner'` on every cron tick. The `|| echo "...non-fatal"` catches the non-zero exit, the workflow proceeds green, and `auto_tuner.py:1033 maybe_train_ml(db, state, ranker)` — which is the only path that calls `MLSignalRanker.train()` and writes `alpha_engine/data/rf_model.pkl` via `ml_ranker.py:1109` — never executes.

**Why nobody noticed for 12+ days.** Three failure modes compounded:
- The `|| echo` swallows the exit code, so the GitHub Actions step turns green.
- There is no CI assertion that `rf_model.pkl` mtime advanced after the run; the workflow `git add -f`s the file unconditionally (`alpha-engine-live.yml` later in the commit step), so the artifact appears in commits even when its bytes did not change.
- `git log -- alpha_engine/data/rf_model.pkl` shows zero commits modifying the file between 2026-04-15 and 2026-04-27 (verified with `git log --since="2026-04-15"`). No alert fires on "ML model age > 24h" because no such alert exists.

**Fix (two-part).**

```yaml
# alpha-engine-live.yml:587-592   AFTER
- name: Run Auto-Tuner (enforce strategy quality)
  if: steps.mode.outputs.mode == 'full-cycle' || steps.mode.outputs.mode == 'validate-only'
  env:
    PYTHONPATH: ${{ github.workspace }}
  run: |
    python -m alpha_engine.auto_tuner
    # Assert the trainer actually wrote a fresh model (mtime within last hour)
    python -c "
    import time, os, sys
    p = 'alpha_engine/data/rf_model.pkl'
    if not os.path.exists(p):
        print(f'::error::{p} missing after auto_tuner run'); sys.exit(1)
    age = time.time() - os.path.getmtime(p)
    if age > 3600:
        print(f'::error::{p} not refreshed (age={age:.0f}s)'); sys.exit(1)
    print(f'OK: rf_model.pkl refreshed {age:.0f}s ago')
    "
```

Two changes: `auto_tuner` -> `alpha_engine.auto_tuner` (correct module path), and remove the `|| echo` catch-all. The mtime assertion makes a future silent-failure surface as a red CI step.

**Test plan.** (a) Push the change to a branch, (b) `workflow_dispatch` with `mode=validate-only`, (c) confirm the step logs `OK: rf_model.pkl refreshed Ns ago` and the run succeeds; (d) `git log -1 -- alpha_engine/data/rf_model.pkl` shows a commit on the test run. As a negative test, temporarily rename the file and confirm the assertion fails the step.

**Blast radius.** Removing `|| echo` will turn this previously-silent step red. If `auto_tuner.py` itself has a latent bug that is unrelated to the module path (e.g. a missing dependency on the runner), the entire alpha-engine-live workflow could go red on first run. Mitigation: review `maybe_train_ml`'s dependency chain (`ml_ranker.MLSignalRanker.train`) on a branch first; only land after one clean test run. Also, the same workflow has 35 other `|| echo "non-fatal"` lines (Cross-cutting §1) — fixing this one in isolation does not destabilize them.

---

### Finding 2 — `ml_gatekeeper/models/` never persisted

**Root cause.** `audit-dashboard.yml:320-325` invokes `python ml_gatekeeper/gatekeeper.py`, which calls `joblib.dump(...)` into `ml_gatekeeper/models/` (path defined at `gatekeeper.py:29`, `MODEL_DIR = ROOT / "ml_gatekeeper" / "models"`). The workflow's "Commit updated data" step at `audit-dashboard.yml:531` enumerates a hardcoded file list of ~30 specific JSON / HTML paths to `git add`. **`ml_gatekeeper/models/` is not in that list.** Grep for `git add ml_gatekeeper` across all workflows: zero matches (verified). The trainer runs every cycle, writes to disk on the ephemeral GitHub runner, the runner is destroyed, the model never reaches origin. Internal `gatekeeper_model.joblib` mtime is 2026-04-15T14:06 because that is the last time a *human* committed it.

**Why nobody noticed.** No alert on artifact age. The dashboard's "ML Gatekeeper" status pill at `audit-dashboard.yml:431` only reflects whether the *step* succeeded (it always does — no exit code propagated), not whether the persisted model is fresh. A 12-day-old model still loads and still scores picks; the resulting scores are silently degraded but not visibly broken.

**Fix.** Add a stage step before commit and add a separate commit for binary artifacts.

```yaml
# audit-dashboard.yml: insert after line 325 (the gatekeeper step)
- name: Stage ml_gatekeeper artifacts for persistence
  if: always()
  run: |
    git add ml_gatekeeper/models/ ml_gatekeeper/data/ 2>/dev/null || true
```

Then in the commit step (line ~531) prepend `ml_gatekeeper/models/gatekeeper_model.joblib ml_gatekeeper/models/strategy_router.json ml_gatekeeper/models/training_report.json ml_gatekeeper/models/drift_baseline.json ml_gatekeeper/models/train_score_hist.npy` to the file loop, OR replace the loop `git add` with a directory-level `git add ml_gatekeeper/models/`.

**Test plan.** Branch the change, dispatch `audit-dashboard.yml`. Confirm a commit appears with `ml_gatekeeper/models/gatekeeper_model.joblib` in `git diff --name-only HEAD~1`. After 2 hours of cron runs on main, confirm `git log --since=...-- ml_gatekeeper/models/` returns multiple commits.

**Blast radius.** `gatekeeper_model.joblib` is 3.97 MB. Daily commit of a fresh binary will inflate repo size by ~50 MB/year if every cycle generates a different binary. Mitigation: the trainer should be deterministic given the same input data — most cycles will produce identical bytes and `git diff --staged --quiet` will skip the commit. If not, gate the commit on `git diff --stat` exceeding a threshold. Also: the existing audit-dashboard.yml stash-before-pull logic at line 570 may need updating to include the new staged paths.

---

### Finding 3 — `ml_crypto_predictor/self_improvement.py:9` reads non-existent `results/v4_training_summary.json`

**Root cause.** Two bugs — broken path AND broken import. Reading `ml_crypto_predictor/self_improvement.py` (24 lines, full):

```python
# line 4-5
from enhanced_models.v4_trainer import train_v4_full_suite
from enhanced_models.realistic_backtester import evaluate_model_performance
# line 9
with open('results/v4_training_summary.json', 'r') as f:
```

Two issues:

1. The import at line 4-5 uses `from enhanced_models.*` but the package name is `ml_crypto_predictor.enhanced_models.*`. This script will raise `ModuleNotFoundError` unless run from the `ml_crypto_predictor/` directory.
2. Line 9 opens `results/v4_training_summary.json` as a **relative** path. The directory `ml_crypto_predictor/results/` exists but contains: `last_scan_state.json`, `live_picks_1h.json`, `training_summary.json`, `v3_training_summary.json`, `v4_comprehensive_report.json`, `v4_proof_report.json` — note **no** `v4_training_summary.json` (verified). The closest match is `training_summary.json` (804 bytes) and `v4_comprehensive_report.json` (8.7 KB). The file the script names has never existed in this repo.

The script also does not appear in any workflow (`grep -r self_improvement.py .github/workflows/` returns nothing). It is dead code that would crash if ever invoked.

**Why nobody noticed.** Because no workflow runs it. It is a hand-written "fail-safe" added in the original v4 build that was never wired into a cron. The audit's "self-improvement loop" claim is false — there is no loop.

**Fix.** Two options, decision required:

- **Option A — Wire it up.** Decide what `v4_training_summary.json` should contain; have `enhanced_models/v4_trainer.py:train_v4_full_suite()` write it; fix imports to `from ml_crypto_predictor.enhanced_models.v4_trainer import ...`; resolve the relative path with `Path(__file__).parent / "results" / "v4_training_summary.json"`; add a workflow trigger.
- **Option B — Delete the script.** It is 24 lines of dead code referencing a missing summary file and a wrong module path. If nobody is going to wire it up, removing reduces audit surface.

Recommend Option B unless someone owns this loop. There is no evidence any workflow expected this artifact.

**Test plan (Option B).** Confirm `grep -r self_improvement` only finds the file itself plus this report. Delete and confirm CI tests pass.

**Blast radius.** Option B is zero-risk (dead code). Option A risks introducing a new scheduled retrainer that competes with the existing `ml-monthly-retrain.yml` cron (Finding 4 below) and potentially overwrites freshly-trained models with stale-seed runs.

---

### Finding 4 — `ml_crypto_predictor/enhanced_models/` production models 32+ days stale

**Root cause.** Two compounding issues:

1. The intended retrainer is `ml-monthly-retrain.yml` (cron `0 4 1 * *`, line 4) which calls `python -m ml_crypto_predictor.enhanced_models.main train` (line 39) and `git add ml_crypto_predictor/enhanced_models/models/` (line 64). That schedule fires once per month on the 1st at 04:00 UTC. The 12h `ml-feedback-retrain.yml` cron (`23 */12 * * *`) only updates `outcome_feedback_model.joblib`, not the per-pair / per-timeframe production models — confirmed at `ml-feedback-retrain.yml:97, 105`.

2. **No commit landed from the 2026-04-01 monthly retrain.** Verified: `git log --since="2026-04-01" --until="2026-04-02" --grep="Monthly full retrain"` returns zero commits. The companion `ml_battleground` step from the same workflow run *did* commit (`3f76130641 ML Battleground retrain 2026-04-01T05:05:55Z`), so the workflow fired — but the `ml_crypto_predictor.enhanced_models.main train` step likely failed (or finished with no diff) and the combined commit wrote the battleground change separately. Last actual commit modifying any of the per-pair production joblibs: `f13be58598 2026-03-26 perf: reduce strategy count on dashboard payload` (verified via `git log -- ml_crypto_predictor/enhanced_models/models/AAVEUSDT_15m_A_xgboost.joblib`). That matches the 718h / 30+ day stale flag.

   The 2-hourly `enhanced-ml-crypto.yml` (cron `19 */2 * * *`) `git add`s the same directory at line 169 — which is why mtimes on disk are 2026-04-27 18:49 (every checkout touches them) — but the file *bytes* haven't changed, because that workflow only runs `mode=predict` (line 8 cron) outside the daily `0 2 * * *` train slot at line 7. And only the daily cron at `0 2 * * *` triggers `train-quick`, not the full monthly retrain.

**Why nobody noticed.** (a) The mtime-on-checkout artifact masks the staleness — directory listing shows recent dates. (b) No `assert` step in `ml-monthly-retrain.yml` confirms that step "Full retrain ML Crypto Predictor" actually wrote new bytes (line 38-40 has no diff check). (c) The workflow run history would show "Monthly full retrain" as failed or zero-diff, but nobody is watching cron 0 4 1 * * monthly. (d) Discord notification at `ml-monthly-retrain.yml:71-80` reports "All models refreshed" on success — but success only requires the script to exit zero, not produce diffs.

**Fix.** Two changes:

```yaml
# ml-monthly-retrain.yml:38-40   AFTER
- name: Full retrain ML Crypto Predictor
  run: |
    python -m ml_crypto_predictor.enhanced_models.main train
    # Verify at least 50% of joblibs have mtime < 1h (i.e. were actually retrained)
    python -c "
    import glob, time, os, sys
    files = glob.glob('ml_crypto_predictor/enhanced_models/models/*.joblib')
    fresh = sum(1 for f in files if time.time() - os.path.getmtime(f) < 3600)
    if not files or fresh / len(files) < 0.5:
        print(f'::error::Only {fresh}/{len(files)} joblibs refreshed'); sys.exit(1)
    print(f'OK: {fresh}/{len(files)} joblibs refreshed')
    "
  timeout-minutes: 60
```

Plus add a watchdog workflow that runs daily and alerts if any production joblib has mtime > 35 days:

```yaml
# new file: .github/workflows/ml-staleness-watchdog.yml
on:
  schedule:
    - cron: '0 6 * * *'
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - run: |
          python -c "
          import glob, time, os, sys
          for d in ['ml_crypto_predictor/enhanced_models/models',
                   'ml_gatekeeper/models', 'alpha_engine/data',
                   'mercury2/models']:
              for f in glob.glob(f'{d}/*'):
                  age_d = (time.time() - os.path.getmtime(f)) / 86400
                  if age_d > 35:
                      print(f'::warning::{f} stale ({age_d:.1f} days)')
          "
```

**Test plan.** Manual `workflow_dispatch` of `ml-monthly-retrain.yml` on a branch. Confirm log line `OK: <n>/<n> joblibs refreshed`, confirm a commit lands with diff in `ml_crypto_predictor/enhanced_models/models/`. After merging, monitor 2026-05-01 04:00 UTC cron — expect a "Monthly full retrain 2026-05-01" commit by 06:00 UTC.

**Blast radius.** The mtime assertion will turn a previously-silent failure red. If the trainer crashes due to a recent dependency or data bug (likely — it's been failing silently since at least 2026-04-01), the workflow will go red and trigger Discord alerts. That is the desired outcome but expect support load. Mitigation: have someone on-call when the first post-fix monthly cron fires.

---

## 3. Cross-Cutting Findings

### 3.1 Silent-failure (`|| echo "non-fatal"`) audit

Counted occurrences across `.github/workflows/*.yml`:

| Workflow | `non-fatal` lines |
|---|---:|
| `alpha-engine-live.yml` | **35** |
| `audit-dashboard.yml` | **18** |
| `cross-aggregator.yml` | 7 |
| `darwin-evolution.yml` | 7 |
| `deploy-riseoftheclaw.yml` | 4 |
| `polymarket-signals.yml` | 3 |
| `specialized-scanners.yml` | 3 |
| `paper-trading.yml`, `send-accountability-reminders.yml` | 2 each |
| 24 other workflows | 1 each |

Total: roughly **120+** occurrences. Each is a candidate silent-failure site. Recommend a follow-up audit pass that, for each `non-fatal` step, decides: (a) is the failure truly non-fatal (e.g. optional notification), or (b) is the failure load-bearing (e.g. a trainer)? The two highest-density files (`alpha-engine-live.yml`:35, `audit-dashboard.yml`:18) account for ~44% of the surface and are exactly the workflows powering the four findings above. Priority targets: any step whose script writes a `models/`, `data/`, or `*.json` artifact consumed downstream.

### 3.2 Persistence-gap audit (per-system models/ -> workflow git add)

| Models dir | Trainer workflow | `git add` ? | Status |
|---|---|---|---|
| `alpha_engine/data/rf_model.pkl` | `alpha-engine-live.yml` (per scan) | yes (commit step adds via `git add -f`) | persistence OK; **trainer broken** (Finding 1) |
| `ml_gatekeeper/models/` | `audit-dashboard.yml` | **NO** (Finding 2) | broken |
| `ml_crypto_predictor/enhanced_models/models/` | `ml-monthly-retrain.yml` + `enhanced-ml-crypto.yml` | yes (lines 64, 169) | persistence OK; **trainer not actually firing**(Finding 4) |
| `ml_crypto_predictor/enhanced_models/models/outcome_feedback_model.joblib` | `ml-feedback-retrain.yml` | yes (line 105) | OK (fresh) |
| `mercury2/models/` | `mercury2-retrain.yml` (`0 2 * * 0` weekly) + `ml-monthly-retrain.yml` | yes (lines 64) | OK (fresh) |
| `claude_gainer_ml/models/` | `claude-gainer-tracker.yml` | yes (per audit ref) | OK |
| `ml_battleground/system_*/models/` | `ml-battleground-retrain.yml` (`0 4 * * *`) | yes (`git add ml_battleground/`) | OK |
| `crypto_ml_edge/models/` | `crypto-ml-edge.yml` | not checked end-to-end | **could not verify** |
| `crypto_signal_engine/data/models/` | unknown | not checked | **could not verify** |
| `local_gpu_trainer/models/` | likely manual / local | n/a | n/a |
| `rl_agent/models/` | `rl-agent-ppo.yml` (status `.retired`) | retired workflow | likely abandoned |
| `ml_consensus/models/` | `audit-dashboard.yml` invokes `ml_consensus/consensus.py` | not in commit list | **likely same gap as ml_gatekeeper** |
| `ml_crypto_predictor/models/` (top-level, not enhanced_models/) | `train_crypto_models.yml` | yes (line 87-88) | not actively scheduled — could not verify last commit |
| `HedgeFundData/models/` | none (gitignored per CLAUDE.md memory) | n/a | n/a |

Key new candidate: **`ml_consensus/models/`** is invoked at `audit-dashboard.yml:329` (`python ml_consensus/consensus.py`) but the file-loop commit list in the same workflow does not include `ml_consensus/`. This is a likely twin of Finding 2 — recommend explicit verification.

### 3.3 `model_health_agent.py` assessment

File exists at repo root, 1348 lines (read in full). It implements:

- `DriftDetector` class with KS-test concept drift, Mahalanobis-distance data drift, linear-regression performance decay (lines 576-795).
- `ModelMonitor` class that calls `db.save_metrics`, generates `HealthAlert` rows for accuracy degradation / low Sharpe / low win-rate / consecutive failures (lines 902-963).
- A FastAPI server on port 8001 with `/health/<model>`, `/alerts`, `/dashboard` endpoints (lines 1063-1145).
- A monitoring loop (`_monitoring_loop`, line 1213) that polls every 15 minutes (`Config.MONITORING_INTERVAL_MINUTES = 15`).
- `Config.MODELS_DIR = Path('ml_crypto_predictor/models')` and `PRODUCTION_MODELS_DIR = Path('ml_crypto_predictor/production_models')` at lines 284-285.

**Wiring status.** `grep model_health_agent .github/workflows/*.yml` returns zero matches. The agent has a `__main__` (line 1311) that auto-registers any `*.pkl` in `Config.PRODUCTION_MODELS_DIR` and starts the monitor — but no workflow ever runs `python model_health_agent.py`. The FastAPI server at port 8001 is never started in CI. The SQLite DB at `model_health.db` does not exist in the repo (verified — not in git ls-files for that path).

**Would it have caught the four findings?**

- Finding 1 (`rf_model.pkl` stale): No — `model_health_agent` looks at `ml_crypto_predictor/production_models/`, not `alpha_engine/data/`. Different ML system.
- Finding 2 (`ml_gatekeeper/models/` not persisting): No — same reason.
- Finding 3 (`v4_training_summary.json` missing): No — agent doesn't watch this file.
- Finding 4 (`enhanced_models/` 30+ days stale): **Partially yes**, IF wired. The agent's `Config.PRODUCTION_MODELS_DIR = ml_crypto_predictor/production_models` would auto-register joblibs in that exact path. But `ls ml_crypto_predictor/production_models/` returns "No such file or directory" — that directory does not exist. The agent points at a path the rest of the system doesn't use. The actual production models live in `ml_crypto_predictor/enhanced_models/models/` and `ml_crypto_predictor/enhanced_models/production_models/`.

**Verdict.** `model_health_agent.py` is sophisticated but **completely unwired** — it is not invoked by any workflow, its target directory is empty, its DB is not persisted, and its monitoring thresholds (Sharpe < 0.5, win rate < 45%) would be irrelevant since it never sees real predictions. The audit's "could not verify integration" is correct — there is no integration. Recommend either: (a) write a thin `model_health_runner.yml` workflow that invokes `python model_health_agent.py` daily and ingests metrics from the existing closed-picks JSON, or (b) classify it as a prototype and either retire or scope-tag.

---

## 4. Recommended PR Sequencing

Ship in this order to surface real failures progressively:

1. **PR-1 (lands first, in isolation):** Finding 4's mtime assertion + new `ml-staleness-watchdog.yml`. This is the **diagnostic** — once merged it will start surfacing existing breakage in the next monthly cron and on day 35 of any model. Run it for ~7 days before any other PR to characterize current red surface. Low risk because the watchdog runs on its own cron and can't break other workflows.

2. **PR-2:** Finding 2 (`ml_gatekeeper/models/` git add). Independent of the others; safe to land after PR-1 baseline is established. Combine with the same fix for `ml_consensus/models/` since it's the same defect class.

3. **PR-3:** Finding 1 (`auto_tuner` module path + remove `|| echo`). This will turn the alpha-engine-live workflow red on the first run if there are latent issues. Land it on a Monday morning so on-call has time to debug. Do NOT combine with PR-2 — keep the blast radii independent.

4. **PR-4:** Finding 3 — delete `ml_crypto_predictor/self_improvement.py` (Option B). Five-line PR, zero blast radius. Could also be PR-1 if you want a quick win.

5. **PR-5 (optional, larger scope):** Cross-cutting `|| echo "non-fatal"` reduction. Pick the 5-10 highest-value steps (training, persistence, score generation) and require explicit `continue-on-error: true` instead of the silent `||` pattern. This makes step outcomes visible in the GitHub Actions UI without changing exit semantics.

6. **PR-6 (separate decision required):** `model_health_agent` — wire it up correctly OR retire it. Needs design discussion before any code change.

PRs 1, 2, 3 should NOT ship together — each is designed to surface a different silent failure, and bundling them makes triage harder when the post-merge runs go red.

---

## 5. Open Questions

- **Q1.** Did the `ml-monthly-retrain.yml` 2026-04-01 run actually fail at the `Full retrain ML Crypto Predictor` step, or did it succeed-with-no-diff? Need access to the GitHub Actions run log for run on 2026-04-01 ~04:00 UTC to confirm. Could not verify from local repo state.
- **Q2.** Are `ml_consensus/models/` and `crypto_ml_edge/models/` also persistence-orphans? Suspected by analogy but not verified end-to-end (would require reading 2-3 more workflows fully).
- **Q3.** Is the `alpha_engine/auto_tuner` failure happening on every cron (if so, expect 12 days × 12 runs/day = ~144 silent failures in run history) or only intermittently? Could not verify without the GitHub Actions API.
- **Q4.** What is the intended owner of `model_health_agent.py`? File header says "Author: AI Assistant, Date: 2026" — looks like a one-shot generation that was never integrated. Recommend classifying as prototype.
- **Q5.** Is `ml_crypto_predictor/results/v4_training_summary.json` referenced anywhere outside `self_improvement.py:9`? `grep -r v4_training_summary` would answer this — could not verify in this pass.
- **Q6.** Does `enhanced-ml-crypto.yml`'s daily `0 2 * * *` `train-quick` cron actually retrain the production joblibs, or only a subset? `python -m ml_crypto_predictor.enhanced_models.main train-quick` — semantics of `train-quick` not inspected.

---

*End of report. Investigation strictly read-only — no code or workflow files modified.*
