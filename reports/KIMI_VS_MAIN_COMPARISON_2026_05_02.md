# Kimi Uplift vs Main — Head-to-Head Comparison
**Date:** 2026-05-02
**Scope:** `reports/kimi_uplift_2026_05_02/pr_files/` vs already-merged main (PR #626 / #610)
**Method:** Read-only diff + correctness audit + test execution

---

## Executive Verdict

| Module | Verdict | Confidence |
|---|---|---|
| `statistical_rigor.py` | **KEEP-MAIN** (with cherry-pick of DSR + Acklam PPF) | HIGH |
| `hrp_allocator.py` | **KEEP-MAIN** | HIGH |
| `decay_tracker.py` | **KEEP-MAIN** | HIGH |
| 8 researcher personas | **KEEP-MAIN** | MEDIUM |
| Kimi's "9 bug fixes" claim | **~90% overlap with already-merged PR #610** | HIGH |

Main passes 20/20 unit tests (`tests/test_statistical_rigor.py`, `test_hrp_allocator.py`, `test_decay_and_reconciliation.py`) in 1.34s. Kimi ships **0 unit tests** (only `multiple_testing_researcher.py` mentions tests; none included).

---

## 1. Algorithmic Correctness

### Holm monotonicity bug (Codex bot's PR #621 finding)

- **Main:** Implements **only BH-FDR step-up**, no Holm function exists. Cannot have the bug. (`benjamini_hochberg`, lines 188-220, sorts p-values then finds largest k satisfying `p_(k) ≤ k/N · α` — textbook correct.)
- **Kimi:** Same. Implements `benjamini_hochberg_fdr` (lines 385-462) using sort-rank approach. Adds q-value computation. **Holm is absent in both — Codex's bug is from a different file (`audit_trail/statistical_rigor.py` in PR #621), not relevant here.**

### Bigger correctness flaw in Kimi's `bootstrap_ci` (NEW FINDING)

Kimi's `bootstrap_ci` (lines 54-114) hard-codes `boot_means[i] = sample.mean()`. The function name and docstring promise "any scalar metric" CIs, but it **only ever bootstraps the sample mean.** Calling `bootstrap_ci(returns)` to get a Profit Factor or Sharpe CI silently returns the mean's CI. This is a runtime-silent bug.

Main's `bootstrap_ci` accepts a `metric: Callable` arg (line 126) and applies it to each resample (line 167). Used correctly for PF/WR/Sharpe in `audit_metrics_block` (lines 305-317).

### Kimi's `compute_decay_ratio` time-window bug (NEW FINDING)

Kimi takes "last N observations" via `returns.iloc[-short_window:]` (line 156) — counts **trades**, not days, despite parameter name `short_window: int = 90` documented as "rolling window in days". A source with 200 trades/day collapses 90 days to ~10 hours of data. Main's `compute_decay_blocks` correctly time-buckets via `datetime` filtering (lines 105-128).

### Kimi `_empty_decay_result` returns `decay_ratio=1.0` for missing data (NEW FINDING)

Lines 480-489: any source with insufficient data is reported as `decay_ratio=1.0` ("healthy"). Silent false negative — decayed sources with sparse data look fine. Main returns explicit `status="insufficient"` with `ratio=None`.

### Kimi `detect_regime_change(method='hmm')` is a placeholder

Line 244: `# Placeholder: fall back to threshold method until hmmlearn is wired`. The "HMM" arg silently downgrades to a 4-quadrant vol/drift threshold classifier. Docstring claims HMM but doesn't deliver.

---

## 2. Bloat vs Substance

| Module | Main LOC | Kimi LOC | Substance Verdict |
|---|---|---|---|
| `statistical_rigor` | 337 | 537 | Kimi adds (a) genuine `deflated_sharpe_ratio` (~80 LOC), (b) `block_bootstrap_ci` (~75 LOC), (c) Acklam's `_norm_ppf` approximation (~60 LOC). These are useful additions. Rest is verbose docs. |
| `hrp_allocator` | 290 | 493 | Kimi adds `sharpe_equalized_sizing` (~50 LOC) and `hrp_allocate_by_sharpe` JSON-loading convenience (~70 LOC). However, Kimi requires `scipy.cluster.hierarchy` while main uses pure-numpy single-linkage (better for minimal CI). Net wash. |
| `decay_tracker` | 167 | 489 | Kimi adds broken-by-design `compute_decay_ratio`, fake-HMM `detect_regime_change`, `plot_decay_dashboard`, `demotion_recommendation`. The extra surface area is buggy or stub-grade. **Actively worse.** |
| Personas (avg) | ~92 | ~136 | Kimi versions are ~50% longer mostly via additional `__init__` config + verbose docstrings. Same `Researcher` interface from `base.py`. |

---

## 3. Test Coverage

```
$ pytest tests/test_statistical_rigor.py tests/test_hrp_allocator.py \
        tests/test_decay_and_reconciliation.py
============================= 20 passed in 1.34s ==============================
```

Main: **20 tests, 100% pass**. Kimi: **0 tests** in `pr_files/`.

---

## 4. Researcher Persona Quality

8/8 researcher names overlap exactly. Diff confirms files differ but interface (`Researcher` from `base.py`) is identical. Main's versions are concrete subclasses with `wire_target` strings naming production callers (per PR #626 description). Kimi's are longer but functionally equivalent stubs — no obviously superior algorithm in either.

No reason to swap; KEEP-MAIN.

---

## 5. Wire-Up Rule Compliance

- **Main:** PR #626 lists `wire_target` per persona; modules are explicit opt-in sidecar with Wiring Plan in PR body. Compliant.
- **Kimi:** `HEDGE_FUND_UPLIFT_2026_05_02.md` §3 has a 4-phase Wiring Plan naming exact target functions (`audit_trail.metrics.compute_summary`, `anti_overfit_gate.passed_dsr_check`, etc.). **Also compliant** — actually slightly more specific than main's.

Tie. No swap signal here.

---

## 6. Kimi's "9 critical bugs" vs PR #610

PR #610 (MERGED 2026-05-02) shipped resolver v2.1 fixing exactly **3 bugs**: 1A (breakeven retry loop), 1B (empty `ohlc_window=[]` falsy), 1D (yfinance no-timeout — cross-platform via `ThreadPoolExecutor`, NOT Kimi's Unix-only `signal.alarm` which would crash Windows).

Mapping Kimi's 9 → PR #610:

| Kimi # | Bug | In PR #610? | Notes |
|---|---|---|---|
| 1 | Infinite retry loop | YES (= 1A) | Main uses `MAX_RESOLVE_RETRIES=3` exactly as Kimi proposes |
| 2 | Lookahead bias entry-day | NO — but unverified claim, no test in Kimi |
| 3 | Empty OHLC `[]` falsy | YES (= 1B) | Identical fix |
| 4 | yfinance hang | YES (= 1D) — but **PR #610's fix is superior** (cross-platform). Kimi's `signal.alarm(15)` would break Windows operator |
| 5 | Breakeven status `None` | Partial — PR #610 sets `status="FLAT"` after retry cap |
| 6 | 5bp floor misclassification | NO — config change, not in #610 |
| 7 | Active pick zombie loop | YES — same as 1A (deduplicated by PR #610) |
| 8 | Asset-class threshold map | NO — already addressed by `outcome_resolver.py:97` `PNL_WIN_THRESHOLD` (per CLAUDE.md) |
| 9 | Retry counting metadata | YES — PR #610 adds `_resolve_max_retries_hit` flag |

**~6/9 already in PR #610**; bug 4 has a **regression risk** (Kimi's `signal.alarm` is Unix-only); bugs 2, 6, 8 are config/policy claims, not code-verified, no tests. Kimi's "9 bugs" framing inflates 3 distinct fixes.

---

## 7. Codex bot atr_adaptive_stops NameError (PR #621:188)

Kimi does not ship `atr_adaptive_stops.py`. Not relevant.

---

## Per-Module Verdict

### `statistical_rigor.py` → **KEEP-MAIN**, optionally cherry-pick DSR
**Why:** Kimi's `bootstrap_ci` is broken (mean-only despite docstring promise). Main's metric-callable design is correct and tested (10 unit tests). However, Kimi's `deflated_sharpe_ratio` (with Acklam PPF) is genuinely useful and absent from main — worth a follow-up cherry-pick PR adding `dsr` + `_norm_ppf` only.

### `hrp_allocator.py` → **KEEP-MAIN**
**Why:** Both implementations are correct. Main uses pure-numpy single-linkage (no scipy needed for minimal CI), has 5 tests passing, and is aligned with main's "pure-Python fallbacks" design philosophy from `statistical_rigor.py`. Kimi's `sharpe_equalized_sizing` helper is trivial enough to add to main as a 10-line helper if needed.

### `decay_tracker.py` → **KEEP-MAIN** (Kimi version is buggy)
**Why:** Kimi has the time-window-as-trade-count bug (line 156), the `decay_ratio=1.0` silent-healthy fallback (line 483), and a fake-HMM placeholder. Main's time-bucketed `compute_decay_blocks` is correct, tested (5 tests), and explicitly returns `status="insufficient"` rather than masking sparse data.

### 8 researcher personas → **KEEP-MAIN**
**Why:** Functionally equivalent stubs with same interface. Kimi adds verbosity, not capability. PR #626 already integrated main's versions with explicit `wire_target` fields naming production callers.

---

## Overall Assessment of Kimi PR

**90%+ overlap with already-merged work, plus introduces 3 net-new bugs.** The Kimi PR was a parallel-but-late effort that:

- Duplicates PR #626 (`alpha_engine/statistical_rigor.py`, `hrp_allocator.py`, `decay_tracker.py`, 8 personas) — main has tests, Kimi has none.
- Duplicates PR #610 resolver fixes — main has cross-platform yfinance timeout + 38 tests; Kimi proposes Unix-only `signal.alarm` which would break the Windows operator.
- Introduces 3 algorithmic regressions (mean-only bootstrap, trade-count-as-days decay window, silent-healthy missing-data fallback).

**Recommended action:** Reject swap. File a small follow-up to cherry-pick Kimi's `deflated_sharpe_ratio` function (the one genuinely useful addition) into `alpha_engine/statistical_rigor.py` with its own unit test. Discard the rest.

---

## Files Referenced

- `e:/findtorontoevents_antigravity.ca/alpha_engine/statistical_rigor.py` (main, 337 LOC, 10 tests)
- `e:/findtorontoevents_antigravity.ca/alpha_engine/hrp_allocator.py` (main, 290 LOC, 5 tests)
- `e:/findtorontoevents_antigravity.ca/alpha_engine/decay_tracker.py` (main, 167 LOC, 5 tests)
- `e:/findtorontoevents_antigravity.ca/reports/kimi_uplift_2026_05_02/pr_files/alpha_engine/{statistical_rigor,hrp_allocator,decay_tracker}.py`
- `e:/findtorontoevents_antigravity.ca/tests/test_statistical_rigor.py`
- `e:/findtorontoevents_antigravity.ca/tests/test_hrp_allocator.py`
- `e:/findtorontoevents_antigravity.ca/tests/test_decay_and_reconciliation.py`
- GitHub PR #610 (resolver v2.1, MERGED) — supersedes Kimi bugs 1, 3, 4, 7, 9
- GitHub PR #626 (uplift foundation, MERGED) — supersedes Kimi modules + personas
- GitHub PR #621 (CLOSED) — Codex bot's Holm/NameError findings, both moot for Kimi PR

*Document version: 1.0 — Read-only audit, no code modified.*
