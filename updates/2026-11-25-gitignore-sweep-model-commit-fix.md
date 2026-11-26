# Fix: gitignore sweep made two ML pipelines green-but-dead — 2026-11-25

## What was broken

Commit **`94c208b8d43`** ("chore: gitignore v6 (Round 4) — hindsight + live-state JSONs +
universal ML hygiene", 2026-05-25) did two things at once to four model directories:

1. **deleted** the tracked model binaries from the tree, and
2. **added ignore rules** for the same paths.

Because the paths were then untracked *and* ignored, every retrain workflow's `git add <models>/`
became a **silent no-op**. Each one is followed by
`git diff --cached --quiet && echo "No changes" && exit 0`, so the job reports **success**.

Meanwhile the consuming scanners guard on the model file with `::warning::` + `exit 0` — also
success. Net effect: **permanently green pipelines that never run.**

### Verified damage

| Pipeline | Retrain cadence | Status | Evidence |
|---|---|---|---|
| **Mercury 2 Signal Scanner** | hourly (`35 * * * *`) | dead since **2026-05-25** | `mercury2/models/` absent from `origin/main`; last added by `bfa7242becf` (2026-05-24); deleted by `94c208b8d43`; `.gitignore:367` |
| **Mercury 2 Weekly Retrain** | weekly (Sun 02:00) | 8/8 green, all no-ops | `2026-10-04 → 2026-11-22` all `success`; `git add mercury2/models/` ignored |
| **Claude Gainer ML** (live + tracker) | 30 min | 5/5 green, `scanner_ran=false` | `claude_gainer_ml/models/*.joblib` ignored; tracker trains at line 135/337 but the add is ignored |

Field observation of the dead scan (raw log, run `45724028919`):

```
##[warning]ensemble_conservative.joblib not found — skipping scanner
          (models committed by Mercury 2 Weekly Retrain workflow; run it first via workflow_dispatch)
```

## What was changed

### 1. `.gitignore` — un-ignore the two pipelines that commit models

Removed:

```diff
-claude_gainer_ml/models/*.joblib
-mercury2/models/*.joblib
```

Kept (not part of this fix — see "Still broken"):

```
crypto_ml_edge/models/*.joblib
ml_battleground/**/models/*.pt
ml_battleground/**/models/*.joblib
```

A comment block was added explaining the history so the rule is not re-added by a future
"hygiene" sweep.

### 2. Fail-open scanners now report and fail instead of exiting green

Three guard blocks changed from `::warning:: … exit 0` to `::error:: … write status … exit 1`:

- `.github/workflows/mercury2-scan.yml` → writes `updates/data/mercury2_scan_status.json`
  (`scanner_ran: false`, `scanner_reason: "no_models"`, `expected_model`, `scanner_checked_at`)
- `.github/workflows/claude-gainer-ml-live.yml` → updates `updates/data/antigravity_ml_performance.json`
- `.github/workflows/claude-gainer-tracker.yml` → same file

The status write **merges** into existing JSON (reads, updates keys, rewrites) so other fields are
preserved, and uses `os.environ["GITHUB_WORKSPACE"]` rather than a relative path so it works from
inside `claude_gainer_ml/`.

Consequence to be aware of: these jobs will now be **red** until models are committed again. That is
intentional — a red job is the honest signal that a scan did not happen. Once the next retrain/
tracker run commits its models, they go green because a scan actually ran. If hourly red is
unacceptable during the gap, change `exit 1` to `exit 0` and keep the status write.

## How it was verified

```
# ignore rules now behave as intended
claude_gainer_ml/models/claude_rf.joblib                -> NOT ignored -> can be committed
mercury2/models/ensemble_conservative.joblib            -> NOT ignored -> can be committed
crypto_ml_edge/models/BTCUSDT_1h_edge.joblib            -> IGNORED (unchanged)
ml_battleground/system_a_filter/models/filter_xgb.joblib-> IGNORED (unchanged)

# status writer: ran the exact snippet, redirected to a temp path
{"scanner_ran": false, "scanner_reason": "no_models",
 "scanner_checked_at": "2026-11-26T00:18:54Z"}     # valid JSON, second run merged cleanly

# YAML still parses
OK .github/workflows/mercury2-scan.yml
OK .github/workflows/claude-gainer-ml-live.yml
OK .github/workflows/claude-gainer-tracker.yml

# no stale fail-open text remains
grep 'skipping scanner' <edited workflows>  -> none
```

**Not verified end-to-end:** no workflow was dispatched or pushed, so the models themselves have not
been re-committed yet. Mercury 2 regenerates on the next weekly retrain (Sun 02:00 UTC) or via
`workflow_dispatch`; Claude Gainer's tracker retrains on its normal cadence. Until then those jobs
will be red by design.

## Still broken (reported, not changed)

- **`ml_battleground`** — `ml-battleground-retrain.yml` runs **daily, 4/4 green**, but only
  `ml_battleground/system_c_deeplearn/models/arch_config.json` survives in the tree; 7 model files
  were deleted by the same commit and `git add ml_battleground/system_*/models/` is ignored. Exactly
  the same silent no-op, on a daily cadence.
- **`crypto_ml_edge`** — **14 `.joblib` models deleted**, only 13 `*_meta.json` files remain tracked.
  No workflow commits `crypto_ml_edge/models/` at all (the monthly retrain's `git add` list does not
  include it), so unlike Mercury 2 this pipeline has **no path back** even if the ignore rule were
  removed.

Both would be fixed the same way, but they were outside the scope of this change.

---

# Second pass — ml_battleground, crypto_ml_edge, and a watchdog (same day)

## ml_battleground — fixed the same way

Removed `ml_battleground/**/models/*.pt` and `ml_battleground/**/models/*.joblib` from
`.gitignore`. `ml-battleground-retrain.yml` already runs `git add ml_battleground/system_*/models/`
daily, so it can commit again.

Evidence of the same failure: the commit deleted **7** model files; only
`ml_battleground/system_c_deeplearn/models/arch_config.json` survives; the daily retrain has been
green (2026-11-22 → 11-25) while committing nothing.

## crypto_ml_edge — commit path added, but nothing trains it

- Removed `crypto_ml_edge/models/*.joblib` from `.gitignore`.
- Added `crypto_ml_edge/models/` to the commit step of `ml-monthly-retrain.yml`.

**Important limitation:** this creates a commit *path*, not a trainer. `crypto_ml_edge/trainer.py`
defines an `EdgeTrainer` **class** with no `__main__` block and no argparse, and no workflow invokes
it, so the 14 deleted `.joblib` files will not reappear by themselves. Adding the un-ignore alone
would have accomplished nothing, which is why the commit line was also added.

Also worth knowing before reviving it: `crypto_ml_edge/AUDIT.md` records that these models scored
**ROC-AUC 0.27–0.28** (near-zero discriminative power) across 793 trained models, and that the
production pick generator was not gated on the validation gates. The deletion may have been
partly intentional. Reviving the pipeline needs a real training driver *and* a re-validation.

## Watchdog — fails when a scanner has been dead > 24h

New step in `.github/workflows/ml-staleness-watchdog.yml`:
"Scanner liveness (fail if scanner_ran=false for > 24h)".

To make "for how long" measurable, the three scanners now persist `scanner_ran_false_since`
(set once when the scanner first reports false, and **preserved** across later failures) alongside
`scanner_checked_at` (refreshed every run). The watchdog reads:

- `updates/data/antigravity_ml_performance.json` (claude_gainer_ml)
- `updates/data/mercury2_scan_status.json` (mercury2)

and exits 1 with `::error::scanner '<name>' has not run for <age>` when the age exceeds 24h.
Missing status files are skipped, not failed, so a fresh checkout does not trip it.

### Verification of the watchdog

Extracted the workflow's embedded python and ran it against fixtures:

| case | expected | actual |
|---|---|---|
| no status files | exit 0 | exit 0 |
| `scanner_ran=false`, 1h old | exit 0 (within limit) | exit 0 |
| `scanner_ran=false`, 30h old | exit 1 | exit 1 + `::error::` |
| `scanner_ran=true` | exit 0 | exit 0 |
| false with only a 48h `scanner_checked_at` | exit 1 | exit 1 |

Guard idempotency: ran the mercury2 status writer twice with a seeded 40h-old
`scanner_ran_false_since` — the stamp was **unchanged** on the second run while
`scanner_checked_at` refreshed, so age keeps accruing instead of resetting to now.

All five edited workflows parse with `yaml.safe_load`.
