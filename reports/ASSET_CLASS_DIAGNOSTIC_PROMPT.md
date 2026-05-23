# Asset-Class Diagnostic Prompt — minimal, per-class

A bare-minimum prompt to hand an AI agent (or a swarm SMART-tier model) so it
can diagnose why one asset class's picks are not tradeable and prescribe the
path to a world-class system. Replace `{ASSET_CLASS}` and `{CLASS_FACT}`.

Use the SMART tier only (`swarm_models.smart_endpoints()`) — this demands
numeric reasoning. Per `reports/swarm_model_test_*.md`: deepseek, xai-grok,
openrouter, kimi, mistral.

---

## THE PROMPT (copy, fill the 2 placeholders)

```
You are a senior quant auditing one asset class of a multi-asset signal
system. Be blunt. No generic trading-blog advice. Every claim names the
number or file it rests on.

ASSET CLASS: {ASSET_CLASS}
CLASS FACT: {CLASS_FACT}

GROUND TRUTH (do not re-litigate):
- The verdict gate is tools/edge_stability_harness.py :: is_admissible() —
  a signal is real ONLY if eff>=0.30, SAME SIGN, >=3 of 5 walk-forward
  windows. Win-rate / profit-factor / Sharpe / DSR / White's-SPA passing is
  necessary but NOT sufficient — every one of those has been fooled here.
- 10 candidates across all classes were already KILLED by that harness
  (technicals, COT, ml_enhanced 149-variant sprawl, qlib factors, regime,
  roll-yield, 2s10s slope, funding-rate directional, PEAD, funding-arb,
  options-flow, on-chain). All failed identically: in-sample separation
  that does not hold a stable SIGN out-of-sample. Do NOT re-propose these.
- The pick ledger is alpha_engine/data/closed_picks.json; filter by
  asset_class. Money posture is paper-only.

ANSWER 4 QUESTIONS, each with concrete evidence:
1. WHY DO {ASSET_CLASS} PICKS SUCK — name the 2-3 STRUCTURAL reasons (not
   symptoms) this class has profit factor near 1 and no harness-admissible
   edge. Tie each to a measurable artifact (a source, a metric, a bias).
2. WHAT IS SALVAGEABLE — is there ANY sub-slice (a strategy, a regime, a
   symbol cohort) with a real, leakage-free signal — or is the honest answer
   "do not trade this class"? Say which.
3. THE FIX TO WORLD-CLASS — the single highest-EV change. It must be: free
   data, implementable, and end in a falsifiable acceptance test phrased as
   a harness gate (eff>=0.30, same sign, >=3/5 windows) PLUS a post-cost
   survival check (net edge >= 60% of gross after fees+slippage).
4. KILL-OR-KEEP — given 10 prior kills and this class's numbers, your honest
   probability (%) that {ASSET_CLASS} ever produces a real retail edge.

SELF-AUDIT: name the 2 weakest claims in your own answer and what evidence
would overturn each. ~600-900 words.
```

---

## Per-class `{CLASS_FACT}` (one line each — the only class-specific input)

| `{ASSET_CLASS}` | `{CLASS_FACT}` |
|---|---|
| CRYPTO | PF ~1.25-1.28 net, WR ~44.6%, n~8000. Headline edge was the ml_enhanced 149-variant curve-fit sprawl (family PF 0.63); `confidence` inverts above 0.85; 5/30 active symbols carry opposing-direction picks. |
| EQUITY | PF ~0.72 net — a deep loser. PEAD/SUE was built and harness-killed (sign-unstable 3+/2−). Classic factor edges are zero-sum vs HFT/institutional flow at retail latency. |
| FOREX | PF ~0.33 — catastrophic, worse than random. FOREX_HARD_DISABLE active. LONG side is the drag (29% WR); SHORT showed transient edge but did not survive walk-forward. |
| COMMODITY | PF ~1.17 net. Apparent edge was ~49% CT=F (cotton) — COT-publication look-ahead leakage, falsified. Roll-yield z-score harness-killed (sign-unstable 4+/2−). |
| ETF | Borderline; n often <100. 12-1 cross-sectional momentum is the academically-grounded untested candidate — must run CPCV-by-quarter, ex-microcap. |
| BOND | n~18 — below any statistical-power floor. 2s10s slope-momentum harness-killed (sign-unstable 144+/182−). Term-premium is the only untried angle; needs prime-broker feeds. |

---

## Why this prompt is "bare minimum"

It carries exactly four things and nothing else: (1) the verdict gate, so the
agent cannot pass off a gaudy PF as edge; (2) the kill list, so it does not
waste the answer re-proposing dead families; (3) the ledger path, so it can
ground claims; (4) one class-specific fact line. Everything else (roles,
formatting boilerplate, persona padding) is cut — a SMART-tier model does not
need it, and extra context dilutes the numeric discipline. Fan it to the
SMART set; the harness gates whatever it proposes.
