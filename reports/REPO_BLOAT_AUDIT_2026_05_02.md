# Repository Data Hygiene Audit — `findtorontoevents_antigravity.ca`

**Date:** 2026-05-02  
**Auditor:** Kimi Code CLI  
**Commit range:** `8d1eb4e0` (48h ago) → `HEAD`  

---

## 1. Executive Summary

The repository is experiencing severe bloat from auto-generated data artifacts committed directly to `main`. In the last **48 hours** there were **3,725 commits**, the majority of which were `[skip ci]` auto-commits updating binary and JSON data files. Tracked artifacts currently consume **~1.36 GB** of the working tree, and ~473 MB of binary churn landed in just the last two days.

**Key finding:** `.gitignore` has large, obvious gaps. There are **no global ignores** for `*.parquet`, `*.pkl`, `*.npy`, or `*.log`, and high-churn data directories are not blanket-ignored. Meanwhile, CI workflows commit these files to git on every run instead of using workflow artifacts or external storage.

---

## 2. Current `.gitignore` Gap Analysis

| Pattern | Globally Ignored? | Notes |
|---------|-------------------|-------|
| `*.parquet` | **NO** | Only `alpha_engine/data/bt_cache_*.parquet` and `ml_crypto_predictor/enhanced_models/data/klines/` are ignored. `data/parquet/*` is fully tracked. |
| `*.pkl` | **NO** | 20+ tracked `.pkl` files (~380 MB), including `ml_crypto_predictor/production_models/*.pkl` and `KIMI_RISEOFTHECLAW/data/rf_model.pkl`. |
| `*.npy` | **NO** | `ml_gatekeeper/models/train_score_hist.npy` is tracked and modified hourly. |
| `*.log` | **NO** | Only `scanner_lifecycle.log` is explicitly ignored. `market_beating_bot.log`, `trading_bot.log`, `battle_test.log`, `KIMI_FEB172026/logs/unified_forward_test.log` are all tracked. |
| `*.db` | **Partially** | Globally ignored, but four DBs are explicitly **un-ignored** with `!` rules. Several other `.db` files are tracked (e.g., `signal_recorder/data/signal_log.db`, `meta_strategy/data/meta_strategy.db`, `incubator/forward_test.db`). |
| `alpha_engine/data/*.json` | **NO** | **1,893 JSON data files** tracked in this directory alone. Most are auto-generated every hour. |
| `battleground/data/*.json` | **NO** | 30 tracked JSON data files. |
| `crypto_signal_engine/data/*.json` | **NO** | 10 tracked JSON data files. |
| `copy_trader_intel/data/*.json` | **NO** | 135 tracked JSON data files. |

### Existing exceptions that must be preserved

The current `.gitignore` already un-ignores specific DBs required for state persistence:

```gitignore
!sandbox/data/opposite_day.db
!paper_trading/data/paper.db
!coinglass_strategies/data/coinglass.db
!quan_engine/data/quan_engine.db
```

Additionally, `alpha_engine/data/` contains **source files** that must remain tracked:

- `alpha_engine/data/__init__.py`
- `alpha_engine/data/analyze_dow_asset.py`
- `alpha_engine/data/bucket_backtest.py`
- `alpha_engine/data/earnings.py`
- `alpha_engine/data/fundamentals.py`
- `alpha_engine/data/insider.py`
- `alpha_engine/data/macro.py`
- `alpha_engine/data/price_loader.py`
- `alpha_engine/data/send_to_bus.py`
- `alpha_engine/data/sentiment.py`
- `alpha_engine/data/tmp_quant.py`
- `alpha_engine/data/universe.py`
- `alpha_engine/data/DOW_ASSET_ANALYSIS.md`
- `alpha_engine/data/ml_integration_report.md`
- `alpha_engine/data/trading_signal_analysis_20260328.md`
- `alpha_engine/data/continuous_improvement_report.md`

These must be preserved with `!` rules or by using narrow ignore patterns rather than blanket directory ignores.

---

## 3. Quantified Bloat Impact (Last 48 Hours)

### 3.1 Commit velocity
- **Total commits:** 3,725
- **Commits with `[skip ci]`:** ~90% (auto-generated data updates)

### 3.2 Binary artifacts (parquet, pkl, npy, log, db)

| Metric | Value |
|--------|-------|
| Unique files touched | 56 |
| Total current size of touched files | **~473 MB** |
| Largest single file | `signal_recorder/data/signal_log.db` (66.3 MB) |
| Largest category | `.pkl` production models (~350 MB combined) |

**Top offenders by size (current on-disk):**

| File | Size |
|------|------|
| `signal_recorder/data/signal_log.db` | 66.3 MB |
| `meta_strategy/data/meta_strategy.db` | 55.0 MB |
| `ml_crypto_predictor/production_models/SOL_USDT_production.pkl` | 23.9 MB |
| `ml_crypto_predictor/production_models/TRX_USDT_production.pkl` | 23.6 MB |
| `ml_crypto_predictor/production_models/DOGE_USDT_production.pkl` | 23.1 MB |
| `coinglass_strategies/data/coinglass.db` | 22.5 MB |
| `KIMI_RISEOFTHECLAW/data/rf_model.pkl` | 4.7 MB |
| `quan_engine/data/quan_engine.db` | 4.1 MB |
| `market_beating_bot.log` | 2.4 MB |
| `battle_test.log` | 1.5 MB |

### 3.3 JSON data files

| Metric | Value |
|--------|-------|
| JSON files modified | 501 |
| JSON files added | 244 |
| Total JSON churn | **745 files** |
| Top churned file | `alpha_engine/data/active_picks.json` (128 modifications) |
| Second highest | `copy_trader_intel/data/polymarket_trader_profiles.json` (108 modifications) |

**Top JSON churn files (modification count in 48h):**

| File | Times Modified |
|------|----------------|
| `alpha_engine/data/active_picks.json` | 128 |
| `copy_trader_intel/data/polymarket_trader_profiles.json` | 108 |
| `copy_trader_intel/data/polymarket_picks.json` | 108 |
| `cross_aggregation/data/consensus_outcomes.json` | 99 |
| `alpha_engine/data/kalshi_signals.json` | 86 |
| `alpha_engine/data/prediction_market_picks.json` | 86 |
| `KIMI_RISEOFTHECLAW/data/rf_model.pkl` | 60 |
| `prediction_market_agents/data/*.json` | 55 each |
| `crypto_signal_engine/data/*.json` | 54 each |
| `audit_trail/data/dashboard_payload.json` | 37 |

### 3.4 Total tracked artifact footprint

| File type | Tracked file count | Total size |
|-----------|-------------------|------------|
| `.parquet`, `.pkl`, `.npy`, `.log`, `.db` | 251 | **741.8 MB** |
| `.json` | 6,340 | **616.3 MB** |
| **Combined data artifacts** | **~6,600** | **~1.36 GB** |

---

## 4. Proposed `.gitignore` Patch

The following patch adds global ignores for high-churn binary formats and directory-level ignores for the worst-offending data directories, while preserving existing exceptions and source files.

```diff
--- a/.gitignore
+++ b/.gitignore
@@ -1,5 +1,14 @@
 # Backtest cache (parquet files from yfinance)
 alpha_engine/data/bt_cache_*.parquet
+
+# Global ignores for auto-generated binary artifacts
+*.parquet
+*.pkl
+*.npy
+*.log
+
+# Ignore all JSON data dumps in high-churn engine directories
+alpha_engine/data/*.json
 
 # FRED data cache (rebuildable from API; see alpha_engine/fred_data_fetcher.py)
 alpha_engine/data/fred_cache/
@@ -21,10 +30,24 @@ __pycache__/
 *.db-wal
 *.db-shm
 *.db.bak
+
 # Exception: DBs committed by GH Actions for state persistence
 !sandbox/data/opposite_day.db
 !paper_trading/data/paper.db
 !coinglass_strategies/data/coinglass.db
 !quan_engine/data/quan_engine.db
+
+# Exception: source files in alpha_engine/data must remain tracked
+!alpha_engine/data/__init__.py
+!alpha_engine/data/*.py
+!alpha_engine/data/*.md
+!alpha_engine/data/*.txt
+
+# Exception: specific DBs currently required by workflows
+!signal_recorder/data/signal_log.db
+!meta_strategy/data/meta_strategy.db
+!incubator/forward_test.db
+
+# Exception: preserve .gitkeep files so directory structure stays
+!**/.gitkeep
 
 # Environment files
 .env
@@ -63,7 +86,6 @@ audit_trail/data/hf_gate_telemetry.json
 .pytest_cache/
 
 # Generated strategy bundles (large, auto-generated)
-alpha_engine/generated_v2_bundle.py
 alpha_engine/new_strategies/multi_asset_report.json
 
 # Temp files
@@ -81,6 +103,19 @@ docs/*.tmp
 # Large DB files (>100MB GitHub limit)
 genome/strategy_registry.db
 genome/phoenix_registry.db
+
+# High-churn data directories (auto-generated every hour)
+battleground/data/*.json
+crypto_signal_engine/data/*.json
+copy_trader_intel/data/*.json
+ml_crypto_predictor/enhanced_models/data/klines/
+ml_crypto_predictor/enhanced_models/live_picks/*.json
+ml_crypto_predictor/enhanced_models/feedback_data/*.json
+ml_crypto_predictor/production_models/*.pkl
+ml_gatekeeper/models/*.npy
+ml_gatekeeper/models/*.joblib
+KIMI_RISEOFTHECLAW/data/*.json
+KIMI_RISEOFTHECLAW/data/*.pkl
+riseoftheclaw/data/*.json
 
 # SQL dumps (contain internal IPs and DB schemas) — added 2026-04-11
 data/*.sql
```

**Note:** The `!alpha_engine/data/*.py`, `!*.md`, and `!*.txt` rules ensure the 16+ source/analysis files in `alpha_engine/data/` are not accidentally ignored. The `!**/.gitkeep` rule ensures empty data directories remain tracked.

---

## 5. CI Architecture Recommendation

### 5.1 Problem

Currently, ~280 workflows commit data directly to `main` on every run. Examples:

- `parquet-ingest.yml` runs every 4 hours and commits `data/parquet/*`
- `market_beating.yml` runs every 2 hours and commits `market_beating_bot.log`, `signals_database.json`, etc.
- `audit-dashboard.yml` commits generated HTML/JSON payloads
- `battle_test.yml`, `live_trading.yml`, `signal-recorder.yml`, and dozens more commit `.db`, `.json`, and `.log` files

This creates:
- **3,000+ commits per day**
- **Merge conflicts** when multiple workflows race (evidenced by frequent "Merge branch 'main'" commits)
- **Extremely slow clones** (`git clone` must download every historical version of every `.pkl` and `.db`)
- **LFS trap risk**: If LFS is enabled later, all historical binary blobs would need rewriting

### 5.2 Recommended changes

#### Option A: Workflow Artifacts (short-term, lowest effort)

Replace `git add` + `git commit` + `git push` in data-producing workflows with `actions/upload-artifact`.

**Example migration for `market_beating.yml`:**

```yaml
- name: Upload run artifacts
  uses: actions/upload-artifact@v4
  with:
    name: market-beating-data-${{ github.run_id }}
    path: |
      signals_database.json
      validation_results.json
      tweak_history.json
      MARKET_BEATING_REPORT.md
      market_beating_bot.log
    retention-days: 30   # or 90
```

**Pros:**
- No repo bloat
- Artifacts are downloadable from the Actions UI
- Native GitHub integration

**Cons:**
- 90-day retention limit (GitHub default)
- Not accessible to downstream workflows unless using `actions/download-artifact` with known run IDs

#### Option B: External Data Lake (medium-term, best practice)

Write auto-generated data to an external store instead of git:

| Store | Best for | Estimated cost |
|-------|----------|----------------|
| **S3 / R2 / B2** | `.parquet`, `.pkl`, `.db`, `.log` archives | ~$5-20/mo for <100 GB |
| **FTP / GoDaddy** (already used for deploy) | HTML dashboards, JSON pick files | Near-zero (existing) |
| **SQLite on persistent runner / self-hosted** | Stateful `.db` files (e.g., `signal_log.db`) | Existing infrastructure |
| **Separate `data` repo** | If git history is required for audit | Same LFS risks, but isolates bloat |

**Implementation sketch:**

1. Add a composite action `.github/actions/upload-data-lake` that wraps `aws s3 sync` or `lftp` to the existing FTP server.
2. Update workflows to write to `s3://antigravity-data/<workflow>/<date>/` instead of committing.
3. For the audit dashboard, read from the data lake at render time or copy latest artifacts into the build step.

#### Option C: Hybrid — Keep config, move data

- **Keep in git:** Source code, `.MD` docs, `.html` templates, `.yml` workflows, configuration JSON, `.gitkeep`
- **Move to artifacts/data lake:** `.parquet`, `.pkl`, `.npy`, `.db`, `.log`, hourly JSON dumps, backtest results

This is the **recommended long-term architecture**.

---

## 6. Risk Assessment

| Risk | Current State | If Changes Applied |
|------|---------------|-------------------|
| **Repo clone time** | Very slow (~1.36 GB of data artifacts in working tree, much more in history) | Significant improvement; new clones skip data artifacts |
| **Merge conflicts** | High — 3,725 commits in 48h cause constant race conditions | Near-zero for data files; conflicts only on actual source code |
| **GitHub LFS costs** | Currently not using LFS, but binaries in history make migration painful | If LFS is adopted later, only source files need migration |
| **CI minute burn** | High — every workflow does full checkout + push cycle | Lower — artifact upload is faster than `git push` |
| **Data loss risk** | Low (git keeps everything) | Medium if artifacts are the only copy; mitigate with 90-day retention + S3 sync |
| **Workflow breakage** | N/A | **High** if `.gitignore` is applied without updating workflows — workflows that `git add` ignored files will silently stop committing data, which may break downstream steps that expect committed files |

### Critical warning

**Do NOT apply the `.gitignore` patch without simultaneously updating the workflows.** If workflows continue to run but their `git add` commands silently ignore files, downstream jobs that read `alpha_engine/data/active_picks.json` from the repo will see stale data. The migration must be:

1. Update workflows to write data to artifacts / external store
2. Update downstream consumers to read from the new location
3. **Then** apply `.gitignore`
4. Optionally run `git-filter-repo` or BFG Repo-Cleaner to remove historical blobs (this rewrites history and requires force-push coordination)

---

## 7. Immediate Action Items

| Priority | Action | Owner |
|----------|--------|-------|
| P0 | Update the top 10 highest-churn workflows to use `actions/upload-artifact` instead of `git commit` | DevOps / CI owner |
| P1 | Apply the proposed `.gitignore` patch to prevent new data artifacts from being committed | Repo maintainer |
| P1 | Create a composite action for uploading artifacts to the existing FTP/S3 data lake | DevOps |
| P2 | Audit `alpha_engine/data/*.json` — identify which files are truly config vs. auto-generated dumps | Data engineer |
| P2 | Evaluate `git-filter-repo` to strip historical `.pkl`, `.db`, and `.log` blobs from history (rewrites history — coordinate with team) | Repo maintainer |
| P3 | Document the data architecture: "source code in git, generated data in artifacts" | Tech lead |

---

*End of audit.*
