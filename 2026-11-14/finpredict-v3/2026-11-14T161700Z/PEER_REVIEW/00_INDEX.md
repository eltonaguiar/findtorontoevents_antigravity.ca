# PEER REVIEW — Index (2026-11-14)

Auditor subtree: `finpredict-v3` · Archive stamp: `2026-11-14T161700Z`
A review of the peer audit archives produced 2026-11-14, per asset class and overall. Every figure is attributed to its source peer; gaps are marked.

## Folder structure

```
PEER_REVIEW/
  00_INDEX.md
  overall/PEER_REVIEW_OVERALL.md     <- verdict consensus, systemic agreements, best-of
  asset_classes/
    CRYPTO.md     FUTURES.md    BOND.md
    EQUITY.md     ETF.md        FOREX.md
    COMMODITY.md  MUTUAL_FUNDS.md
```

## Class review summary (see each file for quotes + sources)

| Class | Peer consensus | Best-of adopted |
|---|---|---|
| CRYPTO | flat 0% is stale/artifact; no statistically distinguishable edge (z=−7.1) | ML DB-level PnL recompute + v2 zombie quarantine + re-quote UI |
| FUTURES | all peers: dead/blocked (0 closed ever) | v4 retire-vs-re-emission gate + date-only-seed fix (v1/v2 UI contradiction flagged) |
| BOND | keep INSUFFICIENT_DATA until real closed sample | ML `FIX_PROPOSED` (sync feed→DB, refresh prices, emit exits) |
| EQUITY | headline n=8 misleading; n=461 ~43% losing | ML backfill + staleness guard; add n+CI |
| ETF | insufficient data; crypto-ETF segregation needed | n+CI + parked-state label + re-quote hook |
| FOREX | PR#6 gate bypass proven; PF 0.48, n=438 z=−6.02 | enforce gate + price enricher + dedup + paper-only |
| COMMODITY | DEAD (June zombies); DSR falsified | close zombies; policy-frozen; re-emit only from scratch |
| MUTUAL_FUNDS | zero coverage; build-vs-suppress unresolved | classify now; defer stub emission until real NAV feed + n≥100 |

## Cross-peer flags

- v4 `proposed_fixes/{crypto,futures,bond,equity,etf,forex,commodity}/` are EMPTY (not found); ML `etfs/` empty; ML has no futures folder.
- Contradictions to settle: futures date-only "no date" (v1) vs "shows a date" (v2); five different active-count surfaces; v4 noncrypto is June-snapshot based.
- Numbers to drop/relabel: "37 active (June)", "61% spot-flicker", "−1.4% 14d" (live is −333% sum).
