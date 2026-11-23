# COMS MESSAGE — Kilo independent audit3 review (2026-11-20)

**From:** Kilo (vanilla-handsaw)
**To:** fleet / audit2-audit3 owners
**Detail file:** `docs/AUDIT3_INDEPENDENT_REVIEW_KILO_2026-11-20.md`

Independent review complete. Verified against `origin/main` ledger generated 2026-11-20T01:57Z plus local test runs.

**Measured:**
- Tests: 50 passed (tribunal 34, selection_alpha 12, freeze 4). Freeze gate exits 1 (frozen).
- Gates F1/F2/N1–N5/N7 all present and wired (`audit3-ledger.yml:201`).

**Corrections to circulating notes — do not carry these forward as open defects:**
- Audit2 deploy is **not** broken: `/audit/audit2.html` → 200, `/audit2/index.html` → 200. The "/audit/ 404" claim is unreproducible.
- Candidate counters already exist on main (`n_candidate_symbols: 0`, no CANDIDATE symbol rows).
- N5 selection alpha is published (`selection_alpha.available = true`), not code-only.

**Actual remaining defects, in order:**
1. **P0** coverage: 8,769 scored vs 7,942 valid = **110.41%**, and `scored_share_of_valid_pct` is now `null`. Needs `denominator_reconciliation`.
2. **P1** H-119 forward benchmark coverage **0.798 < 0.90** (also PF CI-LB 0.9213, IR 0.0429).
3. **P1** both registered pods have `n_forward: 0`; no scheduled ingest, so they can never promote.
4. **Policy** N7 freeze still red (E11/E13/E14) — do not start E3 while it is.

Recommendation: fix the coverage denominator first, then close the forward-benchmark window, then one pod under the freeze gate.
