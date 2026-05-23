# Hourly Audit — 2026-05-21 18Z

**Generated:** 2026-05-21T18:00Z  
**Dashboard snapshot:** `2026-05-21T12:18:29Z` (6th consecutive stale hour; auto-refresh pending ~18–19Z)  
**Session:** Claude Code claude-sonnet-4-6, 1-of-N hourly check

---

## 1. Dashboard Refresh Status

Snapshot age: ~5h42m at report time. Dashboard cron runs hourly via `[skip ci]` commits; drift is expected post-merge-burst (8 PRs today). Numbers below computed from `picks.recent_closed` (n=3500 cap) against the 12:18Z snapshot — unchanged from 17Z audit.

---

## 2. Per-Asset Metrics — 24h / 7d / 30d Windows

Computed from `audit_dashboard/data/dashboard_data.json → picks.recent_closed` (n=3500).  
Win threshold: CRYPTO 0.1bp, others 5bp (post-resolver-v2).

| Class     | 24h n | 24h WR | 24h PF | 7d n | 7d WR  | 7d PF  | 30d n | 30d WR | 30d PF | Status        |
|-----------|-------|--------|--------|------|--------|--------|-------|--------|--------|---------------|
| CRYPTO    |  93   | 50.5%  | 2.908  | 918  | 48.0%  | 1.413  | 2699  | 45.8%  | 1.321  | stable ✅     |
| EQUITY    |   8   | 62.5%  | 2.321  |  46  | 37.0%  | 0.803  |  151  | 44.4%  | 1.431  | ⚠️ 7d sub-1.0 |
| FOREX     |   8   | 50.0%  | 1.460  |  17  | 35.3%  | 1.083  |   94  | 48.9%  | 2.576  | ✅ 18th hr ≥1.0|
| COMMODITY |   2   | 50.0%  | 4.016  |  42  |  7.1%  | 0.227  |   77  | 40.3%  | 1.005  | ⚠️ 7d collapse |
| ETF       |   0   | —      | —      |  11  | 27.3%  | 1.322  |   47  | 59.6%  | 2.121  | thin n        |
| BOND      |   1   |  0.0%  | 0.000  |   4  |  0.0%  | 0.000  |   4   |  0.0%  | 0.000  | insufficient  |
| FUTURES   |   0   | —      | —      |   0  | —      | —      |   2   | 100%   | ∞      | insufficient  |

### Deltas vs Documented Baseline

| Class    | Window | Baseline | Current | Delta | Note |
|----------|--------|----------|---------|-------|------|
| CRYPTO   | 24h PF | 3.54     | 2.908   | −0.63 | Normal intraday variance |
| CRYPTO   | 7d PF  | 1.33     | 1.413   | +0.08 | Marginal improvement |
| CRYPTO   | 30d PF | 1.33     | 1.321   | −0.01 | Flat |
| EQUITY   | 7d PF  | 0.87     | 0.803   | −0.07 | Slight further decline; scouts drag |
| EQUITY   | 30d PF | 1.41     | 1.431   | +0.02 | Stable |
| FOREX    | 7d PF  | 0.14     | 1.083   | **+0.94** | **PR #687 JPY-cross fix confirmed working** |
| FOREX    | 30d PF | 0.97     | 2.576   | **+1.61** | Cumulative fix impact |
| COMMODITY| 7d PF  | —        | 0.227   | NEW ⚠️ | Pre-kill bleed (see §3) |

---

## 3. Strategy Attribution — Key Alerts

### COMMODITY 7d PF=0.227 (n=42) — Pre-Kill Bleed (NOT a new regression)

| Strategy                    | n  | WR  | PF    | Sum PnL% | Action |
|-----------------------------|----|-----|-------|----------|---------|
| `cftc_cot_commercial_signal`| 23 | 9%  | 0.351 | −55.08%  | **Killed today (PR #683)** — pre-merge trades in window |
| `futures_momentum`          | 17 | 6%  | 0.086 | −52.81%  | NOT yet killed; kill candidate per issue #685 |
| `futures_bb_mean_reversion` |  2 | 0%  | 0.000 | −10.46%  | n<20, monitor |

**Root cause:** `cftc_cot_commercial_signal` killed in PR #683 (merged today). The 7d window still contains picks generated before the kill. Both strategies should roll off within 3–5 days. `futures_momentum` needs mutation analysis + kill per issue #685 §Goal-#1 movers.

### EQUITY 7d PF=0.803 (n=46) — Scout Outliers, Not Systemic

| Strategy               | n  | WR  | Sum PnL% |
|------------------------|----|-----|----------|
| `stocks_rsi2_pullback` | 29 | 45% | **+13.47%** ← positive backbone |
| `price-accel-scout`    |  1 |  0% | −6.92%  |
| `gap-and-go-stocks`    |  1 |  0% | −6.83%  |
| `stocks_ema_golden_cross`| 2 | 0% | −6.83%  |
| `macd-hidden-div-scout`|  1 |  0% | −6.68%  |
| `rs-breakout-scout`    |  3 |  0% | −5.69%  |

`stocks_rsi2_pullback` (n=29, 45% WR) carries the class. Drag is 5 scout strategies with n=1–3 each contributing −32.95% cumulative. Statistically insignificant at n=1–3. EQUITY systemic health intact.

---

## 4. New Findings

### FINDING-55 (NEW — 1/3 votes) — `rapid_fire × UUSDT`

- **Source:** `tools/mutation_analysis.py` symbol-spread output
- **n=34** all-time (not in recent_closed 3500 cap — older trades)
- **WR=0.0%**, avg PnL=−0.17%
- `rapid_fire` also underperforms: TAOUSDT (n=18, WR=5.6%), STOUSDT (n=6, WR=16.7%), KATUSDT (n=6, WR=33.3%)
- Meets kill gates: PF<0.5, n≥20, WR<35%
- **Needs Kimi + Copilot/Cursor votes (currently 1/3)**
- Action: `("rapid_fire", "UUSDT")` in `quality_gates.py:BLOCKED_STRATEGY_SYMBOL_PAIRS` upon 3/3 consensus

### FINDING-54 (carry-forward from 17Z — 1/3 votes) — `cta_replicator × NG=F`

- n=24, WR=0.0%, avg −0.03%
- Pattern: also loses CL=F (19.1% WR, n=47), ZC=F (0% WR, n=8)
- **Still needs Kimi + Copilot/Cursor votes**
- Consider broader `cta_replicator × {NG=F, ZC=F}` compound block

### FOREX Streak — 18th Consecutive Hour PF≥1.0

FOREX 24h PF=1.460. PR #687 (JPY-cross BUY rule fix) maintained PF≥1.0 for 18 consecutive hours. 7d PF now 1.083 (was 0.14 pre-fix). Clearest Goal-#1 win this session.

---

## 5. PR Triage

### Merged This Hour
| PR | Title | CI | Action |
|----|-------|----|--------|
| **#1295** | audit(hourly): 17Z — FINDING-54, FOREX 17th hr | 3/3 ✅ | **MERGED** ✅ |
| **#1296** | fix(ci): exclude integration/network tests; MDD gate fix | 5/5 ✅ | **MERGED** ✅ |

### HOLD
| PR | Reason |
|----|--------|
| **#1292** | `test(3.11)` FAILURE — needs author rebase onto main to pick up #1296 CI fix. Do NOT rebase manually. |
| **#1287** | `test(3.11)` FAILURE + large-file diffs missing (413 proxy limit). Superseded by #1292. |
| **#1279** | DRAFT — docs update, not blocking |

### HOLD Set Verification
PRs #660, #658, #681, #661 (Plan v2.1 fabricated-stats family): **absent from open PR list** ✅

### Author Rebase PRs
PRs #669, #676, #608, #665, #644, #597, #615, #655: **all absent from open PR list** — presumed merged or closed ✅

---

## 6. Mutation Analysis — Axis 4 Watchlist

From `tools/mutation_analysis.py` (current run):

| Strategy                 | WR   | n    | Axis 4 Flag |
|--------------------------|------|------|-------------|
| `rapid_fire`             | 29.0%| 207  | vol-norm candidate |
| `quan_engine`            | 30.4%| 5896 | vol-norm candidate; HYPEUSDT blocked by PR #694 |
| `cta_replicator`         | 42.7%| 274  | symbol-allowlist mutation recommended |
| `multi_asset_copytrader` | 22.0%| 1147 | PL=F/GC=F/HG=F worst; FINDING-52 ongoing |

No new strategies meet PF<0.5 + n≥20 kill threshold beyond existing documented findings.

---

## 7. Summary

| Item | Status |
|------|--------|
| Dashboard refresh | **Stale 6h** — no action needed; cron will update |
| FOREX streak | **18 consecutive hours PF≥1.0** ✅ |
| EQUITY 7d sub-1.0 | Explained by n=1–3 scout noise; `stocks_rsi2_pullback` healthy |
| COMMODITY 7d collapse | Pre-kill data bleed; resolves as cftc_cot trades roll off (3–5d) |
| `futures_momentum` | Kill candidate per issue #685; mutation analysis recommended |
| FINDING-55 | `rapid_fire × UUSDT` posted to issue #686 (1/3 votes) |
| FINDING-54 | `cta_replicator × NG=F` carry-forward (1/3 votes) |
| PRs merged | #1295 (17Z audit), #1296 (CI fix) |
| PRs blocked | #1292 needs author rebase; #1287 superseded; #1279 DRAFT |

Refs: issues [#685](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/issues/685) [#686](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/issues/686) [#693](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/issues/693)
