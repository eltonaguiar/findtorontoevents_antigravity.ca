# Next-Steps Verdict: What should the agent do next? (2026-05-19)

You are reviewing the current state of a multi-asset algorithmic trading audit system. The operator runs an autonomous Claude Code agent that advances the system. Your job: given the facts below, give a prioritized verdict on what the agent should do NEXT. Be concrete and terse.

## Current Dashboard State

| Class     | Verdict          | n_resolved | Notes |
|-----------|------------------|------------|-------|
| CRYPTO    | MONEY_READY      | 292        | ml_enhanced elite strategies PF=40-53, WR=90%+ |
| COMMODITY | WATCH            | 215        | WR=51.16% < 55% floor; CT=F 56% concentration; multi_asset_copytrader n=51 WR=56.9% PF=1.67 is the only clean strategy |
| EQUITY    | INSUFFICIENT_DATA| 9          | MySQL sync 2026-05-24 unlocks n=240 |
| FOREX     | NOT_READY (HARD_DISABLED) | 641 | WR=32%, structurally broken |
| FUTURES   | INSUFFICIENT_DATA| 12         | multi_asset_scanner n=11 WR=9.1% PF=0.48 |
| BOND      | INSUFFICIENT_DATA| 1          | scanner accumulating |
| ETF       | INSUFFICIENT_DATA| 1          | scanner runs every 6h, n approaching 87 |

## Hypothesis Registry

| ID    | Status                | n    | Verdict |
|-------|-----------------------|------|---------|
| H-001 | LIVE_TESTING          | 134  | WATCH — 2 walk-forward windows stable (need 3); WR=78.4% direction consistent |
| H-002 | SHADOW_IMPLEMENTATION | —    | PEAD strategy; shadow runner + CI just deployed (pead_shadow_log.jsonl collection starts today) |
| H-003 | SHADOW_LIVE           | —    | ETF 12-1 cross-sectional momentum, 22 ETFs, running in scanner |
| H-004 | PENDING_IMPLEMENTATION| —    | COMMODITY: inventory_surprise_roll_yield (EIA/USDA surprise + roll yield); no code yet |
| H-005 | FAILED_ARCHIVED       | —    | futures_momentum inversion does NOT rescue it (WR=2% both directions) |

## Gates in Shadow Mode (not yet enforcing)

- **M-001** `COT_STALE_GATE_ENFORCE=0` — COT data >10 days old rejects COMMODITY picks when flipped to 1
- **M-002** `COMMODITY_CTF_WEEKLY_CAP=0` — CT=F >40% in any 7-day window blocked when flipped to 1
- **M-096** `COMMODITY_CTF_CAP=shadow` — CT=F symbol concentration cap per active picks

## Pending User-Approval Items

1. Block `("FUTURES", "futures_momentum")` — WR=2%, n=202, H-005 confirmed inversion fails
2. COMMODITY paper pilot launch — D-001 decision: $0 defer vs $50K 10% shadow
3. COMMODITY WR floor: keep 55% (WATCH) or drop to 52% to allow MONEY_READY with n=215, WR=51.16%?
4. Flip M-001 to enforce (`COT_STALE_GATE_ENFORCE=1`)
5. Flip M-002 to enforce (`COMMODITY_CTF_WEEKLY_CAP=1`)

## Completed This Session

- 10 CRYPTO strategy blocks (BLOCKED_STRATEGIES)
- E-003: VTV/VUG added to H-003 universe (22 ETFs)
- H-002 shadow runner + pead-shadow-collector.yml CI deployed
- Zero non-CRYPTO strategies with n≥20 WR<50% remain unblocked
- M-001/M-002 implemented in shadow mode (already done)

## Questions for the Swarm

**Q1.** Should M-001 (`COT_STALE_GATE_ENFORCE=1`) and M-002 (`COMMODITY_CTF_WEEKLY_CAP=1`) be autonomously flipped to enforce mode? These are quality guards, not signal killers. Risks?

**Q2.** H-004 (inventory_surprise_roll_yield) is PENDING_IMPLEMENTATION. Is this the highest-value next engineering task, or should something else take priority?

**Q3.** Given COMMODITY WR=51.16% and floor=55%, is the right action: (a) drop floor to 52%, (b) wait for bad historical picks to age out, (c) block cta_replicator COMMODITY to lift WR, (d) block another strategy? Which is most defensible?

**Q4.** futures_momentum is WR=2% n=202 and the inversion test failed. Should it be added to BLOCKED_ASSET_STRATEGY_PAIRS immediately, or wait for any further evidence? This is a clear P0 block.

**Q5.** What is the single highest-ROI next autonomous action the agent should take RIGHT NOW?

Answer in ≤3 paragraphs. Be direct. Use the evidence. Do not hedge.
