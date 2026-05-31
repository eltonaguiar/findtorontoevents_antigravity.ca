# /money-maker-readyv2 — COMMODITY

## Class verdict at 06:30Z 2026-05-31
- **Raw basis (all closed)**: n=5,566, WR=5.4% (298W/5,268L), PF=0.36, avg=-0.118%, σ=2.03 — polluted by 4,727 TIME_EXIT rows all with pnl=0
- **CLEAN basis (`status IN ('WON','TP_HIT','LOST')`)**: n=839, WR=35.5% (298W/541L), PF=0.36 (gw=370.40 / |gl|=1028.01), avg=-0.79%, σ=5.19
- **T2 status**: **FAIL on all four gates** — PF 0.36<<1.5, WR 35.5%<50%, n=839 is fine but quality is destructive, MDD cannot save it
- **14d recency**: 44 clean closures, 1 win, gross_win 5.00 / gross_loss -207.18 → PF ≈ 0.024, WR ≈ 2.3% (catastrophic collapse — class is actively bleeding)
- **Concentration**: HG=F 27% / SI=F 26% / PL=F 19% / GC=F 11% / CL=F 6% on clean — HHI ≈ 0.18 (within concentration gate)
- **Active queue**: 871 OPEN/ACTIVE picks waiting to resolve

## Best candidate
**None at n≥100.** Only candidates with n≥10 clean:

| source_system | strategy | n_clean | W | L | WR | PF | avg |
|---|---|---|---|---|---|---|---|
| multi_asset_copytrader | futures_momentum | 628 | 223 | 405 | 35.5% | **0.25** | -0.67% |
| cta_replicator | cta_cross_asset_tsmom | 97 | 19 | 78 | 19.6% | **0.29** | -1.46% |
| cta_replicator | cta_commodity_momentum_term | 52 | 21 | 31 | 40.4% | **0.32** | -0.34% |
| cta_replicator | cta_golden_cross_200 | 26 | 20 | 6 | **76.9%** | **11.61** | **+3.86%** |

`cta_golden_cross_200` is the only edge — and it is **already retired by Phase 5 / PR #182** as a resolver artifact (per session brief). Real MC P(T2 at n=100) for this strategy on COMMODITY: **not flagged on Phase 3 watchlist** (no commodity MC candidate exists).

`cta_commodity_momentum_term` is already in `alpha_engine/strategy_blocklist.py:319` (banned 2026-05-03, PF 0.02). The 52 clean closures here are pre-block carry-over.

## T2 gap
- At PF=0.36 and WR=35.5%, **no number of additional closures gets this class to T2**. The trajectory is negative-EV.
- Even restricting to the best non-artifact strategy (`futures_momentum`, n=628, PF 0.25), more data only deepens the loss.
- 14d cadence: 44 clean closures / 14d = **3.1 clean closures/day** — but the **TIME_EXIT rate is ~85%** of all closures, so production is emitting picks faster than they're being properly resolved.
- **The real bottleneck is the resolver**, not strategy edge: 4,727 of 6,516 picks (72.5%) hit TIME_EXIT with pnl=0. That's a resolver that gives up without checking intrabar TP/SL — direct Phase 4 finding applied to this class.

## Actions ranked by impact

### 1. **P0 — Fix the TIME_EXIT plague (resolver intrabar verification)** — biggest impact by far
- **Symptom**: 4,727 COMMODITY rows = `TIME_EXIT` with `pnl_pct=0`. These are picks the resolver gave up on without checking whether TP or SL was touched intrabar during the holding window.
- **File**: `alpha_engine/outcome_resolver.py` — same code path Phase 4 identified.
- **Fix**: when a pick reaches its time horizon, fetch intrabar OHLC (1h or 4h bars from `yfinance` `=F` symbols are free) for the holding window and apply TP-first-touch vs SL-first-touch rule, then mark as `TP_HIT` / `LOST` / true `TIME_EXIT` (only if neither barrier touched). Mirror crypto path that already does this.
- **Expected impact**: of the 4,727 TIME_EXIT rows, MC estimate ~25–35% will resolve to TP_HIT, ~30–40% to LOST, ~30% to true flat — recovering n≈2,000 clean closures across all strategies and unlocking real per-strategy verdicts. This is the **single highest-leverage PR** for COMMODITY.

### 2. **P0 — Quarantine `futures_momentum` on COMMODITY (multi_asset_copytrader)** — stop the bleed
- **Strategy**: `multi_asset_copytrader / futures_momentum` — n=628 clean, **PF 0.25, WR 35.5%, avg -0.67%/trade**. This single (source, strategy) pair represents **75% of all clean closures** in COMMODITY and is the primary cause of class-level PF=0.36.
- **File**: `alpha_engine/commodity_kill_switch.py:48-55` — add `("multi_asset_copytrader", "futures_momentum")` to a new `_RETIRED_PAIRS_FOR_COMMODITY` set, OR add `multi_asset_copytrader_futures_momentum_commodity` to `alpha_engine/strategy_blocklist.py::_BLOCKED_SOURCE_STRATEGY_PAIRS` (line ~190).
- **Mutation-three-axis**: the strategy fails on all three axes simultaneously — no regime gate helps (broad fail across 8 symbols), no vol floor helps (already losing in all vol regimes), no source-confluence helps (it's the largest single source). Verdict: **KILL on COMMODITY only** (preserve on FOREX/EQUITY if used there).
- **Expected impact**: drops class to n=211 clean, but PF improves to roughly (370.40-150) / (1028.01-272) ≈ 0.29 — still bad, exposes the truth that no real edge exists yet.

### 3. **P1 — Auto-tune `commodity_kill_switch` PF threshold from 0.9 to 1.0** — defense in depth
- **File**: `alpha_engine/commodity_kill_switch.py:37` — `_PF_KILL_THRESHOLD = 0.9` → `1.0`. Combined with #2 above, this catches `cta_cross_asset_tsmom` (PF 0.29) and `non_crypto_consensus` (PF 0.0 on 544 closed) on the next sweep.
- **Wire-up check**: confirm `feed_hygiene.is_valid_active_pick()` calls this kill-switch on COMMODITY signal evaluation (per file docstring line 16). If not wired, this PR also needs the integration line.

### 4. **P1 — Reclassify TIME_EXIT pnl=0 as `UNRESOLVED` not as closure**
- **File**: `alpha_engine/outcome_resolver.py` AND `audit_dashboard/dashboard_data_generator.py` (whichever computes `asset_class_health`) — exclude `status='TIME_EXIT' AND pnl_pct=0` from the closed-count denominator. This stops the dashboard from claiming "5,566 closed picks" when 84% are unresolved.
- Also: backfill the 8 `null_pnl` rows flagged in the overall query.

### 5. **P2 — ADD: BOIL/UNG vs NG=F mean-reversion sidecar (opt-in)**
- The one slightly bright spot is HG=F (109W/116L = 48.4% WR — closest to break-even of any commodity symbol). Build a dedicated **copper mean-reversion** strategy gated on inventory data (LME copper stocks + CME warrant changes, both free APIs) instead of generic CTA momentum.
- **File to add**: `alpha_engine/copper_inventory_reversion.py` (new) — opt-in sidecar per the Wire-Up Rule, with `## Wiring Plan` naming `production_scanner.score_pick` as target caller for 2026-06-14.
- This is the one COMMODITY add with a credible hypothesis (mean-reversion driven by warehouse stock surprises is documented in CFTC literature).

### 6. **P2 — WATCHLIST: `multi_asset_cot / cot_positioning`**
- n=44 clean, WR 4.5%, PF 1.67, avg +0.087. Small sample, hint of edge if WR is real. Protect emission cadence (don't block during sweep). Need n≥30 more clean closures before MC.

## What I would ship next

### PR A — `fix(resolver): intrabar TP/SL verification for COMMODITY time-exits`
- Modify `alpha_engine/outcome_resolver.py` to fetch yfinance 1h OHLC for `*=F` symbols across the holding window and apply first-touch rule, mirroring crypto path.
- Backfill: one-shot script `tools/backfill_commodity_time_exits.py` to reprocess the 4,727 existing TIME_EXIT rows.
- Acceptance: after backfill, TIME_EXIT rows with pnl=0 drop below 10% of COMMODITY closures.

### PR B — `fix(commodity): kill `multi_asset_copytrader/futures_momentum` and tighten kill-switch`
- `alpha_engine/strategy_blocklist.py`: add `("multi_asset_copytrader","futures_momentum")` to `_BLOCKED_SOURCE_STRATEGY_PAIRS` with comment citing PF 0.25 / n=628 / 2026-05-31 verdict.
- `alpha_engine/commodity_kill_switch.py:37`: `_PF_KILL_THRESHOLD = 0.9` → `1.0`.
- `audit_dashboard/dashboard_data_generator.py`: exclude `TIME_EXIT AND pnl=0` from class-health denominator.
- Acceptance: COMMODITY class PF on clean basis recomputes above 0.4 (still FAIL, but honest), and 14d emission falls because blocked pairs stop generating.

## Risk factors / blockers
- **Resolver bug (Phase 4)**: directly hits COMMODITY harder than any other class — 72.5% TIME_EXIT pollution. Until fixed, every per-strategy verdict is suspect.
- **Category tagging**: only `commodity` (lowercase) appears in this DB for this class. No `commodities` plural drift detected.
- **Stale pf_registry**: not cross-checked here — likely shows different numbers because it post-dates Phase 5 retirement of `cta_golden_cross_200` but pre-dates the TIME_EXIT cleanup proposed above. Operator should rerun `pf_registry` generator after PR A.
- **No MC candidate**: COMMODITY did not produce a Phase 3 MC watchlist entry. Without a credible MC-flagged strategy, sizing-up is off the table for this class until either PR A surfaces buried edge in `futures_momentum`/`cta_cross_asset_tsmom` post-resolver-fix, or PR-A1 ("copper inventory reversion") ships.
- **Active queue overhang**: 871 OPEN picks — if PR A's intrabar verifier is applied, expect a large one-time PF shift (could swing either direction). Run on a shadow column first, validate distribution, then apply.

---
DOCS_PR target: docs-only changes (the two reports above). Implementation PRs A/B are separate.
