# Expanded Enhancement Plan — 2026-05-14

**Purpose:** unify four overlapping protocols into a single actionable plan against today's repo state, and ship a daily on-track report so we stop drifting.

**Inputs reconciled:**
1. `FOOLPROOF_ACTION_PLAN.md v2.1` (Kimi/Downloads, 2026-05-02) — 12-week phased plan + corrected gate config §4.2.
2. Kimi Gate System (pasted 2026-05-14) — Levels 1-5 commit-forcing gates.
3. Inception Labs 6-Phase Protocol (pasted 2026-05-14) — Foundations → Validation → Robustness → Paper → Live → Continuous → Options.
4. Grok Foolproof Live-Trading Protocol v1 (pasted 2026-05-14) — 5 levels + per-class roadmap with first-real-money date 2026-05-23.

**Repo audit anchor:** `reports/money_maker_ready_20260514T231246Z.md` (this session) + investigator findings below.

---

## 1. Protocol convergence map

All four sources are 80% the same architecture. Treat them as one canonical "Gate Ladder":

| Stage | Foolproof phase | Kimi level | Inception phase | Grok level | What it enforces |
|---|---|---|---|---|---|
| **A. Governance** | Phase 0 (gov+CI) | (implicit) | Phase 0 | (implicit) | Reproducible artifacts, audit trail, risk policy, kill-switch infra |
| **B. Validation** | Phase 0 (R:R+ml_score gates) | Level 1 | Phase 1 | Level 1 | Out-of-time split, monkey test, PSR/DSR, walk-forward, 2-regime test |
| **C. Robustness** | Phase 1 (decay+PSR+tx-cost) | Level 2 | Phase 2 | Level 2 | Slippage/cost/latency, weekend test, OOD detection, MC ruin |
| **D. Safety architecture** | Phase 0 (gates) + Phase 1 (decay tracker) | Level 3 | Phase 4 (kill-switch) | Level 3 | Circuit breakers, quarter-Kelly, correlation cap, auto-shutdown |
| **E. Paper / Shadow** | Phase 2 (paper strategies) | Level 4 (shadow) | Phase 3 | Level 4 (shadow) | Live data zero-capital, KPI delta vs backtest |
| **F. Micro-deployment** | Phase 2 (golden portfolio) | Level 4 (skin in game) | Phase 4 | Level 4 (real $500-$2k) | Real $ ≤1% capital, 30 days |
| **G. Continuous loop** | Phase 3 (institutional) | (implicit Level 5+) | Phase 5 | (implicit) | Monthly retrain, mutation, drift watchdog |
| **H. Expansion (options/etc)** | Phase 3 + new instruments | Level 5 | Phase 6 | Level 5 | Adjacent class only after 3 are live-profitable 90d |

Action: adopt this **8-stage Gate Ladder** as the canonical ordering in `docs/PERFORMANCE_CHARTER.md` v1.1 (next charter rev). It supersedes ad-hoc P0/P1 in scattered docs.

---

## 2. Current state vs Gate Ladder (evidence-based)

Reconciled from money-maker-ready Section 10 + three investigator agents this session.

| Stage | Current state | Evidence | Gap | Priority |
|---|---|---|---|---|
| A — Governance | PARTIAL | CI runs, audit trail in `audit_dashboard/data/*.json`, but no risk-policy doc with cap+kill-switch matrix. `BLACKLISTED_STRATEGIES` is the closest. | Formal risk-policy doc; auto-pause on drift `KS_D > 0.10` not wired. | P1 |
| B — Validation | PARTIAL | `walkforward.by_class` ships CRYPTO/ETF/BOND/EQUITY (PR #940 adds COMMODITY). DSR/PSR module exists (`alpha_engine/statistical_rigor.py`). No monkey test. | Monkey test (1000 random) + bootstrap CI export + `validation_results.json`. CPCV upgrade (`project_cpcv_gap_2026_04_28.md`). | P1 |
| C — Robustness | MISSING (mostly) | `alpha_engine/transaction_costs.py` exists but **NOT called** from resolver. Tracking window 120h hard-coded for FOREX/BOND only (`outcome_resolver.py:229`). No autoencoder OOD. | Tx-cost in PnL; global 120h window; OOD module; weekend-toggle test; latency sim. | P0 |
| D — Safety | PARTIAL | `quality_gates.py` has 67 BLOCKED pairs + 5 BLACKLISTED strategies. Crypto-short regime gate is **only** true exec-time enforcement gate. PCG-5 (DAILY_IDEAS 2026-05-12) designed but unshipped. | PCG-5 shadow→enforce; circuit breaker on rolling 30d Sharpe<0.5; `disclosure≠enforcement` lift. | P1 |
| E — Paper / Shadow | PARTIAL | Paper-trade running on TV accounts (zerounderscore, theswarm, Leap, SCALPER, TESTER). swarm_picks tracking shipped 2026-05-12. No formal paper-vs-live shadow with statistical comparison report. | Shadow KPI dashboard (latency/fill/slippage/realized-vs-pred). Daily edge-report script (`scripts/daily_edge_report.py` MISSING per investigator §14). | P1 |
| F — Micro-deployment | NOT STARTED | $0 live. Grok target 2026-05-23 on COMMODITY `cot_positioning` requires (a) lag-patch (PR #941), (b) DSR re-verify, (c) Level 1-3 gates clean. | All prerequisites are LIVE blockers — see Section 4 critical path. | P0 (unblocks) |
| G — Continuous loop | PARTIAL | Hourly dashboard refresh + outcome resolver run hourly via CI. **`hf_stats` 22 days stale** (concept_drift unmonitored). No monthly retrain cadence. | Re-compute hf_stats cron; monthly retrain ritual; mutation tracking via existing `MUTATION_THREE_AXIS_PROTOCOL.md`. | P0 (re-compute drift) |
| H — Expansion | DEFERRED | INDEX_STOCK scaffold zero picks; OPTIONS not started; MEME class proposed by Foolproof §3.1 but not split out. | Block until ≥3 classes hit Level 4 (Foolproof + Grok rule). Don't start. | P3 |

---

## 3. Investigator findings reconciled (from this session)

### Foolproof Phase 0+1 status (14 deliverables)

- **SHIPPED (1):** feature_flags enabled (`config/feature_flags.json:15-17`).
- **PARTIAL (6):** signal_quality_ml exists/orphan, R:R gate (1.25 vs target 1.50 floor + 3.0 vs target 2.0 ceiling), ml_score (0.82 vs target 0.90), soft_gates enabled (`config/hf_quality_gates.json:59-73`) but no A/B router wiring, PSR/DSR module exists (no JSON export, no bootstrap), outcome_resolver has 2nd copy in `copy_trader_intel/` (intentional per-workflow scope).
- **MISSING (7):** alpha/beta benchmark badge, track_records.json per-strat-sym-dir, paper-trade comparison report, decay_dashboard.json export, tx-cost in PnL, global 120h tracking window, daily edge report script.

### Orphan goldmines (5 candidates)

- **3 ORPHAN (per `[Wire-Up Rule]` in CLAUDE.md):** `forward_testing/signal_quality_ml.py`, `battleground/alpha_vs_beta_benchmark.py`, `audit_dashboard/meta_model_chatgpt.py` — zero importers in production path.
- **WIRED:** `config/feature_flags.json` (via `alpha_engine/feature_flags.py::FeatureFlagManager` → `alpha_engine/health_check.py` + `audit_trail/daily_report.py`).
- **Score Tracker / ML Health / 4-AI Battle** widgets ARE in `audit_dashboard/template.html:1306-1866` — Foolproof §6.1 item #3 already satisfied.

### Gate-config drift vs Foolproof §4.2

Live config in `config/hf_quality_gates.json` **diverges intentionally** from Foolproof §4.2 target. Investigator found `config/hf_quality_gates.json` includes a comment line (line 15) **empirically refuting** Foolproof's PF 5.81 @ R:R 1.5-2.0 claim — live measured PF 1.258 on n=1244. Foolproof §4.2 is therefore an **outdated target**, not a regression.

| Field | Foolproof target | Live | Verdict |
|---|---|---|---|
| `min_risk_reward` | 1.50 | 1.25 | Live retained because target unprofitable in fresh data |
| `max_risk_reward` | 2.00 | 3.00 | Live retained pending re-test |
| `min_ml_score` | 0.90 | 0.82 | Live retained because 0.90 yields n=0 picks |
| `tracking_window_hours` | 120 | MISSING global; 120 FOREX/BOND only | **Foolproof correct — wire globally** |
| `transaction_cost_model` | per-class table | MISSING | **Foolproof correct — wire globally** |
| `kelly_by_rr_band` | 0.118 @ 1.5-2.0, 0 elsewhere | 0.25 global cap | Per-band is better, ship it |

### Reconciled gate-config target (v2.1 + empirical override)

```jsonc
{
  // EMPIRICAL: gates that were tested + retained
  "min_risk_reward": 1.25,    // do NOT raise to 1.5 — proven worse on n=1244
  "max_risk_reward": 3.00,    // pending re-test; Foolproof claims 2.0 worse but stale
  "min_ml_score": 0.82,       // 0.90 yields n=0 picks
  "ml_score_bands": {         // CURRENT 4-tier — keep
    "below_0.70": "block",
    "0.70_0.82": "sizing 0.50",
    "0.82_0.90": "sizing 0.85",
    "above_0.90": "sizing 1.00"
  },
  // NEW: ship these (currently missing)
  "tracking_window_hours_global": 120,           // P0 — ship in Phase 0
  "transaction_cost_model": {
    "crypto": 0.0023, "meme": 0.0053,
    "forex": 0.0003, "equity": 0.0003,
    "bond": 0.0005, "commodity": 0.0010,
    "futures": 0.0008, "etf": 0.0003
  },
  "kelly_by_rr_band": {                          // promote from global 0.25 cap
    "1.25_2.50": 0.20,
    "below_1.25": 0.0,
    "above_2.50": 0.05
  },
  "drift_auto_pause": {                          // NEW — Inception Phase 2 + 0
    "ks_d_threshold": 0.10,
    "lookback_n": 1000,
    "action": "pause_new_sizing"
  }
}
```

---

## 4. Critical path to first real money (next 14 days)

Grok's 2026-05-23 first-real-money date on COMMODITY `cot_positioning` is achievable **only if** these blockers resolve in order:

1. **DAY 1-2 (TODAY-Sat):** Apply COT publication-lag patch (PR #941). Re-backtest `cot_positioning` on CT=F with lag-corrected data. DeepSeek estimates corrected WR ~45-55% (vs claimed 89.8%); if confirmed, COMMODITY's PF 2.74 / WR 63.5% still passes T2 — proceed. If COMMODITY drops below T2, **abort 2026-05-23 target**.
2. **DAY 2-3:** Recompute `hf_stats` (22d stale). If `concept_drift.KS_D` still > 0.10, drift watchdog must **auto-pause** sizing, including on COMMODITY. Currently watchdog doesn't fire. Ship the auto-pause wire BEFORE the pilot.
3. **DAY 3-5:** Reconcile `kimi_signal_tracking` contradiction (blacklisted in code, PF 5.80 in payload). Without resolution, no PF figure in the dashboard is trustworthy.
4. **DAY 5-7:** Wire transaction-cost model from `alpha_engine/transaction_costs.py` into `outcome_resolver.py`. Re-compute all per-class PF net-of-cost. If COMMODITY net PF < 1.5, **abort 2026-05-23 target**.
5. **DAY 7-9:** Wire global 120h tracking window. Re-resolve all OPEN picks > 24h. Compare WR before/after.
6. **DAY 9-11:** Shadow paper-trade COMMODITY `cot_positioning` for 30 picks. Compute realized vs backtest gap.
7. **DAY 11-13:** Safety gates — Kimi Level 3 + Grok Level 3: hard daily 2% / weekly 5% / 3-loss cooldown / 30d Sharpe<0.5 kill switch. PCG-5 in shadow mode (DAILY_IDEAS 2026-05-12).
8. **DAY 13-14:** Go/No-Go gate. If everything green → $500 pilot on 2026-05-23 (Grok target). If anything red → push 7 days.

**Hard abort:** if `hf_stats.concept_drift.KS_D` ratio (D/critical) > 5 after recompute, no class goes live regardless of single-strategy edge.

---

## 5. Expanded Best-Possible-Action list (P0-P5, ranked)

Supersedes money-maker-ready Section 10. Each item maps to Gate Ladder stage above.

| # | Pri | Stage | Action | Effort h | Reversible | Expected impact |
|---|---|---|---|---|---|---|
| 1 | **P0** | A,B | **Re-compute `hf_stats` (22d stale)** | 1 | Y | Drift signal becomes trustworthy; auto-pause precondition |
| 2 | **P0** | D | **Wire drift auto-pause on `KS_D > 0.10`** in `passes_smart_gate` | 6 | Y | Discipline gate; required before any live $ |
| 3 | **P0** | A | **Reconcile `kimi_signal_tracking` contradiction** (blacklist in code, live PF 5.80) | 3 | Y | Unblocks trust in every PF figure |
| 4 | **P0** | C | **Wire `alpha_engine/transaction_costs.py` into `outcome_resolver.py`** | 5 | Y | Net-of-cost PF; Foolproof + Grok Level 2 |
| 5 | **P0** | C | **Global 120h tracking window** (extend from FOREX/BOND-only at `outcome_resolver.py:229`) | 2 | Y | Foolproof §11.2 + Grok Level 4 prereq |
| 6 | **P0** | F | **Apply COT publication-lag patch (PR #941) + re-backtest `cot_positioning`** | 4 | Y | Honest verdict on the strongest single-strategy edge |
| 7 | **P0** | C | **Investigate-then-mutate `multi_asset` + `mutation_lab`** (still emitting at PF<0.32) | 4 | Y | Stops live PnL drag |
| 8 | **P1** | B | **Monkey test** — 1000 random strategies vs each Tier-2 candidate. Reject if not >95th pctile | 8 | Y | Foolproof §1 monkey test; catches AI-overfit |
| 9 | **P1** | A | **`scripts/daily_edge_report.py`** — emits `edge_report.json` for the daily tracker (see Section 6) | 6 | Y | Foolproof §9 + Inception Phase 5 continuous loop |
| 10 | **P1** | B | **Wire orphan `forward_testing/signal_quality_ml.py`** — add `quality_score` to dashboard payload | 5 | Y | Foolproof §6.1 #1; +5-15pp WR claim |
| 11 | **P1** | B | **Wire orphan `battleground/alpha_vs_beta_benchmark.py`** — add `alpha_verdict` badge | 4 | Y | Foolproof §6.1 #2; institutional credibility |
| 12 | **P1** | D | **PCG-5 portfolio gates shadow log → enforce** (DAILY_IDEAS 2026-05-12) | 12 | Y | Disclosure→enforcement lift |
| 13 | **P1** | G | **Mark INACTIVE systems** (`last_signal > 30d`): `ml_crypto_pred_v12`, `mercury2_fast`, `alpha_engine_fast`, `goldmine_stocks`, `fast_stocks_competition`, ml_bg_*, `rl_agent` | 2 | Y | Signal/noise on dashboard |
| 14 | **P1** | B | **COMMODITY + FOREX + FUTURES walk-forward output** (currently missing from `walkforward.by_class`) | 3 | Y | Unblocks T2 promotion gates |
| 15 | **P1** | A | **`FRED_API_KEY` secret + wire macro feed** (DXY, VIX, yield curve) | 6 | Y | Regime-conditional sizing; Grok BOND prereq |
| 16 | **P2** | B | **CPCV (purged combinatorial CV)** over walk-forward for n<30 cohorts | 12 | Y | Drops bad small-n promotions; `project_cpcv_gap_2026_04_28.md` |
| 17 | **P2** | C | **OOD detector** (autoencoder on feature vectors, 3σ reconstruction error → safety gate) | 16 | Y | Inception Phase 2 |
| 18 | **P2** | E | **Shadow KPI dashboard** — latency/fill/slippage/realized-vs-pred per paper account | 10 | Y | Inception Phase 3 |
| 19 | **P2** | C | **Slippage + latency simulator** (100-500ms entry/exit delay) for re-backtest | 8 | Y | Kimi Level 2 weekend test |
| 20 | **P2** | F | **ETF scale to n≥200 + push PF over 1.5** | 8 | Y | Unblocks ETF T2 |
| 21 | **P3** | A | **Riskfolio-Lib HRP/CVaR risk-budget** at portfolio gate | 10 | Y | Risk-cap discipline |
| 22 | **P3** | G | **Mutation cadence** — automated hyperparameter sweep on Tier-3 candidates per `MUTATION_THREE_AXIS_PROTOCOL.md` | 16 | Y | Inception Phase 5; replace dead strategies |
| 23 | **P4** | A | **Polymarket / Kalshi prediction-market consensus broadening** | 8 | Y | Catalyst-driven directional bias |
| 24 | **P5** | H | **Options sleeve scaffolding** (delta-neutral calendar spreads only) | 24 | Y | Inception Phase 6 — DO NOT START until 3 classes pass Stage F |

---

## 6. Daily supreme-plan tracker — spec

User explicitly asked for a daily report tracking the amended supreme improvement plan. Design below.

### 6.1 Trigger + outputs

- **Trigger:** new GitHub Actions workflow `daily-supreme-tracker.yml`, cron `0 6 * * *` (06:00 UTC = 02:00 ET).
- **Writes:** `reports/daily_supreme_tracker/<YYYY-MM-DD>.md` + `reports/daily_supreme_tracker/latest.json` + appends one row to `reports/daily_supreme_tracker/_index.csv`.
- **Renders:** new tab on `/audit` named **"Daily Tracker"** that reads `latest.json` and the trailing 14 daily rows from the CSV.

### 6.2 Inputs (read, never invent — same rule as money-maker-ready)

| Section | Source | What it tells us |
|---|---|---|
| Per-class verdict | `audit_dashboard/data/dashboard_data.json::performance.asset_class_health` | T1/T2/T3/Below today |
| Walk-forward | `dashboard_data.json::walkforward.by_class` | OOS WR, sharpe, decay |
| Drift | `dashboard_data.json::hf_stats.concept_drift` | KS_D vs critical, auto-pause status |
| Plan progress | this file's Section 5 P0-P5 list — manually maintained `STATUS:` field | did we ship anything yesterday? |
| Stage Ladder | Section 2 of this file | which stage is each class in |
| Critical path | Section 4 day-counter | days remaining to next milestone |
| Failing CI | `gh run list --branch main` | infrastructure red flags |
| INACTIVE systems | `systems[].last_signal_at > 30d` | dead-system count |

### 6.3 Output format (markdown)

```
# Daily Supreme Tracker — YYYY-MM-DD

## On-track verdict
GREEN / YELLOW / RED  +  one-line reason

## Per-class status (vs target tier)
| Class | n | WR | PF | tier | trend(7d) | gate-ladder-stage | days-since-shipped-item |

## P0 burn-down (Section 5 items 1-7)
| # | item | status | owner | ETA | risk |

## Critical-path day counter
"Day X of 14 to first real money (2026-05-23 target on COMMODITY cot_positioning)"
| Blocker | Status | Days left |

## Drift state
KS_D: <value>  ratio: <value>×critical  auto-pause: <ON/OFF>  hf_stats_age: <hours>

## CI / infra
N failed workflows on main without subsequent success: <list>

## Yesterday's progress
- 1 line per merged PR touching the plan
- 1 line per ship from P0-P5 in Section 5

## Auto-flags
- list of contradictions found by cross-check (e.g. blacklisted-but-emitting, sparkline-vs-total mismatch)
```

### 6.4 GREEN / YELLOW / RED rule

- **GREEN:** all P0 items in Section 5 either DONE or in-progress with ETA ≤ 3 days, drift auto-pause ON or KS_D < 0.10, 0 failing CI workflows, 0 unresolved cross-contradictions.
- **YELLOW:** 1-2 P0 slipping, OR drift_alert TRUE but auto-pause armed, OR 1-2 failing CI workflows, OR 1 cross-contradiction.
- **RED:** any P0 item stalled >7 days, OR drift_alert TRUE + auto-pause OFF, OR ≥3 failing CI workflows, OR ≥2 cross-contradictions, OR `kimi_signal_tracking` (or similar BLACKLISTED) still emitting picks.

### 6.5 Implementation effort

- Script: `scripts/daily_supreme_tracker.py` ~250 LOC, ~6h to write + 2h to add the `/audit` Daily Tracker tab.
- Wire as GHA cron + on-push trigger on main.
- Auto-commit the markdown back to repo (per existing `[skip ci]` payload pattern).

### 6.6 Acceptance criteria

1. Output runs in <60s, succeeds on green CI.
2. Cross-contradictions auto-flag (e.g., catches today's kimi_signal_tracking blacklist-vs-live).
3. `latest.json` schema stable so the dashboard tab can read without daily ad-hoc patches.
4. After 14 daily runs, GREEN/YELLOW/RED trend chart on dashboard renders.
5. Trigger condition for "we shipped real money on COMMODITY" can be answered yes/no from a single `latest.json` field.

---

## 7. What this plan does NOT do (kept honest)

- Does **not** accept Grok's PF 5.81 / WR 1.5-2.0-band claim — empirically refuted in our own config (line 15 of `hf_quality_gates.json`).
- Does **not** force Foolproof's R:R floor 1.5 — proven worse on n=1244.
- Does **not** ship `kimi_signal_tracking` as a Tier-2 winner — blacklist is correct, the PF number is suspect until reconciled.
- Does **not** start options expansion or new asset classes — Stage H is locked until ≥3 classes pass Stage F.
- Does **not** trust the 89.8% WR on `cot_positioning_CT_locked` until PR #941 lag patch lands.

---

## 8. Reproducer commands

```bash
# Generate this report's anchor (money-maker-ready):
# already at reports/money_maker_ready_20260514T231246Z.md

# Verify gate-config drift:
python -c "import json; print(json.load(open('config/hf_quality_gates.json'))['hard_gates'])"

# Verify orphan goldmines (zero importers):
for m in signal_quality_ml alpha_vs_beta_benchmark meta_model_chatgpt; do
  echo "=== $m ==="
  grep -rln "from .*\.$m\|import .*\.$m" alpha_engine/ audit_trail/ audit_dashboard/ tools/ scripts/ live-monitor/ 2>/dev/null | head -5
done

# Verify drift state:
python -c "import json; print(json.load(open('audit_dashboard/data/dashboard_data.json'))['hf_stats']['concept_drift'])"

# Verify INACTIVE systems:
python -c "
import json
from datetime import datetime, timezone
d = json.load(open('audit_dashboard/data/dashboard_data.json'))
now = datetime.now(timezone.utc)
for s in d.get('systems', []):
    ts = s.get('last_signal_at')
    if ts:
        try:
            dt = datetime.fromisoformat(ts.replace('Z','+00:00'))
            if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
            days = (now - dt).days
            if days > 30: print(f'{s[\"name\"]} | last={ts} | {days}d')
        except: pass
"
```

---

## 8b. Fresh hf_stats + swarm-validated drift threshold (this session)

Ran `python tools/hf_stats.py` on fresh `audit_dashboard/data/dashboard_data.json` (origin/main@62faff3291e). Wrote `tools/data/hf_stats_summary.json`. Key delta vs 22-day-stale snapshot:

| Metric | Stale (2026-04-22) | Fresh (2026-05-14) | Δ |
|---|---|---|---|
| KS_D | 0.3126 | **0.0498** | -84% |
| ks_critical_05 | 0.0473 | 0.0460 | -3% |
| D / critical | **6.6×** | **1.08×** | dramatic drop |
| drift_alert | TRUE | TRUE (barely) | held |
| var_ratio | 1.07 | **1.43** | +33% |
| Sharpe (all) | None | **1.71** | new |
| Sortino | None | 3.15 | new |
| MDD | None | 119.85% | new |
| WR (all) | n/a | 45.0% | new |
| PF (all) | n/a | 1.36 | new |

**Per-class fresh (recent_closed n=3500):**
- BOND: n=12, SR=-2.72, PF 0.66, WR 50%, MDD 2.9%
- COMMODITY: n=74, SR=5.81, PF 2.26, WR 54%, MDD 49.2%
- CRYPTO: n=2891, SR=1.26, PF 1.25, WR 44%, MDD 112%
- EQUITY: n=271, SR=3.67, PF 1.82, WR 52%, MDD 62%
- ETF: n=104, SR=2.70, PF 1.49, WR 59%, MDD 45%
- FOREX: n=148, SR=1.35, PF 1.31, **WR 30%**, MDD 8%

**FOREX cross-contradiction:** `asset_class_health` says FOREX WR 52.2% / PF 0.81 / n=341. Fresh recent_closed slice says WR 30% / PF 1.31 / n=148. Different windows (asset_class_health is cumulative-since-inception; this is recent_closed slice). **Document the window discrepancy on the dashboard tile to prevent confusion.**

### Swarm second-opinion (3/3 consensus, $0.06)

`swarm_runs/second-opinion-20260514T233053Z/` — deepseek + xai + kilo agree:

- **Q1 — auto-pause all classes at marginal D?** NO — too aggressive at 1.08× critical. The crypto-short regime gate is the right pattern; a system-wide all-class pause is overkill.
- **Q2 — threshold?** Use `D > 2 × ks_critical_05` (effect-size based). NOT plain p-value significance (large-n inflates false positives), NOT the flat 0.10 LdP rule of thumb (doesn't scale with sample size or critical value).
- **Q3 — per-class or system-wide?** Per-asset-class via `hf_stats.by_asset_class[CLASS].concept_drift` (if absent, compute on the fly). System-wide pause only when ≥2 classes simultaneously breach OR a single class breaches `D > 3 × critical_05`.

### Investigator-located wire site

- New gate fn: `audit_trail/quality_gates.py:876` — `_passes_drift_auto_pause_gate(pick) -> Optional[str]`
- Caller patch: `audit_trail/quality_gates.py:4636` inside `passes_active_gate`, after the existing `_crypto_short_gate_block_reason` call.
- Payload reader precedent: `audit_trail/dashboard_generator.py:14499` already reads `hf_stats.concept_drift` — reuse loader pattern.
- Regime-cache pattern to follow: `audit_trail/quality_gates.py:792-845` (mtime + fallback default).
- A second caller exists in `passes_smart_gate` at `audit_trail/quality_gates.py:5594` — patch both for parity with crypto-short gate.

### Final drift-gate config (swarm + investigator validated)

```python
DRIFT_GATE_CONFIG = {
    "enabled": True,
    "per_class_threshold_mult": 2.0,       # D > 2 * ks_critical_05
    "system_wide_breach_mult": 3.0,        # D > 3 * critical OR 2+ classes breach
    "min_n_for_gate": 200,                 # below this, skip gate (insufficient data)
    "hf_stats_max_age_hours": 36,          # if stale > 36h, FAIL OPEN (no pause)
}
```

Effort to ship: **~5h** (function + 2 caller patches + unit test + payload reader plumbing).

---

## 9. Sign-off

- This plan is **additive** to existing supreme_plan_review_2026-05-13.md, not replacement. The supreme plan's Wave 1 items remain valid.
- Charter v1.1 update should fold Section 1 (Gate Ladder) in as the canonical stage model.
- Daily tracker (Section 6) is the standing instrument to detect drift away from this plan, including drift caused by adding more plans on top of plans.
