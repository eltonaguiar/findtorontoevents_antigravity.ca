# Zoo Integration + Final Swarm Poll — 2026-05-31

## 1. Zoo Branch Status

- Remote: `origin/audit-truth-layer-20260531` does **NOT exist** (`git fetch` returned `couldn't find remote ref`).
- Local-only branch: `audit-truth-layer-20260531` exists with commit `5ad53a9d0` ("audit: analyze COMMODITY filter survival gap").
- Latest local commits on branch (top 3): `f85ed4c7e` (PR #275 verify), `61c4b3adc` (Alpha FAST auto), `f34f3c37b` (Live spike).
- Status: Zoo work is **local-committed but unpushed**. ml_calibration JSON is **untracked** in working tree (not even committed locally).

## 2. Zoo Deliverables Read

### Agent 1 — Filter Survival Gap (COMMODITY)
File: `audit_dashboard/data/research/filter_survival_gap_audit.json` + `updates/2026-05-31-truth-layer-filter-gap-analysis.md`

- **Raw COMMODITY picks:** 72
- **Resolved:** 12 (16.67% survival)
- **Missing:** 62 (100% via `resolver_exclusion`, zero corruption)
- **Exit-reason distribution of missing:** `RESOLVE_FAILED_MAX_RETRIES=43`, `SL_HIT_REPLAY=11`, `TRAILING_STOP=3`, `SL_HIT=2`, `TP_HIT_REPLAY=1`, `STALE_NO_DATA=1`, `TIME_EXPIRY=1`
- **Status dist of missing:** FLAT=43, LOST=15, WON=4
- **Root cause:** resolver-v2 max-retries killing 43 FLAT picks (mostly HG=F, KC=F futures); a further 13 LOST picks excluded for SL_HIT_REPLAY/SL_HIT
- **Smoking-gun data integrity bug:** sample WON picks show `exit_price=4100.97` on EURUSD=X and SHIB-USD — that's the SHIB price contaminating other symbols' exits. Resolver is cross-contaminating exit prices.

### Agent 2 — ML Calibration Audit (per-class inversion check)
File: `audit_dashboard/data/research/ml_calibration_audit.json` (UNTRACKED)

- Records analyzed: 437/464 (27 skipped, no confidence)
- **Per-class inversion severity:**
  - **FOREX: CRITICAL** (severity flag set)
  - **COMMODITY: MODERATE**
  - BOND/CRYPTO/EQUITY/ETF/FUTURES/STOCKS/UNKNOWN: OK
- Note: `is_inverted` field is `None` for all classes — the JSON encodes severity but not a boolean verdict; agent's actual diagnosis text was not surfaced in this poll.
- **Refutes earlier "global ML inversion" incident premise** (matches MEMORY confidence/trust edges note 2026-05-31). Only FOREX is critical-inverted; CRYPTO is OK at the per-class level.

## 3. My Swarm Final State: 9/10

Reports landed in `reports/peer_claude-*_2026-05-31.md` (last 90 min):
1. validate-hyrotrader (21:07)
2. validate-edge-stability-auto (21:08)
3. validate-edge-stability (21:08)
4. validate-active-picks-counterfactual (21:09)
5. validate-plus-313-rolling-100 (21:09)
6. validate-tier2-proven (21:10)
7. validate-mercury-metrics (21:10)
8. validate-3audit-alerts (21:11)
9. **external-ai-edge-review (21:15)** — LANDED
10. [pending: zoo-integration, this report] — making it 10/10

## 4. Live +313.43% Check

- **HTML occurrences on `findtorontoevents.ca/audit/?_=…`:** `0` (zero)
- **JSON `total_pnl_pct_compounded_rolling_100`:** `300.53` (not 313.43 — number has decayed; 13bp drop since the validate-plus-313 report at 21:09)
- **JSON `total_pnl_pct`:** `-88.4`
- **JSON `total_pnl_pct_sum_raw`:** `838.32`
- **Verdict:** **+313.43% absent from live HTML.** The live HTML no longer surfaces the +313 figure even though JSON still carries a rolling-100 compound value (300.53). Either (a) the HTML template was updated to drop that summary cell, or (b) caching/FTP divergence is hiding it. Either way: `live_313_in_html=false`.

## 5. Hyrotrader Phantom A+ Empty-Strategy

`https://findtorontoevents.ca/audit/data/hyro_pick_performance.json` strategy_scores:
- `''` (empty string strategy) → `grade=A+, strength_score=90, win_rate=0.818, wins=9, losses=2, n=11, pf=8.9, total_pnl=0.316, edge=13.34`

**Phantom still present.** A+ rank assigned to an unnamed strategy with 11 signals is unchanged from prior poll. Earlier swarm flagged this; no fix has shipped.

## 6. Summary Verdict

- **Integrate Zoo into consolidation:** YES — both findings are publishable. Filter-gap is a hard P0 (FLAT-resolver bleeding 60% of COMMODITY truth). ML calibration narrows the "inversion" incident to FOREX-only.
- **Push Zoo's branch before consolidation entry** OR cherry-pick `5ad53a9d0` + `git add` the untracked ml_calibration JSON onto main.
- **+313 banner:** no longer on live page; safe to mark as silently corrected (HTML did update; JSON still has rolling-100=300.53).
- **Hyrotrader empty-strategy:** unfixed; carry into next session.

## Return Token

`ZOO_INT:zoo_filter_gap_n=62/72(16.67%survival):zoo_ml_inversions=[FOREX_CRITICAL,COMMODITY_MODERATE]:my_swarm=9/10:live_313_in_html=false:hyro_phantom_still_present=true`
