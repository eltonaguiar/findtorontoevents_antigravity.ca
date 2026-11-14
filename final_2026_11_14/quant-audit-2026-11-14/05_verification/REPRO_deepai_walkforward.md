# Verification — deepAI Variant C Reproduction

**Question:** does `n=237 / WR 47.3% / PF 1.26 / +98.7pp / p<0.0013` reproduce on the live payload?

**Answer: yes, to the digit.** This is the only peer profitability claim in the round that I could
reproduce, and it reproduces exactly.

## Method (verbatim peer code, live data)

```bash
cd /tmp/peercheck
git -C /home/eaguiar2015/findtorontoevents_antigravity.ca \
    show origin/audit/live-audit-2026-11-14:2026-11-14/deepAI_final_audit_20261114_1809/notes/evidence/walkforward_v6.py \
    > walkforward_v6.py
curl -sS -o dashboard_payload.json https://findtorontoevents.ca/audit/data/dashboard_payload.json
python3 walkforward_v6.py dashboard_payload.json
```

- `curl`: HTTP 200, **34,584,792 bytes**
- runtime: 5.5 s
- script unmodified (copy kept here as `walkforward_v6.py`)

## Output

```
VARIANT C walk-forward: n=237 WR=47.3% PF=1.26 sum=+98.7pp z=-0.84
randomization null: 0/800 = p=0.0000
```

## Reconciliation with the peer document

| Metric | Peer doc | My run | Match |
|---|---|---|---|
| Forward trades | 237 | 237 | ✅ |
| Win rate | 47.3% | 47.3% | ✅ |
| Profit factor | 1.26 | 1.26 | ✅ |
| Total P/L | +98.7pp | +98.7pp | ✅ |
| Randomization p | <0.0013 | 0/800 → ≤1/801 = 0.00125 | ✅ (correctly reported bound) |
| z | not reported | **−0.84** | ⚠️ peer omitted it |

The peer's `p<0.0013` is the mathematically correct upper bound for 0 exceedances in 800 draws.
Their document does **not** print `z=-0.84`; that is the number showing the win rate is *below* a
coin flip. Its omission changes the reader's impression of the result, and is the one fair criticism
of the reporting.

## Payload provenance (independent of the peer)

| Property | Measured |
|---|---|
| `picks.recent_closed` rows | 3,500 |
| numeric `pnl_pct` | 3,500 (100%) |
| exact `0.0` pnl | **11 (0.3%)** |
| status distribution | LOST 2,043 · WON 1,446 · CLOSED 11 |
| `resolution_method` | **`None` for all 3,500** |
| date range | 2026-02-21 → 2026-11-14 |

Two consequences:

1. **The `recent_closed` ledger is much cleaner than `active_raw`.** Only 0.3% zeros here, versus the
   78.6% zombie rate in `active_raw`. So deepAI did not accidentally build a walk-forward on
   fabricated zeros — good.
2. **But exit provenance is absent.** With `resolution_method: None` on every row, a "win" could be a
   take-profit, a stop that gapped favorably, or a time exit that happened to be green. PF 1.26 is a
   real measurement of *something*; nobody can currently say what.

## What this reproduction does and doesn't license

- **Does:** confirm the peer's arithmetic and that the selection procedure beat its own random
  baseline on this sample.
- **Doesn't:** establish market edge (the null tests selection, not prices), or T2 status (PF 1.26 <
  1.5, WR 47.3% < 50%), or capital readiness. The peer says all three themselves.

## Note on merge-ability

`audit/live-audit-2026-11-14` is based on `f54efb3b4ac` (2026-06-06). Two-dot diff against `main`:
**23,488 files changed, 1,138,311 insertions, 29,754,980 deletions**. It is not an ancestor of
`main`. The analysis must be extracted as files, not merged as a branch.
