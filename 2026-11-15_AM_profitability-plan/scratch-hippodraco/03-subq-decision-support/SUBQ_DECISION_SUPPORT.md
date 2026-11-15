# SubQ API Decision Support — Usage & Fact-Checking Framework
**Date:** 2026-11-15  
**Worktree:** scratch-hippodraco  
**Security rule (absolute):** `~/dbpasses.txt` is gitignored and contains live DB passwords + LLM API keys. **Never print, paste, echo, or commit its contents.** Read keys only at runtime to populate env vars or `tools/db_env.py` fallbacks. Never hardcode a key in committed code.

---

## 1. How to leverage SubQ API key(s) (methodology, not keys)

The SubQ (SubQuery) API key(s) live in `~/dbpasses.txt` alongside other provider keys (NVIDIA, Cerebras, OpenRouter, xAI, Cloudflare, etc.). They are read at runtime through `tools/db_env.py` (single source of truth) — the same pattern used by `tools/consult_multi.py` and the LiteLLM proxy.

**Runtime access pattern (do not hardcode):**
```python
from tools.db_env import get_stocks_creds, get_backtests_creds
# db_env.py reads env vars first (DB_PASS_STOCKS / DB_NAME_STOCKS, etc.),
# then falls back to verified defaults from ~/dbpasses.txt
creds = get_stocks_creds()   # {host, user, password, database, port}
```
For LLM/provider keys including SubQ, use the same `db_env.py` fallback convention or `~/dbpasses.txt` entry, resolved into an env var before the call. The key never touches a committed file.

**Recommended SubQ use cases (decision support only, never as a sizing surface):**
1. **Second-opinion triangulation** — ask SubQ (and other providers via fan-out) to critique a proposed edge: "Is this PF/WIN-rate claim consistent with the mandatory data-integrity filters?"
2. **Fact-check dashboard cells** — feed a suspicious `pick_funnel.html` WR/PF cell plus the canonical `pf_registry.json::by_asset_class_policy_clean_net` numbers; ask SubQ whether the cell is deduped, concentration-checked, and outlier-capped.
3. **Hypothesis pre-registration review** — ask SubQ to review a pre-registered hypothesis for multiple-testing flaws (nb_trials, look-ahead, survivor bias) before running it.
4. **Code review of QA scripts** — review `tools/pnl_zero_validator.py`, `tools/qa_blank_fields.py`, etc. for logic gaps.

**Never use SubQ output as:**
- A buy/sell signal
- A position-size input
- A substitute for clean OOS + cost-adjusted PF
- A replacement for the mandatory data-integrity filters

---

## 2. Fact-checking framework — is a SubQ response grounded in reality?

When SubQ (or any external model) gives an answer about profitability, edge, or a trading algorithm, run it through this checklist before acting:

| Check | Question | Pass criterion |
|-------|----------|----------------|
| **C1 — Source citation** | Does the response cite a specific file/line/JSON path (e.g., `audit_dashboard/data/money_ready_verdict.json::classes.EQUITY`)? | Must cite concrete, verifiable source |
| **C2 — (asset_class \| n \| timeframe)** | Are all performance claims labeled with asset class, sample size, and timeframe? | Reject any claim missing any of the three (money-maker-ready hard rule) |
| **C3 — Data-integrity filters** | Were the 6 mandatory filters applied (no backfill labels, no banned sources, sane-pnl guard, EXPIRED=non-win, intrabar validation, ≥3 months n≥30)? | If not, the WR/PF is inflated — reject |
| **C4 — Multiple-testing correction** | Was `nb_trials` = all strategies tested that season (not nb_trials=1)? Was DSR/SPA/PBO applied? | If nb_trials=1, the claim is statistically meaningless |
| **C5 — Cost reality** | Were realistic round-trip costs (fees/spreads/funding/roll) applied per class? | Equity ~0.10%, CRYPTO ~0.30%, FOREX ~0.08% (from `tools/data/transaction_costs.json`) |
| **C6 — Benchmark comparison** | Is the edge measured vs a transparent benchmark (SPY total return for equity/ETF, BTC-USD for crypto, flat cash for FX direction)? | Must beat benchmark, not just be positive |
| **C7 — Out-of-sample** | Was the selection rule pre-registered and never shown the test month? | Walk-forward required; in-sample-only = reject |
| **C8 — Single-source concentration** | Is >60% of decisive picks from one `source_system`? | If yes, it's concentration, not edge — reject |
| **C9 — Outlier cap** | Is PF > ~10? | Likely a few corrupt `pnl_pct` rows; cap/winsorize and recompute |
| **C10 — Reproducibility** | Can the claim be re-derived from the DB/JSON with a shown command? | Must be reproducible; frozen numbers are suspect |

**Grounding rule:** ALWAYS include canonical `pf_registry.json` numbers + `reports/OBS_FINDING_JUNE8.MD` rejected-hypothesis entries in the SubQ prompt. Multi-AI consensus increases signal-to-noise ONLY when the prompt is grounded. (5 models once converged on a wrong answer — COMMODITY as #1 alpha — because they never saw the leakage evidence.)

---

## 3. Logical-principles sanity check (grounded in reality)

Before trusting any SubQ-suggested algorithm or edge, confirm it rests on these principles:

| Principle | What it means | Red flag if violated |
|-----------|---------------|----------------------|
| **Economic rationale** | Why should this edge exist? (liquidity provision, mean reversion in over-extended assets, funding-rate arbitrage, etc.) | "The model found a pattern" with no economic story |
| **Cost-adjusted** | Edge survives after realistic fees/spreads/funding/roll | Edge disappears once costs applied |
| **Capacity-aware** | Edge doesn't depend on infinite size or zero market impact | Edge only works at tiny size |
| **Regime-stable** | Edge holds across bull/bear/sideways, not one month | Edge = one lucky regime |
| **Execution-realistic** | Assumes real fills, slippage, intrabar TP-before-SL | Assumes ideal fills, end-of-bar pricing |
| **Multiple-testing honest** | Corrects for all strategies tested that season | Reports best-of-thousands as if it were one test |
| **Negative filters count** | Knowing what NOT to trade is as important as what to trade | Only positive signals, no exclusion rules |

**Reject-without-reverify list (from money-maker-readyv2):** FOREX 14d WR 64%/PF 2.43; GBPUSD 58.8% n=114; `stocks_rsi2_pullback` n=894/PF 2.68; `mega_mutation` T1 without intrabar; `bt_backtest_trades` 32.6M rows as live edge; AI tournament WR as trading edge.

---

## 4. Recommended workflow

1. **Pre-register** the hypothesis in writing (asset class, style, holding period, entry/exit rule, benchmark, cost assumptions, nb_trials).
2. **Run locally first** against `dashboard_data.json` + `pf_registry.json` + DB via `tools/db_env.py` (read-only).
3. **Feed SubQ** the local numbers + hypothesis + mandatory-filter results; ask it to find flaws (C1–C10 above).
4. **Cross-validate** with a second provider (fan-out via `tools/consult_multi.py --fanout`) — require agreement grounded in the same canonical numbers.
5. **Only then** consider paper-pilot; never live capital until T2 certification (n≥100, PF≥1.5, WR≥50%, MDD<20% on forward record).

---
