# TODO — EAGLE audit review + quick wins

- [ ] Create `EAGLE_YYYY-MM-DD_HHMMEST_<MODEL_PROVIDER>.md` with:
  - [ ] Top P0/P1 incidents + recommended quick-win PR list
  - [ ] Per-asset-class “what was filtered out” hypotheses (EQUITY/CRYPTO/FOREX/COMMODITY/ETF/BOND/FUTURES/PENNY)
  - [ ] Remaining items dashboard sections (Incidents / Enhancements)
  - [ ] DB table proposal for incidents/enhancements
- [ ] Implement a dedupe helper script that:
  - [ ] Crawls repo for incident/enhancement markdown references
  - [ ] Extracts absolute/relative MD file paths
  - [ ] Dedupes by identical canonical path, preferring shortest path
  - [ ] Outputs non-duplicated path list
- [ ] Create “quick win” PR markdown stubs for top items and link them in the EAGLE file
- [ ] Commit created markdown + script to main (with EAGLE file name including EAGLE + EST timestamp + model/provider)
- [ ] Run quick sanity checks (lint/format) for new script
