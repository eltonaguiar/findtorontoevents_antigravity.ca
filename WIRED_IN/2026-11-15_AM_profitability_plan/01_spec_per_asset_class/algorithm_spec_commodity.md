# Algorithm Specification — COMMODITY / FUTURES

**Asset Class:** COMMODITY / FUTURES
**Status:** BLOCKED — Copy-trader claims debunked, no proven edge
**sizing_allowed:** false

---

## 1. Algorithm Specification

### Strategies Tested / Identified (Ground Truth from closed_picks.json)

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

**Zero of the 186 COMMODITY picks were ever resolved with an actual trading outcome.**

The WR=93.8% claim (n=96) was formally retracted on 2026-05-16 as a pre-dedup over-emission artifact (46× over-emission on CT=F cotton). Post-dedup WR collapsed to ~40%, PF to 0.17. DB-level data shows n=635 WR=34.3% PF=0.74 — a consistent loser.

### Cost Model

No cost model needed — strategy is blocked (all picks force-closed toxic).

### Benchmark

No benchmark needed — strategy is blocked.

### Walk-Forward Design

Not applicable — strategy is blocked.

---

## 2. Backtest Results (Per-Class CopyTrader Audit — Ground Truth)

**Source:** `alpha_engine/data/closed_picks.json`, `reports/commodity_deep_dive_swarm_2026-05-16.md`

| Class | n | WR | Volume Share | Status | Action |
|-------|---|-----|-------------|--------|--------|
| **COMMODITY** | 186 | 0% (unresolved) | — | ❌ All force-closed toxic | **BLOCKED** |
| EQUITY | 28 | 42.9% | — | ⚠️ Thin (n<100) | Monitor |
| **FOREX** | 160 | 12.5% (win/total) | — | ❌ Massive drag | **MUTATE-BEFORE-KILL** |
| **FUTURES** | 31 | 0% (unresolved) | — | ❌ All force-closed toxic | **SURGICAL BLOCK** |

### Aggregate Masking Problem

Dashboard reports `multi_asset_copytrader` PF=4.28 / WR=47.3% / n=1505 / MDD=16.67%.

This aggregate is **misleading** — it does not reflect per-class reality. COMMODITY and FUTURES are all force-closed toxic; FOREX is massively negative.

### Peer Claim FALSIFIED

Peer Big Pickle claimed: "multi_asset_copytrader is your most robust system — PF 4.09, n=812, MDD=16.67%, spans 5 classes. Best candidate for go-live TODAY."

**Falsified on multiple counts:**
1. Spans 3-4 classes, not 5
2. NOT go-live ready — FOREX is massively negative
3. COMMODITY claims are false — all picks force-closed toxic
4. WR=93.8% claim retracted on 2026-05-16 as pre-dedup artifact

### Recommended Actions

| ID | Action | Priority | Status |
|----|--------|----------|--------|
| Block `(FUTURES, multi_asset_copytrader)` | P0 — WR=0% n=31, all force-closed toxic | DONE (quality_gates.py line 2715) |
| Block `(COMMODITY, multi_asset_copytrader)` | P0 — WR=0% n=186, all force-closed toxic | PENDING |
| Mutate-before-kill `(FOREX, multi_asset_copytrader)` | P1 — 160 picks at 12.5% WR needs axis analysis | PENDING |

---

## 3. Pick Justification

**No COMMODITY pick is justified for deployment.**

**Reasoning:**
1. **All 186 COMMODITY copy-trader picks were force-closed toxic** with pnl=0 — zero resolved trades
2. **WR=93.8% claim is false** — debunked on 2026-05-16 as pre-dedup artifact
3. **DB-level data confirms losing strategy** — n=635 WR=34.3% PF=0.74
4. **No walk-forward, no cost model, no gate evaluation** — nothing to deploy

---

## 4. Elimination Reason

- **COMMODITY copy-trader:** BLOCKED — all 186 picks force-closed toxic, zero resolved trades
- **COMMODITY COT:** BLOCKED — same toxic pattern, not in closed_picks
- **FUTURES copy-trader:** BLOCKED — all 31 picks force-closed toxic, WR=0%
- **FOREX copy-trader:** MUTATE-BEFORE-KILL — 160 picks at 12.5% WR, massive drag
- **CTA Trend:** BLOCKED — no data, no contract identity pipeline

---

## 5. Money-Ready Gate Result

**Not evaluated** — COMMODITY copy-trader/COT is blocked (all picks force-closed toxic). No gate evaluation needed for a blocked strategy.
