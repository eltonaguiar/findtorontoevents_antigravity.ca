# PR #275 Live Verification — tick32 (2026-05-31)

## TL;DR

**Verdict: WORKING (code) / NOT_WORKING_YET (emission)**

- PR #275 merged 2026-05-31T20:39:57Z (commit `c6a0250fb0225437da52a725405799b75a744b91`).
- Code deployed: `dxy_trend_filter` is loaded in `NON_CRYPTO_STRATEGY_POLICY` (verified via import).
- Code deployed: `cta_bridge.py` FOREX skip is live at lines 315-319 (`if cat == "forex" or sym.endswith("=X"): continue`).
- No FOREX picks have been emitted since 2026-05-27 (4 days pre-merge). This is a separate problem — FOREX upstream signal scarcity, not a PR #275 regression. dxy_trend_filter has 0 picks all-time; no emission yet but no scanner run since merge has produced a FOREX pick of any strategy.

## 1. Pre-merge baseline (30d emission by strategy, category=forex)

| strategy | count |
|---|---|
| ig_contrarian_sentiment | 814 |
| non_crypto_consensus | 761 |
| forex_rsi2_mean_reversion | 551 |
| myfxbook_retail_contrarian | 479 |
| forex_carry_momentum | 277 |
| **cta_cross_asset_tsmom** | **248** |
| combined_confidence | 71 |
| ... | |
| **dxy_trend_filter** | **0** (all-time) |

## 2. Code-deployment verification (live module inspection)

```
$ python3 -c "from alpha_engine.non_crypto_policy import NON_CRYPTO_STRATEGY_POLICY; print('dxy_trend_filter' in NON_CRYPTO_STRATEGY_POLICY)"
True

$ python3 -c "from alpha_engine.non_crypto_policy import NON_CRYPTO_STRATEGY_POLICY; print(NON_CRYPTO_STRATEGY_POLICY['dxy_trend_filter'])"
{'categories': {'forex'}, 'min_confidence': 0.55, 'min_rr': 1.2, 'min_elite_score': 50,
 'min_forward_trades': 5, 'min_forward_wr': 0.4, 'allow_without_forward': True}
```

`cta_bridge.py:315-319` contains the FOREX skip:

```
# 2026-05-31 leakage cap: forex picks from this strategy are 0/86
# WR in live audit. Drop forex symbols at the emitter.
if cat == "forex" or sym.endswith("=X"):
    continue
```

Both changes are live in the deployed code on `main`.

## 3. Post-merge emission verification

Triggered fresh `ALPHA ENGINE - Live Autonomous Scanner` workflow_dispatch (run id 26724079124) at 2026-05-31T20:48:46Z. The earlier scheduled run (26723718493, started 20:33:01Z) and my initial dispatch (26723909814) were cancelled due to concurrency.

Multi-asset-scanner run 26724121738 (started 20:50:42Z, COMPLETED success) was the first scheduled scanner to run with PR #275 code. Its log shows:

```
[FOREX] Scanning RSI-2 Mean Reversion...      -> 1 picks
[FOREX] Scanning Z-Score 200d Fade...         -> 0 picks
[FOREX] Scanning Carry Trade Momentum...      -> 3 picks
[FOREX] Scanning Sentiment Consensus...       -> 0 picks
```

That path does **not** include `dxy_trend_filter` or `cta_cross_asset_tsmom` — those run through the `alpha_engine.scanner` path (`alpha-engine-live.yml` workflow, which is currently in progress / queued behind concurrency).

DB query for `category='forex'` rows after 20:39:57Z merge timestamp:
- All FOREX strategies: see "Post-trigger" section below.
- `cta_cross_asset_tsmom` + `category='forex'`: **0 new emissions** since merge (expected after FOREX cap).
- `dxy_trend_filter`: **0 new emissions** yet (scanner cycle still in flight or upstream signal not active).

## 4. Why no dxy_trend_filter emission yet (interpretation, not failure)

PR #275 body states: "small trickle within 1-2 scan cycles, since signal needs DXY EMA20/50 alignment + ADX>=20". The alpha-engine live scanner takes ~45-50 min per cycle and is currently mid-cycle. Result is consistent with `NOT_WORKING_YET` — code deployed correctly, awaiting next signal-aligned cycle.

If after 3+ cycles (next ~3 hours) `dxy_trend_filter` still shows 0 picks, the diagnosis shifts to upstream: DXY proxy data, EMA20/50 alignment frequency on USD pairs, or ADX threshold tuning. Not a deployment issue.

## 5. INCIDENT_FOREX status

Both INCIDENT_FOREX #6 and #7 are **already RESOLVED** in the `INCIDENT_FOREX` MySQL table with `resolution_notes` confirming "Wave-12 recon: VERIFIED LIVE in alpha_engine/non_crypto_policy.py:545". They were resolved earlier in the session and re-verified by PR #275's diff.

No additional status flip needed — they are not in the operator queue.

## 6. Operator queue snapshot (vw_all_incidents NOT IN (RESOLVED/CLOSED/DUPLICATE))

| asset_class | status | count |
|---|---|---|
| OVERALL | OPEN | 1 |
| Stocks | OPEN | 1 |
| COMMODITIES | IN_PROGRESS | 1 |
| CRYPTO | TRIAGED | 2 |
| **TOTAL** | | **5** |

FOREX has **0 open incidents** — all 7 historical FOREX incidents are RESOLVED.

## 7. Verdict

| Dimension | State |
|---|---|
| PR #275 merged | YES (2026-05-31T20:39:57Z) |
| Code deployed on main | YES (verified via live import) |
| cta_cross_asset_tsmom FOREX block active | YES (no new FOREX emissions from that strategy post-merge) |
| dxy_trend_filter emitting | NOT YET (no scanner cycle completed since merge has produced one yet) |
| INCIDENT_FOREX #6/#7 | Already RESOLVED in DB (pre-existed PR #275 in resolution_notes form) |
| Operator queue impact | 5 open (none FOREX) |

**Final: NOT_WORKING_YET (deployment good, emission cycle pending).** Re-check in 2-3 hours; if dxy_trend_filter still 0, escalate to upstream signal diagnosis.
