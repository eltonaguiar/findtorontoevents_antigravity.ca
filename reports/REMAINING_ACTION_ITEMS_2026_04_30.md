# 2026-04-30 — Remaining Action Items + Multi-AI Feedback Request

This doc consolidates **all open follow-ups from the 2026-04-30 session**
into a single ranked queue for the next autonomous loop. Every item has:
acceptance criteria, risk classification, target file(s), and a
prerequisite chain so the loop never picks up an item whose dependency
isn't ready.

**Authoritative ordering:** the table at section 6 is the single source of
truth — the loop should walk it top-down. Section 4 has the unranked
backlog with technical detail; section 5 enumerates the multi-AI feedback
prompt to use before starting any item.

## 1. Context

Session 2026-04-30 shipped 6 sequenced PRs (#543–#548) that closed the
"no LONG_TERM Timeframe on EQUITY" complaint. All merged. Empirical
verification of impact lands once the next dashboard cron rebuilds
(within 1 hour of merge timestamp 20:12 UTC).

The remaining work falls into three buckets:

- **Bucket A — Verification follow-ups** (do these FIRST; no merge work)
- **Bucket B — Small UI / CI tweaks** (each ≤2 files, ≤30 minutes)
- **Bucket C — Phase 2-6 of Cursor's Audit Concepts plan** (each ≥1 PR)

## 2. Decision rules for the autonomous loop

The loop should **only** pick up an item if all of these are true:

1. The item is in the queue at section 6 below, ordered.
2. Its `prerequisites` column is empty OR every prerequisite is marked
   ✅ in this same doc (the loop updates this doc as items finish).
3. No more than **one item from Bucket C** is in flight at a time
   (Cursor's plan explicitly says scoring/gate enforcement is gated on
   evidence accruing — don't stack Phase 3 + Phase 5 simultaneously).
4. Every item PR follows the established session pattern:
   - branch off latest `main`
   - per-PR `updates/<date>-<short-name>.md` doc co-shipped
   - tests added / extended
   - `safe_push.sh` for any auto-commit workflow
   - Wire-Up Rule honored: opt-in flag if not yet wired to a production
     caller, OR explicit wiring plan in the PR body

## 3. Verification before code (Bucket A)

These run BEFORE the loop touches code. They convert the "expected
benefits" claims from this session into observed reality. No PR
follows; the loop just records findings under
`reports/POST_MERGE_VERIFICATION_<date>.md`.

| ID | Verification | How to verify | Pass criterion |
|----|---|---|---|
| **V1** | UEPS picks reach `active_picks.json` | `python -c "import json; d=json.load(open('alpha_engine/data/active_picks.json')); print(sum(1 for p in d.get('active_picks', d if isinstance(d,list) else []) if (p.get('id','').startswith('ueps_') or p.get('pick_type')=='long_term_value')))"` after next 4-hour cron | ≥1 row tagged `ueps_*` OR `pick_type=long_term_value` |
| **V2** | Existing closed equity picks reclassify to POSITION | `tools/asset_class_edge_audit.py` after dashboard rebuild | EQUITY × POSITION row count > 0 in the recent-window table |
| **V3** | TradingAgents emitter dormant when flag off | `python -m alpha_engine.tradingagents_emitter --dry-run` | "TRADINGAGENTS_EMITTER_ENABLED: OFF" + zero file writes |
| **V4** | Penny skyrocket cron wired | `gh workflow list --json name | jq '.[] | select(.name | test("Penny Skyrocket"))'` | workflow returned; not disabled |
| **V5** | PEAD cache persists across runs | After 2 alpha-engine-live cron cycles: `git log --oneline -- data/earnings/ \| head -5` | At least one auto-commit landed touching `data/earnings/` |
| **V6** | Concept taxonomy stamps on every pick | `python -c "import json; d=json.load(open('audit_dashboard/data/dashboard_data.json')); active=d['picks']['active']; print(f'tagged: {sum(1 for p in active if \"concept_family\" in p)}/{len(active)}')"` | 100% coverage on `picks.active` |
| **V7** | BOND credit-spread emits | After next bond-agent cron: `python -c "import json; d=json.load(open('non_crypto_agent/data/bond_picks.json')); print(sum(1 for p in d.get('picks',[]) if p.get('strategy')=='bond_credit_spread_mean_reversion'))"` | ≥1 pick (modulo signal-availability — if 0, log diagnostic, don't fail) |
