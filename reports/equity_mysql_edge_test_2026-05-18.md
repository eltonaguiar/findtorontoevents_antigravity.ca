# EQUITY MySQL Edge Re-Test — 2026-05-18

Source: `ejaguiar1_stocks.at_signal_outcomes` WHERE asset_class=EQUITY.
Pulled 738 rows · 0 ghost/dup dropped · **738 clean EQUITY resolved picks**.

## Aggregate (clean)
- WR **1.2%** · PF **0.09** · EV **-0.670%/pick** (pnl_pct is already percentage-points)

JSON `closed_picks.json` carried ~44 EQUITY picks. MySQL clean count = 738. MySQL is the fuller source.

## Walk-forward (14-day windows, newest first)

| window | n | WR | PF | EV%/pick |
|---|---|---|---|---|
| 0 | 18 | 11.1% | 1.11 | +0.056% |
| 1 | 11 | 54.5% | 999.00 | +3.289% |
| 2 | 13 | 7.7% | 0.16 | -2.039% |
| 3 | 618 | 0.0% | 0.00 | -0.735% |
| 4 | 78 | 0.0% | 0.00 | -0.646% |

## Discrimination — does `confidence` separate winners?

insufficient WON/LOST split for a discrimination test

## Verdict — cross-table contradiction

`at_consensus_picks` holds **738 resolved EQUITY picks** (vs ~44 in `closed_picks.json`) — the data gap is real (~16x). But this fuller sample reports **WR 1.2% / PF 0.09 / EV -0.670%/pick**.

**This flatly contradicts** `dashboard_data.json::asset_class_health.EQUITY` (WR 52.7%, PF 1.41 — the basis for EQUITY's 'best candidate' label) and Kimi's audit (WR 53.1%, 'SAFE'). Two repo data sources disagree on EQUITY by ~50 WR points.

Status mix here: 9 WON (+5.7% avg), 394 LOST (-1.4% avg), 335 EXPIRED (0.0%). The 335 EXPIRED-at-flat + 394 LOST pattern is consistent with the documented non-crypto resolver bug (feedback_noncrypto_resolver_live_close_bug — closes at stale spot, mislabels).

**Option-A result: the EQUITY edge hypothesis is UNRESOLVABLE today — not because there is no edge, but because EQUITY's resolved data is internally contradictory across tables.** The 'EQUITY best candidate' framing rests on `asset_class_health` numbers that `at_consensus_picks` contradicts. Prerequisite before any EQUITY edge claim: reconcile the two tables + fix the non-crypto resolver, then re-run this test.