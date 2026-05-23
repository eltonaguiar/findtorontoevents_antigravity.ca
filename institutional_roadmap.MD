# Institutional Roadmap

## Enhancements Overview
This document outlines the planned enhancements to move the prediction system toward institutional-grade performance across asset classes. Each enhancement is tied to measurable goals and projected completion dates (EST).

## Key Enhancements
1. **Secure Credential Management**
   - Implement Windows environment variable integration for `DB_PASS_STOCKS` and `DB_PASS_BACKTESTS`.
   - Rotate credentials quarterly and log access for audit compliance.

2. **CI/CD Pipeline Optimization**
   - Add GitHub Actions jobs for automated backtesting using MySQL databases.
   - Introduce path-based triggers to prevent infinite deployment loops.
   - Integrate GPU-accelerated testing (CUDA) for model inference validation.

3. **Database Integration**
   - Use ORM (SQLAlchemy) for safe query construction.
   - Add connection pooling and retry logic for MySQL interactions.
   - Implement data integrity checks between `ejaguiar1_stocks` and `ejaguiar1_backtests`.

4. **Performance Monitoring**
   - Deploy centralized logging for database queries and GitHub Actions runs.
   - Monitor query performance with MySQL Performance Schema.
   - Set up alerts for failed jobs or connection issues.

5. **GPU-Accelerated Workflows**
   - Enable GPU-enabled runners for CUDA-based model testing.
   - Use RAPIDS cuDF for accelerated data preprocessing.
   - Collect and upload GPU performance metrics as artifacts.

6. **Institutional-Level Quality Gates**
   - Implement PCG-5 portfolio construction gates with strict risk limits.
   - Add drift detection and auto-pause mechanisms.
   - Integrate institutional-grade backtesting (CPCV) for small-n cohorts.

## Projected Institutional Readiness by Asset Class

| Asset Class | Current Status | Projected EST for Institutional Quality* | Key Milestones |
|-------------|--------------|----------------------------------------|----------------|
| COMMODITY | Strong edge (PF ~3.94, WR 67.8%) | **2026-06-15** | - Complete PCG-5 gate integration<br>- Validate with 90-day walk-forward<br>- Achieve MDD ≤10% |
| CRYPTO | High volume, PF ~1.36, WR 46.5% | **2026-08-30** | - Implement institutional-grade backtesting (CPCV)<br>- Tighten risk gates (MDD ≤10%)<br>- Secure credential rotation |
| EQUITY | Moderate edge (PF 1.55, WR 53.2%) | **2026-09-15** | - Expand feature set with macro indicators<br>- Validate with institutional backtesting<br>- Achieve PF ≥2.0 |
| FOREX | Toxic (PF 0.29) | **2026-11-01** | - Resolve liquidity and spread issues<br>- Implement COT reversal gates<br>- Achieve PF ≥1.5 |
| BOND | Thin (n=11, PF 0.66) | **2026-10-15** | - Expand universe (TLT/IEF)<br>- Add macro feature engineering<br>- Achieve WR ≥55% |
| FUTURES | Dead (no active signals) | **2026-12-01** | - Revive with new data sources<br>- Implement seasonal strategies<br>- Achieve PF ≥2.0 |

\*Projected dates assume timely completion of enhancements and no major setbacks.

## Success Metrics
- **Institutional Quality Definition**: PF ≥2.0, WR ≥55%, MDD ≤10%, n ≥200 per asset class.
- **Performance Validation**: 90-day walk-forward backtest with out-of-sample data.
- **Risk Compliance**: All positions must pass PCG-5 gates before live deployment.

## Next Steps
- Prioritize secure credential management and CI/CD pipeline enhancements.
- Begin GPU-accelerated workflow trials for model inference.
- Initiate institutional-grade backtesting for COMMODITY and CRYPTO.