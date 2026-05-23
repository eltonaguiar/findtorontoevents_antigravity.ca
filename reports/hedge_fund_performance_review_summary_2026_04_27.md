# Hedge-Fund-Grade Performance Review — Per Asset Class — 2026-04-27

**Author:** claude-opus-4-7 (consolidated review)
**Sources:** `reports/asset_class_independent_recompute_2026_04_27.md` (canonical numbers, 5-peer reconciled) + per-class source-system breakdown from `audit_trail/data/dashboard_payload.json` (fresh 22:08:21Z payload).
**Companion:** `reports/hedge_fund_performance_review_detailed_2026_04_27.md` (deep per-class analysis).

## TL;DR

| Class | n | PF | Real edge? | Verdict | Headline action |
|---|---:|---:|---|---|---|
| **EQUITY** | 381 | 1.385 | YES (clean wins 87% of wins, +245% from `kimi_riseoftheclaw` alone) | Tier 2 — only investable class | **Scale.** Ramp size on the 2 winning sources, kill `goldmine_stocks` + `fast_stocks_competition` (both 0% WR, -75% sum). |
| **CRYPTO** | 1,598 | 1.140 | YES but MDD 178% | Below Tier 3 — edge real, drawdown lethal | **Cap & filter.** Kill 4 zombie sources, reverse-bias the 6 confirmed poison-pill symbols, vol-target the survivors. |
| **ETF** | 83 | 1.220 | Likely yes (clean-win share 80%+) | Tier 3 borderline (n<100) | **Grow data.** Add 1-2 more ETF-specialist sources before sizing decisions. |
| **FOREX** | 794 | 1.349 | **NO — 63% of wins are 1bp resolver flicker** | Cannot evaluate | **Block.** No FOREX verdict possible until `outcome_resolver.py:384-405` patched (Workstream B). |
| **COMMODITY** | 622 | 0.896 | **NO — 67% of wins are 1bp resolver flicker, AND `cta_replicator` has 1 clean win on n=105** | Likely zero edge | **Suspend.** Block COMMODITY emissions pending resolver fix; the underlying alpha appears absent on top of the resolver bug. |
| **BOND** | 17 | 1.601 | Insufficient | Skip | **Add data sources** before any framework decision. |

## The macro picture

Of 3,500 closed picks across 6 asset classes, **only EQUITY clears Tier 2 with real edge**. CRYPTO has edge but a survival-threatening drawdown. The four other classes are either too small (BOND, ETF) or contaminated by a resolver bug that converts 1bp moves into "wins" (FOREX, COMMODITY). The hedge-fund-grade move is to *concentrate where the edge is real* and *fix the data layer* before scaling anywhere else.

## What pro hedge funds do that we don't

1. **Vol-targeting at portfolio + per-class level.** Renaissance/Two Sigma/AQR run constant-vol exposure (10-15% annualized). We have no vol-targeting layer; CRYPTO MDD 178% is the proof.
2. **Per-class capital allocation by Sharpe, not WR.** EQUITY Sharpe (per-trade) 0.1265 is 2.7× CRYPTO's 0.0465. A risk-parity allocator would put ~70% of risk budget on EQUITY today; we don't have one.
3. **Resolver / settlement integrity SLAs.** Every prop shop has an end-of-day reconciler that flags unresolved positions; ours treats live yfinance spot as fill price for non-crypto, which is the source of the FOREX/COMMODITY contamination.
4. **Regime overlays.** Bridgewater All-Weather, AQR Style Premia — both rotate exposure based on macro regime. Our `regime_terminal` exists (n=19 CRYPTO, n=2 FOREX, n=3 UNKNOWN) but isn't gating sizing.
5. **External alpha sourcing for weak classes.** When internal strategies don't have an edge in a class, hedge funds buy it: AQR licenses commodity-CTA factors, BlackRock licenses fixed-income data from PIMCO. We already have `multi_asset_copytrader` infrastructure (n=1,037 non-crypto picks) — but it's our largest source AND our largest noise generator. Wrong external alpha is worse than none.

## Class-by-class one-liner

- **EQUITY** — the franchise. Double down on `kimi_riseoftheclaw` (+245.8% sum on n=166) and `stocks_competition` (+90.3% on n=133). Two zombies to kill.
- **CRYPTO** — keep `luxalgo_filters` (+63.1% on n=181) and `claude_gainer_st` (+36.6% on n=256); kill `quan_engine` (0% WR), `dna_rapid_fire_mutations` (25% WR), `mercury2` (27% WR), `rapid_fire` (-52.8% sum); vol-target the remainder.
- **ETF** — `kimi_riseoftheclaw` doing 95% of the n. Add 2 ETF-specialist sources (sector rotation, low-vol factor) before sizing.
- **FOREX** — block all verdicts; G10 carry trade and dollar-block momentum are the industry-standard FX playbook to add *after* the resolver bug is fixed.
- **COMMODITY** — block all verdicts; CTA term-structure (Winton/AHL playbook) and seasonal patterns are the standard plays once the resolver is fixed AND a real signal source is found.
- **BOND** — skip until either internal alpha grows or external rates strategy is added (BlackRock/PIMCO-style duration management).

## Recommended copy traders / external alpha sources

Only suggested for classes with insufficient internal edge. Due-diligence required before any wire-up — the existing `multi_asset_copytrader` shows that "copy a leader" can amplify noise as easily as alpha.

| Class | Why external | Industry-standard sources to evaluate |
|---|---|---|
| FOREX (post-resolver-fix) | Internal sources are mostly noise; pro FX is broker-edge dependent | **Darwinex** (regulated copy + DARWIN factor scoring), **eToro CopyTrader** (largest pool, retail-skewed), **ZuluTrade** (verified track records ≥3y), **Myfxbook** AutoTrade (audited equity curves) |
| COMMODITY (post-resolver-fix) | No internal edge once noise filtered | **Striker Securities** (managed futures marketplace), **AlgoTrader** marketplace (CTA strategies), **iSystems** (TradeStation futures portfolios) |
| BOND | n=17, no internal infrastructure | **PIMCO StocksPLUS** style (pre-baked factor portfolios via ETF wrappers — BIL, SHV), **Vanguard Bond Index** as benchmark beta |
| ETF (augment) | Single-source concentration risk | **State Street Sector SPDR rotation** (free signals), **Research Affiliates RAFI** (fundamental factor index licenses) |

## Sequencing

1. **This week (P0 / blocking):** Workstream B resolver fix → re-resolve historical FOREX/COMMODITY. Without this, no non-crypto decision is data-supported.
2. **This week (P0 / non-blocking):** Workstream A ML pipeline fixes (silent-failure, gatekeeper persistence, self_improvement.py path).
3. **Next:** EQUITY scale-up (size up `kimi_riseoftheclaw` + `stocks_competition`, kill 2 zombies).
4. **Next:** CRYPTO MDD reduction (Workstream C — kill 6 poison pills, vol-target survivors, kill 4 zombie source-systems identified in detailed doc).
5. **Then:** External alpha evaluation for FOREX/COMMODITY/BOND (only after resolver fix proves internal sources have/don't have edge).

See `reports/hedge_fund_performance_review_detailed_2026_04_27.md` for per-class strategy inventory, gap analysis, and industry-playbook detail.
