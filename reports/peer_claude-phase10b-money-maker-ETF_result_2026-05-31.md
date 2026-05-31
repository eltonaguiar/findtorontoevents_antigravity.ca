# /money-maker-readyv2 — ETF

**Generated:** 2026-05-31 06:30Z
**Author:** peer_claude (Opus 4.7 subagent)
**Source:** live `ejaguiar1_stocks.trading_picks` + `audit_dashboard/data/pf_registry.json`

## Class verdict at 06:30Z 2026-05-31

```
PF=0.48  WR=50.0%  n=4  Sharpe~n/a  T2-status: FAIL on (n<<100; INSUFFICIENT_DATA)
```

Two parallel reads — both fail T2:

| View | n | WR | PF | avg_pnl | Source |
|---|---|---|---|---|---|
| pf_registry policy-clean-net | 4 | 50.0% | 0.48 | -0.008 | `pf_registry.json` `by_asset_class_policy_clean_net.ETF` |
| Live DB, status IN ('WON','LOST') | 18 | 5.6% | 0.004 | -2.39% | `trading_picks LOWER(category)='etf'` |
| Live DB, ALL pnl_pct NOT NULL | 22 | 36.4% | 0.98 | -0.004 | same, treats TP_HIT/EXPIRED with non-zero pnl as closed |

Status mix in DB (320 total ETF picks):
- 159 OPEN (zero pnl_pct, never resolved) — leveraged_etf_decay shorts + new etf_all_strategies emissions
- 134 TIME_EXIT (pnl_pct = 0.00000000 forced — **suspicious; matches Phase 4 resolver-zero-pnl bug**)
- 17 LOST, 5 TP_HIT, 2 EXPIRED, 2 ACTIVE, 1 WON
- **3 LOST rows have pnl_pct=NULL** (Phase 4 NULL-pnl bug applies to ETF too)

## Best candidate

`etf_rsi2_pullback` (Connors RSI-2) — pf_registry shows `n=1 WR=100% PF=undefined(no_losses)` for the `file:alpha_engine` source variant; live DB shows the same strategy across THREE source_system tags producing wildly different outcomes:

| source_system | strategy | n | W | L | PF | last_seen |
|---|---|---|---|---|---|---|
| etf_scanner | etf_rsi2_pullback | 1 | 1 | 0 | undef (avg +24.5%) | 2026-05-18 |
| etf_all_strategies | etf_rsi2_pullback | 33 | 0 | 1 | 0.0 (avg -0.06%) | 2026-05-20 |
| etf_scanner | etf_rsi2_pullback (LOST row) | 1 | 0 | 1 | 0 | 2026-05-27 |

The 33-row `etf_all_strategies` cohort has 0/0 W/L despite 33 closures — **every one has pnl_pct ≈ 0**, i.e. all closed at TIME_EXIT with no movement. This is either: (a) emitter generates ultra-tight TP/SL that never trigger, or (b) resolver is closing at entry price. Without a real candidate at n≥10 with a non-degenerate PF, ETF has **no MC-flagged real-edge candidate** — it was not in the Phase 3 list.

MC P(T2 at n=100) = N/A (no MC simulation in PR #179 for ETF).

## T2 gap

T2 minimum: n≥100, PF>1.5, WR>50, MDD<20.

- Clean closures at usable strategy: **0** (the 33-pick `etf_rsi2_pullback` cohort is all zero-pnl; cannot count).
- New closures needed: **100+** at one strategy with non-degenerate pnl distribution.
- Emission rate (last 30d): 288 picks → 9.6/day across the class. Concentrated 2026-05-18 → 2026-05-30; spike came from `leveraged_etf_decay` (39 picks) + `etf_all_strategies` family (~80 picks across 7 strategies) + new mimo/baby strategies.
- **Closure rate (last 30d): 4 closures** (2 on 2026-05-27, 2 on 2026-05-28). That is ~0.13 closures/day. **At this cadence, time-to-T2 = ~770 days (>2 years).** Bottleneck is NOT emission; it is the **resolver writing TIME_EXIT pnl_pct=0** for everything else.

Bottlenecks ranked:
1. **Resolver TIME_EXIT zero-pnl bug** (Phase 4 finding) — 134 rows stuck at TIME_EXIT with `pnl_pct=0.00000000`, meaning we have **134 unresolved-but-marked-closed ETF picks** sitting on the dashboard as no-edge data. If resolver re-runs intrabar-correct on these, we likely get 80-100 usable closures overnight.
2. **159 OPEN picks never reach TIME_EXIT** — leveraged_etf_decay (39 of these) sets TP/SL on multi-week horizons but the resolver loop appears not to age them. The `leveraged_etf_decay_picks.json` sidecar at `alpha_engine/outcome_resolver.py:2489` may be silently re-emitting without aging-out.
3. **Mis-tagging of ETF as EQUITY** — `multi_asset_scanner / vix_reversal` (n=3 in ETF) and `institutional_picks_engine / extreme_oversold_bounce` (n=5 LOST) are scanning SPY/QQQ-class tickers but tagging some as equity. Verified `pf_registry.json` EQUITY top sources include `multi_asset_scanner` — there is leakage both directions.

## Actions ranked by impact

### 1. [P0] Force-resolve the 134 TIME_EXIT zero-pnl ETF rows with intrabar replay

**Files:** `alpha_engine/outcome_resolver.py:1504-1512` (TIME_EXIT_AFTER_TP_1_5 + TIME_EXIT branches), `alpha_engine/outcome_resolver.py:1014-1019` (EXPIRED/TIME_EXIT/MAX_HOLD prefix labeling).

**Symptom:** 134 rows where `status='TIME_EXIT' AND pnl_pct=0.00000000 AND category='etf'`. Expected behavior — TIME_EXIT should still capture the close-vs-entry price spread (pnl ≠ 0 unless price literally unchanged).

**Fix:** Add a backfill pass `tools/backfill_etf_time_exit_pnl.py` that:
- selects rows where `category='etf' AND status IN ('TIME_EXIT','EXPIRED') AND pnl_pct=0`,
- re-fetches OHLC at `closed_at` from yfinance + Polygon fallback,
- computes pnl_pct = sign(direction) × (close - entry_price)/entry_price × 100,
- updates pnl_pct in-place, leaves status='TIME_EXIT'.

Expected uplift: 80-100 ETF rows graduate from "zero-pnl artifact" to "real closure".

### 2. [P0] Investigate why etf_all_strategies generates 33 zero-pnl `etf_rsi2_pullback` picks

**File:** `alpha_engine/etf_strategies.py` (RSI-2 logic), `alpha_engine/etf_scanner.py` (emitter wiring), `tools/etf_emitter_spike.py:90 (run())`.

**Symptom:** 33 picks, 0 wins, 0 losses by status, 1 LOST. Average pnl is -0.06% — essentially noise. The TP and SL bands are likely either: (a) set inside the bid-ask spread, or (b) set so wide that nothing triggers before TIME_EXIT.

**Action:** Add a diagnostic logger to `etf_strategies.py` that logs `(entry, tp, sl, tp_distance_bps, sl_distance_bps)` per emission. Verify against 14d ETF OHLC range — TP/SL should not be < 25 bps from entry for any ETF (median daily range SPY 50-80 bps; smaller sector ETFs 100-150 bps).

### 3. [P1] Add ETF to Phase 3 Monte-Carlo watchlist

**File:** `tools/mc_simulate_strategy_topup.py` (PR #179).

ETF has no MC candidate because no strategy has n≥10 closures with a non-degenerate pnl distribution. AFTER action #1 backfill lands, re-run MC for:
- `etf_all_strategies / etf_rsi2_pullback` (33→ usable)
- `etf_all_strategies / etf_faber_tactical` (15 → usable)
- `etf_all_strategies / etf_sector_momentum` (13 → usable)
- `leveraged_etf_decay / leveraged_etf_decay` (39 → usable if aged-out)

Likely best ETF candidate post-backfill: **etf_faber_tactical** (Faber 10-month SMA + 3m sector rotation has 14yr OOS PF~1.4-1.7 in academic backtests).

### 4. [P1] KILL: `institutional_picks_engine / extreme_oversold_bounce` for ETF

**Evidence:** n=5 LOST, WR=0%, avg pnl=-3.10%. Strategy targets penny-stock-style oversold reversals. ETF mean reversion (especially leveraged ETFs) has different mechanics. Strategy fires on QQQ/SPY/SQQQ but the entry rule doesn't account for sector ETFs that don't bounce.

**Action:** Add ETF to a denylist for this strategy. Search `alpha_engine/`:
```bash
grep -rn "extreme_oversold_bounce" alpha_engine/ | grep -iv test
```
Add `if category == 'etf': return None` at emission gate.

### 5. [P1] MUTATE: `etf_rsi2_pullback` per Three-Axis protocol

Per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (regime / vol-floor / source-confluence):
- **Regime gate:** require VIX<25 AND SPY > SPY-200-SMA (Faber filter). Connors RSI-2 OOS PF degrades in trending markets.
- **Vol floor:** ETF ATR(14)/price > 1.0% for sector ETFs, > 0.5% for SPY/QQQ. The 33 zero-pnl picks suggest emission during dead-quiet sessions.
- **Source confluence:** require 2-of-3 confirmation across RSI-2 < 5, BB%B < 0.05, and 5-day return < -3%.

**File:** `alpha_engine/etf_strategies.py` Connors RSI-2 function. Add the three gates above the emission return.

### 6. [P2] ADD: 200-day MA trend strategy for ETFs

This is Phase 9 candidate #6 directly. SPY/QQQ/IWM/TLT/GLD trend persistence is one of the strongest documented edges (Faber 2007, ~13% CAGR / 12% MaxDD 1973-2017). Wire as a new emitter:

**New file:** `alpha_engine/strategies/etf_200dma_trend.py`
**Emit when:** price crosses above 200-SMA from below, ATR-scaled stop 2× ATR-14, TP at +3× ATR-14.
**Wire-up rule (CLAUDE.md):** must be called from `production_scanner` or `etf_scanner` per the rule — do not ship as orphan.

### 7. [P2] Resolve `leveraged_etf_decay` aging

**File:** `alpha_engine/outcome_resolver.py:2489` references `ETF_LEVERAGED_DECAY_FILE = DATA_DIR / "leveraged_etf_decay_picks.json"`.

39 picks sitting OPEN with no closures suggests the sidecar isn't being aged into the main `trading_picks` flow. Check whether `active_picks_sync.py` reads `leveraged_etf_decay_picks.json` and whether the resolver's `_TIME_REASONS` set (line ~1931) includes it.

## What I would ship next (concrete PRs)

### PR A — `tools/backfill_etf_time_exit_pnl.py`
- Re-resolve 134 ETF TIME_EXIT rows with intrabar replay.
- Single-file tool, ~120 lines, mirrors existing `backfill_trust_score.py` shape (already modified in this branch).
- Acceptance: zero ETF rows where `status='TIME_EXIT' AND category='etf' AND pnl_pct=0` post-run.

### PR B — ETF emission gates (combined)
- In `alpha_engine/etf_strategies.py`: add VIX<25 + SPY-200-SMA gate to `etf_rsi2_pullback`, add ATR-vol floor.
- In `alpha_engine/etf_scanner.py`: add ETF denylist for `extreme_oversold_bounce`.
- Acceptance: emission rate drops 40-60%, but expected closure pnl distribution moves off zero-mean.

### PR C (next session) — 200-day MA trend strategy
- New `alpha_engine/strategies/etf_200dma_trend.py` + wire into `production_scanner`.
- Backtest 2010-2025 SPY/QQQ/IWM, target PF>1.6 / MDD<15.
- Ships with `## Wiring Plan` section per the wire-up rule.

## Risk factors

- **Resolver bug confirmed for ETF** — 134 zero-pnl TIME_EXIT rows. Phase 4 fix may have addressed CRYPTO but not ETF.
- **Mis-tagging risk:** `multi_asset_scanner` straddles equity / ETF. Picks on SPY/QQQ tagged 'etf' in pf_registry but might be tagged 'equity' in others. Recommend a one-time relabel pass.
- **No MC candidate** — until backfill PR A lands, ETF cannot enter the Phase 3 MC watchlist.
- **`pf_registry` ETF top_source='file:alpha_engine'** — `single_source_pct=0.5` is borderline; the concentration gate is not enforced before DSR/SPA (open P0 per CLAUDE.md), so even a successful MC pass would have a known caveat.

---
**One-line:** ETF FAIL+INSUFF-N (PF 0.48 / WR 50% / n=4 policy-clean; 134 TIME_EXIT rows stuck at pnl=0 — resolver backfill PR is the unlock).
