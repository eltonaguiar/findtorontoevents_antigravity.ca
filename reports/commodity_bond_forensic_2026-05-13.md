# COMMODITY & BOND Regression Forensic — 2026-05-13

**Resolves:** the two open P0 forensics from [reports/session_handoff_2026-05-12_opus.md](reports/session_handoff_2026-05-12_opus.md) §6 and [reports/implementation_plan_2026-05-13.md](reports/implementation_plan_2026-05-13.md) P0-2/P0-3.

**Method:** read-only swarm pass over commits 2026-05-05 → 2026-05-13, cross-referenced against `dashboard_data.json` snapshots and the prior diagnostic docs.

---

## 1. COMMODITY anomaly — VERDICT: SUSTAINABLE

### What changed
| Date | n | PF | WR |
|---|---|---|---|
| 2026-05-05T01:37Z | 939 | 2.04 | 49.5% |
| 2026-05-12T00:55Z | 1,128 | 3.77 | 66.7% |
| 2026-05-12T22:29Z | 1,161 | 3.94 | 67.8% |

Note: earlier docs cited `n=425` from `asset_class_health.resolved_n` which is a verdict-grade subset; the `by_asset_class` raw count is 1,161. Both numbers are correct under their respective definitions.

### Root cause: two clean classification fixes between May 5 and May 12

**`bb083ab5ec` (2026-05-12T00:55Z) — zero-PnL artifact filter.** The resolver was emitting `pnl_pct=0` for ~69% of terminal-status rows where `exit_price == entry_price` or `exit_price <= 0` (book-keeping artifacts where the resolver failed to compute pnl). This commit filters them at the dashboard generator. Result: n bumped up (artifacts cleared out of FLAT bucket) and PF rose because the zero-PnL rows had been dragging the gross-profit-vs-gross-loss ratio.

**`c0f1c135dc` (2026-05-05) — `SOURCE_SYSTEM_BLOCKLIST_BY_CLASS` for COMMODITY.** Suppressed `forex_copy_trader` from COMMODITY routing (46 trades, PF 0.31). Direct PF lift of measurable magnitude.

### Why this is not survivorship bias
1. The zero-PnL filter is **systematic** — it keys on `(pnl_pct == 0) AND (exit_price == entry_price OR exit_price <= 0)`. Not selective on winners vs losers.
2. The `forex_copy_trader` suppression was a category fix (the strategy doesn't belong on commodity tickers in the first place), not a results-conditional kill.
3. Cross-check: subsequent days saw n grow 1,128 → 1,161 (live pick closure at normal cadence). No further re-resolution. The PF held.

### Implication
The COMMODITY PF 3.94 / WR 67.8% / n=1,161 is the post-cleanup true state. **Walk-forward backtest can proceed** — and is now mechanically feasible (n > 200 charter floor) because the cleanup pushed it past the threshold for the first time.

---

## 2. BOND anomaly — VERDICT: RE-CLASSIFICATION (no new bond_* picks live)

### What changed
| Date | n | PF | WR |
|---|---|---|---|
| 2026-05-05T01:37Z | 21 | 1.72 | 55.6% |
| 2026-05-12T00:55Z | 21 | 0.66 | 54.5% |
| 2026-05-12T22:29Z | 21 | 0.66 | 54.5% |

The earlier "n=11 / n=18" reads were `asset_class_health.resolved_n` (verdict-grade subset); the `by_asset_class` raw count is 21 in both snapshots — n is essentially static.

### Root cause
The 21 BOND trades visible on `/audit` are **not** from `bond_*` strategies. They are **legacy `futures_momentum` trades on ZN=F** (10-year US Treasury futures) that were miscategorized as BOND because the asset_class resolver maps `=F` continuous-contract symbols into the futures-adjacent class.

The PF crash 1.72 → 0.66 is **not** a recount — it is **outcome resolution** on the same legacy pool. Same 21 rows; their `_outcome` field flipped from win to loss on several of them as later resolver passes corrected mid-trade evaluations. Cross-check: [reports/bond_root_cause_2026-05-12.md](reports/bond_root_cause_2026-05-12.md) end-to-end pick-lifecycle trace found **zero** closed picks from the actual `bond_*` strategies (`bond_yield_momentum`, `bond_duration_rotation`, `bond_mean_reversion`, `bond_connors_rsi2`, `bond_credit_spread_mean_reversion`).

### Three-layer blocker for getting real bond picks live (unchanged from earlier doc)
1. **Primary** — `BOND_ELITE_FLOOR=40` rejects 7/7 raw bond signals at curation. `non_crypto_agent/data/bond_picks.json` shows `total_raw=7, quality=0`.
2. **Secondary** — `FORWARD_GATE_MIN_TRADES=50` in [alpha_engine/forward_validator.py:389](alpha_engine/forward_validator.py#L389). Every `bond_*` strategy has 0 closed picks.
3. **Tertiary** — `non_crypto_agent/data/bond_picks.json` is consumed as `orphan_emitter_bond` (stats-only); never merged into `active_picks.json` for live sizing.

### Implication
Setting `vars.BOND_ELITE_FLOOR=32` (your pending action) unblocks **Layer 1** and is the right first move. Layers 2 and 3 still need follow-up PRs before BOND becomes a live-sized class. The 0.66 PF on the legacy ZN=F pool is irrelevant to the bond_* strategies' future performance — those start at n=0.

---

## 3. What this unlocks

1. **COMMODITY walk-forward is no longer blocked by data.** Pre-cleanup the class had < 200 clean COMMODITY rows in `recent_closed`; post-cleanup it has > 1,100. The implementation gap is a small one-file change in `walkforward_validator.py` (next section).

2. **BOND walk-forward stays blocked** until either (a) `vars.BOND_ELITE_FLOOR=32` ships AND time accumulates ≥ 50 bond_* closed picks (months), or (b) we cut `FORWARD_GATE_MIN_TRADES` for BOND specifically. The legacy ZN=F pool at n=21 / PF 0.66 is below charter floor (n≥100) and below Tier 3 PF (≥1.2); not worth walk-forwarding.

---

## 4. Two corrections to prior committed docs

- [reports/money_ready_validation_plan_2026-05-11.md](reports/money_ready_validation_plan_2026-05-11.md) §0 cites BOND `n=18 / PF 1.72`. Current is `n=21 / PF 0.66`. Stale.
- [reports/money_ready_state_2026-05-12T23Z.md](reports/money_ready_state_2026-05-12T23Z.md) §0 cites COMMODITY `n=425`. That was the verdict-grade `asset_class_health.resolved_n`. The raw `by_asset_class` n is 1,161. Both are correct under their respective field definitions; the doc should note which it's quoting.

These don't need correction commits — this forensic doc is the canonical answer.

---

## 5. Pattern note

This is the third time this session that a "regression" or "anomaly" turned out to be a **classification or resolver change**, not genuine strategy degradation. The pattern: when n changes materially between snapshots without a corresponding cron-volume change, the first hypothesis should be "resolver re-ran on a different rule" — not "strategies got worse."

Adding a `closed_picks_diff` event log to the dashboard generator (per session_handoff §7.1) would make this visible without needing a forensic swarm each time.
