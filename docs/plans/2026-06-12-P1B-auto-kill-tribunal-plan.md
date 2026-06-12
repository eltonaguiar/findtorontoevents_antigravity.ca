# P1-B — Auto-kill tribunal (WR<35% & PF<0.8 @ n≥30)

**Priority:** P1 · **Date:** 2026-06-12  
**Evidence:** Part IV §36 — 7/13 CRYPTO strategies n≥10 fail WR<40% & Σpnl<0; no automated demotion.

---

## Problem statement

Kills are manual, incomplete, and bypassable (P0-B). Strategies like `bollinger_squeeze` (WR 4.3%) and `rsi_bounce` (WR 20%) still appear in scanner rotation.

`audit_trail/promotion_gate.py:51-53` — `PROMOTED_STRATEGIES` empty; demotion path unused.

---

## Success criteria

1. Weekly job emits `reports/strategy_tribunal_YYYY-MM-DD.json` with KILL / PROBATION / KEEP verdicts.
2. KILL verdicts auto-append to `emitter_discipline.HARD_KILL_STRATEGIES` via `emitter_audit.json` recommended_actions (human ack optional).
3. Zero strategies with n≥30 intrabar, WR<35%, PF<0.8 remain in PROVEN tier after 2 consecutive tribunal weeks.

---

## Implementation plan

### Step 1 — New tool `tools/strategy_kill_tribunal.py`

Input: SQL on `at_signal_outcomes` intrabar-resolved cohort (90d default).

Rules (per strategy × asset_class):

| Verdict | Condition |
|---------|-----------|
| **KILL** | n≥30 AND WR<35% AND PF<0.8 |
| **PROBATION** | n≥15 AND (WR<40% OR PF<1.0) |
| **KEEP** | else |

Output JSON:

```json
{
  "generated_at": "...",
  "kills": [{"strategy": "rsi_bounce", "class": "CRYPTO", "n": 40, "wr": 0.20, "pf": 0.38}],
  "probation": [...],
  "keep": [...]
}
```

### Step 2 — Wire to emitter_discipline

On `--apply` ( gated ):

```python
# merge kills into emitter_audit.json recommended_actions.force_kill
# dedupe with existing HARD_KILL_STRATEGIES
```

Never auto-remove from HARD_KILL (one-way ratchet).

### Step 3 — GHA schedule

`.github/workflows/audit-dashboard.yml` weekly (Friday slot) OR new `strategy-tribunal.yml`:

```yaml
on:
  schedule:
    - cron: '0 14 * * 5'  # Fri 14:00 UTC
```

Dry-run default; `--apply` requires `TRIBUNAL_APPLY=1` secret.

### Step 4 — Dashboard card

`/audit` → “Strategy tribunal” collapsible: last run, kill count, link to JSON report.

### Step 5 — Exception path (luxalgo)

Strategies on master-loop **do-not-relitigate** list require **manual override** to KILL even if metrics fail — unless intrabar n≥100 and WR<40% (auto-override).

---

## Verification

```bash
python3 tools/strategy_kill_tribunal.py --dry-run
# Expect: rsi_bounce, bollinger_squeeze, prediction_market_consensus → KILL
```

---

## Rollback

Revert `emitter_audit.json` force_kill additions; set `TRIBUNAL_APPLY=0`.

---

## Risks

| Risk | Mitigation |
|------|------------|
| Small-n false kill | n≥30 floor; Wilson CI in report |
| Kill luxalgo at n=93 WR=50% | Exception path |
| Overlap with P0-B manual list | Tribunal **superset** — P0-B adds immediate horrors |

---

## Metrics (acceptance)

After 4 weeks with P0-A+B+C + P1-B:

- Count of emitting strategies with intrabar WR<35% @ n≥30 → **0**
- alpha_engine CRYPTO Σpnl slope ≥ 0 (bleed stopped)
