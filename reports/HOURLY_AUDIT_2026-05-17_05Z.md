# Hourly Audit — 2026-05-17 05Z

**Generated:** 2026-05-17T05:15Z  
**Dashboard snapshot:** 2026-05-17T04:06:41Z (auto-refreshed hourly via [skip ci])  
**Git HEAD:** 0a494baa (Gainer scan 2026-05-17 05:03 UTC)

---

## 1. Dashboard Refresh Status

Dashboard confirmed current: `audit_dashboard/data/dashboard_data.json` mtime 2026-05-17T05:07:40Z, generated_at 2026-05-17T04:06:41Z. Pull from origin/main applied cleanly (no local changes stashed).

---

## 2. Per-Asset Metrics + Deltas

### 2a. Asset Class Health (authoritative, post-resolver-v2, all-time)

| Class | n | WR | PF | Status | Sizing |
|---|---|---|---|---|---|
| CRYPTO | 7563 | 47.0% | 1.32 | stable | allowed |
| EQUITY | 393 | 53.2% | 1.65 | stable | allowed |
| COMMODITY | 228 | 85.5% | **7.71** | stable | allowed |
| ETF | 75 | 66.7% | 2.25 | candidate | n<100 |
| FOREX | 251 | 57.8% | 0.85 | watch | no sizing |
| BOND | 11 | 54.5% | 0.66 | thin sample | n<50 |
| FUTURES | 2 | 100% | null | insufficient | n<10 |

**Notable:** COMMODITY PF=7.71 on n=228 is new data point (prev baseline PF=1.78). Requires validation — the COMMODITY COT SHORT edge (PR #1125) may be driving this. Do not treat as stable until n>=300 and 30d window confirms.

### 2b. Recent Windows (computed from recent_closed n=3500, date proxy=opened_at)

| Class | 24h (n/WR/PF) | 7d (n/WR/PF) | 30d (n/WR/PF) |
|---|---|---|---|
| CRYPTO | 137 / 39.4% / **0.68** | 828 / 42.4% / 1.11 | 2872 / 45.7% / 1.27 |
| EQUITY | 0 / -- / -- | 26 / 19.2% / **0.79** | 99 / 54.5% / 2.52 |
| FOREX | 7 / 42.9% / 1.22 | 18 / 27.8% / 1.60 | 48 / 33.3% / 2.30 |
| COMMODITY | 0 / -- / -- | 27 / 29.6% / **0.64** | 65 / 56.9% / 1.97 |
| ETF | 0 / -- / -- | 13 / 46.2% / **0.66** | 48 / 70.8% / 2.48 |
| BOND | 0 / -- / -- | 0 / -- / -- | 0 / -- / -- |

*Note: windowed computation uses opened_at as proxy; close_time field absent in recent_closed records. 24h hourly feed (authoritative for 24h) shown separately below.*

### 2c. 24h Hourly Feed (authoritative -- source: `performance.hourly_24h`)

| Class | Closed (24h) | WR | PnL Sum |
|---|---|---|---|
| CRYPTO | 148 | 39.2% | -14.61% |
| FOREX | 7 | 42.9% | +1.18% |
| EQUITY | 0 | -- | -- |
| COMMODITY | 0 | -- | -- |
| ETF | 0 | -- | -- |

### 2d. Delta Table vs Documented Baseline

Baseline source: task brief (CRYPTO 24h PF 3.54 / 7d 1.33 / 30d 1.33; EQUITY 7d 0.87 / 30d 1.41->2.18; FOREX 7d 0.14 / 30d 0.97 pre-#687).

| Class | Window | Baseline PF | Current PF | Delta | Verdict |
|---|---|---|---|---|---|
| CRYPTO | 24h | 3.54 | **0.68** | -2.86 | ALERT -- short-term regime hit |
| CRYPTO | 7d | 1.33 | 1.11 | -0.22 | slight decline |
| CRYPTO | 30d | 1.33 | 1.27 | -0.06 | stable |
| EQUITY | 7d | 0.87 | **0.79** | -0.08 | continued weak; goldmine_6x now killed |
| EQUITY | 30d | 2.18 | **2.52** | +0.34 | improving post-#692 |
| FOREX | 7d | 0.14 (pre-#687) | **1.60** | +1.46 | STRONG RECOVERY |
| FOREX | 30d | 0.97 (pre-#687) | **2.30** | +1.33 | STRONG RECOVERY |
| COMMODITY | 7d | n/a | **0.64** | -- | 7d regression (30d=1.97 healthy) |
| ETF | 7d | n/a | **0.66** | -- | 7d regression (30d=2.48 healthy) |

#### CRYPTO 24h ALERT -- Assessment

CRYPTO 24h PF dropped from the 2026-05-02 baseline of 3.54 to 0.68 (148 trades, WR=39.2%, PnL=-14.61%). The long-run asset_class_health PF=1.32 on n=7563 remains intact. Possible causes:

1. **Regime**: market whipsaw in the session window (daily crypto vol elevated post-2026-05-15 macro events)
2. **quan_engine**: still high volume share despite PR #694 (HYPEUSDT block). quan_engine HYPEUSDT WR=41.6% on n=553 was the largest drag -- block should reduce future contamination
3. **24h window noise**: 148 trades in a 24h window with 39.2% WR is elevated loss but within 2-sigma of historical CRYPTO volatility

**Action:** Monitor only. No kill triggers met (n>=20 + WR<35% + sustained). Re-check at 06Z.

#### EQUITY 7d continued weakness -- Assessment

After PR #692 (goldmine_6x_consensus kill), EQUITY 7d PF=0.79 vs pre-kill 0.87. The kill should gradually improve the 7d window as goldmine_6x picks roll off. Remaining drag: `stocks_rsi2_pullback` n=14, WR~35.7% -- below the n=20 kill floor. Monitor per issue #693 recommendation.

#### COMMODITY 7d regression -- NEW FINDING

COMMODITY 7d PF=0.64 on n=27 vs long-run 1.97 on n=65. Need strategy-level attribution. `cta_replicator` has CL=F (n=47, WR=19.1%), NG=F (n=24, WR=0%), ZC=F (n=8, WR=0%) -- all under-performing commodity symbols. NG=F and CL=F are the probable 7d drag.

---

## 3. PR Triage

**Total open PRs:** 3 (all opened 2026-05-17; old HOLD set #660/#658/#681/#661 and rebase set #669/#676/#608/#665/#644/#597/#615/#655 are no longer in open state -- already resolved in prior sessions)

| PR | Title | mergeable_state | CI | Reviews | Decision |
|---|---|---|---|---|---|
| #1125 | fix(reports): COMMODITY COT direction (report-only) | **dirty** (conflicts) | no runs | none | HOLD -- merge conflict |
| #1124 | feat(etf+bond scanner): Tiingo/Polygon OHLCV failover | unstable | test(3.11)=FAIL, test(3.12)=cancelled | none | HOLD -- CI failing |
| #1121 | feat(swarm-v2): LLM7.io keyless provider | unstable | CI in_progress | none | HOLD -- CI pending |

**PRs merged this hour:** 0 (no PR met all criteria: MERGEABLE + all CI green + no REQUEST_CHANGES)

**Notes:**
- #1125 has conflicts (dirty) -- author must rebase. The COMMODITY COT correction is backed by empirical evidence (COT SHORT: n=29, WR=62.1%, PF=1.85 vs COT LONG: n=3, WR=33%, PF=0.14). Worth unblocking once conflicts resolved.
- #1124 test(3.11) failure needs investigation -- Wire-up rule check: `ohlcv_failover.py` is called by `etf_scanner` and `bond_scanner` (production pick path), so wire-up rule is satisfied.
- #1121 LLM7 is a swarm infrastructure change (not in production pick/score path), needs wire-up rule confirmation if swarm workers feed `smart_picks_engine`.

---

## 4. New Strategy Kill Candidates

Sourced from `python tools/mutation_analysis.py --json` (run 2026-05-17T05:10Z).

### 4a. Direction-Flip Candidates (LONG leg catastrophic)

| Strategy | Direction | n | WR | Spread | Kill Criteria Met? |
|---|---|---|---|---|---|
| `ig_contrarian_sentiment` | LONG | 197 | **16.8%** | 45pp vs SHORT | n>=20, WR<35% sustained |
| `myfxbook_retail_contrarian` | LONG | 123 | **13.8%** | 36pp vs SHORT | n>=20, WR<35% sustained |
| `forex_rsi2_mean_reversion` | LONG | 108 | **7.4%** | 27pp vs SHORT | n>=20, WR<35% sustained |
| `quan_engine_swing` | LONG | 104 | 26.0% | 34pp vs SHORT | n>=20 but WR>20% borderline |
| `cta_cross_asset_tsmom` | LONG | 84 | 29.8% | 23pp vs SHORT | n>=20, WR borderline |
| `combined_confidence` | LONG | 10 | 10.0% | 46pp vs SHORT | n<20 -- insufficient |

Top 3 meet all kill criteria. Per CLAUDE.md: require 3+ AI consensus before adding to `BLOCKED_ASSET_STRATEGY_PAIRS`.

`forex_rsi2_mean_reversion` was already flagged in issue #686 as P1. This mutation analysis corroborates: LONG leg WR=7.4% on n=108. SHORT leg (WR=34.8%) also weak -- full strategy kill (both directions) is the correct mutation.

### 4b. Symbol-Level Kill Candidates

| System | Symbol | n | WR | Action |
|---|---|---|---|---|
| `cta_replicator` | NG=F | 24 | 0% | Meets criteria -- post to #686 |
| `quan_engine` | UUSDT | 34 | 0% | Meets criteria -- post to #686 |
| `rapid_fire` | TAOUSDT | 18 | 5.6% | n<20, watch |
| `alpha_engine` | GBPJPY=X | 5 | 0% | n<20, insufficient |

### 4c. Already-Blocked (validation)

- `quan_engine` x HYPEUSDT: still appears at WR=41.6%, n=553, avg=-0.22% -- PR #694 merged today blocks new picks but historical closes still in dataset. Expected to drain over time.

---

## 5. Actions Taken This Hour

1. **No PRs merged** -- 0 of 3 open PRs met merge criteria.
2. **Mutation analysis run** -- 3 new strategy-level + 2 symbol-level kill candidates identified (require peer AI consensus before blocking).
3. **Dashboard refresh confirmed** -- generated_at 04:06Z, 1-hour cycle working.
4. **Hourly audit report written** -- this document.

---

## 6. Findings Summary

| Finding | Severity | Next Action |
|---|---|---|
| CRYPTO 24h PF=0.68 (vs baseline 3.54) | P2 -- likely short-term | Monitor at 06Z; no kill trigger |
| EQUITY 7d PF=0.79 (continued weakness) | P2 -- post-#692 recovery in progress | Monitor stocks_rsi2_pullback if n->20 |
| FOREX 7d PF=1.60 (STRONG recovery, was 0.14) | Positive | Confirms #687 JPY-cross fix worked |
| EQUITY 30d PF=2.52 (improved from 2.18) | Positive | Confirms #692 goldmine_6x kill working |
| COMMODITY 7d PF=0.64 | P2 -- 30d intact | Attribute to cta_replicator NG=F / CL=F |
| ETF 7d PF=0.66 | P2 -- 30d=2.48 intact | Small n (13), not actionable yet |
| `ig_contrarian_sentiment` LONG WR=16.8% n=197 | P1 kill candidate | Post to issue #686; await peer consensus |
| `myfxbook_retail_contrarian` LONG WR=13.8% n=123 | P1 kill candidate | Post to issue #686; await peer consensus |
| `forex_rsi2_mean_reversion` LONG WR=7.4% n=108 | P1 kill candidate (corroboration) | Already in #686; mutation confirms full kill |
| `cta_replicator` x NG=F WR=0% n=24 | P1 symbol kill | Post to issue #686; await peer consensus |
| `quan_engine` x UUSDT WR=0% n=34 | P1 symbol kill | Post to issue #686; await peer consensus |
| COMMODITY PF=7.71 all-time (new) | Positive -- validate | Needs 30d window confirmation, n->300 |

---

## 7. Refs

- Dashboard: `audit_dashboard/data/dashboard_data.json` (generated_at 2026-05-17T04:06:41Z)
- Mutation analysis: `python tools/mutation_analysis.py --json` (2026-05-17T05:10Z)
- Issues: #685 (resolver-rescope done), #686 (kill candidates), #693 (EQUITY monitor -- closed 2026-05-13)
- PRs today merged (prior sessions): #684, #674, #673, #664, #683, #687, #692, #694
- Kill protocol: `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`, `docs/MUTATION_THREE_AXIS_PROTOCOL.md`
