# DAILY IDEAS — OLLAMA MODEL ROTATION — 2026-05-16

**Author:** Claude Opus 4.7 (1M) orchestrator + Ollama model fleet
**Method:** Cross-checked ~30 `daily_idea*` / `DAILY_IDEAS*` files across 4 repo
copies (main, `_deepdive_pr`, `tmp/dailyidea-main-push`, `tmp/ghcopilot-main`),
built one consolidated quant-audit prompt, rotated it through Ollama cloud +
local model families for variety of insight.
**Goal:** Goal #1 — phenomenal per-asset-class edge on `/audit`.

---

## 0. Cross-check result (input to the model rotation)

| File | Copies | Verdict |
|---|---|---|
| `daily_idea_antigravity.MD` | 3 — byte-identical | 8-Rung S-BEP protocol + PCG-5 gates + sizing schedule |
| `daily_idea_cursor.MD` | 3 — ghcopilot copy is **stale** (missing 23:31 EST addendum) | 10 CI/DB ideas + 4 enhancement clusters |
| `DAILY_IDEAS.MD` | 4 — **all 4 differ** (main 130KB canonical, `_deepdive_pr` 55KB oldest, tmp copies 76KB) | 12-session brainstorm dump; main is source-of-truth |
| `daily_ideas_edge_per_class_*.md` | 4 — byte-identical | 16 ranked edges + 5 next-steps + 3 anti-edges |
| `daily_ideas_ghcopilot_auto.MD` | 3 — minor wording drift | 8 DB/CI enhancements |
| `daily_ideas_nvidia.MD` | 3 — byte-identical | GPU/CI infra (no edge thesis — flagged drop) |
| `DAILY_IDEAS_GROK_2026_05_16.MD` | 1 | COMMODITY post-dedup Tier-1 claim; CRYPTO DOW refuted |
| `DAILY_IDEAS_KIMICLI_2026_05_16.MD` | 1 | `edge_filter_engine_v3.py` — CRYPTO/EQUITY/COMMODITY all PF>2 |
| `DAILY_IDEAS_CURSORCLI_2026_05_16.MD` | 1 | strict gate — **only EQUITY** passes real-money |
| `daily_ideas_KimiCode.MD` | 1 (30KB; `.kimi` baseline copy = 0 bytes empty) | MySQL-native rewrite, 3 new tables |
| `daily_ideas_Kilocode_laguna.MD` | 1 | DB health audit + 12-point schedule |
| `daily_ideas_synthesis_2026-05-15.md` | 1 | prior 11-file synthesis — 6/11 sources were dup/missing |
| `dAILY_IDEAS_GROK_MAY162026_502pmEST.MD` | 1 | **placeholder stub, 244 bytes — no content** |

**Two unresolved conflicts fed to the models:**
1. KimiCLI says CRYPTO+EQUITY+COMMODITY all filter to PF>2; Cursor-CLI strict gate says ONLY EQUITY passes.
2. COMMODITY PF reported as 2.26 / 2.57 / 3.89 / 21.33 across files.

---

## 1. Models rotated

| Family | Model | Tier | Status |
|---|---|---|---|
| OpenAI-OSS | `gpt-oss:120b-cloud` | cloud | ✅ |
| Moonshot Kimi | `kimi-k2.5:cloud` | cloud | ✅ (k2 + k2-thinking 500-error, used k2.5) |
| Zhipu GLM | `glm-5:cloud` | cloud | ✅ |
| DeepSeek | `deepseek-v3.2:cloud` | cloud | ✅ |
| Qwen | `qwen3:14b` | local | ✅ |
| Google Gemma | `gemma3:4b` | local | ✅ |
| Microsoft Phi | `phi3.5` | local | ✅ |
| Qwen-Coder | `qwen2.5-coder:14b` | local | ✅ |
| MiniMax / Cogito / qwen3-coder:480b | cloud | — | ❌ Ollama cloud auth dropped mid-run (`ollama signin` needed) |
| Mixtral 8x7b / glm-4.7-flash | local | — | ❌ host RAM exhausted (peers held VRAM; 16.8GiB needed / 2.4GiB free) |

8 models delivered insight across 7 distinct architecture families.

---

## 2. Strongest NON-OBVIOUS insights (de-duplicated, ranked)

### INSIGHT-O1 — COMMODITY PF 21.33 is a bookkeeping artifact, not a market anomaly *(gpt-oss:120b, glm-5, deepseek, qwen3:14b — 4-model convergence)*

- PR #994 removed the CT=F COT **duplicate-emission** but did **not re-aggregate** PF. The 21.33 figure still contains the duplicated 144 cotton trades — inflates WR ~+12pp and PF ~9×.
- glm-5: the bug likely double-counted Commercial-hedging exits while position stayed open → phantom mean-reversion → the 88.2% WR.
- **Falsification test (deepseek + gpt-oss):** regress CT=F returns on *lagged* COT net-position change. If R² collapses from >0.4 to <0.05 after dedup, the 21.33 PF is spurious serial-correlation and the true number is Grok's ~2.57.
- **Sizing rule:** even at 2.57, haircut hard — cotton open interest cannot absorb the implied Sharpe without slippage destroying the edge. Size by **Sharpe**, not PF.

### INSIGHT-O2 — KimiCLI vs Cursor-CLI = multiple-testing / post-hoc subset selection *(gpt-oss:120b, kimi-k2.5, glm-5, deepseek, qwen3:14b — 5-model convergence)*

- KimiCLI's CRYPTO PF 3.15 (n=305, <4% of CRYPTO volume) was found by scanning the "LONG+7-family" subset **after** observing aggregate underperformance. That induces look-ahead/selection bias estimated at ~1.8 Sharpe.
- **Cursor-CLI is correct:** only EQUITY's *full, de-duplicated* universe passes a strict pre-trade gate without peeking.
- **Resolution:** trust KimiCLI's filter ONLY if its filter spec is timestamped *before* the first trade in the sample. Otherwise re-run KimiCLI's PF>2 subset through Cursor-CLI's PCG-5 exec-time gate (latency + slippage + per-strategy WR>55%) — survivors will match.

### INSIGHT-O3 — "Confidence inversion" has two competing mechanisms; both are testable *(gpt-oss:120b, kimi-k2.5, glm-5, deepseek)*

- **Hypothesis A (gpt-oss) — code bug:** confidence is a Beta(α,β) fit where the code feeds β as the *mean* instead of the *failure count*, flipping the posterior. Fix: `α ← α+wins, β ← β+losses`. Cheap to check in the scorer.
- **Hypothesis B (kimi-k2.5) — adverse selection:** high-confidence signals coincide with latency-arbitrage footprints (large incoming market orders) — the model is providing liquidity to toxic flow. Fix: a "confidence-collapse" filter — if predicted vol term-structure inverts within 100ms of signal generation, withhold execution.
- **Action:** decide A-vs-B by inspecting the scorer code first (5 min). If A → one-line fix. If B → micro-structure filter.

### INSIGHT-O4 — non-ergodic cumulative-PnL is the trap every agent missed *(gpt-oss:120b, deepseek, qwen2.5-coder)*

- `claude_gainer_st` (cumulative PF 6.80 → real WR 26.5%) is an **absorbing-barrier** artifact: early wins inflated the denominator; path-dependent kill-switches / position-sizing decay masked later losses. Geometric-Brownian assumptions fail under kill switches.
- **Mandate:** pre-live validation must use **log-return bootstrap resampling**, not cumulative sum. Strategy selection must read **rolling-window, post-blacklist stats only** — never cumulative-since-inception.

### INSIGHT-O5 — ship UTC-hour edge as an execution wrapper, not a strategy *(gpt-oss:120b, kimi-k2.5, glm-5, qwen3:14b — 4-model convergence; HIGHEST-ROI / LOWEST-EFFORT)*

- 22:00 UTC = 61.2% WR / 08–09 UTC = death zone. It is a **clock-time variance risk premium** (overnight vs Asia open), not directional alpha.
- **Implement:** hard time-gate blocking all CRYPTO emissions 06:00–11:00 UTC + a UTC-hour mask that scales position size by inverse realized vol of the prior 24h bucket. Zero new model, zero retraining, uses existing infra.
- gpt-oss: the 22:00 halo appears jointly in BTC, crude (CL) and SPY momentum after timezone-drift adjustment → combined PF ≈ 2.84 / WR ≈ 68% across the 3 highest-liquidity symbols, ρ ≈ 0.12.

### INSIGHT-O6 — cross-asset edge nobody proposed: BOND/COMMODITY COT as a CRYPTO sizing overlay *(kimi-k2.5 — novel)*

- BOND is too thin (n=11–18) for a *directional* signal — but usable as a *real-time filter*. When COMMODITY COT net-speculator positioning hits extreme percentiles (|z|>2), rotate CRYPTO sizing inversely via variance-risk-premium.
- Pure volatility-overlay trade, orthogonal to CRYPTO directional alpha. Exploits the covariance breakdown during COT-release windows that the duplicate bug previously obscured.

### INSIGHT-O7 — single source of truth: canonical PF registry *(gpt-oss:120b)*

- The "2.26 vs 21.33" ambiguity exists because every daily-ideas file recomputes PF independently. Build a **canonical PF registry** table keyed `(asset_class, strategy_id, trade_date)`: ingest raw execution ledger → apply dedup + spot-price sanitizer → recompute PF/WR → version-stamp. Every downstream surface (dashboards, daily-ideas, sizing engine) reads ONLY this table.

---

## 3. Contested / minority takes (flagged — do NOT ship blind)

- **glm-5 & deepseek-v3.2:** "invert the signal of the 4 sub-PF<1 crypto drag strategies — a PF<1 strategy is a robust *negative* edge, flip it to PF~2.5." ⚠️ **Caution:** PF<1 ≠ exploitable inverse edge once spread/fees/slippage are paid twice; an inverted loser usually nets to PF<1 again. Backtest the *inverse with full friction* before believing this. Safer baseline action = **quarantine** the drag strategies (matches synthesis idea #4).
- **gemma3:4b:** "Forex −1026% PnL is almost certainly a system error, halt all FOREX." Partly correct — but memory already records the resolver live-close bug inflated non-crypto losses. Verdict: FOREX is genuinely sub-floor AND partly resolver-polluted. Re-resolve before final kill (mutate-before-kill protocol).
- **phi3.5 / qwen2.5-coder:** mostly generic ("multi-asset diversification", "recalibrate confidence") — low signal, retained only for family coverage.

---

## 4. Recommended action order (Ollama-fleet consensus)

1. **[5 min]** Inspect the confidence scorer code → decide INSIGHT-O3 Hypothesis A vs B.
2. **[1 h]** Ship INSIGHT-O5 — UTC time-gate (06–11 UTC block) behind `CRYPTO_HOUR_FILTER=1`. Free edge, highest ROI.
3. **[2 h]** Run the INSIGHT-O1 regression test on CT=F; block any COMMODITY sizing until R² verdict lands.
4. **[2 h]** Quarantine the 4 CRYPTO drag strategies (>40% volume, PF<1) — do NOT invert blind.
5. **[M]** Build INSIGHT-O7 canonical PF registry; re-point dashboard + daily-ideas at it.
6. **[M]** Backtest INSIGHT-O6 COT-overlay as a CRYPTO variance filter.

**Hard gate:** no real-money sizing until canonical-registry PF + 30-day rolling-clean (NOT cumulative) + DSR ≥ 0.85. INSIGHT-O4 says cumulative-since-inception numbers are structurally untrustworthy.

---
*Generated 2026-05-16. Ollama cloud auth needs `ollama signin` refresh — 3 cloud
models (minimax, cogito, qwen3-coder:480b) skipped. Companion file:
`DAILY_IDEAS_HUGGINGFACE.MD`.*
