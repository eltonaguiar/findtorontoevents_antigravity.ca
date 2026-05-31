# /money-maker-readyv2 — FUTURES

_Snapshot: 2026-05-31 ~06:30Z. Source: live `ejaguiar1_stocks.trading_picks` (no `status='CLOSED'` rows exist for FUTURES — verdict pipeline silently drops the entire class; numbers below use the terminal-status union `('CLOSED','WON','LOST','TP_HIT','SL_HIT','TIME_EXIT','EXPIRED')`)._

## Class verdict at 06:30Z 2026-05-31

```
PF=1.02   WR=1.27%   n_terminal=393 (n_with_pnl_signal=19)   avg_pnl=+0.07%   std=0.72%   Sharpe-proxy~0.10
T2 status: FAIL on all 4 axes (PF, WR, MDD-not-measurable, n_effective)
```

**The reported n=393 is a mirage.** 374/393 terminal rows are `TIME_EXIT` with `exit_price = entry_price` and `pnl_pct = 0.0000` and `closed_at IS NULL` — the resolver wrote a terminal status without ever marking to market. After excluding those, the *real* sample is **n_effective = 19** (5 wins / 14 losses → WR 26.3%, PF 1.02, all of which is noise on so few rows).

Status histogram (category='futures'):

```
OPEN       35
TIME_EXIT 374   <- 372 of 374 have pnl_pct=0 + closed_at NULL (resolver bug, INCIDENT_FUTURES#1)
LOST       14
WON         4
TP_HIT      1
            (no SL_HIT, no CLOSED)
```

## Best candidate

No strategy in this class has n>=10 *real* closures. The least-broken candidate is:

```
proven_futures_term_structure_proxy
  n_term=1, WON, pnl=+1.17%, age <72h
  4 active open positions on ES/NQ (entered 2026-05-26 to 2026-05-29)
```

Honorable mention (insufficient n but non-zero edge):

```
ema_stack_momentum         n=2  WR=50%  PF=1.71  avg=+1.66%   (Mar 2026, stale)
hyperopt_connors_rsi2      n=3  WR=33%  PF=0.08  avg=-0.94%   (Mar 2026, stale)
```

There is **no FUTURES candidate on the Phase 3 MC watchlist** — the live `futures_cross_asset_momentum` (n=14, 100% OPEN) is too young for MC scoring; closest analog is FOREX `fx_smart_carry_trade_momentum` (P(T2 at n=100)=64%).

## T2 gap

- **Headline gap:** 100 - 0 real clean closures = **100 closures needed**.
- **Emission cadence (last 14 days):** ~3 picks/day; ~9 picks on 2026-05-29 peak, only 16-pick `multi_asset_copytrader` spike on 2026-05-04 historically.
- **Resolution cadence:** **ZERO real closures in 60+ days** because resolver is shorting the FUTURES path. The only meaningful row in the entire 30-day window is `proven_futures_term_structure_proxy` (1 WON, hand-resolved).
- **Time-to-T2 at *current* cadence:** indeterminate (∞). Even at 3 picks/day, if the resolver is fixed and we maintain the current ~33% real WR with PF~1.0, **we'd need ~100 / 3 ≈ 34 calendar days minimum** to reach n=100 — but P(T2 at n=100) at PF=1.0 is functionally 0%, so reaching n=100 doesn't help.
- **Real bottleneck (in order):**
  1. **Resolver TIME_EXIT mark-to-market bug** (INCIDENT_FUTURES#1) — strands the entire class.
  2. **No edge yet** — the only strategy with volume (`futures_connors_rsi2`, n=373) shows PF=undefined / avg=+0.02% i.e. random walk. Mean-reversion on e-minis with 96h max-hold is not an edge in 2026 regime.
  3. **Single-strategy concentration** — `futures_connors_rsi2` is 87% (373/428) of the class. Per CLAUDE.md "concentration = strategy not engine" rule, HHI on strategy = **0.76** → way over the 0.30 ceiling.

## Actions ranked by impact

### 1. SHIP — fix FUTURES TIME_EXIT mark-to-market in resolver (P0, unblocks the whole class)
- **File:** `alpha_engine/outcome_resolver.py`
- **Bug:** lines 1507-1512 — when `aged_out` and neither TP nor SL hit, resolver calls `classify_outcome(pnl_pct)` but `pnl_pct` is the *current* mid-quote at resolve-time-of-day, which for non-crypto with weekend/after-hours data fetched via yfinance often returns the last close == entry price → pnl_pct=0 → outcome=NONE → status flips to TIME_EXIT with exit_price unchanged. Also `closed_at IS NULL` is never set on this path for FUTURES (see line 1808 only sets it in v2.3 flow).
- **Fix:** on the TIME_EXIT branch for `=F` symbols, force a yfinance `1m` intraday fetch for the close at `pick.created_at + max_hold_hours` and only fall back to `1d` close if intraday is empty; on success, set `exit_price=close_at_t_exit`, `pnl_pct=(exit_price-entry_price)/entry_price * direction_sign`, `closed_at=t_exit`, `status='CLOSED'`.
- **One-shot DB backfill:** `tools/backfill_futures_time_exit.py` (new) — for the 372 stranded rows, compute `t_exit = created_at + 96h`, fetch yfinance 1m bars at that window, write exit_price/pnl_pct/closed_at, flip status TIME_EXIT → CLOSED.
- **Expected impact:** real n jumps from 19 → ~391 overnight, real PF/WR computable for the first time, class enters T2 evaluation.

### 2. KILL — `futures_connors_rsi2` after backfill if PF<1.2 (likely)
- **File:** add `futures_connors_rsi2` to `BLOCKED_SOURCE_SYSTEMS` only if backfill confirms PF<1.2 at n=300+.
- **Pre-kill mutation pass per** `docs/MUTATION_THREE_AXIS_PROTOCOL.md`:
  - Axis A — regime gate: VIX > 25 only (futures mean-reversion historically works in elevated-vol regime; 2026 has been a low-vol grind).
  - Axis B — vol floor: ATR(14)/close > 0.8% per symbol (skip dead-zone YM/ES sessions).
  - Axis C — source-confluence: require co-signal from `proven_futures_term_structure_proxy` OR `contango_roll_yield` to fire.
- **Where:** likely lives in `alpha_engine/multi_asset_copytrader.py` or `alpha_engine/futures_strategies.py` — caller wires to `multi_asset_copytrader` (371/428 picks).
- **Decision:** if mutated PF still <1.2 at n>=50 post-mutation, kill. Otherwise re-emit under `_v2` suffix.

### 3. ADD — short-volatility-of-volatility / VIX term-structure edge
- **Concrete:** new strategy `futures_vix_term_structure_v1` — short VIX futures when VX1!/VX2! contango >5%, target the front-month roll yield, max hold 5 days. Historical edge (DBMF/SVXY analogs) is real and uncorrelated to e-mini directional bets.
- **Wire:** add emitter under `alpha_engine/futures_strategies.py` or follow the `proven_futures_term_structure_proxy` pattern; symbol set `{VX=F, VXM=F}` only.
- **Data source:** yfinance `^VIX9D`, `^VIX`, `^VIX3M`, `^VIX6M` for live term-structure signal (free).
- **Why:** of the 6 FUTURES strategies emitting today, 5 are e-mini index mean-reversion (correlation ~1 to EQUITY). The class needs an actually-futures-native edge.

### 4. ADD — 200-day MA trend strategy on commodity futures (Phase 9 candidate #6)
- **Concrete:** `futures_200dma_trend` — long when close > 200-day SMA and 50-day MA > 200-day MA, on `{GC=F, SI=F, CL=F, HG=F, NG=F}`. Max hold 30 days. This implements PR #190 Phase 9 candidate #6 for the FUTURES asset class specifically.
- **Wire:** new file `alpha_engine/futures_trend_200dma.py`, register in `alpha_engine/strategy_registry.py` under category=`futures`, caller: `alpha_engine/multi_asset_scanner.py` (which already has 16 futures rows).
- **Pre-register hypothesis** under M-107 before first emission: `reports/hypothesis_registry.json` += entry `H-FUT-200DMA-2026-05-31`.

### 5. WATCHLIST — protect emission cadence on `proven_futures_term_structure_proxy`, `contango_roll_yield`, `futures_cross_asset_momentum`
- These three together are 28 picks all opened May 17 onwards. Once resolver is fixed (action #1), they will start producing real closures.
- **Action:** add to a `FUTURES_PROTECTED_STRATEGIES` set in `alpha_engine/active_picks_manager.py` so dedupe / suppression policies don't silently kill them.

### 6. FIX — symbol concentration (e-mini index basket is 91.8% of class)
- YM=F 35.0% + ES=F 22.9% + NQ=F 21.3% + RTY=F 12.6% = 91.8% (these are all S&P / Dow / Nasdaq / Russell e-minis, i.e. EQUITY-correlated, not real futures diversity).
- **Action:** add a per-symbol cap of 25% to the emission policy for `category='futures'` in whichever scanner emits — likely `alpha_engine/multi_asset_copytrader.py`. Force daily rotation across `{GC=F, SI=F, CL=F, HG=F, NG=F, ZN=F, ZB=F, ZC=F, ZS=F}` when those symbols clear the gate.

## Risk factors / blockers

- **Resolver bug (Phase 4 finding) confirmed in FUTURES:** 372/393 terminal rows are pnl=0 phantom-closes. Severity HIGH. INCIDENT_FUTURES#1 above.
- **Category mis-tag risk:** verified — only `futures` (lowercase) is used. No `future` / `futs` / `FUTURES` rows exist. Verdict pipeline must continue to lowercase-match.
- **Cross-tag risk with COMMODITY:** the `=F` suffix is shared. `commodity_carry_momo_double_sort`, `commodity_momentum`, `commodity_channel_index_bounce` all land under `futures` category here but the same logic emitted under COMMODITY category elsewhere — confirm `category` set at emit-time matches the strategy intent or we double-count. Audit query:
  ```sql
  SELECT strategy, category, COUNT(*) FROM trading_picks
  WHERE strategy LIKE 'commodity_%' GROUP BY strategy, category;
  ```
- **Stale pf_registry:** `pf_registry.by_asset_class_policy_clean_net` shows FUTURES as INSUFF-N (n=0). After action #1 ships, registry must be recomputed. Trigger: `python3 tools/update_pf_registry.py --class FUTURES`.
- **Yfinance after-hours / weekend gap:** the resolver's TIME_EXIT branch needs to gracefully handle when `t_exit` falls on a Sunday or holiday — fall forward to the next session open.
- **No MDD computable** until n_effective > 30.

## What I would ship next (concrete PRs)

### PR A — `fix(resolver): FUTURES TIME_EXIT mark-to-market + backfill`
- `alpha_engine/outcome_resolver.py`: patch lines 1507-1512 to fetch intraday close at `t_exit` for `symbol LIKE '%=F'` before classifying.
- `tools/backfill_futures_time_exit.py`: new — backfill the 372 stranded rows; idempotent on `closed_at IS NULL AND status='TIME_EXIT' AND category='futures'`.
- `reports/INCIDENT_FUTURES_1_time_exit_phantom_close_2026-05-31.md`: post-mortem.
- Expected lift: class n jumps from 19→~391; real verdict numbers computable for first time.

### PR B — `feat(futures): VIX-term-structure strategy v1 (sidecar)`
- `alpha_engine/futures_vix_term_structure.py` (new).
- `alpha_engine/strategy_registry.py`: register under `category='futures'`.
- `reports/hypothesis_registry.json`: pre-register `H-FUT-VIXTERM-2026-05-31` per M-107.
- `## Wiring Plan` block in PR body: production caller = `alpha_engine/multi_asset_scanner.py`, target wire-up PR within 7 days.
- Goal: add an actually-futures-native edge to break the 91.8% e-mini-index concentration.

---

**Bottom line.** FUTURES isn't strategy-blocked; it's plumbing-blocked. Fix the resolver, get 372 real outcomes overnight, and only THEN make a real T2 call. The single most leveraged action in this entire class is **PR A**. Everything else (kill futures_connors_rsi2, add VIX term-structure, add 200dma trend) is downstream of getting honest numbers on the board.
