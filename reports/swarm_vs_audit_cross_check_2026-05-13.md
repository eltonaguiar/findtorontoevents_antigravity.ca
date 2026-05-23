# Swarm consensus picks vs /audit active picks — 2026-05-13

## Headline

The swarm session (38 picks, 33 still open) and the /audit active list (44 picks
across 43 symbols) **barely overlap**: only 7 of 33 swarm-active picks share a
symbol with /audit-active, and **2 of those 7 disagree on direction**.

- 5 agree (both LONG): APTUSDT, ETHUSDT, BTCUSDT, BNBUSDT, INJUSDT.
- 2 conflict: **DOTUSDT** (swarm **UNANIMOUS SHORT** vs /audit LONG) and
  **TIAUSDT** (swarm MODERATE SHORT vs /audit LONG).
- 15 swarm-active picks have no /audit-active OR /audit-recent_closed
  counterpart (mostly EQUITY SHORTs the production scanner doesn't surface).
- 36 /audit-active symbols (mostly mid-cap alt-CRYPTO) are unrated by the swarm.

Both directional conflicts are CRYPTO LONG-only-source bias on the /audit side
(see `feedback_long_source_bias.md`) vs a swarm that votes both ways. DOTUSDT
unanimous SHORT is a real signal worth flagging.

## Direction conflicts (action required)

| Symbol | Asset | Swarm | Tier | /audit dir | Note |
|---|---|---|---|---|---|
| DOTUSDT | CRYPTO | SHORT | **UNANIMOUS** | LONG | 3/3 swarm models agree SHORT; /audit production scanner still long |
| TIAUSDT | CRYPTO | SHORT | moderate | LONG | Fewer models consulted (2/2) but 100% agreed SHORT — still a real disagreement |

**Recommended action:** before next sizing change, audit the /audit DOTUSDT
and TIAUSDT long entries — confirm source-system, run mutate-before-kill (cf.
`docs/MUTATION_THREE_AXIS_PROTOCOL.md`), and decide whether to trim the long
based on the unanimous-swarm SHORT signal.

## Coverage gaps — swarm picks /audit ignores (15)

These are picks where the swarm sees an opportunity but /audit has
**neither** an `active` pick **nor** a `recent_closed` pick on the same
symbol. A simpler 'active-only' filter gives 25 symbols — the additional
10 (ADAUSDT, AMZN, BAC, DOGEUSDT, GLD, LINKUSDT, PFE, POLUSDT, RUNEUSDT,
TLT) do exist in /audit's 3,500-row `recent_closed` log and are excluded
from this list as 'seen recently':

| Symbol | Asset | Swarm | Tier |
|---|---|---|---|
| NVDA   | EQUITY  | SHORT | **strong** |
| TSLA   | EQUITY  | SHORT | **strong** |
| PLTR   | EQUITY  | SHORT | moderate |
| CRWD   | EQUITY  | LONG  | moderate |
| F      | EQUITY  | LONG  | single |
| VZ     | EQUITY  | LONG  | single |
| USB    | EQUITY  | LONG  | single |
| UNM    | EQUITY  | LONG  | single |
| KMI    | EQUITY  | LONG  | single |
| AUDJPY | FOREX   | LONG  | single |
| USDCAD | FOREX   | LONG  | single |
| MES1!  | FUTURES | SHORT | single |
| BTCUSDC.P  | CRYPTO | SHORT | single |
| ETHUSDC.P  | CRYPTO | SHORT | single |
| DOGEUSDC.P | CRYPTO | LONG  | single |

Two **strong**-tier EQUITY SHORTs (NVDA 5/6 models, TSLA 5/6 models) and one
**moderate**-tier EQUITY SHORT (PLTR 2/2 models — same direction, smaller
sample) stand out — production scanner clearly has no equity-short surface,
consistent with the CLAUDE.md goal of advancing Goal #1 toward phenomenal
EQUITY performance (currently T2-candidate PF 1.41 / WR 52.7%).

## Coverage gaps — /audit picks the swarm hasn't evaluated (36)

| Sample (mid-cap CRYPTO alts) |
|---|
| AVAXUSDT, FETUSDT, SAGAUSDT, FILUSDT, XRPUSDT, ALGOUSDT, APEUSDT, ZKUSDT, STRKUSDT, HBARUSDT, SUIUSDT, SEIUSDT, ARBUSDT, DYDXUSDT, ATOMUSDT, … |

The swarm session ran a curated symbol list (BTC/ETH majors + selected EQUITY
+ FOREX) rather than scanning the full /audit-active set. The next swarm
session should ingest the /audit-active symbol list as the canonical universe,
so cross-validation can happen on every pick that /audit is currently long/short.

## Numbers summary

| Metric | Value |
|---|---|
| Swarm picks total | 38 (33 open, 5 resolved) |
| /audit active picks | 44 (43 unique symbols) |
| /audit recent_closed | 3500 picks across 266 symbols |
| Swarm-active ∩ /audit-active by symbol | 7 |
| Direction-aligned | 5 |
| Direction-conflict | 2 (DOTUSDT, TIAUSDT) |
| Swarm-only (no /audit footprint) | 15 |
| /audit-only (no swarm footprint) | 36 |
| Swarm tier dist (active) | 17 single · 6 moderate · 5 strong · 5 unanimous |

## Next steps

1. **Resolve the 2 direction conflicts.** DOTUSDT unanimous SHORT is the
   highest-conviction disagreement on the board — investigate before next
   /audit refresh. TIAUSDT is moderate but worth flagging.
2. **Replay the swarm against the /audit-active universe.** Use the swarm
   orchestrator with `--symbols <audit-active-list>` so the next session
   produces consensus votes for every open pick, not a curated subset.
3. **Promote the 2 strong-tier EQUITY shorts (NVDA, TSLA) and 1 moderate-
   tier short (PLTR)** to a shadow paper account via `tv-paper-trade`
   and watch correlation with /audit's blind spot for equity-short.
   Sized smaller for PLTR until conviction widens beyond 2 models.

## Refs

- Swarm picks file: `audit_dashboard/data/swarm_picks.json`
- /audit picks file: `audit_dashboard/data/dashboard_data.json::picks.active`
- Swarm metric audit (resolver bias caveat): `reports/swarm_pick_metric_audit_2026-05-13.md`
- LONG-source-bias warning that explains why /audit may not show DOTUSDT/TIAUSDT SHORTs: `memory/feedback_long_source_bias.md`
