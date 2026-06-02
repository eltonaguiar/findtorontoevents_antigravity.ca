# EAGLE2 — Quant Review & Enhancement Plan

**Author:** Composer (Cursor Agent)  
**Date:** 2026-06-02  
**Surfaces:** [findtorontoevents.ca/audit](https://findtorontoevents.ca/audit), [ai_leaderboard.html](https://findtorontoevents.ca/audit/ai_leaderboard.html), [ai-tournament.html](https://findtorontoevents.ca/audit/ai-tournament.html), [pick_funnel.html](https://findtorontoevents.ca/audit/pick_funnel.html)  
**`pf.html` (clarification):** [findtorontoevents.ca/audit/pf.html](https://findtorontoevents.ca/audit/pf.html) — the **AI tournament paper-portfolio drill-down page** (one portfolio per `?key=`, e.g. `?key=deepseek_v4__aggressive`). Linked from tournament rows in `ai-tournament.html`; reads `audit/data/pf_portfolios.json`. **Not** the main Smart Picks production book on `/audit`.  
**Live baseline:** `audit_dashboard/data/money_ready_verdict.json` (2026-06-02T06:21Z) — **0/9 money-ready**  
**Phase 0 PR:** [#441](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/441) (stop-bleed gates, in review)  
**NFA — research memo, not a sizing recommendation.**

---

## 1. Executive summary

**Bottom line:** This is **not** mainly a “wait longer” problem. The main `/audit` production book is weak because **research edge ≠ deployed edge**. Live, policy-clean performance is still bad in the classes that matter most (CRYPTO, EQUITY, FOREX), while the places that *do* show edge are mostly **paper/tournament-only**, **overly concentrated**, **insufficiently sampled**, or **contaminated by resolver/label issues**.

The **AI Leaderboard** (`/audit/ai_leaderboard.html`) has a **different failure mode**: it is a thin attribution layer over swarm picks, not a capital-ready per-class book. As of 2026-06-01 it ranks **one engine** (`claude-opus-4-7`, n=83 resolved) with **503 research candidates** still un-attributed — so it cannot yet answer “which AI is profitable per asset class” at production grade.

**Portfolio status:** The example book is **not empty**. Live `pf_portfolios.json` shows **81 portfolios, 66 with open positions**; `deepseek_v4__aggressive` has **11 open names**. Empty `pf.html?key=…` UI → corrupted/invisible Unicode in `?key=` or stale cache (fixed in `pf.html` 2026-06-02).

---

## 2. Quant verdict (four questions)

| Question | Answer |
|----------|--------|
| **Do we just need more time?** | Only for **ETF** and small-sample sleeves (forward n→100). **Not** for the main production book — CRYPTO n=374, EQUITY n=52, FOREX n=32 are already large enough to reject. |
| **Do our strategies suck?** | **Deployed production mix: yes** for capital. Lab/tournament has isolated edges, but they are gated off or live in a separate universe. |
| **What are we doing wrong?** | Promoting from wrong evidence, too many weak emitters, concentration masquerading as edge, inconsistent validation standards, tournament↔production conflation. |
| **Mutation / inversion?** | **Mutation yes** — per-sleeve, axis-specific (`docs/MUTATION_THREE_AXIS_PROTOCOL.md`). **Inversion rarely** — only after explicit OOS proof of negative edge. |
| **Data/resolver issues?** | **Yes** for FOREX/FUTURES/disputed cohorts — but **not the whole story**. CRYPTO/EQUITY fail on honest PF even after policy-clean filters. |

---

## 3. Root cause — why `/audit` has no profitable per-class book

### 3.1 Canonical numbers (policy-clean, 2026-06-02)

Source: `money_ready_verdict.json` via `strategy_admissibility.json`.

| Class | n | WR | PF | Verdict | Top source share | Root cause (one line) |
|-------|---|-----|-----|---------|------------------|------------------------|
| **CRYPTO** | 374 | 35.6% | 0.89 | NOT_READY | 54.5% UNKNOWN | Bulk scanner loss-skew; lab VWAP/Bollinger PASS but opt-in only |
| **EQUITY** | 52 | 26.9% | 0.33 | NOT_READY | 40.4% regime_terminal | Weak emitter + concentration; no verified sleeve merged |
| **FOREX** | 32 | 28.1% | 0.48 | INSUFFICIENT_DATA | 34.4% multi_asset_scanner | Resolver EXPIRED mislabels + thin carry lab |
| **ETF** | 3 | 66.7% | 1.46 | INSUFFICIENT_DATA | 66.7% | **Best lab candidate** (dual momentum Tier-2) — need forward n≥100 |
| **COMMODITY** | 4 | 50% | 1.68 | INSUFFICIENT_DATA | — | Sample too small; COT strategies dead post-leakage |
| **FUTURES** | 13 | — | 0.52 | INSUFFICIENT_DATA | — | TIME_EXIT zombies + concentration |
| **BOND** | 8 | 0% | 0 | INSUFFICIENT_DATA | — | No meaningful live sample |

**Money-ready classes: 0/9.**

### 3.2 Structural root causes (production `/audit`)

1. **Universe split violation** — Smart Picks / production scanner emits from ~88 strategies; only ~5% have M-108 walk-forward artifacts. Lab winners (`verified_strategies/`, tournament) never merge unless `verified_promotion_gate.*_merge_allowed()` is true.

2. **Wrong emitters dominate volume** — `regime_terminal`, `incubator_gainer`, unverified mercury2 paths contribute disproportionate CRYPTO/EQUITY closes with PF<1. CRYPTO top_source_share 54.5% (UNKNOWN bucket = provenance gap).

3. **Concentration artifacts** — Single-source or single-symbol dominance inflates funnel/tournament surface stats. Pick_funnel “78.9% CRYPTO Smart-Picks” cell is **DISPUTED** (duplicate signal-ts, mislabels, 91.7% concentration in one source).

4. **Resolver/label pollution** — FOREX shows high WR / terrible PF pattern (EXPIRED→positive PnL). FUTURES `futures_connors_rsi2` TIME_EXIT at pnl≈0 distorts decisive-rate.

5. **Validation engine split** — `real_data_backtest.py` path lacks purged WF + DSR/PBO for 25/31 academic strategies. Promotion from raw PF alone is forbidden by M-108 but still happens informally via scanner breadth.

6. **Sizing on wrong metric layer** — Headline WR on dashboard ≠ policy-clean PF after flicker-dedup, slippage, concentration caps, and SPA/DSR gates.

### 3.3 Where edge actually lives (trust hierarchy)

| Rank | Surface | Edge? | Capital? |
|------|---------|-------|----------|
| 1 | `/audit` money-ready (policy-clean) | **No** | **No** |
| 2 | `/audit/ai-tournament.html` + `pf.html` | **Best paper edge** (deepseek_v4 n≈208, pf_ci_lo≈2.5) | Paper only |
| 3 | `/audit/pick_funnel.html` | Discovery cells (CRYPTO RR bands) | No — holdout/concentration/dispute flags |
| 4 | Verified lab + forward pilots | **Best future candidates** (ETF dual momentum Tier-2) | After forward n≥100 |

**Rule:** Size capital **only** from policy-clean money-ready → verified forward book → gradual scale. Never from tournament rank or funnel green cell alone.

---

## 4. Root cause — why `/audit/ai_leaderboard.html` shows no per-class profit

The leaderboard is **not broken** — it is **under-powered and misread**.

### 4.1 What the page actually measures

Built by `tools/ai_attribution/build_ai_leaderboard.py`. It attributes swarm picks to `models_consulted[].underlying_model`, joins realized outcomes, ranks with **Wilson shrinkage** (min n=20 to rank).

Live index (`ai_leaderboard_index.json`, 2026-06-01):

| Metric | Value | Implication |
|--------|-------|-------------|
| Engines ranked | **1** (`claude-opus-4-7`) | Almost no multi-engine comparison yet |
| Resolved picks | 29 (index totals) / 83 (engine overall) | Thin sample vs production book (374+ CRYPTO alone) |
| Research candidates | **503** | Lab ideas **not wired** to attribution pipeline |
| Per-class n (claude-opus) | CRYPTO 43, EQUITY 20, ETF 16, FOREX 2 | ETF/FOREX **building** (below rank floor) |

**Per-class snapshot (claude-opus-4-7 only):**

| Class | n | WR | PF | Rank eligible? |
|-------|---|-----|-----|----------------|
| CRYPTO | 43 | 37.2% | 1.33 | Yes — but CI wide [24.4, 52.1] |
| EQUITY | 20 | 45.0% | 2.15 | Yes — n barely at floor |
| ETF | 16 | 6.2% | 0.10 | **No** — honest fail |
| FOREX | 2 | 0% | 0.0 | **No** — no sample |

### 4.2 Why leaderboard ≠ production profitability

1. **Different universe** — Leaderboard tracks **AI swarm attribution**, not Smart Picks production scanner. Tournament models (deepseek_v4, gpt4o, grok3) appear on `pf.html`, not necessarily in leaderboard attribution.

2. **Sparse attribution** — 503 research candidates vs 1 ranked engine means the page cannot yet answer “best AI per class” — it answers “best AI **we have attributed closes for** per class.”

3. **MA-trend research warning (2026-05-29)** — Page banner: high PF on MA-trend strategies is **shape not edge** (Monte Carlo null p=0.28–0.67). PF column reflects trend-following payoff skew, not admissible alpha.

4. **No M-108 gate on leaderboard rows** — Rank score uses WR shrinkage, not DSR/PBO/forward book. A lucky 20-trade sleeve can show PF>2 with Wilson lower bound still <50% WR.

5. **Not connected to money_ready** — Leaderboard has no `policy_clean` flag, no concentration cap, no resolver dispute filter.

### 4.3 Leaderboard-specific fix

Treat leaderboard as **Universe A (discovery)** — hypothesis generation only. Before any class shows “PROFITABLE” badge:

- Require n≥50 per class per engine after policy-clean filter
- Require concentration HHI <0.20 on that engine×class slice
- Require forward virtual book n≥30 for promotion ticket
- Wire tournament engines into attribution (`build_ai_leaderboard.py` must ingest `pf_portfolios` daily closes)

---

## 5. How I would handle this (operating model)

### Three universes, one admissibility pipe

```
DISCOVERY (A)          LAB + FORWARD (B)           PRODUCTION (C)
pick_funnel            rigorous_backtest_harness    production_scanner
ai_leaderboard         walkforward_suite            money_ready_verdict
ai-tournament          pilot_virtual_book           verified_promotion_gate
        │                      │                           │
        └──── M-107 pre-register ──── M-108 stages 0–5 ──────┘
                                      shadow 30d → size
```

**Parallel, never auto-merge:** Universe T (tournament paper / pf.html daily engine).

### Immediate actions (Phase 0 — in PR #441)

| Action | Status |
|--------|--------|
| 0% intake: regime_terminal, incubator_gainer, mercury2_fast | PR #441 |
| BLOCKED_SOURCE_SYSTEMS / asset pairs | PR #441 |
| 60% single-source cap per class (Smart Picks) | PR #441 |
| Concentration probation exclude mode | PR #441 |
| Dashboard policy-clean honesty strip | PR #441 |
| pf.html Unicode key sanitization | Done on main |

### Capital policy (effective now)

- **CRYPTO / EQUITY / FOREX:** zero default sizing until `money_ready_verdict` → READY
- **ETF dual momentum:** shadow pilot only until forward n≥100
- **Tournament (deepseek_v4 etc.):** paper portfolios only — extract rules → M-108 lab sleeve before any merge

---

## 6. Standardized validation pipeline — worked example

Every sleeve must pass **M-108** (`docs/BACKTEST_ADMISSIBILITY_STANDARD.md`). Below is a **concrete end-to-end example** for `etf_dual_momentum` using repo tooling.

### Stage 0 — Pre-register (M-107)

```bash
# Before any OHLCV run — register hypothesis
python3 -c "
import json
from pathlib import Path
reg = Path('reports/hypothesis_registry.json')
data = json.loads(reg.read_text()) if reg.exists() else {'hypotheses': []}
data['hypotheses'].append({
  'id': 'H-ETF-DM-001',
  'strategy': 'etf_dual_momentum',
  'asset_class': 'ETF',
  'registered_at': '2026-06-02',
  'kill_on_leakage': True
})
reg.write_text(json.dumps(data, indent=2))
"
```

### Stage 1–4 — Purged walk-forward + costs + DSR/PBO

```bash
# Rigorous harness (purged k-fold, embargo, costs, DSR, PBO, block bootstrap)
python3 alpha_engine/rigorous_backtest_harness.py \
  --strategy etf_dual_momentum \
  --class ETF
```

Core gate logic (from `rigorous_backtest_harness.py`):

```python
# DEFAULT_COSTS applied per trade
DEFAULT_COSTS = {
    'CRYPTO': 0.001, 'EQUITY': 0.0005, 'FOREX': 0.0003,
    'ETF': 0.0005, 'COMMODITY': 0.0005, 'FUTURES': 0.0003,
}

# Walk-forward: 8 splits, 5% purge, 2% embargo
WF_PARAMS = {'n_splits': 8, 'purge_pct': 0.05, 'embargo_pct': 0.02}

def run_backtest(pnl_series, asset_class, strategy_name='unknown', ...):
    # Returns: pf_net, wr, dsr, pbo, bootstrap_ci, tier (T1/T2/FAIL)
    ...
```

**Acceptance (lab):** OOS PF ≥ 1.2, OOS n ≥ 10; full promotion n ≥ 30; DSR ≥ 0.90 (T2), PBO ≤ 0.10.

Fallback lab path:

```bash
python3 verified_strategies/walkforward_suite.py --sleeve etf_dual_momentum
# Output: verified_strategies/WALKFORWARD_REPORT.json
```

### Stage 5 — Forward virtual book (mandatory for scanner merge)

```bash
python3 verified_strategies/paper_pilot/pilot_virtual_book.py --sleeve etf_dual_momentum
python3 tools/pilot_forward_dashboard.py --write
python3 tools/etf_forward_stats.py --write
```

Promotion gate (from `verified_promotion_gate.py`):

```python
def etf_scanner_merge_allowed() -> bool:
    report = etf_forward_report()
    if report.get("recommend_scanner_enable") is True:
        return True
    pilot = report.get("paper_pilot_forward") or {}
    return pilot.get("promotion_ready") is True  # forward n>=100, PF>=1.5, etc.
```

**Forward gate:** n_closed ≥ 100, forward PF ≥ 1.5, forward WR ≥ 50%, forward PF ≥ 0.85 × lab OOS PF.

### Stage 6 — Shadow → sized capital

```bash
# Shadow only (default OFF)
ETF_VERIFIED_DUAL_MOMENTUM_ENABLED=shadow python3 alpha_engine/production_scanner.py

# After 30d shadow + money_ready flip:
python3 alpha_engine/money_ready_verdict.py --json
```

### Unified report (dashboard consumer)

```bash
python3 tools/strategy_admissibility_report.py --write --fetch-live-portfolios
# → audit_dashboard/data/strategy_admissibility.json
```

**Required promotion artifact on disk:**

```json
{
  "strategy_id": "etf_dual_momentum",
  "asset_class": "ETF",
  "stages_passed": [0, 1, 2, 3, 4, 5],
  "oos_pf_net": 1.21,
  "oos_n": 32,
  "forward_n": 100,
  "forward_pf": 1.55,
  "dsr": 0.92,
  "pbo": 0.08,
  "promotion_ready": true
}
```

---

## 7. Real-time monitoring — concentration & resolver disputes

### 7.1 Concentration metrics

| Metric | Definition | Source | Alert (warn) | Alert (critical) | Action |
|--------|------------|--------|--------------|------------------|--------|
| **top_source_share** | max(source) / n_closed per class | `money_ready_verdict.json` | >40% | >60% | Trim via `eagle2_class_source_cap.py`; exclude in Smart Picks |
| **top_symbol_share** | max(symbol) / n_closed per class | same | >25% | >40% | Symbol concentration block in `smart_picks_engine.py` |
| **HHI (source)** | Σ(share²) over sources | compute daily from closed CSV | >0.20 | >0.25 | Concentration probation exclude mode |
| **HHI (symbol)** | Σ(share²) over symbols | same | >0.15 | >0.22 | Cap new picks on dominant symbol |
| **cross_portfolio overlap** | symbol in ≥N pf books | `smart_picks_engine.py` log | ≥3 books | ≥5 books | Flag in dashboard; no size-up |
| **Smart Picks cell concentration** | single cell >X% of class row | `pick_funnel.html` / nav matrix | >50% | >70% | DISPUTED banner; no promotion |

**Implementation hook (already in repo):**

```python
# alpha_engine/eagle2_class_source_cap.py
MAX_SINGLE_SOURCE_SHARE = 0.60  # Phase 0

def enforce_class_single_source_cap(picks, asset_class):
    # Drop lowest-score picks from dominant source until share <= 60%
    ...
```

```python
# config/risk_policy.json (Phase 0)
"enable_concentration_probation_v2": true,
"concentration_controls": { "mode": "exclude", "max_single_source_share": 0.60 }
```

### 7.2 Resolver dispute metrics

| Metric | Definition | Source | Alert (warn) | Alert (critical) | Action |
|--------|------------|--------|--------------|------------------|--------|
| **EXPIRED_pos_pnl_rate** | EXPIRED rows with pnl>0 / all EXPIRED | 14d closed panel SQL | >5% | >10% | Fix `universal_pick_resolver.py` |
| **TIME_EXIT_decisive_share** | TIME_EXIT @ \|pnl\|<ε / class n | resolver audit | >5% | >10% | Block zombie strategies in quality_gates |
| **duplicate_signal_ts_groups** | count(distinct ts groups with dupes) | pick_funnel audit | >500/90d | trending up | Insert-time dedup |
| **disputed_cohort_rate** | picks flagged DISPUTED / total | `pick_summary_stats_2w.json` | >2% | >5% | Exclude from policy-clean rollup |
| **entry_price_zero_rate** | entry=0 / inserts | pipeline_health | >0.1% | >1% | Block emitter pre-insert |
| **WR↑ PF↓ divergence** | WR>55% AND PF<0.5 same class 14d | daily class panel | any class | 2+ classes | Resolver audit sprint |

**Daily job (proposed — wire to existing CI):**

```bash
python3 tools/strategy_admissibility_report.py --write
python3 tools/db_freshness_check.py
# New: tools/resolver_dispute_panel.py --days 14 --json-out reports/resolver_dispute_panel.json
```

Slack alert when any **critical** threshold breached for **2 consecutive days**.

---

## 8. Mutation testing framework — failed lab sleeves

### 8.1 Philosophy

Per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`: **mutate before kill**. Most “losers” are misapplied on symbol, direction, or timeframe — not fundamentally broken alpha.

**Do not** class-wide invert. **Do** axis-specific gates + re-validate through M-108.

### 8.2 Tool chain (already in repo)

| Step | Tool | Output |
|------|------|--------|
| 1. Slice closed picks | `tools/mutation_analysis.py --json` | 3-axis report |
| 2. Symbol allowlist | `tools/matrix_rules_from_csv.py` | `alpha_engine/data/matrix_symbol_gates.json` |
| 3. DNA mutations | `alpha_engine/strategy_mutator.py` | `alpha_engine/data/mutation_results.json` |
| 4. Re-backtest winner | `rigorous_backtest_harness.py` | promotion artifact |
| 5. Forward shadow | `pilot_virtual_book.py` | forward stats JSON |

### 8.3 Example workflow — `regime_terminal` (EQUITY loser)

```bash
# Step 1: Autopsy
python3 tools/mutation_analysis.py --json \
  --min-trades 5 --dir-spread 20 --sym-spread 30 \
  -o reports/mutation_regime_terminal.txt

# Step 2: If symbol axis shows edge (e.g. INTC-only WR>55%):
python3 tools/matrix_rules_from_csv.py \
  -i mutation_artifacts/compat_matrix.csv \
  -o alpha_engine/data/matrix_symbol_gates.json

# Step 3: DNA mutation candidates (inverse / tighter TP-SL / top-5 symbols)
python3 alpha_engine/strategy_mutator.py

# Step 4: Promote mutation only if:
#   mutation WR > original WR + 10pp AND mutation WR > 45%
#   AND harness OOS PF >= 1.2 on mutated sleeve
python3 alpha_engine/rigorous_backtest_harness.py --strategy regime_terminal_mut_b --class EQUITY
```

**Promotion thresholds** (from `strategy_mutator.py`):

```python
MIN_TRADES = 10
WR_IMPROVE_THRESHOLD = 0.10   # +10pp vs original
WR_PROMOTE_MIN = 0.45         # 45% floor
# Plus M-108: OOS PF >= 1.2, forward n >= 100 for scanner merge
```

### 8.4 Mutation candidates by class (Phase 3C)

| Sleeve | Axis | Mutation | Kill if |
|--------|------|----------|---------|
| Faber TAA | universe | QQQ vs SPY; +10bps costs | forward PF <1.0 @ n=50 |
| crypto VWAP/Bollinger | filter | RR band 1.0–1.5 LONG only | forward PF <1.3 |
| FOREX carry | pair set | multi-pair + FRED cache | OOS n <30 @ D+90 |
| equity 12-1 mom | risk | MDD cap + sector neutral | WF still FAIL |
| regime_terminal | symbol | allowlist winners only | harness PF <1.0 |

**Inversion:** Only when mutation_analysis shows **consistent negative edge on all axes** AND inverse OOS PF ≥ 1.2 (e.g. explicit short-only flip with proof). Never invert Connors crypto (loss-skew, not wrong sign).

### 8.5 CI integration

- Weekly: `.github/workflows/mutation-analysis-report.yml` (already exists)
- On WR decay >15pp week-over-week: `tools/matrix_diff.py` → block promotion
- New mutations must register as separate hypothesis IDs in M-107 before backtest

---

## 9. Enhancement plan — 12-week timeline

### Phase 0 — Stop the bleed (Week 1) ✅ PR #441

Depromote toxic sources, concentration cap, honesty strip, pf.html fix.

### Phase 1 — Data integrity (Weeks 1–3)

| # | Action | Acceptance |
|---|--------|------------|
| 1.1 | EXPIRED→WON audit | FOREX EXPIRED_pos_pnl <10% on 14d |
| 1.2 | TIME_EXIT zombie purge | FUTURES TIME_EXIT share <5% |
| 1.3 | Insert-time signal-ts dedup | CRYPTO dup_groups −50% on 90d |
| 1.4 | Wire leaderboard ↔ tournament attribution | ≥5 engines ranked per class |
| 1.5 | Policy-clean canonical everywhere | No sizing docs cite raw `by_asset_class` |

### Phase 2 — Unified validation (Weeks 2–6)

| # | Action | Acceptance |
|---|--------|------------|
| 2.1 | `academic_backtest_bridge.py` | 31/31 academic → harness |
| 2.2 | Purged WF on main backtester | Methodology audit Flaw #1 closed |
| 2.3 | Block bootstrap replaces i.i.d. MC | No MC-only promotion |
| 2.4 | Strategy census + kill list | ≤15 active emitters/class with artifact |
| 2.5 | CI admissibility gate on scanner PRs | New emitter blocked without WF path |

### Phase 3 — Promote proven sleeves (Weeks 3–12)

| Candidate | Action | Gate |
|-----------|--------|------|
| **ETF dual momentum** | Daily forward pilot | n→100, PF≥1.5 → shadow → merge |
| **Crypto VWAP/Bollinger** | Hyro WF pilot | sleeve-only sizing, not aggregate CRYPTO |
| **Faber TAA / carry** | Mutation track | forward PF≥1.0 @ n=50 |
| **deepseek_v4 tournament** | Extract rules → M-108 lab | never raw pick copy to Smart Picks |

### Phase 4 — Tournament bridge (Weeks 6–12)

- Label tournament picks `universe=tournament_paper` in DB
- pf.html roster health widget (open count, last run)
- pick_funnel PROVEN cell → auto hypothesis ticket

---

## 10. Success definition (D+90)

| Metric | Today | Target |
|--------|-------|--------|
| Money-ready classes | 0/9 | **≥1** (ETF first) |
| CRYPTO policy-clean PF | 0.89 | ≥1.0 (stop bleed) → ≥1.2 |
| ETF forward n_closed | ~0 | ≥100 |
| Active emitters with M-108 artifact | ~5% | 100% |
| Leaderboard engines ranked per class | 1 | ≥5 |
| Resolver dispute rate | elevated | <1% |
| Source HHI (aggregate book) | >0.25 | <0.20 |
| Tournament→production conflation | ongoing | **0** |

---

## 11. Per-class playbook (summary)

| Class | Primary action | Mutation? | Invert? | First capital path |
|-------|----------------|-----------|---------|-------------------|
| CRYPTO | VWAP/Bollinger sleeve; depromote bulk | RR band filter | No | Sleeve-only after forward proof |
| EQUITY | Kill regime_terminal; Faber shadow | Faber QQQ + costs | No | None until W8+ |
| ETF | **Promote dual momentum** | Sector basket | No | **W10–12** |
| FOREX | Fix resolver first; carry pilot | Multi-pair | Per-pair only | W12+ |
| COMMODITY | Vol-scaled cross-mom | Drop ZC=F | No | W12+ |
| FUTURES | TIME_EXIT fix | N/A | No | W3 cleanup |
| BOND | HYG/LQD momentum pilot | Credit Faber | No | W12+ |

---

## 12. References & reproducers

```bash
# Live verdict
python3 alpha_engine/money_ready_verdict.py --json

# Unified admissibility + edge map
python3 tools/strategy_admissibility_report.py --write --fetch-live-portfolios

# Portfolio roster
curl -sA 'Mozilla/5.0' 'https://findtorontoevents.ca/audit/data/pf_portfolios.json' | python3 -m json.tool | head

# Leaderboard rebuild
python3 tools/ai_attribution/build_ai_leaderboard.py

# Phase 0 tests
python3 -m pytest tests/test_eagle2_phase0_gates.py -q

# Prior memos
# reports/EAGLE_JUNE2_COMPOSER.md
# reports/quant_strategy_root_cause_review_2026-06-02.md
# docs/BACKTEST_ADMISSIBILITY_STANDARD.md
```

---

**Prepared by:** Composer (Cursor Agent) — EAGLE2 Initiative  
**Date:** 2026-06-02
