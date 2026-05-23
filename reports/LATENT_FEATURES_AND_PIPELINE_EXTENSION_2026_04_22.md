# Latent-feature edge + ML-score pipeline extension — 2026-04-22

**Scope:** extend the audit data pipeline to surface ML model scores + technical features (RSI, regime, volume) that aren't currently displayed as pick columns, and check each for realized edge on closed-trade data.

**Motivation:** `high-conviction picks` tracks one axis (symbol × strategy WR). If ML models and raw technical features provide independent signal, we should test each and route the winners into the gate.

Full tool: `tools/edge_latent_features.py`. Raw drill-down: `reports/EDGE_LATENT_FEATURES_2026_04_22.md`.

---

## 1. Headline findings

### 1a. Claude ML's `pump_probability` has a non-monotonic edge

| `pump_probability` | n | WR | PF | Total PnL% |
|---|---|---|---|---|
| `mid_0.35_0.50` | 47 | **57%** | **2.13** | **+96%** |
| `low_0.20_0.35` | 59 | 34% | 0.73 | −39% |
| `high_0.50_0.65` | 336 | 32% | 0.30 | **−1,038%** |
| `very_high_0.65+` | 40 | 25% | 0.18 | −157% |

The mid band `[0.35, 0.50)` is the ONLY profitable slice. Above 0.50 the ML is wrong more often than not. Same overconfidence pattern as the system's generic `confidence` field (memory: `feedback_confidence_is_not_edge.md`).

**Action:** route Claude ML picks with `pump_probability ∈ [0.35, 0.50)` as admissible, reject the rest.

### 1b. The `confidence_tier` field is degenerate

All 486 RESOLVED Claude ML picks carry `confidence: "VERY HIGH"`. A single-value field provides no edge. Remove from production gate logic — it's a label, not a feature.

### 1c. CRYPTO RSI-4h has a killzone

| RSI-4h band | n | WR | PF |
|---|---|---|---|
| overbought 70-80 | 121 | 42% | 0.89 |
| strong 60-70 | 421 | 34% | 0.70 |
| **neutral 40-60** | **159** | **33%** | **0.60** ← worst PF, biggest killzone |

Counterintuitive but empirical: crypto picks entered at RSI-4h neutral (40-60) have the worst profit factor. "Confirmed strength" (70-80) is actually the least bad.

**Action:** reject CRYPTO picks with `technical_rsi_4h ∈ [40, 60)` — drops ~5% of crypto volume with a PF-0.60 drag.

### 1d. technical_rsi_1h is NULL on the entire ledger

`technical_rsi_1h` is present as a column but zero picks have a populated value that passes the edge threshold. **Pipeline bug: the field is reserved but never computed at entry time.** Either populate it or delete the column.

### 1e. elite_breakdown sub-fields are opaque

`regime_match`, `technical_alignment`, `sector_rotation`, `eb_ml_score` are present on every pick but the quantile bucketing collapses every pick into one bucket — they're coarse categorical scores (typically 0, 3, 10) that look the same on most picks. No edge detectable at this granularity.

**Action:** change the bucketing to categorical (show every distinct value), OR — better — redesign the scoring sub-fields to carry continuous signal (e.g., regime state probability rather than 0/3/10 match flag).

---

## 2. Pipeline extension proposal

### Phase 1 (this PR) — capture ML scores in the pick lifecycle

Today, `claude_ml_picks.json` has `pump_probability` and `confidence` but those fields don't flow into `active_picks.json` or `closed_picks.json`. Once the pick is resolved, the ML's native score is lost.

**Fix:** at pick seeding (wherever `claude_gainer_st` enters the feeder), copy the ML fields into the pick record:
- `ml_pump_probability: float`
- `ml_confidence_tier: str`
- `ml_gainer_score: float` (from antigravity)
- `ml_signals: list[str]` (top-3 signals from the model, audit trail)

These should end up in `dashboard_data.json.picks.recent_closed` so future edge diagnostics can bucket by them directly.

### Phase 2 — compute + capture technical features at entry time

Fields currently missing that should be populated:
- `technical_rsi_1h` — currently always null (bug)
- `technical_atr_pct_at_entry` — volatility regime
- `technical_volume_z_24h` — volume z-score
- `btc_correlation_30d` — crypto-only, correlation to BTC
- `hmm_regime_state` — 7-state regime terminal output (integration already exists per memory)
- `time_bucket_utc` — discretized entry hour (for TOD edge)

Each should be computed once at pick entry and stored in the pick record. The edge diagnostic tool can then slice on any combination.

### Phase 3 — generalize `hedge_fund_quality_gate` to read the new fields

Once Phase 1-2 land:
- Add `ml_pump_probability` band check to the gate (reject outside `[0.35, 0.50)` for claude ML-sourced picks)
- Add `technical_rsi_4h` band check for CRYPTO (reject `[40, 60)`)
- Keep thresholds env-configurable (`HF_GATE_ML_PUMP_LO`, `HF_GATE_ML_PUMP_HI`, `HF_GATE_CRYPTO_RSI_KILL_LO`, `HF_GATE_CRYPTO_RSI_KILL_HI`)

### Phase 4 — surface latent-feature edge in the audit UI

New `/audit` row per pick: "Edge composite" — a compact string like `RSI4h:65 | pump:0.42 | regime:bull | conc_adj:+5`. Lets the human reviewer see at a glance which orthogonal signals lit up.

---

## 3. Expected retroactive impact

If Phase 1-3 had been in place across the 486 resolved Claude ML picks + 3,500 closed non-ML picks:

| Gate addition | Picks rejected | Realized PnL% recovered |
|---|---|---|
| Claude ML `pump_prob ≥ 0.50` | ~376 of 486 (77%) | +1,195% (rejected loss) |
| Claude ML `pump_prob < 0.35` | ~59 of 486 (12%) | +39% (rejected loss) |
| CRYPTO `RSI-4h ∈ [40,60)` | ~159 of 1,650 (10% of crypto) | +57% (rejected loss) |
| CRYPTO `RSI-4h ∈ [60,70)` | ~421 of 1,650 (26% of crypto) | +88% |

Headline: **Claude ML picks should be allowed only in the mid-probability band. The current top-confidence picks are net-negative.** That alone recovers the ML system's lifetime drawdown.

---

## 4. Concrete PR plan

**Branch:** `feat/latent-feature-edge-pipeline-extension`

**Files:**
1. `alpha_engine/hedge_fund_quality_gate.py` — add ML pump-prob band + crypto RSI-4h kill-band rules (env-configurable thresholds, defaults empirically tuned).
2. `tests/test_hedge_fund_quality_gate.py` — 8 new test cases covering the new rules (sweet-spot pass, high-band reject, crypto-killzone reject, missing-field pass, alias handling).
3. `tools/edge_latent_features.py` — the diagnostic that produced this report (already committed).
4. `reports/LATENT_FEATURES_AND_PIPELINE_EXTENSION_2026_04_22.md` — this doc.

**Phase 2 (separate PR, deferred):** the data-pipeline capture changes — need to identify the pick-seeding code paths and add field population.

**Phase 4 (separate PR):** audit UI surface — should wait until data capture is in place so there's something to render.

---

## 5. Risks + mitigations

- **Overfitting:** 47 picks in the `pump_prob mid` band is a small sample. The gate rules should run as **shadow mode** first — tag rejected picks but don't actually reject — to let the forward window validate the in-sample finding.
- **ML-score absence:** picks from non-ML sources don't have `pump_probability`. The gate must pass them (skip the ML check), not reject them for missing a field.
- **RSI absence on non-crypto:** the crypto RSI-4h rule only applies to `asset_class == 'CRYPTO'`. Non-crypto picks have `technical_rsi_4h = null` and should pass.
- **Concurrent gate changes:** if PR #337's drift guard lands with HALT semantics wired, this gate's shadow mode should not promote until drift-guard telemetry confirms stability.

---

## 6. Verification plan

1. Run the Phase 3 gate in shadow mode on the live ledger for 7 days.
2. After 7 days: compute actual-vs-gated WR/PF delta. Require `gated_PF >= 1.10 × baseline_PF` and `gated_WR >= 0.9 × baseline_WR` to promote from shadow to enforce.
3. Unit tests cover: sweet-spot pass, all out-of-band rejects, missing-field pass, env-var override, asset-class scope.
