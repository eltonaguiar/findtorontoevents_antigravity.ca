# final_v4 — finpredict summary (2026-11-14T21:50Z)

Final review pass (round 4). Reviewed: the consolidated `final_v3/` master (which **shipped code**, not just prose), all peer `final_v3/` folders, every file modified today (committed + uncommitted), and the remote. This summary is the convergence point.

## The one-line answer

The prediction system is **not money-ready** (0/166 cells, 4/170 ledgers pass at 95% vs 8.5 expected by chance — i.e. *worse than random*). No peer has proven a raw-alpha edge. What exists is: (a) **EQUITY** as the only class with a measured positive margin (needs a benchmark-vs-SPY test), (b) **CRYPTO** as the only class with a diagnosed, fixable defect hiding a possible edge, and (c) **index/mutual funds as the passive market-beta baseline** — not a prediction edge, but the "least money, least maintenance" always-on return the user asked for.

## Common themes (converged across 10 peers + the coordinator's shipped-fix pass)

**Top bugs (from the consolidated `final_v3/00_common_themes/BUGS.md` B1–B14, cross-checked against my own audit):**
- **B1** A refuted strategy (VWAP mean-reversion) is still labelled "VALIDATED" in a live package — the highest-consequence bug (actively misdirects a reader). DSR=1.0 + PBO=0.489 are internally inconsistent.
- **B2** Same class, 3 counts: ETF win rate spans **2.22% → 68.42%**, PF 0.022 → 1.788 (85× spread). No artifact states its filter chain, so a bug and a different cohort are indistinguishable.
- **B3** Crypto stop-fills 1.54× planned risk = **98.8% of the class loss**, 94% from one system — **fixed today** (`audit_trail/stop_fill.py`).
- **B4** 40–56% of non-crypto "SL_HIT" rows **never touched the stop** — unexplained (deep-investigation).
- **B5** Exit taxonomy lives in `exit_reason`; `resolution_method` is null on all 3,500 rows.
- **B8** 170 ledgers, only **4 pass** at 95% vs **8.5 expected by chance** — the system is anti-profitable on average.
- Plus my own: PnL-unit mix off 100×; EXPIRED→WON mislabeling; frozen prices as 0%; `scanner.py:2942` `KeyError:'LONG'`; `summary_picks` WR>100%; Python 3.14 masquerade (197 workflows); `dashboard_enhancements.js` parse-broken since 2026-10-04.

**Deep-investigation queue:** 11 FOREX phantom provenance; PnL-unit writer attribution (needs a `pnl_source` column); whether any edge survives a **bear-inclusive** window + benchmark-relative test (0/40 trials pass the null so far).

## What shipped (not just prose)

The consolidated final_v3 pass **implemented** fixes: `audit_trail/stop_fill.py` (20 tests), gap-aware resolver fill, `tools/per_class_cost_gate.py` (18 tests, per-class 3× cost gate), `after_cost_net_per_trade` population, intrabar replay harness (30 crypto + 25 equity + 25 ETF), and a COT contrarian backtest that **failed 4/4** (honestly reported). My own `fix/audit-p0-truth` (scanner KeyError guard, WR≤100%, no None→0.0) remains pushed.

## Focus decision (matches the consolidated screen)

A class qualifies only if it (1) clears 3× round-trip cost, (2) has a diagnosed loss mechanism, (3) n≥100:

| Class | 3× cost | Loss mech known | n | Verdict |
|---|---|---|---|---|
| **EQUITY** | ✅ 3.23× | ✅ no defect (stops 0.91×) | 738 | **SLOT 1** — benchmark vs SPY |
| **CRYPTO** | ❌ 0.58× | ✅ late fills (fixed today) | 1,966 | **SLOT 2** — conditional on forward fill evidence |
| ETF | ❌ 0.40× | ✅ cost≥edge (267%) | 567 | no |
| FOREX | ❌ −1.94× | ✅ contaminated | 187 | no |
| BOND | ❌ −4.41× | ⚠️ broken exit labels | 35 | no |
| COMMODITY | ❌ thin | ✅ 422% cost | 7 | no |
| MUTUAL FUND | n/a | n/a | 0 | not a prediction edge |

**Mutual-fund / index subset (least $ in, lowest fee, least capital):** `VTI` (0.03% ER, $0 min, fractional $1) + `BND` + `SGOV`/`VGSH` core (70/15/15). This is **equity beta + T-bill carry** (~7–9% + ~4–5% nominal), the baseline every "edge" failed to beat — treat as the control arm, never a pick emitter.

## TradingView contest winners (the user's original premise, now with real data)

finpredict-v4's uncommitted research pulled the official leaderboards: `BenBernanke1` +5,220.72% (94% profitable, **59,187 contestants**), `yxiao8911` +1,673.74% (**103,158 contestants**), and `KingBob09` won Commodities with only **43% profitable trades**. With 100k entrants, a +5,000% winner is **survivorship + leverage + regime luck**, and the 43%-profitable winner proves winners aren't even consistently right — they're just the extreme tail. Not a reproducible method.

## SubQ clarification

"SubQ" is not a real tool on this host (not on PATH, no repo reference). It was interpreted as **sub-question/sub-agent coverage**: I dispatched 3 parallel subagents (common-themes / asset-class ranking / mutual-fund subset), and the coordinator's final_v3 did the same. Recorded, not substituted.

## End state

The profitable path is **one clean, benchmark-relative-validated sleeve per class** (EQUITY first, CRYPTO conditional) plus the passive index baseline — not the 683-strategy zoo. Data-integrity P0 fixes must land first: 0/166 money-ready is a data symptom, not a strategy symptom.
