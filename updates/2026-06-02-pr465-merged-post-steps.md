# PR #465 merged — post-merge operational steps (2026-06-02)

## Merged

- **PR:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/465
- **Main commit:** `4e2887f9e` — mutation PF harden + `production_scanner` promotion gate shadow (§6f2.8)
- **CI:** portfolio_engine TP/SL tests aligned with `config/portfolio_risk_profiles.json` (conservative `-6.5%`)

## Verified on main (this session)

```bash
python3 -m pytest tests/test_mutation_framework_pf.py -q   # 4 passed
DB_PASS_STOCKS=... python3 tools/run_mutation_scan_honest.py  # 5 INVERT adopt/consider
python3 tools/run_verified_pilots_daily.py                   # ok=True
python3 tools/etf_forward_stats.py --write
```

| Check | Result |
|-------|--------|
| Honest mutation scan | 2298 closed / 35 strategies → **5** INVERT adopt/consider |
| `PROMOTED_STRATEGIES` | **Empty** (by design) |
| ETF forward `n_closed` | **0** — XLK BUY OPEN (shadow gate `n<30`) |
| Stale OPEN resolver | 10 batches × 500 → **0 stale** (2489 OPEN total) |
| Resolver health | **YELLOW** (stale_by_category estimate > 0; forward_test GREEN) |

## Operator gates (unchanged)

1. **Do not set** `PROMOTION_GATE_ENFORCE=1` until at least one strategy is on `audit_trail/promotion_gate.PROMOTED_STRATEGIES` — empty allowlist blocks all emission.
2. **Do not add** `etf_verified_dual_momentum` to allowlist until `paper_pilot_forward.n_closed >= 30` (then promotion at 100).
3. **Do not ship** Mimo INVERT mutations to production — `baby_strategies/inverted_strategies.py` remains RESEARCH ONLY.

## Next actions (priority)

| P | Action | Command / trigger |
|---|--------|-------------------|
| P1 | Daily pilot + forward stats | Cron or `python3 tools/run_verified_pilots_daily.py` |
| P1 | Honest mutation scan weekly | `python3 tools/run_mutation_scan_honest.py` |
| P2 | Resolver catch-up | CI/cron `universal_pick_resolver` — last resolve ~22h stale on file mtime |
| P2 | ETF XLK close path | Wait monthly rebalance or manual pilot close → first `n_closed` |
| P3 | Allowlist admission | After shadow n≥30 + gates: edit `PROMOTED_STRATEGIES` + optional `PROMOTION_GATE_ENFORCE=1` soak |

## Cross-PC

Broadcast sent via `192.168.2.32:8788` (PR465 merge summary).

## Ops completed (2026-06-02 ~19:02 UTC)

| Job | Result |
|-----|--------|
| `universal_pick_resolver.py` | **+123** newly resolved (TP 75 / SL 37 / EXP 11); 565 active checked |
| `resolve_stale_open_picks.py` | **24** MySQL stale rows closed; OPEN count **2465** |
| `run_mutation_scan_honest.py` | 5 INVERT adopt/consider (unchanged) |
| `run_verified_pilots_daily.py` | ok=True |
| Resolver `last_pick_resolved_at` | GREEN (~12 min ago after run) |

Live doc: https://findtorontoevents.ca/updates/2026-06-02-pr465-merged-post-steps.md

## Wave 2 ops (~19:04 UTC)

| Job | Result |
|-----|--------|
| `backfill_source_system_from_strategy.py` | 0 rows (already clean) |
| `outcome_resolver.py --mysql` | 3 non-crypto bar-replay (FOREX TP×2, COMMODITY SL×1); use `PYTHONPATH=.` |
| `run_eagle_suite.py` | ok=True; money_ready 0/9 freeze active |
| MySQL `trading_picks` | OPEN **2465** (commodity 771, equity 765, crypto 432); ACTIVE **3726** separate |
| `resolve_stale_open_picks` | 0 time-stale in 10×500 batches (hold-window rules) |

**Note:** `check_resolver_health` YELLOW `stale_by_category` counts *all* OPEN rows as `estimated_stale` — not time-expired picks. Real backlog is OPEN volume + ACTIVE status hygiene, not the health label alone.
