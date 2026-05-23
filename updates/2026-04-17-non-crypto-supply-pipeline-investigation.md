# Non-Crypto Supply Pipeline Investigation (COMMODITY / BOND / ETF)

**Date:** 2026-04-17  **Branch:** TBD (no commit yet — read-only diagnosis)
**Source data:** `audit_dashboard/data/dashboard_data.json` snapshot, `non_crypto_agent/data/*.json`, GHA run history, code grep.

User-reported state on findtorontoevents.ca/audit:

| Class | WR | PF | Active | Closed |
|---|---|---|---|---|
| Equities    | 49.4% | 0.81 | 7  | 312 |
| Forex       | 27.6% | 3.50 | 5  | 759 |
| Commodities | 25.9% | 1.17 | **0** | 444 |
| ETFs        | 42.6% | 0.00 | **1** | 61  |
| Bonds       | 47.1% | 1.60 | **0** | 17  |

Dashboard JSON cross-check (3,500 closed, 60 active, 189 active_raw): matches above; CRYPTO=47/1878 active/closed dominates.

---

## 1. Per-class supply gap diagnosis

For each class, the question is **where in the pipeline picks die**: emitter → scoring → policy gate → quality_gates.passes_active_gate → dashboard.

### 1.1 Where the pipeline dies (active_raw vs final active)

| Class | active_raw | active | Picks dropped (and why) |
|---|---|---|---|
| ETF       | 4 | 1 | XLK + ARKK (`rs-breakout-scout`, src=`kimi_riseoftheclaw`) and XLE (`quality-minus-junk`) all carry `trust_tier=UNTRUSTED` → killed by `BLOCKED_ACTIVE_TRUST_TIERS` (`quality_gates.py:586,3541`). |
| COMMODITY | 1 | 0 | CT=F (`non_crypto_consensus`) elite_grade=C, score=45, conf=0.6 — likely killed by elite_grade threshold or non_crypto_policy `min_confidence` 0.55 + no_forward_history (`non_crypto_policy.py` strategy not registered for `non_crypto_consensus`). |
| BOND      | 0 | 0 | Not even one **raw** emission. No source produces BOND-class picks today. |

### 1.2 Upstream emitters: who is (and is **not**) producing for these classes

`active_raw` source breakdown:

| Class | Total raw | Sources |
|---|---|---|
| EQUITY    | 22 | regime_terminal(9), smart_money(3), kimi_riseoftheclaw(3), super_signals(2), ml_*(3), goldmine(1) |
| FOREX     | 18 | non_crypto_consensus(10), alpha_engine(5), copytrader(1), regime_terminal(1), ml_gatekeeper(1) |
| ETF       | 4  | kimi_riseoftheclaw(3), super_signals(1) |
| COMMODITY | 1  | non_crypto_consensus(1) |
| BOND      | 0  | — |

**Critical observation:** `commodities-agent.yml`, `etf-agent.yml`, `futures-agent.yml`, `equities-agent.yml`, `forex-agent.yml` all run successfully (last 5 runs each: `gh run list` shows green). They write to `non_crypto_agent/data/*_picks.json`. **But every one of those files reports `quality: 0`** today:

```
commodities: total_raw=1,  quality=0,  symbols=12, strategies=5
etf:         total_raw=4,  quality=0,  symbols=37, strategies=4
futures:     total_raw=3,  quality=0,  symbols=15, strategies=4
forex:       total_raw=14, quality=0,  symbols=21, strategies=8
equities:    total_raw=0,  quality=0,  symbols=20, strategies=12
```

Even when the agents survive their own quality filter, **no downstream consumer reads those JSONs** (`grep` for `non_crypto_agent/data` returns only the 5 workflow YAMLs themselves). The agent outputs are **orphaned files**. None of `audit_trail/`, `alpha_engine/`, or `copy_trader_intel/` ingests `commodities_picks.json`, `etf_picks.json`, `bond_picks.json`, etc.

### 1.3 Why the agents themselves emit zero quality picks

Workflow gate is identical across all 5 agents: `confidence >= 0.50 AND risk_reward >= 1.15-1.20 AND elite_score >= 50`.

`elite_score` for a synthetic ETF/Bond/Commodity pick (test in `alpha_engine/elite_scorer.py compute_elite_score`):

| Symbol | Class | conf | rr | elite_score | Pass gate? |
|---|---|---|---|---|---|
| GLD     | ETF | 0.65 | 2.0 | **12** | NO |
| TLT     | BOND | 0.65 | 2.0 | **12** | NO |
| GC=F    | COMMODITY | 0.65 | 2.0 | **23** | NO |
| BTCUSDT | CRYPTO | 0.65 | 2.0 | 38 | NO |

The `elite_score` formula in `alpha_engine/elite_scorer.py` zeroes the `risk_reward` component (IC=-0.127), zeroes most components, and gives the largest single bonus (`forward_wr` up to +40) **only when `forward_wr` and `forward_trades` populate**. For non-crypto classes that have no forward feed → permanent score~12-23 → permanent fail of the gate=50 → agent emits zero quality picks → no consumer would read them anyway. **Chicken-and-egg starvation.**

Additional crypto-only bonuses: `TIER1_COINS`/`TIER2_COINS` (`elite_scorer.py:72-83`) and `_SOURCE_SYSTEM_SCORES` (`production_scanner.py:3304+`) reward only crypto strategies. Non-crypto gets `market_cap_tier=-5`.

### 1.4 BOND-specific: missing infrastructure

- **No `bond-agent.yml` workflow exists** (`ls .github/workflows | grep -i bond` → empty).
- `alpha_engine/bond_strategies.py` defines `BOND_STRATEGIES` (imported by `scanner.py:241`) but no scheduled job invokes them.
- `non_crypto_agent/main.py` does NOT import `bond_strategies` (only commodity/etf/futures/equity/forex). Bonds are a complete orphan.
- `non_crypto_policy.py` registers exactly **one** bond strategy (`bond_connors_rsi2`); no emitter ever fires it.

### 1.5 Smart-picks score floors

`SMART_PICKS_MIN_SCORE_*` in `audit_trail/quality_gates.py:224-241` were lowered from 60 → 40 on 2026-04-18 for COMMODITY/FUTURES, and 40 for BOND/ETF. Floors are not the bottleneck: zero raw picks reach this stage.

---

## 2. Symbol universe gap table

`alpha_engine/config.py` current vs reasonable expansion (top liquid yfinance tickers):

### COMMODITY (`COMMODITY_SYMBOLS`, n=12 today)

| Ticker | Name | Status |
|---|---|---|
| GC=F SI=F NG=F HG=F ZC=F ZW=F ZS=F KC=F SB=F PL=F CT=F CC=F | gold/silver/natgas/copper/ags | **HAVE** |
| CL=F | WTI crude | **REMOVED** (3.8% WR on 26 trades) — could re-add as SHORT-only or with seasonality filter |
| BZ=F | Brent crude | MISSING |
| RB=F | RBOB Gasoline | MISSING |
| HO=F | Heating Oil | MISSING |
| PA=F | Palladium | MISSING |
| LE=F GF=F HE=F | Cattle/Feeder/Hogs | MISSING |
| OJ=F LB=F | Orange juice / Lumber | MISSING |
| GLD SLV USO UNG DBA DBC PDBC | Commodity ETF proxies | MISSING (would help when futures data flaky) |

### ETF (`ETF_SYMBOLS`, n=24 today)

Have: SPY QQQ DIA XLK XLF XLE XLV XLI XLB XLU XLY XLP XLC SMH SOXX ARKK KWEB EEM EFA VEA VNQ GLD SLV IWM (+ a few missed).

| Ticker | Status |
|---|---|
| VOO VTI VTV VUG VEU IXN IYR | MISSING (broad/factor) |
| IEMG ACWI EWJ EWZ FXI INDA | MISSING (regional) |
| TQQQ SQQQ UPRO SPXL SOXL TNA | MISSING (3x leveraged — high signal) |
| ARKG ARKW ARKQ ARKF | MISSING (other ARK) |
| XBI IBB | MISSING (biotech) |
| XLRE | MISSING (real estate sector) |
| GDX GDXJ | MISSING (gold miners — much more signal than GLD) |
| FXE FXY UUP | MISSING (currency ETFs) |
| VIXY UVXY | MISSING (vol ETFs — useful for regime gates) |

### BOND (`BOND_SYMBOLS`, n=8 today)

Have: TLT IEF SHY LQD HYG AGG BND EMB.

| Ticker | Status |
|---|---|
| TLH | MISSING (10-20yr treasury) |
| GOVT BIV BSV | MISSING (broader treasury) |
| MUB | MISSING (munis) |
| TIP VTIP | MISSING (TIPS) |
| BNDX | MISSING (international bond) |
| JNK | MISSING (high yield twin of HYG) |
| BIL SGOV | MISSING (cash equivalents) |
| ZB=F ZN=F ZT=F ZF=F | Already in FUTURES_SYMBOLS, not bridged into BOND emitters |

**Estimate:** universe expansion alone (without strategy fix) raises raw-emission count linearly: COMMODITY 12→25 (+108%), ETF 24→45 (+88%), BOND 8→14 (+75%). Won't fix the elite_score gate but doubles the funnel input.

---

## 3. Baby strategies inventory & release readiness

`baby_strategies/`: 191 `.py` files, 48 `.meta.json` files (40 named `*.py.meta.json`, 8 `*.meta.json`).

| Status (from `meta.json:status`) | Count | Notes |
|---|---|---|
| `backtest_failed` | 19 | Killed |
| `backtest_passed` | 8 | All show `WR=0.0, PF=0.0` (placeholder metrics — actually never re-validated) |
| `awaiting_forward_test` | 6 | Inverse mutations (consecutive_beats, earnings_drift, value_quality, etc.) |
| `ready_for_forward_test` | 4 | **`vol_scaled_keltner` WR 75% PF 20.96**, `multi_timeframe_ema_cloud` WR 72% PF 6.95, `regime_sentinel_composite` WR 50% PF 2.56, `moving_average_slope_momentum` WR 56% PF 1.33 |
| `utility_framework` | 7 | Not strategies — runners/helpers |
| `awaiting_backtest` | 2 | Pending |
| `draft - not wired` | 2 | Explicit no-promote |
| **No metadata at all** | 149 | Never even backtested (or backtested via untracked path) |

`vt_baby_strategies` is imported in `scanner.py:441`, but **none of the high-PF candidates above** (`vol_scaled_keltner`, `multi_timeframe_ema_cloud`, `regime_sentinel_composite`) is wired into any registry that emits to `active_raw`. They are not in `non_crypto_agent/main.py`, not in `commodities-agent.yml`, not in `etf-agent.yml`, not in `bond_strategies.py`'s `BOND_STRATEGIES`, and not in `non_crypto_policy.NON_CRYPTO_STRATEGY_POLICY`.

**Bottom line:** ~149 baby strategies never backtested; 18 with usable metadata; **4 are "ready_for_forward_test" with passing metrics but zero of them are RELEASED**. `vol_scaled_keltner` PF 20.96 is the most extreme outlier — should be re-validated on a chrono split before promotion (likely overfit), but also could be a genuine tight-vol regime filter.

---

## 4. Top strategies per class that COULD generate active picks

From `picks.recent_closed`: which strategies HAVE produced closed picks in each class? Are they still active in registries?

### COMMODITY (438 closed)

| Strategy | Closed n | Wired into emitter? | Notes |
|---|---|---|---|
| `futures_momentum`         | 369 | YES (in `futures_strategies.py`) | Dominant historical producer; not running for COMMODITY in commodities-agent (only `seasonal_momentum`, `gold_safe_haven`, `oil_inventory_momentum`, `metals_mean_reversion`, `agricultural_spread`). |
| `cta_cross_asset_tsmom`    | 31  | Defined in `cta_bridge.py` | Not invoked by any GHA workflow on a schedule. |
| `cta_commodity_momentum_term` | 20 | Policy registered (`non_crypto_policy.py:61`) | No emitter wires it. |
| `cta_golden_cross_200`     | 6   | Unknown | Probably orphaned `cta_bridge.py` output. |
| `cot_positioning`          | 5   | Policy registered                | No active commodity feed. |

### BOND (17 closed)

| Strategy | Closed n | Wired? | Notes |
|---|---|---|---|
| `futures_momentum`         | 8 | Yes (futures_strategies) | Was emitting on ZN=F; needs to be re-routed for BOND emission. |
| `betting-against-beta`     | 5 | Unknown — looks like `kimi_riseoftheclaw` source | Could be amplified. |
| `pairs-trading`            | 2 | Unknown | |
| `rs-breakout-scout`        | 1 | Yes (kimi) | Per-pick UNTRUSTED kills it. |
| `vwap-reversion-scout`     | 1 | Yes (kimi) | Same. |

### ETF (61 closed)

| Strategy | Closed n | Wired? | Notes |
|---|---|---|---|
| `quality-minus-junk`        | 10 | YES (kimi_riseoftheclaw) | UNTRUSTED gate kills it (XLE today). |
| `intermarket-flow-scout`    | 7  | YES (kimi) | Same trust gate. |
| `proven_vwap_mean_reversion`| 4  | Unknown | Probably orphaned. |
| `betting-against-beta`      | 4  | YES (kimi) | Same trust gate. |
| `vwap-reversion-scout`/`rsi-divergence-scout`/`call-surge-scout`/`options-flow-scout` | 3 ea | YES (kimi) | All UNTRUSTED. |

**Pattern:** ETF and BOND historical producers are dominantly `kimi_riseoftheclaw` strategies that are now **all globally suppressed by `BLOCKED_ACTIVE_TRUST_TIERS = {BANNED, AVOID, UNTRUSTED}`**. The 7 leaked picks at score=120 in 2026-04-04 (referenced in `quality_gates.py:587`) caused this blanket trust rejection. Side effect: kimi was the only ETF/Bond emitter, so the entire feed went dark.

---

## 5. Concrete next steps (numbered, with risk profile)

| # | Step | Effort | Risk | Estimated uplift |
|---|---|---|---|---|
| 1 | **Wire `non_crypto_agent/data/*_picks.json` into the pick aggregator.** Add a reader in `audit_trail/dashboard_generator.py` that loads commodities_picks.json + etf_picks.json + futures_picks.json + equities_picks.json + forex_picks.json into `active_raw` with `source_system='non_crypto_agent'`. | LOW | LOW (additive) | Limited until step #2 because agents emit 0 quality today, but unblocks pipeline. |
| 2 | **Recalibrate `elite_score` for non-crypto** — either (a) add `+25 base bonus` for `category in {etf,bond,commodity,futures}` until forward_wr populates, or (b) bypass elite_score gate when `category != crypto` AND policy.allow_without_forward=True. Without this, agents emit 0 → step 1 has no payload. | LOW | MED (could let in low-quality non-crypto) | +5-15 active picks/day across COMMODITY+ETF+BOND combined within first week. |
| 3 | **Create `bond-agent.yml`** following `etf-agent.yml` template. Import from `bond_strategies` (BOND_STRATEGIES already exists). Cron daily 14:30 UTC. Include TLT IEF SHY LQD HYG AGG BND EMB + add TLH GOVT JNK MUB TIP. | LOW | LOW | +1-3 active BOND picks/day. |
| 4 | **Surgical un-block of kimi ETF/Bond strategies.** Replace blanket `UNTRUSTED` trust block with per-strategy carve-out: allow `quality-minus-junk`, `intermarket-flow-scout`, `betting-against-beta` (10/7/4 closed picks each, modest WR) on ETF only, with `min_score=45` floor instead of trust tier. | LOW | MED (these are why UNTRUSTED was applied — re-audit closed WR before unblocking). | +3-5 ETF actives/day immediately. |
| 5 | **Expand symbol universes** per §2 table. COMMODITY 12→25, ETF 24→45, BOND 8→14. Single edit to `alpha_engine/config.py`. | LOW | LOW | Linear funnel widening; +50% raw signal volume per class. |
| 6 | **Re-validate + promote `vol_scaled_keltner`, `multi_timeframe_ema_cloud`, `regime_sentinel_composite`, `moving_average_slope_momentum`** from `baby_strategies/`. Run a chrono split on each (the 75%/72% WR is suspect — likely overfit). If real, register in `non_crypto_policy.NON_CRYPTO_STRATEGY_POLICY` and wire into etf/futures/commodities agents. | MED | MED (overfit risk) | If 2 of 4 survive forward validation: +2-5 actives/day across ETF+COMMODITY. |
| 7 | **Re-route `futures_momentum` strategy** (369 commodity closed picks!) to commodities-agent. It's the dominant historical commodity producer but the GHA workflow only invokes 5 strategies (none being `futures_momentum`). Add it to the import block. | LOW | LOW (proven historical edge) | +5-10 commodity actives/day; reverses the 0 → multi-pick gap. |
| 8 | **Add `cta_commodity_momentum_term` + `cta_cross_asset_tsmom` + `cot_positioning` emitters** — all three are policy-registered but lack a scheduled emitter. Either invoke `cta_bridge.py` from a new GHA workflow OR import their functions into commodities-agent.yml. | MED | LOW | +2-4 commodity actives/day. |
| 9 | **Investigation doc** for restoring `kimi_riseoftheclaw` UNTRUSTED → WATCH on ETF subset only. Cite the 4-10 closed picks per strategy with realized WR/PF. Path: `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` template (in reverse: investigation_before_unblock). Required by `CLAUDE.md` policy. | MED | LOW | Gates step #4. |
| 10 | **Symbol-level expansion of equities universe (DEFAULT_UNIVERSE n=37)** to top S&P 100 + Nasdaq 100 winners. Currently the equities-agent runs against only 20 symbols (per `equities_picks.json: symbols_tracked=20`) which produces 0 raw picks every run. | LOW | LOW | +3-7 EQUITY actives/day. |

### Estimated active-pick uplift (per day, after all steps)

| Class | Today | After steps 1-3 | After all (1-10) |
|---|---|---|---|
| COMMODITY | 0 | 1-2 | **8-15** |
| BOND      | 0 | 0-1 | **3-5** |
| ETF       | 1 | 3-5 | **8-12** |
| EQUITY    | 7 | 7 | 10-14 |
| **Total non-crypto** | **13** | ~17-20 | **~35-50** |

---

## 6. Code hotspots referenced

- `alpha_engine/non_crypto_policy.py` — strategy registry (lines 24-206) + asset normalization
- `alpha_engine/elite_scorer.py` — scoring formula crypto-biased (lines 14-34, 72-83)
- `alpha_engine/config.py` — symbol universes (lines 530-647)
- `audit_trail/quality_gates.py:586` — `BLOCKED_ACTIVE_TRUST_TIERS` (kills kimi ETF)
- `audit_trail/quality_gates.py:224-241` — SMART_PICKS_MIN_SCORE per class
- `audit_trail/quality_gates.py:3509-3582` — `passes_active_gate` chain
- `alpha_engine/production_scanner.py:2178-2237` — Gate 0 strategy block list
- `non_crypto_agent/main.py` — entrypoint that lacks bond import
- `.github/workflows/{commodities,etf,futures,forex,equities}-agent.yml` — workflow runners (no bond-agent.yml)
- `baby_strategies/*.meta.json` — promotion candidates, status field
