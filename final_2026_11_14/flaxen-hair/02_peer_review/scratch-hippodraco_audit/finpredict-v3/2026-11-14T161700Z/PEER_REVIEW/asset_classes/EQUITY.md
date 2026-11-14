# PEER REVIEW — EQUITY (STOCKS)

**Reviewer:** finpredict-v3 peer-review subagent, 2026-11-14T16:17Z

## 1. Peer docs read
- v4 `noncrypto_deep_dive.md` §2 EQUITY (n=249 intrabar, 757 live picks).
- v4 `dashboard_data_report.md` §2.1/2.2/2.3/4.2 §5 (EQUITY NOT_READY; filter inversion).
- v4 `market_crossref_report.md` Equities (MSFT/AMZN/BRK.B/PLTR/GOOGL sampling).
- v1 `2026-11-14-prediction-system-audit.md` §2/§7 (n=8 vs n=759 vs n=738; z=+1.39).
- v2 `E_statistical.md` §5 (policy-clean n=461, z=-3.03) + §7.1 (summary WR 162.4% bug).
- ML-audit `proposed_fixes/stocks/FIX_PROPOSED.md` (5 stale active; 1 closed; backfill).
- ML-audit `proposed_fixes/overall/FIX_PROPOSED.md` (PnL calc, staleness, lifecycle).
- Mine `2026-11-14-prediction-data-hygiene.md` (EQUITY no price bug; last_quote).

## 2. Peer verdict per class
- v4 (noncrypto): "EQUITY Verdict: STALE / REHAB" — 757 open, avg PnL **-5.22%**, intrabar **FAIL (n=249, WR 59%, PF 0.934)**; all top picks demoted to WATCH with null TP/SL, position_size 0.0.
- v4 (dashboard): money-ready **NOT_READY** (PF 0.94, WR 59.20, MDD 100%, SPA p=0.256); dashboard Recent-closed vs raw DB 90d "filters out winners".
- v1: "EQUITY is NOT a robust positive" — three inconsistent aggregators: headline **n=8 (75% WR, PF 8.86, CI≈[0.41,0.93])**; non_crypto n=759 (46.1%); recent_closed n=738 (47.0%); peer v3 full **n=461 ~43% / PF 0.70**. z=+1.39 (not significant).
- v2: **n=461, WR 42.95%, PF 0.7022, z=-3.03, p=2.5e-3** — survives Bonferroni as *significantly BELOW 50%*.
- ML: stocks pipeline produces ~no resolved outcomes — **5 active stock picks (AMZN/AAPL/QQQ) stale ~172d (2026-05-25)**, still ACTIVE, no current_price/pnl; **only 1 closed stock pick** vs 6,400 crypto.

## 3. Peer-proposed quick wins (with source + dedup)
1. Backfill `asset_class='EQUITY'` via `alpha_engine.asset_class.EQUITY_SYMBOLS` (ML stocks §3.2; ML overall §3.3 — DUPLICATE).
2. Refresh `current_price`/`unrealized_pnl` for stale picks via `fetch_stock_prices.py` (ML stocks §3.1; ML overall §3.2; v4 dashboard rec #5 — DUPLICATE).
3. Staleness guard: auto-close/flag picks >30–60d (TIME_EXIT/STALE_AGEOUT) (ML stocks §3.3; ML overall §3.4; v4 crossref rec #1/#3; mine §per-class — DUPLICATE).
4. Re-run equity scanners (equity_breakout, bb_zscore_mr, rsi_divergence_mr, pead, factor, insider, sector_rotation) + gatekeeper EQUITY:2 (ML stocks §3.4).
5. Investigate EQUITY dashboard filter inversion (raw DB 90d WR 66.7%/PF 5.56/+4.94% vs dashboard 37.4%/0.70/-0.72%) (v4 dashboard §4.2) — UNIQUE to v4.
6. Resolve TIME_EXIT backlog (4,220 symbol-days) so forward WR/PF become valid (v4 dashboard rec #3; v1 §3).

## 4. Disagreements / contradictions
- **n=8 vs n=461**: v1 headline n=8 (75% WR) is a survivor artifact; v2 canonical n=461 says significantly losing. Reconciliation: use n=461 (policy-clean net) as the significance surface; treat n=8 as meaningless.
- **Positive vs losing**: v1 recent_closed EQUITY sum +238.4 (positive) but v2 policy-clean net PF 0.70 (losing) and v4 intrabar PF 0.934. Aggregate "roughly breakeven"; sign depends on surface + filter.
- **Live counts**: ML/DB `live_picks.db` shows 5 active; v4 `picks_now_live_pnl.json` shows 757 open. Different inventories; both stale/unresolved.

## 5. Gaps
- v4 `proposed_fixes/equity/` is EMPTY (no fix doc) — NOT FOUND.
- No class-level n>=100 forward/paper ledger; `at_signal_outcomes` stale ~80d makes intrabar truth frozen.
- No resolution of the 5–757 stale open equity rows (no exit events).

## 6. Recommended best-of (master plan)
Use v2 policy-clean **n=461 (z=-3.03)** as the canonical significance reading (EQUITY loses). Apply ML/U backfill + staleness-guard + price refresh as P0 infra. Add v4's filter-inversion investigation (rows are being excluded that flip the sign). Treat as **not money-ready / rehabilitate** — do not size until a forward ledger n>=100 with PF>=1.5 exists.
