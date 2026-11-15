# AUDIT_REPORT.md — Template

## 1. Executive Summary
- **Project:** Antigravity Trading System Audit
- **Audit date:** YYYY-MM-DD
- **Auditor:** [agent / team]
- **Bottom line:** [One sentence: "0/X strategies proven profitable" or "N strategies meet Phase 4 proof standard"]

---

## 2. Inventory of All Strategies Attempted

### 2.1 Table: Complete Strategy Registry

| # | Strategy name | Asset class(es) | Timeframe | Entry logic | Exit logic | TP / SL | Position sizing / risk mgmt | Statistical / ML methods used | Result observed | Suspected failure mode | File path(s) |
|---|---------------|-----------------|-----------|-------------|------------|---------|----------------------------|-------------------------------|-----------------|----------------------|--------------|
| 1 | | | | | | | | | | | |
| 2 | | | | | | | | | | | |
| … | | | | | | | | | | | |

> **Coverage required:** stocks, crypto, forex, bonds, ETFs, mutual funds, multi-asset rotation, copy-trading, prediction markets.

---

## 3. Forensic Failure Analysis

### 3.1 Failure Mode Taxonomy (with counts)

| Failure mode | Count | % of total | Representative strategies | Evidence |
|--------------|-------|------------|---------------------------|----------|
| 1. Overfitting / data snooping | | | | |
| 2. Look-ahead bias | | | | |
| 3. Survivorship / universe bias | | | | |
| 4. Unrealistic cost model | | | | |
| 5. Weak signal-to-noise ratio | | | | |
| 6. Regime dependence | | | | |
| 7. Implementation gap (backtest ≠ live) | | | | |
| 8. Insufficient sample size | | | | |
| 9. Wrong objective optimized | | | | |
| 10. Risk management failures | | | | |

### 3.2 Per-Strategy Failure Narrative
For each strategy with a non-obvious failure, write 2-3 sentences explaining **what went wrong and why**.

---

## 4. Catalogue of Methods Already Used

### 4.1 Statistical Methods
| Method | Where used (file path) | Purpose | Verdict (worked / failed / inconclusive) |
|--------|------------------------|---------|------------------------------------------|
| e.g., bootstrap CI | | | |

### 4.2 Risk-Management Methods
| Method | Where used | Purpose | Verdict |
|--------|------------|---------|---------|

### 4.3 Mathematical / Algorithmic Methods
| Method | Where used | Purpose | Verdict |
|--------|------------|---------|---------|

### 4.4 Machine-Learning Methods
| Method | Where used | Purpose | Verdict |
|--------|------------|---------|---------|

> **Purpose:** prevent re-proposing methods already tried.

---

## 5. Data Quality Assessment

| Issue | Severity | Affected strategies | Evidence | Mitigation status |
|-------|----------|---------------------|----------|-------------------|
| e.g., blank TP/SL in EQUITY | P0 | | | |
| e.g., fabricated flat PnL=0% | P0 | | | |
| e.g., stale / missing prices | P1 | | | |

---

## 6. Infrastructure Gaps

| Gap | Impact | Recommended fix | Priority |
|-----|--------|-----------------|----------|
| e.g., no walk-forward harness | Cannot prove OOS robustness | Build WFO wrapper | P0 |

---

## 7. Conclusions
- Total strategies audited:
- Strategies passing Phase 4 proof standard:
- Strategies warranting forward test:
- Strategies permanently rejected:
- Data blockers preventing audit completion:

---

## Appendix A: File Path Index
Alphabetical list of every file cited in this report.

## Appendix B: Glossary
Define any technical terms or abbreviations used.
