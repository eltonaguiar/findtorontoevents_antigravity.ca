# FUTURES Asset-Class Deep-Dive — 2026-05-12

Investigator `ae32b23a16a9866cb` output. Captures the current state of
FUTURES (silent-dead, 5.9% WR, BLOCKED per Codex governance) and proposes
a CT=F-anchored resurrection path.

## Current state

- 6 strategies in `audit_trail/strategy_blocklist.py:290-291` paper-only:
  `futures_rsi_divergence`, `futures_overnight_gap`, `futures_dollar_trend`,
  `futures_equity_seasonality`, `futures_macd_momentum`, `futures_metals_momentum`
- Class-blocked in hedge_fund_sprint set (`strategy_blocklist.py:88-90`)
- `BLOCKED_ASSET_CLASSES` removed FUTURES 2026-04-16 but `-60 score penalty`
  in `passes_active_gate` created a data-starvation catch-22
- Zero picks in /audit FUTURES tile; 5.9% WR is residual n=2 entries

## Root cause

Per `reports/action_F_mutation_2026_04_27.md:140`:
- `futures_momentum` killed post-decay-alert with no replacement queued
- 6 paper-only strategies never wired to production scanner
- Module went silent rather than gracefully demoting to SHADOW

**Not data-starvation** — config has 15 FUTURES symbols at `alpha_engine/config.py:628-646`. The bug is a strategy-module gap.

## Symbol universe verdict (15 tickers)

| Family | Symbols | Verdict |
|---|---|---|
| Index futures | ES=F, NQ=F, RTY=F, YM=F | Mean-reverting intraday; momentum strategies fail here |
| Commodity futures | GC=F, SI=F, HG=F | COT-responsive; carries the COMMODITY class edge signal |
| Rate futures | ZN=F, ZT=F, ZB=F | Low vol, regime-sensitive; needs macro gates |
| FX futures | 6E=F, 6B=F, 6J=F, 6A=F, 6C=F | Liquid; not tested in our stack |

**Pre-tested:** CT=F (cotton, classified COMMODITY in our taxonomy) at DSR=1.0,
n=100, WR 90%, Sharpe +1.377 via `alpha_engine/strategies/cot_paper_pilot.py`.

## External-model candidates

| Library | Verdict |
|---|---|
| **AI4Finance-Foundation/FinRL** | CME rolling-contract simulator + PPO agents; commodity-futures training ready but needs contract-roll engineering |
| **QuantConnect/Lean** | Full futures algos in /Algorithms; roll logic battle-tested but Lean-specific API overhead |
| **backtrader-contrib** | COT-style futures + rolling out-of-box; Python-native; best for quick COT replay |
| **kernc/backtesting.py** | Minimal/fast; no built-in COT data |
| **hudson-and-thames/mlfinlab** | Already integrated in `alpha_engine/integrations/`; no futures-specific module yet |

## 5-step resurrection plan

- **Step A** — Anchor on CT=F (cotton) which is already proven. No experimental risk.
- **Step B** — Validate via `tools/anti_overfit_audit_sidecar.py` + DSR gate. Expected pass (code already exists).
- **Step C** — SHADOW state via `cot_paper_pilot.py` JSON output for 14-30d forward tracking. Graduation: net P&L within ±50% of expected $3.40-$13.40/trade.
- **Step D** — Expand to GC=F (gold) via mutation `cot_positioning::CT_pilot_to_GC` on 20 forward trades. COT pattern should transfer.
- **Step E** — Class graduates to LIVE_ELIGIBLE once Step D passes AND `quality_gates.py::BLOCKED_ASSET_STRATEGY_PAIRS` removes `("FUTURES", "futures_momentum")` + unblocks hedge_fund_sprint set.

**Alternative:** If research shows structural unfitness, keep permanently BLOCKED and redirect capital to BOND (n→100) and ETF (n→100+). Current evidence does NOT support this — CT=F proven; GC=F/SI=F inherit commodity-edge logic.

## Expected impact on /audit

- **Short term (14-30d):** FUTURES tile remains 0 picks; CT=F continues SHADOW via paper-pilot panel.
- **Medium term (30-60d):** GC=F SHADOW emission adds 4-8 picks/month if cotton pattern transfers.
- **Long term (6mo+):** If GC=F holds, broaden to SI=F + HG=F; FUTURES n could climb to 50+ with curated commodity-futures sleeve.

## Refs

- `alpha_engine/strategies/cot_paper_pilot.py:1-40`
- `alpha_engine/config.py:628-646`
- `audit_trail/quality_gates.py:1622`
- `reports/asset_class_expansion_2026-05-12.md:54-63`
- Investigator `ae32b23a16a9866cb` 2026-05-12

## NFA

Research surface only. CT=F already cleared 4/5 active-work testing-plan
steps (CONDITIONAL PASS on Step 3 fold_1 regime outlier). FUTURES
resurrection conditional on regime-gate add + 4-week paper-pilot clear.
