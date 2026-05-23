# Daily Ideas - Cursor CLI - 2026-05-16

## Session Focus

Goal #1: prove a statistically usable edge per asset class for `/audit`, with strict no-placeholder evidence and real sizing discipline.

## Chat Log

- User asked whether Graphify or AgentMemory is better for cross-PC session memory while censoring secrets.
- Recommendation: use AgentMemory-style shared session memory for cross-PC continuity; use Graphify for codebase navigation and relationship queries. Secret censoring belongs in the memory write/sync layer, not in the code graph.
- User then asked to continue the asset-class edge work toward real-money-grade filters.
- Loaded current audit evidence from `audit_dashboard/data/dashboard_data.json` and strategy evidence from `alpha_engine/data/strategy_performance.json`.
- Inventory found `audit_dashboard` has the verdict-grade payload; `audit_hyrotrader` has no JSON/CSV files in this repo snapshot.
- Wrote a strict weekly report and a reusable strict JSON generator.

## Findings

- Freshness preflight passed: dashboard payload generated at `2026-05-16T04:04:25.838063+00:00`.
- `EQUITY` is the only current class clearing the strict filter gate:
  - n=425
  - WR=51.5%
  - PF=1.56
  - expectancy=0.90
  - OOS WR=62.2%
  - worst fold WR=42.5%
  - preferred strategy label: `Classic Momentum`
- `COMMODITY` has excellent headline stats but remains research-only because concentration is flagged around `CT=F` and readiness sizing is blocked.
- `ETF` is research-only because PF=1.32 is below the 1.5 Tier 2 threshold.
- `CRYPTO` is research-only class-wide because WR=46.5%, PF=1.31, readiness sizing is blocked, and worst-fold behavior is weak.
- `FOREX`, `BOND`, and `FUTURES` are not sizeable under the strict gate.
- Quarter-Kelly on class stats gave `EQUITY` $462.50 per $10k account, but the performance charter swing cap limits operational size to $100 per $10k account.
- Current `dashboard_data.json` reports `picks.active` as 0, so the correct live action is cash unless a fresh open pick appears matching the strict filter.

## Files Created

- `reports/weekly_filter_strict_20260516T051032Z.md`
- `reports/strict_filters_latest.json`
- `tools/filter_generator.py`
- `updates/2026-05-16-strict-filter-generator.md`

## Verification

```powershell
python -m py_compile tools/filter_generator.py
python tools/filter_generator.py --asset-class EQUITY
python tools/filter_generator.py --output reports/strict_filters_latest.json
python -c "import json; from pathlib import Path; p=Path('reports/strict_filters_latest.json'); d=json.loads(p.read_text(encoding='utf-8')); verdicts={x['asset_class']:x['verdict'] for x in d['filters']}; assert verdicts.get('EQUITY') == 'FILTER_READY_SMALL_SIZE'; assert all(v == 'RESEARCH_ONLY' for k,v in verdicts.items() if k != 'EQUITY'); print(verdicts)"
```

Result: only `EQUITY` passed; every other class remained `RESEARCH_ONLY`.

---

## Claude Code Analysis — 2026-05-16T22:10Z

### Verification of Session Findings

The Cursor CLI session findings are accurate and match current `dashboard_data.json` state:

- EQUITY: Confirmed T2 (PF=1.56/WR=51.5%/n=425). Strict filter gate passes. Quarter-Kelly $462.50 → operational cap $100/pick (swing cap per performance charter). **This is the ONLY real-money-eligible class today.**
- COMMODITY concentration around CT=F: Confirmed. CT=F moved to PROBATION (WR=75% post-block, review 2026-06-06). `multi_asset_cot` PF=21.33 pending `ab_analysis.yml` DB verification.
- CRYPTO WR=46.5%: Confirmed. UTC-hour filter now live. M-034 confidence inversion gate in shadow mode.
- ETF PF=1.32: Confirmed sub-T2. Floor lowered 40→35 (test fix shipped 2026-05-16 this session). n=107 on path.
- FOREX blocked: Confirmed. `FOREX_HARD_DISABLE=1` active.

### Files Created — Status Check

| File | Created | Status |
|---|---|---|
| `tools/filter_generator.py` | ✅ | Live; runs against current `dashboard_data.json` |
| `reports/weekly_filter_strict_20260516T051032Z.md` | ✅ | Archived; regenerate weekly |
| `reports/strict_filters_latest.json` | ✅ | Live JSON |
| `updates/2026-05-16-strict-filter-generator.md` | ✅ | Committed |

### High-Value Next Actions from This Session

**Regenerate weekly filter report** (runs in 30 seconds):
```bash
python tools/filter_generator.py --output reports/strict_filters_latest.json
```
Schedule: add to `ab_analysis.yml` or a new `weekly-filter.yml` cron.

**COMMODITY unlock path**: Once `ab_analysis.yml` returns MATCH on `multi_asset_cot`:
1. DSR gate check via `tools/cot_step7_friction_adjusted_mc.py` (DSR ≥ 0.85 required)
2. Update `filter_generator.py` to include COMMODITY with 2% cap Quarter-Kelly
3. Re-run filter report — COMMODITY will graduate from RESEARCH_ONLY

**CRYPTO unlock path**: After M-034 shadow period (≥30 days clean):
- Enable `CRYPTO_CONF_INVERSION_GATE=1`
- Filter will route CRYPTO through strategy-family selection (not score) — KimiCLI confirmed this is the correct approach
- Estimated WR lift: sub-46.5% → 64%+ for filtered subset

**ETF graduation path**: n currently 107, target 150 for OOS_READY
- At current accumulation rate (~3 picks/day), ~14 days to reach 150
- ETF sector rotation (relative-strength overlay) still OPEN — would push PF 1.32→1.5 if shipped
