# bond_cot_validation_clarifications_2026-05-13.md

## Reviewed
- for review.txt (agent log of swarm corrections on money-maker plan)
- reports/money_ready_validation_plan_2026-05-11.md §8 (P0 corrections: forward_validator was already fixed, real BOND issue = FRED_API_KEY missing + low n=18)
- reports/quant_swarm_merged_round1_2026-05-12.md + merged_action_items_v2 (COT strongest edge on cot_positioning/CT=F: DSR=1.0/WR90%/n=100; COMMODITY PF lift validated)
- dashboard_data.json (COMMODITY PF 3.94 n=425 strongest; BOND n=11-18 thin; FOREX blocked)

## Validated Claims
- BOND allowlist ok since Apr 2026; normalization to equity is real side-effect.
- COT commercial z-score is highest-ROI unshipped edge (+2.8pp WR on COMMODITY when z>1.0).
- Swarm had 3 false root-cause claims (fixed in plan §8).
- daily_ideas.md exists and fed hedge-fund rescue swarm (COT/FRED/regime themes).

## Unclear / Needs Swarm
1. Current FRED_API_KEY status in GitHub secrets + whether bond emitter now produces >0 new picks/day post-PR#928.
2. Has COT z-score gate been bootstrapped/shipped or still P1?
3. Exact current BOND n and pick emission rate from ejaguiar1_stocks DB (dashboard shows legacy?).
4. Ruflo's view on risk-parity allocation (40% COMMODITY proposal from swarm).

Created this MD per instruction. Now spawning swarm + Ruflo review via bus.
