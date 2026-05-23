---
name: money-maker-ready
description: Use when user wants to audit findtorontoevents.ca/audit (+ /audit/hyrotrader, ejaguiar1_stocks, ejaguiar1_backtests) for production-grade real-money readiness. Per-asset-class statistical-edge hunt with cross-source correlation, external-data integration suggestions, dashboard UI/filter audit, and ranked Best-Possible-Action recommendations. Triggers — `/money-maker-ready`, "is /audit ready for real money?", "find edge per asset class", "money maker audit", "edge hunt", "what's our best statistical edge?", "should we go live with X asset class?". Aliases — mmready, money-maker, edge-hunt, real-money-audit, edge-by-class.
---

# Money-Maker-Ready Audit Skill

**Goal:** turn the 1-shot `/audit` real-money-readiness investigation into a repeatable, evolving evaluation. Project owner wants `/audit` ready for real-money use ("hedge-fund level picks per asset class, people spend their REAL money").

## Hard rule (enforced throughout)

**Every performance claim must be labeled `(asset_class | n | timeframe)`.** Reject any claim missing any of these. Cite source path + line number from actual data files (`audit_dashboard/data/dashboard_data.json::path.to.field`).

**`n`-citation discipline (added v1.1, 2026-05-15).** The verdict-grade count is
`asset_class_health.<CLASS>.n` (= `resolved_n` = `wins + losses` after the
`_is_valid_resolved_pick` filter). It is a deterministic pure-function output —
proven reproducible (`tools/_verify_n_reproducible.py`, 3 identical SHA256 runs;
see `reports/asset_class_verification_2026-05-15.md`). Do NOT cite raw `closed`
(`by_asset_class.<CLASS>.closed`) as `n` — it is 1.5-3× larger (it includes
corrupted / blocked-history / pip-confused / `pnl==0` rows). Reports that quote
raw `closed` as the verdict `n` are the source of every "n drift" complaint.
Always say which one you mean.

**Plan-staleness rule.** `FOOLPROOF_ACTION_PLAN.md` and the 90-day plans carry
snapshot numbers that go stale within days and have shipped self-contradictions
(BOND PF 0.66 vs 1.72). NEVER quote a plan's PF/WR/n as current — re-read
`asset_class_health` live and treat the plan only as intent/direction.

## Inputs (read, never invent)

| Source | What | Status to verify |
|---|---|---|
| `audit_dashboard/data/dashboard_data.json` | Canonical post-resolver-v2 dashboard data, 18.8MB, hourly auto-refreshed | `::generated_at` not stale (>2h = stale) |
| `docs/PERFORMANCE_CHARTER.md` | Tier 1/2/3 thresholds, KPI definitions | v1.0 2026-04-28 = canonical |
| `TESTING_PROTOCOL.MD` | Layered test stack L0-L9, rehab pipeline | re-check date |
| `docs/MUTATION_THREE_AXIS_PROTOCOL.md` | Symbol/direction/timeframe split before kill | required reading before BLOCKED edits |
| `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` | Investigation ladder | required reading before BLOCKED edits |
| `audit_trail/quality_gates.py::BLOCKED_ASSET_STRATEGY_PAIRS` | Current per-class strategy blocks | live |
| `alpha_engine/config.py::BLACKLISTED_STRATEGIES` | Per-strategy blocks at pick-intake | live |
| `audit_dashboard/template.html` | Real dashboard HTML — UI/filter buttons | DO NOT edit `audit_dashboard/index.html` (auto-generated) |
| `audit_dashboard/template.html` (hyrotrader section) | hyrotrader-specific tabs/filters | locate `hyrotrader` mentions |
| `mysql.50webs.com::ejaguiar1_stocks` | Live primary DB (322 tables) | creds in **Windows env** `DB_NAME_STOCKS` / `DB_PASS_STOCKS` (NOT `live-monitor/api/.env`) |
| `mysql.50webs.com::ejaguiar1_backtests` | Backtest history DB (6 tables) | Windows env `DB_NAME_BACKTESTS` / `DB_PASS_BACKTESTS` |
| `docs/DB_SCHEMA_stocks_backtests_2026-05-15.md` | Up-to-date DB schema doc | regenerate via `tools/_db_schema_doc.py` (reads env creds) |
| `FOOLPROOF_ACTION_PLAN.md` | Master action plan (amended 2026-05-15) | intent only — verify numbers live |
| `reports/asset_class_action_items_2026-05-15.md` | Per-class action items (graphify cross-ref) | latest verified action list |
| `reports/asset_class_verification_2026-05-15.md` | Verification deep-dive + method/evidence | the proof layer |
| `reports/SUPREME_PLAN_90days.md` + `reports/asset_class_90day_plan_*_2026-05-15.md` | 90-day plans per class | intent only — verify numbers live |
| `audit_dashboard/data/dashboard_data.json::walkforward.by_class` | Walk-forward OOS per class | freshness check |
| `audit_dashboard/data/dashboard_data.json::fwd_vs_bt_divergence.rows` | Backtest-overfit detector | live |
| `audit_dashboard/data/dashboard_data.json::hf_stats` | Sharpe/MDD/Calmar per class | check freshness |

## Output structure (deterministic)

Produce ONE markdown file at `reports/money_maker_ready_<UTC>.md` with these sections in this order:

```
# Money-Maker-Ready Audit — <UTC>

## 0. Freshness preflight
[fail-fast if dashboard_data.json::generated_at older than 2h]

## 1. Per-class baseline (verdict-grade)
[asset_class_health table; tier vs charter]

## 2. Walk-forward verification (per class, OOS)
[walkforward.by_class table; consistency, decay, oos_sharpe]

## 3. Cumulative-since-inception system winners (Tier-2-MDD-verified)
[systems where PF>=1.5, WR>=50, MDD<=20, n>=100; per (asset_class | n | timeframe)]

## 4. System draggers (negative PnL contribution)
[bottom 10 systems by pnl_pct; flag PF<0.5 OR -100 PnL% as kill candidates]

## 5. Backtest-overfit detector flags
[fwd_vs_bt_divergence.rows; group by system family; recommend surgical quarantine]

## 6. Drift state
[hf_stats::concept_drift; auto-pause-recommend if D > 0.10]

## 7. UI/Filter audit
[Smart Picks tab vs filter behavior; High-Conviction button audit]

## 8. External data integrations to consider for more edge
[ranked list with expected-impact estimate]

## 9. Top statistical edges per asset class
[per (CRYPTO/EQUITY/COMMODITY/ETF/FOREX/BOND): symbol+strategy+source combos that meet stat-sig + Tier-2 thresholds]

## 10. Best-Possible-Action ranked recommendations
[priority P0-P5 with expected impact, effort, risk]

## 11. Verifiable claims log
[reproducible commands + git SHAs]
```

## Step-by-step workflow

### Step 1 — Freshness preflight (FAIL-FAST)

```bash
python -c "
import json, time
from pathlib import Path
from datetime import datetime, timezone
p = Path('audit_dashboard/data/dashboard_data.json')
d = json.loads(p.read_text(encoding='utf-8'))
gen = datetime.fromisoformat(d['generated_at'].replace('Z','+00:00').rstrip('Z'))
age_h = (datetime.now(timezone.utc) - gen).total_seconds()/3600
if age_h > 2:
    print(f'STALE: {age_h:.1f}h old; aborting per Money-Maker-Ready protocol')
    exit(1)
print(f'OK: dashboard_data.json {age_h:.1f}h old')
"
```

If stale: surface to user, ask whether to proceed anyway or wait for next refresh cycle (hourly via `chore(audit-dashboard): refresh payload [skip ci]` cron).

### Step 2 — Per-class baseline

Read `dashboard_data.json::performance.asset_class_health`. Per class:

| Class | n | WR | PF | MDD (if available) | sample_tier | Tier vs charter |
|---|---|---|---|---|---|---|

Tier mapping (per `docs/PERFORMANCE_CHARTER.md`):
- Tier 1: PF≥2.0, WR≥55%, MDD≤10%, n≥200
- Tier 2: PF≥1.5, WR≥50%, MDD≤20%, n≥100
- Tier 3: PF≥1.2, WR≥45%, MDD≤25%, n≥100
- Below: <1.2 PF OR <45% WR OR >25% MDD OR n<100

### Step 3 — Walk-forward verification

Read `dashboard_data.json::walkforward.by_class` AND `walkforward.generated_at`. Per-class table: folds, oos_wr, oos_wr_std, oos_sharpe, decay, consistency, worst-best WR. Flag classes missing from `by_class`.

Verify: positive decay = strategy improves OOS (good); negative decay = backtest overfit. Consistency <80% = unstable.

### Step 4 — Cumulative system winners

Filter `dashboard_data.json::systems` for systems where:
- `profit_factor >= 1.5`
- `win_rate >= 50`
- `max_drawdown <= 20`
- `closed_picks >= 100`

Output table: name | asset_classes (multi) | closed_picks | win_rate | profit_factor | max_drawdown | last_signal | live_status (active/monitoring/dead).

Mark DEAD any system where `last_signal_at` > 30 days ago — flag INACTIVE.

### Step 5 — System draggers

Filter for systems where `total_pnl_pct < -50` OR `profit_factor < 0.5`. Sort by most negative PnL. Recommend per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` — investigation gate before BLOCK.

### Step 6 — Backtest-overfit detector

Read `dashboard_data.json::fwd_vs_bt_divergence.rows`. Group by `system`. For each family with ≥3 flagged strategies, recommend SURGICAL quarantine (per-strategy add to `BLOCKED_ASSET_STRATEGY_PAIRS`), NOT system-wide block. Template: `reports/baby_strats_overfit_quarantine_proposal_2026_05_10.md`.

### Step 7 — Drift state

Read `dashboard_data.json::hf_stats.concept_drift`. If `drift_alert: True`:
- Surface KS_D + critical
- Compute `D / critical` ratio (>5 = severe)
- Recommend auto-pause sizing if D > 0.10

Standard response: pause new sizing, investigate distribution shift, re-train or re-validate before resume.

### Step 8 — UI / Filter audit

Read `audit_dashboard/template.html`. Locate:
- "Smart Picks" tab → grep `id="tab-smart"` or similar
- "High-Conviction" button → grep `data-filter="high_conviction"` or similar
- Filter chips: "All", "Today", "Active", per-asset-class chips

Per filter, verify:
1. JS filter logic matches user-facing label
2. Filter excludes based on actual `dashboard_data.json` field, not hardcoded
3. "High-Conviction" defined consistently with `confidence_recalibrator` if present (confidence may be inverted across classes)

Output: list of UI/filter mismatches between label and code behavior.

### Step 9 — External data integrations to consider

| Library / data source | Asset class fit | Expected impact | Integration effort | Current gap |
|---|---|---|---|---|
| **VectorBT** (polakowo) | Crypto + HFT | 50-100x faster vectorized backtests | Low-Med | Slow backtest iteration |
| **Riskfolio-Lib** (dcajasn) | All (esp. Hyro/Prop) | CVaR/HRP risk budgeting | Low | Risk-cap audit gap |
| **pandas-ta** (twopirllc) | All | 130+ indicators | Very Low | Manual indicator code |
| **Freqtrade** (freqtrade) | Crypto live | Hyperopt + live execution | Med | Live exec layer |
| **FinRL** (AI4Finance) | Crypto adaptive | RL regime switching | High | Regime adaptation |
| **QuantStats** (ranaroussi) | Reporting | Pro perf reports | Very Low | Audit report polish |
| **PyPortfolioOpt** (robertmartin8) | Stocks | Black-Litterman, HRP | Low | Multi-asset portfolio opt |
| **CoinGecko Pro API** | Crypto | Mirror exchange data + on-chain | Low | Already in failover chain |
| **Polymarket API** | Cross-asset sentiment | Real-money prediction-market signal | Med | Already wired (`prediction_market_consensus.py`) |
| **Kalshi API** | Cross-asset (US-regulated) | Pairwise consensus with Polymarket | Med | Sidecar: `pm_consensus_overlay.py` |
| **FRED data (St. Louis Fed)** | Macro | Yield curves, VIX, DXY | Low | `fred_data_fetcher.py` exists, need `FRED_API_KEY` |
| **Glassnode / Coinglass** | On-chain | Whale flows, funding rates | Med | Some integration; widen |

### Step 10 — Top statistical edges per asset class

For each class with sufficient data (n≥100), output TOP-N (N=5) `(symbol, strategy, source_system)` triples where:
- `n >= 8` (TESTING_PROTOCOL Layer 2.5 stat-sig gate)
- `WR >= 52%` (above coin-flip threshold)
- `PF >= 1.5` (Tier 2 PF floor)

If DB credentials available, run live SQL. Otherwise pull from `dashboard_data.json::cross_strategy_permutations` or `cross_system_permutations`.

Per-class template:
```
### CRYPTO top 5 edges
| Rank | (symbol | strategy | source_system) | n | WR % | PF | Avg PnL % | timeframe |
```

### Step 11 — Best-Possible-Action ranked recommendations

Final output P0-P5 ranked list:

```
| Priority | Action | Asset class impact | Effort (hr) | Risk | Reversibility | Expected lift |
```

Starter kit (current verified state, 2026-05-15 — per
`reports/asset_class_action_items_2026-05-15.md` + verification):
- P0: Re-derive COMMODITY PF/WR on post-PR-#994 (COT-dedup) picks — headline
  PF 2.37 / n=326 carries pre-dedup over-emission; do NOT make a Tier-1 claim
  on it first.
- P0: Add a class-wide `PENNY_STOCK` + `MEMECOIN` gate — `PENNY_STOCK` is
  entirely absent from `quality_gates.py` (zero gating today).
- P0: Fix the `quan_engine` cap desync — `per_source_volume_cap.py`=5% vs
  `quarantine_manifest.json` + tests=12%; pin one.
- P1: Cap `luxalgo_filters` CRYPTO volume (uncapped, PF 1.12, ~17.5% vol) +
  give `enforce_cap()` a `production_scanner.py` caller (one caller today).
- P1: Debug the ETF sector emitter — it is default-ON but emits 0 picks
  (silent failure), not "opt-in".
- P1: Drift auto-pause logic (KS D > 0.10); mark dead systems INACTIVE.
- P2: Wire the FOREX directional gate (LONG bias is the drag — `BLOCKED_ASSET_STRATEGY_TRIPLES` has no FOREX rows).
- P2: Lower `BOND_ELITE_FLOOR` (default 40) to unblock the BOND emitter (n=11).
- P2: Fix FUTURES `=F`→COMMODITY misclassification + `conf_floor` 0.50→0.40.
- P3: Wire `kill_gate.evaluate_kill()` into `quality_gates.passes_active_gate`
  (it is wired into the kill switches but not the active gate).
- P3: Standardize the cited verdict metric on `resolved_n`; UI/filter fixes.
- P4: Set `FRED_API_KEY` (unblocks macro data for BOND + EQUITY + COMMODITY).
- P5: Pilot paper-trade real-time variance test.

## Output destination + persistence

```bash
TS=$(date -u +%Y%m%dT%H%M%SZ)
OUT="reports/money_maker_ready_${TS}.md"
# write report
git add "$OUT"
git commit -m "audit(money-maker-ready): per-class edge audit ${TS}"
# DON'T auto-push — let user decide
```

## Hard constraints (refuse if violated)

- NEVER run `audit_trail/dashboard_generator.py` locally (overwrites live HTML per CLAUDE.md)
- NEVER edit `audit_dashboard/index.html` (auto-generated)
- NEVER auto-add to `BLOCKED_ASSET_STRATEGY_PAIRS` or `BLACKLISTED_STRATEGIES` without explicit user approval
- NEVER claim performance numbers without `(asset_class | n | timeframe)` triple
- NEVER trust per-engine swarm-fabricated file contents — verify with grep/ls before acting
- NEVER hardcode credentials in committed code (use `live-monitor/api/.env` or env vars)

## Cross-skill integration

Consumes outputs from:
- `check-gh-actions` (verify CI pipeline health before trusting auto-refresh)
- `homepage-perf-audit` (sister skill for consumer-facing homepage)

Produces inputs for:
- `swarm-second-opinion` (multi-engine review of audit findings)
- `swarm-pr-review` (when audit recommends a code change)

## Companion subagents

When deep investigation needed:
- Spawn `cavecrew-investigator` to locate specific code paths (e.g. "where is `passes_smart_gate` called?")
- Spawn `pr-reviewer` if recommending PR-level change
- Spawn 4-5 engine swarm via `swarm-run.py` for second opinion on Best-Possible-Action ranking

## Failure modes the skill must handle

| Mode | Detection | Response |
|---|---|---|
| Dashboard data >2h stale | freshness preflight | abort, surface, ask wait/proceed |
| MySQL unreachable | timeout on DB query | fall back to `dashboard_data.json` aggregates + flag |
| Walkforward absent for class | empty `by_class[CLASS]` | mark "UNVERIFIED — walk-forward missing" not "WORKING" |
| Drift alert TRUE | `concept_drift.drift_alert` | emit P1 recommendation, do NOT proceed to "ready for real money" verdict |
| Hermes peer in shared `.git` | files appear modified mid-run | snapshot working tree before/after, never auto-commit peer changes |

## Versioning

Skill version **1.1** (2026-05-15). v1.0 shipped 2026-05-11 from
`docs/proposals/money-maker-ready_skill_proposal_2026-05-10.md`.
v1.1 changes: `n`-citation discipline + plan-staleness rule; DB creds moved to
Windows env (`DB_PASS_STOCKS` / `DB_PASS_BACKTESTS`); inputs now include the
amended `FOOLPROOF_ACTION_PLAN.md`, the 2026-05-15 action-items + verification
reports, and the 90-day plans; starter recommendations re-based on the verified
action stack; kill_gate / volume-cap / graphify rows added. After each run,
capture lessons learned + refine.

## Acceptance criteria (v1.0)

1. Skill runs end-to-end in <5 min on cold cache
2. Output report has all 11 sections populated
3. ≥1 fabrication-flag triggered (proves verifier works)
4. Best-Possible-Action P0 list survives 4-engine swarm review
5. UI/filter audit catches at least 1 mismatch (proves it's not a checklist)

## Reference data sources

| Source | Path | Status |
|---|---|---|
| Verdict-grade per-class | `audit_dashboard/data/dashboard_data.json::performance.asset_class_health` | live |
| Walk-forward by class | `audit_dashboard/data/dashboard_data.json::walkforward.by_class` | live |
| Backtest-overfit | `audit_dashboard/data/dashboard_data.json::fwd_vs_bt_divergence.rows` | live |
| HF metrics (drift) | `audit_dashboard/data/dashboard_data.json::hf_stats` | check freshness |
| System list | `audit_dashboard/data/dashboard_data.json::systems` | live |
| Tier thresholds | `docs/PERFORMANCE_CHARTER.md` v1.0 | canonical 2026-04-28 |
| BLOCKED pairs | `audit_trail/quality_gates.py BLOCKED_ASSET_STRATEGY_PAIRS` (~:1933) | live — pairs only, no class-wide gate |
| BLOCKED triples | `audit_trail/quality_gates.py BLOCKED_ASSET_STRATEGY_TRIPLES` (~:2045) | live — direction axis; no FOREX rows yet |
| Blacklist | `alpha_engine/config.py BLACKLISTED_STRATEGIES` | live |
| Kill gate (M-055) | `audit_trail/kill_gate.py` | wired into `commodity_kill_switch.py` / `fx_kill_switch.py` / `policy_backtest.py`; NOT in `passes_active_gate` |
| Volume caps | `alpha_engine/per_source_volume_cap.py` + `quarantine_manifest.json` | desynced (5% vs 12%) — verify both |
| Live dashboard HTML | `audit_dashboard/template.html` | live |
| Codebase knowledge graph | `graphify-out/graph.json` via `/graphify-ask` | query for "which module feeds X" |
