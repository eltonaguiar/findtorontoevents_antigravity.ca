# Hourly Audit — 2026-05-12 05:00Z

**Generated:** 2026-05-12T05:00Z  
**Dashboard snapshot:** `2026-05-12T04:06:19Z` (≈59 min old at audit time)  
**Branch:** audit/hourly-05z  
**Auditor:** Claude Sonnet 4.6 (automated hourly loop)

---

## 1. Dashboard Refresh Status

- `git pull --rebase origin main` completed clean (no local stash needed).
- `audit_dashboard/data/dashboard_data.json` generated at **2026-05-12T04:06:19Z**.
- `total_closed_picks`: 31,015 | `recent_closed` window: 3,500 (most recent by close time).
- System-wide summary: **WR 42.7% / PF 1.09 / Sharpe(annual) 1.17 / MDD(30d) 10.92%**.

---

## 2. Per-Asset PF/WR — 24h / 7d / 30d Windows

Computed from `picks.recent_closed` (n=3,500 cap). Baseline from CLAUDE.md / issues #686 #693.

### 2a. 24-Hour Window

| Class | n | WR | PF | Sum PnL% | vs Baseline |
|---|---|---|---|---|---|
| CRYPTO | 77 | 63.6% | 2.62 | +72.96% | ▼ from 3.54 (−0.92, normal variance) |
| EQUITY | 13 | 7.7% | 2.66 | +5.88% | small n, skewed by 1-2 big wins |
| FOREX | 12 | 66.7% | 3.32 | +7.70% | **🚀 recovery signal (PR #687 effect)** |
| COMMODITY | 2 | 100% | ∞ | +10.17% | too small |
| ETF | 3 | 100% | ∞ | +6.21% | too small |
| BOND | 0 | — | — | — | — |

### 2b. 7-Day Window

| Class | n | WR | PF | Sum PnL% | vs Baseline | Verdict |
|---|---|---|---|---|---|---|
| CRYPTO | 855 | 45.0% | **1.46** | +340.65% | ▲ from 1.33 (+0.13) | ✅ improving |
| EQUITY | 31 | 41.9% | **5.29** | +100.07% | ▲ from 0.87 (+4.42) | **🚀 goldmine_6x kill confirmed** |
| FOREX | 79 | 24.1% | **1.01** | +0.22% | ▲ from 0.14 (+0.87) | **🚀 JPY-cross fix working** |
| COMMODITY | 17 | 94.1% | 39.96 | +74.87% | — | small n; real signal pending n≥30 |
| ETF | 13 | 100% | ∞ | +26.83% | ▲ from 1.24 | small n |
| BOND | 0 | — | — | — | — | — |

### 2c. 30-Day Window

| Class | n | WR | PF | Sum PnL% | vs Baseline | Verdict |
|---|---|---|---|---|---|---|
| CRYPTO | 1,879 | 47.0% | **1.45** | +642.15% | ▲ from 1.33 (+0.12) | ✅ solid |
| EQUITY | 134 | 57.5% | **3.06** | +276.29% | ▲ from 1.41–2.18 | ✅ Tier-2 confirmed |
| FOREX | 574 | 41.5% | **0.64** | −24.56% | ▼ from 0.97 (tail drag) | ⚠️ pre-kill history still dragging 30d |
| COMMODITY | 102 | 56.9% | **6.44** | +131.56% | ▲ from 1.78 (+4.66) | **🚀 structural improvement** |
| ETF | 47 | 83.0% | **6.44** | +83.37% | ▲ from 1.24 (+5.20) | **🚀 Tier-1 territory** |
| BOND | 0 | — | — | — | n=12 full-history; below charter floor | — |

### Non-crypto full-history (all-time from `summary.non_crypto_performance`)

| Class | Closed | WR | Total PnL% |
|---|---|---|---|
| EQUITY | 303 | 51.5% | +339.31% |
| COMMODITY | 168 | 43.5% | +123.20% |
| ETF | 99 | 57.6% | +46.85% |
| FOREX | 1,032 | 21.1% | +15.43% |
| BOND | 12 | 50.0% | −1.53% |

---

## 3. Issue #693 — EQUITY 7d/14d/30d Divergence Monitor

Issue #693 tracked EQUITY monotonic deterioration (30d PF 2.18 → 14d 1.05 → 7d 0.87).

**Post-PR-#692 update (goldmine_6x_consensus killed):**
- EQUITY 7d: PF **5.29** (was 0.87) — reversal confirmed ✅
- EQUITY 30d: PF **3.06** (was 1.41–2.18) — improved ✅
- **Action:** Issue #693 deterioration thesis is resolved. Recommend closing #693 once 14d window can be re-verified (~7 days from now). Stocks_rsi2_pullback (WR 35.7% on n=14) remains a monitor candidate per #693.

---

## 4. PR Triage

### Open PRs at audit time: **1** (PR #916 only)

| PR | Title | CI | Mergeable | Request_Changes | Action |
|---|---|---|---|---|---|
| #916 | feat(commodity): seasonal supply-demand strategy | `gate` FAIL / `test(3.12)` FAIL | unknown | None | **HOLD — CI red** |

**HOLD set checked** (#660 #658 #681 #661): not present in open PR list — previously closed.  
**Author-rebase PRs checked** (#669 #676 #608 #665 #644 #597 #615 #655): not present in open PR list — previously merged/closed.

### PRs merged this hour: **0**

---

## 5. Mutation Analysis — New Strategy Kill Candidates

`python tools/mutation_analysis.py --json` run against `closed_picks_fast.json`.

### Section 1 — Direction-flip signals

| Strategy | Bad side | n | WR | PF | Kill action |
|---|---|---|---|---|---|
| `ig_contrarian_sentiment` | LONG | 177 | **16.9%** | ~0.2 est. | Kill LONG-only; SHORT (n=48, WR 62.5%) healthy |
| `myfxbook_retail_contrarian` | LONG | 122 | **13.1%** | ~0.15 est. | Investigate LONG-only kill |
| `cta_cross_asset_tsmom` | LONG | 75 | 26.7% | 1.20 | PF above kill floor; monitor only |

**Note:** `ig_contrarian_sentiment` and `myfxbook_retail_contrarian` do **not** appear in `recent_closed` 3,500 window — may already be idle. Verify activity before blocking.

### Section 3 — Symbol-variance signals

| Strategy / Symbol | n | WR | Action |
|---|---|---|---|
| `rapid_fire` / UUSDT | 34 | 0% | Meets symbol-block threshold; verify activity status |
| `rapid_fire` / TAOUSDT | 18 | 5.6% | Below n=20; monitor |
| `quan_engine` / MATICUSDT | est. | 0% | HYPEUSDT already blocked by PR #694; add to block list |

**Consensus gate:** No new kills actioned this hour — all candidates require 3+ AI consensus per CLAUDE.md. Posted findings to issue #686.

---

## 6. Key Findings Summary

| Finding | Evidence | Priority |
|---|---|---|
| EQUITY recovery confirmed post-PR-#692 | 7d PF 0.87→5.29 | P0 — close #693 watch |
| FOREX 7d PF 0.14→1.01 (PR #687 working) | 7d window, n=79 | P1 — continue monitoring |
| FOREX 30d still PF 0.64 | Pre-kill historical drag | Expected; no action |
| CRYPTO 7d/30d improving | PF 1.33→1.46/1.45 | P2 — do not destabilize |
| ETF + COMMODITY 30d structural improvement | PF 6.44x both classes | P2 — real signal, small n still |
| `ig_contrarian_sentiment` LONG 16.9% WR | n=177 in closed_picks_fast | Needs activity check before kill |
| PR #916 CI red | gate+test(3.12) fail | HOLD; needs author fix |

---

## 7. Next Actions

1. **#916 author**: fix `gate` + `test(3.12)` failures — do not merge until all CI green.
2. **Activity check**: grep `ig_contrarian_sentiment` and `myfxbook_retail_contrarian` in `picks.active` before proposing direction-block PR.
3. **Issue #693**: monitor EQUITY 14d window for 7 more days to confirm full recovery; if PF≥1.5, close issue.
4. **FOREX 30d**: expect organic improvement as post-kill picks replace pre-kill picks. No code action needed.
5. **quan_engine / MATICUSDT**: verify symbol is not already blocked; if active, add to `BLOCKED_STRATEGY_SYMBOL_PAIRS` with 3+ AI consensus.

---

*Refs: issue #685 (resolver-rescope DONE), #686 (per-asset quality), #693 (EQUITY divergence monitor), PR #916 (commodity seasonal HOLD)*
