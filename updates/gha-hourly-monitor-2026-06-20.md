# GHA Hourly Health Monitor — 2026-06-20

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 30 on main):** 0 success, 30 failure, 0 in_progress

**Chronic workflows:** none (sports-smoke-and-e2e is GREEN: 15/15 successes in last 15 runs; 2 isolated cancels on 2026-06-18/19 do not meet chronic threshold)

**Open PRs RED:** All 7 open PRs (#562, #564, #577, #581, #594, #595, #600) share the same failing main branch — all have red CI.

**Action required:** AUTHOR FIX — `passes_active_gate()` regression is blocking all picks (returns `False` for every pick that should pass). Regression has been live for 34+ hours (first failure: 2026-06-19T02:54Z). Operator must diagnose and fix `alpha_engine/` gate logic ASAP. See failing run: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/27871725655

---

### Failure Detail

- **Run ID:** 27871725655
- **Triggered:** 2026-06-20T12:51:39Z on `main` (SHA `5b1c130f`)
- **Failing step (both Python 3.11 + 3.12):** `Run all tests (gating — known-drift quarantined)` (step 8)
- **Regression onset:** ~2026-06-19T02:54Z — 30 consecutive failures since then

**Root cause pattern:** `passes_active_gate()` returns `False` for virtually all picks that should pass. Observed across **10+ test files, 60+ test cases**.

Key failing assertions (representative sample):
```
FAILED tests/test_phase1_active_gates.py::Phase1DeadZoneGateTests::test_high_conf_crypto_passes
  — AssertionError: False is not true
FAILED tests/test_quality_gates.py::test_active_gate_rejects_exempt_safety_mode
  — AssertionError: baseline ml_enhanced pick should pass (sanity)
FAILED tests/test_crypto_gates_p0.py::TestM037CryptoMlScoreFloor::test_ml_score_above_floor_passes
  — AssertionError: assert False is True  (where False = passes_active_gate({...CRYPTO LONG...}))
FAILED tests/test_hf_quality_gate_wire.py::test_hf_on_rejects_banned_symbol
  — AssertionError: assert 'DOGEUSDT' in ''  (reason string is empty — gate not running)
FAILED tests/test_m097_book_direction_conflict.py::TestM097BookDirectionConflict::test_enforce_allows_when_higher_confidence
  — AssertionError: Enforce mode must allow LONG with conf=0.85 > existing SHORT conf=0.50
FAILED tests/test_p1_gates_etf_tight_crypto_consensus.py::test_crypto_consensus_forward_bypass_exempts_proven_strategies
  — AssertionError: forward bypass not firing
```

Secondary observation: coverage report emits `Couldn't parse 'alpha_engine/backtest_quant_algorithms.py' as Python source: 'invalid syntax' at line 1` — possible related syntax error in that file.

**Most recently merged PR at failure time:** #621 (merged 2026-06-19T21:10Z) — CI was already broken when it merged.

**Failing run URL:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/27871725655/job/82484592516

---

### Secondary Workflow Alert

- **`alpha-engine-live.yml`** (not a CI gate): 1 failure at 2026-06-20T13:05Z (run 27872051765). Not chronic; likely a transient live-engine error. Monitor for repeat.

---

### Workflow Health Summary

| Workflow | Recent status |
|---|---|
| CI Tests | 🔴 30/30 failures (34+ h streak) |
| Sports endpoint smoke + Playwright | 🟢 15/15 successes |
| alpha-engine-live.yml | ⚠️ 1 failure (transient, monitor) |
| All other ~28 sampled workflows | 🟢 success |
