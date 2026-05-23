# ML ENHANCEMENT INTEGRATION - DEPLOYMENT PLAYBOOK
## Crypto Prediction System - Production Deployment Strategy

---

## EXECUTIVE SUMMARY

This playbook provides a detailed deployment strategy for integrating 5 ML agent improvements into the crypto prediction system. The strategy emphasizes phased rollouts, comprehensive validation gates, and robust rollback capabilities.

---

## PART 1: CURRENT DEPLOYMENT SEQUENCE ANALYSIS

### 1.1 Merge Order Assessment

| Component | Agent | Current Order | Assessment | Recommendation |
|-----------|-------|---------------|------------|----------------|
| Feature Contract | 4 | 1st (FIRST) | CORRECT - Foundation layer | KEEP |
| Dead Features Fix | 1 | 2nd (SECOND) | CORRECT - Builds on contract | KEEP |
| SL Calibrator | 2 | DONE | CORRECT - Independent | KEEP |
| Entry Timing | 5 | LAST | CORRECT - Most complex, needs stability | KEEP |

### 1.2 Dependency Analysis

DEPENDENCY GRAPH:

                    +-------------------------------------+
                    |   Stage 0: SL Calibrator (DONE)     |
                    |   Status: Independent, Active       |
                    +------------------+------------------+
                                       |
                                       v (no dependency)
                    +-------------------------------------+
                    |   Stage 1: Feature Contract         |
                    |   Agent 4 - FOUNDATION              |
                    |   Output: ml_features_at_entry      |
                    +------------------+------------------+
                                       |
                                       v (hard dependency)
                    +-------------------------------------+
                    |   Stage 2: Dead Features Fix        |
                    |   Agent 1 - EXTENDS contract        |
                    |   Requires: ml_features_at_entry    |
                    +------------------+------------------+
                                       |
                                       v (soft dependency - stability)
                    +-------------------------------------+
                    |   Stage 3: Entry Timing             |
                    |   Agent 5 - CONSUMES features       |
                    |   Requires: Stable feature pipeline |
                    +-------------------------------------+

### 1.3 Critical Path Analysis

**Critical Path:** Agent 4 -> Agent 1 -> Agent 5 (sequential, no parallelization possible)

**Parallel Opportunities:**
- SL Calibrator expansion (Agent 2) can run in parallel with ALL stages
- Testing and validation can overlap with development of next stage
- Documentation and runbook updates can proceed in parallel

### 1.4 Bottleneck Identification

| Bottleneck | Impact | Mitigation |
|------------|--------|------------|
| Feature contract must be stable before Agent 1 | Delays Agent 1 start | Early freeze on contract interface |
| Agent 1 requires 3 stable retrains | ~2-3 week delay | Accelerated retrain schedule in staging |
| Agent 5 requires all prior KPIs green | Final gate risk | Pre-validation in shadow mode |
| SL calibrator needs 10+ winners/group | Coverage expansion slow | Parallel group calibration |

---

## PART 2: DETAILED DEPLOYMENT STAGES

### STAGE 0: SL CALIBRATOR (Agent 2) - VERIFICATION & EXPANSION
**Status: Already Deployed, Tighten-Only Mode**

#### Pre-Deployment Checklist (Verification)
- [ ] Confirm 2/N groups currently calibrated
- [ ] Document current coverage percentage
- [ ] Verify hierarchical fallback chain operational
- [ ] Review "tighten-only" mode enforcement

#### Deployment Steps (Expansion Phase)

1. **Identify Priority Groups**
   - Rank uncalibrated groups by trade frequency
   - Target groups with >50 trades in last 90 days first
   
2. **Parallel Calibration Process**
   
   For each priority group:
   - Collect minimum 10 winning trades
   - Calculate group-specific SL parameters
   - Validate against parent bucket
   - A/B test vs hierarchical fallback
   - Promote to active if win rate improves

3. **Coverage Tracking Dashboard**
   - Metric: `% groups with direct calibration`
   - Target: 80% coverage within 60 days
   - Alert if coverage < target for 7 consecutive days

#### Validation Criteria
| Metric | Current | Target | Threshold |
|--------|---------|--------|-----------|
| Calibrated Groups | 2/N | 80% of N | Minimum 10 winners/group |
| Fallback Rate | TBD | <15% | Alert if >25% |
| SL-hit Rate | Baseline | -5% vs baseline | Rollback if +2% |

#### Monitoring Period
- **Continuous monitoring** with weekly coverage reports
- **Monthly deep-dive** on calibrated groups performance

#### Go/No-Go Decision
- **GO**: Coverage expanding, no SL-hit rate degradation
- **NO-GO**: Coverage stalled >14 days OR SL-hit rate increases

---

### STAGE 1: FEATURE CONTRACT (Agent 4)
**Foundation Layer - Merge FIRST**

#### Pre-Deployment Checklist
- [ ] All 39 feature schemas documented
- [ ] Contract interface frozen and versioned
- [ ] Backward compatibility test suite passes
- [ ] Health gate implementation code-reviewed
- [ ] Dead feature detection algorithm validated
- [ ] Rollback procedure documented

#### Deployment Steps

**Phase 1.1: Contract Deployment (Day 1-2)**

```python
# 1. Deploy contract schema to staging
ml_features_contract.deploy(
    version="v1.0.0",
    features=ALL_39_FEATURES,
    health_gate=HealthGate(
        dead_threshold=0.50,  # Start permissive
        check_frequency="per_retrain"
    )
)

# 2. Enable contract validation (non-blocking)
feature_validator.enable(mode="log_only")

# 3. Run validation against last 5 retrains
validation_results = feature_validator.backtest(
    retrains=5,
    expected_features=39
)
```

**Phase 1.2: Health Gate Activation (Day 3-7)**

```python
# Gradual enforcement progression
health_gate_stages = {
    "stage_1": {"dead_threshold": 0.50, "action": "warn"},
    "stage_2": {"dead_threshold": 0.35, "action": "warn"},  # After 3 stable
    "stage_3": {"dead_threshold": 0.20, "action": "block"},  # After backfill
    "stage_4": {"dead_threshold": 0.10, "action": "block"}   # Final
}
```

**Phase 1.3: Stabilization (Week 2-4)**
- Monitor contract adherence across all pipelines
- Collect metrics on feature availability
- Document any contract violations

#### Validation Criteria
| Criterion | Method | Pass Threshold |
|-----------|--------|----------------|
| Contract adherence | Automated check | >95% of pipelines |
| Feature availability | Metric | All 39 features present |
| Health gate functional | Test | Correctly flags violations |
| No production errors | Monitoring | Zero contract-related errors |

#### Monitoring Period
- **Intensive**: 7 days post-deployment
- **Standard**: 14 additional days
- **Total before next stage**: 21 days minimum

#### Go/No-Go Decision

**GO Criteria (ALL must pass):**
1. Contract validated across all pipelines
2. Zero contract-related production errors for 7 days
3. Health gate correctly identifies violations in test
4. Feature availability >98% for all 39 features

**NO-GO Triggers (ANY triggers rollback):**
1. Contract violation causes pipeline failure
2. Feature availability drops below 90%
3. Health gate produces false positives >5%
4. Production errors related to contract in first 48h

---

### STAGE 2: DEAD FEATURES FIX (Agent 1)
**Extends Feature Contract - Merge SECOND**

#### Pre-Deployment Checklist
- [ ] Stage 1 GO decision recorded
- [ ] Time/vol/outcome feature schemas finalized
- [ ] Feature importance analysis completed
- [ ] Dead feature list (<10/39 target) documented
- [ ] New feature code coverage >90%
- [ ] Integration tests with contract pass

#### Deployment Steps

**Phase 2.1: Feature Addition (Day 1-3)**

```python
# Add new features to existing contract
contract.extend_features([
    "time_features",      # Hour, day of week, session
    "volatility_features", # Realized vol, implied vol spread
    "outcome_features"     # Post-entry price action
])

# Deploy to staging first
staging_deploy(contract_v1_1_0)

# Run parallel pipeline for 3 days
run_shadow_pipeline(
    baseline=contract_v1_0_0,
    candidate=contract_v1_1_0,
    duration="72h"
)
```

**Phase 2.2: Health Gate Tightening (Week 2-5)**

```python
# Progressive tightening schedule
tightening_schedule = {
    "week_2": {"dead_threshold": 0.50, "status": "monitoring"},
    "week_3": {"dead_threshold": 0.50, "status": "awaiting_retrains"},
    "week_4": {"dead_threshold": 0.35, "status": "3_stable_retrains_achieved"},
    "week_5": {"dead_threshold": 0.20, "status": "backfill_complete"}
}
```

**Phase 2.3: Dead Feature Reduction (Ongoing)**

```python
dead_feature_tracking = {
    "target": "<=10 dead features",
    "baseline": "TBD from initial scan",
    "weekly_action": "Review dead feature report",
    "removal_criteria": [
        "Dead for 3+ consecutive retrains",
        "Importance score < 0.01",
        "No planned fix in backlog"
    ]
}
```

#### Validation Criteria
| Criterion | Target | Measurement |
|-----------|--------|-------------|
| Dead features | <=10/39 | Weekly scan |
| New feature coverage | 100% | Feature availability metric |
| Model performance | Neutral or better | A/B test vs baseline |
| Pipeline stability | No new errors | Error rate monitoring |

#### Monitoring Period
- **Phase 2.1**: 3 days shadow mode
- **Phase 2.2**: 21 days for 3 stable retrains
- **Phase 2.3**: Ongoing

#### Go/No-Go Decision

**GO Criteria:**
1. Dead features reduced to <=15/39 (intermediate target)
2. 3 consecutive stable retrains completed
3. No pipeline errors attributed to new features
4. Model performance neutral or improved

**NO-GO Triggers:**
1. Dead features increase vs baseline
2. New features cause pipeline instability
3. Model performance degradation >2%
4. Unable to achieve 3 stable retrains in 30 days

---

### STAGE 3: ENTRY TIMING (Agent 5)
**Most Complex - Merge LAST with Feature Flag**

#### Pre-Deployment Checklist
- [ ] Stage 2 GO decision recorded
- [ ] Entry timing model trained and validated
- [ ] Feature flag infrastructure ready
- [ ] Shadow mode testing completed (2+ weeks)
- [ ] Adverse entry bps baseline established
- [ ] Kill switch procedure tested

#### Deployment Steps

**Phase 3.1: Feature Flag Setup (Day 1)**

```python
# Define feature flag
entry_timing_flag = FeatureFlag(
    name="entry_timing_agent5",
    states=["off", "shadow", "canary_10", "canary_25", "canary_50", "full"],
    default="off",
    kill_switch=True,
    rollback_on_error=True
)

# Deploy flag infrastructure
feature_flag_system.deploy(entry_timing_flag)
```

**Phase 3.2: Shadow Mode (Week 1-2)**

```python
# Shadow mode: Calculate but don't act
entry_timing_flag.set_state("shadow")

# Collect metrics without affecting trades
shadow_metrics = {
    "adverse_entry_bps": "compare_to_baseline",
    "signal_agreement": "with_baseline_signals",
    "latency": "inference_time_ms"
}
```

**Phase 3.3: Canary Rollout (Week 3-6)**

```
Week 3: 10% traffic -> Monitor 3 days -> Decision
Week 4: 25% traffic -> Monitor 5 days -> Decision  
Week 5: 50% traffic -> Monitor 7 days -> Decision
Week 6: 100% traffic -> Full monitoring
```

**Phase 3.4: Full Deployment (Week 7+)**
- Remove feature flag after 14 days stable at 100%
- Archive flag for future use

#### Validation Criteria
| Criterion | Target | Measurement Period |
|-----------|--------|-------------------|
| Adverse entry bps | Reduced vs baseline | Continuous |
| Signal latency | <50ms p99 | Continuous |
| Model accuracy | >= baseline | Weekly |
| Error rate | Zero critical | Continuous |

#### Monitoring Period
- **Shadow**: 14 days minimum
- **Canary 10%**: 3 days
- **Canary 25%**: 5 days
- **Canary 50%**: 7 days
- **Full**: 14 days before flag removal

#### Go/No-Go Decision

**GO Criteria (per canary stage):**
1. Adverse entry bps reduced or neutral
2. No critical errors
3. Latency within SLA
4. Manual approval from ML lead

**NO-GO Triggers:**
1. Adverse entry bps increases >10%
2. Any critical error
3. Latency >100ms p99
4. Model accuracy drops >5%

---

## PART 3: FEATURE FLAG STRATEGY

### 3.1 Flag Naming Conventions

```
NAMESPACE: ml_enhancement_[year]_[component]_[agent]

Examples:
- ml_enhancement_2024_entry_timing_agent5
- ml_enhancement_2024_feature_contract_agent4
- ml_enhancement_2024_dead_features_agent1
- ml_enhancement_2024_sl_calibrator_agent2
```

### 3.2 Flag States and Transitions

STATE MACHINE:

    +---------+    deploy     +----------+
    |  OFF    | ------------> |  SHADOW  |
    | (init)  |               | (observe)|
    +---------+               +-----+----+
         ^                          |
         |                          |
         |                     +----v-----+
         |                     | CANARY_10|
         |                     |  (10%)   |
         |                     +-----+----+
         |                          |
         |                          | 3 days stable
         |                     +----v-----+
         |                     | CANARY_25|
         |                     |  (25%)   |
         |                     +-----+----+
         |                          |
         |                          | 5 days stable
         |                     +----v-----+
         |                     | CANARY_50|
         |                     |  (50%)   |
         |                     +-----+----+
         |                          |
         |                          | 7 days stable
         |                     +----v-----+
         |                     |   FULL   |
         |                     |  (100%)  |
         |                     +-----+----+
         |                          |
         |                          | 14 days stable
         |                     +----v-----+
         |                     |REMOVE FLAG|
         |                     | (complete)|
         |                     +----------+
         |
         +---------------------------+
              KILL SWITCH (any state)

### 3.3 Percentage Rollout Plan

| Stage | Traffic % | Duration | Success Criteria | Failure Action |
|-------|-----------|----------|------------------|----------------|
| Shadow | 0% (log only) | 14 days | Metrics collected | Extend shadow |
| Canary 1 | 10% | 3 days | No errors, metrics good | Rollback to shadow |
| Canary 2 | 25% | 5 days | Performance neutral | Rollback to 10% |
| Canary 3 | 50% | 7 days | Performance improved | Rollback to 25% |
| Full | 100% | 14 days | Stable operation | Rollback to 50% |
| Complete | Remove flag | N/A | N/A | N/A |

### 3.4 Kill Switch Procedures

**Emergency Kill Switch:**

```python
def emergency_kill(flag_name):
    # Execute in <30 seconds
    feature_flags.set_state(flag_name, "off")
    alert_pagerduty(urgency="P1")
    notify_slack(channel="#ml-alerts")
    log_incident(flag_name, reason="emergency_kill")
```

**Graceful Kill Switch:**

```python
def graceful_kill(flag_name, drain_seconds=300):
    # Execute in <5 minutes
    # Allows in-flight requests to complete
    feature_flags.set_state(flag_name, "draining")
    time.sleep(drain_seconds)
    feature_flags.set_state(flag_name, "off")
    notify_slack(channel="#ml-ops")
```

---

## PART 4: ROLLBACK STRATEGY

### 4.1 Rollback Triggers

| Severity | Trigger | Response Time | Action |
|----------|---------|---------------|--------|
| CRITICAL | Production error affecting trades | <5 min | Emergency kill |
| HIGH | KPI degradation >10% | <15 min | Graceful kill |
| MEDIUM | KPI degradation 5-10% | <1 hour | Rollback to previous stage |
| LOW | Anomaly detected | <4 hours | Investigate, prepare rollback |

### 4.2 Component-Specific Rollback

**Stage 1: Feature Contract Rollback**

```bash
# Rollback procedure
# 1. Identify last known good version
# 2. Deploy previous contract version
# 3. Verify pipeline restoration
# 4. Notify stakeholders

# Command
ml_contract.rollback(to_version="v0.9.9")
```

**Stage 2: Dead Features Fix Rollback**

```bash
# Rollback procedure
# 1. Remove new features from contract
# 2. Revert to contract v1.0.0
# 3. Restart affected pipelines
# 4. Verify dead feature count returns to baseline

# Command
ml_contract.rollback(to_version="v1.0.0")
```

**Stage 3: Entry Timing Rollback**

```python
# Immediate rollback
def rollback_entry_timing():
    feature_flags.set_state("ml_enhancement_2024_entry_timing_agent5", "off")
    
    # Verify rollback
    verification = {
        "flag_state": feature_flags.get_state("entry_timing_agent5"),
        "baseline_active": check_baseline_model_active(),
        "no_errors": check_error_rate() == 0
    }
    
    return verification
```

### 4.3 Rollback Verification

```python
rollback_verification_checklist = {
    "service_health": "All services healthy",
    "error_rate": "Zero new errors",
    "metrics_baseline": "Metrics returned to pre-deployment baseline",
    "data_integrity": "No data corruption detected",
    "stakeholder_notification": "Team notified of rollback"
}
```

### 4.4 Communication Plan

| Event | Channels | Recipients | Timing |
|-------|----------|------------|--------|
| Rollback initiated | Slack #ml-alerts, PagerDuty | ML team, On-call | Immediate |
| Rollback complete | Slack #ml-ops | ML team, Stakeholders | Within 15 min |
| Post-mortem scheduled | Email, Calendar | All involved | Within 24 hours |
| Incident report | Confluence | Leadership | Within 48 hours |

---

## PART 5: ENVIRONMENT STRATEGY

### 5.1 Environment Architecture

ENVIRONMENT FLOW:

+-------------+     +-------------+     +-------------+     +-------------+
|   LOCAL     | --> |    DEV      | --> |   STAGING   | --> |  PRODUCTION |
|  (developer)|     |  (feature)  |     |  (pre-prod) |     |   (live)    |
+-------------+     +-------------+     +-------------+     +-------------+
                                              |
                                              v
                                        +-------------+
                                        |   SHADOW    |
                                        |  (mirrors   |
                                        |  production)|
                                        +-------------+

### 5.2 Environment Specifications

| Environment | Purpose | Data | Traffic | Monitoring |
|-------------|---------|------|---------|------------|
| Local | Development | Synthetic | None | Console logs |
| Dev | Feature testing | Sampled (1%) | Simulated | Basic metrics |
| Staging | Integration testing | Full historical | Simulated | Full metrics |
| Shadow | Production validation | Production | Mirrored (no action) | Full metrics |
| Production | Live trading | Production | 100% | Full metrics + alerts |

### 5.3 Testing by Environment

| Test Type | Local | Dev | Staging | Shadow | Production |
|-----------|-------|-----|---------|--------|------------|
| Unit tests | Y | Y | Y | - | - |
| Integration tests | - | Y | Y | - | - |
| Contract validation | - | Y | Y | Y | Y |
| Performance tests | - | - | Y | Y | Y |
| A/B tests | - | - | Y | Y | Y (canary) |
| Chaos tests | - | - | Y | - | - |
| Load tests | - | - | Y | - | - |

### 5.4 Promotion Criteria

**Local -> Dev:**
- [ ] All unit tests pass
- [ ] Code review approved
- [ ] No linting errors

**Dev -> Staging:**
- [ ] Integration tests pass
- [ ] Contract validation passes
- [ ] Performance baseline met

**Staging -> Shadow:**
- [ ] All KPIs green in staging
- [ ] Load test passed
- [ ] Security review complete

**Shadow -> Production:**
- [ ] Shadow mode metrics validated
- [ ] Manual approval from ML lead
- [ ] Rollback procedure tested

---

## PART 6: ENHANCED RECOMMENDATIONS

### 6.1 Parallelization Opportunities

| Activity | Can Parallelize With | Time Saved |
|----------|---------------------|------------|
| SL calibrator expansion | All stages | ~2 weeks |
| Documentation updates | All stages | ~1 week |
| Runbook development | Stage 1-2 | ~1 week |
| Training material | Stage 2-3 | ~1 week |

### 6.2 Risk Mitigation Enhancements

1. **Pre-deployment Dry Run**
   - Full deployment rehearsal in staging
   - Simulate failures and practice rollback
   - Validate all monitoring and alerts

2. **Extended Shadow Mode**
   - Recommend 21 days for Agent 5 (vs 14)
   - Include market stress period in shadow

3. **Feature Flag Hierarchy**

   ```
   master_kill_switch (all ML enhancements)
   |-- component_flag (per agent)
   |   +-- sub_feature_flag (per capability)
   +-- emergency_rollback (bypass all)
   ```

4. **Automated Rollback Triggers**
   - Auto-rollback on critical error
   - Auto-rollback on latency > SLA
   - Auto-rollback on error rate spike

### 6.3 Success Metrics Dashboard

```python
deployment_dashboard = {
    "overall_health": {
        "all_stages_deployed": "boolean",
        "all_kpis_green": "boolean",
        "days_since_last_rollback": "integer"
    },
    "stage_status": {
        "sl_calibrator": {"status": "done", "coverage": "%"},
        "feature_contract": {"status": "pending", "health": "%"},
        "dead_features": {"status": "pending", "dead_count": "int"},
        "entry_timing": {"status": "pending", "flag_state": "string"}
    },
    "kpis": {
        "dead_features": {"current": "int", "target": "<=10"},
        "constant_features": {"current": "%", "target": "<=20%"},
        "entry_quality": {"current": "bps", "target": "improved"},
        "stop_quality": {"current": "rate", "target": "lower"},
        "regime_robustness": {"current": "score", "target": "balanced"},
        "live_safety": {"current": "drawdown", "target": "no increase"}
    }
}
```

---

## APPENDIX: QUICK REFERENCE

### Emergency Contacts
- ML On-Call: [PagerDuty rotation]
- Engineering Lead: [Contact]
- Product Owner: [Contact]

### Key Commands

```bash
# Check feature flag status
ml-flags status --flag=entry_timing_agent5

# Emergency kill
ml-flags kill --flag=entry_timing_agent5 --reason="[reason]"

# Rollback component
ml-deploy rollback --component=feature_contract --version=v1.0.0

# View deployment status
ml-deploy status --all
```

### Useful Links
- Deployment Dashboard: [URL]
- Feature Flag Console: [URL]
- Runbook Wiki: [URL]
- Incident Response: [URL]

---

Document Version: 1.0
Last Updated: [Current Date]
Owner: ML Engineering Team
