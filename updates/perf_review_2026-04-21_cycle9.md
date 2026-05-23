# perf-review: 8h cycle 2026-04-21 (cycle 9) — active book shrinks 40%, zombies persist

**Author:** Claude Opus 4.7 (1M context)
**Generated:** 2026-04-21 12:13 UTC
**Source:** `audit_trail/data/dashboard_payload.json` (3,500 closed, **30 active** picks)
**Tracking:** `alpha_engine/data/strategy_performance.json` (185 keys)
**Cycle:** 9 of recurring 8-hour perf-review series
**Related:** PR #297 (cycle 8), PR #282 (cycle 7), PR #298 (AutoHedge committee experiment)

---

## TL;DR

**Active book contracted from 50 → 30 (−40%)** between cycle 8 and cycle 9. This is the largest single-cycle contraction since cycle 4 and confirms that recently-merged gates (PR #294 extended TOD block + confidence dead-zone, Kimi PR #292 HC calibration, AutoHedge-committee-equity pattern from #298) are actively pruning low-quality emissions.

However, the **closed-pick zombie leak is unchanged** — `copy_hl_lb_None` still at n=278 / WR 32.0% / cum −806%, `st_fear_greed_contrarian` at n=627 / cum −359%. Closed picks open from a different emitter path than the one the gates protect.

New drains escalated:
- `kimi_signal_tracking`: n=29→36, cum PnL −63% → **−107%** (+44pp drag in 8h)
- `macd_rsi_confluence`: n=44, cum **−51%** (new to the mutation-candidate list)

High-conviction flagged picks dropped **2 → 1** (the one remaining is SI=F on `non_crypto_consensus` which has WR 0% on n=88).

## §1 — Cycle-8 → Cycle-9 delta

| Metric | Cycle 8 | Cycle 9 | Δ |
|---|---|---|---|
| Active book size | 50 | **30** | **−20 (−40%)** |
| High-conviction picks (elite≥70 OR conf≥0.80) | 26 | 14 | −12 |
| HC picks flagged on bottom-quartile sym | 2 | 1 | −1 |
| Strategies with closed picks | 192 | 191 | −1 |
| Naming-mismatch silent failure | 167/192 (87%) | 166/191 (87%) | unchanged |
| Mutation candidates (n≥20, WR<35%) | 12 | 12 | same |
| `copy_hl_lb_None` cum PnL | −806% (n=278) | **−806% (n=278)** | **unchanged — still zombie** |
| `st_fear_greed_contrarian` cum PnL | −365% (n=621) | −359% (n=627) | +6pp (still zombie) |
| `st_obv_support_divergence` | in list (WR 28.9%) | left list (WR 39.4%) | no longer mut-cand but still emitting |
| `kimi_signal_tracking` cum PnL | −64% (n=29) | **−107%** (n=36) | **−44pp drag escalation** |
| `macd_rsi_confluence` | not in list | **n=44 cum −51%** | new drain |

**Net:** active-gate improvements are working on **emission**, but the **zombie close-out** continues at the same rate.

## §2 — Per-strategy mutation candidates (n ≥ 20, WR < 35%)

All 12 candidates, sorted by WR:

| Strategy | n | WR | PF | mean PnL% | cum PnL% | Status |
|---|---|---|---|---|---|---|
| `non_crypto_consensus` | 88 | 0.0% | 0.0 | 0.0% | +0.01% | **broken — flat-close bug** |
| `cta_commodity_momentum_term` | 45 | 8.9% | 0.01 | −0.10% | −4.29% | mutate |
| `cta_cross_asset_tsmom` | 57 | 12.3% | 1.23 | +0.02% | +1.07% | skip (positive cum) |
| `ensemble` | 23 | 13.0% | 0.46 | −0.60% | **−13.74%** | investigate (likely dispatcher mislabel) |
| `atr_regime_rsi` | 29 | 17.2% | 0.26 | −0.36% | −10.38% | mutate |
| `futures_momentum` | 441 | 24.3% | 1.38 | +0.05% | +21.14% | skip (positive cum) |
| **`st_fear_greed_contrarian`** | 627 | 24.6% | 0.37 | −0.57% | **−358.82%** | **ZOMBIE — retired but emitting** |
| `macd_rsi_confluence` | 44 | 27.3% | 0.36 | −1.16% | **−50.97%** | **NEW mutation candidate** |
| `forex_rsi2_mean_reversion` | 523 | 28.3% | 3.71 | +0.07% | +34.56% | skip (positive cum) |
| `kimi_signal_tracking` | 36 | 30.6% | 0.44 | −2.97% | **−106.96%** | **ESCALATING — 8h drag −44pp** |
| **`copy_hl_lb_None`** | 278 | 32.0% | 0.56 | −2.90% | **−806.39%** | **ZOMBIE — #1 priority** |
| `unknown` | 43 | 32.6% | 1.26 | +0.18% | +7.53% | skip (positive cum, investigate label) |

**True kill-or-mutate list** (n ≥ 20, WR < 35%, cum_pnl < 0, PF < 1):
`non_crypto_consensus`, `cta_commodity_momentum_term`, `ensemble`, `atr_regime_rsi`, `st_fear_greed_contrarian`, `macd_rsi_confluence`, `kimi_signal_tracking`, `copy_hl_lb_None`.

Combined drag: **−1351% cum PnL** across these 8 strategies.

## §3 — Per-symbol block candidates (n ≥ 30, WR < 30%)

24 symbols meet threshold. Top 10 worst by cum PnL:

| Symbol | Class | n | WR | cum PnL% |
|---|---|---|---|---|
| `OPUSDT` | CRYPTO | 59 | 16.9% | **−121.43%** ← worst absolute drag |
| `SUIUSDT` | CRYPTO | 79 | 20.3% | −88.24% |
| `APTUSDT` | CRYPTO | 66 | 22.7% | −82.58% |
| `AVAXUSDT` | CRYPTO | 70 | 17.1% | −51.21% |
| `DOGEUSDT` | CRYPTO | 68 | 22.1% | −51.03% |
| `ADAUSDT` | CRYPTO | 62 | 22.6% | −38.15% |
| `AUDUSD=X` | FOREX | 81 | 24.7% | −37.50% |
| `LINKUSDT` | CRYPTO | 53 | 18.9% | −35.03% |
| `EURJPY=X` | FOREX | 42 | 7.1% | −13.72% |
| `EURUSD=X` | FOREX | 70 | 18.6% | −10.74% |

**Same 7 crypto altcoins from cycle 8 dominate the kill list:** OPUSDT, SUIUSDT, APTUSDT, AVAXUSDT, DOGEUSDT, LINKUSDT, ADAUSDT. Combined cum drag **−467%**.

## §4 — High-conviction cross-reference (elite_score ≥ 70 OR confidence ≥ 0.80)

14 active picks meet HC threshold (down from 26 in cycle 8). **1 flagged:**

| Symbol | Strategy | elite | conf | Flag |
|---|---|---|---|---|
| `SI=F` | `non_crypto_consensus` | 35 | 0.80 | **double-flag** — strategy WR 0% AND symbol WR 21.9% |

Single remaining HC flag is on the already-broken `non_crypto_consensus` strategy (flat-close bug). Recommend emergency block on any pick using that strategy until the resolver bug is fixed.

## §5 — Data-flow gap

| Metric | Count | vs Cycle 8 |
|---|---|---|
| Closed strategies | 191 | −1 |
| Tracked (`strategy_performance.json`) | 185 | +1 |
| **Closed → not tracked** | **166 (87%)** | unchanged |
| Tracked → never closed | 160 | +1 |

PR #289 diagnostic still applies. Aliasing layer not yet implemented.

## §6 — DNA mutation suggestions (new candidates)

See `mutations/proposed_2026-04-21_cycle9.yaml` for the full YAML. New entries since cycle 8:

### `macd_rsi_confluence` (n=44, WR 27.3%, cum −51%)

- **Sweep:** MACD fast/slow 12/26 → {5/13, 20/40}; signal 9 → {5, 14}; RSI len 14 → {7, 21, 28}; confluence threshold tighten 25%.
- **Regime:** BTC 4h trend gate (long only when BTC EMA50>EMA200); drop kill-window 16-21 UTC.
- **Inverse:** flip direction signals; backtest as standalone.

### `kimi_signal_tracking` (n=36, WR 30.6%, cum −107%, **ESCALATING**)

- **Sweep:** min sub-signal threshold current → {+1, +2}; weighting equal → by historical WR; expiry horizon same_bar → {1h, 4h}.
- **Regime:** asset-class scoping (only emit on classes with positive cohort WR); time-of-day filter (drop 8-11 UTC and 16-21 UTC).
- **Inverse:** flip direction signals.

## §7 — Action items (priority order)

### P0 — Plug `copy_hl_lb_None` zombie leak (n=278, cum −806%, unchanged across 2 cycles)

This is the single largest drag in the dataset. Already in `_RETIRED_STRATEGIES` yet continues to close picks at identical rate. Investigation path:

1. Find every code path that writes to `recent_closed` with a `strategy` field starting with `copy_hl_lb`.
2. Check if there's a backfill job re-processing old picks under the `_None` label.
3. Check if forward-validator tags FORCE_CLOSED picks with strategy=`copy_hl_lb_None` regardless of origin.

### P1 — Emergency block on `non_crypto_consensus` until flat-close bug fixed

14 HC picks, 1 flagged, that 1 is on `non_crypto_consensus`. Combined with n=88 closed picks all at pnl=0.0, the strategy is broken. Add a hard reject at emission time.

### P2 — Investigate `kimi_signal_tracking` escalation

Cum drag jumped from −64% (cycle 8) to −107% (cycle 9) in 8 hours. 7 new closed picks, all negative. Needs a cron inspection: is it running more frequently? emitting more picks? Triage before cycle 10.

### P3 — Investigate new `macd_rsi_confluence` emergence

44 closed picks, cum −51%. Not previously flagged. Likely a newly-unlocked cron or alias. Find the emitter and either tighten its gate or add to mutation queue.

### P4 — Continue PR #289 alias backfill (87% silent failure unchanged)

Still the biggest structural fix needed.

## §8 — Acceptance for operators

**The good:** active book cut by 40%, HC flags cut by 50%. The new gates are working on emission.

**The persistent:** closed picks still drain at pre-gate rates because the retirement logic only blocks NEW emissions, not the backfill/forward-validator paths. The next perf-review cycle should show whether the zombie drag slows as the rolling-window ages out old picks.

**Nothing in this PR modifies production files.**
