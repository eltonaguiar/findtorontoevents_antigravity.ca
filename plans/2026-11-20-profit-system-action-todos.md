# Profit System — Action Todos (Immediate)

**Created:** 2026-11-20
**Canonical plan:** `plans/2026-11-20-market-profit-system-plan.md` (Zoo)
**Kickoff:** `plans/2026-11-20-phase0-implementation-kickoff.md`
**Todos v2:** `plans/2026-11-20-profit-program-todos-v2.json`
**COMS checkpoints:** After every 3-5 todos, check COMS, reply to peers, broadcast status update.

---

## IMMEDIATE (This Session)

### 1. P0.0c — Point-in-time audit
- [ ] Audit every feature in `alpha_engine/` and `tools/` for look-ahead bias
- [ ] Check COT signals (M-095 precedent: cot_positioning is leakage-falsified)
- [ ] Check RSI/EMA indicators use only past bars (no future data)
- [ ] Check earnings surprise (SUE) features use only published filings
- [ ] Check momentum features use only past returns (no future returns)
- [ ] Check volume features use only past volume
- [ ] Document any look-ahead found in `updates/2026-11-20-point-in-time-audit.md`
- [ ] Fix or quarantine any leaking features
- **COMS checkpoint**: check COMS, reply, broadcast status

### 2. P0.0e — Wire PBO/CPCV/DSR as hard gates
- [ ] Identify all places where PBO/CPCV/DSR are computed but not enforced
- [ ] Add `if not pbo_pass: reject` gates in `alpha_engine/money_ready_verdict.py`
- [ ] Add `if not dsr_pass: reject` gates in `alpha_engine/audit3_tribunal.py`
- [ ] Add `if not cpcv_pass: reject` gates where CPCV is computed
- [ ] Ensure walk-forward is enforced before any promotion
- [ ] Write tests for each hard gate
- [ ] Document in `updates/2026-11-20-hard-gates-wired.md`
- **COMS checkpoint**: check COMS, reply, broadcast status

### 3. P0.0h — CI enforcement (highest leverage)
- [ ] Create `.github/workflows/validation-gates.yml` that runs PBO/CPCV/DSR checks
- [ ] Make at least one gate BLOCKING (not continue-on-error)
- [ ] Ensure the workflow runs on every PR and push to main
- [ ] Add `tools/run_anti_overfit_audit.py` to CI
- [ ] Add `tools/pbo_cscv.py` to CI
- [ ] Add `tools/wfe.py` to CI
- [ ] Document in `updates/2026-11-20-ci-gates-enforced.md`
- **COMS checkpoint**: check COMS, reply, broadcast status

### 4. P0.0g — Fix expected_pct persistence bug
- [ ] In `tools/residual_mean_reversion.py` `simulate()`, persist `expected_pct` to trade dict
- [ ] Two lines to fix (as noted by peer)
- [ ] Add test for expected_pct persistence
- [ ] Document in `updates/`

### 5. P0.0i — Deprecate probabilistic_sharpe_engine
- [ ] Add deprecation notice to `probabilistic_sharpe_engine.py`
- [ ] Redirect all imports to `alpha_engine/anti_overfit_validator.deflated_sharpe` or `research/profitability/backtest.deflated_sharpe`
- [ ] Verify no importers in main tree (currently none, but guard against future)
- [ ] Document in `updates/`

### 6. P0.0j — Fix evaluate_strategy PBO degraded mode
- [ ] In `alpha_engine/anti_overfit_validator.py`, return nan instead of plausible number when using synthetic zero-mean peers
- [ ] Add test for degraded mode returning nan
- [ ] Document in `updates/`

### 7. P0.0k — Cost gate redesign
- [ ] Redesign cost gate to condition on sigma_eq (not filter on it)
- [ ] Trade only when sigma_eq above median AND expected_pct > cost
- [ ] Update `alpha_engine/cost_implied_trade_gate.py`
- [ ] Re-run paired comparison with corrected gate logic
- [ ] Document in `updates/`

### 8. P0.0l — Cost gate corrected comparison
- [ ] Use captured reversion ((|s_entry|-0.5)*sigma_eq) not full reversion (|s_entry|*sigma_eq)
- [ ] Test at varying cost levels (0.4%, 1.0%, 2.0%)
- [ ] Test at varying entry thresholds (1.25, 1.0, 0.75)
- [ ] Identify binding point
- [ ] Document in `updates/`

---

## SHORT-TERM (Next 1-2 Sessions)

### 9. P0.1 — Price freshness SLA
- [ ] Extend tools/db_freshness_check.py for equity/FX/futures price vintage
- [ ] Create price-freshness-guardian.yml workflow
- [ ] Backfill FX 2026-02->11, fix AUDJPY mapping, retire EURUSDT
- **COMS checkpoint**

### 10. P0.2 — Canonical population + exclusion bias
- [ ] Pin one canonical population (resolved_closed_picks_net)
- [ ] Bound exclusion bias (41.2% unscored book)
- [ ] Publish selection alpha per class on dashboard
- [ ] Publish MDE per asset class
- **COMS checkpoint**

### 11. P0.3 — Profit factor split + trial counter
- [ ] Publish pf_gross, pf_net, expectancy_net separately
- [ ] Fix policy_clean_* invariant
- [ ] Thread global trial counter into deflated_sharpe
- [ ] Record real n_trials for all DSR claims
- **COMS checkpoint**

### 12. P1.1-P1.5 — Harness calibration
- [ ] Port RSI(2) on SPY/QQQ through audit3 tribunal
- [ ] Run on BTC/SOL for known-negative calibration
- [ ] Implement alpha_per_exposed_day and time_in_market metrics
- **COMS checkpoint**

### 13. P1.6-P1.9 — Residual MR pod (H-144)
- [ ] Pre-register H-144 in hypothesis registry
- [ ] Implement stat_arb_residual.py (PCA + sector-ETF variants)
- [ ] Run through full gates
- [ ] H-147: selection-alpha decomposition
- **COMS checkpoint**

### 14. P1.10-P1.12 — Energy calendar spreads (H-145)
- [ ] Pre-register H-145 in hypothesis registry
- [ ] Implement energy_calendar_spread.py (CL, NG first)
- [ ] Run through full gates (bootstrap significance + realistic roll costs)
- **COMS checkpoint**

---

## MEDIUM-TERM (Next 2-4 Sessions)

### 15. P2 — Stop destroying value
- [ ] Paired-bootstrap A/B of TP/SL vs symmetric vol-scaled time exit
- [ ] Reconcile modelled slippage vs measured fills
- [ ] Kill expressions with alpha <= 0 in two regimes
- [ ] Cost-implied trade gate wired into order gateway
- [ ] Change discovery objective to mean forward return net of cost
- [ ] Mandatory direction check in every scan
- [ ] Variance artifact verdict
- [ ] Per-feature coverage instead of global dropna
- [ ] Explicit inconclusive records
- **COMS checkpoint**

### 16. P3 — One premium, pre-registered, forward clock
- [ ] Pre-register chosen hypothesis with kill rule
- [ ] Freeze spec, max 5 configurations, log every trial
- [ ] Purged walk-forward + embargo, 2x slippage, 1-bar delay
- [ ] Random-entry and beta-matched hold control arms
- [ ] Accrue forward paper rows to n>=100
- [ ] Residual-book construction
- [ ] Cost-model reconciliation
- **COMS checkpoint**

### 17. P4 — Portfolio, not pick list
- [ ] Correlation matrix of survivors on forward returns
- [ ] Vol targeting + evidence weight + per-sleeve risk budget
- [ ] Regime detection with per-regime exposure caps
- [ ] Drawdown circuit breaker at -15% HWM
- [ ] Core beta + premia sleeve + sandbox allocation
- [ ] Paper trade 60-90 days before funding
- [ ] Establish max drawdown capacity
- **COMS checkpoint**

### 18. P5 — Reconcile, calibrate, decay-check
- [ ] Daily reconciliation sleeve equity vs positions+cash
- [ ] Brier score of verdicts
- [ ] Sabotage suite (fake rejected, real accepted)
- [ ] Quarterly decay review per surviving edge
- [ ] Hypothesis registry append guard
- **COMS checkpoint**

---

## COMS CHECKPOINT PROTOCOL

After every 3-5 todos (or at phase boundaries):
1. Check COMS: `timeout 10 mosquitto_sub -h 192.168.2.52 -p 1883 -t '#' -W 6 -F '%t|%l' | sort -u`
2. Read any new messages on `profit-system/plan`, `mentions/all`, and `inbox/gx10-c9b9/findtorontoevents-antigravity-ca/opencode-beam-free`
3. Reply to peers if they've asked questions
4. Broadcast status update to `profit-system/plan` (retained) with:
   - Completed todo IDs
   - Next todo IDs
   - Any blockers
   - Any findings

## NOTES

- No new strategy generation while P0 or P1 todos are open
- A phase may not start before the previous phase's exit test is written down
- Every todo must name the artifact that proves it is done
- Negative result is a valid, publishable outcome (PROTOCOL §1)
- No real capital until Phase 4 gates met
- COMS check uses -W (time window), not -C (count)
- Subscribe to specific topics, not inbox/#
- Use notes/<slug> for durable messages, inbox/<host>/<worktree>/all for pointers