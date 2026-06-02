# EAGLE2 Grounded Synthesis — Research Edge → Capital-Ready Strategies

**Author:** Claude Opus 4.8 (1M) · **Date:** 2026-06-02 · **Goal:** #1 (per-asset-class edge on /audit)

> **Provenance rule honored:** every number below is read from on-disk canonical JSON
> (`audit_dashboard/data/money_ready_verdict.json` gen 2026-06-02T10:19Z +
> `audit_dashboard/data/pf_registry.json` `by_asset_class*_policy_clean_net`). No model was
> allowed to "fetch" the page. AI brainstorm outputs (proxy fan-out) are quarantined in
> `reports/eagle2_brainstorm_*.md` and treated as *flavor, not evidence* — one model
> (Gemma) fabricated an "NVDA 62.9% WR" stat (that figure is `deepseek_r1`'s tournament WR).

---

## 0. TL;DR

- **`money_ready = []`.** As of 2026-06-02 10:19Z, **zero asset classes** pass the production
  (policy-clean) gate. This is consistent with the EAGLE2 thesis: *the live book has no
  deployable edge.*
- **The edge that exists is on `/audit/ai-tournament.html`, and it is PAPER, not production.**
  `deepseek_v4` (n=208, WR 57.7%, PF 3.46) is the single best real-sample sleeve anywhere in
  the project. The production policy-clean layer for the same universe is PF < 1.
- **The gap between those two numbers IS the entire problem.** Research/paper edge does not
  survive the translation into the policy-clean production layer because of (a) concentration,
  (b) resolver/label pollution, (c) thin-n, (d) no multiple-testing correction.
- **Best honest "pick" today: none are real-money-ready.** The defensible move is to
  *shadow-size the `deepseek_v4` tournament sleeve* and *forward-test `crypto_liquidity_wick_reversal`*,
  not to buy NVDA/BTC on our own signal. Rationale in §5.

---

## 1. Ground-truth current state (verbatim from canonical JSON)

### Production — policy-clean, money_ready_verdict.json (2026-06-02 10:19Z)

| Class | n | WR | PF | Expectancy | MDD | Verdict | Top sym (share) | Top src share |
|---|---:|---:|---:|---:|---:|---|---|---:|
| CRYPTO | 368 | 36.1% | 0.92 | −0.0077 | 1.00 | **NOT_READY** | BTCUSDT (22%) | 55% |
| EQUITY | 52 | 26.9% | 0.33 | −0.0183 | 0.62 | **NOT_READY** | INTC (17%) | 42% |
| FOREX | 32 | 28.1% | 0.48 | −0.0227 | 0.82 | INSUFFICIENT | USDJPY (25%) | 34% |
| FUTURES | 13 | 15.4% | 0.52 | −0.0078 | 0.17 | INSUFFICIENT | CL=F (31%) | 85% |
| ETF | 3 | 66.7% | 1.46 | 0.000 | — | INSUFFICIENT | SPY (50%) | 100% |
| COMMODITY | 4 | 50.0% | 1.68 | 0.004 | — | INSUFFICIENT | GC=F (75%) | 50% |
| BOND | 0 | — | — | — | — | INSUFFICIENT | — | — |
| UNKNOWN | 9 | 66.7% | 0.72 | −0.0068 | — | INSUFFICIENT | AAPL (67%) | 89% |
| PENNY_STOCK | 1 | 0% | 0.00 | — | — | INSUFFICIENT | SOFI | 100% |

CRYPTO gate detail: `dsr_ok=false`, `spa_p=0.59` (1/5 strategies pass SPA), `pbo=0.22`,
`mdd=1.0`, `cvar_95=−85.1%`. Even the largest class fails every risk gate except PBO.

### Production strategies, n≥20, PF>1 (pf_registry policy_clean_net) — the ONLY positive signals

| Class | Strategy | n | WR | PF | Single-source? |
|---|---|---:|---:|---:|---|
| CRYPTO | `crypto_liquidity_wick_reversal` | 30 | 60.0% | **1.55** | 100% (artifact-flag) |
| CRYPTO | `atr_percentile_gate` | 29 | 58.6% | **1.10** | 100% (artifact-flag) |

Everything else with n≥20 is PF < 1 (`battleground_luxalgo` 0.83, `copy_trader_clones` 0.78,
`regime_terminal` EQUITY 0.75, `copy_trader_intel`/`ml_breakout` 0.00).

### Paper — ai-tournament.html leaderboard (real-n sleeves, noise-stripped)

| Model sleeve | n_resolved | WR | PF |
|---|---:|---:|---:|
| **deepseek_v4** | 208 | 57.7% | **3.46** |
| gpt4o | 134 | 59.7% | 3.14 |
| deepseek_r1 | 132 | 62.9% | 2.93 |
| claude_haiku_4_5 | 74 | 66.2% | 2.71 |
| nvidia_minimax_m2 | 25 | 64.0% | 2.53 |

(The PF 24 / 11 / 10 top-of-board entries are n_resolved = 9 / 7 / 10 — pure noise, correctly
ranked below threshold by `min_n_to_rank`.)

**Where the most profitable picks live → `/audit/ai-tournament.html`, deepseek_v4 sleeve.**
But this is forward-paper, evaluated under more generous labeling than the policy-clean layer.

---

## 2. Why paper edge dies in production (root cause, evidence-backed)

1. **Concentration artifacts.** CRYPTO top source = 55% of the book; FUTURES top source = 85%;
   the 2 PF>1 strategies are *100% single-source*. A single emitter's regime carries the whole
   class — when it rolls over, the class collapses. `is_single_source_artifact` exists but is
   not a hard pre-DSR gate.
2. **Resolver/label pollution.** CRYPTO CVaR95 = −85% with MDD = 1.0 is a tell of mislabeled /
   never-closed tails (consistent with the long-standing `outcome_resolver` live-close + ghost-row
   issues in repo memory). Paper tournament uses cleaner closes → higher WR.
3. **Thin-n + multiple testing.** ETF n=3, COMMODITY n=4, BOND n=0. The 2 "good" crypto
   strategies are n≈30. Across ~73 class×strategy cells, 2 surviving PF>1 at α=0.05 is exactly
   what you expect **by chance** — and we apply **no Bonferroni/FDR correction** before promotion.
4. **Standards mismatch.** Tournament scoring vs `money_ready_verdict` gate use different
   labeling, cost, and inclusion rules. Same picks, two scoreboards.

---

## 3. Per-asset-class strategy archetypes to backtest (the "more strategies" ask #1/#2)

Grounded in what already shows life + standard institutional archetypes. Each is a *hypothesis to
pre-register* (rule M-107) — not a claim of edge.

| Class | Archetype to backtest | Why (evidence) | First step |
|---|---|---|---|
| CRYPTO | Liquidity-wick-reversal **de-concentrated** (rotate beyond single source) + ATR-percentile vol gate | Only 2 prod sleeves with PF>1 are both this family | Re-run on ≥3 sources; check PF holds out-of-source |
| EQUITY | Cross-sectional momentum (12-1) + 200-day MA trend filter, top-decile | `regime_terminal` 0.75 PF shows trend logic underwater on current emitter; classic momentum is the cheapest replicable equity edge | Walk-forward on S&P 500 universe in `ejaguiar1_backtests` |
| ETF | **Dual-momentum** (abs + relative), monthly rebalance | EAGLE consensus "best lab edge, low concentration"; n=3 live insufficient | 24-mo walk-forward, SPY/EFA/AGG/GLD sleeve |
| FOREX | Carry + trend overlay (not mean-reversion scalps) | FOREX WR 28% PF 0.48 = current intraday signals are anti-edge; resolver-mislabel suspected | Rebuild resolver first, then test daily carry |
| COMMODITY | Time-series momentum (managed-futures KMLM/DBMF style) | n=4 too thin; momentum is the documented commodity edge | Long lookback backtest before any live |
| BOND | Yield-curve / duration-timing pilot | n=0 — pure data gap | Stand up data feed first |
| FUTURES | Drop intraday; only TSMOM | WR 15% PF 0.52, 85% single-source = artifact | Quarantine current emitter |

**Where to document them:** strategy *definitions + backtest results* → **`ejaguiar1_backtests`**
(this is also the destructive-op backup DB per project rule); live *emitted picks* →
**`ejaguiar1_stocks`**. Pre-registration row → `reports/hypothesis_registry.json` (M-107) before
any backtest is run.

---

## 4. Statistical "real-money-ready" framework (ask #4/#5/#6)

Consolidated from the EAGLE2 tables + repo's existing DSR/PBO/SPA gates. Two of three brainstorm
models independently named **multiple-testing correction** as the #1 missing gate.

**Bare minimum (a signal is NOT capital-ready if it fails any):**
PF ≥ 1.5 · Sharpe ≥ 1.0 (net of cost) · MDD ≤ 20% · IS/OOS split with OOS PF ≥ 80% of IS ·
**Bonferroni / FDR over the number of strategies tested** · flat 5-bps cost model.

**Ideal (production-grade):** purged-embargoed walk-forward (30d purge + 10d embargo) ·
block-bootstrap 1000-resample CI (95% CI for PF must not cross 1.0) · regime-segmented
(edge in ≥3 of 4 regimes) · asset-class cost+slippage curves · DSR/PBO/SPA · HHI < 0.20 ·
shadow-size ≤0.5% for 4–8 weeks.

**Forward-testing minimum:** ≥30–50 distinct symbols/instances per class, ≥2× longest lookback
duration, live PF within ±10% of backtest PF for two consecutive 4-week windows before scaling.

**The single most important gate we are missing today:** a **multiple-testing correction applied
to the cross-section of strategies *before* DSR/SPA** (CLAUDE.md already flags concentration gate
not enforced pre-DSR → 2 false Tier-1 PASSes). Bonferroni at α=0.05 over ~73 cells = required
p < 0.00068; neither surviving crypto sleeve clears that on n≈30.

---

## 5. "Best picks today" — honest answer (ask #1)

**No pick in the project is real-money-ready.** Detailed rationale per the candidates asked:

- **NVDA** — We have *no clean equity signal on NVDA*. EQUITY production is WR 27% / PF 0.33.
  NVDA's appeal is a fundamental/momentum macro story (AI capex leader), not our edge. As a
  *long-only buy-and-hold* it is a reasonable beta position, but that is **not a strategy we
  validated** — do not present it as an /audit pick. The one model that "endorsed" NVDA cited a
  fabricated 62.9% WR (actually deepseek_r1's tournament number) — exactly the hallucination
  CLAUDE.md warns about.
- **BTCUSD** — Our *only* PF>1 crypto sleeves (`crypto_liquidity_wick_reversal` 1.55,
  `atr_percentile_gate` 1.10) trade crypto incl. BTC, and BTCUSDT is the top crypto symbol (22%).
  This is the **most defensible forward-test candidate** — but n≈30, single-source, fails
  Bonferroni. Shadow-size only.
- **Safe long-term pick** — A broad index ETF (e.g. SPY/VOO) is the only "well-known safe" holding
  defensible *without* a proven signal: it is a market-beta allocation, not an alpha claim. ETF
  dual-momentum (§3) is the path to turning that into an actual backtested sleeve.

**Defensible action ranking:** (1) shadow-size `deepseek_v4` tournament sleeve at ≤0.5%;
(2) forward-test `crypto_liquidity_wick_reversal` de-concentrated; (3) backtest ETF dual-momentum;
(4) fix CRYPTO/FOREX resolver before trusting any of those WRs.

---

## 6. Plan

### Short-term (0–2 weeks)
1. Add **Bonferroni/FDR pre-gate** to `money_ready_verdict` before DSR/SPA (close the false-PASS hole).
2. Enforce `is_single_source_artifact` as a **hard reject** at promotion (kills the 2 false-positive crypto sleeves until de-concentrated).
3. Resolver hygiene pass on CRYPTO + FOREX (the CVaR −85% / MDD 1.0 tell).
4. Pre-register the §3 archetypes in `reports/hypothesis_registry.json`.

### Long-term (3–12 weeks)
1. Purged-embargoed walk-forward harness as the *single* promotion path (kill the two-scoreboard split — tournament and production must use the same labels/costs).
2. Shadow-size sleeve for anything that clears the harness; ≤0.5% capital, 4–8 wk, live-PF tracking.
3. Build ETF dual-momentum + commodity/bond data feeds (the empty-class gaps).
4. Promote to real capital only after two consecutive 4-week windows hold within ±10% of backtest PF + regime-robustness.

**Definition of done (quarterly):** ≥2 sleeves with live PF ≥ 1.5 surviving Bonferroni, HHI < 0.20
book-wide, resolver dispute < 1%.

---

## 7. Achievements this session
- Synced local repo to origin/main (1820 commits behind → 0); stale 2538-file index preserved on `backup/presync-20260602`.
- Verified all 3 new LiteLLM proxy modes live: `ollama-cloud-large`→Claude, `ollama-cloud`→Qwen, `ollama-cloud-local`→Gemma (`reports/eagle2_brainstorm_*.md`).
- Reconciled 30+ peer EAGLE docs against canonical JSON; corrected the record where a model fabricated a pick stat.
- Produced this grounded synthesis + per-class backtest archetypes + real-money-ready framework.
