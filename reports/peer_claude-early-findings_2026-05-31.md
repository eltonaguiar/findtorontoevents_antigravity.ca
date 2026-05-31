# Early Findings — Validation Swarm Mid-Flight
**As of:** 2026-05-31 ~21:13 UTC
**Scope:** First 5/10 expected validation reports + scanner state + DXY emission check.

---

## 1. Landed reports (5/10)

### a. `peer_claude-validate-plus-313-rolling-100`
- **Headline:** `PLUS_313:verdict=FABRICATED:definition=other:source_query_found=false`
- The "+313.43%" claim is **mathematically implausible** vs WR=25% / PF=0.61. Closest natural reading on live `trading_picks` last-100 closed cohort = +132.93% arithmetic / +257.12% compound, but only over ~48h with WR=48% / PF=3.34 (inconsistent with headline).
- Likely LLM fabrication per CLAUDE.md warning, OR cherry-picked arithmetic over undeclared filter.

### b. `peer_claude-validate-active-picks-counterfactual`
- **Headline:** Best lane = `SMART_PICKS_30D` (CRYPTO-only Sharpe 2.08, +0.39%/pick). `EQUITY_30D` LOSING (-0.89% / Sharpe -5.80). `VERIFIED_ALPHA` emits **zero rows** (claws_of_doom writes nothing → dashboard banner lane has no coverage). UEPS picks all still ACTIVE in JSON sidecar (no closed-row pipeline).
- Action: kill EQUITY_30D until intrabar resolver lands; reboot VERIFIED_ALPHA emitter; UEPS needs trading_picks sink.

### c. `peer_claude-validate-edge-stability` (manual cell pull)
- **Headline:** All 6 classes drift >5% from stale 2026-05-12 snapshot. Live: CRYPTO PF=0.96/WR=48.8% n=4082 (MIXED 7d lift); FOREX PF=2.45/WR=45.7% n=1653 (PF-rich, recency-decaying 7d WR=21%); EQUITY PF=0.61/WR=46.7% n=92 (NO_EDGE); COMMODITY narrative on stale page is **false today**.
- 4 stale-flag escalations: page hasn't rebuilt since 2026-05-12; upstream `dashboard_payload.json` was missing from local pipeline; BOND PF=362 is small-n artifact; FOREX PF=2.45 deserves money-maker-readyv2 deep-dive.

### d. `peer_claude-validate-edge-stability-auto`
- **Headline:** EST stamp on page matches (`audit_dashboard/edge_stability.html:97` already EST-formats `as_of`). **Wired**: PR **#285** (draft) — `.github/workflows/edge-stability-refresh.yml` cron 00:30 UTC daily, curls live `dashboard_payload.json` (HTTP 200 confirmed, 18.6MB) → runs `tools.edge.edge_stability --all` → commits `[skip ci]`.

### e. `peer_claude-validate-hyrotrader`
- **Headline:** `HYRO:tables=5:fresh=3:stale=1:mismatches=2:phantom_strategy_resolved=false`
- Phantom blank-strategy A+ row (score 90.0) **still served live**. Bug at `tools/hyro_pick_performance_validator.py:461` (no empty-key guard) → sorted to rank 1 → renders blank-label row at top of consumer page. No fix commit found today (last 3 commits are `[skip ci]` data refreshes). `account_snapshot` stale since 2026-04-08 (53 days); `picks_len=7` vs documented 10.

---

## 2. Still-pending reports (5/10)
Not yet landed in `reports/` matching the glob:
- `peer_claude-swarm-setup_2026-05-31.md`
- `peer_claude-external-ai-edge-review_2026-05-31.md`
- 3 additional validate-* slots (validate suite implied 8 total; only 5 landed → 3 still in-flight)

---

## 3. Scanner state
- `Winner Pattern Precursor Scanner` — in_progress (21:09:32Z)
- `CRYPTO SMART PICKS - Portfolio A/B/C/D Scanner` — in_progress (21:09:57Z)
- `ALPHA ENGINE - Dynamic Runner` — pending (21:10:07Z)

**No completed runs in the last batch yet** — too early to verify post-fix dxy emission.

## 4. DXY emission (last 90m)
- DXY-tagged strategies / DXY-symbol picks: **0** (none in last 180m either)
- By category (last 90m): crypto=28, equity=29, commodity=22, index=2, stocks=1
- **Verdict: dxy=0** — scanner hasn't surfaced any DXY-explicit emissions in the most recent window. Either (a) the dxy emitter is gated on a condition not triggering now, (b) DXY routes through `index` category (2 rows, worth checking after scanners complete), or (c) the fix isn't deployed in the active scanner generation.

---

## 5. Urgent flags

1. **PLUS_313 FABRICATED** — the headline number used somewhere upstream cannot be reproduced. If any consumer (dashboard, social, swarm prompt) is citing +313.43%, it needs a public correction. Suggest grep `+313\|313\.43` across `audit_dashboard/`, `updates/`, recent peer reports.
2. **Edge-stability page stale 19+ days** — flagship COMMODITY narrative on `/audit/edge_stability.html` is materially wrong today. PR #285 fixes the cron; should be expedited.
3. **Phantom blank-strategy A+ row** still live on Hyrotrader page despite "earlier today fix" claim — claim is false. Producer at `hyro_pick_performance_validator.py:461` + consumer HTML both lack empty-key filter.
4. **VERIFIED_ALPHA lane = 0 rows** — confirmed; consistent with DISPUTED banner on template.html:909. Lane is named on dashboard but emits nothing.
5. **DXY scanner output not yet observable** — scanners still in-flight; recheck after 21:25Z.

---

## Result
`EARLY:landed=5/10:scanner=in_progress:dxy=0:flags=PLUS_313_FABRICATED,edge_stability_19d_stale,hyro_phantom_row_unfixed,VERIFIED_ALPHA_zero_rows`
