# /audit major-goal wording refresh — stale claims corrected against live data

**Date:** 2026-11-16 · **File:** `audit_dashboard/template.html` (`#major-goal-banner`)
**Trigger:** the page's per-asset-class narrative is static HTML while the tiles underneath are
JS-updated from live JSON. Several of those static claims had drifted far enough to be wrong.

## What was stale (live values at 2026-11-16T04:03–04:07Z)

| Static claim in the page | Live value | Source |
|---|---|---|
| `0/6 money-ready` | **10 classes**: 4 NOT_READY, 1 WATCH (COMMODITY), 5 INSUFFICIENT_DATA | `money_ready_verdict.json` (04:07Z) |
| `CRYPTO 32.9% PF0.74` "only class n≥100, FAIL" | CRYPTO **35.8% / PF 0.92 / n=3716**; FOREX n=612, EQUITY n=250, COMMODITY n=229 are all ≥100 too | `intrabar_truth_by_class.json` (04:03Z) |
| `EQUITY 60% PF2.13 n=72` "(closest)" | **59.2% / PF 0.94 / n=250** — PF is now *below* 1, i.e. net-negative, not "closest" | same |
| `COMMODITY 42% PF1.77 n=81` | **40.2% / PF 1.03 / n=229** — breakeven, not 1.77 | same |
| `DB health GREEN: ghost rows 0, status mismatch 0, non-canonical statuses 0` | ghost_rows **22,947** (`ok: true` = harness tolerated, not zero), mismatches 0, non-canonical 0, 5/5 checks pass | `db_health.json` (03:52Z) |
| Per-class spans (EQUITY PF0.70/n567, CRYPTO PF0.98+PF0.96, ETF n=1/n=13 PF0.34, COMMODITY n=3 / FUTURES n=11 9.09%/0.475, FOREX PF0.29/46.1%/-1026%, BOND 78 rows) | 2026-05/06 vintage; live values differ per class (ETF 2.2%/PF 0.02 n=45, FUTURES 42.3%/1.09 n=52, FOREX 32.2%/0.66 n=612, BOND 7.7%/0.39 n=26) | same |

**Why the spans matter even though JS updates them:** the page script does not replace the
static text — it moves it into a `<details>` labelled *"Forensic snapshot (static HTML)"* and
renders the live line above it. So the stale numbers stay one click away and read as current
unless the vintage is stated.

## Regression note (why this keeps happening)

`#828` (`a154912f8c4c`) fixed the ghost-rows footer. The next template rebuild
(`3ce350d60ab5`, PM/theory wiring) re-introduced the pre-#828 copy — the file was regenerated
from an older `index.html` source rather than edited in place. That is the same silent-revert
class AGENTS.md already warns about, and it is why the wording now has tests.

## What changed

1. **Header sentence** — `0/10` with the real verdict split, the intrabar figures corrected to
   the 2026-11-16T04:03Z snapshot, and an explicit "the per-class tiles below auto-update, this
   sentence does not".
2. **Footer** — replaced the green/zero claim with the live DB-health reading (5/5 checks,
   22,947 quarantined rows, quarantine-not-delete policy, "this footer is static").
3. **"Cleanest leads" → "Historical leads (static, forward-track only, not sized)"** so the two
   forward-track examples are not read as current recommendations.
4. **`<details>` label** — now `Forensic snapshot (static HTML, 2026-05/06 — not live)` in both
   render paths, so the frozen spans announce their vintage.
5. **ML-calibration banner** — added `(static measurement 2026-05-15)`; its confidence bands have
   no refresh path.
6. **New tests** — `tests/test_audit_truth_claims.py` (5 assertions) pin: no `ghost rows 0`, no
   `0/6 money-ready`, dated header, labelled snapshot, and the freshness banner's `hasMissing`.

## Verified

```
python3 -m pytest -q tests/test_audit_truth_claims.py    # 5 passed
python3 -m pytest -q tests/test_deploy_audit_files_strict_json.py  # 6 passed
grep -c "ghost rows 0"                audit_dashboard/template.html  -> 0
grep -c "0/6 money-ready"             audit_dashboard/template.html  -> 0
grep -c "Forensic snapshot (static HTML, 2026-05/06" ... -> 2
```
No JS logic changed: only string content in static HTML and the two label literals, so the
`data-mg-class` render contract and `major-goal-asof` update path are untouched.

## Revert

```bash
git checkout <pre-sha> -- audit_dashboard/template.html tests/test_audit_truth_claims.py
```
