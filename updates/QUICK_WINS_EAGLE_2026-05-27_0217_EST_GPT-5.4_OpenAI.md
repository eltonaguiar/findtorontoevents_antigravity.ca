# Audit quick wins — EAGLE review

**Timestamp:** 2026-05-27 02:17 EST (Toronto local review window)  
**Model / provider:** GPT-5.4 / OpenAI

## What was reviewed

- Deduplicated canonical report set:
  - `reports/90day_gap_analysis_2026-05-15.md`
  - `reports/asset_class_90day_plan_{BOND,COMMODITY,CRYPTO,EQUITY,ETF,FOREX,FUTURES,PENNY_MEME}_2026-05-15.md`
- Pipeline / gate path:
  - `audit_trail/quality_gates.py`
  - `tools/dashboard_hc_rules.py`
  - `audit_dashboard/hc_filter.js`
  - `alpha_engine/money_ready_verdict.py`
  - `audit_dashboard/data/pf_registry.json`
  - `audit_dashboard/data/quarantine_manifest.json`
- Roadmap / incidents surfaces:
  - `DAILY_IDEAS.MD`
  - `audit_dashboard/incidents.html`
  - `updates/index.html`

## Lead verdict

1. **Best near-term classes:** EQUITY and ETF.
2. **Potential but not trustworthy yet:** COMMODITY until COT history is re-aggregated post dedup.
3. **Needs hard containment or isolation:** FOREX, PENNY_STOCK, MEMECOIN.
4. **Research-only for now:** BOND.
5. **Should stop being its own empty tile:** FUTURES; merge conceptually into a unified futures / commodity-futures sleeve.

## Per-asset-class strategy call

| Class | Current call | Best next strategy |
| --- | --- | --- |
| CRYPTO | Too noisy; broad dynamic universe dilutes edge | Liquid-core sleeve only: BTC/ETH/SOL + top liquid L1s, on-chain/funding, strict liquidity/source whitelist |
| EQUITY | Strongest non-crypto path | Large-cap momentum + quality + PEAD + hard VIX/SPY regime gates; split out penny/meme contamination |
| ETF | Most underused clean edge | SPDR sector rotation + VIX<25 gate + dual-momentum fallback |
| COMMODITY | Metrics currently overstated by COT history bug risk | Re-aggregate first, then diversified COT + carry/momo across 5-7 contracts |
| FOREX | Realized book still weak | 4-major paper-only sleeve with SHORT/DXY/session gating; isolate winners, suppress class drag |
| BOND | Thin sample, no real edge yet | Research-only: TIPS MR, curve carry, HYG-LQD credit MR |
| FUTURES | Empty tile, duplicate taxonomy | Merge into futures/commodity-futures reporting model; add financial futures only as research sidecars |
| PENNY / MEME | Structural drag | Full quarantine, no production sleeve |

## Safety-gate conclusions

- **Profitable-but-filtered risk exists.** Likely false negatives are concentrated in:
  - HC JS/Python drift,
  - strict small-sample FOREX / non-core class forward-trade floors,
  - concentration gates masking concentrated but real sleeves,
  - quarantine logic that hides winners instead of surfacing them for audit.
- **Hot-streak support is incomplete today.** The repo has streak scoring in `audit_trail/quality_gates.py`, but **not** a clean auditable hot-streak exemption path in the live admission stack.
- **No class currently deserves a blind “sure thing” exemption.** There are repeatable mean-reversion / range behaviors in ETF, BOND, and some major FX setups, but nothing in the current evidence base justifies calling any trade a guaranteed two-price oscillation.

## Quick wins executed in this pass

### 1. Canonical markdown path output for dedup reviews

**Problem:** `tools/dedup_md_files.py` already deduplicated markdown content correctly, but there was no direct CLI mode for “just print the exact canonical paths” without piping JSON through `jq`.

**Change made:**

- Added `--paths-only` to `tools/dedup_md_files.py`
- Updated `.claude/skills/dedup-md-files/SKILL.md` with the direct canonical-path invocation

**Why it matters:** this makes large audit/report review batches faster and safer by giving one canonical path per duplicate group immediately, which is exactly the workflow requested for the asset-class report sweep.

**Verification used:**

```bash
python3 -m py_compile tools/dedup_md_files.py
python3 tools/dedup_md_files.py --from-file /tmp/user_md_paths.txt --paths-only
```

## Proposed PR list (highest ROI first)

1. **dedup-md-files: add `--paths-only` direct canonical output**  
   Files: `tools/dedup_md_files.py`, `.claude/skills/dedup-md-files/SKILL.md`
2. **audit-review docs: cross-asset quick wins + remaining backlog**  
   Files: `updates/*EAGLE*.md`
3. **profitable-but-filtered audit lane**  
   Files: `audit_trail/quality_gates.py`, `audit_trail/dashboard_generator.py`, optional DB sidecar table
4. **HC parity: JS/Python rule drift removal**  
   Files: `audit_dashboard/hc_filter.js`, `tools/dashboard_hc_rules.py`, `config/hc_gate_params.json`
5. **EQUITY clean-universe split**  
   Files: `alpha_engine/config.py`, `alpha_engine/scanner.py`, `alpha_engine/equity_strategies.py`
6. **ETF VIX-gated sector rotation activation**  
   Files: `alpha_engine/etf_strategies.py`, emitter wiring, gate/config path
7. **COMMODITY post-dedup re-aggregation + honest tile reset**  
   Files: dashboard generator / reporting path, COT audit helpers
8. **FOREX isolation / hard-disable guard**  
   Files: `audit_trail/quality_gates.py`, config/env gates

## Seed rows for Incidents / Enhancements dashboard

### Proposed INCIDENT rows

| Type | Class | Priority | Title | Why it belongs on the board |
| --- | --- | --- | --- | --- |
| INCIDENT | OVERALL | P0 | Profitable-but-filtered picks are not surfaced anywhere | Hides false negatives and blocks gate-quality learning |
| INCIDENT | OVERALL | P0 | HC JS/Python parity drift changes eligibility by surface | Same pick can qualify differently across code paths |
| INCIDENT | COMMODITY | P0 | COMMODITY headline PF/WR still contaminated by pre-clean COT aggregation | Current class story is not trust-safe |
| INCIDENT | FOREX | P1 | FOREX class still aggregates losers around a small winner subset | Needs isolation instead of blanket class treatment |
| INCIDENT | EQUITY | P1 | Penny/meme names still pollute main EQUITY sleeve | Backtests use clean large-cap set; live path does not |
| INCIDENT | FUTURES | P1 | FUTURES is a zombie tile with real futures hidden under COMMODITY | Taxonomy obscures edge and misleads the page |

### Proposed ENHANCEMENT rows

| Type | Class | Impact | Title | Why it matters |
| --- | --- | --- | --- | --- |
| ENHANCEMENT | OVERALL | HIGH | Add profitable-but-quarantined / profitable-but-filtered audit lane | Makes false negatives visible without changing live picks |
| ENHANCEMENT | OVERALL | HIGH | Add bounded hot-streak exemption with explicit audit trail | Lets proven sleeves earn temporary exemptions safely |
| ENHANCEMENT | ETF | HIGH | Make VIX-gated sector rotation the primary ETF sleeve | Strongest low-cost clean edge in the current stack |
| ENHANCEMENT | EQUITY | HIGH | Split LARGE_CAP_EQUITY from PENNY_MEME research-only names | Removes a major hidden drag |
| ENHANCEMENT | COMMODITY | HIGH | Recompute class health from deduped independent COT cycles only | Restores trust in commodity metrics |
| ENHANCEMENT | FUTURES | MED | Replace empty FUTURES tile with unified futures taxonomy | Makes `/audit` reporting honest |

## Recommended unified database model

### `finding`

- `id`
- `finding_type` (`incident`, `enhancement`, `roadmap`)
- `asset_class`
- `severity`
- `impact`
- `status`
- `title`
- `summary`
- `component`
- `recommended_fix`
- `owner`
- `reporter`
- `source_doc_path`
- `source_doc_url`
- `parent_id`
- `canonical_hash`
- `evidence_json`
- `created_at`
- `updated_at`
- `closed_at`

### `finding_event`

- `id`
- `finding_id`
- `event_type`
- `old_value`
- `new_value`
- `actor`
- `event_at`
- `payload_json`

### Optional `finding_link`

Cross-links between findings, PRs, reports, incidents, enhancements, and roadmap epics.

## Sources used

- `reports/90day_gap_analysis_2026-05-15.md`
- `reports/asset_class_90day_plan_CRYPTO_2026-05-15.md`
- `reports/asset_class_90day_plan_EQUITY_2026-05-15.md`
- `reports/asset_class_90day_plan_FOREX_2026-05-15.md`
- `reports/asset_class_90day_plan_COMMODITY_2026-05-15.md`
- `reports/asset_class_90day_plan_ETF_2026-05-15.md`
- `reports/asset_class_90day_plan_BOND_2026-05-15.md`
- `reports/asset_class_90day_plan_FUTURES_2026-05-15.md`
- `reports/asset_class_90day_plan_PENNY_MEME_2026-05-15.md`
- `DAILY_IDEAS.MD`
- `audit_dashboard/incidents.html`
- `updates/index.html`
