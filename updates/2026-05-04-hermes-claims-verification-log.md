# Hermes claims verification log — 2026-05-04

Session-long log of every Hermes-agent claim that was verified or refuted against actual data this session. Future operators reading prior `CHATWITHCLAUDE*.md` / `URGENT_CLAUDE_FROMHERMES.md` content should consult this file before acting.

**Pattern across the session:** ~80% of specific Hermes numeric claims either (a) come from stale hardcoded HTML/JS values rather than current data, (b) cite metrics with no underlying audit trail, or (c) are dollar-PnL projections with no derivation. **Always grep the JSON / DB before integrating.**

---

## ✅ CONFIRMED — actionable, real

### `regime_terminal` Gaussian HMM engine — **MAJOR FINDING, already wired**
**Hermes claim:** Production-grade `hmmlearn` Gaussian HMM at `findtorontoevents.ca/regime_terminal/`. 7-state HMM with 3-bar hysteresis, scans 43 symbols across 6 categories, generates 12 live signals with leverage multipliers (0.5x/0.75x/1.5x/2.0x).

**Verdict:** **CONFIRMED.** Engine is real and **already wired into production**:
- `regime_terminal/hmm_engine.py:25` `from hmmlearn.hmm import GaussianHMM`
- `regime_terminal/config.py:46` `MIN_REGIME_BARS=3` (hysteresis confirmed)
- `regime_terminal/data/active_signals.json` has SPY/QQQ/NVDA entries with leverage field; values 0.75 / 1.5 / -2.0 / -1.5 / -0.5 / 0.5 present
- `hmmlearn` in `regime_terminal/requirements.txt:1`, `alpha_engine/requirements.txt:25`, `.github/workflows/regime-terminal.yml:35`
- **Wire-Up confirmed**: consumed by `audit_trail/universal_pick_resolver.py:103`, `audit_trail/dashboard_generator.py:3634`, `alpha_engine/isolated_signal_integrator.py:84,350`, `alpha_engine/smart_picks_engine.py:385,407`

**Caveat:** `dashboard_generator.py:3632` notes regime_terminal is a **classifier**, not a pick generator (no TP/SL/entry). Hermes's framing as "priority #1 for /audit integration" overstates — it's already integrated as a signal feed. Any further work is incremental UI surface, not greenfield wire-up. **Reject any PR claiming it needs to be integrated from scratch.**

### Battleground 8/8 anti-overfit framework
**Hermes claim:** "8/8 anti-overfit checks passed" on 10 survivor strategies.

**Verdict:** **Framework CONFIRMED** in `alpha_engine/survivor_backtest.py:2110-2122` (8 named checks: `min_trades_30`, `win_rate_gt_50`, `p_value_lt_05`, `profit_factor_gt_1_2`, `oos_profitable`, `multi_asset_3plus`, `regime_2plus`, `consistent_halves`). Live JSON `alpha_engine/data/survivor_backtest_results.json` regenerated 2026-05-04.

### `bt_backtest_trades` archive plan
**Hermes claim:** 282K-row table dominates `ejaguiar1_stocks` (14 GB).

**Verdict:** **Direction confirmed; numbers off.** Live MySQL probe: **1,271,867 rows / 1.4 GB data + 125 MB indexes** (4.5× Hermes's estimate). Archive plan PR #794 merged with `BACKTESTS_DB_NAME` env split.

### DNA Engine permutation counts
**Hermes claim:** 4,939 permutations / 1,489 active combos.

**Verdict:** **Counts CONFIRMED** in `battleground/data/combo_metrics.json:3-4`. **BUT:** top winner in same file shows `sharpe: 145732.416` on `total_trades: 5` — textbook overfit. `genome/HONEST_ASSESSMENT.md` openly admits winners-only seeding inflates WR to 100%. **Wire-Up Rule violation** for `combo_metrics` — zero references in production scoring path. Genome pick-files ARE wired via `dashboard_generator.py:3583-3590` but the combo metrics specifically are sidecar. **Do not promote any "DNA-engine alpha" until winners-only seeding is fixed.**

---

## ❌ REFUTED — fabricated or stale

### Battleground 10-survivor specific metrics
**Hermes claim:** Connors R3 71.4% WR / Sharpe 1.53 / n=803 · Keltner MR 67.6% / Sharpe 2.06 / n=111 · Connors RSI-2 68.4% / Sharpe 1.17 / n=895.

**Verdict:** **REFUTED.** Those are stale **2026-02-28 hardcoded values** in `battleground/app.js`. Live JSON (`alpha_engine/data/survivor_backtest_results.json`, regen 2026-05-04) shows: n=756 / WR=71.6% / Sharpe=1.5 · n=102 / WR=67.6% / Sharpe=1.98 · n=855 / WR=68.2% / Sharpe=1.04. **All three n-values, plus 2/3 Sharpes, are wrong.** Any "Classic Strategies" /audit tab must source from live JSON, not Hermes's app.js scrape.

### "Pages that don't exist in the repo"
**Hermes claim:** `/findcryptopairs/meme.html` (7.8% WR / 476 signals / -0.41% avg PnL / TST/USDT showing $0.0000000000), `/findstocks/portfolio2/algo-study.html` (404), `/live-monitor/multi-dimensional.html` (Fear & Greed / Sector Rotation signals).

**Verdict:** **None exist in the repo.** `Glob **/meme.html` → 0 hits; `**/algo-study.html` → 0 hits; `**/multi-dimensional.html` → 0 hits. If these exist on the prod FTP, they're static HTML with no Python signal generator behind them. The "Fear & Greed / Sector Rotation" multi-dim signals **are not computed Python-side anywhere** in `alpha_engine/`, `audit_trail/`, `audit_dashboard/` — cannot wire into `dashboard_generator.py` until somebody builds the signal generators. Aspirational pages, not existing ones.

### Per-asset-class swarm Sharpe values from `MASTER_HEALTH_REPORT.md`
**Hermes claim:** COMMODITY OOS Sharpe -2.343, FOREX -1.895, plus per-asset "health scores" (COMMODITY 28/100, FOREX 32/100).

**Verdict:**
- **Sharpe -2.343 / -1.895** appear in `dashboard_data.json::walk_forward_by_class` and trace to `walkforward_validator.py`. Numbers reproduce, BUT `test_size=10` fold windows have std up to 9.4 — Sharpe estimator collapses; the mean is **not informative**. Per-class fold sizing reformed in PR #793.
- **28/100 / 32/100 health scores:** **No formula or generator exists.** Pure LLM narrative output, no computational backing. PnL projections (+$120k/month, +$85k/month, +$245k total) in `COMPILED_*_PLAN.json` similarly unsourced.

### 5 PROOF docs from prior Hermes (RR-GATE, STRATEGY-BANS, SCORE-REBALANCE, TIER2-SCALE, chatgpt_combined)
**Hermes claim:** 5 PR proposals with specific WR/PF/n numbers and dollar PnL projections.

**Verdict:**
| # | Claim | Verdict |
|---|---|---|
| 1 | RR-GATE: PF 5.81 in 1.5–2.0 R:R band | ❌ Actual PF 0.39 in same band per `closed_picks.json` |
| 2 | STRATEGY-BANS: `unknown` 18% WR n=many, `gainer_compression_relaxed_mut` 8% WR | ❌ Both have 0 rows in `closed_picks.json`. `cta_commodity_momentum_term` (PF 0.02 claim) already in `strategy_blocklist.py` since 2026-05-03 |
| 3 | SCORE-REBALANCE: forward_wr weight=25 → boost to 55 | ❌ Actual weight is **40** in `elite_scorer.py`, not 25 |
| 4 | HTML-FIX: visible HTML comment leak on US Equity tab | ✅ Real bug, fixed in PR #787 |
| 5 | TIER2-SCALE: signal_validation 184 trades 63% WR, mega_mutation MDD 36%, claude_gainer | ❌ All 3 strategies have 0 rows in `closed_picks.json` |

### chatgpt_combined PROVEN-tier promotion
**Hermes claim:** WR 75-83%, PF ~2.5, trade count >50.

**Verdict:** **REFUTED.** `alpha_engine/data/closed_picks.json` has **0 rows** with `strategy` or `source_system` matching "chatgpt". The strategy file `battleground/data/chatgpt_combined_signals.json` is a scanner config (symbols_scanned=13, active_signals/picks lists) — **not** a closed-trade history. No PnL data to derive WR/PF/Sharpe from. `trust_registry.json` doesn't exist at the proposed path or anywhere in the repo.

### Hermes's mc_winners factor analysis
**Hermes claim:** 257 signals analyzed, 3.9% baseline WR, factor-importance table with `parabolic_momentum: -2.2 (STRONGEST LOSER PREDICTOR)`, etc.

**Verdict:** **Sample biased.** Live MySQL probe: `mc_winners` has **476 rows** (Hermes saw only 257 — 54% of the population). 86% of those had broken resolution tracking; only 10 wins total. Factor analysis on 10/257 sample with selection bias is **not actionable as strategy guidance**. Resolution tracker logic itself is sound and worth rebuilding cleanly with env-var creds + an OHLCV backfill that resolves all 476 rows before any strategy claim.

---

## ⚠️ UNVERIFIED — pending external evidence

### CHATWITHCLAUDE*.md "live performance" tables
Tables in earlier `CHATWITHCLAUDE.MD` versions cited per-strategy "WR drop vs baseline" numbers (e.g., `futures_momentum 11% vs 45% baseline`). The "baseline" calculation is undefined and doesn't reproduce from `closed_picks.json` or the leaderboard JSONs in repo. **Treat as time-stamped narrative.**

### "Live signals" pasted as text in Hermes notes
Polymarket probabilities (Bitcoin $200K 4.2%, Fed cut 0%, China/Taiwan 51.5%) and 12-ticker regime_terminal signal roster — both pasted as markdown text in Hermes notes. Polymarket numbers had no JSON snapshot committed and Hermes admitted in same session "external arXiv/Polymarket queries were blocked by tool restrictions." Regime ticker roster wasn't enumerated against the actual `active_signals.json` count. **Both treated as time-stamped narrative until reproduced from live source.**

### Archive recommendations beyond `bt_backtest_trades`
Hermes recommended retiring `ejaguiar1_events`, archiving `mc_winners` (memecoin → stocks), fixing sportsbet arena (187 stuck bets). Direction is reasonable but specific row counts / "DB health scores" (5/100, 20/100, 35/100, 70/100) have no formula behind them. Treat as topic flags, not engineering metrics.

---

## Operating principle going forward

When a Hermes note arrives with specific numbers:
1. **Grep the source JSON / DB first.** Don't ship anything against numbers Hermes scraped from HTML.
2. **Wire-Up Rule.** Ask: is the proposed source actually consumed by `audit_trail/quality_gates.py`, `audit_trail/dashboard_generator.py`, `alpha_engine/production_scanner.py`, `alpha_engine/smart_picks_engine.py`? If "no", it's a sidecar, label it accordingly.
3. **Charter floors.** Anything claimed at n<100 with no Monte Carlo or out-of-sample is a research highlight, not a deploy candidate.
4. **Dollar-PnL projections** with no derivation are LLM narrative. Strip from PR bodies unless cited to a specific simulation script.

Past the 5-PROOF / mc_winners / Battleground-app.js episodes this session, the empirical hit rate on Hermes's specific numeric claims sits near 1/5. Verify before merging.
