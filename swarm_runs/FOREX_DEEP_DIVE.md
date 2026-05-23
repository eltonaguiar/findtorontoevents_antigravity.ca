# FOREX Deep-Dive Chain — DeepSeek 4-turn

**Run dir:** [`followup_forex_20260503T155122Z/`](followup_forex_20260503T155122Z/)
**Engine:** `deepseek` (deepseek-chat) — single-engine sequential chain
**Chain session:** `55a2a7d3-e775-4a36-8c14-28f033bd88b3`
**Turns:** 4/4 ok (rc=0). Total elapsed ~52.3 s.
**Config:** [`tools/swarm/examples/forex_deep_dive.yaml`](../tools/swarm/examples/forex_deep_dive.yaml)
**Goal:** Goal #1 — push FOREX out of sub-floor (PF 0.27 / WR 46.4% / n=1169 post-resolver-v2) per `audit_dashboard/data/dashboard_data.json::performance.asset_class_health`.

## Turn-by-turn summary

| # | Name | Elapsed | Envelope | Raw | Notes |
|---|---|---:|---:|---:|---|
| 1 | priming | 32.85 s | 9.2 KB | 8.5 KB | Re-summarised 6.8 KB asset-class audit briefing into a 6-class JSON blueprint. Methodology + kill-rule per class. |
| 2 | analysis | 8.32 s | 2.1 KB | 1.8 KB | Narrowed to FOREX. Pinned 58.3% of FOREX volume + 100% of net drag to two source_systems. Picked **regime axis** for mutate-before-kill. |
| 3 | critique | 6.72 s | 1.9 KB | 1.6 KB | Self-flagged the regime-axis recommendation as resting on an empirically false assumption: spreads do **not** narrow in high-volatility FOREX regimes, they widen. |
| 4 | final | 4.38 s | 1.1 KB | 0.8 KB | JSON answer per contract. Confidence MEDIUM (downgraded from turn-2 HIGH after the critique). |

### Turn 1 — priming (warm-up on full briefing)
DeepSeek returned the same per-class methodology blueprint as Run #2's `deepseek.json`. Notable verbatim FOREX recommendation:

> "If 90-day rolling PF < 0.8 or max drawdown exceeds 25%, abandon FOREX class entirely (current PF 0.27 already triggers kill)"

Caveat in turn-1 (DeepSeek's own words): "FOREX PF 0.27 is already below kill threshold — rescue plan may be moot." This frames the rest of the chain as "is there anything left worth mutating, or do we go straight to abandonment?"

### Turn 2 — analysis (pinpoint the drag)
Identified two specific source_systems as the entire FOREX drag:

- **`forex_rsi2_mean_reversion`** — n=616, WR 46.4%, raw PF **1.52**, after-cost sum **–32.2%**. Edge exists pre-cost but transaction costs eat it.
- **`forex_carry_momentum`** — n=66, WR **6.1%**, PF **0.02**, after-cost sum **–32.2%**. Signal looks inverted.

Combined: 58.3% of FOREX volume, ~64.4% of after-cost loss. Remaining 487 trades (41.7%) too small to offset.

> "A regime filter (e.g., ATR percentile gate or volatility regime) would avoid low-volatility periods where spread eats the mean-reversion edge."

Recommended axis: **regime** (per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`).

Falsification slice (<30 min): split the 616 RSI2 trades by ATR percentile and recompute after-cost PF: subset (a) ATR pct > 70, subset (b) ATR pct < 30. If (a) > 1.5 and (b) < 0.8 → regime confirmed. If both < 1.0 → edge dead, drop the strategy.

### Turn 3 — critique (self-attack)
DeepSeek (verbatim) walked back two of its own turn-2 sentences:

> "Retract: 'A regime filter would avoid low-volatility periods where spread eats the mean-reversion edge' — this assumes spreads are higher in low volatility, which is the opposite of typical FOREX market microstructure."

> "Retract: 'The forex_rsi2_mean_reversion strategy shows a raw PF of 1.52 (profitable before costs)' — this is unverifiable from the briefing and may be false if PF is already post-cost."

Unstated assumption it surfaced: regime-axis choice presumes high-vol regimes have **tighter** spreads. False for FOREX (especially EM pairs). The falsification test could come back negative for a reason unrelated to the strategy edge — bad regime variable.

This is a useful hedge: even if the falsification slice runs cleanly, "ATR percentile" may be the wrong regime variable for the FX spread story.

### Turn 4 — final JSON

```json
{
  "asset_class": "FOREX",
  "primary_drag": "Two strategies, forex_rsi2_mean_reversion (n=616, after-cost sum=-32.2%) and forex_carry_momentum (n=66, after-cost sum=-32.2%), account for 58.3% of volume and the entire net loss.",
  "recommended_axis": "regime",
  "falsification_query": "Compare after-cost PF of forex_rsi2_mean_reversion trades split by ATR percentile >70 vs <30; if both subsets show PF<1.0, regime hypothesis is falsified.",
  "weakest_claim": "The claim that 'forex_rsi2_mean_reversion shows raw PF of 1.52 (profitable before costs)' is the weakest.",
  "confidence": "MEDIUM",
  "next_action": "Run the ATR percentile split on the 616 forex_rsi2_mean_reversion trades using existing dashboard_data.json to confirm or reject the regime hypothesis."
}
```

## Specific questions answered

### 1. Edge mechanism behind `forex_rsi2_mean_reversion` (n=616, PF 1.52, after-cost –32%)
Short-horizon mean-reversion off a 2-period RSI extreme. **Raw edge looks real (PF 1.52)** but is wholly destroyed by spread + transaction cost on the round-trip. DeepSeek's own critique (turn 3) flagged that we cannot verify from the briefing whether the 1.52 PF is gross-of-cost or already net of the resolver-v2 5bp threshold — so the "edge before costs" framing may itself be an artifact. **Don't trust this number until the falsification slice in `dashboard_data.json` reproduces it.**

### 2. Kill, mutate, or paper-trade FOREX class?
**Per the chain: mutate first, then kill if mutation fails** — consistent with `docs/MUTATION_THREE_AXIS_PROTOCOL.md` and the CLAUDE.md FOREX directive ("apply mutate-before-kill protocol... do NOT silently kill"). Sequence:

1. Run the ATR-percentile falsification slice (cheap, <30 min).
2. If subset (a) PF > 1.5 net of cost → ship the regime-gated variant `forex_rsi2_mean_reversion_atr70+` to paper.
3. If both subsets < 1.0 → kill `forex_rsi2_mean_reversion` outright, don't waste another mutation cycle on it.
4. `forex_carry_momentum` (PF 0.02) is more likely a **signal-polarity** problem — try inverse polarity first, kill if PF still < 1.0 after n=30.
5. Class-level: paper-trade only the survivors. No live FOREX capital until at least one strategy passes Wilson 50% LB at WR > 50% with n ≥ 100.

### 3. What about `forex_carry_momentum` (n=66, PF 0.02)?
Tiny n, catastrophic PF. Turn 2 cite (verbatim): "the carry signal is inverted; signal polarity mutation is secondary but less likely to recover edge than regime gating." Turn 3 didn't add commentary on this strategy. The chain didn't have enough room to deep-dive it; the practical answer is: **try inverse polarity, kill if still failing after n=30 forward trades.** Do not size up regardless — n=66 is too small for any aggregate verdict.

### 4. Foolproof rescue plan with 30/60/90 day gates

**30 days:**
- Run ATR-percentile falsification slice on `forex_rsi2_mean_reversion` (cheap).
- Test inverse polarity on `forex_carry_momentum`.
- Hard-cap any single FOREX strategy at 15% of class volume (per CLAUDE.md concentration rule).
- Acceptance gate: at least one variant shows after-cost PF > 1.5 in the slice OR both source_systems are queued for kill per `MUTATION_THREE_AXIS_PROTOCOL.md` exit criteria.

**60 days:**
- Forward-paper any surviving variant for n ≥ 30 trades. Compare to MyFXBook top-10% Sharpe benchmark.
- If no surviving variant clears Wilson 50% LB at WR > 50%, flag FOREX class for abandonment.

**90 days:**
- Full Tier-2 gate review: PF > 1.5, WR > 50%, n ≥ 100, MDD < 20%.
- Decision: promote to live, keep on paper, or remove FOREX from `/audit` and document the abandonment in `reports/deep_dive_FOREX_*.md`.

## Concrete action items

- [ACTION] Run ATR-percentile falsification slice on `forex_rsi2_mean_reversion`: this is the smallest test that can either save FOREX or unlock kill authority. <30 min, uses existing data. Cmd: `python tools/mutation_analysis.py --strategy forex_rsi2_mean_reversion --regime-split atr_percentile --bins "0-30,70-100"`
- [ACTION] Test inverse polarity on `forex_carry_momentum`: PF 0.02 strongly suggests sign error. Cheaper to flip than to redesign. Cmd: `python tools/mutation_analysis.py --strategy forex_carry_momentum --axis signal --invert`
- [ACTION] Verify whether the FOREX `PF 1.52` figure in the briefing is gross or net of resolver-v2 5bp: this is the chain's flagged weakest claim and gates the entire regime-axis hypothesis. Cmd: `python -c "from alpha_engine.outcome_resolver import PNL_WIN_THRESHOLD_BY_CLASS; print(PNL_WIN_THRESHOLD_BY_CLASS)"` then cross-check `audit_dashboard/data/dashboard_data.json::by_asset_class.FOREX` raw vs `asset_class_health.FOREX`.
- [ACTION] Hard-cap any single FOREX strategy at 15% class volume before running any further FOREX mutations: prevents `forex_rsi2_mean_reversion` from compounding the drag during the 30-day mutation window. Code change in pick generator's gate.
- [ACTION] If both falsification subsets return PF < 1.0 after cost, draft `reports/deep_dive_FOREX_2026_05_03.md` with abandonment recommendation per CLAUDE.md "deep-dive process": include external replication options (DBMF / MyFXBook / KMLM) and 30/60/90 plan.

## Confidence

**MEDIUM.** Chain coherence was strong: turn 2 made a specific, falsifiable claim, turn 3 attacked the strongest assumption behind it (FOREX spread-vs-volatility correlation), and turn 4 retained the action plan but downgraded its own confidence from HIGH to MEDIUM in response. The chain did the actual self-critique work — it didn't rubber-stamp turn 2. Two caveats temper the score: (1) the entire analysis rests on numbers from the briefing rather than from `dashboard_data.json` directly, so a stale or wrong figure poisons the chain; (2) the recommended falsification test uses ATR percentile as the regime variable, but turn 3 itself flagged that this may not be the right variable for the FX spread story — meaning a "negative" falsification could be a regime-variable failure rather than a strategy-edge failure.
