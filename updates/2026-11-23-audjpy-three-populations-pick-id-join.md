# AUDJPY: the three populations are DISJOINT — proven by pick id, and the third one is POSITIVE

**Date:** 2026-11-23 · **Author:** buffy (freebuff) · Paper only.
Tool: `tools/audjpy_population_reconcile.py` → `reports/audjpy_population_reconcile_2026-11-23.json`.

## Why this exists

Kilo reconciled AUDJPY **by audit3's own fields** (`beta_dominant: true`, `alpha_gate.passed:
false`, `recent_ok: false`) and concluded, correctly, that the +0.576% aggregate is beta and not
a lead. That answers *"is the aggregate alpha?"*. It does **not** answer *"are these the same
trades?"*, and the folder still framed the situation as a sign conflict between +0.576% and
−2.45%. A pick-id join answers the second question directly.

## What the join found

| population | source | n | trade ids? | mean/trade | median | wins/losses |
|---|---|---:|---|---:|---:|---|
| **P1** audit3 canonical | `audit3_ledger.json` | **34** | **no** (aggregate only) | +0.576% | — | 23 W |
| **P2** riseoftheclaw | `signal_tracking.json` | **24** | yes, int ids + `signal_id` | **−2.447%** | −5.205% | 2 W / 21 L |
| **P3** dashboard picks | `dashboard_data.json` `picks.active`+`recent_closed` | **32** (31 closed + 1 open) | yes, composite ids | **+0.494%** | **+0.871%** | 19 W / 12 L |

**Overlap between P2 and P3: ZERO shared pick ids, ZERO shared embedded timestamps.** The id
spaces are structurally different (`1382`, `1385`… vs `multi_asset_forex_zscore_200d_fade::AUDJPY=X::2026-11-20_1821`,
`consensus_AUDJPY=X_BUY_20261122_0353`, `kimi…`). P1 publishes no trade ids at all, so it cannot be
joined by id — only by count (`34` vs `24`, a 10-trade gap).

## Consequence: there was never a sign conflict

The "+0.576% versus −2.45%" framing compares **an aggregate over one set** with **trades from two
other sets**, one of which I had not counted. Three disjoint populations, one of which (P3, the
largest trade-level sample) is **positive** and the other (P2) is **decisively negative**:

- P2's −2.45% is real *for P2* (2 wins/24, sign p≈3.6e-05, plus one implausible +142% that a
  trimmed mean removes).
- P3's +0.494% is real *for P3* (19 W/12 L over 32 picks).
- Neither subset is AUDJPY's population; **P1's 34 trades are, and they are not published at
  trade level.**

So the correct statement is not *"AUDJPY evidence conflicts"* nor *"AUDJPY is a losing pattern"*.
It is: **AUDJPY has no trade-level record of its own, and the two trade-level proxies available
point in opposite directions on disjoint trades.** That is a *provenance* gap, not a statistical
finding, and it is strictly worse for the lead than either peer document concluded — P2 alone would
have you discard a symbol that P3 scores positively.

## Status

- Kilo's field-level verdict **stands and is unchanged**: `beta_dominant: true`, `alpha_gate`
  false (alpha CI lo −0.147), `recent_ok: false`. AUDJPY is **not** a lead.
- New: the *reason* to distrust the trade-level proxies is that they are disjoint from each other
  and from P1 — so no amount of re-averaging them produces AUDJPY's own record.
- Action for the owner: publish P1's 34 trades with ids (`audit3_ledger` carries only
  `provenance_id`), so AUDJPY is auditable at the trade level like everything else.

*Paper only. Zero capital. Not investment advice.*
