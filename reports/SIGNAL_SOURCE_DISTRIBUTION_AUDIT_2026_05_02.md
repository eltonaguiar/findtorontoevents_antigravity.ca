# Signal-Source Distribution Audit (MIMO P1)

**Date:** 2026-05-02
**Closed picks scored:** 7,445 (skipped 0 — all carried numeric `pnl_pct`)
**Active picks (context only — not in PF math):** 143
**Bucket coverage (non-OTHER share of closed picks):** 19.5%

## Methodology

Closed picks were classified into MIMO source-type buckets via case-insensitive substring heuristics on `source_system` + `strategy`. Rules are evaluated in priority order — `COPY_TRADING > ML_PRICE_ONLY > TA_INDICATORS > FUNDING_RATE > SENTIMENT > CROSS_ASSET` — so a `multi_asset_copytrader` row lands in `COPY_TRADING`, not `CROSS_ASSET`. Heuristic risk: any `source_system`/`strategy` whose names don't contain one of the listed keywords falls into `OTHER`. **`OTHER` is huge here (5,994 / 7,445 = 80.5%)** because the dominant `source_system` `quan_engine` (5,896 picks, 79.2% of the dataset) is not in MIMO's taxonomy. Profit factor (PF) is `sum(wins) / abs(sum(losses))` on the raw `pnl_pct` field (a fractional return, not %). Win = `pnl_pct > 0`. Active picks are reported as context only — their `pnl_pct` is mark-to-market and is not included in PF / WR. Read-only audit; no production code modified, no blocklist changes.

## Overall bucket breakdown (sorted by sum PnL DESC)

| Bucket | n | WR % | Avg pnl_pct | Sum pnl_pct | PF |
|---|---:|---:|---:|---:|---:|
| CROSS_ASSET    |    41 | 85.37 | +0.03526  |    +1.4458 | 8.029 |
| SENTIMENT      |     1 | 100.00 | +0.03000 |    +0.0300 | inf |
| COPY_TRADING   |   496 | 29.03 | -0.00120  |    -0.5967 | 0.800 |
| TA_INDICATORS  |   135 | 37.78 | -0.11011  |   -14.8653 | 0.355 |
| ML_PRICE_ONLY  |   778 | 52.57 | -0.01989  |   -15.4727 | 0.643 |
| OTHER          | 5,994 | 30.20 | -0.17128  | -1,026.6030 | 0.404 |

**Edge-positive buckets at n>=50:** none after `OTHER` is excluded; only `CROSS_ASSET` (n=41) clears PF>=1.0 and it falls below the n>=50 sample gate.

## Per-asset-class bucket breakdown (top 4 buckets by n per class)

### COMMODITY

| Bucket | n | WR % | Avg pnl_pct | Sum pnl_pct | PF |
|---|---:|---:|---:|---:|---:|
| CROSS_ASSET  | 41 | 85.37 | +0.03526 | +1.4458 | 8.029 |
| COPY_TRADING | 33 | 78.79 | +0.03232 | +1.0667 | 5.792 |

### CRYPTO

| Bucket | n | WR % | Avg pnl_pct | Sum pnl_pct | PF |
|---|---:|---:|---:|---:|---:|
| OTHER     | 2 | 0.00 | -0.02000 | -0.0400 | 0.000 |
| SENTIMENT | 1 | 100.00 | +0.03000 | +0.0300 | inf |

> Only 3 closed CRYPTO picks reach the resolver — extremely low coverage given the repo's CRYPTO emphasis. Either CRYPTO `source_system` strings are being routed to `UNKNOWN` asset_class (see below), or the resolver is dropping them.

### EQUITY

| Bucket | n | WR % | Avg pnl_pct | Sum pnl_pct | PF |
|---|---:|---:|---:|---:|---:|
| COPY_TRADING  | 26 | 42.31 | +0.00351 | +0.0913 | 1.203 |
| TA_INDICATORS |  2 |  0.00 | -0.01704 | -0.0341 | 0.000 |

### FOREX

| Bucket | n | WR % | Avg pnl_pct | Sum pnl_pct | PF |
|---|---:|---:|---:|---:|---:|
| COPY_TRADING  | 405 | 26.17 | -0.00215 | -0.8726 | 0.372 |
| OTHER         |  14 | 42.86 | +0.00038 | +0.0053 | 1.208 |
| TA_INDICATORS |   3 | 100.00 | +0.00500 | +0.0150 | inf |

### FUTURES

| Bucket | n | WR % | Avg pnl_pct | Sum pnl_pct | PF |
|---|---:|---:|---:|---:|---:|
| COPY_TRADING | 31 | 0.00 | -0.02959 | -0.9171 | 0.000 |

### STOCKS

| Bucket | n | WR % | Avg pnl_pct | Sum pnl_pct | PF |
|---|---:|---:|---:|---:|---:|
| OTHER | 1 | 0.00 | -0.04490 | -0.0449 | 0.000 |

### UNKNOWN (the 80% bulk — almost entirely `quan_engine`)

| Bucket | n | WR % | Avg pnl_pct | Sum pnl_pct | PF |
|---|---:|---:|---:|---:|---:|
| OTHER         | 5,977 | 30.18 | -0.17175 | -1,026.5234 | 0.404 |
| ML_PRICE_ONLY |   778 | 52.57 | -0.01989 |    -15.4727 | 0.643 |
| TA_INDICATORS |   130 | 36.92 | -0.11420 |    -14.8462 | 0.355 |
| COPY_TRADING  |     1 | 100.00 | +0.03500 |    +0.0350 | inf |

> The `UNKNOWN` asset_class accounting for 7,000+ rows of `quan_engine` is itself a finding — these picks bypass MIMO's per-class signal-quality framework entirely because they have no class tag.

## Operator summary

**Where edge actually lives in this repo's data.** With n>=50 as the sample-quality gate, **no MIMO bucket clears PF=1.0**. The only edge-positive group is `CROSS_ASSET` (PF 8.03, WR 85%, n=41) — exclusively the `multi_asset_cot` source on COMMODITY — but its n is below the 50-trade gate. The top-3 by realized sum PnL are `CROSS_ASSET` (+1.45), `SENTIMENT` (+0.03, n=1, ignore), and `COPY_TRADING` (-0.60, less bad than the rest). The bottom-3 are `OTHER` (-1,026.6, almost all `quan_engine`), `ML_PRICE_ONLY` (-15.47), and `TA_INDICATORS` (-14.87, almost entirely `rapid_fire/volume_spike_breakout`). Note that even MIMO's predicted MEDIUM-HIGH category `FUNDING_RATE` has **zero** matched rows in this dataset — either we have no funding-rate strategy live, or its `source_system` string doesn't contain "funding"/"basis"/"perp_spot" (worth verifying separately).

**MIMO predictions vs empirics.** MIMO's "LOW = retail copy-trading" prediction matches: `multi_asset_copytrader` is PF 0.81 / WR 25.2% on 412 picks — losing money but only mildly, and on COMMODITY+EQUITY it actually wins (PF 5.79 / 1.20). MIMO's "LOW = pure TA" prediction is sharply confirmed: `rapid_fire/volume_spike_breakout` is PF 0.35 / WR 36.4% on 129 picks. MIMO's "LOW-MEDIUM = ML on price alone" is also confirmed — the ML_PRICE_ONLY bucket is PF 0.64 on 778 picks, though WR is a deceptive 52.6% (small wins, large losses). The biggest MIMO **miss** is the 80% of the book it does not classify at all: `quan_engine` (PF 0.40, -995 sum_pnl, 5,896 picks) is the dominant alpha drain and falls outside MIMO's taxonomy entirely. MIMO's predicted edge buckets (`FUNDING_RATE`, `SENTIMENT`, `CROSS_ASSET`) are essentially absent from realized data: 0 + 1 + 41 picks combined. Either we are not deploying these signal types at scale, or our per-class WR/PF measurement is missing them due to source-name mismatch — which is itself the action item.

## Demote candidate `source_system` list (PF<1.0, n>=50)

Per-bucket per-source rollup. Both gates required.

| Bucket | source_system | n | WR % | Sum pnl_pct | PF |
|---|---|---:|---:|---:|---:|
| OTHER          | `quan_engine`            | 5,896 | 30.38 | -995.6135 | 0.411 |
| OTHER          | `rapid_fire`             |    78 | 16.67 |  -30.8749 | 0.014 |
| ML_PRICE_ONLY  | `unknown`                |   778 | 52.57 |  -15.4727 | 0.643 |
| TA_INDICATORS  | `rapid_fire`             |   129 | 36.43 |  -14.8566 | 0.354 |
| COPY_TRADING   | `multi_asset_copytrader` |   412 | 25.24 |   -0.6047 | 0.787 |
| COPY_TRADING   | `cta_replicator`         |    83 | 46.99 |   -0.0270 | 0.812 |

**Total demote candidates:** 6 distinct `source_system` strings (5 unique — `rapid_fire` appears in two buckets via different strategy names).

Notes:
- `quan_engine` is the dominant loss-maker but is also 79% of the dataset; **before any demotion, confirm whether `quan_engine` is paper-only / sandbox or actually fills real-money accounts** — its sheer volume suggests synthetic/scan output rather than executed picks. (Cross-check with `audit_trail/quality_gates.py` and the `BLOCKED_SOURCE_SYSTEMS` list per `STRATEGY_INVESTIGATION_BEFORE_KILL.md`.)
- `rapid_fire/volume_spike_breakout` (TA bucket) has WR 36% / PF 0.35 — clean demote signal, low ambiguity.
- `multi_asset_copytrader` (COPY bucket) is PF 0.79 system-wide but PF 5.79 on COMMODITY and PF 1.20 on EQUITY — **kill at the asset-class level, not system-wide**: drop FOREX (PF 0.37 on 324 picks) and FUTURES (PF 0.00 on 31 picks) only.
- The `ML_PRICE_ONLY/unknown` row is suspicious — all 778 picks have `source_system='unknown'` and a strategy name containing one of the ML keywords. Investigate the upstream tagger before acting; this could be a labeling bug masking the real source.

## Followups (not actioned in this read-only audit)

1. Verify the 5,896 `quan_engine` rows are real fills vs. scanner output before any blocklist action.
2. Check why all 778 `ML_PRICE_ONLY` picks have `source_system='unknown'` — likely upstream tagger gap.
3. CRYPTO has only 3 closed picks reaching the resolver despite being a Tier-2 candidate per `CLAUDE.md` Goal #1 — likely the same `outcome_resolver.py` issue noted in `feedback_noncrypto_resolver_live_close_bug.md` is also dropping CRYPTO classification.
4. Re-grep `source_system` strings for any funding-rate / basis-trade signal — current rule set found zero, but `funding_rate_carry` is named in MIMO's matrix so it should exist somewhere.

---

_Heuristic-based bucketing audit — `OTHER` bucket size (80.5%) is the upper bound on misclassification noise. Source data: `alpha_engine/data/closed_picks.json` (7,445 rows) and `alpha_engine/data/active_picks.json` (143 rows)._
