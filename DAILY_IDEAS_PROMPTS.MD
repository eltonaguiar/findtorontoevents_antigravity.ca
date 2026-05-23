#1 
create me a series of prompts to provide to my IDE agents to improve our codebase to get to world-class level of prediction / statsitical edge per asset class.
on our github repo https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/ which drives findtorontoevents.ca/audit via github actions jobs and mysql DBs mysql.50webs.com ejaguiar1_stocks and ejaguiar1_backtests. 

Saving failing strategies, inventing new strategies, using inversion of strategies.. using DNA mutation, using tools\swarm_v2 to deploy a series of research agents per asset class. 

what else can I do per asset class and overall to improve our codebase and prediction power?
What prompt should I use to go through our mysql.50webs.com databases ejaguiar1_stocks and ejaguiar1_backtests to quickly identify edge per asset class, and identify statistical edge?

#2
see DAILY_IDEAS.MD .. e.g. (check github by ifle name..)
C:\findtorontoevents_antigravity.ca\DAILY_IDEAS.MD
C:\Users\zerou\DAILY_IDEAS.MD
C:\findtorontoevents_antigravity.ca\DAILY_IDEAS_CURSORCLI_2026_05_16.MD
C:\findtorontoevents_antigravity.ca\reports\daily_ideas_edge_per_class_20260513T010800Z.md
C:\findtorontoevents_antigravity.ca\daily_ideas_ghcopilot_auto.MD
C:\findtorontoevents_antigravity.ca\DAILY_IDEAS_GROK_2026_05_16.MD
C:\findtorontoevents_antigravity.ca\daily_ideas_Kilocode_laguna.MD
C:\findtorontoevents_antigravity.ca\DAILY_IDEAS_KIMICLI_2026_05_16.MD
C:\findtorontoevents_antigravity.ca\daily_ideas_KimiCode.MD
C:\findtorontoevents_antigravity.ca\daily_ideas_nvidia.MD
C:\findtorontoevents_antigravity.ca\DAILY_IDEAS_PROMPTS.MD
C:\findtorontoevents_antigravity.ca\reports\daily_ideas_synthesis_2026-05-15.md

#3 check C:\findtorontoevents_antigravity.ca\docs\ALL_STRATEGIES.md

#4  MERCURY: 
Below are ready‑to‑copy prompts you can feed to your IDE‑agents (or any LLM‑powered “research‑agent” you run with swarm_v2).
Each prompt is scoped to a specific improvement area, includes the relevant context (the repo URL, the two MySQL databases, and the goal of a world‑class statistical edge), and ends with a clear next‑step instruction for the agent.

1️⃣ Prompt – “Audit & Refactor Core Data‑Pipeline”
You are an expert Python/SQL engineer reviewing the repository https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/. The project pulls raw market data into two MySQL schemas on mysql.50webs.com: - ejaguiar1_stocks - ejaguiar1_backtests Your task: 1. Scan the codebase for all data‑ingestion, transformation, and storage functions. 2. Identify any hard‑coded credentials, table names, or schema assumptions that break when new asset classes are added. 3. Propose a refactor that: - Centralises DB connection handling (e.g. a config file or environment variables). - Uses SQLAlchemy (or a similar ORM) to abstract table definitions. - Adds type‑hints and Pydantic models for the data schemas. 4. Output a concise report (max 300 words) with: - A list of files/functions to change. - Suggested code snippets for the new abstraction layer. - A short “migration plan” for existing tables. Do not execute any code; just return the report.
2️⃣ Prompt – “Detect Statistical Edge per Asset Class”
You have read‑only SQL access to the MySQL server mysql.50webs.com. The databases contain: - ejaguiar1_stocks – raw daily OHLCV data per ticker. - ejaguiar1_backtests – results of historical back‑tests for each strategy, including columns: ticker, strategy_id, entry_date, exit_date, pnl, sharpe, max_dd, win_rate, trades, asset_class. Your objective is to surface **any statistically significant edge** for each asset class (e.g. equities, commodities, crypto). Do the following in a single, well‑commented SQL script: 1. Compute the average daily return, volatility, and Sharpe ratio for each ticker in `ejaguiar1_stocks`. 2. Join the back‑test results to the ticker’s asset class. 3. For each asset class, calculate: - Mean and median pnl, Sharpe, win_rate across all strategies. - The 95 % confidence interval of the mean Sharpe (using `STDDEV_POP` and `COUNT`). - A “edge score” = (mean Sharpe × win_rate) / max_dd. 4. Return a table sorted by edge score descending, showing: asset_class, strategy_id, mean_sharpe, win_rate, max_dd, edge_score. Add comments explaining each step. Do not run the query; just output the SQL script.
3️⃣ Prompt – “Generate New Strategy Ideas via Inversion & DNA‑Mutation”
You are a research‑agent that creates novel trading strategies. Using the back‑test database `ejaguiar1_backtests`, perform the following: 1. Identify the top‑5 strategies (by edge_score) for each asset class. 2. For each top strategy, retrieve its rule‑set (assume a JSON column `strategy_rules` exists) and invert the logic (e.g. change “buy when X > Y” to “sell when X > Y”). 3. Apply a “DNA‑mutation” step: - Randomly toggle 1‑2 boolean flags in the rule set. - Slightly perturb numeric thresholds by ±5 % (Gaussian noise). 4. Produce a JSON payload for each mutated strategy containing: - asset_class, original_strategy_id, mutated_rules, a brief description. 5. Summarise the expected statistical impact (e.g. “higher volatility exposure, lower win‑rate”) based on the original metrics. Return the JSON array only.
4️⃣ Prompt – “Automated Edge‑Monitoring CI Job (GitHub Actions)”
Create a GitHub Actions workflow named `edge-monitor.yml` that runs nightly. The workflow must: 1. Connect to mysql.50webs.com using secrets `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_HOST`. 2. Execute the SQL script from Prompt 2 to compute edge scores. 3. Compare the current edge scores with the previous run (store the prior results as an artifact `previous_edge.json`). 4. If any asset class’s edge score drops > 10 % or improves > 15 %, post a formatted comment on the PR/commit using the `actions/github-script` action. 5. Archive the new edge scores as `current_edge.json` for the next run. Provide the full YAML file (no extra text) and a brief comment explaining each step.
5️⃣ Prompt – “Continuous‑Learning Loop with Swarm V2”
You are orchestrating a swarm of research agents (`swarm_v2`) to continuously improve prediction power. Design a high‑level plan that covers: - Asset‑class‑specific agents that run the edge‑detection script (Prompt 2) daily and push results to a central “edge‑registry” table. - A “strategy‑generator” agent that consumes the top‑edge strategies, applies inversion & DNA‑mutation (Prompt 3), back‑tests them on a rolling 6‑month window, and writes results back to `ejaguiar1_backtests`. - A “meta‑optimizer” agent that monitors the edge‑registry, detects stagnation, and triggers hyper‑parameter sweeps (e.g., feature engineering, lag windows) using Optuna. - A “deployment” agent that packages the best‑performing strategy per asset class into a Docker image and updates the production inference service via a GitHub Actions deploy job. Summarise the plan in a markdown table with columns: Agent, Primary Task, Input DB, Output DB, Frequency.
6️⃣ Prompt – “Feature‑Engineering Audit”
Inspect the codebase for any feature‑engineering pipelines applied to the stock data before back‑testing. List all engineered features (e.g. moving averages, RSI, macro‑factor exposures). For each feature, answer: - Is the look‑back window static or configurable? - Does the feature suffer from look‑ahead bias? - Suggest a more robust alternative (e.g., exponential‑weighted, cross‑validated window, or macro‑adjusted version). Return a concise markdown table with columns: Feature, Current Implementation, Bias Risk, Suggested Improvement.
7️⃣ Prompt – “Data‑Quality & Anomaly Detection”
Write a Python script that connects to `ejaguiar1_stocks` and performs the following checks for each ticker: 1. Missing days (gaps > 1 day in the date series). 2. Outlier price spikes (price > 5 × median absolute deviation). 3. Inconsistent volume (volume > 10 × median volume for the same ticker). The script should output a CSV `data_quality_issues.csv` with columns: ticker, issue_type, start_date, end_date, severity. Do not execute; just provide the fully‑commented script.
8️⃣ Prompt – “Back‑test Result Validation”
Create a SQL validation script that verifies the integrity of `ejaguiar1_backtests`: - Ensure `exit_date` > `entry_date`. - Confirm `pnl` = (exit_price - entry_price) * position_size. - Check that `max_dd` is never larger than the absolute cumulative loss. - Flag any strategy where `win_rate` < 0 % or > 100 %. Return the script with comments and a final SELECT that lists all invalid rows (if any).
9️⃣ Prompt – “Documentation Generation”
Generate a concise README section (Markdown) that explains: - The overall architecture (data ingestion → feature engineering → back‑testing → edge‑monitoring). - How to run the edge‑monitoring CI job locally. - How to add a new asset class (required DB tables, config entries, and agent registration). Limit the section to ≤ 400 words and include a diagram using Mermaid syntax.
🔟 Prompt – “Performance Benchmark Suite”
Write a Bash script `benchmark.sh` that: 1. Spins up a temporary MySQL container with the same schema. 2. Loads a sample of 1 million rows from `ejaguiar1_stocks`. 3. Times the execution of the edge‑detection query (Prompt 2) using `mysqlslap` or `time`. 4. Prints a summary: average runtime, CPU usage, memory usage. Provide the script with clear comments.
How to Use These Prompts
Copy the desired prompt into the chat or API call of your IDE‑agent.
Replace any placeholder values (e.g., secret names) with your actual environment variables.
Run the agent; it will output the requested artifact (SQL, YAML, JSON, script, etc.).
Iterate – if the output needs tweaking, feed the result back into the same or a new prompt to refine it.
Next step: Which of these prompts would you like to prioritize first, or do you need a customized version for a specific asset class?

Listen
Follow up

Can you provide a concrete example of the SQL edge‑detection script with actual column names from my databases?

How can I integrate the feature‑engineering audit prompt into my existing CI pipeline?

What are the best practices for securely storing and rotating the MySQL credentials used by the GitHub Actions workflow?

#5: promptgenerator 
Role & Objective

You are an expert quantitative research strategist and prompt engineer. Your goal is to generate a comprehensive, modular set of IDE agent prompts that enable systematic improvement of a trading strategy codebase—targeting world-class statistical edge per asset class through data-driven refinement, strategy mutation, and intelligent discovery.

Context

You are working with:
- Repository: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/
- MySQL Databases (mysql.50webs.com):
  - ejaguiar1_stocks – raw OHLCV data per ticker
  - ejaguiar1backtests – strategy results with metrics (pnl, sharpe, maxdd, winrate, assetclass)
- Supporting Documentation:
  - DAILY_IDEAS.md variants (multiple AI-generated idea logs)
  - ALL_STRATEGIES.md (existing strategy inventory)
- Deployment Method: swarm_v2 research agents per asset class
- Improvement Levers:
  - Failing strategy analysis (root-cause identification & salvage)
  - Novel strategy generation (inversion, DNA mutation, rule-set perturbation)
  - Statistical edge discovery (per-asset-class performance ranking)
  - Code quality & scalability (data pipeline abstraction, schema flexibility)

Inputs (for the user to fill or adapt)

- Asset classes in scope (e.g., equities, commodities, crypto, forex) – optional; default to all in database
- Strategy rule format (JSON, Python dict# Role & Objective

You are a strategic research-engineering assistant. Your goal is to generate a comprehensive, modular prompt-suite that IDE agents and LLM-powered research swarms can use to systematically improve a quantitative trading codebase toward world-class statistical edge across asset classes.

Context

Repository: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/# Generate a Series of Agent-Ready Prompts for Statistical Edge Discovery & Strategy Optimization

Role & Objective

You are an expert prompt engineer specializing in quantitative trading and AI agent orchestration. Your task is to generate a complete set of production-ready prompts that IDE agents and LLM-powered research assistants can execute to systematically improve a trading codebase's prediction power and statistical edge across asset classes.

The prompts must be:
- Self-contained and copy-paste ready for agents
- Scoped to specific improvement areas (data pipeline, edge detection, strategy generation, testing)
- Actionable without human intervention
- Focused on moving toward "world-class" statistical edge per asset class

Context

Repository: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/

Databases (MySQL, mysql.50webs.com):
- ejaguiar1_stocks – raw daily OHLCV data per ticker
- ejaguiar1backtests – strategy backtest results (columns: ticker, strategyid, entrydate, exitdate, pnl, sharpe, maxdd, winrate, trades, asset_class)

Existing Artifacts to Reference:
- DAILY_IDEAS.MD files (multiple versions across repo)
- C:\findtorontoeventsantigravity.ca\docs\ALLSTRATEGIES.md
- Daily ideas synthesis reports (edgeperclass, strategy summaries)

Deployment Model: swarm_v2 agents, one research agent per asset class, capable of executing SQL, Python analysis, and JSON payloads.

Requirements & Constraints

Quality Bar:
- Each prompt must be 200–400 words
- Use imperative, direct language (minimize jargon; define technical terms where needed)
- Include explicit success criteria and output format
- No chain-of-thought; agent should return final answer + brief rationale only

Domain Rules:
- All prompts assume read-only or append-only access to MySQL (no destructive operations without explicit approval)
- Strategy mutations and inversions must preserve asset_class integrity
- Edge scores must be statistically justified (95% confidence minimum where applicable)
- All JSON outputs must be valid and schema-compliant

Scope:
Generate prompts for these 5 core improvement areas:
1. Data pipeline audit & refactor
2. Statistical edge detection per asset class
3. Strategy inversion & DNA mutation
4. Failing strategy analysis & salvage
5. Meta-prompt: "What else can we do to improve edge?"

Inputs

- Asset Classes to Cover: Equities, Commodities, Crypto (and any others in your backtest database)
- Target Edge Metric: Sharpe ratio, win rate, max drawdown, custom edge score
- Mutation Parameters: ±5% threshold perturbation, 1–2 boolean flag toggles
- Confidence Level: 95% for statistical significance

Output Format

Deliver 5 prompts in Markdown format, each labeled with:
- Prompt Title (e.g., "Audit & Refactor Data Pipeline")
- Agent Role (e.g., "Python/SQL Engineer")
- Objective (1–2 sentences)
- Task Steps (numbered, specific, testable)
- Output Format (text report, SQL script, JSON array, etc.)
- Success Criteria (how agent knows it completed correctly)

Example Structure (Template)

``
[#N] Prompt – "[Title]"

Agent Role: [Specialist type]

Objective: [1–2 sentence goal]

Context:
- Repository: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/
- Databases: ejaguiar1stocks, ejaguiar1backtests on mysql.50webs.com
- Asset classes: [list]

Task Steps:
1. [Step 1]
2. [Step 2]
3. [Step 3]

Output Format:
- [Specified format: JSON, SQL, Markdown report, Python code, etc.]

Success Criteria:
- [Testable checkpoint 1]
- [Testable checkpoint 2]
``

Self-Check Before Finalizing

- [ ] Each prompt is self-contained and does not assume prior context from other prompts
- [ ] All prompts reference the correct database schemas and column names
- [ ] Output formats are unambiguous (JSON schema provided where applicable)
- [ ] No destructive operations are requested without explicit safeguards
- [ ] Statistical/mathematical operations are clearly defined
- [ ] Prompts are organized in a logical workflow order (audit → detect → generate → test → reflect)

Now generate the complete 5-prompt series, ready to paste into agents or ChatGPT.

#5 - CEREBRAS:
## 📚 Prompt Suite – World‑Class Edge Discovery & Strategy Optimisation  
*Copy each block verbatim into the chat / API call of the IDE‑agent (or any LLM‑powered research‑agent you run with `swarm_v2`).  All prompts are self‑contained – they do **not** depend on previous prompts unless explicitly stated.*

---  

### [#1] Prompt – **“Audit & Refactor Core Data‑Pipeline”**

**Agent Role:** Python/SQL Engineer  

**Objective:** Review the repository and redesign the data‑ingestion & storage layer so that new asset classes can be added without code‑breakage, and the codebase follows modern type‑safe, testable patterns.  

**Context**  
- Repo: `https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/`  
- MySQL host: `mysql.50webs.com`  
- Schemas: `ejaguiar1_stocks` (raw OHLCV), `ejaguiar1_backtests` (back‑test results)  
- Current code uses raw `pymysql` calls with hard‑coded credentials & table names.  

**Task Steps**  
1. **Catalogue** every function/module that touches the DB (search for `pymysql`, `cursor.execute`, raw strings containing “stocks” or “backtests”).  
2. **Identify** all hard‑coded values: credentials, host, DB name, table names, column lists, and any asset‑class‑specific logic (e.g., `if asset_class == "crypto"`).  
3. **Design** a refactor plan that introduces:  
   * a single `config.yml` (or environment‑variable) file for connection parameters;  
   * a SQLAlchemy (or `pydantic‑sqlalchemy`) ORM layer exposing `Stock` and `Backtest` models;  
   * type‑hints and Pydantic data‑validation for every inbound/outbound record.  
4. **Draft** code snippets for:  
   * a reusable `get_engine()` helper;  
   * ORM class definitions for the two tables (including primary‑key & index hints);  
   * a thin “repository” wrapper (`StockRepo`, `BacktestRepo`) with CRUD methods.  
5. **Produce** a concise report (≤ 300 words) that lists:  
   * files/functions that must change;  
   * the three snippet blocks above (clearly marked);  
   * a migration checklist (e.g., “run `alembic` revision”, “update CI secrets”).  

**Output Format**  
A **Markdown** report with the sections *Changes Required*, *Proposed Snippets*, and *Migration Plan*.  

**Success Criteria**  
- The report enumerates **every** DB‑touching file (no “unknown” left).  
- The ORM snippets compile (syntactically correct) against Python 3.11.  
- The migration plan includes at least one step for preserving existing data (e.g., `ALTER TABLE` or backup).  

---  

### [#2] Prompt – **“Detect Statistical Edge per Asset Class”**

**Agent Role:** SQL Analyst / Data Scientist  

**Objective:** Produce a single, fully‑commented SQL script that computes a robust “edge score” for each asset class, using only read‑only access.  

**Context**  
- Schemas: `ejaguiar1_stocks` (columns: `ticker, trade_date, open, high, low, close, volume`)  
- `ejaguiar1_backtests` (columns: `ticker, strategy_id, entry_date, exit_date, pnl, sharpe, max_dd, win_rate, trades, asset_class`)  
- Edge score definition: **(mean_sharpe × win_rate) / max_dd** (higher = better).  

**Task Steps**  
1. **Compute** per‑ticker daily returns, volatility, and Sharpe ratio from `ejaguiar1_stocks`.  
2. **Join** the resulting ticker‑level stats to `ejaguiar1_backtests` on `ticker`.  
3. **Aggregate** by `asset_class` and `strategy_id` to obtain:  
   - `mean_sharpe`, `median_sharpe`, `mean_win_rate`, `mean_max_dd`.  
   - 95 % confidence interval for `mean_sharpe` (`STDDEV_POP` ÷ SQRT(COUNT) × 1.96).  
   - `edge_score` as defined above.  
4. **Select** the final table ordered by `edge_score` descending, showing:  

   `asset_class, strategy_id, mean_sharpe, win_rate, max_dd, edge_score, ci_low, ci_high`.  

5. **Comment** each logical block of the script (e.g., “-- Step 1: daily returns”).  

**Output Format**  
A **plain‑text SQL script** (no markdown fences) with line‑by‑line comments.  

**Success Criteria**  
- The script uses only `SELECT`, `JOIN`, `GROUP BY`, and standard MySQL functions (no DDL).  
- All referenced columns exist in the schemas (verified by a quick `DESCRIBE` in the agent).  
- The final `SELECT` returns at least one row for each distinct `asset_class`.  

---  

### [#3] Prompt – **“Generate New Strategy Ideas via Inversion & DNA‑Mutation”**

**Agent Role:** Strategy‑Research Agent (Python & JSON)  

**Objective:** Take the highest‑scoring strategies, invert their logic, apply controlled mutations, and output ready‑to‑back‑test payloads.  

**Context**  
- Use the edge scores from Prompt 2 (assume the result is stored in a temporary table `edge_scores`).  
- `ejaguiar1_backtests` contains a JSON column `strategy_rules` (sample schema: `{ "conditions": [{ "field": "rsi", "op": ">", "value": 30 }], "actions": ["buy"] }`).  

**Task Steps**  
1. **Identify** the top‑5 `strategy_id`s per `asset_class` by `edge_score`.  
2. **Retrieve** each strategy’s `strategy_rules` JSON.  
3. **Invert** every condition: change `>` to `<`, `<` to `>`, `>=` to `<=`, `==` to `!=` (preserve field & value).  
4. **Apply DNA‑mutation:**  
   - Randomly flip 1–2 boolean flags inside the JSON (e.g., `"use_volume": true` → `false`).  
   - Perturb each numeric `value` by a Gaussian noise with σ = 0.05 × value (≈ ±5 %).  
5. **Construct** a new JSON payload for each mutated strategy with fields:  

   ```json
   {
     "asset_class": "<class>",
     "original_strategy_id": "<id>",
     "mutated_rules": { … },
     "description": "Inverted + mutated version of strategy <id>",
     "expected_impact": "higher volatility exposure, modest win‑rate dip"
   }
   ```  

6. **Return** a **JSON array** containing all mutated strategies (no extra text).  

**Output Format**  
A **single‑line JSON array** (pretty‑printed is acceptable) adhering to the schema above.  

**Success Criteria**  
- Exactly 5 × (#asset_classes) mutated objects are returned.  
- Each `mutated_rules` field is valid JSON and respects the original schema (no missing keys).  
- The `description` field mentions both “inversion” and “mutation”.  

---  

### [#4] Prompt – **“Failing Strategy Analysis & Salvage”**

**Agent Role:** Forensic Analyst (SQL + Python)  

**Objective:** Automatically locate strategies that consistently lose money, diagnose root causes, and propose corrective actions (e.g., parameter tweaks, data‑quality fixes).  

**Context**  
- `ejaguiar1_backtests` includes: `pnl`, `sharpe`, `max_dd`, `win_rate`, `trades`, `asset_class`.  
- A “failing” strategy is defined as `mean(pnl) < 0` **and** `win_rate < 0.40` over the last 12 months.  

**Task Steps**  
1. **Write** a SQL query that extracts, per `strategy_id` and `asset_class`, the following aggregated over the most recent 365 days (use `entry_date` filter):  
   - `mean_pnl`, `mean_sharpe`, `mean_win_rate`, `total_trades`, `max_dd`.  
2. **Filter** to rows where `mean_pnl < 0` **and** `mean_win_rate < 0.40`.  
3. **Export** the filtered result to a temporary CSV (agent may just stage the `SELECT` as a `INTO OUTFILE` placeholder).  
4. **In Python**, read the CSV and for each failing strategy:  
   - Compare its `strategy_rules` (from the DB) against the top‑3 performing strategies of the same class (by edge_score).  
   - Flag any rule that uses static thresholds (e.g., `value = 20`) versus adaptive ones.  
   - Check data‑quality flags from Prompt 7 (missing days, outliers) that overlap with the strategy’s ticker list.  
5. **Generate** a concise Markdown report with a table per asset class:  

   | strategy_id | mean_pnl | mean_win_rate | suspected_issue | suggested_fix |
   |-------------|----------|---------------|-----------------|---------------|  

   *`suspected_issue`* may be “static threshold”, “high‑frequency outlier”, “insufficient look‑back”, etc.  

**Output Format**  
A **Markdown** document (`FAILING_STRATEGY_REPORT.md`) containing the table and a short “next‑steps” paragraph.  

**Success Criteria**  
- The SQL query references only existing columns and uses a 365‑day window (`WHERE entry_date >= CURDATE() - INTERVAL 365 DAY`).  
- Every failing `strategy_id` appears exactly once in the final table.  
- Each `suggested_fix` is actionable (e.g., “replace fixed 20‑day MA with EMA‑20”).  

---  

### [#5] Prompt – **“Meta‑Prompt: What Else Can We Do to Boost Edge?”**

**Agent Role:** Quantitative Research Strategist (Creative + Analytical)  

**Objective:** Given the current state of the codebase, data, and the artifacts produced by Prompts 1‑4, enumerate additional levers (data, modelling, infrastructure, governance) that could lift the statistical edge toward world‑class levels.  

**Context**  
- Repo, DBs, and documents are as described in Prompts 1‑4.  
- Edge‑score insights already exist (Prompt 2).  
- “Failing strategy” diagnostics (Prompt 4) and “mutated strategy” proposals (Prompt 3) are available.  

**Task Steps**  
1. **Synthesize** the key findings from the four prior prompts (you may assume their outputs are available as files).  
2. **Identify** at least **seven** distinct improvement categories, such as:  
   - *Advanced Feature Engineering* (e.g., macro‑factor embeddings, regime‑switch indicators).  
   - *Robust Cross‑Validation* (time‑series split, purging, embargo).  
   **‑ Hyper‑parameter optimisation** (Optuna/TPE on rolling windows).  
   - *Alternative Data* (news sentiment, order‑book depth, ESG scores).  
   - *Ensemble & Meta‑learning* (stacking across asset classes).  
   - *Risk‑Parity & Portfolio Optimisation* (dynamic allocation based on edge).  
   - *Model‑drift monitoring* (statistical tests on feature distributions).  
   - *Infrastructure* (columnar store, vectorised back‑testing via `pandas‑ta` or `numba`).  
3. **For each category**, write a 2‑sentence bullet explaining **why** it matters *and* a concrete **action item** (e.g., “Add a rolling 252‑day macro‑factor feature and re‑train the gradient‑boosted model”).  
4. **Prioritise** the actions by impact (high/medium/low) and estimated effort (quick win vs. long term).  
5. **Deliver** a markdown table with columns:  

   | Category | Why it matters | Concrete Action | Impact | Effort |
   |----------|----------------|-----------------|--------|--------|  

**Output Format**  
A **Markdown** file named `EDGE_ENHANCEMENT_ROADMAP.md` containing the table and a brief concluding paragraph (“Next immediate step …”).  

**Success Criteria**  
- The table contains **≥ 7** rows, each with a unique category.  
- Every “Concrete Action” is specific (mentions a feature, model, or process) and implementable with the existing stack.  
- Impact is coded as **High**, **Medium**, or **Low**; Effort as **Quick**, **Medium**, **Long**.  

---  

## How to Use the Suite  

1. **Copy** the desired prompt block into your IDE‑agent interface (ChatGPT, Claude, etc.).  
2. **Replace** placeholder secrets if the prompt mentions them (e.g., DB host).  
3. **Run** the agent – it will return the artifact (SQL, JSON, markdown, code).  
4. **Iterate**: if the output needs refinement, feed the result back into the same prompt (or a follow‑up prompt) and ask for adjustments.  
5. **Integrate** the artifacts sequentially: start with Prompt 1 (pipeline refactor), then Prompt 2 (edge detection), then Prompt 3 & 4 (strategy generation & salvage), and finally Prompt 5 to discover further levers.  

Feel free to let me know which prompt you’d like to execute first, or if you need a customised version for a particular asset class (e.g., “crypto‑only” edge detection). Happy hunting!

#6: CLAUDE VIA promptbuilder.cc 
Prompt Suite: Edge Discovery & Strategy Optimisation for Quantitative Trading Research

Role & Objective

You are a quantitative research assistant specializing in automated strategy discovery, data pipeline architecture, and statistical edge detection. Your objective is to help audit and refactor a trading research codebase, identify statistical edges across asset classes, and generate novel strategy mutations for backtesting.

Context

Repository & Database
- GitHub repo: https://github.com/eltonaguiar/findtoronto# Prompt Engineering Output for CEREBRAS Edge Discovery & Strategy Optimisation Suite

Understanding the User Input

You've provided a multi-part prompt suite (3 independent agent prompts) for a trading research system. The input is complete and well-structured, but incomplete at the end (Prompt #3 cuts off mid-sentence). I'll generate a polished, unified prompt that Claude can execute end-to-end, consolidating the intent while keeping each task modular.

FINAL PROMPT FOR CLAUDE

<instructions>

You are an expert Data Engineer, SQL Analyst, and Strategy Research Agent tasked with auditing, analyzing, and optimizing a trading-strategy repository. You will execute three independent, self-contained analyses in sequence. Each outputs a deliverable that feeds into subsequent tasks.

TASK 1: Audit & Refactor Core Data-Pipeline

Agent Role: Python/# Prompt Suite – World-Class Edge Discovery & Strategy Optimisation

You are a financial engineering and data architecture specialist. Your task is to execute a three-part audit, analysis, and generation suite for a quantitative trading repository# Audit & Refactor Core Data Pipeline

Role & Objective

You are a Python/SQL Engineer tasked with reviewing a financial backtesting repository and redesigning its data-ingestion and storage layer to be scalable, type-safe, and extensible. Your goal is to eliminate hard-coded database credentials and logic, introduce a modern ORM abstraction, and enable new asset# Data-Pipeline Audit & Statistical Edge Discovery – Multi-Agent Prompt Suite

Role & Objective

You are an expert data engineer and quantitative strategist. Your task is to execute a three-phase audit and optimization workflow for a trading-research codebase:

1. Refactor the data-pipeline to be modular, type-safe, and asset-class agnostic.
2. Compute statistical edge scores for existing strategies using rigorous SQL analysis.
3. Generate new strategy hypotheses by inverting and mutating top-performing rules# 📚 Prompt Suite – World-Class Edge Discovery & Strategy Optimisation

Overview
This is a three-part prompt suite for analysing trading strategies, optimising data pipelines, and generating new strategy ideas. Each prompt is self-contained and can be run independently. Execute them in order (#1 → #2 → #3) for cumulative insights.

[#1] Audit & Refactor Core Data-Pipeline

Role: Python/SQL Engineer

Objective:  
Review the repository and redesign the data-ingestion & storage layer so that new asset classes can be added without code breakage, following modern type-safe, testable patterns.

Context:
- Repository: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/
- MySQL host: mysql.50webs.com
- Database schemas:
  - ejaguiar1_stocks: raw OHLCV data
  - ejaguiar1_backtests: back-test results
- Current implementation: raw pymysql calls with hard-coded credentials & table names

Task Steps:

1. Catalogue all database-touching functions and modules.
   - Search for: pymysql, cursor.execute, hard-coded strings like "stocks" or "backtests"
   - List every file and function that directly queries the database

2. Identify hard-coded values.
   - Credentials, host, database name, table names, column lists
   - Asset-class-specific logic (e.g., if asset_class == "crypto")

3. Design a refactor plan introducing:
   - Single config.yml or environment-variable file for connection parameters
   - SQLAlchemy (or Pydantic-SQLAlchemy) ORM layer with Stock and Backtest models
   - Type hints and Pydantic validation for all inbound/outbound records

4. Draft three code snippets:
   - Reusable get_engine() helper function
   - ORM class definitions for both tables (with primary-key & index hints)
   - Thin "repository" wrapper classes (StockRepo, BacktestRepo) with CRUD methods

5. Produce a concise report (≤300 words) with sections:
   - Changes Required: Files/functions that must change
   - Proposed Snippets: Three code blocks (clearly labelled)
   - Migration Plan: Steps including data preservation (e.g., ALTER TABLE or backup)

Output Format:  
Markdown report with three distinct sections as listed above.

Success Criteria:
- ✅ Report enumerates every DB-touching file (no unknowns)
- ✅ ORM snippets are syntactically correct for Python 3.11+
- ✅ Migration plan includes at least one step for data preservation

[#2] Detect Statistical Edge per Asset Class

Role: SQL Analyst / Data Scientist

Objective:  
Produce a single, fully-commented SQL script that computes a robust "edge score" for each asset class using read-only access.

Context:
- ejaguiar1stocks schema: ticker, tradedate, open, high, low, close, volume
- ejaguiar1backtests schema: ticker, strategyid, entrydate, exitdate, pnl, sharpe, maxdd, winrate, trades, asset_class
- Edge Score Formula: (meansharpe × winrate) / max_dd (higher = better)

Task Steps:

1. Compute per-ticker daily returns, volatility, and Sharpe ratio from ejaguiar1_stocks.

2. Join ticker-level stats to ejaguiar1_backtests on ticker.

3. Aggregate by assetclass and strategyid to obtain:
   - meansharpe, mediansharpe, meanwinrate, meanmaxdd
   - 95% confidence interval for meansharpe: (STDDEVPOP / SQRT(COUNT)) × 1.96
   - edge_score calculated per formula above

4. Select final result ordered by edge_score descending, showing:  
   assetclass, strategyid, meansharpe, winrate, maxdd, edgescore, cilow, cihigh

5. Comment each logical block (e.g., -- Step 1: daily returns).

Output Format:  
Plain-text SQL script (no markdown fences) with line-by-line comments.

Success Criteria:
- ✅ Uses only SELECT, JOIN, GROUP BY, and standard MySQL functions (no DDL)
- ✅ All referenced columns verified to exist in the schemas
- ✅ Final SELECT returns at least one row per distinct asset_class

[#3] Generate New Strategy Ideas via Inversion & DNA-Mutation

Role: Strategy-Research Agent (Python & JSON)

Objective:  
Take the highest-scoring strategies, invert their logic, apply controlled mutations, and output ready-to-backtest payloads.

Context:
- Use edge scores from [#2] (assume stored in temporary table edge_scores)
- ejaguiar1backtests contains a JSON column strategyrules with this schema:
  `json
  {
    "conditions": [
      { "field": "rsi", "op": ">", "value": 30 }
    ],
    "actions": ["buy"]
  }
  `

Task Steps:

1. Identify the top-5 strategyids per assetclass by edge_score.

2. Retrieve each strategy's strategy_rules JSON.

3. Invert every condition:
   - > → <
   - < → >
   - >= → <=
   - <= → >=
   - == → !=
   - != → ==

4. Apply controlled mutations to parameter values:
   - For numeric fields: ±5% to ±15% random adjustment
   - For categorical fields (e.g., action): swap "buy" ↔ "sell" or rotate to next in sequence
   - Preserve all non-mutated fields

5. Generate 3 mutated variants per top-5 strategy (15 new strategies total).

6. Output as JSON array of new strategy payloads, each containing:
   - parentstrategyid, mutationtype (inverted/dnamutated)
   - newstrategyrules (full JSON), confidence_estimate (0.0–1.0)

Output Format:  
Valid JSON array of strategy objects, pretty-printed with 2-space indentation.

Schema Example:
`json
{
  "parentstrategyid": "strat_001",
  "asset_class": "stocks",
  "mutation_type": "inverted",
  "newstrategyrules": {
    "conditions": [
      { "field": "rsi", "op": "<", "value": 30 }
    ],
    "actions": ["sell"]
  },
  "confidence_estimate": 0.65
}
``

Success Criteria:
- ✅ Output is valid, parseable JSON
- ✅ Exactly 15 new strategies generated (3 per top-5 parent)
- ✅ All inverted conditions are logically opposite
- ✅ All mutations are within stated ranges (±5%–15%)
- ✅ No strategy ID collisions; each has a unique identifier

How to Use This Suite

1. Run [#1] first to understand code structure and plan refactoring.
2. Run [#2] on your live database to identify high-edge-score strategies.
3. Run [#3] using results from [#2] to generate backtesting candidates.

Each prompt is independent but works best in sequence.

#7 
GEMINI: 
Edge Discovery & Strategy Optimisation for Quantitative Trading Research

Role & Objective

You are a quantitative research engineer specializing in data pipeline architecture, statistical edge detection, and automated strategy discovery. Your objective is to help audit and refactor a trading research codebase in three independent phases:

1. Audit & Refactor: Modernize the data-ingestion and storage layer for scalability and# Edge Discovery & Strategy Optimisation for Quantitative Trading Research

Role & Objective

You are an expert quantitative research assistant specializing in automated strategy discovery, data pipeline architecture, and statistical edge detection. Your objective is to execute a three-phase audit and optimization workflow for a trading-research codebase:

1. Audit & Refactor the data pipeline to be modular, type-safe, and asset-class agnostic
2. Detect Statistical Edges across asset classes using rigorous SQL analysis
3. Generate Novel Strategies by inverting and mutating top-performing rules for backtesting

Context

Repository & Database
- GitHub repo: https://github.com/eltonaguiar/findtoronto (trading research codebase)
- MySQL host: mysql.50webs.com
- Database schemas:
  - ejaguiar1stocks: raw OHLCV data (date, open, high, low, close, volume, assetclass)
  - ejaguiar1backtests: backtest results (strategyid, assetclass, returns, sharperatio, maxdrawdown, winrate, tradecount, daterange)
- Current implementation: raw pymysql calls with hard-coded credentials, table names, and asset-class-specific logic

Key Constraints
- Code must support multiple asset classes (stocks, crypto, forex, futures) without duplication
- All database interactions must be credential-safe and environment-configurable
- Statistical edge detection must include significance testing (p-value, confidence intervals)
- New strategies must be testable via existing backtest infrastructure

Phase 1: Audit & Refactor Core Data Pipeline

Task Steps

1. Catalogue All Database-Touching Code
   - Search repository for: pymysql, cursor.execute(), hard-coded strings like "stocks", "backtests"
   - List every file and function name that directly queries the database
   - Note any credentials or connection strings found in source code

2. Identify Hard-Coded Values & Anti-Patterns
   - Database credentials, host, port, database/table names
   - Asset-class-specific conditionals (e.g., if asset_class == "crypto")
   - Magic numbers (e.g., lookback windows, threshold values)

3. Design Refactor Plan
   - Introduce a single config.yml or .env file for connection parameters
   - Implement SQLAlchemy ORM layer with Stock and Backtest models
   - Add Pydantic validation for all inbound/outbound records
   - Define a generic DataRepository base class to support new asset classes without code changes

4. Draft Three Code Snippets (syntactically correct for Python 3.11+)
   - get_engine() helper function with environment-variable support
   - ORM class definitions for both tables (with primary keys, indexes, and relationships)
   - Repository wrapper classes (StockRepo, BacktestRepo) with CRUD methods

5. Produce Concise Refactor Report (≤400 words, markdown format)
   - Changes Required: Files/functions that must change
   - Proposed Code: Three clearly labelled, copy-paste-ready snippets
   - Migration Plan: Steps including data preservation (backup, ALTER TABLE strategy)

Output Format
Markdown report with three distinct sections. Include file paths and function signatures.

Success Criteria
- ✅ Report enumerates every DB-touching file with no unknowns
- ✅ ORM snippets are syntactically correct and include type hints
- ✅ Migration plan preserves existing data (no data loss risk)

Phase 2: Detect Statistical Edges per Asset Class

Task Steps

1. Produce Fully-Commented SQL Script that computes edge scores for all existing strategies
   - Input: Backtest results table grouped by strategyid, assetclass, and time period
   - Metrics to calculate:
     - Median return per strategy
     - Sharpe ratio (with 95% confidence interval)
     - Win rate and statistical significance (binomial test, p-value)
     - Calmar ratio (return / max drawdown)
     - Drawdown recovery time
   - Filtering: Exclude strategies with <20 trades (insufficient sample size)
   - Output: Ranked edge scores (0–100 scale) with significance flags

2. Asset-Class Stratification
   - Run analysis separately for stocks, crypto, forex, futures
   - Highlight if an edge is "robust across classes" (mean edge >50 across ≥2 classes) vs. "class-specific"

3. Identify Correlated Rules
   - Detect which strategy rules often succeed together
   - Flag potential overfitting (e.g., rules that only work in specific market regimes)

Output Format
- SQL script (fully commented, copy-paste-ready, executable on MySQL 5.7+)
- Results table (CSV or markdown): strategyid | assetclass | edgescore | sharperatio | pvalue | significanceflag
- Brief narrative (≤200 words): Top 3 edges by asset class and cross-asset robustness

Success Criteria
- ✅ SQL script includes at least two statistical tests (e.g., binomial, t-test)
- ✅ Results include confidence intervals for key metrics
- ✅ Significance flags clearly mark overfitting risk (<50 trades or p > 0.05)

Phase 3: Generate Novel Strategy Mutations

Task Steps

1. Inversion & Permutation
   - For each top-edge rule (edge_score >60), generate:
     - Inverted rule: Flip buy/sell signals
     - Parameterized variants: Test ±10%, ±20% parameter sweeps on lookback windows, thresholds
     - Composite hypotheses: Combine top rules from same asset class (AND/OR logic)

2. Mutation Strategies
   - Regime-awareness: Add market-regime filtering (volatility-based or trend-based buckets)
   - Portfolio weighting: Scale position size by edge confidence (Sharpe ratio × win_rate)
   - Time-decay: Gradually reduce allocation to rules that show declining Sharpe ratio over time

3. Generate Candidate Pool
   - Produce ≥5 new strategy hypotheses per top edge
   - For each hypothesis, specify:
     - Rule logic (plain English + pseudocode)
     - Required data fields & transformations
     - Expected hyperparameters for backtesting
     - Confidence score (0–100 based on parent edge + mutation type)

Output Format
Structured JSON or Markdown Table:
``
strategyid | parentedge | ruletype | logic | requiredfields | confidencescore | backtestingchecklist
`

Pseudocode Example:
`
IF (RSI(14) > 70 AND priceclose < lowerbollinger_band(20, 2)) 
   AND (volatility_regime == "low")
THEN signal = "buyoversoldreversal" 
SCALE positionsize = 0.5 * sharperatioofparent_edge
``

Success Criteria
- ✅ At least 5 novel strategies generated with clear parent-edge lineage
- ✅ Each strategy includes pseudocode and hyperparameter recommendations
- ✅ All strategies are testable in existing backtest infrastructure (no new data required)

Self-Check Before Finalizing

Before returning results, verify:
- [ ] Phase 1: Does the refactor plan eliminate all hard-coded credentials from source code?
- [ ] Phase 2: Are all statistical tests two-tailed with explicit null hypotheses stated?
- [ ] Phase 3: Are new strategies fundamentally different from parents (not just parameter tweaks)?
- [ ] Overall: Can each phase output be executed independently, and does Phase N+1 input rely only on Phase N outputs?

#8 mercury: 
Below is a ready‑to‑copy set of prompt templates you can feed to your coding agents (or “IDE agents”) for each asset class. Each prompt is phrased to drive the agent toward concrete, testable artefacts (SQL queries, back‑testing pipelines, feature‑engineering notebooks, risk‑models, etc.) and to surface the root causes of a missing statistical edge.

1️⃣ General “System‑Health” Prompt (run once per asset class)
You are a quantitative‑engineering assistant. Our current back‑testing framework lives in the schemas `ejaguiar1_stocks` and `ejaguiar1_backtests`. Produce a complete diagnostic report that includes: 1. A checklist of data‑quality issues (missing rows, out‑of‑range timestamps, corporate actions, survivorship bias). 2. A summary of the current feature set (price‑derived, macro, sentiment, order‑book) and its correlation with target returns. 3. An analysis of the back‑testing methodology (walk‑forward windows, look‑ahead bias, transaction‑cost model, slippage assumptions). 4. A list of “edge‑candidates” that have a profit‑factor > 1.2 or win‑rate > 55 % on any 6‑month rolling window, including the exact SQL query that extracts the candidate’s performance from `ejaguiar1_backtests`. Return the report as a markdown table and a set of SQL snippets ready to run.
Why it helps: It forces the agent to audit data, feature relevance, and methodology before you start building new strategies.

2️⃣ Asset‑Class Specific Prompt Templates
📈 Stocks
You are a stock‑strategy developer. Using the `ejaguiar1_stocks` schema, design a factor‑based long‑short model that: - Uses only daily OHLCV and fundamental fundamentals (PE, ROE, Debt/Equity). - Applies a “quality‑momentum” filter: top 30 % by ROE *and* 30 % by 12‑month price momentum. - Includes a transaction‑cost model of 0.05 % per trade and a max‑drawdown constraint of 10 %. Generate: 1. The full SQL query that builds the factor scores and back‑tests the strategy over the last 10 years. 2. A Python (pandas) script that loads the query result, computes the profit‑factor, Sharpe, and win‑rate, and plots equity curves. 3. A brief “root‑cause” analysis if the profit‑factor < 1.2 (e.g., over‑fitting, sector concentration).
🪙 Crypto
You are a crypto‑pair researcher. Create a multi‑time‑frame mean‑reversion strategy for BTC‑USDT and ETH‑USDT that: - Uses 5‑minute, 1‑hour, and 4‑hour VWAP bands. - Signals a long when price crosses below the 5‑min VWAP and the 1‑hour VWAP is trending upward. - Limits exposure to 5 % of portfolio per trade and caps daily turnover at 20 %. Provide: 1. A MongoDB‑style query (or SQL if stored in `ejaguiar1_stocks`) that extracts the required OHLCV data for the past 6 months. 2. A Jupyter‑notebook cell block that implements the strategy, back‑tests with realistic exchange fees (0.04 % taker) and slippage (0.02 %). 3. A diagnostic section that checks for “data‑staleness” (API latency) and its impact on the win‑rate.
💱 Forex
You are a forex‑signal engineer. Design a carry‑trade + trend‑filter model for EUR‑USD, GBP‑USD, and AUD‑USD that: - Calculates the 30‑day interest‑rate differential using the provided `interest_rate` table. - Enters a long position only when the 20‑day EMA of price is above the 50‑day EMA. - Applies a stop‑loss of 1.5 % and a take‑profit of 3 %. Deliver: 1. A SQL script that joins `ejaguiar1_stocks` price data with the `interest_rate` table and computes the carry score. 2. An R script that runs a Monte‑Carlo simulation of the strategy under varying spread scenarios. 3. A summary of the statistical edge (profit‑factor, Sharpe) and a checklist of “why‑edge‑might‑be‑ill‑us” items.
📈 Bonds (Treasuries, Corporate)
You are a fixed‑income analyst. Build a yield‑curve‑steepening/flattening rotation strategy that: - Uses daily yields for 2‑yr, 5‑yr, 10‑yr, and 30‑yr Treasury bonds. - Goes long the 2‑yr and short the 10‑yr when the 2‑yr/10‑yr spread widens beyond its 1‑year rolling 90th percentile. - Limits net exposure to 3 % of equity‑equivalent capital. Output: 1. A PostgreSQL query that pulls the yield data from `ejaguiar1_stocks` and computes the spread percentile. 2. A MATLAB function that back‑tests the rotation, includes a bid‑ask spread of 0.5 bps, and returns the profit‑factor. 3. An analysis of “edge‑decay” over successive quarters.
📊 ETFs
You are an ETF‑pair‑trading specialist. Create a statistical‑arbitrage model for sector‑ETF pairs (e.g., XLK vs. VGT) that: - Calculates the cointegration rank using the Engle‑Granger test on 1‑day closing prices. - Opens a spread trade when the residual deviates > 2 σ from its mean. - Uses a dynamic hedge ratio updated weekly. Provide: 1. A Python script (statsmodels) that runs the cointegration test, estimates the hedge ratio, and back‑tests the spread trade over the last 5 years. 2. A SQL query that extracts the daily close prices for the relevant ETFs from `ejaguiar1_stocks`. 3. A risk‑report that quantifies maximum drawdown and the probability of “break‑out” events.
📜 Futures
You are a futures‑strategy coder. Design a term‑structure roll‑carry model for Crude‑Oil (CL) and Gold (GC) that: - Computes the roll yield between the front‑month and the next‑month contract. - Enters a long when the roll yield is positive for three consecutive days and the 30‑day trend of the front‑month price is upward. - Caps daily notional exposure at $500 k. Return: 1. A BigQuery‑compatible SQL that pulls contract‑price data from `ejaguiar1_stocks` and calculates roll yields. 2. A C# program that runs a back‑test with realistic CME fee schedule and slippage of 0.03 %. 3. A root‑cause analysis if the win‑rate stays below 50 % (e.g., contango‑bias, data‑frequency mismatch).
🪙 Commodities (Metals, Agriculture)
You are a commodity‑signal developer. Create a macro‑driven trend‑following model for Copper and Wheat that: - Uses the Bloomberg‑style “global industrial production index” (provided in `macro_data`) as a leading indicator. - Generates a long signal when the index rises > 0.2 % month‑over‑month AND the 20‑day SMA of the commodity price is above its 60‑day SMA. - Applies a volatility‑scaled position size (target 1 % of portfolio volatility). Deliver: 1. A SQL join between `ejaguiar1_stocks` price tables and `macro_data`. 2. A Julia notebook that implements the strategy, back‑tests with a 0.07 % commission, and plots the cumulative returns. 3. A diagnostic section that checks for “over‑reliance on macro lag” and suggests alternative leading indicators.
3️⃣ Prompt to Diagnose the Root Cause of No Edge
You are a statistical‑edge forensic assistant. Given the back‑test results stored in `ejaguiar1_backtests` for a specific asset class, produce a “Failure‑Mode Report” that: 1. Calculates the distribution of per‑trade returns and highlights any heavy‑tailed outliers. 2. Checks for look‑ahead bias by verifying that all feature timestamps precede the target label by at least the holding period. 3. Evaluates the impact of transaction costs by re‑running the back‑test with a 0.1 % cost increase and reporting the delta in profit‑factor. 4. Performs a feature‑importance analysis (e.g., SHAP) on the model used and lists the top‑5 features that contribute > 10 % of predictive power. 5. Summarizes the most likely “edge‑killer” (e.g., over‑fitting, data‑snooping, regime‑change). Return a concise markdown report and a set of actionable next steps.
4️⃣ Prompt to Generate New Edge‑Finding Strategies
You are a strategy‑generation AI. Using the asset‑class‑specific data in `ejaguiar1_stocks`, automatically: 1. Enumerates all possible pairwise combinations of technical indicators (e.g., RSI, MACD, Bollinger Bands, ATR) up to three‑indicator combos. 2. For each combo, builds a simple rule‑based signal (e.g., “RSI < 30 AND price < lower Bollinger”). 3. Runs a fast back‑test (1‑year rolling windows) and records profit‑factor, Sharpe, and win‑rate. 4. Returns a ranked list of the top‑10 combos that achieve profit‑factor > 1.3 and win‑rate > 55 % on at least two non‑overlapping periods. Provide the SQL/ Python snippets needed to generate the indicator matrix and the back‑test loop.
5️⃣ Prompt to Expand the Strategy Library
You are a portfolio‑construction assistant. Create a “strategy‑catalog” JSON file that contains for each asset class: - Strategy name - Description (one sentence) - Required data fields (e.g., `open, high, low, close, volume, macro_index`) - Back‑test performance metrics (profit‑factor, Sharpe, max‑drawdown) - Risk‑management rules (position sizing, stop‑loss, max‑drawdown) The JSON must be validated against a JSON schema you also generate. Explain how this catalog can be consumed by an automated “strategy‑selector” service that picks the top‑N strategies per market regime.
6️⃣ Prompt for Risk‑Management / Quant Roles for the IDE Agent
Role	Core Prompt (what to tell the agent)	Typical Deliverables
Risk‑Manager	“You are a risk‑engine. Using the portfolio‑level P&L from ejaguiar1_backtests, compute real‑time VaR, CVaR, and stress‑test scenarios (10 % market move, 2× volatility). Generate alerts when any metric exceeds pre‑set limits.”	Python risk‑engine, alert‑system, risk‑dashboard UI
Quant‑Researcher	“You are a quant researcher. Identify statistically significant predictors from the feature set in ejaguiar1_stocks. Use LASSO regression and cross‑validation to select a parsimonious model. Output the model coefficients and a back‑test of the resulting signal.”	Jupyter notebook, model file, performance summary
Data‑Engineer	“You are a data‑pipeline engineer. Build an ETL job that nightly extracts raw market data, cleans it (removes outliers, aligns timestamps), and stores the tidy dataset in ejaguiar1_stocks. Include data‑quality metrics (missing‑row %).”	Airflow DAG / dbt model, data‑quality report
Strategy‑Tester	“You are a back‑testing engine. Implement a walk‑forward framework with 12‑month training, 3‑month testing windows, and a realistic commission model. Produce a PDF report for each asset class with equity curves and statistical significance tests.”	Automated reporting script, PDF reports
Execution‑Optimizer	“You are an execution‑algorithm designer. Given a target order size and market depth data, compute an optimal schedule (VWAP/TWAP) that minimizes market impact while respecting a max‑slippage of 0.05 %.”	Python optimizer, execution logs
Portfolio‑Allocator	“You are a mean‑variance optimizer. Using the expected returns from the top‑5 strategies per asset class, construct a risk‑parity portfolio that targets a 12 % annualized Sharpe. Output the allocation matrix and rebalance schedule.”	Optimization script, allocation CSV
7️⃣ “What Struggling Companies Do” – Quick Checklist
Diagnose Data & Pipeline – audit for survivorship bias, stale timestamps, missing corporate actions.
Simplify & De‑overfit – strip back to the most robust, low‑dimensional factor set; remove overly complex ML models that perform well only in‑sample.
Add True Diversification – introduce uncorrelated asset classes or alternative data (e.g., satellite imagery, ESG scores).
Improve Transaction‑Cost Modeling – use realistic slippage, market‑impact, and latency; often the “edge” disappears once costs are properly accounted for.
Regime‑Detection Layer – build a simple macro‑regime classifier (e.g., bull vs. bear) and switch strategies on/off accordingly.
Robust Walk‑Forward & Out‑of‑Sample – enforce a strict 2‑year out‑of‑sample holdout before any live deployment.
Risk‑Budgeting & Position‑Sizing – replace fixed‑size bets with volatility‑scaled sizing; cap per‑trade drawdown.
Iterative Feature Engineering – use feature‑importance tools (SHAP, permutation importance) to prune noisy features.
Peer Review & Code Audits – have an independent quant review the back‑test code for hidden look‑ahead or leakage.
Continuous Monitoring – set up live‑performance dashboards that trigger alerts when the live profit‑factor deviates > 10 % from back‑test expectations.
How to Use the Prompts
Copy the relevant prompt into your IDE‑agent’s “task” field.
Run the agent; it will output the requested SQL/Python/Notebook artefacts.
Iterate by feeding the generated artefacts back into the “diagnostic” prompt to see if the edge improves.
Assign the role‑specific prompts to dedicated agents (e.g., a “Risk‑Manager” bot that continuously monitors VaR).
Next step: Which asset class would you like to start with, and do you prefer the “diagnostic” prompt or a “new‑edge‑generation” prompt for that class?

Listen
Follow up

Can you walk me through a concrete example of running the diagnostic prompt for the stocks asset class, including the expected SQL output and how to interpret the results?

What are some best practices for integrating the risk‑manager role into an automated pipeline, and how can I set up real‑time alerts for VaR breaches?

Could you provide a step‑by‑step guide for the new‑edge‑generation prompt, especially how to efficiently enumerate and back‑test all indicator combinations without overwhelming compute resources?

#9 
Role & Objective

You are a financial engineering and quantitative trading strategy consultant. Your role is to provide actionable guidance on diagnosing and fixing underperforming prediction systems across multiple asset classes (stocks, crypto, forex, bonds, ETFs, futures, commodities), and to generate a prioritized list of specific prompts and directives for coding agents to systematically improve trading performance.

Context

The user operates a multi-asset trading prediction system with existing infrastructure:
- Databases: ejaguiar1stocks and ejaguiar1backtests containing historical performance and backtest results
- Current challenge: Lack of statistical edge (low profit factor and/or win-rate) across one or more asset classes
- Goal: Identify root causes of underperformance, discover proven statistical edges, and implement institutional-grade prediction capabilities
- Tools: Coding agents (IDE-based automation) that can execute queries, run analyses, and implement strategies

Inputs

- Asset classes in scope: Stocks, crypto, forex, bonds, ETFs, futures, commodities (or specify which underperform most)
- Backtesting infrastructure: Describe your current protocol (e.g., walk-forward, Monte Carlo, out-of-sample validation, slippage/commissions modeled?)
- Current strategy portfolio: Are you running 1 strategy, 10, 100+? Which are losing?
- Performance threshold: Define "solid and proven" (e.g., Sharpe > 1.5, profit factor > 2.0, win-rate > 55%?)
- Constraints: Capital availability for R&D, computational resources, regulatory restrictions by asset class?

Requirements & Constraints

Quality Bar:
- Cite peer-reviewed research, industry case studies, or documented institutional practices where possible
- Distinguish between root causes (data quality, overfitting, market regime shifts, execution slippage) and surface symptoms
- Provide both strategic direction (what to fix) and tactical prompts (how to query/analyze via agents)
- Assume intermediate quantitative knowledge; avoid overly academic or purely introductory explanations

Domain Rules:
- Recommend only strategies and practices legal and compliant in major jurisdictions (US, EU, APAC)
- Acknowledge that not all asset classes respond equally to the same techniques (e.g., mean reversion works differently in crypto vs. bonds)
- Flag common pitfalls (look-ahead bias, curve-fitting, insufficient out-of-sample data)

Evidence Standard:
- If a technique is speculative or lacks strong empirical support, state that explicitly and offer caveats
- Prioritize techniques with auditable results from your own backtests or published institutional track records

Output Format

Deliver a structured response in the following sections:

``json
{
  "rootcausediagnostic_framework": {
    "section_1": "Common reasons for statistical edge loss in multi-asset systems",
    "section_2": "Diagnosis checklist: which to investigate first based on asset class"
  },
  "strategic_recommendations": {
    "improveexistingstrategies": ["action 1", "action 2", "..."],
    "addnewstrategies": ["technique A", "technique B", "..."],
    "pruneorconsolidate": ["when to cut underperformers", "..."]
  },
  "agentprompttemplates": [
    {
      "title": "Prompt Name",
      "asset_class": "Stock|Crypto|Forex|Bond|ETF|Futures|Commodities",
      "objective": "What the agent should accomplish",
      "sample_query": "Pseudocode or SQL-style directive",
      "expected_output": "What success looks like"
    }
  ],
  "agentrolerecommendations": {
    "role_1": "Quant Analyst",
    "role_2": "Risk Manager",
    "role_3": "Data Engineer",
    "role_4": "Backtester / Validator",
    "rationale": "Why each role matters"
  },
  "institutionalgradetechniques": [
    {
      "technique": "Name",
      "asset_classes": ["applicable to"],
      "evidence": "Brief citation or result",
      "implementation_complexity": "Low|Medium|High",
      "expectedprofitfactor_lift": "20-50%|50-100%|etc. (realistic range)"
    }
  ],
  "case_studies": [
    {
      "firm_type": "Hedge fund|Prop trading|Retail operation",
      "problem": "What they faced",
      "solution": "What worked",
      "source": "Industry report | Published case | Your hypothesis"
    }
  ]
}
`

Expand each section into prose and bullet points below the JSON skeleton.

Examples

Example 1: Root Cause Diagnostic Prompt for a Coding Agent

`
Task: "Query ejaguiar1backtests for all strategies marked [assetclass=crypto].
Aggregate profit factor, Sharpe ratio, max drawdown, and win rate by year and by market regime 
(bull, bear, ranging). Flag any strategy where profit factor dropped below 1.2 in the last 12 months.
Output: CSV with [strategyid, startdate, enddate, profitfactor, sharpe, maxdd, winrate, marketregime, regressionflag]."
`

Example 2: Institutional-Grade Technique Evaluation Prompt

`
Task: "Backtest a Fama-French 3-factor model (market excess return, size, value) 
on the stock universe in ejaguiar1_stocks for the past 5 years, using walk-forward validation 
(6-month train, 1-month test). Calculate out-of-sample Sharpe ratio, alpha, and beta.
Report: Does it outperform a buy-and-hold baseline by >0.5 Sharpe points? 
Include transaction costs of 5 bps per trade."
``

Self-Check

Before finalizing your response, verify:

- ✓ Have I identified at least 3 distinct root causes (e.g., overfitting, regime change, data quality, execution slippage)?
- ✓ Have I distinguished between strategy pruning and strategy addition with clear criteria for each?
- ✓ Have I generated 5+ actionable prompts that a coding agent can execute against the user's databases?
- ✓ Have I specified agent roles with concrete responsibilities (e.g., "Quant Analyst: identify statistical arbitrage opportunities")?
- ✓ Have I cited or referenced at least 2 institutional practices (e.g., walk-forward testing, factor model validation)?
- ✓ Have I flagged realistic profit factor and Sharpe targets per asset class (e.g., "stocks: >1.5 PF", "crypto: >1.3 PF")?
- ✓ Have I stated assumptions about your current backtesting rigor and data quality (e.g., "assuming slippage is modeled")?

Delivery Notes

- Use this prompt as a single copy-paste input to Perplexity
- Perplexity will return a comprehensive diagnostic + actionable framework
- Use the resulting prompts to brief your coding agents or development team
- Iterate: after agents execute the first batch of diagnostics, feed results back into refined prompts

#10 :
consider the techniques within C:\findtorontoevents_antigravity.ca\DAILY_IDEAS_PROMPTS.MD  inspect https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/  and/or mysql.50webs.com -->eajaguiar1_stocks / ejaguiar1_backtests and look for areas where we can improve our statistical edge and prediction quality per asset class or overal with safety gates, blocked symbols, etc..  and consider what criteria to use to consider to unblock a symbol that maybe had its performance tanked and now is a suitable candiddate once more.

---

## Claude Code Analysis — 2026-05-16T22:10Z

### Prompt Suite Assessment — Which Are High-Value Now

This file is a prompt library, not a plan. The prompts themselves are well-crafted. Here is which to run NOW vs. which to park:

| Prompt | Source | Value Now | Why |
|---|---|---|---|
| **#4 edge-monitoring CI job (`edge-monitor.yml`)** | Mercury | HIGH | Nightly edge scores + 10%/15% change alerts are exactly what `ab_analysis.yml` already does for COMMODITY. Extend to ALL asset classes. |
| **#2 Statistical edge per asset class SQL** | Cerebras | HIGH | Run against live `ejaguiar1_backtests` to get current ground truth. Feed into dashboard weekly. |
| **#3 System-health diagnostic** | Mercury Prompt 1 | HIGH | Run immediately when debugging a class drop. Template already valid. |
| **#4 Failing strategy analysis** | Cerebras | HIGH | Run against FOREX/CRYPTO drag systems quarterly. |
| **#5 Meta: what else can we do?** | Cerebras | MEDIUM | Park until T2 graduation of 2 classes; then revisit for expansion |
| **#5 Swarm continuous-learning loop** | Mercury | MEDIUM | Already partially implemented via swarm_v2 + ab_analysis; wire the missing meta-optimizer |
| **#7 Data quality + anomaly detection** | Mercury | HIGH | Run immediately against `ejaguiar1_stocks` for gap detection |
| **#10 Symbol unblock criteria** | Prompt #10 | HIGH | See below |

### Prompt #10 — Symbol Unblock Criteria (Concrete Implementation)

Current state: blocked symbols include AAPL (un-banned 2026-05-16), CVX (PROBATION), CT=F (PROBATION). Re-add criteria should be:

**For symbol PROBATION → ACTIVE:**
- Forward WR ≥ 55% post-block (verified from `closed_picks.json`, not backtest)
- n ≥ 30 post-block closed picks (sample credibility)
- PF ≥ 1.0 post-block
- No resolver artifacts (check `alpha_engine/data/ml_health_status.json`)
- For EQUITY: `forward_validated=True` flag in hedge_fund_quality_gate

**For fully blocked symbol → PROBATION:**
- One of: (a) `MUTATION_THREE_AXIS_PROTOCOL.md` shows mutant variant with positive edge, (b) underlying source system moved from BLOCKED to ACTIVE/PARTIAL_MUTATION, (c) symbol appears in a new source system with clean track record n≥20

**Current PROBATION symbols:**
- CVX: review 2026-05-30 (WR=75%, PF=3.48, n=12 post-block — needs n≥30)
- CT=F: review 2026-06-06 (post-block OOS WR=75% — but in COMMODITY, not standalone)

### Top 3 Prompts to Execute This Week

**Priority 1 — Run Prompt #2 (SQL edge detection) against `ejaguiar1_backtests`:**
This directly answers "where is the edge" with current data. Output: ranked table of `strategy_id × asset_class × edge_score`. Use as input to weekly filter.

**Priority 2 — Run Prompt #4 (CI edge monitor) and extend `ab_analysis.yml`:**
Current `ab_analysis.yml` only covers COMMODITY `multi_asset_cot`. Extend to run edge-score queries for all 6 classes on each push. Alert if any class edge-score drops >10%.

**Priority 3 — Run Prompt #7 (data quality scanner) against `ejaguiar1_stocks`:**
Ghost rows, duplicate close events, impossible PnL values — these directly inflate WR/PF stats. Run `tools/mysql_prediction_anomaly_scanner.py` (once shipped) on a monthly schedule.

#11 PER KIMI CODE AGENT SWARM:
Let me create a comprehensive prompt library and strategic improvement plan for you.
Here's your complete Agent Prompt Library — 20 production-ready prompts organized by priority.

---

## What I Built

**1 file: `AGENT_PROMPT_LIBRARY.md`** (35 KB) — 20 copy-paste-ready prompts for your IDE agents, organized into 5 sections:

---

## Section Summary

### SECTION 1: MySQL Edge Extraction (2 prompts) — RUN THESE FIRST
| Prompt | What It Does | Output |
|--------|-------------|--------|
| **1A** `Database Edge Scanner` | Connects to `ejaguiar1_stocks` + `ejaguiar1_backtests`, calculates PF/WR/Sharpe/MDD per asset class with 95% confidence intervals, rolling decay analysis, inversion candidates | `edge_report_mysql.md` + `edge_per_class.json` |
| **1B** `Deep Strategy Autopsy` | Per-strategy forensic analysis: streak analysis, fat tails, concentration risk, day-of-week effects, serial correlation | `strategy_autopsy.json` |

### SECTION 2: Per-Asset-Class Fixes (6 prompts)
| Class | Prompt | Problem It Solves |
|-------|--------|-------------------|
| **CRYPTO** | 2A Confidence Recalibration | ML inverted: conf≥0.90 → 14.4% WR. Implements isotonic regression + direction flip layer |
| **EQUITY** | 2B Scale What Works | PF 1.55 → systematic amplification with regime filters + conviction stack |
| **FOREX** | 2C Mutation Protocol | PF 0.86 → full mutation (invert, session filter, COT overlay, A/B test) |
| **COMMODITY** | 2D Clean COT Artifact | Remove CT=F dedup contamination, add seasonality + clean COT |
| **ETF** | 2E Sector Rotation | PF 1.33 → 1.5 (T2) via relative strength rotation + macro overlay |
| **BOND** | 2F Accumulator | Paper-only until n=100, yield curve + credit spread signals |

### SECTION 3: System-Wide Engines (6 prompts)
| Prompt | Concept | What It Does |
|--------|---------|-------------|
| **3A** DNA Mutation Engine | Genetic algorithm for strategies | Evolves strategies via point mutation, crossover, regime switching. Weekly evolution loop with fitness scoring |
| **3B Strategy Inversion Layer** | "Invert the losers" | Auto-detects strategies with 35-45% WR, creates inverted variants, A/B tests them |
| **3C Swarm Research Agents** | Multi-agent per-asset research | 5 parallel research agents (Crypto/Equity/Forex/Commodity/Bond-ETF) with technical, fundamental, sentiment, and COT tools |
| **3D The Necromancer** | Save failing strategies | Diagnoses WHY strategies fail, applies treatment (regime filter, parameter re-opt, symbol removal), resurrects via paper trading |
| **3E Multi-Timeframe Confluence** | Require 3 timeframe agreement | 1h/1d/1w must align for signal = fewer but higher-quality trades |
| **3F Adaptive Risk Manager** | Kelly + CPPI hybrid | Dynamic position sizing: Kelly * drawdown_factor * correlation_factor, hard CPPI floor |

### SECTION 4: CI/CD Integration (2 prompts)
| Prompt | What It Does |
|--------|-------------|
| **4A** Efficient GitHub Actions | Adds swarm research to existing workflows (parallel matrix, shared cache, ~2 min overhead) |
| **4B** Automated Edge Alerts | Every 6 hours: Critical/Warning/Info alerts + auto-pause on degradation |

### SECTION 5: 10-Week Roadmap
Complete phased plan: Foundation → Amplify Winners → Fix Losers → Evolve → Swarm → Optimize

---

## Top 5 Prompts to Run Immediately

| Rank | Prompt | Why First |
|------|--------|-----------|
| 1 | **1A (MySQL Edge Scanner)** | You need ground truth before any improvements |
| 2 | **2A (CRYPTO Calibration)** | Your biggest leak: high confidence = high losses |
| 3 | **3B (Inversion Layer)** | Free alpha: strategies with 35-45% WR become 55-65% when flipped |
| 4 | **2B (EQUITY Scale)** | Only proven T2 edge — scale systematically |
| 5 | **3A (DNA Mutation)** | Long-term: automated strategy evolution |

Every prompt is copy-paste ready for your IDE agents. Each includes acceptance criteria, output formats, and expected impact.

.. SEE ALSO 
"C:\Users\zerou\Downloads\AGENT_PROMPT_LIBRARY.md"

---

## Comet Browser arena.ai Prompt — 2026-05-16

Source: Comet browser deep-inspection of repo. Use in arena.ai Battle Mode (compare multiple top models). See DAILY_IDEAS.MD "2026-05-16 Comet Browser" for full context and diagnosed failure modes.

Paste this into arena.ai's chat input:

---

You are a quantitative engineer with 15+ years at Two Sigma, DE Shaw, and AQR. I need you to architect and implement the SINGLE most impactful fix that transforms this failing crypto prediction system into something that belongs at a world-class hedge fund.

REPO: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca (branch: main)

CURRENT STATE (diagnosed from 28-agent audit + 3,500 closed trades):
- 1,927 closed picks, 41% WR, -0.12% avg PnL
- Backtest-forward correlation = -0.91 (system is ANTI-predictive)
- 96.5% strategies fail OOS; only 1/260 survives walk-forward
- 78.9% trades hit SL (stops too tight for 15m noise)
- DNA live WR = 14.3%
- elite_score rho = +0.012 (zero predictive power)
- Cost model subtracts fees on EVERY bar, not just trade bars -> all DSR invalid
- 14 signal weights (IC-calibrated) exist but system picks kill strategies
- 35+ strategies cataloged, 5-agent ensemble, LightGBM/XGBoost/HMM present

CORE INFRASTRUCTURE THAT ACTUALLY WORKS:
- antigravity_quant_engine.py: 6-stage pipeline (StrategyEvaluator, RegimeDetector, AgreementAlpha, SignalWeightedScorer, KellySizer, FinalGate)
- RegimeDetector: live 6-regime classification from BTC/ETH 4h Binance klines
- AgreementAlpha: family deduplication, MIN 2 diverse models with 55% confidence
- SignalWeightedScorer: 14 IC-weighted signals (bb_squeeze=10, volume_surge=8, ema_cross=7...)
- KellySizer: half-Kelly with score/regime/chop caps
- FinalGate: MIN_SCORE=65, MIN_RR=1.5, max 8/day, CRYPTO_ONLY

THE SINGLE MOST IMPACTFUL FIX TASK:

Design and write a complete, self-contained Python module called edge_concentrator.py that:

1. IMPLEMENTS A ROLLING INFORMATION COEFFICIENT (IC) MONITOR
   - Compute daily IC for each strategy/symbol pair using (pred_direction x actual_return)
   - Bayesian shrinkage toward zero for strategies with <30 observations
   - Auto-pause any strategy where rolling 30-day IC falls below 0.05
   - Output: ordered list of surviving strategy x symbol pairs ranked by IC

2. IMPLEMENTS ATR-BASED DYNAMIC TP/SL
   - SL = entry +/- (ATR_14 x multiplier), where multiplier adapts to regime
   - TP = entry -/+ (ATR_14 x targeting_ratio) with targeting_ratio by regime:
     STRONG_BULL: 2.5, BULL: 2.0, LEANING_BULL: 1.8, CHOP: 1.5, LEANING_BEAR: 1.2, BEAR: 0.8
   - This directly addresses the 78.9% SL hit rate

3. IMPLEMENTS SYMBOL TIER FILTERING
   - Tier 1 (always allow): BTC, ETH, SOL, BNB (> $10B mcap, high volume)
   - Tier 2 (require IC > 0.10): XRP, ADA, AVAX, DOT, LINK, MATIC, UNI
   - Tier 3 (require IC > 0.15 + ATR check): all others
   - Kill list: UNI, APT, OP permanently banned until IC prove-out

4. IMPLEMENTS REGIME-ROUTED STRATEGY ALLOCATION
   - Each strategy must declare which regime(s) it performs best in
   - In CHOP: only mean-reversion strategies (BB squeeze, RSI divergence)
   - In STRONG_BULL: only trend-following + breakout
   - In BEAR: only short-biased + funding rate extreme
   - Cross-reference against the RegimeDetector output

5. OUTPUTS A SINGLE ENRICHED PICK STRUCTURE:
   {
     "symbol": str, "direction": "BUY"|"SELL",
     "strategy": str, "confidence": float,
     "entry_price": float,
     "sl_atr_dynamic": float,
     "tp_atr_dynamic": float,
     "position_size_pct": float,
     "ic_score": float,
     "symbol_tier": 1|2|3,
     "regime_fit": bool,
     "paused_reason": str | null,
     "forward_wr_estimate": float,
     "expected_edge_bps": float,
   }

CONSTRAINTS:
- Standard library + numpy + pandas only (no sklearn/tensorflow for this module)
- Must be able to run as: python edge_concentrator.py --demo
- Must integrate with existing RegimeDetector class from antigravity_quant_engine.py
- Must read strategy stats from alpha_engine/data/strategy_symbol_edge_registry.json
- Include a 200-line demo that synthesizes signals and shows the filtering pipeline in action
- Every function must have docstrings with type hints and a one-line hedge-fund-purpose comment
- This module should be able to drop into the existing pipeline between AgreementAlpha and FinalGate

The goal: Reduce 110 active picks -> 5-10/week, project WR from 41% -> 70%+, move from negative to positive expectancy.

---

Why this prompt is maximally efficient:
1. Feeds context upfront — model skips clarifying questions
2. Single bounded deliverable (edge_concentrator.py) not vague "improvement"
3. Leverages existing infrastructure (RegimeDetector, edge registry, KellySizer)
4. Addresses 3 critical failure modes simultaneously: signal quality (IC monitor + tier filter), transaction costs (ATR dynamic SL), infrastructure enforcement (auto-pause + regime routing)
5. Demo requirement lets you verify immediately
6. Measurable success criterion (110 -> 5-10 picks, 41% -> 70%+ WR)
