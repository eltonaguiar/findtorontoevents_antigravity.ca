# VERIFY: COMMODITY LONG MC SL/TP claim — REFUTED

**Date:** 2026-05-31
**Verifier:** peer_claude (opus-4.7)
**Claim source:** kilo transcript — "COMMODITY LONG SL -0.5% / TP +5.7% → PF 4.43, WR 19.15%"

## Verdict: REFUTED with multiple methodology red flags

| Metric | Claimed (kilo) | My replication (capping) | Raw (no cap) |
|---|---|---|---|
| n | (not stated) | 440 | 440 |
| WR | 19.15% | **45.00%** | 45.00% |
| PF | 4.43 | **3.561** | **0.685** |

**Neither WR nor PF matches.** PF 3.56 is closer to the claim than FOREX SHORT case, but the **raw PF is 0.685 — a money-loser**. The "PF 3.56" only appears via the cap-as-truth fiction.

## Independent replication query
`category='COMMODITY' AND direction='LONG' AND closed_at IS NOT NULL`, capped at [-0.5, +5.7]:
- n=440 (198 wins / 207 losses / 35 zero-pnl)
- WR 45.00%, PF_capped 3.561
- Raw avg win 1.18%, raw avg loss −1.64% → **raw PF 0.685 (losing strategy)**

## Red flag #1 — Methodology is capping, NOT intrabar replay

Same fatal flaw as FOREX SHORT case. Capping pnl at [-0.5, +5.7] **assumes every trade that ever touched +5.7% locked in +5.7%**, ignoring that intrabar a tighter SL would have been hit first by the same volatility. Memory `reference-sl-optimization-needs-pricepath` already proved this session: tightening SL collapses PF via whipsaw — opposite of the capped estimate. Cannot trust without OHLC replay.

## Red flag #2 — Extreme concentration (worst yet)

**Top-3 symbols = 96.0% of all winning trades.**
- HG=F (copper) 100 wins (50.5% of all wins)
- PL=F (platinum) 49 wins
- SI=F (silver) 41 wins

HG=F alone (n=204): WR 49% / PF_capped 7.63, but **raw avg pnl +0.04%** — i.e. the capped PF is almost entirely a winsorization artifact. This is not a portfolio strategy; it is a copper-vol-clipping artifact.

## Red flag #3 — WR mismatch suggests different denominator

Claimed 19.15% WR vs measured 45%. The only way to get ~19% is if kilo:
- counted only capped-at-+5.7 trades as "wins" (i.e. trades that actually hit the TP cap), excluding partial wins below 5.7%
- and/or filtered to a sub-cohort (single source, single symbol) not stated

Without kilo's exact query the 4.43 PF is unreproducible. The 19.15% WR strongly implies "fraction of trades that fully reached +5.7% TP cap" — which is **NOT a valid WR definition** for evaluating an SL/TP regime.

## Red flag #4 — cta_replicator survivorship

cta_replicator contributes 85/440 rows. PR #182 era retired losing cta strategies. Excluding cta_replicator: n=355, WR 42.82%, PF_capped 1.695 — even the capped fairy-tale PF collapses to sub-T2 once survivorship is purged.

## Verdict

**REFUTED.** PF 4.43 / WR 19.15% is unreproducible from live trading_picks. Closest plausible source is a winsorized + symbol-filtered + arbitrary-denominator computation on a single instrument (HG=F copper), which under raw pnl loses money (PF 0.685) and concentrates 96% of wins in 3 contracts. Do not size up COMMODITY LONG on this MC — same intrabar-replay requirement as every other SL/TP claim this session.

## Recommended action

1. Reject any genome promotion based on this MC.
2. Require OHLC intrabar replay (see `tools/sl_optimization_pricepath.py` pattern) before any commodity SL/TP tuning.
3. Open INCIDENT on monte-carlo harness if it computes WR as "fraction reaching TP cap" — that is a labeling bug.
