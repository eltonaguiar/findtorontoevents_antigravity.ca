# Edge Harvest — concrete per-class tactics — 2026-05-18

Multi-AI idea harvest on "how to actually get to safe + profitable per asset
class." Engines: xAI Grok (swarm + `grok -p` headless), DeepSeek, Groq,
ollama_cloud, pollinations. Prior consult: Grok + DeepSeek roadmap review.

## Per-class consensus

| class | signal the swarm converged on | realistic PF ceiling | verdict |
|-------|-------------------------------|----------------------|---------|
| **CRYPTO** | Order-book imbalance + exchange net-flow (CryptoQuant/Kaiko) | 1.3–1.6 | **the one retail bet** |
| EQUITY | Post-earnings-announcement drift (PEAD) — earnings surprise + first-15-min reversal | 1.1–1.3 | modest, secondary |
| COMMODITY | COT positioning / roll-yield term structure | 1.2–1.7 | mostly tapped — COT is leakage-flagged (M-095), roll-yield is H-007 REJECTED |
| FOREX | — | — | **hopeless for retail** (near-unanimous: spreads + HFT) |
| FUTURES | calendar-spread mispricing only | ~1.1 | **hopeless** — needs co-location latency |
| BOND | — | — | **hopeless** — dealer-dominated, retail data too coarse |

**Take:** stop spending effort on FOREX / FUTURES / BOND. CRYPTO is the bet;
EQUITY-PEAD is the only viable second. This matches the roadmap.

## The magic-filter question — UNANIMOUS answer

Every engine independently named the same corrupt cohort: **duplicate
re-emissions** — the same symbol/direction/size signal firing repeatedly within
seconds-to-minutes. They inflate trade count and destroy PF with repeated
losers in trending markets. This is the **4,830 dropped duplicate re-emissions**
already visible in `pf_registry.json` counts.

Secondary filter most likely to be consistently profitable if any edge exists:
**time-of-day** (first 30 min of session) combined with a **FWD-WR ≥0.55
bucket**.

## The #1 move this week (`grok -p`, decisive)

> Freeze all signal work. Surgically excise the duplicate-re-emission bug from
> the crypto tick pipeline: deterministic unique key (`exchange_ts + trade_id +
> seq` for trades; `price+qty+side+micro_ts` hash for book deltas), a zero-copy
> dedup stage immediately after the raw decoder, a 60-day backfill writing only
> the deduplicated stream to a new immutable dataset, then exact volume
> reconciliation against exchange REST trade-history endpoints (target <0.05%
> notional/count mismatch). Publish the before/after trade-count delta and the
> revised walk-forward PF. Only after the data layer is certified do we touch
> order-book imbalance / net-flow / funding-OI logic.

Data integrity before signals. The whole swarm + the roadmap consult agree.

## Cheapest paid data worth buying

CryptoQuant / Kaiko exchange-flow feeds — the one structural advantage retail
lacks. Worth more than months of free-API mining.

## The common retail mistake (beyond overfitting)

Ignoring **capacity decay** — signals that backtest at PF 1.4 "die above ~$50k
capital" (DeepSeek, ollama_cloud). Any edge claim must be net-of-cost AND
capacity-aware, or it evaporates the moment real size is applied.

## Actionable sequencing (3 months, one operator, CRYPTO)

1. **Wk 1–2** — fix the duplicate-re-emission bug at the writer; 60-day clean
   backfill; REST reconciliation. Certify the data layer.
2. **Wk 3–4** — backfill `regime` onto the clean ledger; ship the
   regime-conditional harness (`evaluate_by_regime`).
3. **Wk 5–8** — build ONE causal-hypothesis signal: CRYPTO order-book imbalance
   + exchange net-flow, regime-filtered. Pre-register, harness-run.
4. **Wk 9–12** — if it passes: forward-test net-of-cost + capacity-aware. If it
   kills (9th kill): declare paper-only.

## Cross-check vs prior session work

- Aligns with `ROADMAP_TO_EDGE_2026-05-18.md` (Phase 0 honesty → Phase 1
  harness → Phase 2 one causal hypothesis).
- The dedup fix = the 83%-data-loss bug already flagged.
- on-chain crypto owner = peer STRAND B (`OWNERSHIP_DECISION_2026-05-18.md`).
- Funding-OI divergence is borderline a banned family (funding-rate directional
  was killed) — prefer order-book imbalance + net-flow, which are clean.

*Swarm run: `swarm_runs/edge-harvest-2026-05-18/`. Prompt:
`swarm_runs/_prompts/edge_harvest_2026-05-18.md`.*
