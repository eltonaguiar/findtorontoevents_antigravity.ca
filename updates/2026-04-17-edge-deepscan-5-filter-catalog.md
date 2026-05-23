# Edge Deepscan #5 — Filter Catalog & Edge-Claim Re-verification

**Date:** 2026-04-17
**Author:** Claude (audit subagent)
**Source files audited:**
- `audit_dashboard/template.html` (16,400 lines)
- `audit_dashboard/hc_filter.js` (497 lines)
- `audit_trail/quality_gates.py` (4,346 lines)
- `audit_trail/dashboard_generator.py` (13,367 lines)
- `audit_dashboard/data/dashboard_data.json` (21 MB, 3,500 closed picks)
- `alpha_engine/smart_picks_engine.py` (2,102 lines)
- `config/hc_gate_params.json`, `config/hf_conviction_tiers.json`

**Method:** Loaded `picks.recent_closed` (n=3,500) and recomputed each headline edge claim. WR/PF reported with simple status-based win classification (`status=WON` or `pnl_pct>0`).

---

## 1. Top-3 Stale Claims (lead findings)

| # | Claim (template.html lines 844–854) | Reality (n=3,500 recent_closed) | Drift |
|---|---|---|---|
| 1 | "Crypto Confidence 0.85–0.90 — strongest single filter: **82% WR, PF 11.8**" | n=87 across all conf-decimal forms; if you keep only the strict crypto+0.85–0.90 bucket: **WR 71% PF 47.6 on n=31**; the "all variants" superset is **WR 52.9% PF 0.94**. The 82%/11.8 figure does not reproduce. | -10pp WR, -10× PF (depending on slice) |
| 2 | "Direction = BUY → 28.9% WR PF 0.38 on n=3,909" vs "Direction = LONG → 54.9% WR PF 3.14 on n=441" | n(BUY)=**26**, n(LONG)=**2,547**. The cohorts are inverted (LONG is the dominant 73% of book). The "BUY 3,909 vs LONG 441" claim is exactly backwards relative to the current dataset. | Cohort sizes inverted; claim text is wrong |
| 3 | "Proven + High Confidence Combo: 71.3% WR, PF 13.21, n=94" (PROVEN + conf 0.8–0.9) | **n=1**, WR 0%, PnL −6.15%. The combo collapses because `trust_tier='PROVEN'` is now sparse (508/3,500) and `confidence` rarely lives in 0.8–0.9 for proven rows. | n collapsed 94 → 1 |

Plus four more failing claims summarised in §6.

---

## 2. Filter UI Catalog

Filter chip / button definitions across `template.html` lines 800–1010 plus handlers around 11080–11400. "Tooltip claim" is verbatim from the `title=` attribute. "Re-verified" uses recent_closed n=3,500 unless noted.

| Name | Where | Default | Logic (code ref) | Tooltip Claim | Re-verified | Status |
|---|---|---|---|---|---|---|
| Asset dropdown | `#f-asset` L926 | All | Server-supplied options, filters by `pick.asset_class` | "All" | wired (filter logic L3625-3700) | ACCURATE |
| System dropdown | `#f-system` L928 | All | Filters by `pick.source_system` | (none) | wired | ACCURATE |
| Status dropdown | `#f-status` L930 | All | OPEN / CLOSED filter | (none) | wired | ACCURATE |
| Direction dropdown | `#f-dir` L932 | All | LONG / SHORT (no BUY option even though 26 BUY rows exist) | (none) | wired but missing BUY/SELL options | GHOST OPTION |
| Conf dropdown | `#f-conf` L940 | All | `pick.confidence ≥ threshold` | "≥ 0.50 / 0.65 / 0.75 / 0.85" | wired | ACCURATE |
| PnL dropdown | `#f-pnl` L938 | All | `pick.pnl_pct` band | "Profitable / Losing / >5% / >10%" | wired | ACCURATE |
| Age dropdown | `#f-age` L942 | All | `pick.age_hours` cutoff | "≤1h ... ≤48h" | wired | ACCURATE |
| TP-Rem dropdown | `#f-tp-rem` L944 | All | `pick.tp_remaining_pct ≤ N` | "≤30/50/70%" | wired | ACCURATE |
| Conflicts dropdown | `#f-conflicts` L946 | All | `pick.has_conflict` | "No conflicts / Conflicts only" | wired | ACCURATE |
| Timeframe dropdown | `#f-timeframe` L947 | All | `pick.trade_timeframe` enum | "SCALP/INTRADAY/SWING/POSITION" | wired | ACCURATE |
| Sort dropdown | `#f-sort` L948 | Default (Time) | Sort key for active+closed table | "Score / ML / Smart / PnL / Conf / TP / Age" | wired | ACCURATE |
| Score Tier dropdown | `#f-score-tier` L955 | All Scores | `score>=30/50/70` | "Below 30 = 19-35% WR; 70+ = **82% WR**" | 70+: see §3 — claim ≈55% in current data, not 82% | STALE |
| Best Score btn | `#btn-best-fresh` L950 | inactive | Sort by score desc + age≤48h | "Dashboard-score preset only" | wired (L11083) | ACCURATE |
| Proven Only btn | `#btn-proven-picks` L951 | inactive | `window._provenOnlyFilter`, name-match against `_TRUST_PROVEN_STRATEGIES`/`_TRUST_PROVEN_SYSTEMS` (L7480-7520) | "Filters using manual trust registry, NOT live closed-pick query" | wired (L11122) — tooltip is honest | ACCURATE |
| In Profit btn | `#btn-strong-picks` L952 | inactive | `pnl_pct>0` then sort | "Currently profitable picks moving toward target" | wired (L11100) | ACCURATE |
| Smart Picks btn | `#btn-smart-picks` L967 | inactive | `applySmartPicks()` — intersect active vs `D.smart_picks_feed` keys | "Smart Picks filter cannot be verified as edge on closed data" | tooltip honest; logic intersects with backend feed | ACCURATE-ish (see §4) |
| Verified Alpha btn | `#btn-verified-alpha` L968 | inactive | `isVerifiedAlphaPick()` (L1995-2063) | "≥55% forward WR on ≥5 trades" + PM/copy-trader allowlist | code matches: `forward_wr ≥ 0.55 && forward_trades ≥ 5` (L2037) | ACCURATE |
| HIGH CONVICTION btn | `#btn-conviction-picks-hero` L969 | inactive | `applyHighConvictionPreset` (L11298) → `filterHcStrict` = `hc_filter.js` gates AND `passesValidatedEdgePerClass` | "score≥40, trust tier, forward WR, regime, consensus + per-asset floors" | 9 gates exactly as listed in `hc_filter.js`; per-class floors below | ACCURATE (logic), STALE (per-class floors – see §3, §5) |
| Hide-No-Price chk | `#f-hide-no-price` L971 | checked | Hides rows with `current_price` falsy | (none) | wired | ACCURATE |
| Clear All btn | `#btn-clear-filters` L972 | — | Resets all filters + `window._hcEdgeStrict=false` | (none) | wired | ACCURATE |
| Col Settings btn | `#btn-col-settings` L974 | — | Toggles column visibility panel | "Customize visible columns" | wired | ACCURATE |
| Reload Page btn | `#btn-refresh` L983 | — | `location.reload()` | "Reload page with latest cached data" | wired | ACCURATE |
| Full Refresh btn | `#btn-full-refresh` L984 | — | Triggers GHA workflow (auth-gated) | "Triggers GitHub Actions pipeline... requires auth token" | tooltip honest; falls back to reload | ACCURATE |
| Refresh Picks btn | `#btn-refresh-picks` L985 | — | Runs Momentum Scalp Scanner | "Run Momentum Scalp Scanner" | wired | ACCURATE |
| Export Active CSV | `#btn-export-excel` L964 | — | CSV of filtered active | (descriptive) | wired | ACCURATE |
| Export Closed CSV | `#btn-export-closed` L965 | — | CSV of filtered closed | (descriptive) | wired | ACCURATE |
| Export All CSV | `#btn-export-all` L966 | — | CSV of all picks | (descriptive) | wired | ACCURATE |
| Perf Conviction chips | `#perf-conviction-bar` L4327 | "All picks" | `_PERF_CONVICTION_FILTER` modes: all / high-grade / trusted / rr-15 / safe-symbols | "High-grade D/F lose -375% PnL on non-crypto; Trusted drops BANNED/UNTRUSTED/WATCH" | "Trusted" mode keeps RELIABLE+PROVEN. RELIABLE=1565, PROVEN=508; WATCH=816 dropped. wired (L4373-4389) | ACCURATE |
| Perf Recent N chips | same bar L4351 | "All" | `_PERF_RECENT_N`, slices closed picks by close-time desc | "Tiles with <5 picks fall back to All" | wired (L4381) | ACCURATE |
| Tab buttons | `.tab-btn` L990-1005 | "Overview" | Show/hide tab-content divs | n/a | wired | ACCURATE |
| Mimo Entry QC btn | `#btn-xiaomi-mimo-entry` (no UI button per L954 comment) | — | `passesXiaomiMimoEntryPick` L2075 — entry-time checks only | "regime aligned, fwd WR≥5% w/3 trades, tech 3/3, conf 2-4, trust WATCH+, TF intraday/swing" | logic exists, button removed L954 — handler retained but no DOM trigger | **GHOST** |
| Trust Book toggle | `#btn-trust-book-toggle` L11140 | — | `window._hfTrustBook` narrows to PROVEN/DEVELOPING | (none) | listener attached only if button exists; button not rendered in current HTML | **GHOST** |
| Score Gate filter | `window._scoreGateFilter` L3652,8300 | false | `score >= 24` filter | (none) | logic wired in 4 places, but no UI button toggles it (state init L3557, never set true except `applySmartPicks`) | **GHOST UI** (logic ok) |
| Removed High Conv duplicate | comment L953 | — | "Removed duplicate High Conviction button" | — | confirmed removed | OK (cleanup note) |
| Removed Warnings tab | comment L1005 | — | "Removed: Warnings tab" | — | tab-content `#tab-warnings` div still exists L1063 (orphan) | **GHOST DIV** |
| Removed Audit Log tab | comment L1006 | — | "Removed: Audit Log tab" | — | tab-content `#tab-audit` div still exists L1064 (orphan) | **GHOST DIV** |

---

## 3. Edge-Claim Re-verification (current `recent_closed` n=3,500)

All numbers below recomputed by Python from `audit_dashboard/data/dashboard_data.json` (loaded 2026-04-17). PF = sum(positive PnL) / |sum(negative PnL)|.

| Claim (location) | Tooltip text | Re-computed | Drift | Status |
|---|---|---|---|---|
| L846 | "Crypto Conf 0.85-0.90: 82% WR PF 11.8" | n=87 WR 52.9% PF 0.94 (full 0.85-0.90); strict numeric `[0.85, 0.9)` n=31 WR 71.0% PF 47.6 | -11pp WR / +PF on smaller slice; original 82% not reproducible | STALE |
| L846 | "Crypto >0.90 hits overfit cliff (47% WR)" | n=22 WR 54.5% PF 3.63 (closer to 50%) | +7pp better than claimed | STALE (not as bad as advertised) |
| L847 | "Proven ML Strategies: 79.4% WR, PF 11.34, n=199" | All PROVEN n=508 WR 54.9% PF 2.27. PROVEN with 'ml' substring n=13 WR 53.8% PF 1.46 | n collapsed 199→13; WR -25pp; PF -10× | **STALE — major** |
| L848 | "Proven + Conf 0.8-0.9 Combo: 71.3% WR PF 13.21 n=94" | n=1 (one pick) WR 0% PnL −6.15% | n collapsed 94→1 | **STALE — major** |
| L849 | "R:R 1.5-2.0 only profitable band: 55.8% WR PF 3.15 +0.05% avg" | n=1,267 WR 52.6% PF 1.81 +0.70% avg | -3pp WR, -1.3 PF | STALE (still profitable; numbers softer) |
| L849 | "R:R ≥2.0 harmful: 29.5% WR -0.16% avg" | n=949 WR 45.6% PF 1.87 +0.42% avg | +16pp WR, PF actually >1, sign positive | **STALE — claim inverted** |
| L849 | "R:R <1.0 catastrophic: 25.2% WR" | n=73 WR 47.9% PF 0.83 | +23pp WR, less catastrophic | STALE |
| L850 | "FOREX peak 0.75-0.80 (49% WR); 0.70-0.75 DANGER 25%" | 0.75-0.80: n=420 WR 49.3% PF 2.95. 0.70-0.75: n=39 WR 25.6% PF 0.24 | both reproduce | **ACCURATE** |
| L850 | "EQUITY bipolar: >0.90 67% WR; 0.85-0.90 worst 20%" | 0.90+: n=44 WR 63.6% PF 2.31. 0.85-0.90: n=5 WR 20% PF 0.25 | both within 4pp of claim | **ACCURATE** (note: 0.85-0.90 only n=5, fragile) |
| L850 | "COMMODITY peak 0.70-0.75 (48% WR)" | n=89 WR 48.3% PF 1.89 | reproduces | **ACCURATE** |
| L851 | "Direction=BUY: n=3,909 WR 28.9% PF 0.38" | **n=26** WR 30.8% PF 0.60 | **n cohort collapsed 3,909→26; field semantics changed** | **STALE — n wrong by ~150×** |
| L851 | "Direction=LONG: n=441 WR 54.9% PF 3.14" | **n=2,547** WR 50.1% PF 1.85 | n grew 441→2,547; WR -5pp | **STALE — n wrong by ~6×** |
| L851 | "BUY+LONG combo at 62.6% WR" | `signal_type=BUY AND direction=LONG`: n=0 (signal_type field not present in current rows) | n=0 | **STALE — combo unreachable** |
| L852 | "High-grade A/B 49.3% WR PF 0.66 n=483 — NOT an edge" | n=996 WR 58.5% PF 3.00 +0.92% avg | +9pp WR, PF 4.5× the claim, **A/B IS an edge now** | **STALE — claim contradicts data** |
| L853 | "ML-Enhanced (crypto) 55.1% WR PF 1.77" | n=344 WR 66.6% PF 4.51 +1.87% avg | +11pp WR, PF +2.7× | STALE (better than claimed) |
| L853 | "Quan Engine (crypto) 29.0% WR PF 0.38" | n=1 (single pick) | n collapsed → unverifiable | STALE-but-blocked (quan_engine in BLOCKED_SOURCE_SYSTEMS already) |

**Composition snapshot:** asset = CRYPTO 1873 / FOREX 785 / COMMODITY 416 / EQUITY 346 / ETF 63 / BOND 17. direction = LONG 2547 / SHORT 927 / BUY 26. trust_tier = RELIABLE 1565 / WATCH 816 / PROVEN 508 / UNTRUSTED 347 / BANNED 264 (note: tooltip lists tiers as "PROVEN/DEVELOPING/WATCH/SANDBOX/PROBATION" but the data uses **RELIABLE/UNTRUSTED/BANNED** labels — see §6).

---

## 4. Smart Picks weight breakdown — verified

`alpha_engine/smart_picks_engine.py` L867-973 (function `score_pick`).

| Component | Tooltip claim | Code value (crypto) | Code value (non-crypto) | Status |
|---|---|---|---|---|
| Regime match | 25% | `regime_max=25` (L878) | `regime_max=15` (L875) | ACCURATE for crypto; non-crypto silently downweights to 15% |
| Quality / elite score | 35% | `quality_max=35` (L879) | `quality_max=40` (L876) | ACCURATE for crypto; non-crypto secretly bumps to 40% |
| Freshness | 15% | 15→12→8→4→0 by age bucket (L900) | same | ACCURATE |
| TP upside | 15% | 15→10→5→0 by tp_rem (L903) | same | ACCURATE |
| HTF alignment | 10% | 10 / 5 / 0 by `htf_bias` (L921-930) | same | ACCURATE |
| Proven Winner Boost | "+8 to +15" | `PROVEN_WINNERS[strat]['boost']` + tier_strength + `rapid_fire→max(.,12)` (L935-957) | same | ACCURATE — but boost also stacks `_sym_boost` from `symbol_strength_tiers.json`, so range can exceed +15 |
| Copy Trader Premium | **NOT IN TOOLTIP** | +10 if `_is_vetted_copy_pick` (L962) | same | **HIDDEN COMPONENT** |
| Institutional Sweet Spot | **NOT IN TOOLTIP** | +10 if ML score ≥0.65 AND conf 0.60-0.70 (L971) | same | **HIDDEN COMPONENT** |
| Regime penalty | **NOT IN TOOLTIP** | -20 LONG in bear (non-exempt) / -8 in neutral (L905-915) | only non-crypto skips | **HIDDEN COMPONENT** |

**Verdict:** weights match tooltip but tooltip omits 3 score modifiers (+10 copy, +10 institutional, ‑20 regime penalty) that can swing a pick ±20 points. Update the glossary to list them.

---

## 5. Verified Alpha + High Conviction + Trust Tier definitions

### Verified Alpha (`isVerifiedAlphaPick`, template.html L1995-2063)
Eight gates — pick passes if ANY of:
1. `source_system` in `pmSources` (6 prediction-market sources, L2007)
2. `source_system` in `copySources` (7 audited copy-trader sources, L2012)
3. Strategy prefix in {`copy_pm_`, `clone_hl_`, `copy_hl_`, `hs_`, `consensus_`} (L2017-2021)
4. `multi_asset_copytrader` source AND specific 4 strategies (L2024-2029)
5. `cta_replicator` source AND specific 3 strategies (L2030-2034)
6. **`forward_wr ≥ 0.55 AND forward_trades ≥ 5`** (L2037) ← matches tooltip
7. v102 expansion: `history_wr ≥ 0.55 AND history_trades ≥ 20` OR `wf_p_value < 0.05` (L2043-2046)
8. v102 fallback: `strat_fwd_wr ≥ 0.55 AND strat_fwd_trades ≥ 5` (L2052)
9. Score AND trust escape: `score ≥ 80 AND trust_score ≥ 6` (L2056)
10. Consensus escape: `agreement_count ≥ 3 AND strat_fwd_wr ≥ 0.50 AND strat_fwd_trades ≥ 3` (L2060)

**Tooltip claim verified:** the ≥55% / ≥5 thresholds are correct, but the tooltip omits seven additional escape clauses. Result: a pick can show as Verified Alpha with **forward_wr=0** if it has a PM/copy source. Tooltip understates the breadth.

### High Conviction (`hc_filter.js` + `passesValidatedEdgePerClass` template.html L11210)
9 shared gates (`evaluateHcGates1to9`, hc_filter.js L286):
1. Score ≥ 40 (`scoreAbsoluteFloor`)
2. Score ≥ 50 OR trust ≥ 8 (`scoreCompoundFloor`)
3. trust_tier NOT in {SANDBOX, UNPROVEN, PROBATION, DEMOTED}
4. Asset-class FWD trades floor (CRYPTO/EQUITY/FOREX = 5; BOND/FUTURES/COMMODITY/ETF = 2)
5. Asset-class FWD WR floor (CRYPTO 45 / EQUITY 55 / FOREX 55→50 if N<20 / COMMODITY 40 / FUTURES 40 / BOND 40 / ETF 40)
6. Asset-class score floor (CRYPTO 55 / EQUITY 50 / FOREX 40 / COMMODITY 40 / FUTURES 40 / BOND 40 / ETF 40)
7. Trust score floor (CRYPTO 6 / other 5)
8. Confidence cliffs: conf>0.95 needs FWD≥30; conf>0.90 needs FWD≥20; conf in [0.85,0.95] needs FWD≥30
9. Regime: LONG blocked in bear regimes; SHORT in bull requires PROVEN
10. Walk-forward verdict not "FAILING"
11. ≥3 independent signal groups (skip for stamped S/A tier)

PLUS **per-class validated-edge gate** (template.html L11210-11240):
- CRYPTO: `fwd_wr≥45% AND score≥55 AND trust≥3`
- EQUITY: `fwd_wr≥55% AND score≥50 AND trust≥3`
- FOREX: `fwd_wr≥55% (50% if N<20) AND score≥40`
- COMMODITY/BOND/ETF/FUTURES: **ALL REJECTED** (returns false at L11240)

**Tooltip claim accurate.** Per-asset-class floors documented above match tooltip's "per-asset-class floors" mention. **Note: COMMODITY data shows PF 1.89 for conf 0.70-0.75 cohort (n=89, real edge), but it's still rejected by HC strict — gap to investigate.**

### Trust Tier source-of-truth (`getTrustTier`, template.html L7552-7659)
Single function, longest-prefix-match precedence. Tier elevation rules (Bayesian-shrunk WR with 50% prior, weight 20):

| Tier | Per-strategy gate (L7616-7621, ≥5 trades) | Per-system gate (L7642-7647, ≥5 trades) |
|---|---|---|
| PROVEN | shrunkWR ≥58 AND PF ≥2.0 (manual registry override) | (manual registry, with v95 live-data override) |
| DEVELOPING | shrunkWR ≥53 AND PF ≥1.5 | shrunkSysWR ≥57 AND PF ≥2.0 OR shrunkSysWR ≥53 AND PF ≥1.5 |
| WATCH | shrunkWR ≥48 OR ≥42 | shrunkSysWR ≥50 / ≥47 |
| SANDBOX | shrunkWR <42 | shrunkSysWR <47 OR <40 with n≥20 |
| PROBATION | system in `_TRUST_PROBATION` table | — |
| Auto-disable | PF<1.1 with ≥20 trades → SANDBOX | PF<1.1 with ≥20 trades → WATCH |

**Rolling, recomputed every render.** Tiers are NOT point-in-time pinned — they re-classify on every payload load.

**Schema clash:** the perf-conviction-chip "Trusted" mode (template.html L4296-4304) keeps `RELIABLE` and `PROVEN`. But `getTrustTier()` only ever returns `PROVEN/DEVELOPING/WATCH/SANDBOX/PROBATION/DEMOTED` — never `RELIABLE`/`BANNED`/`UNTRUSTED`. Yet `recent_closed` rows ship with `trust_tier` already containing `RELIABLE` (1565) / `BANNED` (264) / `UNTRUSTED` (347). **Two different vocabularies coexist** — closed-pick stamping uses one taxonomy, dashboard reclassification uses another. This is a major data-integrity bug that needs reconciliation.

---

## 6. TV Account Name Tag System — `HIGHFWWRABV55_SCOREABOVE50_V3`

**Searched:** all of repo for `HIGHFW*`, `SCOREABOVE*`, `FWWR*` — **zero hits in code, config, JSON, or markdown.**

**Conclusion:** the TV paper account name `HIGHFWWRABV55_SCOREABOVE50_V3` has **no programmatic backing** in this codebase. It is a free-form label entered into TradingView's paper portfolio dropdown. The 5 documented portfolios in `.claude/skills/tv-paper-trade/SKILL.md` are: SCALPER ($2K), TESTER ($3K), TRUSTOURSCORE ($90K), BROKIE ($1K), zerounderscore ($100K). HIGHFWWRABV55 is not in that list either.

Inferred meaning from naming convention:
- `HIGHFWWRABV55` = "high forward win-rate above 55%" (matches HC's `forwardWRMinPct: 55` floor)
- `SCOREABOVE50` = "score above 50" (matches HC's `scoreCompoundFloor: 50`)
- `_V3` = third iteration

**Hypothesis:** the user manually selected picks that *should* satisfy `fwd_wr ≥ 55% AND score ≥ 50` and pasted them into a new TV account. If 8/8 are red, the most likely failure modes are:
1. Picks were chosen from the dashboard while HC strict filter was OFF → user saw rows that pass per-class CRYPTO floor of **45%**, not 55%.
2. `score` field on Active Picks is the dashboard-computed `computeScore` (template.html L7661+), which is a multi-factor weighted metric — not the same `score` semantics used in any backtest validation.
3. The "Proven + High Confidence Combo: 71.3% WR n=94" claim that anchored the user's mental model has collapsed to n=1 (see §3 row 4) — meaning the historical edge that justified `>=55% / >=50` no longer exists in the current data.

**Recommendation:** add a config file `config/tv_paper_account_filters.json` mapping each TV account name to an explicit JSON predicate (asset class + score floor + fwd_wr floor + trust_tier whitelist + min N), and have a CLI tool re-validate the filter against `recent_closed` weekly. Without this mapping the user has no way to audit whether picks placed under a label match the label's promise.

---

## 7. Ghost Filters

| ID | Type | Issue |
|---|---|---|
| `#btn-xiaomi-mimo-entry` | Removed UI button | Comment at L954 says "removed 2026-04-11"; handler at L11168 is `if (_btnMimo) addEventListener` — survives, but DOM element never rendered. Filter logic still callable via `window._xiaomiMimoEntryFilter = true` from console. |
| `#btn-trust-book-toggle` | Conditional handler, button missing | L11140 wrapped in `if (_btnTB)`, button never declared in HTML. Listener never attached. |
| `#tab-warnings` div | Orphan tab-content | Tab button removed (L1005 comment) but `<div id="tab-warnings">` still present at L1063. Unreachable. |
| `#tab-audit` div | Orphan tab-content | Same — comment L1006, div L1064 still exists. Unreachable. |
| `f-dir` BUY/SELL options | Missing options | Dropdown only has LONG/SHORT but data has 26 BUY rows; user cannot filter to that cohort from UI. |
| `window._scoreGateFilter` | Missing UI | Logic wired in 4 render paths (L3652, 8300, 10624, etc.) but no UI button toggles it; only set true by `applySmartPicks` indirectly. The "Score ≥ 24" filter tag (L4145) appears with no way to toggle it on. |
| Mimo SHORT-bias path | Filter exists, blocklist 4 symbols | L2066 `_XIAOMI_MIMO_SYMBOL_BLOCKLIST` blocks 4 symbols; rest of code references regime/tech alignment but UI exposes nothing. |

---

## 8. Stale Claims Summary (drift > 10pp OR n collapsed > 5×)

| Claim | Drift type | Evidence |
|---|---|---|
| "Crypto Conf 0.85-0.90: 82% WR PF 11.8" | WR off by -10–30pp | n=87 WR 52.9% PF 0.94 OR n=31 WR 71% PF 47.6 (sliced) |
| "Proven ML Strategies: 79.4% WR PF 11.34 n=199" | WR off by -25pp; n collapsed 199→13 | n=13 PROVEN+'ml' WR 53.8% PF 1.46 |
| "PROVEN + Conf 0.8-0.9 Combo: 71.3% WR n=94" | n collapsed 94→1 | one pick, lost |
| "Direction=BUY n=3,909 / Direction=LONG n=441" | Cohort sizes inverted (~150× off for BUY, ~6× off for LONG) | LONG=2,547, BUY=26 |
| "BUY+LONG combo 62.6% WR" | n=0 — combo unreachable | signal_type field absent from current closed rows |
| "R:R ≥2.0 harmful: 29.5% WR" | sign of claim inverted | n=949 WR 45.6% PF 1.87 — actually positive |
| "High-grade A/B: 49.3% WR PF 0.66 — NOT an edge" | claim contradicts data | n=996 WR 58.5% PF 3.00 — IS an edge |
| Score Tier "70+ → 82% WR" (L960) | Untestable in current dataset (most rows lack `score` field on closed picks); but claim repeated in 2 places | needs verification with `pick.score` populated on closed |
| Trust tier vocabulary mismatch | RELIABLE/BANNED/UNTRUSTED in data, never produced by `getTrustTier()` | data has 1565 RELIABLE / 264 BANNED that the dashboard re-classifier doesn't know about |

---

## 9. Top-3 Recommended Fixes

1. **Rewrite the L835-855 "Where Our Edge Actually Is" panel** with a build-time data-driven generator. Replace every hardcoded percentage with a token like `{{CRYPTO_CONF_85_90_WR}}` populated by a script that runs on each `recent_closed` rebuild. Add a `last_verified_at` timestamp + `n_at_verification` per claim. **Acceptance:** zero hardcoded numbers in the help overlay; every claim has a freshness badge.

2. **Reconcile the trust-tier vocabulary.** Either:
   - (a) make `getTrustTier()` return `RELIABLE/BANNED/UNTRUSTED` when those are present in `pick.trust_tier`, OR
   - (b) re-stamp every row in `picks.recent_closed` to use the 5-tier taxonomy listed in the help overlay (PROVEN/DEVELOPING/WATCH/SANDBOX/PROBATION).
   Then update the perf-conviction "Trusted" predicate (L4296-4304) to use the canonical vocabulary. **Acceptance:** `set(pick.trust_tier for pick in recent_closed) ⊆ {PROVEN, DEVELOPING, WATCH, SANDBOX, PROBATION, DEMOTED}`.

3. **Create `config/tv_paper_account_filters.json`** that maps each TradingView paper account name to an explicit predicate (asset_class, min_score, min_fwd_wr, min_fwd_trades, allowed_trust_tiers, allowed_strategies). Add `tools/audit_tv_account.py <account_name>` that re-runs the filter against current `picks.active` and current `picks.recent_closed` and reports forward+backward edge. **Acceptance:** running `python tools/audit_tv_account.py HIGHFWWRABV55_SCOREABOVE50_V3` prints (a) what picks would currently qualify, (b) historical WR/PF for the cohort matching that filter, (c) a green/red "edge confirmed" verdict.

---

## Appendix: Sources Re-verified

```
Total recent_closed: 3,500
Asset composition: CRYPTO 1873 / FOREX 785 / COMMODITY 416 / EQUITY 346 / ETF 63 / BOND 17
Direction:        LONG 2547 / SHORT 927 / BUY 26 (no SELL)
Trust tier:       RELIABLE 1565 / WATCH 816 / PROVEN 508 / UNTRUSTED 347 / BANNED 264
Elite grade:      C 1536 / B 980 / D 890 / F 78 / A 16
```

End of report.
