# Blocker 2 — Deep Analysis: clone_hl_copy Placeholder Stats Bypassing HC Gate

**Date:** 2026-04-22  
**Author:** Antigravity (independent review of user-reported blocker)  
**Severity:** 🔴 CRITICAL — pipeline integrity issue enabling non-edge picks to pass quality gates  
**Status:** CONFIRMED — user diagnosis validated against code + data

---

## 1. Executive Summary

The HC (High Conviction) quality gate in `audit_dashboard/hc_filter.js` is **mathematically correct** but is being **gamed by upstream data** from the `clone_hl_copy_*` copy-trader pipeline. All 50 CRYPTO picks that pass the gate share a pathological pattern: `score ≈ n ≈ fwd_wr`, with empty `trust_tier` and null `trust_score`. This is not edge — it is a **data generation bug** in the copy-trader clone pipeline that mints synthetic stats, which the gate then naively accepts.

**The gate is doing its job; the inputs are lies.**

---

## 2. Evidence Audit

### 2.1 The Identical-Triple Pattern (CONFIRMED)

User's finding: all 50 CRYPTO HC gate passes are `clone_hl_copy_*` rows with:

| Source Strategy | score | n | fwd_wr | Symbols |
|---|---|---|---|---|
| `clone_hl_copy_PensionFund_24M` | 100 | 100 | 100.0% | BTC, BNB, AVAX, LINK, NEAR, SUI, RENDER, HYPE, ONDO |
| `clone_hl_copy_lb_None` (longs) | 100 | 100 | 100.0% | Same basket |
| `clone_hl_copy_whale_433roi` | 85 | 85 | 85.7% | RENDER, ONDO |
| `clone_hl_copy_lb_None` (shorts) | 80 | 80 | 80.0% | BTC, ETH, ADA, XRP, SOL, DOGE, AVAX, LINK... |

**Why this is not a computed statistic:** A forward validation pipeline that independently measures win rate from closed trades produces values like 52.3%, 66.7%, 48.1% — fractions with denominators reflecting actual trade counts. `score=100, n=100, fwd_wr=100.0%` across 9 unrelated symbols is what you get from a **template or default initialization**, not from real market observation.

### 2.2 Trust Fields Missing (CONFIRMED)

All `clone_hl_copy_*` rows have:
- `trust_tier = ""` (empty string)
- `trust_score = null`

The HC gate (hc_filter.js L296-297, L316-320) reads these fields:
```javascript
var trust = Number(p.trust_score || p.trust_score_1 || 0);  // → 0
var trustTier = String(p.trust_tier || '').toUpperCase();     // → ""
```

Gate 3 (trust tier blacklist) checks if the tier is in `[SANDBOX, UNPROVEN, PROBATION, DEMOTED]`. An **empty string** is not in the blacklist — so the check **silently passes**. The trust score floor (Gate 6, L362-366) requires `trust ≥ 4` for CRYPTO, but `0 < 4` should fail... **unless** the score compound gate (L314) provides an alternate path: `score < 50 AND trust < 8 → reject`. With `score=100`, the compound check passes regardless of trust.

**Root cause:** The HC gate was designed assuming trust fields would always be populated. The clone pipeline doesn't populate them, creating a **bypass-by-omission**.

> [!IMPORTANT]
> Fix requires **either** the clone pipeline to properly populate trust fields **or** the HC gate to treat null/empty trust as a rejection (fail-closed rather than fail-open).

### 2.3 Cross-Check Against Dashboard Pipeline (CONFIRMED)

- **User's `active_picks.json` HC pass rate:** 50/126 = 39.7% (all clone_hl_copy_*)
- **`edge_report.md` on `dashboard_data.json`:** 1/31 = 3.2% HC pass rate
- **50× inflation** between the two JSON sources confirms different row populations with different stat quality

The `dashboard_data.json` pipeline (via `audit_trail/dashboard_generator.py`) populates `trust_tier` and `trust_score` from `getTrustTier()` at render time. The `active_picks.json` (via `alpha_engine/data/`) receives rows from copy-trader pipelines **before** trust enrichment — explaining why the fields are empty.

### 2.4 Prior Findings Confirm This Pattern

- `updates/2026-04-17-edge-deepscan-5-filter-catalog.md` §6 (lines 179-196): Flagged `HIGHFWWRABV55_SCOREABOVE50_V3` TV label as unbacked in code, with historical edge for the "Proven + High Confidence Combo" collapsing from n=94 to n=1.
- Same deepscan §3 row 4: "PROVEN + Conf 0.8-0.9 Combo: 71.3% WR PF 13.21 n=94" → **n=1, WR 0%, PnL −6.15%** in current data.
- System-wide metrics (from memory): WR 31.1%, PF 0.72 on ~3,500 trades — the aggregate book has **negative edge**, so any row showing 100% WR on 100 trades is structurally impossible in this system.

### 2.5 Code Path Traced: Where Clone Score Originates

Traced through `copy_trader_intel/generate_dashboard_data.py`:

1. **`compute_pick_score()`** (L285-385): Computes a 0-100 score from trader WR, PF, symbol specialization, consensus, PnL, and enrichment signals. This function produces **realistic scores** (e.g., 35-85 range) based on actual trader profile data.

2. **But `score=100` rows are not from this function.** The `clone_hl_copy_*` rows in `active_picks.json` carry pre-stamped `score`/`n`/`fwd_wr` fields that were **not computed by `compute_pick_score()`** — they were injected upstream, likely by the Hyperliquid clone pipeline that creates pick records with placeholder forward validation stats.

3. The `n=100` field is particularly telling: it suggests a **hardcoded default** (`n = score` as a template), not a forward trade count from `strat_fwd_trades` which would be 0 or a small integer for new clone strategies.

4. The `copytrader_verification_report.json` shows **42 status mismatches** for clone picks (all `source_status: "open"` vs `resolved_status: "closed"`) — confirming the pipeline doesn't properly track position lifecycle for these rows.

---

## 3. Technical Root Cause

```
Copy Trader Clone Pipeline                    HC Gate (hc_filter.js)
─────────────────────────                    ──────────────────────
Mint clone_hl_copy_* row                     Gate 1: score >= 40   ✅ (score=100)
  ├── score = ???                            Gate 2: score >= 50 OR trust >= 8  ✅ (score=100)
  ├── n = score  ← PLACEHOLDER              Gate 3: trust_tier not blacklisted  ✅ (empty = not in list)
  ├── fwd_wr = score  ← PLACEHOLDER         Gate 4: fwd_trades >= 5  ✅ (n=100)
  ├── trust_tier = ""  ← NOT POPULATED      Gate 5: fwd_wr >= 40%  ✅ (100%)
  └── trust_score = null  ← NOT POPULATED   Gate 6: trust_score >= 4  ❌... but:
                                                     → L314: score(100) >= 50 → compound gate bypassed
                                             Gate 7: confidence checks → pass
                                             Gate 8: regime checks → pass
                                             Gate 9: independent groups → skip (no sources)
                                             
                                             Result: PASS ← WRONG (data is fake)
```

The gate was designed for picks with **real forward validation data**. The clone pipeline emits rows that satisfy every numeric threshold through **coincidental placeholder values**, not demonstrated edge.

---

## 4. Feedback on User's Option Matrix

| Option | Assessment | Risk |
|--------|-----------|------|
| **(a)** Place single real HC pass from `edge_report.md` | **Good interim discipline.** Matches what the gate was designed for. But requires manual identification of which pick ID that is. | Low risk, low throughput |
| **(b)** Drop `fwd_wr ≥ 55` and route non-clone sources | **Dilutes the label promise.** If the account is named `HIGHFWWRABV55`, the trades should match. Semantic integrity matters for audit trail. | Medium risk — label mismatch creates future confusion |
| **(c)** Accept clone_hl_copy picks explicitly | **Highest risk.** Must be documented as an override. Given `trust_tier=""` and `trust_score=null`, these picks have **zero provenance** — you're trading on a label, not on evidence. | High risk — documented override required |
| **(d)** Fix the placeholder-stat pipeline first | **Correct long-term answer.** Fix means: (1) populate `trust_tier`/`trust_score` on clone rows before they enter the gate, (2) derive `fwd_wr` and `n` from actual closed trade history in `highscore_pick_history.json`, (3) reject rows where `score == n == fwd_wr` as a sanity check. | Lowest risk, highest effort |

### Recommended Path: **(d)** with **(a)** as interim

**Immediate (< 1 hour):**
- Add a **sanity guard** to `hc_filter.js`: if `trust_tier` is empty/null AND `trust_score` is null/0, **reject** the pick (fail-closed). This is a one-line fix:
  ```javascript
  // After L297, before Gate 3:
  if (!trustTier && trust <= 0) return false;  // Reject picks with no trust provenance
  ```
- This alone blocks all 50 placeholder-stat picks without touching the upstream pipeline.

**Short-term (1-3 days):**
- Trace the exact code path that mints `score=n=fwd_wr` on clone rows. Candidates:
  - `copy_trader_intel/main.py` (L830-833) — strategy name extraction
  - Whichever module stamps `forward_wr`, `forward_trades`, and `score` on `active_picks.json` rows
- Wire clone picks through `load_copytrader_history_scorebook()` to get real PnL-based stats from `highscore_pick_history.json`

**Medium-term (1 week):**
- Add the `config/tv_paper_account_filters.json` mapping recommended in deepscan §6
- Add a CI check: `tools/audit_tv_account.py HIGHFWWRABV55_SCOREABOVE50_V3` runs weekly and flags when no picks qualify

---

## 5. Pipeline Integrity Gaps (Beyond This Blocker)

| Gap | Where | Impact |
|-----|-------|--------|
| Trust fields not populated on clone rows | Clone mint pipeline → `active_picks.json` | Bypasses trust-based gates |
| `score == n == fwd_wr` not caught as anomaly | `hc_filter.js` evaluateHcGates1to9 | Placeholder data passes numeric checks |
| Two trust vocabularies coexist | `getTrustTier()` vs stamped `trust_tier` on closed picks | RELIABLE/BANNED/UNTRUSTED never match PROVEN/DEVELOPING/WATCH/SANDBOX |
| 42 status mismatches in clone picks | `copytrader_verification_report.json` | Open/closed lifecycle not tracked |
| Non-crypto classes hard-rejected by HC strict | `template.html` L11240 | COMMODITY/FUTURES/BOND/ETF always return false even with edge |

---

## 6. Action Checklist

- [ ] **Immediate:** Add fail-closed guard in `hc_filter.js` for empty trust_tier + null trust_score
- [ ] **Trace:** Find the exact module stamping `score=n=fwd_wr` on clone_hl_copy rows in `active_picks.json`
- [ ] **Fix:** Wire clone picks through the history scorebook for real forward stats
- [ ] **Reconcile:** Unify trust-tier vocabulary (RELIABLE/BANNED vs PROVEN/DEVELOPING)
- [ ] **Audit:** Add `score == n` anomaly detector as a pre-gate sanity check
- [ ] **Document:** Record user's decision on option (a)-(d) in this file once made
- [ ] **TV Account:** Create `config/tv_paper_account_filters.json` mapping

---

## 7. Cross-References

| File | Relevance |
|------|-----------|
| [hc_filter.js](file:///e:/findtorontoevents_antigravity.ca/audit_dashboard/hc_filter.js) | HC gate implementation (501 lines, 9 gates) |
| [active_picks.json](file:///e:/findtorontoevents_antigravity.ca/alpha_engine/data/active_picks.json) | Source data with 126 rows, 50 clone passes |
| [deepscan-5](file:///e:/findtorontoevents_antigravity.ca/updates/2026-04-17-edge-deepscan-5-filter-catalog.md) | §6 flagged HIGHFWWRABV55 label as unbacked |
| [generate_dashboard_data.py](file:///e:/findtorontoevents_antigravity.ca/copy_trader_intel/generate_dashboard_data.py) | Copy trader scoring pipeline |
| [copytrader_verification_report.json](file:///e:/findtorontoevents_antigravity.ca/tools/data/copytrader_verification_report.json) | 42 clone status mismatches |
| [quality_gates.py](file:///e:/findtorontoevents_antigravity.ca/audit_trail/quality_gates.py) | Python-side quality gates (4,500+ lines) |

---

*This document supersedes `updates/2026-04-22-feedback-blocker2.md` (earlier draft from an interrupted session). Both are preserved for audit trail.*
