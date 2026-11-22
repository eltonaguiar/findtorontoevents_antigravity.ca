# Part 3 · P3-4: Promotion-Path Fix Blueprint

**Author:** GitHub Copilot / Mercury-3 AI (`githubcopilot-mercury3AI`)
**Date:** 2026-11-22 04:00 EST
**Builds on:** Part 2 forward-clock + P3-2 decay findings.

---

## 1. The problem (restated)

The system has **430 real forward rows** with a genuine **+1.79% selection alpha** (73.3% alpha WR, 100% intrabar) — but they are **orphaned under H-119**, owned by no pod, linked to no backtest strategy. Result:

- Nothing can promote (G8 requires own pod forward rows).
- Decay/divergence watchlists stay empty (P3-2).
- The strongest OOS evidence in the book is locked away.

---

## 2. Fix A — Adopt H-119 into a registered pod

**Create `POD-H119-FORWARD-ALPHA`** (CRYPTO) in `audit_dashboard/data/audit2_pods.json`:

```json
{
  "id": "POD-H119-FORWARD-ALPHA",
  "status": "pre_registered",
  "hypothesis": "H-119",
  "klass": "CRYPTO",
  "dir": "LONG / SHORT",
  "evidence": "430 forward rows, selection alpha +1.79%, 73.3% alpha WR, 100% intrabar, 109 symbols",
  "gate": "n>=100 forward, 2x-cost CI-LB>0, split-half stable, IR>=0.5 vs BTC/ETH"
}
```

**Effect:** the 430 rows immediately become a testable confirmatory cohort → the book gets its first legitimate promotion candidate.

---

## 3. Fix B — Wire the tribunal to block emission

The current tribunal is a web page, not a denylist the scanner reads (a Known finding from the peer review). **Patch:** route `audit3_ledger.json` `kill_tribunal.kills[]` into a machine-readable denylist that the scanner/scoring path consults before emitting.

**Files:** `alpha_engine/production_scanner.py`, `alpha_engine/outcome_resolver.py`, `alpha_engine/check_active_picks.py`.

---

## 4. Fix C — Link forward rows to backtest strategies

Map `reports/forward_observations.jsonl` (H-119) to a `strategy`/`system` key so `backtest_vs_forward` populates (unblocks P3-2 decay clock).

---

## 5. Fix D — Directional kill segmentation

The CRYPTO KILL aggregate hides a **positive SHORT cell** (strong consensus SHORT +3.40). Segment kills by direction before extinguishing: kill the LONG emitters, preserve SHORT cells that are positive. This prevents throwing away real edge.

---

## 6. Acceptance criteria

- `audit2_pods.json` contains `POD-H119-FORWARD-ALPHA` (status `pre_registered`).
- `hf_decay_watchlist.rows` non-empty at next build.
- Scanner consults the kill denylist (grep for `kill_tribunal` in `production_scanner.py`).

---
*Not investment advice. Builds on Part 2 findings.*
