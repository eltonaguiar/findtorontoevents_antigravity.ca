# Quarantine Diff Proposal — Grok recommendations vs Live DB (2026-06-05)

Source of truth: `ejaguiar1_stocks.trading_picks`, queried 2026-06-05 via `tools.db_env.get_stocks_creds()`.

## PART A — ml_crypto_predictor staleness

### Q1 — Last-update timeline

| source_system        | last `created_at`        | last `closed_at`         | total rows |
|----------------------|--------------------------|--------------------------|------------|
| `ml_crypto_predictor`| 2026-06-05 03:32:04      | 2026-05-25 15:49:43      | 1,896      |
| `ml_crypto_pred`     | 2026-03-29 00:33:20      | 2026-04-20 01:29:40      | 69         |

Local model state: `ml_crypto_predictor/enhanced_models/live_picks/active_picks.json` modified 2026-06-03 14:23 UTC; 29 active picks, top entry `enhanced_ml_A_xgboost` BTCUSDT LONG with `timestamp 2026-05-25T18:54:28Z`. **The on-disk active_picks.json has stale embedded timestamps** while the DB keeps receiving new rows — confirms the `SOURCE_SCORE_AUDIT` stale-score alert.

### Q2 — 90-day forward perf

| source_system        | n_closed | wins | avg_pnl_% | PF    |
|----------------------|---------:|-----:|----------:|------:|
| `ml_crypto_predictor`|      135 |    0 |    -4.257 | 0.000 |
| `ml_crypto_pred`     |        3 |    0 |    -6.274 | 0.000 |

Zero wins on 135 closed picks. Avg PnL -4.26%. Note WR=0 / PF=0 also indicates resolver may be mis-stamping outcomes (consistent with the Tier-0 resolver bug documented in CLAUDE.md), but the **negative avg_pnl is the truth signal** — actual realized PnL is bleeding regardless of the WIN/LOST tag.

### Q3 — Stale-out / emission cadence (last 10 days)

| date       | emit | OPEN | EXPIRED | WON | LOST |
|------------|-----:|-----:|--------:|----:|-----:|
| 2026-06-05 |   29 |   29 |       0 |   0 |    0 |
| 2026-06-04 |   29 |   29 |       0 |   0 |    0 |
| 2026-06-03 |   29 |   29 |       0 |   0 |    0 |
| 2026-06-02 |   29 |    0 |       0 |   0 |    0 |
| 2026-06-01 |   29 |    0 |       0 |   0 |    0 |
| 2026-05-31 |   30 |    0 |       0 |   0 |    0 |
| 2026-05-30 |   29 |    0 |       0 |   0 |    0 |

Status reading: emits **~29 picks/day every day**, but anything older than ~48h is no longer OPEN (closed/expired but with zero WON/LOST → resolver leaves them in non-terminal state). This is the classic "stale-out" pattern: emit → never resolve cleanly → 0 wins.

### Conclusion — Part A

`ml_crypto_predictor` is already in `PERMANENTLY_KILLED_STRATEGIES` (`quality_gates.py:1491`, LONG kill) and `BLOCKED_DIRECTION_TRIPLES` (`:3027`, SHORT kill via `("CRYPTO","ml_crypto_predictor","SHORT")`). **Both directions blocked at the strategy level — but the source system is not in `BLOCKED_SOURCE_SYSTEMS`**, so 29 picks/day still leak through pipelines that admit on `source_system` before consulting strategy/direction gates. Recommend defense-in-depth addition to `BLOCKED_SOURCE_SYSTEMS` (same pattern as `quan_engine_scalp`, `futures_momentum`, `cot_positioning`).

## PART B — Quarantine diff for Grok's named draggers

### Current state (existing blocklists)

- `alpha_engine/config.py:257` — `BLACKLISTED_STRATEGIES` already contains: `kimi_signal_tracking`, `quan_engine_scalp`, `claude_gainer_st`, `binance_smart_money`, `hl_funding_fade`, `rapid_fire`, `ensemble`, `battleground_luxalgo`, `multi_period_rsi_confluence_eth`, `ml_breakout`, `genome_mutations`, `multi_asset_scanner`, `ctar_replicator`, `forex_rsi2_mean_reversion`, `inverse_carry_contrarian`, `carry_trade_momentum`, `forex_carry_momentum`, `forex_carry_ppp`, `myfxbook_retail_contrarian`, `forex_carry_bb_hybrid`.
- `audit_trail/quality_gates.py:1929` — `BLOCKED_SOURCE_SYSTEMS` already contains: `incubator_gainer`, `mercury2_fast`, `stocks_competition`, `fast_stocks_competition`, `ml_bg_system_a/b/c/f`, `ml_crypto_pred_v12`, `crypto_winners`, `ml_bg_ensemble`, `breakout_b_ml`, `kimi_claw_research`, `rocket_scanner`, `copy_trader_highscore`, `goldmine_stocks`, `multi_asset`, `quan_engine_scalp`, `cot_positioning`, `futures_momentum`, `cta_golden_cross_200`, `prediction_market_consensus`.
- `audit_trail/quality_gates.py:2551` — `BLOCKED_ASSET_STRATEGY_PAIRS` already contains the 3 + 9 `crypto_soc_*` baby_strats (`a02-a09_v1` variants + base names), plus FOREX `forex_carry_momentum`, EQUITY `penny_deep_oversold`, EQUITY goldmine_1x-7x_consensus, etc.

### Live-DB scrutiny on Grok's named draggers (90d, closed_picks only)

| Grok-named target          | DB status (90d)                                         | Verdict |
|----------------------------|----------------------------------------------------------|---------|
| `kimi_signal_tracking`     | last activity 2026-03-29; n=0 in 90d window             | **Already in `BLACKLISTED_STRATEGIES` (config.py:262), dormant — no action needed** |
| `crypto_soc_*` baby_strats | last activity 2026-03-27; n=18 all-time on a10_v1 only  | **12 variants already in `BLOCKED_ASSET_STRATEGY_PAIRS` (CRYPTO). Remaining "a05/a06" variants emit 0 picks — no action needed** |
| Penny stocks               | `penny_deep_oversold` already blocked EQUITY; `fractal_decay_penny` n=3 (May 27-Jun 1) PF undefined; `goldmine_stocks` source already blocked | **Already covered** |
| Most FOREX/CRYPTO baby_strats | per 90d losers query: `forex_rsi2_mean_reversion` (n=287/309), `myfxbook_retail_contrarian` (n=145), `ig_contrarian_sentiment` (n=146), `non_crypto_consensus` (n=44) all PF=0 / negative PnL | `forex_rsi2_mean_reversion` and `myfxbook_retail_contrarian` already blacklisted. Remaining leak source = `multi_asset_copytrader` emitting them (already blocked at `(FOREX, multi_asset_copytrader)` pair). **No new action needed.** |

### Newly-uncovered active bleeders (90d, n≥30, PF<1.0)

These were NOT named by Grok but the live DB shows they are actively emitting AND structurally losing — these are the real quarantine candidates:

| source_system            | n   | avg_pnl | last_close   | Action |
|--------------------------|----:|--------:|-------------:|--------|
| `ml_crypto_predictor`    | 135 |  -4.257 | 2026-05-25   | **ADD to BLOCKED_SOURCE_SYSTEMS** (defense-in-depth; LONG+SHORT strategy blocks already exist but source still emits 29/day) |
| `mega_mutation`          | 107 |  -3.141 | 2026-06-04   | **ADD to BLOCKED_SOURCE_SYSTEMS** (active, no existing source-level block; score=15 in `_SOURCE_SYSTEM_SCORES` line 5834 = currently *promoted*) |
| `mercury2`               |  45 | -12.941 | 2026-04-10   | **ADD to BLOCKED_SOURCE_SYSTEMS** (dormant but had been bleeding; defense-in-depth before any restart) |
| `alpha_engine_fast`      | 131 |  -2.599 | 2026-05-25   | Investigate — alpha_engine is a meta-engine; need per-strategy breakdown before blanket block |
| `battleground_luxalgo`   |  33 |  -7.025 | 2026-06-01   | **ADD to BLOCKED_SOURCE_SYSTEMS** (`luxalgo_confluence` strategy already in BLACKLISTED_STRATEGIES via `battleground_luxalgo`, but source emits other strategies too) |

## Concrete diff (apply directly)

### File 1 — `audit_trail/quality_gates.py`

Insert into `BLOCKED_SOURCE_SYSTEMS` (around line 2029, just before the closing `}`):

```python
    # ── 2026-06-05 defense-in-depth additions (Grok-recommended + live DB scrutiny) ──
    # ml_crypto_predictor: LONG already in PERMANENTLY_KILLED_STRATEGIES (line 1491),
    # SHORT already in BLOCKED_DIRECTION_TRIPLES (line 3027). Source still emits
    # ~29 picks/day — 90d perf: n=135 closed / 0% WR / avg PnL -4.26% / PF 0.00.
    # Source-level block closes the leak in pipelines that admit on source_system.
    # Ref: reports/quarantine_diff_proposal_2026-06-05.md
    "ml_crypto_predictor",
    # mega_mutation: 90d n=107 / 0% WR / avg PnL -3.14% / PF 0.00. Currently
    # *promoted* via _SOURCE_SYSTEM_SCORES["mega_mutation"]=15 (line 5834).
    # Active emitter (last close 2026-06-04). No existing source-level block.
    "mega_mutation",
    # mercury2: 90d n=45 / 0% WR / avg PnL -12.94% / PF 0.00. Dormant
    # (last close 2026-04-10) but pre-emptive block before any restart.
    # Distinct from already-blocked mercury2_fast. Score=0 already (line 5841).
    "mercury2",
    # battleground_luxalgo: 90d n=33 / 0% WR / avg PnL -7.03% / PF 0.00 (last
    # close 2026-06-01). Already in BLACKLISTED_STRATEGIES at the strategy
    # level, but the source emits other strategy names too — source-level
    # block stops all variants.
    "battleground_luxalgo",
```

Also recommend updating `_SOURCE_SYSTEM_SCORES["mega_mutation"]` (`quality_gates.py:5834`) from `15` to `-30` to disarm the promotion path (mirror the `ml_crypto_pred_v12: -5` / `rocket_scanner: -30` pattern at lines 5790 and 5858):

```python
-    "mega_mutation": 15,
+    "mega_mutation": -30,  # 2026-06-05: 90d 0% WR / -3.14% avg / PF 0.00 — demoted; BLOCKED_SOURCE_SYSTEMS now blocks it
```

### File 2 — `alpha_engine/config.py`

No additions needed. All Grok-named draggers (`kimi_signal_tracking`, `forex_rsi2_mean_reversion`, `myfxbook_retail_contrarian`, etc.) are already in `BLACKLISTED_STRATEGIES`.

### File 3 — `BLOCKED_ASSET_STRATEGY_PAIRS`

No additions needed. The remaining `crypto_soc_*` baby_strat variants (a05/a06/a11+) emit 0 picks in 90d; explicit enumeration would be cosmetic.

## Summary

- **Grok's named targets are ALL already blocked or dormant.** The audit-pipeline alert `[SOURCE_SCORE_AUDIT] stale scores: ['forex_copy_trader', 'ml_crypto_predictor']` is the operational signal worth acting on.
- **Real action items:** 4 source-level additions to `BLOCKED_SOURCE_SYSTEMS` + 1 score demotion. All four have 90d live-DB evidence of n≥30, 0% WR, negative avg PnL.
- **Not recommended:** blanket adding the dormant Grok names — would add maintenance noise without changing emitted volume.
