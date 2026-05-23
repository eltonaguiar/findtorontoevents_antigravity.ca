# Correction — Non-crypto active picks diagnosis (cloud agent, 2026-04-16)

**Source being corrected:** `copilot/investigate-non-crypto-assets-picks` branch, commit `35605f564`, file `updates/2026-04-16-non-crypto-active-picks-diagnosis.md`.

**Reviewer:** Claude Opus 4.7 (1M), 2026-04-19 post-merge verification.

## Two factual errors in the cloud agent's diagnosis

### 1. `forward_validator.WINNER_FILTER_CONFIG["allowed_asset_classes"]` claim

**Agent claimed:** `allowed_asset_classes = ["crypto", "meme"]` — blocks non-crypto.

**Actual ([alpha_engine/forward_validator.py:419-426](../alpha_engine/forward_validator.py#L419-L426)):**
```python
"allowed_asset_classes": [
    "crypto", "meme",
    "forex", "fx",
    "equity", "stock", "stocks",
    "commodity", "commodities",
    "futures", "future",
    "etf",
]
```

All six non-crypto asset classes are allowed at this gate. The forward validator is **not** the non-crypto bottleneck.

### 2. `production_scanner.apply_quality_gates()` Gate 0 claim

**Agent claimed:** Gate 0 hard-blocks equity/stock/etf/commodity/futures/bond categories.

**Actual ([alpha_engine/production_scanner.py:2179-2217](../alpha_engine/production_scanner.py#L2179-L2217)):** The blanket `_BLOCKED_CATEGORIES` was **removed 2026-04-19** (same day the agent ran). It's been replaced with surgical per-(category, strategy) blocks in `_BLOCKED_CATEGORY_STRATEGIES`:
- Equity: `yahoo_analyst_consensus`, `claude_gainer_ml`, `value_quality_factor`, `consecutive_beats`, `earnings_drift`, `dividend_aristocrats`, `penny_deep_oversold`, `extreme_oversold_bounce`, 4 `goldmine_*` variants
- Commodity: `cftc_cot_commercial_signal`
- Futures: `futures_mean_reversion`, `ema_stack_momentum`

Commit rationale (from the file): *"The cited '0% WR on 92 equity picks' and '19% WR on 16 commodity picks' were from killed strategies (now in BLOCKED_STRATEGIES in quality_gates.py) and toxic symbols. New academic strategies (TSMOM 12m, Faber TAA, Connors RSI2, bond_yield_momentum, etc.) can't build forward history if the class is blocked."*

The cloud agent appears to have read a stale snapshot of this file (predating the 2026-04-19 blanket-block removal) or a different installation.

## What parts of the diagnosis are still accurate

- **FOREX PF collapse** (payoff asymmetry — small avg wins, large avg losses): valid. Matches today's finding that `kimi_signal_tracking/default` on FX accounts for 98% of the asset-class bleed.
- **EQUITY negative expectancy / PF < 1**: valid. `stocks_competition/Breakout Momentum` vs `fast_stocks_competition/Breakout Momentum` config drift is a known open issue.
- **BOND/ETF/FUTURES thin flow**: valid symptom; correct diagnosis (gate/policy) but wrong on which gate.
- **Suggested plan** (per-stage reject ledger, allowlist recovery, payoff recalibration): all sound, not blocked by the factual errors.

## Revised bottleneck hypothesis

After today's work on main, the remaining non-crypto suppression likely comes from:

1. **Dashboard-side `passes_smart_gate` per-asset floors** (`SMART_PICKS_MIN_SCORE_EQUITY`, `SMART_PICKS_MIN_SCORE_FOREX`, etc.) in [audit_trail/quality_gates.py](../audit_trail/quality_gates.py) — floors may be too strict for thin non-crypto flow.
2. **Feed ingestion skew**: most source_systems write crypto-heavy picks. Non-crypto emitters (`multi_asset_scanner`, `cta_cross_asset_tsmom`, bond/futures strategies) are fewer.
3. **Strategy-level blocklist** (which grew today) now paper-flags 20+ non-crypto strategies (ETF/bond/futures/forex families from PR #256 + #262 batches + golden_combo_* + luxalgo + st_obv).

The right next step is the agent's **"Gate Attribution Pass"** proposal (a per-stage reject ledger). That would reveal the actual suppression layer empirically rather than by source-code inspection.

## Recommendation

- Do NOT merge the cloud agent's branch as-is — the two incorrect source-code claims would misdirect future debugging.
- The suggested plan (§4 of the original doc) is sound; adopt it with the corrections noted here.
- Route any follow-up implementation through the same v1.1 discipline applied to Phase A/B scoring fixes shipped today.

## Cross-references (landed today)

- `cb54fee16` — Phase A: classify_pick_quality_v2 delegates to passes_smart_gate
- `75e41adc4` — Phase B: smart_score piecewise base + copy-trader 0.8x cap
- `0c650f9cb` — Reverted Gemini's rr>=1.00 ETF/Bond loosening
- `77910d1dc` — 14 strategies paper-flagged + PROVEN demote-on-decay
- `45d567454` — luxalgo + 5 golden_combos paper-flagged
