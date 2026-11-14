# Remediation Plan — /audit Prediction System

**Date:** 2026-11-14
**Inputs:** `updates/2026-11-14-quant-audit-multitest.md` (audit) and `updates/2026-11-14-edge-search-results.md` (v1–v4 edge search)
**Premise:** the audit verdict is NOT profitable / NOT statistically sound. This plan is the shortest credible path to either (a) one statistically defensible sleeve, or (b) a defensible decision to stop.

---

## 0. Why the current numbers cannot be fixed by tuning

Five independent defects each independently inflate results. Fixing one without the others reproduces the same illusion.

| # | Defect | Measured today | Effect on reported performance |
|---|---|---|---|
| D1 | Denominator corruption: expired picks excluded from WON/LOST | 3,378 expired rows, `closed_at` empty, P/L 0.0 | Upward: slow-bleed outcomes vanish from the denominator |
| D2 | Multiple testing computed but not enforced | 177 strategies; Bonferroni threshold 2.82e-4; `_fdr_gate_enforce=false`; 0 emitters significant | "Best" cells are selection artifacts |
| D3 | Pseudo-replication | 997 rows in 414 duplicate (symbol,dir,day,strategy) groups, max 9; 84.9% of outcomes from 2 emitters | Inflated n, optimistic p-values |
| D4 | Broken measurement surface | 60 of 189 active-pick fields empty; 514 open rows with null price; 10 displayed vs 4,361 tracked open | Nothing on the page is auditable per-pick |
| D5 | Operational decay | Alpha scanner crash-looping 17×/day (`KeyError: 'LONG'`, `scanner.py:2942`); Resolver Step 5-6 and Step 7 never ran; CI red on both Python shards | Stale/never-resolved ledger |

**Implication:** the plan is ordered D5 → D1 → D3 → D4 → D2. Gates cannot be trusted until the data they run on is honest, and data cannot be trusted while the resolver does not run.

---

## 1. Five highest-leverage changes (ranked by impact × certainty ÷ effort)

### C1 — Make every pick terminate, and count it
**What:** one resolver path that always writes a terminal state (`TP_HIT` / `SL_HIT` / `TIME_EXIT` / `EXPIRED`) plus `exit_price` and `closed_at`. `EXPIRED` becomes a real outcome (0% return, counted as a non-win), never a silent exclusion.
**Acceptance test:** zero picks older than 30 days without a terminal state; `SUM(terminal) == COUNT(all picks)`; re-running the resolver twice produces byte-identical results (idempotent).
**Impact × certainty ÷ effort:** highest. Unblocks every other number.

### C2 — Enforce the gate in the code path, reject by default
**What:** a single `admit_strategy()` function that returns `False` unless **all** hold: effective independent n ≥ 100; DSR ≥ 0.95 using correlation-adjusted trial count; PBO ≤ 0.10; BH-FDR q < 0.05 across the tested family; OOS PF ≥ 1.25 after class costs. No dashboard, scanner, or promotion path may bypass it; the FDR flag is deleted, not defaulted off.
**Acceptance test:** a synthetic null strategy run through 100 trials is rejected in ≥95% of simulated panels; no strategy with n < 100 can appear in Smart Picks / Verified Alpha / High Conviction (assert in tests).
**Impact × certainty ÷ effort:** high impact, high certainty, moderate effort. This is the single change that makes "some win by chance" impossible to publish.

### C3 — De-duplicate at write time, report effective n
**What:** idempotent upsert keyed on `(symbol, direction, strategy, signal_date)`; every aggregate publishes `n_raw` and `n_effective` (block-bootstrap / cluster count).
**Acceptance test:** duplicate groups = 0; `n_effective ≤ n_raw` on every row; the 414 known duplicate groups collapse.
**Impact × certainty ÷ effort:** high impact, deterministic, low effort.

### C4 — One ledger, marked to market hourly
**What:** dashboard and live tracker read the same open-position view; `current_price` non-null or the row is excluded from P/L (not shown as 0.0).
**Acceptance test:** open-count difference between dashboard and tracker < 1%; zero open rows with null price and non-null P/L; spot-check 10 rows against Binance/CNBC within 1%.
**Impact × certainty ÷ effort:** high impact, low certainty on effort (touches generator + template).

### C5 — Consolidate operations to five workflows
**What:** `alpha-scan`, `resolver`, `dashboard`, `ml-retrain`, `freshness-guard`. Everything else archived. Fix the scanner `KeyError` by normalizing direction tokens at the boundary (`LONG/SHORT → BUY/SELL`) with a regression test.
**Acceptance test:** 7 consecutive days where all five are green; no core workflow whose most recent run failed; total workflow count < 20.
**Impact × certainty ÷ effort:** high impact on diagnosability; moderate effort (mostly deletion).

---

## 2. Multiple-testing framework to adopt (and where to enforce it)

| Layer | Method | Why this one | Where enforced |
|---|---|---|---|
| Per-strategy credibility | **Deflated Sharpe Ratio ≥ 0.95** with N = *effective* trials | Corrects selection bias and non-normal returns; N must be correlation-adjusted or it over-penalises (Bailey & López de Prado 2014; effective-trials literature 2026) | `admit_strategy()` — hard boolean |
| Family-wise screen | **Benjamini–Hochberg FDR q < 0.05** across all strategies tested in the class | Bonferroni at 177 tests demands p<2.8e-4, which no retail-frequency sleeve will reach; BH controls the false-discovery proportion instead of the family-wise error | `admit_strategy()` — hard boolean |
| Overfitting probability | **PBO ≤ 0.10** via CSCV | Directly estimates "probability the backtest winner underperforms OOS"; more interpretable than a p-value | `admit_strategy()` |
| Class-level claim | **SPA / White's Reality Check** when ≥2 strategies compete | Controls for the full search when claiming "this class has edge" | class-level report only |
| Reporting | publish **n_effective**, DSR, PBO, BH q next to every PF/WR | The page must show the correction, not just the raw metric | dashboard payload |

**Critical detail:** the site currently *computes* corrections (`n_bonferroni_pass: 21`, `n_fdr_tested: 83`) and then *does not enforce them* (`_fdr_gate_enforce: false`). Enforcement means the function refuses to emit the pick — not a badge.

**Why not Bonferroni alone:** at 177 trials the threshold is 2.82e-4. With realistic retail samples (n≈100–500) no honest sleeve clears it, so a Bonferroni-only gate would reject everything including a genuine 0.4-Sharpe carry book. Use BH for the screen and DSR for the per-strategy hurdle.

---

## 3. Denominator integrity (how expired picks must be handled)

Three ledgers, never mixed:

1. **Emissions** — everything the scanners produced (counts only; no performance claim).
2. **Resolved** — terminal state with `exit_price`. WR/PF computed here.
3. **All-inclusive** — resolved plus expired-at-zero plus still-open marked to market. **This is the only ledger allowed to make a headline performance claim.**

Rules:
- `EXPIRED` = 0% return, counted as **not a win**. Never dropped, never converted to LOST with a fabricated price.
- Open positions are marked to market hourly; an open position with no price is excluded from P/L and **reported as unpriced**, not as 0.0%.
- Report `censored_pct` (expired + unpriced) beside every WR. If censored > 20%, the headline is labelled INCOMPLETE.
- Retire the current `TIME_EXIT → LOST, pnl=0.0` bulk update class of fix: it destroys the record.

**Acceptance test:** recomputing 2026-11 with the new ledgers changes reported WR by a documented, explained amount, and `resolved + expired + open = emissions` exactly.

---

## 4. Pseudo-replication (177 strategies, 2 emitters)

- Cluster before counting: group by `(symbol, direction, signal_date)`; a cluster is one independent observation.
- Report `n_effective` from a block bootstrap over date clusters, not row count.
- Cap per-emitter contribution: if one emitter supplies > 50% of a class's observations, the class cannot be promoted on that evidence alone.
- Require ≥ 100 **independent** trades (≈ ≥ 100 clusters) before any promotion claim.
- Keep the 2-emitter concentration as a permanent dashboard metric (`source_hhi`).

**Acceptance test:** the 3,500-row recent-closed ledger reports n_effective materially below n_raw; no class card shows n_effective < 100 without an INSUFFICIENT tag.

---

## 5. Kill list

**Kill immediately (no further evidence needed):**
- All strategies with n < 100 or BH q > 0.05 — includes every current Smart Picks / High Conviction entry.
- The 11 `SURVIVOR` labels with `fwd_trades = 0` (label awarded on backtest alone).
- The 3 sidecars marked `PROMOTED` with n = 0.
- FOREX (n=612, WR 32.2%, PF 0.66), ETF (WR 2.2%, PF 0.02), MEME (WR 10%, PF 0.023), BOND (n=1).
- The 20 never-run workflows and the 19 whose last run is >90 days old.

**Keep only as shadow candidates (no capital, no dashboard headline):**
- `battleground`: 56.6% WR, n=122, PF 1.756, p=0.087 — the only positive deviation; needs ≥200 independent trades and null p<0.05 to be reconsidered.
- `luxalgo_filters`: PF 1.131 on n=1,271 — positive but below any cost-adjusted significance bar.
- `multi_asset_copytrader`: PF 1.696 on n=39 — too small to interpret.

**Evidence that would justify keeping anything:** ≥200 independent trades, intrabar-resolved, cost-inclusive, DSR ≥ 0.95, PBO ≤ 0.10, BH q < 0.05, and beat a matched random-entry null at p < 0.05.

---

## 6. Four-week sequencing (dependencies explicit)

| Week | Work | Depends on | Exit criterion |
|---|---|---|---|
| 1 | C5 ops fixes; normalise direction tokens; run Resolver Step 5-6 and Step 7 for the first time; terminate the 3,378 expired rows | — | Scanner completes 7 consecutive runs; 0 picks >30d without terminal state |
| 2 | C1 denominator ledgers; C3 dedupe + n_effective; backfill `exit_price` | W1 | `resolved + expired + open = emissions`; duplicate groups = 0 |
| 3 | C2 gate enforcement; re-run all 177 strategies through `admit_strategy()`; C4 single ledger | W2 | Promotion list is a strict subset of DSR/PBO/BH passers; dashboard vs tracker <1% |
| 4 | Pre-register hypotheses (M-107) for survivors; run forward pilot with random-entry null; publish go/no-go | W3 | Exactly one of: one sleeve passes all gates, or a written stop decision |

**Parallel, non-blocking:** the edge search (`updates/2026-11-14-edge-search-results.md`) continues on public data; it does not depend on the site's ledger and should not wait for it.

---

## 7. The single go/no-go metric

> **Lower 95% bootstrap bound of cost-inclusive expectancy > 0, on ≥ 200 independently clustered out-of-sample trades, after BH-FDR across the tested family, with DSR ≥ 0.95 and PBO ≤ 0.10.**

Operationalised as: **one asset class reaches PF ≥ 1.25, n_effective ≥ 200, DSR ≥ 0.95, PBO ≤ 0.10, BH q < 0.05, and beats a matched random-entry null at p < 0.05 — held for 90 days of paper trading.**

Until then the system is a research project. The current evidence (3,489 resolved picks, WR 41.8%, binomial p = 1.00; 0/8 emitters significant; 0/40 own-backtest trials passing) says it is not close.

---

## 8. What this audit cannot conclude

- **Magnitude of the expiration bias** — whether the 3,378 expired picks were net winners or losers is not recoverable from the published payload (no `exit_price`, no `closed_at`).
- **Futures pricing** — ES/PA/SB could not be verified (Yahoo 429, CNBC null, Stooq JS-gated).
- **Warning-level CI annotations** — run-level `/annotations` returns 404 for this repo; only failure logs were inspected.
- **MySQL source tables** — not queried; all figures come from published JSON + the GitHub API.
- **Whether a genuine edge exists somewhere in the 177 strategies** — the data as published cannot answer this, because the denominator, the labeling, and the trial count are all corrupt. That is precisely what C1–C3 are for.
- **Multi-AI review** — the cloud consult presets are broken (retired model IDs: 404/410/402), so the plan is my synthesis plus the cited literature, not a consensus of external models. The one local 14B consult produced generic advice and is not relied upon.
