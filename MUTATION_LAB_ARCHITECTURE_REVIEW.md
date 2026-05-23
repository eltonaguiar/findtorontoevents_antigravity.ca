# Mutation Lab Architecture Review – v2

## Executive Summary
The Mutation Lab is a high‑throughput strategy‑generation engine that mutates top‑performing (winner) and under‑performing (loser) strategies from the audit database. The goal is to produce a curated set of candidate strategies that can be auto‑ingested by the live dashboard (`genome/data/mutation_lab_picks.json`).

Three implementation approaches were evaluated. **Approach 2 – Multi‑Stage Pipeline** remains the preferred design, but this version adds deeper technical feedback, risk considerations, and a concrete implementation checklist.

---

## 1. Detailed Approach Review

### 1.1 Approach 1 – Single Monolithic Script (`genome/hourly_mutation_lab.py`)

**Pros**
- Minimal file count; easy to spin up locally.
- Straight‑forward debugging (single entry point).

**Cons**
- **Performance**: Sequential back‑testing of ~50 mutations (5 strategies × 10 targets) on 3 symbols × 750 bars can exceed 30‑60 min, risking GitHub Action time‑outs and limiting scalability.
- **Fault Isolation**: Any exception aborts the entire run, losing all work.
- **Maintainability**: Adding new mutation types or scaling out (e.g., more symbols) requires a full rewrite.

**Verdict** – Suitable for a quick prototype or local experimentation, but not for production.

### 1.2 Approach 2 – Multi‑Stage Pipeline (Recommended)

**Workflow Overview**
| Stage | Purpose | Artifact | Parallelism |
|-------|---------|----------|-------------|
| **SCOUT** | Query audit DB for top‑15 winners & bottom‑15 losers; write `mutation_targets.json`. | `mutation_targets.json` | No |
| **MUTATE + BACKTEST** | Generate mutations (A‑amplify, B‑flip, C‑fix/invert) and back‑test each on 3 symbols × 750 bars. | `mutation_results_*.json` (one per job) | 3 parallel jobs (A, B, C) |
| **PROMOTE** | Merge results, apply quality gates, register winners in `strategy_registry.db`, write final picks to `genome/data/mutation_lab_picks.json`. | `mutation_lab_picks.json` | No |

**Pros**
- **Scalability**: Parallel back‑testing reduces wall‑clock time to ~20‑25 min.
- **Reliability**: Individual job failure does not affect the others; can be retried automatically.
- **Extensibility**: New mutation strategies can be added as additional matrix jobs.
- **Clear Separation** of concerns – each stage can be unit‑tested independently.

**Cons**
- Slightly more complex CI configuration (artifact handling, matrix setup).
- Requires a shared storage location (e.g., GitHub Actions artifacts or a workspace‑mounted volume) for passing JSON files between stages.

**Additional Technical Recommendations**
1. **Matrix Strategy** – Parameterize the back‑test job over the list of symbols to enable future scaling without duplicating jobs.
2. **Caching** – Cache the audit DB query result (`mutation_targets.json`) using the `actions/cache` step to avoid unnecessary DB hits when the data has not changed.
3. **Early Filtering** – Apply cheap heuristics (e.g., max drawdown < 20 %) before the expensive back‑test to prune low‑quality mutations early.
4. **Artifact Size Management** – Compress JSON results (`gzip`) before uploading to keep artifact payloads small.
5. **Security** – Ensure the workflow runs with a least‑privilege token; restrict write access to `genome/data/`.

**Sample Workflow Snippet**
```yaml
name: Mutation Lab Pipeline
on:
  schedule:
    - cron: '0 * * * *'   # hourly
jobs:
  scout:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v3
      - name: Run SCOUT
        run: python scripts/scout.py
      - name: Upload targets
        uses: actions/upload-artifact@v3
        with:
          name: mutation_targets
          path: mutation_targets.json

  mutate-a:
    needs: scout
    runs-on: ubuntu-latest
    strategy:
      matrix:
        symbol: [BTCUSDT, ETHUSDT, SOLUSDT]
    steps:
      - name: Download targets
        uses: actions/download-artifact@v3
        with:
          name: mutation_targets
      - name: Run Mutation A
        run: python scripts/mutate_a.py --symbol ${{ matrix.symbol }}
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: results-a
          path: mutation_results_a.json

  # mutate-b and mutate-c similar …

  promote:
    needs: [mutate-a, mutate-b, mutate-c]
    runs-on: ubuntu-latest
    steps:
      - name: Download all results
        uses: actions/download-artifact@v3
        with:
          name: results-*
      - name: Merge & filter
        run: python scripts/promote.py
      - name: Commit picks
        run: |
          git config user.name "github-actions"
          git config user.email "actions@github.com"
          git add genome/data/mutation_lab_picks.json
          git commit -m "Update mutation lab picks"
          git push
```

**Verdict** – Production‑ready, meets performance and reliability goals.

### 1.3 Approach 3 – Extend `darwin-evolution.yml`

**Pros**
- No new workflow file; reuses existing triggers and environment.

**Cons**
- **Resource Contention** – The existing Darwin pipeline already runs five heavy engines; adding a mutation stage may push total runtime beyond the 6‑hour GitHub limit.
- **Coupling** – Failures in the mutation lab would affect the evolution pipeline, making debugging harder.
- **Responsibility Violation** – Mixing two distinct problem domains (evolution vs mutation) reduces clarity and future maintainability.

**Verdict** – Not recommended unless a dedicated pipeline is unavailable.

---

## 2. Revised Recommendation & Action Plan

**Adopt Approach 2** with the enhancements listed above. The following concrete steps will bring the design to implementation:

1. **Create Directory Structure** – `genome/mutation_lab/` for scripts and a `templates/` sub‑folder for YAML snippets.
2. **Implement Stage Scripts** – `scout.py`, `mutate_a.py`, `mutate_b.py`, `mutate_c.py`, `promote.py`. Each script should accept command‑line arguments for symbols, targets, and output paths.
3. **Add Unit Tests** – For each script, write pytest cases under `alpha_engine/tests/mutation_lab/` to validate JSON schema and quality‑gate logic.
4. **Draft GitHub Actions Workflow** – Place the YAML in `.github/workflows/mutation_lab.yml` using the snippet above as a starting point.
5. **Run Local Smoke Test** – Execute the full pipeline locally with a reduced symbol list to verify artifact passing.
6. **Deploy and Monitor** – Enable the workflow, monitor runtime and cost (expected <$0.02 per run), and adjust caching or parallelism as needed.

---

## 3. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **GitHub Action timeout** – Back‑test takes longer than expected | Low (with parallel jobs) | High (pipeline failure) | Use matrix parallelism, early filtering, and monitor runtime. |
| **Artifact corruption** – JSON payloads become malformed | Low | Medium | Validate JSON schema after each stage; fail fast on errors. |
| **Database schema change** – Audit DB column rename | Medium | Medium | Abstract DB access behind a thin wrapper; version‑control queries. |
| **Excessive cost** – Unexpected increase in compute minutes | Low | Low | Set a budget alert; use `actions/cache` to reduce DB reads. |

---

## 4. Closing Remarks
The multi‑stage pipeline provides a robust, extensible foundation for the Mutation Lab while keeping the existing audit dashboard untouched. By following the action plan and risk mitigations, the team can deliver a reliable, high‑throughput strategy‑generation system that scales with future data volumes.
