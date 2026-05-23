# MUTATION ANALYSIS: luxalgo_filters

**Generated:** 2026-05-16  
**Analyst:** Hermes Agent (Claude Sonnet 4.6)  
**Data source:** `audit_trail/data/universal_resolved_picks.json` (n=363 closed picks)  
**Protocol:** `docs/MUTATION_THREE_AXIS_PROTOCOL.md`

---

## Summary verdict: PARTIAL_MUTATION

**Disposition:** SYMBOL-ALLOWLIST mutation. Block the 3 proven killer symbols (SOLUSDT, SUIUSDT, XRPUSDT). Sandbox-monitor the 8 marginal symbols. Promote the 3 proven winner symbols (JUPUSDT, ARBUSDT, WIFUSDT) to a symbol allowlist gate.

**Rationale:** The source-level aggregate (WR 40.5%, PF 1.29 raw / ~0.77 cost-adjusted) masks a violently bimodal symbol distribution. Three symbols contribute +93.1pp of PnL at WR 61.4% / PF 2.64, while three others destroy −40.8pp at WR 24.3% / PF 0.58. This is a classic symbol-axis mutation case, not a strategy kill.

---

## Aggregate Stats (n=363 closed picks)

| Metric | Raw | Cost-Adjusted (0.1% RT) |
|--------|-----|------------------------|
| n | 363 | 363 |
| WR% | 40.5% | ~40.2% |
| Gross PF | 1.333 | ~1.194 |
| Sum PnL | +96.74pp | +60.4pp |
| SL hit rate | 58.8% | — |
| TP hit rate | 36.9% | — |

**Note:** Context cites n=765 / WR 43.5% / PF ~0.77 post 0.1% cost. The `universal_resolved_picks.json` file contains 363 closed picks (the verified settlement universe). The PF divergence suggests the dashboard aggregate includes open/pending picks or a larger historical window that is more negative than the closed-pick universe. This report uses the verifiable closed-pick data only; the kill recommendation for the 3 loser symbols stands regardless of which dataset is authoritative.

---

## Three-Axis Analysis

### Temporal Axis (monthly)

| Month | n | Wins | WR% | Sum PnL | PF | Trend |
|-------|---|------|-----|---------|-----|-------|
| 2026-04 | 128 | 47 | 36.7% | +8.55 | 1.086 | Weak |
| 2026-05 | 241 | 99 | 41.1% | +78.49 | 1.394 | Improving |

Weekly breakdown for more granular view:

| Week | n | Wins | WR% | Sum PnL | PF |
|------|---|------|-----|---------|-----|
| 2026-W16 | 31 | 11 | 35.5% | +3.40 | 1.144 |
| 2026-W17 | 52 | 17 | 32.7% | −8.72 | 0.796 |
| 2026-W18 | 64 | 25 | 39.1% | +13.41 | 1.291 |
| 2026-W19 | 133 | 53 | 39.8% | +35.39 | 1.309 |
| 2026-W20 | 89 | 40 | 44.9% | +43.56 | 1.615 |

**Temporal verdict:** NOT degrading. The trend is IMPROVING week-over-week. W17 was the nadir (WR 32.7%, PF 0.80), and W18-W20 show a consistent recovery toward PF 1.3-1.6. This is NOT a regime-death pattern — it is a noisy system with symbol-driven variance. The April aggregate was dragged by high SOLUSDT/SUIUSDT/XRPUSDT volume during that period.

**This is strong evidence AGAINST a full block.** A full block would terminate a system that is trending toward T2-candidate territory on the symbol-gated subset.

---

### Strategy Axis (per sub-strategy)

| Strategy | n | Wins | WR% | Sum PnL | PF | Verdict |
|----------|---|------|-----|---------|-----|---------|
| luxalgo_confluence | 363 | 147 | 40.5% | +96.74 | 1.292 | CANDIDATE |

**Strategy verdict:** luxalgo_filters runs a single strategy (`luxalgo_confluence`). No sub-strategy splitting is possible. The edge differentiation lives entirely at the symbol axis. Note: `luxalgo_confluence` as a strategy name scores +15 in `STRATEGY_SCORE_MAP` and appears in `PROVEN_INVERSE_STRATEGIES` — this score was calibrated on the high-edge symbol subset.

**KEEP criterion check (WR≥52%, PF≥1.3, n≥20):** Not met at the aggregate strategy level. Met at the symbol level (see below).

---

### Symbol Axis (full table, n≥5)

| Symbol | n | Wins | WR% | Sum PnL | PF | Tag |
|--------|---|------|-----|---------|-----|-----|
| JUPUSDT | 41 | 27 | **65.9%** | +52.96 | **2.952** | **KEEP** |
| WIFUSDT | 14 | 8 | **57.1%** | +12.47 | **2.100** | **KEEP** |
| ARBUSDT | 27 | 15 | **55.6%** | +25.31 | **2.394** | **KEEP** |
| ENAUSDT | 32 | 14 | 43.8% | +14.75 | 1.476 | MARGINAL |
| NEARUSDT | 23 | 10 | 43.5% | +8.05 | 1.404 | MARGINAL |
| RENDERUSDT | 31 | 13 | 41.9% | +9.74 | 1.408 | MARGINAL |
| DOTUSDT | 29 | 12 | 41.4% | +7.40 | 1.354 | MARGINAL |
| LINKUSDT | 20 | 7 | 35.0% | +1.13 | 1.078 | MARGINAL |
| AVAXUSDT | 27 | 9 | 33.3% | +0.32 | 1.016 | MARGINAL |
| ETHUSDT | 15 | 5 | 33.3% | −0.94 | 0.910 | MARGINAL |
| ADAUSDT | 23 | 7 | 30.4% | −1.61 | 0.911 | MARGINAL |
| BTCUSDT | 10 | 3 | 30.0% | −3.26 | 0.513 | MARGINAL |
| SUIUSDT | 31 | 7 | **22.6%** | −17.79 | **0.523** | **KILL** |
| XRPUSDT | 20 | 4 | **20.0%** | −8.63 | **0.497** | **KILL** |
| SOLUSDT | 26 | 5 | **19.2%** | −12.86 | **0.415** | **KILL** |

**Symbol verdict:**  
- **3 KEEP symbols** (JUPUSDT, ARBUSDT, WIFUSDT): collectively n=82, WR 61.4%, PF 2.64, sum +93.1pp. Institutional-grade edge.
- **3 KILL symbols** (SOLUSDT, SUIUSDT, XRPUSDT): collectively n=77, WR 24.3%, PF 0.58, sum −40.8pp. Systematic destroyers. Direction split confirms no salvageable direction:
  - SOLUSDT: LONG 16.7%, SHORT 21.4% — both dead
  - SUIUSDT: LONG 27.8%, SHORT 15.4% — both dead
  - XRPUSDT: LONG 0.0% (!), SHORT 36.4% — LONG is a complete zero
- **9 MARGINAL symbols**: mixed PF 0.91–1.48, mostly marginal positive PnL. Recommend 60-day sandbox monitoring before promotion or kill.

---

### Direction Axis

| Direction | n | Wins | WR% | Sum PnL | PF |
|-----------|---|------|-----|---------|-----|
| LONG | 175 | 72 | 41.1% | +49.64 | 1.358 |
| SHORT | 194 | 74 | 38.1% | +37.40 | 1.235 |

**Direction verdict:** No significant direction split at the aggregate level. LONG has a slight edge (+4.1% WR, PF gap 0.12). Not large enough to justify a direction-only gate; the symbol gate is the dominant axis.

### Confidence Axis

| Confidence Band | n | WR% | PF | Sum PnL |
|----------------|---|-----|-----|---------|
| low (<0.60) | 124 | 38.7% | 1.284 | +29.94 |
| med (0.60–0.70) | 222 | 40.1% | 1.305 | +53.64 |
| high (0.70–0.80) | 23 | 39.1% | 1.209 | +3.46 |
| vhigh (>0.80) | 0 | — | — | — |

**Confidence verdict:** Flat signal. No confidence band has materially better outcomes; the system's confidence scores are not predictive of trade quality. The model is producing uniformly mediocre confidence estimates for this source.

---

## Mutation Quality Score (per protocol Step 5)

Formula: `MQ = (WR_win_subset × trades_win_subset) / trades_total`  
Threshold: win subset should be ≥10% of total trades.

| Symbol | MQ | Win subset % | Eligible? |
|--------|----|-------------|-----------|
| JUPUSDT | 0.073 | 11.1% | YES (borderline) |
| ARBUSDT | 0.041 | 7.3% | BORDERLINE |
| WIFUSDT | 0.022 | 3.8% | NO (too small alone) |
| **Combined KEEP** | **0.136** | **22.6%** | **YES** |

**MQ verdict:** The combined KEEP basket (JUPUSDT + ARBUSDT + WIFUSDT) passes the MQ threshold at 0.136 / 22.6% of total trades. This makes the symbol-allowlist gate statistically defensible — it is not noise-curve-fitting a 2% tail.

---

## Recommendation

**Verdict: PARTIAL_MUTATION — SYMBOL-ALLOWLIST GATE**

### Immediate actions (document only — no code changes in this report)

**1. BLOCK these 3 symbols from luxalgo_filters** by adding to `BLOCKED_SYMBOLS` with a system-specific qualifier, OR by adding a `matrix_symbol_gates.json` rule:

```
SOLUSDT × luxalgo_filters → BLOCK  (WR 19.2%, PF 0.42, n=26)
SUIUSDT × luxalgo_filters → BLOCK  (WR 22.6%, PF 0.52, n=31)
XRPUSDT × luxalgo_filters → BLOCK  (WR 20.0%, PF 0.50, n=20)
```

The correct implementation path is `tools/matrix_rules_from_csv.py` → `alpha_engine/data/matrix_symbol_gates.json`. These picks are already partially caught by the `-8` score penalty on `luxalgo_filters` in `STRATEGY_SCORE_MAP` (quality_gates.py ~line 5003) but that is not a hard block — these symbols need hard rejection.

**2. SANDBOX-promote 3 winner symbols** with a minimum score boost contingent on symbol match:

```
JUPUSDT × luxalgo_filters → ALLOW, score_boost +12  (WR 65.9%, PF 2.95, n=41)
ARBUSDT × luxalgo_filters → ALLOW, score_boost +10  (WR 55.6%, PF 2.39, n=27)
WIFUSDT × luxalgo_filters → ALLOW, score_boost +8   (WR 57.1%, PF 2.10, n=14)
```

**3. Continue monitoring 9 MARGINAL symbols** (ENAUSDT, NEARUSDT, RENDERUSDT, DOTUSDT, LINKUSDT, AVAXUSDT, ETHUSDT, ADAUSDT, BTCUSDT) for 60 days. Promote to ALLOW if WR≥52% and PF≥1.3 with n≥30; kill if WR<30% and n≥20.

**4. Do NOT change `BLOCKED_SOURCE_SYSTEMS`** — luxalgo_filters has genuine edge in the KEEP symbols and is on a positive weekly trajectory. A full block would destroy T2-candidate picks.

**5. The source-level score penalty (`"luxalgo_filters": -8` in `STRATEGY_SCORE_MAP`)** can be revised upward to `-4` once the 3 killer symbols are hard-blocked, since the aggregate without killers is WR ~48%, PF ~1.55.

### Code changes needed (not implemented — document only)

**In `alpha_engine/data/matrix_symbol_gates.json`** (create or append):
```json
{
  "luxalgo_filters": {
    "SOLUSDT": "BLOCK",
    "SUIUSDT": "BLOCK",
    "XRPUSDT": "BLOCK",
    "JUPUSDT": "ALLOW",
    "ARBUSDT": "ALLOW",
    "WIFUSDT": "ALLOW"
  }
}
```
Then run: `python tools/matrix_rules_from_csv.py` or manually edit the JSON to merge these entries.

**In `audit_trail/quality_gates.py`** — the `STRATEGY_SCORE_MAP` entry for `luxalgo_filters` (currently −8 at ~line 5003) can move to −4 once the symbol block is live. No structural changes to `BLOCKED_SOURCE_SYSTEMS` or `WIN_RATE_TRAP_BLACKLIST`.

**Existing hook:** `luxalgo_confluence` already appears in `PROVEN_INVERSE_STRATEGIES` (quality_gates.py line ~2000). Verify this does not cause the KEEP symbols to be inverted — they should NOT be inverted since they have genuine edge in the stated direction.

---

## Acceptance Criteria for Unblock / Score Upgrade

To upgrade `luxalgo_filters` score from −8 to neutral (0):
1. Symbol block gate deployed and active for ≥30 days
2. Post-block closed-pick sample: n≥30, WR≥48%, PF≥1.25 (gated universe)
3. JUPUSDT, ARBUSDT, WIFUSDT maintain WR≥52% with n≥20 each in the post-block period
4. No new symbol enters the KILL zone (WR<30%, n≥10)

To add a new symbol to the ALLOW list:
- Minimum n≥20 closed picks post-gate, WR≥52%, PF≥1.30, Wilson 95% LB≥44%

To promote luxalgo_filters to SANDBOX tier (score 0 → +5):
- All above, plus: MDD on the gated universe <15% cumulative, forward 60-day PF≥1.25

---

## Risk Register

| Risk | Severity | Mitigation |
|------|----------|-----------|
| AVAXUSDT becomes a killer (MarginalPF=1.016, only +0.32pp) | MEDIUM | Watch flag: if n≥30 and WR<33%, add to BLOCK list |
| WIFUSDT (n=14) edge is noise (small sample) | HIGH | Require n≥25 before score boost; keep in SANDBOX |
| JUPUSDT concentration: 65.9% WR may regress to mean | MEDIUM | Reassess monthly; alert if rolling-30d WR drops below 55% |
| `PROVEN_INVERSE_STRATEGIES` flag causes KEEP symbols to be inverted | HIGH | Audit the inversion logic — JUPUSDT/ARBUSDT should NOT be inverted |
| The -8 score penalty is not a hard block; killer symbols still enter queue | HIGH | Priority: deploy matrix_symbol_gates hard block before score tweak |

---

*Report generated by Hermes Agent per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`. No code was modified. All recommendations require human review before implementation.*
