# Cross-Asset Edge Synthesis — all classes, all sources, 5 parallel agents (2026-07-04)

**Author:** claude (fable) + 5 subagents. **Mandate:** stop tunnel-visioning on crypto; test EVERY asset class + the sources the operator expects edge from (copytraders, fundamentals, prediction markets), across all 9 databases, with the 3 mandatory controls. **Every stat below came from a live SQL/API query — no fabrication.**

## Verdict table — NO promotable edge anywhere, but the *reason* is diagnostic

| Source / class | best honest number | verdict | why it's not edge |
|---|---|---|---|
| **Copytraders / public trades** | n_resolvable = **0** | NO-EDGE / INSUFFICIENT | 243k Hyperliquid-clone positions are **100% status=OPEN, never resolved** (2-day March snapshot). The few with pnl are placeholder constants. Hardcoded `copy_hl_NMTD_25M = 81.3% WR` (`elite_scorer.py:444`, `auto_tuner.py:148`) is **fabricated — zero resolved trades back it.** |
| **Prediction markets (Kalshi/Polymarket)** | intrabar net PF **0.37** | NO-EDGE | Only raw PM table is a **single snapshot** (no time series → no CLV). The "PM strategy" is really a losing crypto signal; the repo's own forward pilot already marked it REFUTED (n=2627). |
| **Equity — fundamentals/value** | market-neutral value PF <1 (neg both halves) | NO-EDGE | Value & quality had **no market-neutral edge** 2021–26 (growth regime). Random long-only from the 230 current constituents = **Sharpe 0.46 / +36% with zero skill** → every long-only "win" is survivorship+beta. |
| **Equity — momentum** | mkt-neutral 12-1 Sharpe 0.86 | WEAK, NOT ROBUST | **Fails both-halves** (H1 −0.12 / H2 1.98 — all edge is 2024–26), boot CI-LB ≈ 0. |
| **Memecoin (58-table DB)** | bt100 SHORT PF 5.33 | SURVIVORSHIP/REGIME ARTIFACT | 69/70 shorts fired in a **3-day crash** (Feb 14–16); pairs are symmetric TP/SL mirrors ("short wins" = "market fell"). Universe **86% under $500K/24h** → unfillable. |
| **32.7M `bt_backtest_trades`** | meta_strategy PF **1.011** | NO-EDGE | **89.5% OPEN** + 100s× re-import duplication (1.72M→787 dedup). Sole survivor (justin_breakout n≥200) fails both-halves + CI-LB 0.952 + absent from forward ledger. pnl_pct itself is clean. |
| **CRYPTO directional (prior work)** | clean-entry = random baseline | NO-EDGE | entry_price bug + −27% regime + signal-bar look-ahead (see `DATA_INTEGRITY_entry_price_2026-07-03.md`). |

## The real diagnosis — it's a MEASUREMENT/RESOLUTION failure, not (only) an alpha failure

The operator's instinct ("we should have edge *somewhere* — copytraders, fundamentals, prediction markets") is reasonable, but the data can't answer it, and here's the mechanical reason, repeated across **every** source:

1. **~90% of captured positions NEVER RESOLVE.** Copytraders: 243k rows 100% OPEN. `bt_backtest_trades`: 89.5% OPEN (29.25M rows). Memecoin `science_engine_picks`: 588 all WATCHING. The pipelines record entries but never fetch/attach exits → no realized PnL → nothing to measure.
2. **The resolved subset is contaminated.** The crypto forward ledger's `entry_price` is ~29% clean / +1.3% biased, and `intrabar_pnl_pct` rides it (P0).
3. **Massive re-import duplication** inflates row counts 100s× and fakes significance until you dedup.
4. **Single-regime / single-snapshot** capture (memecoin 3-day window; PM one snapshot) → no out-of-regime test possible.

You cannot find a consistent winner with a scoreboard that (a) leaves 90% of games unfinished, (b) mis-records the scores it does keep, and (c) only watched one season. **That — not "no alpha exists" — is why we've been stuck for months.**

## What IS real / worth keeping
- **Point-in-time fundamentals are now obtainable** (Finnhub `/stock/metric series.quarterly`, 229 tickers, dated back ~1990) — the DB never had PIT history. This unblocks an honest fundamentals test on a *better* universe (small-caps + delisted) later.
- The **clean daily feeds** (`equity_daily_ohlcv` 230×5yr, `futures_daily_ohlcv` 11×5yr) are uncontaminated and usable for look-ahead-free daily-horizon tests.
- `bt_backtest_trades.pnl_pct` is trustworthy where closed (0/5000 mismatch) — the table is a usable strategy inventory once deduped + resolved.

## The unlock (singular, highest-leverage — above any strategy)
**Fix the resolution + entry pipeline, then re-run this whole sweep on clean, resolved, multi-asset data:**
1. **Resolve the OPEN backlog** — fetch exits for the ~90% OPEN positions (copytraders, bt_backtest_trades) so strategies actually accumulate forward outcomes.
2. **Fix `entry_price`** at the writer + re-resolve `intrabar_pnl_pct` from bar-aligned NEXT-bar entries (non-destructive sidecar, backup first).
3. **Dedup on import** (strategy,symbol,entry_time) — kill the 100s× re-import inflation.
4. **Then** re-mine every class/source (this synthesis becomes the baseline) with the 3 controls.

## Immediate cleanups (small, real)
- Remove/neutralize the **fabricated `copy_hl_NMTD_25M` 81.3% WR** in `elite_scorer.py:444` + `auto_tuner.py:148` — it's weighting production scores off fiction.
- Register memecoin `bt100_*` / `mc_winners` as survivorship/regime traps.

**Bottom line for the operator:** No, there is no confirmable edge in any asset class or source today — but we now know it's because the measurement layer is broken across the board (90% unresolved + corrupt entries + duplication + single-regime), not because we lack strategies or markets. Fixing resolution is the path to a real winner; it is the same root cause everywhere.
