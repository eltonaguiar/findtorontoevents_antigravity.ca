# thingstocheck_June2026 — Full Audit Review of Trading Prediction Edge, Pages, DBs, and Picks Performance

**Trigger:** `/thingstocheck_June2026` or "run thingstocheck June2026" or the full prompt below.

**Purpose:** Comprehensive review of why no high-certainty (even tiny) profitable picks per asset class on the trading prediction system (stocks/crypto/forex/bonds/etfs/commodities/futures + plans for meme/cheap/penny/IPO/copytrader/prediction markets). Review all key /audit/ webpages, buttons, filters, tabs for hidden edge or bugs. Debug performance (FWD WR% vs strategy WR, 21.1% on picks-now, gpt4_1 55.6% verify, kimi bias, stale pages, synthetic data, reverse splits, limits, etc.). Use DBs safely (backup first), source code, live pages, previous velocity/HF tactics, money-maker skills. Produce PLAN_INSIGHTS_GROK_...MD + update main reports grok MD + todos progress. Goal #1 priority.

**Full prompt to execute (verbatim from user):**
We are a trading prediction github , which tries to predict stocks/crypto/forex/bonds/etfs/commodities/futures .. however ,  
it seems we dont have anything with a high certainty of a profit.. even if a tiny profit.. which is very bad.  we also have  
https://findtorontoevents.ca/audit/picks-now.html where we try to use valuation and other factors to come up with the best   
possible picks now.  we have databases mysql.50webs.com ejaguiar1_stocks ejaguiar1_backtests and ejaguiar1_backups (backups  
are for descrutive db operations we would make a backup there first) .. db passes are here:                                  
/home/eaguiar2015/dbpasses.txt                                                                                               
                                                                                                                               
  We also had concepts such as copytrader/ prediction markets like Kalshi/Polymarket..    we even had meme coins, cheap        
  stocks, penny stocks, etc or at least plans for those and also IPOs ..                                                       
                                                                                                                               
  have a review of our key webpages https://findtorontoevents.ca/audit/ and their various buttons, filters, and see if we have 
  a hidden edge, and if not, debug why we dont have any profitable picks per asset class.. not even for a single asset class!  
   We have been working months on this..  any insights you have put into a PLAN_INSIGHTS_<MODEL>_<DATE>_<TIME>.MD so a         
  date/time EST simply like PLAN_INSIGHTS_CURSOR_June122026_224pm.MD  something like that.. although if it exists, just add an 
  _A at the end before file extension or _B etc. to ensure uniqueness.                                                         
                                                                                                                               
  key webpages https://findtorontoevents.ca/audit/ -- > "high-conviction picks" was once our top edge, or so we thought, but   
  we also have a "smart picks" tab, "smart picks button" , we had a "proven only" button, a "best score" button. under the     
  "star" tab, we have active picks, that are supposed to show their FWD WR% and track record, etc, it seems often this         
  tracking is lost and shows the STRATEGY win-rate rather then the STRATEGY-SYMBOL-DIRECTION win-rate. something like that..   
  have a look at our active picks, and recently closed picks, are they mostly winning? losing? we also had a section called    
  "verified alpha" and a tab called "smart picks" a tab called "US Equity picks",  and within that tab there is "long-term     
  value" "swing plays" "Closed holds" we also had "portfolios" tab , but it appears that is stale? please confirm              
  https://findtorontoevents.ca/audit/portfolio_history.html and if so deteremine why its stale, and whether its worth to       
  ressurect that or leave it. Is there an edge buried somewhere on findtorontoevents.ca/audit  amongst all the combinations of 
  filters, button clicks tabs etc? we had tried to make a page to answer that                                                  
  https://findtorontoevents.ca/audit/pick_funnel.html , but check if that page is accurate. we also had                        
  https://findtorontoevents.ca/audit/ai_leaderboard.html which attempted to find us winning model picks,it seems stale as only 
  claude-opus-4.7 has data.. why? we had https://findtorontoevents.ca/audit/research_index.html , are we leveraging that       
  research? another key page is https://findtorontoevents.ca/audit/ai-tournament.html ... everything there is labelled as NOT  
  MONEY-ready why! we had picks from a TON of AI models.. the best appears to be kimi_direct and gpt4_1 it seems kimi_direct   
  was biased due to a single snapshot resolver, so maybe we need to backfill or fix that,. or nuke the old data and start      
  fresh for that? we also had gpt4_1 it claims a 55.6% win-rate is that actually true? double-check in detail and confirm.     
  we need to avoid mistakes like strategies with reverse stock splits causing wrong numbers, or our limits such as # of active 
  pick limits, causing incorrect data.  ,  under that page we also had a Model Portfolios — Risk-Managed Books , seems a ton   
  of losing portfolios! why, leverage our AI swarm as needed /peerreviewswarmoptions  . save this prompt as a                  
  /thingstocheck_June2026 skill and slash command ,  also this https://findtorontoevents.ca/audit/picks-now.html should be our 
  best possible picks we could make now, consider also concepts like this                                                      
  https://github.com/starboi-63/growth-stock-screener?tab=readme-ov-file in terms of finding us good picks, lets ensure we     
  have the pick performance tracked properly. that page has a  FORWARD-TESTED PERFORMANCE  , with a measly 21.1% win-rate      
  which is HORRIBLE! investigate why , and lets get that fixed

**How to use (workflow):**
- Invoke skill: follow exactly (read this + use money-maker-ready-June112026edition, audit-pick-flow, large-repo-read, verification-before-completion, hypothesis-registry, db-schema).
- 1. Create/update todos (based on latest grok deep-dive Pass + this).
- 2. Fetch/analyze live pages (web_fetch/open_page on all listed).
- 3. Source code review (template.html, manifest 47 buttons/17 tabs/31 filters, quality_gates active/smart/HC/MR, dashboard_generator, money_ready_verdict, pf_registry, edge_finder, stamp, june candidates, config BLACKLIST, resolver, production_scanner, feature_populator; use sed/grep/python targeted).
- 4. DB safe: tools/db_env.py + backup to ejaguiar1_backups first for any write; targeted queries on at_raw_picks/at_signal_outcomes/at_filter_log/trading_picks etc for per-class/symbol-dir WR/PF/n (vs strat only), active/closed, FWD, concentration, NULL/mispriced/ghost (post fixes), recency. Use schema from docs/DB_SCHEMA_*.md.
- 5. Concepts: copytrader, Polymarket/Kalshi signals, meme/cheap/penny/IPO, growth-stock-screener integration for equity.
- 6. Debug specific: picks-now 21.1% WR root (methodology vs gates, adverse, entry, data quality, reverse splits, limits); ai-tournament NOT MONEY-ready + synthetic (kimi 49%, cursor 100%, gpt4_1 verify 55.6%?); ai_leaderboard stale (only claude-opus); portfolio_history stale (why, value?); pick_funnel accuracy + disputed CRYPTO 78.9% vs raw 39%; research_index NO_EDGE mostly (small n); active FWD WR% loss to strat WR; hidden edge in filter combos?
- 7. Insights/plan in reports/PLAN_INSIGHTS_GROK_June122026_<time>EST.MD (add _A etc unique); append summary to main grok4-3-quant-deep-dive...md as Pass 68 (with HF tactics applied: velocity on 1774+1134, pre-reg, adverse kill from granular, stamp F wire, COT, TWR/attr, recency enforce, 4h sprint continuation, COM priority).
- 8. Verif before claims: run+read py_compile, JSON loads, grep, page status, safe DB queries, etc.
- Leverage swarm/peerreviewswarmoptions for multi-AI review of findings/bugs.
- Output: todos progress, skill created, PLAN MD, updated grok MD, actionable plan (fix generators, clean synthetic, enforce recency/conc, wire velocity/stamp, integrate screener, DB hygiene, paper on admissible, etc.). Goal #1. Read-only unless backup+safe. No generators.

**References (from context):** Previous Pass 67 (Grok picks autopsy, per-class with futures_mom n61/50.8/1.586 + stamp retention, HF 12pt FAST: velocity 50-100x, pre-reg M-107, stop bleeder, shadow MONITORED T1 sleeves, entry stamp F>>exit, adverse explicit kill vol/regime/alpha first, monkey/stress/AddH n_eff/CI before size, COT lag3, TWR/attr, 14d/48h first, 2-3 focus COM, ratchet, 4h sprints, paper admissible, hostile verif). master loop, sprint-refine, velocity MD, stamp.py:98-165, june.py, entry 1134, verdict 04:47Z (0 classes T2), pf COM 31/58/2.04 but small, tier drags, granular adverse, recency 06-05 stale.

Follow skills exactly. Evidence (asset_class | n | timeframe) + file:line/JSON. Verification iron law. Coord peers. Update memory if sig. 

**End of skill.** (This file created 2026-06-12 per user request to save the prompt as skill+command.)