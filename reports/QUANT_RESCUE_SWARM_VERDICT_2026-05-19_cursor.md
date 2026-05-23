# Quant Rescue Swarm Verdict — 2026-05-19 (Cursor session)

**Prompt:** `swarm_runs/_prompts/quant_rescue_deepdive_2026-05-19.md`  
**Runs:** R1 `all-free-api`, R2 `consensus-3`, R3 `non-opus-4` (follow-up), R4 `all-cli` (follow-up)  
**Grok (WSL):** full Q1–5 + Q4 ranking follow-up  
**Local:** `ollama_local` (R1); HF router skipped (no `HF_API_KEY`); large GGUF runs timed out / still running

**Ground truth (do not override):** 11/11 pre-registered causal hypotheses **killed** by `tools/edge_stability_harness.py::is_admissible()`. Class-level PF in `pf_registry.json` is **ledger accounting**, not harness-admissible edge unless a **new** pre-registered family clears the gate forward.

---

## Executive summary (concise)

| Question | Verdict |
|----------|---------|
| **Salvageable per class?** | **No for live money today.** Honest posture: **paper-only** everywhere except a **narrow CRYPTO probe** (mega_mutation forward track + optional intraday microstructure experiment). EQUITY/FOREX/BOND/FUTURES daily-bar rescue is **not** supported by the 11/11 kill + thin/biased resolution. |
| **#1 lever** | **Dual track, ordered:** (1) **Data integrity at emission** — dedup at writer, policy-clean tagging, dashboard reads `pf_registry` only (Kilo + R3 panel + OpenCode). (2) **Scope amputation** — freeze non-crypto **new** hypothesis work; crypto-only for any 90-day bet (Grok + xAI + DeepSeek). |
| **Universe widening** | **Noise** without a primary signal (Grok, xAI, DeepSeek, Groq, ollama_local R1). Narrow aperture is selection bias, not edge. |
| **3-month bet** | Fund **intraday/tick crypto microstructure** only. **P(admissible) ≈ 12–20%** (Grok Q4: 12%; Grok Q1: 18–22%; xAI: 15–20%). Meta-labeling / daily causal-inference / cross-sectional daily ranking: **≤7%** or **invalid** (no primary). |
| **Week-1 plan** | See §6 — integrity + freeze + mega_mutation paper ledger + 3–4 week intraday **probe** (not full build). |

---

## 1. Salvageable or paper-only?

### Consensus (evidence-respecting engines)

- **Grok (WSL):** Paper-only for all classes under daily free bars. CRYPTO `mega_mutation` (n=72, PF 2.19) forward-unproven — paper only. *"Retail-accessible daily-bar edge space is empty."*
- **DeepSeek (R2):** *"Not salvageable… paper-only is the only honest answer."* Exception: 6-month paper on mega_mutation only.
- **xAI (R2):** *"Retail-accessible daily-bar edge space is empty."* Paper or tiny live on single crypto cohort while tracked.
- **Kilo (R2, partial/timeout):** ~5–8% chance in CRYPTO **if** data layer fixed first.

### Dissent (flagged — registry PF ≠ harness edge)

- **Claude (R4):** Called **EQUITY money-ready** (PF 1.85, n=401) and **FOREX contested/T2** from `by_asset_class_policy_clean_net`. **Reject for rescue verdict:** conflates heterogeneous closed-pick ledger with **admissible causal edge**; ignores 11/11 kill and MACRO autopsy (EQUITY clean n≈33 for verdict-grade cohorts in prompt).
- **OpenCode (R4):** Conditional Y on `smart_money_consensus` / `cta_replicator` from registry slices. **Same flaw** — strategy-level backtest PF without walk-forward harness sign-stability.
- **Groq (R1), ollama_local (R1):** Generic "maybe causal-inference / meta-labeling" — **prompt rephrase**, not architecture-grounded (fabrication risk HIGH).

### Synthesis

**Salvageable into profitable multi-class picks? No.**  
**Salvageable into a disciplined paper lab with one crypto forward track + one intraday probe? Yes, with low base rate.**

Per asset class (money-ready **today**, harness-grade):

| Class | Money-ready today? | Engine notes |
|-------|-------------------|--------------|
| **CRYPTO** | **No** (paper probe only) | Only class with a non-killed *candidate* (mega_mutation); class PF 1.23 net in registry is not Tier-2. xAI/Grok: intraday only path. |
| **EQUITY** | **No** | DeepSeek/Grok: daily edge empty; resolution 45%. Claude/OpenCode **dissent** — see above. |
| **COMMODITY** | **No** | n=52 policy-clean net — underpowered; no admissible causal family. |
| **ETF** | **No** | n=1 in registry. |
| **FOREX** | **No** | 11/11 + 22% resolution; Claude/OpenCode **dissent** on cta_replicator — not harness-validated. |
| **BOND** | **No** | n=1; unanimous N. |
| **FUTURES** | **No** | n=12 clean; DeepSeek/xAI: halt emitter. |

---

## 2. ONE highest-leverage change

**Ordered pair (not either/or):**

1. **Data / integrity (Kilo, R3 DeepSeek/xAI/Groq, OpenCode):** Dedup at emission; `hypothesis_id` + bar_freq on insert; dashboard **only** `pf_registry` / policy-clean-net view; deterministic registry regen. *Causal mechanism:* duplicate re-emissions and policy leakage manufacture fake WR (prompt: ~4,830 dupes; R4 OpenCode: 42% re-emission rate claim).

2. **Scope (Grok, xAI, DeepSeek):** **Stop new daily-bar alpha on non-crypto.** All 90-day engineering on **crypto intraday** only.

**Not #1:** Universe widening (unanimous noise). **Not #1:** Meta-labeling or causal-inference on daily data (Grok Q4: 1–4% / dead-on-arrival without primary).

---

## 3. Symbol-universe widening

**Verdict: noise, not lever** (unless a **primary** already clears harness — none do).

- **Grok:** *"Noise… multiplier of existing problem."*
- **xAI:** *"Noise… best WR on narrowest aperture = selection bias."*
- **DeepSeek:** *"Multiplying false discovery rate by 14×."*

---

## 4. Three-month bet + realistic odds

| Approach | Grok Q4 P(admissible) | Grok Q1 | xAI R2 | DeepSeek R2 | Panel call |
|----------|----------------------|---------|--------|-------------|------------|
| **A) Intraday/tick crypto microstructure** | **12%** | 18–22% | 15–20% | <5% (arch can't support) | **Fund (probe only)** |
| B) Cross-sectional daily ranking | 7% | — | second-order | <5% | Deprioritize |
| C) Meta-labeling on existing signals | **1%** | 0% w/o primary | useless w/o primary | <5% | **Do not fund** |
| D) Causal-inference on daily data | 4% | — | redundant w/ harness | <5% | **Do not fund** |

**Mechanism (A):** short-horizon **adverse-selection / liquidity provision** to uninformed aggressive flow on liquid perps (Grok Q4) — sign more stable than funding/COT/on-chain daily features that flipped in walk-forward.

**Recommendation:** **3–4 week time-boxed probe** (Grok Q4): Binance 1m + aggTrade, top 10–12 perps, replay through existing harness on 6–9mo history; **stop** if no window clears eff/sign/cost. Full 3-month build only if probe passes.

**Joint P(any approach admissible in 90d):** Grok ≈ **5–6%**.

---

## 5. Where engines DISAGREED (do not average)

| Topic | Camp A | Camp B | Adjudication |
|-------|--------|--------|--------------|
| **Salvageability** | Paper-only (Grok, DeepSeek, xAI) | EQUITY/FOREX "money-ready" from registry PF (Claude, OpenCode) | **Camp A** — registry ≠ harness; 11/11 is decisive for *causal* claims |
| **Week-1 priority** | Data fix first (Kilo, R3 all) | Freeze + intraday probe first (Grok, xAI) | **Sequence:** 1–2d dedup/registry wiring (Kilo/OpenCode), then freeze + probe on **clean** path |
| **3-month bet** | Intraday crypto (Grok, xAI) | Meta-labeling / causal-inference (Groq, ollama R1) | **Intraday crypto** only; meta/causal on daily **invalid** |
| **Week-1 "kill system"** | Freeze all 36 workflows (DeepSeek) | Surgical emitter cuts (OpenCode, Claude) | **Surgical** — freeze **new** non-crypto hypotheses + dead emitters; keep resolution/registry CI |
| **DeepSeek vs Grok on P(intraday)** | <5% | 12–22% | Report **range**; both agree it's the *only* bet worth attempting |

### Engines that mostly rephrased the prompt

- **gemini_api, ofox, pollinations (R1):** empty / 500 / no API key.
- **Groq (R1):** generic ML stack without MySQL/harness specifics.
- **ollama_local (R1, llama3.2:3b):** vague meta-labeling — **LOW signal**.
- **gemini, agent, copilot (R4):** described **code changes** not adjudication — **task confusion**; ignore for Q1–5 substance.

---

## 6. Week-1 action plan (swarm-merged, architecture-specific)

**Days 1–2 — Integrity (Kilo + R3 + OpenCode)**

1. **Emitter dedup guard** before MySQL/`at_raw_picks` append (dedup_hash / 5-min bucket).  
2. **Mandatory fields** on insert: `hypothesis_id`, `bar_freq`, `emission_event_ts`, `policy_clean` flag.  
3. **Dashboard contract:** tiles read **`pf_registry.json`** (`by_asset_class_policy_clean_net`) only; red-banner if raw ≠ canonical.  
4. **Registry regen** script: deterministic `closed_picks → pf_registry` + sha256 in CI.  
5. Audit query: re-emissions, resolve_ts ≤ emission_ts, per-class unique symbols (30d).

**Days 3–4 — Scope freeze (Grok, xAI, DeepSeek)**

6. **Freeze** new daily-bar hypothesis registrations outside crypto.  
7. **Halt** FUTURES emitter (n=12, PF≈0.96 net). Quarantine **quan_engine** from CRYPTO class aggregates (volume drag).  
8. **`paper_crypto_mm` table** — forward paper for **mega_mutation** only; Binance 1m resolution; no registry backfill in sample.

**Days 5–7 — Probe kickoff (Grok, xAI)**

9. Minimal **WebSocket** 1m OHLCV + aggTrade → parquet/MySQL side schema (top 10–12 perps).  
10. **One** pre-registered microstructure family (e.g. signed volume imbalance / post-liquidation mean reversion); run `edge_stability_harness` — **do not** change killed families.  
11. Extend harness: `bar_freq=intraday` + optional 5d windows (xAI) — **no** retroactive re-test of killed IDs.

**Do NOT week-1:** widen symbol universe; meta-label daily noise; promote EQUITY/FOREX to live based on registry PF alone.

---

## 7. Local / HF model consultation (supplemental)

| Run | Status | Notes |
|-----|--------|-------|
| `ollama_local` R1 (llama3.2:3b) | OK | Weak; meta-labeling focus — discounted |
| `qwen3:14b`, `deepseek-r1:14b` CLI | Timeout (>15m) | No output captured |
| `phi3.5` via Python | 180s timeout | — |
| `mistral-nemo`, `qwen2.5-coder:7b` api_consult | Running / slow | Check `swarm_runs/local-*-money-ready.txt` when complete |
| `huggingface` swarm engine | Skipped | No `HF_API_KEY` |

**Local-model alignment (where available):** smaller local models **mirror Groq R1** (meta-labeling, causal-inference) and **contradict** the 11/11 kill — treat as **non-independent** generic LLM prior, not empirical verification.

---

## 8. Skepticism / independence checklist

- [x] **11/11 kill** treated as settled — no engine allowed to "find edge" in dashboard tiles.  
- [x] **Claude/OpenCode R4** flagged for **registry PF → live edge** leap.  
- [x] **Failed/empty engines** not counted toward consensus.  
- [x] **Grok + xAI** treated as strongest architecture-grounded pair (crypto intraday + paper-only).  
- [x] **N agreeing** on meta-labeling (Groq, ollama) noted as **correlated stale prior**, not verification.

---

## 9. Source index (engine → claim)

| Engine | Run | Key claim |
|--------|-----|-----------|
| Grok WSL | direct | Paper-only; scope→crypto; universe noise; intraday 18–22%; week-1 matrix + websocket |
| Grok WSL | Q4 | Rank A=12% … C=1%; fund A probe only |
| DeepSeek | R2 | Paper-only; kill workflows; <5% on new techniques |
| xAI | R2 | Paper-only; crypto intraday 15–20%; week-1 freeze + paper_crypto_mm |
| Kilo | R2 | Data layer #1; intraday 5–8% |
| DeepSeek/xAI/Groq | R3 | Kilo wins week-1 sequencing |
| Claude | R4 | **DISSENT:** EQUITY/FOREX money-ready from registry |
| OpenCode | R4 | **DISSENT:** smart_money / cta_replicator paths |
| Groq | R1 | Meta-labeling 30–40% — **disregard** |

---

## 10. Concise user-facing bottom line

1. **Salvageable?** **Not for multi-class live money.** **Paper-only** + **crypto-only** R&D lane.  
2. **#1 lever:** **Fix emission/registry truth**, then **crypto-only intraday probe** — not universe widening.  
3. **3-month bet:** **Intraday/tick crypto microstructure** — **~12–20%** chance of one admissible family; run as **4-week probe** first.  
4. **Week-1:** Dedup + pf_registry dashboard contract + freeze non-crypto hypotheses + mega_mutation forward paper + start websocket probe.

**Artifacts:** `swarm_runs/quant-rescue-r{1,2,3,4}/`, Grok session IDs in tool output, this file.
