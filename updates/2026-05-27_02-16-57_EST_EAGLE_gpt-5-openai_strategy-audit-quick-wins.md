# EAGLE Strategy Audit Quick Wins

Generated: 2026-05-27 02:16:57 EST
Model/provider: GPT-5 / OpenAI Codex
Scope: audit dashboard, incidents/enhancements, updates roadmap, DAILY_IDEAS.MD, root 90-day asset-class plans, safety gates, symbol universe, and strategy health artifacts.

## Sources Reviewed

- Live/local dashboard surfaces:
  - https://findtorontoevents.ca/audit/
  - https://findtorontoevents.ca/audit/incidents.html
  - https://findtorontoevents.ca/updates/index.html
- Repo artifacts:
  - `DAILY_IDEAS.MD`
  - `audit_dashboard/data/incidents_enhancements_feed.json`
  - `audit_dashboard/data/pick_funnel_90d.json`
  - `audit_dashboard/data/pick_funnel_rejected_universe.json`
  - `audit_dashboard/data/top_edges_per_class.json`
  - `audit_dashboard/data/db_health.json`
  - `audit_dashboard/data/money_ready_verdict.json`
  - `audit_dashboard/data/edge_stability/*.json`
  - `alpha_engine/data/missed_gainers_log.json`
  - `alpha_engine/data/filter_danger_report.json`
  - `alpha_engine/data/smart_picks_improvement_report.json`
  - `reports/gate_sweep.csv`
- Code paths inspected:
  - `audit_trail/quality_gates.py`
  - `alpha_engine/smart_picks_engine.py`
  - `alpha_engine/score_booster.py`
  - `alpha_engine/confidence_calibrator.py`
  - `alpha_engine/smart_picks_performance.py`

## Deduped Plan Files

The user-provided Windows list contains many worktree copies. In this checkout, the `.claude/worktrees/...` paths are not present, so the canonical, shortest available files are:

- `reports/90day_gap_analysis_2026-05-15.md`
- `reports/asset_class_90day_plan_BOND_2026-05-15.md`
- `reports/asset_class_90day_plan_COMMODITY_2026-05-15.md`
- `reports/asset_class_90day_plan_CRYPTO_2026-05-15.md`
- `reports/asset_class_90day_plan_EQUITY_2026-05-15.md`
- `reports/asset_class_90day_plan_ETF_2026-05-15.md`
- `reports/asset_class_90day_plan_FOREX_2026-05-15.md`
- `reports/asset_class_90day_plan_FUTURES_2026-05-15.md`
- `reports/asset_class_90day_plan_PENNY_MEME_2026-05-15.md`

The committed `dedup-md-files` skill now validates after removing unsupported frontmatter. It wraps `tools/dedup_md_files.py`, hashes file contents, and chooses the shortest path per duplicate group.

## Executive Verdict

Do not grant broad safety-gate exemptions yet. The core outcome ledger is currently too dirty for real-money policy changes: `db_health.json` shows validator freeze/open bloat, WON rows with negative average PnL, large PnL mismatches, and ghost-row contamination. Any "gate filtered a winner" claim must be replayed through a counterfactual rejected-pick ledger before it changes production gates.

The best immediate work is not a new alpha layer. It is instrumentation plus a small set of asset-class-specific pilots that are already suggested by the plans and incidents feed.

## Quick Wins Executed Now

1. Fixed the committed dedupe skill validator issue:
   - File: `.claude/skills/dedup-md-files/SKILL.md`
   - Issue: unsupported `aliases` key in YAML frontmatter.
   - Verification: `quick_validate.py` passes after the edit.

2. Produced this EAGLE quick-win audit and a separate remaining-items EAGLE backlog.

No strategy execution logic was changed in this pass. That is deliberate: the evidence says the data-integrity gates must be repaired before changing trade gates.

## Safety-Gate Findings

### Missed Big Winners

There is evidence of missed winners, but not yet proof that safety gates consistently filtered them out.

- `alpha_engine/data/missed_gainers_log.json` shows missed crypto movers:
  - RAINUSDT +43.78% and DRIFTUSDT +37.23% were not in the universe.
  - REQUSDT +35.82%, OSMOUSDT +29.87%, and PHAUSDT +17.73% were in universe but no strategy fired.
- `pick_funnel_rejected_universe.json` shows QQQ, AMD, TSLA, and AAPL rejected around `SCORE<60 (got 57)`.

The first group is a universe/trigger gap. The second group is a gray-zone gate candidate. Neither is enough to prove exemption eligibility without resolved counterfactual outcomes.

### Exemptions

No blanket exemption should be added. The right design is a scoped exemption trial:

- Scope: `asset_class + strategy + symbol + direction + regime + gate_name`.
- Allowed bypass: small score/trust-floor relaxation only, never liquidity, max-loss, stale-price, concentration, or data-integrity gates.
- Evidence threshold: at least 30-50 clean rejected counterfactuals, PF >= 1.5, WR >= 52%, Wilson lower bound >= 48%, no data-quality red flags, and no single-symbol overconcentration.
- Auto-expiry: expire after 1-2 losses, regime flip, 7-day PF collapse, or data-health red state.

The existing streak cache in `quality_gates.py` is useful as a feature, but a hot streak alone should not bypass gates. It can add a small score bonus or move a pick into a probation bucket after the rejected-ledger evidence exists.

### "Two-Price" Oscillation Trades

No current evidence supports calling any oscillation trade a sure thing. Several mean-reversion strategies are explicitly blocked or unhealthy, including forex RSI2 mean reversion, futures mean reversion, bond mean reversion, and memecoin mean reversion.

The practical quick win is an oscillation detector for pairs and liquid ETF/bond relationships only:

- Candidate pairs: TLT/IEF, TIP/IEF, HYG/LQD, XLE/XLF sector spreads, selected FX majors.
- Required tests: cointegration, ADF, Hurst exponent, half-life, spread z-score, borrow/fee/slippage model, and out-of-sample walk-forward.
- Output: research-only until n >= 100 and PF/WR survive costs.

## Best Strategy Per Asset Class

| Asset class | Best near-term strategy | Production posture |
|---|---|---|
| Stocks/equity | VIX-regime-filtered 12-1 momentum on liquid large-cap core plus PEAD/factor sleeves. Remove penny/meme/speculative names from the equity production universe. | Best candidate for probation once ledger health is green. |
| Crypto | Liquid-core BTC/ETH/SOL/top-L1 universe, source whitelist, ADV gate, funding/on-chain confirmation, BTC UTC-hour filter, and confidence calibration. | Paper/probation only until missed-gainer and confidence-inversion audits are resolved. |
| Forex | Pruned majors-only short-bias/DXY-confluence pilot with real carry and real CFTC FX COT. | Research-only or hard-disabled until PF > 1.3 with clean n >= 50. |
| Bonds | TLT/IEF, TIP/IEF, HYG/LQD relative-value pilots with FRED yield curve, MOVE, duration, and credit-spread regimes. | Research-only; current sample is too small and concentrated. |
| Commodities | COT-deduped diversified carry/momentum across multiple contracts, with one pick per COT release and symbol concentration caps. | Block sizing until COT truth table and regenerated outcomes are clean. |
| ETFs | SPDR sector rotation/Faber tactical allocation with VIX < 25 regime gate and dual-momentum confirmation. | Strong quick-win pilot after emitter scheduling and VIX gate wiring. |
| Futures | Merge zombie FUTURES tile into a unified CTA/futures bucket or add real financial futures emitters for MES/MNQ/MGC/MYM. | No production sizing; current futures tile has nearly no valid sample. |
| Penny/cheap/IPO | Keep penny/meme quarantined. Cheap-stock/IPO research only with ADV, float, lock-up, SEC filing, borrow, spread, and halt filters. | 0% allocation until a separate speculative ledger proves edge. |

## PR Queue

### PR-1: Rejected-Pick Counterfactual Ledger

Create a table and resolver for picks rejected by gates, with the same exit logic used for opened picks. This directly answers whether gates are blocking winners.

Acceptance:
- Every gate rejection records symbol, asset class, strategy, score, confidence, gate name, fail reason, entry reference, TP/SL, and timestamp.
- Resolver computes MFE, MAE, counterfactual PnL, outcome, and data-quality flags.
- Dashboard shows winners blocked, losers blocked, and net avoided loss by gate and asset class.

### PR-2: Outcome Ledger Health Freeze

Add a production policy flag that prevents new exemptions and money-ready promotion whenever DB health is red.

Acceptance:
- Blocks exemption promotion when validator is frozen, PnL mismatch rate is high, WON/PnL contradiction exists, or ghost rows exceed threshold.
- Incidents page displays "Promotion frozen by data health" at top.

### PR-3: Equity/ETF Gray-Zone Replay

Replay score 55-60 rejected large-cap/ETF candidates, especially QQQ, AMD, TSLA, AAPL, and SPDR sectors.

Acceptance:
- Creates per-symbol and per-strategy results for score bands 50-55, 55-60, 60-65, 65-70.
- If score 55-60 large-cap candidates show clean PF >= 1.5, add a probation gate, not a full exemption.

### PR-4: ETF VIX Sector Rotation Pilot

Wire/schedule `etf_sector_emitter.py` and make VIX < 25 the default ETF sector-rotation regime filter.

Acceptance:
- SPDR sector universe only.
- XLE concentration capped.
- Dashboard shows VIX-filtered vs unfiltered results.

### PR-5: Crypto Missed-Gainer Universe and Trigger Audit

Convert missed-gainer logs into a daily universe/trigger report.

Acceptance:
- Separates "not in universe", "strategy did not fire", "gate rejected", and "rejected by source trust".
- Adds a liquid-core watchlist expansion path, not meme/unfiltered expansion.

### PR-6: Commodity COT Truth Table

Regenerate commodity outcomes with one pick per `(symbol, COT_report_date, direction)` and publish raw vs deduped vs pilot metrics.

Acceptance:
- COT publication lag enforced.
- CT=F contribution capped or flagged above 30%.
- No commodity production promotion until post-dedup PF/WR survives.

### PR-7: Penny/Meme Quarantine Enforcement

Formalize penny, meme, and low-quality speculative buckets as research-only.

Acceptance:
- Parent EQUITY and CRYPTO production universes exclude penny/meme/speculative names by default.
- Dashboard explains whether blocked picks were speculative drag.

### PR-8: Forex Hard-Disable and Pruned Pilot

Disable broad forex emission and run only a pruned majors/DXY/carry/COT research pilot.

Acceptance:
- Only EURUSD, GBPUSD, USDJPY, USDCHF or a similarly documented major set.
- SHORT-bias and DXY confluence explicitly tracked.
- Promotion requires clean 60-day PF > 1.3 and n >= 50.

### PR-9: Bond Scanner and Relative-Value Pilots

Wire `bond_scanner.py` only for research-output pilots.

Acceptance:
- TLT/IEF, TIP/IEF, HYG/LQD pilots run with FRED/MOVE/credit-spread regimes.
- Production sizing remains blocked for 90 days.

### PR-10: Roadmap DB Table for Incidents/Enhancements

Unify incidents, enhancements, experiments, and roadmap items into queryable tables.

Acceptance:
- Incidents page can group by asset class, severity, component, status, PR link, evidence, and success metric.
- Enhancement dashboard can show backlog aging and next action.

## Suggested Roadmap Tables

```sql
CREATE TABLE audit_roadmap_items (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  item_type ENUM('INCIDENT','ENHANCEMENT','ROADMAP','EXPERIMENT') NOT NULL,
  asset_class VARCHAR(32) NOT NULL,
  severity ENUM('P0','P1','P2','P3') DEFAULT NULL,
  impact ENUM('CRITICAL','HIGH','MEDIUM','LOW') DEFAULT 'MEDIUM',
  effort ENUM('XS','S','M','L','XL') DEFAULT 'M',
  status ENUM('OPEN','IN_PROGRESS','BLOCKED','VALIDATING','DONE','REJECTED') NOT NULL DEFAULT 'OPEN',
  title VARCHAR(255) NOT NULL,
  description TEXT NOT NULL,
  component VARCHAR(128) DEFAULT NULL,
  recommended_fix TEXT DEFAULT NULL,
  success_metric TEXT DEFAULT NULL,
  source_path VARCHAR(255) DEFAULT NULL,
  source_url VARCHAR(512) DEFAULT NULL,
  evidence_json JSON DEFAULT NULL,
  tags JSON DEFAULT NULL,
  priority_score DECIMAL(6,2) DEFAULT NULL,
  confidence DECIMAL(5,4) DEFAULT NULL,
  owner VARCHAR(128) DEFAULT NULL,
  model_provider VARCHAR(128) DEFAULT NULL,
  linked_pr_url VARCHAR(512) DEFAULT NULL,
  linked_issue_url VARCHAR(512) DEFAULT NULL,
  supersedes_id BIGINT DEFAULT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  due_at TIMESTAMP NULL DEFAULT NULL,
  resolved_at TIMESTAMP NULL DEFAULT NULL,
  INDEX idx_roadmap_status_class (status, asset_class),
  INDEX idx_roadmap_priority (severity, priority_score),
  INDEX idx_roadmap_item_type (item_type)
);
```

```sql
CREATE TABLE audit_rejected_pick_outcomes (
  reject_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  pick_key VARCHAR(191) NOT NULL,
  asset_class VARCHAR(32) NOT NULL,
  symbol VARCHAR(64) NOT NULL,
  strategy VARCHAR(128) NOT NULL,
  source_system VARCHAR(128) DEFAULT NULL,
  direction VARCHAR(16) NOT NULL,
  entry_price DECIMAL(20,8) DEFAULT NULL,
  take_profit DECIMAL(20,8) DEFAULT NULL,
  stop_loss DECIMAL(20,8) DEFAULT NULL,
  confidence DECIMAL(8,5) DEFAULT NULL,
  score DECIMAL(8,4) DEFAULT NULL,
  gate_name VARCHAR(128) NOT NULL,
  fail_reason TEXT NOT NULL,
  would_open_if_exempt TINYINT(1) DEFAULT 0,
  created_at TIMESTAMP NOT NULL,
  resolved_at TIMESTAMP NULL DEFAULT NULL,
  max_favorable_excursion DECIMAL(12,6) DEFAULT NULL,
  max_adverse_excursion DECIMAL(12,6) DEFAULT NULL,
  outcome ENUM('WON','LOST','OPEN','TIME_EXIT','UNKNOWN') DEFAULT 'UNKNOWN',
  pnl_pct DECIMAL(12,6) DEFAULT NULL,
  counterfactual_exit_reason VARCHAR(128) DEFAULT NULL,
  price_source VARCHAR(128) DEFAULT NULL,
  data_quality_flags JSON DEFAULT NULL,
  INDEX idx_rejected_gate_class (asset_class, gate_name),
  INDEX idx_rejected_strategy (asset_class, strategy, symbol),
  INDEX idx_rejected_created (created_at)
);
```

```sql
CREATE TABLE gate_exemption_trials (
  trial_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  scope_hash VARCHAR(64) NOT NULL,
  asset_class VARCHAR(32) NOT NULL,
  strategy VARCHAR(128) NOT NULL,
  symbol VARCHAR(64) DEFAULT NULL,
  direction VARCHAR(16) DEFAULT NULL,
  regime VARCHAR(128) DEFAULT NULL,
  gate_name VARCHAR(128) NOT NULL,
  exemption_type ENUM('SCORE_RELAXATION','TRUST_RELAXATION','PROBATION_ROUTE') NOT NULL,
  score_delta DECIMAL(8,4) DEFAULT NULL,
  criteria_json JSON NOT NULL,
  start_at TIMESTAMP NOT NULL,
  end_at TIMESTAMP NULL DEFAULT NULL,
  n_shadow INT DEFAULT 0,
  win_rate DECIMAL(8,5) DEFAULT NULL,
  profit_factor DECIMAL(12,6) DEFAULT NULL,
  wilson_lower DECIMAL(8,5) DEFAULT NULL,
  dsr DECIMAL(8,5) DEFAULT NULL,
  status ENUM('PROPOSED','ACTIVE','PASSED','FAILED','EXPIRED') DEFAULT 'PROPOSED',
  auto_expire_reason TEXT DEFAULT NULL,
  INDEX idx_exemption_status (status, asset_class),
  INDEX idx_exemption_scope (scope_hash)
);
```

## Dashboard Items To Add

| Class | Type | Severity | Title | Recommended dashboard action |
|---|---|---|---|---|
| OVERALL | INCIDENT | P0 | Outcome ledger health blocks gate decisions | Add red banner and freeze promotions until health is green. |
| OVERALL | ENHANCEMENT | P0 | Rejected-pick counterfactual ledger | Add winners-blocked/losers-blocked by gate. |
| EQUITY | ENHANCEMENT | P1 | Score 55-60 large-cap replay | Show gray-zone replay for QQQ/AMD/TSLA/AAPL. |
| ETF | ENHANCEMENT | P1 | VIX < 25 sector-rotation pilot | Show filtered/unfiltered SPDR sector results. |
| CRYPTO | ENHANCEMENT | P1 | Missed-gainer universe/trigger audit | Split misses into universe, trigger, gate, and trust causes. |
| COMMODITY | INCIDENT | P0 | COT over-emission contamination | Publish raw vs dedup vs pilot metrics before promotion. |
| FOREX | INCIDENT | P0 | Broad forex edge not investable | Hard-disable broad emission; track pruned majors pilot. |
| BOND | INCIDENT | P1 | Bond sample too small and concentrated | Keep research-only until scanner/pilots produce clean sample. |
| FUTURES | INCIDENT | P2 | Futures tile has no real sample | Merge/deprecate tile or wire financial futures emitter. |
| PENNY | INCIDENT | P0 | Penny/meme bucket is negative expectancy | Quarantine from parent asset-class production universes. |

## Verification

- Validated skill frontmatter:
  - `python3 /home/eaguiar2015/.codex/skills/.system/skill-creator/scripts/quick_validate.py .claude/skills/dedup-md-files`
- Dedupe command used:
  - `python3 tools/dedup_md_files.py --glob 'reports/asset_class_90day_plan_*_2026-05-15.md' --glob 'reports/90day_gap_analysis_2026-05-15.md' --json`
- Result: 9 input files, 9 unique canonical files, 0 missing in the root checkout.
