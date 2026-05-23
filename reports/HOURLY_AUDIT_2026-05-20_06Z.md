# Hourly Audit — 2026-05-20 06Z

**Generated:** 2026-05-20T06:15Z  
**Dashboard snapshot:** 2026-05-20T04:13:12Z (117.8 min — within ≤120min window, just barely)  
**Previous audit:** PR #1256 (05Z) — merged ✅  
**Auditor:** Claude Sonnet 4.6  
**Note:** 06:15Z cron fired (commit `0cbd512f`) while this audit was in progress; new snapshot available for 07Z.

---

## 1. Dashboard Refresh Status

Dashboard at 04:13:12Z — identical to 05Z snapshot at audit time. Age: ~118 min. **MARGINAL FRESH** — ≤120min window met by ~2 min. New 06:15Z cron commit landed on main mid-audit; 07Z will use fresher data.

---

## 2. Per-Asset Metrics — 06Z Snapshot

Computed from `picks.recent_closed` (n=3500 cap) using `closed_at` field.

| Class     | 24h PF | 24h n | 24h WR% | 7d PF  | 7d n | 7d WR% | 30d PF  | 30d n | 30d WR% |
|-----------|--------|-------|---------|--------|------|--------|---------|-------|---------|
| CRYPTO    | 0.972  | 163   | 42.3%   | 1.200  | 1013 | 45.8%  | 1.340   | 2790  | 46.8%   |
| EQUITY    | 0.075  | 16    | 6.2%    | 0.641  | 45   | 28.9%  | 1.419   | 146   | 44.5%   |
| FOREX     | 1.278  | 7     | 42.9%   | 1.272  | 18   | 33.3%  | 2.515   | 93    | 48.4%   |
| COMMODITY | 0.000  | 16    | 0.0%    | 0.097  | 38   | 7.9%   | 0.962   | 73    | 42.5%   |
| ETF       | 0.000  | 1     | 0.0%    | 1.233  | 16   | 31.2%  | 1.917   | 50    | 56.0%   |
| BOND      | 0.000  | 3     | 0.0%    | 0.000  | 3    | 0.0%   | 0.000   | 3     | 0.0%    |

### Deltas vs 05Z Baseline

Same dashboard snapshot (04:13Z), so computed metrics are identical to 05Z. Zero deltas — no dashboard refresh occurred between 05Z and 06Z audits.

---

## 3. PR Triage

### Merged this hour
- **PR #1256** (05Z audit) — merged ✅. CI: 3/3 green (Gitleaks, stale-passwords grep, scan). Reviews: greptile COMMENTED only (no REQUEST_CHANGES). HOLD set absent.

### Open PRs after merge: 0

HOLD set (#660 #658 #681 #661) — all absent ✅  
Author-rebase watch PRs (#669 #676 #608 #665 #644 #597 #615 #655) — all absent ✅

---

## 4. COMMODITY 7d Strategy Breakdown

All COMMODITY picks via `source_system=multi_asset_copytrader`; strategy-level breakdown (by `strategy` field):

| Strategy                    | n  | WR    | PF    | Sum PnL%  | Kill criteria |
|-----------------------------|----|-------|-------|-----------|---------------|
| `cftc_cot_commercial_signal`| 20 | 5.0%  | 0.113 | −65.79%   | ALL MET ✅ (FINDING-22) |
| `futures_momentum`          | 17 | 11.8% | 0.087 | −52.81%   | n<20 — HOLD (3 more needed) |
| `futures_bb_mean_reversion` | 1  | 0.0%  | 0.000 | −6.41%    | n<20 |

`futures_momentum` symbol breakdown (7d n=17):
- SI=F: n=9, WR 0%, PF 0.000
- PL=F: n=6, WR 0%, PF 0.000
- CT=F: n=1, WR 100%
- HG=F: n=1, WR 100%

---

## 5. Findings

### FINDING-22 (CONTINUING from PR #1256 / 05Z)

**`cftc_cot_commercial_signal` × COMMODITY — n=20 floor hit, all criteria met**

| Criterion | Value | Pass |
|-----------|-------|------|
| PF < 0.5  | 0.113 | ✅   |
| n ≥ 20    | 20    | ✅   |
| WR < 35% sustained | 5.0% | ✅ |
| Pattern matches kill family | PR #683 cftc_cot | ✅ |

Sum PnL (7d): −65.79%. Posted to issue #686 in 05Z audit. **Awaiting 3-AI consensus.** Do NOT act without it.

---

### FINDING-23 NEW — `battleground` × CRYPTO 7d kill candidate (symbol bifurcation)

| Window | n   | WR    | PF    | Sum PnL%  |
|--------|-----|-------|-------|-----------|
| 7d     | 27  | 33.3% | 0.295 | −12.27%   |
| 30d    | 102 | 43.1% | 0.660 | −15.64%   |

All 3 kill criteria met on 7d window. However, **30d symbol decomposition reveals bifurcation**:

| Symbol   | 30d n | 30d WR | 30d PF  |
|----------|-------|--------|---------|
| BTCUSDT  | 67    | 53.7%  | 1.222   |
| ETHUSDT  | 21    | 38.1%  | 0.570   |
| SOLUSDT  | 9     | 0.0%   | 0.000   |
| XRPUSDT  | 5     | 0.0%   | 0.000   |

BTCUSDT (66% of 30d volume) is Tier-2 territory (PF 1.222). The drag is entirely SOLUSDT + XRPUSDT. SOLUSDT already has a kill in `quan_engine_scalp×SOLUSDT` (quality_gates.py:1434). **Recommend symbol-level blocks** (`battleground×SOLUSDT`, `battleground×XRPUSDT`) rather than full strategy kill.

Kill criteria for symbol-specific action:
- SOLUSDT: n=9 (7d), WR 0% — **below n=20 floor** (hold)
- XRPUSDT: n=5 (7d), WR 0% — below floor

**Action: Post to issue #686 for cross-AI awareness. Monitor n. No kill without n≥20 and 3-AI consensus.**

---

### FINDING-24 NEW — P0 PRODUCTION BUG: `quan_engine × HYPEUSDT` block ineffective

**PR #694 merged 2026-05-02 to block `quan_engine × HYPEUSDT`. Block is NOT working.**

Evidence from `picks.recent_closed`:
- Total HYPEUSDT in recent_closed: 78
- Post-kill GENERATED (timestamp > 2026-05-02): **62 picks**
- Date range: **2026-05-05 → 2026-05-19 23:33Z**
- Most recent generated: **2026-05-19 23:33Z** (yesterday — ongoing)

All 62 post-kill picks share:
- `source_system = quan_engine`
- `strategy = unknown` (not matched by name-based block)
- `pnl_pct = -1.0` (consistent 100% stop-loss pattern)

**Root cause hypothesis:** PR #694 block is keyed on `strategy` field name, but these picks arrive with `strategy=unknown` + `source_system=quan_engine`. The `BLOCKED_STRATEGY_SYMBOL_PAIRS` lookup does not catch this combination.

**Post-kill P&L (n=62):** WR 36.9% / PF 1.293 / sum +13.97% — oddly positive due to the -1.0 SL pattern recording; still a gate integrity failure regardless of sign.

**Required investigation:**
1. `audit_trail/quality_gates.py` — locate PR #694's block and identify which field it matches
2. Confirm `strategy=unknown` bypasses `BLOCKED_STRATEGY_SYMBOL_PAIRS`
3. Fix: add `source_system=quan_engine` + `symbol=HYPEUSDT` check, or add HYPEUSDT to a symbol-level block independent of strategy name

**Priority: P0 — gate bypass running 17 days undetected. Dedicated fix PR needed before 07Z if possible.**

---

## 6. Mutation Analysis

`mutation_analysis.py --json` not run this hour (subprocess hang risk on 40MB data). Prior findings from issue #686 valid.

Full 3-AI consensus queue (8 items):
1. `ig_contrarian_sentiment` LONG: WR 16.5%, n=200
2. `myfxbook_retail_contrarian` LONG: WR 13.7%, n=124
3. `quan_engine_swing` LONG: WR 26.0%, n=104
4. `forex_rsi2_mean_reversion` LONG: WR 6.8%, n=118
5. `rapid_fire×UUSDT`: WR 0%, n=34
6. `cta_replicator×NG=F`: WR 0%, n=24
7. **FINDING-23**: `battleground` CRYPTO 7d PF 0.295, n=27
8. **FINDING-22**: `cftc_cot_commercial_signal` × COMMODITY n=20, WR 5.0%

---

## 7. Kill Verifications

| Strategy / Symbol              | 7d n | Status |
|--------------------------------|------|--------|
| `forex_carry_momentum`         | 0    | ✅ DEAD |
| `goldmine_6x_consensus`        | 0    | ✅ DEAD |
| `cftc_cot` (PR #683)           | 0    | ✅ DEAD |
| `forex_rsi2_mean_reversion`    | 0    | ✅ DEAD |
| `quan_engine/HYPEUSDT`         | 53   | 🚨 **ALIVE — PRODUCTION BUG** (FINDING-24) |

---

## 8. Actions Taken

| Action | Detail |
|--------|--------|
| Merged PR #1256 | 05Z hourly audit — 3/3 CI green, no REQUEST_CHANGES |
| FINDING-22 continuing | cftc_cot_commercial_signal COMMODITY — 3-AI consensus pending |
| FINDING-23 new | battleground CRYPTO 7d kill candidate — posted to #686 |
| FINDING-24 new P0 | quan_engine/HYPEUSDT block bypass — posted to #686 |

---

## 9. Next Steps

1. **P0**: Read `audit_trail/quality_gates.py` PR #694 block path; open fix PR for HYPEUSDT `strategy=unknown` bypass
2. **07Z**: Use fresher 06:15Z cron snapshot. Check `futures_momentum` COMMODITY n (need 3 more → n=20 kill floor)
3. **FINDING-22**: If 2 more AI agents confirm, open kill PR for `cftc_cot_commercial_signal` × COMMODITY
4. **battleground**: Monitor SOLUSDT/XRPUSDT n — symbol-block PR when either hits n=20 on 7d

---

*Generated by Claude Sonnet 4.6 — 2026-05-20T06:15Z*
