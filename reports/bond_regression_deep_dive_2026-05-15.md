# BOND Asset Class Regression — Deep Dive (2026-05-15)

## Context

External evaluation cited BOND at PF 1.72 / WR 55.6% / n=18 (~2026-04-22 snapshot). Current `audit_dashboard/data/dashboard_data.json` (origin/main blob `b1e976ba998`) reports BOND at **PF 0.66 / WR 54.5% / n=11**. Period-over-period swing of -1.06 PF flagged as the only material regression across 6 asset classes during validation work on PR #1044.

## Raw data — 12 closed BOND picks on current main

| # | Symbol | Entry | Exit | pnl_pct | Status |
|---|---|---|---|---|---|
| 1 | TLT | 86.26 | 86.26 | -0.00 | UNRESOLVED |
| 2 | TLT | 87.24 | 86.31 | -1.07 | LOST |
| 3 | HYG | 79.20 | 79.55 | +0.44 | WON |
| 4 | HYG | 79.17 | 79.76 | +0.75 | WON |
| 5 | TLT | 87.01 | 87.50 | +0.56 | WON |
| 6 | HYG | 79.50 | 79.18 | -0.40 | LOST |
| 7 | TLT | 86.92 | 87.26 | +0.40 | WON |
| 8 | TLT | 87.64 | 86.92 | -0.82 | LOST |
| 9 | TLT | 88.28 | 88.40 | +0.13 | LOST (SL_HIT) |
| 10 | TLT | 88.78 | 87.64 | -1.28 | LOST |
| 11 | TLT | 90.08 | 89.21 | -0.97 | LOST |
| 12 | TLT | 89.43 | 90.08 | +0.73 | WON |

Source: `audit_dashboard/data/dashboard_data.json::picks.recent_closed` filtered to BOND. Side / source / strategy fields all reported `N/A` — provenance metadata is not surfaced in `recent_closed`.

## Math verification

Dashboard reports PF=0.66, WR=54.5%, n=11.

Excluding pick #1 (UNRESOLVED): 11 picks valid.
- Wins (pnl_pct > 0): 6 picks (#3, #4, #5, #7, #9, #12), gross profit = +3.005
- Losses (pnl_pct ≤ 0): 5 picks (#2, #6, #8, #10, #11), gross loss = -4.537
- PF = 3.005 / 4.537 = **0.662** ✓
- WR = 6/11 = **54.5%** ✓

Math is correct.

## Bugs found

### Bug 1: pick #9 status/pnl_pct disagreement

Pick #9 (TLT, entry 88.28, exit 88.40, pnl_pct=+0.131%) is labeled `status=LOST` with `exit_reason=SL_HIT`. Stop-loss closure but net-positive return. Status string and pnl_pct sign disagree.

**Math impact: NONE.** The dashboard PF/WR computation uses `pnl_pct` sign, not the status string, so #9 correctly counts as a WIN for performance. The `status=LOST` label only affects display-layer status badges.

**Origin:** likely `outcome_resolver.py` sets `status=LOST` whenever `exit_reason==SL_HIT` regardless of realized pnl, where a tight SL just above entry can produce a tiny positive return when crossed mid-bar. Cosmetic data-quality issue, not a metric corruption.

### Bug 2: pick #1 UNRESOLVED with pnl_pct=-0.0

TLT pick where entry=exit=86.26. Zero move. `status=UNRESOLVED`. Either a duplicate ledger row, an aborted entry-fill, or a price-fetch staleness artifact. Not counted toward PF/WR.

## Real story behind the regression

1. **Universe concentration.** BOND class = `TLT` and `HYG` only. Two ETFs. 6/12 picks are TLT. Asset-class diagnosis from n=11 across 2 symbols is statistically meaningless. CLAUDE.md already calls out n<100 charter floor violation; this is below half of half.

2. **Direction bet timing.** TLT picks lean LONG (rate-cut/dovish positioning); their losing tape (-1.28, -1.07, -0.97, -0.82) is consistent with a sustained-rate environment over the snapshot window. HYG (credit) is 2W/1L — net positive. The regression is bond-DURATION-LONG getting bled, not bond-broad.

3. **Sample turnover.** 18-pick snapshot → 11-pick snapshot means ~7 picks rolled off whatever rolling window the dashboard uses. The old 18 likely contained more HYG/short-duration WINs from the prior dovish-tape period; the new 11 is heavier TLT-LONG.

   Cannot verify without the 18-pick frozen list — that snapshot is not preserved anywhere in the repo. Recommend a frozen-snapshot capture mechanism for any class flagged for verdict-grade reporting.

## What's NOT happening

- Not a resolver-v2 bug. Resolver math correct.
- Not a `_is_valid_resolved_pick()` mis-filter. Function applies uniform non-BOND-specific checks: paper-trade rejection (4615), null/corrupt pnl (4622), non-crypto >50% move rejection (4633), >100x entry/exit ratio rejection (4641), blocked-pick rejection (4648), non-performance exit-reason rejection (4656). Zero BOND-specific carve-outs.
- Not a count inversion. Earlier investigator hypothesis (dashboard 6W/5L vs published 5W/6L) was an artifact of using status-string vs pnl_pct-sign as the win criterion. Math is internally consistent.

## Recommendations

| ID | Action | Effort |
|---|---|---|
| 1 | **Do not act on BOND verdicts at n=11/12 across 2 symbols.** Period-over-period swings of this magnitude are noise. Note in master plan that BOND remains charter-floor violation. | None |
| 2 | **Investigate TLT direction-bias.** 6/12 BOND picks are TLT. Pull the strategy/source that generates them. If LONG-only, it's a regime-mismatch (long-duration bet during rate-stay). Candidate for mutate-before-kill per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`. | 1 session |
| 3 | **Fix pick #9 status label cosmetic bug.** In `outcome_resolver.py`, change SL_HIT status to derive from `pnl_pct` sign, not from exit_reason alone. Small surface (one function). | 30 min |
| 4 | **Expand BOND universe.** Charter floor n>=100 unreachable with TLT/HYG alone. Candidates: IEF/SHY/TIPS for rates duration, LQD/EMB for credit, MUB for munis. Wire as new symbols into BOND scraper inputs. | 1 PR |
| 5 | **Freeze snapshot infrastructure.** Save daily `dashboard_data.json` to `audit_dashboard/data/snapshots/YYYY-MM-DD.json` (deduped) so period-over-period verdicts can be reproduced. Disk impact ~5MB/day, ~150MB/month. | 1 PR |

## Verdict

**BOND regression is real but uninterpretable at this sample size.** The headline "PF 1.72 → 0.66" should not drive policy. The actionable signal is: TLT-LONG is a concentrated, money-losing position right now. The asset-class metric is noise around that single concentrated trade.

External eval's Phase 2 recommendation to "scale BOND" off the stale PF 1.72 was wrong on both axes — stale numbers AND charter-floor violation. Recommendation 4 (expand universe) is the prerequisite for any BOND verdict, full stop.
