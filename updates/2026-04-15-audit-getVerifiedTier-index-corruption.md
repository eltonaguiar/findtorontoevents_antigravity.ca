# Fix: `getVerifiedTier` in `audit_dashboard/index.html` broke pick tables

## What was broken

`audit_dashboard/index.html` contained a corrupted `getVerifiedTier` implementation: the TRACK-tier branch ran **before** `idx`, `s`, and `combo_key` were declared, and the GOLDEN/VERIFIED logic was placed **after** an unconditional `return`, so it was dead code.

Every row render calls `getVerifiedTier`, which threw **`ReferenceError: idx is not defined`**. That prevented `renderPicks()` from completing, so **`#tab-active`** and **`#tab-closed`** never received `table.data-table tbody tr` rows. Playwright tests waiting for those selectors timed out.

`audit_dashboard/template.html` already had the correct function order (GOLDEN/VERIFIED first, then TRACK).

## What changed

Replaced `getVerifiedTier` in `index.html` to match the working `template.html` version: guard on `window._verifiedEdgeIndex`, define `s` / `combo_key`, evaluate GOLDEN and VERIFIED, then TRACK fallbacks, with null-safe property reads.

## How verified

```powershell
npx playwright test tests/audit_verified_edge_active_picks.spec.ts --project="Desktop Chrome"
```

Both tests passed (Active Picks rows present; Closed tab headers include Exit, Trust, FWD WR, FWD N, EDGE; no critical console/page errors).

## Production

Live `https://findtorontoevents.ca/audit/` initially still served the broken function until deploy. **Audit-only FTP deploy** (`python tools/deploy_to_ftp.py --audit-only`) uploaded the fixed `index.html` / `template.html`.

Remote tab smoke (load, click Active / Closed / Overview / Smart Picks, no critical JS errors, `getVerifiedTier` sane):

```powershell
$env:VERIFY_REMOTE='1'; npx playwright test tests/audit_remote_tabs_no_errors.spec.ts --project="Desktop Chrome"
```
