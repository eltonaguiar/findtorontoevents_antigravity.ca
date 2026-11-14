# FP1 — Independent Review: flaxen-hair "Mega Mutation" Profitability Claim

**Verdict: FAIL — NOT PROVED** (the claim that the edge is "statistically validated / proven" is **FALSIFIED**; the underlying forward signal remains positive but **UNPROVEN**).

- Reviewer: FP1 (independent, read-only; no repo source modified)
- Clock: 2026-11-14 ~20:20Z
- Claim docs: `TRUE_PROFITABILITY_VALIDATED.md`, `PROFITABLE_APPROACH_PROVEN.md` (root and `.kilo/worktrees/flaxen-hair/` — byte-identical, verified by `diff`: no drift between the two copies)
- Data: MySQL `trading_picks` (read-only, `mysql.50webs.com/ejaguiar1_stocks`), `genome/data/*.json`, `reports/*`, `verified_strategies/paper_pilot/*`
- Cross-check: our `research/profitability/HYPOTHESES.md`, `research/profitability/validation/VWAP_VERDICT.md`, `2026-11-14/finpredict-v2_20261114-1602/MASTER_AUDIT.md`

---

## 1. Exact claim extracted

| Element | Claim as written | Source |
|---|---|---|
| Strategy | `mega_mutation_macd_rsi` / `ema_momentum` on CRYPTO; 8 selected combos | `PROFITABLE_APPROACH_PROVEN.md:9-11,17-30` |
| Symbols | ENA, JUP, ADA, WIF, STX, RENDER (MACD_RSI); AVAX, DOT (EMA_CROSS) | `PROFITABLE_APPROACH_PROVEN.md:21-30` |
| Backtest PF/WR/n | PF **3.12–5.816**, WR **64–76%**, n=**100–593** (summary); per-combo PF 3.72–8.28, WR 77.8–87.5% | `PROFITABLE_APPROACH_PROVEN.md:10,21-30`; `TRUE_PROFITABILITY_VALIDATED.md:11-16,60` |
| Forward PF/WR/n | PF **8.32**, WR **84%**, n=**50** | `TRUE_PROFITABILITY_VALIDATED.md:13,36`; `PROFITABLE_APPROACH_PROVEN.md:11,38` |
| Forward period | "live since 2026-06-06" → 2026-11-14 | `TRUE_PROFITABILITY_VALIDATED.md:34-36`; `PROFITABLE_APPROACH_PROVEN.md:32` |
| Benchmark | BTC-USD, paired bootstrap + random-entry Monte Carlo (Task 10) | `TRUE_PROFITABILITY_VALIDATED.md:18-32` |
| PnL normalization | 100× ratio-vs-percent bug fixed; **4,202 closed picks / 6 data sources**; all other classes PF 0.18–0.31, WR 12–40% | `TRUE_PROFITABILITY_VALIDATED.md:7`; `PROFITABLE_APPROACH_PROVEN.md:7,15` |
| Intrabar replay | conservative PF **2.72** ("edge holds under realistic fills") | `PROFITABLE_APPROACH_PROVEN.md:13` |
| Proof status asserted | "statistically valid edge — not a backtest artifact"; "FOUND AND PROVEN" | `TRUE_PROFITABILITY_VALIDATED.md:32`; title of `PROFITABLE_APPROACH_PROVEN.md` |

---

## 2. Recomputation from the underlying data (not the markdown)

All figures below were computed directly from MySQL `trading_picks` and the JSON artifacts; no markdown numbers were trusted.

### 2.1 Forward aggregate (pilot's own dedup + window)

Query reproduced the pilot path (`verified_strategies/paper_pilot/mega_mutation_forward_pilot.py:108-135`): `source_system LIKE '%mega_mutation%'`, `closed_at > '2026-06-05T06:40:21+00:00'`, status in {TP_HIT,SL_HIT,LOST,TIME_EXIT,WON}, dedup on `(symbol,direction,entry,tp,sl,DATE(closed_at))`.

| Cut | n | WR | PF | avg PnL |
|---|---:|---:|---:|---:|
| **Deduped forward (headline)** | **50** | **84.00%** | **8.3193** | **+4.024%** |
| Raw forward (no dedup) | 73 | 84.93% | 8.11 | — |

**The headline "n=50, WR 84%, PF 8.32" reproduces exactly.** ✅ This is the one load-bearing number that survives.

### 2.2 The per-symbol table is the *raw* set, not the deduped set

`PROFITABLE_APPROACH_PROVEN.md:33-37` lists ADA n=13, ENA n=11, JUP n=10, WIF n=7, STX n=5. Those counts only exist in the **raw 73-row** set, not the deduped 50-row set:

| Symbol | Claim (n / WR) | Raw 73 rows (matches claim) | Deduped 50 rows (headline set) |
|---|---|---|---|
| ADAUSDT | 13 / 100% | 13 / 100% | **10** / 100% |
| ENAUSDT | 11 / 90.9% | 11 / 90.91% | **10** / 90.0% |
| JUPUSDT | 10 / 90% | 10 / 90.0% | **6** / 83.3% |
| WIFUSDT | 7 / 100% | 7 / 100% | **4** / 100% |
| STXUSDT | 5 / 100% | 5 / 100% | **4** / 100% |
| DOTUSDT | omitted | 11 / 72.7% (PF 2.22) | 7 / 71.4% (PF 2.04) |
| AVAXUSDT | omitted | 10 / 70.0% (PF 2.74) | 5 / 60.0% (PF 2.64) |
| RENDERUSDT | omitted | 5 / 60.0% (PF 2.29) | 3 / 66.7% (PF 2.84) |
| JTOUSDT | 1 / -5.14% | 1 / 0% | 1 / 0% |

Two consequences:
- The doc mixes datasets: **per-symbol table = raw 73**, **overall claim = deduped 50**. An internal inconsistency.
- `"All symbols profitable except JTOUSDT"` (`TRUE_PROFITABILITY_VALIDATED.md:37`) is **false**: DOT, AVAX and RENDER each contain losses in both the raw and deduped sets.

### 2.3 The claimed backtest numbers are not reproducible from the named data file

`PROFITABLE_APPROACH_PROVEN.md:19` says the combos come "from `genome/mega_mutation_live_tracker.py`"; the actual backfill data is `genome/data/closed_picks.json` (1,221 rows). Recomputing the claimed (mutation, symbol) pairs over that file:

| Mutation / Symbol | Claim PF / WR | Recompute from `closed_picks.json` | n |
|---|---|---|---|
| m048 / JUP | 6.44 / 85.7% | 6.60 / **79.7%** | 153 |
| m084 / ENA | 8.28 / 83.3% | **6.23 / 76.9%** | 104 |
| m017 / ADA | 3.72 / 77.8% | **4.45 / 73.9%** | 153 |
| m048 / WIF | 4.00 / 80.0% | **2.73 / 60.2%** | 166 |
| m048 / STX | 4.88 / 83.3% | **3.40 / 64.4%** | 132 |
| m048 / RENDER | 4.08 / 87.5% | **2.30 / 55.2%** | 154 |
| m006 / AVAX | 4.66 / 87.5% | **0.54 / 41.7% (LOSING)** | 206 |
| m006 / DOT | 3.75 / 85.7% | **1.06 / 56.9%** | 153 |

The claimed PF/WR are **not** the full-sample backtest — they match ~5–6-trade tournament OOS windows (e.g., 83.3% = 5/6). The whole-mutation aggregate for `ema_momentum_m006` is **PF 0.73, WR 48%** (n=359): the two "winning" AVAX/DOT entries are cherry-picked from a net-losing mutation.

### 2.4 Task 10 benchmark report — numbers reproduce, but the sample is 6–9 trades

`reports/benchmark_mega_mutation_2026-11-14.json` (generated 2026-11-14T18:55:02Z) was re-read and matches the doc:

| Ledger | n | PF | Cum | vs BTC | bootstrap CI | frac+ | pass_95 | MC pct |
|---|---:|---:|---:|---:|---|---:|---:|---:|
| m084 | 8 | 11.71 | +48.00% | +43.58pp | [+0.11%, +8.53%] | 0.9787 | ✅ | 0.9487 |
| m048 | 9 | 7.40 | +46.03% | +46.07pp | [+0.29%, +7.70%] | 0.9816 | ✅ | 0.6919 |
| m006 | 6 | 3.74 | +9.30% | +12.09pp | [−1.04%, +5.22%] | 0.8884 | ❌ | 0.7569 |
| m017 | 6 | ∞ | +26.14% | +22.66pp | [−0.25%, +6.80%] | 0.9494 | ❌ | 0.9328 |

Claim lines 23–30 are accurate transcriptions of this report. **However the report itself states `wr_published: false` / `n<20: WR/wilson hidden (insufficient sample)`** — i.e., the tool that produced the "proof" explicitly refuses to publish a win rate at n=8.

---

## 3. Multiple-testing / selection analysis (the core problem)

| Fact | Evidence |
|---|---|
| Search space = **1,000 mutations × 33 symbols = 33,000 backtests** | `genome/data/tournament_results.json` `config.total_backtests=33000`, `n_mutations=1000`, `n_symbols=33`; `genome/mega_mutation_tournament.py:895-931` |
| 877 combos labelled "robust"; top-50 exported; **8 chosen** for the live tracker | `tournament_results.json summary.total_robust=877`; `mega_mutation_live_tracker.py:52` |
| "Deflated Sharpe" correction is **not a correction**: `survives_dsr = dsr_pval > 0.50` ("lenient threshold for now") | `genome/mega_mutation_tournament.py:1020` |
| Expected-max under null uses `n_mutations=1000`, **not** the 33,000 trials actually run | `genome/mega_mutation_tournament.py:1014` |
| Only **3 of 50** top combos clear even that 0.50 lenient bar | recompute of `top_50_combos` |
| Tournament trades per combo = **5–10** | `tournament_results.json` (all 50 combos) |

At α=0.05 with Bonferroni over 33,000 trials the required per-test p is ≈ **1.5×10⁻⁶**. A 5-of-6 combo has a two-sided binomial p ≈ **0.109** (six orders of magnitude too weak). A 6-of-6 combo is p≈0.031. **None of the reported combos clear an honest multiple-testing bar.**

### 3.1 The 8 "verified winners" are not traceable to the stored tournament

The `WINNING_COMBOS` in `genome/mega_mutation_live_tracker.py:52-182` use short names `macd_rsi_m048 / m084 / m017 / ema_momentum_m006`. The saved top-50 from the 2026-05-01 tournament contains **none of these names**. Its ENAUSDT winners are `bb_squeeze_momentum_m030_…` (PF 8.73, 5 trades) and `bb_squeeze_momentum_m054_…`; its top overall is `bb_overbought_short_m003_…` FILUSDT at PF 19.30 / WR 100% on **5 trades**. The doc's "tournament winners" therefore cannot be reproduced from the only tournament artifact in the tree → **provenance UNVERIFIED**.

### 3.2 n=50 split across 8 combos

Even taking the deduped 50 at face value: 50 / 8 ≈ **6 trades per combo**, and 4 of the 8 combos (m006 on AVAX/DOT, plus the post-hoc "additional predictable symbols" m048/WIF/STX/RENDER at `mega_mutation_live_tracker.py:133-181`) were extended by hand after the base mutation won. Net effective sample per tested hypothesis is single digits.

---

## 4. Forward integrity (out-of-sample check)

| Check | Result |
|---|---|
| Tournament/selection time | `tournament_results.json generated_at = 2026-05-01T07:03Z` |
| Pilot start | `mega_mutation_state.json started_at = 2026-06-05T06:40:21Z` (doc says "2026-06-06" — drift) |
| Genuine forward entries | `created_at` 2026-06-22 → 2026-11-06 (25 distinct dates) — **after** selection ✅ |
| Filter used by pilot | **only `closed_at > started_at`** (`mega_mutation_forward_pilot.py:119`), not `created_at` |
| Contaminated rows | **21 of the deduped 50 (42%)** have `created_at = NULL` (`source_system='mega_mutation'`, blank strategy), closing 2026-06-05→06-11 |

The project's own bridge report (`reports/MEGA_MUTATION_BRIDGE_CANDIDATE_2026-06-05.md`, "INCIDENT #91 caveat") documents that `created_at=None` rows are **"synthetic/replay signal"** and that the same rows inflated the lab ledger 2.72×. The pilot's docstring promises "No lab/backfill data is counted as forward" (`mega_mutation_forward_pilot.py:20-22`), but because it filters on `closed_at` only, it silently counts 21 synthetic/replay closes as forward.

### 4.1 The genuinely-OOS subset still looks positive (the saving grace)

| Subset | n | WR | PF | avg |
|---|---:|---:|---:|---:|
| All deduped forward | 50 | 84.00% | 8.32 | +4.02% |
| **Genuine OOS** (`created_at` not null, `genome_mega_mutation`) | **29** | **82.76%** | **9.49** | +3.92% |
| NULL-created backlog (not provably OOS) | 21 | 85.71% | 7.21 | +4.17% |

So the forward window is **not** pure backtest reuse — there are 29 genuinely post-selection trades with strongly positive PnL. That is why the claim is **not falsified outright**, only unproven. But 29 is below the project's own T2 floor of n≥100 (bridge report) and below the n≥30 promotion gate (it clears only because the 21 backlog rows pad it to 50).

---

## 5. Standard failure modes checklist

| Failure mode | Finding |
|---|---|
| 8 winners from huge search | **Present.** 8 of 33,000; DSR threshold 0.50 and expected-max from 1,000 not 33,000 (`tournament.py:1014,1020`). |
| Forward overlapping selection | **Partial.** Genome subset is post-selection (2026-06-22+); 21/50 backlog rows are pre-selection/replay with NULL entry time. |
| PnL unit normalization | **Inconsistent conventions.** `benchmark_closed_ledger.py:423` does `pnl_pct/100` (percent input); `quick_wins/shared/normalize_pnl_units.py` writes decimal **ratio** (`-0.04`). The crypto path is internally consistent (all percent), but the "4,202 / 6 sources" normalization artifact is not committed anywhere → **UNVERIFIED**. |
| Survivorship / resolution bias | **Present.** Of 24 forward `TP_HIT` rows, **13 never reached their TP price**; they were closed at "PRICE_RESOLVED" marks. All 29 `tp_fill_method`, `intrabar_status`, `execution_slippage_pct` are **NULL**. |
| Cost / slippage | **Absent.** `pnl_pct` is computed purely from entry/exit price; no fees, no slippage column populated. The benchmark's claim that "realized returns are net of costs" is false for this data. |
| Benchmark mismatch | **Present but excluded from proof.** The 4 `Revival_Mutated_*` ledger rows are `asset_class='crypto'` (lowercase) and silently fell back to **SPY** (`"no price series for benchmark SPY"`), not BTC. They are excluded from `n_full_proof`, but they are in the 33-row "ledger." |
| n=50 across 8 combos | **Yes** — ~6/combo; 4 combos hand-extended post-hoc. |
| Intrabar replay method | **Mismatch.** The advertised "conservative PF 2.72" is from `reports/intrabar_replay_mega_mutation_20260605/ohlcv_replay_…json` on **n=139 lab trades (min_date 2026-05-01)**, not the forward picks. Forward picks have zero intrabar verification. |

### 5.1 Strict TP-reach sensitivity (genuine OOS)

Recomputing the 29 genuine-OOS trades, dropping the 13 `TP_HIT`s that never reached TP:

| Cut | n | WR | PF |
|---|---:|---:|---:|
| As-reported (price-resolved) | 29 | 82.76% | 9.49 |
| **Strict TP-reach only** | **16** | **68.75%** | **5.19** |

Still positive, but the "84% WR / PF 8.32" headline is a **mark-to-market** win rate, not a bracket-fill win rate. PF 8.32 is also arithmetically mechanical given WR 84% and avg-win/avg-loss ≈ 6.1/3.7.

---

## 6. Citation spot-check (13 items; 7 verified, 6 drift/false)

| # | Claim | Location | Verdict |
|---|---|---|---|
| 1 | Forward PF 8.32 / WR 84% / n=50 | `TRUE_PROFITABILITY_VALIDATED.md:13` | ✅ VERIFIED (DB dedup) |
| 2 | m084 PF 11.71, cum +48.00%, vs BTC +43.58pp | `TRUE_PROFITABILITY_VALIDATED.md:23` | ✅ VERIFIED (report) |
| 3 | m084 CI [+0.11%, +8.53%], frac 0.979, pass_95 | `TRUE_PROFITABILITY_VALIDATED.md:24` | ✅ VERIFIED (0.00112/0.08532/0.9787) |
| 4 | m084 MC percentile 0.949 | `TRUE_PROFITABILITY_VALIDATED.md:25` | ✅ VERIFIED (0.9487) |
| 5 | m048 PF 7.40, cum +46.03%, vs BTC +46.07pp | `TRUE_PROFITABILITY_VALIDATED.md:28` | ✅ VERIFIED |
| 6 | m084 genes tp_atr 2.2 / sl_atr 1.4527 | `TRUE_PROFITABILITY_VALIDATED.md:55` | ✅ VERIFIED (`tracker.py:93`) |
| 7 | 8 combos sit in `mega_mutation_live_tracker.py` | `PROFITABLE_APPROACH_PROVEN.md:19` | ✅ VERIFIED (source location only) |
| 8 | Per-symbol ADA13/ENA11/JUP10/WIF7/STX5 | `PROFITABLE_APPROACH_PROVEN.md:33-37` | ❌ DRIFT — raw 73-set, not dedup 50 |
| 9 | `production_enable=false, promotion_ready=false` | `PROFITABLE_APPROACH_PROVEN.md:58` | ❌ DRIFT — `state.json` = true; `TRUE…:45` = true |
| 10 | "live since 2026-06-06" | `TRUE_PROFITABILITY_VALIDATED.md:34` | ❌ DRIFT — `started_at` = 2026-06-05 |
| 11 | "1 clears MC top decile" | `TRUE_PROFITABILITY_VALIDATED.md:32` | ❌ DRIFT — summary `n_mc_top_decile=2` |
| 12 | Backtest "PF 3.12–5.816, n=100–593" | `PROFITABLE_APPROACH_PROVEN.md:10`; `TRUE…:60` | ❌ UNVERIFIED — 5.816 and 593 absent; bridge says 296 raw / 109 dedup |
| 13 | "All symbols profitable except JTO" | `TRUE_PROFITABILITY_VALIDATED.md:37` | ❌ FALSE — DOT/AVAX/RENDER lose |

---

## 7. Multiple-testing math (why "proven" cannot stand)

- Trials: 33,000. Bonferroni α=0.05 → per-test p < 1.5×10⁻⁶.
- Best reported ledger: n=8, 7 wins → two-sided binomial p = 9/128 ≈ **0.070**; after ×33,000 → **p_adj ≈ 1**.
- Even the strongest possible 8/8 is p = 1/256 ≈ 0.0039 → ×33,000 = **129** (i.e., ≫1).
- The project's own protocol (`research/profitability/HYPOTHESES.md:77-80`) labels such results **NOT_PROVED**, and the T2 floor is n≥100 (`MEGA_MUTATION_BRIDGE_CANDIDATE_2026-06-05.md`). The proof ledger is n=6–9.

---

## 8. Verdict

**FAIL — NOT PROVED.**

- The **forward aggregate** (n=50 / PF 8.32 / WR 84%) reproduces exactly, and a genuinely post-selection subset (n=29, PF 9.49) is positive. Under a strict TP-fill reading it is still positive (n=16, PF 5.19). So this is **not a fabricated result**; there is a real directional signal worth monitoring.
- But the document's central assertion — a **"statistically valid" / "PROVEN"** edge — does not survive independent scrutiny:
  1. Selection of 8 combos from 33,000 backtests with a **0.50-threshold "DSR"** and an expected-max that ignores 32,000 of the trials.
  2. Proof sample is **n=6–9**, far below the project's own n≥100 / Bonferroni gate.
  3. **42% of the headline n=50** is unverifiable `created_at=NULL` replay/backlog; the pilot filters on `closed_at` only.
  4. The claimed backtest PF/WR table is **not reproducible** from the named data (m006/AVAX actually PF 0.54; m048/RENDER 2.30 vs claimed 4.08).
  5. Forward "TP_HIT" is **not intrabar- or fill-verified** (13/24 never reached TP; all intrabar/slippage fields NULL; no costs).
  6. The two claim docs **contradict each other** on production status, and several load-bearing numbers (5.816, 593, per-symbol n, "only JTO loses") drift or are false.

**On the PROVED / PROVISIONAL / FALSIFIED scale:** the *claim of proof* is **FALSIFIED**; the *edge itself* is **NOT_PROVED** (positive but statistically unestablished). It is **not** PROVISIONAL (fails n≥100, clean-OOS, and multiple-testing gates) and **not** PROVED. Consistent with our own `VWAP_VERDICT.md` treatment, the correct disposition is **FAIL — NOT PROVED**, with the mega-mutation forward sleeve allowed to continue only as a small paper-trading monitor.

**Minimum work to reclassify as PROVISIONAL:** (a) restrict forward stats to `created_at > started_at` (removes the 21 replay rows); (b) publish the intrabar/tp_fill method and re-run under `intrabar_status`; (c) fabricate-proof the tournament provenance (reproduce the 8 combos from a committed run or drop the "tournament winner" claim); (d) apply a real DSR/Bonferroni over 33,000 trials; (e) reach n≥100 genuinely-OOS closes with costs.

---

## 9. UNVERIFIED

- **4,202 closed picks from 6 data sources** and the per-class "PF 0.18–0.31 / WR 12–40%" composite: asserted in `memory/2026-11-14.md:3` and the claim docs, but no committed artifact contains 4,202 rows or the 6-source breakdown. Per-class quick-win docs give different figures (ETFs PF 0.022/WR 2.3%; bonds PF 0.391/WR 7.7%; equities PF 0.934/WR 59%; crypto PF 0.371/WR 39.4%).
- **"Backtest PF 3.12–5.816, n=100–593"**: `5.816` and `593` appear nowhere in the tree; bridge report gives 296 raw / 109 deduped (PF 3.12 / 2.79).
- **Tournament provenance of the 8 combos**: not present in `genome/data/tournament_results.json` (2026-05-01); the short-name mutations `m048/m084/m017/m006` are untraceable to any committed tournament run.
- **Genuineness of the 21 `created_at=NULL` forward closes**: project docs call them "synthetic/replay," but their true entry time cannot be recovered from the DB.
- **"Net of costs"**: no fee/slippage field is populated for any forward pick.
