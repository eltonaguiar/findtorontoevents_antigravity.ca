# 04 — Common Themes, Bugs & Deeper Investigation (Deduped)

## A. Common Themes
1. **Not money-ready/proven** (0/166, 23/0). 2. **Measurement > alpha** (units, fills, stale/zombie marks, provenance). 3. **Pipeline/observability broken** (audit trail, freshness, regime ~0.25%, CI churn, fragmentation). 4. **Overfitting/benchmark illusions** (multiple testing, VWAP/IT-005/H10 disputes). 5. **Single-source concentration.** 6. **Path:** integrity → reproduce (net, benchmark-relative) → paper → gated live.

## B. Bug/Defect Register
| ID | Defect | Impact | Status | Pri |
|---|---|---|---|---|
| B01 | PnL unit/scale/calc (`pnl*=100`, sign/calc mismatches) | Corrupt PnL | Open | P0 |
| B02 | Null/zero `entry_price`, bad sync | Invalid marks | Open | P0 |
| B03 | Hardcoded `expected_2026_prices` | False validation | Open | P0 |
| B04 | Stale/frozen picks (~172d, 0% frozen) | Masks losses | Open | P0 |
| B05 | EXPIRED→WON / ~78.6% zombies | Survivorship/PnL bias | Open | P0 |
| B06 | Stop/fill realism & exit-label/taxonomy issues | Untrustworthy exits | Partial local/peer fixes, system Open | P0/P1 |
| B07 | Futures/commodity ~98.4% zero-PnL/roll/marks | Invalid commodity perf | Open | P0 |
| B08 | Audit trail/provenance missing (`resolution_method`, lineage) | No auditability | Open | P0 |
| B09 | Dead/stale feeds/outcomes (e.g. `fetch_prices.php` 404 reported) | Fabricated/stale metrics | Open (verify) | P0 |
| B10 | Cohort/ledger reconciliation mismatch | Verdicts untrustworthy | Open | P0 |
| B11 | Single-source concentration (166 cells) | No confirmation | Open | P1 |
| B12 | Harness defects (MIN_WINDOWS, gap windows, no multiple-testing, costs not netted) | False passes | Open | P0/P1 |
| B13 | Regime coverage ~0.25% | Unauditable regime gates | Open | P1 |
| B14 | CI failures/cancellations/stale workflows | Unreliable outputs | Open | P1 |
| B15 | Source fragmentation (unsynced/stale JSONs) | Inconsistent truth | Open | P1 |
| B16 | Class contamination/allowlist/timestamp issues (e.g. FOREX) | Misleading stats | Open | P1 |
| B17 | MF class not wired despite infra | Opportunity unused | Open (build) | P2 |

## C. Deeper Investigation
| ID | Investigation | Exit |
|---|---|---|
| D1 | VWAP-MR >730d exchange, core-only | Proper CSCV/PBO<0.3, conservative fills, cost stress |
| D2 | VWAP annualization/intrabar independent audit | Repro script resolves falsification conflict |
| D3 | TSMOM benchmark & bear alpha | Risk-matched bench, bear/subperiods, costs/funding, bootstrap CI |
| D4 | Variant C reproduction | Raw, net, expanded OOS |
| D5 | mega_mutation reproduction | Independent OOS, path-verified, full costs |
| D6 | Cross-ledger reconciliation | Row-level diff + canonical cohorts |
| D7 | Resolution/label provenance audit | Schema enforced, backfilled, sampled checks |
| D8 | Benchmark-relative & effective-N re-score | Corrected significance/carry split |
| D9 | MF live viability (low-fee $0-min) | Wired class, NAV walk-forward, next-NAV, paper |
| D10 | CI/workflow root causes & freshness SLAs | Fixed concurrency/timeouts/perms, hard TTL gates |
