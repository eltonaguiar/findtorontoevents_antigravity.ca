# Asset Class 90-Day Plan — PENNY_MEME (Low-Quality Equities: Penny Stocks + Meme Coins) — 2026-05-15

**Senior Quant Audit** using `money-maker-continual-improve` skill (brutal skeptical deep-dive on high-risk bucket).  
**Focus**: Dedicated high-risk category (Penny Stocks + Meme Coins) performing far below coin toss (MEMECOIN PF 0.499 / WR 15.7% n=1869; PENNY_STOCK WR 6.76% / PF 0.19 n=148); symbol universe small but illiquid/low-float (8 equity names + ~9-11 crypto memes + dynamic low-cap emissions); primary drag on EQUITY (8/18 speculative tickers) and CRYPTO (volume king but quality disaster); extreme risk management failures (gap risk, manipulation, loose CATEGORY_RISK, no ADV gate); **Recommendation: Full quarantine (0% risk allocation), research-only, NO dedicated high-volatility sleeve**. Already partially enforced in quarantine_manifest + quality_gates but leaks persist. Not investable; toxic to "phenomenal performance" Goal #1.

**Data sources**: `audit_dashboard/data/quarantine_manifest.json` (MEMECOIN/PENNY_STOCK size_caps max_risk=0, PF 0.499 / WR 6.76%), `audit_trail/quality_gates.py:1919-1974` (MEMECOIN class-wide block details), `reports/kimi_edge_audit_2026-05-11/metrics_by_asset_class.csv` (exact stats + rolling_PENNY_STOCK.png / rolling_MEMECOIN.png), `audit_dashboard/data/dashboard_data.json` (2026-05-15T02:28Z: symbol_performance small-n meme winners, recent_closed 150 lowq/3500 total, WIFUSDT 2799 occ, DOGE failing sym_track_wr 29.6%, smart_picks excluded_reasons.meme_long_bear), `alpha_engine/config.py` (CATEGORY_RISK "meme"/"penny" looser SL/TP/hold, EQUITY_SYMBOLS:6 penny+2 meme, CRYPTO_SYMBOLS ~11 meme, SECTOR_MAP, TRAILING_STOP), `alpha_engine/equity_strategies.py:160` (penny_volume_breakout), `alpha_engine/community_strategies.py:631` (community_penny_volume_surge), `alpha_engine/ml_ranker.py:420` (CATEGORY_MAP penny=3/meme=4), `alpha_engine/scanner.py`, `reports/asset_class_90day_plan_EQUITY_2026-05-15.md` (P0 universe split, 8 speculative drag), `reports/asset_class_90day_plan_CRYPTO_2026-05-15.md` (M-038 MEMECOIN quarantine pending, shrink to 25 liquid), `reports/SUPREME_PLAN_90days.md`, `reports/grok_money_maker_audit_transcript_2026-05-15.md` (explicitly queued as "worst categories"), `reports/kimi_edge_audit_2026-05-11/raw_picks_clean.csv` + comprehensive_analysis_report.md.

**Current Charter context** (from CLAUDE.md / master plan / dashboard): No dedicated "PENNY_MEME" in asset_class_health dropdown (mixed into EQUITY PF 1.57/51.9%/n=420 T2-candidate and CRYPTO 1.36/46.7%/n=8011 sub-T2); but quarantine_manifest + quality_gates treat as separate classes with 0% risk cap ("Class quarantined"). EQUITY concentration on AMD (11.65%) but 8/18 tickers speculative pennies/memes (NIO/LCID/RIVN gaps-to-zero, GME/AMC sentiment); CRYPTO heavy WIF/DOGE/PEPE emissions (high occ in dashboard_data). Master plan / SUPREME_PLAN queues this deep-dive + M-038. Kimi F13/F14 + 5-agent swarm 2026-05-12 flagged as structurally broken (synthetic fixtures, kimi_tracker leaks). Sizing_allowed false for these buckets by design. "Penny / Meme" called out by user as worst in /audit dropdown — worse than FOREX (PF 0.81).

---

## Step 1: Establish Brutal Baseline (PENNY_MEME as standalone high-risk bucket)

**Live / Historical performance** (quarantine_manifest.json + kimi_edge_audit_2026-05-11/metrics_by_asset_class.csv + dashboard_data.json + quality_gates.py):

- **MEMECOIN class** (crypto memes: DOGEUSDT, SHIBUSDT, PEPEUSDT, WIFUSDT, FARTCOINUSDT, BONKUSDT, BRETTUSDT, TRUMPUSDT, POPCATUSDT + dynamic): 
  - Kimi audit resolved n=1869: WR 15.73%, n_wins=294 / n_losses=1575, avg_return_pct=-3.5784%, median=0, std=24.52%, cumulative_pnl_pct=-6688.05%, Sharpe_annualized=-2.7877, Sortino=-2.36, MaxDD=-6688%, Calmar=-0.195, **PF=0.499**, expectancy=-3.5784%, long_WR 15.24%, short 16.81%. 
  - Quarantine_manifest: PF 0.499 on n=1869 (matches), max_pct_of_risk=0 ("Class quarantined").
  - Production emissions volume even higher (raw_picks_clean n=123k+ for related) but still negative edge (PF~0.58 in some slices).
  - Dashboard 2026-05-15 symbol_performance (small-n survivors only): PNUTUSDT 7/7 100% +23.5, POPCATUSDT 5/5 100%, BRETTUSDT 5/5 100%, TRUMPUSDT 8/5 62.5% +8 — **illusory** (n<=9, selection bias in consensus list of 50; real forward WR on strats ~30-40%).
  - Recent_closed sample (DOGEUSDT): LOST, SL_HIT, quan_engine (blocked for MEMECOIN), grade D, trust WATCH, sym_track_wr 29.6%, wf_verdict FAILING, ml_composite_grade D, high concentration penalties.

- **PENNY_STOCK class** (equity: PLTR, SOFI, RIVN, LCID, NIO, SNDL + GME, AMC memes):
  - Kimi resolved n=148: WR 6.76% (10 wins / 138 losses), avg_return=-0.8659%, std=4.07%, cum_pnl=-128.15%, Sharpe=-3.3786, Sortino=-1.80, **PF=0.1939** (catastrophic), expectancy=-0.8659%, long_WR 3.76% (short 33% on tiny 15 trades), MaxDD=-129%.
  - Quarantine_manifest: WR 6.76% on n=148 ("noise"), max_risk=0.
  - In EQUITY live: 8/18 tickers (per EQUITY 90d plan); contributes to narrow speculative universe, gap risk (NIO/LCID/RIVN can gap -30-80% on delisting/news), but some AMD/PLTR/SOFI momentum lift hides it. Recent symbol_perf shows AMC 9 trades 8 wins 88.9% +46.99 (again small-n cherry).

- **Overall bucket**: Sub-coin-toss across thousands of trades. Negative expectancy, extreme negative Sharpe, massive drawdowns. High kurtosis/skew (fat tails from gaps/pumps). Dashboard asset_class_health has no entry (intentionally hidden/mixed); effective contribution to EQUITY/CRYPTO realized PnL is drag (inflates vol, eats edge on liquid names via concentration penalties in ml_composite). 150 lowq picks in 3500 recent_closed (~4% but high-impact on quality perception). Meme_long_bear gate exists but 0 triggers (insufficient filter).

**Symbol universe size, liquidity, concentration risk**:
- Static: EQUITY 8 names (6 penny high-beta EV/tech/spec: NIO/LCID/RIVN/SNDL/PLTR/SOFI; 2 meme: GME/AMC). CRYPTO ~9-11 meme (DOGE/SHIB/PEPE/FARTCOIN/BONK/FLOKI/WIF/BRETT/TRUMP + POPCAT/MEW/NEIRO variants in SECTOR_MAP).
- Dynamic: Scanners (volume_surge, community_penny, goldmine_meme, incubator, kimi_tracker, quan_engine) + new launches emit far more (WIF 2799 dashboard occ, DOGE 466; PNUT/POPCAT fresh memes). Total unique lowq >>20.
- Liquidity: **Poor/illiquid by design**. Legacy config comments: "Low liquidity (<$1M vol), prone to pump/dump", "Sub-$1M volume... illiquid". No runtime ADV gate (unlike crypto research proposals). Low float (pennies), thin orderbooks (memes), high slippage on entry/exit. Data fragility (yfinance/stooq fails more on micro-caps; equity_price_failover.py).
- Concentration: In CRYPTO top counts include multiple memes; EQUITY AMD dominates but speculative names add idiosyncratic risk. Violates diversification (one tweet = -50% gap).

**Why this bucket drags EQUITY / CRYPTO / overall stats**:
- Volume illusion: Volatile names = easy "signals" for vol/breakout/volume_surge strats → high emission count → inflates n in CRYPTO (8011) and pollutes EQUITY (420 from 18 narrow). But realized edge negative.
- Hidden in aggregates: Main class PF/WR improved post-resolver-v2 / quality_gates (EQUITY T2-candidate, CRYPTO 1.36), but sub-bucket PF<0.5 drags the "elite" strategies (e.g. in ml_composite source_concentration_penalty, strat_concentration). Kimi/quan/goldmine (historical 18%/7% vol @ PF 0.35-0.70 in CRYPTO autopsy) specialized in memes/pennies.
- Sentiment vs factor: GME/AMC retail frenzy, meme coins twitter/cex pumps — not persistent academic edge (contrast VIX-regime momentum on LC or COT on CT=F). Correlated to noise, not macro/regime.
- From EQUITY 90d: "pennies/memes inflate vol, gaps, correlation to retail sentiment"; research backtests use clean 30 LC (no overlap), live on mixed 18.
- From CRYPTO 90d: ~15% memes in counts, "high % low-liquidity / meme / new alts dilute edge"; M-038 pending.
- System-wide: Contributes to "sub-T2" labels, high MDD tail risk, poor DSR/Wilson on affected strats, leaks past smart_picks (meme_long_bear 0 despite gate).

**Earnings/SEC/fundamentals or on-chain usage**: None meaningful. Pennies: yf wrapper only (no EDGAR 10-K depth, no float/insider for low-cap). Meme coins: on-chain (coinglass funding, dune?) used in some strats but overwhelmed by hype noise; no real "value" factors. Pure technical/sentiment/vol — fails forward (wf_p_value high, failing verdicts).

**Outcome tracking / DB reality**: 3500 recent_closed includes 150 lowq; many WATCH tier, paper_trade=False, after_cost_net missing (slippage not modeled). Quarantine_manifest is source of truth but enforcement in quality_gates.py (BLOCKED_ASSET_STRATEGY_PAIRS etc) + scanner may have gaps (DOGE from quan_engine still in sample). Ghost rows=0 system-wide but lowq historical polluted by kimi synthetic fixtures (1.6M backtest rows fake).

**GitHub Actions / Data flow + recent activity**: Scanners emit → score_booster (ml_ranker uses CATEGORY_MAP penny/meme) → quality_gates (passes_active_gate checks? but class-level blocks in BLOCKED_*) → dashboard. Recent: kimi_edge_audit_2026-05-11 swarm, 5-agent synthesis 2026-05-12, quarantine_manifest 2026-05-12, EQUITY/CRYPTO 90d plans flag it, SUPREME_PLAN queues this. No dedicated sleeve wired.

**Summary baseline**: Far worse than coin toss (PF 0.2-0.5, WR 7-16%, negative Sharpe -2.8 to -3.4, thousands of trades negative expectancy). Small-n "winners" in symbol_perf are survivors bias / noise. Drags main classes via volume bloat + tail risk. Universe illiquid/speculative. Risk params deliberately looser (failure). Already quarantined on paper (0% risk) but needs ruthless enforcement + removal from emitters. Matches "worst categories" user callout. Not Tier anything — Graveyard candidate.

---

## Step 2: Identify the Single Best Pilot Candidate (within PENNY_MEME)

**Filters**: Any sub with PF>1.0 / WR>50% / n≥30 sustained post-noise + explainable non-manipulated edge + liquidity? **None exist**.

- **No pilot recommended**. All evidence (kimi n=1869+148, dashboard recent, quarantine rationale) shows structural negative alpha. "High-vol sleeve" would be pure speculation/gambling, not quant edge (contrast COMMODITY COT real factor or EQUITY VIX-regime on liquid).
- Justification for none: External replication (e.g. meme coin indices, penny ETF backtests, Hyperliquid low-cap, MyFXBook retail meme) also show negative long-term (retail favorite = smart money exit). Academic: low-float anomalies decay fast post-publication; manipulation (wash trading, twitter pumps) not replicable in size. Building sleeve violates "size up where edge best worth the risk" + "institutional/hedge-fund-grade" (Tier 2 min PF>1.5/WR>50/MDD<20).
- Secondary: Research-only hypothesis testing (e.g. extreme vol mean-reversion on >5x ADV spikes with hard 0.5% micro-size + 1d hold max, strict liquidity gate) **only** after 6m+ paper on clean data, DSR>0.95, no leaks. But expectation: still fails (data snooping on noise).
- Gap vs current: EQUITY/CRYPTO still emit via volume/breakout strats on these names (community_penny_volume_surge, penny_volume_breakout, goldmine_meme etc); CATEGORY_RISK allows -15% SL / +35% TP on meme (vs equity -1.5%/+2.5%); no ADV/float/gap circuit breaker.

---

## Step 3: Gap Analysis (PENNY_MEME)

| Gap Type                  | Diagnostic (data-backed)                                                                 | Severity | Typical Fix |
|---------------------------|------------------------------------------------------------------------------------------|----------|-------------|
| Performance (sub-coin-toss, negative expectancy) | MEMECOIN PF 0.499 / WR 15.7% n=1869 (kimi + manifest); PENNY_STOCK WR 6.76% / PF 0.1939 n=148; Sharpe -2.8 to -3.4; cum_pnl -6.7k / -128%; recent DOGE sym_track_wr 29.6% failing. Small-n 100% WR illusions in symbol_perf. | **P0 Critical** | Full class quarantine (already in manifest/gates for MEMECOIN 20+ strats + PENNY deep_oversold); enforce 0% in position_sizer / risk; delete or research-only all emitters. |
| Symbol universe / liquidity (illiquid + low-float manipulation) | 8 equity (PLTR/SOFI/RIVN/LCID/NIO/SNDL/GME/AMC) + 9-11 crypto memes (DOGE/WIF/PEPE etc) + dynamic; low ADV (<$1M comments); no runtime is_liquid() gate (scanner.py:877 loose); WIF 2799 occ, high slippage/gap risk (NIO to zero). | **P0** | Split in config.py: LARGE_CAP_EQUITY (20-30 ADV>$5M) + SPECULATIVE_RESEARCH_ONLY (move 8); CRYPTO LIQUID_25 (exclude memes per M-038); add ADV + float + min_volume gate in production_scanner.py + equity_strategies + crypto paths before emit. Deprecate penny/meme cats. |
| Risk management failures (loose params + no gap/ADV model) | CATEGORY_RISK "meme" (-15% SL / +35% TP / hold 3d), "penny" (-12%/25%/5d) vs "equity" (-1.5%/2.5%/7d); TRAILING_STOP looser; no overnight gap circuit, no low-float ban, no slippage_validator wired (PR#1026 scaffold); CATEGORY_RISK_FAST even tighter but still permissive. | **P0** | Remove or map penny/meme to ultra-tight or BLOCK in CATEGORY_RISK / risk.py; add gap_risk_filter (e.g. no hold if float<10M or ADV<2M or earnings proximity); wire vol-target + ADV-based sizer; hard max 0.1% risk per name. |
| Strategy bloat / toxic emitters | penny_volume_breakout, community_penny_volume_surge (equity_strategies/community_strategies); goldmine_meme, incubator_gainer, meme_signals, kimi_tracker, quan_engine on MEMECOIN (20+ blocked in quality_gates:1919); ml_ranker CATEGORY_MAP treats as distinct but leaks. | **P0** | Block all in BLOCKED_ASSET_STRATEGY_PAIRS + strategy_blocklist.py; prune from _RAW_EQUITY_STRATEGIES / COMMUNITY / baby_strategies; research-only dir for vol_surge ideas. |
| Data quality / synthetic leaks / tracking | Kimi synthetic fixtures (PEPE training leak, 1.6M fake backtest rows); yf/stooq fragile on micro; no PIT for low-cap; resolver noise (similar COT over-emission); at_signal_outcomes incomplete for lowq. | **P1** | Ghost sweep + kimi_tracker full block (already partial); strict data source whitelist for research; DB Freshness + outcome coverage for MEMECOIN/PENNY tables; no synthetic in prod. |
| Hidden regime / factor not applicable | No persistent factor (VIX hurts pennies more per equity_strategies:169 "VIX>30: penny crushed"); sentiment-driven dies in risk-off. Research on clean LC + regime succeeds; here opposite. | **P2** | None for prod; if research, test only VIX>30 short-bias or extreme vol-reversion (paper first). |

**Why PF <<1 and WR<<30%?** Scanners exploit vol (easy breakouts on low-float pumps) but no edge persistence; manipulation + gaps create asymmetric losses (big losers, capped winners); loose risk params designed for "high vol" amplify; historical sources (kimi/goldmine/quan) were synthetic/noisy on this exact bucket; forward tests fail (wf_verdict FAILING, low sym_track_wr); research backtests avoid these names entirely. Data quality > model: noise floor dominates. Matches "data quality > model sophistication" + "prune > add".

---

## Step 4: Decision Framework for Strategies (live >60d)

- **Statistically significant negative alpha (PF<1.0 or WR<40% sustained, n>30 on sub)**: **Delete or hard quarantine** (BLOCKED_ + probation + 0 sizing). **All** penny/meme dedicated or heavy emitters qualify (penny_volume_breakout if low realized; community_penny_volume_surge; goldmine_meme, incubator_gainer, meme_signals, kimi_tracker, quan_engine on MEMECOIN, many more per quality_gates 20+ list).
- **Only keep if survives walk-forward + live paper with real costs + ADV gate**: None currently. Move entire bucket to research-only (hypothesis: "does extreme vol surge + ADX filter work on $10M+ ADV subset?"). No production emissions.
- **Per master (M-038 + EQUITY P0 split + CRYPTO shrink)**: Enforce class-level quarantine; deprecate from EQUITY_SYMBOLS/CRYPTO_SYMBOLS; update size_caps to formal 0%; add to dashboard as QUARANTINED.
- **Strategies to delete/invert/promote (file paths)**:
  - **Quarantine/delete (P0)**: All MEMECOIN/PENNY emitters → `audit_trail/quality_gates.py` (expand BLOCKED_ASSET_STRATEGY_PAIRS + class-wide), `alpha_engine/strategy_blocklist.py`, `config.py` (remove or isolate to RESEARCH_SPECULATIVE_SYMBOLS), `alpha_engine/equity_strategies.py` (deprecate penny_volume_breakout + community_penny), `community_strategies.py`, `ml_ranker.py` (remove or hard-block penny/meme categories in live path), `scanner.py` + `production_scanner.py` (add is_high_risk_low_quality() gate returning []).
  - **Research-only**: Vol surge / breakout ideas in separate baby/research dir; test with strict filters (ADV>$10M, no overnight for pennies, 0.5% micro size).
  - **Promote (in clean classes only)**: VIX/liquidity gates, trust_score, ADV filters from EQUITY/CRYPTO plans.
  - Reference: `quality_gates.py:1919` (MEMECOIN block), `quarantine_manifest.json:9-10` (size_caps 0), `config.py:173` (CATEGORY_RISK), `equity_strategies.py:172` (penny_symbols filter), `non_crypto_quality_gate.py:115`.

---

## Step 5: Leverage AI Keys Intelligently (High-ROI Prompts)

(Per skill: ideation / literature / deconstruction — not prod code.)

**Feature Ideation (PENNY_MEME)**: 
```
Given kimi_edge_audit metrics (MEMECOIN n=1869 PF=0.499 WR=15.7% Sharpe=-2.79; PENNY_STOCK n=148 WR=6.76% PF=0.19) + dashboard recent_closed (150 lowq picks, DOGE sym_track_wr=29.6% failing from quan_engine) + config CATEGORY_RISK looser for meme/penny + community_penny_volume_surge emitting on GME/NIO/WIF + no ADV gate: design 3 concrete production gates (1. liquidity/ADV + float filter, 2. gap_risk overnight ban for <X float, 3. category risk hard map to BLOCK) with pseudocode for scanner.py / quality_gates.py / position_sizer. Quantify expected volume reduction (target -95% lowq emissions) and PF lift on parent EQUITY/CRYPTO (0.1-0.2). Include test against 2026-05-15 dashboard_data recent_closed distribution.
```
(Use for research only; verify with CPCV/DSR on liquid subsets.)

**Deconstruction**: "Why do volume surge strats 'work' in backtest but fail live on pennies/memes?" → Pump/dump + lookahead in low-float data + no slippage model + retail herding decay.

---

## Step 6: 30/60/90 Day Execution Plan (Quarantine & Cleanup)

**30 Days (P0 — Enforce zero-risk quarantine + stop leaks)**:
- Formalize PENNY_STOCK / MEMECOIN as first-class in BLOCKED_ASSET_STRATEGY_PAIRS + BLOCKED_SOURCE_SYSTEMS (expand from quality_gates.py:1919 list of 20+ + penny_deep_oversold); update quarantine_manifest.json with current date + full rationale + rolling stats from kimi.
- In `alpha_engine/config.py`: Create RESEARCH_ONLY_SPECULATIVE_SYMBOLS (move 8 equity penny/meme + all meme coins); add `is_low_quality_or_meme(symbol)` returning True for them + dynamic low-cap heuristic (e.g. yf market_cap < $2B or binance ADV < $5M). Gate in scanner.py:877, production_scanner, equity_strategies (remove penny_symbols loop or return []), community_strategies, ml_ranker live path.
- Wire hard block in `audit_trail/quality_gates.py` + `non_crypto_quality_gate.py` / crypto equivalent (class == "MEMECOIN" or "PENNY_STOCK" or cat in ("penny","meme") → fail gate, 0 conf).
- Update CATEGORY_RISK / TRAILING_STOP: map "penny"/"meme" to BLOCK or ultra-micro (0.1% max, 1d hold, tight 0.5% SL).
- Add ADV + gap filter (e.g. using cached CoinGecko/Binance or yf volume; ban if < threshold or pre-earnings low-float).
- Success: 0 new emissions of lowq symbols in next 30d dashboard recent_closed; quarantine_manifest size_caps enforced in live risk; EQUITY/CRYPTO concentration shifts fully to liquid (AMD/BTC + LC/L1); no "meme_long_bear" needed because upstream block.
- Files: config.py, quality_gates.py, scanner.py, equity_strategies.py, community_strategies.py, production_scanner.py. Small PRs, Wire-Up, swarm review.

**60 Days (P1 — Quantify hidden drag + research hygiene)**:
- Run full autopsy on 2026-02 to 2026-05 lowq emissions: PnL attribution, slippage estimate (5-50bp+ on illiquids), gap loss % (overnight/weekend), source breakdown (kimi/quan/goldmine share of negative).
- Backtest liquidation cost model + realistic fill on these names (use tick data if avail or conservative 0.5-2% roundtrip); re-compute EQUITY/CRYPTO PF with/without lowq volume (expect +0.1-0.25 PF lift, -30-50% vol).
- Prune all lowq strats from baby_strategies / incubator / goldmine families; move vol_surge logic to research/ with strict ADV gate + paper-only.
- Update edge_stability reports, health/ daily, dashboard_generator to tag or exclude PENNY_MEME from asset_class_health (or show as QUARANTINED with red "0 risk" pill).
- 30d paper on any research hypothesis (extreme vol mean-rev on filtered >$10M ADV subset only): target DSR>0.9, no MDD breach, n>50. Expect failure.
- Success: Documented drag quantification (e.g. "PENNY_MEME contributed -X% to EQUITY MDD, Y% volume for -Z% PnL"); zero leaks; master plan M-038 closed as "quarantined, no sleeve".

**90 Days (P2 — Permanent deprecation + dashboard hygiene)**:
- If research paper fails (expected): Delete lowq-specific strats (or archive with "graveyard" tag); remove penny/meme cats from CATEGORY_MAP / SECTOR_MAP; deprecate from any live scanners. Update SUPREME_PLAN / MASTER_ACTION_PLAN_2026-05-15.md Section 21 (mark complete, no future M-0xx for sleeve).
- Dashboard: Add /audit note "PENNY_MEME / MEMECOIN / PENNY_STOCK: Quarantined (research-only, 0% allocation). Historical PF<0.5 / WR<16%. See quarantine_manifest.json." Remove from any dropdown or mark red.
- External validation: Compare to public (e.g. MEME index performance, penny stock survivorship studies, Hyperliquid low-cap books) — confirm no scalable edge.
- If miraculously research succeeds (unlikely, require CPCV + live paper + costs + DSR + corr<0.3 to main + swarm consensus): Propose 0.05-0.1% micro sleeve with draconian rules (max 2 names, 0.5% risk total, 1d max hold, ADV gate, VIX>25 only, full costs model). But bar is Tier-1 on paper first.
- Overall: Bucket contributes 0 to live PnL / risk; EQUITY becomes clean LC + VIX (path to T2+), CRYPTO focused liquid + onchain (T2 lift); system-wide "phenomenal across ALL" advanced by removing toxic waste. No more "Futures / Penny / Meme worse than coin toss".
- Risks avoided: No "high-vol sleeve" gambling; no mutation of dead edge (per MUTATION_THREE_AXIS_PROTOCOL.md — class-level PF<0.5 is kill, not drift); no silent leaks; evidence-first (kimi + manifest + dashboard + code).

**Risks / Anti-patterns avoided**: No revival of negative-alpha bucket via "high vol" story; no new complex ML on noise; no production sizing without 6m+ clean paper + external replication; prune/delete > "fix"; protect main EQUITY/CRYPTO stats; follow AGENTS.md (no auto heavy scripts, swarm for changes, small PRs); respects "mutate-before-kill" (already past kill threshold via data).

**Files to touch (Wire-Up compliant, small focused PRs)**: `audit_dashboard/data/quarantine_manifest.json` (update date/rationale), `audit_trail/quality_gates.py` (expand blocks + class gates), `alpha_engine/config.py` (RESEARCH_ONLY lists + is_low_quality gate + CATEGORY_RISK BLOCK), `alpha_engine/equity_strategies.py` + `community_strategies.py` (deprecate emitters or hard return []), `alpha_engine/scanner.py` + `production_scanner.py` (upstream gate), `alpha_engine/ml_ranker.py` (block categories), `reports/MASTER_ACTION_PLAN_2026-05-15.md` + `SUPREME_PLAN_90days.md` (status close M-038), dashboard_generator / template.html (quarantine pill). Reference kimi_edge_audit_2026-05-11/ for evidence. All via clean branches + peer/swarm review per AGENTS.md.

**Expected impact**: -100% PnL/risk from bucket (was negative); +0.1-0.25 PF / lower MDD/vol on EQUITY (clean 15-20 LC) and CRYPTO (25 liquid); reduced false signals / concentration penalties; cleaner n in dashboard (less 150 lowq noise); institutional-grade hygiene (no sub-7% WR buckets). Positions system for Tier-2+ across classes without toxic drag. Avoids FOREX/PENNY trap of slow bleed.

**Next**: No deep-dive subagent for "sleeve design" (edge falsified). If user requests external replication (e.g. specific meme mean-rev paper), spawn then. Update links in updates/index.html + findtorontoevents.ca/audit after PR. Prioritize COMMODITY real-money + EQUITY VIX wire + ETF sector rotation.

**References** (absolute paths):
- Data: `/mnt/e/findtorontoevents_antigravity.ca/audit_dashboard/data/quarantine_manifest.json`, `/mnt/e/findtorontoevents_antigravity.ca/audit_dashboard/data/dashboard_data.json` (symbol_performance, recent_closed, smart_picks_feed), `/mnt/e/findtorontoevents_antigravity.ca/reports/kimi_edge_audit_2026-05-11/metrics_by_asset_class.csv` (MEMECOIN/PENNY_STOCK rows), `/mnt/e/findtorontoevents_antigravity.ca/reports/kimi_edge_audit_2026-05-11/raw_picks_clean.csv`, rolling_MEMECOIN.png, rolling_PENNY_STOCK.png
- Master/Code: `/mnt/e/findtorontoevents_antigravity.ca/audit_trail/quality_gates.py:1919` (MEMECOIN class-wide + 20+ blocks), `alpha_engine/config.py:173` (CATEGORY_RISK meme/penny), `587` (EQUITY_SYMBOLS), `alpha_engine/equity_strategies.py:160` (penny_volume_breakout + penny_symbols), `alpha_engine/community_strategies.py:631` (community_penny_volume_surge), `ml_ranker.py:420`, `scanner.py`
- Reports: `/mnt/e/findtorontoevents_antigravity.ca/reports/asset_class_90day_plan_EQUITY_2026-05-15.md` (universe quality + P0 split), `/mnt/e/findtorontoevents_antigravity.ca/reports/asset_class_90day_plan_CRYPTO_2026-05-15.md` (M-038 + liquidity), `SUPREME_PLAN_90days.md`, `grok_money_maker_audit_transcript_2026-05-15.md` (queued + "worse than coin toss")
- Other: `reports/kimi_edge_audit_2026-05-11/comprehensive_analysis_report.md`, `audit_dashboard/data/edge_stability/edge_stability_EQUITY.json`, `edge_stability_CRYPTO.json`

This plan is ruthless, data-driven, and decisive: the PENNY_MEME bucket is not "high-risk high-reward" — it is high-risk negative-reward noise that has no place in production. Quarantine permanently. Quality (liquid, factor-driven, evidence-backed) over quantity (vol on memes/pennies). One class (or bucket) done right advances Goal #1 phenomenal /audit performance across ALL assets. Follows AGENTS.md / CLAUDE.md / SOUL.md / every-session reads + money-maker-continual-improve.

---
*Generated 2026-05-15 per money-maker-continual-improve skill invocation on Low-Quality Equities (Penny Stocks + Meme Coins) audit. System pilot remains COMMODITY (COT real edge); this is high-risk bucket quarantine plan (no sleeve). Follows AGENTS.md / CLAUDE.md / SOUL.md / memory/2026-05-15.md + skill.*