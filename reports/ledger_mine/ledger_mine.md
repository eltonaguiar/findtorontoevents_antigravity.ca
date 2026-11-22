# Ledger mine -- leakage, per-class robustness, source attribution

- ledger: `audit_dashboard/data/resolved_closed_picks_net.json` generated `2026-11-22T10:57:17Z`
- rows: 10,968 raw -> 10,968 kept
- evidence class: **OBSERVED** (live resolved picks, net of ledger cost)
- n_trials: 20 sources screened for one winner

## Leakage findings

- L1 48 rows are WON on gross but LOSS on net (1.0% of gross wins). Any WR computed from the won flag overstates by this much.
- L2 48 status-label conflicts (0.44% of rows).
- L3 src 'luxalgo_filters' is 36.7% of the ledger; any ledger-wide stat is mostly that one emitter.
- L3 cls 'CRYPTO' is 83.0% of the ledger; any ledger-wide stat is mostly that one emitter.
- L4 3916 rows are redundant re-emissions of the same symbol-day (35.7%). iid stats treat them as independent evidence; they are not.
- L5 2 rows move >50% net; verify against raw prints before any of them is counted as evidence.

## Per-class (cluster-robust by symbol-day)

| class | n | clusters | gross bp | net bp | WR% | PF | PF CI-LB | t |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| CRYPTO | 9,099 | 4,319 | -8.20 | -18.17 | 43.02 | 0.885 | 0.829 | -4.34 |
| EQUITY | 936 | 769 | 23.60 | 18.60 | 46.47 | 1.088 | 0.885 | 1.00 |
| ETF | 590 | 477 | 4.68 | -0.32 | 42.88 | 0.997 | 0.802 | -0.03 |
| FOREX | 252 | 209 | -13.13 | -15.13 | 40.48 | 0.668 | 0.420 | -2.36 |
| COMMODITY | 44 | 19 | -331.51 | -346.51 | 15.91 | 0.120 | 0.033 | -4.32 |
| BOND | 35 | 30 | -13.22 | -18.22 | 40.00 | 0.657 | 0.268 | -1.12 |
| FUTURES | 12 | 11 | 72.09 | 57.09 | 58.33 | 1.556 | 0.341 | 0.62 |
| **ALL** | 10,968 | | | -15.24 | | 0.904 | 0.852 | -3.91 |

## Source attribution

- n_trials = 20
- positive raw: 9, positive after Benjamini-Hochberg: 3

## 78.9% CRYPTO claim

- CRYPTO n=9,099, WR net 43.02%, WR gross 43.48%, net -18.17 bp, PF 0.885

---
No capital deployed. Not investment advice. UNMEASURED means unmeasured, not zero.
