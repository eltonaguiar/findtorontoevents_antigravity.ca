# 08 — Evidence Index

## Reviewed Inputs
- **All `final_v3`:** root (`README`, BUGS/DEEP_INVESTIGATION, plans, SubQ, focus, evidence), `final_v3/childlike-airport/**`, `final_v3/quant-audit-2026-11-14/**`, `final_v3/feat-stop-fill-cost-gate-final-v3/**`, `.kilo/worktrees/finpredict/final_v3/finpredict/**`, `.kilo/worktrees/hilarious-seer/final_v3/**`.
- **Earlier:** `final_v2/childlike-airport/**`, `final_2026_11_14/final_v2/childlike-airport`, `final_v2/{quant-audit,fix-p0-safe-fixes,finpredict-v2,hilarious-seer}`, `2026-11-14/finpredict*`, `research/profitability/**`.
- **Local uncommitted/24h:** `git status`; prediction-relevant mtime scan; untracked `alpha_engine/*mutual_fund*`, `audit_trail/{compound_overlap_aware,integrity_gates,ledger_gates}.py`, `audit_dashboard/data/mf*`, `calculate_metrics*.py`, `mega_mutation_closed_ledger.json`.
- **Remote:** `git fetch origin`; `git log --since=2026-11-14`/name-status on `origin/main` & branch refs (VWAP validation/falsification, scorecard v3/v4, final_v2/v3 peers).

## Key Numbers
- **VWAP v12 (this session):** `/tmp/kilo/regime_filtered_vwap_v12_results.json` — n=129, WR 44.2%, PF 1.210, Sharpe 3.76, Ret 12.7%, MDD 10.0%, PBO 0.489, P(SR>0)=1.000 (strict PBO<0.3 FAIL). Core profitable BTC/ETH/SOL/XRP/ADA; losers DOGE/AVAX/LINK.
- **VWAP v11:** PF 1.435, Sharpe 7.10, MDD 3.5%, n=65, PBO 0.480.
- **TSMOM (IT-005):** CAGR 23.0%, Sharpe 2.13, PF 1.40, MDD −17.4%, CI [1.25,3.25] (7.4y).
- **Variant C:** PF 1.26, n=237, p<0.0013. **mega_mutation:** PF 3.12–5.816 BT / 8.32 FW (candidate).
- **System:** 0/166 money-ready cells; 23 protocol candidates 0 proved; 81% fake 0% P/L; ~78.6% zombies; 129 picks stale ~172d; audit trail core empty; CI failures/cancellations (peer-reported).

## Commands (representative, read-only/analysis)
`git fetch/log/status`, `find/ls/cat/rg` across final_v2/v3/v4, 2026-11-14, research/profitability, MF artifacts; executed `python3 /tmp/kilo/regime_filtered_vwap_v12.py` (captured JSON).

## Limitations
No live SubQ artifact (matrix is SubQ-equivalent). Peer replay/backtest metrics not independently reproduced except VWAP v12. Dirty worktree with unrelated untracked files. Deliverable is documentation-only; no commits/push.
