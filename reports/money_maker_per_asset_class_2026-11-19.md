# Money-maker per asset class — research, cross-check & $2,000 verdict (2026-11-19)

**Author:** copilot-cli-moneyresearch session (plan: `ACTIONPLAN_AUDITPAGE/2026-11-19T1906Z_copilot-moneyresearch/PLAN.md`).
**Scope:** goal #1. Cross-checks the three audit surfaces against each other and against external evidence, answers "which asset class for $2,000", and ships the live paper-sim program that makes the answer testable.
**Not investment advice. Nothing here is money-ready.**

---

## 1. Ground truth, fetched live 2026-11-19

### /audit — `money_ready_verdict.json` (18:47Z)

| Class | Verdict | n_res | WR | PF | Expectancy/trade |
|---|---|---|---|---|---|
| CRYPTO | NOT_READY | 3,726 | 41.5% | 0.26 | −0.057 |
| FOREX | NOT_READY | 634 | 34.9% | 0.26 | −0.020 |
| EQUITY | NOT_READY | 257 | 32.2% | 0.60 | +0.008 |
| ETF | INSUFFICIENT_DATA | 53 | **58.6%** | **1.82** | −0.021 |
| COMMODITY | WATCH | 234 | 28.6% | 0.36 | −0.015 |
| FUTURES | INSUFFICIENT_DATA | 60 | 35.3% | 1.27 | +0.004 |
| BOND / MEME / PENNY / CHEAP / MF | INSUFFICIENT_DATA | ≤10 each | — | — | — |

### /audit3 — kill tribunal ledger (18:32Z)

- **0 PROVEN, 0 CANDIDATE out of 359 cells.** CRYPTO = **KILL** (n=6,740, PF 0.84), COMMODITY = **KILL**; EQUITY / ETF / FOREX / BOND = WEAK; FUTURES insufficient-n.
- **Selection alpha is NEGATIVE: −0.276%/trade, 95% CI [−0.51, −0.04], n=3,192** — our picks underperform direction-adjusted buy-and-hold over the same windows. This is the most important number on all three pages: the pick layer currently *subtracts* value versus just holding.
- 7 forward pods registered 2026-11-19, all `n_forward = 0` — the forward clock has only just started.

### /audit2 — candidate & methodology library

Doctrine: remaining public edges are risk premia + microstructure/flow; the *expression* (symmetric, vol-scaled, time-based exits) changes the statistics more than the signal. Cost gate: net PnL ≥ 3× measured slippage (ETF slippage ≈234% of per-trade PnL at monthly cadence; CRYPTO ≈37%).

---

## 2. Cross-check of claims (requested: "cross-check others' claims")

| Claim | Verdict | Evidence |
|---|---|---|
| `/audit` sleeve **"Multi-Timeframe Trend Alignment"** 87% WR / PF 11.8 (n=394); **"AuditEnsemble_LONG"** PF 10.1; **"Price Acceleration Detector"** PF 5.9 | **UNCORROBORATED** | None of these names exist among audit3's 277 scored strategies, and none appear in the 3,500-row dashboard payload (`picks.recent_closed`) audit3 ingests. They live only in MySQL `at_pick_outcomes` and are *selected post-hoc* by `_top_sleeves_from_outcomes` (hard filter WR≥50 & PF≥1.5 across ~277+ strategies, no multiplicity correction) — survivorship display, not scored edge. **Fix shipped:** sleeves are now cross-marked with the tribunal verdict (`audit3_verdict` / `tribunal_corroborated`) in `money_ready_verdict.py`, and `/audit` renders an "UNVERIFIED (not in audit3)" badge. |
| FOREX sleeve `non_crypto_consensus` PF 9.68 / WR 52.9% (n=223) vs class PF 0.26 | **SUSPECT** | Same mechanism: a sleeve PF ~37× its own class PF, from a resolver-grade query the tribunal never scored. Now carries the same badge. |
| "78.9% CRYPTO Smart-Picks" (pick_funnel) | **CORROBORATED AS DISPUTED** | Already flagged on-page; audit3 independently rates CRYPTO = KILL at 40.4% WR / PF 0.84 on n=6,740. |
| ETF tactical rotation / dual momentum edge | **CORROBORATED** | `reports/TACTICAL_ROTATION_EDGE_2026-07-04.md`: top5-6m rotation, 2007–2026 incl. GFC/COVID/2022: Sharpe 0.88 vs SPY 0.74, MaxDD −19% vs −51%, positive in all 3 time-thirds; VAA-G4 independent corroboration; matches the Faber/Antonacci literature and Hurst-Ooi-Pedersen's century of trend evidence. Caveat: smart-beta (risk control), not alpha; **forward n=0**. |
| Best "worth forward-testing" cells | Plausible, unproven | ETF `rs-breakout-scout` (n=80, WR 56%, net +0.58%/trade, q=0.167); ETF `adx-trend-scout` (n=43, q=0.167); EQUITY `donchian-stock-breakout` (n=45, net +1.89%); CRYPTO `btc-4h-rsi-macd-scout` (n=35, net +2.0%, DSR 0.118 — highest in class). All fail the 2×-cost stress; none promotable. |

## 3. What works per asset class (local evidence × external research)

External research report (with citations): `ACTIONPLAN_AUDITPAGE/2026-11-19T1906Z_copilot-moneyresearch/RESEARCH_EXTERNAL_EDGES.md`. Key synthesis:

| Class | Credible net-of-cost edge for a small account | Our status |
|---|---|---|
| **ETF** | Trend/tactical allocation (Faber 10-mo SMA, dual momentum): Sharpe ~0.5–0.8, drawdown roughly halved; monthly turnover survives costs (Novy-Marx & Velikov: >~50% monthly turnover rarely survives) | The ONE validated in-repo edge; forward clock newly unstuck (this PR) |
| **CRYPTO** | Funding carry compressed to ~2.7–6%/yr pre-fee (≈$0–80/yr on $2k — not worth building); 1–4wk time-series momentum documented (Liu-Tsyvinski) but gross, early-sample, decayed | Directional picks = KILL; 3 pre-registered paper slots now ticking live |
| **EQUITY** | Low-turnover 12-1 momentum survives costs; PEAD is dead for tradeable stocks (Martineau). **PDT $25k rule repealed** — FINRA 26-10, effective 2026-06-04 (broker phase-in to 2027-10-20) | Breakout family is the best WEAK cluster; POD-EQUITY-BREAKOUT registered |
| **FOREX** | Carry + momentum documented but concentrated in high-cost pairs; ESMA: 74–89% of retail CFD accounts lose | Class fails every gate; observe-only is correct |
| **COMMODITY** | Roll-yield/term-structure portfolios (Erb-Harvey) need a futures universe, not $2k | KILL + concentration; observe-only |
| **BOND** | Trend/duration timing earns a few %/yr vs T-bills ~3.4% — cash is the honest benchmark | insufficient n |
| **FUTURES** | Diversified trend needs dozens of markets; one overnight MES exceeds a $2k account; the Brazil 97%-loss study IS futures day trading | insufficient n |
| **PREDICTION MARKETS** | Only structural retail edge is **maker-side** (Kalshi maker 1.75% vs taker ~7%; maker-vs-taker cuts P(loss) by 9.3pp) | any live expression must be maker-only |

Base rates every short-term plan must beat: Brazil futures day traders — 97% of 300-day persisters lose (Chague et al.); Taiwan — −23.9bp/day net, <3% predictably profitable (Barber et al.); published anomalies decay 26–58% post-publication (McLean-Pontiff).

## 4. The $2,000 question

**Verdict: ETF — tactical dual-momentum rotation — for real capital, held strictly as a *drawdown-control* allocation (lagged reproduction §6.1: Sharpe edge narrows to +0.13 at 1-day lag and CAGR trails SPY; the crash protection is what survives). CRYPTO for the live *paper* sim. $0 real into short-term trading in any class today. A holder comfortable with −50% drawdowns should simply hold SPY/VOO.**

1. ETF TAA is the only edge with 20-year robust in-repo evidence AND deep external replication. On $2k: 4–5 commission-free ETFs, fractional shares, monthly rebalance, ~2–5bp cost. Expected: market-like return at roughly half the drawdown (≈$100–200/yr — the value is capital preservation + a provable process, not income).
2. Every short-term class we measure has **negative selection alpha** (−0.28%/trade ≈ −$5.5 expected per $2k trade), before the brutal day-trading base rates.
3. CRYPTO remains the right short-term *sandbox*: 24/7, fine-grained sizing, our richest data/resolver infra, documented short-horizon momentum. Real sizing only after a pod clears the audit3 forward gate (n≥100, net PF CI-LB > 1.0, 100% intrabar honesty, ≥90% benchmark coverage).
4. External ranking agrees: ETF (slow) > crypto spot momentum (experimental, maker orders only) > prediction-market maker > everything else; FX/futures/commodity day trading worst.

## 5. What shipped with this report (the live simulation program)

| Piece | File | What it does |
|---|---|---|
| Sleeve cross-mark | `alpha_engine/money_ready_verdict.py` (`_audit3_cross_mark`) + `/audit` badge in `audit_dashboard/template.html` | Every top-sleeve now carries the tribunal's independent verdict; uncorroborated sleeves say **UNVERIFIED (not in audit3)** |
| Live crypto paper sim | `verified_strategies/paper_pilot/crypto_intraday_sim.py` + `.github/workflows/crypto-intraday-sim.yml` (cron :07/:37) | 3 pre-registered slots (H-2026-11-19-01 VWAP reversion, -02 Bollinger MR, **-07 BTC 4h RSI+MACD — new**) on real 4h bars via the Binance→KuCoin→CryptoCompare failover chain; prop-firm guardrails (10% trailing-DD halt, 3% daily-loss pause, 40% consistency flag, n≥20 before judgment) |
| Forward bridge | `tools/pilot_forward_bridge.py` (+ `tools/crypto_bars.py`) | Re-resolves every pilot CLOSE intrabar-honestly from real bars into `reports/forward_observations.jsonl` (validated, idempotent) — audit2/audit3 consume it with zero new plumbing |
| ETF forward clock unstuck | `verified_strategies/paper_pilot/etf_dual_momentum_pilot.py` | Calendar-month segment closes (winner-stays holds produced forward n=0 since June); CLOSE rows now bridgeable under **H-2026-11-19-06 / POD-ETF-DUAL-MOMENTUM (new)**; the existing faber pilot feeds POD-FABER-TAA |
| Pre-registrations | `reports/hypothesis_registry.json`, `reports/audit3_confirmatory.json` | H-2026-11-19-06 (ETF dual momentum) and H-2026-11-19-07 (BTC 4h RSI/MACD) registered BEFORE any forward data, per M-107 |

**Monitoring / trial-and-error loop:** the workflow warns on every non-ACTIVE slot; mutate per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` only after n≥20; a halted slot's replacement must be a new pre-registered hypothesis (parallel new strategies, never silent parameter edits). First live tick 2026-11-19 opened `vwap_reversion` LONG BTCUSDT @ 62,757 (z=−1.96), paper-only.

**What success looks like:** a pod reaching n=100 forward rows with net PF CI-LB > 1.0. At ~30-min ticks with 3 slots × 3 symbols, expect months, not days — that is the honest cost of evidence. Forward tests verify *execution honesty* (slippage, fills, rule drift), not alpha; a few months of live data cannot statistically confirm a modest edge (SR 1.0 needs ~9 years for t=3), which is exactly why nothing promotes without the gate.

## 6. Peer review (2026-11-19, buffy via COMS) — status of the blocking items

1. **"ETF TAA does not reproduce under a one-month lag"** — **RESOLVED 20:31Z: partially upheld.** The written spec (`tools/taa_lagged_reproduction.py`, free yfinance data) + results (`reports/TAA_LAGGED_REPRODUCTION_2026-11-19.md`) show the headline Sharpe 0.89 / MaxDD −19.1% reproduces **only at same-close (lag0) execution** — the 2026-07-04 report's number was effectively unlagged. With an honest 1-day lag: Sharpe 0.82 vs SPY 0.69 (Calmar 0.43 vs 0.20, MaxDD −20.9% vs −52.9%) but **CAGR loses to SPY in every cell** (8.9% vs 10.8%). Under buffy's 1-month lag the 6m signal decays hard; 9m is lag-robust at ≈SPY Sharpe with half the drawdown. Acceptance threshold (Sharpe ≥ 0.88 lagged) NOT met. **$2k consequence:** TAA retained only as a *drawdown-controlled* allocation (SPY-minus-1-2% CAGR at ~half the drawdown); a holder comfortable with −50% drawdowns is better served by plain SPY/VOO buy-and-hold.
2. **"Selection alpha −0.276% is in no committed artifact"** — REFUTED against current origin/main: `audit_dashboard/data/audit3_ledger.json` (commit `3840d888270`, generated 2026-11-19T18:32Z) ships `selection_alpha.available=true`, overall `alpha_pct=-0.2763`, CI [−0.506, −0.043], n=3,192. The reviewer's branch was stale.
3. **"Class aggregates disagree up to 3.2× between surfaces"** — ACKNOWLEDGED. CRYPTO PF 0.26 (money_ready policy-clean/intrabar cohort) vs 0.84 (audit3 payload-net cohort) are different denominators and cost conventions; this report quotes each table under its own source and never mixes them. The structural fix is kilo-general's P0 backlog item "one canonical ledger per class" (`ACTIONPLAN_AUDITPAGE/2026-11-16T2210Z_kilo_auditpage-v3/BACKLOG_2026-11-16.md`), which needs an owner/design call.
4. **"Add a cost floor before the forward clock starts"** — ADOPTED immediately: `crypto_intraday_sim.py` now refuses any entry whose expected move to target is below 4× the 16bp round-trip cost (`COST_FLOOR_MULT × ROUND_TRIP_COST_PCT`), with tests. The btc-4h slot stays observe-only (all slots are; n=35 / DSR 0.12 was registered as a *hypothesis*, not evidence).
