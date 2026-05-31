# Tick 33 — EQUITY UN-KILL `stocks_rsi2_pullback`

**Date:** 2026-05-31
**Author:** claude-opus-4.7 (tick 33)
**Goal:** Surface Goal #1 — un-kill the best EQUITY P(T2) candidate per Phase 3 MC.
**Ground truth:** PR #276 (verbatim COMMODITY+EQUITY structure map).

---

## Context

- PR #270 deep-dive: EQUITY n=1424 outcomes, WR 42.1%, PF 0.39 — FAIL.
- Phase 3 MC: `stocks_rsi2_pullback` P(T2)=52% at n=100 (best EQUITY candidate).
- Session memory (project-money-ready-2026-05-31): killed prematurely at n=10 on 2026-05-28.
- INCIDENT_STOCKS #3: claim that `production_scanner` doesn't route EQUITY. Per PR #276 §B.6 the verdict is NUANCED — scanner.py:2070-2071 routes EQUITY; production_scanner is a post-emission gate, not a dispatcher. So there is **no routing gap** that blocks an un-kill — the kill switch is purely the blacklist.

## Diff

`alpha_engine/config.py:269-271` — remove blacklist entry for `stocks_rsi2_pullback` and replace with un-kill audit trail. Smallest possible diff (1 logical line removed, 4 comment lines added).

### BEFORE (verbatim, was lines 269-271)
```
    'genome_mutations',          # 6 trades, 0% WR, -107% PnL — mutation engine not working
    'stocks_rsi2_pullback',      # 10 EQUITY trades, WR 30%, PF 0.032 — catastrophically bad
    'multi_asset_scanner',       # FOREX n=11 WR 9.1%, FUTURES n=11 WR 9.1% — universal loser
```

### AFTER
```
    'genome_mutations',          # 6 trades, 0% WR, -107% PnL — mutation engine not working
    # 2026-05-31 (tick 33): stocks_rsi2_pullback UN-KILLED — was killed at n=10 (premature per Phase 3 MC P(T2)=52% @ n=100).
    # Definition lives at copy_trader_intel/multi_asset_copytrader_scraper.py:1247 (scan_stocks_rsi2_pullback) and is dispatched
    # via scan loop at line 2480. quality_gates.py:2791 block already removed 2026-05-19 (WR 50.7% @ n=73 cleared 45% floor).
    # Re-kill trigger: WR<40% on next 30 resolved picks. Mandatory review: 2026-06-15 or n_resolved>=30 post-unkill.
    'multi_asset_scanner',       # FOREX n=11 WR 9.1%, FUTURES n=11 WR 9.1% — universal loser
```

## Self-Red-Team

| Check | Result |
|---|---|
| BEFORE block byte-for-byte match | PASS — Read file:269-271 verbatim, matches PR #276 §B.7 quote |
| `py_compile alpha_engine/config.py` | PASS |
| `import config` + `'stocks_rsi2_pullback' in BLACKLISTED_STRATEGIES` | PASS → `False` (was True) |
| `BLACKLISTED_STRATEGIES` length 14 → 13 | PASS (1 entry removed) |
| Strategy definition exists post-unkill | PASS — `copy_trader_intel/multi_asset_copytrader_scraper.py:1247 def scan_stocks_rsi2_pullback`, called at line 2480 |
| Other blockers cleared | quality_gates.py:2791 already commented out 2026-05-19. production_scanner.py:384 is only a boost-set comment (not a block) |
| Routing-gap check (INCIDENT_STOCKS #3) | NUANCED — scanner.py:2070 routes EQUITY (no gap); production_scanner is gate-layer. Un-kill is sufficient. |

## Re-kill triggers (codified in the new comment)

- WR < 40% on next 30 resolved post-unkill picks → re-add to BLACKLISTED_STRATEGIES.
- Mandatory review date: 2026-06-15 OR when n_resolved >= 30, whichever is later.

## Out-of-scope (intentionally not touched)

- Did NOT re-add to `_BOOSTED_NON_CRYPTO_STRATEGIES` (production_scanner.py:383). Un-kill should clear the floor first under default (non-boosted) conf weights before any 1.2x boost is re-introduced.
- Did NOT add new policy gate in `non_crypto_policy.py` — strategy uses default policy (per PR #276 §B.5 it never had a standalone policy entry).
- Did NOT touch INCIDENT_STOCKS #3 routing claim — per PR #276 §B.6 the framing is wrong, the dispatcher (scanner.py:2070-2071) already routes EQUITY. Treating that incident as a separate plumbing PR.

## Return signal

`EQUITY:rt=P:PR=<pending>:merged=<pending>:routing_gap=false`
