# Ledger mine -- leakage, per-class robustness, source attribution

- ledger: `audit_dashboard/data/resolved_closed_picks_net.json` generated `2026-11-22T10:57:17Z`
- rows: 10,968 raw -> 10,593 kept
- evidence class: **OBSERVED** (live resolved picks, net of ledger cost)
- n_trials: 20 sources screened for one winner

## Leakage findings

- L1 48 rows are WON on gross but LOSS on net (1.0% of gross wins). Any WR computed from the won flag overstates by this much.
- L2 48 status-label conflicts (0.45% of rows).
- L3 src 'luxalgo_filters' is 36.4% of the ledger; any ledger-wide stat is mostly that one emitter.
- L3 cls 'CRYPTO' is 82.4% of the ledger; any ledger-wide stat is mostly that one emitter.
- L4 3668 rows are redundant re-emissions of the same symbol-day (34.6%). iid stats treat them as independent evidence; they are not.
- L5 2 rows move >50% net; verify against raw prints before any of them is counted as evidence.

## Per-class (cluster-robust by symbol-day)

| class | n | clusters | gross bp | net bp | WR% | PF | PF CI-LB | t |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| CRYPTO | 8,733 | 4,220 | -6.07 | -16.04 | 42.94 | 0.898 | 0.842 | -3.76 |
| EQUITY | 934 | 769 | 24.29 | 19.29 | 46.57 | 1.091 | 0.885 | 1.03 |
| ETF | 585 | 475 | 4.78 | -0.22 | 42.74 | 0.998 | 0.816 | -0.02 |
| FOREX | 251 | 208 | -13.45 | -15.45 | 40.24 | 0.662 | 0.429 | -2.41 |
| COMMODITY | 43 | 18 | -354.80 | -369.80 | 13.95 | 0.083 | 0.022 | -4.70 |
| BOND | 35 | 30 | -13.22 | -18.22 | 40.00 | 0.657 | 0.263 | -1.12 |
| FUTURES | 12 | 11 | 72.09 | 57.09 | 58.33 | 1.556 | 0.334 | 0.62 |
| **ALL** | 10,593 | | | -13.40 | | 0.915 | 0.859 | -3.38 |

## Source attribution

- n_trials = 20
- positive raw: 9, positive after Benjamini-Hochberg: 3

## 78.9% CRYPTO claim

- CRYPTO n=8,733, WR net 42.94%, WR gross 43.42%, net -16.04 bp, PF 0.898

---
No capital deployed. Not investment advice. UNMEASURED means unmeasured, not zero.
