# 05 — BOND + MUTUAL FUNDS consolidated review

**Consolidated:** 2026-11-14T17:44Z · **Read-only** (no code changed)
**Peers:** V2 (deep remediation), V3 (quick-wins + peer-review), V4 (noncrypto deep dive), ML (childlike-airport FIX_PROPOSED), ME/V1 (quick-wins)

---

## 1. Consensus

| # | Finding | Peers agreeing |
|---|---|---|
| C1 | **Vacuous PASS** — BOND `activeCount==0` short-circuits the quality gate (`active_count == 0 or …`), rendering a green `thresholdPass=true` that contradicts the authoritative `INSUFFICIENT_DATA` verdict. | V2 (QW-1, code-verified), V3-QW (B2), ME (class stuck INSUFFICIENT_DATA), V3-PR, V4 (do not size) |
| C2 | **BOND n=1 policy-clean** — only 1 settled trade (`0W/1L, WR 0%, PF 0, pnl −0.01159`); class is `policy_frozen=true`, `BLOCKED`, `sizing_allowed=false`. No peer found a money-ready edge. | V2, ME/V1, V4, V3-PR |
| C3 | **MUTUAL FUNDS unbuilt/untracked** — no tracked ranker, no page, no emitter, no picks; `alpha_engine/mutual_fund_ranker.py` + `mutual_fund_metadata.csv` are **untracked** (absent from `origin/main`); ranker output path has typo `mutut_fund_rankings.json` (line 53). | V2, ME/V1, V3-QW, V3-PR, ML (ZERO coverage) |
| C4 | **Do NOT build a live MF pick class.** De-advertise MF, render `NOT BUILT` / `PLANNED`, keep it out of `CANONICAL_ASSET_CLASSES` and `_PER_ASSET_CLASSES`. | V2 (QW-2, P1-5), ME/V1, V3-QW, V3-PR (reconciliation) |
| C5 | **BOND price gap** — 9/15 `active_raw` seeds have `current_price=None`/`pnl=0`; resolver never quotes most bond ETFs. | V2 (QW-4), V3-QW (B1/B4), ML (3.2), ME/V1 |

---

## 2. Unique per-peer

- **V2 (deepest):** code-verified fixes — QW-1 vacuous PASS, QW-3 `summary_picks` WR>100% (BOND 127.8%) SQL bug, QW-5 cross-source dedupe (15→6 rows), QW-6 FRED `SKIP_FRED:'1'` hard-code, QW-7 price-coverage gate; P1-1 single BOND emitter, P1-2 promotion gate + shadow accrual, P1-3 FRED cache/backfill, P1-4 class-health contract; **10-item Do-Not-Do list** (incl. veto of `current_price=entry_price` backfill and of adding MF to canonical classes).
- **V3-QW:** QW-B1 backfill null prices, QW-B2 suppress stats until closed n≥floor, QW-B3 age-gate stale seeds, QW-B4 verify bond price-source routing; MF "PLANNED — not implemented" badge + note `audit_dashboard/funds.html` exists but role unconfirmed.
- **V3-PR:** recommends **ML FIX_PROPOSED as backbone** (sync→DB, refresh price, emit exits, symbol_strategy_stats); MF reconciliation = **classify now, emit later** (defer stub emission).
- **V4:** BOND **1293 open** in `picks_now_live_pnl.json` vs 15 in `active_raw` (layer mismatch); intrabar n=26 WR 7.7% PF 0.39 → INSUFFICIENT_N; `db_n=0` for all top picks; `dashboard_data.json` 26 days stale.
- **ML:** `live_picks.db` sync gap (2 active ~172d stale vs 7 in fresh `active_picks_bond.json`); Fixes 3.1–3.4; MF `ASSET_CLASS_MAP` add `"MUTUAL_FUND": 7` + `MUTUAL_FUND_SYMBOLS` + stub scanner/strategies.
- **ME/V1:** stamp `current_price=entry_price` after `_save_bond_picks()` (or drop unquoted signals); auto-expire stale unquoted seeds as `exit_reason=STALE_NO_QUOTE`; relabel MF claim in `institutional_readiness_plan.html:190`.

---

## 3. Consolidated fixes (dedup)

Legend — **VETO** = flagged destructive/against policy. Effort: S / M / L. Risk: Low / Med / High.

| # | Fix | Primary files (`file:line`) | Effort | Risk | Proposer(s) |
|---|---|---|---|---|---|
| F1 | Kill vacuous PASS: `activeCount==0`/`resolved_n<30` → `INSUFFICIENT_DATA`, never `thresholdPass=true` | `audit_trail/dashboard_generator.py:6824-6826`; `audit_trail/quality_monitor.py:171-174`; `audit_dashboard/template.html:4946-4953` | S | Low | V2 (also V3-B2, ME) |
| F2 | De-advertise MF: `summary.unbuilt_asset_classes` + `NOT BUILT` badge; mark `tactical_fund_rotation` `RESEARCH_ONLY` | `audit_trail/dashboard_generator.py:18006-18014`; `audit_dashboard/template.html:4913-4966`; `multi_asset/portfolio_defs.py:382-395`; `audit_dashboard/institutional_readiness_plan.html:190` | S | Low | V2, ME/V1, V3-QW |
| F3 | Fix `summary_picks` WR>100%: make wins/losses a strict subset of `resolved`; guard emits `None`/`DATA_INCONSISTENT` | `tools/sync_summary_picks_json.py:63-65,153-162` | S | Low | V2 |
| F4 | BOND price coverage trio: read `picks` dict schema; use real `FMP_API_KEY` (not `demo`); resolver knows all 14 `BOND_SYMBOLS` | `audit_trail/fetch_stock_prices.py:68-77`; `audit_trail/dashboard_generator.py:1599`; `audit_trail/universal_pick_resolver.py:433-443` | S–M | Low-Med | V2 (QW-4), V3-B1/B4, ML 3.2 |
| F5 | Cross-source dedupe (BOND 15 rows→6, 5 instruments): collapse on `(ac,symbol,direction,strategy)`, not `source_system`/`pick_id` | `audit_trail/dashboard_generator.py:9831-9836,9876,:9538` | S–M | Low | V2 (QW-5) |
| F6 | Sync `active_picks_bond.json` (7) into `live_picks.db`; upsert by `(symbol,strategy)` | `alpha_engine/audit_sync.py`; `alpha_engine/production_scanner.py`; `live_picks.db` | M | Med | ML 3.1 (endorsed V3-PR) |
| F7 | Emit exit events (TP/SL/time) for BOND so closed sample grows past 3; auto-expire `current_price=null && age>24h` as `STALE_NO_QUOTE` | `audit_trail/universal_pick_resolver.py`; `alpha_engine/bond_scanner.py` | M | Med | ML 3.3, ME/V1 |
| F8 | Populate `symbol_strategy_stats` for bond strategies (attribution) | `audit_trail/dashboard_generator.py`; `alpha_engine/config.py` | M | Low | ML 3.4 |
| F9 | Re-enable FRED in bond scanner (`SKIP_FRED` default `'0'`) | `.github/workflows/etf-bond-scanner.yml:159`; `alpha_engine/bond_scanner.py:289-296` | S | Low | V2 (QW-6) |
| F10 | BOND price-coverage gate: `<80%` priced ⇒ `DATA_STALE`, `thresholdPass=false` | `audit_trail/dashboard_generator.py:18006-18014` (new helper) | S | Low | V2 (QW-7) |
| F11 | Age-gate stale seeds at emission (max-hold window) | `alpha_engine/bond_scanner.py`; `tools/bond_emitter_spike.py` | S | Low | V3-B3, ME/V1 |
| F12 | Single canonical BOND emitter (keep `bond_scanner`; `bond-agent` → health job) | `.github/workflows/etf-bond-scanner.yml:150-165`; `.github/workflows/bond-agent.yml:217,246-320`; `alpha_engine/scanner.py:293` | M–L | Med | V2 (P1-1) |
| F13 | BOND promotion gate + paper shadow accrual (n≥100, WR≥50%, PF≥1.5, coverage≥90%, top-source≤40%) | `audit_trail/quality_gates.py:1724-1730`; new `tools/bond_promotion_gate.py` | M | Med | V2 (P1-2) |
| F14 | FRED bundle cache/backfill (persist 10-series bundle; repair closed marks) | `.github/workflows/bond-agent.yml:126-148`; `alpha_engine/bond_data_fred.py:313`; `tools/backfill_*.py` | M | Med | V2 (P1-3) |
| F15 | Class-health contract: `status`,`activeRawCount`,`data_coverage`,`policyFrozen` in summary + CI assertion | `audit_trail/dashboard_generator.py:6830-6848`; `tests/test_dashboard_payload_contract.py` | M | Low-Med | V2 (P1-4) |
| F16 | MF classification-only (if any fund tickers exist): `MUTUAL_FUND_SYMBOLS` + gatekeeper `"MUTUAL_FUND":7` + dashboard tile | `alpha_engine/asset_class.py`; `ml_gatekeeper/gatekeeper.py:73`; `audit_trail/dashboard_generator.py:6763` | S–M | Low | ML, V3-PR |
| — | **VETO** — backfill `current_price = entry_price` (ME #1) | — | — | — | **REJECTED** (V2 Do-Not-Do #2: exact mechanism behind frozen-price artifacts) |
| — | **VETO** — build MF stub scanner/emitter emitting placeholder signals (ML 3.3) | — | — | — | **DEFER** (V3-PR: emits fabricated/empty output; classify only) |
| — | **VETO** — add MF to `CANONICAL_ASSET_CLASSES`/`_PER_ASSET_CLASSES` to "fix" absence | — | — | — | **REJECTED** (V2 Do-Not-Do #4; re-opens vacuous PASS) |

---

## 4. Conflicts

1. **BOND open-count layers disagree:** V4 = 1293 (`picks_now_live_pnl`) vs V2/ME = 15 (`active_raw`) vs ML = 2 (`live_picks.db`) vs 7 (fresh feed). Not a true contradiction — different data layers; root is ML's sync gap. Master plan must name which layer each claim refers to.
2. **BOND price-backfill method:** ME/V1 says stamp `current_price=entry_price`; V2 explicitly vetoes that (Do-Not-Do #2). Resolution: fetch a real mark (F4), never copy entry.
3. **MF build vs suppress:** ML proposes building a stub scanner/emitter; V1/V2/V3 recommend suppress + de-advertise. Resolution: classify-now (F16), emit-later; do NOT build a live pick class.
4. **`funds.html` role:** V3-QW notes `audit_dashboard/funds.html` exists but unconfirmed as the MF page; V2 finds no `mutual-funds.html`. Unresolved — verify before any wiring.

---

## 5. UNVERIFIED

- Post-fix BOND `win_rate_pct` exact value (only the old 127.8% invalidity is proven).
- Whether yfinance is currently reachable from GitHub Actions runner IPs.
- `mutual_fund_metadata.csv` contents (fund count / categories / `as_of` never parsed).
- Mutual-fund ranker runtime behaviour — never produced an output file (`mutut_fund_rankings.json` absent, no NAV cache).
- Live `asset_class_summary` at read time (all quotes from archived ~14:30Z payload).
- Worktree file *contents* vs `origin/main` (line numbers verified; file contents may differ — V2 explicitly flags this).
- Emitter attribution of the 13:39Z `alpha_engine_*` BOND rows (inferred from id prefix, no run log inspected).
- Whether any consumer reads `summary_picks.json` beyond diagnostics.
- Browser rendering of new badges (not visually verified).
- `funds.html` purpose (see Conflict 4).

---

## 6. P0 order (day-1)

1. **F1** — Kill vacuous PASS (foundational; fixes BOND/ETF/FUTURES false-green).
2. **F2** — De-advertise MF / `NOT BUILT` badge (**de-advertise, do NOT build a live MF pick class**).
3. **F3** — `summary_picks` WR>100% fix.
4. **F4** — BOND price coverage (real marks, not entry-copy).
5. **F5** — Cross-source dedupe (15→6).
6. **F6 + F7** — Sync feed→DB + emit exit events (grow closed sample from 3).
7. **F9** — FRED re-enable, then **F10** coverage gate.

Structural (P1, later): F12 → F13 → F14 → F15. MF F16 only if fund tickers must stop misclassifying as EQUITY/UNKNOWN.
