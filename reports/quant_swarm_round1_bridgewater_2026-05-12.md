# Quant Swarm Round 1 — Bridgewater Lens — 2026-05-12

> Channel: Dalio / Bridgewater Associates. All Weather, risk parity,
> macro regime quadrants, principle-driven > data-mined.
> Corpus: n=55,510 raw, WR 11.13%, PF 0.46, ~69% zero-PnL artifact.
> Filtered live view: CRYPTO PF 1.36, COMMODITY PF 2.08, FOREX PF 0.29.
> Week-1 rescue (truth-layer banner, zero-PnL filter, ML mtime gate) shipped.

## Principle first

Numbers no mean nothing without **environment**. Bridgewater frame = four
boxes: growth up/down × inflation up/down. Each box favor different asset.
Holy grail = 15 uncorrelated return streams across boxes, risk-balanced,
NOT 23 negative-return strats stacked on one CRYPTO bet. Current portfolio
is anti-All-Weather: concentrated CRYPTO (92% of n), zero box-diversification,
single regime detector (BTC 24h %). That is the disease, not the symptom.

## 1. Per-class verdict via macro quadrant

| Class | Filtered PF | Bridgewater box | Verdict |
|---|---|---|---|
| CRYPTO | 1.36 | Risk-on / growth-up (proxy NDX β=0.6) | **KEEP, shrink concentration**. Strip `alpha_engine_fast` PF 0.62 + `kimi_signal_tracking` PF 0.26 — those are dead weight in any regime. |
| COMMODITY | 2.08 (n=750) | Inflation-up / growth-up — Bridgewater's strongest historical box | **KEEP, scale carefully**. This is the natural inflation hedge leg of All Weather. PF 2.08 not noise; commodity trend-following has 40yr academic edge (Hurst/Ooi/Pedersen). |
| BOND | 1.72 (n=18) | Growth-down / inflation-down — flight-to-quality | **REBUILD with patience**. n=18 << charter 100; PF real but unproven. Bond is structurally the deflation hedge — we cannot ship All Weather without it. Source: PIMCO/AGG trend-following replication. |
| EQUITY | 1.41 (n=421) | Growth-up — risk-on core | **KEEP**. Lowest-risk lift candidate; n=421 stable. |
| FOREX | 0.29 (n=1343) | **Cross-quadrant** — DXY is the regime *meta-signal*, not its own bet | **REBUILD SHORT-only**. Per deep-dive, SHORT side 36pp edge over LONG. FX is information layer, not P&L layer until rehab Step C clears. |
| FUTURES | sub-floor | Inflation-up / trend-following | **REBUILD via CTA TSMOM**. DBMF/KMLM replication is the canonical fix. |
| ETF | 1.24 (n=87) | Multi-quadrant | **KEEP**, n→100. |
| MEMECOIN / PENNY | negative | No box — pure beta junk | **KILL** as systematic strats. Tactical only. |

## 2. Hidden-insight queries (run these)

a. Per-class score-vs-PnL ρ split by **VIX quartile** — Performance Reality
   memo says trust_score ρ=+0.196 system-wide; suspect it inverts in
   high-VIX (>25) quartile because risk-on scores predict mean-reversion losses.
b. **Dormant strats x regime**: any strat with zero-fills last 14d crossed
   against BTC-bullish/bearish flag. `forex_carry_momentum` blocked since
   USD-rate cut cycle started — that strat lives in growth-up/inflation-up
   box and is being judged in wrong regime.
c. Zero-PnL distribution by **hour-of-day** (Asian session vs London/NY).
   38k zero-PnL = 69% — bet most are off-session prints, regime-irrelevant.

## 3. Macro-regime conditioning

Current detector (`regime_flip_detector.py`) is **inadequate** for
Bridgewater frame:
- Only BTC 24h % → 3 states (BULLISH/BEARISH/CHOPPY).
- No DXY input despite FOREX deep-dive citing DXY cross-check.
- No VIX, no growth/inflation breakouts (10y-2y curve, breakevens, copper/gold).
- HMM exists (`hmm_regime.json`, `bayesian_regime_reference.py`) but is **not
  wired** into emission gating per CLAUDE.md wire-up rule.

Principle-driven gating: every strat must declare its **target quadrant**
in metadata. Emission filtered by current quadrant probability. This is
Dalio's "know what environment you're in before placing bet."

## 4. ML reality — principle > data-mining

ML acc 32.6% / Brier 0.374 / precision 11.5 → model say WIN always.
That is **data-mining without principle**. Bridgewater historical view:
ML works when constrained by economic priors (cause→effect chains), not
when free-fit to noisy P&L labels. 69% of training labels are zero-PnL
artifacts — model learned the noise floor, not the edge.

**Fix:** kill free-form ML as primary signal. Use ML only as **filter** on
rule-based candidates (per `feedback_ml_reviews_consolidated.md`). Train on
**filtered post-resolver-v2 corpus** (n~10k clean), not raw 55k. Retrain
every regime flip, not every N hours.

## 5. THE ONE THING — Day 1

**Wire HMM regime states into emission gating, declare per-strat target
quadrant.** No new strat, no new ML. Take what already runs and route it
by environment. COMMODITY-trend ships only when inflation-up state fires;
CRYPTO-momentum only in growth-up risk-on; FOREX SHORT-only when DXY-trend
state fires. Single PR — `audit_trail/quality_gates.py` adds
`regime_quadrant_required` per strategy; reads `hmm_regime.json` already
on disk. Expected lift: cuts emission ~40%, lifts WR on what remains
because we stop trading the wrong leg in the wrong box.

Everything else (bond rebuild, CTA replication, ML retrain) follows from
that one wiring change. No regime, no All Weather. No All Weather,
no real money.

## NFA

Principle-driven research. Real-money sizing remains gated on the
10-step Lopez de Prado AFML pipeline regardless. Cite-evidence only.
