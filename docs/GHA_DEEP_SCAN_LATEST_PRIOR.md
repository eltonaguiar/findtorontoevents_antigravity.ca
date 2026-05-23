# GitHub Actions deep scan (latest + prior on failure)

Generated: **2026-04-16 18:48 UTC**

## Method

- **Repo:** `eltonaguiar/findtorontoevents_antigravity.ca`
- **Branch:** `main`
- **Discovery:** workflows seen in the last **24h** among the **250** newest runs.
- **Runs per workflow:** **latest** always; **if latest is `completed` and not `success`/`skipped`,** also the **previous** run.
- **Logs:** `gh run view --log-failed` first; if empty, tail of full `--log`.
- **Shards:** merged from parallel runs (part 0 + part 1)

## Summary table

| Workflow | Latest | Prior (if scanned) | Signal hits (latest) |
|----------|--------|--------------------|----------------------|
| [torontoevent.net] Deploy Rise of the Claw | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527293101) | — | 2 hit(s) |
| [torontoevent.net] Goldmine Tracker - Archive & Maintain | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527156848) | — | 0 hits |
| [torontoevent.net] Rapid Validation Engine | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527694815) | — | 2 hit(s) |
| [torontoevent.net] Run Backtests & Deploy Dashboards | [- / in_progress](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527702003) | — | 0 hits |
| [torontoevent.net] Spike Scanner | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527334509) | — | 0 hits |
| ALPHA  Verify Predictions | [- / in_progress](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527951908) | — | 0 hits |
| ALPHA ENGINE - Dynamic Runner (Cloud or Local) | [- / pending](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527800989) | — | 0 hits |
| ALPHA ENGINE - Incubator Strategies | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527696978) | — | 2 hit(s) |
| ALPHA ENGINE - Live Autonomous Scanner | [- / in_progress](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527372635) | — | 0 hits |
| ALPHA ENGINE - Quant Stack (KAMA + ATR + Regime) | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527460785) | — | 3 hit(s) |
| ALPHA ENGINE - Universe Expander | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24523987327) | — | 2 hit(s) |
| ALPHA ENGINE FAST Tighter TP/SL, Shorter Holds | [- / in_progress](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527463068) | — | 0 hits |
| ALPHA ENGINE Gainer Capture (15min) | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527542667) | — | 2 hit(s) |
| Analyst Tracker  Top 20 Crypto Analysts | [skipped / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526967300) | — | 0 hits |
| ANTIGRAVITY ML  Hourly Discord Status + Picks | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526977785) | — | 2 hit(s) |
| ANTIGRAVITY-CLAUDEOPUS  Live Picks & Discord | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527287815) | — | 2 hit(s) |
| AsterDEX Paper Trading | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527498779) | — | 2 hit(s) |
| Audit Drift Telemetry | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527552041) | — | 2 hit(s) |
| Audit Impact Tracker | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526787959) | — | 2 hit(s) |
| Baby Strat Real Forward Monitor | [- / in_progress](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527689670) | — | 0 hits |
| Backfill Missing Audit Trail Sources | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527246630) | — | 2 hit(s) |
| Breakout Arena  3 Approaches | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527521448) | — | 2 hit(s) |
| Buy Now Analysis & Tracking | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527126348) | — | 2 hit(s) |
| Check Streamer Live Status | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526900107) | — | 2 hit(s) |
| CI Tests | [- / in_progress](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527927111) | — | 0 hits |
| Claude Gainer ML  Live Scanner | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527626441) | — | 3 hit(s) |
| Claude Gainer Short-Term Predictor | [- / in_progress](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527505847) | — | 0 hits |
| Coinglass DNA Scanner | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527491854) | — | 2 hit(s) |
| Conflict Marker Check | [- / in_progress](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527927089) | — | 0 hits |
| Consensus Outcome Tracker | [cancelled / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527045714) | [cancelled](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24524564588) | 4 hit(s) |
| Contested Pick Checker (Claude vs Antigravity) | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527315850) | — | 7 hit(s) |
| Conviction Picks Ultra-Selective Discord Alert | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526619131) | — | 4 hit(s) |
| Copy Trader Forward Test | [- / in_progress](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527772251) | — | 0 hits |
| Copy Trader Intelligence  Scrape + Analyze + Track | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526551492) | — | 3 hit(s) |
| Copy Trader Portfolio Tracker | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24523526046) | — | 2 hit(s) |
| Cross-Asset Correlation Monitor | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527696167) | — | 2 hit(s) |
| Cross-System Signal Aggregator | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527526278) | — | 2 hit(s) |
| Crypto Gainer ML Live Tracker | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526727097) | — | 2 hit(s) |
| Crypto ML Edge GSD Scanner | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527152125) | — | 2 hit(s) |
| Crypto Signal Engine | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527327900) | — | 2 hit(s) |
| CRYPTO SMART PICKS - Portfolio A/B/C/D Scanner | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24523804396) | — | 2 hit(s) |
| Crypto Winner Scanner  Auto Scan | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527163971) | — | 0 hits |
| Daily Feed Summary | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526697150) | — | 2 hit(s) |
| DARWIN ENGINE - DNA Evolution Pipeline | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526950663) | — | 2 hit(s) |
| Dashboard Pick Trader | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526187035) | — | 5 hit(s) |
| Data Pipeline Reliability Test | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527288845) | — | 2 hit(s) |
| Deploy Battleground to FTP | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24523671674) | — | 2 hit(s) |
| Deploy Competition to Live Site | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527780727) | — | 2 hit(s) |
| Deploy FindCryptoPairs to FTP | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527691177) | — | 2 hit(s) |
| Deploy MOVIESHOWS2 + MOVIESHOWS3 (All 3 Domains) | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527552693) | — | 2 hit(s) |
| Deploy Rise of the Claw Dashboard | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527014074) | — | 2 hit(s) |
| Discord Bot  Persistent | [- / in_progress](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527446176) | — | 0 hits |
| Discord ML Status Report | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527051216) | — | 2 hit(s) |
| DNA Genome Daily Pipeline | [- / in_progress](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526740896) | — | 0 hits |
| EMA Retracement Mean Reversion Scanner | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527619278) | — | 2 hit(s) |
| Enhanced ML Crypto Train & Predict | [- / in_progress](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527730704) | — | 0 hits |
| FC-CRYPTO PRO Top Actionable Picks | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527459655) | — | 2 hit(s) |
| Feed Health Check | [- / in_progress](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527931095) | — | 0 hits |
| Fix Battleground Deployment | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24523671656) | — | 4 hit(s) |
| Forex Agent | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24524371833) | — | 3 hit(s) |
| Forex Smart Picks Scanner | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526742659) | — | 2 hit(s) |
| Forward Signal Scanner | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526870556) | — | 2 hit(s) |
| Forward Trade Tracking v2 | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526921107) | — | 2 hit(s) |
| Forward-Test New Strategies Tracker | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526710872) | — | 2 hit(s) |
| Gainer Predictor Scanner | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527339871) | — | 2 hit(s) |
| Goldmine Tracker - Archive & Maintain | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527198769) | — | 0 hits |
| Hindsight Learner  Hourly Winner Analysis | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527494185) | — | 2 hit(s) |
| Hoffman IRB Strategy Tracker | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527076059) | — | 2 hit(s) |
| Hourly Master Picks to Discord | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527489476) | — | 2 hit(s) |
| Hub Data Sync | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527849217) | — | 3 hit(s) |
| KIMI Goldmine Data Collection | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527099221) | — | 2 hit(s) |
| KIMI_FEB172026 - Live Trading System | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526946515) | — | 2 hit(s) |
| Live Picks Tracker | [- / in_progress](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527879218) | — | 0 hits |
| Live Trading Monitor  Auto Refresh | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24525966757) | — | 19 hit(s) |
| Low-Score Winner Tracker | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527496439) | — | 2 hit(s) |
| LuxAlgo Signal Generator | [- / in_progress](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527905682) | — | 0 hits |
| Market Beating System - Crypto & Forex Priority | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527199994) | — | 2 hit(s) |
| Master Automation Scheduler | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526825943) | — | 3 hit(s) |
| Mega Mutation Live Tracker | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526292713) | — | 2 hit(s) |
| Meme Coin Scanner Auto Scan & Resolve | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526954553) | — | 2 hit(s) |
| Meme Coin Scanner v2  Fixed & Monitored | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527538051) | — | 2 hit(s) |
| Mercury 2  Signal Scanner | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24525743796) | — | 2 hit(s) |
| Meta-Strategy Permutation Engine | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527797288) | — | 2 hit(s) |
| Mirror: findtorontoevents.ca  torontoevent.net | [- / in_progress](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526892351) | — | 0 hits |
| Missed Opportunity Analyzer Hourly Self-Improvement | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527812901) | — | 2 hit(s) |
| ML Battleground System F (Claws of Doom) | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526350305) | — | 2 hit(s) |
| ML Crypto  Discord Hourly Status | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527084524) | — | 2 hit(s) |
| ML Feedback Loop | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527077157) | — | 3 hit(s) |
| ML Model Auto-Training | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527353891) | — | 2 hit(s) |
| ML Strategy Reviver Bridge & Standalone | [- / in_progress](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527926226) | — | 0 hits |
| ML System Health Monitor | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527078580) | — | 2 hit(s) |
| MOMENTUM CATCHER - Real-time Pump Detector | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527271439) | — | 3 hit(s) |
| MOMENTUM TRACKER - Real-Time Gainer Scanner | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24525805221) | — | 2 hit(s) |
| Multi-Asset Copytrader Scanner v2  Forex/Futures/Stocks/Commodities | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527319847) | — | 2 hit(s) |
| Mutation Lab  Strategy Evolution Pipeline | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526805282) | — | 2 hit(s) |
| MySQL Trading Picks Sync | [- / in_progress](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24528090792) | — | 0 hits |
| OBI Hourly Snapshot | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24525620571) | — | 2 hit(s) |
| Outcome Resolver  Validate Unresolved Picks | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527582125) | — | 2 hit(s) |
| Pick Monitor & Price Validator (30min) | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526698444) | — | 2 hit(s) |
| Pine Script Generator | [skipped / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527226891) | — | 0 hits |
| Polymarket Prediction Market Signals | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527625955) | — | 2 hit(s) |
| Portfolio Trackers (Real Money + Theory) | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527659606) | — | 2 hit(s) |
| Prediction Market Agents | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527696055) | — | 2 hit(s) |
| Prediction Quality Tracker | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526207107) | — | 2 hit(s) |
| Proven Strategies Scanner | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526878799) | — | 2 hit(s) |
| QUAN ENGINE - Live Autonomous Scanner | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527429546) | — | 3 hit(s) |
| QuantumFusion Crypto Engine | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527176355) | — | 2 hit(s) |
| Quick Guess ML Agent | [cancelled / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527537305) | [cancelled](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24525009553) | 4 hit(s) |
| Rapid Fire - NOW Scanner | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527655948) | — | 3 hit(s) |
| Real-Time Battle Test - Eliminate Losers, Optimize Winners | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527197115) | — | 2 hit(s) |
| Recommended Portfolio Generator | [- / in_progress](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24528072515) | — | 0 hits |
| Refresh Top Movies Data | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527428933) | — | 15 hit(s) |
| Regime Terminal  HMM Live Scanner | [- / in_progress](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24528055782) | — | 0 hits |
| Run Backtests & Deploy Dashboards | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526988058) | — | 2 hit(s) |
| Send Accountability Reminders | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526874460) | — | 0 hits |
| Signal Integrator - Isolated Source Aggregator | [- / in_progress](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527655699) | — | 0 hits |
| Signal Quality Monitor | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527633915) | — | 2 hit(s) |
| Signal Recorder | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526337700) | — | 6 hit(s) |
| Signal Tracking & Validation - Beat the Market | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526852966) | — | 2 hit(s) |
| Skyrocket Detector  Live Scanner | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24525773385) | — | 2 hit(s) |
| Smart Picks Tracker | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526607370) | — | 2 hit(s) |
| Specialized Scanners - Rocket, Short Engine, TSMOM | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24524677383) | — | 2 hit(s) |
| Spike Scanner | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526896060) | — | 0 hits |
| Sports Betting  Odds Refresh & Auto-Settle | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526714447) | — | 0 hits |
| Strategy Forward Tester | [- / in_progress](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527624992) | — | 0 hits |
| Strategy Genome Evolution | [- / in_progress](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527654815) | — | 0 hits |
| SUPERPOWERS - Bootstrap All 3 ML Systems | [- / in_progress](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527185464) | — | 0 hits |
| Sustained Gainer Confluence Scanner | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527618414) | — | 2 hit(s) |
| System Health Check | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527286198) | — | 2 hit(s) |
| Test Portfolios  Hourly Strategy Validation | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527852846) | — | 2 hit(s) |
| Top Gainers Spike Scanner | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527432809) | — | 3 hit(s) |
| TV Paper TP/SL Watchdog | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527735597) | — | 2 hit(s) |
| Unified Audit Dashboard | [- / pending](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527927103) | — | 0 hits |
| Update Creator News | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527280242) | — | 0 hits |
| VOLATILE ALT SCANNER Hyperliquid High-Vol Alts | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527462857) | — | 2 hit(s) |
| Winner Pattern Precursor Scanner | [success / completed](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527856166) | — | 2 hit(s) |

## Detailed excerpts

### [torontoevent.net] Deploy Rise of the Claw — **latest** (success / completed) [run 24527293101](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527293101)

Signal lines:

```text
deploy	Post Checkout repository	2026-04-16T18:39:40.6682839Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
deploy	Post Checkout repository	2026-04-16T18:39:40.6939581Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### [torontoevent.net] Goldmine Tracker - Archive & Maintain — **latest** (success / completed) [run 24527156848](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527156848)

*No signal regex hits; last 25 log lines:*

```text
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:30:09.8293800Z [36;1mecho " Current alerts..."[0m
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:30:09.8294783Z [36;1mALERTS=$(curl -sf --max-time 10 \[0m
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:30:09.8296214Z [36;1m  "https://torontoevent.net/live-monitor/api/goldmine_tracker.php?action=alerts" \[0m
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:30:09.8297604Z [36;1m  2>&1 || echo '{"ok":false}')[0m
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:30:09.8299821Z [36;1mALERT_COUNT=$(echo "$ALERTS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('active_count','?'))" 2>/dev/null || echo "?")[0m
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:30:09.8301811Z [36;1mecho "Active alerts: $ALERT_COUNT"[0m
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:30:09.8302759Z [36;1m[0m
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:30:09.8303497Z [36;1mecho ""[0m
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:30:09.8304504Z [36;1mecho " Goldmine tracker maintenance complete on torontoevent.net"[0m
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:30:09.8525190Z shell: /usr/bin/bash -e {0}
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:30:09.8526591Z ##[endgroup]
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:30:09.8748031Z  Triggering goldmine tracker archive + outcomes on torontoevent.net...
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:30:10.2102640Z Archive response: {"ok":false,"error":"timeout or blocked"}
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:30:10.2103866Z 
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:30:10.2104288Z  Running maintenance tasks...
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:30:10.5259784Z Maintenance response: {"status":{"stale_sports_picks":0,"stale_meme_picks":0,"stale_penny_picks":0,"consolidated_missing_price":0,"active_alerts":10,"duplicate_alerts":0},"expire":{"sports_expired":0,"meme_expired":0,"other_expired":0,"consolidated_missing_prices":[]},"prices":{"fixed":0,"failed":[],"details":[]},"alerts":{"duplicates_resolved":0,"remaining_active":[{"source_system":"portfolio","alert_type":"systemic_failure","severity":"warning","title":"Portfolio: 2 systems underperforming","alert_date":"2026-02-16"},{"source_system":"sports","alert_type":"stale_data","severity":"warning","title":"sports: 4 days since last pick","alert_date":"2026-02-16"},{"source_system":"meme","alert_type":"stale_data","severity":"warning","title":"meme: 4 days since last pick","alert_date":"2026-02-16"},{"source_system":"meme","alert_type":"losing_streak","severity":"warning","title":"meme: 6 consecutive losses","alert_date":"2026-02-16"},{"source_system":"edge","alert_type":"stale_data","severity":"warning","title":"edge: 6 days since last pick","alert_date":"2026-02-16"},{"source_system":"live_signal","alert_type":"algo_underperform","severity":"warning","title":"live_signal: Algorithm \"Consensus\" underperforming (24.2% win rate)","alert_date":"2026-02-16"},{"source_system":"consolidated","alert_type":"negative_roi","severity":"warning","title":"consolidated: Average return negative (-3.3%)","alert_date":"2026-02-16"},{"source_system":"live_signal","alert_type":"losing_streak","severity":"critical","title":"live_signal: 11 consecutive losses","alert_date":"2026-02-16"},{"source_system":"meme","alert_type":"algo_underperform","severity":"critical","title":"meme: Algorithm \"Meme Scanner\" failing (0% win rate)","alert_date":"2026-02-16"},{"source_system":"consolidated","alert_type":"accuracy_drop","severity":"critical","title":"consolidated: Win rate critically low (11.1%)","alert_date":"2026-02-16"}],"remaining_count":10},"ok":true,"action":"run","dry_run":false,"timestamp":"2026-04-16 18:30:10"}
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:30:10.5271528Z 
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:30:10.5271856Z  Final status check...
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:30:10.8101416Z Status: {"status":{"stale_sports_picks":0,"stale_meme_picks":0,"stale_penny_picks":0,"consolidated_missing_price":0,"active_alerts":10,"duplicate_alerts":0},"ok":true,"action":"status","dry_run":false,"timestamp":"2026-04-16 18:30:10"}
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:30:10.8104768Z 
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:30:10.8105301Z  Current alerts...
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:30:11.0603029Z Active alerts: ?
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:30:11.0604006Z 
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:30:11.0605091Z  Goldmine tracker maintenance complete on torontoevent.net
track-and-maintain	Complete job	﻿2026-04-16T18:30:11.0746042Z Cleaning up orphan processes
```

### [torontoevent.net] Rapid Validation Engine — **latest** (success / completed) [run 24527694815](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527694815)

Signal lines:

```text
rapid-validation	Post Checkout repository	2026-04-16T18:44:43.0398969Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
rapid-validation	Post Checkout repository	2026-04-16T18:44:43.0644835Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### [torontoevent.net] Run Backtests & Deploy Dashboards — **latest** (- / in_progress) [run 24527702003](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527702003)

*No signal regex hits; last 25 log lines:*

```text
run 24527702003 is still in progress; logs will be available when it is complete
```

### [torontoevent.net] Spike Scanner — **latest** (success / completed) [run 24527334509](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527334509)

*No signal regex hits; last 25 log lines:*

```text
scan	Trigger Spike Scan	2026-04-16T18:34:08.2234338Z ##[endgroup]
scan	Trigger Spike Scan	2026-04-16T18:34:09.2255109Z Spike scan triggered on torontoevent.net
scan	Trigger Pattern Build	﻿2026-04-16T18:34:09.2549836Z ##[group]Run curl -s "https://torontoevent.net/live-monitor/api/pair_fingerprint.php?action=build&key=livetrader2026" || true
scan	Trigger Pattern Build	2026-04-16T18:34:09.2552920Z [36;1mcurl -s "https://torontoevent.net/live-monitor/api/pair_fingerprint.php?action=build&key=livetrader2026" || true[0m
scan	Trigger Pattern Build	2026-04-16T18:34:09.2555516Z [36;1mecho "Pattern build triggered on torontoevent.net"[0m
scan	Trigger Pattern Build	2026-04-16T18:34:09.2593930Z shell: /usr/bin/bash -e {0}
scan	Trigger Pattern Build	2026-04-16T18:34:09.2594883Z ##[endgroup]
scan	Trigger Pattern Build	2026-04-16T18:34:09.9858661Z Pattern build triggered on torontoevent.net
scan	Wait for processing	﻿2026-04-16T18:34:09.9970307Z ##[group]Run sleep 30
scan	Wait for processing	2026-04-16T18:34:09.9972293Z [36;1msleep 30[0m
scan	Wait for processing	2026-04-16T18:34:10.0013320Z shell: /usr/bin/bash -e {0}
scan	Wait for processing	2026-04-16T18:34:10.0015793Z ##[endgroup]
scan	Check Status	﻿2026-04-16T18:34:40.0195751Z ##[group]Run echo "Spike Scanner Status (torontoevent.net):"
scan	Check Status	2026-04-16T18:34:40.0196652Z [36;1mecho "Spike Scanner Status (torontoevent.net):"[0m
scan	Check Status	2026-04-16T18:34:40.0197796Z [36;1mcurl -s "https://torontoevent.net/live-monitor/api/spike_scanner.php?action=status" | head -c 500[0m
scan	Check Status	2026-04-16T18:34:40.0198659Z [36;1mecho ""[0m
scan	Check Status	2026-04-16T18:34:40.0199172Z [36;1mecho "Pair Fingerprint Status (torontoevent.net):"[0m
scan	Check Status	2026-04-16T18:34:40.0200155Z [36;1mcurl -s "https://torontoevent.net/live-monitor/api/pair_fingerprint.php?action=status" | head -c 500[0m
scan	Check Status	2026-04-16T18:34:40.0236581Z shell: /usr/bin/bash -e {0}
scan	Check Status	2026-04-16T18:34:40.0237105Z ##[endgroup]
scan	Check Status	2026-04-16T18:34:40.0304816Z Spike Scanner Status (torontoevent.net):
scan	Check Status	2026-04-16T18:34:40.3499324Z {"ok":true,"engine":"Multi-Asset Spike Scanner","version":"CURSORCODE_Feb152026","active_spikes":328,"total_scans":328,"baselines":198,"last_scan":"2026-04-03 11:46:46","breakdown":[{"asset_class":"STOCK","severity":"ALERT","cnt":"45"},{"asset_class":"STOCK","severity":"URGENT","cnt":"4"},{"asset_class":"STOCK","severity":"WATCH","cnt":"279"}],"asset_classes":["CRYPTO","STOCK","FOREX"],"methodology":"Real-time volume + price spike detection calibrated per-pair using EWMA baselines. Similar to co
scan	Check Status	2026-04-16T18:34:40.3506114Z Pair Fingerprint Status (torontoevent.net):
scan	Check Status	2026-04-16T18:34:40.9410451Z {"ok":true,"engine":"Pair Fingerprint Engine","version":"CURSORCODE_Feb152026","fingerprints":37,"active_alerts":0,"last_build":"2026-02-17 09:37:17","last_scan":"never","asset_breakdown":[{"asset_class":"CRYPTO","pairs":"27","avg_wr":0},{"asset_class":"FOREX","pairs":"8","avg_wr":0},{"asset_class":"STOCK","pairs":"2","avg_wr":0}],"methodology":"Per-pair behavioral profiling. Unlike generic indicator strategies, this engine studies each asset's unique patterns: mean-reversion tendency, momentum 
scan	Complete job	﻿2026-04-16T18:34:40.9495678Z Cleaning up orphan processes
```

### ALPHA  Verify Predictions — **latest** (- / in_progress) [run 24527951908](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527951908)

*No signal regex hits; last 25 log lines:*

```text
run 24527951908 is still in progress; logs will be available when it is complete
```

### ALPHA ENGINE - Dynamic Runner (Cloud or Local) — **latest** (- / pending) [run 24527800989](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527800989)

*No signal regex hits; last 25 log lines:*

```text
run 24527800989 is still in progress; logs will be available when it is complete
```

### ALPHA ENGINE - Incubator Strategies — **latest** (success / completed) [run 24527696978](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527696978)

Signal lines:

```text
incubator-scan	Post Checkout repository	2026-04-16T18:45:01.4659334Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
incubator-scan	Post Checkout repository	2026-04-16T18:45:01.4901709Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### ALPHA ENGINE - Live Autonomous Scanner — **latest** (- / in_progress) [run 24527372635](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527372635)

*No signal regex hits; last 25 log lines:*

```text
run 24527372635 is still in progress; logs will be available when it is complete
```

### ALPHA ENGINE - Quant Stack (KAMA + ATR + Regime) — **latest** (success / completed) [run 24527460785](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527460785)

Signal lines:

```text
quant-stack	Commit and push data changes	2026-04-16T18:39:52.2062359Z [36;1m  git pull --rebase --no-recurse-submodules -X theirs origin main 2>/dev/null || {[0m
quant-stack	Post Checkout repository	2026-04-16T18:39:52.5205354Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
quant-stack	Post Checkout repository	2026-04-16T18:39:52.5456798Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### ALPHA ENGINE - Universe Expander — **latest** (success / completed) [run 24523987327](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24523987327)

Signal lines:

```text
expand-universe	UNKNOWN STEP	2026-04-16T17:21:10.7690391Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
expand-universe	UNKNOWN STEP	2026-04-16T17:21:10.7918737Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### ALPHA ENGINE FAST Tighter TP/SL, Shorter Holds — **latest** (- / in_progress) [run 24527463068](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527463068)

*No signal regex hits; last 25 log lines:*

```text
run 24527463068 is still in progress; logs will be available when it is complete
```

### ALPHA ENGINE Gainer Capture (15min) — **latest** (success / completed) [run 24527542667](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527542667)

Signal lines:

```text
gainer-capture	Post Checkout repository	2026-04-16T18:40:54.5172243Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
gainer-capture	Post Checkout repository	2026-04-16T18:40:54.5394760Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Analyst Tracker  Top 20 Crypto Analysts — **latest** (skipped / completed) [run 24526967300](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526967300)

*No signal regex hits; last 25 log lines:*

```text

```

### ANTIGRAVITY ML  Hourly Discord Status + Picks — **latest** (success / completed) [run 24526977785](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526977785)

Signal lines:

```text
post-status	Post Run actions/checkout@v4	2026-04-16T18:27:46.6620956Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
post-status	Post Run actions/checkout@v4	2026-04-16T18:27:46.6873486Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### ANTIGRAVITY-CLAUDEOPUS  Live Picks & Discord — **latest** (success / completed) [run 24527287815](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527287815)

Signal lines:

```text
live-picks	Post Checkout repository	2026-04-16T18:38:13.6455740Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
live-picks	Post Checkout repository	2026-04-16T18:38:13.6691175Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### AsterDEX Paper Trading — **latest** (success / completed) [run 24527498779](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527498779)

Signal lines:

```text
trade	Post Checkout repository	2026-04-16T18:40:20.6876355Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
trade	Post Checkout repository	2026-04-16T18:40:20.7104075Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Audit Drift Telemetry — **latest** (success / completed) [run 24527552041](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527552041)

Signal lines:

```text
drift	Post Checkout	2026-04-16T18:41:10.8189456Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
drift	Post Checkout	2026-04-16T18:41:10.8416846Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Audit Impact Tracker — **latest** (success / completed) [run 24526787959](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526787959)

Signal lines:

```text
audit-impact	Post Checkout repository	2026-04-16T18:24:43.9242203Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
audit-impact	Post Checkout repository	2026-04-16T18:24:43.9479615Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Baby Strat Real Forward Monitor — **latest** (- / in_progress) [run 24527689670](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527689670)

*No signal regex hits; last 25 log lines:*

```text
run 24527689670 is still in progress; logs will be available when it is complete
```

### Backfill Missing Audit Trail Sources — **latest** (success / completed) [run 24527246630](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527246630)

Signal lines:

```text
backfill	Post Checkout repository	2026-04-16T18:36:11.8224833Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
backfill	Post Checkout repository	2026-04-16T18:36:11.8539802Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Breakout Arena  3 Approaches — **latest** (success / completed) [run 24527521448](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527521448)

Signal lines:

```text
scan-all	Post Run actions/checkout@v4	2026-04-16T18:42:28.4983751Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
scan-all	Post Run actions/checkout@v4	2026-04-16T18:42:28.5217377Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Buy Now Analysis & Tracking — **latest** (success / completed) [run 24527126348](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527126348)

Signal lines:

```text
analyze-and-track	Post Checkout repository	2026-04-16T18:39:40.3156705Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
analyze-and-track	Post Checkout repository	2026-04-16T18:39:40.3395241Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Check Streamer Live Status — **latest** (success / completed) [run 24526900107](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526900107)

Signal lines:

```text
check-streamers	Post Checkout repository	2026-04-16T18:27:56.0234699Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
check-streamers	Post Checkout repository	2026-04-16T18:27:56.0484632Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### CI Tests — **latest** (- / in_progress) [run 24527927111](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527927111)

*No signal regex hits; last 25 log lines:*

```text
run 24527927111 is still in progress; logs will be available when it is complete
```

### Claude Gainer ML  Live Scanner — **latest** (success / completed) [run 24527626441](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527626441)

Signal lines:

```text
scan	Commit results	2026-04-16T18:47:36.1818121Z CONFLICT (content): Merge conflict in claude_gainer_ml/tracker/claude_live_picks.json
scan	Post Run actions/checkout@v4	2026-04-16T18:47:49.3867057Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
scan	Post Run actions/checkout@v4	2026-04-16T18:47:49.4100200Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Claude Gainer Short-Term Predictor — **latest** (- / in_progress) [run 24527505847](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527505847)

*No signal regex hits; last 25 log lines:*

```text
run 24527505847 is still in progress; logs will be available when it is complete
```

### Coinglass DNA Scanner — **latest** (success / completed) [run 24527491854](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527491854)

Signal lines:

```text
scan	Post Run actions/checkout@v4	2026-04-16T18:42:32.8701859Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
scan	Post Run actions/checkout@v4	2026-04-16T18:42:32.8941231Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Conflict Marker Check — **latest** (- / in_progress) [run 24527927089](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527927089)

*No signal regex hits; last 25 log lines:*

```text
run 24527927089 is still in progress; logs will be available when it is complete
```

### Consensus Outcome Tracker — **latest** (cancelled / completed) [run 24527045714](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527045714)

Signal lines:

```text
track-outcomes	Commit outcome updates	2026-04-16T18:30:49.1845039Z [36;1m  git pull --rebase --no-recurse-submodules -X theirs origin main 2>/dev/null || {[0m
track-outcomes	Commit outcome updates	2026-04-16T18:37:52.4748482Z ##[error]The operation was canceled.
track-outcomes	Post Run actions/checkout@v4	2026-04-16T18:37:52.7202736Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
track-outcomes	Post Run actions/checkout@v4	2026-04-16T18:37:52.7667057Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Consensus Outcome Tracker — **prior** (cancelled / completed) [run 24524564588](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24524564588)

Signal lines:

```text
track-outcomes	UNKNOWN STEP	2026-04-16T17:34:14.9606270Z [36;1m  git pull --rebase --no-recurse-submodules -X theirs origin main 2>/dev/null || {[0m
track-outcomes	UNKNOWN STEP	2026-04-16T17:41:39.5531032Z ##[error]The operation was canceled.
track-outcomes	UNKNOWN STEP	2026-04-16T17:41:39.7842680Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
track-outcomes	UNKNOWN STEP	2026-04-16T17:41:39.8154805Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Contested Pick Checker (Claude vs Antigravity) — **latest** (success / completed) [run 24527315850](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527315850)

Signal lines:

```text
check-contested	Fix broken submodule entry	﻿2026-04-16T18:35:46.8506093Z ##[group]Run git rm --cached tmp/fte_clone 2>/dev/null || true
check-contested	Fix broken submodule entry	2026-04-16T18:35:46.8506626Z [36;1mgit rm --cached tmp/fte_clone 2>/dev/null || true[0m
check-contested	Fix broken submodule entry	2026-04-16T18:35:46.8507069Z [36;1mgit config --global --add safe.directory "$GITHUB_WORKSPACE"[0m
check-contested	Fix broken submodule entry	2026-04-16T18:35:46.8531616Z shell: /usr/bin/bash -e {0}
check-contested	Fix broken submodule entry	2026-04-16T18:35:46.8531893Z ##[endgroup]
check-contested	Post Checkout repository	2026-04-16T18:35:48.5978183Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
check-contested	Post Checkout repository	2026-04-16T18:35:48.6203680Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Conviction Picks Ultra-Selective Discord Alert — **latest** (success / completed) [run 24526619131](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526619131)

Signal lines:

```text
conviction-picks	Run Conviction Picks scanner	2026-04-16T18:20:27.7344141Z   [WARN] Binance klines failed (https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=4h&limit=60): HTTP Error 451:
conviction-picks	Run Conviction Picks scanner	2026-04-16T18:20:28.2631298Z   [WARN] Binance klines failed (https://api1.binance.com/api/v3/klines?symbol=BTCUSDT&interval=4h&limit=60): HTTP Error 451:
conviction-picks	Post Run actions/checkout@v4	2026-04-16T18:20:48.6738249Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
conviction-picks	Post Run actions/checkout@v4	2026-04-16T18:20:48.6915672Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Copy Trader Forward Test — **latest** (- / in_progress) [run 24527772251](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527772251)

*No signal regex hits; last 25 log lines:*

```text
run 24527772251 is still in progress; logs will be available when it is complete
```

### Copy Trader Intelligence  Scrape + Analyze + Track — **latest** (success / completed) [run 24526551492](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526551492)

Signal lines:

```text
copy-trader-scan	Commit all data changes	2026-04-16T18:42:19.1401968Z CONFLICT (content): Merge conflict in copy_trader_intel/data/polymarket_trader_profiles.json
copy-trader-scan	Post Checkout	2026-04-16T18:42:20.9989338Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
copy-trader-scan	Post Checkout	2026-04-16T18:42:21.0296578Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Copy Trader Portfolio Tracker — **latest** (success / completed) [run 24523526046](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24523526046)

Signal lines:

```text
track-copytrader	UNKNOWN STEP	2026-04-16T17:10:18.5641073Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
track-copytrader	UNKNOWN STEP	2026-04-16T17:10:18.5861807Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Cross-Asset Correlation Monitor — **latest** (success / completed) [run 24527696167](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527696167)

Signal lines:

```text
correlation-monitor	Post Checkout repository	2026-04-16T18:45:14.0550702Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
correlation-monitor	Post Checkout repository	2026-04-16T18:45:14.0803069Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Cross-System Signal Aggregator — **latest** (success / completed) [run 24527526278](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527526278)

Signal lines:

```text
aggregate	Post Checkout repository	2026-04-16T18:44:01.0014724Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
aggregate	Post Checkout repository	2026-04-16T18:44:01.0268749Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Crypto Gainer ML Live Tracker — **latest** (success / completed) [run 24526727097](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526727097)

Signal lines:

```text
predict-and-track	Post Checkout repository	2026-04-16T18:21:45.1970412Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
predict-and-track	Post Checkout repository	2026-04-16T18:21:45.2201435Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Crypto ML Edge GSD Scanner — **latest** (success / completed) [run 24527152125](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527152125)

Signal lines:

```text
scan	Post Run actions/checkout@v4	2026-04-16T18:33:44.0033213Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
scan	Post Run actions/checkout@v4	2026-04-16T18:33:44.0219323Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Crypto Signal Engine — **latest** (success / completed) [run 24527327900](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527327900)

Signal lines:

```text
signal-engine	Post Run actions/checkout@v4	2026-04-16T18:37:41.3782454Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
signal-engine	Post Run actions/checkout@v4	2026-04-16T18:37:41.4042931Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### CRYPTO SMART PICKS - Portfolio A/B/C/D Scanner — **latest** (success / completed) [run 24523804396](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24523804396)

Signal lines:

```text
crypto-smart-picks	UNKNOWN STEP	2026-04-16T17:16:39.3860754Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
crypto-smart-picks	UNKNOWN STEP	2026-04-16T17:16:39.4089140Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Crypto Winner Scanner  Auto Scan — **latest** (success / completed) [run 24527163971](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527163971)

*No signal regex hits; last 25 log lines:*

```text
scan-and-track	Print leaderboard	2026-04-16T18:30:39.6343438Z [36;1mecho "=== Scanner Performance Leaderboard ==="[0m
scan-and-track	Print leaderboard	2026-04-16T18:30:39.6344656Z [36;1mRESULT=$(curl -s --max-time 15 "https://findtorontoevents.ca/findcryptopairs/api/crypto_winners.php?action=stats") || true[0m
scan-and-track	Print leaderboard	2026-04-16T18:30:39.6345881Z [36;1mecho "$RESULT" | python3 -c "[0m
scan-and-track	Print leaderboard	2026-04-16T18:30:39.6346416Z [36;1mimport sys, json[0m
scan-and-track	Print leaderboard	2026-04-16T18:30:39.6346861Z [36;1mtry:[0m
scan-and-track	Print leaderboard	2026-04-16T18:30:39.6347261Z [36;1m    d = json.load(sys.stdin)[0m
scan-and-track	Print leaderboard	2026-04-16T18:30:39.6347768Z [36;1m    if d.get('ok'):[0m
scan-and-track	Print leaderboard	2026-04-16T18:30:39.6348257Z [36;1m        s = d.get('stats', {})[0m
scan-and-track	Print leaderboard	2026-04-16T18:30:39.6348910Z [36;1m        print(f'Total signals: {s.get(\"total_signals\",0)}')[0m
scan-and-track	Print leaderboard	2026-04-16T18:30:39.6349747Z [36;1m        print(f'Win rate: {s.get(\"overall_win_rate\",\"--\")}%')[0m
scan-and-track	Print leaderboard	2026-04-16T18:30:39.6350518Z [36;1m        print(f'Avg PnL: {s.get(\"avg_pnl\",\"--\")}%')[0m
scan-and-track	Print leaderboard	2026-04-16T18:30:39.6351431Z [36;1m        print(f'Best: +{s.get(\"best_trade\",0)}% | Worst: {s.get(\"worst_trade\",0)}%')[0m
scan-and-track	Print leaderboard	2026-04-16T18:30:39.6352818Z [36;1m        print(f'Resolved: {s.get(\"resolved\",0)} | Pending: {s.get(\"pending\",0)}')[0m
scan-and-track	Print leaderboard	2026-04-16T18:30:39.6353634Z [36;1mexcept:[0m
scan-and-track	Print leaderboard	2026-04-16T18:30:39.6354064Z [36;1m    print('Parse error')[0m
scan-and-track	Print leaderboard	2026-04-16T18:30:39.6354597Z [36;1m" || echo "Stats: $RESULT"[0m
scan-and-track	Print leaderboard	2026-04-16T18:30:39.6383200Z shell: /usr/bin/bash -e {0}
scan-and-track	Print leaderboard	2026-04-16T18:30:39.6383509Z ##[endgroup]
scan-and-track	Print leaderboard	2026-04-16T18:30:39.6423375Z === Scanner Performance Leaderboard ===
scan-and-track	Print leaderboard	2026-04-16T18:30:39.8723704Z Total signals: 317
scan-and-track	Print leaderboard	2026-04-16T18:30:39.8724224Z Win rate: 41.5%
scan-and-track	Print leaderboard	2026-04-16T18:30:39.8724694Z Avg PnL: -0.38%
scan-and-track	Print leaderboard	2026-04-16T18:30:39.8725134Z Best: +18% | Worst: -11.8211%
scan-and-track	Print leaderboard	2026-04-16T18:30:39.8725614Z Resolved: 316 | Pending: 1
scan-and-track	Complete job	﻿2026-04-16T18:30:39.8808460Z Cleaning up orphan processes
```

### Daily Feed Summary — **latest** (success / completed) [run 24526697150](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526697150)

Signal lines:

```text
generate-summary	Post Run actions/checkout@v4	2026-04-16T18:19:54.5328349Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
generate-summary	Post Run actions/checkout@v4	2026-04-16T18:19:54.5549906Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### DARWIN ENGINE - DNA Evolution Pipeline — **latest** (success / completed) [run 24526950663](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526950663)

Signal lines:

```text
evolve	Post Checkout	2026-04-16T18:35:28.0247754Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
evolve	Post Checkout	2026-04-16T18:35:28.0436961Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Dashboard Pick Trader — **latest** (success / completed) [run 24526187035](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526187035)

Signal lines:

```text
trade-dashboard-picks	Run Dashboard Pick Trader	2026-04-16T18:10:32.9924643Z   [API] binance failed: HTTP Error 451:
trade-dashboard-picks	Run Dashboard Pick Trader	2026-04-16T18:10:32.9925013Z   [API] binance_mirror1 failed: HTTP Error 451:
trade-dashboard-picks	Run Dashboard Pick Trader	2026-04-16T18:10:32.9925453Z   [API] binance_mirror2 failed: HTTP Error 451:
trade-dashboard-picks	Post Checkout repository	2026-04-16T18:10:50.4769617Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
trade-dashboard-picks	Post Checkout repository	2026-04-16T18:10:50.4993977Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Data Pipeline Reliability Test — **latest** (success / completed) [run 24527288845](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527288845)

Signal lines:

```text
test-data-sources	Post Checkout repository	2026-04-16T18:41:50.8230776Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
test-data-sources	Post Checkout repository	2026-04-16T18:41:50.8484611Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Deploy Battleground to FTP — **latest** (success / completed) [run 24523671674](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24523671674)

Signal lines:

```text
deploy	UNKNOWN STEP	2026-04-16T17:13:25.7970357Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
deploy	UNKNOWN STEP	2026-04-16T17:13:25.8197441Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Deploy Competition to Live Site — **latest** (success / completed) [run 24527780727](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527780727)

Signal lines:

```text
deploy	Post Checkout	2026-04-16T18:46:47.0204666Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
deploy	Post Checkout	2026-04-16T18:46:47.0430964Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Deploy FindCryptoPairs to FTP — **latest** (success / completed) [run 24527691177](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527691177)

Signal lines:

```text
deploy	Post Checkout	2026-04-16T18:44:25.1643907Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
deploy	Post Checkout	2026-04-16T18:44:25.1877854Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Deploy MOVIESHOWS2 + MOVIESHOWS3 (All 3 Domains) — **latest** (success / completed) [run 24527552693](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527552693)

Signal lines:

```text
deploy	Post Run actions/checkout@v4	2026-04-16T18:41:45.0810067Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
deploy	Post Run actions/checkout@v4	2026-04-16T18:41:45.0997844Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Deploy Rise of the Claw Dashboard — **latest** (success / completed) [run 24527014074](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527014074)

Signal lines:

```text
deploy	Post Checkout repository	2026-04-16T18:33:27.5035985Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
deploy	Post Checkout repository	2026-04-16T18:33:27.5276459Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Discord Bot  Persistent — **latest** (- / in_progress) [run 24527446176](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527446176)

*No signal regex hits; last 25 log lines:*

```text
run 24527446176 is still in progress; logs will be available when it is complete
```

### Discord ML Status Report — **latest** (success / completed) [run 24527051216](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527051216)

Signal lines:

```text
send-status	Post Run actions/checkout@v4	2026-04-16T18:29:47.5207143Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
send-status	Post Run actions/checkout@v4	2026-04-16T18:29:47.5427482Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### DNA Genome Daily Pipeline — **latest** (- / in_progress) [run 24526740896](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526740896)

*No signal regex hits; last 25 log lines:*

```text
run 24526740896 is still in progress; logs will be available when it is complete
```

### EMA Retracement Mean Reversion Scanner — **latest** (success / completed) [run 24527619278](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527619278)

Signal lines:

```text
ema-retracement	Post Checkout repository	2026-04-16T18:43:05.0614640Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
ema-retracement	Post Checkout repository	2026-04-16T18:43:05.0879876Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Enhanced ML Crypto Train & Predict — **latest** (- / in_progress) [run 24527730704](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527730704)

*No signal regex hits; last 25 log lines:*

```text
run 24527730704 is still in progress; logs will be available when it is complete
```

### FC-CRYPTO PRO Top Actionable Picks — **latest** (success / completed) [run 24527459655](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527459655)

Signal lines:

```text
fc-crypto-pro	Post Run actions/checkout@v4	2026-04-16T18:39:33.7713188Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
fc-crypto-pro	Post Run actions/checkout@v4	2026-04-16T18:39:33.7953268Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Feed Health Check — **latest** (- / in_progress) [run 24527931095](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527931095)

*No signal regex hits; last 25 log lines:*

```text
run 24527931095 is still in progress; logs will be available when it is complete
```

### Fix Battleground Deployment — **latest** (success / completed) [run 24523671656](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24523671656)

Signal lines:

```text
deploy-battleground	UNKNOWN STEP	2026-04-16T17:20:34.6190077Z  * [new branch]            fix/js-typeerror-picks-guard -> origin/fix/js-typeerror-picks-guard
deploy-battleground	UNKNOWN STEP	2026-04-16T17:20:36.9640352Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
deploy-battleground	UNKNOWN STEP	2026-04-16T17:20:36.9939895Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'http\.https\:\/\/github\.com\/\.extraheader' && git config --local --unset-all 'http.https://github.com/.extraheader' || :"
deploy-battleground	UNKNOWN STEP	2026-04-16T17:20:37.0199589Z [command]/usr/bin/git submodule foreach --recursive git config --local --show-origin --name-only --get-regexp remote.origin.url
```

### Forex Agent — **latest** (success / completed) [run 24524371833](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24524371833)

Signal lines:

```text
Forex Scanner	UNKNOWN STEP	2026-04-16T17:29:23.3083774Z HTTP Error 404: Not Found{"quoteSummary":{"result":null,"error":{"code":"Not Found","description":"Quote not found for symbol: DX=F"}}}
Forex Scanner	UNKNOWN STEP	2026-04-16T17:29:35.6882605Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
Forex Scanner	UNKNOWN STEP	2026-04-16T17:29:35.7054258Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Forex Smart Picks Scanner — **latest** (success / completed) [run 24526742659](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526742659)

Signal lines:

```text
forex-smart-picks	Post Checkout repository	2026-04-16T18:23:15.3377655Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
forex-smart-picks	Post Checkout repository	2026-04-16T18:23:15.3615581Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Forward Signal Scanner — **latest** (success / completed) [run 24526870556](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526870556)

Signal lines:

```text
scan	Post Run actions/checkout@v4	2026-04-16T18:27:59.4668633Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
scan	Post Run actions/checkout@v4	2026-04-16T18:27:59.4914590Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Forward Trade Tracking v2 — **latest** (success / completed) [run 24526921107](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526921107)

Signal lines:

```text
track-signals	Post Checkout repository	2026-04-16T18:29:16.9932678Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
track-signals	Post Checkout repository	2026-04-16T18:29:17.0152626Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Forward-Test New Strategies Tracker — **latest** (success / completed) [run 24526710872](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526710872)

Signal lines:

```text
forward-test	Post Checkout repository	2026-04-16T18:22:26.0177640Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
forward-test	Post Checkout repository	2026-04-16T18:22:26.0418313Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Gainer Predictor Scanner — **latest** (success / completed) [run 24527339871](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527339871)

Signal lines:

```text
scan	Post Run actions/checkout@v4	2026-04-16T18:42:43.5605372Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
scan	Post Run actions/checkout@v4	2026-04-16T18:42:43.5840267Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Goldmine Tracker - Archive & Maintain — **latest** (success / completed) [run 24527198769](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527198769)

*No signal regex hits; last 25 log lines:*

```text
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:31:03.5747908Z [36;1mALERTS=$(curl -sf --max-time 10 \[0m
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:31:03.5748807Z [36;1m  "https://findtorontoevents.ca/live-monitor/api/goldmine_tracker.php?action=alerts" \[0m
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:31:03.5749665Z [36;1m  2>&1 || echo '{"ok":false}')[0m
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:31:03.5750813Z [36;1mALERT_COUNT=$(echo "$ALERTS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('active_count','?'))" 2>/dev/null || echo "?")[0m
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:31:03.5751924Z [36;1mecho "Active alerts: $ALERT_COUNT"[0m
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:31:03.5752530Z [36;1m[0m
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:31:03.5753015Z [36;1mecho ""[0m
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:31:03.5753516Z [36;1mecho " Goldmine tracker maintenance complete"[0m
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:31:03.6162615Z shell: /usr/bin/bash -e {0}
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:31:03.6163626Z ##[endgroup]
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:31:03.6367636Z  Triggering goldmine tracker archive + outcomes...
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:31:04.3744862Z Archive response: {"ok":false,"error":"Unauthorized"}
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:31:04.9467146Z Health check response: {"ok":true,"action":"check_health","result":{"health_snapshots":8,"alerts_created":14}}
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:31:04.9468287Z 
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:31:04.9468462Z  Running maintenance tasks...
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:31:05.2016262Z Maintenance response: {"status":{"stale_sports_picks":0,"stale_meme_picks":0,"stale_penny_picks":0,"consolidated_missing_price":0,"active_alerts":14,"duplicate_alerts":0},"expire":{"sports_expired":0,"meme_expired":0,"other_expired":0,"consolidated_missing_prices":[]},"prices":{"fixed":0,"failed":[],"details":[]},"alerts":{"duplicates_resolved":0,"remaining_active":[{"source_system":"consolidated","alert_type":"negative_roi","severity":"warning","title":"consolidated: Average return negative (-4%)","alert_date":"2026-04-16"},{"source_system":"consolidated","alert_type":"zero_picks","severity":"warning","title":"consolidated: No picks generated in 7 days","alert_date":"2026-04-16"},{"source_system":"live_signal","alert_type":"zero_picks","severity":"warning","title":"live_signal: No picks generated in 7 days","alert_date":"2026-04-16"},{"source_system":"edge","alert_type":"zero_picks","severity":"warning","title":"edge: No picks generated in 7 days","alert_date":"2026-04-16"},{"source_system":"meme","alert_type":"zero_picks","severity":"warning","title":"meme: No picks generated in 7 days","alert_date":"2026-04-16"},{"source_system":"sports","alert_type":"zero_picks","severity":"warning","title":"sports: No picks generated in 7 days","alert_date":"2026-04-16"},{"source_system":"penny","alert_type":"zero_picks","severity":"warning","title":"penny: No picks generated in 7 days","alert_date":"2026-04-16"},{"source_system":"sports","alert_type":"accuracy_drop","severity":"warning","title":"Sports: Overall win rate low (30% across 10 bets)","alert_date":"2026-04-16"},{"source_system":"consolidated","alert_type":"stale_data","severity":"critical","title":"consolidated: No new picks for 61 days","alert_date":"2026-04-16"},{"source_system":"live_signal","alert_type":"stale_data","severity":"critical","title":"live_signal: No new picks for 59 days","alert_date":"2026-04-16"},{"source_system":"edge","alert_type":"stale_data","severity":"critical","title":"edge: No new picks for 65 days","alert_date":"2026-04-16"},{"source_system":"meme","alert_type":"stale_data","severity":"critical","title":"meme: No new picks for 63 days","alert_date":"2026-04-16"},{"source_system":"sports","alert_type":"stale_data","severity":"critical","title":"sports: No new picks for 63 days","alert_date":"2026-04-16"},{"source_system":"penny","alert_type":"stale_data","severity":"critical","title":"penny: No new picks for 59 days","alert_date":"2026-04-16"}],"remaining_count":14},"ok":true,"action":"run","dry_run":false,"timestamp":"2026-04-16 18:31:05"}
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:31:05.2025694Z 
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:31:05.2026754Z  Final status check...
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:31:05.3078757Z Status: {"status":{"stale_sports_picks":0,"stale_meme_picks":0,"stale_penny_picks":0,"consolidated_missing_price":0,"active_alerts":14,"duplicate_alerts":0},"ok":true,"action":"status","dry_run":false,"timestamp":"2026-04-16 18:31:05"}
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:31:05.3080843Z 
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:31:05.3081235Z  Current alerts...
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:31:05.5590920Z Active alerts: 14
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:31:05.5591502Z 
track-and-maintain	Archive new picks & check outcomes	2026-04-16T18:31:05.5591800Z  Goldmine tracker maintenance complete
track-and-maintain	Complete job	﻿2026-04-16T18:31:05.5771168Z Cleaning up orphan processes
```

### Hindsight Learner  Hourly Winner Analysis — **latest** (success / completed) [run 24527494185](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527494185)

Signal lines:

```text
analyze	Post Run actions/checkout@v4	2026-04-16T18:40:30.6757701Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
analyze	Post Run actions/checkout@v4	2026-04-16T18:40:30.6977448Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Hoffman IRB Strategy Tracker — **latest** (success / completed) [run 24527076059](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527076059)

Signal lines:

```text
track	Post Checkout	2026-04-16T18:30:24.1078726Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
track	Post Checkout	2026-04-16T18:30:24.1300754Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Hourly Master Picks to Discord — **latest** (success / completed) [run 24527489476](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527489476)

Signal lines:

```text
send-master-picks	Post Checkout repository	2026-04-16T18:40:21.8581948Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
send-master-picks	Post Checkout repository	2026-04-16T18:40:21.8810771Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Hub Data Sync — **latest** (success / completed) [run 24527849217](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527849217)

Signal lines:

```text
sync	Collect system data for hub	2026-04-16T18:47:59.7017879Z Traceback (most recent call last):
sync	Post Run actions/checkout@v4	2026-04-16T18:48:00.7316668Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
sync	Post Run actions/checkout@v4	2026-04-16T18:48:00.7541913Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### KIMI Goldmine Data Collection — **latest** (success / completed) [run 24527099221](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527099221)

Signal lines:

```text
collect-and-update	Post Checkout repository	2026-04-16T18:40:18.8663155Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
collect-and-update	Post Checkout repository	2026-04-16T18:40:18.8928574Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### KIMI_FEB172026 - Live Trading System — **latest** (success / completed) [run 24526946515](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526946515)

Signal lines:

```text
kimi-trading	Post Checkout repository	2026-04-16T18:29:54.1666609Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
kimi-trading	Post Checkout repository	2026-04-16T18:29:54.1939173Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Live Picks Tracker — **latest** (- / in_progress) [run 24527879218](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527879218)

*No signal regex hits; last 25 log lines:*

```text
run 24527879218 is still in progress; logs will be available when it is complete
```

### Live Trading Monitor  Auto Refresh — **latest** (success / completed) [run 24525966757](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24525966757)

Signal lines:

```text
live-refresh	Check circuit breakers	﻿2026-04-16T18:03:43.1143141Z ##[group]Run echo "=== Checking circuit breakers ==="
live-refresh	Check circuit breakers	2026-04-16T18:03:43.1143561Z [36;1mecho "=== Checking circuit breakers ==="[0m
live-refresh	Check circuit breakers	2026-04-16T18:03:43.1144224Z [36;1mRESULT=$(curl -s --max-time 15 "https://findtorontoevents.ca/live-monitor/api/breaker_live.php?action=check&key=livetrader2026") || true[0m
live-refresh	Check circuit breakers	2026-04-16T18:03:43.1144852Z [36;1mecho "$RESULT" | python3 -c "[0m
live-refresh	Check circuit breakers	2026-04-16T18:03:43.1145110Z [36;1mimport sys, json[0m
live-refresh	Check circuit breakers	2026-04-16T18:03:43.1145335Z [36;1md = json.load(sys.stdin)[0m
live-refresh	Check circuit breakers	2026-04-16T18:03:43.1145579Z [36;1mif d.get('ok'):[0m
live-refresh	Check circuit breakers	2026-04-16T18:03:43.1145819Z [36;1m    active = d.get('active_breakers', [])[0m
live-refresh	Check circuit breakers	2026-04-16T18:03:43.1146101Z [36;1m    if active:[0m
live-refresh	Check circuit breakers	2026-04-16T18:03:43.1146348Z [36;1m        print(f'ACTIVE BREAKERS: {len(active)}')[0m
live-refresh	Check circuit breakers	2026-04-16T18:03:43.1146644Z [36;1m        for b in active:[0m
live-refresh	Check circuit breakers	2026-04-16T18:03:43.1147079Z [36;1m            print(f'  {b.get(\"rule\",\"?\")}: {b.get(\"reason\",\"?\")} (cooldown: {b.get(\"remaining_minutes\",0)}m)')[0m
live-refresh	Check circuit breakers	2026-04-16T18:03:43.1147554Z [36;1m    else:[0m
live-refresh	Check circuit breakers	2026-04-16T18:03:43.1147828Z [36;1m        print('No active circuit breakers - trading allowed')[0m
live-refresh	Check circuit breakers	2026-04-16T18:03:43.1148162Z [36;1m" || echo "Breakers: $RESULT"[0m
live-refresh	Check circuit breakers	2026-04-16T18:03:43.1169505Z shell: /usr/bin/bash -e {0}
live-refresh	Check circuit breakers	2026-04-16T18:03:43.1169748Z ##[endgroup]
live-refresh	Check circuit breakers	2026-04-16T18:03:43.1209916Z === Checking circuit breakers ===
live-refresh	Check circuit breakers	2026-04-16T18:03:43.4666111Z No active circuit breakers - trading allowed
```

### Low-Score Winner Tracker — **latest** (success / completed) [run 24527496439](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527496439)

Signal lines:

```text
track	Post Checkout	2026-04-16T18:39:55.0129727Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
track	Post Checkout	2026-04-16T18:39:55.0352668Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### LuxAlgo Signal Generator — **latest** (- / in_progress) [run 24527905682](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527905682)

*No signal regex hits; last 25 log lines:*

```text
run 24527905682 is still in progress; logs will be available when it is complete
```

### Market Beating System - Crypto & Forex Priority — **latest** (success / completed) [run 24527199994](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527199994)

Signal lines:

```text
market-beating	Post Checkout code	2026-04-16T18:43:29.7457411Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
market-beating	Post Checkout code	2026-04-16T18:43:29.8466534Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Master Automation Scheduler — **latest** (success / completed) [run 24526825943](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526825943)

Signal lines:

```text
hourly-tasks	Poll all systems with ML enhancement	2026-04-16T18:25:52.9288779Z Traceback (most recent call last):
hourly-tasks	Post Run actions/checkout@v4	2026-04-16T18:25:54.3457533Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
hourly-tasks	Post Run actions/checkout@v4	2026-04-16T18:25:54.3685281Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Mega Mutation Live Tracker — **latest** (success / completed) [run 24526292713](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526292713)

Signal lines:

```text
track	Post Checkout	2026-04-16T18:13:32.6220512Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
track	Post Checkout	2026-04-16T18:13:32.6444277Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Meme Coin Scanner Auto Scan & Resolve — **latest** (success / completed) [run 24526954553](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526954553)

Signal lines:

```text
meme-scan	Post Run actions/checkout@v4	2026-04-16T18:28:03.0189917Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
meme-scan	Post Run actions/checkout@v4	2026-04-16T18:28:03.0416640Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Meme Coin Scanner v2  Fixed & Monitored — **latest** (success / completed) [run 24527538051](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527538051)

Signal lines:

```text
meme-scan	Post Checkout code	2026-04-16T18:40:57.1347349Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
meme-scan	Post Checkout code	2026-04-16T18:40:57.1568569Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Mercury 2  Signal Scanner — **latest** (success / completed) [run 24525743796](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24525743796)

Signal lines:

```text
scan	Post Run actions/checkout@v4	2026-04-16T18:02:06.0566409Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
scan	Post Run actions/checkout@v4	2026-04-16T18:02:06.0827768Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Meta-Strategy Permutation Engine — **latest** (success / completed) [run 24527797288](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527797288)

Signal lines:

```text
meta-strategy	Post Checkout	2026-04-16T18:48:22.5062371Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
meta-strategy	Post Checkout	2026-04-16T18:48:22.5320010Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Mirror: findtorontoevents.ca  torontoevent.net — **latest** (- / in_progress) [run 24526892351](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526892351)

*No signal regex hits; last 25 log lines:*

```text
run 24526892351 is still in progress; logs will be available when it is complete
```

### Missed Opportunity Analyzer Hourly Self-Improvement — **latest** (success / completed) [run 24527812901](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527812901)

Signal lines:

```text
missed-opportunity-scan	Post Checkout	2026-04-16T18:47:28.6663456Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
missed-opportunity-scan	Post Checkout	2026-04-16T18:47:28.6884993Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### ML Battleground System F (Claws of Doom) — **latest** (success / completed) [run 24526350305](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526350305)

Signal lines:

```text
sync	Post Run actions/checkout@v4	2026-04-16T18:16:16.4220381Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
sync	Post Run actions/checkout@v4	2026-04-16T18:16:16.4409048Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### ML Crypto  Discord Hourly Status — **latest** (success / completed) [run 24527084524](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527084524)

Signal lines:

```text
send-status	Post Checkout repository	2026-04-16T18:30:35.6338787Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
send-status	Post Checkout repository	2026-04-16T18:30:35.6577748Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### ML Feedback Loop — **latest** (success / completed) [run 24527077157](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527077157)

Signal lines:

```text
feedback-check	Check for retrain trigger	2026-04-16T18:30:40.6182674Z   "reason": "Circuit breaker: 53 consecutive losses",
feedback-check	Post Run actions/checkout@v4	2026-04-16T18:31:00.2048185Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
feedback-check	Post Run actions/checkout@v4	2026-04-16T18:31:00.2298393Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### ML Model Auto-Training — **latest** (success / completed) [run 24527353891](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527353891)

Signal lines:

```text
check-and-train	Post Checkout repository	2026-04-16T18:45:51.5089858Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
check-and-train	Post Checkout repository	2026-04-16T18:45:51.5411131Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### ML Strategy Reviver Bridge & Standalone — **latest** (- / in_progress) [run 24527926226](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527926226)

*No signal regex hits; last 25 log lines:*

```text
run 24527926226 is still in progress; logs will be available when it is complete
```

### ML System Health Monitor — **latest** (success / completed) [run 24527078580](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527078580)

Signal lines:

```text
health-check	Post Run actions/checkout@v4	2026-04-16T18:30:37.9190703Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
health-check	Post Run actions/checkout@v4	2026-04-16T18:30:37.9412829Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### MOMENTUM CATCHER - Real-time Pump Detector — **latest** (success / completed) [run 24527271439](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527271439)

Signal lines:

```text
momentum-scan	Merge momentum picks into active_picks.json	2026-04-16T18:35:19.6664082Z [36;1m    except (json.JSONDecodeError, ValueError):[0m
momentum-scan	Post Checkout repository	2026-04-16T18:35:38.2182877Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
momentum-scan	Post Checkout repository	2026-04-16T18:35:38.2424529Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### MOMENTUM TRACKER - Real-Time Gainer Scanner — **latest** (success / completed) [run 24525805221](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24525805221)

Signal lines:

```text
momentum-scan	Post Checkout repository	2026-04-16T18:02:10.0257257Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
momentum-scan	Post Checkout repository	2026-04-16T18:02:10.0499717Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Multi-Asset Copytrader Scanner v2  Forex/Futures/Stocks/Commodities — **latest** (success / completed) [run 24527319847](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527319847)

Signal lines:

```text
multi-asset-scan	Post Checkout	2026-04-16T18:37:27.3822618Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
multi-asset-scan	Post Checkout	2026-04-16T18:37:27.4050894Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Mutation Lab  Strategy Evolution Pipeline — **latest** (success / completed) [run 24526805282](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526805282)

Signal lines:

```text
promote	Post Run actions/checkout@v4	2026-04-16T18:23:49.2847173Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
promote	Post Run actions/checkout@v4	2026-04-16T18:23:49.3078722Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### MySQL Trading Picks Sync — **latest** (- / in_progress) [run 24528090792](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24528090792)

*No signal regex hits; last 25 log lines:*

```text
run 24528090792 is still in progress; logs will be available when it is complete
```

### OBI Hourly Snapshot — **latest** (success / completed) [run 24525620571](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24525620571)

Signal lines:

```text
snapshot	Post Run actions/checkout@v4	2026-04-16T17:58:00.5373904Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
snapshot	Post Run actions/checkout@v4	2026-04-16T17:58:00.5596729Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Outcome Resolver  Validate Unresolved Picks — **latest** (success / completed) [run 24527582125](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527582125)

Signal lines:

```text
resolve-outcomes	Post Checkout repository	2026-04-16T18:44:31.0592215Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
resolve-outcomes	Post Checkout repository	2026-04-16T18:44:31.0831082Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Pick Monitor & Price Validator (30min) — **latest** (success / completed) [run 24526698444](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526698444)

Signal lines:

```text
monitor-and-validate	Post Checkout repository	2026-04-16T18:22:44.0461846Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
monitor-and-validate	Post Checkout repository	2026-04-16T18:22:44.0686294Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Pine Script Generator — **latest** (skipped / completed) [run 24527226891](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527226891)

*No signal regex hits; last 25 log lines:*

```text

```

### Polymarket Prediction Market Signals — **latest** (success / completed) [run 24527625955](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527625955)

Signal lines:

```text
polymarket-scan	Post Checkout repository	2026-04-16T18:48:59.2902165Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
polymarket-scan	Post Checkout repository	2026-04-16T18:48:59.3101229Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Portfolio Trackers (Real Money + Theory) — **latest** (success / completed) [run 24527659606](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527659606)

Signal lines:

```text
track	Post Run actions/checkout@v4	2026-04-16T18:46:03.8412810Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
track	Post Run actions/checkout@v4	2026-04-16T18:46:03.8640839Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Prediction Market Agents — **latest** (success / completed) [run 24527696055](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527696055)

Signal lines:

```text
prediction-market-scan	Post Checkout repository	2026-04-16T18:45:20.7104780Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
prediction-market-scan	Post Checkout repository	2026-04-16T18:45:20.7368691Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Prediction Quality Tracker — **latest** (success / completed) [run 24526207107](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526207107)

Signal lines:

```text
track-quality	Post Checkout repository	2026-04-16T18:11:24.3666897Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
track-quality	Post Checkout repository	2026-04-16T18:11:24.3855131Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Proven Strategies Scanner — **latest** (success / completed) [run 24526878799](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526878799)

Signal lines:

```text
scan	Post Run actions/checkout@v4	2026-04-16T18:28:56.1791358Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
scan	Post Run actions/checkout@v4	2026-04-16T18:28:56.2014261Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### QUAN ENGINE - Live Autonomous Scanner — **latest** (success / completed) [run 24527429546](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527429546)

Signal lines:

```text
quan-engine	Commit results	2026-04-16T18:39:50.8487524Z fatal: pathspec 'data/audit_trail.db' did not match any files
quan-engine	Post Checkout repository	2026-04-16T18:40:19.3030564Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
quan-engine	Post Checkout repository	2026-04-16T18:40:19.3278072Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### QuantumFusion Crypto Engine — **latest** (success / completed) [run 24527176355](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527176355)

Signal lines:

```text
quantum-fusion	Post Checkout repository	2026-04-16T18:33:13.0488850Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
quantum-fusion	Post Checkout repository	2026-04-16T18:33:13.0713889Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Quick Guess ML Agent — **latest** (cancelled / completed) [run 24527537305](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527537305)

Signal lines:

```text
quick-guess	Commit results	2026-04-16T18:42:24.6125216Z [36;1m  git pull --rebase --no-recurse-submodules -X theirs origin main 2>/dev/null || {[0m
quick-guess	Commit results	2026-04-16T18:47:14.5974886Z ##[error]The operation was canceled.
quick-guess	Post Run actions/checkout@v4	2026-04-16T18:47:14.7816310Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
quick-guess	Post Run actions/checkout@v4	2026-04-16T18:47:14.8148694Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Quick Guess ML Agent — **prior** (cancelled / completed) [run 24525009553](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24525009553)

Signal lines:

```text
quick-guess	Commit results	2026-04-16T17:45:02.8002663Z [36;1m  git pull --rebase --no-recurse-submodules -X theirs origin main 2>/dev/null || {[0m
quick-guess	Commit results	2026-04-16T17:50:12.9258803Z ##[error]The operation was canceled.
quick-guess	Post Run actions/checkout@v4	2026-04-16T17:50:13.2203690Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
quick-guess	Post Run actions/checkout@v4	2026-04-16T17:50:13.2617451Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Rapid Fire - NOW Scanner — **latest** (success / completed) [run 24527655948](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527655948)

Signal lines:

```text
scan	Commit results	2026-04-16T18:44:51.8473546Z CONFLICT (content): Merge conflict in data/freshpicks_gate_state.json
scan	Post Checkout	2026-04-16T18:45:09.7418758Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
scan	Post Checkout	2026-04-16T18:45:09.7682774Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Real-Time Battle Test - Eliminate Losers, Optimize Winners — **latest** (success / completed) [run 24527197115](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527197115)

Signal lines:

```text
battle-test	Post Checkout code	2026-04-16T18:40:50.9912039Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
battle-test	Post Checkout code	2026-04-16T18:40:51.0158685Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Recommended Portfolio Generator — **latest** (- / in_progress) [run 24528072515](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24528072515)

*No signal regex hits; last 25 log lines:*

```text
run 24528072515 is still in progress; logs will be available when it is complete
```

### Refresh Top Movies Data — **latest** (success / completed) [run 24527428933](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527428933)

Signal lines:

```text
refresh	Fix broken submodule entry	﻿2026-04-16T18:38:29.2888268Z ##[group]Run if [ -f .gitmodules ]; then
refresh	Fix broken submodule entry	2026-04-16T18:38:29.2888638Z [36;1mif [ -f .gitmodules ]; then[0m
refresh	Fix broken submodule entry	2026-04-16T18:38:29.2889119Z [36;1m  git config -f .gitmodules --remove-section submodule.tmp/fte_clone 2>/dev/null || true[0m
refresh	Fix broken submodule entry	2026-04-16T18:38:29.2889771Z [36;1m  git config -f .gitmodules --remove-section submodule.STOCKSUNIFY 2>/dev/null || true[0m
refresh	Fix broken submodule entry	2026-04-16T18:38:29.2890216Z [36;1mfi[0m
refresh	Fix broken submodule entry	2026-04-16T18:38:29.2915255Z shell: /usr/bin/bash -e {0}
refresh	Fix broken submodule entry	2026-04-16T18:38:29.2915514Z ##[endgroup]
refresh	Restore workspace (prevent post-checkout submodule error)	﻿2026-04-16T18:39:02.3575927Z ##[group]Run git config -f .gitmodules --remove-section submodule.tmp/fte_clone 2>/dev/null || true
refresh	Restore workspace (prevent post-checkout submodule error)	2026-04-16T18:39:02.3576649Z [36;1mgit config -f .gitmodules --remove-section submodule.tmp/fte_clone 2>/dev/null || true[0m
refresh	Restore workspace (prevent post-checkout submodule error)	2026-04-16T18:39:02.3577278Z [36;1mgit config -f .gitmodules --remove-section submodule.STOCKSUNIFY 2>/dev/null || true[0m
refresh	Restore workspace (prevent post-checkout submodule error)	2026-04-16T18:39:02.3577765Z [36;1mgit rm --cached tmp/fte_clone 2>/dev/null || true[0m
refresh	Restore workspace (prevent post-checkout submodule error)	2026-04-16T18:39:02.3598126Z shell: /usr/bin/bash -e {0}
refresh	Restore workspace (prevent post-checkout submodule error)	2026-04-16T18:39:02.3598372Z ##[endgroup]
refresh	Post Run actions/checkout@v4	2026-04-16T18:39:02.6569064Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
refresh	Post Run actions/checkout@v4	2026-04-16T18:39:02.6805305Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Regime Terminal  HMM Live Scanner — **latest** (- / in_progress) [run 24528055782](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24528055782)

*No signal regex hits; last 25 log lines:*

```text
run 24528055782 is still in progress; logs will be available when it is complete
```

### Run Backtests & Deploy Dashboards — **latest** (success / completed) [run 24526988058](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526988058)

Signal lines:

```text
backtest	Post Checkout repository	2026-04-16T18:32:22.8223999Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
backtest	Post Checkout repository	2026-04-16T18:32:22.8467539Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Send Accountability Reminders — **latest** (success / completed) [run 24526874460](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526874460)

*No signal regex hits; last 25 log lines:*

```text
send-reminders	Send Accountability Coach Reminders	2026-04-16T18:23:45.7957299Z [36;1mimport sys, json[0m
send-reminders	Send Accountability Coach Reminders	2026-04-16T18:23:45.7957989Z [36;1mdata = json.load(sys.stdin)[0m
send-reminders	Send Accountability Coach Reminders	2026-04-16T18:23:45.7958668Z [36;1mprint(f\"Discord DMs sent: {data.get('sent_discord', 0)}\")[0m
send-reminders	Send Accountability Coach Reminders	2026-04-16T18:23:45.7959530Z [36;1mprint(f\"Dashboard notifs sent: {data.get('sent_dashboard', 0)}\")[0m
send-reminders	Send Accountability Coach Reminders	2026-04-16T18:23:45.7960417Z [36;1mprint(f\"Skipped (wrong hour): {data.get('skipped', 0)}\")[0m
send-reminders	Send Accountability Coach Reminders	2026-04-16T18:23:45.7961109Z [36;1mif data.get('dry_run'):[0m
send-reminders	Send Accountability Coach Reminders	2026-04-16T18:23:45.7961672Z [36;1m    previews = data.get('previews', [])[0m
send-reminders	Send Accountability Coach Reminders	2026-04-16T18:23:45.7962339Z [36;1m    print(f\"Preview count: {len(previews)}\")[0m
send-reminders	Send Accountability Coach Reminders	2026-04-16T18:23:45.7962971Z [36;1m    for p in previews[:10]:[0m
send-reminders	Send Accountability Coach Reminders	2026-04-16T18:23:45.7963613Z [36;1m        print(f\"  -> {p.get('channel')}: {p.get('task')}\")[0m
send-reminders	Send Accountability Coach Reminders	2026-04-16T18:23:45.7964269Z [36;1mif data.get('errors'):[0m
send-reminders	Send Accountability Coach Reminders	2026-04-16T18:23:45.7964794Z [36;1m    for e in data['errors']:[0m
send-reminders	Send Accountability Coach Reminders	2026-04-16T18:23:45.7965625Z [36;1m        print(f\"Error: {e}\")[0m
send-reminders	Send Accountability Coach Reminders	2026-04-16T18:23:45.7966166Z [36;1m"[0m
send-reminders	Send Accountability Coach Reminders	2026-04-16T18:23:45.7987875Z shell: /usr/bin/bash -e {0}
send-reminders	Send Accountability Coach Reminders	2026-04-16T18:23:45.7988391Z env:
send-reminders	Send Accountability Coach Reminders	2026-04-16T18:23:45.7989077Z   EVENT_NOTIFY_API_KEY: ***
send-reminders	Send Accountability Coach Reminders	2026-04-16T18:23:45.7989568Z ##[endgroup]
send-reminders	Send Accountability Coach Reminders	2026-04-16T18:23:45.8038595Z Sending accountability reminders...
send-reminders	Send Accountability Coach Reminders	2026-04-16T18:23:46.3426383Z HTTP Status: 200
send-reminders	Send Accountability Coach Reminders	2026-04-16T18:23:46.3428140Z Response: {"success":true,"sent_discord":0,"sent_dashboard":0,"message":"No data yet"}
send-reminders	Send Accountability Coach Reminders	2026-04-16T18:23:46.3623108Z Discord DMs sent: 0
send-reminders	Send Accountability Coach Reminders	2026-04-16T18:23:46.3624320Z Dashboard notifs sent: 0
send-reminders	Send Accountability Coach Reminders	2026-04-16T18:23:46.3625398Z Skipped (wrong hour): 0
send-reminders	Complete job	﻿2026-04-16T18:23:46.3724979Z Cleaning up orphan processes
```

### Signal Integrator - Isolated Source Aggregator — **latest** (- / in_progress) [run 24527655699](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527655699)

*No signal regex hits; last 25 log lines:*

```text
run 24527655699 is still in progress; logs will be available when it is complete
```

### Signal Quality Monitor — **latest** (success / completed) [run 24527633915](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527633915)

Signal lines:

```text
monitor-quality	Post Checkout repository	2026-04-16T18:43:22.9091430Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
monitor-quality	Post Checkout repository	2026-04-16T18:43:22.9299260Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Signal Recorder — **latest** (success / completed) [run 24526337700](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526337700)

Signal lines:

```text
record-signals	Fetch TradingView technicals	2026-04-16T18:14:30.3649350Z   MATICUSDT/1h: Exchange or symbol not found.
record-signals	Fetch TradingView technicals	2026-04-16T18:14:30.3649839Z   MATICUSDT/4h: Exchange or symbol not found.
record-signals	Fetch TradingView technicals	2026-04-16T18:14:30.3650293Z   MATICUSDT/1d: Exchange or symbol not found.
record-signals	Fetch TradingView technicals	2026-04-16T18:14:30.3650796Z   MATICUSDT/1w: Exchange or symbol not found.
record-signals	Post Run actions/checkout@v4	2026-04-16T18:15:12.7728150Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
record-signals	Post Run actions/checkout@v4	2026-04-16T18:15:12.7964888Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Signal Tracking & Validation - Beat the Market — **latest** (success / completed) [run 24526852966](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526852966)

Signal lines:

```text
track-and-validate	Post Checkout code	2026-04-16T18:35:49.0843412Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
track-and-validate	Post Checkout code	2026-04-16T18:35:49.1085543Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Skyrocket Detector  Live Scanner — **latest** (success / completed) [run 24525773385](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24525773385)

Signal lines:

```text
scan	Post Run actions/checkout@v4	2026-04-16T18:03:12.9433463Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
scan	Post Run actions/checkout@v4	2026-04-16T18:03:12.9671121Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Smart Picks Tracker — **latest** (success / completed) [run 24526607370](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526607370)

Signal lines:

```text
track	Post Run actions/checkout@v4	2026-04-16T18:20:38.9998397Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
track	Post Run actions/checkout@v4	2026-04-16T18:20:39.0224510Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Specialized Scanners - Rocket, Short Engine, TSMOM — **latest** (success / completed) [run 24524677383](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24524677383)

Signal lines:

```text
run-scanners	UNKNOWN STEP	2026-04-16T17:38:44.8096366Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
run-scanners	UNKNOWN STEP	2026-04-16T17:38:44.8316880Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Spike Scanner — **latest** (success / completed) [run 24526896060](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526896060)

*No signal regex hits; last 25 log lines:*

```text
scan	Trigger Spike Scan	2026-04-16T18:24:16.4932909Z ##[endgroup]
scan	Trigger Spike Scan	2026-04-16T18:24:20.0206995Z {"ok":true,"action":"scan_all","crypto":{"count":0,"spikes":[],"scanned":0,"errors":["No crypto data source available"]},"stocks":{"count":0,"spikes":[],"scanned":30,"errors":[]},"forex":{"count":0,"spikes":[],"scanned":17,"errors":[]},"total_spikes":0,"elapsed":"2.27s","tag":"CURSORCODE_Feb152026"}Spike scan triggered
scan	Trigger Pattern Build	﻿2026-04-16T18:24:20.0369008Z ##[group]Run curl -s "https://findtorontoevents.ca/live-monitor/api/pair_fingerprint.php?action=build&key=livetrader2026" || true
scan	Trigger Pattern Build	2026-04-16T18:24:20.0370174Z [36;1mcurl -s "https://findtorontoevents.ca/live-monitor/api/pair_fingerprint.php?action=build&key=livetrader2026" || true[0m
scan	Trigger Pattern Build	2026-04-16T18:24:20.0370828Z [36;1mecho "Pattern build triggered"[0m
scan	Trigger Pattern Build	2026-04-16T18:24:20.0392693Z shell: /usr/bin/bash -e {0}
scan	Trigger Pattern Build	2026-04-16T18:24:20.0393000Z ##[endgroup]
scan	Trigger Pattern Build	2026-04-16T18:24:46.3286736Z {"ok":true,"action":"build","built":47,"pairs_analyzed":47,"errors":[],"elapsed":"25.14s","tag":"CURSORCODE_Feb152026"}Pattern build triggered
scan	Wait for processing	﻿2026-04-16T18:24:46.3322807Z ##[group]Run sleep 30
scan	Wait for processing	2026-04-16T18:24:46.3323118Z [36;1msleep 30[0m
scan	Wait for processing	2026-04-16T18:24:46.3344833Z shell: /usr/bin/bash -e {0}
scan	Wait for processing	2026-04-16T18:24:46.3345144Z ##[endgroup]
scan	Check Status	﻿2026-04-16T18:25:16.3431976Z ##[group]Run echo "Spike Scanner Status:"
scan	Check Status	2026-04-16T18:25:16.3432342Z [36;1mecho "Spike Scanner Status:"[0m
scan	Check Status	2026-04-16T18:25:16.3432849Z [36;1mcurl -s "https://findtorontoevents.ca/live-monitor/api/spike_scanner.php?action=status" | head -c 500[0m
scan	Check Status	2026-04-16T18:25:16.3433350Z [36;1mecho ""[0m
scan	Check Status	2026-04-16T18:25:16.3433576Z [36;1mecho "Pair Fingerprint Status:"[0m
scan	Check Status	2026-04-16T18:25:16.3434427Z [36;1mcurl -s "https://findtorontoevents.ca/live-monitor/api/pair_fingerprint.php?action=status" | head -c 500[0m
scan	Check Status	2026-04-16T18:25:16.3455849Z shell: /usr/bin/bash -e {0}
scan	Check Status	2026-04-16T18:25:16.3456105Z ##[endgroup]
scan	Check Status	2026-04-16T18:25:16.3495212Z Spike Scanner Status:
scan	Check Status	2026-04-16T18:25:16.6686589Z {"ok":true,"engine":"Multi-Asset Spike Scanner","version":"CURSORCODE_Feb152026","active_spikes":0,"total_scans":0,"baselines":82,"last_scan":"never","breakdown":[],"asset_classes":["CRYPTO","STOCK","FOREX"],"methodology":"Real-time volume + price spike detection calibrated per-pair using EWMA baselines. Similar to commercial services like Elxes and MEFAI but integrated with our Pair Fingerprint Engine for asset-specific context. Covers crypto (top 100), stocks\/penny stocks, and forex majors."}
scan	Check Status	2026-04-16T18:25:16.6690249Z Pair Fingerprint Status:
scan	Check Status	2026-04-16T18:25:17.1012195Z {"ok":true,"engine":"Pair Fingerprint Engine","version":"CURSORCODE_Feb152026","fingerprints":47,"active_alerts":0,"last_build":"2026-04-16 18:24:20","last_scan":"never","asset_breakdown":[{"asset_class":"CRYPTO","pairs":"27","avg_wr":0},{"asset_class":"FOREX","pairs":"8","avg_wr":0},{"asset_class":"STOCK","pairs":"12","avg_wr":0}],"methodology":"Per-pair behavioral profiling. Unlike generic indicator strategies, this engine studies each asset's unique patterns: mean-reversion tendency, momentum
scan	Complete job	﻿2026-04-16T18:25:17.1060600Z Cleaning up orphan processes
```

### Sports Betting  Odds Refresh & Auto-Settle — **latest** (success / completed) [run 24526714447](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24526714447)

*No signal regex hits; last 25 log lines:*

```text
odds-refresh	Dashboard summary	2026-04-16T18:20:10.0677024Z ROI: 46.61%
odds-refresh	Dashboard summary	2026-04-16T18:20:10.0677254Z Total PnL: $45.28
odds-refresh	Dashboard summary	2026-04-16T18:20:10.0677511Z Active Bets: 10
odds-refresh	Credit usage check	﻿2026-04-16T18:20:10.0794712Z ##[group]Run echo "=== API Credit Usage ==="
odds-refresh	Credit usage check	2026-04-16T18:20:10.0795116Z [36;1mecho "=== API Credit Usage ==="[0m
odds-refresh	Credit usage check	2026-04-16T18:20:10.0795771Z [36;1mRESULT=$(curl -s --max-time 10 "https://findtorontoevents.ca/live-monitor/api/sports_odds.php?action=credit_usage") || true[0m
odds-refresh	Credit usage check	2026-04-16T18:20:10.0796393Z [36;1mecho "$RESULT" | python3 -c "[0m
odds-refresh	Credit usage check	2026-04-16T18:20:10.0796652Z [36;1mimport sys, json[0m
odds-refresh	Credit usage check	2026-04-16T18:20:10.0796865Z [36;1mtry:[0m
odds-refresh	Credit usage check	2026-04-16T18:20:10.0797058Z [36;1m    d = json.load(sys.stdin)[0m
odds-refresh	Credit usage check	2026-04-16T18:20:10.0797306Z [36;1m    if d.get('ok'):[0m
odds-refresh	Credit usage check	2026-04-16T18:20:10.0797684Z [36;1m        print(f'Monthly used: {d.get(\"monthly_used\",0)}/{d.get(\"monthly_limit\",500)}')[0m
odds-refresh	Credit usage check	2026-04-16T18:20:10.0798182Z [36;1m        print(f'Remaining: {d.get(\"monthly_remaining\",\"?\")}')[0m
odds-refresh	Credit usage check	2026-04-16T18:20:10.0798562Z [36;1m        print(f'Used: {d.get(\"pct_used\",0)}%')[0m
odds-refresh	Credit usage check	2026-04-16T18:20:10.0798834Z [36;1m    else:[0m
odds-refresh	Credit usage check	2026-04-16T18:20:10.0799085Z [36;1m        print(f'Error: {d.get(\"error\",\"unknown\")}')[0m
odds-refresh	Credit usage check	2026-04-16T18:20:10.0799442Z [36;1mexcept: print('Parse error')[0m
odds-refresh	Credit usage check	2026-04-16T18:20:10.0799701Z [36;1m" || echo "Credits: $RESULT"[0m
odds-refresh	Credit usage check	2026-04-16T18:20:10.0821716Z shell: /usr/bin/bash -e {0}
odds-refresh	Credit usage check	2026-04-16T18:20:10.0822007Z ##[endgroup]
odds-refresh	Credit usage check	2026-04-16T18:20:10.0863064Z === API Credit Usage ===
odds-refresh	Credit usage check	2026-04-16T18:20:10.2986760Z Monthly used: 42/500
odds-refresh	Credit usage check	2026-04-16T18:20:10.2987197Z Remaining: 458
odds-refresh	Credit usage check	2026-04-16T18:20:10.2987521Z Used: 8.4%
odds-refresh	Complete job	﻿2026-04-16T18:20:10.3076577Z Cleaning up orphan processes
```

### Strategy Forward Tester — **latest** (- / in_progress) [run 24527624992](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527624992)

*No signal regex hits; last 25 log lines:*

```text
run 24527624992 is still in progress; logs will be available when it is complete
```

### Strategy Genome Evolution — **latest** (- / in_progress) [run 24527654815](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527654815)

*No signal regex hits; last 25 log lines:*

```text
run 24527654815 is still in progress; logs will be available when it is complete
```

### SUPERPOWERS - Bootstrap All 3 ML Systems — **latest** (- / in_progress) [run 24527185464](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527185464)

*No signal regex hits; last 25 log lines:*

```text
run 24527185464 is still in progress; logs will be available when it is complete
```

### Sustained Gainer Confluence Scanner — **latest** (success / completed) [run 24527618414](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527618414)

Signal lines:

```text
sustained-gainer	Post Checkout repository	2026-04-16T18:41:50.4742511Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
sustained-gainer	Post Checkout repository	2026-04-16T18:41:50.4968407Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### System Health Check — **latest** (success / completed) [run 24527286198](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527286198)

Signal lines:

```text
health-check	Post Checkout repository	2026-04-16T18:36:29.5540736Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
health-check	Post Checkout repository	2026-04-16T18:36:29.5765713Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Test Portfolios  Hourly Strategy Validation — **latest** (success / completed) [run 24527852846](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527852846)

Signal lines:

```text
run	Post Run actions/checkout@v4	2026-04-16T18:47:57.9273342Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
run	Post Run actions/checkout@v4	2026-04-16T18:47:57.9497994Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Top Gainers Spike Scanner — **latest** (success / completed) [run 24527432809](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527432809)

Signal lines:

```text
scan	Run top gainers scanner	2026-04-16T18:38:47.3401039Z 18:38:47 [ERROR] HTTP Error 404: Not Found{"quoteSummary":{"result":null,"error":{"code":"Not Found","description":"Quote not found for symbol: MULN"}}}
scan	Post Checkout	2026-04-16T18:39:43.3320830Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
scan	Post Checkout	2026-04-16T18:39:43.3567075Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### TV Paper TP/SL Watchdog — **latest** (success / completed) [run 24527735597](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527735597)

Signal lines:

```text
audit	Post Checkout	2026-04-16T18:45:22.0526607Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
audit	Post Checkout	2026-04-16T18:45:22.0775506Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Unified Audit Dashboard — **latest** (- / pending) [run 24527927103](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527927103)

*No signal regex hits; last 25 log lines:*

```text
run 24527927103 is still in progress; logs will be available when it is complete
```

### Update Creator News — **latest** (success / completed) [run 24527280242](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527280242)

*No signal regex hits; last 25 log lines:*

```text
update-news	Check Result	2026-04-16T18:34:26.3762216Z         {
update-news	Check Result	2026-04-16T18:34:26.3762415Z             "name": "WTFPreston",
update-news	Check Result	2026-04-16T18:34:26.3762679Z             "items_found": 0
update-news	Check Result	2026-04-16T18:34:26.3763034Z         },
update-news	Check Result	2026-04-16T18:34:26.3763218Z         {
update-news	Check Result	2026-04-16T18:34:26.3763416Z             "name": "Xqc",
update-news	Check Result	2026-04-16T18:34:26.3763652Z             "items_found": 0
update-news	Check Result	2026-04-16T18:34:26.3763883Z         },
update-news	Check Result	2026-04-16T18:34:26.3764065Z         {
update-news	Check Result	2026-04-16T18:34:26.3764266Z             "name": "Zarthestar",
update-news	Check Result	2026-04-16T18:34:26.3764516Z             "items_found": 0
update-news	Check Result	2026-04-16T18:34:26.3764746Z         },
update-news	Check Result	2026-04-16T18:34:26.3764928Z         {
update-news	Check Result	2026-04-16T18:34:26.3765128Z             "name": "Zherka",
update-news	Check Result	2026-04-16T18:34:26.3765374Z             "items_found": 0
update-news	Check Result	2026-04-16T18:34:26.3765605Z         },
update-news	Check Result	2026-04-16T18:34:26.3765793Z         {
update-news	Check Result	2026-04-16T18:34:26.3765985Z             "name": "Zople",
update-news	Check Result	2026-04-16T18:34:26.3766223Z             "items_found": 0
update-news	Check Result	2026-04-16T18:34:26.3766446Z         }
update-news	Check Result	2026-04-16T18:34:26.3766635Z     ],
update-news	Check Result	2026-04-16T18:34:26.3766876Z     "message": "Aggregated content for 121 creators",
update-news	Check Result	2026-04-16T18:34:26.3767197Z     "timestamp": "2026-04-16 18:34:26"
update-news	Check Result	2026-04-16T18:34:26.3767458Z }
update-news	Complete job	﻿2026-04-16T18:34:26.3827449Z Cleaning up orphan processes
```

### VOLATILE ALT SCANNER Hyperliquid High-Vol Alts — **latest** (success / completed) [run 24527462857](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527462857)

Signal lines:

```text
volatile-alt-scan	Post Checkout repository	2026-04-16T18:38:01.6071512Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
volatile-alt-scan	Post Checkout repository	2026-04-16T18:38:01.6293920Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```

### Winner Pattern Precursor Scanner — **latest** (success / completed) [run 24527856166](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/24527856166)

Signal lines:

```text
winner-pattern-scan	Post Checkout repository	2026-04-16T18:48:52.2302710Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
winner-pattern-scan	Post Checkout repository	2026-04-16T18:48:52.2524689Z fatal: No url found for submodule path '.pr41-review' in .gitmodules
```
