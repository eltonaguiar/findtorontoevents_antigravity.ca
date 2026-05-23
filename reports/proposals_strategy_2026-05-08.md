# Strategy Improvement Proposals — 2026-05-08

**Author:** Claude Opus 4.7 (1M ctx) peer
**Goal:** lift `findtorontoevents.ca/audit` per-asset-class performance toward Tier-2 (PF >= 1.5, WR >= 50%, MDD < 20%) — Goal #1 from `CLAUDE.md`.
**Mode:** read-only proposal. No code changes. Ranked-by-ROI summary at the bottom.

---

## Current state (verified 2026-05-08, live `audit_dashboard/data/dashboard_data.json::performance.asset_class_health`)

| Class    | n     | WR%  | PF   | Total PnL% | Live status         | Tier verdict                          |
|----------|-------|------|------|------------|---------------------|---------------------------------------|
| EQUITY   | 439   | 53.8 | 1.58 | +388.83    | stable              | **T2 met** (PF>=1.5, WR>=50)          |
| COMMODITY| 372   | 67.2 | 4.07 | +600.23    | stable              | **T1 territory** (lift n further)     |
| CRYPTO   | 7,920 | 47.9 | 1.39 | +3,229.08  | stable              | sub-T2 (drag from `alpha_engine_fast`/`kimi_signal_tracking`) |
| ETF      | 98    | 59.2 | 1.44 | +43.38     | candidate           | borderline (n>=100 unlocks sizing)    |
| FOREX    | 653   | 45.9 | 0.25 | -1,027.18  | stressed            | sub-floor (apply mutate-before-kill)  |
| BOND     | 11    | 54.5 | 0.66 | -1.53      | thin                | meets WR; PF and n both below floor   |
| MEMECOIN | n/a   | n/a  | n/a  | n/a        | not a tracked class | covered today only inside CRYPTO bucket |

> **Note on prompt vs live numbers:** the brief cited EQUITY 52.8/1.42 and COMMODITY 48.7/2.08; the live `asset_class_health` block at session start (2026-05-08T20:01Z) reads 53.8/1.58 and 67.2/4.07 respectively. Live numbers are more current and used for verdicts below. CRYPTO and FOREX directional reads agree with the brief.

---

## Per-class proposals

Each proposal: ONE strategy upgrade, effort, expected lift, risk, repo asset to leverage.

### 1. CRYPTO — sub-T2 (PF 1.39 / WR 47.9 / n 7,920)

**Proposal: Polymarket-confirmed CRYPTO LONG gate v2 + cohort-level kill of `alpha_engine_fast` and `kimi_signal_tracking`.**

The PF 1.39 system aggregate is being dragged down by two sub-PF-1.0 cohorts (per `project_strategy_state_2026_05_03.md`: `alpha_engine_fast` PF 0.62, `kimi_signal_tracking` PF 0.26). Removing those two from the CRYPTO LONG basket and *requiring* Polymarket volume-spike confirmation (which already exists per `polymarket_vol_filter.py` and the recent commit on main) for the remaining sources should lift the bucket toward PF 1.6-1.8 with WR > 50%.

- **Repo asset:** `alpha_engine/polymarket_vol_filter.py` (just hardened on 2026-05-07: `is_polymarket_volume_confirmed` now returns False when no spike); `BLOCKED_SOURCE_SYSTEMS` registry in `alpha_engine/strategy_blocklist.py`; `feed_hygiene` step 5b.
- **Effort:** ~80 LoC, 1-2 days. Add `alpha_engine_fast` and `kimi_signal_tracking` to a CRYPTO-LONG-only sub-blocklist. Extend Polymarket gate from "confidence-boost" to "block on no-spike for high-conviction tier".
- **Expected lift:** +10-15pp PF (1.39 -> ~1.6), +3-5pp WR (47.9 -> ~52). Evidence: `polymarket_vol_filter.py` test fixture shows 2.0-2.2x spike picks have historical WR > 55% in `alpha_engine/data/strategy_performance.json`.
- **Risk:** n drops sharply (Polymarket hard-block could cut CRYPTO LONG volume 40-60%). Mitigation — apply the gate ONLY to `alpha_engine_fast` + `kimi_signal_tracking` recovery cohorts plus tier=HIGH_CONVICTION elsewhere.
- **Failure mode:** if Polymarket markets don't exist for a symbol the gate must default-allow (already the case per the 2026-05-07 fix); if it default-blocks we starve the bucket.

### 2. EQUITY — T2 met (PF 1.58 / WR 53.8 / n 439)

**Proposal: Wire STOCKSUNIFY2 CAN SLIM + Replicator into production via `data/daily-stocks.json` bridge — push toward T1 (PF>2 / WR>55).**

EQUITY is already T2 thanks to `chatgpt_combined`, `skyrocket_detector`, and `earnings_drift`. The marginal upgrade is *not* another strategy; it's enrolling the dormant STOCKSUNIFY2 sibling repo (CAN SLIM growth + 24h Skyrocket + Replicator) which is ready-to-wire. CAN SLIM historically tracks 35-40%/yr in published O'Neil journals — high WR/high-PF complement to our existing momentum picks.

- **Repo asset:** `STOCKSUNIFY/` directory at repo root; `tools/run_ueps_pickers.py` cron pattern is the template; `alpha_engine/strategies/skyrocket_detector.py` already exists for momentum overlap dedupe.
- **Effort:** ~120 LoC + cron entry, 2-3 days. New emitter `alpha_engine/stocksunify_emitter.py` reading from `STOCKSUNIFY/data/daily-stocks.json`; production-scanner caller registration; per-Wire-Up Rule, must include caller in `score_pick`/`smart_picks_engine`.
- **Expected lift:** EQUITY PF 1.58 -> ~1.9, WR 53.8 -> ~57. Evidence: O'Neil's CAN SLIM published median 18-month WR ~52-58%, PF >= 2 in clean periods (`HEDGE_FUND_STRATEGIES_RESEARCH.md`).
- **Risk:** STOCKSUNIFY2 picks may overlap with `skyrocket_detector` and `chatgpt_combined`; risk of correlated drawdowns. Mitigation — dedupe on (symbol, side, day) with confidence-tiebreak.
- **Failure mode:** sibling-repo data freshness — if `daily-stocks.json` goes stale we need a freshness gate (>24h = skip).

### 3. ETF — candidate (PF 1.44 / WR 59.2 / n 98) — almost-stable, n=98 vs floor 100

**Proposal: Lift n above 100 by adding the missing two ETF capital-reallocation 3.0x overrides as opt-in tier-2 picks, then promote.**

ETF is two trades short of "stable" status. The recent 3.0x override commit (`311754fdcb9`) widened ETF capital but didn't add new strategies. The PF/WR are healthy (1.44 / 59.2) — we just need volume.

- **Repo asset:** `alpha_engine/etf_strategies.py`, `alpha_engine/etf_decay_shorts.py`, `alpha_engine/etf_rebalancer.py`, `alpha_engine/etf_scanner.py`. Already wired.
- **Effort:** ~30 LoC + config tweak, half-day. Lower per-day ETF emission cap from current setting; add ETF earnings-week momentum pick (mirroring `earnings_drift.py` structure).
- **Expected lift:** unblocks `sizing_allowed=true` (currently false because `sample_tier=candidate`). PF/WR stay roughly constant; this is purely a sample-size unlock.
- **Risk:** chasing volume can dilute PF if the new picks come from low-quality scanners. Mitigation — gate by existing per-pick `net_edge_bps` ranker.
- **Failure mode:** ETF universe is narrow; risk of correlated DD if all picks are SPY/QQQ flavored. Already partly mitigated by `etf_decay_shorts` adding inverse ETF exposure.

### 4. COMMODITY — T1-territory (PF 4.07 / WR 67.2 / n 372)

**Proposal: Don't touch the model — scale capital allocation 2x and add per-symbol concentration cap.**

COMMODITY is the standout performer. PF 4.07 and WR 67.2 over 372 closed trades is *Renaissance-tier*. The single-line action is "give it more dollars" — but with a per-symbol concentration cap because `commodity_kill_switch.py` shows we historically had inverse-momentum failure modes. The recent commit `682bee875e3` correctly fixed where the kill-switch fires; that audit should now be on for safety.

- **Repo asset:** `alpha_engine/commodity_signal_generator.py`, `alpha_engine/commodity_kill_switch.py` (kill point now correct per 2026-05-07 fix).
- **Effort:** ~20 LoC config + position-sizer tweak, half-day. Bump COMMODITY sizing multiplier from default to 2.0x in capital-reallocation config; add `MAX_COMMODITY_PER_SYMBOL_PCT = 0.15` cap.
- **Expected lift:** Total PnL% scales linearly with allocation if PF holds. PF/WR unchanged — this is the "let winners run" move, not a model upgrade. WR may hold at 67% only at current sample size; expect mean-reversion to ~58-62 at 2x volume.
- **Risk:** fattest-tail risk in the system. Single `commodity_inverse_momentum` failure mode could blow up at 2x sizing; that's why per-symbol cap is mandatory.
- **Failure mode:** if PF 4.07 reflects sample-size luck not edge, 2x-sized DD scales 2x. Mitigation — staged rollout (1.5x for 30 days, then 2.0x).

### 5. FOREX — sub-floor (PF 0.25 / WR 45.9 / n 653, status=`stressed`, sizing_allowed=false)

**Proposal: Mutate-before-kill protocol — replace existing FOREX strategies with carry-and-trend (G10 only), keep the recent 13-21 UTC session gate.**

FOREX is the sub-floor class. The 2026-05-07 commit added a 13-21 UTC FOREX session gate; that's the right direction. Per CLAUDE.md, do NOT silently kill FOREX — apply `MUTATION_THREE_AXIS_PROTOCOL.md`. The existing assets (`forex_carry.py`, `forex_carry_ppp.py`, `tsmom.py`) are textbook hedge-fund FX strategies that haven't been wired into production.

- **Repo asset:** `alpha_engine/strategies/new_strategies/forex_carry.py`, `alpha_engine/strategies/new_strategies/tsmom.py`, `alpha_engine/forex_carry_ppp.py`, `alpha_engine/forex_walk_forward_builtins.py`, plus the just-shipped 13-21 UTC session gate.
- **Effort:** ~250 LoC + deep-dive doc, 4-6 days. Step 1 — produce `reports/deep_dive_forex_*.md` with per-source autopsy (mandatory per CLAUDE.md). Step 2 — wire carry+TSMOM into production-scanner. Step 3 — restrict to G10 majors (EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF, NZDUSD).
- **Expected lift:** PF 0.25 -> ~0.9-1.1 (path to T2 over 90d). Evidence — DBMF/KMLM external benchmarks PF ~1.3-1.5; MyFXBook G10-carry trackers PF 1.1-1.4.
- **Risk:** mutate-without-kill = continued bleed during the 90d trial. Mitigation — cut sizing to 0.25x while running mutation in parallel-paper.
- **Failure mode:** if carry+TSMOM also fail post-2025 USD-cycle (USD weakness regime), we exhaust mutation axes. Then and only then apply kill per protocol.

### 6. BOND — thin sample (PF 0.66 / WR 54.5 / n 11)

**Proposal: Wire `bond_scanner.py` and `bond_data_fred.py` into production scanner with conservative emission cap; target n=100 over 60 days.**

BOND has acceptable WR (54.5) but sub-1.0 PF over only 11 trades — pure noise. The class has the assets (`bond_pricer.py`, `bond_scanner.py`, `bond_strategies.py`, `bond_data_fred.py`) but isn't generating volume. Per Wire-Up Rule, opt-in is fine here as long as a wiring plan exists.

- **Repo asset:** `alpha_engine/bond_pricer.py`, `alpha_engine/bond_scanner.py`, `alpha_engine/bond_data_fred.py`, `alpha_engine/bond_strategies.py`. FRED API key likely already in env.
- **Effort:** ~150 LoC + cron + Wiring Plan doc, 3-4 days. Add bond emitter to production scanner; target 1-2 BOND picks per day; FRED yield-curve regime filter as gate.
- **Expected lift:** n=11 -> 100 in ~60 days; PF 0.66 -> ~1.4 (yield-curve regime filtering is well-documented edge — PIMCO tactical bond benchmarks).
- **Risk:** bond drawdowns are slow; small sample makes early kill tempting. Mitigation — explicit "no kill before n=50" policy in Wiring Plan.
- **Failure mode:** FRED data latency (1-day lag) misses fast rate moves. Mitigation — augment with TLT/IEF intraday ETF prints as proxy.

### 7. MEMECOIN — not a tracked class today

**Proposal: Carve MEMECOIN out of CRYPTO bucket as a dedicated 3rd asset class with its own gate and sizing track.**

MEMECOIN trades inside CRYPTO today and likely *contributes disproportionately to the PF 1.39 drag*. We have `pump_guard.py`, `whale_concentration_index.py`, `whale_index.py`, `cross_chain_dex_arbitrage.py`, and `hyperliquid_traders.py` — all the infrastructure, none of the asset-class isolation. Splitting it lets us either (a) prove MEMECOIN edge separately or (b) cleanly kill it without affecting BTC/ETH stats.

- **Repo asset:** `alpha_engine/pump_guard.py`, `alpha_engine/whale_concentration_index.py`, `alpha_engine/hyperliquid_traders.py`, `outcome_resolver.py` `PNL_WIN_THRESHOLD_BY_CLASS` (just add MEMECOIN entry).
- **Effort:** ~200 LoC + dashboard tile, 4-5 days. New asset_class enum; classifier in `alpha_engine/asset_class.py` (DOGE/SHIB/PEPE/BONK/WIF/etc.); separate `asset_class_health` aggregation; dashboard tile.
- **Expected lift:** depends on hidden truth. Likely MEMECOIN is sub-1.0 PF (drag reason); isolating it lifts CRYPTO base PF by 5-15% and gives MEMECOIN its own kill/mutate path.
- **Risk:** the data isn't there to know what we'll find. Could discover MEMECOIN is the *positive* contributor and the rest of CRYPTO is worse than thought.
- **Failure mode:** classifier mis-tags (e.g., SOL is borderline). Mitigation — hand-curated whitelist initially, ML later.

---

## Cross-cutting initiatives

### A. Best single bet — STOCKSUNIFY2 wire-in (Proposal #2)

Best risk-adjusted ROI. EQUITY is already at Tier-2 so the upgrade has the lowest "make-it-worse" risk. The data file (`STOCKSUNIFY/data/daily-stocks.json`) and emitter pattern (`tools/run_ueps_pickers.py`) are both ready-to-clone. CAN SLIM has 60+ years of public evidence; Replicator adds copy-trader-style diversification. We pay 2-3 days of dev, get a credible jump from PF 1.58 -> ~1.9 with WR holding above 55%.

Why not COMMODITY scale-up? Because the risk envelope is asymmetric — a botched 2x sizing on commodities can blow up the whole audit dashboard reputation. STOCKSUNIFY2 wire-in fails gracefully (just doesn't emit picks).

### B. Diversification gap — BOND

BOND (n=11) is by far the most under-served asset class vs market opportunity. The fixed-income market is multiples larger than equities by AUM, and we have all the code (`bond_*.py`) sitting unwired. Hedge funds get half their alpha from rates/bonds — we've punted entirely. Wiring `bond_scanner.py` is plumbing, not innovation, and gets us into a previously-zero exposure.

ETF is a close second (n=98, two trades from stable). MEMECOIN (untracked) is a *visibility* gap, not a diversification gap — we have exposure, just not labeled.

### C. Quick scale-up — COMMODITY at 2.0x sizing (Proposal #4)

This is where the throttled pipeline already proven works. PF 4.07 over n=372 is the highest-conviction edge in the system, and the kill-switch was just hardened on 2026-05-07. The capital reallocation infra (commit `311754fdcb9`) gives us 3.0x overrides; we need a 2.0x override on COMMODITY plus a per-symbol cap. This is half a day of work for what could be a step-change in total PnL — *not* PF, just Total PnL% via larger sizing.

If we want to be aggressive, do this in addition to Proposal #1 (CRYPTO drag-cohort kill) — they're orthogonal.

---

## Top-5 ranked by ROI (ROI = expected lift per day-of-effort, weighted by Tier-1/2 progress probability)

| Rank | Proposal | Class    | Effort | Expected lift                          | Why it ranks here |
|------|----------|----------|--------|----------------------------------------|-------------------|
| **1** | COMMODITY 2.0x sizing + per-symbol cap     | COMMODITY | 0.5d   | Total PnL +80-100%, PF holds 3.0+      | Half-day, proven edge, highest dollar ROI |
| **2** | STOCKSUNIFY2 CAN SLIM + Replicator wire-in | EQUITY    | 2-3d   | PF 1.58 -> ~1.9, WR -> ~57             | Lowest risk T2->T1 jump; ready-to-wire |
| **3** | CRYPTO drag-cohort kill + Polymarket gate v2| CRYPTO    | 1-2d   | PF 1.39 -> ~1.6, WR +3-5pp             | Largest n class; biggest absolute PnL upside |
| **4** | ETF emission-cap raise + earnings-week pick | ETF       | 0.5d   | n 98 -> 150, sizing unlock              | Half-day to unlock `sizing_allowed=true` |
| **5** | FOREX carry+TSMOM mutate-before-kill        | FOREX     | 4-6d   | PF 0.25 -> ~1.0 over 90d                | Highest sub-T2 lift potential, but slow + risky |

Below the cut: BOND wiring (#6 — 60d to n=100, slow), MEMECOIN class-split (#7 — high research value, low immediate PnL).

**Recommendation:** ship #1 + #4 this week (1 day total), #2 + #3 in parallel next week (3-4 days, two engineers). Defer #5 until #1-4 are verified live for 7d.

---

*Generated 2026-05-08. Read-only proposal — no code modified. References: `audit_dashboard/data/dashboard_data.json::performance.asset_class_health`, `CLAUDE.md` Goal #1 banner, `docs/MUTATION_THREE_AXIS_PROTOCOL.md`, `project_strategy_state_2026_05_03.md`, recent commits 311754fdcb9 / 989d60358b7 / 682bee875e3.*
