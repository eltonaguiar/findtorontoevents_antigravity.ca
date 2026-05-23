# Session AU — Swarm Review Request
# Date: 2026-05-17
# Session: AU (following AT — APPROVE)

## Context

Session AU: Post-AT hygiene and audit pass. No new gates or metrics added. Three findings:
(1) CI is fully green, (2) PENDING_UNBLOCK_REVIEW symbols all correctly remain blocked,
(3) WIN_RATE_TRAP_BLACKLIST is dead code — documented and left as-is.

## Session AU Changes

### 1. DYDXUSDT PENDING_UNBLOCK_REVIEW — Data Artifact Documented

**Background:** DYDXUSDT was in PENDING_UNBLOCK_REVIEW with a prior entry citing
WR=93.8%, PF=19.05 (n=16) with a note "remarkable recovery — verify dedup_ratio."

**Audit result:** All 33 closed_picks for DYDXUSDT have `source_system='?'` (unknown source).
- avg_win = +0.02% per winning trade
- avg_loss = -0.02% per losing trade
- WR=90.9%, PF=11.33 are arithmetic artifacts of near-zero PnL, NOT real trading alpha

**Fix:** Updated PENDING_UNBLOCK_REVIEW comment in quality_gates.py:
```python
"DYDXUSDT": "2026-06-30",  # CRYPTO: DATA ARTIFACT — DO NOT PROMOTE (2026-05-17 AU audit).
                           # n=33 in closed_picks; ALL from source_system='?' (unknown source).
                           # avg_win=+0.02%, avg_loss=-0.02% — near-zero PnL, not real trading edge.
                           # WR=90.9%/PF=11.33 are arithmetic artifacts of tiny PnL values, not alpha.
                           # Remains blocked. Re-review only if source_system='?' entries are traced.
```

**Commit:** baf8ea96f2

### 2. WIN_RATE_TRAP_BLACKLIST — Dead Code Documented (Prior Session AU Commit)

**Finding:** `WIN_RATE_TRAP_BLACKLIST` frozenset in quality_gates.py is NEVER checked
in `passes_active_gate()`. The frozenset is defined at line ~1515 but no gate function
reads it.

**Symbols listed:**
- ETHUSDT (quan_engine): WR=33.6%, 143 picks — ALREADY blocked via score gates
- INJUSDT, FETUSDT: appear OK in current data, not actively a problem
- STRKUSDT: trap pattern but blocked by score gate mechanisms

**Fix:** Added docstring comment explaining dead code status and warning not to wire
without re-verifying each symbol's current state. No gate logic changed.
**Commit:** 37e8d0cda6

### 3. PENDING_UNBLOCK_REVIEW Audit — All Overdue Symbols Correctly Blocked

Reviewed all overdue (review date in past) symbols:

| Symbol | Review Date | Current Status | Decision |
|--------|------------|----------------|----------|
| JTOUSDT | 2026-05-01 | WR=30.6%, PF=0.35 (n=18) | REMAIN BLOCKED |
| XLMUSDT | 2026-05-01 | WR=38.3%, PF=0.64 (n=47) | REMAIN BLOCKED |
| ICPUSDT | 2026-05-01 | WR=30.6%, PF=0.40 (n=36) | REMAIN BLOCKED |
| RENDERUSDT | 2026-05-15 | WR=31.1%, PF=0.40 (n=45) | REMAIN BLOCKED |
| NVDA | 2026-05-05 | Data insufficient/blocked | REMAIN BLOCKED |
| DYDXUSDT | 2026-05-30 | DATA ARTIFACT (source='?') | REMAIN BLOCKED (see §1) |

No unblocks warranted from this audit.

### 4. CI Status

GitHub Actions on main: all completed workflows show success. No stale failures,
no chronic cancellations, no recurring failure streaks. Fully green.

## Pending User Approvals (unchanged from AO/AP/AS/AT)

1. **Block `cta_cross_asset_tsmom` for COMMODITY** — WR=12.7%, n=71
2. **`CONCENTRATION_CAP_BY_CLASS = {"COMMODITY": 0.85}`** — CT=F at 65.25% > 60% cap

Both required for COMMODITY MONEY_READY. Deepseek (AT): evidence is overwhelming, safe
to apply without mutation protocol. Still awaiting explicit user approval per CLAUDE.md.

## Asset Class Status (unchanged from AT)

| Class | Verdict | PF | WR | n | Blocker |
|-------|---------|----|----|---|---------|
| CRYPTO | MONEY_READY ✅ | 2.60 | 68.2% | 475 | — |
| COMMODITY | WATCH ⏳ | 2.15 | 60.2% | 354 | concentration_capped (CT=F 65.25% > 60% cap) |
| EQUITY | WATCH ⏳ | 2.04 | 54.2% | 238 | no unblocked strategy with n≥20 |
| ETF | WATCH ⏳ | 2.49 | 67.6% | 74 | no strategy n≥20 in closed_picks |
| FOREX | NOT_READY ❌ | 0.48 | 33.3% | N/A | FOREX_HARD_DISABLE=1 (default) |
| BOND | INSUFFICIENT_DATA | 0.66 | 50.0% | 12 | n too small |

## Questions for Swarm

1. **DYDXUSDT data artifact**: source_system='?' is the artifact origin. Should we add a
   gate that explicitly blocks picks with source_system='?' from ever entering closed_picks,
   or is this handled upstream already?

2. **WIN_RATE_TRAP_BLACKLIST**: The dead code has been documented. Is there any case where
   we'd want to wire it? Current score/trust gates already handle the listed symbols. If the
   answer is "no, it's genuinely dead," should we just delete the frozenset entirely?

3. **PENDING_UNBLOCK_REVIEW overdue symbols**: All 4 overdue symbols (JTOUSDT, XLMUSDT,
   ICPUSDT, RENDERUSDT) have WR 30-38% — well below 50% threshold. All review dates were
   2026-05-01/05-15 and are now in the past. Should we update their review dates to avoid
   false "overdue" alerts, or leave as is to maintain pressure for re-review?

4. **Overall verdict**: Is Session AU APPROVE?

## Verification

- Commits: DYDXUSDT artifact (baf8ea96f2), WIN_RATE_TRAP dead code (37e8d0cda6)
- CI: green on main
- py_compile: OK on quality_gates.py after both edits
- Prior swarm verdicts: AQ/AR/AS/AT all deepseek APPROVE
