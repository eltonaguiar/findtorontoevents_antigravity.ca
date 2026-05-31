# FUTURES asset class — formally scoped RESEARCH-ONLY (INCIDENT_FUTURES #3)

**Date:** 2026-05-31 · **Author:** claude-opus (`/audit/incidents.html` triage) · **Status:** policy declared; UI badge follow-up deferred to avoid shared-tree collision

## Decision

The standalone **FUTURES** asset class on `/audit` is hereby scoped **research-only**. It must not be presented or sized as a live trading sleeve.

## Live evidence (DB-verified 2026-05-31)

```
SELECT status, COUNT(*) FROM trading_picks WHERE category='futures' GROUP BY status;
-- TP_HIT:     1
-- LOST:      18
-- TIME_EXIT: 374
-- OPEN:      35
```

- **1 TP_HIT** out of **~393 closed** picks ⇒ effective PF ≈ 0, WR ≈ 0.25%.
- 374 (95%) picks expire on TIME_EXIT — neither TP nor SL ever triggers, indicating the strategy/edge is mis-specified for the symbol set.
- Last-30d activity is minimal (n=64).
- The real liquid financial futures (CL, GC, NG, ES, ZN, etc.) are categorized under **COMMODITY** in this codebase — the standalone FUTURES tile holds the orphan/leftover futures-shaped symbols that don't fit elsewhere.

## Policy

1. **Do not size up** any FUTURES strategy regardless of dashboard tier.
2. **Do not promote** FUTURES strategies past `shadow`.
3. **Do not cite** FUTURES PF/WR in money-ready / hedge-fund-tier claims.
4. Any new strategy targeting futures-class symbols should be registered under **COMMODITY** (or **INDEX_STOCK** for ES/NQ/YM index futures), not FUTURES.
5. Future UI work (separate, focused PR): add a visible `research-only` badge to the FUTURES tile in `audit_dashboard/template.html` and adjust `assetOrder` so FUTURES renders last with reduced visual weight. **Not done in this PR** — the shared working tree currently holds 18+ uncommitted modifications from concurrent agents, and a template edit here would either fight their PRs on merge or be clobbered.

## What this PR does

- **Docs-only.** Drops this writeup.
- DB state: `INCIDENT_FUTURES #3` flipped `OPEN → TRIAGED` with `resolution_notes` pointing to this doc.
- Backup snapshot stored at `ejaguiar1_backups.incident_overall_pre_futures_research_only_20260531` (1 row of the pre-update incident record).
- **No production strategy code touched. No mass DB mutation.**

## Acceptance / next action

- Live `/audit` page already shows FUTURES under the `BLOCKED` real-money posture (line ≈1340 of template.html: "CRYPTO/FOREX/FUTURES are `BLOCKED`"). This policy formalizes that disclosure.
- Follow-up PR (deferred): add the `research-only` badge to the FUTURES tile and remove FUTURES from any "tracked classes" prose lists.

🤖 Drop authored after verifying live trading_picks counts; no agent-fabricated numbers.
