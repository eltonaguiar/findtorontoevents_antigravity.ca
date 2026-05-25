# CRYPTO 78% WR / n=337 — End-to-End Verification

**Date:** 2026-05-25
**Investigator:** Claude (audit-pick-flow)
**Verdict:** **DISPUTED — not real edge.** The number is reproducible in the dashboard cohort but does not survive a DB-side cross-check. Root cause is **(a) single-source concentration**, **(b) EXPIRED-as-WIN labelling**, and **(c) the dashboard cohort being a curated subset, not the production-wide closed pool.**

---

## 1. Where the 78%/337 lives on the page

`audit_dashboard/pick_funnel.html` renders a **Navigation-surface Edge Matrix** from `audit_dashboard/data/nav_surface_edge_matrix.json`. The "Smart Picks" CRYPTO row in that file:

```json
{"asset_class": "CRYPTO", "n": 337, "wr_pct": 78.9, "wr_shrunk_pct": 77.3,
 "pf": 9.69, "train_pf": 6.163, "holdout_pf": 71.162,
 "pass_holdout": true, "pass_bonferroni": true, "is_edge": true}
```

The same cohort produces the equally implausible rows:
- Verified Alpha CRYPTO: n=304, WR=83.2%, PF=11.19, holdout_pf=58.42
- High-Conviction CRYPTO: n=231, WR=87.9%, PF=18.5, holdout_pf=69.05
- ELITE display tier CRYPTO: n=155, WR=87.7%, PF=16.4, holdout_pf=11.85

Generator: `tools/audit_pick_funnel/build_nav_surface_matrix.py`. Source: `audit/data/dashboard_data.json::picks.recent_closed` filtered with predicate `(elite_score >= 60) AND (confidence >= 0.60)` and `status IN ('WON','LOST')`.

## 2. Exact reproduction (numerator / denominator)

```python
import json
d = json.load(open('audit/data/dashboard_data.json'))
rc = d['picks']['recent_closed']
cohort = [p for p in rc
          if p['asset_class']=='CRYPTO'
          and p['status'] in ('WON','LOST')
          and (p.get('elite_score') or 0) >= 60
          and (p.get('confidence') or 0) >= 0.60]
n = len(cohort)             # 337
wins = sum(1 for p in cohort if p['status']=='WON')   # 266
# wr = 266/337 = 78.93% ; wr_shrunk = (266+10)/(337+20) = 77.31%
```

PF math: `sum_pos = 686.92%`, `|sum_neg| = 70.89%` → PF = 9.69. ✅ Reproduces exactly.

## 3. Cohort composition (what 337 picks actually are)

| Tag | Count | Share |
|---|---|---|
| source_system = `claude_gainer_st` | 309 | **91.7%** |
| strategy = `st_fear_greed_contrarian` | 236 | **70.0%** |
| strategy = `st_obv_support_divergence` | 68 | 20.2% |
| Top symbol DOTUSDT | 33 | 9.8% |

**This is not a portfolio. It is one source-system's track record under the Smart filter.**

### Exit-reason breakdown (the smoking gun)

| exit_reason | n | WR | sum_pnl |
|---|---|---|---|
| TP_HIT | 199 | 100.0% | +564.75% |
| EXPIRED | 97 | **63.9%** | +63.37% |
| SL_HIT | 24 | 0.0% | −43.01% |
| ATR trailing stop hit | 12 | 0.0% | +8.82% (?!) |
| WON | 4 | 100.0% | +12.65% |
| PRICE_RESOLVED | 1 | 100.0% | +9.45% |

- **EXPIRED at 63.9% WR is the inflation driver.** When a pick expires without hitting TP or SL, the resolver is labelling intraday positive-drift exits as WON. A truly noise-free EXPIRED bucket should be ~50/50; +14 points above 50 is a labelling rule, not market edge.
- `ATR trailing stop hit` rows have status=LOST but sum_pnl is positive — bookkeeping inconsistency.

## 4. DB ground truth — does not corroborate

Queries against `ejaguiar1_stocks.at_raw_picks` over the same 90d window (via `closed_at`):

```sql
-- All CRYPTO closed-decisive, 90d
SELECT SUM(status='WON') wins, SUM(status='LOST') losses,
       SUM(IF(pnl_pct>0,pnl_pct,0)) pos,
       SUM(IF(pnl_pct<0,pnl_pct,0)) neg
FROM at_raw_picks
WHERE asset_class='CRYPTO' AND status IN ('WON','LOST')
  AND closed_at >= NOW() - INTERVAL 90 DAY;
-- → wins=788 losses=1213 n=2001  WR=39.38%  PF=0.371  mean_pnl=-4.60%

-- "Smart"-like slice (confidence>=0.60; elite_score not in raw_picks)
SELECT COUNT(*) n, SUM(status='WON') w
FROM at_raw_picks
WHERE asset_class='CRYPTO' AND status IN ('WON','LOST')
  AND closed_at >= NOW() - INTERVAL 90 DAY AND confidence>=0.60;
-- → n=1210, w=399  WR=32.98%  PF=0.60
```

Dashboard says CRYPTO Smart = **78.93%** on n=337. DB says CRYPTO conf≥0.60 = **32.98%** on n=1210. The dashboard cohort is a hand-picked 337-row slice; the bulk of real CRYPTO closes (the other ~870+ rows) are losing trades that never enter the curated `recent_closed` set.

Per-source breakdown of the raw DB CRYPTO 90d closed pool:

| source_system | n_closed | WR | mean_pnl |
|---|---|---|---|
| meta_strategy | 1035 | 41.2% | +0.29% |
| incubator_gainer | 319 | 42.9% | −2.07% |
| alpha_engine_unified | 220 | 57.3% | +2.55% |
| quan_engine | 136 | 32.4% | −3.57% |
| sandbox_opposite | 111 | 1.8% | −6.00% |
| claude_gainer_st | **3** | (NA) | (NA) |

**`claude_gainer_st` has 3 closed-decisive rows in the raw DB but 309 in the dashboard cohort.** This is the root of the divergence: the dashboard JSON includes a 90d snapshot that draws from a different/older source pool than the live `at_raw_picks` table, and the live picks the system is actually producing today look nothing like the cohort being scored.

## 5. Leakage checklist

| Check | Result |
|---|---|
| (a) closed_at < pick timestamp (impossible) | **PASS** (0 rows in cohort, 0 rows in DB CRYPTO 90d) |
| (a') closed_at == pick timestamp (0-sec hold, PIT) | **PASS** (0 rows) |
| (a'') closed within 60s of pick (near-PIT) | **PASS** (0 rows) |
| (b) outcomes use prices unknown at pick time | **INCONCLUSIVE** (not directly tested — would need to fetch historical OHLC and replay) |
| (c) exit_price recorded at pick instant | **PASS** (cohort hold-time median 7.76h, min 0.93h) |
| (d) duplicate-row counting | **FAIL** — 1,864 duplicate (symbol, signal_timestamp, source_system) groups in CRYPTO 90d `at_raw_picks` |
| (e) `_stamp_pit_sym_track` shadow column bypassed | **NOT DIRECTLY APPLICABLE** — the nav-matrix builder reads `dashboard_data.json` not the PIT-shadow table; whether `dashboard_data.json` itself respects PIT-shadow is a follow-up |
| (f) EXPIRED→WON labelling | **FAIL** — 97 EXPIRED rows at 63.9% WR; a flat-noise EXPIRED bucket should be ~50% |
| (g) ATR-trailing bookkeeping | **FAIL** — 12 rows status=LOST with sum_pnl=+8.82% |
| (h) source concentration | **FAIL** — 91.7% from one source_system, 70% from one strategy |
| (i) holdout PF sanity | **FAIL** — holdout_pf=71.16 (train_pf=6.16) is mathematically implausible for an honest cohort |

## 6. Recommended next actions (in priority order)

1. **Fix EXPIRED resolver labelling.** In `alpha_engine/outcome_resolver.py` (and any sibling resolver feeding `recent_closed`), an EXPIRED pick that hit neither TP nor SL should be `EXPIRED` status, not `WON`/`LOST`. Right now intraday drift is being silently converted to WON. Re-resolve the 90d CRYPTO closed pool and re-render dashboard.
2. **De-duplicate `at_raw_picks` on (symbol, signal_timestamp, source_system).** 1,864 duplicate groups in CRYPTO 90d alone is inflating both numerators and denominators.
3. **Decouple the "Smart Picks" nav-surface row from a single source_system.** Add a `concentration_penalty` to the `is_edge` decision — if top-source-share > 60% on a surface, mark it `concentration=` in `why_no_edge` and flip `is_edge=false` even if WR/PF/holdout pass. The current build_nav_surface_matrix.py already computes source concentration in `_why_no_edge` but the verdict logic ignores it.
4. **Add the DISPUTED banner that this run shipped** to template.html's audit MAJOR-GOALS section as well, so the same warning shows on /audit/ not just /audit/pick_funnel.html.
5. **Rebuild `nav_surface_edge_matrix.json` after the resolver fix** and verify CRYPTO Smart WR falls into the 35–50% band (where the raw DB shows it).

## 7. Files touched in this run (no commit)

- `audit_dashboard/data/pick_summary_stats.json` (new)
- `audit_dashboard/pick_funnel.html` (added DISPUTED banner + Active+Closed Summary section)
- `reports/2026-05-25_crypto_78pct_wr_verification.md` (this file)
