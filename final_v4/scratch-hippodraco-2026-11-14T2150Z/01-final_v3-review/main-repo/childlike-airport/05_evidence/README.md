# 05 — Evidence & Review Inventory

**Date:** 2026-11-14 | **Reviewer:** Kilo (childlike-airport)

## 1. Local Files Modified Today (working tree)
- `audit_trail/dashboard_generator.py` — after-cost net-per-trade fallback (`stamp_class_after_cost`).
- `audit_trail/universal_pick_resolver.py` — gap-aware fill pricing (`_gap_fill_price`).
- `tools/hc_gates_python.py` — `passes_per_class_cost_gate`.
- `___HELL_HEALTH_OPENCODE.MD` — context/health note.

## 2. GitHub `origin/main` Reviewed (2026-11-14)
Representative: `66885645` (quant-audit final_v2), `b5116469/1b7cff57` (finpredict-v2), `681f2fe6/b8d7d033` (per-class profitability+corrections), `ee8a6e20` (profitability synthesis), `5bf4991e` (accept correction), `cb346162` (finpredict-v3 adjudication), `355d50f6` (hilarious-seer), `97001b6f` (VWAP replication/validation/falsification), `9732f283` (v3/v4 scorecard/verdicts not proved), plus `[skip ci]` data/scan updates. Notable: `updates/2026-11-14-PROFITABLE-APPROACH-VWAP-MEAN-REVERSION.md`, `research/profitability/{SCORECARD,HYPOTHESES,README,validation/VWAP_*}`.

## 3. `final_v2` Packages Reviewed
- `final_v2/childlike-airport/` (this session): exec summary, peer synthesis, per-asset, candidates (incl. v12), roadmap, remediation, validation framework.
- `final_v2/quant-audit-2026-11-14/` (0/166 money-ready, verdict/remediation), `final_v2/fix-p0-safe-fixes-2026-11-14-main/` (adjudication), `final_v2/finpredict-v2/`, `final_v2/hilarious-seer/`, `final_2026_11_14/final_v2/childlike-airport/`.

## 4. Older/Local Prediction Structures Reviewed
- `2026-11-14/finpredict/2026-11-14T160004Z/` (plan, peer reconciliation, quick wins, ITERATION-001..005).
- `2026-11-14/finpredict-v2_20261114-1602/` (master audit, actions GA1-4, recommendations).
- `2026-11-14/finpredict-v3_20261114-1620/`, `2026-11-14/finpredict-v4_20261114T1622Z/`.
- `research/profitability/` (SCORECARD: 23 candidates, 0 proved; v1-v4; VWAP replication/stats/verdict).
- `final_v3/quant-audit-2026-11-14/` (pre-existing).

## 5. Untracked/Supporting Artifacts (MF & infra)
- `alpha_engine/data/mutual_fund_metadata.csv` (37 funds: ER 0.015%–0.74%, $0/$3000 mins, no load/12b-1).
- `alpha_engine/mutual_fund_ranker.py`, `alpha_engine/fund_holdings_deriver.py`.
- `audit_dashboard/data/mutut_fund_rankings.json` (T1 SWPPX 87.1, T2 FSKAX 79.0, 2026-10-22), `mf_walkforward_results.json`, `mf_traits_walkforward_results.json`, `audit_dashboard/mutual-funds.html`.

## 6. New Computation (this session)
- `/tmp/kilo/regime_filtered_vwap_v12.py` → `/tmp/kilo/regime_filtered_vwap_v12_results.json`: 4h, 730d, 40% size, 20bps RT, 8-symbol pooled n=129, WR 44.2%, PF 1.210, Sharpe 3.76, Ret 12.7%, MDD 10.0%, PBO 0.489, P(SR>0)=1.000 (strict PBO<0.3 FAIL). Core profitable: BTC/ETH/SOL/XRP/ADA; losers: DOGE/AVAX/LINK.

## 7. Key Numbers Cited
- System: 81% fake 0% P/L, losses ~10x understated, ~78.6% EXPIRED zombies, 129 picks stale ~172d, audit trail core empty, 0/166 money-ready cells, 23 protocol candidates 0 proved.
- VWAP-MR: v11 PF 1.435 Sharpe 7.10 MDD 3.5% n=65 PBO 0.480; v12 PF 1.210 Sharpe 3.76 MDD 10% n=129 PBO 0.489.
- TSMOM (IT-005): CAGR 23.0%, Sharpe 2.13, PF 1.40, MDD −17.4%, t=5.56, CI [1.25,3.25] (7.4y).
- Variant C: PF 1.26, n=237, p<0.0013 (pilot). mega_mutation: PF 3.12–5.816 BT / 8.32 FW (candidate).

*Inventory only; no claim of live profitability.*
