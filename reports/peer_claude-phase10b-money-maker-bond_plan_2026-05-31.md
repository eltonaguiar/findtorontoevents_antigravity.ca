# /money-maker-readyv2 — BOND (plan)

**Author:** peer_claude (Opus 4.7), Phase 10b
**Timestamp:** 2026-05-31 ~06:30Z
**Source data:** `ejaguiar1_stocks.trading_picks WHERE category='bond'` (n_total=164)
**Inputs:** Phase 2 audit, Phase 3 MC results (no BOND candidate flagged), Phase 4 resolver bug bundle, Phase 5 RETIRE list.

## Plan of attack

1. Pull raw `trading_picks` rows for `category='bond'` and break out by `status`, `source_system`, `symbol`.
2. Identify resolver artefacts (exit_price == entry_price → forged pnl=0). Distinguish "real edge" from "no edge" only after fixing.
3. Cross-reference Phase 3 MC watchlist (no BOND candidate present → BOND is purely INSUFF-N + resolver-blocked).
4. Recommend the smallest set of changes that would actually let BOND reach n>=100 clean closures.

## Per-class facts captured upstream

- `money_ready_verdict.json` (2026-05-24) lists BOND as INSUFF-N: PF=0, WR=0%, n=8.
- The 8-n verdict corresponds to the `bond_scanner` LOSS cluster (-0.65% avg, 0 wins). After removing resolver artefacts (TIME_EXIT with exit==entry), the real closed-n is ~14 (8 bond_scanner LOST + 3 multi_asset_copytrader TP_HIT + 3 multi_asset_copytrader LOST/other).

## Method

- "Real closure" = `status != OPEN/ACTIVE AND NOT (exit_price = entry_price)`.
- For each `source_system` x `symbol`, compute n_real, wins, gross_win, gross_loss, PF.
- For resolver artefacts, point at the exact code path that writes a forged exit_price.
- Recommended actions are concrete files / line ranges / config blocks.

## Deliverable

`reports/peer_claude-phase10b-money-maker-bond_result_2026-05-31.md` (action plan).
