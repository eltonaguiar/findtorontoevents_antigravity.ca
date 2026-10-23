# Perf accuracy fix — placeholder-exit (0% P&L) rows + proven-pick integration

**Date:** 2026-10-22
**Files touched:** `audit_trail/dashboard_generator.py`, `audit_dashboard/index.html`, `audit_trail/data/dashboard_payload.json` (local refresh)
**Task:** cross-check crypto + non-crypto performance accuracy; fix stale data and 0% P&L items; integrate proven top picks.

## What was broken

1. **Placeholder/sentinel exits counted as flat closes.** 38 rows in the live
   `recent_closed` payload carry `exit_price = 0.0`, `pnl_pct = 0.0`,
   `outcome = null`, staleexit_reason = TIME_EXIT`. These are price-fetch
   FAILURES stamped as flat closes — not real trade outcomes. They were counted
   as legitimate "flat" results, inflating flat counts and deflating WR/PF.

   - 9 rows in **EQUITY** (stocksunify2: V, MA, JPM, JNJ, GOOGL, AMZN, LLY, GE, CAT)
   - 29 rows in **FOREX** (signal_validation: GBP-USD, EUR-USD, …)

   (Independent Grok audit 2026-10-22 reproduced the same counts: "9 exit_price=0
   rows" stocks, "29 exit_price=0 rows" FX — R7 "no placeholder exits".)

2. **Local repo payload ~144 days stale.** `audit_trail/data/dashboard_payload.json`
   was generated 2026-05-31 (production was fresh at 0.7 h). Refreshed the local
   copy from the production payload.

## What changed

1. **`audit_trail/dashboard_generator.py` — `_is_valid_resolved_pick()`** now
   rejects rows whose `exit_price` is present and `<= 0` (placeholder/sentinel).
   This keeps server-computed `non_crypto_performance`, summary metrics, and the
   published `recent_closed` free of the fetch-failure rows on the next run.

2. **`audit_dashboard/index.html` — `renderNonCryptoPanel()` and
   `renderCryptoPanel()`** filter chains now also drop rows with `exit_price <= 0`
   (client-side parity, so a payload generated before the fix is still clean).

3. **`audit_dashboard/index.html` — new `renderProvenEdgeStrip()`** renders an
   integrated "Research Proof Status (per class)" strip after the perf panels:
   for each class it shows `n resolved / WR / PF / Expectancy / CI-LB` plus a
   verdict badge and the top proven candidate sleeves (from
   `D.money_ready_verdicts`), with an explicit research-proof-not-money-ready
   disclaimer. All classes currently fail the money-ready bar; the strip
   surfaces that honestly instead of overstating "proven" picks.

## Verification

- `python3 -c "import py_compile; py_compile.compile('audit_trail/dashboard_generator.py', doraise=True)"` → **OK**.
- `node --check` on the full extracted main `<script>` block (1.01 MB) → **OK**.
- Rendering harness: `renderProvenEdgeStrip()` against the live payload renders
  10,183 chars; all classes + NOT READY / WATCH / INSUFFICIENT DATA badges +
  disclaimer + timestamp present.
- Filter replication over the live payload: new filter removes exactly **38**
  rows (9 EQUITY + 29 FOREX). Flat counts per class drop from
  EQUITY 14 → 5, FOREX 44 → 15 (rest are genuine near-break-even closes).

## Notes / remaining

- The asset-class mislabel finding (crypto symbols tagged EQUITY/FOREX) is
  documented separately; not changed here to avoid broad refactor risk.
- The 3,500-row cap means "recent_closed" mixes in rows older than 30 days
  (oldest 2026-02-21); the panel labels it "recent" but it is a capped
  all-closed list. Surfacing that is a separate UI-labeling change.
- **Production deploy not run** — `tools/deploy_audit_files.py` is the publish
  path; it leaves the machine and requires operator approval.

*Not financial advice. Research/educational only. Past performance does not guarantee future results.*
