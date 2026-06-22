# Winner-Hunt Honest Scorecard (2026-06-22)

User ask: "get us to winners." This is the honest result of a systematic hunt with a
falsification gate (regime / P&L-concentration / session / time-split), not a pick list.

## Method
- `tools/mine_entry_condition_cells.py` (#641): enumerate all (class × dir × RSI-band × session)
  cells over the honest intrabar cohort + BH-FDR. Surfaces candidates fast.
- Every candidate then gated through: time-split (IS/OOS), per-month regime vs BTC direction,
  top-3-symbol net-P&L concentration (>60% = fail), session clustering. Plus a consensus-3 swarm.

## Candidate 1 — crypto_short_rsi5070 (CRYPTO SHORT, RSI50-70): **REFUTED** (#645)
- Headline looked great: net PF 1.52 (n=45), last-30d PF 2.44.
- REGIME: won only in BTC-down months; **lost 0/7 in the one up-month (Mar)**. Directional, not RSI.
- CONCENTRATION: top-3 = 82% of net P&L. SESSION: US 82% WR vs EU 17%.
- Verdict: regime+concentration artifact. Relabeled `..._REGIMEWATCH` (monitor only).

## Candidate 2 — crypto_rsi5070_us (CRYPTO LONG, RSI50-70, US): **MARGINAL, fat-tail-fragile**
- REGIME: **PASSES** — wins in up-months (Mar netPF 1.87, Apr 1.09) AND a down-month (May 1.14);
  only Jun (BTC −12.7%) lost. Not directional regime exposure. Better than the SHORT.
- COUNT diversification: PASSES — 63 distinct symbols over 99 picks (no single symbol dominates count).
- **P&L CONCENTRATION: FAILS** — top-3 symbols (ONDO/PIXEL/JTO, 8 of 99 picks) = +38.6 of the +19.0
  total net. **Ex-top-3: n=91, WR 36.3%, netPF 0.74, −19.6% pnl.** Median single-pick = −1.0%.
- netPF is window-sensitive: 1.02 on this 4000-row slice vs 1.28 on the live tracker (n=116).
- Verdict: a **low-WR (40%), fat-tail-dependent** setup. Positive expectancy rides on catching
  occasional breakouts. At n≈100 we cannot distinguish a real breakout-catching edge from 8 lucky
  picks — which is precisely why the **n≥150 + net-PF CI-LB>1.15** forward gate exists. NOT sizable now.

## Honest bottom line
**We do not currently have a robust, broad, money-ready winner.** We have one marginal,
fat-tail-dependent LONG setup (rsi5070-LONG) that survives regime + IS/OOS but whose edge is
concentrated in ~8 picks, and a refuted SHORT mirage. This is consistent with the project's
standing reality (0/9 classes pass T2; the bottleneck is measurement + forward-n + edge breadth,
not a hidden strategy).

## What actually moves us toward winners (no false positives)
1. **Accrue forward n on rsi5070-LONG to its gate** — the ONLY way to learn if the fat-tail wins
   repeat (skill) or were luck. Pipeline is durable + self-sustaining (this session's #623–#640).
2. **Keep mining with the falsification gate** — `mine_entry_condition_cells.py` surfaces candidates
   cheaply; the gate (regime/concentration/session/time-split/swarm) kills the artifacts. Expect
   most small-n cells to fail. A survivor that passes ALL axes at n≥80 is a genuine new lead.
3. **Prefer higher-WR, lower-concentration conditions** — a 55%-WR setup whose edge survives
   ex-top-3 removal is worth far more than a 40%-WR fat-tail setup at the same headline PF.
4. **Do not size on headline PF.** Both candidates had attractive headline PF; both were fragile
   underneath. The ex-top-3 / regime tests are now part of the standard gate.
