# Hedge-fund-quality roadmap — coordinated next steps

**Purpose:** Single place for multi-agent alignment (Redis bus + repo). Tactical fixes are landing; this lists **architectural** and **gating** steps toward institutional-grade pick quality.

**Execution / locks / order:** See [`HF_HIGH_IMPACT_COORDINATION_PLAN.md`](HF_HIGH_IMPACT_COORDINATION_PLAN.md) (Threshold A, VA cohort, decay UI, preferred pairs, `risk_policy.json`, optional `hf_policy_thresholds.py`).

**Related bus threads (2026-04-04):** unified risk (crypto + sports), loser forensics (single-strategy losers vs multi-system winners), hedge-fund tier funnel (score + trust + direction conflict), VA cohort structural gap.

---

## P0 — Truth layer (what we measure)

1. **Verified Alpha / research cohort** — Every active pick must be joinable to a **verifiable cohort** (not only aggregate `verified_alpha` counts). *Peered finding:* VA summary vs per-pick refs. **Owner:** audit pipeline + `audit_trail/dashboard_generator.py` + template (coordinate locks). **Progress:** verified-alpha picks now carry `va_cohort_id`, `va_cohort_n`, `va_rule_version`, `va_cohort_basis`, `va_cohort_wr_pct` on the payload (generator); add `/audit` column or tooltip when template lock allows.
2. **Forward vs backtest decay** — Already computed in `collect_backtest_vs_forward()` / strategy leaderboard in [`audit_trail/dashboard_generator.py`](audit_trail/dashboard_generator.py); **surface prominently** on `/audit` and **hard-gate** promotion when `decay` exceeds threshold (policy TBD: e.g. fwd WR &lt; BT WR − 15% with n≥20). **Progress:** `hf_decay_watchlist` (top 10 worst decay, FWD n≥20) in `dashboard_payload.json` + BT vs FWD tab banner (NFA); default table sort = worst decay first.
3. **Forward degradation tracker** — [`audit_trail/forward_degradation_tracker.py`](audit_trail/forward_degradation_tracker.py): extend coverage to **all** published sources; wire alerts into dashboard or `quality_gates`.

## P1 — Risk & concentration

4. **Cross-domain risk** — Same discipline as sports: **odds/stake caps**, **book/symbol whitelist**, **Kelly dampening** → mirror for crypto (per-wallet / per-symbol notional caps, max concurrent correlated picks). *Discuss on bus:* single `risk_policy.json` consumed by scanner + sports bankroll. **Progress:** [`config/risk_policy.json`](../config/risk_policy.json) v1 + [`alpha_engine/risk_policy_loader.py`](../alpha_engine/risk_policy_loader.py); virtual portfolio uses `per_trade_cap_pct` cap.
5. **Concentration** — Block or down-rank when one symbol/strategy &gt; X% of notional or repeated single-system picks (bus: ALGO concentration case).

## P2 — Consensus & signal hygiene

6. **Multi-system agreement** — Treat **agreeing_systems ≥ 2** (or trust-weighted equivalent) as default for **tier-1 display**; single-system picks labeled **experimental** (super_signal / aggregator already bias this direction).
7. **KOL / news** — [`docs/AGENT_BUS_KOL_SLICE_2026-04-04.md`](AGENT_BUS_KOL_SLICE_2026-04-04.md): news vs KOL scoring done; **next:** promote `kol_consensus` in [`cross_aggregation/system_trust_registry.py`](cross_aggregation/system_trust_registry.py) only after **closed-trade** evidence; keep `predictions` BANNED until forward audit.

## P3 — Ops & CI

8. **Social pipeline** — [`.github/workflows/social-prediction-tracker.yml`](.github/workflows/social-prediction-tracker.yml): ensure `kol_consensus_engine` + `active_predictions` export run green; monitor empty JSON as **data incident**, not silent OK. After each consensus run, CI runs [`tools/verify_kol_consensus_export.py`](../tools/verify_kol_consensus_export.py) (fails on malformed export; **warns** if the array is empty).
9. **Playwright / TESTING_PROTOCOL** — Keep `/audit` and main pages on the JS-error gate; add assertions for **tier labels**, **forward_validated**, **non-null cohort** when VA features ship.

---

## Suggested Redis bus protocol

- **Broadcast** when claiming P0 files (`template.html`, `quality_gates.py`, `dashboard_generator.py`).
- **Tag messages** `HF-P0` / `HF-P1` so log stays searchable.
- **cursor-kol-bus** focus: consensus + KOL trust + integrator; avoid conflicting with active **VA / elite_score** locks.

---

## Immediate actions (any agent)

- [ ] Resolve **VA per-pick cohort** (P0 #1) — blocks honest "hedge fund" marketing of VA.
- [ ] One **dashboard row** or section: "Backtest vs forward decay" top 10 worst strategies.
- [x] Bus: propose numeric thresholds for decay + concentration (team sign-off). **APPROVED 2026-04-04**

---

## Approved numeric thresholds (2026-04-04, user-approved)

| ID | Policy | Threshold |
|---|---|---|
| A | BT/FWD decay hard-gate | Reject if `fwd_WR < BT_WR − 15pp` AND `n_closed ≥ 20` — **wired:** `audit_trail/hf_policy_thresholds.py` + penalty + Smart Picks exclusion in `quality_gates.py` when `bt_win_rate` is present on the pick |
| B | Concentration caps | Max 10% equity per symbol, 20% per direction-side, 2 portfolios holding same symbol-direction |
| C | Tier-1 display default | `agreeing_systems ≥ 2`; single-system tagged `experimental` |
| D | Strategy retirement | Auto-BANNED if `fwd_WR < 45%` after 30 closed trades |
| E | Portfolio circuit breaker | DD > 15% → pause new picks 24h |
| F | ml_composite fallback | `conf * 0.5` (was 0.8) when `ml_score is None` |
| G | Consensus conflict hard-reject | Direction opposes recommended_direction AND `confidence_delta > 0.25` AND `is_real_conflict` |

**Sources:** Loser forensics `docs/TV_LOSER_FORENSICS.md` (F, G), Kimi audit §4 (A), ALGO 30%-equity concentration incident (B), FETUSDT under-scoring (C), existing `quality_gates` thresholds (D), hedge-fund standard practice (E).

**Owners:** A/B/C/D/F/G → `claude-opus-scoring` (scoring pipeline); E → portfolio layer (TBD).
