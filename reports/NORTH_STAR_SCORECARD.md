# North Star Scorecard — Hedge-Fund-Grade Edge Per Asset Class

**Last Updated:** 2026-05-19  
**Next Update:** 2026-05-26 (weekly)

---

## TIER TARGETS

| Tier | PF | WR | MDD | n per class |
|------|-----|-----|-----|-------------|
| **Tier-2 (Charter Minimum)** | ≥1.5 | ≥50% | <20% | ≥100 |
| **Tier-1 (Renaissance)** | ≥2.0 | ≥55% | <10% | ≥200 |

---

## CURRENT STATE

| Metric | Current | Target (T2) | Target (T1) | Status |
|--------|---------|-------------|-------------|--------|
| **Admissible signals (harness)** | 0/12 tested | ≥1 per class | ≥3 per class | 🔴 |
| | | | | |
| **CRYPTO PF** (policy_clean_net) | 0.66 | ≥1.5 | ≥2.0 | 🔴 |
| **CRYPTO WR** | 44.4% | ≥50% | ≥55% | 🔴 |
| **CRYPTO n** | 1127 | ≥100 | ≥200 | ✅ |
| **CRYPTO MDD** | 100% | <20% | <10% | 🔴 |
| | | | | |
| **COMMODITY PF** | 1.42 | ≥1.5 | ≥2.0 | 🟡 |
| **COMMODITY WR** | 54.5% | ≥50% | ≥55% | ✅ |
| **COMMODITY n** | 55 | ≥100 | ≥200 | 🔴 |
| **COMMODITY MDD** | 52.4% | <20% | <10% | 🔴 |
| | | | | |
| **EQUITY PF** | 0.25 | ≥1.5 | ≥2.0 | 🔴 |
| **EQUITY WR** | 20.0% | ≥50% | ≥55% | 🔴 |
| **EQUITY n** | 5 | ≥100 | ≥200 | 🔴 |
| **EQUITY MDD** | 12.9% | <20% | <10% | ✅ |
| | | | | |
| **FOREX PF*** | 1.49 | ≥1.5 | ≥2.0 | 🟡 |
| **FOREX WR*** | 56.1% | ≥50% | ≥55% | ✅ |
| **FOREX n*** | 148 | ≥100 | ≥200 | ✅ |
| **FOREX MDD*** | 4.3% | <20% | <10% | ✅ |
| | | | | |
| **ETF PF** | — | ≥1.5 | ≥2.0 | 🔴 |
| **ETF WR** | 50.0% | ≥50% | ≥55% | 🟡 |
| **ETF n** | 2 | ≥100 | ≥200 | 🔴 |
| **ETF MDD** | 2.0% | <20% | <10% | ✅ |
| | | | | |
| **BOND PF** | 0.00 | ≥1.5 | ≥2.0 | 🔴 |
| **BOND WR** | 0.0% | ≥50% | ≥55% | 🔴 |
| **BOND n** | 5 | ≥100 | ≥200 | 🔴 |
| **BOND MDD** | 47.9% | <20% | <10% | 🔴 |

*\*FOREX class-blocked at 0% risk cap; metrics shown for study only.*

---

## INFRASTRUCTURE METRICS

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Forward resolution rate (non-crypto) | 0% | ≥80% | 🔴 |
| Active crypto symbols | 12 | ≥50 | 🔴 |
| Hypotheses tested | 12 | 20 | 🟡 |
| Hypotheses admitted | 0 | ≥3 | 🔴 |
| Emitter whitelist enforce | 0 (shadow) | 1 | 🔴 |
| NULL strategy picks in ledger | 5,945 | 0 | 🔴 |
| Dashboard single source of truth | No | Yes | 🔴 |

---

## HYPOTHESIS REGISTRY STATUS

| ID | Hypothesis | Class | Status | Result |
|----|------------|-------|--------|--------|
| H-001..H-011 | Previously tested (see EDGE_VERDICT) | Various | KILLED | 0/11 admitted |
| H-006 | CRYPTO funding-rate | CRYPTO | REJECTED | Sign-unstable (n=4,838) |
| H-007 | COMMODITY roll-yield | COMMODITY | REJECTED | Sign-unstable (n=2,964) |
| H-008 | BOND 2s10s slope-momentum | BOND | REJECTED | Sign-unstable (n=57,117) |
| | | | | |
| **H-009** | COMMODITY inventory-surprise × roll yield | COMMODITY | NOT TESTED | — |
| **H-010** | EQUITY PEAD (SUE-based) | EQUITY | NOT TESTED | — |
| **H-011** | ETF 12-1 cross-sectional momentum | ETF | NOT TESTED | — |
| **H-012** | CRYPTO tick-level order-flow imbalance | CRYPTO | REQUIRES DATA | — |
| **H-013** | CRYPTO UTC-hour filter | CRYPTO | NOT TESTED | — |
| **H-014** | trust_score replaces confidence | ALL | NOT TESTED | — |

---

## WEEKLY CHANGELOG

| Date | Change | Author |
|------|--------|--------|
| 2026-05-19 | Initial scorecard created | Claude Code |
