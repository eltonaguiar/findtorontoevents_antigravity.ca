# Hourly Audit — 2026-05-14 04Z

**UTC time:** 2026-05-14T04:10Z  
**Session:** Claude Sonnet 4.6 autonomous hourly check (1 of N)  
**Priority goal:** #1 — Phenomenal performance across all asset classes on /audit

---

## 1. DASHBOARD REFRESH STATUS

- **Pull result:** `git pull --rebase origin main` — already up to date (forced-update from b16328ef)
- **dashboard_data.json meta:** no `generated_at` field (meta section absent in current payload)
- **recent_closed n:** 3,500 picks; `closed_at` range 2026-02-21 to 2026-05-14

---

## 2. PER-ASSET PF/WR — WINDOWED ANALYSIS

All numbers computed from `picks.recent_closed` using `closed_at` as the trade-close timestamp.

### 2a. asset_class_health (verdict-grade, all-time post-resolver-v2)

| Class | PF | WR | n |
|---|---|---|---|
| CRYPTO | 1.34 | 46.4% | 7,882 |
| EQUITY | 1.55 | 51.4% | 416 |
| COMMODITY | 4.03 | 70.5% | 281 |
| FOREX | 0.81 | 52.0% | 331 |
| ETF | 1.41 | 56.6% | 106 |
| BOND | 0.66 | 54.5% | 11 |
| FUTURES | N/A | 0.0% | 0 |

Note: FOREX all-time PF 0.81 reflects the tail of the pre-kill regime. Post-kill recent windows (see §2c) show recovery.

### 2b. Windowed (recent_closed by closed_at)

| Class | 24h n | 24h PF | 24h WR | 7d n | 7d PF | 7d WR | 30d n | 30d PF | 30d WR |
|---|---|---|---|---|---|---|---|---|---|
| CRYPTO | 118 | **0.87** | 37.3% | 823 | 1.24 | 42.5% | 2,874 | 1.30 | 45.7% |
| EQUITY | 7 | 0.25 | 14.3% | 35 | 1.03 | 22.9% | 131 | **2.29** | 52.7% |
| COMMODITY | 0 | — | — | 14 | inf | 100% | 47 | **7.88** | 80.9% |
| FOREX | 9 | 1.50 | 33.3% | 45 | **1.87** | 17.8% | 88 | 1.46 | 28.4% |
| ETF | 3 | inf | 100% | 15 | 1.60 | 53.3% | 55 | 3.99 | 72.7% |
| BOND | 0 | — | — | 0 | — | — | 0 | — | — |

### 2c. Delta vs documented baseline

| Class | Window | Baseline | Current | Delta | Signal |
|---|---|---|---|---|---|
| CRYPTO | 24h PF | 3.54 | 0.87 | -2.67 | RED — sharp drop (n=118, may be noise) |
| CRYPTO | 7d PF | 1.33 | 1.24 | -0.09 | YELLOW — slight decline |
| CRYPTO | 30d PF | 1.33 | 1.30 | -0.03 | GREEN — stable |
| EQUITY | 7d PF | 0.87 | 1.03 | +0.16 | GREEN — recovering post #692 |
| EQUITY | 30d PF | 1.41–2.18 | 2.29 | at/above high end | GREEN — strong |
| FOREX | 7d PF | 0.14 (pre-#687) | 1.87 | +1.73 | GREEN — dramatic recovery |
| FOREX | 30d PF | 0.97 (pre-kill) | 1.46 | +0.49 | GREEN — improved |

**Most significant signal:** FOREX 7d PF 0.14 → 1.87 following PR #687 (JPY-cross BUY block fix) + PR #692 (forex_carry_momentum + goldmine_6x kills). This is the largest positive delta in the system.

**Watch item:** CRYPTO 24h PF 0.87 on n=118. The 7d/30d are stable; 24h noise at this sample size is expected. Do not act on 24h signal alone — watch the 7d window in the next cycle.

**COMMODITY:** 30d PF 7.88, 7d PF=inf (14/14 wins). Comfortably above Tier-2. PR #674 ETF/B11 and existing cftc_cot kill (PR #683) appear effective.

---

## 3. PR TRIAGE

### 3a. Open PRs — CI status and merge decisions (04:10Z)

| PR | Title | CI status | Reviews | Action |
|---|---|---|---|---|
| #1007 | deep-dive verification matrix | 4 checks in-progress | none | WAIT — CI running |
| #1006 | docs(mmr-corrections) | scan ✅ only | none | HOLD — mergeable_state=unknown |
| #1005 | fix(walkforward-gate) n-floor | audit ✅ scan ✅ | none | HOLD — test suite absent for code PR |
| #1004 | fix(cot-ledger) atomic+lock | test(3.11) FAIL gate FAIL | none | HOLD — CI failed |
| #1003 | feat(equity-rsi2-short) | test(3.11) FAIL gate FAIL | none | HOLD — CI failed |
| #1002 | fix(quality-gates) quarantine zombies | audit ✅ scan ✅ | none | HOLD — test suite absent for code PR |
| #996 | docs(mmr-synthesis) | scan ✅ only | none | HOLD — mergeable_state=unknown |
| #995 | fix(etf-sector-momentum) TLT/HYG | test(3.11) FAIL gate FAIL | none | HOLD — CI failed |
| #994 | fix(multi-asset-cot) emit dedup | scan ✅ only | none | HOLD — test suite absent for code PR |
| #993 | fix(walkforward) BOND+FUTURES | test cancelled gate FAIL | none | HOLD — CI failed |
| #986 | audit(money-maker-ready) | scan ✅ only | none | HOLD — mergeable_state=unknown |

**Merges this hour: 0**

Rationale: All code PRs with only scan/audit checks (no test/gate suite) are held pending full CI confirmation. Docs-only PRs are held because mergeable_state=unknown (GitHub has not computed merge conflict status). No PR satisfies all three criteria: MERGEABLE + ALL_CI_GREEN + no REQUEST_CHANGES.

### 3b. HOLD set — confirmed already resolved

| PR | Final status |
|---|---|
| #660 | MERGED 2026-05-03 (already done, not re-mergeable) |
| #658 | CLOSED 2026-05-03 (not merged — Plan v2.1 fabricated stats) |
| #681 | CLOSED 2026-05-03 (not merged — fabricated WR table, Wire-Up Rule fail) |
| #661 | MERGED 2026-05-03 (infrastructure v2.0) |

### 3c. Author-rebase set — all resolved

All 8 PRs in the author-rebase watch set are resolved: #669/#676/#608/#665/#644/#597/#615 merged; #655 closed without merge. No rebase actions needed.

---

## 4. MUTATION ANALYSIS

Run: `python tools/mutation_analysis.py --json` at 04:11Z

### 4a. Direction-asymmetry candidates (n>=20, WR<35%)

| Strategy | Direction | n | WR | Vs. opposite | Action |
|---|---|---|---|---|---|
| `ig_contrarian_sentiment` | LONG | 190 | **16.3%** | vs SHORT 62.5% (46pp gap) | Post to #686 |
| `myfxbook_retail_contrarian` | LONG | 122 | **13.1%** | vs SHORT 46.2% (33pp gap) | Post to #686 |
| `quan_engine_swing` | LONG | 104 | **26.0%** | vs SHORT 60.0% (34pp gap) | Monitor |
| `cta_cross_asset_tsmom` | LONG | 81 | 30.9% | vs SHORT 53.1% (22pp gap) | Monitor |

PF values not computable from `recent_closed` (these strategies route through a separate source path). Full mutation / inverse / symbol-rotation analysis required before any kill. **No BLOCKED list additions without 3+ AI consensus per CLAUDE.md.**

### 4b. Symbol-level concern — rapid_fire × UUSDT

- UUSDT: n=34, WR=0% under rapid_fire
- Matches existing kill pattern (SOLVUSDT/ORCAUSDT already blocked in BLOCKED_STRATEGY_SYMBOL_PAIRS)
- Meets criteria (a) pattern match, (b) n>=20, (c) WR<35%
- **Recommendation:** Add `("rapid_fire", "UUSDT")` to BLOCKED_STRATEGY_SYMBOL_PAIRS — but requires 3+ AI consensus before merge. TAOUSDT (n=18) below n=20 floor — monitor only.

### 4c. System symbol-concentration (sandbox candidates)

- `quan_engine`: MATICUSDT 0% WR, ONDOUSDT 22%, SOLUSDT 23% — symbol-rotation candidates alongside HYPEUSDT (already blocked PR #694)
- `multi_asset_copytrader`: ZW=F, PL=F, GC=F all 0% WR — n unknown, verify before acting
- `rapid_fire`: UUSDT/ESPUSDT/TAOUSDT symbol allowlist needed

---

## 5. ISSUE COMPLIANCE

**Issue #685 (resolver-rescope DONE):**
- No resolver-rescope PRs opened or pending. ✅
- No PR body references "widen re-resolve scope". ✅

**Issue #686 (per-asset quality regression):**
- FOREX recovery confirmed post kills. ✅
- EQUITY 7d partial recovery confirmed post #692. ✅
- New mutation findings (ig_contrarian_sentiment LONG, myfxbook_retail_contrarian LONG) to be posted.

**Issue #693 (EQUITY 7d/14d/30d divergence monitor — CLOSED):**
- Closed as completed 2026-05-13. EQUITY 30d PF 2.29 confirms long-run strength intact. ✅
- stocks_rsi2_pullback 7d WR ~35% on n<20 — continue monitoring per issue guidance.

---

## 6. NEXT CYCLE PRIORITIES

1. Re-check #1007 CI (4 checks in-progress) — if green and no REQUEST_CHANGES, merge
2. Re-check #1002/#1005/#994 for test suite completion — merge if all green
3. Post mutation direction-asymmetry findings to issue #686
4. Monitor CRYPTO 24h PF — if 7d dips below 1.10 on n>=200, investigate strategy attribution
5. rapid_fire × UUSDT consensus check (need Kimi + Copilot agreement before adding to BLOCKED_STRATEGY_SYMBOL_PAIRS)

