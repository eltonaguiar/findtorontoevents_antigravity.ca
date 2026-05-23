## Review: REQUEST CHANGES

This PR bundles multiple unrelated concerns and introduces regressions. While the `outcome_resolver.py` v2.1 retry-cap logic is well-designed, it does not belong in a PR titled "resolve 5 scanner blockers." Below are specific line-level issues and action items.

### Critical regressions

**`alpha_engine/production_scanner.py` (line ~30)** — The `__builtins__.print = print` pattern is broken in CPython test context where `__builtins__` is a `dict`, not a module. This causes:
```
AttributeError: 'dict' object has no attribute 'print'
```
in `tests/test_production_scanner_failover.py` (8 failures). **Fix:** `import builtins; builtins.print = print`.

**`alpha_engine/production_scanner.py` (line ~26)** — The tee-to-log branch is unreachable because `kwargs["file"]` is unconditionally set to `sys.stdout` on line 20, making the `if _log_file is not None and "file" not in kwargs` check always false. Local runs never mirror to `scanner_lifecycle.log`.

### Test failures
- **8 failures** from the `__builtins__.print` regression (see above).
- **2 failures** in `tests/test_quality_gates.py::test_normalize_exit_reason_*` because this branch is behind `main` where PR #617 changed `normalize_exit_reason` behavior. **Action:** rebase on `origin/main` and update expectations.

### Circuit breaker reset is a safety risk
**`alpha_engine/data/circuit_breaker.json`** — Changing `status` from `EMERGENCY` to `NORMAL` while `total_drawdown_pct` reads **-25,465.5%** is not a fix; it is a bypass. A -25,465% drawdown is physically impossible in any conventionally leveraged account and indicates either a catastrophic calculation bug or fabricated data. Per Issue #623 (opened by the same author), the correct path is:
1. Recompute `total_drawdown_pct` using post-#497 `_daily_loss` logic.
2. Only then flip `status` to `NORMAL` with an accurate baseline.
**Action:** revert this file change from the PR; ship CB reset separately after recomputation.

### yfinance timeout does not bound runtime
**`alpha_engine/outcome_resolver.py` (~line 350)** — `ThreadPoolExecutor(max_workers=1)` with `future.result(timeout=15)` raises `TimeoutError` after 15 s, but exiting the `with` block triggers `shutdown(wait=True)`, which waits for the stuck `yf.Ticker.history()` thread to finish. In practice the resolver batch can still stall. **Fix:** use `shutdown(wait=False)` or switch to `threading.Thread(daemon=True)`.

### Scope / decomposition
- The PR body says "stdout fix only" but ships +119/-19 in `outcome_resolver.py` (resolver v2.1). That work belongs in PR #610 (already in flight).
- The +227-line new test file also belongs with resolver work, not scanner fixes.
- The claimed "earnings dict bug" fix references `scripts/alpha_refresh.py`, which **does not exist** in this repo or in the PR diff.

### Recommended split
1. **PR-a (scanner stdout only):** Keep `inverse_edge_system.py` and `cta_strategy_replicator.py` try/except wraps; fix `builtins.print` in `production_scanner.py`; fix log-tee reachability. Small, surgical, mergeable.
2. **PR-b (resolver v2.1):** Cherry-pick `outcome_resolver.py` + tests into PR #610 (or close as duplicate).
3. **Drop** `circuit_breaker.json` reset from code PRs; handle as operator runbook action after Issue #623 SLA.

### Fabrication risk note
The -25,465.5% drawdown figure in `circuit_breaker.json` is unsourced and physically impossible. Treat this as a data-integrity violation requiring audit before any reset.

**Verdict:** 🛑 REQUEST CHANGES. Do not merge until the dict-print regression is fixed, branch is rebased on main, and the circuit breaker reset is removed or justified with recomputed drawdown.
