# 06 — SubQ Decision Support and Fact-Check

## SubQ usage (this session)
- **Goal:** leverage SubQ for decision support as requested.
- **Credentials/endpoint:** `dbpasses.txt` contains SubQ token entries (lines ~86,89; labels only — **never printed or committed**). Known API pattern in-repo: `https://api.subq.ai/v1/systemone` (e.g. `2026-11-15_1227AM_profitability/buffy/07_subq/subq_run_20261115T002900Z.json`).
- **Verifiable run status:** prior attempt in-repo returned **HTTP 422 validation_error** (schema mismatch on `proof_strength` score definition), so **no completed SubQ decision payload** was available as evidence. No other verifiable live SubQ artifact was produced in this worktree session.
- **Action taken:** provided **SubQ-style structured decision support** (questions/matrix framing, ranking, and benchmark-aware criteria) and **fact-checked** all material claims against repo evidence and grounded principles below. This is explicitly labeled — not a substitute for a successful, logged SubQ run.

## SubQ-style decision matrix (applied, fact-checked)
| Question | Assessment | Grounding |
|---|---|---|
| Is any class reliably profitable now? | **No** | `money_ready_verdict.json` (CRYPTO PF 0.9196/expectancy < 0; EQUITY PF 0.9392 & gates failed), peer `final_v4` 0/23 survived (reported) |
| Should real capital deploy to prediction system today? | **No** | Sizing/gates not passed; integrity/0%/blank/fill issues unresolved |
| Highest probability lower-risk real-money path? | **Low-cost diversified ETF/MF passive allocation (beta/ballast)**, disciplined rebalance, risk limits | Beta/cost discipline; must be benchmark-relative, net-of-fee |
| Best research candidates (if repaired)? | **EQUITY vs SPY total return** (pre-registered) and **narrow crypto sleeves** (e.g. TSMOM/VWAP-core) only after fixes | Evidence mixed/unproven; PBO/forward hurdles remain |
| Can MFs be a daily pick/intrabar-stop class? | **No (as prediction class)**; **yes as NAV-based allocation sleeve** | Next-NAV, fee/constraint structure, benchmark overlay reality |
| Does ETF evidence prove “no edge”? | **Not by itself**; it shows insufficient/contaminated proof of edge today | Thin-n/contradictory snapshots; needs clean net forward tests |
| Daytrading/scalping viable retail after costs? | **Unproven / generally unlikely here** | Costs/slippage/latency/multiple-testing; repo fill/expiry issues |
| Highest-value next action? | **Fix measurement/QA & 0%/blank validation**, then pre-registered benchmark-relative forward tests | Integrity before alpha |
| Proof strength (0–9) for money-readiness | **~0–2 (none-to-weak/contradicted)** | No net, benchmark-relative, OOS, DSR/PBO-clean, forward-confirmed edge |

## Fact-check of key claims and principles

| Claim | Verdict | Rationale (grounded) |
|---|---|---|
| Mutual funds “would be winners given enough time” | **Plausible for low-cost diversified index funds as beta; not guaranteed; not system alpha** | Long-horizon equity/bond premia exist but with drawdowns/sequence risk; active outperformance after fees is uncommon (SPIVA-like prior). Must be net-of-fee vs benchmark. |
| Beating 0% is enough | **False as a success criterion** | Must beat appropriate hurdle (SPY/T-bill/blended benchmark) on **net, risk-adjusted** basis. |
| Buy-and-hold low-cost index is hard to beat after costs | **Generally supported** for many active approaches | Cost/turnover/tax drag and selection/overfit challenges; evaluate per case. |
| TSMOM/trend-following is “proven” | **Documented across assets historically, not guaranteed** | Works in trends, suffers in chop/crashes; requires diversification, costs, risk controls, out-of-sample/forward validation. |
| Connors RSI(2) / famous rules are “winners” | **Context-dependent, decay/overfit-prone** | Can work in specific liquid regimes/universes; must be revalidated net & forward. |
| Contest winners / top backtests = deployable edge | **False without validation** | Selection bias, short windows, multiple testing, unrealized frictions. |
| Copy trading (incl. Polymarket/Kalshi wallets) transfers edge | **Often false** | Latency/adverse selection, missing hedges/book context, fees/limits, resolution/model risk, non-stationarity. |
| 0% PnL means “no trade impact” | **Not necessarily** | Can be stale/unquoted mark, coercion, or true flat — requires per-pick market-data validation. |
| More strategies => more profit | **False by default** | Increases multiple-testing/complexity/ops risk unless governed by strict gates.

## Limits & compliance notes
- Did **not** expose or transmit credentials; did **not** fabricate SubQ results.
- External “famous/industry” references are stated at principle level; for any capital decision, re-verify against primary sources/data and run the repo’s pre-registered gates.
