# FP6 — Final-Stage Review of Peer `final_v2/` Packages

**Reviewer:** FP6
**Clock:** 2026-11-14T21:25Z
**Root:** `/home/eaguiar2015/findtorontoevents_antigravity.ca`
**Mode:** read-only on repo source, data, and peer artifacts. The only file written is this report.
**Method:** peer trees read from `origin/main` with `git ls-tree` / `git show` (no checkout over the
working tree). `origin/main` was fetched immediately before review. Our baseline was read from the
local worktree `final_v2/finpredict-v2/` (untracked; **not on `origin/main`**).

**Baseline compared against:** `01_audit/MASTER_AUDIT.md`, the eight
`02_per_asset_class_profitability/*.md` files, `05_final/reference_final_2026_11_14/FINAL_SYNTHESIS.md`,
`PEER_CLAIMS_MATRIX.md`, `01_audit/recommendations/overall/{ROADMAP,DATA_CONTRACT,CI_GATES}.md`, and
`04_peer_reviews/FP1–FP5`.

---

## 0. Coverage verdict — PASS for the named folders, FAIL for reproducibility and safety

| Coverage item | Verdict | Basis |
|---|---|---|
| Named peer folders exist on `origin/main` | **PASS** | `final_v2/{finpredict,finpredict-v3,flaxen-hair}` all present |
| Every file in the three named folders read | **PASS** | 3 + 5 + 17 = 25 files; all `.md` read; the one `.py` inspected for the DSR defect |
| Inventory / purpose / verdict per folder | **PASS** | §1 |
| Unique per-asset ideas extracted and classified | **PASS** | §2 |
| Every new profitability claim traced to a source | **PASS with caveats** | §3; several are literature priors, not measurements |
| Claims reproducible **from the `final_v2` package itself** | **FAIL** | `finpredict` and `finpredict-v3` ship summaries only; `flaxen-hair` ships code but no data; only the extra `quant-audit` folder ships scripts + console + JSON |
| Peer references to our work accurate | **PARTIAL** | §5; paths correctly point to the older `final_2026_11_14/finpredict-v2`, not our unpublished `final_v2`; two stale peer references (childlike-airport "on main"; ML leakage "fixed") |
| No dangerous/destructive recommendations | **FAIL** | `flaxen-hair` recommends `production_enable=true` for mega_mutation and adding a `MUTUAL_FUND` class (§4) |

**Additional folder discovered on `origin/main` after the brief was written:** `final_v2/quant-audit-2026-11-14/`
(commit `681f2fe6cbb`, 2026-11-14 21:18:54Z, 16 files). It is outside the three-folder brief but was
sampled because it reviews our work and contains the strongest new measurement in the set. It is
reported separately in §1.4 and its unique items are included in §2.

**Commit/clock facts**

| Folder | Commit | UTC time | Files | Bytes |
|---|---|---|---:|---:|
| `final_v2/finpredict` | `5bf4991e900` | 21:13:37 | 3 | 11,760 |
| `final_v2/finpredict-v3` | `cb346162f43` | 21:13:30 | 5 | 16,518 |
| `final_v2/flaxen-hair` | `ee8a6e20483` | 21:16:13 | 17 | 130,884 |
| `final_v2/quant-audit-2026-11-14` (extra) | `681f2fe6cbb` | 21:18:54 | 16 | — |

---

## 1. Per-folder inventory

### 1.1 `final_v2/finpredict/` — v1 correction + convergence + per-class roadmap

**Purpose:** accept the quant-audit correction to its own ITERATION-005 "PROVEN" claim, state the
convergent negative verdict, and give a short per-class profitability roadmap.

**Files:** `README.md`; `peer-review/FINAL_RECONCILIATION.md`; `per-asset-class/PROFITABILITY_ROADMAP.md`.

**Key findings / ideas**
- Explicitly withdraws the "PROVEN" label on diversified vol-targeted trend: t=5.56 tested absolute
  return > 0, not > buy-and-hold; the same 10 assets' B&H Sharpe was ≈2.2 vs the strategy's 2.13;
  PF 1.40 is a bar ratio that fails its own PF>1.5 gate; the window was bull-flattered.
- Corrected claim: trend is a credible **risk-premium harvest** with regime-dependent Sharpe 0.5–2.1;
  benchmark-relative alpha unproven (`README.md` §1).
- All peer surfaces converge on 0/166 cells money-ready, negative class-level WR/PF, −1.42% live open
  P&L, and `money_ready_verdict=[]` (`README.md` §2).
- Per-class roadmap: CRYPTO trend + carry; EQUITY/ETF diversified factor portfolio; FOREX carry +
  trend; FUTURES CTA trend with a real feed; BOND duration/trend + carry; COMMODITY real curve feed;
  MUTUAL FUNDS de-advertise (`PROFITABILITY_ROADMAP.md`).
- Recommends closing the research→production gap with one clean sleeve per class, measured
  excess-of-benchmark, and enabling `_FDR_GATE_ENFORCE` / `_SINGLE_SOURCE_GATE_ENFORCE`.

**Verdict:** agrees with ours on FAIL / not money-ready / no proven benchmark-relative alpha. The
main residual overstatements are "short-term reversal (weak)" as a crypto premium and "0 closed ever"
for FUTURES; both are contradicted by our evidence (§4).

### 1.2 `final_v2/finpredict-v3/` — per-class reality + peer adjudication + proposals

**Purpose:** re-derive the honest per-class picture, adjudicate the VWAP dispute and the trend claim,
and propose a small portfolio of 2–4 risk-premium strategies.

**Files:** `00_INDEX.md`; `01_profitability_per_asset_class/PROFITABILITY_PER_ASSET_CLASS.md`;
`02_peer_reviews/FINAL_PEER_ADJUDICATION.md`; `03_ideas_proposals/IDEAS_PROPOSALS.md`;
`04_evidence/EVIDENCE_MANIFEST.md`.

**Key findings / ideas**
- Correctly rejects the VWAP 3.76 claim: annualization error → real Sharpe ≈1.18; proper CSCV PBO
  0.84–0.97; intrabar PF 0.81 (`02_peer_reviews/FINAL_PEER_ADJUDICATION.md:27-34`).
- Adjudicates ITERATION-005 as "best genuine edge candidate" but "risk premium, not alpha"; B&H of
  the same 10 ≈2.2; TSMOM365 OOS 0.57, null p=0.200 (`:36-47`).
- Per-class states: CRYPTO WR 35.9% / PF 0.92 (n=4,907 intrabar); EQUITY 59.2% / 0.94; FOREX 32.2% /
  0.66 (n=82); ETF PF 1.836 (n=15); FUTURES n=52 PF 1.09; BOND n=3 PF 0.0; MUTUAL FUNDS unbuilt.
- Proposes: CRYPTO vol-targeted trend, ETF multi-asset trend, BTC funding/carry sleeve,
  `universal_price_enricher` wired into the build, a horizon-harness release gate, a unified data
  contract, and an optional VWAP re-test.

**Verdict:** mostly agrees with our negative verdict and adds a useful implementation item
(`universal_price_enricher`) and a concrete release-gate definition. However, its own `00_INDEX.md`
says "**Real profitable signal families found**" and lists "regime-filtered mean-reversion", which
directly contradicts its own VWAP adjudication and our FALSIFIED verdict (§4).

### 1.3 `final_v2/flaxen-hair/` — mega_mutation promotion case + copied finpredict-v4 research

**Purpose:** argue that `mega_mutation_macd_rsi` / `ema_momentum` is the only forward-validated edge,
copy the finpredict-v4 6-gate framework and TradingView contest research, and give a 4-phase
execution plan.

**Files (17):** `README.md`; `01_asset_class_profitability_ideas/PROFITABILITY_IDEAS.md`;
`02_peer_work_review/{PEER_REVIEW_SYNTHESIS.md,finpredict_profitable_scoring_framework.md,
finpredict_statistical_scoring_framework.py,finpredict_tradingview_contest_research.md}`;
`03_root_repo_review/{README.md,ROOT_REPO_REVIEW.md,HYPOTHESES.md,VERDICT.md,SCORECARD.md,
VWAP_VERDICT.md,PROTOCOL_v4.md}`; `04_profitability_strategies/PROFITABILITY_STRATEGIES.md`;
`05_risk_management/RISK_MANAGEMENT.md`; `06_execution_plan/EXECUTION_PLAN.md`;
`07_summary_recommendations/SUMMARY_RECOMMENDATIONS.md`.

**Key findings / ideas**
- Claims mega_mutation forward n=50, WR 84%, PF 8.32; `production_enable=true`,
  `promotion_ready=true` (`README.md:25-34`; `07_summary_recommendations/SUMMARY_RECOMMENDATIONS.md:7,24`).
- Repeats the 23-candidate research program as "root repo review" and correctly reports 0 proved,
  H10 NOT_PROVED, VWAP FALSIFIED.
- Copies the 6-gate scoring framework; the Python implementation at
  `02_peer_work_review/finpredict_statistical_scoring_framework.py:169-203` still feeds an annualized
  Sharpe into a per-period standard error, the exact defect our FP5 identified (SR 0.50 → DSR 1.0000
  instead of 0.0241).
- Proposes bond-ETF TSMOM, mutual-fund dual momentum (and adding `MUTUAL_FUND` to `config.py`),
  FX mean reversion, commodity TSMOM/seasonality, TradingView winner symbols / 14:00Z–21:00Z windows,
  and heterogeneous ML stacking.

**Verdict:** **FAIL on the positive claim.** The negative material it copies is consistent with ours,
but its headline is the same mega_mutation claim our FP1 falsified as "proven" (42% of the n=50
forward set is `created_at=NULL` synthetic/replay; selection 8-of-33,000; no costs; strict TP n=16
PF 5.19). Its promotion recommendation is the most dangerous item in the peer set.

### 1.4 Extra: `final_v2/quant-audit-2026-11-14/` — measured per-class mechanics (out of brief)

**Purpose:** a second pass that measures per-class breakeven, stop-fill fidelity, cost share, and
R-multiples on the live 3,500-row `recent_closed` payload.

**Key findings**
- **Stop-fill slippage is the mechanism behind the crypto loss:** planned risk 1.919%, realized
  2.990% (+1.071pp/trade); total overshoot +828.0pp vs class total −837.8pp = **98.8% of the crypto
  loss**; same signals filled at the stop would move PF 0.768 → ≈1.00 (`README.md:44-60`;
  `03_ideas_ranked/RANKED_IDEAS.md:12-25`).
- **170 benchmark ledgers → 4 pass at 95% vs 8.5 expected by chance** — fewer than chance; the
  cleanest negative statement in the peer set (`01_peer_reviews/finpredict_v2.md:13`).
- Per-class table: CRYPTO PF 0.768/−837.8pp; EQUITY 1.154/+238.3pp (t=1.52, p=0.12); ETF 1.036/+22.9pp;
  FOREX 0.634; BOND 0.586; COMMODITY 0.604; ALL 0.895/−617.5pp (`00_executive_summary/README.md`).
- Cost gate: average slippage as share of average PnL — ETF 267%, COMMODITY 422%, CRYPTO 39.7%
  (`03_ideas_ranked/RANKED_IDEAS.md:25-33`).
- Exit mix drives class PF; TIME_EXIT is the best bucket, FORCE_CLOSED is noise; use R-multiples,
  not PF, for cross-class ranking (`02_per_asset_class/ANALYSIS.md:49-64`).
- **Two self-corrections that correct us too:** (1) `resolution_method` is not the right field;
  `exit_reason` is populated (SL_HIT 1,468 / TP_HIT 873 / FORCE_CLOSED 615 / TIME_EXIT 517 /
  UNKNOWN 22 / EXPIRED 5); (2) the 100× PnL-unit error does **not** exist in the 3,500-row dashboard
  ledger — 3,500/3,500 reproduce within 0.05pp; it is real in `multi_asset_closed.json` and the MySQL
  store (`README.md:32-42`).

**Verdict:** **agrees with ours (no class profitable)** and contributes the strongest new *measurement*
(not edge). It cannot have reviewed our `final_v2` because ours is not on `origin/main`; it reviews
our earlier `MASTER_AUDIT.md` and rates it CONFIRMED (`01_peer_reviews/finpredict_v2.md:3-19`).

---

## 2. Unique per-asset-class ideas and fixes — ADOPT / MERGE / REJECT / ALREADY_COVERED

`ADOPT` = new, high-value, add directly. `MERGE` = overlaps but adds a concrete variant/detail; fold
into the named section. `ALREADY_COVERED` = substantively present; cite as corroboration.
`REJECT` = contradicted, unsafe, or an unregistered trial with no basis.

| # | Class | Idea / fix (exact source) | Class. | Target in our `final_v2` | Why |
|---:|---|---|---|---|---|
| 1 | CRYPTO | Stop-fill slippage: 98.8% of crypto loss is stops filling 56% worse than placed; replay with intrabar fill-at-stop (`quant-audit-2026-11-14/README.md:44-60`, `03_ideas_ranked/RANKED_IDEAS.md:9-25`) | **ADOPT** | `02_per_asset_class_profitability/CRYPTO.md` new §1.4 + `05_final/FINAL_SYNTHESIS.md` new C6 | New mechanism; our docs discuss intrabar stops for VWAP but never quantify the live stop-fill overshoot. It changes the diagnostic, not the verdict. |
| 2 | Cross-class | 170-ledger benchmark: 4 pass at 95% vs 8.5 expected by chance (`quant-audit-2026-11-14/01_peer_reviews/finpredict_v2.md:13`; `README.md` status) | **ADOPT** | `05_final/FINAL_SYNTHESIS.md` §5 + `PEER_CLAIMS_MATRIX.md` new row | Independent, sharper negative than "32.9 expected FP at N=658"; uses a different artifact (`benchmark_ledger_proof.json`). |
| 3 | Cross-class | Cost gate: do not emit a pick whose class average PnL is under 3× round-trip cost (`quant-audit.../03_ideas_ranked/RANKED_IDEAS.md:25-33`) | **ADOPT** | `01_audit/recommendations/overall/CI_GATES.md` new G14; mirrored in ETF/FOREX/BOND pages | Concrete, falsifiable gate; ETF (267%) and COMMODITY (422%) fail outright. |
| 4 | Cross-class | `universal_price_enricher` wired into the build; `UNQUOTED` instead of fabricated 0% (`finpredict-v3/03_ideas_proposals/IDEAS_PROPOSALS.md:33-38`) | **ADOPT** | `05_final/FINAL_SYNTHESIS.md` §7 C4 + `DATA_CONTRACT.md` §2.2 | Names the existing producer; our C4 is currently tool-agnostic. |
| 5 | CRYPTO | CRYPTO POSITION bucket n=33, WR 69.7%, PF 3.18 → forward test at n≥100; kill CRYPTO SWING n=243, PF 0.457 (`quant-audit.../02_per_asset_class/ANALYSIS.md:103-114`; `03_ideas_ranked/RANKED_IDEAS.md:75-83`) | **ADOPT** | `CRYPTO.md` §3 new C-6 (forward candidate) + §5 kill list | Cheap, pre-registered, and correctly framed as undersampled; the SWING kill removes 39% of the class loss. |
| 6 | Cross-class | Report R-multiples and exit mix; do not rank classes by PF from `recent_closed` (`quant-audit.../02_per_asset_class/ANALYSIS.md:49-64,66-84`) | **ADOPT** | `FINAL_SYNTHESIS.md` §5/§8; EQUITY/ETF/FOREX/BOND evidence sections | PF is mechanically tied to exit composition (TP_HIT 99.9% wins). Our per-class docs already use multiple surfaces but do not state this ranking rule. |
| 7 | Cross-class | `exit_reason` is populated; `resolution_method` was the wrong key; PnL units are consistent in the 3,500-row dashboard ledger (`quant-audit.../README.md:32-42`) | **ADOPT (correction)** | `FINAL_SYNTHESIS.md` §5 C0/C1 + §7 step 2; `PEER_CLAIMS_MATRIX.md`; `FP5` erratum; `CRYPTO.md` §6.8; `EQUITY.md` §6.4 | Directly corrects our `resolution_method=None` and "every PnL claim invalid" statements. Must be fixed before the synthesis is used. |
| 8 | CRYPTO | 50d+200d trend blend, 20% vol target, 0.1% cost, 20–40 liquid pairs; measure paired bootstrap vs equal-weight B&H (`finpredict/per-asset-class/PROFITABILITY_ROADMAP.md:12`) | **MERGE** | `CRYPTO.md` C-4 | Close to H1/H6/H15 but a different signal blend; must be counted as a new trial and pre-registered, not assumed to be the same family. |
| 9 | EQUITY | Combined momentum + value + quality + low-vol portfolio, equal-risk-weight across 50+ names, monthly (`finpredict/.../PROFITABILITY_ROADMAP.md:19`) | **MERGE** | `EQUITY.md` E2/E3/E4 (portfolio construction note) | Our docs test the factors separately; the combined portfolio is a legitimate construction variant. It still needs the same DSR/PBO/SPA gates. |
| 10 | Cross-class | Enable `_FDR_GATE_ENFORCE=1` and `_SINGLE_SOURCE_GATE_ENFORCE=1` (`finpredict/README.md` §2/§8) | **MERGE** | `FINAL_SYNTHESIS.md` §7 C2 | Our C2 says delete the off-switch; naming the exact env vars makes it implementable. |
| 11 | Cross-class | One clean sleeve per class + close the research→production gap (`finpredict/README.md` §2-3) | **MERGE (with sequencing)** | `FINAL_SYNTHESIS.md` §7 | Valid only after C0–C4; the peer's wording can be read as deploy-now. Keep our "no real-money sizing until C0–C4 green". |
| 12 | Cross-class | Horizon-harness release gate: n≥60, 95% CI excludes 50%, PF>1.05, win-majority ≥66%, multiple-testing-adjusted (`finpredict-v3/02.../FINAL_PEER_ADJUDICATION.md:69-70`) | **MERGE** | `FINAL_SYNTHESIS.md` §7 C2 + `patch_plan/acceptance_tests.md` | Already recommended by FP5; the exact thresholds are useful. Fix the `MIN_WINDOWS` bug FP5 found before adopting as a gate. |
| 13 | CRYPTO | Funding/carry sleeve capped at 10–15% of book (`finpredict-v3/03.../IDEAS_PROPOSALS.md:25-29`) | **MERGE** | `CRYPTO.md` C-1 / H24 risk sizing | Adds a book-level cap; keep the block-null and capital-adjusted gates. |
| 14 | BOND/ETF | Bond-ETF TSMOM on TLT/IEF/SHY/TBT (`flaxen-hair/01.../PROFITABILITY_IDEAS.md:96-100`) | **MERGE → ETF T3, reject as BOND** | `ETF.md` T3; `BOND.md` §2.2 | A bond ETF is a duration exposure, not a bond; our BOND page already says price momentum on a bond ETF is not a bond strategy. As an ETF trend sleeve it is covered by T3. |
| 15 | Cross-class | 6-gate structure (data → significance → walk-forward → gross → net → direction) (`flaxen-hair/02.../finpredict_profitable_scoring_framework.md`) | **MERGE (structure only)** | `FINAL_SYNTHESIS.md` §7 C2 | The structure is useful; the implementation is invalid (DSR saturates). Add per-period Sharpe, estimated `V`, PBO/CSCV, SPA, block bootstrap, N=658/683. |
| 16 | Cross-class | Unique pick-ID validator (`flaxen-hair/06.../EXECUTION_PLAN.md:29-32`) | **MERGE** | `FINAL_SYNTHESIS.md` §7 C3 | Complements our dedup/identity gate; do not adopt the peer's claimed "already done" status. |
| 17 | Cross-class | Retail risk envelope: 2% risk/trade, −5% daily, −20% monthly, Kelly 0.25–0.5×, 3-loss halt (`flaxen-hair/05_risk_management/RISK_MANAGEMENT.md`) | **MERGE (low priority)** | `FINAL_SYNTHESIS.md` §7 (risk envelope note) | Generic but sensible; not asset-class evidence. Do not let it imply the strategies are validated. |
| 18 | Cross-class | Cut trade count to T2 quality: n≥30 + PF≥1.2 at strategy level before emitting (`quant-audit.../03_ideas_ranked/RANKED_IDEAS.md:40-56`) | **MERGE** | `FINAL_SYNTHESIS.md` §7 C2 | Consistent with our kill/keep plan; adds a monthly trade-count cap. |
| 19 | COMMODITY | CFTC COT contrarian at weekly frequency, using the existing `commodity_cot_contrarian` sidecar (`quant-audit.../PER_CLASS_PATHS_TO_PROFIT.md:96-104`; `RANKED_IDEAS.md:89-100`) | **MERGE** | `COMMODITY.md` CO-4 | Our CO-4 already covers hedging-pressure/COT; the sidecar and weekly gate are concrete. Include the over-emission guard. |
| 20 | EQUITY/ETF/FOREX/BOND | Quant-audit per-class evidence: EQUITY +2.9pp after-cost margin t=1.52; ETF slippage 267% of PnL; FOREX avg win 0.69 vs loss 0.76 and TP fills at ~0.5R; BOND n=35/no duration model (`quant-audit.../PER_CLASS_PATHS_TO_PROFIT.md`) | **MERGE** | `EQUITY.md` §1.3; `ETF.md` §1.3; `FOREX.md` §1.3/§2; `BOND.md` §1.3 | Additional surfaces from the same 3,500-row ledger; label the window and do not merge with policy-clean numbers. |
| 21 | Cross-class | Carry, factor, CTA, duration-rotation, real-commodity-feed paths (`finpredict/.../PROFITABILITY_ROADMAP.md:7-60`) | **ALREADY_COVERED** | `CRYPTO.md` C-1/C-4; `EQUITY.md` E1–E4; `FOREX.md` H-FX-1..3; `FUTURES.md` F-1/F-2; `BOND.md` H-BD-1/3; `COMMODITY.md` CO-1/CO-2 | Same documented premia, generally with less detail than our pages. Cite as corroboration. |
| 22 | All classes | finpredict-v3's per-class plan (fundamental factor, market-neutral, PEAD, ETF trend/risk parity, bond carry, FX trend, futures roll, MF not built) (`finpredict-v3/01.../PROFITABILITY_PER_ASSET_CLASS.md`) | **ALREADY_COVERED** | `EQUITY.md` E1–E4; `ETF.md` T1–T3; `BOND.md` H-BD-1/3; `FOREX.md` H-FX-1/2; `FUTURES.md` F-1; `MUTUAL_FUNDS.md` §7 | Our pages are more precise about gates, data, and failure modes. |
| 23 | CRYPTO/EQUITY | H10 RSI(2) clean forward test; funding carry as a capital-capped sleeve (`flaxen-hair/01.../PROFITABILITY_IDEAS.md:27-49,62-70`) | **ALREADY_COVERED** | `EQUITY.md` §1.2; `CRYPTO.md` C-1/H24 | Our own v2 already produced H10 and downgraded it; our CRYPTO page already treats carry as capital-marginal. |
| 24 | Cross-class | "Do not add mutual fund coverage"; "do not trust PF from `recent_closed`"; "test EQUITY vs SPY" (`quant-audit.../03_ideas_ranked/RANKED_IDEAS.md:140-146`) | **ALREADY_COVERED** | `MUTUAL_FUNDS.md` §6/§7; `FINAL_SYNTHESIS.md` §5/§8; `EQUITY.md` §7 | Same conclusions; use as independent corroboration. |
| 25 | CRYPTO | "Short-term reversal (weak)" as a real premium (`finpredict/.../PROFITABILITY_ROADMAP.md:9`) | **REJECT** | `CRYPTO.md` C-M6 / H14 | H14 OOS Sharpe −0.36, CAGR −44.3%; C-M6 is "likely absent". The peer offers no new evidence. |
| 26 | Cross-class | "Real profitable signal families found ... regime-filtered mean-reversion" (`finpredict-v3/00_INDEX.md:19-21`) | **REJECT** | `FINAL_SYNTHESIS.md` §4 (new contradiction note) | Contradicts the same folder's VWAP refutation (`:22-24`) and our FALSIFIED verdict. "Profitable" is not supported by any proof gate. |
| 27 | CRYPTO | Adopt vol-targeted trend as "the first real profitable strategy"; funding/carry sleeve as an income stream (`finpredict-v3/02.../FINAL_PEER_ADJUDICATION.md:61-65`) | **REJECT (as a proof/deployment claim)** | `FINAL_SYNTHESIS.md` §4.7 + `CRYPTO.md` §3 | Correct as a `PILOT` candidate, wrong as "real profitable". The peer's own adjudication says it is a risk premium, not alpha. |
| 28 | CRYPTO | mega_mutation `production_enable=true`, `promotion_ready=true`, paper→live after n=100 (`flaxen-hair/README.md:25-34`; `07.../SUMMARY_RECOMMENDATIONS.md:7,24`; `06.../EXECUTION_PLAN.md:44-52`) | **REJECT — DANGEROUS** | `FINAL_SYNTHESIS.md` §4.8; `PEER_CLAIMS_MATRIX.md` row 5 update | FP1: 21/50 "forward" rows are synthetic/replay; 8 winners from 33,000; 13/24 TP_HIT never reached TP; strict OOS n=16 PF 5.19; no costs. Quant-audit's 170-ledger artifact scores the sibling m006 at PF 0.767. Do not enable. |
| 29 | MUTUAL FUNDS | Add `MUTUAL_FUND` to `config.py` / build NAV dual-momentum (`flaxen-hair/01.../PROFITABILITY_IDEAS.md:110-115`; `04.../PROFITABILITY_STRATEGIES.md`) | **REJECT — DANGEROUS** | `MUTUAL_FUNDS.md` §6.1/§7; `MASTER_AUDIT.md` §10 veto | Re-opens the vacuous-PASS class, adds a permanently n=0 tile, and a T+1 NAV instrument cannot support intraday TP/SL. Our explicit veto stands. |
| 30 | FOREX | Mean reversion RSI(2)<30 on major pairs (`flaxen-hair/01.../PROFITABILITY_IDEAS.md:123-127`) | **REJECT** | `FOREX.md` §2/§3 | Not one of the four surviving FX families; adds a trial on a class whose policy-clean sample is significantly negative (WR 35.62%, z −6.02). |
| 31 | Cross-class | Decimal-ratio PnL normalization (`flaxen-hair/06.../EXECUTION_PLAN.md:19-24`; `02.../finpredict_statistical_scoring_framework.py`) | **REJECT** | `DATA_CONTRACT.md` §3; `QUICK_WINS.md` | Our FP5: percent-at-write, `pnl_source`, recompute-or-NULL; the ratio convention silently turns +150% into 1.5%. |
| 32 | Cross-class | TradingView winner symbols / 14:00Z–21:00Z entry windows (`flaxen-hair/02.../finpredict_tradingview_contest_research.md:110-122`) | **REJECT** | `FINAL_SYNTHESIS.md` §4.6; `PEER_CLAIMS_MATRIX.md` row 16 | Descriptive, outcome-selected (155 WON rows, no loser control); time cluster is likely resolver/cron batching; adds 8 symbols × 2 windows as unregistered trials. |
| 33 | Cross-class | Heterogeneous stacking (LightGBM + GRU + Ridge) and prediction tail clipping (`flaxen-hair/06.../EXECUTION_PLAN.md:85-100`) | **REJECT (out of scope)** | — | No asset-class evidence, no gate, and it adds model-selection trials. Could be a future note in `NEXT_DATA_REQUIREMENTS.md`, not a profitability fix. |
| 34 | Cross-class | "All other asset classes negative (PF 0.18–0.31)" (`flaxen-hair/README.md:36-38`; `07.../SUMMARY_RECOMMENDATIONS.md:28-38`) | **REJECT (factually wrong)** | `FINAL_SYNTHESIS.md` §4.8 | The 3,500-row `recent_closed` ledger has EQUITY PF 1.154 (+238.3pp) and ETF 1.036 (+22.9pp); the 0.18–0.31 range is a different policy-clean/quick-win surface. |
| 35 | FUTURES | "0 closed ever" (`finpredict/.../PROFITABILITY_ROADMAP.md:32`) | **REJECT (factual error)** | `FUTURES.md` §1.2 (already correct) | There are 0 rows in `picks.recent_closed`, but n=13 policy-clean and n=52 intrabar exist. The peer's own FP5 reconciliation knew this. |

---

## 3. New profitability claims — sourced? reproducible? status vs our matrix

Legend: `VERIFIED` = reproduced from a named artifact; `VERIFIED NEGATIVE` = a negative finding
reproduced; `PARTIAL` = some numbers traceable, interpretation not; `UNVERIFIED` = no artifact in the
package; `CONTRADICTED` = conflicts with the underlying data; `OVERSTATED` = headline exceeds evidence.

| # | Claim | Source | Sourced? | Reproducible from `final_v2` package? | Status vs `PEER_CLAIMS_MATRIX` |
|---:|---|---|---|---|---|
| 1 | Diversified vol-targeted trend is a credible risk-premium harvest; Sharpe 0.5–2.1; alpha unproven | `finpredict/README.md` §1 | Yes (ITERATION-005 + quant-audit re-run) | No — summary only; the run lives in the older `final_2026_11_14/finpredict` tree | **PILOT / NOT_PROVED** — matches matrix row 14; keep the `PILOT` label |
| 2 | Funding-rate carry is "real but capacity-limited", ~4.8% vs 4.5% cash | `finpredict/.../PROFITABILITY_ROADMAP.md:9`; `README.md` §2 | Yes (v4 H21–H23) | No — summary only | **PARTIAL** — nominal economics exist; block-null p=1.000 (quant-audit) and capital-adjusted return is below cash. Do not headline as "real edge" |
| 3 | Short-term reversal is a weak real premium | `finpredict/.../PROFITABILITY_ROADMAP.md:9` | No new artifact | No | **CONTRADICTED** — H14 Sharpe −0.36, CAGR −44.3%; C-M6 "likely absent" |
| 4 | Per-class realistic Sharpe bands (EQUITY 0.4–0.8; FOREX 0.3–0.6; FUTURES 0.5–1.0; BOND 0.3–0.6; COMMODITY 0.3–0.7) | `finpredict/.../PROFITABILITY_ROADMAP.md` | Literature priors, not measurements | No | **UNVERIFIED** — planning estimates; label them as such, not evidence |
| 5 | "Real profitable signal families found: TSMOM, funding/carry, regime-filtered mean-reversion" | `finpredict-v3/00_INDEX.md:19-21` | Partly (ITERATION-005, H21–H23) | No | **OVERSTATED / CONTRADICTED** — no proof gate; mean-reversion contradicts the same folder's VWAP refutation |
| 6 | CRYPTO WR 35.9% / PF 0.92 (n=4,907 intrabar) | `finpredict-v3/04_evidence/EVIDENCE_MANIFEST.md` | Yes (prior audit) | No — manifest links only | **VERIFIED** — matches our `money_ready_verdict` intrabar surface (35.87% / 0.92) |
| 7 | EQUITY WR 59.2% / PF 0.94 (n=250 intrabar); ETF PF 1.836 (n=15); FUTURES n=52 PF 1.09; BOND n=3 PF 0.0 | same | Partly | No | **PARTIAL/VERIFIED** — EQUITY/ETF/FUTURES match our surfaces; FOREX n=82 and BOND n=3 are different populations from our policy-clean n=438/n=1 |
| 8 | Horizon harness 0/6 groups at n≥60, 0/26 at n≥30 | `finpredict-v3/04_evidence/EVIDENCE_MANIFEST.md:9-12` | Yes (tool + output) | No — output not in the package | **VERIFIED NEGATIVE** — our FP5 reproduced 0/6 and 0/26 |
| 9 | mega_mutation forward n=50, WR 84%, PF 8.32; "statistically valid"; production enabled | `flaxen-hair/README.md:25-34`; `07.../SUMMARY_RECOMMENDATIONS.md:7,24` | Headline reproduces from MySQL | No — no DB extract in the package | **OVERSTATED / NOT_PROVED** — FP1 reproduced the headline but 21/50 are synthetic/replay, 8/33,000 selection, 13/24 TP_HIT never reached TP; strict n=16 PF 5.19. Matrix row 5 stands |
| 10 | H10 RSI(2)+cash: Sharpe 1.83, CAGR 22.0%, DSR 0.978 at N=12 | `flaxen-hair/03_root_repo_review/VERDICT.md` | Yes (our v2) | No | **NOT_PROVED** — our own adversarial review already downgraded it (effective N≈38 DSR 0.9365, ex-best-day 0.8993, 2-day lag 0.696) |
| 11 | Funding carry DSR 1.0 | `flaxen-hair/03_root_repo_review/SCORECARD.md`; `04.../PROFITABILITY_STRATEGIES.md` | Yes (v4) | No | **ARTIFACT/UNVERIFIED** — nominal DSR; block-null p=1.000 (peer-reported), capital-adjusted below cash |
| 12 | 6-gate framework can certify edges | `flaxen-hair/02.../finpredict_profitable_scoring_framework.md` + `.py` | Code exists | Code only, no data | **INVALID AS IMPLEMENTED** — `.py:169-203` feeds an annualized Sharpe into a per-period SE; SR 0.50 → DSR 1.0000 instead of 0.0241; `V=0`; no PBO/CSCV/SPA |
| 13 | TradingView winners are predictive / copyable | `flaxen-hair/02.../finpredict_tradingview_contest_research.md` | Internal counts verify; external leaderboard unarchived | No | **DESCRIPTIVE / UNVERIFIED EXTERNALLY** — matrix row 16 |
| 14 | "All other classes negative (PF 0.18–0.31)" | `flaxen-hair/README.md:36-38` | No (surface unstated) | No | **CONTRADICTED** — `recent_closed` EQUITY 1.154, ETF 1.036 |
| 15 | Stop-fill slippage = 98.8% of crypto loss; PF 0.768 → ≈1.00 if filled at the stop | `quant-audit.../README.md:44-60`; `03_ideas_ranked/RANKED_IDEAS.md:12-25` | Yes (script + console) | **Yes** — `04_verification/*.py`, `05_evidence/*` | **VERIFIED NEGATIVE / NEW MECHANISM** — not a profitability claim; it is a measurement defect. Add to matrix as a new negative row |
| 16 | 170 benchmark ledgers → 4 pass at 95% vs 8.5 expected | `quant-audit.../01_peer_reviews/finpredict_v2.md:13` | Yes (`benchmark_ledger_proof.json`) | **Yes** | **VERIFIED NEGATIVE** — stronger than our N=658 expected-FP statement |
| 17 | EQUITY is the only class above its after-cost breakeven (+2.9pp), but t=1.52 (p=0.12) | `quant-audit.../00_executive_summary/README.md:28`; `PER_CLASS_PATHS_TO_PROFIT.md:40` | Yes (script) | **Yes** | **VERIFIED, NOT SIGNIFICANT** — candidate only; matches our EQUITY "not a robust edge" |
| 18 | "No asset class is profitable after costs; no class is sizing-allowed" | `quant-audit.../00_executive_summary/README.md` | Yes | **Yes** | **VERIFIED NEGATIVE** — agrees with our 0/9 money-ready verdict |

**Bottom line on claims:** no positive profitability claim in the peer `final_v2` set is both sourced
and reproducible to a proof gate. The strongest new material is negative: stop-fill slippage, the
170-ledger benchmark, and the per-class R-multiple/cost analysis. The only positive candidate that
survives as a *candidate* is the vol-targeted trend sleeve, already labelled `PILOT` in our matrix.

---

## 4. Contradictions with our verdict and dangerous recommendations

### 4.1 Contradictions

| # | Peer claim | Our position | Evidence | Severity |
|---:|---|---|---|---|
| 1 | "Real profitable signal families found" (`finpredict-v3/00_INDEX.md:19-21`) | No proven edge; 23 candidates, 0 proved; live system 0/9 money-ready | Our FINAL_SYNTHESIS §1/§3/§6; MASTER_AUDIT §5; this folder's own VWAP refutation at `:22-24` | **High** — a reader who stops at the index line would believe profitability is established |
| 2 | "Adopt CRYPTO vol-targeted trend as the first real profitable strategy" (`finpredict-v3/02.../FINAL_PEER_ADJUDICATION.md:61-63`) | Trend is `PILOT`; B&H of the same 10 ≈2.2 vs 2.13; PF 1.40 is a bar ratio; independent TSMOM365 OOS 0.57, null p=0.200 | FINAL_SYNTHESIS §4.6; FP5 §2 C9; CRYPTO.md C-4 | **High** — deployment framing, not just research |
| 3 | "Regime-filtered mean-reversion" is a real profitable family (`finpredict-v3/00_INDEX.md:19-21`) | VWAP mean reversion is FALSIFIED (Sharpe ~1.18, t=0.91, intrabar PF 0.81, CSCV PBO 0.84–0.97) | FINAL_SYNTHESIS §4.1; VWAP_VERDICT; same folder `:22-24` | **High** — internal self-contradiction |
| 4 | "Short-term reversal (weak)" as a real crypto premium (`finpredict/.../PROFITABILITY_ROADMAP.md:9`) | Likely absent; H14 Sharpe −0.36, CAGR −44.3% | CRYPTO.md §1.1, C-M6 | **Medium** |
| 5 | mega_mutation `production_enable=true`, promotion-ready (`flaxen-hair/README.md:25-34`) | NOT_PROVED; do not enable; 21/50 synthetic; 8/33,000 selection; no costs; strict n=16 PF 5.19 | FP1 §3–§8; quant-audit 170-ledger m006 PF 0.767 | **Critical** |
| 6 | "All other classes negative (PF 0.18–0.31)" (`flaxen-hair/README.md:36-38`) | EQUITY 1.154/+238.3pp and ETF 1.036/+22.9pp on `recent_closed`; still not statistically established | quant-audit ANALYSIS §1; our EQUITY/ETF pages | **Medium** — wrong surface, not a safe comparison |
| 7 | Add `MUTUAL_FUND` / build NAV dual momentum (`flaxen-hair/01.../PROFITABILITY_IDEAS.md:110-115`) | Do not add; `NOT_BUILT`; re-opens vacuous PASS; T+1 NAV cannot support TP/SL | MUTUAL_FUNDS.md §6.1/§7; MASTER_AUDIT §10 veto | **High** |
| 8 | Bond-ETF TSMOM as a bond strategy (`flaxen-hair/01...:96-100`) | A bond ETF has no coupon/roll-down/maturity; price momentum on it is not a bond strategy | BOND.md §2.2 | **Medium** |
| 9 | 6-gate framework certifies edges (`flaxen-hair/02...`) | Invalid as implemented: DSR saturates at 1.0; `V=0`; no PBO/SPA | FP5 §4.2; `.py:169-203` | **High** — a false-certification layer |
| 10 | "0 closed ever" for FUTURES (`finpredict/.../PROFITABILITY_ROADMAP.md:32`) | 0 rows in `picks.recent_closed`, but n=13 policy-clean and n=52 intrabar exist | FUTURES.md §1.2; MASTER_AUDIT §10 correction #4 | **Low/medium** — population error |

### 4.2 Dangerous or destructive recommendations

1. **`flaxen-hair` promotes an unproven strategy to live capital.** `production_enable=true`,
   `promotion_ready=true`, and a 4-phase plan that ends in "flip production_enable = true, allocate
   capital" (`06.../EXECUTION_PLAN.md:44-52`; `07.../SUMMARY_RECOMMENDATIONS.md:7,24`). This is the
   single most dangerous item in the peer set. The evidence is FP1-falsified and the peer's own
   copied research says 0/23 proved. **Veto: do not enable.**
2. **`flaxen-hair` re-opens the vacuous-PASS mutual-fund class.** "Add `MUTUAL_FUND` to
   `alpha_engine/config.py`" (`01.../PROFITABILITY_IDEAS.md:114`) contradicts our explicit veto and
   would create a permanently n=0 class that renders green. **Veto.**
3. **`flaxen-hair` enforces decimal-ratio PnL units.** `06.../EXECUTION_PLAN.md:19-24` says the unit
   fix is "already done — decimal ratio units enforced." Our FP5 and DATA_CONTRACT require
   percent-at-write; the ratio convention corrupts percent rows. **Reject the normalizer.**
4. **`finpredict-v3` recommends deploying trend and carry as "real profitable" sleeves.** The
   research is useful, but the label is an overclaim; deployment before C0–C4 and a clean forward
   OOS would repeat the original system's error. **Downgrade to `PILOT`; no capital.**
5. **`finpredict` recommends closing the research→production gap with one sleeve per class.** This is
   directionally right but must be sequenced after data truth; a naive reading deploys before C0–C4.
   **Keep our gate.**
6. **No destructive SQL in the three named `final_v2` folders.** `finpredict-v3`'s veto list still
   holds the line on `DELETE`/`UPDATE`/`INSERT OR REPLACE`. The extra `quant-audit` folder also uses
   read-only scripts. The danger here is deployment, not database destruction.

---

## 5. Do the peers reference our work correctly? Drift list

| # | Peer reference | What it says | Actual state | Drift / action |
|---:|---|---|---|---|
| 1 | `finpredict/peer-review/FINAL_RECONCILIATION.md:10` | `finpredict-v2` = `final_2026_11_14/finpredict-v2`; "most rigorous: 23 candidates NOT PROVED; falsified VWAP; funding carry capital-limited; PnL-unit bug" | Correct summary of our **older** archive; our `final_v2/finpredict-v2` is untracked and **not on `origin/main`** | **Path drift:** peers could not review our final_v2. State this in our synthesis; publish our folder before claiming peer coverage |
| 2 | `finpredict/.../FINAL_RECONCILIATION.md:14` | finpredict-v3 "ML leakage found (**fixed** on main `d8c8dd25581`)" | Our MASTER says the commit flipped leakage-masking default **ON** and still **needs review** | **Wording drift:** "fixed" is not established; keep "needs sign-off" |
| 3 | `finpredict-v3/02.../FINAL_PEER_ADJUDICATION.md:11` | `finpredict-v2` = reconciliation backbone; "best root causes (P0-1..9, Actions deep-dive)" | Correct for our older folder; no reference to our final_v2 | **Coverage drift**, not a factual error |
| 4 | `finpredict-v3/.../FINAL_PEER_ADJUDICATION.md:27` | "finpredict-v2 SCORECARD independently falsifies the same VWAP claim" | Correct (our `03_research/profitability/SCORECARD.md`) | **Accurate** |
| 5 | `finpredict-v3/04_evidence/EVIDENCE_MANIFEST.md:20` | "Confirmed childlike-airport final folder exists with 8 subfolders" | `origin/main` has **no** `final_2026_11_14/childlike-airport/` (only finpredict, finpredict-v2, finpredict-v3, flaxen-hair, hilarious-seer, quant-audit) | **Stale/unverifiable** — our FP5 already found this local-only |
| 6 | `finpredict-v3/.../EVIDENCE_MANIFEST.md:18` | PnL-unit mix: cites `.kilo/worktrees/flaxen-hair/quick_wins/shared/normalize_pnl_units.py`, 93 rows (47 ratio/32 percent/14 off) | The `.kilo/worktrees/...` path is not a tracked artifact on `origin/main`; the normalizer is the one FP5 calls unsafe | **Unverifiable path + unsafe fix** — do not adopt |
| 7 | `flaxen-hair/02_peer_work_review/PEER_REVIEW_SYNTHESIS.md:94` | `finpredict-v2_20261114-1602/` — "Actions deepdive, raw data, recommendations" | Correct archive copy; but flaxen does not engage with our final_v2 per-asset pages or our `NOT_PROVED` reconciliation | **Partial coverage / attribution drift** |
| 8 | `flaxen-hair/03_root_repo_review/{README,HYPOTHESES,VERDICT,SCORECARD}.md` | Presents `research/profitability/*` as "root repo review" | These files are our research program (the same 23 candidates); flaxen copies them without crediting finpredict-v2 | **Attribution drift** — not false, but our final_v2 pages are the more recent synthesis |
| 9 | `quant-audit.../01_peer_reviews/finpredict_v2.md:3-19` | Reviews our `MASTER_AUDIT.md`: **CONFIRMED**; calls our `CI_GATES`/`DATA_CONTRACT`/`ROADMAP` "the most implementable remediation set" | Accurate for the older folder; our final_v2 is not on main, so it could not review it | **Accurate, coverage gap** |
| 10 | `finpredict/.../FINAL_RECONCILIATION.md:36-37` | Roster: finpredict-v3 guardian 14 tests; finpredict-v4 destructive SQL vetoed; quant-audit 0/166; flaxen PnL units | All consistent with our FP4/FP5 inventory | **Accurate** |

**Net:** the peers reference our **older** `final_2026_11_14/finpredict-v2` correctly and treat it as
the reconciliation backbone. None references `final_v2/finpredict-v2` (it is not published). Two
references are stale/wrong (childlike-airport on main; "fixed" ML leakage), and one relies on an
untracked worktree normalizer.

---

## 6. Required edits to our `final_v2` synthesis (exact targets)

These are **corrections/additions required before our final_v2 is treated as the reference**. They do
not change our verdict; they correct two factual claims and add the strongest new measurements.

| # | Target | Change |
|---:|---|---|
| 1 | `05_final/reference_final_2026_11_14/FINAL_SYNTHESIS.md` §1 table, "Is there a real edge anywhere?" | Replace "**Only low-vol carry**" with: "**No proven risk-adjusted edge.** Nominal funding carry exists but is below cash after capital (3.7–4.8% vs 4.5%) and is not significant under a run-length-preserving block null (p=1.000)." (FP5 item 4, still unapplied.) |
| 2 | `FINAL_SYNTHESIS.md` §5 C0 and §1 "What should be done first?" | Scope the PnL-unit bug: the 17,632 percent / 6,306 fraction mismatch is in MySQL `at_signal_outcomes` and sidefiles (`multi_asset_closed.json`); the 3,500-row `recent_closed` dashboard ledger reproduces from entry/exit within 0.05pp on **3,500/3,500 rows** (quant-audit `README.md:38-42`). Keep canonical units as prevention, but do not say "every PnL claim is invalid". |
| 3 | `FINAL_SYNTHESIS.md` §4.6/§5 C1 and §7 step 2; `CRYPTO.md` §6.8; `EQUITY.md` §6.4 | Replace "`resolution_method` is `None` for 100% of the 3,500 rows" with: "`exit_reason` **is populated** (SL_HIT 1,468 / TP_HIT 873 / FORCE_CLOSED 615 / TIME_EXIT 517 / UNKNOWN 22 / EXPIRED 5). The missing piece is **fill fidelity**, not exit taxonomy: crypto stops fill 56% worse than placed." Add the stop-fill finding as the C1 rationale. |
| 4 | `FINAL_SYNTHESIS.md` §5 — new **C6 — stop-fill fidelity** | Add: planned crypto risk 1.919%, realized 2.990%; overshoot +828.0pp vs −837.8pp class total = 98.8% of the loss; replay stops against intrabar OHLCV, fill at stop, gap at bar close; gate median realized loss within 5% of planned. PF 0.768 → ≈1.00 is breakeven, not profit. Source: `final_v2/quant-audit-2026-11-14/README.md:44-60`. |
| 5 | `FINAL_SYNTHESIS.md` §5 — new **C7 — R-multiples and exit mix** | Add: class PF is mechanically driven by exit mix (TP_HIT 99.9% wins; TIME_EXIT best; FORCE_CLOSED noise); rank strategies on R-multiples, not cross-class PF. Source: `quant-audit.../02_per_asset_class/ANALYSIS.md:49-84`. |
| 6 | `FINAL_SYNTHESIS.md` §5/§6 — add the 170-ledger benchmark | Add: `benchmark_ledger_proof.json` evaluates 170 ledgers; 4 pass paired bootstrap at 95% vs 8.5 expected by chance. This is a second, independent negative alongside the 32.9-expected-FP-at-N=658 statement. Source: `quant-audit.../01_peer_reviews/finpredict_v2.md:13`. |
| 7 | `FINAL_SYNTHESIS.md` §4 — new §4.7 (finpredict-v3 overclaim) | Add: `finpredict-v3/00_INDEX.md:19-21` calls TSMOM, carry and regime-filtered mean-reversion "real profitable signal families"; this contradicts its own VWAP adjudication (`:22-24`) and our FALSIFIED/NOT_PROVED verdict. Label trend `PILOT`; carry `NOT_PROVED`; mean-reversion `FALSIFIED`. |
| 8 | `FINAL_SYNTHESIS.md` §4 — new §4.8 (flaxen final_v2) | Add: `flaxen-hair` re-asserts mega_mutation `production_enable=true` and "only statistically valid edge"; FP1 + quant-audit 170-ledger (m006 PF 0.767) contradict it. Keep production disabled. Also note the "all other classes negative PF 0.18–0.31" statement is false on `recent_closed` (EQUITY 1.154, ETF 1.036). |
| 9 | `FINAL_SYNTHESIS.md` §7 | Add to C2/C4: cost gate (average class PnL ≥ 3× round-trip cost; ETF/COMMODITY fail today); stop-fill replay gate; T2 trade-count cut (n≥30 + PF≥1.2 at strategy level); R-multiple reporting; `universal_price_enricher` wiring; horizon-harness thresholds (after fixing `MIN_WINDOWS`). |
| 10 | `FINAL_SYNTHESIS.md` §8 | Add: `final_v2/{finpredict,finpredict-v3,flaxen-hair}` were reviewed in FP6; `final_v2/quant-audit-2026-11-14` was discovered at 21:18Z and sampled; **our own `final_v2/finpredict-v2` is not on `origin/main`**, so no peer could review it. |
| 11 | `05_final/reference_final_2026_11_14/PEER_CLAIMS_MATRIX.md` | Update row 5 (mega_mutation) with the 170-ledger m006 PF 0.767 and the `production_enable=true` contradiction. Update row 14 (ITERATION-005) with "risk premium, alpha unproven" (already). Update row 17 (`resolution_method=None`) to `exit_reason populated / fill-fidelity defect`. Add rows: 18 finpredict per-asset roadmap (PARTIAL), 19 finpredict-v3 "real profitable families" (OVERSTATED), 20 flaxen `production_enable` (DANGEROUS/REJECT), 21 quant-audit stop-fill (VERIFIED NEGATIVE), 22 quant-audit 170-ledger (VERIFIED NEGATIVE), 23 quant-audit PnL-unit correction (VERIFIED). |
| 12 | `02_per_asset_class_profitability/CRYPTO.md` | Add §1.4 stop-fill; add C-6 CRYPTO POSITION forward test (n=33, PF 3.18) and kill CRYPTO SWING (n=243, PF 0.457); add the 50d+200d blend as a pre-registered C-4 variant; remove the `resolution_method=None` sentence at §6.8. |
| 13 | `02_per_asset_class_profitability/EQUITY.md` | Add quant-audit's +2.9pp after-cost margin / t=1.52 (p=0.12) as another surface; add the combined 4-factor 50+ name portfolio as an E2/E3/E4 construction variant. |
| 14 | `02_per_asset_class_profitability/ETF.md` | Add the cost gate and the 267%-of-PnL slippage figure; state that intraday ETF picks should stop (monthly horizon only). |
| 15 | `02_per_asset_class_profitability/FOREX.md` | Add the R:R inversion finding (avg win 0.69% vs loss 0.76%; TP_HIT fills at ~0.5R) and the n≥300 concentration warning. |
| 16 | `02_per_asset_class_profitability/BOND.md` | Add "declare BOND out of scope" as an explicit option; reaffirm that bond-ETF TSMOM is an ETF duration sleeve, not a bond strategy. |
| 17 | `02_per_asset_class_profitability/COMMODITY.md` | Add the `commodity_cot_contrarian` sidecar / weekly COT test, with the existing over-emission guard. |
| 18 | `02_per_asset_class_profitability/MUTUAL_FUNDS.md` | Add a note: `flaxen-hair` recommends adding `MUTUAL_FUND`; our veto stands. |
| 19 | `04_peer_reviews/FP5_peer_final_folders.md` | Append an erratum: (a) `resolution_method` was the wrong key — `exit_reason` is populated; (b) the PnL-unit bug is not in the 3,500-row dashboard ledger; (c) point to FP6 for the final_v2 peers. |
| 20 | `01_audit/MASTER_AUDIT.md` §10 | Add corrections #14–#16: stop-fill slippage; 170-ledger benchmark; `exit_reason` vs `resolution_method`; scope the PnL-unit claim. |

---

## 7. `UNVERIFIED` register

- **`finpredict` and `finpredict-v3` numbers are not reproducible from their `final_v2` packages.**
  Both ship summaries only; the run artifacts live in the older `final_2026_11_14/*` trees or in
  tools outside the package. The numbers may be correct (our FP4/FP5 reviewed much of the underlying
  work), but the `final_v2` deliverable alone does not carry the evidence.
- **`flaxen-hair` mega_mutation forward ledger.** The package has no DB extract. The headline was
  reproduced by FP1 from MySQL, but the exact `n=50` composition cannot be re-derived from the
  `final_v2` folder.
- **`flaxen-hair` "93 rows / 47 ratio / 32 percent / 14 off" PnL normalization.** The source is an
  untracked worktree file; the 93-row count was not re-queried here.
- **`flaxen-hair` TradingView external leaderboard figures.** No archived page, contest ID, or trade
  log; `UNVERIFIED` from this host.
- **`flaxen-hair` 6-gate framework's worked example numbers.** The document says n≈385/100; its own
  formula gives 783/194. The code's `minimum_sample_size()` is correct; the document is not.
- **`finpredict-v3` "childlike-airport final folder exists with 8 subfolders."** Not on `origin/main`;
  local-only per our FP5.
- **`finpredict-v3` cited `.kilo/worktrees/flaxen-hair/quick_wins/shared/normalize_pnl_units.py`.**
  Not a tracked artifact; the normalizer is unsafe (FP5/FP4).
- **`quant-audit` stop-fill and per-class numbers.** They ship the scripts and console output, but
  this review did not re-run them. `VERIFIED` here means "traceable to a committed script/output",
  not "independently recomputed by FP6".
- **`quant-audit` 170-ledger pass rate.** Read from the peer's review and `benchmark_ledger_proof.json`
  description; the JSON was not re-opened row-by-row here.
- **`finpredict` "funding carry is real."** Nominal economics are real; the risk-adjusted claim is
  not confirmed (block-null p=1.000 is peer-reported by quant-audit, not re-derived here).
- **Whether any peer saw our final_v2.** They could not: `git ls-tree origin/main final_v2/` lists only
  `finpredict`, `finpredict-v3`, `flaxen-hair`, and `quant-audit-2026-11-14`. Our folder is untracked
  in the worktree.

---

## 8. Top 6 findings

1. **Coverage PASS, reproducibility FAIL.** All 25 files in the three named peer folders were read,
   plus the extra `quant-audit` folder. The `final_v2` packages are mostly summaries: `finpredict`
   and `finpredict-v3` have no embedded run artifacts, and `flaxen-hair` has code but no data. Only
   `quant-audit` is self-contained (scripts + console + JSON).
2. **The strongest new finding is a measurement defect, not an edge.** Crypto stops are placed at a
   mean 1.919% risk and realize 2.990%; the +828.0pp overshoot is **98.8% of the −837.8pp crypto
   loss**. Filling at the stop moves PF 0.768 → ≈1.00 (breakeven). This must become our new C6 and a
   CRYPTO evidence section; it changes the diagnosis from "signal failure" to "fill fidelity".
3. **Two of our synthesis claims are factually wrong and must be corrected.** (a) `resolution_method`
   is the wrong key — `exit_reason` is populated (SL_HIT/TP_HIT/FORCE_CLOSED/TIME_EXIT/UNKNOWN/EXPIRED).
   (b) The 100× PnL-unit bug is **not** in the 3,500-row dashboard ledger (3,500/3,500 reproduce
   within 0.05pp); it is real in MySQL/sidefiles. Our C0/C1 wording and the `PEER_CLAIMS_MATRIX` row
   need scoping.
4. **The peer positive claims remain unproved, and one is dangerous.** `finpredict-v3` calls trend,
   carry and regime-filtered mean-reversion "real profitable signal families" while its own folder
   refutes the VWAP mean-reversion claim; `flaxen-hair` re-asserts mega_mutation
   `production_enable=true` despite FP1's falsification and quant-audit's 170-ledger artifact
   (m006 PF 0.767; 4 passes vs 8.5 expected). Do not enable; label trend `PILOT`.
5. **The peers' per-class ideas are largely already covered, with five real additions.** ADOPT:
   stop-fill replay, 170-ledger benchmark, cost gate (3× round-trip), `universal_price_enricher`,
   CRYPTO POSITION/SWING split. MERGE: 50d+200d trend variant, 4-factor 50+ name portfolio, horizon
   harness, carry book cap, bond-ETF trend into ETF T3, COT contrarian sidecar, R-multiples/exit mix.
   REJECT: short-term reversal, "real profitable" labels, `MUTUAL_FUND` build, decimal-ratio PnL,
   TradingView winner windows, ML stacking, and the "all other classes negative" statement.
6. **Reference drift is real but narrow.** Peers correctly cite our **older**
   `final_2026_11_14/finpredict-v2` as the reconciliation backbone; none can cite our `final_v2`
   because it is not on `origin/main`. Two references are stale/wrong: "childlike-airport final folder
   exists" (not on main) and "ML leakage fixed" (it is a default flip that still needs review). One
   relies on an untracked, unsafe PnL normalizer.

---

*FP6 complete, 2026-11-14T21:25Z. Read-only: no repo source, data, or peer artifact was modified. The
only file written is this report. All peer claims are attributed to the named artifact and line; every
item that could not be checked directly is in §7 `UNVERIFIED`.*
