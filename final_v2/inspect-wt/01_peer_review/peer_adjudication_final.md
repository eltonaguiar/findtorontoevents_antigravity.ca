# Final peer adjudication — last chance (2026-11-14, deepAI)

**Scope:** every peer claim on the table at the final stage — `final_2026_11_14/` (6 packages)
and `final_v2/` (finpredict, finpredict-v3, flaxen-hair at time of writing). Each verdict is
re-executed where I had the artifact; otherwise explicitly UNVERIFIED. This closes my review;
the master synthesizer should treat this table + quant-audit's `00_executive_summary` as the
two independent adjudications.

## A. Claim-by-claim verdicts

| # | Claim (source) | My verdict | Evidence / why |
|---|---|---|---|
| 1 | System is not money-ready (`/audit`, all 6 final_2026 packages) | **ACCEPTED — consensus** | My independent: 0/9 surfaces, fleet PF 0.26–0.80, 78.6% zombie EXPIRED, 81% fake 0% open P/L. quant-audit: 0/166 cells; finpredict-v3: 0/6 n≥60 + 0/26 n≥30. |
| 2 | Root cause = data integrity + multiple testing, not tuning (finpredict, v2, v3, quant-audit, mine) | **ACCEPTED** | 646-strategy universe, only 4 cells n≥100, zero pass n≥100+PF>1.3+z>1.96; 69/80 live anti-overfit OVERFIT_LIKELY. |
| 3 | PnL-unit mix bug at `dashboard_generator.py:8065-8072` (v3, flaxen-hair, finpredict) | **ACCEPTED** | Multi-peer file:line verified; matches my EURGBP 688.17-class garbage-ingest evidence. |
| 4 | `resolution_method=None` for all 3,500 `recent_closed` rows (quant-audit) | **CONFIRMED BY ME** | Re-run on my payload: `{'None': 3500}`. **Blocks certification of every PF including variant C.** Values still *look* intrabar (MOMENTUM_15M short 0.13588 < nominal TP 0.15395) but the field is unpopulated → unverifiable. |
| 5 | Kilo/childlike-airport VWAP "Sharpe 3.76" (peer doc) | **FALSIFIED (double)** | finpredict-v2: correct ≈1.18, t=0.91 p=0.18, CSCV PBO 0.84–0.97, 79/129 stops breached intrabar (PF 0.81); quant-audit: impossible vol arithmetic (1.84%/yr on 40%-sized 4h crypto), inverted PBO gate. Two independent refutations — settled. |
| 6 | `mega_mutation` PROVEN, `production_enable=true` (flaxen-hair) | **DISPUTED → pilot only** | My checks: **0 rows in `recent_closed`**; pf_registry top cells `is_single_source_artifact=True`, PF 49–53/n=124 from single source `mysql:at_pick_outcomes`; finpredict-v2: 21/50 synthetic/replay, strict n=16 PF 5.19, selection 8/33,000 uncorrected. Best *candidate* in the system (agrees with my V2 p=0.048 both halves) but single-source + ledger disagreement + n<30 strict OOS. |
| 7 | TSMOM "PROVEN, Sharpe 2.13, CI excludes 0" (finpredict ITERATION-005) | **CORRECTED BY ITS AUTHOR** | finpredict's own final_v2 accepts all 4 quant-audit points (t tests mean>0 not vs B&H; bear-inclusive OOS Sharpe 0.57, null p=0.200; PF 1.40 mislabeled; bar-count deficit). Now honestly framed as "credible risk-premium harvest, benchmark-relative alpha UNPROVEN". **I endorse the correction** — it is a CTA-style sleeve, not system alpha. |
| 8 | Funding/carry real but capacity-limited (finpredict-v2: 4.8% vs 4.5% cash at 1.5×) | **ACCEPTED as cash-alternative, NOT as edge** | Capital-adjusted honesty: it clears cash by ~0.3pp — a financing decision, not alpha. |
| 9 | **My variant C** (n=237 PF 1.26 +98.7pp p<0.0013) — reproduced by quant-audit ("only claim surviving re-execution") and finpredict-v2 ("REPRODUCED / SELECTION EFFECT") | **REPRODUCED, SUB-T2, NOT PROVED** | My own re-execution for this final pass: **clone objection REFUTED** (only 6/237 same-day clones; dedup PF 1.25–1.27, +94.7–99.2pp); **slippage objection PARTIALLY ACCEPTED** (`slippage_pct`=0 on all 3,500 closed rows → my "net of slippage" wording downgraded to UNVERIFIED, breakeven buffer 0.416%/trade still healthy); **Oct-23 vintage objection UNVERIFIABLE** (artifact gone; suspect non-stationary `recent_closed` window — Oct 1,137 rows vs ~180/mo earlier); **Bonferroni/random-null objections ACCEPTED** (selection-based; forward record is the real test). Status: the system-native pilot, arbitration = weekly pre-registered task `5992b142`. |
| 10 | `quan_engine` 95.8% WR / `st_rsi…` 65.1% / SHORT 72% claims (PLAN_PATH doc) | **ARTIFACT / UNVERIFIED** (finpredict-v2) | I did not re-test; their evidence (snapshot-only, zero rows in 5 datasets, 25-row cells, full population opposite) is specific and consistent with my zombie/backfill findings → accept as FALSIFIED. |
| 11 | "The gap is research → production" (finpredict final_v2) | **ACCEPTED — key insight** | Profitable harnesses exist in `/tmp/*.py`; the deployed 683-strategy zoo is overfit noise on broken data. The roadmap implication: **stop mining, deploy2–4 verified sleeves**. |
| 12 | Per-class roadmap premia + realistic Sharpes (finpredict final_v2 `PROFITABILITY_ROADMAP`, finpredict-v3 per-class) | **ACCEPTED with my amendments** | Their numbers (crypto TSMOM 0.5–2.1, equity factors 0.4–0.8, forex carry 0.3–0.6, futures CTA 0.5–1.0, bonds 0.3–0.6) are the right honest range. My amendments are in `02_profitability_per_asset_class/`: their plans under-weight *the system's own live output* (variant C pilot) and the **order of operations** (resolution_method first). |

## B. Review of the final_v2 packages specifically

- **`final_v2/finpredict`** — best-in-class honesty: self-corrects its own "PROVEN" commit,
  accepts all 4 quant-audit points, convergent verdict table, full per-class roadmap.
  Weakness: paths are all *research re-builds* (new harnesses); it under-uses the one
  reproduced system-native result (variant C) — it names it only as "a lead to reproduce",
  which has since been reproduced twice. **No factual disputes.**
- **`final_v2/finpredict-v3`** — adds a concrete global release gate (n≥60, Wilson CI vs 50%,
  PF>1.05, walk-forward win-majority ≥66%, multiple-testing + capital adjustment) — stricter
  than T2 on CI, looser on n (60 vs 100). Recommendation for the master plan: **adopt T2's
  n≥100 + v3's CI/walk-forward-window tests merged** (T2 ∧ v3, not either alone). Its
  `02_peer_reviews/` adjudicates the VWAP dispute consistent with #5 above.
- **`final_v2/flaxen-hair`** (dir appeared while I wrote this) — not yet read in depth;
  standing dispute #6 (mega_mutation "PROVEN") applies until its rows pass independent
  price-truth verification. **Action for master:** require flaxen-hair to publish the 50
  forward rows with symbols+timestamps so they can be checked against Binance klines.

## C. What remains open (cannot be closed tonight)
1. `resolution_method` backfill → then re-certify ALL PFs (owner: pipeline, not audit).
2. Oct-23 payload vintage (artifact gone) → payload-vintage sensitivity of variant C unresolved.
3. Linux host 192.168.2.52 peer work — SSH password required; UNVERIFIED.
4. flaxen-hair final_v2 additions (pending at time of writing).
5. 180/365 workflows' last-run status (API budget) + failure logs (403 admin-only).

## D. The one synthesis I want the master plan to keep
Peers converge on *premia portfolios and research harnesses*; my contribution is that **the
system already emits ~28 trades/month on equity/ETF whose strategy-composition, under a
pre-registered selection rule, has beaten random selection twice-over (two independent
reproductions) and is the only system-native path to a certified edge.** Fix the data layer
(order of operations), run that pilot honestly with kill criteria, and treat everything else
as documented risk premia — not alpha.
