# Final peer reconciliation — last-chance review (2026-11-14 ~21:15Z)

Reviewed all peers' `final_2026_11_14/*` folders and the newest `quant-audit-2026-11-14` peer. This is the convergence point.

## Peer roster and what each contributed

| Peer | Final folder | Key contribution |
|---|---|---|
| `finpredict` (me) | `final_2026_11_14/finpredict` | full audit, quick-wins, master plan, trend research (Sharpe 2.13, later corrected) |
| `finpredict-v2` | `final_2026_11_14/finpredict-v2` | most rigorous: 23 candidates → **NOT PROVED**; falsified peer VWAP 3.76→1.18; funding carry = capital-limited; PnL-unit bug |
| `finpredict-v3` | `final_2026_11_14/finpredict-v3` | runnable `pi_data_hygiene` guardian (14 tests); ML leakage found (fixed on main `d8c8dd25581`); horizon harness 0/6 & 0/26 |
| `finpredict-v4` | (worktree `fix/p0-safe-fixes`) | destructive-SQL vetoed; stale-snapshot corrections |
| `flaxen-hair` | `final_2026_11_14/flaxen-hair` | PnL-unit recomputation (93 rows, 100× errors); **reviewed MY scoring framework + TradingView research** |
| `hilarious-seer` | `final_2026_11_14/hilarious-seer` | TradingView winner archetypes; model-roster fix; corroboration |
| `quant-audit-2026-11-14` | `final_2026_11_14/quant-audit-2026-11-14` | **0/166 cells money-ready**; money_ready_screener; **reviewed & corrected my ITERATION-005** |
| `childlike-airport` (ML) | on main commits | VWAP MR + trend validation (VWAP later falsified) |
| `deepAI`/`inspect-wt` | branch `audit/live-audit-2026-11-14` (now on origin) | walk-forward Variant C (PF 1.26, p<0.0013 — needs independent reproduction) |
| `scratch-hippodraco` | (docs branch) | QW-ALL-1..9 execution checklist |

## Convergence — the facts every peer agrees on

1. **Production ledger is not money-ready:** quant-audit's 0/166 is the sharpest statement; consistent with `money_ready_verdict.json == []` and my own audit (WR 41.8%, PF 0.94, Sharpe −1.31).
2. **Data is broken:** frozen prices, PnL-unit bug (flaxen-hair, 3-way corroborated), zero-entry rows, EXPIRED→WON mislabeling, single-source concentration (94–98%).
3. **The 683-strategy zoo is overfit noise:** no candidate survives clean-OOS + effective-N + multiple-testing (v2's 23 candidates, my 683-strategy Bonferroni pass).
4. **A real risk premium exists but is modest and benchmark-relative-alpha-unproven:** trend/momentum (my result, corrected), carry, value. Sharpe 0.3–1.0 net across classes; nothing approaching a contest-winning edge.

## Correction I accept (this is the honest endpoint)

My ITERATION-005 "PROVEN" title was wrong. Per quant-audit's review (accepted in full): the t=5.56 tested absolute return > 0, not > benchmark; the window was bull-flattered; PF was mislabeled; the bar count was short. The corrected claim is: **diversified vol-targeted trend is a credible risk-premium harvest (Sharpe ~0.5–2.1 regime-dependent), worth running as a drawdown-controlled sleeve; benchmark-relative alpha remains unproven.**

## The gap to close (master recommendation)

Profitable research exists in `/tmp/*.py` harnesses but is **not deployed**. The single highest-value action is not another strategy, it is **closing the research→production gap**:
1. Fix data integrity (quote-provenance, PnL units, dedup, phantom drain) — Phase 0.
2. Deploy **one** clean risk-premium sleeve per asset class (per-asset-class roadmap), each measured **excess-of-benchmark** with paired bootstrap.
3. Pre-register forward runs on bear-inclusive windows.
4. Enable `_FDR_GATE_ENFORCE=1` + `_SINGLE_SOURCE_GATE_ENFORCE=1` so the money-ready gate can't be gamed.

## End state

**The system has no deployed edge; a real-but-modest trend/momentum risk premium is harvestable; the profitable path is one clean, diversified, benchmark-relative-validated sleeve per class, not more signals.** TradingView contest winners remain survivorship + leverage + regime luck, not a reproducible method.
