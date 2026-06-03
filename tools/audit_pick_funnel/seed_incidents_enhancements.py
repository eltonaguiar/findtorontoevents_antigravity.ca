"""
Seed INCIDENT_* + ENHANCEMENT_* tables with findings from the 2026-05-25
multi-AI audit (Claude Opus 4.7 + Ring-2.6-1T + opencode + grok session
exports). Idempotent: uses INSERT ... ON DUPLICATE KEY UPDATE keyed on title.

Pattern: one row per actionable finding. Tables tagged by asset class.
'OVERALL' table catches cross-cutting issues (resolver dead, env-var bugs).
"""
from __future__ import annotations
import json, os
import pymysql

# Data rows use a few historical singular asset-class labels, while the
# dashboard migration standardized the table names to plural suffixes.
TABLE_SUFFIX_ALIASES = {
    "ETF": "ETFS",
    "STOCK": "STOCKS",
    "COMMODITY": "COMMODITIES",
    "BOND": "BONDS",
}


def table_suffix(label: str) -> str:
    return TABLE_SUFFIX_ALIASES.get(label, label)


# (table_suffix, title, description, severity, status, affected, fix, link_md_path, link_url, link_github_ref, reporter)
INCIDENTS = [
    # ---- OVERALL (cross-cutting) ----
    ("OVERALL", "trust_score NULL on 99.99% of closed picks",
     "trading_picks.trust_score is NULL on 38,884 of 38,889 closed picks. HC overlay requires trust_score>=4 (CRYPTO) / >=5 (EQUITY). Cited CRYPTO 60.3% N=562 and EQUITY 68.1% N=72 stats unreproducible — only 5 closed picks have a non-NULL trust_score.",
     "P0", "OPEN", "trading_picks.trust_score / audit_dashboard/hc_filter.js",
     "Backfill trust_score from strategy registry OR move HC gate to a field that IS populated (elite_score / derived TRUST tier). Or mark HC overlay UNVERIFIABLE on UI until backfill lands.",
     "reports/2026-05-25_audit_ui_edge_audit.md", None, None, "claude-opus-4-7"),

    ("OVERALL", "5 FOREX rows have pnl_pct < -100% (one at -106,700%)",
     "Unit-clamp bug commit #876 missed 5 rows. Distorts FOREX avg to -8% and rounds PF to 0.00, making the entire class look catastrophic even though baseline WR is 43.9% on n=1666.",
     "P0", "OPEN", "trading_picks.pnl_pct (FOREX category)",
     "UPDATE trading_picks SET pnl_pct = -100 WHERE pnl_pct < -100 AND category='FOREX'. Investigate the 5 rows to see which strategy/script bypassed the clamp.",
     "reports/2026-05-25_audit_ui_edge_audit.md", None, None, "claude-opus-4-7"),

    ("OVERALL", "signal_outcomes table 82 days stale",
     "Last resolved 2026-03-04. Outcome resolver pipeline appears dead. All forward-WR performance claims unverifiable because signal_outcomes has only 0.09% coverage of raw picks.",
     "P0", "OPEN", "at_signal_outcomes / outcome resolver pipeline",
     "Investigate why resolver stopped writing. Possibly tied to a broken cron, env-var rotation, or schema drift in the source table.",
     None, None, None, "ring-2.6-1t"),

    ("OVERALL", "Top-N Rank Backtest tool returned Access denied",
     "tools/top_n_rank_backtest.py read DB_STOCKS_PASSWORD but this host sets DB_PASS_STOCKS. Fell back to default password 'stocks' -> MySQL 1045 Access denied. Also queried asset_class/score columns that don't exist on live trading_picks (uses category/elite_score).",
     "P1", "RESOLVED", "tools/top_n_rank_backtest.py",
     "Two commits: 702eac27 (env-var aliasing) + c5fcbdc1 (schema columns). Verified live: EQUITY 90d returns n=85, top-10/day cum PnL +1.16%.",
     None, None, "702eac27,c5fcbdc1", "ring-2.6-1t"),

    ("OVERALL", "COT paper pilot over-emission",
     "cot_paper_pilot.py counts the same weekly CFTC release as ~100 separate trades. Inflates n from ~5 real unique releases to 101. The DSR=1.0/WR=86.5% headline is therefore overstated. Three independent AI audits flagged this.",
     "P0", "OPEN", "cot_paper_pilot.py / cot_positioning strategy",
     "Deduplicate by CFTC release week. Recompute DSR + WR + PF on the deduped n. Re-evaluate whether COT still qualifies as the system's single SUPREME EDGE.",
     None, None, None, "ring-2.6-1t"),

    ("OVERALL", "ML calibration system-wide inverted",
     "Confidence is anti-predictive: conf>=0.9 -> WR 14.4%, conf 0.5-0.6 -> WR 60.3%. The 5-factor Smart Picks engine weights quality/elite_score at 35% which is derived from confidence, so the top-of-funnel ranker is structurally flipped — at least for crypto.",
     "P0", "TRIAGED", "smart_picks_engine.py / score derivation",
     "Invert the confidence contribution for crypto (or use trust_score as primary signal as code-comment already suggests). Validate across other classes — likely needs per-class inversion.",
     None, None, None, "kimi/multiple"),

    ("OVERALL", "Smart Picks 'Signal Time' is dashboard-file age, not pick age",
     "smart_picks_feed pick objects lack the signal_time field. Template logic falls back to age_hours which is computed at dashboard JSON build time. So all rows display the same '1.4h ago' regardless of when the pick actually fired.",
     "P1", "OPEN", "audit_trail/dashboard_generator.py (smart_picks_feed builder)",
     "Populate signal_time = trading_picks.created_at on every entry in the smart_picks_feed payload. One-line addition.",
     "reports/2026-05-25_audit_ui_edge_audit.md", "https://findtorontoevents.ca/audit/", None, "claude-opus-4-7"),

    ("OVERALL", "smart_picks.json file 25 days stale",
     "data/smart_picks.json last regenerated 2026-04-30T02:56. The dashboard reads smart_picks_feed which IS more recent (~1.5h), but the underlying picks may be cycled with stale entry prices.",
     "P0", "OPEN", "data/smart_picks.json / smart_picks_engine.py",
     "Re-run smart_picks_engine.py and wire to a daily cron. Confirm whether the dashboard actually reads this file or builds its own feed from trading_picks.",
     None, None, None, "ring-2.6-1t"),

    ("OVERALL", "Swarm Picks tab effectively abandoned",
     "data/swarm_picks.json has 38 picks; newest is dated 2026-05-12 (13 days old). Workflow swarm-pick-review.yml runs daily but no longer adds picks — only resolves the existing 38.",
     "P1", "OPEN", "audit/ Swarm Picks tab / .github/workflows/swarm-pick-review.yml",
     "Either revive multi_model_pick_gen.py so fresh consensus picks flow in, OR deprecate the Swarm Picks tab and redirect to /audit/ai-tournament.html.",
     "reports/2026-05-25_audit_ui_edge_audit.md", "https://findtorontoevents.ca/audit/", None, "claude-opus-4-7"),

    # ---- per-class ----
    ("STOCKS", "PEAD equity strategy stuck in shadow mode",
     "The only WF-VERIFIED equity strategy (62.2% OOS WR on 2-day window) is the new pead_equity, but it never made it past shadow. Meanwhile the broken earnings_drift (0% WR on 92 picks) was active in prod.",
     "P0", "OPEN", "alpha_engine/pead_equity (shadow mode)",
     "Promote pead_equity from shadow -> probation. Document wire-up in updates/ per the Wire-Up Rule.",
     None, None, None, "ring-2.6-1t"),

    ("STOCKS", "US Equity screener emits zero picks",
     "The /audit/ueps tab is rendered (n=0/100 disclaimer shown) but no picks have ever been emitted. Composite (Magic Formula x Piotroski x Acquirer's Multiple x SafetyGate) is documented but has no live writer.",
     "P1", "OPEN", "alpha_engine equity scanner / US Equity Picks tab",
     "Wire the UEPS composite to a weekly scanner. First emit can be sample/seed to validate plumbing end-to-end.",
     "reports/2026-05-25_audit_ui_edge_audit.md", "https://findtorontoevents.ca/audit/#ueps", None, "claude-opus-4-7+ring"),

    ("STOCKS", "EQUITY production scanner may not be routed",
     "code grep found no _run_equity_scanner or similar routing function in production_scanner.py main loop. Strategies (connors_rsi2, quality_compounders, equity_momentum_regime, pead_equity) exist in code but may never be called.",
     "P1", "OPEN", "alpha_engine/production_scanner.py main loop",
     "Add explicit per-class routing functions; verify each documented strategy is reachable from main(). Add a smoke test.",
     None, None, None, "ring-2.6-1t"),

    ("CRYPTO", "ML 'edges' with PF 99-1094 are likely look-ahead leakage",
     "Pick-funnel top_edges_per_class found cells like 'copy_trader_intel & LONG' (n=21, PF 1094) and 'conf=0.80-0.85 & ml' (n=42, PF 674) — values that high on tiny samples almost always indicate look-ahead bias in the feature pipeline, not real edge.",
     "P1", "TRIAGED", "alpha_engine ml_enhanced_* family / copy_trader_intel feature pipeline",
     "Audit the feature pipeline for look-ahead bias. Add walk-forward gate before any ML strategy claims edge. Mark current 'DSR=0.9995' claims as 'small-sample, awaiting n>=100 confirmation' on the dashboard.",
     "audit_dashboard/data/top_edges_per_class.json", None, None, "claude-opus-4-7+deepseek+cerebras"),

    ("CRYPTO", "quan_engine_scalp degraded to PF 0.42 / WR 37%",
     "edge_decay_heatmap shows quan_engine_scalp at n=4236, WR 37.4%, PF 0.42 — verdict 'dead'. Yet it remains a substantial share of open CRYPTO volume per CLAUDE.md ('18% volume @ PF 0.70 drag elite strategies down').",
     "P1", "OPEN", "alpha_engine quan_engine_scalp emitter",
     "Per the mutation-three-axis protocol: cut volume share, mutate, or kill. Required to lift the CRYPTO class PF above the T2 threshold.",
     "audit_dashboard/data/edge_decay_heatmap.json", None, None, "claude/edge_stability"),

    ("CRYPTO", "claude_ml_moderate_mut bootstrap PASS is single-row JUPUSDT outlier (945x)",
     "PR #481/#482 bootstrap CI: IS_PF=310.77 on n=67 but pf_lo_95=1.31. One row (id=214622) JUPUSDT pnl_pct=76573 drives gross-profit sum; without it PF collapses. Do not promote to live or forward-pilot until sustained_pf / pf_lo_95>=1.5 on clean sample.",
     "P1", "OPEN", "verified_strategies/claude_ml_moderate_mut / bootstrap CI gate",
     "Block promotion; add sustained_pf resample metric (see updates/2026-06-02-suspicious-pass-investigation.md). B_flip and inverse_ml_enhanced_BTCUSDT_15m_D are legit forward-test candidates instead.",
     "updates/2026-06-02-suspicious-pass-investigation.md", None, None, "grok-2026-06-03"),

    ("FOREX", "forex_carry.py exists in repo but is NOT in allowlist",
     "alpha_engine/new_strategies/forex_carry.py implements G10 interest-rate differential carry with claimed 55-60% WR / PF 1.2-1.5 but is not registered in non_crypto_policy.NON_CRYPTO_STRATEGY_POLICY so it never emits picks.",
     "P1", "OPEN", "alpha_engine/non_crypto_policy.py allowlist",
     "Add forex_carry to NON_CRYPTO_STRATEGY_POLICY with probation thresholds. Document wire-up in updates/.",
     None, None, None, "ring-2.6-1t"),

    ("FOREX", "FOREX SL at 0.5% sits at median daily FX ATR",
     "Causes 44% SL hit rate vs 12% TP hit (3.7x more stops than targets). After April 2026 widening (TP 0.75%->1.5%, SL 0.5%->0.8%) the situation improved but still asymmetric.",
     "P1", "TRIAGED", "alpha_engine FOREX TP/SL config",
     "Widen FOREX SL to >=1.0% (or use 1.5x daily ATR). Backtest before deploying.",
     None, None, None, "ring-2.6-1t"),

    ("COMMODITIES", "cftc_cot_commercial_signal BLOCKED (19% WR on n=16)",
     "Strategy is in code but blocked from production. Either rehab via mutation protocol or formally retire.",
     "P2", "OPEN", "alpha_engine cftc_cot_commercial_signal",
     "Run mutation analysis (docs/MUTATION_THREE_AXIS_PROTOCOL.md). If no axis recovers, formally retire and remove from allowlist.",
     "docs/MUTATION_THREE_AXIS_PROTOCOL.md", None, None, "ring-2.6-1t"),

    ("FUTURES", "futures_mean_reversion and ema_stack_momentum BANNED at 0% WR",
     "Both strategies sit in code with BANNED status. Remove from registry to declutter.",
     "P3", "OPEN", "alpha_engine futures_mean_reversion / ema_stack_momentum",
     "Formal retirement entry. Move source files to deprecated/ subfolder.",
     None, None, None, "ring-2.6-1t"),

    ("BONDS", "bond_connors_rsi2 new, probation, no forward trades",
     "Claims 73% WR but is brand new — needs forward-test data before promotion.",
     "P3", "OPEN", "alpha_engine/new_strategies/bond_connors_rsi2.py",
     "Run for 60 days in shadow; gate to probation when n>=20 with WR>=55%.",
     None, None, None, "ring-2.6-1t"),

    ("ETFS", "All 5 ETF strategies on probation with ZERO verified forward trades",
     "etf_dual_momentum, etf_sector_momentum, etf_risk_parity_rotation, etf_faber_tactical, etf_trend_following all allow_without_forward=True. No track record.",
     "P2", "OPEN", "alpha_engine ETF strategies / config",
     "Pick one (etf_faber_tactical has strongest academic backing per Ring) and graduate to probation with a real forward floor. Document promotion path.",
     None, None, None, "ring-2.6-1t"),

    ("PENNY", "skyrocket_detector NOT wired to production",
     "alpha_engine/skyrocket_detector.py has the SIDU pattern framework ($0.63->$3.79 example) but is not called from production_scanner.py.",
     "P2", "OPEN", "alpha_engine/skyrocket_detector.py",
     "Wire to production scanner per Wire-Up Rule. Add tests + integration doc.",
     None, None, None, "ring-2.6-1t"),

    ("PENNY", "penny_deep_oversold BLOCKED by Gate 0",
     "Strategy emits but every pick is rejected at Gate 0 (initial filter). Either fix Gate 0 to allow penny-class scores or move to a class-specific scoring path.",
     "P3", "OPEN", "audit_trail/quality_gates.py Gate 0",
     "Investigate Gate 0 logic. Likely needs per-class score floor.",
     None, None, None, "ring-2.6-1t"),

    # ---- Added 2026-05-25 from Qwen db_health.json exploration ----
    ("OVERALL", "PnL integrity mismatch on 38.97% of sampled closed picks",
     "db_health.json reports 10,501 / 26,945 sampled rows have a >1% pnl discrepancy between stored pnl_pct and recomputed (entry/exit/direction). 12,735 have >0.01% mismatch. Tier: RED. All cohort WR/PF stats built on top of trading_picks.pnl_pct are suspect at this drift level.",
     "P0", "OPEN", "trading_picks.pnl_pct integrity",
     "Re-resolve historical closed picks via re_resolve_historical_v2.py (referenced in template.html). Quantify per-strategy drift and re-publish asset_class_health post-fix.",
     "audit_dashboard/data/db_health.json", None, None, "qwen-code"),

    ("OVERALL", "WON status rows show avg pnl_pct = -41.1%",
     "won_pnl_contradiction check: 2,531 rows tagged status='WON' have avg_pnl=-41.13%, 9 with negative pnl. SL_HIT rows are all negative as expected (good); TP_HIT all positive (good); LOST rows mostly negative (correct). The WON status is a labeling bug, not a stats artifact — every claim using status='WON' as a win flag is corrupted.",
     "P0", "OPEN", "trading_picks.status='WON' rows",
     "Re-label legacy 'WON' rows by recomputing from pnl_pct sign + exit_reason. WON->TP_HIT where pnl>0, WON->LOST or EXPIRED where pnl<=0. Add a CHECK constraint going forward.",
     "audit_dashboard/data/db_health.json", None, None, "qwen-code"),

    ("OVERALL", "56,559 ghost rows in trading_picks (top cohort: 20,474 identical MATICUSDT entries)",
     "ghost_rows audit: 12 cohorts with thousands of identical (asset_class, strategy, symbol, direction, pnl_pct) rows. Top: CRYPTO/quan_engine/MATICUSDT/LONG/pnl=-15.0 with n=20,474 from 1 distinct entry. MEMECOIN/meta_strategy variants make up the next 10. This single cohort alone is dragging quan_engine_scalp stats to PF 0.42 / WR 37%.",
     "P0", "OPEN", "trading_picks ghost-row write path",
     "DEDUP via (asset_class, strategy, symbol, direction, pnl_pct, created_at) where distinct_entries=1 and n>50. Investigate the writer that's emitting the duplicates. quan_engine + meta_strategy are the top offenders.",
     "audit_dashboard/data/db_health.json", None, None, "qwen-code"),

    ("OVERALL", "29.2M open positions in bt_backtest_trades (NOT trading_picks); monitoring script miscounted",
     "open_bloat check on 2026-05-25: db_health_check.py queried bt_backtest_trades (millions of backtest rows) and reported 29,254,204 OPEN rows. The incident was incorrectly attributed to trading_picks (which had ~46K rows at the time). info_schema estimate for bt_backtest_trades was 1,271,867 — the 23x divergence was itself a monitoring bug (COUNT(*) vs TABLE_ROWS sampling). The forward_validator was never frozen (alpha-engine-live ran green every ~2h); the actual freeze was the Outcome Resolver workflow (git-add on gitignored file). Fixed 2026-05-28: db_health_check.py now queries both tables independently + cross-validates against info_schema with >10x divergence detection.",
     "P0", "RESOLVED", "tools/db_health_check.py check_open_bloat() + outcome-resolver.yml",
     "Fixed: db_health_check.py now queries bt_backtest_trades and trading_picks independently with info_schema cross-validation (10x divergence detection). The 29.2M was a monitoring bug (COUNT(*) on backtest table, not trading_picks). Forward validator was never frozen — the actual freeze was the Outcome Resolver workflow. No further remediation needed for this incident.",
     "updates/2026-05-28-forward-validator-outcome-resolver-remediation.md", None, None, "qwen-code+buffy"),

    ("OVERALL", "UNKNOWN asset_class on 951 active + 54 closed picks",
     "Category is NULL/UNKNOWN for 951 active picks (~10% of active set) and 54 closed (35.2% WR). UI can't apply per-class gates to UNKNOWN rows. Cross-class stats undercount these.",
     "P2", "OPEN", "trading_picks.category writer / classifier",
     "Backfill UNKNOWN rows using symbol pattern matching (USDT/BTC suffix -> CRYPTO; =X suffix -> FOREX; etc.). Add a classifier guard at write time.",
     None, None, None, "claude-opus-4-7"),

    ("BONDS", "Antigravity_bond: 0% WR on n=9 — kill emission",
     "audit_benchmark_analysis_2026-05-24.md: BOND class is 0% WR / PF 0.00 / Sharpe -2.465. Only strategy is antigravity_bond with 1 historical pick. Already flagged P0 in Freebuff 2026-05-17.",
     "P0", "OPEN", "alpha_engine antigravity_bond",
     "Kill BOND emission entirely. Re-enable only after a viable yield-curve or duration strategy is built (see ENHANCEMENT_BONDS).",
     "reports/audit_benchmark_analysis_2026-05-24.md", None, None, "qwen-code+freebuff"),

    ("COMMODITIES", "Class-level COMMODITY 11.9% WR / PF 0.29 / Sharpe -0.534",
     "Benchmark says CRITICAL — cot_positioning at the STRATEGY level is strong (DSR=1.0 per Ring) but at the CLASS level (n=140 closed) numbers are catastrophic because cot_positioning is now BLOCKED per audit benchmark, and remaining cta_cross_asset_tsmom + cta_commodity_momentum_term are losers.",
     "P0", "OPEN", "alpha_engine commodity strategies (post cot_positioning block)",
     "Retire all remaining COMMODITY strategies. Rebuild from non-COT signals (term structure, EIA inventory, weather overlay). Reconcile the Ring 'cot DSR=1.0' claim vs the audit-benchmark 'cot BLOCKED' claim — see COMMODITY rationalize entry.",
     "reports/audit_benchmark_analysis_2026-05-24.md", None, None, "qwen-code+freebuff"),

    ("COMMODITIES", "Reconcile: cot_positioning DSR=1.0 (Ring) vs BLOCKED (audit benchmark) — contradiction",
     "Ring's 2026-05-25 audit says cot_positioning is the SUPREME EDGE (DSR=1.0, WR=86.5%, n=104). audit_benchmark_analysis_2026-05-24 says cot_positioning is BLOCKED and the COT-dedup audit downgraded WR to 5% / PF 0.12 on n=20 post-dedup. Both can't be true.",
     "P0", "OPEN", "cot_positioning evaluation (pipeline vs paper-pilot vs class aggregate)",
     "Run the COT-dedup audit live, compute n + WR + PF under (a) raw, (b) deduped-by-release-week, (c) cot_paper_pilot-only sleeve. Publish the truth-table; update the page's SUPREME EDGE callout to match.",
     "reports/audit_benchmark_analysis_2026-05-24.md", None, None, "claude-opus-4-7"),

    # ---- Added from opencode session-ses_1a2d.md queued action items ----
    ("OVERALL", "sync_active_mysql_picks_to_json upstream writer missing — root cause of 0.09% raw-pick outcome coverage",
     "Opencode 2026-05-12 identified the missing upstream writer that should read ACTIVE at_raw_picks, detect TP/SL/time-exit per asset class, and feed new entries into closed_picks.json. Without it the signal_outcomes table has 0.09% coverage of raw picks — every forward-WR claim is built on 0.1% of the actual pick population.",
     "P0", "OPEN", "alpha_engine/active_picks_sync.py (proposed) + forward_validator.validate_picks()",
     "New module alpha_engine/active_picks_sync.py invoked inline from forward_validator. Reuses existing failover price fetchers. Estimate 2-3h with tests. This is the upstream of the 'signal_outcomes 82d stale' incident already filed.",
     "session-ses_1a2d.md", None, None, "opencode/ring-2.6-1t"),

    ("CRYPTO", "meta_strategy template explosion — 1.6M template rows across ~140 symbol/dir pairs in bt_backtest_trades",
     "Opencode flagged 1.6M template rows from meta_strategy across MEMECOIN/CRYPTO symbol+direction pairs in backtest_trades. Same root cause as the ghost-rows finding from Qwen's db_health (top 11 ghost cohorts are meta_strategy MEMECOIN). Defer blanket-block until db_health ghost_rows.top_cohorts repopulates after CI commit-list fix lands.",
     "P1", "TRIAGED", "meta_strategy emitter / bt_backtest_trades writer",
     "Wait 1-2 cron cycles for db_health refresh post-commit d317560ac9c. Then decide: blanket-block meta_strategy on CRYPTO/MEMECOIN OR symbol-triple enumeration.",
     "session-ses_1a2d.md", None, "d317560ac9c", "opencode/ring-2.6-1t"),

    ("FOREX", "All FOREX strategies losers except cta_cross_asset_tsmom SHORT (93% USDJPY concentration)",
     "Per benchmark report: forex_carry_momentum, forex_rsi2_mean_reversion, myfxbook_retail_contrarian all losing. Only cta_cross_asset_tsmom SHORT has WR 57.6% but is 93% concentrated in USDJPY — not a diversified edge, just one carry trade.",
     "P0", "OPEN", "alpha_engine FOREX strategies (concentration risk)",
     "Block all FOREX strategies except cta_cross_asset_tsmom SHORT. Force symbol diversification on that one (cap USDJPY at <50%). Add forex_carry (Ring's recommendation) as the second leg.",
     "reports/audit_benchmark_analysis_2026-05-24.md", None, None, "qwen-code+ring-2.6-1t"),

    ("OVERALL", "Multi-AI panel reached wrong COMMODITY consensus on ungrounded prompt",
     "5-engine NVIDIA NIM panel (Kimi K2.6 + GPT-OSS-120B + GLM-5.1 + Nemotron Super 49B + Mistral Nemotron) unanimously declared COMMODITY the system's #1 alpha, recommending 20-30% allocation. The 3-engine codex/grok/gemini panel (shown the same numbers PLUS leakage signals) classified the same cell DATA_QUALITY_LEAKAGE at ~90% confidence. In-house verification confirmed the leakage panel — 87.6% one-symbol concentration (CT=F cotton), fake Bonferroni denominator, 30-day hot streak only. The merged-cohort registry rerun collapses COMMODITY policy-clean NET PF from 0.18 -> 0.937 (still under T2's 1.5 bar).",
     "P1", "OPEN", "tools/swarm/api_consult.py + consult-nvidia-models / consult-cloudflare-models skills",
     "Mandate inclusion of reports/hypothesis_registry.json rejected-hypothesis entries that intersect the prompt's asset class. Update consult-nvidia-models/SKILL.md + consult-cloudflare-models/SKILL.md to require a leakage-context block in every prompt template. Add a sentence: 'Be skeptical; if data suggests one symbol/source dominates, flag concentration risk.'",
     "reports/2026-05-25_multi_ai_panel_meta_review.md", None, None, "claude-opus-4-7+roo-deepseek-session"),

    # ---- Added from EAGLE review 2026-05-27 ----
    ("OVERALL", "Profitable-but-filtered picks are not surfaced anywhere",
     "The current audit pipeline shows rejects in aggregate but provides no durable lane for picks that failed gates and later would have won materially. That hides false negatives and prevents learning whether concentration, thin-sample, or quarantine rules are discarding real edge.",
     "P0", "OPEN", "audit_trail/quality_gates.py + dashboard_generator.py audit surfaces",
     "Add a profitable-but-filtered / profitable-but-quarantined audit lane with per-pick first-failed gate, later outcome, and asset-class rollups. Keep it observational first — do not weaken live gates in the first batch.",
     "updates/QUICK_WINS_EAGLE_2026-05-27_0217_EST_GPT-5.4_OpenAI.md", None, None, "gpt-5.4/openai"),

    ("OVERALL", "HC JS/Python parity drift can change eligibility by surface",
     "The High Conviction decision path is split across audit_dashboard/hc_filter.js and tools/dashboard_hc_rules.py. EAGLE review found likely drift around confidence handling and small-sample relaxations, so the same pick can qualify differently depending on which surface evaluates it.",
     "P0", "OPEN", "audit_dashboard/hc_filter.js / tools/dashboard_hc_rules.py",
     "Create one canonical HC parameter contract and parity test corpus. Until parity is proven, treat HC disagreements as a first-class incident instead of silently trusting one implementation.",
     "updates/QUICK_WINS_EAGLE_2026-05-27_0217_EST_GPT-5.4_OpenAI.md", None, None, "gpt-5.4/openai"),

    ("COMMODITIES", "COMMODITY headline PF/WR still contaminated by pre-clean COT aggregation",
     "EAGLE review converged with the existing COT forensic concern: the class story remains unsafe while pre-clean or over-emitted COT history can still dominate class-level PF/WR claims. The page should not treat COMMODITY as trustable until independent-cycle-only stats are canonical.",
     "P0", "OPEN", "COMMODITY class-health aggregation / COT-derived history",
     "Recompute class health from deduped independent COT cycles only, then re-derive the honest class verdict. Block promotional Tier claims until the cleaned aggregation is the live source of truth.",
     "updates/QUICK_WINS_EAGLE_2026-05-27_0217_EST_GPT-5.4_OpenAI.md", None, None, "gpt-5.4/openai"),

    ("FOREX", "FOREX class still aggregates losers around a small winner subset",
     "EAGLE review found the class story is dominated by a few stronger sleeves while the aggregate is dragged down by broad losers. The dashboard does not expose that isolate-the-winner vs kill-the-drag distinction cleanly enough.",
     "P1", "OPEN", "FOREX class aggregation / per-sleeve visibility",
     "Add per-sleeve isolation reporting and treat FOREX as a basket of sleeves, not one monolith. Promote only the proven sleeve(s) in audit visibility and keep the rest explicitly quarantined or paper-only.",
     "updates/QUICK_WINS_EAGLE_2026-05-27_0217_EST_GPT-5.4_OpenAI.md", None, None, "gpt-5.4/openai"),

    ("STOCKS", "Penny/meme names still pollute the main EQUITY sleeve",
     "Research and backtest evidence is concentrated in cleaner large-cap equity universes, but live EQUITY still carries penny/meme contamination. This distorts both edge claims and gate calibration for the parent class.",
     "P1", "OPEN", "alpha_engine/config.py EQUITY universe / live EQUITY routing",
     "Split LARGE_CAP_EQUITY from PENNY research-only names and report them separately. Do not let speculative names share the same production quality story as the large-cap sleeve.",
     "updates/QUICK_WINS_EAGLE_2026-05-27_0217_EST_GPT-5.4_OpenAI.md", None, None, "gpt-5.4/openai"),

    ("FUTURES", "FUTURES is a zombie tile with real futures hidden under COMMODITY",
     "The standalone FUTURES class has near-zero useful activity while real futures exposure is represented under COMMODITY. This makes the /audit taxonomy misleading and blocks honest per-class review.",
     "P1", "OPEN", "asset-class taxonomy / FUTURES vs COMMODITY reporting",
     "Replace the empty FUTURES story with a unified futures taxonomy or clearly scope FUTURES as research-only financial futures. The page should stop presenting a zombie tile as if it were a live class.",
     "updates/QUICK_WINS_EAGLE_2026-05-27_0217_EST_GPT-5.4_OpenAI.md", None, None, "gpt-5.4/openai"),
]

# target_release defaults to None for all existing entries; the backfill
# script (tools/audit_pick_funnel/backfill_enhancement_targets.py) computes
# dates based on impact/effort mapping for rows that have NULL target_release.
#
# To set an explicit target_release on a new entry, add it as the 14th tuple
# element (e.g. '2026-07-01 12:00 EST' or '2026-07-01'). Default: None.
ENHANCEMENTS = [
    # (table_suffix, title, description, category, expected_impact, effort, status, proposed_by, related_persona, success_metric, link_md_path, link_url, link_github_ref, target_release)
    ("OVERALL", "Verify the 648-for-0 un-gated-picks claim (DeepSeek session)",
     "Roo's NIM panel session (2026-05-25) reports moderate_confidence (n=455) and low_confidence (n=193) buckets went 0-for-648 over the 6-day window 2026-05-16..21, destroying -825% PnL, while 300 gated picks generated +994%. If real this is the single highest-leverage filter in the system. 0-for-455 is statistically implausible (p~=0.5^455) on honest trades — the bucket may be circularly defined by 'failed all upstream gates.' Verify against audit_dashboard/data/dashboard_data.json::picks.recent_closed filtered to that date range; if buckets are post-gate residuals, 'gate them' is already done.",
     "VALIDATION", "HIGH", "S", "BACKLOG", "claude-opus-4-7", None,
     "Verified n / WR per quality_tier bucket from raw DB; circular-definition determination documented in reports/",
     "reports/2026-05-25_multi_ai_panel_meta_review.md", None, None),

    ("ETF", "Verify regime_adaptive x ETF Wilson CI 49.7-91.8% claim",
     "Roo's session reports that regime_adaptive x ETF is the only persona-asset pair passing all statistical gates (binomial significance + positive PnL + positive Sharpe), Wilson CI 49.7-91.8%. Cross-reference with the prior 30d ETF PF=3.88 'STRONG RECENT' regime-shift thesis. If confirmed, this is the first non-COMMODITY production candidate after the COMMODITY edge debunk.",
     "VALIDATION", "MEDIUM", "M", "BACKLOG", "claude-opus-4-7", None,
     "Wilson CI reproduced from regime_adaptive persona's ETF picks; binomial significance test documented",
     "reports/2026-05-25_multi_ai_panel_meta_review.md", "audit_dashboard/data/research/edge_significance_gate.json", None),

    ("OVERALL", "Verify kimi_signal_tracking + aggregated_picks 6-day source-system claims",
     "Roo's session reports: kimi_signal_tracking 168 picks WR 53.6% +257.34% (best source by total PnL); aggregated_picks 58 picks WR 74.1% +111.02% (underpowered but interesting). Run the same per-source rollup over a longer window (30d/90d) to test if these are persistent edges or 6-day noise. Apply the same dedup/policy/single-source-concentration checks that killed the COMMODITY claim.",
     "VALIDATION", "MEDIUM", "S", "BACKLOG", "claude-opus-4-7", None,
     "Per-source 30d/90d WR/PF confirmed with dedup + concentration flag; advancement-or-rejection documented",
     "reports/2026-05-25_multi_ai_panel_meta_review.md", None, None),

    ("OVERALL", "Backfill trust_score on historical closed picks",
     "Backfill from strategy registry so HC overlay claims become reproducible. Unblocks all 'closed-book edge' callouts on the page.",
     "DATA_FEED", "HIGH", "M", "BACKLOG", "claude-opus-4-7", None,
     "HC-gated closed picks recompute to claimed CRYPTO 60.3%/EQUITY 68.1% (within 5pp tolerance)",
     "reports/2026-05-25_audit_ui_edge_audit.md", None, None),

    ("OVERALL", "Add signal_time field to smart_picks_feed payload",
     "One-line addition in dashboard_generator.py. Stops the 'all picks show 1.4h ago' misleading display.",
     "UI", "MEDIUM", "S", "BACKLOG", "claude-opus-4-7", None,
     "Smart Picks rows display per-pick ages spanning the actual pick lifetime (not all same value)",
     "reports/2026-05-25_audit_ui_edge_audit.md", "https://findtorontoevents.ca/audit/", None),

    ("OVERALL", "Implement random-guess audit self-flag prompt",
     "After each AI-tournament submission, re-prompt the model: 'Are these picks based on cited live market data or speculation? Mark each.' Store flag in tournament_pick_research.research_basis.",
     "METHODOLOGY", "HIGH", "M", "BACKLOG", "claude-opus-4-7", None,
     "research_basis populated on every new pick within 7 days of rollout",
     "DAILY_IDEAS.MD", None, None),

    ("OVERALL", "Cross-model consensus tier-rating extractor",
     "Build tools/ai_tournament/consensus_tier_algorithm.py: for each (asset_class, feature_concept), take median weight across all models in tournament_rating_algorithms. Features with >=2-model consensus seed alpha_engine/score_v3.py.",
     "SCORING", "HIGH", "L", "BACKLOG", "claude-opus-4-7+swarm", None,
     "score_v3.py opt-in sidecar shows >=3pp WR lift vs current score_pick.py on 90d closed picks (paired bootstrap p<0.05)",
     "DAILY_IDEAS.MD", None, None),

    ("CRYPTO", "Add on-chain + funding-rate feed (Glassnode + Coinglass)",
     "Top recommendation from persona-improvement survey: addresses CLAUDE.md CRYPTO PF 1.25 -> T2 PF 1.5 gap. Covers 6 crypto personas (~453 picks).",
     "DATA_FEED", "HIGH", "L", "BACKLOG", "claude+persona_survey", "ring_crypto_native",
     "CRYPTO PF improves from 1.25 to >=1.5 on next 90d sample with funding+whale gates applied",
     "reports/2026-05-25_persona_improvement_survey.md", None, None),

    ("COMMODITIES", "Wire CFTC COT weekly feed for non-cot strategies",
     "Top-2 data-feed investment from survey. Addresses sub-floor FOREX/COMMODITY classes by giving cta_trend / supply_demand / inventory_cycle real positioning data instead of inferring from price.",
     "DATA_FEED", "HIGH", "M", "BACKLOG", "claude+persona_survey", None,
     "CFTC COT data ingested weekly into a dedicated table; non-cot strategies show >=5pp WR lift",
     "reports/2026-05-25_persona_improvement_survey.md", None, None),

    ("OVERALL", "Add VIX/realised-vol regime tag at pick submission",
     "Cheapest single fix per persona-survey — addresses 7 personas / ~470 picks. ~30% of picks fire in the wrong regime today.",
     "GATE", "HIGH", "S", "BACKLOG", "claude+persona_survey", "mean_reversion+momentum_scalp+sharma_quant_momentum",
     "Picks tagged with regime; backtest shows >=3pp WR improvement when filtering by regime-aligned subset",
     "reports/2026-05-25_persona_improvement_survey.md", None, None),

    ("OVERALL", "Universe expansion v1.2 — match AI tournament universe to /audit traded symbols",
     "Currently the AI tournament locks symbols to 2026-05-19 snapshot. Widen to S&P 500 + active /audit picks per class so cross-system comparison is apples-to-apples.",
     "METHODOLOGY", "MEDIUM", "M", "BACKLOG", "claude-opus-4-7", None,
     "Per-class universe doubles or matches /audit symbol count; tournament leaderboard remains stable across switch",
     "audit_dashboard/ai-tournament.html (universe panel)", "https://findtorontoevents.ca/audit/ai-tournament.html", None),

    ("STOCKS", "Promote pead_equity from shadow to probation",
     "Only WF-VERIFIED equity strategy (62.2% OOS WR). Currently dormant.",
     "METHODOLOGY", "HIGH", "S", "BACKLOG", "ring-2.6-1t", None,
     "pead_equity emits >=30 forward picks in first 30 days post-promotion with WR>=55%",
     None, None, None),

    ("FOREX", "Add forex_carry to non_crypto_policy allowlist",
     "Implementation already in repo (alpha_engine/new_strategies/forex_carry.py) with G10 rate differential, claimed 55-60% WR. Only missing the allowlist entry.",
     "GATE", "MEDIUM", "S", "BACKLOG", "ring-2.6-1t", "voss_global_macro",
     "Strategy emits picks within 7 days of allowlist add; achieves >=50% WR on n>=10 within 30 days",
     None, None, None),

    ("BONDS", "Add yield-curve-momentum (TLT/IEF steepener-flattener)",
     "Use new_strategies/tsmom.py framework to trade the 10Y-2Y curve via TLT vs IEF. BOND class currently has only bond_connors_rsi2 (new, no track record).",
     "METHODOLOGY", "MEDIUM", "M", "BACKLOG", "ring-2.6-1t", "voss_global_macro",
     "New strategy emits picks; BOND class n grows from 18 (sub-floor) toward charter n>=100",
     None, None, None),

    ("FUTURES", "Add commodity term-structure roll-yield strategy",
     "Use cta_commodity_momentum_term framework. Captures contango/backwardation premium — proven hedge-fund recipe.",
     "METHODOLOGY", "MEDIUM", "M", "BACKLOG", "ring-2.6-1t", "lang_value_contrarian",
     "Roll-yield strategy emits picks; FUTURES class WR rises above 30% (current 11.1%)",
     None, None, None),

    ("PENNY", "Implement float-squeeze detector from skyrocket_detector framework",
     "Penny stocks have only one (unwired) strategy. Build float-squeeze + volume-breakout signal using existing SIDU pattern code.",
     "METHODOLOGY", "MEDIUM", "L", "BACKLOG", "ring-2.6-1t", None,
     "New strategy wired into production_scanner; emits >=20 picks/month; first 50 picks show WR>=50%",
     None, None, None),

    ("ETFS", "Add real GEX + 0DTE flow data for gamma_raid persona",
     "spotgamma/unusualwhales feeds. gamma_raid currently narrates gamma without consuming it; persona is already at WR 67.9% — real data should lift it further.",
     "DATA_FEED", "MEDIUM", "L", "BACKLOG", "claude+persona_survey", "gamma_raid",
     "gamma_raid persona shows >=3pp WR improvement after data integration",
     "reports/2026-05-25_persona_improvement_survey.md", None, None),

    # ---- Added from opencode session-ses_1a2d.md queued action items ----
    ("OVERALL", "WON-vs-PnL backfill SQL — re-label legacy contradicted rows",
     "Opencode P0 DRAFT. UPDATE pass that re-computes status from pnl_pct for any (status='WON', pnl_pct<0) or (status='LOST', pnl_pct>0) row. Sign-coherence guard already stops NEW contradictions; this backfills the historical 2,531+ WON rows with negative PnL flagged in db_health.json::won_pnl_contradiction.",
     "SCORING", "HIGH", "S", "BACKLOG", "opencode/ring-2.6-1t", None,
     "All WON rows have pnl_pct >= 0; all LOST/SL_HIT rows have pnl_pct <= 0; aggregates re-published",
     "session-ses_1a2d.md", None, None),

    ("BONDS", "Wire bond_scanner.py (3 strategies) to production cron",
     "alpha_engine/bond_scanner.py exists with yield_momentum, duration_rotation, mean_reversion; not currently wired into production_scanner main loop. Universe of 14 symbols ready at config.py:721. Wiring should lift BOND n from 18 to 50+ within 2 weeks.",
     "METHODOLOGY", "HIGH", "S", "BACKLOG", "opencode/ring-2.6-1t", None,
     "BOND n>=50 within 2 weeks of wire-up; class no longer marked 'sample-size-thin' on /audit",
     "session-ses_1a2d.md", None, None),

    ("OVERALL", "Batch-DSR backtest the 206 baby_strategies/ files (zero currently wired)",
     "Opencode found 206 files in alpha_engine/baby_strategies/, ZERO wired to production. Massive untapped pipeline. Surface a batch DSR runner (anti_overfit_audit_sidecar.py over baby_strategies/*) to find DSR-real candidates and promote them per the Wire-Up Rule.",
     "METHODOLOGY", "HIGH", "M", "BACKLOG", "opencode/ring-2.6-1t", None,
     "DSR audit completes on 206 strategies; >=3 candidates with DSR>=0.95 promoted to probation with documented production caller",
     "session-ses_1a2d.md", None, None),

    ("COMMODITIES", "Execute COT 7-step testing plan (steps 1-5 active work + step 6 paper-pilot + step 7 risk-of-ruin)",
     "Opencode P2 PASSIVE. Gates the only currently-DSR-verified single-class deviation candidate (cot_positioning + CT=F). Steps 1-5 ~6h active work; Step 6 = 4-week paper pilot (currently SHADOW); Step 7 = Monte Carlo risk-of-ruin sim.",
     "METHODOLOGY", "MEDIUM", "L", "BACKLOG", "opencode/ring-2.6-1t", "lang_value_contrarian",
     "All 7 steps green; cot_positioning + CT=F clears the 10-step Lopez de Prado AFML readiness gate; first eligible LIVE candidate",
     "reports/cot_paper_pilot_testing_plan_2026-05-12.md", None, None),

    ("OVERALL", "Pick-funnel rejection visibility on /audit",
     "Show why each symbol scanned but not picked was rejected (which gate killed it). Pick-funnel automation already extracts this; needs UI surface beyond /audit/pick_funnel.html.",
     "UI", "MEDIUM", "M", "BACKLOG", "claude-opus-4-7", None,
     "Each asset class shows funnel: scanned -> passed score -> passed trust -> passed regime -> opened. Visible from main /audit page.",
     "audit_dashboard/pick_funnel.html", "https://findtorontoevents.ca/audit/pick_funnel.html", None),

    # ---- Added from EAGLE review 2026-05-27 ----
    ("OVERALL", "Add profitable-but-filtered / profitable-but-quarantined audit lane",
     "Create a non-admission-changing observability lane that records picks rejected by gates or quarantine rules but later resolved positively. This turns hidden false negatives into measurable backlog without weakening live safety gates on day one.",
     "GATE", "HIGH", "M", "BACKLOG", "gpt-5.4/openai", None,
     "Dashboard exposes per-asset-class counts and PF/WR for profitable filtered picks; every row includes first-failed gate + later outcome.",
     "updates/QUICK_WINS_EAGLE_2026-05-27_0217_EST_GPT-5.4_OpenAI.md", None, None),

    ("OVERALL", "Add bounded hot-streak exemption with explicit audit trail",
     "Current streak logic influences scoring but does not create a controlled exemption path. Add a time-boxed, per-sleeve exemption contract so repeated clean winners can earn temporary gate relief without silently changing the system.",
     "GATE", "HIGH", "M", "BACKLOG", "gpt-5.4/openai", None,
     "Every hot-streak exemption has a minimum clean sample, expiry timestamp, explicit reason, and automatic rollback on deterioration.",
     "updates/QUICK_WINS_EAGLE_2026-05-27_0217_EST_GPT-5.4_OpenAI.md", None, None),

    ("ETFS", "Make VIX-gated sector rotation the primary ETF sleeve",
     "EAGLE review identified ETF sector rotation plus VIX gating as the cleanest underused edge in the current repo. Existing mixed ETF sources dilute that cleaner regime-aware strategy story.",
     "METHODOLOGY", "HIGH", "M", "BACKLOG", "gpt-5.4/openai", None,
     "ETF rotation becomes a first-class tracked sleeve with rolling PF/WR/MDD and contributes the majority of ETF class quality picks.",
     "updates/QUICK_WINS_EAGLE_2026-05-27_0217_EST_GPT-5.4_OpenAI.md", None, None),

    ("STOCKS", "Split LARGE_CAP_EQUITY from PENNY research-only names",
     "The main EQUITY sleeve should reflect the clean large-cap / regime-controlled strategy set, while penny/meme names live in a separate research-only bucket. This improves both reporting honesty and future gate calibration.",
     "METHODOLOGY", "HIGH", "S", "BACKLOG", "gpt-5.4/openai", None,
     "Main EQUITY class no longer contains penny/meme symbols; parent-class PF/WR and gate calibration are recomputed on the clean universe.",
     "updates/QUICK_WINS_EAGLE_2026-05-27_0217_EST_GPT-5.4_OpenAI.md", None, None),

    ("COMMODITIES", "Recompute class health from deduped independent COT cycles only",
     "The class should only advertise edge using independent-cycle-aware COT accounting. This enhancement formalizes the honest source-of-truth rule and blocks stale, over-emitted history from defining the class story.",
     "METHODOLOGY", "HIGH", "M", "BACKLOG", "gpt-5.4/openai", None,
     "COMMODITY dashboard tile and supporting rollups use independent-cycle-only metrics; Tier verdict matches the recomputed clean history.",
     "updates/QUICK_WINS_EAGLE_2026-05-27_0217_EST_GPT-5.4_OpenAI.md", None, None),

    ("FUTURES", "Replace empty FUTURES tile with unified futures taxonomy",
     "A unified futures taxonomy would stop the page from showing a nearly empty standalone FUTURES class while real futures exposure is discussed elsewhere. This is primarily a reporting/trust fix before it is a strategy expansion.",
     "UI", "MEDIUM", "M", "BACKLOG", "gpt-5.4/openai", None,
     "The dashboard no longer presents FUTURES as a zombie class; futures exposure is represented under one honest taxonomy with clear sub-sleeves.",
     "updates/QUICK_WINS_EAGLE_2026-05-27_0217_EST_GPT-5.4_OpenAI.md", None, None),
]


def main():
    conn = pymysql.connect(
        host='mysql.50webs.com', user='ejaguiar1_stocks',
        password=os.environ['DB_PASS_STOCKS'], database=os.environ['DB_NAME_STOCKS'],
        port=3306, connect_timeout=20, autocommit=False)
    inc_inserted = inc_updated = 0
    enh_inserted = enh_updated = 0
    with conn.cursor() as cur:
        for (cls, title, desc, sev, st, comp, fix, md, url, gh, reporter) in INCIDENTS:
            tbl = f"INCIDENT_{table_suffix(cls)}"
            # Check existence by title
            cur.execute(f"SELECT incident_id FROM {tbl} WHERE title=%s LIMIT 1", (title,))
            existing = cur.fetchone()
            if existing:
                cur.execute(f"""UPDATE {tbl} SET description=%s, severity=%s, status=%s,
                    affected_component=%s, recommended_fix=%s, link_md_path=%s,
                    link_url=%s, link_github_ref=%s, reported_by=%s
                    WHERE incident_id=%s""",
                    (desc, sev, st, comp, fix, md, url, gh, reporter, existing[0]))
                inc_updated += 1
            else:
                cur.execute(f"""INSERT INTO {tbl} (title, description, severity, status,
                    affected_component, recommended_fix, link_md_path, link_url,
                    link_github_ref, reported_by)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (title, desc, sev, st, comp, fix, md, url, gh, reporter))
                inc_inserted += 1
        for enh in ENHANCEMENTS:
            # Unpack with optional 14th element (target_release)
            cls, title, desc, cat, imp, eff, st, prop, persona, metric, md, url, gh, *tr_rest = enh
            target_release = tr_rest[0] if tr_rest else None
            tbl = f"ENHANCEMENT_{table_suffix(cls)}"
            cur.execute(f"SELECT enhancement_id FROM {tbl} WHERE title=%s LIMIT 1", (title,))
            existing = cur.fetchone()
            if existing:
                cur.execute(f"""UPDATE {tbl} SET description=%s, category=%s, expected_impact=%s,
                    effort=%s, status=%s, proposed_by=%s, related_persona_id=%s,
                    success_metric=%s, link_md_path=%s, link_url=%s, link_github_ref=%s,
                    target_release=COALESCE(%s, target_release)
                    WHERE enhancement_id=%s""",
                    (desc, cat, imp, eff, st, prop, persona, metric, md, url, gh, target_release, existing[0]))
                enh_updated += 1
            else:
                cur.execute(f"""INSERT INTO {tbl} (title, description, category, expected_impact,
                    effort, status, proposed_by, related_persona_id, success_metric,
                    link_md_path, link_url, link_github_ref, target_release)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (title, desc, cat, imp, eff, st, prop, persona, metric, md, url, gh, target_release))
                enh_inserted += 1

    conn.commit()
    print(f"INCIDENTS:   {inc_inserted} inserted, {inc_updated} updated")
    print(f"ENHANCEMENTS: {enh_inserted} inserted, {enh_updated} updated")
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM vw_all_incidents"); print(f"vw_all_incidents:    {cur.fetchone()[0]} rows")
        cur.execute("SELECT COUNT(*) FROM vw_all_enhancements"); print(f"vw_all_enhancements: {cur.fetchone()[0]} rows")
        cur.execute("""SELECT asset_class, COUNT(*) FROM vw_all_incidents GROUP BY asset_class ORDER BY 2 DESC""")
        print("\nIncidents by class:")
        for r in cur.fetchall(): print(f"  {r[0]:14s} {r[1]}")
        cur.execute("""SELECT asset_class, COUNT(*) FROM vw_all_enhancements GROUP BY asset_class ORDER BY 2 DESC""")
        print("\nEnhancements by class:")
        for r in cur.fetchall(): print(f"  {r[0]:14s} {r[1]}")
    conn.close()


if __name__ == "__main__":
    main()
