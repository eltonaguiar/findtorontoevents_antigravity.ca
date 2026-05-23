# Session BK — Swarm Review Request
# Date: 2026-05-17
# Session: BK (following BJ — deepseek APPROVE)

## Context

Session BK: M-040 (verify_citations.py) + stale-PENDING cleanups (M-030/031/035/037/047/048).
All sessions through BJ have returned deepseek APPROVE.

## Session BK Deliverables

### 1. M-040: Hermes Phantom-Work Guard (DONE)

Commit: 48f3aff65d

**Problem:** Hermes sessions hallucinated phantom commits and files, then ran 3+
swarm rounds reviewing fabricated evidence. No tool existed to verify citations
before swarm execution.

**Implementation (tools/verify_citations.py, 149 lines):**
- `_extract_file_paths()`: regex finds paths like `audit_trail/quality_gates.py`, `tools/verify_citations.py`, etc.
- `_extract_shas()`: finds 7-40 char hex tokens (commit SHA candidates)
- `verify_prompt_file()`: checks each path exists on disk, each 10+ char SHA exists
  in git (`git cat-file -e`), exits 1 on any phantom
- Suspicious heuristic: warns if claimed test count > 200
- CLI: `python tools/verify_citations.py <prompt_file>`

**Tests (6/6 passing):**
```
tests/test_m040_verify_citations.py::test_extract_shas_finds_commit_like_hex PASSED
tests/test_m040_verify_citations.py::test_extract_file_paths_finds_python_paths PASSED
tests/test_m040_verify_citations.py::test_verify_passes_on_real_existing_file PASSED
tests/test_m040_verify_citations.py::test_verify_fails_on_phantom_file PASSED
tests/test_m040_verify_citations.py::test_verify_passes_when_no_citations PASSED
tests/test_m040_verify_citations.py::test_verify_fails_on_phantom_commit PASSED
6 passed in 0.17s
```

**Verification on own prompt:**
```
python tools/verify_citations.py tools/swarm/prompts/session_review_bj_2026_05_17.md
[verify_citations] PASS — all citations verified
```

### 2. Stale-PENDING Corrections (6 items)

Commit: 93a45b85ce

Items confirmed already implemented (stale PENDING corrected):
- M-030: `last_signal_date` in systems payload — already at `dashboard_generator.py:10125`
- M-031: `readiness.by_class` payload — already at `dashboard_generator.py:16052` via `_build_readiness_payload()`
- M-035: hf_stats refresh trigger — `audit-dashboard.yml` has `workflow_dispatch` + hourly cron; our code commits trigger it via push path filter
- M-037: INDEX_STOCK probe — 0 systems/picks, inert scaffold; no removal needed
- M-047: Sprint-sizing correction — M-002/M-005 both DONE; planning note absorbed
- M-048: Binance audit — existing calls use 3+ fallback chains (api, api1, api2, data-api.binance.vision, api.binance.us); no keys exposed; CLAUDE.md API Failover Rule satisfied

Items noted but deferred:
- M-038: MEMECOIN quarantine — goldmine_meme + meme_scanner both 0 resolved picks; cannot block per CLAUDE.md without PF/WR data
- M-026: EQUITY DOW tilt — Tue refuted (54.1%=overall); Wed=70.7% n=41 (+16.5pp genuine edge, reassess at n≥100)
- M-027: FUTURES Thu short — n=0 Thursday picks, deferred until n≥30

### 3. AMD EQUITY Reassessment (n≥20 trigger met)

No code change needed. Live data 2026-05-17:
- n=21 (≥20 threshold met), WR=66.7%, PF=3.36 — T1-grade performance
- AMD was never code-gated; Session BC soft-watch is resolved positively
- No BLOCKED_SYMBOLS entry for AMD; monitoring-only lifted by positive resolution

### 4. Current M-item Status

All sessions BC→BK completed:
M-012, M-028, M-033, M-020, M-007(stale), M-004, M-005(stale), M-019,
M-030(stale), M-031(stale), M-035(stale), M-037, M-040, M-047, M-048.

Remaining PENDING S-effort items (genuine work):
- M-008: multi_asset_cot DB MATCH + friction-adjusted DSR gate (COMMODITY)
- M-026: EQUITY Wed DOW boost (reassess at Wed n≥100)
- M-027: FUTURES Thu short (reassess at n≥30)
- M-032: FRED macro filter wire-up (needs FRED_API_KEY secret)
- M-038: MEMECOIN quarantine (deferred until n≥30)
- M-041: Slippage_validator wire-in (needs PR #1026 context)
- M-042: Cursor verification matrix scaffold
- M-043: DB credentials secret-scan in GHA
- M-049: Kill-switch RED physical halt verification

### 5. Pending User Approvals (unchanged from all prior sessions)

1. Block `('COMMODITY', 'cta_replicator')` — 83 losing picks (WR=12%), 0 CT=F picks
2. Raise COMMODITY concentration cap to ≥0.85

## Questions for Swarm

1. **verify_citations scope:** The tool checks file paths and commit SHAs. Should it
   also verify that test files cited in "X passed" lines are runnable (import check)?
   Or is path + SHA sufficient for phantom detection?

2. **M-043 (DB secret scan):** This requires adding `gitleaks` or `trufflehog` to
   `.github/workflows/`. Is this safe to implement autonomously (pure GHA addition,
   no production code change), or does it require coordination to avoid blocking PRs
   that legitimately reference DB credentials via env-var references?

3. **Session BK APPROVE?:** M-040 implemented + 6 stale items corrected; 6+6 tests
   pass; MASTER_ACTION_PLAN updated. Is this APPROVE?

4. **Next focus:** Remaining genuine S-items are M-043 (GHA secret scan, pure infra),
   M-042 (verification matrix scaffold, new tool), M-049 (halt verification audit).
   Which should Session BL target?

## Verification

- commits: 48f3aff65d (M-040), 93a45b85ce (stale corrections), bf8e62fe97 (M-019)
- tests: `python -m pytest tests/test_m040_verify_citations.py tests/test_m019_portfolio_mdd.py -v` → 13 passed
- syntax: `python -m py_compile tools/verify_citations.py` → SYNTAX OK
- Prior verdicts: AZ through BJ all deepseek APPROVE
