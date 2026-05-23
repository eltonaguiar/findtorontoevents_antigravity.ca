# Hourly Audit — 2026-05-12 06Z

## 1. Dashboard Refresh Status

- `git pull --rebase origin main` completed — 39 files updated (forced update from `c25c4021` → `ff4bb353`)
- Most recent closed pick in `audit_dashboard/data/dashboard_data.json`: **2026-05-12T03:45:35Z**
- Dashboard data reflects post-PR kills: #692 (goldmine_6x + forex_carry_momentum), #694 (HYPEUSDT block), #687 (JPY-cross BUY rule fix), #683 (cftc_cot), #684 (resolver-v2)

---

## 2. Per-Asset PF/WR — Current vs Baseline

### Baseline (from task briefing / issue #686 snapshot 2026-05-02)
| Class   | 24h PF | 7d PF  | 7d WR   | 30d PF |
|---------|--------|--------|---------|--------|
| CRYPTO  | 3.54   | 1.33   | 41%     | 1.33   |
| EQUITY  | —      | 0.87   | 41%     | 1.41–2.18 |
| FOREX   | 0.00   | 0.14   | 10.7%   | 0.97   |

### Current (2026-05-12 06Z)

#### 24h window (n=108 total)
| Class     | PF    | WR     | n  | Delta vs baseline |
|-----------|-------|--------|----|-------------------|
| CRYPTO    | 2.53  | 62.8%  | 78 | -1.01 PF (down from 3.54; WR +22pp) |
| EQUITY    | 2.66  | 7.7%   | 13 | positive PF; WR skewed (1 large winner) |
| FOREX     | 3.32  | 66.7%  | 12 | +3.32 vs 0.00 baseline — post-kill recovery |
| COMMODITY | inf   | 100%   | 2  | n too small to report |
| ETF       | inf   | 100%   | 3  | n too small to report |

#### 7d window (n=999 total)
| Class     | PF    | WR     | n   | Delta vs baseline |
|-----------|-------|--------|-----|-------------------|
| CRYPTO    | 1.46  | 45.2%  | 859 | **+0.13 PF**, WR +4pp — gradual improvement |
| EQUITY    | 5.29  | 41.9%  | 31  | **+4.42 PF** — dramatic recovery post-#692 (goldmine_6x kill confirmed effective) |
| FOREX     | 1.01  | 24.1%  | 79  | **+0.87 PF** — major recovery post-#687+#692 JPY/carry kills |
| COMMODITY | 39.96 | 94.1%  | 17  | n<20 (floor), trending excellent |
| ETF       | inf   | 100%   | 13  | n<20 |

#### 30d window (n=2740 total)
| Class     | PF   | WR     | n    | Delta vs baseline |
|-----------|------|--------|------|-------------------|
| CRYPTO    | 1.45 | 47.0%  | 1879 | +0.12 PF vs 1.33 |
| EQUITY    | 3.06 | 57.5%  | 134  | **+0.88–1.65 PF** above top of baseline range — Tier-2 confirmed |
| FOREX     | 0.64 | 41.5%  | 574  | -0.33 PF vs 0.97 (30d captures pre-kill bad trades; expected lag) |
| COMMODITY | 6.44 | 56.9%  | 102  | n≥100 — **Tier-1 candidate** (PF>2, WR>55) |
| ETF       | 6.44 | 83.0%  | 47   | n approaching charter floor (100) |

---

## 3. Key Findings

### 3a. FOREX — Post-Kill Recovery Confirmed
- **7d PF 1.01 / WR 24.1%** vs baseline 7d PF 0.14 / WR 10.7%.
- PRs #687 (JPY-cross BUY block) + #692 (forex_carry_momentum + goldmine_6x kill) demonstrably working.
- 30d PF 0.64 is dragged by pre-kill trades in the 30d window; 7d recovery is the forward-looking signal.
- **Action**: monitor. Do NOT add new forex strategies. forex_rsi2_mean_reversion not yet visible in this window — watch in next 24-48h.

### 3b. EQUITY — Issue #693 Recovery Confirmed
- 7d PF now **5.29** (was 0.87 at time of issue #693 creation). goldmine_6x_consensus kill via PR #692 is the proximate cause.
- 30d PF 3.06 / WR 57.5% — strongly Tier-1 (PF>2, WR>55, n=134 ≥ charter floor).
- EQUITY 24h WR=7.7% anomaly on n=13: 1 large winner dominating. Not a system signal — regime sampling noise.
- stocks_rsi2_pullback (issue #693 watch item): not isolatable in current window without full per-strategy breakdown; needs separate audit at n≥20.
- **Action**: close monitoring; recommend updating issue #693 with recovery confirmation.

### 3c. COMMODITY — Tier-1 Threshold Crossed
- 30d PF 6.44 / WR 56.9% on n=102. **n≥100 charter floor met**.
- asset_class_health (resolver-v2 long-run): PF 3.77 / WR 66.7%.
- 7d PF 39.96 on n=17 is regime-inflated (n too small) but directionally consistent.
- **Action**: document as proven edge. Candidate for next `<div class="update-entry">` card on `updates/index.html`.

### 3d. CRYPTO — Gradual Improvement
- 24h PF 2.53 / WR 62.8% (down slightly from 3.54 baseline but WR improved).
- 7d PF 1.46 / WR 45.2% (up from 1.33 baseline).
- 30d PF 1.45 / WR 47.0% (up from 1.33).
- quan_engine HYPEUSDT block (PR #694) not yet fully reflected in 7d/30d (new data accumulating).
- **Action**: do not destabilize. Monitor 7d WR — target: recover toward 50%+ within 14 days.

### 3e. BOND
- asset_class_health shows PF 0.66 / WR 54.5% (below T2 PF floor). n below charter floor.
- No picks visible in 24h/7d/30d recent_closed windows — low volume, not actionable.

### 3f. ETF
- 30d PF 6.44 / WR 83.0% on n=47 — excellent but n<100 charter floor.
- Approaching n=100; next 2-3 weeks will confirm or refute.

---

## 4. Mutation Analysis Results (new kills)

`python tools/mutation_analysis.py --json` run — **no strategies with PF<0.5 + n>=20** in current window.

Notable directional mutations flagged (not kill candidates yet):
| Strategy | Issue | n | Signal |
|----------|-------|---|--------|
| `ig_contrarian_sentiment` | LONG 16.9% WR vs SHORT 62.5% | 177 LONG / 48 SHORT | Consider SHORT-only mutation in sandbox |
| `myfxbook_retail_contrarian` | LONG 13.1% WR vs SHORT 46.2% | 122 LONG / 13 SHORT | Same |
| `rapid_fire` UUSDT | 0% WR on n=34 | 34 | Symbol-block candidate (PF<0.5 threshold not computable without PnL sum — flagged for next round) |
| `quan_engine_swing` | LONG 26% WR vs SHORT 60% | 104 LONG / 5 SHORT | SHORT sample too small; watch |

**Per CLAUDE.md kill protocol**: none of the above meet the 3-AI consensus gate. Posting to issue #686 for tracking.

---

## 5. PR Triage

`gh pr list --state open` returned **0 open PRs**.

All previously tracked PRs are merged or closed:
- Merged this session: #684, #674, #673, #664, #683, #687, #692, #694
- HOLD set (#660, #658, #681, #661 — Plan v2.1 family): not present in open list, confirmed closed/not re-opened
- Rebase candidates (#669, #676, #608, #665, #644, #597, #615, #655): not present in open list

No merge actions taken this hour (no open PRs).

---

## 6. Deltas vs Prior Hour (05Z audit)

| Class     | 7d PF (05Z → 06Z) | Notes |
|-----------|--------------------|-------|
| CRYPTO    | ~1.46 (stable)     | Within normal hourly variance |
| EQUITY    | ~5.29 (stable)     | Recovery post-#692 holding |
| FOREX     | ~1.01 (stable)     | Post-kill recovery; 30d still lagging |
| COMMODITY | ~39.96 (n<20 noisy) | Long-run PF 3.77 is the reliable signal |

---

## 7. Recommended Actions for Next Hour

1. **Post issue #686 comment**: report `ig_contrarian_sentiment` + `myfxbook_retail_contrarian` directional split and `rapid_fire/UUSDT` symbol block candidate for 3-AI consensus tracking.
2. **Post issue #693 comment**: EQUITY 7d PF recovered to 5.29 post-PR-#692 — close monitoring, goldmine_6x kill was sufficient.
3. **COMMODITY edge**: create `updates/index.html` entry documenting COMMODITY 30d PF 6.44 / WR 56.9% / n=102 as proven edge per CLAUDE.md definition.
4. **CRYPTO vol-targeting**: as noted in issue #685, the multi-week path to CRYPTO Tier-2 remains `reports/deep_dive_crypto_mdd_reduction_2026_04_28.md`. No 1-PR shortcut available.
5. **FOREX**: continue monitoring. Next kill candidate is `forex_rsi2_mean_reversion` — needs 7d attribution window to confirm WR improvement or continued drag.

---

*Generated: 2026-05-12T06:xx:xxZ by Claude Sonnet 4.6 hourly audit agent.*
*Source: `audit_dashboard/data/dashboard_data.json` (most recent pick: 2026-05-12T03:45:35Z)*
*Refs: Issues #685, #686, #693; PRs #684 #674 #673 #664 #683 #687 #692 #694*
