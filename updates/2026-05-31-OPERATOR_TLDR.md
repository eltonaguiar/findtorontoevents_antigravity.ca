# OPERATOR TL;DR — 2026-05-31 (single-page action packet)

When you return to this session, read THIS page first. Everything else can wait.
Total time to clear PRIORITY 1: ~12 minutes. Total to clear PRIORITY 2: ~2 hours.

---

## TOP OF PAGE: 60-second status

- **Banner state**: `any_red=false` — 5/5 checks passed (verified live via `db_health.json` `.overall`)
- **Production pipeline**: 476 outcomes resolved in last hour; 2 of 3 critical hourlies still queued on GHA capacity
- **GHA queue depth**: 20 runs currently queued (limit-bound — see PRIORITY 1)
- **Session PRs merged**: 147
- **Action items pinned for you**: 14
- **Open incidents**: see `vw_all_incidents` (TRIAGED + OPEN) — count via reproducibility block below

---

## PRIORITY 1 — do FIRST (5-minute decisions, ~12 min total)

1. **GHA-unblock pick** — PR #250 ships 3 options (A/B/C). Packet's recommendation: **OPTION A**.
   - Decision required: **A / B / C**
   - Why now: unblocks the 2 stalled critical hourlies feeding `pf_registry`
   - Time: 5 min

2. **PR #229 — `harness_healthy` draft**: approve OR reject (1-click).
   - Time: 2 min

3. **PR #227 — reject-INVERT verdict**: approve OR override with bucket-dampen.
   - If you override → set bucket-dampen factor in same decision
   - Time: 5 min

---

## PRIORITY 2 — do second (10–30 min decisions, ~2 hours total)

- **PR #228 — `skyrocket_detector`**: pick one — approve SHADOW_PILOT 30d / retire / re-do. 10 min.
- **9-item diagnostic packets** (PR #239 + #243 polish): straight-apply at your own pace. ~15 min per item.
- **33 persona activation steps** (PR #233 + RT corrections):
  - CRYPTO persona **BLOCKED** until resolver intrabar rewrite lands (upstream T2 blocker per MEMORY.md)
  - The other 32 are unblocked. 30 min for the batch.

---

## PRIORITY 3 — heavy lifts (1–3 hr each)

- **FOREX kill list** (INCIDENT_FOREX #6 / #7): wire `dxy_trend_filter`; retire `cta_cross_asset_tsmom` whitelist.
- **COMMODITY rebuild** from non-COT signals (current COT-heavy stack is failing — PF 0.31 / WR 11% / n=28 per CLAUDE.md).
- **EQUITY rebuild**: un-kill `stocks_rsi2_pullback` (live audit refutes the kill premise).
- **PENNY Gate 0 + UEPS scanner** stand-up.

---

## DO NOT

- Do **NOT** apply PR #232 diffs — **REVOKED** (fabricated; warning landed in PR #235).
- Do **NOT** trust agent self-reports of `verified=N` without an independent third-party check (see lesson in PR #238).
- Do **NOT** `git add -A` in the shared working tree — multiple agents are stashing/branching simultaneously.
- Do **NOT** size up any class on the historical May-3 figures — the deprecated `AUDIT_HEALTH_SOURCE=recompute` path bypassed flicker-dedup.

---

## Reproducibility (paste-able)

```bash
# Banner state
curl -sL "https://findtorontoevents.ca/audit/data/db_health.json" | jq '.overall'

# GHA queue depth
gh run list --status queued | wc -l

# Open incidents
mysql -e "SELECT COUNT(*) FROM vw_all_incidents WHERE status IN ('OPEN','TRIAGED')"

# Verify CRYPTO post-M-067 figures (NOT the disputed 78.9% Smart-Picks cell)
jq '.asset_class_health.CRYPTO' audit_dashboard/data/money_ready_verdict.json
```

---

## Links

- **Diagnostic packets**: PR #239 + #243
- **Verdicts**: #227 (reject-INVERT), #228 (skyrocket_detector), #229 (harness_healthy)
- **Revoked + lesson**: #232 (warned in #235), #238
- **GHA unblock options**: PR #250
- **Ledgers**: PR #220, #226 (v1), #246 (v2), #251 (v3)

---

## Context refs (read only if a PRIORITY 1 decision is ambiguous)

- `CLAUDE.md` — MAJOR GOALS section (north-star: phenomenal /audit performance, Tier-2 min)
- `MEMORY.md` → `project-money-ready-2026-05-31` (resolver intrabar = THE upstream T2 blocker)
- `MEMORY.md` → `project-confidence-trust-edges-2026-05-31` (live audit refutes "global ML inversion")
- `docs/MUTATION_THREE_AXIS_PROTOCOL.md` — mutate-before-kill protocol (cite before any kill PR)

— Generated 2026-05-31 by wrap-up agent. Pinned at `/updates/index.html` above the auto-incidents block per CLAUDE.md entry-insertion rule.
