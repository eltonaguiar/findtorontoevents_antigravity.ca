# Money-Ready Validation Plan — `findtorontoevents.ca/audit`

**Date:** 2026-05-11
**Author:** Claude Opus 4.7 (1M ctx)
**Inputs:**
- `C:\Users\zerou\Downloads\最终审核报告.docx` (Wenxin AI "Final Strategy Improvement Audit Report", dated 2026-04-22)
- Live audit fetch: `https://findtorontoevents.ca/audit` (2026-05-05T01:37Z, post-resolver-v2)
- Repo state at HEAD `cdeb17a65c2`
- Swarm feedback: 3 parallel Explore agents (Bond universe / Forex mutate-before-kill / Single-pick launch candidate)

---

## 0. TL;DR

| Class | Live (2026-05-05) | Report claim (2026-04-22) | Verdict |
|---|---|---|---|
| EQUITY | PF 1.42 / WR 52.8% / n=428 | ~PF 2.0 / WR ~50% | Report optimistic; T2-candidate |
| CRYPTO | PF 1.26 / WR 44.8% / n=8162 | PF 0.9 / WR 38% | Resolver-v2 already lifted; report is **pre-fix and stale** |
| ETF | PF 1.20 / WR 53.4% / n=88 | "0 emitted rows" | **Stale** — data IS flowing; borderline T2 |
| **COMMODITY** | **PF 2.08 / WR 48.7% / n=816** | PF ~1.6 / WR ~45% | **Stronger than report — only T2 ✓, DSR=1.0000** |
| **FOREX** | **PF 0.28 / WR 45.6% / n=1249** | PF ~1.8 / WR ~48% | **Report MUCH too optimistic — real emergency** |
| BOND | PF 1.72 / WR 55.6% / n=18 | "0 emitted rows" | **Stale** — n=18 already exists; gap is sample size |

**Headline corrections to the Chinese report:**
1. The report's per-class current-state numbers are pre-resolver-v2 and pre-noise-filter. **Do not trust its severity table.**
2. FOREX is far worse than the report describes. Treat as P0, not P1.
3. ETF and BOND data pipelines are **not broken** (rows are emitting); the gap is sample-size / gating, not emit logic.
4. The Chinese report's *prescriptions* (gate composition, TP/SL ladders, four-tier WR bands, CTA 3-win activation) are mostly sound — only the diagnosis is dated.

**Single-pick launch candidate** (correcting the peer claim "it would be cotton"):
- **Cotton (CT=F) is BLACKLISTED** — 8.3% WR, −8.41% PnL, killed by PR #535. The peer was wrong.
- **Best single-symbol launch:** **HG=F (Copper)** — PF 2.17 / WR 44.9% / n=147 in COMMODITY's allowed universe.
- **Best whole-class launch:** **COMMODITY** — PF 2.08 / WR 48.7% / n=816, DSR=1.0000 (most validated edge). 1.3pp WR below T2 target.
- **Do NOT launch on `multi_asset_cot`** — its PF=12.16 / WR=81.3% (n=91) is currently flagged "implausible, DB-verify before any sizing" (PR #904 + DB_STOCKS_PASSWORD pending).

---

## 1. P0 — Ship within 7 days (blockers for any money-ready launch)

### P0-A · FOREX hard-cap sizing to 0 until PF ≥ 0.8 *(not silent kill — explicit per-class gate)*
- **Why:** Live FOREX PF 0.28; mutate-before-kill protocol still open. Repository is now leaking sized FOREX picks despite walk-forward Tier-1 block (`cf4e924744a`) — the gate exists at scoring, not at sizing.
- **Where:** `audit_trail/quality_gates.py` + `alpha_engine/sizing.py` — add per-class sizing gate keyed off `asset_class_health.profit_factor`.
- **Status today:** Open P0 cluster item in updates/index.html (lines 164, 239); **not** shipped. Buffy mutate-decisions already re-blocked the LONG side of `ig_contrarian_sentiment`, `myfxbook_retail_contrarian`, `quan_engine_swing` on 2026-05-11 (commit `a64e80e70d1`), but full sizing gate is missing.
- **Acceptance:** zero new FOREX picks sized > 0 until `asset_class_health.FOREX.profit_factor >= 0.8` for n ≥ 250 rolling.

### P0-B · BOND winner-filter unblock + symbol-universe expansion *(answers user's "would expanding universe help?" — yes, decisively)*
- **Root cause found by swarm:** `alpha_engine/forward_validator.py:395-466` hardcodes `allowed_asset_classes = ["crypto", "meme"]`. **All BOND picks are silently dropped at emission.** The fact that n=18 exists at all is upstream-historical, not currently flowing.
- **Action 1 (one-line fix):** add `"bond"` to `allowed_asset_classes`.
- **Action 2 (universe expansion):** current bond universe = TLT/IEF/LQD/HYG/JNK/EMB/TLH/MUB/BND (per `audit_daily.py:70-72`). Add TIP, AGG, SHY, VCIT, VCSH, BIL. Justification per ticker in swarm report.
- **Action 3 (wire the orphan):** `bond_inflation_rotation_v1` is registered in `BOND_STRATEGIES` dict but **the strategy file is missing** — research/P3 stub showed PF 1.99 / Sharpe 0.40 / MDD 5.5% on TIP (n=11, SMA-proxy). Either ship the real strategy or remove the dict entry per the Wire-Up Rule.
- **Action 4 (loosen gates exactly as Chinese report proposes for BOND):** Trust Floor −30%, Score Floor −20%, no WR Floor — but **only** after Action 1 ships (otherwise loosening gates does nothing because picks never reach gates).
- **Action 5 (Connors RSI2 on TLT/IEF/LQD):** swarm projects ~120 trades/yr from RSI2 alone; combined with credit-spread (LQD-HYG pair, already env-enabled via PR #545) → n=100 in **2–3 months**.
- **Acceptance:** BOND n ≥ 100 within 90 days, PF ≥ 1.5, WR ≥ 50%. Stretch: hit the report's 1.8–2.5 PF / 60–68% WR band.

### P0-C · CRYPTO source-volume cut *(refines Chinese P0-1; do NOT do a full Crypto rebuild)*
- **Why:** Report says PF 0.9 → rebuild everything. Reality: PF 1.26 already. Elite strategies (PF 2.34–3.97) are dragged by `quan_engine` (18% volume @ PF 0.70) + `unknown` (7% @ PF 0.35). Volume cut is enough; do not re-tune every elite.
- **Action 1:** cap `quan_engine` to 12% CRYPTO volume (open P0 in updates/index.html line 164).
- **Action 2:** route `source_system='unknown'` through `mutation_analysis.py` per TESTING_PROTOCOL.md §7 → if it can't be attributed, add to `BLOCKED_SOURCE_SYSTEMS`.
- **Action 3:** keep the Chinese report's source-weighting concept (Battleground 1.5x / Alpha 1.3x / Copy 1.0x / Roo 0.8x / ML Edge 0.7x) as a candidate for a **separate AB-test PR**, not bundled with the volume cut.
- **Action 4:** add 48h same-symbol cooldown **only for high-vol BTC/ETH** (per report's own risk #6). Low-vol alts get a 24h cap.
- **Acceptance:** CRYPTO PF crosses 1.5 (T2 candidacy) with no degradation in elite-strategy emission rate.

---

## 2. P1 — Ship within 2–4 weeks

### P1-A · FOREX composite ranking (Chinese report's `Final_Score = 0.4·WR + 0.3·Trust + 0.2·Score + 0.1·Liquidity`)
- **Status today:** `calculate_smart_score` in `quality_gates.py` uses 7-component additive scoring; **no WR weighting in final ranking.** Repository has long flagged "pure score ranking incorrectly ranks FX."
- **How to ship safely:** sidecar formula behind a feature flag (`FOREX_RANKING_V2`), A/B against current on closed Q2 2026 picks. Keep pure score as fallback per Chinese risk #3.
- **Acceptance:** A/B PnL parity + walk-forward consistency improves vs current; only then flip the flag.

### P1-B · EQUITY sample expansion *(matches Chinese P1-2)*
- Lower Smart Picks gate 85 → 78.
- Dynamic Trust: `base × (1 + log(n)/10)`.
- Early WR cut at n ≥ 10, threshold 48%.
- Wire through `passes_smart_gate` / `calculate_smart_score` per Wire-Up Rule.
- **Acceptance:** n=428 → n=600 within 4 weeks, PF ≥ 1.5 maintained.

### P1-C · ETF push to n ≥ 100 + PF ≥ 1.5
- Apply Chinese ETF-specific floors (Trust −20%, Score −15%, Smart Picks → 70) + min-hold ≥ 4h.
- Cross with separate updates/index.html proposal: add SPY/QQQ/IWM/XLF/GLD/TLT to `multi_asset_copytrader` eligibility (line 1606) — that proposal is real and pending.
- ETF was the **only** asset class with a surfaced signal in the research orchestrator's P5 verdicts (MIXED, not NO_EDGE) — there's edge to find here.

### P1-D · COMMODITY WR lift *(report P2)*
- PF 2.08 already meets T2; WR is 1.3pp short. Chinese report's "thin-coverage compensation" (WR +5%, Score +10%) and "CTA 3-win activation + first-trade SL halved" map well.
- **Caveat:** swarm flagged `multi_asset_cot` PF=12.16 / 19.19 contradiction across two reports. **Do NOT lean on this strategy for the WR lift until DB-verified** (PR #904, requires `DB_STOCKS_PASSWORD`).

---

## 3. P2 — Follow-up structural

- Forward validator allowlist refactor (`allowed_asset_classes` should be config-driven, not hardcoded).
- Walk-forward for BOND + ETF (open P1 in updates/index.html line 165).
- `performance_alerts` → auto-shadow-probation wire-up (proposed PR 3 in updates/index.html line 400).
- `tools/mutation_analysis.py` re-run quarterly for every class touching gates (TESTING_PROTOCOL §7).
- Update MAJOR GOAL banner in `audit_dashboard/template.html:808-820` to reflect FOREX-as-real-emergency framing once P0-A lands.

---

## 4. Single-pick launch — defensible answer

If we had to launch with one pick today:

| Tier | Choice | Evidence |
|---|---|---|
| **Single symbol** | **HG=F (Copper)** | PF 2.17, n=147, in already-restricted COMMODITY universe (PR #535) |
| **Class-level** | **COMMODITY** | PF 2.08, n=816, DSR=1.0000 (only T2-✓), walk-forward exists, no drift |
| **NEVER** | Cotton (CT=F) | KILLED at 8.3% WR / −8.41% PnL — peer claim was wrong |
| **NOT YET** | `multi_asset_cot` | Implausible PF 12.16/19.19 contradiction; DB verify first |
| **NOT YET** | `mega_mutation` / `st_fear_greed_contrarian` | Small sample, and `st_fear_greed_contrarian` is on the retired list but still zombie-emitting |

---

## 5. Risk register additions to the Chinese report

| # | New / refined risk | Mitigation |
|---|---|---|
| R1 | **Chinese report's diagnosis is stale by 19+ days and pre-resolver-v2.** | Use only its *prescriptions* (gates, TP/SL, formulas); discard its severity table. |
| R2 | **Cotton-style misclaims propagate fast in swarm output.** | All single-pick claims must cite per-symbol PF/WR/n from `dashboard_data.json` before adoption. |
| R3 | **FOREX silent leakage past walk-forward Tier-1 gate.** | Sizing gate (P0-A) closes the leak; banner update so future audits see real emergency. |
| R4 | **BOND emit looks healthy but is suppressed at forward_validator.** | One-line allowlist fix; audit other `allowed_asset_classes` constants for similar hardcodes. |
| R5 | **multi_asset_cot PF contradiction (12.16 vs 19.19) could anchor a wrong launch decision.** | Block any tier promotion until PR #904 DB query resolves. |

---

## 6. Mapping to existing `updates/index.html` entries

| Plan item | Already covered in updates/ | Gap this plan adds |
|---|---|---|
| P0-A FOREX sizing cap | Mentioned in master plan (line 164) + Cursor money-maker plan (line 261) — **not shipped** | Concrete acceptance criterion + sizing-gate location |
| P0-B BOND universe expansion | Hinted at line 1586/1606 (copy_trader ETF list incl. TLT) + research P3 stub line 353 | **Identifies forward_validator.py:395 winner-filter as the root cause** — net-new |
| P0-C CRYPTO source volume cut | Open P0 line 164 (`quan_engine` cap), Kimi P0 shipped (line 142) | Adds `unknown` source routing + cooldown carve-out for high-vol only |
| P1-A FOREX composite ranking | Repository note "pure score ranks FX wrong"; no PR yet | Concrete formula + A/B harness proposal |
| P1-B EQUITY sample expansion | Cursor plan Phase 2 (line 261) | Specific gate numbers (78, n≥10, 48%) |
| P1-C ETF n≥100 push | Cursor plan Phase 2 + research P5 MIXED verdict | Floor numbers + min-hold; ties to copy_trader eligibility |
| P1-D COMMODITY WR lift | Master plan Phase 2 | Adds blocker on `multi_asset_cot` DB verification |
| Single-pick launch | Kimi aggressive plan (line 283) implies EQUITY+COMMODITY now | This plan picks **HG=F** as the defensible single-symbol answer + warns off cotton |

No item in this plan **conflicts** with a shipped or in-flight updates/ entry. The plan slots cleanly above the existing money-maker plans (Cursor/Copilot/Kimi/Codex) as a verification + ordering pass.

---

## 7. Charter compliance gates before "real money"

Per `CLAUDE.md` MAJOR GOAL #1, real money requires:
- ≥ 2 asset classes at Tier-2 (PF > 1.5, WR > 50%, MDD < 20%) with n ≥ 100, walk-forward consistency ≥ 70%
- All P0 items above shipped + verified for 30 days out-of-sample
- FOREX **either** restored to PF ≥ 0.8 **or** explicitly excluded from sizing

Current proximity to gate:
- **COMMODITY:** ✓ PF, near-✓ WR (1.3pp gap), walk-forward consistency 34.8% (NOT yet at 70% — **gating risk**)
- **EQUITY:** near-✓ PF (1.42 vs 1.5), ✓ WR, walk-forward 87.5%
- **ETF:** PF 1.20 below T2 floor, ✓ WR, walk-forward 100% (small n)
- **BOND:** ✓ PF, ✓ WR, n=18 (below floor)

**Realistic 2-class T2 lineup at 60-day horizon:** EQUITY + COMMODITY *if* walk-forward consistency for COMMODITY can be lifted (regime-conditional sizing proposal in updates/ line 409 is the right thread). BOND can join the lineup at 90 days if P0-B ships now.
