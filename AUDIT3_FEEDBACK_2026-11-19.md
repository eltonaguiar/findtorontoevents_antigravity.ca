# Review — audit3 ("Quant Kill Tribunal"), /audit, FINANCE_DB_SCHEMA_SPEC
**v3 · 2026-11-19 · cross-checked against live payloads, the merged surface-review (PR #891, c6bcc9a), MONEY_MAKER audits, and the protocol docs**

Changelog: v1 original → v2 (post-#891 verification: scope problem, class contradictions, measured slippage, Pod reorder to EQUITY; spec confirmed on main) → v3 (this revision): adds (a) review of STRATEGY_DISCOVERY_PROTOCOL.md / TESTING_PROTOCOL.MD / EAGLE-2026-05-27 plan, (b) MONEY_MAKER audit arc May→June→Nov, (c) granular sweep of /audit — Portfolios tab, US Equity factor screens, Smart-Picks vs MONEY-READY presets — with a prioritized worth-moving-on list, (d) H-119 tile-vintage conflict found in live HTML, (e) merged v3 priority list (P0/P1/P2) replacing the old §5 order.*

Changelog v1 → v2 (verification status):

- Spec is on main (PR #890, merged earlier) — my v1 links (and the "on a branch / paste-into-web-AI" framing for the spec) were stale; the PR #891 doc is the surface review. Both confirmed via GitHub API + raw fetch.
- v1 underestimated audit3's biggest problem: it judges 21.4% of the closed book (3,500 of 16,330 rows; window 2026-02-21 → today), and the other 78.6% — including 7,502 integrity-excluded (46%) and 9,100 auto-expired — is analysed on neither page. Verified in live payload.
- v1 said "killing crypto LONGs may be a spurious recent-window artifact." The walk-forward panel weakens that excuse: CRYPTO OOS Sharpe −2.077 over 32 folds (46.2% WR EQUITY +0.608, 33 folds; ETF +0.212, 53 folds). The kills were directionally right.
- v1's measured-slippage critique stands but is softened in one direction: audit3's flat constants sit above measured, so its kills are conservative (no false kills from cost modeling). The fix is to adopt measured per-strategy slippage, not to distrust the kills.
- v1 recommended a crypto ensemble-grade pod first. Reordered: the EQUITY pod is now first-choice (only positive OOS Sharpe with real folds).
- New: smart-picks tile contradiction, dead "tier2 proven" panel, kill-list reconciliation (1 shared name), gate pressure stats, EQUITY exit-geometry decomposition, payload-vintage mixing — all verified in the 26MB payload today.

0. What each artifact is
| Artifact | Status (verified) | Role |
|---|---|---|
| /audit | live, payload generated 04:04Z, 1.44MB page, 26MB dashboard_data.json | wide, per-class + per-system view; contradictory tiles |
| audit3 ("Quant Kill Tribunal") | live, ledger generated 04:54Z, scores last-246-day window (2026-02-21→) | narrow, statistically honest; instance-scoped |
| docs/AUDIT_SURFACE_REVIEW_2026-11-19.md | merged to main via PR #891 (merge commit c6bcc9a, doc-only) | other reviewer's surface audit — verified below |
| docs/FINANCE_DB_SCHEMA_SPEC.md | on main via PR #890 (not a branch) | DB inventory; hostile to share un-redacted; useful for the canonical-view fix |
| MASTER_AUDIT.md, edge-search, hypothesis registry (finpredict-v2) | on main | your own honest negative results |

1. audit3 — strengths, scope problem, gate bugs, wiring
1.1 Strengths (keep)
Pre-declared method; Wilson CIs; bootstrap net-expectancy CI (2,000 seeded resamples) after per-class slippage; BH-FDR; split-half; concentration caps; doctrine "innocent until proven guilty"; kill rule = net-CI<0 and BH harm q ≤ 0.10. Genuinely better statistics than the main page.

1.2 Scope problem (the headline from #891 — verified)
| Population | Rows |
|---|---|
| closed picks in existence | 16,330 |
| valid (headline unique) | 7,901 (mirror dups removed 97) |
| integrity-excluded | 7,502 (46%) |
| auto-expired excluded | 9,100 |
| resolved | 8,731 |
| rows audit3 scores | 3,500 (21.4%), 246-day window |
| tested cells / proven / kills | 45 / 0 / 11 kills, 34 WEAK, 126 INSUFFICIENT |

Excluded detail (forward-validation audit, rows_scanned=25,430): 3,467 expired zero-PnL rows, 44 stale exits beyond planned stop, 23 clamped losses, 3 missing closed_at. A zero-PnL expiry is not neutral — dropping those rows changes the win rate. Action A1 (from #891): publish an "excluded cohorts" panel + header statement "judging X of Y picks". Even if the exclusion is defensible (integrity rows are untrustworthy), it must be quantified and displayed, not silent.

Additional internal inconsistency found v2: the tribunal scores the 3,500-window but dsr provenance says 59 cells scored; summary says 45 tested. One canonical trial counter must feed DSR/BH/Bonferroni across audit3, money_ready_verdict.py and the emitter.

1.3 The two surfaces contradict each other (verified against both)
| Class | /audit (money_ready_verdict) | audit3 | Verdict |
|---|---|---|---|
| ETF | n=52, WR 1.9%, PF 0.02 (also bridge tile n=47 PF 0.021) | n=584, WR 43.1%, PF 0.98 | unreconcilable — no ETF conclusion loadable |
| EQUITY | n=256, WR 60.2%, PF 0.97 | n=761, WR 45.9%, PF 1.05 | n differs 3×, WR 14pp |
| COMMODITY | n=232, PF 1.04 | n=55, WR 14.5%, PF 0.12 | opposite signs |
| CRYPTO | n=3,724, PF 0.917 | n=1,851, PF 0.72 | PF differs 0.20 |
| FOREX | n=623, PF 0.653 | n=211, PF 0.69 | close |

Action A2 (from #891): one canonical resolved_closed_picks_net view — class slippage applied, exclusions flagged — queried by both surfaces. The DB schema spec already defines the columns this needs; this is the single highest-leverage engineering fix on the table.

1.4 Gate bugs found v1 (still open)
- G1 (binomial WR > 50%) is mis-specified: 50% break-even only holds for avg-win = avg-loss payoffs. It can never certify a trend/premia cell and it misjudges your own EQUITY class in reverse. Make bootstrap net-expectancy CI > 0 (G2) the primary edge gate; WR is a descriptor.
- BH pooled across all 171 cells mixes confirmatory and discovery. Split namespaces; promotion gates only inside a small pre-registered confirmatory set.
- Selection bias on the CI>0 segments: grade A/score≥60 CRYPTO (n=33, net +1.47, CI [+0.48, +2.45]) and elite_grade B (n=72, +1.41, [+0.62, +2.19]) are overlapping sets from a 65-segment screen — nominal 95% CIs are optimistic post-selection; print selection-adjusted CIs, dedupe A⊂B, require SL-wins-ties labels before nomination.
- Split-half only → add rolling monthly cohort check.
- Ledger provenance embeds /tmp/audit3/dashboard_data.json — embed commit SHA + input hashes.
- Tribunal not wired to the emitter — PR #6 allowlist historically had 0 call sites. Tribunal KILL must auto-denylist the scanner; PROVEN_T2 needs a forward-clock promotion path (30/60/90 d, small size cap) or nothing can ever graduate.

1.5 Measured slippage replaces the flat constants (from #891, verified exactly)
From dashboard_data.json.slippage_validation (201 strategies flagged, 78 flagged / 36 critical):

| Class | n | measured | slippage as % of per-trade PnL | audit3 flat const |
|---|---|---|---|---|
| CRYPTO | 11,341 | 0.0997% | 37.2% | 0.15% (conservative) |
| ETF | 602 | 0.0500% | 234.1% | 0.08% (conservative) |
| FUTURES | 19 | 0.1500% | 75.4% | 0.10% (optimistic) |
| BOND | 35 | 0.0500% | 26.4% | 0.08% (conservative) |
| COMMODITY | 135 | 0.1500% | 13.5% | 0.12% (optimistic) |
| EQUITY | 1,696 | 0.0500% | 13.4% | 0.10% (conservative) |
| FOREX | 692 | 0.0200% | 8.9% | 0.05% (conservative) |

Institutional facts: ETF edge is 234% consumed by costs — only monthly-cadence rotation could ever survive; FUTURES/COMMODITY flat constants are below measured — audit3's futures verdicts are not conservative, adjust them; luxalgo_confluence book-wide measured slippage 0.10% = 2,175.8% of per-trade PnL (avg PnL ≈ 0.005%) — the +0.67%/trade on the SHORT cell (which survived audit3's net gate after the 0.15% flat crypto slippage) is favorable-regime selection and must clear 2×-measured-slippage before any nomination. Action A3: per-strategy measured slippage where available, class constant fallback.

2. /audit main page — verified defects
- Walk-forward OOS table (on the page, 2026-11-18 21:47 EST): EQUITY 33 folds WR 46.2% Sharpe +0.608; ETF 53 folds +0.212; CRYPTO 32 folds WR 38.4% −2.077 (worst-fold WR 18%, consistency 25%); FOREX 3 folds −4.382; BOND 30 folds n/a (degenerate); COMMODITY 3 folds n/a. This is the single most decision-relevant table on the page and it is on neither headline. EQUITY is where premia live; CRYPTO — 60% of volume — is broken out-of-sample.
- Smart-picks tile contradiction (verified both sides): smart_picks_feed.total_scored = 0, picks: [] and quality_stats.smart_picks_count = 0, versus smart_picks_snapshot_summary: 45 resolved batches, 95 picks, 68.4% WR (all 95 in SWING), metric labeled "not execution-accurate — price at batch resolution, not fills". Two "smart picks" definitions on one page; snapshot ≠ feed. Action A5: one definition, one number, or label clearly. (Page also shows the snapshot tile staler than the payload — 1,544 trades / 45.5% vs payload 2,098 trades / 45.0%.)
- tier2_proven_strategies is dead weight under a "proven" label (verified): three cards — signal_validation dead (WR 4.9%, PF 0.08, MDD 127.3%, n=102), mega_mutation Tier 3 paper-floor (58.1%, PF 1.95, n=105; audit3 also has it at WR 73.7% n=19 → INSUFFICIENT_N), rl_agent empty (n=0). Page header: "0/3 clear strict Tier-2". Action A6: retire the panel until a card is alive.
- EQUITY's 60.2% WR at PF 0.97 is exit geometry, not skill: summary avg_win 3.95% vs avg_loss 3.08% → break-even WR ≈ 43.8%; 60% WR harvests small wins, eats tail losses. Audit3's EQUITY (45.9% WR, PF 1.05) is the same book measured differently — near break-even either way. Payoff-asymmetry tile needed; WR headline must die.
- Gate pressure (verified in payload): quality_stats: 134 before gates → 15 active (88.8% filtered; signal_to_trade_pct 33.9%; PCG5 shadow 119/134 REJECT). 89 names demoted from "PROVEN" this run (proven_badge_audit.demoted_from_proven_this_run). Strategy IC analysis: 43 positive IC / 30 negative of 116 (4 Bonferroni-significant).
- Kill-switch lift is a vanity metric as published: WR lift +6.10pp but PF lift −0.022 — removing 42 "losers" didn't improve profit factor. Report forward-PnL lift only.
- Kill lists don't reconcile (verified by diff): kill_switch 42/56 evaluated vs audit3 11 — they share exactly one name (futures_momentum). Either reconcile vocabularies or label each list with its pipeline ("cell-gate verdicts" vs "strategy-register verdicts").
- Three vintages on one page: analyst leaderboard (2026-03-26), walkforward (11-18 21:47), money_ready_verdict (04:03), payload (04:04), smart snapshot (Nov 18 22:19 EST) — all presented as one current view. Stamp vintage inline per tile.
- Verified-alpha cohort (verified): 1 active pick (regime_crash AMD SHORT — a strategy on the kill list), realized 2,098 trades @ 45.0% WR, expectancy +0.13%; audited n=1, avg sample 2.0. It is simultaneously the only positive-expectancy cohort on the page and the least-audited. Do not size it.
- "Renaissance T1/T2/T3" branding and tournament "4285/7099 mispriced" language — remove or relegate; they invite sizing mistakes on non-money-ready cohorts.
- Selection alpha (the metric that separates skill from beta) is not in the payload. #891's A4 cites CRYPTO LONG −0.442%/pick and ETF −0.272%/pick vs holding; those numbers are not present in dashboard_data.json — presumably from alpha_engine/benchmark_closed_ledger.py (the timing-null companion audit3's own conventions point to). Verify the report path before using them as headline; then adopt A4 anyway — it's the only beta-separation metric available and both pages need it.
- Theory tracker H-020…H-025 KILLs (COT small-spec, PEAD, fear/greed, G10 carry @ n=950, ETF breadth) — these died as TP/SL pick harnesses, not as vol-targeted baskets. Do not generalize "carry/PEAD are dead"; a different expression is a different hypothesis needing its own pre-registration — but it must also beat the sleeve benchmark, else it's academic trivia.
- FOREX: PF 0.65, 3 walk-forward folds, price table reportedly ends 2026-02-09 — retire from the money path until backfilled (last point unverified from sandbox).

3. The actionable shortlist (revised v2)
The only structure the verified numbers support is the barbell: low-cost beta core + one EQUITY premia sleeve. Nothing speculative until selection alpha is positive in two regimes.

Pod 1 (first) — EQUITY/ETF premia, implemented literature-correctly
- Candidates: PEAD drift (SUE-ranked, large-caps, 60-day hold — your H-020 harness failed as TP/SL; test the basket version) and 12–1 momentum / trend with symmetric vol-scaled exits, monthly rebalance, vol-targeted to ~10–12% portfolio vol.
- Why: only class with positive OOS Sharpe (+0.61/33 folds) and near-break-even PF; audit3 shows pooled equity-scout breakout cells (donchian/rs-breakout/vol-contraction/adx-trend ≈ 250 trades) at net +0.4–0.6%/trade — same family, same direction.
- Gates (confirmatory namespace): n≥100 forward trades, net CI > 0 at 2× measured slippage, IR ≥ 0.5 vs SPY at matched exposure, 90-day forward clock, kill if CI-LB ≤ 0 at day 30/60.

Pod 2 (second) — luxalgo_confluence SHORT, re-expressed
- Verified: n=476, WR 54.4%, net +0.67% (post-0.15% flat crypto slippage), CI [+0.35, +0.96], split-half stable & improving, DSR 0.977, p=0.030, q=0.338, single-source 97.7%, book-wide measured slippage 2,176% of per-trade PnL, LONG mirror n=754 KILL (PF 0.80). Treat as an observation, not an edge: check BTC-beta of the pod (is it short-beta?), require a second source (concentration cap 0.9), re-express exits as symmetric vol/time stops, and only nominate after clearing 2× measured slippage. Lowest priority of the two pods; kill on day-30 forward CI-LB ≤ 0.

Pod C (exploratory, 30-day fuse) — breakout family vs timing null
- Run the pooled equity/ETF breakout family through benchmark_closed_ledger.py's random-entry null using daily_prices; promote or kill within 30 days. Do not widen scope.

Explicitly starved (all verified kills/harm)
- CRYPTO directional anything (OOS −2.08, selection alpha negative, class KILL, every major-symbol LONG killed), FOREX (retire until data backfill), commodity picks (class KILL, n=55 WR 14.5%), MEME (10% WR), prediction_market_consensus (on kill list; PM taker fee math stands), copytrader family (n=81 net −1.34% KILL), luxalgo_confluence LONG, futures_momentum (the one name both kill lists share), mega_mutation (observe only — INSUFFICIENT_N; its "Tier-2 PROVEN" card is fiction).

Portfolio frame
- 70–85% beta core (total-market index ETFs + bonds, ≤0.20% ER, TFSA/RRSP sheltering) + ≤15–25% premia satellite (Pod 1 sleeve; managed-futures/commodity trend as complement if you don't run it yourself) + ≤5% pods, vol-targeted, −15%/−25% drawdown circuit-breakers. Broker wrapper choice ≥ fund selection; never let "satellite" leak into core.

4. FINANCE_DB_SCHEMA_SPEC.md (now on main via #890)
Still valid (v1) and now more urgent, because the fix for the ETF contradiction (A2) runs through it:

- Redact before any external paste: §1 host mysql.50webs.com, ejaguiar1_<db> user map, §10 credential path (tools/db_env.py + ~/dbpasses.txt). The doc proposes web-AI sharing — treat that as in_scope/unchecked; split into public spec + private infra appendix.
- Declare systems of record: trading_picks vs at_pick_outcomes vs at_signal_outcomes overlap; pick one canonical (suggest at_signal_outcomes — carries intrabar fields) + derived views; kill ad-hoc _is_valid_resolved_pick sprinkling. This is A2's implementation.
- Add the forward-ledger contract (forward_observations with hypothesis_id FK, fees, funding, resolver_version, intrabar_first_touch, matched benchmark leg). Without it audit3 can never mint PROVEN from live data.
- Pre-aggregate bt_backtest_trades (~32.7M) to (strategy, symbol, class, month); drop/repurpose the duplicate stocks mirror after parity check; partition ~76M at_local_picks.
- CI freshness assertions per table (e.g., portfolio_snapshots stale since March would fail loud); decision-log the 110+20+9 empty tables and dormant clusters; quarterly restore-test for the 414-table backups DB; row-count parity bt_backtest_trades vs mirror.
- Scan discord_* columns (consensus_tracked) for tokens/webhooks before any distribution; fix dead refs (RECOVERY_PROTOCOL.MD).
- Note the spec's own known-gaps list is honest (bt_backtest_trades unscanned; backtests are evidence not verdicts; cost_basis unknown). Keep the audit3_evidence doctrine — 2,727 records / 66,764 trades stay evidence, never verdicts.
- Merge hygiene done: spec on main via #890 ✓; PR #891 doc-only ✓. Add the spec regeneration to CI with redaction step instead of monthly manual edits.

5. Merge the two reviews into one work order (A1–A7, prioritized)
| # | Action | Source | Effort |
|---|---|---|---|
| A2 | One resolved_closed_picks_net canonical view (schema spec makes it possible); both pages query it | #891 + v1 | M |
| A1 | Excluded-cohort panel on audit3; "judging 21.4% of the book" stated in header | #891 + verified | S |
| A4 | Selection alpha (vs buy-and-hold, matched exposure) as the per-class headline; demote raw PF; do not ship −0.442/−0.272 until traced to benchmark_closed_ledger.py output | #891 (A4) | M |
| A3 | Measured per-strategy slippage in audit3; fix FUTURES/COMMODITY constants (they're below measured) | #891 + verified | S |
| A7 | Port walk-forward OOS + kill reconciliation into audit3 (one vocabulary, one pipeline label) | #891 + verified | M |
| A5/A6 | One smart-picks definition (or two clearly labelled); retire dead tier2_proven_strategies panel; stamp tile vintages | #891 + verified | XS–S |
| — | audit3 gate fix: expectancy-CI as G1; confirmatory/discovery split; SL-wins-ties pre-check; wire KILL→denylist; /tmp provenance → SHAs | v1 | S |
| — | EQUITY premia pod pre-registered; luxalgo SHORT watch-pod; breakout family timing-null (30 days) | v1 + corrected | M |
| — | Beta core + ≤5–25% satellite framed in artifacts; retire FOREX/MEME/PM-taker/copytrader from money path | v1 | XS |

6. Verification appendix (what I checked today)
Verified against live payloads/pages (2026-11-19 ~06:30Z): commit c6bcc9a = merge of PR #891 ✓; spec on main (HTTP 200) ✓; walk-forward table values ✓ (EQUITY 0.608/33 folds, CRYPTO −2.077/32, ETF 0.212/53, FOREX −4.382/3, BOND/COMMODITY n/a) ✓; quality_stats.total_active_before_gates=134 → active_after_gates=15 ✓; quality_stats.smart_picks_count=0 ✓ vs snapshot 95 picks/68.4%/45 batches ✓; pcg5_shadow_summary.gate_results = 134 rows, REJECT 119 / TAKE-ish 15 ✓; proven_badge_audit.demoted_from_proven_this_run=89 ✓; slippage_validation.asset_class_stats (incl. ETF 234.05%, CRYPTO 37.24%, luxalgo_confluence 2,175.8% of PnL, totals 201/78/36) ✓; summary avg_win 3.95 / avg_loss 3.08 / expectancy −0.16 / PF 0.91 ✓; 16,330 closed / 7,901 valid / 7,502 integrity-excluded / 9,100 auto-expired / 8,731 resolved / 25,430 rows scanned w/ 3,467 zero-PnL + 44 beyond-stop ✓; verified_alpha 1 active (regime_crash AMD SHORT), realized 2,098 @ 45.0%, expectancy +0.13%, audited n=1 sample 2.0 ✓; kill lists intersect in exactly futures_momentum ✓ (diffed both lists); tier2 panel contents (dead/paper/empty, "0/3 clear Tier-2") ✓; audit3 ledger internals (0 PROVEN, 11 KILLs, CI>0 segments, luxalgo SHORT n=476 CI [+0.35,+0.96], dsr 0.977) ✓.
Not verifiable from the sandbox (flagged, not falsified): FOREX price-table end date 2026-02-09; selection-alpha figures (−0.442 / −0.272) — not in dashboard_data.json; presumably the benchmark_closed_ledger.py timing-null report; cross-check that report path before adopting the numbers. audit3's claim cadence (2026-02-21 window) is as published by audit3.

7. Bottom line
Nothing in either page challenges the structure of the plan in v1 — it sharpens it: agree the denominator (A2), publish what's excluded (A1), make selection alpha vs buy-and-hold the headline (A4), spend the next quarter on EQUITY (the only positive OOS Sharpe) and on fixing the two surfaces to tell the same truth, and keep everything starved until forward clock proves otherwise. The win available to this project is a small, honest, compounding satellite on top of a boring beta core — and an audit pipeline investors can actually read.

Not personalized investment advice.

---

Part 3 (v3 addendum) — Protocol docs, MONEY_MAKER arc, and a granular /audit sweep

8. The protocol docs — what they settle
8.1 docs/STRATEGY_DISCOVERY_PROTOCOL.md (2026-04-19, decent skeleton)
Good: novelty requirement |ρ| < 0.2 vs library on aligned daily returns; round-trip costs before promotion; correlation-prune CI gate; purged K-fold / hold-out; spec sheets. Gaps that matter for your situation:

- It never demands the one thing that decides everything: why should this edge exist, and who is losing money to it? "Distinct template" ≠ "economically motivated". Decorrelated AI-generated noise is still noise — your library is proof (700+ templates, 0 PROVED).
- The cost table is indicative (5–20 bps equities) and self-declared stale; your own page now ships measured per-strategy slippage — reconcile against slippage_validation quarterly, as the doc itself instructs.
- Novelty by decorrelation is never actually enforced against the library — correlation_prune_strategies.py exists but /audit shows no pruned-by-ρ cohort counts. Run it on everything emitted in the last 90 days; expect a graveyard.
- Verdict: keep the skeleton, prepend an economics pre-filter (behavioral/structural reason + counterparty losing money + capacity) before any backtest is allowed to run.

8.2 TESTING_PROTOCOL.MD (Section 0, 2026-05-31 canonical — read this part, it is good)
Load-bearing strengths to keep forever: five conjunctive hard gates (paper-pilot graduation n≥500; Wilson LB vs break-even; bootstrap-PF CI-LB > 1.0; Bonferroni p<0.0071; top-symbol concentration ≤0.60 checked BEFORE DSR/SPA — the error that shipped two false Tier-1s on 2026-05-17), the six n-floor decoder (every claim must name its surface/floor — kills the most common argument-by-misquoted-n in this repo), TIME_EXIT must be in pnl_pct, resolver-intrabar as upstream blocker.
Dangerous sections to quarantine:

- §6 "Scarcity analysis" (<25 trades = noise) and §7 "Rehabilitation-First Pipeline" (7-stage: cross-symbol → cross-class → inverse → mutation grid → regime filter → crossover → "graveyard only as last resort"). This is a variant-generation machine: failing parents birth dozens of "new" children; the best-looking child gets promoted. That is multiple-testing wearing a remediation costume, and it is exactly the mechanism that produced the June "Tier 1" slate. Every rehab variant must inherit the parent's cumulative trial count in the DSR/Bonferroni accounting, or the whole ledger silently resets its p-values.
- The file itself catalogs the standing contradictions you must never re-litigate: DSR alpha 0.1 vs Bonferroni 0.007 (canonical 0.007), PBO 0.05 vs 0.55 (canonical 0.05), bootstrap 1000/seed 17 (not 5000), T3 display-only vs charter PF 1.2 (charter wins), tournament T3 1.3 drifted (charter wins).
- Landmine confirmations worth citing: cloudflare-hosted agents cite deprecated views (always feed JSON verbatim); "Trust=7 IS a real edge (85.9% WR n=99)" — a local edge too thin to trade, and a warning that single-bucket inversions are usually noise; agent code-diff fabrication ~9% trustworthy (1/11); caveat #18: resolver intrabar replay is THE upstream blocker.

8.3 EAGLE_2026-05-27_Grok43_EMERGENCY_EXECUTION_PLAN.md — honest diagnosis, dated cures
Right about root cause: load-bearing integrity failures (signal_outcomes 82d stale; 38.97% pnl mismatch; 2,531 WON-with-pnl<0; ~56,559 ghost rows; trust_score NULL 99.99%; inverted ml_score calibration; tautological "100% WR" buckets). Two structural problems with it:

- The cure is still more machinery producing more candidates (gates, build-out phases), not a smaller, pre-registered hypothesis space. Phase 3's contemporaneous "Tier 1" calls have since been disproven one by one (stocks_rsi2 PF 4.76 → #96 dispute → 33.9% WR; smart_money_accumulation → 61.6% single-source dup dispute; luxalgo_confluence → split LONG-KILL/SHORT-WEAK).
- The marquee "largest sample, most trustworthy" Tier-1, crypto_liquidity_wick_reversal_v1 (June: "n=4,904, WR 58.1%, PF 1.50"), is backtest size. The realized forward cohort in today's payload is n=43, WR 58.1% but avg +0.15%/trade ≈ 15 bps — below the ~20 bps round-trip crypto cost → expectancy ≈ 0 post-cost. The plan never separated backtest n from realized n; that is the single most expensive confusion in this repo.
- Still useful: its Phase 0 instincts (freeze labels, quarantine ghost rows, disable FOREX, pause CT=F COT, VIX gate for EQUITY) matched what survived; and its ML-leakage masking caveat (money-maker-readyv2, Nov-14) stands: masking ≠ forward evaluation.

9. The MONEY_MAKER* arc — a repeating novel written three times
May 2026 (ready_yyyymmdd): list of "Tier-1"s gated by n≥30/PF>1.5 → June: several downgraded by own peer reviews (June edition shipped with a data-correction notice: "TWO classes — CRYPTO and EQUITY — have proven edges"; stocks_rsi2 PF 4.76 flagged "likely overfit"). Nov: 0/23 hypotheses PROVED; sizing_allowed=false everywhere; promotion gates OFF by default (MONEY_READY_FDR_GATE=0, MONEY_READY_SINGLE_SOURCE_GATE=0); cost gate has fail-open paths (per_class_cost_gate.py:29,152-179); after-cost stamping errors suppressed (dashboard_generator.py:7772-7789); concentration-checked-after-DSR historical leak; every June Tier-1 has since died or split.

Pattern, one sentence: small-sample PF>2 "Tier 1" → discovered to be overfit / single-source / label-corruption / backtest-only. The fix is not another audit; it is (i) gates ON by default, (ii) n measured in realized trades, (iii) promotion only through the audit3/forward-clock path.
JUN claim "CRYPTO and EQUITY proven" — Nov data: CRYPTO walk-forward −2.08 (32 folds), selection alpha negative, class KILL. EQUITY was the only part that survived.

10. /audit, button by button / tab by tab — anything actually worth moving on?
10.1 "💰 MONEY READY 👑" and "🧠 Smart Picks" — treat as empty, always

- The 👑 button is a filter preset (per-asset floors), not an endorsement; 0/9 classes MONEY_READY ⇒ every 👑 row is sandbox. The page itself disclaims point-estimates pending risk-adjusted metrics.
- Smart Picks feed today = 0 picks (regime NEUTRAL, F&G=10; ~22 scored, 8 banned / 10 non-crypto probation / 4 stale — everything filtered). The green "68.4% (95 picks)" tile is the snapshot metric — batch-resolution pricing, not fills — a second, different "smart picks" (and stale: embedded 2026-11-18 22:19 EST vs payload 04:04Z). One definition, one number, or neither tile ships.
- High Conviction preset: forward-validated floors, currently ~0 qualifiers; fine as machinery, useless as signal today.

10.2 Portfolios tab — retire or re-register; nothing there is alpha
23 payload portfolios, all paper scaffolding, realized: medium_conviction +1.96% (n=1), correlation +1.7% (n=4), high_conviction +0.25% (n=3), leap +1.26% (n=1); speculative −8.71% (n=13), derivatives −9.45% (n=13), verified −2.7% (n=5, 0% WR), technical −0.14% (n=11); 12 kimi_*-live algo portfolios never traded; DB portfolio_snapshots frozen since 2026-03-10. Verdict: zero promotable. Decide each (retire vs re-register with ONE pre-registered honest methodology); do not let the tab imply a track record.

10.3 "📈 US Equity Picks" tab — untested factor screens, the right direction, zero evidence
Live feeds: magic_formula_x_piotroski_x_acquirers (22 active; SOURCE "ueps"; concentration_summary top strategy 7.51% share; no audited resolved record), Quality Compounders (8 resolved, 50% WR, +18.62 total, avg +2.33% — tiny n, mildly positive), Dividend Aristocrats (no resolved data), stocksunify2* (6–7 active, 0 resolved), top_gainers_momentum (EXPIRED zombie rows; its sibling top_gainer_predictor: resolved 0 → dead), etf_cross_sectional_momentum / tsmom_volscaled / regime_crash / regime_terminal / leveraged_etf_decay (the last = LABD SHORT "leveraged decay" thesis in curated actives: 0 resolved — legit academic idea, currently just a story).
These are factor priors wearing a UI — the correct habitat for the one OOS-positive class (EQUITY +0.61, 33 folds), but still zero audited forward record. The move is not to trade them; it is to pre-register ONE factor pod (quality-value composite, e.g., magic-formula/Piotroski-lite or quality-minus-junk tilt, US large-caps, monthly cadence, vol-scaled) and let the forward clock decide. If you want the leveraged-decay short in the same experiment, it is a competing implementation of the same pod — pick one.

10.4 H-119 crypto_rsi5070_us lead — real but permanently below the bar, and the page embeds two vintages

- Embedded/static June tile: net PF 1.36 @16bp, CI-LB 0.95, n = 108, IS/OOS 1.44/1.30, top-sym RENDERUSDT 5.6%, refs reports/CRYPTO_RSI5070_US_LEAD_CANDIDATE_2026-06-13.md, "re-evaluate at n≥150 (~2026-06-25)".
- Live Nov tile (today): net PF 1.12, CI-LB 0.92, n = 431 (+gate met), IS/OOS 1.08/1.16, top-sym JUPUSDT 5.1% — same hypothesis, worse metrics, more samples, still below the CI-LB>1.15 bar. FOURTH vintage conflict on the page.
- Action: keep shadow-only; reconcile the two tiles; if CI-LB is still <1.15 at the next audit, retire H-119 cleanly instead of nominally tracking it forever. Note this is the only instrumented forward-shadow candidate the project has — that scarcity is the finding.

10.5 EQUITY/ETF recent filtered panel — encouraging, not actionable
EQUITY: 66 active / 15 closed, 53.3% WR, PF 1.81, +10.0, expectancy +0.67. ETF: 16/15, 40% WR, PF 2.26, +16.1, avg win 4.81 vs loss 1.42. FUTURES: 4 closed, PF 2.02 (meaningless n). Consistent with walk-forward (EQ +0.61/33 folds, ETF +0.21/53) and audit3 (EQ PF 1.05/net +0.12% WEAK; ETF n=584 PF 0.98). But: ETF measured slippage = 234% of per-trade PnL ⇒ ETF only survives monthly cadence; June audit flagged ETF Layer-A "PF 2.93/n=23" vs intrabar 0 TPs in 16 — cost/label artifact until monthly data says otherwise. EQUITY is the only class with statistical right-to-play; ETF is corroboration, not a pod.

10.6 The backtest_vs_forward "SURVIVOR" list — large samples, zero forward truth, one family worth exactly one pod
connors_rsi2 (bt 918tr WR 68.7% Sh 1.75), connors_r3 (820tr, 71.5%, 1.85), three_day_low (1155tr, bt_pf 1.22, OOS WR 63.9%), macd_divergence (499tr, 68.1%), keltner_mean_reversion (112tr, 64.3%, 1.78), bollinger_mean_reversion (359tr, 61.3%), williams_r_oversold (497tr, 60.0%), double_seven (905tr, bt_pf 1.16, OOS WR 67.1%) — every one shows fwd_trades = 0; connors_rsi2 realized forward: 8 trades, WR 12.5% (−18.35). These are the only backtests with real breadth and published analogues (Connors). They justify one pre-registered forward paper pod (SPY/QQQ RSI-2 or three_day_low, monthly/weekly cadence, cost-aware) — which also serves as the honest post-mortem of H10's ghost — and nothing more.

10.7 Verified-Alpha cohort — real money plumbing, unsizable
2,098 realized, 45.0% WR, expectancy +0.13%, 1 active (regime_crash AMD SHORT — a killed strategy), audited n=1, avg sample 2.0. Use it as the calibration source for measured-slippage models (it's the one execution-priced cohort). Do not size.

10.8 Adopt immediately (kill/high-confidence negative findings, verified)
luxalgo_confluence LONG (KILL, n=754), futures_momentum (the one name in both kill lists; KILL incl. COMMODITY-SHORT 0% WR), london-breakout LONG (KILL), extreme_fear / crypto-momentum-scout / crypto-bb-squeeze-scout / crypto_signal_engine / rsi-divergence-scalp-scout / momentum_breakout / cci-crypto-reversal (all CRYPTO LONGs, KILL), FOREX (retire until price backfill; 3 folds, table ended 2026-02-09), COMMODITY class (KILL, n=55, WR 14.5%), copytrader family (KILL, n=81, net −1.34), PredictionMarket taker anything (KILL list; fee math), mega_mutation (Tier-3 paper-floor only; 19 resolved WR 73.7% — observe, never size), tier2-proven deck (dead/paper/empty cards).

11. v3 master priority list (P0 → P2)
P0 — stop the fiction (days, do all):

- A2 canonical resolved_closed_picks_net view; both pages query it (kills ETF 1.9%↔43.1% and the CRYPTO/EQ/COMMODITY divergences at the root).
- A1 excluded-cohort panel on audit3 (counts/reasons; "judging 21.4% of the book" stated in the header).
- A4 selection alpha (vs buy-and-hold, matched exposure) as per-class headline; demote raw PF; trace the −0.442/−0.272 figures to benchmark_closed_ledger.py output before publishing.
- A5 single smart-picks definition; A6 retire tier2 panel; A6b fix kill-switch card (PF lift −0.022 ≠ "POSITIVE"); A4b kill "Renaissance T1/T2/T3" labels and Prime-Picks branding; A5b stamp vintage on every tile.
- Promotion gates ON by default (FDR + single-source), close cost-gate fail-open paths, un-suppress after-cost stamping errors; quarantine TESTING_PROTOCOL §6–8 (scarcity/rehab/super-strategy mutation machinery) under cumulative trial accounting.
- Reconcile H-119 tiles (or retire it); reconcile the two kill lists into one labeled vocabulary; fix the H-119 "re-run at n≥150" stale note (gate passed; CI-LB still fails).
- audit3 gate fix: expectancy-CI primary (G2 not WR binomial G1); confirmatory/discovery namespaces; SL-wins-ties pre-nomination check; wire KILL→emitter denylist (else tribunal = ceremony); provenance SHA not /tmp.

P1 — two pods maximum (weeks):
- 8. Pod 1 — EQUITY premia sleeve: one pre-registered implementation of "quality-momentum" (12–1 momentum + quality tilt) OR PEAD basket (SUE-ranked, large caps, 60-day hold), monthly cadence, vol-targeted ~10–12%, SPY-matched-exposure benchmark leg, net CI>0 at 2× measured slippage (EQ 5 bps), IR≥0.5, kill CI-LB≤0 at day 30/60. The factor screens (10.3) are the intake; Quality Compounders (8/8-trade-forward) is the best-seeded intake — start there, not from symbols.
- 9. Pod 2 — H-119 stays shadow; optional Connors-family forward pod (SPY/QQQ RSI-2) — only if Pod 1 staffing allows; else let it die. luxalgo_confluence SHORT remains observation-only (needs 2nd source + beta decomposition + 2× measured-slippage survival); mega_mutation observe-only.

P2 — portfolio structure (months):
- 10. Barbell: 70–85% beta core (index ETFs / Canadian equivalents e.g. XEQT-class + aggregate bonds, fee ≤0.20%, TFSA/RRSP sheltering) + ≤15–25% premia satellite (Pod 1) + ≤5% pods with −15%/−25% circuit-breakers; never size on 👑/"High Conviction"/snapshot tiles; report every month against matched-exposure benchmarks.
- 11. If nothing passes by day-90: conclude "no deployable edge on available data" in writing, retire the pipeline budget, keep the audit harness as a public good, put the money in the core. That is a successful outcome of this program, not a failure.

12. Updated bottom line (v3)
The docs now agree with the data: no class is money-ready, the one OOS-positive class is EQUITY (+0.61, 33 folds), the only forward-instrumented lead (H-119) fails its own bar, the value/factor screens have zero audited forward record, the paper portfolios are scaffolding, and the promotion machinery is fail-open in places. The winning move set is unchanged from v2 and now sharper: agree the denominator; make selection-alpha-vs-hold the headline; fix the two pages to tell one truth; spend the next quarter on ONE equity premia pod; keep everything else starved; hold beta for the compounding. Anything that cannot survive two months of forward clock, you never had.

Not personalized investment advice.

---

Part 4 (v3.1) — Cross-check vs main AFTER the agent's fix commits (verified 2026-11-19 ~07:00Z)
The on-main copy of this file was v1, and your AI agent's review (docs/AUDIT3_FEEDBACK_RESPONSE_2026-11-19.md) closed out several v1 items. Verified directly on main this morning — your re-uploaded copy (this file) reflects both the fixes and the remaining open items, so do not let the agent re-grade stale §-numbers against them:

Landed on main (verified):

- §2.1 expectancy gate — fixed. alpha_engine/audit3_tribunal.py: BH family now uses one-sided bootstrap P(net mean ≤ 0) (p_value); WR binomial is p_wr — "reported, never gated"; p_harm switched to bootstrap P(net mean ≥ 0); conventions string updated. (Note: the agent found this was worse than v1 claimed — q≈1.0 for any WR<50% cell, so premia cells were doubly blocked.)
- §2.4 trial accounting — DSR fixed (45 vs 59 vs registry-99 reconciled in code comments); Bonferroni alpha = 1/45-ish per tested cells.
- §2.8 provenance — input hash/retention instead of raw /tmp path (per response doc; tribunal conventions now read "audit3.v1 … seeded resamples").
- §2.2 A⊂B pairing — the segment-dedup logic issue recorded; pairing acknowledged-fixed in response doc.
- §5.1 spec redaction — done (partially). docs/FINANCE_DB_SCHEMA_SPEC.md on main: 0 occurrences of host (mysql.50webs.com) and credential path (dbpasses); ~4 residual mentions of database names (ejaguiar1_stocks/ejaguiar1_backtests) remain — acceptable if intentional; delete them too if this repo is ever made public. (Grep verification, this pass.)
- §2.9 partial — plus their new finding documented in updates/ ("audit3-coverage-panel-and-selection-alpha", "audit3-edge-hunt-no-positive-alpha", "audit3-enforcement-denylist" … — read these; they add material from main that v1 never saw).
- §1.4 of this doc (confirmatory/discovery BH namespace) — scaffold live. reports/audit3_confirmatory.json exists: a pod may reach PROVEN_T2 only if pre-registered there; "pods": [] — the registry is empty. This is now the single most valuable 200 bytes in the repo: the promotion path is built and unused. Register Pod 1 (§11.8) there before looking at a single new forward datapoint.
- .github/workflows/audit3-ledger.yml + audit3_denylist.py + test_audit3_enforcement.py exist on main — enforcement work in flight (response doc marks §2.10 "the most important item; not done"). Expect this to land; do not duplicate it in the re-upload.

Still open (v3's §11 list stands): tribunal→emitter wiring (their §2.10 / doc's "denylist ceremony"), BH confirmatory split as an applied discipline (scaffold only), slippage 2× stress column + measured per-strategy constants (their §2.6 — note they disagree with my v1 "optimistic" framing; v2 above already narrowed this to FUTURES/COMMODITY + 2× stress, which they added), forward_observations ledger (their §5.8 deferred — still missing), stability beyond split-half, ETF conclusions (needs A2 canonical view), per-tile vintage stamping, kill-list vocabulary reconciliation (1 shared name), H-119 dual-tile fix, tier2 panel deletion, portfolios tab disposition.

For the agent reviewing the re-upload: this file (v3.1) supersedes the v1 on main. The agent's response doc remains the correct historical record of which v1 items were fixed/deferred; do not re-litigate those. The open items that remain genuinely open are in §11 (P0/P1/P2) and this Part 4. The subject line "nothing to size / agree the denominator first" is unchanged.
