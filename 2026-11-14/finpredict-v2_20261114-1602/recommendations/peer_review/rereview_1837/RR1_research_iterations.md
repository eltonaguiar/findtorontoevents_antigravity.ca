# RR1 — Peer Review: New Research Iterations (PROOF_PROTOCOL + ITERATION-001..003)

**Verdict: FAIL — not merge-ready as proof-bearing research.**
Conditional PASS only as *corroborating negative evidence* after the corrections in §6–§7.

**Reviewer:** RR1 (read-only; no repo source modified)
**Review time:** 2026-11-14 ~18:38Z
**Peer artifacts reviewed:**
- `.kilo/worktrees/finpredict/2026-11-14/finpredict/2026-11-14T160004Z/research/PROOF_PROTOCOL.md`
- `.../research/ITERATION-001.md`, `ITERATION-002.md`, `ITERATION-003.md`
- `.kilo/worktrees/finpredict/updates/2026-11-14-quant-audit-multitest.md`

**Our artifacts compared:**
`research/profitability/{PROTOCOL.md,HYPOTHESES.md,README.md}`, `runs/v2/{VERDICT.md,ROBUSTNESS.md,results.json}`, `validation/STATS_REVIEW_H10.md`.

**Why FAIL (one line):** the peer never claims a proved edge — good — but ITERATION-003's "clean single-hypothesis OOS" is selection-contaminated, ITERATION-002's cleaning arithmetic/counts are wrong, costs are never verified, and the underlying closed ledger mutates materially intraday (Σ PnL −469.52 → −574.12 in 3.5h).

---

## 1. Per-iteration extraction

| Iter | Hypothesis / question | Dataset (exact) | Split | Costs | Metrics | Claimed verdict | Reproduction status |
|---|---|---|---|---|---|---|---|
| 001 | Are the apparent edges real? Apply purity + multiple-testing first. | `audit_dashboard/data/pf_registry.json::by_asset_class_strategy_policy_clean_net` (683 rows); `audit_dashboard/data/anti_overfit_audit.json` (80) | none (descriptive) | none — uses ledger PnL as-is | n, WR, PF, one-sided binomial, Bonferroni α=0.05/683 | **FAIL gate 1**; 15 hits are CRYPTO artifacts; nothing provable yet | **PARTIAL.** 683/80/69/15 and named rows reproduce. WR/PF range claim is wrong; one seed is contradicted by the clean registry (§2, D4–D5). |
| 002 | After a row-level purity filter, does any strategy prove profitable? | live `dashboard_data.json::picks.recent_closed` (3,500 rows) — numbers match the **14:30Z** snapshot, not the audit's cited 16:15Z payload | none (full sample) | **none verified** (`after_cost_net_per_trade` null on live picks; PnL basis unknown) | n, Σ/mean PnL, PF, one-sided t, Bonferroni N=683 | **No.** Best candidate `rs-breakout-scout` t=2.37/p=0.0089 fails α=7.3e-5; book net-negative | **MOSTLY.** Σ/mean/PF/t reproduce; cleaning step is arithmetically impossible; 9/14 → 7/14 (§2, D1–D3). |
| 003 | Single "pre-registered" OOS test of `rs-breakout-scout` + 2 secondaries, 70/30 time split. | same `recent_closed` (14:30Z snapshot) | 70/30 chronological, cutoff ≈2026-09-09 (not declared in 002) | **none** | IS/OOS PF, t, one-sided p | **OOS fails.** rs t 2.07→1.16 (p=0.124); luxalgo PF 1.235<1.5; vol-contraction reverses PF 1.43→0.49; **size all strategies to zero** | **MOSTLY reproduces numerically** (rs OOS t=1.14/p=0.127; luxalgo & vol exact). **But the OOS is not clean**, all 3 OOS n are <100, and vol n=25 is <30 (§3). |

**Peer's own proof bar (PROOF_PROTOCOL.md:5–15) vs what the iterations actually executed:**

| Gate | Requirement | Implemented in 001–003? |
|---|---|---|
| 1 Data purity | row-level exclusions (frozen, flat-3%, forward-seed, zero-entry, single-source≥40%) | **Partial** — 002 drops a claimed 23 rows; no single-source/forward-seed per-strategy pass |
| 2 Sample size | n≥100 per claim (n≥30 only with PF CI strongly ≠1) | **No** — all 3 OOS n are <100 (rs 40, lux 388, vol 25); vol also fails n≥30; no CI anywhere |
| 3 PF + paired-bootstrap CI | PF>1.5, CI lower bound >1.0 via `benchmark_closed_ledger.py` | **No bootstrap CI computed anywhere** |
| 4 Expectancy significance | Bonferroni/Holm across N=683 | **Partial** — Bonferroni computed in 002; no Holm; no clustering/effective-n correction |
| 5 WR plausibility | WR>80% / PF>5 ⇒ artifact | **Informal only** (used narratively, not gated) |
| 6 OOS | walk-forward windows profitable ≥67% | **No** — one arbitrary 70/30 split substituted; `walkforward_validator.py` never run |
| 7 Autocorr + DSR | `autocorr_flag==OK`, DSR>0.95 at n_trials=683 | **No DSR at all**; autocorr only quoted for one seed |
| 8 Costs | net of slippage + fees | **No** — cost basis of `pnl_pct` never established |
| 9 Not single-source | edge persists >1 source/regime | **No** — luxalgo is admitted single-source; rs-breakout is 1 emitter |

So the proof protocol is **aspirational**: the iterations use roughly 4 of 9 gates, and the confirmatory iteration (003) is the weakest.

---

## 2. Claim verification (independent recomputation)

Method: loaded the same public JSON artifacts. Two local payload snapshots were used —
`/tmp/kilo/dashboard_data_latest.json` (generated **14:30:07Z**, 3,500 recent_closed) and
`/tmp/kilo/dash.json` (generated **17:58:53Z**, 3,500 recent_closed); plus
`audit_dashboard/data/pf_registry.json` and `audit_dashboard/data/anti_overfit_audit.json`
(mtime 18:23Z) and `audit_dashboard/data/picks_now_live_pnl.json` (17:56:33Z).
`pnl_pct` was taken as published; one-sided t = mean/std(ddof=1)·√n; PF = Σwins/|Σlosses|.

| # | Claim (source:line) | Independent check | Result |
|---|---|---|---|
| V1 | "FULL strategy universe (N = 683), α = 0.05/683 ≈ 7.3e-5" (PROOF_PROTOCOL.md:10) | 0.05/683 = 7.321e-5; `by_asset_class_strategy_policy_clean_net` has exactly **683** rows | **PASS** |
| V2 | "80 audited strategies … 69/80 OVERFIT_LIKELY" (PROOF_PROTOCOL.md:27; ITERATION-001.md:3) | `anti_overfit_audit.json`: `n_strategies_audited=80`, verdicts `{EDGE_LIKELY_REAL:6, UNDETERMINED:5, OVERFIT_LIKELY:69}` | **PASS** |
| V3 | "15 strategies pass a naive Bonferroni test on win-rate (PF>1)" (ITERATION-001.md:7) | Recomputed one-sided binomial p per strategy vs α=0.05/683 with PF>1 ⇒ **exactly 15** hits | **PASS** |
| V4 | "all 15 are CRYPTO with WR 77–98% and PF 5–56" (ITERATION-001.md:7) | All 15 are CRYPTO, but observed ranges are **WR 65.1%–98.0%** and **PF 1.2–56.7** (e.g. `hs_lb_None` 69.6%/1.2; `Order Book Imbalance` 65.1%/3.1) | **DRIFT** (overstated band) |
| V5 | "ADX Trend Confirmation 213 / 97.2% / 56.7" (ITERATION-001.md:11) | registry: n=213, WR 97.2%, PF **56.726** | **PASS** |
| V6 | "`mega_mut_macd_rsi_m084` 124 / 90.3% / 49.4" (ITERATION-001.md:12) | registry: n=124, 90.3%, PF **49.371** | **PASS** |
| V7 | "`forex_rsi2_mean_reversion` FOREX n=1,464 PF 1.645" (ITERATION-001.md:27) | anti-overfit: n=1,464, PF 1.645, `HIGH_AUTOCORR` — **but the policy-clean registry row is n=359, WR 34.5%, PF 0.860 (losing)**; the caveat is undisclosed | **DRIFT / misleading seed** |
| V8 | "Bollinger Squeeze Breakout 745 / 46.7% / 1.44" (ITERATION-001.md:28) | registry: 745 / 46.7% / **1.440** | **PASS** |
| V9 | "CCI Reversal Scout 257 / 44.4% / 1.31"; "VerifiedStochRsi 231 / 50.2% / 1.66"; "MeanReversionBB 201 / 49.8% / 1.41" (ITERATION-001.md:29–31) | registry: 257/44.4/1.312; 231/50.2/1.659; 201/49.8/1.413 | **PASS** |
| V10 | "3,500 rows → dropped 23 … → 3,488 clean" (ITERATION-002.md:7,13) | **3,500 − 23 = 3,477 ≠ 3,488**. 3,488 corresponds to dropping 12, not 23 | **FAIL (arithmetic)** |
| V11 | "12 `pnl=0` frozen, 11 UNKNOWN phantoms" (ITERATION-002.md:7) | 14:30 snapshot: `pnl_pct==0` = **11** (all `status=CLOSED`, `exit_reason=UNKNOWN`); `status=="UNKNOWN"` = **0**; `exit_reason=="UNKNOWN"` = **22** | **FAIL (counts)** |
| V12 | "0 placeholder all-wins-exactly-3.0% strategies in the closed ledger" (ITERATION-002.md:8) | Recomputed: **0** strategies in `recent_closed` whose every trade is exactly +3.0 | **PASS** |
| V13 | "n=3,488, sum PnL −469.51%, mean −0.1346%/trade" (ITERATION-002.md:13) | 14:30 snapshot over 3,500 rows: Σ **−469.52**, mean **−0.1341** (zero-PnL drops do not change the sum). Sum/mean PASS; n FAIL (V10) | **PARTIAL** |
| V14 | "14 strategies have n≥50; 9 of 14 have PF<1.0" (ITERATION-002.md:14) | 14 strategies with n≥50 ✓; **7 of 14** have PF<1.0 (qmj, rsi-div, stoch-rsi, price-accel, london, macd-hidden, unknown) | **DRIFT** |
| V15 | "`rs-breakout-scout` ETF n=133, WR 53.4%, PF 1.652, tPnL +95.12" (ITERATION-002.md:15) | EXACT: n=133, mean +0.7152, WR 53.4%, PF 1.652, Σ +95.12 | **PASS** |
| V16 | "t=2.37, p=0.0089" (ITERATION-002.md:21) | t=**2.36**, one-sided p=**0.00914** (snapshot drift) | **PASS (within drift)** |
| V17 | "`luxalgo_confluence` 1,290 / +0.167% / t=1.71 / p=0.044" (ITERATION-002.md:22) | 1,290 / +0.1673 / t=**1.71** / p=**0.0436** | **PASS** |
| V18 | "`vol-contraction-scout` 81 / +0.229% / t=0.39"; "momentum-factor 105/+0.101/t=0.23"; "intermarket 104/+0.065/t=0.25" (ITERATION-002.md:23–25) | 81/+0.2287/t=0.389; 105/+0.1013/t=0.229; 104/+0.0649/t=0.248 | **PASS** |
| V19 | rs-breakout IS 93 / PF 1.695 / t 2.07; OOS 40 / PF 1.539 / t 1.16, p=0.124 (ITERATION-003.md:9) | IS 93/1.695/**2.059**; OOS 40/1.539/**1.141**, p=**0.127** | **PASS (within drift)** |
| V20 | luxalgo IS 902/1.070/0.88; OOS 388/1.235/1.85/0.032; vol IS 56/1.427/1.06; OOS 25/0.487/−1.37/0.915 (ITERATION-003.md:10–11) | lux 902/1.070/0.880, OOS 388/1.235/1.850/p=0.0322; vol 56/1.427/1.052, OOS 25/0.487/−1.062/t=−1.343/p=0.9104 | **PASS** |
| V21 | "policy-clean aggregate PF 0.94" (PROOF_PROTOCOL.md:27) | 14:30 payload `summary.profit_factor` = **0.94** (17:58: 0.92). The **policy-clean strategy ledger** aggregate is **0.265** (n=23,001); class-level 0.272; raw 0.986. 0.94 is the dashboard summary PF, **not** the policy-clean aggregate | **MISLABELLED** |
| V22 | "3,489 resolved, WR 41.8%" (audit:263) | 17:58: WON 1,454 + LOST 2,035 = **3,489**, WR **41.7%**; 14:30 `summary.overall_win_rate` = **41.8%** | **PASS** |
| V23 | Bonferroni for 177 strategies = 2.82e-4 (audit:265) | 0.05/177 = 2.825e-4 | **PASS** |
| V24 | money_ready table, all 9 classes (audit:294–304) | EXACT on 14:30 and 17:58: CRYPTO 3,705/35.87/0.9196; EQUITY 250/59.2/0.9392; FOREX 612/32.19/0.6596; COMMODITY 229/40.17/1.0256; FUTURES 52/42.31/1.0936; ETF 45/2.22/0.0216; MEME 10/10.0/0.0234; BOND 1/0/0; PENNY 1/0/0 | **PASS** |
| V25 | "n_bonferroni_pass 21 / 83 tested", `_fdr_gate_enforce:false`, "sizing_allowed:false for every class", "kill_switch 177/56/42, wr_lift +6.16, pf_lift −0.0223" (audit:306–309) | 17:58: `n_bonferroni_pass=21`, `n_fdr_tested=83`, `_fdr_gate_enforce=False`; `readiness.by_class[*].sizing_allowed=False` (9/9); kill_switch 177/56/42, impact `{wr_lift_pp:6.16, pf_lift:-0.0223, baseline_pf:0.0314, post_pf:0.0091}` | **PASS** |
| V26 | "EXPIRED … `closed_at` empty on 100%" (audit:139) | 14:30: 3,377 EXPIRED, **3,377** empty `closed_at` (100.0%) | **PASS** |
| V27 | "`picks_now` n_open 4,361, n_priced 3,900, avg −1.90%, 1,460 pos / 2,401 neg / 461 no price" (audit:146) | local `picks_now_live_pnl.json` (17:56:33Z): **4,361 / 3,900 / −1.9 / 1,460 / 2,401 / 461** — exact | **PASS** |
| V28 | picks_now by class: BOND 1,313 (1,249, −1.67) · EQUITY 767 (648, −7.08) · ETF 1,730 (1,527, −0.68) · FOREX 547 (476, +0.64) · COMMODITY 4 (0 priced) · CRYPTO absent (audit:147) | EXACT, including CRYPTO absent | **PASS** |
| V29 | "365 workflows: 361 active, 4 disabled" (audit:26) | `raw/A_workflows.json` (NDJSON): 365 records, `{active:361, disabled_manually:4}` | **PASS** |
| V30 | "997 rows sit in 414 duplicate `(symbol,direction,day,strategy)` groups (max 9)" (audit:287) | 14:30: **430 groups / 664 extra rows / max 11**; 17:58: **431 / 668 / max 14**. Direction holds; exact counts do not | **DRIFT** |
| V31 | "EQUITY 75% / PF 8.86 on n=8" (audit:124) | `performance.by_asset_class.EQUITY`: wins 6 / losses 2, PF 8.86 | **PASS** |
| V32 | audit rolling windows: 30d n=1,323/Σ−443.1/PF 0.804; 365d n=3,380/Σ−189.4/PF 0.965 (audit:205–211) | Not reproducible from either retained snapshot: 14:30 all-3,500 Σ−469.5/PF 0.92; 17:58 Σ−574.1/PF 0.903. Window anchors/status filters not documented | **UNVERIFIED** |

**Net:** the peer's *quantitative core* for the research iterations is largely reproducible (V3, V5–V6, V8–V9, V15–V20, V24–V29), but the **cleaning step (V10–V11), the seed selection (V7), and two summary bands (V4, V14) are wrong**, and one headline label is wrong (V21).

---

## 3. Does the peer claim a **proved** profitable approach?

**No.** Every iteration explicitly concludes the opposite:
- 001: "a profitable approach cannot be proven on this ledger until gate 1 is applied" (ITERATION-001.md:19).
- 002: "No strategy proves profitable on the closed ledger" (ITERATION-002.md:29).
- 003: "No profitable approach is provable on this system" (ITERATION-003.md:19).

There is therefore **no positive edge claim to falsify**. That is the honest part of this work and it matches our own `NOT PROVED` verdict.

The problem is the **confirmatory framing** of 003:

1. **Seen OOS reused for selection.** `rs-breakout-scout` was selected in 002 from the **full 3,500-row sample**. 003 then splits that same sample 70/30 and calls the last 30% "OOS". The 30% participated in the ranking that made it the "sole candidate", so it is *seen* data. No cutoff date was declared in 002 (002:33 only says "hold out a date cutoff" as a future step). This is exactly the failure mode our protocol §4 forbids (`PROTOCOL.md:41–44`), and the reason H10 was downgraded.
2. **The correction waiver is invalid.** 003:3 says "a single pre-registered OOS test needs only nominal significance (no 683-way correction)". Since the window was not held out before selection, and 003 in fact reports **three** OOS tests (rs, luxalgo, vol-contraction), the correct multiplicity is at least 3 — and none of the three passes at α=0.05/3 on its own gate.
3. **Gate 2 is violated by the peer's own rule.** PROOF_PROTOCOL.md:8 requires n≥100 (or n≥30 with a PF CI strongly away from 1). Two of the three OOS tests fail outright on sample size — rs n=40 (<100, no CI) and vol-contraction n=25 (<30) — and the third (luxalgo, n=388) passes n but fails the PF bar (1.235<1.5). No bootstrap CI is computed for any of them.
4. **Costs are never established.** `pnl_pct` is taken from the dashboard ledger. The same payload shows `after_cost_net_per_trade` is null on all live picks (audit:101–106). `rs-breakout-scout` has only ~+95pp of net PnL cushion (gross profit ≈241.0, gross loss ≈145.9); subtracting a 20 bps round trip (71 wins, 62 losses) gives **PF ≈1.43, below the peer's own 1.5 bar**. At the peer's implied ETF cost (5 bps/side) it is ≈1.54 — a knife-edge that was never tested. The peer's gate 8 is unenforced, and the negative conclusion is only conservative by accident, not by construction.

**Verdict on the claim:** the negative conclusion is **supported in direction** (closed ledger net-negative; nothing survives N=683; OOS decays/reverses), but **003 does not constitute a clean confirmatory test** and cannot be cited as "pre-registered OOS evidence".

---

## 4. Method deltas

### 4.1 What the peer adds that we missed (candidate adoption)

| Peer method | Why it matters for us | How we would use it |
|---|---|---|
| **Row-level purity exclusions** (frozen/unquoted, flat-3% placeholder, forward-seed, zero-entry, single-source ≥40%) — PROOF_PROTOCOL.md:7 | Our forward ledger will eventually ingest live picks; these are cheap, explicit tripwires for exactly the artifacts that poisoned the production book | Add to forward-ledger QA as **hard excludes/annotations**, never retro-applied to v1/v2 |
| **WR>80% ∧ PF>5 ⇒ artifact until proven** — PROOF_PROTOCOL.md:11 | Catches frozen-price/placeholder pathologies before they enter a claim; our clean-data backtests never hit it, but a forward/live sleeve can | Add as a **sanity gate** on forward results |
| **Bonferroni/Holm across the full production universe (N=683 / 177)** — PROOF_PROTOCOL.md:10, audit:265 | Our N=12/38 controls only *our* search; it does not control a claim mined from the 683-row production ledger | Use as a **screening correction** for any production-ledger claim; keep N≥38 for our frozen forward hypothesis |
| **`autocorr_flag==OK` pre-screen** — PROOF_PROTOCOL.md:13 | Ledger trades are clustered (997-row pseudo-replication claim); an autocorr flag is a fast red flag | Pre-screen any ledger-derived p-value; block bootstrap remains the primary inference |
| **"Not single-source" gate** — PROOF_PROTOCOL.md:15 | Our out-of-universe ETFs (DIA/IWM/VTI) test breadth, but not emitter concentration | Add a **source-concentration** check to forward evidence (>40% one emitter ⇒ not promotable) |
| **Universe-wide "count every look, including failures"** — the analogue of our `PROTOCOL.md` §8, stated at PROOF_PROTOCOL.md:10/23 | Reinforces our own N accounting; the peer's 683/177 count is more conservative than our 38 | Adopt the *principle*; do not adopt 683 as the confirmatory N for a frozen single hypothesis |

### 4.2 What we have that the peer missed (do not regress)

| Our method | Why it is load-bearing | Peer gap |
|---|---|---|
| **Independent, point-in-time public data** (Binance Vision, Nasdaq, Treasury) | Removes the contaminated production ledger entirely | Peer measures a ledger whose outcomes mutate intraday (§5, D8) |
| **Locked pre-registration before results** (`PROTOCOL.md:3–7`) | Makes the OOS meaningful | Peer protocol/iterations are same-minute artifacts; pre-registration cannot be established (D10) |
| **True OOS discipline** (rolling OOS; seen OOS demoted, `PROTOCOL.md:41–44`) | Prevents post-hoc variant selection | 003 reuses the 002 sample as "OOS" |
| **Costs per side + 2× stress** (`PROTOCOL.md:50–51`; `run_v2.py:126–133`) | Kills cost-fragile edges; H10 dies at 30 bps (`STATS_REVIEW_H10.md:319–328`) | No cost basis; gate 8 unenforced |
| **Benchmark (B&H + risk-matched) and excess-of-rf Sharpe** (`PROTOCOL.md:65–66`; `STATS_REVIEW_H10.md:273–297`) | Separates beta/cash carry from skill | Peer has **no benchmark at all**; absolute PF in a 2024-26 bull tape is not evidence of edge |
| **Return-series metrics** (Sharpe, CAGR, vol, maxDD, Calmar, turnover, exposure) | Compounds, sizes, and risk-adjusts; per-trade mean % does not | Peer reports only n/WR/PF/mean-PnL; no exposure or drawdown |
| **DSR with skew/kurtosis + PBO/CSCV + block bootstrap** (`backtest.py:119–160`) | Corrects for selection and non-normal returns | No DSR, no PBO, no bootstrap in 001–003 |
| **Execution-lag, ex-top-day, parameter-stability, regime, risk-matched tests** (`validate_h10.py`; `STATS_REVIEW_H10.md` §4–5) | These are what downgraded H10 despite passing mechanical gates | Peer never stress-tests its "best" candidate |
| **Forward paper ledger with frozen parameters** (`forward/README.md`) | Only path to `PROVISIONAL`/`PROVED` | Peer recommends forward testing but ships no ledger |
| **Explicit N including grid looks (38) and ex-top-day DSR** | Honest effective multiplicity | Peer's N=683 is universe-wide but never applied per candidate in 003 |

### 4.3 Shared weaknesses (both programs)

- Daily/per-trade granularity; no intraday fill model; shorts/funding not modeled (our v1 is mostly long/flat; the peer's ledger has shorts and no funding).
- Both are dominated by the same 2024-2026 regime; neither has out-of-regime confirmation.
- Both rely on a single vendor/format for at least one class (peer: dashboard JSON; us: Nasdaq price-only closes).

---

## 5. Drift register

### 5.1 Peer drift (verified above)

| ID | Drift | Evidence |
|---|---|---|
| D1 | "3,500 − 23 → 3,488" is arithmetically impossible | 3,500−23=3,477 (ITERATION-002.md:7,13) |
| D2 | "12 `pnl=0`, 11 UNKNOWN phantoms" | observed 11 `pnl_pct==0` (all CLOSED/exit UNKNOWN); `status==UNKNOWN` = 0; `exit_reason==UNKNOWN` = 22 |
| D3 | "9 of 14 have PF<1" | observed 7 of 14 |
| D4 | "WR 77–98%, PF 5–56" for the 15 hits | observed WR 65.1–98.0%, PF 1.2–56.7 |
| D5 | `forex_rsi2_mean_reversion` PF 1.645 seed | policy-clean registry: n=359, WR 34.5%, PF 0.860 |
| D6 | "policy-clean aggregate PF 0.94" | that is `summary.profit_factor` at 14:30; policy-clean strategy aggregate = 0.265 |
| D7 | **Provenance mismatch**: research numbers match the **14:30** payload (Σ −469.52), the audit cites a **16:15:51** payload (WON 1,459/LOST 2,030), and the archive README says the source was **14:30** | ITERATION-002.md:13 vs audit:65 vs peer README |
| D8 | **Closed ledger mutates intraday**: the 3,500-row `recent_closed` slice, 14:30→17:58, moved Σ PnL **−469.52 → −574.12** and PF **0.92 → 0.903**; in `picks.active_raw` the resolved counts moved backward, SL_HIT **55 → 35**, TP_HIT **25 → 22** | 14:30 vs 17:58 payloads; outcomes move backward |
| D9 | Duplicate/pseudo-replication counts | 414 groups/997 rows/max 9 claimed vs 430/664/max 11 (14:30) and 431/668/max 14 (17:58) |
| D10 | **Chronology not corroborated**: in-doc 18:15/18:20/18:24Z vs file mtimes 18:17/18:17/18:18/18:19 (003 mtime *earlier* than its claimed 18:24) | `ls -l` on the four files |
| D11 | active_raw 4,164 / EXPIRED 3,378 / OPEN 703 / SL 57 / TP 26 | nearest snapshots: 4,148 (3,377/691/55/25) at 14:30 and 4,166 (3,369/740/35/22) at 17:58; no 16:15 payload retained |
| D12 | "83 resolved picks still in active feed" | 80 at 14:30, 57 at 17:58; not reproducible at the claimed count |

### 5.2 **Our own** drift (found while comparing; must be fixed before publication)

This is the same class of problem the peer has, and it matters because `STATS_REVIEW_H10.md` is our adversarial-review artifact.

| ID | Drift | Evidence |
|---|---|---|
| O1 | Review headline numbers ≠ committed `results.json` | STATS: Sharpe **1.845180**, DSR **0.978851**, p **0.00180184**, 2× **1.683406**, boot p05 **1.275667**; results.json: **1.832195 / 0.977597 / 0.00194093 / 1.659554 / 1.269015** |
| O2 | PBO mismatch | STATS 0.237685 vs results.json **0.238850**; all-12 OOS 0.1036 vs **0.106371** |
| O3 | Run times | STATS says v1 18:20:28 / v2 18:23:19; current `run_at` v1 **18:34:40**, v2 **18:36:05** (artifacts regenerated *after* the review) |
| O4 | H7 numbers | STATS 1.514575 / DSR 0.9507 / p 0.0104108 vs v1 results **1.503960 / 0.948347 / 0.0109616** |
| O5 | MaxDD / yearly rounding | `ROBUSTNESS.md` −7.7% vs `VERDICT.md` −7.6% vs results **−7.665%**; 2024 Sharpe 2.98 vs STATS 3.01; 2026 2.42 vs 2.44 |
| O6 | PBO sample label | `HYPOTHESES.md`/`VERDICT.md` cite **0.106** (OOS-only, non-standard); STATS §2.2 gives full-sample all-12 **0.4173**. Pass either way, but the label is wrong |
| O7 | `file:line` citations | STATS cites `backtest.py:135-159` (def at **136**), `strategies.py:132-146` (def at **135**), `backtest.py:171-184` (**172-183**), `run_v2.py:114-126` (gates loop **120-136**), `run_v2.py:96-106` (merge block **106-116**, `setdefault` **113**). `validate_h10.py:73-81` ✓ exact |
| O8 | Two p-values in one folder | H10 row/VERDICT cite **0.00194** (results.json); STATS cites **0.00180** |

**Root cause of O1–O4:** `run_v1.py`/`run_v2.py` were re-run at 18:34:40/18:36:05, after `STATS_REVIEW_H10.md` was written, and the data cache is gitignored/refreshed. The review's "matches to 9.84e-17" was against the earlier `oos_returns.csv`. The conclusion is unchanged (all gates still fail the strict standard), but the numbers must be reconciled to one frozen artifact set.

---

## 6. ADOPT / MERGE / REJECT (exact source → target)

> No source changes were made by this review; this is the recommended merge plan.

| Decision | Peer source | Target in our research folder | Change |
|---|---|---|---|
| **ADOPT** | `PROOF_PROTOCOL.md:7` (row-level purity exclusions) | `research/profitability/PROTOCOL_ADDENDUM_2.md` (new) §"Forward-ledger QA" | Add explicit excludes/annotations: `current_price==entry`, flat-3% all-wins, forward-seed batch, zero-entry, single-source ≥40%. Forward-only; do **not** retro-apply to v1/v2. |
| **ADOPT** | `PROOF_PROTOCOL.md:11` (WR>80%/PF>5 artifact tripwire) | `forward/update_ledger.py` (validate step) + `PROTOCOL_ADDENDUM_2.md` | Hard-fail/flag forward stats when WR>80% or PF>5 with n<30; never celebrate an "impossible" metric. |
| **ADOPT** | `PROOF_PROTOCOL.md:10,13,15` (universe-wide correction, autocorr, single-source) | `PROTOCOL_ADDENDUM_2.md` §"Screening" + `forward/README.md` rules | Use N=683/177 Bonferroni/Holm **as a screen** for production-ledger claims; require `autocorr_flag==OK`; no emitter >40% of forward evidence. Keep N≥38 for our frozen forward hypothesis. |
| **MERGE** | `ITERATION-002.md:13` + `ITERATION-003.md:17–26` | `runs/v2/VERDICT.md` → new "Independent ledger cross-check (corroboration only)" subsection | Add 4 bullets: recent_closed net-negative (Σ −469.5% at 14:30 snapshot), no candidate survives N=683, OOS decay/reversal, 0/9 money-ready. Label **peer-reported / corroboration**, cite the snapshot time, and state the ledger is unstable (D8). |
| **MERGE** | `updates/2026-11-14-quant-audit-multitest.md:294–309` | `runs/v2/VERDICT.md` → "Prior system context" | Add verified: 0/9 money-ready, `readiness.sizing_allowed=false` 9/9, kill_switch 42/56 killed yet `pf_lift=−0.0223`. These numbers re-verified exact (V24–V25). |
| **MERGE** | `validation/STATS_REVIEW_H10.md` §1.2, §2.2 | `HYPOTHESES.md` H10 row + `VERDICT.md` table | Fix PBO label (**0.106 = OOS-only**; full-sample all-12 **0.417**) and reconcile the headline set to the committed `results.json` (1.8322 / 0.9776 / 0.001941 / 1.6596 / 1.2690). |
| **MERGE** | — | `runs/v2/ROBUSTNESS.md` | Regenerate from `results.json`/`robustness.json`; align maxDD (−7.665%) and 2024/2026 yearly Sharpe (3.01/2.44). |
| **MERGE** | — | `validation/STATS_REVIEW_H10.md` | Add an **erratum block**: numbers were computed on a pre-18:34 data snapshot; list both sets and label the artifact each came from. |
| **REJECT** | `ITERATION-003.md:3` ("single pre-registered OOS test needs only nominal significance") | — (do not import) | Invalid: the 70/30 window was inside the 002 selection sample and no cutoff was pre-declared. No correction waiver. |
| **REJECT** | `ITERATION-002.md:7–9,13` ("closed ledger largely clean / 3,488 clean") | — | Not proof-grade: arithmetic wrong, 3,377 expired rows unresolved, 664+ pseudo-replicated rows, no cost basis, ledger mutates intraday. Corroboration only. |
| **REJECT** | `ITERATION-001.md:27` (`forex_rsi2_mean_reversion` PF 1.645 seed) | — | Contradicted by policy-clean registry (n=359, WR 34.5%, PF 0.860). Not a candidate. |
| **REJECT** | `PROOF_PROTOCOL.md:27` ("policy-clean aggregate PF 0.94") | — | Replace with measured: policy-clean strategy-ledger PF **0.265** (n=23,001); summary PF 0.92 (17:58) / 0.94 (14:30); raw 0.986. |
| **REJECT** | `ITERATION-003.md:9` (single 70/30 split as gate 6) | — | Does not satisfy PROOF_PROTOCOL gate 6 (walk-forward windows ≥67% profitable). Run `alpha_engine/walkforward_validator.py` or declare gate 6 unimplemented. |

### 6.1 Required edits to `HYPOTHESES.md` / `VERDICT.md`

**`HYPOTHESES.md`**
- Do **not** add H13 / the peer's candidates. No status changes: all 12 stay `NOT_PROVED`.
- H10 row: keep `NOT_PROVED (exploratory)`; replace "PBO 0.106" with "PBO 0.106 (OOS-only all-12; full-sample all-12 0.417)"; keep p=0.00194 (matches `results.json`) and add a note that the review's p=0.00180 came from a pre-18:34 data snapshot.
- Add a one-line registry note: "Cross-check 2026-11-14: an independent production-ledger audit (3,500 recent_closed rows) also found no strategy surviving N=683 and 0/9 classes money-ready. Corroboration only; ledger unstable intraday."

**`runs/v2/VERDICT.md`**
- Add §"Independent ledger cross-check (peer-reported, corroboration only)" with the 4 bullets above and snapshot times.
- In the H10 metrics table, label every row's artifact (`results.json` vs `STATS_REVIEW_H10.md`), and reconcile the five drifting metrics (O1).
- Change "PBO (all 12, common calendar) 0.106" to "PBO 0.106 (OOS-only all-12; full-sample 0.417)".
- Add one sentence: "The peer review's negative conclusion is directionally consistent, but its 70/30 split is not a clean OOS (selection-contaminated) and its cost basis is unverified."

---

## 7. Fabricated / unsupported numbers and destructive recommendations

**Fabricated:** none found. There is no invented positive edge, and the peer explicitly marks futures prices, GitHub warnings, MySQL, and attrition magnitude as unverified. That is commendable.

**Unsupported or mislabelled as stated:**
1. `PROOF_PROTOCOL.md:27` "policy-clean aggregate PF 0.94" — 0.94 is `summary.profit_factor`, not the policy-clean strategy aggregate (0.265).
2. `ITERATION-001.md:7` "WR 77–98%, PF 5–56" — actual 65.1–98.0% / 1.2–56.7.
3. `ITERATION-002.md:7` "3,500 − 23 → 3,488" and "12 pnl=0 / 11 UNKNOWN phantoms" — arithmetic and counts.
4. `ITERATION-002.md:14` "9 of 14 PF<1" — 7.
5. `ITERATION-001.md:27` `forex_rsi2` PF 1.645 without disclosing policy-clean PF 0.860.
6. `audit:287` duplicate counts (414/997/max 9) — not reproducible (430/664/max 11 at 14:30).
7. `audit:205–211` rolling-window table — not reproducible from retained snapshots (anchor/filter undocumented).

**Destructive recommendations:** none in the reviewed files. "Size all strategies to zero for live capital" (ITERATION-003.md:26) is a capital-allocation recommendation, not a destructive repo action, and it is consistent with `readiness.sizing_allowed=false` for all 9 classes (V25). It should be framed as a **risk decision**, not as proof that no edge can ever exist.

⚠️ Separate warning (outside the reviewed set): the peer's `peer-review/PEER_RECONCILIATION.md` records a veto list for sibling v4 `proposed_fixes/**` containing destructive SQL (`DELETE` ghost rows, `UPDATE TIME_EXIT→LOST, pnl_pct=0.0`, `EXPIRED_FORCE` mass rewrite, unblocking FUTURES/COMMODITY without a feed). Those must **not** be merged or executed; they are not part of the research iterations reviewed here.

---

## 8. UNVERIFIED

| Item | Why unverified |
|---|---|
| Exact 16:15Z payload counts (active=10, active_raw=4,164, WON 1,459/LOST 2,030, EXPIRED 3,378/OPEN 703/SL 57/TP 26, "83 resolved in active feed") | No 16:15 payload retained in the peer folder; nearest snapshots are 14:30 and 17:58 and they differ materially (D8, D11, D12) |
| Audit rolling windows (1d/7d/30d/90d/365d) | Anchor/filter not documented; not reproducible from either retained snapshot (V32) |
| "365 workflows: 292 success / 30 failure / 11 cancelled / 11 in-progress / 1 skipped / 20 never-run" | Only totals (365/361/4) verified from `A_workflows.json`; per-workflow last-run conclusions were not re-queried |
| "77 failures in 1,500 runs (5.1%)" | GitHub API window not re-queried |
| Futures prices ES=F / PA=F / SB=F | No reachable source (Yahoo 429, CNBC empty, Stooq JS-gated) — peer's own label is correct |
| GitHub warning-level annotations | Run-level `/annotations` 404 for this repo |
| MySQL tables (`ejaguiar1_stocks`, `ejaguiar1_backtests`, `at_signal_outcomes`) | Not queried; peer did not query them either |
| Whether `pnl_pct` is net of any cost for any row | `after_cost_net_per_trade` null on all live picks; no cost field populated |
| Magnitude/direction of attrition bias from 3,377 expired rows | Cannot be determined from the published JSON |
| Peer in-document chronology (18:15/18:20/18:24Z) | Contradicted by file mtimes (18:17–18:19Z); pre-registration cannot be established |
| `picks_now` EQUITY −7.08% cause | Not established (genuine drawdown vs split-adjusted entry mismatch) |
| Our own pre-18:34 vs post-18:36 artifact set | Two data pulls exist; the "correct" H10 numbers depend on which snapshot is frozen |

---

## 9. Top 5 findings

1. **No proved-profitability claim exists — the peer's negative result is honest and its core numbers reproduce** (683 universe, 15 Bonferroni hits, `rs-breakout` 133/53.4%/1.652/+95.12, luxalgo t=1.71, vol-contraction OOS reversal, 0/9 money-ready, kill_switch 42/56). FAIL is about rigor, not honesty.
2. **ITERATION-003 is not a clean OOS.** The 70/30 window was inside the sample that selected `rs-breakout-scout` in 002, no cutoff was pre-declared (002:33), and all three OOS samples are under n=100 (rs 40, lux 388, vol 25) — the 25-trade window fails even the relaxed n≥30 rule. The "no correction needed" waiver is invalid; cite 003 only as descriptive evidence.
3. **The closed ledger is not stable enough to support p-values.** Between 14:30 and 17:58 the 3,500-row `recent_closed` slice moved Σ PnL −469.52 → −574.12 and PF 0.92 → 0.903, and `picks.active_raw` resolved counts moved backward (SL_HIT 55→35, TP_HIT 25→22). The research numbers come from the 14:30 snapshot while the audit cites 16:15 — a provenance mismatch inside one archive.
4. **ITERATION-002's cleaning step is arithmetically wrong and its seed table is misleading.** 3,500−23≠3,488; 12 pnl=0 is really 11; there are no `status=UNKNOWN` rows; 9/14 PF<1 is really 7/14; and the `forex_rsi2` "PF 1.645" seed is PF 0.860 in the policy-clean registry.
5. **Our own H10 review has the same drift and must be reconciled before publishing.** `STATS_REVIEW_H10` (1.8452 / 0.9789 / 0.001802 / 1.6834 / boot 1.2757) ≠ committed `results.json` (1.8322 / 0.9776 / 0.001941 / 1.6596 / 1.2690); the PBO headline 0.106 is OOS-only and full-sample all-12 is 0.417. Neither changes `NOT PROVED`, but the docs must name one frozen artifact set.

---

## Appendix A — Reproduction notes

- Peer numbers were recomputed from the public artifacts named in §2; no network calls were needed beyond the already-downloaded payloads.
- `pf_registry.json` aggregate PF is computed as Σ`gross_profit` / Σ`gross_loss` over `by_asset_class_strategy_policy_clean_net` (683 rows) and over `by_asset_class_policy_clean_net` (9 rows).
- One-sided p for a t-statistic uses the normal approximation `0.5·erfc(t/√2)`; scipy was available for the same check.
- 70/30 splits sort candidate rows by `closed_at` and cut at `floor(0.70·n)`; this reproduces 93/40, 902/388, 56/25 exactly.
- Duplicate groups use the key `(symbol, direction, closed_at-date, strategy)` as in the peer audit.
- Snapshot comparison used `generated_at` 2026-11-14T14:30:07.135931+00:00 and 2026-11-14T17:58:53.402962+00:00.
- No repository source file was modified by this review; only this report was written.
