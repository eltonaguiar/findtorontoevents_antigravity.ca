# APPROACH — Proving a Profitable Edge in the Audit Pipeline

## High-Level Plan

**Goal:** Find at least one **PROVEN** winning strategy/asset class across `findtorontoevents.ca/audit` + `/audit/hyprotrader`, document it, and wire it into production.

### Phase 1: Survey the battlefield (DONE)
- Located 66+ JSON files in `audit_dashboard/data/` — performance snapshots, forward tests, walk-forward validators, winner certificates from prior agents.
- Located MySQL `ejaguiar1_stocks.at_raw_picks` — the raw, authoritative pick ledger (source of truth).
- Auth: `dbpasses.txt` (see Phase 2 notes).

### Phase 2: Independently verify every winner claim (DONE)
- Read `SOUL.md`, `USER.md`, `AGENTS.md`, today's memory.
- Query the DB directly with `pymysql` — do NOT trust JSON certificates produced by other agents.
- Build artifact detection: frozen-exit bug = many picks sharing the same `exit_price` + same `closed_at` timestamp (the Universal Pick Resolver stamped a single resolution across batches).
- De-frozen-exit: recompute stats *excluding* clustered exit prices.

**Key findings:**
| Strategy | Symbol | n (clean) | WR (clean) | PF | Status |
|---|---|---|---|---|---|
| `high_trust_momentum` | CRYPTO basket | 202 | 57.9% | 1.81 | **PROVEN** — edge survives artifact removal |
| `commodity_term_cot` | HG=F | 335 | 47.2% | — | **DISPROVEN** — edge was an artifact; original 55.6% WR inflated by frozen-exit |

### Phase 3: Wire the PROVEN winner into production (IN PROGRESS)
1. Add `high_trust_momentum` to `audit_trail/strategy_whitelist.json` (if not already there).
2. Add `commodity_term_cot` to `audit_trail/strategy_blocklist.py` (disqualified due to artifact contamination).
3. Create `paper_trading/paper_cohort_high_trust_momentum.py` — independent forward-cohort tracker using live Binance prices, cost-inclusive PnL, artifact detection.
4. Surface the winner on `/audit` dashboard picks.
5. Write `updates/` MD documenting the full investigation + verdict.

### Phase 4: Continuous monitoring
- Weekly heartbeat runs to re-verify clean stats as new picks resolve.
- `forward_edge_validator.py` with strict gates (WR≥50%, PF≥1.15, n≥100, Wilson p<0.005, no artifact contamination).

---

See `updates/poolside-verification-2026-10-22.md` for full verification details, SQL queries, and artifact analysis.
See `updates/questions-log-2026-10-22.md` for the key investigative questions I tried to answer.

*Not financial advice. Research/educational only. Past performance does not guarantee future results.*
