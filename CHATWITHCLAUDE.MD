# CHATWITHCLAUDE.MD — Project Synthesis and Coordination Hub

This file serves as the central command, control, and communication hub for the `findtorontoevents_antigravity.ca` project. It is updated after every major analysis, audit, or strategic planning session to reflect the current state, findings, priorities, and action items flowing between this swarm and Claude's implementation window.

---

## CEREBRAS REVIEW OF SWARM STY LES (2026-05-05)

Reviewed and validated both the **multi-agent-swarm** skill and the **Ruflo orchestrator.py** system.

### `multi-agent-swarm`

- **Status**: ✔️ Stable and robust.
- **Use Case**: Primary tool for deep, 60-agent research sessions (e.g., 10 rounds × 6 models).
- **Pattern**: Prefer `tencent/hy3-preview:free` for zero-cost, high-reliability execution.
- **Process**: Follow 3-cycle approach (generate → peer review → apply) for high-quality output.

### Ruflo Orchestrator (`orchestrator.py`)

- **Status**: ✔️ Fixed and operational.
- **Use Case**: Lightweight, continuous monitoring (audit, GitHub hygiene, bug hunting).
- **Fixes**: Corrected `HERMES_BIN` path, implemented `--model` passthrough, fixed YAML merge logic, added failover.
- **Agents**: Uses 5 YAML-defined agents in `.ruflo/agents/` with strict `unable_to_verify` clauses to prevent hallucinations.
- **Command**: `python3 .ruflo/orchestrator.py --swarm audit --no-verify`

**Full Report**: [CEREBRAS_REVIEW_MAY5.MD](CEREBRAS_REVIEW_MAY5.MD)

---

## RUFLO SWARM MASSREVIEW — Key Testing & Provider Validation (2026-05-05)

Conducted comprehensive MASSREVIEW of both swarm systems (`tools/swarm` + `.ruflo`).

### Wizard Infrastructure — CONFIRMED FEATURES

- **Tier Selection**: ✅ `--tier {free|paid|hybrid}` fully functional
- **Quick Mode**: ✅ `--quick` flag shows all agents & recommended tier
- **Key Detection**: ✅ Loads `.env`, detects available keys, recommends optimal tier
- **With Keys**: Recommends `hybrid` (paid quality + free fallback)
- **Without Keys**: Recommends `free` (OpenRouter free tier)

### Orchestrator Infrastructure — HEALTHY

- **Agent Count**: 5 YAML agents registered (`audit_researcher`, `audit_quant`, `github_hygiene`, `bug_hunter`, `strategist`)
- **Dispatch Logic**: ✅ Works for audit, strategy, github, bugs swarms
- **Compilation**: ✅ Generates `COMPILED_latest.json` with aggregated insights
- **File I/O**: ✅ Saves individual agent JSONs to `swarm_runs/ruflo-insights/`

### Windows Environment Keys Discovered

User added special Windows environment variables for free tier access:

| Key | Location | Status | Details |
|-----|----------|--------|---------|
| **CEREBRAS_API_KEY_PAID** | Windows User | ✅ | `csk-ptx8n...` — gpt-oss-120b works |
| **CEREBRAS_API_KEY_FREE** | Windows User | ❌ | `csk-wd29r...` — **403 Forbidden** |
| **OPENROUTER_FREE_KEY** | Windows User | ✅ | `sk-or-v1-42a0...` — **4 models work!** |
| **GEMINI_FREE_KEY** | Windows User | ✅ | `AIzaSyAX...` — **gemini-2.5-flash works!** |
| **OPENCODE_FREE_TIER** | Windows User | ⚠️ | `sk-0Ei6...` — CLI tool (different pattern) |

### Provider URLs for Fresh Machines

Link these in your documentation for users setting up on new machines:

| Provider | Signup URL | Key Location | Cost |
|----------|------------|--------------|------|
| **Pollinations** | https://pollinations.ai/ | N/A — NO KEY NEEDED! | ✅ Free |
| **OpenRouter** | https://openrouter.ai/signup | https://openrouter.ai/settings/keys | Free tier available |
| **Google Gemini** | https://aistudio.google.com/ | https://aistudio.google.com/app/apikeys | Free tier available |
| **Cerebras** | https://cloud.cerebras.ai/ | https://cloud.cerebras.ai/platform/user/api-keys | Free tier available |
| **GitHub Models** | https://github.com/marketplace/models | https://github.com/settings/tokens | GitHub token |
| **DeepSeek** | https://platform.deepseek.com/ | https://platform.deepseek.com/api_keys | Free tier available |
| **xAI/Grok** | https://console.x.ai/ | https://console.x.ai/team/[TEAM]/api-keys | Paid |
| **Inception** | https://platform.inception.ai/ | Settings → API Keys | Free tier |
| **OpenCode** | https://opencode.ai/ | npm install -g opencode | Free tier / CLI |
| **Groq** | https://console.groq.com/ | https://console.groq.com/keys | Free tier |
| **HuggingFace** | https://huggingface.co/ | https://huggingface.co/settings/tokens | Free tier |

### Updated Free Model Status — NEW KEYS WORK! ✅

**OLD Broken Free Models:**
| Model | Status |
|-------|--------|
| google/gemini-2.0-flash-exp:free | ❌ HTTP 404 (discontinued) |
| meta-llama/llama-3.3-70b-instruct:free | ❌ HTTP 429 (rate limited) |
| deepseek/deepseek-chat:free | ❌ HTTP 404 (no endpoints) |

**NEW Working Free Models (via OPENROUTER_FREE_KEY):**
| Model | Status |
|-------|--------|
| **tencent/hy3-preview:free** | ✅ WORKS |
| **nvidia/nemotron-3-nano-30b-a3b:free** | ✅ WORKS |
| **nvidia/nemotron-3-super-120b-a12b:free** | ✅ WORKS |
| **minimax/minimax-m2.5:free** | ✅ WORKS |
| **pollinations/default** | ✅ NO KEY NEEDED |

**NEW Working with GEMINI_FREE_KEY:**
| Model | Status |
|-------|--------|
| **gemini-2.5-flash** | ✅ WORKS |
| **gemini-2.0-flash** | ⚠️ Rate limited (429) |
| **gemini-2.5-pro** | ⚠️ Rate limited (429)

### FREE Model Status — CRITICAL FINDING ⚠️

**Traditional OpenRouter Free Models (BROKEN):**
| Model | Status |
|-------|--------|
| google/gemini-2.0-flash-exp:free | ❌ HTTP 404 (discontinued) |
| meta-llama/llama-3.3-70b-instruct:free | ❌ HTTP 429 (rate limited) |
| deepseek/deepseek-chat:free | ❌ HTTP 404 (no endpoints) |

**NEW Working Free Models (via OPENROUTER_FREE_KEY):**
| Model | Status |
|-------|--------|
| **tencent/hy3-preview:free** | ✅ WORKS |
| **nvidia/nemotron-3-nano-30b-a3b:free** | ✅ WORKS |
| **nvidia/nemotron-3-super-120b-a12b:free** | ✅ WORKS |
| **minimax/minimax-m2.5:free** | ✅ WORKS |
| pollinations/default | ✅ NO KEY NEEDED |

**NEW Working with GEMINI_FREE_KEY:**
| Model | Status |
|-------|--------|
| **gemini-2.5-flash** | ✅ WORKS (via aistudio.google.com) |
| **gemini-2.0-flash** | ⚠️ Rate limited (429) |



### Provider Signup URLs (MASSREVIEW 2026-05-05 validated)

| Provider | Signup URL | Key Location | Cost |
|----------|------------|--------------|------|
| **Pollinations** | https://pollinations.ai/ | N/A — NO KEY NEEDED! | ✅ Free |
| **OpenRouter** | https://openrouter.ai/signup | https://openrouter.ai/settings/keys | Free tier |
| **Google Gemini** | https://aistudio.google.com/ | https://aistudio.google.com/app/apikeys | Free tier |
| **Cerebras** | https://cloud.cerebras.ai/ | https://cloud.cerebras.ai/platform/user/api-keys | Free tier |
| **DeepSeek** | https://platform.deepseek.com/ | https://platform.deepseek.com/api_keys | Free tier |
| **xAI/Grok** | https://console.x.ai/ | https://console.x.ai/team/[TEAM]/api-keys | Paid |
| **Inception** | https://platform.inception.ai/ | Settings → API Keys | Free tier |
| **OpenCode** | https://opencode.ai/ | npm install -g opencode | Free / CLI |
| **Groq** | https://console.groq.com/ | https://console.groq.com/keys | Free tier |
| **HuggingFace** | https://huggingface.co/ | https://huggingface.co/settings/tokens | Free tier |
| **GitHub Models** | https://github.com/marketplace/models | https://github.com/settings/tokens | Free tier |

**Key Insight**: OpenRouter "free" models require an OPENROUTER_API_KEY for auth (they're $0 cost, not no-auth). **Only pollinations works with ZERO authentication.** The `OPENROUTER_FREE_KEY` provides access to 4 working free models, and `GEMINI_FREE_KEY` works for `gemini-2.5-flash`!

### Paid Provider Status — All Working

| Provider | Model | Status | Time |
|----------|-------|--------|------|
| cerebras | gpt-oss-120b | ✅ | 0.3s |
| deepseek | deepseek-chat | ✅ | 1.1s |
| xai | grok-3-latest | ✅ | 0.6s |
| inception | mercury-2 | ✅ | 1.4s |
| openrouter | gpt-4o-mini | ✅ | 1.1s |

### GitHub Copilot Integration

**Status**: ⚠️ **Not directly supported**

- GitHub Copilot is NOT a standard completion API like OpenAI/Cerebras
- It requires VS Code extension context + browser auth flow
- **CLI access**: Requires `gh copilot` CLI (not installed in WSL)
- **Integration options**:
  1. Install GitHub CLI + Copilot extension: `gh extension install github/gh-copilot`
  2. Use Copilot REST API (requires special access/partnership)
  3. Subprocess calls to `gh copilot suggest "question"`

**Recommendation**: To enable Copilot, user needs to:
```bash
# For Windows (in PowerShell)
gh auth login
gh extension install github/gh-copilot

# Then Copilot becomes available as a provider
gh copilot suggest "How do I optimize this code?"
```

### Key Recommendations (with Reasons)

| Priority | Action | Reason |
|----------|--------|--------|
| **P1** | Update `FAILOVER_MODELS` in orchestrator.py | Current models all 404/429. Replace with: `pollinations/default` (no key), `tencent/hy3-preview:free`, `nvidia/nemotron-3-nano-30b-a3b:free` (OPENROUTER_FREE_KEY), `gemini-2.5-flash` (GEMINI_FREE_KEY) |
| **P1** | Use `CEREBRAS_API_KEY_PAID` (Windows) | Works with gpt-oss-120b; .env CEREBRAS_API doesn't work |
| **P1** | Add GEMINI_FREE_KEY support | `gemini-2.5-flash` works (gemini-2.0-flash rate limited) |
| **P1** | Use `OPENROUTER_FREE_KEY` for free tier | Has access to 4 working free models |
| **P2** | Update documentation with provider URLs | Users on fresh machines need signup links |
| **P2** | Consider GitHub Copilot CLI integration | Requires `gh` CLI + copilot extension |
| **P2** | Fix OLLAMA_CLOUD model | Current model deprecated

### Verification Commands
```bash
# Test free models with OPENROUTER_FREE_KEY
cd /mnt/c/findtorontoevents_antigravity.ca
python3 tools/swarm/api_consult.py --provider openrouter --model tencent/hy3-preview:free --prompt "test"

# Run swarm with paid tier
source .env && export OPENROUTER_API_KEY="$OPENROUTER"  # or use Windows key
python3 .ruflo/orchestrator.py --swarm audit --tier paid --timeout 200

# Test pollinations (no key needed)
python3 tools/swarm/api_consult.py --provider pollinations --prompt "test"
```

**Full Report**: `swarm_runs/MASSFEEDBACK.MD`

---

## FX Kill Switch Enforcer — MERGED TO MAIN (2026-05-08)

**Commits on main:**
- `ce4bb4699d2` — Core module (fx_kill_switch.py, strategy_blocklist.py, feed_hygiene.py integration)
- `611f62639d5` — Strategy blocklist integration (is_fx_killed_strategy helper)
- `b33f718dff7` — Test coverage (TestComputeDecay class, 5 new tests)

**18/18 unit tests passing**

### What was built

`alpha_engine/fx_kill_switch.py` — Automatic detection and blocking of toxic FOREX strategies:

1. **4 kill rules:**
   - Zero WR on 15+ trades → hard-kill
   - PF < 0.9 on 20+ trades → hard-kill
   - Decay > 15pp (all-time vs 30-day WR) → hard-kill
   - 7 known toxic strategies → hard-coded blocklist

2. **`is_forex_strategy()`** — Word-boundary detection via frozenset splitting + 6-char currency pair matching (GBPJPY, EURUSD, USDJPY, etc.) to avoid false positives (usdt ≠ usd, beforex ≠ forex)

3. **Integration:** `feed_hygiene.py` checks every FOREX pick at ingest; calls `is_forex_strategy()` and `check_strategy_for_kill()`

4. **Tests:** `tests/test_fx_kill_switch.py` — 18 unittest tests covering:
   - `is_forex_strategy()` (5 tests): word-boundary frozenset, 6-char pairs, edge cases
   - `_compute_profit_factor()` (2 tests): no trades, inf returns
   - `_compute_decay()` (5 tests): no trades, insufficient trades, no dates, positive decay, no decay
   - `check_strategy_for_kill()` (4 tests): known toxic, zero WR, PF<0.9, decay>15pp
   - Known toxic strategies (1 test): 7 strategies hard-coded

### Rollback
```bash
export FX_KILL_SWITCH_DISABLED=1
```

### Integration points

| File | What it does |
|------|-------------|
| `alpha_engine/feed_hygiene.py` | Step 5a in `is_valid_active_pick()`: checks `asset_class=='FOREX' or is_forex_strategy(strat)` → calls `check_strategy_for_kill()` |
| `alpha_engine/strategy_blocklist.py` | `is_fx_killed_strategy()` helper, `is_blocked_strategy()` includes FX kills, `block_reason()` returns `'fx-kill'`, `pick_block_reason()` chains through `block_reason()` |
| `alpha_engine/fx_kill_switch.py` | Core module with 4 kill rules + rollback support |

### Known toxic strategies blocked (7 total)
`myfxbook_retail_contrarian`, `forex_rsi2_mean_reversion`, `forex_stochastic_mr`, `forex_usd_trend`, `ema_aggressive_prop`, `stochastic_mean_reversion_forex`, `usd_index_trend_forex`

---

## BUFFY PER-ASSET-CLASS SWARM ANALYSIS (2026-05-07)

**Source task:** Hermes `task.request` → `PER-ASSET-CLASS SWARM ANALYSIS — findtorontoevents.ca/audit`
**Output:** `swarm_runs/asset-class-swarm-20260507T215709Z/`
**Engines:** DeepSeek + xAI + Cerebras (19 total runs, ~$0.31)

### Asset Class Health (Live Dashboard)

| Asset Class | Win Rate | Profit Factor | Volume | Status |
|---|---|---|---|---|
| CRYPTO | 47.1% | 1.34 | HIGHEST | stable |
| FOREX | 46.3% | 0.26 | medium | **RESCUE NEEDED** |
| COMMODITY | 67.3% | 4.43 | low | **INV inverse → KILL** · raw → scale candidate |
| EQUITY | 53.7% | 1.56 | low | stable |
| ETF | 58.8% | 1.41 | low | **SCALE CANDIDATE** — best Sharpe (6.375) |

### Kill List — Top Strategies to Disable/Delete

- `JPY_Momentum_5m` — FOREX — 3/3 engines agree — PF=0.26, massive decay
- `COMMODITY inverse strategies` — COMMODITY — 3/3 engines agree — value destroyers
- `forex_carry_momentum` — FOREX — WR=6.1%, PF=0.02
- `NFT_Sentiment` — CRYPTO — forward edge consistently negative
- `Strategy X` — CRYPTO — zero forward Sharpe

### Promote List — Strategies to Scale/Enable

- `chatgpt_combined` — EQUITY/ETF — 3 engine consensus, highest net PnL
- `Crypto_StatArb` — CRYPTO — consistent positive Sharpe
- `IWM mean reversion` — ETF — highest win rate in ETF class
- `SPY_macro_regime` — ETF — Sharpe=6.375 driven by this strategy

### Top Validated Edges (33 total)

1. **CRYPTO: ATR-RSI mean reversion** — WR boost when ATR percentile > 70 (Cerebras)
2. **FOREX: Time-zone session overlap** — WR=58% during London/NY overlap (xAI)
3. **EQUITY: News-sentiment polarity** — R:R improves 1.4x around earnings (DeepSeek)
4. **ETF: Macro-correlation regime** — SPY/DJI correlation spike = directional signal (Cerebras)
5. **COMMODITY: Inverse flip** — inverse test flips kill → promote (all engines)

### BONUS Discoveries (Phase 2 — Buffy Complementary Swarms)

| # | Discovery | Asset | Finding |
|---|---|---|---|
| 1 | Entry/Exit Buffer Optimization | CRYPTO | ATR percentile > 70 = mean reversion WR boost |
| 2 | Polymarket/Kalshi Correlation | FOREX | Polymarket volume spike confirms 4h FX momentum |
| 3 | Regime HMM Alignment | ETF | VIX regime 3 = inverse ETF long, 73% win rate |
| 4 | Kelly Position Sizing | COMMODITY | Full Kelly=18%, half-Kelly=9%; FOREX=0 until fixed |
| 5 | Cross-Asset Correlation | ETF/CRYPTO | dXY>1.5 = directional equity signal; BTC-Gold corr turn = macro indicator |

### Priority Action Items

| Priority | Action | Reason |
|---|---|---|
| **IMMEDIATE** | Kill COMMODITY inverse strategies | 3/3 engine consensus, negative Sharpe |
| **HIGH** | Rescue FOREX | PF=0.26 — needs inverse strategy or session filter |
| **MEDIUM** | Scale ETF strategies | Sharpe=6.375, WR=60.9% — best in system |
| **MEDIUM** | Add Polymarket signal layer to CRYPTO | Volume spike = momentum confirmation |
| **LOW** | Investigate EQUITY news-sentiment edge | R:R improves 1.4x around earnings |

### Output Files

All 6 files written to `swarm_runs/asset-class-swarm-20260507T215709Z/`:
- `manifest.json` — 492 bytes
- `findings.json` — 22,239 bytes (68 unique findings across 5 asset classes)
- `edges.json` — 10,833 bytes (33 validated edges)
- `kill_list.json` — 11,140 bytes (**39** kill recommendations — consensus across ≥2 engines)
- `promote_list.json` — 6,404 bytes (8 promote recommendations)
- `summary.md` — 3,815 bytes (executive summary)

**Hermes ping:** ✅ Sent via cross-PC protocol (msg ID: `8dc76151-6a5f-4f72-a4d4-4415a74c7882`)

---