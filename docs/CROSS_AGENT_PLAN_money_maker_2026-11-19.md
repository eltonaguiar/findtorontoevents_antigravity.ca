<!-- Published verbatim by kilo 2026-11-19T19:10Z from copilot session d9b004db-79cc-4f99-b5f6-5418f84ef36f. Author: copilot-cli-moneyresearch. Review: docs/FEEDBACK_ON_CROSS_AGENT_PLAN_2026-11-19.md -->

# Plan — Money-maker per asset class: research, cross-check, $2k pick, and a LIVE short-term sim loop

## 0. COMS status (answered)

- **Updated & checked.** `AGENT_FOLDERFRAMEWORK` local == `origin/main` @ `269f121` (includes the `6f30d86` Windows `unregister` fix announced on the bus).
- 1 retained `mentions/all` message read: Windows re-review — all verbs pass; remaining opens are Windows-roster raw-dump + B6 warn-only. No action required from this side.
- Registered seat `copilot-cli-moneyresearch` on `inbox/gx10-c9b9/findtorontoevents_antigravity-ca/copilot-cli-moneyresearch`.

## 1. Ground truth from the three audit surfaces (fetched live 2026-11-19)

### /audit (money_ready_verdict.json, generated 18:47Z)
| Class | Verdict | n_res | WR | PF | Expectancy |
|---|---|---|---|---|---|
| CRYPTO | NOT_READY | 3726 | 41.5% | 0.26 | −0.057 |
| FOREX | NOT_READY | 634 | 34.9% | 0.26 | −0.020 |
| EQUITY | NOT_READY | 257 | 32.2% | 0.60 | +0.008 |
| ETF | INSUFFICIENT_DATA | 53 | **58.6%** | **1.82** | −0.021 |
| COMMODITY | WATCH | 234 | 28.6% | 0.36 | −0.015 |
| FUTURES | INSUFFICIENT_DATA | 60 | 35.3% | 1.27 | +0.004 |
| BOND/MEME/PENNY/CHEAP/MF | INSUFFICIENT_DATA | ≤10 | — | — | — |

### /audit3 (kill tribunal, 18:32Z)
- **0 PROVEN, 0 CANDIDATE of 359 cells.** CRYPTO = **KILL** (n=6740, PF 0.84), COMMODITY = **KILL**; EQUITY/ETF/FOREX/BOND = WEAK.
- **Selection alpha is NEGATIVE: −0.276%/trade, 95% CI [−0.51, −0.04] (excludes zero, n=3192)** — our picks lose to direction-adjusted buy-and-hold on the same windows. This is the single most important number on all three pages: the system currently has *negative* selection skill overall.
- 7 forward pods registered 2026-11-19, **all n_forward=0** (EQUITY-BREAKOUT, CRYPTO-VWAP-REVERSION, CRYPTO-BOLLINGER-MR, FABER-TAA, FOREX-USDJPY-MOMENTUM, COMMODITY-ROLL-YIELD, CRYPTO-POSITION). Forward clock just started; nothing can promote yet.

### /audit2 (candidate library)
- Doctrine: remaining public edges = risk premia + microstructure/flow; expression (symmetric vol-scaled exits) matters more than signal. Cost gate: net PnL ≥ 3× measured slippage (ETF slippage ≈234% of per-trade PnL at monthly cadence; CRYPTO ≈37%).

## 2. Cross-check of others' claims (requested)

| Claim | Verdict | Evidence |
|---|---|---|
| `/audit` sleeve “Multi-Timeframe Trend Alignment” 87% WR / PF 11.8 (n=394), “AuditEnsemble_LONG” PF 10.1, “Price Acceleration Detector” PF 5.9 | **UNCORROBORATED** | None of these names exist among audit3's 277 strategy cells. Source is `resolver_grade` top_sleeves in money_ready_verdict; audit3 ingests closed DB rows directly. Either a naming/ingestion gap or sleeve-level survivorship. Must reconcile before anyone sizes on them. |
| FOREX sleeve `non_crypto_consensus` PF 9.68 / WR 52.9% (n=223) vs class PF 0.26 | **SUSPECT** | Same pattern — sleeve PF 37× the class PF from the same rows; classic grade-source divergence. |
| “78.9% CRYPTO Smart-Picks” (pick_funnel) | **Already DISPUTED on-page** | audit3 says CRYPTO = KILL, raw 40.4% WR / PF 0.84 on n=6740. Tribunal corroborates the dispute. |
| ETF TAA / dual momentum edge | **RETRACTED 2026-11-20** (was CORROBORATED) | **See `reports/money_maker_per_asset_class_2026-11-19.md` §0.** "Sharpe 0.88 vs SPY 0.74, MaxDD −19% vs −51%" reproduces **only at same-close execution**. Honest 1-day lag: Sharpe 0.82 vs SPY 0.69, MaxDD −20.9% vs −52.9%, **CAGR 8.94% vs SPY 10.79%**. Pre-registered 576-cell grid: **0/576** clear Sharpe ≥0.88 *and* MaxDD ≥−19% at lag=1/≥5bps; all 85 cells that do clear both bars sit in 2018–2026 (no 2008) → **window artefact, not look-ahead**. Survivor: **drawdown control** (−50.78% → −31.61%, 38% cut, ~0.54%/yr CAGR give-up) — smart-beta risk control, not alpha; forward n=0. Evidence: `reports/TAA_SETTLE_2026-11-19.md`. |
| Best WEAK cells worth forward-testing | Plausible but unproven | ETF `rs-breakout-scout` (n=80, WR 56%, net +0.58%/trade, q=0.167), ETF `adx-trend-scout` (n=43, q=0.167), EQUITY `donchian-stock-breakout` (n=45, net +1.89%), CRYPTO `btc-4h-rsi-macd-scout` (n=35, net +2.0%, dsr 0.12). All fail 2×-cost stress; none promotable. |

## 3. What works per asset class — synthesis (local evidence + external research agent)

- **ETF**: tactical asset allocation / dual momentum (validated in-repo across 20y incl. 2008/2020/2022; the most-replicated practitioner edge in literature). Monthly cadence, tiny cost. The ONE thing we've proven. Blocker: pilot stuck OPEN → forward n=0.
- **CRYPTO**: our directional picks are KILL. Literature-credible retail edges are funding-rate carry and (marginally) BTC trend at 4h+; our `btc-4h-rsi-macd-scout` is the only crypto cell with positive net expectancy + the highest DSR (0.12). 24/7, no PDT, granular sizing → the only *practical* class for a $2k short-term LIVE sim.
- **EQUITY**: breakout family (donchian, Breakout Momentum) shows the best WEAK cluster. **Correction from external research: the PDT $25k rule was repealed** — FINRA Notice 26-10 (effective 2026-06-04, broker phase-in until 2027-10-20) replaces it with exposure-proportional intraday margin; confirm per-broker implementation. So equity day trading at $2k is now *legal* — but the Taiwan/Brazil evidence (97% of persistent day traders lose; <3% predictably profitable) says it's still a losing game.
- **FOREX**: class is net-negative at every gate; USDJPY concentration. Observe-only pod is correct; no new spend.
- **COMMODITY**: KILL + 57% concentration in one strategy. Roll-yield pod is observe-only; correct.
- **FUTURES/BOND**: insufficient n; one overnight MES position exceeds $2k margin at most brokers; the Brazil 97%-loss study is literally futures day trading. BOND trend timing earns a few %/yr at best vs T-bills ~3.4%.
- **PREDICTION MARKETS**: only structural retail edge is maker-side (Kalshi maker fee 1.75% vs taker ~7%; WSJ: 67-70% of Polymarket users lose; going maker cuts P(loss) by 9.3pp). Relevant to our pm_consensus/Kalshi modules: any live expression must be maker-only.

### External research agent highlights (full report in session files + to be committed in reports/)
- **Day-trading base rates**: Brazil futures (Chague et al.): 97% of 300-day persisters lose; Taiwan (Barber/Odean et al.): −23.9bp/day net, <3% predictably profitable. These are the priors our live sim must beat.
- **Publication decay** (McLean & Pontiff): haircut any backtested edge 26–58% post-publication.
- **Costs kill** (Novy-Marx & Velikov): >~50% monthly turnover rarely survives costs → monthly-cadence ETF TAA is structurally privileged; crypto taker round-trips at US retail tiers run 0.8–1.8% → sim must assume maker fills or low-fee venue and model costs explicitly.
- **Crypto funding carry has compressed** to ~2.7–6%/yr pre-fee (2026) → ~$0–80/yr on $2k; not worth building for at this size.
- **Forward-test epistemology**: a few months of live data cannot confirm a modest edge (SR 1.0 needs ~9 years for t=3); forward tests verify *execution honesty* (slippage, fills, rule drift), not alpha — which is exactly what the audit3 forward gate is for.
- **Prop-firm guardrails to borrow for the sim**: max trailing drawdown, daily loss limit, consistency rule (no single day >40% of profit).

## 4. The $2,000 question

**Recommendation: ETF (via tactical dual-momentum rotation) for real money; CRYPTO for the live *paper* day-trading sim. Do not put the $2k into short-term trading in any class today.**

Why:
1. ETF TAA is the only edge with 20-year robust evidence in-repo AND the deepest external replication (Faber/Antonacci). At $2k it's implementable with 4-5 commission-free ETFs, monthly rebalance, ~2-5bp cost. Expected: market-like return, roughly half the drawdown. It is the only allocation a hedge-fund reviewer would not laugh at.
2. Every short-term class we measure has negative selection alpha (−0.28%/trade). Putting $2k into that live = paying ~$5.5/trade in expected loss, on top of base rates where 97% of persistent day traders lose (Brazil study).
3. CRYPTO is still the right *sandbox* for the short-term sim (24/7, fine-grained sizing, our richest data + resolver infra, and the only class with documented 1–4wk momentum at this horizon) — but at $0 real until a pod clears the forward gate (n≥100, net PF CI-LB > 1.0). External research ranks the same way: ETF (slow) > crypto spot momentum (experimental, maker orders only) > prediction-market maker > everything else.
4. Honest dollar framing: even a good net edge on $2k ≈ $100–200/yr. The value of the sim program is building a *proven process* that justifies larger capital later, not income at $2k.

## 5. LIVE short-term/day-trading simulation design (the build)

Reuse the existing pilot harness pattern (`verified_strategies/paper_pilot/*_pilot.py` + state JSON + paper_log JSONL + GH Actions cron) — don't invent a new framework.

**A. Crypto intraday live-sim runner** (`verified_strategies/paper_pilot/crypto_intraday_sim.py`)
- Strategies (each a parallel slot, pre-registered per M-107): existing pods CRYPTO-VWAP-REVERSION, CRYPTO-BOLLINGER-MR + promote `btc-4h-rsi-macd-scout` into a pod (best DSR cell).
- Cadence: GH Actions cron every 30min (new workflow `crypto-intraday-sim.yml`); Binance 4-mirror → CoinGecko → KuCoin → CryptoCompare failover per repo rule.
- Each entry writes a row with TP/SL/time-exit, intrabar first-touch resolution, net-of-cost at 2× measured slippage (0.2%); closed rows appended to `reports/forward_observations.jsonl` with pod/hypothesis id so the audit3 forward gate + /audit2 forward clock consume them automatically — zero new dashboard plumbing.
- Monitoring/trial-error loop encoded in the runner config: judge nothing before n≥20; auto-HALT a slot at harm (net CI upper < 0 at n≥30); mutate per docs/MUTATION_THREE_AXIS_PROTOCOL.md; max 3 concurrent slots; equal notional $500 paper per slot.
- Prop-firm-style guardrails per slot (from research): trailing max-DD 10% → slot HALT; daily loss limit 3% → pause 24h; consistency flag if one day >40% of cumulative P&L (marks luck, blocks promotion).
- Cost model: maker-fee assumption flagged explicitly per venue tier; every row stores gross AND net at 1× and 2× measured slippage. Forward test verifies *execution honesty*, not alpha — promotion stays gated by audit3.

**B. Unstick the ETF TAA forward clock**
- Fix `etf_dual_momentum_pilot.py` close logic (positions stuck OPEN, forward n=0 since June) and mirror a `faber_taa` pilot; wire closes into forward_observations.jsonl under POD-FABER-TAA.

**C. Reconcile the sleeve-claim gap (cross-check action)**
- Trace why `Multi-Timeframe Trend Alignment` / `AuditEnsemble` / `Price Acceleration Detector` top_sleeves never appear as audit3 cells (name mapping vs. source filtering in `alpha_engine/audit3_tribunal.py` vs `money_ready_verdict.py`). Outcome: either ingest them (so the tribunal scores them) or flag the sleeves as UNVERIFIED on /audit.

**D. Documentation + comms**
- `reports/money_maker_per_asset_class_2026-11-19.md` (this research, incl. external agent citations) + `updates/` entry card (before the AUTO-INJECTED marker) + FTP deploy of updates + durable COMS broadcast.
- `updates/*.md` fix-doc per mandatory rule.

## Todos
1. research-doc — write reports/money_maker_per_asset_class_2026-11-19.md (merge external agent findings)
2. sleeve-reconcile — trace + fix/flag the /audit top_sleeves vs audit3 cells gap
3. etf-pilot-unstick — fix dual-momentum pilot close logic; forward rows flowing
4. crypto-sim-runner — build crypto_intraday_sim.py + 3 slots + cost model + forward_observations writer
5. crypto-sim-workflow — .github/workflows/crypto-intraday-sim.yml (30min cron) + smoke test
6. pod-register-btc4h — pre-register btc-4h-rsi-macd pod in hypothesis_registry.json
7. updates-entry — updates/index.html card + FTP deploy + verify curl
8. coms-broadcast — retained mentions/all summary of findings + sim launch
9. memo-2k — $2,000 allocation memo section in the research doc

## Notes / considerations
- No real money moves; everything is paper/forward until the audit3 forward gate promotes (n≥100, PF CI-LB>1.0, 100% intrabar honesty).
- Never run dashboard generators locally; py_compile only. New pipeline files get added to the AGENTS.md path registry table in the same PR.
- The GH-cron sim is "live" in the forward-test sense (real-time prices, pre-registered, append-only log) — the strongest honesty guarantee our infra supports.
