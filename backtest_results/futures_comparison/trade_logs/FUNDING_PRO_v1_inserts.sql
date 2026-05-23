-- Trade log for FUNDING_PRO_v1
-- Generated: 2026-03-08T18:36:22.472211
-- Total trades: 567


INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'AF7E9CAED4E2763F', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2020-01-01 21:00:00', '2020-01-02 08:48:19', 3986.56057464, 4002.38385518,
    4046.35898326, 3886.89656027, 0.1194,
    -0.3969, -4.74, 'TIME_EXIT', 11.81,
    0, '1h', '2026-03-08T18:36:22.451963'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3969,
    pnl_amount = -4.74,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '23D1DF64CD8D4E57', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2020-01-04 11:00:00', '2020-01-04 22:30:56', 3356.66525944, 3387.24954145,
    3306.31528055, 3440.58189093, 0.0967,
    0.9112, 8.81, 'TIME_EXIT', 11.52,
    1, '1h', '2026-03-08T18:36:22.449056'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9112,
    pnl_amount = 8.81,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2AABB350E2F1EB8A', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2020-01-09 02:00:00', '2020-01-09 09:55:15', 1608.74490879, 1616.76223379,
    1584.61373516, 1648.96353151, 0.1013,
    0.4984, 5.05, 'TIME_EXIT', 7.92,
    1, '1h', '2026-03-08T18:36:22.453975'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4984,
    pnl_amount = 5.05,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3DF52BEDFCE6DF09', 'FUNDING_PRO_v1', 'DOGEUSDT', 'SHORT',
    '2020-01-14 20:00:00', '2020-01-15 06:57:08', 4563.1205149, 4524.20739303,
    4631.56732262, 4449.04250202, 0.1045,
    0.8528, 8.91, 'TAKE_PROFIT', 10.95,
    1, '1h', '2026-03-08T18:36:22.449711'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8528,
    pnl_amount = 8.91,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1EF14F08DACF1EEA', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2020-01-17 19:00:00', '2020-01-17 23:26:03', 584.0252997, 589.11307336,
    575.26492021, 598.62593219, 0.0863,
    0.8712, 7.52, 'TRAILING_STOP', 4.43,
    1, '1h', '2026-03-08T18:36:22.449914'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8712,
    pnl_amount = 7.52,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '36C7A19D8CBF3678', 'FUNDING_PRO_v1', 'ADAUSDT', 'SHORT',
    '2020-01-19 11:00:00', '2020-01-19 22:43:10', 1085.60816111, 1075.67983771,
    1101.89228353, 1058.46795709, 0.098,
    0.9145, 8.96, 'TIME_EXIT', 11.72,
    1, '1h', '2026-03-08T18:36:22.450061'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9145,
    pnl_amount = 8.96,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BCB3F8CA84107642', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2020-01-22 15:00:00', '2020-01-22 21:18:31', 4552.96383748, 4574.47659814,
    4621.25829504, 4439.13974154, 0.0938,
    -0.4725, -4.43, 'STOP_LOSS', 6.31,
    0, '1h', '2026-03-08T18:36:22.452903'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4725,
    pnl_amount = -4.43,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FBEEE7E00192A0D8', 'FUNDING_PRO_v1', 'BNBUSDT', 'SHORT',
    '2020-01-23 07:00:00', '2020-01-23 12:07:05', 993.08318321, 997.3983312,
    1007.97943096, 968.25610363, 0.0949,
    -0.4345, -4.12, 'STOP_LOSS', 5.12,
    0, '1h', '2026-03-08T18:36:22.453789'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4345,
    pnl_amount = -4.12,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2BBA70FB1D17464A', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2020-01-26 03:00:00', '2020-01-26 08:00:22', 4950.58185103, 4996.34168537,
    4876.32312326, 5074.3463973, 0.0857,
    0.9243, 7.92, 'TIME_EXIT', 5.01,
    1, '1h', '2026-03-08T18:36:22.450978'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9243,
    pnl_amount = 7.92,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DEFCC9CF92A3E090', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2020-01-26 07:00:00', '2020-01-26 13:33:24', 28802.45017411, 28951.77347665,
    28370.41342149, 29522.51142846, 0.0832,
    0.5184, 4.31, 'TRAILING_STOP', 6.56,
    1, '1h', '2026-03-08T18:36:22.449545'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5184,
    pnl_amount = 4.31,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6B3F77BB87A41F8F', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2020-02-02 18:00:00', '2020-02-02 22:48:29', 2289.29452806, 2281.84313623,
    2254.95511014, 2346.52689127, 0.0802,
    -0.3255, -2.61, 'STOP_LOSS', 4.81,
    0, '1h', '2026-03-08T18:36:22.454439'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3255,
    pnl_amount = -2.61,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '49193B7232014958', 'FUNDING_PRO_v1', 'XRPUSDT', 'LONG',
    '2020-02-05 12:00:00', '2020-02-05 23:21:50', 3278.15537667, 3265.24934254,
    3228.98304602, 3360.10926108, 0.1067,
    -0.3937, -4.2, 'STOP_LOSS', 11.36,
    0, '1h', '2026-03-08T18:36:22.453626'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3937,
    pnl_amount = -4.2,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2C24A790615787C0', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2020-02-05 21:00:00', '2020-02-06 01:51:55', 27386.53931656, 27495.27843002,
    27797.33740631, 26701.87583364, 0.0916,
    -0.3971, -3.64, 'TIME_EXIT', 4.87,
    0, '1h', '2026-03-08T18:36:22.449132'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3971,
    pnl_amount = -3.64,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'CCEE9CAB6D27AD21', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2020-02-07 08:00:00', '2020-02-07 13:20:34', 4788.39984818, 4807.31118308,
    4860.22584591, 4668.68985198, 0.0832,
    -0.3949, -3.29, 'STOP_LOSS', 5.34,
    0, '1h', '2026-03-08T18:36:22.448957'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3949,
    pnl_amount = -3.29,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C70054A610951F84', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2020-02-07 12:00:00', '2020-02-07 14:27:35', 23219.79865028, 23137.79881485,
    22871.50167052, 23800.29361654, 0.0801,
    -0.3531, -2.83, 'STOP_LOSS', 2.46,
    0, '1h', '2026-03-08T18:36:22.450287'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3531,
    pnl_amount = -2.83,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EE910F5A1AA441D7', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2020-02-11 02:00:00', '2020-02-11 04:52:43', 4367.52190054, 4341.82194186,
    4433.03472905, 4258.33385303, 0.0945,
    0.5884, 5.56, 'TIME_EXIT', 2.88,
    1, '1h', '2026-03-08T18:36:22.449330'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5884,
    pnl_amount = 5.56,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '350C1558538B9ABB', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2020-02-14 08:00:00', '2020-02-14 17:40:28', 502.74311496, 505.41799618,
    495.20196824, 515.31169284, 0.0862,
    0.5321, 4.59, 'TIME_EXIT', 9.67,
    1, '1h', '2026-03-08T18:36:22.452732'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5321,
    pnl_amount = 4.59,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '23A5E427B715111A', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2020-02-17 02:00:00', '2020-02-17 04:59:40', 1561.92724272, 1556.04776838,
    1538.49833408, 1600.97542378, 0.0956,
    -0.3764, -3.6, 'TIME_EXIT', 2.99,
    0, '1h', '2026-03-08T18:36:22.451241'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3764,
    pnl_amount = -3.6,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'ACB4610BF531B3DF', 'FUNDING_PRO_v1', 'DOGEUSDT', 'LONG',
    '2020-02-25 22:00:00', '2020-02-26 08:30:18', 4664.7472511, 4644.86868538,
    4594.77604233, 4781.36593238, 0.0906,
    -0.4261, -3.86, 'STOP_LOSS', 10.51,
    0, '1h', '2026-03-08T18:36:22.449620'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4261,
    pnl_amount = -3.86,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6F421F0209F48743', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2020-03-13 06:00:00', '2020-03-13 10:14:18', 26666.43949317, 26442.00900523,
    27066.43608557, 25999.77850585, 0.1176,
    0.8416, 9.9, 'TIME_EXIT', 4.24,
    1, '1h', '2026-03-08T18:36:22.453671'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8416,
    pnl_amount = 9.9,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '75D6F69653660A95', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2020-03-13 11:00:00', '2020-03-13 18:33:19', 1451.20600877, 1462.72828932,
    1429.43791864, 1487.48615899, 0.1103,
    0.794, 8.76, 'TAKE_PROFIT', 7.56,
    1, '1h', '2026-03-08T18:36:22.450645'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.794,
    pnl_amount = 8.76,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '50E53C02B05BBCD5', 'FUNDING_PRO_v1', 'AVAXUSDT', 'LONG',
    '2020-03-16 15:00:00', '2020-03-16 18:23:57', 4702.15773434, 4687.0296447,
    4631.62536833, 4819.7116777, 0.1129,
    -0.3217, -3.63, 'STOP_LOSS', 3.4,
    0, '1h', '2026-03-08T18:36:22.453779'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3217,
    pnl_amount = -3.63,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'CA54FF7A0EA6C449', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2020-03-18 19:00:00', '2020-03-18 22:37:01', 1589.01987703, 1574.14789488,
    1612.85517519, 1549.29438011, 0.0886,
    0.9359, 8.29, 'TAKE_PROFIT', 3.62,
    1, '1h', '2026-03-08T18:36:22.449629'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9359,
    pnl_amount = 8.29,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '75C35DE16A83A339', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2020-03-20 22:00:00', '2020-03-21 04:59:28', 36032.86950795, 36274.77248577,
    35492.37646533, 36933.69124564, 0.1188,
    0.6713, 7.97, 'TRAILING_STOP', 6.99,
    1, '1h', '2026-03-08T18:36:22.449198'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6713,
    pnl_amount = 7.97,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7A981E668A78B959', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2020-03-21 07:00:00', '2020-03-21 11:05:32', 2361.31264964, 2351.1988769,
    2325.8929599, 2420.34546588, 0.0863,
    -0.4283, -3.69, 'TIME_EXIT', 4.09,
    0, '1h', '2026-03-08T18:36:22.452854'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4283,
    pnl_amount = -3.69,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '09978DEC4F92A962', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2020-03-23 16:00:00', '2020-03-24 01:42:56', 748.79257332, 745.85410544,
    737.56068472, 767.51238765, 0.0964,
    -0.3924, -3.78, 'STOP_LOSS', 9.72,
    0, '1h', '2026-03-08T18:36:22.454489'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3924,
    pnl_amount = -3.78,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4EB81570AF218CBE', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2020-03-29 09:00:00', '2020-03-29 11:31:06', 18476.36263906, 18409.91429475,
    18199.21719948, 18938.27170504, 0.1,
    -0.3596, -3.6, 'TIME_EXIT', 2.52,
    0, '1h', '2026-03-08T18:36:22.450942'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3596,
    pnl_amount = -3.6,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '164BA79293FA856C', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2020-04-05 11:00:00', '2020-04-05 22:23:37', 352.66870098, 351.04991347,
    347.37867046, 361.4854185, 0.1016,
    -0.459, -4.66, 'TIME_EXIT', 11.39,
    0, '1h', '2026-03-08T18:36:22.449104'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.459,
    pnl_amount = -4.66,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '99075C7D4BC9CA01', 'FUNDING_PRO_v1', 'AVAXUSDT', 'LONG',
    '2020-04-08 10:00:00', '2020-04-08 14:56:22', 3556.34986243, 3574.42858992,
    3503.0046145, 3645.25860899, 0.1054,
    0.5084, 5.36, 'TRAILING_STOP', 4.94,
    1, '1h', '2026-03-08T18:36:22.451695'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5084,
    pnl_amount = 5.36,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A211F2CE13BD42AB', 'FUNDING_PRO_v1', 'ADAUSDT', 'SHORT',
    '2020-04-09 08:00:00', '2020-04-09 18:32:02', 4378.56656518, 4350.07775413,
    4444.24506366, 4269.10240105, 0.1141,
    0.6506, 7.42, 'TAKE_PROFIT', 10.53,
    1, '1h', '2026-03-08T18:36:22.451343'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6506,
    pnl_amount = 7.42,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1E2699490336C76B', 'FUNDING_PRO_v1', 'DOGEUSDT', 'LONG',
    '2020-04-11 01:00:00', '2020-04-11 06:44:45', 4539.31043928, 4573.98349686,
    4471.22078269, 4652.79320026, 0.1012,
    0.7638, 7.73, 'TRAILING_STOP', 5.75,
    1, '1h', '2026-03-08T18:36:22.453746'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7638,
    pnl_amount = 7.73,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '67D5F86A02408876', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2020-04-12 17:00:00', '2020-04-12 21:06:11', 19207.63370917, 19134.15625321,
    18919.51920354, 19687.8245519, 0.0993,
    -0.3825, -3.8, 'STOP_LOSS', 4.1,
    0, '1h', '2026-03-08T18:36:22.450475'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3825,
    pnl_amount = -3.8,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '903BCDBE6D24BDCE', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2020-04-25 11:00:00', '2020-04-25 13:11:21', 3420.55598696, 3400.91127285,
    3471.86432677, 3335.04208729, 0.0981,
    0.5743, 5.63, 'TRAILING_STOP', 2.19,
    1, '1h', '2026-03-08T18:36:22.450385'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5743,
    pnl_amount = 5.63,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4397EFCD169B2955', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2020-04-26 22:00:00', '2020-04-27 01:29:54', 13592.94315283, 13481.7806885,
    13796.83730012, 13253.11957401, 0.1084,
    0.8178, 8.87, 'TIME_EXIT', 3.5,
    1, '1h', '2026-03-08T18:36:22.452635'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8178,
    pnl_amount = 8.87,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1FFBC7FE187C39B2', 'FUNDING_PRO_v1', 'AVAXUSDT', 'SHORT',
    '2020-04-27 04:00:00', '2020-04-27 07:48:53', 1270.30436737, 1259.84531811,
    1289.35893288, 1238.54675819, 0.1118,
    0.8233, 9.2, 'TIME_EXIT', 3.81,
    1, '1h', '2026-03-08T18:36:22.450430'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8233,
    pnl_amount = 9.2,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EA4D82D67E65FB63', 'FUNDING_PRO_v1', 'DOGEUSDT', 'LONG',
    '2020-04-30 03:00:00', '2020-04-30 11:26:54', 4077.03090339, 4102.66486358,
    4015.87543984, 4178.95667598, 0.0901,
    0.6287, 5.66, 'TIME_EXIT', 8.45,
    1, '1h', '2026-03-08T18:36:22.453853'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6287,
    pnl_amount = 5.66,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E77B8B486D8D97C7', 'FUNDING_PRO_v1', 'AVAXUSDT', 'SHORT',
    '2020-05-03 13:00:00', '2020-05-03 19:10:04', 4234.81183775, 4200.26665821,
    4298.33401531, 4128.9415418, 0.0839,
    0.8157, 6.84, 'TAKE_PROFIT', 6.17,
    1, '1h', '2026-03-08T18:36:22.450849'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8157,
    pnl_amount = 6.84,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0261916D80958DBE', 'FUNDING_PRO_v1', 'DOTUSDT', 'LONG',
    '2020-05-06 13:00:00', '2020-05-06 20:49:02', 4572.78226085, 4555.79454648,
    4504.19052694, 4687.10181738, 0.1003,
    -0.3715, -3.73, 'TIME_EXIT', 7.82,
    0, '1h', '2026-03-08T18:36:22.453195'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3715,
    pnl_amount = -3.73,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '940EFC8E156F4744', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2020-05-10 18:00:00', '2020-05-10 22:38:29', 1914.44539834, 1905.3652498,
    1885.72871736, 1962.3065333, 0.0975,
    -0.4743, -4.62, 'TIME_EXIT', 4.64,
    0, '1h', '2026-03-08T18:36:22.452864'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4743,
    pnl_amount = -4.62,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E1283CDA9D943812', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2020-05-12 15:00:00', '2020-05-12 19:13:31', 45491.70376242, 45098.45103317,
    46174.07931886, 44354.41116836, 0.0822,
    0.8644, 7.1, 'TAKE_PROFIT', 4.23,
    1, '1h', '2026-03-08T18:36:22.450988'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8644,
    pnl_amount = 7.1,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '35BFA32ECE514EEB', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2020-05-18 16:00:00', '2020-05-19 00:54:21', 4185.47394032, 4170.2032113,
    4122.69183121, 4290.11078883, 0.1075,
    -0.3649, -3.92, 'STOP_LOSS', 8.91,
    0, '1h', '2026-03-08T18:36:22.453359'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3649,
    pnl_amount = -3.92,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E8B1B180741826B8', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2020-05-19 11:00:00', '2020-05-19 17:39:25', 940.77401279, 934.45120621,
    954.88562298, 917.25466247, 0.0936,
    0.6721, 6.29, 'TIME_EXIT', 6.66,
    1, '1h', '2026-03-08T18:36:22.450951'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6721,
    pnl_amount = 6.29,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '94B775D1A21CEC26', 'FUNDING_PRO_v1', 'XRPUSDT', 'SHORT',
    '2020-05-19 14:00:00', '2020-05-19 22:38:40', 3157.9440904, 3170.16938121,
    3205.31325176, 3078.99548814, 0.1164,
    -0.3871, -4.51, 'STOP_LOSS', 8.64,
    0, '1h', '2026-03-08T18:36:22.450133'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3871,
    pnl_amount = -4.51,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6AC5472F26CCAEBA', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2020-05-23 19:00:00', '2020-05-24 03:24:02', 376.44418884, 379.15802664,
    370.797526, 385.85529356, 0.1065,
    0.7209, 7.68, 'TRAILING_STOP', 8.4,
    1, '1h', '2026-03-08T18:36:22.452817'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7209,
    pnl_amount = 7.68,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '67FCAEA52FAC6209', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2020-05-24 22:00:00', '2020-05-25 02:48:16', 26362.69665923, 26555.03628873,
    25967.25620935, 27021.76407571, 0.0957,
    0.7296, 6.99, 'TRAILING_STOP', 4.8,
    1, '1h', '2026-03-08T18:36:22.453176'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7296,
    pnl_amount = 6.99,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '51CC35F318DE2C59', 'FUNDING_PRO_v1', 'ADAUSDT', 'LONG',
    '2020-05-30 11:00:00', '2020-05-30 13:51:47', 3613.43663446, 3598.89533489,
    3559.23508494, 3703.77255032, 0.0839,
    -0.4024, -3.38, 'TIME_EXIT', 2.86,
    0, '1h', '2026-03-08T18:36:22.452254'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4024,
    pnl_amount = -3.38,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B7DD59EB15F2DD61', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2020-06-01 04:00:00', '2020-06-01 06:19:15', 3501.22028355, 3487.86278621,
    3448.7019793, 3588.75079064, 0.0938,
    -0.3815, -3.58, 'STOP_LOSS', 2.32,
    0, '1h', '2026-03-08T18:36:22.449602'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3815,
    pnl_amount = -3.58,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3BBC410655453B07', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2020-06-07 07:00:00', '2020-06-07 12:53:31', 285.54428647, 284.2550891,
    281.26112218, 292.68289364, 0.1192,
    -0.4515, -5.38, 'STOP_LOSS', 5.89,
    0, '1h', '2026-03-08T18:36:22.450014'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4515,
    pnl_amount = -5.38,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '59DC02260CED376A', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2020-06-10 03:00:00', '2020-06-10 11:43:03', 28308.65018862, 28176.16888922,
    27884.02043579, 29016.36644333, 0.0914,
    -0.468, -4.28, 'TIME_EXIT', 8.72,
    0, '1h', '2026-03-08T18:36:22.451731'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.468,
    pnl_amount = -4.28,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2DFE72B576D88E4D', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2020-06-16 00:00:00', '2020-06-16 06:25:14', 852.52493259, 857.21502674,
    839.7370586, 873.8380559, 0.1184,
    0.5501, 6.51, 'TIME_EXIT', 6.42,
    1, '1h', '2026-03-08T18:36:22.449339'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5501,
    pnl_amount = 6.51,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4C01ED373639D5B9', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2020-06-18 03:00:00', '2020-06-18 13:57:56', 1107.78707847, 1102.64983775,
    1091.17027229, 1135.48175543, 0.1033,
    -0.4637, -4.79, 'TIME_EXIT', 10.97,
    0, '1h', '2026-03-08T18:36:22.452335'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4637,
    pnl_amount = -4.79,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9DC9CE58792C81AB', 'FUNDING_PRO_v1', 'DOGEUSDT', 'LONG',
    '2020-06-20 03:00:00', '2020-06-20 13:13:39', 1527.16575835, 1539.31322253,
    1504.25827198, 1565.34490231, 0.1104,
    0.7954, 8.78, 'TAKE_PROFIT', 10.23,
    1, '1h', '2026-03-08T18:36:22.453521'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7954,
    pnl_amount = 8.78,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9057C068B8774EB9', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2020-06-20 09:00:00', '2020-06-20 11:10:03', 4023.60583681, 4036.7194347,
    4083.95992437, 3923.01569089, 0.1164,
    -0.3259, -3.79, 'STOP_LOSS', 2.17,
    0, '1h', '2026-03-08T18:36:22.452891'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3259,
    pnl_amount = -3.79,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A449124E1FD8DA3E', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2020-06-28 20:00:00', '2020-06-29 02:06:53', 3437.92156747, 3411.38025051,
    3489.49039098, 3351.97352828, 0.1132,
    0.772, 8.74, 'TRAILING_STOP', 6.11,
    1, '1h', '2026-03-08T18:36:22.451250'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.772,
    pnl_amount = 8.74,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D24A77E47C210A94', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2020-06-29 01:00:00', '2020-06-29 09:52:02', 33726.13008493, 34036.32759794,
    33220.23813365, 34569.28333705, 0.088,
    0.9198, 8.1, 'TRAILING_STOP', 8.87,
    1, '1h', '2026-03-08T18:36:22.450838'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9198,
    pnl_amount = 8.1,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9D4E672473250678', 'FUNDING_PRO_v1', 'AVAXUSDT', 'LONG',
    '2020-06-29 13:00:00', '2020-06-29 15:01:36', 468.33877949, 471.79368061,
    461.3136978, 480.04724898, 0.1024,
    0.7377, 7.55, 'TIME_EXIT', 2.03,
    1, '1h', '2026-03-08T18:36:22.451498'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7377,
    pnl_amount = 7.55,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '28638E02738E689A', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2020-06-29 18:00:00', '2020-06-30 01:56:49', 1991.69997302, 1980.75843711,
    2021.57547262, 1941.9074737, 0.0851,
    0.5494, 4.68, 'TIME_EXIT', 7.95,
    1, '1h', '2026-03-08T18:36:22.448828'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5494,
    pnl_amount = 4.68,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5DF7E56121CA5CD2', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2020-07-01 17:00:00', '2020-07-02 02:40:31', 2994.75288724, 2979.086866,
    3039.67418055, 2919.88406506, 0.1087,
    0.5231, 5.69, 'TRAILING_STOP', 9.68,
    1, '1h', '2026-03-08T18:36:22.450224'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5231,
    pnl_amount = 5.69,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '07145E73D836167C', 'FUNDING_PRO_v1', 'AVAXUSDT', 'SHORT',
    '2020-07-02 04:00:00', '2020-07-02 11:17:47', 858.42913456, 862.24710501,
    871.30557157, 836.96840619, 0.0839,
    -0.4448, -3.73, 'STOP_LOSS', 7.3,
    0, '1h', '2026-03-08T18:36:22.454252'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4448,
    pnl_amount = -3.73,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F9E02A59F69BCE2F', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2020-07-10 07:00:00', '2020-07-10 12:19:01', 843.85337746, 852.10148947,
    831.19557679, 864.94971189, 0.0893,
    0.9774, 8.73, 'TRAILING_STOP', 5.32,
    1, '1h', '2026-03-08T18:36:22.453579'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9774,
    pnl_amount = 8.73,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1F19A4BC9B800DBC', 'FUNDING_PRO_v1', 'XRPUSDT', 'LONG',
    '2020-07-10 22:00:00', '2020-07-11 08:28:34', 3843.705023, 3866.19240208,
    3786.04944765, 3939.79764857, 0.088,
    0.585, 5.15, 'TRAILING_STOP', 10.48,
    1, '1h', '2026-03-08T18:36:22.450756'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.585,
    pnl_amount = 5.15,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7447A3023722468F', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2020-07-12 00:00:00', '2020-07-12 09:53:51', 17870.79387423, 17744.59908274,
    18138.85578234, 17424.02402737, 0.1143,
    0.7062, 8.07, 'TIME_EXIT', 9.9,
    1, '1h', '2026-03-08T18:36:22.452044'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7062,
    pnl_amount = 8.07,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '927CF40946EFDF69', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2020-07-15 15:00:00', '2020-07-15 20:47:19', 25708.27001711, 25621.50894508,
    25322.64596685, 26350.97676753, 0.0856,
    -0.3375, -2.89, 'STOP_LOSS', 5.79,
    0, '1h', '2026-03-08T18:36:22.452948'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3375,
    pnl_amount = -2.89,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '303FAF919A48E6F9', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2020-07-24 17:00:00', '2020-07-24 21:21:51', 4794.6277214, 4762.43046252,
    4866.54713722, 4674.76202836, 0.1192,
    0.6715, 8.0, 'TIME_EXIT', 4.36,
    1, '1h', '2026-03-08T18:36:22.450719'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6715,
    pnl_amount = 8.0,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D91692709DC57840', 'FUNDING_PRO_v1', 'DOGEUSDT', 'SHORT',
    '2020-07-25 13:00:00', '2020-07-25 22:47:39', 2382.35717841, 2391.69203143,
    2418.09253609, 2322.79824895, 0.0949,
    -0.3918, -3.72, 'STOP_LOSS', 9.79,
    0, '1h', '2026-03-08T18:36:22.449563'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3918,
    pnl_amount = -3.72,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A8C519AD3D177F25', 'FUNDING_PRO_v1', 'XRPUSDT', 'LONG',
    '2020-08-01 13:00:00', '2020-08-02 00:03:11', 1274.8790998, 1281.81832524,
    1255.7559133, 1306.75107729, 0.0887,
    0.5443, 4.83, 'TRAILING_STOP', 11.05,
    1, '1h', '2026-03-08T18:36:22.453207'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5443,
    pnl_amount = 4.83,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D66E375591EEA9E3', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2020-08-05 08:00:00', '2020-08-05 18:30:49', 34400.27238907, 34663.45349354,
    33884.26830324, 35260.2791988, 0.114,
    0.7651, 8.72, 'TRAILING_STOP', 10.51,
    1, '1h', '2026-03-08T18:36:22.450215'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7651,
    pnl_amount = 8.72,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '24E54378849F7BF5', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2020-08-09 10:00:00', '2020-08-09 12:45:28', 2600.09608461, 2613.96081609,
    2561.09464334, 2665.09848672, 0.0863,
    0.5332, 4.6, 'TRAILING_STOP', 2.76,
    1, '1h', '2026-03-08T18:36:22.450169'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5332,
    pnl_amount = 4.6,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2DB9179AFA530184', 'FUNDING_PRO_v1', 'AVAXUSDT', 'LONG',
    '2020-08-09 11:00:00', '2020-08-09 16:57:10', 4546.50628334, 4582.55424186,
    4478.30868909, 4660.16894043, 0.1173,
    0.7929, 9.3, 'TRAILING_STOP', 5.95,
    1, '1h', '2026-03-08T18:36:22.450349'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7929,
    pnl_amount = 9.3,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '92DB0E37E815BE52', 'FUNDING_PRO_v1', 'AVAXUSDT', 'LONG',
    '2020-08-21 01:00:00', '2020-08-21 06:26:53', 1986.89137419, 1998.17252691,
    1957.08800358, 2036.56365855, 0.1148,
    0.5678, 6.52, 'TIME_EXIT', 5.45,
    1, '1h', '2026-03-08T18:36:22.449302'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5678,
    pnl_amount = 6.52,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '213DDD00B083A85C', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2020-08-29 00:00:00', '2020-08-29 06:51:22', 3299.0978191, 3310.55268405,
    3348.58428639, 3216.62037362, 0.0872,
    -0.3472, -3.03, 'STOP_LOSS', 6.86,
    0, '1h', '2026-03-08T18:36:22.452292'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3472,
    pnl_amount = -3.03,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D764476C3C0F5BE8', 'FUNDING_PRO_v1', 'DOGEUSDT', 'SHORT',
    '2020-08-30 14:00:00', '2020-08-30 22:25:29', 1758.85825243, 1767.05318268,
    1785.24112622, 1714.88679612, 0.0976,
    -0.4659, -4.55, 'TIME_EXIT', 8.42,
    0, '1h', '2026-03-08T18:36:22.450296'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4659,
    pnl_amount = -4.55,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '61B52E7A76D8C341', 'FUNDING_PRO_v1', 'ADAUSDT', 'SHORT',
    '2020-08-31 10:00:00', '2020-08-31 21:16:18', 4743.58013292, 4710.46144713,
    4814.73383492, 4624.9906296, 0.1115,
    0.6982, 7.79, 'TIME_EXIT', 11.27,
    1, '1h', '2026-03-08T18:36:22.454157'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6982,
    pnl_amount = 7.79,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '03D8CDCD546CECDB', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2020-08-31 21:00:00', '2020-09-01 02:01:21', 1075.54154205, 1066.73028614,
    1091.67466518, 1048.6530035, 0.1051,
    0.8192, 8.61, 'TRAILING_STOP', 5.02,
    1, '1h', '2026-03-08T18:36:22.452573'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8192,
    pnl_amount = 8.61,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C5424F0952D8A505', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2020-09-02 16:00:00', '2020-09-02 20:31:07', 2062.74537871, 2081.01596358,
    2031.80419803, 2114.31401318, 0.1149,
    0.8857, 10.18, 'TIME_EXIT', 4.52,
    1, '1h', '2026-03-08T18:36:22.449886'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8857,
    pnl_amount = 10.18,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C2C8F162BDD5C025', 'FUNDING_PRO_v1', 'XRPUSDT', 'SHORT',
    '2020-09-04 22:00:00', '2020-09-05 09:28:37', 2079.61596743, 2061.79639122,
    2110.81020695, 2027.62556825, 0.0998,
    0.8569, 8.55, 'TIME_EXIT', 11.48,
    1, '1h', '2026-03-08T18:36:22.452872'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8569,
    pnl_amount = 8.55,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '230E3BE19CD940DE', 'FUNDING_PRO_v1', 'XRPUSDT', 'LONG',
    '2020-09-09 05:00:00', '2020-09-09 16:27:34', 716.51678291, 720.93518495,
    705.76903117, 734.42970248, 0.1033,
    0.6167, 6.37, 'TRAILING_STOP', 11.46,
    1, '1h', '2026-03-08T18:36:22.452444'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6167,
    pnl_amount = 6.37,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0978DC6607C5E614', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2020-09-13 23:00:00', '2020-09-14 09:36:06', 3574.42110765, 3544.81381913,
    3628.03742427, 3485.06057996, 0.1198,
    0.8283, 9.92, 'TRAILING_STOP', 10.6,
    1, '1h', '2026-03-08T18:36:22.449516'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8283,
    pnl_amount = 9.92,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '182D844585D6BDAB', 'FUNDING_PRO_v1', 'DOGEUSDT', 'SHORT',
    '2020-09-15 11:00:00', '2020-09-15 21:58:06', 2428.03309729, 2438.23254058,
    2464.45359375, 2367.33226986, 0.1003,
    -0.4201, -4.21, 'TIME_EXIT', 10.97,
    0, '1h', '2026-03-08T18:36:22.449151'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4201,
    pnl_amount = -4.21,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '00870A94630AA08B', 'FUNDING_PRO_v1', 'BNBUSDT', 'SHORT',
    '2020-09-18 23:00:00', '2020-09-19 05:11:01', 3402.5167395, 3371.57464152,
    3453.55449059, 3317.45382101, 0.0969,
    0.9094, 8.82, 'TRAILING_STOP', 6.18,
    1, '1h', '2026-03-08T18:36:22.450573'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9094,
    pnl_amount = 8.82,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '417B885973D7F4E3', 'FUNDING_PRO_v1', 'DOGEUSDT', 'SHORT',
    '2020-09-22 22:00:00', '2020-09-23 00:55:03', 438.44266727, 440.22466335,
    445.01930728, 427.48160059, 0.0942,
    -0.4064, -3.83, 'TIME_EXIT', 2.92,
    0, '1h', '2026-03-08T18:36:22.448862'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4064,
    pnl_amount = -3.83,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B9EDBA22688716A1', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2020-09-23 19:00:00', '2020-09-24 00:33:10', 4136.17122213, 4109.29074549,
    4198.21379046, 4032.76694157, 0.084,
    0.6499, 5.46, 'TIME_EXIT', 5.55,
    1, '1h', '2026-03-08T18:36:22.453817'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6499,
    pnl_amount = 5.46,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0EF7A3F052546E65', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2020-09-26 15:00:00', '2020-09-27 00:42:20', 49196.98692586, 49512.83598107,
    48459.03212197, 50426.91159901, 0.1109,
    0.642, 7.12, 'TRAILING_STOP', 9.71,
    1, '1h', '2026-03-08T18:36:22.452554'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.642,
    pnl_amount = 7.12,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D105767C41722935', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2020-09-28 18:00:00', '2020-09-29 03:11:59', 38190.37631918, 38333.80547937,
    38763.23196397, 37235.6169112, 0.1145,
    -0.3756, -4.3, 'STOP_LOSS', 9.2,
    0, '1h', '2026-03-08T18:36:22.454419'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3756,
    pnl_amount = -4.3,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7F043F2003047B09', 'FUNDING_PRO_v1', 'DOTUSDT', 'LONG',
    '2020-09-30 16:00:00', '2020-10-01 01:58:05', 1286.33174558, 1296.73555462,
    1267.0367694, 1318.49003922, 0.1159,
    0.8088, 9.38, 'TAKE_PROFIT', 9.97,
    1, '1h', '2026-03-08T18:36:22.453871'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8088,
    pnl_amount = 9.38,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0EF5F30070AB6E3F', 'FUNDING_PRO_v1', 'XRPUSDT', 'SHORT',
    '2020-10-02 06:00:00', '2020-10-02 16:02:07', 3690.69475212, 3670.80973496,
    3746.0551734, 3598.42738332, 0.0875,
    0.5388, 4.71, 'TIME_EXIT', 10.04,
    1, '1h', '2026-03-08T18:36:22.452399'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5388,
    pnl_amount = 4.71,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A7BB39566A0DA326', 'FUNDING_PRO_v1', 'DOGEUSDT', 'LONG',
    '2020-10-06 15:00:00', '2020-10-06 19:08:27', 4462.01057392, 4442.87811914,
    4395.08041531, 4573.56083827, 0.116,
    -0.4288, -4.97, 'TIME_EXIT', 4.14,
    0, '1h', '2026-03-08T18:36:22.454370'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4288,
    pnl_amount = -4.97,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '05CA709E6CAFEE5C', 'FUNDING_PRO_v1', 'ADAUSDT', 'LONG',
    '2020-10-09 04:00:00', '2020-10-09 13:08:00', 3276.35267442, 3300.61503789,
    3227.20738431, 3358.26149128, 0.1069,
    0.7405, 7.91, 'TRAILING_STOP', 9.13,
    1, '1h', '2026-03-08T18:36:22.450177'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7405,
    pnl_amount = 7.91,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3C248C9359AB2707', 'FUNDING_PRO_v1', 'AVAXUSDT', 'LONG',
    '2020-10-10 05:00:00', '2020-10-10 07:10:39', 4096.88980674, 4126.69344586,
    4035.43645964, 4199.31205191, 0.0827,
    0.7275, 6.01, 'TRAILING_STOP', 2.18,
    1, '1h', '2026-03-08T18:36:22.453617'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7275,
    pnl_amount = 6.01,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7C9523FF227B63DF', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2020-10-11 20:00:00', '2020-10-12 03:21:58', 18140.96624518, 18242.73729835,
    17868.8517515, 18594.49040131, 0.0815,
    0.561, 4.57, 'TRAILING_STOP', 7.37,
    1, '1h', '2026-03-08T18:36:22.454232'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.561,
    pnl_amount = 4.57,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '652AC3ED1E1E17C1', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2020-10-17 12:00:00', '2020-10-17 20:48:16', 118.70513335, 119.43047364,
    116.92455635, 121.67276168, 0.084,
    0.611, 5.13, 'TRAILING_STOP', 8.8,
    1, '1h', '2026-03-08T18:36:22.449481'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.611,
    pnl_amount = 5.13,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4C9ACA4DF79AEA9F', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2020-10-18 03:00:00', '2020-10-18 06:50:16', 3597.68829392, 3585.0707388,
    3543.72296951, 3687.63050127, 0.1147,
    -0.3507, -4.02, 'TIME_EXIT', 3.84,
    0, '1h', '2026-03-08T18:36:22.450692'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3507,
    pnl_amount = -4.02,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '11C44531CE6162F1', 'FUNDING_PRO_v1', 'ADAUSDT', 'LONG',
    '2020-10-18 06:00:00', '2020-10-18 10:25:19', 528.29682929, 531.88293001,
    520.37237685, 541.50425002, 0.1194,
    0.6788, 8.11, 'TAKE_PROFIT', 4.42,
    1, '1h', '2026-03-08T18:36:22.452581'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6788,
    pnl_amount = 8.11,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '75573A6F367C14B6', 'FUNDING_PRO_v1', 'DOGEUSDT', 'LONG',
    '2020-10-19 04:00:00', '2020-10-19 10:21:22', 2288.73327579, 2301.65459968,
    2254.40227666, 2345.95160769, 0.0836,
    0.5646, 4.72, 'TIME_EXIT', 6.36,
    1, '1h', '2026-03-08T18:36:22.453228'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5646,
    pnl_amount = 4.72,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4B4ABABF92511E7B', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2020-10-20 04:00:00', '2020-10-20 06:43:51', 4438.67223986, 4461.15603503,
    4372.09215626, 4549.63904586, 0.1194,
    0.5065, 6.05, 'TRAILING_STOP', 2.73,
    1, '1h', '2026-03-08T18:36:22.451091'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5065,
    pnl_amount = 6.05,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '505B25FFE753F8D4', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2020-10-21 18:00:00', '2020-10-22 05:57:01', 4519.15432366, 4477.03229336,
    4586.94163851, 4406.17546557, 0.1192,
    0.9321, 11.11, 'TAKE_PROFIT', 11.95,
    1, '1h', '2026-03-08T18:36:22.451829'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9321,
    pnl_amount = 11.11,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FD99FAA358E0FD7D', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2020-10-24 03:00:00', '2020-10-24 08:47:32', 33594.26524655, 33784.8296753,
    33090.35126785, 34434.12187771, 0.0802,
    0.5673, 4.55, 'TIME_EXIT', 5.79,
    1, '1h', '2026-03-08T18:36:22.453387'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5673,
    pnl_amount = 4.55,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '44B89970DBDED4DA', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2020-10-30 04:00:00', '2020-10-30 13:03:19', 4913.79809881, 4885.96358774,
    4987.50507029, 4790.95314633, 0.0824,
    0.5665, 4.67, 'TRAILING_STOP', 9.06,
    1, '1h', '2026-03-08T18:36:22.450079'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5665,
    pnl_amount = 4.67,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3A3462639942B8C7', 'FUNDING_PRO_v1', 'DOTUSDT', 'LONG',
    '2020-11-01 19:00:00', '2020-11-02 06:21:50', 3054.01535594, 3073.19742514,
    3008.2051256, 3130.36573984, 0.1046,
    0.6281, 6.57, 'TIME_EXIT', 11.36,
    1, '1h', '2026-03-08T18:36:22.452920'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6281,
    pnl_amount = 6.57,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9DC3522943256C29', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2020-11-04 06:00:00', '2020-11-04 13:47:30', 2534.940726, 2554.57568834,
    2496.91661511, 2598.31424415, 0.0837,
    0.7746, 6.49, 'TIME_EXIT', 7.79,
    1, '1h', '2026-03-08T18:36:22.449160'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7746,
    pnl_amount = 6.49,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9715A7A83B7195AE', 'FUNDING_PRO_v1', 'DOGEUSDT', 'LONG',
    '2020-11-10 16:00:00', '2020-11-10 20:12:52', 1315.27949339, 1323.93605407,
    1295.55030099, 1348.16148072, 0.1168,
    0.6582, 7.69, 'TIME_EXIT', 4.21,
    1, '1h', '2026-03-08T18:36:22.450564'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6582,
    pnl_amount = 7.69,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '229B10D77A5E2809', 'FUNDING_PRO_v1', 'DOGEUSDT', 'LONG',
    '2020-11-14 14:00:00', '2020-11-14 16:03:31', 2790.68741569, 2811.23187291,
    2748.82710446, 2860.45460109, 0.087,
    0.7362, 6.41, 'TAKE_PROFIT', 2.06,
    1, '1h', '2026-03-08T18:36:22.448872'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7362,
    pnl_amount = 6.41,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9FFC17760A705BA8', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2020-11-23 22:00:00', '2020-11-24 08:19:45', 1678.38121567, 1666.91159043,
    1703.5569339, 1636.42168528, 0.0958,
    0.6834, 6.55, 'TAKE_PROFIT', 10.33,
    1, '1h', '2026-03-08T18:36:22.451111'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6834,
    pnl_amount = 6.55,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'CA6BBAB860319B19', 'FUNDING_PRO_v1', 'DOGEUSDT', 'SHORT',
    '2020-11-28 21:00:00', '2020-11-29 06:11:01', 2735.61086905, 2719.64191951,
    2776.64503209, 2667.22059733, 0.0837,
    0.5837, 4.89, 'TAKE_PROFIT', 9.18,
    1, '1h', '2026-03-08T18:36:22.453937'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5837,
    pnl_amount = 4.89,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BE5E528F89F5C553', 'FUNDING_PRO_v1', 'AVAXUSDT', 'LONG',
    '2020-12-09 23:00:00', '2020-12-10 03:24:50', 3022.89593069, 3042.56524979,
    2977.55249173, 3098.46832895, 0.1192,
    0.6507, 7.76, 'TIME_EXIT', 4.41,
    1, '1h', '2026-03-08T18:36:22.453509'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6507,
    pnl_amount = 7.76,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9A7F83ED2D569A63', 'FUNDING_PRO_v1', 'DOGEUSDT', 'LONG',
    '2020-12-14 13:00:00', '2020-12-14 18:27:31', 3492.23344723, 3480.45473467,
    3439.84994552, 3579.53928341, 0.1151,
    -0.3373, -3.88, 'STOP_LOSS', 5.46,
    0, '1h', '2026-03-08T18:36:22.453310'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3373,
    pnl_amount = -3.88,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E671FE1F6790E522', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2020-12-21 11:00:00', '2020-12-21 22:15:41', 1635.3262631, 1623.00947486,
    1659.85615705, 1594.44310652, 0.0943,
    0.7532, 7.11, 'TRAILING_STOP', 11.26,
    1, '1h', '2026-03-08T18:36:22.452372'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7532,
    pnl_amount = 7.11,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2C14B850E75AFC71', 'FUNDING_PRO_v1', 'XRPUSDT', 'SHORT',
    '2020-12-25 03:00:00', '2020-12-25 10:55:46', 4511.85235328, 4528.96740579,
    4579.53013858, 4399.05604445, 0.094,
    -0.3793, -3.57, 'STOP_LOSS', 7.93,
    0, '1h', '2026-03-08T18:36:22.449358'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3793,
    pnl_amount = -3.57,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C805CC0ECFA78BD2', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2020-12-26 20:00:00', '2020-12-27 05:23:03', 927.9745474, 937.00467677,
    914.05492919, 951.17391109, 0.1157,
    0.9731, 11.26, 'TRAILING_STOP', 9.38,
    1, '1h', '2026-03-08T18:36:22.449639'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9731,
    pnl_amount = 11.26,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '11766D828A040E65', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2020-12-28 21:00:00', '2020-12-29 01:18:03', 1122.89163939, 1132.48709244,
    1106.0482648, 1150.96393038, 0.1143,
    0.8545, 9.76, 'TIME_EXIT', 4.3,
    1, '1h', '2026-03-08T18:36:22.453060'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8545,
    pnl_amount = 9.76,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D99B30EB497C4AED', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2020-12-31 01:00:00', '2020-12-31 03:08:21', 3564.68362025, 3592.11980325,
    3511.21336594, 3653.80071075, 0.1088,
    0.7697, 8.38, 'TIME_EXIT', 2.14,
    1, '1h', '2026-03-08T18:36:22.454184'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7697,
    pnl_amount = 8.38,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'ECCF0951C346A256', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2021-01-03 13:00:00', '2021-01-03 18:49:25', 1713.69365843, 1705.58535975,
    1687.98825355, 1756.53599989, 0.0865,
    -0.4731, -4.09, 'TIME_EXIT', 5.82,
    0, '1h', '2026-03-08T18:36:22.454092'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4731,
    pnl_amount = -4.09,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BC017DBE69B1DF6D', 'FUNDING_PRO_v1', 'LINKUSDT', 'LONG',
    '2021-01-08 08:00:00', '2021-01-08 12:21:27', 1228.65438106, 1224.62929955,
    1210.22456534, 1259.37074058, 0.105,
    -0.3276, -3.44, 'STOP_LOSS', 4.36,
    0, '1h', '2026-03-08T18:36:22.451129'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3276,
    pnl_amount = -3.44,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '38BC20C2668A6EF9', 'FUNDING_PRO_v1', 'DOGEUSDT', 'LONG',
    '2021-01-08 22:00:00', '2021-01-09 06:00:59', 1435.12173672, 1429.65112393,
    1413.59491066, 1470.99978013, 0.0834,
    -0.3812, -3.18, 'TIME_EXIT', 8.02,
    0, '1h', '2026-03-08T18:36:22.448988'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3812,
    pnl_amount = -3.18,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6C0AD1E568091FB1', 'FUNDING_PRO_v1', 'AVAXUSDT', 'LONG',
    '2021-01-09 14:00:00', '2021-01-09 22:56:16', 222.21250777, 224.02605562,
    218.87932016, 227.76782047, 0.0991,
    0.8161, 8.09, 'TAKE_PROFIT', 8.94,
    1, '1h', '2026-03-08T18:36:22.449794'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8161,
    pnl_amount = 8.09,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A655FED7FA5EED8A', 'FUNDING_PRO_v1', 'DOGEUSDT', 'LONG',
    '2021-01-11 18:00:00', '2021-01-12 02:22:19', 3667.36282959, 3688.72766924,
    3612.35238715, 3759.04690033, 0.1142,
    0.5826, 6.65, 'TIME_EXIT', 8.37,
    1, '1h', '2026-03-08T18:36:22.451749'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5826,
    pnl_amount = 6.65,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '275637069B815DAA', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2021-01-21 22:00:00', '2021-01-22 01:23:37', 1008.78747067, 1000.31637393,
    1023.91928273, 983.5677839, 0.1062,
    0.8397, 8.92, 'TAKE_PROFIT', 3.39,
    1, '1h', '2026-03-08T18:36:22.452957'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8397,
    pnl_amount = 8.92,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '318D9BF0785FC548', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2021-01-28 00:00:00', '2021-01-28 07:36:32', 2070.17973051, 2062.68593551,
    2039.12703455, 2121.93422377, 0.1031,
    -0.362, -3.73, 'TIME_EXIT', 7.61,
    0, '1h', '2026-03-08T18:36:22.451552'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.362,
    pnl_amount = -3.73,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3752130D9B539376', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2021-02-02 22:00:00', '2021-02-03 03:27:56', 12840.00092917, 12939.73658173,
    12647.40091523, 13161.0009524, 0.1036,
    0.7768, 8.04, 'TAKE_PROFIT', 5.47,
    1, '1h', '2026-03-08T18:36:22.453738'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7768,
    pnl_amount = 8.04,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '266999A16835CAE0', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2021-02-05 01:00:00', '2021-02-05 07:24:12', 34209.36695073, 34478.0245525,
    33696.22644647, 35064.6011245, 0.0928,
    0.7853, 7.29, 'TIME_EXIT', 6.4,
    1, '1h', '2026-03-08T18:36:22.449007'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7853,
    pnl_amount = 7.29,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F8E39FD709EB09F4', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2021-02-08 05:00:00', '2021-02-08 11:14:34', 44161.37493966, 43845.5619764,
    44823.79556375, 43057.34056617, 0.119,
    0.7151, 8.51, 'TRAILING_STOP', 6.24,
    1, '1h', '2026-03-08T18:36:22.450106'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7151,
    pnl_amount = 8.51,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F801C08CC0C54F2D', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2021-02-08 10:00:00', '2021-02-08 14:58:23', 2741.91727666, 2756.41127407,
    2700.78851751, 2810.46520857, 0.1038,
    0.5286, 5.49, 'TIME_EXIT', 4.97,
    1, '1h', '2026-03-08T18:36:22.451802'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5286,
    pnl_amount = 5.49,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9B8CA65D9EF9A2E6', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2021-02-09 20:00:00', '2021-02-10 06:17:05', 3566.5547705, 3554.14531124,
    3513.05644895, 3655.71863977, 0.0862,
    -0.3479, -3.0, 'TIME_EXIT', 10.28,
    0, '1h', '2026-03-08T18:36:22.450124'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3479,
    pnl_amount = -3.0,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BD59B315E244B484', 'FUNDING_PRO_v1', 'AVAXUSDT', 'LONG',
    '2021-02-11 06:00:00', '2021-02-11 10:53:57', 353.86313125, 356.53516655,
    348.55518429, 362.70970954, 0.1128,
    0.7551, 8.52, 'TAKE_PROFIT', 4.9,
    1, '1h', '2026-03-08T18:36:22.451873'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7551,
    pnl_amount = 8.52,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '83E63A72015CEFA9', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2021-02-14 02:00:00', '2021-02-14 08:17:30', 776.81710452, 771.01181936,
    788.46936108, 757.3966769, 0.1193,
    0.7473, 8.91, 'TIME_EXIT', 6.29,
    1, '1h', '2026-03-08T18:36:22.451443'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7473,
    pnl_amount = 8.91,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A6287A008F0DD776', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2021-02-20 13:00:00', '2021-02-20 16:14:28', 3651.21823154, 3626.97454425,
    3705.98650502, 3559.93777576, 0.1175,
    0.664, 7.8, 'TRAILING_STOP', 3.24,
    1, '1h', '2026-03-08T18:36:22.451120'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.664,
    pnl_amount = 7.8,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '77F1BE0E6C3F5BC0', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2021-03-02 07:00:00', '2021-03-02 15:58:21', 21803.95412693, 21636.28219681,
    22131.01343883, 21258.85527375, 0.1001,
    0.769, 7.7, 'TAKE_PROFIT', 8.97,
    1, '1h', '2026-03-08T18:36:22.451369'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.769,
    pnl_amount = 7.7,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '46F3EE9BAE159F52', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2021-03-04 16:00:00', '2021-03-04 22:52:24', 4238.69791252, 4221.10862619,
    4175.11744384, 4344.66536034, 0.1178,
    -0.415, -4.89, 'TIME_EXIT', 6.87,
    0, '1h', '2026-03-08T18:36:22.451221'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.415,
    pnl_amount = -4.89,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8E8DBE489FC57E3E', 'FUNDING_PRO_v1', 'DOGEUSDT', 'LONG',
    '2021-03-08 20:00:00', '2021-03-08 23:34:19', 3360.30336737, 3392.19795389,
    3309.89881686, 3444.31095155, 0.0833,
    0.9492, 7.91, 'TIME_EXIT', 3.57,
    1, '1h', '2026-03-08T18:36:22.452244'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9492,
    pnl_amount = 7.91,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DF16DC1737AA9A93', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2021-03-15 09:00:00', '2021-03-15 13:19:19', 3341.19536727, 3317.8811516,
    3391.31329778, 3257.66548309, 0.114,
    0.6978, 7.95, 'TAKE_PROFIT', 4.32,
    1, '1h', '2026-03-08T18:36:22.453031'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6978,
    pnl_amount = 7.95,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6FA16E1F36853D65', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2021-03-23 06:00:00', '2021-03-23 13:56:24', 4332.44473904, 4297.88953321,
    4397.43141013, 4224.13362057, 0.1146,
    0.7976, 9.14, 'TIME_EXIT', 7.94,
    1, '1h', '2026-03-08T18:36:22.451999'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7976,
    pnl_amount = 9.14,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D141651F4E0D333C', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2021-03-28 22:00:00', '2021-03-29 07:10:20', 47358.78309246, 47053.56322076,
    48069.16483885, 46174.81351515, 0.1112,
    0.6445, 7.17, 'TAKE_PROFIT', 9.17,
    1, '1h', '2026-03-08T18:36:22.454012'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6445,
    pnl_amount = 7.17,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '319B7C770DE0AEB1', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2021-04-06 12:00:00', '2021-04-06 14:40:47', 15751.42125384, 15808.64020347,
    15987.69257265, 15357.6357225, 0.0849,
    -0.3633, -3.08, 'TIME_EXIT', 2.68,
    0, '1h', '2026-03-08T18:36:22.452564'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3633,
    pnl_amount = -3.08,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1DDE18C26BCE4FBB', 'FUNDING_PRO_v1', 'ADAUSDT', 'SHORT',
    '2021-04-08 01:00:00', '2021-04-08 06:09:33', 4895.35133044, 4913.96619233,
    4968.78160039, 4772.96754718, 0.0814,
    -0.3803, -3.1, 'TIME_EXIT', 5.16,
    0, '1h', '2026-03-08T18:36:22.450600'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3803,
    pnl_amount = -3.1,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '91A6DBFFBBF7C268', 'FUNDING_PRO_v1', 'ADAUSDT', 'SHORT',
    '2021-04-14 22:00:00', '2021-04-15 07:17:54', 4918.63914626, 4937.68247774,
    4992.41873345, 4795.6731676, 0.0899,
    -0.3872, -3.48, 'STOP_LOSS', 9.3,
    0, '1h', '2026-03-08T18:36:22.453728'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3872,
    pnl_amount = -3.48,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '98C69412B720BDFA', 'FUNDING_PRO_v1', 'ADAUSDT', 'SHORT',
    '2021-04-16 18:00:00', '2021-04-16 23:04:44', 4127.92729387, 4145.07666308,
    4189.84620328, 4024.72911152, 0.0968,
    -0.4154, -4.02, 'STOP_LOSS', 5.08,
    0, '1h', '2026-03-08T18:36:22.452807'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4154,
    pnl_amount = -4.02,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7CF03925FE119BD9', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2021-04-20 12:00:00', '2021-04-20 17:58:37', 4532.70251977, 4509.31640071,
    4600.69305756, 4419.38495677, 0.0935,
    0.5159, 4.82, 'TIME_EXIT', 5.98,
    1, '1h', '2026-03-08T18:36:22.449179'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5159,
    pnl_amount = 4.82,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '10385A791CF1D519', 'FUNDING_PRO_v1', 'DOTUSDT', 'LONG',
    '2021-04-20 15:00:00', '2021-04-21 02:38:18', 822.54212096, 819.62847523,
    810.20398914, 843.10567398, 0.0849,
    -0.3542, -3.01, 'TIME_EXIT', 11.64,
    0, '1h', '2026-03-08T18:36:22.451659'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3542,
    pnl_amount = -3.01,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6FF323D60B8176B6', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2021-04-21 11:00:00', '2021-04-21 21:10:03', 3047.34025653, 3021.9778271,
    3093.05036037, 2971.15675011, 0.1146,
    0.8323, 9.54, 'TAKE_PROFIT', 10.17,
    1, '1h', '2026-03-08T18:36:22.450968'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8323,
    pnl_amount = 9.54,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '180EC177E196F4CE', 'FUNDING_PRO_v1', 'DOGEUSDT', 'SHORT',
    '2021-04-24 14:00:00', '2021-04-25 01:01:03', 4676.01502134, 4634.44073935,
    4746.15524666, 4559.11464581, 0.0813,
    0.8891, 7.23, 'TAKE_PROFIT', 11.02,
    1, '1h', '2026-03-08T18:36:22.450160'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8891,
    pnl_amount = 7.23,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C9BBA213072404CB', 'FUNDING_PRO_v1', 'AVAXUSDT', 'SHORT',
    '2021-04-28 10:00:00', '2021-04-28 15:16:30', 708.29162381, 704.71025093,
    718.91599817, 690.58433322, 0.1053,
    0.5056, 5.32, 'TRAILING_STOP', 5.28,
    1, '1h', '2026-03-08T18:36:22.451847'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5056,
    pnl_amount = 5.32,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '55B2C6097D9423A2', 'FUNDING_PRO_v1', 'LINKUSDT', 'LONG',
    '2021-05-01 15:00:00', '2021-05-02 01:20:58', 3381.07006251, 3411.58245222,
    3330.35401157, 3465.59681407, 0.1036,
    0.9024, 9.35, 'TIME_EXIT', 10.35,
    1, '1h', '2026-03-08T18:36:22.448840'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9024,
    pnl_amount = 9.35,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '912EC7EFF133CEC7', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2021-05-01 17:00:00', '2021-05-01 23:54:09', 7529.85221368, 7456.40516141,
    7642.79999689, 7341.60590834, 0.0835,
    0.9754, 8.15, 'TRAILING_STOP', 6.9,
    1, '1h', '2026-03-08T18:36:22.448978'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9754,
    pnl_amount = 8.15,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '53A3DF07AB287B09', 'FUNDING_PRO_v1', 'XRPUSDT', 'SHORT',
    '2021-05-04 01:00:00', '2021-05-04 08:38:57', 3384.13987151, 3364.8561506,
    3434.90196958, 3299.53637472, 0.1007,
    0.5698, 5.74, 'TIME_EXIT', 7.65,
    1, '1h', '2026-03-08T18:36:22.449666'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5698,
    pnl_amount = 5.74,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E309666D1790833C', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2021-05-06 02:00:00', '2021-05-06 04:32:53', 3018.80001242, 3000.91649084,
    3064.08201261, 2943.33001211, 0.0885,
    0.5924, 5.24, 'TRAILING_STOP', 2.55,
    1, '1h', '2026-03-08T18:36:22.450915'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5924,
    pnl_amount = 5.24,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '017EAC948CFF5CA9', 'FUNDING_PRO_v1', 'ADAUSDT', 'LONG',
    '2021-05-10 08:00:00', '2021-05-10 17:24:46', 2349.52712994, 2365.88344249,
    2314.28422299, 2408.26530818, 0.0905,
    0.6962, 6.3, 'TIME_EXIT', 9.41,
    1, '1h', '2026-03-08T18:36:22.452080'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6962,
    pnl_amount = 6.3,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '330ADBE361F761CE', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2021-05-10 09:00:00', '2021-05-10 17:38:01', 1620.38220569, 1629.63588536,
    1596.0764726, 1660.89176083, 0.103,
    0.5711, 5.88, 'TIME_EXIT', 8.63,
    1, '1h', '2026-03-08T18:36:22.450701'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5711,
    pnl_amount = 5.88,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'CA0993D797AF3D39', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2021-05-18 09:00:00', '2021-05-18 18:26:03', 154.27625187, 154.79569732,
    156.59039564, 150.41934557, 0.1163,
    -0.3367, -3.92, 'STOP_LOSS', 9.43,
    0, '1h', '2026-03-08T18:36:22.452742'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3367,
    pnl_amount = -3.92,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '25DF40D644465E83', 'FUNDING_PRO_v1', 'LINKUSDT', 'SHORT',
    '2021-05-20 19:00:00', '2021-05-20 23:16:02', 3778.40529573, 3748.42978083,
    3835.08137517, 3683.94516334, 0.0993,
    0.7933, 7.88, 'TIME_EXIT', 4.27,
    1, '1h', '2026-03-08T18:36:22.450829'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7933,
    pnl_amount = 7.88,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E19AA928CA6440C5', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2021-05-22 04:00:00', '2021-05-22 12:38:08', 4417.12138296, 4387.31825409,
    4483.3782037, 4306.69334838, 0.0931,
    0.6747, 6.28, 'TAKE_PROFIT', 8.64,
    1, '1h', '2026-03-08T18:36:22.450456'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6747,
    pnl_amount = 6.28,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '02CE1EE3B9AA8025', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2021-05-24 20:00:00', '2021-05-25 06:43:29', 1466.80462785, 1452.73807219,
    1488.80669726, 1430.13451215, 0.086,
    0.959, 8.24, 'TAKE_PROFIT', 10.72,
    1, '1h', '2026-03-08T18:36:22.450034'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.959,
    pnl_amount = 8.24,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2F2F06A4FE15E24F', 'FUNDING_PRO_v1', 'DOTUSDT', 'SHORT',
    '2021-05-27 12:00:00', '2021-05-27 20:10:05', 2121.29019052, 2103.35413249,
    2153.10954338, 2068.25793576, 0.0871,
    0.8455, 7.36, 'TAKE_PROFIT', 8.17,
    1, '1h', '2026-03-08T18:36:22.449684'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8455,
    pnl_amount = 7.36,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1D6A4376D845D094', 'FUNDING_PRO_v1', 'XRPUSDT', 'LONG',
    '2021-05-30 15:00:00', '2021-05-30 21:48:44', 1660.54181288, 1652.92230273,
    1635.63368568, 1702.0553582, 0.1065,
    -0.4589, -4.88, 'STOP_LOSS', 6.81,
    0, '1h', '2026-03-08T18:36:22.452844'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4589,
    pnl_amount = -4.88,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1ABFC1A8CA2B2F13', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2021-06-04 07:00:00', '2021-06-04 12:06:26', 45269.22491007, 44974.57164348,
    45948.26328372, 44137.49428732, 0.0929,
    0.6509, 6.05, 'TRAILING_STOP', 5.11,
    1, '1h', '2026-03-08T18:36:22.450376'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6509,
    pnl_amount = 6.05,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '027D2C20966B961C', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2021-06-04 12:00:00', '2021-06-04 23:54:26', 1694.86499137, 1682.2416623,
    1720.28796624, 1652.49336659, 0.0843,
    0.7448, 6.28, 'TIME_EXIT', 11.91,
    1, '1h', '2026-03-08T18:36:22.453157'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7448,
    pnl_amount = 6.28,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F410F5CA8092F77A', 'FUNDING_PRO_v1', 'LINKUSDT', 'SHORT',
    '2021-06-06 16:00:00', '2021-06-06 20:03:13', 2193.33774835, 2200.64049938,
    2226.23781458, 2138.50430464, 0.0905,
    -0.333, -3.01, 'TIME_EXIT', 4.05,
    0, '1h', '2026-03-08T18:36:22.453167'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.333,
    pnl_amount = -3.01,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7FC8F45C57FD01AC', 'FUNDING_PRO_v1', 'DOGEUSDT', 'SHORT',
    '2021-06-15 04:00:00', '2021-06-15 10:13:33', 3347.84724235, 3316.54159244,
    3398.06495098, 3264.15106129, 0.1067,
    0.9351, 9.98, 'TAKE_PROFIT', 6.23,
    1, '1h', '2026-03-08T18:36:22.453680'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9351,
    pnl_amount = 9.98,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BAF3279E5B9DD3E2', 'FUNDING_PRO_v1', 'LINKUSDT', 'LONG',
    '2021-06-19 01:00:00', '2021-06-19 04:48:22', 629.61971236, 634.72103395,
    620.17541667, 645.36020517, 0.0816,
    0.8102, 6.61, 'TRAILING_STOP', 3.81,
    1, '1h', '2026-03-08T18:36:22.451838'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8102,
    pnl_amount = 6.61,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C0E806CEF572189A', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2021-06-19 15:00:00', '2021-06-19 22:52:57', 4824.61537014, 4864.91446089,
    4752.24613959, 4945.23075439, 0.0826,
    0.8353, 6.9, 'TRAILING_STOP', 7.88,
    1, '1h', '2026-03-08T18:36:22.450025'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8353,
    pnl_amount = 6.9,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6EEC335EBA9D2FAF', 'FUNDING_PRO_v1', 'AVAXUSDT', 'LONG',
    '2021-06-21 06:00:00', '2021-06-21 15:57:21', 4979.44134253, 5008.30782364,
    4904.7497224, 5103.9273761, 0.1127,
    0.5797, 6.53, 'TAKE_PROFIT', 9.96,
    1, '1h', '2026-03-08T18:36:22.453292'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5797,
    pnl_amount = 6.53,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2D3DA6E47629676C', 'FUNDING_PRO_v1', 'DOGEUSDT', 'SHORT',
    '2021-06-23 14:00:00', '2021-06-23 23:29:12', 2241.2690649, 2223.04158437,
    2274.88810088, 2185.23733828, 0.0887,
    0.8133, 7.21, 'TAKE_PROFIT', 9.49,
    1, '1h', '2026-03-08T18:36:22.450206'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8133,
    pnl_amount = 7.21,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '29B833B7984AC9C0', 'FUNDING_PRO_v1', 'DOGEUSDT', 'SHORT',
    '2021-06-24 02:00:00', '2021-06-24 12:26:34', 1071.85323465, 1064.81895641,
    1087.93103317, 1045.05690379, 0.0929,
    0.6563, 6.09, 'TAKE_PROFIT', 10.44,
    1, '1h', '2026-03-08T18:36:22.452723'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6563,
    pnl_amount = 6.09,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '91A15F2CCFE5A9D3', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2021-06-24 16:00:00', '2021-06-24 18:05:14', 4686.10935544, 4646.23614934,
    4756.40099577, 4568.95662155, 0.0809,
    0.8509, 6.88, 'TAKE_PROFIT', 2.09,
    1, '1h', '2026-03-08T18:36:22.450803'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8509,
    pnl_amount = 6.88,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8F5BAFB9450E1CB2', 'FUNDING_PRO_v1', 'XRPUSDT', 'LONG',
    '2021-06-24 23:00:00', '2021-06-25 05:00:53', 1576.77387856, 1586.79857784,
    1553.12227038, 1616.19322552, 0.1025,
    0.6358, 6.52, 'TIME_EXIT', 6.01,
    1, '1h', '2026-03-08T18:36:22.449831'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6358,
    pnl_amount = 6.52,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4FFC1C529C646C04', 'FUNDING_PRO_v1', 'XRPUSDT', 'LONG',
    '2021-06-26 12:00:00', '2021-06-26 18:47:38', 2561.21642939, 2583.64231107,
    2522.79818295, 2625.24684013, 0.1122,
    0.8756, 9.83, 'TRAILING_STOP', 6.79,
    1, '1h', '2026-03-08T18:36:22.449085'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8756,
    pnl_amount = 9.83,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6EDC4AE09D8974F3', 'FUNDING_PRO_v1', 'XRPUSDT', 'LONG',
    '2021-06-27 05:00:00', '2021-06-27 14:36:36', 289.8618832, 288.83054,
    285.51395495, 297.10843028, 0.0967,
    -0.3558, -3.44, 'TIME_EXIT', 9.61,
    0, '1h', '2026-03-08T18:36:22.452674'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3558,
    pnl_amount = -3.44,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '996ADA9FB99444EA', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2021-06-27 09:00:00', '2021-06-27 13:45:34', 1106.08897972, 1096.20475142,
    1122.68031441, 1078.43675523, 0.1023,
    0.8936, 9.14, 'TIME_EXIT', 4.76,
    1, '1h', '2026-03-08T18:36:22.453599'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8936,
    pnl_amount = 9.14,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E840CAAEEE040515', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2021-07-10 04:00:00', '2021-07-10 15:41:36', 3711.91711001, 3741.05664525,
    3656.23835336, 3804.71503776, 0.0873,
    0.785, 6.85, 'TRAILING_STOP', 11.69,
    1, '1h', '2026-03-08T18:36:22.448903'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.785,
    pnl_amount = 6.85,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C8862116D8C887A6', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2021-07-13 13:00:00', '2021-07-14 00:51:35', 43828.78585393, 43475.6665131,
    44486.21764173, 42733.06620758, 0.1074,
    0.8057, 8.65, 'TAKE_PROFIT', 11.86,
    1, '1h', '2026-03-08T18:36:22.451044'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8057,
    pnl_amount = 8.65,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A4F1C7A6C62F90EC', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2021-07-14 22:00:00', '2021-07-15 00:42:11', 23625.14116682, 23543.10844031,
    23270.76404931, 24215.76969599, 0.0946,
    -0.3472, -3.29, 'TIME_EXIT', 2.7,
    0, '1h', '2026-03-08T18:36:22.454130'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3472,
    pnl_amount = -3.29,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '23EB8E42960E9D73', 'FUNDING_PRO_v1', 'BNBUSDT', 'SHORT',
    '2021-07-18 03:00:00', '2021-07-18 14:24:55', 2999.9483325, 2979.2175231,
    3044.94755749, 2924.94962419, 0.0893,
    0.691, 6.17, 'TAKE_PROFIT', 11.42,
    1, '1h', '2026-03-08T18:36:22.451605'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.691,
    pnl_amount = 6.17,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C76E264CAF30A755', 'FUNDING_PRO_v1', 'ADAUSDT', 'SHORT',
    '2021-07-19 20:00:00', '2021-07-20 04:52:04', 2228.83244446, 2217.63482897,
    2262.26493112, 2173.11163335, 0.1069,
    0.5024, 5.37, 'TIME_EXIT', 8.87,
    1, '1h', '2026-03-08T18:36:22.452993'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5024,
    pnl_amount = 5.37,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A960D958D4C0162B', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2021-07-26 23:00:00', '2021-07-27 01:33:14', 1508.23779637, 1519.04421876,
    1485.61422942, 1545.94374128, 0.0993,
    0.7165, 7.12, 'TIME_EXIT', 2.55,
    1, '1h', '2026-03-08T18:36:22.449435'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7165,
    pnl_amount = 7.12,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C920198CFAADF721', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2021-08-01 14:00:00', '2021-08-01 23:53:29', 3136.27284707, 3126.08949349,
    3089.22875436, 3214.67966824, 0.1084,
    -0.3247, -3.52, 'STOP_LOSS', 9.89,
    0, '1h', '2026-03-08T18:36:22.449996'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3247,
    pnl_amount = -3.52,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6A887A247470FB2F', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2021-08-07 12:00:00', '2021-08-07 22:34:20', 3471.42161294, 3443.0275372,
    3523.49293714, 3384.63607262, 0.087,
    0.8179, 7.12, 'TAKE_PROFIT', 10.57,
    1, '1h', '2026-03-08T18:36:22.453237'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8179,
    pnl_amount = 7.12,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B50924295FA3F7BB', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2021-08-12 07:00:00', '2021-08-12 13:50:40', 4054.13569762, 4076.54669737,
    3993.32366215, 4155.48909006, 0.0881,
    0.5528, 4.87, 'TRAILING_STOP', 6.84,
    1, '1h', '2026-03-08T18:36:22.450421'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5528,
    pnl_amount = 4.87,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BECB28E2DDB312B2', 'FUNDING_PRO_v1', 'XRPUSDT', 'LONG',
    '2021-08-12 23:00:00', '2021-08-13 03:18:17', 230.69049899, 229.71598254,
    227.2301415, 236.45776146, 0.1014,
    -0.4224, -4.28, 'TIME_EXIT', 4.3,
    0, '1h', '2026-03-08T18:36:22.450004'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4224,
    pnl_amount = -4.28,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'AAB67E7B5E3F7712', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2021-08-21 00:00:00', '2021-08-21 04:15:57', 2194.7382388, 2178.35489163,
    2227.65931238, 2139.86978283, 0.1055,
    0.7465, 7.88, 'TRAILING_STOP', 4.27,
    1, '1h', '2026-03-08T18:36:22.453701'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7465,
    pnl_amount = 7.88,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1675B24CDE8A23C4', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2021-08-22 23:00:00', '2021-08-23 07:32:20', 33967.05646296, 33658.37133422,
    34476.5623099, 33117.88005138, 0.096,
    0.9088, 8.72, 'TRAILING_STOP', 8.54,
    1, '1h', '2026-03-08T18:36:22.449017'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9088,
    pnl_amount = 8.72,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5A1236FA5B40A21C', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2021-08-23 20:00:00', '2021-08-24 00:37:34', 1400.3664519, 1386.7477581,
    1421.37194868, 1365.35729061, 0.0966,
    0.9725, 9.39, 'TAKE_PROFIT', 4.63,
    1, '1h', '2026-03-08T18:36:22.452107'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9725,
    pnl_amount = 9.39,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B34B2D6BE3730915', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2021-09-04 22:00:00', '2021-09-05 02:46:10', 546.924888, 543.20785693,
    555.12876132, 533.2517658, 0.0912,
    0.6796, 6.2, 'TIME_EXIT', 4.77,
    1, '1h', '2026-03-08T18:36:22.449977'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6796,
    pnl_amount = 6.2,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9A0665C5D0580293', 'FUNDING_PRO_v1', 'LINKUSDT', 'LONG',
    '2021-09-20 18:00:00', '2021-09-21 05:24:19', 2576.19805466, 2566.36722465,
    2537.55508384, 2640.60300603, 0.1083,
    -0.3816, -4.13, 'TIME_EXIT', 11.41,
    0, '1h', '2026-03-08T18:36:22.452426'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3816,
    pnl_amount = -4.13,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F2F102DA771E2067', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2021-09-20 22:00:00', '2021-09-21 09:42:26', 4181.5562551, 4148.92166544,
    4244.27959893, 4077.01734872, 0.0837,
    0.7804, 6.53, 'TAKE_PROFIT', 11.71,
    1, '1h', '2026-03-08T18:36:22.453283'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7804,
    pnl_amount = 6.53,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D313A809A65B411E', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2021-09-29 19:00:00', '2021-09-30 06:54:12', 4962.56367851, 4929.47270152,
    5037.00213369, 4838.49958655, 0.0891,
    0.6668, 5.94, 'TRAILING_STOP', 11.9,
    1, '1h', '2026-03-08T18:36:22.453570'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6668,
    pnl_amount = 5.94,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '51D4BF4C49064600', 'FUNDING_PRO_v1', 'ADAUSDT', 'LONG',
    '2021-09-30 03:00:00', '2021-09-30 11:19:07', 808.96468747, 815.55592771,
    796.83021716, 829.18880466, 0.082,
    0.8148, 6.68, 'TIME_EXIT', 8.32,
    1, '1h', '2026-03-08T18:36:22.452599'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8148,
    pnl_amount = 6.68,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9CBE52C550BBD9EC', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2021-09-30 06:00:00', '2021-09-30 10:09:00', 23069.85964081, 23224.56000433,
    22723.8117462, 23646.60613183, 0.0983,
    0.6706, 6.59, 'TAKE_PROFIT', 4.15,
    1, '1h', '2026-03-08T18:36:22.449189'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6706,
    pnl_amount = 6.59,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7D766ADCE029285C', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2021-10-04 13:00:00', '2021-10-04 22:00:49', 170.73780207, 169.36012293,
    173.2988691, 166.46935702, 0.1193,
    0.8069, 9.63, 'TAKE_PROFIT', 9.01,
    1, '1h', '2026-03-08T18:36:22.451351'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8069,
    pnl_amount = 9.63,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8FD68B8B7B848682', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2021-10-08 07:00:00', '2021-10-08 15:44:21', 3880.35102848, 3892.84390236,
    3938.5562939, 3783.34225276, 0.1008,
    -0.322, -3.24, 'STOP_LOSS', 8.74,
    0, '1h', '2026-03-08T18:36:22.449867'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.322,
    pnl_amount = -3.24,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0EBE687F122B4526', 'FUNDING_PRO_v1', 'BNBUSDT', 'SHORT',
    '2021-10-18 17:00:00', '2021-10-19 02:28:57', 982.0825958, 976.34343581,
    996.81383473, 957.5305309, 0.1099,
    0.5844, 6.42, 'TRAILING_STOP', 9.48,
    1, '1h', '2026-03-08T18:36:22.453498'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5844,
    pnl_amount = 6.42,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F3A316BEF91B230F', 'FUNDING_PRO_v1', 'DOGEUSDT', 'SHORT',
    '2021-10-25 08:00:00', '2021-10-25 12:05:46', 2141.6446903, 2151.36339971,
    2173.76936066, 2088.10357304, 0.0809,
    -0.4538, -3.67, 'STOP_LOSS', 4.1,
    0, '1h', '2026-03-08T18:36:22.450821'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4538,
    pnl_amount = -3.67,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5895E4147DF8111B', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2021-11-03 08:00:00', '2021-11-03 10:05:40', 3165.34361331, 3135.0314306,
    3212.82376751, 3086.21002298, 0.0821,
    0.9576, 7.86, 'TAKE_PROFIT', 2.09,
    1, '1h', '2026-03-08T18:36:22.449036'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9576,
    pnl_amount = 7.86,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9DBE3E8C8B89690B', 'FUNDING_PRO_v1', 'XRPUSDT', 'LONG',
    '2021-11-11 19:00:00', '2021-11-11 23:33:41', 409.77683159, 408.21652973,
    403.63017912, 420.02125238, 0.09,
    -0.3808, -3.43, 'TIME_EXIT', 4.56,
    0, '1h', '2026-03-08T18:36:22.452537'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3808,
    pnl_amount = -3.43,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F29E869C83B76F86', 'FUNDING_PRO_v1', 'ADAUSDT', 'LONG',
    '2021-11-12 15:00:00', '2021-11-13 02:31:38', 4354.34100481, 4396.269484,
    4289.02588974, 4463.19952993, 0.0897,
    0.9629, 8.64, 'TIME_EXIT', 11.53,
    1, '1h', '2026-03-08T18:36:22.451434'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9629,
    pnl_amount = 8.64,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '218873FD6DC7A0B7', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2021-11-13 02:00:00', '2021-11-13 10:40:12', 25056.97729609, 24955.6861613,
    24681.12263665, 25683.4017285, 0.1122,
    -0.4042, -4.54, 'STOP_LOSS', 8.67,
    0, '1h', '2026-03-08T18:36:22.452491'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4042,
    pnl_amount = -4.54,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4E96F5DC9A605B2A', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2021-11-14 09:00:00', '2021-11-14 20:00:57', 15325.10164397, 15178.06933964,
    15554.97816863, 14941.97410287, 0.1136,
    0.9594, 10.9, 'TIME_EXIT', 11.02,
    1, '1h', '2026-03-08T18:36:22.453880'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9594,
    pnl_amount = 10.9,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A222276B2C0CC3FA', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2021-11-16 21:00:00', '2021-11-17 02:56:21', 3926.79278903, 3944.49956645,
    3985.69468086, 3828.6229693, 0.1114,
    -0.4509, -5.02, 'TIME_EXIT', 5.94,
    0, '1h', '2026-03-08T18:36:22.452301'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4509,
    pnl_amount = -5.02,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '21C87107505E956A', 'FUNDING_PRO_v1', 'ADAUSDT', 'LONG',
    '2021-11-19 08:00:00', '2021-11-19 11:48:09', 2635.37125748, 2656.40012795,
    2595.84068862, 2701.25553892, 0.1026,
    0.7979, 8.18, 'TAKE_PROFIT', 3.8,
    1, '1h', '2026-03-08T18:36:22.454173'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7979,
    pnl_amount = 8.18,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4D70461AEED04287', 'FUNDING_PRO_v1', 'DOGEUSDT', 'LONG',
    '2021-11-21 15:00:00', '2021-11-21 23:23:47', 3936.02465274, 3961.64317049,
    3876.98428295, 4034.42526906, 0.0964,
    0.6509, 6.27, 'TIME_EXIT', 8.4,
    1, '1h', '2026-03-08T18:36:22.452500'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6509,
    pnl_amount = 6.27,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DD2521EA81424FA3', 'FUNDING_PRO_v1', 'ADAUSDT', 'SHORT',
    '2021-11-24 01:00:00', '2021-11-24 07:47:52', 1986.66009559, 1995.7697161,
    2016.45999702, 1936.9935932, 0.1118,
    -0.4585, -5.12, 'STOP_LOSS', 6.8,
    0, '1h', '2026-03-08T18:36:22.453718'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4585,
    pnl_amount = -5.12,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '91B9D70DEC91A4F7', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2021-12-01 02:00:00', '2021-12-01 04:18:06', 4098.16817984, 4072.19157647,
    4159.64070254, 3995.71397535, 0.0831,
    0.6339, 5.27, 'TAKE_PROFIT', 2.3,
    1, '1h', '2026-03-08T18:36:22.451624'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6339,
    pnl_amount = 5.27,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '090DBA7844DA91B6', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2021-12-01 09:00:00', '2021-12-01 16:06:49', 1158.83394199, 1167.25633367,
    1141.45143286, 1187.80479054, 0.092,
    0.7268, 6.68, 'TIME_EXIT', 7.11,
    1, '1h', '2026-03-08T18:36:22.453551'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7268,
    pnl_amount = 6.68,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '45B814D68D6262AF', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2021-12-09 19:00:00', '2021-12-09 23:26:16', 469.61994136, 472.61095752,
    462.57564224, 481.3604399, 0.1059,
    0.6369, 6.74, 'TRAILING_STOP', 4.44,
    1, '1h', '2026-03-08T18:36:22.450879'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6369,
    pnl_amount = 6.74,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8277F283B5DED7BA', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2021-12-12 19:00:00', '2021-12-13 06:12:23', 116.82007257, 115.90953148,
    118.57237366, 113.89957076, 0.0886,
    0.7794, 6.91, 'TRAILING_STOP', 11.21,
    1, '1h', '2026-03-08T18:36:22.450368'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7794,
    pnl_amount = 6.91,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '58750088DAD366EA', 'FUNDING_PRO_v1', 'ADAUSDT', 'SHORT',
    '2021-12-16 06:00:00', '2021-12-16 17:34:10', 3752.60868002, 3727.66285591,
    3808.89781022, 3658.79346302, 0.1047,
    0.6648, 6.96, 'TIME_EXIT', 11.57,
    1, '1h', '2026-03-08T18:36:22.451055'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6648,
    pnl_amount = 6.96,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BCF9F5851550A581', 'FUNDING_PRO_v1', 'ADAUSDT', 'LONG',
    '2021-12-16 23:00:00', '2021-12-17 07:18:09', 4746.46621266, 4788.60623297,
    4675.26921947, 4865.12786798, 0.0999,
    0.8878, 8.87, 'TAKE_PROFIT', 8.3,
    1, '1h', '2026-03-08T18:36:22.451308'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8878,
    pnl_amount = 8.87,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '00D8AFB77C4E7E5E', 'FUNDING_PRO_v1', 'LINKUSDT', 'LONG',
    '2021-12-18 20:00:00', '2021-12-19 03:59:00', 827.90007667, 835.09575884,
    815.48157552, 848.59757858, 0.0975,
    0.8691, 8.47, 'TAKE_PROFIT', 7.98,
    1, '1h', '2026-03-08T18:36:22.449471'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8691,
    pnl_amount = 8.47,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '305C4E41E9E95093', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2021-12-20 12:00:00', '2021-12-20 21:03:02', 3369.22674035, 3397.78360106,
    3318.68833925, 3453.45740886, 0.113,
    0.8476, 9.58, 'TAKE_PROFIT', 9.05,
    1, '1h', '2026-03-08T18:36:22.449416'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8476,
    pnl_amount = 9.58,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B07FFC55B10DB2B3', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2021-12-27 11:00:00', '2021-12-27 14:36:56', 628.07302677, 631.57131054,
    618.65193136, 643.77485244, 0.1114,
    0.557, 6.21, 'TRAILING_STOP', 3.62,
    1, '1h', '2026-03-08T18:36:22.450312'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.557,
    pnl_amount = 6.21,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E5992C22B52E7DAF', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2021-12-28 13:00:00', '2021-12-28 17:37:34', 3607.59997742, 3635.39559742,
    3553.48597776, 3697.78997686, 0.1085,
    0.7705, 8.36, 'TRAILING_STOP', 4.63,
    1, '1h', '2026-03-08T18:36:22.450773'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7705,
    pnl_amount = 8.36,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6F408BF00CB90101', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2022-01-08 07:00:00', '2022-01-08 14:03:20', 24509.68021673, 24591.70174873,
    24877.32541998, 23896.93821131, 0.0914,
    -0.3346, -3.06, 'TIME_EXIT', 7.06,
    0, '1h', '2026-03-08T18:36:22.451561'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3346,
    pnl_amount = -3.06,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '29E4F93885DE6F8F', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2022-01-12 04:00:00', '2022-01-12 15:41:10', 42311.26852944, 42060.33736711,
    42945.93755738, 41253.4868162, 0.0986,
    0.5931, 5.85, 'TIME_EXIT', 11.69,
    1, '1h', '2026-03-08T18:36:22.450889'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5931,
    pnl_amount = 5.85,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EAEB2915D73BEF9E', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2022-01-17 14:00:00', '2022-01-17 18:55:59', 3264.96974148, 3278.71111934,
    3313.9442876, 3183.34549794, 0.0832,
    -0.4209, -3.5, 'STOP_LOSS', 4.93,
    0, '1h', '2026-03-08T18:36:22.452035'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4209,
    pnl_amount = -3.5,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '489B98C1A4C8618F', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2022-01-27 14:00:00', '2022-01-27 19:02:20', 42098.3394194, 42282.65101097,
    42729.81451069, 41045.88093392, 0.1144,
    -0.4378, -5.01, 'STOP_LOSS', 5.04,
    0, '1h', '2026-03-08T18:36:22.451740'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4378,
    pnl_amount = -5.01,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '98D8E81E882B7F57', 'FUNDING_PRO_v1', 'ADAUSDT', 'SHORT',
    '2022-01-27 19:00:00', '2022-01-28 04:13:58', 897.57061131, 901.20881074,
    911.03417048, 875.13134603, 0.0879,
    -0.4053, -3.56, 'TIME_EXIT', 9.23,
    0, '1h', '2026-03-08T18:36:22.452071'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4053,
    pnl_amount = -3.56,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '74E9BB25A0625F3F', 'FUNDING_PRO_v1', 'ADAUSDT', 'SHORT',
    '2022-01-30 12:00:00', '2022-01-30 19:37:50', 4106.70262123, 4067.92249631,
    4168.30316055, 4004.0350557, 0.0944,
    0.9443, 8.92, 'TIME_EXIT', 7.63,
    1, '1h', '2026-03-08T18:36:22.450869'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9443,
    pnl_amount = 8.92,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B4467205EB8B88D0', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2022-02-04 01:00:00', '2022-02-04 05:42:45', 1076.59030638, 1081.72649887,
    1092.73916097, 1049.67554872, 0.1104,
    -0.4771, -5.27, 'STOP_LOSS', 4.71,
    0, '1h', '2026-03-08T18:36:22.454399'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4771,
    pnl_amount = -5.27,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3141D8B3C95B9C64', 'FUNDING_PRO_v1', 'DOTUSDT', 'LONG',
    '2022-02-12 06:00:00', '2022-02-12 14:49:18', 4455.42037294, 4435.60128212,
    4388.58906735, 4566.80588227, 0.0916,
    -0.4448, -4.08, 'STOP_LOSS', 8.82,
    0, '1h', '2026-03-08T18:36:22.452026'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4448,
    pnl_amount = -4.08,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '54A724C00BC32ACB', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2022-02-13 11:00:00', '2022-02-13 18:11:43', 1351.04250857, 1341.79597069,
    1371.3081462, 1317.26644586, 0.1017,
    0.6844, 6.96, 'TIME_EXIT', 7.2,
    1, '1h', '2026-03-08T18:36:22.451390'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6844,
    pnl_amount = 6.96,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '53037A12B149E61E', 'FUNDING_PRO_v1', 'DOGEUSDT', 'SHORT',
    '2022-02-14 23:00:00', '2022-02-15 01:43:35', 2403.69752866, 2384.01219589,
    2439.75299159, 2343.60509045, 0.1065,
    0.819, 8.72, 'TIME_EXIT', 2.73,
    1, '1h', '2026-03-08T18:36:22.454195'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.819,
    pnl_amount = 8.72,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BFD5CA87654462F3', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2022-02-15 11:00:00', '2022-02-15 21:43:13', 2991.32645923, 2966.34416599,
    3036.19635611, 2916.54329774, 0.0828,
    0.8352, 6.91, 'TRAILING_STOP', 10.72,
    1, '1h', '2026-03-08T18:36:22.454204'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8352,
    pnl_amount = 6.91,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D7BF534E51E276EA', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2022-02-16 22:00:00', '2022-02-17 01:24:54', 4973.68911431, 5012.35708122,
    4899.08377759, 5098.03134217, 0.0882,
    0.7775, 6.86, 'TIME_EXIT', 3.42,
    1, '1h', '2026-03-08T18:36:22.449858'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7775,
    pnl_amount = 6.86,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FA47DB58B490BE5B', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2022-02-20 23:00:00', '2022-02-21 07:44:54', 4672.05617098, 4712.45049758,
    4601.97532841, 4788.85757525, 0.087,
    0.8646, 7.52, 'TRAILING_STOP', 8.75,
    1, '1h', '2026-03-08T18:36:22.450340'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8646,
    pnl_amount = 7.52,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DFBE785372AA3B97', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2022-02-21 17:00:00', '2022-02-21 20:57:41', 49871.3988145, 50191.27433734,
    49123.32783228, 51118.18378486, 0.111,
    0.6414, 7.12, 'TIME_EXIT', 3.96,
    1, '1h', '2026-03-08T18:36:22.450195'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6414,
    pnl_amount = 7.12,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '75D91749FBF9BB5A', 'FUNDING_PRO_v1', 'AVAXUSDT', 'LONG',
    '2022-02-22 04:00:00', '2022-02-22 14:55:31', 131.24036998, 130.66886713,
    129.27176443, 134.52137923, 0.1119,
    -0.4355, -4.87, 'TIME_EXIT', 10.93,
    0, '1h', '2026-03-08T18:36:22.453653'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4355,
    pnl_amount = -4.87,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '300AE5EE032DDE4B', 'FUNDING_PRO_v1', 'BNBUSDT', 'SHORT',
    '2022-02-22 07:00:00', '2022-02-22 16:33:29', 53.15715185, 52.78514544,
    53.95450913, 51.82822306, 0.1023,
    0.6998, 7.16, 'TIME_EXIT', 9.56,
    1, '1h', '2026-03-08T18:36:22.454263'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6998,
    pnl_amount = 7.16,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8EEC60DFB2887633', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2022-02-26 19:00:00', '2022-02-27 00:42:40', 42617.09496075, 42308.17439665,
    43256.35138516, 41551.66758673, 0.0877,
    0.7249, 6.36, 'TIME_EXIT', 5.71,
    1, '1h', '2026-03-08T18:36:22.452315'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7249,
    pnl_amount = 6.36,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0BF5C683E1A7C31E', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2022-02-28 22:00:00', '2022-03-01 06:16:43', 1951.29498836, 1967.29615422,
    1922.02556354, 2000.07736307, 0.0907,
    0.82, 7.44, 'TAKE_PROFIT', 8.28,
    1, '1h', '2026-03-08T18:36:22.452518'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.82,
    pnl_amount = 7.44,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4AEDAA6CCC3D66BE', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2022-03-02 23:00:00', '2022-03-03 01:00:04', 3461.76519142, 3446.19436812,
    3409.83871355, 3548.30932121, 0.0953,
    -0.4498, -4.29, 'TIME_EXIT', 2.0,
    0, '1h', '2026-03-08T18:36:22.454448'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4498,
    pnl_amount = -4.29,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B744FB7CF66D6D88', 'FUNDING_PRO_v1', 'XRPUSDT', 'LONG',
    '2022-03-04 05:00:00', '2022-03-04 09:54:47', 4517.56133152, 4543.39675778,
    4449.79791155, 4630.50036481, 0.1063,
    0.5719, 6.08, 'TRAILING_STOP', 4.91,
    1, '1h', '2026-03-08T18:36:22.454002'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5719,
    pnl_amount = 6.08,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '46529B8BBCA43C7E', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2022-03-05 06:00:00', '2022-03-05 15:38:18', 2804.10578121, 2818.66592504,
    2762.04419449, 2874.20842574, 0.1103,
    0.5192, 5.73, 'TRAILING_STOP', 9.64,
    1, '1h', '2026-03-08T18:36:22.449785'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5192,
    pnl_amount = 5.73,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6C16F98454136BC3', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2022-03-18 02:00:00', '2022-03-18 05:32:27', 12436.42086811, 12510.37333742,
    12249.87455509, 12747.33138981, 0.1124,
    0.5946, 6.69, 'TIME_EXIT', 3.54,
    1, '1h', '2026-03-08T18:36:22.450186'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5946,
    pnl_amount = 6.69,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8A70B9289531BA1B', 'FUNDING_PRO_v1', 'XRPUSDT', 'SHORT',
    '2022-03-28 00:00:00', '2022-03-28 07:44:56', 3846.53041101, 3859.12510043,
    3904.22836717, 3750.36715073, 0.0809,
    -0.3274, -2.65, 'STOP_LOSS', 7.75,
    0, '1h', '2026-03-08T18:36:22.454497'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3274,
    pnl_amount = -2.65,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B9CE7525293D29A9', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2022-03-28 02:00:00', '2022-03-28 04:42:15', 31987.167963, 31844.14576591,
    31507.36044355, 32786.84716207, 0.1189,
    -0.4471, -5.32, 'STOP_LOSS', 2.7,
    0, '1h', '2026-03-08T18:36:22.449094'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4471,
    pnl_amount = -5.32,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '325A5A579F064CF4', 'FUNDING_PRO_v1', 'DOGEUSDT', 'LONG',
    '2022-03-31 17:00:00', '2022-04-01 02:03:36', 1577.14587275, 1587.58518428,
    1553.48868466, 1616.57451957, 0.1092,
    0.6619, 7.23, 'TIME_EXIT', 9.06,
    1, '1h', '2026-03-08T18:36:22.449321'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6619,
    pnl_amount = 7.23,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B1822FB97E4298A6', 'FUNDING_PRO_v1', 'DOTUSDT', 'LONG',
    '2022-04-05 05:00:00', '2022-04-05 15:31:48', 2206.93873257, 2198.6346271,
    2173.83465158, 2262.11220088, 0.1146,
    -0.3763, -4.31, 'TIME_EXIT', 10.53,
    0, '1h', '2026-03-08T18:36:22.451722'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3763,
    pnl_amount = -4.31,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '05EEFD94DE4AFA40', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2022-04-05 23:00:00', '2022-04-06 10:19:01', 4939.78214384, 4916.92041202,
    4865.68541168, 5063.27669743, 0.0884,
    -0.4628, -4.09, 'TIME_EXIT', 11.32,
    0, '1h', '2026-03-08T18:36:22.449923'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4628,
    pnl_amount = -4.09,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D97A36A964222698', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2022-04-07 05:00:00', '2022-04-07 14:29:00', 415.18769, 419.14661912,
    408.95987465, 425.56738225, 0.1154,
    0.9535, 11.0, 'TAKE_PROFIT', 9.48,
    1, '1h', '2026-03-08T18:36:22.453369'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9535,
    pnl_amount = 11.0,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F9CF0880EDB53A3B', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2022-04-10 07:00:00', '2022-04-10 13:04:57', 42930.92933457, 43113.12279334,
    43574.89327459, 41857.65610121, 0.0868,
    -0.4244, -3.68, 'TIME_EXIT', 6.08,
    0, '1h', '2026-03-08T18:36:22.453906'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4244,
    pnl_amount = -3.68,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'AC66447B007B5C53', 'FUNDING_PRO_v1', 'XRPUSDT', 'LONG',
    '2022-04-11 07:00:00', '2022-04-11 15:01:09', 2688.25749407, 2702.26220859,
    2647.93363166, 2755.46393142, 0.0833,
    0.521, 4.34, 'TRAILING_STOP', 8.02,
    1, '1h', '2026-03-08T18:36:22.451380'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.521,
    pnl_amount = 4.34,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EFFD847E2BD75AFC', 'FUNDING_PRO_v1', 'LINKUSDT', 'LONG',
    '2022-04-22 02:00:00', '2022-04-22 10:37:23', 1464.4884554, 1475.95801344,
    1442.52112856, 1501.10066678, 0.1092,
    0.7832, 8.56, 'TRAILING_STOP', 8.62,
    1, '1h', '2026-03-08T18:36:22.450924'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7832,
    pnl_amount = 8.56,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '517CD80D6747FA46', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2022-04-22 09:00:00', '2022-04-22 17:55:44', 5846.75766061, 5805.54640938,
    5934.45902552, 5700.58871909, 0.1019,
    0.7049, 7.18, 'TRAILING_STOP', 8.93,
    1, '1h', '2026-03-08T18:36:22.450933'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7049,
    pnl_amount = 7.18,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8EF06F12275B5107', 'FUNDING_PRO_v1', 'XRPUSDT', 'SHORT',
    '2022-04-25 02:00:00', '2022-04-25 06:12:48', 4660.82040051, 4619.76386623,
    4730.73270652, 4544.2998905, 0.0887,
    0.8809, 7.81, 'TRAILING_STOP', 4.21,
    1, '1h', '2026-03-08T18:36:22.452354'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8809,
    pnl_amount = 7.81,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C8AFC165A31C1296', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2022-04-26 23:00:00', '2022-04-27 09:36:24', 468.52416586, 470.25815794,
    475.55202835, 456.81106172, 0.1083,
    -0.3701, -4.01, 'STOP_LOSS', 10.61,
    0, '1h', '2026-03-08T18:36:22.451202'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3701,
    pnl_amount = -4.01,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '07CD07F208426E06', 'FUNDING_PRO_v1', 'AVAXUSDT', 'LONG',
    '2022-04-28 02:00:00', '2022-04-28 05:54:42', 4785.77024521, 4817.96819504,
    4713.98369153, 4905.41450134, 0.1017,
    0.6728, 6.84, 'TIME_EXIT', 3.91,
    1, '1h', '2026-03-08T18:36:22.452089'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6728,
    pnl_amount = 6.84,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3C97482E8208EC90', 'FUNDING_PRO_v1', 'AVAXUSDT', 'SHORT',
    '2022-04-28 08:00:00', '2022-04-28 18:04:47', 145.36446267, 146.02130945,
    147.54492961, 141.7303511, 0.0991,
    -0.4519, -4.48, 'TIME_EXIT', 10.08,
    0, '1h', '2026-03-08T18:36:22.449256'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4519,
    pnl_amount = -4.48,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9AE3A56490E65224', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2022-05-02 16:00:00', '2022-05-03 03:52:31', 3632.38957806, 3661.65892874,
    3577.90373439, 3723.19931751, 0.1146,
    0.8058, 9.24, 'TIME_EXIT', 11.88,
    1, '1h', '2026-03-08T18:36:22.452152'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8058,
    pnl_amount = 9.24,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'ADB8C99875479CE3', 'FUNDING_PRO_v1', 'DOGEUSDT', 'LONG',
    '2022-05-06 15:00:00', '2022-05-06 18:22:55', 1797.84958226, 1813.01225284,
    1770.88183853, 1842.79582182, 0.1044,
    0.8434, 8.8, 'TIME_EXIT', 3.38,
    1, '1h', '2026-03-08T18:36:22.453011'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8434,
    pnl_amount = 8.8,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4E77DA04B94DCB59', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2022-05-08 13:00:00', '2022-05-08 19:42:57', 44935.38011861, 45104.58346312,
    45609.41082039, 43811.99561565, 0.0894,
    -0.3765, -3.37, 'STOP_LOSS', 6.72,
    0, '1h', '2026-03-08T18:36:22.454121'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3765,
    pnl_amount = -3.37,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '276863FB1C3EF71A', 'FUNDING_PRO_v1', 'ADAUSDT', 'LONG',
    '2022-05-08 22:00:00', '2022-05-09 08:53:02', 178.62960238, 178.047863,
    175.95015835, 183.09534244, 0.1024,
    -0.3257, -3.34, 'STOP_LOSS', 10.88,
    0, '1h', '2026-03-08T18:36:22.452771'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3257,
    pnl_amount = -3.34,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0DF95FC99994CD0D', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2022-05-14 16:00:00', '2022-05-15 01:26:00', 1199.53416046, 1210.58027513,
    1181.54114805, 1229.52251447, 0.0813,
    0.9209, 7.49, 'TAKE_PROFIT', 9.43,
    1, '1h', '2026-03-08T18:36:22.453835'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9209,
    pnl_amount = 7.49,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A87A87EA568FA9D2', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2022-05-15 03:00:00', '2022-05-15 10:13:50', 5934.42620361, 5899.77851721,
    6023.44259667, 5786.06554852, 0.0879,
    0.5838, 5.13, 'TRAILING_STOP', 7.23,
    1, '1h', '2026-03-08T18:36:22.451927'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5838,
    pnl_amount = 5.13,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'ADFEE3540BB47D48', 'FUNDING_PRO_v1', 'ADAUSDT', 'LONG',
    '2022-05-19 13:00:00', '2022-05-19 19:07:19', 4190.22214012, 4218.16392933,
    4127.36880802, 4294.97769362, 0.1184,
    0.6668, 7.9, 'TRAILING_STOP', 6.12,
    1, '1h', '2026-03-08T18:36:22.451298'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6668,
    pnl_amount = 7.9,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9030C9E0023D212E', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2022-05-19 14:00:00', '2022-05-19 18:29:26', 3215.3538579, 3203.89477186,
    3167.12355003, 3295.73770434, 0.0974,
    -0.3564, -3.47, 'STOP_LOSS', 4.49,
    0, '1h', '2026-03-08T18:36:22.450860'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3564,
    pnl_amount = -3.47,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3A9DBF7162B3D14B', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2022-05-30 09:00:00', '2022-05-30 20:14:44', 4523.98546307, 4563.65238008,
    4456.12568112, 4637.08509965, 0.0871,
    0.8768, 7.64, 'TRAILING_STOP', 11.25,
    1, '1h', '2026-03-08T18:36:22.452117'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8768,
    pnl_amount = 7.64,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7F349E252FC76769', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2022-05-30 23:00:00', '2022-05-31 10:18:04', 1139.450063, 1143.49123924,
    1156.54181394, 1110.96381142, 0.0827,
    -0.3547, -2.93, 'STOP_LOSS', 11.3,
    0, '1h', '2026-03-08T18:36:22.454430'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3547,
    pnl_amount = -2.93,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C59B6FA02D35CB32', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2022-06-06 15:00:00', '2022-06-07 00:51:41', 99.07761056, 98.19951487,
    100.56377472, 96.60067029, 0.0934,
    0.8863, 8.28, 'TIME_EXIT', 9.86,
    1, '1h', '2026-03-08T18:36:22.451516'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8863,
    pnl_amount = 8.28,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A706757927D9D390', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2022-06-09 12:00:00', '2022-06-09 15:18:59', 42672.02451749, 42480.39956927,
    42031.94414973, 43738.82513043, 0.0915,
    -0.4491, -4.11, 'TIME_EXIT', 3.32,
    0, '1h', '2026-03-08T18:36:22.449275'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4491,
    pnl_amount = -4.11,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '75BE8102BA8EE8BF', 'FUNDING_PRO_v1', 'LINKUSDT', 'LONG',
    '2022-06-12 08:00:00', '2022-06-12 11:02:45', 4451.18301682, 4484.74018429,
    4384.41527157, 4562.46259224, 0.0956,
    0.7539, 7.21, 'TAKE_PROFIT', 3.05,
    1, '1h', '2026-03-08T18:36:22.450674'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7539,
    pnl_amount = 7.21,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B8334264FB8B900B', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2022-06-13 07:00:00', '2022-06-13 12:04:24', 1116.52088538, 1112.70277644,
    1099.7730721, 1144.43390751, 0.104,
    -0.342, -3.56, 'TIME_EXIT', 5.07,
    0, '1h', '2026-03-08T18:36:22.449246'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.342,
    pnl_amount = -3.56,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DC497797A176AF14', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2022-06-20 18:00:00', '2022-06-21 05:35:22', 4394.67434568, 4354.77012472,
    4460.59446087, 4284.80748704, 0.0824,
    0.908, 7.48, 'TRAILING_STOP', 11.59,
    1, '1h', '2026-03-08T18:36:22.451918'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.908,
    pnl_amount = 7.48,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7C0B81003B99E31A', 'FUNDING_PRO_v1', 'LINKUSDT', 'LONG',
    '2022-06-23 02:00:00', '2022-06-23 12:03:22', 2232.74503593, 2223.14095381,
    2199.25386039, 2288.56366183, 0.114,
    -0.4301, -4.9, 'TIME_EXIT', 10.06,
    0, '1h', '2026-03-08T18:36:22.452509'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4301,
    pnl_amount = -4.9,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '600382ED5609D62C', 'FUNDING_PRO_v1', 'DOTUSDT', 'LONG',
    '2022-06-23 22:00:00', '2022-06-24 00:47:12', 4364.64207974, 4346.63139384,
    4299.17244855, 4473.75813174, 0.0813,
    -0.4126, -3.36, 'STOP_LOSS', 2.79,
    0, '1h', '2026-03-08T18:36:22.450331'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4126,
    pnl_amount = -3.36,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1E0566730A8CEC25', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2022-06-24 08:00:00', '2022-06-24 13:05:37', 2321.19113729, 2328.73906507,
    2356.00900435, 2263.16135886, 0.1069,
    -0.3252, -3.48, 'TIME_EXIT', 5.09,
    0, '1h', '2026-03-08T18:36:22.450729'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3252,
    pnl_amount = -3.48,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'CBD0F67DAAC0CAB3', 'FUNDING_PRO_v1', 'DOGEUSDT', 'LONG',
    '2022-06-28 16:00:00', '2022-06-29 01:47:55', 2495.7436558, 2484.6071119,
    2458.30750096, 2558.13724719, 0.1154,
    -0.4462, -5.15, 'TIME_EXIT', 9.8,
    0, '1h', '2026-03-08T18:36:22.449170'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4462,
    pnl_amount = -5.15,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EFD5120B915D3DCA', 'FUNDING_PRO_v1', 'DOTUSDT', 'SHORT',
    '2022-07-08 13:00:00', '2022-07-08 15:00:22', 1827.01870245, 1815.34538322,
    1854.42398299, 1781.34323489, 0.1131,
    0.6389, 7.22, 'TRAILING_STOP', 2.01,
    1, '1h', '2026-03-08T18:36:22.449702'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6389,
    pnl_amount = 7.22,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DD683F9C9F6C5049', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2022-07-12 09:00:00', '2022-07-12 19:27:51', 4031.3301063, 4056.49426343,
    3970.86015471, 4132.11335896, 0.0929,
    0.6242, 5.8, 'TRAILING_STOP', 10.46,
    1, '1h', '2026-03-08T18:36:22.454035'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6242,
    pnl_amount = 5.8,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '96196F04F5097054', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2022-07-16 09:00:00', '2022-07-16 20:52:47', 842.412648, 845.21968989,
    855.04883772, 821.3523318, 0.0957,
    -0.3332, -3.19, 'STOP_LOSS', 11.88,
    0, '1h', '2026-03-08T18:36:22.453662'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3332,
    pnl_amount = -3.19,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FD3F9F2D2F99E5BD', 'FUNDING_PRO_v1', 'ADAUSDT', 'SHORT',
    '2022-07-18 18:00:00', '2022-07-19 02:38:13', 3015.04984397, 3027.12937607,
    3060.27559163, 2939.67359787, 0.1098,
    -0.4006, -4.4, 'STOP_LOSS', 8.64,
    0, '1h', '2026-03-08T18:36:22.449293'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4006,
    pnl_amount = -4.4,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8DEE549FFE5B4CC7', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2022-07-19 08:00:00', '2022-07-19 11:54:04', 9043.45348049, 8957.90477469,
    9179.10528269, 8817.36714347, 0.1078,
    0.946, 10.2, 'TIME_EXIT', 3.9,
    1, '1h', '2026-03-08T18:36:22.451954'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.946,
    pnl_amount = 10.2,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '473C39650AA97221', 'FUNDING_PRO_v1', 'DOGEUSDT', 'LONG',
    '2022-07-23 05:00:00', '2022-07-23 12:26:22', 3681.53580572, 3714.12947986,
    3626.31276863, 3773.57420086, 0.0956,
    0.8853, 8.46, 'TRAILING_STOP', 7.44,
    1, '1h', '2026-03-08T18:36:22.450394'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8853,
    pnl_amount = 8.46,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '24994AB444A83072', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2022-07-27 22:00:00', '2022-07-28 03:02:54', 26495.79790123, 26390.5583603,
    26098.36093271, 27158.19284876, 0.1095,
    -0.3972, -4.35, 'TIME_EXIT', 5.05,
    0, '1h', '2026-03-08T18:36:22.454273'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3972,
    pnl_amount = -4.35,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8297A0E01F12C805', 'FUNDING_PRO_v1', 'DOTUSDT', 'LONG',
    '2022-07-29 08:00:00', '2022-07-29 15:56:55', 1832.43460462, 1845.97055349,
    1804.94808555, 1878.24546973, 0.1126,
    0.7387, 8.32, 'TRAILING_STOP', 7.95,
    1, '1h', '2026-03-08T18:36:22.450517'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7387,
    pnl_amount = 8.32,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4A60CA2B299EA4FC', 'FUNDING_PRO_v1', 'DOGEUSDT', 'LONG',
    '2022-08-03 04:00:00', '2022-08-03 08:41:50', 1319.56394915, 1326.81219439,
    1299.77048991, 1352.55304787, 0.0806,
    0.5493, 4.43, 'TAKE_PROFIT', 4.7,
    1, '1h', '2026-03-08T18:36:22.451650'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5493,
    pnl_amount = 4.43,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8893D68F0039CAF8', 'FUNDING_PRO_v1', 'DOTUSDT', 'LONG',
    '2022-08-03 12:00:00', '2022-08-03 18:44:17', 3335.45580344, 3365.7489581,
    3285.42396639, 3418.84219853, 0.0962,
    0.9082, 8.73, 'TIME_EXIT', 6.74,
    1, '1h', '2026-03-08T18:36:22.451334'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9082,
    pnl_amount = 8.73,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B6DD451F0154310C', 'FUNDING_PRO_v1', 'LINKUSDT', 'SHORT',
    '2022-08-05 06:00:00', '2022-08-05 13:51:34', 992.07727908, 985.09444585,
    1006.95843827, 967.2753471, 0.1174,
    0.7039, 8.26, 'TRAILING_STOP', 7.86,
    1, '1h', '2026-03-08T18:36:22.453957'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7039,
    pnl_amount = 8.26,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5CCB1234BE24DE41', 'FUNDING_PRO_v1', 'ADAUSDT', 'LONG',
    '2022-08-14 10:00:00', '2022-08-14 16:11:59', 1412.54142664, 1407.09131394,
    1391.35330524, 1447.85496231, 0.1167,
    -0.3858, -4.5, 'TIME_EXIT', 6.2,
    0, '1h', '2026-03-08T18:36:22.452062'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3858,
    pnl_amount = -4.5,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '10748FA609CC21C1', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2022-08-17 20:00:00', '2022-08-18 07:27:35', 2957.8145016, 2978.4976518,
    2913.44728407, 3031.75986414, 0.1045,
    0.6993, 7.3, 'TIME_EXIT', 11.46,
    1, '1h', '2026-03-08T18:36:22.450243'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6993,
    pnl_amount = 7.3,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B2D647C2541A048E', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2022-08-18 09:00:00', '2022-08-18 19:13:53', 33007.17045117, 32753.70187909,
    33502.27800794, 32181.99118989, 0.1065,
    0.7679, 8.18, 'TRAILING_STOP', 10.23,
    1, '1h', '2026-03-08T18:36:22.450997'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7679,
    pnl_amount = 8.18,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '02D88EAF529799D1', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2022-08-20 04:00:00', '2022-08-20 08:13:38', 3724.78004348, 3752.43514396,
    3668.90834282, 3817.89954456, 0.0824,
    0.7425, 6.12, 'TRAILING_STOP', 4.23,
    1, '1h', '2026-03-08T18:36:22.450897'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7425,
    pnl_amount = 6.12,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '89CABFA76E9032FD', 'FUNDING_PRO_v1', 'XRPUSDT', 'LONG',
    '2022-08-21 15:00:00', '2022-08-21 21:24:29', 1127.12930989, 1137.13816549,
    1110.22237024, 1155.30754264, 0.0854,
    0.888, 7.58, 'TIME_EXIT', 6.41,
    1, '1h', '2026-03-08T18:36:22.454063'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.888,
    pnl_amount = 7.58,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7C37C4304CCA2AA1', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2022-08-22 13:00:00', '2022-08-22 23:28:24', 4024.27771508, 4061.51328518,
    3963.91354935, 4124.88465796, 0.1153,
    0.9253, 10.67, 'TIME_EXIT', 10.47,
    1, '1h', '2026-03-08T18:36:22.453185'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9253,
    pnl_amount = 10.67,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '448CD492B828708F', 'FUNDING_PRO_v1', 'AVAXUSDT', 'SHORT',
    '2022-08-27 23:00:00', '2022-08-28 03:14:05', 4378.80287648, 4339.50213843,
    4444.48491963, 4269.33280457, 0.1078,
    0.8975, 9.68, 'TRAILING_STOP', 4.23,
    1, '1h', '2026-03-08T18:36:22.450466'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8975,
    pnl_amount = 9.68,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '823A1DD26A49AD4D', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2022-08-28 03:00:00', '2022-08-28 05:33:35', 48641.30380025, 48257.39253739,
    49370.92335725, 47425.27120524, 0.0808,
    0.7893, 6.38, 'TIME_EXIT', 2.56,
    1, '1h', '2026-03-08T18:36:22.450784'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7893,
    pnl_amount = 6.38,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'AE9DAC015D6BDC3B', 'FUNDING_PRO_v1', 'DOTUSDT', 'SHORT',
    '2022-08-29 13:00:00', '2022-08-29 15:05:08', 407.83584526, 404.18514479,
    413.95338294, 397.63994913, 0.0802,
    0.8951, 7.18, 'TRAILING_STOP', 2.09,
    1, '1h', '2026-03-08T18:36:22.454213'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8951,
    pnl_amount = 7.18,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C001E70769B25E84', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2022-09-04 03:00:00', '2022-09-04 05:28:50', 1062.80663848, 1072.09689897,
    1046.8645389, 1089.37680444, 0.0809,
    0.8741, 7.07, 'TRAILING_STOP', 2.48,
    1, '1h', '2026-03-08T18:36:22.451775'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8741,
    pnl_amount = 7.07,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5BE492911D49584C', 'FUNDING_PRO_v1', 'ADAUSDT', 'SHORT',
    '2022-09-06 08:00:00', '2022-09-06 18:21:35', 638.44584935, 633.58322331,
    648.02253709, 622.48470311, 0.1012,
    0.7616, 7.71, 'TIME_EXIT', 10.36,
    1, '1h', '2026-03-08T18:36:22.452789'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7616,
    pnl_amount = 7.71,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7679F724A706D418', 'FUNDING_PRO_v1', 'XRPUSDT', 'LONG',
    '2022-09-07 03:00:00', '2022-09-07 14:18:29', 519.02399079, 523.27520605,
    511.23863092, 531.99959056, 0.1185,
    0.8191, 9.7, 'TRAILING_STOP', 11.31,
    1, '1h', '2026-03-08T18:36:22.450403'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8191,
    pnl_amount = 9.7,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '13B0775CE2302709', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2022-09-08 06:00:00', '2022-09-08 15:48:46', 9945.9665144, 9875.18155457,
    10095.15601212, 9697.31735154, 0.113,
    0.7117, 8.04, 'TRAILING_STOP', 9.81,
    1, '1h', '2026-03-08T18:36:22.449573'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7117,
    pnl_amount = 8.04,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2B339820AC4FDF42', 'FUNDING_PRO_v1', 'DOTUSDT', 'LONG',
    '2022-09-13 10:00:00', '2022-09-13 15:35:40', 244.10925694, 246.09647655,
    240.44761809, 250.21198837, 0.1113,
    0.8141, 9.06, 'TIME_EXIT', 5.59,
    1, '1h', '2026-03-08T18:36:22.452382'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8141,
    pnl_amount = 9.06,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D7984C6DB881CD75', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2022-09-13 11:00:00', '2022-09-13 20:19:26', 49346.58469999, 48875.39955851,
    50086.78347049, 48112.92008249, 0.0924,
    0.9548, 8.82, 'TRAILING_STOP', 9.32,
    1, '1h', '2026-03-08T18:36:22.452345'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9548,
    pnl_amount = 8.82,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8E5C7BC3BC204DFE', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2022-09-14 04:00:00', '2022-09-14 08:48:58', 32922.62399856, 32806.27506231,
    32428.78463858, 33745.68959853, 0.0959,
    -0.3534, -3.39, 'TIME_EXIT', 4.82,
    0, '1h', '2026-03-08T18:36:22.454147'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3534,
    pnl_amount = -3.39,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2F8177E3374E2788', 'FUNDING_PRO_v1', 'XRPUSDT', 'SHORT',
    '2022-09-19 01:00:00', '2022-09-19 10:54:52', 1595.04214582, 1585.66382612,
    1618.96777801, 1555.16609218, 0.0942,
    0.588, 5.54, 'TAKE_PROFIT', 9.91,
    1, '1h', '2026-03-08T18:36:22.452008'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.588,
    pnl_amount = 5.54,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D6290BD93508D327', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2022-09-21 18:00:00', '2022-09-22 01:58:47', 4232.59681936, 4212.89839657,
    4169.10786707, 4338.41173985, 0.1033,
    -0.4654, -4.81, 'TIME_EXIT', 7.98,
    0, '1h', '2026-03-08T18:36:22.454458'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4654,
    pnl_amount = -4.81,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3747DD066DF86AFA', 'FUNDING_PRO_v1', 'AVAXUSDT', 'SHORT',
    '2022-09-23 06:00:00', '2022-09-23 11:55:17', 2518.7055382, 2500.0794551,
    2556.48612127, 2455.73789974, 0.1145,
    0.7395, 8.46, 'TAKE_PROFIT', 5.92,
    1, '1h', '2026-03-08T18:36:22.450321'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7395,
    pnl_amount = 8.46,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B9B557A1859589A9', 'FUNDING_PRO_v1', 'LINKUSDT', 'SHORT',
    '2022-09-26 00:00:00', '2022-09-26 11:39:56', 4359.0568942, 4327.34958912,
    4424.44274762, 4250.08047185, 0.0874,
    0.7274, 6.36, 'TIME_EXIT', 11.67,
    1, '1h', '2026-03-08T18:36:22.453644'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7274,
    pnl_amount = 6.36,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '720251A3EDDC76CB', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2022-09-27 09:00:00', '2022-09-27 18:44:23', 2101.58297536, 2111.0226487,
    2133.10671999, 2049.04340098, 0.1137,
    -0.4492, -5.11, 'STOP_LOSS', 9.74,
    0, '1h', '2026-03-08T18:36:22.451909'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4492,
    pnl_amount = -5.11,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FA71D34313ABCA32', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2022-09-29 00:00:00', '2022-09-29 10:56:24', 12202.37519576, 12252.90972453,
    12385.4108237, 11897.31581587, 0.0924,
    -0.4141, -3.83, 'STOP_LOSS', 10.94,
    0, '1h', '2026-03-08T18:36:22.452390'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4141,
    pnl_amount = -3.83,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F56365506C4CCCE6', 'FUNDING_PRO_v1', 'ADAUSDT', 'SHORT',
    '2022-09-30 04:00:00', '2022-09-30 15:32:12', 3629.17357313, 3645.3255259,
    3683.61117673, 3538.4442338, 0.1179,
    -0.4451, -5.25, 'STOP_LOSS', 11.54,
    0, '1h', '2026-03-08T18:36:22.449592'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4451,
    pnl_amount = -5.25,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3EAE631EA9AA1185', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2022-10-03 14:00:00', '2022-10-03 17:12:33', 2312.96632701, 2303.02291912,
    2278.27183211, 2370.79048519, 0.1162,
    -0.4299, -5.0, 'STOP_LOSS', 3.21,
    0, '1h', '2026-03-08T18:36:22.454053'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4299,
    pnl_amount = -5.0,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '80F012EF04495D9F', 'FUNDING_PRO_v1', 'DOGEUSDT', 'SHORT',
    '2022-10-08 05:00:00', '2022-10-08 10:56:23', 132.26108304, 132.71956827,
    134.24499928, 128.95455596, 0.1164,
    -0.3467, -4.03, 'STOP_LOSS', 5.94,
    0, '1h', '2026-03-08T18:36:22.451793'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3467,
    pnl_amount = -4.03,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F8CCB927AABCA74B', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2022-10-08 12:00:00', '2022-10-08 21:16:45', 297.93331465, 299.46311366,
    293.46431493, 305.38164751, 0.1074,
    0.5135, 5.52, 'TIME_EXIT', 9.28,
    1, '1h', '2026-03-08T18:36:22.450052'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5135,
    pnl_amount = 5.52,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '091A6A027C64B2A4', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2022-10-09 14:00:00', '2022-10-10 00:19:32', 17.25892917, 17.1382838,
    17.5178131, 16.82745594, 0.1169,
    0.699, 8.17, 'TRAILING_STOP', 10.33,
    1, '1h', '2026-03-08T18:36:22.452826'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.699,
    pnl_amount = 8.17,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'ACC894BCCC813C57', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2022-10-15 13:00:00', '2022-10-15 23:01:51', 929.26467063, 922.68693873,
    943.20364069, 906.03305387, 0.1034,
    0.7078, 7.32, 'TIME_EXIT', 10.03,
    1, '1h', '2026-03-08T18:36:22.452417'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7078,
    pnl_amount = 7.32,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1D4AEE618E17F15A', 'FUNDING_PRO_v1', 'LINKUSDT', 'LONG',
    '2022-10-16 05:00:00', '2022-10-16 11:09:54', 4098.16077352, 4079.22726629,
    4036.68836192, 4200.61479286, 0.1111,
    -0.462, -5.13, 'STOP_LOSS', 6.17,
    0, '1h', '2026-03-08T18:36:22.450508'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.462,
    pnl_amount = -5.13,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '968512DA5A3E9576', 'FUNDING_PRO_v1', 'XRPUSDT', 'LONG',
    '2022-10-25 21:00:00', '2022-10-26 04:56:22', 4050.36300556, 4077.67821486,
    3989.60756048, 4151.6220807, 0.1099,
    0.6744, 7.41, 'TRAILING_STOP', 7.94,
    1, '1h', '2026-03-08T18:36:22.453966'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6744,
    pnl_amount = 7.41,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'CFDA323F397E405C', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2022-10-30 16:00:00', '2022-10-30 21:01:58', 4049.98143591, 4077.15198709,
    3989.23171437, 4151.2309718, 0.1074,
    0.6709, 7.21, 'TIME_EXIT', 5.03,
    1, '1h', '2026-03-08T18:36:22.449406'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6709,
    pnl_amount = 7.21,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2973759C3FB71CA1', 'FUNDING_PRO_v1', 'XRPUSDT', 'LONG',
    '2022-11-01 20:00:00', '2022-11-02 07:28:52', 1282.36573706, 1294.60600638,
    1263.130251, 1314.42488049, 0.1154,
    0.9545, 11.01, 'TAKE_PROFIT', 11.48,
    1, '1h', '2026-03-08T18:36:22.450794'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9545,
    pnl_amount = 11.01,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4291F7AA035013E7', 'FUNDING_PRO_v1', 'AVAXUSDT', 'SHORT',
    '2022-11-04 03:00:00', '2022-11-04 05:04:35', 1543.50383357, 1549.53424181,
    1566.65639108, 1504.91623773, 0.114,
    -0.3907, -4.46, 'STOP_LOSS', 2.08,
    0, '1h', '2026-03-08T18:36:22.451891'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3907,
    pnl_amount = -4.46,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '13E8302ACB3C33C7', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2022-11-07 10:00:00', '2022-11-07 19:34:18', 33185.44522502, 32988.41754624,
    33683.2269034, 32355.8090944, 0.0964,
    0.5937, 5.73, 'TRAILING_STOP', 9.57,
    1, '1h', '2026-03-08T18:36:22.451641'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5937,
    pnl_amount = 5.73,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9C5E32BE06E7F1E6', 'FUNDING_PRO_v1', 'DOGEUSDT', 'LONG',
    '2022-11-07 17:00:00', '2022-11-08 00:50:02', 3576.38740293, 3599.73789025,
    3522.74159189, 3665.79708801, 0.0993,
    0.6529, 6.48, 'TAKE_PROFIT', 7.83,
    1, '1h', '2026-03-08T18:36:22.450115'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6529,
    pnl_amount = 6.48,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '924688D3980EDB50', 'FUNDING_PRO_v1', 'XRPUSDT', 'LONG',
    '2022-11-12 20:00:00', '2022-11-12 23:24:39', 3347.83705349, 3369.41772944,
    3297.61949769, 3431.53297982, 0.1116,
    0.6446, 7.2, 'TAKE_PROFIT', 3.41,
    1, '1h', '2026-03-08T18:36:22.453897'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6446,
    pnl_amount = 7.2,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5D0901E7AFA24A78', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2022-11-14 10:00:00', '2022-11-14 13:37:17', 2785.22545378, 2796.85255231,
    2827.00383559, 2715.59481743, 0.1007,
    -0.4175, -4.2, 'STOP_LOSS', 3.62,
    0, '1h', '2026-03-08T18:36:22.449648'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4175,
    pnl_amount = -4.2,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2C87CFCB0BA9778E', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2022-11-23 01:00:00', '2022-11-23 10:46:34', 1954.3352918, 1970.97428792,
    1925.02026242, 2003.19367409, 0.1091,
    0.8514, 9.29, 'TIME_EXIT', 9.78,
    1, '1h', '2026-03-08T18:36:22.452984'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8514,
    pnl_amount = 9.29,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '101160EDD5A43766', 'FUNDING_PRO_v1', 'XRPUSDT', 'SHORT',
    '2022-11-23 12:00:00', '2022-11-23 19:04:20', 776.21671643, 771.42607201,
    787.85996718, 756.81129852, 0.1059,
    0.6172, 6.53, 'TIME_EXIT', 7.07,
    1, '1h', '2026-03-08T18:36:22.453328'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6172,
    pnl_amount = 6.53,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3391AF2F72EB1B8E', 'FUNDING_PRO_v1', 'LINKUSDT', 'LONG',
    '2022-11-28 10:00:00', '2022-11-28 15:09:01', 4552.84491938, 4597.0554362,
    4484.55224559, 4666.66604236, 0.1183,
    0.9711, 11.48, 'TRAILING_STOP', 5.15,
    1, '1h', '2026-03-08T18:36:22.453265'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9711,
    pnl_amount = 11.48,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'ACC0DB817D089266', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2022-12-04 14:00:00', '2022-12-04 23:45:57', 1238.9335984, 1233.39310928,
    1220.34959443, 1269.90693836, 0.109,
    -0.4472, -4.88, 'STOP_LOSS', 9.77,
    0, '1h', '2026-03-08T18:36:22.454223'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4472,
    pnl_amount = -4.88,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D030D1456B6C2E0E', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2022-12-10 09:00:00', '2022-12-10 18:30:50', 4978.19508316, 4931.63483015,
    5052.86800941, 4853.74020608, 0.1049,
    0.9353, 9.81, 'TAKE_PROFIT', 9.51,
    1, '1h', '2026-03-08T18:36:22.450636'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9353,
    pnl_amount = 9.81,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8991F6711071015B', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2022-12-10 11:00:00', '2022-12-10 14:44:11', 3371.78113629, 3403.97833562,
    3321.20441925, 3456.0756647, 0.1152,
    0.9549, 11.0, 'TAKE_PROFIT', 3.74,
    1, '1h', '2026-03-08T18:36:22.448851'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9549,
    pnl_amount = 11.0,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '82F10F54BC8F3014', 'FUNDING_PRO_v1', 'LINKUSDT', 'SHORT',
    '2022-12-14 15:00:00', '2022-12-15 00:21:58', 907.58665413, 902.70040775,
    921.20045394, 884.89698777, 0.0901,
    0.5384, 4.85, 'TAKE_PROFIT', 9.37,
    1, '1h', '2026-03-08T18:36:22.448935'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5384,
    pnl_amount = 4.85,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '10D99D981BAF884C', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2022-12-16 08:00:00', '2022-12-16 10:10:57', 24495.52773888, 24584.45151656,
    24862.96065496, 23883.13954541, 0.0977,
    -0.363, -3.55, 'TIME_EXIT', 2.18,
    0, '1h', '2026-03-08T18:36:22.449822'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.363,
    pnl_amount = -3.55,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7DC5951C9C829D2F', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2022-12-17 14:00:00', '2022-12-17 17:57:45', 3377.148915, 3402.32207257,
    3326.49168128, 3461.57763788, 0.1191,
    0.7454, 8.88, 'TRAILING_STOP', 3.96,
    1, '1h', '2026-03-08T18:36:22.451147'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7454,
    pnl_amount = 8.88,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6D31BD11120A7673', 'FUNDING_PRO_v1', 'DOTUSDT', 'LONG',
    '2022-12-22 21:00:00', '2022-12-23 06:43:28', 1393.29208224, 1406.47646056,
    1372.392701, 1428.12438429, 0.0868,
    0.9463, 8.22, 'TRAILING_STOP', 9.72,
    1, '1h', '2026-03-08T18:36:22.449526'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9463,
    pnl_amount = 8.22,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2064D984B00D4960', 'FUNDING_PRO_v1', 'BNBUSDT', 'SHORT',
    '2022-12-25 23:00:00', '2022-12-26 02:27:57', 3001.92548373, 2974.61978356,
    3046.95436599, 2926.87734664, 0.1107,
    0.9096, 10.07, 'TRAILING_STOP', 3.47,
    1, '1h', '2026-03-08T18:36:22.449877'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9096,
    pnl_amount = 10.07,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '10F8E38651FD4231', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2022-12-30 06:00:00', '2022-12-30 14:26:55', 2196.99788928, 2206.78857377,
    2229.95285762, 2142.07294204, 0.1114,
    -0.4456, -4.97, 'TIME_EXIT', 8.45,
    0, '1h', '2026-03-08T18:36:22.449949'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4456,
    pnl_amount = -4.97,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F2F043EE2BF8A6EB', 'FUNDING_PRO_v1', 'DOGEUSDT', 'SHORT',
    '2022-12-31 10:00:00', '2022-12-31 20:47:42', 887.41799836, 878.72397294,
    900.72926834, 865.2325484, 0.1113,
    0.9797, 10.9, 'TRAILING_STOP', 10.8,
    1, '1h', '2026-03-08T18:36:22.451945'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9797,
    pnl_amount = 10.9,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C9C2D103B769876F', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2023-01-07 02:00:00', '2023-01-07 08:14:23', 4624.69708757, 4596.10789755,
    4694.06754389, 4509.07966038, 0.0887,
    0.6182, 5.48, 'TIME_EXIT', 6.24,
    1, '1h', '2026-03-08T18:36:22.453378'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6182,
    pnl_amount = 5.48,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0B3B7A172BBE2A9A', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2023-01-07 22:00:00', '2023-01-08 01:03:41', 40426.9182228, 40254.46193171,
    39820.51444946, 41437.59117837, 0.1091,
    -0.4266, -4.66, 'STOP_LOSS', 3.06,
    0, '1h', '2026-03-08T18:36:22.451481'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4266,
    pnl_amount = -4.66,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '47AF80C5F72A65E1', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2023-01-11 04:00:00', '2023-01-11 06:40:13', 2528.40414824, 2550.40912943,
    2490.47808602, 2591.61425195, 0.1124,
    0.8703, 9.79, 'TRAILING_STOP', 2.67,
    1, '1h', '2026-03-08T18:36:22.452472'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8703,
    pnl_amount = 9.79,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'AEEF76C0FDB58AD8', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2023-01-14 12:00:00', '2023-01-14 19:01:50', 12.46840782, 12.54081872,
    12.28138171, 12.78011802, 0.0814,
    0.5808, 4.73, 'TRAILING_STOP', 7.03,
    1, '1h', '2026-03-08T18:36:22.450536'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5808,
    pnl_amount = 4.73,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '37188250B87456B1', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2023-02-04 00:00:00', '2023-02-04 07:18:44', 1490.69284505, 1503.91228024,
    1468.33245237, 1527.96016618, 0.0813,
    0.8868, 7.21, 'TRAILING_STOP', 7.31,
    1, '1h', '2026-03-08T18:36:22.453069'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8868,
    pnl_amount = 7.21,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '472A06911DF6CCF6', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2023-02-07 06:00:00', '2023-02-07 14:53:11', 47895.76665061, 48061.6499387,
    48614.20315037, 46698.37248434, 0.1017,
    -0.3463, -3.52, 'TIME_EXIT', 8.89,
    0, '1h', '2026-03-08T18:36:22.449377'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3463,
    pnl_amount = -3.52,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'ABF25ACF2A340DC4', 'FUNDING_PRO_v1', 'DOGEUSDT', 'SHORT',
    '2023-02-09 00:00:00', '2023-02-09 03:44:07', 1296.4037949, 1285.07900606,
    1315.84985182, 1263.99370003, 0.0826,
    0.8736, 7.22, 'TIME_EXIT', 3.74,
    1, '1h', '2026-03-08T18:36:22.451260'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8736,
    pnl_amount = 7.22,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1E43D35B34554C67', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2023-02-13 11:00:00', '2023-02-13 14:46:43', 1162.27561372, 1169.40778179,
    1144.84147951, 1191.33250406, 0.0921,
    0.6136, 5.65, 'TRAILING_STOP', 3.78,
    1, '1h', '2026-03-08T18:36:22.451686'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6136,
    pnl_amount = 5.65,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DF7262AFDDAEF689', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2023-02-18 12:00:00', '2023-02-18 18:49:08', 3152.98228176, 3177.40352878,
    3105.68754754, 3231.80683881, 0.105,
    0.7745, 8.13, 'TAKE_PROFIT', 6.82,
    1, '1h', '2026-03-08T18:36:22.452481'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7745,
    pnl_amount = 8.13,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D7DF7BB7376EADB7', 'FUNDING_PRO_v1', 'BNBUSDT', 'SHORT',
    '2023-02-21 19:00:00', '2023-02-21 22:04:19', 2952.76475194, 2925.53096666,
    2997.05622321, 2878.94563314, 0.1007,
    0.9223, 9.29, 'TRAILING_STOP', 3.07,
    1, '1h', '2026-03-08T18:36:22.452017'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9223,
    pnl_amount = 9.29,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DFE773FA70487AD8', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2023-02-22 15:00:00', '2023-02-23 02:34:07', 36134.28002754, 36010.30094133,
    35592.26582712, 37037.63702823, 0.1037,
    -0.3431, -3.56, 'TIME_EXIT', 11.57,
    0, '1h', '2026-03-08T18:36:22.449941'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3431,
    pnl_amount = -3.56,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D44EC26788426A10', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2023-02-23 04:00:00', '2023-02-23 10:48:53', 9820.48459783, 9779.52100254,
    9673.17732887, 10065.99671278, 0.0878,
    -0.4171, -3.66, 'TIME_EXIT', 6.81,
    0, '1h', '2026-03-08T18:36:22.449959'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4171,
    pnl_amount = -3.66,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C102490C117A7C7C', 'FUNDING_PRO_v1', 'XRPUSDT', 'LONG',
    '2023-02-25 22:00:00', '2023-02-26 02:23:24', 1918.21354365, 1909.72974575,
    1889.4403405, 1966.16888224, 0.0912,
    -0.4423, -4.03, 'TIME_EXIT', 4.39,
    0, '1h', '2026-03-08T18:36:22.454381'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4423,
    pnl_amount = -4.03,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '05CB03EAE847C6F2', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2023-02-27 14:00:00', '2023-02-27 17:32:29', 23432.40674609, 23328.50710033,
    23080.92064489, 24018.21691474, 0.1199,
    -0.4434, -5.31, 'STOP_LOSS', 3.54,
    0, '1h', '2026-03-08T18:36:22.450088'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4434,
    pnl_amount = -5.31,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DBA4D9DC80351659', 'FUNDING_PRO_v1', 'XRPUSDT', 'SHORT',
    '2023-03-01 18:00:00', '2023-03-02 03:51:39', 1791.68966892, 1778.69382728,
    1818.56501395, 1746.89742719, 0.0998,
    0.7253, 7.24, 'TAKE_PROFIT', 9.86,
    1, '1h', '2026-03-08T18:36:22.449284'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7253,
    pnl_amount = 7.24,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '30D51C0CBC904B4F', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2023-03-05 16:00:00', '2023-03-05 19:09:12', 3415.18953285, 3438.55406401,
    3363.96168986, 3500.56927118, 0.095,
    0.6841, 6.5, 'TAKE_PROFIT', 3.15,
    1, '1h', '2026-03-08T18:36:22.451543'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6841,
    pnl_amount = 6.5,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BA2FD31F836113E1', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2023-03-07 19:00:00', '2023-03-07 23:43:24', 1506.64248452, 1511.69140654,
    1529.24212179, 1468.97642241, 0.0846,
    -0.3351, -2.84, 'TIME_EXIT', 4.72,
    0, '1h', '2026-03-08T18:36:22.451399'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3351,
    pnl_amount = -2.84,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4804F22778C3B549', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2023-03-08 10:00:00', '2023-03-08 21:20:41', 41885.16090584, 42128.63992895,
    41256.88349225, 42932.28992848, 0.1046,
    0.5813, 6.08, 'TIME_EXIT', 11.34,
    1, '1h', '2026-03-08T18:36:22.448998'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5813,
    pnl_amount = 6.08,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '073DAF884295EF50', 'FUNDING_PRO_v1', 'AVAXUSDT', 'SHORT',
    '2023-03-10 14:00:00', '2023-03-10 22:08:34', 4619.25377039, 4640.28782205,
    4688.54257695, 4503.77242613, 0.1154,
    -0.4554, -5.26, 'TIME_EXIT', 8.14,
    0, '1h', '2026-03-08T18:36:22.449840'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4554,
    pnl_amount = -5.26,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '240AFD7CDDDFFA28', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2023-03-11 13:00:00', '2023-03-12 00:22:12', 25448.66751344, 25683.65089853,
    25066.93750074, 26084.88420127, 0.0857,
    0.9234, 7.92, 'TRAILING_STOP', 11.37,
    1, '1h', '2026-03-08T18:36:22.450142'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9234,
    pnl_amount = 7.92,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B86CA4CC4614E3B1', 'FUNDING_PRO_v1', 'LINKUSDT', 'SHORT',
    '2023-03-13 06:00:00', '2023-03-13 08:31:53', 1502.40825001, 1508.40151085,
    1524.94437376, 1464.84804376, 0.0939,
    -0.3989, -3.75, 'STOP_LOSS', 2.53,
    0, '1h', '2026-03-08T18:36:22.450448'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3989,
    pnl_amount = -3.75,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B6BA68214AB132A0', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2023-03-22 03:00:00', '2023-03-22 10:17:00', 23365.06373357, 23555.98398239,
    23014.58777756, 23949.19032691, 0.083,
    0.8171, 6.78, 'TRAILING_STOP', 7.28,
    1, '1h', '2026-03-08T18:36:22.453590'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8171,
    pnl_amount = 6.78,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F5E6591E1B317755', 'FUNDING_PRO_v1', 'DOGEUSDT', 'LONG',
    '2023-03-24 00:00:00', '2023-03-24 07:21:15', 848.53023295, 856.0821045,
    835.80227946, 869.74348878, 0.1077,
    0.89, 9.58, 'TRAILING_STOP', 7.35,
    1, '1h', '2026-03-08T18:36:22.451471'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.89,
    pnl_amount = 9.58,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1ABE2DE4BA8BC8FC', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2023-03-26 15:00:00', '2023-03-26 22:49:18', 1355.1052586, 1341.98459961,
    1375.43183748, 1321.22762714, 0.0994,
    0.9682, 9.63, 'TIME_EXIT', 7.82,
    1, '1h', '2026-03-08T18:36:22.450555'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9682,
    pnl_amount = 9.63,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6F42A2B28BF37AC0', 'FUNDING_PRO_v1', 'ADAUSDT', 'SHORT',
    '2023-03-29 19:00:00', '2023-03-30 02:28:38', 2836.24097549, 2816.24968286,
    2878.78459012, 2765.3349511, 0.0925,
    0.7049, 6.52, 'TIME_EXIT', 7.48,
    1, '1h', '2026-03-08T18:36:22.449895'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7049,
    pnl_amount = 6.52,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C20B7C1420B9372E', 'FUNDING_PRO_v1', 'DOGEUSDT', 'SHORT',
    '2023-04-05 06:00:00', '2023-04-05 10:30:29', 2963.99655858, 2936.78575261,
    3008.45650696, 2889.89664462, 0.0895,
    0.918, 8.22, 'TAKE_PROFIT', 4.51,
    1, '1h', '2026-03-08T18:36:22.449265'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.918,
    pnl_amount = 8.22,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B20C38AA859A7300', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2023-04-08 11:00:00', '2023-04-08 19:42:17', 2901.22691626, 2917.53503251,
    2857.70851251, 2973.75758916, 0.0998,
    0.5621, 5.61, 'TRAILING_STOP', 8.7,
    1, '1h', '2026-03-08T18:36:22.450097'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5621,
    pnl_amount = 5.61,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '67EF5510803966E7', 'FUNDING_PRO_v1', 'AVAXUSDT', 'LONG',
    '2023-04-11 03:00:00', '2023-04-11 08:26:22', 489.2258804, 492.92700158,
    481.88749219, 501.45652741, 0.1169,
    0.7565, 8.84, 'TRAILING_STOP', 5.44,
    1, '1h', '2026-03-08T18:36:22.453339'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7565,
    pnl_amount = 8.84,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9F01F5EB6E6AE2F9', 'FUNDING_PRO_v1', 'ADAUSDT', 'SHORT',
    '2023-04-15 00:00:00', '2023-04-15 04:29:21', 4629.77898291, 4646.99373512,
    4699.22566765, 4514.03450834, 0.0818,
    -0.3718, -3.04, 'TIME_EXIT', 4.49,
    0, '1h', '2026-03-08T18:36:22.450070'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3718,
    pnl_amount = -3.04,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '099345DF724CD792', 'FUNDING_PRO_v1', 'LINKUSDT', 'SHORT',
    '2023-04-15 17:00:00', '2023-04-16 02:40:21', 79.41592559, 78.78070184,
    80.60716447, 77.43052745, 0.0822,
    0.7999, 6.58, 'TAKE_PROFIT', 9.67,
    1, '1h', '2026-03-08T18:36:22.452098'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7999,
    pnl_amount = 6.58,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '25769CA869F3E631', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2023-04-19 15:00:00', '2023-04-20 01:28:32', 3773.05437254, 3759.01921987,
    3716.45855695, 3867.38073185, 0.0914,
    -0.372, -3.4, 'TIME_EXIT', 10.48,
    0, '1h', '2026-03-08T18:36:22.451194'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.372,
    pnl_amount = -3.4,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '137AB9216B18EA21', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2023-04-24 19:00:00', '2023-04-24 23:22:37', 2582.8973103, 2591.7653422,
    2621.64076996, 2518.32487754, 0.1165,
    -0.3433, -4.0, 'STOP_LOSS', 4.38,
    0, '1h', '2026-03-08T18:36:22.451185'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3433,
    pnl_amount = -4.0,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '37118E22F301A815', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2023-04-29 14:00:00', '2023-04-29 22:55:42', 3125.87493429, 3139.74155716,
    3172.7630583, 3047.72806093, 0.1053,
    -0.4436, -4.67, 'TIME_EXIT', 8.93,
    0, '1h', '2026-03-08T18:36:22.452143'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4436,
    pnl_amount = -4.67,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C468C54BEC98852E', 'FUNDING_PRO_v1', 'ADAUSDT', 'SHORT',
    '2023-04-30 22:00:00', '2023-05-01 07:29:58', 2687.13433266, 2698.38914574,
    2727.44134765, 2619.95597435, 0.119,
    -0.4188, -4.99, 'STOP_LOSS', 9.5,
    0, '1h', '2026-03-08T18:36:22.449387'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4188,
    pnl_amount = -4.99,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B73E48847883CD57', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2023-05-03 01:00:00', '2023-05-03 11:12:48', 9547.43387168, 9490.75617353,
    9690.64537976, 9308.74802489, 0.0892,
    0.5936, 5.3, 'TIME_EXIT', 10.21,
    1, '1h', '2026-03-08T18:36:22.452134'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5936,
    pnl_amount = 5.3,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9FBB5CF0B6083DDD', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2023-05-03 18:00:00', '2023-05-03 21:36:34', 46615.91829453, 46800.95435573,
    47315.15706895, 45450.52033717, 0.1181,
    -0.3969, -4.69, 'TIME_EXIT', 3.61,
    0, '1h', '2026-03-08T18:36:22.451668'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3969,
    pnl_amount = -4.69,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '06219D058CF9011D', 'FUNDING_PRO_v1', 'LINKUSDT', 'LONG',
    '2023-05-06 04:00:00', '2023-05-06 15:35:52', 4670.24621099, 4697.10464763,
    4600.19251783, 4787.00236627, 0.1049,
    0.5751, 6.03, 'TAKE_PROFIT', 11.6,
    1, '1h', '2026-03-08T18:36:22.452930'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5751,
    pnl_amount = 6.03,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D0B22001FCE83F56', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2023-05-06 06:00:00', '2023-05-06 13:54:50', 5958.01644041, 6009.07490515,
    5868.64619381, 6106.96685142, 0.1143,
    0.857, 9.79, 'TIME_EXIT', 7.91,
    1, '1h', '2026-03-08T18:36:22.450591'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.857,
    pnl_amount = 9.79,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3A12927578993850', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2023-05-09 01:00:00', '2023-05-09 05:41:26', 25.29466927, 25.38702197,
    25.67408931, 24.66230254, 0.1065,
    -0.3651, -3.89, 'STOP_LOSS', 4.69,
    0, '1h', '2026-03-08T18:36:22.451507'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3651,
    pnl_amount = -3.89,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '96F7B4DD586A80DB', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2023-05-11 04:00:00', '2023-05-11 09:08:42', 2324.86408409, 2305.44019467,
    2359.73704535, 2266.74248199, 0.0846,
    0.8355, 7.07, 'TIME_EXIT', 5.15,
    1, '1h', '2026-03-08T18:36:22.453826'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8355,
    pnl_amount = 7.07,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '006258FA67A1E3C6', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2023-05-17 14:00:00', '2023-05-17 22:02:12', 2802.86140638, 2793.40173881,
    2760.81848529, 2872.93294154, 0.0852,
    -0.3375, -2.87, 'STOP_LOSS', 8.04,
    0, '1h', '2026-03-08T18:36:22.450526'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3375,
    pnl_amount = -2.87,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '262B60BDC26E5ECE', 'FUNDING_PRO_v1', 'ADAUSDT', 'SHORT',
    '2023-05-20 22:00:00', '2023-05-21 09:18:10', 4122.52928281, 4082.700762,
    4184.36722205, 4019.46605074, 0.1023,
    0.9661, 9.88, 'TAKE_PROFIT', 11.3,
    1, '1h', '2026-03-08T18:36:22.450906'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9661,
    pnl_amount = 9.88,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '59083177C50710D5', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2023-05-23 16:00:00', '2023-05-23 19:14:51', 2761.47072686, 2787.32678048,
    2720.04866596, 2830.50749503, 0.1009,
    0.9363, 9.45, 'TAKE_PROFIT', 3.25,
    1, '1h', '2026-03-08T18:36:22.453844'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9363,
    pnl_amount = 9.45,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E8D370A9B48F982E', 'FUNDING_PRO_v1', 'BNBUSDT', 'LONG',
    '2023-05-28 09:00:00', '2023-05-28 13:43:52', 2760.17619319, 2748.04553721,
    2718.77355029, 2829.18059802, 0.0886,
    -0.4395, -3.9, 'STOP_LOSS', 4.73,
    0, '1h', '2026-03-08T18:36:22.453042'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4395,
    pnl_amount = -3.9,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7B8BEDD24DA76227', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2023-05-29 13:00:00', '2023-05-29 18:15:14', 246.82068551, 248.33692332,
    243.11837523, 252.99120265, 0.1161,
    0.6143, 7.13, 'TAKE_PROFIT', 5.25,
    1, '1h', '2026-03-08T18:36:22.454083'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6143,
    pnl_amount = 7.13,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1B100EBD302CE2A3', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2023-05-29 22:00:00', '2023-05-30 06:47:44', 4978.98905193, 4944.70249491,
    5053.67388771, 4854.51432564, 0.1041,
    0.6886, 7.17, 'TAKE_PROFIT', 8.8,
    1, '1h', '2026-03-08T18:36:22.452363'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6886,
    pnl_amount = 7.17,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E7E577F264B55DCB', 'FUNDING_PRO_v1', 'XRPUSDT', 'SHORT',
    '2023-05-30 01:00:00', '2023-05-30 06:34:28', 4649.26654247, 4614.29270742,
    4719.00554061, 4533.03487891, 0.0953,
    0.7522, 7.17, 'TIME_EXIT', 5.57,
    1, '1h', '2026-03-08T18:36:22.451408'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7522,
    pnl_amount = 7.17,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '446EA7B4AFBE33A1', 'FUNDING_PRO_v1', 'XRPUSDT', 'LONG',
    '2023-05-30 23:00:00', '2023-05-31 08:49:17', 1111.52663361, 1117.70063719,
    1094.8537341, 1139.31479945, 0.0862,
    0.5555, 4.79, 'TAKE_PROFIT', 9.82,
    1, '1h', '2026-03-08T18:36:22.451588'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5555,
    pnl_amount = 4.79,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '777B4D909FFD0862', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2023-05-31 16:00:00', '2023-05-31 23:37:18', 2567.8105561, 2555.94303521,
    2529.29339776, 2632.00582, 0.116,
    -0.4622, -5.36, 'STOP_LOSS', 7.62,
    0, '1h', '2026-03-08T18:36:22.450764'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4622,
    pnl_amount = -5.36,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5A2600B2065AA69F', 'FUNDING_PRO_v1', 'XRPUSDT', 'LONG',
    '2023-06-03 20:00:00', '2023-06-04 00:01:01', 633.5823165, 638.70555874,
    624.07858175, 649.42187441, 0.0928,
    0.8086, 7.51, 'TRAILING_STOP', 4.02,
    1, '1h', '2026-03-08T18:36:22.452798'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8086,
    pnl_amount = 7.51,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DAD1AE796989E357', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2023-06-15 17:00:00', '2023-06-15 21:08:05', 26307.31554072, 26088.10923061,
    26701.92527383, 25649.6326522, 0.1033,
    0.8333, 8.61, 'TRAILING_STOP', 4.13,
    1, '1h', '2026-03-08T18:36:22.450665'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8333,
    pnl_amount = 8.61,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DA416F4190F5318A', 'FUNDING_PRO_v1', 'BNBUSDT', 'LONG',
    '2023-06-23 20:00:00', '2023-06-24 01:53:14', 4638.65697408, 4619.93864363,
    4569.07711947, 4754.62339844, 0.0801,
    -0.4035, -3.23, 'TIME_EXIT', 5.89,
    0, '1h', '2026-03-08T18:36:22.449776'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4035,
    pnl_amount = -3.23,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'ACDA207EE239C788', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2023-06-24 18:00:00', '2023-06-24 21:48:29', 11253.3136815, 11337.20590403,
    11084.51397628, 11534.64652354, 0.0953,
    0.7455, 7.1, 'TRAILING_STOP', 3.81,
    1, '1h', '2026-03-08T18:36:22.452324'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7455,
    pnl_amount = 7.1,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '510321C9770CA51C', 'FUNDING_PRO_v1', 'XRPUSDT', 'SHORT',
    '2023-06-26 02:00:00', '2023-06-26 07:43:10', 1858.93140901, 1845.38807556,
    1886.81538014, 1812.45812378, 0.1136,
    0.7286, 8.27, 'TIME_EXIT', 5.72,
    1, '1h', '2026-03-08T18:36:22.449583'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7286,
    pnl_amount = 8.27,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '013D76121D857CBE', 'FUNDING_PRO_v1', 'DOGEUSDT', 'LONG',
    '2023-07-16 07:00:00', '2023-07-16 11:43:20', 4935.99695268, 4916.4337964,
    4861.95699839, 5059.3968765, 0.1051,
    -0.3963, -4.17, 'TIME_EXIT', 4.72,
    0, '1h', '2026-03-08T18:36:22.452881'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3963,
    pnl_amount = -4.17,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B173A32A1BC45093', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2023-07-16 11:00:00', '2023-07-16 16:42:29', 12420.5225056, 12308.98401506,
    12606.83034319, 12110.00944296, 0.1045,
    0.898, 9.39, 'TRAILING_STOP', 5.71,
    1, '1h', '2026-03-08T18:36:22.451016'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.898,
    pnl_amount = 9.39,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B00517686C679FFB', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2023-07-18 21:00:00', '2023-07-19 02:48:07', 2596.2097669, 2575.8408118,
    2635.15291341, 2531.30452273, 0.1053,
    0.7846, 8.26, 'TIME_EXIT', 5.8,
    1, '1h', '2026-03-08T18:36:22.449535'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7846,
    pnl_amount = 8.26,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8E7AE9FF94E13A05', 'FUNDING_PRO_v1', 'ADAUSDT', 'SHORT',
    '2023-07-22 02:00:00', '2023-07-22 04:28:25', 100.54344453, 99.91059907,
    102.0515962, 98.02985841, 0.1144,
    0.6294, 7.2, 'TAKE_PROFIT', 2.47,
    1, '1h', '2026-03-08T18:36:22.451489'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6294,
    pnl_amount = 7.2,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DBC6622C551C9ED7', 'FUNDING_PRO_v1', 'BNBUSDT', 'SHORT',
    '2023-07-26 12:00:00', '2023-07-26 18:09:45', 999.96482689, 993.56819411,
    1014.96429929, 974.96570622, 0.0856,
    0.6397, 5.48, 'TRAILING_STOP', 6.16,
    1, '1h', '2026-03-08T18:36:22.453799'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6397,
    pnl_amount = 5.48,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '49F544BE7A062CF4', 'FUNDING_PRO_v1', 'DOGEUSDT', 'LONG',
    '2023-07-29 20:00:00', '2023-07-30 02:40:44', 790.60752693, 795.55592217,
    778.74841402, 810.3727151, 0.0975,
    0.6259, 6.1, 'TRAILING_STOP', 6.68,
    1, '1h', '2026-03-08T18:36:22.451758'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6259,
    pnl_amount = 6.1,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '80F5C26D2ACB0399', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2023-08-02 17:00:00', '2023-08-03 00:03:33', 26273.1069395, 26155.23334348,
    25879.01033541, 26929.93461299, 0.1172,
    -0.4486, -5.26, 'STOP_LOSS', 7.06,
    0, '1h', '2026-03-08T18:36:22.452528'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4486,
    pnl_amount = -5.26,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4042CEA9AC26247F', 'FUNDING_PRO_v1', 'ADAUSDT', 'SHORT',
    '2023-08-03 09:00:00', '2023-08-03 13:43:57', 3849.36226946, 3823.10353112,
    3907.1027035, 3753.12821272, 0.1054,
    0.6822, 7.19, 'TIME_EXIT', 4.73,
    1, '1h', '2026-03-08T18:36:22.452751'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6822,
    pnl_amount = 7.19,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A8FE29004F8C25A1', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2023-08-05 14:00:00', '2023-08-05 19:00:16', 4904.51228155, 4946.6718047,
    4830.94459733, 5027.12508859, 0.0815,
    0.8596, 7.0, 'TAKE_PROFIT', 5.0,
    1, '1h', '2026-03-08T18:36:22.452835'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8596,
    pnl_amount = 7.0,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '30C81FC4208DBA2C', 'FUNDING_PRO_v1', 'AVAXUSDT', 'SHORT',
    '2023-08-08 09:00:00', '2023-08-08 11:17:57', 1352.36162399, 1341.2692121,
    1372.64704835, 1318.55258339, 0.1194,
    0.8202, 9.79, 'TRAILING_STOP', 2.3,
    1, '1h', '2026-03-08T18:36:22.448808'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8202,
    pnl_amount = 9.79,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4604D63B1527F1E2', 'FUNDING_PRO_v1', 'XRPUSDT', 'LONG',
    '2023-08-10 18:00:00', '2023-08-11 05:09:05', 3455.80569649, 3481.89666726,
    3403.96861104, 3542.2008389, 0.1161,
    0.755, 8.77, 'TIME_EXIT', 11.15,
    1, '1h', '2026-03-08T18:36:22.452617'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.755,
    pnl_amount = 8.77,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '50452930AA84B332', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2023-08-12 04:00:00', '2023-08-12 07:27:15', 4698.90112198, 4744.81549841,
    4628.41760515, 4816.37365003, 0.0837,
    0.9771, 8.18, 'TIME_EXIT', 3.45,
    1, '1h', '2026-03-08T18:36:22.453993'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9771,
    pnl_amount = 8.18,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1A9576CE854D3785', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2023-08-12 07:00:00', '2023-08-12 11:00:48', 23202.81331712, 23428.2760134,
    22854.77111736, 23782.88365004, 0.115,
    0.9717, 11.18, 'TRAILING_STOP', 4.01,
    1, '1h', '2026-03-08T18:36:22.450043'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9717,
    pnl_amount = 11.18,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1D0881EFF8362E67', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2023-08-13 19:00:00', '2023-08-14 00:35:05', 3262.83251616, 3288.66996091,
    3213.89002842, 3344.40332907, 0.109,
    0.7919, 8.63, 'TAKE_PROFIT', 5.58,
    1, '1h', '2026-03-08T18:36:22.449065'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7919,
    pnl_amount = 8.63,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EA2DD91E8BF1C1C2', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2023-08-14 13:00:00', '2023-08-14 19:50:41', 3988.78840189, 4001.77492373,
    4048.62022792, 3889.06869184, 0.1042,
    -0.3256, -3.39, 'TIME_EXIT', 6.84,
    0, '1h', '2026-03-08T18:36:22.453764'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3256,
    pnl_amount = -3.39,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '84576C4AA94E7FB3', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2023-08-14 17:00:00', '2023-08-15 02:28:47', 1475.22535145, 1480.65034403,
    1497.35373172, 1438.34471766, 0.0918,
    -0.3677, -3.37, 'TIME_EXIT', 9.48,
    0, '1h', '2026-03-08T18:36:22.449554'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3677,
    pnl_amount = -3.37,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3D16586F43F2F2FF', 'FUNDING_PRO_v1', 'XRPUSDT', 'SHORT',
    '2023-08-16 09:00:00', '2023-08-16 16:09:39', 4832.4871993, 4850.78845937,
    4904.97450729, 4711.67501932, 0.0814,
    -0.3787, -3.08, 'TIME_EXIT', 7.16,
    0, '1h', '2026-03-08T18:36:22.449368'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3787,
    pnl_amount = -3.08,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0DC83C77CCC37B39', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2023-08-23 20:00:00', '2023-08-24 07:17:20', 133.50166021, 132.34469541,
    135.50418512, 130.16411871, 0.09,
    0.8666, 7.8, 'TAKE_PROFIT', 11.29,
    1, '1h', '2026-03-08T18:36:22.452453'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8666,
    pnl_amount = 7.8,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9E47AF9D59FE4F39', 'FUNDING_PRO_v1', 'AVAXUSDT', 'SHORT',
    '2023-08-24 08:00:00', '2023-08-24 15:14:12', 4873.76172421, 4831.6645417,
    4946.86815007, 4751.9176811, 0.0979,
    0.8638, 8.45, 'TRAILING_STOP', 7.24,
    1, '1h', '2026-03-08T18:36:22.453608'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8638,
    pnl_amount = 8.45,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8BA8E679AC54DBA1', 'FUNDING_PRO_v1', 'DOGEUSDT', 'SHORT',
    '2023-08-28 09:00:00', '2023-08-28 16:20:25', 3015.05842282, 3028.70331805,
    3060.28429917, 2939.68196225, 0.1063,
    -0.4526, -4.81, 'STOP_LOSS', 7.34,
    0, '1h', '2026-03-08T18:36:22.452695'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4526,
    pnl_amount = -4.81,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '9785E080C190000A', 'FUNDING_PRO_v1', 'XRPUSDT', 'SHORT',
    '2023-08-28 23:00:00', '2023-08-29 07:34:39', 818.07040646, 821.60213154,
    830.34146255, 797.61864629, 0.0952,
    -0.4317, -4.11, 'STOP_LOSS', 8.58,
    0, '1h', '2026-03-08T18:36:22.451138'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4317,
    pnl_amount = -4.11,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B34E2D66C1DE497D', 'FUNDING_PRO_v1', 'DOGEUSDT', 'SHORT',
    '2023-09-01 09:00:00', '2023-09-01 18:37:03', 2981.5303862, 2961.60232744,
    3026.25334199, 2906.99212655, 0.0942,
    0.6684, 6.29, 'TAKE_PROFIT', 9.62,
    1, '1h', '2026-03-08T18:36:22.449905'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6684,
    pnl_amount = 6.29,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B4B02C9F5CB489D2', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2023-09-06 03:00:00', '2023-09-06 11:17:15', 1573.57534062, 1565.6860564,
    1597.17897073, 1534.2359571, 0.1057,
    0.5014, 5.3, 'TAKE_PROFIT', 8.29,
    1, '1h', '2026-03-08T18:36:22.451713'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5014,
    pnl_amount = 5.3,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BB6B5600E73C5DDB', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2023-09-07 22:00:00', '2023-09-08 02:13:22', 14662.35292156, 14590.35352702,
    14882.28821539, 14295.79409852, 0.1118,
    0.491, 5.49, 'TAKE_PROFIT', 4.22,
    1, '1h', '2026-03-08T18:36:22.451981'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.491,
    pnl_amount = 5.49,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '03F03F7D4AAC9353', 'FUNDING_PRO_v1', 'DOGEUSDT', 'SHORT',
    '2023-09-09 21:00:00', '2023-09-10 06:57:49', 2535.26172675, 2547.35940973,
    2573.29065265, 2471.88018358, 0.1104,
    -0.4772, -5.27, 'STOP_LOSS', 9.96,
    0, '1h', '2026-03-08T18:36:22.453888'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4772,
    pnl_amount = -5.27,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3D0AD0C0ED3957D5', 'FUNDING_PRO_v1', 'DOTUSDT', 'SHORT',
    '2023-09-10 10:00:00', '2023-09-10 13:27:26', 2339.46256636, 2319.00765239,
    2374.55450486, 2280.9760022, 0.0977,
    0.8743, 8.54, 'TAKE_PROFIT', 3.46,
    1, '1h', '2026-03-08T18:36:22.451632'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8743,
    pnl_amount = 8.54,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E803366AA6565CB7', 'FUNDING_PRO_v1', 'AVAXUSDT', 'SHORT',
    '2023-09-11 23:00:00', '2023-09-12 01:11:08', 522.91229028, 524.93666981,
    530.75597464, 509.83948303, 0.1138,
    -0.3871, -4.41, 'STOP_LOSS', 2.19,
    0, '1h', '2026-03-08T18:36:22.453925'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3871,
    pnl_amount = -4.41,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2D67B72CFB96425B', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2023-09-12 07:00:00', '2023-09-12 14:22:36', 40307.90951986, 40142.4039367,
    39703.29087706, 41315.60725785, 0.1148,
    -0.4106, -4.72, 'STOP_LOSS', 7.38,
    0, '1h', '2026-03-08T18:36:22.450494'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4106,
    pnl_amount = -4.72,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '863C47D55489D205', 'FUNDING_PRO_v1', 'XRPUSDT', 'LONG',
    '2023-09-14 12:00:00', '2023-09-14 17:05:05', 3067.01993643, 3096.10535492,
    3021.01463738, 3143.69543484, 0.094,
    0.9483, 8.91, 'TIME_EXIT', 5.08,
    1, '1h', '2026-03-08T18:36:22.450151'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9483,
    pnl_amount = 8.91,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '36CE869DFF29A021', 'FUNDING_PRO_v1', 'DOGEUSDT', 'LONG',
    '2023-09-18 12:00:00', '2023-09-18 17:58:50', 437.72158392, 435.84892798,
    431.15576016, 448.66462351, 0.0969,
    -0.4278, -4.15, 'STOP_LOSS', 5.98,
    0, '1h', '2026-03-08T18:36:22.451704'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4278,
    pnl_amount = -4.15,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1942836396B8C8BE', 'FUNDING_PRO_v1', 'DOTUSDT', 'SHORT',
    '2023-09-20 15:00:00', '2023-09-21 02:44:45', 2533.33008722, 2542.96141564,
    2571.33003853, 2469.99683504, 0.0814,
    -0.3802, -3.1, 'STOP_LOSS', 11.75,
    0, '1h', '2026-03-08T18:36:22.450710'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3802,
    pnl_amount = -3.1,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '346B53DBC0991F62', 'FUNDING_PRO_v1', 'DOGEUSDT', 'LONG',
    '2023-09-30 15:00:00', '2023-09-30 20:58:06', 1634.59644521, 1644.51859001,
    1610.07749853, 1675.46135634, 0.0822,
    0.607, 4.99, 'TIME_EXIT', 5.97,
    1, '1h', '2026-03-08T18:36:22.453985'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.607,
    pnl_amount = 4.99,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'ED31569D75CFF80B', 'FUNDING_PRO_v1', 'AVAXUSDT', 'LONG',
    '2023-09-30 21:00:00', '2023-09-30 23:26:28', 4241.19165562, 4269.46025607,
    4177.57378079, 4347.22144701, 0.0948,
    0.6665, 6.32, 'TAKE_PROFIT', 2.44,
    1, '1h', '2026-03-08T18:36:22.452053'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6665,
    pnl_amount = 6.32,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5BEABBE064AD7428', 'FUNDING_PRO_v1', 'DOTUSDT', 'SHORT',
    '2023-10-05 04:00:00', '2023-10-05 12:19:33', 2852.90794931, 2834.19588251,
    2895.70156855, 2781.58525058, 0.1007,
    0.6559, 6.61, 'TIME_EXIT', 8.33,
    1, '1h', '2026-03-08T18:36:22.450683'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6559,
    pnl_amount = 6.61,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FD0FF8250737E6C5', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2023-10-07 08:00:00', '2023-10-07 10:03:07', 1836.11382591, 1829.48559632,
    1808.57211852, 1882.01667155, 0.0905,
    -0.361, -3.27, 'TIME_EXIT', 2.05,
    0, '1h', '2026-03-08T18:36:22.451289'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.361,
    pnl_amount = -3.27,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '214D844231662CEE', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2023-10-08 01:00:00', '2023-10-08 12:30:10', 10013.12143786, 10084.2040942,
    9862.92461629, 10263.4494738, 0.0935,
    0.7099, 6.64, 'TRAILING_STOP', 11.5,
    1, '1h', '2026-03-08T18:36:22.453349'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7099,
    pnl_amount = 6.64,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7C2E606CBAB5AD56', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2023-10-11 12:00:00', '2023-10-11 20:12:35', 35437.79514198, 35643.55670056,
    34906.22821485, 36323.74002053, 0.089,
    0.5806, 5.17, 'TRAILING_STOP', 8.21,
    1, '1h', '2026-03-08T18:36:22.451990'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5806,
    pnl_amount = 5.17,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F669EEEF0CCB02B5', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2023-10-12 06:00:00', '2023-10-12 11:56:32', 22979.58637402, 23168.90124108,
    22634.89257841, 23554.07603337, 0.0816,
    0.8238, 6.72, 'TIME_EXIT', 5.94,
    1, '1h', '2026-03-08T18:36:22.451316'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8238,
    pnl_amount = 6.72,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'ED1ED53DCC5C685F', 'FUNDING_PRO_v1', 'DOGEUSDT', 'LONG',
    '2023-10-14 17:00:00', '2023-10-14 20:23:10', 3824.87896775, 3849.85310973,
    3767.50578324, 3920.50094195, 0.1083,
    0.6529, 7.07, 'TIME_EXIT', 3.39,
    1, '1h', '2026-03-08T18:36:22.449675'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6529,
    pnl_amount = 7.07,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1B17ECFC0EFEBDE0', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2023-10-16 09:00:00', '2023-10-16 17:46:26', 2846.88758493, 2869.8313653,
    2804.18427115, 2918.05977455, 0.1076,
    0.8059, 8.67, 'TAKE_PROFIT', 8.77,
    1, '1h', '2026-03-08T18:36:22.451596'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8059,
    pnl_amount = 8.67,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B16B38D738BE6928', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2023-10-22 23:00:00', '2023-10-23 10:24:53', 32317.60754024, 32147.96467115,
    32802.37165334, 31509.66735173, 0.1071,
    0.5249, 5.62, 'TAKE_PROFIT', 11.41,
    1, '1h', '2026-03-08T18:36:22.449657'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5249,
    pnl_amount = 5.62,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2B10F208C25E959C', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2023-10-25 13:00:00', '2023-10-25 15:31:17', 3779.0220357, 3806.55896227,
    3722.33670517, 3873.49758659, 0.1081,
    0.7287, 7.88, 'TRAILING_STOP', 2.52,
    1, '1h', '2026-03-08T18:36:22.449396'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7287,
    pnl_amount = 7.88,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '301393F5EF57B001', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2023-10-28 03:00:00', '2023-10-28 07:20:11', 48989.64284112, 48525.25433973,
    49724.48748374, 47764.9017701, 0.1115,
    0.9479, 10.57, 'TIME_EXIT', 4.34,
    1, '1h', '2026-03-08T18:36:22.453560'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9479,
    pnl_amount = 10.57,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'AC2B23E914702348', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2023-11-12 08:00:00', '2023-11-12 19:04:08', 42463.84927956, 42655.00869443,
    43100.80701876, 41402.25304757, 0.0985,
    -0.4502, -4.43, 'TIME_EXIT', 11.07,
    0, '1h', '2026-03-08T18:36:22.449986'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4502,
    pnl_amount = -4.43,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '88FF6087F23EF40F', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2023-11-22 02:00:00', '2023-11-22 06:00:24', 1076.00075718, 1086.47921775,
    1059.86074582, 1102.90077611, 0.1123,
    0.9738, 10.93, 'TAKE_PROFIT', 4.01,
    1, '1h', '2026-03-08T18:36:22.449758'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9738,
    pnl_amount = 10.93,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '19357EE7D0AE6EFB', 'FUNDING_PRO_v1', 'XRPUSDT', 'LONG',
    '2023-11-22 10:00:00', '2023-11-22 19:20:17', 138.59203086, 139.53015414,
    136.51315039, 142.05683163, 0.1086,
    0.6769, 7.35, 'TRAILING_STOP', 9.34,
    1, '1h', '2026-03-08T18:36:22.454025'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6769,
    pnl_amount = 7.35,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8312FCAAFC286578', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2023-11-23 02:00:00', '2023-11-23 04:29:50', 422.84745917, 420.53550441,
    429.19017106, 412.27627269, 0.1072,
    0.5468, 5.86, 'TAKE_PROFIT', 2.5,
    1, '1h', '2026-03-08T18:36:22.450582'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5468,
    pnl_amount = 5.86,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6F2BD910455135C1', 'FUNDING_PRO_v1', 'XRPUSDT', 'LONG',
    '2023-11-23 22:00:00', '2023-11-24 00:50:18', 4306.19967238, 4287.58624607,
    4241.60667729, 4413.85466419, 0.0947,
    -0.4322, -4.09, 'STOP_LOSS', 2.84,
    0, '1h', '2026-03-08T18:36:22.453808'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4322,
    pnl_amount = -4.09,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3E1D0A9D2D98F9FE', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2023-12-07 12:00:00', '2023-12-07 19:54:50', 6585.86438361, 6539.38622318,
    6684.65234937, 6421.21777402, 0.1121,
    0.7057, 7.91, 'TAKE_PROFIT', 7.91,
    1, '1h', '2026-03-08T18:36:22.451936'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7057,
    pnl_amount = 7.91,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '634396E906F669BE', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2023-12-10 12:00:00', '2023-12-10 21:59:25', 20125.73104546, 20013.68348761,
    20427.61701114, 19622.58776932, 0.1196,
    0.5567, 6.66, 'TRAILING_STOP', 9.99,
    1, '1h', '2026-03-08T18:36:22.452760'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5567,
    pnl_amount = 6.66,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8F6A38E0C8AA1514', 'FUNDING_PRO_v1', 'ADAUSDT', 'LONG',
    '2023-12-11 20:00:00', '2023-12-12 01:59:50', 2470.69369228, 2462.20694977,
    2433.6332869, 2532.46103459, 0.1096,
    -0.3435, -3.76, 'STOP_LOSS', 6.0,
    0, '1h', '2026-03-08T18:36:22.453274'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3435,
    pnl_amount = -3.76,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B4FD3D85E5BF5C16', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2023-12-12 23:00:00', '2023-12-13 03:05:41', 2552.85344782, 2533.91635557,
    2591.14624953, 2489.03211162, 0.1054,
    0.7418, 7.82, 'TIME_EXIT', 4.09,
    1, '1h', '2026-03-08T18:36:22.453147'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7418,
    pnl_amount = 7.82,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F97EB82619923805', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2023-12-16 20:00:00', '2023-12-17 05:52:34', 46814.48077714, 46993.32433837,
    47516.6979888, 45644.11875771, 0.103,
    -0.382, -3.93, 'STOP_LOSS', 9.88,
    0, '1h', '2026-03-08T18:36:22.451100'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.382,
    pnl_amount = -3.93,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D508541F63FDA760', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2023-12-17 00:00:00', '2023-12-17 08:35:04', 1196.74200982, 1185.20586172,
    1214.69313997, 1166.82345958, 0.089,
    0.964, 8.57, 'TAKE_PROFIT', 8.58,
    1, '1h', '2026-03-08T18:36:22.451082'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.964,
    pnl_amount = 8.57,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EAE8889635C90BEF', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2023-12-24 17:00:00', '2023-12-24 19:21:43', 4690.24803941, 4662.37050794,
    4760.60176, 4572.99183843, 0.0906,
    0.5944, 5.38, 'TIME_EXIT', 2.36,
    1, '1h', '2026-03-08T18:36:22.451972'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5944,
    pnl_amount = 5.38,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C631D543EEFAD431', 'FUNDING_PRO_v1', 'ADAUSDT', 'SHORT',
    '2023-12-29 13:00:00', '2023-12-29 19:37:29', 1834.25740746, 1824.00457694,
    1861.77126857, 1788.40097227, 0.1177,
    0.559, 6.58, 'TAKE_PROFIT', 6.62,
    1, '1h', '2026-03-08T18:36:22.453051'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.559,
    pnl_amount = 6.58,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E747180C80681438', 'FUNDING_PRO_v1', 'LINKUSDT', 'LONG',
    '2023-12-30 09:00:00', '2023-12-30 18:26:57', 1560.90241818, 1574.47474282,
    1537.48888191, 1599.92497864, 0.1042,
    0.8695, 9.06, 'TRAILING_STOP', 9.45,
    1, '1h', '2026-03-08T18:36:22.450412'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8695,
    pnl_amount = 9.06,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7AE448066333F986', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2024-01-05 11:00:00', '2024-01-05 21:31:39', 4617.96801786, 4601.62699435,
    4548.69849759, 4733.41721831, 0.1043,
    -0.3539, -3.69, 'TIME_EXIT', 10.53,
    0, '1h', '2026-03-08T18:36:22.449611'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3539,
    pnl_amount = -3.69,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A5F09335512A63F6', 'FUNDING_PRO_v1', 'AVAXUSDT', 'SHORT',
    '2024-01-05 18:00:00', '2024-01-05 23:34:44', 1710.93821672, 1699.37938787,
    1736.60228997, 1668.1647613, 0.1046,
    0.6756, 7.07, 'TAKE_PROFIT', 5.58,
    1, '1h', '2026-03-08T18:36:22.449506'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6756,
    pnl_amount = 7.07,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'FF2A6F0C74D1D006', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2024-01-05 18:00:00', '2024-01-06 03:41:58', 48672.33444861, 48912.4373259,
    47942.24943188, 49889.14280982, 0.0977,
    0.4933, 4.82, 'TRAILING_STOP', 9.7,
    1, '1h', '2026-03-08T18:36:22.451325'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4933,
    pnl_amount = 4.82,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C14FFD5F113BA6DC', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2024-01-07 18:00:00', '2024-01-07 23:51:38', 4512.15141491, 4554.64617067,
    4444.46914368, 4624.95520028, 0.0897,
    0.9418, 8.45, 'TAKE_PROFIT', 5.86,
    1, '1h', '2026-03-08T18:36:22.452974'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9418,
    pnl_amount = 8.45,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E44D2A539B801240', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2024-01-12 23:00:00', '2024-01-13 09:05:00', 4608.15245045, 4567.69826699,
    4677.27473721, 4492.94863919, 0.0802,
    0.8779, 7.04, 'TIME_EXIT', 10.08,
    1, '1h', '2026-03-08T18:36:22.450738'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8779,
    pnl_amount = 7.04,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EA08E38B04BB2302', 'FUNDING_PRO_v1', 'DOGEUSDT', 'SHORT',
    '2024-01-17 21:00:00', '2024-01-18 02:48:36', 4294.94765281, 4263.99164717,
    4359.3718676, 4187.57396149, 0.1125,
    0.7208, 8.1, 'TRAILING_STOP', 5.81,
    1, '1h', '2026-03-08T18:36:22.452126'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7208,
    pnl_amount = 8.1,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '30E585BF00C058AC', 'FUNDING_PRO_v1', 'BNBUSDT', 'SHORT',
    '2024-01-18 11:00:00', '2024-01-18 21:53:39', 4553.31005044, 4528.61603691,
    4621.6097012, 4439.47729918, 0.0875,
    0.5423, 4.74, 'TIME_EXIT', 10.89,
    1, '1h', '2026-03-08T18:36:22.452463'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5423,
    pnl_amount = 4.74,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '74356B15BD527699', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2024-01-20 06:00:00', '2024-01-20 14:28:29', 3444.24303183, 3459.03896269,
    3495.90667731, 3358.13695603, 0.0813,
    -0.4296, -3.49, 'STOP_LOSS', 8.47,
    0, '1h', '2026-03-08T18:36:22.449730'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4296,
    pnl_amount = -3.49,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'AAF629C4FADEE8FF', 'FUNDING_PRO_v1', 'AVAXUSDT', 'SHORT',
    '2024-01-22 17:00:00', '2024-01-22 21:27:04', 2674.53904379, 2652.53487481,
    2714.65712945, 2607.6755677, 0.0818,
    0.8227, 6.73, 'TIME_EXIT', 4.45,
    1, '1h', '2026-03-08T18:36:22.451156'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8227,
    pnl_amount = 6.73,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '682F1BBDF07E9E08', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2024-01-23 22:00:00', '2024-01-24 04:55:41', 6153.91379988, 6198.15814,
    6061.60509288, 6307.76164487, 0.1076,
    0.719, 7.74, 'TIME_EXIT', 6.93,
    1, '1h', '2026-03-08T18:36:22.451570'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.719,
    pnl_amount = 7.74,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DE1892C1A7E71DFB', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2024-01-26 14:00:00', '2024-01-26 22:29:27', 9383.44016689, 9418.39161151,
    9524.19176939, 9148.85416272, 0.0841,
    -0.3725, -3.13, 'STOP_LOSS', 8.49,
    0, '1h', '2026-03-08T18:36:22.451166'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3725,
    pnl_amount = -3.13,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '79E6C768FB0B4F75', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2024-01-30 02:00:00', '2024-01-30 11:13:27', 44298.49503389, 43949.79656593,
    44962.9724594, 43191.03265804, 0.0879,
    0.7872, 6.92, 'TAKE_PROFIT', 9.22,
    1, '1h', '2026-03-08T18:36:22.450618'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7872,
    pnl_amount = 6.92,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '485ACDEB0AB28502', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2024-01-31 07:00:00', '2024-01-31 11:25:35', 4349.37639617, 4330.88331308,
    4284.13575023, 4458.11080607, 0.0914,
    -0.4252, -3.89, 'TIME_EXIT', 4.43,
    0, '1h', '2026-03-08T18:36:22.449693'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4252,
    pnl_amount = -3.89,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3DA093B16780DF0E', 'FUNDING_PRO_v1', 'ADAUSDT', 'LONG',
    '2024-02-06 21:00:00', '2024-02-07 04:17:36', 3387.53765841, 3406.96239017,
    3336.72459354, 3472.22609987, 0.1192,
    0.5734, 6.83, 'TRAILING_STOP', 7.29,
    1, '1h', '2026-03-08T18:36:22.449461'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5734,
    pnl_amount = 6.83,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '290DFE523CBC87AF', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2024-02-07 00:00:00', '2024-02-07 10:39:49', 3337.87274376, 3364.26486146,
    3287.8046526, 3421.31956235, 0.093,
    0.7907, 7.35, 'TRAILING_STOP', 10.66,
    1, '1h', '2026-03-08T18:36:22.451064'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7907,
    pnl_amount = 7.35,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '327A5E66623B5EF8', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2024-02-08 23:00:00', '2024-02-09 04:05:55', 2277.87955303, 2289.77468147,
    2243.71135973, 2334.82654185, 0.1027,
    0.5222, 5.37, 'TRAILING_STOP', 5.1,
    1, '1h', '2026-03-08T18:36:22.449123'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5222,
    pnl_amount = 5.37,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5B67FA57AF93449D', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2024-02-09 02:00:00', '2024-02-09 06:29:00', 1036.88386506, 1045.28886621,
    1021.33060708, 1062.80596169, 0.0938,
    0.8106, 7.6, 'TIME_EXIT', 4.48,
    1, '1h', '2026-03-08T18:36:22.452644'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8106,
    pnl_amount = 7.6,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D0C056B31115E094', 'FUNDING_PRO_v1', 'LINKUSDT', 'SHORT',
    '2024-02-09 16:00:00', '2024-02-09 23:26:02', 1298.36883729, 1303.55564106,
    1317.84436985, 1265.90961636, 0.1127,
    -0.3995, -4.5, 'TIME_EXIT', 7.43,
    0, '1h', '2026-03-08T18:36:22.453635'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3995,
    pnl_amount = -4.5,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B87B7BD42E7053E9', 'FUNDING_PRO_v1', 'DOGEUSDT', 'SHORT',
    '2024-02-12 12:00:00', '2024-02-12 23:05:45', 4200.65002941, 4167.8867775,
    4263.65977985, 4095.63377867, 0.0867,
    0.78, 6.76, 'TRAILING_STOP', 11.1,
    1, '1h', '2026-03-08T18:36:22.451767'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.78,
    pnl_amount = 6.76,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '54132E713A332C29', 'FUNDING_PRO_v1', 'XRPUSDT', 'SHORT',
    '2024-02-13 05:00:00', '2024-02-13 15:55:59', 3017.59349088, 3030.24391793,
    3062.85739324, 2942.15365361, 0.0864,
    -0.4192, -3.62, 'STOP_LOSS', 10.93,
    0, '1h', '2026-03-08T18:36:22.452263'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4192,
    pnl_amount = -3.62,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '76221367B1AEE765', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2024-02-17 00:00:00', '2024-02-17 07:40:51', 19501.36855202, 19330.50414328,
    19793.8890803, 19013.83433822, 0.0954,
    0.8762, 8.36, 'TAKE_PROFIT', 7.68,
    1, '1h', '2026-03-08T18:36:22.451073'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8762,
    pnl_amount = 8.36,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '705F07A23268C994', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2024-02-20 05:00:00', '2024-02-20 10:57:33', 3773.73396121, 3798.01234929,
    3717.12795179, 3868.07731024, 0.1195,
    0.6434, 7.69, 'TIME_EXIT', 5.96,
    1, '1h', '2026-03-08T18:36:22.449968'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6434,
    pnl_amount = 7.69,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '651CEB7B59147E76', 'FUNDING_PRO_v1', 'DOGEUSDT', 'LONG',
    '2024-03-04 22:00:00', '2024-03-05 06:28:48', 111.99001921, 112.94151782,
    110.31016892, 114.78976969, 0.0895,
    0.8496, 7.61, 'TAKE_PROFIT', 8.48,
    1, '1h', '2026-03-08T18:36:22.452714'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8496,
    pnl_amount = 7.61,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '53B712BB5B0EEB87', 'FUNDING_PRO_v1', 'XRPUSDT', 'LONG',
    '2024-03-06 07:00:00', '2024-03-06 16:35:23', 3121.04771853, 3107.03620396,
    3074.23200276, 3199.0739115, 0.0882,
    -0.4489, -3.96, 'TIME_EXIT', 9.59,
    0, '1h', '2026-03-08T18:36:22.453301'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4489,
    pnl_amount = -3.96,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '51E0DADFA15F6579', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2024-03-09 05:00:00', '2024-03-09 11:27:34', 2722.60578027, 2733.49071013,
    2763.44486697, 2654.54063576, 0.1104,
    -0.3998, -4.42, 'TIME_EXIT', 6.46,
    0, '1h', '2026-03-08T18:36:22.450747'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3998,
    pnl_amount = -4.42,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '80720A0B7B919EE0', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2024-03-09 12:00:00', '2024-03-09 20:48:20', 11370.69659897, 11308.32865364,
    11541.25704795, 11086.42918399, 0.089,
    0.5485, 4.88, 'TRAILING_STOP', 8.81,
    1, '1h', '2026-03-08T18:36:22.451534'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5485,
    pnl_amount = 4.88,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7182C7640D8CD71D', 'FUNDING_PRO_v1', 'LINKUSDT', 'SHORT',
    '2024-03-12 20:00:00', '2024-03-12 23:32:39', 3968.45169273, 3933.9853201,
    4027.97846812, 3869.24040041, 0.1019,
    0.8685, 8.85, 'TIME_EXIT', 3.54,
    1, '1h', '2026-03-08T18:36:22.452965'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8685,
    pnl_amount = 8.85,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F1AECB9979A1AB7D', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2024-03-14 11:00:00', '2024-03-14 16:46:07', 13324.06716541, 13414.81704183,
    13124.20615793, 13657.16884454, 0.0957,
    0.6811, 6.52, 'TAKE_PROFIT', 5.77,
    1, '1h', '2026-03-08T18:36:22.453396'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6811,
    pnl_amount = 6.52,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '998DF11D79F740A9', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2024-03-16 05:00:00', '2024-03-16 12:39:46', 1399.85752916, 1411.77740272,
    1378.85966623, 1434.85396739, 0.0818,
    0.8515, 6.97, 'TAKE_PROFIT', 7.66,
    1, '1h', '2026-03-08T18:36:22.450358'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8515,
    pnl_amount = 6.97,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3690814A837FF637', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2024-03-20 14:00:00', '2024-03-21 01:13:02', 2616.33999072, 2601.72871792,
    2655.58509058, 2550.93149095, 0.0833,
    0.5585, 4.65, 'TAKE_PROFIT', 11.22,
    1, '1h', '2026-03-08T18:36:22.452661'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5585,
    pnl_amount = 4.65,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '20261C9BCC1506A8', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2024-03-22 19:00:00', '2024-03-22 21:46:14', 4354.27957727, 4340.10899939,
    4288.96538361, 4463.1365667, 0.1035,
    -0.3254, -3.37, 'TIME_EXIT', 2.77,
    0, '1h', '2026-03-08T18:36:22.449426'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3254,
    pnl_amount = -3.37,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '809799EEB43E4F24', 'FUNDING_PRO_v1', 'ADAUSDT', 'LONG',
    '2024-03-28 13:00:00', '2024-03-28 16:19:30', 4040.2915042, 4064.69821552,
    3979.68713163, 4141.2987918, 0.1099,
    0.6041, 6.64, 'TAKE_PROFIT', 3.33,
    1, '1h', '2026-03-08T18:36:22.448882'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6041,
    pnl_amount = 6.64,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BE31DB2A0F120E3A', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2024-03-28 20:00:00', '2024-03-29 06:05:26', 881.5805653, 887.21343123,
    868.35685682, 903.62007943, 0.1187,
    0.639, 7.58, 'TIME_EXIT', 10.09,
    1, '1h', '2026-03-08T18:36:22.449113'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.639,
    pnl_amount = 7.58,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8EC0697CCF4A5395', 'FUNDING_PRO_v1', 'LINKUSDT', 'SHORT',
    '2024-03-28 22:00:00', '2024-03-29 00:04:07', 914.50963394, 917.68246851,
    928.22727844, 891.64689309, 0.1088,
    -0.3469, -3.77, 'TIME_EXIT', 2.07,
    0, '1h', '2026-03-08T18:36:22.453691'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3469,
    pnl_amount = -3.77,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E6557BE6ADE0893B', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2024-04-02 10:00:00', '2024-04-02 16:09:41', 1606.50849904, 1597.46958648,
    1630.60612652, 1566.34578656, 0.1106,
    0.5626, 6.22, 'TRAILING_STOP', 6.16,
    1, '1h', '2026-03-08T18:36:22.448945'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5626,
    pnl_amount = 6.22,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E07CB41613B103D5', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2024-04-03 04:00:00', '2024-04-03 07:13:04', 119.86394166, 118.69106306,
    121.66190079, 116.86734312, 0.1165,
    0.9785, 11.4, 'TRAILING_STOP', 3.22,
    1, '1h', '2026-03-08T18:36:22.451784'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9785,
    pnl_amount = 11.4,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5B95B39071D54BCF', 'FUNDING_PRO_v1', 'AVAXUSDT', 'SHORT',
    '2024-04-03 11:00:00', '2024-04-03 13:38:37', 932.1113555, 926.60125618,
    946.09302584, 908.80857162, 0.1022,
    0.5911, 6.04, 'TAKE_PROFIT', 2.64,
    1, '1h', '2026-03-08T18:36:22.451856'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5911,
    pnl_amount = 6.04,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B4C9F1C8344CA8B3', 'FUNDING_PRO_v1', 'DOTUSDT', 'SHORT',
    '2024-04-04 08:00:00', '2024-04-04 16:14:53', 4745.72482824, 4704.90432362,
    4816.91070067, 4627.08170754, 0.111,
    0.8602, 9.55, 'TIME_EXIT', 8.25,
    1, '1h', '2026-03-08T18:36:22.452653'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8602,
    pnl_amount = 9.55,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C0483D5BFED21007', 'FUNDING_PRO_v1', 'DOGEUSDT', 'LONG',
    '2024-04-04 12:00:00', '2024-04-04 23:07:45', 44.3147257, 44.13828759,
    43.65000481, 45.42259384, 0.1176,
    -0.3981, -4.68, 'STOP_LOSS', 11.13,
    0, '1h', '2026-03-08T18:36:22.449076'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3981,
    pnl_amount = -4.68,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B13E29CBF8F5C911', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2024-04-09 15:00:00', '2024-04-10 01:06:11', 40672.31108535, 40873.50544576,
    40062.22641907, 41689.11886249, 0.1013,
    0.4947, 5.01, 'TIME_EXIT', 10.1,
    1, '1h', '2026-03-08T18:36:22.448925'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4947,
    pnl_amount = 5.01,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EEF962646E02417B', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2024-04-10 07:00:00', '2024-04-10 10:50:19', 395.86903979, 398.78610254,
    389.9310042, 405.76576579, 0.1092,
    0.7369, 8.04, 'TAKE_PROFIT', 3.84,
    1, '1h', '2026-03-08T18:36:22.452938'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7369,
    pnl_amount = 8.04,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '83A8DBB14BD8A26C', 'FUNDING_PRO_v1', 'ADAUSDT', 'SHORT',
    '2024-04-14 05:00:00', '2024-04-14 08:37:04', 1500.19343724, 1491.16082978,
    1522.6963388, 1462.68860131, 0.1031,
    0.6021, 6.21, 'TAKE_PROFIT', 3.62,
    1, '1h', '2026-03-08T18:36:22.454074'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6021,
    pnl_amount = 6.21,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A83879E3CFB06B37', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2024-04-14 23:00:00', '2024-04-15 03:46:52', 4673.01575246, 4714.48426255,
    4602.92051618, 4789.84114627, 0.0987,
    0.8874, 8.76, 'TRAILING_STOP', 4.78,
    1, '1h', '2026-03-08T18:36:22.450260'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8874,
    pnl_amount = 8.76,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D2004AD57D0D28B2', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2024-04-15 00:00:00', '2024-04-15 04:57:45', 40130.00182351, 40501.40136978,
    39528.05179616, 41133.2518691, 0.0807,
    0.9255, 7.47, 'TAKE_PROFIT', 4.96,
    1, '1h', '2026-03-08T18:36:22.449046'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9255,
    pnl_amount = 7.47,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '38551C33E1410D95', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2024-04-19 04:00:00', '2024-04-19 08:21:13', 1142.61759386, 1133.68195723,
    1159.75685776, 1114.05215401, 0.1141,
    0.782, 8.92, 'TAKE_PROFIT', 4.35,
    1, '1h', '2026-03-08T18:36:22.451026'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.782,
    pnl_amount = 8.92,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B9A5E537BB384DE3', 'FUNDING_PRO_v1', 'XRPUSDT', 'LONG',
    '2024-04-25 22:00:00', '2024-04-26 09:44:46', 660.78883373, 666.94416542,
    650.87700123, 677.30855458, 0.1069,
    0.9315, 9.95, 'TAKE_PROFIT', 11.75,
    1, '1h', '2026-03-08T18:36:22.450439'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9315,
    pnl_amount = 9.95,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '3571DC5A2BD345D0', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2024-04-27 13:00:00', '2024-04-27 22:18:13', 3274.87893896, 3303.5182377,
    3225.75575488, 3356.75091244, 0.0866,
    0.8745, 7.57, 'TAKE_PROFIT', 9.3,
    1, '1h', '2026-03-08T18:36:22.453002'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8745,
    pnl_amount = 7.57,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '30C4334655B14F88', 'FUNDING_PRO_v1', 'AVAXUSDT', 'LONG',
    '2024-04-28 10:00:00', '2024-04-28 17:35:29', 4748.61884934, 4732.03575907,
    4677.3895666, 4867.33432057, 0.1043,
    -0.3492, -3.64, 'STOP_LOSS', 7.59,
    0, '1h', '2026-03-08T18:36:22.451231'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3492,
    pnl_amount = -3.64,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1322A23897DA4ED9', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2024-05-06 05:00:00', '2024-05-06 09:44:38', 375.63951619, 373.62722945,
    381.27410893, 366.24852828, 0.1083,
    0.5357, 5.8, 'TRAILING_STOP', 4.74,
    1, '1h', '2026-03-08T18:36:22.449236'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5357,
    pnl_amount = 5.8,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2D8242528533E8A0', 'FUNDING_PRO_v1', 'XRPUSDT', 'SHORT',
    '2024-05-07 15:00:00', '2024-05-07 18:05:21', 1737.55847647, 1727.2612603,
    1763.62185362, 1694.11951456, 0.0958,
    0.5926, 5.68, 'TRAILING_STOP', 3.09,
    1, '1h', '2026-03-08T18:36:22.454138'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5926,
    pnl_amount = 5.68,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D4FE523974F0BD95', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2024-05-10 22:00:00', '2024-05-11 04:47:46', 927.5618822, 919.37000374,
    941.47531043, 904.37283515, 0.0879,
    0.8832, 7.76, 'TRAILING_STOP', 6.8,
    1, '1h', '2026-03-08T18:36:22.452608'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8832,
    pnl_amount = 7.76,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2E958AFC7C4D857D', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2024-05-20 08:00:00', '2024-05-20 12:34:57', 15388.38595259, 15464.62642985,
    15157.5601633, 15773.0956014, 0.1136,
    0.4954, 5.63, 'TRAILING_STOP', 4.58,
    1, '1h', '2026-03-08T18:36:22.451425'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4954,
    pnl_amount = 5.63,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2EEB5989515FBF52', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2024-05-27 05:00:00', '2024-05-27 15:22:14', 3329.63583907, 3298.72942858,
    3379.58037666, 3246.3949431, 0.0819,
    0.9282, 7.6, 'TIME_EXIT', 10.37,
    1, '1h', '2026-03-08T18:36:22.453133'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9282,
    pnl_amount = 7.6,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8B59FBEFD4920BB3', 'FUNDING_PRO_v1', 'XRPUSDT', 'LONG',
    '2024-05-30 07:00:00', '2024-05-30 14:28:42', 4540.76119369, 4581.68588187,
    4472.64977579, 4654.28022354, 0.1049,
    0.9013, 9.46, 'TAKE_PROFIT', 7.48,
    1, '1h', '2026-03-08T18:36:22.449026'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9013,
    pnl_amount = 9.46,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8C6C6484B9922A46', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2024-06-03 14:00:00', '2024-06-03 18:42:26', 43.0948105, 42.74746738,
    43.74123265, 42.01744023, 0.1173,
    0.806, 9.45, 'TIME_EXIT', 4.71,
    1, '1h', '2026-03-08T18:36:22.449748'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.806,
    pnl_amount = 9.45,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '67D99E048066979E', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2024-06-10 04:00:00', '2024-06-10 11:00:58', 1274.27817718, 1285.38208444,
    1255.16400453, 1306.13513161, 0.0962,
    0.8714, 8.38, 'TRAILING_STOP', 7.02,
    1, '1h', '2026-03-08T18:36:22.452912'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8714,
    pnl_amount = 8.38,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '79D47E2C42B563C3', 'FUNDING_PRO_v1', 'XRPUSDT', 'LONG',
    '2024-06-16 04:00:00', '2024-06-16 10:51:11', 3859.10609183, 3878.38910215,
    3801.21950046, 3955.58374413, 0.0948,
    0.4997, 4.73, 'TIME_EXIT', 6.85,
    1, '1h', '2026-03-08T18:36:22.453755'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4997,
    pnl_amount = 4.73,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E9E091B000094350', 'FUNDING_PRO_v1', 'XRPUSDT', 'SHORT',
    '2024-06-17 03:00:00', '2024-06-17 08:05:15', 2449.95948363, 2427.16915777,
    2486.70887588, 2388.71049654, 0.1031,
    0.9302, 9.59, 'TAKE_PROFIT', 5.09,
    1, '1h', '2026-03-08T18:36:22.448892'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9302,
    pnl_amount = 9.59,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '104B2D142854FF93', 'FUNDING_PRO_v1', 'DOGEUSDT', 'LONG',
    '2024-06-27 19:00:00', '2024-06-28 05:08:01', 1981.29244245, 1972.79090503,
    1951.57305582, 2030.82475352, 0.087,
    -0.4291, -3.73, 'STOP_LOSS', 10.13,
    0, '1h', '2026-03-08T18:36:22.451882'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4291,
    pnl_amount = -3.73,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7959EF9248EB4942', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2024-06-29 20:00:00', '2024-06-30 03:45:29', 3068.69368396, 3058.77131884,
    3022.6632787, 3145.41102606, 0.1082,
    -0.3233, -3.5, 'TIME_EXIT', 7.76,
    0, '1h', '2026-03-08T18:36:22.454282'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3233,
    pnl_amount = -3.5,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6504C86B6B51CD73', 'FUNDING_PRO_v1', 'DOGEUSDT', 'LONG',
    '2024-07-01 15:00:00', '2024-07-02 02:17:11', 1048.42061065, 1054.99200391,
    1032.69430149, 1074.63112592, 0.0958,
    0.6268, 6.0, 'TRAILING_STOP', 11.29,
    1, '1h', '2026-03-08T18:36:22.449217'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6268,
    pnl_amount = 6.0,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2BF7883FD401549B', 'FUNDING_PRO_v1', 'ADAUSDT', 'LONG',
    '2024-07-08 05:00:00', '2024-07-08 16:13:24', 769.67634915, 775.86546462,
    758.13120392, 788.91825788, 0.0821,
    0.8041, 6.6, 'TIME_EXIT', 11.22,
    1, '1h', '2026-03-08T18:36:22.452625'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8041,
    pnl_amount = 6.6,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D6BB73B1614B0952', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2024-07-11 02:00:00', '2024-07-11 11:01:40', 15900.69763822, 16040.65959659,
    15662.18717364, 16298.21507917, 0.1008,
    0.8802, 8.88, 'TIME_EXIT', 9.03,
    1, '1h', '2026-03-08T18:36:22.450546'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8802,
    pnl_amount = 8.88,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0AB900B565AB6473', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2024-07-12 12:00:00', '2024-07-12 14:18:25', 21448.8724018, 21288.0146368,
    21770.60548782, 20912.65059175, 0.0811,
    0.75, 6.08, 'TAKE_PROFIT', 2.31,
    1, '1h', '2026-03-08T18:36:22.449227'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.75,
    pnl_amount = 6.08,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F14B48A3A3F5AC33', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2024-07-14 11:00:00', '2024-07-14 16:20:09', 579.00849486, 581.33915642,
    587.69362228, 564.53328249, 0.0801,
    -0.4025, -3.22, 'TIME_EXIT', 5.34,
    0, '1h', '2026-03-08T18:36:22.452436'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4025,
    pnl_amount = -3.22,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1424C349E236D650', 'FUNDING_PRO_v1', 'AVAXUSDT', 'LONG',
    '2024-07-15 19:00:00', '2024-07-16 03:08:06', 4380.80177628, 4421.30448094,
    4315.08974964, 4490.32182069, 0.1044,
    0.9246, 9.66, 'TIME_EXIT', 8.14,
    1, '1h', '2026-03-08T18:36:22.453021'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9246,
    pnl_amount = 9.66,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '482D1C263D9AAD41', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2024-07-17 21:00:00', '2024-07-18 08:19:58', 33132.2687454, 32835.85824267,
    33629.25277658, 32303.96202677, 0.0878,
    0.8946, 7.85, 'TRAILING_STOP', 11.33,
    1, '1h', '2026-03-08T18:36:22.449721'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8946,
    pnl_amount = 7.85,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '68E1B65E125752C2', 'FUNDING_PRO_v1', 'DOGEUSDT', 'SHORT',
    '2024-07-20 14:00:00', '2024-07-20 22:29:26', 4790.49098903, 4760.24572217,
    4862.34835387, 4670.72871431, 0.092,
    0.6314, 5.81, 'TAKE_PROFIT', 8.49,
    1, '1h', '2026-03-08T18:36:22.449813'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6314,
    pnl_amount = 5.81,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'ACC4090A02790353', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2024-07-20 18:00:00', '2024-07-21 03:47:08', 1765.50933722, 1773.03763663,
    1791.99197728, 1721.37160379, 0.0821,
    -0.4264, -3.5, 'STOP_LOSS', 9.79,
    0, '1h', '2026-03-08T18:36:22.454408'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4264,
    pnl_amount = -3.5,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '55184B560E00B0D2', 'FUNDING_PRO_v1', 'BNBUSDT', 'LONG',
    '2024-07-23 20:00:00', '2024-07-23 23:58:53', 1567.80516858, 1562.10283796,
    1544.28809105, 1607.00029779, 0.0971,
    -0.3637, -3.53, 'STOP_LOSS', 3.98,
    0, '1h', '2026-03-08T18:36:22.449932'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3637,
    pnl_amount = -3.53,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'AEA58BF96660AF9E', 'FUNDING_PRO_v1', 'DOGEUSDT', 'LONG',
    '2024-07-25 04:00:00', '2024-07-25 13:42:57', 4342.25632422, 4375.92763663,
    4277.12247936, 4450.81273233, 0.0954,
    0.7754, 7.4, 'TAKE_PROFIT', 9.72,
    1, '1h', '2026-03-08T18:36:22.450252'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7754,
    pnl_amount = 7.4,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'EF8CFD7A477F447D', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2024-08-01 17:00:00', '2024-08-02 00:50:29', 1034.85672738, 1041.83760172,
    1019.33387647, 1060.72814556, 0.0925,
    0.6746, 6.24, 'TRAILING_STOP', 7.84,
    1, '1h', '2026-03-08T18:36:22.452273'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6746,
    pnl_amount = 6.24,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7CA61B4C15C7AA0D', 'FUNDING_PRO_v1', 'DOTUSDT', 'SHORT',
    '2024-08-16 16:00:00', '2024-08-17 03:09:02', 785.66658456, 780.20804886,
    797.45158332, 766.02491994, 0.1128,
    0.6948, 7.83, 'TRAILING_STOP', 11.15,
    1, '1h', '2026-03-08T18:36:22.453255'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6948,
    pnl_amount = 7.83,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C4D3C992DACE875D', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2024-08-16 19:00:00', '2024-08-16 21:14:22', 1273.42490238, 1263.53206134,
    1292.52627591, 1241.58927982, 0.0875,
    0.7769, 6.8, 'TIME_EXIT', 2.24,
    1, '1h', '2026-03-08T18:36:22.451361'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7769,
    pnl_amount = 6.8,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'B237DBB1F084214B', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2024-08-21 02:00:00', '2024-08-21 09:53:21', 25618.3987263, 25704.71847468,
    26002.67470719, 24977.93875814, 0.1082,
    -0.3369, -3.65, 'STOP_LOSS', 7.89,
    0, '1h', '2026-03-08T18:36:22.452590'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3369,
    pnl_amount = -3.65,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E01C1EF75A0B076A', 'FUNDING_PRO_v1', 'BNBUSDT', 'SHORT',
    '2024-08-24 10:00:00', '2024-08-24 20:35:30', 2888.53860382, 2898.45083271,
    2931.86668288, 2816.32513873, 0.1133,
    -0.3432, -3.89, 'STOP_LOSS', 10.59,
    0, '1h', '2026-03-08T18:36:22.452705'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3432,
    pnl_amount = -3.89,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '15286B3DAB15D95E', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2024-08-24 14:00:00', '2024-08-24 17:11:33', 2061.4532828, 2076.36949167,
    2030.53148356, 2112.98961487, 0.108,
    0.7236, 7.81, 'TIME_EXIT', 3.19,
    1, '1h', '2026-03-08T18:36:22.451462'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7236,
    pnl_amount = 7.81,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '22B0451C258CAF6A', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2024-08-28 14:00:00', '2024-08-28 21:11:52', 39773.07300521, 39979.5547246,
    39176.47691013, 40767.39983034, 0.0878,
    0.5191, 4.56, 'TIME_EXIT', 7.2,
    1, '1h', '2026-03-08T18:36:22.450959'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5191,
    pnl_amount = 4.56,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A0F97BFC8008DBFE', 'FUNDING_PRO_v1', 'AVAXUSDT', 'SHORT',
    '2024-09-05 01:00:00', '2024-09-05 12:54:39', 326.72515501, 327.85883233,
    331.62603234, 318.55702614, 0.087,
    -0.347, -3.02, 'TIME_EXIT', 11.91,
    0, '1h', '2026-03-08T18:36:22.452282'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.347,
    pnl_amount = -3.02,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '070EF576C72B95BE', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2024-09-12 09:00:00', '2024-09-12 14:32:34', 26768.2798715, 27028.12558178,
    26366.75567342, 27437.48686828, 0.0903,
    0.9707, 8.76, 'TRAILING_STOP', 5.54,
    1, '1h', '2026-03-08T18:36:22.449208'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9707,
    pnl_amount = 8.76,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A717D9D3B4695A81', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2024-09-13 12:00:00', '2024-09-13 23:16:48', 971.29861916, 974.99388123,
    985.86809844, 947.01615368, 0.0945,
    -0.3804, -3.6, 'STOP_LOSS', 11.28,
    0, '1h', '2026-03-08T18:36:22.451453'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3804,
    pnl_amount = -3.6,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '900E94594A5F9561', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2024-09-14 08:00:00', '2024-09-14 10:26:12', 1055.37172161, 1059.26636219,
    1071.20229743, 1028.98742857, 0.0824,
    -0.369, -3.04, 'STOP_LOSS', 2.44,
    0, '1h', '2026-03-08T18:36:22.451417'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.369,
    pnl_amount = -3.04,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'D27B70AD2239CECC', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2024-09-15 11:00:00', '2024-09-15 20:30:36', 15019.15744118, 14898.88929195,
    15244.4448028, 14643.67850515, 0.1187,
    0.8008, 9.5, 'TIME_EXIT', 9.51,
    1, '1h', '2026-03-08T18:36:22.448914'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8008,
    pnl_amount = 9.5,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '57824EDED5614C3B', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2024-09-15 11:00:00', '2024-09-15 19:41:59', 3886.53553932, 3868.74129418,
    3828.23750623, 3983.6989278, 0.107,
    -0.4578, -4.9, 'TIME_EXIT', 8.7,
    0, '1h', '2026-03-08T18:36:22.450656'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4578,
    pnl_amount = -4.9,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '10F89BA3670BF936', 'FUNDING_PRO_v1', 'DOGEUSDT', 'SHORT',
    '2024-09-18 15:00:00', '2024-09-18 17:23:54', 1983.23138471, 1972.54221475,
    2012.97985548, 1933.65060009, 0.1068,
    0.539, 5.75, 'TIME_EXIT', 2.4,
    1, '1h', '2026-03-08T18:36:22.452546'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.539,
    pnl_amount = 5.75,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4D2B6E04CD986C12', 'FUNDING_PRO_v1', 'XRPUSDT', 'LONG',
    '2024-09-18 16:00:00', '2024-09-18 20:21:27', 880.9749901, 885.33392248,
    867.76036525, 902.99936486, 0.1071,
    0.4948, 5.3, 'TAKE_PROFIT', 4.36,
    1, '1h', '2026-03-08T18:36:22.450812'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4948,
    pnl_amount = 5.3,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '71A3D2C3098E342C', 'FUNDING_PRO_v1', 'ADAUSDT', 'LONG',
    '2024-09-20 05:00:00', '2024-09-20 13:01:16', 2498.07516618, 2512.07887515,
    2460.60403869, 2560.52704533, 0.1165,
    0.5606, 6.53, 'TRAILING_STOP', 8.02,
    1, '1h', '2026-03-08T18:36:22.452684'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5606,
    pnl_amount = 6.53,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E0F871451DE32A57', 'FUNDING_PRO_v1', 'DOGEUSDT', 'LONG',
    '2024-09-26 03:00:00', '2024-09-26 09:52:57', 937.33008345, 933.31387049,
    923.2701322, 960.76333554, 0.1147,
    -0.4285, -4.92, 'TIME_EXIT', 6.88,
    0, '1h', '2026-03-08T18:36:22.449739'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4285,
    pnl_amount = -4.92,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E9D780999B8976AC', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2024-09-27 02:00:00', '2024-09-27 13:02:47', 20325.17498371, 20152.46629177,
    20630.05260846, 19817.04560911, 0.0985,
    0.8497, 8.37, 'TIME_EXIT', 11.05,
    1, '1h', '2026-03-08T18:36:22.449492'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8497,
    pnl_amount = 8.37,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '54500EF36FBB8F95', 'FUNDING_PRO_v1', 'XRPUSDT', 'SHORT',
    '2024-09-29 05:00:00', '2024-09-29 10:22:28', 460.32073339, 455.91360191,
    467.22554439, 448.81271505, 0.0958,
    0.9574, 9.18, 'TIME_EXIT', 5.37,
    1, '1h', '2026-03-08T18:36:22.451864'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9574,
    pnl_amount = 9.18,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '093810D07C3C3321', 'FUNDING_PRO_v1', 'AVAXUSDT', 'SHORT',
    '2024-10-05 07:00:00', '2024-10-05 16:54:36', 4001.89142177, 4015.03289255,
    4061.91979309, 3901.84413622, 0.1172,
    -0.3284, -3.85, 'TIME_EXIT', 9.91,
    0, '1h', '2026-03-08T18:36:22.450484'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3284,
    pnl_amount = -3.85,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4F803508A2B0C2A4', 'FUNDING_PRO_v1', 'LINKUSDT', 'SHORT',
    '2024-10-12 12:00:00', '2024-10-12 14:16:36', 2864.51117414, 2848.32641144,
    2907.47884175, 2792.89839479, 0.1053,
    0.565, 5.95, 'TIME_EXIT', 2.28,
    1, '1h', '2026-03-08T18:36:22.453217'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.565,
    pnl_amount = 5.95,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BF156DB4CB8258AD', 'FUNDING_PRO_v1', 'ETHUSDT', 'LONG',
    '2024-10-15 05:00:00', '2024-10-15 08:22:50', 1858.932363, 1875.92900871,
    1831.04837755, 1905.40567207, 0.107,
    0.9143, 9.79, 'TIME_EXIT', 3.38,
    1, '1h', '2026-03-08T18:36:22.451614'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9143,
    pnl_amount = 9.79,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '94856B54CAA1F261', 'FUNDING_PRO_v1', 'XRPUSDT', 'SHORT',
    '2024-10-17 04:00:00', '2024-10-17 12:37:00', 372.37867831, 370.50396574,
    377.96435848, 363.06921135, 0.1128,
    0.5034, 5.68, 'TAKE_PROFIT', 8.62,
    1, '1h', '2026-03-08T18:36:22.451035'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5034,
    pnl_amount = 5.68,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C2ABAD76183C34BC', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2024-10-18 05:00:00', '2024-10-18 08:43:08', 455.89285672, 453.48151493,
    462.73124957, 444.4955353, 0.1163,
    0.5289, 6.15, 'TIME_EXIT', 3.72,
    1, '1h', '2026-03-08T18:36:22.451820'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5289,
    pnl_amount = 6.15,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '050DECA62B5B3239', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2024-10-19 05:00:00', '2024-10-19 16:05:10', 616.95269, 611.58731151,
    626.20698035, 601.52887275, 0.0864,
    0.8697, 7.51, 'TAKE_PROFIT', 11.09,
    1, '1h', '2026-03-08T18:36:22.450278'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8697,
    pnl_amount = 7.51,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '425628129E22CBA6', 'FUNDING_PRO_v1', 'AVAXUSDT', 'LONG',
    '2024-10-19 10:00:00', '2024-10-19 19:41:30', 462.56574024, 466.99750964,
    455.62725413, 474.12988374, 0.1057,
    0.9581, 10.13, 'TRAILING_STOP', 9.69,
    1, '1h', '2026-03-08T18:36:22.453319'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9581,
    pnl_amount = 10.13,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8C74B09A804347A1', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2024-10-20 16:00:00', '2024-10-20 22:00:37', 1541.60178861, 1548.46163387,
    1564.72581544, 1503.06174389, 0.0966,
    -0.445, -4.3, 'STOP_LOSS', 6.01,
    0, '1h', '2026-03-08T18:36:22.453915'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.445,
    pnl_amount = -4.3,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '2E17859813A8DAD8', 'FUNDING_PRO_v1', 'LINKUSDT', 'LONG',
    '2024-10-27 18:00:00', '2024-10-28 00:33:48', 2474.48681502, 2464.5886408,
    2437.36951279, 2536.34898539, 0.084,
    -0.4, -3.36, 'STOP_LOSS', 6.56,
    0, '1h', '2026-03-08T18:36:22.450269'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4,
    pnl_amount = -3.36,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '636723F6DAE5D3F2', 'FUNDING_PRO_v1', 'SOLUSDT', 'LONG',
    '2024-10-30 01:00:00', '2024-10-30 03:46:30', 4477.77830895, 4518.86978251,
    4410.61163432, 4589.72276668, 0.115,
    0.9177, 10.55, 'TAKE_PROFIT', 2.78,
    1, '1h', '2026-03-08T18:36:22.449349'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9177,
    pnl_amount = 10.55,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '1CB6BE87C02847A1', 'FUNDING_PRO_v1', 'BNBUSDT', 'LONG',
    '2024-10-30 13:00:00', '2024-10-30 22:43:07', 3213.42456635, 3244.72978833,
    3165.22319785, 3293.7601805, 0.1011,
    0.9742, 9.84, 'TIME_EXIT', 9.72,
    1, '1h', '2026-03-08T18:36:22.451579'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9742,
    pnl_amount = 9.84,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'BD2596AC6AD40E27', 'FUNDING_PRO_v1', 'ADAUSDT', 'LONG',
    '2024-11-01 18:00:00', '2024-11-02 05:37:15', 4615.88876605, 4654.15422438,
    4546.65043456, 4731.28598521, 0.0874,
    0.829, 7.24, 'TRAILING_STOP', 11.62,
    1, '1h', '2026-03-08T18:36:22.449142'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.829,
    pnl_amount = 7.24,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A2B2BCB5F4CB7AD5', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2024-11-03 03:00:00', '2024-11-03 08:27:57', 2893.18518439, 2866.01097369,
    2936.58296216, 2820.85555478, 0.0819,
    0.9392, 7.69, 'TRAILING_STOP', 5.47,
    1, '1h', '2026-03-08T18:36:22.451525'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9392,
    pnl_amount = 7.69,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5BE1DF4010761840', 'FUNDING_PRO_v1', 'AVAXUSDT', 'SHORT',
    '2024-11-05 01:00:00', '2024-11-05 04:10:50', 2588.53247449, 2600.27196482,
    2627.36046161, 2523.81916263, 0.0998,
    -0.4535, -4.53, 'TIME_EXIT', 3.18,
    0, '1h', '2026-03-08T18:36:22.454467'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4535,
    pnl_amount = -4.53,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '152F7CD8F88FB718', 'FUNDING_PRO_v1', 'DOTUSDT', 'SHORT',
    '2024-11-09 06:00:00', '2024-11-09 17:25:07', 594.22141385, 589.27775887,
    603.13473506, 579.3658785, 0.0919,
    0.832, 7.65, 'TAKE_PROFIT', 11.42,
    1, '1h', '2026-03-08T18:36:22.454242'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.832,
    pnl_amount = 7.65,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '03CA456B07958F1F', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2024-11-10 03:00:00', '2024-11-10 07:53:38', 14710.3974315, 14569.15480873,
    14931.05339298, 14342.63749572, 0.104,
    0.9602, 9.98, 'TIME_EXIT', 4.89,
    1, '1h', '2026-03-08T18:36:22.451269'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9602,
    pnl_amount = 9.98,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '0F5237506EB327D8', 'FUNDING_PRO_v1', 'DOGEUSDT', 'SHORT',
    '2024-11-11 21:00:00', '2024-11-12 01:06:55', 4262.16999912, 4231.26960221,
    4326.10254911, 4155.61574914, 0.0962,
    0.725, 6.98, 'TAKE_PROFIT', 4.12,
    1, '1h', '2026-03-08T18:36:22.452780'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.725,
    pnl_amount = 6.98,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'F227F125603B7F27', 'FUNDING_PRO_v1', 'ADAUSDT', 'SHORT',
    '2024-11-13 20:00:00', '2024-11-14 03:05:47', 3443.77076438, 3426.63877955,
    3495.42732584, 3357.67649527, 0.1108,
    0.4975, 5.51, 'TRAILING_STOP', 7.1,
    1, '1h', '2026-03-08T18:36:22.454111'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.4975,
    pnl_amount = 5.51,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7CB877729575DCEA', 'FUNDING_PRO_v1', 'ADAUSDT', 'LONG',
    '2024-11-17 06:00:00', '2024-11-17 08:36:06', 4824.91302843, 4859.43305016,
    4752.539333, 4945.53585414, 0.1014,
    0.7155, 7.26, 'TRAILING_STOP', 2.6,
    1, '1h', '2026-03-08T18:36:22.451677'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7155,
    pnl_amount = 7.26,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '69093276CC875AC8', 'FUNDING_PRO_v1', 'XRPUSDT', 'SHORT',
    '2024-11-20 22:00:00', '2024-11-21 03:30:00', 109.54101307, 110.04126298,
    111.18412827, 106.80248774, 0.1048,
    -0.4567, -4.79, 'TIME_EXIT', 5.5,
    0, '1h', '2026-03-08T18:36:22.451007'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4567,
    pnl_amount = -4.79,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'DFE71B98518CF549', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2024-11-21 11:00:00', '2024-11-21 13:50:37', 32902.33654778, 32747.81862075,
    32408.80149957, 33724.89496148, 0.0839,
    -0.4696, -3.94, 'STOP_LOSS', 2.84,
    0, '1h', '2026-03-08T18:36:22.454479'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4696,
    pnl_amount = -3.94,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '4C872D548EFBB7F2', 'FUNDING_PRO_v1', 'XRPUSDT', 'LONG',
    '2024-11-27 00:00:00', '2024-11-27 04:34:37', 2820.78285574, 2810.83616119,
    2778.47111291, 2891.30242714, 0.1104,
    -0.3526, -3.89, 'STOP_LOSS', 4.58,
    0, '1h', '2026-03-08T18:36:22.450233'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3526,
    pnl_amount = -3.89,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '961B52D736C3707D', 'FUNDING_PRO_v1', 'XRPUSDT', 'LONG',
    '2024-11-27 01:00:00', '2024-11-27 04:58:48', 323.77720132, 325.6061395,
    318.9205433, 331.87163135, 0.1027,
    0.5649, 5.8, 'TAKE_PROFIT', 3.98,
    1, '1h', '2026-03-08T18:36:22.451176'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.5649,
    pnl_amount = 5.8,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'C385677F8F59AFD8', 'FUNDING_PRO_v1', 'BNBUSDT', 'SHORT',
    '2024-12-05 01:00:00', '2024-12-05 12:27:01', 4939.85800252, 4904.89869074,
    5013.95587256, 4816.36155246, 0.1047,
    0.7077, 7.41, 'TRAILING_STOP', 11.45,
    1, '1h', '2026-03-08T18:36:22.450627'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7077,
    pnl_amount = 7.41,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '7771EA5BD6D481E0', 'FUNDING_PRO_v1', 'XRPUSDT', 'LONG',
    '2024-12-06 08:00:00', '2024-12-06 15:26:17', 349.5277742, 351.84872203,
    344.28485759, 358.26596856, 0.1195,
    0.664, 7.93, 'TIME_EXIT', 7.44,
    1, '1h', '2026-03-08T18:36:22.451278'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.664,
    pnl_amount = 7.93,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '167000F536D8E3CC', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2024-12-09 02:00:00', '2024-12-09 07:00:53', 696.97039137, 691.6470887,
    707.42494724, 679.54613159, 0.1142,
    0.7638, 8.72, 'TIME_EXIT', 5.01,
    1, '1h', '2026-03-08T18:36:22.452408'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7638,
    pnl_amount = 8.72,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '90A4AD6E32C7B2CB', 'FUNDING_PRO_v1', 'BNBUSDT', 'LONG',
    '2024-12-14 10:00:00', '2024-12-14 18:43:49', 3063.39053719, 3086.9450327,
    3017.43967913, 3139.97530062, 0.1186,
    0.7689, 9.12, 'TIME_EXIT', 8.73,
    1, '1h', '2026-03-08T18:36:22.453540'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7689,
    pnl_amount = 9.12,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '6A83549FB65640EF', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2024-12-21 13:00:00', '2024-12-21 20:16:10', 14884.80378331, 14832.58757305,
    14661.53172656, 15256.92387789, 0.0996,
    -0.3508, -3.49, 'TIME_EXIT', 7.27,
    0, '1h', '2026-03-08T18:36:22.454390'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3508,
    pnl_amount = -3.49,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '8A13243DB24D2562', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2024-12-24 04:00:00', '2024-12-24 08:23:01', 21642.95794226, 21545.62540089,
    21318.31357313, 22184.03189082, 0.0999,
    -0.4497, -4.49, 'STOP_LOSS', 4.38,
    0, '1h', '2026-03-08T18:36:22.452162'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4497,
    pnl_amount = -4.49,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'E1F5D87E03CA3677', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2024-12-24 07:00:00', '2024-12-24 13:48:45', 2304.91206081, 2312.96039015,
    2339.48574172, 2247.28925929, 0.1199,
    -0.3492, -4.19, 'TIME_EXIT', 6.81,
    0, '1h', '2026-03-08T18:36:22.451212'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3492,
    pnl_amount = -4.19,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'ACCBC6AED720CB9C', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2024-12-27 16:00:00', '2024-12-27 19:20:45', 26827.27309259, 26914.9501964,
    27229.68218898, 26156.59126527, 0.1042,
    -0.3268, -3.41, 'STOP_LOSS', 3.35,
    0, '1h', '2026-03-08T18:36:22.449803'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3268,
    pnl_amount = -3.41,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '012F3760F9DF1E56', 'FUNDING_PRO_v1', 'ETHUSDT', 'SHORT',
    '2024-12-27 19:00:00', '2024-12-27 23:26:32', 2193.87972893, 2178.7295614,
    2226.78792486, 2139.0327357, 0.1026,
    0.6906, 7.09, 'TRAILING_STOP', 4.44,
    1, '1h', '2026-03-08T18:36:22.449311'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.6906,
    pnl_amount = 7.09,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '83EB7D54BB9945F1', 'FUNDING_PRO_v1', 'BTCUSDT', 'SHORT',
    '2025-01-05 08:00:00', '2025-01-05 15:10:26', 41899.19656769, 41514.09569101,
    42527.6845162, 40851.71665349, 0.0911,
    0.9191, 8.37, 'TRAILING_STOP', 7.17,
    1, '1h', '2026-03-08T18:36:22.453862'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.9191,
    pnl_amount = 8.37,
    exit_reason = 'TRAILING_STOP';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '96248017550A2871', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2025-01-11 09:00:00', '2025-01-11 20:41:35', 1693.37813424, 1700.44715985,
    1718.77880625, 1651.04368088, 0.0884,
    -0.4175, -3.69, 'STOP_LOSS', 11.69,
    0, '1h', '2026-03-08T18:36:22.448968'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4175,
    pnl_amount = -3.69,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '010746F2DB44B3DE', 'FUNDING_PRO_v1', 'BTCUSDT', 'LONG',
    '2025-01-13 21:00:00', '2025-01-14 05:18:00', 4462.12868379, 4440.92514276,
    4395.19675353, 4573.68190088, 0.1034,
    -0.4752, -4.92, 'TIME_EXIT', 8.3,
    0, '1h', '2026-03-08T18:36:22.449767'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4752,
    pnl_amount = -4.92,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'A3900FABD1012EC9', 'FUNDING_PRO_v1', 'LINKUSDT', 'LONG',
    '2025-01-18 22:00:00', '2025-01-19 01:32:57', 3517.18723087, 3505.50977832,
    3464.4294224, 3605.11691164, 0.1049,
    -0.332, -3.48, 'STOP_LOSS', 3.55,
    0, '1h', '2026-03-08T18:36:22.450609'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.332,
    pnl_amount = -3.48,
    exit_reason = 'STOP_LOSS';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '58B7BEBBFC8614F7', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2025-02-04 06:00:00', '2025-02-04 13:23:20', 215.62864976, 216.37833957,
    218.86307951, 210.23793352, 0.1141,
    -0.3477, -3.97, 'TIME_EXIT', 7.39,
    0, '1h', '2026-03-08T18:36:22.451900'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.3477,
    pnl_amount = -3.97,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '60E4AFC74CFD7169', 'FUNDING_PRO_v1', 'ADAUSDT', 'LONG',
    '2025-02-05 03:00:00', '2025-02-05 08:42:42', 1574.5622124, 1586.11121907,
    1550.94377921, 1613.92626771, 0.1037,
    0.7335, 7.61, 'TIME_EXIT', 5.71,
    1, '1h', '2026-03-08T18:36:22.449849'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7335,
    pnl_amount = 7.61,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '62E92EFE46F9A5AC', 'FUNDING_PRO_v1', 'XRPUSDT', 'SHORT',
    '2025-02-14 03:00:00', '2025-02-14 13:21:12', 799.87594369, 794.26933723,
    811.87408285, 779.8790451, 0.0931,
    0.7009, 6.52, 'TIME_EXIT', 10.35,
    1, '1h', '2026-03-08T18:36:22.451811'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.7009,
    pnl_amount = 6.52,
    exit_reason = 'TIME_EXIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    '5AF0CF97983CDED8', 'FUNDING_PRO_v1', 'XRPUSDT', 'SHORT',
    '2025-02-15 04:00:00', '2025-02-15 12:55:56', 1061.67066063, 1052.72391268,
    1077.59572054, 1035.12889411, 0.1158,
    0.8427, 9.76, 'TAKE_PROFIT', 8.93,
    1, '1h', '2026-03-08T18:36:22.453247'
) ON DUPLICATE KEY UPDATE
    pnl_pct = 0.8427,
    pnl_amount = 9.76,
    exit_reason = 'TAKE_PROFIT';

INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, timeframe, created_at
) VALUES (
    'CB683AB517211D1E', 'FUNDING_PRO_v1', 'SOLUSDT', 'SHORT',
    '2025-02-15 09:00:00', '2025-02-15 17:35:08', 3425.00163137, 3439.59599127,
    3476.37665585, 3339.37659059, 0.1105,
    -0.4261, -4.71, 'STOP_LOSS', 8.59,
    0, '1h', '2026-03-08T18:36:22.449445'
) ON DUPLICATE KEY UPDATE
    pnl_pct = -0.4261,
    pnl_amount = -4.71,
    exit_reason = 'STOP_LOSS';