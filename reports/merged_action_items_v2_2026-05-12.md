# Merged Action Items v2 — 2026-05-12

**Supersedes:** [reports/merged_action_items_2026-05-12.md](reports/merged_action_items_2026-05-12.md)
**Why v2:** v1 took cloud agent + Grok claims at face value. Two verification swarms ([reports/cloud_agent_claims_validation_2026-05-12.md](reports/cloud_agent_claims_validation_2026-05-12.md)) found multiple falsifications. This v2 is the verified action queue.

---

## 0. Final state of the autonomous run

| Item | Status | Why |
|---|---|---|
| **P0-A** FOREX hard-cap sizing | ✅ SHIPPED PR #909 | Verified, merged 2026-05-12 05:00Z |
| **P0-B** BOND `_elite_floor` 40→32 | 🚫 PUSH-BLOCKED | Session PAT lacks `workflow` scope. Workaround: user sets `vars.BOND_ELITE_FLOOR=32` at GitHub Settings (no code change needed) |
| **P0-C** 48h BTC/ETH same-symbol cooldown | 🔄 NEEDS RECONSIDERATION | Chinese report proposed at CRYPTO PF 0.9. Now at PF 1.26. Original rationale weak; needs n-significance test before shipping |
| **P0-D** confidence-inversion gate | 🔨 CLOUD AGENT OWNS | +56 lines in working tree on quality_gates.py, uncommitted |
| **P0-E** activate 41 dormant high-WR strategies | ❌ REMOVED | Top 3 named strategies falsified by swarm: cftc_cot_commercial_signal RETIRED with 0% WR (not 79.7%); rs-breakout-scout + donchian-stock-breakout don't exist in codebase |
| **P0-F** COT z-score gate from Grok | 🔻 DOWNGRADED to P1 | Grok's +2.8pp / +18% / PF 3.77 claims have no supporting data in repo. Bootstrap-first before any gate ships |
| **Single-pick launch** | ✅ ANSWER FIRM | `cot_positioning` on CT=F — DSR=1.0, n=100, WR 90%. Verified in `cot_paper_pilot.py` |

---

## 1. What the user needs to do (manual actions only an authorized human can take)

### 1a. Unblock BOND emission — 30 seconds, no code change
- Go to GitHub Settings → Secrets and variables → Actions → Variables
- Add: `BOND_ELITE_FLOOR = 32`
- The bond-agent workflow already reads `vars.BOND_ELITE_FLOOR` so it takes effect on the next scheduled run (daily 14:32 UTC on weekdays)
- **Acceptance:** /audit BOND n advances from 18 to ≥25 within 14 days while PF stays ≥1.5 and WR ≥50%
- **Stop-loss:** if PF drops below 1.0 on the first 30 new picks, revert variable to 38

### 1b. Coordinate cloud agent's commit
The parallel cloud agent has 8 dirty files in the working tree, including:
- `audit_trail/quality_gates.py` (+56 line confidence-inversion gate)
- `reports/money_ready_validation_plan_2026-05-11.md` (§8 addendum — contains the FALSIFIED FRED-timeout theory; needs correction after their commit)
- `alpha_engine/config.py`, `scanner.py`, `tools/backtest_etf_economic.py`
- 3 workflow yml files (will hit the same PAT scope issue this session did)

The cloud agent's CI test fixes and confidence-inversion gate are valuable; the BOND/FRED theory in §8 is wrong. Either commit their work and let me follow up with corrections, or have them re-read [reports/bond_root_cause_2026-05-12.md](reports/bond_root_cause_2026-05-12.md) §3 and fix §8 before committing.

---

## 2. P1 queue — work that can ship without `workflow` scope

Ordered by leverage. None blocked.

### P1-A · FOREX composite ranking (Chinese formula)
- Add feature-flagged sidecar in `audit_trail/quality_gates.py`: `Final_Score = 0.4·WR + 0.3·Trust + 0.2·Score + 0.1·Liquidity`
- Four-tier WR bands: A≥65 / B 55–64 / C 50–54 Major-only / reject <50%
- A/B against current scoring on closed Q2 2026 picks; flip flag only on win
- **Caveat:** `quality_gates.py` is dirty in cloud agent's tree. Must wait for their commit first.

### P1-B · EQUITY sample expansion (Chinese P1-2)
- Smart Picks gate 85→78; dynamic Trust `base × (1 + log(n)/10)`; early WR cut at n≥10 / 48%
- Acceptance: n=428 → n=600 within 4 weeks, PF≥1.5 maintained
- **Same caveat:** touches `quality_gates.py`

### P1-C · ETF push to n≥100 + PF≥1.5
- Trust −20%, Score −15%, Smart Picks→70, min-hold ≥4h
- Add SPY/QQQ/IWM/XLF/GLD/TLT to `multi_asset_copytrader` eligibility (line 1606 of updates/index.html)

### P1-D · COMMODITY WR lift
- WR +5% / Score +10% thin-coverage compensation; CTA 3-win activation + first-trade SL halved
- **Blocker:** `multi_asset_cot` PF=12.16/19.19 contradiction. Await PR #913 forensic output before sizing leans on this strategy.

### P1-E · COT z-score bootstrap analysis (replaces removed P0-F)
- Produce `reports/cot_zscore_bootstrap_2026-05-XX.md` with stratified bootstrap on closed COMMODITY picks splitting by `commercial_net_z` quintile
- Required artifacts:
  - WR + PF for `commercial_net_z > +1.0` vs baseline, with permutation p-value
  - Temporal alignment of Friday CFTC release dates to pick timestamps
  - Reconciliation of threshold mismatch (Grok says +1.0; code says ±2.0)
- **Only ship a gate if `WR lift ≥ 1.5pp` at `p < 0.01`**

### P1-F · dormant-strategies-audit-v2 (replaces removed P0-E)
- Produce a reproducible query against `dashboard_data.json` listing `(strategy, source_system, n_closed, win_rate, last_emit_date)` where `win_rate ≥ 0.55` and `last_emit_date < now() − 14d`
- Output a CSV
- **Then** decide what to activate — each candidate evaluated against Wire-Up Rule + retirement-status check (since cftc_cot_commercial_signal was retired but still appeared in the original cloud agent claim)

### P1-G · macro regime awareness (hedge-fund swarm theme)
- FRED + COT + VIX feeders exist; never connected
- Single `alpha_engine/macro_regime.py` that emits `{bull/bear/risk-off/risk-on, vol_regime, credit_spread_regime}` consumed by quality_gates + sizing
- Precondition for P1-H asymmetric allocation

### P1-H · asymmetric risk allocation (hedge-fund swarm theme)
- Per-class weights: COMMODITY 3–4× ETF baseline; FOREX 0× (already enforced by PR #909); CRYPTO conditional on backtest-vs-live consistency check
- Note: CRYPTO backtest-vs-live gap is **−31.12pp** (2× alert threshold). Stop sizing CRYPTO on backtest validation alone.

---

## 3. P2 — Structural

- `performance_alerts` → auto-shadow-probation wire-up
- Walk-forward for BOND + ETF
- 248 strategies × 14 families factor decomposition → daily `/audit/factors/` panel
- MAJOR GOAL banner update at `audit_dashboard/template.html:808-820` reframing FOREX as the real (now-blocked) emergency

---

## 4. Pattern-recognition note

Three agents in this session produced confidently-wrong claims (forward_validator allowlist, FRED API timeout, 41 dormant strategies, COT lift numbers). The common failure: **none of the wrong claims included a reproducible query.** Each agent identified *a* file or *a* number and stopped before re-running its own claim end-to-end.

**Procedural recommendation for future sessions:** require every "X is broken" or "Y has high WR" claim to ship with a one-liner grep / SQL / shell command anyone can re-run. Without that, the claim is opinion, not evidence. The three validation passes in this session caught four false claims for the cost of three swarm calls — that's a strongly positive ROI procedure.

---

## 5. Session-shipped artifacts (on `main`)

| Commit | What |
|---|---|
| `6a2c6b2a30` | Money-ready validation plan |
| `5e37cd3999` | FOREX deep-dive per mutate-before-kill protocol |
| `348a3078c7` | BOND root cause (three-layer blocker analysis) |
| `08a0fc1180` | Merged action items v1 |
| `6cecfa585e` | Cloud agent + Grok claims validation |
| (this commit) | Merged action items v2 (verified queue) |

Plus: the FOREX deep-dive partially fulfills CLAUDE.md mutate-before-kill protocol for FOREX. BOND root cause + this v2 close out the BOND research thread for the session.

---

## 6. Where to resume next session

- Once cloud agent commits dirty tree → push a correction commit that strikes the FRED claim in `money_ready_validation_plan_2026-05-11.md` §8 and replaces with link to [reports/bond_root_cause_2026-05-12.md](reports/bond_root_cause_2026-05-12.md)
- User sets `vars.BOND_ELITE_FLOOR=32` → monitor /audit BOND n for 14 days
- Start P1-A / P1-B / P1-C in order (FOREX composite ranking, EQUITY expansion, ETF push) **after** cloud agent's `quality_gates.py` work is in
- Ship P1-E (COT bootstrap) and P1-F (dormant-strategies query) as research docs before any gate change
