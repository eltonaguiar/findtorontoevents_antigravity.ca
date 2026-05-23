# AI Strategy Lab — Design Document
**Date:** 2026-05-19  
**Author:** Hermes Agent (Claude Sonnet 4.6)  
**Status:** DRAFT — implementation Sprint 1 complete

---

## Section 1: Current State

### What exists

| Component | File | Status |
|-----------|------|--------|
| Anonymous AI council runner | `tools/anon_ai_council/council_v2_runner.py` | Working (Pollinations via HTTP; Perplexity/Grok/HuggingChat/DuckAI via Playwright). 6/102 sources confirmed accessible without credentials. |
| Swarm engine runner | `tools/swarm/swarm_run.py` | Working. Supports 23 engines; `deepseek`, `kilo`, `xai`, `cerebras`, `groq` all produce detailed strategy proposals with academic citations. |
| AI tournament (pick scoring) | `tools/ai_tournament/` | Working. `price_tracker.py` resolves individual symbol picks (TP/SL/expiry). `update_leaderboard.py` scores models by WR/PF with Wilson CI + bootstrap PF CI. |
| Pick pipeline | `alpha_engine/smart_picks_engine.py` | Working. Picks from all source systems → ML composite scoring → curated output. |
| Strategy registry | MySQL `strategy_registry` + `at_strategy_stats` | Working. Records strategy name, system, asset class, win rate. |
| Strategy incubator | MySQL `at_incubator_strategies` | Working. Tracks permuted strategies through INCUBATOR → PAPER_TESTING → GRADUATED → REJECTED lifecycle. |

### What is broken / missing

**The closed loop does not exist.** The current system has two unconnected halves:

- **Left half:** AIs propose strategies in natural language (via council_v2_runner or swarm engines). Output goes to JSON files in `swarm_runs/`. No parsing of signal rules into executable conditions. No database storage linking "which AI said what."
- **Right half:** The alpha engine runs hard-coded strategies. The incubator (`at_incubator_strategies`) stores permuted parameter variants of *existing* strategies, not AI-invented new ones. No table records the AI source, methodology, or academic backing.

**There is no feedback loop.** Once a strategy is tested, the result is not sent back to the AI that proposed it. The AI cannot improve its proposals based on what actually worked.

**Database access issue:** `ejaguiar1_backtests` is not accessible to `ejaguiar1_stocks` MySQL user (only `GRANT ALL PRIVILEGES ON ejaguiar1_stocks.*` exists). The new tables were created in `ejaguiar1_stocks` instead.

---

## Section 2: Database Schema

Both tables are now live in `ejaguiar1_stocks` as of 2026-05-19.

### `ai_strategy_proposals`

```sql
CREATE TABLE ai_strategy_proposals (
  id INT AUTO_INCREMENT PRIMARY KEY,
  ai_source VARCHAR(100),           -- 'pollinations', 'deepseek', 'perplexity', etc.
  proposed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  asset_class VARCHAR(50),          -- 'EQUITY', 'CRYPTO', 'FOREX', 'COMMODITY', 'ETF', 'BOND'
  strategy_name VARCHAR(200),
  signal_rule TEXT,                 -- human-readable signal calculation
  entry_condition TEXT,             -- precise entry trigger
  exit_condition TEXT,
  hold_days INT DEFAULT 20,
  direction ENUM('LONG','SHORT','BOTH') DEFAULT 'LONG',
  methodology TEXT,                 -- economic rationale (causal, not correlational)
  academic_backing TEXT,            -- 1-2 paper citations with author + year
  confidence_score FLOAT DEFAULT 0.5, -- AI's self-rated confidence 0-1
  hypothesis_id VARCHAR(50),        -- links to hypothesis_registry.json (e.g. 'E-ANON-001')
  status ENUM('proposed','backtesting','shadow','live','killed','deferred') DEFAULT 'proposed',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### `ai_strategy_forward_tests`

```sql
CREATE TABLE ai_strategy_forward_tests (
  id INT AUTO_INCREMENT PRIMARY KEY,
  proposal_id INT NOT NULL,
  symbol VARCHAR(50),
  entry_date DATE,
  exit_date DATE,
  entry_price FLOAT,
  exit_price FLOAT,
  pnl_pct FLOAT,
  outcome ENUM('WIN','LOSS','OPEN') DEFAULT 'OPEN',
  signal_value FLOAT,               -- signal score at entry (e.g. momentum ratio)
  notes TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_proposal_id (proposal_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### Relationship to existing tables

- `ai_strategy_proposals.hypothesis_id` links to `hypothesis_registry.json` entries (H-xxx, E-xxx prefixes).
- Graduated proposals should be promoted to `at_incubator_strategies` (status → INCUBATOR) and `strategy_registry` for tracking in the main dashboard.
- Forward test results feed `at_strategy_stats` for cross-source comparisons.

---

## Section 3: Enhanced Prompt Engineering for council_v2_runner

Current prompt (`council_v2_runner.py` DEFAULT_PROMPT) is too vague: "Give exactly 2 concise ideas." It produces prose that cannot be parsed into executable signals.

### Required improvements

**1. Structured output mandate** — Force 11 labelled fields:
```
STRATEGY_NAME: <name>
SIGNAL_RULE: <exact calculation>
ENTRY_CONDITION: <precise trigger>
EXIT_CONDITION: <precise trigger>
HOLD_DAYS: <integer>
DIRECTION: LONG|SHORT|BOTH
METHODOLOGY: <causal economic rationale, 1-2 sentences>
ACADEMIC_BACKING: <Author Year "Title">; <Author Year "Title">
SELF_CRITIQUE: 1) <failure mode>  2) <failure mode>
FIRST_3_TRADES: DATE | SYMBOL | DIRECTION | EXPECTED_RETURN
CONFIDENCE: <0.0-1.0>
```

**2. Self-critique requirement** — Forces the AI to pre-identify failure modes, which (a) improves strategy quality, (b) gives testers a hypothesis to falsify.

**3. First-3-trades requirement** — Grounds the proposal in recent data. If an AI cannot name 3 specific recent trades, the strategy is likely too vague to be testable.

**4. Anti-hallucination citation check** — After collecting proposals, cross-check citations against known paper databases. Flag any citation that doesn't match a real DOI.

**5. Multi-AI debate round** — After collecting proposals from 3+ sources, run a second prompt: "AI-1 proposed X. AI-2 proposed Y. What are the weaknesses of each? Which do you recommend and why?" This surfaces disagreements before testing.

---

## Section 4: AI Source Rankings for Strategy Invention

Ranked by likelihood to produce testable, academically-grounded alpha:

### 1. DeepSeek (swarm engine) — BEST
- Produces detailed, self-critical responses with real paper citations
- Identifies failure modes and market regime conditions unprompted
- Provides specific parameter values (e.g. "5-day / 21-day momentum ratio, rebalance weekly")
- Academic references consistently check out against known literature
- Self-critique quality: HIGH (names crowding risk, transaction costs, data-snooping)
- Implementation value: HIGH (structured output parseable with light regex)

### 2. Pollinations.ai (HTTP GET, free) — SECOND
- Fastest response (no browser automation required, pure HTTP)
- Cited Jegadeesh-Titman (1993) and carry trade academic basis unprompted
- Moderate structure — uses numbered lists that are parseable
- Occasionally produces Python pseudocode for signal calculation
- Best for: rapid iteration, high-volume strategy generation
- Limitation: GPT-oss-20b model, shallower reasoning than DeepSeek

### 3. Perplexity.ai (browser, sonar model) — THIRD
- Includes live web citations (searches for supporting evidence in real-time)
- Referenced CRSP data sources, which shows awareness of data infrastructure
- Proposals are grounded in current market conditions (searched before responding)
- Implementation value: MEDIUM (responses are conversational, less structured)
- Limitation: Playwright browser required; guest mode rate-limits aggressively

### 4. Kilo (swarm engine) — FOURTH
- Practical, flags implementation risks and data availability issues
- Good for: validation and critique of other AIs' proposals
- Limitation: less creative than DeepSeek; tends to propose well-known strategies
- Best role: debate moderator, not primary inventor

### 5. XAI/Grok (swarm engine) — FIFTH
- Broad knowledge, occasionally produces contrarian ideas
- Less consistent structure; requires more regex work
- Best for: diversity of ideas, not precision

**Not recommended for strategy invention:**
- HuggingChat (Llama-3 guest): generic responses, no academic grounding
- DuckAI (GPT-4o-mini): short responses, no specifics
- eye2.ai: provides Python code (highest implementation value) but requires browser

---

## Section 5: Implementation Roadmap

### Sprint 1 (DONE — 2026-05-19)
- [x] Schema: `ai_strategy_proposals` + `ai_strategy_forward_tests` created in `ejaguiar1_stocks`
- [x] Seed: 3 AI proposals inserted (E-ANON-001, F-ANON-001, H-OPT-001)
- [x] Scaffold: `tools/ai_strategy_lab/council_to_forwardtest.py` — full closed-loop runner
  - `propose_strategy()`: queries AI, parses structured fields, stores in MySQL
  - `run_forward_test()`: yfinance-based forward test, stores per-trade results
  - `get_leaderboard()`: ranks AI sources by WR/PF of proposed strategies
  - `generate_feedback_prompt()`: builds a feedback prompt for the AI that proposed a strategy

### Sprint 2 (next session, estimated 4-6h)
**Goal:** Connect the right half — wire AI proposals into the pick generation path.

- [ ] **Parser hardening** — `parse_strategy_response()` handles edge cases; unit tests
- [ ] **council_v2_runner prompt update** — Replace DEFAULT_PROMPT with structured 11-field template
- [ ] **Promotion gate** — When a proposal reaches n>=10 forward test trades AND WR>=50% AND PF>=1.5, auto-promote to `at_incubator_strategies` (status=INCUBATOR) and file a GitHub issue for manual review
- [ ] **GitHub Actions workflow** — `tools/ai_strategy_lab/run_lab_cycle.yml` — daily 06:00 UTC: query 3 engines, store proposals, run forward tests on top 50 EQUITY symbols, update leaderboard
- [ ] **Feedback loop trigger** — When a proposal hits n=20 resolved trades, auto-send feedback prompt to same AI source and store revision as new proposal (linked by `parent_hypothesis_id`)

### Sprint 3 (following session, estimated 6-8h)
**Goal:** Multi-AI debate and strategy synthesis.

- [ ] **Debate round** — After 3 AIs each propose a strategy, run a second prompt: "Review these 3 proposals and recommend the best one with reasons." Store debate transcript.
- [ ] **Synthesis** — Combine top-voted strategy attributes into a hybrid proposal
- [ ] **Integration into dashboard** — Add `AI Strategy Lab` panel to `audit_dashboard/template.html` showing: proposals pipeline, leaderboard, recent forward test results
- [ ] **Hypothesis registry link** — Auto-register new proposals in `hypothesis_registry.json` with status=PROPOSED
- [ ] **ejaguiar1_backtests access** — Request MySQL GRANT ALL PRIVILEGES on ejaguiar1_backtests for ejaguiar1_stocks user (requires server admin), then migrate tables

---

## Gap Analysis

| Gap | Severity | Effort | Description |
|-----|----------|--------|-------------|
| Strategy schema gap | **P0** | 2h | AIs output free text; no parser converting to executable signal rules. `parse_strategy_response()` in council_to_forwardtest.py is first fix, but needs hardening + tests. |
| Feedback loop gap | **P0** | 3h | AIs never see results of prior proposals. `generate_feedback_prompt()` exists but not yet wired into the council runner's prompt chain. |
| Forward-test tracking gap | **P1** | DONE | No dedicated table existed for AI-invented strategy testing. Tables now created; basic yfinance-based test in `run_forward_test()`. |
| Multi-AI debate gap | **P1** | 4h | No mechanism to make AIs critique each other's strategies before testing. Debate round design exists (Section 3) but not implemented. |
| Methodology documentation gap | **P2** | 1h | No record of WHY each AI proposed what it did. Now stored in `methodology` field but not surfaced in dashboard. |

---

## Appendix: Seed Proposals

| ID | Hypothesis | Source | Asset Class | Status |
|----|-----------|--------|-------------|--------|
| 1 | E-ANON-001 | pollinations+perplexity | EQUITY | proposed |
| 2 | F-ANON-001 | pollinations+perplexity+eye2 | FOREX | proposed |
| 3 | H-OPT-001 | deepseek | EQUITY | deferred (options data needed) |
