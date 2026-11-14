**PRIORITY: HIGH** — highest feasibility of the three assigned classes: real data is keyless, the mechanism is economically identified, and the live system already generates 21,988 policy-clean crypto outcomes. But the only proven-in-data mechanism is capital-marginal, so "high feasibility" is not "high expected return".

**EXPECTED EDGE: LOW-BUT-REAL CARRY** — funding/basis carry is a genuine low-vol return stream, but it returns 3.7–4.8% on capital at 1.5× capital vs 4.5% cash. Price-only momentum/reversal show no edge in the 2024–2026 OOS. An equity-beating crypto edge is **likely absent** in the current keyless dataset; it would require options or L2 order-flow data.

# CRYPTO — Profitability Playbook

**Clock:** 2026-11-14T21:15Z. **Scope:** research and implementation planning only; no repo source modified. Every number below is quoted from the evidence files named in §7. Anything not directly verified is marked `UNVERIFIED`.

---

## 1. Current evidence — what was tested, what failed, and why

### 1.1 Pre-registered research (23 candidates, 0 proved)

| ID | Hypothesis | OOS result | Benchmark | Why it failed |
|---|---|---|---|---|
| H1 | BTC 200d TSMOM long/flat | Sharpe **0.60**, CAGR **16.5%**, n=29 | BTC B&H Sharpe **0.56** | No edge over simply holding BTC |
| H2 | ETH 200d TSMOM | Sharpe **0.47**, CAGR **11.5%**, n=21 | ETH B&H **0.22** | Absolute Sharpe below the 1.0 gate; n<30 |
| H3 | XS crypto momentum, weekly top-3 (10 majors) | Sharpe **−0.00**, CAGR **−19.2%** | 0.22 | Momentum sign flipped in OOS |
| H4 | Crypto RSI(2) BTC/ETH/SOL | Sharpe **0.06**, CAGR **−4.6%** | 0.34 | Mean reversion did not pay after costs |
| H6 | Vol-scaled BTC TSMOM (40% target, 1.5× cap) | Sharpe **0.55** | 0.56 | Vol targeting added nothing over B&H |
| H13 | XS crypto momentum, top quintile (30 pairs) | Sharpe **−0.18**, CAGR **−31.9%**, SPA **0.488** | −0.01 | Breadth correlated the bets; no independent edge |
| H14 | Crypto short-term reversal, long losers (30 pairs) | Sharpe **−0.36**, CAGR **−44.3%** | −0.01 | Reversal also negative net of 10 bps |
| H15 | Crypto TSMOM breadth, vol-targeted (20 pairs) | Sharpe **0.20**, CAGR **−2.9%** | 0.06 | Trend breadth did not survive costs |
| H20 | Crypto momentum + BTC trend filter (30 pairs) | Sharpe **−0.08**, CAGR **−21.3%** | −0.01 | Regime filter did not rescue momentum |
| H21 | Funding carry, top-5 positive-funding perps | Sharpe **6.42**, notional CAGR **5.6%**, capital/1.5 **3.7%** | Cash **4.5%** | Capital-adjusted return **below cash** |
| H22 | Funding carry, BTC-only | Sharpe **14.24**, notional **7.2%**, capital/1.5 **4.8%** | Cash **4.5%** | Clears cash, but only **10 rebalances < 30** |
| H23 | Funding carry, top-10 positive-funding perps | Sharpe **8.34**, notional **6.2%**, capital/1.5 **4.1%** | Cash **4.5%** | Capital-adjusted return **below cash** |

Sources: `03_research/profitability/HYPOTHESES.md` rows H1–H23; `runs/v3/VERDICT.md`; `runs/v4/VERDICT.md`; `runs/v4/REPORT.md`; `README.md` headline table.

**What this means.** v3 killed the "buy winners / buy losers" families across **30 crypto pairs**: best crypto candidate H15 was Sharpe **0.20** and the Reality Check across all 8 v3 candidates was **p=0.488** (indistinguishable from the bootstrap null). Crypto PBO was **0.59**, i.e. overfit-prone. v4 found a real carry signal — DSR 1.0, bootstrap p05 **4.5–11.9**, 2× cost Sharpe **1.7–11.2**, 5-day-lag Sharpe barely dented — but the **economic** gate failed: at 1.5× capital, top-5/top-10 return **3.7%/4.1%** vs **4.5%** T-bills, and BTC-only at **4.8%** has only **10** rebalances.

FP5 adds a material correction that this playbook adopts: quant-audit re-ran funding carry under a **run-length-preserving block null** and the p-value moved from 0.002 to **1.000** (`FP5_peer_final_folders.md` §2 C2). So the nominal carry economics exist, but the *risk-adjusted* significance is **not confirmed**. This is why §4 treats a block null as a hard gate, not an optional robustness check.

### 1.2 Live-system evidence (the `/audit` fleet, not the research program)

| Surface | CRYPTO number | Reading |
|---|---|---|
| `pf_registry.by_asset_class_policy_clean_net` | n=**21,988**, WR **42.35%**, PF **0.2595**, z **−22.69** | Significantly **below** 50% after Bonferroni; 98.9% single-source |
| `money_ready_verdict` (intrabar) | WR **35.87%**, PF **0.92**, expectancy **−0.059** | 0/9 classes money-ready |
| `recent_closed` CRYPTO | WR **40.2%**, sum PnL **−689.9%**, n=1,966, median close age **29.1 d** | Recent feed is mostly months old |
| Curated active panel | 3 CRYPTO rows; 19/20 panel rows have `pnl_pct=0` | Only **NEARUSDT SHORT** was genuinely marked: dashboard +2.74% → live **+3.1–3.8%** |
| Raw inventory | **402 OPEN**, **334 (83%) frozen** at 0% / null, median raw age **88.7 d** | The visible book is not a live book |
| Summary WR | **98.3%** (wins+losses > resolved) | Arithmetically impossible; `sync_summary_picks_json.py:63-65,161` |

Sources: `01_audit/MASTER_AUDIT.md` §2, §4, §5; `04_peer_reviews/crypto_commodity_review.md` §2 rows 1–5.

### 1.3 Peer crypto claims — all falsified as proofs

| Claim | Claimed | Independent result | Verdict |
|---|---|---|---|
| VWAP mean reversion, 4h | Sharpe **3.76**, PF 1.21 | Annualization artifact → correct Sharpe **~1.18** (t=0.91, p=0.18); **79/129** trades breached stops intrabar (PF **0.81**, **−17.4%**); CSCV PBO **0.84–0.97**; OOS **7.18 months**, not 22; 5 symbols, n=72 | **FALSIFIED** (`validation/VWAP_VERDICT.md`) |
| mega_mutation forward | n=50, WR **84%**, PF **8.32** | Reproduces exactly, but 8 combos selected from **33,000** backtests; "DSR" threshold 0.50; genuinely-OOS subset n=**29**, PF **9.49**; strict TP-reach n=**16**, WR **68.75%**, PF **5.19**; no costs; 13/24 TP_HITs never reached TP | **NOT_PROVED** (`FP1` §3–§5) |
| deepAI variant C | n=237, PF **1.26**, +98.7pp, p<0.0013 | Reproduced on live payload but **z=−0.84** (WR below coin flip), **4/8 months negative**, null is selection-over-clone-re-emissions, slippage never deducted, family correction truncated 4 vs ≥46 | **REPRODUCED, NOT AN EDGE** (`FP2`; `FP5` §2 C1) |

**Root causes, stated plainly:** (a) multiple testing over a **658-strategy / 33,000-backtest** search; (b) single-source resolver artifacts (21 "Bonferroni survivors" are all `single_source_pct=1.00` from one MySQL source); (c) survivorship — **90,523/143,156** picks never resolve and **63%** of the population is excluded from headline stats; (d) no costs in the peer claims. Source: `MASTER_AUDIT.md` §5.

---

## 2. Where an edge could actually exist — mechanism and structural basis

| # | Mechanism | Structural / academic basis | Verdict on current evidence | What it needs that we lack |
|---|---|---|---|---|
| C-M1 | **Funding-rate carry** (long spot / short perp) | Perpetual funding is a fee paid by the crowded side; delta-neutral harvest of the funding premium. Documented carry family (Koijen, Moskowitz, Pedersen, Vrugt, "Carry", JFE 2018); crypto-specific venue segmentation (Makarov & Schoar, "Trading and arbitrage in cryptocurrency markets", JFE 2020) | **Real but capacity-limited / capital-marginal.** DSR 1.0 and 2× cost survives, but ROC **3.7–4.8%** vs **4.5%** cash; block-null p→**1.000** per FP5 | Venue-level margin/capital, fee tiers, basis and counterparty risk; n≥30 |
| C-M2 | **Cross-venue / spot-perp basis dislocation** (episodic) | Same segmentation literature: price gaps across venues persist while capital cannot move fast enough (Makarov & Schoar 2020) | **Real but episodic and capacity-limited.** Not tested here. Likely the highest raw-return crypto mechanism, but it is an execution/ops business, not a signal | L2 books, transfer times/fees, venue limits, real-time basis |
| C-M3 | **Options variance-risk premium** (short delta-hedged straddles / covered calls) | Vol sellers earn a premium for bearing crash/gamma risk; documented in equity index options (Bakshi & Kapadia 2003) and crypto vol markets since Deribit | **Likely real, tail-heavy, untested.** No options data in this repo | Deribit options surfaces, DVOL, funding/borrow, margin model |
| C-M4 | **Intraday order-flow / market-making** (microprice, OFI) | Microstructure: short-horizon predictability from order-flow imbalance and queue position (Cont, Kukanov & Stoikov 2014) | **Real but HFT-competitive and capacity-limited.** Daily/4h bars cannot see it; the VWAP peer claim was a failed proxy | 1m/5m L2 book + trades (Binance/Coinbase archives, Tardis) |
| C-M5 | **Time-series momentum** (daily/weekly) | Documented cross-asset (Moskowitz, Ooi & Pedersen 2012) and crypto (Liu & Tsyvinski, "Risks and Returns of Cryptocurrency", RFS 2021) | **Likely absent net of costs at this horizon.** OOS 0.20–0.60 vs B&H 0.56; breadth H15 0.20 | Nothing new; family is exhausted on this data |
| C-M6 | **Cross-sectional momentum / reversal** | Liu, Tsyvinski & Wu ("Common Risk Factors in Cryptocurrency", JF 2022) find a crypto momentum factor in-sample | **Likely absent in 2024–26 OOS.** H3 −0.00, H13 −0.18, H14 −0.36; PBO 0.59 | Point-in-time universe including delisted pairs; survivor bias is material |

**Real but capacity-limited:** C-M1, C-M2, C-M3, C-M4. **Likely absent (do not re-run on the same data):** C-M5, C-M6.

---

## 3. Hypotheses ranked by evidence × feasibility

Ranking rule: evidence strength (independent, out-of-sample, economically motivated) × feasibility (data available, cost to test, execution realism). Failures are listed too; a ranked hypothesis is not an endorsement.

### C-1 — Capital-adjusted funding + basis carry (rank 1)
- **Signal:** trailing 7-day realized funding per perp; enter delta-neutral (long spot, short perp) when funding > 0 and the *net* carry (funding − fees − basis drift) exceeds a threshold. Exit on funding sign flip or when net carry < 0.
- **Universe:** top-30 liquid USDT perps + their spot pairs (Binance USD-M and spot), cross-checked on OKX/Bybit.
- **Rebalance:** weekly (Monday 00:00 UTC), with a 5-day execution-lag stress.
- **Mechanism:** harvest the funding premium paid by crowded longs; C-M1.
- **Data required:** `fapi/v1/fundingRate` (8h), mark/index price, spot klines, **venue fee tiers and margin requirements**, transfer costs. Existing: funding + spot. Missing: venue capital/margin (`NEXT_DATA_REQUIREMENTS.md` priority #3).
- **Cost / capacity:** 10 bps per side on notional changes (already optimistic); 20 bps sensitivity. Capital multiplier **1.5×** (1× spot + 0.5× perp margin). Capacity is venue- and coin-dependent; report per-symbol notional caps.
- **Failure mode to watch:** capital-adjusted CAGR ≤ cash; block-null p high (the exact FP5 failure); funding-sign reversal during a squeeze; basis blowout causing a margin call on the short-perp leg; survivor universe (delisted perps excluded).

### C-2 — Options variance-risk premium (rank 2)
- **Signal:** short delta-hedged ATM straddle or systematic covered call when implied vol − realized vol (VRP) is in the top tercile of its trailing 1-year distribution; hedge delta daily.
- **Universe:** BTC and ETH options (Deribit), quarterly/monthly expiries.
- **Rebalance:** weekly entry, daily delta hedge, hold to expiry or 7 days.
- **Mechanism:** sell expensive gamma/vega; C-M3.
- **Data required:** Deribit instruments, DVOL, option marks, borrow/funding, margin. All missing.
- **Cost / capacity:** exchange fees + spread + delta-hedge slippage; model **gamma and gap risk**, not just Sharpe. Capacity limited by open interest.
- **Failure mode to watch:** a single crash wipes years of premium; mark-to-market drawdown and margin calls; VRP estimated with overlapping windows.

### C-3 — Cross-venue basis dislocation (rank 3)
- **Signal:** |spot price venue A − venue B| or |perp mark − index| above the trailing 95th percentile, after transfer cost and time.
- **Universe:** BTC/ETH/stablecoins across 3–5 venues.
- **Rebalance:** event-driven (intraday), flat by default.
- **Mechanism:** segmentation arbitrage; C-M2.
- **Data required:** synchronized L2 quotes, transfer fees/times, venue withdrawal limits. Missing.
- **Cost / capacity:** taker fees both legs + transfer + financing; capacity bounded by transfer throughput.
- **Failure mode to watch:** the gap is compensation for withdrawal risk (FTX-style solvency), not free money; latency makes the measured gap unattainable; stale quotes.

### C-4 — Time-series momentum, re-tested only with a block null (rank 4, low expectation)
- **Signal:** 200-day TSMOM long/flat, vol-targeted; exactly H1/H6/H15.
- **Universe:** BTC/ETH + 20 majors.
- **Rebalance:** daily signal, monthly evaluation.
- **Mechanism:** trend risk premium; C-M5.
- **Data required:** already held (Binance Vision daily klines).
- **Cost / capacity:** 10 bps/side, 2× stress. Capacity high.
- **Failure mode to watch:** B&H beta masquerading as alpha (H1 0.60 vs 0.56); repeating an already-seen OOS; data-mined parameter grid.
- **Why rank 4:** the family has already failed twice (v1, v3). Only a genuinely new sample or a new mechanism (e.g. intraday trend) would justify it.

### C-5 — Intraday order-flow market-making (rank 5, highest ceiling / highest cost)
- **Signal:** microprice / order-flow-imbalance imbalance beyond a threshold; quote both sides, inventory-capped.
- **Universe:** BTC/ETH/SOL on one venue.
- **Rebalance:** continuous (1m/5m), inventory limits.
- **Mechanism:** microstructure; C-M4.
- **Data required:** 1m/5m L2 book + trades (priority #1 in `NEXT_DATA_REQUIREMENTS.md`); high storage cost.
- **Cost / capacity:** maker rebates vs taker fees; adverse selection; capacity small but real.
- **Failure mode to watch:** backtest fills assume queue position that does not exist; latency; fees flip the sign; the VWAP peer failure is the cautionary example.

**Deliberately excluded from the ranking:** cross-sectional momentum/reversal (C-M6) — already failed at n=30 pairs with negative OOS Sharpe and PBO 0.59; re-testing it on the same window is a prohibited sweep.

---

## 4. Pre-registered next experiment (one only)

### H24 — Capital-adjusted cross-venue funding+basis carry (CRYPTO)

This is the **only** crypto experiment worth running next, because C-M1 is the one mechanism with a documented economic basis and existing data. Its purpose is to decide whether carry is investable *after real capital and a block null* — not to find a higher Sharpe.

**Hypothesis.** A delta-neutral basket of the highest net-of-fee funding perps earns a return on capital (ROC) at least **100 bps above the 13-week T-bill** in the 2024-01-01+ OOS, after 2× costs, a 5-day execution lag, and a run-length-preserving block null.

**Data (exact).**
- Funding: Binance USD-M `GET https://fapi.binance.com/fapi/v1/fundingRate` (8h, paginated), plus OKX `GET /api/v5/public/funding-rate-history` and Bybit `GET /v5/market/funding/history` for cross-venue confirmation.
- Spot: Binance Vision monthly klines `https://data.binance.vision/data/spot/monthly/klines/<SYM>/1d/`; current month via `api.binance.com/api/v3/klines`.
- Mark/index: `fapi/v1/premiumIndex` and `fapi/v1/klines` (mark price) for basis.
- Cash: Treasury.gov 13-week bill (same series as v4).
- Fees/margin: venue published fee tiers (maker/taker) and maintenance-margin schedule, recorded in the manifest. If a venue's fee tier cannot be verified, that venue is excluded — do **not** assume the lowest tier.
- Universe fixed ex ante: the 30 USDT perps in `PROTOCOL_v4.md`, with first-available-bar entry and no backfill; symbols with <21 days of funding history excluded at rebalance.
- **Manifest:** symbol, source, rows, first/last date, SHA-256, retrieval timestamp — same contract as `PROTOCOL.md` §2.

**Split.** Train **2020-01-01 .. 2023-12-31**; OOS **2024-01-01 .. 2026-11-13** (last complete bar at run time). Parameters (carry threshold, top-N, exit rule) chosen on train only. OOS evaluated once. If revised after seeing OOS, the next OOS starts at the revision date and the prior OOS is demoted to "seen" (`PROTOCOL.md` §4).

**Execution.**
- Signal from the 00:00 UTC bar close; positions from the **next** 8h funding interval (t+1). No same-bar execution.
- Weekly rebalance, equal weight, gross notional ≤ 1.0×; **capital multiplier 1.5×** (1× spot + 0.5× perp margin), reported as ROC, never as notional Sharpe.
- 5-day execution-lag stress: shift all entries by 5 days, recompute.
- Intrabar stops: **not applicable to the carry leg** (funding accrues on a schedule); instead model a basis/margin stop — if the short-perp leg's margin ratio exceeds 80% of maintenance, forced unwind at the mark. Report gap risk on the unwind.
- No basis PnL in the base case (delta-neutral), but report a `basis_drift` sensitivity that marks both legs to market daily.

**Costs.** 10 bps per side on notional changes for spot+perp netted (the v4 convention, already optimistic), **plus** venue taker fees if the trade crosses, **plus** transfer cost when capital moves venue. Stress at **2×** total cost. Report gross and net separately; never label gross as net (the FP2 failure).

**Concurrent capital.** 1.5× notional per unit of capital; maximum 25% of capital in any one symbol; cross-venue leg capital counted separately. Report peak gross exposure and the funding-sign-reversal drawdown.

**Gates (all must pass; any failure = NOT_PROVED).**
1. **Economic:** OOS net ROC ≥ T-bill + **100 bps**, at 1.5× capital.
2. **True DSR ≥ 0.95** at **N = all trials** (H1–H23 + H24 = 24; also report DSR at N=683, the research universe, as a sensitivity). DSR must use the **per-period** Sharpe and an estimated cross-trial variance `V`, not an annualized Sharpe fed into a per-period SE (the FP5 §4.2 defect).
3. **CSCV PBO ≤ 0.10** on a genuine **time-indexed T×S** matrix of candidate returns (T≥1000, S = all candidates), not a strategy-sorted matrix (the MASTER_AUDIT §5 degeneracy).
4. **SPA / Reality Check** with a stationary bootstrap, p < 0.05, across the full candidate set.
5. **Run-length-preserving block null** p < 0.10 on the carry return series (the FP5 C2 correction; this is a hard gate).
6. **n ≥ 30** OOS rebalances/round trips. BTC-only alone cannot pass this.
7. **2× cost** ROC still ≥ T-bill + 50 bps.
8. **5-day execution lag** ROC still ≥ T-bill.
9. **Independent replication** on a fresh data pull before any "PROVISIONAL" label.

**Pre-registered kill (see §5).** The experiment is designed to fail fast if carry is only a cash substitute.

---

## 5. Kill criteria — abandon crypto (as a research class) if any holds

1. **H24 fails the economic gate** (ROC < T-bill + 50 bps after 2× costs at 1.5× capital) — that closes the last documented keyless-data mechanism, and the class becomes "no investable edge without options/L2 data".
2. **Block-null p ≥ 0.10** on the carry series, confirming the FP5 C2 finding at full sample.
3. **n < 30** OOS rebalances even after pooling top-5/top-10/BTC-only — i.e. the strategy trades too rarely to certify.
4. **No verifiable venue margin/fee data** — without it, the capital-adjusted result is an assumption, not evidence, and must not be published.
5. **Any candidate requires symbol cherry-picking or a post-hoc regime filter** to pass — that is the mega_mutation/VWAP failure, not an edge.
6. **A re-run of momentum/reversal on the same 2018–2026 window "passes"** — this is a multiple-testing artifact by construction; it does not reopen the class.

If killed: pivot the crypto budget to **C-M3 (options VRP)** or **C-M4 (L2 order-flow)** only after the data in `NEXT_DATA_REQUIREMENTS.md` priorities #1/#2 is acquired.

---

## 6. What NOT to do

1. **No more parameter sweeps on the same window.** The 2018–2026 daily/4h crypto space is exhausted (23 candidates; `README.md`). Another grid cell is a new trial, not new evidence.
2. **No post-hoc regime filters.** H20 already tried a BTC trend filter and still lost (−21.3%). A filter fitted after seeing OOS is a prohibited degree of freedom.
3. **No symbol cherry-picking.** Mega-mutation chose 8 symbols from 33,000 backtests; the per-symbol table mixed raw and deduped sets (`FP1` §2.2). Fix the universe ex ante.
4. **No notional Sharpe as a headline.** A 14.24 Sharpe on a 0.5–0.9% vol carry is a cash-plus arbitrage; report ROC vs cash (`runs/v4/VERDICT.md` §2).
5. **No gross labelled as net.** deepAI's "net of slippage" was gross; `pnl_pct` is a price return (`FP2` §4.3). Costs are a gate, not a footnote.
6. **No annualization from trade count.** The VWAP claim's 3.76 → 1.18 error came from annualizing per-trade returns. Use `sqrt(periods_per_year)` from bar frequency.
7. **No degenerate PBO.** "PBO < 0.5" from a bootstrap p≈0.5 is not a gate; require CSCV PBO ≤ 0.10 on a time-indexed T×S matrix.
8. **No reusing the system's own `pnl_pct` ledger as ground truth.** 63% of picks never resolve; `resolution_method` is `None` for 100% of 3,500 `recent_closed` rows (`FP5` §2 A6). Use independent OHLCV/intrabar replay.
9. **No survivor-only universe.** Binance spot history excludes delisted pairs; state the delisting rule and test sensitivity.
10. **No funding-carry "proof" from BTC-only n=10.** Ten rebalances is a sample, not a certification (`runs/v4/VERDICT.md`).

---

## 7. Evidence index and `UNVERIFIED` markers

**Primary evidence read for this file**
- `final_v2/finpredict-v2/01_audit/MASTER_AUDIT.md` §2, §4, §5 (live-system crypto stats, survivorship, multiple testing).
- `final_v2/finpredict-v2/03_research/profitability/README.md`, `SCORECARD.md`, `HYPOTHESES.md` (H1–H23, version log).
- `.../runs/v3/VERDICT.md` (breadth; SPA 0.488; crypto PBO 0.59).
- `.../runs/v4/VERDICT.md`, `.../runs/v4/REPORT.md` (H21–H23 exact metrics).
- `.../validation/VWAP_VERDICT.md` (as summarized in README/SCORECARD).
- `final_v2/finpredict-v2/04_peer_reviews/FP1_flaxen_hair_mega_mutation.md`, `FP2_deepAI_profitable_v1.md`, `FP5_peer_final_folders.md`.
- `final_v2/finpredict-v2/04_peer_reviews/crypto_commodity_review.md`.
- `research/profitability/NEXT_DATA_REQUIREMENTS.md` — **path correction:** the brief named `03_research/profitability/NEXT_DATA_REQUIREMENTS.md`, which does not exist; the file is at the repo-root `research/profitability/NEXT_DATA_REQUIREMENTS.md`.

**`UNVERIFIED` (do not treat as fact)**
- v3's CRYPTO "policy-clean-net PF 0.98 / WR 39.7%" — not reproducible from the archived `pf_registry` (0.2595 / 42.3504) or `money_ready_verdict` (0.9196 / 35.87%) (`crypto_commodity_review.md` §8).
- v4's exact ML confidence bands (14.4% vs 60.3% WR) — the inverted pattern is corroborated historically, exact figures not recomputed (`crypto_commodity_review.md` §8).
- `ci_challenge_antigravity_active_picks.json` age — 9 OPEN rows with null price / 0% PnL are verified; the "245 days / 2026-03" age is not timestamped in the file.
- The FP5 block-null p=1.000 is **peer-reported** (quant-audit) and not re-derived here; it is used as a gate rationale, not as a number in a proof.
- Venue fee tiers, margin schedules, and per-symbol capacity are **not available** in the repo and must be captured before H24 can publish a capital-adjusted result.

---

## Addendum (final_v2, FP6)

**Stop-fill defect (C6).** Planned crypto risk is **1.919%**, realized loss **2.990%** (56% worse).
The overshoot is **+828.0 pp** against a **−837.8 pp** class total — **98.8% of the crypto loss**.
Replaying exits at the stop (intrabar OHLCV, gap at bar close) moves PF **0.768 → ≈1.00**: breakeven,
not profit. This must be fixed before any crypto signal is judged.

**Actionable split (undersampled).** `CRYPTO POSITION` bucket: n=33, WR 69.7%, PF 3.18 — forward
test at n≥100 before any claim. Kill `CRYPTO SWING`: n=243, PF 0.457 (39% of class loss).

**Correction.** `exit_reason` is populated (SL_HIT/TP_HIT/FORCE_CLOSED/TIME_EXIT/UNKNOWN/EXPIRED);
`resolution_method` was the wrong key. The missing piece is fill fidelity, not exit taxonomy.

**Peer check.** The 170-ledger benchmark scores sibling m006 at PF 0.767; mega_mutation
`production_enable` must stay **false** until the FP1 issues are resolved and n≥100 forward.
