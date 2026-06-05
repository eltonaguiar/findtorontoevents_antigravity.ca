# Zero-PnL Data Pipeline Audit — 2026-06-05

**Verdict on Grok's 69% claim: SLIGHTLY LOW for `at_pick_outcomes`, HIGH for `trading_picks`.**

## Headline numbers (live `ejaguiar1_stocks`)

| Table | Resolved rows | pnl=0 OR NULL | Share |
|---|---|---|---|
| `at_pick_outcomes` | 38,384 | 28,218 | **73.5%** |
| `trading_picks` | 8,590 | 1,590 | **18.5%** |

Grok's "69%" sits between the two; closest to `at_pick_outcomes` (73.5%, +4.5pp).

## 1. Where the zeros live (status × pnl)

`at_pick_outcomes`: **100% of the 28,218 zero rows are status=EXPIRED** (97.7% of all EXPIRED). WON and LOST rows have zero pnl=0. Resolution_method = `TIME_EXPIRED` for every single one.

This is **NOT the regime_mild_bear bug** (WON+zero double-count). It is a different pathology: the time-expiry resolver writes `pnl_pct=0` instead of computing the actual close-vs-entry mark. These rows are then either ignored (good) or counted as flat trades dragging PF toward 1.0 (bad).

`trading_picks`: the regime_mild_bear bug IS present — **375 TP_HIT rows have pnl=0** (10.6% of TP_HIT). Plus 250 `FORCE_CLOSED_TOXIC` are 100% zero (expected — kill switch).

## 2. Per asset_class (at_pick_outcomes zero-pnl share)

FUTURES 98.4% · INDEX 99.0% · BOND 89.1% · COMMODITY 84.9% · FOREX 83.7% · ETF 83.1% · EQUITY 79.5% · CRYPTO 56.5% · MEME 25.0% · STOCK 12.1%

CRYPTO is the least-broken class but still 56.5% zero. Non-crypto classes are nearly entirely zero-resolved.

## 3. Per resolver_version (concentration test — YES, concentrated)

| Resolver | n | zero% |
|---|---|---|
| `backfill_widened_202…` | 24,938 | **81.2%** |
| `backfill_updated_202…` | 7,879 | **96.6%** |
| `backfill_2026-06-01` | 3,264 | 5.2% |
| `universal_v2` | 1,933 | 10.1% |
| `signflip_purge_20260…` | 367 | 0.0% |

**Bug is concentrated in the two `backfill_widened/updated` resolvers (32,817 rows, 85.0% combined zero share).** Newer resolvers (`backfill_2026-06-01`, `universal_v2`, `signflip_purge`) are clean (<10% zero). Re-running the bad cohort through `backfill_2026-06-01` would drop the global zero share from 73.5% to ~7%.

## 4. Top dragger strategies (n≥20, 100% zero-pnl) — quarantine candidates

`copy_pm_comtruise` (555), `copy_pm_justdance` (458), `pm_momentum_detector` (401), `pm_whale_0xa2f1fe` (281), `pm_whale_0xcc500c` (249), `pm_whale_0xde17f7` (144), `copy_pm_elpolloloco` (130), `copy_pm_pm_6e1d5040` (107), `pm_whale_0x6e1d50` (95), `pm_whale_0x6916cc` (87). All Polymarket copy/whale strategies — resolver has no price feed for these → writes zero.

Also: `stocks_rsi2_pullback_aggressive` (51), `leveraged_etf_decay` (43).

## 5. WON × zero-pnl inconsistency check

- `at_pick_outcomes`: **0 WON rows have pnl=0** (status integrity clean here).
- `trading_picks`: **375 TP_HIT rows with pnl=0** — confirmed regime_mild_bear pattern in this table; dashboard PF computed off `trading_picks` will overcount wins.

## Recommended actions

1. Re-resolve the 32,817 `backfill_widened/updated` rows via `backfill_2026-06-01` resolver.
2. Quarantine the 15 Polymarket `pm_*` / `copy_pm_*` strategies (no price feed → unresolvable) in `BLOCKED_SOURCE_SYSTEMS`.
3. Patch trading_picks: reclassify the 375 TP_HIT+pnl=0 rows as EXPIRED or recompute pnl from `closed_at` × symbol price.
