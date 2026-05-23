# MiniMax Agent Findings — Vetting Report
**Vetted by:** Claude Code (Desktop) | **Date:** 2026-05-16T06:30Z
**Source:** MiniMax agent session notes relayed via operator
**Vetting method:** All claims cross-checked against pre-registered OOS split (2026-04-01 cutoff, n=4,170 closed picks)

---

## Agent Conduct Issues (Pre-Vetting)

1. **English-only violation:** MiniMax began with Chinese-language output ("收到您的请求..."). User directive is English only. All valid findings below are from the English portions of their output.
2. **Sandbox limitation:** MiniMax operated in a cloud sandbox where `C:/findtorontoevents_antigravity.ca/` did not exist natively — they cloned the repo fresh. Their analysis is based on a point-in-time snapshot, not live data.
3. **Fabricated system names:** "Momentum London/NY" and "Battleground DNA" do not correspond to any named systems in `universal_resolved_picks.json` or `audit_dashboard/data/dashboard_data.json`.

---

## Claim-by-Claim Vetting

### Claim 1: "Battleground DNA — 62% WR, PF 1.8" (Crypto, Grade A)

**OOS Reality (`source_system = battleground`):**
| n | WR | PF |
|---|----|----|
| 27 | **0.0%** | **0.00** |

**Verdict: ❌ FABRICATED.** `battleground` has zero winners in 27 OOS closed picks. This is our worst-performing system — not even close to 62% WR. MiniMax appears to have confused the `kimi_signal_tracking` system (which DID show 88.9% WR OOS) with their fabricated "Battleground DNA" label. Do not use this figure.

---

### Claim 2: "Forex Momentum London/NY — 70% WR, PF 2.1" (Forex, Grade A+)

**OOS Reality (FOREX strategies):**
| Strategy | n | WR | PF |
|----------|---|----|----|
| MeanReversionBB | 16 | 62.5% | 2.60 |
| MomentumEMA | 5 | 80.0% | 48.83 |

**Verdict: ⚠️ PARTIALLY DIRECTIONALLY CORRECT, OVERSTATED.** There IS a `MomentumEMA` FOREX strategy with high WR (80%) but n=5 — statistically meaningless. `MeanReversionBB` at n=16, WR=62.5%, PF=2.60 is real but also thin. The "London/NY session filter" is MiniMax's fabrication — we have no session-time data in the picks. MiniMax's "70% WR, PF 2.1" is a reasonable estimate directionally (between our two real FOREX strategies) but presented without data backing. **Do not size on this — n=21 total FOREX OOS picks is insufficient.**

---

### Claim 3: "Equity Competition — 55% WR, PF 1.4" (Equity, Grade B+)

**OOS Reality (`source_system = stocks_competition`, EQUITY only):**
| n | WR | PF | AC1 |
|---|----|----|-----|
| 11 | 81.8% | 7.88 | 0.74 |

**Verdict: ⚠️ DIRECTIONALLY CORRECT (equity has edge) but numbers wrong.** `stocks_competition` real stock picks (n=11) actually show WR=81.8%, PF=7.88 — far better than MiniMax's 55%/1.4. However, AC1=0.74 makes this fragile (effective n≈8). The PF=1.4 may be MiniMax's CLASS-WIDE figure (which is unreliable since 131 of 160 "EQUITY" picks are actually crypto tokens mislabeled as EQUITY by `signal_validation`).

---

### Claim 4: "ETF Sector Rotation — 60% WR, PF 1.5" (ETF, Grade B+)

**OOS Reality:** ETF has <10 OOS closed picks in `universal_resolved_picks.json`. No reliable OOS ETF stats possible.

**Dashboard data:** PF=1.32, WR=57.0%, n=107 (live dashboard, not pre-registered OOS)

**Verdict: ❌ UNVERIFIABLE / LIKELY DASHBOARD-DERIVED.** MiniMax may have scraped the live dashboard stats without acknowledging these are in-sample figures. The dashboard-sourced ETF stats (PF=1.32, WR=57%) are below their claimed 1.5/60%. Fabricated system name "Sector Rotation" — no such named system exists.

---

### Claim 5: "Commodities Futures Momentum — 54% WR, PF 1.2"

**OOS Reality:** COMMODITY has n=0 picks in `universal_resolved_picks.json`. No OOS validation possible.

**Verdict: ❌ ENTIRELY UNVERIFIABLE.** `multi_asset_cot` (dashboard PF=4.72) has zero picks in the validated dataset. MiniMax had no data to base this on.

---

### Claim 6: Capital Allocation — $150k ($50k Forex 35%, $35k Crypto 25%, $25k Options 20%)

**Verdict: ❌ DO NOT USE.** Based on fabricated/unverified statistics. Real capital allocation must use our pre-registered OOS bootstrap results:
- CRYPTO: `aggregated_picks` OOS PF=7.02, `kimi_signal_tracking` OOS PF=15.94 → max 0.5-0.75% per pick
- EQUITY: `stocks_competition` OOS PF=3.71 but AC1=0.74 → max 0.5% per pick until AC1 normalizes
- FOREX: 21 total OOS picks — **blocked**, accumulation-gated
- COMMODITY: 0 OOS picks — **blocked**, pipeline investigation needed
- OPTIONS: No data at all — not in our system

---

## MiniMax Findings Worth Keeping

Despite the above issues, MiniMax identified **one genuinely useful insight** from their analysis:

> "Only 2 of 15+ systems are profitable according to their audit"

This directionally aligns with our OOS finding: 3 Tier 1 systems (`aggregated_picks`, `kimi_signal_tracking`, `stocks_competition`) and 1 Tier 2 (`signal_validation`) out of 18 systems tested. The "2 of 15" observation is qualitatively correct and consistent.

MiniMax's **architectural observation** is also valid: they noted a React dashboard approach for visualizing per-class edge metrics. Their deployed URL (`dm4havp0pwdj.space.minimax.io`) is a sandbox demo with fabricated data — do not share with real investors, but the visualization approach is worth considering for a future production dashboard.

---

## Recommended Follow-Up

1. **Do not use MiniMax's stats for any real-money sizing decision.** All figures are either fabricated or unverified.
2. **MiniMax's React dashboard template** could be adapted with our actual OOS data from `reports/oos_validation_2026-05-16.md`.
3. **FOREX MomentumEMA** (n=5, WR=80%) is worth watching — if it grows to n=20+ with sustained edge, it would cross the FOREX unblock threshold (`tools/forex_unblock_tracker.py` monitors this automatically).

---

*Vetting performed against: `audit_trail/edge_filter_bootstrap.py` output, pre-registered OOS split 2026-04-01.*
*Ground truth: `audit_trail/data/universal_resolved_picks.json` (5,000 picks).*
