# Local-Model Idea Harvest — Quant Rescue Deep-Dive

**Date:** 2026-05-19
**Lane:** LOCAL models only (ollama local + HuggingFace cache check). The cloud/swarm consultation is a separate agent's deliverable.
**Input prompt:** `swarm_runs/_prompts/quant_rescue_deepdive_2026-05-19.md` (full system architecture + 11/11 kill verdict) — tightened per-asset-class version at `swarm_runs/_prompts/_local_quant_focused_2026-05-19.txt`.
**Raw model outputs:** `swarm_runs/_local_harvest_2026-05-19/*.clean.txt` (ANSI-stripped; raw `.txt` retained too).

> Real model calls only — no fabricated content. Every idea below is traceable to a named local model's raw output file.

---

## 1. Models that ran

`ollama` was already running on `127.0.0.1:11434`. Six local (non-cloud-tagged) models were sent the focused per-asset-class prompt. All six responded.

| Model | Family | Params | Responded | Output quality |
|---|---|---|---|---|
| `qwen3:14b` | Qwen3 | 14B | YES | Good — followed format, mostly avoided killed families |
| `qwen3.5:9b` | Qwen3.5 | 9B | YES | Best — visible self-critique, explicit "no edge" honesty, format-clean |
| `deepseek-r1:14b` | DeepSeek-R1 | 14B | YES | Mixed — reasoning trace strong, but slipped a killed family (roll-yield) |
| `llama3.1:latest` | Llama 3.1 | 8B | YES | Weak — ~half the ideas are killed families (carry, COT) |
| `mistral-nemo:latest` | Mistral-Nemo | 12B | YES | Weak — re-proposed two killed families verbatim (on-chain counts, COT) |
| `phi3.5:latest` | Phi-3.5 | 3.8B | YES | Worst — open-interest/COT/contango/carry — almost all killed; verbose filler |

**HuggingFace / GGUF check:** `~/.cache/huggingface/hub` contains only small task-specific models — `ProsusAI/finbert`, `cardiffnlp/twitter-roberta-base-sentiment`, `sentence-transformers/all-MiniLM-L6-v2`, `Qwen2.5-3B-Instruct`, and `hpcai-tech/Open-Sora-v2` (video). No general-purpose chat GGUF beyond what ollama already covers. Per task rules, **no multi-GB models were downloaded fresh.** finbert/roberta are sentiment classifiers, not idea-generators — skipped. `Qwen2.5-3B` is strictly weaker than the ollama Qwen3 models already run, so it would add nothing. Local-ollama was the priority and is fully covered.

**Cloud-tagged models** (`gpt-oss:120b-cloud`, `deepseek-v3.1:671b-cloud`, `kimi-k2-thinking:cloud`, etc.) were **NOT run** — they are out of lane (cloud) and belong to the separate swarm agent.

---

## 2. Honest assessment of local-model output quality

Local models are materially weaker than the cloud swarm for this task. Concretely:

- **Killed-family recidivism was rampant.** Despite the prompt explicitly listing 11 forbidden families, `phi3.5`, `llama3.1` and `mistral-nemo` each re-proposed at least one (COT positioning, carry/funding-arb, roll-yield/contango, on-chain address counts). The smaller the model, the worse the recidivism. Those ideas are **discarded** below.
- **"Causal mechanism" was frequently just a restatement of the signal**, not a structural reason an edge persists net of cost. Most outputs do not engage with the 30 bps cost hurdle at all.
- **No model produced anything the harness would obviously pass.** They cannot run a walk-forward; their "would survive" claims are unverified assertion. Treat everything below as *hypothesis seed*, not edge.
- **The two Qwen models were the only substantive contributors.** `qwen3.5:9b` was the standout: it visibly reasoned about the 30 bps hurdle and honestly returned "No Retail Edge" for FOREX and BOND rather than fabricating an idea — which is the correct answer and matches the macro verdict.

So: of ~42 raw ideas (6 models x 7 classes), the **substantive, non-generic, non-killed** residue is small — roughly 6-8 distinct seeds, listed in section 3. The rest is filler.

---

## 3. Per-asset-class harvest — best non-generic, non-killed ideas

Killed families excluded: COT positioning, funding-rate directional, roll-yield, yield-curve momentum, PEAD daily, funding-arb carry, options-flow, on-chain address counts, funding-settlement cascade, exchange net-flow, cross-exchange premium.

Each surviving idea is tagged **[SUBSTANTIVE]** or **[THIN]**.

### CRYPTO

**Idea C1 — Volatility-cluster mean reversion** [SUBSTANTIVE] (`qwen3.5:9b`, echoed by `mistral-nemo`)
- **Signal:** Fade the daily open after a day where daily range > ~5% AND volume > 2.5x its 20-day average — i.e. enter counter-trend the bar after an extreme high-volume bar.
- **Data:** Binance public OHLCV, daily, top-50 USDT pairs. Retail-accessible, free.
- **Causal mechanism:** Volatility clustering is one of the most robust stylized facts in crypto, and extreme high-volume bars exhaust the resting passive liquidity on one side of the book; market-makers then re-quote wider and a portion of the move snaps back as inventory rebalances. The mechanism is microstructural, not regime-dependent — it should hold in both bull and bear vol regimes (the cluster is the signal, not the direction).
- **Harness note:** This is a *reversion* hypothesis with a participant-behavior mechanism, distinct from all 11 kills. To clear the harness it must show same-sign effect across 3/5 windows; the risk is that crypto trends through clusters in strong regimes (sign flip). Worth pre-registering as a hypothesis with regime-conditioning (only trade clusters when 50-day trend is flat).

**Idea C2 — BTC/ETH ratio reversion** [THIN] (`qwen3:14b`)
- **Signal:** Long BTC vs ETH when the BTC/ETH price ratio crosses far below its 20-day MA.
- **Data:** Binance spot BTC + ETH, daily.
- **Causal mechanism:** Claimed capital rotation between the two majors. Plausible but the model gave no quantified dislocation threshold and the ratio itself trends for long stretches — likely a sign-flip casualty. Lower priority than C1.

### EQUITY

**Idea E1 — Liquidity-shock reversion on small-caps** [SUBSTANTIVE] (`qwen3.5:9b`, similar from `qwen3:14b` and `deepseek-r1`)
- **Signal:** In the Russell-2000 universe, enter the bar after a session with relative volume > 3x the 10-day average and a weak close (close < open). Fade the panic.
- **Data:** yfinance OHLCV for small-cap constituents, daily.
- **Causal mechanism:** Small-caps have thin institutional float and slow institutional capital deployment; a forced-liquidation / retail-panic volume spike overshoots fair value because there is no fast institutional bid to absorb it. The reversion is the lagged arrival of that institutional bid. The mechanism is a structural liquidity constraint (small-cap float depth), not a regime call.
- **Harness note:** Distinct from PEAD (no earnings event required — it is a pure volume-shock filter). Concern: the EQUITY clean ledger is only n=33; this idea is only testable if the scanner aperture is widened (see cross-check section). Pre-register before any backtest per M-107.

### FOREX

**Verdict: No retail edge — matches the macro verdict.** [SUBSTANTIVE — as a negative result]
- `qwen3.5:9b` explicitly returned **"No Retail Edge"** for FOREX, reasoning that a >30 bps gross edge is unrealistic at daily-bar resolution given how noisy FX dailies are and how tight major-pair spreads make any small statistical reversion. This is the honest answer and converges with `reports/MACRO_WHY_NO_EDGE_2026-05-18.md` and the FOREX PF 0.27 live number.
- Every *positive* FOREX idea from the local models was a killed family (carry trade — `llama3.1`, `phi3.5`) or a VIX-correlation overlay (`qwen3:14b`) with no quantified edge. **Nothing harvestable.**
- Action: do not spend harness budget on a FOREX hypothesis. Treat FOREX as paper-only / scope-cut candidate.

### COMMODITY

**Idea CM1 — Agricultural seasonality (harvest-cycle reversion)** [THIN-to-SUBSTANTIVE] (`qwen3.5:9b`, `mistral-nemo`)
- **Signal:** Long grain futures (corn/wheat) when price is near a multi-year seasonal low AND volume is rising into the planting/harvest window.
- **Data:** yfinance / CME public futures OHLCV, daily.
- **Causal mechanism:** Agricultural commodities have a genuine physical seasonal supply cycle — harvest gluts depress price, pre-planting scarcity lifts it — and this cycle is calendar-anchored, so the effect-size *sign* is stable across years (it does not flip with macro regime, unlike momentum). That calendar-anchoring is exactly the property the harness rewards.
- **Harness note:** This is the single most structurally defensible commodity idea harvested — seasonality is causally real and sign-stable. BUT: it is well-known and may already be arbitraged down below the 30 bps hurdle; and per-window pick count (>=80) is hard to hit with a once-a-year calendar window. Pre-register and test honestly; modest expectations.

### FUTURES

**No substantive non-killed idea harvested.** The local models defaulted to roll-yield/contango (`phi3.5`, `deepseek-r1` — both **killed**), open-interest momentum (`qwen3:14b`, `mistral-nemo` — COT-adjacent, weak), or a VIX-regime overlay (`qwen3.5:9b` — generic, no quantified edge). FUTURES clean n=12 makes this moot anyway. **Nothing harvestable; scope-cut candidate.**

### BOND

**Verdict: No retail edge.** [SUBSTANTIVE — as a negative result]
- `qwen3.5:9b` and `qwen3:14b` both independently concluded BOND has **no retail edge** at daily-bar free-data resolution — low volatility means daily noise swamps any sub-30 bps signal, and the only mechanisms the models could name (yield-curve, flight-to-safety) are either killed families or unquantified.
- This converges with the macro verdict. **Nothing harvestable.** Scope-cut candidate.

### ETF

**Idea ET1 — ETF premium/discount-to-NAV reversion** [THIN] (`qwen3.5:9b`, `qwen3:14b`, `deepseek-r1`)
- **Signal:** When a liquid ETF trades at a measurable premium/discount to its NAV (or to a same-exposure twin ETF, e.g. SPY vs IVV) AND volume is below its 10-day average, fade the dislocation toward parity.
- **Data:** yfinance ETF price + published NAV (or twin-ETF price), daily.
- **Causal mechanism:** The authorized-participant create/redeem arbitrage normally pins ETF price to NAV; in low-liquidity windows the AP arb is slower/less aggressive, so small dislocations persist a day or two before being closed. The edge is the lag in the AP correction.
- **Harness note:** Causally real but the dislocation on *liquid* ETFs is tiny (basis points) — almost certainly below the 30 bps round-trip hurdle for SPY/QQQ/VTI. Would only have a chance on *less liquid* ETFs where the dislocation is bigger, which reintroduces cost/slippage. **Low priority; likely a 30 bps casualty.** Listed for completeness, not recommended for the first harness slot.

---

## 4. Cross-check: do local-model ideas converge with the cloud-swarm / macro verdict?

**Yes, strongly, on the negative side.** The most reliable local-model signal is not the positive ideas — it is the *honest "no edge"* answers:

- `qwen3.5:9b` independently returned **"No Retail Edge" for FOREX and BOND**, with cost-hurdle reasoning, before seeing any of this repo's reports. That converges with `reports/MACRO_WHY_NO_EDGE_2026-05-18.md`, `project_edge_verdict_2026_05_18.md`, and the live FOREX PF 0.27 / sub-floor numbers.
- Every model that engaged with the 30 bps round-trip cost (`qwen3.5:9b` most explicitly) concluded that daily-bar free-data strategies *generally* produce 5-10 bps gross — i.e. below the cost hurdle — which is exactly the macro root cause ("free-data + daily-bar signal space is empirically empty").
- This supports the existing **paper-only / fix-data-first** posture. None of the local models produced an idea that would change the verdict; at best they offer 3-4 seeds (C1, E1, CM1) worth *pre-registering as hypotheses* — they do NOT constitute discovered edge.

**Where local models did NOT help:** they cannot evaluate the architecture-specific questions (widening scanner aperture, meta-labeling, intraday resolution, the harness design itself). Their context is too small and they have no access to the ledger. Those questions are the cloud swarm's lane.

---

## 5. Bottom line

- **6/6 local models ran and responded.** Only the two Qwen models contributed substantively; the 3.8B-12B Mistral/Llama/Phi models largely recycled killed families and are not trustworthy for this task.
- **Top idea per class (harvestable seeds only):**
  - CRYPTO — **C1 volatility-cluster mean reversion** (Binance OHLCV; microstructural liquidity-exhaustion mechanism). Best of the harvest.
  - EQUITY — **E1 small-cap liquidity-shock reversion** (yfinance; thin-float overshoot mechanism). Needs wider aperture to be testable.
  - COMMODITY — **CM1 agricultural harvest seasonality** (CME/yfinance; calendar-anchored, sign-stable). Most structurally defensible but possibly already arbitraged.
  - ETF — **ET1 NAV-dislocation reversion** (thin; likely a 30 bps casualty).
  - FOREX, FUTURES, BOND — **no harvestable idea; local models concur with the no-edge verdict.** Scope-cut candidates.
- **Honest quality call:** local models are weak idea-generators here. Their highest-value output was *agreeing the edge space is mostly empty* and being honest about it for FOREX/BOND. The 3 positive seeds (C1/E1/CM1) are worth pre-registering as harness hypotheses per rule M-107 — but they are seeds, not edge. Nothing here overturns the paper-only, fix-data-first conclusion.
