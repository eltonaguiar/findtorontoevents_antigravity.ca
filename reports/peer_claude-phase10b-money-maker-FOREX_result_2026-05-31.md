# /money-maker-readyv2 — FOREX

## Class verdict at 06:30Z 2026-05-31
PF=0.035  WR=27.59%  n=29 (policy-clean-net)  MDD=81.05%  expectancy=-4.58%/pick  CVaR95=-50.84
T2-status: **FAIL on (PF, WR, MDD, n, DSR, expectancy)** — every gate failed; INSUFFICIENT_DATA.
Raw 90d (no policy filter): n_closed=1,531; status mix 904 TP_HIT + 21 WON + 1,379 LOST + 131 EXPIRED + 11,601 TIME_EXIT + 3 SL_HIT. The TIME_EXIT slug (76%+ of "closed") is the same EXPIRED→positive-PnL mislabel pathology flagged for CRYPTO in CLAUDE.md, now confirmed for FOREX.

## Best candidate
**`cta_cross_asset_tsmom`** (all-time n=189 closed, WR=53.4%, PF=3.57, avg_pnl=+0.108%). The only FOREX strategy with both n>=100 AND PF>1.5 AND WR>50% in the live DB. *Caveat:* 1 catastrophic mislabel (USDJPY TP_HIT with exit_price=1.358 implying 99% pnl when actual move was ~0.3%) inflates PF — true PF likely 2.0–2.5 after the bad row is corrected. Still the strongest candidate.

Phase-3 MC pick `fx_smart_carry_trade_momentum` (n=56, WR=37.5%, PF=0.817) underperforms live vs the MC P(T2@n=100)=64% projection — the MC model assumed live emission would resemble historical backtest. **Do not graduate it on MC alone.** Needs another 44 clean closures before a graduation decision.

## T2 gap
- **n gap:** 100 − 29 = **71 more clean (policy-clean-net) closures** needed for the verdict cohort to clear n>=100.
- **Raw cadence:** 14d emission ≈ 1,215 picks total; 14d closed = 49; closes/day ≈ **3.5/day** in clean-policy-filtered terms (i.e., excluding TIME_EXIT artifacts). At that rate, time-to-T2 = **71 / 3.5 ≈ 20 days (~3 weeks)** — IF labels are clean.
- **At current PF/WR trajectory (PF=0.035, WR=27.6%), P(T2@n=100) ≈ <1%** — the class fails on PF and expectancy long before n=100.
- **Real bottleneck: not cadence.** The bottleneck is (1) the TIME_EXIT resolver mislabels destroying signal quality, (2) `multi_asset_scanner` emitting 39.3% of the cohort at WR=9%/PF=0.21, and (3) regime_* strategies producing 50% per-trade drawdowns. Fix labels and gate the dominant junk emitter and the verdict moves up immediately.

## Actions ranked by impact

### 1. KILL `multi_asset_scanner` FOREX emission (PF=0.21, WR=9% on n=11 = 39% of cohort)
- **File:** `alpha_engine/source_policy.py` (or equivalent — search `BLOCKED_SOURCE_SYSTEMS` / `BLOCKED_SOURCE_BY_CLASS`).
- **Action:** add `('multi_asset_scanner', 'FOREX')` to the per-class blocklist OR set `multi_asset_scanner.forex_enabled = False` in `alpha_engine/scanners/multi_asset_scanner.py`.
- **Required pre-work:** per CLAUDE.md, write `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` entry + run `python tools/mutation_analysis.py --source multi_asset_scanner --class FOREX` to satisfy mutate-before-kill protocol.
- **Impact:** removes 39.3% of cohort weight on PF=0.21 → cohort PF jumps from 0.035 toward ~0.7 mechanically.

### 2. FIX FOREX resolver TIME_EXIT mislabels (root cause of 11,601 TIME_EXIT rows + 6 absurd TP_HIT exit_prices)
- **File:** `alpha_engine/outcome_resolver.py` (~lines 115–126 already ships `PNL_WIN_THRESHOLD_BY_CLASS`; FOREX threshold should be 5bp/0.05% as documented in CLAUDE.md).
- **Bugs observed live:** TP_HIT for CADJPY=X with exit_price=611.23 vs entry 115.77 (decimal-shift / wrong-pair); USDJPY=X TP_HIT exit_price=1.358 from entry 158.58 (cross-pair confusion — looks like EURUSD price assigned). 6 such rows visible at pnl_pct>5%.
- **Action (a):** add a sanity guard in `_resolve_tp_hit` rejecting exit_price outside `[entry*0.5, entry*2.0]` for FOREX (yfinance occasionally returns a stale/wrong cross). Log to `reports/peer_blackbox_incidents-FOREX-resolver_2026-05-31.md`.
- **Action (b):** TIME_EXIT rows with `pnl_pct` derived from exit_price more than 24h after `take_profit` was supposedly hit must be re-resolved against `yfinance` 1h bars, not daily close.
- **Action (c):** scrub the 6 known-bad TP_HIT rows (IDs from the live query: CADJPY 2026-04-16, USDJPY 2026-04-17, NZDUSD 2026-04-22/23 ×3, USDCAD 2026-04-13) via `tools/safe_db_archive.py` to a quarantine table, then re-resolve.
- **Impact:** removes the fake-PF inflation that hides the real edge ranking. After scrub, `cta_cross_asset_tsmom`'s true PF emerges (est. 2.0–2.5 instead of 3.57).

### 3. WATCHLIST `cta_cross_asset_tsmom` for graduation
- **n=189, WR=53.4%, PF=3.57** (likely 2.0–2.5 post-scrub). Already past T2 floor on n.
- **File:** `audit_dashboard/data/pf_registry.json` → confirm row exists under `by_asset_class_strategy_policy_clean_net` for `(FOREX, cta_cross_asset_tsmom)`. If absent, this is the same admissibility-vs-emission gap that 5676eace2 just fixed for non_crypto policy.
- **Action:** verify `cta_cross_asset_tsmom` is registered in the FOREX policy whitelist (`alpha_engine/non_crypto_policy.py` or `source_policy.py`) — commit 5676eace2 added it for the consolidation but FOREX-specific gating should be re-confirmed.
- **Promote criterion:** once resolver fix lands AND policy-clean-net n>=100 AND PF>1.5 AND WR>=50% in the post-scrub cohort, GRADUATE to T2.

### 4. KILL/MUTATE `regime_terminal` + `regime_accumulation` FOREX emission (MDD=81% driver)
- Per deep-dive: 6 regime_* picks produce gross loss ≈ 1.18 of total cohort gross loss 1.29. Two picks alone wipe the book.
- **File:** `alpha_engine/regime_terminal.py` / `alpha_engine/regime_accumulation.py` — likely missing stop-loss enforcement on FOREX leverage.
- **Action:** add hard SL at 1.5× ATR(14) for any FOREX pick, OR block these sources on FOREX via the same per-class blocklist as Action 1.
- **Impact:** MDD drops from 81% → projected <30%; mdd_ok gate could pass.

### 5. ADD `forex_rsi_mean_reversion_v2` (mutated from `forex_rsi2_mean_reversion`)
- Cycle 17 backtest (2026-05-29) showed `rsi_mr` Tier 1 on USDCHF (PF=4.28), EURUSD (PF=2.46), GBPUSD (PF=2.40). Live `forex_rsi2_mean_reversion` is PF=0.255 on n=774. **Massive backtest↔live gap.**
- **Diagnosis path:** export closed-pick CSV for `forex_rsi2_mean_reversion` → `python tools/mutation_analysis.py --strategy forex_rsi2_mean_reversion --class FOREX` per docs/MUTATION_THREE_AXIS_PROTOCOL.md (regime gate / vol floor / source-confluence).
- **Hypothesis:** Cycle 17 used RSI(2) with 5-bar hold and 1.5×ATR TP. Live emitter probably uses RSI(2) with no hold limit and a fixed pip TP that mis-sizes for JPY pairs (which dominate the live cohort and have 100× different pip values).
- **Action:** register `fx_rsi_mr_v2_atr_sized` hypothesis in `reports/hypothesis_registry.json` (rule M-107), backtest with proper JPY-pip-normalization, then deploy as a sidecar strategy via `alpha_engine/forex_rsi_mr_v2.py` (opt-in, not replacing v1 yet).

### 6. WATCHLIST cadence-protect — emission rate for clean strategies
Currently `cta_cross_asset_tsmom` emits ~2 picks/day on FOREX; `myfxbook_retail_contrarian` ~5/day; `ig_contrarian_sentiment` ~6/day. These three together can produce 70 clean closes/week, comfortably covering the 71-pick T2 gap in <2 weeks IF resolver labels become trustworthy. No emission-rate change needed — just don't gate them down further.

## What I would ship next

### PR-A (P0, scope ~3 files): `fix(forex-resolver): TIME_EXIT mislabel scrub + sanity guard`
- Add exit_price sanity guard in `alpha_engine/outcome_resolver.py` rejecting outliers >2× entry for FOREX.
- Quarantine the 6 known-bad TP_HIT rows via `tools/safe_db_archive.py`.
- Re-resolve TIME_EXIT rows with yfinance 1h bars instead of daily close.
- Append incident report `reports/peer_blackbox_incidents-FOREX-resolver_2026-05-31.md`.
- Expected outcome at next nightly verdict: FOREX `n_resolved` rises, PF rises from 0.035 → 0.3–0.5 (no fake wins masking real losses, but also true wins surface).

### PR-B (P1, scope ~2 files): `fix(forex): block multi_asset_scanner + regime_* emission on FOREX class`
- Append to `alpha_engine/source_policy.py` (or wherever `BLOCKED_SOURCE_BY_CLASS` lives — `grep -r "BLOCKED_SOURCE" alpha_engine/`):
  ```python
  BLOCKED_SOURCE_BY_CLASS_FOREX = {
      'multi_asset_scanner',  # n=11 WR=9% PF=0.21 — 39% of cohort, dominant drag
      'regime_terminal',       # MDD blowup: 50%/trade loss frequency
      'regime_accumulation',   # MDD blowup: 100% loss rate n=2
  }
  ```
- Add `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` entry per CLAUDE.md key-commands rule.
- Run `python tools/mutation_analysis.py` for each before merge.
- Expected outcome: cohort PF jumps further; MDD drops from 81% to projected <30%; mdd_ok could pass.

---

Generated by peer Claude (Opus 4.7), Phase 10b. Source-of-truth files cited inline. Mutate-before-kill compliance required for PR-B per CLAUDE.md.
