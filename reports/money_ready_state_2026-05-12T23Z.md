# Money-Ready State Snapshot — 2026-05-12T23:43Z

**Why this doc:** A Grok session pulled fresh `dashboard_data.json` (generated_at `2026-05-12T23:43:57Z`, age 0.2h) and the per-class numbers are materially different from the `2026-05-05T01:37Z` snapshot cited in all prior plan docs ([reports/money_ready_validation_plan_2026-05-11.md](reports/money_ready_validation_plan_2026-05-11.md), [reports/merged_action_items_v2_2026-05-12.md](reports/merged_action_items_v2_2026-05-12.md)). This doc is the current state of record.

---

## 0. Current asset_class_health (verbatim from `dashboard_data.json::performance.asset_class_health`)

| Class | n | WR | PF | total_pnl_pct | status | sizing_allowed | Tier vs Charter §2 |
|---|---|---|---|---|---|---|---|
| **CRYPTO** | 7,800 | 46.5% | **1.36** | +3024.33 | stable | true | **Tier 3** (PF≥1.2, WR≥45%, n≥100) |
| **EQUITY** | 447 | 53.2% | **1.55** | +376.68 | stable | true | **Tier 2** ✓ (PF≥1.5, WR≥50%, n≥100; MDD TBD) |
| **COMMODITY** | 425 | **67.8%** | **3.94** | +697.73 | stable | true | **Tier 1 candidate** (PF≥2.0 ✓ / WR≥55% ✓ / MDD TBD / n≥200 ✓) |
| **FOREX** | 1,357 | 46.3% | **0.29** | −1025.43 | stressed | **false** | Below Tier 3 (PF<1.2) — sizing blocked per PR #909 |
| **ETF** | 107 | 56.1% | **1.34** | +37.48 | stable | true | **Tier 3** (PF≥1.2 ✓, WR≥45% ✓, n≥100 ✓) — short of T2 PF by 0.16 |
| **BOND** | 11 | 54.5% | **0.66** | −1.53 | thin_sample | **false** | Below charter n floor (n<100) AND **PF crashed below 1.0** |
| FUTURES | 0 | — | null | 0 | insufficient | false | not classified |
| UNKNOWN | 6 | 50% | 2.4 | +0.13 | insufficient | false | not classified |

**Total system view (`summary`):** 134 systems, 8,423 valid closed picks, overall PF 1.1 / WR 42.3%. Charter floors apply per-class, not to the rollup.

---

## 1. Delta vs. my May 5 baseline

| Class | May 5 baseline (cited in plan) | May 12 23:43Z (current) | Direction |
|---|---|---|---|
| CRYPTO | 1.26 / 44.8% / 8162 | 1.36 / 46.5% / 7800 | ↑ improved |
| EQUITY | 1.42 / 52.8% / 428 | **1.55 / 53.2% / 447** | **↑ NOW MEETS T2** |
| COMMODITY | 2.08 / 48.7% / 816 | **3.94 / 67.8% / 425** | **↑↑ NOW T1 CANDIDATE** |
| FOREX | 0.28 / 45.6% / 1249 | 0.29 / 46.3% / 1357 | flat — still blocked |
| ETF | 1.20 / 53.4% / 88 | **1.34 / 56.1% / 107** | **↑ past charter n=100 floor** |
| **BOND** | **1.72 / 55.6% / 18** | **0.66 / 54.5% / 11** | **↓↓ REGRESSED HARD** |

Two oddities to investigate:
- **COMMODITY n dropped from 816 to 425** while PF nearly doubled (2.08 → 3.94). That's not organic — looks like a re-resolution / re-classification removed historical rows. Possible cause: the COT-positioning paper-pilot rows being split out, or the CT=F/KC=F blacklist being applied retroactively to closed-picks history.
- **BOND n dropped from 18 to 11 and PF crashed from 1.72 to 0.66.** Same kind of re-resolution event. The 7 rows that disappeared were likely the futures_momentum/ZN=F legacy rows being correctly re-categorized OUT of BOND.

If both deltas come from the same re-resolution pass, **the new numbers are more accurate**, not less. The legacy BOND `n=18` figure was artifact; current `n=11` is the true BOND book today. COMMODITY's PF 3.94 may be the true post-cleanup edge — or it may be temporary survivorship bias from removing big losers.

---

## 2. Walk-forward coverage gap (CRITICAL)

`walkforward.by_class` keys (from Grok dump): **`['ETF', 'CRYPTO', 'FOREX', 'EQUITY']`**.

**No COMMODITY walk-forward. No BOND walk-forward.**

Per Charter §8: "Promotion to Tier 2 live capital: requires 3 consecutive months of clean Tier 2 metrics in walk-forward + n ≥ 100 closed picks."

This means COMMODITY at PF 3.94 / WR 67.8% / n=425 **cannot be promoted to live capital** under the charter, no matter how good the headline numbers look. Walk-forward for COMMODITY is now the highest-leverage net-new task on the queue. Without it, the strongest-looking class is stuck in paper-only.

---

## 3. Updated action queue (supersedes [reports/merged_action_items_v2_2026-05-12.md](reports/merged_action_items_v2_2026-05-12.md) §0)

### New P0
| Item | Why | Effort |
|---|---|---|
| **COMMODITY walk-forward backtest** | Class is at headline T1, no OOS validation → can't promote to live per Charter §8. Single highest-leverage gap. | Medium — wire `value_backtest.py` or equivalent against COMMODITY universe |
| **BOND regression forensic** | n dropped 18→11, PF crashed 1.72→0.66. Need to know whether (a) re-resolution corrected an artifact (good — true state revealed) or (b) recent picks are genuinely worse (bad — need to investigate). | Small — SQL diff between May 5 and May 12 closed-picks |
| **COMMODITY n-drop forensic** | n dropped 816→425 while PF doubled. Same question: re-classification correction or selective survivor? | Small — same diff method |

### Reaffirmed P0
| Item | Status |
|---|---|
| Set `vars.BOND_ELITE_FLOOR = 32` | Still the right call. Even with n=11 / PF 0.66, more raw signals → faster forensic + faster path back to T2 once the cause is understood. |
| FOREX hard-cap sizing (PR #909) | Verified live: `sizing_allowed: false` in current payload. ✓ |
| CT=F `cot_positioning` paper pilot | Still the single-pick launch answer; track to ~2026-05-23 graduation. |

### Items now achievable
- **CLAUDE.md MAJOR GOAL #1 two-class T2 lineup** is closer than the plan claimed. **EQUITY + COMMODITY** could fill it the moment COMMODITY walk-forward lands. ETF is one PF tick short (1.34 vs T2's 1.5) but has the charter n now — it's the natural third slot.

---

## 4. Implications for prior committed docs

These files now contain stale per-class numbers but the framework / methodology / corrections in them remain valid:

- [reports/money_ready_validation_plan_2026-05-11.md](reports/money_ready_validation_plan_2026-05-11.md) §0 table cites May 5 snapshot; superseded by §0 of this doc.
- [reports/merged_action_items_2026-05-12.md](reports/merged_action_items_2026-05-12.md) — v1, fully superseded by v2.
- [reports/merged_action_items_v2_2026-05-12.md](reports/merged_action_items_v2_2026-05-12.md) §0 — partially stale; new P0 items above supersede the COMMODITY / BOND lines.
- [reports/bond_root_cause_2026-05-12.md](reports/bond_root_cause_2026-05-12.md) — its three-layer analysis is still correct in *structure*, but the n=18 / PF 1.72 starting numbers are now n=11 / PF 0.66. The conclusion that the elite_floor is the binding gate is unchanged.
- [reports/deep_dive_forex_2026-05-12.md](reports/deep_dive_forex_2026-05-12.md) — FOREX numbers virtually unchanged (PF 0.28 → 0.29). Doc remains current.
- [reports/cloud_agent_claims_validation_2026-05-12.md](reports/cloud_agent_claims_validation_2026-05-12.md) — methodology still applies; the rejections of P0-E and P0-F are unaffected.

---

## 5. Note on Grok's methodology in the source pull

Grok ran the freshness preflight cleanly (0.2h fresh, OK) and extracted `asset_class_health` correctly. Two execution stumbles to flag for future sessions reading their output:
- Hit a Python heredoc syntax error twice before getting bash escaping right. Numbers in the working output are still correct — just took two extra rounds.
- Couldn't find `daily_ideas.md` (file doesn't exist in repo under that name; closest is the per-day `memory/*.md` series). Their per-class enhancement claims should therefore be read as derived from `dashboard_data.json` + `PERFORMANCE_CHARTER.md`, NOT from a `daily_ideas.md` priors document.

The Grok numerical findings are reproducible and check out. Their commentary on what's needed (walk-forward gaps, drift state, factor analysis, external data wires) is consistent with what's already on our P1/P2 queue.

---

## 6. Single sentence for the next operator

The dashboard snapshot moved meaningfully between May 5 and May 12: COMMODITY and EQUITY now look money-ready on headline metrics, ETF is past the charter sample floor, and BOND regressed in a way that needs forensic before any "money-ready" claim — and the binding constraint on promoting any class is now the absence of walk-forward for COMMODITY / BOND.
