# Hourly Audit — 2026-05-21 19Z

**Dashboard snapshot:** `2026-05-21T12:18:29Z` (**7th consecutive stale hour** — cron may be stuck; no refresh since 12Z)
**Computed at:** 2026-05-21T19:10Z
**Previous audit:** PR #1297 (18Z) — merged this hour ✅

---

## Per-asset summary (19Z)

| Class | PF (long-run) | WR% (long-run) | 24h PF | 7d (approx) | Status | vs Baseline |
|-------|--------------|----------------|--------|-------------|--------|-------------|
| CRYPTO | 1.356 | 48.1% | 1.071 (n=28) | declining | ⚠️ 24h weak | +0.03 vs 1.33 baseline |
| EQUITY | **0.703** | **35.7%** | — | n=10 PF=0.108 | ⚠️⚠️ sub-0.75 | **−0.17 vs 0.87 last audit** |
| FOREX | **2.900** | **54.9%** | — | n=2 | ✅ recovery sustained | **+2.76 vs 0.14 pre-#687** |
| COMMODITY | 1.422 | 52.5% | — | — | ✅ T2-candidate | +0.24 vs 1.18 baseline |
| ETF | 11.995 | 50.0% | — | n=7 PF=0 WR=0% | ⚠️ outlier n | thin |
| BOND | 0.000 | 0.0% | — | — | insufficient | — |
| FUTURES | 0.956 | 16.7% | — | — | sub-floor | insufficient n |

> **Note:** 30d windows from `recent_closed` timestamp parsing: CRYPTO 30d PF=1.182 WR=36.8% (n=1097), EQUITY 30d PF=1.821 WR=46.4% (n=84), ETF 30d PF=1.689 WR=61.4% (n=44), FOREX 30d PF=6.088 WR=34.5% (n=29). Snapshot stale since 12:18Z; live precision reduced.

---

## Dashboard refresh alert

**7th consecutive stale hour.** Snapshot timestamp `2026-05-21T12:18:29Z` unchanged since the 13Z audit. The hourly `[skip ci]` cron likely failed silently. Operator action needed: check `outcome-resolver.yml` / `dashboard-generator.yml` workflow runs for failures after 12Z.

---

## Deltas vs 18Z audit (PR #1297 baseline)

| Class | 18Z PF | 19Z PF | Delta | Notes |
|-------|--------|--------|-------|-------|
| CRYPTO | 1.413 (7d) | 1.356 (long-run) | comparable | 24h dropped to 1.071 |
| EQUITY | 0.803 (7d) | 0.703 (long-run) | down 0.10 | continuing decline |
| FOREX | 1.083 (7d) | 2.900 (long-run) | consistent | 19th+ hr >=1.0 post-#687 |
| COMMODITY | 0.227 (7d) | 1.422 (long-run) | cftc_cot bleed resolving | on track |
| ETF | 1.322 (7d) | 11.995 (long-run) | n artifact | treat as thin |

---

## Mutation analysis — NEW findings (FINDING-56 / 57 / 58)

Running `python tools/mutation_analysis.py --json` 2026-05-21T19:09Z against current data.

### NEW FINDING-56 — `ig_contrarian_sentiment x LONG` (1/3 votes)
- **LONG n=200, WR=16.5%** vs SHORT n=58, WR=60.3% — 44pp directional spread
- Meets kill gates: n>=20, WR<35% — sustained across full dataset
- Pattern: directional misfiring, SHORT edge present
- Candidate: block LONG direction or add to `BLOCKED_ASSET_STRATEGY_PAIRS` for LONG only
- **Needs Kimi + Copilot/Cursor votes (currently 1/3)**

### NEW FINDING-57 — `myfxbook_retail_contrarian x LONG` (1/3 votes)
- **LONG n=124, WR=13.7%** vs SHORT n=14, WR=50.0% — 36pp directional spread
- Meets kill gates: n>=20, WR<35%
- Pattern: same directional misfiring as ig_contrarian_sentiment
- Candidate: block LONG direction
- **Needs Kimi + Copilot/Cursor votes (currently 1/3)**

### NEW FINDING-58 — `quan_engine_swing x LONG` (1/3 votes)
- **LONG n=104, WR=26.0%** vs SHORT n=5, WR=60.0% — 34pp directional spread
- Meets kill gates: n>=20, WR<35%
- Pattern: LONG directional bias failure in `quan_engine_swing`
- **Needs Kimi + Copilot/Cursor votes (currently 1/3)**

### FINDING-54 carry — `cta_replicator x NG=F` (1/3 votes)
- n=24 WR=0% avg -3% — unchanged from prior hours
- Also: `cta_replicator x ZC=F` n=8 WR=0% (below n=20 threshold — monitor only)
- **Still needs Kimi + Copilot/Cursor votes**

### FINDING-55 carry — `rapid_fire x UUSDT` (1/3 votes)
- n=34 WR=0% avg -0.17% — unchanged
- Compound: `rapid_fire x TAOUSDT` n=18 WR=5.6% (near threshold); `ESPUSDT` n=5 WR=0% (too small)
- **Still needs Kimi + Copilot/Cursor votes**

### Additional mutation signals (below kill threshold, monitor):
- `forex_rsi2_mean_reversion x LONG`: n=124, WR=12.1% — may qualify once full FOREX kill protocol complete
- `cta_cross_asset_tsmom x LONG`: n=85, WR=29.4% — borderline, monitor

---

## PR triage (19Z)

| PR | Status | Action |
|----|--------|--------|
| **#1297** | CI 3/3 green, no REQUEST_CHANGES | **MERGED this hour** |
| **#1292** | CI 6/6 green (test 3.11+3.12 now pass post-#1296 fix) | **HOLD — XSS unpatched** (see below) |
| **#1287** | CI failed (test 3.11 failure, ueps-pytest cancelled) | HOLD — superseded by #1292 |
| **#1279** | DRAFT | HOLD — DRAFT state |
| HOLD set (#660 #658 #681 #661) | absent | clean |
| Plan v2.1 PRs | absent | clean |
| Author rebase PRs (#669 #676 #608 #665 #644 #597 #615 #655) | all absent | merged/closed |

### #1292 XSS block (P1 security)
Diff review confirms `kpi.tickers`, `kpi.strategies`, and `kpi.message` are interpolated into `panel.innerHTML` without HTML escaping (`esc()` helper). The `esc()` fix from loop run #39 (PR comment 15:41Z) has NOT been applied to the latest commit (`3442e23`). This is a stored XSS vector in the audit dashboard (internal, but still a defect). **Not auto-merge eligible until XSS fix applied.** Fix is 3 lines as documented in PR #1292 comment (15:41Z).

---

## Goal-#1 assessment (19Z)

| Class | Status | Priority |
|-------|--------|----------|
| CRYPTO | PF 1.356 — stable but below T2 (need PF>1.5) | `rapid_fire x UUSDT` kill pending 3-AI vote |
| EQUITY | PF 0.703 — declining | FINDING-56/57/58 directional kills may help; `stocks_rsi2_pullback` backbone healthy per 18Z |
| FOREX | PF 2.900 — T2+ | sustained recovery post-#687; monitor toward T1 if sustained |
| COMMODITY | PF 1.422 — T2-candidate | cftc_cot bleed resolving; `futures_momentum` kill pending issue #685 |
| ETF | n too thin | wait for n->100 |
| BOND | n=4 — cold start | insufficient |

**Top priority for next hour:**
1. Flag dashboard refresh failure to operator (7 consecutive stale hours is anomalous)
2. Apply XSS fix to #1292 and merge
3. Post FINDING-56/57/58 to issue #686 for 3-AI consensus (done this hour)

---

## Peer coordination
- check_messages() — no pending messages (polling this turn)
- No peer uncommitted changes detected (stash returned "No local changes to save")

---

Refs: issues #685 #686 #693 | PRs merged: #1297
