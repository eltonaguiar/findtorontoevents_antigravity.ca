# Disagreement Resolution — CONSENSUS_v2 followup turns

- **Run timestamp (UTC):** 2026-05-03T15:48:00Z
- **Method:** session-resume followup turns via `tools/swarm/worker_runner.py --from-session ...`
- **Source disagreements:** `swarm_runs/CONSENSUS_v2.md` §"Disagreement section"
- **Sessions used:** all 3 from `swarm_runs/_sessions.db`; 0 failures
- **Raw answers:** `swarm_runs/_disagree/{etf,bond,forex}.json` + matching `.raw.txt`
- **Prompts:** `swarm_runs/_disagree/_prompt_{etf,bond,forex}.txt`

## Disagreement #1 — ETF edge direction (momentum vs mean-reversion)

**Original positions (CONSENSUS_v2 §ETF):**
- 4/5 (deepseek, kilo, inception, cerebras): cross-sectional 12-mo momentum + vol-parity
- 1/5 (xai): mean-reversion on sector rotation overreaction

**Followup (resumed xai, session `40502e7b…`):** asked xai to defend with a public ETF
paper-trade track record (RSP, MTUM, USMV, AQR factor ETFs) or concede.

**Followup answer (parsed):**
```json
{
  "position": "concede",
  "evidence": "Insufficient forward-only evidence after costs for mean-reversion on sector rotation in ETFs compared to cross-sectional momentum. Current data (n=87, PF=1.24) lacks statistical power to defend against momentum's broader academic and practical support.",
  "public_track": "MTUM (iShares MSCI USA Momentum Factor ETF) demonstrates consistent outperformance with a Sharpe ratio >0.8 over 5+ years, supporting cross-sectional 12-month momentum with vol-parity as a stronger approach.",
  "switch_to": "momentum"
}
```

**Final verdict:** **MOMENTUM CAMP WINS — 5/5 unanimous after concede.**
xai cited MTUM's 5+yr Sharpe>0.8 as the stronger forward-only public track; could not
produce a comparable mean-reversion track. ETF methodology is now uncontested:
cross-sectional 12-month momentum with vol-parity, AQR/S&P-family benchmark,
n>=100 floor.

**Action items:**
- Drop the proposed A/B paper-trade (was the v2 §ETF tie-breaker plan); commit straight
  to momentum-only in the ETF rescue plan.
- Update `audit_dashboard/template.html` MAJOR-GOAL banner ETF row to reference
  MTUM/RSP-style cross-sectional momentum as the target methodology family.
- Reach n>=100 (currently n=87 per dashboard_data 2026-05-03T00:06Z) before promoting
  ETF out of "borderline" status.

## Disagreement #2 — BOND viability with current n=18

**Original positions (CONSENSUS_v2 §BOND):**
- 3/5 (xai, inception, cerebras): yield-curve steepness arb is salvageable; PIMCO BOND benchmark
- 2/5 (deepseek, kilo): no defensible approach; merge to ETF until n>=100

**Followup (resumed deepseek, session `07729506…`):** asked the strongest skeptic
whether n=30 with documented duration-hedge execution + Wilson LB WR>=55% would
flip the verdict from "merge to ETF" to "passive paper trade until n>=100".

**Followup answer (parsed):**
```json
{
  "verdict_holds": true,
  "min_n_to_reopen": 100,
  "required_evidence": [
    "Daily duration-hedge P&L logs with CUSIP-level execution timestamps",
    "Wilson LB on WR >= 55% at n=30 with lower bound > 50%",
    "Rolling 12-month PF >= 1.5 with max drawdown < 10%",
    "Independent replication by second engine on same data feed"
  ]
}
```

**Final verdict:** **STILL SPLIT — but the operational gate is unanimous.**
deepseek did NOT concede; verdict still "merge to ETF" until n>=100. Importantly though,
the *required-evidence* bundle deepseek demands (Wilson LB on WR>=55% at n=30 with
LB>50% AND PF>=1.5 over rolling 12mo AND independent replication) is the same gate
the 3-engine yield-curve camp would need to pass to claim edge anyway. So **operationally
the two camps converge on the same next step**: passive data-collection ONLY, no live
sizing, until n>=100. 3 engines (xai/inception/cerebras) get to design the hypothesis,
2 engines (deepseek/kilo) get the veto on live deployment.

**Action items:**
- BOND class is **paper-only / passive** for at least 90 days. No live sizing.
- Implement duration-hedge execution logging (CUSIP-level timestamps) as a prerequisite,
  per deepseek's required-evidence list.
- Tag yield-curve steepness arb as the *candidate* hypothesis (per the 3-engine majority)
  but do NOT promote past paper until all 4 evidence items pass.
- Re-poll the swarm at n=30 milestone; deepseek explicitly retains veto authority.

## Disagreement #3 — FOREX dragger handling: kill vs mutate

**Original positions (CONSENSUS_v2 §Q2 30d):**
- 2/5 (deepseek, cerebras): direct kill — after-cost is already net negative on n>500
- 3/5 (xai, inception, kilo): mutate-then-kill per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`

**Followup (resumed kilo, session `64ada602…`):** asked the most detailed mutate-first
proponent to commit to 3 specific mutations AND a hard kill criterion AFTER those fail.

**Followup answer (parsed):**
```json
{
  "mutations": [
    {"axis": "param",     "proposal": "Shift RSI period 2->3-4 and threshold ±1.5σ->±1.2σ; add volatility filter ATR>0.6% to skip choppy regimes"},
    {"axis": "symbol",    "proposal": "Restrict to G10 majors (EURUSD, USDJPY, GBPUSD) only; eliminate EM pairs to reduce spread+slippage drag"},
    {"axis": "polarity",  "proposal": "Invert entry polarity (flip long->short/sell->buy on RSI <30/>70); add 4h trend-confluence filter (EMA20>EMA50 for longs, reverse for shorts)"}
  ],
  "kill_after": "Reject if after-cost net <= -10% OR PF < 1.2 on n>=200 post-mutation trades; eliminate if Wilson LB < 50% OR Sharpe < 0.5",
  "budget_trades": 400
}
```

**Final verdict:** **MUTATE-FIRST WINS — by repo policy + concrete plan.**
Project policy (`docs/MUTATION_THREE_AXIS_PROTOCOL.md` + `STRATEGY_INVESTIGATION_BEFORE_KILL.md`)
already mandates mutate-first; the v2 split was the panel ignoring policy. kilo's
3-mutation bundle covers all three axes (param, symbol, polarity) and gives the
direct-kill camp what they need: a hard, time-boxed exit criterion (n>=200 post-mutation,
PF<1.2 OR after-cost ≤ -10% OR Wilson LB<50% OR Sharpe<0.5; total budget 400 trades).

**Action items:**
- Implement kilo's 3 mutations as forex_rsi2_mean_reversion variants in
  `alpha_engine/` (track via mutation analysis CSV per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`).
- Hardcode the kill-after criterion as an automated gate (per `feedback_halt_flag_must_be_hardcoded.md`):
  on hit, refuse new fills, do not just log.
- Trade budget: 400 trades total across all 3 mutations; ~133/mutation. Run sequentially
  (param → symbol → polarity) so each mutation gets its own n>=100 sample before stacking.
- Apply same mutate-first protocol to the other two FOREX draggers (`forex_carry_momentum`,
  `unknown` source). For `unknown`, the prerequisite is source attribution (per CONSENSUS_v2
  risk register: "Trace each unknown trade to source API; reclassify within 7 days").

## Sessions failed

**0 failed.** All three session-resume calls returned valid structured JSON on the first
attempt. No engine-down events, no parse fallbacks, no expired sessions.

## Net new action items for the swarm operator

1. **ETF (now unanimous):** commit to cross-sectional momentum + vol-parity; drop the
   A/B paper-trade plan. Wait for n>=100 (currently n=87) before public promotion.
2. **BOND (operationally aligned):** lock to paper-only / passive collection for 90 days;
   stand up duration-hedge CUSIP-level logging; re-poll the swarm at n=30 milestone.
3. **FOREX (mutate-first locked in):** implement kilo's 3 mutations on
   `forex_rsi2_mean_reversion`; hardcode kill-after gate; budget 400 trades total
   (133/mutation, sequential). Apply same protocol to `forex_carry_momentum` and
   `unknown` (after source attribution).
4. **Hardcode automation:** the kill criteria from disagreements #1 and #3 must be
   enforced in code, not just documented (per `feedback_halt_flag_must_be_hardcoded.md`
   and CONSENSUS_v2 90d milestone "Codify and AUTOMATE kill-rules").
5. **Update CLAUDE.md MAJOR GOALS section** ETF row from "borderline" with no
   methodology to "borderline (n=87→100); methodology = MTUM-style cross-sectional
   12-mo momentum with vol-parity per swarm v2 + xai concede 2026-05-03".
