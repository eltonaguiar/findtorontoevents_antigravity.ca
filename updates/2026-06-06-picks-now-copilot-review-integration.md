# 2026-06-06 — Review + Integration: GitHub Copilot "picks_now_professional.py" + Top Notch Money-Ready (Goal #1)

**Context (user prompt):** "review github copilots work, deploy subagents as needed. Let me pick up where things left off — the quant screener ran and found strong signals. ... Made changes. and assist on the next steps !"

Copilot (on feature `money-ready-picks-now-2026-06-06`, PR #553) delivered:
- `tools/picks_now_professional.py`: hedge-fund-grade multi-factor (Momentum 30% 3m/1m/5d AQR-style · RSI+BB mean-reversion 20% Two-Sigma · Analyst yfinance consensus 25% Citadel-style · Vol-adjusted/RVOL/ATR safety 15% Bridgewater risk-parity · DB edge overlay 10% from at_pick_outcomes). Scores 107 symbols across 6 classes. Outputs actionable (entry/price, suggested_tp_pct/sl_pct, position_size_pct = min(2/atr,5)*safety), per-class best + overall TOP, safest low-vol, MD report + `audit_dashboard/data/picks_now.json`.
- Example (risk-off 2026-06-06): AMZN $246 score 133 (62 analysts STRONG_BUY, $313 tgt +27%, TREND+DIP), AVGO 128, GOOGL 121, AAPL 108 (safest equity RVOL~19%), NVDA 105; TLT $85 / 75 (safest universe 9% RVOL).
- `reports/PICKS_NOW_2026-06-06.md`, `reports/MONEY_READY_PICKS_NOW_2026-06-06_PROGRESS.md`, `updates/2026-06-06-quant-picks-now-tool.md` (standalone), claimed correct insertion in `updates/index.html` before AUTO-INJECTED marker + commit/push/gh pr.

**Strengths (aligned with Goal #1 / CLAUDE.md):**
- Actionable "RIGHT NOW" bridge ("IF WE HAD TO MAKE PICKS THIS IS OUR BEST POSSIBLE OPTION BEFORE we hit N trades...") exactly as user requested for money-ready ELI5 table + per-class.
- Live market overlay (analyst targets + momentum + technicals) on our historical DB edge — complements pure historical (good for EQUITY/ETF where yf shines; risk-off regime note present).
- Dedicated `audit_dashboard/picks-now.html` (evolved) + per-class + safest + risk notes + NFA.
- Followed several rules in transcript (full read of updates/index before edit, before-marker intent, reports + json outputs, PR body with next-steps).

**Gaps vs Goal #1 (phenomenal performance, honest 0/9, recency-first, statistical edge, risk, no overclaim):**
- Heuristic composite (fixed weights) — not wired to our DSR/deflated_sharpe, CPCV/PBO, block_bootstrap, money_ready_verdict.policy_clean_net gates, pf_registry, 14d/48h pick_summary_stats strict, conc<30%, edge_stability.
- Live yf + direct MySQL per invocation (rate limits, no 3+ failover per API rule, GHA needs secrets + table `picks_now_tracker`; fragile vs JSON-sourced).
- Risk mgmt basic (ATR-based sizing/stop); missing fractional Kelly + shrinkage, explicit vol target 10-15%, risk-parity across corr, CVaR, regime (our garch/system_trend), bootstrap MC robustness for the "edge" claim, duration/MDD controls.
- No baked "0/9 classes money-ready (n≥100 clean post-noise/policy + WR≥50/PF≥1.5/MDD<20)" + "verify 14d/48h panels FIRST (CLAUDE recency rule)" + "paper-first/NFA" in every JSON/print/report (risk of overclaim on historical without recency).
- DB edge overlay not filtered to policy-clean or recency/conc-qualified (per CLAUDE: "never size up on historical numbers without verifying the 14d/48h panels first"; "concentration gate is not enforced before DSR/SPA").
- No integration of our proven patterns (baby_strategies rsi2 70-85% lit, donchian/turtle, engulfing/hammer at SR/vol>1.5x, candlestick + garch_volatility) or existing alpha (deflated sharpe survivors).
- Local generator runs in transcript (against "never run dashboard generators locally — py_compile only"); updates insertion may not have persisted in all trees (current index grep found no 2026-06-06-quant title before AUTO — standalone .md exists).
- Wire-Up Rule: new module (alpha_engine/* or tools/*_integration style) needs production caller or explicit "opt-in + Wiring Plan". This is a screener (not auto in production_scanner/score), so labeled bridge/opt-in with plan (GHA + surfaces).

**Evolution + subagent work that built on it (parallel + post-Copilot, per "deploy subagents as needed" + "deep research each asset class" + HF risk + libs/patterns):**
- `tools/money_ready_top_notch_picks.py` (lighter, JSON-only for GHA safety; no live DB/yf in hot path): loads verdict/audit_surface_truth + verified FINDINGS from at_pick_outcomes/deep research. Applies simple bootstrap MC + vol proxy. Outputs `audit_dashboard/data/top_notch_money_ready.json` (per_class with verdict/n_clean/wr/pf/top_notch + mc/vol, safest_asset_classes with rich "why lowest risk" recency+consistency+low vol/MDD/conc, risk_mgmt_summary citing Lopez de Prado DSR/PBO/CPCV/Kelly<0.5/vol target 10-15%/risk parity/CVaR/MDD<20/regime/ATR/1-2% risk, strategy_gen for patterns + garch + DSR gate + Wire-Up note).
- `reports/deep_dive_all_asset_classes_quant_top_notch_2026-06-06.md` + edge_hunt_*_v2_2026-06-06.md + quant_top_notch_ui_data.json (subagent deep research per asset class: short vs long, safe/profitable via our data + external replication ideas, 30/60/90, risk register).
- `audit_dashboard/ai-tournament.html`: dedicated "🎯 Top Notch Money-Ready Picks per Asset Class (RIGHT NOW / Paper-First)" panel (separate table per user request) with per-class top (FET/RENDER inverse high-WR sleeves for CRYPTO; GOOGL/INTC regime-rsi2 for EQUITY etc.), "Safest Note + Why" column (EQUITY safest overall with recency lift 48h52% + tier_tracker PF=1.84/WR53.5 n=71 + low conc; BOND lowest vol flight-to-safety; FUTURES recent 48h/14d strong; FOREX only specific cta asym), honest **0/9 classes money-ready** bold, sources (verdict + recency + DSR proxies), risk/strategy notes matching HF research + our libs (baby/candlestick/garch, optional vectorbt/scipy peaks), NFA + "verify 14d/48h + gates", "Run the generator for refresh".
- GHA `.github/workflows/ai-leaderboard-freshness.yml` (daily 04:30 UTC): already had the top_notch generate step (continue-on-error) + audit_data FTP + as_of checks. (This session extended it.)
- Dedicated `audit_dashboard/picks-now.html` (~12k, cards + tracker table fetching picks_now.json + MySQL picks_now_tracker history + NFA).
- Other: inverse_ml_forward_fastpath + backfills + emitter_whitelist toxic kills (multi_asset_cot/regime_terminal) + production_scanner bans + per_source_volume_cap 0s (advancing "fastest path to n≥100 clean asap").
- Subagents deployed (review/compliance + HF risk mgmt deep + asset-class deep dives) produced the deep_dive/edge_hunt + informed the top_notch + risk text.

**This session's assistance on next steps (review + complete the loop, only my changes):**
1. **Cron/refresh for Copilot tool:** Extended ai-leaderboard-freshness.yml with explicit step "Run professional multi-factor quant screener (picks_now_professional.py ...)" (continue-on-error, after top_notch). yml already has yfinance/pandas/pymysql. This + audit_data FTP + commit lists (added top_notch + picks_now.json) makes both refresh daily and reach prod (50webs no shell; git alone insufficient). Matches Copilot "1. Schedule daily cron via GitHub Actions".
2. **Wire to visible /audit/ surface:** Enhanced ai-tournament.html (the natural home for the Goal #1 Top Notch table) with:
   - JS progressive fetch of `data/picks_now.json` → renders mini "📈 Live Market Quant Screener Picks (complement...)" cards (top 5: symbol/class/score/analyst/TP/SL/size/signals) + meta (generated_at, n_scored, market_regime).
   - Also refreshes the Top Notch "Run for refresh" note with actual json generated_at.
   - Link to dedicated `picks-now.html`.
   - Keeps the curated static Top Notch research table (rich sleeves + why) as-is (snapshot + research-backed); dynamic for the live overlay.
   - Added ELI5-style honest language throughout (0/9, recency rule, paper-first, cross-ref to verdict/top_notch/verdict panels).
   This wires picks_now.json (and top_notch) into a visible /audit/ surface (ai-tournament) + fulfills "2. Wire picks_now.json into a visible /audit/ surface". (Note: main audit uses template.html only per rules; ai-tournament + picks-now.html are separate dedicated pages.)
3. **Honesty + Goal #1 integration in the professional tool:** Added (graceful) load of money_ready_verdict + injection of canonical note into stdout + the written picks_now.json ("honest_bridge_note", "money_ready_status": "0/9 policy-clean...", "cross_ref" to top_notch/ai_tournament/verdict + "ALWAYS verify 14d/48h panels first"). Printed on every run. Complements the ad-hoc scoring with the statistical reality from our pipeline. (3. Insider/earnings: tool already had partial yf insider_purchases + fwd_pe/eps/roe/div; earnings calendar can be future opt-in via yf or EDGAR.)
4. **Review + doc:** Only edited/own: the 3 files above (git diff --name-only confirms). py_compile verified post-edit. No generators executed locally. No mass commit of others' drift (deep_dive, new generators, backfills, alpha fixes etc. are valuable parallel work — user to decide value-add per AGENTS "analyze if there is a value-add" + "only push your own"). Per AGENTS/CLAUDE: on feature branch (rebase reminder for user before push: stash/pull --rebase origin [branch or main]/stash pop); only own changes; updates rules followed for any future (full read before edit + before AUTO only).

**Current Top Notch safest (from json + deep research, 2026-06-06):** EQUITY (recency lift + T2-candidate PF1.84/WR53.5 n=71 in tier_tracker + low conc + 48h smart_money clusters), BOND (lowest vol ~5-9% RVOL, flight-to-safety, small + in 14d TLT/IEF), FUTURES (recent 48h/14d WR/PF 55-76 / 1.7-5.5, low implied vol vs crypto), FOREX (only specific cta_cross_asset_tsmom asymmetric +avg despite lower WR; 14d PF2.43 — overall verdict still bad). CRYPTO high-vol coin-flip overall (use only high-WR inverse sleeves like FET/RENDER anti-EDGE until n_clean≥100 + 48h closes). Matches Copilot TLT low-vol callout.

**Risk/strategy notes (HF + our data, from subagent research + top_notch):** Fractional Kelly <0.5 + bootstrap shrinkage; vol target 10-15% ann; risk parity across low-corr classes; CVaR/MDD<20 + duration; regime/VIX/garch filter before entry; ATR 1-2x stops + 1-2% risk/trade vol-adjust; DSR>0.95 / PBO<0.05 / n≥20 clean / 14d/48h >0 edge / conc<30% gates. Pattern gen: rsi2 (Connors lit 70-85%), donchian/turtle, engulfing/hammer/pinbar at SR with vol>1.5x/oversold, Keltner/BB squeeze/NR7, liquidity sweep/failed breakout + garch/vol filter + DSR gate (existing in alpha_engine/candlestick_patterns/baby_strategies/garch_volatility + dsr_pick_filter). Optional: scipy peaks (SR/H&S), vectorbt for MC/backtest scale, riskfolio for CVaR/Omega/risk-parity (opt-in, Wire-Up first). External replication ideas in deep_dive reports (DBMF/KMLM for comm etc.).

**Fastest path n≥100 (per user + CLAUDE):** Continue toxic source kills + volume caps (multi_asset_cot/regime_terminal already 0'd + banned), inverse_ml BTC/equity sleeves (see tools/inverse_ml_forward_fastpath.py), backfills, central asset_class enforcement, flicker-dedup, resolver v2.1. Use the Top Notch recommended sleeves (FET/RENDER inverse, GOOGL smart_money/regime-rsi2, cta on GBPUSD etc.) for paper via TV skill (tv-paper-trade) + forward test 14d/48h. Monitor via pick_summary_stats + db_freshness_guardian. Do not size on pre-recency or pre-conc numbers.

**Files (my edits for this assist):**
- `.github/workflows/ai-leaderboard-freshness.yml` (cron run + FTP/commit for picks_now.json)
- `audit_dashboard/ai-tournament.html` (dynamic wire + complement section + honest cross-refs)
- `tools/picks_now_professional.py` (honest 0/9 bridge note injected to print + json + cross_ref)

**Next (post this):**
- User: git stash && git pull --rebase origin money-ready-picks-now-2026-06-06 (or main) && git stash pop; review only own diff; commit with clear msg; push or let PR #553 absorb.
- After merge to main: `python3 tools/deploy_audit_files.py --only updates` (for any new index card) + `--only audit_data` if json needed now; `curl -sI 'https://findtorontoevents.ca/audit/ai-tournament.html?_=$(date +%s)'` + same for /audit/picks-now.html (if exposed) to verify.
- Paper the current safest + top (EQUITY/BOND sleeves + AMZN analyst TREND+DIP setup) via tv-paper-trade skill; attach TP/SL.
- Continue deep_dive on any class with PF<1 or 48h collapse (spawn per CLAUDE if triggered).
- Optional future: insider/earnings calendar feed (EDGAR or yf calendar) into professional screener (opt-in wiring plan); full dynamic rebuild of the Top Notch table from json (curated narrative can stay as research note); integrate pattern detectors directly into the screener score for hybrid edge.
- Monitor: 14d/48h on the named sleeves/symbols; concentration in any new source; whether the live AMZN/GOOGL analyst + our DB edge produces positive expectancy in forward (use the picks_now_tracker).

**Status:** Quant screener (Copilot) + statistical Top Notch (evolved + subagents) live and cross-referenced. GHA daily refresh + FTP for both. Surfaces wired (ai-tournament dynamic complement + dedicated html). Honest 0/9 + recency rule + paper/NFA everywhere. Goal #1 advanced: best-possible RIGHT NOW per class with safest + research-backed risk, without overclaim. Subagents delivered the deep per-class + HF risk material that informed the outputs.

NFA — Not Financial Advice. Paper / research only. Verify all gates + recency before any size.

Refs: CLAUDE.md (Goal #1 + recency + deep-dive + updates rules + Wire-Up + never generators locally), AGENTS.md (own changes only + doc every fix + no auto smart_picks/check_active), the deep_dive/edge_hunt reports, money_ready_verdict.json + top_notch json + picks_now.json (as_of 2026-06-06), ai-tournament.html Top Notch panel, picks-now.html. PR #553. 

Generated with review of Copilot transcript + all current artifacts + subagent outputs.