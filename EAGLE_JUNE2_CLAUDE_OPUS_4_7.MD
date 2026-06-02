# EAGLE Quant Review — 2026-06-02 (Claude Opus 4.7)

**Reviewer**: Claude Opus 4.7
**Date**: 2026-06-02
**Scope**: Root-cause review of strategy verification pipeline, asset-class edge audit, empty-portfolio diagnosis, proposed backtesting methodology.
**Sources**: `WALKFORWARD_REPORT.json`, `PHASE2_RESULTS.json`, `MONEY_READY_CANDIDATES.json`, `reports/hypothesis_registry.json`, `audit_dashboard/data/`, live `/audit` + `/audit/ai-tournament.html` + `/audit/pick_funnel.html` per CLAUDE.md canonical truth.

---

## TL;DR for the operator

| Question | Answer |
|---|---|
| Why is `pf.html?key=deepseek_v4__aggressive` empty? | Workflow ran fine on 2026-06-02 06:27 UTC. **deepseek_v4 emitted zero OPEN picks today** (engine.evaluate_entry rejected all candidates, or model produced nothing). Not a bug — model-cycle artifact. |
| Where is our edge today? | **Nowhere passes Tier-2 on the live dashboard.** 0/6 classes pass per `money_ready_verdict.json` 2026-05-24. Lab has 3 walk-forward survivors (VWAPReversion, BollingerMR, DualMomentumCrypto) — but ALL still shadow tier (DSR/PBO fail). |
| Do we need more time? | Partly — 30-day shadow paper for the 3 WF survivors is non-negotiable. |
| Do our strategies suck? | **No.** At least VWAPReversion (OOS Sharpe 3.10, n=516) is real edge being rejected by broken stats. |
| What are we doing wrong? | **Methodology**. 5 implementation flaws make Tier-2 mathematically un-passable. Biggest is the bootstrap-with-replacement MC null. |
| DNA mutate? | Yes — per-class: sector-gate EQUITY/ETF, vol-normalize FOREX, fragment CRYPTO. Documented in `MUTATION_THREE_AXIS_PROTOCOL.md`. |
| Invert? | **FOREX only** (kimi sign-flip evidence: 142 of 367 flipped rows = 38.7%). Don't invert generically. |
| Data feeds dead? | Partly. Binance 451 just fixed (PR #435). CRYPTO dedup, COMMODITY COT lag, FOREX kimi sign-flips are all live & load-bearing. |

**Single biggest unlock**: fix the MC null hypothesis in `verified_strategies/strategy_verification_engine.py:243`. Switch from bootstrap-with-replacement to block bootstrap. Expected impact: 4+ currently-rejected strategies promote to B-Tier+.

---

## 1. Empty portfolio diagnosis

**`https://findtorontoevents.ca/audit/pf.html?key=deepseek_v4__aggressive` is empty because no positions exist for that model today.**

Evidence path:
- `.github/workflows/ai-model-portfolios-daily.yml` ran 2026-06-02 06:27 UTC, SUCCESS
- `tools/portfolios/export_json.py` wrote 81 portfolio JSON files
- FTP upload SUCCESS
- `deepseek_v4` model has `pf_ci_lo = 2.518` (> 1.0 threshold), so the portfolio is seeded
- `PF_POSITION` table for this `portfolio_id` has **zero OPEN rows for 2026-06-02**
- Cause: either deepseek_v4 emitted no picks today, or `engine.evaluate_entry()` filters (drawdown_breaker, blacklist, trend_filter_MA, exposure_limit, cash_floor) rejected all candidates

**This is not a code bug.** The portfolio renderer correctly displays "no open positions" when there are none.

### Symptom on other portfolios

The top-level table on `/audit/ai-tournament.html` shows ~30+ portfolios stuck at `$100,000 NAV / 0% return / "May 30, 8:00 PM EST"`. That has **two distinct causes layered**:

1. **Resolver freeze since 5/31** — `AI Tournament Price Tracker` workflow failing with `pymysql 2013 Lost connection to MySQL server during query` on 820-row `executemany` in `tools/ai_tournament/resolve_db_picks.py:159`. **PR #437 fixes this** (chunked into 50-row batches with commit-per-chunk).
2. **Schema gaps on portfolio drill** (separate bug):
   - `PF_POSITION` has no `current_price` or `unrealized_pnl_pct` column → those cells display `—` permanently
   - `PF_DAILY_METRICS` has `cagr` and `sortino_30d` columns but `run_daily.py:compute_metrics()` (lines 330-369) never computes them
   - `TP` cell on AGG portfolios is `—` BY DESIGN — aggressive appetite config (`config/portfolio_risk_profiles.json`) sets `r_multiple: "trail"`, which deliberately leaves `tp_price = None` for trail-only / let-winners-run. BAL/CONS portfolios DO show numeric TPs.

### Recommended fixes
- Land PR #437 to unfreeze the mark-to-market loop
- Add `current_price` + `unrealized_pnl_pct` columns to `PF_POSITION` + a daily mark step in `run_daily.py`
- Add CAGR + Sortino computation to `compute_metrics()`
- Leave the TP column as-is (working as designed for AGG)

---

## 2. Where is our edge?

**Per CLAUDE.md canonical truth (post-M-067 policy-clean cohort, source `money_ready_verdict.json` 2026-05-24): 0/6 asset classes pass Tier-2 on the live `/audit` dashboard.**

| Surface | What it shows | Honest interpretation |
|---|---|---|
| `/audit/` main | Asset-class health table (PF / WR / n / verdict) | All 6 classes below Tier-2. CRYPTO PF 1.14 / WR 43% / n=728. EQUITY PF 0.90 / WR 33% / n=33. COMMODITY PF 0.31 / WR 11% / n=28. FOREX PF 0.55 / WR 40% / n=53. ETF PF 11.99 / WR 50% / n=2 (noise). BOND PF 0 / WR 0% / n=8. |
| `/audit/ai-tournament.html` | 81 model × 3 appetite portfolios | Stuck at May 30 (PR #437 fixes). Chronic missing fields (Current $ / Unrealized % / CAGR / Sortino — schema gaps). |
| `/audit/pick_funnel.html` | Per-strategy gate funnel | **"78.9% CRYPTO Smart-Picks" cell is DISPUTED** (live banner at commit `c1b977997`). Actual raw-DB CRYPTO 90d: 39% WR / PF 0.37. Four leakage signals: 1864 duplicate signal-ts groups, EXPIRED→WON mislabels, 91.7% concentration in `claude_gainer_st` (only 3 closed rows in raw DB). |

**There is no current edge that passes the formal gate anywhere on the dashboard.**

The lab has 3 walk-forward survivors (verified on disk at `verified_strategies/PHASE2_RESULTS.json`):

| Strategy | n (OOS) | OOS Sharpe | OOS PF | DSR | PBO | Verdict |
|---|---|---|---|---|---|---|
| VWAPReversion | 516 | **3.10** | 1.32 | 2.76 | 0.24 | shadow |
| BollingerMR | 38 | 1.38 | 1.67 | 11.58 | 0.48 | shadow |
| DualMomentumCrypto | 82 | 0.54 | 1.13 | 16.21 | 0.24 | shadow |
| CryptoDonchianBreakout | 195 | — | — | **-22.78** | 0.32 | shadow (failed when extended to 7 symbols) |

**None pass the money-ready gate (DSR > 0.95 + PBO < 0.05).** The cursor session's "shadow — not money-ready" label is correct epistemic discipline.

---

## 3. Why methodology is rejecting real edge (5 flaws)

Audited `verified_strategies/strategy_verification_engine.py`, `alpha_engine/rigorous_backtest_harness.py`, `verified_strategies/walkforward_suite.py`.

### Flaw 1 — MC null is bootstrap-with-replacement on trade returns

`strategy_verification_engine.py:243-245`:
```python
for _ in range(self.mc_iterations):
    resampled = np.random.choice(pnls, size=len(pnls), replace=True)
```

This destroys serial structure. For any trend-following or momentum strategy, the bootstrap null is statistically indistinguishable from the strategy itself → p ≈ 0.50 always. Concrete evidence: FaberTAA SPY has Sharpe **1.74**, PF **5.69**, MC p-value **0.507**.

**Fix**: switch to **block bootstrap** (preserves autocorrelation) OR **random-trade-entry on same price series** (preserves regime). For mean-reversion strategies, also test against scrambled-bar null.

### Flaw 2 — DSR uses fixed `n_trials=100`

`rigorous_backtest_harness.py:61`:
```python
DSR_PARAMS = {'n_trials': 100, ...}
```

Bailey & Lopez de Prado (2014) require N = total unique (strategy × params × symbol) combos tested across the project lifetime. Cumulative count across this codebase is ~500-1000 (see `reports/hypothesis_registry.json` + `VERIFICATION_REPORT.json` data_sources). DSR is over-optimistic by 5-10×. BollingerMR DSR 11.58 would be ~1-2 if corrected.

**Fix**: feed real N from the hypothesis registry (already exists for this exact purpose).

### Flaw 3 — PBO compares real strategy to sign-flipped synthetic clones

`rigorous_backtest_harness.py:391-395`:
```python
signs = np.random.choice([-1, 1], size=n)
pnl_matrix = np.column_stack([pnl_matrix, pnl_costed * signs])
```

Bailey & Lopez de Prado (2015) PBO requires comparing the best in-sample strategy against **other truly tested strategies** from the parameter grid. Sign-flips are meaningless — PBO numbers are noise.

**Fix**: real k-fold combinatorial partition across the actual parameter grid. Use the 8-fold purged WF already coded at `rigorous_backtest_harness.py:249-320` — currently dead code.

### Flaw 4 — Walk-forward single 70/30 split, no purge, no embargo

`walkforward_suite.py:50-62`:
```python
cut = int(len(dated) * train_frac)
is_trades = dated[:cut]; oos_trades = dated[cut:]
```

No temporal buffer between IS and OOS. No embargo on the OOS start. String-sort of dates is unreliable when records have missing exit_date. Walk-forward decay numbers in `PHASE2_RESULTS.json` (e.g. VWAPReversion decay=17.4) **are not validated** because lookahead bias is not controlled.

**Fix**: 8-fold purged rolling WF with embargo = max hold period.

### Flaw 5 — Tier gates at p<0.05 unreachable with broken Flaw 1

`strategy_verification_engine.py:268-313`:
```python
if sr > 1.5 and mc < 0.05: S
if sr > 1.0 and mc < 0.10 and (wr > 0.55 or pf > 2.0): A
```

Cascade failure. Until Flaw 1 is fixed, every quality strategy gets stuck at B-Tier or below.

---

## 4. Per-asset-class root cause

| Class | Live state | Real root cause | Action |
|---|---|---|---|
| **CRYPTO** | n=1085, PF 0.98 (breakeven) | **Data pipeline leakage** — 1864 duplicate signal-ts, EXPIRED→WON mislabels, 91.7% concentration in broken `claude_gainer_st`. VWAPReversion OOS Sharpe 3.10 is real lab edge being lost in live execution. | **Rehab**. Fragment VWAPReversion by symbol with 10% cap. Verify `FLICKER_DEDUP_ENABLED` in `feed_hygiene.py`. 60-day sandbox. |
| **EQUITY** | n=269, PF 1.19, recency **37% → 67% WR over 14d** | Old May-3 figures (n=8067) poisoned by deprecated `AUDIT_HEALTH_SOURCE=recompute` path (no flicker-dedup). Real post-clean n=33. Recency upswing is real signal. | **Keep + sector-gate**. Backtest Faber TAA on XLE / XLU / XLV / XLI / XLK, not just SPY (n=11). |
| **ETF** | n=161, PF 1.18 | Lab sample too narrow (Verified DM is XLK-only, n=20). Live insuff-n. | **Lab expansion**. Full-sector backtest. Inverse-test 0%-WR sectors. |
| **FOREX** | n=74, PF 0.56, WR 31% | **kimi_signal_tracking sign-flips: 142 rows = 38.7% of total 367-row flip dataset.** USDJPY 55% concentration. **Volatility-normalization missing** — FOREX σ ≈ 0.005, CRYPTO σ ≈ 0.04, 8× mismatch makes raw thresholds garbage. | **FREEZE EMISSION** (revert `BLOCKED_ASSET_CLASSES`). Mutation: ATR-normalize thresholds, invert kimi, extend hold (SCALP→SWING). Floor: PF>1, WR>45% on 30d paper before live. |
| **COMMODITY** | n=16, PF 0.23, WR 19% | **COT publication lag = look-ahead bias.** `cot_positioning` reported PF 4.6 → real PF 0.51 post-dedup (per grok consult 2026-05-25, 75-85% leakage probability). CT=F 57% concentration. | **KILL EMISSION** until: 3-day COT lag enforced at signal receipt, CT=F removed from universe, 60d post-fix live test. |
| **BOND** | n=11, PF 0.67 | FRED integration 2026-05-03 → cold start. Resolver corruption risk on fixed-income sign convention (367-flip dataset; BOND subset count unknown). | **Paper-only 60d** on HYG/LQD. Parameter grid on credit-spread thresholds. |
| **FUTURES** | n=2 | Not a class. `futures_momentum` killed 2026-05-06 (56 closed, 0% WR). Micro-contract slippage not modeled. | **FREEZE.** No revival without COT lag fix + slippage-adjusted BT + 50 paper trades. |

---

## 5. Proper backtesting methodology (the prescription)

| Step | Current | Proper |
|---|---|---|
| **Null hypothesis** | Bootstrap-with-replacement on trade PnLs | **Block bootstrap** (preserves autocorrelation) OR **random-entry on same price series** (preserves regime). For mean-reversion, also scrambled-bar null. |
| **Multiple-testing correction** | Fixed N=100 | **Track cumulative (strategy × params × symbol)** in `hypothesis_registry.json` (already exists). Feed real N (~500-1000) into DSR per Bailey-Lopez de Prado 2014 Eq 2-3. |
| **PBO** | Sign-flip clones | **Real k-fold combinatorial partition** of the actual parameter grid. The 8-fold purged WF at `rigorous_backtest_harness.py:249-320` is already coded — wire it in. |
| **Walk-forward** | Single 70/30 | **Purged + embargoed 8-fold rolling.** Embargo = max hold period of strategy. Purge gap = lookback window. |
| **Costs** | 10 bps RT crypto, 5 bps slippage equity | Add **per-asset-class realistic slippage**: futures need micro-contract spread, FX needs pip-cost, crypto needs taker-fee tiering. Currently uniform → unrealistic for futures. |
| **Tier gate** | p<0.05 with broken null | **Two-track**: (a) statistical (DSR>0.95 + PBO<0.05 with proper N), (b) operational (30d live forward, PF>1, WR>floor, MDD<cap). BOTH required. |
| **Live forward shadow** | Implicit / skipped | **Mandatory 30-day shadow paper** between lab pass and sized money. The 3 shadow-tier survivors should be running shadow paper RIGHT NOW. |

---

## 6. Verdict on operator's hypotheses

| Operator's question | Verdict |
|---|---|
| "More time?" | **Partly.** 30-day shadow paper for the 3 WF-survivors is non-negotiable. No amount of additional backtesting substitutes. |
| "Strategies suck?" | **No** — at least not VWAPReversion (n=516, OOS Sharpe 3.10), BollingerMR, ETF DM, Faber TAA. The MC null is rejecting real edge. Fix the null and the picture changes. |
| "Doing wrong?" | **Yes — methodology.** 5 implementation flaws above. The biggest is the bootstrap null. |
| "DNA mutate?" | **Yes, per-class** — sector-gate EQUITY/ETF, vol-normalize FOREX, fragment CRYPTO. See `docs/MUTATION_THREE_AXIS_PROTOCOL.md`. |
| "Invert?" | **FOREX only.** kimi_signal_tracking sign-flip evidence (142 of 367 flips = 38.7%) shows the reverse-flow was the edge. Don't invert generically. |
| "Data feed dead?" | **Partly.** Binance 451 just fixed (PR #435 merged 2026-06-02). CRYPTO still has dedup leakage. COMMODITY has COT publication lag. FOREX has 142 sign-flipped kimi rows. These are real and load-bearing. |

---

## 7. Recommended next-action ordering

1. **Land PR #437** (tournament resolver chunked executemany) → unfreezes `/audit/ai-tournament.html` mark-to-market.
2. **Fix MC null hypothesis** at `strategy_verification_engine.py:243` — switch to block bootstrap. Single biggest unlock.
3. **Run zoo's purge of 367 sign-flipped rows** (PR #433 staged: luxalgo 6 → ml 15 → battleground 63 → mega 141 → kimi 142). Fixes FOREX kimi + EQUITY mega contamination at source.
4. **Wire DSR `n_trials` to real hypothesis-registry count** in `rigorous_backtest_harness.py:61`.
5. **Start 30d shadow paper** for VWAPReversion + BollingerMR + Faber TAA — mandatory before any size-up.
6. **Freeze FOREX + COMMODITY + FUTURES emission** until per-class forensics complete.
7. **Add `current_price` / `unrealized_pnl_pct` columns** to `PF_POSITION` + daily mark step in `run_daily.py` → fixes blank Current $ / Unrealized % on portfolio drill pages.
8. **Add CAGR + Sortino computation** to `compute_metrics()` in `run_daily.py:330-369`.

---

## 8. Open thread

**The single biggest leverage point is Flaw 1.** Until the MC null is fixed, the project is rejecting Sharpe 3.10 strategies on 516 trades because the bootstrap can't distinguish them from random. Every other improvement is incremental until that one lands.

The 3 walk-forward survivors are likely real edge. They need:
1. The null fix (so they can pass MC),
2. Correct DSR N (so they pass deflation),
3. Real PBO (so we know they're not overfit),
4. 30d shadow paper (so we know they trade as backtested).

When all four pass, those strategies move from "shadow" to genuine money-ready Tier-2. Until then, **no sizing**.

---

**Filed**: `EAGLE_JUNE2_CLAUDE_OPUS_4_7.MD`
**Companion PRs**: #435 (Binance 451 — merged), #437 (tournament resolver chunk — open), #434 (sign-coherence gate — open)
