# Cross-check & merge — deepAI audit vs peer agent work (2026-11-14)

Purpose: reconcile my live audit with prior peer work in `reports/`, `docs/`, `updates/`,
`.planning/`. Every item below is a correction, merge, or new gap. Peer quotes are verbatim.

---

## 1. CORRECTION to my zero-PnL diagnosis (important)

**My original claim:** "1,147/1,882 (61%) dropped as *spot-flicker*; resolver writes zero-delta exits."

**Peer root cause (more precise):** `reports/zero_pnl_data_pipeline_audit_2026-06-05.md`
> "`at_pick_outcomes`: **100% of the 28,218 zero rows are status=EXPIRED** ... Resolution_method =
> `TIME_EXPIRED` for every single one. **This is NOT the regime_mild_bear bug** ... the time-expiry
> resolver writes `pnl_pct=0` instead of computing the actual close-vs-entry mark."
> "Bug is concentrated in the two `backfill_widened/updated` resolvers (32,817 rows, 85.0% combined
> zero share). Newer resolvers (`backfill_2026-06-01`, `universal_v2`, `signflip_purge`) are clean (<10% zero)."

**Merge:** my `fixspec_spot_flicker_resolver.md` is renamed in spirit to a **TIME_EXPIRED mark-computation
fix**. The correct remediation is *not* "retry with better quote" but:
1. Re-resolve the 32,817 `backfill_widened/updated` rows through `backfill_2026-06-01` (peer-specified).
2. Make the time-expiry resolver compute close-vs-entry instead of writing 0.
3. Keep treating zero rows as excluded from PF (never as flat trades).
Per-class zero share (peer): FUTURES 98.4% · INDEX 99.0% · BOND 89.1% · COMMODITY 84.9% ·
FOREX 83.7% · ETF 83.1% · EQUITY 79.5% · CRYPTO 56.5%. **This matches my finding that non-crypto
classes are dead-but-displayed** and explains it: they are near-entirely zero-resolved.

## 2. CORRECTION to my "surfaces disagree = arbitrary filters" claim

**Peer explanation:** `reports/PAPER_PILOT_RESOLVER_FAIL_2026-06-05.md` documents the
**`NOMINAL_TP_LEGACY` resolver bug** — TP assumed a clean fill with no intrabar drawdown.
Intrabar 1h OHLCV replay showed reclassify rates of 28% / 87.5% / 100% / 100% across 4 sleeves
("every TP was actually SL" for ENAUSDT and DYDXUSDT).

**So the 2–8x surface spread I measured (ETF registry PF 1.84 vs money_ready 0.0216) is largely
NOMINAL (inflated) vs INTRABAR-TRUTH (corrected) resolution.** Not random filtering.
**Merge:** `fixspec_single_canonical_ledger.md` and `fixspec_surface_disagreement_banner.md` now
state that **intrabar-truth is the trustworthy surface** and nominal must be retired/labelled.

## 3. NEW FINDING I MISSED — `mega_mutation` is a genuine edge

**My audit said** "no class n≥100 shows PF>1.3 on honest surfaces" and did not name any real edge.

**Peer (2026-06-05):** `reports/2026-06-05-PER-CLASS-T2-INVENTORY-POST-FILTER.md`
> "Only `mega_mutation::crypto` is T1-confirmed (5/5 PASS_ALL_AXES) ... n=295, WR 64.1%, PF **3.16**"
> "`mega_mutation::crypto` is the only confirmed T1 in CRYPTO. The two near-promotions
> (`luxalgo_filters`, `kimi_signal_tracking`) fail the binomial axis."

**My independent Nov-14 confirmation from live payload `.picks.recent_closed`:**
| window | n | WR | PF | avg |
|---|---|---|---|---|
| all in 3,500-row window | 18 | 72.2% | **3.20** | +3.31% |
| last 30d | 7 | 57.1% | 1.58 | +1.30% |

**Conclusion: mega_mutation remains positive in Nov (PF 3.20 all-time-in-window; 1.58 last-30d on
n=7 — noisy but not decayed).** This is the single strongest real-edge candidate in the system and
my audit must credit it. It still lacks n≥100 in the live window, so it is a *pilot* candidate, not
a proven edge, per the T2 charter.

## 4. MERGE — source bans peers already specified (do not reinvent)

`reports/wr_scrutiny_honest_2026-06-05.md` already specifies the ban list:
`polymarket_whale_tracker` (n=1,582, 0.0% WR, 100% null close), `short_dominant_engine` (n=1,840,
0.0%, 99.9%), `polymarket_momentum` (n=389, 0.0%, 100%), `copy_trader_polymarket` (n=1,183, 0.1%),
`luxalgo_filters` (n=2,121, 0.0%), `prediction_market_agents` (n=2,731, 1.3%, 96.5% null),
`signal_validation` (322/353 stale → resolve ABANDONED).

**My live check (Nov 14) finds these STILL EMITTING in `.picks.active_raw`:**
`luxalgo_filter` = 16 rows, `prediction_market*` = 3 rows. **The June ban was never enforced on the
live emission path.** That is a concrete, verifiable regression to add to the fix list.
(Note: `luxalgo_filters` shows n=1,277 PF 1.11 in my Nov recent_closed — so a blanket ban may now
be too harsh; peer's "BAN" was based on 0.0% WR pre-backfill-filter. Recommend re-scope rather than
blind-ban — flag for the master-plan agent.)

## 5. NEW — data-integrity caveat that affects my own numbers

**Peer:** `reports/REAL_MONEY_MASTER_2026-06-05.md`
> "**`trading_picks` DB — 2026-06-04 closed_at backfill contaminated ~35,494 rows.** 99% of 'edges'
> were single-day batch artifacts (e.g. `futures_bb_mean_reversion` 250/255 trades on 2026-06-04)."

**Impact on my audit:** my `pf_registry` long-horizon claims (CRYPTO PF 0.232, n=23,636) read
`at_pick_outcomes` all-time and **may include 2026-06-04 backfill rows**. My 14-day recompute
(CRYPTO PF 0.805, n=471) is from Nov `recent_closed` and is NOT affected by the June backfill.
**Action:** all my registry-derived numbers are now labelled "may include 2026-06-04 backfill
contamination; 14d recompute is clean." The master plan must filter `DATE(closed_at) != '2026-06-04'`.

## 6. CONFIRMED-AGAIN — 0/9 money-ready, BOND non-viable

- Peers: "Headline: 0/9 classes are money-ready." — independently confirms my live surface_truth read.
- Peers: `reports/asset_class_90day_plan_BOND_2026-05-15.md` — "BOND is not a money-maker and should
  be de-prioritized for any real-money sizing for the full 90 days ... n=11, PF 0.66 ... 2-symbol
  (TLT 79% share) concentration ... elite_score floor unreachable for low-vol bond ETFs."
  **Merges with my "BOND dead-but-displayed (newest closed 98h)"** — same conclusion, peer has the
  mechanism (elite floor + FRED timeouts + emitter producing 0 picks).
- Peers: `REAL_MONEY_NO_SURVIVORS_2026-06-05.md` — "NO surviving real-money candidates"; all 4
  crypto sleeves refuted at resolver gate. **Strengthens my FAIL verdict.**

## 7. PEER PLAN ARTIFACTS to cite (already exist, don't duplicate)

- `reports/PR-01-cot-lag-concentration.md` — COMMODITY COT 3-day lag + CT=F concentration cap (M-095).
- `reports/PR-02-etf-vix-gate.md` — ETF VIX<25 gate (WATCH → money-ready path).
- `reports/PR-D_swarm.json` / `.planning/prs_2026_05_12/swarm_reviews/CONSENSUS.md` — swarm consensus.
- `reports/asset_class_90day_plan_ETF_2026-05-15.md` — ETF was PF 1.48/WR 58.5%/n=106 in May;
  the Nov money_ready ETF PF 0.0216/WR 2.2% is therefore either **a real regression or an intrabar
  correction of previously-nominal numbers** — must be resolved before trusting either.

## 8. PRESENTATION-vs-REALITY corroboration

`reports/2026-05-25_etf_golden_long_audit.md`:
> "The 'golden' appearance is NOT earned via the closed-ledger ... the yellow glow ... is almost
> certainly the `display_tier='ELITE'` row-styling cascade ... The label is NOT a closed-ledger
> statistical edge endorsement."
**Merges with my "presentation surfaces overstate reality" thesis** and adds a concrete display bug:
`template.html:8786` ELITE row-styling applied independent of statistical edge.

---

## 9. PLAYWRIGHT — live JS/console error test (new evidence)

Ran Chromium 1.58.2 against the live site (headless, 9–12s settle):

| Page | HTTP | JS exceptions | Console errors | Verdict |
|---|---|---|---|---|
| `/audit/` | 200 | **0** | 4 (1× 404 + 3× CORS/ERR_FAILED) | renders (2,673 rows, 112 tables, 74 tabs) but has failed sub-resources |
| `/audit/hyrotrader/` | 200 | 0 | 0 | clean, 406 rows (renders fine despite 157h-stale perf JSON — page is static) |
| `/audit/funds.html` | 200 | 0 | 0 | **BUG: "Prices: Loading..." never resolves** |
| `/audit/pick_funnel.html` | 200 | 0 | 0 | clean, 574 rows |

Concrete bugs found:
1. **404** `https://findtorontoevents.ca/audit/data/strategy_tribunal_latest.json` — missing data
   file, same class of deploy gap as the `pick_funnel_snapshot.json` 404 I already reported.
2. **CORS failures**: `min-api.cryptocompare.com` histohour HYPE fetches blocked
   (`No 'Access-Control-Allow-Origin'`), plus `api.allorigins.win`→Kucoin proxy `ERR_ABORTED`.
   HYPE price enrichment is broken in-browser.
3. **funds.html price bug**: after 12s the header still reads "Prices: Loading... • Data: 2h ago".
   It fetches `api.binance.com/api/v3/ticker/price` (+api1/api2/data-api mirrors); those
   requests do not populate the price column → user sees perpetual "Loading..." for prices
   while fund stats (71 active funds, 18,257 trades) load fine from the 2h-old payload.
4. No hard `pageerror` anywhere — the dashboards' JS is syntactically sound at runtime; failures
   are data/resource-level, not code crashes.

## 10. Summary of doc changes made
- `fixspecs/fixspec_spot_flicker_resolver.md` → root cause corrected to TIME_EXPIRED mark computation
  + backfill_widened re-resolution (peer-specified).
- `fixspecs/fixspec_single_canonical_ledger.md` → intrabar-truth is authoritative; nominal must be retired.
- `fixspecs/fixspec_surface_disagreement_banner.md` → name the NOMINAL_TP_LEGACY vs intrabar cause.
- `per_asset_class/crypto/quick_wins.md` → NEW, includes mega_mutation as the real edge + source-ban
  enforcement regression.
- `per_asset_class/_overall_dashboard/quick_wins_and_proposed_fix.md` → added Playwright bugs + backfill caveat.
- `README.md` → added "peer cross-check" section pointing here.
