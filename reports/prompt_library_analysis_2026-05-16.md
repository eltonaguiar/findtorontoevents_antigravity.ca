# DAILY_IDEAS_PROMPTS.MD & AGENT_PROMPT_LIBRARY.md Analysis
**Date:** 2026-05-16  
**Analyst:** opencode  
**Status:** Complete

---

## Executive Summary

Reviewed two comprehensive prompt libraries designed to improve statistical edge across asset classes for the findtorontoevents.ca/audit system. Both libraries are well-structured and complementary. Key finding: **significant overlap with work already completed or in progress**, but several high-value prompts remain unexecuted.

---

## File 1: DAILY_IDEAS_PROMPTS.MD (Current Repo)

### Structure
- 8 sections (#1 through #8) from different AI sources
- Contains iterative prompt generations from: Mercury, Cerebras, Claude, Gemini, and others
- Heavy focus on: data pipeline audit, SQL edge detection, strategy inversion/DNA mutation, swarm agents

### Key Themes Across Iterations
| Theme | Frequency | Quality |
|-------|-----------|---------|
| Data pipeline refactor (SQLAlchemy/Pydantic) | 6/8 | Medium — generic, not repo-specific |
| SQL edge detection per asset class | 7/8 | High — solid SQL patterns |
| Strategy inversion (35-45% WR → flip) | 5/8 | High — actionable |
| DNA mutation engine | 5/8 | Medium — needs concrete implementation |
| Swarm research agents per asset class | 4/8 | Medium — architecture-heavy |
| Failing strategy salvage | 3/8 | High — "Necromancer" concept useful |
| Multi-timeframe confluence | 2/8 | High — MTF filtering proven concept |
| Adaptive risk management (Kelly+CPPI) | 2/8 | High — production-worthy |

### Critique
- **Strengths:** Comprehensive coverage, good progression from audit → fix → evolve
- **Weaknesses:** Repetitive across iterations (same 5 prompts regenerated 8 times), some prompts assume DB schemas that don't match reality (e.g., `strategy_rules` JSON column may not exist)
- **Best section:** #5 (Cerebras) — most structured with clear success criteria

---

## File 2: AGENT_PROMPT_LIBRARY.md (Downloads)

### Structure
- 5 sections, 20 prompts total
- Organized by priority: MySQL Edge Extraction → Per-Asset-Class Fixes → System-Wide Engines → CI/CD → Roadmap
- Much more actionable than DAILY_IDEAS_PROMPTS.MD

### Section-by-Section Assessment

#### SECTION 1: MySQL Edge Extraction (2 prompts) — RUN FIRST
| Prompt | Assessment | Status |
|--------|-----------|--------|
| **1A** Database Edge Scanner | Excellent — schema discovery + edge calc + confidence intervals + time decay + inversion analysis | **PARTIALLY DONE** — `/money-maker-readyv2` already produced weekly_filter report with PF/WR per class |
| **1B** Deep Strategy Autopsy | Strong — pick distribution, concentration risk, streak analysis, fat tails | **NOT DONE** — valuable addition |

#### SECTION 2: Per-Asset-Class Fixes (6 prompts)
| Prompt | Problem | Assessment | Status |
|--------|---------|-----------|--------|
| **2A** CRYPTO Confidence Recalibration | High conf = 14.4% WR (inverted) | Critical fix — isotonic regression + direction flip | **NOT DONE** |
| **2B** EQUITY Scale What Works | PF 1.55 — only T2 edge | Smart conviction stack + regime filters | **PARTIALLY DONE** — gap-risk helper wired |
| **2C** FOREX Mutation Protocol | PF 0.86, losing money | Direction flip + session filter + COT overlay | **NOT DONE** |
| **2D** COMMODITY Clean COT | CT=F dedup artifact | Clean seasonal + COT + roll yield strategies | **NOT DONE** |
| **2E** ETF Sector Rotation | PF 1.33 → target 1.5 | RS rotation + macro overlay | **PARTIALLY DONE** — emitter fixed |
| **2F** BOND Accumulator | n=11, PF 0.66 | Paper-only to 100 picks | **NOT DONE** |

#### SECTION 3: System-Wide Engines (6 prompts)
| Prompt | Concept | Assessment | Status |
|--------|---------|-----------|--------|
| **3A** DNA Mutation Engine | Genetic algorithm evolution | Ambitious but valuable | **NOT DONE** |
| **3B** Strategy Inversion Layer | "Invert the losers" | Free alpha — high priority | **NOT DONE** |
| **3C** Swarm Research Agents | Multi-agent per-asset research | Architecture-heavy, good long-term | **NOT DONE** |
| **3D** The Necromancer | Save failing strategies | Excellent concept — diagnose before kill | **NOT DONE** |
| **3E** Multi-Timeframe Confluence | 3 timeframe agreement | Proven concept, +0.2-0.5 PF lift expected | **NOT DONE** |
| **3F** Adaptive Risk Manager | Kelly + CPPI hybrid | Production-worthy risk management | **NOT DONE** |

#### SECTION 4: CI/CD Integration (2 prompts)
| Prompt | Assessment | Status |
|--------|-----------|--------|
| **4A** Efficient GitHub Actions | Parallel matrix, shared cache, ~2min overhead | **NOT DONE** |
| **4B** Automated Edge Alerts | Critical/Warning/Info alerts + auto-pause | **NOT DONE** |

#### SECTION 5: 10-Week Roadmap
Phased plan is sound. Current progress: ~Week 1-2 (foundation phase).

---

## Cross-Reference: What We've Already Done

| Completed Fix | Related Prompt | Impact |
|--------------|---------------|--------|
| BLOCKED_SYMBOLS check in production_scanner.py | 2A (CRYPTO) | P0 — 12 blocked picks removed from active |
| XLMUSUT → XLMUSDT typo fix | N/A | Bug fix |
| ETF emitter source_system fix | 2E (ETF) | Correct attribution |
| is_gap_risk_equity() wired | 2B (EQUITY) | Gap-risk penalty active |
| PEAD warning added | 2B (EQUITY) | Visibility |
| Symbol unblock monitor created | 3D (Necromancer) | Tiered unblock protocol |
| Weekly filter report generated | 1A (Edge Scanner) | Per-class verdicts |
| Statistical edge improvement plan | 1A + 1B | P0-P2 roadmap |

---

## Top 5 Prompts to Execute Next (Ranked)

| Rank | Prompt | Why | Expected Impact |
|------|--------|-----|-----------------|
| **1** | **2A CRYPTO Confidence Recalibration** | Biggest leak: high confidence = high losses | WR 14.4% → 55%+ for conf≥0.80 |
| **2** | **3B Strategy Inversion Layer** | Free alpha from 35-45% WR strategies | 35-45% WR → 55-65% WR inverted |
| **3** | **1B Deep Strategy Autopsy** | Know what you have before fixing | Per-strategy health scores |
| **4** | **2C FOREX Mutation Protocol** | Worst performer (PF 0.86) | PF 0.86 → 1.2+ or kill |
| **5** | **3E Multi-Timeframe Confluence** | Proven +0.2-0.5 PF lift | Fewer but higher-quality trades |

---

## Recommendations

1. **Consolidate**: DAILY_IDEAS_PROMPTS.MD has 8 redundant iterations. Keep AGENT_PROMPT_LIBRARY.md as the canonical source — it's cleaner and better organized.

2. **Execute in order**: Run prompts 2A → 3B → 1B → 2C → 3E. Each builds on the previous.

3. **Skip generic prompts**: Prompts about "SQLAlchemy refactor" and "data pipeline audit" are generic software engineering tasks, not quant edge improvements. Our codebase works — focus on edge, not refactoring.

4. **Adapt to reality**: Some prompts assume DB columns that don't exist (e.g., `strategy_rules` JSON). Verify schema before executing.

5. **Track progress**: Each prompt execution should produce an `updates/` doc with before/after metrics.

---

## Files Created This Session

| File | Purpose |
|------|---------|
| `alpha_engine/production_scanner.py` (modified) | BLOCKED_SYMBOLS filter at source |
| `tools/symbol_unblock_monitor.py` | Tiered unblock monitoring tool |
| `reports/statistical_edge_improvement_plan_2026-05-16.md` | P0-P2 improvement roadmap |
| `reports/weekly_filter_2026-05-16T0747Z.md` | Per-class edge verdicts |
| `updates/2026-05-16-opencode-72h-review-feedback.md` | 72h commit/PR review |
| `reports/prompt_library_analysis_2026-05-16.md` | This file |
