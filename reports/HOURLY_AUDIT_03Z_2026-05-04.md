# Hourly Audit — 2026-05-04T03Z

Generated: 2026-05-04T03:22Z  
Dashboard snapshot: `audit_dashboard/data/dashboard_data.json` generated_at `2026-05-04T02:21:53Z`  
Recent-closed pool: n=3500  

---

## 1. Dashboard Refresh Status

Dashboard refreshed at **02:21:53Z** (≈60 min before this audit). Auto-refresh cron is active (`[skip ci]` commits). Data is current.

---

## 2. Per-Asset Windowed Metrics

### Computed from `picks.recent_closed` (reference: 03:22Z)

| Class | Window | n | WR% | PF | Sum PnL% |
|---|---|---|---|---|---|
| **CRYPTO** | 24h | 52 | 36.5 | 0.90 | -3.50 |
| **CRYPTO** | 7d | 546 | 43.6 | 1.25 | +110.53 |
| **CRYPTO** | 30d | 1243 | 41.8 | 1.32 | +268.95 |
| **EQUITY** | 24h | 0 | — | — | — |
| **EQUITY** | 7d | 32 | 50.0 | 1.09 | +4.77 |
| **EQUITY** | 30d | 122 | 64.8 | 3.31 | +261.95 |
| **FOREX** | 24h | 9 | 44.4 | 1.56 | +2.19 |
| **FOREX** | 7d | 94 | 35.1 | 0.45 | -15.69 |
| **FOREX** | 30d | 533 | 48.0 | 0.81 | -6.33 |
| **COMMODITY** | 24h | 0 | — | — | — |
| **COMMODITY** | 7d | 59 | 40.7 | 1.18 | +9.50 |
| **COMMODITY** | 30d | 491 | 41.1 | 0.81 | -17.19 |
| **ETF** | 24h | 0 | — | — | — |
| **ETF** | 7d | 8 | 62.5 | 1.57 | +3.86 |
| **ETF** | 30d | 36 | 77.8 | 4.06 | +56.60 |
| **BOND** | 24h/7d/30d | 0 | — | — | — |

### Long-run baseline (asset_class_health, post-resolver-v2)

| Class | PF | WR% | Note |
|---|---|---|---|
| EQUITY | 1.42 | 53.0 | T2 candidate |
| CRYPTO | 1.24 | 44.5 | Below T2, improving 7d |
| FOREX | 0.27 | 46.3 | Sub-floor, kill protocol active |
| COMMODITY | 1.78 | 46.9 | T2 PF, WR needs lift |
| ETF | 1.24 | 55.2 | Borderline (n→100) |
| BOND | 1.72 | 55.6 | n=18 below charter floor |

---

## 3. Delta vs Documented Baselines

| Class | Window | Baseline | This Hour | Delta | Signal |
|---|---|---|---|---|---|
| CRYPTO | 24h PF | 3.54 | **0.90** | -2.64 | ⚠ 24h dip — monitor only, do not destabilize |
| CRYPTO | 7d PF | 1.33 | 1.25 | -0.08 | Minor drift, within noise |
| CRYPTO | 30d PF | 1.33 | 1.32 | -0.01 | Stable |
| EQUITY | 7d PF | 0.87 (pre-#692) | **1.09** | +0.22 | ✅ goldmine_6x kill confirmed effective |
| EQUITY | 30d PF | 1.41–2.18 | **3.31** | +1.13 | ✅ Tier-1 intact; strong |
| FOREX | 7d PF | 0.14 (pre-#687) | 0.45 | +0.31 | ✅ #687+#692 kills improved; still sub-1 |
| FOREX | 30d PF | 0.97 (pre-#687) | 0.81 | -0.16 | 30d still drag; bad picks aging out |

### CRYPTO 24h regression note

24h: n=52, WR 36.5%, PF 0.90. Dominant drag:
- `unknown` source: n=11, WR 9.1%, sum -7.59%
- `rapid_momentum_filter_mut`: n=3, WR 0%, sum -3.27%
- `ensemble`: n=3, WR 0%, sum -4.47%

7d/30d both profitable (PF 1.25/1.32). 24h dip is noise — same pattern in prior 02Z audit (WR 35%, n=71). **Do not destabilize CRYPTO per issue #686 directive.**

---

## 4. FOREX Strategy Attribution (Post-Kills #687 + #692)

`forex_carry_momentum` absent from 7d window (killed in PR #692 ✅).  
Current FOREX 7d strategy breakdown (n=94):

| Strategy | n | WR% | Sum PnL% |
|---|---|---|---|
| `forex_rsi2_mean_reversion` | 49 | **14.3** | -17.38 |
| `non_crypto_consensus` | 19 | 78.9 | +0.02 |
| `unknown` | 10 | 50.0 | +2.26 |
| `fx_smart_carry_trade_momentum` | 8 | 12.5 | -1.60 |
| `combined_confidence` | 4 | 75.0 | +1.29 |

**`forex_rsi2_mean_reversion` is now the sole FOREX killer** — n=49, WR 14.3%, -17.38% 7d.  
Mutation analysis directional split: SHORT 27.3% WR (n=11) vs LONG 4.3% WR (n=46).

---

## 5. Mutation Analysis New Findings

Run: `python3 tools/mutation_analysis.py`

### P1 — `quan_engine × ONDOUSDT`
- 30d: n=31, WR 16.1%, sum -14.43%
- Pattern matches existing `quan_engine` symbol-block kills (HYPEUSDT PR #694, SOLUSDT flagged 02Z)
- All 3 kill criteria met: pattern match, n≥20, WR<35%
- **Posted to issue #686 for 3-AI consensus gate**

### P1 — `rapid_fire × UUSDT`
- n=34, WR 0.0%, avg -0.17%
- Meets all 3 criteria: symbol-specific kill pattern, n≥20, WR 0%
- **Posted to issue #686 for 3-AI consensus gate**

### P2 (directional, not a clean kill) — `forex_rsi2_mean_reversion LONG`
- LONG: n=46, WR 4.3% — block `("FOREX","forex_rsi2_mean_reversion","BUY")` proposed
- SHORT: n=11, WR 27.3% — preserve pending full mutation run
- Full `docs/MUTATION_THREE_AXIS_PROTOCOL.md` required before any action

### Watching (approaching threshold)
- `rapid_fire × TAOUSDT`: n=18, WR 5.6% — below n=20 floor; recheck next hour

---

## 6. PR Triage

| PR | Title | CI | Reviews | Action |
|---|---|---|---|---|
| #763 | audit: hourly 02Z | scan ✅ | none | ✅ **MERGED** |
| #759 | fix(sports): admin-auth fallback | test3.11 ✅ test3.12 ✅ scan ✅ drift ✅ | Codex COMMENTED (not blocking) | ✅ **MERGED** |
| #769 | feat(personas): batch B ETF/Bond/Futures | scan ✅ drift ✅ | Codex COMMENTED | ❌ **CONFLICT** — holds per no-rebase rule |
| #764 | feat(b5): concept-aware scoring shadow | test3.12 ❌ FAILURE | — | ❌ **HOLD** — CI failure |

### HOLD set status (Plan v2.1 fabricated-stats family)
- #660: **Already merged 2026-05-03T21:55Z** (pre-session; contains refuted WINNER_FILTER claim per issue #685)
- #658: CLOSED (not merged) ✅
- #681, #661: Confirmed closed (not in open PR list)

### Author rebases check (#669, #676, #608, #665, #644, #597, #615, #655)
All 8 already MERGED or CLOSED. No action required.

---

## 7. Issue #693 Monitor — EQUITY Deterioration

Per issue #693 action items:
1. After PR #692 merges — ✅ done. 7d EQUITY PF 0.87→1.09 ✅
2. `stocks_rsi2_pullback` 7d: n=14 in prior window — below n=20 floor, no kill action yet
3. EQUITY 14d target PF≥1.5 within 7 days — not yet measured (next cycle)
4. EQUITY 30d PF 3.31 — Tier-1 intact, no escalation needed

---

## 8. Summary

- **Merges this hour:** #763, #759 — **2 PRs merged**
- **Held/Conflicted:** #769 (conflict), #764 (CI red)
- **New findings:** 2 P1 kill candidates + 1 directional mutation candidate — posted to issue #686
- **EQUITY (issue #693):** 7d PF 1.09 ✅ recovering, 30d PF 3.31 ✅ Tier-1. goldmine_6x kill confirmed.
- **FOREX:** 7d improved 0.14→0.45. forex_rsi2_mean_reversion remains sole killer (n=49 WR 14%). Mutation protocol required.
- **CRYPTO:** 24h dip (PF 0.90) is noise; 7d/30d stable. No action.
- **COMMODITY:** 30d PF 0.81 despite long-run PF 1.78 — potential edge decay; monitor next cycle.
