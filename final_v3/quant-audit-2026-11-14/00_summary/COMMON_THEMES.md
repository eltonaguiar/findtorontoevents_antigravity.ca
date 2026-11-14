# 00 Summary — Common Themes from All Reviews (final_v3, 2026-11-14)

**Scope:** All files modified today + final_v2 peer packages + remote GitHub commits today + local untracked financial-prediction files  
**Date:** 2026-11-14  
**Bottom line:** No asset class is money-ready. All 9 classes are `NOT_READY`, `WATCH`, or `INSUFFICIENT_DATA`. Zero of 166 live-ledger strategy×class×direction cells pass all money-ready gates. Zero of ~23 protocol research candidates passed strict proof. Zero peer approaches survive independent re-examination.

---

## Files Reviewed Today

### Modified source files (working tree)
| File | Change | Relevance |
|---|---|---|
| `audit_trail/dashboard_generator.py` | +12 lines: after-cost net-per-trade fallback via `stamp_class_after_cost` | Fixes dead `after_cost_net_per_trade=None` for all 3,500 closed rows |
| `audit_trail/universal_pick_resolver.py` | +57 lines: gap-aware fill pricing (`_gap_fill_price`) | Corrects SL understatement on gap-downs, TP overstatement on gap-ups |
| `tools/hc_gates_python.py` | +33 lines: per-class cost gate (`passes_per_class_cost_gate`) | Blocks picks when class avg PnL < 3x round-trip cost; ~390 picks/month were emitted despite costs exceeding average result |
| `___HELL_HEALTH_OPENCODE.MD` | +156 lines | Health context |

### Commits today (GitHub)
| Commit | Message | Relevance |
|---|---|---|
| `66885645bb0` | docs: add final_v2 per-asset-class profitability audit | My final_v2 deliverable |
| `b5116469f6e` / `1b7cff57858` | final_v2: per-class profitability playbooks + peer review | Peer final_v2 package |
| `681f2fe6cbb` / `b8d7d03343e` | docs(audit): final_v2 — per-class profitability + two corrections | Corrections to prior audit |
| `ee8a6e20483` | docs: add final_v2 profitability research and strategy synthesis | Strategy synthesis |
| `5bf4991e900` | final_v2: last-chance review — accept quant-audit correction | Peer convergence |
| `cb346162f43` | final_v2(finpredict-v3): profitability-per-asset-class + peer adjudication | Finpredict-v3 adjudication |
| `355d50f62f8` | docs: add final_v2/hilarious-seer consolidated deliverable | Peer package |

### Untracked financial-prediction files (local)
| File | Relevance |
|---|---|
| `alpha_engine/data/mutual_fund_metadata.csv` | 38 mutual funds, ER 0.015%-0.74%, categories, load/12b-1 data |
| `alpha_engine/fund_holdings_deriver.py` | Derives equity screen from winning mutual fund top-10 holdings |
| `alpha_engine/mutual_fund_ranker.py` | Mutual fund ranker with hard gates (ER ≤0.50% index / ≤0.75% active, no load, AUM ≥$100M, age ≥5y, min initial ≤$3,000) |
| `audit_dashboard/data/mf_traits_walkforward_results.json` | 32 walk-forward windows, 59-universe US mutual fund WF results |
| `audit_dashboard/data/mf_walkforward_results.json` | MF walkforward results container |
| `audit_dashboard/data/mutut_fund_rankings.json` | Mutual fund T1/T2 rankings output |
| `audit_dashboard/mutual-funds.html` | Mutual funds dashboard page |
| `audit_dashboard/data/fund_holdings_consensus.json` | Fund holdings consensus output |

---

## Common Theme 1 — Data Pipeline Is Broken (All Peers Agree)

| Defect | Evidence | Affected Classes |
|---|---|---|
| Stale active picks | 129/129 ~172 days stale (childlike-airport) | All |
| PnL sign contradictions | 8 picks (e.g., NEARUSDT shows −0.129 but correct is +0.129) | CRYPTO |
| PnL calc mismatches | 15 picks vs (cp−ep)/ep | CRYPCO |
| `audit_trail.db` empty | 9 tables × 0 rows | All |
| EXPIRED→WON mislabeling | Survivorship bias; dashboard CRYPCO Smart Picks 78.93% vs DB raw 39.38% | CRYPCO |
| 53 picks frozen at pnl_pct=0% | `recent_closed_array.json` | All |
| `recent_closed.json` = 0 bytes | Abandoned file, no writer | All |
| `at_signal_outcomes` RED | ~80 days stale, n_resolved_today=0 | All |
| Dead price refresh | `fetch_prices.php` HTTP 404 since 2026-04-29 | All |
| After-cost net dead | `after_cost_net_per_trade=None` for all 3,500 closed rows (fixed today) | All |
| Gap-fill pricing bug | SL understated on gap-downs, TP overstated on gap-ups (fixed today) | All |
| Cost gate missing | ~390 picks/month emitted despite costs exceeding average PnL (ETF 267%, COMMODITY 422%) | ETF, COMMODITY |

---

## Common Theme 2 — Multiple Testing Not Properly Corrected

| Issue | Evidence | Source |
|---|---|---|
| Horizon harness reports groups_tested/groups_passed but no multiple-testing adjustment | `pi_horizon_validation.py`: `MIN_WINDOWS=4` declared but never enforced; docstring incorrectly calls reporting a correction | finpredict-v3 peer review |
| Windows split on gaps between adjacent trades, not fixed independent 60-day calendar intervals | Same file | finpredict-v3 peer review |
| PnL not netted for execution costs | Same file | finpredict-v3 peer review |
| No valid `resolution_method` required even though field missing on all 3,500 closed rows | Same file | finpredict-v3 peer review |
| 683-strategy zoo exhausted; 0/166 cells pass all gates | quant-audit screener | All |
| deepAI Variant C: null compares selection vs random selection, emissions cloned/repeated, costs not deducted | peer adjudication | deepAI |
| ITERATION-005 trend: buy-and-hold Sharpe ~2.2 on same selected assets; bear-inclusive OOS Sharpe 0.57 / null p=0.200 | peer adjudication | trend |
| mega_mutation: synthetic/replay rows, selection from very large search, TP hits not confirmed by price path | peer adjudication | mega_mutation |
| VWAP mean reversion: Sharpe/PBO certification refuted by independent re-examination | peer adjudication | VWAP |

---

## Common Theme 3 — Benchmark-Relative Alpha Unproven

| Candidate | Reported Metric | Benchmark Reality | Verdict |
|---|---|---|---|
| ITERATION-005 trend | Sharpe 2.13, CI [1.25,3.25] | Buy-and-hold Sharpe ~2.2 on same assets; OOS Sharpe 0.57 / null p=0.200 | Not proven |
| H10 SPY/QQQ RSI(2) | Sharpe 1.83, CAGR 22%, DSR 0.978 | Risk-matched benchmark Sharpe 2.168–2.285 > 1.83; edge largely T-bill carry (+3.6pp ≈ 0.827×4.38% cash yield); single-day dependence (2025-04-09 +11.20%); 1-day lag drops Sharpe to 0.696 | PASSED_GATES but NOT PROVED |
| VWAP mean reversion | Sharpe 3.76, PF 1.21, PBO 0.489 | Refuted by independent re-examination; PBO borderline 0.489 > strict 0.3 | Not validated |
| H22 BTC funding carry | Sharpe 14.24, cash CAGR 4.8% > T-bill 4.5% | n=10 < 30 minimum; capital-adjusted CAGR below T-bill for top-5/top-10 | NOT_PROVED |
| H10 (v2) | PASSED_GATES | Effective N≈38 → DSR 0.9365 < 0.95; Bonferroni α 0.001316 < p 0.001802 | Not proved |

---

## Common Theme 4 — Single-Source Concentration

| Finding | Evidence |
|---|---|
| All 166 live-ledger cells single-source | 100% from one `source_system` |
| Multi-source gate mechanically impossible for single-strategy cells | Peer adjudication: "this makes 'multi-source' mechanically impossible and the 0/166 count overstates that particular gate's evidence" |
| CRYPCO top-source share 0.9847 | money_ready_verdict.json |
| FOREX top-source share 0.8597 | money_ready_verdict.json |
| EQUITY top-source share 1.0 | money_ready_verdict.json |

---

## Common Theme 5 — Mutual Fund Infrastructure Exists but Is Not Connected to Picks

| Asset | Status |
|---|---|
| `mutual_fund_metadata.csv` | 38 funds, ER 0.015%-0.74%, categories, load/12b-1 data — complete |
| `mutual_fund_ranker.py` | Hard gates + composite score (Cost 22%, Risk 26%, Consistency 18%, Downside 16%, Capacity 10%, Manager 8%) — complete |
| `fund_holdings_deriver.py` | Derives equity screen from winning mutual fund top-10 holdings — complete |
| `mf_walkforward_results.json` | 32 windows, 59-universe US MF WF, net of ER — complete |
| `mf_traits_walkforward_results.json` | Trait-based WF results — complete |
| `mutut_fund_rankings.json` | T1/T2 output — complete |
| **Live mutual fund picks class** | **NOT_BUILT** — no mutual fund class in `asset_class.py` or gatekeeper |

---

## Deeper Investigation Items Needed

1. **Cross-ledger reconciliation**: `money_ready_verdict`, `pf_registry`, `recent_closed`, `at_raw_picks` have materially different counts (CRYPCO n=3,705 vs n=22,055; EQUITY n=250 vs n=469). Row-level reconciliation not published.
2. **Resolution provenance**: All 3,500 closed rows missing valid `resolution_method`.
3. **Per-class cost gate indexing**: `tools/per_class_cost_gate.py` index built from closed rows + `tools/data/transaction_costs.json` — needs validation.
4. **Mutual fund low-fee subset**: 38 funds in metadata, but no live class, no realized cohort, no benchmark. Need to identify sub-$50M AUM, sub-0.20% ER index funds with $0 min initial.
5. **SubQ comparison**: Not yet performed — need SubQ for coverage/comparison across options.

---

## Next: Improvement Plan →
