# GitHub Actions Curated Job Log Review

**Mode: STRICT** — only failed/cancelled/timed_out jobs reported.

Generated: 2026-05-29 06:45 UTC
Repository: eltonaguiar/findtorontoevents_antigravity.ca
Branch: main
Workflows reviewed: 40
Jobs with signals: 8 (STRICT mode)

## Curated Analysis (swarm_v2)

## Top Failing Jobs

1. **CI Tests / test (3.11)** – [Run 26621565175](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26621565175) – 13 test failures
2. **CI Tests / test (3.11)** – [Run 26621503772](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26621503772) – 12 test failures
3. **CI Tests / test (3.12)** – [Run 26621485029](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26621485029) – 12 test failures
4. **CI Tests / test (3.12)** – [Run 26621503772](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26621503772) – 12 test failures (cancelled)
5. **CI Tests / test (3.12)** – [Run 26621565175](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26621565175) – 12 test failures (cancelled)
6. **CI Tests / test (3.11)** – [Run 26621485029](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26621485029) – 12 test failures (cancelled)
7. **Mercury 2 Signal Scanner / scan** – [Run 26620934466](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26620934466) – Process exited with code 1
8. **DNA Mutation Cycle / mutation-cycle** – [Run 26621843862](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26621843862) – Process exited with code 1

## Repeated Error Themes

- **`test_m096_ctf_concentration_cap.py`** – All 4 tests failing consistently across all CI runs (test_ctf_passes_when_below_cap, test_non_ctf_symbol_unaffected, test_fail_open_when_no_data, test_skip_when_fewer_than_5_commodity_picks)
- **`test_m098_etf_vix_gate.py`** – All 4 tests failing consistently across all CI runs (test_shadow_stamps_when_vix_above_threshold, test_custom_threshold, test_disabled_gate_skips_check, test_e006_exception_log_written)
- **`test_outcome_resolver_noncrypto.py`** – TestTimeExitV22 tests failing across all runs (test_long_time_exit_resolves_at_last_close, test_short_time_exit_loss)
- **`test_hf_conviction_tier.py`** – test_tier_b_major failing in 4 of 6 CI runs
- **`test_pr_triage_2026_04_25_merge_success.py`** – Test391_CIStashFix::test_strategy_performance_json_is_tracked failing in 2 runs
- **`test_equity_pead_strategy.py`** – TestPEADGate::test_gate_off_by_default failing in 2 runs (Python 3.12 only)

## High-Noise Warnings to Deprioritize

- `warnings.warn(` – Generic Python deprecation warnings, no actionable context
- `if-no-files-found: warn` – Upload steps for test-results.xml and coverage.xml; expected when tests fail early
- `##[warning]No files were found with the provided path: coverage.xml` – Artifact upload warning, not a test issue
- `##[warning]No files were found with the provided path: test-results.xml` – Artifact upload warning, not a test issue
- `##[warning]Node.js 20 actions are deprecated...` – Infrastructure deprecation notice for actions/cache@v4 and actions/upload-artifact@v4; deadline June 2, 2026

## Quick Fix Queue

- Investigate `test_m096_ctf_concentration_cap.py` – all 4 tests failing across all Python versions; likely a shared dependency or data issue
- Investigate `test_m098_etf_vix_gate.py` – all 4 tests failing across all Python versions; likely a shared dependency or data issue
- Investigate `test_outcome_resolver_noncrypto.py` – TestTimeExitV22 tests failing across all runs
- Investigate `test_hf_conviction_tier.py::test_tier_b_major` – failing in 4 of 6 runs
- Investigate `test_equity_pead_strategy.py::TestPEADGate::test_gate_off_by_default` – failing in Python 3.12 only
- Investigate `test_pr_triage_2026_04_25_merge_success.py::Test391_CIStashFix::test_strategy_performance_json_is_tracked` – failing in 2 runs
- Investigate **Mercury 2 Signal Scanner** exit code 1 – no error details provided beyond process failure
- Investigate **DNA Mutation Cycle** exit code 1 – commit mutation data step failing
- Update `actions/cache` and `actions/upload-artifact` to Node.js 24-compatible versions before June 2, 2026 deadline
- Add `coverage.xml` generation step or remove upload step to eliminate `if-no-files-found` warnings

## Top Job Findings

| Rank | Workflow | Job | Conclusion | Error lines | Warning lines | Run | Job |
|---:|---|---|---|---:|---:|---|---|
| 1 | CI Tests | test (3.11) | failure | 12 | 7 | [run 26621565175](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26621565175) | [job 78450136885](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26621565175/job/78450136885) |
| 2 | CI Tests | test (3.11) | failure | 12 | 7 | [run 26621503772](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26621503772) | [job 78448301815](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26621503772/job/78448301815) |
| 3 | CI Tests | test (3.12) | failure | 12 | 7 | [run 26621485029](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26621485029) | [job 78448239056](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26621485029/job/78448239056) |
| 4 | CI Tests | test (3.12) | cancelled | 12 | 7 | [run 26621503772](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26621503772) | [job 78448301805](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26621503772/job/78448301805) |
| 5 | CI Tests | test (3.12) | cancelled | 12 | 5 | [run 26621565175](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26621565175) | [job 78450136893](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26621565175/job/78450136893) |
| 6 | CI Tests | test (3.11) | cancelled | 12 | 5 | [run 26621485029](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26621485029) | [job 78448239027](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26621485029/job/78448239027) |
| 7 | Mercury 2  Signal Scanner | scan | failure | 7 | 0 | [run 26620934466](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26620934466) | [job 78450138185](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26620934466/job/78450138185) |
| 8 | DNA Mutation Cycle | mutation-cycle | failure | 1 | 0 | [run 26621843862](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26621843862) | [job 78450134390](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26621843862/job/78450134390) |

## Error And Warning Excerpts

### CI Tests :: test (3.11) :: run 26621565175

Errors:
- test (3.11) Run dashboard card-metrics JS guard 2026-05-29T06:33:07.7894644Z 14 passed, 0 failed.
- test (3.11) Run all tests 2026-05-29T06:34:56.1731923Z tests/test_m096_ctf_concentration_cap.py::TestM096CTFConcentrationCap::test_ctf_passes_when_below_cap FAILED [ 55%]
- test (3.11) Run all tests 2026-05-29T06:34:56.1863668Z tests/test_m096_ctf_concentration_cap.py::TestM096CTFConcentrationCap::test_non_ctf_symbol_unaffected FAILED [ 55%]
- test (3.11) Run all tests 2026-05-29T06:34:56.1982519Z tests/test_m096_ctf_concentration_cap.py::TestM096CTFConcentrationCap::test_fail_open_when_no_data FAILED [ 55%]
- test (3.11) Run all tests 2026-05-29T06:34:56.2102896Z tests/test_m096_ctf_concentration_cap.py::TestM096CTFConcentrationCap::test_skip_when_fewer_than_5_commodity_picks FAILED [ 55%]
- test (3.11) Run all tests 2026-05-29T06:34:56.2583221Z tests/test_m098_etf_vix_gate.py::TestM098ETFVixGate::test_shadow_stamps_when_vix_above_threshold FAILED [ 55%]
- test (3.11) Run all tests 2026-05-29T06:34:56.2776209Z tests/test_m098_etf_vix_gate.py::TestM098ETFVixGate::test_custom_threshold FAILED [ 55%]
- test (3.11) Run all tests 2026-05-29T06:34:56.2938510Z tests/test_m098_etf_vix_gate.py::TestM098ETFVixGate::test_disabled_gate_skips_check FAILED [ 55%]
- test (3.11) Run all tests 2026-05-29T06:34:56.3160193Z tests/test_m098_etf_vix_gate.py::TestM098ETFVixGate::test_e006_exception_log_written FAILED [ 55%]
- test (3.11) Run all tests 2026-05-29T06:34:59.9013650Z tests/test_outcome_resolver_noncrypto.py::TestTimeExitV22::test_long_time_exit_resolves_at_last_close FAILED [ 63%]
- test (3.11) Run all tests 2026-05-29T06:34:59.9112804Z tests/test_outcome_resolver_noncrypto.py::TestTimeExitV22::test_short_time_exit_loss FAILED [ 63%]
- test (3.11) Run all tests 2026-05-29T06:35:05.1512287Z tests/test_pr_triage_2026_04_25_merge_success.py::Test391_CIStashFix::test_strategy_performance_json_is_tracked FAILED [ 68%]
Warnings:
- test (3.11) Run all tests 2026-05-29T06:35:33.0301108Z warnings.warn(
- test (3.11) Run all tests 2026-05-29T06:35:33.0304318Z warnings.warn(
- test (3.11) Run all tests 2026-05-29T06:35:33.0307399Z warnings.warn(
- test (3.11) Upload test results 2026-05-29T06:35:35.0274211Z if-no-files-found: warn
- test (3.11) Upload coverage report 2026-05-29T06:35:35.7763770Z if-no-files-found: warn
- test (3.11) Upload coverage report 2026-05-29T06:35:35.9909547Z ##[warning]No files were found with the provided path: coverage.xml. No artifacts will be uploaded.
- test (3.11) Complete job 2026-05-29T06:35:37.8411824Z ##[warning]Node.js 20 actions are deprecated. The following actions are running on Node.js 20 and may not work as expected: actions/cache@v4, actions/upload-artifact@v4. Actions will be forced to run with Node.js 24 by default starting June 2nd, 2026. Node.js 20 will be removed from the runner on September 16th, 2026. Please check if updated versions of these actions are available that support Node.js 24. To opt into Node.js 24 now, set the F...

### CI Tests :: test (3.11) :: run 26621503772

Errors:
- test (3.11) Run dashboard card-metrics JS guard 2026-05-29T06:17:22.4875663Z 14 passed, 0 failed.
- test (3.11) Run all tests 2026-05-29T06:19:02.6172307Z tests/test_hf_conviction_tier.py::test_tier_b_major FAILED [ 45%]
- test (3.11) Run all tests 2026-05-29T06:19:05.5292128Z tests/test_m096_ctf_concentration_cap.py::TestM096CTFConcentrationCap::test_ctf_passes_when_below_cap FAILED [ 55%]
- test (3.11) Run all tests 2026-05-29T06:19:05.5408828Z tests/test_m096_ctf_concentration_cap.py::TestM096CTFConcentrationCap::test_non_ctf_symbol_unaffected FAILED [ 55%]
- test (3.11) Run all tests 2026-05-29T06:19:05.5527249Z tests/test_m096_ctf_concentration_cap.py::TestM096CTFConcentrationCap::test_fail_open_when_no_data FAILED [ 55%]
- test (3.11) Run all tests 2026-05-29T06:19:05.5646065Z tests/test_m096_ctf_concentration_cap.py::TestM096CTFConcentrationCap::test_skip_when_fewer_than_5_commodity_picks FAILED [ 55%]
- test (3.11) Run all tests 2026-05-29T06:19:05.6130547Z tests/test_m098_etf_vix_gate.py::TestM098ETFVixGate::test_shadow_stamps_when_vix_above_threshold FAILED [ 55%]
- test (3.11) Run all tests 2026-05-29T06:19:05.6333995Z tests/test_m098_etf_vix_gate.py::TestM098ETFVixGate::test_custom_threshold FAILED [ 55%]
- test (3.11) Run all tests 2026-05-29T06:19:05.6509434Z tests/test_m098_etf_vix_gate.py::TestM098ETFVixGate::test_disabled_gate_skips_check FAILED [ 55%]
- test (3.11) Run all tests 2026-05-29T06:19:05.6734432Z tests/test_m098_etf_vix_gate.py::TestM098ETFVixGate::test_e006_exception_log_written FAILED [ 55%]
- test (3.11) Run all tests 2026-05-29T06:19:08.8748799Z tests/test_outcome_resolver_noncrypto.py::TestTimeExitV22::test_long_time_exit_resolves_at_last_close FAILED [ 63%]
- test (3.11) Run all tests 2026-05-29T06:19:08.8845065Z tests/test_outcome_resolver_noncrypto.py::TestTimeExitV22::test_short_time_exit_loss FAILED [ 63%]
Warnings:
- test (3.11) Run all tests 2026-05-29T06:23:36.0473367Z warnings.warn(
- test (3.11) Run all tests 2026-05-29T06:23:36.0479081Z warnings.warn(
- test (3.11) Run all tests 2026-05-29T06:23:36.0482436Z warnings.warn(
- test (3.11) Upload test results 2026-05-29T06:23:38.4737122Z if-no-files-found: warn
- test (3.11) Upload coverage report 2026-05-29T06:23:39.0448034Z if-no-files-found: warn
- test (3.11) Upload coverage report 2026-05-29T06:23:39.2573314Z ##[warning]No files were found with the provided path: coverage.xml. No artifacts will be uploaded.
- test (3.11) Complete job 2026-05-29T06:23:41.0654180Z ##[warning]Node.js 20 actions are deprecated. The following actions are running on Node.js 20 and may not work as expected: actions/cache@v4, actions/upload-artifact@v4. Actions will be forced to run with Node.js 24 by default starting June 2nd, 2026. Node.js 20 will be removed from the runner on September 16th, 2026. Please check if updated versions of these actions are available that support Node.js 24. To opt into Node.js 24 now, set the F...

### CI Tests :: test (3.12) :: run 26621485029

Errors:
- test (3.12) Run dashboard card-metrics JS guard 2026-05-29T06:16:52.8673010Z 14 passed, 0 failed.
- test (3.12) Run all tests 2026-05-29T06:18:35.5145144Z tests/test_equity_pead_strategy.py::TestPEADGate::test_gate_off_by_default FAILED [ 34%]
- test (3.12) Run all tests 2026-05-29T06:18:43.3667957Z tests/test_hf_conviction_tier.py::test_tier_b_major FAILED [ 45%]
- test (3.12) Run all tests 2026-05-29T06:18:49.8035715Z tests/test_m096_ctf_concentration_cap.py::TestM096CTFConcentrationCap::test_ctf_passes_when_below_cap FAILED [ 55%]
- test (3.12) Run all tests 2026-05-29T06:18:49.8506251Z tests/test_m096_ctf_concentration_cap.py::TestM096CTFConcentrationCap::test_non_ctf_symbol_unaffected FAILED [ 55%]
- test (3.12) Run all tests 2026-05-29T06:18:49.8884863Z tests/test_m096_ctf_concentration_cap.py::TestM096CTFConcentrationCap::test_fail_open_when_no_data FAILED [ 55%]
- test (3.12) Run all tests 2026-05-29T06:18:49.9327485Z tests/test_m096_ctf_concentration_cap.py::TestM096CTFConcentrationCap::test_skip_when_fewer_than_5_commodity_picks FAILED [ 55%]
- test (3.12) Run all tests 2026-05-29T06:18:50.1231193Z tests/test_m098_etf_vix_gate.py::TestM098ETFVixGate::test_shadow_stamps_when_vix_above_threshold FAILED [ 55%]
- test (3.12) Run all tests 2026-05-29T06:18:50.1682896Z tests/test_m098_etf_vix_gate.py::TestM098ETFVixGate::test_custom_threshold FAILED [ 55%]
- test (3.12) Run all tests 2026-05-29T06:18:50.2825712Z tests/test_m098_etf_vix_gate.py::TestM098ETFVixGate::test_disabled_gate_skips_check FAILED [ 55%]
- test (3.12) Run all tests 2026-05-29T06:18:50.3026984Z tests/test_m098_etf_vix_gate.py::TestM098ETFVixGate::test_e006_exception_log_written FAILED [ 55%]
- test (3.12) Run all tests 2026-05-29T06:18:53.0543772Z tests/test_outcome_resolver_noncrypto.py::TestTimeExitV22::test_long_time_exit_resolves_at_last_close FAILED [ 63%]
Warnings:
- test (3.12) Run all tests 2026-05-29T06:22:38.9191644Z warnings.warn(
- test (3.12) Run all tests 2026-05-29T06:22:38.9195956Z warnings.warn(
- test (3.12) Run all tests 2026-05-29T06:22:38.9199978Z warnings.warn(
- test (3.12) Upload test results 2026-05-29T06:22:40.9009454Z if-no-files-found: warn
- test (3.12) Upload coverage report 2026-05-29T06:22:41.8937200Z if-no-files-found: warn
- test (3.12) Upload coverage report 2026-05-29T06:22:42.0583471Z ##[warning]No files were found with the provided path: coverage.xml. No artifacts will be uploaded.
- test (3.12) Complete job 2026-05-29T06:22:43.3858477Z ##[warning]Node.js 20 actions are deprecated. The following actions are running on Node.js 20 and may not work as expected: actions/cache@v4, actions/upload-artifact@v4. Actions will be forced to run with Node.js 24 by default starting June 2nd, 2026. Node.js 20 will be removed from the runner on September 16th, 2026. Please check if updated versions of these actions are available that support Node.js 24. To opt into Node.js 24 now, set the F...

### CI Tests :: test (3.12) :: run 26621503772

Errors:
- test (3.12) Run dashboard card-metrics JS guard 2026-05-29T06:17:41.0430844Z 14 passed, 0 failed.
- test (3.12) Run all tests 2026-05-29T06:19:44.0844339Z tests/test_hf_conviction_tier.py::test_tier_b_major FAILED [ 45%]
- test (3.12) Run all tests 2026-05-29T06:19:52.7821646Z tests/test_m096_ctf_concentration_cap.py::TestM096CTFConcentrationCap::test_ctf_passes_when_below_cap FAILED [ 55%]
- test (3.12) Run all tests 2026-05-29T06:19:52.8341928Z tests/test_m096_ctf_concentration_cap.py::TestM096CTFConcentrationCap::test_non_ctf_symbol_unaffected FAILED [ 55%]
- test (3.12) Run all tests 2026-05-29T06:19:52.8855686Z tests/test_m096_ctf_concentration_cap.py::TestM096CTFConcentrationCap::test_fail_open_when_no_data FAILED [ 55%]
- test (3.12) Run all tests 2026-05-29T06:19:52.9374132Z tests/test_m096_ctf_concentration_cap.py::TestM096CTFConcentrationCap::test_skip_when_fewer_than_5_commodity_picks FAILED [ 55%]
- test (3.12) Run all tests 2026-05-29T06:19:53.1601435Z tests/test_m098_etf_vix_gate.py::TestM098ETFVixGate::test_shadow_stamps_when_vix_above_threshold FAILED [ 55%]
- test (3.12) Run all tests 2026-05-29T06:19:53.2212817Z tests/test_m098_etf_vix_gate.py::TestM098ETFVixGate::test_custom_threshold FAILED [ 55%]
- test (3.12) Run all tests 2026-05-29T06:19:53.2779962Z tests/test_m098_etf_vix_gate.py::TestM098ETFVixGate::test_disabled_gate_skips_check FAILED [ 55%]
- test (3.12) Run all tests 2026-05-29T06:19:53.2994506Z tests/test_m098_etf_vix_gate.py::TestM098ETFVixGate::test_e006_exception_log_written FAILED [ 55%]
- test (3.12) Run all tests 2026-05-29T06:19:57.1615290Z tests/test_outcome_resolver_noncrypto.py::TestTimeExitV22::test_long_time_exit_resolves_at_last_close FAILED [ 63%]
- test (3.12) Run all tests 2026-05-29T06:19:57.1726463Z tests/test_outcome_resolver_noncrypto.py::TestTimeExitV22::test_short_time_exit_loss FAILED [ 63%]
Warnings:
- test (3.12) Run all tests 2026-05-29T06:23:45.1125837Z warnings.warn(
- test (3.12) Run all tests 2026-05-29T06:23:45.1131275Z warnings.warn(
- test (3.12) Run all tests 2026-05-29T06:23:45.1136492Z warnings.warn(
- test (3.12) Upload test results 2026-05-29T06:23:47.0090815Z if-no-files-found: warn
- test (3.12) Upload coverage report 2026-05-29T06:23:48.1205267Z if-no-files-found: warn
- test (3.12) Upload coverage report 2026-05-29T06:23:48.3347605Z ##[warning]No files were found with the provided path: coverage.xml. No artifacts will be uploaded.
- test (3.12) Complete job 2026-05-29T06:23:50.0065460Z ##[warning]Node.js 20 actions are deprecated. The following actions are running on Node.js 20 and may not work as expected: actions/cache@v4, actions/upload-artifact@v4. Actions will be forced to run with Node.js 24 by default starting June 2nd, 2026. Node.js 20 will be removed from the runner on September 16th, 2026. Please check if updated versions of these actions are available that support Node.js 24. To opt into Node.js 24 now, set the F...

### CI Tests :: test (3.12) :: run 26621565175

Errors:
- test (3.12) Run dashboard card-metrics JS guard 2026-05-29T06:33:11.8786607Z 14 passed, 0 failed.
- test (3.12) Run all tests 2026-05-29T06:35:07.1153385Z tests/test_m096_ctf_concentration_cap.py::TestM096CTFConcentrationCap::test_ctf_passes_when_below_cap FAILED [ 55%]
- test (3.12) Run all tests 2026-05-29T06:35:07.1638832Z tests/test_m096_ctf_concentration_cap.py::TestM096CTFConcentrationCap::test_non_ctf_symbol_unaffected FAILED [ 55%]
- test (3.12) Run all tests 2026-05-29T06:35:07.2110363Z tests/test_m096_ctf_concentration_cap.py::TestM096CTFConcentrationCap::test_fail_open_when_no_data FAILED [ 55%]
- test (3.12) Run all tests 2026-05-29T06:35:07.2587387Z tests/test_m096_ctf_concentration_cap.py::TestM096CTFConcentrationCap::test_skip_when_fewer_than_5_commodity_picks FAILED [ 55%]
- test (3.12) Run all tests 2026-05-29T06:35:07.4672772Z tests/test_m098_etf_vix_gate.py::TestM098ETFVixGate::test_shadow_stamps_when_vix_above_threshold FAILED [ 55%]
- test (3.12) Run all tests 2026-05-29T06:35:07.5240068Z tests/test_m098_etf_vix_gate.py::TestM098ETFVixGate::test_custom_threshold FAILED [ 55%]
- test (3.12) Run all tests 2026-05-29T06:35:07.5784100Z tests/test_m098_etf_vix_gate.py::TestM098ETFVixGate::test_disabled_gate_skips_check FAILED [ 55%]
- test (3.12) Run all tests 2026-05-29T06:35:07.5982524Z tests/test_m098_etf_vix_gate.py::TestM098ETFVixGate::test_e006_exception_log_written FAILED [ 55%]
- test (3.12) Run all tests 2026-05-29T06:35:11.0900818Z tests/test_outcome_resolver_noncrypto.py::TestTimeExitV22::test_long_time_exit_resolves_at_last_close FAILED [ 63%]
- test (3.12) Run all tests 2026-05-29T06:35:11.1008408Z tests/test_outcome_resolver_noncrypto.py::TestTimeExitV22::test_short_time_exit_loss FAILED [ 63%]
- test (3.12) Run all tests 2026-05-29T06:35:21.7095830Z tests/test_pr_triage_2026_04_25_merge_success.py::Test391_CIStashFix::test_strategy_performance_json_is_tracked FAILED [ 68%]
Warnings:
- test (3.12) Upload test results 2026-05-29T06:35:52.7575602Z if-no-files-found: warn
- test (3.12) Upload test results 2026-05-29T06:35:52.9728170Z ##[warning]No files were found with the provided path: test-results.xml. No artifacts will be uploaded.
- test (3.12) Upload coverage report 2026-05-29T06:35:52.9860466Z if-no-files-found: warn
- test (3.12) Upload coverage report 2026-05-29T06:35:53.2053929Z ##[warning]No files were found with the provided path: coverage.xml. No artifacts will be uploaded.
- test (3.12) Complete job 2026-05-29T06:35:53.5840375Z ##[warning]Node.js 20 actions are deprecated. The following actions are running on Node.js 20 and may not work as expected: actions/cache@v4, actions/upload-artifact@v4. Actions will be forced to run with Node.js 24 by default starting June 2nd, 2026. Node.js 20 will be removed from the runner on September 16th, 2026. Please check if updated versions of these actions are available that support Node.js 24. To opt into Node.js 24 now, set the F...

### CI Tests :: test (3.11) :: run 26621485029

Errors:
- test (3.11) Run dashboard card-metrics JS guard 2026-05-29T06:16:48.3168607Z 14 passed, 0 failed.
- test (3.11) Run all tests 2026-05-29T06:18:20.8277810Z tests/test_equity_pead_strategy.py::TestPEADGate::test_gate_off_by_default FAILED [ 34%]
- test (3.11) Run all tests 2026-05-29T06:18:29.1868185Z tests/test_hf_conviction_tier.py::test_tier_b_major FAILED [ 45%]
- test (3.11) Run all tests 2026-05-29T06:18:32.3665649Z tests/test_m096_ctf_concentration_cap.py::TestM096CTFConcentrationCap::test_ctf_passes_when_below_cap FAILED [ 55%]
- test (3.11) Run all tests 2026-05-29T06:18:32.3785136Z tests/test_m096_ctf_concentration_cap.py::TestM096CTFConcentrationCap::test_non_ctf_symbol_unaffected FAILED [ 55%]
- test (3.11) Run all tests 2026-05-29T06:18:32.3903314Z tests/test_m096_ctf_concentration_cap.py::TestM096CTFConcentrationCap::test_fail_open_when_no_data FAILED [ 55%]
- test (3.11) Run all tests 2026-05-29T06:18:32.4021184Z tests/test_m096_ctf_concentration_cap.py::TestM096CTFConcentrationCap::test_skip_when_fewer_than_5_commodity_picks FAILED [ 55%]
- test (3.11) Run all tests 2026-05-29T06:18:32.4482401Z tests/test_m098_etf_vix_gate.py::TestM098ETFVixGate::test_shadow_stamps_when_vix_above_threshold FAILED [ 55%]
- test (3.11) Run all tests 2026-05-29T06:18:32.4713403Z tests/test_m098_etf_vix_gate.py::TestM098ETFVixGate::test_custom_threshold FAILED [ 55%]
- test (3.11) Run all tests 2026-05-29T06:18:32.4871247Z tests/test_m098_etf_vix_gate.py::TestM098ETFVixGate::test_disabled_gate_skips_check FAILED [ 55%]
- test (3.11) Run all tests 2026-05-29T06:18:32.5082964Z tests/test_m098_etf_vix_gate.py::TestM098ETFVixGate::test_e006_exception_log_written FAILED [ 55%]
- test (3.11) Run all tests 2026-05-29T06:18:35.8642937Z tests/test_outcome_resolver_noncrypto.py::TestTimeExitV22::test_long_time_exit_resolves_at_last_close FAILED [ 63%]
Warnings:
- test (3.11) Upload test results 2026-05-29T06:22:58.5398092Z if-no-files-found: warn
- test (3.11) Upload test results 2026-05-29T06:22:58.7674611Z ##[warning]No files were found with the provided path: test-results.xml. No artifacts will be uploaded.
- test (3.11) Upload coverage report 2026-05-29T06:22:58.7816990Z if-no-files-found: warn
- test (3.11) Upload coverage report 2026-05-29T06:22:59.0022756Z ##[warning]No files were found with the provided path: coverage.xml. No artifacts will be uploaded.
- test (3.11) Complete job 2026-05-29T06:22:59.4154358Z ##[warning]Node.js 20 actions are deprecated. The following actions are running on Node.js 20 and may not work as expected: actions/cache@v4, actions/upload-artifact@v4. Actions will be forced to run with Node.js 24 by default starting June 2nd, 2026. Node.js 20 will be removed from the runner on September 16th, 2026. Please check if updated versions of these actions are available that support Node.js 24. To opt into Node.js 24 now, set the F...

### Mercury 2  Signal Scanner :: scan :: run 26620934466

Errors:
- scan Run Mercury 2 scanner 2026-05-29T06:32:55.3073384Z ##[error]Process completed with exit code 1.
- scan Notify sandbox on failure ﻿2026-05-29T06:32:55.3154381Z ##[group]Run bash .github/notify-failure.sh "Mercury 2 Signal Scanner" "$DISCORD_WEBHOOK_SANDBOX" "eltonaguiar/findtorontoevents_antigravity.ca" "26620934466"
- scan Notify sandbox on failure 2026-05-29T06:32:55.3155783Z bash .github/notify-failure.sh "Mercury 2 Signal Scanner" "$DISCORD_WEBHOOK_SANDBOX" "eltonaguiar/findtorontoevents_antigravity.ca" "26620934466"
- scan Notify sandbox on failure 2026-05-29T06:32:55.3183564Z shell: /usr/bin/bash -e {0}
- scan Notify sandbox on failure 2026-05-29T06:32:55.3183845Z env:
- scan Notify sandbox on failure 2026-05-29T06:32:55.3184752Z DISCORD_WEBHOOK_SANDBOX: ***
- scan Notify sandbox on failure 2026-05-29T06:32:55.3185038Z ##[endgroup]

### DNA Mutation Cycle :: mutation-cycle :: run 26621843862

Errors:
- mutation-cycle Commit mutation data 2026-05-29T06:32:17.2652544Z ##[error]Process completed with exit code 1.
