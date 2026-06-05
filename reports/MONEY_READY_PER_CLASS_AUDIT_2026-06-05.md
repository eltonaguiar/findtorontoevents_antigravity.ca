# Per-Asset-Class Money-Ready Picks Audit & Wire-Up Plan
**Date:** 2026-06-05 14:21 UTC
**Operator goal:** top money-ready picks per asset class on /audit + /audit/ai-tournament.html
**Status:** 0/8 classes pass T2 money-ready. Cannot wait months for forward tests. Audit + immediate wire-up in progress.

---

## Executive Summary

| Class | Policy-clean stats | Single-source risk | Best unfiltered candidate | Gap to money-ready |
|---|---|---|---|---|
| CRYPTO | n=301 WR=34.6% PF=0.99 | All high-PF rows SINGLE | battleground_luxalgo n=26 WR=50% PF=3.98 | Multi-source replication |
| EQUITY | n=45 WR=24.4% PF=0.26 | Yes + regime_terminal is the drag | cta_golden_cross_200 n=63 WR=66.7% avg+0.41% | Re-emit via 2nd source |
| FOREX | n=22 WR=22.7% PF=11.22 | All SINGLE | non_crypto_consensus n=102 WR=58.8% | Decompose aggregator |
| COMMODITY | n=6 WR=50% PF=3.06 | All SINGLE | non_crypto_consensus n=836 WR=59.0% avg+0.79% | Decompose aggregator |
| ETF | n=11 WR=63.6% PF=0.80 | All SINGLE | antigravity_strategies n=120 WR=77.5% PF=4.22 | 2nd independent emitter |
| FUTURES | n=15 WR=6.7% PF=0.07 | Yes | antigravity_strategies n=227 WR=71.8% PF=5.26 | Resolver bug (TIME_EXIT) |
| BOND | n=0 (under-threshold) | All single | n/a — no live emitter | No sleeve wired |
| PENNY_STOCK | excluded by charter | n/a | n/a | excluded |

**Top blocker across ALL classes: single-source concentration.** Every high-PF row is one generator's bias — the 2026-06-02 mega_mutation sign-flip incident (141 rows WR inflated from 36.8% to 65.4%) is a precedent for this exact failure mode. Source diversity is the #1 thing we lack.

**Second blocker: 3 orphan emitters exist that already produce daily picks but never reach trading_picks**:
- `forex_carry_momentum` (4 fresh picks today, production_enable=true in JSON, no INSERT to trading_picks)
- `funding_rate_arb` (10 picks/day, never measured in pf_registry)
- `commodity_term_cot` (3 picks in JSON, production_enable=false)

**Third blocker: structural losers still emitting**:
- `multi_asset_cot` (COMMODITY n=223 WR=17%) — dominant emitter, actively losing
- `regime_terminal` (EQUITY n=17 WR=17.6% PF=0.19) — live emitting 2026-06-05

---

## Finished Actions (this session)

### 1. Per-asset-class subagent swarm
Dispatched 4 parallel subagent audits (CRYPTO, EQUITY, ETF+FUTURES+BOND, FOREX+COMMODITY). All 4 returned DB-verified inventories of strategies, external data, top candidates, and concrete wire-up plans with file:line references. See `reports/per_class_scrutiny_*` and the per-agent outputs.

### 2. Per-class baseline inventory (live DB)
- `by_asset_class_policy_clean_net`: CRYPTO n=301 WR=34.6% PF=0.99 (worst class), FUTURES n=15 WR=6.7% PF=0.07 (catastrophic)
- `by_asset_class_strategy_policy_clean_net`: best CRYPTO row is battleground_luxalgo PF=3.98 (n=26 SINGLE); UNKNOWN bucket PF=3.12 (n=40 multi-source)
- All other classes have n<25 in policy-clean — too thin to derive edge from internal data alone

### 3. External data source inventory
- **Analyst picks**: `predictions/data/leaderboard.json` 222 entries, 10d stale, is_known_analyst=0 for all (scraper broken)
- **Earnings**: pead_earnings_cache.json has 4 tickers (AAPL/MSFT/AMZN/GOOGL) with real surprise_pct; earnings_calendar.json empty; PEAD_EQUITY_ENABLED=0
- **On-chain**: coinmetrics_signal.py + arkham_smart_money.py exist but not emitting
- **COT**: 12 commodity files fresh 2026-06-05 09:07; consumed only by multi_asset_cot (broken) and cot_paper_pilot (falsified)
- **Yields**: ^TNX only; no 3M OIS, no FRED
- **Funding rates**: Binance/Bybit live via basis_carry.py/funding_rate_arb.py (CRYPTO-only)

### 4. Identified top unfiltered picks (raw DB, not policy-clean)
These have real edge but ALL carry single-source risk:
- **CRYPTO/antigravity_strategies** n=120 WR=77.5% PF=4.22
- **FUTURES/antigravity_strategies** n=227 WR=71.8% PF=5.26
- **EQUITY/cta_golden_cross_200** n=63 WR=66.7% avg+0.41%
- **ETF/antigravity_strategies** n=120 WR=77.5% PF=4.22
- **COMMODITY/non_crypto_consensus** n=836 WR=59.0% avg+0.79%
- **FOREX/non_crypto_consensus** n=102 WR=58.8% avg+0.18%

---

## Remaining Action Items (in priority order)

### P0 — Block structural losers (immediate)
1. **Block `multi_asset_cot` for COMMODITY**: WR=17% on 223 closed, dominating 91 OPEN commodity picks. Add category filter or WR-fail-safe in emit path.
2. **Block `regime_terminal` from EQUITY** or isolate its regime_mild_bull sub-strategy: parent is n=17 WR=17.6% PF=0.19 but regime_mild_bull is n=24 WR=58.3% (suspect contamination).
3. **Investigate `forex_copy_trader`**: forex_rsi2_mean_reversion shows 50/50 TP_HIT vs LOST split (closed-pairs artifact).

### P0 — Wire orphan emitters (immediate)
4. **forex_carry_momentum → trading_picks INSERT**: `tools/feature_signals/forex_carry_momentum.py` emits 4 picks today to JSON only. Add INSERT loop to write source_system='forex_carry_momentum' to trading_picks. This unblocks FOREX edge measurement.
5. **Flip commodity_term_cot production_enable=true**: 3 picks in JSON today, blocked. Locate emit path, flip, persist.
6. **Wire funding_rate_arb to audit_sync.py**: emits 10 picks/day to alpha_engine/data/funding_rate_picks.json but never reaches pf_registry. Add to EMITTER_WHITELIST in alpha_engine/isolated_signal_integrator.py:80-110 OR call from audit_sync.py.

### P1 — Enable shadow sleeves (high value, low risk)
7. **Set `PEAD_EQUITY_ENABLED=1`** in alpha-engine-live.yml:111: logs live PEAD signals from pead_earnings_cache.json (4 tickers cached, real surprise_pct). Shadow mode.
8. **Enable `FACTOR_EMITTERS_ENABLED=1`** for etf_sector_rotation and bond_duration_momentum sleeves: both already emit production_enable=true payloads but blocked at orchestrator.py:171 gate. Per the ETF+BOND audit this is "without code changes."
9. **Confirm FACTOR_EMITTERS_ENABLED is actually enabling emission** — the CRYPTO audit says it's set in feature-signals-hourly.yml but sleeves still show n=0 closed. Investigate the orchestrator gate.

### P1 — Earnings/fundamental integration
10. **Populate earnings_calendar.json** via daily GHA cron (Mon-Fri 06:00 UTC): `EarningsCalendarFetcher().fetch_batch()` on S&P 100 → alpha_engine/data/earnings_calendar.json. Currently empty.
11. **Refresh ipo_calendar.json**: replace 2023-2024 manual list with 2024-2025 IPOs from NASDAQ/Finnhub. ipo_post_listing_winner is dead without it.
12. **Fix value_screener_runner universe** (alpha_engine/value_screener_runner.py:330): emits n=1 from n_universe=1 — market_cap_provider failing for 50/52 tickers. Trace and re-emit.

### P1 — Source diversity (long-term, requires code)
13. **Multi-source replication for antigravity_strategies**: the 3 high-PF rows (CRYPTO/ETF/FUTURES) all come from one source. Wire a 2nd independent emitter per class (e.g., equity_momentum_quality for EQUITY, commodity_term_cot for COMMODITY, basis_strategies for FUTURES).
14. **Decompose non_crypto_consensus**: 14+ sub-strategies contribute to WR=59% on n=836. Run attribution to find which sub-strategies carry the alpha.

### P2 — Data quality / hygiene
15. **Re-enable analyst scraper**: leaderboard.json is 10d stale, is_known_analyst=0 for all 222 entries. Without named analyst picks we cannot break single-source risk on CRYPTO via external signal.
16. **Replace ^TNX with 3M OIS** in forex_carry_momentum: flagged low_proxy_trend in data_caveats; disqualifies from money-ready.
17. **Classify low_volatility_factor** correctly: 18/26 picks are QQQ/SPY (ETF-proxy), only 8 are pure stock (AAPL/JNJ). Inflates EQUITY count with ETF.
18. **Investigate FUTURES resolver**: TIME_EXIT on multi_asset_scanner → "zombie" WR 6.7% PF 0.07. Real edge (PF 5.26) excluded by policy-clean filter.

### P3 — Dashboard surfacing
19. **Build per-asset-class money-ready panel** at /audit (and /audit/ai-tournament.html): show the 3-5 best picks per class with 5-axis verdict (concentration, fat-tail, OOS, batch, binomial), source-diversity flag, recency.
20. **Surface SINGLE-source flag** in /audit UI for every PF>1 row. Currently buried in pf_registry.json::is_single_source_artifact.

### P3 — Operator decisions (human approval required)
21. **mega_mutation unblock**: HOLD per swarm. Re-check ~2026-06-12-16 (sign coherence clean + 1 live signal fires cleanly).
22. **Walk-forward promotion for etf_dual_momentum**: lab OOS PF 2.746 n=11 PASS but forward n=0. Decide whether to paper-trade.
23. **falsified edge re-emergence guard**: cot_paper_pilot was TIER_1_RENAISSANCE on over-emission; same dedup-by-release-week audit must run on multi_asset_cot.

---

## Top 5 Things to Wire TODAY (highest ROI, lowest risk)

1. **Block multi_asset_cot for COMMODITY** — bleeding 91 OPEN picks, WR=17%
2. **Wire forex_carry_momentum JSON → trading_picks** — 4 fresh picks today
3. **Set PEAD_EQUITY_ENABLED=1** — earnings data is cached, no risk to enable
4. **Enable FACTOR_EMITTERS_ENABLED shadow sleeves** — already production_enable=true, blocked at gate
5. **Fix value_screener_runner universe** — currently emitting n=1 from 52-ticker universe

Each is ≤2 lines of code, deploys in next workflow run.

---

## What Real-Money Picks Will Require (per CLAUDE.md charter)

Per `docs/PERFORMANCE_CHARTER.md` T2 floor: PF≥1.5 + WR≥50% + MDD≤20% + n≥100. To get a class to MONEY_READY we need:
- (a) **At least 2 independent sources** for the strategy (kills single-source artifact risk)
- (b) **Multi-window OOS validation** (e.g., 60/40 walk-forward)
- (c) **Recency check** (recency gate now wired at 14d/48h per commit 030efe8d3e)
- (d) **Bootstrap 95% CI** on net expectancy (lower bound >0)
- (e) **No concentration** (HHI<30%, single source <50%)
- (f) **No batch artifact** (single date <35% of n)
- (g) **Sign coherence** (status=payout sign matches pnl sign, 0 flips)

The recency gate (e), single-source flag (b), and sign coherence (g) are wired. CI (d) is computed in shadow mode. Walk-forward harness (b) needs implementation. Source diversity (a) needs the wire-ups above.

**Realistic ETA to first MONEY_READY class: 4-6 weeks** if we:
- (this week) Block losers, wire orphans, enable PEAD/FACTOR_EMITTERS shadow
- (next 2 weeks) Run multi-source replication on top 3 classes
- (weeks 3-4) Walk-forward + bootstrap CI on replicated strategies
- (weeks 5-6) First MONEY_READY class emerges with 100+ n from ≥2 sources

Cannot shortcut this without compromising charter. The 2026-06-02 mega_mutation incident (141 sign-flipped rows) is exactly the failure mode that skipping the multi-source replication would repeat.
