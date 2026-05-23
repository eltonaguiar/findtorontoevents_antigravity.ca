# Hourly Audit — 2026-05-21 10Z

**Generated:** 2026-05-21T10:12Z  
**Dashboard snapshot:** `recent_closed` n=3500 (data through 2026-05-21T08:32:59Z)  
**Session refs:** Issues #685, #686, #693

---

## 1. Dashboard Refresh Status

| Field | Value |
|-------|-------|
| `meta.generated_at` | 2026-05-21T08:32:59.027285+00:00 |
| `picks.recent_closed` count | 3,500 |
| Lag to audit run | ~1h 40m |
| Status | ✅ Fresh (auto-refresh on [skip ci] cycle) |

---

## 2. Per-Asset Metrics — 24h / 7d / 30d Windows

Computed from `picks.recent_closed` using `status ∈ {WON, LOST}` (excludes UNRESOLVED/CLOSED).  
PF = gross_gain / gross_loss on resolved trades only.

| Class | 24h n | 24h WR | 24h PF | 7d n | 7d WR | 7d PF | 30d n | 30d WR | 30d PF |
|-------|------:|-------:|-------:|-----:|------:|------:|------:|-------:|-------:|
| CRYPTO | 88 | 49.4% | 2.952 | 902 | 48.8% | 1.468 | 2,656 | 46.6% | 1.365 |
| EQUITY | 8 | 62.5% | 2.321 | 46 | 37.0% | 0.803 | 151 | 48.6% | 1.431 |
| FOREX | 8 | 50.0% | 1.446 | 17 | 40.0% | 1.070 | 94 | 58.2% | 2.577 |
| COMMODITY | 2 | 0.0% | 0.000 | 41 | 7.3% | 0.088 | 76 | 40.8% | 0.879 |
| ETF | — | — | — | 11 | 27.3% | 1.322 | 47 | 59.6% | 2.121 |
| BOND | 1 | 0.0% | 0.000 | 4 | 0.0% | 0.000 | 4 | 0.0% | 0.000 |
| FUTURES | 1 | 100.0% | 999.0 | 1 | 100.0% | 999.0 | 3 | 100.0% | 999.0 |

*FUTURES: n=1/1/3 too small for statistical inference; PF=999 = single TP_HIT (cftc_cot_commercial_signal NG=F).*

---

## 3. Deltas vs Baselines

### vs Documented Baseline (task brief + issue #686, ~2026-05-02)

| Class | Window | Baseline | 10Z | Delta | Signal |
|-------|--------|----------|-----|-------|--------|
| CRYPTO | 24h PF | 3.54 | 2.952 | −0.588 | Normal regime variance; 7d/30d both improving |
| CRYPTO | 7d PF | 1.33 | 1.468 | +0.138 | ✅ Gradual improvement |
| CRYPTO | 30d PF | 1.33 | 1.365 | +0.035 | ✅ Slow upward drift |
| EQUITY | 7d PF | 0.87 | 0.803 | −0.067 | 🔴 Regression persists; goldmine_6x kill (PR #692) not yet reflected |
| EQUITY | 30d PF | 1.41–2.18 | 1.431 | Tracking low end | Monitor |
| FOREX | 7d PF | 0.14 | 1.070 | **+0.930** | ✅✅ PRs #687+#692 working |
| FOREX | 30d PF | 0.97 | 2.577 | +1.607 | ✅✅ Historic improvement |
| COMMODITY | 7d PF | Not tracked | 0.088 | — | 🔴🔴 Crisis (see §5) |

### vs 09Z Baseline (PR #1284)

| Class | Window | 09Z | 10Z | Delta |
|-------|--------|-----|-----|-------|
| CRYPTO | 24h PF | 2.867 | 2.952 | +0.085 ✅ |
| CRYPTO | 7d PF | 1.468 | 1.468 | 0 (flat) |
| EQUITY | 24h PF | 2.321 | 2.321 | 0 (flat — same 8 picks) |
| EQUITY | 7d PF | 0.803 | 0.803 | 0 (flat) |
| FOREX | 7d PF | 1.070 | 1.070 | 0 (flat) |
| COMMODITY | 7d PF | 0.088 | 0.088 | 0 — **PERSISTENT** 🔴🔴 |

---

## 4. PR Triage

### Merged this turn
| PR | Title | CI | Merge criteria | Action |
|----|-------|----|----------------|--------|
| **#1284** | audit(hourly): 09Z 2026-05-21 | 3/3 ✅ | mergeable=clean, greptile COMMENT only | **MERGED** ✅ |

### Open PRs assessed
| PR | State | Notes | Action |
|----|-------|-------|--------|
| **#1279** | DRAFT | Cursor agent docs fix — DRAFT, no merge until author promotes | HOLD |

### HOLD set (#660 #658 #681 #661)
Not present in open PR list ✅

### Author-rebase watch (#669 #676 #608 #665 #644 #597 #615 #655)
Per 09Z audit: all already merged or closed ✅ — no action required.

---

## 5. NEW FINDING: FINDING-48 — `cftc_cot_commercial_signal` × COMMODITY

### Evidence

| Metric | Value |
|--------|-------|
| Strategy | `cftc_cot_commercial_signal` |
| Asset class | COMMODITY |
| 7d n | 22 |
| 7d WR | 4.5% |
| 7d PF | 0.099 |
| 30d n | 76 (all COMMODITY strategies combined) |

**Kill threshold check:**  
- ✅ n ≥ 20 (n=22)  
- ✅ WR < 35% (4.5%)  
- ✅ PF < 0.5 (0.099)  
- ✅ Pattern matches existing COMMODITY kills (cftc_cot×COMMODITY previously flagged, cot_positioning blocked for COT look-ahead leakage)

**Current gate status:**  
- `cftc_cot_commercial_signal` is in `COT_DEDUP_SYSTEMS` (72h dedup) — NOT a kill  
- NOT in `BLOCKED_ASSET_STRATEGY_PAIRS`  
- NOT in `BLOCKED_SOURCE_SYSTEMS`  
- NOT in `PERMANENTLY_KILLED_STRATEGIES`  
- Still generating active picks (last close: 2026-05-21T08:30Z NG=F WON)

**Context:** COMMODITY 7d PF=0.088 is driven by:
- `cftc_cot_commercial_signal`: n=22, WR=4.5%, PF=0.099 ← **THIS FINDING**
- `futures_momentum`: n=17, WR=11.8%, PF=0.087 ← already blocked in `BLOCKED_SOURCE_SYSTEMS`
- `futures_bb_mean_reversion`: n=2, WR=0% ← below n=20 floor

**Status:** 1/3 AI vote (this audit). Per CLAUDE.md §"NEW STRATEGY KILLS": post to issue #686, await 2nd+3rd consensus before adding to `BLOCKED_ASSET_STRATEGY_PAIRS`.

**Recommended block (pending consensus):**
```python
# In audit_trail/quality_gates.py BLOCKED_ASSET_STRATEGY_PAIRS:
("COMMODITY", "cftc_cot_commercial_signal"),  # n=22, WR=4.5%, PF=0.099 (7d), look-ahead leakage family
```

---

## 6. Mutation Analysis Highlights (tools/mutation_analysis.py)

### Directional splits with existing findings

| Strategy | Direction | n | WR | Finding | Status |
|----------|-----------|---|----|---------|--------|
| `ig_contrarian` | LONG | 21 | 9.5% | FINDING-37/46 | Monitor — n=0 in recent_closed (all UNRESOLVED?); signal_recorder source only |
| `forex_rsi2_mean_reversion` | LONG | 124 | 12.1% | Prior finding | Both directions failing |
| `cta_cross_asset_tsmom` | LONG | 85 | 29.4% | FINDING-45 | 1/3 votes, n≥20, WR<35% |

### Symbol-level dangers
| Source | Symbol | n | WR | Finding | Status |
|--------|---------|---|----|---------|--------|
| `cta_replicator` | NG=F | 24 | 0% | FINDING-34 | Pending 3-AI consensus |
| `rapid_fire` | UUSDT | 34 | 0% | FINDING-36 | Pending 3-AI consensus |
| `quan_engine` | HYPEUSDT | 553 | 41.6% | PR #694 | **MERGED** ✅ |

### Axis 4 (vol-normalisation) candidates
| Source | n | WR | Priority |
|--------|---|----|----------|
| `multi_asset_copytrader` | 1,143 | 22.0% | High — large n, system-level drag |
| `rapid_fire` | 207 | 29.0% | Medium |
| `quan_engine` | 5,896 | 30.4% | Medium (HYPEUSDT block helps) |

---

## 7. Kill Queue (consolidated)

| Finding | Strategy/Symbol | Class | n | WR | PF | AI votes | Action |
|---------|----------------|-------|---|----|----|----------|--------|
| FINDING-34 | `cta_replicator`×NG=F | FUTURES | 24 | 0% | 0.000 | 1/3 | Await consensus |
| FINDING-36 | `rapid_fire`×UUSDT | CRYPTO | 34 | 0% | — | 1/3 | Await consensus |
| FINDING-37/46 | `ig_contrarian` LONG | FOREX | 21 | 9.5% | low | 1/3 | Monitor (n=0 in recent_closed) |
| FINDING-44 | `quan_engine_swing` LONG | CRYPTO | — | low | low | 1/3 | Await consensus |
| FINDING-45 | `cta_cross_asset_tsmom` LONG | MULTI | 85 | 29.4% | — | 1/3 | Await consensus |
| FINDING-47 | `crypto_mtf_ema_slope_alignment_v1` SHORT | CRYPTO | 38 | 31.6% | 0.497 | **1/3** | Await 2nd+3rd |
| **FINDING-48** | `cftc_cot_commercial_signal`×COMMODITY | COMMODITY | 22 | 4.5% | 0.099 | **1/3 NEW** | Post to #686 |

---

## 8. Plan v2.1 Guardrails

| Check | Status |
|-------|--------|
| HOLD set (#660 #658 #681 #661) in open PRs | Not present ✅ |
| PRs citing PF 5.81 / ml_score 0.90 / WINNER_FILTER | None detected ✅ |
| Resolver-rescope PRs (issue #685: DONE) | None detected ✅ |
| PRs claiming 'widen re-resolve scope' | None ✅ |

---

## 9. Summary

**Merged:** #1284 (09Z audit)  
**New findings:** 1 (FINDING-48: `cftc_cot_commercial_signal`×COMMODITY, n=22, WR=4.5%, PF=0.099)  
**COMMODITY alert:** 7d PF=0.088 is 10th consecutive hour below 0.1 — primary driver is `cftc_cot_commercial_signal` (unblocked). Needs CLAUDE.md deep-dive protocol + 2nd/3rd AI consensus before kill.  
**Bright spots:** FOREX recovery holding (7d PF 1.070, 9th hr ≥1.0). CRYPTO 24h PF 2.952 ✅.  
**EQUITY:** 7d PF 0.803 continues below T2 floor; post-#692 window too short to assess goldmine_6x kill impact.

---

*Refs: issues #685, #686, #693 | `audit_trail/quality_gates.py` | `tools/mutation_analysis.py`*
