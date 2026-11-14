# Peer Review — deepAI `audit/live-audit-2026-11-14`

**Verdict: REPRODUCED EXACTLY. Claim is honest but narrower than it reads. Sub-T2.**

## What I did

Fetched their evidence script straight off the branch and ran it, unmodified, against the live
payload the audit reads:

```bash
git show origin/audit/live-audit-2026-11-14:2026-11-14/deepAI_final_audit_20261114_1809/notes/evidence/walkforward_v6.py > walkforward_v6.py
curl -sS -o dashboard_payload.json https://findtorontoevents.ca/audit/data/dashboard_payload.json   # HTTP 200, 34,584,792 bytes
python3 walkforward_v6.py dashboard_payload.json
```

## Result

```
VARIANT C walk-forward: n=237 WR=47.3% PF=1.26 sum=+98.7pp z=-0.84
randomization null: 0/800 = p=0.0000
```

Every number in their document reproduces: n=237, WR 47.3%, PF 1.26, +98.7pp. `p=0.0000` is the
formatter's 4-decimal rendering of 0/800; the correct upper bound is 1/801 = **0.00125**, which is
what they printed as "p<0.0013". That is the right way to report it and they did it right.

**This makes deepAI the only peer whose central numeric claim I could reproduce to the digit.**

## What the result actually means

Three things get lost in the headline:

1. **Their own z is negative.** `z=-0.84` means WR 47.3% is *below* a coin flip and not
   distinguishable from it. The entire PF 1.26 comes from payoff asymmetry (winners larger than
   losers), not from hit rate. A PF carried by asymmetry alone is the most fragile kind — it dies
   the moment the tail win stops recurring.

2. **The null tests selection, not the market.** `random_pick` draws 6 strategies uniformly from
   those with ≥20 trades. Variant C takes the top 6 by prior-month PF. So p<0.0013 answers:
   *"does ranking by prior PF beat random ranking?"* — yes. It does **not** answer *"is there an
   edge in the market?"* And in a pool my own audit found riddled with clone re-emissions
   (`inverse_mutations` = 2,262 re-emissions of three symbols), "best 6 vs random 6" partly
   measures real strategies vs clones.

3. **Resolution limit.** With 800 draws the smallest attainable p is 0.00125. Their Bonferroni over
   4 variants lands at 0.005, which is arithmetically fine — but the test simply cannot resolve
   anything smaller, so "survives Bonferroni" is a weak statement here.

## Credit where due

- They report all four variants A–D with the losers included. That is the behaviour the audit asked
  for and almost nobody else did.
- They explicitly refuse to call it capital-ready: *"PF 1.26 < 1.5 and WR 47.3% < 50% — below T2"*.
- They publish the failure mode themselves: 4 of 8 months negative, July PF 0.50 (−45.9pp), and the
  "alive-only" refinement **failed** (PF 0.80–0.84) — an honest disclosure that the edge depends on
  strategies that stop emitting.
- Sizing is computed honestly (¼ Kelly ≈ 2.5%/trade from WR 47.3%, W/L 1.41).

## Blocking caveats I add

| Issue | Detail |
|---|---|
| **Ledger provenance is absent** | In the live payload, all 3,500 `recent_closed` rows have `resolution_method: None`. You cannot distinguish TP / SL / time exit. Any PF built on it is a PF of unknown exit quality. |
| **Branch is unmergeable** | Based on `f54efb3b4ac` (2026-06-06). Two-dot diff vs `main` = **23,488 files changed, 29.7M deletions**. Not an ancestor of `main`. The analysis is current; the tree is 5 months stale. |
| **Single window** | Feb–Nov 2026 only. No regime-out test is possible, as they state. |
| **In-progress month** | Nov PF 1.72 is a partial month. Their "4 consecutive improving months" leans on it. |

## Recommendation

Accept variant C as a **pre-registered paper pilot**, not an edge:
keep the rule frozen, evaluate monthly, require n≥100 forward, PF≥1.5, WR≥50%, MDD<20% at stated
sizing, kill on 2 consecutive months PF<0.5. Before any of that, fix `resolution_method` so the next
walk-forward can distinguish exit types.
