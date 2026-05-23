# multi_asset_copytrader Per-Class Audit — 2026-05-13T01:40Z

**Spec:** AA-2 follow-up to peer Big Pickle's "best go-live candidate" claim.
**Subagent:** cavecrew-investigator `a4a7d4aa692a6c056` decomposed 943
closed_picks rows by asset_class.

## Headline numbers vs decomposed reality

Dashboard payload: `multi_asset_copytrader` PF=4.28 / WR=47.3% / n=1505 /
MDD=16.67% spanning COMMODITY+EQUITY+FOREX+FUTURES.

**Per-class breakdown from `alpha_engine/data/closed_picks.json`:**

| Class | n | WR % | volume share | Status |
|---|---|---|---|---|
| **COMMODITY** | 96 | **93.8** | 6.4% | ✅ Real edge — pristine WR |
| EQUITY | 28 | 42.9 | 1.9% | ⚠️ thin (n<100) |
| **FOREX** | 662 | **14.8** | 44.0% | ❌ Massive drag |
| **FUTURES** | 157 | **2.5** | 10.4% | ❌ Critical drain |

(Remaining ~37% volume = active/open, not yet resolved)

## Peer Big Pickle claim FALSIFIED

Peer's hidden insight #3 (DAILY_IDEAS.MD via open-code session):
> "multi_asset_copytrader is your most robust system — PF 4.09, n=812,
>  MDD 16.67%, spans 5 classes. Best candidate for go-live TODAY."

**Wrong on multiple counts:**

1. **Spans 3 classes**, not 5 (COMMODITY + EQUITY + FOREX in dashboard; closed-picks shows FUTURES too)
2. **NOT go-live ready** — 44% of resolved-pick volume comes from FOREX
   with 14.8% WR. Active-trading those picks would be catastrophic.
3. **System's true edge is COMMODITY-only**, identical to
   `multi_asset_cot` finding from this session's concentration audit.
   The COMMODITY 93.8% WR sub-system is what's driving the PF=4.28
   aggregate; the FOREX/FUTURES drag is masked by COMMODITY's tail wins.

This is **exactly** the FOREX-leak concern peer raised on multi_asset_copytrader
materialized — and dramatically worse than expected.

## Surgical action — mutate-before-kill protocol

Per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` + memory `[Mutate Before Kill]`:

### FUTURES — straight surgical block

`(FUTURES, multi_asset_copytrader)` should be added to
`audit_trail/quality_gates.py::BLOCKED_ASSET_STRATEGY_PAIRS`:
- n=157 with 2.5% WR is empirically dead
- FUTURES class as a whole is silent-dead per memory `project_futures_kill_without_replacement`
- NOT a FOREX-mutation case; clear kill

### FOREX — must run mutate-before-kill

`(FOREX, multi_asset_copytrader)` requires investigation first:
- 662 picks @ 14.8% WR could be:
  - Symbol-specific drag (some currency pair is the worst part)
  - Direction-specific drag (all LONGs lose; SHORTs may be fine)
  - Timeframe-specific drag (intraday vs overnight)
- Run `python tools/mutation_analysis.py --strategy multi_asset_copytrader --class FOREX`
- IF mutation-axes confirm class-wide failure → add to BLOCKED_PAIRS
- IF one axis profitable → preserve that subset

### COMMODITY — preserve + audit further

COMMODITY 96 @ 93.8% WR is the legitimate edge. Cross-check:
- Is this the same CT=F that drives the broader class concentration?
- Or does multi_asset_copytrader trade non-CT=F commodity instruments
  with the same hit-rate?
- Symbol-level audit pending (uses A3 cron output once landed).

## Cross-system note: this PATTERN is the actual hidden insight

Peer's two-regime thesis (trend-follow vs pattern-recog) is real, but
the bigger pattern visible from this audit:

> **Multi-class systems are aggregate-misleading. Class-level decomposition
> is the only honest read.**

This applies to:
- `multi_asset_copytrader` (just audited — false robust)
- `signal_validation` PF 4.31 spans CRYPTO+FOREX — needs same audit
- `copy_trader_intel` PF 1.84 spans COMMODITY+CRYPTO — needs same audit
- `multi_asset` PF 0.30 spans COMMODITY+FOREX — already class-quarantined by peer freebuff

The supreme plan's "go-live candidate" surface should be **per-class-decomposed-system** not raw-aggregate-system.

## Updated rankings — non-aggregate Tier-2 candidates

After this audit, the only confirmed clean per-class edge candidates are:

| (Class, System, n, WR) | Status |
|---|---|
| (COMMODITY, multi_asset_cot, 102, 94.1%) | Tier-1-PF candidate — DB-verify pending NS-A |
| (COMMODITY, multi_asset_copytrader, 96, 93.8%) | Tier-1-PF candidate — confirmed |
| (CRYPTO, aggregated_picks, 404, 73.2%) | Fails T2 MDD cap (49.25%) |
| (CRYPTO, copy_trader_intel, 690, 50.0%) | T2 MDD ✓ but PF<2 |

**Three of four candidates are concentrated in COMMODITY (CT=F).** The
COMMODITY sleeve is the strongest single bet across the entire dashboard.

## Net effect on supreme plan

Add 2 new actions:

| ID | Action | Effort | Priority |
|---|---|---|---|
| AA-6 | Block `(FUTURES, multi_asset_copytrader)` in quality_gates | 0.5h | P0 |
| AA-7 | Run mutation-axes analysis on `(FOREX, multi_asset_copytrader)` 662 picks | 2h | P1 |

Downgrade:
- Peer Big Pickle hidden insight #3 → FALSIFIED. multi_asset_copytrader
  is NOT a single-system go-live candidate. Its COMMODITY subset IS.

## NFA

Audit only. No DB writes. AA-6 block can ship per protocol — FUTURES
class is already known dead; this surgical add does not require
mutate-before-kill (FOREX/COMMODITY-only carve-out per memory).
