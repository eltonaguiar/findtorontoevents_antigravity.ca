# UEPS Active-Gate Fix — Action Plan (2026-05-01)

## Problem

30 UEPS picks (long-horizon EQUITY, magic_formula × piotroski × acquirers, TF=POSITION) sit in `picks.active_raw` but 0 reach `picks.active` (the gated production list).

## Empirical Diagnosis

Instrumented `audit_trail/quality_gates.py:passes_active_gate` against each of the 30 UEPS picks. Rejection breakdown:

| Cause | Count | % | Examples |
|---|---|---|---|
| `non-crypto raw score below active-display floor` (`raw_active_score < 55`) | 19 | 63% | META=19, QCOM=52, V=45, MA=50, PYPL=51 |
| `blocked symbol (data quality issue)` (BLOCKED_SYMBOLS) | 6 | 20% | ADBE, HD, CRM, MSFT, TSLA, NVDA |
| `elite_grade=D hard-blocked` | 4 | 13% | IBM, AVGO, BMY, BA |
| `closed status=SL_HIT` (stale leak) | 1 | 3% | GOOGL |
| `trust_score < 3` | **0** | 0% | (UEPS trust=3 strict-passes; floor is `< 3`) |
| `forward_wr floor` | **0** | 0% | (only triggers `edge_trades >= 20`; UEPS has 0) |

The "no fwd_wr" theory was empirically falsified. The actual blockers are calibrated for short-term strategies: score-55 floor, data-feed BLOCKED_SYMBOLS, and elite_grade short-term-momentum quality bands.

## Decision (3-AI consensus, unanimous)

**Option B**: long-horizon source bypass behind env flag `UEPS_LONG_HORIZON_GATE_BYPASS_ENABLED` (default-OFF, 14-day shadow).

When flag is ON AND `pick.source_system == "ueps"` AND `pick.trade_timeframe == "POSITION"`, skip **four** short-term-calibrated filters:
1. score-55 non-crypto floor (`ACTIVE_DISPLAY_NON_CRYPTO_MIN_RAW_SCORE`)
2. universal score-40 floor (the `score < 40` early-reject at `quality_gates.py:4577`) — discovered empirically: with only filters 1+2+3 bypassed, only 20/30 UEPS picks passed (META=19, IBM=38, AVGO=37, BMY=34, BA=31, XOM=25, AAPL=21 still failed the universal-40 floor). Adding filter 2 got 29/30 through. The universal-40 floor is also short-term-calibrated; bypassing it is consistent with the plan's intent. **Test 8** in `tests/test_ueps_long_horizon_gate_bypass.py` pins this as intentional.
3. BLOCKED_SYMBOLS hard-block (mega-caps blocked for short-term feed/redenomination issues — UEPS 3y horizon is not exposed to those)
4. elite_grade D hard-block (short-term momentum grade)

The gate continues to enforce: trust_score, status (SL_HIT/closed), wf_verdict=FAILING, EXEMPT_FROM_SAFETY_GATES, jpy_cross_buy_kill, healthcare_long_momentum_blacklist, forward_wr_floor, entry_price sanity. Long-horizon picks still must pass real safety checks.

Reviewers (DeepSeek + Cerebras Qwen-235B + xAI Grok-3) unanimously rejected:
- **A** (only score floor) — leaves 33% of UEPS still blocked
- **C** (global TF=POSITION floor drop) — bleeds into short-term strategies
- **D** (separate UI panel) — UI hack, gate still blocks live picks
- **E** (defer until 20+ closed) — chicken-and-egg perpetuated

## Wire-Up Rule Compliance

Flag is **default-OFF**. Production gate behavior unchanged on merge. Operator flips ON after 14-day shadow review (see Canary section below). On flip-on, UEPS picks land in `picks.active`. No new module imports — same gate file, additive code path.

## Implementation

**File**: `audit_trail/quality_gates.py` only.

Add helper near top (after constants):

```python
def _ueps_long_horizon_bypass_active(pick) -> bool:
    """Return True if the UEPS long-horizon bypass should skip
    short-term-calibrated rejecters for this pick. Default-OFF.

    Bypasses score-55 floor, universal score-40 floor, BLOCKED_SYMBOLS,
    and elite_grade D for source_system=ueps + trade_timeframe=POSITION.
    Other safety gates (trust_score, wf_verdict, status, forward_wr_floor)
    still apply.
    """
    if os.environ.get("UEPS_LONG_HORIZON_GATE_BYPASS_ENABLED", "0") != "1":
        return False
    if str(pick.get("source_system", "") or "").lower() != "ueps":
        return False
    if str(pick.get("trade_timeframe", "") or "").upper() != "POSITION":
        return False
    return True
```

Then guard each of the four filters (score-55, universal-40, BLOCKED_SYMBOLS, elite_grade D) with the bypass check.

## Canary (14-day shadow review)

Operator monitors daily after flag flip:
- `picks.active` count where `source_system=ueps` — expected ≤30 (UEPS emits 30/4h, deduped on symbol)
- `picks.active` total count — expected to grow ~30 only; if >+50, rollback
- Closed-trade WR for UEPS once first 20 close — expected ≥45% (Magic-Formula+Piotroski historical baseline)

## Rollback

Flip `UEPS_LONG_HORIZON_GATE_BYPASS_ENABLED=0` (or unset). Gate reverts to current behavior. No PR revert needed.

## Tests (`tests/test_ueps_long_horizon_gate_bypass.py`)

1. **Default-OFF safety**: UEPS POSITION pick with score=19 fails the gate when flag is unset (current behavior preserved).
2. **Bypass-on score**: UEPS POSITION pick with score=19 passes when flag is ON.
3. **Bypass-on blocked symbol**: UEPS POSITION NVDA pick passes when flag is ON; non-UEPS NVDA pick still fails.
4. **Bypass-on elite_grade D**: UEPS POSITION pick with elite_grade=D passes when flag is ON.
5. **Non-UEPS unaffected**: kimi_riseoftheclaw POSITION pick with score=19 unchanged regardless of flag (control).
6. **Status-closed still blocks**: UEPS POSITION pick with status=SL_HIT still rejected when flag is ON (real-safety gate preserved).
7. **Forward-WR floor still enforced**: UEPS POSITION pick with `edge_trades >= 20` and `forward_wr` below the non-crypto floor is still rejected when flag is ON (added per final-reviewer SHIP-WITH-MINOR-EDITS feedback).

## Out of Scope (separate PR)

- Stale GOOGL `status=SL_HIT` leaking into `active_raw` — that's a resolver freshness bug, not a gate bug. File as separate issue.
- UEPS forward_wr backfill (chicken-and-egg) — once flag is flipped on and 20+ UEPS picks close, gate's existing `_effective_forward_wr_ratio` floor kicks in naturally.

## Sequence

This is a **standalone fix** outside the action plan v2 sequence — it unblocks Goal #1 (phenomenal /audit performance) by surfacing 30 long-horizon equity picks the operator already paid to generate via PR #582. ETA: 1 PR, ~50 LOC + tests, ~1 hour.

## References

- `reports/feedback/deepseek-ueps.md` — recommended B
- `reports/feedback/cerebras-qwen-ueps.md` — recommended B
- `reports/feedback/xai-grok-ueps.md` — recommended B
- `audit_trail/quality_gates.py:3808` — `passes_active_gate`
- `audit_trail/quality_gates.py:4400` — non-crypto trust gate
- `audit_trail/quality_gates.py:4406-4417` — non-crypto raw score floor (target #1)
- `audit_trail/quality_gates.py:3903-3905` — BLOCKED_SYMBOLS (target #2)
- `audit_trail/quality_gates.py:4087-4093` — elite_grade D block (target #3)
