# North Star Action Plan — Hedge-Fund-Grade Edge Per Asset Class

**Created:** 2026-05-19  
**Last Updated:** 2026-05-20 (KIMI RENAISSANCE REVIEW + 5-ENGINE PEER REVIEW)  
**Standing Order:** Main mission = statistical edge per asset class. Credential fixes, infra-only work, and UI polish are PARKED until edge is proven.

---

## 🚨 EMERGENCY UPDATE — KIMI RENAISSANCE REVIEW (2026-05-20)

**Kimi (Renaissance/Two Sigma background) conducted a comprehensive audit of the audit infrastructure and GitHub codebase. The verdict: CONDITIONALLY OPERATIONAL with significant remediation required.**

### CRITICAL FINDINGS (Previously Unknown)

| # | Severity | Finding | Impact |
|---|----------|---------|--------|
| **K-01** | 🔴 CRITICAL | **Outcome resolver at 0.09% coverage** — effectively dead. No new pick is being validated. Every "live" metric is stale. | All downstream metrics invalid |
| **K-02** | 🔴 CRITICAL | **DB integrity at 61%** — 10,501/26,945 picks have PnL mismatch >1pp. 655K ghost rows unresolved. | PF/WR/DSR/PBO/WFE computed on corrupt data |
| **K-03** | 🔴 CRITICAL | **4 statistical bugs**: (1) DSR negative variance returns garbage via `max(sr_var, 1e-16)`, (2) PBO fallback has ZERO purging (massive info leakage), (3) IS Sharpe uses market avg return not strategy return, (4) trade-level Sharpe annualizes by sqrt(250) on trade PnLs | All statistical gates mathematically invalid |
| **K-04** | 🔴 CRITICAL | **Score thresholds actively snooped** — CRYPTO 70→65→60, FOREX 55→40, COMMODITY 60→30, all lowered since plan written to maintain pick flow | Manufacturing false edges |
| **K-05** | 🔴 CRITICAL | **DB credentials exposed** — `mysql.50webs.com` + `ejaguiar1_stocks` in public `.github/workflows/ab_analysis.yml` | Security breach risk |
| **K-06** | 🔴 CRITICAL | **`continue-on-error: true` on ALL CI steps** — every failure swallowed silently. Pipeline permanently green. | No failure detection |
| **K-07** | 🟡 HIGH | **H-037/H-001 invisible on dashboard** — hypothesis IDs exist only in JSON, not wired to active_picks or any dashboard view | No traceability |
| **K-08** | 🟡 HIGH | **No threshold freeze mechanism** — thresholds being actively lowered | Data snooping ongoing |
| **K-09** | 🟡 HIGH | **No hypothesis-to-emitter wiring** — rejected hypotheses (H-004 "HARNESS_REJECTED") can still trade | No enforcement |
| **K-10** | 🟡 HIGH | **No liquidity/ADV hard gate** — strategies validated on illiquid instruments | Execution risk |
| **K-11** | 🟡 HIGH | **17 strategies with >20% 7-day WR decay** — including cot_positioning (7d WR 23% vs baseline 93%) | Edge decay unaddressed |
| **K-12** | 🟡 HIGH | **COMMODITY PF=2.48 unadjusted** — inflated by COT dedup artifact (dashboard WR=85.5% vs raw WR=60.2%) | Misleading metrics |

### ONE HIGHEST-IMPACT CHANGE (per Kimi)

**Emergency-freeze all score thresholds for 90 days, then fix the outcome resolver (0.09% → >90% coverage) and DB integrity (61% → 95%) before declaring any hypothesis "live" — because H-037's "passed" status and every PF/WR/DSR metric on the dashboard are computed on data that is 39% PnL-corrupt and 99.91% unresolved, making statistical gates mathematically invalid regardless of how well the formulas are implemented.**

---

## ⚠ PEER REVIEW FINDINGS (2026-05-20)

**5-engine consensus (Grok WSL, DeepSeek, xAI, Cerebras):**

1. **H-037 (VIX term structure carry, ETF) is the FIRST harness-admissible hypothesis** — WR=58.9%, PF=1.295, n=1185, 3/4 WF folds admissible, eff=0.75. The plan's "0 admissible" premise is **structurally invalid** and must be rewritten.
2. **H-037 PF=1.295 is below Tier-2 PF>=1.5 gate** — "harness-admissible" ≠ "Tier-2 ready." Needs PF boost (~+0.22 achievable via vol-scaled sizing + tighter stops, per Cerebras review).
3. **H-001 COT (COMMODITY) REJECTED** — M-095 look-ahead leakage. WR=78.4% was falsified. After fix: WR=30%, PF=0.51.
4. **KILL H-035 intraday crypto probe** — 5-20% odds too low; redirect resources to H-021 COT small-spec.
5. **3-engine consensus on PF boost**: +0.10-0.18 realistic (not +0.22). Regime filter (VIX>14, contango>5%) needed for Tier-2.

---

## 0. HONEST CURRENT STATE (as of 2026-05-20)

### ⚠ DATA INTEGRITY WARNING

**Per Kimi Renaissance Review:** The outcome resolver is at 0.09% coverage (effectively dead). DB integrity is 61% (39% PnL mismatch). 655K ghost rows unresolved. **All metrics below are computed on corrupt/stale data.** Fix resolver + DB integrity BEFORE trusting any number.

### Canonical Performance (`pf_registry` → `policy_clean_net`)

| Class | n | PF (net) | WR% | MDD% | Tier-2 Gap | Tier-1 Gap |
|-------|--:|---------:|----:|---:|-----------|-----------|
| **FOREX** | 148 | **1.49** | 56.1 | 4.3 | PF +0.01 | PF +0.51, n +352 |
| **CRYPTO** | 1053 | 1.24 | 47.4 | 100.0 | PF +0.26, WR +2.6pp, MDD -80pp | PF +0.76, WR +7.6pp, MDD -90pp |
| **COMMODITY** | 55 | 1.42 | 54.5 | 52.4 | PF +0.08, MDD -32pp, n +45 | All 4 gaps |
| **ETF** | 2 | 11.99 | 50.0 | 2.0 | n +98 | WR +5pp, n +498 |
| **FUTURES** | 12 | 0.96 | 16.7 | 16.6 | All 3 gaps | All 4 gaps |
| **EQUITY** | 5 | 0.25 | 20.0 | 12.9 | All 3 gaps | All 4 gaps |
| **BOND** | 6 | 0.00 | 0.0 | 48.2 | All 4 gaps | All 4 gaps |

### Live Hypothesis Status (from `hypothesis_registry.json`)

| ID | Hypothesis | Class | Status | Key Metrics |
|----|------------|-------|--------|-------------|
| **H-037** | VIX term structure carry | ETF | **PASSED** harness | WR=58.9%, PF=1.295, n=1185, 3/4 folds, eff=0.75 |
| **H-001** | COT positioning | COMMODITY | **REJECTED** | M-095 look-ahead leakage. After fix: WR=30%, PF=0.51 |
| **H-021** | COT small spec exhaustion | COMMODITY | NEAR_ADMISSIBLE | 2/3 windows stable, eff_z=1.48/1.21, await window 3 (~2026-05-26) |
| **H-002** | PEAD (SUE-based) | EQUITY | SHADOW_IMPLEMENTATION | — |
| ~14 others | Various | Various | KILLED/REJECTED | Sign instability dominant failure mode |

**30+ hypotheses registered. 1 PASSED, 0 LIVE_TESTING, 1 NEAR_ADMISSIBLE, ~14 killed.**

### What Has Been Tested & Killed (EDGE_VERDICT 2026-05-18)

| Candidate | Kill Method | Verdict |
|-----------|-------------|---------|
| `method_a_score` | Walk-forward: inverts in prior window | Regime noise — DEAD |
| `risk_reward` | Leakage-control → n=17, −3%/pick; WF flips sign | Confound — DEAD |
| COT commercial-net z-score | 13yr CFTC backtest: 53.8% pooled, year-unstable | Regime-dependent — DEAD |
| `cot_positioning` | 85% CT=F; ex-CT=F n=20 WR 30% PF 0.51 | Leakage artifact — DEAD |
| CRYPTO `ml_enhanced_*` | Placeholder-stat artifact (near-zero avg_loss inflates PF) | Artifact — DEAD |
| qlib `pv_corr30` | Clean-universe: −0.14% tercile spread | DEAD |
| qlib `vol_ratio` | Clean-universe: mixed-sign, not year-stable | DEAD |
| qlib `realized_vol30` | Timing signal: beats B&H on 1/10 ETFs, 12/32 years | DEAD |
| H-006 CRYPTO funding-rate | 6yr history, n=4,838: sign-unstable | DEAD |
| H-007 COMMODITY roll-yield | n=2,964: sign-unstable | DEAD |
| H-008 BOND 2s10s | n=57,117 continuous: sign-unstable (regime noise) | DEAD |
| H-035 intraday crypto | 5-20% odds too low | DEAD |
| H-027 inventory surprise | 4/6 real EIA proxies WR=48.8%, edge=-1.03bps | DEAD |

---

## 1. TIER GATES (Institutional Thresholds — Non-Negotiable)

| Gate | Tier-2 (Charter Minimum) | Tier-1 (Renaissance) |
|------|-------------------------|----------------------|
| Profit factor (net 30bps round-trip) | ≥ 1.5 | ≥ 2.0 |
| Win rate (canonical resolved picks) | ≥ 50% | ≥ 55% |
| Max drawdown (lifetime, post-canonical) | < 20% | < 10% |
| n (clean post-dedup, post-policy-clean-net) | ≥ 100 | ≥ 500 |
| **Deflated Sharpe** (DSR, López de Prado) | > 0.95 | > 0.95 |
| **PBO** (probability of backtest overfitting) | < 0.05 | < 0.05 |
| **WFE** (walk-forward efficiency: OOS Sharpe ÷ IS Sharpe) | > 60% | > 80% |
| **Edge stability `eff`** (harness) | ≥ 0.30 same-sign, ≥3/5 windows | unchanged |
| **FDR** (Benjamini-Hochberg, q) | ≤ 0.10 | ≤ 0.05 |
| **Cost survival** (% gross retained after 30bps) | ≥ 60% | ≥ 70% |

**H-037 Status:** PASSED harness (eff=0.75, 3/4 folds) but PF=1.295 < 1.5 → **not Tier-2 ready**. Needs PF boost.  
**H-001 Status:** REJECTED (M-095 look-ahead leakage). Not salvageable.  
**H-021 Status:** NEAR_ADMISSIBLE — 2/3 windows stable, await window 3 (~2026-05-26).

### ⚠ STATISTICAL GATE BUGS (per Kimi Code Review)

| Bug | File | Severity | Impact |
|-----|------|----------|--------|
| DSR negative variance returns garbage via `max(sr_var, 1e-16)` | `statistical_gates.py` (SG-01) | CRITICAL | DSR values corrupted for high-Sharpe, negative-skew strategies |
| PBO fallback has ZERO purging | `anti_overfit_validator.py` (AOV-01) | CRITICAL | Massive information leakage; PBO meaningless |
| IS Sharpe uses market avg return, not strategy return | `walk_forward.py` (WF-02) | CRITICAL | sharpe_decay metric meaningless |
| Trade-level Sharpe annualizes by sqrt(250) on trade PnLs | `walk_forward.py` (WF-01) | HIGH | Incorrect performance assessment |
| No enforcement of rejected hypotheses | `hypothesis_registry.json` (HR-01) | MEDIUM | H-004 "HARNESS_REJECTED" can still trade |

---

## 2. STRATEGIC FORK — DECIDED (Updated Per Kimi + Peer Review)

**Decision:** **EMERGENCY FREEZE** all score thresholds for 90 days. Fix outcome resolver + DB integrity BEFORE declaring any hypothesis "live." Paper-only until harness passes + Tier-2 gates met + data integrity >95%.

**Priority Reordering (per Kimi Renaissance Review + 5-engine consensus):**
1. **P0: Fix outcome resolver** (0.09% → >90% coverage) — without this, ALL metrics are stale
2. **P0: Fix DB integrity** (61% → 95%, 655K ghost rows) — without this, ALL metrics are corrupt
3. **P0: Freeze all score thresholds** for 90 days — stop data snooping immediately
4. **P0: Fix 4 statistical bugs** (DSR variance, PBO purging, IS Sharpe, trade Sharpe) — without this, ALL gates are invalid
5. **H-037 VIX carry (ETF)** — paper trading active, 30-day forward verification started
6. **H-021 COT small-spec (COMMODITY)** — await window 3 (~2026-05-26)
7. **FOREX** — 0.01 PF away from Tier-2; fastest unlock if data integrity fixed

---

## 3. CONCRETE ACTION PLAN — PRIORITIZED

### PHASE 0: EMERGENCY — Data Integrity + Statistical Gate Fixes (Next 24-48 Hours) — P0

**Per Kimi Renaissance Review: "Emergency-freeze all score thresholds for 90 days, then fix the outcome resolver and DB integrity before declaring any hypothesis 'live' — because H-037's 'passed' status and every PF/WR/DSR metric are computed on data that is 39% PnL-corrupt and 99.91% unresolved."**

| ID | Action | File(s) | Expected Impact | Effort |
|----|--------|---------|-----------------|--------|
| **E0-1** | **EMERGENCY FREEZE all score thresholds** for 90 days | `audit_trail/quality_gates.py` | Stop data snooping immediately | 1h |
| **E0-2** | **Fix outcome resolver** (0.09% → >90% coverage) | `audit_trail/universal_pick_resolver.py` | Enable live validation of all new picks | 8h |
| **E0-3** | **Fix DB integrity** (61% → 95%, 655K ghost rows) | `audit_trail/dashboard_generator.py` + SQL | All downstream metrics valid | 12h |
| **E0-4** | **Fix DSR negative variance bug** (SG-01) — return DSR=0 when variance invalid | `tools/statistical_gates.py`, `alpha_engine/anti_overfit_validator.py` | DSR values correct | 2h |
| **E0-5** | **Fix PBO fallback zero-purging bug** (AOV-01) — install `timeseriescv` as hard dependency, remove non-purging fallback | `alpha_engine/anti_overfit_validator.py` | PBO meaningful | 2h |
| **E0-6** | **Fix IS Sharpe computation** (WF-02) — use actual strategy returns, not market average | `alpha_engine/walk_forward.py` | sharpe_decay metric valid | 2h |
| **E0-7** | **Fix trade-level Sharpe annualization** (WF-01) — use correct formula with trading frequency | `alpha_engine/walk_forward.py` | Performance assessment correct | 2h |
| **E0-8** | **Remove `continue-on-error: true`** from critical CI steps | `.github/workflows/audit-dashboard.yml`, `ab_analysis.yml` | Failures visible | 1h |
| **E0-9** | **Redact DB credentials** from workflow files (host + username in plaintext) | `.github/workflows/ab_analysis.yml` | Security fix | 30min |
| **E0-10** | **Wire hypothesis-to-emitter** — prevent rejected hypotheses from trading | `alpha_engine/production_scanner.py` + `hypothesis_registry.json` | H-004 can't trade if rejected | 4h |

**H-037 paper trading already shipped** (commit dfaba75f32f). 30-day forward verification ACTIVE, Day 0/30.
**DSR/PBO/WFE/FDR tools already shipped** (`tools/dsr.py`, `tools/pbo.py`, `tools/wfe.py`, `tools/fdr_control.py`).
**H-035 already killed** in hypothesis_registry.json.

### PHASE 1: Data Pipeline + Emitter Hygiene (Days 2-7) — P1

| ID | Action | File(s) | Expected Impact | Effort |
|----|--------|---------|-----------------|--------|
| **D1-1** | **Add threshold freeze mechanism** — env var `THRESHOLD_FREEZE=1` blocks all score floor changes | `audit_trail/quality_gates.py` | Prevent future snooping | 2h |
| **D1-2** | **Add liquidity/ADV hard gate** — minimum ADV filter per asset class | `audit_trail/quality_gates.py` | No illiquid instrument validation | 4h |
| **D1-3** | **Widen harness ledger scope** (1/32 → ≥80% of files visible) | `tools/edge_stability_harness.py::_load()` | All cohorts scoreable | 4h |
| **D1-4** | **Dedup guard** before `at_raw_picks` append — re-emission 36% → <5% | emitter layer + `dedup_hash` | Tightens canonical n | 4h |
| **D1-5** | **Dashboard reads only `pf_registry.json::by_asset_class_policy_clean_net`** | `audit_dashboard/dashboard_generator.py` | Stops inflated tiles | 4h |
| **D1-6** | **Investigate `ensemble` CRYPTO** (n=79, WR=5.1%, PF=0.01, −56pp) | `tools/mutation_analysis.py` | Confirm ghost vs real drag | 1h |
| **D1-7** | **Block confirmed drag emitters** — ensemble/CRYPTO, toxic pairs | `BLOCKED_ASSET_STRATEGY_PAIRS` | CRYPTO PF 0.64 → 1.21 | 1h |
| **D1-8** | **Classify UNKNOWN rows** (n=38, PF=1.72) | `audit_trail/asset_classification.py` | UNKNOWN row → 0 | 4h |
| **D1-9** | **Halt FUTURES emitter** — n=12, PF=0.96, zero edge | workflow gate | Stop wasting compute | 1h |

### PHASE 2: Emitter Hygiene (Days 7-14) — P1

#### FOREX — Push Borderline to T2 (PF 1.49 → ~1.51)

| ID | Action | File(s) | Expected Impact | Effort |
|----|--------|---------|-----------------|--------|
| **F-1** | **Shadow `cta_replicator` FOREX** (n=97, WR=64.9%, PF=2.38) | `ml_consensus/consensus.py` | n→150 + harness clearance | — |
| **F-2** | **Block `alpha_engine`/FOREX** (n=15, WR=40%, PF=0.84) | `BLOCKED_ASSET_STRATEGY_PAIRS` | 0 new alpha_engine FOREX | 1h |
| **F-3** | **Block `multi_asset_scanner`/FOREX** (n=11, PF=0.21, WR=9.1%) | `BLOCKED_ASSET_STRATEGY_PAIRS` | 0 new picks | 1h |
| **F-4** | **Harness run on `cta_replicator`** once n≥150 | `edge_stability_harness.py` | Verdict: ADMISSIBLE/REJECTED | — |

#### COMMODITY — Close the n-Gap (n=55 → n=100)

| ID | Action | File(s) | Expected Impact | Effort |
|----|--------|---------|-----------------|--------|
| **K-1** | **Whitelist `multi_asset_copytrader` COMMODITY** (n=54, WR=53.7%, PF=1.38) | `EMITTER_WHITELIST` | Continue emission | — |
| **K-2** | **Block `cta_replicator`/COMMODITY** per Grok autopsy | `BLOCKED_ASSET_STRATEGY_PAIRS` | 0 new cta_replicator COMMODITY | 1h |
| **K-3** | **At n=100: harness run** | `edge_stability_harness.py` | ADMISSIBLE → T2; else kill | — |

#### EQUITY / ETF / BOND — Too Thin to Act On

| ID | Action | Note |
|----|--------|------|
| **E-1** | Wait for canonical n≥100 EQUITY; then harness | Passive |
| **ETF-1** | H-037 paper track is the ONLY ETF action | Active — see D0-1 |
| **BOND-1** | n=5, 0% WR. Hold all sizing. Wait for emitter activity | Passive |

### PHASE 3: Scale & Harden (Days 14-90) — P2

| ID | Action | Expected Impact | Effort |
|----|--------|-----------------|--------|
| **P3-1** | **H-037 30-day paper result** — if PF≥1.5 forward → Tier-2 candidate | First class to clear | Ongoing |
| **P3-2** | **H-001 3rd window result** — if 3/3 windows → full admissibility | COMMODITY edge proven | Time-gated |
| **P3-3** | **Kill-switch automation** — rolling WR/PF monitors auto-disable strategies | Prevents alpha decay | 3 days |
| **P3-4** | **Polymarket/Kalshi prediction market signals** — genuinely new input class | New edge source | 1 week |
| **P3-5** | **On-chain data integration** (Glassnode, DefiLlama) | New edge source | 2+ weeks |

---

## 4. CROSS-CUTTING INFRASTRUCTURE (Raises Every Class)

| ID | Item | Status | Why |
|----|------|--------|-----|
| **X-1** | **HARNESS_FDR_GATE** — Benjamini-Hochberg q=0.10 in `is_admissible()` | RECOMMENDED (unanimous swarm) | Multiple-testing correction across 30+ hypotheses |
| **X-2** | **DSR (Deflated Sharpe)** — López de Prado formula | NEW — D0-2 | DSR > 0.95 is Renaissance-grade marker |
| **X-3** | **PBO (Probability of Backtest Overfitting)** — CSCV | NEW — D0-2 | PBO < 0.05 required for institutional defense |
| **X-4** | **WFE (Walk-Forward Efficiency)** — OOS Sharpe ÷ IS Sharpe | NEW — D0-2 | > 60% Tier-2 / > 80% Tier-1 |
| **X-5** | Widen `is_admissible()` ledger scope from 1/32 files → ≥80% | OPEN, P1 | Most cohorts invisible to harness |
| **X-6** | Confidence corruption clamp at emission | SHIPPED across 3 insert paths | Drift continues unless write-gate enforced |
| **X-7** | Dashboard tiles read **only** `pf_registry.json::by_asset_class_policy_clean_net` | PARTIAL | Stops inflated tiles |
| **X-8** | LDP-gate pre-flight check (lookahead / leakage / inverted confidence) | NEW | Run before any new hypothesis lands |

---

## 5. RENAISSANCE-GRADE PROMPT TEMPLATE (Canonical)

Use this for every harvest run against any AI engine:

```
You are a senior quant researcher at Renaissance Technologies. Our end goal
is a statistically defensible edge per asset class:

  DSR > 0.95  ·  PBO < 0.05  ·  WFE > 60%  ·  FDR(q) ≤ 0.10  ·  forward WR > 55%
  PF > 1.8 (Tier-2 push) / PF > 2.0 (Tier-1)  ·  MDD < {20%|10%}  ·  n ≥ {100|500}
  Edge stability `eff` ≥ 0.30 same-sign across ≥3 of 5 14-day windows
  Cost survival ≥ 60% (30 bps round-trip)

Current state:
  - H-037 (ETF VIX carry): PASSED harness, WR=58.9%, PF=1.295, n=1185, eff=0.75 (NEEDS PF BOOST TO 1.5)
  - H-001 (COMMODITY COT): LIVE_TESTING, WR=78.4%, n=134, 2/3 windows stable
  - Canonical ledger: audit_dashboard/data/pf_registry.json → by_asset_class_policy_clean_net
  - Hypothesis registry: reports/hypothesis_registry.json (30+ registered, 1 passed, 1 live, ~14 killed)
  - Harness: tools/edge_stability_harness.py::is_admissible() (UNMODIFIED — M-107)
  - Toxic pairs blocked: quan_engine/CRYPTO, cta_replicator/COMMODITY, ensemble/CRYPTO

Asset class focus: {CLASS}

Task — output ONLY production-ready code + numbers:
  1. LDP-gate analysis on the latest {class}_recent.csv from canonical ledger
  2. Identify any lookahead, leakage, or inverted-confidence in:
     - audit_trail/quality_gates.py
     - alpha_engine/forward_validator.py
     - alpha_engine/emitter_whitelist.py
  3. Output:
     - A ready-to-apply .patch file for any fix
     - The exact `tools/edge_stability_harness.py is_admissible(...)` command
       to run AFTER the patch
     - Projected Sharpe / PF / WR / DSR / PBO / WFE after the change
  4. If no admissible hypothesis exists for this class, suggest exactly ONE
     pre-registerable family (NOT on the killed list) with:
       - Family name, bar_freq + data source (free-data only)
       - Causal economic prior (1 sentence)
       - test_statistic (must invoke `is_admissible()` verbatim)

Do not give general advice. No filler. Production-ready code + numbers ONLY.
```

---

## 6. SCORECARD — TRACK PROGRESS

| Metric | Current | Target (T2) | Target (T1) | Status |
|--------|---------|-------------|-------------|--------|
| **Admissible signals** | 1 passed (H-037), PF<1.5 | ≥1 per class, PF≥1.5 | ≥3 per class | 🟡 |
| **H-037 PF** | 1.295 | ≥1.5 | ≥2.0 | 🟡 (needs +0.22 boost) |
| **H-037 WR** | 58.9% | ≥50% | ≥55% | ✅ |
| **H-037 n** | 1185 | ≥100 | ≥500 | ✅ |
| **H-037 eff** | 0.75 | ≥0.30 | ≥0.30 | ✅ |
| **H-037 WF folds** | 3/4 | ≥3/5 | ≥3/5 | ✅ |
| **H-001 WR** | 78.4% | ≥50% | ≥55% | ✅ |
| **H-001 n** | 134 | ≥100 | ≥500 | ✅ |
| **H-001 windows** | 2/3 | ≥3/5 | ≥3/5 | 🟡 |
| **CRYPTO PF** | 0.64 | ≥1.5 | ≥2.0 | 🔴 |
| **FOREX PF** | 1.49 | ≥1.5 | ≥2.0 | 🟡 |
| **COMMODITY PF** | 1.42 | ≥1.5 | ≥2.0 | 🟡 |
| **COMMODITY n** | 55 | ≥100 | ≥500 | 🔴 |
| **EQUITY n** | 5 | ≥100 | ≥500 | 🔴 |
| **Harness scope** | 1/32 files | ≥80% | 100% | 🔴 |
| **Hypotheses killed** | ~14 | — | — | — |

---

## 7. DECISIONS NEEDING OPERATOR APPROVAL

| Decision | Swarm Recommendation | Status |
|----------|---------------------|--------|
| **H-037 paper trading NOW** | Yes — 30-day forward verification with kill-switch | ☐ |
| **H-037 PF boost** (vol-scaled sizing + tighter stops) | Yes — target +0.22 PF → 1.52 | ☐ |
| **H-001 COT 3rd window** — pre-commit end date, stream forward | Yes — fastest path to full admissibility | ☐ |
| **KILL H-035 intraday crypto probe** | Yes — 5-20% odds too low, redirect to H-001/H-037 | ☐ |
| Buy GX10 in 90d | **No** — revisit after 60d pipeline green | ☐ |
| `EMITTER_WHITELIST_ENFORCE=1` | **After** 200-close forward clean window | ☐ |
| FOREX stays at 0% risk cap | Yes — unanimous across all rounds | ☐ |

---

## 8. PARKED (NOT EDGE-IMPROVING — DO NOT WORK ON THESE)

| Item | Reason Parked |
|------|---------------|
| Hardcoded credential fixes | Not pick quality — fix after edge proven |
| Dashboard UI polish / template.html static banner updates | Cosmetic |
| N_INSUFFICIENT warning badges | Display-only |
| Ollama local model benchmarks | Tooling |
| Idea harvest mega scripts | Tooling |
| USB model inventory | Tooling |
| Cross-PC protocol debugging | Infra |
| Swarm infrastructure fixes | Tooling |
| Pick traceability Phase 1 | Nice-to-have, not edge-improving |
| **H-035 intraday crypto probe** | KILLED per peer review (5-20% odds) |

---

## 9. GUARDRAILS

1. **No score ranks or gates picks** unless it clears `edge_stability_harness.py` (eff≥0.30, same sign, ≥3/5 windows)
2. **No real-money sizing** until ≥4 weeks paper-traded with non-negative CLV and post-cost expectancy > 0
3. **Pre-register every hypothesis** before touching data — no p-hacking (M-107)
4. **`[skip ci]` on all workflow commits** — prevent infinite trigger loops
5. **Document every fix** in `updates/` with `.MD` file per AGENTS.md
6. **Only push own changes** — never push commits from other agents/tools without approval
7. **No auto-run forbidden scripts** (`check_active_picks.py`, `smart_picks_engine.py`) — run only when explicitly requested
8. **Do NOT re-test killed families** on the same ledger (convergence trap killed ~14 prior)
9. **Do NOT trust dashboard tiles** — canonical `pf_registry.json::by_asset_class_policy_clean_net` only
10. **Do NOT claim any class is money-ready** until harness clears + Tier-2 PF≥1.5 + forward 30-day OOS

---

## 10. KEY FILE REFERENCE

| Purpose | Path |
|---------|------|
| Edge stability harness (THE GATE) | `tools/edge_stability_harness.py` |
| PF registry (canonical) | `audit_dashboard/data/pf_registry.json` |
| Hypothesis registry | `reports/hypothesis_registry.json` |
| Quality gates | `audit_trail/quality_gates.py` |
| Edge verdict (authoritative) | `reports/EDGE_VERDICT_2026-05-18.md` |
| PF improvement per class | `reports/PF_IMPROVEMENT_PER_CLASS_2026-05-19T2137Z.md` |
| Quant rescue verdict | `reports/QUANT_RESCUE_SWARM_VERDICT_2026-05-19_cursor.md` |
| North star upgrade | `reports/MONEY_MAKER_READYV2_NORTH_STAR_2026-05-19T2350Z.md` |
| Audit pipeline review | `updates/2026-05-20-audit-pipeline-review-chatlog.md` |

---

## 11. FIRST 48 HOURS — IMMEDIATE ACTIONS

1. **D0-1: Stand up H-037 paper trading** — 30-day forward verification with kill-switch
2. **D0-2: Ship DSR/PBO/WFE/FDR tools** — complete north-star metric suite
3. **D0-3: H-037 PF boost** — vol-scaled sizing + tighter stops (target +0.22 → 1.52)
4. **D0-4: H-001 COT 3rd window** — lock parameters, pre-commit end date, stream forward
5. **D0-5: Kill H-035** in hypothesis_registry.json
6. **D0-6: Rewrite plan baseline** — update "0 admissible" → "1 passed, 1 live, 1 near" ✅ DONE

---

*This document is the single source of truth for the north star objective. All commits should advance one or more items in this plan. If a PR does not map to a P0/P1/P2 item here, it is a goal mismatch unless P0 prod-protect.*

*Peer reviewed by: Grok WSL (2 rounds), DeepSeek API, xAI Grok-3-mini API, Cerebras gpt-oss-120b API. Consensus: H-037 is first admissible, H-001 gets priority, H-035 should be killed, plan premise was structurally invalid.*
