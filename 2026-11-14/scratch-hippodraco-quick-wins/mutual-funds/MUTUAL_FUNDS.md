# MUTUAL FUNDS — Retire-vs-Build Decision
Audit: §4.3/§6 — **phantom class**. No MUTUAL_FUNDS in `alpha_engine/asset_class.py:102-120` or `alpha_engine/config.py:1087-1134`; tickers like VFIAX/FXAIX fall through to `equity` (`asset_class.py:259-260`); MySQL `mf_*`/`mf2_*` (20+15 funds) frozen: NAV to 2026-02-06 / 2026-03-27, last tracked pick 2026-02-15, `mf2_category_perf`/`mf2_comparisons` empty; `findmutualfunds2/` is a legacy shell. All three peer audits independently confirm: zero algorithm, zero data source, zero picks (active or closed).

## Recommendation: RETIRE the surface, QUARANTINE the tables (do not build now)
Rationale: the live system has no honest edge in any traded class yet (audit verdict FAIL); mutual funds are EOD-NAV instruments incompatible with the intraday TP/SL pick engine, so a real build is a new product (NAV feed, distribution/load handling, EOD-only resolution), not a quick win. Keeping a dead surface invites users to believe coverage exists.

## QW-MF-1 · Remove/annotate every mutual-fund mention (S, <2h)
- **Fix:** Grep user-facing surfaces (dashboards, READMEs, capability lists) for mutual-fund claims; remove or mark `not currently covered`. Ensure no asset-class summary can render a MUTUAL_FUNDS row (it cannot today — keep it that way and add a contract-test assertion).
- **Verify:** Contract test: payload class keys ⊆ traded classes; UI copy grep clean.

## QW-MF-2 · Stop equity-fallback misclassification of fund tickers (S)
- **Problem:** VFIAX-style tickers silently become `equity` with intraday TP/SL rules — wrong instrument semantics if any emitter ever sends one.
- **Fix:** In the unified classifier, recognise 5-letter tickers ending in X with a fund-list check (or an explicit known-fund set) → classify `MUTUAL_FUNDS_UNSUPPORTED` and reject at ingest with a logged reason, instead of equity fallback.
- **Verify:** VFIAX fixture rejected/logged, never an equity pick; default-to-equity fallback now logs every use (it currently manufactures equities silently).

## QW-MF-3 · Quarantine `mf_*`/`mf2_*` (S)
- **Fix:** Rename-or-flag the frozen tables as archived in the schema inventory (`tools/recon_uncharted_tables.py` already maps `mf_`/`mf2_` families — annotate as retired 2026-11), exclude from any freshness/stats surface, keep data (no DROP) for provenance.
- **Verify:** Inventory lists them retired; no dashboard/query reads them.

## Correction (2026-11-14 ~18:00Z, from finpredict-v2 synthesis)
A mutual-fund artefact **does exist — as an untracked prototype**: `alpha_engine/mutual_fund_ranker.py` + `mutual_fund_metadata.csv` are `??` files in the main checkout only, **absent from `origin/main`**, output file carries a typo (`mutut_fund_rankings.json`, 39KB + NAV cache — so "no output ever produced" was also wrong). This does not change the recommendation: an uncommitted filename-typo'd prototype with monthly-NAV semantics is not coverage. Retire/de-advertise stands; add "delete or properly track the prototype" to QW-MF-3 so it cannot silently become a surface. All reviewers veto building a live MF pick class / stub scanner emitting placeholder picks.

## Subagent-refined (verified)
- **Retire confirmed independently**, including class-list evidence: no MUTUAL_FUNDS in `money_ready_verdict.py:226` (`CANONICAL_ASSET_CLASSES`) or `dashboard_generator.py:6763` (`_PER_ASSET_CLASSES`) either.
- **QW-MF-1 concrete:** remove `findmutualfunds*` deploy entries (`tools/deploy_to_altsite.py:139-141`); readiness-plan row (`audit_dashboard/institutional_readiness_plan.html:219`, "not yet ingested") → `RETIRED 2026-11-14`; archive `findmutualfunds2/` per AGENTS.md convention rather than deleting. Only `tools/recon_*.py` + deploy config reference it.
- **QW-MF-3 concrete:** blocklist `MUTUAL_FUND_TICKERS` in `asset_class.py` sourced from the frozen `mf_funds` inventory, classifying as rejected/`mutual_fund_retired` instead of the equity fallback (`asset_class.py:259-260`; `config.py:1127-1132`). Test: `asset_class_from_symbol("VFIAX") != "equity"`.
- Freshness tombstone: MF family reports `RETIRED` in `db_freshness_check.py`, never RED; document in `updates/2026-11-14-mutual-funds-retirement.md` when implemented. **No DROP** without separate owner approval.

## If the decision is BUILD instead (explicit non-quick-win, L+)
Minimum honest scope: NAV EOD feed (per-fund, distributions reinvested), EOD-only entry/exit at NAV (no intraday TP/SL — use time/NAV-% bands), separate class + ledger + freshness lane, forward accrual from zero before any claim. Estimate: weeks, plus a data-source decision. Do not bolt funds onto the equity pick engine.
