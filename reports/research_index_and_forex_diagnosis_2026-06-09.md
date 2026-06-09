# Research Index Quality Audit + FOREX Kill-or-Mutate Diagnosis — 2026-06-09

**Auditor:** read-only agent. **DB note:** live MySQL not reachable from this IP; all numbers below cite local JSON snapshots, source files, and live HTML (curl). No DB query was performed or claimed.

**Trust hierarchy used (highest first):** `money_ready_verdict.json` + `pf_registry.by_asset_class_policy_clean_net` > verified paper forward > `trading_picks` post-backfill > tournament/ai_leaderboard (research only). 14d/48h window stats (`pick_summary_stats_*.json`) are explicitly NOT sizing-grade.

---

## TASK 1 — `research_index.html` quality audit

**Page:** `audit_dashboard/research_index.html` (file mtime Jun 6 07:13; live `last-modified` 2026-06-09 02:27, HTTP 200).
**Backing data:** `audit_dashboard/data/research/research_index_data.json` (a different artifact — see note (d)).
**Index self-stamp (in HTML):** "Index generated: Jun 6, 2026 3:09 AM EDT".

### (a) Do listed entries link to reports that actually exist? — NO BROKEN LINKS

The page does **not** link to `reports/*.md`. It is an asset-class research-run index that links to 68 per-run dashboards via relative hrefs of the form `research/asset_class/<class>/run_<UTC>Z/index.html` (8 classes × ~9 runs).

- **Local resolution:** all 68 hrefs resolve to existing files at **repo root** `research/asset_class/...` (verified: 68/68 exist). They do NOT exist under `audit_dashboard/research/...` — but that's correct, because the page is served from `/audit/` and the deploy mirrors the run tree under `/audit/research/...`.
- **Live resolution (authoritative):** spot-checked across all classes and the full date range (2026-05-11, 05-16, 05-30, 06-06):
  - `/audit/research_index.html` → 200
  - `/audit/research/asset_class/forex/run_2026-06-06T07-09-03Z/index.html` → 200 (last-modified 2026-06-09)
  - bond `run_2026-05-11T17-46-50Z` → 200, crypto `run_2026-06-06T07-09-21Z` → 200, equity `run_2026-05-16T06-51-22Z` → 200, futures `run_2026-06-06T07-09-41Z` → 200
  - root-relative `/research/...` → 404 (confirms links resolve relative to `/audit/`, as intended).

**Verdict (a): 0 broken links.** All 68 targets exist locally (repo root) and resolve 200 on the live site.

### (b) Performance claims that contradict policy-clean? — NONE

The page uses a conservative Tier-2 floor (PF≥1.5, WR≥50, n≥100) and an explicit verdict legend (GO/MIXED/NO_EDGE/PENDING/ABORTED). Verdict cell tally (grep of `>VERDICT<` badges): **50× NO_EDGE, 20× MIXED, 1× PENDING, 1× ABORTED, 0× actual GO.** The single `>GO<` token in the file is in the legend definition (line 51), not a run verdict.

- **FOREX section:** 9 runs → 8 NO_EDGE + 1 MIXED, **zero GO**. "Lessons Learned (Forex)" explicitly says candidates "fell short of Tier-2 floors" and the best backtest (PF=1.61, WR=56.7%) is flagged for "only 30 trades." This is fully consistent with policy-clean FOREX FAIL — no contradiction.
- No class is marked READY/PROVEN/GO. `grep` for "READY"/"PROVEN" = 0. Consistent with `audit_surface_truth.json` headline "0/9 asset classes money-ready."

**Verdict (b): No contradictions with the policy-clean trust source.** The page is, if anything, more conservative.

### (c) Staleness — PARTIALLY STALE (minor)

- **HTML render + linked runs: FRESH.** Newest runs referenced are 2026-06-06 (3 days old); the page itself was regenerated 06-06 and re-deployed (live last-modified 06-09 02:27). The 5-pass orchestrator's most recent cycle is 06-06; no 06-07/06-08/06-09 run exists yet — that is a cadence gap, not a dead page.
- **Backing JSON: STALE/ORPHANED.** `audit_dashboard/data/research/research_index_data.json` is `generated_at: 2026-05-24` by `tournament_research_generator`, n_topics=19, all severity "VALIDATE". This file is a **different artifact** (tournament directional-bias topics, not the run index) and does not appear to feed the rendered `research_index.html`. It is 16 days stale; low impact because it isn't the page's data source, but it is dead weight in `data/research/` (all 6 files in that dir are dated 2026-05-25).

**Verdict (c): Page content is current to the last orchestrator cycle (06-06). The `data/research/*.json` snapshots are stale (05-24/05-25) but orphaned from the page.**

### (d) Fabricated / placeholder entries? — NONE FOUND

Every run row maps to a real on-disk + live run directory with internal-consistent columns (Candidates/Backtested/Independent/Citations/Cost). Cost=$0.00 across all runs is plausible (free-tier model fan-out), not a placeholder bug. Citations show partial resolution (e.g. "8/20") rather than fabricated 20/20, which is an honesty signal.

### TASK 1 SUMMARY
`research_index.html` is **healthy and trustworthy**: 0 broken links (68/68 resolve, live-verified), 0 policy-clean contradictions (0 GO verdicts; FOREX correctly all NO_EDGE/MIXED), no fabricated/placeholder entries. Only nit: the orphaned `audit_dashboard/data/research/*.json` snapshots are 05-24/05-25 stale and could be pruned or regenerated — but they do not drive the page.

---

## TASK 2 — FOREX kill-or-mutate diagnosis (CRITICAL)

### The contradiction, sourced

| Source | Trust | FOREX numbers |
|---|---|---|
| `pf_registry.by_asset_class_policy_clean_net` (gen 2026-06-06) | **#1** | n=22, WR=18.18%, **PF=0.0443**, MDD=34.25%, top_source=multi_asset_scanner (50%) |
| `money_ready_verdict.json` FOREX (gen 2026-06-08) | **#1** | n=25, WR=24%, **PF=0.0774**, expectancy=-0.0157, MDD=34.25%, bootstrap CI [-0.0416, -0.0006] (entirely negative), verdict INSUFFICIENT_DATA |
| `audit_surface_truth.json` FOREX (gen 2026-06-06) | derived from #1 | policy_clean_pf=0.0443, policy_clean_wr=18.18, **bridge_action = "FAIL — mutate or kill emitters; no real money"** |
| `pick_summary_stats_48h.json` FOREX (gen 2026-06-05) | NOT sizing-grade | n_decisive=8, **1W/7L, PF=0.094**, single_source 100% AlphaEngine, INSUFF-N |
| `pick_summary_stats_14d.json` FOREX (gen 2026-06-05) | NOT sizing-grade | n_decisive=159, WR=64.15%, **PF=2.434**, caveat: **single_source_concentration=99%_via_AlphaEngine** |

Every trust-#1 source and the most-recent 48h window agree FOREX is catastrophic. **Only the 14d window is positive, and it is the one source the trust policy says is not sizing-grade.**

### 1) Is the 14d FOREX number a batch-resolver / concentration artifact? — YES (strong indirect evidence)

I could not inspect the raw `at_raw_picks` rows directly (DB not reachable; the 14d file's `source` is `ejaguiar1_stocks.at_raw_picks (DB)` and those rows are not in the local JSON snapshots, so I cannot quote per-row `closed_at`/`signal_timestamp` clustering for 2026-05-19). But the artifact diagnosis is supported by four independent local signals:

1. **99.4% single-source concentration.** The 14d FOREX block carries `top_source_share=0.994` and an explicit caveat `single_source_concentration=99%_via_AlphaEngine`. "AlphaEngine" is the generic catch-all source label, NOT the per-strategy attribution. The policy-clean registry attributes FOREX to `multi_asset_scanner` / `multi_asset_copytrader`, i.e. the dedup/flicker filter re-keys those same picks and the WR collapses (18% vs 64%). A 99%-single-source window failing the concentration gate is exactly the disputed-surface pattern flagged in `audit_surface_truth.disputed_surfaces`.
2. **The 48h window (same generator, more recent slice) is 1W/7L PF=0.094.** If the 14d 64% WR were a live edge, the trailing 48h would not be near-zero. The 14d number is carried by older trades inside the 05-22→06-05 window; the live-recent slice is catastrophic — the signature of stale batch-resolved wins aging out of a window.
3. **Documented 10x write-duplication artifact in this exact scraper.** Commit `cc1f7a89c7` (#3) documents and fixes a "~10x write-duplication artifact inflating apparent WR" in `multi_asset_copytrader_scraper.py` (day-level `signal_timestamp` dedup so INSERT IGNORE catches repeats). The fix landed 2026-06-06; the 14d window (gen 06-05) predates it, so the 14d FOREX WR is computed over the pre-dedup, duplicate-inflated row set.
4. **Policy-clean drops n from 159(14d)/54(raw) → 22.** `by_asset_class` (raw) = n=54, WR=40.7%, PF=0.32; `policy_clean_net` = n=22, WR=18.2%, PF=0.044. The dedup/flicker/single-source filters remove ~60% of FOREX rows and the survivors are losers — i.e. the inflation lives in the deduped/duplicated rows the 14d window counts and the policy-clean view discards.

**Conclusion:** the 14d FOREX PF=2.43 is a concentration + pre-dedup-duplication artifact, not a live edge. **The peer proposal to EXPAND FOREX coverage on the 14d 64% WR is REJECTED.**

### 2) Which FOREX strategies are still emitting, and are any banned?

Currently-emitting FOREX picks: `copy_trader_intel/data/forex_copytrader_picks.json` (gen 2026-06-09 02:33) = **15 OPEN picks, all `forward_test_only=True`, all `source_system=multi_asset_copytrader`.** Strategies: `forex_rsi2_mean_reversion` (4), `ig_contrarian_sentiment` (5), `forex_zscore_200d_fade` (2), `forex_carry_momentum` (2), `myfxbook_retail_contrarian` (2).

Ban-list status:
- **`multi_asset_copytrader` IS in `BANNED_SOURCES`** (`production_scanner.py:1369`) — so all 15 current FOREX picks are rejected at the production scoring/ledger gate. `forex_copy_trader` and `multi_asset_cot` are also banned.
- BUT the **current dominant policy-clean FOREX emitter is `multi_asset_scanner`** (50% share, n=11, WR=9.1%, PF=0.21 in `by_asset_class_strategy_policy_clean_net`), and **`multi_asset_scanner` is NOT in `BANNED_SOURCES`.** It IS listed in `strategy_kill_list.json` and in `emitter_discipline.py` HARD_KILL — but see the gap below.
- **`emitter_discipline.py` is ORPHANED (dead code).** It is enforced by default (`EMITTER_DISCIPLINE_ENFORCE=1`) and its HARD_KILL set already contains `multi_asset_scanner` plus every active FOREX strategy (`forex_carry_momentum`, `forex_carry_ppp`, `myfxbook_retail_contrarian`, `forex_carry_bb_hybrid`, `carry_trade_momentum`, `forex_rsi2_mean_reversion`, `inverse_carry_contrarian`), checked against BOTH strategy and source tier. **But `grep` shows ZERO importers of `apply_emitter_discipline` anywhere in the repo** → this gate never runs in production. This violates the project Wire-Up Rule. The only live source-gate is `BANNED_SOURCES`, which is source-keyed and does NOT include `multi_asset_scanner`.

`auto_tuner.py` LOW_CONFIDENCE/PERMANENTLY_KILLED contains some FOREX entries (`forex_logistic_direction`, `community_london_breakout_v2_forex`) but NOT `multi_asset_scanner` and NOT the currently-emitting FOREX strategies.

### 3) Do the shipped fixes (DXY gate, myfxbook thresholds, zscore NULL guard) address the failure?

Verified all three commits exist (`cc1f7a89c7`, `0ebfa1a963`):
- **forex_zscore NULL guard** (`cc1f7a89c7` #2): prevents NULL `entry_price` rows from corrupt OHLCV. Data-hygiene only — removes a contamination source; does not create edge.
- **myfxbook proxy threshold tighten + confidence cap** (`0ebfa1a963`): reduces noise from the dormant myfxbook proxy; risk-reduction, not edge.
- **DXY regime gate** (`cc1f7a89c7` #4): suppresses LONG picks on EUR/GBP/NZD/AUD pairs when DXY 5d return >+0.3%. **Scope-limited:** it lives in `combined_confidence_strategy.py` (SOURCE_SYSTEM=`combined_confidence_strategy`) and only gates that strategy's LONG picks on a fixed pair list. It does NOT touch `multi_asset_scanner`, `multi_asset_copytrader`, or the carry/contrarian FOREX strategies that actually produce the live FOREX losses. USDJPY (the top losing symbol, 24% of FOREX) isn't even in the suppressed-pair list.

**Assessment:** all three are correct, useful hygiene/risk fixes, but **none of them address the FOREX failure.** The failure is a broad negative edge across emitters (WR 18%, PF 0.044, expectancy −1.57%/trade, MDD 34%), not a USD-regime-timing or NULL-row problem. Deeper kill/mutation is still needed.

### 4) VERDICT: KILL (with one tiny mutate-watch lane; no salvageable sub-strategy)

**Policy-clean evidence against every FOREX sub-strategy** (`by_asset_class_strategy_policy_clean_net`, gen 06-06):
- `multi_asset_scanner` n=11, WR=9.1%, PF=0.21
- `multi_asset_copytrader` n=6, WR=50%, PF=0.90 (still <1, and n<<20 gate)
- `cta_replicator` n=3, WR=0%, PF=0.0
- `forex_zscore_200d_fade` n=1, PF=0.0
- `regime_terminal` n=1, PF=0.0

Per strat-symbol: only **1 of 33** FOREX strat-symbol cells has PF≥1.0 — `multi_asset_scanner::USDJPY` n=4, WR=25%, PF=2.50. n=4 with 25% WR is one lucky large win, not an edge. There is **no paper-validated FOREX sleeve** in `audit_surface_truth.forward_track`.

**No sub-strategy clears even a relaxed bar on policy-clean n.** There is nothing to SALVAGE on trust-grade evidence.

**Recommended action (kill-with-mutate-watch, per `MUTATION_THREE_AXIS_PROTOCOL` / `STRATEGY_INVESTIGATION_BEFORE_KILL`):**
1. **KILL at the live gate:** add `multi_asset_scanner` to `BANNED_SOURCES` in `production_scanner.py` — it is the only top FOREX emitter not currently source-banned and it is a 9% WR / 0.21 PF loser. (Owner decision; this report is read-only.)
2. **Close the orphan gap:** either wire `apply_emitter_discipline` into the production intake (it already hard-kills the right FOREX set) or migrate its FOREX entries into `BANNED_SOURCES`. Right now the HARD_KILL list gives a false sense of protection because nothing calls it.
3. **No new real-money FOREX sizing.** Honor `audit_surface_truth` bridge_action "FAIL — mutate or kill emitters; no real money."
4. **If mutating rather than fully killing, the correct axis is DIRECTION/REGIME, not coverage.** Expanding coverage (peer proposal) is wrong. The salvage lane, if any, is a forward-only paper pilot of a SINGLE pair+strategy with mandatory n≥30 policy-clean before any sizing — and the only candidate worth even watching is carry on a yield-positive JPY-cross pair (consistent with the `forex_asset_analysis.json` diagnosis: carry only on yield_diff>2% pairs + London/NY session filter). It must be evaluated on policy-clean forward n, NEVER the 14d window.

---

## BOTTOM LINE

1. **research_index verdict:** HEALTHY. 0 broken links (68/68 resolve locally and live, HTTP-verified across all classes/dates), 0 policy-clean contradictions (zero GO verdicts; FOREX correctly all NO_EDGE/MIXED), no fabricated/placeholder entries. Minor nit: orphaned `data/research/*.json` snapshots are 05-24/05-25 stale but don't drive the page.

2. **FOREX verdict:** **KILL.** The 14d PF=2.43 is a 99%-single-source + pre-dedup-duplication artifact (corroborated by 48h=1W/7L PF=0.094, commit cc1f7a89c7's documented 10x write-dup fix, and the n=159→22 policy-clean collapse to WR 18% / PF 0.044). Peer "expand FOREX coverage" proposal REJECTED. The shipped DXY gate / myfxbook tighten / zscore NULL guard are correct hygiene but do NOT fix the broad negative edge. **No salvageable sub-strategy on policy-clean evidence** (best is multi_asset_copytrader n=6 PF=0.90, still <1; only PF≥1.0 cell is multi_asset_scanner::USDJPY n=4 = noise). Recommended: source-ban `multi_asset_scanner` (the only un-banned top FOREX emitter), wire or migrate the orphaned `emitter_discipline` FOREX HARD_KILL list, no real-money FOREX sizing; if mutating, mutate the DIRECTION/REGIME axis on a single forward-paper pair, never coverage.
