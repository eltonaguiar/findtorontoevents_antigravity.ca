# Edition Review — 2026-07 (June112026 → July112026)

Per Section E of the money-ready skill, run on the 11th. This review supersedes `money-maker-ready-June112026edition` with `money-maker-ready-July112026edition`.

## 1. Score the month (per the June edition's bet)
The June edition's structural bet: "converge toward 2-3 profitable asset classes even from 0/9" by mining the crypto `at_signal_outcomes` ledger. **Outcome: the bet failed, and we now know exactly why.**
- Exhaustive 2026-07 sweep (all 9 DBs, all asset classes, all cross-cutting sources, peer-AI + subagents, the 3 controls): **NO net-of-cost systematic alpha anywhere.** Every candidate (luxalgo SHORT, rsi5070, mega_mutation, funding, copytraders, prediction-markets, memecoin, 32.7M backtests, equity fundamentals) dissolved.
- Root cause is NOT missing strategies: (a) `entry_price` P0 — ~29% clean, +1.3% biased, `intrabar_pnl_pct` rides it → manufactured phantom SHORT edges; (b) ~90% of positions never resolve; (c) net-of-cost retail alpha on free data is ~impossible (inefficiencies < cost). CI-LB never cleared; checkpoints (rsi5070 n≥150, luxalgo n≥80) reached but REFUTED under the 3 controls.

## 2. What circled (add to do-not-relitigate)
- **The crypto ledger directional-edge hunt is closed** until the ledger is re-resolved from bar-aligned NEXT-bar entries. Do NOT re-run replay-variant batches on the contaminated ledger.
- **The OPEN backlog resolution is a DEAD END** — the 3.19M resolvable OPEN crypto rows are systematic losers (net PF 0.60; they're OPEN because price never hit TP).
- **Fabricated hardcoded WRs** (copytrader 81.3%, ML 87-94%, reviver 0.941) — a recurring anti-pattern; all removed. Any hardcoded WR must be live-verified.
- **The gap-fade + funding carry** are real gross effects but sub-retail-cost — do-not-relitigate as tradeable for a small operator.

## 3. What the next edition changes (ONE structural change max)
**The primary money-making track moves from crypto-ledger directional-edge-mining (dead/broken) to ETF TACTICAL ASSET ALLOCATION (the one validated find).** ACT's default focus is now the TAA/ETF track + data-integrity fixes; crypto replay-variant batches are gated behind ledger re-resolution. Rationale: TAA is the only thing that robustly beats passive risk-adjusted (Sharpe 0.88-0.89, MaxDD −16/−19% vs SPY −51%, 2007-2026 incl the 2008 GFC, both-halves + all-thirds+), it's honest (smart-beta, not alpha), deployable on free ETF data, and has a live measurable POC.

## 4. Deliverables this edition
- New skill `money-maker-ready-July112026edition/SKILL.md` (supersedes June; carries the mandatory all-asset breadth block, the P0 gate + 3 controls, and NEW the no-fabricated-WR rule).
- TAA stack: `tools/tactical_rotation_tracker.py` (6m default), `tools/tactical_blend_tracker.py` (v2 POC), `reports/TACTICAL_ROTATION_EDGE_2026-07-04.md`.
- Live POC: `ejaguiar1_stocks.poc_picks` + `poc-picks-checkpoint.yml` (auto-resolves 2026-07-18) + `tools/resolve_poc_picks.py`.
- Data-integrity fixes: `daily_prices` un-frozen (`tools/refresh_daily_prices_yf.py`, +11,791 rows); fabricated WRs removed (elite_scorer, ml_strategy_reviver); ML audit (`reports/ML_AUDIT_2026-07-04.md`).

## 5. External-review task spec (Section E step 5)
This edition made a structural change (TAA pivot), so the operator should commission an external review of: (a) is the TAA blend's 2005-2026 backtest genuinely look-ahead-free + not over-fit (independent re-implementation)? (b) is "smart-beta not alpha" the right framing / sizing? (c) forward-track discipline — 6-12mo vs SPY before sizing. Verdict to fold into the August edition.

## Open items carried into July
Finish ML remediation (gate ml_crypto_predictor emission, wire/retire ml_gatekeeper, restart ml_health); cap blend concentration (~35%/ETF); validate more documented TAA variants (DAA/PAA/GTAA); measure poc_picks 2026-07-18.
