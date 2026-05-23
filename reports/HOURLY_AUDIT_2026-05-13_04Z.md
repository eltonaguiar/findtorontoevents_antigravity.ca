# Hourly Audit — 2026-05-13 04Z

**Generated:** 2026-05-13T04:30Z  
**Dashboard snapshot:** 2026-05-13T02:20:51Z (auto-refresh via [skip ci] hourly cron, healthy)  
**Session context:** Post-8-PR merge day (#684 #674 #673 #664 #683 #687 #692 #694 — all cross-AI verified)

---

## 1. Dashboard Refresh Status

`git pull --rebase origin main` completed. Latest `dashboard_data.json` timestamp: **2026-05-13T02:20:51Z** (~2h old at audit time). 6 files updated on pull (trader log, portfolio, prediction history, futures backtest data, GHA monitor).

---

## 2. Per-Asset Metrics — 24h / 7d / 14d / 30d Windows

Computed from `picks.recent_closed` (n=3,500). Baseline from CLAUDE.md (2026-05-03T00:06Z) and issue #686 (2026-05-02 19:55Z).

### Long-run `asset_class_health` (full history, dashboard generated)

| Class | PF | WR% | vs Baseline PF | vs Baseline WR |
|---|---|---|---|---|
| CRYPTO | 1.37 | 46.6 | +0.12 | +2.0pp |
| EQUITY | 1.58 | 52.0 | +0.17 | -0.7pp |
| FOREX | 0.63 | 41.4 | +0.36 | -5.0pp |
| COMMODITY | 4.08 | 70.7 | **+2.30** | +23.8pp |
| ETF | 1.38 | 55.8 | +0.14 | +0.6pp |
| BOND | 0.66 | 54.5 | -1.06 | -1.1pp |
| FUTURES | N/A | 0.0 | — | — |

### Windowed metrics (recent_closed)

| Class | 24h n/PF/WR% | 7d n/PF/WR% | 14d n/PF/WR% | 30d n/PF/WR% |
|---|---|---|---|---|
| CRYPTO | 163/0.98/31.3 | 940/1.30/41.0 | 1582/1.39/45.1 | 2799/1.27/44.7 |
| EQUITY | 5/0.00/0.0 *(n<10)* | 35/**3.33**/37.1 | 53/**2.45**/43.4 | 127/**2.61**/55.1 |
| FOREX | 10/**1.97**/30.0 | 75/1.00/21.3 | 172/0.68/20.3 | 187/0.64/19.8 |
| COMMODITY | 6/inf/100.0 *(n<10)* | 18/**44.07**/94.4 | 36/**31.01**/91.7 | 47/**7.88**/80.9 |
| ETF | 7/0.00/0.0 *(n<10)* | 20/**2.65**/65.0 | 27/**2.44**/63.0 | 54/**3.88**/72.2 |
| BOND | 0/—/— | 0/—/— | 0/—/— | 0/—/— |
| FUTURES | 0/—/— | 0/—/— | 0/—/— | 0/—/— |

*Note: 24h small-n (n<10) cells are noise-dominated; ignore PF/WR for EQUITY/ETF 24h.*

### Deltas vs issue #686 baseline (2026-05-02 19:55Z)

| Class | #686 7d PF/WR | Now 7d PF/WR | Delta | Driver |
|---|---|---|---|---|
| CRYPTO | 1.21 / 41% | 1.30 / 41.0% | +0.09 / flat | Organic regime improvement |
| EQUITY | 0.87 / 41% | **3.33 / 37.1%** | **+2.46 PF** | PR #692 goldmine_6x kill |
| FOREX | 0.14 / 10.7% | **1.00 / 21.3%** | **+0.86 PF / +10.6pp** | PR #687 JPY-cross BUY fix |
| COMMODITY | 1.18 / — | **44.07 / 94.4%** | ⬆ stellar | PR #683 cftc_cot noise kill |
| ETF | 1.57 / — | **2.65 / 65.0%** | +1.08 PF | Organic + noise kill effect |

---

## 3. Issue #693 — EQUITY Divergence Monitor: RESOLVED

Per issue #693 acceptance criterion: *"If EQUITY 14d returns to PF ≥ 1.5 within 7 days post-#692, the deterioration was concentrated in goldmine_6x and the kill was sufficient."*

| Window | Pre-#692 (issue #693) | Now (post-#692) |
|---|---|---|
| 30d | 2.18 | **2.61** |
| 14d | 1.05 | **2.45** |
| 7d | 0.87 | **3.33** |

**EQUITY 14d PF = 2.45 >> 1.5 threshold. Criterion met.** The monotonic decline documented in issue #693 was entirely attributable to `goldmine_6x_consensus`. Remaining risk: `stocks_rsi2_pullback` at 7d WR 35.7% / n=14 — below n=20 floor, continue passive monitoring per #693 §4.

**→ Issue #693 should be closed as resolved.**

---

## 4. PR Triage

### Open PRs (5 total — page 2 empty, confirmed complete list)

| PR | Title | gate | test(3.11) | Verdict |
|---|---|---|---|---|
| #949 | feat(futures): Donchian breakout + term structure | FAILURE | FAILURE | HOLD — CI red |
| #948 | feat(forex): Donchian Channel Breakout / Turtle | FAILURE | FAILURE | HOLD — CI red |
| #946 | Copilot: confluence-based forex & futures picks | FAILURE | FAILURE | HOLD — CI red + strategic concern |
| #943 | feat(audit): system staleness detection | FAILURE | FAILURE | HOLD — CI red |
| #942 | feat(audit): anti-overfit validator default-ON | FAILURE | FAILURE | HOLD — CI red |

**Merged this hour: 0.** All 5 fail CI on `test(3.11)` and `gate`. Zero merges.

**Strategic note on #946 (Copilot confluence FX+futures):** Adds new FOREX strategies while FOREX 30d PF=0.64 (sub-floor). Even if CI cleared, content is premature — FOREX must recover WR above 35% sustained before adding new signal volume.

### HOLD set (#660 #658 #681 #661): All closed — no action needed.

### Author-rebase set (#669 #676 #608 #665 #644 #597 #615 #655): All merged or closed — no action needed.

---

## 5. Mutation Analysis — New Kill Candidates

Run: `python tools/mutation_analysis.py --json` at 04:15Z on 2026-05-13.

### Direction asymmetry findings (Section 1)

| Strategy | LONG n/WR% | SHORT n/WR% | Spread | Status |
|---|---|---|---|---|
| `ig_contrarian_sentiment` | 190 / **16.3%** | 48 / 62.5% | 46pp | Kill candidate (LONG) — n≥20, WR<35% |
| `quan_engine_swing` | 104 / **26.0%** | 5 / 60.0% | 34pp | Watch — SHORT n<20 |
| `myfxbook_retail_contrarian` | 122 / **13.1%** | 13 / 46.2% | 33pp | Watch — SHORT n<20 |
| `cta_cross_asset_tsmom` | 75 / **26.7%** | 147 / 53.1% | 26pp | SHORT-only mutation candidate |

### Symbol-level kill candidates (new)

| System | Symbol | n | WR% | Kill criteria met? |
|---|---|---|---|---|
| `rapid_fire` | UUSDT | 34 | **0.0%** | YES — n≥20, WR<35%, matches HYPEUSDT pattern |
| `rapid_fire` | TAOUSDT | 18 | 5.6% | NO — n<20 floor |

### Assessment vs CLAUDE.md kill protocol

**`ig_contrarian_sentiment` LONG direction:**  
Criteria: (a) matches existing direction-kill precedent ✅, (b) n=190 ≥ 20 ✅, (c) WR 16.3% < 35% ✅.  
→ Post evidence to issue #686 for 3-AI consensus. Do NOT auto-block.

**`rapid_fire` × UUSDT:**  
Criteria: (a) matches HYPEUSDT symbol-block pattern (PR #694) ✅, (b) n=34 ≥ 20 ✅, (c) WR 0% < 35% ✅.  
→ Post to issue #686 for 3-AI consensus vote before `BLOCKED_STRATEGY_SYMBOL_PAIRS` addition.

**No new strategies meet PF<0.5 + n≥20 outright-kill threshold.**

---

## 6. Key Findings Summary

| # | Finding | Severity | Action |
|---|---|---|---|
| 1 | EQUITY fully recovered — 14d PF 2.45 >> 1.5 threshold | POSITIVE | Close issue #693 |
| 2 | EQUITY 30d PF 2.61, WR 55.1% — approaching Tier-1 territory | POSITIVE | Document as verified edge if sustained 30d |
| 3 | FOREX 7d PF improved 0.14→1.00 post-#687, WR 10.7%→21.3% | POSITIVE | Monitor; still sub-floor 30d |
| 4 | COMMODITY stellar — 7d PF 44.07 / WR 94.4% (n=18, needs n→50) | POSITIVE | Grow n; n≥50 for Tier evidence |
| 5 | ETF strong — 7d PF 2.65 / WR 65.0%, 30d PF 3.88 | POSITIVE | Near Tier-2 promotion threshold |
| 6 | CRYPTO 24h PF 0.98 — single-day dip in otherwise healthy 7d/14d trend | WATCH | No action; monitor next 24h |
| 7 | BOND n=0 in all recency windows — n-starvation | WATCH | Resolver not processing BOND picks |
| 8 | `ig_contrarian_sentiment` LONG n=190, WR 16.3% | P2 | Post to #686 for consensus |
| 9 | `rapid_fire` × UUSDT n=34, WR 0% | P2 | Post to #686 for consensus |
| 10 | All 5 open PRs: CI red, zero merges | INFO | Authors to fix CI |

---

## 7. Issue Cross-References

- **#685 (resolver-rescope):** No new resolver PRs. Confirmed DONE. No action.
- **#686 (per-asset quality):** Post findings #8 and #9 from this audit.
- **#693 (EQUITY divergence monitor):** Criterion met → close as resolved.

---

*Audit branch: `audit/hourly-04z-2026-05-13`*
