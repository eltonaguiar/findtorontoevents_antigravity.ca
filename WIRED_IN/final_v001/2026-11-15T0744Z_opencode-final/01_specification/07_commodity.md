# 01_SPECIFICATION — COMMODITY / FUTURES (Copy-Trader / COT)

**Asset Class:** COMMODITY / FUTURES
**Status:** BLOCKED — Copy-Trader Claims Debunked, No Proven Edge
**sizing_allowed:** false
**Source:** `alpha_engine/data/closed_picks.json`, `reports/commodity_deep_dive_swarm_2026-05-16.md`, `groksstuff.txt`, `final_v3/quant-audit-2026-11-14/04_asset_class_fixes/ASSET_CLASS_FIXES.md`

---

## 1. Algorithm Specification

### Strategies Attempted

| Strategy | Class | n | WR | Status | Source |
|----------|-------|---|-----|--------|--------|
| multi_asset_copytrader | COMMODITY | 186 | 0% (unresolved) | BLOCKED — all force-closed toxic | closed_picks.json |
| multi_asset_cot | COMMODITY | n/a | n/a | BLOCKED — same toxic pattern | Not in closed_picks |
| multi_asset_copytrader | FOREX | 160 | 12.5% (win/total) | BLOCKED — massive drag | closed_picks.json |
| multi_asset_copytrader | FUTURES | 31 | 0% (unresolved) | BLOCKED — all force-closed toxic | closed_picks.json |
| CTA trend following | COMMODITY | n/a | n/a | BLOCKED — no data | Legacy data |

### Ground Truth from closed_picks.json

All 186 multi_asset_copytrader COMMODITY picks have identical resolution profile:
- `status`: `"CLOSED"` (never `"WON"` or `"LOST"`)
- `pnl_pct`: `0.0`
- `pnl_dollar`: `0.0`
- `exit_reason`: `"FORCE_CLOSED_TOXIC"`
- `_wr_excluded`: `true`
- `_wr_excluded_reason`: `"force_closed_toxic_admin"`

**Zero of the 186 COMMODITY picks were ever resolved with an actual trading outcome.** There is no win rate to calculate — the denominator of resolved trades is 0.

### COMMODITY symbols (186 picks across 8 symbols):

| Symbol | Count |
|--------|-------|
| SI=F (Silver) | 68 |
| PL=F (Platinum) | 68 |
| HG=F (Copper) | 42 |
| SB=F (Sugar) | 2 |
| KC=F (Coffee) | 2 |
| ZS=F (Soybeans) | 2 |
| CL=F (Crude) | 1 |
| ZC=F (Corn) | 1 |

---

## 2. The 93.8% WR Claim — Where It Appears and Why It's Wrong

**Where the claim appears (all in plan/audit documents):**

| File | Line | Claim |
|------|------|-------|
| `archive/2026-05-31_testing_protocol_dedupe/reports_money_maker_ready_20260515T211949Z.md` | 212 | `multi_asset_copytrader` (COMMODITY only) \| 96 \| 93.8% \| est >3.0 |
| Various plan/audit documents | various | WR=93.8% (n=96) — pristine win rate |
| Various justification documents | various | COMMODITY — WR 93.8-94.1%, n=96-102 |
| Various elimination logs | various | multi_asset_copytrader COMMODITY — WR=93.8%, n=96, real edge |

**The claim was DEBUNKED on 2026-05-16 as a pre-dedup artifact:**

| File | Line | Refutation |
|------|------|------------|
| `reports/commodity_deep_dive_swarm_2026-05-16.md` | 200 | WR 93.8% (multi_asset_copytrader) — both measured **before** the COT dedup fix and are inflated. Post-dedup: WR~40%, PF~0.17. |
| `reports/commodity_deep_dive_swarm_2026-05-16.md` | 206 | REMOVED 2026-05-16: multi_asset_copytrader (WR 93.8% was CT=F over-emission artifact) |
| `reports/2026-05-25_policy_clean_vs_top_edges_funnel.md` | 86 | REMOVED 2026-05-16 after a swarm deep-dive proved the WR=93.8% PF=20.54 was a pre-dedup artifact (46× over-emission on CT=F cotton). Post-dedup the cell collapsed to WR=40% PF=0.17. |

**Current DB-level data** (`groksstuff.txt:1588`): commodity `multi_asset_copytrader` n=635 WR=34.3% PF=0.74 — consistent with a losing strategy, not a 93.8% winner.

**Current `closed_picks.json`**: 186 COMMODITY picks, ALL unresolved (status=CLOSED, pnl=0, force_closed_toxic) → WR is undefined (0/0 resolved), effectively 0%.

---

## 3. Per-Class CopyTrader Results (Ground Truth vs Audit Report)

| Class | Audit Report Claim | Ground Truth (closed_picks.json) | Discrepancy |
|-------|-------------------|----------------------------------|-------------|
| COMMODITY | n=96, WR=93.8% | n=186, WR=0% (all force-closed toxic) | Claim is false — all picks unresolved |
| EQUITY | n=28, WR=42.9% | n=28, WR=42.9% | Matches |
| FOREX | n=662, WR=14.8% | n=160, WR=12.5% (win/total) | n differs (662 vs 160) — audit report may include open picks |
| FUTURES | n=157, WR=2.5% | n=31, WR=0% (all force-closed toxic) | Claim is false — all picks unresolved |

---

## 4. Final Verdict

| Criterion | Threshold | Actual | Status |
|-----------|-----------|--------|--------|
| Net expectancy | > 0 | 0.0% (all $0 PnL) | **FAIL** |
| Win Rate | > 50% | 0% (unresolved) | **FAIL** |
| Profit Factor | > 1.15 | undefined (0/0) | **FAIL** |
| DSR | ≥ 0.95 | Not computed | **FAIL** |
| PBO | ≤ 0.10 | Not computed | **FAIL** |
| Forward closes | ≥ 100 over 3 months | 0 | **FAIL** |
| Max Drawdown | < 20% | 0.0% (all $0 PnL) | PASS (trivially) |
| Sample size | n ≥ 100 | n=186 (but 0 resolved) | **FAIL** (0 resolved trades) |

**COMMODITY copy-trader/COT is BLOCKED.** All picks force-closed toxic with zero resolved outcomes. No commodity copy-trader candidate is viable.

**File paths for every claim:**
- Closed picks JSON: `alpha_engine/data/closed_picks.json` — 186 COMMODITY picks, all force-closed toxic, WR=0% unresolved
- Retraction of 93.8% WR claim: `reports/commodity_deep_dive_swarm_2026-05-16.md`
- DB-level data: `groksstuff.txt:1588` — commodity multi_asset_copytrader n=635 WR=34.3% PF=0.74
- Asset class fixes: `final_v3/quant-audit-2026-11-14/04_asset_class_fixes/ASSET_CLASS_FIXES.md` — COMMODITY section
