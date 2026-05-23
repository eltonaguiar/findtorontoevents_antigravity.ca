# CRYPTO Tuesday DOW Analysis — 2026-05-16

## Verdict: Claim REFUTED — Gate NOT Implemented

**Claim in `FOOLPROOF_ACTION_PLAN.md` (L115):** "Tuesday has +18% WR lift due to institutional flow patterns."

**Actual data: Tuesday WR = 24.7% vs overall CRYPTO WR = 20.2% → +4.4pp lift.**

The claim overstates the effect by ~4×. The +18% figure has no basis in `closed_picks.json`.

---

## Data

- **Source:** `alpha_engine/data/closed_picks.json`
- **Filtered to:** `asset_class == 'CRYPTO'`
- **Win condition:** `outcome == 'WIN'` OR `pnl_pct > 0.05` (matching existing gate logic)
- **n total (parseable):** 6,677 | **skipped (no timestamp / parse error):** 207

### Day-of-Week Breakdown

| Day       |    n | Wins | Losses |    WR | 95% CI (Wilson)    | vs Overall |
|-----------|-----:|-----:|-------:|------:|--------------------|------------|
| Monday    |  582 |  112 |    470 | 19.2% | [16.2%, 22.6%]     | −1.0pp     |
| **Tuesday**| **604** | **149** | **455** | **24.7%** | **[21.4%, 28.3%]** | **+4.4pp** |
| Wednesday |  859 |  119 |    740 | 13.9% | [11.7%, 16.3%]     | −6.4pp     |
| Thursday  |  710 |  103 |    607 | 14.5% | [12.1%, 17.3%]     | −5.7pp     |
| Friday    | 1106 |  202 |    904 | 18.3% | [16.1%, 20.6%]     | −2.0pp     |
| Saturday  | 1602 |  397 |  1,205 | 24.8% | [22.7%, 27.0%]     | +4.5pp     |
| Sunday    | 1214 |  269 |    945 | 22.2% | [19.9%, 24.6%]     | +1.9pp     |
| **Overall** | **6677** | **1351** | **5326** | **20.2%** | — | — |

### Source-System Breakdown (CRYPTO only, n ≥ 50)

| Source          |    n | Overall WR | Tuesday WR | Tue delta | Tue n |
|-----------------|-----:|-----------:|-----------:|----------:|------:|
| quan_engine     | 5896 |      20.7% |      26.3% |    +5.6pp |   521 |
| unknown         |  778 |      16.8% |      14.5% |    −2.4pp |    83 |

---

## Decision

**Gate NOT implemented.** Both decision-rule thresholds are evaluated:

| Threshold | Required | Actual | Pass? |
|-----------|----------|--------|-------|
| Tuesday WR ≥ 5pp above overall | +5pp | +4.4pp | **FAIL** |
| Tuesday n ≥ 100 | 100 | 604 | PASS |

Tuesday misses the ≥5pp threshold by 0.6pp. The Wilson 95% CI [21.4%, 28.3%] overlaps heavily with neighboring days (Saturday [22.7%, 27.0%], Sunday [19.9%, 24.6%]), confirming no statistically distinct "Tuesday effect" — Saturday is virtually identical in WR.

**The two genuinely bad days are Wednesday (−6.4pp) and Thursday (−5.7pp)**, both already captured in `_DOW_KILL["CRYPTO"]` in `audit_trail/quality_gates.py` (L5022), from the 2026-05-11 Kimi audit.

---

## What the Claim Got Wrong

The FOOLPROOF_ACTION_PLAN.md claim of "+18% WR lift" appears to conflate:
1. The absolute Tuesday WR (24.7%) with a percentage-point delta — these are not the same thing.
2. Possibly a stale, unfiltered subsample (pre-resolver-v2 noise filter) that inflated apparent Tuesday volume.

The `quan_engine` subsystem (88% of CRYPTO volume) shows +5.6pp on Tuesday, just over the gate threshold — but the `unknown` source (12% volume) shows −2.4pp Tuesday drag, pulling the blended delta below the floor.

---

## Existing Gate Already Covers the Real Signal

`audit_trail/quality_gates.py` line 5021–5024:
```python
_DOW_KILL = {
    "CRYPTO": {"Monday", "Wednesday"},  # worst 2 days from Kimi audit 2026-05-11
    "MEMECOIN": {"Saturday"},
}
```

Wednesday (13.9% WR, −6.4pp) and Thursday (14.5% WR, −5.7pp) are the real outliers. The existing gate handles Wednesday. **Thursday is not yet in `_DOW_KILL`** — that is a better candidate for future investigation (n=710, −5.7pp below average, outside the 95% CI of Tuesday/Saturday/Sunday).

---

## Recommendation

1. **Do not add a Tuesday gate** — data does not support it.
2. **Remove the Tuesday claim from FOOLPROOF_ACTION_PLAN.md** (L115 and L196) to avoid future agents wasting time on it.
3. **Consider adding Thursday to `_DOW_KILL["CRYPTO"]`** in a future PR — but only after verifying it holds on the post-resolver-v2 `asset_class_health` numbers and on the `quan_engine` subsystem specifically (n=710 total, sufficient sample).
4. **Saturday is effectively tied with Tuesday** (24.8% vs 24.7%) — the "institutional flow" narrative has no basis; the weekend lift is more consistent than any weekday signal.

---

*Analysis run: 2026-05-16. Source: `alpha_engine/data/closed_picks.json`, n=6,677 CRYPTO picks with parseable timestamps.*
