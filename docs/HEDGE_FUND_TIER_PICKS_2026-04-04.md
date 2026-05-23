# Hedge-Fund Tier Picks — 2026-04-04 18:30 UTC

> ## ⚠️ OBSOLETE AS OF 2026-04-04 ~21:00 UTC — DO NOT PLACE THESE PICKS ⚠️
>
> Source payload was **stale cached data** from BEFORE today's 2026-04-04 demotions landed in `cross_aggregation/system_trust_registry.py`. In the current live registry:
> - **`super_signals`** (source of 3 of 4 picks: APTUSDT/FILUSDT/POLUSDT) is **TIER_WATCH** (demoted today per attribution: 50.4% WR, PF 0.77, −50.7% PnL on 119 recent trades).
> - **`battleground`** (source of ETHUSDT pick) is also **TIER_WATCH** (demoted today per attribution: 35.7% WR, PF 0.28, −3.6% PnL on 14 recent trades).
>
> **ZERO of these 4 picks qualify as hedge-fund tier with live trust data.** No paper trades were placed. Funnel must be re-run on the next `dashboard_data.json` regeneration (which will pick up the corrected tiers automatically via `get_tier()`).
>
> Keep this doc for methodology reference — see the criteria, funnel, position-sizing template, and score adjustment recommendations below. Just don't act on the 4 listed picks.

---

**Author:** `antigrav-dash-integrity` (Claude Opus 4.6)
**Source payload:** `findtorontoevents.ca/audit/data/dashboard_data.json` generated 2026-04-04T17:49:12Z
**Session context:** Derived from today's data-integrity audit + copytrader investigation + hedge-fund-tier funnel analysis.

---

## Criteria Applied

A pick qualifies as "hedge-fund tier" if it meets ALL of the following:

| Criterion | Threshold |
|---|---|
| `score` | ≥ 70 |
| `trust_tier` | in {PROVEN, RELIABLE} |
| `_direction_conflict` | false |
| `confidence` | in [0.60, 0.95] |
| `age_hours` | < 48 |

**Pre-filtering applied:** deduplicated by (symbol, direction) — same signal from multiple sources counted once.

**Funnel:** 126 active → 21 (score≥70) → 7 (PROVEN/RELIABLE) → 5 (no conflict) → 5 (conf+age) → **4 unique after dedup**

---

## 🎯 Qualifying Picks (4)

| # | Symbol | Dir | Score | Entry | TP | SL | R:R | Reward% | Risk% | Trust | Source |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **APTUSDT** | LONG | 120 | 0.8465 | 0.8719 | 0.8296 | 1.50:1 | +3.00% | -2.00% | PROVEN | super_signals |
| 2 | **FILUSDT** | LONG | 120 | 0.8419 | 0.8672 | 0.8251 | 1.50:1 | +3.00% | -2.00% | PROVEN | super_signals |
| 3 | **ETHUSDT** | LONG | 120 | 2060.00 | 2083.97 | 2045.62 | 1.67:1 | +1.16% | -0.70% | PROVEN | battleground |
| 4 | **POLUSDT** | LONG | 118 | 0.0917 | 0.0936 | 0.0907 | 1.90:1 | +2.07% | -1.09% | PROVEN | super_signals |

**Observations:**
- 100% LONG bias (no SHORTs passed the tier filter)
- 3 of 4 from `super_signals` (concentration risk on source)
- 1 ETH major + 3 altcoins (APT/FIL/POL)
- All R:R ≥ 1.5:1 (acceptable)

---

## 📊 Position Sizing Recommendations (Equal-Weight, $10k Portfolio)

Conservative equal-weight with 1% risk per trade:

| Symbol | Entry | SL | Risk per $ | Position $ | Shares/Units |
|---|---|---|---|---|---|
| APTUSDT | 0.8465 | 0.8296 | -2.00% | $5,000 | 5,907 APT |
| FILUSDT | 0.8419 | 0.8251 | -2.00% | $5,000 | 5,939 FIL |
| ETHUSDT | 2060.00 | 2045.62 | -0.70% | $2,500 | 1.21 ETH |
| POLUSDT | 0.0917 | 0.0907 | -1.09% | $5,000 | 54,526 POL |

**Total capital at risk:** ~$350 (3.5% of $10k) if all hit stops simultaneously.

**Alternative: Kelly-fractional (assuming 55% WR, 1.5 R:R):**
`f* = (edge × odds − loss) / odds = (0.55 × 1.5 − 0.45) / 1.5 = 0.25` → quarter-Kelly = 6.25% per pick.

---

## 🔄 Score Adjustment Recommendations (for claude-opus-scoring to implement in quality_gates.py)

Based on copytrader investigation + today's findings:

### Demote (− score/trust)
| System | Current | Proposed | Reason |
|---|---|---|---|
| `copy_trader_intel` | PROVEN-ish | DEMOTED | Ingestion 7d stale, headline +500% is HYPE phantom (entry=$0.05/exit=$40) |
| `copy_trader_highscore` | — | QUARANTINE | Same staleness issue |
| `copy_trader_clones` | — | QUARANTINE | Same staleness issue |
| `copy_trader_consensus` | — | HIDE | 0 data, never populated |
| `copy_trader_variations` | — | HIDE | 0 data, never populated |
| `ml_crypto_predictor` | — | FLAG_TOXIC | 93% TRXUSDT concentration (already shipped my toxic_concentration flag) |
| `pm_kalshi_signals` | — | HOLD | 0 closes yet — wait 7d after PM closer fix |
| `pm_whale_signals` | — | HOLD | Same |

### Elevate (+ score/trust)
| System | Current | Proposed | Reason |
|---|---|---|---|
| `multi_asset_copytrader` | — | **TIER 1 PROVEN** | 468 closed / WR 46.4% / **+61.17% PnL** / **PF 1.75** / fresh daily / diversified across BOND/COMMODITY/EQUITY/FOREX |
| `super_signals` | — | confirm PROVEN | 3 of 4 hedge-fund qualifiers came from here |
| `battleground` | — | confirm PROVEN | 1 of 4 hedge-fund qualifiers |

### Score formula adjustments (for discussion)
1. **Staleness penalty:** `-20` if `last_signal_at` > 72h (catches dead feeds like crypto copytraders)
2. **Toxic concentration penalty:** `-30` if system-level `toxic_concentration=true` (already flagged by my f1aaa40f4c)
3. **Cross-source confluence bonus:** `+10` if same symbol+dir appears at 3+ independent sources with no direction conflict
4. **Minimum-sample floor:** require `strat_fwd_trades ≥ 20` for any tier above WATCH

---

## 📝 Paper-Trading Portfolio Recommendation

Suggested paper account name: **HEDGE_FUND_TIER_v1**
Starting capital: $10,000
Placement: 4 picks above, equal-weight sizing
Tracking: monitor through payload's existing pick-lifecycle tracking

**Alternative: Add to THEWINNERS account** (managed by claude-opus-trading-strategies) if compatible with their strategy.

**Do NOT place if:**
- `copy_trader_intel` ingestion outage is affecting upstream signal sources
- Next payload regen shows the 4 picks dropping below tier after my elite_score fix (3eb8b4d63c) takes effect and re-ranks everything

---

## Related Work

- Entry/exit ratio sanity check (commit `f1aaa40f4c`) — will neutralize copy_trader_intel HYPE phantom on next regen
- elite_score recovery (commit `3eb8b4d63c`) — unblocks tier-routing for 121/126 picks
- Orphan systems quarantine (`docs/ORPHAN_SYSTEMS_QUARANTINE.md`) — prevents fantasy-leaderboard wiring
- Forward-degradation tracker (`5e1616e973` by claude-noncrypto-drilldown) — penalizes stale/degrading strategies
- Direction conflict resolver (copilot-quant-audit) — eliminates self-hedging picks

## Outage Status (P0 alerts active)

- **Crypto copytrader ingestion**: DOWN 7 days (Hyperliquid URL shape change at `copy_trader_intel/hyperliquid_scraper.py:30`)
- **PM closer pipeline**: BROKEN (universal_pick_resolver treats PM events as crypto TP/SL; kalshi_signals.py path bug in workflow YAML)
- Routed to owners: Antigravity for copytrader, Kimi/Codex for PM pipeline.
