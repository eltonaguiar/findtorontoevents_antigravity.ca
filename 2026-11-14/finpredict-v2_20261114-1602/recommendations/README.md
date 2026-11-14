# Recommendations — 2026-11-14 / finpredict-v2

This folder converts the audit findings in `../MASTER_AUDIT.md` into an implementation-ready,
ranked remediation plan. It is additive and read-only with respect to the running pipeline;
nothing here has been applied.

## Folder structure

```
recommendations/
  README.md                 <- this file
  QUICK_WINS.md             <- top 12 P0 fixes, deduplicated and ranked
  overall/
    ROADMAP.md              <- phased 4-week plan with exit criteria
    DATA_CONTRACT.md        <- schema v2.0.0: timestamps, quote provenance, PnL, status, class, dedup
    CI_GATES.md             <- G1-G13 gates wired to exact workflow lines
  per_asset_class/
    crypto_commodity.md     <- CRYPTO + COMMODITY (7 P0 / 8 P1)
    equity_etf.md           <- EQUITY + ETF (7 P0 / structural)
    forex_futures.md        <- FOREX + FUTURES (6 P0)
    bond_mutual_funds.md    <- BOND + MUTUAL FUNDS (7 P0; MF = de-advertise + NOT_BUILT)
  patch_plan/
    P0_QUICK_WINS.md        <- cross-cutting P0 detail blocks (9 items)
    P1_STRUCTURAL.md        <- structural programs
    acceptance_tests.md     <- 18 test groups + one-shot gate
  peer_review/              <- reviewer memos (per-class + overall) -- added by review pass
```

## How to use

1. Read `QUICK_WINS.md` first. It is the deduplicated P0 set; the per-class files contain the
   detailed rationale and verified `file:line` targets.
2. Anything that changes a published number (e.g. `summary_picks` WR) ships with the fix and a
   changelog note; do not silently rebase historical values.
3. Anything that changes a displayed pick (UNQUOTED/STALE labels, dedup, class routing) must be
   behind a flag and reversible, and must keep the underlying rows auditable.
4. Do not size real money on any surface until the class clears the project's own Tier-2 charter
   (n>=100, WR>=50%, PF>=1.5) on a time-ordered, policy-clean ledger.

## Ground rules used by every plan

- **No fabricated numbers.** Every count traces to `../sub/*.md`, `../raw/*.json`, or a named peer archive.
- **No destructive cleanup.** Zombies are quarantined/tagged, never deleted; the audit trail stays intact.
- **No honesty regressions.** Never hide losing cohorts or re-introduce cherry-picked windows.
- **No trading changes in P0.** P0 is truth-telling and reliability only; resolver/signal changes are P1.
- **Flag + rollback** for every behavior change.

## Cross-references

- `../MASTER_AUDIT.md` — evidence and verdict
- `../PEER_CROSSREF.md` — finpredict v1/v2/v3/v4 reconciliation
- `../../../../audits/2026-11-14/finpredict-v4_2026-11-14-1555/` — v4 archive (main repo root)
- `../../../finpredict/2026-11-14/...` and `../../../finpredict-v3/2026-11-14/...` — v1/v3 archives
- `../../../../updates/2026-11-14-ML-AUDIT-childlike-airport.md` — ML/DB peer audit (172-day-stale `live_picks.db`, PnL sign bug, empty `audit_trail.db`, no mutual funds)
