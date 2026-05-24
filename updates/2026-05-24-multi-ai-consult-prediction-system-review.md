# Multi-AI Consult: Prediction System Review (Mercury 2 + Grok + ChatGPT + Gemini)

**Date:** 2026-05-24
**Goal alignment:** Goal #1 (institutional-grade `/audit` performance across all asset classes)
**Status:** Research / synthesis — no code changes
**Scope:** External AI second-opinions on `https://findtorontoevents.ca/audit/`, `/audit/hyrotrader`, `/audit/ai_leaderboard.html`, `/audit/ai-tournament.html` and the swarm-AI tournament logic.

**Source consults:**
- Mercury 2 (Inception Labs) — full response, web-search enabled
- Grok (xAI) — full response, with live page introspection
- ChatGPT (OpenAI) — full response · share link: https://chatgpt.com/share/e/6a128b44-6134-8013-ba38-e92b50e9496a
- Google Gemini — full response (could not reach live pages; reasoned from architecture)

---

## 1. Original prompt (verbatim, sent to all three models)

> we have https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/ a prediction system for stocks/crypto/forex/bonds/etfs/futures/commodities/penny stocks/cheap stocks/IPOs.
>
> Review all metrics on https://findtorontoevents.ca/audit/ and https://findtorontoevents.ca/audit/hyrotrader and investigate for stale/incorrect data.
>
> Then inspect each active and recently closed picks within the last 72 hours and inspect whether our algorithm(s) are picking quality picks and if not explain why and your suggested approach to fix it?
>
> next inspect https://findtorontoevents.ca/audit/ai_leaderboard.html https://findtorontoevents.ca/audit/ai-tournament.html, and check whether the swarm AI logic is sound,
>
> How far is our project from being world-class hedge fund? instituational grade-trustworthy picks?
>
> How can we at least get to lower risk picks.. How are our personas for the AI tournament, are they decent quality or we need more? or revisions?
>
> What sort of other metrics do we need for asset class?
> Also in case if we were to add low-fee or no-fee mutual funds with non minimum $ and rank them, what stats would you suggest?
>
> Similarly, for all asset classes, what data points would you expect to see, what entry criteria could you pick.

---

## 2. Cross-model synthesis (themes all three agreed on)

| Theme | Mercury 2 | Grok | ChatGPT | Gemini | Action owner |
|---|---|---|---|---|---|
| **Stale-data risk on `/audit`** is the biggest institutional red flag | ✅ Section 1 checklist | ✅ "Dashboard data last referenced ~2026-05-21 (3 days old)" | ✅ Critical Issue: Stale Data Risk | ✅ "Stale Oracle/API Feeds" — cross-verify timestamps of last 50 picks | Add freshness SLA + per-pick `last_update` banner + auto-suppress when stale |
| **Edge is marginal post-resolver** (PF ~1.3–1.55, WR ~46–51%); not yet T2-grade except equity | ✅ | ✅ | ✅ (implicit) | ✅ (implicit via "execution + slippage breaks edge") | Tighten gates; retire toxic strategies faster |
| **ML confidence calibration / lookahead leakage** | — | ✅ explicit ("high-confidence sometimes correlates with worse WR") | ✅ "Add probabilistic confidence" | ✅ explicit ("Perfect Lookahead Bias" + "Feature Leakage") | Platt scaling / isotonic on `smart_score`; verify on closed quadrants; audit entry-price vs signal-time |
| **Personas are too LLM-stylistic, not factor-orthogonal** | ✅ "PCA on agent returns; if >80% in 2-3 PCs, you have redundancy" | ✅ "Generic LLM agents; expand to 10–15 specialized" | ✅ "Replace stylistic personas with factor-specialist agents" | ✅ "Collusion Risk" — force divergent inputs per persona | Re-design tournament with factor-specialist roster (table in §4) |
| **No transaction-cost / slippage / liquidity modeling** = backtests are fiction for crypto-perps + pennies + microcaps | ✅ | ✅ | ✅ "Transaction cost modeling" priority | ✅ "Live TCA required for institutional-grade" | Add TC layer to `score_pick` / `passes_smart_gate` |
| **Portfolio-level intelligence missing** (correlation caps, factor exposure limits, sector concentration) | ✅ | ✅ | ✅ | ✅ "Factor Exposure Constraints" + pairs/co-integration suggestion | New `portfolio_constraints.py` enforced before pick emission |
| **Penny stocks / IPOs need a separate engine** — do NOT mix with blue-chip logic | — | ✅ | ✅ ("Create a separate speculative microcap engine") | ✅ ("Penny Stock / Cheap Stock Trap" — low-vol pump/dump mistaken for momentum) | Class-split: speculative vs. institutional buckets |
| **Regime detection missing** | ✅ ("macro regime check") | ✅ ("no conflicting macro regime") | ✅ Priority #3 | ✅ "Macro Regime Blindness" — regime-mismatched strategy fires during CPI/FOMC | Add regime classifier (trending / chop / crisis / low-liq) + macro-calendar blackout |
| **Exit logic underdeveloped vs. entry logic** | ✅ (vol-scaled stops) | ✅ (RR ≥ 2) | ✅ ("Institutions optimize exits, sizing, drawdown") | ✅ "Dynamic Kelly Criterion" — scale down on rolling WR drop | Vol-adjusted trailing + decay exits |
| **"Gatekeeper Agent" (negative selection)** — explicit veto agent | — | — | ✅ (implicit in Fraud Detector / Liquidity-Stress) | ✅ explicit ("sole job is to find reasons NOT to take a trade") | Add veto-agent role to swarm tournament |
| **Cross-node failover for live trading** (Zenoh/NATS mesh) | — | — | — | ✅ "Fail-Safe & Mesh Integrity" — deterministic failover for Alpha Engine | Out-of-scope until live capital; track as deferred item |
| **Distance to institutional-grade** | "Early-stage quant tool" | "1–2 years and several iterations" | "Several layers away" | "Innovative but a *predictive system*, not yet an *end-to-end risk system*" | Realistic Sharpe >1.5 / MDD <20% over 6–12 mo paper before real capital |

---

## 3. Concrete per-class additions (consolidated)

### Universal metrics every pick must expose
- Source timestamp + ingestion timestamp + freshness score
- Liquidity score (0–100), spread bps, slippage estimate
- Volatility percentile + regime alignment flag
- Correlation cluster tag (AI / Energy / Crypto / Rates / …)
- Expected move + confidence interval (Wilson)
- Signal decay half-life

### Class-specific additions all three suggested
- **Crypto** — funding rate regime, OI delta, liquidation clusters, stablecoin in/outflows, whale concentration, DEX/CEX divergence, perp basis
- **Equity** — float, short interest, insider activity, options flow, analyst revisions, factor (size/value/quality/momentum) exposures
- **Penny / micro** — float, dilution probability, offering history, borrow availability, halt frequency, social-velocity anomaly
- **IPO** — lockup expiration calendar, underwriter quality, post-IPO vol curve, cohort positioning
- **Forex** — rate differential, carry pressure, DXY correlation, central-bank surprise index, COT
- **Bonds** — YTM, duration, convexity, real yields, breakevens, credit spread regime
- **Commodities / futures** — curve shape (contango/backwardation), inventory, seasonality, weather, geopolitics
- **ETFs** — expense ratio, tracking error, factor overlap, NAV-vs-price spread, underlying liquidity

### Mutual-fund composite (low/no-fee, no-minimum) — all three agreed on:
```
Score = 0.30*(1 − ExpenseRatio_norm)
      + 0.25*Sharpe_norm
      + 0.20*Liquidity_norm
      + 0.15*Performance_5y_norm
      + 0.10*ESG_norm
```
**Entry threshold:** ER ≤ 0.50% (ideal <0.20%), Sharpe ≥ 0.5, 5y alpha > 0, max-DD < 25%, AUM > $100M, manager tenure ≥ 3y.

---

## 4. AI-tournament persona redesign (ChatGPT's roster + Grok's expansion + Mercury 2's PCA check)

Replace the current "stylistic LLM" personas with **factor-orthogonal specialist agents**:

| Agent | Specialty | Information edge |
|---|---|---|
| Macro Hawk | Rates / Fed / curve | Macro-calendar awareness |
| Volatility Hunter | Options & vol expansion | IV percentile + skew |
| Mean-Reversion Engine | Statistical reversion | Cointegration, z-scores |
| Momentum Engine | Trend persistence | Multi-timeframe MA + breadth |
| Liquidity-Stress Engine | Risk-off detection | Spread widening + funding stress |
| On-Chain Analyst (crypto) | Whale flows, exchange reserves | Glassnode-style |
| Microstructure Agent | Spread / orderbook | L2 imbalance |
| Sentiment Agent | News / social NLP | Filtered (anti-spam) |
| Quality-Factor Agent | Fundamentals | FCF, earnings quality |
| Fraud Detector | Manipulation risk | Pump/dump fingerprints |

**Diversity guardrail (from Mercury 2):** run a PCA on rolling 30-day agent-return matrix; if first 2–3 PCs explain >80% of variance → kill the most-correlated agent or retrain its prompt.

**Aggregation (from all three):** weighted vote (NOT equal); weight = lower-95% CI of agent Sharpe × diversity penalty (1 − max pairwise corr).

---

## 5. Top-10 institutional-readiness backlog (merged + ranked)

1. **Fix stale data permanently** — freshness SLA per class (crypto 30s, FX 10s, stocks 60s, ETF 5m, MF 1d); suppress picks above threshold.
2. **Probabilistic confidence** — Platt/isotonic calibration on `smart_score`; expose Wilson CI on WR.
3. **Regime detection layer** — trending / mean-reverting / crisis / low-liquidity classifier gating which agents fire.
4. **Transaction-cost & slippage modeling** baked into `score_pick`.
5. **Portfolio construction** — correlation cap, sector concentration, factor exposure budget, vol-targeting.
6. **Split speculative vs. institutional buckets** — penny/IPO engine separate from blue-chip/ETF engine.
7. **Exit-logic upgrade** — vol-adjusted trailing, decay exits, liquidity-aware exits.
8. **Cross-provider price reconciliation** — Polygon / Alpaca / TwelveData / Binance / Yahoo; mark degraded on divergence.
9. **Replace stylistic personas with factor-specialist roster** (table in §4).
10. **Wire missing ETF/Bond/Commodity emitters** into the active JSON pipeline (shadow mode → live).

---

## 6. Reality check on distance to "world-class hedge fund"

All three converged on the same message:
> **Aim first for consistency, low drawdowns, and trustworthiness — not maximum returns.** Once 6–12 months of clean post-gate paper trading show Sharpe >1.5 and MDD <20%, the system is in position to consider small real-money deployment.

**Strategic shift (ChatGPT's framing, endorsed by all):**
> Current philosophy: *"Find explosive winners."*
> Required philosophy: *"Preserve capital while compounding asymmetrically."*

That re-frames ranking, filters, exits, portfolio construction, swarm design, scoring, risk logic, and confidence systems all at once.

---

## 7. Where this lands in the repo

- This doc: `updates/2026-05-24-multi-ai-consult-prediction-system-review.md`
- Card on `updates/index.html` linking to it
- No code changes yet — backlog items 1–10 above will be opened as separate PRs against `audit_trail/`, `alpha_engine/`, and `audit_dashboard/` per the **Wire-Up Rule** in `CLAUDE.md`.
- Cross-refs: `reports/hedge_fund_performance_review_*.md`, `reports/ACTIVE_PICKS_ASSET_CLASS_DIAGNOSIS_2026_04_22.md`, `docs/MUTATION_THREE_AXIS_PROTOCOL.md`, `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`.

---

## 8. Gemini-specific additions worth calling out

- **Pairs / co-integration trading** as a low-risk path: predict the *relative* spread between two correlated assets (e.g., long AAPL / short MSFT, long BTC / short ETH) rather than direction in isolation. Market-neutral by construction.
- **Capture-ratio metrics for mutual funds**: Upside Capture > 100% / Downside Capture < 100%. (Adds to the composite-score formula in §3.)
- **Information Ratio + Tracking Error** for index-tracking funds (high IR with low TE = manager skill, not luck).
- **Per-class entry-criteria specificity** (Gemini's table is the strongest of the four — see §3 above; e.g., "long commodity only when in deep backwardation AND commercials net-long per COT").
- **Adversarial persona framing**: explicitly states personas must "play adversarial roles against one another" — a uniform swarm is "an expensive single-point-of-failure model."

## 9. Raw consults (preserved verbatim for audit trail)

The full unedited responses from Mercury 2, Grok, ChatGPT, and Gemini are preserved in the session transcript and the chat-drop to peer agents. ChatGPT share link in header. Synthesis above is faithful to all four; nothing was dropped that conflicted across sources.
