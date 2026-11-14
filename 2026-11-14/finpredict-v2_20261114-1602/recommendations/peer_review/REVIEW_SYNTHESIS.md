# Peer Review Synthesis — 2026-11-14

**Reviewers:** PR1 (crypto/commodity), PR2 (equity/ETF/bond/MF), PR3 (forex/futures/CI), PR4 (overall).
**Review clock:** 2026-11-14T16:32Z.
**Question:** are the audit and the remediation plans coherent enough to hand to a master-plan agent?

## Verdicts

| Reviewer | Scope | Verdict | Meaning |
|---|---|---|---|
| PR1 | CRYPTO + COMMODITY | **FAIL** | P0 fixes are safe; COMMODITY/FUTURES structural premise was wrong (both gate-blocked; commodity generator uses crypto proxies) |
| PR2 | EQUITY + ETF + BOND + MF | **FAIL** | Core counts reproduce; one acceptance test cannot pass; UNQUOTED/LAST_CLOSE collision; MF evidence was stale |
| PR3 | FOREX + FUTURES + Actions/CI | **PASS (conditional)** | 4 factual corrections; no P0 sequence change |
| PR4 | Overall coherence | **FAIL** | 9 numeric conflicts + 6 contradictory fix mechanics; central FAIL verdict is not in dispute |

**Net:** the audit conclusion is robust; the first draft of the recommendations needed correction. All corrections have been applied to `../MASTER_AUDIT.md`, `../QUICK_WINS.md`, and the per-class plans.

## Corrections applied

| # | Correction | New value |
|---|---|---|
| 1 | Duplicate IDs | **248 groups / 297 extra rows / 56 cross-ledger** |
| 2 | Quoted OPEN | **177 entry-differing; 123 also non-zero PnL; 29 exact; 485 null** |
| 3 | `summary_picks` | **7 classes WR>100%; 9 with `wins+losses > resolved`** |
| 4 | FUTURES history | **0 in `recent_closed`; full history n=13; intrabar n=52** |
| 5 | FOREX date-only | **105/277 `entry_time`** (not 12) |
| 6 | FOREX block | **0 call sites; 0/277 pass; 4 retired strategies emit ~95/277** |
| 7 | COMMODITY/FUTURES | Both in `BLOCKED_ASSET_CLASSES` (`quality_gates.py:1724`); COMMODITY uses crypto proxies |
| 8 | Mutual funds | Unbuilt in production/`origin/main`; untracked prototype exists in the main checkout |
| 9 | v4 | Internally contradictory (INDEX says 0 active/26 d; its own deep-dives say 20 active/14:30Z) |
| 10 | SQLite layer | `live_picks.db` 128/129 stale, 8 PnL sign bugs, `audit_trail.db` empty |

## Fix mechanics now unified

- **Quote status:** `LIVE` · `LAST_CLOSE` · `STALE` · `UNQUOTED` · `PLACEHOLDER`; never `0.00%` for a missing quote.
- **`pnl_pct`:** `null` when unquoted; never a fabricated 0.
- **Dedup:** ID key for exact duplicates; economic key `(symbol, strategy, direction, entry_time, entry_price)` for cross-source duplicates.
- **`summary_picks`:** one terminal-status population for resolved/wins/losses; clamp + assert.
- **Class field:** `class_canonical` (one name) with `class_raw` + `class_mismatch` preserved.
- **UI target:** generated `audit_dashboard/index.html` + `template.html` must consume the same status contract.

## Peer fixes explicitly vetoed

`DELETE` ghost rows · `UPDATE TIME_EXIT → LOST, pnl_pct=0.0` · `EXPIRED_FORCE` mass rewrite · invert the ML gate · unblock FUTURES/COMMODITY without a real feed · add `MUTUAL_FUND` to canonical classes before an emitter exists · re-enable the audit-dashboard `push:` trigger.

## Unreferenced peer deliverables now noted

- v1 `quick-wins/**` (binomial CI, `edge_ratio` mismatch, `INSUFFICIENT` at `forward_trades==0`, outlier clamp, visibility-floor exposure).
- v3 `2026-11-14T161500Z/QUICK_WINS/**` and `T161700Z/PEER_REVIEW/**`, incl. the runnable `tools/pi_data_hygiene.py`.
- v4 `proposed_fixes/**` (contains the destructive SQL and dangerous policy reversals — reject, do not apply).
- ML peer `updates/2026-11-14-ML-AUDIT-childlike-airport/proposed_fixes/**`.
- `updates/2026-11-14-hilarious-seer-audit-summary.md` + `audit_quickwins/2026-11-14-hilarious-seer/**` (independent FAIL; regime-layer and PnL cross-reference findings).

## Original-brief questions still only partially answered

- Warning census across all 365 workflows — `UNVERIFIED`.
- Root causes for mid-retry failures — `UNVERIFIED`.
- Fair-market vs arbitrary `FORCE_CLOSED`/`TIME_EXIT` exits — `UNVERIFIED`.
- Exact age of the AI Challenge registry — `UNVERIFIED` (broken state is verified; timestamps absent).
- 234 closed FUTURES rows in JSON feeds (ML peer) — peer-reported, not independently reproduced.

## Hand-off recommendation

Use `../QUICK_WINS.md` as the execution order. Do **not** start Phase 3 (strategy kill/keep or real-money sizing) until the Phase 0 truth fixes and the Phase 1 data-consistency gates are green.
