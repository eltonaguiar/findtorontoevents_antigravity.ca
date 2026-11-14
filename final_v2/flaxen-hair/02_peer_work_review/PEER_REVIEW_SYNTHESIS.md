# Peer Work Review — final_v2

**Date:** 2026-11-14 | **Worktree:** flaxen-hair

This document reviews all peer agent worktrees for the final_v2 stage, synthesizing their findings into actionable profitability guidance.

## Peer Worktree Summary

| Peer | Worktree | Branch | Latest Commit | Key Contribution |
|------|----------|--------|---------------|------------------|
| finpredict-v4 | finpredict-v4 | fix/p0-safe-fixes-2026-11-14 | 8689bac2245 | 6-gate statistical scoring framework + TradingView contest winner research |
| hilarious-seer | hilarious-seer | audit/hilarious-seer-quickwins-2026-11-14 | fe5edb5a312 | Per-asset-class quick-win synthesis, live PnL refresh, conviction scans |
| scratch-hippodraco | scratch-hippodraco | — | 1e5146bfe50 | Per-asset-class quick-wins bundle + peer review + ML validation |
| childlike-airport | childlike-airport | audit-stale-data-and-accuracy-across-asset-classes | 1d9354ab9e2 | Stale data + accuracy audit across asset classes |

---

## finpredict-v4 — Statistical Scoring Framework (PRIMARY)

### Files reviewed:
- `alpha_engine/statistical_scoring_framework.py` — Complete 6-gate StrategyCertifier implementation
- `research/PROFITABLE_SCORING_FRAMEWORK.md` — Full specification with thresholds
- `research/tradingview_contest_winner_research_2026-11-14.md` — Contest winner archetypes and methods

### Key findings:

**6-Gate Certification Pipeline:**
```
GATE 0: Data Quality        → n≥30, complete trade log, no missing prices
GATE 1: Statistical Significance → Bootstrap CI PF_lower>1.0, Sharpe_lower>0
GATE 2: Walk-Forward        → ≥60% profitable folds, mean OOS PF>1.2
GATE 3: Gross Profitability → PF>1.5, Sharpe>1.0, WR>50%, Sortino>1.5
GATE 4: Money-Ready (Net)   → Net PF>1.2, Net Sharpe>0.5, DSR>0.95
GATE 5: Direction Validation → Both sides pass Gate 4 or single-direction certified
```

**Sample size requirements:**
- Discovery: n≥30
- Validation: n≥100
- Money-Ready: n≥200

**Multiple testing correction:**
- Bonferroni for final certification (FWER control)
- Benjamini-Hochberg FDR for discovery (α=0.10)

**Cost model:**
- 10 bps commission per trade
- 5 bps spread
- 5 bps base slippage + volatility penalty
- 10 bps intrabar penalty for winners (23-24% win-to-SL flip)

### TradingView Contest Winner Research:

**Two winner archetypes:**
1. **High-WR Grinders** (83-95% WR, modest per-trade gains, massive sample size) — e.g., prodigy5284 (+17.58%, 95% WR, Stocks)
2. **High-R:R Snipers** (43-52% WR, huge outlier trades, tight risk control) — e.g., KingBob09 (+45.58%, 43% WR, Commodities)

**Key insight:** "No consistent winner is a generalist. They pick ONE pattern, master it, and exploit it in the asset class where it works best."

**Red flags (NOT to copy):**
- Repainting/lookahead bias
- Over-leveraged survivorship bias
- Ignoring costs (live results are 60-70% of backtests)

**Actionable recommendations:**
1. Adopt two-archetype model (separate pipelines for High-WR Grinders and High-R:R Snipers)
2. Add proven-winner symbols: AUDJPY=X, GBPJPY=X, BAT-USD, CRV-USD, ZECUSDT, WLD-USD, XTZ-USD, MINAUSDT
3. Time window targeting: 14:00Z / 21:00Z UTC resolution windows
4. Implement heterogeneous stacking (LightGBM + GRU-Attention + Ridge)
5. Add prediction tail clipping [2nd, 98th] percentile
6. Enforce competition-grade gates (DSR > 0.95, cost-adjusted Sharpe > 0, regime coverage)

---

## hilarious-seer — Live PnL Refresh + Conviction Scans

### Latest commits:
- `fe5edb5a312` — Conviction scan 2026-11-14 20:57 UTC (cross_aggregation/data/conviction_picks.json)
- `fab7526551f` — Live PnL refresh 2026-11-14 20:57 UTC (audit_dashboard/data/picks_now_live_pnl.json)
- `371f422cf95` — Smart picks batch 2026-11-14 20:57 UTC

### Key findings:
- Live PnL data is being refreshed hourly
- Conviction picks are being generated cross-system
- Smart picks are being batched

---

## scratch-hippodraco — Per-Asset-Class Quick-Wins Bundle

### Files reviewed:
- `scratch-hippodraco.MD` (258 lines) — Complete audit summary
- `scratch-hippodraco-quick-wins/` — Per-asset-class quick wins (bond, commodity, crypto, equity-stocks, etf, forex, futures, mutual-funds, overall, peer-review)
- `finpredict-v2_20261114-1602/` — Actions deepdive, raw data, recommendations
- `finpredict-v3/` — Multiple timestamped versions with QUICK_WINS, PEER_REVIEW, ML_VALIDATION

### Key findings from scratch-hippodraco quick-wins:

**Per-asset-class priorities:**
- Bond: Sync active_picks_bond.json into live_picks.db, dedupe SHY ×3
- Commodity: PnL unit normalization, resolve stale open picks, fix non-unique IDs
- Crypto: Fix price fetcher (PnL freezing), kill PF inflation, purge zombie positions
- Equity: Backfill asset_class, refresh stale prices, emit CLOSED events
- ETF: Dedupe duplicate picks, make IDs unique, resolve stale opens
- Forex: Widen PROVEN_STRATEGIES whitelist, honor BLACKLISTED_STRATEGIES
- Futures: Normalize PnL units, fix stale picks, COT data freshness
- Mutual funds: Zero coverage — add MUTUAL_FUND class + symbol set + scanner wiring

**Overall quick wins (P0-P3):**
- P0: PnL calc + staleness refresh, asset_class backfill + MUTUAL_FUND, pick lifecycle, Alpha Engine cancellations, TP/SL resolution bug
- P1: audit_trail.db population, ghost MEMECOIN dedup, TIME_EXIT limbo, JSON artifact freshness, frozen dashboard prices
- P2: Decouple ml_score from confidence, unique pick ID enforcement, recent_picks.txt header fix

---

## childlike-airport — Stale Data + Accuracy Audit

### Branch: audit-stale-data-and-accuracy-across-asset-classes

### Key findings:
- Stale data across all asset classes
- Accuracy issues in picks and PnL calculations
- Review inventory and dated chatlog

---

## Cross-Peer Consensus

All peers agree on:
1. **PnL unit bug** (ratio vs percent, up to 100× disagreement)
2. **Stale picks** (2026-03/04 still OPEN, 172-day SQLite picks)
3. **Non-unique pick IDs** (date-only IDs produce duplicates)
4. **ml_score == confidence** (ML code is sound; inversion is a data bug)
5. **Mutual funds: zero coverage** (confirmed by all peers)
6. **Empty audit_trail.db tables** (all 9 tables empty)
7. **Alpha Engine dead** (9 cancelled + 1 failure, ~24h outage)

**Divergence:** finpredict-v4's profitability research program (23 hypotheses, NONE PROVED) is the most rigorous negative result — it shows that the keyless data hypothesis space is exhausted and no approach is PROVED.
