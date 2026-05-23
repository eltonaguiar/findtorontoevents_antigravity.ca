# Post-Concentration Action Plan — 2026-05-12T22:59:14Z

**Trigger event:** P0-#2 `asset_class_concentration` field shipped + live data
on `dashboard_data.json` confirms COMMODITY is 75.57% one symbol (CT=F).
Headline class PF=3.89 is single-symbol, not broad-class, edge.

**Context:**
- `dashboard_data.json` @ 2026-05-12T22:28:34Z (fresh)
- Concentration tier counts: 8 OK, 1 WARN (COMMODITY), 0 BLOCK
- 486 P0-related tests passing
- DRY-RUN for `active_picks_sync` finally produced output: ~9,700 ACTIVE rows would close (4711 CRYPTO + 4989 EQUITY of 5000-row caps each)
- 4 sidecars (anti_overfit DSR, COT paper pilot, top-N rank backtest, COT Step 7 ROR MC) just got their pymysql fix; first real output expected this cycle

---

## Action items (ranked by leverage)

### A1 — Verify multi_asset_cot PF=19.93 against DB (already shipped, awaiting cron)

P0-#1 `tools/verify_system_pf.py` is on main + wired into `ab_analysis.yml`.
Next daily run (05:30 UTC) will produce
`audit_dashboard/data/system_pf_verification.json`. If verdict =
`DASHBOARD_INFLATED` for `multi_asset_cot`, the entire COMMODITY edge
collapses. If `MATCH`, this is the highest-conviction system in the
entire codebase (PF 19.93 with n=135 is ~20× Tier-1 floor).

**Status:** code shipped. **Block:** waiting on next daily cron OR manual `gh workflow run ab_analysis.yml`.

### A2 — Flip active_picks_sync to `--apply` for one class first

DRY-RUN found 9,700 ACTIVE rows due for resolution. PR-#2 live writer code
shipped (commit `8e04e2a20e5`) but workflow flip not done. Risk: 4,989
EQUITY rows would_close with 0 stay_open is suspicious — either the
backlog is real OR the close-criteria is too aggressive.

**Two-step rollout (safest):**
1. Run `active_picks_sync --apply` for ONE class (CRYPTO first, smaller blast radius) with `--max-rows 500` cap.
2. Inspect actual MySQL rowcount + closed_picks.json delta.
3. If output sane, raise cap to 5000 and add EQUITY.
4. Otherwise back off, refine `compute_verdict()` thresholds.

**Effort:** 30 min. **Risk:** mid (writes to prod DB). **Reversibility:** rollback via `WHERE closed_at > NOW() - INTERVAL 1 HOUR` revert SQL.

### A3 — Per-strategy concentration (extension of P0-#2)

Symbol-level concentration shipped. Next layer: which **strategy** within
each class drives the share? COMMODITY's 75% CT=F is presumably nearly
100% from `multi_asset_cot`. Confirming that closes the loop:
"COMMODITY edge = multi_asset_cot on CT=F" is a one-sentence Day-1
posture that's much clearer than "COMMODITY PF 3.89."

**Implementation:** extend `dashboard_generator.py` per-class accumulator
to also bin by `(symbol, strategy)`. Emit
`asset_class_concentration.{CLASS}.top_strategy` + `top_strategy_share_pct`.

**Effort:** 1.5h.

### A4 — CT=F sizing capacity model

If A1 confirms `multi_asset_cot` PF=19.93 is real, the next gate is
liquidity. CT=F is cotton futures — one contract represents 50,000 lbs
(~$35k notional). Average daily volume is ~25k contracts. Sizing real
money against this single instrument has hard capacity limits; a $5M
allocation can move the market on its own.

**Output:** `reports/ct_f_capacity_model.md` — per-tier max contract size
that stays under 5% ADV impact. Pair with friction-adjusted MC
(`cot_step7_friction_adjusted_mc.py` already shipped) to compute
sustainable real-money allocation.

**Effort:** 2-3h.

### A5 — UI surface for concentration WARN tier

The payload field is live but template.html doesn't render it yet.
The per-class banner spans (`audit_dashboard/template.html` ~ line 866)
should show `(CT=F 76% — single-symbol class)` after the PF number when
`tier=WARN`. Same band for BLOCK in red. Implementation gated on swarm
Q3 (WARN vs BLOCK) — already resolved as WARN with config flag.

**Effort:** 1h.

### A6 — Correlation-regime sidecar follow-up

The first run of `tools/correlation_regime_sidecar.py` (shipped
`459d38064a4`) flagged 3 just-crossed pairs:
- EQUITY ↔ FOREX_USD: -0.20 → -0.78
- ETF ↔ FOREX_USD: -0.18 → -0.77
- GOLD ↔ EQUITY: +0.20 → +0.76

GOLD-EQUITY going strongly positive is risk-on/risk-off correlation
breakdown — the diversifier (gold) is moving WITH equities. Implications
for COMMODITY sizing: if cotton is also caught up in this regime, the
"COMMODITY = independent factor" assumption breaks.

**Investigation:** cross-check cotton specifically against the regime
matrix. If CT=F has high correlation with SPY/QQQ in the current
30d window, we lose the diversification benefit even if the PF is real.

**Effort:** 1h.

### A7 — CRYPTO sub-Tier-2 root-cause audit

CRYPTO PF=1.36 / WR=46.5% on n=7935. Diversified (top symbol BTCUSDT
only 10%) so it's NOT a single-symbol artifact like COMMODITY. But
WR<50% means most picks lose. Either:
- Strategy generation is overfit (consistent loss across many symbols)
- Or one or two specific strategies are huge draggers within the class

Per-strategy concentration (A3) will surface this. Likely candidates:
`kimi_signal_tracking` (already blacklisted), `alpha_engine_fast` (just
quarantined by freebuff), `crypto_winners` (PF 0.39 / WR 30.6%).

**Effort:** 1h after A3 lands.

### A8 — Friction-adjusted DSR gate verification

Action #3 shipped (`d60a7b2656d`). Next cron will produce
`audit_dashboard/data/cot_step7_friction_adjusted_mc.json`. The
gate spec says: friction-adjusted DSR ≥ 0.85 at n_trials=500
is required for CT=F LIVE_ELIGIBLE.

If output shows DSR < 0.85, CT=F is NOT live-eligible regardless of
paper-pilot result. This is the hard math gate. Sanity-check the
output once the cron completes.

**Effort:** 15 min review.

---

## Swarm questions

1. Is the 9,700 backlog from `active_picks_sync` DRY-RUN actually a backlog (good — resolves the F1 0.09% raw-pick coverage crisis), or is the close-criteria too aggressive (would close legitimate active positions)?

2. For COMMODITY single-symbol-class concentration: should the dashboard *reframe* the class as "CT=F sleeve" entirely, or keep the class-level rollup with a WARN badge?

3. Per-strategy concentration (A3) — is `(class, strategy, share_pct)` the right granularity, or should it also include direction split (LONG share vs SHORT share within strategy)?

4. CT=F capacity model — what's the right ADV-impact threshold? Industry default is 5% but cotton has different microstructure (less HFT, more commercial hedger flow).

5. Correlation-regime crossing of GOLD↔EQUITY to +0.76 — does this invalidate the COMMODITY sleeve's intended diversification role? Should sizing be paused until the correlation regime reverts?

6. Friction-adjusted DSR gate at n_trials=500 — is this overly conservative for a single-instrument strategy where the universe of "trials" is much smaller? Should the gate be relaxed for single-symbol strategies (and tightened for multi-symbol)?

## Output format

```
A1. <STATUS>: <one-line reason>
A2. <GO|HOLD|STAGE>: <one-line>
A3. <SHIP_NOW|DEFER>: <one-line>
A4. <NEEDED|SKIP>: <one-line>
A5. <SHIP_NOW|DEFER>: <one-line>
A6. <REQUIRE_FOLLOWUP|NOT_BLOCKING>: <one-line>
A7. <SHIP_AFTER_A3|SHIP_NOW>: <one-line>
A8. <ENFORCE|RELAX>: <one-line>
Q1-Q6 answer block (under 200 words total)
Net_recommendation: <one paragraph; flag if new P0 emerges>
```

Keep total response under 600 words. Cite plan section by A-id / Q-id.
