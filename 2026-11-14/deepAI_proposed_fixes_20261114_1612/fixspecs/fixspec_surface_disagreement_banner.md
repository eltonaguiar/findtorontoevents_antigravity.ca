# Fix spec — Surface-disagreement banner (display-only)

## Problem (evidence, live 2026-11-14)
Same class, same day, PF differing up to 8x across official surfaces with no user-facing warning:
- ETF: registry PF 1.84 (n=15) vs money_ready PF 0.0216 (n=45)
- CRYPTO: registry 0.232 (n=23,636) vs money_ready 0.9196 (n=3,705)
- FOREX: registry 1.214 vs money_ready 0.660
- EQUITY: registry 0.707 vs money_ready 0.939
The dashboard already has an honesty-banner pattern (asset-class card warnings quoting
pf_registry vs money_ready), so this extends an existing convention.

## Proposed change (frontend-only)
1. In the asset-class card renderer (template.html), when both
   `pf_registry.by_asset_class[class].profit_factor` and
   `money_ready_verdict.classes[class].pf` are present and differ by >25%:
   render badge `⚠ SURFACES DISAGREE: registry PF {a} (n={na}) vs verdict PF {b} (n={nb})`
   with a tooltip linking to the ledger filter report (see fixspec_single_canonical_ledger.md).
2. Suppress "best strategy" / HIGH CONVICTION highlights for any class carrying the badge.
3. Also apply to ETF/BOND where money_ready n is tiny (n<20 ⇒ INSUFFICIENT badge regardless).

## Acceptance test
- ETF card shows the badge (PF spread 8.5x today); CRYPTO card shows it (4x spread);
- no class card shows tradeable highlights while badged.
