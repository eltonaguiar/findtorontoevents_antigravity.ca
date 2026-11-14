| MySQL Q-001 — Create picks table + sync from JSON | `mysql-q001-sync.yml` | active | annual/specific-month | 0 8 24 5 * | 2026-05-24 11:32:03 | 174.3 | within cadence |
| Forex Agent | `forex-agent.yml` | disabled_manually | weekly | 0 0,8,13,17 * * 1-5 | 2026-06-03 18:29:34 | 164.0 | within cadence |
| Forex Smart Picks Scanner | `forex-smart-picks.yml` | disabled_manually | weekly | 0 2,6,10,14,18,22 * * 1-5 | 2026-06-03 22:41:44 | 163.8 | within cadence |
| AI Tournament Pipeline — Daily Picks + DB Ingest | `ai-tournament-pipeline.yml` | disabled_manually | daily | 0 12 * * * | 2026-06-04 13:12:44 | 163.2 | within cadence |
| Real-Time Battle Test - Eliminate Losers, Optimize Winners | `battle_test.yml` | disabled_manually | intraday | 0 * * * * | 2026-06-13 01:39:52 | 154.7 | within cadence |
| POC Picks Checkpoint (2-week reminder) | `poc-picks-checkpoint.yml` | active | annual/specific-month | 0 21 18 7 *; 0 21 20 7 * | 2026-07-20 21:25:17 | 116.9 | within cadence |
| UEPS Value Resolver Quarterly | `value_resolver_quarterly.yml` | active | quarterly~ | 0 7 1 */3 * | 2026-10-01 07:25:25 | 44.4 | within cadence |
| Backup Restore Verification | `backup-verify.yml` | active | monthly | 0 6 15 * * | 2026-10-15 09:11:26 | 30.4 | within cadence |
| ML Monthly Full Retrain | `ml-monthly-retrain.yml` | active | monthly | 0 4 1 * * | 2026-11-01 04:01:08 | 13.6 | within cadence |
| Beta Portfolio Refresh (monthly) | `beta-portfolio-refresh.yml` | active | monthly | 20 6 1 * * | 2026-11-01 06:29:57 | 13.5 | within cadence |
| Monthly DNA Tournament | `monthly-tournament.yml` | active | monthly | 0 6 1 * * | 2026-11-01 06:13:31 | 13.5 | within cadence |
| Monthly Confidence Calibrator Refit (M-060) | `monthly-calibrator-refit.yml` | active | monthly | 0 7 1 * * | 2026-11-01 07:05:33 | 13.4 | within cadence |
| Secret Rotation Reminder | `secret-rotation-reminder.yml` | active | monthly | 0 9 1 * * | 2026-11-01 09:07:09 | 13.4 | within cadence |
| H-103 Forward Logger | `h103-forward-logger.yml` | active | monthly | 0 14 1 * * | 2026-11-01 14:01:39 | 13.2 | within cadence |