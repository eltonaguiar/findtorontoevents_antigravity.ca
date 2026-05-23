# Roadmap to a Money-Ready System — 2026-05-18

Revised roadmap, swarm-reviewed (Grok / xAI + DeepSeek). Supersedes the
external-AI draft `ROADMAP_TO_PROFIT.md` (which was never committed — local-only).

## 1. Honest verdict (read this first)

After **8 straight walk-forward harness kills**, the canonical policy-clean
ledger (`audit_dashboard/data/pf_registry.json`, gen 2026-05-18) shows **no
asset class with a real edge**:

| class | n (clean) | PF | verdict |
|-------|-----------|-----|---------|
| EQUITY | 33 | 0.60 | no edge |
| COMMODITY | 173 | 1.11 | sub-floor |
| CRYPTO | 6,353 | 0.88 | sub-floor |
| FOREX | — | outlier-fake | single-pair artifact |
| FUTURES | 127 | 0.11 | catastrophic |

Two independent AI reviewers put the probability of building **hedge-fund-grade
edge per asset class on shared hosting + free APIs** at **5–8%**. The honest
default posture: **this is a research sandbox, not a money-ready system.** Real
capital stays at $0 until the harness passes something. That is not failure —
8 kills before real money is the system working.

The roadmap below is the **5–8% path** — pursued honestly, with the dashboard
telling the truth while it runs.

## 2. Why the external-AI roadmap was wrong

The draft `ROADMAP_TO_PROFIT.md` said: "ingest genuinely new data (options flow,
on-chain, 13F, FRED) → harness-gate → money-ready." Both reviewers independently
called this **"the 8th version of the same overfitting trap with fancier
inputs."** New inputs into the same single-signal-hunt + same harness produce
8 more kills. Also: its `-$8.9M / -1056%` portfolio figure is a **raw-ledger +
pnl_pct unit-mismatch artifact** — not canonical. Do not cite it.

## 3. What actually has to change (swarm consensus)

1. **Causal hypothesis BEFORE data.** For every signal write the economic
   mechanism first ("dealer gamma flips sign when VIX>20 because hedging
   pressure reverses"), then test only that hypothesis. No data-dredging.
2. **Regime-conditional admissibility.** The current harness tests only
   sign-stability across 5 windows — it **kills regime-dependent edges**, which
   is most real edge. Add a regime-stratified mode: a signal may be admissible
   *within* a regime even if it flips across regimes.
3. **Ensemble, not single-signal hunts.** Top funds run hundreds of weak,
   partially-correlated signals with Bayesian shrinkage + portfolio
   optimization. Stop hunting one hero signal per class.
4. **Risk model as a first-class gate.** Signals are tested in isolation today,
   then fail in multi-asset context (cross-asset hedging, correlation,
   liquidity). Model portfolio risk before admitting any signal.
5. **Fix the upstream data loss.** 14,705 raw rows → 2,445 clean = 83% dropped
   (4,830 duplicate re-emissions + 4,763 policy-excluded). The duplicate
   re-emission bug must be fixed at the writer, not papered over downstream.

## 4. This week (highest-leverage — both reviewers agree)

**Make the dashboard tell the truth.** `/audit` "Smart Picks" / "High
Conviction" / "Money Ready" tabs imply an edge that does not exist.

- "Money Ready" → shows the honest empty state: *"No admissible edge — 0/8
  signal families passed walk-forward. Paper-only research sandbox."*
- Every pick tile carries a harness-verdict badge: RESEARCH / WATCHED /
  ADMISSIBLE / MONEY-READY.
- Default the per-class tiles to the canonical `pf_registry.json` source
  (already tracked: **issue #1221**).

This is a `dashboard_generator.py` + `template.html` change — peer-hot
(codebuff lane). Coordinate; do not blind-edit.

## 5. Per-asset-class plan

- **CRYPTO — the one real bet.** Both reviewers independently picked crypto and
  near-identical signals: **exchange net-flow + stablecoin-velocity divergence,
  regime-filtered.** This is already in flight — peer STRAND B
  (`tools/onchain_crypto_research.py`, branch `feat/strand-b-onchain`). The
  external AI's local `alpha_engine/onchain_crypto.py` **duplicates this** —
  coordinate, do not double-build. Harness + cost gate as always.
- **EQUITY / FOREX / FUTURES / BOND** — paper-only. No real capital. Re-test
  only when (a) the regime-conditional harness ships and (b) a causal
  hypothesis is pre-registered. FOREX/FUTURES stay hard-disabled.
- **COMMODITY** — the prior "best" (cot_positioning) was COT look-ahead leakage
  (M-095 block). PF 1.11 clean is not an edge. Paper-only.

## 6. Phases & gates

| phase | window | exit gate |
|-------|--------|-----------|
| 0 — honesty | this week | dashboard shows true state; #1221 closed |
| 1 — harness upgrade | 2–3 wk | regime-conditional admissibility mode shipped + tested |
| 2 — one causal hypothesis | 3–6 wk | CRYPTO net-flow signal pre-registered, harness-run; honest kill-or-pass |
| 3 — ensemble + risk | only if Phase 2 passes | ≥2 admissible signals combined w/ portfolio construction |
| 4 — money-ready | only if Phase 3 holds OOS | ≥10 fwd trades, WR≥50%, PF≥1.3, net-of-cost |

If Phase 2 kills (9th kill), that is the decision point: **declare paper-only,
stop the real-money hunt.** Honest given 8 priors.

## 7. What NOT to do

- Do not commit the external AI's local `options_flow.py` / `onchain_crypto.py`
  to main unreviewed — unverified, and `onchain_crypto.py` collides with peer
  STRAND B.
- Do not promote any class to "money-ready" on dashboard-tile numbers — those
  are inflated (un-deduped). Canonical = `pf_registry.json` only.
- Do not rebuild banned families (funding-rate directional, yield-curve,
  F&G/RSI, COT). Grok's suggested crypto signal includes a funding-rate filter —
  a *regime filter* is allowed; a funding-rate *directional predictor* is not.

---

*Swarm run: `swarm_runs/roadmap-edge-2026-05-18/` (Grok grok-4.3 + DeepSeek).
Canonical data: `audit_dashboard/data/pf_registry.json`. Prior: 8 harness kills,
`reports/EDGE_VERDICT_2026-05-18.md`, `reports/EQUITY_VERDICT_FINAL_2026-05-18.md`.*
