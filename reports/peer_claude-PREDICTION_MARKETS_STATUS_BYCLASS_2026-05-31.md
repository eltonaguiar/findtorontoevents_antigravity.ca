# Prediction-Market Status by Asset Class — 2026-05-31

**Author:** peer_claude
**Scope:** Kalshi + Polymarket scrapers/signals/picks across CRYPTO / EQUITY / FOREX / COMMODITY / ETF / BOND
**Mode:** READ-ONLY (live `ejaguiar1_stocks.trading_picks` + filesystem + `gh`)

---

## TL;DR

- **Polymarket upstream = ALIVE & HEALTHY.** Multiple workflows green within last 30 min (`polymarket-signals.yml`, `prediction-market-agents.yml`, `sports-prediction-market-sync.yml`). 2,404 CRYPTO picks emitted in last 30d; 271 `prediction_market_consensus` rows post the retire-decision (PR #182, 2026-05-31 05:47 UTC).
- **Kalshi upstream = NEARLY DEAD as a trade-signal feed.** Modules exist (`alpha_engine/kalshi_signals.py`, `predictions/scrapers/kalshi_scraper.py`, `prediction_market_agents/kalshi_signal_agent.py`, `tools/kalshi_sports_fetch.py`), but only **4 rows ever** in `trading_picks` with `kalshi` in strategy/source, last at **2026-03-28** — 64 days stale. Snapshots dir `data/kalshi_snapshots/` has 1 file from 2026-04-26. No dedicated `kalshi-*.yml` workflow; only referenced inside polymarket/alpha-engine/social-prediction workflows.
- **Retire decision (PR #182) = CORRECT on data-integrity grounds, but it threw out an alive feed.** The headline PF 24.5 / WR 90% on `prediction_market_consensus` was a resolver artifact (PR #180 forensic: DOGE SHORTs tagged `SL_HIT_RESOLVED [PRICE_MISMATCH]` with POSITIVE pnl; XRP row `SL_HIT (REPAIRED_PNL_CONTRADIC)` worth +80.37%). My own confirming probe: TP_HIT avg time-to-close is **negative 3,849 minutes** on `prediction_market_consensus` (n=83) — exits stamped *before* entry. That's not edge, that's corruption.
- **But the upstream is fine.** Polymarket workflows are emitting; the corruption is in the **resolver/labelling stage**, not the scraper. The retire blocks the *current* mis-resolved output from polluting `money_ready_verdict.json`, which is appropriate; it does NOT mean the Polymarket feed itself has no edge.
- **Net assessment:** `kalshi_alive=False`, `polymarket_alive=True`, `scoring_broken=True` (resolver-side, not signal-side), `retire_was_correct=True` (as a stop-gap), but a follow-on PM-resolver-fix PR is needed to recover the edge instead of leaving it permanently blocked.

---

## 1. Upstream Inventory

### Polymarket
- **Modules:** `alpha_engine/polymarket_signals.py`, `polymarket_merger.py`, `polymarket_pmxt.py`, `prediction_market_whales.py`, `pm_consensus_overlay.py`, `prediction_market_consensus.py`, `prediction_market_signals.py`, `copytrader_integration.py`, `copy_trader_bridge.py`, `sports_prediction_market_sync.py`.
- **Workflows (last runs):**
  | Workflow | Last status | Last completed |
  |---|---|---|
  | `polymarket-signals.yml` | in_progress (success on previous 2 runs) | 2026-05-31T21:33Z success |
  | `prediction-market-agents.yml` | success | 2026-05-31T20:37Z |
  | `sports-prediction-market-sync.yml` | success | 2026-05-31T20:29Z |
  | `prediction-quality-tracker.yml` | queued (success on previous run) | 2026-05-31T21:08Z |
  | `alpha-verify-predictions.yml` | success | 2026-05-31T20:45Z |
- **DB output (`trading_picks`):** sources include `polymarket_whale_tracker`, `copy_trader_polymarket`, `prediction_market_agents`, `prediction_market_consensus`, `combined_confidence_strategy`. Latest emit `2026-05-31 21:40 UTC` (copy_pm). Strategies: `copy_pm_*` (clones of whale wallets), `pm_whale_*`, `prediction_market_consensus`.

### Kalshi
- **Modules:** `alpha_engine/kalshi_signals.py`, `predictions/scrapers/kalshi_scraper.py`, `prediction_market_agents/kalshi_signal_agent.py`, `tools/kalshi_sports_fetch.py`, `tools/verify_kalshi_picks.py`.
- **Workflows:** none dedicated. Referenced from `polymarket-signals.yml`, `alpha-engine-live.yml`, `audit-dashboard.yml`, `social-prediction-tracker.yml`.
- **DB output:** 4 rows total, last `2026-03-28 22:21 UTC` (64 days stale).
- **Snapshots:** `data/kalshi_snapshots/20260426T025427Z.json` (one file, 35 days stale).
- **Assessment:** code is wired but production feed has stopped emitting trades. Likely auth/cookie expiration or scraper drift. Treat as DARK upstream until verified.

---

## 2. Pick Volume by Asset Class (last 30d, all PM-related strategies/sources)

| Class | n_30d (PM-related) |
|---|---|
| CRYPTO | 2,404 |
| EQUITY | 5 |
| FOREX | 3 |
| COMMODITY | 2 |
| ETF | 0 |
| BOND | 0 |
| MEME | 0 |

**Mapping observation:** Polymarket markets are politics/macro/sports, but the consumer side (`prediction_market_consensus`, `copy_pm_*`, `pm_whale_*`) emits **crypto perpetual** picks (DOGEUSDT/BTCUSDT/XRPUSDT etc.) — i.e., the PM signal is being used as a directional overlay on crypto pairs, not directly traded on Kalshi/Polymarket. Tiny EQUITY/FOREX/COMMODITY leakage (n=5/3/2 in 30d) appears to be misclassification edges, not a real cross-class engine.

---

## 3. Resolved-Trade WR/PF (status IN ('TP_HIT','SL_HIT','WON','LOST'))

```
strategy                           source                            n   wins  losses  WR%   PF
prediction_market_consensus        prediction_market_agents          72  64    8       88.9  44.81
prediction_market_consensus        prediction_market_consensus       20  17    3       85.0   6.63
```
Per class (resolved):
```
crypto   n=96  WR=86.5%  PF=24.51
forex    n=3   WR=66.7%  PF=3.33
```
**These numbers are the same suspect-PF flagged in PR #180 / #182.** My corruption probe confirmed it:

| status | n | avg minutes from `created_at` → `closed_at` |
|---|---|---|
| TP_HIT | 83 | **-3,849** (NEGATIVE — exits stamped before entry) |
| LOST | 10 | 241 |
| SL_HIT | 3 | 98 |

Resolver is back-dating TP_HIT exits. Headline 88.9% WR / PF 44.81 is **not real**.

**`copy_pm_*` and `pm_whale_*` resolved sample = 0.** All sit in `ACTIVE`/`TIME_EXIT`/`OPEN`. We cannot judge their edge yet — they need a *correct* resolver run.

---

## 4. Status Distribution (all PM-related rows)

```
LOST       171   avg pnl -3.72%
TP_HIT     248   avg pnl +5.85%
OPEN       667
TIME_EXIT  5,033
ACTIVE     1,789
EXPIRED    27
SL_HIT     3
```
**~63% of all PM-related rows are `TIME_EXIT`** with avg pnl ≈ 0.000 — these are auto-closed at horizon with no real exit logic. This bloats n and masks any genuine edge.

---

## 5. Why PR #182 Retired `prediction_market_consensus`

PR #182 (merged 2026-05-31 05:47 UTC) added `cta_golden_cross_200` and `prediction_market_consensus` to `BLOCKED_SOURCE_SYSTEMS` (`audit_trail/quality_gates.py:2015`). Evidence from PR #180:
1. 23 DOGEUSDT SHORT rows tagged `SL_HIT_RESOLVED [PRICE_MISMATCH]` with **positive** pnl_pct (exit_reason / pnl-sign contradiction).
2. One XRPUSDT row literally tagged `SL_HIT (REPAIRED_PNL_CONTRADIC)` worth +80.37%.
3. My probe confirms negative time-to-close — resolver is corrupting timestamps too.

**The retire was correct as a stop-the-bleeding move:** it prevents the inflated PF from propagating into `money_ready_verdict.json` and the Smart Picks gate. But:
- The polymarket upstream is **still emitting** (2,404 picks in 30d, last 21:40 UTC today). PR #182 just blocks them at Layer-1 policy filter; rows continue to write to `trading_picks`.
- We have **no clean read** on whether Polymarket consensus actually has edge — the resolver corruption masks it.

---

## 6. Recommended Follow-Ons (NOT executed in this pass — read-only)

| # | Action | Owner suggestion | Priority |
|---|---|---|---|
| F1 | Open `INCIDENT_PM_RESOLVER` — fix the resolver corruption (negative time-to-close, PRICE_MISMATCH bypass, REPAIRED_PNL_CONTRADIC class). Until fixed, ALL PF on PM strategies is untrustworthy. | resolver owner | **P0** |
| F2 | Resolve the 1,789 ACTIVE + 667 OPEN `copy_pm_*` / `pm_whale_*` rows correctly using intrabar OHLC, then re-measure WR/PF on a clean cohort. Goal: decide if copy-trade-Polymarket-whales has real edge on CRYPTO. | resolver + portfolio | **P0** |
| F3 | Kalshi feed revival: scraper has not emitted a tradeable pick in 64 days. Either repair `predictions/scrapers/kalshi_scraper.py` + add a dedicated `.github/workflows/kalshi-signals.yml` cron, OR officially deprecate `alpha_engine/kalshi_signals.py` and the 4 callsites. Current state (code present, zero output) is the worst of both. | data/scrapers | P1 |
| F4 | Wire-Up Rule check: `pm_consensus_overlay.py`, `polymarket_merger.py`, `polymarket_pmxt.py` — verify each is reached from the production pick path. Lots of PM modules; only `prediction_market_consensus` and `copy_pm_*` actually surface in `trading_picks`. | rule M-Wire-Up | P2 |
| F5 | Once F1+F2 land, re-evaluate the retire: if clean resolver still shows PF>1.5 on n>=100 closed, **unblock** in `BLOCKED_SOURCE_SYSTEMS`; if not, escalate to `PERMANENTLY_KILLED_STRATEGIES`. | money-ready owner | P1 |

---

## 7. Direct Answers to the Brief

- **Are the upstream Kalshi/Polymarket scrapers still running?**
  - Polymarket: **Yes**, multiple workflows green within 30 min, 2,404 CRYPTO picks last 30d.
  - Kalshi: **No tradeable output for 64 days**. Modules wired, scraper dark.

- **Are they producing useful signals that just weren't being scored well?**
  - Polymarket: **Likely yes, but unverifiable** under current resolver. The resolver corrupts exit timestamps and pnl signs, so PF 24.5 / WR 90% is fake — but `copy_pm_*` (n=1,789 ACTIVE) and `pm_whale_*` have NEVER been cleanly resolved. We don't know the true edge.
  - Kalshi: cannot evaluate, no fresh picks.

- **Was the retire correct?** **Yes, defensively** (stop the fake PF from polluting money_ready). **No, strategically** if there's real edge buried under the resolver bug — fixing the resolver should come before any permanent kill.

---

## Appendix — Sources

- `audit_trail/quality_gates.py:2010-2018, 3714-3718, 5771-5773, 9970-9985`
- `reports/peer_claude-phase4-suspect-pf-audit_result_2026-05-31.md` (referenced by PR #180)
- PR #180 merged `2026-05-31T05:47Z` — Phase-4 SUSPECT-PF audit
- PR #182 merged `2026-05-31T05:47Z` — Phase-5 retire
- GH workflow API: `polymarket-signals.yml`, `prediction-market-agents.yml`, `sports-prediction-market-sync.yml`, `prediction-quality-tracker.yml`, `alpha-verify-predictions.yml`
- Live DB: `ejaguiar1_stocks.trading_picks` (READ-ONLY, queried 2026-05-31 ~22:15 UTC)
