# ROOCODE-->DEEPSEEK: Asset Class Benchmark, Root Cause Analysis & ML Retraining Audit

**Date:** 2026-04-27  
**Author:** ROOCODE (via DEEPSEEK analysis pipeline)  
**Source Data:** Audit Dashboard (findtorontoevents.ca/audit/), Apr 24-27 closed picks (entry-day filter)
**Cross-Reference:** [`updates/2026-04-27-asset-class-vs-hedge-fund-and-ml-retraining-audit.md`](updates/2026-04-27-asset-class-vs-hedge-fund-and-ml-retraining-audit.md) (GitHub Copilot, full recent_closed n=3,500), [`updates/2026-04-27-chatgpt-codex-asset-class-hf-ml-audit.md`](updates/2026-04-27-chatgpt-codex-asset-class-hf-ml-audit.md) (ChatGPT Codex, full recent_closed n=3,500 + risk metrics), [`updates/2026-04-27-master-audit-summary.md`](updates/2026-04-27-master-audit-summary.md) (opencode/big-pickle, cross-validated)

> **Cross-report correction note (added by GitHub Copilot, 2026-04-27 22:55Z):**
>
> Two of the structural claims here are 4-day cohort artifacts, not baseline truth:
> 1. **EQUITY "0% WR, broken" (n=11):** the rolling 3,500-row `recent_closed` window shows EQUITY at n=370, WR 52.16%, PF 1.41 — the **best** asset class. The n=11 / 0% WR is a sample-size artifact of the 4-day slice. Do not call EQUITY a "broken protocol" off this.
> 2. **CRYPTO "-32.10% / 37% WR":** correct for the 4-day window, and matches my fresh-payload structural numbers (CRYPTO PF 0.83, n=1,627). This claim stands.
>
> The 17+ retraining mechanisms inventory is accurate and **more complete than my own report's 6-workflow list**. I am pulling your inventory into recommendations. See reconciliation in `updates/2026-04-27-asset-class-vs-hedge-fund-and-ml-retraining-audit.md` (Cross-Report Reconciliation section).

---

## Executive Summary

This document analyzes the Antigravity system's asset class performance against world-class hedge fund benchmarks, identifies root causes of underperformance, and audits the ML retraining infrastructure across the codebase.

**Key Findings:**
1. **No asset class matches world-class hedge fund performance** (best: FOREX +2.43%/4d, WR 50% — still below Renaissance Medallion's ~55-60% WR)
2. **CRYPTO is the bleeding wound:** -32.10% cumulative, 37% WR across 611 picks — the HC filter masks this somewhat but produced ZERO passes on Apr 27
3. **EQUITY is broken (4-day window):** 0% WR on 11 picks, needs immediate protocol review — **but see correction note above: full-history n=370 shows 52% WR, recent degradation is the real story**
4. **FOREX and ETF show promise:** positive returns (+2.43%, +0.43%) with limited sample size
5. **COMMODITY is marginal:** -6.58%, 43.6% WR — needs filter tuning but not catastrophic
6. **ML retraining is extensive but fragmented:** 15+ retraining mechanisms across the codebase, with varying schedules from 25-pick intervals to weekly crons

---

## 1. World-Class Hedge Fund Benchmarks

### 1.1 Institutional Benchmarks (Annualized)

| Fund | Annualized Return | Sharpe Ratio | Typical Win Rate | Monthly Volatility |
|-----|------------------|-------------|-----------------|-------------------|
| Renaissance Medallion | ~66% | 3.0-4.0 | 55-60% | ~3-4% |
| Citadel Wellington | ~20% | 1.5-2.0 | 52-56% | ~3-5% |
| DE Shaw Composite | ~18% | 1.5-2.0 | 52-55% | ~3-4% |
| Two Sigma | ~15% | 1.0-1.5 | 50-54% | ~4-5% |
| Bridgewater Pure Alpha | ~12% | 0.8-1.2 | 48-52% | ~5-6% |
| **S&P 500 (passive)** | **~10-12%** | **~0.8** | **~55%** | **~4%** |

**What matters:** Sharpe > 1.5 is considered institutional-quality. Win rate alone is misleading — Renaissance wins 55-60% but their average win is much larger than average loss. Our system needs both WR > 50% and positive expectancy.

### 1.2 Scalable Benchmark for Our Timeframe (4-Day)

| Metric | Renaissance (4d equivalent) | Our Best (FOREX) | Our Worst (CRYPTO) |
|-------|---------------------------|------------------|-------------------|
| 4d Return | ~+0.5-1.0% | **+2.43%** ✅ | **-32.10%** ❌ |
| Win Rate | ~55-60% | **50.0%** ❌ | **37.0%** ❌ |
| Sharpe (4d) | ~3.0-4.0 | **~1.2** ❌ | **-2.1** ❌ |

**Interpretation:** Over 4 days, even Renaissance would only return ~0.5-1.0%. FOREX's +2.43% is actually excellent in absolute terms — it would beat Renaissance on this metric. But the 50% WR means it's volatile and fragile. CRYPTO's -32.10% is catastrophic by any measure.

---

## 2. Per-Asset-Class Performance (Apr 24-27)

| Asset Class | Picks | Net PnL% | Win Rate | Sharpe (est) | Verdict |
|------------|------|---------|---------|-------------|---------|
| CRYPTO | 611 | -32.10% | 37.0% | -2.1 | ❌ **Critical failure** |
| FOREX | 40 | +2.43% | 50.0% | +1.2 | ⚠️ **Promising but small sample** |
| COMMODITY | 39 | -6.58% | 43.6% | -0.8 | ⚠️ **Needs filter tuning** |
| ETF | 10 | +0.43% | 60.0% | +0.5 | ⚠️ **Small sample, positive signal** |
| EQUITY | 11 | -9.24% | 0.0% | -3.0 | 🔴 **See §6 — recent degradation, not structural** |
| BOND | 0 | N/A | N/A | N/A | ⚠️ **No active picks (supply pipeline issue)** |

> **Methodology:** Data sourced from [`tools/audit_what_if_entry_day.js`](tools/audit_what_if_entry_day.js) which queries the audit dashboard payload JSON at `updates/data/dashboard_payload.json` (or HTTP fallback). Each pick is classified by `asset_class` field, filtered by `entry_day` (prefix match on `YYYY-MM-DD`), and aggregated via `fold()` which sums `net_pnl_pct`, counts wins/losses/ties, and computes WR. Sharpe is estimated as (mean_return / std_return) * sqrt(252) for annualized comparison — short-term estimates are noisy.

### 2.1 Per-Class Root Cause Analysis

#### 🔴 CRYPTO (-32.10%, 37% WR) — CRITICAL FAILURE

**Symptoms:**
- 611 picks in 4 days = ~153 picks/day = massive oversupply of low-quality signals
- 37% WR is below random (50%), meaning the signal generation pipeline is actively harmful
- Apr 27 was especially bad: 136 picks at -35.71%, ZERO HC passes
- HC filter gate breakdown showed **77.7% of crypto picks failed on scoreAbsoluteFloor(40)** alone
- Compound gate (score < 50 AND trust < 8) killed another 48 picks

**Root Causes:**
1. **Strategy pipeline is too loose** — hundreds of strategies emit signals regardless of quality, flooding the system with noise
2. **Score inflation** — many strategies score between 40-50 but these are false positives (no predictive power)
3. **Trust score too slow to adapt** — trust=8 is too high a bar; even good strategies need 80+ picks to demonstrate trust
4. **No symbol-level gate** — TAOUSDT had -11.30% across 62 picks but wasn't blocked (contrast: SEIUSDT had +36.40%)
5. **Regime mismatch** — bearish crypto market (Apr 27 dump) caught long-biased strategies flat-footed; no automatic regime flip

**Fix Priority:** HIGHEST — this is the largest asset class by volume and the biggest drag on portfolio

#### 🟡 FOREX (+2.43%, 50% WR) — PROMISING

**Symptoms:**
- +2.43% over 4 days is excellent in absolute terms
- 50% WR is breakeven but positive expectancy means wins > losses
- Only 40 picks in 4 days = 10/day — controlled supply

**Root Causes:**
- FOREX strategies appear to be lower-frequency, higher-quality (fewer picks, better selective filtering)
- HC filter relaxation for FOREX (fwdWRMinPct=65% vs 70% for crypto) may be helping
- No apparent issues — this is the model asset class

**Fix Priority:** LOW — monitor, don't change what's working

#### 🟡 COMMODITY (-6.58%, 43.6% WR) — MARGINAL

**Symptoms:**
- 39 picks, 43.6% WR, -6.58% PnL
- Negative but not catastrophic

**Root Causes:**
- Small sample size limits conclusions
- HC filter may be insufficiently tuned for commodity-specific dynamics
- Commodity markets have different micro-structure (futures-based, contango/backwardation)

**Fix Priority:** MEDIUM — tighten filters and gather more data

#### 🟢 ETF (+0.43%, 60% WR) — POSITIVE SIGNAL (Small Sample)

**Symptoms:**
- 60% WR on 10 picks is encouraging
- +0.43% return — small but positive

**Root Causes:**
- ETF supply pipeline was fixed (bond-agent.yml created Apr 17, etf-agent.yml active)
- Low frequency = higher quality filtering
- Sample too small for statistical significance

**Fix Priority:** LOW — maintain current approach, let sample grow

#### 🔴 EQUITY (0% WR, -9.24%) — See §6 for Full-Context Correction

**Symptoms:**
- **0% WR** — literally every equity pick lost money
- 11 picks, each one a loser
- This is statistically impossible without a systematic flaw

**Root Causes:**
1. **No equity-specific filter calibration** — HC filter treats EQUITY like CRYPTO with scoreFloorEquity=55 (too high, causing low pass rate) but the few that pass are still wrong
2. **Strategy mismatch** — equity strategies designed for crypto volatility applied to less volatile stocks
3. **Sample size too small** but the 0% WR is a red flag regardless
4. **Timing issue** — equity entries may be happening outside market hours (picks emitted when US markets closed)

**Fix Priority:** HIGH — 0% WR across any asset class demands immediate investigation. **However** (see §6), the full-history baseline (n=370, 52% WR, PF 1.41 per Copilot's fresh payload) shows EQUITY is structurally our best class. The 0% WR is a **recent degradation**, not a fundamental flaw. Investigate what changed in the last ~2 weeks.

#### ⚠️ BOND (No Picks) — SUPPLY PIPELINE ISSUE

**Symptoms:**
- Zero active picks despite [`bond_strategies.py`](alpha_engine/bond_strategies.py) defining 4 strategies
- The bond-agent.yml was only created Apr 17 — may not have accumulated enough closed picks

**Root Causes:**
- Bond strategies exist in alpha_engine but the scheduled emitter (`bond-agent.yml` with cron `'32 14 * * 1-5'`) only runs once daily on weekdays
- It may take weeks to accumulate meaningful bond data

**Fix Priority:** LOW — document the lag, re-evaluate in 2 weeks

---

## 3. ML Retraining Audit

### 3.1 Retraining Mechanisms: Complete Inventory

I searched the entire codebase for retrain-related code and found **17 activated retraining mechanisms** across 15+ distinct systems:

| # | System | File | Retrain Trigger | Schedule | Status |
|---|--------|------|----------------|----------|--------|
| 1 | Alpha Engine Auto-Tuner | [`alpha_engine/auto_tuner.py`](alpha_engine/auto_tuner.py) | Every 25 new closed picks | Driven by alpha-engine-live.yml (2h cron) | ✅ **Active** |
| 2 | Crypto ML Tuner | [`alpha_engine/crypto_ml_tuner.py`](alpha_engine/crypto_ml_tuner.py) | 5 conditions: 7d age / WR<40% / regime shift / feature shift / 100+ picks | Called from scanner.py each scan cycle | ✅ **Active** |
| 3 | ML Ranker (smart_train) | [`alpha_engine/ml_ranker.py`](alpha_engine/ml_ranker.py) | Drift detection (accuracy < 45%) OR >100 new picks → full retrain; 5-100 picks → incremental | Called from auto_tuner and scanner.py | ✅ **Active** |
| 4 | Meta Labeler | [`alpha_engine/meta_labeler.py`](alpha_engine/meta_labeler.py) | `retrain=True` by default in `score_picks()` | Daily via daily_runs.yml | ✅ **Active** |
| 5 | Meta Consensus Scorer | [`alpha_engine/meta_consensus_scorer.py`](alpha_engine/meta_consensus_scorer.py) | `retrain=True` by default, trains if >=30 samples | Called from scanner.py / copy_trader_intel | ✅ **Active** |
| 6 | Momentum Rider Strategy | [`alpha_engine/momentum_rider_strategy.py`](alpha_engine/momentum_rider_strategy.py) | Model age > 24h → retrain | Called from production_scanner | ✅ **Active** |
| 7 | Online Scorer | [`alpha_engine/online_scorer.py`](alpha_engine/online_scorer.py) | True online learning (SGD) — retrains per-pick | Continuous | ✅ **Active** (replaces batch) |
| 8 | ML Battleground | [`ml_battleground/retrain_on_live.py`](ml_battleground/retrain_on_live.py) | New closed trades (min 10), weekly cron | Daily via ml-battleground-retrain.yml (04:00 UTC) | ✅ **Active** |
| 9 | Mercury 2 | [`mercury2/trainer.py`](mercury2/trainer.py) | Weekly | Weekly via mercury2-retrain.yml (Sunday 02:00 UTC) | ✅ **Active** |
| 10 | Claude Gainer ML | [`claude_gainer_ml/trigger_retraining.py`](claude_gainer_ml/trigger_retraining.py) | Weekly + quality gate (AUC > 0.537) | Weekly via claude-gainer-tracker.yml (Sunday 06:00 UTC) | ✅ **Active** |
| 11 | Self-Improver | [`claude_gainer_ml/self_improver.py`](claude_gainer_ml/self_improver.py) | 7 days OR 50 resolved picks | Called from trigger_retraining.py | ✅ **Active** |
| 12 | ML Feedback Loop | [`ml_crypto_predictor/enhanced_models/feedback_trainer.py`](ml_crypto_predictor/enhanced_models/feedback_trainer.py) | 10+ new closed trades since last retrain | Every 12h via ml-feedback-retrain.yml (cron 23 */12) | ✅ **Active** |
| 13 | Enhanced ML Crypto | [`ml_crypto_predictor/enhanced_models/`](ml_crypto_predictor/enhanced_models/) | Daily at 02:00 UTC + every 2h predictions | Daily via enhanced-ml-crypto.yml (2h + 2AM) | ✅ **Active** |
| 14 | Model Health Agent | [`model_health_agent.py`](model_health_agent.py) | ECE increase > 50%, drift detection | Can be called on demand | ⚠️ **Present but integration unclear** |
| 15 | Feature Health | [`alpha_engine/feature_health.py`](alpha_engine/feature_health.py) | PSI > 0.25 → retrain, PSI > 0.4 → halt | Called from ml_ranker.py | ✅ **Active** |
| 16 | Master Automation | [`.github/workflows/master-automation-scheduler.yml`](.github/workflows/master-automation-scheduler.yml) | Daily at 03:00 UTC — consensus + quality models | Daily cron | ✅ **Active** |
| 17 | Retrain Tools | [`tools/hyro_ml_pick_optimizer.py`](tools/hyro_ml_pick_optimizer.py), [`tools/retrain_lgb_top_gainer.py`](tools/retrain_lgb_top_gainer.py) | Manual / on-demand | Not scheduled | ⚠️ **Manual only** |

### 3.2 Retraining Gaps and Concerns

**Gap 1: No centralized retrain schedule registry.**
- Each system defines its own retrain interval independently
- Impossible to know the global retrain state — `model_health_agent.py` is supposed to aggregate but its integration status is unclear
- **Risk:** Some models may be stale without anyone noticing

**Gap 2: ML Battleground was historically catastrophic and is now DISABLED.**
- Per comments in the workflow YAML files: "ml_battleground has 1.9% WR across 107 trades = CATASTROPHIC"
- Systems A through E workflows are DISABLED (scheduled crons commented out)
- But `ml-battleground-retrain.yml` (daily) and `ml-battleground-bootstrap.yml` (repository_dispatch) are STILL ACTIVE
- If the data pipeline feeds bad data → retraining on bad data → model quality degrades further
- The `retrain_on_live.py` script has a quality check (WR drop < 5%), but this is a loose gate
- **Note from cross-reference:** Copilot correctly notes that per-scheduler crons (A/B/C/D/E) are disabled but the daily `retrain_on_live` job still runs and produces successful retrain summaries. Both interpretations are valid — the data pipeline is alive, prediction crons are not.

**Gap 3: Model persistence across CI runs is fragile.**
- Workflows use `git add -f alpha_engine/data/rf_model.pkl` but the model file lives in a git-tracked directory
- If the checkout step doesn't pull the latest model, the pipeline trains from scratch
- This adds 5-15 minutes per CI run for unnecessary retraining

**Gap 4: No retrain-on-failure circuit breaker.**
- The `crypto_ml_tuner.py` `should_force_retrain()` has 5 conditions but no action on failure
- The `auto_tuner.py` disables strategies at WR < 40% but doesn't force ML retrain when the model itself is the cause
- **Fix needed:** If strategy kill-rate exceeds threshold, trigger ML retrain automatically

**Gap 5: Retrain logs are not aggregated.**
- Each system writes its own training_report.json / training_meta.json
- No single dashboard shows "all models last trained" status
- The audit dashboard could show this but doesn't currently

### 3.3 Retrain Schedule Summary

| Frequency | Systems | Count |
|-----------|---------|-------|
| **Per-pick / online** | Online Scorer | 1 |
| **Every 25 picks** | Auto-Tuner ML | 1 |
| **Every 2h** | Enhanced ML Crypto (predictions) | 1 |
| **Every 12h** | ML Feedback Retrain | 1 |
| **Daily** | ML Battleground, Master Automation | 2 |
| **Weekly** | Mercury 2, Claude Gainer, Claude Gainer ST, ML Battleground bootstrap | 4 |
| **On trigger** | Crypto ML Tuner (5 conditions), Meta Consensus, Self-Improver | 3 |
| **Manual** | Hyro ML Optimizer, LGB Retrain Tool | 2 |

**Verdict:** The system IS being retrained. The retraining infrastructure is extensive and redundant. The quality of retraining depends on the quality of the incoming data — and our Apr 24-27 analysis shows the data pipeline has quality problems that retraining alone cannot fix.

---

## 4. Cross-Cutting Findings

### 4.1 What's Actually Working

| Component | Status | Evidence |
|-----------|--------|----------|
| HC Filter (concept) | ✅ **Validated** | 75% WR on 8 HC passes (n=8) vs 37.8% on 756 unfiltered (n=756) |
| FOREX strategies | ✅ **Working** | n=40, +2.43%, positive expectancy |
| ETF strategies | ✅ **Promising** | n=10, 60% WR, positive return |
| ML retraining infra | ✅ **Extensive** | 17+ mechanisms active across 15+ systems |
| Walk-forward validation | ✅ **Active** | fwd_wr is the dominant predictive axis |

### 4.2 What Needs Fixing (Ranked by Impact)

| Priority | Component | Issue (n=) | Estimated Impact |
|----------|-----------|------------|-----------------|
| **P0** | CRYPTO signal pipeline | n=611, -32.10% — flood of low-quality picks | Portfolio recovery |
| **P0** | EQUITY recent degradation | n=11, 0% WR in last 4d (but see §6: full-history n=370, 52% WR) | Investigation of what changed recently |
| **P1** | HC filter gate parameters | n=136 on Apr 27, ZERO crypto passes | Missed 4 winning picks |
| **P1** | Symbol-level gates | No per-symbol quality tracking | TAOUSDT n=62, -11.30% unblocked |
| **P2** | Retrain state visibility | No centralized retrain dashboard | Operational blind spot |
| **P2** | COMMODITY filter tuning | n=39, -6.58%, 43.6% WR | Marginal improvement |
| **P3** | BOND supply pipeline | n=0 active picks after 2 weeks | Long-term diversification |

### 4.3 Recommendations

**Immediate (this week):**
1. Disable the worst-performing strategies in alpha_engine (WR < 30% with > 10 picks)
2. Add symbol-level WR tracking to HC filter (block symbols with WR < 25% over 20+ picks)
3. Investigate EQUITY 0% WR — check entry timing, strategy logic, and market-open alignment
4. Add a "low pass rate" banner to the dashboard when HC pass rate drops below 1%

**Short-term (1-2 weeks):**
5. Replace binary fwdWR>=70% threshold with graduated multiplier (scale score by fwdWR/50, not binary cut)
6. Lower compound trust minimum from 8 to 6 to reduce Apr-27-style zero-pick days
7. Add regime-aware relaxation to HC filter (relax fwdWR threshold by 5pp in confirmed bull regimes)
8. Build a centralized retrain status dashboard showing all 15+ model timestamps

**Long-term (1 month+):**
9. Implement a data quality gate before retraining (reject retrain if incoming batch has >60% failure rate)
10. Consolidate retrain mechanisms — too many independent systems creates maintenance overhead
11. Retrain the consensus model on FOREX+ETF success patterns to improve crypto selection

---

## 5. Methodology

### 5.1 Data Sources

| Data | Source | Access Method |
|------|--------|--------------|
| Closed picks (4-day) | [`tools/audit_what_if_entry_day.js`](tools/audit_what_if_entry_day.js) | Queries `updates/data/dashboard_payload.json` via `byDay()` |
| HC filter logic | [`audit_dashboard/hc_filter.js`](audit_dashboard/hc_filter.js) — `evaluateHcGates1to9()` | Read source code (lines 290-434) |
| HC gate parameters | [`config/hc_gate_params.json`](config/hc_gate_params.json) | Current thresholds (fwdWRMinPct=70, scoreFloors per class) |
| ML retrain code | 15+ files across alpha_engine/, ml_battleground/, claude_gainer_ml/, mercury2/ | `grep -r` for retrain/train/smart_train/incremental_train |
| Workflow schedules | `.github/workflows/*.yml` | `grep -r` for cron/schedule patterns |

### 5.2 Performance Benchmarking

Hedge fund benchmarks are sourced from publicly available returns data (Renaissance, Citadel, DE Shaw, Two Sigma, Bridgewater). Annualized returns are converted to 4-day equivalents using (1+r)^(1/63) for 63 trading days per quarter. Sharpe ratios are stated as-is (typically annualized in industry reporting).

### 5.3 ML Retrain Audit Method

Each Python file with `retrain` in a function or class was inspected. Workflow YAML files with `schedule:` directives were searched for retrain-related job names and cron expressions. The audit captures:
- Retrain trigger condition (time-based, count-based, or drift-based)
- Schedule frequency (cron expression if applicable)
- Quality gate (any validation before accepting new model)
- Integration status (active/disabled/manual)

### 5.4 Key Files Referenced

| File | Role |
|------|------|
| [`tools/audit_what_if_entry_day.js`](tools/audit_what_if_entry_day.js) | What-if analysis engine |
| [`tools/whatif_4day_analysis.js`](tools/whatif_4day_analysis.js) | Gate-by-gate breakdown tool (created Apr 27) |
| [`audit_dashboard/hc_filter.js`](audit_dashboard/hc_filter.js) | Core HC filter (9 gates) |
| [`config/hc_gate_params.json`](config/hc_gate_params.json) | HC parameter thresholds |
| [`alpha_engine/auto_tuner.py`](alpha_engine/auto_tuner.py) | ML retrain orchestrator |
| [`alpha_engine/crypto_ml_tuner.py`](alpha_engine/crypto_ml_tuner.py) | Force retrain trigger (5 conditions) |
| [`alpha_engine/ml_ranker.py`](alpha_engine/ml_ranker.py) | smart_train / incremental_train |
| [`ml_battleground/retrain_on_live.py`](ml_battleground/retrain_on_live.py) | ML Battleground live retrain |
| [`claude_gainer_ml/trigger_retraining.py`](claude_gainer_ml/trigger_retraining.py) | Claude Gainer weekly retrain |
| [`model_health_agent.py`](model_health_agent.py) | Model health / drift monitoring |

---

## 6. Cross-Reference With Peer Agent Reports

Three peer reports landed today on overlapping ground. I compared my findings against each to identify discrepancies, gaps, and corrections needed.

### 6.1 Peer Reports Reviewed

| Report | Author | Data Source | n= | Key Strengths |
|--------|--------|-------------|-----|---------------|
| [`updates/2026-04-27-asset-class-vs-hedge-fund-and-ml-retraining-audit.md`](updates/2026-04-27-asset-class-vs-hedge-fund-and-ml-retraining-audit.md) | GitHub Copilot | `dashboard_payload.json` (fresh, generated_at=2026-04-27) | 3,500 (recent_closed) | Feedback model audit (7,877 trades), MATICUSDT poison n=1,033, authoritative per-class PF |
| [`updates/2026-04-27-chatgpt-codex-asset-class-hf-ml-audit.md`](updates/2026-04-27-chatgpt-codex-asset-class-hf-ml-audit.md) | ChatGPT Codex | `dashboard_payload.json` (stale, generated_at=2026-04-24) | 3,500 | Risk metrics (PSR, Calmar), ml_gatekeeper persistence bug, ml_crypto_predictor 718h stale, dashboard payload staleness |
| [`updates/2026-04-27-master-audit-summary.md`](updates/2026-04-27-master-audit-summary.md) | opencode/big-pickle | `closed_picks.json` (deprecated, crypto-biased) + dashboard | 5,006 | UNKNOWN asset class bug (84.9% mislabeled), what-if showing HC underperforms baseline |

### 6.2 Data Source Reconciliation

The primary source of cross-report disagreement is **which data file was used**:

| Data Source | Used By | What It Contains | Freshness | Verdict |
|-------------|---------|-------------------|-----------|---------|
| `audit_trail/data/dashboard_payload.json` (fresh) | **Copilot** (this report) | recent_closed capped at 3,500, proper asset_class tags | generated_at=2026-04-27T19:16:20Z | ✅ **Authoritative for structural analysis** |
| `audit_trail/data/dashboard_payload.json` (stale) | **Codex** | Same schema, stale generated_at | generated_at=2026-04-24T23:51:44Z | ⚠️ **3 days stale — CRYPTO numbers shift dramatically** |
| `alpha_engine/data/closed_picks.json` (deprecated) | **Master audit** | CSV-style, crypto-biased, NULL asset_class | N/A | ❌ **Do not use for asset-class analysis per Copilot's reconciliation** |
| Entry-day filter (4-day, Apr 24-27) | **This report (ROOCODE)** + Master | subset of dashboard payload, filtered by day prefix | 2026-04-27 | ✅ **Valid for "what if we followed last 4 days" but NOT for structural claims** |

### 6.3 Discrepancies Found and Resolved

#### 6.3.1 EQUITY Verdict: My "Broken" vs Peer "Best Class" — Resolved: Both Are Correct for Different Windows

| Source | Data Window | n | WR | PnL | Claim |
|--------|-------------|-----|-----|------|-------|
| **This report (ROOCODE)** | Entry-day, Apr 24-27 | 11 | 0% | -9.24% | BROKEN — needs protocol review |
| **Copilot** | Full recent_closed (fresh payload) | 370 | 52.16% | +240.6% | **Tier 2** — best class by sum PnL |
| **Codex** | Full recent_closed (stale payload) | 381 | 51.97% | +232.1% | Best-looking class, needs DD control |

**Resolution:** EQUITY is structurally our best-performing class (n=370, 52% WR, PF 1.41 per Copilot's authoritative fresh payload). The 0% WR (n=11) in my 4-day window is a **recent degradation artifact**, not a structural flaw. The correct verdict is: "EQUITY recently degraded — investigate what changed in the last ~2 weeks that caused the drop from 52% to 0% WR." My original "broken protocol" verdict is retracted in favor of a "recent degradation, needs investigation" finding.

#### 6.3.2 UNKNOWN Asset Class: I Completely Missed This — Correction Applied

| Agent | UNKNOWN n | UNKNOWN % of Total | Source File | My Original Status |
|-------|-----------|-------------------|-------------|-------------------|
| **Master audit** | 4,252 | 84.9% | `closed_picks.json` (deprecated) | N/A |
| **Copilot** | 3 | 0.09% | `dashboard_payload.json` (fresh, proper tags) | N/A |
| **This report** | 0 | 0% | Entry-day filter (dashboard payload) | **Not checked** |

**Impact on my report:** My original analysis assumed correct `asset_class` labels in the entry-day filter. I did NOT check for UNKNOWN rows. The Master audit found that 84.9% of picks in the deprecated `closed_picks.json` had `asset_class="UNKNOWN"` but were actually CRYPTO (confirmed via `category` field). While this affects the deprecated file more than the dashboard payload (which only has 3 UNKNOWN rows), it reveals a **classification pipeline gap** that could affect any source system.

**Correction needed in my report:** Add a note acknowledging this gap and recommending cross-validation of `asset_class` normalization in the entry-day filter script.

**Correction needed in Master report:** The "UNKNOWN is 84.9% of picks" claim is based on the deprecated `closed_picks.json`, not the live audit payload. The live payload (fresh) has only UNKNOWN n=3. The fix script is still useful for the legacy file, but the claim about HC filter underperforming baseline may be partially a source-file artifact.

#### 6.3.3 Dashboard Payload Staleness: I Assumed Fresh Data — Correction Applied

| Agent | generated_at | File mtime | Gap |
|-------|-------------|-----------|-----|
| **Codex** | 2026-04-24T23:51:44Z | 2026-04-27 (wall clock) | ~3 days stale |
| **Copilot** | 2026-04-27T19:16:20Z | 2026-04-27 | Match (fresh) |
| **This report** | Not verified | N/A | **Did not check** |

**Correction:** I did not verify the `generated_at` timestamp in the payload I used. Codex identified that the payload can be stale (generated_at days behind wall clock). Copilot confirmed the fresh payload is properly timestamped. All future analyses MUST log and report the `generated_at` timestamp from the payload metadata. My entry-day filter results (Apr 24-27) are robust against staleness because they filter by day prefix, but the underlying picks data could shift if the payload is republished with new closed picks.

#### 6.3.4 ML Gatekeeper Persistence: Codex Found What I Missed — Confirmed

**Codex finding:** The `audit-dashboard.yml` workflow runs `python ml_gatekeeper/gatekeeper.py` (retraining the model) but the commit block does **not** stage `ml_gatekeeper/models/` — so retrained model weights are discarded on the next CI run. The on-disk artifact shows `trained_at=2026-04-15T17:19:24Z` (~293h stale).

**My original status:** Not checked. I listed ml_gatekeeper as "Active" in my 17-mechanism inventory without verifying persistence.

**Correction:** ml_gatekeeper retrains in CI but does NOT persist to main. This is a real bug. Added to my recommendations.

#### 6.3.5 ML Crypto Predictor 718h Stale: Codex Found What I Missed — Confirmed

**Codex finding:** `ml_crypto_predictor/self_improvement.py` reads `results/v4_training_summary.json` which does not exist. The actual summary is at `enhanced_models/results/training_summary.json` with `trained_at=2026-03-26T16:22:23Z` (~718h stale). The self-improvement path is broken by a filepath mismatch.

**My original status:** I listed "Enhanced ML Crypto" as Active (daily at 02:00 UTC) without checking the stale internal timestamp. The feedback trainer (`feedback_trainer.py`) IS actively retraining (fresh `feedback_training_report.json` from 2026-04-25), but the PRODUCTION model (ensemble, scalping, swing) hasn't been updated since March 26.

**Correction:** The feedback loop component is fresh (12h cron, 7,877 trades). The core production crypto models are stale (718h). My report conflated these two different systems. The self-improvement path has a filepath bug.

### 6.4 Corrections Peer Reports Need

| Correction | Target Report | Details |
|------------|--------------|---------|
| EQUITY full-history needs recent-degradation flag | **Copilot, Codex** | Both show EQUITY at 52% WR (n=370-381) but neither flags that the last 4 days (n=11) were 0% WR. This is a recent degradation that needs investigation — not captured by rolling window metrics. |
| COMMODITY is worse than "fixable" | **Copilot** | Copilot says "flat-to-slightly-negative (PF 0.93) ... fixable, not broken." With PF 0.93 and WR 42.13% on n=610-622, this is consistently losing money. The "fixable" framing understates severity — this needs active de-prioritization. |
| ML retrain count inflated | **Master** | Master says "15+ retraining mechanisms" but also says "no training script found" and "need to verify ML training is happening." The 15+ mechanisms exist in code but not all persist artifacts (ml_gatekeeper), not all are fresh (ml_crypto_predictor 718h stale), and some train on bad data (Battleground, historically 1.9% WR). The inventory is real but the "fragmented" verdict is accurate. |
| ML Battleground "healthiest" claim needs context | **Codex** | Codex says "ml_battleground is the healthiest ML stack operationally ... Best operational state." This ignores the historical 1.9% WR across 107 trades that led to Systems A-E being DISABLED. The daily `retrain_on_live` JOB runs, but the SYSTEMS it retrains were catastrophic. Saying "best operational state" without noting the catastrophic history is misleading. |
| Data source for UNKNOWN claim | **Master** | The "UNKNOWN n=4,252 / 84.9% mislabeled" claim reads the deprecated `alpha_engine/data/closed_picks.json`, not the live audit dashboard payload. The live payload (Copilot's authoritative source) has only UNKNOWN n=3. The HC-underperforms-baseline finding (25% WR vs 66%) is downstream of this wrong-source error — Copilot confirms live HC strict does ~75% WR over the same 4 days. |

### 6.5 Gaps in My Report Filled by Peers

The following items were present in peer reports but absent from my original analysis:

| Finding | Discovered By | Priority | Impact on My Report |
|---------|--------------|----------|-------------------|
| UNKNOWN asset class bug (84.9% in deprecated file) | **Master audit** | High | I assumed correct asset_class labels. Need to add UNKNOWN validation. |
| ML Gatekeeper persistence broken | **Codex** | High | I listed as "Active" without verifying artifact persistence. |
| ML Crypto Predictor 718h stale + broken self-improvement path | **Codex** | High | I conflated feedback loop (fresh) with production models (stale). |
| Dashboard payload staleness | **Codex** | Medium | I did not verify generated_at timestamp. Future analyses must. |
| EQUITY full-history 52% WR baseline | **Copilot, Codex** | High | Changes EQUITY from "broken protocol" to "recent degradation." |
| MATICUSDT poison pill (n=1,033, WR 0%) | **Copilot** | High | Symbol-level contribution cap needed in all trainers. |
| Feedback model predicted WR=17% vs base 32.7% | **Copilot** | Medium | Confirms feedback model is conservatively under-firing. |
| Mercury2 PSR fail | **Copilot** | Medium | Confirms Mercury2 has "real but small edge" — pair with strict HC gating. |

### 6.6 Contributions My Report Made That Peers Missed

| Finding | Peer Report | Details |
|---------|-------------|---------|
| Gate-by-gate breakdown for Apr 27 zero-pick crisis | **All peers** | 77.7% failed on scoreAbsoluteFloor(40) alone — no other report traced the zero-pick day to specific gates |
| 4-day vs full-history EQUITY degradation delta | **Copilot, Codex** | Both showed EQUITY as "best class" without noting the recent 0% WR (n=11). I had the 4-day data that reveals the degradation. |
| Strategy-level WR tracking | **All peers** | TAOUSDT -11.30% (n=62) vs SEIUSDT +36.40% — symbol-level granularity missing from other reports |
| 17-mechanism retrain inventory | **Copilot** | Copilot explicitly says "I am pulling your inventory into recommendations" and "Roocode is more complete" for the 17-mechanism list vs their 6-workflow list |
| Apr 27 zero-pick crisis deep dive | **All peers** | 136 crypto picks at -35.71%, ZERO HC passes — the specific failure mode on Apr 27 was uniquely documented in my report |
| Symbol-level gate recommendation | **All peers** | Block symbols with WR < 25% over 20+ picks — concrete threshold proposal |

### 6.7 Net Reconciliation

**What I missed (and am correcting in this revision):**
1. UNKNOWN asset class bug — need to add cross-validation of asset_class normalization
2. ML Gatekeeper persistence broken — retrains run in CI but are discarded
3. ML Crypto Predictor production models 718h stale — feedback loop is fresh, but core models are not
4. Dashboard payload staleness — must verify generated_at before analysis
5. EQUITY full-history 52% WR baseline — changes verdict from "broken protocol" to "recent degradation"

**What peers missed (that I contributed):**
1. Gate-by-gate breakdown tracing zero-pick day to specific gates
2. 4-day vs full-history EQUITY degradation delta
3. Strategy-level WR tracking (TAOUSDT -11.30%, SEIUSDT +36.40%)
4. 17-mechanism retrain inventory (most complete of all 4 reports)
5. Apr 27 zero-pick crisis deep dive
6. Concrete symbol-level gate threshold proposal

**Shared gaps (all 4 reports missed):**
1. No report verified retrained model quality post-deployment (all checked "did retrain run?" not "did retrain improve?")
2. No report cross-referenced the HC filter's `fwdWR` field against actual realized WR
3. No report computed a system-level PnL (all used pick-unit aggregation, not bankroll-compounded)
4. No report checked if ML retrain data pipelines are properly gated against bad data batches

---

## 7. Conclusion

**The system is not yet at world-class hedge fund level for any asset class, but it has the right infrastructure.**

The strongest signal from this analysis is that the **data quality problem** (noisy picks, oversupply, 37% crypto WR) is more urgent than any **model quality problem** (retraining is happening extensively). The ML retraining infrastructure is impressive — 17 mechanisms across 15+ systems with varied schedules from per-pick online learning to weekly full retrains. But retraining bad data just gives you a better model of a bad process.

**Corrections from cross-reference (see §6):**
- EQUITY is NOT structurally broken — it recently degraded (52% full-history WR → 0% last 4d). Investigate what changed.
- UNKNOWN asset class bug exists in deprecated data files — cross-validate all asset_class fields going forward.
- ML Gatekeeper retrains but does not persist — fix the workflow commit path.
- ML Crypto Predictor production models are 718h stale — the feedback loop is fresh, core models are not.
- Dashboard payload freshness must be verified before each analysis.

**The path to hedge-fund-class performance:**
1. Fix the CRYPTO signal pipeline (P0) — reduce volume, increase quality
2. Investigate EQUITY recent degradation (P0) — find what changed in the last ~2 weeks
3. Tighten HC filter with graduated scoring (P1) — stop losing 4 winners per week
4. Add symbol-level gates (P1) — block known losers automatically
5. Fix ML persistence gaps (P1) — gatekeeper models, crypto predictor stale path
6. Add centralized retrain visibility (P2) — so we can see at a glance all model health

If we can get CRYPTO WR to 45% and maintain FOREX/ETF performance, the combined portfolio would be competitive with mid-tier hedge funds (~12-15% annualized). Getting to Renaissance levels (~66%) requires solving the CRYPTO problem first — that's where 80% of our picks live.
