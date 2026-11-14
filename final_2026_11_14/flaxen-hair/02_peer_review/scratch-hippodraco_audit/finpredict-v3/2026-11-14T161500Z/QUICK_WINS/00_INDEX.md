# QUICK-WINS — Proposed Fixes (2026-11-14)

Auditor subtree: `finpredict-v3` · Archive stamp: `2026-11-14T161500Z`
This folder proposes concrete, low-effort fixes per asset class and system-wide, built on the verified findings in `2026-11-14/finpredict-v3/2026-11-14T155500Z/` (audit + data-hygiene guardian). Each proposal cites a real target file (verified on disk) and rates Impact / Effort / Risk.

## Folder structure

```
QUICK_WINS/
  00_INDEX.md                     <- this file
  overall/
    GLOBAL_QUICK_WINS.md          <- 7 systemic fixes (highest leverage first)
  asset_classes/
    CRYPTO.md                     <- ALIVE: stale/pinned prices, zombie feed, garbage entries
    FUTURES.md                    <- DEAD: placeholder, date-only seed, no date in UI
    BOND.md                       <- STALE: null-price seeds, n=1 closed
    EQUITY.md                     <- ALIVE: prices legit; needs statistical disclosure (n+CI)
    ETF.md                        <- ALIVE: weekend park legit; thin closed sample
    FOREX.md                      <- ALIVE: 11 phantom closed rows to purge; batch timestamps
    COMMODITY.md                  <- ALIVE but unproven (0 closed trades)
    MUTUAL_FUNDS.md               <- PLANNED: ranker/site unbuilt; mark not-implemented
```

## Class verdicts at a glance

| Class | Verdict | Top quick win | Effort |
|---|---|---|---|
| CRYPTO | ALIVE (stale) | live re-quote + quarantine `inverse_*` zombies + reject zero-entr | S/M |
| FUTURES | DEAD (placeholder) | gate non-live seeds from active panel + fix date-only timestamp | S |
| BOND | STALE | backfill null prices / suppress stats until n≥10 | S |
| EQUITY | ALIVE | add n + binomial CI to headline WR; label "last quote = Fri close" | S |
| ETF | ALIVE | parked-state label + re-quote hook on next open | S |
| FOREX | ALIVE | purge 11 phantom closed rows + dedupe batch `closed_at` | S |
| COMMODITY | ALIVE/unproven | "unproven" badge + route through forward-validator | S/M |
| MUTUAL_FUNDS | PLANNED | mark not-implemented OR build minimal ranker | M |

## Systemic top-3 (see GLOBAL_QUICK_WINS.md for all 7)

1. **Gate the hygiene tool in audit-dashboard CI** — `tools/pi_data_hygiene.py` (exit 1 on findings) wired into the audit workflow. Effort S, Impact high.
2. **Publish true payload lag / price age** — stop the misleading "5-min refresh"; show `payload_lag_seconds` and last price-quote time instead of signal age.
3. **Stop pinning crypto current_price to entry / disclose survivorship** — re-quote crypto at build; show dual-cohort headline (valid vs all closed).

All target paths flagged in the files were verified to exist in this worktree; anything not verifiable is marked UNVERIFIED in-file.
