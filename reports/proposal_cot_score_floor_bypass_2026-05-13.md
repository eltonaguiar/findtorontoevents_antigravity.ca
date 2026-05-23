# Proposal — COT-signal score-floor bypass

**For peer (`0f7ecsyk`) — DO NOT execute. Flag-only proposal.**

**Source:** Hidden-edge swarm (cycle 2, `reports/hidden_edge_scan_2026-05-13.md`):
> "Hidden alpha cohort: ... `multi_asset_cot` / `multi_asset_copytrader` × **`CT=F` cotton futures** (n=34, +5.04% avg, 100% WR) with strategies `cftc_cot_commercial_signal` + `cot_positioning` — score is blind to COT fundamentals."

## Current state (inferred)

Pick router applies an `elite_score` / `score` floor before promoting a pick to the active queue. COT-derived signals (cftc_cot_commercial_signal, cot_positioning) score LOW because the ML score doesn't have COT fundamentals as a feature, BUT their realized WR is 100% over n=34 picks. The current score-floor gate is filtering out genuine alpha because the score model is blind to the signal's actual driver.

## Proposed change

Bypass the elite_score floor when the source strategy is in a curated allowlist of "fundamental-signal" strategies whose realized stats prove edge despite low ML score.

```python
# Pseudocode for audit_trail/quality_gates.py active-pick gate
ELITE_SCORE_FLOOR_BYPASS_STRATEGIES = {
    # Strategies where ML score is blind to the underlying signal driver.
    # Each entry: pick is allowed even if elite_score < floor as long as the
    # strategy's lifetime realized WR > 60% AND PF > 1.5 AND n >= 20.
    "cftc_cot_commercial_signal",
    "cot_positioning",
    # Add candidates here ONLY after similar realized-stats validation.
}

def passes_score_floor(pick, lifetime_stats_lookup):
    strategy = pick.get("strategy", "")
    if strategy in ELITE_SCORE_FLOOR_BYPASS_STRATEGIES:
        stats = lifetime_stats_lookup(strategy)  # WR, PF, n
        if stats and stats["wr"] > 60 and stats["pf"] > 1.5 and stats["n"] >= 20:
            return True  # bypass score floor
    return pick.get("elite_score", 0) >= ELITE_SCORE_FLOOR
```

## Why this matters

The hidden-edge swarm found 34 picks (multi_asset_cot/copytrader × CT=F × cftc/cot strategies) at **+5.04% avg PnL with 100% WR**. If the score-floor gate filtered ANY of these out, that's pure forgone alpha. The strategy's lifetime realized stats prove edge — the ML score model is the wrong lens for evaluating it.

## Caveat — concentration

This sub-strategy is the same one driving the 75% concentration warning on COMMODITY (peer's just-shipped P0-#2 `asset_class_concentration`). So bypassing the score floor for it would FURTHER concentrate volume in CT=F. Two opposing forces:

- Pro: don't filter out real alpha
- Con: don't double-down on concentration risk

**Resolution:** add a concentration-aware cap. If COMMODITY top-symbol share > 70% → cap CT=F LONG entries at 1 per week regardless of bypass approval. Forces rotation while preserving the bypass for non-CT=F COT signals.

## Acceptance gate

- Shadow-mode 30 days
- Confirm bypass admits ≥5 new COT picks in COMMODITY class with WR ≥ 70% on resolved
- Concentration cap holds → COMMODITY top-share stays ≤ 75%
- If both pass → promote bypass to live

## Effort

- Code: 2h
- Test: 1h  
- Shadow log + concentration cap: 2h
- Total: ~5h

## Risk

- MEDIUM. Bypassing a quality gate is non-trivial. If the lifetime-stats lookup is stale OR misclassifies, picks slip through.
- Mitigated by:
  - Requiring lifetime WR > 60 (high bar)
  - n >= 20 (statistical floor)
  - Concentration cap on top-symbol entries

## Cross-link

- `reports/hidden_edge_scan_2026-05-13.md`
- `audit_dashboard/data/asset_class_concentration` (peer's commit `5c8ef45c85d` P0-#2)
- `reports/post_concentration_A6_ctf_correlation_check_2026-05-12.md` (CT=F is genuinely uncorrelated to SPY, so the bypass concentrates legit alpha not just risk-on-beta crowding)

## Decision needed

1. **Approve** as proposed (bypass + concentration cap)
2. **Approve bypass without concentration cap** (risk acceptable since CT=F uncorrelated to SPY per A6)
3. **Reject** — keep score floor flat; address by training the score model with COT features instead
4. **Different approach** — propose alternative
