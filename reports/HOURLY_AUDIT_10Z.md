# Hourly Audit — 2026-05-17T10Z

**Session start:** 2026-05-17T10:09Z  
**Dashboard generated_at:** 2026-05-17T09:49:57Z  
**Data source:** `audit_dashboard/data/dashboard_data.json` (pulled from origin/main, 7 files updated)  
**Resolved picks in window:** 3,486 with valid `closed_at`

---

## 1. Dashboard Refresh Status

Pull succeeded. Fast-forward merge from `61297197→bbdf265d`. Changed files:
- `alpha_engine/data/momentum_picks.json` (308 lines)
- `alpha_engine/data/portfolio_copytrader.json`
- `alpha_engine/data/portfolio_copytrader_raw.json`
- `cross_aggregation/data/consensus_outcomes.json` (745 lines)
- `crypto_signal_engine/data/audit.json`
- `crypto_signal_engine/data/price_cache.json`
- `crypto_signal_engine/data/top_gainers.json`

Dashboard data current as of 09:49Z — within the 60-min hourly cron window.

---

## 2. Per-Asset Metrics

### 2a. Long-Run Baseline (asset_class_health, post-noise-filter)

| Class     | PF   | WR%  | n     | Tier Status        | Delta vs #686 baseline |
|-----------|------|------|-------|--------------------|------------------------|
| CRYPTO    | 1.30 | 46.3 | 7,339 | Sub-T2             | PF -0.03 (stable)      |
| EQUITY    | 1.97 | 53.3 | 240   | T2 candidate       | PF +0.56 vs 1.41 — improving long-run |
| FOREX     | 2.07 | 35.7 | 98    | Watch (WR sub-50%) | PF +1.10 vs 0.97 — post-#687 JPY fix |
| ETF       | 2.41 | 67.6 | 74    | T2 (n just below 100 floor) | PF +1.17 vs 1.24 |
| COMMODITY | 7.30 | 85.5 | 228   | T1-elite           | PF +5.52 vs 1.78 — very strong |
| FUTURES   | N/A  | 100.0| 2     | n too small        | —                      |
| BOND      | 0.54 | 50.0 | 12    | Sub-floor, n<18    | —                      |

> Note: FOREX PF 2.07 long-run with WR 35.7% indicates asymmetric payoff (big winners, frequent losers). Post-JPY-cross kill (#687 + #692) this is plausible — verify with 30d window below.

### 2b. 24-Hour Window (closed_at >= 2026-05-16T10:09Z)

| Class   | n   | W  | L  | WR%  | PF   | Notes                          |
|---------|-----|----|----|------|------|--------------------------------|
| CRYPTO  | 105 | 51 | 54 | 48.6 | 1.39 | **Below baseline 3.54** — regression |
| FOREX   | 7   | 3  | 4  | 42.9 | 1.22 | Small sample, hold judgment    |

**24h finding:** CRYPTO PF 1.39 / WR 48.6% is a significant drop from the #686 baseline of PF 3.54 / WR 64%. This may reflect regime shift post-HYPEUSDT-block (#694) reducing high-PF outliers, or genuine intraday deterioration. Requires 48h observation before action.

### 2c. 7-Day Window (closed_at >= 2026-05-10T10:09Z)

| Class     | n   | W   | L   | WR%  | PF   | Delta vs #686 baseline         |
|-----------|-----|-----|-----|------|------|-------------------------------|
| CRYPTO    | 834 | 355 | 479 | 42.6 | 1.12 | vs 7d PF 1.21 WR 41% — stable |
| EQUITY    | 14  | 4   | 10  | 28.6 | 0.62 | **vs 7d PF 0.87 WR 41% — regression** (n too small, post-#692 kill) |
| FOREX     | 11  | 5   | 6   | 45.5 | 1.60 | **vs 7d PF 0.14 WR 10.7% — dramatic improvement post-#687** |
| COMMODITY | 27  | 8   | 19  | 29.6 | 0.64 | **vs 7d PF 1.18 — regression, n=27 borderline** |
| ETF       | 13  | 6   | 7   | 46.2 | 0.66 | vs 7d PF 1.57 — regression, n=13 small |

**7d findings:**
- **FOREX recovery confirmed:** PF 1.60 vs 0.14 pre-#687 — JPY-cross BUY fix is working
- **EQUITY 7d degraded further:** PF 0.62 (was 0.87 in #686 baseline, was 2.18 at 30d). #692 goldmine_6x kill should clear but n=14 is too small to judge yet — per issue #693 protocol, monitor only
- **COMMODITY 7d regression:** PF 0.64, WR 29.6%, n=27 is borderline (>20 but sample covers mixed strategies). Flag for investigation if 14d stays below 1.0
- **ETF 7d regression:** PF 0.66, n=13 — too small to act on

### 2d. 30-Day Window (closed_at >= 2026-04-17T10:09Z)

| Class     | n    | W    | L    | WR%  | PF   | Delta vs #693 baseline         |
|-----------|------|------|------|------|------|-------------------------------|
| CRYPTO    | 2852 | 1312 | 1540 | 46.0 | 1.29 | vs 30d PF 1.33 — stable       |
| EQUITY    | 87   | 53   | 34   | 60.9 | 2.47 | vs 30d PF 2.18 — improved     |
| FOREX     | 33   | 16   | 17   | 48.5 | 2.30 | vs 30d PF 0.97 — major improvement post-#687 |
| COMMODITY | 65   | 37   | 28   | 56.9 | 1.97 | T2-eligible (PF>1.5, WR>50%)  |
| ETF       | 48   | 34   | 14   | 70.8 | 2.48 | Strong, approaching n=100 floor |

**30d findings:**
- EQUITY 30d recovered to PF 2.47 / WR 60.9% — #692 goldmine_6x kill impact not yet in 30d window; the 7d deterioration is isolated
- FOREX 30d PF 2.30 confirms PR #687 structural fix (not just short-term noise)
- COMMODITY 30d T2-eligible (PF 1.97, WR 56.9%) — notable upgrade from #686 snapshot

---

## 3. PR Triage

### 3a. Open PRs found

**Queue at audit time: 0 actionable open PRs.**

- **#1160** (`docs/money-ready-methodology`) — found open at session start, already merged by `eltonaguiar` at 10:09Z before merge evaluation. PR was docs-only, no Plan v2.1 claims found.

### 3b. HOLD set status

All HOLD-set PRs were already closed before this session:

| PR  | Title                                  | State            | Note                             |
|-----|----------------------------------------|------------------|----------------------------------|
| #660 | P0 Emergency Gate Fixes               | **Merged** 2026-05-03 | HOLD criteria met post-fact; cited WINNER_FILTER (fabricated per #685) |
| #658 | Hedge Fund Quality Enhancement        | Closed (no merge) 2026-05-03 | Plan v2.1 family — correctly not merged |
| #681 | Strategy Decay Guard                  | Closed (no merge) 2026-05-03 | Wire-up rule fail + fabricated WRs |
| #661 | Infrastructure v2.0                   | **Merged** 2026-05-03 | Docs/infrastructure only — no Plan v2.1 claims |

> Note: #660 merged despite citing WINNER_FILTER (Plan v2.1 fabrication). Already in main, cannot reverse. Flagging for awareness.

### 3c. Author rebases check

All rebase-check PRs already merged prior to this session:

| PR  | Merged at        |
|-----|-----------------|
| #669 | 2026-05-02T23:08Z |
| #676 | 2026-05-03T21:52Z |
| #608 | 2026-05-03T21:57Z |
| #665 | 2026-05-02T23:08Z |
| #644 | 2026-05-03T22:00Z |
| #597 | 2026-05-03T22:33Z |
| #615 | 2026-05-03T21:57Z |
| #655 | Closed (no merge) 2026-05-03 |

**This hour: 0 PR merges performed by this session.** Queue is clear.

---

## 4. Mutation Analysis — New Findings

Output from `python tools/mutation_analysis.py --json` (2026-05-17T10:11Z):

### 4a. Direction-flip candidates (Axis 1)

| Strategy | Direction | WR% | n   | Spread | Action needed? |
|----------|-----------|-----|-----|--------|----------------|
| `ig_contrarian_sentiment` | LONG | 16.8 | 197 | 45pp vs SHORT 61.4% | **P1: n>=20, WR<35%** — meets kill criteria axis; needs PF verification |
| `myfxbook_retail_contrarian` | LONG | 13.8 | 123 | 36pp vs SHORT 50% | **P1: n>=20, WR<35%** — meets kill criteria axis |
| `combined_confidence` | LONG | 10.0 | 10  | 46pp vs SHORT 55.6% | n<20, hold |
| `quan_engine_swing` | LONG | 26.0 | 104 | 34pp vs SHORT 60% | WR 26% < 35%, n>=20 — borderline |
| `forex_rsi2_mean_reversion` | LONG | 7.4  | 108 | 27pp vs SHORT 34.8% | **Already P1 kill candidate per #686** |
| `cta_cross_asset_tsmom` | LONG | 29.8 | 84  | 23pp vs SHORT 52.4% | WR near 30%, watch |

### 4b. Symbol-variance candidates (Axis 3)

- `rapid_fire` / `UUSDT`: WR 0%, n=34 — **meets kill criteria (n>=20, WR 0%)**; pattern matches existing kills
- `cta_replicator` / `NG=F`: WR 0%, n=24 — meets n>=20 floor
- `cta_replicator` / `ZC=F`: WR 0%, n=8 — n<20, hold
- `quan_engine` / `HYPEUSDT`: n=553, WR 41.6% — HYPEUSDT block (#694) should reduce new pick flow; historical data will clear over time

### 4c. New findings vs existing blocks

`rapid_fire/UUSDT` (n=34, WR 0%) is new and not in `BLOCKED_STRATEGY_SYMBOL_PAIRS`. Pattern matches existing kills (0% WR + n>=20). Requires 3-AI consensus per kill protocol before blocking.

`ig_contrarian_sentiment` LONG direction (n=197, WR 16.8%) is a strong candidate — not currently blocked. Represents 197 trades dragging this strategy below T2.

---

## 5. Issues Cross-Reference

- **Issue #685** (resolver-rescope done): No PR found claiming widen re-resolve scope. Confirmed clear.
- **Issue #686** (FOREX catastrophic + EQUITY drift): FOREX 7d PF recovered to 1.60 post-#687. `forex_carry_momentum` and `goldmine_6x_consensus` killed in #692. New candidates: `ig_contrarian_sentiment` LONG and `myfxbook_retail_contrarian` LONG — posting to #686.
- **Issue #693** (EQUITY 7d/14d/30d monitor, closed): EQUITY 30d PF=2.47 is healthy; 7d=0.62 with n=14 post-#692 is too small to conclude. Monitor per #693 protocol (check again at 72h post-merge).

---

## 6. Action Items

| Priority | Item | Constraint |
|----------|------|------------|
| P1 | Post `ig_contrarian_sentiment` LONG (n=197, WR 16.8%) to issue #686 for 3-AI review | Do not auto-block; post evidence only |
| P1 | Post `myfxbook_retail_contrarian` LONG (n=123, WR 13.8%) to issue #686 | Do not auto-block; post evidence only |
| P1 | Post `rapid_fire/UUSDT` (n=34, WR 0%) to issue #686 | Do not auto-block; 3-AI consensus required |
| P2 | Re-check COMMODITY 7d in 24h (PF 0.64, WR 29.6%, n=27) | Sample borderline; investigate if 14d < 1.0 |
| P2 | CRYPTO 24h PF 1.39 — monitor next cycle | May reflect HYPEUSDT removal reducing outlier PF |
| P3 | EQUITY 7d recovery check at 72h post-#692 (due 2026-05-04~05, already past) | Review actual 7d now — see §2c |

---

## 7. Summary

- **Dashboard refreshed:** ✅ 09:49Z data current
- **PRs merged this hour:** 0 (queue empty; all pending PRs closed prior to session)
- **New strategy kill candidates:** 3 (ig_contrarian_sentiment LONG, myfxbook_retail_contrarian LONG, rapid_fire/UUSDT) — require 3-AI consensus before blocking
- **Key positive signal:** FOREX 7d PF 1.60 (+1.46 vs baseline) confirms PR #687 JPY-cross fix is working
- **Key concern:** CRYPTO 24h PF 1.39 (vs 3.54 baseline) — monitor; may be structural post-HYPEUSDT block

_Generated: 2026-05-17T10:12Z_
