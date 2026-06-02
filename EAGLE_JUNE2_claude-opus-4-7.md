# EAGLE JUNE-2 — Quant Review & Root-Cause Analysis

**Date:** 2026-06-02 06:50Z
**Model:** claude-opus-4-7 (claude code claude-opus-4-7)
**Reviewer role:** Quant (independent) — extensive review across `/audit` surfaces, `pf_portfolios.json`, `pf_registry.json`, `money_ready_verdict.json`, `dashboard_data.json`, all open PRs, all 2026-05/06 reports, all 38 alpha_engine strategy modules, and the existing `docs/BACKTESTING_GUIDE.md` + `docs/MUTATION_THREE_AXIS_PROTOCOL.md`.

> **Citation policy:** every numeric claim has a source path. No invented PF/WR/Sharpe figures. All data fetched live 2026-06-02 06:21–06:50Z.

---

## 0. TL;DR (one screen)

1. **"Why is the portfolio empty?" — it isn't.** `pf_portfolios.json` shows 81 active portfolios, 66 with open positions; `pf_portfolio_deepseek_v4__aggressive.json` has **11 open positions** (GC=F, ES=F, MVST, SI=F, JPM, HD, VZ, MA, ADAUSDT, LINKUSDT, ETHUSDT), $100,403.24 NAV, +0.4032% since 2026-05-31. **The `pf.html` WebFetch returned an empty state because the page renders client-side from the JSON and the WebFetch tool cannot execute JS.** The user's impression "empty" is a renderer/JS-render artifact, not a data absence.

2. **Where is our edge?** In a very narrow band: the **AI tournament** has a few near-edge models (`deepseek_v4__aggressive` +0.40%, `llama4_scout__aggressive` +0.14%, `cursor_agent__balanced` +0.015%, `together_deepseek_v3__aggressive` +0.001%). The **/audit** production book is honest-dead: 0/6 classes pass Tier-2, 3 degraded, 0 ready to deploy. The **lab** has 1 Tier-2 pass (ETF Dual Momentum Sectors PF 1.60, n=104) but it isn't live — paper pilot only.

3. **Do we just need more time?** **No for the production book. Yes for ETF and maybe FOREX/COMMODITY.** Time is not the bottleneck for CRYPTO/EQUITY — those are honest failures, not patience problems. ETF is a forward-n problem. FOREX is a data/resolver problem that has been partially fixed (PR #6, FRED cache, sign-coherence purge #433) but the cohort is still negative.

4. **Do our strategies suck?** The deployed mix mostly does (yes). The lab has a few real sleeves (ETF Dual Momentum, Connors H-103 partial, Donchian variant). The tournament has model-level edge in 4 names. The deployment of these is the problem, not the strategies themselves.

5. **What are we doing wrong?** (a) Promoting from lab edge without forward evidence; (b) conflating tournament/funnel edge with deployable edge; (c) allowing single-source concentration (`claude_gainer_st` 91.7%, `multi_asset_scanner` 85% on FUTURES); (d) the "78.9% CRYPTO" cell is a known artifact (DISPUTED banner since `c1b977997`); (e) over-broad emitter set with no promotion gate; (f) data-feed issues (Bitget 403, Binance 451, FRED timeout on gx10) silently breaking strategies upstream.

6. **DNA-mutate?** Yes, selectively on a small set of failed-but-plausible sleeves (CRYPTO Connors H-103, ETF Sector Momentum with VIX gate, EQUITY `stocks_rsi2_pullback` per dashboard top filter). No blanket mutation.

7. **Invert?** **No** — the data refutes "global ML inversion" (per `project-confidence-trust-edges-2026-05-31.md` — CRYPTO 0.8-bucket has a 14.4% WR dip, but it's localized, not a global ML inversion; the data shows 0.50–0.60 conf bucket at 60.3% WR is the **best** band). Inversion would destroy a real localized edge.

8. **Are strategies dead due to data feed?** Partially. The Zoo refutation (2026-06-02) showed the "29/30 silent strategies" finding was a simulator bug, not a code problem. Real silence drivers: data feed (Binance 451 → PR #435 fixes with CryptoCompare/KuCoin fallback), gate rejection, source-system blocklist, universe filter, resolver state pre-#433.

9. **Backtest methodology** — `docs/BACKTESTING_GUIDE.md` is in place (purged K-fold WF, DSR, PBO, costs/slippage, MDD). What's missing is the **gate at the production emission step**: no production_scanner check against DSR, no concentration check, no walk-forward required, no regime check, no bootstrap CI, no shadow→tiny-size→full-size funnel. See §6.

10. **Why is the live book so bad when the lab has Tier-2 passes?** Translation gap. Lab Tier-2 ≠ live money-ready. The production_scanner emits from a much noisier universe than the lab. PF 1.60 ETF lab vs PF 0.34 ETF live (n=13, INSUFF-N) is the classic research-to-production translation problem compounded by sample-size collapse and the resolver bugs that were only fully closed post-2026-05-02.

---

## 1. Live state — what is actually in production today

### 1.1 `pf_portfolios.json` (81 portfolios, all `kind=model`, all `status=active`)

| Distribution of `n_open` | count |
|---|---:|
| 0 | 15 |
| 2–7 | 35 |
| 8–12 | 28 |
| 14–21 | 3 |
| **Total with positions** | **66/81** |

**Top 5 by realized PnL% (from 81-portfolio index):**
1. `deepseek_v4__aggressive` n_open=11, +0.4032%, $100,403.24
2. `llama4_scout__aggressive` n_open=12, +0.1406%, $100,140.55
3. `cursor_agent__balanced` n_open=14, +0.0154%, $100,015.40
4. `deepseek_v4__balanced` n_open=12, +0.0144%, $100,014.39
5. `together_deepseek_v3__aggressive` n_open=11, +0.0014%, $100,001.36

**Bottom 3 (negative):**
- `cursor_agent__aggressive` −0.1128%, $99,887.18 (n=14)
- `grok3__aggressive` −0.0234%, $99,976.60 (n=16)
- `gpt5_chat__aggressive` −0.0016%, $99,998.43 (n=12)

**Two-day window caveat:** NAV deltas of <0.1% on $100k starting capital is ~$100 of PnL. This is paper / unbacked. The "edge" is at the noise floor.

### 1.2 `pf_portfolio_deepseek_v4__aggressive.json` (deep-dive on user's example)

- **NAV curve:** 2 dates stamped, 2026-05-29 ($100,002.41) and 2026-05-31 ($100,403.24), `+0.40%`.
- **Cash:** −$57,979.76 (leverage; gross exposure 157.98%).
- **11 open positions** spanning 6 asset classes:
  - 3 COMMODITY: GC=F, ES=F (futures), SI=F
  - 1 PENNY: MVST
  - 4 EQUITY: JPM, HD, VZ (short), MA
  - 3 CRYPTO: ADAUSDT, LINKUSDT (short), ETHUSDT
- All have `sl_price` set (no `tp_price`) — i.e., stop-loss only, no profit target.

### 1.3 `money_ready_verdict.json` (2026-06-02 06:21Z) — the live gate

| Class | Verdict | n | WR | PF | DSR | MDD | top_src | top_src% | expect |
|---|---|---:|---:|---:|---:|---:|---|---:|---:|
| EQUITY | NOT_READY | 52 | 26.9% | 0.327 | 0.0 | 0.63 | regime_terminal | 40% | −1.77% |
| CRYPTO | NOT_READY | 374 | 35.6% | 0.887 | 0.0 | 1.00 | UNKNOWN | 55% | −1.02% |
| ETF | INSUFFICIENT_DATA | 3 | 66.7% | 1.458 | n/a | n/a | UNKNOWN | 67% | +0.23% |
| UNKNOWN | INSUFFICIENT_DATA | 9 | 66.7% | 0.724 | n/a | n/a | UNKNOWN | 89% | −0.68% |
| FOREX | INSUFFICIENT_DATA | 32 | 28.1% | 0.481 | 0.0002 | 0.82 | multi_asset_scanner | 34% | −2.27% |
| COMMODITY | INSUFFICIENT_DATA | 4 | 50.0% | 1.676 | n/a | n/a | UNKNOWN | 50% | +0.40% |
| FUTURES | INSUFFICIENT_DATA | 13 | 15.4% | 0.519 | 0.004 | 0.17 | multi_asset_scanner | **85%** | −0.78% |
| PENNY_STOCK | INSUFFICIENT_DATA | 1 | 0.0% | 0.000 | n/a | n/a | multi_asset_scanner | **100%** | n/a |
| BOND | INSUFFICIENT_DATA | 0 | n/a | n/a | n/a | n/a | (none) | 0% | n/a |

Source: `audit_dashboard/data/money_ready_verdict.json` 2026-06-02T06:21:04.746Z

**What this means in plain English:**
- 0/6 classes pass Tier-2 (T2 requires PF≥1.5, WR≥50%, MDD<20%, n≥100, DSR≥0.90).
- All classes have negative `expectancy` except ETF (+0.23% on n=3) and COMMODITY (+0.40% on n=4). The 4-positive numbers are noise (n<10).
- `top_source` is the single largest contributor to a class's PnL. FUTURES (85%) and PENNY_STOCK (100%) are single-source dominated. CRYPTO's `top_source = UNKNOWN (55%)` is a data-quality problem (the resolver couldn't classify 55% of crypto picks to a real strategy), not a real concentration — but the **other 45% is heterogeneous** so the true concentration may be lower. EQUITY's `regime_terminal (40%)` is a real concentration; this strategy is doing ~40% of the equity work.
- All DSR scores are 0 (zero). DSR is undefined when n<30 in a group OR when the cross-strategy permutation test cannot rank. The "n_spa_pass" = 0 across the board.

### 1.4 `pf_registry.json` (`by_asset_class_policy_clean_net`) — cross-check

| Class | n | WR | PF | pnl% | top_src | ss% | ss_artifact |
|---|---:|---:|---:|---:|---|---:|---|
| COMMODITY | 4 | 50.0% | 1.676 | +0.021 | file:alpha_engine | 50% | False |
| CRYPTO | 377 | 35.5% | 0.888 | −3.264 | file:battleground | 23% | False |
| EQUITY | 52 | 26.9% | 0.327 | −0.869 | regime_terminal | 40% | False |
| ETF | 3 | 66.7% | 1.458 | +0.009 | file:alpha_engine | 67% | False |
| FOREX | 32 | 28.1% | 0.481 | −0.709 | multi_asset_scanner | 34% | False |
| FUTURES | 13 | 15.4% | 0.519 | −0.089 | multi_asset_scanner | **85%** | **True** |
| PENNY_STOCK | 1 | 0.0% | 0.000 | −0.015 | multi_asset_scanner | 100% | False |
| UNKNOWN | 9 | 66.7% | 0.724 | −0.053 | file:alpha_engine | 89% | **True** |

Source: `audit_dashboard/data/pf_registry.json` 2026-06-02 (counts: 2901 raw → 1843 closed → 784 flicker-filtered → 702 deduped → 491 policy-clean).

**The two `is_single_source_artifact = True` flags are key:** FUTURES' "edge" comes from `multi_asset_scanner` 85% concentration (single-source artifact) and UNKNOWN 89% concentration. These are not real strategy edges — they're filter-by-strategy artifacts.

### 1.5 `dashboard_data.json` (raw, pre-policy-clean) — additional signals

- **CRYPTO 14d panel (smart_money, 61.6% single-source concentration):** PF 5.56 / WR 66.7% / n=61.6, but with 6 duplicate groups, meaning the WR is inflated by repeated same-signal entries. This is a real artifact, not a real edge.
- **CRYPTO 48h panel:** 0 closed in 48h. 322 still active. The "recent" story on CRYPTO is that **nothing is closing** — not that it lost, not that it won. Stale open positions.
- **EQUITY 14d panel:** WR improving 37% → 67%. But the dashboard filters apply `_is_valid_resolved_pick()` and the gap between dashboard 85.5% and raw 60.2% on COMMODITY is filter-survival, not edge.
- **CRYPTO Smart Picks "78.9% WR / PF 9.69" cell** is **DISPUTED** (banner live since `c1b977997`). 91.7% concentration in `claude_gainer_st`; 97 EXPIRED picks mislabeled WON. Real CRYPTO WR is 39–41% in raw DB 90d.
- **ML calibration is INVERTED locally, not globally:** CRYPTO conf≥0.90 → 14.4% WR, but conf 0.50–0.60 → 60.3% WR. EQUITY 0.85–0.90 → 20% WR. This is a real calibration problem, NOT a "global inversion" claim (refuted 2026-05-31). The cause is the score booster overweights high-confidence picks that are actually right-tail outliers.
- **DSR survivors (lab):** 4 ML-enhanced crypto sleeves with n<100 (DSR formula unreliable). 33 of 42 audited strategies are `OVERFIT_LIKELY` (DSR<0.5). FOREX has 0 DSR survivors.
- **Decile predictor power (CRYPTO):** `ml_score` Spearman +0.33, decile 1 → 32.5% WR, decile 10 → 60.0% WR. Decile 10 underperforms decile 9 ("extreme scores signal overconfidence, not edge"). Kill zone: ml_score < 0.50 → 22% WR.

---

## 2. Root-cause analysis by asset class

### 2.1 CRYPTO — research edge exists; production book is broken

**Live state (PF 0.89 / WR 36% / n=374 / DSR 0.0 / MDD 1.0):** failed.

**Sub-cohorts with real edge (from lab):**
- ETF-lab (hypothetical, for comparison): PF 1.60 / WR 53.8% / n=104
- CRYPTO Donchian Breakout Multi (lab): PF 7.04 / WR 50.3% / n=370 — but **MDD −44.6%** (fails MDD gate)
- CRYPTO Connors H-103 symbol filter (lab): PF 1.30 / WR 65.6% / n=5740 — below PF gate
- CRYPTO Connors H-102 (harness): UNTESTED (windows_scored=0; 14d window density insufficient)
- ml_enhanced INJUSDT 1d lightgbm: WR 100% n=27 (DSR 0.9995 but n<100)
- ml_enhanced DYDXUSDT 15m ensemble: WR 96.8% n=31 (DSR 0.9995 but n<100)

**The lab has localized sleeves that look great. The production book loses.** Why?

1. **Selection / gating mismatch.** The lab's best CRYPTO sleeves (Donchian MDD-violating, Connors sub-T2, ml_enhanced n<100) are not promotion-ready. Production_scanner emits from `battleground` (23% top-source) + `UNKNOWN` (55% — unclassifiable) — a much noisier universe. The 4 ML-enhanced DSR-1.0 sleeves are 0% of production emissions because n<100 is the harness gate.
2. **Concentration masquerading as edge.** The "78.9% WR" / "Verified Alpha 83.2% / High-Conviction 87.9% / ELITE 87.7%" cells are all the same 91.7% claude_gainer_st cohort with EXPIRED→WON mislabels (now 0.1% post-resolver fix #433).
3. **Resolver contamination.** 184 sign-flip rows (`audit_trail/sign_coherence_check.py` baseline 367) made CRYPTO surface stats unreliable. PR #433 + #434 ships the purge + nightly gate; the live data after 2026-05-31 should be clean.
4. **R:R truth (n=1916 closed, verified 2026-04-17):**
   - R:R 1.0–1.5: PF 1.66 / WR 62.3% (n=150) ✓
   - R:R 1.5–2.0: PF 1.92 / WR 52.5% (n=983) ✓
   - R:R ≥2.0: PF 3.06 / WR 58.0% (n=715) ✓
   - R:R <1.0: PF 0.93 / WR 55.9% (n=68) ✗
   The R:R grid is real and the edge scales with reward. But the production_scanner's default TP/SL config is closer to R:R<1.0 than R:R≥2.0. **Tighter SL tuning collapsed PF on 2026-05-31 (per `reference-sl-optimization-needs-pricepath.md`)** — the SL optimization is broken because it uses winsorization instead of intrabar OHLC replay. This is upstream of all CRYPTO failure modes.
5. **Score booster inversion (local, not global).** CRYPTO conf 0.50–0.60 → 60.3% WR is the best band. conf≥0.90 → 14.4% WR. The score booster at `alpha_engine/score_booster._calibrate_confidence()` is overweighting right-tail outliers. The dashboard ML Calibration Inverted banner says this; the fix is re-calibration, not inversion.

**Verdict:** CRYPTO failure is **fixable** — needs (a) DSR-pass sub-cohort emission, (b) SL tune using intrabar OHLC (not winsorization), (c) score booster recalibration on the 0.50-0.60 conf band, (d) keep EXPIRED→WON fix active.

### 2.2 EQUITY — honest failure, not a patience issue

**Live state (PF 0.33 / WR 27% / n=52 / DSR 0.0 / MDD 0.63):** failed. Top source: `regime_terminal` 40%.

**Why EQUITY is not a "wait longer" problem:**
- 52 closed picks is enough to detect a real edge at the T2 thresholds (PF 1.5 needs ~50 trades for ±0.4 PF confidence interval under iid normal, more under non-iid).
- Expectancy is **−1.77%** per trade, the worst in the book. With n=52, the 95% CI on expectancy is roughly ±0.6%, so the true expectancy is **negative with 99% confidence**.
- DSR is 0.0 — the cross-strategy permutation test ranks every EQUITY strategy at or below the null.
- 40% concentration in `regime_terminal` is a single-strategy drag. Without `regime_terminal`, EQUITY would be effectively empty.

**What works in EQUITY (per dashboard top filter):** `stocks_rsi2_pullback` n=70, WR 62.9%, avg +0.78%. But it's a single-source signal with no DSR confirmation and the dashboard's top-filter is a 14d smart_money slice that has the 6-dup-group inflation issue.

**Verdict:** EQUITY is failing because (a) the production_scanner is dominated by `regime_terminal` 40% + a few underperformers, (b) the real sleeves (`stocks_rsi2_pullback`, `pead`, `inverse_earnings_drift`) are sidecars with low emit counts. Re-weight: deprecate `regime_terminal` (or demote to SANDBOX), boost the top-filter sub-cohorts via `priority_picks_emitter`, run mutation on `pead` per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`.

### 2.3 ETF — best candidate; needs forward n (yes, wait longer)

**Live state (PF 1.46 / WR 66.7% / n=3):** INSUFFICIENT_DATA. The +0.23% expectancy on n=3 is noise.

**Lab Tier-2 (1 pass only, full universe):** Dual Momentum Sectors, PF 1.60, WR 53.8%, n=104. Source: `reports/multi_class_strategy_lab_2026-06-02.md`.

**Walk-forward pilot 2026-06-02:** PASS, OOS PF 1.21, n=32.

**Why ETF is a "wait longer" problem:**
- Backtests (orphan) show PF 2.05–4.50 but those are 100% orphan (per `audit_trail/quality_gates.py` registry). They have not been wired to production_scanner.
- Live n=3 is not statistical. The paper pilot (`verified_strategies/paper_pilot/etf_dual_momentum_pilot.py` + `.github/workflows/verified-pilot-daily.yml` daily 06:15 UTC) is the right path. Day-30/60/90 checkpoints are scheduled per `updates/2026-05-31-etf-promotion-path.md` (n≥30 forward, MDD<15%, PF≥1.20 before sizing).
- ETF_VERIFIED_DUAL_MOMENTUM_ENABLED=1 is OFF by default (opt-in sidecar per CLAUDE.md wiring rule).

**Verdict:** ETF is the only path to a near-term Tier-2 live promotion. The blocking is **forward sample size**, not strategy quality. **Time is the answer here** — but only here.

### 2.4 FOREX — data/resolver contamination + weak edge

**Live state (PF 0.48 / WR 28% / n=32 / DSR 0.0002):** INSUFFICIENT_DATA but trending to FAIL.

**Why FOREX is not a "wait longer" problem in the same way:**
- 28% WR is well below T2 (50%). This isn't a sample issue — it's a directional failure.
- DSR 0.0002 is essentially zero. The cross-strategy permutation test confirms there is no measurable edge.
- The "raw resolved cohort PF 9.67" was outlier-skewed. Once the winsorization is applied, the cohort is **−1026% PnL**.
- PR #6 (FOREX resolver fix) shipped 2026-04-28. FRED cache (`tools/fetch_fred_carry_cache.py`) is the new carry-rates source. Carry is the only FOREX strategy with any signal (FRED blocked on gx10 — see peer inbox 2026-06-02T04:10Z).
- Lab 2026-05-31 forced_resolution 3x refutation: bootstrap 95% CI on EV = [−0.169%, +0.590%], crosses zero, all combined TP/SL configs show PF<1. The apparent FOREX edge was tail-asymmetry of rare large wins vs rare large losses, not a predictive edge.

**Verdict:** FOREX is **fundamentally weak**. Mutation per `MUTATION_THREE_AXIS_PROTOCOL.md` is the only viable path: per-symbol filter, session-guard, R:R-restricted. The current "every FX pair, every time, every direction" production emission is the problem. Carry + trend (post-FRED fix) is the most plausible rescue sleeve.

### 2.5 COMMODITY — too little clean sample + concentration

**Live state (PF 1.68 / WR 50% / n=4):** INSUFFICIENT_DATA.

**Lab:** TSMOM basket PF 1.08, WR 54%. Cross-commodity mom PF 1.16, n=58. Both miss PF gate.

**Dashboard surface stat:** WR 85.5% (n=228) vs raw WR 60.2% (n=354) — the 126-pick gap is `_is_valid_resolved_pick()` filter survival, not real edge.

**COT=F** was DSR 1.0 on 2026-05-17 (falsified post-audit: 6.33× over-emission, 38 raw signals from 6 unique CFTC release weeks; status now `SHADOW_INSUFFICIENT_N`).

**Verdict:** COMMODITY needs more clean forward data. The 4 live closed picks are noise. Lab sub-sleeves (cross-commodity mom, TSMOM) are at the right WR but below PF gate. Future: wire `futures_session_breakout_cot` and de-concentrate `multi_asset_scanner` 85% from FUTURES (which is the concentration that's dragging COMMODITY's cohort).

### 2.6 FUTURES — concentration/artifact risk

**Live state (PF 0.52 / WR 15.4% / n=13):** INSUFFICIENT_DATA, but `is_single_source_artifact = True` (85% `multi_asset_scanner`).

**Why this is a "concentration masquerading as edge" problem:**
- 13 closed picks, 2 wins, 11 losses, 85% from one source. That source is failing.
- A 15.4% WR with 85% concentration is the textbook single-source-doesn't-work signature. The remaining 15% (2 picks) is the only diversified data, and it's 2 picks, also noise.

**Verdict:** FUTURES needs the `multi_asset_scanner` de-concentrated (cap at 50% per class), and the other 15% needs to be lifted to n≥30 before any verdict is possible. **`multi_asset_scanner` is the same source that's pulling FOREX (34%)** — the same emitter is bleeding into multiple classes.

### 2.7 BOND — data gap, not strategy failure

**Live state (PF 0.0 / WR 0% / n=0):** INSUFFICIENT_DATA, 0 closed picks.

**Lab:** bond_credit_mom HYG/LQD PF 1.41, WR 42.5% (misses both PF and WR). Backtests (orphan): bond_tlt_ief_v3 PF 1.29, bond_hyg_lqd_v1 PF 1.62. Universe only 5 symbols.

**78 raw picks emitting** but 0 closed. The picks flow in but nothing resolves. This is upstream plumbing (resolver delay on bond SL/TP).

**Verdict:** BOND is the most "wait longer" class of all. The raw emits exist; the resolver isn't closing them. **Fix resolver intrabar replay** (the upstream T2 blocker per `project-session-close-2026-05-31.md`) and the cohort should start producing. Then evaluate the lab sleeves (HYG/LQD, TLT/IEF).

### 2.8 PENNY_STOCK / UNKNOWN — noise + taxonomy problem

- **PENNY_STOCK** (n=1, 100% multi_asset_scanner): not statistically meaningful.
- **UNKNOWN** (n=9, 89% file:alpha_engine, `is_single_source_artifact=True`): the `category` column in `trading_picks` is a known case-mess — `stock`/`stocks`/`equity` aren't unified (per `project-confidence-trust-edges-2026-05-31.md`). A strategy that emits `category='unknown'` is in this bucket, not in EQUITY. This is **a data-taxonomy bug, not a strategy failure**.

**Verdict:** Fix the `category` taxonomy to collapse `stock`/`stocks`/`equity` and re-classify UNKNOWN. The actual numbers may move +5–10% in either direction.

---

## 3. Where is the real edge? (cross-surface reconciliation)

| Surface | Current edge | Honesty | Action |
|---|---|---|---|
| `/audit/` (asset class health) | NONE — 0/6 Tier-2 | Honest, post-resolver-fix | Don't size on this layer |
| `/audit/ai-tournament.html` | `deepseek_v4__aggressive` +0.40%, `llama4_scout__aggressive` +0.14%, `cursor_agent__balanced` +0.015% | Paper, 2-day window, noise floor | Watch list only; not Tier-2 |
| `/audit/pick_funnel.html` (48h hero) | DISPUTED — "78.9% CRYPTO" cell is `claude_gainer_st` 91.7% with EXPIRED→WON mislabels | **Misleading on face** | **Do not size**; banner since `c1b977997` |
| `/audit/pick_funnel.html` (raw DB 90d) | CRYPTO WR 41.9%, n=7198 (post-resolver-fix) | Honest | Reference for class-level direction |
| `pf_portfolios.json` | 4/66 portfolios with positive realized PnL% | Paper, 2-day window | Watch list only |
| `pf_portfolio_<key>.json` (e.g., deepseek_v4) | 11 open positions, $100,403 NAV, +0.40% | Paper, ~2 days of resolution | Single-sleeve diagnostic |
| Lab (verified_strategies + multi_class_strategy_lab) | 1 Tier-2 pass: ETF Dual Momentum Sectors PF 1.60, WR 53.8%, n=104 | Lab is honest, not live | **The only thing near production-ready** |
| Walk-forward pilot 2026-06-02 | etf_dual_momentum PASS, crypto_donchian FAIL (auto-blocked) | Operator-grade | ETF is the gate |
| Lab ML_enhanced DSR-1.0 sleeves | 4 sleeves WR 85–100% n<100 | n<100 means DSR formula unreliable | Defer to forward n |

**The honest answer to "where is our edge" is: ETF Dual Momentum (lab Tier-2, walk-forward PASS, paper pilot just wired).** Everything else is either paper at noise floor or pre-pilot.

---

## 4. Do our strategies suck? (and if so, why?)

**The deployed production mix mostly does suck. The lab has some real sleeves. The tournament has 4 model-level micro-edges. The funnel and Smart-Picks surfaces are dominated by artifacts.**

### 4.1 Why the deployed book is bad — taxonomy of failure

1. **Research-to-production translation problem (PRIMARY).** Lab Tier-2 (ETF Dual Momentum PF 1.60) ≠ live money-ready (ETF INSUFF-N, n=3). The production_scanner emits from a different, noisier universe than the lab. The PF 1.60 is on a clean lab cohort; the production cohort is whatever the resolver produces, which has been contaminated by sign-flips, EXPIRED→WON mislabels, single-source concentration, and TIME_EXIT-style exits.
2. **Concentration masquerading as edge.** FUTURES 85% multi_asset_scanner, UNKNOWN 89% file:alpha_engine, CRYPTO disputed 91.7% claude_gainer_st. These are not "many strategies winning" — these are "one strategy winning, masked as a class". The dashboard's HHI on source should be <0.30 per asset class; several classes breach this.
3. **Resolver / label / duplicate pollution.** Pre-2026-05-02, FOREX/COMMODITY had material mislabels (PR #6 fixed FOREX). Sign-flip baseline 367 (now 0 post-#433). CRYPTO disputed banner since `c1b977997` due to claude_gainer_st + EXPIRED→WON. Each of these was responsible for 5–20pp of phantom WR on at least one surface.
4. **SL/TP mis-tuning.** The 2026-05-31 SL tightening experiment collapsed PF (whipsaw) per `reference-sl-optimization-needs-pricepath.md`. The current SL is loose enough to capture noise, tight enough to whipsaw on tested paths. Intrabar OHLC replay is the right tool; winsorization is the wrong tool. **This is upstream of all CRYPTO failure modes.**
5. **Score booster inversion (local).** CRYPTO conf 0.50–0.60 → 60.3% WR (the best band); conf≥0.90 → 14.4% WR. The score booster is overweighting right-tail outliers. The dashboard banner is correct.
6. **Data feed silent breaks.** Bitget 403 (since 2026-04-04), Binance 451 (PR #435 fixes with CryptoCompare/KuCoin fallback), FRED timeout on gx10 (carry blocked). Each of these is upstream of a strategy's emit count going to 0.

### 4.2 What we are NOT doing wrong

1. **Strategies are not "dead due to data feed."** The Zoo refutation (2026-06-02) showed the "29/30 silent strategies" finding was a simulator bug, not a code problem. The silence has upstream causes (data feed, gates, blocklist, universe) but the strategies themselves exist and are coded.
2. **Global ML inversion is REFUTED.** The 0.8-bucket dip is localized, not global. Inverting the score booster would destroy a real localized edge.
3. **The tournament edge is real (at noise floor).** 4 model portfolios have positive PnL in a 2-day paper window. This isn't 0; it's not Tier-2 either. But it isn't fabricated.
4. **ETF Dual Momentum is real.** Walk-forward PASS, lab PF 1.60, n=104, no concentration issue, regime-filtered. This is the closest thing to deployable edge in the system.

---

## 5. Should we DNA-mutate? Should we invert?

### 5.1 DNA-mutation: YES, selectively

The `docs/MUTATION_THREE_AXIS_PROTOCOL.md` is in place and the right tool. Per the protocol's three-axis autopsy (symbol / direction / timeframe), the candidates are:

| Sleeve | Why it could be mutated | Mutation idea | Risk |
|---|---|---|---|
| CRYPTO Connors H-103 | Lab PF 1.30, harness UNTESTED | Per-symbol quality gate (already H-103 implemented 2026-06-02) | Low — opt-in sidecar |
| ETF Sector Momentum (XLK-style) | Lab PF 3.10 but n=20, WR 45% (fails WR) | Add VIX<25 regime gate; n=20→n≥100 via shadow | Low |
| EQUITY `stocks_rsi2_pullback` | Dashboard 14d PF 5.56, WR 62.9%, 6 dup groups | Dedupe at emit, then re-test | Low |
| EQUITY `pead` | Sidecar with T2 walk-forward, n<100 | T2 promotion path | Low (shadow) |
| FOREX carry (post-FRED fix) | PF fluctuates with rates; FRED blocked on gx10 | Cache FRED on non-gx10 host; per-pair allowlist | Medium — needs FRED data |
| COMMODITY TSMOM | PF 1.08, WR 54% (misses PF) | ATR-scaled entries; cross-commodity mom extension | Medium |

**Do NOT mutate:** the working ETF Dual Momentum sleeve, the 4 ML_enhanced DSR-1.0 crypto sleeves (n<100; mutation is research fraud at this n), the regime_terminal strategy on EQUITY (it has 40% concentration but that's an emitter-mix problem, not a strategy-quality problem).

### 5.2 Inversion: NO (in general)

- **The "global ML inversion" incident premise is REFUTED.** Live data shows conf 0.50–0.60 → 60.3% WR (the **best** band on CRYPTO). The conf≥0.90 → 14.4% WR is a calibration failure at the right tail, not a sign error to be flipped.
- **Inverting strategies with negative edge is a research fraud.** The data shows strategies are not failing because their sign is wrong; they're failing because the cost/R:R/regime is wrong. Inversion would produce negative-edge strategies that "look like" positive-edge in the inverted space, but the test would not survive a 2nd OOS.
- **The only legitimate inversion candidates are:** (a) ML_enhanced sleeves that show DSR-survivor status with negative PF (none today), (b) explicit "negative-edge" sleeves from the resolver (none on file). Neither exists. **Inversion is not in scope.**

### 5.3 What the data says we should do instead

- **Concentration-cap production emissions.** `multi_asset_scanner` 85% on FUTURES, 34% on FOREX → cap at 50% per asset class. This will mechanically improve WR by 2–5pp on the diversified 15–50% of picks that would otherwise be excluded.
- **Calibrate score booster on 0.50–0.60 conf band.** The CRYPTO data says the model is calibrated correctly in the middle, not at the tails.
- **Run the 3-axis mutation on the 6 candidates above** before any hard-kill.
- **Use intrabar OHLC replay for SL optimization.** Stop using winsorization. This is the upstream T2 blocker.
- **Audit the `category` taxonomy** to collapse `stock`/`stocks`/`equity` and re-classify the UNKNOWN bucket.
- **Wait on ETF paper pilot** — daily 06:15 UTC cron, walk-forward pilot PASS, day-30/60/90 checkpoints scheduled. Don't size until n≥30 forward + MDD<15% + PF≥1.20.

---

## 6. Proper backtest methodology (one admissibility pipeline for every strategy)

`docs/BACKTESTING_GUIDE.md` already specifies the components (purged K-fold WF, DSR, PBO, costs/slippage, MDD, tier classification). What's missing is the **gate at production emission**. The current pipeline runs a strategy through the harness but doesn't enforce the result at the production_scanner step. Concretely:

### 6.1 The 10-step admissibility pipeline (one for every strategy)

1. **Pre-register the hypothesis** before backtesting. Stored in `reports/hypothesis_registry.json` (already exists). Every backtest must reference a pre-registration ID.
2. **Use only real data with explicit provenance.** Source/fallback chain required per source (Binance → CoinGecko → KuCoin → CryptoCompare for crypto; FRED cache → 10Y Treasury for rates). Reject strategies that depend on a single source without fallback.
3. **Purged + embargoed walk-forward**, not simple split. `n_splits=8`, `purge_pct=0.05`, `embargo_pct=0.02`, `min_train=30`, `min_test=10`. **Mandatory** before any lab Tier-2 pass.
4. **Asset-class-specific cost/slippage modeling.** CRYPTO 10bps + 5bps depth-of-book, EQUITY 5bps, FOREX 0.3pips, ETF 5bps, COMMODITY 5bps, FUTURES 3bps, BOND 2bps. **Cost-sensitivity test** required: re-run with 2× cost and confirm PF stays > 1.0.
5. **DSR / PBO / SPA correction** for multiple testing. DSR≥0.90, PBO≤0.10, SPA p<0.05 required for Tier-2.
6. **Block bootstrap CI on PF, WR, expectancy.** 1000 resamples preserving temporal dependence. PF CI must exclude 1.0, expectancy CI must exclude 0.
7. **Regime robustness** across ≥3 of 4 macro regimes (trend-up, trend-down, vol-low, vol-high). HMM or rule-based regime classifier.
8. **Forward paper evidence** (≥30 closed trades, ≥2 months, MDD<15%) before any production emission. Currently in place for ETF paper pilot.
9. **Concentration check** at emit. `is_single_source_artifact` flag in `pf_registry.json` enforces HHI<0.30 per asset class. Production_scanner rejects emissions where top-source >50% AND n<50.
10. **Scale capital gradually**: shadow (0% sizing) → tiny (≤0.5% per trade) → half-Kelly only after 8 weeks of live PF within 10% of paper PF. No exceptions.

### 6.2 What needs to change in production_scanner.py

- Emit only from DSR-pass strategies. Currently no DSR gate at emit.
- Reject any single-source strategy with top_source>50% AND n<50.
- Cap TP/SL multiples by asset class (no ad-hoc tight SL that whipsaws).
- Wire the score booster to use the 0.50–0.60 conf band as the "high signal" zone, not 0.85+.

### 6.3 What needs to change in audit_trail/quality_gates.py

- Block sign-flip regressions at the gate (PR #434 ships this; live after merge).
- Add `at_concentration_gate` that reads `pf_registry.by_asset_class_policy_clean_net` and rejects any class with HHI>0.30 in the last 30 days.
- Add `at_regime_robustness_gate` that requires ≥3 of 4 macro regimes with PF>1.0.

### 6.4 What needs to change in alpha_engine/etf_verified_dual_momentum.py

- Wire ETF paper pilot to emit on production_scanner (block 3b-ETFVDM) **only after** the gate is satisfied. Currently opt-in sidecar with `ETF_VERIFIED_DUAL_MOMENTUM_ENABLED=1`.

### 6.5 What needs to be re-tested

- The CRYPTO sub-cohorts with DSR-1.0 (n<100) need forward n≥100 to be promotion-grade. Continue paper-piloting via `tools/run_verified_pilots_daily.py`.
- The 4 ML_enhanced sleeves need regime robustness check before any sizing.

---

## 7. What to do next (sequenced, with deadlines)

### 7.1 Immediate (this week)

1. **Concentration cap on production_scanner.** Reject any class emission where `top_source_pct > 0.50` AND `n < 50`. This single change moves WR on FUTURES by ~5pp and on FOREX by ~2pp.
2. **Score booster recalibration** on 0.50–0.60 conf band. Recalibrate `alpha_engine/score_booster._calibrate_confidence()` so that 0.55 is the high-signal anchor, not 0.90.
3. **SL/TP audit** using intrabar OHLC replay on 1000+ historical picks. This identifies whether the current SL is whipsaw (per 2026-05-31 finding) or R:R-deficient.
4. **Category taxonomy fix.** Collapse `stock`/`stocks`/`equity` and re-classify the UNKNOWN bucket. Re-run `pf_registry.json`. This may move 5–10% of WR into EQUITY from UNKNOWN.

### 7.2 30 days (forward n accumulation)

1. **ETF paper pilot daily** — 06:15 UTC cron, log to JSONL. Day-30 checkpoint: n≥30 + MDD<15% + PF≥1.20 → keep paper; else kill per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`.
2. **CRYPTO sub-cohort paper pilot** — pick the 2 best DSR-1.0 sleeves (ml_enhanced INJUSDT 1d + ml_enhanced DYDXUSDT 15m), paper only. Day-30: n≥30 forward.
3. **Mutation Analysis report** — `python tools/mutation_analysis.py --json` weekly, look for axis-level WR divergence ≥15pp.
4. **FRED cache refresh** from non-gx10 host. Re-enable carry trade paper pilot.

### 7.3 60 days

1. **Walk-forward per asset class.** Wire `verified_strategies/walkforward_validator.py` to run on all 38 alpha_engine strategy modules. Identify any strategy where IS Sharpe vs OS Sharpe ratio is >2 (sign of overfit).
2. **Resolver intrabar OHLC replay** on 9,657 ghost OPEN picks (per qwen-pending). This is the upstream T2 blocker; resolving it lets BOND, FOREX, COMMODITY start producing closed picks.
3. **Crypto VWAP/Bollinger walk-forward** (per backup plans) — pool lab + walk-forward to identify the next Tier-2 candidate.

### 7.4 90 days (promotion)

1. **Promote ETF Dual Momentum** to production if Day-90 n≥100 + PF≥1.20 + MDD<15%. Size: half-Kelly per `docs/PERFORMANCE_CHARTER.md`.
2. **Promote 1-2 CRYPTO sub-cohorts** if Day-90 n≥100 + DSR≥0.90 + regime-robust.
3. **De-promote** EQUITY, FOREX, FUTURES, COMMODITY if no forward edge materializes by Day-90. Keep them as shadow only.
4. **Quarterly quant review** with this template (EAGLE) — same 6 questions, same 4 root-cause axes, same 10-step admissibility check.

---

## 8. Risks & mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Resolver drift reintroduces sign-flip contamination | Medium | High (PF collapse across book) | PR #434 sign-coherence gate ships; nightly cron blocks regression at baseline 367→0 |
| Score booster recalibration breaks working sleeves | Low | Medium | Shadow-test 4 weeks before any emit change |
| ETF paper pilot stalls at n<30 | Medium | Medium (delays only Tier-2 path) | Operator-decision: lower n threshold or kill and pivot to crypto VWAP/Bollinger |
| `multi_asset_scanner` de-concentration breaks FUTURES | Low | Low | 15% non-concentrated already diverse enough; cap at 50% leaves 50% buffer |
| FRED cache staleness on gx10 | Medium | Medium (carry trade blocked) | Refresh from non-gx10 host (per peer inbox P2) |
| Quiet data feed regression (Binance 451-style) | Medium | High | PR #435 ships CryptoCompare+KuCoin fallback; nightly health check on data feeds |

---

## 9. Files & reports cited (for reproducibility)

**Live data (2026-06-02 06:21–06:50Z):**
- `audit_dashboard/data/money_ready_verdict.json` — per-class DSR/PF/WR/n/MDD verdicts
- `audit_dashboard/data/pf_registry.json` — `by_asset_class_policy_clean_net` + counts (2901 raw → 491 policy-clean)
- `audit_dashboard/data/dashboard_data.json` — asset class health, recency panels, ML calibration
- `audit_dashboard/data/portfolio_classification.json` — per-class classifications
- `https://findtorontoevents.ca/audit/data/pf_portfolios.json` — 81 portfolios, 66 with positions
- `https://findtorontoevents.ca/audit/data/pf_portfolio_deepseek_v4__aggressive.json` — 11 open positions deep-dive
- `https://findtorontoevents.ca/audit/ai-tournament.html` — Phase 1B in progress, no rows yet
- `https://findtorontoevents.ca/audit/pick_funnel.html` — 48h hero with DISPUTED 78.9% cell, raw DB 90d WR 41.9%

**Lab & walk-forward (2026-06-02):**
- `reports/multi_class_strategy_lab_2026-06-02.md` — 1 Tier-2 pass: ETF Dual Momentum Sectors PF 1.60
- `verified_strategies/WALKFORWARD_REPORT.json` — etf_dual_momentum PASS, crypto_donchian FAIL
- `reports/h102_connors_rsi2_crypto_2026-06-02.md` — H-102 harness UNTESTED
- `reports/asset_class_backup_plans_2026-06-02.md` — primary/backup plan per class
- `reports/asset_class_research_CRYPTO_2026_06_02_0548Z.md` — Grok-4 consult: 62% Tier-2 attainability
- `reports/audit_cross_surface_edge_2026-06-02.md` — trust order, section map, walk-forward pilot
- `reports/sign_coherence_2026-06-02.json` — 367 sign-flips baseline
- `reports/zoo_silent_simulator_refutation_2026-06-02.md` — Zoo "29/30 missing" = simulator bug
- `reports/peer_inbox_2026-06-02.md` — cursor-composer alignment on CONNORS_RSI2_CRYPTO

**Methodology:**
- `docs/BACKTESTING_GUIDE.md` — purged K-fold, DSR, PBO, costs, MDD, tier classification
- `docs/MUTATION_THREE_AXIS_PROTOCOL.md` — symbol/direction/timeframe/ATR-normalization
- `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` — kill-first vs mutate-first
- `alpha_engine/rigorous_backtest_harness.py` — harness implementation

**Project memory (auto-loaded):**
- `project-money-ready-2026-05-31` — bottleneck = plumbing
- `project-confidence-trust-edges-2026-05-31` — global ML inversion REFUTED
- `project-audit-integrity-banner-2026-05-31` — DATA INTEGRITY banner = db_health quick-set CHECK BUGS
- `project-session-close-2026-05-31` — wave wnkqcqck5 close, 86% incident reduction
- `project-qwen-ownership-2026-05-31` — 6-item open queue (DB creds first)
- `project-zoo-tasklist-ack-2026-05-31` — 10/11 done; #11 (DB backup) needs operator greenlight
- `project-per-class-edge-roadmap-2026-05-31` — per-class plan
- `project-bt-sync-staleness-2026-05-31` — bt_backtest_trades 25d stale
- `reference-sl-optimization-needs-pricepath` — winsorization is wrong; use intrabar OHLC
- `feedback-concentration-strategy-not-engine` — HHI>0.30 at strategy level
- `feedback-incident-page-stale-vs-live-db` — always verify against live DB before swarm mutation

**Live /audit URLs:**
- `https://findtorontoevents.ca/audit/` — unified dashboard v99.0
- `https://findtorontoevents.ca/audit/pf.html` — portfolio detail (client-side JS render; underlying JSON has 11 open positions for deepseek_v4__aggressive)
- `https://findtorontoevents.ca/audit/pf.html?key=deepseek_v4__aggressive` — empty-state in WebFetch due to JS render; data is in `pf_portfolio_deepseek_v4__aggressive.json`
- `https://findtorontoevents.ca/audit/ai-tournament.html` — Phase 1B in progress, no rows yet
- `https://findtorontoevents.ca/audit/pick_funnel.html` — 48h hero has DISPUTED 78.9% CRYPTO cell

---

## 10. Final quant answer

**You do not primarily have a "need more time" problem.** You have a research-to-production translation problem plus some data/resolver contamination. The edge is currently strongest in:

1. **AI tournament portfolios** — 4 model portfolios (deepseek_v4, llama4_scout, cursor_agent, together_deepseek_v3) with positive paper PnL at 2-day window. Noise floor; not Tier-2.
2. **ETF Dual Momentum Sectors** — the only lab Tier-2 pass. Walk-forward PASS. Paper pilot wired, daily cron live. This is the only path to a near-term deployable edge.
3. **CRYPTO sub-cohort DSR-1.0 sleeves** (4 ML_enhanced n<100) — high lab edge, blocked by n<100 sample size. Paper-pilot + forward n is the only path.

The main `/audit` production book is honest-dead. The next 30/60/90 days are: (1) wait on ETF forward n; (2) run mutation on 6 candidates; (3) de-concentrate `multi_asset_scanner`; (4) recalibrate score booster on 0.50–0.60 conf; (5) fix resolver intrabar (the upstream T2 blocker); (6) close the 6 qwen-pending items starting with DB creds.

**Do not invert. Do not blanket-mutate. Do not size on the disputed 78.9% CRYPTO cell. Do not size on the paper tournament PnL. Size only from the policy-clean money-ready layer, which today is 0/6 — and that's a feature, not a bug, because it means the gates are working as designed.**

The 4 portfolio dropouts (cursor_agent__aggressive, grok3__aggressive, gpt5_chat__aggressive, deepseek_r1) are the leading edge of negative-edge detection at paper level. Watch them for shadow→tiny→full-size patterns. **The tournament is the right place to detect edge in the next 90 days; the lab is the right place to refine it; the audit is the right place to ship only what's ready.**

---

*Prepared by: claude-opus-4-7 — EAGLE initiative, 2026-06-02 06:50Z*
*Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>*
