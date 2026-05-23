# Top High-Conviction (HC) Picks — 2026-04-20 Snapshot

**Source:** `audit_dashboard/data/dashboard_data.json` (as of 2026-04-21 ~20:30 UTC)
**Filter:** `audit_trail.feed_membership.evaluate_hc_tier` (Phase 1 placeholder gates)
**Universe:** 67 live active picks → 2 HC-qualifying (3.0%)

---

## Headline

**Only 2 of 67 active picks pass the HC gate, both grade-b, both CRYPTO.**
Five of the six asset classes (EQUITY, ETF, FOREX, COMMODITY, BOND) currently have **zero HC-grade picks live.** No grade-a picks exist in any class.

### Why so few pass
From the 67 active picks (stdlib counter on the evaluator's reject reasons):

| Reject reason | Count |
|---|---|
| `score < 60` | 56 |
| `trust_tier == WATCH` (not PROVEN/RELIABLE) | 41 |
| `confidence < 0.70` | 28 |

Trust-tier distribution of the live feed is `WATCH: 41` / `RELIABLE: 26` / `PROVEN: 0`. With zero PROVEN picks live, grade-a is mechanically unreachable today.

### Asset-class coverage of active feed
`CRYPTO: 50 • EQUITY: 10 • COMMODITY: 5 • FOREX: 2 • ETF: 0 • BOND: 0`
ETF and BOND have no live picks at all (not an HC gap — a sourcing gap).

---

## Top HC Picks by Asset Class

### CRYPTO (2 HC of 50 active)

| Rank | Symbol | Dir | Entry | TP | SL | R:R | Strategy | Source | Score | Conf | strat_fwd_wr | HC |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | XRPUSDT | LONG | 1.43 | 1.46 | 1.41 | 1.5 | `drawdown_recovery_rsi_xrp` | `fc_crypto_pro` | 93 | 0.818 | 72.2% (n=18) | grade-b |
| 2 | AVAXUSDT | LONG | 9.42 | 9.98 | 9.18 | 2.34 | `ml_enhanced_AVAXUSDT_4h_A_xgboost` | `alpha_engine` | 68 | 0.70 | 49.8% (n=1312) | grade-b |

Neither reaches grade-a despite pick #1 satisfying the grade-a score (93 ≥ 70) and confidence (0.818 ≥ 0.80) thresholds — it is blocked by `trust_tier = RELIABLE`, not PROVEN. Pick #2 is marginal on every axis (score 68, conf exactly 0.70).

### EQUITY (0 HC of 10 active)
**Empty.** 10 active equity picks, none pass. Dominant reject: `score < 60` and low confidence. Actionable: investigate why the equity scorer is compressing scores below 60.

### ETF (0 HC of 0 active)
**No live ETF picks at all.** This is a sourcing/emission issue, not an HC-gate issue.

### FOREX (0 HC of 2 active)
**Empty.** Sample too small to diagnose (n=2).

### COMMODITY (0 HC of 5 active)
**Empty.** 5 active picks, none pass gates. Commodities agent last ran 2026-04-20 20:15 UTC (recent commits).

### BOND (0 HC of 0 active)
**No live BOND picks at all.** Sourcing gap.

---

## Historical Edge Validation

For each strategy in the live HC top list, its realized history in `picks.recent_closed` (3,500 rows):

| Strategy | N closed | Real WR | PF | Mean PnL% | Max DD (cum) | Verdict |
|---|---|---|---|---|---|---|
| `drawdown_recovery_rsi_xrp` | 1 | 0.0% | 0.0 | -1.33% | -1.33% | **Small sample (n<10).** HC label rests on gates, not empirics. The single closed trade was a loss; `strat_fwd_wr=72.2%` on the pick card comes from a forward-trade cohort (n=18) that is not co-located in this closed window. |
| `ml_enhanced_AVAXUSDT_4h_A_xgboost` | 0 | — | — | — | — | **No closed rows** in `recent_closed` under this exact strategy name. Pick card self-reports `strat_fwd_trades=1312`, `strat_fwd_wr=49.8%` — essentially a coin-flip at scale. The AVAXUSDT card also carries `_phase1_conf_shadow_reject: confidence=0.700 < 0.8`, i.e. it would fail a stricter phase-1 shadow gate. |

Neither strategy shows empirical validation for its HC label in the 3,500-row closed window. The XRP pick looks strong on card-level metadata (symbol track record WR 70% n=10, SUPER_PICK score 120) but that signal comes from symbol-level stats, not strategy-level realized PnL.

---

## Per-Class Commentary

- **CRYPTO — HC-thin but present.** Only the two picks above clear the gates, both grade-b. The XRP pick is the closest thing to a standout (score 93, conf 0.82, strong per-card forward cohort). The AVAX pick is borderline on every axis.
- **EQUITY — HC-empty despite 10 live picks.** Score compression below 60 is the primary blocker. Worth a look at equity scorer calibration.
- **ETF & BOND — structurally absent.** Zero live picks today. Check whether ETF/BOND emitters ran on schedule.
- **FOREX & COMMODITY — HC-empty, small feeds.** Not enough picks to diagnose.

---

## Caveats (read these before acting)

1. **HC gate is a placeholder.** `evaluate_hc_tier` uses conservative round-number thresholds (score ≥ 60 / ≥ 70, conf ≥ 0.70 / ≥ 0.80, trust in {PROVEN, RELIABLE}). Phase 3 parity test (`tools/hc_parity_test.py`) against `audit_dashboard/hc_filter.js` runs weekly and will shift these thresholds to match the JS source of truth.
2. **Realized HC edge (PF 1.61 / WR 51.6% / n=62) comes from the 2026-04-20 effectiveness audit.** It is not re-derived here. Today's gate produces a smaller candidate set (n=2) than that audit cohort.
3. **No risk-adjusted metrics.** Sharpe / Sortino / regime-conditioned PF are Phase 4 work; rankings here are raw PF and WR.
4. **Small samples.** Every strategy in the top list has n<10 closed trades under the exact `strategy` key used in `picks.recent_closed`. Card-level forward stats (`strat_fwd_wr`, `sym_track_wr`) live in a separate cohort and may overstate edge.
5. **Zero PROVEN-tier picks live** means grade-a is unreachable today regardless of score/confidence. If the operator wants grade-a coverage, the bottleneck is trust-tier promotion, not scorer thresholds.
6. **No peer coordination performed** (MCP bus tools were deferred in this agent context). If a peer is concurrently retuning gates, this snapshot may go stale quickly.
