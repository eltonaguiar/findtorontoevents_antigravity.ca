# Session Review — 2026-05-17 Round 12 (Final)

## Context
Quant/systems review. Final continuation of the 2026-05-17 extended session (rounds 1-11 previously reviewed). This round covers work done in session l — the final stretch after session k was marked DONE.

## Session Deliverables (this round)

### 1. GSD Scanner CI Fix — SHIPPED to main
- **File:** `.github/workflows/crypto-ml-edge.yml`
- **Fix:** Added `if: github.ref == 'refs/heads/main'` condition to "Commit updated picks" step
- **Rationale:** `safe_push.sh` calls `git push origin main` which fails on PR branch checkouts ("src refspec main does not match any"). The push-to-main step only needs to run when building on the main branch.
- **Commit:** `7a4046914a` — `fix(ci): skip GSD scanner push-to-main on non-main branches`
- **Impact:** PR #1132 scan: FAILURE cleared. CI re-queued after PR #1132 branch rebased onto updated main.

### 2. PR #1132 CI Re-Running (fix/c1bc-d2-resolver)
- Rebased `fix/c1bc-d2-resolver` onto updated main (picks up workflow fix)
- Force-pushed with `--force-with-lease`
- All CI checks queued/in-progress as of session end: CI Tests, Quant Auditor, walkforward-gate, Secret Scan, Conflict Marker, No stale DB passwords
- Test assertion already updated (51000.0 → 51500.0) from session k; 29/29 tests pass locally

### 3. PR #1137 MERGED
- `fix(requirements): declare 6 undeclared third-party deps (yfinance, pymysql, redis, ...)` — merged 2026-05-17T07:13:33Z
- All Gitleaks, CI Tests, 3.11+3.12 checks passed

### 4. PR #1125 Closed as Stale
- Target files (`reports/DAILY_IDEAS_COMMODITY_CLAUDE_May162026.MD`, `DAILY_IDEAS_PROMPTS.MD`) deleted/restructured in main
- Core SHORT finding preserved in `reports/mutation_investigation_2026_05_17.md` + BLOCKED_DIRECTION_TRIPLES

### 5. PR #1139 Open (Hourly Audit 07Z — Tracking Only)
- Reports CRYPTO recovery (06Z nadir PF=0.21 → 07Z PF=1.142), EQUITY 7d degradation (PF=0.682, n=22, unresolved picks contaminating window)
- Lists 5 direction-asymmetry candidates — ALL already in BLOCKED_DIRECTION_TRIPLES (verified in quality_gates.py)
- Tracking-only PR (no code changes); CI: Secret Scan in_progress

## Full Session Summary (all rounds)

### Completed in sessions j+k+l
| Item | Status |
|------|--------|
| C1 Path B/C test assertion fix (51000→51500) | ✅ DONE |
| Swarm worker preamble-before-fence recovery | ✅ DONE |
| Swarm worker 2000-char cap removed | ✅ DONE |
| M-053 stat validation (COMMODITY bias, FOREX paradox) | ✅ DONE |
| Charter drift circuit breaker WON/LOST fix | ✅ DONE |
| COMMODITY survivorship warning in template.html | ✅ DONE |
| GSD Scanner CI fix (non-main branch push) | ✅ DONE |
| PR #1137 merged (yfinance + deps) | ✅ DONE |
| PR #1136 merged (oi_change_24h persistence) | ✅ DONE |
| PR #1133 merged (ETF-bond sequence) | ✅ DONE |
| PR #1125 closed (stale) | ✅ DONE |
| Issue #688, #689 closed (already blocked) | ✅ DONE |
| PR #1132 CI re-running (after workflow fix) | ⏳ CI in progress |

### Still Externally Blocked
| Item | Blocker |
|------|---------|
| MySQL ghost-row purge (655k rows ejaguiar1_stocks) | PA console required |
| UEPS_ENABLE_PEAD=1 prod .env verification | PA console required |
| Issue #1095 FRED_API_KEY secret | Manual GH secret required |
| Schema drift watchdog (Item 3.5) | MySQL console required |

### Time-Gated (future-enable decisions)
| Item | Enable date | Trigger |
|------|-------------|---------|
| META_LABEL_GATE_ENFORCE=1 | ~2026-06-16 | WR≥55% × 30 consecutive days, n≥50 shadow obs, EQUITY-first |
| EQUITY_CONVICTION_TIERS=1 | 2026-06-15 | Shadow validation complete |
| NUPL_GATE_ENFORCE=1 | 2026-06-16 | Shadow validation complete |
| FOREX_COPYTRADER_ENABLE=1 | when non-JPY-cross n≥30 | Data accumulation |

## Swarm Questions

1. **PR #1132 merge decision**: Once CI passes (expected: all checks green given 29/29 tests pass locally + workflow fix applied), should PR #1132 be merged immediately, or should the C1 Path B/C vs OHLC revert be split into separate PRs first? The PR combines: (a) live_price as exit for C1 B/C, (b) OHLC gap-aware fill revert from _scan_ohlc_for_touch. These are logically independent changes.

2. **EQUITY 7d degradation in PR #1139**: The 07Z audit shows EQUITY 7d PF=0.682 with 11/22 picks having pnl=0 (unresolved). Should we add a filter to the 7d WR/PF calculation to exclude picks with `pnl_pct==0 AND status==OPEN` (i.e., exclude unresolved), so the window metric reflects only settled picks? Or flag this as a data quality issue in the dashboard banner?

3. **PR #1139 merge decision**: The hourly audit PR is tracking-only (no code changes). Should it be merged to preserve the audit trail, or closed since the direction-asymmetry findings it documents are already in BLOCKED_DIRECTION_TRIPLES?

4. **kilo/groq preamble-before-fence validation**: The swarm worker fix (secondary re.search pass for preamble-before-fence) was shipped with unit tests on synthetic strings. Should we run a live validation test with a known-fenced real engine response before the next scheduled swarm run?

5. **realized_n_30d cold-start fix**: Charter drift circuit breaker WON/LOST fix landed. On next dashboard generation, realized_n_30d should be non-zero for classes with recent closed picks. What's the minimum n required before a circuit breaker verdict should be considered reliable (n=30 default, or is that too low for BOND/ETF)?

## Format
```json
{
  "verdict": "DONE | MOSTLY_DONE | NEEDS_WORK",
  "pr_1132_split_recommendation": "SPLIT_PRs | KEEP_COMBINED | NO_OPINION",
  "equity_7d_pnl0_filter": "FILTER_UNRESOLVED | DASHBOARD_NOTE | DEFER",
  "pr_1139_disposition": "MERGE | CLOSE | DEFER",
  "swarm_worker_live_validation": "RUN_TEST | TRUST_UNIT_TESTS | DEFER",
  "circuit_breaker_min_n": 30,
  "remaining_code_actionable": ["any items missed"],
  "summary": "one paragraph"
}
```
